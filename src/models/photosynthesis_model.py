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
    # Required parameters (no defaults)
    phi_psii: float       # Quantum yield of PSII (mol e-/mol photons)
    r: float            # Gas constant (J/mol/K)
    ci_fraction: float    # Internal CO2 fraction of ambient (stomatal limitation)
    
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
            kc=config_dict['kc'],
            ko=config_dict['ko'],
            gamma_star=config_dict['gamma_star'],
            
            # Maximum rates at 25C
            jmax_25=config_dict['jmax_25'],
            vcmax_25=config_dict['vcmax_25'],
            
            # Light response parameters
            theta=config_dict['theta'],
            alpha=config_dict['alpha'],
            
            # Respiration
            rd_25=config_dict['rd_25'],
            
            # Activation energies
            eaj=config_dict['eaj'],
            eav=config_dict['eav'],
            ear=config_dict['ear'],
            
            # Required parameters
            phi_psii=config_dict['phi_psii'],
            r=config_dict['r'],
            ci_fraction=config_dict['ci_fraction'],
            
            # Physical constants
            o2_mmol_mol=config_dict['o2_mmol_mol']
        )
    


class PhotosynthesisModel:
    """Simplified Farquhar-type model for daily carbon assimilation."""

    def __init__(self, parameters: Optional[PhotosynthesisParameters] = None):
        self.params = parameters or PhotosynthesisParameters()

    def _arrhenius_temp_response(self, rate_25: float, ea: float, temp_c: float) -> float:
        """Calculate temperature response using Arrhenius equation."""
        temp_k = float(temp_c) + 273.15
        return rate_25 * np.exp(ea * (temp_k - 298.15) / (298.15 * self.params.r * temp_k))

    def calculate_hourly_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, 
                                     lai: float, hour: int, ec_factor: float = 1.0, 
                                     config_dict: Optional[Dict[str, Any]] = None) -> float:
        """Calculate hourly carbon assimilation (g C/m2 ground area/hour).
        
        DSSAT-style hourly photosynthesis calculation for internal integration.
        
        Args:
            par_umol_m2_s: Photosynthetic active radiation (μmol/m²/s)
            co2_ppm: CO2 concentration (ppm)
            temp_c: Temperature (°C)
            lai: Leaf area index
            hour: Hour of day (0-23) for light-dependent calculations
            ec_factor: EC stress factor (0-1)
            config_dict: Additional configuration parameters
            
        Returns:
            Hourly carbon assimilation (g C/m²/hour)
        """
        # No photosynthesis during night hours or with zero PAR
        if par_umol_m2_s <= 0.1:
            return 0.0
            
        return self._calculate_instantaneous_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, lai, ec_factor, config_dict
        )
    
    def _calculate_instantaneous_assimilation(self, par_umol_m2_s: float, co2_ppm: float, 
                                            temp_c: float, lai: float, ec_factor: float = 1.0, 
                                            config_dict: Optional[Dict[str, Any]] = None) -> float:
        """Calculate instantaneous photosynthesis rate (g C/m²/hour).
        
        Core Farquhar model calculation extracted for hourly integration.
        """
        # Convert CO2 ppm to umol/mol and apply stomatal limitation
        ci = co2_ppm * self.params.ci_fraction

        # Temperature-adjusted rates
        vcmax_base = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax_base = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)
        
        # Load LAI thresholds from CSV configuration
        enzyme_saturation_lai = 5.0
        light_penetration_lai = 6.0
        
        if config_dict:
            enzyme_saturation_lai = config_dict.get('enzyme_saturation_lai', 5.0)
            light_penetration_lai = config_dict.get('light_penetration_lai', 6.0)
        
        # Enzyme saturation at high LAI
        if lai > enzyme_saturation_lai:
            enzyme_saturation_factor = 1.0 - 0.1 * (lai - enzyme_saturation_lai)
            enzyme_saturation_factor = max(0.3, enzyme_saturation_factor)
            vcmax = vcmax_base * enzyme_saturation_factor
            jmax = jmax_base * enzyme_saturation_factor
        else:
            vcmax = vcmax_base
            jmax = jmax_base

        # Rubisco-limited rate (Ac)
        o2_umol_mol = self.params.o2_mmol_mol * 1000.0
        ko_umol_mol = self.params.ko * 1000.0
        ac = vcmax * (ci - self.params.gamma_star) / (ci + self.params.kc * (1 + o2_umol_mol / ko_umol_mol))

        # Light-limited rate (Aj)
        i2 = self.params.alpha * par_umol_m2_s
        j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
        aj = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))

        # Net photosynthesis rate (μmol CO2/m²/s)
        net_photosynthesis_rate = max(0.0, min(ac, aj) - rd)
        
        # Convert to hourly g C/m² (3600 seconds/hour, 1.201e-5 g C/μmol CO2)
        hourly_g_c_per_m2 = net_photosynthesis_rate * 3600.0 * 1.201e-5
        
        # Handle light penetration constraints
        if lai > light_penetration_lai:
            light_penetration_factor = light_penetration_lai / lai
            effective_par = par_umol_m2_s * light_penetration_factor
            
            # Recalculate with reduced light
            i2 = self.params.alpha * effective_par
            j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
            aj_shaded = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))
            
            net_rate_shaded = max(0.0, min(ac, aj_shaded) - rd)
            hourly_g_c_per_m2 = net_rate_shaded * 3600.0 * 1.201e-5
            
            effective_lai = light_penetration_lai + (lai - light_penetration_lai) * 0.2
        else:
            effective_lai = lai
        
        # Scale by effective LAI and apply stress factors
        total_hourly_assimilation = hourly_g_c_per_m2 * effective_lai * ec_factor
        
        return max(0.0, total_hourly_assimilation)

    def calculate_daily_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, lai: float, photoperiod_hours: float = 16.0, ec_factor: float = 1.0, config_dict: Optional[Dict[str, Any]] = None) -> float:
        """Calculate daily carbon assimilation (g C/m2 ground area/day).

        This function calculates photosynthesis PER UNIT LEAF AREA first, then scales by 
        effective LAI to get total canopy assimilation per unit ground area.
        
        Uses photoperiod_hours to integrate over light period rather than 24h.
        Includes real-world light penetration and shading constraints.
        """
        # Convert CO2 ppm to umol/mol and apply stomatal limitation
        ci = co2_ppm * self.params.ci_fraction

        # Temperature-adjusted rates with enzyme saturation constraints
        vcmax_base = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax_base = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)
        
        # Load LAI thresholds from CSV configuration
        enzyme_saturation_lai = 5.0  # Default
        light_penetration_lai = 6.0  # Default
        
        if config_dict:
            enzyme_saturation_lai = config_dict.get('enzyme_saturation_lai', 5.0)
            light_penetration_lai = config_dict.get('light_penetration_lai', 6.0)
        
        # Real-world enzyme saturation at high LAI
        # RuBisCO and electron transport capacity don't scale infinitely with leaf area
        if lai > enzyme_saturation_lai:
            # Enzyme limitation factor - diminishing returns above threshold
            enzyme_saturation_factor = 1.0 - 0.1 * (lai - enzyme_saturation_lai)
            enzyme_saturation_factor = max(0.3, enzyme_saturation_factor)  # Minimum 30% capacity
            vcmax = vcmax_base * enzyme_saturation_factor
            jmax = jmax_base * enzyme_saturation_factor
        else:
            vcmax = vcmax_base
            jmax = jmax_base

        # Rubisco-limited rate (Ac)
        # O2 concentration: convert mmol/mol to μmol/mol for consistency with ci and kinetic constants
        o2_umol_mol = self.params.o2_mmol_mol * 1000.0  # 210 mmol/mol → 210,000 μmol/mol
        ko_umol_mol = self.params.ko * 1000.0  # Convert Ko from mmol/mol to μmol/mol
        ac = vcmax * (ci - self.params.gamma_star) / (ci + self.params.kc * (1 + o2_umol_mol / ko_umol_mol))

        # Light-limited rate (Aj)
        # J = (alpha * PAR * Jmax) / sqrt( (alpha * PAR)^2 + Jmax^2 )
        # Simplified light response (non-rectangular hyperbola)
        i2 = self.params.alpha * par_umol_m2_s
        j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
        aj = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))

        # Net photosynthesis: subtract dark respiration (Farquhar model standard)
        # Dark respiration occurs during both light and dark periods
        net_photosynthesis_rate = max(0.0, min(ac, aj) - rd)
        
        # Integrate net photosynthesis over photoperiod
        photoperiod_seconds = max(0.0, photoperiod_hours) * 3600.0
        net_day_umol = net_photosynthesis_rate * photoperiod_seconds
        
        # Dark respiration continues during dark period (24 - photoperiod_hours)
        dark_period_hours = max(0.0, 24.0 - photoperiod_hours)
        dark_period_seconds = dark_period_hours * 3600.0
        dark_respiration_umol = rd * dark_period_seconds
        
        # Total daily net carbon = net photosynthesis - dark period respiration
        net_umol_day = max(0.0, net_day_umol - dark_respiration_umol)
        # Convert from umol CO2 to g C: 1 umol CO2 ≈ 1.201e-5 g C
        g_c_m2_day = max(0.0, net_umol_day) * 1.201e-5

        # Real-world light penetration constraints using CSV parameters
        # Effective LAI decreases with canopy density due to shading
        if lai > light_penetration_lai:
            # Severe shading above threshold - diminishing returns
            light_penetration_factor = light_penetration_lai / lai  # Linear decline in effectiveness
            effective_par = par_umol_m2_s * light_penetration_factor
            
            # Recalculate with reduced light
            i2 = self.params.alpha * effective_par
            j = (i2 + jmax - np.sqrt((i2 + jmax)**2 - 4 * self.params.theta * i2 * jmax)) / (2 * self.params.theta)
            aj_shaded = j * (ci - self.params.gamma_star) / (4 * (ci + 2 * self.params.gamma_star))
            
            photoperiod_seconds = max(0.0, photoperiod_hours) * 3600.0
            gross_day_umol_shaded = max(0.0, min(ac, aj_shaded)) * photoperiod_seconds
            net_umol_day = gross_day_umol_shaded
            g_c_m2_day = max(0.0, net_umol_day) * 1.201e-5
            
            # Only threshold LAI contributes fully, rest at diminishing returns
            effective_lai = light_penetration_lai + (lai - light_penetration_lai) * 0.2  # 20% efficiency for excess canopy
        else:
            effective_lai = lai
        
        # Scale by effective LAI to get total canopy assimilation per ground area
        # g_c_m2_day is per unit leaf area, effective_lai converts to per unit ground area
        total_g_c_m2_day = g_c_m2_day * effective_lai
        
        # Apply EC stress factor to final photosynthesis
        # EC stress affects stomatal conductance and nutrient availability
        total_g_c_m2_day *= ec_factor


        return max(0.0, total_g_c_m2_day)


def create_lettuce_photosynthesis_model(system_config=None) -> PhotosynthesisModel:
    """Create photosynthesis model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        PhotosynthesisModel configured with CSV parameters
    """
    try:
        # Get photosynthesis parameters from CSV data loaded in system_config
        photosynthesis_params = getattr(system_config, 'photosynthesis_parameters', {})
        
        # Create parameters from CSV config
        parameters = PhotosynthesisParameters.from_config(photosynthesis_params)
        return PhotosynthesisModel(parameters)
        
    except Exception as e:
        print(f"Warning: Could not load CSV photosynthesis parameters: {e}")
        print("Using default photosynthesis parameters")
        return PhotosynthesisModel()



