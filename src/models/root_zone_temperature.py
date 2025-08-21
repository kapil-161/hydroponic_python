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
    optimal_rzt_offset: float = 3.0  # °C above air temperature
    min_effective_rzt: float = 15.0  # °C
    max_effective_rzt: float = 35.0  # °C
    linear_growth_slope: float = 0.08  # Growth factor per °C below optimum
    rapid_decline_slope: float = 0.15  # Decline factor per °C above optimum
    base_growth_factor: float = 1.0  # Baseline at optimal temperature
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'RZTParameters':
        """Create RZTParameters from configuration dictionary."""
        return cls(
            optimal_rzt_offset=config_dict.get('optimal_rzt_offset', 3.0),
            min_effective_rzt=config_dict.get('min_effective_rzt', 15.0),
            max_effective_rzt=config_dict.get('max_effective_rzt', 35.0),
            linear_growth_slope=config_dict.get('linear_growth_slope', 0.08),
            rapid_decline_slope=config_dict.get('rapid_decline_slope', 0.15),
            base_growth_factor=config_dict.get('base_growth_factor', 1.0)
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
            factor = 1.0 + (temperature_diff * 0.06)  # Slightly less sensitive
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * 0.12)  # More sensitive to excess
        
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
            factor = 1.0 + (temperature_diff * 0.04)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * 0.08)
        
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
            factor = 1.0 + (temperature_diff * 0.03)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * 0.05)
        
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
            factor = 1.0 + (temperature_diff * 0.1)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = 1.0 - (temperature_excess * 0.18)
        
        return np.clip(factor, 0.3, 1.6)
    
    

def demonstrate_rzt_model():
    """Demonstrate root zone temperature effects across temperatures."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        rzt_cfg = config_loader.get_rzt_parameters()
        model = RootZoneTemperatureModel(RZTParameters.from_config(rzt_cfg))
    except Exception:
        model = RootZoneTemperatureModel()

    print("=" * 80)
    print("ROOT ZONE TEMPERATURE (RZT) MODEL DEMONSTRATION")
    print("=" * 80)

    air_temp = 22.0
    print(f"{'RZT':<6} {'Growth':<8} {'Nutrient':<9} {'Water':<7} {'Photosyn':<8} {'Metab':<7}")
    print("-" * 80)
    for rzt in [14, 16, 18, 20, 22, 24, 28, 32, 36]:
        g = model.calculate_rzt_growth_factor(rzt, air_temp)
        n = model.calculate_nutrient_uptake_factor(rzt, air_temp)
        w = model.calculate_water_uptake_factor(rzt, air_temp)
        p = model.calculate_photosynthesis_factor(rzt, air_temp)
        m = model.calculate_root_metabolism_factor(rzt, air_temp)
        print(f"{rzt:<6.0f} {g:<8.2f} {n:<9.2f} {w:<7.2f} {p:<8.2f} {m:<7.2f}")


if __name__ == "__main__":
    demonstrate_rzt_model()

