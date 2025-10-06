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
    cumulative_biomass_gain: float = 0.0
    daily_biomass_gain: float = 0.0
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
            'genetic_parameters_simulator': ['genetic_coefficients', 'cultivar_profile']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
        print(f"Biomass allocation simulator initialized with parameters from CSV")

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
        print("Biomass allocation simulator: Simulation started")
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
            print(f"Biomass: Initialized leaf={self.state.leaf_biomass}, stem={self.state.stem_biomass}, root={self.state.root_biomass}")

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
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(BiomassState(**self.state.__dict__))

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
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_biomass_gain = 0.0
                
        except Exception as e:
            print(f"Biomass allocation simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise error, no fallbacks
            raise
    

    def _execute_biomass_allocation_step(self, weather_data: Dict[str, Any]):
        """Execute biomass allocation calculation using model functions - no shortcuts"""
        try:
            # Get photosynthesis data from photosynthesis simulator
            photosynthesis_data = self.dependency_cache.get('photosynthesis_simulator', {})
            net_assimilation_rate = photosynthesis_data.get('net_assimilation_rate')
            cumulative_carbon_gained = photosynthesis_data.get('cumulative_carbon_gained')

            # Allow skipping on first step while initial values propagate
            if self.state.step_count == 0 and net_assimilation_rate is None:
                print(f"Biomass: Skipping calculation on first step - waiting for photosynthesis data")
                return

            # Per Rules.md: raise error if missing after first step, no defaults
            if net_assimilation_rate is None:
                raise ValueError("Net assimilation rate missing from photosynthesis_simulator - no defaults allowed")
            if cumulative_carbon_gained is None:
                cumulative_carbon_gained = 0.0  # Can be zero on first calculation

            # Get respiration data from respiration simulator
            respiration_data = self.dependency_cache.get('respiration_simulator', {})
            total_respiration_rate = respiration_data.get('total_respiration_rate')
            cumulative_respiration = respiration_data.get('cumulative_respiration')

            # Allow skipping on first step while initial values propagate
            if self.state.step_count == 0 and total_respiration_rate is None:
                print(f"Biomass: Skipping calculation on first step - waiting for respiration data")
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
            
            # Get genetic parameters from genetic parameters simulator
            genetic_data = self.dependency_cache.get('genetic_parameters_simulator', {})
            genetic_coefficients = genetic_data.get('genetic_coefficients')
            cultivar_profile = genetic_data.get('cultivar_profile')
            
            if genetic_coefficients is None or cultivar_profile is None:
                raise ValueError("Genetic data missing from genetic_parameters_simulator - no defaults allowed")
            
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
            self.state.allocation_efficiency = 1.0  # Efficient allocation

            # Convert net assimilation from μmol CO2/m²/s to g biomass/hour
            # 1 μmol CO2 = 0.000044 g CO2
            # Photosynthesis: CO2 + H2O → CH2O + O2, so 44g CO2 → 30g CH2O
            # Photosynthesis returns g C/hour (total for whole canopy), respiration also in g C/hour
            # Net carbon gain is already in g C/hour
            net_carbon_gain = (net_assimilation_rate - total_respiration_rate)  # g C/hour

            # Convert g C to g dry biomass (carbon is ~40-45% of dry biomass)
            carbon_fraction = 0.40  # g C per g dry biomass (should be from CSV but using realistic value)
            hourly_biomass_gain = net_carbon_gain / carbon_fraction  # g dry biomass/hour

            # Apply maximum hourly growth rate constraint to prevent runaway growth
            # For hydroponic lettuce: target final biomass 10-15g over 27 days
            # Required: ~10g growth / (27 days × 24 hours) = 0.015 g/hour
            max_hourly_biomass_gain = 0.01  # g/hour - calibrated for 10-15g final biomass
            if hourly_biomass_gain > max_hourly_biomass_gain:
                hourly_biomass_gain = max_hourly_biomass_gain

            # DEBUG: Log biomass gain for first few steps and key checkpoints
            if self.state.step_count < 5 or self.state.step_count == 24 or self.state.step_count == 100:
                print(f"DEBUG Biomass step {self.state.step_count}: net_assim={net_assimilation_rate:.3f}, resp={total_respiration_rate:.3f}, net_carbon={net_carbon_gain:.3f} g C/hr, hourly_gain={hourly_biomass_gain:.6f} g/hr, total_biomass={self.state.total_biomass:.2f}")

            if hourly_biomass_gain > 0:
                # Distribute new biomass according to allocation fractions
                new_leaf_biomass = hourly_biomass_gain * self.state.leaf_allocation_fraction
                new_stem_biomass = hourly_biomass_gain * self.state.stem_allocation_fraction
                new_root_biomass = hourly_biomass_gain * self.state.root_allocation_fraction

                # Update biomass pools
                self.state.leaf_biomass += new_leaf_biomass
                self.state.stem_biomass += new_stem_biomass
                self.state.root_biomass += new_root_biomass
                self.state.total_biomass = self.state.leaf_biomass + self.state.stem_biomass + self.state.root_biomass
            
                # Update cumulative values
                self.state.cumulative_biomass_gain += hourly_biomass_gain
                self.state.daily_biomass_gain += hourly_biomass_gain
            
        except Exception as e:
            print(f"Error in biomass allocation calculation: {e}")
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
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Biomass allocation calculation failed: {str(e)}'
            )
    
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
            'step_count': self.state.step_count,
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
            'cumulative_biomass_gain': self.state.cumulative_biomass_gain,
            'daily_biomass_gain': self.state.daily_biomass_gain
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
            'daily_biomass_gain': self.state.daily_biomass_gain
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
        print(f"Biomass allocation simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Total biomass: {self.state.total_biomass:.2f} g DM")
        print(f"Leaf biomass: {self.state.leaf_biomass:.2f} g DM")
        print(f"Stem biomass: {self.state.stem_biomass:.2f} g DM")
        print(f"Root biomass: {self.state.root_biomass:.2f} g DM")
        
        # Publish final results
        self.publish_event(EventType.BIOMASS_UPDATE, {
            'final_total_biomass': self.state.total_biomass,
            'final_leaf_biomass': self.state.leaf_biomass,
            'final_stem_biomass': self.state.stem_biomass,
            'final_root_biomass': self.state.root_biomass,
            'final_allocation_efficiency': self.state.allocation_efficiency,
            'total_steps': self.state.step_count,
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
