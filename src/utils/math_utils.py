"""
Mathematical Utility Functions

Common mathematical operations used across crop simulation models.
Eliminates duplication of clamping, scaling, and validation operations.
"""

import math
from typing import Union, Optional, Dict, List


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


def clamp_positive(value: float) -> float:
    """
    Ensure a value is non-negative.
    
    Args:
        value: Value to clamp
        
    Returns:
        Value clamped to be >= 0
    """
    return max(0.0, value)


def clamp_fraction(value: float) -> float:
    """
    Clamp a value to be a valid fraction (0-1).
    
    Args:
        value: Value to clamp
        
    Returns:
        Value clamped between 0 and 1
    """
    return clamp_value(value, 0.0, 1.0)


def clamp_stress_factor(value: float) -> float:
    """
    Clamp a stress factor to valid range (0 = no stress, 1 = full stress).
    
    Args:
        value: Stress factor value
        
    Returns:
        Stress factor clamped between 0 and 1
    """
    return clamp_value(value, 0.0, 1.0)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division with default value for zero denominator.
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value when denominator is zero
        
    Returns:
        Division result or default value
    """
    return numerator / denominator if abs(denominator) > 1e-10 else default


def safe_sqrt(value: float) -> float:
    """
    Safe square root that handles negative values.
    
    Args:
        value: Input value
        
    Returns:
        Square root of absolute value
    """
    return math.sqrt(abs(value))


def safe_log(value: float, base: float = math.e, default: float = 0.0) -> float:
    """
    Safe logarithm that handles zero and negative values.
    
    Args:
        value: Input value
        base: Logarithm base
        default: Default value for invalid inputs
        
    Returns:
        Logarithm or default value
    """
    if value <= 0:
        return default
    
    if base == math.e:
        return math.log(value)
    else:
        return math.log(value) / math.log(base)


def linear_interpolate(value: float, 
                      in_min: float, in_max: float,
                      out_min: float = 0.0, out_max: float = 1.0,
                      clamp_output: bool = True) -> float:
    """
    Linear interpolation between input and output ranges.
    
    Args:
        value: Input value
        in_min: Input range minimum
        in_max: Input range maximum
        out_min: Output range minimum  
        out_max: Output range maximum
        clamp_output: Whether to clamp output to range
        
    Returns:
        Interpolated value
    """
    if abs(in_max - in_min) < 1e-10:
        return out_min
    
    ratio = (value - in_min) / (in_max - in_min)
    
    if clamp_output:
        ratio = clamp_value(ratio, 0.0, 1.0)
    
    return out_min + ratio * (out_max - out_min)


def sigmoid_response(value: float, midpoint: float = 0.5, steepness: float = 1.0) -> float:
    """
    Sigmoid response function for smooth transitions.
    
    Args:
        value: Input value
        midpoint: Midpoint of sigmoid curve
        steepness: Steepness of curve (higher = steeper)
        
    Returns:
        Sigmoid response (0-1)
    """
    try:
        exponent = -steepness * (value - midpoint)
        return 1.0 / (1.0 + math.exp(exponent))
    except OverflowError:
        return 0.0 if value < midpoint else 1.0


def gaussian_response(value: float, optimum: float, width: float = 1.0) -> float:
    """
    Gaussian response function peaked at optimum value.
    
    Args:
        value: Input value
        optimum: Optimal value where response = 1
        width: Width of gaussian curve
        
    Returns:
        Gaussian response (0-1)
    """
    if width <= 0:
        return 1.0 if abs(value - optimum) < 1e-10 else 0.0
    
    deviation = (value - optimum) / width
    return math.exp(-0.5 * deviation * deviation)


def weighted_average(values: List[float], weights: List[float]) -> float:
    """
    Calculate weighted average from lists of values and weights.
    
    Args:
        values: List of values
        weights: List of weights
        
    Returns:
        Weighted average or 0 if no valid weights
    """
    if len(values) != len(weights) or not values:
        return 0.0
    
    total_weighted = sum(v * w for v, w in zip(values, weights) if w > 0)
    total_weights = sum(w for w in weights if w > 0)
    
    return safe_divide(total_weighted, total_weights, 0.0)


def weighted_average_dict(values: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Calculate weighted average from dictionaries of values and weights.
    
    Args:
        values: Dictionary of values
        weights: Dictionary of weights
        
    Returns:
        Weighted average or 0 if no valid weights
    """
    if not values or not weights:
        return 0.0
    
    common_keys = set(values.keys()) & set(weights.keys())
    if not common_keys:
        return 0.0
    
    total_weighted = sum(values[k] * weights[k] for k in common_keys if weights[k] > 0)
    total_weights = sum(weights[k] for k in common_keys if weights[k] > 0)
    
    return safe_divide(total_weighted, total_weights, 0.0)


def calculate_rmse(predicted: List[float], observed: List[float]) -> float:
    """
    Calculate Root Mean Square Error between predicted and observed values.
    
    Args:
        predicted: List of predicted values
        observed: List of observed values
        
    Returns:
        RMSE value
    """
    if len(predicted) != len(observed) or not predicted:
        return float('inf')
    
    squared_errors = [(p - o) ** 2 for p, o in zip(predicted, observed)]
    mean_squared_error = sum(squared_errors) / len(squared_errors)
    
    return math.sqrt(mean_squared_error)


def calculate_percentage_error(predicted: float, observed: float) -> float:
    """
    Calculate percentage error between predicted and observed values.
    
    Args:
        predicted: Predicted value
        observed: Observed value
        
    Returns:
        Percentage error (-100 to +100)
    """
    if abs(observed) < 1e-10:
        return 0.0 if abs(predicted) < 1e-10 else 100.0
    
    return clamp_value(100.0 * (predicted - observed) / observed, -100.0, 100.0)


def moving_average(values: List[float], window_size: int = 3) -> List[float]:
    """
    Calculate moving average of a list of values.
    
    Args:
        values: List of values
        window_size: Size of moving window
        
    Returns:
        List of moving averages
    """
    if not values or window_size < 1:
        return values.copy()
    
    if window_size >= len(values):
        avg = sum(values) / len(values)
        return [avg] * len(values)
    
    result = []
    for i in range(len(values)):
        start_idx = max(0, i - window_size // 2)
        end_idx = min(len(values), i + window_size // 2 + 1)
        window_values = values[start_idx:end_idx]
        result.append(sum(window_values) / len(window_values))
    
    return result


def exponential_decay(initial_value: float, decay_rate: float, time: float) -> float:
    """
    Calculate exponential decay.
    
    Args:
        initial_value: Initial value at time 0
        decay_rate: Decay rate constant
        time: Time elapsed
        
    Returns:
        Value after exponential decay
    """
    return initial_value * math.exp(-decay_rate * time)


def logistic_growth(initial_value: float, carrying_capacity: float, 
                   growth_rate: float, time: float) -> float:
    """
    Calculate logistic growth.
    
    Args:
        initial_value: Initial value
        carrying_capacity: Maximum carrying capacity
        growth_rate: Growth rate constant
        time: Time elapsed
        
    Returns:
        Value after logistic growth
    """
    if initial_value <= 0 or carrying_capacity <= 0:
        return 0.0
    
    try:
        ratio = carrying_capacity / initial_value
        denominator = 1.0 + (ratio - 1.0) * math.exp(-growth_rate * time)
        return carrying_capacity / denominator
    except (OverflowError, ZeroDivisionError):
        return carrying_capacity if time > 0 else initial_value


# Validation functions
def validate_range(value: Union[int, float], min_val: float, max_val: float, 
                  param_name: str = "value") -> float:
    """
    Validate that a value is within the specified range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        param_name: Parameter name for error messages
        
    Returns:
        Validated value as float
        
    Raises:
        TypeError: If value is not numeric
        ValueError: If value is outside range
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f"{param_name} must be numeric, got {type(value).__name__}")
    
    if value < min_val or value > max_val:
        raise ValueError(f"{param_name} must be between {min_val} and {max_val}, got {value}")
    
    return float(value)


def validate_positive(value: Union[int, float], param_name: str = "value") -> float:
    """
    Validate that a value is positive.
    
    Args:
        value: Value to validate
        param_name: Parameter name for error messages
        
    Returns:
        Validated positive value
    """
    return validate_range(value, 0.0, float('inf'), param_name)


def validate_fraction(value: Union[int, float], param_name: str = "value") -> float:
    """
    Validate that a value is a valid fraction (0-1).
    
    Args:
        value: Value to validate
        param_name: Parameter name for error messages
        
    Returns:
        Validated fraction value
    """
    return validate_range(value, 0.0, 1.0, param_name)


def ensure_real(value: Union[int, float, complex]) -> float:
    """
    Ensure a value is real (not complex).
    
    Args:
        value: Input value (int, float, or complex)
        
    Returns:
        Real part of the value as float
    """
    if isinstance(value, complex):
        return float(value.real)
    return float(value)


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file contains mathematical utility functions - the basic mathematical tools used throughout 
the hydroponic simulation. Think of it as a sophisticated calculator toolbox that provides 
safe, reliable mathematical operations specifically designed for biological modeling. It's like 
having a set of specialized tools that prevent mathematical errors and handle edge cases that 
could crash the simulation.

PURPOSE OF MATHEMATICAL UTILITIES:

In plant biology simulations, mathematical calculations can encounter problematic situations:
- Division by zero (like calculating growth rate when time = 0)
- Negative values in square roots (mathematically impossible)
- Values outside realistic biological ranges
- Complex numbers appearing in real-world calculations

These utilities provide "bulletproof" mathematical functions that handle these issues gracefully.

KEY MATHEMATICAL SAFETY FUNCTIONS:

1. clamp_value() & related functions
   - What it does: Forces values to stay within specified limits
   - Example: Ensures stress factors stay between 0-1, never -5 or 300
   - Real-world meaning: Like speed limits on roads - prevents dangerous extremes. 
     In biology, a plant can't be "200% stressed" or have "-30% growth."

2. safe_divide()
   - What it does: Prevents division by zero errors
   - Problem solved: Growth_rate = biomass / time fails when time = 0
   - Solution: Returns a default value when denominator is zero
   - Real-world meaning: Like having a backup plan when a calculation becomes impossible.

3. safe_sqrt()
   - What it does: Handles square roots of negative numbers
   - Problem solved: sqrt(-5) crashes programs
   - Solution: Uses absolute value, so sqrt(-5) becomes sqrt(5)
   - Real-world meaning: Like taking the square root of a measurement - negative distances 
     don't exist physically, so we assume it meant the positive value.

4. safe_log()
   - What it does: Handles logarithms of zero or negative numbers
   - Problem solved: log(0) or log(-3) are mathematically undefined
   - Solution: Returns default value for invalid inputs
   - Real-world meaning: Like measuring pH or growth rates on logarithmic scales - 
     impossible inputs are handled gracefully.

INTERPOLATION AND SCALING FUNCTIONS:

5. linear_interpolate()
   - What it does: Smoothly converts values from one scale to another
   - Example: Convert temperature 15-25°C to growth factor 0.5-1.0
   - Equation: output = out_min + ((value - in_min) / (in_max - in_min)) × (out_max - out_min)
   - Real-world meaning: Like converting between measurement units (inches to centimeters) 
     but for any relationship. Creates smooth transitions instead of sudden jumps.

6. sigmoid_response()
   - What it does: Creates smooth S-shaped curves for biological responses
   - Pattern: Gradual change → rapid change → gradual change again
   - Example: Plant response to increasing nutrient concentration
   - Real-world meaning: Like how your alertness responds to coffee - gradual at first, 
     then rapid effect, then levels off. Many biological processes follow this pattern.

7. gaussian_response()
   - What it does: Creates bell-shaped curves with optimal peaks
   - Pattern: Response peaks at optimal value, decreases as you move away
   - Example: Temperature response (optimal at 22°C, worse at 10°C or 35°C)
   - Real-world meaning: Like performance in sports - there's an optimal training intensity, 
     too little or too much both reduce performance.

STATISTICAL AND ANALYSIS FUNCTIONS:

8. weighted_average()
   - What it does: Calculates averages where some values are more important than others
   - Example: Overall plant stress = (0.4 × water_stress) + (0.3 × temp_stress) + (0.3 × nutrient_stress)
   - Real-world meaning: Like calculating your grade where the final exam counts more 
     than homework assignments.

9. calculate_rmse() - Root Mean Square Error
   - What it does: Measures how accurate predictions are compared to real measurements
   - Lower RMSE = more accurate predictions
   - Real-world meaning: Like measuring how close your GPS estimates are to actual 
     travel times - smaller error means better predictions.

10. moving_average()
    - What it does: Smooths out daily fluctuations by averaging nearby values
    - Example: 3-day moving average of growth rate reduces day-to-day noise
    - Real-world meaning: Like looking at your average weight over a week instead of 
      daily fluctuations - reveals the underlying trend.

BIOLOGICAL GROWTH PATTERNS:

11. exponential_decay()
    - What it does: Models how things decrease over time at a constant rate
    - Equation: value(t) = initial_value × e^(-decay_rate × time)
    - Examples: Radioactive decay, nutrient breakdown, enzyme degradation
    - Real-world meaning: Like how a car depreciates - fastest loss initially, 
      then gradually slowing.

12. logistic_growth()
    - What it does: Models growth that starts slow, accelerates, then levels off
    - Pattern: Slow start → rapid growth → approaching maximum limit
    - Example: Plant biomass growth in limited space
    - Real-world meaning: Like population growth in a city - starts small, grows rapidly 
      with resources available, then slows as space/resources become limited.

VALIDATION FUNCTIONS:

13. validate_range(), validate_positive(), validate_fraction()
    - What they do: Check that input values make biological sense
    - Purpose: Prevent impossible inputs like negative biomass or 150% humidity
    - Real-world meaning: Like quality control inspectors checking that measurements 
      are reasonable before processing.

14. ensure_real()
    - What it does: Converts complex mathematical results back to real numbers
    - Problem: Sometimes calculations produce complex numbers (like 3+2i)
    - Solution: Takes only the real part for biological applications
    - Real-world meaning: Like ignoring the imaginary part of a calculation - 
      plants exist in the real world, not mathematical imaginary space.

PRACTICAL APPLICATIONS:

For Simulation Reliability:
1. **Error Prevention**: Stops simulations from crashing due to mathematical errors
2. **Boundary Enforcement**: Keeps values within biologically realistic ranges
3. **Graceful Degradation**: Handles edge cases without failing completely
4. **Data Quality**: Validates inputs before processing

For Biological Accuracy:
1. **Response Curves**: Models realistic plant responses to environmental factors
2. **Growth Patterns**: Captures natural growth limitations and saturation effects
3. **Stress Integration**: Combines multiple stress factors appropriately
4. **Statistical Analysis**: Validates model predictions against experimental data

For Model Development:
1. **Parameter Fitting**: Helps calibrate models against experimental data
2. **Sensitivity Analysis**: Determines which factors most affect outcomes
3. **Uncertainty Handling**: Manages mathematical uncertainties gracefully
4. **Optimization**: Finds optimal growing conditions mathematically

MATHEMATICAL CONCEPTS EXPLAINED:

Linear vs Non-Linear Responses:
- **Linear**: Output changes proportionally with input (double input = double output)
- **Non-Linear**: Complex relationships (Sigmoid, Gaussian, Exponential)
- **Biology Reality**: Most biological processes are non-linear

Saturation Effects:
- **Concept**: Increasing inputs eventually show diminishing returns
- **Example**: More fertilizer helps up to a point, then becomes toxic
- **Mathematical**: Modeled with sigmoid or logistic functions

Optimization Curves:
- **Bell Curves**: One optimal point with decreasing performance on either side
- **Example**: Temperature response - optimal at 22°C, worse at 10°C or 35°C
- **Mathematical**: Gaussian functions capture this behavior

Error Handling Philosophy:
- **Fail-Safe**: When impossible calculations occur, choose safe defaults
- **Biological Realism**: Replace mathematical artifacts with realistic values
- **Continuous Operation**: Never crash the simulation over mathematical issues

KEY CONCEPTS FOR NON-CODERS:

Robust Programming: Writing code that handles unexpected situations gracefully, 
like designing a bridge that can handle unusual loads without collapsing.

Edge Cases: Unusual situations that might break normal calculations, like what 
happens when you divide by zero or take the square root of a negative number.

Boundary Conditions: The limits of what makes sense in real-world applications, 
like ensuring percentages stay between 0% and 100%.

Response Curves: Mathematical descriptions of how living things respond to changes 
in their environment, usually following predictable patterns.

Statistical Validation: Comparing model predictions with real measurements to 
determine accuracy and reliability.

These mathematical utilities provide the foundation for reliable, accurate simulation 
of plant biology by ensuring that all calculations remain mathematically valid and 
biologically meaningful. They enable sophisticated modeling while preventing the 
computational errors that could compromise simulation accuracy or stability.
"""