"""
Leaf Development Simulator

Handles leaf development simulation loop and inter-simulator communication
for leaf growth, expansion, and senescence in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.leaf_development import (
    LeafDevelopmentModel, LeafParameters, LeafStage, LeafCohort
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class LeafAgeDistribution:
    """Distribution of leaf ages"""
    young_leaves: int = 0
    mature_leaves: int = 0
    old_leaves: int = 0
    senescing_leaves: int = 0


@dataclass
class LeafSizeDistribution:
    """Distribution of leaf sizes"""
    small_leaves: float = 0.0
    medium_leaves: float = 0.0
    large_leaves: float = 0.0


@dataclass
class LeafNitrogenDistribution:
    """Distribution of leaf nitrogen content"""
    low_nitrogen: float = 0.0
    medium_nitrogen: float = 0.0
    high_nitrogen: float = 0.0


@dataclass
class LeafDevelopmentState:
    """State tracking for leaf development simulator"""
    total_leaves: int = 0
    leaf_appearance_rate: float = 0.0
    leaf_expansion_rate: float = 0.0
    leaf_senescence_rate: float = 0.0
    total_leaf_area: float = 0.0
    total_leaf_weight: float = 0.0
    leaf_area_index: float = 0.0
    leaf_weight_ratio: float = 0.0
    leaf_nitrogen_content: float = 0.0
    leaf_nitrogen_ratio: float = 0.0
    leaf_age_distribution: Dict[str, int] = field(default_factory=dict)
    leaf_size_distribution: Dict[str, float] = field(default_factory=dict)
    leaf_nitrogen_distribution: Dict[str, float] = field(default_factory=dict)
    cumulative_thermal_time: float = 0.0
    daily_thermal_time: float = 0.0
    phyllochron_adjusted: float = 0.0
    leaf_growth_stress: float = 1.0
    leaf_senescence_stress: float = 1.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class LeafDevelopmentSimulator(BaseSimulator):
    """Simulator for leaf development - follows Rules.md strictly"""
    
    def __init__(self, 
                 leaf_params: LeafParameters = None):
        super().__init__("leaf_development_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if leaf_params is None:
            raise ValueError("LeafParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.leaf_params = leaf_params
        self.model = LeafDevelopmentModel(self.leaf_params)
        
        # State tracking
        self.state = LeafDevelopmentState()
        self.history: List[LeafDevelopmentState] = []
        
        # Initialize leaf stages
        self.leaf_stages = ['primordial', 'emerging', 'expanding', 'mature', 'senescing']
        for stage in self.leaf_stages:
            self.state.leaf_age_distribution[stage] = 0
            self.state.leaf_size_distribution[stage] = 0.0
            self.state.leaf_nitrogen_distribution[stage] = 0.0
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'environmental_control': ['temperature', 'humidity', 'light_intensity'],
            'phenology_simulator': ['growth_stage', 'development_index'],
            'biomass_allocation_simulator': ['leaf_biomass', 'total_biomass'],
            'stress_models': ['temperature_stress', 'water_stress', 'nutrient_stress'],
            'nutrient_models_simulator': ['nitrogen_availability', 'nitrogen_uptake'],
            'canopy_architecture_simulator': ['canopy_height', 'lai']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = leaf_params.cache_timeout  # Get from CSV parameters
        
        print(f"Leaf development simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Leaf development simulator: Simulation started")
        self.state = LeafDevelopmentState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Initialize leaf state
        initial_leaf_state = LeafDevelopmentState(
            total_leaves=0,
            leaf_appearance_rate=0.0,
            leaf_expansion_rate=0.0,
            leaf_senescence_rate=0.0,
            total_leaf_area=0.0,
            total_leaf_weight=0.0,
            leaf_area_index=0.0,
            leaf_weight_ratio=0.0,
            leaf_nitrogen_content=0.0,
            leaf_nitrogen_ratio=0.0,
            leaf_age_distribution={},
            leaf_size_distribution={},
            leaf_nitrogen_distribution={}
        )
        
        # Publish initial state
        self.publish_event(EventType.LEAF_DEVELOPMENT_UPDATE, {
            'total_leaves': self.state.total_leaves,
            'total_leaf_area': self.state.total_leaf_area,
            'total_leaf_weight': self.state.total_leaf_weight,
            'leaf_area_index': self.state.leaf_area_index,
            'leaf_appearance_rate': self.state.leaf_appearance_rate
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

# Execute leaf development calculation using model functions
            self._execute_leaf_development_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(LeafDevelopmentState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.LEAF_DEVELOPMENT_UPDATE, {
                'total_leaves': self.state.total_leaves,
                'leaf_appearance_rate': self.state.leaf_appearance_rate,
                'leaf_expansion_rate': self.state.leaf_expansion_rate,
                'leaf_senescence_rate': self.state.leaf_senescence_rate,
                'total_leaf_area': self.state.total_leaf_area,
                'total_leaf_weight': self.state.total_leaf_weight,
                'leaf_area_index': self.state.leaf_area_index,
                'leaf_weight_ratio': self.state.leaf_weight_ratio,
                'leaf_nitrogen_content': self.state.leaf_nitrogen_content,
                'leaf_nitrogen_ratio': self.state.leaf_nitrogen_ratio,
                'leaf_age_distribution': self.state.leaf_age_distribution,
                'leaf_size_distribution': self.state.leaf_size_distribution,
                'leaf_nitrogen_distribution': self.state.leaf_nitrogen_distribution,
                'cumulative_thermal_time': self.state.cumulative_thermal_time,
                'phyllochron_adjusted': self.state.phyllochron_adjusted,
                'leaf_growth_stress': self.state.leaf_growth_stress,
                'leaf_senescence_stress': self.state.leaf_senescence_stress,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_thermal_time = 0.0
                
        except Exception as e:
            print(f"Leaf development simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Raise error according to Rules.md - no error suppression
            raise
    

    def _execute_leaf_development_step(self, weather_data: Dict[str, Any]):
        """Execute leaf development calculation using model functions - no shortcuts"""
        try:
            # Get environmental data from environmental control simulator
            env_data = self.dependency_cache.get('environmental_control', {})
            temperature = env_data.get('temperature')
            humidity = env_data.get('humidity')
            light_intensity = env_data.get('light_intensity')
            
            if any(x is None for x in [temperature, humidity, light_intensity]):
                raise ValueError("Environmental data missing from environmental_control - no defaults allowed")
            
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            
            if any(x is None for x in [growth_stage, development_index]):
                raise ValueError("Phenology data missing from phenology_simulator - no defaults allowed")
            
            # Get biomass data from biomass allocation simulator
            biomass_data = self.dependency_cache.get('biomass_allocation_simulator', {})
            leaf_biomass = biomass_data.get('leaf_biomass')
            total_biomass = biomass_data.get('total_biomass')
            
            if any(x is None for x in [leaf_biomass, total_biomass]):
                raise ValueError("Biomass data missing from biomass_allocation_simulator - no defaults allowed")
            
            # Get stress data from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            temperature_stress = stress_data.get('temperature_stress')
            water_stress = stress_data.get('water_stress')
            nutrient_stress = stress_data.get('nutrient_stress')
            
            if any(x is None for x in [temperature_stress, water_stress, nutrient_stress]):
                raise ValueError("Stress data missing from stress_models - no defaults allowed")
            
            # Get nutrient data from nutrient models simulator
            nutrient_data = self.dependency_cache.get('nutrient_models_simulator', {})
            nitrogen_availability = nutrient_data.get('nitrogen_availability')
            nitrogen_uptake = nutrient_data.get('nitrogen_uptake')
            
            if any(x is None for x in [nitrogen_availability, nitrogen_uptake]):
                raise ValueError("Nutrient data missing from nutrient_models_simulator - no defaults allowed")
            
            # Get canopy data from canopy architecture simulator
            canopy_data = self.dependency_cache.get('canopy_architecture_simulator', {})
            canopy_height = canopy_data.get('canopy_height')
            lai = canopy_data.get('lai')
            
            if any(x is None for x in [canopy_height, lai]):
                raise ValueError("Canopy data missing from canopy_architecture_simulator - no defaults allowed")
            
            # Create current leaf state
            current_leaf_state = LeafDevelopmentState(
                total_leaves=self.state.total_leaves,
                leaf_appearance_rate=self.state.leaf_appearance_rate,
                leaf_expansion_rate=self.state.leaf_expansion_rate,
                leaf_senescence_rate=self.state.leaf_senescence_rate,
                total_leaf_area=self.state.total_leaf_area,
                total_leaf_weight=self.state.total_leaf_weight,
                leaf_area_index=self.state.leaf_area_index,
                leaf_weight_ratio=self.state.leaf_weight_ratio,
                leaf_nitrogen_content=self.state.leaf_nitrogen_content,
                leaf_nitrogen_ratio=self.state.leaf_nitrogen_ratio,
                leaf_age_distribution=self.state.leaf_age_distribution,
                leaf_size_distribution=self.state.leaf_size_distribution,
                leaf_nitrogen_distribution=self.state.leaf_nitrogen_distribution
            )
            
            # Calculate leaf development using model functions - no shortcuts
            # Use update_leaf_areas method with simplified parameters
            daily_thermal_time_list = [self.state.daily_thermal_time]

            # Calculate stress factors using the model's method
            stress_factors = self.model.calculate_stress_factors(
                water_stress_list=[water_stress],
                nitrogen_stress_list=[nutrient_stress],
                temperature_stress_list=[temperature_stress]
            )

            # CRITICAL: Update V-stage to create new leaf cohorts based on thermal time
            # This must be called BEFORE update_leaf_areas to ensure new leaves are tracked
            new_leaves = self.model.update_v_stage(
                daily_thermal_time_list=daily_thermal_time_list,
                stress_factors=stress_factors
            )

            result = self.model.update_leaf_areas(
                daily_thermal_time_list=daily_thermal_time_list,
                stress_factors=stress_factors
            )
            
            # Update state with model results
            self.state.total_leaves = result.get('total_leaves', self.state.total_leaves)
            self.state.leaf_appearance_rate = result.get('leaf_appearance_rate', self.state.leaf_appearance_rate)
            self.state.leaf_expansion_rate = result.get('leaf_expansion_rate', self.state.leaf_expansion_rate)
            self.state.leaf_senescence_rate = result.get('leaf_senescence_rate', self.state.leaf_senescence_rate)
            self.state.total_leaf_area = result.get('total_leaf_area', self.state.total_leaf_area)
            self.state.total_leaf_weight = result.get('total_leaf_weight', self.state.total_leaf_weight)
            self.state.leaf_area_index = result.get('leaf_area_index', self.state.leaf_area_index)
            self.state.leaf_weight_ratio = result.get('leaf_weight_ratio', self.state.leaf_weight_ratio)
            self.state.leaf_nitrogen_content = result.get('leaf_nitrogen_content', self.state.leaf_nitrogen_content)
            self.state.leaf_nitrogen_ratio = result.get('leaf_nitrogen_ratio', self.state.leaf_nitrogen_ratio)
            
            # Update distributions
            leaf_age_dist = result.get('leaf_age_distribution', {})
            for stage in self.leaf_stages:
                if stage in leaf_age_dist:
                    self.state.leaf_age_distribution[stage] = leaf_age_dist[stage]
            
            leaf_size_dist = result.get('leaf_size_distribution', {})
            for stage in self.leaf_stages:
                if stage in leaf_size_dist:
                    self.state.leaf_size_distribution[stage] = leaf_size_dist[stage]
            
            leaf_nitrogen_dist = result.get('leaf_nitrogen_distribution', {})
            for stage in self.leaf_stages:
                if stage in leaf_nitrogen_dist:
                    self.state.leaf_nitrogen_distribution[stage] = leaf_nitrogen_dist[stage]
            
            # Update thermal time and phyllochron
            hourly_thermal_time = result.get('thermal_time_increment', 0.0) * 3600  # Convert to hourly
            self.state.daily_thermal_time += hourly_thermal_time
            self.state.cumulative_thermal_time += hourly_thermal_time
            self.state.phyllochron_adjusted = result.get('phyllochron_adjusted', self.state.phyllochron_adjusted)
            
            # Update stress factors
            self.state.leaf_growth_stress = result.get('leaf_growth_stress', self.state.leaf_growth_stress)
            self.state.leaf_senescence_stress = result.get('leaf_senescence_stress', self.state.leaf_senescence_stress)
            
        except Exception as e:
            print(f"Error in leaf development calculation: {e}")
            # Raise error according to Rules.md - no error suppression
            raise
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity,
                'light_intensity': inputs.solar_radiation,  # Use solar_radiation instead of light_intensity
                'co2_concentration': inputs.co2_concentration
            }
            
            # Execute leaf development step using model functions
            self._execute_leaf_development_step(weather_data)
            
            # Create output
            outputs = {
                'total_leaves': self.state.total_leaves,
                'leaf_appearance_rate': self.state.leaf_appearance_rate,
                'leaf_expansion_rate': self.state.leaf_expansion_rate,
                'leaf_senescence_rate': self.state.leaf_senescence_rate,
                'total_leaf_area': self.state.total_leaf_area,
                'total_leaf_weight': self.state.total_leaf_weight,
                'leaf_area_index': self.state.leaf_area_index,
                'leaf_weight_ratio': self.state.leaf_weight_ratio,
                'leaf_nitrogen_content': self.state.leaf_nitrogen_content,
                'leaf_nitrogen_ratio': self.state.leaf_nitrogen_ratio,
                'leaf_age_distribution': self.state.leaf_age_distribution,
                'leaf_size_distribution': self.state.leaf_size_distribution,
                'leaf_nitrogen_distribution': self.state.leaf_nitrogen_distribution,
                'cumulative_thermal_time': self.state.cumulative_thermal_time,
                'phyllochron_adjusted': self.state.phyllochron_adjusted,
                'leaf_growth_stress': self.state.leaf_growth_stress,
                'leaf_senescence_stress': self.state.leaf_senescence_stress,
                'daily_thermal_time': self.state.daily_thermal_time
            }
            
            return DailyUpdateOutput(
                model_name='leaf_development_simulator',
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
                model_name='leaf_development_simulator',
                day=inputs.day,
                success=False,
                primary_results={},
                secondary_results={'error_message': f'Leaf development calculation failed: {str(e)}'},
                internal_state={},
                validation_result=None,
                processing_time_ms=0.0
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'total_leaves': self.state.total_leaves,
            'leaf_appearance_rate': self.state.leaf_appearance_rate,
            'leaf_expansion_rate': self.state.leaf_expansion_rate,
            'leaf_senescence_rate': self.state.leaf_senescence_rate,
            'total_leaf_area': self.state.total_leaf_area,
            'total_leaf_weight': self.state.total_leaf_weight,
            'leaf_area_index': self.state.leaf_area_index,
            'leaf_weight_ratio': self.state.leaf_weight_ratio,
            'leaf_nitrogen_content': self.state.leaf_nitrogen_content,
            'leaf_nitrogen_ratio': self.state.leaf_nitrogen_ratio,
            'leaf_age_distribution': self.state.leaf_age_distribution,
            'leaf_size_distribution': self.state.leaf_size_distribution,
            'leaf_nitrogen_distribution': self.state.leaf_nitrogen_distribution,
            'cumulative_thermal_time': self.state.cumulative_thermal_time,
            'phyllochron_adjusted': self.state.phyllochron_adjusted,
            'leaf_growth_stress': self.state.leaf_growth_stress,
            'leaf_senescence_stress': self.state.leaf_senescence_stress,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        leaf_data = {
            'total_leaves': self.state.total_leaves,
            'leaf_appearance_rate': self.state.leaf_appearance_rate,
            'leaf_expansion_rate': self.state.leaf_expansion_rate,
            'leaf_senescence_rate': self.state.leaf_senescence_rate,
            'total_leaf_area': self.state.total_leaf_area,
            'total_leaf_weight': self.state.total_leaf_weight,
            'leaf_area_index': self.state.leaf_area_index,
            'leaf_weight_ratio': self.state.leaf_weight_ratio,
            'leaf_nitrogen_content': self.state.leaf_nitrogen_content,
            'leaf_nitrogen_ratio': self.state.leaf_nitrogen_ratio,
            'leaf_age_distribution': self.state.leaf_age_distribution,
            'leaf_size_distribution': self.state.leaf_size_distribution,
            'leaf_nitrogen_distribution': self.state.leaf_nitrogen_distribution,
            'cumulative_thermal_time': self.state.cumulative_thermal_time,
            'daily_thermal_time': self.state.daily_thermal_time,
            'phyllochron_adjusted': self.state.phyllochron_adjusted,
            'leaf_growth_stress': self.state.leaf_growth_stress,
            'leaf_senescence_stress': self.state.leaf_senescence_stress,
            'leaf_cohorts': self.model.leaf_cohorts  # CRITICAL: Share real leaf cohorts for senescence
        }

        # Add individual stage data
        for stage in self.leaf_stages:
            leaf_data[f'{stage}_leaves'] = self.state.leaf_age_distribution.get(stage, 0)
            leaf_data[f'{stage}_size'] = self.state.leaf_size_distribution.get(stage, 0.0)
            leaf_data[f'{stage}_nitrogen'] = self.state.leaf_nitrogen_distribution.get(stage, 0.0)

        self.dependency_cache['leaf_development_simulator'] = leaf_data

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'total_leaves': self.state.total_leaves,
            'leaf_appearance_rate': self.state.leaf_appearance_rate,
            'leaf_expansion_rate': self.state.leaf_expansion_rate,
            'leaf_senescence_rate': self.state.leaf_senescence_rate,
            'total_leaf_area': self.state.total_leaf_area,
            'total_leaf_weight': self.state.total_leaf_weight,
            'leaf_area_index': self.state.leaf_area_index,
            'leaf_weight_ratio': self.state.leaf_weight_ratio,
            'leaf_nitrogen_content': self.state.leaf_nitrogen_content,
            'leaf_nitrogen_ratio': self.state.leaf_nitrogen_ratio,
            'leaf_age_distribution': self.state.leaf_age_distribution,
            'leaf_size_distribution': self.state.leaf_size_distribution,
            'leaf_nitrogen_distribution': self.state.leaf_nitrogen_distribution,
            'cumulative_thermal_time': self.state.cumulative_thermal_time,
            'phyllochron_adjusted': self.state.phyllochron_adjusted,
            'leaf_growth_stress': self.state.leaf_growth_stress,
            'leaf_senescence_stress': self.state.leaf_senescence_stress,
            'daily_thermal_time': self.state.daily_thermal_time,
            'leaf_area': self.state.total_leaf_area,  # Add leaf_area alias
            'leaf_number': self.state.total_leaves,  # Add leaf_number alias
            'leaf_size': self.state.total_leaf_area / max(self.state.total_leaves, 1)  # Add leaf_size alias (average leaf size)
        }
        
        # Add individual stage data
        for stage in self.leaf_stages:
            data_map[f'leaf_count_{stage}'] = self.state.leaf_age_distribution.get(stage, 0)
            data_map[f'leaf_area_{stage}'] = self.state.leaf_size_distribution.get(stage, 0.0)
            data_map[f'leaf_nitrogen_{stage}'] = self.state.leaf_nitrogen_distribution.get(stage, 0.0)
        
        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            # Environmental data will be requested when needed
            
        elif event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters from phenology simulator
            phenology_data = event.data
            # Phenology data will be requested when needed
            
        elif event.event_type == EventType.BIOMASS_UPDATE:
            # Update biomass parameters from biomass allocation simulator
            biomass_data = event.data
            # Biomass data will be requested when needed
            
        elif event.event_type == EventType.STRESS_UPDATE:
            # Update stress factors from stress models simulator
            stress_data = event.data
            # Stress data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Leaf development simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final total leaves: {self.state.total_leaves}")
        print(f"Final leaf area: {self.state.total_leaf_area:.2f} cm²")
        print(f"Final leaf weight: {self.state.total_leaf_weight:.2f} g")
        print(f"Final leaf area index: {self.state.leaf_area_index:.3f}")
        print(f"Final leaf nitrogen content: {self.state.leaf_nitrogen_content:.2f} g")
        print(f"Total thermal time: {self.state.cumulative_thermal_time:.1f} °C-day")
        
        # Print leaf stage distribution
        print("Final leaf stage distribution:")
        for stage, count in self.state.leaf_age_distribution.items():
            print(f"  {stage}: {count} leaves")
        
        # Publish final results
        self.publish_event(EventType.LEAF_DEVELOPMENT_UPDATE, {
            'final_total_leaves': self.state.total_leaves,
            'final_leaf_appearance_rate': self.state.leaf_appearance_rate,
            'final_leaf_expansion_rate': self.state.leaf_expansion_rate,
            'final_leaf_senescence_rate': self.state.leaf_senescence_rate,
            'final_total_leaf_area': self.state.total_leaf_area,
            'final_total_leaf_weight': self.state.total_leaf_weight,
            'final_leaf_area_index': self.state.leaf_area_index,
            'final_leaf_weight_ratio': self.state.leaf_weight_ratio,
            'final_leaf_nitrogen_content': self.state.leaf_nitrogen_content,
            'final_leaf_nitrogen_ratio': self.state.leaf_nitrogen_ratio,
            'final_leaf_age_distribution': self.state.leaf_age_distribution,
            'final_leaf_size_distribution': self.state.leaf_size_distribution,
            'final_leaf_nitrogen_distribution': self.state.leaf_nitrogen_distribution,
            'total_thermal_time': self.state.cumulative_thermal_time,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Leaf development simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        leaf_counts = [s.total_leaves for s in self.history]
        leaf_areas = [s.total_leaf_area for s in self.history]
        leaf_weights = [s.total_leaf_weight for s in self.history]
        lai_values = [s.leaf_area_index for s in self.history]
        
        # Calculate leaf development rates
        if len(leaf_counts) > 1:
            leaf_appearance_rate = (leaf_counts[-1] - leaf_counts[0]) / len(leaf_counts)
        else:
            leaf_appearance_rate = 0.0
        
        return {
            'total_steps': len(self.history),
            'final_total_leaves': self.state.total_leaves,
            'avg_total_leaves': sum(leaf_counts) / len(leaf_counts),
            'final_leaf_area': self.state.total_leaf_area,
            'avg_leaf_area': sum(leaf_areas) / len(leaf_areas),
            'final_leaf_weight': self.state.total_leaf_weight,
            'avg_leaf_weight': sum(leaf_weights) / len(leaf_weights),
            'final_leaf_area_index': self.state.leaf_area_index,
            'avg_leaf_area_index': sum(lai_values) / len(lai_values),
            'leaf_appearance_rate': leaf_appearance_rate,
            'total_thermal_time': self.state.cumulative_thermal_time,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
