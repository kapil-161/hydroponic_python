```python
import math
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import numpy as np

# =========================
# Core Utilities Module
# =========================

class ParameterAccessError(Exception):
    """Custom exception for parameter access errors."""
    pass

class StrictParameterAccessor:
    """
    Strictly access parameters from configuration, enforcing CSV-based inputs.
    No hardcoded defaults or fallbacks allowed.
    """
    
    def __init__(self, config: Any):
        """
        Initialize with configuration object.

        Args:
            config: Configuration object containing parameter categories.
        """
        self.config = config

    def get_category(self, category_name: str) -> Dict[str, Any]:
        """
        Retrieve a parameter category with strict validation.

        Args:
            category_name: Name of the parameter category.

        Returns:
            Dictionary of parameters in the category.

        Raises:
            ParameterAccessError: If category is missing or invalid.
        """
        if not hasattr(self.config, category_name):
            raise ParameterAccessError(
                f"Category '{category_name}' not found in configuration. "
                "Ensure it is defined in master_parameters.csv."
            )
        category_params = getattr(self.config, category_name)
        if not isinstance(category_params, dict) or not category_params:
            raise ParameterAccessError(
                f"Category '{category_name}' is empty or invalid. "
                "Add required parameters to master_parameters.csv."
            )
        return category_params

    def get_param(self, category_name: str, param_name: str) -> Any:
        """
        Retrieve a single parameter with strict validation.

        Args:
            category_name: Name of the parameter category.
            param_name: Name of the parameter.

        Returns:
            Parameter value.

        Raises:
            ParameterAccessError: If parameter is missing or category is invalid.
        """
        category_params = self.get_category(category_name)
        if param_name not in category_params:
            raise ParameterAccessError(
                f"Parameter '{param_name}' not found in category '{category_name}'. "
                "Add it to master_parameters.csv."
            )
        return category_params[param_name]

def get_strict_category(config: Any, category_name: str) -> Dict[str, Any]:
    """
    Retrieve parameter category with strict validation.

    Args:
        config: Configuration object.
        category_name: Name of the parameter category.

    Returns:
        Dictionary of parameters in the category.

    Raises:
        ParameterAccessError: If category is missing or invalid.
    """
    return StrictParameterAccessor(config).get_category(category_name)

def get_strict_param(config: Any, category_name: str, param_name: str) -> Any:
    """
    Retrieve single parameter with strict validation.

    Args:
        config: Configuration object.
        category_name: Name of the parameter category.
        param_name: Name of the parameter.

    Returns:
        Parameter value.

    Raises:
        ParameterAccessError: If parameter or category is missing.
    """
    return StrictParameterAccessor(config).get_param(category_name, param_name)

# =========================
# Common Calculations
# =========================

def calculate_thermal_time(temperature: float, config: Any) -> float:
    """
    Calculate thermal time (growing degree days) for plant development.

    Args:
        temperature: Current temperature (°C).
        config: Configuration with 'environment' category containing 'base_temp', 'max_temp'.

    Returns:
        Thermal time (degree-days).

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If temperature is outside realistic range.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")
    base_temp = get_strict_param(config, 'environment', 'base_temp')
    max_temp = get_strict_param(config, 'environment', 'max_temp')
    
    if temperature <= base_temp:
        return 0.0
    elif temperature >= max_temp:
        return max_temp - base_temp
    return temperature - base_temp

def calculate_temperature_factor(temperature: float, config: Any) -> float:
    """
    Calculate temperature response factor for biological processes using Q10 model.

    Args:
        temperature: Current temperature (°C).
        config: Configuration with 'environment' category containing 'optimal_temp', 'temp_range', 'q10'.

    Returns:
        Temperature factor (0.0-1.0).

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If temperature is outside realistic range.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")
    optimal_temp = get_strict_param(config, 'environment', 'optimal_temp')
    temp_range = get_strict_param(config, 'environment', 'temp_range')
    q10 = get_strict_param(config, 'environment', 'q10')
    
    if temperature <= 0:
        return 0.0
    
    temp_diff = temperature - optimal_temp
    if abs(temp_diff) < 0.1:
        return 1.0
    
    factor = q10 ** (temp_diff / 10.0)
    
    if temp_diff > temp_range:
        stress = 1.0 - ((temp_diff - temp_range) / temp_range) ** 2
        factor *= max(0.0, stress)
    elif temp_diff < -temp_range:
        stress = 1.0 - ((abs(temp_diff) - temp_range) / temp_range) ** 2
        factor *= max(0.0, stress)
    
    return clamp_value(factor, 0.0, 1.0)

def calculate_temperature_stress_factor(temperature: float, config: Any) -> float:
    """
    Calculate temperature stress factor using a linear model (0 = severe stress, 1 = optimal).

    Args:
        temperature: Current temperature (°C).
        config: Configuration with 'environment' category containing 'optimal_temp_min',
                'optimal_temp_max', 'stress_temp_min', 'stress_temp_max'.

    Returns:
        Stress factor (0.0-1.0).

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If temperature is outside realistic range.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")
    optimal_temp_min = get_strict_param(config, 'environment', 'optimal_temp_min')
    optimal_temp_max = get_strict_param(config, 'environment', 'optimal_temp_max')
    stress_temp_min = get_strict_param(config, 'environment', 'stress_temp_min')
    stress_temp_max = get_strict_param(config, 'environment', 'stress_temp_max')
    
    if optimal_temp_min <= temperature <= optimal_temp_max:
        return 1.0
    
    if temperature < optimal_temp_min:
        if temperature <= stress_temp_min:
            return 0.0
        return (temperature - stress_temp_min) / (optimal_temp_min - stress_temp_min)
    
    if temperature >= stress_temp_max:
        return 0.0
    return (stress_temp_max - temperature) / (stress_temp_max - optimal_temp_max)

def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp value to specified range.

    Args:
        value: Value to clamp.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        Clamped value.
    """
    return max(min_val, min(max_val, value))

def calculate_q10_factor(temperature: float, config: Any) -> float:
    """
    Calculate Q10 temperature response factor.

    Args:
        temperature: Current temperature (°C).
        config: Configuration with 'environment' category containing 'reference_temp', 'q10',
                'min_q10_factor', 'max_q10_factor'.

    Returns:
        Q10 factor.

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If temperature is outside realistic range.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")
    reference_temp = get_strict_param(config, 'environment', 'reference_temp')
    q10 = get_strict_param(config, 'environment', 'q10')
    min_q10_factor = get_strict_param(config, 'environment', 'min_q10_factor')
    max_q10_factor = get_strict_param(config, 'environment', 'max_q10_factor')
    
    temp_diff = temperature - reference_temp
    factor = q10 ** (temp_diff / 10.0)
    return clamp_value(factor, min_q10_factor, max_q10_factor)

def calculate_vpd(temperature: float, relative_humidity: float) -> float:
    """
    Calculate vapor pressure deficit (kPa) using Tetens equation.

    Args:
        temperature: Current temperature (°C).
        relative_humidity: Relative humidity (%).

    Returns:
        Vapor pressure deficit (kPa).

    Raises:
        ValueError: If inputs are outside realistic ranges.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")
    validate_parameter_range(relative_humidity, 0.0, 100.0, "relative_humidity")
    
    svp = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
    avp = svp * relative_humidity / 100.0
    return svp - avp

def calculate_ph_effect(ph: float, config: Any) -> float:
    """
    Calculate pH effect factor (0.0-1.0).

    Args:
        ph: Current pH value.
        config: Configuration with 'solution_chemistry' category containing 'optimal_ph_min',
                'optimal_ph_max', 'stress_ph_min', 'stress_ph_max'.

    Returns:
        pH effect factor (0.0-1.0).

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If pH is outside realistic range.
    """
    validate_parameter_range(ph, 0.0, 14.0, "pH")
    optimal_ph_min = get_strict_param(config, 'solution_chemistry', 'optimal_ph_min')
    optimal_ph_max = get_strict_param(config, 'solution_chemistry', 'optimal_ph_max')
    stress_ph_min = get_strict_param(config, 'solution_chemistry', 'stress_ph_min')
    stress_ph_max = get_strict_param(config, 'solution_chemistry', 'stress_ph_max')
    
    if optimal_ph_min <= ph <= optimal_ph_max:
        return 1.0
    
    if ph < optimal_ph_min:
        if ph <= stress_ph_min:
            return 0.0
        return (ph - stress_ph_min) / (optimal_ph_min - stress_ph_min)
    
    if ph >= stress_ph_max:
        return 0.0
    return (stress_ph_max - ph) / (stress_ph_max - optimal_ph_max)

def safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Perform safe division with fallback for zero denominator.

    Args:
        numerator: Numerator value.
        denominator: Denominator value.
        default: Value to return if denominator is near zero.

    Returns:
        Division result or default value.
    """
    if abs(denominator) < 1e-10:
        return default
    return numerator / denominator

def interpolate_linear(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Perform linear interpolation between two points.

    Args:
        x: Input value to interpolate.
        x1, y1: First point coordinates.
        x2, y2: Second point coordinates.

    Returns:
        Interpolated value.
    """
    if abs(x2 - x1) < 1e-10:
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

# =========================
# Weather Interpolation
# =========================

def create_hourly_interpolation(daily_temp_min: float, daily_temp_max: float,
                               daily_humidity: float, daily_solar: float) -> List[Dict[str, float]]:
    """
    Create hourly weather interpolation from daily values.

    Args:
        daily_temp_min: Daily minimum temperature (°C).
        daily_temp_max: Daily maximum temperature (°C).
        daily_humidity: Daily average relative humidity (%).
        daily_solar: Daily total solar radiation (MJ/m²/day).

    Returns:
        List of dictionaries with hourly weather data (temperature, humidity, solar_radiation, vpd).

    Raises:
        ValueError: If inputs are outside realistic ranges.
    """
    validate_parameter_range(daily_temp_min, -50.0, 60.0, "daily_temp_min")
    validate_parameter_range(daily_temp_max, -50.0, 60.0, "daily_temp_max")
    validate_parameter_range(daily_humidity, 0.0, 100.0, "daily_humidity")
    validate_parameter_range(daily_solar, 0.0, 50.0, "daily_solar")
    
    if daily_temp_min > daily_temp_max:
        raise ValueError("Minimum temperature cannot exceed maximum temperature")
    
    hourly_data = []
    for hour in range(24):
        temp_fraction = 0.5 * (1 - math.cos(2 * math.pi * (hour - 6) / 24))
        temperature = daily_temp_min + temp_fraction * (daily_temp_max - daily_temp_min)
        
        solar_radiation = daily_solar * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0.0
        humidity = daily_humidity * (1.2 - 0.4 * temp_fraction)
        
        hourly_data.append({
            'hour': hour,
            'temperature': temperature,
            'humidity': clamp_value(humidity, 0.0, 100.0),
            'solar_radiation': max(0.0, solar_radiation),
            'vpd': calculate_vpd(temperature, humidity)
        })
    
    return hourly_data

# =========================
# Mathematical Utilities
# =========================

def sigmoid(x: float, config: Any) -> float:
    """
    Sigmoid function for smooth transitions.

    Args:
        x: Input value.
        config: Configuration with 'math' category containing 'sigmoid_midpoint', 'sigmoid_steepness'.

    Returns:
        Sigmoid output (0.0-1.0).

    Raises:
        ParameterAccessError: If required parameters are missing.
    """
    midpoint = get_strict_param(config, 'math', 'sigmoid_midpoint')
    steepness = get_strict_param(config, 'math', 'sigmoid_steepness')
    
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
    except OverflowError:
        return 0.0 if x < midpoint else 1.0

def gaussian(x: float, config: Any) -> float:
    """
    Gaussian function for normal distributions.

    Args:
        x: Input value.
        config: Configuration with 'math' category containing 'gaussian_mean', 'gaussian_std_dev'.

    Returns:
        Gaussian output.

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If standard deviation is non-positive.
    """
    mean = get_strict_param(config, 'math', 'gaussian_mean')
    std_dev = get_strict_param(config, 'math', 'gaussian_std_dev')
    
    if std_dev <= 0:
        raise ValueError("Standard deviation must be positive")
    
    return math.exp(-0.5 * ((x - mean) / std_dev) ** 2)

def exponential_decay(x: float, config: Any) -> float:
    """
    Exponential decay function.

    Args:
        x: Input value.
        config: Configuration with 'math' category containing 'decay_rate', 'initial_value'.

    Returns:
        Decay output.

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If decay rate is negative.
    """
    decay_rate = get_strict_param(config, 'math', 'decay_rate')
    initial_value = get_strict_param(config, 'math', 'initial_value')
    
    if decay_rate < 0:
        raise ValueError("Decay rate must be non-negative")
    
    return initial_value * math.exp(-decay_rate * x)

def scale_linear(value: float, in_min: float, in_max: float, out_min: float = 0.0, out_max: float = 1.0) -> float:
    """
    Scale value from input range to output range.

    Args:
        value: Value to scale.
        in_min: Input range minimum.
        in_max: Input range maximum.
        out_min: Output range minimum.
        out_max: Output range maximum.

    Returns:
        Scaled value.

    Raises:
        ValueError: If input range is invalid.
    """
    if in_max == in_min:
        raise ValueError("Input range minimum and maximum cannot be equal")
    
    scaled = (value - in_min) / (in_max - in_min)
    return out_min + scaled * (out_max - out_min)

# =========================
# Parameter Validation
# =========================

def validate_parameter_range(value: float, min_val: float, max_val: float, param_name: str) -> None:
    """
    Validate parameter is within realistic range.

    Args:
        value: Parameter value.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.
        param_name: Parameter name for error message.

    Raises:
        ValueError: If value is outside specified range.
    """
    if not (min_val <= value <= max_val):
        raise ValueError(f"Parameter '{param_name}' ({value}) outside range [{min_val}, {max_val}]")

def validate_allocation_fractions(fractions: Dict[str, float], tolerance: float = 0.05) -> None:
    """
    Validate allocation fractions sum to approximately 1.0.

    Args:
        fractions: Dictionary of allocation fractions.
        tolerance: Allowed deviation from 1.0.

    Raises:
        ValueError: If fractions sum is outside tolerance.
    """
    total = sum(fractions.values())
    if not (1.0 - tolerance <= total <= 1.0 + tolerance):
        raise ValueError(f"Allocation fractions sum to {total:.3f}, expected 1.0 ± {tolerance}")

# =========================
# Results Formatting
# =========================

def format_scientific(value: float, precision: int = 3) -> str:
    """
    Format number in scientific notation if needed.

    Args:
        value: Value to format.
        precision: Number of decimal places.

    Returns:
        Formatted string.
    """
    if value is None or math.isnan(value):
        return "N/A"
    if abs(value) < 0.001 or abs(value) >= 1000:
        return f"{value:.{precision}e}"
    return f"{value:.{precision}f}"

def create_summary_table(data: Dict[str, float], title: str = "Results") -> str:
    """
    Create formatted summary table.

    Args:
        data: Dictionary of results.
        title: Table title.

    Returns:
        Formatted string table.
    """
    lines = [f"{title}:", "=" * len(title)]
    for key, value in data.items():
        formatted_value = format_scientific(value)
        lines.append(f"  {key:<25} {formatted_value:>15}")
    return "\n".join(lines)

# =========================
# Configuration Utilities
# =========================

def extract_config_subset(config: Any, category_name: str, parameter_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract subset of parameters with name mapping.

    Args:
        config: Configuration object.
        category_name: Name of the parameter category.
        parameter_mapping: Mapping of internal names to CSV names.

    Returns:
        Dictionary of extracted parameters.

    Raises:
        ParameterAccessError: If required parameters are missing.
    """
    category_params = get_strict_category(config, category_name)
    extracted_params = {}
    missing_params = []
    
    for internal_name, csv_name in parameter_mapping.items():
        if csv_name in category_params:
            extracted_params[internal_name] = category_params[csv_name]
        else:
            missing_params.append(csv_name)
    
    if missing_params:
        raise ParameterAccessError(
            f"Missing parameters in {category_name}: {missing_params}. "
            "Add them to master_parameters.csv."
        )
    
    return extracted_params

# =========================
# Validation and Testing
# =========================

def quick_validate(config: Optional[Any] = None) -> bool:
    """
    Perform minimal validation of core functions.

    Args:
        config: Configuration object (optional for basic checks).

    Returns:
        True if core functions pass, False otherwise.
    """
    try:
        # Mock config for testing
        mock_config = {
            'environment': {
                'base_temp': 10.0,
                'max_temp': 40.0,
                'optimal_temp': 22.0,
                'temp_range': 10.0,
                'q10': 2.0,
                'reference_temp': 25.0,
                'min_q10_factor': 0.1,
                'max_q10_factor': 4.0,
                'optimal_temp_min': 18.0,
                'optimal_temp_max': 24.0,
                'stress_temp_min': 10.0,
                'stress_temp_max': 35.0
            },
            'solution_chemistry': {
                'optimal_ph_min': 5.5,
                'optimal_ph_max': 6.5,
                'stress_ph_min': 4.0,
                'stress_ph_max': 8.0
            }
        }
        
        # Test core calculations
        vpd = calculate_vpd(25.0, 60.0)
        gdd = calculate_thermal_time(25.0, mock_config)
        temp_factor = calculate_temperature_factor(22.0, mock_config)
        temp_stress = calculate_temperature_stress_factor(22.0, mock_config)
        
        # Basic sanity checks
        if not (0.8 <= vpd <= 1.4):
            return False
        if gdd != 15.0:
            return False
        if not (0.8 <= temp_factor <= 1.2):
            return False
        if temp_stress != 1.0:
            return False
        
        return True
    except:
        return False

def check_critical_params(config: Any) -> List[str]:
    """
    Check for critical parameters, returning missing ones.

    Args:
        config: Configuration object.

    Returns:
        List of missing parameter names.
    """
    critical_params = [
        ('photosynthesis_parameters', 'jmax_25'),
        ('photosynthesis_parameters', 'vcmax_25'),
        ('water_parameters', 'base_crop_coefficient'),
        ('environment', 'optimal_temperature_min')
    ]
    missing = []
    
    for category, param in critical_params:
        try:
            get_strict_param(config, category, param)
        except ParameterAccessError:
            missing.append(f"{category}.{param}")
    
    return missing
