"""
Unified Stress Models

Combines:
- Temperature stress model (heat/cold/frost, acclimation, damage)
- Integrated multi-stress model (water, temperature, nutrient, light, salinity, etc.)

This consolidation replaces:
- src/models/temperature_stress.py
- src/models/integrated_stress.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import math
import numpy as np

# =========================
# Temperature Stress Model
# =========================


class TemperatureStressType(Enum):
    HEAT = "heat"
    COLD = "cold"
    FROST = "frost"
    OPTIMAL = "optimal"


@dataclass
class TemperatureStressParameters:
    optimal_temp_min: float = None
    optimal_temp_max: float = None
    heat_threshold_mild: float = None
    heat_threshold_severe: float = None
    heat_lethal_temperature: float = None
    cold_threshold_mild: float = None
    cold_threshold_severe: float = None
    frost_threshold: float = None  # Must be provided in CSV configuration
    photosynthesis_heat_sensitivity: float = None  # Must be provided in CSV configuration
    photosynthesis_cold_sensitivity: float = None  # Must be provided in CSV configuration
    respiration_heat_sensitivity: float = None  # Must be provided in CSV configuration
    respiration_cold_sensitivity: float = None  # Must be provided in CSV configuration
    growth_heat_sensitivity: float = None  # Must be provided in CSV configuration
    growth_cold_sensitivity: float = None  # Must be provided in CSV configuration
    development_heat_sensitivity: float = None  # Must be provided in CSV configuration
    development_cold_sensitivity: float = None  # Must be provided in CSV configuration
    acclimation_rate: float = None  # Must be provided in CSV configuration
    max_acclimation_days: int = None  # Must be provided in CSV configuration
    acclimation_decay_rate: float = None  # Must be provided in CSV configuration
    heat_damage_threshold: float = None  # Must be provided in CSV configuration
    cold_damage_threshold: float = None  # Must be provided in CSV configuration
    frost_damage_rate: float = None  # Must be provided in CSV configuration
    recovery_rate_heat: float = None  # Must be provided in CSV configuration
    recovery_rate_cold: float = None  # Must be provided in CSV configuration
    stress_memory_duration: int = None  # Must be provided in CSV configuration
    memory_effect_strength: float = None  # Must be provided in CSV configuration

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "TemperatureStressParameters":
        """Create TemperatureStressParameters from CSV configuration data.
        
        Args:
            config: Dictionary containing stress parameters from CSV files
        """
        return cls(
            # Temperature thresholds from CSV
            optimal_temp_min=config["optimal_temp_min"],
            optimal_temp_max=config["optimal_temp_max"],
            heat_threshold_mild=config["heat_threshold_mild"],
            heat_threshold_severe=config["heat_threshold_severe"],
            heat_lethal_temperature=config["heat_lethal_temperature"],
            cold_threshold_mild=config["cold_threshold_mild"],
            cold_threshold_severe=config["cold_threshold_severe"],
            frost_threshold=config["frost_threshold"],
            
            # Process sensitivity parameters from CSV
            photosynthesis_heat_sensitivity=config["photosynthesis_heat_sensitivity"],
            photosynthesis_cold_sensitivity=config["photosynthesis_cold_sensitivity"],
            respiration_heat_sensitivity=config["respiration_heat_sensitivity"],
            respiration_cold_sensitivity=config["respiration_cold_sensitivity"],
            growth_heat_sensitivity=config["growth_heat_sensitivity"],
            growth_cold_sensitivity=config["growth_cold_sensitivity"],
            development_heat_sensitivity=config["development_heat_sensitivity"],
            development_cold_sensitivity=config["development_cold_sensitivity"],
            
            # Acclimation parameters from CSV
            acclimation_rate=config["acclimation_rate"],
            max_acclimation_days=int(config["max_acclimation_days"]),
            acclimation_decay_rate=config["acclimation_decay_rate"],
            
            # Damage and recovery parameters from CSV
            heat_damage_threshold=config["heat_damage_threshold"],
            cold_damage_threshold=config["cold_damage_threshold"],
            frost_damage_rate=config["frost_damage_rate"],
            recovery_rate_heat=config["recovery_rate_heat"],
            recovery_rate_cold=config["recovery_rate_cold"],
            stress_memory_duration=int(config["stress_memory_duration"]),
            memory_effect_strength=config["memory_effect_strength"],
        )


@dataclass
class TemperatureAcclimation:
    heat_acclimation: float = None  # Must be provided in CSV configuration
    cold_acclimation: float = None  # Must be provided in CSV configuration
    acclimation_history: List[float] = None

    def __post_init__(self):
        if self.acclimation_history is None:
            self.acclimation_history = []


@dataclass
class TemperatureDamage:
    heat_damage: float = None  # Must be provided in CSV configuration
    cold_damage: float = None  # Must be provided in CSV configuration
    frost_damage: float = None  # Must be provided in CSV configuration
    damage_recovery_rate: float = None  # Must be provided in CSV configuration


@dataclass
class ProcessStressFactors:
    photosynthesis: float = None  # Must be provided in CSV configuration
    respiration: float = None  # Must be provided in CSV configuration
    growth: float = None  # Must be provided in CSV configuration
    development: float = None  # Must be provided in CSV configuration
    overall: float = None  # Must be provided in CSV configuration


@dataclass
class TemperatureStressResponse:
    stress_type: TemperatureStressType
    stress_level: float
    process_factors: ProcessStressFactors
    acclimation_state: TemperatureAcclimation
    damage_state: TemperatureDamage
    temperature_deviation: float
    stress_duration: float
    memory_effect: float


class TemperatureStressModel:
    def __init__(self, params: TemperatureStressParameters):
        self.params = params
        # Initialize acclimation with valid starting values (0.0 = no acclimation)
        self.acclimation = TemperatureAcclimation(
            heat_acclimation=0.0,  # Start with no heat acclimation
            cold_acclimation=0.0,  # Start with no cold acclimation
            acclimation_history=[]
        )
        # Initialize damage with valid starting values (0.0 = no damage)
        self.damage = TemperatureDamage(
            heat_damage=0.0,      # Start with no heat damage
            cold_damage=0.0,      # Start with no cold damage
            frost_damage=0.0,     # Start with no frost damage
            damage_recovery_rate=0.0  # Start with no recovery rate
        )
        self.stress_history: List[Tuple[float, float]] = []
        self.current_stress_duration = 0.0
        self.last_temperature: Optional[float] = None

    def classify_temperature_stress(self, temperature: float) -> TemperatureStressType:
        temp = float(temperature)  # Ensure temperature is numeric
        if self.params.optimal_temp_min <= temp <= self.params.optimal_temp_max:
            return TemperatureStressType.OPTIMAL
        elif temp < self.params.frost_threshold:
            return TemperatureStressType.FROST
        elif temp < self.params.optimal_temp_min:
            return TemperatureStressType.COLD
        else:
            return TemperatureStressType.HEAT

    def calculate_base_stress_level(self, temperature: float) -> float:
        temp = float(temperature)  # Ensure temperature is numeric
        if self.params.optimal_temp_min <= temp <= self.params.optimal_temp_max:
            return 0.0
        if temp > self.params.optimal_temp_max:
            if temp <= self.params.heat_threshold_mild:
                excess_temp = temp - self.params.optimal_temp_max
                mild_range = self.params.heat_threshold_mild - self.params.optimal_temp_max
                return 0.3 * (excess_temp / mild_range)
            elif temp <= self.params.heat_threshold_severe:
                excess_temp = temp - self.params.heat_threshold_mild
                moderate_range = self.params.heat_threshold_severe - self.params.heat_threshold_mild
                return 0.3 + 0.4 * (excess_temp / moderate_range)
            else:
                excess_temp = temp - self.params.heat_threshold_severe
                severe_range = self.params.heat_lethal_temperature - self.params.heat_threshold_severe
                return 0.7 + 0.3 * min(1.0, excess_temp / severe_range)
        else:
            if temp >= self.params.cold_threshold_mild:
                temp_deficit = self.params.optimal_temp_min - temp
                mild_range = self.params.optimal_temp_min - self.params.cold_threshold_mild
                return 0.2 * (temp_deficit / mild_range)
            elif temp >= self.params.cold_threshold_severe:
                temp_deficit = self.params.cold_threshold_mild - temp
                moderate_range = self.params.cold_threshold_mild - self.params.cold_threshold_severe
                return 0.2 + 0.3 * (temp_deficit / moderate_range)
            elif temp >= self.params.frost_threshold:
                temp_deficit = self.params.cold_threshold_severe - temp
                severe_range = self.params.cold_threshold_severe - self.params.frost_threshold
                return 0.5 + 0.3 * (temp_deficit / severe_range)
            else:
                return 0.8 + 0.2 * min(1.0, abs(temp - self.params.frost_threshold) / 5.0)

    def update_acclimation(self, temperature: float, stress_type: TemperatureStressType):
        self.acclimation.acclimation_history.append(temperature)
        max_history = self.params.max_acclimation_days
        if len(self.acclimation.acclimation_history) > max_history:
            self.acclimation.acclimation_history = self.acclimation.acclimation_history[-max_history:]
        if stress_type == TemperatureStressType.HEAT:
            target = min(
                1.0,
                (temperature - self.params.optimal_temp_max)
                / (self.params.heat_threshold_severe - self.params.optimal_temp_max),
            )
            change = self.params.acclimation_rate * (target - self.acclimation.heat_acclimation)
            self.acclimation.heat_acclimation += change
            self.acclimation.cold_acclimation *= 1.0 - self.params.acclimation_decay_rate
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            target = min(
                1.0,
                (self.params.optimal_temp_min - temperature)
                / (self.params.optimal_temp_min - self.params.cold_threshold_severe),
            )
            change = self.params.acclimation_rate * (target - self.acclimation.cold_acclimation)
            self.acclimation.cold_acclimation += change
            self.acclimation.heat_acclimation *= 1.0 - self.params.acclimation_decay_rate
        else:
            self.acclimation.heat_acclimation *= 1.0 - self.params.acclimation_decay_rate
            self.acclimation.cold_acclimation *= 1.0 - self.params.acclimation_decay_rate
        self.acclimation.heat_acclimation = max(0.0, min(1.0, self.acclimation.heat_acclimation))
        self.acclimation.cold_acclimation = max(0.0, min(1.0, self.acclimation.cold_acclimation))

    def apply_acclimation_effects(self, base_stress: float, stress_type: TemperatureStressType) -> float:
        if stress_type == TemperatureStressType.HEAT:
            return base_stress * (1.0 - self.acclimation.heat_acclimation * 0.4)
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            return base_stress * (1.0 - self.acclimation.cold_acclimation * 0.5)
        return base_stress

    def calculate_memory_effects(self) -> float:
        if not self.stress_history:
            return 0.0
        recent = self.stress_history[-self.params.stress_memory_duration :]
        if not recent:
            return 0.0
        total_w = 0.0
        weighted = 0.0
        for i, (level, _) in enumerate(recent):
            w = (i + 1) / len(recent)
            weighted += level * w
            total_w += w
        return (weighted / total_w) * self.params.memory_effect_strength if total_w else 0.0

    def calculate_process_stress_factors(self, stress_level: float, stress_type: TemperatureStressType) -> ProcessStressFactors:
        f = ProcessStressFactors()
        
        # Initialize all fields with default values (no stress = 1.0)
        f.photosynthesis = 1.0
        f.respiration = 1.0
        f.growth = 1.0
        f.development = 1.0
        
        if stress_type == TemperatureStressType.HEAT:
            f.photosynthesis = max(0.0, 1.0 - stress_level * self.params.photosynthesis_heat_sensitivity)
            f.respiration = max(0.0, 1.0 - stress_level * self.params.respiration_heat_sensitivity)
            f.growth = max(0.0, 1.0 - stress_level * self.params.growth_heat_sensitivity)
            f.development = max(0.0, 1.0 - stress_level * self.params.development_heat_sensitivity)
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            f.photosynthesis = max(0.0, 1.0 - stress_level * self.params.photosynthesis_cold_sensitivity)
            f.respiration = max(0.0, 1.0 - stress_level * self.params.respiration_cold_sensitivity)
            f.growth = max(0.0, 1.0 - stress_level * self.params.growth_cold_sensitivity)
            f.development = max(0.0, 1.0 - stress_level * self.params.development_cold_sensitivity)
        
        # Calculate overall factor (weighted average)
        f.overall = (
            f.photosynthesis * 0.35 + f.growth * 0.35 + f.development * 0.20 + f.respiration * 0.10
        )
        return f

    def update_damage_and_recovery(self, stress_level: float, stress_type: TemperatureStressType, duration_hours: float = 24.0):
        if stress_type == TemperatureStressType.HEAT and stress_level > self.params.heat_damage_threshold:
            damage_rate = (stress_level - self.params.heat_damage_threshold) * 0.01
            self.damage.heat_damage = min(1.0, self.damage.heat_damage + damage_rate)
            self.damage.damage_recovery_rate = self.params.recovery_rate_heat
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            if stress_type == TemperatureStressType.FROST:
                self.damage.frost_damage = min(1.0, self.damage.frost_damage + self.params.frost_damage_rate / 24.0)
            if stress_level > self.params.cold_damage_threshold:
                damage_rate = (stress_level - self.params.cold_damage_threshold) * 0.008
                self.damage.cold_damage = min(1.0, self.damage.cold_damage + damage_rate)
                self.damage.damage_recovery_rate = self.params.recovery_rate_cold
        else:
            # FIX: Scale recovery rates by time step duration
            time_scale = duration_hours / 24.0  # Convert to daily fraction
            
            if self.damage.heat_damage > 0:
                recovery_amount = self.params.recovery_rate_heat * time_scale
                self.damage.heat_damage = max(0.0, self.damage.heat_damage - recovery_amount)
            if self.damage.cold_damage > 0:
                recovery_amount = self.params.recovery_rate_cold * time_scale
                self.damage.cold_damage = max(0.0, self.damage.cold_damage - recovery_amount)
            if self.damage.frost_damage > 0:
                recovery_amount = self.params.recovery_rate_cold * 0.5 * time_scale
                self.damage.frost_damage = max(0.0, self.damage.frost_damage - recovery_amount)

    def daily_update(self, temperature: float, duration_hours: float = 24.0) -> TemperatureStressResponse:
        stress_type = self.classify_temperature_stress(temperature)
        base_stress = self.calculate_base_stress_level(temperature)
        self.update_acclimation(temperature, stress_type)
        adjusted_stress = self.apply_acclimation_effects(base_stress, stress_type)
        memory_effect = self.calculate_memory_effects()
        final_stress = min(1.0, adjusted_stress + memory_effect)

        if self.last_temperature is not None and abs(temperature - self.last_temperature) < 2.0:
            self.current_stress_duration += duration_hours
        else:
            self.current_stress_duration = duration_hours

        process_factors = self.calculate_process_stress_factors(final_stress, stress_type)
        total_damage = max(self.damage.heat_damage, self.damage.cold_damage, self.damage.frost_damage)
        if total_damage > 0:
            damage_factor = 1.0 - total_damage * 0.5
            process_factors.photosynthesis *= damage_factor
            process_factors.growth *= damage_factor
            process_factors.development *= damage_factor
            process_factors.overall *= damage_factor

        self.update_damage_and_recovery(final_stress, stress_type, duration_hours)
        self.stress_history.append((final_stress, temperature))
        if len(self.stress_history) > self.params.stress_memory_duration:
            self.stress_history = self.stress_history[-self.params.stress_memory_duration :]

        if stress_type == TemperatureStressType.HEAT:
            temp_dev = temperature - self.params.optimal_temp_max
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            temp_dev = self.params.optimal_temp_min - temperature
        else:
            temp_dev = 0.0
        self.last_temperature = temperature

        return TemperatureStressResponse(
            stress_type=stress_type,
            stress_level=final_stress,
            process_factors=process_factors,
            acclimation_state=self.acclimation,
            damage_state=self.damage,
            temperature_deviation=temp_dev,
            stress_duration=self.current_stress_duration,
            memory_effect=memory_effect,
        )


def create_lettuce_temperature_stress_model(system_config=None) -> TemperatureStressModel:
    """Create a temperature stress model using CSV configuration data.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        TemperatureStressModel configured with CSV parameters
    """
    try:
        # Get stress parameters from CSV data loaded in system_config
        stress_params = getattr(system_config, 'stress_parameters', {})
        environment_params = getattr(system_config, 'environment_parameters', {})
        thermal_params = getattr(system_config, 'thermal_requirements', {})
        
        # Combine parameters from different CSV files
        config = {}
        
        # Add stress parameters
        config.update(stress_params)
        
        # Add environment parameters that affect temperature stress
        if 'optimal_temperature_min' in environment_params:
            config['optimal_temp_min'] = environment_params['optimal_temperature_min']
        if 'optimal_temperature_max' in environment_params:
            config['optimal_temp_max'] = environment_params['optimal_temperature_max']
            
        # Add thermal requirements if available
        config.update(thermal_params)
        
        # Create parameters from combined config
        params = TemperatureStressParameters.from_config(config)
        return TemperatureStressModel(params)
        
    except Exception as e:
        raise ValueError(f"❌ Failed to load temperature stress parameters from CSV: {e}. No hardcoded defaults allowed.")


# =========================
# Integrated Stress Model
# =========================


class StressType(Enum):
    WATER = "water"
    TEMPERATURE = "temperature"
    NUTRIENT = "nutrient"
    LIGHT = "light"
    SALINITY = "salinity"
    OXYGEN = "oxygen"
    PH = "ph"
    MECHANICAL = "mechanical"
    PATHOGEN = "pathogen"


class StressInteractionType(Enum):
    MULTIPLICATIVE = "multiplicative"
    ADDITIVE = "additive"
    SYNERGISTIC = "synergistic"
    ANTAGONISTIC = "antagonistic"
    THRESHOLD = "threshold"


class ProcessType(Enum):
    PHOTOSYNTHESIS = "photosynthesis"
    RESPIRATION = "respiration"
    TRANSPIRATION = "transpiration"
    GROWTH = "growth"
    DEVELOPMENT = "development"
    NUTRIENT_UPTAKE = "nutrient_uptake"
    SENESCENCE = "senescence"
    FLOWERING = "flowering"


@dataclass
class IntegratedStressParameters:
    stress_weights: Dict[str, float] = None
    stress_interactions: Dict[str, Dict[str, Dict[str, float]]] = None
    process_sensitivity: Dict[str, Dict[str, float]] = None
    stress_memory_duration: Dict[str, float] = None
    cumulative_threshold: Dict[str, float] = None
    damage_accumulation_rate: Dict[str, float] = None
    recovery_rates: Dict[str, float] = None
    recovery_thresholds: Dict[str, float] = None
    full_recovery_time: Dict[str, float] = None
    acclimation_rates: Dict[str, float] = None
    acclimation_capacity: Dict[str, float] = None
    acclimation_memory: Dict[str, float] = None
    stress_onset_thresholds: Dict[str, float] = None
    damage_thresholds: Dict[str, float] = None

    def __post_init__(self):
        # Generate missing parameters from available CSV data where possible
        if self.stress_weights is None:
            raise ValueError("❌ stress_weights must be provided from CSV - no hardcoded defaults allowed")
        
        # Generate reasonable stress interactions if not provided
        if self.stress_interactions is None:
            self.stress_interactions = self._generate_default_interactions()
        
        # Generate process sensitivity if not provided  
        if self.process_sensitivity is None:
            self.process_sensitivity = self._generate_default_process_sensitivity()
            
        # Generate other missing parameters with reasonable defaults based on stress weights
        if self.stress_memory_duration is None:
            self.stress_memory_duration = self._generate_memory_duration()
        if self.recovery_rates is None:
            self.recovery_rates = self._generate_recovery_rates()
        if self.acclimation_rates is None:
            self.acclimation_rates = self._generate_acclimation_rates()
        if self.stress_onset_thresholds is None:
            self.stress_onset_thresholds = self._generate_onset_thresholds()
        if self.damage_thresholds is None:
            self.damage_thresholds = self._generate_damage_thresholds()
    
    def _generate_default_interactions(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Generate reasonable stress interactions based on biological principles."""
        return {
            StressType.WATER.value: {
                StressType.TEMPERATURE.value: {"type": "synergistic", "factor": 1.3},
                StressType.SALINITY.value: {"type": "synergistic", "factor": 1.4},
                StressType.NUTRIENT.value: {"type": "multiplicative", "factor": 1.2},
            },
            StressType.TEMPERATURE.value: {
                StressType.WATER.value: {"type": "synergistic", "factor": 1.3},
                StressType.LIGHT.value: {"type": "additive", "factor": 1.1},
            },
            StressType.NUTRIENT.value: {
                StressType.WATER.value: {"type": "multiplicative", "factor": 1.2},
                StressType.PH.value: {"type": "synergistic", "factor": 1.5},
                StressType.SALINITY.value: {"type": "multiplicative", "factor": 1.1},
            },
        }
    
    def _generate_default_process_sensitivity(self) -> Dict[str, Dict[str, float]]:
        """Generate process sensitivity based on stress weights."""
        return {
            ProcessType.PHOTOSYNTHESIS.value: {st: 0.8 for st in self.stress_weights.keys()},
            ProcessType.GROWTH.value: {st: 0.7 for st in self.stress_weights.keys()},
            ProcessType.NUTRIENT_UPTAKE.value: {st: 0.6 for st in self.stress_weights.keys()},
        }
    
    def _generate_memory_duration(self) -> Dict[str, float]:
        """Generate memory duration inversely related to stress weights."""
        return {st: 5.0 / max(0.1, weight) for st, weight in self.stress_weights.items()}
    
    def _generate_recovery_rates(self) -> Dict[str, float]:
        """Generate recovery rates inversely related to stress weights."""
        return {st: 0.3 / max(0.1, weight) for st, weight in self.stress_weights.items()}
    
    def _generate_acclimation_rates(self) -> Dict[str, float]:
        """Generate acclimation rates based on stress weights."""
        return {st: 0.1 * weight for st, weight in self.stress_weights.items()}
    
    def _generate_onset_thresholds(self) -> Dict[str, float]:
        """Generate onset thresholds based on stress sensitivity."""
        return {st: 0.8 - (weight * 0.2) for st, weight in self.stress_weights.items()}
    
    def _generate_damage_thresholds(self) -> Dict[str, float]:
        """Generate damage thresholds based on stress weights."""
        return {st: 0.4 - (weight * 0.1) for st, weight in self.stress_weights.items()}

    @classmethod
    def from_config(cls, config_dict: dict) -> "IntegratedStressParameters":
        """Create IntegratedStressParameters from CSV configuration data.
        
        Args:
            config_dict: Dictionary containing stress parameters from CSV files
        """
        # Extract stress weights from CSV data using scientific literature values
        stress_weights = {}
        if "stress_weight_water" in config_dict:
            stress_weights = {
                StressType.WATER.value: config_dict["stress_weight_water"],
                StressType.TEMPERATURE.value: config_dict["stress_weight_temperature"],
                StressType.NUTRIENT.value: config_dict["stress_weight_nutrient"],
                StressType.LIGHT.value: config_dict["stress_weight_light"],
                StressType.SALINITY.value: config_dict["stress_weight_salinity"],
                StressType.OXYGEN.value: config_dict["stress_weight_oxygen"],
                StressType.PH.value: config_dict["stress_weight_ph"],
            }
        
        # Extract stress interactions from CSV data using scientific literature values
        stress_interactions = {}
        if "water_temp_interaction_factor" in config_dict:
            stress_interactions = {
                StressType.WATER.value: {
                    StressType.TEMPERATURE.value: {"type": "synergistic", "factor": config_dict["water_temp_interaction_factor"]},
                    StressType.SALINITY.value: {"type": "synergistic", "factor": config_dict["water_salinity_interaction_factor"]},
                    StressType.NUTRIENT.value: {"type": "multiplicative", "factor": config_dict["water_nutrient_interaction_factor"]},
                },
                StressType.TEMPERATURE.value: {
                    StressType.WATER.value: {"type": "synergistic", "factor": config_dict["water_temp_interaction_factor"]},
                    StressType.LIGHT.value: {"type": "additive", "factor": config_dict["temp_light_interaction_factor"]},
                },
                StressType.NUTRIENT.value: {
                    StressType.WATER.value: {"type": "multiplicative", "factor": config_dict["water_nutrient_interaction_factor"]},
                    StressType.PH.value: {"type": "synergistic", "factor": config_dict["nutrient_ph_interaction_factor"]},
                    StressType.SALINITY.value: {"type": "multiplicative", "factor": config_dict["nutrient_salinity_interaction_factor"]},
                },
            }
        
        process_sensitivity = config_dict.get("process_sensitivity", {})
        memory_duration = config_dict.get("stress_memory_duration", {})
        
        # Convert single stress_memory_duration value to dictionary if needed
        if isinstance(memory_duration, (int, float)):
            memory_duration = {
                StressType.WATER.value: float(memory_duration),
                StressType.TEMPERATURE.value: float(memory_duration),
                StressType.NUTRIENT.value: float(memory_duration),
                StressType.LIGHT.value: float(memory_duration),
                StressType.SALINITY.value: float(memory_duration),
                StressType.OXYGEN.value: float(memory_duration),
                StressType.PH.value: float(memory_duration),
            }
        
        recovery_rates = config_dict.get("recovery_rates", {})
        acclimation_rates = config_dict.get("acclimation_rates", {})
        onset_thresholds = config_dict.get("stress_onset_thresholds", {})
        damage_thresholds = config_dict.get("damage_thresholds", {})
        
        # Stress weights must be provided in CSV configuration
        if not stress_weights:
            raise ValueError("Stress weights must be provided in CSV configuration")
        
        return cls(
            stress_weights=stress_weights or None,
            stress_interactions=stress_interactions or None,
            process_sensitivity=process_sensitivity or None,
            stress_memory_duration=memory_duration or None,
            recovery_rates=recovery_rates or None,
            acclimation_rates=acclimation_rates or None,
            stress_onset_thresholds=onset_thresholds or None,
            damage_thresholds=damage_thresholds or None,
        )


@dataclass
class StressState:
    stress_type: str
    current_level: float
    acute_stress: float = None  # Must be provided in CSV configuration
    chronic_stress: float = None  # Must be provided in CSV configuration
    acclimation_level: float = None  # Must be provided in CSV configuration
    damage_level: float = None  # Must be provided in CSV configuration
    recovery_progress: float = None  # Must be provided in CSV configuration
    days_under_stress: int = 0
    stress_history: List[float] = None

    def __post_init__(self):
        if self.stress_history is None:
            self.stress_history = []


@dataclass
class StressResponse:
    process_type: str
    individual_stress_effects: Dict[str, float]
    combined_stress_factor: float
    interaction_effects: Dict[str, float]
    acclimation_benefits: Dict[str, float]
    recovery_effects: Dict[str, float]
    damage_effects: Dict[str, float]
    limiting_stress_types: List[str]


@dataclass
class IntegratedStressResponse:
    stress_states: Dict[str, StressState]
    process_responses: Dict[str, StressResponse]
    overall_stress_factor: float
    stress_severity: str
    dominant_stresses: List[str]
    stress_interactions_active: List[str]
    acclimation_active: List[str]
    recovery_active: List[str]


class IntegratedStressModel:
    def __init__(self, parameters: Optional[IntegratedStressParameters] = None):
        if parameters is None:
            raise ValueError("❌ IntegratedStressParameters required - no hardcoded defaults allowed")
        self.params = parameters
        self.stress_states: Dict[str, StressState] = {}
        self.stress_history: List[Dict[str, Any]] = []
        self.cumulative_damage: Dict[str, float] = {}
        for st in self.params.stress_weights.keys():
            # Initialize stress state with valid starting values
            self.stress_states[st] = StressState(
                stress_type=st,
                current_level=1.0,  # Start with no stress
                acute_stress=0.0,   # Start with no acute stress
                chronic_stress=0.0, # Start with no chronic stress
                acclimation_level=0.0, # Start with no acclimation
                damage_level=0.0,   # Start with no damage
                recovery_progress=0.0, # Start with no recovery
                days_under_stress=0,
                stress_history=[]
            )
            self.cumulative_damage[st] = 0.0

    def calculate_acute_stress(self, stress_type: str, current_level: float) -> float:
        """Calculate acute stress factor from current stress level.
        
        Args:
            stress_type: Type of stress (water, temperature, etc.)
            current_level: Current stress level (0.0 = no stress, 1.0 = maximum stress)
            
        Returns:
            Acute stress factor (0.0 = no stress, 1.0 = maximum stress)
        """
        threshold = self.params.stress_onset_thresholds.get(stress_type, 0.8)
        
        # If stress level is above threshold, return the stress level directly
        if current_level >= threshold:
            return current_level
        
        # For stress levels below threshold, apply non-linear scaling
        if current_level < 0.5:
            # Quadratic scaling for low stress levels
            stress_factor = (current_level / 0.5) ** 2
        else:
            # Linear scaling for moderate stress levels
            stress_factor = current_level
        
        return max(0.0, min(1.0, stress_factor))

    def calculate_chronic_stress(self, stress_state: StressState) -> float:
        if not stress_state.stress_history:
            return 1.0
        st_type = stress_state.stress_type
        memory_d = self.params.stress_memory_duration.get(st_type, 5.0)
        recent = stress_state.stress_history[-int(memory_d) :]
        if not recent:
            return 1.0
        weights = np.exp(-np.arange(len(recent)) / (memory_d / 3))[::-1]
        weighted = np.average(recent, weights=weights)
        if stress_state.days_under_stress > memory_d:
            chronic_factor = 1.0 - (1.0 - weighted) * 1.5
        else:
            chronic_factor = weighted
        return max(0.1, min(1.0, chronic_factor))

    def calculate_acclimation_effect(self, stress_state: StressState) -> float:
        if stress_state.days_under_stress < 3:
            return 0.0
        rate = self.params.acclimation_rates.get(stress_state.stress_type, 0.1)
        max_acc = 0.3
        potential = min(max_acc, stress_state.days_under_stress * rate)
        severity = 1.0 - stress_state.current_level
        eff = max(0.2, 1.0 - severity)
        return potential * eff

    def calculate_recovery_effect(self, stress_state: StressState) -> float:
        if stress_state.current_level < 0.8:
            return 0.0
        rate = self.params.recovery_rates.get(stress_state.stress_type, 0.2)
        if stress_state.chronic_stress > 0.7:
            daily = rate
        elif stress_state.chronic_stress > 0.4:
            daily = rate * 0.7
        else:
            daily = rate * 0.3
        return min(1.0, stress_state.recovery_progress + daily)

    def calculate_stress_interactions(self, active_stresses: Dict[str, float]) -> Dict[str, float]:
        effects: Dict[str, float] = {}
        types = list(active_stresses.keys())
        for i, s1 in enumerate(types):
            for s2 in types[i + 1 :]:
                if s1 in self.params.stress_interactions and s2 in self.params.stress_interactions[s1]:
                    interaction = self.params.stress_interactions[s1][s2]
                    t = interaction["type"]
                    factor = interaction["factor"]
                    l1 = 1.0 - active_stresses[s1]
                    l2 = 1.0 - active_stresses[s2]
                    if t == "multiplicative":
                        combined = l1 * l2 * factor
                    elif t in ("synergistic", "additive"):
                        combined = (l1 + l2) * factor
                    else:
                        combined = max(l1, l2) * factor
                    effects[f"{s1}_{s2}"] = min(1.0, combined)
        return effects

    def calculate_process_stress_response(self, process_type: str, stress_states: Dict[str, StressState]) -> StressResponse:
        indiv: Dict[str, float] = {}
        accl_benefits: Dict[str, float] = {}
        recov: Dict[str, float] = {}
        dmg: Dict[str, float] = {}
        sensitivities = self.params.process_sensitivity.get(process_type, {})
        active: Dict[str, float] = {}
        for st, state in stress_states.items():
            sensitivity = sensitivities.get(st, None)
            if sensitivity is None:
                raise ValueError(f"Process sensitivity for {st} must be provided in CSV configuration")
            acute = state.acute_stress
            chronic = state.chronic_stress
            combined = min(acute, chronic * 0.8 + acute * 0.2)
            proc_stress = 1.0 - ((1.0 - combined) * sensitivity)
            indiv[st] = proc_stress
            if proc_stress < 0.9:
                active[st] = proc_stress
            accl_benefits[st] = state.acclimation_level * 0.3
            recov[st] = state.recovery_progress
            dmg[st] = self.cumulative_damage.get(st, 0.0)
        interactions = self.calculate_stress_interactions(active)
        if not indiv:
            combined_factor = 1.0
        else:
            base = min(indiv.values())
            interaction_penalty = sum(interactions.values()) * 0.1
            accl_bonus = sum(accl_benefits.values()) * 0.1
            recov_bonus = sum(recov.values()) * 0.05
            dmg_penalty = sum(dmg.values()) * 0.2
            combined_factor = max(0.1, min(1.0, base - interaction_penalty + accl_bonus + recov_bonus - dmg_penalty))
        limiting = [s for s, val in indiv.items() if val < 0.8]
        limiting.sort(key=lambda x: indiv[x])
        return StressResponse(
            process_type=process_type,
            individual_stress_effects=indiv,
            combined_stress_factor=combined_factor,
            interaction_effects=interactions,
            acclimation_benefits=accl_benefits,
            recovery_effects=recov,
            damage_effects=dmg,
            limiting_stress_types=limiting[:3],
        )

    def update_stress_states(self, current_stress_levels: Dict[str, float]):
        for st_type, level in current_stress_levels.items():
            if st_type in self.stress_states:
                state = self.stress_states[st_type]
                state.current_level = level
                state.stress_history.append(level)
                memory = self.params.stress_memory_duration.get(st_type, None)
                if memory is None:
                    raise ValueError(f"Stress memory duration for {st_type} must be provided in CSV configuration")
                if len(state.stress_history) > memory:
                    state.stress_history = state.stress_history[-int(memory) :]
                threshold = self.params.stress_onset_thresholds.get(st_type, None)
                if threshold is None:
                    raise ValueError(f"Stress onset threshold for {st_type} must be provided in CSV configuration")
                if level < threshold:
                    state.days_under_stress += 1
                else:
                    state.days_under_stress = max(0, state.days_under_stress - 1)
                state.acute_stress = self.calculate_acute_stress(st_type, level)
                state.chronic_stress = self.calculate_chronic_stress(state)
                state.acclimation_level = self.calculate_acclimation_effect(state)
                state.recovery_progress = self.calculate_recovery_effect(state)
                damage_threshold = self.params.damage_thresholds.get(st_type, None)
                if damage_threshold is None:
                    raise ValueError(f"Damage threshold for {st_type} must be provided in CSV configuration")
                if level < damage_threshold:
                    rate = (damage_threshold - level) / damage_threshold * 0.01
                    self.cumulative_damage[st_type] += rate
                    self.cumulative_damage[st_type] = min(0.5, self.cumulative_damage[st_type])
                state.damage_level = self.cumulative_damage[st_type]

    def daily_update(self, current_stress_levels: Dict[str, float]) -> IntegratedStressResponse:
        self.update_stress_states(current_stress_levels)
        process_responses: Dict[str, StressResponse] = {}
        for proc in self.params.process_sensitivity.keys():
            process_responses[proc] = self.calculate_process_stress_response(proc, self.stress_states)
        if process_responses:
            overall = float(np.mean([r.combined_stress_factor for r in process_responses.values()]))
        else:
            overall = 1.0
        if overall > 0.8:
            severity = "mild"
        elif overall > 0.6:
            severity = "moderate"
        elif overall > 0.3:
            severity = "severe"
        else:
            severity = "critical"
        impacts: Dict[str, float] = {}
        for st, state in self.stress_states.items():
            impacts[st] = state.acute_stress * self.params.stress_weights.get(st, None)
            if self.params.stress_weights.get(st, None) is None:
                raise ValueError(f"Stress weight for {st} must be provided in CSV configuration")
        dominant = sorted(impacts.keys(), key=lambda x: impacts[x], reverse=True)[:3]
        interactions_active: List[str] = []
        for resp in process_responses.values():
            interactions_active.extend(resp.interaction_effects.keys())
        interactions_active = list(set(interactions_active))
        accl_active = [st for st, s in self.stress_states.items() if s.acclimation_level > 0.1]
        recov_active = [st for st, s in self.stress_states.items() if s.recovery_progress > 0.1]
        self.stress_history.append(
            {
                "overall_stress_factor": overall,
                "severity": severity,
                "dominant_stresses": dominant,
                "active_interactions": len(interactions_active),
            }
        )
        return IntegratedStressResponse(
            stress_states=self.stress_states.copy(),
            process_responses=process_responses,
            overall_stress_factor=overall,
            stress_severity=severity,
            dominant_stresses=dominant,
            stress_interactions_active=interactions_active,
            acclimation_active=accl_active,
            recovery_active=recov_active,
        )

    def get_stress_summary(self) -> Dict[str, Any]:
        current: Dict[str, Any] = {}
        accl_status: Dict[str, float] = {}
        total_damage = 0.0
        for st, state in self.stress_states.items():
            current[st] = {
                "current_level": state.current_level,
                "acute_stress": state.acute_stress,
                "chronic_stress": state.chronic_stress,
                "days_under_stress": state.days_under_stress,
            }
            accl_status[st] = state.acclimation_level
            total_damage += self.cumulative_damage.get(st, 0.0)
        return {
            "current_stresses": current,
            "acclimation_status": accl_status,
            "cumulative_damage": self.cumulative_damage.copy(),
            "total_damage": total_damage,
            "stress_history_length": len(self.stress_history),
        }


def create_lettuce_integrated_stress_model(system_config=None) -> IntegratedStressModel:
    """Create an integrated stress model using CSV configuration data.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        IntegratedStressModel configured with CSV parameters
    """
    try:
        # Get parameters from CSV data loaded in system_config
        stress_params = getattr(system_config, 'stress_parameters', {})
        genetic_stress_weights = getattr(system_config, 'genetic_stress_weights', {})
        environment_params = getattr(system_config, 'environment_parameters', {})
        
        # Combine parameters from different CSV files
        config = {}
        
        # Add stress parameters
        config.update(stress_params)
        
        # Add genetic stress weights
        config['genetic_stress_weights'] = genetic_stress_weights
        
        # Add environment parameters that affect stress
        config.update(environment_params)
        
        # Create parameters from combined config
        parameters = IntegratedStressParameters.from_config(config)
        return IntegratedStressModel(parameters)
        
    except Exception as e:
        raise ValueError(f"❌ Failed to load integrated stress parameters from CSV: {e}. No hardcoded defaults allowed.")


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file models plant stress - how plants respond to unfavorable environmental conditions. 
Think of it as modeling the plant's "stress response system" like how humans react to different 
types of stress (physical, emotional, environmental). Plants have sophisticated mechanisms to 
detect, respond to, and adapt to stressful conditions.

SECTION 1: TEMPERATURE STRESS MODEL

Temperature stress affects plants like extreme weather affects humans - too hot or cold causes 
immediate discomfort and long-term damage if sustained.

KEY FUNCTIONS AND EQUATIONS:

1. classify_temperature_stress()
   - What it does: Categorizes temperature into stress types
   - Categories: optimal, heat, cold, frost
   - Thresholds: Based on plant-specific temperature ranges
   - Real-world meaning: Like categorizing weather as comfortable, hot, chilly, or freezing. 
     Each category affects the plant differently.

2. calculate_base_stress_level()
   - What it does: Calculates stress intensity based on temperature deviation from optimal
   - Equation: Linear scaling in zones (mild: 0-0.3, moderate: 0.3-0.7, severe: 0.7-1.0)
   - Heat stress: temp > optimal_max triggers increasing stress
   - Cold stress: temp < optimal_min triggers increasing stress
   - Real-world meaning: Like measuring discomfort level - slightly warm is minor stress, 
     sweltering heat is major stress.

3. update_acclimation()
   - What it does: Models plant adaptation to repeated stress exposure
   - Equation: acclimation += rate × (target - current_acclimation)
   - Heat acclimation: Plants develop heat tolerance over days/weeks
   - Cold acclimation: Plants develop frost tolerance (hardening)
   - Real-world meaning: Like how people adapt to climate when moving to new locations. 
     Gradual exposure builds tolerance.

4. apply_acclimation_effects()
   - What it does: Reduces stress impact based on acclimation level
   - Equation: adjusted_stress = base_stress × (1 - acclimation × effectiveness)
   - Heat acclimation: 40% stress reduction when fully acclimated
   - Cold acclimation: 50% stress reduction when fully acclimated
   - Real-world meaning: Like how athletes perform better in conditions they've trained in. 
     Adapted plants handle stress better.

5. calculate_process_stress_factors()
   - What it does: Determines how stress affects different plant functions
   - Processes affected: photosynthesis, growth, development, respiration
   - Equation: process_factor = max(0, 1 - stress_level × sensitivity)
   - Real-world meaning: Like how stress affects different human abilities differently. 
     Heat might affect thinking more than physical strength.

6. update_damage_and_recovery()
   - What it does: Tracks permanent damage and healing over time
   - Damage accumulation: Severe stress causes lasting damage
   - Recovery: Plants heal gradually under good conditions
   - Real-world meaning: Like how injuries heal over time, but severe trauma may leave 
     permanent effects. Plants can recover from mild stress but not severe damage.

SECTION 2: INTEGRATED STRESS MODEL

This models how multiple stresses interact - like dealing with multiple problems at once, 
which is usually worse than dealing with each separately.

KEY FUNCTIONS AND EQUATIONS:

7. calculate_acute_stress()
   - What it does: Measures immediate stress response
   - Threshold-based: Stress below threshold is scaled non-linearly
   - Equation: For stress < 0.5: factor = (stress/0.5)², above 0.5: linear
   - Real-world meaning: Like immediate pain response - minor discomfort barely registers, 
     but severe pain demands immediate attention.

8. calculate_chronic_stress()
   - What it does: Measures long-term stress effects using weighted history
   - Equation: weighted_average with exponential decay (recent stress weighted more)
   - Memory effect: Recent stress has more impact than old stress
   - Real-world meaning: Like chronic health conditions - ongoing stress accumulates and 
     has lasting effects even when current conditions improve.

9. calculate_acclimation_effect()
   - What it does: Models adaptation to sustained stress over 3+ days
   - Rate-based: Gradual increase in tolerance with exposure time
   - Effectiveness: Depends on stress severity (can't adapt to extreme stress)
   - Real-world meaning: Like building calluses from manual labor - repeated exposure 
     builds tolerance, but there are limits.

10. calculate_stress_interactions()
    - What it does: Models how different stresses combine (usually making each other worse)
    - Interaction types:
      * Multiplicative: stresses multiply each other's effects
      * Synergistic: stresses amplify each other beyond multiplication
      * Additive: stresses simply add together
    - Examples: drought + heat = much worse than either alone
    - Real-world meaning: Like how being sick and tired makes everything worse than 
      either condition alone. Multiple problems compound each other.

11. calculate_process_stress_response()
    - What it does: Determines how combined stresses affect specific plant processes
    - Combines: individual stress effects + interactions + acclimation + damage
    - Process sensitivity: Different processes have different stress tolerance
    - Real-world meaning: Like how different skills are affected differently by stress - 
      some people lose creativity first, others lose physical coordination.

STRESS TYPES AND EFFECTS:

Water Stress:
- Drought: Reduced water availability, triggers wilting and leaf drop
- Flooding: Root suffocation, nutrient washout
- Interactive effects: Makes temperature stress much worse
- Biological response: Stomatal closure, root growth toward water

Temperature Stress:
- Heat: Protein denaturation, enzyme dysfunction, increased respiration
- Cold: Membrane damage, reduced enzyme activity, ice crystal formation
- Frost: Cell rupture from ice crystals, tissue death
- Acclimation: Heat shock proteins, membrane composition changes

Nutrient Stress:
- Deficiency: Reduced growth, chlorosis, specific symptoms per nutrient
- Toxicity: Ion imbalance, pH changes, metabolic disruption
- Interactive effects: pH affects nutrient availability

Light Stress:
- Low light: Reduced photosynthesis, etiolation, competition responses
- High light: Photoinhibition, free radical damage, heat buildup
- Photoperiod: Day length affects flowering and development

Salinity Stress:
- Osmotic effect: Water uptake difficulty, cellular dehydration
- Ionic effect: Sodium/chloride toxicity, nutrient imbalances
- Interactive effects: Compounds water stress effects

pH Stress:
- Acidic: Aluminum toxicity, phosphorus deficiency
- Alkaline: Iron deficiency, micronutrient lockout
- Buffer system: Plants try to maintain internal pH

Oxygen Stress:
- Hypoxia: Root suffocation, anaerobic respiration, root rot
- Critical in hydroponics: Dissolved oxygen must stay above 3-4 mg/L
- Root zone aeration essential for healthy plants

STRESS RESPONSE MECHANISMS:

Immediate Responses (minutes to hours):
- Stomatal closure to conserve water
- Osmotic adjustment (accumulating sugars/salts)
- Heat shock protein production
- Antioxidant enzyme activation

Short-term Responses (hours to days):
- Growth rate adjustment
- Resource reallocation
- Leaf angle changes (heat avoidance)
- Root growth toward resources

Long-term Responses (days to weeks):
- Morphological changes (smaller leaves, deeper roots)
- Biochemical acclimation (membrane composition)
- Developmental changes (early flowering)
- Epigenetic modifications

ACCLIMATION VS ADAPTATION:

Acclimation (Individual Response):
- Physiological adjustments during plant's lifetime
- Reversible changes based on environment
- Examples: heat tolerance, cold hardiness, drought tolerance
- Like learning to work in different conditions

Adaptation (Population Response):
- Genetic changes over generations
- Irreversible improvements in stress tolerance
- Natural selection favors stress-resistant individuals
- Like evolution of desert plants

STRESS MEMORY AND PRIMING:

Stress Memory:
- Plants "remember" previous stress exposure
- Faster/stronger response to repeated stress
- Molecular basis: epigenetic marks, protein modifications
- Duration: typically days to weeks

Stress Priming:
- Mild stress prepares plants for severe stress
- Cross-protection: one stress type can protect against another
- Practical application: controlled stress to improve tolerance
- Like vaccination - small exposure prevents severe damage

PRACTICAL APPLICATIONS:

For Hydroponic Growers:
1. **Environmental Monitoring**: Track all stress factors continuously
2. **Stress Prevention**: Maintain optimal ranges for all parameters
3. **Gradual Acclimation**: Slowly adjust conditions rather than sudden changes
4. **Multi-stress Awareness**: Address combinations of stresses, not just individual ones
5. **Recovery Time**: Allow plants time to recover between stress events
6. **Early Detection**: Monitor for early stress symptoms before damage occurs

For System Design:
1. **Redundant Systems**: Backup systems for critical environmental controls
2. **Buffer Capacity**: Design systems to handle environmental fluctuations
3. **Sensor Integration**: Monitor multiple stress factors simultaneously
4. **Alarm Systems**: Alert for stress conditions before damage occurs
5. **Automated Response**: Systems that automatically adjust to prevent stress
6. **Recovery Protocols**: Procedures for helping plants recover from stress

STRESS INTERACTION EXAMPLES:

Drought + Heat (Synergistic):
- Combined effect worse than sum of parts
- Water shortage + high temperature = rapid plant death
- Prevention: Extra water during heat waves

Cold + Wet (Multiplicative):
- Cold reduces root function, excess water causes root rot
- Common in winter hydroponic systems
- Prevention: Reduce watering frequency in cold conditions

Nutrient Deficiency + pH Imbalance (Synergistic):
- Wrong pH makes nutrient deficiency worse
- Nutrients present but not available to plant
- Prevention: Maintain optimal pH (5.5-6.5) at all times

Light Stress + Temperature Stress (Additive):
- High light generates heat, both stress the plant
- Common under grow lights without adequate cooling
- Prevention: Provide adequate ventilation and light management

KEY CONCEPTS FOR NON-CODERS:

Stress Tolerance: A plant's ability to maintain function under unfavorable conditions,
like a person's ability to work under pressure.

Stress Avoidance: Mechanisms to prevent exposure to stress, like seeking shade or
closing stomata, similar to wearing warm clothes in cold weather.

Hormesis: The concept that mild stress can actually benefit plants by triggering
protective mechanisms, like how exercise stress makes people stronger.

Stress Memory: Plants can "learn" from stress experiences and respond better to
future stress, like how people develop coping mechanisms.

Stress Signaling: Plants have sophisticated communication systems that detect and
respond to stress, like the human nervous system detecting pain and responding.

This stress model helps predict plant responses to environmental challenges, optimize
growing conditions to minimize stress, and design systems that maintain plant health
even under changing conditions, leading to more resilient and productive hydroponic
crop production.
"""

