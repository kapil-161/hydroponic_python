import math
from typing import Dict, Any, List

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

def calculate_thermal_time(temperature: float, config: Any, method: str = 'linear') -> float:
    """
    Calculate thermal time (growing degree days) for plant development.

    Consolidates all thermal time calculation methods used across models:
    - Linear: Simple base temperature method (T - Tbase)
    - Cardinal: Full cardinal temperature approach with optimal range
    - Scaled: Cardinal with thermal_time_scale factor

    Args:
        temperature: Current temperature (°C).
        config: Configuration with thermal time parameters.
        method: Calculation method ('linear', 'cardinal', 'scaled').

    Returns:
        Thermal time (degree-days).

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If temperature is outside realistic range or method is invalid.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")

    if method not in ['linear', 'cardinal', 'scaled']:
        raise ValueError(f"Invalid thermal time method: {method}. Must be 'linear', 'cardinal', or 'scaled'")

    # Get base parameters (required for all methods)
    base_temp = get_strict_param(config, 'thermal_time', 'base_temp')

    if method == 'linear':
        # Simple linear method: TT = T - Tbase (clamped at max)
        max_temp = get_strict_param(config, 'thermal_time', 'max_temp')

        if temperature <= base_temp:
            return 0.0
        elif temperature >= max_temp:
            return max_temp - base_temp
        return temperature - base_temp

    elif method in ['cardinal', 'scaled']:
        # Cardinal temperature approach: TT = f(T, Tmin, Topt1, Topt2, Tmax)
        opt_temp_min = get_strict_param(config, 'thermal_time', 'optimal_temp_min')
        opt_temp_max = get_strict_param(config, 'thermal_time', 'optimal_temp_max')
        max_temp = get_strict_param(config, 'thermal_time', 'max_temp')

        # Validate parameter order
        if base_temp >= opt_temp_min or opt_temp_min >= opt_temp_max or opt_temp_max >= max_temp:
            raise ValueError("Invalid temperature parameters: base < opt_min < opt_max < max")

        # Calculate thermal time scaling factor
        thermal_scale = 1.0
        if method == 'scaled':
            thermal_scale = get_strict_param(config, 'thermal_time', 'thermal_time_scale')

        # No development outside cardinal range
        if temperature <= base_temp or temperature >= max_temp:
            return 0.0

        # Calculate based on temperature range
        if base_temp < temperature <= opt_temp_min:
            # Increasing efficiency from base to optimal minimum
            efficiency_factor = (temperature - base_temp) / (opt_temp_min - base_temp)
            return (temperature - base_temp) * efficiency_factor * thermal_scale

        elif opt_temp_min < temperature <= opt_temp_max:
            # Maximum efficiency in optimal range
            return (temperature - base_temp) * thermal_scale

        else:  # opt_temp_max < temperature < max_temp
            # Decreasing efficiency from optimal maximum to lethal
            efficiency_factor = (max_temp - temperature) / (max_temp - opt_temp_max)
            return (temperature - base_temp) * efficiency_factor * thermal_scale


def calculate_thermal_time_list(temperature_list: List[float], config: Any, method: str = 'cardinal') -> List[float]:
    """
    Calculate thermal time for a list of temperatures.

    Consolidates list-based thermal time calculations used in leaf development model.

    Args:
        temperature_list: List of daily temperatures (°C).
        config: Configuration with thermal time parameters.
        method: Calculation method ('linear', 'cardinal', 'scaled').

    Returns:
        List of thermal time values.
    """
    return [calculate_thermal_time(temp, config, method) for temp in temperature_list]

def calculate_temperature_factor(temperature: float, config: Any, method: str = 'q10') -> float:
    """
    Calculate temperature response factor for biological processes.

    Consolidates all temperature factor calculation methods used across models:
    - Q10: Standard Q10 model with optimal range (e^(ln(Q10)*(T-Tref)/10))
    - Linear: Simple linear response with optimal range
    - Thermal: Based on thermal time efficiency
    - Clamped: Q10 with hard min/max limits

    Args:
        temperature: Current temperature (°C).
        config: Configuration with temperature factor parameters.
        method: Calculation method ('q10', 'linear', 'thermal', 'clamped').

    Returns:
        Temperature factor (0.0-4.0, depending on method).

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If temperature is outside realistic range or method is invalid.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")

    if method not in ['q10', 'linear', 'thermal', 'clamped']:
        raise ValueError(f"Invalid temperature factor method: {method}. Must be 'q10', 'linear', 'thermal', or 'clamped'")

    if method == 'q10':
        # Standard Q10 model with stress at range limits
        optimal_temp = get_strict_param(config, 'temperature_factor', 'optimal_temp')
        temp_range = get_strict_param(config, 'temperature_factor', 'temp_range')
        q10 = get_strict_param(config, 'temperature_factor', 'q10')

        if temperature <= 0:
            return 0.0

        temp_diff = temperature - optimal_temp
        if abs(temp_diff) < 0.1:
            return 1.0

        factor = q10 ** (temp_diff / 10.0)

        # Apply stress at range limits
        if temp_diff > temp_range:
            stress = 1.0 - ((temp_diff - temp_range) / temp_range) ** 2
            factor *= max(0.0, stress)
        elif temp_diff < -temp_range:
            stress = 1.0 - ((abs(temp_diff) - temp_range) / temp_range) ** 2
            factor *= max(0.0, stress)

        return clamp_value(factor, 0.0, 1.0)

    elif method == 'linear':
        # Simple linear response with optimal range
        optimal_temp = get_strict_param(config, 'temperature_factor', 'optimal_temp')
        temp_sensitivity = get_strict_param(config, 'temperature_factor', 'temperature_sensitivity')
        temp_tolerance = get_strict_param(config, 'temperature_factor', 'temp_tolerance')

        # Check if within optimal range
        if optimal_temp - temp_tolerance <= temperature <= optimal_temp + temp_tolerance:
            return 1.0

        # Linear decline with distance from optimal
        min_factor = get_strict_param(config, 'temperature_factor', 'min_factor')
        temp_deviation = abs(temperature - optimal_temp)
        factor = max(min_factor, 1.0 - temp_deviation * temp_sensitivity)
        return factor

    elif method == 'thermal':
        # Based on thermal time efficiency (uses thermal time calculation)
        max_thermal_time = get_strict_param(config, 'temperature_factor', 'max_thermal_time')

        # Get thermal time for this temperature
        thermal_time = calculate_thermal_time(temperature, config, method='cardinal')

        if max_thermal_time <= 0:
            raise ValueError("Maximum thermal time must be positive")

        return max(0.0, min(1.0, thermal_time / max_thermal_time))

    elif method == 'clamped':
        # Q10 with hard min/max limits (for respiration, root uptake)
        # ALL parameters must come from CSV configuration
        optimal_temp = get_strict_param(config, 'temperature_factor', 'optimal_temp')
        q10 = get_strict_param(config, 'temperature_factor', 'q10')
        min_factor = get_strict_param(config, 'temperature_factor', 'min_factor')
        max_factor = get_strict_param(config, 'temperature_factor', 'max_factor')
        max_temp_threshold = get_strict_param(config, 'temperature_factor', 'max_temp_threshold')
        temp_decay_factor = get_strict_param(config, 'temperature_factor', 'temp_decay_factor')

        # Basic Q10 calculation
        temp_diff = temperature - optimal_temp
        factor = q10 ** (temp_diff / 10.0)

        # Apply hard limits
        factor = max(min_factor, min(max_factor, factor))

        # Apply exponential decay at extreme high temperatures
        if temperature > max_temp_threshold:
            excess_temp = temperature - max_temp_threshold
            factor *= math.exp(-temp_decay_factor * excess_temp)

        return factor

def calculate_temperature_stress_factor(temperature: float, config: Any, method: str = 'linear') -> float:
    """
    Calculate temperature stress factor (0 = severe stress, 1 = optimal).

    Consolidates all temperature stress factor calculation methods:
    - Linear: Standard linear stress model with optimal/stress thresholds
    - Photosynthesis: Specialized for photosynthesis with hardcoded limits replaced by CSV
    - Respiration: Progressive stress levels (moderate/severe thresholds)

    Args:
        temperature: Current temperature (°C).
        config: Configuration with temperature stress parameters.
        method: Calculation method ('linear', 'photosynthesis', 'respiration').

    Returns:
        Stress factor (0.0-1.0 for linear/photosynthesis, 0.0-2.0+ for respiration).

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If temperature is outside realistic range or method is invalid.
    """
    validate_parameter_range(temperature, -50.0, 60.0, "temperature")

    if method not in ['linear', 'photosynthesis', 'respiration']:
        raise ValueError(f"Invalid stress factor method: {method}. Must be 'linear', 'photosynthesis', or 'respiration'")

    if method == 'linear':
        # Standard linear stress model
        optimal_temp_min = get_strict_param(config, 'temperature_stress', 'optimal_temp_min')
        optimal_temp_max = get_strict_param(config, 'temperature_stress', 'optimal_temp_max')
        stress_temp_min = get_strict_param(config, 'temperature_stress', 'stress_temp_min')
        stress_temp_max = get_strict_param(config, 'temperature_stress', 'stress_temp_max')

        if optimal_temp_min <= temperature <= optimal_temp_max:
            return 1.0

        if temperature < optimal_temp_min:
            if temperature <= stress_temp_min:
                return 0.0
            return (temperature - stress_temp_min) / (optimal_temp_min - stress_temp_min)

        if temperature >= stress_temp_max:
            return 0.0
        return (stress_temp_max - temperature) / (stress_temp_max - optimal_temp_max)

    elif method == 'photosynthesis':
        # Photosynthesis-specific stress (removes hardcoded 5.0 and 40.0)
        optimal_temp_min = get_strict_param(config, 'temperature_stress', 'optimal_temp_min')
        optimal_temp_max = get_strict_param(config, 'temperature_stress', 'optimal_temp_max')
        cold_limit = get_strict_param(config, 'temperature_stress', 'photosynthesis_cold_limit')
        heat_limit = get_strict_param(config, 'temperature_stress', 'photosynthesis_heat_limit')
        min_factor = get_strict_param(config, 'temperature_stress', 'min_factor')

        if optimal_temp_min >= optimal_temp_max:
            raise ValueError("optimal_temp_min must be less than optimal_temp_max")

        if temperature < optimal_temp_min:
            return max(min_factor, (temperature - cold_limit) / (optimal_temp_min - cold_limit))
        elif temperature <= optimal_temp_max:
            return 1.0
        else:
            return max(min_factor, (heat_limit - temperature) / (heat_limit - optimal_temp_max))

    elif method == 'respiration':
        # Respiration-specific stress with progressive levels
        optimal_temp = get_strict_param(config, 'temperature_stress', 'optimal_temperature')
        moderate_threshold = get_strict_param(config, 'temperature_stress', 'moderate_stress_threshold')
        severe_threshold = get_strict_param(config, 'temperature_stress', 'severe_stress_threshold')
        moderate_factor = get_strict_param(config, 'temperature_stress', 'moderate_stress_factor')
        severe_base = get_strict_param(config, 'temperature_stress', 'severe_stress_base')
        severe_factor = get_strict_param(config, 'temperature_stress', 'severe_stress_factor')

        temp_deviation = abs(temperature - optimal_temp)

        if temp_deviation <= moderate_threshold:
            return 1.0
        elif temp_deviation <= severe_threshold:
            return 1.0 + moderate_factor * (temp_deviation - moderate_threshold)
        else:
            return severe_base + severe_factor * (temp_deviation - severe_threshold)

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
# Centralized Utility Functions
# =========================

def calculate_dynamic_dry_matter_content(result: Any, plant_part: str, config: Any, strict_validation: bool = True) -> float:
    """
    Calculate dynamic dry matter content based on plant development, environment, and plant part.

    Consolidates dry matter calculations used across data structures and display utilities.
    ALL parameters now come from CSV configuration - no hardcoded values.

    Args:
        result: DailyResults object with plant state
        plant_part: Plant part ('leaf', 'stem', 'shoot', 'root')
        config: Configuration with dry matter parameters
        strict_validation: If True, raises errors for missing parameters

    Returns:
        Fraction (0.0-1.0) of dry matter in fresh weight

    Raises:
        ParameterAccessError: If required parameters are missing.
        ValueError: If plant part is invalid or required fields are missing.
    """
    if plant_part not in ['leaf', 'stem', 'shoot', 'root']:
        raise ValueError("Plant part must be 'leaf', 'stem', 'shoot', or 'root'")

    # Required parameters from result
    day = result.day
    growth_stage = result.growth_stage
    total_biomass = result.total_biomass
    water_stress = result.water_stress
    temperature_stress = result.temperature_stress_factor
    integrated_stress = result.integrated_stress_factor

    # Strict validation
    if strict_validation:
        if day is None:
            raise ValueError("Day must be provided in DailyResults")
        if growth_stage is None:
            raise ValueError("Growth stage must be provided in DailyResults")
        if total_biomass is None:
            raise ValueError("Total biomass must be provided in DailyResults")
        if water_stress is None:
            raise ValueError("Water stress must be provided in DailyResults")
        if temperature_stress is None:
            raise ValueError("Temperature stress factor must be provided in DailyResults")
        if integrated_stress is None:
            raise ValueError("Integrated stress factor must be provided in DailyResults")

    # Get ALL parameters from CSV configuration - no unused variable

    # Base dry matter content by plant part - from CSV
    base_dm = get_strict_param(config, 'dry_matter_parameters', f'base_dry_matter_{plant_part}')

    # Development stage parameters - from CSV
    early_development_days = get_strict_param(config, 'dry_matter_parameters', 'early_development_days')
    mature_development_days = get_strict_param(config, 'dry_matter_parameters', 'mature_development_days')
    early_factor_min = get_strict_param(config, 'dry_matter_parameters', 'early_factor_min')
    late_development_factor = get_strict_param(config, 'dry_matter_parameters', 'late_development_factor')
    late_development_rate = get_strict_param(config, 'dry_matter_parameters', 'late_development_rate')

    # Development factor calculation
    if day <= early_development_days:
        development_factor = early_factor_min + (day / early_development_days) * (1.0 - early_factor_min)
    elif day <= mature_development_days:
        development_factor = 1.0
    else:
        excess_days = day - mature_development_days
        development_factor = 1.0 + min(late_development_factor, excess_days * late_development_rate)

    # Growth stage factor - from CSV
    stage_factor = get_strict_param(config, 'dry_matter_parameters', f'stage_factor_{growth_stage}')

    # Stress effect parameters - from CSV
    water_stress_multiplier = get_strict_param(config, 'dry_matter_parameters', 'water_stress_multiplier')
    temp_stress_multiplier = get_strict_param(config, 'dry_matter_parameters', 'temp_stress_multiplier')
    integrated_stress_multiplier = get_strict_param(config, 'dry_matter_parameters', 'integrated_stress_multiplier')

    # Calculate stress effects
    water_stress_factor = 1.0 + water_stress * water_stress_multiplier
    temp_stress_factor = 1.0 + temperature_stress * temp_stress_multiplier
    stress_factor = 1.0 + integrated_stress * integrated_stress_multiplier

    # Growth rate factor parameters - from CSV
    high_growth_threshold = get_strict_param(config, 'dry_matter_parameters', 'high_growth_threshold')
    low_growth_threshold = get_strict_param(config, 'dry_matter_parameters', 'low_growth_threshold')
    high_growth_factor = get_strict_param(config, 'dry_matter_parameters', 'high_growth_factor')
    low_growth_factor = get_strict_param(config, 'dry_matter_parameters', 'low_growth_factor')

    # Growth rate factor calculation
    biomass_growth_rate = total_biomass / max(1, day)
    if biomass_growth_rate > high_growth_threshold:
        growth_rate_factor = high_growth_factor
    elif biomass_growth_rate < low_growth_threshold:
        growth_rate_factor = low_growth_factor
    else:
        growth_rate_factor = 1.0

    # Plant part adjustment - from CSV
    part_adjustment = get_strict_param(config, 'dry_matter_parameters', f'part_adjustment_{plant_part}')

    # Calculate final dry matter content
    final_dry_matter = (base_dm * development_factor * stage_factor *
                        water_stress_factor * temp_stress_factor * stress_factor *
                        growth_rate_factor * part_adjustment)

    # Biological limits - from CSV
    if plant_part == 'root':
        min_dm = get_strict_param(config, 'dry_matter_parameters', 'root_min_dry_matter')
        max_dm = get_strict_param(config, 'dry_matter_parameters', 'root_max_dry_matter')
    else:
        min_dm = get_strict_param(config, 'dry_matter_parameters', 'shoot_min_dry_matter')
        max_dm = get_strict_param(config, 'dry_matter_parameters', 'shoot_max_dry_matter')

    final_dry_matter = max(min_dm, min(max_dm, final_dry_matter))

    return final_dry_matter

# =========================
# Validation and Testing
# =========================

def quick_validate() -> bool:
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
