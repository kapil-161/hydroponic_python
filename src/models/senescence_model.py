"""
Advanced Senescence Model for Hydroponic Crop Simulation
Based on CROPGRO SENES.for and plant senescence research

Key concepts implemented:
1. Multiple senescence triggers (age, stress, shading, developmental)
2. Nutrient remobilization during senescence
3. Tissue-specific senescence rates
4. Environmental stress-induced senescence
5. Gradual vs. rapid senescence pathways
6. Senescence recovery under favorable conditions

Research basis:
- Gregersen et al. (2013) - Plant senescence and crop productivity
- Masclaux-Daubresse et al. (2010) - Nitrogen remobilization during senescence
- Lim et al. (2007) - Leaf senescence
- Bleecker & Patterson (1997) - Last exit: senescence, abscission and meristem arrest
"""

import numpy as np
from typing import Dict, Tuple, Any, List
from dataclasses import dataclass
from enum import Enum


class SenescenceType(Enum):
    """Types of senescence triggers."""
    AGE_BASED = "age_based"                   # Natural aging
    WATER_STRESS = "water_stress"             # Drought-induced
    NITROGEN_STRESS = "nitrogen_stress"       # N deficiency-induced
    TEMPERATURE_STRESS = "temperature_stress" # Heat/cold-induced
    LIGHT_STRESS = "light_stress"             # Shading-induced
    DEVELOPMENTAL = "developmental"           # Reproductive priority
    PATHOGEN = "pathogen"                     # Disease-induced
    MECHANICAL = "mechanical"                 # Physical damage


class SenescenceStage(Enum):
    """Stages of senescence progression."""
    HEALTHY = "healthy"                       # No senescence
    EARLY_SENESCENCE = "early_senescence"     # Initial signs
    ACTIVE_SENESCENCE = "active_senescence"   # Rapid senescence
    LATE_SENESCENCE = "late_senescence"       # Near death
    DEAD = "dead"                            # Tissue death


@dataclass
class SenescenceParameters:
    """Parameters for senescence model."""
    
    # Age-based senescence
    natural_lifespan_gdd: float       # GDD for natural leaf lifespan
    age_senescence_rate: float        # Daily senescence rate when old
    
    # Stress-induced senescence thresholds
    water_stress_threshold: float       # Below this triggers senescence
    nitrogen_stress_threshold: float    # Below this triggers senescence
    temperature_stress_threshold: float # Below this triggers senescence
    light_stress_threshold: float       # Below this triggers senescence
    
    # Stress senescence rates
    water_stress_rate: float          # Daily rate under water stress
    nitrogen_stress_rate: float       # Daily rate under N stress
    temperature_stress_rate: float    # Daily rate under temp stress
    light_stress_rate: float          # Daily rate under light stress
    
    # Senescence progression
    early_senescence_threshold: float  # Tissue damage to trigger early senescence
    active_senescence_threshold: float # Tissue damage for active senescence
    late_senescence_threshold: float   # Tissue damage for late senescence
    death_threshold: float             # Tissue damage for death
    
    # Nutrient remobilization efficiency
    remobilization_efficiency: Dict[str, float]
    
    # Recovery parameters
    recovery_rate: float              # Daily recovery rate under good conditions
    max_recovery: float                 # Maximum recovery from senescence damage
    
    # Developmental senescence
    reproductive_priority_factor: float  # Senescence acceleration during reproduction
    lower_canopy_factor: float          # Senescence acceleration for shaded leaves
    
    # Advanced senescence parameters
    active_senescence_multiplier: float  # Multiplier for active senescence remobilization
    normal_senescence_multiplier: float  # Multiplier for normal senescence remobilization
    stress_history_days: int             # Number of days to keep stress history
    daily_area_loss_factor: float        # Daily area loss factor during senescence
    daily_biomass_loss_factor: float     # Daily biomass loss factor during senescence
    
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'SenescenceParameters':
        """Create SenescenceParameters from CSV configuration data.
        
        Args:
            config_dict: Dictionary containing senescence parameters from CSV files
        """
        # Handle remobilization efficiency from CSV
        remob_eff = config_dict.get('remobilization_efficiency', {})
        if not remob_eff:
            # Build from individual CSV parameters
            remob_eff = {
                'nitrogen': config_dict['nitrogen_recovery'],
                'phosphorus': config_dict['phosphorus_recovery'],
                'potassium': config_dict['potassium_recovery'],
                'magnesium': config_dict['magnesium_recovery'],
                'sulfur': config_dict['sulfur_recovery'],
                'calcium': config_dict['calcium_recovery'],
                'iron': config_dict['iron_recovery'],
                'manganese': config_dict['manganese_recovery'],
                'zinc': config_dict['zinc_recovery'],
                'copper': config_dict['copper_recovery'],
                'boron': config_dict['boron_recovery'],
                'molybdenum': config_dict['molybdenum_recovery']
            }
        
        return cls(
            # Age-based senescence parameters
            natural_lifespan_gdd=config_dict['natural_lifespan_gdd'],
            age_senescence_rate=config_dict['age_senescence_rate'],
            
            # Stress-induced senescence thresholds
            water_stress_threshold=config_dict['water_stress_threshold'],
            nitrogen_stress_threshold=config_dict['nitrogen_stress_threshold'],
            temperature_stress_threshold=config_dict['temperature_stress_threshold'],
            light_stress_threshold=config_dict['light_stress_threshold'],
            
            # Stress senescence rates
            water_stress_rate=config_dict['water_stress_rate'],
            nitrogen_stress_rate=config_dict['nitrogen_stress_rate'],
            temperature_stress_rate=config_dict['temperature_stress_rate'],
            light_stress_rate=config_dict['light_stress_rate'],
            
            # Senescence progression thresholds
            early_senescence_threshold=config_dict['early_senescence_threshold'],
            active_senescence_threshold=config_dict['active_senescence_threshold'],
            late_senescence_threshold=config_dict['late_senescence_threshold'],
            death_threshold=config_dict['death_threshold'],
            
            # Nutrient remobilization efficiency
            remobilization_efficiency=remob_eff,
            
            # Recovery parameters
            recovery_rate=config_dict['recovery_rate'],
            max_recovery=config_dict['max_recovery'],
            
            # Developmental senescence
            reproductive_priority_factor=config_dict['reproductive_priority_factor'],
            lower_canopy_factor=config_dict['lower_canopy_factor'],
            
            # Advanced senescence parameters
            active_senescence_multiplier=config_dict['active_senescence_multiplier'],
            normal_senescence_multiplier=config_dict['normal_senescence_multiplier'],
            stress_history_days=int(config_dict['stress_history_days']),  # Ensure integer for slicing
            daily_area_loss_factor=config_dict['daily_area_loss_factor'],
            daily_biomass_loss_factor=config_dict['daily_biomass_loss_factor']
        )


@dataclass
class LeafCohortSenescence:
    """Senescence state for a leaf cohort."""
    cohort_id: int
    age_gdd: float = 0.0                      # Age in growing degree days
    senescence_damage: float = 0.0            # Cumulative senescence damage (0-1)
    senescence_stage: SenescenceStage = SenescenceStage.HEALTHY
    active_senescence_types: List[SenescenceType] = None
    daily_senescence_rate: float = 0.0        # Current daily senescence rate
    nutrient_content: Dict[str, float] = None # Nutrient content (g nutrient/g biomass)
    remobilizable_nutrients: Dict[str, float] = None  # Available for remobilization
    is_recoverable: bool = True               # Whether senescence can be reversed
    
    def __post_init__(self):
        if self.active_senescence_types is None:
            self.active_senescence_types = []
        if self.nutrient_content is None:
            self.nutrient_content = {}
        if self.remobilizable_nutrients is None:
            self.remobilizable_nutrients = {}


@dataclass
class SenescenceResponse:
    """Daily senescence calculation results."""
    cohort_responses: Dict[int, LeafCohortSenescence]
    total_senescence_rate: float              # Total daily senescence across all cohorts
    remobilized_nutrients: Dict[str, float]   # Total nutrients remobilized (g/day)
    senesced_area: float                      # Total leaf area lost (m²/day)
    senesced_biomass: float                   # Total biomass lost (g/day)
    active_senescence_types: List[SenescenceType]
    average_senescence_stage: SenescenceStage


class AdvancedSenescenceModel:
    """
    Advanced senescence model following CROPGRO principles.
    
    Handles multiple senescence triggers, nutrient remobilization,
    and recovery under favorable conditions.
    """
    
    def __init__(self, parameters: SenescenceParameters):
        self.params = parameters
        self.cohort_states: Dict[int, LeafCohortSenescence] = {}
        self.stress_history: Dict[str, List[float]] = {
            'water': [],
            'nitrogen': [],
            'temperature': [],
            'light': []
        }
        self.remobilization_pool: Dict[str, float] = {}
        
    def initialize_cohort(self, cohort_id: int, initial_nutrient_content: Dict[str, float]):
        """
        Initialize senescence tracking for a new leaf cohort.
        
        Args:
            cohort_id: Unique identifier for the cohort
            initial_nutrient_content: Initial nutrient content (g nutrient/g biomass)
        """
        self.cohort_states[cohort_id] = LeafCohortSenescence(
            cohort_id=cohort_id,
            nutrient_content=initial_nutrient_content.copy(),
            remobilizable_nutrients={}
        )
        
        # Calculate initial remobilizable nutrients
        for nutrient, content in initial_nutrient_content.items():
            if nutrient in self.params.remobilization_efficiency:
                efficiency = self.params.remobilization_efficiency[nutrient]
                self.cohort_states[cohort_id].remobilizable_nutrients[nutrient] = content * efficiency
    
    def calculate_age_senescence(self, cohort_state: LeafCohortSenescence) -> float:
        """
        Calculate age-based senescence rate.
        
        Args:
            cohort_state: Current cohort senescence state
            
        Returns:
            Daily senescence rate due to age
        """
        if cohort_state.age_gdd <= self.params.natural_lifespan_gdd:
            return 0.0
        
        # Exponential increase in senescence rate with age
        excess_age = cohort_state.age_gdd - self.params.natural_lifespan_gdd
        age_factor = 1.0 + (excess_age / 100.0)  # Increase rate with extreme age
        
        return self.params.age_senescence_rate * age_factor
    
    def calculate_stress_senescence(self, water_stress: float, nitrogen_stress: float,
                                  temperature_stress: float, light_stress: float) -> Dict[str, float]:
        """
        Calculate stress-induced senescence rates.
        
        Args:
            water_stress: Water stress level (0-1, 1=no stress)
            nitrogen_stress: Nitrogen stress level (0-1, 1=no stress)
            temperature_stress: Temperature stress level (0-1, 1=no stress)
            light_stress: Light stress level (0-1, 1=no stress)
            
        Returns:
            Dictionary of stress-specific senescence rates
        """
        stress_rates = {}
        
        # Water stress senescence
        if water_stress < self.params.water_stress_threshold:
            stress_intensity = (self.params.water_stress_threshold - water_stress) / self.params.water_stress_threshold
            stress_rates['water'] = self.params.water_stress_rate * stress_intensity
        else:
            stress_rates['water'] = 0.0
        
        # Nitrogen stress senescence
        if nitrogen_stress < self.params.nitrogen_stress_threshold:
            stress_intensity = (self.params.nitrogen_stress_threshold - nitrogen_stress) / self.params.nitrogen_stress_threshold
            stress_rates['nitrogen'] = self.params.nitrogen_stress_rate * stress_intensity
        else:
            stress_rates['nitrogen'] = 0.0
        
        # Temperature stress senescence
        if temperature_stress < self.params.temperature_stress_threshold:
            stress_intensity = (self.params.temperature_stress_threshold - temperature_stress) / self.params.temperature_stress_threshold
            stress_rates['temperature'] = self.params.temperature_stress_rate * stress_intensity
        else:
            stress_rates['temperature'] = 0.0
        
        # Light stress senescence
        if light_stress < self.params.light_stress_threshold:
            stress_intensity = (self.params.light_stress_threshold - light_stress) / self.params.light_stress_threshold
            stress_rates['light'] = self.params.light_stress_rate * stress_intensity
        else:
            stress_rates['light'] = 0.0
        
        return stress_rates
    
    def calculate_developmental_senescence(self, is_reproductive: bool, 
                                         canopy_position: float) -> float:
        """
        Calculate developmental senescence rate.
        
        Args:
            is_reproductive: Whether plant is in reproductive stage
            canopy_position: Position in canopy (0=bottom, 1=top)
            
        Returns:
            Developmental senescence rate
        """
        dev_rate = 0.0
        
        # Reproductive priority senescence
        if is_reproductive:
            dev_rate += self.params.age_senescence_rate * (self.params.reproductive_priority_factor - 1.0)
        
        # Lower canopy senescence (shading effect)
        if canopy_position < 0.5:  # Lower half of canopy
            shading_factor = (0.5 - canopy_position) * 2.0  # 0-1 scale
            dev_rate += self.params.age_senescence_rate * shading_factor * (self.params.lower_canopy_factor - 1.0)
        
        return dev_rate
    
    def calculate_recovery_rate(self, cohort_state: LeafCohortSenescence,
                               current_stress_levels: Dict[str, float]) -> float:
        """
        Calculate senescence recovery rate under favorable conditions.
        
        Args:
            cohort_state: Current cohort senescence state
            current_stress_levels: Current stress levels for all stress types
            
        Returns:
            Daily recovery rate (negative senescence rate)
        """
        if not cohort_state.is_recoverable or cohort_state.senescence_damage > self.params.max_recovery:
            return 0.0
        
        # Check if conditions are favorable for recovery
        all_stress_low = all(stress > 0.8 for stress in current_stress_levels.values())
        
        if all_stress_low and cohort_state.senescence_stage in [SenescenceStage.EARLY_SENESCENCE]:
            # Recovery possible only in early stages and under good conditions
            max_recovery_rate = min(self.params.recovery_rate, 
                                  cohort_state.senescence_damage * 0.1)  # 10% of damage per day max
            return max_recovery_rate
        
        return 0.0
    
    def update_senescence_stage(self, cohort_state: LeafCohortSenescence):
        """
        Update senescence stage based on accumulated damage.
        
        Args:
            cohort_state: Cohort senescence state to update
        """
        damage = cohort_state.senescence_damage
        
        if damage >= self.params.death_threshold:
            cohort_state.senescence_stage = SenescenceStage.DEAD
            cohort_state.is_recoverable = False
        elif damage >= self.params.late_senescence_threshold:
            cohort_state.senescence_stage = SenescenceStage.LATE_SENESCENCE
            cohort_state.is_recoverable = False
        elif damage >= self.params.active_senescence_threshold:
            cohort_state.senescence_stage = SenescenceStage.ACTIVE_SENESCENCE
        elif damage >= self.params.early_senescence_threshold:
            cohort_state.senescence_stage = SenescenceStage.EARLY_SENESCENCE
        else:
            cohort_state.senescence_stage = SenescenceStage.HEALTHY
    
    def calculate_nutrient_remobilization(self, cohort_state: LeafCohortSenescence,
                                        daily_senescence_rate: float) -> Dict[str, float]:
        """
        Calculate nutrient remobilization from senescing tissue.
        
        Args:
            cohort_state: Cohort senescence state
            daily_senescence_rate: Daily senescence rate
            
        Returns:
            Dictionary of remobilized nutrients (g/day)
        """
        remobilized = {}
        
        # Only remobilize during active senescence
        if daily_senescence_rate > 0 and cohort_state.senescence_stage != SenescenceStage.HEALTHY:
            for nutrient, available in cohort_state.remobilizable_nutrients.items():
                if available > 0:
                    # Remobilization rate depends on senescence rate and efficiency
                    efficiency = self.params.remobilization_efficiency.get(nutrient, None)
                    if efficiency is None:
                        raise ValueError(f"❌ Remobilization efficiency for {nutrient} must be provided in CSV configuration - no hardcoded defaults allowed")
                    
                    # More aggressive remobilization during active senescence
                    if cohort_state.senescence_stage == SenescenceStage.ACTIVE_SENESCENCE:
                        remob_rate = daily_senescence_rate * self.params.active_senescence_multiplier
                    else:
                        remob_rate = daily_senescence_rate * self.params.normal_senescence_multiplier
                    
                    daily_remobilization = available * remob_rate * efficiency
                    remobilized[nutrient] = daily_remobilization
                    
                    # Update available nutrients
                    cohort_state.remobilizable_nutrients[nutrient] = max(0.0, available - daily_remobilization)
        
        return remobilized
    
    def daily_update(self, cohort_data: Dict[int, Dict[str, Any]], 
                    environmental_stress: Dict[str, float],
                    developmental_state: Dict[str, Any]) -> SenescenceResponse:
        """
        Daily senescence update for all cohorts.
        
        Args:
            cohort_data: Dictionary with cohort info (age_gdd, area, biomass, etc.)
            environmental_stress: Current stress levels (water, nitrogen, temperature, light)
            developmental_state: Plant developmental information
            
        Returns:
            Complete senescence response
        """
        # Update stress history
        for stress_type, level in environmental_stress.items():
            if stress_type in self.stress_history:
                self.stress_history[stress_type].append(level)
                # Keep only recent history (configurable from CSV)
                if len(self.stress_history[stress_type]) > self.params.stress_history_days:
                    self.stress_history[stress_type] = self.stress_history[stress_type][-self.params.stress_history_days:]
        
        # Calculate stress senescence rates
        stress_rates = self.calculate_stress_senescence(
            environmental_stress.get('water', None),
            environmental_stress.get('nitrogen', None),
            environmental_stress.get('temperature', None),
            environmental_stress.get('light', None)
        )
        
        # Validate that all required stress values are provided
        for stress_type in ['water', 'nitrogen', 'temperature', 'light']:
            if environmental_stress.get(stress_type) is None:
                raise ValueError(f"❌ {stress_type.capitalize()} stress level must be provided in environmental conditions - no hardcoded defaults allowed")
        
        # Process each cohort
        total_senescence = 0.0
        total_remobilized = {}
        total_senesced_area = 0.0
        total_senesced_biomass = 0.0
        active_senescence_types = []
        stage_counts = {stage: 0 for stage in SenescenceStage}
        
        for cohort_id, data in cohort_data.items():
            # Initialize cohort if not exists
            if cohort_id not in self.cohort_states:
                initial_nutrients = data.get('nutrient_content')
                if initial_nutrients is None:
                    raise ValueError("❌ Initial nutrient content must be provided in CSV configuration - no hardcoded defaults allowed")
                self.initialize_cohort(cohort_id, initial_nutrients)
            
            cohort_state = self.cohort_states[cohort_id]
            
            # Update age
            age_gdd = data.get('age_gdd', None)
            if age_gdd is None:
                raise ValueError(f"❌ Age GDD for cohort {cohort_id} must be provided in cohort data - no hardcoded defaults allowed")
            cohort_state.age_gdd = age_gdd
            
            # Calculate different senescence components
            age_senescence = self.calculate_age_senescence(cohort_state)
            
            # Get developmental state
            is_reproductive = developmental_state.get('is_reproductive', None)
            if is_reproductive is None:
                raise ValueError("❌ Reproductive state must be provided in developmental state - no hardcoded defaults allowed")
            
            canopy_position = data.get('canopy_position', None)
            if canopy_position is None:
                raise ValueError(f"❌ Canopy position for cohort {cohort_id} must be provided in cohort data - no hardcoded defaults allowed")
            
            dev_senescence = self.calculate_developmental_senescence(
                is_reproductive,
                canopy_position
            )
            
            # Combine stress senescence rates
            stress_senescence = max(stress_rates.values()) if stress_rates else 0.0
            
            # Calculate recovery
            recovery_rate = self.calculate_recovery_rate(cohort_state, environmental_stress)
            
            # Total daily senescence rate
            total_daily_rate = age_senescence + dev_senescence + stress_senescence - recovery_rate
            total_daily_rate = max(0.0, total_daily_rate)  # Can't be negative
            
            cohort_state.daily_senescence_rate = total_daily_rate
            
            # Update senescence damage
            cohort_state.senescence_damage += total_daily_rate
            cohort_state.senescence_damage = min(1.0, max(0.0, cohort_state.senescence_damage))
            
            # Update senescence stage
            self.update_senescence_stage(cohort_state)
            
            # Track active senescence types
            cohort_state.active_senescence_types = []
            if age_senescence > 0:
                cohort_state.active_senescence_types.append(SenescenceType.AGE_BASED)
            if stress_rates.get('water', 0) > 0:
                cohort_state.active_senescence_types.append(SenescenceType.WATER_STRESS)
            if stress_rates.get('nitrogen', 0) > 0:
                cohort_state.active_senescence_types.append(SenescenceType.NITROGEN_STRESS)
            if stress_rates.get('temperature', 0) > 0:
                cohort_state.active_senescence_types.append(SenescenceType.TEMPERATURE_STRESS)
            if stress_rates.get('light', 0) > 0:
                cohort_state.active_senescence_types.append(SenescenceType.LIGHT_STRESS)
            if dev_senescence > 0:
                cohort_state.active_senescence_types.append(SenescenceType.DEVELOPMENTAL)
            
            # Calculate nutrient remobilization
            remobilized = self.calculate_nutrient_remobilization(cohort_state, total_daily_rate)
            
            # Accumulate totals
            cohort_area = data.get('area', None)
            if cohort_area is None:
                raise ValueError(f"❌ Area for cohort {cohort_id} must be provided in cohort data - no hardcoded defaults allowed")
            
            cohort_biomass = data.get('biomass', None)
            if cohort_biomass is None:
                raise ValueError(f"❌ Biomass for cohort {cohort_id} must be provided in cohort data - no hardcoded defaults allowed")
            
            total_senescence += total_daily_rate
            total_senesced_area += cohort_area * cohort_state.senescence_damage * self.params.daily_area_loss_factor
            total_senesced_biomass += cohort_biomass * cohort_state.senescence_damage * self.params.daily_biomass_loss_factor
            
            for nutrient, amount in remobilized.items():
                if nutrient not in total_remobilized:
                    total_remobilized[nutrient] = 0.0
                total_remobilized[nutrient] += amount
            
            active_senescence_types.extend(cohort_state.active_senescence_types)
            stage_counts[cohort_state.senescence_stage] += 1
        
        # Determine average senescence stage
        if stage_counts[SenescenceStage.DEAD] > 0:
            avg_stage = SenescenceStage.DEAD
        elif stage_counts[SenescenceStage.LATE_SENESCENCE] > 0:
            avg_stage = SenescenceStage.LATE_SENESCENCE
        elif stage_counts[SenescenceStage.ACTIVE_SENESCENCE] > 0:
            avg_stage = SenescenceStage.ACTIVE_SENESCENCE
        elif stage_counts[SenescenceStage.EARLY_SENESCENCE] > 0:
            avg_stage = SenescenceStage.EARLY_SENESCENCE
        else:
            avg_stage = SenescenceStage.HEALTHY
        
        # Store remobilized nutrients in pool
        for nutrient, amount in total_remobilized.items():
            if nutrient not in self.remobilization_pool:
                self.remobilization_pool[nutrient] = 0.0
            self.remobilization_pool[nutrient] += amount
        
        return SenescenceResponse(
            cohort_responses=self.cohort_states.copy(),
            total_senescence_rate=total_senescence,
            remobilized_nutrients=total_remobilized,
            senesced_area=total_senesced_area,
            senesced_biomass=total_senesced_biomass,
            active_senescence_types=list(set(active_senescence_types)),
            average_senescence_stage=avg_stage
        )
    
    def get_remobilization_pool(self) -> Dict[str, float]:
        """
        Get current remobilization pool.
        
        Returns:
            Dictionary of available remobilized nutrients
        """
        return self.remobilization_pool.copy()
    
def create_lettuce_senescence_model(system_config=None) -> AdvancedSenescenceModel:
    """Create senescence model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        AdvancedSenescenceModel configured with CSV parameters
    """
    try:
        # Get senescence parameters from CSV data loaded in system_config
        senescence_params = getattr(system_config, 'senescence_parameters', {})
        nitrogen_params = getattr(system_config, 'nitrogen_parameters', {})
        leaf_params = getattr(system_config, 'leaf_development_parameters', {})
        
        # Combine parameters from different CSV files
        config = {}
        
        # Add senescence parameters
        config.update(senescence_params)
        
        # Get stress thresholds from leaf development since they share the same values
        if 'water_stress_threshold' not in config and 'water_stress_threshold' in leaf_params:
            config['water_stress_threshold'] = leaf_params['water_stress_threshold']
        if 'nitrogen_stress_threshold' not in config and 'nitrogen_stress_threshold' in leaf_params:
            config['nitrogen_stress_threshold'] = leaf_params['nitrogen_stress_threshold']
        
        # Add nitrogen parameters that affect senescence
        if 'senescence_rate' in nitrogen_params:
            config['nitrogen_recovery'] = nitrogen_params['senescence_rate']
        
        # Create parameters from combined config
        parameters = SenescenceParameters.from_config(config)
        return AdvancedSenescenceModel(parameters)
        
    except Exception as e:
        raise ValueError(f"❌ Failed to load CSV senescence parameters: {e}. System requires CSV data - no hardcoded defaults allowed.")


