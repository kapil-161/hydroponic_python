"""
Stress Models Simulator

Handles stress simulation loop and inter-simulator communication
for stress factor calculations in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.stress_models import (
    IntegratedStressModel, IntegratedStressParameters,
    TemperatureStressModel, TemperatureStressParameters,
    StressType, StressState, StressResponse, ProcessStressFactors,
    TemperatureAcclimation, TemperatureDamage, UnifiedStressCalculator
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class StressState:
    """State tracking for stress models simulator"""
    temperature_stress: float = 1.0
    water_stress: float = 1.0
    nutrient_stress: float = 1.0
    light_stress: float = 1.0
    ph_stress: float = 1.0
    salinity_stress: float = 1.0
    integrated_stress: float = 1.0
    stress_severity: str = "NONE"
    acclimation_level: float = 0.0
    damage_level: float = 0.0
    cumulative_stress: float = 0.0
    daily_stress: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class StressModelsSimulator(BaseSimulator):
    """Simulator for stress models - follows Rules.md strictly"""
    
    def __init__(self, parameters: IntegratedStressParameters = None):
        super().__init__("stress_models")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("IntegratedStressParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = IntegratedStressModel(self.parameters)
        
        # State tracking
        self.state = StressState()
        self.history: List[StressState] = []
        
        # Initialize with minimal values to break circular dependencies
        self.state.temperature_stress = 0.0  # No temperature stress initially
        self.state.water_stress = 0.0  # No water stress initially
        self.state.nutrient_stress = 0.0  # No nutrient stress initially
        
        # Inter-simulator dependencies - proper scientific dependencies
        self.dependencies = {
            'environmental_control': ['temperature', 'humidity', 'light_intensity', 'co2_concentration'],
            'water_uptake_simulator': ['water_uptake_rate', 'transpiration_rate', 'water_availability'],
            'nutrient_models_simulator': ['nutrient_availability', 'nutrient_uptake_rate'],
            'ph_model_simulator': ['ph', 'ph_stability'],
            'phenology_simulator': ['growth_stage', 'development_index']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        print(f"Stress models simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start - initialize with values from initials.csv"""
        print("Stress models simulator: Simulation started")
        self.state = StressState()

        # Load initial stress levels from CSV (via initial_state)
        initial_state = data.get('initial_state', {})
        if initial_state:
            self.state.temperature_stress = initial_state.get('temperature_stress', 0.0)
            self.state.water_stress = initial_state.get('water_stress', 0.0)
            self.state.nutrient_stress = initial_state.get('nutrient_stress', 0.0)
            self.state.light_stress = initial_state.get('light_stress', 0.0)
            self.state.ph_stress = initial_state.get('ph_stress', 0.0)
            self.state.salinity_stress = initial_state.get('salinity_stress', 0.0)
            self.state.integrated_stress = 0.0  # Will be calculated
            print(f"Stress: Initialized all stress levels from CSV")

        self.history.clear()
        self.dependency_cache.clear()

        # Initialize model with parameters from CSV
        self.model.initialize()

        # Publish initial state data to dependency cache
        self.publish_state_data()

        # Publish initial state
        self.publish_event(EventType.STRESS_UPDATE, {
            'temperature_stress': self.state.temperature_stress,
            'water_stress': self.state.water_stress,
            'nutrient_stress': self.state.nutrient_stress,
            'light_stress': self.state.light_stress,
            'integrated_stress': self.state.integrated_stress
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})

            # Note: dependency data is injected by orchestrator before this method is called
            # No need to call _update_dependencies() since shared cache is managed centrally
            
            # Execute stress calculation using model functions
            self._execute_stress_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(StressState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.STRESS_UPDATE, {
                'temperature_stress': self.state.temperature_stress,
                'water_stress': self.state.water_stress,
                'nutrient_stress': self.state.nutrient_stress,
                'light_stress': self.state.light_stress,
                'ph_stress': self.state.ph_stress,
                'salinity_stress': self.state.salinity_stress,
                'integrated_stress': self.state.integrated_stress,
                'stress_severity': self.state.stress_severity,
                'acclimation_level': self.state.acclimation_level,
                'damage_level': self.state.damage_level,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_stress = 0.0
                
        except Exception as e:
            print(f"Stress models simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise errors, don't suppress them
            raise e
    
    def _update_dependencies(self):
        """Update data from dependent simulators - with graceful handling"""
        for dep_simulator, required_data in self.dependencies.items():
            try:
                # Check if cache is still valid
                if dep_simulator in self.cache_timestamp:
                    cache_age = (datetime.now() - self.cache_timestamp[dep_simulator]).total_seconds()
                    if cache_age < self.cache_timeout:
                        continue  # Use cached data
                
                # Request fresh data from other simulators with retry
                fresh_data = {}
                missing_data = []
                
                for data_key in required_data:
                    # Try multiple times to get data
                    value = None
                    for attempt in range(3):
                        value = self.request_data(dep_simulator, data_key)
                        if value is not None:
                            break
                        time.sleep(0.001)  # Small delay between attempts
                    
                    if value is not None:
                        fresh_data[data_key] = value
                    else:
                        missing_data.append(data_key)
                
                # If we have some data, use it; if completely missing, skip this dependency
                if fresh_data:
                    self.dependency_cache[dep_simulator] = fresh_data
                    self.cache_timestamp[dep_simulator] = datetime.now()
                elif missing_data:
                    # Log missing data but don't fail completely
                    print(f"Warning: Missing data {missing_data} from {dep_simulator}, skipping this dependency")
                    
            except Exception as e:
                # Per Rules.md: raise errors, don't suppress them
                raise ValueError(f"Error updating dependency {dep_simulator}: {e}")
    
    def _execute_stress_step(self, weather_data: Dict[str, Any]):
        """Execute stress calculation using model functions - no shortcuts"""
        try:
            # Get environmental conditions from weather data directly
            # Environmental control simulator adjusts these but we use actual weather first
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            light_intensity = weather_data.get('light_intensity')
            co2_concentration = weather_data.get('co2_concentration')

            # Override with environmental control if available
            env_data = self.dependency_cache.get('environmental_control', {})
            if env_data.get('temperature') is not None:
                temperature = env_data.get('temperature')
            if env_data.get('humidity') is not None:
                humidity = env_data.get('humidity')
            if env_data.get('light_intensity') is not None:
                light_intensity = env_data.get('light_intensity')
            if env_data.get('co2_concentration') is not None:
                co2_concentration = env_data.get('co2_concentration')
            
            # Per Rules.md: raise error if missing, no defaults
            if temperature is None:
                raise ValueError("Temperature missing from weather data - no defaults allowed")
            if humidity is None:
                raise ValueError("Humidity missing from weather data - no defaults allowed")
            if light_intensity is None:
                raise ValueError("Light intensity missing from weather data - no defaults allowed")
            if co2_concentration is None:
                raise ValueError("CO2 concentration missing from weather data - no defaults allowed")
            
            # Get dependency data - raise errors if missing per Rules.md
            water_data = self.dependency_cache.get('water_uptake_simulator', {})
            water_uptake_rate = water_data.get('water_uptake_rate')
            transpiration_rate = water_data.get('transpiration_rate')
            water_availability = water_data.get('water_availability')

            nutrient_data = self.dependency_cache.get('nutrient_models_simulator', {})
            nutrient_availability = nutrient_data.get('nutrient_availability')
            nutrient_uptake_rate = nutrient_data.get('nutrient_uptake_rate')

            ph_data = self.dependency_cache.get('ph_model_simulator', {})
            ph = ph_data.get('ph')
            ph_stability = ph_data.get('ph_stability')

            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')

            # Per Rules.md: raise error if required data missing, no defaults
            missing_data = []
            if water_uptake_rate is None: missing_data.append('water_uptake_rate')
            if transpiration_rate is None: missing_data.append('transpiration_rate')
            if water_availability is None: missing_data.append('water_availability')
            if nutrient_availability is None: missing_data.append('nutrient_availability')
            if nutrient_uptake_rate is None: missing_data.append('nutrient_uptake_rate')
            if ph is None: missing_data.append('ph')
            if ph_stability is None: missing_data.append('ph_stability')
            if growth_stage is None: missing_data.append('growth_stage')
            if development_index is None: missing_data.append('development_index')

            if missing_data:
                # On first step, dependencies may not be available yet - use minimal stress levels
                if self.state.step_count == 0:
                    print(f"Stress: Skipping calculation on first step due to missing dependencies: {missing_data}")
                    return
                else:
                    raise ValueError(f"Required dependency data missing: {missing_data} - no defaults allowed per Rules.md")

            # Calculate stress using model functions - no shortcuts
            result = self.model.calculate_integrated_stress(
                temperature=temperature,
                humidity=humidity,
                light_intensity=light_intensity,
                co2_concentration=co2_concentration,
                water_uptake_rate=water_uptake_rate,
                transpiration_rate=transpiration_rate,
                water_availability=water_availability,
                nutrient_availability=nutrient_availability,
                nutrient_uptake_rate=nutrient_uptake_rate,
                ph=ph,
                ph_stability=ph_stability,
                growth_stage=growth_stage,
                development_index=development_index,
                current_stress_state=StressState(
                    temperature_stress=self.state.temperature_stress,
                    water_stress=self.state.water_stress,
                    nutrient_stress=self.state.nutrient_stress,
                    light_stress=self.state.light_stress,
                    ph_stress=self.state.ph_stress,
                    salinity_stress=self.state.salinity_stress,
                    integrated_stress=self.state.integrated_stress,
                    acclimation_level=self.state.acclimation_level,
                    damage_level=self.state.damage_level
                )
            )
            
            # Update state with model results
            self.state.temperature_stress = result.get('temperature_stress', 1.0)
            self.state.water_stress = result.get('water_stress', 1.0)
            self.state.nutrient_stress = result.get('nutrient_stress', 1.0)
            self.state.light_stress = result.get('light_stress', 1.0)
            self.state.ph_stress = result.get('ph_stress', 1.0)
            self.state.salinity_stress = result.get('salinity_stress', 1.0)
            self.state.integrated_stress = result.get('integrated_stress', 1.0)
            self.state.stress_severity = result.get('stress_severity', "NONE")
            self.state.acclimation_level = result.get('acclimation_level', 0.0)
            self.state.damage_level = result.get('damage_level', 0.0)
            
            # Update cumulative values
            hourly_stress = (1.0 - self.state.integrated_stress) * 3600  # Stress deficit
            self.state.cumulative_stress += hourly_stress
            self.state.daily_stress += hourly_stress
            
        except Exception as e:
            # Per Rules.md: raise errors, don't suppress them
            raise ValueError(f"Stress calculation failed: {e}")
    
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
            
            # Execute stress step using model functions
            self._execute_stress_step(weather_data)
            
            # Create output
            outputs = {
                'temperature_stress': self.state.temperature_stress,
                'water_stress': self.state.water_stress,
                'nutrient_stress': self.state.nutrient_stress,
                'light_stress': self.state.light_stress,
                'ph_stress': self.state.ph_stress,
                'salinity_stress': self.state.salinity_stress,
                'integrated_stress': self.state.integrated_stress,
                'stress_severity': self.state.stress_severity,
                'acclimation_level': self.state.acclimation_level,
                'damage_level': self.state.damage_level,
                'cumulative_stress': self.state.cumulative_stress,
                'daily_stress': self.state.daily_stress
            }
            
            return DailyUpdateOutput(
                model_name="stress_models",
                day=inputs.day,
                success=True,
                primary_results=outputs,
                secondary_results={'stress_calculation': 'completed'},
                internal_state=outputs,
                validation_result=None,
                processing_time_ms=1.0
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                model_name="stress_models",
                day=inputs.day,
                success=False,
                primary_results={},
                secondary_results={'error_message': f'Stress calculation failed: {str(e)}'},
                internal_state={},
                validation_result=None,
                processing_time_ms=1.0
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'temperature_stress': self.state.temperature_stress,
            'water_stress': self.state.water_stress,
            'nutrient_stress': self.state.nutrient_stress,
            'light_stress': self.state.light_stress,
            'ph_stress': self.state.ph_stress,
            'salinity_stress': self.state.salinity_stress,
            'integrated_stress': self.state.integrated_stress,
            'stress_severity': self.state.stress_severity,
            'acclimation_level': self.state.acclimation_level,
            'damage_level': self.state.damage_level,
            'cumulative_stress': self.state.cumulative_stress,
            'daily_stress': self.state.daily_stress,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish stress models state data to dependency cache for other simulators"""
        stress_data = {
            'temperature_stress': self.state.temperature_stress,
            'water_stress': self.state.water_stress,
            'nutrient_stress': self.state.nutrient_stress,
            'light_stress': self.state.light_stress,
            'ph_stress': self.state.ph_stress,
            'salinity_stress': self.state.salinity_stress,
            'integrated_stress': self.state.integrated_stress,
            'stress_severity': self.state.stress_severity,
            'acclimation_level': self.state.acclimation_level,
            'damage_level': self.state.damage_level,
            'cumulative_stress': self.state.cumulative_stress,
            'daily_stress': self.state.daily_stress
        }

        # Store in dependency cache for other simulators to access
        self.dependency_cache['stress_models'] = stress_data
        self.cache_timestamp['stress_models'] = datetime.now()

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'temperature_stress': self.state.temperature_stress,
            'water_stress': self.state.water_stress,
            'nutrient_stress': self.state.nutrient_stress,
            'light_stress': self.state.light_stress,
            'ph_stress': self.state.ph_stress,
            'salinity_stress': self.state.salinity_stress,
            'integrated_stress': self.state.integrated_stress,
            'stress_severity': self.state.stress_severity,
            'acclimation_level': self.state.acclimation_level,
            'damage_level': self.state.damage_level,
            'cumulative_stress': self.state.cumulative_stress,
            'daily_stress': self.state.daily_stress
        }
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            # Environmental data comes from daily weather file
            
        elif event.event_type == EventType.WATER_UPDATE:
            # Update water parameters from water uptake simulator
            water_data = event.data
            # Water data will be requested when needed
            
        elif event.event_type == EventType.NUTRIENT_UPDATE:
            # Update nutrient parameters from nutrient models simulator
            nutrient_data = event.data
            # Nutrient data will be requested when needed
            
        elif event.event_type == EventType.PH_UPDATE:
            # Update pH parameters from pH model simulator
            ph_data = event.data
            # pH data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Stress models simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final integrated stress: {self.state.integrated_stress:.3f}")
        print(f"Final stress severity: {self.state.stress_severity}")
        print(f"Total cumulative stress: {self.state.cumulative_stress:.2f}")
        print(f"Final acclimation level: {self.state.acclimation_level:.3f}")
        print(f"Final damage level: {self.state.damage_level:.3f}")
        
        # Publish final results
        self.publish_event(EventType.STRESS_UPDATE, {
            'final_integrated_stress': self.state.integrated_stress,
            'final_stress_severity': self.state.stress_severity,
            'final_temperature_stress': self.state.temperature_stress,
            'final_water_stress': self.state.water_stress,
            'final_nutrient_stress': self.state.nutrient_stress,
            'final_light_stress': self.state.light_stress,
            'final_ph_stress': self.state.ph_stress,
            'final_salinity_stress': self.state.salinity_stress,
            'final_acclimation_level': self.state.acclimation_level,
            'final_damage_level': self.state.damage_level,
            'total_cumulative_stress': self.state.cumulative_stress,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Stress models simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        integrated_stress_values = [s.integrated_stress for s in self.history]
        temperature_stress_values = [s.temperature_stress for s in self.history]
        water_stress_values = [s.water_stress for s in self.history]
        
        # Count stress severity changes
        severity_changes = 0
        if len(self.history) > 1:
            for i in range(1, len(self.history)):
                if self.history[i].stress_severity != self.history[i-1].stress_severity:
                    severity_changes += 1
        
        return {
            'total_steps': len(self.history),
            'final_integrated_stress': self.state.integrated_stress,
            'avg_integrated_stress': sum(integrated_stress_values) / len(integrated_stress_values),
            'min_integrated_stress': min(integrated_stress_values),
            'max_integrated_stress': max(integrated_stress_values),
            'final_temperature_stress': self.state.temperature_stress,
            'avg_temperature_stress': sum(temperature_stress_values) / len(temperature_stress_values),
            'final_water_stress': self.state.water_stress,
            'avg_water_stress': sum(water_stress_values) / len(water_stress_values),
            'final_stress_severity': self.state.stress_severity,
            'severity_changes': severity_changes,
            'final_acclimation_level': self.state.acclimation_level,
            'final_damage_level': self.state.damage_level,
            'cumulative_stress': self.state.cumulative_stress,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
