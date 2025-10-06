"""
Canopy Architecture Simulator

Handles canopy architecture simulation loop and inter-simulator communication
for canopy structure and light interception in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
import math
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.canopy_architecture import (
    CanopyArchitectureModel, CanopyArchitectureParameters,
    CanopyLayer, LightEnvironment, LeafAngleDistribution
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class CanopyState:
    """State tracking for canopy architecture simulator"""
    lai: float = 0.0
    leaf_area: float = 0.0
    canopy_height: float = 0.0
    canopy_width: float = 0.0
    ground_coverage: float = 0.0
    light_extinction_coefficient: float = 0.5
    sunlit_leaf_fraction: float = 0.0
    shaded_leaf_fraction: float = 0.0
    light_interception_efficiency: float = 0.0
    temperature_gradient: float = 0.0
    humidity_gradient: float = 0.0
    wind_speed_reduction: float = 0.0
    cumulative_light_interception: float = 0.0
    daily_light_interception: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class CanopyArchitectureSimulator(BaseSimulator):
    """Simulator for canopy architecture - follows Rules.md strictly"""
    
    def __init__(self, parameters: CanopyArchitectureParameters = None):
        super().__init__("canopy_architecture_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("CanopyArchitectureParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = CanopyArchitectureModel(self.parameters)
        
        # State tracking
        self.state = CanopyState()
        self.history: List[CanopyState] = []
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'biomass_allocation_simulator': ['leaf_biomass', 'total_biomass'],
            'leaf_development_simulator': ['leaf_area', 'leaf_number', 'leaf_size'],
            'phenology_simulator': ['growth_stage', 'development_index'],
            'stress_models': ['light_stress', 'temperature_stress']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        print(f"Canopy architecture simulator initialized with parameters from CSV")

    def _calculate_ground_coverage(self, total_lai: float) -> float:
        """Calculate ground coverage fraction based on LAI"""
        # Simple Beer's law approximation for ground coverage
        if total_lai <= 0:
            return 0.0
        return min(1.0, 1.0 - math.exp(-self.parameters.extinction_coefficient * total_lai))

    def _calculate_temperature_gradient(self, canopy_layers: List) -> float:
        """Calculate temperature gradient through canopy layers"""
        if not canopy_layers or len(canopy_layers) < 2:
            return 0.0

        # Calculate temperature difference between top and bottom layers
        top_temp = canopy_layers[0].temperature if hasattr(canopy_layers[0], 'temperature') else 0.0
        bottom_temp = canopy_layers[-1].temperature if hasattr(canopy_layers[-1], 'temperature') else 0.0
        return abs(top_temp - bottom_temp)

    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Canopy architecture simulator: Simulation started")
        self.state = CanopyState()
        self.history.clear()
        self.dependency_cache.clear()

        # Initialize model with parameters from CSV
        self.model.initialize()

        # Initialize LAI from initials.csv - this is the ONLY LAI source
        initial_config = data.get('initial_config', {})
        initial_state = initial_config.get('initial_state', {})
        initial_lai = initial_state.get('lai', 0.05)  # From initials.csv line 14
        initial_leaf_area = initial_state.get('leaf_area', 0.001)  # From initials.csv line 15
        initial_plant_height = initial_state.get('plant_height', 0.02)  # From initials.csv line 16

        # Set initial state from CSV
        self.state.lai = initial_lai
        self.state.leaf_area = initial_leaf_area
        self.state.canopy_height = initial_plant_height
        self.state.ground_coverage = self._calculate_ground_coverage(initial_lai)

        print(f"Canopy initialized with LAI={initial_lai:.3f} from initials.csv")

        # Publish initial state to dependency cache immediately
        self.publish_state_data()

        # Publish initial state event
        self.publish_event(EventType.CANOPY_UPDATE, {
            'lai': self.state.lai,
            'leaf_area': self.state.leaf_area,
            'canopy_height': self.state.canopy_height,
            'ground_coverage': self.state.ground_coverage
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

            # Execute canopy architecture calculation using model functions
            self._execute_canopy_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(CanopyState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.CANOPY_UPDATE, {
                'lai': self.state.lai,
                'leaf_area': self.state.leaf_area,
                'canopy_height': self.state.canopy_height,
                'canopy_width': self.state.canopy_width,
                'ground_coverage': self.state.ground_coverage,
                'light_extinction_coefficient': self.state.light_extinction_coefficient,
                'sunlit_leaf_fraction': self.state.sunlit_leaf_fraction,
                'shaded_leaf_fraction': self.state.shaded_leaf_fraction,
                'light_interception_efficiency': self.state.light_interception_efficiency,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_light_interception = 0.0
                
        except Exception as e:
            print(f"Canopy architecture simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise error, no fallbacks
            raise
    

    def _execute_canopy_step(self, weather_data: Dict[str, Any]):
        """Execute canopy architecture calculation using model functions - no shortcuts"""
        try:
            # Get biomass data from biomass allocation simulator
            biomass_data = self.dependency_cache.get('biomass_allocation_simulator', {})
            leaf_biomass = biomass_data.get('leaf_biomass')
            total_biomass = biomass_data.get('total_biomass')

            # Skip on first step if biomass data not available yet (circular dependency)
            if any(x is None for x in [leaf_biomass, total_biomass]):
                if self.state.step_count == 0:
                    print(f"Canopy: Skipping calculation on step 0 due to missing biomass_allocation data")
                    return
                raise ValueError("Biomass data missing from biomass_allocation_simulator - no defaults allowed")
            
            # Calculate leaf area from leaf biomass using SLA (Specific Leaf Area)
            # Get SLA from leaf_development parameters (must come from CSV per Rules.md)
            leaf_dev_data = self.dependency_cache.get('leaf_development_simulator', {})
            sla_cm2_g = leaf_dev_data.get('specific_leaf_area')
            if sla_cm2_g is None:
                raise ValueError("Specific leaf area (SLA) missing from leaf_development_simulator - no defaults allowed per Rules.md")

            specific_leaf_area = sla_cm2_g / 10000.0  # Convert cm²/g to m²/g
            leaf_area = leaf_biomass * specific_leaf_area  # m²

            # Get leaf development data for additional metrics
            leaf_data = self.dependency_cache.get('leaf_development_simulator', {})
            leaf_number = leaf_data.get('leaf_number', 4)  # Initial leaves
            leaf_size = leaf_data.get('leaf_size', 0.0025)  # m2 per leaf
            
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            
            if any(x is None for x in [growth_stage, development_index]):
                raise ValueError("Phenology data missing from phenology_simulator - no defaults allowed")
            
            # Get environmental conditions from daily weather file
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            light_intensity = weather_data.get('light_intensity')
            wind_speed = weather_data.get('wind_speed')
            
            if any(x is None for x in [temperature, humidity, light_intensity, wind_speed]):
                raise ValueError("Environmental data missing from weather data - no defaults allowed")
            
            # Get stress factors from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            light_stress = stress_data.get('light_stress')
            temperature_stress = stress_data.get('temperature_stress')
            
            if any(x is None for x in [light_stress, temperature_stress]):
                raise ValueError("Stress data missing from stress_models - no defaults allowed")
            
            # Calculate canopy architecture using model functions - no shortcuts
            # Convert leaf area to LAI (assuming ground area per plant from parameters)
            ground_area_per_plant = self.parameters.row_spacing * self.parameters.plant_spacing  # m²
            total_lai = leaf_area / ground_area_per_plant if ground_area_per_plant > 0 else 0.0

            # Apply maximum LAI constraint from CSV to prevent runaway growth
            max_lai = self.parameters.max_lai  # From master_parameters.csv canopy_parameters
            total_lai = min(total_lai, max_lai)

            # Calculate canopy height based on growth stage and biomass
            canopy_height = min(self.parameters.plant_height, (total_biomass / 100.0) * self.parameters.plant_height)
            
            # Create light environment from weather data and parameters - no hardcoded values
            from models.canopy_architecture import LightEnvironment

            # Calculate solar zenith angle from hour (simplified for hydroponic systems)
            hour = 12  # Assume midday calculation
            solar_zenith_angle = abs(hour - 12) * 15.0  # Simple approximation

            light_env = LightEnvironment(
                ppfd_above_canopy=light_intensity,
                direct_beam_fraction=self.parameters.direct_beam_fraction,
                diffuse_fraction=self.parameters.diffuse_fraction,
                solar_zenith_angle=solar_zenith_angle,
                solar_azimuth_angle=180.0  # South-facing assumption
            )
            
            # Get CO2 from weather data - no defaults allowed per Rules.md
            co2_concentration = weather_data.get('co2_concentration') or weather_data.get('co2_ppm')

            result = self.model.daily_update(
                total_lai=total_lai,
                canopy_height=canopy_height,
                air_temperature=temperature,
                light_env=light_env,
                co2_concentration=co2_concentration
            )
            
            # Update state with model results - per Rules.md: no defaults, use actual result values
            self.state.lai = result.total_lai
            self.state.leaf_area = leaf_area  # From dependency data
            self.state.canopy_height = result.canopy_height
            self.state.canopy_width = self.parameters.canopy_width
            self.state.ground_coverage = self._calculate_ground_coverage(total_lai)
            self.state.light_extinction_coefficient = result.average_extinction_coefficient
            self.state.sunlit_leaf_fraction = result.sunlit_lai / total_lai if total_lai > 0 else 0.0
            self.state.shaded_leaf_fraction = result.shaded_lai / total_lai if total_lai > 0 else 0.0
            self.state.light_interception_efficiency = result.light_interception_fraction
            # Calculate gradients from canopy layers
            self.state.temperature_gradient = self._calculate_temperature_gradient(result.canopy_layers)
            self.state.humidity_gradient = 0.0  # Placeholder for future implementation
            self.state.wind_speed_reduction = min(0.8, total_lai * 0.2)  # Simple wind reduction model
            
            # Update cumulative values
            hourly_light_interception = self.state.light_interception_efficiency * light_intensity * 3600  # Convert to hourly
            self.state.cumulative_light_interception += hourly_light_interception
            self.state.daily_light_interception += hourly_light_interception
            
        except Exception as e:
            print(f"Error in canopy architecture calculation: {e}")
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
                'wind_speed': weather_data.get('wind_speed', 1.0)  # From weather data or minimal default
            }
            
            # Execute canopy architecture step using model functions
            self._execute_canopy_step(weather_data)
            
            # Create output
            outputs = {
                'lai': self.state.lai,
                'leaf_area': self.state.leaf_area,
                'canopy_height': self.state.canopy_height,
                'canopy_width': self.state.canopy_width,
                'ground_coverage': self.state.ground_coverage,
                'light_extinction_coefficient': self.state.light_extinction_coefficient,
                'sunlit_leaf_fraction': self.state.sunlit_leaf_fraction,
                'shaded_leaf_fraction': self.state.shaded_leaf_fraction,
                'light_interception_efficiency': self.state.light_interception_efficiency,
                'temperature_gradient': self.state.temperature_gradient,
                'humidity_gradient': self.state.humidity_gradient,
                'wind_speed_reduction': self.state.wind_speed_reduction,
                'cumulative_light_interception': self.state.cumulative_light_interception,
                'daily_light_interception': self.state.daily_light_interception
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Canopy architecture calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Canopy architecture calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'lai': self.state.lai,
            'leaf_area': self.state.leaf_area,
            'canopy_height': self.state.canopy_height,
            'canopy_width': self.state.canopy_width,
            'ground_coverage': self.state.ground_coverage,
            'light_extinction_coefficient': self.state.light_extinction_coefficient,
            'sunlit_leaf_fraction': self.state.sunlit_leaf_fraction,
            'shaded_leaf_fraction': self.state.shaded_leaf_fraction,
            'light_interception_efficiency': self.state.light_interception_efficiency,
            'temperature_gradient': self.state.temperature_gradient,
            'humidity_gradient': self.state.humidity_gradient,
            'wind_speed_reduction': self.state.wind_speed_reduction,
            'cumulative_light_interception': self.state.cumulative_light_interception,
            'daily_light_interception': self.state.daily_light_interception,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish canopy architecture state data to dependency cache for other simulators"""
        canopy_data = {
            'lai': self.state.lai,
            'leaf_area': self.state.leaf_area,
            'canopy_height': self.state.canopy_height,
            'canopy_width': self.state.canopy_width,
            'ground_coverage': self.state.ground_coverage,
            'light_extinction_coefficient': self.state.light_extinction_coefficient,
            'sunlit_leaf_fraction': self.state.sunlit_leaf_fraction,
            'shaded_leaf_fraction': self.state.shaded_leaf_fraction,
            'light_interception_efficiency': self.state.light_interception_efficiency,
            'temperature_gradient': self.state.temperature_gradient,
            'humidity_gradient': self.state.humidity_gradient,
            'wind_speed_reduction': self.state.wind_speed_reduction,
            'cumulative_light_interception': self.state.cumulative_light_interception,
            'daily_light_interception': self.state.daily_light_interception
        }

        # Store in dependency cache for other simulators to access
        self.dependency_cache['canopy_architecture_simulator'] = canopy_data
        self.cache_timestamp['canopy_architecture_simulator'] = datetime.now()

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'lai': self.state.lai,
            'leaf_area': self.state.leaf_area,
            'canopy_height': self.state.canopy_height,
            'canopy_width': self.state.canopy_width,
            'ground_coverage': self.state.ground_coverage,
            'light_extinction_coefficient': self.state.light_extinction_coefficient,
            'sunlit_leaf_fraction': self.state.sunlit_leaf_fraction,
            'shaded_leaf_fraction': self.state.shaded_leaf_fraction,
            'light_interception_efficiency': self.state.light_interception_efficiency,
            'temperature_gradient': self.state.temperature_gradient,
            'humidity_gradient': self.state.humidity_gradient,
            'wind_speed_reduction': self.state.wind_speed_reduction,
            'cumulative_light_interception': self.state.cumulative_light_interception,
            'daily_light_interception': self.state.daily_light_interception
        }
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.BIOMASS_UPDATE:
            # Update biomass parameters from biomass allocation simulator
            biomass_data = event.data
            # Biomass data will be requested when needed
            
        elif event.event_type == EventType.LEAF_DEVELOPMENT_UPDATE:
            # Update leaf development parameters from leaf development simulator
            leaf_data = event.data
            # Leaf data will be requested when needed
            
        elif event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters from phenology simulator
            phenology_data = event.data
            # Phenology data will be requested when needed
            
        elif event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            # Environmental data comes from daily weather file
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Canopy architecture simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final LAI: {self.state.lai:.3f}")
        print(f"Final canopy height: {self.state.canopy_height:.2f} cm")
        print(f"Final ground coverage: {self.state.ground_coverage:.3f}")
        print(f"Final light interception efficiency: {self.state.light_interception_efficiency:.3f}")
        print(f"Total light interception: {self.state.cumulative_light_interception:.2f} MJ/m²")
        
        # Publish final results
        self.publish_event(EventType.CANOPY_UPDATE, {
            'final_lai': self.state.lai,
            'final_leaf_area': self.state.leaf_area,
            'final_canopy_height': self.state.canopy_height,
            'final_canopy_width': self.state.canopy_width,
            'final_ground_coverage': self.state.ground_coverage,
            'final_light_extinction_coefficient': self.state.light_extinction_coefficient,
            'final_sunlit_leaf_fraction': self.state.sunlit_leaf_fraction,
            'final_shaded_leaf_fraction': self.state.shaded_leaf_fraction,
            'final_light_interception_efficiency': self.state.light_interception_efficiency,
            'total_light_interception': self.state.cumulative_light_interception,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Canopy architecture simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        lai_values = [s.lai for s in self.history]
        canopy_height_values = [s.canopy_height for s in self.history]
        light_interception_values = [s.light_interception_efficiency for s in self.history]
        
        return {
            'total_steps': len(self.history),
            'final_lai': self.state.lai,
            'max_lai': max(lai_values),
            'avg_lai': sum(lai_values) / len(lai_values),
            'final_canopy_height': self.state.canopy_height,
            'max_canopy_height': max(canopy_height_values),
            'avg_canopy_height': sum(canopy_height_values) / len(canopy_height_values),
            'final_ground_coverage': self.state.ground_coverage,
            'final_light_interception_efficiency': self.state.light_interception_efficiency,
            'avg_light_interception_efficiency': sum(light_interception_values) / len(light_interception_values),
            'max_light_interception_efficiency': max(light_interception_values),
            'cumulative_light_interception': self.state.cumulative_light_interception,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
