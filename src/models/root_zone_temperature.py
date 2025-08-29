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



