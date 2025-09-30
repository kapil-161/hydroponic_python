from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum

class LettuceGrowthStage(Enum):
    GERMINATION = "GE"
    EMERGENCE = "VE"
    FIRST_LEAF = "V1"
    SECOND_LEAF = "V2"
    THIRD_LEAF = "V3"
    FOURTH_LEAF = "V4"
    FIFTH_LEAF = "V5"
    SIXTH_LEAF = "V6"
    SEVENTH_LEAF = "V7"
    EIGHTH_LEAF = "V8"
    NINTH_LEAF = "V9"
    TENTH_LEAF = "V10"
    MATURE_VEGETATIVE = "V11+"
    HEAD_INITIATION = "HI"
    HEAD_DEVELOPMENT = "HD"
    HARVEST_MATURITY = "HM"
    BOLTING_INITIATION = "BI"
    FLOWERING = "FL"
    ANTHESIS = "AN"
    SEED_DEVELOPMENT = "SD"
    PHYSIOLOGICAL_MATURITY = "PM"

@dataclass
class PhenologyParameters:
    base_temperature: float
    optimal_temperature_min: float
    optimal_temperature_max: float
    maximum_temperature: float
    thermal_requirements: Dict[str, float]
    photoperiod_sensitive: bool
    critical_photoperiod: float
    bolting_photoperiod_threshold: float
    bolting_temperature_threshold: float
    head_formation_node_requirement: int
    environmental_buffer_days: int
    bolting_photoperiod_divisor: float
    bolting_photoperiod_risk_max: float
    bolting_temperature_divisor: float
    bolting_temperature_risk_max: float
    environmental_history_days: int
    bolting_sustained_stress_risk: float
    bolting_maturity_risk_factor: float
    bolting_maturity_risk_max: float
    bolting_risk_threshold: float
    photoperiod_slope: float
    thermal_time_scale: float
    vernalization_required: bool
    vernalization_temperature: float
    vernalization_days: float
    stress_acceleration_factor: float
    optimal_water_stress: float
    drought_threshold: float
    heat_threshold: float

    # Remove non-existent parameters per Rules.md

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'PhenologyParameters':
        required_params = [
            'base_temperature', 'optimal_temperature_min', 'optimal_temperature_max', 'maximum_temperature',
            'photoperiod_sensitive', 'critical_photoperiod', 'photoperiod_slope',
            'bolting_photoperiod_threshold', 'bolting_temperature_threshold', 'head_formation_node_requirement',
            'environmental_buffer_days', 'bolting_photoperiod_divisor', 'bolting_photoperiod_risk_max',
            'bolting_temperature_divisor', 'bolting_temperature_risk_max', 'environmental_history_days',
            'bolting_sustained_stress_risk', 'bolting_maturity_risk_factor', 'bolting_maturity_risk_max',
            'bolting_risk_threshold', 'thermal_time_scale', 'vernalization_required', 'vernalization_temperature',
            'vernalization_days', 'stress_acceleration_factor', 'drought_threshold', 'heat_threshold'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")

        if 'thermal_requirements' not in config or not config['thermal_requirements']:
            raise KeyError("thermal_requirements must be provided and non-empty")
        
        required_transitions = [
            'GE_to_VE', 'VE_to_V1', 'V1_to_V2', 'V2_to_V3', 'V3_to_V4', 'V4_to_V5',
            'V5_to_V6', 'V6_to_V7', 'V7_to_V8', 'V8_to_V9', 'V9_to_V10', 'V10_to_V11+',
            'V11+_to_HI', 'HI_to_HD', 'HD_to_HM', 'HM_to_BI', 'BI_to_FL', 'FL_to_AN',
            'AN_to_SD', 'SD_to_PM'
        ]
        for transition in required_transitions:
            if transition not in config['thermal_requirements']:
                raise KeyError(f"Missing thermal requirement for transition: {transition}")

        thermal_time_scale = float(config['thermal_time_scale'])
        if not (0.5 <= thermal_time_scale <= 2.0):
            raise ValueError(f"thermal_time_scale must be between 0.5 and 2.0, got {thermal_time_scale}")
        
        if config['optimal_temperature_min'] >= config['optimal_temperature_max']:
            raise ValueError("optimal_temperature_min must be less than optimal_temperature_max")
        if config['base_temperature'] >= config['optimal_temperature_min']:
            raise ValueError("base_temperature must be less than optimal_temperature_min")
        if config['maximum_temperature'] <= config['optimal_temperature_max']:
            raise ValueError("maximum_temperature must be greater than optimal_temperature_max")
        if config['environmental_buffer_days'] <= 0 or config['environmental_history_days'] <= 0:
            raise ValueError("environmental_buffer_days and environmental_history_days must be positive")
        if config['bolting_risk_threshold'] < 0 or config['bolting_risk_threshold'] > 1:
            raise ValueError("bolting_risk_threshold must be between 0 and 1")

        return cls(
            base_temperature=float(config['base_temperature']),
            optimal_temperature_min=float(config['optimal_temperature_min']),
            optimal_temperature_max=float(config['optimal_temperature_max']),
            maximum_temperature=float(config['maximum_temperature']),
            thermal_requirements=config['thermal_requirements'],
            photoperiod_sensitive=bool(config['photoperiod_sensitive']),
            critical_photoperiod=float(config['critical_photoperiod']),
            bolting_photoperiod_threshold=float(config['bolting_photoperiod_threshold']),
            bolting_temperature_threshold=float(config['bolting_temperature_threshold']),
            head_formation_node_requirement=int(config['head_formation_node_requirement']),
            environmental_buffer_days=int(config['environmental_buffer_days']),
            bolting_photoperiod_divisor=float(config['bolting_photoperiod_divisor']),
            bolting_photoperiod_risk_max=float(config['bolting_photoperiod_risk_max']),
            bolting_temperature_divisor=float(config['bolting_temperature_divisor']),
            bolting_temperature_risk_max=float(config['bolting_temperature_risk_max']),
            environmental_history_days=int(config['environmental_history_days']),
            bolting_sustained_stress_risk=float(config['bolting_sustained_stress_risk']),
            bolting_maturity_risk_factor=float(config['bolting_maturity_risk_factor']),
            bolting_maturity_risk_max=float(config['bolting_maturity_risk_max']),
            bolting_risk_threshold=float(config['bolting_risk_threshold']),
            photoperiod_slope=float(config['photoperiod_slope']),
            thermal_time_scale=float(config['thermal_time_scale']),
            vernalization_required=bool(config['vernalization_required']),
            vernalization_temperature=float(config['vernalization_temperature']),
            vernalization_days=float(config['vernalization_days']),
            stress_acceleration_factor=float(config['stress_acceleration_factor']),
            optimal_water_stress=float(config['optimal_water_stress']),
            drought_threshold=float(config['drought_threshold']),
            heat_threshold=float(config['heat_threshold'])
        )

@dataclass
class DevelopmentalState:
    current_stage: LettuceGrowthStage
    thermal_time_accumulated: float
    thermal_time_required: float
    total_thermal_time: float
    stage_progress: float
    days_in_stage: int
    vernalization_days: float = 0.0
    is_bolting: bool = False
    node_number: int = 0
    can_form_head: bool = False

@dataclass
class PhenologyResponse:
    daily_thermal_time: float
    temperature_factor: float
    photoperiod_factor: float
    stress_factor: float
    development_rate: float
    stage_changed: bool
    new_stage: Optional[LettuceGrowthStage]
    bolting_risk: float

class ComprehensivePhenologyModel:
    def __init__(self, parameters: PhenologyParameters, initial_stage: LettuceGrowthStage):
        if not parameters:
            raise ValueError("PhenologyParameters must be provided")
        self.params = parameters
        thermal_accumulated = 0.0
        next_stage = self.get_next_stage(initial_stage)
        thermal_required = self.get_thermal_requirement(initial_stage, next_stage)
        self.developmental_state = DevelopmentalState(
            current_stage=initial_stage,
            thermal_time_accumulated=thermal_accumulated,
            thermal_time_required=thermal_required,
            total_thermal_time=thermal_accumulated,
            stage_progress=0.0,
            days_in_stage=0
        )
        self.photoperiod_history: List[float] = []
    
    def initialize(self):
        """Initialize the phenology model"""
        self.temperature_history: List[float] = []

    def calculate_thermal_time(self, temperature: float) -> float:
        """Use consolidated thermal time calculation from core_utils."""
        from utils.core_utils import calculate_thermal_time

        if temperature is None:
            raise ValueError("Temperature must be provided")

        # Create config structure for consolidated function
        thermal_config = type('Config', (), {
            'thermal_time': {
                'base_temp': self.params.base_temperature,
                'optimal_temp_min': self.params.optimal_temperature_min,
                'optimal_temp_max': self.params.optimal_temperature_max,
                'max_temp': self.params.maximum_temperature,
                'thermal_time_scale': self.params.thermal_time_scale
            }
        })

        return calculate_thermal_time(temperature, thermal_config, method='scaled')

    def calculate_temperature_factor(self, temperature: float) -> float:
        """Use consolidated temperature factor calculation from core_utils."""
        from utils.core_utils import calculate_temperature_factor

        # Create config structure for consolidated function
        temp_config = type('Config', (), {
            'temperature_factor': {
                'max_thermal_time': (self.params.optimal_temperature_min - self.params.base_temperature) * self.params.thermal_time_scale
            },
            'thermal_time': {
                'base_temp': self.params.base_temperature,
                'optimal_temp_min': self.params.optimal_temperature_min,
                'optimal_temp_max': self.params.optimal_temperature_max,
                'max_temp': self.params.maximum_temperature,
                'thermal_time_scale': self.params.thermal_time_scale
            }
        })

        return calculate_temperature_factor(temperature, temp_config, method='thermal')

    def calculate_photoperiod_factor(self, daylength: float) -> float:
        if daylength is None or daylength < 0:
            raise ValueError("Daylength must be provided and non-negative")
        if not self.params.photoperiod_sensitive:
            return 1.0
        if self.developmental_state.current_stage.value.startswith('V'):
            return 1.0
        elif self.developmental_state.current_stage in [
            LettuceGrowthStage.BOLTING_INITIATION,
            LettuceGrowthStage.FLOWERING
        ]:
            if daylength <= self.params.critical_photoperiod:
                # Return minimum factor instead of raising error
                return 0.5
            excess_hours = daylength - self.params.critical_photoperiod
            factor = 1.0 + (excess_hours * self.params.photoperiod_slope)
            return min(1.5, factor)
        else:
            return 1.0

    def calculate_stress_factor(self, water_stress: float, temperature_stress: float) -> float:
        if water_stress is None or temperature_stress is None:
            raise ValueError("Water and temperature stress factors must be provided")
        if not (0 <= water_stress <= 1 and 0 <= temperature_stress <= 1):
            raise ValueError("Stress factors must be between 0 and 1")
        water_factor = self.params.stress_acceleration_factor if water_stress < self.params.drought_threshold else 1.0
        temp_factor = self.params.stress_acceleration_factor if temperature_stress < self.params.heat_threshold else 1.0
        return max(water_factor, temp_factor)

    def calculate_bolting_risk(self, temperature: float, daylength: float) -> float:
        if temperature is None or daylength is None:
            raise ValueError("Temperature and daylength must be provided")
        self.temperature_history.append(temperature)
        self.photoperiod_history.append(daylength)
        buffer_days = self.params.environmental_buffer_days
        if len(self.temperature_history) > buffer_days:
            self.temperature_history = self.temperature_history[-buffer_days:]
            self.photoperiod_history = self.photoperiod_history[-buffer_days:]
        risk = 0.0
        if daylength > self.params.bolting_photoperiod_threshold:
            photoperiod_risk = (daylength - self.params.bolting_photoperiod_threshold) / self.params.bolting_photoperiod_divisor
            risk += min(self.params.bolting_photoperiod_risk_max, photoperiod_risk)
        if temperature > self.params.bolting_temperature_threshold:
            temp_risk = (temperature - self.params.bolting_temperature_threshold) / self.params.bolting_temperature_divisor
            risk += min(self.params.bolting_temperature_risk_max, temp_risk)
        history_days = self.params.environmental_history_days
        if len(self.temperature_history) >= history_days:
            avg_temp = sum(self.temperature_history[-history_days:]) / history_days
            avg_photoperiod = sum(self.photoperiod_history[-history_days:]) / history_days
            if avg_temp > self.params.bolting_temperature_threshold and avg_photoperiod > self.params.bolting_photoperiod_threshold:
                risk += self.params.bolting_sustained_stress_risk
        if self.developmental_state.node_number > 10:
            maturity_risk = (self.developmental_state.node_number - 10) * self.params.bolting_maturity_risk_factor
            risk += min(self.params.bolting_maturity_risk_max, maturity_risk)
        return max(0.0, min(1.0, risk))

    def get_next_stage(self, current_stage: LettuceGrowthStage) -> LettuceGrowthStage:
        stage_progression = {
            LettuceGrowthStage.GERMINATION: LettuceGrowthStage.EMERGENCE,
            LettuceGrowthStage.EMERGENCE: LettuceGrowthStage.FIRST_LEAF,
            LettuceGrowthStage.FIRST_LEAF: LettuceGrowthStage.SECOND_LEAF,
            LettuceGrowthStage.SECOND_LEAF: LettuceGrowthStage.THIRD_LEAF,
            LettuceGrowthStage.THIRD_LEAF: LettuceGrowthStage.FOURTH_LEAF,
            LettuceGrowthStage.FOURTH_LEAF: LettuceGrowthStage.FIFTH_LEAF,
            LettuceGrowthStage.FIFTH_LEAF: LettuceGrowthStage.SIXTH_LEAF,
            LettuceGrowthStage.SIXTH_LEAF: LettuceGrowthStage.SEVENTH_LEAF,
            LettuceGrowthStage.SEVENTH_LEAF: LettuceGrowthStage.EIGHTH_LEAF,
            LettuceGrowthStage.EIGHTH_LEAF: LettuceGrowthStage.NINTH_LEAF,
            LettuceGrowthStage.NINTH_LEAF: LettuceGrowthStage.TENTH_LEAF,
            LettuceGrowthStage.TENTH_LEAF: LettuceGrowthStage.MATURE_VEGETATIVE,
            LettuceGrowthStage.MATURE_VEGETATIVE: LettuceGrowthStage.HEAD_INITIATION,
            LettuceGrowthStage.HEAD_INITIATION: LettuceGrowthStage.HEAD_DEVELOPMENT,
            LettuceGrowthStage.HEAD_DEVELOPMENT: LettuceGrowthStage.HARVEST_MATURITY,
            LettuceGrowthStage.HARVEST_MATURITY: LettuceGrowthStage.BOLTING_INITIATION,
            LettuceGrowthStage.BOLTING_INITIATION: LettuceGrowthStage.FLOWERING,
            LettuceGrowthStage.FLOWERING: LettuceGrowthStage.ANTHESIS,
            LettuceGrowthStage.ANTHESIS: LettuceGrowthStage.SEED_DEVELOPMENT,
            LettuceGrowthStage.SEED_DEVELOPMENT: LettuceGrowthStage.PHYSIOLOGICAL_MATURITY,
            LettuceGrowthStage.PHYSIOLOGICAL_MATURITY: LettuceGrowthStage.PHYSIOLOGICAL_MATURITY
        }
        return stage_progression[current_stage]

    def get_thermal_requirement(self, current_stage: LettuceGrowthStage, next_stage: LettuceGrowthStage) -> float:
        transition_key = f"{current_stage.value}_to_{next_stage.value}"
        if transition_key not in self.params.thermal_requirements:
            raise KeyError(f"Missing thermal requirement for transition: {transition_key}")
        return float(self.params.thermal_requirements[transition_key])

    def update_developmental_state(self, temperature: float, daylength: float,
                                  water_stress: float, temperature_stress: float) -> PhenologyResponse:
        if temperature is None or daylength is None or water_stress is None or temperature_stress is None:
            raise ValueError("All environmental inputs (temperature, daylength, water_stress, temperature_stress) must be provided")
        daily_tt = self.calculate_thermal_time(temperature)
        temp_factor = self.calculate_temperature_factor(temperature)
        photoperiod_factor = self.calculate_photoperiod_factor(daylength)
        stress_factor = self.calculate_stress_factor(water_stress, temperature_stress)
        bolting_risk = self.calculate_bolting_risk(temperature, daylength)
        if bolting_risk > self.params.bolting_risk_threshold and not self.developmental_state.is_bolting:
            self.developmental_state.is_bolting = True
        development_rate = daily_tt * photoperiod_factor * stress_factor
        self.developmental_state.thermal_time_accumulated += development_rate
        self.developmental_state.total_thermal_time += development_rate
        self.developmental_state.days_in_stage += 1
        if self.developmental_state.thermal_time_required > 0:
            self.developmental_state.stage_progress = (
                self.developmental_state.thermal_time_accumulated / self.developmental_state.thermal_time_required
            )
        stage_changed = False
        new_stage = None
        if self.developmental_state.stage_progress >= 1.0:
            next_stage = self.get_next_stage(self.developmental_state.current_stage)
            if next_stage != self.developmental_state.current_stage:
                self.developmental_state.current_stage = next_stage
                self.developmental_state.thermal_time_accumulated = 0.0
                self.developmental_state.thermal_time_required = self.get_thermal_requirement(
                    self.developmental_state.current_stage, self.get_next_stage(next_stage)
                )
                self.developmental_state.stage_progress = 0.0
                self.developmental_state.days_in_stage = 0
                stage_changed = True
                new_stage = next_stage
                if next_stage.value.startswith('V') and next_stage.value[1:].isdigit():
                    self.developmental_state.node_number = int(next_stage.value[1:])
                elif next_stage.value.startswith('V') and '+' in next_stage.value:
                    self.developmental_state.node_number += 1
                if self.developmental_state.node_number >= self.params.head_formation_node_requirement:
                    self.developmental_state.can_form_head = True
        if self.params.vernalization_required and self.developmental_state.current_stage == LettuceGrowthStage.GERMINATION:
            if abs(temperature - self.params.vernalization_temperature) <= 2.0:
                self.developmental_state.vernalization_days += 1
            if self.developmental_state.vernalization_days < self.params.vernalization_days:
                development_rate = 0.0
                daily_tt = 0.0
                stage_changed = False
                new_stage = None
        return PhenologyResponse(
            daily_thermal_time=daily_tt,
            temperature_factor=temp_factor,
            photoperiod_factor=photoperiod_factor,
            stress_factor=stress_factor,
            development_rate=development_rate,
            stage_changed=stage_changed,
            new_stage=new_stage,
            bolting_risk=bolting_risk
        )

    def get_developmental_summary(self) -> Dict[str, Any]:
        stage = self.developmental_state.current_stage
        return {
            'stage_name': stage.value,
            'stage_code': stage.name,
            'is_vegetative': stage.value.startswith('V') or stage == LettuceGrowthStage.EMERGENCE,
            'is_reproductive': stage in [
                LettuceGrowthStage.BOLTING_INITIATION,
                LettuceGrowthStage.FLOWERING,
                LettuceGrowthStage.ANTHESIS,
                LettuceGrowthStage.SEED_DEVELOPMENT,
                LettuceGrowthStage.PHYSIOLOGICAL_MATURITY
            ],
            'is_head_forming': stage in [
                LettuceGrowthStage.HEAD_INITIATION,
                LettuceGrowthStage.HEAD_DEVELOPMENT
            ],
            'is_harvestable': stage in [
                LettuceGrowthStage.HEAD_DEVELOPMENT,
                LettuceGrowthStage.HARVEST_MATURITY
            ],
            'node_number': self.developmental_state.node_number,
            'can_form_head': self.developmental_state.can_form_head,
            'is_bolting': self.developmental_state.is_bolting,
            'stage_progress': self.developmental_state.stage_progress,
            'days_in_stage': self.developmental_state.days_in_stage,
            'total_thermal_time': self.developmental_state.total_thermal_time,
            'vernalization_days': self.developmental_state.vernalization_days
        }

def create_lettuce_phenology_model(system_config: Any, initial_stage: LettuceGrowthStage) -> 'ComprehensivePhenologyModel':
    if system_config is None:
        raise ValueError("System configuration must be provided")
    config = getattr(system_config, 'phenology_parameters', None)
    if config is None:
        raise ValueError("phenology_parameters section must be provided in configuration")
    parameters = PhenologyParameters.from_config(config)
    return ComprehensivePhenologyModel(parameters, initial_stage)

"""
INPUT PARAMETERS (from configuration):
- base_temperature: Minimum temperature for development (°C)
- optimal_temperature_min: Lower bound of optimal temperature range (°C)
- optimal_temperature_max: Upper bound of optimal temperature range (°C)
- maximum_temperature: Maximum temperature for development (°C)
- thermal_requirements: Dictionary of GDD requirements for transitions (e.g., 'GE_to_VE', 'VE_to_V1')
- photoperiod_sensitive: Whether plant responds to day length (bool)
- critical_photoperiod: Day length triggering reproductive development (hours)
- bolting_photoperiod_threshold: Day length triggering bolting (hours)
- bolting_temperature_threshold: Temperature triggering bolting (°C)
- head_formation_node_requirement: Minimum nodes for head formation (int)
- environmental_buffer_days: Days to store environmental history (int)
- bolting_photoperiod_divisor: Divisor for photoperiod risk calculation
- bolting_photoperiod_risk_max: Maximum photoperiod risk contribution
- bolting_temperature_divisor: Divisor for temperature risk calculation
- bolting_temperature_risk_max: Maximum temperature risk contribution
- environmental_history_days: Days for sustained stress calculation (int)
- bolting_sustained_stress_risk: Risk from sustained stress
- bolting_maturity_risk_factor: Risk increase per node beyond 10
- bolting_maturity_risk_max: Maximum maturity risk contribution
- bolting_risk_threshold: Threshold for bolting initiation (0-1)
- photoperiod_slope: Sensitivity to photoperiod changes
- thermal_time_scale: Scaling factor for daily GDD (0.5-2.0)
- vernalization_required: Whether vernalization is needed (bool)
- vernalization_temperature: Optimal temperature for vernalization (°C)
- vernalization_days: Required vernalization days
- stress_acceleration_factor: Factor by which stress accelerates development
- drought_threshold: Water stress threshold for acceleration (0-1)
- heat_threshold: Temperature stress threshold for acceleration (0-1)

INPUT VARIABLES:
- temperature: Daily average temperature (°C)
- daylength: Day length (hours)
- water_stress: Water stress factor (0-1, 1=no stress)
- temperature_stress: Temperature stress factor (0-1, 1=no stress)
- initial_stage: Initial growth stage (LettuceGrowthStage)

OUTPUT VARIABLES:
- PhenologyResponse:
  - daily_thermal_time: Daily GDD accumulated
  - temperature_factor: Temperature effect on development (0-1)
  - photoperiod_factor: Photoperiod effect on development (0.5-1.5)
  - stress_factor: Stress effect on development (≥1 if accelerated)
  - development_rate: Effective daily development rate
  - stage_changed: Whether stage transitioned (bool)
  - new_stage: New stage if transitioned (LettuceGrowthStage or None)
  - bolting_risk: Risk of bolting (0-1)

FUNCTION EXPLANATIONS FOR NON-CODERS:
This model tracks the developmental stages of a hydroponic crop, like a biological calendar for lettuce, predicting when it germinates, grows leaves, forms heads, or bolts.

1. calculate_thermal_time:
   - Calculates daily Growing Degree Days (GDD): `GDD = (T - Tbase) * factor * scale`.
   - Like tracking how much "heat" a plant needs to grow, similar to baking time for bread.

2. calculate_temperature_factor:
   - Determines how temperature affects development rate: `factor = GDD / max_GDD`.
   - Like how you perform better in comfortable weather, plants grow best at optimal temperatures.

3. calculate_photoperiod_factor:
   - Adjusts development based on day length: `factor = 1 + slope * (daylength - critical)`.
   - Like how daylight affects your sleep cycle, longer days can trigger flowering in plants.

4. calculate_stress_factor:
   - Calculates how stress accelerates development: `factor = max(water_acceleration, temp_acceleration)`.
   - Like how stress pushes you to act faster, plants rush to reproduce under stress.

5. calculate_bolting_risk:
   - Predicts bolting risk: `risk = photoperiod_risk + temp_risk + sustained_risk + maturity_risk`.
   - Like assessing the chance of a teenager rebelling, long days and heat increase bolting risk.

6. get_next_stage:
   - Determines the next growth stage based on current stage and bolting status.
   - Like a roadmap for plant growth, guiding it from germination to harvest or flowering.

7. update_developmental_state:
   - Updates the plant’s stage daily, integrating thermal time, photoperiod, and stress effects.
   - Like a daily growth journal, tracking progress and predicting stage changes.

PRACTICAL APPLICATIONS:
- Predicts harvest dates for planning crop cycles.
- Guides temperature and lighting control to prevent bolting.
- Optimizes planting schedules for continuous production.
- Identifies stress conditions to adjust growing environment.
- Supports variety selection for specific climates or seasons.
"""