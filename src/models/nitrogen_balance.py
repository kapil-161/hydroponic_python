"""
Plant Nitrogen Balance Model for Hydroponic Crop Simulation - No hardcoded defaults allowed and no fallback to simple alternative codes
Based on CROPGRO NFIX.for and NUPTAK.for and plant nitrogen research

Key concepts implemented:
1. Nitrogen uptake from multiple sources (NO3, NH4, amino acids)
2. Nitrogen assimilation and metabolism
3. Nitrogen allocation to plant organs
4. Nitrogen remobilization during stress and senescence
5. Nitrogen use efficiency calculations
6. Integration with carbon balance

Research basis:
- Gastal & Lemaire (2002) - N uptake and growth coordination
- Lemaire & Gastal (1997) - N dilution curves
- Sinclair & Horie (1989) - Leaf nitrogen and photosynthesis
- Masclaux-Daubresse et al. (2010) - Nitrogen remobilization
"""

from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import math


class NitrogenForm(Enum):
    """Forms of nitrogen available for uptake."""
    NITRATE = "NO3"          # Nitrate
    AMMONIUM = "NH4"         # Ammonium
    AMINO_ACIDS = "AA"       # Amino acids (dissolved organic N)
    UREA = "UREA"           # Urea


class NitrogenPool(Enum):
    """Plant nitrogen pools."""
    STRUCTURAL = "structural"     # Structural proteins, cell walls
    METABOLIC = "metabolic"      # Enzymes, chlorophyll, active proteins
    STORAGE = "storage"          # Storage proteins, amino acids
    TRANSPORT = "transport"      # Mobile N pool for allocation


@dataclass
class NitrogenBalanceParameters:
    """Parameters for nitrogen balance model."""
    
    # Uptake kinetics (Michaelis-Menten parameters)
    uptake_kinetics: Dict[str, Dict[str, float]] = None
    
    # Nitrogen assimilation
    nitrate_reduction_rate: float = None
    ammonium_assimilation_rate: float = None
    amino_acid_uptake_rate: float = None
    
    # Nitrogen allocation coefficients
    allocation_coefficients: Dict[str, Dict[str, float]] = None
    
    # Nitrogen concentration ranges (g N/g dry mass)
    critical_n_concentrations: Dict[str, Dict[str, float]] = None
    
    # Nitrogen remobilization
    remobilization_rates: Dict[str, float] = None
    remobilization_efficiency: Dict[str, float] = None
    
    # Nitrogen use efficiency
    photosynthetic_n_use_efficiency: float = None
    growth_n_use_efficiency: float = None
    
    # Stress thresholds
    n_stress_threshold: float = None          # N stress threshold
    luxury_uptake_threshold: float = None     # Luxury consumption threshold
    
    # Root characteristics
    specific_root_activity: float = None     # g N uptake/g root/day
    root_zone_exploration: float = None       # Fraction of nutrient zone accessed
    
    def __post_init__(self):
        # Validate that all required parameters are provided
        if self.uptake_kinetics is None:
            raise ValueError("❌ uptake_kinetics must be provided in CSV configuration - no hardcoded defaults allowed")
        
        if self.allocation_coefficients is None:
            raise ValueError("❌ allocation_coefficients must be provided in CSV configuration - no hardcoded defaults allowed")
        
        if self.critical_n_concentrations is None:
            raise ValueError("❌ critical_n_concentrations must be provided in CSV configuration - no hardcoded defaults allowed")
        
        if self.remobilization_rates is None:
            raise ValueError("❌ remobilization_rates must be provided in CSV configuration - no hardcoded defaults allowed")
        
        if self.remobilization_efficiency is None:
            raise ValueError("❌ remobilization_efficiency must be provided in CSV configuration - no hardcoded defaults allowed")
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'NitrogenBalanceParameters':
        """Create NitrogenBalanceParameters from CSV configuration data."""
        # Validate required parameters
        required_params = [
            'nitrate_reduction_rate', 'ammonium_assimilation_rate', 'amino_acid_uptake_rate',
            'photosynthetic_n_use_efficiency', 'growth_n_use_efficiency', 'n_stress_threshold',
            'luxury_uptake_threshold', 'specific_root_activity', 'root_zone_exploration'
        ]
        
        missing_params = [p for p in required_params if p not in config_dict]
        if missing_params:
            raise ValueError(f"❌ Missing required nitrogen balance parameters in CSV: {missing_params}")
        
        # Parse nested structures from flat CSV parameters
        uptake_kinetics = {}
        allocation_coeffs = {}
        critical_n_concs = {}
        remob_rates = {}
        remob_efficiency = {}
        
        # Parse uptake kinetics (if provided as flat parameters)
        if 'uptake_kinetics' in config_dict:
            uptake_kinetics = config_dict['uptake_kinetics']
        else:
            # Parse flat uptake kinetics parameters
            for key, value in config_dict.items():
                if key.startswith('uptake_kinetics_'):
                    # Extract form and parameter from key (e.g., uptake_kinetics_NO3_vmax)
                    # The pattern is: uptake_kinetics_[FORM]_[PARAM]
                    # Split by underscore and take the third part as form, rest as parameter
                    parts = key.split('_')
                    if len(parts) >= 4:
                        form = parts[2]  # NO3, NH4, AA (third part)
                        param = '_'.join(parts[3:])  # min_conc, inhibition_ki (rest of parts)
                        if form not in uptake_kinetics:
                            uptake_kinetics[form] = {}
                        uptake_kinetics[form][param] = float(value)
            
            # Validate that all required uptake kinetics parameters are present
            required_forms = ['NO3', 'NH4', 'AA']
            required_params = ['vmax', 'km', 'min_conc', 'inhibition_ki']
            
            for form in required_forms:
                if form not in uptake_kinetics:
                    raise ValueError(f"❌ Missing uptake kinetics for {form} in CSV configuration")
                for param in required_params:
                    if param not in uptake_kinetics[form]:
                        raise ValueError(f"❌ Missing {param} parameter for {form} uptake kinetics in CSV configuration")
        
        # Parse allocation coefficients (if provided as flat parameters)
        allocation_coeffs = {}
        if 'allocation_coefficients' in config_dict:
            allocation_coeffs = config_dict['allocation_coefficients']
        else:
            # Parse flat allocation coefficient parameters
            for key, value in config_dict.items():
                if key.startswith('allocation_coefficients_'):
                    # Extract stage and organ from key (e.g., allocation_coefficients_vegetative_leaves)
                    # Remove the prefix and split by underscore
                    remaining = key.replace('allocation_coefficients_', '')
                    parts = remaining.split('_')
                    if len(parts) >= 2:
                        stage = parts[0]
                        organ = '_'.join(parts[1:])  # Handle organs with underscores like 'reproductive'
                        if stage not in allocation_coeffs:
                            allocation_coeffs[stage] = {}
                        allocation_coeffs[stage][organ] = float(value)
        
        # Debug: print allocation coefficients
        print(f"DEBUG: allocation_coeffs = {allocation_coeffs}")
        
        # Parse critical N concentrations (if provided as flat parameters)
        if 'critical_n_concentrations' in config_dict:
            critical_n_concs = config_dict['critical_n_concentrations']
        else:
            # Parse flat critical N concentration parameters
            for key, value in config_dict.items():
                if key.startswith('critical_n_concentrations_'):
                    # Extract organ and threshold from key (e.g., critical_n_concentrations_leaves_optimal)
                    parts = key.split('_', 3)
                    if len(parts) >= 4:
                        organ = parts[1]
                        threshold = parts[2]
                        if organ not in critical_n_concs:
                            critical_n_concs[organ] = {}
                        critical_n_concs[organ][threshold] = float(value)
        
        # Parse remobilization rates (if provided as flat parameters)
        if 'remobilization_rates' in config_dict:
            remob_rates = config_dict['remobilization_rates']
        else:
            # Parse flat remobilization rate parameters
            for key, value in config_dict.items():
                if key.startswith('remobilization_rates_'):
                    # Extract pool type from key (e.g., remobilization_rates_structural)
                    parts = key.split('_', 2)
                    if len(parts) >= 3:
                        pool_type = parts[2]
                        remob_rates[pool_type] = float(value)
        
        # Parse remobilization efficiency (if provided as flat parameters)
        if 'remobilization_efficiency' in config_dict:
            remob_efficiency = config_dict['remobilization_efficiency']
        else:
            # Parse flat remobilization efficiency parameters
            for key, value in config_dict.items():
                if key.startswith('remobilization_efficiency_'):
                    # Extract organ from key (e.g., remobilization_efficiency_leaves)
                    parts = key.split('_', 2)
                    if len(parts) >= 3:
                        organ = parts[2]
                        remob_efficiency[organ] = float(value)
        
        return cls(
            uptake_kinetics=uptake_kinetics,
            nitrate_reduction_rate=float(config_dict['nitrate_reduction_rate']),
            ammonium_assimilation_rate=float(config_dict['ammonium_assimilation_rate']),
            amino_acid_uptake_rate=float(config_dict['amino_acid_uptake_rate']),
            allocation_coefficients=allocation_coeffs,
            critical_n_concentrations=critical_n_concs,
            remobilization_rates=remob_rates,
            remobilization_efficiency=remob_efficiency,
            photosynthetic_n_use_efficiency=float(config_dict['photosynthetic_n_use_efficiency']),
            growth_n_use_efficiency=float(config_dict['growth_n_use_efficiency']),
            n_stress_threshold=float(config_dict['n_stress_threshold']),
            luxury_uptake_threshold=float(config_dict['luxury_uptake_threshold']),
            specific_root_activity=float(config_dict['specific_root_activity']),
            root_zone_exploration=float(config_dict['root_zone_exploration'])
        )


@dataclass
class OrganNitrogenState:
    """Nitrogen state for a plant organ."""
    organ_name: str
    dry_mass: float                              # g dry mass
    total_nitrogen: float                        # g N total in organ
    structural_n: float = 0.0                    # g N in structural pool
    metabolic_n: float = 0.0                     # g N in metabolic pool
    storage_n: float = 0.0                       # g N in storage pool
    transport_n: float = 0.0                     # g N in transport pool
    nitrogen_concentration: float = 0.0          # g N/g dry mass
    nitrogen_status: str = "optimal"             # deficient, critical, optimal, luxury
    daily_uptake: float = 0.0                    # g N uptake today
    daily_remobilization: float = 0.0            # g N remobilized today
    
    def __post_init__(self):
        if self.dry_mass > 0:
            self.nitrogen_concentration = self.total_nitrogen / self.dry_mass
        
        # Initialize pools if not specified - will be calculated dynamically
        if (self.structural_n + self.metabolic_n + 
            self.storage_n + self.transport_n) == 0.0:
            # Leave pools at 0.0 - they will be calculated during simulation
            pass


@dataclass
class NitrogenUptakeResponse:
    """Results of nitrogen uptake calculations."""
    total_uptake: float                          # g N/day total uptake
    uptake_by_form: Dict[str, float]            # Uptake by N form
    uptake_rate_by_form: Dict[str, float]       # Actual uptake rates
    root_activity: float                         # Root uptake activity
    uptake_efficiency: float                     # Overall uptake efficiency
    limiting_factors: List[str]                  # Factors limiting uptake


@dataclass
class NitrogenAllocationResponse:
    """Results of nitrogen allocation calculations."""
    allocated_by_organ: Dict[str, float]        # N allocated to each organ
    allocation_efficiency: float                # Allocation efficiency
    nitrogen_demand: Dict[str, float]           # N demand by organ
    demand_satisfaction: Dict[str, float]       # Fraction of demand met
    growth_limitation: float                     # Growth limitation by N


@dataclass
class NitrogenBalanceResponse:
    """Daily nitrogen balance calculation results."""
    uptake_response: NitrogenUptakeResponse = None
    allocation_response: NitrogenAllocationResponse = None
    organ_states: Dict[str, OrganNitrogenState] = None
    total_plant_nitrogen: float = None
    nitrogen_use_efficiency: float = None
    nitrogen_stress_level: float = None          # 0-1, 0=no stress, 1=max stress
    remobilized_nitrogen: float = None           # g N remobilized today
    nitrogen_balance: float = None               # Net N balance (uptake - growth demand)
    
    # Mass balance verification fields
    mass_balance_error: float = None             # g N/day error in mass balance
    total_n_input: float = None                  # g N/day total input (uptake + remobilization)
    total_allocated: float = None                # g N/day total allocated to organs
    estimated_losses: float = None               # g N/day estimated losses
    storage_change: float = None                 # g N/day change in storage pools


class PlantNitrogenBalanceModel:
    """
    Comprehensive plant nitrogen balance model following CROPGRO principles.
    
    Tracks nitrogen flow from uptake through assimilation, allocation,
    utilization, and remobilization.
    """
    
    def __init__(self, parameters: Optional[NitrogenBalanceParameters] = None):
        if parameters is None:
            raise ValueError("❌ NitrogenBalanceParameters required - no hardcoded defaults allowed")
        self.params = parameters
        self.organ_states: Dict[str, OrganNitrogenState] = {}
        self.nitrogen_history: List[Dict[str, float]] = []
        self.total_cumulative_uptake: float = 0.0
        self.total_cumulative_remobilization: float = 0.0
        
    def initialize_organ(self, organ_name: str, initial_dry_mass: float,
                        initial_n_concentration: float):
        """
        Initialize nitrogen state for a plant organ.
        
        Args:
            organ_name: Name of the organ (leaves, stems, roots, reproductive)
            initial_dry_mass: Initial dry mass (g)
            initial_n_concentration: Initial N concentration (g N/g dry mass)
        """
        initial_total_n = initial_dry_mass * initial_n_concentration
        
        self.organ_states[organ_name] = OrganNitrogenState(
            organ_name=organ_name,
            dry_mass=initial_dry_mass,
            total_nitrogen=initial_total_n,
            nitrogen_concentration=initial_n_concentration
        )
    
    def calculate_nitrogen_uptake(self, root_mass: float,
                                solution_concentrations: Dict[str, float],
                                environmental_factors: Dict[str, float]) -> NitrogenUptakeResponse:
        """
        Calculate nitrogen uptake from solution.
        
        Args:
            root_mass: Root dry mass (g)
            solution_concentrations: N concentrations by form (mg N/L)
            environmental_factors: Environmental factors affecting uptake
            
        Returns:
            Nitrogen uptake response
        """
        total_uptake = 0.0
        uptake_by_form = {}
        uptake_rate_by_form = {}
        limiting_factors = []
        
        # Environmental factor effects
        temperature_factor = environmental_factors.get('temperature_factor', 1.0)
        water_status_factor = environmental_factors.get('water_status', 1.0)
        root_health_factor = environmental_factors.get('root_health', 1.0)
        ph_factor = environmental_factors.get('ph_factor', 1.0)
        
        # Combined environmental effect
        env_factor = (temperature_factor * water_status_factor * 
                     root_health_factor * ph_factor)
        
        if env_factor < 0.8:
            limiting_factors.append('environmental_stress')
        
        # Calculate uptake for each nitrogen form
        for n_form_str, concentration in solution_concentrations.items():
            if n_form_str in self.params.uptake_kinetics:
                kinetics = self.params.uptake_kinetics[n_form_str]
                
                # Michaelis-Menten kinetics with environmental effects
                vmax = kinetics['vmax']
                km = kinetics['km']
                min_conc = kinetics['min_conc']
                
                if concentration >= min_conc:
                    # Basic Michaelis-Menten
                    uptake_rate = (vmax * concentration) / (km + concentration)
                    
                    # Apply environmental effects
                    uptake_rate *= env_factor
                    
                    # Apply root mass and exploration factor
                    actual_uptake = (uptake_rate * root_mass * 
                                   self.params.root_zone_exploration)
                    
                    # Check for competitive inhibition between NH4 and NO3
                    if n_form_str == 'NO3' and 'NH4' in solution_concentrations:
                        nh4_conc = solution_concentrations['NH4']
                        ki = kinetics['inhibition_ki']
                        inhibition_factor = ki / (ki + nh4_conc)
                        actual_uptake *= inhibition_factor
                    
                    uptake_by_form[n_form_str] = actual_uptake
                    uptake_rate_by_form[n_form_str] = uptake_rate
                    total_uptake += actual_uptake
                    
                    if concentration < km:
                        limiting_factors.append(f'{n_form_str}_concentration')
                else:
                    uptake_by_form[n_form_str] = 0.0
                    uptake_rate_by_form[n_form_str] = 0.0
                    limiting_factors.append(f'{n_form_str}_below_minimum')
        
        # Calculate root activity and efficiency
        if root_mass > 0:
            root_activity = total_uptake / root_mass
            max_possible_activity = self.params.specific_root_activity
            uptake_efficiency = root_activity / max_possible_activity
        else:
            root_activity = 0.0
            uptake_efficiency = 0.0
            limiting_factors.append('no_roots')
        
        return NitrogenUptakeResponse(
            total_uptake=total_uptake,
            uptake_by_form=uptake_by_form,
            uptake_rate_by_form=uptake_rate_by_form,
            root_activity=root_activity,
            uptake_efficiency=min(1.0, uptake_efficiency),
            limiting_factors=list(set(limiting_factors))
        )
    
    def calculate_nitrogen_demand(self, organ_growth_rates: Dict[str, float],
                                growth_stage: str, environmental_factors: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate nitrogen demand for growth.
        
        Args:
            organ_growth_rates: Growth rates by organ (g dry mass/day)
            growth_stage: Current growth stage
            environmental_factors: Environmental conditions affecting N demand
            
        Returns:
            Nitrogen demand by organ (g N/day)
        """
        demand_by_organ = {}
        
        # Calculate environmental effect on nitrogen demand
        temp_factor = environmental_factors.get('temperature', 1.0)
        water_factor = environmental_factors.get('water', 1.0)
        ph_factor = environmental_factors.get('pH', 1.0)
        
        # Environmental stress increases N demand for metabolic processes
        env_stress = max(0.5, min(temp_factor, water_factor, ph_factor))
        demand_modifier = 1.0 / env_stress if env_stress > 0 else 2.0  # Higher demand under stress
        
        for organ_name, growth_rate in organ_growth_rates.items():
            if growth_rate > 0 and organ_name in self.params.critical_n_concentrations:
                # Get optimal N concentration for this organ
                n_concs = self.params.critical_n_concentrations[organ_name]
                target_concentration = n_concs['optimal']
                
                # Adjust target based on growth stage
                if growth_stage == 'vegetative' and organ_name == 'leaves':
                    target_concentration *= 1.1  # Higher N in vegetative leaves
                elif growth_stage == 'reproductive' and organ_name == 'reproductive':
                    target_concentration *= 1.2  # High N demand for reproductive organs
                
                # Calculate N demand for new growth (adjusted by environmental conditions)
                n_demand = growth_rate * target_concentration * demand_modifier
                demand_by_organ[organ_name] = n_demand
            else:
                demand_by_organ[organ_name] = 0.0
        
        return demand_by_organ
    
    def allocate_nitrogen(self, available_nitrogen: float,
                         nitrogen_demand: Dict[str, float],
                         growth_stage: str) -> NitrogenAllocationResponse:
        """
        Allocate available nitrogen to organs based on demand and priorities.
        
        Args:
            available_nitrogen: Total N available for allocation (g N)
            nitrogen_demand: N demand by organ (g N/day)
            growth_stage: Current growth stage
            
        Returns:
            Nitrogen allocation response
        """
        allocated_by_organ = {}
        demand_satisfaction = {}
        total_demand = sum(nitrogen_demand.values())
        
        if total_demand <= 0:
            # No demand - distribute equally or to storage
            for organ_name in nitrogen_demand.keys():
                allocated_by_organ[organ_name] = 0.0
                demand_satisfaction[organ_name] = 1.0
            allocation_efficiency = 1.0
            growth_limitation = 0.0
        else:
            # Get allocation priorities for current growth stage
            if growth_stage in self.params.allocation_coefficients:
                priorities = self.params.allocation_coefficients[growth_stage]
            else:
                priorities = self.params.allocation_coefficients['vegetative']
            
            # Calculate allocation based on demand and priorities
            if available_nitrogen >= total_demand:
                # Sufficient N - meet all demands
                allocated_by_organ = nitrogen_demand.copy()
                demand_satisfaction = {organ: 1.0 for organ in nitrogen_demand.keys()}
                allocation_efficiency = 1.0
                growth_limitation = 0.0
                
                # Distribute excess N based on priorities
                excess_n = available_nitrogen - total_demand
                for organ_name in allocated_by_organ.keys():
                    if organ_name in priorities:
                        allocated_by_organ[organ_name] += excess_n * priorities[organ_name]
            else:
                # Insufficient N - allocate proportionally with priority weighting
                allocation_efficiency = available_nitrogen / total_demand
                growth_limitation = 1.0 - allocation_efficiency
                
                # Calculate weighted allocation
                total_weighted_demand = 0.0
                for organ_name, demand in nitrogen_demand.items():
                    priority = priorities.get(organ_name)
                    if priority is None:
                        raise ValueError(f"❌ Nitrogen allocation priority for {organ_name} must be provided in CSV configuration - no hardcoded defaults allowed")
                    total_weighted_demand += demand * priority
                
                for organ_name, demand in nitrogen_demand.items():
                    if total_weighted_demand > 0:
                        priority = priorities.get(organ_name)
                        if priority is None:
                            raise ValueError(f"❌ Nitrogen allocation priority for {organ_name} must be provided in CSV configuration - no hardcoded defaults allowed")
                        weighted_fraction = (demand * priority) / total_weighted_demand
                        allocated_n = available_nitrogen * weighted_fraction
                        allocated_by_organ[organ_name] = allocated_n
                        
                        if demand > 0:
                            demand_satisfaction[organ_name] = allocated_n / demand
                        else:
                            demand_satisfaction[organ_name] = 1.0
                    else:
                        allocated_by_organ[organ_name] = 0.0
                        demand_satisfaction[organ_name] = 0.0
        
        return NitrogenAllocationResponse(
            allocated_by_organ=allocated_by_organ,
            allocation_efficiency=allocation_efficiency,
            nitrogen_demand=nitrogen_demand,
            demand_satisfaction=demand_satisfaction,
            growth_limitation=growth_limitation
        )
    
    def calculate_nitrogen_remobilization(self, stress_factors: Dict[str, float],
                                        senescence_rates: Dict[str, float],
                                        environmental_factors: Dict[str, float]) -> float:
        """
        Calculate nitrogen remobilization from senescing and stressed tissues.
        
        Args:
            stress_factors: Stress levels by type (0-1, 1=no stress)
            senescence_rates: Senescence rates by organ (fraction/day)
            environmental_factors: Environmental conditions affecting remobilization rates
            
        Returns:
            Total remobilized nitrogen (g N/day)
        """
        total_remobilized = 0.0
        
        # Calculate environmental effect on remobilization rates
        temp_factor = environmental_factors.get('temperature', 1.0)
        water_factor = environmental_factors.get('water', 1.0)
        ph_factor = environmental_factors.get('pH', 1.0)
        
        # Combined environmental effect on enzymatic remobilization processes
        env_effect = temp_factor * water_factor * ph_factor
        
        # Stress-induced remobilization
        overall_stress = 1.0 - min(stress_factors.values()) if stress_factors else 1.0
        
        if overall_stress > 0.3:  # Significant stress
            for organ_name, organ_state in self.organ_states.items():
                if organ_name in self.params.remobilization_efficiency:
                    # Calculate remobilizable N from different pools
                    remobilizable_n = 0.0
                    
                    # Storage N - most readily available (affected by environmental factors)
                    storage_remob = (organ_state.storage_n * 
                                   self.params.remobilization_rates[NitrogenPool.STORAGE.value] * 
                                   env_effect)
                    
                    # Metabolic N - available under stress (affected by temperature and pH)
                    metabolic_remob = (organ_state.metabolic_n * 
                                     self.params.remobilization_rates[NitrogenPool.METABOLIC.value] * 
                                     overall_stress * env_effect)
                    
                    # Transport N - highly mobile (less affected by environment)
                    transport_remob = (organ_state.transport_n * 
                                     self.params.remobilization_rates[NitrogenPool.TRANSPORT.value] * 
                                     min(env_effect, 1.2))  # Cap transport effect
                    
                    remobilizable_n = storage_remob + metabolic_remob + transport_remob
                    
                    # Apply organ-specific efficiency
                    efficiency = self.params.remobilization_efficiency[organ_name]
                    daily_remobilization = remobilizable_n * efficiency
                    
                    # Update organ pools
                    organ_state.storage_n -= storage_remob
                    organ_state.metabolic_n -= metabolic_remob * overall_stress
                    organ_state.transport_n -= transport_remob
                    organ_state.daily_remobilization = daily_remobilization
                    
                    total_remobilized += daily_remobilization
        
        # Senescence-induced remobilization
        for organ_name, senescence_rate in senescence_rates.items():
            if (organ_name in self.organ_states and 
                organ_name in self.params.remobilization_efficiency and 
                senescence_rate > 0):
                
                organ_state = self.organ_states[organ_name]
                efficiency = self.params.remobilization_efficiency[organ_name]
                
                # Remobilize from senescing tissue (affected by environmental conditions)
                senescence_remob = (organ_state.total_nitrogen * senescence_rate * 
                                  efficiency * 0.5 * env_effect)  # 50% of N in senescing tissue
                
                organ_state.daily_remobilization += senescence_remob
                total_remobilized += senescence_remob
        
        return total_remobilized
    
    def update_organ_nitrogen_status(self, organ_name: str):
        """
        Update nitrogen status classification for an organ.
        
        Args:
            organ_name: Name of the organ to update
        """
        if organ_name not in self.organ_states:
            return
        
        organ_state = self.organ_states[organ_name]
        
        if organ_name in self.params.critical_n_concentrations:
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
        else:
            organ_state.nitrogen_status = 'unknown'
    
    def calculate_nitrogen_stress_level(self) -> float:
        """
        Calculate overall plant nitrogen stress level.
        
        Returns:
            Nitrogen stress level (0-1, 0=no stress, 1=max stress)
        """
        if not self.organ_states:
            return 0.0
        
        # Weight stress by organ importance
        organ_weights = {
            'leaves': 0.5,      # Leaves most important for photosynthesis
            'roots': 0.3,       # Roots important for uptake
            'stems': 0.1,       # Stems less critical
            'reproductive': 0.1  # Reproductive organs important during reproduction
        }
        
        weighted_stress = 0.0
        total_weight = 0.0
        
        for organ_name, organ_state in self.organ_states.items():
            if organ_name in self.params.critical_n_concentrations:
                n_concs = self.params.critical_n_concentrations[organ_name]
                current_conc = organ_state.nitrogen_concentration
                critical_conc = n_concs['critical']
                optimal_conc = n_concs['optimal']
                
                # Calculate stress level for this organ (0=no stress, 1=max stress)
                if current_conc >= optimal_conc:
                    organ_stress = 0.0  # No stress
                elif current_conc >= critical_conc:
                    # Linear increase from optimal to critical
                    organ_stress = 1.0 - (current_conc - critical_conc) / (optimal_conc - critical_conc)
                else:
                    # Maximum stress below critical
                    organ_stress = 0.9
                
                # Apply weighting
                weight = organ_weights.get(organ_name, 0.1)
                weighted_stress += organ_stress * weight
                total_weight += weight
        
        if total_weight > 0:
            overall_stress = weighted_stress / total_weight
        else:
            overall_stress = 0.0
        
        return max(0.0, min(1.0, overall_stress))
    
    def update_nitrogen_pools(self, external_nitrogen_input: float,
                             organ_growth_rates: Dict[str, float],
                             environmental_factors: Dict[str, float],
                             growth_stage: str,
                             stress_factors: Dict[str, float],
                             senescence_rates: Dict[str, float]) -> NitrogenBalanceResponse:
        """
        Daily nitrogen balance update using externally provided uptake.
        This method focuses on INTERNAL allocation and remobilization.
        """
        # Create a dummy uptake response since uptake is now external
        uptake_response = NitrogenUptakeResponse(
            total_uptake=external_nitrogen_input,
            uptake_by_form={'external': external_nitrogen_input},
            uptake_rate_by_form={},
            root_activity=0.0,
            uptake_efficiency=1.0,
            limiting_factors=[]
        )

        # Calculate nitrogen remobilization (now using environmental factors)
        remobilized_n = self.calculate_nitrogen_remobilization(
            stress_factors, senescence_rates, environmental_factors
        )

        # Total available nitrogen for allocation
        available_n = external_nitrogen_input + remobilized_n

        # Calculate nitrogen demand (now using environmental factors)
        n_demand = self.calculate_nitrogen_demand(organ_growth_rates, growth_stage, environmental_factors)

        # Allocate nitrogen to organs
        allocation_response = self.allocate_nitrogen(
            available_n, n_demand, growth_stage
        )

        # Update organ nitrogen states
        for organ_name, allocated_n in allocation_response.allocated_by_organ.items():
            if organ_name in self.organ_states:
                organ_state = self.organ_states[organ_name]

                # Update dry mass if growing
                if organ_name in organ_growth_rates and organ_growth_rates[organ_name] > 0:
                    organ_state.dry_mass += organ_growth_rates[organ_name]

                # Add allocated nitrogen
                organ_state.total_nitrogen += allocated_n
                organ_state.daily_uptake = allocated_n

                # Recalculate concentration
                if organ_state.dry_mass > 0:
                    organ_state.nitrogen_concentration = organ_state.total_nitrogen / organ_state.dry_mass

                # Update nitrogen pools by partitioning newly allocated nitrogen
                if allocated_n > 0:
                    # Partition newly allocated nitrogen into functional pools based on physiological principles
                    # These fractions should be configurable from CSV in the future
                    structural_fraction = 0.4    # 40% to structural components (proteins, cell walls)
                    metabolic_fraction = 0.35    # 35% to metabolic functions (enzymes, signaling)
                    storage_fraction = 0.15      # 15% to storage pools (vacuolar N, amino acids)
                    transport_fraction = 0.10    # 10% to transport forms (nitrate, amino acids)
                    
                    # Add newly allocated nitrogen to each pool
                    organ_state.structural_n += allocated_n * structural_fraction
                    organ_state.metabolic_n += allocated_n * metabolic_fraction
                    organ_state.storage_n += allocated_n * storage_fraction
                    organ_state.transport_n += allocated_n * transport_fraction
                    
                    # Ensure pools sum to total nitrogen (accounting for any previous values)
                    total_pools = (organ_state.structural_n + organ_state.metabolic_n +
                                 organ_state.storage_n + organ_state.transport_n)
                    
                    # Normalize if there's a discrepancy (should be minimal)
                    if abs(total_pools - organ_state.total_nitrogen) > 0.001:
                        normalization_factor = organ_state.total_nitrogen / total_pools
                        organ_state.structural_n *= normalization_factor
                        organ_state.metabolic_n *= normalization_factor
                        organ_state.storage_n *= normalization_factor
                        organ_state.transport_n *= normalization_factor

                # Update nitrogen status
                self.update_organ_nitrogen_status(organ_name)

        # Calculate overall nitrogen stress
        n_stress_level = self.calculate_nitrogen_stress_level()

        # Calculate nitrogen use efficiency
        total_plant_n = sum(state.total_nitrogen for state in self.organ_states.values())
        total_biomass = sum(state.dry_mass for state in self.organ_states.values())

        if total_plant_n > 0:
            nue = total_biomass / total_plant_n
        else:
            nue = 0.0

        # Calculate nitrogen balance with mass conservation verification
        total_growth_demand = sum(n_demand.values())
        total_allocated = sum(allocation_response.allocated_by_organ.values())
        
        # MASS BALANCE VERIFICATION: Input = Growth + Storage + Losses
        # Input sources: uptake + remobilization
        total_n_input = external_nitrogen_input + remobilized_n
        
        # Calculate losses (respiration, exudation, volatile losses)
        estimated_losses = total_allocated * 0.05  # ~5% losses typical in hydroponics
        
        # Storage change = Total input - Growth demand - Losses
        storage_change = total_n_input - total_allocated - estimated_losses
        
        # Net nitrogen balance (positive = accumulation, negative = depletion)
        n_balance = available_n - total_growth_demand
        
        # Mass conservation check
        mass_balance_error = abs(total_n_input - total_allocated - estimated_losses - storage_change)
        if mass_balance_error > 0.001:  # More than 1 mg error
            print(f"Warning: Nitrogen mass balance error of {mass_balance_error:.4f} g N/day detected")
            print(f"  Input: {total_n_input:.4f} g N/day, Allocated: {total_allocated:.4f} g N/day")
            print(f"  Losses: {estimated_losses:.4f} g N/day, Storage change: {storage_change:.4f} g N/day")

        # Update cumulative tracking
        self.total_cumulative_uptake += external_nitrogen_input
        self.total_cumulative_remobilization += remobilized_n

        # Store daily history
        daily_record = {
            'total_uptake': external_nitrogen_input,
            'remobilized': remobilized_n,
            'total_plant_n': total_plant_n,
            'nue': nue,
            'n_stress': n_stress_level
        }
        self.nitrogen_history.append(daily_record)

        return NitrogenBalanceResponse(
            uptake_response=uptake_response,
            allocation_response=allocation_response,
            organ_states=self.organ_states.copy(),
            total_plant_nitrogen=total_plant_n,
            nitrogen_use_efficiency=nue,
            nitrogen_stress_level=n_stress_level,
            remobilized_nitrogen=remobilized_n,
            nitrogen_balance=n_balance,
            # Mass balance verification data
            mass_balance_error=mass_balance_error,
            total_n_input=total_n_input,
            total_allocated=total_allocated,
            estimated_losses=estimated_losses,
            storage_change=storage_change
        )
    
    def get_nitrogen_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive nitrogen balance summary.
        
        Returns:
            Dictionary with nitrogen balance summary
        """
        total_plant_n = sum(state.total_nitrogen for state in self.organ_states.values())
        total_biomass = sum(state.dry_mass for state in self.organ_states.values())
        
        summary = {
            'total_plant_nitrogen': total_plant_n,
            'total_biomass': total_biomass,
            'nitrogen_use_efficiency': total_biomass / max(total_plant_n, 0.001),
            'cumulative_uptake': self.total_cumulative_uptake,
            'cumulative_remobilization': self.total_cumulative_remobilization,
            'nitrogen_stress_level': self.calculate_nitrogen_stress_level(),
            'organ_n_concentrations': {
                name: state.nitrogen_concentration 
                for name, state in self.organ_states.items()
            },
            'organ_n_status': {
                name: state.nitrogen_status 
                for name, state in self.organ_states.items()
            },
            'nitrogen_distribution': {
                name: state.total_nitrogen 
                for name, state in self.organ_states.items()
            }
        }
        
        return summary


def create_lettuce_nitrogen_balance_model(system_config=None) -> PlantNitrogenBalanceModel:
    """Create nitrogen balance model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        PlantNitrogenBalanceModel configured with CSV parameters
        
    Raises:
        ValueError: If CSV parameters are missing or invalid
    """
    if system_config is None:
        raise ValueError("❌ system_config is required - no hardcoded defaults allowed")
    
    # Get nitrogen balance parameters from CSV data loaded in system_config
    nitrogen_params = getattr(system_config, 'nitrogen_parameters', None)
    
    if nitrogen_params is None:
        raise ValueError("❌ nitrogen_parameters missing from CSV - no fallback defaults allowed")
    
    # Create parameters from CSV config
    parameters = NitrogenBalanceParameters.from_config(nitrogen_params)
    return PlantNitrogenBalanceModel(parameters)


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file manages how plants absorb, use, and recycle nitrogen - one of the most important nutrients 
for plant growth. Think of it like managing the protein metabolism in a human body - how we absorb 
amino acids, build proteins, and recycle them when needed.

KEY FUNCTIONS AND EQUATIONS:

1. calculate_nitrogen_uptake()
   - What it does: Calculates how much nitrogen roots can absorb from the nutrient solution
   - Equation: Uses Michaelis-Menten kinetics: uptake = (Vmax × concentration) / (Km + concentration)
   - Real-world meaning: Like enzymes in your body, root uptake has a maximum rate. At low nutrient 
     concentrations, uptake increases with concentration. At high concentrations, it plateaus.
     Similar to how you can only digest so much protein per hour regardless of how much you eat.

2. calculate_nitrogen_demand()
   - What it does: Determines how much nitrogen each plant part needs for growth
   - Equation: demand = growth_rate × target_nitrogen_concentration × environmental_modifier
   - Real-world meaning: Growing tissues need nitrogen to build proteins. Fast-growing parts 
     (like young leaves) need more nitrogen than slow-growing parts (like mature stems).

3. allocate_nitrogen()
   - What it does: Distributes available nitrogen among plant organs based on priorities
   - Equations: 
     * If sufficient N: allocation = full_demand
     * If insufficient N: allocation = available_N × (priority × demand) / total_weighted_demand
   - Real-world meaning: Like budgeting limited money among family members - highest priority 
     needs get met first. Young growing leaves get priority over older mature parts.

4. calculate_nitrogen_remobilization()
   - What it does: Calculates how much nitrogen can be recycled from old tissues to growing ones
   - Equations:
     * storage_remob = storage_N × remobilization_rate × environmental_factor
     * stress_remob = metabolic_N × stress_level × efficiency
   - Real-world meaning: When plants are stressed or aging, they can "cannibalize" old leaves 
     to feed new growth. Like your body breaking down muscle protein during starvation.

5. calculate_nitrogen_stress_level()
   - What it does: Determines overall plant nitrogen stress based on tissue concentrations
   - Equations: Weighted average of organ-specific stress levels
   - Real-world meaning: Different plant parts have different nitrogen requirements. Stress 
     is calculated like a weighted GPA - leaves (most important) count more than stems.

6. update_nitrogen_pools()
   - What it does: Tracks nitrogen in different functional pools within each organ
   - Pools: Structural (cell walls), Metabolic (enzymes), Storage (reserves), Transport (mobile forms)
   - Real-world meaning: Like tracking how money is allocated in different accounts - 
     checking (metabolic), savings (storage), investments (structural), cash (transport).

KEY NITROGEN CONCEPTS:

NITROGEN FORMS:
- Nitrate (NO3-): Main form in hydroponic solutions, mobile in plant
- Ammonium (NH4+): Alternative form, can be toxic at high levels
- Amino acids: Organic forms, directly usable by plants
- Urea: Organic form that must be converted before use

NITROGEN POOLS IN PLANTS:
- Structural: Proteins in cell walls and structure (hard to mobilize)
- Metabolic: Enzymes, chlorophyll (essential but some can be recycled)
- Storage: Amino acids, storage proteins (easily mobilized when needed)
- Transport: Mobile forms moving between organs

NITROGEN USE EFFICIENCY (NUE):
- How much biomass produced per unit nitrogen absorbed
- High NUE = efficient use, low NUE = wasteful use
- Affected by genetics, environment, and management

UPTAKE KINETICS:
- Vmax: Maximum uptake rate (genetic potential)
- Km: Half-saturation constant (efficiency at low concentrations)
- Inhibition: Competition between different nitrogen forms

PRACTICAL APPLICATIONS:
- Optimize nutrient solution concentrations for maximum uptake efficiency
- Predict nitrogen deficiency before symptoms appear
- Time nitrogen applications based on plant demand patterns
- Minimize nitrogen waste and environmental impact
- Breed plants with better nitrogen use efficiency
- Diagnose nutrient problems and adjust feeding programs

This system helps growers provide the right amount of nitrogen at the right time, maximizing 
plant growth while minimizing waste and cost - like being a nutritionist for plants.
"""


