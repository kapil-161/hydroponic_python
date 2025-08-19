"""
Photosynthesis Model (Simplified Farquhar-type)
Calculates daily carbon assimilation based on light, CO2, and temperature.
"""

import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PhotosynthesisParameters:
    """Parameters for photosynthesis model."""
    kc: float = 404.0           # Michaelis-Menten constant for CO2 (umol/mol)
    ko: float = 248.0           # Michaelis-Menten constant for O2 (umol/mol)
    gamma_star: float = 36.9    # CO2 compensation point in absence of respiration (umol/mol)
    jmax_25: float = 500.0      # Maximum electron transport rate at 25C (umol/m2/s)
    vcmax_25: float = 250.0     # Maximum carboxylation rate at 25C (umol/m2/s)
    theta: float = 0.85         # Curvature factor of light response
    phi_psii: float = 0.3       # Quantum yield of PSII (mol e-/mol photons)
    alpha: float = 0.2          # Quantum efficiency of CO2 assimilation (mol CO2/mol photons)
    rd_25: float = 0.1          # Dark respiration rate at 25C (umol CO2/m2/s)
    eaj: float = 30000.0        # Activation energy for Jmax (J/mol)
    eav: float = 60000.0        # Activation energy for Vcmax (J/mol)
    ear: float = 46390.0        # Activation energy for Rd (J/mol)
    r: float = 8.314            # Gas constant (J/mol/K)
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'PhotosynthesisParameters':
        """Create PhotosynthesisParameters from configuration dictionary."""
        return cls(
            kc=config_dict.get('kc', 404.0),
            ko=config_dict.get('ko', 248.0),
            gamma_star=config_dict.get('gamma_star', 36.9),
            jmax_25=config_dict.get('jmax_25', 500.0),
            vcmax_25=config_dict.get('vcmax_25', 250.0),
            theta=config_dict.get('theta', 0.85),
            phi_psii=config_dict.get('phi_psii', 0.3),
            alpha=config_dict.get('alpha', 0.2),
            rd_25=config_dict.get('rd_25', 0.1),
            eaj=config_dict.get('eaj', 30000.0),
            eav=config_dict.get('eav', 60000.0),
            ear=config_dict.get('ear', 46390.0),
            r=config_dict.get('r', 8.314)
        )


class PhotosynthesisModel:
    """Simplified Farquhar-type model for daily carbon assimilation."""

    def __init__(self, parameters: Optional[PhotosynthesisParameters] = None):
        self.params = parameters or PhotosynthesisParameters()

    def _arrhenius_temp_response(self, rate_25: float, ea: float, temp_c: float) -> float:
        """Calculate temperature response using Arrhenius equation."""
        temp_k = temp_c + 273.15
        return rate_25 * np.exp(ea * (temp_k - 298.15) / (298.15 * self.params.r * temp_k))

    def calculate_daily_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, lai: float) -> float:
        """Calculate daily carbon assimilation (g C/m2/day)."""
        # Convert CO2 ppm to umol/mol
        ci = co2_ppm * 1.0 # Assuming internal CO2 is similar to ambient for simplicity

        # Temperature-adjusted rates
        vcmax = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)

        # Rubisco-limited rate (Ac)
        ac = vcmax * (ci - self.params.gamma_star) / (ci + self.params.kc * (1 + 210000 / self.params.ko)) # O2 is 21% or 210000 ppm

        # Light-limited rate (Aj)
        # J = (alpha * PAR * Jmax) / sqrt( (alpha * PAR)^2 + Jmax^2 )
        # Simplified light response (non-rectangular hyperbola)
        i2 = self.params.alpha * par_umol_m2_s
        j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
        aj = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))

        # Net assimilation (A) is the minimum of Ac and Aj, minus respiration
        a_net_umol_m2_s = min(ac, aj) - rd

        # Convert from umol CO2/m2/s to g C/m2/day
        # 1 umol CO2 = 12.01 g C / 1,000,000 umol = 1.201e-5 g C
        # Seconds in a day = 24 * 3600 = 86400
        # Assimilation per m2 of leaf area
        g_c_m2_day = a_net_umol_m2_s * 1.201e-5 * 86400

        # Scale by LAI to get assimilation per ground area
        total_g_c_m2_day = g_c_m2_day * lai

        return max(0.0, total_g_c_m2_day)


def create_lettuce_photosynthesis_model() -> PhotosynthesisModel:
    """Create photosynthesis model with lettuce-specific parameters."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        photosynthesis_config = config_loader.get_photosynthesis_parameters()
        parameters = PhotosynthesisParameters.from_config(photosynthesis_config)
        return PhotosynthesisModel(parameters)
    except ImportError:
        # Fallback to default values if config loader not available
        return PhotosynthesisModel()
