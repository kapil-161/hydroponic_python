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
    o2_mmol_mol: float = 210.0  # Atmospheric O2 concentration in mmol/mol (≈21%)
    ci_fraction: float = 0.75    # Internal CO2 fraction of ambient (stomatal limitation)
    
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
            # Optional override for O2 concentration (mmol/mol) with validation
            self.o2_mmol_mol = self._validate_parameter(
                cfg.get('o2_mmol_mol', cfg.get('O2_MMOL_MOL', 210.0)),
                200.0, 220.0, 210.0, 'o2_mmol_mol'
            )
            # Internal CO2 fraction (0.65–0.85 typical for C3) with validation
            self.ci_fraction = self._validate_parameter(
                cfg.get('ci_fraction', cfg.get('CI_FRACTION', 0.75)),
                0.65, 0.85, 0.75, 'ci_fraction'
            )
        except Exception:
            # Config loader not available; leave any explicitly provided values as-is
            # and rely on defaults above where needed.
            pass
    
    def _validate_parameter(self, value: float, min_val: float, max_val: float, default: float, param_name: str) -> float:
        """Validate parameter is within biological bounds."""
        if value is None:
            return default
        if not (min_val <= value <= max_val):
            import warnings
            warnings.warn(f"Parameter {param_name}={value} outside valid range [{min_val}, {max_val}]. Using default {default}")
            return default
        return value
    
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
        Includes real-world light penetration and shading constraints.
        """
        # Convert CO2 ppm to umol/mol and apply stomatal limitation
        ci = co2_ppm * self.params.ci_fraction

        # Temperature-adjusted rates with enzyme saturation constraints
        vcmax_base = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax_base = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)
        
        # Real-world enzyme saturation at high LAI
        # RuBisCO and electron transport capacity don't scale infinitely with leaf area
        if lai > 5.0:
            # Enzyme limitation factor - diminishing returns above LAI 5
            enzyme_saturation_factor = 1.0 - 0.1 * (lai - 5.0)  # 10% reduction per LAI unit above 5
            enzyme_saturation_factor = max(0.3, enzyme_saturation_factor)  # Minimum 30% capacity
            vcmax = vcmax_base * enzyme_saturation_factor
            jmax = jmax_base * enzyme_saturation_factor
        else:
            vcmax = vcmax_base
            jmax = jmax_base

        # Rubisco-limited rate (Ac)
        # O2 concentration: convert mmol/mol to μmol/mol for consistency with ci and kinetic constants
        o2_umol_mol = self.params.o2_mmol_mol * 1000.0  # 210 mmol/mol → 210,000 μmol/mol
        ac = vcmax * (ci - self.params.gamma_star) / (ci + self.params.kc * (1 + o2_umol_mol / self.params.ko))

        # Light-limited rate (Aj)
        # J = (alpha * PAR * Jmax) / sqrt( (alpha * PAR)^2 + Jmax^2 )
        # Simplified light response (non-rectangular hyperbola)
        i2 = self.params.alpha * par_umol_m2_s
        j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
        aj = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))

        # Net carbon: integrate gross photosynthesis over photoperiod 
        # NOTE: Dark respiration is handled separately by the respiration model
        # to avoid double-counting and unit mismatches
        photoperiod_seconds = max(0.0, photoperiod_hours) * 3600.0
        gross_day_umol = max(0.0, min(ac, aj)) * photoperiod_seconds
        # Do NOT subtract respiration here - it's handled by the respiration model
        net_umol_day = gross_day_umol
        # Convert from umol CO2 to g C: 1 umol CO2 ≈ 1.201e-5 g C
        g_c_m2_day = max(0.0, net_umol_day) * 1.201e-5

        # Real-world light penetration constraints
        # Effective LAI decreases with canopy density due to shading
        if lai > 6.0:
            # Severe shading above LAI 6 - diminishing returns
            light_penetration_factor = 6.0 / lai  # Linear decline in effectiveness
            effective_par = par_umol_m2_s * light_penetration_factor
            
            # Recalculate with reduced light
            i2 = self.params.alpha * effective_par
            j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
            aj_shaded = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))
            
            photoperiod_seconds = max(0.0, photoperiod_hours) * 3600.0
            gross_day_umol_shaded = max(0.0, min(ac, aj_shaded)) * photoperiod_seconds
            net_umol_day = gross_day_umol_shaded
            g_c_m2_day = max(0.0, net_umol_day) * 1.201e-5
            
            # Only 6.0 effective LAI contributes fully, rest at diminishing returns
            effective_lai = 6.0 + (lai - 6.0) * 0.2  # 20% efficiency for excess canopy
        else:
            effective_lai = lai
        
        # Scale by effective LAI to get realistic assimilation per ground area
        total_g_c_m2_day = g_c_m2_day * effective_lai

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

