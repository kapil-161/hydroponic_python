from typing import Dict, Any
from dataclasses import dataclass
import math

@dataclass
class RZTParameters:
    """Parameters for root zone temperature model."""
    optimal_rzt_offset: float  # °C above air temperature
    min_effective_rzt: float  # °C
    max_effective_rzt: float  # °C
    linear_growth_slope: float  # Growth factor per °C below optimum
    rapid_decline_slope: float  # Decline factor per °C above optimum
    base_growth_factor: float  # Baseline at optimal temperature
    nutrient_uptake_sensitivity_low: float  # per °C below optimum
    nutrient_uptake_sensitivity_high: float  # per °C above optimum
    water_uptake_sensitivity_low: float  # per °C below optimum
    water_uptake_sensitivity_high: float  # per °C above optimum
    photosynthesis_sensitivity_low: float  # per °C below optimum
    photosynthesis_sensitivity_high: float  # per °C above optimum
    root_metabolism_sensitivity_low: float  # per °C below optimum
    root_metabolism_sensitivity_high: float  # per °C above optimum
    min_growth_factor: float  # Minimum growth factor below effective temperature
    max_growth_factor: float  # Maximum growth factor
    min_nutrient_uptake_factor: float  # Minimum nutrient uptake factor
    max_nutrient_uptake_factor: float  # Maximum nutrient uptake factor
    min_water_uptake_factor: float  # Minimum water uptake factor
    max_water_uptake_factor: float  # Maximum water uptake factor
    min_photosynthesis_factor: float  # Minimum photosynthesis factor
    max_photosynthesis_factor: float  # Maximum photosynthesis factor
    min_root_metabolism_factor: float  # Minimum root metabolism factor
    max_root_metabolism_factor: float  # Maximum root metabolism factor
    thermal_mass_factor: float  # How quickly RZT responds to changes
    ambient_temp_amplitude: float  # Amplitude of diurnal temperature variation
    root_respiration_heat: float  # Heat generation from root respiration
    pump_heat_generation: float  # Heat generation from circulation pumps
    ambient_exchange_factor: float  # Factor for ambient temperature exchange
    thermal_response_time: float  # Thermal response time constant (hours)
    heat_transfer_coefficient: float  # Heat transfer coefficient for calculations
    base_factor_constant: float  # Base constant for factor calculations
    thermal_stress_normalizer: float  # Thermal stress normalization factor
    diurnal_cycle_shift: int  # Hour shift for diurnal temperature cycle
    diurnal_cycle_period: int  # Period of diurnal temperature cycle
    daily_representative_hour: int  # Representative hour for daily calculations

    def __post_init__(self):
        if any(x is None for x in [
            self.optimal_rzt_offset, self.min_effective_rzt, self.max_effective_rzt,
            self.linear_growth_slope, self.rapid_decline_slope, self.base_growth_factor,
            self.nutrient_uptake_sensitivity_low, self.nutrient_uptake_sensitivity_high,
            self.water_uptake_sensitivity_low, self.water_uptake_sensitivity_high,
            self.photosynthesis_sensitivity_low, self.photosynthesis_sensitivity_high,
            self.root_metabolism_sensitivity_low, self.root_metabolism_sensitivity_high,
            self.min_growth_factor, self.max_growth_factor, self.min_nutrient_uptake_factor,
            self.max_nutrient_uptake_factor, self.min_water_uptake_factor, self.max_water_uptake_factor,
            self.min_photosynthesis_factor, self.max_photosynthesis_factor,
            self.min_root_metabolism_factor, self.max_root_metabolism_factor,
            self.thermal_mass_factor, self.ambient_temp_amplitude, self.root_respiration_heat,
            self.pump_heat_generation, self.ambient_exchange_factor, self.thermal_response_time,
            self.heat_transfer_coefficient, self.base_factor_constant, self.thermal_stress_normalizer,
            self.diurnal_cycle_shift, self.diurnal_cycle_period, self.daily_representative_hour
        ]):
            raise ValueError("All RZTParameters fields must be provided")
        if self.min_effective_rzt >= self.max_effective_rzt:
            raise ValueError("min_effective_rzt must be less than max_effective_rzt")
        if self.linear_growth_slope < 0 or self.rapid_decline_slope < 0:
            raise ValueError("linear_growth_slope and rapid_decline_slope must be non-negative")
        if self.min_growth_factor >= self.max_growth_factor:
            raise ValueError("min_growth_factor must be less than max_growth_factor")
        if any(min_val >= max_val for min_val, max_val in [
            (self.min_nutrient_uptake_factor, self.max_nutrient_uptake_factor),
            (self.min_water_uptake_factor, self.max_water_uptake_factor),
            (self.min_photosynthesis_factor, self.max_photosynthesis_factor),
            (self.min_root_metabolism_factor, self.max_root_metabolism_factor)
        ]):
            raise ValueError("Minimum factors must be less than maximum factors")
        if self.thermal_response_time <= 0:
            raise ValueError("thermal_response_time must be positive")
        if self.heat_transfer_coefficient < 0:
            raise ValueError("heat_transfer_coefficient must be non-negative")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'RZTParameters':
        """Create RZTParameters from configuration dictionary."""
        required_params = [
            'optimal_rzt_offset', 'min_effective_rzt', 'max_effective_rzt',
            'linear_growth_slope', 'rapid_decline_slope', 'base_growth_factor',
            'nutrient_uptake_sensitivity_low', 'nutrient_uptake_sensitivity_high',
            'water_uptake_sensitivity_low', 'water_uptake_sensitivity_high',
            'photosynthesis_sensitivity_low', 'photosynthesis_sensitivity_high',
            'root_metabolism_sensitivity_low', 'root_metabolism_sensitivity_high',
            'min_growth_factor', 'max_growth_factor', 'min_nutrient_uptake_factor',
            'max_nutrient_uptake_factor', 'min_water_uptake_factor', 'max_water_uptake_factor',
            'min_photosynthesis_factor', 'max_photosynthesis_factor',
            'min_root_metabolism_factor', 'max_root_metabolism_factor',
            'thermal_mass_factor', 'ambient_temp_amplitude', 'root_respiration_heat',
            'pump_heat_generation', 'ambient_exchange_factor', 'thermal_response_time',
            'heat_transfer_coefficient', 'base_factor_constant', 'thermal_stress_normalizer',
            'diurnal_cycle_shift', 'diurnal_cycle_period', 'daily_representative_hour'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")
        return cls(
            optimal_rzt_offset=float(config['optimal_rzt_offset']),
            min_effective_rzt=float(config['min_effective_rzt']),
            max_effective_rzt=float(config['max_effective_rzt']),
            linear_growth_slope=float(config['linear_growth_slope']),
            rapid_decline_slope=float(config['rapid_decline_slope']),
            base_growth_factor=float(config['base_growth_factor']),
            nutrient_uptake_sensitivity_low=float(config['nutrient_uptake_sensitivity_low']),
            nutrient_uptake_sensitivity_high=float(config['nutrient_uptake_sensitivity_high']),
            water_uptake_sensitivity_low=float(config['water_uptake_sensitivity_low']),
            water_uptake_sensitivity_high=float(config['water_uptake_sensitivity_high']),
            photosynthesis_sensitivity_low=float(config['photosynthesis_sensitivity_low']),
            photosynthesis_sensitivity_high=float(config['photosynthesis_sensitivity_high']),
            root_metabolism_sensitivity_low=float(config['root_metabolism_sensitivity_low']),
            root_metabolism_sensitivity_high=float(config['root_metabolism_sensitivity_high']),
            min_growth_factor=float(config['min_growth_factor']),
            max_growth_factor=float(config['max_growth_factor']),
            min_nutrient_uptake_factor=float(config['min_nutrient_uptake_factor']),
            max_nutrient_uptake_factor=float(config['max_nutrient_uptake_factor']),
            min_water_uptake_factor=float(config['min_water_uptake_factor']),
            max_water_uptake_factor=float(config['max_water_uptake_factor']),
            min_photosynthesis_factor=float(config['min_photosynthesis_factor']),
            max_photosynthesis_factor=float(config['max_photosynthesis_factor']),
            min_root_metabolism_factor=float(config['min_root_metabolism_factor']),
            max_root_metabolism_factor=float(config['max_root_metabolism_factor']),
            thermal_mass_factor=float(config['thermal_mass_factor']),
            ambient_temp_amplitude=float(config['ambient_temp_amplitude']),
            root_respiration_heat=float(config['root_respiration_heat']),
            pump_heat_generation=float(config['pump_heat_generation']),
            ambient_exchange_factor=float(config['ambient_exchange_factor']),
            thermal_response_time=float(config['thermal_response_time']),
            heat_transfer_coefficient=float(config['heat_transfer_coefficient']),
            base_factor_constant=float(config['base_factor_constant']),
            thermal_stress_normalizer=float(config['thermal_stress_normalizer']),
            diurnal_cycle_shift=int(config['diurnal_cycle_shift']),
            diurnal_cycle_period=int(config['diurnal_cycle_period']),
            daily_representative_hour=int(config['daily_representative_hour'])
        )

@dataclass
class RZTModelOutput:
    """Output structure for root zone temperature model calculations."""
    current_rzt: float  # Current root zone temperature (°C)
    optimal_rzt: float  # Optimal root zone temperature (°C)
    rzt_deviation: float  # Deviation from optimal RZT (°C)
    growth_factor: float  # Growth factor due to RZT
    nutrient_uptake_factor: float  # Nutrient uptake efficiency factor
    water_uptake_factor: float  # Water uptake capacity factor
    photosynthesis_factor: float  # Photosynthesis efficiency factor
    root_metabolism_factor: float  # Root metabolism activity factor
    thermal_stress: float  # Normalized thermal stress
    target_rzt: float  # Target RZT considering heat sources (°C)
    thermal_lag: float  # Difference between current and target RZT (°C)
    heat_transfer_rate: float  # Heat transfer rate (W/m²)
    heating_required: float  # Heating needed to reach target RZT (°C)
    cooling_required: float  # Cooling needed to reach target RZT (°C)

class RootZoneTemperatureModel:
    """
    Model for root zone temperature effects on hydroponic plant growth.

    Implements temperature-dependent factors affecting:
    1. Root physiological processes
    2. Nutrient uptake efficiency
    3. Water uptake capacity
    4. Photosynthesis efficiency
    5. Root metabolism

    Based on scientific findings:
    - Linear growth increase up to optimum temperature (typically 3°C above air temperature)
    - Rapid decline beyond optimum
    - RZT affects nutrient uptake (Mg, K, Fe, Cu, Se, Rb), water uptake, photosynthesis, and root metabolism
    """
    def __init__(self, parameters: RZTParameters):
        if not isinstance(parameters, RZTParameters):
            raise ValueError("RZTParameters must be provided")
        self.params = parameters
        self._previous_rzt: float = None  # Initialize as None, set in first update

    def calculate_optimal_rzt(self, air_temperature: float) -> float:
        """
        Calculate optimal root zone temperature based on air temperature.

        Args:
            air_temperature: Air temperature (°C)

        Returns:
            Optimal RZT (°C)
        """
        if air_temperature is None:
            raise ValueError("air_temperature must be provided")
        optimal_rzt = air_temperature + self.params.optimal_rzt_offset
        return max(self.params.min_effective_rzt, min(self.params.max_effective_rzt, optimal_rzt))

    def calculate_rzt_growth_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT-based growth factor:
        - Linear increase up to optimum
        - Rapid decline beyond optimum

        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)

        Returns:
            Growth factor
        """
        if current_rzt is None or air_temperature is None:
            raise ValueError("current_rzt and air_temperature must be provided")
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        if current_rzt <= optimal_rzt:
            if current_rzt >= self.params.min_effective_rzt:
                temperature_diff = optimal_rzt - current_rzt
                factor = self.params.base_growth_factor + (temperature_diff * self.params.linear_growth_slope)
            else:
                factor = self.params.min_growth_factor
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = self.params.base_growth_factor - (temperature_excess * self.params.rapid_decline_slope)
        return max(self.params.min_growth_factor, min(self.params.max_growth_factor, factor))

    def calculate_nutrient_uptake_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on nutrient uptake efficiency (affects Mg, K, Fe, Cu, Se, Rb).

        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)

        Returns:
            Nutrient uptake efficiency factor
        """
        if current_rzt is None or air_temperature is None:
            raise ValueError("current_rzt and air_temperature must be provided")
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = self.params.base_factor_constant + (temperature_diff * self.params.nutrient_uptake_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = self.params.base_factor_constant - (temperature_excess * self.params.nutrient_uptake_sensitivity_high)
        return max(self.params.min_nutrient_uptake_factor, min(self.params.max_nutrient_uptake_factor, factor))

    def calculate_water_uptake_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on water uptake capacity.

        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)

        Returns:
            Water uptake factor
        """
        if current_rzt is None or air_temperature is None:
            raise ValueError("current_rzt and air_temperature must be provided")
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = self.params.base_factor_constant + (temperature_diff * self.params.water_uptake_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = self.params.base_factor_constant - (temperature_excess * self.params.water_uptake_sensitivity_high)
        return max(self.params.min_water_uptake_factor, min(self.params.max_water_uptake_factor, factor))

    def calculate_photosynthesis_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on photosynthesis and assimilate distribution.

        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)

        Returns:
            Photosynthesis factor
        """
        if current_rzt is None or air_temperature is None:
            raise ValueError("current_rzt and air_temperature must be provided")
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = self.params.base_factor_constant + (temperature_diff * self.params.photosynthesis_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = self.params.base_factor_constant - (temperature_excess * self.params.photosynthesis_sensitivity_high)
        return max(self.params.min_photosynthesis_factor, min(self.params.max_photosynthesis_factor, factor))

    def calculate_root_metabolism_factor(self, current_rzt: float, air_temperature: float) -> float:
        """
        Calculate RZT effect on root metabolism and activity.

        Args:
            current_rzt: Current root zone temperature (°C)
            air_temperature: Current air temperature (°C)

        Returns:
            Root metabolism factor
        """
        if current_rzt is None or air_temperature is None:
            raise ValueError("current_rzt and air_temperature must be provided")
        optimal_rzt = self.calculate_optimal_rzt(air_temperature)
        if current_rzt <= optimal_rzt:
            temperature_diff = optimal_rzt - current_rzt
            factor = self.params.base_factor_constant + (temperature_diff * self.params.root_metabolism_sensitivity_low)
        else:
            temperature_excess = current_rzt - optimal_rzt
            factor = self.params.base_factor_constant - (temperature_excess * self.params.root_metabolism_sensitivity_high)
        return max(self.params.min_root_metabolism_factor, min(self.params.max_root_metabolism_factor, factor))

    def calculate_thermal_dynamics(self, air_temp: float, solution_temp: float, hour: int, dt_hours: float) -> Dict[str, float]:
        """
        Calculate thermal dynamics in the hydroponic system.

        Factors affecting root zone temperature:
        - Solution temperature (direct contact)
        - Air temperature (convective exchange)
        - Thermal mass of system
        - External ambient conditions

        Args:
            air_temp: Air temperature (°C)
            solution_temp: Solution temperature (°C)
            hour: Hour of day (0-23)
            dt_hours: Time step in hours

        Returns:
            Dictionary with thermal dynamics metrics
        """
        if any(x is None for x in [air_temp, solution_temp, hour, dt_hours]):
            raise ValueError("air_temp, solution_temp, hour, and dt_hours must be provided")
        if dt_hours <= 0:
            raise ValueError("dt_hours must be positive")
        if not 0 <= hour <= 23:
            raise ValueError("hour must be between 0 and 23")

        # Diurnal temperature variation (peaks at 18:00)
        ambient_temp_variation = self.params.ambient_temp_amplitude * math.sin(2 * math.pi * (hour - self.params.diurnal_cycle_shift) / self.params.diurnal_cycle_period)

        # Heat sources/sinks
        heat_sources = {
            'solution_heating': 0.0,  # Controlled by external system
            'root_respiration': self.params.root_respiration_heat,
            'pump_heat': self.params.pump_heat_generation,
            'ambient_exchange': ambient_temp_variation * self.params.ambient_exchange_factor
        }

        # Calculate equilibrium temperature
        target_rzt = solution_temp + sum(heat_sources.values())

        # Initialize previous RZT if first call
        if self._previous_rzt is None:
            self._previous_rzt = solution_temp

        # Exponential approach to target with time constant
        response_rate = self.params.base_factor_constant - math.exp(-dt_hours / self.params.thermal_response_time)
        new_rzt = self._previous_rzt + (target_rzt - self._previous_rzt) * response_rate
        self._previous_rzt = new_rzt

        # Heat transfer rate (W/m²)
        heat_transfer_rate = abs(new_rzt - air_temp) * self.params.heat_transfer_coefficient

        return {
            'effective_rzt': new_rzt,
            'target_rzt': target_rzt,
            'thermal_lag': new_rzt - target_rzt,
            'heat_transfer_rate': heat_transfer_rate,
            'heating_required': max(0.0, target_rzt - new_rzt),
            'cooling_required': max(0.0, new_rzt - target_rzt)
        }

    def calculate_hourly_metrics(self, environmental_conditions: Dict[str, float], hour: int, dt_hours: float) -> RZTModelOutput:
        """
        Calculate hourly root zone temperature effects.

        Args:
            environmental_conditions: Dictionary with 'air_temperature' and 'solution_temperature' (°C)
            hour: Hour of day (0-23)
            dt_hours: Time step in hours

        Returns:
            RZTModelOutput with temperature effects and factors
        """
        air_temp = environmental_conditions.get('air_temperature')
        solution_temp = environmental_conditions.get('solution_temperature')
        if any(x is None for x in [air_temp, solution_temp]):
            raise ValueError("air_temperature and solution_temperature must be provided in environmental_conditions")

        # Calculate thermal dynamics
        thermal_response = self.calculate_thermal_dynamics(air_temp, solution_temp, hour, dt_hours)
        current_rzt = thermal_response['effective_rzt']
        optimal_rzt = self.calculate_optimal_rzt(air_temp)

        # Calculate temperature-dependent factors
        growth_factor = self.calculate_rzt_growth_factor(current_rzt, air_temp)
        nutrient_factor = self.calculate_nutrient_uptake_factor(current_rzt, air_temp)
        water_factor = self.calculate_water_uptake_factor(current_rzt, air_temp)
        photosynthesis_factor = self.calculate_photosynthesis_factor(current_rzt, air_temp)
        metabolism_factor = self.calculate_root_metabolism_factor(current_rzt, air_temp)

        return RZTModelOutput(
            current_rzt=current_rzt,
            optimal_rzt=optimal_rzt,
            rzt_deviation=current_rzt - optimal_rzt,
            growth_factor=growth_factor,
            nutrient_uptake_factor=nutrient_factor,
            water_uptake_factor=water_factor,
            photosynthesis_factor=photosynthesis_factor,
            root_metabolism_factor=metabolism_factor,
            thermal_stress=abs(current_rzt - optimal_rzt) / self.params.thermal_stress_normalizer,
            target_rzt=thermal_response['target_rzt'],
            thermal_lag=thermal_response['thermal_lag'],
            heat_transfer_rate=thermal_response['heat_transfer_rate'],
            heating_required=thermal_response['heating_required'],
            cooling_required=thermal_response['cooling_required']
        )

    def calculate_daily_metrics(self, environmental_conditions: Dict[str, float]) -> RZTModelOutput:
        """
        Calculate daily root zone temperature effects using noon as representative hour.

        Args:
            environmental_conditions: Dictionary with 'air_temperature' and 'solution_temperature' (°C)

        Returns:
            RZTModelOutput with temperature effects and factors
        """
        return self.calculate_hourly_metrics(environmental_conditions, hour=self.params.daily_representative_hour, dt_hours=self.params.diurnal_cycle_period)

def create_lettuce_rzt_model(system_config: Any) -> RootZoneTemperatureModel:
    """
    Create root zone temperature model with lettuce-specific parameters from configuration.

    Args:
        system_config: Configuration object containing RZT and water parameters

    Returns:
        RootZoneTemperatureModel configured with parameters
    """
    if not system_config:
        raise ValueError("System configuration must be provided")
    rzt_params = getattr(system_config, 'root_zone_temperature_parameters', None)
    water_params = getattr(system_config, 'water_parameters', None)
    if not rzt_params:
        raise ValueError("root_zone_temperature_parameters must be provided in configuration")
    if not water_params:
        raise ValueError("water_parameters must be provided in configuration")

    # Map renamed parameters
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
    config_dict = rzt_params.copy()
    for csv_name, model_name in param_mapping.items():
        if csv_name in config_dict:
            config_dict[model_name] = config_dict[csv_name]

    # Incorporate water uptake sensitivities from water parameters
    config_dict['water_uptake_sensitivity_low'] = water_params.get('water_uptake_sensitivity_low')
    config_dict['water_uptake_sensitivity_high'] = water_params.get('water_uptake_sensitivity_high')
    if any(x is None for x in [config_dict['water_uptake_sensitivity_low'], config_dict['water_uptake_sensitivity_high']]):
        raise ValueError("water_uptake_sensitivity_low and water_uptake_sensitivity_high must be provided in water_parameters")

    parameters = RZTParameters.from_config(config_dict)
    return RootZoneTemperatureModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- optimal_rzt_offset: °C above air temperature (typically 3°C)
- min_effective_rzt: Minimum effective RZT (°C, e.g., 15°C)
- max_effective_rzt: Maximum effective RZT (°C, e.g., 28°C)
- linear_growth_slope: Growth factor increase per °C below optimum
- rapid_decline_slope: Growth factor decrease per °C above optimum
- base_growth_factor: Growth factor at optimal RZT
- nutrient_uptake_sensitivity_low: Nutrient uptake sensitivity per °C below optimum
- nutrient_uptake_sensitivity_high: Nutrient uptake sensitivity per °C above optimum
- water_uptake_sensitivity_low: Water uptake sensitivity per °C below optimum
- water_uptake_sensitivity_high: Water uptake sensitivity per °C above optimum
- photosynthesis_sensitivity_low: Photosynthesis sensitivity per °C below optimum
- photosynthesis_sensitivity_high: Photosynthesis sensitivity per °C above optimum
- root_metabolism_sensitivity_low: Root metabolism sensitivity per °C below optimum
- root_metabolism_sensitivity_high: Root metabolism sensitivity per °C above optimum
- min_growth_factor: Minimum growth factor
- max_growth_factor: Maximum growth factor
- min_nutrient_uptake_factor: Minimum nutrient uptake factor
- max_nutrient_uptake_factor: Maximum nutrient uptake factor
- min_water_uptake_factor: Minimum water uptake factor
- max_water_uptake_factor: Maximum water uptake factor
- min_photosynthesis_factor: Minimum photosynthesis factor
- max_photosynthesis_factor: Maximum photosynthesis factor
- min_root_metabolism_factor: Minimum root metabolism factor
- max_root_metabolism_factor: Maximum root metabolism factor
- thermal_mass_factor: How quickly RZT responds to changes
- ambient_temp_amplitude: Amplitude of diurnal temperature variation (°C)
- root_respiration_heat: Heat from root respiration (°C)
- pump_heat_generation: Heat from circulation pumps (°C)
- ambient_exchange_factor: Factor for ambient temperature exchange
- thermal_response_time: Thermal response time constant (hours)
- heat_transfer_coefficient: Heat transfer coefficient (W/m²/°C)

INPUT VARIABLES:
- environmental_conditions: Dictionary with 'air_temperature' (°C) and 'solution_temperature' (°C)
- hour: Hour of day (0-23) for hourly updates
- dt_hours: Time step in hours for hourly updates

OUTPUT VARIABLES (RZTModelOutput):
- current_rzt: Current root zone temperature (°C)
- optimal_rzt: Optimal root zone temperature (°C)
- rzt_deviation: Deviation from optimal RZT (°C)
- growth_factor: Growth factor due to RZT
- nutrient_uptake_factor: Nutrient uptake efficiency factor
- water_uptake_factor: Water uptake capacity factor
- photosynthesis_factor: Photosynthesis efficiency factor
- root_metabolism_factor: Root metabolism activity factor
- thermal_stress: Normalized thermal stress
- target_rzt: Target RZT considering heat sources (°C)
- thermal_lag: Difference between current and target RZT (°C)
- heat_transfer_rate: Heat transfer rate (W/m²)
- heating_required: Heating needed to reach target RZT (°C)
- cooling_required: Cooling needed to reach target RZT (°C)

FUNCTION EXPLANATIONS FOR NON-CODERS:
This model manages root zone temperature (RZT) in hydroponic systems, like controlling the water temperature in a fish tank, which affects how well plant roots grow and function.

1. calculate_optimal_rzt:
   - Determines the ideal root temperature: `optimal_RZT = air_temperature + offset`.
   - Like setting the thermostat for your feet to be slightly warmer than the room for comfort.

2. calculate_rzt_growth_factor:
   - Calculates how RZT affects plant growth:
     - Below optimum: `factor = base + (optimal - current) * slope`
     - Above optimum: `factor = base - (current - optimal) * decline_slope`
   - Like how your energy increases in comfortable weather but drops if it's too hot or cold.

3. calculate_nutrient_uptake_factor:
   - Determines how RZT affects nutrient absorption: `factor = 1.0 ± (difference * sensitivity)`.
   - Like how a straw works better at the right temperature to sip nutrients; too cold or hot makes it harder.

4. calculate_water_uptake_factor:
   - Calculates RZT effect on water uptake: similar to nutrient uptake but with different sensitivity.
   - Like how roots pump water to leaves, which slows down if too cold or gets damaged if too hot.

5. calculate_photosynthesis_factor:
   - Shows how RZT impacts photosynthesis: `factor = 1.0 ± (difference * sensitivity)`.
   - Like how healthy roots support better food production in leaves; root stress affects the whole plant.

6. calculate_root_metabolism_factor:
   - Calculates RZT effect on root cell activity: `factor = 1.0 ± (difference * sensitivity)`.
   - Like how active your body is at different temperatures; roots need the right temperature to stay active.

7. calculate_thermal_dynamics:
   - Models how RZT changes over time: `new_RZT = previous + (target - previous) * response_rate`.
   - Like how a pot of water takes time to heat or cool due to its mass, affected by pumps and air.

8. calculate_hourly_metrics:
   - Updates RZT effects hourly, combining thermal dynamics and factor calculations.
   - Like checking a weather forecast hourly to adjust your plans for plant care.

9. calculate_daily_metrics:
   - Provides daily RZT effects using noon as a representative hour.
   - Like a daily summary of how root temperature affects plant health.

PRACTICAL APPLICATIONS:
- Optimize heating/cooling systems to maintain ideal RZT (e.g., 18-25°C for lettuce).
- Predict plant growth based on RZT to adjust nutrient or water delivery.
- Diagnose poor plant performance due to RZT stress (e.g., <15°C or >28°C).
- Design hydroponic systems with proper thermal mass and heat management.
- Schedule irrigation or nutrient dosing based on uptake efficiencies.
- Improve photosynthesis and yield by maintaining optimal RZT.
"""