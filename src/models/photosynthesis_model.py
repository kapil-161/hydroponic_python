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
            ci_fraction=float(config_dict['ci_fraction']),
            
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
    """Simplified Farquhar-type model for daily carbon assimilation."""

    def __init__(self, parameters: Optional[PhotosynthesisParameters] = None):
        if parameters is None:
            raise ValueError("❌ PhotosynthesisParameters required - no hardcoded defaults allowed")
        self.params = parameters

    def _arrhenius_temp_response(self, rate_25: float, ea: float, temp_c: float) -> float:
        """Calculate temperature response using Arrhenius equation."""
        temp_k = float(temp_c) + 273.15
        return rate_25 * np.exp(ea * (temp_k - 298.15) / (298.15 * self.params.r * temp_k))

    def calculate_hourly_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, 
                                     lai: float, hour: int, ec_factor: float, 
                                     config_dict: Optional[Dict[str, Any]] = None,
                                     sunlit_lai: Optional[float] = None, 
                                     shaded_lai: Optional[float] = None) -> float:
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
        if par_umol_m2_s <= self.params.min_par_threshold:
            return 0.0
        
        # Use provided sunlit/shaded LAI or fall back to total LAI if not available
        if sunlit_lai is None:
            sunlit_lai = lai
        if shaded_lai is None:
            shaded_lai = 0.0
            
        # Ensure sunlit + shaded = total LAI
        if abs((sunlit_lai + shaded_lai) - lai) > 0.001:
            # Normalize to ensure they sum to total LAI
            total_calculated = sunlit_lai + shaded_lai
            if total_calculated > 0:
                sunlit_lai = (sunlit_lai / total_calculated) * lai
                shaded_lai = (shaded_lai / total_calculated) * lai
            else:
                sunlit_lai = lai
                shaded_lai = 0.0
        
        # Calculate photosynthesis for sunlit portion
        sunlit_photosynthesis = self._calculate_instantaneous_assimilation(
            par_umol_m2_s, co2_ppm, temp_c, sunlit_lai, ec_factor, config_dict
        )
        
        # Calculate photosynthesis for shaded portion with reduced light
        if shaded_lai > 0:
            # Shaded leaves receive diffuse light only
            # Use a fraction of the incident PAR for shaded leaves
            shaded_par = par_umol_m2_s * self.params.shaded_light_fraction if hasattr(self.params, 'shaded_light_fraction') else par_umol_m2_s * 0.3
            
            shaded_photosynthesis = self._calculate_instantaneous_assimilation(
                shaded_par, co2_ppm, temp_c, shaded_lai, ec_factor, config_dict
            )
        else:
            shaded_photosynthesis = 0.0
        
        # Total canopy photosynthesis is sum of sunlit and shaded portions
        total_canopy_photosynthesis = sunlit_photosynthesis + shaded_photosynthesis
        
        return total_canopy_photosynthesis
    
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
        if config_dict is None:
            raise ValueError("❌ Configuration dictionary required for LAI thresholds - no hardcoded defaults allowed")
        
        enzyme_saturation_lai = config_dict.get('enzyme_saturation_lai')
        light_penetration_lai = config_dict.get('light_penetration_lai')
        
        if enzyme_saturation_lai is None or light_penetration_lai is None:
            raise ValueError("❌ LAI thresholds must be provided in CSV configuration - no hardcoded defaults allowed")
        
        # Enzyme saturation at high LAI
        if lai > enzyme_saturation_lai:
            enzyme_saturation_factor = 1.0 - self.params.enzyme_saturation_rate * (lai - enzyme_saturation_lai)
            enzyme_saturation_factor = max(self.params.min_enzyme_factor, enzyme_saturation_factor)
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
        

        
        # Convert to hourly g C/m² (3600 seconds/hour, configurable g C/μmol CO2)
        hourly_g_c_per_m2 = net_photosynthesis_rate * 3600.0 * self.params.umol_to_g_carbon_ratio
        
        # Scale by LAI to get total assimilation for this portion per ground area
        # The calling function handles sunlit/shaded LAI separation
        total_hourly_assimilation = hourly_g_c_per_m2 * lai * ec_factor
        
        return max(0.0, total_hourly_assimilation)

    def calculate_daily_assimilation(self, par_umol_m2_s: float, co2_ppm: float, temp_c: float, lai: float, photoperiod_hours: float, ec_factor: float, config_dict: Optional[Dict[str, Any]] = None, sunlit_lai: Optional[float] = None, shaded_lai: Optional[float] = None) -> float:
        """Calculate daily carbon assimilation (g C/m2 ground area/day).

        This function calculates photosynthesis separately for sunlit and shaded portions
        of the canopy, then sums them to get total canopy assimilation per unit ground area.
        
        Uses photoperiod_hours to integrate over light period rather than 24h.
        Includes real-world light penetration and shading constraints.
        
        Args:
            par_umol_m2_s: Photosynthetically active radiation (μmol/m²/s)
            co2_ppm: CO2 concentration (ppm)
            temp_c: Temperature (°C)
            lai: Total leaf area index
            photoperiod_hours: Photoperiod length (hours)
            ec_factor: EC stress factor
            config_dict: Configuration dictionary with LAI thresholds
            sunlit_lai: Sunlit leaf area index (if None, will use total LAI)
            shaded_lai: Shaded leaf area index (if None, will use 0)
        """
        # Convert CO2 ppm to umol/mol and apply stomatal limitation
        ci = co2_ppm * self.params.ci_fraction

        # Temperature-adjusted rates with enzyme saturation constraints
        vcmax_base = self._arrhenius_temp_response(self.params.vcmax_25, self.params.eav, temp_c)
        jmax_base = self._arrhenius_temp_response(self.params.jmax_25, self.params.eaj, temp_c)
        rd = self._arrhenius_temp_response(self.params.rd_25, self.params.ear, temp_c)
        
        # Load LAI thresholds from CSV configuration
        enzyme_saturation_lai = config_dict.get('enzyme_saturation_lai')
        light_penetration_lai = config_dict.get('light_penetration_lai')
        
        if enzyme_saturation_lai is None or light_penetration_lai is None:
            raise ValueError("❌ LAI thresholds must be provided in CSV configuration - no hardcoded defaults allowed")
        
        # Use provided sunlit/shaded LAI or fall back to total LAI if not available
        if sunlit_lai is None:
            sunlit_lai = lai
        if shaded_lai is None:
            shaded_lai = 0.0
            
        # Ensure sunlit + shaded = total LAI
        if abs((sunlit_lai + shaded_lai) - lai) > 0.001:
            # Normalize to ensure they sum to total LAI
            total_calculated = sunlit_lai + shaded_lai
            if total_calculated > 0:
                sunlit_lai = (sunlit_lai / total_calculated) * lai
                shaded_lai = (shaded_lai / total_calculated) * lai
            else:
                sunlit_lai = lai
                shaded_lai = 0.0
        
        # Calculate photosynthesis for sunlit portion
        sunlit_photosynthesis = self._calculate_portion_photosynthesis(
            par_umol_m2_s, ci, temp_c, sunlit_lai, photoperiod_hours,
            vcmax_base, jmax_base, rd, enzyme_saturation_lai, light_penetration_lai
        )
        
        # Calculate photosynthesis for shaded portion with reduced light
        if shaded_lai > 0:
            # Shaded leaves receive diffuse light only
            # Use a fraction of the incident PAR for shaded leaves
            shaded_par = par_umol_m2_s * self.params.shaded_light_fraction if hasattr(self.params, 'shaded_light_fraction') else par_umol_m2_s * 0.3
            
            shaded_photosynthesis = self._calculate_portion_photosynthesis(
                shaded_par, ci, temp_c, shaded_lai, photoperiod_hours,
                vcmax_base, jmax_base, rd, enzyme_saturation_lai, light_penetration_lai
            )
        else:
            shaded_photosynthesis = 0.0
        
        # Total canopy photosynthesis is sum of sunlit and shaded portions
        total_canopy_photosynthesis = sunlit_photosynthesis + shaded_photosynthesis
        
        # Apply EC stress factor to final photosynthesis
        total_canopy_photosynthesis *= ec_factor
        
        return max(0.0, total_canopy_photosynthesis)
    
    def _calculate_portion_photosynthesis(self, par_umol_m2_s: float, ci: float, temp_c: float, 
                                        portion_lai: float, photoperiod_hours: float,
                                        vcmax_base: float, jmax_base: float, rd: float,
                                        enzyme_saturation_lai: float, light_penetration_lai: float) -> float:
        """Calculate photosynthesis for a specific portion of the canopy (sunlit or shaded).
        
        Args:
            par_umol_m2_s: Photosynthetically active radiation (μmol/m²/s)
            ci: Internal CO2 concentration (μmol/mol)
            temp_c: Temperature (°C)
            portion_lai: Leaf area index for this portion
            photoperiod_hours: Photoperiod length (hours)
            vcmax_base: Base Vcmax at current temperature
            jmax_base: Base Jmax at current temperature
            rd: Dark respiration rate
            enzyme_saturation_lai: LAI threshold for enzyme saturation
            light_penetration_lai: LAI threshold for light penetration
            
        Returns:
            Photosynthesis for this portion (g C/m² ground area/day)
        """
        if portion_lai <= 0:
            return 0.0
            
        # Real-world enzyme saturation at high LAI
        # RuBisCO and electron transport capacity don't scale infinitely with leaf area
        if portion_lai > enzyme_saturation_lai:
            # Enzyme limitation factor - diminishing returns above threshold
            enzyme_saturation_factor = 1.0 - self.params.enzyme_saturation_rate * (portion_lai - enzyme_saturation_lai)
            enzyme_saturation_factor = max(self.params.min_enzyme_factor, enzyme_saturation_factor)
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

        # Net photosynthesis: subtract dark respiration
        net_photosynthesis_rate = max(0.0, min(ac, aj) - rd)
        
        # Integrate net photosynthesis over photoperiod
        photoperiod_seconds = max(0.0, photoperiod_hours) * self.params.seconds_per_hour
        net_day_umol = net_photosynthesis_rate * photoperiod_seconds
        
        # Dark respiration continues during dark period
        dark_period_hours = max(0.0, self.params.hours_per_day - photoperiod_hours)
        dark_period_seconds = dark_period_hours * self.params.seconds_per_hour
        dark_respiration_umol = rd * dark_period_seconds
        
        # Total daily net carbon for this portion
        net_umol_day = max(0.0, net_day_umol - dark_respiration_umol)
        
        # Convert from umol CO2 to g C
        g_c_m2_day = max(0.0, net_umol_day) * self.params.umol_to_g_carbon_ratio
        
        # Scale by portion LAI to get total assimilation for this portion per ground area
        total_g_c_m2_day = g_c_m2_day * portion_lai
        
        return max(0.0, total_g_c_m2_day)


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
        
    # Get photosynthesis parameters from CSV data loaded in system_config
    photosynthesis_params = getattr(system_config, 'photosynthesis_parameters', None)
    if photosynthesis_params is None:
        photosynthesis_params = getattr(system_config, 'photosynthesis', None)
    
    if photosynthesis_params is None:
        raise ValueError("❌ photosynthesis parameters missing from CSV - no fallback defaults allowed")
    
    # Validate required CSV parameters
    required_params = ['kc', 'ko', 'gamma_star', 'jmax_25', 'vcmax_25', 'theta', 'alpha', 'rd_25', 'eaj', 'eav', 'ear', 'phi_psii', 'r', 'ci_fraction', 'o2_mmol_mol']
    missing_params = [p for p in required_params if p not in photosynthesis_params]
    if missing_params:
        available_params = list(photosynthesis_params.keys())
        raise ValueError(f"❌ Missing required photosynthesis parameters in CSV: {missing_params}. Available: {available_params}")
    
    # Create parameters from CSV config only
    parameters = PhotosynthesisParameters.from_config(photosynthesis_params)
    return PhotosynthesisModel(parameters)


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file models photosynthesis - the process where plants use light, CO2, and water to make 
food (sugar). Think of it as modeling the "solar panel + factory" system in leaves that 
converts sunlight into plant growth.

KEY FUNCTIONS AND EQUATIONS:

1. calculate_daily_assimilation()
   - What it does: Calculates how much carbon (sugar) the plant produces in one day
   - Uses: Farquhar-von Caemmerer-Berry model (the gold standard for photosynthesis)
   - Real-world meaning: Like calculating how much electricity your solar panels produce 
     per day based on sunlight, temperature, and panel efficiency.

2. _arrhenius_temp_response()
   - What it does: Calculates how temperature affects enzyme activity in photosynthesis
   - Equation: rate = base_rate × exp(activation_energy × (T - 25°C) / (25°C × R × T))
   - Real-world meaning: Enzymes work faster when warm, slower when cold. Like how you 
     move faster on a warm day vs a cold day. But too hot damages the enzymes.

3. Rubisco-limited rate (Ac)
   - What it does: Calculates photosynthesis when the Rubisco enzyme is the bottleneck
   - Equation: Ac = Vcmax × (Ci - Γ*) / (Ci + Kc × (1 + O2/Ko))
   - Real-world meaning: Rubisco is the main enzyme that "catches" CO2. When CO2 is low 
     or Rubisco is saturated, this becomes the limiting factor. Like having only one 
     cashier at a busy store - the cashier speed limits everything.

4. Light-limited rate (Aj)
   - What it does: Calculates photosynthesis when light capture is the bottleneck
   - Equations: 
     * J = (I + Jmax - √((I + Jmax)² - 4θIJmax)) / 2θ
     * Aj = J × (Ci - Γ*) / (4(Ci + 2Γ*))
   - Real-world meaning: When light is dim, the "solar panels" in leaves can't capture 
     enough energy to run the factory at full speed. Like trying to work in a dark room.

5. Net photosynthesis calculation
   - What it does: Subtracts plant "breathing" (respiration) from gross photosynthesis
   - Equation: Net = min(Ac, Aj) - Rd
   - Real-world meaning: Plants use some of their own sugar for maintenance and growth 
     (respiration). Net photosynthesis = total production - plant's own consumption.

KEY PHOTOSYNTHESIS CONCEPTS:

LIMITING FACTORS:
- Rubisco-limited: Not enough enzyme or too little CO2
- Light-limited: Not enough light energy
- The slowest process limits overall rate (like weakest link in chain)

TEMPERATURE EFFECTS:
- Low temperatures: Enzymes work slowly
- Optimal temperatures: Maximum enzyme activity  
- High temperatures: Enzyme damage and increased respiration

CO2 EFFECTS:
- Higher CO2 = more photosynthesis (up to a point)
- CO2 enhancement: 20-30% yield increase possible with enrichment
- Diminishing returns: Eventually other factors become limiting

LIGHT EFFECTS:
- More light = more energy for photosynthesis
- Light saturation: Eventually photosystem capacity is exceeded
- Daily integration: Total production depends on both intensity and duration

LAI (LEAF AREA INDEX) EFFECTS:
- More leaves = more "solar panels" = more photosynthesis
- But leaves shade each other, reducing efficiency per leaf
- Optimal LAI balances total capture vs per-leaf efficiency

ENVIRONMENTAL INTERACTIONS:
- EC stress: High salt reduces photosynthesis efficiency
- Water stress: Stomata close, reducing CO2 uptake
- Nutrient stress: Reduces enzyme production and chlorophyll

PRACTICAL APPLICATIONS:
- Optimize light intensity and duration for maximum carbon gain
- Design CO2 enrichment strategies for best return on investment
- Predict yield based on environmental conditions
- Time harvests when daily carbon gain starts declining
- Manage leaf area for optimal light interception
- Design greenhouse climate control for maximum photosynthesis

This system helps growers understand how environmental factors affect the fundamental 
process that drives all plant growth - converting sunlight into plant biomass.
"""



