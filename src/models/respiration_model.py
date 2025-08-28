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
    maintenance_base_rate: float     # g C/g biomass/day at 25°C
    reference_temperature: float     # °C reference temperature
    q10_factor: float                # Temperature response coefficient
    
    # Growth respiration parameters
    growth_efficiency: float         # Conversion efficiency (glucose → biomass)
    biosynthetic_cost: float         # g glucose/g biomass
    
    # Tissue-specific factors
    tissue_factors: Dict[str, float]
    
    # Age effects
    age_effect_coefficient: float    # Daily increase in respiration per day of age
    max_age_effect: float            # Maximum age multiplier
    
    # Temperature acclimation
    acclimation_rate: float          # Rate of thermal acclimation
    acclimation_memory: float        # Days of temperature memory
    
    # Nitrogen effects
    n_effect_slope: float            # Respiration response to leaf N content
    reference_leaf_n: float          # g N/g biomass reference
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'RespirationParameters':
        """Create RespirationParameters from configuration dictionary with clear error reporting."""
        import logging
        logger = logging.getLogger(__name__)
        
        def _get_required_param(param_dict: dict, param_name: str, param_source: str) -> any:
            """Get a required parameter with clear error message if missing."""
            if param_name not in param_dict:
                available_params = list(param_dict.keys()) if param_dict else 'None'
                error_msg = f"❌ Missing required parameter '{param_name}' in {param_source}. Available parameters: {available_params}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            return param_dict[param_name]
        
        # Handle tissue factors with defaults for missing values
        tissue_factors = config_dict.get('tissue_factors', {})
        if not tissue_factors:
            tissue_factors = {
                TissueType.LEAVES.value: 1.0,
                TissueType.STEMS.value: 0.7,
                TissueType.ROOTS.value: 0.8,
                TissueType.REPRODUCTIVE.value: 1.2
            }
        
        return cls(
            maintenance_base_rate=_get_required_param(config_dict, 'maintenance_base_rate', 'respiration_parameters.csv'),
            reference_temperature=_get_required_param(config_dict, 'reference_temperature', 'respiration_parameters.csv'),
            q10_factor=_get_required_param(config_dict, 'q10_factor', 'respiration_parameters.csv'),
            growth_efficiency=_get_required_param(config_dict, 'growth_efficiency', 'respiration_parameters.csv'),
            biosynthetic_cost=_get_required_param(config_dict, 'biosynthetic_cost', 'respiration_parameters.csv'),
            tissue_factors=tissue_factors,
            age_effect_coefficient=_get_required_param(config_dict, 'age_effect_coefficient', 'respiration_parameters.csv'),
            max_age_effect=_get_required_param(config_dict, 'max_age_effect', 'respiration_parameters.csv'),
            acclimation_rate=_get_required_param(config_dict, 'acclimation_rate', 'respiration_parameters.csv'),
            acclimation_memory=_get_required_param(config_dict, 'acclimation_memory', 'respiration_parameters.csv'),
            n_effect_slope=_get_required_param(config_dict, 'n_effect_slope', 'respiration_parameters.csv'),
            reference_leaf_n=_get_required_param(config_dict, 'reference_leaf_n', 'respiration_parameters.csv')
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
        from ..utils.temperature_utils import calculate_q10_temperature_factor
        
        reference_temp = acclimated_temp or self.acclimated_reference_temp
        
        # Use shared Q10 calculation
        factor = calculate_q10_temperature_factor(
            temperature=temperature,
            reference_temp=reference_temp,
            q10_factor=self.params.q10_factor,
            min_factor=0.1,
            max_factor=4.0
        )
        
        # Prevent excessive respiration at very high temperatures
        if temperature > 40.0:
            # Protein denaturation effects
            excess_temp = temperature - 40.0
            factor *= np.exp(-0.1 * excess_temp)
        
        return factor
    
    def calculate_age_factor(self, age_days: float) -> float:
        """
        Calculate age effect on maintenance respiration.
        
        Args:
            age_days: Age of tissue in days
            
        Returns:
            Age factor (1.0 for young tissue)
        """
        from ..utils.math_utils import clamp_value
        
        # Natural exponential increase in respiration with age - no caps
        age_effect = 1.0 + (self.params.age_effect_coefficient * max(0.0, age_days))
        return max(1.0, age_effect)  # Natural aging without artificial limits
    
    def calculate_nitrogen_factor(self, nitrogen_content: float, tissue_type: TissueType) -> float:
        """
        Calculate nitrogen effect on respiration.
        
        Args:
            nitrogen_content: Tissue N content (g N/g biomass)
            tissue_type: Type of tissue
            
        Returns:
            Nitrogen factor (1.0 at reference N content)
        """
        from ..utils.math_utils import safe_divide
        
        if tissue_type != TissueType.LEAVES:
            return 1.0  # N effects mainly in leaves
        
        n_ratio = safe_divide(nitrogen_content, self.params.reference_leaf_n, 1.0)
        factor = 1.0 + self.params.n_effect_slope * (n_ratio - 1.0)
        
        return max(0.1, factor)  # Natural nitrogen response without caps
    
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
        
        # Real-world maintenance penalties for excessive biomass
        # Large plants have disproportionately high maintenance costs
        size_penalty_factor = 1.0
        if biomass_pool.dry_mass > 50.0:  # Above normal lettuce size
            excess_mass = biomass_pool.dry_mass - 50.0
            # Exponential penalty for maintaining excessive biomass
            size_penalty_factor = 1.0 + 0.02 * excess_mass  # 2% increase per gram above 50g
        
        # Combined maintenance respiration with realistic size penalties
        maintenance_respiration = (base_rate * biomass_pool.dry_mass * 
                                 temp_factor * age_factor * n_factor * tissue_factor * size_penalty_factor)
        
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
            from ..utils.math_utils import clamp_value
            self.acclimated_reference_temp = clamp_value(
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

def create_lettuce_respiration_model() -> EnhancedRespirationModel:
    """Create respiration model with lettuce-specific parameters from CSV config."""
    from ..utils.config_loader import get_config_loader
    config_loader = get_config_loader()
    respiration_config = config_loader.get_respiration_parameters()
    parameters = RespirationParameters.from_config(respiration_config)
    return EnhancedRespirationModel(parameters)


def demonstrate_respiration_model():
    """Demonstrate respiration model with sample biomass pools."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        r_config = config_loader.get_respiration_parameters()
        model = EnhancedRespirationModel(RespirationParameters.from_config(r_config))
    except Exception as e:
        print(f"⚠️ Could not load respiration parameters from CSV: {e}")
        print("Please ensure respiration_parameters.csv exists with all required parameters")
        return

    # Define sample biomass pools
    pools = [
        BiomassPool(TissueType.LEAVES, dry_mass=50.0, age_days=20, nitrogen_content=4.0, recent_growth=1.5),
        BiomassPool(TissueType.STEMS, dry_mass=20.0, age_days=30, nitrogen_content=1.5, recent_growth=0.3),
        BiomassPool(TissueType.ROOTS, dry_mass=15.0, age_days=25, nitrogen_content=1.0, recent_growth=0.4),
    ]

    print("=" * 80)
    print("RESPIRATION MODEL DEMONSTRATION")
    print("=" * 80)

    for temp in [18.0, 22.0, 26.0]:
        components = model.calculate_total_respiration(pools, temperature=temp, total_new_growth=sum(p.recent_growth for p in pools))
        print(f"Temp {temp:.1f}C -> Maintenance: {components.maintenance_respiration:.2f} gC/d, "
              f"Growth: {components.growth_respiration:.2f} gC/d, Total: {components.total_respiration:.2f} gC/d")


if __name__ == "__main__":
    demonstrate_respiration_model()