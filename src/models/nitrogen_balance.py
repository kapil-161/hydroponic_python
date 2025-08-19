"""
Plant Nitrogen Balance Model for Hydroponic Crop Simulation
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

import numpy as np
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
    nitrate_reduction_rate: float = 0.8      # Maximum NO3 reduction rate (g N/g root/day)
    ammonium_assimilation_rate: float = 1.2  # Maximum NH4 assimilation rate
    amino_acid_uptake_rate: float = 0.3      # Direct amino acid uptake rate
    
    # Nitrogen allocation coefficients
    allocation_coefficients: Dict[str, Dict[str, float]] = None
    
    # Nitrogen concentration ranges (g N/g dry mass)
    critical_n_concentrations: Dict[str, Dict[str, float]] = None
    
    # Nitrogen remobilization
    remobilization_rates: Dict[str, float] = None
    remobilization_efficiency: Dict[str, float] = None
    
    # Nitrogen use efficiency
    photosynthetic_n_use_efficiency: float = 36.0  # μmol CO2/μmol N/s
    growth_n_use_efficiency: float = 25.0          # g biomass/g N
    
    # Stress thresholds
    n_stress_threshold: float = 0.7          # N stress threshold
    luxury_uptake_threshold: float = 1.3     # Luxury consumption threshold
    
    # Root characteristics
    specific_root_activity: float = 0.05     # g N uptake/g root/day
    root_zone_exploration: float = 0.8       # Fraction of nutrient zone accessed
    
    def __post_init__(self):
        if self.uptake_kinetics is None:
            # Default Michaelis-Menten kinetics for each N form
            self.uptake_kinetics = {
                NitrogenForm.NITRATE.value: {
                    "vmax": 0.8,     # Maximum uptake rate (g N/g root/day)
                    "km": 20.0,      # Half-saturation constant (mg N/L)
                    "min_conc": 5.0, # Minimum effective concentration
                    "inhibition_ki": 100.0  # Competitive inhibition constant
                },
                NitrogenForm.AMMONIUM.value: {
                    "vmax": 1.2,
                    "km": 8.0,
                    "min_conc": 2.0,
                    "inhibition_ki": 50.0
                },
                NitrogenForm.AMINO_ACIDS.value: {
                    "vmax": 0.3,
                    "km": 5.0,
                    "min_conc": 1.0,
                    "inhibition_ki": 25.0
                },
                NitrogenForm.UREA.value: {
                    "vmax": 0.6,
                    "km": 15.0,
                    "min_conc": 3.0,
                    "inhibition_ki": 75.0
                }
            }
        
        if self.allocation_coefficients is None:
            # Allocation to different plant organs by growth stage
            self.allocation_coefficients = {
                "vegetative": {
                    "leaves": 0.60,      # High leaf allocation during vegetative growth
                    "stems": 0.20,
                    "roots": 0.20
                },
                "reproductive": {
                    "leaves": 0.40,
                    "stems": 0.15,
                    "roots": 0.15,
                    "reproductive": 0.30  # High allocation to reproductive organs
                },
                "senescence": {
                    "leaves": 0.20,
                    "stems": 0.10,
                    "roots": 0.30,
                    "reproductive": 0.40
                }
            }
        
        if self.critical_n_concentrations is None:
            # Critical N concentrations for different organs (g N/g dry mass)
            self.critical_n_concentrations = {
                "leaves": {
                    "minimum": 0.025,    # Below this = severe deficiency
                    "critical": 0.040,   # Critical concentration
                    "optimal": 0.055,    # Optimal concentration
                    "maximum": 0.070     # Above this = luxury consumption
                },
                "stems": {
                    "minimum": 0.008,
                    "critical": 0.015,
                    "optimal": 0.025,
                    "maximum": 0.035
                },
                "roots": {
                    "minimum": 0.012,
                    "critical": 0.020,
                    "optimal": 0.030,
                    "maximum": 0.045
                },
                "reproductive": {
                    "minimum": 0.015,
                    "critical": 0.025,
                    "optimal": 0.040,
                    "maximum": 0.055
                }
            }
        
        if self.remobilization_rates is None:
            # Daily remobilization rates from different pools (fraction/day)
            self.remobilization_rates = {
                NitrogenPool.STORAGE.value: 0.10,    # Storage N readily available
                NitrogenPool.METABOLIC.value: 0.05,  # Metabolic N less available
                NitrogenPool.STRUCTURAL.value: 0.01, # Structural N minimally available
                NitrogenPool.TRANSPORT.value: 0.20   # Transport pool highly mobile
            }
        
        if self.remobilization_efficiency is None:
            # Efficiency of N remobilization from different organs
            self.remobilization_efficiency = {
                "leaves": 0.75,       # High efficiency from leaves
                "stems": 0.45,        # Moderate from stems
                "roots": 0.35,        # Lower from roots
                "reproductive": 0.10  # Minimal from reproductive organs
            }
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'NitrogenBalanceParameters':
        """Create NitrogenBalanceParameters from configuration dictionary."""
        uptake_kinetics = config_dict.get('uptake_kinetics', {})
        allocation_coeffs = config_dict.get('allocation_coefficients', {})
        critical_n_concs = config_dict.get('critical_n_concentrations', {})
        remob_rates = config_dict.get('remobilization_rates', {})
        remob_efficiency = config_dict.get('remobilization_efficiency', {})
        
        return cls(
            uptake_kinetics=uptake_kinetics if uptake_kinetics else None,
            nitrate_reduction_rate=config_dict.get('nitrate_reduction_rate', 0.8),
            ammonium_assimilation_rate=config_dict.get('ammonium_assimilation_rate', 1.2),
            amino_acid_uptake_rate=config_dict.get('amino_acid_uptake_rate', 0.3),
            allocation_coefficients=allocation_coeffs if allocation_coeffs else None,
            critical_n_concentrations=critical_n_concs if critical_n_concs else None,
            remobilization_rates=remob_rates if remob_rates else None,
            remobilization_efficiency=remob_efficiency if remob_efficiency else None,
            photosynthetic_n_use_efficiency=config_dict.get('photosynthetic_n_use_efficiency', 36.0),
            growth_n_use_efficiency=config_dict.get('growth_n_use_efficiency', 25.0),
            n_stress_threshold=config_dict.get('n_stress_threshold', 0.7),
            luxury_uptake_threshold=config_dict.get('luxury_uptake_threshold', 1.3),
            specific_root_activity=config_dict.get('specific_root_activity', 0.05),
            root_zone_exploration=config_dict.get('root_zone_exploration', 0.8)
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
        
        # Distribute total N among pools if not specified
        if (self.structural_n + self.metabolic_n + 
            self.storage_n + self.transport_n) == 0.0:
            # Default distribution
            self.structural_n = self.total_nitrogen * 0.4   # 40% structural
            self.metabolic_n = self.total_nitrogen * 0.35   # 35% metabolic
            self.storage_n = self.total_nitrogen * 0.20     # 20% storage
            self.transport_n = self.total_nitrogen * 0.05   # 5% transport


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
    uptake_response: NitrogenUptakeResponse
    allocation_response: NitrogenAllocationResponse
    organ_states: Dict[str, OrganNitrogenState]
    total_plant_nitrogen: float
    nitrogen_use_efficiency: float
    nitrogen_stress_level: float                 # 0-1, 0=no stress, 1=max stress
    remobilized_nitrogen: float                  # g N remobilized today
    nitrogen_balance: float                      # Net N balance (uptake - growth demand)


class PlantNitrogenBalanceModel:
    """
    Comprehensive plant nitrogen balance model following CROPGRO principles.
    
    Tracks nitrogen flow from uptake through assimilation, allocation,
    utilization, and remobilization.
    """
    
    def __init__(self, parameters: Optional[NitrogenBalanceParameters] = None):
        self.params = parameters or NitrogenBalanceParameters()
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
                                growth_stage: str) -> Dict[str, float]:
        """
        Calculate nitrogen demand for growth.
        
        Args:
            organ_growth_rates: Growth rates by organ (g dry mass/day)
            growth_stage: Current growth stage
            
        Returns:
            Nitrogen demand by organ (g N/day)
        """
        demand_by_organ = {}
        
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
                
                # Calculate N demand for new growth
                n_demand = growth_rate * target_concentration
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
                    priority = priorities.get(organ_name, 0.25)  # Default priority
                    total_weighted_demand += demand * priority
                
                for organ_name, demand in nitrogen_demand.items():
                    if total_weighted_demand > 0:
                        priority = priorities.get(organ_name, 0.25)
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
                                        senescence_rates: Dict[str, float]) -> float:
        """
        Calculate nitrogen remobilization from senescing and stressed tissues.
        
        Args:
            stress_factors: Stress levels by type (0-1, 1=no stress)
            senescence_rates: Senescence rates by organ (fraction/day)
            
        Returns:
            Total remobilized nitrogen (g N/day)
        """
        total_remobilized = 0.0
        
        # Stress-induced remobilization
        overall_stress = 1.0 - min(stress_factors.values()) if stress_factors else 1.0
        
        if overall_stress > 0.3:  # Significant stress
            for organ_name, organ_state in self.organ_states.items():
                if organ_name in self.params.remobilization_efficiency:
                    # Calculate remobilizable N from different pools
                    remobilizable_n = 0.0
                    
                    # Storage N - most readily available
                    storage_remob = (organ_state.storage_n * 
                                   self.params.remobilization_rates[NitrogenPool.STORAGE.value])
                    
                    # Metabolic N - available under stress
                    metabolic_remob = (organ_state.metabolic_n * 
                                     self.params.remobilization_rates[NitrogenPool.METABOLIC.value] * 
                                     overall_stress)
                    
                    # Transport N - highly mobile
                    transport_remob = (organ_state.transport_n * 
                                     self.params.remobilization_rates[NitrogenPool.TRANSPORT.value])
                    
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
                
                # Remobilize from senescing tissue
                senescence_remob = (organ_state.total_nitrogen * senescence_rate * 
                                  efficiency * 0.5)  # 50% of N in senescing tissue
                
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
    
    def daily_update(self, root_mass: float,
                    solution_concentrations: Dict[str, float],
                    environmental_factors: Dict[str, float],
                    organ_growth_rates: Dict[str, float],
                    growth_stage: str,
                    stress_factors: Dict[str, float],
                    senescence_rates: Dict[str, float]) -> NitrogenBalanceResponse:
        """
        Daily nitrogen balance update.
        
        Args:
            root_mass: Root dry mass (g)
            solution_concentrations: N concentrations by form (mg N/L)
            environmental_factors: Environmental factors affecting processes
            organ_growth_rates: Growth rates by organ (g dry mass/day)
            growth_stage: Current growth stage
            stress_factors: Stress levels by type
            senescence_rates: Senescence rates by organ
            
        Returns:
            Complete nitrogen balance response
        """
        # Calculate nitrogen uptake
        uptake_response = self.calculate_nitrogen_uptake(
            root_mass, solution_concentrations, environmental_factors
        )
        
        # Calculate nitrogen remobilization
        remobilized_n = self.calculate_nitrogen_remobilization(
            stress_factors, senescence_rates
        )
        
        # Total available nitrogen for allocation
        available_n = uptake_response.total_uptake + remobilized_n
        
        # Calculate nitrogen demand
        n_demand = self.calculate_nitrogen_demand(organ_growth_rates, growth_stage)
        
        # Allocate nitrogen to organs
        allocation_response = self.allocate_nitrogen(
            available_n, n_demand, growth_stage
        )
        
        # Update organ nitrogen states
        for organ_name, allocated_n in allocation_response.allocated_by_organ.items():
            if organ_name in self.organ_states:
                organ_state = self.organ_states[organ_name]
                
                # Update dry mass if growing (do this first)
                if organ_name in organ_growth_rates and organ_growth_rates[organ_name] > 0:
                    organ_state.dry_mass += organ_growth_rates[organ_name]
                
                # Add allocated nitrogen
                organ_state.total_nitrogen += allocated_n
                organ_state.daily_uptake = allocated_n
                
                # Recalculate concentration
                if organ_state.dry_mass > 0:
                    organ_state.nitrogen_concentration = organ_state.total_nitrogen / organ_state.dry_mass
                
                # Update nitrogen pools proportionally
                if organ_state.total_nitrogen > 0:
                    # Maintain pool proportions
                    total_pools = (organ_state.structural_n + organ_state.metabolic_n + 
                                 organ_state.storage_n + organ_state.transport_n)
                    if total_pools > 0:
                        scale_factor = organ_state.total_nitrogen / total_pools
                        organ_state.structural_n *= scale_factor
                        organ_state.metabolic_n *= scale_factor
                        organ_state.storage_n *= scale_factor
                        organ_state.transport_n *= scale_factor
                
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
        
        # Calculate nitrogen balance
        total_growth_demand = sum(n_demand.values())
        n_balance = available_n - total_growth_demand
        
        # Update cumulative tracking
        self.total_cumulative_uptake += uptake_response.total_uptake
        self.total_cumulative_remobilization += remobilized_n
        
        # Store daily history
        daily_record = {
            'total_uptake': uptake_response.total_uptake,
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
            nitrogen_balance=n_balance
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


def create_lettuce_nitrogen_balance_model() -> PlantNitrogenBalanceModel:
    """Create nitrogen balance model with lettuce-specific parameters."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        nitrogen_config = config_loader.get_nitrogen_balance_parameters()
        parameters = NitrogenBalanceParameters.from_config(nitrogen_config)
        return PlantNitrogenBalanceModel(parameters)
    except ImportError:
        # Fallback to default values if config loader not available
        return PlantNitrogenBalanceModel()


def demonstrate_nitrogen_balance_model():
    """Demonstrate nitrogen balance model capabilities."""
    # Create model with reduced uptake rates for realistic demo
    params = NitrogenBalanceParameters()
    # Reduce uptake rates
    for n_form in params.uptake_kinetics:
        params.uptake_kinetics[n_form]['vmax'] *= 0.1  # Reduce by 90%
    
    model = PlantNitrogenBalanceModel(params)
    
    print("=" * 80)
    print("PLANT NITROGEN BALANCE MODEL DEMONSTRATION")
    print("=" * 80)
    
    # Initialize plant organs
    model.initialize_organ('leaves', 3.0, 0.045)     # 3g leaves, 4.5% N
    model.initialize_organ('stems', 1.0, 0.020)      # 1g stems, 2.0% N  
    model.initialize_organ('roots', 2.0, 0.025)      # 2g roots, 2.5% N
    
    print("Initial plant state:")
    for organ_name, state in model.organ_states.items():
        print(f"  {organ_name}: {state.dry_mass:.1f}g, {state.nitrogen_concentration*100:.1f}% N, {state.nitrogen_status}")
    
    # Simulate nitrogen balance over time
    print(f"\nSimulating nitrogen balance:")
    print(f"{'Day':<4} {'Uptake':<7} {'Remob':<6} {'LeafN%':<7} {'Stress':<7} {'NUE':<6} {'Balance':<8}")
    print("-" * 80)
    
    for day in range(1, 21):
        # Varying solution conditions (reduced concentrations)
        solution_concs = {
            'NO3': 150.0 + 20.0 * np.sin(day * 2 * np.pi / 10),  # mg N/L
            'NH4': 15.0 + 5.0 * np.sin(day * 2 * np.pi / 7),
            'AA': 3.0,
            'UREA': 5.0
        }
        
        # Environmental factors
        env_factors = {
            'temperature_factor': 0.9 + 0.1 * np.sin(day * 2 * np.pi / 5),
            'water_status': 0.95,
            'root_health': 0.9,
            'ph_factor': 0.95
        }
        
        # Growth rates (g/day) - increased to match N uptake
        if day < 15:  # Vegetative growth
            growth_rates = {'leaves': 0.5, 'stems': 0.2, 'roots': 0.3}
            growth_stage = 'vegetative'
        else:  # Slower growth, some stress
            growth_rates = {'leaves': 0.3, 'stems': 0.1, 'roots': 0.2}
            growth_stage = 'vegetative'
        
        # Stress levels
        stress_factors = {
            'water': 0.9,
            'temperature': 0.85 + 0.1 * np.sin(day * 2 * np.pi / 8),
            'light': 0.9
        }
        
        # Senescence rates (minimal for vegetative stage)
        senescence_rates = {'leaves': 0.001, 'stems': 0.0005, 'roots': 0.0002}
        
        # Get current root mass
        root_mass = model.organ_states['roots'].dry_mass
        
        # Daily update
        response = model.daily_update(
            root_mass=root_mass,
            solution_concentrations=solution_concs,
            environmental_factors=env_factors,
            organ_growth_rates=growth_rates,
            growth_stage=growth_stage,
            stress_factors=stress_factors,
            senescence_rates=senescence_rates
        )
        
        # Print daily summary
        leaf_n_pct = model.organ_states['leaves'].nitrogen_concentration * 100
        
        print(f"{day:<4} {response.uptake_response.total_uptake:<7.3f} "
              f"{response.remobilized_nitrogen:<6.3f} {leaf_n_pct:<7.2f} "
              f"{response.nitrogen_stress_level:<7.3f} {response.nitrogen_use_efficiency:<6.1f} "
              f"{response.nitrogen_balance:<8.3f}")
    
    # Final summary
    summary = model.get_nitrogen_summary()
    print(f"\nFinal nitrogen balance summary:")
    print(f"• Total plant nitrogen: {summary['total_plant_nitrogen']:.2f} g N")
    print(f"• Total biomass: {summary['total_biomass']:.1f} g")
    print(f"• Nitrogen use efficiency: {summary['nitrogen_use_efficiency']:.1f} g biomass/g N")
    print(f"• Cumulative uptake: {summary['cumulative_uptake']:.2f} g N")
    print(f"• Cumulative remobilization: {summary['cumulative_remobilization']:.3f} g N")
    print(f"• Nitrogen stress level: {summary['nitrogen_stress_level']:.3f}")
    
    print(f"\nOrgan nitrogen concentrations:")
    for organ, conc in summary['organ_n_concentrations'].items():
        status = summary['organ_n_status'][organ]
        print(f"  {organ}: {conc*100:.2f}% N ({status})")


if __name__ == "__main__":
    demonstrate_nitrogen_balance_model()