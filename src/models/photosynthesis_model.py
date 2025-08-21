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
    kc: float = None            # Michaelis-Menten constant for CO2 (umol/mol)
    ko: float = None            # Michaelis-Menten constant for O2 (umol/mol)
    gamma_star: float = None    # CO2 compensation point for lettuce (umol/mol)
    jmax_25: float = None       # Realistic Jmax for lettuce at 25C (umol/m2/s) 
    vcmax_25: float = None      # Realistic Vcmax for lettuce at 25C (umol/m2/s)
    theta: float = None         # Curvature factor of light response
    phi_psii: float = 0.3       # Quantum yield of PSII (mol e-/mol photons) - biochemical constant
    alpha: float = None         # Realistic quantum efficiency for lettuce (mol CO2/mol photons)
    rd_25: float = None         # Realistic dark respiration for lettuce at 25C (umol CO2/m2/s)
    eaj: float = None           # Activation energy for Jmax (J/mol)
    eav: float = None           # Activation energy for Vcmax (J/mol)
    ear: float = None           # Activation energy for Rd (J/mol)
    r: float = 8.314            # Gas constant (J/mol/K) - physical constant
    
    def __post_init__(self):
        """Load parameters from centralized JSON config if not provided."""
        try:
            from ..utils.config_loader import get_config_loader
            loader = get_config_loader()
            cfg = loader.get_photosynthesis_parameters()

            # Only fill missing fields from config
            if self.kc is None:
                self.kc = cfg.get('kc', 404.0)
            if self.ko is None:
                self.ko = cfg.get('ko', 248.0)
            if self.gamma_star is None:
                self.gamma_star = cfg.get('gamma_star', 42.75)
            if self.jmax_25 is None:
                self.jmax_25 = cfg.get('jmax_25', 150.0)
            if self.vcmax_25 is None:
                self.vcmax_25 = cfg.get('vcmax_25', 80.0)
            if self.theta is None:
                self.theta = cfg.get('theta', 0.90)
            if self.alpha is None:
                self.alpha = cfg.get('alpha', 0.08)
            if self.rd_25 is None:
                self.rd_25 = cfg.get('rd_25', 1.2)
            if self.eaj is None:
                self.eaj = cfg.get('eaj', 30000.0)
            if self.eav is None:
                self.eav = cfg.get('eav', 60000.0)
            if self.ear is None:
                self.ear = cfg.get('ear', 46390.0)
        except Exception:
            # Config loader not available; leave any explicitly provided values as-is
            # and rely on defaults above where needed.
            pass
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'PhotosynthesisParameters':
        """Create PhotosynthesisParameters from configuration dictionary."""
        return cls(
            kc=config_dict.get('kc'),
            ko=config_dict.get('ko'),
            gamma_star=config_dict.get('gamma_star'),
            jmax_25=config_dict.get('jmax_25'),
            vcmax_25=config_dict.get('vcmax_25'),
            theta=config_dict.get('theta'),
            phi_psii=config_dict.get('phi_psii', 0.3),
            alpha=config_dict.get('alpha'),
            rd_25=config_dict.get('rd_25'),
            eaj=config_dict.get('eaj'),
            eav=config_dict.get('eav'),
            ear=config_dict.get('ear'),
            r=config_dict.get('r', 8.314)
        )


class PhotosynthesisModel:
    """Simplified Farquhar-type model for daily carbon assimilation."""

    def __init__(self, parameters: Optional[PhotosynthesisParameters] = None):
        if parameters is None:
            # Load parameters strictly from JSON config
            from ..utils.config_loader import get_config_loader
            loader = get_config_loader()
            p_cfg = loader.get_photosynthesis_parameters()
            self.params = PhotosynthesisParameters.from_dict(p_cfg)
        else:
            self.params = parameters

    def _arrhenius_temp_response(self, rate_25: float, ea: float, temp_c: float) -> float:
        """Calculate temperature response using Arrhenius equation."""
        temp_k = temp_c + 273.15
        return rate_25 * np.exp(ea * (temp_k - 298.15) / (298.15 * self.params.r * temp_k))

    def calculate_daily_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, lai: float, photoperiod_hours: float = 16.0) -> float:
        """Calculate daily carbon assimilation (g C/m2/day).

        Uses photoperiod_hours to integrate over light period rather than 24h.
        """
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
        # Integrate over photoperiod seconds
        photoperiod_seconds = max(0.0, photoperiod_hours) * 3600.0
        # Assimilation per m2 of leaf area
        g_c_m2_day = a_net_umol_m2_s * 1.201e-5 * photoperiod_seconds

        # Scale by LAI to get assimilation per ground area
        total_g_c_m2_day = g_c_m2_day * lai

        return max(0.0, total_g_c_m2_day)



def demonstrate_photosynthesis_model():
    """Demonstrate photosynthesis model with sample conditions."""
    from ..utils.config_loader import get_config_loader
    config_loader = get_config_loader()
    p_config = config_loader.get_photosynthesis_parameters()
    model = PhotosynthesisModel(PhotosynthesisParameters.from_dict(p_config))

    print("=" * 80)
    print("PHOTOSYNTHESIS MODEL DEMONSTRATION")
    print("=" * 80)

    # Sample scenarios: varying PAR and LAI at fixed CO2 and temperature
    co2_ppm = 1200.0
    temp_c = 24.0
    scenarios = [
        (200.0, 1.0),
        (600.0, 2.5),
        (1000.0, 3.5),
        (1500.0, 5.0),
    ]

    print(f"{'PAR':<7} {'LAI':<5} {'Assim gC/m2/day':<18}")
    print("-" * 80)
    for par, lai in scenarios:
        assimilation = model.calculate_daily_assimilation(par, co2_ppm, temp_c, lai)
        print(f"{par:<7.0f} {lai:<5.1f} {assimilation:<18.2f}")


if __name__ == "__main__":
    demonstrate_photosynthesis_model()

