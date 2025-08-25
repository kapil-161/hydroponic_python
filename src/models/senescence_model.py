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
from typing import Dict, Tuple, Optional, Any, List
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
    natural_lifespan_gdd: float = 700.0       # GDD for natural leaf lifespan
    age_senescence_rate: float = 0.005        # Daily senescence rate when old
    
    # Stress-induced senescence thresholds
    water_stress_threshold: float = 0.4       # Below this triggers senescence
    nitrogen_stress_threshold: float = 0.5    # Below this triggers senescence
    temperature_stress_threshold: float = 0.6 # Below this triggers senescence
    light_stress_threshold: float = 0.3       # Below this triggers senescence
    
    # Stress senescence rates
    water_stress_rate: float = 0.015          # Daily rate under water stress
    nitrogen_stress_rate: float = 0.012       # Daily rate under N stress
    temperature_stress_rate: float = 0.020    # Daily rate under temp stress
    light_stress_rate: float = 0.008          # Daily rate under light stress
    
    # Senescence progression
    early_senescence_threshold: float = 0.05  # Tissue damage to trigger early senescence
    active_senescence_threshold: float = 0.20 # Tissue damage for active senescence
    late_senescence_threshold: float = 0.60   # Tissue damage for late senescence
    death_threshold: float = 0.90             # Tissue damage for death
    
    # Nutrient remobilization efficiency
    remobilization_efficiency: Dict[str, float] = None
    
    # Recovery parameters
    recovery_rate: float = 0.002              # Daily recovery rate under good conditions
    max_recovery: float = 0.1                 # Maximum recovery from senescence damage
    
    # Developmental senescence
    reproductive_priority_factor: float = 1.5  # Senescence acceleration during reproduction
    lower_canopy_factor: float = 1.2          # Senescence acceleration for shaded leaves
    
    def __post_init__(self):
        if self.remobilization_efficiency is None:
            # Default remobilization efficiencies for different nutrients
            self.remobilization_efficiency = {
                'nitrogen': 0.70,     # 70% of N can be remobilized
                'phosphorus': 0.60,   # 60% of P can be remobilized
                'potassium': 0.80,    # 80% of K can be remobilized
                'magnesium': 0.30,    # 30% of Mg can be remobilized
                'sulfur': 0.50,       # 50% of S can be remobilized
                'calcium': 0.05,      # 5% of Ca (mostly immobile)
                'iron': 0.10,         # 10% of Fe
                'manganese': 0.15,    # 15% of Mn
                'zinc': 0.20,         # 20% of Zn
                'copper': 0.15,       # 15% of Cu
                'boron': 0.05,        # 5% of B (immobile)
                'molybdenum': 0.25    # 25% of Mo
            }
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'SenescenceParameters':
        """Create SenescenceParameters from configuration dictionary."""
        remob_eff = config_dict.get('remobilization_efficiency', {})
        
        return cls(
            natural_lifespan_gdd=config_dict.get('natural_lifespan_gdd', 700.0),
            age_senescence_rate=config_dict.get('age_senescence_rate', 0.005),
            water_stress_threshold=config_dict.get('water_stress_threshold', 0.4),
            nitrogen_stress_threshold=config_dict.get('nitrogen_stress_threshold', 0.5),
            temperature_stress_threshold=config_dict.get('temperature_stress_threshold', 0.6),
            light_stress_threshold=config_dict.get('light_stress_threshold', 0.3),
            water_stress_rate=config_dict.get('water_stress_rate', 0.015),
            nitrogen_stress_rate=config_dict.get('nitrogen_stress_rate', 0.012),
            temperature_stress_rate=config_dict.get('temperature_stress_rate', 0.020),
            light_stress_rate=config_dict.get('light_stress_rate', 0.008),
            early_senescence_threshold=config_dict.get('early_senescence_threshold', 0.05),
            active_senescence_threshold=config_dict.get('active_senescence_threshold', 0.20),
            late_senescence_threshold=config_dict.get('late_senescence_threshold', 0.60),
            death_threshold=config_dict.get('death_threshold', 0.90),
            remobilization_efficiency=remob_eff if remob_eff else None,
            recovery_rate=config_dict.get('recovery_rate', 0.002),
            max_recovery=config_dict.get('max_recovery', 0.1),
            reproductive_priority_factor=config_dict.get('reproductive_priority_factor', 1.5),
            lower_canopy_factor=config_dict.get('lower_canopy_factor', 1.2)
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
    
    def __init__(self, parameters: Optional[SenescenceParameters] = None):
        self.params = parameters or SenescenceParameters()
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
                    efficiency = self.params.remobilization_efficiency.get(nutrient, 0.0)
                    
                    # More aggressive remobilization during active senescence
                    if cohort_state.senescence_stage == SenescenceStage.ACTIVE_SENESCENCE:
                        remob_rate = daily_senescence_rate * 2.0
                    else:
                        remob_rate = daily_senescence_rate
                    
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
                # Keep only recent history (7 days)
                if len(self.stress_history[stress_type]) > 7:
                    self.stress_history[stress_type] = self.stress_history[stress_type][-7:]
        
        # Calculate stress senescence rates
        stress_rates = self.calculate_stress_senescence(
            environmental_stress.get('water', 1.0),
            environmental_stress.get('nitrogen', 1.0),
            environmental_stress.get('temperature', 1.0),
            environmental_stress.get('light', 1.0)
        )
        
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
                initial_nutrients = data.get('nutrient_content', {
                    'nitrogen': 0.04,  # Default N content
                    'phosphorus': 0.01,
                    'potassium': 0.03
                })
                self.initialize_cohort(cohort_id, initial_nutrients)
            
            cohort_state = self.cohort_states[cohort_id]
            
            # Update age
            cohort_state.age_gdd = data.get('age_gdd', 0.0)
            
            # Calculate different senescence components
            age_senescence = self.calculate_age_senescence(cohort_state)
            
            dev_senescence = self.calculate_developmental_senescence(
                developmental_state.get('is_reproductive', False),
                data.get('canopy_position', 0.5)
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
            cohort_area = data.get('area', 0.0)
            cohort_biomass = data.get('biomass', 0.0)
            
            total_senescence += total_daily_rate
            total_senesced_area += cohort_area * cohort_state.senescence_damage * 0.1  # 10% of damaged area lost per day
            total_senesced_biomass += cohort_biomass * cohort_state.senescence_damage * 0.1
            
            for nutrient, amount in remobilized.items():
                total_remobilized[nutrient] = total_remobilized.get(nutrient, 0.0) + amount
            
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
            self.remobilization_pool[nutrient] = self.remobilization_pool.get(nutrient, 0.0) + amount
        
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
    
def create_lettuce_senescence_model(config=None) -> AdvancedSenescenceModel:
    """Create senescence model with lettuce-specific parameters."""
    try:
        if config is None:
            from ..utils.config_loader import get_config_loader
            config = get_config_loader()
        
        senescence_config = config.get_senescence_parameters()
        parameters = SenescenceParameters.from_config(senescence_config)
        return AdvancedSenescenceModel(parameters)
    except (ImportError, FileNotFoundError):
        # Fallback to default values if config loader not available
        return AdvancedSenescenceModel()


def demonstrate_senescence_model():
    """Demonstrate senescence model capabilities."""
    model = create_lettuce_senescence_model()
    
    print("=" * 80)
    print("ADVANCED SENESCENCE MODEL DEMONSTRATION")
    print("=" * 80)
    
    # Create test cohorts
    cohort_data = {
        1: {'age_gdd': 800, 'area': 0.005, 'biomass': 1.2, 'canopy_position': 0.8},  # Old, top
        2: {'age_gdd': 600, 'area': 0.004, 'biomass': 1.0, 'canopy_position': 0.5},  # Middle age, middle
        3: {'age_gdd': 400, 'area': 0.003, 'biomass': 0.8, 'canopy_position': 0.2},  # Young, bottom
    }
    
    # Simulate different stress scenarios
    scenarios = [
        ("Normal conditions", {'water': 1.0, 'nitrogen': 1.0, 'temperature': 1.0, 'light': 1.0}),
        ("Water stress", {'water': 0.3, 'nitrogen': 1.0, 'temperature': 1.0, 'light': 1.0}),
        ("Nitrogen stress", {'water': 1.0, 'nitrogen': 0.4, 'temperature': 1.0, 'light': 1.0}),
        ("Heat stress", {'water': 1.0, 'nitrogen': 1.0, 'temperature': 0.5, 'light': 1.0}),
        ("Shading stress", {'water': 1.0, 'nitrogen': 1.0, 'temperature': 1.0, 'light': 0.2}),
    ]
    
    developmental_state = {'is_reproductive': False}
    
    print(f"{'Scenario':<15} {'Total Sen.':<10} {'Remob. N':<9} {'Stage':<15} {'Active Types':<20}")
    print("-" * 80)
    
    for scenario_name, stress in scenarios:
        response = model.daily_update(cohort_data, stress, developmental_state)
        
        remob_n = response.remobilized_nutrients.get('nitrogen', 0.0)
        stage = response.average_senescence_stage.value
        active_types = [t.value.split('_')[0] for t in response.active_senescence_types[:3]]
        
        print(f"{scenario_name:<15} {response.total_senescence_rate:<10.3f} "
              f"{remob_n:<9.4f} {stage:<15} {', '.join(active_types):<20}")
    
    # Show cohort details
    print(f"\nCohort senescence details:")
    print(f"{'Cohort':<7} {'Age(GDD)':<9} {'Damage':<7} {'Stage':<15} {'Daily Rate':<11}")
    print("-" * 50)
    
    for cohort_id, state in response.cohort_responses.items():
        print(f"{cohort_id:<7} {state.age_gdd:<9.0f} {state.senescence_damage:<7.3f} "
              f"{state.senescence_stage.value:<15} {state.daily_senescence_rate:<11.4f}")
    
    # Show remobilization pool
    print(f"\nRemobilization pool:")
    remob_pool = model.get_remobilization_pool()
    for nutrient, amount in remob_pool.items():
        if amount > 0:
            print(f"  {nutrient}: {amount:.4f} g")


if __name__ == "__main__":
    demonstrate_senescence_model()