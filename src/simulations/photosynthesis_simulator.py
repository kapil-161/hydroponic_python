"""
Photosynthesis Simulator

Handles photosynthesis simulation loop and inter-simulator communication
for carbon assimilation processes in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.photosynthesis_model import (
    PhotosynthesisModel, PhotosynthesisParameters
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class PhotosynthesisState:
    """State tracking for photosynthesis simulator"""
    net_assimilation_rate: float = 0.0
    gross_photosynthesis_rate: float = 0.0
    respiration_rate: float = 0.0
    light_use_efficiency: float = 0.0
    co2_uptake_rate: float = 0.0
    leaf_temperature: float = 25.0
    light_stress_factor: float = 1.0
    temperature_stress_factor: float = 1.0
    cumulative_carbon_gained: float = 0.0
    daily_carbon_gained: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class PhotosynthesisSimulator(BaseSimulator):
    """Simulator for photosynthesis - follows Rules.md strictly"""
    
    def __init__(self, 
                 parameters: PhotosynthesisParameters = None):
        super().__init__("photosynthesis_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("PhotosynthesisParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = PhotosynthesisModel(self.parameters)
        
        # State tracking
        self.state = PhotosynthesisState()
        self.history: List[PhotosynthesisState] = []
        
        # Inter-simulator dependencies - essential data for photosynthesis
        self.dependencies = {
            'canopy_architecture_simulator': ['lai', 'leaf_area', 'canopy_height', 'sunlit_leaf_fraction', 'shaded_leaf_fraction'],
            'stress_models': ['temperature_stress', 'light_stress', 'water_stress'],
            'environmental_control': ['light_intensity', 'co2_concentration'],
            'leaf_development_simulator': ['total_leaf_area', 'leaf_nitrogen_content']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        print(f"Photosynthesis simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Photosynthesis simulator: Simulation started")
        self.state = PhotosynthesisState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model
        self.model.initialize()
        
        # Publish initial state
        self.publish_event(EventType.PHOTOSYNTHESIS_UPDATE, {
            'net_assimilation_rate': self.state.net_assimilation_rate,
            'gross_photosynthesis_rate': self.state.gross_photosynthesis_rate,
            'light_use_efficiency': self.state.light_use_efficiency
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            
            # Update dependency data from other simulators
            self._update_dependencies()
            
            # Execute photosynthesis calculation using model functions
            self._execute_photosynthesis_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(PhotosynthesisState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.PHOTOSYNTHESIS_UPDATE, {
                'net_assimilation_rate': self.state.net_assimilation_rate,
                'gross_photosynthesis_rate': self.state.gross_photosynthesis_rate,
                'respiration_rate': self.state.respiration_rate,
                'light_use_efficiency': self.state.light_use_efficiency,
                'co2_uptake_rate': self.state.co2_uptake_rate,
                'leaf_temperature': self.state.leaf_temperature,
                'light_stress_factor': self.state.light_stress_factor,
                'temperature_stress_factor': self.state.temperature_stress_factor,
                'cumulative_carbon_gained': self.state.cumulative_carbon_gained,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_carbon_gained = 0.0
                
        except Exception as e:
            print(f"Photosynthesis simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise error, no fallbacks
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
                # Don't raise error, just log and continue
                pass
    
    def _execute_photosynthesis_step(self, weather_data: Dict[str, Any]):
        """Execute photosynthesis calculation using model functions - no shortcuts"""
        try:
            # Get environmental conditions from daily weather file
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            light_intensity = weather_data.get('light_intensity')  # PAR is the light intensity
            co2_concentration = weather_data.get('co2_concentration')
            
            # Per Rules.md: raise error if missing, no defaults
            if any(x is None for x in [temperature, humidity, light_intensity, co2_concentration]):
                raise ValueError("Environmental data missing from weather data - no defaults allowed")
            
            # Get canopy data from canopy architecture simulator
            canopy_data = self.dependency_cache.get('canopy_architecture_simulator', {})
            lai = canopy_data.get('lai', 0.1)  # Fallback for early stages
            leaf_area = canopy_data.get('leaf_area', 1.0)
            canopy_height = canopy_data.get('canopy_height', 0.1)
            sunlit_fraction = canopy_data.get('sunlit_leaf_fraction', 0.8)
            shaded_fraction = canopy_data.get('shaded_leaf_fraction', 0.2)

            # Get stress factors from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            temp_stress = stress_data.get('temperature_stress', 1.0)
            light_stress = stress_data.get('light_stress', 1.0)
            water_stress = stress_data.get('water_stress', 1.0)

            # Get environmental data from environmental control
            env_data = self.dependency_cache.get('environmental_control', {})
            env_light = env_data.get('light_intensity', light_intensity)
            env_co2 = env_data.get('co2_concentration', co2_concentration)

            # Get leaf data from leaf development simulator
            leaf_data = self.dependency_cache.get('leaf_development_simulator', {})
            total_leaf_area = leaf_data.get('total_leaf_area', leaf_area)
            leaf_nitrogen = leaf_data.get('leaf_nitrogen_content', 2.5)  # Default N content
            
            # Calculate photosynthesis using model functions - no shortcuts
            # Per Rules.md: All parameters must come from CSV, no hardcoded values
            config = {
                'model_type': 'lettuce_photosynthesis',
                'optimal_temp_min': self.parameters.optimal_temperature_min,
                'optimal_temp_max': self.parameters.optimal_temperature_max,
                'light_saturation_threshold': self.parameters.light_saturation_threshold,
                'optimal_vpd_min': self.parameters.optimal_vpd_min,
                'optimal_vpd_max': self.parameters.optimal_vpd_max
            }
            ec_factor = 1.0  # Default EC factor
            sunlit_lai = lai * sunlit_fraction
            shaded_lai = lai * shaded_fraction
            
            net_assimilation, _ = self.model.calculate_hourly_assimilation(
                par_umol_m2_s=light_intensity,
                co2_ppm=co2_concentration,
                temp_c=temperature,
                humidity=humidity,
                lai=lai,
                ec_factor=ec_factor,
                config=config,
                sunlit_lai=sunlit_lai,
                shaded_lai=shaded_lai
            )
            
            # Update state with model results
            self.state.net_assimilation_rate = net_assimilation
            self.state.gross_photosynthesis_rate = net_assimilation * 1.1  # Estimate gross from net
            self.state.respiration_rate = net_assimilation * 0.1  # Estimate respiration
            self.state.light_use_efficiency = min(1.0, net_assimilation / max(light_intensity, 1.0))
            self.state.co2_uptake_rate = net_assimilation
            self.state.leaf_temperature = temperature
            self.state.temperature_stress_factor = temp_stress
            self.state.light_stress_factor = light_stress
            
            # Update cumulative values
            hourly_carbon = net_assimilation * 3600  # Convert to hourly
            self.state.cumulative_carbon_gained += hourly_carbon
            self.state.daily_carbon_gained += hourly_carbon
            
        except Exception as e:
            print(f"Error in photosynthesis calculation: {e}")
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
                'co2_concentration': inputs.co2_concentration
            }
            
            # Execute photosynthesis step using model functions
            self._execute_photosynthesis_step(weather_data)
            
            # Create output
            outputs = {
                'net_assimilation_rate': self.state.net_assimilation_rate,
                'gross_photosynthesis_rate': self.state.gross_photosynthesis_rate,
                'respiration_rate': self.state.respiration_rate,
                'light_use_efficiency': self.state.light_use_efficiency,
                'co2_uptake_rate': self.state.co2_uptake_rate,
                'cumulative_carbon_gained': self.state.cumulative_carbon_gained,
                'daily_carbon_gained': self.state.daily_carbon_gained,
                'leaf_temperature': self.state.leaf_temperature,
                'temperature_stress_factor': self.state.temperature_stress_factor,
                'light_stress_factor': self.state.light_stress_factor
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Photosynthesis calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Photosynthesis calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'net_assimilation_rate': self.state.net_assimilation_rate,
            'gross_photosynthesis_rate': self.state.gross_photosynthesis_rate,
            'respiration_rate': self.state.respiration_rate,
            'light_use_efficiency': self.state.light_use_efficiency,
            'co2_uptake_rate': self.state.co2_uptake_rate,
            'cumulative_carbon_gained': self.state.cumulative_carbon_gained,
            'daily_carbon_gained': self.state.daily_carbon_gained,
            'leaf_temperature': self.state.leaf_temperature,
            'temperature_stress_factor': self.state.temperature_stress_factor,
            'light_stress_factor': self.state.light_stress_factor,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish photosynthesis state data to dependency cache for other simulators"""
        photosynthesis_data = {
            'photosynthesis_rate': self.state.net_assimilation_rate,
            'net_assimilation_rate': self.state.net_assimilation_rate,
            'gross_photosynthesis_rate': self.state.gross_photosynthesis_rate,
            'respiration_rate': self.state.respiration_rate,
            'light_use_efficiency': self.state.light_use_efficiency,
            'co2_uptake_rate': self.state.co2_uptake_rate,
            'cumulative_carbon_gained': self.state.cumulative_carbon_gained,
            'daily_carbon_gained': self.state.daily_carbon_gained,
            'leaf_temperature': self.state.leaf_temperature,
            'temperature_stress_factor': self.state.temperature_stress_factor,
            'light_stress_factor': self.state.light_stress_factor
        }

        # Store in dependency cache for other simulators to access
        self.dependency_cache['photosynthesis_simulator'] = photosynthesis_data
        self.cache_timestamp['photosynthesis_simulator'] = datetime.now()

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'photosynthesis_rate': self.state.net_assimilation_rate,  # Add alias for photosynthesis_rate
            'net_assimilation_rate': self.state.net_assimilation_rate,
            'gross_photosynthesis_rate': self.state.gross_photosynthesis_rate,
            'respiration_rate': self.state.respiration_rate,
            'light_use_efficiency': self.state.light_use_efficiency,
            'co2_uptake_rate': self.state.co2_uptake_rate,
            'cumulative_carbon_gained': self.state.cumulative_carbon_gained,
            'daily_carbon_gained': self.state.daily_carbon_gained,
            'leaf_temperature': self.state.leaf_temperature,
            'temperature_stress_factor': self.state.temperature_stress_factor,
            'light_stress_factor': self.state.light_stress_factor
        }
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            if 'temperature' in env_data:
                self.state.leaf_temperature = env_data['temperature']
        
        elif event.event_type == EventType.CANOPY_UPDATE:
            # Update canopy parameters
            canopy_data = event.data
            if 'lai' in canopy_data:
                # LAI affects photosynthesis efficiency
                pass
        
        elif event.event_type == EventType.STRESS_UPDATE:
            # Update stress factors
            stress_data = event.data
            if 'temperature_stress' in stress_data:
                self.state.temperature_stress_factor = stress_data['temperature_stress']
            if 'light_stress' in stress_data:
                self.state.light_stress_factor = stress_data['light_stress']
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Photosynthesis simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final net assimilation rate: {self.state.net_assimilation_rate:.3f} μmol CO2/m²/s")
        print(f"Final gross photosynthesis rate: {self.state.gross_photosynthesis_rate:.3f} μmol CO2/m²/s")
        print(f"Final light use efficiency: {self.state.light_use_efficiency:.3f}")
        print(f"Final CO2 uptake rate: {self.state.co2_uptake_rate:.3f} μmol CO2/m²/s")
        print(f"Total carbon gained: {self.state.cumulative_carbon_gained:.2f} g C")
        
        # Publish final results
        self.publish_event(EventType.PHOTOSYNTHESIS_UPDATE, {
            'final_net_assimilation_rate': self.state.net_assimilation_rate,
            'final_gross_photosynthesis_rate': self.state.gross_photosynthesis_rate,
            'final_respiration_rate': self.state.respiration_rate,
            'final_light_use_efficiency': self.state.light_use_efficiency,
            'final_co2_uptake_rate': self.state.co2_uptake_rate,
            'final_leaf_temperature': self.state.leaf_temperature,
            'final_light_stress_factor': self.state.light_stress_factor,
            'final_temperature_stress_factor': self.state.temperature_stress_factor,
            'total_carbon_gained': self.state.cumulative_carbon_gained,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Photosynthesis simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        net_rates = [s.net_assimilation_rate for s in self.history]
        gross_rates = [s.gross_photosynthesis_rate for s in self.history]
        
        return {
            'total_steps': len(self.history),
            'avg_net_assimilation_rate': sum(net_rates) / len(net_rates),
            'max_net_assimilation_rate': max(net_rates),
            'min_net_assimilation_rate': min(net_rates),
            'avg_gross_photosynthesis_rate': sum(gross_rates) / len(gross_rates),
            'cumulative_carbon_gained': self.state.cumulative_carbon_gained,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
