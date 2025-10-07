from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
import math

@dataclass
class PhotosynthesisParameters:
    phi_psii: float
    r: float
    g_max: float
    min_par_threshold: float
    enzyme_saturation_lai: float
    light_penetration_lai: float
    enzyme_saturation_rate: float
    min_enzyme_factor: float
    excess_lai_efficiency: float
    umol_to_g_carbon_ratio: float
    seconds_per_hour: int
    hours_per_day: int
    kc: float
    ko: float
    gamma_star: float
    jmax_25: float
    vcmax_25: float
    theta: float
    alpha: float
    rd_25: float
    eaj: float
    eav: float
    ear: float
    o2_mmol_mol: float
    shaded_light_fraction: float
    photosynthesis_cold_limit: float
    photosynthesis_heat_limit: float
    min_stress_factor: float
    optimal_temperature_min: float
    optimal_temperature_max: float
    light_saturation_threshold: float
    optimal_vpd_min: float
    optimal_vpd_max: float
    reference_leaf_nitrogen: float
    nitrogen_sensitivity: float
    water_stress_sensitivity: float
    # Physical constants (from CSV)
    kelvin_conversion: float
    reference_temp_kelvin: float
    saturation_vapor_pressure_constant: float
    vapor_pressure_temp_coefficient: float
    vapor_pressure_base_temp: float
    # Model-specific constants (from CSV)
    initial_ci_fraction: float
    ci_convergence_max_iterations: int
    ci_convergence_tolerance_ppm: float
    stomatal_conductance_co2_diffusion_ratio: float
    minimum_stomatal_conductance_threshold: float
    minimum_vpd_threshold: float
    # Sunlit fraction calculation parameters - NO HARDCODED VALUES (Rules.md)
    sunlit_fraction_lai_coefficient: float
    sunlit_fraction_minimum: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'PhotosynthesisParameters':
        required_params = [
            'phi_psii', 'r', 'g_max', 'min_par_threshold', 'enzyme_saturation_lai',
            'light_penetration_lai', 'enzyme_saturation_rate', 'min_enzyme_factor',
            'excess_lai_efficiency', 'umol_to_g_carbon_ratio', 'seconds_per_hour',
            'hours_per_day', 'kc', 'ko', 'gamma_star', 'jmax_25', 'vcmax_25',
            'theta', 'alpha', 'rd_25', 'eaj', 'eav', 'ear', 'o2_mmol_mol',
            'shaded_light_fraction', 'photosynthesis_cold_limit', 'photosynthesis_heat_limit',
            'min_stress_factor', 'optimal_temperature_min', 'optimal_temperature_max',
            'light_saturation_threshold', 'optimal_vpd_min', 'optimal_vpd_max',
            'reference_leaf_nitrogen', 'nitrogen_sensitivity', 'water_stress_sensitivity',
            # Physical constants
            'kelvin_conversion', 'reference_temp_kelvin', 'saturation_vapor_pressure_constant',
            'vapor_pressure_temp_coefficient', 'vapor_pressure_base_temp',
            # Model-specific constants
            'initial_ci_fraction', 'ci_convergence_max_iterations', 'ci_convergence_tolerance_ppm',
            'stomatal_conductance_co2_diffusion_ratio', 'minimum_stomatal_conductance_threshold',
            'minimum_vpd_threshold',
            # Sunlit fraction calculation - NO HARDCODED VALUES (Rules.md)
            'sunlit_fraction_lai_coefficient', 'sunlit_fraction_minimum'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")

        if config['min_par_threshold'] < 0:
            raise ValueError("min_par_threshold must be non-negative")
        if config['g_max'] <= 0:
            raise ValueError("g_max must be positive")
        if config['seconds_per_hour'] <= 0 or config['hours_per_day'] <= 0:
            raise ValueError("seconds_per_hour and hours_per_day must be positive")
        if config['shaded_light_fraction'] <= 0 or config['shaded_light_fraction'] >= 1:
            raise ValueError("shaded_light_fraction must be between 0 and 1")
        if config['theta'] <= 0 or config['theta'] >= 1:
            raise ValueError("theta must be between 0 and 1")
        if config['min_enzyme_factor'] <= 0 or config['min_enzyme_factor'] >= 1:
            raise ValueError("min_enzyme_factor must be between 0 and 1")

        return cls(
            phi_psii=float(config['phi_psii']),
            r=float(config['r']),
            g_max=float(config['g_max']),
            min_par_threshold=float(config['min_par_threshold']),
            enzyme_saturation_lai=float(config['enzyme_saturation_lai']),
            light_penetration_lai=float(config['light_penetration_lai']),
            enzyme_saturation_rate=float(config['enzyme_saturation_rate']),
            min_enzyme_factor=float(config['min_enzyme_factor']),
            excess_lai_efficiency=float(config['excess_lai_efficiency']),
            umol_to_g_carbon_ratio=float(config['umol_to_g_carbon_ratio']),
            seconds_per_hour=int(config['seconds_per_hour']),
            hours_per_day=int(config['hours_per_day']),
            kc=float(config['kc']),
            ko=float(config['ko']),
            gamma_star=float(config['gamma_star']),
            jmax_25=float(config['jmax_25']),
            vcmax_25=float(config['vcmax_25']),
            theta=float(config['theta']),
            alpha=float(config['alpha']),
            rd_25=float(config['rd_25']),
            eaj=float(config['eaj']),
            eav=float(config['eav']),
            ear=float(config['ear']),
            o2_mmol_mol=float(config['o2_mmol_mol']),
            shaded_light_fraction=float(config['shaded_light_fraction']),
            photosynthesis_cold_limit=float(config['photosynthesis_cold_limit']),
            photosynthesis_heat_limit=float(config['photosynthesis_heat_limit']),
            min_stress_factor=float(config['min_stress_factor']),
            optimal_temperature_min=float(config['optimal_temperature_min']),
            optimal_temperature_max=float(config['optimal_temperature_max']),
            light_saturation_threshold=float(config['light_saturation_threshold']),
            optimal_vpd_min=float(config['optimal_vpd_min']),
            optimal_vpd_max=float(config['optimal_vpd_max']),
            reference_leaf_nitrogen=float(config['reference_leaf_nitrogen']),
            nitrogen_sensitivity=float(config['nitrogen_sensitivity']),
            water_stress_sensitivity=float(config['water_stress_sensitivity']),
            # Physical constants
            kelvin_conversion=float(config['kelvin_conversion']),
            reference_temp_kelvin=float(config['reference_temp_kelvin']),
            saturation_vapor_pressure_constant=float(config['saturation_vapor_pressure_constant']),
            vapor_pressure_temp_coefficient=float(config['vapor_pressure_temp_coefficient']),
            vapor_pressure_base_temp=float(config['vapor_pressure_base_temp']),
            # Model-specific constants
            initial_ci_fraction=float(config['initial_ci_fraction']),
            ci_convergence_max_iterations=int(config['ci_convergence_max_iterations']),
            ci_convergence_tolerance_ppm=float(config['ci_convergence_tolerance_ppm']),
            stomatal_conductance_co2_diffusion_ratio=float(config['stomatal_conductance_co2_diffusion_ratio']),
            minimum_stomatal_conductance_threshold=float(config['minimum_stomatal_conductance_threshold']),
            minimum_vpd_threshold=float(config['minimum_vpd_threshold'])
        )

@dataclass
class PhotosynthesisResponse:
    daily_assimilation: float
    hourly_assimilation: float
    dark_respiration_loss: float
    stomatal_conductance: float

class PhotosynthesisModel:
    def __init__(self, parameters: PhotosynthesisParameters):
        if not parameters:
            raise ValueError("PhotosynthesisParameters must be provided")
        self.params = parameters
    
    def initialize(self):
        """Initialize the photosynthesis model"""
        pass

    def _arrhenius_temp_response(self, rate_25: float, ea: float, temp_c: float) -> float:
        if temp_c is None:
            raise ValueError("Temperature must be provided")
        temp_k = float(temp_c) + self.params.kelvin_conversion
        if temp_k <= 0:
            raise ValueError("Temperature in Kelvin must be positive")
        return rate_25 * math.exp(ea * (temp_k - self.params.reference_temp_kelvin) / (self.params.reference_temp_kelvin * self.params.r * temp_k))

    def _calculate_instantaneous_assimilation(self, par_umol_m2_s: float, co2_ppm: float,
                                            temp_c: float, humidity: float, lai: float,
                                            ec_factor: float, config: Dict[str, Any],
                                            leaf_nitrogen: float, water_stress: float) -> Tuple[float, float]:
        if any(x is None for x in [par_umol_m2_s, co2_ppm, temp_c, humidity, lai, ec_factor, config, leaf_nitrogen, water_stress]):
            raise ValueError("All inputs (par, co2, temp, humidity, lai, ec_factor, config, leaf_nitrogen, water_stress) must be provided")
        if par_umol_m2_s < self.params.min_par_threshold:
            return 0.0, 0.0
        if lai < 0 or ec_factor < 0 or humidity < 0 or humidity > 100:
            raise ValueError("Invalid input: lai, ec_factor must be non-negative, humidity must be 0-100")
        if 'optimal_temp_min' not in config or 'optimal_temp_max' not in config:
            raise KeyError("config must contain optimal_temp_min and optimal_temp_max")

        vcmax = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)

        # Apply nitrogen effect
        nitrogen_factor = 1 + self.params.nitrogen_sensitivity * (leaf_nitrogen - self.params.reference_leaf_nitrogen)
        vcmax *= nitrogen_factor
        jmax *= nitrogen_factor

        enzyme_saturation_lai = config.get('enzyme_saturation_lai', self.params.enzyme_saturation_lai)
        if lai > enzyme_saturation_lai:
            enzyme_saturation_factor = 1.0 - self.params.enzyme_saturation_rate * (lai - enzyme_saturation_lai)
            enzyme_saturation_factor = max(self.params.min_enzyme_factor, enzyme_saturation_factor)
            vcmax *= enzyme_saturation_factor
            jmax *= enzyme_saturation_factor

        es = self.params.saturation_vapor_pressure_constant * math.exp(self.params.vapor_pressure_temp_coefficient * temp_c / (temp_c + self.params.vapor_pressure_base_temp))
        ea = es * (humidity / 100.0)
        vpd = max(self.params.minimum_vpd_threshold, es - ea)

        # All parameters must come from CSV per Rules.md
        if 'light_saturation_threshold' not in config:
            raise KeyError("light_saturation_threshold must be provided in config from CSV")
        if 'optimal_vpd_min' not in config or 'optimal_vpd_max' not in config:
            raise KeyError("optimal_vpd_min and optimal_vpd_max must be provided in config from CSV")

        f_light = min(1.0, par_umol_m2_s / config['light_saturation_threshold'])
        f_temp = self._calculate_temperature_stress_factor(temp_c, config['optimal_temp_min'], config['optimal_temp_max'])

        # Use VPD range from CSV parameters
        optimal_vpd_min = config['optimal_vpd_min']
        optimal_vpd_max = config['optimal_vpd_max']
        optimal_vpd = (optimal_vpd_min + optimal_vpd_max) / 2.0

        if vpd <= optimal_vpd:
            f_vpd = max(self.params.minimum_vpd_threshold, vpd / optimal_vpd)
        else:
            vpd_decline_range = optimal_vpd_max - optimal_vpd_min
            if vpd_decline_range > 0:
                f_vpd = max(self.params.minimum_vpd_threshold, 1.0 - (vpd - optimal_vpd) / vpd_decline_range)
            else:
                f_vpd = self.params.minimum_vpd_threshold

        gs = self.params.g_max * f_light * f_temp * f_vpd

        # Apply water stress effect (water_stress: 0.0 = no stress, 1.0 = full stress)
        # Higher stress reduces stomatal conductance
        water_stress_factor = 1.0 - (self.params.water_stress_sensitivity * water_stress)
        gs *= max(0.0, water_stress_factor)

        ci = co2_ppm * self.params.initial_ci_fraction
        net_photosynthesis_rate = 0.0

        # Iterate until CO2 concentration converges (proper numerical solution)
        max_iterations = self.params.ci_convergence_max_iterations
        tolerance = self.params.ci_convergence_tolerance_ppm  # CO2 concentration convergence tolerance (ppm)

        for iteration in range(max_iterations):
            ci_prev = ci

            ac = vcmax * (ci - self.params.gamma_star) / (ci + self.params.kc * (1 + self.params.o2_mmol_mol / self.params.ko))
            i2 = self.params.alpha * par_umol_m2_s * self.params.phi_psii
            j = (i2 + jmax - math.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
            aj = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))
            net_photosynthesis_rate = max(0.0, min(ac, aj) - rd)

            if gs > self.params.minimum_stomatal_conductance_threshold:
                ci = co2_ppm - (net_photosynthesis_rate * self.params.stomatal_conductance_co2_diffusion_ratio / gs)
                ci = max(self.params.gamma_star, ci)
            else:
                ci = co2_ppm

            # Check for convergence
            if abs(ci - ci_prev) < tolerance:
                break

        hourly_g_c_per_m2 = net_photosynthesis_rate * self.params.seconds_per_hour * self.params.umol_to_g_carbon_ratio
        final_result = max(0.0, hourly_g_c_per_m2 * lai * ec_factor)

        return final_result, gs

    def _calculate_temperature_stress_factor(self, temp_c: float, optimal_temp_min: float, optimal_temp_max: float) -> float:
        """Use consolidated temperature stress factor calculation from core_utils."""
        from utils.core_utils import calculate_temperature_stress_factor

        # Create config structure for consolidated function
        # ALL parameters must come from CSV configuration - no hardcoded values like 5.0, 40.0
        temp_config = type('Config', (), {
            'temperature_stress': {
                'optimal_temp_min': optimal_temp_min,
                'optimal_temp_max': optimal_temp_max,
                # These parameters must be defined in CSV - no hardcoded fallbacks
                'photosynthesis_cold_limit': self.params.photosynthesis_cold_limit,
                'photosynthesis_heat_limit': self.params.photosynthesis_heat_limit,
                'min_factor': self.params.min_stress_factor
            }
        })

        return calculate_temperature_stress_factor(temp_c, temp_config, method='photosynthesis')

    def calculate_hourly_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, humidity: float,
                                     lai: float, ec_factor: float, config: Dict[str, Any],
                                     sunlit_lai: float, shaded_lai: float,
                                     leaf_nitrogen: float, water_stress: float,
                                     dynamic_shaded_par: Optional[float] = None) -> Tuple[float, float]:
        if any(x is None for x in [par_umol_m2_s, co2_ppm, temp_c, humidity, lai, ec_factor, config, sunlit_lai, shaded_lai, leaf_nitrogen, water_stress]):
            raise ValueError("All inputs must be provided")
        if abs((sunlit_lai + shaded_lai) - lai) > 0.001:
            raise ValueError("Sum of sunlit_lai and shaded_lai must equal lai")

        sunlit_photosynthesis, sunlit_gs = self._calculate_instantaneous_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, humidity, sunlit_lai, ec_factor, config, leaf_nitrogen, water_stress
        )
        shaded_photosynthesis = 0.0
        shaded_gs = 0.0
        if shaded_lai > 0:
            # Use dynamic shaded PAR if provided, otherwise fallback to static fraction
            if dynamic_shaded_par is not None:
                shaded_par = dynamic_shaded_par  # Use dynamic PAR from CanopyArchitectureModel
            else:
                shaded_par = par_umol_m2_s * self.params.shaded_light_fraction  # Fallback to static fraction
            shaded_photosynthesis, shaded_gs = self._calculate_instantaneous_assimilation(
                shaded_par, co2_ppm, temp_c, humidity, shaded_lai, ec_factor, config, leaf_nitrogen, water_stress
            )
        total_gs = (sunlit_gs * sunlit_lai + shaded_gs * shaded_lai) / lai if lai > 0 else 0.0
        return sunlit_photosynthesis + shaded_photosynthesis, total_gs

    def calculate_daily_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, humidity: float,
                                    lai: float, photoperiod_hours: float, ec_factor: float,
                                    config: Dict[str, Any], sunlit_lai: float, shaded_lai: float,
                                    leaf_nitrogen: float, water_stress: float,
                                    dynamic_dark_respiration_rate: Optional[float] = None) -> PhotosynthesisResponse:
        if any(x is None for x in [par_umol_m2_s, co2_ppm, temp_c, humidity, lai, photoperiod_hours, ec_factor, config, sunlit_lai, shaded_lai, leaf_nitrogen, water_stress]):
            raise ValueError("All inputs must be provided")
        if photoperiod_hours < 0 or photoperiod_hours > self.params.hours_per_day:
            raise ValueError("photoperiod_hours must be between 0 and hours_per_day")
        if lai < 0 or ec_factor < 0:
            raise ValueError("lai and ec_factor must be non-negative")

        hourly_assimilation, stomatal_conductance = self.calculate_hourly_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, humidity, lai, ec_factor, config, sunlit_lai, shaded_lai, leaf_nitrogen, water_stress
        )
        daily_assimilation = hourly_assimilation * photoperiod_hours

        # Use dynamic respiration rate if provided, otherwise fallback to simplified calculation
        if dynamic_dark_respiration_rate is not None:
            # Use dynamic respiration rate from EnhancedRespirationModel (following "model output" rule)
            dark_period_hours = self.params.hours_per_day - photoperiod_hours
            total_dark_respiration_loss = dynamic_dark_respiration_rate * dark_period_hours
        else:
            # Fallback to simplified static calculation
            rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)
            dark_respiration_umol_per_sec = rd * lai
            dark_respiration_g_c_per_hour = dark_respiration_umol_per_sec * self.params.seconds_per_hour * self.params.umol_to_g_carbon_ratio
            dark_period_hours = self.params.hours_per_day - photoperiod_hours
            total_dark_respiration_loss = dark_respiration_g_c_per_hour * dark_period_hours
        net_daily_assimilation = max(0.0, daily_assimilation - total_dark_respiration_loss)

        return PhotosynthesisResponse(
            daily_assimilation=net_daily_assimilation,
            hourly_assimilation=hourly_assimilation,
            dark_respiration_loss=total_dark_respiration_loss,
            stomatal_conductance=stomatal_conductance
        )

def create_lettuce_photosynthesis_model(system_config: Any) -> 'PhotosynthesisModel':
    if system_config is None:
        raise ValueError("System configuration must be provided")
    config = getattr(system_config, 'photosynthesis_parameters', None)
    if config is None:
        raise ValueError("photosynthesis_parameters section must be provided in configuration")
    parameters = PhotosynthesisParameters.from_config(config)
    return PhotosynthesisModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- phi_psii: Quantum yield of PSII (mol e-/mol photons)
- r: Gas constant (J/mol/K)
- g_max: Maximum stomatal conductance (mol/m2/s)
- min_par_threshold: Minimum PAR for photosynthesis (umol/m2/s)
- enzyme_saturation_lai: LAI threshold for enzyme saturation
- light_penetration_lai: LAI threshold for light penetration
- enzyme_saturation_rate: Rate of enzyme saturation decline
- min_enzyme_factor: Minimum enzyme efficiency factor
- excess_lai_efficiency: Efficiency factor for excess LAI
- umol_to_g_carbon_ratio: Conversion ratio from umol CO2 to g C
- seconds_per_hour: Seconds per hour for time conversions
- hours_per_day: Hours per day for calculations
- kc: Michaelis-Menten constant for CO2 (umol/mol)
- ko: Michaelis-Menten constant for O2 (umol/mol)
- gamma_star: CO2 compensation point (umol/mol)
- jmax_25: Maximum electron transport rate at 25°C (umol/m2/s)
- vcmax_25: Maximum carboxylation rate at 25°C (umol/m2/s)
- theta: Curvature factor of light response
- alpha: Quantum efficiency (mol CO2/mol photons)
- rd_25: Dark respiration rate at 25°C (umol CO2/m2/s)
- eaj: Activation energy for Jmax (J/mol)
- eav: Activation energy for Vcmax (J/mol)
- ear: Activation energy for Rd (J/mol)
- o2_mmol_mol: Atmospheric O2 concentration (mmol/mol)
- shaded_light_fraction: Fraction of PAR for shaded leaves

INPUT VARIABLES:
- par_umol_m2_s: Photosynthetically active radiation (umol/m2/s)
- co2_ppm: CO2 concentration (ppm)
- temp_c: Temperature (°C)
- humidity: Relative humidity (%)
- lai: Leaf area index
- photoperiod_hours: Hours of daylight
- ec_factor: Electrical conductivity factor (dimensionless)
- sunlit_lai: Sunlit leaf area index
- shaded_lai: Shaded leaf area index
- config: Dictionary with optimal_temp_min, optimal_temp_max, light_saturation, optimal_vpd, vpd_decline_rate

OUTPUT VARIABLES:
- PhotosynthesisResponse:
  - daily_assimilation: Net daily carbon assimilation (g C/m2/day)
  - hourly_assimilation: Hourly carbon assimilation (g C/m2/hour)
  - dark_respiration_loss: Daily dark respiration loss (g C/m2/day)
  - stomatal_conductance: Stomatal conductance (mol/m2/s)

FUNCTION EXPLANATIONS FOR NON-CODERS:
This model calculates how much carbon a plant captures daily through photosynthesis, like tracking how much "food" a plant makes to grow. It accounts for light, CO2, temperature, and humidity effects on leaf pores (stomata).

1. _arrhenius_temp_response:
   - Adjusts photosynthesis rates for temperature: `rate = rate_25 * exp(ea * ΔT / (R * T))`.
   - Like how cooking speeds up with heat, plant enzymes work faster at warmer temperatures, up to a limit.

2. _calculate_instantaneous_assimilation:
   - Calculates photosynthesis rate: `An = min(Ac, Aj) - Rd`, with dynamic stomatal conductance.
   - Like a factory production rate, it balances CO2 uptake with enzyme and light limitations.

3. calculate_hourly_assimilation:
   - Computes hourly carbon gain for sunlit and shaded leaves: `total = sunlit + shaded`.
   - Like tracking energy production from solar panels, some leaves get full sun, others partial.

4. calculate_daily_assimilation:
   - Calculates daily carbon gain: `daily = hourly * photoperiod - respiration`.
   - Like a daily energy budget, balancing what the plant produces minus what it burns at night.

PRACTICAL APPLICATIONS:
- Optimizes light and CO2 levels for maximum growth.
- Guides temperature and humidity control to enhance photosynthesis.
- Predicts carbon assimilation for biomass growth models.
- Helps design lighting systems for hydroponic facilities.
- Supports yield forecasting for production planning.
"""