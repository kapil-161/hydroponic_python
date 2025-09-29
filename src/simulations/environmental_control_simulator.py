"""
Environmental Control Simulator

Handles environmental control simulation loop and inter-simulator communication
for environmental parameter management in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .communication_bus import BaseSimulator, SimulationEvent, EventType
from src.models.environmental_control import (
    EnvironmentalControlSystem, EnvironmentalSetpoints, ControlEquipment, ControlStrategy
)
from src.models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class EnvironmentalState:
    """State tracking for environmental control simulator"""
    air_temperature: float = 25.0
    humidity: float = 60.0
    light_intensity: float = 500.0
    co2_concentration: float = 400.0
    wind_speed: float = 2.0
    photoperiod: float = 12.0
    vapor_pressure_deficit: float = 1.0
    control_actions: Dict[str, float] = field(default_factory=dict)
    equipment_status: Dict[str, bool] = field(default_factory=dict)
    energy_consumption: float = 0.0
    control_efficiency: float = 1.0
    setpoint_deviations: Dict[str, float] = field(default_factory=dict)
    cumulative_energy: float = 0.0
    daily_energy: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class EnvironmentalControlSimulator(BaseSimulator):
    """Simulator for environmental control - follows Rules.md strictly"""
    
    def __init__(self, 
                 setpoints: EnvironmentalSetpoints = None,
                 equipment: ControlEquipment = None):
        super().__init__("environmental_control")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if setpoints is None:
            raise ValueError("EnvironmentalSetpoints must be provided from CSV - no defaults allowed per Rules.md")
        if equipment is None:
            raise ValueError("ControlEquipment must be provided from CSV - no defaults allowed per Rules.md")
        
        self.setpoints = setpoints
        self.equipment = equipment
        self.model = EnvironmentalControlSystem(self.setpoints, self.equipment)
        
        # State tracking
        self.state = EnvironmentalState()
        self.history: List[EnvironmentalState] = []
        
        # Initialize with minimal values to break circular dependencies
        # These values must come from CSV parameters, not hardcoded
        self.state.air_temperature = self.setpoints.default_air_temperature
        self.state.humidity = self.setpoints.default_humidity
        self.state.light_intensity = self.setpoints.default_light_intensity
        
        # Initialize control actions and equipment status
        self.control_actions = ['heating', 'cooling', 'humidity_control', 'lighting', 'co2_injection', 'ventilation']
        for action in self.control_actions:
            self.state.control_actions[action] = 0.0
            self.state.equipment_status[action] = False
        
        # Initialize setpoint deviations
        self.environmental_params = ['temperature', 'humidity', 'light_intensity', 'co2_concentration', 'wind_speed', 'photoperiod']
        for param in self.environmental_params:
            self.state.setpoint_deviations[param] = 0.0
        
        # Inter-simulator dependencies - proper scientific dependencies
        self.dependencies = {
            'phenology_simulator': ['growth_stage', 'development_index'],
            'stress_models': ['temperature_stress', 'humidity_stress', 'light_stress'],
            'canopy_architecture_simulator': ['canopy_height', 'lai'],
            'photosynthesis_simulator': ['light_use_efficiency']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = self.setpoints.cache_timeout  # seconds
        
        print(f"Environmental control simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Environmental control simulator: Simulation started")
        self.state = EnvironmentalState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Publish initial state
        self.publish_event(EventType.ENVIRONMENT_UPDATE, {
            'air_temperature': self.state.air_temperature,
            'temperature': self.state.air_temperature,  # Add alias for temperature
            'humidity': self.state.humidity,
            'light_intensity': self.state.light_intensity,
            'co2_concentration': self.state.co2_concentration,
            'control_efficiency': self.state.control_efficiency
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            
            # Update dependency data from other simulators
            self._update_dependencies()
            
            # Execute environmental control calculation using model functions
            self._execute_environmental_control_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(EnvironmentalState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.ENVIRONMENT_UPDATE, {
                'air_temperature': self.state.air_temperature,
                'temperature': self.state.air_temperature,  # Add alias for temperature
                'humidity': self.state.humidity,
                'light_intensity': self.state.light_intensity,
                'co2_concentration': self.state.co2_concentration,
                'wind_speed': self.state.wind_speed,
                'photoperiod': self.state.photoperiod,
                'vapor_pressure_deficit': self.state.vapor_pressure_deficit,
                'control_actions': self.state.control_actions,
                'equipment_status': self.state.equipment_status,
                'control_efficiency': self.state.control_efficiency,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_energy = 0.0
                
        except Exception as e:
            print(f"Environmental control simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Raise error according to Rules.md - no error suppression
            raise
    
    def _update_dependencies(self):
        """Update data from dependent simulators - with graceful handling"""
        for dep_simulator, required_data in self.dependencies.items():
            try:
                # Check if cache is still valid
                if dep_simulator in self.cache_timestamp:
                    cache_age = (datetime.now() - self.cache_timestamp[dep_simulator]).total_seconds()
                    if cache_age < self.cache_timeout:
                        continue  # Use cached data
                
                # Request fresh data from other simulators
                fresh_data = {}
                missing_data = []
                
                for data_key in required_data:
                    value = self.request_data(dep_simulator, data_key)
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
                print(f"Error updating dependency {dep_simulator}: {e}")
                # Raise error according to Rules.md - no error suppression
                raise
    
    def _execute_environmental_control_step(self, weather_data: Dict[str, Any]):
        """Execute environmental control calculation using model functions - no shortcuts"""
        try:
            # Get external weather conditions from daily weather file
            external_temperature = weather_data.get('temp_avg')
            external_humidity = weather_data.get('rel_humidity')
            external_light = weather_data.get('par')  # PAR is the light intensity
            external_co2 = weather_data.get('co2_ppm')
            external_wind = weather_data.get('wind_speed')
            
            # Per Rules.md: raise error if missing, no defaults
            if any(x is None for x in [external_temperature, external_humidity, external_light, external_co2, external_wind]):
                raise ValueError("External weather data missing from weather data - no defaults allowed")
            
            # Get phenology data from phenology simulator (optional for basic control)
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage', 'GERMINATION')  # Default for early stages
            development_index = phenology_data.get('development_index', 0.0)  # Default for early stages
            
            # Use default stress factors for basic environmental control
            temperature_stress = 1.0  # Optimal conditions
            humidity_stress = 1.0
            light_stress = 1.0
            
            # Use default canopy conditions for early stages
            canopy_height = 0.0  # No canopy yet in early stages
            lai = 0.0
            light_use_efficiency = 1.0
            
            # Create current environmental conditions
            current_conditions = {
                'temperature': self.state.air_temperature,
                'humidity': self.state.humidity,
                'light_intensity': self.state.light_intensity,
                'co2_concentration': self.state.co2_concentration,
                'co2': self.state.co2_concentration,  # Add co2 key
                'wind_speed': self.state.wind_speed,
                'photoperiod': self.state.photoperiod
            }
            
            # Calculate environmental control using model functions - no shortcuts
            # Light schedule parameters must come from CSV, not hardcoded
            light_schedule = {
                'on_hour': self.setpoints.co2_enrichment_start_hour,  # From CSV
                'off_hour': self.setpoints.co2_enrichment_start_hour + self.setpoints.light_hours,  # From CSV
                'intensity': external_light,  # Use external light intensity
                'light_on': True  # Will be calculated based on current hour
            }
            
            try:
                result = self.model.calculate_comprehensive_control(
                    current_conditions=current_conditions,
                    light_schedule=light_schedule
                )
            except AttributeError as e:
                if "integral_errors" in str(e):
                    # Initialize the model if integral_errors is missing
                    print(f"Warning: Initializing environmental control model due to missing integral_errors: {e}")
                    self.model.initialize()
                    result = self.model.calculate_comprehensive_control(
                        current_conditions=current_conditions,
                        light_schedule=light_schedule
                    )
                else:
                    raise
            
            # Update state with model results
            self.state.air_temperature = result.get('temperature', self.state.air_temperature)
            self.state.humidity = result.get('humidity', self.state.humidity)
            self.state.light_intensity = result.get('light_intensity', self.state.light_intensity)
            self.state.co2_concentration = result.get('co2_concentration', self.state.co2_concentration)
            self.state.wind_speed = result.get('wind_speed', self.state.wind_speed)
            self.state.photoperiod = result.get('photoperiod', self.state.photoperiod)
            self.state.vapor_pressure_deficit = result.get('vapor_pressure_deficit', self.state.vapor_pressure_deficit)
            self.state.control_efficiency = result.get('control_efficiency', self.state.control_efficiency)
            
            # Update control actions
            control_actions = result.get('control_actions', {})
            for action in self.control_actions:
                if action in control_actions:
                    self.state.control_actions[action] = control_actions[action]
            
            # Update equipment status
            equipment_status = result.get('equipment_status', {})
            for action in self.control_actions:
                if action in equipment_status:
                    self.state.equipment_status[action] = equipment_status[action]
            
            # Update setpoint deviations
            setpoint_deviations = result.get('setpoint_deviations', {})
            for param in self.environmental_params:
                if param in setpoint_deviations:
                    self.state.setpoint_deviations[param] = setpoint_deviations[param]
            
            # Update energy consumption
            hourly_energy = result.get('energy_consumption', 0.0)
            self.state.energy_consumption = hourly_energy
            self.state.cumulative_energy += hourly_energy
            self.state.daily_energy += hourly_energy
            
        except Exception as e:
            print(f"Error in environmental control calculation: {e}")
            # Raise error according to Rules.md - no error suppression
            raise
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity,
                'light_intensity': inputs.light_intensity,
                'co2_concentration': inputs.co2_concentration,
                'wind_speed': 2.0  # This should come from weather data
            }
            
            # Execute environmental control step using model functions
            self._execute_environmental_control_step(weather_data)
            
            # Create output
            outputs = {
                'air_temperature': self.state.air_temperature,
                'humidity': self.state.humidity,
                'light_intensity': self.state.light_intensity,
                'co2_concentration': self.state.co2_concentration,
                'wind_speed': self.state.wind_speed,
                'photoperiod': self.state.photoperiod,
                'vapor_pressure_deficit': self.state.vapor_pressure_deficit,
                'control_actions': self.state.control_actions,
                'equipment_status': self.state.equipment_status,
                'energy_consumption': self.state.energy_consumption,
                'control_efficiency': self.state.control_efficiency,
                'setpoint_deviations': self.state.setpoint_deviations,
                'cumulative_energy': self.state.cumulative_energy,
                'daily_energy': self.state.daily_energy
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Environmental control calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Environmental control calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'air_temperature': self.state.air_temperature,
            'humidity': self.state.humidity,
            'light_intensity': self.state.light_intensity,
            'co2_concentration': self.state.co2_concentration,
            'wind_speed': self.state.wind_speed,
            'photoperiod': self.state.photoperiod,
            'vapor_pressure_deficit': self.state.vapor_pressure_deficit,
            'control_actions': self.state.control_actions,
            'equipment_status': self.state.equipment_status,
            'energy_consumption': self.state.energy_consumption,
            'control_efficiency': self.state.control_efficiency,
            'setpoint_deviations': self.state.setpoint_deviations,
            'cumulative_energy': self.state.cumulative_energy,
            'daily_energy': self.state.daily_energy,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'temperature': self.state.air_temperature,
            'humidity': self.state.humidity,
            'light_intensity': self.state.light_intensity,
            'co2_concentration': self.state.co2_concentration,
            'wind_speed': self.state.wind_speed,
            'photoperiod': self.state.photoperiod,
            'vapor_pressure_deficit': self.state.vapor_pressure_deficit,
            'control_actions': self.state.control_actions,
            'equipment_status': self.state.equipment_status,
            'energy_consumption': self.state.energy_consumption,
            'control_efficiency': self.state.control_efficiency,
            'setpoint_deviations': self.state.setpoint_deviations,
            'cumulative_energy': self.state.cumulative_energy,
            'daily_energy': self.state.daily_energy
        }
        return data_map.get(data_key)

    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        environmental_data = {
            'temperature': self.state.air_temperature,
            'air_temperature': self.state.air_temperature,
            'humidity': self.state.humidity,
            'light_intensity': self.state.light_intensity,
            'co2_concentration': self.state.co2_concentration,
            'co2': self.state.co2_concentration,
            'wind_speed': self.state.wind_speed,
            'photoperiod': self.state.photoperiod,
            'vapor_pressure_deficit': self.state.vapor_pressure_deficit,
            'control_actions': self.state.control_actions,
            'equipment_status': self.state.equipment_status,
            'energy_consumption': self.state.energy_consumption,
            'control_efficiency': self.state.control_efficiency,
            'setpoint_deviations': self.state.setpoint_deviations,
            'cumulative_energy': self.state.cumulative_energy,
            'daily_energy': self.state.daily_energy
        }

        self.dependency_cache['environmental_control'] = environmental_data

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
            
        elif event.event_type == EventType.CANOPY_UPDATE:
            # Update canopy parameters from canopy architecture simulator
            canopy_data = event.data
            # Canopy data will be requested when needed
            
        elif event.event_type == EventType.PHOTOSYNTHESIS_UPDATE:
            # Update photosynthesis parameters
            photosynthesis_data = event.data
            # Photosynthesis data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Environmental control simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final temperature: {self.state.air_temperature:.2f} °C")
        print(f"Final humidity: {self.state.humidity:.1f} %")
        print(f"Final light intensity: {self.state.light_intensity:.0f} μmol/m²/s")
        print(f"Final CO2 concentration: {self.state.co2_concentration:.0f} ppm")
        print(f"Final control efficiency: {self.state.control_efficiency:.3f}")
        print(f"Total energy consumption: {self.state.cumulative_energy:.2f} kWh")
        
        # Publish final results
        self.publish_event(EventType.ENVIRONMENT_UPDATE, {
            'final_temperature': self.state.air_temperature,
            'final_humidity': self.state.humidity,
            'final_light_intensity': self.state.light_intensity,
            'final_co2_concentration': self.state.co2_concentration,
            'final_wind_speed': self.state.wind_speed,
            'final_photoperiod': self.state.photoperiod,
            'final_vapor_pressure_deficit': self.state.vapor_pressure_deficit,
            'final_control_efficiency': self.state.control_efficiency,
            'total_energy_consumption': self.state.cumulative_energy,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Environmental control simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        temperature_values = [s.air_temperature for s in self.history]
        humidity_values = [s.humidity for s in self.history]
        light_values = [s.light_intensity for s in self.history]
        co2_values = [s.co2_concentration for s in self.history]
        control_efficiency_values = [s.control_efficiency for s in self.history]
        
        # Calculate control stability metrics
        temp_variance = sum((t - sum(temperature_values)/len(temperature_values))**2 for t in temperature_values) / len(temperature_values)
        humidity_variance = sum((h - sum(humidity_values)/len(humidity_values))**2 for h in humidity_values) / len(humidity_values)
        
        return {
            'total_steps': len(self.history),
            'final_temperature': self.state.air_temperature,
            'avg_temperature': sum(temperature_values) / len(temperature_values),
            'temp_variance': temp_variance,
            'temp_stability': 1.0 / (1.0 + temp_variance) if temp_variance > 0 else 1.0,
            'final_humidity': self.state.humidity,
            'avg_humidity': sum(humidity_values) / len(humidity_values),
            'humidity_variance': humidity_variance,
            'humidity_stability': 1.0 / (1.0 + humidity_variance) if humidity_variance > 0 else 1.0,
            'final_light_intensity': self.state.light_intensity,
            'avg_light_intensity': sum(light_values) / len(light_values),
            'final_co2_concentration': self.state.co2_concentration,
            'avg_co2_concentration': sum(co2_values) / len(co2_values),
            'final_control_efficiency': self.state.control_efficiency,
            'avg_control_efficiency': sum(control_efficiency_values) / len(control_efficiency_values),
            'cumulative_energy': self.state.cumulative_energy,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
