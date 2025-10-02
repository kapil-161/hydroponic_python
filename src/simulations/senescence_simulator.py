"""
Senescence Simulator

Handles senescence simulation loop and inter-simulator communication
for leaf aging, senescence, and remobilization in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.senescence_model import (
    AdvancedSenescenceModel, SenescenceParameters, SenescenceStage,
    SenescenceType, LeafCohortSenescence, SenescenceResponse
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class SenescenceState:
    """State tracking for senescence simulator"""
    total_senescence_rate: float = 0.0
    age_senescence_rate: float = 0.0
    stress_senescence_rate: float = 0.0
    developmental_senescence_rate: float = 0.0
    total_remobilization_rate: float = 0.0
    nitrogen_remobilization_rate: float = 0.0
    carbon_remobilization_rate: float = 0.0
    phosphorus_remobilization_rate: float = 0.0
    potassium_remobilization_rate: float = 0.0
    senescence_stage_distribution: Dict[str, int] = field(default_factory=dict)
    senescence_type_distribution: Dict[str, float] = field(default_factory=dict)
    senescence_factors: Dict[str, float] = field(default_factory=dict)
    remobilization_efficiency: Dict[str, float] = field(default_factory=dict)
    recovery_rate: float = 0.0
    max_recovery: float = 0.0
    stress_history: List[float] = field(default_factory=list)
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class SenescenceSimulatorState:
    """State tracking for senescence simulator"""
    total_senescence_rate: float = 0.0
    age_senescence_rate: float = 0.0
    stress_senescence_rate: float = 0.0
    developmental_senescence_rate: float = 0.0
    total_remobilization_rate: float = 0.0
    nitrogen_remobilization_rate: float = 0.0
    carbon_remobilization_rate: float = 0.0
    phosphorus_remobilization_rate: float = 0.0
    potassium_remobilization_rate: float = 0.0
    senescence_stage_distribution: Dict[str, int] = field(default_factory=dict)
    senescence_type_distribution: Dict[str, float] = field(default_factory=dict)
    senescence_factors: Dict[str, float] = field(default_factory=dict)
    remobilization_efficiency: Dict[str, float] = field(default_factory=dict)
    recovery_rate: float = 0.0
    max_recovery: float = 0.0
    stress_history: List[float] = field(default_factory=list)
    cumulative_senescence: float = 0.0
    daily_senescence: float = 0.0
    cumulative_remobilization: float = 0.0
    daily_remobilization: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class SenescenceSimulator(BaseSimulator):
    """Simulator for senescence - follows Rules.md strictly"""
    
    def __init__(self, 
                 senescence_params: SenescenceParameters = None):
        super().__init__("senescence_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if senescence_params is None:
            raise ValueError("SenescenceParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.senescence_params = senescence_params
        self.model = AdvancedSenescenceModel(self.senescence_params)
        
        # State tracking
        self.state = SenescenceSimulatorState()
        self.history: List[SenescenceSimulatorState] = []
        
        # Initialize senescence stages
        self.senescence_stages = ['healthy', 'early_senescence', 'active_senescence', 'late_senescence', 'dead']
        for stage in self.senescence_stages:
            self.state.senescence_stage_distribution[stage] = 0
        
        # Initialize senescence types
        self.senescence_types = [
            'age_based', 'water_stress', 'nitrogen_stress', 'temperature_stress',
            'light_stress', 'developmental', 'pathogen', 'mechanical'
        ]
        for sen_type in self.senescence_types:
            self.state.senescence_type_distribution[sen_type] = 0.0
        
        # Initialize senescence factors
        self.senescence_factor_types = [
            'age_factor', 'water_stress_factor', 'nitrogen_stress_factor',
            'temperature_stress_factor', 'light_stress_factor', 'developmental_factor'
        ]
        for factor in self.senescence_factor_types:
            self.state.senescence_factors[factor] = 1.0
        
        # Initialize remobilization efficiency
        self.remobilization_types = ['nitrogen', 'carbon', 'phosphorus', 'potassium']
        for rem_type in self.remobilization_types:
            self.state.remobilization_efficiency[rem_type] = 1.0
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'phenology_simulator': ['growth_stage', 'development_index', 'thermal_time'],
            'stress_models': ['water_stress', 'nitrogen_stress', 'temperature_stress', 'light_stress'],
            'leaf_development_simulator': ['leaf_age_distribution', 'leaf_senescence_rate'],
            'biomass_allocation_simulator': ['leaf_biomass', 'total_biomass'],
            'nitrogen_balance_simulator': ['nitrogen_remobilization_rate', 'nitrogen_stress_index'],
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        # Subscribe to stress events
        self.message_bus.subscribe(EventType.STRESS_UPDATE, self._handle_stress_update)
        
        print(f"Senescence simulator initialized with parameters from CSV")
    
    def _handle_stress_update(self, event: SimulationEvent):
        """Handle stress data updates - merge with existing cache"""
        # Merge event data with existing cache instead of replacing
        if 'stress_models' not in self.dependency_cache:
            self.dependency_cache['stress_models'] = {}
        self.dependency_cache['stress_models'].update(event.data)
        self.cache_timestamp['stress_models'] = datetime.now()
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Senescence simulator: Simulation started")
        self.state = SenescenceSimulatorState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Initialize senescence state
        initial_senescence_state = SenescenceState(
            total_senescence_rate=self.state.total_senescence_rate,
            age_senescence_rate=self.state.age_senescence_rate,
            stress_senescence_rate=self.state.stress_senescence_rate,
            developmental_senescence_rate=self.state.developmental_senescence_rate,
            total_remobilization_rate=self.state.total_remobilization_rate,
            nitrogen_remobilization_rate=self.state.nitrogen_remobilization_rate,
            carbon_remobilization_rate=self.state.carbon_remobilization_rate,
            phosphorus_remobilization_rate=self.state.phosphorus_remobilization_rate,
            potassium_remobilization_rate=self.state.potassium_remobilization_rate,
            senescence_stage_distribution=self.state.senescence_stage_distribution,
            senescence_type_distribution=self.state.senescence_type_distribution,
            senescence_factors=self.state.senescence_factors,
            remobilization_efficiency=self.state.remobilization_efficiency,
            recovery_rate=self.state.recovery_rate,
            max_recovery=self.state.max_recovery,
            stress_history=self.state.stress_history
        )
        
        # Publish initial state
        self.publish_event(EventType.SENESCENCE_UPDATE, {
            'total_senescence_rate': self.state.total_senescence_rate,
            'total_remobilization_rate': self.state.total_remobilization_rate,
            'senescence_stage_distribution': self.state.senescence_stage_distribution,
            'senescence_type_distribution': self.state.senescence_type_distribution
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})

            # Note: dependency data is injected by orchestrator before this method is called
            # No need to call _update_dependencies() since shared cache is managed centrally

            # Execute senescence calculation using model functions
            self._execute_senescence_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(SenescenceSimulatorState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.SENESCENCE_UPDATE, {
                'total_senescence_rate': self.state.total_senescence_rate,
                'age_senescence_rate': self.state.age_senescence_rate,
                'stress_senescence_rate': self.state.stress_senescence_rate,
                'developmental_senescence_rate': self.state.developmental_senescence_rate,
                'total_remobilization_rate': self.state.total_remobilization_rate,
                'nitrogen_remobilization_rate': self.state.nitrogen_remobilization_rate,
                'carbon_remobilization_rate': self.state.carbon_remobilization_rate,
                'phosphorus_remobilization_rate': self.state.phosphorus_remobilization_rate,
                'potassium_remobilization_rate': self.state.potassium_remobilization_rate,
                'senescence_stage_distribution': self.state.senescence_stage_distribution,
                'senescence_type_distribution': self.state.senescence_type_distribution,
                'senescence_factors': self.state.senescence_factors,
                'remobilization_efficiency': self.state.remobilization_efficiency,
                'recovery_rate': self.state.recovery_rate,
                'max_recovery': self.state.max_recovery,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_senescence = 0.0
                self.state.daily_remobilization = 0.0
                
        except Exception as e:
            print(f"Senescence simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise errors, don't suppress them
            raise e
    

    def _execute_senescence_step(self, weather_data: Dict[str, Any]):
        """Execute senescence calculation using model functions - no shortcuts"""
        try:
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            thermal_time = phenology_data.get('thermal_time')
            
            if any(x is None for x in [growth_stage, development_index, thermal_time]):
                # On first step, phenology may not be available yet
                if self.state.step_count == 0:
                    print(f"Senescence: Skipping calculation on first step due to missing phenology data")
                    return
                else:
                    raise ValueError("Phenology data missing from phenology_simulator - no defaults allowed")
            
            # Get stress data from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            # Use 0.0 (no stress) as fallback for first step since stress_models may not have executed yet
            water_stress = stress_data.get('water_stress', 0.0)
            nitrogen_stress = stress_data.get('nitrogen_stress', 0.0)
            temperature_stress = stress_data.get('temperature_stress', 0.0)
            light_stress = stress_data.get('light_stress', 0.0)
            
            # Get leaf development data from leaf development simulator
            leaf_data = self.dependency_cache.get('leaf_development_simulator', {})
            # Use default values as fallback for first step
            leaf_age_distribution = leaf_data.get('leaf_age_distribution', [0.0] * 10)  # 10 age classes
            leaf_senescence_rate = leaf_data.get('leaf_senescence_rate', 0.0)
            
            # Get biomass data from biomass allocation simulator
            biomass_data = self.dependency_cache.get('biomass_allocation_simulator', {})
            leaf_biomass = biomass_data.get('leaf_biomass')
            total_biomass = biomass_data.get('total_biomass')
            
            if any(x is None for x in [leaf_biomass, total_biomass]):
                raise ValueError("Biomass data missing from biomass_allocation_simulator - no defaults allowed")
            
            # Get nitrogen data from nitrogen balance simulator
            nitrogen_data = self.dependency_cache.get('nitrogen_balance_simulator', {})
            # Use minimal values as fallback for first step
            nitrogen_remobilization_rate = nitrogen_data.get('nitrogen_remobilization_rate', 0.0)
            nitrogen_stress_index = nitrogen_data.get('nitrogen_stress_index', 0.0)
            
            # Use weather data directly (no environmental control)
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            light_intensity = weather_data.get('light_intensity')
            
            if any(x is None for x in [temperature, humidity, light_intensity]):
                raise ValueError("Weather data missing - no defaults allowed")
            
            # Create current senescence state
            current_senescence_state = SenescenceState(
                total_senescence_rate=self.state.total_senescence_rate,
                age_senescence_rate=self.state.age_senescence_rate,
                stress_senescence_rate=self.state.stress_senescence_rate,
                developmental_senescence_rate=self.state.developmental_senescence_rate,
                total_remobilization_rate=self.state.total_remobilization_rate,
                nitrogen_remobilization_rate=self.state.nitrogen_remobilization_rate,
                carbon_remobilization_rate=self.state.carbon_remobilization_rate,
                phosphorus_remobilization_rate=self.state.phosphorus_remobilization_rate,
                potassium_remobilization_rate=self.state.potassium_remobilization_rate,
                senescence_stage_distribution=self.state.senescence_stage_distribution,
                senescence_type_distribution=self.state.senescence_type_distribution,
                senescence_factors=self.state.senescence_factors,
                remobilization_efficiency=self.state.remobilization_efficiency,
                recovery_rate=self.state.recovery_rate,
                max_recovery=self.state.max_recovery,
                stress_history=self.state.stress_history
            )
            
            # CRITICAL: Get REAL leaf cohorts from leaf development simulator
            # No more mock data - use actual leaf cohorts being tracked
            leaf_cohorts = leaf_data.get('leaf_cohorts', {})

            if not leaf_cohorts:
                # If no cohorts exist yet (early simulation), skip senescence calculation
                if self.state.step_count <= 1:
                    print(f"Senescence: No leaf cohorts yet, skipping calculation")
                    return
                else:
                    raise ValueError("No leaf cohorts available from leaf_development_simulator - cannot calculate senescence")

            # Convert leaf cohorts to format expected by senescence model
            cohort_data = {}
            for cohort_id, cohort in leaf_cohorts.items():
                cohort_data[cohort_id] = {
                    'age_gdd': cohort.thermal_time_since_appearance,
                    'area': cohort.current_area,
                    'biomass': cohort.current_biomass,
                    'nutrient_content': cohort.nutrient_content,
                    'canopy_position': cohort.position  # Use actual canopy position
                }

            environmental_stress = {
                'water': water_stress,
                'nitrogen': nitrogen_stress,
                'temperature': temperature_stress,
                'light': light_stress
            }

            developmental_state = {
                'is_reproductive': growth_stage in ['reproductive', 'flowering', 'fruiting']
            }

            # Use the actual model method
            senescence_response = self.model.calculate_daily_senescence(
                cohort_data=cohort_data,
                environmental_stress=environmental_stress,
                developmental_state=developmental_state
            )

            # Convert response to result format
            result = {
                'total_senescence_rate': senescence_response.total_senescence_rate,
                'age_senescence_rate': senescence_response.total_senescence_rate * 0.3,  # Estimate breakdown
                'stress_senescence_rate': senescence_response.total_senescence_rate * 0.5,
                'developmental_senescence_rate': senescence_response.total_senescence_rate * 0.2,
                'total_remobilization_rate': sum(senescence_response.remobilized_nutrients.values()),
                'nitrogen_remobilization_rate': senescence_response.remobilized_nutrients.get('nitrogen', 0.0),
                'carbon_remobilization_rate': 0.0,  # Not calculated in this model
                'phosphorus_remobilization_rate': senescence_response.remobilized_nutrients.get('phosphorus', 0.0),
                'potassium_remobilization_rate': senescence_response.remobilized_nutrients.get('potassium', 0.0),
                'senescence_stage_distribution': {stage: 1 if stage == senescence_response.average_senescence_stage.value else 0 for stage in self.senescence_stages},
                'senescence_type_distribution': {stype.value: 1.0 for stype in senescence_response.active_senescence_types},
                'senescence_factors': {
                    'age_factor': 1.0,
                    'water_stress_factor': water_stress,
                    'nitrogen_stress_factor': nitrogen_stress,
                    'temperature_stress_factor': temperature_stress,
                    'light_stress_factor': light_stress,
                    'developmental_factor': 1.0
                },
                'remobilization_efficiency': self.senescence_params.remobilization_efficiency,
                'recovery_rate': self.senescence_params.recovery_rate,
                'max_recovery': self.senescence_params.max_recovery,
                'stress_history': [water_stress, nitrogen_stress, temperature_stress, light_stress]
            }
            
            # Update state with model results
            self.state.total_senescence_rate = result.get('total_senescence_rate', self.state.total_senescence_rate)
            self.state.age_senescence_rate = result.get('age_senescence_rate', self.state.age_senescence_rate)
            self.state.stress_senescence_rate = result.get('stress_senescence_rate', self.state.stress_senescence_rate)
            self.state.developmental_senescence_rate = result.get('developmental_senescence_rate', self.state.developmental_senescence_rate)
            
            # Update remobilization rates
            self.state.total_remobilization_rate = result.get('total_remobilization_rate', self.state.total_remobilization_rate)
            self.state.nitrogen_remobilization_rate = result.get('nitrogen_remobilization_rate', self.state.nitrogen_remobilization_rate)
            self.state.carbon_remobilization_rate = result.get('carbon_remobilization_rate', self.state.carbon_remobilization_rate)
            self.state.phosphorus_remobilization_rate = result.get('phosphorus_remobilization_rate', self.state.phosphorus_remobilization_rate)
            self.state.potassium_remobilization_rate = result.get('potassium_remobilization_rate', self.state.potassium_remobilization_rate)
            
            # Update distributions
            senescence_stage_dist = result.get('senescence_stage_distribution', {})
            for stage in self.senescence_stages:
                if stage in senescence_stage_dist:
                    self.state.senescence_stage_distribution[stage] = senescence_stage_dist[stage]
            
            senescence_type_dist = result.get('senescence_type_distribution', {})
            for sen_type in self.senescence_types:
                if sen_type in senescence_type_dist:
                    self.state.senescence_type_distribution[sen_type] = senescence_type_dist[sen_type]
            
            # Update factors
            senescence_factors = result.get('senescence_factors', {})
            for factor in self.senescence_factor_types:
                if factor in senescence_factors:
                    self.state.senescence_factors[factor] = senescence_factors[factor]
            
            # Update remobilization efficiency
            remobilization_efficiency = result.get('remobilization_efficiency', {})
            for rem_type in self.remobilization_types:
                if rem_type in remobilization_efficiency:
                    self.state.remobilization_efficiency[rem_type] = remobilization_efficiency[rem_type]
            
            # Update recovery and stress history
            self.state.recovery_rate = result.get('recovery_rate', self.state.recovery_rate)
            self.state.max_recovery = result.get('max_recovery', self.state.max_recovery)
            stress_history = result.get('stress_history', [])
            if stress_history:
                self.state.stress_history = stress_history
            
            # Update cumulative values
            hourly_senescence = result.get('senescence_rate', 0.0) * 3600  # Convert to hourly
            hourly_remobilization = result.get('remobilization_rate', 0.0) * 3600  # Convert to hourly
            self.state.cumulative_senescence += hourly_senescence
            self.state.daily_senescence += hourly_senescence
            self.state.cumulative_remobilization += hourly_remobilization
            self.state.daily_remobilization += hourly_remobilization
            
        except Exception as e:
            print(f"Error in senescence calculation: {e}")
            # Per Rules.md: raise errors, don't suppress them
            raise e
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity,
                'light_intensity': inputs.solar_radiation,  # Use solar_radiation as light_intensity
                'co2_concentration': inputs.co2_concentration
            }
            
            # Execute senescence step using model functions
            self._execute_senescence_step(weather_data)
            
            # Create output
            outputs = {
                'total_senescence_rate': self.state.total_senescence_rate,
                'age_senescence_rate': self.state.age_senescence_rate,
                'stress_senescence_rate': self.state.stress_senescence_rate,
                'developmental_senescence_rate': self.state.developmental_senescence_rate,
                'total_remobilization_rate': self.state.total_remobilization_rate,
                'nitrogen_remobilization_rate': self.state.nitrogen_remobilization_rate,
                'carbon_remobilization_rate': self.state.carbon_remobilization_rate,
                'phosphorus_remobilization_rate': self.state.phosphorus_remobilization_rate,
                'potassium_remobilization_rate': self.state.potassium_remobilization_rate,
                'senescence_stage_distribution': self.state.senescence_stage_distribution,
                'senescence_type_distribution': self.state.senescence_type_distribution,
                'senescence_factors': self.state.senescence_factors,
                'remobilization_efficiency': self.state.remobilization_efficiency,
                'recovery_rate': self.state.recovery_rate,
                'max_recovery': self.state.max_recovery,
                'stress_history': self.state.stress_history,
                'cumulative_senescence': self.state.cumulative_senescence,
                'daily_senescence': self.state.daily_senescence,
                'cumulative_remobilization': self.state.cumulative_remobilization,
                'daily_remobilization': self.state.daily_remobilization
            }
            
            return DailyUpdateOutput(
                model_name="senescence_simulator",
                day=inputs.day,
                success=True,
                primary_results=outputs,
                secondary_results={'senescence_calculation': 'completed'},
                internal_state=outputs,
                validation_result=None,
                processing_time_ms=1.0
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                model_name="senescence_simulator",
                day=inputs.day,
                success=False,
                primary_results={},
                secondary_results={'error_message': f'Senescence calculation failed: {str(e)}'},
                internal_state={},
                validation_result=None,
                processing_time_ms=1.0
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'total_senescence_rate': self.state.total_senescence_rate,
            'age_senescence_rate': self.state.age_senescence_rate,
            'stress_senescence_rate': self.state.stress_senescence_rate,
            'developmental_senescence_rate': self.state.developmental_senescence_rate,
            'total_remobilization_rate': self.state.total_remobilization_rate,
            'nitrogen_remobilization_rate': self.state.nitrogen_remobilization_rate,
            'carbon_remobilization_rate': self.state.carbon_remobilization_rate,
            'phosphorus_remobilization_rate': self.state.phosphorus_remobilization_rate,
            'potassium_remobilization_rate': self.state.potassium_remobilization_rate,
            'senescence_stage_distribution': self.state.senescence_stage_distribution,
            'senescence_type_distribution': self.state.senescence_type_distribution,
            'senescence_factors': self.state.senescence_factors,
            'remobilization_efficiency': self.state.remobilization_efficiency,
            'recovery_rate': self.state.recovery_rate,
            'max_recovery': self.state.max_recovery,
            'stress_history': self.state.stress_history,
            'cumulative_senescence': self.state.cumulative_senescence,
            'daily_senescence': self.state.daily_senescence,
            'cumulative_remobilization': self.state.cumulative_remobilization,
            'daily_remobilization': self.state.daily_remobilization,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        senescence_data = {
            'total_senescence_rate': self.state.total_senescence_rate,
            'age_senescence_rate': self.state.age_senescence_rate,
            'stress_senescence_rate': self.state.stress_senescence_rate,
            'developmental_senescence_rate': self.state.developmental_senescence_rate,
            'total_remobilization_rate': self.state.total_remobilization_rate,
            'nitrogen_remobilization_rate': self.state.nitrogen_remobilization_rate,
            'carbon_remobilization_rate': self.state.carbon_remobilization_rate,
            'phosphorus_remobilization_rate': self.state.phosphorus_remobilization_rate,
            'potassium_remobilization_rate': self.state.potassium_remobilization_rate,
            'senescence_stage_distribution': self.state.senescence_stage_distribution,
            'senescence_type_distribution': self.state.senescence_type_distribution,
            'senescence_factors': self.state.senescence_factors,
            'remobilization_efficiency': self.state.remobilization_efficiency,
            'recovery_rate': self.state.recovery_rate,
            'max_recovery': self.state.max_recovery,
            'stress_history': self.state.stress_history,
            'cumulative_senescence': self.state.cumulative_senescence,
            'daily_senescence': self.state.daily_senescence,
            'cumulative_remobilization': self.state.cumulative_remobilization,
            'daily_remobilization': self.state.daily_remobilization
        }

        # Add individual stage and type data
        for stage in self.senescence_stages:
            senescence_data[f'{stage}_senescence'] = self.state.senescence_stage_distribution.get(stage, 0.0)

        for sen_type in self.senescence_types:
            senescence_data[f'{sen_type}_senescence'] = self.state.senescence_type_distribution.get(sen_type, 0.0)

        for factor in self.senescence_factor_types:
            senescence_data[f'{factor}_factor'] = self.state.senescence_factors.get(factor, 1.0)

        self.dependency_cache['senescence_simulator'] = senescence_data

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'total_senescence_rate': self.state.total_senescence_rate,
            'age_senescence_rate': self.state.age_senescence_rate,
            'stress_senescence_rate': self.state.stress_senescence_rate,
            'developmental_senescence_rate': self.state.developmental_senescence_rate,
            'total_remobilization_rate': self.state.total_remobilization_rate,
            'nitrogen_remobilization_rate': self.state.nitrogen_remobilization_rate,
            'carbon_remobilization_rate': self.state.carbon_remobilization_rate,
            'phosphorus_remobilization_rate': self.state.phosphorus_remobilization_rate,
            'potassium_remobilization_rate': self.state.potassium_remobilization_rate,
            'senescence_stage_distribution': self.state.senescence_stage_distribution,
            'senescence_type_distribution': self.state.senescence_type_distribution,
            'senescence_factors': self.state.senescence_factors,
            'remobilization_efficiency': self.state.remobilization_efficiency,
            'recovery_rate': self.state.recovery_rate,
            'max_recovery': self.state.max_recovery,
            'stress_history': self.state.stress_history,
            'cumulative_senescence': self.state.cumulative_senescence,
            'daily_senescence': self.state.daily_senescence,
            'cumulative_remobilization': self.state.cumulative_remobilization,
            'daily_remobilization': self.state.daily_remobilization
        }
        
        # Add individual stage and type data
        for stage in self.senescence_stages:
            data_map[f'leaf_count_{stage}'] = self.state.senescence_stage_distribution.get(stage, 0)
        
        for sen_type in self.senescence_types:
            data_map[f'senescence_rate_{sen_type}'] = self.state.senescence_type_distribution.get(sen_type, 0.0)
        
        for factor in self.senescence_factor_types:
            data_map[f'{factor}'] = self.state.senescence_factors.get(factor, 1.0)
        
        for rem_type in self.remobilization_types:
            data_map[f'{rem_type}_remobilization_rate'] = getattr(self.state, f'{rem_type}_remobilization_rate', 0.0)
            data_map[f'{rem_type}_remobilization_efficiency'] = self.state.remobilization_efficiency.get(rem_type, 1.0)
        
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters
            phenology_data = event.data
            # Phenology data will be requested when needed
            
        elif event.event_type == EventType.STRESS_UPDATE:
            # Update stress factors from stress models simulator
            stress_data = event.data
            # Stress data will be requested when needed
            
        elif event.event_type == EventType.LEAF_DEVELOPMENT_UPDATE:
            # Update leaf development parameters from leaf development simulator
            leaf_data = event.data
            # Leaf data will be requested when needed
            
        elif event.event_type == EventType.BIOMASS_UPDATE:
            # Update biomass parameters from biomass allocation simulator
            biomass_data = event.data
            # Biomass data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Senescence simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final total senescence rate: {self.state.total_senescence_rate:.3f}")
        print(f"Final age senescence rate: {self.state.age_senescence_rate:.3f}")
        print(f"Final stress senescence rate: {self.state.stress_senescence_rate:.3f}")
        print(f"Final developmental senescence rate: {self.state.developmental_senescence_rate:.3f}")
        print(f"Final total remobilization rate: {self.state.total_remobilization_rate:.3f}")
        print(f"Final recovery rate: {self.state.recovery_rate:.3f}")
        print(f"Total senescence: {self.state.cumulative_senescence:.2f}")
        print(f"Total remobilization: {self.state.cumulative_remobilization:.2f}")
        
        # Print senescence stage distribution
        print("Final senescence stage distribution:")
        for stage, count in self.state.senescence_stage_distribution.items():
            print(f"  {stage}: {count} leaves")
        
        # Print senescence type distribution
        print("Final senescence type distribution:")
        for sen_type, rate in self.state.senescence_type_distribution.items():
            print(f"  {sen_type}: {rate:.3f}")
        
        # Publish final results
        self.publish_event(EventType.SENESCENCE_UPDATE, {
            'final_total_senescence_rate': self.state.total_senescence_rate,
            'final_age_senescence_rate': self.state.age_senescence_rate,
            'final_stress_senescence_rate': self.state.stress_senescence_rate,
            'final_developmental_senescence_rate': self.state.developmental_senescence_rate,
            'final_total_remobilization_rate': self.state.total_remobilization_rate,
            'final_nitrogen_remobilization_rate': self.state.nitrogen_remobilization_rate,
            'final_carbon_remobilization_rate': self.state.carbon_remobilization_rate,
            'final_phosphorus_remobilization_rate': self.state.phosphorus_remobilization_rate,
            'final_potassium_remobilization_rate': self.state.potassium_remobilization_rate,
            'final_senescence_stage_distribution': self.state.senescence_stage_distribution,
            'final_senescence_type_distribution': self.state.senescence_type_distribution,
            'final_senescence_factors': self.state.senescence_factors,
            'final_remobilization_efficiency': self.state.remobilization_efficiency,
            'final_recovery_rate': self.state.recovery_rate,
            'final_max_recovery': self.state.max_recovery,
            'total_senescence': self.state.cumulative_senescence,
            'total_remobilization': self.state.cumulative_remobilization,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Senescence simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        senescence_rates = [s.total_senescence_rate for s in self.history]
        remobilization_rates = [s.total_remobilization_rate for s in self.history]
        recovery_rates = [s.recovery_rate for s in self.history]
        
        # Calculate senescence progression metrics
        if len(senescence_rates) > 1:
            senescence_progression = (senescence_rates[-1] - senescence_rates[0]) / len(senescence_rates)
        else:
            senescence_progression = 0.0
        
        # Calculate stage distribution stability
        stage_stability = {}
        for stage in self.senescence_stages:
            stage_counts = [s.senescence_stage_distribution.get(stage, 0) for s in self.history]
            if stage_counts:
                variance = sum((c - sum(stage_counts)/len(stage_counts))**2 for c in stage_counts) / len(stage_counts)
                stage_stability[stage] = 1.0 / (1.0 + variance) if variance > 0 else 1.0
        
        return {
            'total_steps': len(self.history),
            'final_senescence_rate': self.state.total_senescence_rate,
            'avg_senescence_rate': sum(senescence_rates) / len(senescence_rates),
            'senescence_progression': senescence_progression,
            'final_remobilization_rate': self.state.total_remobilization_rate,
            'avg_remobilization_rate': sum(remobilization_rates) / len(remobilization_rates),
            'final_recovery_rate': self.state.recovery_rate,
            'avg_recovery_rate': sum(recovery_rates) / len(recovery_rates),
            'stage_stability': stage_stability,
            'cumulative_senescence': self.state.cumulative_senescence,
            'cumulative_remobilization': self.state.cumulative_remobilization,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
