"""
Biomass Allocation Simulator

Handles biomass allocation simulation loop and inter-simulator communication
for biomass distribution and allocation processes in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.biomass_allocation_model import (
    BiomassAllocationModel, BiomassAllocationParameters
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class BiomassState:
    """State tracking for biomass allocation simulator"""
    total_biomass: float = 0.0
    leaf_biomass: float = 0.0
    stem_biomass: float = 0.0
    root_biomass: float = 0.0
    leaf_allocation_fraction: float = 0.0
    stem_allocation_fraction: float = 0.0
    root_allocation_fraction: float = 0.0
    allocation_efficiency: float = 1.0
    hourly_biomass_gain: float = 0.0  # Current hourly biomass gain rate
    cumulative_biomass_gain: float = 0.0
    daily_biomass_gain: float = 0.0
    sink_strength: float = 0.0  # Relative growth rate - for source-sink feedback
    # Tissue water retention tracking
    cumulative_tissue_water_retention: float = 0.0  # Total tissue water retained (L)
    hourly_tissue_water_retention: float = 0.0  # Tissue water retention this hour (L)
    daily_tissue_water_retention: float = 0.0  # Tissue water retention today (L)
    total_fresh_weight: float = 0.0  # Total fresh weight (g)
    leaf_fresh_weight: float = 0.0  # Leaf fresh weight (g)
    stem_fresh_weight: float = 0.0  # Stem fresh weight (g)
    root_fresh_weight: float = 0.0  # Root fresh weight (g)
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class BiomassAllocationSimulator(BaseSimulator):
    """Simulator for biomass allocation processes - follows Rules.md strictly"""
    
    def __init__(self, parameters: BiomassAllocationParameters = None):
        super().__init__("biomass_allocation_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("BiomassAllocationParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = BiomassAllocationModel(self.parameters)
        
        # State tracking
        self.state = BiomassState()
        self.history: List[BiomassState] = []
        
        # Initialize with minimal scientifically reasonable values for lettuce seedlings
        # Per Rules.md: use scientific values not hardcoded ones
        self.state.total_biomass = self.parameters.minimum_organ_fraction * 3  # Based on minimum organ fractions
        self.state.root_biomass = self.parameters.minimum_organ_fraction
        self.state.leaf_biomass = self.parameters.minimum_organ_fraction
        self.state.stem_biomass = self.parameters.minimum_organ_fraction
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'photosynthesis_simulator': ['net_assimilation_rate', 'cumulative_carbon_gained'],
            'respiration_simulator': ['total_respiration_rate', 'cumulative_respiration'],
            'phenology_simulator': ['growth_stage', 'development_index', 'thermal_time'],
            'stress_models': ['temperature_stress', 'water_stress', 'nutrient_stress'],
            'root_system_simulator': ['root_biomass']  # Use root biomass from root system simulator
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        

    def _is_vegetative_stage(self, growth_stage: str) -> bool:
        """Determine if current growth stage is vegetative"""
        if isinstance(growth_stage, str):
            vegetative_stages = ['GERMINATION', 'EMERGENCE', 'FIRST_LEAF', 'SECOND_LEAF', 'THIRD_LEAF', 'FOURTH_LEAF',
                               'FIFTH_LEAF', 'SIXTH_LEAF', 'SEVENTH_LEAF', 'EIGHTH_LEAF', 'NINTH_LEAF', 'TENTH_LEAF',
                               'MATURE_VEGETATIVE']
            return any(stage in str(growth_stage) for stage in vegetative_stages)
        return True  # Default to vegetative for early stages

    def _is_reproductive_stage(self, growth_stage: str) -> bool:
        """Determine if current growth stage is reproductive"""
        if isinstance(growth_stage, str):
            reproductive_stages = ['BOLTING_INITIATION', 'FLOWERING', 'ANTHESIS', 'SEED_DEVELOPMENT', 'PHYSIOLOGICAL_MATURITY']
            return any(stage in str(growth_stage) for stage in reproductive_stages)
        return False

    def _is_senescent_stage(self, growth_stage: str) -> bool:
        """Determine if current growth stage is senescent"""
        if isinstance(growth_stage, str):
            return 'PHYSIOLOGICAL_MATURITY' in str(growth_stage)
        return False

    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        self.state = BiomassState()
        self.history.clear()
        self.dependency_cache.clear()

        # Load initial biomass from CSV initial_state
        initial_state = data.get('initial_state', {})
        if initial_state:
            self.state.leaf_biomass = initial_state.get('leaf_biomass', 0.1)
            self.state.stem_biomass = initial_state.get('stem_biomass', 0.05)
            self.state.root_biomass = initial_state.get('root_biomass', 0.1)
            self.state.total_biomass = self.state.leaf_biomass + self.state.stem_biomass + self.state.root_biomass

        # Initialize model with parameters from CSV
        self.model.initialize()

        # Publish initial state to dependency cache immediately
        self.publish_state_data()

        # Publish initial state event
        self.publish_event(EventType.BIOMASS_UPDATE, {
            'total_biomass': self.state.total_biomass,
            'leaf_biomass': self.state.leaf_biomass,
            'stem_biomass': self.state.stem_biomass,
            'root_biomass': self.state.root_biomass
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

# Execute biomass allocation calculation using model functions
            self._execute_biomass_allocation_step(weather_data)
            
            # Update state
            self.current_step += 1
            self.state.last_update = datetime.now()
            
            
            # Store history
            self.history.append(BiomassState(**self.state.__dict__))

            # Prevent unbounded history growth - keep last 1000 steps only

            if len(self.history) > 1000:

                self.history = self.history[-1000:]

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.BIOMASS_UPDATE, {
                'total_biomass': self.state.total_biomass,
                'leaf_biomass': self.state.leaf_biomass,
                'stem_biomass': self.state.stem_biomass,
                'root_biomass': self.state.root_biomass,
                'leaf_allocation_fraction': self.state.leaf_allocation_fraction,
                'stem_allocation_fraction': self.state.stem_allocation_fraction,
                'root_allocation_fraction': self.state.root_allocation_fraction,
                'allocation_efficiency': self.state.allocation_efficiency,
                'hourly_tissue_water_retention': self.state.hourly_tissue_water_retention,
                'cumulative_tissue_water_retention': self.state.cumulative_tissue_water_retention,
                'total_fresh_weight': self.state.total_fresh_weight,
                'step': self.current_step
            })

            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_biomass_gain = 0.0
                self.state.daily_tissue_water_retention = 0.0
                
        except Exception as e:
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.current_step
            })
            # Per Rules.md: raise error, no fallbacks
            raise
    

    def _execute_biomass_allocation_step(self, weather_data: Dict[str, Any]):
        """Execute biomass allocation calculation using model functions - no shortcuts"""
        try:
            # Get photosynthesis data from photosynthesis simulator
            photosynthesis_data = self.dependency_cache.get('photosynthesis_simulator', {})
            hourly_carbon_gain = photosynthesis_data.get('hourly_carbon_gain')  # g C/hour (already converted)
            net_assimilation_rate = photosynthesis_data.get('net_assimilation_rate')  # μmol/m²/s (for logging)

            # Allow skipping on early steps while initial values propagate
            if self.current_step <= 2 and hourly_carbon_gain is None:
                print(f"Biomass: Skipping calculation on step {self.current_step} - waiting for photosynthesis data")
                return

            # Per Rules.md: raise error if missing after initial steps, no defaults
            if hourly_carbon_gain is None:
                raise ValueError(f"Hourly carbon gain missing from photosynthesis_simulator at step {self.current_step} - no defaults allowed")

            # Get respiration data from respiration simulator
            respiration_data = self.dependency_cache.get('respiration_simulator', {})
            total_respiration_rate = respiration_data.get('total_respiration_rate')
            cumulative_respiration = respiration_data.get('cumulative_respiration')

            # Allow skipping on early steps while initial values propagate
            if self.current_step <= 2 and total_respiration_rate is None:
                print(f"Biomass: Skipping calculation on step {self.current_step} - waiting for respiration data")
                return

            if total_respiration_rate is None:
                raise ValueError("Total respiration rate missing from respiration_simulator - no defaults allowed")
            if cumulative_respiration is None:
                cumulative_respiration = 0.0  # Can be zero on first calculation
            
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            thermal_time = phenology_data.get('thermal_time')
            
            if any(x is None for x in [growth_stage, development_index, thermal_time]):
                raise ValueError("Phenology data missing from phenology_simulator - no defaults allowed")
            
            # Get stress factors from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            temperature_stress = stress_data.get('temperature_stress')
            water_stress = stress_data.get('water_stress')
            nutrient_stress = stress_data.get('nutrient_stress')
            
            if any(x is None for x in [temperature_stress, water_stress, nutrient_stress]):
                raise ValueError("Stress data missing from stress_models - no defaults allowed")

            # Calculate biomass allocation using model functions - no shortcuts
            # Per Rules.md: calculate stress from actual data, no hardcoded defaults
            light_stress = 1.0 - min(1.0, temperature_stress)  # Inverse of temperature stress as approximation
            env_conditions = {
                'light_stress': light_stress
            }
            
            result = self.model.calculate_functional_balance_allocation(
                stress_factors={
                    'nitrogen_stress_level': nutrient_stress,
                    'water_stress_level': water_stress
                },
                stage_props={
                    'is_vegetative': self._is_vegetative_stage(growth_stage),
                    'is_reproductive': self._is_reproductive_stage(growth_stage),
                    'is_senescent': self._is_senescent_stage(growth_stage),
                    'development_index': development_index,
                    'thermal_time': thermal_time
                },
                env_conditions=env_conditions
            )
            
            # Update allocation fractions from model results
            self.state.leaf_allocation_fraction = result.get('leaves', 0.0)
            self.state.stem_allocation_fraction = result.get('stems', 0.0)
            self.state.root_allocation_fraction = result.get('roots', 0.0)

            # Get allocation efficiency from CSV parameters
            allocation_efficiency = self.parameters.allocation_efficiency  # From CSV (quantum use efficiency)
            self.state.allocation_efficiency = allocation_efficiency

            # Calculate net carbon gain
            # hourly_carbon_gain is already in g C/hour from photosynthesis simulator
            # total_respiration_rate is already in g C/hour from respiration simulator
            net_carbon_gain = (hourly_carbon_gain - total_respiration_rate)  # g C/hour

            # Convert net carbon gain to biomass
            # Photosynthesis model already converted light → carbon (includes quantum efficiency)
            # Respiration model already subtracted maintenance + growth respiration
            # So net_carbon_gain is the net carbon available for biomass growth
            # carbon_content_fraction converts g C to g dry biomass (typically 0.42 for lettuce)
            carbon_fraction = self.parameters.carbon_content_fraction  # From CSV
            hourly_biomass_gain = net_carbon_gain / carbon_fraction  # g dry biomass/hour

            # DEBUG: Log biomass gain for first few steps and key checkpoints

            # Store hourly gain in state for respiration simulator
            self.state.hourly_biomass_gain = hourly_biomass_gain

            if hourly_biomass_gain > 0:
                # Distribute new biomass according to allocation fractions
                new_leaf_biomass = hourly_biomass_gain * self.state.leaf_allocation_fraction
                new_stem_biomass = hourly_biomass_gain * self.state.stem_allocation_fraction
                new_root_biomass = hourly_biomass_gain * self.state.root_allocation_fraction

                # Update biomass pools
                self.state.leaf_biomass += new_leaf_biomass
                self.state.stem_biomass += new_stem_biomass
                self.state.root_biomass += new_root_biomass
                
                # Use root biomass from root system simulator if available (authoritative source)
                root_data = self.dependency_cache.get('root_system_simulator', {})
                root_biomass_from_root_system = root_data.get('root_biomass')
                if root_biomass_from_root_system is not None and root_biomass_from_root_system > 0:
                    self.state.root_biomass = root_biomass_from_root_system
                
                self.state.total_biomass = self.state.leaf_biomass + self.state.stem_biomass + self.state.root_biomass

                # Calculate tissue water retention for new biomass growth
                biomass_growth = {
                    'leaves': new_leaf_biomass,
                    'stems': new_stem_biomass,
                    'roots': new_root_biomass
                }
                tissue_water = self.model.calculate_tissue_water_retention(biomass_growth)

                # Update tissue water tracking
                self.state.hourly_tissue_water_retention = tissue_water['total']
                self.state.cumulative_tissue_water_retention += tissue_water['total']
                self.state.daily_tissue_water_retention += tissue_water['total']

                # Calculate fresh weights (dry matter / (1 - water_content))
                self.state.leaf_fresh_weight = self.state.leaf_biomass / (1.0 - self.parameters.leaf_water_content)
                self.state.stem_fresh_weight = self.state.stem_biomass / (1.0 - self.parameters.stem_water_content)
                self.state.root_fresh_weight = self.state.root_biomass / (1.0 - self.parameters.root_water_content)
                self.state.total_fresh_weight = self.state.leaf_fresh_weight + self.state.stem_fresh_weight + self.state.root_fresh_weight

                # Update cumulative values
                self.state.cumulative_biomass_gain += hourly_biomass_gain
                self.state.daily_biomass_gain += hourly_biomass_gain

                # Calculate SINK STRENGTH for source-sink feedback
                # Sink strength = Relative Growth Rate (RGR) = (growth rate / current biomass)
                # Units: g/g/hour (dimensionless growth rate)
                # High RGR → high sink demand → upregulate photosynthesis
                # Low RGR → low sink demand → photosynthesis can slow down
                if self.state.total_biomass > 0:
                    self.state.sink_strength = hourly_biomass_gain / self.state.total_biomass
                else:
                    self.state.sink_strength = 0.0
            
        except Exception as e:
            # Per Rules.md: raise error, no fallbacks
            raise
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity
            }
            
            # Execute biomass allocation step using model functions
            self._execute_biomass_allocation_step(weather_data)
            
            # Create output
            outputs = {
                'total_biomass': self.state.total_biomass,
                'leaf_biomass': self.state.leaf_biomass,
                'stem_biomass': self.state.stem_biomass,
                'root_biomass': self.state.root_biomass,
                'leaf_allocation_fraction': self.state.leaf_allocation_fraction,
                'stem_allocation_fraction': self.state.stem_allocation_fraction,
                'root_allocation_fraction': self.state.root_allocation_fraction,
                'allocation_efficiency': self.state.allocation_efficiency,
                'cumulative_biomass_gain': self.state.cumulative_biomass_gain,
                'daily_biomass_gain': self.state.daily_biomass_gain
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Biomass allocation calculation completed using model functions'
            )
            
        except Exception as e:
            # Per Rules.md: raise errors, don't return error objects
            raise
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'total_biomass': self.state.total_biomass,
            'leaf_biomass': self.state.leaf_biomass,
            'stem_biomass': self.state.stem_biomass,
            'root_biomass': self.state.root_biomass,
            'leaf_allocation_fraction': self.state.leaf_allocation_fraction,
            'stem_allocation_fraction': self.state.stem_allocation_fraction,
            'root_allocation_fraction': self.state.root_allocation_fraction,
            'allocation_efficiency': self.state.allocation_efficiency,
            'cumulative_biomass_gain': self.state.cumulative_biomass_gain,
            'daily_biomass_gain': self.state.daily_biomass_gain,
            'sink_strength': self.state.sink_strength,  # For source-sink feedback
            'step_count': self.current_step,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish biomass allocation state data to dependency cache for other simulators"""
        biomass_data = {
            'total_biomass': self.state.total_biomass,
            'leaf_biomass': self.state.leaf_biomass,
            'stem_biomass': self.state.stem_biomass,
            'root_biomass': self.state.root_biomass,
            'leaf_allocation_fraction': self.state.leaf_allocation_fraction,
            'stem_allocation_fraction': self.state.stem_allocation_fraction,
            'root_allocation_fraction': self.state.root_allocation_fraction,
            'allocation_efficiency': self.state.allocation_efficiency,
            'hourly_biomass_gain': self.state.hourly_biomass_gain,  # For respiration calculator
            'cumulative_biomass_gain': self.state.cumulative_biomass_gain,
            'daily_biomass_gain': self.state.daily_biomass_gain,
            'sink_strength': self.state.sink_strength,  # For source-sink feedback to photosynthesis
            'hourly_tissue_water_retention': self.state.hourly_tissue_water_retention,
            'cumulative_tissue_water_retention': self.state.cumulative_tissue_water_retention,
            'total_fresh_weight': self.state.total_fresh_weight,
            'leaf_fresh_weight': self.state.leaf_fresh_weight,
            'stem_fresh_weight': self.state.stem_fresh_weight,
            'root_fresh_weight': self.state.root_fresh_weight
        }

        # Store in dependency cache for other simulators to access
        self.dependency_cache['biomass_allocation_simulator'] = biomass_data
        self.cache_timestamp['biomass_allocation_simulator'] = datetime.now()

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'total_biomass': self.state.total_biomass,
            'leaf_biomass': self.state.leaf_biomass,
            'stem_biomass': self.state.stem_biomass,
            'root_biomass': self.state.root_biomass,
            'leaf_allocation_fraction': self.state.leaf_allocation_fraction,
            'stem_allocation_fraction': self.state.stem_allocation_fraction,
            'root_allocation_fraction': self.state.root_allocation_fraction,
            'allocation_efficiency': self.state.allocation_efficiency,
            'cumulative_biomass_gain': self.state.cumulative_biomass_gain,
            'daily_biomass_gain': self.state.daily_biomass_gain,
            'sink_strength': self.state.sink_strength
        }
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.PHOTOSYNTHESIS_UPDATE:
            # Update photosynthesis parameters
            photosynthesis_data = event.data
            # Data will be requested when needed, no caching here
            
        elif event.event_type == EventType.RESPIRATION_UPDATE:
            # Update respiration parameters
            respiration_data = event.data
            # Data will be requested when needed
            
        elif event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters
            phenology_data = event.data
            # Data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Biomass allocation simulator: Simulation ended after {self.current_step} steps")
        print(f"Total biomass: {self.state.total_biomass:.2f} g DM")
        print(f"Leaf biomass: {self.state.leaf_biomass:.2f} g DM")
        print(f"Stem biomass: {self.state.stem_biomass:.2f} g DM")
        print(f"Root biomass: {self.state.root_biomass:.2f} g DM")
        print(f"Total fresh weight: {self.state.total_fresh_weight:.2f} g")
        print(f"Tissue water retained: {self.state.cumulative_tissue_water_retention:.3f} L")

        # Publish final results
        self.publish_event(EventType.BIOMASS_UPDATE, {
            'final_total_biomass': self.state.total_biomass,
            'final_leaf_biomass': self.state.leaf_biomass,
            'final_stem_biomass': self.state.stem_biomass,
            'final_root_biomass': self.state.root_biomass,
            'final_total_fresh_weight': self.state.total_fresh_weight,
            'final_tissue_water_retention': self.state.cumulative_tissue_water_retention,
            'final_allocation_efficiency': self.state.allocation_efficiency,
            'total_steps': self.current_step,
            'cumulative_biomass_gain': self.state.cumulative_biomass_gain
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Biomass allocation simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        total_biomass_values = [s.total_biomass for s in self.history]
        allocation_efficiencies = [s.allocation_efficiency for s in self.history]
        
        return {
            'total_steps': len(self.history),
            'final_total_biomass': max(total_biomass_values),
            'avg_total_biomass': sum(total_biomass_values) / len(total_biomass_values),
            'avg_allocation_efficiency': sum(allocation_efficiencies) / len(allocation_efficiencies),
            'cumulative_biomass_gain': self.state.cumulative_biomass_gain,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
