"""
Enhanced Respiration Model for Hydroponic Crop Simulation
Based on CROPGRO RESPIR.for and plant respiration research

Key concepts implemented:
1. Maintenance respiration - Q10 temperature response
2. Growth respiration - Based on biosynthetic costs
3. Tissue-specific respiration rates
4. Age effects on respiration
5. Temperature acclimation

Research basis:
- Amthor (2000) - Plant respiratory metabolism
- McCree (1970) - Growth vs maintenance respiration
- Ryan (1991) - Temperature effects on respiration
- Atkin & Tjoelker (2003) - Thermal acclimation of respiration
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from enum import Enum


class TissueType(Enum):
    """Plant tissue types with different respiration characteristics."""
    LEAVES = "leaves"
    STEMS = "stems"
    ROOTS = "roots"
    REPRODUCTIVE = "reproductive"


@dataclass
class RespirationParameters:
    """Parameters for respiration model."""
    
    # Maintenance respiration parameters
    maintenance_base_rate: float = 0.015    # g C/g biomass/day at 25°C
    reference_temperature: float = 25.0     # °C reference temperature
    q10_factor: float = 2.3                 # Temperature response coefficient
    
    # Growth respiration parameters
    growth_efficiency: float = 0.75         # Conversion efficiency (glucose → biomass)
    biosynthetic_cost: float = 1.44         # g glucose/g biomass
    
    # Tissue-specific factors
    tissue_factors: Dict[str, float] = None
    
    # Age effects
    age_effect_coefficient: float = 0.002   # Daily increase in respiration per day of age
    max_age_effect: float = 2.0             # Maximum age multiplier
    
    # Temperature acclimation
    acclimation_rate: float = 0.1           # Rate of thermal acclimation
    acclimation_memory: float = 7.0         # Days of temperature memory
    
    # Nitrogen effects
    n_effect_slope: float = 0.5             # Respiration response to leaf N content
    reference_leaf_n: float = 4.0           # g N/g biomass reference
    
    def __post_init__(self):
        if self.tissue_factors is None:
            self.tissue_factors = {
                TissueType.LEAVES.value: 1.0,      # Reference tissue
                TissueType.STEMS.value: 0.7,       # Lower metabolic activity
                TissueType.ROOTS.value: 0.8,       # Moderate activity
                TissueType.REPRODUCTIVE.value: 1.2  # High activity during development
            }
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'RespirationParameters':
        """Create RespirationParameters from configuration dictionary."""
        tissue_factors = config_dict.get('tissue_factors', {})
        
        return cls(
            maintenance_base_rate=config_dict.get('maintenance_base_rate', 0.015),
            reference_temperature=config_dict.get('reference_temperature', 25.0),
            q10_factor=config_dict.get('q10_factor', 2.3),
            growth_efficiency=config_dict.get('growth_efficiency', 0.75),
            biosynthetic_cost=config_dict.get('biosynthetic_cost', 1.44),
            tissue_factors=tissue_factors if tissue_factors else None,
            age_effect_coefficient=config_dict.get('age_effect_coefficient', 0.002),
            max_age_effect=config_dict.get('max_age_effect', 2.0),
            acclimation_rate=config_dict.get('acclimation_rate', 0.1),
            acclimation_memory=config_dict.get('acclimation_memory', 7.0),
            n_effect_slope=config_dict.get('n_effect_slope', 0.5),
            reference_leaf_n=config_dict.get('reference_leaf_n', 4.0)
        )


@dataclass
class BiomassPool:
    """Represents a plant tissue biomass pool."""
    tissue_type: TissueType
    dry_mass: float                    # g dry weight
    age_days: float = 0.0             # Days since formation
    nitrogen_content: float = 0.0     # g N/g biomass
    recent_growth: float = 0.0        # g dry weight added today


@dataclass
class RespirationComponents:
    """Results of respiration calculations."""
    maintenance_respiration: float     # g C/day
    growth_respiration: float         # g C/day
    total_respiration: float          # g C/day
    tissue_breakdown: Dict[str, float] # Respiration by tissue type
    temperature_factor: float         # Temperature response factor
    age_factor: float                 # Age effect factor
    nitrogen_factor: float            # Nitrogen effect factor


class EnhancedRespirationModel:
    """
    Enhanced respiration model following CROPGRO principles.
    
    Calculates both maintenance and growth respiration with:
    - Temperature effects (Q10 response)
    - Tissue-specific rates
    - Age effects
    - Nitrogen content effects
    - Temperature acclimation
    """
    
    def __init__(self, parameters: Optional[RespirationParameters] = None):
        self.params = parameters or RespirationParameters()
        self.temperature_history: List[float] = []
        self.acclimated_reference_temp: float = self.params.reference_temperature
        
    def calculate_temperature_factor(self, temperature: float, acclimated_temp: float = None) -> float:
        """
        Calculate temperature effect on respiration using Q10 response.
        
        Args:
            temperature: Current temperature (°C)
            acclimated_temp: Acclimated reference temperature (°C)
            
        Returns:
            Temperature factor (1.0 at reference temperature)
        """
        reference_temp = acclimated_temp or self.acclimated_reference_temp
        temp_diff = temperature - reference_temp
        
        # Q10 temperature response
        factor = self.params.q10_factor ** (temp_diff / 10.0)
        
        # Prevent excessive respiration at very high temperatures
        if temperature > 40.0:
            # Protein denaturation effects
            excess_temp = temperature - 40.0
            factor *= np.exp(-0.1 * excess_temp)
        
        return max(0.1, factor)
    
    def calculate_age_factor(self, age_days: float) -> float:
        """
        Calculate age effect on maintenance respiration.
        
        Args:
            age_days: Age of tissue in days
            
        Returns:
            Age factor (1.0 for young tissue)
        """
        # Exponential increase in respiration with age
        age_effect = 1.0 + (self.params.age_effect_coefficient * age_days)
        return min(age_effect, self.params.max_age_effect)
    
    def calculate_nitrogen_factor(self, nitrogen_content: float, tissue_type: TissueType) -> float:
        """
        Calculate nitrogen effect on respiration.
        
        Args:
            nitrogen_content: Tissue N content (g N/g biomass)
            tissue_type: Type of tissue
            
        Returns:
            Nitrogen factor (1.0 at reference N content)
        """
        if tissue_type != TissueType.LEAVES:
            return 1.0  # N effects mainly in leaves
        
        n_ratio = nitrogen_content / self.params.reference_leaf_n
        factor = 1.0 + self.params.n_effect_slope * (n_ratio - 1.0)
        
        return max(0.5, min(2.0, factor))
    
    def calculate_maintenance_respiration(self, biomass_pool: BiomassPool, 
                                        temperature: float) -> Tuple[float, Dict[str, float]]:
        """
        Calculate maintenance respiration for a biomass pool.
        
        Args:
            biomass_pool: Plant tissue biomass pool
            temperature: Current temperature (°C)
            
        Returns:
            Tuple of (maintenance_respiration_g_C_day, factor_breakdown)
        """
        # Base respiration rate
        base_rate = self.params.maintenance_base_rate
        
        # Temperature effect
        temp_factor = self.calculate_temperature_factor(temperature)
        
        # Age effect
        age_factor = self.calculate_age_factor(biomass_pool.age_days)
        
        # Nitrogen effect
        n_factor = self.calculate_nitrogen_factor(biomass_pool.nitrogen_content, 
                                                biomass_pool.tissue_type)
        
        # Tissue-specific factor
        tissue_factor = self.params.tissue_factors.get(
            biomass_pool.tissue_type.value, 1.0
        )
        
        # Combined maintenance respiration
        maintenance_respiration = (base_rate * biomass_pool.dry_mass * 
                                 temp_factor * age_factor * n_factor * tissue_factor)
        
        factor_breakdown = {
            'temperature_factor': temp_factor,
            'age_factor': age_factor,
            'nitrogen_factor': n_factor,
            'tissue_factor': tissue_factor
        }
        
        return maintenance_respiration, factor_breakdown
    
    def calculate_growth_respiration(self, new_growth: float, 
                                   growth_composition: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate growth respiration based on new biomass formation.
        
        Args:
            new_growth: New biomass added (g dry weight)
            growth_composition: Composition of new growth (protein, carb, lipid fractions)
            
        Returns:
            Growth respiration (g C/day)
        """
        if new_growth <= 0:
            return 0.0
        
        # Simple approach: fixed biosynthetic cost
        if growth_composition is None:
            growth_cost = self.params.biosynthetic_cost  # g glucose/g biomass
            growth_efficiency = self.params.growth_efficiency
            
            # Growth respiration = biosynthetic cost * (1 - efficiency) * new growth
            glucose_required = growth_cost * new_growth
            glucose_respired = glucose_required * (1.0 - growth_efficiency)
            
            # Convert glucose to carbon (glucose = C6H12O6, MW = 180, C content = 40%)
            carbon_respired = glucose_respired * 0.4
            
        else:
            # Detailed approach based on biochemical composition
            # Different biosynthetic costs for protein, carbohydrate, lipid
            costs = {
                'protein': 1.89,      # g glucose/g protein
                'carbohydrate': 1.11, # g glucose/g carbohydrate  
                'lipid': 2.84,        # g glucose/g lipid
                'organic_acid': 1.0,  # g glucose/g organic acid
                'lignin': 2.0         # g glucose/g lignin
            }
            
            total_glucose_cost = 0.0
            for component, fraction in growth_composition.items():
                cost = costs.get(component, 1.44)  # Default cost
                total_glucose_cost += cost * fraction * new_growth
            
            glucose_respired = total_glucose_cost * (1.0 - self.params.growth_efficiency)
            carbon_respired = glucose_respired * 0.4
        
        return carbon_respired
    
    def update_temperature_acclimation(self, temperature: float):
        """
        Update temperature acclimation based on recent temperature history.
        
        Args:
            temperature: Current daily average temperature (°C)
        """
        # Add current temperature to history
        self.temperature_history.append(temperature)
        
        # Keep only recent history
        max_history_days = int(self.params.acclimation_memory)
        if len(self.temperature_history) > max_history_days:
            self.temperature_history = self.temperature_history[-max_history_days:]
        
        # Calculate running average temperature
        if len(self.temperature_history) >= 3:  # Need some history
            recent_avg_temp = np.mean(self.temperature_history)
            
            # Gradual acclimation towards recent average
            temp_diff = recent_avg_temp - self.acclimated_reference_temp
            acclimation_change = temp_diff * self.params.acclimation_rate
            
            self.acclimated_reference_temp += acclimation_change
            
            # Keep within reasonable bounds
            self.acclimated_reference_temp = np.clip(
                self.acclimated_reference_temp, 15.0, 35.0
            )
    
    def calculate_total_respiration(self, biomass_pools: List[BiomassPool], 
                                  temperature: float, 
                                  total_new_growth: float = 0.0) -> RespirationComponents:
        """
        Calculate total plant respiration from all biomass pools.
        
        Args:
            biomass_pools: List of plant tissue biomass pools
            temperature: Current temperature (°C)
            total_new_growth: Total new growth across all tissues (g dry weight)
            
        Returns:
            Complete respiration breakdown
        """
        # Update temperature acclimation
        self.update_temperature_acclimation(temperature)
        
        # Calculate maintenance respiration for each pool
        total_maintenance = 0.0
        tissue_breakdown = {}
        combined_factors = {
            'temperature_factor': 0.0,
            'age_factor': 0.0,
            'nitrogen_factor': 0.0
        }
        total_biomass = 0.0
        
        for pool in biomass_pools:
            maint_resp, factors = self.calculate_maintenance_respiration(pool, temperature)
            total_maintenance += maint_resp
            
            tissue_name = pool.tissue_type.value
            tissue_breakdown[tissue_name] = maint_resp
            
            # Weight factors by biomass for averaging
            weight = pool.dry_mass
            total_biomass += weight
            
            for factor_name, factor_value in factors.items():
                if factor_name in combined_factors:
                    combined_factors[factor_name] += factor_value * weight
        
        # Calculate weighted average factors
        if total_biomass > 0:
            for factor_name in combined_factors:
                combined_factors[factor_name] /= total_biomass
        
        # Calculate growth respiration
        growth_respiration = self.calculate_growth_respiration(total_new_growth)
        
        # Total respiration
        total_respiration = total_maintenance + growth_respiration
        
        return RespirationComponents(
            maintenance_respiration=total_maintenance,
            growth_respiration=growth_respiration,
            total_respiration=total_respiration,
            tissue_breakdown=tissue_breakdown,
            temperature_factor=combined_factors['temperature_factor'],
            age_factor=combined_factors['age_factor'],
            nitrogen_factor=combined_factors['nitrogen_factor']
        )
    
    def get_daily_carbon_loss(self, respiration_components: RespirationComponents) -> Dict[str, float]:
        """
        Get daily carbon loss breakdown for carbon balance calculations.
        
        Args:
            respiration_components: Calculated respiration components
            
        Returns:
            Dictionary with carbon loss breakdown
        """
        return {
            'maintenance_respiration_g_C': respiration_components.maintenance_respiration,
            'growth_respiration_g_C': respiration_components.growth_respiration,
            'total_respiration_g_C': respiration_components.total_respiration,
            'respiration_coefficient': (respiration_components.total_respiration / 
                                      max(1.0, respiration_components.maintenance_respiration + 
                                          respiration_components.growth_respiration))
        }


def create_lettuce_respiration_model() -> EnhancedRespirationModel:
    """Create respiration model with lettuce-specific parameters."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        respiration_config = config_loader.get_respiration_parameters()
        parameters = RespirationParameters.from_config(respiration_config)
        return EnhancedRespirationModel(parameters)
    except ImportError:
        # Fallback to default values if config loader not available
        return EnhancedRespirationModel()


def create_example_biomass_pools() -> List[BiomassPool]:
    """Create example biomass pools for testing."""
    return [
        BiomassPool(
            tissue_type=TissueType.LEAVES,
            dry_mass=15.0,           # g
            age_days=20.0,
            nitrogen_content=4.2,    # g N/g biomass
            recent_growth=2.0        # g new growth today
        ),
        BiomassPool(
            tissue_type=TissueType.STEMS,
            dry_mass=5.0,            # g
            age_days=25.0,
            nitrogen_content=2.0,
            recent_growth=0.5
        ),
        BiomassPool(
            tissue_type=TissueType.ROOTS,
            dry_mass=8.0,            # g
            age_days=30.0,
            nitrogen_content=2.5,
            recent_growth=1.0
        )
    ]


def demonstrate_respiration_model():
    """Demonstrate respiration model capabilities."""
    model = create_lettuce_respiration_model()
    biomass_pools = create_example_biomass_pools()
    
    print("=" * 80)
    print("ENHANCED RESPIRATION MODEL DEMONSTRATION")
    print("=" * 80)
    
    # Test different temperatures
    temperatures = [15.0, 20.0, 25.0, 30.0, 35.0]
    
    print(f"{'Temp(°C)':<8} {'Maint(gC/d)':<12} {'Growth(gC/d)':<13} {'Total(gC/d)':<12} {'TempFactor':<11}")
    print("-" * 80)
    
    for temp in temperatures:
        total_new_growth = sum(pool.recent_growth for pool in biomass_pools)
        
        respiration = model.calculate_total_respiration(
            biomass_pools, temp, total_new_growth
        )
        
        print(f"{temp:<8.1f} {respiration.maintenance_respiration:<12.3f} "
              f"{respiration.growth_respiration:<13.3f} {respiration.total_respiration:<12.3f} "
              f"{respiration.temperature_factor:<11.3f}")
    
    # Show tissue breakdown
    print(f"\nTissue Breakdown at 25°C:")
    respiration_25c = model.calculate_total_respiration(biomass_pools, 25.0, 3.5)
    
    for tissue, resp_rate in respiration_25c.tissue_breakdown.items():
        print(f"  {tissue:<12}: {resp_rate:.3f} g C/day")
    
    print(f"\nRespiration factors:")
    print(f"  Temperature factor: {respiration_25c.temperature_factor:.3f}")
    print(f"  Age factor: {respiration_25c.age_factor:.3f}")
    print(f"  Nitrogen factor: {respiration_25c.nitrogen_factor:.3f}")
    
    # Test temperature acclimation
    print(f"\nTemperature Acclimation Test:")
    print(f"Initial acclimated temp: {model.acclimated_reference_temp:.1f}°C")
    
    # Simulate 10 days of warm weather
    for day in range(10):
        model.update_temperature_acclimation(30.0)
    
    print(f"After 10 days at 30°C: {model.acclimated_reference_temp:.1f}°C")


if __name__ == "__main__":
    demonstrate_respiration_model()