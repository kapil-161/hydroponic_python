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
    
    # Temperature stress parameters
    max_temperature_threshold: float  # Maximum temperature before protein denaturation
    temperature_decay_factor: float   # Decay factor for high temperature respiration
    
    # Size penalty parameters
    size_penalty_threshold: float     # Biomass threshold for size penalty
    size_penalty_rate: float          # Rate of size penalty increase
    
    # Carbon conversion parameters
    glucose_to_carbon_ratio: float    # Glucose to carbon conversion ratio
    
    # History parameters
    min_history_threshold: int        # Minimum temperature history for acclimation
    
    # Day/night cycle parameters
    day_start_hour: int               # Start hour of day
    day_end_hour: int                 # End hour of day
    day_respiration_factor: float     # Day respiration factor
    night_respiration_factor: float   # Night respiration factor
    
    # CO2 conversion parameters
    carbon_to_co2_ratio: float       # Carbon to CO2 conversion ratio
    
    # Circadian rhythm parameters
    circadian_amplitude_1: float     # Amplitude of first circadian peak
    circadian_peak_1: int            # Hour of first circadian peak
    circadian_amplitude_2: float     # Amplitude of second circadian peak
    circadian_peak_2: int            # Hour of second circadian peak
    diurnal_base_factor: float       # Base factor for diurnal variation
    
    # Temperature stress parameters
    optimal_temperature: float        # Optimal temperature for respiration
    moderate_stress_threshold: float  # Temperature threshold for moderate stress
    severe_stress_threshold: float    # Temperature threshold for severe stress
    moderate_stress_factor: float     # Factor for moderate stress
    severe_stress_base: float         # Base factor for severe stress
    severe_stress_factor: float       # Factor for severe stress
    
    # Respiratory quotient parameters
    daytime_respiratory_quotient: float  # RQ during daytime
    nighttime_respiratory_quotient: float  # RQ during nighttime
    
    # Biosynthetic costs (for growth respiration)
    biosynthetic_costs: Dict[str, float]
    
    # Temperature acclimation bounds
    min_acclimation_temperature: float  # Minimum temperature for acclimation
    max_acclimation_temperature: float  # Maximum temperature for acclimation
    
    # Diurnal factor limits
    min_diurnal_factor: float  # Minimum diurnal respiration factor
    max_diurnal_factor: float  # Maximum diurnal respiration factor
    
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
        
        # Handle biosynthetic costs from CSV
        biosynthetic_costs = {
            'protein': get_required_param('protein_respiration_cost'),
            'carbohydrate': get_required_param('carbohydrate_respiration_cost'),
            'lipid': get_required_param('lipid_respiration_cost'),
            'organic_acid': get_required_param('organic_acid_respiration_cost'),
            'lignin': get_required_param('lignin_respiration_cost')
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
            reference_leaf_n=get_required_param('reference_leaf_n'),
            
            # Temperature stress parameters
            max_temperature_threshold=get_required_param('max_temperature_threshold'),
            temperature_decay_factor=get_required_param('temperature_decay_factor'),
            
            # Size penalty parameters
            size_penalty_threshold=get_required_param('size_penalty_threshold'),
            size_penalty_rate=get_required_param('size_penalty_rate'),
            
            # Carbon conversion parameters
            glucose_to_carbon_ratio=get_required_param('glucose_to_carbon_ratio'),
            
            # History parameters
            min_history_threshold=get_required_param('min_history_threshold'),
            
            # Day/night cycle parameters
            day_start_hour=get_required_param('day_start_hour'),
            day_end_hour=get_required_param('day_end_hour'),
            day_respiration_factor=get_required_param('day_respiration_factor'),
            night_respiration_factor=get_required_param('night_respiration_factor'),
            
            # CO2 conversion parameters
            carbon_to_co2_ratio=get_required_param('carbon_to_co2_ratio'),
            
            # Circadian rhythm parameters
            circadian_amplitude_1=get_required_param('circadian_amplitude_1'),
            circadian_peak_1=get_required_param('circadian_peak_1'),
            circadian_amplitude_2=get_required_param('circadian_amplitude_2'),
            circadian_peak_2=get_required_param('circadian_peak_2'),
            diurnal_base_factor=get_required_param('diurnal_base_factor'),
            
            # Temperature stress parameters
            optimal_temperature=get_required_param('optimal_temperature'),
            moderate_stress_threshold=get_required_param('moderate_stress_threshold'),
            severe_stress_threshold=get_required_param('severe_stress_threshold'),
            moderate_stress_factor=get_required_param('moderate_stress_factor'),
            severe_stress_base=get_required_param('severe_stress_base'),
            severe_stress_factor=get_required_param('severe_stress_factor'),
            
            # Respiratory quotient parameters
            daytime_respiratory_quotient=get_required_param('daytime_respiratory_quotient'),
            nighttime_respiratory_quotient=get_required_param('nighttime_respiratory_quotient'),
            
            # Biosynthetic costs (for growth respiration)
            biosynthetic_costs=biosynthetic_costs,
            
            # Temperature acclimation bounds
            min_acclimation_temperature=get_required_param('min_acclimation_temperature'),
            max_acclimation_temperature=get_required_param('max_acclimation_temperature'),
            
            # Diurnal factor limits
            min_diurnal_factor=get_required_param('min_diurnal_factor'),
            max_diurnal_factor=get_required_param('max_diurnal_factor')
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
        if parameters is None:
            raise ValueError("❌ RespirationParameters required - no hardcoded defaults allowed")
        if config_dict is None:
            raise ValueError("❌ Configuration dictionary required - no hardcoded defaults allowed")
        
        self.params = parameters
        self.config_dict = config_dict
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
        from utils.temperature_utils import calculate_q10_temperature_factor
        
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
        from utils.temperature_utils import sanitize_temperature
        temp = sanitize_temperature(temperature)
        if temp > self.params.max_temperature_threshold:
            # Protein denaturation effects
            excess_temp = temp - self.params.max_temperature_threshold
            factor *= np.exp(-self.params.temperature_decay_factor * excess_temp)
        
        return factor
    
    def calculate_age_factor(self, age_days: float) -> float:
        """
        Calculate age effect on maintenance respiration.
        
        Args:
            age_days: Age of tissue in days
            
        Returns:
            Age factor (1.0 for young tissue)
        """
        # from utils.math_utils import clamp_value  # Module deleted

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
        # from utils.math_utils import safe_divide  # Module deleted
        
        if tissue_type != TissueType.LEAVES:
            return 1.0  # N effects mainly in leaves
        
        if self.params.reference_leaf_n == 0:
            raise ValueError("❌ Reference leaf nitrogen content must be provided in CSV configuration - no hardcoded defaults allowed")
        n_ratio = nitrogen_content / self.params.reference_leaf_n
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
        dry_weight = getattr(biomass_pool, 'dry_mass', None)
        if dry_weight is None:
            dry_weight = getattr(biomass_pool, 'dry_weight', None)
        if dry_weight is None:
            raise ValueError("❌ Biomass pool must have dry_mass or dry_weight attribute - no hardcoded defaults allowed")
        if dry_weight > self.params.size_penalty_threshold:  # Above normal lettuce size
            excess_mass = dry_weight - self.params.size_penalty_threshold
            # Exponential penalty for maintaining excessive biomass
            size_penalty_factor = 1.0 + self.params.size_penalty_rate * excess_mass  # Configurable penalty rate
        
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
            growth_composition = self.params.get_required_growth_composition(self.config_dict)
        
        # Detailed approach based on biochemical composition (now the default)
        if growth_composition is not None:
            # Get biosynthetic costs from CSV configuration - no hardcoded defaults allowed
            if not hasattr(self.params, 'biosynthetic_costs'):
                raise ValueError("❌ Biosynthetic costs must be provided in CSV configuration - no hardcoded defaults allowed")
            
            costs = self.params.biosynthetic_costs
            
            total_glucose_cost = 0.0
            for component, fraction in growth_composition.items():
                cost = costs.get(component)
                if cost is None:
                    raise ValueError(f"❌ Respiration cost for {component} must be provided in CSV configuration - no hardcoded defaults allowed")
                total_glucose_cost += cost * fraction * new_growth
            
            glucose_respired = total_glucose_cost * (1.0 - self.params.growth_efficiency)
            carbon_respired = glucose_respired * self.params.glucose_to_carbon_ratio
            
        else:
            # Fallback to simple approach only if no composition data available
            growth_cost = self.params.biosynthetic_cost  # g glucose/g biomass
            growth_efficiency = self.params.growth_efficiency
            
            # Growth respiration = biosynthetic cost * (1 - efficiency) * new growth
            glucose_required = growth_cost * new_growth
            glucose_respired = glucose_required * (1.0 - growth_efficiency)
            
            # Convert glucose to carbon (glucose = C6H12O6, MW = 180, C content = 40%)
            carbon_respired = glucose_respired * self.params.glucose_to_carbon_ratio
        
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
        if len(self.temperature_history) >= self.params.min_history_threshold:  # Need some history
            recent_avg_temp = np.mean(self.temperature_history)
            
            # Gradual acclimation towards recent average
            temp_diff = recent_avg_temp - self.acclimated_reference_temp
            acclimation_change = temp_diff * self.params.acclimation_rate
            
            self.acclimated_reference_temp += acclimation_change
            
            # Keep within reasonable bounds from CSV configuration
            # from utils.math_utils import clamp_value  # Module deleted
            min_temp = getattr(self.params, 'min_acclimation_temperature', None)
            max_temp = getattr(self.params, 'max_acclimation_temperature', None)
            
            if min_temp is None or max_temp is None:
                raise ValueError("❌ Temperature acclimation bounds (min_acclimation_temperature, max_acclimation_temperature) must be provided in CSV configuration")

            self.acclimated_reference_temp = max(min_temp, min(max_temp, self.acclimated_reference_temp))
    
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
        is_day = self.params.day_start_hour <= hour <= self.params.day_end_hour  # Configurable day/night cycle
        day_night_factor = self.params.day_respiration_factor if is_day else self.params.night_respiration_factor  # Configurable factors
        
        # Combined hourly adjustment
        hourly_adjustment = diurnal_factor * day_night_factor
        
        # Calculate temperature-dependent adjustments  
        temp_stress_factor = self._calculate_temperature_stress_factor(temperature)
        
        # Final hourly respiration rates
        adjusted_maintenance = hourly_maintenance * hourly_adjustment * temp_stress_factor
        adjusted_growth = hourly_growth * hourly_adjustment * temp_stress_factor  # Fix: apply temp_stress_factor
        adjusted_total = adjusted_maintenance + adjusted_growth
        
        # Calculate carbon cost (CO2 release)
        # Respiration releases CO2: C6H12O6 + 6O2 → 6CO2 + 6H2O
        # 1 g C respired → configurable g CO2 released
        co2_release_rate = adjusted_total * self.params.carbon_to_co2_ratio  # g CO2/hour
        
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
        circadian_component1 = self.params.circadian_amplitude_1 * np.sin(2 * np.pi * (hour - self.params.circadian_peak_1) / 24)  # 4 AM peak
        circadian_component2 = self.params.circadian_amplitude_2 * np.sin(2 * np.pi * (hour - self.params.circadian_peak_2) / 24)  # 4 PM peak
        
        # Base respiration varies from configurable range throughout day
        diurnal_factor = self.params.diurnal_base_factor + circadian_component1 + circadian_component2
        
        # Apply limits from CSV configuration - no hardcoded defaults allowed
        min_factor = getattr(self.params, 'min_diurnal_factor', None)
        max_factor = getattr(self.params, 'max_diurnal_factor', None)
        
        if min_factor is None or max_factor is None:
            raise ValueError("❌ Diurnal factor limits (min_diurnal_factor, max_diurnal_factor) must be provided in CSV configuration")
        
        return max(min_factor, min(max_factor, diurnal_factor))
    
    def _calculate_temperature_stress_factor(self, temperature: float) -> float:
        """
        Calculate additional temperature stress effects on respiration.
        
        Beyond the Q10 response, extreme temperatures can cause additional stress.
        """
        optimal_temp = self.params.optimal_temperature  # °C optimal temperature for lettuce
        temp_deviation = abs(temperature - optimal_temp)
        
        if temp_deviation <= self.params.moderate_stress_threshold:
            return 1.0  # No additional stress
        elif temp_deviation <= self.params.severe_stress_threshold:
            # Moderate stress increases respiration
            return 1.0 + self.params.moderate_stress_factor * (temp_deviation - self.params.moderate_stress_threshold)
        else:
            # Severe stress dramatically increases respiration
            return self.params.severe_stress_base + self.params.severe_stress_factor * (temp_deviation - self.params.severe_stress_threshold)
    
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
        is_day = self.params.day_start_hour <= hour <= self.params.day_end_hour
        
        if is_day:
            # Daytime: more carbohydrate respiration
            return self.params.daytime_respiratory_quotient
        else:
            # Nighttime: more mixed substrate respiration
            return self.params.nighttime_respiratory_quotient

def create_lettuce_respiration_model(system_config=None) -> EnhancedRespirationModel:
    """Create respiration model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        EnhancedRespirationModel configured with CSV parameters
        
    Raises:
        ValueError: If required CSV parameters are missing
    """
    if not system_config:
        raise ValueError("❌ System configuration must be provided for respiration model")
    
    try:
        # Get respiration parameters from CSV data loaded in system_config
        respiration_params = getattr(system_config, 'respiration_parameters', {})
        if not respiration_params:
            raise ValueError("❌ Respiration parameters must be provided in CSV configuration for respiration model")
        
        # Get environment parameters for temperature-related values
        environment_params = getattr(system_config, 'environment', {})
        
        # Add environment parameters that respiration model needs
        if 'optimal_temperature' in environment_params:
            respiration_params['optimal_temperature'] = environment_params['optimal_temperature']
        
        # Get model constants for growth composition fractions
        model_constants = getattr(system_config, 'model_constants', {})
        
        # Add growth composition fractions from model_constants to respiration_params
        composition_params = ['protein_fraction', 'carbohydrate_fraction', 'lipid_fraction', 
                            'organic_acid_fraction', 'lignin_fraction']
        for param in composition_params:
            if param in model_constants:
                respiration_params[param] = model_constants[param]
        
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
        
    except KeyError as e:
        raise KeyError(f"Required respiration parameter '{e.args[0]}' not found in CSV configuration. Add to respiration_parameters section")
    except Exception as e:
        raise ValueError(f"Failed to create respiration model from CSV configuration: {e}")


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file models plant respiration - the process where plants "breathe" by consuming their own 
sugar and oxygen to power cellular activities. Think of it as the plant's metabolism or energy 
consumption system, like how humans burn calories to stay alive and active.

KEY FUNCTIONS AND EQUATIONS:

1. calculate_maintenance_respiration()
   - What it does: Calculates energy needed just to keep plant tissues alive
   - Equation: respiration = base_rate × biomass × temp_factor × age_factor × tissue_factor
   - Real-world meaning: Like your body's resting metabolic rate - energy needed just to 
     keep cells alive, maintain proteins, and replace damaged parts. Older tissues need 
     more maintenance, like an old car needing more repairs.

2. calculate_growth_respiration()
   - What it does: Calculates energy cost of building new plant tissues
   - Equations:
     * Simple: growth_respiration = biosynthetic_cost × (1 - efficiency) × new_growth
     * Detailed: growth_respiration = Σ(component_cost × fraction × new_growth)
   - Real-world meaning: Like the extra calories you burn when building muscle. Making 
     new proteins, cell walls, and other components requires energy beyond just maintenance.

3. calculate_temperature_factor()
   - What it does: Calculates how temperature affects metabolic rate
   - Equation: factor = Q10^((temperature - reference) / 10)
   - Real-world meaning: Warmer = faster metabolism, colder = slower metabolism. Like how 
     you're more active on warm days vs cold days. Q10 = 2 means doubling rate every 10°C.

4. calculate_age_factor()
   - What it does: Shows how respiration increases as tissues age
   - Equation: factor = 1.0 + (age_coefficient × age_days)
   - Real-world meaning: Older tissues are less efficient and require more energy maintenance. 
     Like how older machines need more energy to do the same work.

5. hourly_update()
   - What it does: Calculates hourly respiration rates with diurnal (day/night) variation
   - Real-world meaning: Plant respiration varies throughout the day - higher during day 
     when plants are active, lower at night when they're "resting."

6. _calculate_diurnal_respiration_factor()
   - What it does: Models natural daily rhythm in respiration rates
   - Equation: Uses sine waves with peaks at ~4 AM and ~4 PM
   - Real-world meaning: Plants have internal clocks (circadian rhythms) that control 
     metabolism. Respiration peaks don't match photosynthesis peaks.

KEY RESPIRATION CONCEPTS:

TWO TYPES OF RESPIRATION:
- Maintenance: Keeping existing cells alive (like paying rent)
- Growth: Building new tissues (like construction costs)

TEMPERATURE EFFECTS:
- Q10 = 2: Rate doubles every 10°C increase
- Too hot: Enzymes break down, respiration becomes inefficient
- Too cold: Everything slows down dramatically

TISSUE-SPECIFIC RATES:
- Leaves: High respiration (active metabolism)
- Stems: Medium respiration (transport and support)
- Roots: Medium respiration (active uptake)
- Reproductive parts: Very high respiration (rapid development)

RESPIRATORY QUOTIENT (RQ):
- RQ = CO2 produced / O2 consumed
- Carbohydrates: RQ = 1.0
- Fats: RQ = 0.7
- Proteins: RQ = 0.8
- Varies by time of day and substrate being used

ENVIRONMENTAL INTERACTIONS:
- High EC stress: Increases energy cost of maintenance
- Water stress: Forces more energy into osmoregulation
- Size penalties: Large plants have disproportionately high maintenance costs

PRACTICAL APPLICATIONS:
- Calculate daily carbon budget (photosynthesis - respiration = net gain)
- Optimize temperature for maximum growth efficiency
- Predict energy costs of different management strategies
- Understand why plants grow slower at temperature extremes
- Design climate control to minimize energy waste
- Time harvests when daily net carbon gain starts declining

This system helps growers understand the "energy economics" of plant growth - balancing 
energy production (photosynthesis) against energy consumption (respiration) for maximum 
net productivity.
"""


