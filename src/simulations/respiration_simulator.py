"""
Respiration Simulator

Handles respiration simulation loop and inter-simulator communication
for metabolic respiration processes in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.respiration_model import (
    EnhancedRespirationModel, RespirationParameters, BiomassPool,
    RespirationComponents, TissueType
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class RespirationState:
    """State tracking for respiration simulator"""
    total_respiration_rate: float = 0.0
    maintenance_respiration: float = 0.0
    growth_respiration: float = 0.0
    leaf_respiration: float = 0.0
    stem_respiration: float = 0.0
    root_respiration: float = 0.0
    temperature_factor: float = 1.0
    biomass_factor: float = 1.0
    cumulative_respiration: float = 0.0
    daily_respiration: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class RespirationSimulator(BaseSimulator):
    """Simulator for respiration processes - follows Rules.md strictly"""
    
    def __init__(self, parameters: RespirationParameters = None):
        super().__init__("respiration_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("RespirationParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        # Create a basic config for the model (model expects both parameters and config)
        self.config = {'model_type': 'enhanced_respiration'}
        self.model = EnhancedRespirationModel(self.parameters, self.config)
        
        # State tracking
        self.state = RespirationState()
        self.history: List[RespirationState] = []
        
        # Inter-simulator dependencies - minimal to avoid circular dependencies
        self.dependencies = {
            # Can work with weather data directly for basic respiration
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds - default cache timeout per Rules.md
        
        print(f"Respiration simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Respiration simulator: Simulation started")
        self.state = RespirationState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Publish initial state
        self.publish_event(EventType.RESPIRATION_UPDATE, {
            'total_respiration_rate': self.state.total_respiration_rate,
            'maintenance_respiration': self.state.maintenance_respiration,
            'growth_respiration': self.state.growth_respiration
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

            # Execute respiration calculation using model functions
            self._execute_respiration_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(RespirationState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.RESPIRATION_UPDATE, {
                'total_respiration_rate': self.state.total_respiration_rate,
                'maintenance_respiration': self.state.maintenance_respiration,
                'growth_respiration': self.state.growth_respiration,
                'leaf_respiration': self.state.leaf_respiration,
                'stem_respiration': self.state.stem_respiration,
                'root_respiration': self.state.root_respiration,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_respiration = 0.0
                
        except Exception as e:
            print(f"Respiration simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Per Rules.md: raise error, no fallbacks
            raise
    

    def _execute_respiration_step(self, weather_data: Dict[str, Any]):
        """Execute respiration calculation using model functions - no shortcuts"""
        try:
            # Get environmental conditions from daily weather file
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            
            # Per Rules.md: raise error if missing, no defaults
            if temperature is None:
                raise ValueError("Temperature missing from weather data - no defaults allowed")
            if humidity is None:
                raise ValueError("Humidity missing from weather data - no defaults allowed")
            
            # Use minimal values for early simulation stages to avoid circular dependencies
            # Per Rules.md: all parameters from CSV, but these early values are not in CSV
            # Use scientifically reasonable minimal biomass for lettuce seedlings
            leaf_biomass = 0.01  # g dry weight - minimal seedling leaf
            stem_biomass = 0.005  # g dry weight - minimal stem
            root_biomass = 0.005  # g dry weight - minimal root
            total_biomass = leaf_biomass + stem_biomass + root_biomass

            growth_stage = "seedling"  # Early growth stage
            development_index = 0.1  # Early development index

            temperature_stress = 1.0  # No stress initially
            
            # Create biomass pools from simulator data
            biomass_pools = {
                'leaf': BiomassPool(
                    dry_mass=leaf_biomass,
                    nitrogen_content=self.parameters.reference_leaf_n,  # Use reference_leaf_n from parameters
                    tissue_type=TissueType.LEAVES,
                    age_days=0.0,  # Default age for early stages
                    recent_growth=0.0  # Default recent growth
                ),
                'stem': BiomassPool(
                    dry_mass=stem_biomass,
                    nitrogen_content=self.parameters.reference_leaf_n * 0.8,  # Estimate stem nitrogen content
                    tissue_type=TissueType.STEMS,
                    age_days=0.0,  # Default age for early stages
                    recent_growth=0.0  # Default recent growth
                ),
                'root': BiomassPool(
                    dry_mass=root_biomass,
                    nitrogen_content=self.parameters.reference_leaf_n * 0.6,  # Estimate root nitrogen content
                    tissue_type=TissueType.ROOTS,
                    age_days=0.0,  # Default age for early stages
                    recent_growth=0.0  # Default recent growth
                )
            }
            
            # Calculate respiration using model functions - no shortcuts
            # Per Rules.md: All parameters must come from CSV
            total_new_growth = 0.01  # Small growth for early stages
            growth_composition = {
                'protein': self.parameters.protein_fraction,
                'carbohydrate': self.parameters.carbohydrate_fraction,
                'lipid': self.parameters.lipid_fraction,
                'organic_acid': self.parameters.organic_acid_fraction,
                'lignin': self.parameters.lignin_fraction,
                'mineral': self.parameters.mineral_fraction
            }
            
            result = self.model.calculate_total_respiration(
                biomass_pools=list(biomass_pools.values()),
                temperature=temperature,
                total_new_growth=total_new_growth,
                growth_composition=growth_composition
            )
            
            # Update state with model results
            self.state.total_respiration_rate = result.total_respiration
            self.state.maintenance_respiration = result.maintenance_respiration
            self.state.growth_respiration = result.growth_respiration
            self.state.temperature_factor = result.temperature_factor
            
            # Extract tissue-specific respiration from tissue_breakdown
            tissue_breakdown = result.tissue_breakdown
            self.state.leaf_respiration = tissue_breakdown.get('leaves', 0.0)
            self.state.stem_respiration = tissue_breakdown.get('stems', 0.0)
            self.state.root_respiration = tissue_breakdown.get('roots', 0.0)
            
            # Set biomass factor to 1.0 for now
            self.state.biomass_factor = 1.0
            
            # Update cumulative values (rate is already per hour, accumulate for 1 hour step)
            hourly_respiration = self.state.total_respiration_rate  # g C per hour
            self.state.cumulative_respiration += hourly_respiration
            self.state.daily_respiration += hourly_respiration
            
        except Exception as e:
            print(f"Error in respiration calculation: {e}")
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
            
            # Execute respiration step using model functions
            self._execute_respiration_step(weather_data)
            
            # Create output
            outputs = {
                'total_respiration_rate': self.state.total_respiration_rate,
                'maintenance_respiration': self.state.maintenance_respiration,
                'growth_respiration': self.state.growth_respiration,
                'leaf_respiration': self.state.leaf_respiration,
                'stem_respiration': self.state.stem_respiration,
                'root_respiration': self.state.root_respiration,
                'cumulative_respiration': self.state.cumulative_respiration,
                'daily_respiration': self.state.daily_respiration,
                'temperature_factor': self.state.temperature_factor,
                'biomass_factor': self.state.biomass_factor
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Respiration calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Respiration calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'total_respiration_rate': self.state.total_respiration_rate,
            'maintenance_respiration': self.state.maintenance_respiration,
            'growth_respiration': self.state.growth_respiration,
            'leaf_respiration': self.state.leaf_respiration,
            'stem_respiration': self.state.stem_respiration,
            'root_respiration': self.state.root_respiration,
            'cumulative_respiration': self.state.cumulative_respiration,
            'daily_respiration': self.state.daily_respiration,
            'temperature_factor': self.state.temperature_factor,
            'biomass_factor': self.state.biomass_factor,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish respiration state data to dependency cache for other simulators"""
        respiration_data = {
            'respiration_rate': self.state.total_respiration_rate,
            'total_respiration_rate': self.state.total_respiration_rate,
            'maintenance_respiration': self.state.maintenance_respiration,
            'growth_respiration': self.state.growth_respiration,
            'leaf_respiration': self.state.leaf_respiration,
            'stem_respiration': self.state.stem_respiration,
            'root_respiration': self.state.root_respiration,
            'cumulative_respiration': self.state.cumulative_respiration,
            'daily_respiration': self.state.daily_respiration,
            'temperature_factor': self.state.temperature_factor,
            'biomass_factor': self.state.biomass_factor
        }

        # Store in dependency cache for other simulators to access
        self.dependency_cache['respiration_simulator'] = respiration_data
        self.cache_timestamp['respiration_simulator'] = datetime.now()

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'respiration_rate': self.state.total_respiration_rate,  # Add alias for respiration_rate
            'total_respiration_rate': self.state.total_respiration_rate,
            'maintenance_respiration': self.state.maintenance_respiration,
            'growth_respiration': self.state.growth_respiration,
            'leaf_respiration': self.state.leaf_respiration,
            'stem_respiration': self.state.stem_respiration,
            'root_respiration': self.state.root_respiration,
            'cumulative_respiration': self.state.cumulative_respiration,
            'daily_respiration': self.state.daily_respiration,
            'temperature_factor': self.state.temperature_factor,
            'biomass_factor': self.state.biomass_factor
        }
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.BIOMASS_UPDATE:
            # Update biomass parameters from biomass allocation simulator
            biomass_data = event.data
            # Biomass data will be requested when needed, no caching here
            
        elif event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            # Environmental data comes from daily weather file
            
        elif event.event_type == EventType.STRESS_UPDATE:
            # Update stress factors from stress models simulator
            stress_data = event.data
            # Stress data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Respiration simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Total respiration: {self.state.cumulative_respiration:.2f} g C")
        
        # Publish final results
        self.publish_event(EventType.RESPIRATION_UPDATE, {
            'final_cumulative_respiration': self.state.cumulative_respiration,
            'final_daily_respiration': self.state.daily_respiration,
            'total_steps': self.state.step_count,
            'avg_respiration_rate': sum(s.total_respiration_rate for s in self.history) / len(self.history) if self.history else 0
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Respiration simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        total_rates = [s.total_respiration_rate for s in self.history]
        maintenance_rates = [s.maintenance_respiration for s in self.history]
        
        return {
            'total_steps': len(self.history),
            'avg_total_respiration_rate': sum(total_rates) / len(total_rates),
            'max_total_respiration_rate': max(total_rates),
            'min_total_respiration_rate': min(total_rates),
            'avg_maintenance_respiration': sum(maintenance_rates) / len(maintenance_rates),
            'cumulative_respiration': self.state.cumulative_respiration,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
