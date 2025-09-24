"""
Core Utilities Module - No hardcoded defaults allowed and no fallback to simple alternative codes

Consolidated utility functions to reduce file count.
Contains all essential calculations and helper functions.
"""

import math
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, fields, MISSING

# =============================================================================
# STRICT PARAMETER ACCESS
# =============================================================================

class StrictParameterAccessor:
    """Strict parameter accessor that requires all parameters to exist in CSV."""

    def __init__(self, system_config: Any):
        self.system_config = system_config

    def get_required_category(self, category_name: str) -> Dict[str, Any]:
        """Get required parameter category from CSV configuration."""
        if not hasattr(self.system_config, category_name):
            raise ValueError(
                f"❌ Required parameter category '{category_name}' not found in CSV configuration. "
                f"Please ensure this category exists in your master_parameters.csv file."
            )

        category_params = getattr(self.system_config, category_name)
        if not isinstance(category_params, dict) or not category_params:
            raise ValueError(
                f"❌ Parameter category '{category_name}' is empty in CSV configuration. "
                f"Please add required parameters to this category in your master_parameters.csv file."
            )

        return category_params

    def get_required_param(self, category_name: str, param_name: str) -> Any:
        """Get required parameter value from CSV configuration."""
        category_params = self.get_required_category(category_name)

        if param_name not in category_params:
            raise ValueError(
                f"❌ Required parameter '{param_name}' not found in category '{category_name}'. "
                f"Please add this parameter to your master_parameters.csv file."
            )

        return category_params[param_name]


def get_strict_category(system_config: Any, category_name: str) -> Dict[str, Any]:
    """Get parameter category with strict validation - no fallbacks."""
    accessor = StrictParameterAccessor(system_config)
    return accessor.get_required_category(category_name)


def get_strict_param(system_config: Any, category_name: str, param_name: str) -> Any:
    """Get single parameter with strict validation - no fallbacks."""
    accessor = StrictParameterAccessor(system_config)
    return accessor.get_required_param(category_name, param_name)


# =============================================================================
# COMMON CALCULATIONS
# =============================================================================

def calculate_thermal_time(temperature: float, base_temp: float = 0.0, max_temp: float = 40.0) -> float:
    """Calculate thermal time (growing degree days) for plant development."""
    if temperature <= base_temp:
        return 0.0
    elif temperature >= max_temp:
        return max_temp - base_temp
    else:
        return temperature - base_temp


def calculate_temperature_factor(temperature: float, optimal_temp: float,
                               temp_range: float = 10.0, q10: float = 2.0) -> float:
    """Calculate temperature response factor for biological processes."""
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

    return max(0.0, min(1.0, factor))


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to specified range."""
    return max(min_val, min(max_val, value))


def calculate_q10_factor(temperature: float, reference_temp: float = 25.0, q10: float = 2.0) -> float:
    """Calculate Q10 temperature response factor."""
    temp_diff = temperature - reference_temp
    return q10 ** (temp_diff / 10.0)


def calculate_vpd(temperature: float, relative_humidity: float) -> float:
    """Calculate vapor pressure deficit (kPa)."""
    # Saturation vapor pressure (kPa)
    svp = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
    # Actual vapor pressure (kPa)
    avp = svp * relative_humidity / 100.0
    # VPD (kPa)
    return svp - avp


def calculate_ph_effect(ph: float, optimal_ph: float = 6.0, tolerance: float = 1.0) -> float:
    """Calculate pH effect factor (0-1)."""
    ph_diff = abs(ph - optimal_ph)
    if ph_diff <= tolerance:
        return 1.0 - (ph_diff / tolerance) * 0.5
    else:
        return max(0.0, 0.5 - (ph_diff - tolerance) * 0.2)


def safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Perform safe division with fallback for zero denominator."""
    if abs(denominator) < 1e-10:
        return default
    return numerator / denominator


def interpolate_linear(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Linear interpolation between two points."""
    if abs(x2 - x1) < 1e-10:
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)


# =============================================================================
# WEATHER INTERPOLATION
# =============================================================================

def create_hourly_interpolation(daily_temp_min: float, daily_temp_max: float,
                               daily_humidity: float, daily_solar: float) -> List[Dict]:
    """Create hourly weather interpolation from daily values."""
    hourly_data = []

    for hour in range(24):
        # Temperature varies sinusoidally through the day
        temp_fraction = 0.5 * (1 - math.cos(2 * math.pi * (hour - 6) / 24))
        temperature = daily_temp_min + temp_fraction * (daily_temp_max - daily_temp_min)

        # Solar radiation varies with daylight hours
        if 6 <= hour <= 18:
            solar_fraction = math.sin(math.pi * (hour - 6) / 12)
            solar_radiation = daily_solar * solar_fraction
        else:
            solar_radiation = 0.0

        # Humidity inversely related to temperature
        humidity = daily_humidity * (1.2 - 0.4 * temp_fraction)

        hourly_data.append({
            'hour': hour,
            'temperature': temperature,
            'humidity': humidity,
            'solar_radiation': solar_radiation,
            'vpd': calculate_vpd(temperature, humidity)
        })

    return hourly_data


# =============================================================================
# MATHEMATICAL UTILITIES
# =============================================================================

def sigmoid(x: float, midpoint: float = 0.0, steepness: float = 1.0) -> float:
    """Sigmoid function for smooth transitions."""
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
    except OverflowError:
        return 0.0 if x < midpoint else 1.0


def gaussian(x: float, mean: float, std_dev: float) -> float:
    """Gaussian function for normal distributions."""
    return math.exp(-0.5 * ((x - mean) / std_dev) ** 2)


def exponential_decay(x: float, decay_rate: float, initial_value: float = 1.0) -> float:
    """Exponential decay function."""
    return initial_value * math.exp(-decay_rate * x)


def scale_linear(value: float, in_min: float, in_max: float,
                out_min: float = 0.0, out_max: float = 1.0) -> float:
    """Scale value from input range to output range."""
    if in_max == in_min:
        return out_min

    scaled = (value - in_min) / (in_max - in_min)
    return out_min + scaled * (out_max - out_min)


# =============================================================================
# PARAMETER VALIDATION
# =============================================================================

def validate_parameter_range(value: float, min_val: float, max_val: float,
                            param_name: str) -> None:
    """Validate parameter is within scientific range."""
    if not (min_val <= value <= max_val):
        raise ValueError(
            f"❌ Parameter '{param_name}' ({value}) outside realistic range ({min_val}-{max_val})"
        )


def validate_allocation_fractions(fractions: Dict[str, float], tolerance: float = 0.05) -> None:
    """Validate allocation fractions sum to 1.0."""
    total = sum(fractions.values())
    if not (1.0 - tolerance <= total <= 1.0 + tolerance):
        raise ValueError(
            f"❌ Allocation fractions sum to {total:.3f}, should sum to 1.0 ± {tolerance}"
        )


# =============================================================================
# RESULTS FORMATTING
# =============================================================================

def format_scientific(value: float, precision: int = 3) -> str:
    """Format number in scientific notation if needed."""
    if abs(value) < 0.001 or abs(value) >= 1000:
        return f"{value:.{precision}e}"
    else:
        return f"{value:.{precision}f}"


def create_summary_table(data: Dict[str, float], title: str = "Results") -> str:
    """Create formatted summary table."""
    lines = [f"{title}:", "=" * len(title)]

    for key, value in data.items():
        formatted_value = format_scientific(value)
        lines.append(f"  {key:<25} {formatted_value:>15}")

    return "\n".join(lines)


# =============================================================================
# DAILY UPDATE BASE CLASS
# =============================================================================

@dataclass
class DailyUpdateInput:
    """Standard input data structure for daily model updates."""
    day: int
    temperature: float
    humidity: float
    solar_radiation: float
    daylength: float
    vpd: float
    co2_concentration: float
    ph: float
    ec: float
    nutrient_concentrations: Dict[str, float]
    biomass_state: Dict[str, float]
    stress_factors: Dict[str, float]
    environmental_conditions: Dict[str, Any]


@dataclass
class DailyUpdateOutput:
    """Standard output data structure for daily model updates."""
    success: bool
    updated_state: Dict[str, Any]
    calculated_values: Dict[str, float]
    warnings: list = None
    errors: list = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


# =============================================================================
# CONFIGURATION UTILITIES
# =============================================================================

def extract_config_subset(system_config: Any, category_name: str,
                         parameter_mapping: Dict[str, str]) -> Dict[str, Any]:
    """Extract subset of parameters from system configuration with name mapping."""
    category_params = get_strict_category(system_config, category_name)

    extracted_params = {}
    missing_params = []

    for internal_name, csv_name in parameter_mapping.items():
        if csv_name in category_params:
            extracted_params[internal_name] = category_params[csv_name]
        else:
            missing_params.append(csv_name)

    if missing_params:
        raise ValueError(
            f"❌ Missing required parameters in {category_name}: {missing_params}. "
            f"Please add these parameters to your master_parameters.csv file."
        )

    return extracted_params


# =============================================================================
# MINIMAL VALIDATION & TESTING (Essential only)
# =============================================================================

def quick_validate(config_df=None) -> bool:
    """Ultra-minimal validation - just check core functions work"""
    try:
        # Test core calculations
        vpd = calculate_vpd(25.0, 60.0)  # Should be ~1.27 kPa
        gdd = calculate_thermal_time(25.0, 10.0)  # Should be 15
        temp_factor = calculate_temperature_factor(22.0, 22.0)  # Should be ~1.0

        # Basic sanity checks
        if not (0.8 <= vpd <= 1.4): return False
        if gdd != 15.0: return False
        if not (0.8 <= temp_factor <= 1.2): return False

        return True
    except:
        return False

def check_critical_params(system_config) -> List[str]:
    """Check if critical parameters exist - return list of missing ones"""
    critical = ['jmax_25', 'vcmax_25', 'base_crop_coefficient', 'optimal_temperature_min']
    missing = []

    try:
        # Check photosynthesis category
        photo_params = get_strict_category(system_config, 'photosynthesis_parameters')
        if 'jmax_25' not in photo_params: missing.append('jmax_25')
        if 'vcmax_25' not in photo_params: missing.append('vcmax_25')

        # Check water category
        water_params = get_strict_category(system_config, 'water_parameters')
        if 'base_crop_coefficient' not in water_params: missing.append('base_crop_coefficient')

        # Check environment category
        env_params = get_strict_category(system_config, 'environment')
        if 'optimal_temperature_min' not in env_params: missing.append('optimal_temperature_min')

    except Exception as e:
        missing.append(f"Config access error: {str(e)}")

    return missing