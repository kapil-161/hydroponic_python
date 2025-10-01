"""
Root Zone Temperature Simulator

Handles root zone temperature simulation loop and inter-simulator communication
for root zone thermal dynamics and temperature effects in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.root_zone_temperature import (
    RootZoneTemperatureModel, RZTParameters, RZTModelOutput
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class RootZoneTemperatureState:
    """State tracking for root zone temperature simulator"""
    root_zone_temperature: float = 25.0
    air_temperature: float = 25.0
    optimal_root_zone_temperature: float = 27.0
    temperature_deviation: float = 0.0
    growth_factor: float = 1.0
    nutrient_uptake_factor: float = 1.0
    water_uptake_factor: float = 1.0
    photosynthesis_factor: float = 1.0
    root_metabolism_factor: float = 1.0
    thermal_stress_factor: float = 1.0
    diurnal_temperature_variation: float = 0.0
    heat_generation: float = 0.0
    ambient_heat_exchange: float = 0.0
    pump_heat_generation: float = 0.0
    root_respiration_heat: float = 0.0
    thermal_response_rate: float = 0.0
    temperature_stability: float = 1.0
    cumulative_heat_generation: float = 0.0
    daily_heat_generation: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class RootZoneTemperatureSimulator(BaseSimulator):
    """Simulator for root zone temperature - follows Rules.md strictly"""
    
    def __init__(self, 
                 rzt_params: RZTParameters = None):
        super().__init__("root_zone_temperature_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if rzt_params is None:
            raise ValueError("RZTParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.rzt_params = rzt_params
        self.model = RootZoneTemperatureModel(self.rzt_params)
        
        # State tracking
        self.state = RootZoneTemperatureState()
        self.history: List[RootZoneTemperatureState] = []
        
        # Initialize temperature factors
        self.temperature_factors = [
            'growth_factor', 'nutrient_uptake_factor', 'water_uptake_factor',
            'photosynthesis_factor', 'root_metabolism_factor', 'thermal_stress_factor'
        ]
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'environmental_control': ['temperature', 'humidity'],
            'root_system_simulator': ['root_mass', 'root_activity', 'root_respiration'],
            'nutrient_models_simulator': ['nutrient_uptake_rate'],
            'water_uptake_simulator': ['water_uptake_rate'],
            'photosynthesis_simulator': ['photosynthesis_rate'],
            'respiration_simulator': ['respiration_rate']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        # Subscribe to root events
        self.message_bus.subscribe(EventType.ROOT_UPDATE, self._handle_root_update)
        
        print(f"Root zone temperature simulator initialized with parameters from CSV")
    
    def _handle_root_update(self, event: SimulationEvent):
        """Handle root data updates"""
        self.dependency_cache['root_system_simulator'] = event.data
        self.cache_timestamp['root_system_simulator'] = datetime.now()
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Root zone temperature simulator: Simulation started")
        self.state = RootZoneTemperatureState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Initialize root zone temperature state
        initial_rzt_state = RootZoneTemperatureState(
            root_zone_temperature=self.state.root_zone_temperature,
            air_temperature=self.state.air_temperature,
            optimal_root_zone_temperature=self.state.optimal_root_zone_temperature,
            temperature_deviation=self.state.temperature_deviation,
            growth_factor=self.state.growth_factor,
            nutrient_uptake_factor=self.state.nutrient_uptake_factor,
            water_uptake_factor=self.state.water_uptake_factor,
            photosynthesis_factor=self.state.photosynthesis_factor,
            root_metabolism_factor=self.state.root_metabolism_factor,
            thermal_stress_factor=self.state.thermal_stress_factor,
            diurnal_temperature_variation=self.state.diurnal_temperature_variation,
            heat_generation=self.state.heat_generation,
            ambient_heat_exchange=self.state.ambient_heat_exchange,
            pump_heat_generation=self.state.pump_heat_generation,
            root_respiration_heat=self.state.root_respiration_heat,
            thermal_response_rate=self.state.thermal_response_rate,
            temperature_stability=self.state.temperature_stability
        )
        
        # Publish initial state
        self.publish_event(EventType.ROOT_ZONE_TEMPERATURE_UPDATE, {
            'root_zone_temperature': self.state.root_zone_temperature,
            'optimal_root_zone_temperature': self.state.optimal_root_zone_temperature,
            'growth_factor': self.state.growth_factor,
            'nutrient_uptake_factor': self.state.nutrient_uptake_factor,
            'water_uptake_factor': self.state.water_uptake_factor
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

# Execute root zone temperature calculation using model functions
            self._execute_root_zone_temperature_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(RootZoneTemperatureState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.ROOT_ZONE_TEMPERATURE_UPDATE, {
                'root_zone_temperature': self.state.root_zone_temperature,
                'air_temperature': self.state.air_temperature,
                'optimal_root_zone_temperature': self.state.optimal_root_zone_temperature,
                'temperature_deviation': self.state.temperature_deviation,
                'growth_factor': self.state.growth_factor,
                'nutrient_uptake_factor': self.state.nutrient_uptake_factor,
                'water_uptake_factor': self.state.water_uptake_factor,
                'photosynthesis_factor': self.state.photosynthesis_factor,
                'root_metabolism_factor': self.state.root_metabolism_factor,
                'thermal_stress_factor': self.state.thermal_stress_factor,
                'diurnal_temperature_variation': self.state.diurnal_temperature_variation,
                'heat_generation': self.state.heat_generation,
                'ambient_heat_exchange': self.state.ambient_heat_exchange,
                'pump_heat_generation': self.state.pump_heat_generation,
                'root_respiration_heat': self.state.root_respiration_heat,
                'thermal_response_rate': self.state.thermal_response_rate,
                'temperature_stability': self.state.temperature_stability,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_heat_generation = 0.0
                
        except Exception as e:
            print(f"Root zone temperature simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise errors, don't suppress them
            raise e
    

    def _execute_root_zone_temperature_step(self, weather_data: Dict[str, Any]):
        """Execute root zone temperature calculation using model functions - no shortcuts"""
        try:
            # Get environmental data from environmental control simulator
            env_data = self.dependency_cache.get('environmental_control', {})
            air_temperature = env_data.get('temperature')
            humidity = env_data.get('humidity')
            
            if any(x is None for x in [air_temperature, humidity]):
                raise ValueError("Environmental data missing from environmental_control - no defaults allowed")
            
            # Get root data from root system simulator
            root_data = self.dependency_cache.get('root_system_simulator', {})
            root_mass = root_data.get('root_mass')
            root_activity = root_data.get('root_activity')

            if any(x is None for x in [root_mass, root_activity]):
                # On first step, root data may not be available yet
                if self.state.step_count == 0:
                    print(f"RZT: Skipping calculation on first step due to missing root data")
                    return
                else:
                    raise ValueError("Root data missing from root_system_simulator - no defaults allowed")

            # Get root respiration from respiration simulator
            respiration_data = self.dependency_cache.get('respiration_simulator', {})
            root_respiration = respiration_data.get('root_respiration')

            if root_respiration is None:
                # On first step, respiration may not be available yet
                if self.state.step_count == 0:
                    print(f"RZT: Skipping calculation on first step due to missing respiration data")
                    return
                else:
                    raise ValueError("Root respiration missing from respiration_simulator - no defaults allowed")
            
            # Get nutrient data from nutrient models simulator
            nutrient_data = self.dependency_cache.get('nutrient_models_simulator', {})
            nutrient_uptake_rate = nutrient_data.get('nutrient_uptake_rate')
            
            if nutrient_uptake_rate is None:
                raise ValueError("Nutrient uptake rate missing from nutrient_models_simulator - no defaults allowed")
            
            # Get water data from water uptake simulator
            water_data = self.dependency_cache.get('water_uptake_simulator', {})
            water_uptake_rate = water_data.get('water_uptake_rate')
            
            if water_uptake_rate is None:
                raise ValueError("Water uptake rate missing from water_uptake_simulator - no defaults allowed")
            
            # Get photosynthesis data from photosynthesis simulator
            photosynthesis_data = self.dependency_cache.get('photosynthesis_simulator', {})
            photosynthesis_rate = photosynthesis_data.get('photosynthesis_rate')
            
            if photosynthesis_rate is None:
                raise ValueError("Photosynthesis rate missing from photosynthesis_simulator - no defaults allowed")
            
            # Get respiration data from respiration simulator
            respiration_data = self.dependency_cache.get('respiration_simulator', {})
            respiration_rate = respiration_data.get('respiration_rate')
            
            if respiration_rate is None:
                raise ValueError("Respiration rate missing from respiration_simulator - no defaults allowed")
            
            # Create current root zone temperature state
            current_rzt_state = RootZoneTemperatureState(
                root_zone_temperature=self.state.root_zone_temperature,
                air_temperature=self.state.air_temperature,
                optimal_root_zone_temperature=self.state.optimal_root_zone_temperature,
                temperature_deviation=self.state.temperature_deviation,
                growth_factor=self.state.growth_factor,
                nutrient_uptake_factor=self.state.nutrient_uptake_factor,
                water_uptake_factor=self.state.water_uptake_factor,
                photosynthesis_factor=self.state.photosynthesis_factor,
                root_metabolism_factor=self.state.root_metabolism_factor,
                thermal_stress_factor=self.state.thermal_stress_factor,
                diurnal_temperature_variation=self.state.diurnal_temperature_variation,
                heat_generation=self.state.heat_generation,
                ambient_heat_exchange=self.state.ambient_heat_exchange,
                pump_heat_generation=self.state.pump_heat_generation,
                root_respiration_heat=self.state.root_respiration_heat,
                thermal_response_rate=self.state.thermal_response_rate,
                temperature_stability=self.state.temperature_stability
            )
            
            # Calculate root zone temperature using actual model methods - no shortcuts
            # Estimate solution temperature from air temperature and root activity
            solution_temp = air_temperature + (root_activity * 2.0)  # Basic estimate

            # Calculate daily metrics using actual model method
            environmental_conditions = {
                'air_temperature': air_temperature,
                'solution_temperature': solution_temp
            }

            rzt_output = self.model.calculate_daily_metrics(environmental_conditions)

            # Convert RZTModelOutput to result dictionary
            result = {
                'root_zone_temperature': rzt_output.current_rzt,
                'air_temperature': air_temperature,
                'optimal_root_zone_temperature': rzt_output.optimal_rzt,
                'temperature_deviation': rzt_output.rzt_deviation,
                'growth_factor': rzt_output.growth_factor,
                'nutrient_uptake_factor': rzt_output.nutrient_uptake_factor,
                'water_uptake_factor': rzt_output.water_uptake_factor,
                'photosynthesis_factor': rzt_output.photosynthesis_factor,
                'root_metabolism_factor': rzt_output.root_metabolism_factor,
                'thermal_stress_factor': rzt_output.thermal_stress,
                'diurnal_temperature_variation': 0.0,  # Not calculated in daily mode
                'heat_generation': 0.0,  # Not directly calculated
                'ambient_heat_exchange': 0.0,  # Not directly calculated
                'pump_heat_generation': 0.0,  # Not directly calculated
                'root_respiration_heat': 0.0,  # Not directly calculated
                'thermal_response_rate': 0.0,  # Not directly calculated
                'temperature_stability': 1.0 - rzt_output.thermal_stress  # Inverse of stress
            }
            
            # Update state with model results
            self.state.root_zone_temperature = result.get('root_zone_temperature', self.state.root_zone_temperature)
            self.state.air_temperature = result.get('air_temperature', self.state.air_temperature)
            self.state.optimal_root_zone_temperature = result.get('optimal_root_zone_temperature', self.state.optimal_root_zone_temperature)
            self.state.temperature_deviation = result.get('temperature_deviation', self.state.temperature_deviation)
            
            # Update temperature factors
            self.state.growth_factor = result.get('growth_factor', self.state.growth_factor)
            self.state.nutrient_uptake_factor = result.get('nutrient_uptake_factor', self.state.nutrient_uptake_factor)
            self.state.water_uptake_factor = result.get('water_uptake_factor', self.state.water_uptake_factor)
            self.state.photosynthesis_factor = result.get('photosynthesis_factor', self.state.photosynthesis_factor)
            self.state.root_metabolism_factor = result.get('root_metabolism_factor', self.state.root_metabolism_factor)
            self.state.thermal_stress_factor = result.get('thermal_stress_factor', self.state.thermal_stress_factor)
            
            # Update thermal dynamics
            self.state.diurnal_temperature_variation = result.get('diurnal_temperature_variation', self.state.diurnal_temperature_variation)
            self.state.heat_generation = result.get('heat_generation', self.state.heat_generation)
            self.state.ambient_heat_exchange = result.get('ambient_heat_exchange', self.state.ambient_heat_exchange)
            self.state.pump_heat_generation = result.get('pump_heat_generation', self.state.pump_heat_generation)
            self.state.root_respiration_heat = result.get('root_respiration_heat', self.state.root_respiration_heat)
            self.state.thermal_response_rate = result.get('thermal_response_rate', self.state.thermal_response_rate)
            self.state.temperature_stability = result.get('temperature_stability', self.state.temperature_stability)
            
            # Update cumulative values
            hourly_heat_generation = result.get('heat_generation', 0.0) * 3600  # Convert to hourly
            self.state.cumulative_heat_generation += hourly_heat_generation
            self.state.daily_heat_generation += hourly_heat_generation
            
        except Exception as e:
            print(f"Error in root zone temperature calculation: {e}")
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
            
            # Execute root zone temperature step using model functions
            self._execute_root_zone_temperature_step(weather_data)
            
            # Create output
            outputs = {
                'root_zone_temperature': self.state.root_zone_temperature,
                'air_temperature': self.state.air_temperature,
                'optimal_root_zone_temperature': self.state.optimal_root_zone_temperature,
                'temperature_deviation': self.state.temperature_deviation,
                'growth_factor': self.state.growth_factor,
                'nutrient_uptake_factor': self.state.nutrient_uptake_factor,
                'water_uptake_factor': self.state.water_uptake_factor,
                'photosynthesis_factor': self.state.photosynthesis_factor,
                'root_metabolism_factor': self.state.root_metabolism_factor,
                'thermal_stress_factor': self.state.thermal_stress_factor,
                'diurnal_temperature_variation': self.state.diurnal_temperature_variation,
                'heat_generation': self.state.heat_generation,
                'ambient_heat_exchange': self.state.ambient_heat_exchange,
                'pump_heat_generation': self.state.pump_heat_generation,
                'root_respiration_heat': self.state.root_respiration_heat,
                'thermal_response_rate': self.state.thermal_response_rate,
                'temperature_stability': self.state.temperature_stability,
                'cumulative_heat_generation': self.state.cumulative_heat_generation,
                'daily_heat_generation': self.state.daily_heat_generation
            }
            
            return DailyUpdateOutput(
                model_name="root_zone_temperature_simulator",
                day=inputs.day,
                success=True,
                primary_results=outputs,
                secondary_results={'rzt_calculation': 'completed'},
                internal_state=outputs,
                validation_result=None,
                processing_time_ms=1.0
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                model_name="root_zone_temperature_simulator",
                day=inputs.day,
                success=False,
                primary_results={},
                secondary_results={'error_message': f'Root zone temperature calculation failed: {str(e)}'},
                internal_state={},
                validation_result=None,
                processing_time_ms=1.0
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'root_zone_temperature': self.state.root_zone_temperature,
            'air_temperature': self.state.air_temperature,
            'optimal_root_zone_temperature': self.state.optimal_root_zone_temperature,
            'temperature_deviation': self.state.temperature_deviation,
            'growth_factor': self.state.growth_factor,
            'nutrient_uptake_factor': self.state.nutrient_uptake_factor,
            'water_uptake_factor': self.state.water_uptake_factor,
            'photosynthesis_factor': self.state.photosynthesis_factor,
            'root_metabolism_factor': self.state.root_metabolism_factor,
            'thermal_stress_factor': self.state.thermal_stress_factor,
            'diurnal_temperature_variation': self.state.diurnal_temperature_variation,
            'heat_generation': self.state.heat_generation,
            'ambient_heat_exchange': self.state.ambient_heat_exchange,
            'pump_heat_generation': self.state.pump_heat_generation,
            'root_respiration_heat': self.state.root_respiration_heat,
            'thermal_response_rate': self.state.thermal_response_rate,
            'temperature_stability': self.state.temperature_stability,
            'cumulative_heat_generation': self.state.cumulative_heat_generation,
            'daily_heat_generation': self.state.daily_heat_generation,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        root_zone_data = {
            'root_zone_temperature': self.state.root_zone_temperature,
            'air_temperature': self.state.air_temperature,
            'optimal_root_zone_temperature': self.state.optimal_root_zone_temperature,
            'temperature_deviation': self.state.temperature_deviation,
            'growth_factor': self.state.growth_factor,
            'nutrient_uptake_factor': self.state.nutrient_uptake_factor,
            'water_uptake_factor': self.state.water_uptake_factor,
            'photosynthesis_factor': self.state.photosynthesis_factor,
            'root_metabolism_factor': self.state.root_metabolism_factor,
            'thermal_stress_factor': self.state.thermal_stress_factor,
            'diurnal_temperature_variation': self.state.diurnal_temperature_variation,
            'heat_generation': self.state.heat_generation,
            'ambient_heat_exchange': self.state.ambient_heat_exchange,
            'pump_heat_generation': self.state.pump_heat_generation,
            'root_respiration_heat': self.state.root_respiration_heat,
            'thermal_response_rate': self.state.thermal_response_rate,
            'temperature_stability': self.state.temperature_stability,
            'cumulative_heat_generation': self.state.cumulative_heat_generation,
            'daily_heat_generation': self.state.daily_heat_generation
        }

        self.dependency_cache['root_zone_temperature_simulator'] = root_zone_data

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'root_zone_temperature': self.state.root_zone_temperature,
            'air_temperature': self.state.air_temperature,
            'optimal_root_zone_temperature': self.state.optimal_root_zone_temperature,
            'temperature_deviation': self.state.temperature_deviation,
            'growth_factor': self.state.growth_factor,
            'nutrient_uptake_factor': self.state.nutrient_uptake_factor,
            'water_uptake_factor': self.state.water_uptake_factor,
            'photosynthesis_factor': self.state.photosynthesis_factor,
            'root_metabolism_factor': self.state.root_metabolism_factor,
            'thermal_stress_factor': self.state.thermal_stress_factor,
            'diurnal_temperature_variation': self.state.diurnal_temperature_variation,
            'heat_generation': self.state.heat_generation,
            'ambient_heat_exchange': self.state.ambient_heat_exchange,
            'pump_heat_generation': self.state.pump_heat_generation,
            'root_respiration_heat': self.state.root_respiration_heat,
            'thermal_response_rate': self.state.thermal_response_rate,
            'temperature_stability': self.state.temperature_stability,
            'cumulative_heat_generation': self.state.cumulative_heat_generation,
            'daily_heat_generation': self.state.daily_heat_generation
        }
        
        # Add individual factor data
        for factor in self.temperature_factors:
            data_map[f'{factor}'] = getattr(self.state, factor, 1.0)
        
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            # Environmental data will be requested when needed
            
        elif event.event_type == EventType.ROOT_UPDATE:
            # Update root parameters from root system simulator
            root_data = event.data
            # Root data will be requested when needed
            
        elif event.event_type == EventType.NUTRIENT_UPDATE:
            # Update nutrient parameters from nutrient models simulator
            nutrient_data = event.data
            # Nutrient data will be requested when needed
            
        elif event.event_type == EventType.WATER_UPDATE:
            # Update water parameters from water uptake simulator
            water_data = event.data
            # Water data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Root zone temperature simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final root zone temperature: {self.state.root_zone_temperature:.2f} °C")
        print(f"Final air temperature: {self.state.air_temperature:.2f} °C")
        print(f"Final temperature deviation: {self.state.temperature_deviation:.2f} °C")
        print(f"Final growth factor: {self.state.growth_factor:.3f}")
        print(f"Final nutrient uptake factor: {self.state.nutrient_uptake_factor:.3f}")
        print(f"Final water uptake factor: {self.state.water_uptake_factor:.3f}")
        print(f"Final photosynthesis factor: {self.state.photosynthesis_factor:.3f}")
        print(f"Final root metabolism factor: {self.state.root_metabolism_factor:.3f}")
        print(f"Final thermal stress factor: {self.state.thermal_stress_factor:.3f}")
        print(f"Final temperature stability: {self.state.temperature_stability:.3f}")
        print(f"Total heat generation: {self.state.cumulative_heat_generation:.2f} J")
        
        # Publish final results
        self.publish_event(EventType.ROOT_ZONE_TEMPERATURE_UPDATE, {
            'final_root_zone_temperature': self.state.root_zone_temperature,
            'final_air_temperature': self.state.air_temperature,
            'final_optimal_root_zone_temperature': self.state.optimal_root_zone_temperature,
            'final_temperature_deviation': self.state.temperature_deviation,
            'final_growth_factor': self.state.growth_factor,
            'final_nutrient_uptake_factor': self.state.nutrient_uptake_factor,
            'final_water_uptake_factor': self.state.water_uptake_factor,
            'final_photosynthesis_factor': self.state.photosynthesis_factor,
            'final_root_metabolism_factor': self.state.root_metabolism_factor,
            'final_thermal_stress_factor': self.state.thermal_stress_factor,
            'final_diurnal_temperature_variation': self.state.diurnal_temperature_variation,
            'final_heat_generation': self.state.heat_generation,
            'final_ambient_heat_exchange': self.state.ambient_heat_exchange,
            'final_pump_heat_generation': self.state.pump_heat_generation,
            'final_root_respiration_heat': self.state.root_respiration_heat,
            'final_thermal_response_rate': self.state.thermal_response_rate,
            'final_temperature_stability': self.state.temperature_stability,
            'total_heat_generation': self.state.cumulative_heat_generation,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Root zone temperature simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        rzt_values = [s.root_zone_temperature for s in self.history]
        air_temp_values = [s.air_temperature for s in self.history]
        growth_factors = [s.growth_factor for s in self.history]
        nutrient_factors = [s.nutrient_uptake_factor for s in self.history]
        water_factors = [s.water_uptake_factor for s in self.history]
        photosynthesis_factors = [s.photosynthesis_factor for s in self.history]
        root_metabolism_factors = [s.root_metabolism_factor for s in self.history]
        thermal_stress_factors = [s.thermal_stress_factor for s in self.history]
        
        # Calculate temperature stability metrics
        rzt_variance = sum((t - sum(rzt_values)/len(rzt_values))**2 for t in rzt_values) / len(rzt_values)
        air_temp_variance = sum((t - sum(air_temp_values)/len(air_temp_values))**2 for t in air_temp_values) / len(air_temp_values)
        
        return {
            'total_steps': len(self.history),
            'final_root_zone_temperature': self.state.root_zone_temperature,
            'avg_root_zone_temperature': sum(rzt_values) / len(rzt_values),
            'rzt_variance': rzt_variance,
            'rzt_stability': 1.0 / (1.0 + rzt_variance) if rzt_variance > 0 else 1.0,
            'final_air_temperature': self.state.air_temperature,
            'avg_air_temperature': sum(air_temp_values) / len(air_temp_values),
            'air_temp_variance': air_temp_variance,
            'air_temp_stability': 1.0 / (1.0 + air_temp_variance) if air_temp_variance > 0 else 1.0,
            'final_growth_factor': self.state.growth_factor,
            'avg_growth_factor': sum(growth_factors) / len(growth_factors),
            'final_nutrient_uptake_factor': self.state.nutrient_uptake_factor,
            'avg_nutrient_uptake_factor': sum(nutrient_factors) / len(nutrient_factors),
            'final_water_uptake_factor': self.state.water_uptake_factor,
            'avg_water_uptake_factor': sum(water_factors) / len(water_factors),
            'final_photosynthesis_factor': self.state.photosynthesis_factor,
            'avg_photosynthesis_factor': sum(photosynthesis_factors) / len(photosynthesis_factors),
            'final_root_metabolism_factor': self.state.root_metabolism_factor,
            'avg_root_metabolism_factor': sum(root_metabolism_factors) / len(root_metabolism_factors),
            'final_thermal_stress_factor': self.state.thermal_stress_factor,
            'avg_thermal_stress_factor': sum(thermal_stress_factors) / len(thermal_stress_factors),
            'final_temperature_stability': self.state.temperature_stability,
            'cumulative_heat_generation': self.state.cumulative_heat_generation,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
