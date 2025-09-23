"""
Photosynthesis Model (Dynamic Stomatal Conductance)
Calculates daily carbon assimilation based on light, CO2, and temperature.
Integrates a Jarvis-type model for dynamic stomatal conductance.
"""

import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
import math
# from utils.scientific_environmental_model import ScientificEnvironmentalModel  # Module deleted


@dataclass
class PhotosynthesisParameters:
    """Parameters for photosynthesis model."""
    # Required parameters (no defaults)
    phi_psii: float       # Quantum yield of PSII (mol e-/mol photons)
    r: float            # Gas constant (J/mol/K)
    g_max: float          # Maximum stomatal conductance (mol/m2/s)
    min_par_threshold: float     # Minimum PAR threshold for photosynthesis
    enzyme_saturation_lai: float  # LAI threshold for enzyme saturation
    light_penetration_lai: float  # LAI threshold for light penetration
    enzyme_saturation_rate: float # Rate of enzyme saturation decline
    min_enzyme_factor: float     # Minimum enzyme efficiency factor
    excess_lai_efficiency: float # Efficiency factor for excess LAI
    umol_to_g_carbon_ratio: float # Conversion ratio from umol CO2 to g C
    seconds_per_hour: int        # Seconds per hour for time conversions
    hours_per_day: int           # Hours per day for day length calculations
    
    # Optional parameters (loaded from config if None)
    kc: float = None            # Michaelis-Menten constant for CO2 (umol/mol)
    ko: float = None            # Michaelis-Menten constant for O2 (umol/mol)
    gamma_star: float = None    # CO2 compensation point for lettuce (umol/mol)
    jmax_25: float = None       # Realistic Jmax for lettuce at 25C (umol/m2/s) 
    vcmax_25: float = None      # Realistic Vcmax for lettuce at 25C (umol/m2/s)
    theta: float = None         # Curvature factor of light response
    alpha: float = None         # Realistic quantum efficiency for lettuce (mol CO2/mol photons)
    rd_25: float = None         # Realistic dark respiration for lettuce at 25C (umol CO2/m2/s)
    eaj: float = None           # Activation energy for Jmax (J/mol)
    eav: float = None           # Activation energy for Vcmax (J/mol)
    ear: float = None           # Activation energy for Rd (J/mol)
    o2_mmol_mol: float = 210.0  # Atmospheric O2 concentration (physical constant)
    
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'PhotosynthesisParameters':
        """Create PhotosynthesisParameters from CSV configuration data."""
        return cls(
            # Michaelis-Menten constants
            kc=float(config_dict['kc']),
            ko=float(config_dict['ko']),
            gamma_star=float(config_dict['gamma_star']),
            
            # Maximum rates at 25C
            jmax_25=float(config_dict['jmax_25']),
            vcmax_25=float(config_dict['vcmax_25']),
            
            # Light response parameters
            theta=float(config_dict['theta']),
            alpha=float(config_dict['alpha']),
            
            # Respiration
            rd_25=float(config_dict['rd_25']),
            
            # Activation energies
            eaj=float(config_dict['eaj']),
            eav=float(config_dict['eav']),
            ear=float(config_dict['ear']),
            
            # Required parameters
            phi_psii=float(config_dict['phi_psii']),
            r=float(config_dict['r']),
            g_max=float(config_dict['g_max']),
            
            # Physical constants
            o2_mmol_mol=float(config_dict['o2_mmol_mol']),
            
            # Additional parameters for advanced modeling
            min_par_threshold=float(config_dict['min_par_threshold']),
            enzyme_saturation_lai=float(config_dict['enzyme_saturation_lai']),
            light_penetration_lai=float(config_dict['light_penetration_lai']),
            enzyme_saturation_rate=float(config_dict['enzyme_saturation_rate']),
            min_enzyme_factor=float(config_dict['min_enzyme_factor']),
            excess_lai_efficiency=float(config_dict['excess_lai_efficiency']),
            umol_to_g_carbon_ratio=float(config_dict['umol_to_g_carbon_ratio']),
            seconds_per_hour=int(config_dict['seconds_per_hour']),
            hours_per_day=int(config_dict['hours_per_day'])
        )


class PhotosynthesisModel:
    """Farquhar-type model with dynamic stomatal conductance for daily carbon assimilation."""

    def __init__(self, parameters: Optional[PhotosynthesisParameters] = None):
        if parameters is None:
            raise ValueError("❌ PhotosynthesisParameters required - no hardcoded defaults allowed")
        self.params = parameters
        # self.env_model = ScientificEnvironmentalModel()  # Module deleted

    def _arrhenius_temp_response(self, rate_25: float, ea: float, temp_c: float) -> float:
        """Calculate temperature response using Arrhenius equation."""
        temp_k = float(temp_c) + 273.15
        return rate_25 * np.exp(ea * (temp_k - 298.15) / (298.15 * self.params.r * temp_k))

    def calculate_hourly_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, humidity: float,
                                     lai: float, hour: int, ec_factor: float, 
                                     config_dict: Optional[Dict[str, Any]] = None,
                                     sunlit_lai: Optional[float] = None, 
                                     shaded_lai: Optional[float] = None) -> float:
        """Calculate hourly carbon assimilation (g C/m2 ground area/hour)."""
        if par_umol_m2_s <= self.params.min_par_threshold:
            return 0.0
        
        if sunlit_lai is None:
            sunlit_lai = lai
        if shaded_lai is None:
            shaded_lai = 0.0
            
        if abs((sunlit_lai + shaded_lai) - lai) > 0.001:
            total_calculated = sunlit_lai + shaded_lai
            if total_calculated > 0:
                sunlit_lai = (sunlit_lai / total_calculated) * lai
                shaded_lai = (shaded_lai / total_calculated) * lai
            else:
                sunlit_lai = lai
                shaded_lai = 0.0
        
        sunlit_photosynthesis = self._calculate_instantaneous_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, humidity, sunlit_lai, ec_factor, config_dict
        )
        
        if shaded_lai > 0:
            shaded_par = par_umol_m2_s * (self.params.shaded_light_fraction if hasattr(self.params, 'shaded_light_fraction') else 0.3)
            shaded_photosynthesis = self._calculate_instantaneous_assimilation(
                shaded_par, co2_ppm, temp_c, humidity, shaded_lai, ec_factor, config_dict
            )
        else:
            shaded_photosynthesis = 0.0
        
        total_canopy_photosynthesis = sunlit_photosynthesis + shaded_photosynthesis
        return total_canopy_photosynthesis
    
    def _calculate_instantaneous_assimilation(self, par_umol_m2_s: float, co2_ppm: float, 
                                            temp_c: float, humidity: float, lai: float, ec_factor: float = 1.0, 
                                            config_dict: Optional[Dict[str, Any]] = None) -> float:
        """Calculate instantaneous photosynthesis rate (g C/m²/hour) with dynamic stomatal conductance."""
        
        vcmax_base = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax_base = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)
        
        if config_dict is None:
            raise ValueError("❌ Configuration dictionary required for LAI thresholds - no hardcoded defaults allowed")
        
        enzyme_saturation_lai = config_dict.get('enzyme_saturation_lai')
        if lai > enzyme_saturation_lai:
            enzyme_saturation_factor = 1.0 - self.params.enzyme_saturation_rate * (lai - enzyme_saturation_lai)
            enzyme_saturation_factor = max(self.params.min_enzyme_factor, enzyme_saturation_factor)
            vcmax = vcmax_base * enzyme_saturation_factor
            jmax = jmax_base * enzyme_saturation_factor
        else:
            vcmax = vcmax_base
            jmax = jmax_base

        # --- Dynamic Stomatal Conductance Calculation ---
        es = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))
        ea = es * (humidity / 100.0)
        vpd = max(0.1, es - ea)

        # Environmental factors using temperature utilities
        from src.utils.temperature_utils import calculate_temperature_stress_factor

        # Light factor - saturation curve
        f_light = min(1.0, par_umol_m2_s / 2000.0)  # Light saturation at 2000 μmol/m²/s

        # Temperature factor using utility function
        f_temp = calculate_temperature_stress_factor(temp_c,
                                                   optimal_temp_min=18.0,
                                                   optimal_temp_max=26.0,
                                                   stress_temp_min=5.0,
                                                   stress_temp_max=40.0)

        # VPD factor - optimal around 0.8-1.2 kPa
        optimal_vpd = 1.0
        if vpd <= optimal_vpd:
            f_vpd = max(0.1, vpd / optimal_vpd)  # Linear increase to optimal
        else:
            f_vpd = max(0.1, 1.0 - (vpd - optimal_vpd) / 2.0)  # Linear decrease above optimal

        gs = self.params.g_max * f_light * f_temp * f_vpd

        # Iteratively solve for An and Ci
        ci = co2_ppm * 0.7  # Initial guess
        net_photosynthesis_rate = 0.0

        for _ in range(3):  # 3 iterations are usually enough for convergence
            ac = vcmax * (ci - self.params.gamma_star) / (ci + self.params.kc * (1 + self.params.o2_mmol_mol / self.params.ko))
            i2 = self.params.alpha * par_umol_m2_s
            j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
            aj = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))
            net_photosynthesis_rate = max(0.0, min(ac, aj) - rd)

            if gs > 1e-9:
                # Ci = Ca - A * 1.6 / gs (Fick's law with diffusivity ratio)
                ci = co2_ppm - (net_photosynthesis_rate * 1.6 / gs)
                ci = max(self.params.gamma_star, ci)
            else:
                ci = co2_ppm
        # --- End of Dynamic Calculation ---

        hourly_g_c_per_m2 = net_photosynthesis_rate * 3600.0 * self.params.umol_to_g_carbon_ratio
        total_hourly_assimilation = hourly_g_c_per_m2 * lai * ec_factor
        
        return max(0.0, total_hourly_assimilation)

    def calculate_daily_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, humidity: float, lai: float, photoperiod_hours: float, ec_factor: float, config_dict: Optional[Dict[str, Any]] = None, sunlit_lai: Optional[float] = None, shaded_lai: Optional[float] = None) -> float:
        """Calculate daily carbon assimilation (g C/m2 ground area/day)."""
        
        if par_umol_m2_s <= self.params.min_par_threshold:
            return 0.0

        total_hourly_assimilation_rate = self.calculate_hourly_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, humidity, lai, 12, ec_factor, config_dict, sunlit_lai, shaded_lai
        )
        
        daily_assimilation = total_hourly_assimilation_rate * photoperiod_hours
        
        dark_period_hours = max(0.0, self.params.hours_per_day - photoperiod_hours)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)
        dark_respiration_umol_per_sec = rd * lai
        dark_respiration_g_c_per_hour = dark_respiration_umol_per_sec * 3600.0 * self.params.umol_to_g_carbon_ratio
        total_dark_respiration_loss = dark_respiration_g_c_per_hour * dark_period_hours
        
        return max(0.0, daily_assimilation - total_dark_respiration_loss)

def create_lettuce_photosynthesis_model(system_config=None) -> PhotosynthesisModel:
    """Create photosynthesis model with lettuce-specific parameters from CSV config only.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        PhotosynthesisModel configured with CSV parameters
        
    Raises:
        ValueError: If CSV parameters are missing or invalid
    """
    if system_config is None:
        raise ValueError("❌ system_config is required - no hardcoded defaults allowed")
        
    photosynthesis_params = getattr(system_config, 'photosynthesis_parameters', None)
    if photosynthesis_params is None:
        photosynthesis_params = getattr(system_config, 'photosynthesis', None)
    
    if photosynthesis_params is None:
        raise ValueError("❌ photosynthesis parameters missing from CSV - no fallback defaults allowed")
    
    required_params = ['kc', 'ko', 'gamma_star', 'jmax_25', 'vcmax_25', 'theta', 'alpha', 'rd_25', 'eaj', 'eav', 'ear', 'phi_psii', 'r', 'g_max', 'o2_mmol_mol']
    missing_params = [p for p in required_params if p not in photosynthesis_params]
    if missing_params:
        available_params = list(photosynthesis_params.keys())
        raise ValueError(f"❌ Missing required photosynthesis parameters in CSV: {missing_params}. Available: {available_params}")
    
    # Track parameters used in model initialization if tracker is available
    if hasattr(system_config, '_tracker'):
        tracker = getattr(system_config, '_tracker', None)
        if tracker:
            tracker.track_model_initialization(required_params, "photosynthesis_model")
            # Track additional parameters used in equations
            equation_params = ['min_par_threshold', 'enzyme_saturation_lai', 'light_penetration_lai', 
                             'enzyme_saturation_rate', 'min_enzyme_factor', 'excess_lai_efficiency',
                             'umol_to_g_carbon_ratio', 'seconds_per_hour', 'hours_per_day']
            tracker.track_equation_parameters(equation_params, "photosynthesis_calculations")
    
    parameters = PhotosynthesisParameters.from_config(photosynthesis_params)
    return PhotosynthesisModel(parameters)