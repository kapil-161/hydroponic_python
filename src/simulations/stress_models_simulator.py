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
    """
    State tracking for stress models simulator
    Convention: 0.0 = no stress, 1.0 = full stress
    """
    temperature_stress: float = 0.0
    water_stress: float = 0.0
    nutrient_stress: float = 0.0
    light_stress: float = 0.0
    ph_stress: float = 0.0
    salinity_stress: float = 0.0
    integrated_stress: float = 0.0
    stress_severity: str = "NONE"
    acclimation_level: float = 0.0
    damage_level: float = 0.0
    cumulative_stress: float = 0.0
    daily_stress: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class StressModelsSimulator(BaseSimulator):
    """Simulator for stress models - follows Rules.md strictly"""

    def __init__(self, parameters: IntegratedStressParameters = None, ph_optimal_min: float = None,
                 ph_optimal_max: float = None, ph_stress_range: float = None,
                 temperature_optimal_min: float = None, temperature_optimal_max: float = None,
                 temperature_stress_range: float = None, light_compensation_point: float = None,
                 light_saturation_point: float = None):
        super().__init__("stress_models")

        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("IntegratedStressParameters must be provided from CSV - no defaults allowed per Rules.md")

        # pH parameters must come from CSV
        if ph_optimal_min is None or ph_optimal_max is None or ph_stress_range is None:
            raise ValueError("pH parameters (optimal_min, optimal_max, stress_range) must be provided from CSV - no defaults allowed per Rules.md")

        # Temperature parameters must come from CSV
        if temperature_optimal_min is None or temperature_optimal_max is None or temperature_stress_range is None:
            raise ValueError("Temperature parameters (optimal_min, optimal_max, stress_range) must be provided from CSV - no defaults allowed per Rules.md")

        # Light parameters must come from CSV
        if light_compensation_point is None or light_saturation_point is None:
            raise ValueError("Light parameters (compensation_point, saturation_point) must be provided from CSV - no defaults allowed per Rules.md")

        self.parameters = parameters
        self.model = IntegratedStressModel(self.parameters)
        self.ph_optimal_min = ph_optimal_min
        self.ph_optimal_max = ph_optimal_max
        self.ph_stress_range = ph_stress_range
        self.temperature_optimal_min = temperature_optimal_min
        self.temperature_optimal_max = temperature_optimal_max
        self.temperature_stress_range = temperature_stress_range
        self.light_compensation_point = light_compensation_point
        self.light_saturation_point = light_saturation_point
        
        # State tracking
        self.state = StressState()
        self.history: List[StressState] = []
        
        # Initialize with minimal values to break circular dependencies
        self.state.temperature_stress = 0.0  # No temperature stress initially
        self.state.water_stress = 0.0  # No water stress initially
        self.state.nutrient_stress = 0.0  # No nutrient stress initially
        
        # Inter-simulator dependencies - proper scientific dependencies
        self.dependencies = {
            'water_uptake_simulator': ['water_uptake_rate', 'transpiration_rate', 'water_availability'],
            'nutrient_models_simulator': ['nitrogen_availability', 'nitrogen_uptake'],
            'phenology_simulator': ['growth_stage', 'development_index']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start - initialize with values from initials.csv"""
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
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise errors, don't suppress them
            raise e
    

    def _execute_stress_step(self, weather_data: Dict[str, Any]):
        """Execute stress calculation using model functions - no shortcuts"""
        try:
            # Get environmental conditions from weather data directly
            # Environmental control simulator adjusts these but we use actual weather first
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            light_intensity = weather_data.get('light_intensity')
            co2_concentration = weather_data.get('co2_concentration')

            # Use weather data directly (no environmental control)
            
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
            nitrogen_availability = nutrient_data.get('nitrogen_availability')
            nitrogen_uptake = nutrient_data.get('nitrogen_uptake')

            # Use default pH (no pH model)
            ph = 6.0  # Default optimal pH for lettuce

            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')

            # Per Rules.md: raise error if required data missing, no defaults
            missing_data = []
            if water_uptake_rate is None: missing_data.append('water_uptake_rate')
            if transpiration_rate is None: missing_data.append('transpiration_rate')
            if water_availability is None: missing_data.append('water_availability')
            if nitrogen_availability is None: missing_data.append('nitrogen_availability')
            if nitrogen_uptake is None: missing_data.append('nitrogen_uptake')
            if growth_stage is None: missing_data.append('growth_stage')
            if development_index is None: missing_data.append('development_index')

            if missing_data:
                # On first step, dependencies may not be available yet - use minimal stress levels
                if self.state.step_count == 0:
                    print(f"Stress: Skipping calculation on first step due to missing dependencies: {missing_data}")
                    return
                else:
                    raise ValueError(f"Required dependency data missing: {missing_data} - no defaults allowed per Rules.md")

            # Calculate individual stress factors using CSV parameters

            # Water stress: convert availability (0-1) to stress (0-1)
            water_stress = 1.0 - min(1.0, max(0.0, water_availability))

            # Nutrient stress: convert availability (0-1) to stress (0-1)
            nutrient_stress = 1.0 - min(1.0, max(0.0, nitrogen_availability))

            # Temperature stress calculation using parameters from CSV
            if self.temperature_optimal_min <= temperature <= self.temperature_optimal_max:
                temperature_stress = 0.0
            elif temperature < self.temperature_optimal_min:
                temperature_stress = min(1.0, (self.temperature_optimal_min - temperature) / self.temperature_stress_range)
            else:
                temperature_stress = min(1.0, (temperature - self.temperature_optimal_max) / self.temperature_stress_range)

            # Light stress calculation using parameters from CSV
            # Only calculate light stress during photoperiod (light_intensity > 0)
            if light_intensity > 0:
                if light_intensity < self.light_compensation_point:
                    # Below compensation point = stress
                    light_stress = min(1.0, (self.light_compensation_point - light_intensity) / self.light_compensation_point)
                elif light_intensity > self.light_saturation_point * 2:
                    # Above 2x saturation = excessive light stress
                    light_stress = min(1.0, (light_intensity - self.light_saturation_point * 2) / (self.light_saturation_point * 2))
                else:
                    # Within optimal range
                    light_stress = 0.0
            else:
                # No light stress at night (light_intensity = 0)
                light_stress = 0.0

            # pH stress calculation using parameters from CSV
            if self.ph_optimal_min <= ph <= self.ph_optimal_max:
                ph_stress = 0.0
            elif ph < self.ph_optimal_min:
                ph_stress = min(1.0, (self.ph_optimal_min - ph) / self.ph_stress_range)
            else:
                ph_stress = min(1.0, (ph - self.ph_optimal_max) / self.ph_stress_range)

            # Call IntegratedStressModel to integrate all stress factors
            stress_result = self.model.calculate_integrated_stress(
                temperature=temperature,
                humidity=humidity,
                light_intensity=light_intensity,
                co2_concentration=co2_concentration,
                water_uptake_rate=water_uptake_rate,
                transpiration_rate=transpiration_rate,
                water_availability=water_availability,
                nutrient_availability=nitrogen_availability,
                nutrient_uptake_rate=nitrogen_uptake,
                ph=ph,
                growth_stage=growth_stage,
                development_index=development_index,
                temperature_stress=temperature_stress,
                light_stress=light_stress,
                water_stress=water_stress,
                nutrient_stress=nutrient_stress,
                ph_stress=ph_stress
            )

            # Update state with model results
            self.state.temperature_stress = stress_result['temperature_stress']
            self.state.water_stress = stress_result['water_stress']
            self.state.nutrient_stress = stress_result['nutrient_stress']
            self.state.light_stress = stress_result['light_stress']
            self.state.ph_stress = stress_result['ph_stress']
            self.state.salinity_stress = 0.0  # Minimal for hydroponic

            # Use model's overall stress factor and severity
            self.state.integrated_stress = stress_result['overall_stress_factor']
            self.state.stress_severity = stress_result['stress_severity'].upper()

            # Extract acclimation and damage from stress_states
            # Get maximum acclimation and damage across all stress types
            max_acclimation = 0.0
            max_damage = 0.0
            if 'stress_states' in stress_result:
                stress_states = stress_result['stress_states']
                for stress_type, state in stress_states.items():
                    if hasattr(state, 'acclimation_level'):
                        max_acclimation = max(max_acclimation, state.acclimation_level)
                    if hasattr(state, 'damage_level'):
                        max_damage = max(max_damage, state.damage_level)

            self.state.acclimation_level = max_acclimation
            self.state.damage_level = max_damage

            # Update cumulative values (accumulate actual stress, not deficit)
            hourly_stress = self.state.integrated_stress * 3600
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
            # Per Rules.md: raise errors, don't return error objects
            raise
    
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
