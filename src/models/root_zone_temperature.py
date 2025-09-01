"""
Root Zone Temperature (RZT) Model for Hydroponic Systems

Based on scientific findings from:
1. "Raising root zone temperature improves plant productivity and metabolites 
   in hydroponic lettuce production" (2024)
2. "Controlling root zone temperature improves plant growth and pigments 
   in hydroponic lettuce" (2023)

Key findings:
- Linear growth increase with RZT up to optimum temperature
- Rapid decrease beyond optimum
- RZT affects root physiological processes, nutrient uptake, and photosynthesis
- Optimal RZT is typically 3°C above air temperature
"""

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class RZTParameters:
    """Parameters for root zone temperature model."""
    optimal_rzt_offset: float  # °C above air temperature
    min_effective_rzt: float  # °C
    max_effective_rzt: float  # °C
    linear_growth_slope: float  # Growth factor per °C below optimum
    rapid_decline_slope: float  # Decline factor per °C above optimum
    base_growth_factor: float  # Baseline at optimal temperature
    
    # Sensitivity parameters for different processes
    nutrient_uptake_sensitivity_low: float  # per °C below optimum
    nutrient_uptake_sensitivity_high: float  # per °C above optimum
    water_uptake_sensitivity_low: float  # per °C below optimum
    water_uptake_sensitivity_high: float  # per °C above optimum
    photosynthesis_sensitivity_low: float  # per °C below optimum
    photosynthesis_sensitivity_high: float  # per °C above optimum
    root_metabolism_sensitivity_low: float  # per °C below optimum
    root_metabolism_sensitivity_high: float  # per °C above optimum
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'RZTParameters':
        """Create RZTParameters from configuration dictionary."""
        return cls(
            optimal_rzt_offset=config_dict['optimal_rzt_offset'],
            min_effective_rzt=config_dict['min_effective_rzt'],
            max_effective_rzt=config_dict['max_effective_rzt'],
            linear_growth_slope=config_dict['linear_growth_slope'],
            rapid_decline_slope=config_dict['rapid_decline_slope'],
            base_growth_factor=config_dict['base_growth_factor'],
            nutrient_uptake_sensitivity_low=config_dict['nutrient_uptake_sensitivity_low'],
            nutrient_uptake_sensitivity_high=config_dict['nutrient_uptake_sensitivity_high'],
            water_uptake_sensitivity_low=config_dict['water_uptake_sensitivity_low'],
            water_uptake_sensitivity_high=config_dict['water_uptake_sensitivity_high'],
            photosynthesis_sensitivity_low=config_dict['photosynthesis_sensitivity_low'],
            photosynthesis_sensitivity_high=config_dict['photosynthesis_sensitivity_high'],
            root_metabolism_sensitivity_low=config_dict['root_metabolism_sensitivity_low'],
            root_metabolism_sensitivity_high=config_dict['root_metabolism_sensitivity_high']
        )


class RootZoneTemperatureModel:
    """
    Model for root zone temperature effects on hydroponic plant growth.
    
    The model implements temperature-dependent factors affecting:
    1. Root physiological processes
    2. Nutrient uptake efficiency
    3. Water uptake capacity
    4. Root metabolism
    """
    
    def __init__(self, parameters: Optional[RZTParameters] = None):
        self.params = parameters or RZTParameters()
    
    def calculate_optimal_rzt(self, air_temperature: float) -> float:
        """
        Calculate optimal root zone temperature based on air temperature.
        
        Args:
            air_temperature: Air temperature (°C)
            
        Returns:
            Optimal RZT (°C)
        """
        optimal_rzt = air_temperature + self.params.optimal_rzt_offset
        return np.clip(optimal_rzt, self.params.min_effective_rzt, self.params.max_effective_rzt)
    
    def calculate_rzt_growth_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT-based growth factor following the scientific findings:
        - Linear increase up to optimum
        - Rapid decrease beyond optimum
        
        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)
            
        Returns:
            Growth factor (0.2 to 1.5)
        """
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        
        if current_rzt <= optimal_rzt:
            # Linear growth up to optimum
            if current_rzt >= self.params.min_effective_rzt:
                temperature_diff = optimal_rzt - current_rzt
                factor = self.params.base_growth_factor + (temperature_diff * self.params.linear_growth_slope)
            else:
                # Below minimum effective temperature
                factor = 0.2
        else:
            # Rapid decline above optimum
            temperature_excess = current_rzt - optimal_rzt
            factor = self.params.base_growth_factor - (temperature_excess * self.params.rapid_decline_slope)
        
        # Constrain factor within reasonable bounds
        return np.clip(factor, 0.2, 1.5)
    
    def calculate_nutrient_uptake_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on nutrient uptake efficiency.
        
        Based on findings that RZT affects Mg, K, Fe, Cu, Se, Rb uptake.
        
        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)
            
        Returns:
            Nutrient uptake efficiency factor (0.3 to 1.4)
        """
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        
        # Uptake efficiency follows similar pattern but with different sensitivity
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = 1.0 + (temperature_diff * self.params.nutrient_uptake_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * self.params.nutrient_uptake_sensitivity_high)
        
        return np.clip(factor, 0.3, 1.4)
    
    def calculate_water_uptake_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on water uptake capacity.
        
        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)
            
        Returns:
            Water uptake factor (0.4 to 1.3)
        """
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        
        # Water uptake is less sensitive to temperature than growth
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = 1.0 + (temperature_diff * self.params.water_uptake_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * self.params.water_uptake_sensitivity_high)
        
        return np.clip(factor, 0.4, 1.3)
    
    def calculate_photosynthesis_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on photosynthesis and assimilate distribution.
        
        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)
            
        Returns:
            Photosynthesis factor (0.5 to 1.2)
        """
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        
        # Photosynthesis has moderate sensitivity to RZT
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = 1.0 + (temperature_diff * self.params.photosynthesis_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * self.params.photosynthesis_sensitivity_high)
        
        return np.clip(factor, 0.5, 1.2)
    
    def calculate_root_metabolism_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on root metabolism and activity.
        
        Based on findings that RZT activates root metabolism.
        
        Args:
            current_rzt: Current root zone temperature (°C)  
            air_temperature: Current air temperature (°C)
            
        Returns:
            Root metabolism factor (0.3 to 1.6)
        """
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        
        # Root metabolism is highly sensitive to temperature
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = 1.0 + (temperature_diff * self.params.root_metabolism_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * self.params.root_metabolism_sensitivity_high)
        
        return np.clip(factor, 0.3, 1.6)
    
    def hourly_update(self, environmental_conditions: Dict[str, float], 
                     hour: int, dt_hours: float = 1.0) -> Dict[str, float]:
        """
        Hourly root zone temperature model update.
        
        Temperature in hydroponic systems can change rapidly with:
        - Air temperature fluctuations
        - Solution heating/cooling systems
        - Thermal mass effects
        
        Args:
            environmental_conditions: Current conditions including air and solution temps
            hour: Hour of day (0-23)
            dt_hours: Time step in hours
            
        Returns:
            Dict with temperature effects and factors
        """
        air_temp = environmental_conditions.get('air_temperature', 22.0)
        solution_temp = environmental_conditions.get('solution_temperature', air_temp)
        
        # Calculate thermal dynamics
        thermal_response = self._calculate_thermal_dynamics(
            air_temp, solution_temp, hour, dt_hours
        )
        
        # Current effective RZT (solution temperature affects roots directly)
        current_rzt = thermal_response['effective_rzt']
        optimal_rzt = self.calculate_optimal_rzt(air_temp)
        
        # Calculate all temperature-dependent factors
        growth_factor = self.calculate_rzt_growth_factor(current_rzt, air_temp)
        nutrient_factor = self.calculate_nutrient_uptake_factor(current_rzt, air_temp)
        water_factor = self.calculate_water_uptake_factor(current_rzt, air_temp)
        photosynthesis_factor = self.calculate_photosynthesis_factor(current_rzt, air_temp)
        metabolism_factor = self.calculate_root_metabolism_factor(current_rzt, air_temp)
        
        return {
            'current_rzt': current_rzt,
            'optimal_rzt': optimal_rzt,
            'rzt_deviation': current_rzt - optimal_rzt,
            'growth_factor': growth_factor,
            'nutrient_uptake_factor': nutrient_factor,
            'water_uptake_factor': water_factor,
            'photosynthesis_factor': photosynthesis_factor,
            'root_metabolism_factor': metabolism_factor,
            'thermal_stress': abs(current_rzt - optimal_rzt) / 5.0,  # Normalized stress
            **thermal_response
        }
    
    def _calculate_thermal_dynamics(self, air_temp: float, solution_temp: float, 
                                   hour: int, dt_hours: float) -> Dict[str, float]:
        """
        Calculate thermal dynamics in the hydroponic system.
        
        Factors affecting root zone temperature:
        - Solution temperature (direct contact)
        - Air temperature (convective exchange)  
        - Thermal mass of system
        - External ambient conditions
        """
        # Time-dependent thermal effects
        # Root zones have thermal inertia - don't change instantly
        thermal_mass_factor = 0.2  # How quickly RZT responds to changes
        
        # Diurnal temperature variation (outdoor effects)
        ambient_temp_variation = 2.0 * np.sin(2 * np.pi * (hour - 6) / 24)  # Peak at 18:00
        
        # Heat sources/sinks
        heat_sources = {
            'solution_heating': 0.0,  # Would be controlled by system
            'root_respiration': 0.5,  # Small heat generation from roots
            'pump_heat': 0.3,        # Heat from circulation pumps
            'ambient_exchange': ambient_temp_variation * 0.1
        }
        
        # Calculate equilibrium temperature
        # In real systems, this involves heat transfer equations
        target_rzt = solution_temp + sum(heat_sources.values())
        
        # Current state (with thermal inertia)
        if not hasattr(self, '_previous_rzt'):
            self._previous_rzt = solution_temp
        
        # Exponential approach to target with time constant
        time_constant = 2.0  # hours (thermal response time)
        response_rate = 1.0 - np.exp(-dt_hours / time_constant)
        
        new_rzt = self._previous_rzt + (target_rzt - self._previous_rzt) * response_rate
        self._previous_rzt = new_rzt
        
        # Heat transfer rate (W/m² - for energy calculations)
        heat_transfer_rate = abs(new_rzt - air_temp) * 10.0  # Simplified
        
        return {
            'effective_rzt': new_rzt,
            'target_rzt': target_rzt,
            'thermal_lag': new_rzt - target_rzt,
            'heat_transfer_rate': heat_transfer_rate,
            'heating_required': max(0.0, target_rzt - new_rzt),
            'cooling_required': max(0.0, new_rzt - target_rzt)
        }

    def daily_update(self, environmental_conditions: Dict[str, float]) -> Dict[str, float]:
        """
        Daily root zone temperature update for backward compatibility.
        
        Uses average daily conditions for systems that don't need hourly precision.
        """
        air_temp = environmental_conditions.get('air_temperature', 22.0)
        solution_temp = environmental_conditions.get('solution_temperature', air_temp)
        
        # Use noon hour (12) as representative for daily calculation
        return self.hourly_update(environmental_conditions, hour=12, dt_hours=24.0)


def create_lettuce_rzt_model(system_config=None) -> RootZoneTemperatureModel:
    """Create root zone temperature model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        RootZoneTemperatureModel configured with CSV parameters
    """
    try:
        # Get root zone temperature parameters from CSV data loaded in system_config
        rzt_params = getattr(system_config, 'root_zone_temperature_parameters', {})
        
        # Create parameters from CSV config
        parameters = RZTParameters.from_config(rzt_params)
        return RootZoneTemperatureModel(parameters)
        
    except Exception as e:
        print(f"Warning: Could not load CSV root zone temperature parameters: {e}")
        print("Using default root zone temperature parameters")
        return RootZoneTemperatureModel()



