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
    
    def calculate_comprehensive_rzt_effects(self, current_rzt: float, 
                                          air_temperature: float) -> Dict[str, float]:
        """
        Calculate all RZT effects comprehensively.
        
        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)
            
        Returns:
            Dictionary of all RZT effect factors
        """
        return {
            'growth_factor': self.calculate_rzt_growth_factor(current_rzt, air_temperature),
            'nutrient_uptake_factor': self.calculate_nutrient_uptake_factor(current_rzt, air_temperature),
            'water_uptake_factor': self.calculate_water_uptake_factor(current_rzt, air_temperature),
            'photosynthesis_factor': self.calculate_photosynthesis_factor(current_rzt, air_temperature),
            'root_metabolism_factor': self.calculate_root_metabolism_factor(current_rzt, air_temperature),
            'optimal_rzt': self.calculate_optimal_rzt(air_temperature)
        }
    
    def simulate_rzt_control(self, target_rzt: float, current_rzt: float, 
                           heating_capacity: float = 100.0, 
                           cooling_capacity: float = 50.0) -> Tuple[float, float]:
        """
        Simulate RZT control system (heating/cooling).
        
        Args:
            target_rzt: Target root zone temperature (°C)
            current_rzt: Current root zone temperature (°C)
            heating_capacity: Maximum heating rate (W or relative units)
            cooling_capacity: Maximum cooling rate (W or relative units)
            
        Returns:
            Tuple of (new_rzt, energy_used)
        """
        temperature_diff = target_rzt - current_rzt
        
        if temperature_diff > 0:
            # Need heating
            heating_needed = min(abs(temperature_diff), heating_capacity / 10.0)
            new_rzt = current_rzt + heating_needed
            energy_used = heating_needed * 10.0
        elif temperature_diff < 0:
            # Need cooling
            cooling_needed = min(abs(temperature_diff), cooling_capacity / 10.0)
            new_rzt = current_rzt - cooling_needed
            energy_used = cooling_needed * 8.0  # Cooling typically less efficient
        else:
            # No change needed
            new_rzt = current_rzt
            energy_used = 0.0
        
        return new_rzt, energy_used
    
    def get_rzt_recommendations(self, air_temperature_forecast: list) -> Dict[str, float]:
        """
        Get RZT control recommendations based on air temperature forecast.
        
        Args:
            air_temperature_forecast: List of forecasted air temperatures (°C)
            
        Returns:
            RZT recommendations dictionary
        """
        if not air_temperature_forecast:
            return {}
        
        avg_air_temp = np.mean(air_temperature_forecast)
        min_air_temp = np.min(air_temperature_forecast)
        max_air_temp = np.max(air_temperature_forecast)
        
        recommendations = {
            'recommended_rzt': self.calculate_optimal_rzt(avg_air_temp),
            'min_rzt_needed': self.calculate_optimal_rzt(min_air_temp),
            'max_rzt_acceptable': self.calculate_optimal_rzt(max_air_temp),
            'avg_air_temp': avg_air_temp,
            'heating_priority': max(0, self.calculate_optimal_rzt(min_air_temp) - min_air_temp),
            'cooling_priority': max(0, max_air_temp - self.calculate_optimal_rzt(max_air_temp))
        }
        
        return recommendations


def create_default_rzt_model() -> RootZoneTemperatureModel:
    """Create RZT model with default parameters for lettuce."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        rzt_config = config_loader.get_rzt_parameters()
        parameters = RZTParameters.from_config(rzt_config)
        return RootZoneTemperatureModel(parameters)
    except ImportError:
        # Fallback to default values if config loader not available
        return RootZoneTemperatureModel()


def demonstrate_rzt_effects():
    """Demonstrate RZT model effects across temperature range."""
    model = create_default_rzt_model()
    
    air_temps = [20, 25, 30]
    rzt_range = list(range(15, 36))
    
    print("Root Zone Temperature Effects Demonstration")
    print("=" * 60)
    
    for air_temp in air_temps:
        print(f"\nAir Temperature: {air_temp}°C")
        print(f"Optimal RZT: {model.calculate_optimal_rzt(air_temp):.1f}°C")
        print("-" * 40)
        print("RZT(°C) | Growth | Nutrient | Water | Photo | Metabolism")
        print("-" * 40)
        
        for rzt in rzt_range[::3]:  # Every 3rd value for brevity
            effects = model.calculate_comprehensive_rzt_effects(rzt, air_temp)
            print(f"{rzt:6.1f} | {effects['growth_factor']:6.2f} | "
                  f"{effects['nutrient_uptake_factor']:8.2f} | {effects['water_uptake_factor']:5.2f} | "
                  f"{effects['photosynthesis_factor']:5.2f} | {effects['root_metabolism_factor']:10.2f}")


if __name__ == "__main__":
    demonstrate_rzt_effects()