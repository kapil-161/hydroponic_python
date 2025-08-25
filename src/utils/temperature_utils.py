"""
Temperature Utility Functions

Centralized temperature calculations to eliminate duplication across models.
Provides standardized Q10, thermal time, and temperature factor calculations.
"""

import math
from typing import Optional


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
    temp_diff = temperature - reference_temp
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
    if temperature <= base_temp or temperature >= max_temp:
        return 0.0
    
    if optimal_temp_min <= temperature <= optimal_temp_max:
        return temperature - base_temp
    
    if temperature < optimal_temp_min:
        # Linear increase from base to optimal
        return (temperature - base_temp) * (optimal_temp_min - base_temp) / (optimal_temp_min - base_temp)
    
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


def clamp_value(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Clamp a value between minimum and maximum bounds.
    
    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, value))


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


# Common temperature constants (can be overridden by config)
DEFAULT_Q10_FACTOR = 2.0
DEFAULT_BASE_TEMPERATURE = 4.0
DEFAULT_OPTIMAL_TEMP_MIN = 18.0
DEFAULT_OPTIMAL_TEMP_MAX = 24.0
DEFAULT_MAX_TEMPERATURE = 35.0