from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

class SenescenceType(Enum):
    AGE_BASED = "age_based"
    WATER_STRESS = "water_stress"
    NITROGEN_STRESS = "nitrogen_stress"
    TEMPERATURE_STRESS = "temperature_stress"
    LIGHT_STRESS = "light_stress"
    DEVELOPMENTAL = "developmental"
    PATHOGEN = "pathogen"
    MECHANICAL = "mechanical"

class SenescenceStage(Enum):
    HEALTHY = "healthy"
    EARLY_SENESCENCE = "early_senescence"
    ACTIVE_SENESCENCE = "active_senescence"
    LATE_SENESCENCE = "late_senescence"
    DEAD = "dead"

@dataclass
class SenescenceParameters:
    natural_lifespan_gdd: float
    age_senescence_rate: float
    water_stress_threshold: float
    nitrogen_stress_threshold: float
    temperature_stress_threshold: float
    light_stress_threshold: float
    water_stress_rate: float
    nitrogen_stress_rate: float
    temperature_stress_rate: float
    light_stress_rate: float
    early_senescence_threshold: float
    active_senescence_threshold: float
    late_senescence_threshold: float
    death_threshold: float
    remobilization_efficiency: Dict[str, float]
    recovery_rate: float
    max_recovery: float
    reproductive_priority_factor: float
    lower_canopy_factor: float
    active_senescence_multiplier: float
    normal_senescence_multiplier: float
    stress_history_days: int
    daily_area_loss_factor: float
    daily_biomass_loss_factor: float
    stress_recovery_threshold: float
    recovery_stress_threshold: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'SenescenceParameters':
        required_params = [
            'natural_lifespan_gdd', 'age_senescence_rate', 'water_stress_threshold',
            'nitrogen_stress_threshold', 'temperature_stress_threshold', 'light_stress_threshold',
            'water_stress_rate', 'nitrogen_stress_rate', 'temperature_stress_rate', 'light_stress_rate',
            'early_senescence_threshold', 'active_senescence_threshold', 'late_senescence_threshold',
            'death_threshold', 'recovery_rate', 'max_recovery', 'reproductive_priority_factor',
            'lower_canopy_factor', 'active_senescence_multiplier', 'normal_senescence_multiplier',
            'stress_history_days', 'daily_area_loss_factor', 'daily_biomass_loss_factor',
            'stress_recovery_threshold', 'recovery_stress_threshold'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")

        remobilization_efficiency = {
            'nitrogen': float(config['nitrogen_recovery']),
            'phosphorus': float(config['phosphorus_recovery']),
            'potassium': float(config['potassium_recovery']),
            'magnesium': float(config['magnesium_recovery']),
            'sulfur': float(config['sulfur_recovery']),
            'calcium': float(config['calcium_recovery']),
            'iron': float(config['iron_recovery']),
            'manganese': float(config['manganese_recovery']),
            'zinc': float(config['zinc_recovery']),
            'copper': float(config['copper_recovery']),
            'boron': float(config['boron_recovery']),
            'molybdenum': float(config['molybdenum_recovery'])
        }

        if config['early_senescence_threshold'] >= config['active_senescence_threshold'] or \
           config['active_senescence_threshold'] >= config['late_senescence_threshold'] or \
           config['late_senescence_threshold'] >= config['death_threshold']:
            raise ValueError("Senescence thresholds must be increasing: early < active < late < death")
        if any(eff < 0 or eff > 1 for eff in remobilization_efficiency.values()):
            raise ValueError("Remobilization efficiencies must be between 0 and 1")
        if config['stress_history_days'] <= 0:
            raise ValueError("stress_history_days must be positive")
        if config['recovery_rate'] < 0:
            raise ValueError("recovery_rate must be non-negative")
        if config['max_recovery'] < 0 or config['max_recovery'] > 1:
            raise ValueError("max_recovery must be between 0 and 1")

        return cls(
            natural_lifespan_gdd=float(config['natural_lifespan_gdd']),
            age_senescence_rate=float(config['age_senescence_rate']),
            water_stress_threshold=float(config['water_stress_threshold']),
            nitrogen_stress_threshold=float(config['nitrogen_stress_threshold']),
            temperature_stress_threshold=float(config['temperature_stress_threshold']),
            light_stress_threshold=float(config['light_stress_threshold']),
            water_stress_rate=float(config['water_stress_rate']),
            nitrogen_stress_rate=float(config['nitrogen_stress_rate']),
            temperature_stress_rate=float(config['temperature_stress_rate']),
            light_stress_rate=float(config['light_stress_rate']),
            early_senescence_threshold=float(config['early_senescence_threshold']),
            active_senescence_threshold=float(config['active_senescence_threshold']),
            late_senescence_threshold=float(config['late_senescence_threshold']),
            death_threshold=float(config['death_threshold']),
            remobilization_efficiency=remobilization_efficiency,
            recovery_rate=float(config['recovery_rate']),
            max_recovery=float(config['max_recovery']),
            reproductive_priority_factor=float(config['reproductive_priority_factor']),
            lower_canopy_factor=float(config['lower_canopy_factor']),
            active_senescence_multiplier=float(config['active_senescence_multiplier']),
            normal_senescence_multiplier=float(config['normal_senescence_multiplier']),
            stress_history_days=int(config['stress_history_days']),
            daily_area_loss_factor=float(config['daily_area_loss_factor']),
            daily_biomass_loss_factor=float(config['daily_biomass_loss_factor']),
            stress_recovery_threshold=float(config['stress_recovery_threshold']),
            recovery_stress_threshold=float(config['recovery_stress_threshold'])
        )

@dataclass
class LeafCohortSenescence:
    cohort_id: int
    age_gdd: float
    senescence_damage: float
    senescence_stage: SenescenceStage
    active_senescence_types: List[SenescenceType] = field(default_factory=list)
    daily_senescence_rate: float = 0.0
    nutrient_content: Dict[str, float] = field(default_factory=dict)
    remobilizable_nutrients: Dict[str, float] = field(default_factory=dict)
    is_recoverable: bool = True

@dataclass
class SenescenceResponse:
    cohort_responses: Dict[int, LeafCohortSenescence]
    total_senescence_rate: float
    remobilized_nutrients: Dict[str, float]
    senesced_area: float
    senesced_biomass: float
    active_senescence_types: List[SenescenceType]
    average_senescence_stage: SenescenceStage

class AdvancedSenescenceModel:
    def __init__(self, parameters: SenescenceParameters):
        if not parameters:
            raise ValueError("SenescenceParameters must be provided")
        self.params = parameters
        self.cohort_states: Dict[int, LeafCohortSenescence] = {}
        self.stress_history: Dict[str, List[float]] = {
            'water': [], 'nitrogen': [], 'temperature': [], 'light': []
        }
        self.remobilization_pool: Dict[str, float] = {}

    def initialize_cohort(self, cohort_id: int, initial_nutrient_content: Dict[str, float]):
        if cohort_id in self.cohort_states:
            raise ValueError(f"Cohort {cohort_id} already initialized")
        if not initial_nutrient_content:
            raise ValueError("initial_nutrient_content must be provided")
        remobilizable_nutrients = {}
        for nutrient, content in initial_nutrient_content.items():
            if nutrient not in self.params.remobilization_efficiency:
                raise KeyError(f"Remobilization efficiency for {nutrient} not found")
            efficiency = self.params.remobilization_efficiency[nutrient]
            remobilizable_nutrients[nutrient] = content * efficiency
        self.cohort_states[cohort_id] = LeafCohortSenescence(
            cohort_id=cohort_id,
            age_gdd=0.0,
            senescence_damage=0.0,
            senescence_stage=SenescenceStage.HEALTHY,
            nutrient_content=initial_nutrient_content.copy(),
            remobilizable_nutrients=remobilizable_nutrients
        )

    def calculate_age_senescence(self, cohort_state: LeafCohortSenescence) -> float:
        if cohort_state.age_gdd <= self.params.natural_lifespan_gdd:
            return 0.0
        excess_age = cohort_state.age_gdd - self.params.natural_lifespan_gdd
        age_factor = 1.0 + (excess_age / self.params.natural_lifespan_gdd)
        return self.params.age_senescence_rate * age_factor

    def calculate_stress_senescence(self, water_stress: float, nitrogen_stress: float,
                                  temperature_stress: float, light_stress: float) -> Dict[str, float]:
        if any(x is None for x in [water_stress, nitrogen_stress, temperature_stress, light_stress]):
            raise ValueError("All stress levels (water, nitrogen, temperature, light) must be provided")
        if any(not 0 <= x <= 1 for x in [water_stress, nitrogen_stress, temperature_stress, light_stress]):
            raise ValueError("Stress levels must be between 0 and 1")
        stress_rates = {}
        for stress, threshold, rate in [
            (water_stress, self.params.water_stress_threshold, self.params.water_stress_rate),
            (nitrogen_stress, self.params.nitrogen_stress_threshold, self.params.nitrogen_stress_rate),
            (temperature_stress, self.params.temperature_stress_threshold, self.params.temperature_stress_rate),
            (light_stress, self.params.light_stress_threshold, self.params.light_stress_rate)
        ]:
            if stress > threshold:
                stress_intensity = (stress - threshold) / (1.0 - threshold)
                stress_rates['water' if rate == self.params.water_stress_rate else
                            'nitrogen' if rate == self.params.nitrogen_stress_rate else
                            'temperature' if rate == self.params.temperature_stress_rate else
                            'light'] = rate * stress_intensity
            else:
                stress_rates['water' if rate == self.params.water_stress_rate else
                            'nitrogen' if rate == self.params.nitrogen_stress_rate else
                            'temperature' if rate == self.params.temperature_stress_rate else
                            'light'] = 0.0
        return stress_rates

    def calculate_developmental_senescence(self, is_reproductive: bool, canopy_position: float) -> float:
        if is_reproductive is None or canopy_position is None:
            raise ValueError("is_reproductive and canopy_position must be provided")
        if not 0 <= canopy_position <= 1:
            raise ValueError("canopy_position must be between 0 and 1")
        dev_rate = 0.0
        if is_reproductive:
            dev_rate += self.params.age_senescence_rate * (self.params.reproductive_priority_factor - 1.0)
        if canopy_position < 0.5:
            shading_factor = (0.5 - canopy_position) * 2.0
            dev_rate += self.params.age_senescence_rate * shading_factor * (self.params.lower_canopy_factor - 1.0)
        return dev_rate

    def calculate_recovery_rate(self, cohort_state: LeafCohortSenescence, current_stress_levels: Dict[str, float]) -> float:
        if not cohort_state.is_recoverable or cohort_state.senescence_damage > self.params.max_recovery:
            return 0.0
        all_stress_low = all(stress < self.params.recovery_stress_threshold for stress in current_stress_levels.values())
        if all_stress_low and cohort_state.senescence_stage == SenescenceStage.EARLY_SENESCENCE:
            max_recovery_rate = min(self.params.recovery_rate, cohort_state.senescence_damage * 0.1)
            return max_recovery_rate
        return 0.0

    def update_senescence_stage(self, cohort_state: LeafCohortSenescence):
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

    def calculate_nutrient_remobilization(self, cohort_state: LeafCohortSenescence, daily_senescence_rate: float) -> Dict[str, float]:
        remobilized = {}
        if daily_senescence_rate > 0 and cohort_state.senescence_stage != SenescenceStage.HEALTHY:
            for nutrient, available in cohort_state.remobilizable_nutrients.items():
                if available > 0:
                    efficiency = self.params.remobilization_efficiency.get(nutrient)
                    if efficiency is None:
                        raise KeyError(f"Remobilization efficiency for {nutrient} not found")
                    remob_rate = daily_senescence_rate * (self.params.active_senescence_multiplier if cohort_state.senescence_stage == SenescenceStage.ACTIVE_SENESCENCE else self.params.normal_senescence_multiplier)
                    daily_remobilization = available * remob_rate * efficiency
                    remobilized[nutrient] = daily_remobilization
                    cohort_state.remobilizable_nutrients[nutrient] = max(0.0, available - daily_remobilization)
        return remobilized

    def calculate_daily_senescence(self, cohort_data: Dict[int, Dict[str, Any]], 
                                  environmental_stress: Dict[str, float],
                                  developmental_state: Dict[str, Any]) -> SenescenceResponse:
        if not cohort_data or not environmental_stress or not developmental_state:
            raise ValueError("cohort_data, environmental_stress, and developmental_state must be provided")
        required_stress = ['water', 'nitrogen', 'temperature', 'light']
        for stress_type in required_stress:
            if stress_type not in environmental_stress:
                raise KeyError(f"Missing stress level: {stress_type}")
        for cohort_id, data in cohort_data.items():
            for key in ['age_gdd', 'area', 'biomass', 'nutrient_content', 'canopy_position']:
                if key not in data:
                    raise KeyError(f"Missing data key for cohort {cohort_id}: {key}")
        if 'is_reproductive' not in developmental_state:
            raise KeyError("Missing developmental_state key: is_reproductive")
        stress_rates = self.calculate_stress_senescence(
            environmental_stress['water'], environmental_stress['nitrogen'],
            environmental_stress['temperature'], environmental_stress['light']
        )
        total_senescence = 0.0
        total_remobilized = {}
        total_senesced_area = 0.0
        total_senesced_biomass = 0.0
        active_senescence_types = []
        stage_counts = {stage: 0 for stage in SenescenceStage}
        for cohort_id, data in cohort_data.items():
            if cohort_id not in self.cohort_states:
                self.initialize_cohort(cohort_id, data['nutrient_content'])
            cohort_state = self.cohort_states[cohort_id]
            cohort_state.age_gdd = data['age_gdd']
            age_senescence = self.calculate_age_senescence(cohort_state)
            dev_senescence = self.calculate_developmental_senescence(
                developmental_state['is_reproductive'],
                data['canopy_position']
            )
            stress_senescence = max(stress_rates.values())
            recovery_rate = self.calculate_recovery_rate(cohort_state, environmental_stress)
            total_daily_rate = max(0.0, age_senescence + dev_senescence + stress_senescence - recovery_rate)
            cohort_state.daily_senescence_rate = total_daily_rate
            cohort_state.senescence_damage = min(1.0, max(0.0, cohort_state.senescence_damage + total_daily_rate))
            self.update_senescence_stage(cohort_state)
            cohort_state.active_senescence_types = []
            if age_senescence > 0:
                cohort_state.active_senescence_types.append(SenescenceType.AGE_BASED)
            if stress_rates['water'] > 0:
                cohort_state.active_senescence_types.append(SenescenceType.WATER_STRESS)
            if stress_rates['nitrogen'] > 0:
                cohort_state.active_senescence_types.append(SenescenceType.NITROGEN_STRESS)
            if stress_rates['temperature'] > 0:
                cohort_state.active_senescence_types.append(SenescenceType.TEMPERATURE_STRESS)
            if stress_rates['light'] > 0:
                cohort_state.active_senescence_types.append(SenescenceType.LIGHT_STRESS)
            if dev_senescence > 0:
                cohort_state.active_senescence_types.append(SenescenceType.DEVELOPMENTAL)
            remobilized = self.calculate_nutrient_remobilization(cohort_state, total_daily_rate)
            total_senescence += total_daily_rate
            total_senesced_area += data['area'] * cohort_state.senescence_damage * self.params.daily_area_loss_factor
            total_senesced_biomass += data['biomass'] * cohort_state.senescence_damage * self.params.daily_biomass_loss_factor
            for nutrient, amount in remobilized.items():
                total_remobilized[nutrient] = total_remobilized.get(nutrient, 0.0) + amount
            active_senescence_types.extend(cohort_state.active_senescence_types)
            stage_counts[cohort_state.senescence_stage] += 1
        active_senescence_types = list(set(active_senescence_types))
        avg_stage = max(stage_counts, key=stage_counts.get)
        for nutrient, amount in total_remobilized.items():
            self.remobilization_pool[nutrient] = self.remobilization_pool.get(nutrient, 0.0) + amount
        return SenescenceResponse(
            cohort_responses=self.cohort_states.copy(),
            total_senescence_rate=total_senescence,
            remobilized_nutrients=total_remobilized,
            senesced_area=total_senesced_area,
            senesced_biomass=total_senesced_biomass,
            active_senescence_types=active_senescence_types,
            average_senescence_stage=avg_stage
        )

    def get_remobilization_pool(self) -> Dict[str, float]:
        return self.remobilization_pool.copy()

def create_lettuce_senescence_model(system_config: Any) -> AdvancedSenescenceModel:
    if system_config is None:
        raise ValueError("System configuration must be provided")
    config = getattr(system_config, 'senescence_parameters', None)
    if config is None:
        raise ValueError("senescence_parameters section must be provided in configuration")
    parameters = SenescenceParameters.from_config(config)
    return AdvancedSenescenceModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- natural_lifespan_gdd: Leaf lifespan in GDD
- age_senescence_rate: Daily senescence rate for old leaves
- water_stress_threshold: Water stress threshold for senescence
- nitrogen_stress_threshold: Nitrogen stress threshold for senescence
- temperature_stress_threshold: Temperature stress threshold for senescence
- light_stress_threshold: Light stress threshold for senescence
- water_stress_rate: Daily rate under water stress
- nitrogen_stress_rate: Daily rate under nitrogen stress
- temperature_stress_rate: Daily rate under temperature stress
- light_stress_rate: Daily rate under light stress
- early_senescence_threshold: Damage threshold for early senescence
- active_senescence_threshold: Damage threshold for active senescence
- late_senescence_threshold: Damage threshold for late senescence
- death_threshold: Damage threshold for death
- remobilization_efficiency: Dictionary of nutrient remobilization efficiencies
- recovery_rate: Daily recovery rate under good conditions
- max_recovery: Maximum recoverable damage
- reproductive_priority_factor: Senescence acceleration during reproduction
- lower_canopy_factor: Senescence acceleration for shaded leaves
- active_senescence_multiplier: Remobilization multiplier for active senescence
- normal_senescence_multiplier: Remobilization multiplier for normal senescence
- stress_history_days: Days of stress history
- daily_area_loss_factor: Daily area loss factor during senescence
- daily_biomass_loss_factor: Daily biomass loss factor during senescence
- stress_recovery_threshold: Stress threshold for recovery
- recovery_stress_threshold: Stress threshold for recovery initiation

INPUT VARIABLES:
- cohort_data: Dictionary with cohort info (age_gdd, area, biomass, nutrient_content, canopy_position)
- environmental_stress: Dictionary with water, nitrogen, temperature, light stress levels (0-1)
- developmental_state: Dictionary with is_reproductive (bool)

OUTPUT VARIABLES:
- SenescenceResponse:
  - cohort_responses: Senescence states by cohort
  - total_senescence_rate: Total daily senescence rate
  - remobilized_nutrients: Remobilized nutrients (g/day)
  - senesced_area: Leaf area lost (m²/day)
  - senesced_biomass: Biomass lost (g/day)
  - active_senescence_types: Active senescence triggers
  - average_senescence_stage: Average senescence stage

FUNCTION EXPLANATIONS 
This model simulates plant senescence, the aging and dying of leaves, like tracking how leaves yellow and fall off while recycling nutrients.

1. calculate_age_senescence:
   - Calculates natural aging: `rate = base_rate * (1 + excess_age / lifespan)`.
   - Like how wear and tear increases with age; leaves deteriorate faster past their prime.

2. calculate_stress_senescence:
   - Calculates stress-induced aging: `rate = base_rate * (stress - threshold) / (1 - threshold)`.
   - Like how hardship ages people prematurely; stress speeds up leaf death.

3. calculate_developmental_senescence:
   - Calculates senescence for reproduction or shading: `rate = base_rate * factor`.
   - Like redirecting resources to kids; plants drop old leaves to feed new growth or seeds.

4. calculate_recovery_rate:
   - Calculates reversal of early senescence: `rate = min(base_rate, damage * 0.1) if stress low`.
   - Like recovering from a mild cold with rest; early yellowing can reverse under good conditions.

5. update_senescence_stage:
   - Determines leaf health stage based on damage: healthy to dead.
   - Like disease staging; each stage affects nutrient recovery and plant function.

6. calculate_nutrient_remobilization:
   - Calculates nutrient recycling: `amount = available * rate * multiplier * efficiency`.
   - Like salvaging parts from an old car; dying leaves donate nutrients to the plant.

7. calculate_daily_senescence:
   - Updates all leaves daily, combining aging, stress, recovery, and recycling.
   - Like a daily health check for every leaf, predicting losses and nutrient gains.

PRACTICAL APPLICATIONS:
- Predicts leaf loss to adjust lighting or pruning.
- Optimizes nutrient recycling during reproduction.
- Guides stress management to delay senescence.
- Supports harvest timing for maximum yield.
- Helps diagnose environmental issues from leaf aging patterns.
"""