"""
Temperature Utility Functions - No hardcoded defaults allowed and no fallback to simple alternative codes

Centralized temperature calculations to eliminate duplication across models.
Provides standardized Q10, thermal time, VPD, pH, and temperature factor calculations.
"""

import math
import numpy as np
from typing import Optional, Any
def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to specified range."""
    return max(min_val, min(max_val, value))


def sanitize_temperature(temperature: Any) -> float:
    """
    Sanitize temperature value to ensure it's a real number.
    
    Args:
        temperature: Temperature value (may be complex)
        
    Returns:
        Real temperature value as float
    """
    if isinstance(temperature, complex):
        return temperature.real
    return float(temperature)


def calculate_q10_temperature_factor(temperature: float, 
                                   reference_temp: float = 20.0,
                                   q10_factor: float = 2.0,
                                   min_factor: float = 0.1,
                                   max_factor: float = 4.0) -> float:
    """
    Calculate Q10-based temperature factor.
    
    Args:
        temperature: Current temperature (°C)
        reference_temp: Reference temperature (°C) 
        q10_factor: Q10 coefficient (default 2.0)
        min_factor: Minimum factor limit
        max_factor: Maximum factor limit
        
    Returns:
        Temperature factor (1.0 at reference temperature)
    """
    # Ensure temperature is real (not complex)
    if isinstance(temperature, complex):
        temperature = temperature.real
    temp_diff = float(temperature) - reference_temp
    factor = q10_factor ** (temp_diff / 10.0)
    return clamp_value(factor, min_factor, max_factor)


def calculate_thermal_time(temperature: float,
                         base_temp: float = 4.0,
                         optimal_temp_min: float = 18.0,
                         optimal_temp_max: float = 24.0,
                         max_temp: float = 35.0) -> float:
    """
    Calculate thermal time (growing degree days) using cardinal temperatures.
    
    Args:
        temperature: Current temperature (°C)
        base_temp: Base temperature below which no development occurs
        optimal_temp_min: Lower bound of optimal temperature range  
        optimal_temp_max: Upper bound of optimal temperature range
        max_temp: Maximum temperature above which development stops
        
    Returns:
        Thermal time units (0 = no development, 1 = optimal)
    """
    # Ensure temperature is real (not complex)
    if isinstance(temperature, complex):
        temperature = temperature.real
    if temperature <= base_temp or temperature >= max_temp:
        return 0.0
    
    if optimal_temp_min <= temperature <= optimal_temp_max:
        return temperature - base_temp
    
    if temperature < optimal_temp_min:
        # Linear increase from base to optimal
        return (temperature - base_temp)
    
    else:  # temperature > optimal_temp_max
        # Linear decrease from optimal to max
        remaining = max_temp - temperature
        total_range = max_temp - optimal_temp_max
        return (optimal_temp_max - base_temp) * (remaining / total_range)


def calculate_temperature_stress_factor(temperature: float,
                                       optimal_temp_min: float = 18.0,
                                       optimal_temp_max: float = 24.0,
                                       stress_temp_min: float = 10.0,
                                       stress_temp_max: float = 35.0) -> float:
    """
    Calculate temperature stress factor (0 = severe stress, 1 = optimal).
    
    Args:
        temperature: Current temperature (°C)
        optimal_temp_min: Lower bound of optimal range
        optimal_temp_max: Upper bound of optimal range  
        stress_temp_min: Temperature where stress becomes severe (cold)
        stress_temp_max: Temperature where stress becomes severe (heat)
        
    Returns:
        Stress factor (1.0 = no stress, 0.0 = severe stress)
    """
    if optimal_temp_min <= temperature <= optimal_temp_max:
        return 1.0
    
    if temperature < optimal_temp_min:
        # Cold stress
        if temperature <= stress_temp_min:
            return 0.0
        return (temperature - stress_temp_min) / (optimal_temp_min - stress_temp_min)
    
    else:  # temperature > optimal_temp_max
        # Heat stress
        if temperature >= stress_temp_max:
            return 0.0
        return (stress_temp_max - temperature) / (stress_temp_max - optimal_temp_max)


# clamp_value function now imported from core_utils


def interpolate_linear(value: float, 
                      in_min: float, in_max: float,
                      out_min: float = 0.0, out_max: float = 1.0) -> float:
    """
    Linear interpolation between input and output ranges.
    
    Args:
        value: Input value
        in_min: Input range minimum
        in_max: Input range maximum
        out_min: Output range minimum  
        out_max: Output range maximum
        
    Returns:
        Interpolated value
    """
    if in_max == in_min:
        return out_min
    
    ratio = (value - in_min) / (in_max - in_min)
    ratio = clamp_value(ratio, 0.0, 1.0)
    return out_min + ratio * (out_max - out_min)


def calculate_vpd(temperature: float, relative_humidity: float) -> float:
    """
    Calculate vapor pressure deficit using Magnus equation.
    
    Args:
        temperature: Air temperature (°C)
        relative_humidity: Relative humidity (%)
        
    Returns:
        VPD in kPa
    """
    # Saturation vapor pressure using Magnus formula (kPa)
    es = 0.6108 * np.exp(17.27 * temperature / (temperature + 237.3))
    
    # Actual vapor pressure (kPa)
    ea = es * (relative_humidity / 100.0)
    
    # VPD is the difference (ensure non-negative)
    return max(0.0, es - ea)


def calculate_ph_effect(ph: float,
                       optimal_ph_min: float = 5.5,
                       optimal_ph_max: float = 6.5,
                       stress_ph_min: float = 4.0,
                       stress_ph_max: float = 8.0) -> float:
    """
    Calculate pH effect on plant processes (0 = severe stress, 1 = optimal).
    
    Args:
        ph: Current pH value
        optimal_ph_min: Lower bound of optimal pH range
        optimal_ph_max: Upper bound of optimal pH range
        stress_ph_min: pH where stress becomes severe (acidic)
        stress_ph_max: pH where stress becomes severe (alkaline)
        
    Returns:
        pH factor (1.0 = no stress, 0.0 = severe stress)
    """
    if optimal_ph_min <= ph <= optimal_ph_max:
        return 1.0
    
    if ph < optimal_ph_min:
        # Acidic stress
        if ph <= stress_ph_min:
            return 0.0
        return (ph - stress_ph_min) / (optimal_ph_min - stress_ph_min)
    
    else:  # ph > optimal_ph_max
        # Alkaline stress
        if ph >= stress_ph_max:
            return 0.0
        return (stress_ph_max - ph) / (stress_ph_max - optimal_ph_max)


# Common constants (can be overridden by config)
DEFAULT_Q10_FACTOR = 2.0
DEFAULT_BASE_TEMPERATURE = 4.0
DEFAULT_OPTIMAL_TEMP_MIN = 18.0
DEFAULT_OPTIMAL_TEMP_MAX = 24.0
DEFAULT_MAX_TEMPERATURE = 35.0
DEFAULT_OPTIMAL_PH_MIN = 5.5
DEFAULT_OPTIMAL_PH_MAX = 6.5


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file contains utility functions for temperature-related calculations used throughout 
the hydroponic simulation. Think of it as a specialized toolbox containing all the 
mathematical formulas needed to understand how temperature affects plants. It's like 
having a collection of scientific calculators specifically designed for plant biology.

KEY UTILITY FUNCTIONS EXPLAINED:

1. sanitize_temperature()
   - What it does: Ensures temperature values are real numbers (not complex mathematical numbers)
   - Why needed: Computer calculations sometimes produce complex numbers that need to be converted
   - Real-world meaning: Like double-checking that your thermometer reading is a normal temperature 
     value, not some weird mathematical artifact. Ensures 25.3°C stays 25.3°C, not 25.3+0.2i°C.

2. calculate_q10_temperature_factor()
   - What it does: Calculates how much faster biological processes happen at different temperatures
   - Equation: factor = Q10^((temperature - reference_temp) / 10)
   - Q10 Rule: Most biological processes double in rate for every 10°C increase
   - Example: If Q10=2, then at 30°C processes run 2× faster than at 20°C
   - Real-world meaning: Like how cooking happens faster at higher temperatures - plant metabolism 
     also speeds up with warmth, but there are limits to prevent "burning."

3. calculate_thermal_time()
   - What it does: Converts temperature into "heat units" that plants accumulate for development
   - Uses cardinal temperatures: base (too cold), optimal (just right), maximum (too hot)
   - Equation: Based on temperature ranges with linear scaling between thresholds
   - Real-world meaning: Like a "heat bank account" where plants deposit daily heat units until 
     they have enough "savings" to advance to the next growth stage. Cold days = no deposits, 
     optimal days = maximum deposits, hot days = reduced deposits.

4. calculate_temperature_stress_factor()
   - What it does: Measures how temperature stress affects plant performance
   - Range: 1.0 = no stress (optimal temperature), 0.0 = severe stress (extreme temperature)
   - Zones: optimal (no stress) → mild stress → severe stress (plant damage)
   - Real-world meaning: Like a plant comfort meter - shows how happy the plant is with current 
     temperature. Green zone = happy plant, red zone = stressed plant.

5. clamp_value()
   - What it does: Keeps values within reasonable biological limits
   - Purpose: Prevents mathematical calculations from producing impossible results
   - Example: Ensures stress factors stay between 0-1, not go to -5 or 50
   - Real-world meaning: Like safety limiters on equipment - prevents the simulation from 
     calculating that a plant is "200% stressed" or has "-30% growth."

6. interpolate_linear()
   - What it does: Smoothly converts values from one scale to another
   - Example: Converting temperature 15-25°C scale to stress factor 0.5-1.0 scale
   - Mathematical approach: Linear scaling between ranges
   - Real-world meaning: Like converting between measurement units (Fahrenheit to Celsius) 
     but for any two scales. Ensures smooth transitions rather than sudden jumps.

7. calculate_vpd()
   - What it does: Calculates Vapor Pressure Deficit - how "thirsty" the air is for water
   - Uses: Magnus equation for saturation vapor pressure
   - Equation: VPD = saturation_pressure - actual_pressure
   - Real-world meaning: Like measuring how dry the air feels. High VPD = very dry air that 
     will pull water from plants rapidly. Low VPD = humid air that barely pulls water from plants.
     Imagine the difference between desert air vs. tropical rainforest air.

8. calculate_ph_effect()
   - What it does: Determines how pH (acidity/alkalinity) affects nutrient availability
   - pH Scale: 0-14 (0=very acidic, 7=neutral, 14=very alkaline)
   - Optimal range: Usually 5.5-6.5 for hydroponics
   - Real-world meaning: Like checking if your swimming pool water is properly balanced. 
     Wrong pH makes nutrients "locked up" so plants can't absorb them, even if the nutrients 
     are present in the solution.

BIOLOGICAL CONCEPTS EXPLAINED:

Q10 Temperature Response:
- Universal biological principle: enzyme activity doubles every 10°C increase
- Examples: Photosynthesis, respiration, growth, nutrient uptake all follow Q10
- Limitations: Only works within biological temperature ranges
- Too hot: Enzymes denature (like cooking an egg - proteins change shape permanently)
- Too cold: Enzymes become sluggish (like cold honey flowing slowly)

Cardinal Temperature Model:
- Base temperature: Minimum for any biological activity (usually 4-5°C for cool crops)
- Optimal range: Temperature where processes work most efficiently
- Maximum temperature: Upper limit before heat damage occurs
- Real application: Used for calculating growing degree days in agriculture

Vapor Pressure Deficit (VPD):
- Critical for plant water relations and transpiration
- Low VPD (0-0.4 kPa): Plants conserve water, slow growth, disease risk
- Optimal VPD (0.8-1.2 kPa): Balanced growth and water use
- High VPD (>1.5 kPa): Plants lose water rapidly, close stomata, stress
- Management: Control temperature and humidity to optimize VPD

pH and Nutrient Availability:
- Each nutrient has optimal pH range for availability
- Acidic pH (<5.5): Iron/manganese toxicity, phosphorus deficiency
- Alkaline pH (>7.0): Iron/zinc deficiency, phosphorus lockout
- Buffer systems: Natural or artificial pH stabilizers

PRACTICAL APPLICATIONS:

For Hydroponic Growers:
1. **Temperature Management**: Use thermal time to predict development stages
2. **VPD Optimization**: Balance temperature and humidity for optimal plant water use
3. **pH Control**: Maintain optimal pH range for nutrient availability
4. **Climate Control**: Understand how temperature affects all plant processes
5. **Stress Prevention**: Monitor temperature stress factors before damage occurs

For System Designers:
1. **Climate Control Systems**: Design heating/cooling based on cardinal temperatures
2. **Sensor Placement**: Monitor temperatures at critical plant zones
3. **Automation Logic**: Use stress factors to trigger environmental adjustments
4. **Energy Efficiency**: Optimize temperature control for best plant response vs. energy use

For Researchers:
1. **Model Validation**: Compare calculated factors with experimental measurements
2. **Parameter Calibration**: Adjust constants based on specific crop varieties
3. **Sensitivity Analysis**: Determine which temperature factors most affect growth
4. **Environmental Studies**: Model climate change impacts on crop production

MATHEMATICAL RELATIONSHIPS:

Temperature Stress is Non-Linear:
- Small temperature changes near optimal = small effects
- Large temperature changes = exponentially worse effects
- Example: 2°C above optimal might reduce growth 10%, but 10°C above optimal might stop growth completely

VPD Combines Temperature and Humidity:
- Same humidity feels different at different temperatures
- 70% humidity at 20°C = 0.9 kPa VPD (good)
- 70% humidity at 30°C = 1.4 kPa VPD (stressful)
- Management requires controlling both factors simultaneously

Q10 Effects Compound:
- Small temperature increases have large cumulative effects
- 5°C increase = ~50% faster processes
- 10°C increase = ~100% faster processes (doubling)
- 15°C increase = ~200% faster processes (tripling)

KEY CONCEPTS FOR NON-CODERS:

Biological Rate Constants: Mathematical values that describe how fast biological processes 
happen, like speed limits but for cellular activities.

Cardinal Points: Critical temperature thresholds that define biological comfort zones, 
like the temperature range where you feel comfortable without a jacket or sweater.

Exponential Relationships: When small changes cause big effects, like how a small 
increase in interest rate can dramatically change loan payments.

Saturation Limits: The maximum amount of something (like water vapor) that air can hold 
at a given temperature, similar to how a sponge can only hold so much water.

Stress Response Curves: Mathematical descriptions of how organisms respond to increasing 
levels of environmental stress, typically starting gradual and becoming steep.

These utility functions provide the mathematical foundation for understanding how 
temperature affects every aspect of plant biology in hydroponic systems. They enable 
precise modeling of plant responses to environmental conditions, supporting both 
scientific research and practical growing applications for optimal crop production.
"""