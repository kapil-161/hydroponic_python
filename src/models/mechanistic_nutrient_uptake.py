"""
Mechanistic Nutrient Uptake Model using Monod/Michaelis-Menten Kinetics
Implements scientific nutrient uptake with saturation kinetics and biomass-dependent consumption
Based on: NiCoLet model principles and hydroponic crop modeling research
"""

import numpy as np
from typing import Dict, Tuple, Optional
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
    
    def __init__(self):
        # Initialize stage-specific kinetic parameters based on research
        self.kinetic_params = self._initialize_kinetic_parameters()
        
        # Biomass growth parameters (simplified from NiCoLet)
        self.growth_params = {
            'carbon_assimilation_rate': 0.12,     # g C/g-biomass/day
            'nitrogen_assimilation_rate': 0.018,  # g N/g-biomass/day  
            'structural_growth_efficiency': 0.75, # C to structure conversion
            'respiration_rate': 0.02,             # Daily maintenance respiration
            'fresh_to_dry_ratio': 12.0            # Fresh:dry weight ratio for lettuce
        }
        
        # Fault detection thresholds
        self.fault_thresholds = {
            'uptake_prediction_error': 0.25,      # 25% error threshold
            'concentration_depletion_rate': 0.15, # 15% daily depletion limit
            'biomass_inconsistency': 0.20         # 20% biomass prediction error
        }
    
    def _initialize_kinetic_parameters(self) -> Dict[str, Dict[GrowthStage, NutrientKinetics]]:
        """Initialize Monod kinetics parameters for each nutrient and growth stage."""
        
        # Based on hydroponic lettuce research and NiCoLet model parameters
        kinetics = {}
        
        # Nitrogen (NO3-) - Primary growth driver
        kinetics['N-NO3'] = {
            GrowthStage.SLOW_GROWTH: NutrientKinetics(
                nutrient_id='N-NO3', vmax=0.45, km=18.0, 
                min_conc=5.0, max_conc=250.0, uptake_efficiency=0.7
            ),
            GrowthStage.RAPID_GROWTH: NutrientKinetics(
                nutrient_id='N-NO3', vmax=1.2, km=12.0,
                min_conc=10.0, max_conc=300.0, uptake_efficiency=0.95
            ),
            GrowthStage.STEADY_GROWTH: NutrientKinetics(
                nutrient_id='N-NO3', vmax=0.6, km=22.0,
                min_conc=8.0, max_conc=200.0, uptake_efficiency=0.8
            )
        }
        
        # Phosphorus (PO4-3) - Energy metabolism
        kinetics['P-PO4'] = {
            GrowthStage.SLOW_GROWTH: NutrientKinetics(
                nutrient_id='P-PO4', vmax=0.12, km=8.0,
                min_conc=2.0, max_conc=60.0, uptake_efficiency=0.6
            ),
            GrowthStage.RAPID_GROWTH: NutrientKinetics(
                nutrient_id='P-PO4', vmax=0.28, km=6.0,
                min_conc=3.0, max_conc=80.0, uptake_efficiency=0.85
            ),
            GrowthStage.STEADY_GROWTH: NutrientKinetics(
                nutrient_id='P-PO4', vmax=0.15, km=10.0,
                min_conc=2.5, max_conc=50.0, uptake_efficiency=0.7
            )
        }
        
        # Potassium (K+) - Osmoregulation and quality
        kinetics['K'] = {
            GrowthStage.SLOW_GROWTH: NutrientKinetics(
                nutrient_id='K', vmax=0.35, km=25.0,
                min_conc=10.0, max_conc=350.0, uptake_efficiency=0.8
            ),
            GrowthStage.RAPID_GROWTH: NutrientKinetics(
                nutrient_id='K', vmax=0.75, km=20.0,
                min_conc=15.0, max_conc=400.0, uptake_efficiency=0.9
            ),
            GrowthStage.STEADY_GROWTH: NutrientKinetics(
                nutrient_id='K', vmax=0.85, km=18.0,  # Higher for quality
                min_conc=12.0, max_conc=350.0, uptake_efficiency=0.95
            )
        }
        
        # Calcium (Ca2+) - Cell walls and structure
        kinetics['Ca'] = {
            GrowthStage.SLOW_GROWTH: NutrientKinetics(
                nutrient_id='Ca', vmax=0.18, km=15.0,
                min_conc=5.0, max_conc=180.0, uptake_efficiency=0.65
            ),
            GrowthStage.RAPID_GROWTH: NutrientKinetics(
                nutrient_id='Ca', vmax=0.42, km=12.0,
                min_conc=8.0, max_conc=200.0, uptake_efficiency=0.8
            ),
            GrowthStage.STEADY_GROWTH: NutrientKinetics(
                nutrient_id='Ca', vmax=0.25, km=18.0,
                min_conc=6.0, max_conc=160.0, uptake_efficiency=0.7
            )
        }
        
        # Magnesium (Mg2+) - Chlorophyll and enzyme activation
        kinetics['Mg'] = {
            GrowthStage.SLOW_GROWTH: NutrientKinetics(
                nutrient_id='Mg', vmax=0.08, km=8.0,
                min_conc=2.0, max_conc=55.0, uptake_efficiency=0.7
            ),
            GrowthStage.RAPID_GROWTH: NutrientKinetics(
                nutrient_id='Mg', vmax=0.15, km=6.0,
                min_conc=3.0, max_conc=70.0, uptake_efficiency=0.85
            ),
            GrowthStage.STEADY_GROWTH: NutrientKinetics(
                nutrient_id='Mg', vmax=0.10, km=10.0,
                min_conc=2.5, max_conc=50.0, uptake_efficiency=0.75
            )
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
        root_efficiency = 1.0
        root_surface_factor = 1.0
        
        if biomass.root_system:
            # Use actual root system parameters
            root_efficiency = biomass.root_system.uptake_efficiency
            
            # Root surface area factor (more surface = more uptake potential)
            # Normalize against typical mature lettuce root surface (500 cm²)
            root_surface_factor = min(2.0, biomass.root_system.root_surface_area / 500.0)
            
            # Solution contact factor (hydroponic-specific)
            solution_contact = biomass.root_system.solution_root_fraction
            root_efficiency *= solution_contact
        
        # Check if concentration is below minimum threshold
        if concentration < kinetics.min_conc:
            uptake_rate = 0.0
            limitation_factor = "minimum_threshold"
        else:
            # Monod equation with hydroponic root system integration
            # Uptake = (Vmax * C / (Km + C)) * Root_Surface * Efficiency * Environment * Root_Health
            saturation_term = concentration / (kinetics.km + concentration)
            uptake_rate = (kinetics.vmax * saturation_term * uptake_capacity * 
                          kinetics.uptake_efficiency * environmental_factor *
                          root_efficiency * root_surface_factor)
            
            # Determine limiting factor
            if concentration < kinetics.km:
                limitation_factor = "concentration_limited"
            elif uptake_capacity < 1.0:
                limitation_factor = "root_limited"  # Changed from biomass_limited
            elif root_efficiency < 0.7:
                limitation_factor = "root_health_limited"
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
            'root_efficiency': root_efficiency,
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
    
    def update_biomass(self, current_biomass: PlantBiomass, nutrient_uptake: Dict[str, float],
                      environmental_conditions: Dict, stage: GrowthStage) -> PlantBiomass:
        """
        Update plant biomass based on nutrient uptake and environmental conditions.
        Includes hydroponic root system dynamics.
        """
        # Environmental growth factor (temperature, light, etc.)
        env_growth_factor = environmental_conditions.get('growth_factor', 1.0)
        
        # Calculate carbon assimilation (simplified photosynthesis)
        light_factor = min(1.0, environmental_conditions.get('dli_factor', 1.0))
        temp_factor = min(1.0, environmental_conditions.get('temp_factor', 1.0))
        carbon_assimilation = (self.growth_params['carbon_assimilation_rate'] * 
                             current_biomass.structural_mass * light_factor * temp_factor)
        
        # Calculate nitrogen assimilation from uptake
        n_uptake_g = nutrient_uptake.get('N-NO3', 0) / 1000.0  # Convert mg to g
        nitrogen_assimilation = min(n_uptake_g, 
                                  self.growth_params['nitrogen_assimilation_rate'] * 
                                  current_biomass.structural_mass)
        
        # Growth limitation by most limiting factor
        growth_limitation = min(
            carbon_assimilation / (self.growth_params['carbon_assimilation_rate'] * current_biomass.structural_mass + 1e-10),
            nitrogen_assimilation / (self.growth_params['nitrogen_assimilation_rate'] * current_biomass.structural_mass + 1e-10),
            env_growth_factor
        )
        
        # Update biomass compartments
        # Respiration losses
        respiration_loss = current_biomass.structural_mass * self.growth_params['respiration_rate']
        
        # Structural growth (limited by both C and N availability)
        structural_growth = (carbon_assimilation * self.growth_params['structural_growth_efficiency'] * 
                           growth_limitation - respiration_loss)
        structural_growth = max(0, structural_growth)  # No negative growth
        
        # Storage compartments
        excess_carbon = carbon_assimilation - structural_growth / self.growth_params['structural_growth_efficiency']
        excess_nitrogen = nitrogen_assimilation - structural_growth * 0.02  # 2% N in structural mass
        
        # Update root system dynamics (hydroponic-specific)
        updated_root_system = current_biomass.root_system
        if current_biomass.root_system:
            # Create root model for the same system type
            from .hydroponic_root_dynamics import HydroponicRootModel
            
            # Determine system type from root system properties
            if hasattr(current_biomass.root_system, '_system_type'):
                system_type = current_biomass.root_system._system_type
            else:
                # Infer system type from root characteristics
                if current_biomass.root_system.solution_root_fraction > 0.7:
                    from .hydroponic_root_dynamics import HydroponicSystemType
                    system_type = HydroponicSystemType.DWC
                else:
                    from .hydroponic_root_dynamics import HydroponicSystemType
                    system_type = HydroponicSystemType.NFT
            
            root_model = HydroponicRootModel(system_type)
            
            # Convert stage enum to string for root model
            stage_string = stage.value if hasattr(stage, 'value') else 'rapid_growth'
            
            # Environmental conditions for root growth
            root_env_conditions = {
                'temp_avg': environmental_conditions.get('temp_avg', 20.0),
                'dissolved_oxygen': environmental_conditions.get('dissolved_oxygen', 6.0),
                'ph': environmental_conditions.get('ph', 6.0),
                'flow_rate': environmental_conditions.get('flow_rate', 1.0)
            }
            
            # Calculate total biomass for root model
            total_biomass = current_biomass.get_total_dry_mass()
            
            # Update root system
            updated_root_system = root_model.calculate_daily_root_growth(
                current_biomass.root_system, total_biomass, stage_string, root_env_conditions
            )
        
        new_biomass = PlantBiomass(
            structural_mass=current_biomass.structural_mass + structural_growth,
            carbon_storage=current_biomass.carbon_storage + max(0, excess_carbon * 0.5),
            nitrogen_storage=current_biomass.nitrogen_storage + max(0, excess_nitrogen * 0.8),
            total_fresh_weight=(current_biomass.structural_mass + structural_growth) * 
                             self.growth_params['fresh_to_dry_ratio'],
            root_system=updated_root_system  # Include updated root system
        )
        
        return new_biomass
    
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
    root_system = root_model.initialize_root_system(n_plants, initial_fresh_weight_per_plant)
    
    return PlantBiomass(
        structural_mass=total_dry_weight * 0.7,    # 70% structural (includes roots)
        carbon_storage=total_dry_weight * 0.25,    # 25% C storage  
        nitrogen_storage=total_dry_weight * 0.05,  # 5% N storage
        total_fresh_weight=total_fresh_weight,
        root_system=root_system  # Add hydroponic root system
    )