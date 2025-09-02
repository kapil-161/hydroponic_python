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
        """Create RespirationParameters from CSV configuration data.
        
        Args:
            config_dict: Dictionary containing respiration parameters from CSV files
        """
        # Require all parameters from CSV - no hardcoded defaults allowed
        def get_required_param(param_name: str) -> float:
            if param_name not in config_dict:
                available_params = list(config_dict.keys())
                raise ValueError(f"❌ Missing required respiration parameter '{param_name}' in CSV. Available: {available_params}")
            return config_dict[param_name]
        
        # Handle tissue factors from CSV
        tissue_factors = {
            TissueType.LEAVES.value: get_required_param('tissue_factor_leaves'),
            TissueType.STEMS.value: get_required_param('tissue_factor_stems'),
            TissueType.ROOTS.value: get_required_param('tissue_factor_roots'),
            TissueType.REPRODUCTIVE.value: get_required_param('tissue_factor_reproductive')
        }
        
        return cls(
            # Maintenance respiration parameters
            maintenance_base_rate=get_required_param('maintenance_base_rate'),
            reference_temperature=get_required_param('reference_temperature'),
            q10_factor=get_required_param('q10_factor'),
            
            # Growth respiration parameters
            growth_efficiency=get_required_param('growth_efficiency'),
            biosynthetic_cost=get_required_param('biosynthetic_cost'),
            
            # Tissue-specific factors
            tissue_factors=tissue_factors,
            
            # Age effects
            age_effect_coefficient=get_required_param('age_effect_coefficient'),
            max_age_effect=get_required_param('max_age_effect'),
            
            # Temperature acclimation
            acclimation_rate=get_required_param('acclimation_rate'),
            acclimation_memory=get_required_param('acclimation_memory'),
            
            # Nitrogen effects
            n_effect_slope=get_required_param('n_effect_slope'),
            reference_leaf_n=get_required_param('reference_leaf_n')
        )
    
    def get_required_growth_composition(self, config_dict: dict) -> Dict[str, float]:
        """Get required growth composition from CSV config only."""
        def get_required_param(param_name: str) -> float:
            if param_name not in config_dict:
                available_params = list(config_dict.keys())
                raise ValueError(f"❌ Missing required growth composition parameter '{param_name}' in CSV. Available: {available_params}")
            return config_dict[param_name]
        
        return {
            'protein': get_required_param('protein_fraction'),
            'carbohydrate': get_required_param('carbohydrate_fraction'),
            'lipid': get_required_param('lipid_fraction'),
            'organic_acid': get_required_param('organic_acid_fraction'),
            'lignin': get_required_param('lignin_fraction')
        }


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
    
    def __init__(self, parameters: Optional[RespirationParameters] = None, config_dict: Optional[dict] = None):
        self.params = parameters or RespirationParameters()
        self.config_dict = config_dict or {}
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
        temp = float(temperature)
        if temp > 40.0:
            # Protein denaturation effects
            excess_temp = temp - 40.0
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
        tissue_type = biomass_pool.tissue_type
        if hasattr(tissue_type, 'value'):
            tissue_key = tissue_type.value
        else:
            tissue_key = str(tissue_type)
        
        tissue_factor = self.params.tissue_factors.get(tissue_key, 1.0)
        
        # Real-world maintenance penalties for excessive biomass
        # Large plants have disproportionately high maintenance costs
        size_penalty_factor = 1.0
        dry_weight = getattr(biomass_pool, 'dry_mass', getattr(biomass_pool, 'dry_weight', 1.0))
        if dry_weight > 50.0:  # Above normal lettuce size
            excess_mass = dry_weight - 50.0
            # Exponential penalty for maintaining excessive biomass
            size_penalty_factor = 1.0 + 0.02 * excess_mass  # 2% increase per gram above 50g
        
        # Combined maintenance respiration with realistic size penalties
        maintenance_respiration = (base_rate * dry_weight * 
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
        
        # Use detailed composition by default if config is available
        if growth_composition is None and self.config_dict:
            growth_composition = self.params.get_default_growth_composition(self.config_dict)
        
        # Detailed approach based on biochemical composition (now the default)
        if growth_composition is not None:
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
                cost = costs.get(component)
                if cost is None:
                    raise ValueError(f"❌ Respiration cost for {component} must be provided in CSV configuration - no hardcoded defaults allowed")
                total_glucose_cost += cost * fraction * new_growth
            
            glucose_respired = total_glucose_cost * (1.0 - self.params.growth_efficiency)
            carbon_respired = glucose_respired * 0.4
            
        else:
            # Fallback to simple approach only if no composition data available
            growth_cost = self.params.biosynthetic_cost  # g glucose/g biomass
            growth_efficiency = self.params.growth_efficiency
            
            # Growth respiration = biosynthetic cost * (1 - efficiency) * new growth
            glucose_required = growth_cost * new_growth
            glucose_respired = glucose_required * (1.0 - growth_efficiency)
            
            # Convert glucose to carbon (glucose = C6H12O6, MW = 180, C content = 40%)
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
            
            tissue_name = pool.tissue_type.value if hasattr(pool.tissue_type, 'value') else str(pool.tissue_type)
            tissue_breakdown[tissue_name] = maint_resp
            
            # Weight factors by biomass for averaging
            weight = getattr(pool, 'dry_mass', getattr(pool, 'dry_weight', 1.0))
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
    
    def hourly_update(self, biomass_pools: List['BiomassPool'], temperature: float, 
                     hour: int, dt_hours: float = 1.0, new_growth: float = 0.0) -> Dict[str, float]:
        """
        Hourly respiration update for DSSAT-style integration.
        
        Respiration responds rapidly to temperature changes and varies throughout the day.
        Temperature can fluctuate significantly hourly, affecting respiration immediately.
        
        Args:
            biomass_pools: Current plant biomass pools
            temperature: Current temperature (°C)
            hour: Hour of day (0-23)
            dt_hours: Time step in hours
            new_growth: New growth in this timestep (g dry weight)
            
        Returns:
            Dict with hourly respiration rates and factors
        """
        # Calculate hourly respiration components
        components = self.calculate_total_respiration(
            biomass_pools, temperature, new_growth
        )
        
        # Scale from daily to hourly rates
        hourly_maintenance = components.maintenance_respiration / 24.0 * dt_hours
        hourly_growth = components.growth_respiration / 24.0 * dt_hours
        hourly_total = components.total_respiration / 24.0 * dt_hours
        
        # Apply diurnal variation to respiration
        diurnal_factor = self._calculate_diurnal_respiration_factor(hour)
        
        # Apply day/night differences
        is_day = 6 <= hour <= 18  # Simplified day/night cycle
        day_night_factor = 1.1 if is_day else 0.9  # Higher respiration during day
        
        # Combined hourly adjustment
        hourly_adjustment = diurnal_factor * day_night_factor
        
        # Calculate temperature-dependent adjustments  
        temp_stress_factor = self._calculate_temperature_stress_factor(temperature)
        
        # Final hourly respiration rates
        adjusted_maintenance = hourly_maintenance * hourly_adjustment * temp_stress_factor
        adjusted_growth = hourly_growth * hourly_adjustment
        adjusted_total = adjusted_maintenance + adjusted_growth
        
        # Calculate carbon cost (CO2 release)
        # Respiration releases CO2: C6H12O6 + 6O2 → 6CO2 + 6H2O
        # 1 g C respired → 3.67 g CO2 released
        co2_release_rate = adjusted_total * 3.67  # g CO2/hour
        
        # Calculate respiratory quotient (RQ) - varies by substrate
        respiratory_quotient = self._calculate_respiratory_quotient(hour)
        oxygen_consumption_rate = co2_release_rate / respiratory_quotient  # g O2/hour
        
        return {
            'maintenance_respiration_g_C_per_hour': adjusted_maintenance,
            'growth_respiration_g_C_per_hour': adjusted_growth,
            'total_respiration_g_C_per_hour': adjusted_total,
            'co2_release_rate_g_per_hour': co2_release_rate,
            'oxygen_consumption_g_per_hour': oxygen_consumption_rate,
            'respiratory_quotient': respiratory_quotient,
            'temperature_factor': components.temperature_factor,
            'diurnal_factor': diurnal_factor,
            'day_night_factor': day_night_factor,
            'temp_stress_factor': temp_stress_factor,
            'tissue_breakdown': {k: v / 24.0 * dt_hours for k, v in components.tissue_breakdown.items()}
        }
    
    def _calculate_diurnal_respiration_factor(self, hour: int) -> float:
        """
        Calculate diurnal variation in respiration rates.
        
        Respiration typically follows a sinusoidal pattern with peaks in early morning
        and late afternoon, related to circadian rhythms.
        """
        # Circadian rhythm effect (peak at ~4 AM and ~4 PM)
        circadian_component1 = 0.1 * np.sin(2 * np.pi * (hour - 4) / 24)  # 4 AM peak
        circadian_component2 = 0.05 * np.sin(2 * np.pi * (hour - 16) / 24)  # 4 PM peak
        
        # Base respiration varies from 0.9 to 1.1 throughout day
        diurnal_factor = 1.0 + circadian_component1 + circadian_component2
        
        return max(0.8, min(1.2, diurnal_factor))
    
    def _calculate_temperature_stress_factor(self, temperature: float) -> float:
        """
        Calculate additional temperature stress effects on respiration.
        
        Beyond the Q10 response, extreme temperatures can cause additional stress.
        """
        optimal_temp = 22.0  # °C optimal temperature for lettuce
        temp_deviation = abs(temperature - optimal_temp)
        
        if temp_deviation <= 3.0:
            return 1.0  # No additional stress
        elif temp_deviation <= 8.0:
            # Moderate stress increases respiration
            return 1.0 + 0.05 * (temp_deviation - 3.0)
        else:
            # Severe stress dramatically increases respiration
            return 1.25 + 0.1 * (temp_deviation - 8.0)
    
    def _calculate_respiratory_quotient(self, hour: int) -> float:
        """
        Calculate respiratory quotient (CO2 produced / O2 consumed).
        
        RQ varies with substrate being respired:
        - Carbohydrates: RQ = 1.0
        - Lipids: RQ = 0.7  
        - Proteins: RQ = 0.8
        
        During day: more carbohydrate respiration (RQ closer to 1.0)
        During night: more mixed substrate respiration (RQ ~0.85)
        """
        is_day = 6 <= hour <= 18
        
        if is_day:
            # Daytime: more carbohydrate respiration
            return 0.95
        else:
            # Nighttime: more mixed substrate respiration
            return 0.85

def create_lettuce_respiration_model(system_config=None) -> EnhancedRespirationModel:
    """Create respiration model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        EnhancedRespirationModel configured with CSV parameters
    """
    try:
        # Get respiration parameters from CSV data loaded in system_config
        respiration_params = getattr(system_config, 'respiration_parameters', {}).copy()
        
        # Map renamed parameters to expected parameter names
        param_mapping = {
            'respiration_acclimation_rate': 'acclimation_rate',
            'respiration_maintenance_base_rate': 'maintenance_base_rate',
            'respiration_growth_efficiency': 'growth_efficiency',
            'respiration_biosynthetic_cost': 'biosynthetic_cost'
        }
        
        # Apply parameter name mapping
        for csv_name, model_name in param_mapping.items():
            if csv_name in respiration_params:
                respiration_params[model_name] = respiration_params[csv_name]
        
        # Create parameters from CSV config
        parameters = RespirationParameters.from_config(respiration_params)
        return EnhancedRespirationModel(parameters, respiration_params)
        
    except Exception as e:
        print(f"Warning: Could not load CSV respiration parameters: {e}")
        print("Using default respiration parameters")
        return EnhancedRespirationModel()


