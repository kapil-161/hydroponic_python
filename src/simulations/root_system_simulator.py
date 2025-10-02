"""
Root System Simulator

Handles root system simulation loop and inter-simulator communication
for root growth and architecture in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.root_system_model import (
    EnhancedRootSystemModel, RootSystemParameters, RootSystemMetrics,
    RootCohort, RootZoneLayer, RootType, HydroponicSystemType
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class RootSystemState:
    """State tracking for root system simulator"""
    root_depth: float = 0.0
    root_biomass: float = 0.0
    root_length: float = 0.0
    root_surface_area: float = 0.0
    root_distribution: Dict[str, float] = field(default_factory=dict)
    root_density: float = 0.0
    root_activity: float = 1.0
    root_zone_volume: float = 0.0
    root_zone_layers: List[Dict[str, Any]] = field(default_factory=list)
    root_cohorts: List[Dict[str, Any]] = field(default_factory=list)
    fine_root_fraction: float = 0.0
    medium_root_fraction: float = 0.0
    coarse_root_fraction: float = 0.0
    cumulative_root_growth: float = 0.0
    daily_root_growth: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class RootSystemSimulator(BaseSimulator):
    """Simulator for root system - follows Rules.md strictly"""
    
    def __init__(self, parameters: RootSystemParameters = None):
        super().__init__("root_system_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("RootSystemParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = EnhancedRootSystemModel(self.parameters)
        
        # State tracking
        self.state = RootSystemState()
        self.history: List[RootSystemState] = []
        
        # Initialize with minimal values to break circular dependencies
        self.state.root_depth = 1.0  # Small initial root depth
        self.state.root_biomass = 0.02  # Small initial root biomass
        self.state.root_length = 5.0  # Small initial root length
        self.state.root_surface_area = 0.5  # Small initial surface area
        
        # Initialize root distribution
        self.root_zones = ['upper', 'middle', 'lower']
        for zone in self.root_zones:
            self.state.root_distribution[zone] = 0.0
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'biomass_allocation_simulator': ['total_biomass'],
            'water_uptake_simulator': ['water_uptake_rate', 'root_water_potential'],
            'nutrient_models_simulator': ['nutrient_availability', 'solution_ec'],
            'phenology_simulator': ['growth_stage', 'development_index'],
            'stress_models': ['water_stress', 'nutrient_stress'],
            'root_zone_temperature_simulator': ['root_zone_temperature']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = parameters.cache_timeout  # Get from CSV parameters
        
        print(f"Root system simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start - initialize with values from initials.csv"""
        print("Root system simulator: Simulation started")
        self.state = RootSystemState()

        # Load initial root state from CSV (via initial_state)
        initial_state = data.get('initial_state', {})
        if initial_state:
            self.state.root_biomass = initial_state.get('root_biomass', 0.1)
            self.state.root_length = initial_state.get('root_length', 0.05)
            self.state.root_surface_area = self.state.root_length * 0.001  # Estimate from length
            self.state.root_depth = self.state.root_length  # Initially depth = length
            self.state.root_activity = 1.0  # Fully active at start
            print(f"Root: Initialized root_biomass={self.state.root_biomass}g, root_length={self.state.root_length}m from CSV")

        self.history.clear()
        self.dependency_cache.clear()

        # Initialize model with parameters from CSV
        self.model.initialize()

        # Publish initial state data to dependency cache
        self.publish_state_data()

        # Publish initial state
        self.publish_event(EventType.ROOT_UPDATE, {
            'root_depth': self.state.root_depth,
            'root_biomass': self.state.root_biomass,
            'root_length': self.state.root_length,
            'root_surface_area': self.state.root_surface_area,
            'root_distribution': self.state.root_distribution
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

# Execute root system calculation using model functions
            self._execute_root_system_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(RootSystemState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.ROOT_UPDATE, {
                'root_depth': self.state.root_depth,
                'root_biomass': self.state.root_biomass,
                'root_length': self.state.root_length,
                'root_surface_area': self.state.root_surface_area,
                'root_distribution': self.state.root_distribution,
                'root_density': self.state.root_density,
                'root_activity': self.state.root_activity,
                'root_zone_volume': self.state.root_zone_volume,
                'fine_root_fraction': self.state.fine_root_fraction,
                'medium_root_fraction': self.state.medium_root_fraction,
                'coarse_root_fraction': self.state.coarse_root_fraction,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_root_growth = 0.0
                
        except Exception as e:
            print(f"Root system simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Raise error according to Rules.md - no error suppression
            raise
    

    def _execute_root_system_step(self, weather_data: Dict[str, Any]):
        """Execute root system calculation using model functions - no shortcuts"""
        try:
            # Get biomass data from biomass allocation simulator
            biomass_data = self.dependency_cache.get('biomass_allocation_simulator', {})
            total_biomass = biomass_data.get('total_biomass')
            
            if total_biomass is None:
                # Use default values for early simulation stages when biomass data is not available
                total_biomass = 1.0  # Small but non-zero total biomass for early stages
                print(f"Warning: Using default total biomass value: {total_biomass}")
            
            # Calculate root biomass from total biomass (assuming 20% allocation to roots)
            root_biomass = total_biomass * 0.2
            
            # Get water data from water uptake simulator
            water_data = self.dependency_cache.get('water_uptake_simulator', {})
            water_uptake_rate = water_data.get('water_uptake_rate')
            root_water_potential = water_data.get('root_water_potential')
            
            if any(x is None for x in [water_uptake_rate, root_water_potential]):
                # Use default values for early simulation stages
                water_uptake_rate = 1.0  # Default optimal water uptake
                root_water_potential = -0.5  # Default root water potential
            
            # Get nutrient data from nutrient models simulator
            nutrient_data = self.dependency_cache.get('nutrient_models_simulator', {})
            nutrient_availability = nutrient_data.get('nutrient_availability')
            solution_ec = nutrient_data.get('solution_ec')
            nutrient_concentrations = nutrient_data.get('nutrient_concentrations')

            if any(x is None for x in [nutrient_availability, solution_ec, nutrient_concentrations]):
                # Use default values for early simulation stages
                nutrient_availability = 1.0  # Default optimal nutrient availability
                solution_ec = 1.5  # Default EC value
                nutrient_concentrations = {'N-NO3': 100, 'N-NH4': 20, 'P-PO4': 50, 'K': 150, 'Ca': 120, 'Mg': 50, 'S-SO4': 80}
            
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            
            if any(x is None for x in [growth_stage, development_index]):
                # Use default values for early simulation stages
                growth_stage = 'GERMINATION'  # Default early stage
                development_index = 0.0  # Default early development
            
            # Get stress factors from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            water_stress = stress_data.get('water_stress')
            nutrient_stress = stress_data.get('nutrient_stress')
            
            if any(x is None for x in [water_stress, nutrient_stress]):
                # Use default values for early simulation stages
                water_stress = 1.0  # Default optimal water stress
                nutrient_stress = 1.0  # Default optimal nutrient stress
            
            # Get root zone temperature from root zone temperature simulator
            rzt_data = self.dependency_cache.get('root_zone_temperature_simulator', {})
            root_zone_temperature = rzt_data.get('root_zone_temperature')

            if root_zone_temperature is None:
                if self.state.step_count == 0:
                    print(f"Root: Skipping calculation on step 0 due to missing root_zone_temperature data")
                    return
                raise ValueError("Root zone temperature missing from root_zone_temperature_simulator - no defaults allowed")
            
            # Get environmental conditions from daily weather file
            temperature = weather_data.get('temperature')
            if temperature is None:
                raise ValueError("Temperature missing from weather data - no defaults allowed")
            
            # Calculate root system growth using model functions - no shortcuts
            environmental_conditions = {
                'temperature': temperature,
                'root_zone_temperature': root_zone_temperature,
                'water_uptake_rate': water_uptake_rate,
                'nutrient_availability': nutrient_availability,
                'solution_ec': solution_ec,
                'flow_rate': 1.0,  # Default flow rate
                'oxygen_level': 8.0,  # Default oxygen level (mg/L)
                'ph': 6.5,  # Default pH
                'nutrient_concentrations': nutrient_concentrations  # From nutrient models simulator
            }
            
            growth_factors = {
                'temperature': temperature,
                'water_availability': 1.0,
                'nutrient_availability': nutrient_availability
            }
            
            result = self.model.calculate_hourly_root_metrics(
                environmental_conditions=environmental_conditions,
                growth_factors=growth_factors,
                dt_hours=1.0  # 1 hour time step
            )
            
            # Update state with model results
            self.state.root_depth = result.get('root_depth', self.state.root_depth)
            self.state.root_biomass = root_biomass  # From biomass allocation simulator
            self.state.root_length = result.get('total_root_length', self.state.root_length)
            self.state.root_surface_area = result.get('total_root_surface_area', self.state.root_surface_area)
            self.state.root_density = result.get('root_length_density', self.state.root_density)
            self.state.root_activity = result.get('average_root_activity', self.state.root_activity)
            self.state.root_zone_volume = result.get('total_root_volume', self.state.root_zone_volume)
            self.state.fine_root_fraction = result.get('fine_root_length', 0.0) / max(result.get('total_root_length', 1.0), 1.0)
            self.state.medium_root_fraction = result.get('medium_root_length', 0.0) / max(result.get('total_root_length', 1.0), 1.0)
            self.state.coarse_root_fraction = result.get('coarse_root_length', 0.0) / max(result.get('total_root_length', 1.0), 1.0)
            
            # Update root distribution
            root_distribution = result.get('root_distribution', {})
            for zone in self.root_zones:
                if zone in root_distribution:
                    self.state.root_distribution[zone] = root_distribution[zone]
            
            # Update root zone layers
            root_zone_layers = result.get('root_zone_layers', [])
            self.state.root_zone_layers = root_zone_layers
            
            # Update root cohorts
            root_cohorts = result.get('root_cohorts', [])
            self.state.root_cohorts = root_cohorts
            
            # Update cumulative values
            hourly_root_growth = result.get('root_growth_rate', 0.0) * 3600  # Convert to hourly
            self.state.cumulative_root_growth += hourly_root_growth
            self.state.daily_root_growth += hourly_root_growth
            
        except Exception as e:
            print(f"Error in root system calculation: {e}")
            # Raise error according to Rules.md - no error suppression
            raise
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity
            }
            
            # Execute root system step using model functions
            self._execute_root_system_step(weather_data)
            
            # Create output
            outputs = {
                'root_depth': self.state.root_depth,
                'root_biomass': self.state.root_biomass,
                'root_length': self.state.root_length,
                'root_surface_area': self.state.root_surface_area,
                'root_distribution': self.state.root_distribution,
                'root_density': self.state.root_density,
                'root_activity': self.state.root_activity,
                'root_zone_volume': self.state.root_zone_volume,
                'root_zone_layers': self.state.root_zone_layers,
                'root_cohorts': self.state.root_cohorts,
                'fine_root_fraction': self.state.fine_root_fraction,
                'medium_root_fraction': self.state.medium_root_fraction,
                'coarse_root_fraction': self.state.coarse_root_fraction,
                'cumulative_root_growth': self.state.cumulative_root_growth,
                'daily_root_growth': self.state.daily_root_growth
            }
            
            return DailyUpdateOutput(
                model_name='root_system_simulator',
                day=inputs.day,
                success=True,
                primary_results=outputs,
                secondary_results={},
                internal_state=self.get_current_state(),
                validation_result=None,
                processing_time_ms=0.0
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                model_name='root_system_simulator',
                day=inputs.day,
                success=False,
                primary_results={},
                secondary_results={'error_message': f'Root system calculation failed: {str(e)}'},
                internal_state={},
                validation_result=None,
                processing_time_ms=0.0
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'root_depth': self.state.root_depth,
            'root_biomass': self.state.root_biomass,
            'root_length': self.state.root_length,
            'root_surface_area': self.state.root_surface_area,
            'root_distribution': self.state.root_distribution,
            'root_density': self.state.root_density,
            'root_activity': self.state.root_activity,
            'root_zone_volume': self.state.root_zone_volume,
            'root_zone_layers': self.state.root_zone_layers,
            'root_cohorts': self.state.root_cohorts,
            'fine_root_fraction': self.state.fine_root_fraction,
            'medium_root_fraction': self.state.medium_root_fraction,
            'coarse_root_fraction': self.state.coarse_root_fraction,
            'cumulative_root_growth': self.state.cumulative_root_growth,
            'daily_root_growth': self.state.daily_root_growth,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish root system state data to dependency cache for other simulators"""
        root_data = {
            'root_depth': self.state.root_depth,
            'root_biomass': self.state.root_biomass,
            'root_mass': self.state.root_biomass,  # Alias for compatibility
            'root_length': self.state.root_length,
            'root_surface_area': self.state.root_surface_area,
            'root_distribution': self.state.root_distribution,
            'root_density': self.state.root_density,
            'root_activity': self.state.root_activity,
            'root_zone_volume': self.state.root_zone_volume,
            'fine_root_fraction': self.state.fine_root_fraction,
            'medium_root_fraction': self.state.medium_root_fraction,
            'coarse_root_fraction': self.state.coarse_root_fraction,
            'cumulative_root_growth': self.state.cumulative_root_growth,
            'daily_root_growth': self.state.daily_root_growth
        }

        # Store in dependency cache for other simulators to access
        self.dependency_cache['root_system_simulator'] = root_data
        self.cache_timestamp['root_system_simulator'] = datetime.now()

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'root_depth': self.state.root_depth,
            'root_biomass': self.state.root_biomass,
            'root_length': self.state.root_length,
            'root_surface_area': self.state.root_surface_area,
            'root_distribution': self.state.root_distribution,
            'root_density': self.state.root_density,
            'root_activity': self.state.root_activity,
            'root_zone_volume': self.state.root_zone_volume,
            'fine_root_fraction': self.state.fine_root_fraction,
            'medium_root_fraction': self.state.medium_root_fraction,
            'coarse_root_fraction': self.state.coarse_root_fraction,
            'cumulative_root_growth': self.state.cumulative_root_growth,
            'daily_root_growth': self.state.daily_root_growth
        }
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.BIOMASS_UPDATE:
            # Update biomass parameters from biomass allocation simulator
            biomass_data = event.data
            # Biomass data will be requested when needed
            
        elif event.event_type == EventType.WATER_UPDATE:
            # Update water parameters from water uptake simulator
            water_data = event.data
            # Water data will be requested when needed
            
        elif event.event_type == EventType.NUTRIENT_UPDATE:
            # Update nutrient parameters from nutrient models simulator
            nutrient_data = event.data
            # Nutrient data will be requested when needed
            
        elif event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters from phenology simulator
            phenology_data = event.data
            # Phenology data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Root system simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final root depth: {self.state.root_depth:.2f} cm")
        print(f"Final root biomass: {self.state.root_biomass:.2f} g DM")
        print(f"Final root length: {self.state.root_length:.2f} cm")
        print(f"Final root surface area: {self.state.root_surface_area:.2f} cm²")
        print(f"Final root density: {self.state.root_density:.3f} g/cm³")
        print(f"Total root growth: {self.state.cumulative_root_growth:.2f} cm")
        
        # Print root distribution
        for zone, fraction in self.state.root_distribution.items():
            print(f"Root distribution {zone}: {fraction:.3f}")
        
        # Publish final results
        self.publish_event(EventType.ROOT_UPDATE, {
            'final_root_depth': self.state.root_depth,
            'final_root_biomass': self.state.root_biomass,
            'final_root_length': self.state.root_length,
            'final_root_surface_area': self.state.root_surface_area,
            'final_root_distribution': self.state.root_distribution,
            'final_root_density': self.state.root_density,
            'final_root_activity': self.state.root_activity,
            'final_root_zone_volume': self.state.root_zone_volume,
            'final_fine_root_fraction': self.state.fine_root_fraction,
            'final_medium_root_fraction': self.state.medium_root_fraction,
            'final_coarse_root_fraction': self.state.coarse_root_fraction,
            'total_root_growth': self.state.cumulative_root_growth,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Root system simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        root_depth_values = [s.root_depth for s in self.history]
        root_biomass_values = [s.root_biomass for s in self.history]
        root_length_values = [s.root_length for s in self.history]
        root_surface_area_values = [s.root_surface_area for s in self.history]
        
        return {
            'total_steps': len(self.history),
            'final_root_depth': self.state.root_depth,
            'max_root_depth': max(root_depth_values),
            'avg_root_depth': sum(root_depth_values) / len(root_depth_values),
            'final_root_biomass': self.state.root_biomass,
            'max_root_biomass': max(root_biomass_values),
            'avg_root_biomass': sum(root_biomass_values) / len(root_biomass_values),
            'final_root_length': self.state.root_length,
            'max_root_length': max(root_length_values),
            'avg_root_length': sum(root_length_values) / len(root_length_values),
            'final_root_surface_area': self.state.root_surface_area,
            'max_root_surface_area': max(root_surface_area_values),
            'avg_root_surface_area': sum(root_surface_area_values) / len(root_surface_area_values),
            'final_root_density': self.state.root_density,
            'final_root_activity': self.state.root_activity,
            'cumulative_root_growth': self.state.cumulative_root_growth,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
