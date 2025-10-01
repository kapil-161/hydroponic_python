from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import math
import random

class RootType(Enum):
    FINE = "fine"
    MEDIUM = "medium"
    COARSE = "coarse"

class HydroponicSystemType(Enum):
    NFT = "nutrient_film_technique"
    DWC = "deep_water_culture"
    AEROPONICS = "aeroponics"
    DRIP = "drip"
    WICK = "wick_system"
    EBB_FLOW = "ebb_flow"

@dataclass
class RootCohort:
    age_days: float
    length: float
    diameter: float
    root_type: RootType
    zone_depth: float
    biomass: float
    fine_min_activity: float
    medium_min_activity: float
    coarse_min_activity: float
    establishment_plateau_days: float
    initial_activity: float

    def __post_init__(self):
        if any(x is None for x in [self.age_days, self.length, self.diameter, self.root_type, 
                                   self.zone_depth, self.biomass, self.fine_min_activity, 
                                   self.medium_min_activity, self.coarse_min_activity, 
                                   self.establishment_plateau_days, self.initial_activity]):
            raise ValueError("All RootCohort fields must be provided")
        if self.age_days < 0 or self.length <= 0 or self.diameter <= 0 or self.biomass <= 0:
            raise ValueError("RootCohort fields must be non-negative (except age_days) and positive for length, diameter, biomass")
        self.surface_area = self.calculate_surface_area()
        self.activity_factor = self.initial_activity
        self.specific_length = self.length / max(0.001, self.biomass)

    def calculate_surface_area(self) -> float:
        diameter_cm = self.diameter / 10.0
        return math.pi * diameter_cm * self.length

    def calculate_activity_factor(self, fine_half_life: float, medium_half_life: float, coarse_half_life: float) -> float:
        if any(x is None or x <= 0 for x in [fine_half_life, medium_half_life, coarse_half_life]):
            raise ValueError("Half-life parameters must be positive")
        half_life_days = {
            RootType.FINE: fine_half_life,
            RootType.MEDIUM: medium_half_life,
            RootType.COARSE: coarse_half_life
        }[self.root_type]
        min_activity = {
            RootType.FINE: self.fine_min_activity,
            RootType.MEDIUM: self.medium_min_activity,
            RootType.COARSE: self.coarse_min_activity
        }[self.root_type]
        if self.age_days <= self.establishment_plateau_days:
            base_activity = 1.0
        else:
            base_activity = 0.5 ** (self.age_days / half_life_days)
        return max(min_activity, base_activity)

    def calculate_uptake_capacity(self, base_uptake_rate: float) -> float:
        if base_uptake_rate is None or base_uptake_rate < 0:
            raise ValueError("base_uptake_rate must be non-negative")
        return self.surface_area * self.activity_factor * base_uptake_rate

@dataclass
class RootZoneLayer:
    depth_range: Tuple[float, float]
    volume: float
    temperature: float
    flow_rate: float
    oxygen_level: float
    ph: float
    nutrient_concentrations: Dict[str, float]
    temperature_q10: float
    root_base_temperature: float
    temperature_range: float
    min_temperature_factor: float
    max_temperature_factor: float
    min_flow_rate: float
    max_flow_rate: float
    low_flow_factor: float
    high_flow_factor: float
    optimal_flow_rate: float
    optimal_oxygen_level: float
    ph_min: float
    ph_max: float
    min_ph_factor: float
    ph_penalty_factor: float
    root_cohorts: List[RootCohort] = field(default_factory=list)

    def __post_init__(self):
        if any(x is None for x in [self.depth_range, self.volume, self.temperature, self.flow_rate, 
                                   self.oxygen_level, self.ph, self.nutrient_concentrations, 
                                   self.temperature_q10, self.root_base_temperature, self.temperature_range, 
                                   self.min_temperature_factor, self.max_temperature_factor, 
                                   self.min_flow_rate, self.max_flow_rate, self.low_flow_factor, 
                                   self.high_flow_factor, self.optimal_flow_rate, self.optimal_oxygen_level, 
                                   self.ph_min, self.ph_max, self.min_ph_factor, self.ph_penalty_factor]):
            raise ValueError("All RootZoneLayer fields must be provided")
        if self.volume <= 0 or self.depth_range[0] < 0 or self.depth_range[1] <= self.depth_range[0]:
            raise ValueError("volume must be positive, depth_range must be valid")
        if self.temperature_q10 <= 1 or self.temperature_range <= 0 or self.min_flow_rate < 0 or self.max_flow_rate <= self.min_flow_rate or self.ph_min >= self.ph_max:
            raise ValueError("Invalid parameter ranges: q10 > 1, temperature_range > 0, min_flow_rate < max_flow_rate, ph_min < ph_max")

    def calculate_root_length_density(self) -> float:
        total_length = sum(cohort.length for cohort in self.root_cohorts)
        return total_length / max(1.0, self.volume)

    def calculate_root_surface_area_density(self) -> float:
        total_area = sum(cohort.surface_area for cohort in self.root_cohorts)
        return total_area / max(1.0, self.volume)

    def calculate_total_uptake_capacity(self, nutrient: str, base_rate: float) -> float:
        if nutrient is None or base_rate is None or base_rate < 0:
            raise ValueError("nutrient and base_rate must be provided and non-negative")
        total_capacity = 0.0
        adjusted_rate = self.adjust_uptake_rate(base_rate)
        for cohort in self.root_cohorts:
            total_capacity += cohort.calculate_uptake_capacity(adjusted_rate)
        return total_capacity

    def adjust_uptake_rate(self, base_rate: float) -> float:
        if base_rate < 0:
            raise ValueError("base_rate must be non-negative")
        temp_factor = self.temperature_q10 ** ((self.temperature - self.root_base_temperature) / self.temperature_range)
        temp_factor = max(self.min_temperature_factor, min(self.max_temperature_factor, temp_factor))
        if self.flow_rate < self.min_flow_rate:
            flow_factor = self.low_flow_factor
        elif self.flow_rate > self.max_flow_rate:
            flow_factor = self.high_flow_factor
        else:
            flow_factor = min(1.0, self.flow_rate / self.optimal_flow_rate)
        oxygen_factor = min(1.0, self.oxygen_level / self.optimal_oxygen_level)
        if self.ph_min <= self.ph <= self.ph_max:
            ph_factor = 1.0
        else:
            ph_deviation = min(abs(self.ph - self.ph_min), abs(self.ph - self.ph_max))
            ph_factor = max(self.min_ph_factor, 1.0 - ph_deviation * self.ph_penalty_factor)
        return base_rate * temp_factor * flow_factor * oxygen_factor * ph_factor

@dataclass
class RootSystemParameters:
    container_volume: float
    channel_length: float
    system_type: HydroponicSystemType
    channel_width: float
    channel_depth: float
    n_channels: int
    root_zone_independent: bool
    primary_root_growth_rate: float
    lateral_root_density: float
    branching_angle_mean: float
    branching_angle_std: float
    fine_root_fraction: float
    medium_root_fraction: float
    coarse_root_fraction: float
    fine_diameter_mean: float
    fine_diameter_std: float
    medium_diameter_mean: float
    medium_diameter_std: float
    coarse_diameter_mean: float
    coarse_diameter_std: float
    fine_turnover_rate: float
    medium_turnover_rate: float
    coarse_turnover_rate: float
    fine_root_half_life_days: float
    medium_root_half_life_days: float
    coarse_root_half_life_days: float
    root_zone_efficiency_factor: float
    fine_min_activity: float
    medium_min_activity: float
    coarse_min_activity: float
    establishment_plateau_days: float
    initial_root_activity: float
    system_multipliers: Dict[HydroponicSystemType, Dict[str, float]]
    base_uptake_rates: Dict[str, float]
    michaelis_constants: Dict[str, float]
    fine_root_effectiveness: float
    medium_root_effectiveness: float
    coarse_root_effectiveness: float
    # optimal_temperature: float  # Consolidated to phenology_parameters
    phenology_optimal_temperature_min: float  # Minimum optimal temperature from phenology
    phenology_optimal_temperature_max: float  # Maximum optimal temperature from phenology
    q10_factor: float
    optimal_flow_rate: float
    flow_stress_threshold: float
    root_growth_auxin_decay_rate: float
    root_optimal_density: float
    root_density_stress_factor: float
    root_temp_optimum: float
    root_temp_max: float
    root_temp_min_factor: float
    root_oxygen_optimum: float
    root_oxygen_min_factor: float
    nutrient_demand_weights: Dict[str, float]
    nutrient_reference_concentrations: Dict[str, float]
    nutrient_competition_groups: Dict[str, List[str]]
    nutrient_ph_optima: Dict[str, Tuple[float, float]]
    ph_stress_range_acidic: float
    ph_stress_range_basic: float
    ph_stress_factor: float
    young_root_activity: float
    old_root_activity: float
    # Additional hardcoded parameters extracted from code
    temperature_range_factor: float
    min_temperature_factor: float
    max_temperature_factor: float
    low_flow_factor: float
    high_flow_factor: float
    ph_zone_min: float
    ph_zone_max: float
    min_ph_factor: float
    ph_penalty_factor: float
    nft_zone_1_fraction: float
    nft_zone_2_fraction: float
    nft_zone_3_fraction: float
    dwc_zone_1_fraction: float
    dwc_zone_2_fraction: float
    dwc_zone_3_fraction: float
    general_zone_1_fraction: float
    general_zone_2_fraction: float
    general_zone_3_fraction: float
    general_zone_4_fraction: float
    root_biomass_density: float
    coarse_root_min_threshold: float
    fine_root_min_threshold: float
    diameter_minimum_limit: float
    auxin_gradient_weight: float
    nutrient_signal_weight: float
    oxygen_effect_weight: float
    competition_effect_weight: float
    temperature_effect_weight: float
    min_growth_potential: float
    max_growth_potential: float
    max_temp_threshold: float
    temp_decay_factor: float
    flow_rate_offset: float
    flow_rate_multiplier: float
    transport_temp_exponent: float
    minimum_surface_area: float
    minimum_biomass: float
    minimum_volume: float
    effective_area_minimum: float
    cache_timeout: float

    # Hardcoded value replacements (from CSV)
    min_flow_rate_multiplier: float
    default_michaelis_constant: float
    default_reference_nutrient_concentration: float
    nutrient_inhibition_minimum_factor: float
    competition_effect_minimum_factor: float
    heat_stress_minimum_factor: float
    optimization_temp_min: int
    optimization_temp_max: int
    optimization_temp_step: int
    optimization_flow_min: float
    optimization_flow_max: float
    optimization_flow_step: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'RootSystemParameters':
        # Load phenology parameters for temperature consolidation
        phenology_params = config.get('phenology_parameters')
        if not phenology_params:
            raise KeyError("Missing required parameter section: phenology_parameters")
        required_params = [
            'container_volume', 'channel_length', 'system_type', 'channel_width', 'channel_depth',
            'n_channels', 'root_zone_independent', 'primary_root_growth_rate', 'lateral_root_density',
            'branching_angle_mean', 'branching_angle_std', 'fine_root_fraction', 'medium_root_fraction',
            'coarse_root_fraction', 'fine_diameter_mean', 'fine_diameter_std', 'medium_diameter_mean',
            'medium_diameter_std', 'coarse_diameter_mean', 'coarse_diameter_std', 'fine_turnover_rate',
            'medium_turnover_rate', 'coarse_turnover_rate', 'fine_root_half_life_days',
            'medium_root_half_life_days', 'coarse_root_half_life_days', 'root_zone_efficiency_factor',
            'fine_min_activity', 'medium_min_activity', 'coarse_min_activity', 'establishment_plateau_days',
            'initial_root_activity', 'fine_root_effectiveness', 'medium_root_effectiveness',
            'coarse_root_effectiveness', 'q10_factor', 'optimal_flow_rate',
            'flow_stress_threshold', 'root_growth_auxin_decay_rate', 'root_optimal_density',
            'root_density_stress_factor', 'root_temp_optimum', 'root_temp_max', 'root_temp_min_factor',
            'root_oxygen_optimum', 'root_oxygen_min_factor', 'ph_stress_range_acidic', 'ph_stress_range_basic',
            'ph_stress_factor', 'young_root_activity', 'old_root_activity',
            'temperature_range_factor', 'min_temperature_factor', 'max_temperature_factor',
            'low_flow_factor', 'high_flow_factor', 'ph_zone_min', 'ph_zone_max',
            'min_ph_factor', 'ph_penalty_factor', 'nft_zone_1_fraction', 'nft_zone_2_fraction',
            'nft_zone_3_fraction', 'dwc_zone_1_fraction', 'dwc_zone_2_fraction', 'dwc_zone_3_fraction',
            'general_zone_1_fraction', 'general_zone_2_fraction', 'general_zone_3_fraction', 'general_zone_4_fraction',
            'root_biomass_density', 'coarse_root_min_threshold', 'fine_root_min_threshold', 'diameter_minimum_limit',
            'auxin_gradient_weight', 'nutrient_signal_weight', 'oxygen_effect_weight', 'competition_effect_weight',
            'temperature_effect_weight', 'min_growth_potential', 'max_growth_potential', 'max_temp_threshold',
            'temp_decay_factor', 'flow_rate_offset', 'flow_rate_multiplier', 'transport_temp_exponent',
            'minimum_surface_area', 'minimum_biomass', 'minimum_volume', 'effective_area_minimum',
            'optimal_temperature_min', 'optimal_temperature_max', 'cache_timeout',
            # Hardcoded value replacements
            'min_flow_rate_multiplier', 'default_michaelis_constant', 'default_reference_nutrient_concentration',
            'nutrient_inhibition_minimum_factor', 'competition_effect_minimum_factor', 'heat_stress_minimum_factor',
            'optimization_temp_min', 'optimization_temp_max', 'optimization_temp_step',
            'optimization_flow_min', 'optimization_flow_max', 'optimization_flow_step'
        ]
        required_nutrients = ['NO3', 'NH4', 'PO4', 'K', 'Ca', 'Mg', 'SO4']
        for param in required_params:
            if param not in config and param not in phenology_params:
                raise KeyError(f"Missing required parameter: {param}")
        base_uptake_rates = {}
        michaelis_constants = {}
        for nutrient in required_nutrients:
            vmax_key = f'{nutrient.lower()}_uptake_vmax'
            km_key = f'{nutrient.lower()}_uptake_km'
            if vmax_key not in config or km_key not in config:
                raise KeyError(f"Missing required nutrient parameter: {vmax_key} or {km_key}")
            base_uptake_rates[nutrient] = float(config[vmax_key])
            michaelis_constants[nutrient] = float(config[km_key])
        system_multipliers = {}
        for sys_type in HydroponicSystemType:
            prefix = f'system_multipliers_{sys_type.value}'
            if f'{prefix}_root_length_multiplier' in config:
                system_multipliers[sys_type] = {
                    'root_length_multiplier': float(config[f'{prefix}_root_length_multiplier']),
                    'surface_area_multiplier': float(config[f'{prefix}_surface_area_multiplier']),
                    'branching_multiplier': float(config[f'{prefix}_branching_multiplier'])
                }
        nutrient_demand_weights = {
            'N-NO3': float(config['nutrient_demand_weight_no3']),
            'P-PO4': float(config['nutrient_demand_weight_po4']),
            'K': float(config['nutrient_demand_weight_k']),
            'Ca': float(config['nutrient_demand_weight_ca']),
            'Mg': float(config['nutrient_demand_weight_mg'])
        }
        nutrient_reference_concentrations = {
            'N-NO3': float(config['nutrient_ref_concentration_no3']),
            'P-PO4': float(config['nutrient_ref_concentration_po4']),
            'K': float(config['nutrient_ref_concentration_k']),
            'Ca': float(config['nutrient_ref_concentration_ca']),
            'Mg': float(config['nutrient_ref_concentration_mg'])
        }
        nutrient_competition_groups = {
            'N-NO3': config['nutrient_competition_no3'].split(','),
            'N-NH4': config['nutrient_competition_nh4'].split(','),
            'P-PO4': config['nutrient_competition_po4'].split(','),
            'K': config['nutrient_competition_k'].split(','),
            'Ca': config['nutrient_competition_ca'].split(','),
            'Mg': config['nutrient_competition_mg'].split(',')
        }
        nutrient_ph_optima = {
            'N-NO3': (float(config['ph_optimum_no3_min']), float(config['ph_optimum_no3_max'])),
            'N-NH4': (float(config['ph_optimum_nh4_min']), float(config['ph_optimum_nh4_max'])),
            'P-PO4': (float(config['ph_optimum_po4_min']), float(config['ph_optimum_po4_max'])),
            'K': (float(config['ph_optimum_k_min']), float(config['ph_optimum_k_max'])),
            'Ca': (float(config['ph_optimum_ca_min']), float(config['ph_optimum_ca_max'])),
            'Mg': (float(config['ph_optimum_mg_min']), float(config['ph_optimum_mg_max']))
        }
        if not (0 < config['fine_root_fraction'] + config['medium_root_fraction'] + config['coarse_root_fraction'] <= 1.0):
            raise ValueError("Root fractions must sum to (0, 1]")
        if config['q10_factor'] <= 1:
            raise ValueError("q10_factor must be greater than 1")
        if config['optimal_flow_rate'] <= 0 or config['flow_stress_threshold'] <= config['optimal_flow_rate']:
            raise ValueError("optimal_flow_rate must be positive, flow_stress_threshold must be greater")
        if config['root_temp_optimum'] >= config['root_temp_max']:
            raise ValueError("root_temp_optimum must be less than root_temp_max")
        return cls(
            container_volume=float(config['container_volume']),
            channel_length=float(config['channel_length']),
            system_type=HydroponicSystemType(config['system_type']),
            channel_width=float(config['channel_width']),
            channel_depth=float(config['channel_depth']),
            n_channels=int(config['n_channels']),
            root_zone_independent=config['root_zone_independent'],
            primary_root_growth_rate=float(config['primary_root_growth_rate']),
            lateral_root_density=float(config['lateral_root_density']),
            branching_angle_mean=float(config['branching_angle_mean']),
            branching_angle_std=float(config['branching_angle_std']),
            fine_root_fraction=float(config['fine_root_fraction']),
            medium_root_fraction=float(config['medium_root_fraction']),
            coarse_root_fraction=float(config['coarse_root_fraction']),
            fine_diameter_mean=float(config['fine_diameter_mean']),
            fine_diameter_std=float(config['fine_diameter_std']),
            medium_diameter_mean=float(config['medium_diameter_mean']),
            medium_diameter_std=float(config['medium_diameter_std']),
            coarse_diameter_mean=float(config['coarse_diameter_mean']),
            coarse_diameter_std=float(config['coarse_diameter_std']),
            fine_turnover_rate=float(config['fine_turnover_rate']),
            medium_turnover_rate=float(config['medium_turnover_rate']),
            coarse_turnover_rate=float(config['coarse_turnover_rate']),
            fine_root_half_life_days=float(config['fine_root_half_life_days']),
            medium_root_half_life_days=float(config['medium_root_half_life_days']),
            coarse_root_half_life_days=float(config['coarse_root_half_life_days']),
            root_zone_efficiency_factor=float(config['root_zone_efficiency_factor']),
            fine_min_activity=float(config['fine_min_activity']),
            medium_min_activity=float(config['medium_min_activity']),
            coarse_min_activity=float(config['coarse_min_activity']),
            establishment_plateau_days=float(config['establishment_plateau_days']),
            initial_root_activity=float(config['initial_root_activity']),
            system_multipliers=system_multipliers,
            base_uptake_rates=base_uptake_rates,
            michaelis_constants=michaelis_constants,
            fine_root_effectiveness=float(config['fine_root_effectiveness']),
            medium_root_effectiveness=float(config['medium_root_effectiveness']),
            coarse_root_effectiveness=float(config['coarse_root_effectiveness']),
            phenology_optimal_temperature_min=float(phenology_params['optimal_temperature_min']),
            phenology_optimal_temperature_max=float(phenology_params['optimal_temperature_max']),
            q10_factor=float(config['q10_factor']),
            optimal_flow_rate=float(config['optimal_flow_rate']),
            flow_stress_threshold=float(config['flow_stress_threshold']),
            root_growth_auxin_decay_rate=float(config['root_growth_auxin_decay_rate']),
            root_optimal_density=float(config['root_optimal_density']),
            root_density_stress_factor=float(config['root_density_stress_factor']),
            root_temp_optimum=float(config['root_temp_optimum']),
            root_temp_max=float(config['root_temp_max']),
            root_temp_min_factor=float(config['root_temp_min_factor']),
            root_oxygen_optimum=float(config['root_oxygen_optimum']),
            root_oxygen_min_factor=float(config['root_oxygen_min_factor']),
            nutrient_demand_weights=nutrient_demand_weights,
            nutrient_reference_concentrations=nutrient_reference_concentrations,
            nutrient_competition_groups=nutrient_competition_groups,
            nutrient_ph_optima=nutrient_ph_optima,
            ph_stress_range_acidic=float(config['ph_stress_range_acidic']),
            ph_stress_range_basic=float(config['ph_stress_range_basic']),
            ph_stress_factor=float(config['ph_stress_factor']),
            young_root_activity=float(config['young_root_activity']),
            old_root_activity=float(config['old_root_activity']),
            # Additional hardcoded parameters
            temperature_range_factor=float(config['temperature_range_factor']),
            min_temperature_factor=float(config['min_temperature_factor']),
            max_temperature_factor=float(config['max_temperature_factor']),
            low_flow_factor=float(config['low_flow_factor']),
            high_flow_factor=float(config['high_flow_factor']),
            ph_zone_min=float(config['ph_zone_min']),
            ph_zone_max=float(config['ph_zone_max']),
            min_ph_factor=float(config['min_ph_factor']),
            ph_penalty_factor=float(config['ph_penalty_factor']),
            nft_zone_1_fraction=float(config['nft_zone_1_fraction']),
            nft_zone_2_fraction=float(config['nft_zone_2_fraction']),
            nft_zone_3_fraction=float(config['nft_zone_3_fraction']),
            dwc_zone_1_fraction=float(config['dwc_zone_1_fraction']),
            dwc_zone_2_fraction=float(config['dwc_zone_2_fraction']),
            dwc_zone_3_fraction=float(config['dwc_zone_3_fraction']),
            general_zone_1_fraction=float(config['general_zone_1_fraction']),
            general_zone_2_fraction=float(config['general_zone_2_fraction']),
            general_zone_3_fraction=float(config['general_zone_3_fraction']),
            general_zone_4_fraction=float(config['general_zone_4_fraction']),
            root_biomass_density=float(config['root_biomass_density']),
            coarse_root_min_threshold=float(config['coarse_root_min_threshold']),
            fine_root_min_threshold=float(config['fine_root_min_threshold']),
            diameter_minimum_limit=float(config['diameter_minimum_limit']),
            auxin_gradient_weight=float(config['auxin_gradient_weight']),
            nutrient_signal_weight=float(config['nutrient_signal_weight']),
            oxygen_effect_weight=float(config['oxygen_effect_weight']),
            competition_effect_weight=float(config['competition_effect_weight']),
            temperature_effect_weight=float(config['temperature_effect_weight']),
            min_growth_potential=float(config['min_growth_potential']),
            max_growth_potential=float(config['max_growth_potential']),
            max_temp_threshold=float(config['max_temp_threshold']),
            temp_decay_factor=float(config['temp_decay_factor']),
            flow_rate_offset=float(config['flow_rate_offset']),
            flow_rate_multiplier=float(config['flow_rate_multiplier']),
            transport_temp_exponent=float(config['transport_temp_exponent']),
            minimum_surface_area=float(config['minimum_surface_area']),
            minimum_biomass=float(config['minimum_biomass']),
            minimum_volume=float(config['minimum_volume']),
            effective_area_minimum=float(config['effective_area_minimum']),
            cache_timeout=float(config['cache_timeout']),
            # Hardcoded value replacements
            min_flow_rate_multiplier=float(config['min_flow_rate_multiplier']),
            default_michaelis_constant=float(config['default_michaelis_constant']),
            default_reference_nutrient_concentration=float(config['default_reference_nutrient_concentration']),
            nutrient_inhibition_minimum_factor=float(config['nutrient_inhibition_minimum_factor']),
            competition_effect_minimum_factor=float(config['competition_effect_minimum_factor']),
            heat_stress_minimum_factor=float(config['heat_stress_minimum_factor']),
            optimization_temp_min=int(config['optimization_temp_min']),
            optimization_temp_max=int(config['optimization_temp_max']),
            optimization_temp_step=int(config['optimization_temp_step']),
            optimization_flow_min=float(config['optimization_flow_min']),
            optimization_flow_max=float(config['optimization_flow_max']),
            optimization_flow_step=float(config['optimization_flow_step'])
        )

@dataclass
class RootSystemMetrics:
    total_root_length: float
    total_root_surface_area: float
    total_root_biomass: float
    total_root_volume: float
    root_length_density: float
    root_surface_area_density: float
    specific_root_length: float
    average_root_activity: float
    fine_root_length: float
    medium_root_length: float
    coarse_root_length: float
    fine_root_fraction: float
    root_age_days: float
    cumulative_growth: float
    total_nutrient_uptake: float
    uptake_per_surface_area: float
    uptake_temperature_factor: float
    uptake_flow_factor: float
    effective_root_surface_area: float
    total_uptake_g_per_day: float
    nitrogen_uptake_g_per_day: float
    nutrient_uptake_rates: Dict[str, float]
    root_distribution: Dict[int, float] = field(default_factory=dict)

class EnhancedRootSystemModel:
    def __init__(self, parameters: RootSystemParameters):
        if not parameters:
            raise ValueError("RootSystemParameters must be provided")
        self.params = parameters
        self.root_zones: List[RootZoneLayer] = []
        self.total_age_days = 0.0
        self.cumulative_root_growth = 0.0
        self.initialize_root_zones()
    
    def initialize(self):
        """Initialize the root system model"""
        pass

    def initialize_root_zones(self):
        effective_volume = self.params.container_volume * self.params.root_zone_efficiency_factor
        if self.params.system_type == HydroponicSystemType.NFT:
            channel_volume = self.params.channel_length * self.params.channel_width * self.params.channel_depth * self.params.n_channels
            effective_volume = channel_volume * self.params.root_zone_efficiency_factor
            self.root_zones = [
                RootZoneLayer(
                    depth_range=(0, 2), volume=effective_volume * self.params.nft_zone_1_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                ),
                RootZoneLayer(
                    depth_range=(2, 4), volume=effective_volume * self.params.nft_zone_2_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                ),
                RootZoneLayer(
                    depth_range=(4, 6), volume=effective_volume * self.params.nft_zone_3_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                )
            ]
        elif self.params.system_type == HydroponicSystemType.DWC:
            self.root_zones = [
                RootZoneLayer(
                    depth_range=(0, 5), volume=effective_volume * self.params.dwc_zone_1_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                ),
                RootZoneLayer(
                    depth_range=(5, 15), volume=effective_volume * self.params.dwc_zone_2_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                ),
                RootZoneLayer(
                    depth_range=(15, 25), volume=effective_volume * self.params.dwc_zone_3_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                )
            ]
        else:  # Aeroponics, Drip, Wick, Ebb-Flow
            self.root_zones = [
                RootZoneLayer(
                    depth_range=(0, 3), volume=effective_volume * self.params.general_zone_1_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                ),
                RootZoneLayer(
                    depth_range=(3, 8), volume=effective_volume * self.params.general_zone_2_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                ),
                RootZoneLayer(
                    depth_range=(8, 15), volume=effective_volume * self.params.general_zone_3_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                ),
                RootZoneLayer(
                    depth_range=(15, 20), volume=effective_volume * self.params.general_zone_4_fraction, temperature=0.0, flow_rate=0.0, 
                    oxygen_level=0.0, ph=0.0, nutrient_concentrations={}, 
                    temperature_q10=self.params.q10_factor, root_base_temperature=(self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0, 
                    temperature_range=self.params.temperature_range_factor, min_temperature_factor=self.params.min_temperature_factor, max_temperature_factor=self.params.max_temperature_factor, 
                    min_flow_rate=self.params.optimal_flow_rate * self.params.min_flow_rate_multiplier, max_flow_rate=self.params.flow_stress_threshold, 
                    low_flow_factor=self.params.low_flow_factor, high_flow_factor=self.params.high_flow_factor, optimal_flow_rate=self.params.optimal_flow_rate, 
                    optimal_oxygen_level=self.params.root_oxygen_optimum, ph_min=self.params.ph_zone_min, ph_max=self.params.ph_zone_max, 
                    min_ph_factor=self.params.min_ph_factor, ph_penalty_factor=self.params.ph_penalty_factor
                )
            ]

    def calculate_architecture_metrics(self) -> Dict[str, float]:
        total_length = 0.0
        total_surface_area = 0.0
        total_biomass = 0.0
        total_volume = 0.0
        fine_length = 0.0
        medium_length = 0.0
        coarse_length = 0.0
        weighted_activity = 0.0
        total_cohorts = 0
        for zone in self.root_zones:
            for cohort in zone.root_cohorts:
                total_length += cohort.length
                total_surface_area += cohort.surface_area
                total_biomass += cohort.biomass
                diameter_cm = cohort.diameter / 10.0
                cohort_volume = math.pi * (diameter_cm/2)**2 * cohort.length
                total_volume += cohort_volume
                if cohort.root_type == RootType.FINE:
                    fine_length += cohort.length
                elif cohort.root_type == RootType.MEDIUM:
                    medium_length += cohort.length
                else:
                    coarse_length += cohort.length
                weighted_activity += cohort.activity_factor
                total_cohorts += 1
        total_zone_volume = sum(zone.volume for zone in self.root_zones)
        root_length_density = total_length / max(self.params.minimum_volume, total_zone_volume)
        root_surface_area_density = total_surface_area / max(self.params.minimum_volume, total_zone_volume)
        avg_activity = weighted_activity / max(1, total_cohorts)
        specific_root_length = total_length / max(self.params.minimum_biomass, total_biomass)
        # Calculate root distribution by zone
        zone_surface_areas = {}
        for i, zone in enumerate(self.root_zones):
            zone_surface_area = sum(cohort.surface_area for cohort in zone.root_cohorts)
            zone_surface_areas[i] = zone_surface_area

        # Calculate distribution fractions
        root_distribution = {}
        if total_surface_area > 0:
            for zone_id, surface_area in zone_surface_areas.items():
                root_distribution[zone_id] = surface_area / total_surface_area

        return {
            'total_root_length': total_length,
            'total_root_surface_area': total_surface_area,
            'total_root_biomass': total_biomass,
            'total_root_volume': total_volume,
            'root_length_density': root_length_density,
            'root_surface_area_density': root_surface_area_density,
            'specific_root_length': specific_root_length,
            'average_root_activity': avg_activity,
            'fine_root_length': fine_length,
            'medium_root_length': medium_length,
            'coarse_root_length': coarse_length,
            'fine_root_fraction': fine_length / max(self.params.minimum_volume, total_length),
            'root_age_days': self.total_age_days,
            'cumulative_growth': self.cumulative_root_growth,
            'root_distribution': root_distribution
        }

    def calculate_effective_surface_area(self, architecture_metrics: Dict[str, float]) -> float:
        fine_length = architecture_metrics['fine_root_length']
        medium_length = architecture_metrics['medium_root_length']
        coarse_length = architecture_metrics['coarse_root_length']
        fine_diameter_cm = self.params.fine_diameter_mean / 10.0
        medium_diameter_cm = self.params.medium_diameter_mean / 10.0
        coarse_diameter_cm = self.params.coarse_diameter_mean / 10.0
        fine_area = fine_length * math.pi * fine_diameter_cm
        medium_area = medium_length * math.pi * medium_diameter_cm
        coarse_area = coarse_length * math.pi * coarse_diameter_cm
        effective_area = (
            fine_area * self.params.fine_root_effectiveness +
            medium_area * self.params.medium_root_effectiveness +
            coarse_area * self.params.coarse_root_effectiveness
        )
        if effective_area < self.params.effective_area_minimum:
            print(f"Warning: Effective surface area {effective_area} is below minimum {self.params.effective_area_minimum}, using minimum")
            effective_area = self.params.effective_area_minimum
        return effective_area

    def calculate_temperature_factor(self, temperature: float) -> float:
        """Use consolidated temperature factor calculation from core_utils."""
        from utils.core_utils import calculate_temperature_factor

        if temperature is None:
            raise ValueError("Temperature must be provided")

        # Create config structure for consolidated function
        # ALL parameters must come from CSV configuration - no hardcoded values
        temp_config = type('Config', (), {
            'temperature_factor': {
                'optimal_temp': (self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0,
                'q10': self.params.q10_factor,
                'min_factor': self.params.min_temperature_factor,
                'max_factor': self.params.max_temperature_factor,
                'max_temp_threshold': self.params.max_temp_threshold,
                'temp_decay_factor': self.params.temp_decay_factor
            }
        })

        return calculate_temperature_factor(temperature, temp_config, method='clamped')

    def calculate_flow_factor(self, flow_rate: float) -> float:
        if flow_rate is None or flow_rate < 0:
            raise ValueError("flow_rate must be non-negative")
        if flow_rate < self.params.optimal_flow_rate * self.params.flow_rate_multiplier:
            return self.params.low_flow_factor
        elif flow_rate > self.params.flow_stress_threshold:
            return self.params.high_flow_factor
        else:
            return min(1.0, self.params.flow_rate_offset + self.params.flow_rate_multiplier * (flow_rate / self.params.optimal_flow_rate))

    def calculate_nutrient_competition(self, target_nutrient: str, concentrations: Dict[str, float]) -> float:
        if target_nutrient not in self.params.nutrient_competition_groups:
            return 1.0
        competitors = self.params.nutrient_competition_groups[target_nutrient]
        total_competitor_conc = 0.0
        for competitor in competitors:
            if competitor != target_nutrient and competitor in concentrations:
                ki = self.params.michaelis_constants.get(competitor, self.params.default_michaelis_constant)
                total_competitor_conc += concentrations[competitor] / ki
        inhibition_factor = 1.0 / (1.0 + total_competitor_conc)
        return max(self.params.nutrient_inhibition_minimum_factor, inhibition_factor)

    def calculate_ph_effect_on_uptake(self, nutrient: str, ph: float) -> float:
        if nutrient not in self.params.nutrient_ph_optima:
            return 1.0
        optimal_min, optimal_max = self.params.nutrient_ph_optima[nutrient]
        if optimal_min <= ph <= optimal_max:
            return 1.0
        elif ph < optimal_min:
            ph_stress = max(0.0, (optimal_min - ph) / self.params.ph_stress_range_acidic)
            return max(0.2, 1.0 - ph_stress * self.params.ph_stress_factor)
        else:
            ph_stress = max(0.0, (ph - optimal_max) / self.params.ph_stress_range_basic)
            return max(0.2, 1.0 - ph_stress * self.params.ph_stress_factor)

    def calculate_root_age_effect(self, architecture_metrics: Dict[str, float]) -> float:
        fine_root_fraction = architecture_metrics.get('fine_root_fraction', 0.0)
        return max(0.1, fine_root_fraction * self.params.young_root_activity + 
                   (1.0 - fine_root_fraction) * self.params.old_root_activity)

    def update_root_aging(self):
        for zone in self.root_zones:
            surviving_cohorts = []
            for cohort in zone.root_cohorts:
                cohort.age_days += 1.0
                cohort.activity_factor = cohort.calculate_activity_factor(
                    self.params.fine_root_half_life_days,
                    self.params.medium_root_half_life_days,
                    self.params.coarse_root_half_life_days
                )
                survival_prob = {
                    RootType.FINE: 1.0 - self.params.fine_turnover_rate,
                    RootType.MEDIUM: 1.0 - self.params.medium_turnover_rate,
                    RootType.COARSE: 1.0 - self.params.coarse_turnover_rate
                }[cohort.root_type]
                if random.random() < survival_prob:
                    surviving_cohorts.append(cohort)
            zone.root_cohorts = surviving_cohorts

    def calculate_zone_growth_potential(self, zone: RootZoneLayer, zone_index: int, 
                                       environmental_conditions: Dict[str, float]) -> float:
        auxin_gradient = math.exp(-self.params.root_growth_auxin_decay_rate * zone_index)
        nutrient_signal = 0.0
        for nutrient, weight in self.params.nutrient_demand_weights.items():
            conc = zone.nutrient_concentrations.get(nutrient, 0.0)
            ref_conc = self.params.nutrient_reference_concentrations.get(nutrient, self.params.default_reference_nutrient_concentration)
            normalized_conc = min(1.0, conc / ref_conc)
            nutrient_signal += weight * normalized_conc
        oxygen_effect = min(1.0, zone.oxygen_level / self.params.root_oxygen_optimum)
        oxygen_effect = max(self.params.root_oxygen_min_factor, oxygen_effect)
        zone_root_density = zone.calculate_root_length_density()
        if zone_root_density <= self.params.root_optimal_density:
            competition_effect = 1.0
        else:
            density_stress = (zone_root_density - self.params.root_optimal_density) / self.params.root_optimal_density
            competition_effect = max(self.params.competition_effect_minimum_factor, 1.0 - self.params.root_density_stress_factor * density_stress)
        if zone.temperature <= self.params.root_temp_optimum:
            temp_effect = max(self.params.root_temp_min_factor, zone.temperature / self.params.root_temp_optimum)
        else:
            heat_stress = (zone.temperature - self.params.root_temp_optimum) / (self.params.root_temp_max - self.params.root_temp_optimum)
            temp_effect = max(self.params.heat_stress_minimum_factor, 1.0 - heat_stress)
        zone_growth_potential = (
            auxin_gradient * self.params.auxin_gradient_weight +
            nutrient_signal * self.params.nutrient_signal_weight +
            oxygen_effect * self.params.oxygen_effect_weight +
            competition_effect * self.params.competition_effect_weight +
            temp_effect * self.params.temperature_effect_weight
        )
        return max(self.params.min_growth_potential, min(self.params.max_growth_potential, zone_growth_potential))

    def generate_new_roots(self, growth_factors: Dict[str, float], environmental_conditions: Dict[str, float]) -> float:
        for factor in ['nitrogen_stress', 'water_stress', 'temperature_stress']:
            if factor not in growth_factors:
                raise KeyError(f"Missing required growth factor: {factor}")
        nitrogen_growth_factor = max(0.1, 1.0 - growth_factors['nitrogen_stress'])
        water_growth_factor = max(0.1, 1.0 - growth_factors['water_stress'])
        temperature_growth_factor = max(0.1, 1.0 - growth_factors['temperature_stress'])
        effective_growth = self.params.primary_root_growth_rate * nitrogen_growth_factor * water_growth_factor * temperature_growth_factor
        multipliers = self.params.system_multipliers.get(self.params.system_type)
        if not multipliers:
            raise KeyError(f"System multipliers for {self.params.system_type} not found")
        length_mult = multipliers['root_length_multiplier']
        branching_mult = multipliers['branching_multiplier']
        total_new_growth = 0.0
        for i, zone in enumerate(self.root_zones):
            zone_growth_fraction = self.calculate_zone_growth_potential(zone, i, environmental_conditions)
            zone_growth = effective_growth * zone_growth_fraction * length_mult
            if zone_growth > 0.01:
                for root_type in RootType:
                    fraction = {
                        RootType.FINE: self.params.fine_root_fraction,
                        RootType.MEDIUM: self.params.medium_root_fraction,
                        RootType.COARSE: self.params.coarse_root_fraction
                    }[root_type]
                    diameter = max(self.params.diameter_minimum_limit, random.gauss(self.params.fine_diameter_mean, self.params.fine_diameter_std) if root_type == RootType.FINE else
                                  random.gauss(self.params.medium_diameter_mean, self.params.medium_diameter_std) if root_type == RootType.MEDIUM else
                                  random.gauss(self.params.coarse_diameter_mean, self.params.coarse_diameter_std))
                    cohort_length = zone_growth * fraction * branching_mult
                    min_threshold = self.params.coarse_root_min_threshold if root_type == RootType.COARSE else self.params.fine_root_min_threshold
                    if cohort_length > min_threshold:
                        diameter_cm = diameter / 10.0
                        volume = math.pi * (diameter_cm/2)**2 * cohort_length
                        biomass = volume * self.params.root_biomass_density
                        new_cohort = RootCohort(
                            age_days=0.0,
                            length=cohort_length,
                            diameter=diameter,
                            root_type=root_type,
                            zone_depth=sum(zone.depth_range) / 2,
                            biomass=biomass,
                            fine_min_activity=self.params.fine_min_activity,
                            medium_min_activity=self.params.medium_min_activity,
                            coarse_min_activity=self.params.coarse_min_activity,
                            establishment_plateau_days=self.params.establishment_plateau_days,
                            initial_activity=self.params.initial_root_activity
                        )
                        zone.root_cohorts.append(new_cohort)
                        total_new_growth += cohort_length
        return total_new_growth

    def update_environmental_conditions(self, environmental_conditions: Dict[str, float]):
        required_conditions = ['temperature', 'flow_rate', 'oxygen_level', 'ph', 'nutrient_concentrations']
        for condition in required_conditions:
            if condition not in environmental_conditions:
                raise KeyError(f"Missing required environmental condition: {condition}")
        for zone in self.root_zones:
            zone.temperature = environmental_conditions['temperature']
            zone.flow_rate = environmental_conditions['flow_rate']
            zone.oxygen_level = environmental_conditions['oxygen_level']
            zone.ph = environmental_conditions['ph']
            zone.nutrient_concentrations = environmental_conditions['nutrient_concentrations']

    def calculate_daily_root_metrics(self, environmental_conditions: Dict[str, float], 
                                    growth_factors: Dict[str, float]) -> RootSystemMetrics:
        self.update_environmental_conditions(environmental_conditions)
        self.total_age_days += 1.0
        self.update_root_aging()
        new_growth = self.generate_new_roots(growth_factors, environmental_conditions)
        self.cumulative_root_growth += new_growth
        architecture_metrics = self.calculate_architecture_metrics()
        uptake_results = self.calculate_nutrient_uptake(architecture_metrics, environmental_conditions)
        return RootSystemMetrics(
            total_root_length=architecture_metrics['total_root_length'],
            total_root_surface_area=architecture_metrics['total_root_surface_area'],
            total_root_biomass=architecture_metrics['total_root_biomass'],
            total_root_volume=architecture_metrics['total_root_volume'],
            root_length_density=architecture_metrics['root_length_density'],
            root_surface_area_density=architecture_metrics['root_surface_area_density'],
            specific_root_length=architecture_metrics['specific_root_length'],
            average_root_activity=architecture_metrics['average_root_activity'],
            fine_root_length=architecture_metrics['fine_root_length'],
            medium_root_length=architecture_metrics['medium_root_length'],
            coarse_root_length=architecture_metrics['coarse_root_length'],
            fine_root_fraction=architecture_metrics['fine_root_fraction'],
            root_age_days=architecture_metrics['root_age_days'],
            cumulative_growth=architecture_metrics['cumulative_growth'],
            total_nutrient_uptake=uptake_results['total_nutrient_uptake'],
            uptake_per_surface_area=uptake_results['uptake_per_surface_area'],
            root_distribution=architecture_metrics['root_distribution'],
            uptake_temperature_factor=uptake_results['uptake_temperature_factor'],
            uptake_flow_factor=uptake_results['uptake_flow_factor'],
            effective_root_surface_area=uptake_results['effective_root_surface_area'],
            total_uptake_g_per_day=uptake_results['total_uptake_g_per_day'],
            nitrogen_uptake_g_per_day=uptake_results['nitrogen_uptake_g_per_day'],
            nutrient_uptake_rates={k: v for k, v in uptake_results.items() if k.endswith('_uptake_rate')}
        )

    def calculate_hourly_root_metrics(self, environmental_conditions: Dict[str, float], 
                                     growth_factors: Dict[str, float], dt_hours: float) -> Dict[str, Any]:
        if dt_hours <= 0:
            raise ValueError("dt_hours must be positive")
        self.update_environmental_conditions(environmental_conditions)
        if not hasattr(self, '_last_daily_update') or dt_hours > 20.0:
            architecture_metrics = self.calculate_architecture_metrics()
            self._last_daily_update = architecture_metrics
        else:
            architecture_metrics = self._last_daily_update
        uptake_results = self.calculate_hourly_nutrient_uptake(architecture_metrics, environmental_conditions, dt_hours)
        return {
            **architecture_metrics,
            **uptake_results,
            'system_type': self.params.system_type.value
        }

    def calculate_nutrient_uptake(self, architecture_metrics: Dict[str, float], 
                                 environmental_conditions: Dict[str, float]) -> Dict[str, float]:
        total_surface_area = architecture_metrics['total_root_surface_area']
        avg_activity = architecture_metrics['average_root_activity']
        temperature = environmental_conditions.get('temperature')
        flow_rate = environmental_conditions.get('flow_rate')
        nutrient_concentrations = environmental_conditions.get('nutrient_concentrations')
        if any(x is None for x in [temperature, flow_rate, nutrient_concentrations]):
            raise ValueError("temperature, flow_rate, and nutrient_concentrations must be provided")
        temp_factor = self.calculate_temperature_factor(temperature)
        flow_factor = self.calculate_flow_factor(flow_rate)
        nutrient_key_mapping = {
            'N-NO3': 'NO3', 'P-PO4': 'PO4', 'K': 'K', 'Ca': 'Ca', 'Mg': 'Mg', 'S-SO4': 'SO4', 'N-NH4': 'NH4'
        }
        uptake_rates = {}
        for solution_key, concentration in nutrient_concentrations.items():
            uptake_key = nutrient_key_mapping.get(solution_key, solution_key)
            if uptake_key in self.params.base_uptake_rates:
                vmax = self.params.base_uptake_rates[uptake_key]
                km = self.params.michaelis_constants[uptake_key]
                michaelis_rate = (vmax * concentration) / (km + concentration)
                inhibition_factor = self.calculate_nutrient_competition(uptake_key, nutrient_concentrations)
                ph_effect = self.calculate_ph_effect_on_uptake(uptake_key, environmental_conditions['ph'])
                transport_temp_effect = temp_factor ** self.params.transport_temp_exponent
                root_age_effect = self.calculate_root_age_effect(architecture_metrics)
                effective_surface_area = self.calculate_effective_surface_area(architecture_metrics)
                uptake_rate = (
                    effective_surface_area * michaelis_rate * inhibition_factor *
                    ph_effect * transport_temp_effect * flow_factor * avg_activity * root_age_effect
                )
                uptake_rates[f'{uptake_key}_uptake_rate'] = uptake_rate
        total_uptake = sum(uptake_rates.values())
        return {
            **uptake_rates,
            'total_nutrient_uptake': total_uptake,
            'uptake_per_surface_area': total_uptake / max(self.params.minimum_surface_area, total_surface_area),
            'uptake_temperature_factor': temp_factor,
            'uptake_flow_factor': flow_factor,
            'effective_root_surface_area': self.calculate_effective_surface_area(architecture_metrics),
            'total_uptake_g_per_day': total_uptake / 1000.0,
            'nitrogen_uptake_g_per_day': uptake_rates.get('NO3_uptake_rate', 0.0) / 1000.0
        }

    def calculate_hourly_nutrient_uptake(self, architecture_metrics: Dict[str, float], 
                                        environmental_conditions: Dict[str, float], dt_hours: float) -> Dict[str, float]:
        total_surface_area = architecture_metrics['total_root_surface_area']
        avg_activity = architecture_metrics['average_root_activity']
        temperature = environmental_conditions.get('temperature')
        flow_rate = environmental_conditions.get('flow_rate')
        nutrient_concentrations = environmental_conditions.get('nutrient_concentrations')
        if any(x is None for x in [temperature, flow_rate, nutrient_concentrations]):
            raise ValueError("temperature, flow_rate, and nutrient_concentrations must be provided")
        temp_factor = self.calculate_temperature_factor(temperature)
        flow_factor = self.calculate_flow_factor(flow_rate)
        nutrient_key_mapping = {
            'N-NO3': 'NO3', 'P-PO4': 'PO4', 'K': 'K', 'Ca': 'Ca', 'Mg': 'Mg', 'S-SO4': 'SO4', 'N-NH4': 'NH4'
        }
        hourly_uptake_rates = {}
        for solution_key, concentration in nutrient_concentrations.items():
            uptake_key = nutrient_key_mapping.get(solution_key, solution_key)
            if uptake_key in self.params.base_uptake_rates:
                vmax = self.params.base_uptake_rates[uptake_key]
                km = self.params.michaelis_constants[uptake_key]
                michaelis_rate = (vmax * concentration) / (km + concentration)
                inhibition_factor = self.calculate_nutrient_competition(uptake_key, nutrient_concentrations)
                ph_effect = self.calculate_ph_effect_on_uptake(uptake_key, environmental_conditions['ph'])
                transport_temp_effect = temp_factor ** self.params.transport_temp_exponent
                root_age_effect = self.calculate_root_age_effect(architecture_metrics)
                effective_surface_area = self.calculate_effective_surface_area(architecture_metrics)
                hourly_uptake_rate = (
                    effective_surface_area * michaelis_rate * inhibition_factor *
                    ph_effect * transport_temp_effect * flow_factor * avg_activity *
                    root_age_effect * dt_hours
                )
                hourly_uptake_rates[f'{uptake_key}_uptake_rate'] = hourly_uptake_rate
        total_hourly_uptake = sum(hourly_uptake_rates.values())
        return {
            **hourly_uptake_rates,
            'total_nutrient_uptake': total_hourly_uptake,
            'uptake_per_surface_area': total_hourly_uptake / max(self.params.minimum_surface_area, total_surface_area),
            'uptake_temperature_factor': temp_factor,
            'uptake_flow_factor': flow_factor,
            'effective_root_surface_area': self.calculate_effective_surface_area(architecture_metrics),
            'total_uptake_g_per_hour': total_hourly_uptake / 1000.0,
            'nitrogen_uptake_g_per_hour': hourly_uptake_rates.get('NO3_uptake_rate', 0.0) / 1000.0
        }

    def get_spatial_uptake_distribution(self) -> Dict[str, Dict[str, float]]:
        distribution = {}
        for i, zone in enumerate(self.root_zones):
            zone_name = f"zone_{i+1}_depth_{zone.depth_range[0]}-{zone.depth_range[1]}cm"
            zone_surface_area = sum(cohort.surface_area for cohort in zone.root_cohorts)
            zone_uptake = {}
            for nutrient, base_rate in self.params.base_uptake_rates.items():
                zone_uptake[f'{nutrient}_capacity'] = zone.calculate_total_uptake_capacity(nutrient, base_rate)
            zone_uptake['total_surface_area'] = zone_surface_area
            zone_uptake['total_capacity'] = sum(v for k, v in zone_uptake.items() if k.endswith('_capacity'))
            distribution[zone_name] = zone_uptake
        return distribution

    def optimize_environmental_conditions(self, target_uptake_rates: Dict[str, float], 
                                        current_concentrations: Dict[str, float]) -> Dict[str, float]:
        if not target_uptake_rates or not current_concentrations:
            raise ValueError("target_uptake_rates and current_concentrations must be provided")
        current_metrics = self.calculate_architecture_metrics()
        best_conditions = {'temperature': 0.0, 'flow_rate': 0.0}
        best_score = 0.0
        for temp in range(self.params.optimization_temp_min, self.params.optimization_temp_max, self.params.optimization_temp_step):
            flow = self.params.optimization_flow_min
            while flow <= self.params.optimization_flow_max:
                temp_factor = self.calculate_temperature_factor(temp)
                flow_factor = self.calculate_flow_factor(flow)
                score = 0.0
                for nutrient, target_rate in target_uptake_rates.items():
                    if nutrient in self.params.base_uptake_rates:
                        base_rate = self.params.base_uptake_rates[nutrient]
                        concentration = current_concentrations.get(nutrient, 0.0)
                        km = self.params.michaelis_constants.get(nutrient, self.params.default_michaelis_constant)
                        predicted_uptake = (
                            current_metrics['total_root_surface_area'] * base_rate * temp_factor *
                            flow_factor * (concentration / (concentration + km))
                        )
                        error = abs(predicted_uptake - target_rate)
                        score += 1.0 / (1.0 + error / max(1e-6, target_rate))
                if score > best_score:
                    best_score = score
                    best_conditions = {'temperature': temp, 'flow_rate': flow}
                flow += self.params.optimization_flow_step
        return {
            **best_conditions,
            'optimization_score': best_score,
            'predicted_improvement': (best_score / max(1, len(target_uptake_rates))) * 100.0
        }

def create_lettuce_root_system_model(system_config: Any) -> EnhancedRootSystemModel:
    if not system_config:
        raise ValueError("System configuration must be provided")
    config = getattr(system_config, 'root_system_parameters', None)
    if not config:
        raise ValueError("root_system_parameters section must be provided in configuration")
    parameters = RootSystemParameters.from_config(config)
    return EnhancedRootSystemModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- container_volume: Reservoir tank volume (cm³)
- channel_length: Length of channels (cm)
- system_type: Hydroponic system type (NFT, DWC, AEROPONICS, DRIP, WICK, EBB_FLOW)
- channel_width: Width of channels (cm)
- channel_depth: Depth of channels (cm)
- n_channels: Number of parallel channels
- root_zone_independent: Whether root zone size is independent of tank volume
- primary_root_growth_rate: Primary root growth rate (cm/day)
- lateral_root_density: Lateral roots per cm of primary root
- branching_angle_mean: Mean branching angle (degrees)
- branching_angle_std: Standard deviation of branching angle (degrees)
- fine_root_fraction, medium_root_fraction, coarse_root_fraction: Fractions of root types
- fine_diameter_mean, fine_diameter_std, medium_diameter_mean, medium_diameter_std, 
  coarse_diameter_mean, coarse_diameter_std: Root diameter means and standard deviations (mm)
- fine_turnover_rate, medium_turnover_rate, coarse_turnover_rate: Root turnover rates (fraction/day)
- fine_root_half_life_days, medium_root_half_life_days, coarse_root_half_life_days: Root half-life for activity decay (days)
- root_zone_efficiency_factor: Efficiency factor for root zone volume
- fine_min_activity, medium_min_activity, coarse_min_activity: Minimum activity factors for root types
- establishment_plateau_days: Days of establishment plateau for root activity
- initial_root_activity: Initial activity factor for new roots
- system_multipliers: Dictionary of system-specific multipliers (root_length_multiplier, surface_area_multiplier, branching_multiplier)
- base_uptake_rates: Dictionary of nutrient uptake Vmax values (mg/cm²/day)
- michaelis_constants: Dictionary of nutrient Km values (mg/L)
- fine_root_effectiveness, medium_root_effectiveness, coarse_root_effectiveness: Effectiveness factors for root types
- optimal_temperature: Optimal temperature for uptake (°C)
- q10_factor: Q10 factor for temperature response
- optimal_flow_rate: Optimal flow rate (L/min)
- flow_stress_threshold: Flow rate stress threshold (L/min)
- root_growth_auxin_decay_rate: Auxin decay rate for growth potential
- root_optimal_density: Optimal root length density (cm/cm³)
- root_density_stress_factor: Density stress factor
- root_temp_optimum: Optimal root temperature (°C)
- root_temp_max: Maximum root temperature (°C)
- root_temp_min_factor: Minimum temperature factor
- root_oxygen_optimum: Optimal dissolved oxygen level (mg/L)
- root_oxygen_min_factor: Minimum oxygen factor
- nutrient_demand_weights: Weights for nutrient growth signals
- nutrient_reference_concentrations: Reference concentrations for nutrients (mg/L)
- nutrient_competition_groups: Groups of competing nutrients
- nutrient_ph_optima: Optimal pH ranges for nutrients
- ph_stress_range_acidic, ph_stress_range_basic: pH stress ranges
- ph_stress_factor: pH stress factor
- young_root_activity, old_root_activity: Activity factors for young and old roots

INPUT VARIABLES:
- environmental_conditions: Dictionary with temperature (°C), flow_rate (L/min), oxygen_level (mg/L), ph, nutrient_concentrations (mg/L)
- growth_factors: Dictionary with nitrogen_stress, water_stress, temperature_stress (0-1)
- dt_hours: Time step in hours for hourly updates

OUTPUT VARIABLES:
- RootSystemMetrics (daily):
  - total_root_length: Total root length (cm)
  - total_root_surface_area: Total root surface area (cm²)
  - total_root_biomass: Total root biomass (g)
  - total_root_volume: Total root volume (cm³)
  - root_length_density: Root length density (cm/cm³)
  - root_surface_area_density: Root surface area density (cm²/cm³)
  - specific_root_length: Specific root length (cm/g)
  - average_root_activity: Average root activity factor
  - fine_root_length, medium_root_length, coarse_root_length: Lengths by root type (cm)
  - fine_root_fraction: Fraction of fine roots
  - root_age_days: Total root system age (days)
  - cumulative_growth: Cumulative root growth (cm)
  - total_nutrient_uptake: Total nutrient uptake (mg/day)
  - uptake_per_surface_area: Uptake per surface area (mg/cm²/day)
  - uptake_temperature_factor: Temperature factor for uptake
  - uptake_flow_factor: Flow rate factor for uptake
  - effective_root_surface_area: Effective surface area for uptake (cm²)
  - total_uptake_g_per_day: Total uptake (g/day)
  - nitrogen_uptake_g_per_day: Nitrogen uptake (g/day)
  - nutrient_uptake_rates: Dictionary of nutrient-specific uptake rates (mg/day)
- Dictionary (hourly):
  - Same as daily metrics, plus:
  - total_uptake_g_per_hour: Total uptake (g/hour)
  - nitrogen_uptake_g_per_hour: Nitrogen uptake (g/hour)

FUNCTION EXPLANATIONS FOR NON-CODERS:
This model simulates the plant's root system in hydroponic setups, like the "plumbing" that absorbs water and nutrients. It tracks root growth, structure, and nutrient uptake under varying conditions.

1. calculate_architecture_metrics:
   - Calculates root system properties: length, surface area, biomass.
   - Like measuring a city's road network: total length, area covered, and materials used.

2. calculate_effective_surface_area:
   - Determines the effective surface area for nutrient uptake: `area = Σ(type_area * effectiveness)`.
   - Like calculating the usable surface of a sponge, considering different root types' efficiency.

3. calculate_temperature_factor:
   - Adjusts rates based on temperature: `factor = Q10^(ΔT/10)`.
   - Like how your activity changes with temperature; roots work best at optimal temperatures.

4. calculate_flow_factor:
   - Adjusts uptake based on nutrient solution flow: `factor = min(1, 0.5 + 0.5 * flow/optimal)`.
   - Like how water flow affects a waterwheel's efficiency; too slow or fast reduces performance.

5. calculate_nutrient_competition:
   - Models nutrient competition: `factor = 1/(1 + Σ([I]/Ki))`.
   - Like people competing for limited bus seats; similar nutrients compete for root transporters.

6. calculate_ph_effect_on_uptake:
   - Adjusts uptake based on pH: `factor = 1 - stress * factor if outside optimal range`.
   - Like how food digestion depends on stomach acidity; nutrients absorb best at specific pH levels.

7. calculate_root_age_effect:
   - Adjusts uptake based on root age: `effect = fine_fraction * young + (1-fine_fraction) * old`.
   - Like how new tools work better than old ones; young roots absorb more efficiently.

8. calculate_daily_root_metrics:
   - Updates root growth and calculates daily uptake: combines architecture and uptake.
   - Like a daily report on a city's infrastructure and resource consumption.

9. calculate_hourly_root_metrics:
   - Calculates hourly uptake using cached architecture: `uptake = daily_uptake * dt_hours`.
   - Like hourly updates on a factory's production, using daily structure data.

10. generate_new_roots:
    - Grows new roots: `growth = base_rate * stress_factors * multipliers`.
    - Like a city expanding roads where resources are plentiful and conditions are good.

11. calculate_zone_growth_potential:
    - Determines where roots grow: `potential = auxin + nutrients + oxygen + competition + temp`.
    - Like deciding where to build new roads based on demand, space, and resources.

PRACTICAL APPLICATIONS:
- Optimizes nutrient delivery by adjusting solution concentrations and pH.
- Guides system design for adequate root space and aeration.
- Predicts root growth to prevent overcrowding or nutrient depletion.
- Supports temperature and flow rate control for maximum uptake efficiency.
- Helps diagnose root health issues (e.g., low oxygen causing root rot).
"""