import math
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class ParameterError(Exception):
    """Raised when required parameters are missing"""
    pass


def get_required_water_config(config: Dict[str, Any], param_name: str) -> Dict[str, Any]:
    """Get required water configuration section or raise error if missing"""
    if param_name not in config:
        raise ParameterError(f"Required configuration section '{param_name}' missing from water uptake config")
    return config[param_name]


def get_required_water_param(params: Dict[str, Any], param_name: str) -> float:
    """Get required water parameter or raise error if missing"""
    if param_name not in params:
        raise ParameterError(f"Required water parameter '{param_name}' missing from water parameters")
    return params[param_name]

# =========================
# Water Uptake Model
# =========================

class GrowthStage(Enum):
    VEGETATIVE = "vegetative"
    HEAD_FORMATION = "head_formation"
    MATURE = "mature"

@dataclass
class WaterUptakeParameters:
    """Parameters for water uptake calculations based on Penman-Monteith, SPAC, and physiological demand."""
    # Penman-Monteith parameters
    psychrometric_constant: float           # kPa/°C
    wind_speed: float                      # m/s
    net_radiation_factor: float            # Fraction of solar radiation (0 to 1)
    radiation_offset: float                # MJ/m²/day

    # Crop coefficients
    base_crop_coefficient: float           # Base Kc for lettuce
    lai_coefficient_factor: float          # LAI scaling factor

    # Growth stage factors
    vegetative_stage_factor: float         # Kc multiplier for vegetative stage
    head_formation_stage_factor: float    # Kc multiplier for head formation
    mature_stage_factor: float            # Kc multiplier for mature stage

    # Environmental response
    optimal_temperature: float             # °C
    temperature_sensitivity: float         # Temperature response factor
    optimal_vpd_min: float                 # kPa
    optimal_vpd_max: float                 # kPa
    vpd_sensitivity: float                 # VPD response factor

    # Metabolic water demand
    metabolic_water_per_biomass: float    # L per g biomass
    metabolic_water_per_lai: float        # L per LAI unit

    # Hydraulic parameters
    base_root_conductance: float           # L/day/MPa/m²
    root_conductance_scaling_factor: float # Scaling factor for root conductance
    base_xylem_conductance: float          # L/day/MPa
    xylem_conductance_scaling_factor: float # Scaling factor for xylem conductance

    # Water potential parameters
    base_leaf_potential: float             # MPa
    transpiration_potential_factor: float  # MPa per mm/day
    solution_potential_factor: float       # MPa per dS/m
    cavitation_threshold: float            # MPa

    # Stress parameters
    max_osmotic_adjustment: float         # MPa
    salt_stress_osmotic_factor: float      # Dimensionless

    # Temperature factor parameters
    temp_tolerance: float                 # Temperature tolerance range
    min_temp_factor: float               # Minimum temperature factor
    
    # Biomass allocation parameters
    stem_biomass_fraction: float         # Fraction of total biomass allocated to stem
    
    # Phenology temperature parameters (consolidated)
    phenology_optimal_temperature_min: float  # Minimum optimal temperature from phenology
    phenology_optimal_temperature_max: float  # Maximum optimal temperature from phenology
    leaf_area_to_biomass_ratio: float  # Ratio for converting leaf area to biomass

    # Physical constants (from CSV) - shared across models
    kelvin_conversion: float
    saturation_vapor_pressure_constant: float
    vapor_pressure_temp_coefficient: float
    vapor_pressure_base_temp: float
    saturation_curve_slope_constant: float
    penman_monteith_conversion: float
    aerodynamic_resistance_coefficient: float
    wind_speed_coefficient: float

    # Hardcoded value replacements (from CSV)
    minimum_vpd_threshold: float
    minimum_et0_threshold: float
    max_lai_coverage_factor: float
    max_root_surface_area_factor: float
    cavitation_gradient_denominator: float
    lai_to_light_interception_factor: float
    temperature_response_exponent_denominator: float
    vpd_effect_divisor: float
    transpiration_base_rate_scale_factor: float
    transpiration_scaling_multiplier: float
    lai_coefficient_threshold: float
    minimum_coverage_factor: float
    minimum_cavitation_factor: float
    maximum_vpd_effect: float

    def __post_init__(self):
        """Validate parameter ranges to ensure physical realism."""
        # Check for None values first
        none_params = [k for k, v in vars(self).items() if v is None]
        if none_params:
            raise ValueError(f"Parameters cannot be None: {none_params}")
        if not all(isinstance(p, (int, float)) for p in vars(self).values()):
            raise ValueError("All parameters must be numeric")
        if self.psychrometric_constant is not None and self.psychrometric_constant <= 0:
            raise ValueError("Psychrometric constant must be positive")
        if self.wind_speed < 0:
            raise ValueError("Wind speed must be non-negative")
        if not 0 <= self.net_radiation_factor <= 1:
            raise ValueError("Net radiation factor must be between 0 and 1")
        if self.radiation_offset < 0:
            raise ValueError("Radiation offset must be non-negative")
        if self.base_crop_coefficient <= 0:
            raise ValueError("Base crop coefficient must be positive")
        if self.lai_coefficient_factor <= 0:
            raise ValueError("LAI coefficient factor must be positive")
        if any(f <= 0 for f in [self.vegetative_stage_factor, self.head_formation_stage_factor, self.mature_stage_factor]):
            raise ValueError("Growth stage factors must be positive")
        if self.temperature_sensitivity <= 0:
            raise ValueError("Temperature sensitivity must be positive")
        if self.optimal_vpd_min >= self.optimal_vpd_max or self.optimal_vpd_min < 0:
            raise ValueError("Invalid VPD range: optimal_vpd_min must be less than optimal_vpd_max and non-negative")
        if self.vpd_sensitivity <= 0:
            raise ValueError("VPD sensitivity must be positive")
        if self.metabolic_water_per_biomass <= 0 or self.metabolic_water_per_lai <= 0:
            raise ValueError("Metabolic water demands must be positive")
        if self.base_root_conductance <= 0 or self.base_xylem_conductance <= 0:
            raise ValueError("Hydraulic conductances must be positive")
        if self.root_conductance_scaling_factor <= 0 or self.xylem_conductance_scaling_factor <= 0:
            raise ValueError("Conductance scaling factors must be positive")
        if self.transpiration_potential_factor == 0:
            raise ValueError("Transpiration potential factor cannot be zero")
        if self.solution_potential_factor == 0:
            raise ValueError("Solution potential factor cannot be zero")
        if self.max_osmotic_adjustment <= 0 or self.salt_stress_osmotic_factor <= 0:
            raise ValueError("Stress parameters must be positive")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'WaterUptakeParameters':
        """Create parameters from configuration dictionary."""
        water_params = get_required_water_config(config, 'water_parameters')
        stress_params = get_required_water_config(config, 'stress_parameters')
        root_params = get_required_water_config(config, 'root_system_parameters')
        phenology_params = get_required_water_config(config, 'phenology_parameters')
        required_params = [
            'psychrometric_constant', 'wind_speed', 'net_radiation_factor', 'radiation_offset',
            'base_crop_coefficient', 'lai_coefficient_factor', 'vegetative_stage_factor',
            'head_formation_stage_factor', 'mature_stage_factor', 'optimal_vpd_min',
            'optimal_vpd_max', 'vpd_sensitivity', 'metabolic_water_per_biomass',
            'metabolic_water_per_lai', 'base_root_conductance', 'root_conductance_scaling_factor',
            'base_xylem_conductance', 'xylem_conductance_scaling_factor', 'base_leaf_potential',
            'transpiration_potential_factor', 'solution_potential_factor', 'cavitation_threshold',
            'max_osmotic_adjustment', 'salt_stress_osmotic_factor', 'temp_tolerance', 'min_temp_factor', 'stem_biomass_fraction',
            'optimal_temperature_min', 'optimal_temperature_max', 'leaf_area_to_biomass_ratio',
            # Physical constants
            'kelvin_conversion', 'saturation_vapor_pressure_constant', 'vapor_pressure_temp_coefficient',
            'vapor_pressure_base_temp', 'saturation_curve_slope_constant', 'penman_monteith_conversion',
            'aerodynamic_resistance_coefficient', 'wind_speed_coefficient',
            # Hardcoded value replacements
            'minimum_vpd_threshold', 'minimum_et0_threshold', 'max_lai_coverage_factor',
            'max_root_surface_area_factor', 'cavitation_gradient_denominator', 'lai_to_light_interception_factor',
            'temperature_response_exponent_denominator', 'vpd_effect_divisor', 'transpiration_base_rate_scale_factor',
            'transpiration_scaling_multiplier', 'lai_coefficient_threshold', 'minimum_coverage_factor',
            'minimum_cavitation_factor', 'maximum_vpd_effect'
        ]
        for param in required_params:
            if (param not in water_params and
                param not in stress_params and
                param not in root_params and
                param not in phenology_params):
                raise ValueError(f"Missing required parameter: {param}")
        return cls(
            psychrometric_constant=float(water_params['psychrometric_constant']),
            wind_speed=float(water_params['wind_speed']),
            net_radiation_factor=float(water_params['net_radiation_factor']),
            radiation_offset=float(water_params['radiation_offset']),
            base_crop_coefficient=float(water_params['base_crop_coefficient']),
            lai_coefficient_factor=float(water_params['lai_coefficient_factor']),
            vegetative_stage_factor=float(water_params['vegetative_stage_factor']),
            head_formation_stage_factor=float(water_params['head_formation_stage_factor']),
            mature_stage_factor=float(water_params['mature_stage_factor']),
            optimal_temperature=float(get_required_water_param(water_params, 'optimal_temperature')),
            temperature_sensitivity=float(get_required_water_param(water_params, 'temperature_sensitivity')),
            optimal_vpd_min=float(water_params['optimal_vpd_min']),
            optimal_vpd_max=float(water_params['optimal_vpd_max']),
            vpd_sensitivity=float(water_params['vpd_sensitivity']),
            metabolic_water_per_biomass=float(water_params['metabolic_water_per_biomass']),
            metabolic_water_per_lai=float(water_params['metabolic_water_per_lai']),
            base_root_conductance=float(root_params['base_root_conductance']),
            root_conductance_scaling_factor=float(root_params['root_conductance_scaling_factor']),
            base_xylem_conductance=float(root_params['base_xylem_conductance']),
            xylem_conductance_scaling_factor=float(root_params['xylem_conductance_scaling_factor']),
            base_leaf_potential=float(root_params['base_leaf_potential']),
            transpiration_potential_factor=float(root_params['transpiration_potential_factor']),
            solution_potential_factor=float(root_params['solution_potential_factor']),
            cavitation_threshold=float(root_params['cavitation_threshold']),
            max_osmotic_adjustment=float(stress_params['max_osmotic_adjustment']),
            salt_stress_osmotic_factor=float(stress_params['salt_stress_osmotic_factor']),
            temp_tolerance=float(water_params['temp_tolerance']),
            min_temp_factor=float(water_params['min_temp_factor']),
            stem_biomass_fraction=float(water_params['stem_biomass_fraction']),
            phenology_optimal_temperature_min=float(get_required_water_param(phenology_params, 'optimal_temperature_min')),
            phenology_optimal_temperature_max=float(get_required_water_param(phenology_params, 'optimal_temperature_max')),
            leaf_area_to_biomass_ratio=float(water_params['leaf_area_to_biomass_ratio']),
            # Physical constants
            kelvin_conversion=float(water_params['kelvin_conversion']),
            saturation_vapor_pressure_constant=float(water_params['saturation_vapor_pressure_constant']),
            vapor_pressure_temp_coefficient=float(water_params['vapor_pressure_temp_coefficient']),
            vapor_pressure_base_temp=float(water_params['vapor_pressure_base_temp']),
            saturation_curve_slope_constant=float(water_params['saturation_curve_slope_constant']),
            penman_monteith_conversion=float(water_params['penman_monteith_conversion']),
            aerodynamic_resistance_coefficient=float(water_params['aerodynamic_resistance_coefficient']),
            wind_speed_coefficient=float(water_params['wind_speed_coefficient']),
            # Hardcoded value replacements
            minimum_vpd_threshold=float(water_params['minimum_vpd_threshold']),
            minimum_et0_threshold=float(water_params['minimum_et0_threshold']),
            max_lai_coverage_factor=float(water_params['max_lai_coverage_factor']),
            max_root_surface_area_factor=float(water_params['max_root_surface_area_factor']),
            cavitation_gradient_denominator=float(water_params['cavitation_gradient_denominator']),
            lai_to_light_interception_factor=float(water_params['lai_to_light_interception_factor']),
            temperature_response_exponent_denominator=float(water_params['temperature_response_exponent_denominator']),
            vpd_effect_divisor=float(water_params['vpd_effect_divisor']),
            transpiration_base_rate_scale_factor=float(water_params['transpiration_base_rate_scale_factor']),
            transpiration_scaling_multiplier=float(water_params['transpiration_scaling_multiplier']),
            lai_coefficient_threshold=float(water_params['lai_coefficient_threshold']),
            minimum_coverage_factor=float(water_params['minimum_coverage_factor']),
            minimum_cavitation_factor=float(water_params['minimum_cavitation_factor']),
            maximum_vpd_effect=float(water_params['maximum_vpd_effect'])
        )

@dataclass
class WaterUptakeResponse:
    et0_mm: float                          # Reference evapotranspiration (mm/day)
    kc: float                             # Crop coefficient
    etc_mm: float                         # Crop evapotranspiration (mm/day)
    transpiration_mm: float                # Transpiration component (mm/day)
    transpiration_L: float                 # Transpiration component (L/day)
    metabolic_water_L: float               # Metabolic water demand (L/day)
    total_water_uptake_L: float            # Total water uptake (L/day)
    water_use_efficiency_L_kg: float       # Water use efficiency (L/kg biomass)
    vpd_kpa: float                        # Vapor pressure deficit (kPa)
    environmental_factor: float            # Combined environmental factor (0 to 1)
    temperature_factor: float              # Temperature response factor (0 to 1)
    vpd_factor: float                     # VPD response factor (0 to 1)
    hydraulic_uptake: float                # Hydraulic water uptake rate (L/m²/day)
    total_hydraulic_conductance: float     # Total plant hydraulic conductance (L/day/MPa)

class WaterUptakeModel:
    """
    Water uptake model implementing SPAC-based transpiration and hydraulic flow.
    Combines Penman-Monteith evapotranspiration, plant hydraulic conductance, and osmotic adjustments.
    Scientific basis: Allen et al. (1998) FAO-56, Nobel (2009), Jones (2014).
    """
    def __init__(self, parameters: WaterUptakeParameters):
        if not parameters:
            raise ValueError("WaterUptakeParameters must be provided")
        self.params = parameters
    
    def initialize(self):
        """Initialize the water uptake model"""
        pass

    def calculate_realistic_water_uptake(self,
                                        temperature: float,
                                        humidity: float,
                                        solar_radiation: float,
                                        lai: float,
                                        total_biomass: float,
                                        growth_stage: str = GrowthStage.VEGETATIVE.value,
                                        stress_factors: Dict[str, float] = None,
                                        solution_ec: float = 1.5) -> WaterUptakeResponse:
        """
        Calculate water uptake using Penman-Monteith evapotranspiration.

        Args:
            temperature: Air temperature (°C)
            humidity: Relative humidity (%)
            solar_radiation: Solar radiation (MJ/m²/day)
            lai: Leaf Area Index
            total_biomass: Plant biomass (g)
            growth_stage: Growth stage ('vegetative', 'head_formation', 'mature')

        Returns:
            WaterUptakeResponse with water uptake components
        """
        if not all(isinstance(x, (int, float)) for x in [temperature, humidity, solar_radiation, lai, total_biomass]):
            raise ValueError("All numeric inputs must be numbers")
        if not -50 <= temperature <= 60:
            raise ValueError("Temperature must be between -50 and 60°C")
        if not 0 <= humidity <= 100:
            raise ValueError("Humidity must be between 0 and 100%")
        if solar_radiation < 0:
            raise ValueError("Solar radiation must be non-negative")
        if lai < 0 or total_biomass < 0:
            raise ValueError("LAI and biomass must be non-negative")
        if growth_stage not in [e.value for e in GrowthStage]:
            raise ValueError(f"Growth stage must be one of {[e.value for e in GrowthStage]}")

        # Calculate VPD
        es = self.params.saturation_vapor_pressure_constant * math.exp(self.params.vapor_pressure_temp_coefficient * temperature / (temperature + self.params.vapor_pressure_base_temp))
        ea = es * (humidity / 100.0)
        vpd = max(self.params.minimum_vpd_threshold, es - ea)

        # Penman-Monteith reference evapotranspiration
        delta = self.params.saturation_curve_slope_constant * es / ((temperature + self.params.vapor_pressure_base_temp) ** 2)
        net_radiation = solar_radiation * self.params.net_radiation_factor - self.params.radiation_offset
        numerator = (self.params.penman_monteith_conversion * delta * net_radiation +
                     self.params.psychrometric_constant * self.params.aerodynamic_resistance_coefficient / (temperature + self.params.kelvin_conversion) *
                     self.params.wind_speed * vpd)
        denominator = delta + self.params.psychrometric_constant * (1 + self.params.wind_speed_coefficient * self.params.wind_speed)
        et0_mm = max(self.params.minimum_et0_threshold, numerator / denominator if denominator != 0 else self.params.minimum_et0_threshold)

        # Crop coefficient
        lai_factor = min(1.0, lai / self.params.lai_coefficient_factor) if lai > self.params.lai_coefficient_threshold else self.params.lai_coefficient_threshold
        stage_factors = {
            GrowthStage.VEGETATIVE.value: self.params.vegetative_stage_factor,
            GrowthStage.HEAD_FORMATION.value: self.params.head_formation_stage_factor,
            GrowthStage.MATURE.value: self.params.mature_stage_factor
        }
        if growth_stage not in stage_factors:
            raise ParameterError(f"Required growth stage '{growth_stage}' missing from stage factors")
        stage_factor = stage_factors[growth_stage]
        kc = self.params.base_crop_coefficient * lai_factor * stage_factor

        # Environmental factors
        temp_factor = self._calculate_temperature_factor(temperature)
        vpd_factor = self._calculate_vpd_factor(vpd)
        environmental_factor = temp_factor * vpd_factor

        # Crop evapotranspiration
        etc_mm = et0_mm * kc * environmental_factor

        # Scale by canopy coverage
        coverage_factor = min(1.0, lai / self.params.max_lai_coverage_factor) if lai > 0 else self.params.minimum_coverage_factor
        transpiration_mm = etc_mm * coverage_factor
        transpiration_L = transpiration_mm / 1000.0

        # Metabolic water demand
        metabolic_water_L = total_biomass * self.params.metabolic_water_per_biomass

        # Total water uptake
        total_water_uptake_L = transpiration_L + metabolic_water_L

        # Water use efficiency
        wue_L_per_kg = total_water_uptake_L / (total_biomass / 1000.0) if total_biomass > 0 else 0.0

        # Hydraulic uptake calculation
        # Stress factors must be provided - no defaults allowed per Rules.md
        if stress_factors is None:
            raise ValueError("Stress factors must be provided - no defaults allowed per Rules.md")

        hydraulic_uptake, total_conductance = self.calculate_hydraulic_water_uptake(
            light_interception=min(1.0, lai / self.params.lai_to_light_interception_factor),
            temperature=temperature,
            humidity=humidity,
            solar_radiation=solar_radiation,
            vpd=vpd,
            lai=lai,
            stem_biomass=total_biomass * self.params.stem_biomass_fraction,
            solution_ec=solution_ec,  # Must be provided as parameter
            stress_factors=stress_factors
        )

        return WaterUptakeResponse(
            et0_mm=et0_mm,
            kc=kc,
            etc_mm=etc_mm,
            transpiration_mm=transpiration_mm,
            transpiration_L=transpiration_L,
            metabolic_water_L=metabolic_water_L,
            total_water_uptake_L=total_water_uptake_L,
            water_use_efficiency_L_kg=wue_L_per_kg,
            vpd_kpa=vpd,
            environmental_factor=environmental_factor,
            temperature_factor=temp_factor,
            vpd_factor=vpd_factor,
            hydraulic_uptake=hydraulic_uptake,
            total_hydraulic_conductance=total_conductance
        )

    def calculate_hydraulic_water_uptake(self,
                                        light_interception: float,
                                        temperature: float,
                                        humidity: float,
                                        solar_radiation: float,
                                        vpd: float,
                                        lai: float,
                                        stem_biomass: float,
                                        solution_ec: float,
                                        stress_factors: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate water uptake using SPAC hydraulic model: Flow = (ΨSolution - ΨLeaf) / Resistance.

        Args:
            light_interception: Light interception fraction (0 to 1)
            temperature: Air temperature (°C)
            humidity: Relative humidity (%)
            solar_radiation: Solar radiation (MJ/m²/day)
            vpd: Vapor pressure deficit (kPa)
            lai: Leaf Area Index
            stem_biomass: Stem biomass (g)
            solution_ec: Solution electrical conductivity (dS/m)
            stress_factors: Dictionary with water_stress_level and salinity_stress

        Returns:
            Water uptake rate (L/m²/day)
        """
        if stress_factors is None:
            stress_factors = {}
        if not all(isinstance(x, (int, float)) for x in [light_interception, temperature, humidity, solar_radiation, vpd, lai, stem_biomass, solution_ec]):
            raise ValueError("All numeric inputs must be numbers")
        if not 0 <= light_interception <= 1:
            raise ValueError("Light interception must be between 0 and 1")
        if not -50 <= temperature <= 60:
            raise ValueError("Temperature must be between -50 and 60°C")
        if not 0 <= humidity <= 100:
            raise ValueError("Humidity must be between 0 and 100%")
        if solar_radiation < 0 or vpd < 0 or lai < 0 or stem_biomass < 0 or solution_ec < 0:
            raise ValueError("Solar radiation, VPD, LAI, stem biomass, and solution EC must be non-negative")

        # Calculate transpiration demand
        transpiration_demand = self._calculate_transpiration(light_interception, temperature, vpd, humidity, solar_radiation)

        # Leaf water potential
        transpiration_effect = self.params.transpiration_potential_factor * transpiration_demand
        leaf_water_potential = self.params.base_leaf_potential + transpiration_effect
        osmotic_adjustment = self._calculate_osmotic_adjustment(stress_factors)
        adjusted_leaf_potential = leaf_water_potential + osmotic_adjustment

        # Solution water potential
        solution_water_potential = self.params.solution_potential_factor * solution_ec

        # Hydraulic conductances
        root_surface_area_factor = min(2.0, lai / 2.0)
        root_conductance = self.params.base_root_conductance * root_surface_area_factor
        xylem_conductance = self.params.base_xylem_conductance * math.sqrt(max(1.0, stem_biomass / self.params.xylem_conductance_scaling_factor))
        total_conductance = 1.0 / (1.0 / root_conductance + 1.0 / xylem_conductance) if (root_conductance > 0 and xylem_conductance > 0) else 0.1

        # Water flow
        water_potential_gradient = solution_water_potential - adjusted_leaf_potential
        hydraulic_water_uptake = total_conductance * water_potential_gradient

        # Metabolic water demand
        metabolic_water = lai * self.params.metabolic_water_per_lai

        # Cavitation check
        if adjusted_leaf_potential < self.params.cavitation_threshold:
            cavitation_factor = max(self.params.minimum_cavitation_factor, 1.0 + (adjusted_leaf_potential - self.params.cavitation_threshold) / self.params.cavitation_gradient_denominator)
            hydraulic_water_uptake *= cavitation_factor

        return max(self.params.minimum_et0_threshold, hydraulic_water_uptake + metabolic_water), total_conductance

    def _calculate_temperature_factor(self, temperature: float) -> float:
        """Use consolidated temperature factor calculation from core_utils."""
        from utils.core_utils import calculate_temperature_factor

        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be numeric")

        # Create config structure for consolidated function
        # Calculate optimal_temp from min/max range
        optimal_temp = (self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0
        temp_config = type('Config', (), {
            'temperature_factor': {
                'optimal_temp': optimal_temp,
                'temperature_sensitivity': self.params.temperature_sensitivity,
                'temp_tolerance': self.params.temp_tolerance,
                'min_factor': self.params.min_temp_factor
            }
        })

        return calculate_temperature_factor(temperature, temp_config, method='linear')

    def _calculate_vpd_factor(self, vpd: float) -> float:
        """Calculate VPD response factor (0 to 1)."""
        if not isinstance(vpd, (int, float)):
            raise ValueError("VPD must be numeric")
        if self.params.optimal_vpd_min is None or self.params.optimal_vpd_max is None:
            raise ValueError("optimal_vpd_min and optimal_vpd_max must be provided from CSV")
        if self.params.optimal_vpd_min <= vpd <= self.params.optimal_vpd_max:
            return 1.0
        optimal_mid = (self.params.optimal_vpd_min + self.params.optimal_vpd_max) / 2
        return max(0.5, 1.0 - abs(vpd - optimal_mid) * self.params.vpd_sensitivity)

    def _calculate_transpiration(self,
                                light_interception: float,
                                temperature: float,
                                vpd: float,
                                humidity: float,
                                solar_radiation: float) -> float:
        """Calculate transpiration demand (mm/day)."""
        if not all(isinstance(x, (int, float)) for x in [light_interception, temperature, vpd, humidity, solar_radiation]):
            raise ValueError("All inputs must be numeric")
        energy_available = solar_radiation * max(self.params.minimum_et0_threshold, min(1.0, light_interception))
        temp_effect = max(self.params.minimum_et0_threshold, math.exp(-(temperature - self.params.optimal_temperature) ** 2 / self.params.temperature_response_exponent_denominator))
        vpd_effect = min(self.params.maximum_vpd_effect, vpd / self.params.vpd_effect_divisor) if vpd > 0 else self.params.minimum_et0_threshold
        base_rate = self.params.base_crop_coefficient * self.params.transpiration_base_rate_scale_factor  # Scaled base rate
        transpiration = base_rate * energy_available * temp_effect * vpd_effect * self.params.transpiration_scaling_multiplier
        return max(self.params.minimum_et0_threshold, transpiration)

    def _calculate_osmotic_adjustment(self, stress_factors: Dict[str, Any]) -> float:
        """Calculate osmotic adjustment under stress (MPa)."""
        water_stress = get_required_water_param(stress_factors, 'water_stress_level')
        salt_stress = get_required_water_param(stress_factors, 'salinity_stress')
        if not all(0 <= x <= 1 for x in [water_stress, salt_stress]):
            raise ValueError("Stress levels must be between 0 and 1")
        adjustment = self.params.max_osmotic_adjustment * (water_stress + salt_stress * self.params.salt_stress_osmotic_factor)
        return min(self.params.max_osmotic_adjustment, adjustment)

def create_lettuce_water_uptake_model(system_config: Any) -> WaterUptakeModel:
    """
    Create water uptake model for lettuce from system configuration.

    Args:
        system_config: Configuration with water_parameters, stress_parameters, root_system_parameters

    Returns:
        Configured WaterUptakeModel instance
    """
    if system_config is None:
        raise ValueError("System configuration must be provided")
    config = {
        'water_parameters': getattr(system_config, 'water_parameters', {}),
        'stress_parameters': getattr(system_config, 'stress_parameters', {}),
        'root_system_parameters': getattr(system_config, 'root_system_parameters', {})
    }
    for section in ['water_parameters', 'stress_parameters', 'root_system_parameters']:
        if not config[section]:
            raise ValueError(f"Missing configuration section: {section}")
    parameters = WaterUptakeParameters.from_config(config)
    return WaterUptakeModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- psychrometric_constant: kPa/°C, for Penman-Monteith
- wind_speed: m/s, for Penman-Monteith
- net_radiation_factor: Fraction (0 to 1), for net radiation calculation
- radiation_offset: MJ/m²/day, for net radiation
- base_crop_coefficient: Base Kc for lettuce
- lai_coefficient_factor: LAI scaling factor
- vegetative_stage_factor, head_formation_stage_factor, mature_stage_factor: Kc multipliers
- optimal_temperature: °C, midpoint of optimal range
- temperature_sensitivity: Temperature response factor
- optimal_vpd_min, optimal_vpd_max: kPa, VPD range
- vpd_sensitivity: VPD response factor
- metabolic_water_per_biomass: L/g, metabolic demand
- metabolic_water_per_lai: L/LAI, metabolic demand
- base_root_conductance: L/day/MPa/m², root hydraulic conductance
- root_conductance_scaling_factor: Scaling factor for root conductance
- base_xylem_conductance: L/day/MPa, xylem hydraulic conductance
- xylem_conductance_scaling_factor: Scaling factor for xylem conductance
- base_leaf_potential: MPa, baseline leaf water potential
- transpiration_potential_factor: MPa per mm/day, transpiration effect
- solution_potential_factor: MPa per dS/m, solution EC effect
- cavitation_threshold: MPa, cavitation limit
- max_osmotic_adjustment: MPa, maximum osmotic adjustment
- salt_stress_osmotic_factor: Dimensionless, salinity stress effect

OUTPUT VARIABLES (WaterUptakeResponse):
- et0_mm: Reference evapotranspiration (mm/day)
- kc: Crop coefficient
- etc_mm: Crop evapotranspiration (mm/day)
- transpiration_mm: Transpiration component (mm/day)
- transpiration_L: Transpiration component (L/day)
- metabolic_water_L: Metabolic water demand (L/day)
- total_water_uptake_L: Total water uptake (L/day)
- water_use_efficiency_L_kg: Water use efficiency (L/kg biomass)
- vpd_kpa: Vapor pressure deficit (kPa)
- environmental_factor: Combined environmental factor (0 to 1)
- temperature_factor: Temperature response factor (0 to 1)
- vpd_factor: VPD response factor (0 to 1)
- hydraulic_uptake: Hydraulic water uptake rate (L/m²/day)
"""