"""
Mechanistic Nutrient Uptake Model using Monod/Michaelis-Menten Kinetics
Implements scientific nutrient uptake with saturation kinetics and biomass-dependent consumption
Based on: NiCoLet model principles and hydroponic crop modeling research
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from .hydroponic_root_dynamics import HydroponicRootSystem, HydroponicRootModel


class GrowthStage(Enum):
    """Growth stages affecting nutrient uptake kinetics."""
    SLOW_GROWTH = "slow_growth"
    RAPID_GROWTH = "rapid_growth" 
    STEADY_GROWTH = "steady_growth"


@dataclass
class NutrientKinetics:
    """Monod kinetics parameters for specific nutrient and growth stage."""
    nutrient_id: str
    vmax: float      # Maximum uptake rate (mg/g-biomass/day)
    km: float        # Half-saturation constant (mg/L)
    min_conc: float  # Minimum concentration for uptake (mg/L)
    max_conc: float  # Maximum beneficial concentration (mg/L)
    uptake_efficiency: float  # Stage-specific efficiency factor (0-1)


@dataclass
class PlantBiomass:
    """Plant biomass compartments following NiCoLet model with hydroponic root system."""
    structural_mass: float    # g dry weight - shoots + structural roots
    carbon_storage: float     # g C - stored carbohydrates  
    nitrogen_storage: float   # g N - stored nitrogen compounds
    total_fresh_weight: float # g fresh weight - for yield calculations
    shoot_mass: float = 0.0 # g dry weight
    root_mass: float = 0.0 # g dry weight
    
    # Hydroponic root system integration
    root_system: Optional[HydroponicRootSystem] = None
    
    def get_total_dry_mass(self) -> float:
        """Calculate total dry biomass including detailed root mass."""
        base_mass = self.structural_mass + self.carbon_storage + self.nitrogen_storage
        if self.root_system:
            # Root mass is already included in structural_mass, avoid double counting
            return base_mass
        else:
            return base_mass
    
    def get_uptake_capacity(self) -> float:
        """Calculate nutrient uptake capacity based on root surface area and efficiency."""
        if self.root_system:
            # Use actual root surface area and efficiency for uptake capacity
            effective_surface = (self.root_system.root_surface_area * 
                               self.root_system.solution_root_fraction * 
                               self.root_system.uptake_efficiency)
            # Convert cm² to uptake capacity units (approximate scaling)
            return effective_surface * 0.01  # mg/day capacity per cm² surface
        else:
            # Fallback to original calculation
            return self.structural_mass * 0.7 + self.nitrogen_storage * 0.3


class MechanisticNutrientUptake:
    """Mechanistic nutrient uptake model with Monod kinetics."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        # Initialize stage-specific kinetic parameters based on research
        self.kinetic_params = self._initialize_kinetic_parameters(config_dict)
        
        # Biomass growth parameters (simplified from NiCoLet)
        if config_dict and 'growth_params' in config_dict:
            self.growth_params = config_dict['growth_params']
        else:
            self.growth_params = {
                'carbon_assimilation_rate': 0.12,     # g C/g-biomass/day
                'nitrogen_assimilation_rate': 0.018,  # g N/g-biomass/day  
                'structural_growth_efficiency': 0.75, # C to structure conversion
                'respiration_rate': 0.02,             # Daily maintenance respiration
                'fresh_to_dry_ratio': 12.0            # Fresh:dry weight ratio for lettuce
            }
        
        # Fault detection thresholds
        if config_dict and 'fault_thresholds' in config_dict:
            self.fault_thresholds = config_dict['fault_thresholds']
        else:
            self.fault_thresholds = {
                'uptake_prediction_error': 0.25,      # 25% error threshold
                'concentration_depletion_rate': 0.15, # 15% daily depletion limit
                'biomass_inconsistency': 0.20         # 20% biomass prediction error
            }
    
    def _initialize_kinetic_parameters(self, config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[GrowthStage, NutrientKinetics]]:
        """Initialize Monod kinetics parameters for each nutrient and growth stage."""
        
        # Use config if available, otherwise use default values
        kinetic_config = {}
        if config_dict and 'kinetic_parameters' in config_dict:
            kinetic_config = config_dict['kinetic_parameters']
        
        # Based on hydroponic lettuce research and NiCoLet model parameters
        kinetics = {}
        
        # Helper function to get kinetic parameters from config or defaults
        def get_kinetic_params(nutrient_id: str, stage_name: str, defaults: dict) -> NutrientKinetics:
            if nutrient_id in kinetic_config and stage_name in kinetic_config[nutrient_id]:
                params = kinetic_config[nutrient_id][stage_name]
                return NutrientKinetics(
                    nutrient_id=nutrient_id,
                    vmax=params.get('vmax', defaults['vmax']),
                    km=params.get('km', defaults['km']),
                    min_conc=params.get('min_conc', defaults['min_conc']),
                    max_conc=params.get('max_conc', defaults['max_conc']),
                    uptake_efficiency=params.get('uptake_efficiency', defaults['uptake_efficiency'])
                )
            else:
                return NutrientKinetics(nutrient_id=nutrient_id, **defaults)
        
        # Nitrogen (NO3-) - Primary growth driver
        kinetics['N-NO3'] = {
            GrowthStage.SLOW_GROWTH: get_kinetic_params('N-NO3', 'slow_growth', {
                'vmax': 0.45, 'km': 18.0, 'min_conc': 5.0, 'max_conc': 250.0, 'uptake_efficiency': 0.7
            }),
            GrowthStage.RAPID_GROWTH: get_kinetic_params('N-NO3', 'rapid_growth', {
                'vmax': 1.2, 'km': 12.0, 'min_conc': 10.0, 'max_conc': 300.0, 'uptake_efficiency': 0.95
            }),
            GrowthStage.STEADY_GROWTH: get_kinetic_params('N-NO3', 'steady_growth', {
                'vmax': 0.6, 'km': 22.0, 'min_conc': 8.0, 'max_conc': 200.0, 'uptake_efficiency': 0.8
            })
        }
        
        # Phosphorus (PO4-3) - Energy metabolism
        kinetics['P-PO4'] = {
            GrowthStage.SLOW_GROWTH: get_kinetic_params('P-PO4', 'slow_growth', {
                'vmax': 0.12, 'km': 8.0, 'min_conc': 2.0, 'max_conc': 60.0, 'uptake_efficiency': 0.6
            }),
            GrowthStage.RAPID_GROWTH: get_kinetic_params('P-PO4', 'rapid_growth', {
                'vmax': 0.28, 'km': 6.0, 'min_conc': 3.0, 'max_conc': 80.0, 'uptake_efficiency': 0.85
            }),
            GrowthStage.STEADY_GROWTH: get_kinetic_params('P-PO4', 'steady_growth', {
                'vmax': 0.15, 'km': 10.0, 'min_conc': 2.5, 'max_conc': 50.0, 'uptake_efficiency': 0.7
            })
        }
        
        # Potassium (K+) - Osmoregulation and quality
        kinetics['K'] = {
            GrowthStage.SLOW_GROWTH: get_kinetic_params('K', 'slow_growth', {
                'vmax': 0.35, 'km': 25.0, 'min_conc': 10.0, 'max_conc': 350.0, 'uptake_efficiency': 0.8
            }),
            GrowthStage.RAPID_GROWTH: get_kinetic_params('K', 'rapid_growth', {
                'vmax': 0.75, 'km': 20.0, 'min_conc': 15.0, 'max_conc': 400.0, 'uptake_efficiency': 0.9
            }),
            GrowthStage.STEADY_GROWTH: get_kinetic_params('K', 'steady_growth', {
                'vmax': 0.85, 'km': 18.0, 'min_conc': 12.0, 'max_conc': 350.0, 'uptake_efficiency': 0.95
            })
        }
        
        # Calcium (Ca2+) - Cell walls and structure
        kinetics['Ca'] = {
            GrowthStage.SLOW_GROWTH: get_kinetic_params('Ca', 'slow_growth', {
                'vmax': 0.18, 'km': 15.0, 'min_conc': 5.0, 'max_conc': 180.0, 'uptake_efficiency': 0.65
            }),
            GrowthStage.RAPID_GROWTH: get_kinetic_params('Ca', 'rapid_growth', {
                'vmax': 0.42, 'km': 12.0, 'min_conc': 8.0, 'max_conc': 200.0, 'uptake_efficiency': 0.8
            }),
            GrowthStage.STEADY_GROWTH: get_kinetic_params('Ca', 'steady_growth', {
                'vmax': 0.25, 'km': 18.0, 'min_conc': 6.0, 'max_conc': 160.0, 'uptake_efficiency': 0.7
            })
        }
        
        # Magnesium (Mg2+) - Chlorophyll and enzyme activation
        kinetics['Mg'] = {
            GrowthStage.SLOW_GROWTH: get_kinetic_params('Mg', 'slow_growth', {
                'vmax': 0.08, 'km': 8.0, 'min_conc': 2.0, 'max_conc': 55.0, 'uptake_efficiency': 0.7
            }),
            GrowthStage.RAPID_GROWTH: get_kinetic_params('Mg', 'rapid_growth', {
                'vmax': 0.15, 'km': 6.0, 'min_conc': 3.0, 'max_conc': 70.0, 'uptake_efficiency': 0.85
            }),
            GrowthStage.STEADY_GROWTH: get_kinetic_params('Mg', 'steady_growth', {
                'vmax': 0.10, 'km': 10.0, 'min_conc': 2.5, 'max_conc': 50.0, 'uptake_efficiency': 0.75
            })
        }
        
        return kinetics
    
    def calculate_monod_uptake(self, concentration: float, kinetics: NutrientKinetics,
                              biomass: PlantBiomass, environmental_factor: float = 1.0,
                              solution_volume: float = 500.0) -> Tuple[float, Dict]:
        """
        Calculate nutrient uptake using Monod kinetics with hydroponic root dynamics.
        
        Args:
            concentration: Current nutrient concentration (mg/L)
            kinetics: Nutrient kinetics parameters
            biomass: Current plant biomass with root system
            environmental_factor: Environmental stress factor (0-1)
            solution_volume: Total solution volume (L)
            
        Returns:
            Tuple of (uptake_rate_mg_day, uptake_diagnostics)
        """
        # Get active uptake capacity (now based on root surface area if available)
        uptake_capacity = biomass.get_uptake_capacity()
        
        # Root-specific factors
        intrinsic_root_efficiency = 1.0 # Renamed for clarity
        root_surface_factor = 1.0
        solution_contact_factor = 1.0 # New variable for solution contact
        
        if biomass.root_system:
            # Use actual root system parameters
            intrinsic_root_efficiency = biomass.root_system.uptake_efficiency
            
            # Root surface area factor (more surface = more uptake potential)
            # Normalize against typical mature lettuce root surface (500 cm²)
            root_surface_factor = min(2.0, biomass.root_system.root_surface_area / 500.0)
            
            # Solution contact factor (hydroponic-specific)
            solution_contact_factor = biomass.root_system.solution_root_fraction
        
        # Check if concentration is below minimum threshold
        if concentration < kinetics.min_conc:
            uptake_rate = 0.0
            limitation_factor = "minimum_threshold"
        else:
            # Monod equation with hydroponic root system integration
            # Uptake = (Vmax * C / (Km + C)) * Root_Surface * Efficiency * Environment * Root_Health * Solution_Contact
            saturation_term = concentration / (kinetics.km + concentration)
            uptake_rate = (kinetics.vmax * saturation_term * uptake_capacity * 
                          kinetics.uptake_efficiency * environmental_factor *
                          intrinsic_root_efficiency * root_surface_factor *
                          solution_contact_factor)
            
            # Determine limiting factor
            if concentration < kinetics.km:
                limitation_factor = "concentration_limited"
            elif uptake_capacity < 1.0:
                limitation_factor = "root_limited"  # Changed from biomass_limited
            elif environmental_factor < 0.8:
                limitation_factor = "environment_limited"
            else:
                limitation_factor = "optimal"
        
        # Prevent uptake above beneficial concentration
        if concentration > kinetics.max_conc:
            uptake_rate *= 0.7  # Reduced efficiency at high concentrations
            limitation_factor = "luxury_consumption"
        
        # Solution volume effect (larger volume = more stable uptake)
        volume_stability = min(1.0, solution_volume / 100.0)  # Normalize to 100L
        uptake_rate *= volume_stability
        
        # Diagnostic information with hydroponic specifics
        diagnostics = {
            'uptake_rate_mg_day': uptake_rate,
            'saturation_factor': min(1.0, concentration / kinetics.km),
            'root_capacity_factor': uptake_capacity,
            'root_surface_factor': root_surface_factor,
            'root_efficiency': intrinsic_root_efficiency,
            'solution_contact': biomass.root_system.solution_root_fraction if biomass.root_system else 1.0,
            'kinetic_efficiency': kinetics.uptake_efficiency,
            'environmental_factor': environmental_factor,
            'volume_stability': volume_stability,
            'limitation_factor': limitation_factor,
            'predicted_depletion_days': concentration / (uptake_rate + 1e-10),
            'root_health_score': self._get_root_health_score(biomass)
        }
        
        return uptake_rate, diagnostics
    
    def _get_root_health_score(self, biomass: PlantBiomass) -> float:
        """Calculate root health score for diagnostics."""
        if biomass.root_system:
            # Simple health score based on efficiency and growth
            base_score = biomass.root_system.uptake_efficiency * 100
            growth_bonus = min(20, biomass.root_system.root_growth_rate * 1000)  # Bonus for active growth
            senescence_penalty = min(30, biomass.root_system.root_senescence_rate * 2000)  # Penalty for senescence
            return max(0, min(100, base_score + growth_bonus - senescence_penalty))
        else:
            return 75.0  # Default score for simplified model
    
    
    
    def detect_nutrient_faults(self, predicted_concentrations: Dict[str, float],
                             actual_concentrations: Dict[str, float],
                             uptake_diagnostics: Dict[str, Dict]) -> Dict[str, str]:
        """
        Fault detection system comparing predicted vs actual nutrient dynamics.
        """
        faults = {}
        
        for nutrient_id in predicted_concentrations:
            if nutrient_id not in actual_concentrations:
                continue
                
            predicted = predicted_concentrations[nutrient_id]
            actual = actual_concentrations[nutrient_id]
            
            # Prediction error check
            if predicted > 0:
                error = abs(predicted - actual) / predicted
                if error > self.fault_thresholds['uptake_prediction_error']:
                    faults[f'{nutrient_id}_prediction'] = f"High prediction error: {error:.2%}"
            
            # Rapid depletion check
            if nutrient_id in uptake_diagnostics:
                depletion_days = uptake_diagnostics[nutrient_id].get('predicted_depletion_days', float('inf'))
                if depletion_days < 5.0:  # Less than 5 days remaining
                    faults[f'{nutrient_id}_depletion'] = f"Rapid depletion predicted: {depletion_days:.1f} days"
            
            # Concentration range check
            if nutrient_id in self.kinetic_params:
                stage_params = self.kinetic_params[nutrient_id][GrowthStage.RAPID_GROWTH]  # Use rapid as reference
                if actual < stage_params.min_conc:
                    faults[f'{nutrient_id}_deficiency'] = f"Below minimum: {actual:.1f} < {stage_params.min_conc}"
                elif actual > stage_params.max_conc * 1.5:
                    faults[f'{nutrient_id}_excess'] = f"Excessive level: {actual:.1f} > {stage_params.max_conc * 1.5:.1f}"
        
        return faults
    
    def get_optimal_concentrations(self, stage: GrowthStage, biomass: PlantBiomass) -> Dict[str, float]:
        """
        Get optimal nutrient concentrations for given growth stage and biomass.
        """
        optimal_conc = {}
        
        for nutrient_id, stage_params in self.kinetic_params.items():
            if stage in stage_params:
                kinetics = stage_params[stage]
                # Optimal concentration is typically 2-3 times Km for near-maximum uptake
                optimal_conc[nutrient_id] = kinetics.km * 2.5
        
        return optimal_conc
    
    def calculate_nutrient_demand(self, biomass: PlantBiomass, stage: GrowthStage,
                                environmental_factor: float = 1.0) -> Dict[str, float]:
        """
        Calculate theoretical nutrient demand at optimal concentrations.
        Useful for fertigation planning.
        """
        demand = {}
        
        for nutrient_id, stage_params in self.kinetic_params.items():
            if stage in stage_params:
                kinetics = stage_params[stage]
                optimal_conc = kinetics.km * 2.5  # Near-saturating concentration
                
                uptake_rate, _ = self.calculate_monod_uptake(
                    optimal_conc, kinetics, biomass, environmental_factor
                )
                demand[nutrient_id] = uptake_rate
        
        return demand


def create_mechanistic_uptake_model() -> MechanisticNutrientUptake:
    """Create mechanistic nutrient uptake model with configuration."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        uptake_config = config_loader.get_mechanistic_uptake_config()
        return MechanisticNutrientUptake(uptake_config)
    except ImportError:
        # Fallback to default values if config loader not available
        return MechanisticNutrientUptake()


def create_initial_biomass(n_plants: int, initial_fresh_weight_per_plant: float = 2.0,
                          system_type: str = "NFT") -> PlantBiomass:
    """
    Create initial biomass for transplanted lettuce seedlings with hydroponic root system.
    
    Args:
        n_plants: Number of plants in system
        initial_fresh_weight_per_plant: Fresh weight per plant (g)
        system_type: Type of hydroponic system (NFT, DWC, etc.)
    """
    total_fresh_weight = n_plants * initial_fresh_weight_per_plant
    dry_weight_factor = 1.0 / 12.0  # Fresh:dry ratio for young lettuce
    total_dry_weight = total_fresh_weight * dry_weight_factor
    
    # Initialize hydroponic root system
    from .hydroponic_root_dynamics import HydroponicSystemType
    
    # Map string to enum
    system_type_map = {
        "NFT": HydroponicSystemType.NFT,
        "DWC": HydroponicSystemType.DWC,
        "DRIP": HydroponicSystemType.DRIP,
        "AERO": HydroponicSystemType.AERO,
        "WICK": HydroponicSystemType.WICK,
        "EBB_FLOW": HydroponicSystemType.EBB_FLOW
    }
    
    system_enum = system_type_map.get(system_type.upper(), HydroponicSystemType.NFT)
    root_model = HydroponicRootModel(system_enum)
    root_system = root_model.initialize_root_system(n_plants, initial_fresh_weight_per_plant, system_enum)
    
    return PlantBiomass(
        structural_mass=total_dry_weight * 0.7,    # 70% structural (includes roots)
        carbon_storage=total_dry_weight * 0.25,    # 25% C storage  
        nitrogen_storage=total_dry_weight * 0.05,  # 5% N storage
        total_fresh_weight=total_fresh_weight,
        root_system=root_system  # Add hydroponic root system
    )