from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class NitrogenBalanceParameters:
    nitrate_reduction_rate: float
    ammonium_assimilation_rate: float
    amino_acid_uptake_rate: float
    photosynthetic_n_use_efficiency: float
    growth_n_use_efficiency: float
    n_stress_threshold: float
    luxury_uptake_threshold: float
    specific_root_activity: float
    root_zone_exploration: float
    uptake_kinetics: Dict[str, Dict[str, float]]
    allocation_coefficients: Dict[str, Dict[str, float]]
    critical_n_concentrations: Dict[str, Dict[str, float]]
    remobilization_rates: Dict[str, float]
    remobilization_efficiency: Dict[str, float]
    organ_weights: Dict[str, float]
    pool_fractions: Dict[str, Dict[str, float]]
    cache_timeout: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'NitrogenBalanceParameters':
        required_params = [
            'nitrate_reduction_rate', 'ammonium_assimilation_rate', 'amino_acid_uptake_rate',
            'photosynthetic_n_use_efficiency', 'growth_n_use_efficiency', 'n_stress_threshold',
            'luxury_uptake_threshold', 'specific_root_activity', 'root_zone_exploration', 'cache_timeout'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")

        required_dicts = ['uptake_kinetics', 'allocation_coefficients', 'critical_n_concentrations',
                         'remobilization_rates', 'remobilization_efficiency', 'organ_weights']
        for dict_param in required_dicts:
            if dict_param not in config:
                raise KeyError(f"Missing required dictionary parameter: {dict_param}")

        n_forms = ['NO3', 'NH4', 'amino_acids']
        for n_form in n_forms:
            if n_form not in config['uptake_kinetics']:
                raise KeyError(f"Missing uptake kinetics for {n_form}")
            required_kinetics = ['vmax', 'km', 'min_conc', 'inhibition_ki']
            for key in required_kinetics:
                if key not in config['uptake_kinetics'][n_form]:
                    raise KeyError(f"Missing {key} for {n_form} in uptake_kinetics")

        organs = ['leaves', 'stems', 'roots', 'reproductive']
        for organ in organs:
            if organ not in config['allocation_coefficients']['vegetative']:
                raise KeyError(f"Missing allocation coefficients for {organ} in vegetative stage")
            if organ not in config['allocation_coefficients']['reproductive']:
                raise KeyError(f"Missing allocation coefficients for {organ} in reproductive stage")
            if organ not in config['critical_n_concentrations']:
                raise KeyError(f"Missing critical N concentrations for {organ}")
            required_concs = ['minimum', 'critical', 'optimal', 'maximum']
            for key in required_concs:
                if key not in config['critical_n_concentrations'][organ]:
                    raise KeyError(f"Missing {key} concentration for {organ}")
            if organ not in config['remobilization_efficiency']:
                raise KeyError(f"Missing remobilization efficiency for {organ}")
            if organ not in config['organ_weights']:
                raise KeyError(f"Missing organ weight for {organ}")

        pool_types = ['structural', 'metabolic', 'storage', 'transport']
        pool_fractions = {'leaves': {}, 'stems': {}, 'roots': {}, 'reproductive': {}}
        for organ in organs:
            for pool in pool_types:
                key = f"pool_fractions_{organ}_{pool}"
                if key not in config:
                    raise KeyError(f"Missing pool fraction for {organ} {pool}")
                pool_fractions[organ][pool] = float(config[key])

        remob_pools = ['structural', 'metabolic', 'storage', 'transport']
        for pool in remob_pools:
            if pool not in config['remobilization_rates']:
                raise KeyError(f"Missing remobilization rate for pool {pool}")

        return cls(
            nitrate_reduction_rate=float(config['nitrate_reduction_rate']),
            ammonium_assimilation_rate=float(config['ammonium_assimilation_rate']),
            amino_acid_uptake_rate=float(config['amino_acid_uptake_rate']),
            photosynthetic_n_use_efficiency=float(config['photosynthetic_n_use_efficiency']),
            growth_n_use_efficiency=float(config['growth_n_use_efficiency']),
            n_stress_threshold=float(config['n_stress_threshold']),
            luxury_uptake_threshold=float(config['luxury_uptake_threshold']),
            specific_root_activity=float(config['specific_root_activity']),
            root_zone_exploration=float(config['root_zone_exploration']),
            uptake_kinetics=config['uptake_kinetics'],
            allocation_coefficients=config['allocation_coefficients'],
            critical_n_concentrations=config['critical_n_concentrations'],
            remobilization_rates=config['remobilization_rates'],
            remobilization_efficiency=config['remobilization_efficiency'],
            organ_weights=config['organ_weights'],
            pool_fractions=pool_fractions,
            cache_timeout=float(config['cache_timeout'])
        )

@dataclass
class OrganNitrogenState:
    organ_name: str
    dry_mass: float
    total_nitrogen: float
    nitrogen_concentration: float
    structural_n: float = 0.0
    metabolic_n: float = 0.0
    storage_n: float = 0.0
    transport_n: float = 0.0
    daily_uptake: float = 0.0
    daily_remobilization: float = 0.0
    nitrogen_status: str = "unknown"

@dataclass
class NitrogenUptakeResponse:
    total_uptake: float
    uptake_by_form: Dict[str, float]
    uptake_rate_by_form: Dict[str, float]
    root_activity: float
    uptake_efficiency: float
    limiting_factors: List[str]

@dataclass
class NitrogenAllocationResponse:
    allocated_by_organ: Dict[str, float]
    allocation_efficiency: float
    nitrogen_demand: Dict[str, float]
    demand_satisfaction: Dict[str, float]
    growth_limitation: float

@dataclass
class NitrogenBalanceResponse:
    uptake_response: NitrogenUptakeResponse
    allocation_response: NitrogenAllocationResponse
    organ_states: Dict[str, OrganNitrogenState]
    total_plant_nitrogen: float
    nitrogen_use_efficiency: float
    nitrogen_stress_level: float
    remobilized_nitrogen: float
    nitrogen_balance: float
    mass_balance_error: float
    total_n_input: float
    total_allocated: float
    estimated_losses: float
    storage_change: float

class NitrogenBalanceModel:
    def __init__(self, parameters: NitrogenBalanceParameters):
        self.params = parameters
        self.organ_states: Dict[str, OrganNitrogenState] = {}
        self.nitrogen_history: List[Dict[str, Any]] = []
        self.total_cumulative_uptake: float = 0.0
        self.total_cumulative_remobilization: float = 0.0
    
    def initialize(self):
        """Initialize the nitrogen balance model"""
        pass

    def initialize_organ_nitrogen(self, organ_name: str, initial_dry_mass: float, initial_n_concentration: float):
        if organ_name not in self.params.critical_n_concentrations:
            raise KeyError(f"Missing critical N concentrations for {organ_name}")
        if initial_dry_mass <= 0:
            raise ValueError("Initial dry mass must be positive")
        initial_total_n = initial_dry_mass * initial_n_concentration
        pool_fractions = self.params.pool_fractions[organ_name]
        self.organ_states[organ_name] = OrganNitrogenState(
            organ_name=organ_name,
            dry_mass=initial_dry_mass,
            total_nitrogen=initial_total_n,
            nitrogen_concentration=initial_n_concentration,
            structural_n=initial_total_n * pool_fractions['structural'],
            metabolic_n=initial_total_n * pool_fractions['metabolic'],
            storage_n=initial_total_n * pool_fractions['storage'],
            transport_n=initial_total_n * pool_fractions['transport']
        )
        self.update_organ_nitrogen_status(organ_name)

    def calculate_nitrogen_uptake(self, root_mass: float, solution_concentrations: Dict[str, float],
                                 environmental_factors: Dict[str, float]) -> NitrogenUptakeResponse:
        required_env = ['temperature_factor', 'water_status', 'root_health', 'ph_factor']
        for key in required_env:
            if key not in environmental_factors:
                raise KeyError(f"Missing environmental factor: {key}")
        if root_mass <= 0:
            raise ValueError("Root mass must be positive")
        for n_form in ['NO3', 'NH4', 'amino_acids']:
            if n_form not in solution_concentrations:
                raise KeyError(f"Missing concentration for {n_form}")

        total_uptake = 0.0
        uptake_by_form = {}
        uptake_rate_by_form = {}
        limiting_factors = []

        env_factor = (environmental_factors['temperature_factor'] * environmental_factors['water_status'] *
                      environmental_factors['root_health'] * environmental_factors['ph_factor'])
        if env_factor < 0.8:
            limiting_factors.append('environmental_stress')

        for n_form, concentration in solution_concentrations.items():
            if n_form not in self.params.uptake_kinetics:
                raise KeyError(f"Missing uptake kinetics for {n_form}")
            kinetics = self.params.uptake_kinetics[n_form]
            if concentration >= kinetics['min_conc']:
                uptake_rate = (kinetics['vmax'] * concentration) / (kinetics['km'] + concentration)
                uptake_rate *= env_factor
                actual_uptake = uptake_rate * root_mass * self.params.root_zone_exploration
                if n_form == 'NO3' and 'NH4' in solution_concentrations:
                    nh4_conc = solution_concentrations['NH4']
                    inhibition_factor = kinetics['inhibition_ki'] / (kinetics['inhibition_ki'] + nh4_conc)
                    actual_uptake *= inhibition_factor
                uptake_by_form[n_form] = actual_uptake
                uptake_rate_by_form[n_form] = uptake_rate
                total_uptake += actual_uptake
                if concentration < kinetics['km']:
                    limiting_factors.append(f'{n_form}_concentration')
            else:
                uptake_by_form[n_form] = 0.0
                uptake_rate_by_form[n_form] = 0.0
                limiting_factors.append(f'{n_form}_below_minimum')

        root_activity = total_uptake / root_mass if root_mass > 0 else 0.0
        uptake_efficiency = root_activity / self.params.specific_root_activity if self.params.specific_root_activity > 0 else 0.0

        return NitrogenUptakeResponse(
            total_uptake=total_uptake,
            uptake_by_form=uptake_by_form,
            uptake_rate_by_form=uptake_rate_by_form,
            root_activity=root_activity,
            uptake_efficiency=min(1.0, uptake_efficiency),
            limiting_factors=list(set(limiting_factors))
        )

    def calculate_nitrogen_demand(self, organ_growth_rates: Dict[str, float], growth_stage: str,
                                 environmental_factors: Dict[str, float]) -> Dict[str, float]:
        required_env = ['temperature', 'water', 'pH']
        for key in required_env:
            if key not in environmental_factors:
                raise KeyError(f"Missing environmental factor: {key}")

        # Map growth stages to allocation coefficients stages
        stage_map = {'mature': 'reproductive', 'head_formation': 'reproductive'}
        mapped_stage = stage_map.get(growth_stage, growth_stage)

        if mapped_stage not in self.params.allocation_coefficients:
            raise KeyError(f"Invalid growth stage: {growth_stage}")

        demand_by_organ = {}
        env_stress = min(environmental_factors['temperature'], environmental_factors['water'], environmental_factors['pH'])
        if env_stress <= 0:
            raise ValueError("Environmental stress factor must be positive")
        demand_modifier = 1.0 / env_stress

        for organ_name, growth_rate in organ_growth_rates.items():
            if organ_name not in self.params.critical_n_concentrations:
                raise KeyError(f"Missing critical N concentrations for {organ_name}")
            n_concs = self.params.critical_n_concentrations[organ_name]
            target_concentration = n_concs['optimal']
            if mapped_stage == 'vegetative' and organ_name == 'leaves':
                target_concentration *= 1.1
            elif mapped_stage == 'reproductive' and organ_name == 'reproductive':
                target_concentration *= 1.2
            demand_by_organ[organ_name] = growth_rate * target_concentration * demand_modifier if growth_rate > 0 else 0.0

        return demand_by_organ

    def allocate_nitrogen(self, available_nitrogen: float, nitrogen_demand: Dict[str, float],
                         growth_stage: str) -> NitrogenAllocationResponse:
        # Map growth stages to allocation coefficients stages
        stage_map = {'mature': 'reproductive', 'head_formation': 'reproductive'}
        mapped_stage = stage_map.get(growth_stage, growth_stage)

        if mapped_stage not in self.params.allocation_coefficients:
            raise KeyError(f"Invalid growth stage: {growth_stage}")
        priorities = self.params.allocation_coefficients[mapped_stage]
        allocated_by_organ = {}
        demand_satisfaction = {}
        total_demand = sum(nitrogen_demand.values())

        if total_demand <= 0:
            for organ_name in nitrogen_demand:
                if organ_name not in priorities:
                    raise KeyError(f"Missing allocation priority for {organ_name}")
                allocated_by_organ[organ_name] = 0.0
                demand_satisfaction[organ_name] = 1.0
            allocation_efficiency = 1.0
            growth_limitation = 0.0
        else:
            if available_nitrogen >= total_demand:
                allocated_by_organ = nitrogen_demand.copy()
                demand_satisfaction = {organ: 1.0 for organ in nitrogen_demand}
                allocation_efficiency = 1.0
                growth_limitation = 0.0
                excess_n = available_nitrogen - total_demand
                for organ_name in allocated_by_organ:
                    if organ_name not in priorities:
                        raise KeyError(f"Missing allocation priority for {organ_name}")
                    allocated_by_organ[organ_name] += excess_n * priorities[organ_name]
            else:
                allocation_efficiency = available_nitrogen / total_demand
                growth_limitation = 1.0 - allocation_efficiency
                total_weighted_demand = 0.0
                for organ_name, demand in nitrogen_demand.items():
                    if organ_name not in priorities:
                        raise KeyError(f"Missing allocation priority for {organ_name}")
                    total_weighted_demand += demand * priorities[organ_name]
                if total_weighted_demand <= 0:
                    raise ValueError("Total weighted demand must be positive")
                for organ_name, demand in nitrogen_demand.items():
                    weighted_fraction = (demand * priorities[organ_name]) / total_weighted_demand
                    allocated_n = available_nitrogen * weighted_fraction
                    allocated_by_organ[organ_name] = allocated_n
                    demand_satisfaction[organ_name] = allocated_n / demand if demand > 0 else 1.0

        return NitrogenAllocationResponse(
            allocated_by_organ=allocated_by_organ,
            allocation_efficiency=allocation_efficiency,
            nitrogen_demand=nitrogen_demand,
            demand_satisfaction=demand_satisfaction,
            growth_limitation=growth_limitation
        )

    def calculate_nitrogen_remobilization(self, stress_factors: Dict[str, float], senescence_rates: Dict[str, float],
                                         environmental_factors: Dict[str, float]) -> float:
        required_env = ['temperature', 'water', 'pH']
        for key in required_env:
            if key not in environmental_factors:
                raise KeyError(f"Missing environmental factor: {key}")
        for organ_name in self.organ_states:
            if organ_name not in senescence_rates:
                raise KeyError(f"Missing senescence rate for {organ_name}")

        total_remobilized = 0.0
        env_effect = environmental_factors['temperature'] * environmental_factors['water'] * environmental_factors['pH']
        overall_stress = 1.0 - min(stress_factors.values()) if stress_factors else 1.0

        if overall_stress > 0.3:
            for organ_name, organ_state in self.organ_states.items():
                if organ_name not in self.params.remobilization_efficiency:
                    raise KeyError(f"Missing remobilization efficiency for {organ_name}")
                remobilizable_n = 0.0
                storage_remob = organ_state.storage_n * self.params.remobilization_rates['storage'] * env_effect
                metabolic_remob = organ_state.metabolic_n * self.params.remobilization_rates['metabolic'] * overall_stress * env_effect
                transport_remob = organ_state.transport_n * self.params.remobilization_rates['transport'] * min(env_effect, 1.2)
                remobilizable_n = storage_remob + metabolic_remob + transport_remob
                efficiency = self.params.remobilization_efficiency[organ_name]
                daily_remobilization = remobilizable_n * efficiency
                organ_state.storage_n -= storage_remob
                organ_state.metabolic_n -= metabolic_remob * overall_stress
                organ_state.transport_n -= transport_remob
                organ_state.daily_remobilization = daily_remobilization
                total_remobilized += daily_remobilization

        for organ_name, senescence_rate in senescence_rates.items():
            if organ_name in self.organ_states and organ_name in self.params.remobilization_efficiency and senescence_rate > 0:
                organ_state = self.organ_states[organ_name]
                efficiency = self.params.remobilization_efficiency[organ_name]
                senescence_remob = organ_state.total_nitrogen * senescence_rate * efficiency * 0.5 * env_effect
                organ_state.daily_remobilization += senescence_remob
                total_remobilized += senescence_remob

        return total_remobilized

    def update_organ_nitrogen_status(self, organ_name: str):
        if organ_name not in self.organ_states:
            raise KeyError(f"Organ {organ_name} not initialized")
        organ_state = self.organ_states[organ_name]
        if organ_name not in self.params.critical_n_concentrations:
            raise KeyError(f"Missing critical N concentrations for {organ_name}")
        n_concs = self.params.critical_n_concentrations[organ_name]
        current_conc = organ_state.nitrogen_concentration
        if current_conc < n_concs['minimum']:
            organ_state.nitrogen_status = 'severe_deficiency'
        elif current_conc < n_concs['critical']:
            organ_state.nitrogen_status = 'deficient'
        elif current_conc < n_concs['optimal']:
            organ_state.nitrogen_status = 'critical'
        elif current_conc <= n_concs['maximum']:
            organ_state.nitrogen_status = 'optimal'
        else:
            organ_state.nitrogen_status = 'luxury'

    def calculate_nitrogen_stress_level(self) -> float:
        if not self.organ_states:
            raise ValueError("No organ states initialized")
        weighted_stress = 0.0
        total_weight = 0.0
        for organ_name, organ_state in self.organ_states.items():
            if organ_name not in self.params.critical_n_concentrations:
                raise KeyError(f"Missing critical N concentrations for {organ_name}")
            if organ_name not in self.params.organ_weights:
                raise KeyError(f"Missing organ weight for {organ_name}")
            n_concs = self.params.critical_n_concentrations[organ_name]
            current_conc = organ_state.nitrogen_concentration
            critical_conc = n_concs['critical']
            optimal_conc = n_concs['optimal']
            if current_conc >= optimal_conc:
                organ_stress = 0.0
            elif current_conc >= critical_conc:
                organ_stress = 1.0 - (current_conc - critical_conc) / (optimal_conc - critical_conc)
            else:
                organ_stress = 0.9
            weight = self.params.organ_weights[organ_name]
            weighted_stress += organ_stress * weight
            total_weight += weight
        if total_weight <= 0:
            raise ValueError("Total organ weight must be positive")
        return max(0.0, min(1.0, weighted_stress / total_weight))

    def update_nitrogen_pools(self, external_nitrogen_input: float, organ_growth_rates: Dict[str, float],
                             environmental_factors: Dict[str, float], growth_stage: str,
                             stress_factors: Dict[str, float], senescence_rates: Dict[str, float]) -> NitrogenBalanceResponse:
        required_env = ['temperature', 'water', 'pH']
        for key in required_env:
            if key not in environmental_factors:
                raise KeyError(f"Missing environmental factor: {key}")
        for organ_name in organ_growth_rates:
            if organ_name not in self.organ_states:
                raise KeyError(f"Organ {organ_name} not initialized")
            if organ_name not in senescence_rates:
                raise KeyError(f"Missing senescence rate for {organ_name}")

        uptake_response = NitrogenUptakeResponse(
            total_uptake=external_nitrogen_input,
            uptake_by_form={'external': external_nitrogen_input},
            uptake_rate_by_form={},
            root_activity=0.0,
            uptake_efficiency=1.0,
            limiting_factors=[]
        )

        remobilized_n = self.calculate_nitrogen_remobilization(stress_factors, senescence_rates, environmental_factors)
        available_n = external_nitrogen_input + remobilized_n
        n_demand = self.calculate_nitrogen_demand(organ_growth_rates, growth_stage, environmental_factors)
        allocation_response = self.allocate_nitrogen(available_n, n_demand, growth_stage)

        for organ_name, allocated_n in allocation_response.allocated_by_organ.items():
            organ_state = self.organ_states[organ_name]
            if organ_name in organ_growth_rates and organ_growth_rates[organ_name] > 0:
                organ_state.dry_mass += organ_growth_rates[organ_name]
            organ_state.total_nitrogen += allocated_n
            organ_state.daily_uptake = allocated_n
            pool_fractions = self.params.pool_fractions[organ_name]
            if allocated_n > 0:
                organ_state.structural_n += allocated_n * pool_fractions['structural']
                organ_state.metabolic_n += allocated_n * pool_fractions['metabolic']
                organ_state.storage_n += allocated_n * pool_fractions['storage']
                organ_state.transport_n += allocated_n * pool_fractions['transport']
            total_pools = organ_state.structural_n + organ_state.metabolic_n + organ_state.storage_n + organ_state.transport_n
            if abs(total_pools - organ_state.total_nitrogen) > 0.001:
                normalization_factor = organ_state.total_nitrogen / total_pools
                organ_state.structural_n *= normalization_factor
                organ_state.metabolic_n *= normalization_factor
                organ_state.storage_n *= normalization_factor
                organ_state.transport_n *= normalization_factor
            organ_state.nitrogen_concentration = organ_state.total_nitrogen / organ_state.dry_mass if organ_state.dry_mass > 0 else 0.0
            self.update_organ_nitrogen_status(organ_name)

        n_stress_level = self.calculate_nitrogen_stress_level()
        total_plant_n = sum(state.total_nitrogen for state in self.organ_states.values())
        total_biomass = sum(state.dry_mass for state in self.organ_states.values())
        nue = total_biomass / total_plant_n if total_plant_n > 0 else 0.0
        total_growth_demand = sum(n_demand.values())
        total_allocated = sum(allocation_response.allocated_by_organ.values())
        estimated_losses = total_allocated * 0.05
        storage_change = available_n - total_allocated - estimated_losses
        n_balance = available_n - total_growth_demand
        mass_balance_error = abs(available_n - total_allocated - estimated_losses - storage_change)

        self.total_cumulative_uptake += external_nitrogen_input
        self.total_cumulative_remobilization += remobilized_n
        self.nitrogen_history.append({
            'total_uptake': external_nitrogen_input,
            'remobilized': remobilized_n,
            'total_plant_n': total_plant_n,
            'nue': nue,
            'n_stress': n_stress_level
        })

        return NitrogenBalanceResponse(
            uptake_response=uptake_response,
            allocation_response=allocation_response,
            organ_states=self.organ_states.copy(),
            total_plant_nitrogen=total_plant_n,
            nitrogen_use_efficiency=nue,
            nitrogen_stress_level=n_stress_level,
            remobilized_nitrogen=remobilized_n,
            nitrogen_balance=n_balance,
            mass_balance_error=mass_balance_error,
            total_n_input=available_n,
            total_allocated=total_allocated,
            estimated_losses=estimated_losses,
            storage_change=storage_change
        )

    def get_nitrogen_summary(self) -> Dict[str, Any]:
        if not self.organ_states:
            raise ValueError("No organ states initialized")
        total_plant_n = sum(state.total_nitrogen for state in self.organ_states.values())
        total_biomass = sum(state.dry_mass for state in self.organ_states.values())
        return {
            'total_plant_nitrogen': total_plant_n,
            'total_biomass': total_biomass,
            'nitrogen_use_efficiency': total_biomass / max(total_plant_n, 0.001),
            'cumulative_uptake': self.total_cumulative_uptake,
            'cumulative_remobilization': self.total_cumulative_remobilization,
            'nitrogen_stress_level': self.calculate_nitrogen_stress_level(),
            'organ_n_concentrations': {name: state.nitrogen_concentration for name, state in self.organ_states.items()},
            'organ_n_status': {name: state.nitrogen_status for name, state in self.organ_states.items()},
            'nitrogen_distribution': {name: state.total_nitrogen for name, state in self.organ_states.items()}
        }

def create_lettuce_nitrogen_balance_model(system_config: Any) -> 'NitrogenBalanceModel':
    if system_config is None:
        raise ValueError("System configuration must be provided")

    # Get nitrogen parameters
    nitrogen_config = getattr(system_config, 'nitrogen_parameters', None)
    if nitrogen_config is None:
        raise ValueError("nitrogen_parameters section must be provided in configuration")

    # Get additional parameters from other sections to avoid duplicates
    leaf_dev_config = getattr(system_config, 'leaf_development', {})

    # Create merged config using existing parameters where available
    merged_config = dict(nitrogen_config)

    # Use existing n_stress_threshold from leaf_development instead of duplicate
    if 'n_stress_threshold' in leaf_dev_config:
        merged_config['n_stress_threshold'] = leaf_dev_config['n_stress_threshold']
    elif 'n_stress_threshold' not in merged_config:
        # Fallback if neither exists
        merged_config['n_stress_threshold'] = 0.7

    # Reconstruct nested dictionaries from flat CSV parameters

    # 1. Uptake kinetics
    uptake_kinetics = {}
    for n_form in ['NO3', 'NH4', 'amino_acids']:
        uptake_kinetics[n_form] = {}
        for param in ['vmax', 'km', 'min_conc', 'inhibition_ki']:
            key = f'uptake_kinetics_{n_form}_{param}'
            if key in merged_config:
                uptake_kinetics[n_form][param] = merged_config[key]
    merged_config['uptake_kinetics'] = uptake_kinetics

    # 2. Allocation coefficients
    allocation_coefficients = {}
    for stage in ['vegetative', 'reproductive']:
        allocation_coefficients[stage] = {}
        for organ in ['leaves', 'stems', 'roots', 'reproductive']:
            key = f'allocation_coefficients_{stage}_{organ}'
            if key in merged_config:
                allocation_coefficients[stage][organ] = merged_config[key]
    merged_config['allocation_coefficients'] = allocation_coefficients

    # 3. Critical N concentrations
    critical_n_concentrations = {}
    for organ in ['leaves', 'stems', 'roots', 'reproductive']:
        critical_n_concentrations[organ] = {}
        for level in ['minimum', 'critical', 'optimal', 'maximum']:
            key = f'critical_n_concentrations_{organ}_{level}'
            if key in merged_config:
                critical_n_concentrations[organ][level] = merged_config[key]
    merged_config['critical_n_concentrations'] = critical_n_concentrations

    # 4. Remobilization rates
    remobilization_rates = {}
    for pool in ['structural', 'metabolic', 'storage', 'transport']:
        key = f'remobilization_rates_{pool}'
        if key in merged_config:
            remobilization_rates[pool] = merged_config[key]
    merged_config['remobilization_rates'] = remobilization_rates

    # 5. Remobilization efficiency
    remobilization_efficiency = {}
    for organ in ['leaves', 'stems', 'roots', 'reproductive']:
        key = f'remobilization_efficiency_{organ}'
        if key in merged_config:
            remobilization_efficiency[organ] = merged_config[key]
    merged_config['remobilization_efficiency'] = remobilization_efficiency

    # 6. Organ weights
    organ_weights = {}
    for organ in ['leaves', 'stems', 'roots', 'reproductive']:
        key = f'organ_weights_{organ}'
        if key in merged_config:
            organ_weights[organ] = merged_config[key]
    merged_config['organ_weights'] = organ_weights

    parameters = NitrogenBalanceParameters.from_config(merged_config)
    return NitrogenBalanceModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- nitrate_reduction_rate: Rate of nitrate reduction to ammonium (g N/g root/day)
- ammonium_assimilation_rate: Rate of ammonium assimilation into amino acids (g N/g root/day)
- amino_acid_uptake_rate: Rate of amino acid uptake (g N/g root/day)
- photosynthetic_n_use_efficiency: Biomass produced per unit nitrogen in photosynthesis (g biomass/g N)
- growth_n_use_efficiency: Biomass produced per unit nitrogen in growth (g biomass/g N)
- n_stress_threshold: Nitrogen stress threshold for plant response (g N/g dry mass)
- luxury_uptake_threshold: Threshold for luxury nitrogen uptake (g N/g dry mass)
- specific_root_activity: Maximum nitrogen uptake rate per unit root mass (g N/g root/day)
- root_zone_exploration: Root zone exploration factor (dimensionless)
- uptake_kinetics: Dictionary with keys NO3, NH4, amino_acids, each containing:
  - vmax: Maximum uptake rate (g N/g root/day)
  - km: Michaelis constant (mg N/L)
  - min_conc: Minimum concentration for uptake (mg N/L)
  - inhibition_ki: Inhibition constant for competitive uptake (mg N/L)
- allocation_coefficients: Dictionary with keys vegetative, reproductive, each containing organ priorities for leaves, stems, roots, reproductive
- critical_n_concentrations: Dictionary for leaves, stems, roots, reproductive, each containing:
  - minimum: Minimum N concentration (g N/g dry mass)
  - critical: Critical N concentration (g N/g dry mass)
  - optimal: Optimal N concentration (g N/g dry mass)
  - maximum: Maximum N concentration (g N/g dry mass)
- remobilization_rates: Dictionary for structural, metabolic, storage, transport pools (g N/g pool/day)
- remobilization_efficiency: Dictionary for leaves, stems, roots, reproductive (dimensionless)
- organ_weights: Dictionary for leaves, stems, roots, reproductive for stress calculation (dimensionless)
- pool_fractions_[organ]_[pool]: Fractions for structural, metabolic, storage, transport pools for each organ (dimensionless)

INPUT VARIABLES:
- root_mass: Root dry mass (g)
- solution_concentrations: Nitrogen concentrations by form NO3, NH4, amino_acids (mg N/L)
- environmental_factors: Dictionary with temperature_factor, water_status, root_health, ph_factor for uptake; temperature, water, pH for others (dimensionless or °C)
- organ_growth_rates: Growth rates by organ (g dry mass/day)
- growth_stage: Current growth stage (vegetative, reproductive)
- stress_factors: Stress levels by type (0-1, 1=no stress)
- senescence_rates: Senescence rates by organ (fraction/day)

OUTPUT VARIABLES:
- NitrogenUptakeResponse:
  - total_uptake: Total nitrogen uptake (g N/day)
  - uptake_by_form: Uptake by nitrogen form (g N/day)
  - uptake_rate_by_form: Uptake rates (g N/g root/day)
  - root_activity: Uptake per unit root mass (g N/g root/day)
  - uptake_efficiency: Efficiency relative to maximum (dimensionless)
  - limiting_factors: List of limiting factors
- NitrogenAllocationResponse:
  - allocated_by_organ: Nitrogen allocated to each organ (g N/day)
  - allocation_efficiency: Fraction of demand met (dimensionless)
  - nitrogen_demand: Demand by organ (g N/day)
  - demand_satisfaction: Fraction of demand satisfied per organ (dimensionless)
  - growth_limitation: Growth limitation due to nitrogen (dimensionless)
- NitrogenBalanceResponse:
  - uptake_response: NitrogenUptakeResponse object
  - allocation_response: NitrogenAllocationResponse object
  - organ_states: Current organ nitrogen states
  - total_plant_nitrogen: Total nitrogen in plant (g N)
  - nitrogen_use_efficiency: Biomass per unit nitrogen (g biomass/g N)
  - nitrogen_stress_level: Overall stress level (0-1)
  - remobilized_nitrogen: Remobilized nitrogen (g N/day)
  - nitrogen_balance: Net nitrogen balance (g N/day)
  - mass_balance_error: Mass balance discrepancy (g N/day)
  - total_n_input: Total nitrogen input (g N/day)
  - total_allocated: Total nitrogen allocated (g N/day)
  - estimated_losses: Estimated nitrogen losses (g N/day)
  - storage_change: Change in storage nitrogen (g N/day)

FUNCTION EXPLANATIONS FOR NON-CODERS:
This model manages how plants absorb, distribute, and recycle nitrogen, a key nutrient for growth. It’s like a nutrition plan for plants, ensuring they get the right amount of nitrogen at the right time.

1. calculate_nitrogen_uptake:
   - Calculates how much nitrogen roots absorb from the nutrient solution using Michaelis-Menten kinetics: uptake = (vmax * concentration) / (km + concentration).
   - Like how your body absorbs nutrients from food, roots have a maximum absorption rate that depends on nutrient availability and environmental conditions.

2. calculate_nitrogen_demand:
   - Determines how much nitrogen each plant part (leaves, stems, roots, reproductive) needs for growth: demand = growth_rate * target_concentration * environmental_modifier.
   - Growing tissues need nitrogen like a growing child needs protein—more for fast-growing parts like young leaves.

3. allocate_nitrogen:
   - Distributes available nitrogen to plant parts based on their needs and priorities: allocation = available_n * (priority * demand) / total_weighted_demand.
   - Like budgeting limited money, priority organs (e.g., young leaves) get nitrogen first.

4. calculate_nitrogen_remobilization:
   - Calculates nitrogen recycled from old or stressed tissues to support new growth.
   - Like your body breaking down muscle for energy during fasting, plants recycle nitrogen from old leaves when stressed.

5. calculate_nitrogen_stress_level:
   - Assesses plant nitrogen stress based on tissue concentrations, weighted by organ importance.
   - Like a health checkup, it evaluates how nitrogen-deficient the plant is, with leaves being most critical.

6. update_nitrogen_pools:
   - Tracks nitrogen in different pools (structural, metabolic, storage, transport) within each organ.
   - Like managing different bank accounts: some nitrogen is locked in structures, some is ready for use, and some is in transit.

PRACTICAL APPLICATIONS:
- Optimize nutrient solutions for efficient nitrogen uptake.
- Predict and prevent nitrogen deficiencies.
- Time nitrogen applications based on plant growth stages.
- Minimize nitrogen waste in hydroponic systems.
- Diagnose nutrient issues for better crop management.
"""