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
    
    # Advanced thermal dynamics parameters
    min_growth_factor: float  # Minimum growth factor below effective temperature
    thermal_mass_factor: float  # How quickly RZT responds to changes
    ambient_temp_amplitude: float  # Amplitude of diurnal temperature variation
    root_respiration_heat: float  # Heat generation from root respiration
    pump_heat_generation: float  # Heat generation from circulation pumps
    ambient_exchange_factor: float  # Factor for ambient temperature exchange
    thermal_response_time: float  # Thermal response time constant (hours)
    heat_transfer_coefficient: float  # Heat transfer coefficient for calculations
    
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
            root_metabolism_sensitivity_high=config_dict['root_metabolism_sensitivity_high'],
            min_growth_factor=config_dict['min_growth_factor'],
            thermal_mass_factor=config_dict['thermal_mass_factor'],
            ambient_temp_amplitude=config_dict['ambient_temp_amplitude'],
            root_respiration_heat=config_dict['root_respiration_heat'],
            pump_heat_generation=config_dict['pump_heat_generation'],
            ambient_exchange_factor=config_dict['ambient_exchange_factor'],
            thermal_response_time=config_dict['thermal_response_time'],
            heat_transfer_coefficient=config_dict['heat_transfer_coefficient']
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
        if parameters is None:
            raise ValueError("❌ RZTParameters required - no hardcoded defaults allowed")
        self.params = parameters
    
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
                factor = self.params.min_growth_factor
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
        air_temp = environmental_conditions.get('air_temperature', None)
        if air_temp is None:
            raise ValueError("❌ Air temperature must be provided in environmental conditions - no hardcoded defaults allowed")
        
        solution_temp = environmental_conditions.get('solution_temperature', None)
        if solution_temp is None:
            raise ValueError("❌ Solution temperature must be provided in environmental conditions - no hardcoded defaults allowed")
        
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
        thermal_mass_factor = self.params.thermal_mass_factor  # How quickly RZT responds to changes
        
        # Diurnal temperature variation (outdoor effects)
        ambient_temp_variation = self.params.ambient_temp_amplitude * np.sin(2 * np.pi * (hour - 6) / 24)  # Peak at 18:00
        
        # Heat sources/sinks
        heat_sources = {
            'solution_heating': 0.0,  # Would be controlled by system
            'root_respiration': self.params.root_respiration_heat,  # Small heat generation from roots
            'pump_heat': self.params.pump_heat_generation,        # Heat from circulation pumps
            'ambient_exchange': ambient_temp_variation * self.params.ambient_exchange_factor
        }
        
        # Calculate equilibrium temperature
        # In real systems, this involves heat transfer equations
        target_rzt = solution_temp + sum(heat_sources.values())
        
        # Current state (with thermal inertia)
        if not hasattr(self, '_previous_rzt'):
            self._previous_rzt = solution_temp
        
        # Exponential approach to target with time constant
        time_constant = self.params.thermal_response_time  # hours (thermal response time)
        response_rate = 1.0 - np.exp(-dt_hours / time_constant)
        
        new_rzt = self._previous_rzt + (target_rzt - self._previous_rzt) * response_rate
        self._previous_rzt = new_rzt
        
        # Heat transfer rate (W/m² - for energy calculations)
        heat_transfer_rate = abs(new_rzt - air_temp) * self.params.heat_transfer_coefficient  # Simplified
        
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
        air_temp = environmental_conditions.get('air_temperature', None)
        if air_temp is None:
            raise ValueError("❌ Air temperature must be provided in environmental conditions - no hardcoded defaults allowed")
        
        solution_temp = environmental_conditions.get('solution_temperature', None)
        if solution_temp is None:
            raise ValueError("❌ Solution temperature must be provided in environmental conditions - no hardcoded defaults allowed")
        
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
        rzt_params = getattr(system_config, 'root_zone_temperature_parameters', {}).copy()
        water_params = getattr(system_config, 'water_parameters', {})

        # Get water uptake sensitivity from water parameters since RZT duplicates were removed
        if 'water_uptake_sensitivity_low' not in rzt_params and 'water_uptake_sensitivity_low' in water_params:
            rzt_params['water_uptake_sensitivity_low'] = water_params['water_uptake_sensitivity_low']
        if 'water_uptake_sensitivity_high' not in rzt_params and 'water_uptake_sensitivity_high' in water_params:
            rzt_params['water_uptake_sensitivity_high'] = water_params['water_uptake_sensitivity_high']

        # Map renamed parameters to expected parameter names
        param_mapping = {
            'rzt_min_growth_factor': 'min_growth_factor',
            'rzt_thermal_mass_factor': 'thermal_mass_factor',
            'rzt_ambient_temp_amplitude': 'ambient_temp_amplitude',
            'rzt_root_respiration_heat': 'root_respiration_heat',
            'rzt_pump_heat_generation': 'pump_heat_generation',
            'rzt_ambient_exchange_factor': 'ambient_exchange_factor',
            'rzt_thermal_response_time': 'thermal_response_time',
            'rzt_heat_transfer_coefficient': 'heat_transfer_coefficient'
        }
        
        # Apply parameter name mapping
        for csv_name, model_name in param_mapping.items():
            if csv_name in rzt_params:
                rzt_params[model_name] = rzt_params[csv_name]
        
        # Create parameters from CSV config
        parameters = RZTParameters.from_config(rzt_params)
        return RootZoneTemperatureModel(parameters)
        
    except Exception as e:
        raise ValueError(f"❌ Failed to load CSV root zone temperature parameters: {e}. No hardcoded defaults allowed.")


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file manages root zone temperature (RZT) - the temperature around plant roots in hydroponic 
systems. Think of it like controlling the water temperature in a fish tank - it affects everything 
the roots do, from absorbing nutrients to growing.

KEY FUNCTIONS AND EQUATIONS:

1. calculate_optimal_rzt()
   - What it does: Determines the ideal root temperature based on air temperature
   - Equation: optimal_RZT = air_temperature + offset (typically +3°C)
   - Real-world meaning: Plants like their roots slightly warmer than the air around their leaves.
     Like how your feet feel better when they're warmer than your head in cold weather.

2. calculate_rzt_growth_factor()
   - What it does: Calculates how root temperature affects overall plant growth
   - Equations:
     * Below optimal: factor = base_factor + (optimal_temp - current_temp) × linear_slope
     * Above optimal: factor = base_factor - (current_temp - optimal_temp) × decline_slope
   - Real-world meaning: Growth increases linearly until optimal temperature, then drops rapidly 
     if too hot. Like Goldilocks - there's a "just right" temperature zone.

3. calculate_nutrient_uptake_factor()
   - What it does: Calculates how root temperature affects nutrient absorption efficiency
   - Equation: factor = 1.0 ± temperature_difference × sensitivity
   - Real-world meaning: Cold roots can't absorb nutrients well (like trying to drink a thick 
     shake through a straw). Too hot and they get damaged and also can't absorb properly.

4. calculate_water_uptake_factor()
   - What it does: Determines how root temperature affects water absorption
   - Similar equations to nutrient uptake but different sensitivity
   - Real-world meaning: Root temperature affects how efficiently roots can pump water up to 
     the leaves. Cold = sluggish pumping, too hot = damage and poor pumping.

5. calculate_photosynthesis_factor()
   - What it does: Shows how root temperature indirectly affects photosynthesis (food production)
   - Real-world meaning: Happy roots = healthy plant = better photosynthesis. It's all connected - 
     roots are like the foundation of a house, affecting everything above.

6. calculate_root_metabolism_factor()
   - What it does: Calculates how temperature affects root cellular activity
   - Real-world meaning: Root cells need to be active to do their job. Cold = sluggish cells, 
     optimal = active cells, too hot = damaged cells.

7. _calculate_thermal_dynamics()
   - What it does: Models how root zone temperature changes over time with various heat sources/sinks
   - Equations: Uses exponential approach to target temperature with time constants
   - Real-world meaning: Root zones don't change temperature instantly - they have "thermal mass" 
     like how a pot of water takes time to heat up or cool down.

KEY TEMPERATURE CONCEPTS:

OPTIMAL RANGE:
- Usually 3-5°C warmer than air temperature
- For lettuce: typically 18-25°C root zone
- Too cold (<15°C): Slow growth, poor nutrient uptake
- Too hot (>28°C): Root damage, stress, poor growth

THERMAL DYNAMICS:
- Thermal mass: How quickly temperature changes (large systems = slow changes)
- Heat sources: Pumps, ambient air, heaters
- Heat sinks: Cooling systems, evaporation, cold ambient air

RESPONSE PATTERNS:
- Linear increase up to optimal (more heat = better growth)
- Rapid decline above optimal (overheating = damage)
- Different sensitivities for different processes (growth vs nutrient uptake)

PRACTICAL APPLICATIONS:
- Optimize root zone heating systems for maximum efficiency
- Predict plant performance based on root temperature
- Adjust nutrient concentrations based on uptake efficiency
- Schedule irrigation based on water uptake capacity  
- Design thermal management systems for hydroponic facilities
- Understand why plants perform poorly in certain seasons

This system helps growers maintain the "happy zone" for roots, which is the foundation 
for healthy, productive plants. Like keeping your feet warm in winter - it affects 
your whole body's comfort and performance.
"""



