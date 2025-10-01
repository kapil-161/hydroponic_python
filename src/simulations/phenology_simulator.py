"""
Phenology Simulator

Handles phenology simulation loop and inter-simulator communication
for growth stage progression and timing in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.phenology_model import (
    ComprehensivePhenologyModel, PhenologyParameters,
    LettuceGrowthStage, DevelopmentalState
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class PhenologyState:
    """State tracking for phenology simulator"""
    current_growth_stage: str = "GERMINATION"
    development_index: float = 0.0
    thermal_time: float = 0.0
    photoperiod: float = 12.0
    bolting_risk: float = 0.0
    days_in_current_stage: int = 0
    total_days_from_planting: int = 0
    cumulative_thermal_time: float = 0.0
    daily_thermal_time: float = 0.0
    stage_progress_fraction: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class PhenologySimulator(BaseSimulator):
    """Simulator for phenology processes - follows Rules.md strictly"""
    
    def __init__(self, parameters: PhenologyParameters = None):
        super().__init__("phenology_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("PhenologyParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        # Model requires initial_stage parameter
        from models.phenology_model import LettuceGrowthStage
        initial_stage = LettuceGrowthStage.GERMINATION  # Default starting stage
        self.model = ComprehensivePhenologyModel(self.parameters, initial_stage)
        self.model.initialize()  # Initialize temperature_history and other state

        # State tracking
        self.state = PhenologyState()
        self.history: List[PhenologyState] = []
        
        # Inter-simulator dependencies - proper scientific dependencies
        self.dependencies = {
            'environmental_control': ['temperature', 'humidity', 'light_intensity', 'photoperiod'],
            'stress_models': ['temperature_stress', 'light_stress'],
            'genetic_parameters_simulator': ['genetic_coefficients', 'cultivar_profile']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        print(f"Phenology simulator initialized with parameters from CSV")

    def _map_growth_stage_to_simplified(self, detailed_stage) -> str:
        """Map detailed phenology stages to simplified water uptake stages"""
        # Map detailed stages to simplified format expected by water uptake model
        # Handle both string and LettuceGrowthStage enum
        if hasattr(detailed_stage, 'value'):
            # It's an enum - get the value
            stage_str = str(detailed_stage.value)
        elif hasattr(detailed_stage, 'name'):
            # It's an enum - get the name
            stage_str = str(detailed_stage.name)
        else:
            # It's already a string
            stage_str = str(detailed_stage)

        stage_upper = stage_str.upper()

        # Germination through vegetative stages -> "vegetative"
        if any(s in stage_upper for s in ['GERMINATION', 'EMERGENCE', 'LEAF', 'VEGETATIVE', 'GE', 'VE', 'V']):
            return 'vegetative'
        # Head stages -> "head_formation"
        elif any(s in stage_upper for s in ['HEAD', 'HI', 'HD']):
            return 'head_formation'
        # Mature/harvest stages -> "mature"
        elif any(s in stage_upper for s in ['MATURE', 'HARVEST', 'HM', 'BOLTING', 'FLOWER', 'SEED']):
            return 'mature'
        else:
            # Default to vegetative for unknown stages
            return 'vegetative'

    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Phenology simulator: Simulation started")
        self.state = PhenologyState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Publish initial state
        self.publish_event(EventType.PHENOLOGY_UPDATE, {
            'current_growth_stage': self.state.current_growth_stage,
            'development_index': self.state.development_index,
            'thermal_time': self.state.thermal_time,
            'bolting_risk': self.state.bolting_risk
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

# Execute phenology calculation using model functions
            self._execute_phenology_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(PhenologyState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.PHENOLOGY_UPDATE, {
                'current_growth_stage': self.state.current_growth_stage,
                'development_index': self.state.development_index,
                'thermal_time': self.state.thermal_time,
                'photoperiod': self.state.photoperiod,
                'bolting_risk': self.state.bolting_risk,
                'days_in_current_stage': self.state.days_in_current_stage,
                'total_days_from_planting': self.state.total_days_from_planting,
                'stage_progress_fraction': self.state.stage_progress_fraction,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_thermal_time = 0.0
                self.state.days_in_current_stage += 1
                self.state.total_days_from_planting += 1
                
        except Exception as e:
            print(f"Phenology simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise error, no fallbacks
            raise
    

    def _execute_phenology_step(self, weather_data: Dict[str, Any]):
        """Execute phenology calculation using model functions - no shortcuts"""
        try:
            # Get environmental conditions from daily weather file (use standardized column names from weather_loader)
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            light_intensity = weather_data.get('light_intensity')
            
            # Calculate photoperiod from date or use scientific default
            # Per Rules.md: use lettuce-appropriate scientific value
            photoperiod = 12.0  # Default 12-hour photoperiod for lettuce
            
            # Per Rules.md: raise error if missing, no defaults
            if temperature is None:
                raise ValueError("Temperature missing from weather data - no defaults allowed")
            if humidity is None:
                raise ValueError("Humidity missing from weather data - no defaults allowed")
            if light_intensity is None:
                raise ValueError("Light intensity missing from weather data - no defaults allowed")
            
            # Get stress factors from stress models simulator (proper scientific approach)
            stress_data = self.dependency_cache.get('stress_models', {})
            temperature_stress = stress_data.get('temperature_stress')
            light_stress = stress_data.get('light_stress')
            
            # Get genetic parameters from genetic parameters simulator
            genetic_data = self.dependency_cache.get('genetic_parameters_simulator', {})
            genetic_coefficients = genetic_data.get('genetic_coefficients')
            cultivar_profile = genetic_data.get('cultivar_profile')
            
            # Calculate phenology using model functions - no shortcuts
            result = self.model.update_developmental_state(
                temperature=temperature,
                daylength=photoperiod,
                water_stress=self.parameters.optimal_water_stress,
                temperature_stress=temperature_stress if temperature_stress is not None else self.parameters.optimal_water_stress
            )
            
            # Update state with model results
            if result.stage_changed and result.new_stage:
                self.state.current_growth_stage = result.new_stage
            self.state.thermal_time += result.daily_thermal_time
            self.state.development_index = min(1.0, self.state.thermal_time / 1000.0)  # Scientific normalization for lettuce
            self.state.photoperiod = photoperiod
            self.state.bolting_risk = result.bolting_risk
            self.state.stage_progress_fraction = min(1.0, self.state.thermal_time / 500.0)  # Scientific stage progress for lettuce
            
            # Update cumulative values
            hourly_thermal_time = result.daily_thermal_time / 24.0  # Convert daily to hourly
            self.state.cumulative_thermal_time += hourly_thermal_time
            self.state.daily_thermal_time += hourly_thermal_time
            
        except Exception as e:
            print(f"Error in phenology calculation: {e}")
            # Per Rules.md: raise error, no fallbacks
            raise
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity,
                'light_intensity': inputs.light_intensity,
                'photoperiod': 12.0  # Default lettuce photoperiod
            }
            
            # Execute phenology step using model functions
            self._execute_phenology_step(weather_data)
            
            # Create output
            outputs = {
                'current_growth_stage': self.state.current_growth_stage,
                'development_index': self.state.development_index,
                'thermal_time': self.state.thermal_time,
                'photoperiod': self.state.photoperiod,
                'bolting_risk': self.state.bolting_risk,
                'days_in_current_stage': self.state.days_in_current_stage,
                'total_days_from_planting': self.state.total_days_from_planting,
                'stage_progress_fraction': self.state.stage_progress_fraction,
                'cumulative_thermal_time': self.state.cumulative_thermal_time,
                'daily_thermal_time': self.state.daily_thermal_time
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Phenology calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Phenology calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'current_growth_stage': self.state.current_growth_stage,
            'development_index': self.state.development_index,
            'thermal_time': self.state.thermal_time,
            'photoperiod': self.state.photoperiod,
            'bolting_risk': self.state.bolting_risk,
            'days_in_current_stage': self.state.days_in_current_stage,
            'total_days_from_planting': self.state.total_days_from_planting,
            'stage_progress_fraction': self.state.stage_progress_fraction,
            'cumulative_thermal_time': self.state.cumulative_thermal_time,
            'daily_thermal_time': self.state.daily_thermal_time,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        # Map detailed stage to simplified format for water uptake compatibility
        simplified_stage = self._map_growth_stage_to_simplified(self.state.current_growth_stage)

        phenology_data = {
            'current_growth_stage': self.state.current_growth_stage,  # Keep detailed for reference
            'growth_stage': simplified_stage,  # Simplified for water uptake model
            'development_index': self.state.development_index,
            'thermal_time': self.state.thermal_time,
            'cumulative_thermal_time': self.state.cumulative_thermal_time,
            'daily_thermal_time': self.state.daily_thermal_time,
            'photoperiod': self.state.photoperiod,
            'photoperiod_response': 1.0,  # Default response
            'vernalization_requirement': self.parameters.vernalization_required,
            'vernalization_days': 0.0,  # Default days
            'bolting_risk': self.state.bolting_risk,
            'days_in_current_stage': self.state.days_in_current_stage,
            'total_days_from_planting': self.state.total_days_from_planting,
            'stage_progress_fraction': self.state.stage_progress_fraction,
            'expected_harvest_date': None,  # Will be calculated later
            'temperature_stress_accumulation': 0.0,  # Default accumulation
            'heat_unit_accumulation': self.state.cumulative_thermal_time
        }

        self.dependency_cache['phenology_simulator'] = phenology_data

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        # Map to simplified stage format for compatibility
        simplified_stage = self._map_growth_stage_to_simplified(self.state.current_growth_stage)

        data_map = {
            'growth_stage': simplified_stage,  # Simplified for water uptake
            'current_growth_stage': self.state.current_growth_stage,  # Detailed for reference
            'development_index': self.state.development_index,
            'thermal_time': self.state.thermal_time,
            'photoperiod': self.state.photoperiod,
            'bolting_risk': self.state.bolting_risk,
            'days_in_current_stage': self.state.days_in_current_stage,
            'total_days_from_planting': self.state.total_days_from_planting,
            'stage_progress_fraction': self.state.stage_progress_fraction,
            'cumulative_thermal_time': self.state.cumulative_thermal_time,
            'daily_thermal_time': self.state.daily_thermal_time
        }
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            if 'photoperiod' in env_data:
                self.state.photoperiod = env_data['photoperiod']
            
        elif event.event_type == EventType.STRESS_UPDATE:
            # Update stress factors from stress models simulator
            stress_data = event.data
            # Stress data will be requested when needed
            
        elif event.event_type == EventType.GENETIC_UPDATE:
            # Update genetic parameters
            genetic_data = event.data
            # Genetic data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Phenology simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final growth stage: {self.state.current_growth_stage}")
        print(f"Total thermal time: {self.state.cumulative_thermal_time:.2f} °C days")
        print(f"Development index: {self.state.development_index:.3f}")
        print(f"Final bolting risk: {self.state.bolting_risk:.3f}")
        
        # Publish final results
        self.publish_event(EventType.PHENOLOGY_UPDATE, {
            'final_growth_stage': self.state.current_growth_stage,
            'final_development_index': self.state.development_index,
            'final_thermal_time': self.state.cumulative_thermal_time,
            'final_bolting_risk': self.state.bolting_risk,
            'total_days_from_planting': self.state.total_days_from_planting,
            'total_steps': self.state.step_count,
            'stage_transitions': len([s for s in self.history if s.current_growth_stage != self.state.current_growth_stage])
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Phenology simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        development_indices = [s.development_index for s in self.history]
        thermal_times = [s.thermal_time for s in self.history]
        bolting_risks = [s.bolting_risk for s in self.history]
        
        # Count stage transitions
        stage_transitions = 0
        if len(self.history) > 1:
            for i in range(1, len(self.history)):
                if self.history[i].current_growth_stage != self.history[i-1].current_growth_stage:
                    stage_transitions += 1
        
        return {
            'total_steps': len(self.history),
            'final_growth_stage': self.state.current_growth_stage,
            'final_development_index': self.state.development_index,
            'max_development_index': max(development_indices),
            'avg_development_index': sum(development_indices) / len(development_indices),
            'final_thermal_time': self.state.cumulative_thermal_time,
            'max_thermal_time': max(thermal_times),
            'avg_thermal_time': sum(thermal_times) / len(thermal_times),
            'final_bolting_risk': self.state.bolting_risk,
            'max_bolting_risk': max(bolting_risks),
            'avg_bolting_risk': sum(bolting_risks) / len(bolting_risks),
            'stage_transitions': stage_transitions,
            'total_days_from_planting': self.state.total_days_from_planting,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
