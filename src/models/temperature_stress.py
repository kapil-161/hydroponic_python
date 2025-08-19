"""
Temperature Stress Model for Hydroponic Crop Simulation

This module implements comprehensive temperature stress modeling including:
- Heat stress effects on photosynthesis and respiration
- Cold stress and frost damage mechanisms
- Temperature acclimation and memory effects
- Integration with the stress modeling framework

Based on CROPGRO temperature stress modeling principles and current research
in plant temperature responses and acclimation mechanisms.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class TemperatureStressType(Enum):
    """Types of temperature stress."""
    HEAT = "heat"
    COLD = "cold"
    FROST = "frost"
    OPTIMAL = "optimal"


@dataclass
class TemperatureStressParameters:
    """Temperature stress model parameters."""
    
    # Optimal temperature ranges
    optimal_temp_min: float = 18.0  # °C - Lower bound of optimal range
    optimal_temp_max: float = 24.0  # °C - Upper bound of optimal range
    
    # Heat stress parameters
    heat_threshold_mild: float = 28.0    # °C - Mild heat stress threshold
    heat_threshold_severe: float = 35.0  # °C - Severe heat stress threshold
    heat_lethal_temperature: float = 45.0 # °C - Lethal temperature
    
    # Cold stress parameters  
    cold_threshold_mild: float = 12.0    # °C - Mild cold stress threshold
    cold_threshold_severe: float = 5.0   # °C - Severe cold stress threshold
    frost_threshold: float = -1.0        # °C - Frost damage threshold
    
    # Process-specific sensitivities (0-1, where 1 = most sensitive)
    photosynthesis_heat_sensitivity: float = 0.85
    photosynthesis_cold_sensitivity: float = 0.75
    respiration_heat_sensitivity: float = 0.60
    respiration_cold_sensitivity: float = 0.70
    growth_heat_sensitivity: float = 0.90
    growth_cold_sensitivity: float = 0.80
    development_heat_sensitivity: float = 0.70
    development_cold_sensitivity: float = 0.65
    
    # Acclimation parameters
    acclimation_rate: float = 0.05      # Daily acclimation rate (0-1)
    max_acclimation_days: int = 14      # Maximum days for full acclimation
    acclimation_decay_rate: float = 0.02 # Rate of acclimation loss
    
    # Damage and recovery parameters
    heat_damage_threshold: float = 0.7   # Stress level where damage begins
    cold_damage_threshold: float = 0.6   # Stress level where damage begins
    frost_damage_rate: float = 0.2       # Damage per hour below frost threshold
    recovery_rate_heat: float = 0.08     # Recovery rate from heat damage
    recovery_rate_cold: float = 0.05     # Recovery rate from cold damage
    
    # Memory effects
    stress_memory_duration: int = 7      # Days stress memory persists
    memory_effect_strength: float = 0.3  # Strength of memory effect on current stress
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'TemperatureStressParameters':
        """Create parameters from configuration dictionary."""
        return cls(
            optimal_temp_min=config.get('optimal_temp_min', 18.0),
            optimal_temp_max=config.get('optimal_temp_max', 24.0),
            heat_threshold_mild=config.get('heat_threshold_mild', 28.0),
            heat_threshold_severe=config.get('heat_threshold_severe', 35.0),
            heat_lethal_temperature=config.get('heat_lethal_temperature', 45.0),
            cold_threshold_mild=config.get('cold_threshold_mild', 12.0),
            cold_threshold_severe=config.get('cold_threshold_severe', 5.0),
            frost_threshold=config.get('frost_threshold', -1.0),
            photosynthesis_heat_sensitivity=config.get('photosynthesis_heat_sensitivity', 0.85),
            photosynthesis_cold_sensitivity=config.get('photosynthesis_cold_sensitivity', 0.75),
            respiration_heat_sensitivity=config.get('respiration_heat_sensitivity', 0.60),
            respiration_cold_sensitivity=config.get('respiration_cold_sensitivity', 0.70),
            growth_heat_sensitivity=config.get('growth_heat_sensitivity', 0.90),
            growth_cold_sensitivity=config.get('growth_cold_sensitivity', 0.80),
            development_heat_sensitivity=config.get('development_heat_sensitivity', 0.70),
            development_cold_sensitivity=config.get('development_cold_sensitivity', 0.65),
            acclimation_rate=config.get('acclimation_rate', 0.05),
            max_acclimation_days=config.get('max_acclimation_days', 14),
            acclimation_decay_rate=config.get('acclimation_decay_rate', 0.02),
            heat_damage_threshold=config.get('heat_damage_threshold', 0.7),
            cold_damage_threshold=config.get('cold_damage_threshold', 0.6),
            frost_damage_rate=config.get('frost_damage_rate', 0.2),
            recovery_rate_heat=config.get('recovery_rate_heat', 0.08),
            recovery_rate_cold=config.get('recovery_rate_cold', 0.05),
            stress_memory_duration=config.get('stress_memory_duration', 7),
            memory_effect_strength=config.get('memory_effect_strength', 0.3)
        )


@dataclass
class TemperatureAcclimation:
    """Tracks temperature acclimation state."""
    heat_acclimation: float = 0.0       # 0-1, degree of heat acclimation
    cold_acclimation: float = 0.0       # 0-1, degree of cold acclimation
    acclimation_history: List[float] = None  # Recent temperature history
    
    def __post_init__(self):
        if self.acclimation_history is None:
            self.acclimation_history = []


@dataclass
class TemperatureDamage:
    """Tracks cumulative temperature damage."""
    heat_damage: float = 0.0            # Cumulative heat damage (0-1)
    cold_damage: float = 0.0            # Cumulative cold damage (0-1)
    frost_damage: float = 0.0           # Cumulative frost damage (0-1)
    damage_recovery_rate: float = 0.0   # Current recovery rate


@dataclass
class ProcessStressFactors:
    """Temperature stress factors for different plant processes."""
    photosynthesis: float = 1.0         # Photosynthesis stress factor (0-1)
    respiration: float = 1.0            # Respiration stress factor (0-1)
    growth: float = 1.0                 # Growth stress factor (0-1)
    development: float = 1.0            # Development stress factor (0-1)
    overall: float = 1.0                # Overall stress factor


@dataclass
class TemperatureStressResponse:
    """Complete temperature stress response."""
    stress_type: TemperatureStressType
    stress_level: float                 # Overall stress level (0-1)
    process_factors: ProcessStressFactors
    acclimation_state: TemperatureAcclimation
    damage_state: TemperatureDamage
    temperature_deviation: float       # Degrees from optimal range
    stress_duration: float             # Duration of current stress (hours)
    memory_effect: float               # Effect of stress memory (0-1)


class TemperatureStressModel:
    """
    Comprehensive temperature stress model for crop simulation.
    
    Models temperature effects on plant physiology including:
    - Heat and cold stress responses
    - Temperature acclimation mechanisms
    - Cumulative damage and recovery
    - Process-specific stress sensitivities
    - Stress memory effects
    """
    
    def __init__(self, params: TemperatureStressParameters):
        self.params = params
        self.acclimation = TemperatureAcclimation()
        self.damage = TemperatureDamage()
        self.stress_history: List[Tuple[float, float]] = []  # (stress_level, temperature)
        self.current_stress_duration = 0.0  # Hours
        self.last_temperature = None
        
    def classify_temperature_stress(self, temperature: float) -> TemperatureStressType:
        """Classify the type of temperature stress."""
        if self.params.optimal_temp_min <= temperature <= self.params.optimal_temp_max:
            return TemperatureStressType.OPTIMAL
        elif temperature < self.params.frost_threshold:
            return TemperatureStressType.FROST
        elif temperature < self.params.optimal_temp_min:
            return TemperatureStressType.COLD
        else:
            return TemperatureStressType.HEAT
    
    def calculate_base_stress_level(self, temperature: float) -> float:
        """Calculate base stress level before acclimation effects."""
        if self.params.optimal_temp_min <= temperature <= self.params.optimal_temp_max:
            return 0.0
        
        if temperature > self.params.optimal_temp_max:
            # Heat stress calculation
            if temperature <= self.params.heat_threshold_mild:
                # Mild heat stress zone
                excess_temp = temperature - self.params.optimal_temp_max
                mild_range = self.params.heat_threshold_mild - self.params.optimal_temp_max
                return 0.3 * (excess_temp / mild_range)
            
            elif temperature <= self.params.heat_threshold_severe:
                # Moderate heat stress zone
                excess_temp = temperature - self.params.heat_threshold_mild
                moderate_range = self.params.heat_threshold_severe - self.params.heat_threshold_mild
                return 0.3 + 0.4 * (excess_temp / moderate_range)
            
            else:
                # Severe heat stress zone
                excess_temp = temperature - self.params.heat_threshold_severe
                severe_range = self.params.heat_lethal_temperature - self.params.heat_threshold_severe
                return 0.7 + 0.3 * min(1.0, excess_temp / severe_range)
        
        else:
            # Cold stress calculation
            if temperature >= self.params.cold_threshold_mild:
                # Mild cold stress zone
                temp_deficit = self.params.optimal_temp_min - temperature
                mild_range = self.params.optimal_temp_min - self.params.cold_threshold_mild
                return 0.2 * (temp_deficit / mild_range)
            
            elif temperature >= self.params.cold_threshold_severe:
                # Moderate cold stress zone
                temp_deficit = self.params.cold_threshold_mild - temperature
                moderate_range = self.params.cold_threshold_mild - self.params.cold_threshold_severe
                return 0.2 + 0.3 * (temp_deficit / moderate_range)
            
            elif temperature >= self.params.frost_threshold:
                # Severe cold stress zone
                temp_deficit = self.params.cold_threshold_severe - temperature
                severe_range = self.params.cold_threshold_severe - self.params.frost_threshold
                return 0.5 + 0.3 * (temp_deficit / severe_range)
            
            else:
                # Frost zone
                return 0.8 + 0.2 * min(1.0, abs(temperature - self.params.frost_threshold) / 5.0)
    
    def update_acclimation(self, temperature: float, stress_type: TemperatureStressType):
        """Update temperature acclimation state."""
        # Add to temperature history
        self.acclimation.acclimation_history.append(temperature)
        
        # Keep only recent history
        max_history = self.params.max_acclimation_days
        if len(self.acclimation.acclimation_history) > max_history:
            self.acclimation.acclimation_history = self.acclimation.acclimation_history[-max_history:]
        
        # Calculate acclimation based on temperature exposure
        if stress_type == TemperatureStressType.HEAT:
            # Increase heat acclimation
            target_acclimation = min(1.0, (temperature - self.params.optimal_temp_max) / 
                                   (self.params.heat_threshold_severe - self.params.optimal_temp_max))
            
            acclimation_change = self.params.acclimation_rate * (target_acclimation - self.acclimation.heat_acclimation)
            self.acclimation.heat_acclimation += acclimation_change
            
            # Decay cold acclimation
            self.acclimation.cold_acclimation *= (1.0 - self.params.acclimation_decay_rate)
        
        elif stress_type == TemperatureStressType.COLD or stress_type == TemperatureStressType.FROST:
            # Increase cold acclimation
            target_acclimation = min(1.0, (self.params.optimal_temp_min - temperature) / 
                                   (self.params.optimal_temp_min - self.params.cold_threshold_severe))
            
            acclimation_change = self.params.acclimation_rate * (target_acclimation - self.acclimation.cold_acclimation)
            self.acclimation.cold_acclimation += acclimation_change
            
            # Decay heat acclimation
            self.acclimation.heat_acclimation *= (1.0 - self.params.acclimation_decay_rate)
        
        else:
            # Optimal temperature - decay both acclimations
            self.acclimation.heat_acclimation *= (1.0 - self.params.acclimation_decay_rate)
            self.acclimation.cold_acclimation *= (1.0 - self.params.acclimation_decay_rate)
        
        # Ensure bounds
        self.acclimation.heat_acclimation = max(0.0, min(1.0, self.acclimation.heat_acclimation))
        self.acclimation.cold_acclimation = max(0.0, min(1.0, self.acclimation.cold_acclimation))
    
    def apply_acclimation_effects(self, base_stress: float, stress_type: TemperatureStressType) -> float:
        """Apply acclimation effects to base stress level."""
        if stress_type == TemperatureStressType.HEAT:
            # Heat acclimation reduces heat stress
            acclimation_factor = 1.0 - (self.acclimation.heat_acclimation * 0.4)  # Up to 40% reduction
            return base_stress * acclimation_factor
        
        elif stress_type == TemperatureStressType.COLD or stress_type == TemperatureStressType.FROST:
            # Cold acclimation reduces cold stress
            acclimation_factor = 1.0 - (self.acclimation.cold_acclimation * 0.5)  # Up to 50% reduction
            return base_stress * acclimation_factor
        
        return base_stress
    
    def calculate_memory_effects(self) -> float:
        """Calculate stress memory effects on current response."""
        if len(self.stress_history) == 0:
            return 0.0
        
        # Consider only recent stress history
        recent_history = self.stress_history[-self.params.stress_memory_duration:]
        
        if not recent_history:
            return 0.0
        
        # Calculate weighted average of recent stress
        total_weight = 0.0
        weighted_stress = 0.0
        
        for i, (stress_level, _) in enumerate(recent_history):
            # More recent stress has higher weight
            weight = (i + 1) / len(recent_history)
            weighted_stress += stress_level * weight
            total_weight += weight
        
        if total_weight > 0:
            avg_stress = weighted_stress / total_weight
            return avg_stress * self.params.memory_effect_strength
        
        return 0.0
    
    def calculate_process_stress_factors(self, stress_level: float, stress_type: TemperatureStressType) -> ProcessStressFactors:
        """Calculate stress factors for different plant processes."""
        factors = ProcessStressFactors()
        
        if stress_type == TemperatureStressType.HEAT:
            # Heat stress effects
            factors.photosynthesis = max(0.0, 1.0 - stress_level * self.params.photosynthesis_heat_sensitivity)
            factors.respiration = max(0.0, 1.0 - stress_level * self.params.respiration_heat_sensitivity)
            factors.growth = max(0.0, 1.0 - stress_level * self.params.growth_heat_sensitivity)
            factors.development = max(0.0, 1.0 - stress_level * self.params.development_heat_sensitivity)
        
        elif stress_type in [TemperatureStressType.COLD, TemperatureStressType.FROST]:
            # Cold stress effects
            factors.photosynthesis = max(0.0, 1.0 - stress_level * self.params.photosynthesis_cold_sensitivity)
            factors.respiration = max(0.0, 1.0 - stress_level * self.params.respiration_cold_sensitivity)
            factors.growth = max(0.0, 1.0 - stress_level * self.params.growth_cold_sensitivity)
            factors.development = max(0.0, 1.0 - stress_level * self.params.development_cold_sensitivity)
        
        else:
            # Optimal temperature - no stress
            factors.photosynthesis = 1.0
            factors.respiration = 1.0
            factors.growth = 1.0
            factors.development = 1.0
        
        # Calculate overall factor as weighted average
        factors.overall = (
            factors.photosynthesis * 0.35 +
            factors.growth * 0.35 +
            factors.development * 0.20 +
            factors.respiration * 0.10
        )
        
        return factors
    
    def update_damage_and_recovery(self, stress_level: float, stress_type: TemperatureStressType, temperature: float):
        """Update cumulative damage and recovery processes."""
        # Apply damage if stress exceeds threshold
        if stress_type == TemperatureStressType.HEAT and stress_level > self.params.heat_damage_threshold:
            damage_rate = (stress_level - self.params.heat_damage_threshold) * 0.01  # 1% per day at max stress
            self.damage.heat_damage = min(1.0, self.damage.heat_damage + damage_rate)
            self.damage.damage_recovery_rate = self.params.recovery_rate_heat
        
        elif stress_type in [TemperatureStressType.COLD, TemperatureStressType.FROST]:
            if stress_type == TemperatureStressType.FROST:
                # Rapid frost damage
                frost_damage_rate = self.params.frost_damage_rate / 24.0  # Convert to per hour
                self.damage.frost_damage = min(1.0, self.damage.frost_damage + frost_damage_rate)
            
            if stress_level > self.params.cold_damage_threshold:
                damage_rate = (stress_level - self.params.cold_damage_threshold) * 0.008  # 0.8% per day
                self.damage.cold_damage = min(1.0, self.damage.cold_damage + damage_rate)
                self.damage.damage_recovery_rate = self.params.recovery_rate_cold
        
        else:
            # Optimal conditions - allow recovery
            if self.damage.heat_damage > 0:
                self.damage.heat_damage = max(0.0, self.damage.heat_damage - self.params.recovery_rate_heat)
            
            if self.damage.cold_damage > 0:
                self.damage.cold_damage = max(0.0, self.damage.cold_damage - self.params.recovery_rate_cold)
            
            # Frost damage recovers more slowly
            if self.damage.frost_damage > 0:
                self.damage.frost_damage = max(0.0, self.damage.frost_damage - self.params.recovery_rate_cold * 0.5)
    
    def daily_update(self, temperature: float, duration_hours: float = 24.0) -> TemperatureStressResponse:
        """
        Update temperature stress model for one day.
        
        Args:
            temperature: Average daily temperature (°C)
            duration_hours: Duration of temperature exposure (hours)
            
        Returns:
            TemperatureStressResponse with complete stress analysis
        """
        # Classify stress type
        stress_type = self.classify_temperature_stress(temperature)
        
        # Calculate base stress level
        base_stress = self.calculate_base_stress_level(temperature)
        
        # Update acclimation
        self.update_acclimation(temperature, stress_type)
        
        # Apply acclimation effects
        adjusted_stress = self.apply_acclimation_effects(base_stress, stress_type)
        
        # Calculate memory effects
        memory_effect = self.calculate_memory_effects()
        
        # Final stress level includes memory effects
        final_stress = min(1.0, adjusted_stress + memory_effect)
        
        # Update stress duration
        if self.last_temperature is not None and abs(temperature - self.last_temperature) < 2.0:
            self.current_stress_duration += duration_hours
        else:
            self.current_stress_duration = duration_hours
        
        # Calculate process-specific stress factors
        process_factors = self.calculate_process_stress_factors(final_stress, stress_type)
        
        # Apply damage effects to process factors
        total_damage = max(self.damage.heat_damage, self.damage.cold_damage, self.damage.frost_damage)
        if total_damage > 0:
            damage_factor = 1.0 - total_damage * 0.5  # Up to 50% reduction from damage
            process_factors.photosynthesis *= damage_factor
            process_factors.growth *= damage_factor
            process_factors.development *= damage_factor
            process_factors.overall *= damage_factor
        
        # Update damage and recovery
        self.update_damage_and_recovery(final_stress, stress_type, temperature)
        
        # Update stress history
        self.stress_history.append((final_stress, temperature))
        if len(self.stress_history) > self.params.stress_memory_duration:
            self.stress_history = self.stress_history[-self.params.stress_memory_duration:]
        
        # Calculate temperature deviation
        if stress_type == TemperatureStressType.HEAT:
            temp_deviation = temperature - self.params.optimal_temp_max
        elif stress_type in [TemperatureStressType.COLD, TemperatureStressType.FROST]:
            temp_deviation = self.params.optimal_temp_min - temperature
        else:
            temp_deviation = 0.0
        
        # Store current temperature
        self.last_temperature = temperature
        
        return TemperatureStressResponse(
            stress_type=stress_type,
            stress_level=final_stress,
            process_factors=process_factors,
            acclimation_state=self.acclimation,
            damage_state=self.damage,
            temperature_deviation=temp_deviation,
            stress_duration=self.current_stress_duration,
            memory_effect=memory_effect
        )
    
    def get_stress_summary(self) -> Dict[str, Any]:
        """Get comprehensive stress model summary."""
        return {
            'current_heat_acclimation': self.acclimation.heat_acclimation,
            'current_cold_acclimation': self.acclimation.cold_acclimation,
            'cumulative_heat_damage': self.damage.heat_damage,
            'cumulative_cold_damage': self.damage.cold_damage,
            'cumulative_frost_damage': self.damage.frost_damage,
            'stress_history_length': len(self.stress_history),
            'average_recent_stress': sum(s[0] for s in self.stress_history[-7:]) / max(7, len(self.stress_history)),
            'recovery_rate': self.damage.damage_recovery_rate,
            'stress_duration_hours': self.current_stress_duration
        }


def create_lettuce_temperature_stress_model(config_path: Optional[str] = None) -> TemperatureStressModel:
    """
    Factory function to create temperature stress model for lettuce.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Configured TemperatureStressModel instance
    """
    try:
        from src.utils.config_loader import get_config_loader
        
        config_loader = get_config_loader(config_path)
        temp_stress_config = config_loader.get_value('temperature_stress', 'parameters', {})
        
        params = TemperatureStressParameters.from_config(temp_stress_config)
        return TemperatureStressModel(params)
        
    except ImportError:
        # Fallback to default parameters if config system not available
        params = TemperatureStressParameters()
        return TemperatureStressModel(params)


if __name__ == "__main__":
    # Test temperature stress model
    print("Testing Temperature Stress Model")
    print("=" * 50)
    
    # Create model with default parameters
    params = TemperatureStressParameters()
    model = TemperatureStressModel(params)
    
    # Test temperature scenarios
    test_temperatures = [5.0, 12.0, 18.0, 22.0, 28.0, 35.0, 42.0]
    
    print("Temperature stress response analysis:")
    print(f"{'Temp(°C)':<8} {'Type':<8} {'Stress':<8} {'Photo':<8} {'Growth':<8} {'Overall':<8}")
    print("-" * 60)
    
    for temp in test_temperatures:
        response = model.daily_update(temp)
        
        print(f"{temp:<8.1f} {response.stress_type.value:<8} {response.stress_level:<8.3f} "
              f"{response.process_factors.photosynthesis:<8.3f} {response.process_factors.growth:<8.3f} "
              f"{response.process_factors.overall:<8.3f}")
    
    # Test acclimation over time
    print(f"\nTesting heat acclimation (30°C for 14 days):")
    model = TemperatureStressModel(params)  # Reset model
    
    for day in range(14):
        response = model.daily_update(30.0)
        if day % 3 == 0:
            print(f"Day {day+1}: Stress={response.stress_level:.3f}, "
                  f"Acclimation={response.acclimation_state.heat_acclimation:.3f}")
    
    print(f"\nTemperature stress model testing complete!")