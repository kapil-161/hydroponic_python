from typing import Dict, Optional, Any
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

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'PhotosynthesisParameters':
        required_params = [
            'phi_psii', 'r', 'g_max', 'min_par_threshold', 'enzyme_saturation_lai',
            'light_penetration_lai', 'enzyme_saturation_rate', 'min_enzyme_factor',
            'excess_lai_efficiency', 'umol_to_g_carbon_ratio', 'seconds_per_hour',
            'hours_per_day', 'kc', 'ko', 'gamma_star', 'jmax_25', 'vcmax_25',
            'theta', 'alpha', 'rd_25', 'eaj', 'eav', 'ear', 'o2_mmol_mol',
            'shaded_light_fraction', 'photosynthesis_cold_limit', 'photosynthesis_heat_limit',
            'min_stress_factor'
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
            min_stress_factor=float(config['min_stress_factor'])
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

    def _arrhenius_temp_response(self, rate_25: float, ea: float, temp_c: float) -> float:
        if temp_c is None:
            raise ValueError("Temperature must be provided")
        temp_k = float(temp_c) + 273.15
        if temp_k <= 0:
            raise ValueError("Temperature in Kelvin must be positive")
        return rate_25 * math.exp(ea * (temp_k - 298.15) / (298.15 * self.params.r * temp_k))

    def _calculate_instantaneous_assimilation(self, par_umol_m2_s: float, co2_ppm: float,
                                            temp_c: float, humidity: float, lai: float,
                                            ec_factor: float, config: Dict[str, Any]) -> float:
        if any(x is None for x in [par_umol_m2_s, co2_ppm, temp_c, humidity, lai, ec_factor, config]):
            raise ValueError("All inputs (par, co2, temp, humidity, lai, ec_factor, config) must be provided")
        if par_umol_m2_s < self.params.min_par_threshold:
            return 0.0
        if lai < 0 or ec_factor < 0 or humidity < 0 or humidity > 100:
            raise ValueError("Invalid input: lai, ec_factor must be non-negative, humidity must be 0-100")
        if 'optimal_temp_min' not in config or 'optimal_temp_max' not in config:
            raise KeyError("config must contain optimal_temp_min and optimal_temp_max")

        vcmax = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)

        enzyme_saturation_lai = config.get('enzyme_saturation_lai', self.params.enzyme_saturation_lai)
        if lai > enzyme_saturation_lai:
            enzyme_saturation_factor = 1.0 - self.params.enzyme_saturation_rate * (lai - enzyme_saturation_lai)
            enzyme_saturation_factor = max(self.params.min_enzyme_factor, enzyme_saturation_factor)
            vcmax *= enzyme_saturation_factor
            jmax *= enzyme_saturation_factor

        es = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))
        ea = es * (humidity / 100.0)
        vpd = max(0.1, es - ea)

        f_light = min(1.0, par_umol_m2_s / config.get('light_saturation', 2000.0))
        f_temp = self._calculate_temperature_stress_factor(temp_c, config['optimal_temp_min'], config['optimal_temp_max'])
        optimal_vpd = config.get('optimal_vpd', 1.0)
        if vpd <= optimal_vpd:
            f_vpd = max(0.1, vpd / optimal_vpd)
        else:
            f_vpd = max(0.1, 1.0 - (vpd - optimal_vpd) / config.get('vpd_decline_rate', 2.0))

        gs = self.params.g_max * f_light * f_temp * f_vpd
        ci = co2_ppm * 0.7
        net_photosynthesis_rate = 0.0

        for _ in range(3):
            ac = vcmax * (ci - self.params.gamma_star) / (ci + self.params.kc * (1 + self.params.o2_mmol_mol / self.params.ko))
            i2 = self.params.alpha * par_umol_m2_s * self.params.phi_psii
            j = (i2 + jmax - math.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
            aj = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))
            net_photosynthesis_rate = max(0.0, min(ac, aj) - rd)
            if gs > 1e-9:
                ci = co2_ppm - (net_photosynthesis_rate * 1.6 / gs)
                ci = max(self.params.gamma_star, ci)
            else:
                ci = co2_ppm

        hourly_g_c_per_m2 = net_photosynthesis_rate * self.params.seconds_per_hour * self.params.umol_to_g_carbon_ratio
        return max(0.0, hourly_g_c_per_m2 * lai * ec_factor), gs

    def _calculate_temperature_stress_factor(self, temp_c: float, optimal_temp_min: float, optimal_temp_max: float) -> float:
        """Use consolidated temperature stress factor calculation from core_utils."""
        from src.utils.core_utils import calculate_temperature_stress_factor

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
                                     sunlit_lai: float, shaded_lai: float) -> float:
        if any(x is None for x in [par_umol_m2_s, co2_ppm, temp_c, humidity, lai, ec_factor, config, sunlit_lai, shaded_lai]):
            raise ValueError("All inputs must be provided")
        if abs((sunlit_lai + shaded_lai) - lai) > 0.001:
            raise ValueError("Sum of sunlit_lai and shaded_lai must equal lai")

        sunlit_photosynthesis, sunlit_gs = self._calculate_instantaneous_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, humidity, sunlit_lai, ec_factor, config
        )
        shaded_photosynthesis = 0.0
        shaded_gs = 0.0
        if shaded_lai > 0:
            shaded_par = par_umol_m2_s * self.params.shaded_light_fraction
            shaded_photosynthesis, shaded_gs = self._calculate_instantaneous_assimilation(
                shaded_par, co2_ppm, temp_c, humidity, shaded_lai, ec_factor, config
            )
        total_gs = (sunlit_gs * sunlit_lai + shaded_gs * shaded_lai) / lai if lai > 0 else 0.0
        return sunlit_photosynthesis + shaded_photosynthesis, total_gs

    def calculate_daily_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, humidity: float,
                                    lai: float, photoperiod_hours: float, ec_factor: float,
                                    config: Dict[str, Any], sunlit_lai: float, shaded_lai: float) -> PhotosynthesisResponse:
        if any(x is None for x in [par_umol_m2_s, co2_ppm, temp_c, humidity, lai, photoperiod_hours, ec_factor, config, sunlit_lai, shaded_lai]):
            raise ValueError("All inputs must be provided")
        if photoperiod_hours < 0 or photoperiod_hours > self.params.hours_per_day:
            raise ValueError("photoperiod_hours must be between 0 and hours_per_day")
        if lai < 0 or ec_factor < 0:
            raise ValueError("lai and ec_factor must be non-negative")

        hourly_assimilation, stomatal_conductance = self.calculate_hourly_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, humidity, lai, ec_factor, config, sunlit_lai, shaded_lai
        )
        daily_assimilation = hourly_assimilation * photoperiod_hours
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