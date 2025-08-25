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
    optimal_temp_min: float = 18.0
    optimal_temp_max: float = 24.0

    heat_threshold_mild: float = 28.0
    heat_threshold_severe: float = 35.0
    heat_lethal_temperature: float = 45.0

    cold_threshold_mild: float = 12.0
    cold_threshold_severe: float = 5.0
    frost_threshold: float = -1.0

    photosynthesis_heat_sensitivity: float = 0.85
    photosynthesis_cold_sensitivity: float = 0.75
    respiration_heat_sensitivity: float = 0.60
    respiration_cold_sensitivity: float = 0.70
    growth_heat_sensitivity: float = 0.90
    growth_cold_sensitivity: float = 0.80
    development_heat_sensitivity: float = 0.70
    development_cold_sensitivity: float = 0.65

    acclimation_rate: float = 0.05
    max_acclimation_days: int = 14
    acclimation_decay_rate: float = 0.02

    heat_damage_threshold: float = 0.7
    cold_damage_threshold: float = 0.6
    frost_damage_rate: float = 0.2
    recovery_rate_heat: float = 0.08
    recovery_rate_cold: float = 0.05

    stress_memory_duration: int = 7
    memory_effect_strength: float = 0.3

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "TemperatureStressParameters":
        return cls(
            optimal_temp_min=config.get("optimal_temp_min", 18.0),
            optimal_temp_max=config.get("optimal_temp_max", 24.0),
            heat_threshold_mild=config.get("heat_threshold_mild", 28.0),
            heat_threshold_severe=config.get("heat_threshold_severe", 35.0),
            heat_lethal_temperature=config.get("heat_lethal_temperature", 45.0),
            cold_threshold_mild=config.get("cold_threshold_mild", 12.0),
            cold_threshold_severe=config.get("cold_threshold_severe", 5.0),
            frost_threshold=config.get("frost_threshold", -1.0),
            photosynthesis_heat_sensitivity=config.get("photosynthesis_heat_sensitivity", 0.85),
            photosynthesis_cold_sensitivity=config.get("photosynthesis_cold_sensitivity", 0.75),
            respiration_heat_sensitivity=config.get("respiration_heat_sensitivity", 0.60),
            respiration_cold_sensitivity=config.get("respiration_cold_sensitivity", 0.70),
            growth_heat_sensitivity=config.get("growth_heat_sensitivity", 0.90),
            growth_cold_sensitivity=config.get("growth_cold_sensitivity", 0.80),
            development_heat_sensitivity=config.get("development_heat_sensitivity", 0.70),
            development_cold_sensitivity=config.get("development_cold_sensitivity", 0.65),
            acclimation_rate=config.get("acclimation_rate", 0.05),
            max_acclimation_days=config.get("max_acclimation_days", 14),
            acclimation_decay_rate=config.get("acclimation_decay_rate", 0.02),
            heat_damage_threshold=config.get("heat_damage_threshold", 0.7),
            cold_damage_threshold=config.get("cold_damage_threshold", 0.6),
            frost_damage_rate=config.get("frost_damage_rate", 0.2),
            recovery_rate_heat=config.get("recovery_rate_heat", 0.08),
            recovery_rate_cold=config.get("recovery_rate_cold", 0.05),
            stress_memory_duration=config.get("stress_memory_duration", 7),
            memory_effect_strength=config.get("memory_effect_strength", 0.3),
        )


@dataclass
class TemperatureAcclimation:
    heat_acclimation: float = 0.0
    cold_acclimation: float = 0.0
    acclimation_history: List[float] = None

    def __post_init__(self):
        if self.acclimation_history is None:
            self.acclimation_history = []


@dataclass
class TemperatureDamage:
    heat_damage: float = 0.0
    cold_damage: float = 0.0
    frost_damage: float = 0.0
    damage_recovery_rate: float = 0.0


@dataclass
class ProcessStressFactors:
    photosynthesis: float = 1.0
    respiration: float = 1.0
    growth: float = 1.0
    development: float = 1.0
    overall: float = 1.0


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
        self.acclimation = TemperatureAcclimation()
        self.damage = TemperatureDamage()
        self.stress_history: List[Tuple[float, float]] = []
        self.current_stress_duration = 0.0
        self.last_temperature: Optional[float] = None

    def classify_temperature_stress(self, temperature: float) -> TemperatureStressType:
        if self.params.optimal_temp_min <= temperature <= self.params.optimal_temp_max:
            return TemperatureStressType.OPTIMAL
        elif temperature < self.params.frost_threshold:
            return TemperatureStressType.FROST
        elif temperature < self.params.optimal_temp_min:
            return TemperatureStressType.COLD
        else:
            return TemperatureStressType.HEAT

    def calculate_base_stress_level(self, temperature: float) -> float:
        if self.params.optimal_temp_min <= temperature <= self.params.optimal_temp_max:
            return 0.0
        if temperature > self.params.optimal_temp_max:
            if temperature <= self.params.heat_threshold_mild:
                excess_temp = temperature - self.params.optimal_temp_max
                mild_range = self.params.heat_threshold_mild - self.params.optimal_temp_max
                return 0.3 * (excess_temp / mild_range)
            elif temperature <= self.params.heat_threshold_severe:
                excess_temp = temperature - self.params.heat_threshold_mild
                moderate_range = self.params.heat_threshold_severe - self.params.heat_threshold_mild
                return 0.3 + 0.4 * (excess_temp / moderate_range)
            else:
                excess_temp = temperature - self.params.heat_threshold_severe
                severe_range = self.params.heat_lethal_temperature - self.params.heat_threshold_severe
                return 0.7 + 0.3 * min(1.0, excess_temp / severe_range)
        else:
            if temperature >= self.params.cold_threshold_mild:
                temp_deficit = self.params.optimal_temp_min - temperature
                mild_range = self.params.optimal_temp_min - self.params.cold_threshold_mild
                return 0.2 * (temp_deficit / mild_range)
            elif temperature >= self.params.cold_threshold_severe:
                temp_deficit = self.params.cold_threshold_mild - temperature
                moderate_range = self.params.cold_threshold_mild - self.params.cold_threshold_severe
                return 0.2 + 0.3 * (temp_deficit / moderate_range)
            elif temperature >= self.params.frost_threshold:
                temp_deficit = self.params.cold_threshold_severe - temperature
                severe_range = self.params.cold_threshold_severe - self.params.frost_threshold
                return 0.5 + 0.3 * (temp_deficit / severe_range)
            else:
                return 0.8 + 0.2 * min(1.0, abs(temperature - self.params.frost_threshold) / 5.0)

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
        f.overall = (
            f.photosynthesis * 0.35 + f.growth * 0.35 + f.development * 0.20 + f.respiration * 0.10
        )
        return f

    def update_damage_and_recovery(self, stress_level: float, stress_type: TemperatureStressType):
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
            if self.damage.heat_damage > 0:
                self.damage.heat_damage = max(0.0, self.damage.heat_damage - self.params.recovery_rate_heat)
            if self.damage.cold_damage > 0:
                self.damage.cold_damage = max(0.0, self.damage.cold_damage - self.params.recovery_rate_cold)
            if self.damage.frost_damage > 0:
                self.damage.frost_damage = max(0.0, self.damage.frost_damage - self.params.recovery_rate_cold * 0.5)

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

        self.update_damage_and_recovery(final_stress, stress_type)
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


def create_lettuce_temperature_stress_model(config=None) -> TemperatureStressModel:
    try:
        if config is None:
            from ..utils.config_loader import get_config_loader
            config_loader = get_config_loader()
            temp_stress_config = config_loader.get_value("temperature_stress", "parameters", {})
        else:
            temp_stress_config = {}  # Use defaults for CSV config
        params = TemperatureStressParameters.from_config(temp_stress_config)
        return TemperatureStressModel(params)
    except Exception:
        return TemperatureStressModel(TemperatureStressParameters())


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
        if self.stress_weights is None:
            self.stress_weights = {
                StressType.WATER.value: 0.25,
                StressType.TEMPERATURE.value: 0.20,
                StressType.NUTRIENT.value: 0.20,
                StressType.LIGHT.value: 0.15,
                StressType.SALINITY.value: 0.10,
                StressType.OXYGEN.value: 0.05,
                StressType.PH.value: 0.03,
                StressType.MECHANICAL.value: 0.01,
                StressType.PATHOGEN.value: 0.01,
            }
        if self.stress_interactions is None:
            self.stress_interactions = {
                StressType.WATER.value: {
                    StressType.TEMPERATURE.value: {"type": "synergistic", "factor": 1.3},
                    StressType.SALINITY.value: {"type": "synergistic", "factor": 1.4},
                    StressType.NUTRIENT.value: {"type": "multiplicative", "factor": 1.2},
                },
                StressType.TEMPERATURE.value: {
                    StressType.WATER.value: {"type": "synergistic", "factor": 1.3},
                    StressType.LIGHT.value: {"type": "additive", "factor": 1.1},
                    StressType.OXYGEN.value: {"type": "multiplicative", "factor": 1.2},
                },
                StressType.NUTRIENT.value: {
                    StressType.WATER.value: {"type": "multiplicative", "factor": 1.2},
                    StressType.PH.value: {"type": "synergistic", "factor": 1.5},
                    StressType.SALINITY.value: {"type": "multiplicative", "factor": 1.1},
                },
                StressType.LIGHT.value: {
                    StressType.TEMPERATURE.value: {"type": "additive", "factor": 1.1},
                    StressType.WATER.value: {"type": "multiplicative", "factor": 1.1},
                },
                StressType.SALINITY.value: {
                    StressType.WATER.value: {"type": "synergistic", "factor": 1.4},
                    StressType.NUTRIENT.value: {"type": "multiplicative", "factor": 1.1},
                    StressType.OXYGEN.value: {"type": "multiplicative", "factor": 1.2},
                },
            }
        if self.process_sensitivity is None:
            self.process_sensitivity = {
                ProcessType.PHOTOSYNTHESIS.value: {
                    StressType.WATER.value: 0.9,
                    StressType.TEMPERATURE.value: 0.8,
                    StressType.LIGHT.value: 0.9,
                    StressType.NUTRIENT.value: 0.7,
                    StressType.SALINITY.value: 0.6,
                },
                ProcessType.GROWTH.value: {
                    StressType.WATER.value: 0.8,
                    StressType.TEMPERATURE.value: 0.7,
                    StressType.NUTRIENT.value: 0.9,
                    StressType.LIGHT.value: 0.6,
                    StressType.SALINITY.value: 0.7,
                },
                ProcessType.NUTRIENT_UPTAKE.value: {
                    StressType.WATER.value: 0.6,
                    StressType.TEMPERATURE.value: 0.5,
                    StressType.SALINITY.value: 0.9,
                    StressType.OXYGEN.value: 0.8,
                    StressType.PH.value: 0.7,
                },
                ProcessType.DEVELOPMENT.value: {
                    StressType.TEMPERATURE.value: 0.9,
                    StressType.WATER.value: 0.7,
                    StressType.LIGHT.value: 0.6,
                    StressType.NUTRIENT.value: 0.5,
                },
                ProcessType.SENESCENCE.value: {
                    StressType.WATER.value: 0.8,
                    StressType.NUTRIENT.value: 0.7,
                    StressType.TEMPERATURE.value: 0.6,
                    StressType.LIGHT.value: 0.5,
                },
            }
        if self.stress_memory_duration is None:
            self.stress_memory_duration = {
                StressType.WATER.value: 3.0,
                StressType.TEMPERATURE.value: 5.0,
                StressType.NUTRIENT.value: 7.0,
                StressType.LIGHT.value: 2.0,
                StressType.SALINITY.value: 10.0,
                StressType.OXYGEN.value: 1.0,
                StressType.PH.value: 2.0,
            }
        if self.recovery_rates is None:
            self.recovery_rates = {
                StressType.WATER.value: 0.3,
                StressType.TEMPERATURE.value: 0.2,
                StressType.NUTRIENT.value: 0.1,
                StressType.LIGHT.value: 0.5,
                StressType.SALINITY.value: 0.05,
                StressType.OXYGEN.value: 0.8,
                StressType.PH.value: 0.4,
            }
        if self.acclimation_rates is None:
            self.acclimation_rates = {
                StressType.WATER.value: 0.1,
                StressType.TEMPERATURE.value: 0.15,
                StressType.LIGHT.value: 0.2,
                StressType.SALINITY.value: 0.05,
                StressType.NUTRIENT.value: 0.08,
            }
        if self.stress_onset_thresholds is None:
            self.stress_onset_thresholds = {
                StressType.WATER.value: 0.8,
                StressType.TEMPERATURE.value: 0.9,
                StressType.NUTRIENT.value: 0.7,
                StressType.LIGHT.value: 0.6,
                StressType.SALINITY.value: 0.9,
                StressType.OXYGEN.value: 0.8,
                StressType.PH.value: 0.8,
            }
        if self.damage_thresholds is None:
            self.damage_thresholds = {
                StressType.WATER.value: 0.3,
                StressType.TEMPERATURE.value: 0.2,
                StressType.NUTRIENT.value: 0.4,
                StressType.LIGHT.value: 0.2,
                StressType.SALINITY.value: 0.4,
                StressType.OXYGEN.value: 0.3,
                StressType.PH.value: 0.3,
            }

    @classmethod
    def from_config(cls, config_dict: dict) -> "IntegratedStressParameters":
        stress_weights = config_dict.get("stress_weights", {})
        stress_interactions = config_dict.get("stress_interactions", {})
        process_sensitivity = config_dict.get("process_sensitivity", {})
        memory_duration = config_dict.get("stress_memory_duration", {})
        recovery_rates = config_dict.get("recovery_rates", {})
        acclimation_rates = config_dict.get("acclimation_rates", {})
        onset_thresholds = config_dict.get("stress_onset_thresholds", {})
        damage_thresholds = config_dict.get("damage_thresholds", {})
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
    acute_stress: float = 0.0
    chronic_stress: float = 0.0
    acclimation_level: float = 0.0
    damage_level: float = 0.0
    recovery_progress: float = 0.0
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
        self.params = parameters or IntegratedStressParameters()
        self.stress_states: Dict[str, StressState] = {}
        self.stress_history: List[Dict[str, Any]] = []
        self.cumulative_damage: Dict[str, float] = {}
        for st in self.params.stress_weights.keys():
            self.stress_states[st] = StressState(stress_type=st, current_level=1.0)
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
            sensitivity = sensitivities.get(st, 0.5)
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
                memory = self.params.stress_memory_duration.get(st_type, 5.0)
                if len(state.stress_history) > memory:
                    state.stress_history = state.stress_history[-int(memory) :]
                threshold = self.params.stress_onset_thresholds.get(st_type, 0.8)
                if level < threshold:
                    state.days_under_stress += 1
                else:
                    state.days_under_stress = max(0, state.days_under_stress - 1)
                state.acute_stress = self.calculate_acute_stress(st_type, level)
                state.chronic_stress = self.calculate_chronic_stress(state)
                state.acclimation_level = self.calculate_acclimation_effect(state)
                state.recovery_progress = self.calculate_recovery_effect(state)
                damage_threshold = self.params.damage_thresholds.get(st_type, 0.3)
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
            impacts[st] = (1.0 - state.acute_stress) * self.params.stress_weights.get(st, 0.1)
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


def create_lettuce_integrated_stress_model(config=None) -> IntegratedStressModel:
    try:
        if config is None:
            from ..utils.config_loader import get_config_loader
            config = get_config_loader()
            stress_config = config.get_value("integrated_stress", "", {})
        else:
            stress_config = {}  # Use defaults for CSV config
        parameters = IntegratedStressParameters.from_config(stress_config)
        return IntegratedStressModel(parameters)
    except Exception:
        return IntegratedStressModel()


if __name__ == "__main__":
    # Minimal demonstrations
    print("Unified Stress Models - Demonstration")
    print("=" * 80)
    tmodel = create_lettuce_temperature_stress_model()
    tresp = tmodel.daily_update(30.0)
    print(f"Temp 30C -> stress {tresp.stress_level:.3f}, overall factor {tresp.process_factors.overall:.3f}")

    imodel = create_lettuce_integrated_stress_model()
    iresp = imodel.daily_update({"water": 0.7, "temperature": 0.6, "nutrient": 0.8, "light": 0.9, "salinity": 1.0})
    print(f"Integrated overall factor: {iresp.overall_stress_factor:.3f}, severity: {iresp.stress_severity}")
