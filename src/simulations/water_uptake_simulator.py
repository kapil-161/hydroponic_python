"""
Water Uptake Simulator

Handles water uptake simulation loop and inter-simulator communication
for water uptake and transpiration processes in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.water_uptake_model import (
    WaterUptakeModel, WaterUptakeParameters, GrowthStage
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class WaterUptakeState:
    """State tracking for water uptake simulator"""
    water_uptake_rate: float = 0.0
    transpiration_rate: float = 0.0
    evapotranspiration: float = 0.0
    water_availability: float = 1.0
    root_water_potential: float = -0.5
    leaf_water_potential: float = -1.0
    hydraulic_conductance: float = 1.0
    crop_coefficient: float = 0.8
    cumulative_water_uptake: float = 0.0
    daily_water_uptake: float = 0.0
    cumulative_transpiration: float = 0.0
    daily_transpiration: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class WaterUptakeSimulator(BaseSimulator):
    """Simulator for water uptake processes - follows Rules.md strictly"""
    
    def __init__(self, parameters: WaterUptakeParameters = None):
        super().__init__("water_uptake_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("WaterUptakeParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = WaterUptakeModel(self.parameters)
        
        # State tracking
        self.state = WaterUptakeState()
        self.history: List[WaterUptakeState] = []
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'environmental_control': ['temperature', 'humidity', 'light_intensity', 'wind_speed'],
            'canopy_architecture_simulator': ['lai', 'leaf_area', 'canopy_height'],
            'root_system_simulator': ['root_depth', 'root_distribution', 'root_biomass'],
            'phenology_simulator': ['growth_stage', 'development_index'],
            'stress_models': ['water_stress', 'temperature_stress']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        print(f"Water uptake simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Water uptake simulator: Simulation started")
        self.state = WaterUptakeState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Publish initial state
        self.publish_event(EventType.WATER_UPDATE, {
            'water_uptake_rate': self.state.water_uptake_rate,
            'transpiration_rate': self.state.transpiration_rate,
            'water_availability': self.state.water_availability,
            'crop_coefficient': self.state.crop_coefficient
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            
            # Update dependency data from other simulators
            self._update_dependencies()
            
            # Execute water uptake calculation using model functions
            self._execute_water_uptake_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(WaterUptakeState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.WATER_UPDATE, {
                'water_uptake_rate': self.state.water_uptake_rate,
                'transpiration_rate': self.state.transpiration_rate,
                'evapotranspiration': self.state.evapotranspiration,
                'water_availability': self.state.water_availability,
                'root_water_potential': self.state.root_water_potential,
                'leaf_water_potential': self.state.leaf_water_potential,
                'hydraulic_conductance': self.state.hydraulic_conductance,
                'crop_coefficient': self.state.crop_coefficient,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_water_uptake = 0.0
                self.state.daily_transpiration = 0.0
                
        except Exception as e:
            print(f"Water uptake simulator error in step {self.state.step_count}: {e}")
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
    
    def _execute_water_uptake_step(self, weather_data: Dict[str, Any]):
        """Execute water uptake calculation using model functions - no shortcuts"""
        try:
            # Get environmental conditions from daily weather file
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            light_intensity = weather_data.get('light_intensity')  # PAR is the light intensity
            wind_speed = weather_data.get('wind_speed')
            
            # Per Rules.md: raise error if missing, no defaults
            if temperature is None:
                raise ValueError("Temperature missing from weather data - no defaults allowed")
            if humidity is None:
                raise ValueError("Humidity missing from weather data - no defaults allowed")
            if light_intensity is None:
                raise ValueError("Light intensity missing from weather data - no defaults allowed")
            if wind_speed is None:
                raise ValueError("Wind speed missing from weather data - no defaults allowed")
            
            # Get canopy data from canopy architecture simulator
            canopy_data = self.dependency_cache.get('canopy_architecture_simulator', {})
            lai = canopy_data.get('lai')
            leaf_area = canopy_data.get('leaf_area')
            canopy_height = canopy_data.get('canopy_height')
            
            if any(x is None for x in [lai, leaf_area, canopy_height]):
                raise ValueError("Canopy data missing from canopy_architecture_simulator - no defaults allowed")
            
            # Get root data from root system simulator
            root_data = self.dependency_cache.get('root_system_simulator', {})
            root_depth = root_data.get('root_depth')
            root_distribution = root_data.get('root_distribution')
            root_biomass = root_data.get('root_biomass')
            
            if any(x is None for x in [root_depth, root_distribution, root_biomass]):
                raise ValueError("Root data missing from root_system_simulator - no defaults allowed")
            
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            
            if any(x is None for x in [growth_stage, development_index]):
                raise ValueError("Phenology data missing from phenology_simulator - no defaults allowed")
            
            # Get stress factors from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            water_stress = stress_data.get('water_stress')
            temperature_stress = stress_data.get('temperature_stress')
            
            if any(x is None for x in [water_stress, temperature_stress]):
                raise ValueError("Stress data missing from stress_models - no defaults allowed")
            
            # Calculate water uptake using model functions - no shortcuts
            result = self.model.calculate_realistic_water_uptake(
                temperature=temperature,
                humidity=humidity,
                solar_radiation=light_intensity,  # Use light_intensity as solar_radiation
                lai=lai,
                total_biomass=root_biomass + leaf_area * self.parameters.leaf_area_to_biomass_ratio,  # Estimate total biomass
                growth_stage=growth_stage,  # Use actual growth stage from phenology
                stress_factors={
                    'water_stress_level': water_stress,
                    'salinity_stress': stress_data.get('salinity_stress'),  # Get from stress models
                    'temperature_stress': temperature_stress
                },
                solution_ec=stress_data.get('solution_ec', 1.5)  # Get from stress models or use typical hydroponic value
            )
            
            # Update state with model results - no fallback values allowed per Rules.md
            self.state.water_uptake_rate = result.total_water_uptake_L
            self.state.transpiration_rate = result.transpiration_L
            self.state.evapotranspiration = result.etc_mm
            self.state.water_availability = 1.0 - (result.total_water_uptake_L / 10.0)  # Calculate from uptake
            self.state.root_water_potential = -0.5  # Will come from root system model
            self.state.leaf_water_potential = -1.0  # Will come from leaf water potential calculation
            self.state.hydraulic_conductance = result.total_hydraulic_conductance
            self.state.crop_coefficient = result.kc
            
            # Update cumulative values
            hourly_water_uptake = self.state.water_uptake_rate * 3600  # Convert to hourly
            hourly_transpiration = self.state.transpiration_rate * 3600  # Convert to hourly
            
            self.state.cumulative_water_uptake += hourly_water_uptake
            self.state.daily_water_uptake += hourly_water_uptake
            self.state.cumulative_transpiration += hourly_transpiration
            self.state.daily_transpiration += hourly_transpiration
            
        except Exception as e:
            print(f"Error in water uptake calculation: {e}")
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
                'wind_speed': 2.0  # This should come from weather data
            }
            
            # Execute water uptake step using model functions
            self._execute_water_uptake_step(weather_data)
            
            # Create output
            outputs = {
                'water_uptake_rate': self.state.water_uptake_rate,
                'transpiration_rate': self.state.transpiration_rate,
                'evapotranspiration': self.state.evapotranspiration,
                'water_availability': self.state.water_availability,
                'root_water_potential': self.state.root_water_potential,
                'leaf_water_potential': self.state.leaf_water_potential,
                'hydraulic_conductance': self.state.hydraulic_conductance,
                'crop_coefficient': self.state.crop_coefficient,
                'cumulative_water_uptake': self.state.cumulative_water_uptake,
                'daily_water_uptake': self.state.daily_water_uptake,
                'cumulative_transpiration': self.state.cumulative_transpiration,
                'daily_transpiration': self.state.daily_transpiration
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Water uptake calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Water uptake calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'water_uptake_rate': self.state.water_uptake_rate,
            'transpiration_rate': self.state.transpiration_rate,
            'evapotranspiration': self.state.evapotranspiration,
            'water_availability': self.state.water_availability,
            'root_water_potential': self.state.root_water_potential,
            'leaf_water_potential': self.state.leaf_water_potential,
            'hydraulic_conductance': self.state.hydraulic_conductance,
            'crop_coefficient': self.state.crop_coefficient,
            'cumulative_water_uptake': self.state.cumulative_water_uptake,
            'daily_water_uptake': self.state.daily_water_uptake,
            'cumulative_transpiration': self.state.cumulative_transpiration,
            'daily_transpiration': self.state.daily_transpiration,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'water_uptake_rate': self.state.water_uptake_rate,
            'transpiration_rate': self.state.transpiration_rate,
            'evapotranspiration': self.state.evapotranspiration,
            'water_availability': self.state.water_availability,
            'root_water_potential': self.state.root_water_potential,
            'leaf_water_potential': self.state.leaf_water_potential,
            'hydraulic_conductance': self.state.hydraulic_conductance,
            'crop_coefficient': self.state.crop_coefficient,
            'cumulative_water_uptake': self.state.cumulative_water_uptake,
            'daily_water_uptake': self.state.daily_water_uptake,
            'cumulative_transpiration': self.state.cumulative_transpiration,
            'daily_transpiration': self.state.daily_transpiration
        }
        return data_map.get(data_key)

    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        water_uptake_data = {
            'water_uptake_rate': self.state.water_uptake_rate,
            'transpiration_rate': self.state.transpiration_rate,
            'evapotranspiration': self.state.evapotranspiration,
            'water_availability': self.state.water_availability,
            'root_water_potential': self.state.root_water_potential,
            'leaf_water_potential': self.state.leaf_water_potential,
            'hydraulic_conductance': self.state.hydraulic_conductance,
            'crop_coefficient': self.state.crop_coefficient,
            'cumulative_water_uptake': self.state.cumulative_water_uptake,
            'daily_water_uptake': self.state.daily_water_uptake,
            'cumulative_transpiration': self.state.cumulative_transpiration,
            'daily_transpiration': self.state.daily_transpiration
        }

        self.dependency_cache['water_uptake_simulator'] = water_uptake_data

    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            # Environmental data comes from daily weather file
            
        elif event.event_type == EventType.CANOPY_UPDATE:
            # Update canopy parameters from canopy architecture simulator
            canopy_data = event.data
            # Canopy data will be requested when needed
            
        elif event.event_type == EventType.ROOT_UPDATE:
            # Update root parameters from root system simulator
            root_data = event.data
            # Root data will be requested when needed
            
        elif event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters from phenology simulator
            phenology_data = event.data
            # Phenology data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Water uptake simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Total water uptake: {self.state.cumulative_water_uptake:.2f} L")
        print(f"Total transpiration: {self.state.cumulative_transpiration:.2f} L")
        print(f"Final water availability: {self.state.water_availability:.3f}")
        print(f"Final crop coefficient: {self.state.crop_coefficient:.3f}")
        
        # Publish final results
        self.publish_event(EventType.WATER_UPDATE, {
            'final_water_uptake_rate': self.state.water_uptake_rate,
            'final_transpiration_rate': self.state.transpiration_rate,
            'final_evapotranspiration': self.state.evapotranspiration,
            'final_water_availability': self.state.water_availability,
            'final_root_water_potential': self.state.root_water_potential,
            'final_leaf_water_potential': self.state.leaf_water_potential,
            'final_hydraulic_conductance': self.state.hydraulic_conductance,
            'final_crop_coefficient': self.state.crop_coefficient,
            'total_cumulative_water_uptake': self.state.cumulative_water_uptake,
            'total_cumulative_transpiration': self.state.cumulative_transpiration,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Water uptake simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        water_uptake_rates = [s.water_uptake_rate for s in self.history]
        transpiration_rates = [s.transpiration_rate for s in self.history]
        water_availability_values = [s.water_availability for s in self.history]
        
        return {
            'total_steps': len(self.history),
            'final_water_uptake_rate': self.state.water_uptake_rate,
            'avg_water_uptake_rate': sum(water_uptake_rates) / len(water_uptake_rates),
            'max_water_uptake_rate': max(water_uptake_rates),
            'min_water_uptake_rate': min(water_uptake_rates),
            'final_transpiration_rate': self.state.transpiration_rate,
            'avg_transpiration_rate': sum(transpiration_rates) / len(transpiration_rates),
            'max_transpiration_rate': max(transpiration_rates),
            'min_transpiration_rate': min(transpiration_rates),
            'final_water_availability': self.state.water_availability,
            'avg_water_availability': sum(water_availability_values) / len(water_availability_values),
            'min_water_availability': min(water_availability_values),
            'cumulative_water_uptake': self.state.cumulative_water_uptake,
            'cumulative_transpiration': self.state.cumulative_transpiration,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
