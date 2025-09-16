"""
Water Uptake Model for Hydroponic Systems

This module implements water uptake calculations based on:
1. Penman-Monteith evapotranspiration
2. Soil-Plant-Atmosphere Continuum (SPAC) hydraulics
3. Plant physiological water demand

Scientific basis:
- Allen, R.G., et al. (1998). FAO Irrigation and Drainage Paper 56
- Nobel, P.S. (2009). Physicochemical and Environmental Plant Physiology
- Jones, H.G. (2014). Plants and Microclimate
"""

import math
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class WaterUptakeParameters:
    """Parameters for water uptake calculations."""

    # Penman-Monteith parameters
    psychrometric_constant: float           # kPa/°C
    wind_speed: float                       # m/s
    net_radiation_factor: float             # Fraction of solar radiation
    radiation_offset: float                 # MJ/m²/day

    # Crop coefficients
    base_crop_coefficient: float            # Base Kc for lettuce
    lai_coefficient_factor: float           # LAI scaling factor

    # Growth stage factors
    vegetative_stage_factor: float          # Kc multiplier for vegetative stage
    head_formation_stage_factor: float      # Kc multiplier for head formation
    mature_stage_factor: float              # Kc multiplier for mature stage

    # Environmental response
    optimal_temperature: float              # °C
    temperature_sensitivity: float          # Temperature response factor
    optimal_vpd_min: float                  # kPa
    optimal_vpd_max: float                  # kPa
    vpd_sensitivity: float                  # VPD response factor

    # Metabolic water demand
    metabolic_water_per_biomass: float      # L per g biomass
    metabolic_water_per_lai: float          # L per LAI unit

    # Hydraulic parameters
    base_root_conductance: float            # L/day/MPa/m²
    root_conductance_scaling_factor: float  # Scaling factor
    base_xylem_conductance: float           # L/day/MPa
    xylem_conductance_scaling_factor: float # Scaling factor

    # Water potential parameters
    base_leaf_potential: float              # MPa
    transpiration_potential_factor: float   # MPa per mm/day
    solution_potential_factor: float        # MPa per dS/m
    cavitation_threshold: float             # MPa

    # Stress parameters
    max_osmotic_adjustment: float           # MPa
    salt_stress_osmotic_factor: float       # Dimensionless

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'WaterUptakeParameters':
        """Create parameters from configuration dictionary."""

        # Extract parameters from different config sections
        water_params = config.get('water_parameters', {})
        stress_params = config.get('stress_parameters', {})
        root_params = config.get('root_system_parameters', {})

        return cls(
            # Penman-Monteith parameters
            psychrometric_constant=water_params['psychrometric_constant'],
            wind_speed=water_params['wind_speed'],
            net_radiation_factor=water_params['net_radiation_factor'],
            radiation_offset=water_params['radiation_offset'],

            # Crop coefficients
            base_crop_coefficient=water_params['base_crop_coefficient'],
            lai_coefficient_factor=water_params['lai_coefficient_factor'],

            # Growth stage factors
            vegetative_stage_factor=water_params['vegetative_stage_factor'],
            head_formation_stage_factor=water_params['head_formation_stage_factor'],
            mature_stage_factor=water_params['mature_stage_factor'],

            # Environmental response
            optimal_temperature=water_params['optimal_temperature'],
            temperature_sensitivity=water_params['temperature_sensitivity'],
            optimal_vpd_min=water_params['optimal_vpd_min'],
            optimal_vpd_max=water_params['optimal_vpd_max'],
            vpd_sensitivity=water_params['vpd_sensitivity'],

            # Metabolic water demand
            metabolic_water_per_biomass=water_params['metabolic_water_per_biomass'],
            metabolic_water_per_lai=water_params['metabolic_water_per_lai'],

            # Hydraulic parameters
            base_root_conductance=root_params['base_root_conductance'],
            root_conductance_scaling_factor=root_params['root_conductance_scaling_factor'],
            base_xylem_conductance=root_params['base_xylem_conductance'],
            xylem_conductance_scaling_factor=root_params['xylem_conductance_scaling_factor'],

            # Water potential parameters
            base_leaf_potential=root_params['base_leaf_potential'],
            transpiration_potential_factor=root_params['transpiration_potential_factor'],
            solution_potential_factor=root_params['solution_potential_factor'],
            cavitation_threshold=root_params['cavitation_threshold'],

            # Stress parameters
            max_osmotic_adjustment=stress_params['max_osmotic_adjustment'],
            salt_stress_osmotic_factor=stress_params['salt_stress_osmotic_factor']
        )


class WaterUptakeModel:
    """
    Water uptake model implementing SPAC-based transpiration and hydraulic flow.

    This model combines:
    1. Penman-Monteith evapotranspiration for atmospheric demand
    2. Plant hydraulic conductance for water transport capacity
    3. Osmotic adjustment under stress conditions
    """

    def __init__(self, parameters: WaterUptakeParameters):
        """Initialize water uptake model with parameters."""
        self.params = parameters

    def calculate_realistic_water_uptake(self,
                                       temperature: float,
                                       humidity: float,
                                       solar_radiation: float,
                                       lai: float,
                                       total_biomass: float,
                                       growth_stage: str = "vegetative") -> Dict[str, float]:
        """
        Calculate realistic water uptake using Penman-Monteith evapotranspiration.

        Args:
            temperature: Air temperature (°C)
            humidity: Relative humidity (%)
            solar_radiation: Solar radiation (MJ/m²/day)
            lai: Leaf Area Index
            total_biomass: Plant biomass (g)
            growth_stage: Growth stage string

        Returns:
            Dictionary with water uptake components
        """

        # 1. Calculate VPD from temperature and humidity
        es = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
        ea = es * (humidity / 100.0)
        vpd = max(0.1, es - ea)

        # 2. Reference evapotranspiration (Penman-Monteith simplified)
        delta = 4098 * es / ((temperature + 237.3) ** 2)
        net_radiation = solar_radiation * self.params.net_radiation_factor - self.params.radiation_offset

        numerator = (0.408 * delta * net_radiation +
                    self.params.psychrometric_constant * 900 / (temperature + 273) *
                    self.params.wind_speed * vpd)
        denominator = (delta + self.params.psychrometric_constant *
                      (1 + 0.34 * self.params.wind_speed))

        et0_mm = max(0.1, numerator / denominator)

        # 3. Crop coefficient based on LAI and growth stage
        lai_factor = min(1.0, lai / self.params.lai_coefficient_factor) if lai > 0.1 else 0.1

        stage_factors = {
            "vegetative": self.params.vegetative_stage_factor,
            "head_formation": self.params.head_formation_stage_factor,
            "mature": self.params.mature_stage_factor
        }
        stage_factor = stage_factors.get(growth_stage, 1.0)

        kc = self.params.base_crop_coefficient * lai_factor * stage_factor

        # 4. Environmental factors
        temp_factor = self._calculate_temperature_factor(temperature)
        vpd_factor = self._calculate_vpd_factor(vpd)
        environmental_factor = temp_factor * vpd_factor

        # 5. Crop evapotranspiration
        etc_mm = et0_mm * kc * environmental_factor

        # 6. Scale by actual canopy coverage
        coverage_factor = min(1.0, lai / 2.0) if lai > 0 else 0.01
        transpiration_mm = etc_mm * coverage_factor

        # 7. Convert to L/day
        transpiration_L = transpiration_mm / 1000.0

        # 8. Add metabolic water demand
        metabolic_water_L = total_biomass * self.params.metabolic_water_per_biomass

        # 9. Total water uptake
        total_water_uptake_L = transpiration_L + metabolic_water_L

        # 10. Water use efficiency
        wue_L_per_kg = (total_water_uptake_L / (total_biomass / 1000.0)) if total_biomass > 0 else 0.0

        return {
            'et0_mm': et0_mm,
            'kc': kc,
            'etc_mm': etc_mm,
            'transpiration_mm': transpiration_mm,
            'transpiration_L': transpiration_L,
            'metabolic_water_L': metabolic_water_L,
            'total_water_uptake_L': total_water_uptake_L,
            'water_use_efficiency_L_kg': wue_L_per_kg,
            'vpd_kpa': vpd,
            'environmental_factor': environmental_factor,
            'temperature_factor': temp_factor,
            'vpd_factor': vpd_factor
        }

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
        Calculate water uptake using plant hydraulic model.

        Water transport follows SPAC: Flow = (ΨSolution - ΨLeaf) / Resistance

        Args:
            light_interception: Light interception fraction
            temperature: Air temperature (°C)
            humidity: Relative humidity (%)
            solar_radiation: Solar radiation (MJ/m²/day)
            vpd: Vapor pressure deficit (kPa)
            lai: Leaf Area Index
            stem_biomass: Stem biomass (g)
            solution_ec: Solution electrical conductivity (dS/m)
            stress_factors: Current stress factors

        Returns:
            Water uptake rate (L/m²/day)
        """
        if stress_factors is None:
            stress_factors = {}

        # 1. Calculate leaf water potential
        transpiration_demand = self._calculate_transpiration(
            light_interception, temperature, vpd, humidity, solar_radiation)

        base_leaf_potential = self.params.base_leaf_potential
        transpiration_effect = self.params.transpiration_potential_factor * transpiration_demand
        leaf_water_potential = base_leaf_potential + transpiration_effect

        # Osmotic adjustment under stress
        osmotic_adjustment = self._calculate_osmotic_adjustment(stress_factors)
        adjusted_leaf_potential = leaf_water_potential + osmotic_adjustment

        # 2. Solution water potential
        solution_water_potential = self.params.solution_potential_factor * solution_ec

        # 3. Hydraulic conductances
        root_surface_area_factor = min(2.0, lai / 2.0)
        root_conductance = self.params.base_root_conductance * root_surface_area_factor

        xylem_conductance = (self.params.base_xylem_conductance *
                           math.sqrt(stem_biomass / self.params.xylem_conductance_scaling_factor))

        # Series resistances
        total_conductance = 1.0 / (1.0/root_conductance + 1.0/xylem_conductance)

        # 4. Water flow calculation
        water_potential_gradient = solution_water_potential - adjusted_leaf_potential
        hydraulic_water_uptake = total_conductance * water_potential_gradient

        # 5. Metabolic water demand
        metabolic_water = lai * self.params.metabolic_water_per_lai

        # 6. Cavitation check
        if adjusted_leaf_potential < self.params.cavitation_threshold:
            cavitation_factor = max(0.1, 1.0 + (adjusted_leaf_potential - self.params.cavitation_threshold) / 1.0)
            hydraulic_water_uptake *= cavitation_factor

        total_uptake = max(0.1, hydraulic_water_uptake + metabolic_water)

        return total_uptake

    def _calculate_temperature_factor(self, temperature: float) -> float:
        """Calculate temperature response factor."""
        if 15 <= temperature <= 30:
            return 1.0
        else:
            return max(0.3, 1.0 - abs(temperature - self.params.optimal_temperature) * self.params.temperature_sensitivity)

    def _calculate_vpd_factor(self, vpd: float) -> float:
        """Calculate VPD response factor."""
        if self.params.optimal_vpd_min <= vpd <= self.params.optimal_vpd_max:
            return 1.0
        else:
            optimal_mid = (self.params.optimal_vpd_min + self.params.optimal_vpd_max) / 2
            return max(0.5, 1.0 - abs(vpd - optimal_mid) * self.params.vpd_sensitivity)

    def _calculate_transpiration(self,
                               light_interception: float,
                               temperature: float,
                               vpd: float,
                               humidity: float,
                               solar_radiation: float) -> float:
        """Calculate transpiration demand (mm/day)."""

        # Simplified transpiration based on energy balance
        energy_available = solar_radiation * light_interception

        # Temperature and VPD effects
        temp_effect = max(0.1, math.exp(-(temperature - 25)**2 / 200))
        vpd_effect = min(2.0, vpd / 1.0) if vpd > 0 else 0.1

        # Base transpiration rate
        base_rate = 2.0  # mm/day at optimal conditions
        transpiration = base_rate * energy_available * temp_effect * vpd_effect * 0.1

        return max(0.1, transpiration)

    def _calculate_osmotic_adjustment(self, stress_factors: Dict[str, Any]) -> float:
        """Calculate osmotic adjustment under stress conditions."""
        water_stress = stress_factors.get('water_stress_level', 0.0)
        salt_stress = stress_factors.get('salinity_stress', 0.0)

        adjustment = (self.params.max_osmotic_adjustment *
                     (water_stress + salt_stress * self.params.salt_stress_osmotic_factor))

        return min(self.params.max_osmotic_adjustment, adjustment)


def create_lettuce_water_uptake_model(system_config: Any) -> WaterUptakeModel:
    """
    Create water uptake model for lettuce using system configuration.

    Args:
        system_config: System configuration containing parameters

    Returns:
        Configured WaterUptakeModel instance
    """

    # Extract configuration sections
    config = {
        'water_parameters': getattr(system_config, 'water_parameters', {}),
        'stress_parameters': getattr(system_config, 'stress_parameters', {}),
        'root_system_parameters': getattr(system_config, 'root_system_parameters', {})
    }

    # Validate required parameters exist
    required_sections = ['water_parameters', 'stress_parameters', 'root_system_parameters']
    for section in required_sections:
        if not config[section]:
            raise ValueError(f"❌ {section} section must be provided in CSV configuration")

    parameters = WaterUptakeParameters.from_config(config)

    return WaterUptakeModel(parameters)