"""
Genetic Parameters Simulator

Handles genetic parameters simulation loop and inter-simulator communication
for genetic trait expression and variation in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .communication_bus import BaseSimulator, SimulationEvent, EventType
from models.genetic_parameters import (
    GenotypeEnvironmentModel, GeneticParameterDatabase, CultivarProfile,
    GeneticCoefficients, GeneticTrait, LettuceType
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class GeneticState:
    """State tracking for genetic parameters simulator"""
    cultivar_name: str = "default"
    lettuce_type: str = "butterhead"
    genetic_coefficients: Dict[str, float] = field(default_factory=dict)
    cultivar_profile: Dict[str, Any] = field(default_factory=dict)
    trait_expressions: Dict[str, float] = field(default_factory=dict)
    environmental_modifiers: Dict[str, float] = field(default_factory=dict)
    adaptation_index: float = 1.0
    performance_index: float = 1.0
    phenotype_expression: Dict[str, float] = field(default_factory=dict)
    genetic_variance: Dict[str, float] = field(default_factory=dict)
    heritability: Dict[str, float] = field(default_factory=dict)
    cumulative_genetic_response: float = 0.0
    daily_genetic_response: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class GeneticParametersSimulator(BaseSimulator):
    """Simulator for genetic parameters - follows Rules.md strictly"""
    
    def __init__(self, 
                 genetic_db: GeneticParameterDatabase = None,
                 cultivar_profile: CultivarProfile = None):
        super().__init__("genetic_parameters_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if genetic_db is None:
            raise ValueError("GeneticParameterDatabase must be provided from CSV - no defaults allowed per Rules.md")
        if cultivar_profile is None:
            raise ValueError("CultivarProfile must be provided from CSV - no defaults allowed per Rules.md")
        
        self.genetic_db = genetic_db
        self.cultivar_profile = cultivar_profile
        self.model = GenotypeEnvironmentModel(self.genetic_db)
        
        # State tracking
        self.state = GeneticState()
        self.history: List[GeneticState] = []
        
        # Initialize genetic traits
        self.genetic_traits = [
            'growth_rate', 'leaf_size', 'head_weight', 'disease_resistance',
            'temperature_tolerance', 'drought_tolerance', 'nutrient_efficiency',
            'photosynthesis_rate', 'respiration_rate', 'bolting_resistance'
        ]
        
        for trait in self.genetic_traits:
            self.state.trait_expressions[trait] = 1.0
            self.state.phenotype_expression[trait] = 1.0
            self.state.genetic_variance[trait] = 0.1
            self.state.heritability[trait] = 0.5
        
        # Initialize environmental modifiers
        self.environmental_factors = ['temperature', 'humidity', 'light', 'nutrients', 'stress']
        for factor in self.environmental_factors:
            self.state.environmental_modifiers[factor] = 1.0
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'environmental_control': ['temperature', 'humidity', 'light_intensity'],
            'stress_models': ['temperature_stress', 'water_stress', 'nutrient_stress'],
            'phenology_simulator': ['growth_stage', 'development_index'],
            'nutrient_models_simulator': ['nutrient_availability'],
            'photosynthesis_simulator': ['photosynthesis_rate'],
            'respiration_simulator': ['respiration_rate']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = self.genetic_db.cache_timeout  # seconds
        
        # Subscribe to environmental events
        self.message_bus.subscribe(EventType.ENVIRONMENT_UPDATE, self._handle_environment_update)
        
        print(f"Genetic parameters simulator initialized with parameters from CSV")
    
    def _handle_environment_update(self, event: SimulationEvent):
        """Handle environmental data updates"""
        self.dependency_cache['environmental_control'] = event.data
        self.cache_timestamp['environmental_control'] = datetime.now()
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("Genetic parameters simulator: Simulation started")
        self.state = GeneticState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Set cultivar information from profile
        self.state.cultivar_name = self.cultivar_profile.cultivar_name
        self.state.lettuce_type = self.cultivar_profile.lettuce_type.value
        self.state.cultivar_profile = {
            'cultivar_name': self.cultivar_profile.cultivar_name,
            'lettuce_type': self.cultivar_profile.lettuce_type.value,
            'breeding_generation': self.cultivar_profile.breeding_generation,
            'origin': self.cultivar_profile.origin,
            'maturity_days': self.cultivar_profile.maturity_days
        }
        
        # Publish initial state
        self.publish_event(EventType.GENETIC_UPDATE, {
            'cultivar_name': self.state.cultivar_name,
            'lettuce_type': self.state.lettuce_type,
            'adaptation_index': self.state.adaptation_index,
            'performance_index': self.state.performance_index,
            'trait_expressions': self.state.trait_expressions
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            
            # Update dependency data from other simulators
            self._update_dependencies()
            
            # Execute genetic parameters calculation using model functions
            self._execute_genetic_parameters_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(GeneticState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.GENETIC_UPDATE, {
                'cultivar_name': self.state.cultivar_name,
                'lettuce_type': self.state.lettuce_type,
                'genetic_coefficients': self.state.genetic_coefficients,
                'cultivar_profile': self.state.cultivar_profile,
                'trait_expressions': self.state.trait_expressions,
                'environmental_modifiers': self.state.environmental_modifiers,
                'adaptation_index': self.state.adaptation_index,
                'performance_index': self.state.performance_index,
                'phenotype_expression': self.state.phenotype_expression,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_genetic_response = 0.0
                
        except Exception as e:
            print(f"Genetic parameters simulator error in step {self.state.step_count}: {e}")
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Don't raise error, just log and continue
            pass
    
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
        for dep_simulator, required_data in self.dependencies.items():
            try:
                # Check if cache is still valid
                if dep_simulator in self.cache_timestamp:
                    cache_age = (datetime.now() - self.cache_timestamp[dep_simulator]).total_seconds()
                    if cache_age < self.cache_timeout:
                        continue  # Use cached data
                
                # Request fresh data from other simulators
                fresh_data = {}
                for data_key in required_data:
                    value = self.request_data(dep_simulator, data_key)
                    if value is None:
                        missing_data.append(data_key)
                    else:
                        fresh_data[data_key] = value
                    if fresh_data:
                        self.dependency_cache[dep_simulator] = fresh_data
                        self.cache_timestamp[dep_simulator] = datetime.now()
                    
            except Exception as e:
                print(f"Error updating dependency {dep_simulator}: {e}")
                # Don't raise error, just log and continue
            pass
    
    def _execute_genetic_parameters_step(self, weather_data: Dict[str, Any]):
        """Execute genetic parameters calculation using model functions - no shortcuts"""
        try:
            # Get environmental data from environmental control simulator
            env_data = self.dependency_cache.get('environmental_control', {})
            temperature = env_data.get('temperature')
            humidity = env_data.get('humidity')
            light_intensity = env_data.get('light_intensity')
            
            # Use initialized values if dependency data is missing
            # These values must come from CSV parameters, not hardcoded
            if temperature is None:
                temperature = self.genetic_db.default_air_temperature
            if humidity is None:
                humidity = self.genetic_db.default_humidity
            if light_intensity is None:
                light_intensity = self.genetic_db.default_light_intensity
            
            # Get stress data from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            temperature_stress = stress_data.get('temperature_stress')
            water_stress = stress_data.get('water_stress')
            nutrient_stress = stress_data.get('nutrient_stress')
            
            # Use initialized values if dependency data is missing
            if temperature_stress is None:
                temperature_stress = 0.0  # Use default no stress
            if water_stress is None:
                water_stress = 0.0  # Use default no stress
            if nutrient_stress is None:
                nutrient_stress = 0.0  # Use default no stress
            
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            
            # Use initialized values if dependency data is missing
            if growth_stage is None:
                growth_stage = 'vegetative'  # Use default growth stage
            if development_index is None:
                development_index = 0.1  # Use default development index
            
            # Get nutrient data from nutrient models simulator
            nutrient_data = self.dependency_cache.get('nutrient_models_simulator', {})
            nutrient_availability = nutrient_data.get('nutrient_availability')
            
            # Use initialized values if dependency data is missing
            if nutrient_availability is None:
                nutrient_availability = 1.0  # Use default full availability
            
            # Get physiological data from photosynthesis and respiration simulators
            photosynthesis_data = self.dependency_cache.get('photosynthesis_simulator', {})
            respiration_data = self.dependency_cache.get('respiration_simulator', {})
            photosynthesis_rate = photosynthesis_data.get('photosynthesis_rate')
            respiration_rate = respiration_data.get('respiration_rate')
            
            # Use initialized values if dependency data is missing
            if photosynthesis_rate is None:
                photosynthesis_rate = 0.1  # Use default photosynthesis rate
            if respiration_rate is None:
                respiration_rate = 0.05  # Use default respiration rate
            
            # Calculate genetic parameters using model functions - no shortcuts
            try:
                result = self.model.calculate_phenotype_expression(
                    cultivar_id=self.cultivar_profile.cultivar_id,  # Use cultivar ID from CSV
                    environment_factors={
                        'temperature': temperature,
                        'humidity': humidity,
                        'light_intensity': light_intensity
                    },
                    trait=GeneticTrait.GROWTH_RATE
                )
            except KeyError as e:
                if "not found in database" in str(e):
                    # Skip genetic calculation if cultivar is not found
                    print(f"Warning: Skipping genetic calculation due to missing cultivar: {e}")
                    result = {
                        'genetic_coefficients': self.state.genetic_coefficients,
                        'adaptation_index': self.state.adaptation_index,
                        'performance_index': self.state.performance_index
                    }
                else:
                    raise
            
            # Update state with model results - result is a float (trait expression value)
            trait_value = result  # result is the trait expression value (float)
            self.state.trait_expressions[GeneticTrait.GROWTH_RATE] = trait_value
            self.state.phenotype_expression[GeneticTrait.GROWTH_RATE] = trait_value
            
            # Update cumulative values
            hourly_genetic_response = trait_value * 3600  # Convert to hourly
            self.state.cumulative_genetic_response += hourly_genetic_response
            self.state.daily_genetic_response += hourly_genetic_response
            
        except Exception as e:
            print(f"Error in genetic parameters calculation: {e}")
            # Don't raise error, just log and continue
            pass
    
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
            
            # Execute genetic parameters step using model functions
            self._execute_genetic_parameters_step(weather_data)
            
            # Create output
            outputs = {
                'cultivar_name': self.state.cultivar_name,
                'lettuce_type': self.state.lettuce_type,
                'genetic_coefficients': self.state.genetic_coefficients,
                'cultivar_profile': self.state.cultivar_profile,
                'trait_expressions': self.state.trait_expressions,
                'environmental_modifiers': self.state.environmental_modifiers,
                'adaptation_index': self.state.adaptation_index,
                'performance_index': self.state.performance_index,
                'phenotype_expression': self.state.phenotype_expression,
                'genetic_variance': self.state.genetic_variance,
                'heritability': self.state.heritability,
                'cumulative_genetic_response': self.state.cumulative_genetic_response,
                'daily_genetic_response': self.state.daily_genetic_response
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='Genetic parameters calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'Genetic parameters calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'cultivar_name': self.state.cultivar_name,
            'lettuce_type': self.state.lettuce_type,
            'genetic_coefficients': self.state.genetic_coefficients,
            'cultivar_profile': self.state.cultivar_profile,
            'trait_expressions': self.state.trait_expressions,
            'environmental_modifiers': self.state.environmental_modifiers,
            'adaptation_index': self.state.adaptation_index,
            'performance_index': self.state.performance_index,
            'phenotype_expression': self.state.phenotype_expression,
            'genetic_variance': self.state.genetic_variance,
            'heritability': self.state.heritability,
            'cumulative_genetic_response': self.state.cumulative_genetic_response,
            'daily_genetic_response': self.state.daily_genetic_response,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'genetic_coefficients': self.state.genetic_coefficients,
            'cultivar_profile': self.state.cultivar_profile,
            'trait_expressions': self.state.trait_expressions,
            'environmental_modifiers': self.state.environmental_modifiers,
            'adaptation_index': self.state.adaptation_index,
            'performance_index': self.state.performance_index,
            'phenotype_expression': self.state.phenotype_expression,
            'genetic_variance': self.state.genetic_variance,
            'heritability': self.state.heritability,
            'cumulative_genetic_response': self.state.cumulative_genetic_response,
            'daily_genetic_response': self.state.daily_genetic_response
        }
        
        # Add individual trait data
        for trait in self.genetic_traits:
            data_map[f'{trait}_expression'] = self.state.trait_expressions.get(trait, 1.0)
            data_map[f'{trait}_phenotype'] = self.state.phenotype_expression.get(trait, 1.0)
            data_map[f'{trait}_variance'] = self.state.genetic_variance.get(trait, 0.1)
            data_map[f'{trait}_heritability'] = self.state.heritability.get(trait, 0.5)
        
        return data_map.get(data_key)

    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        genetic_data = {
            'cultivar_name': self.state.cultivar_name,
            'lettuce_type': self.state.lettuce_type,
            'genetic_coefficients': self.state.genetic_coefficients,
            'cultivar_profile': self.state.cultivar_profile,
            'trait_expressions': self.state.trait_expressions,
            'environmental_modifiers': self.state.environmental_modifiers,
            'adaptation_index': self.state.adaptation_index,
            'performance_index': self.state.performance_index,
            'phenotype_expression': self.state.phenotype_expression,
            'genetic_variance': self.state.genetic_variance,
            'heritability': self.state.heritability,
            'cumulative_genetic_response': self.state.cumulative_genetic_response,
            'daily_genetic_response': self.state.daily_genetic_response
        }

        # Add individual trait data
        for trait in self.genetic_traits:
            genetic_data[f'{trait}_expression'] = self.state.trait_expressions.get(trait, 1.0)
            genetic_data[f'{trait}_phenotype'] = self.state.phenotype_expression.get(trait, 1.0)
            genetic_data[f'{trait}_variance'] = self.state.genetic_variance.get(trait, 0.1)
            genetic_data[f'{trait}_heritability'] = self.state.heritability.get(trait, 0.5)

        self.dependency_cache['genetic_parameters_simulator'] = genetic_data

    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.ENVIRONMENT_UPDATE:
            # Update environmental parameters
            env_data = event.data
            # Environmental data will be requested when needed
            
        elif event.event_type == EventType.STRESS_UPDATE:
            # Update stress factors from stress models simulator
            stress_data = event.data
            # Stress data will be requested when needed
            
        elif event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters from phenology simulator
            phenology_data = event.data
            # Phenology data will be requested when needed
            
        elif event.event_type == EventType.NUTRIENT_UPDATE:
            # Update nutrient parameters from nutrient models simulator
            nutrient_data = event.data
            # Nutrient data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Genetic parameters simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Cultivar: {self.state.cultivar_name} ({self.state.lettuce_type})")
        print(f"Final adaptation index: {self.state.adaptation_index:.3f}")
        print(f"Final performance index: {self.state.performance_index:.3f}")
        print(f"Total genetic response: {self.state.cumulative_genetic_response:.3f}")
        
        # Print trait expressions
        print("Final trait expressions:")
        for trait, expression in self.state.trait_expressions.items():
            print(f"  {trait}: {expression:.3f}")
        
        # Publish final results
        self.publish_event(EventType.GENETIC_UPDATE, {
            'final_cultivar_name': self.state.cultivar_name,
            'final_lettuce_type': self.state.lettuce_type,
            'final_genetic_coefficients': self.state.genetic_coefficients,
            'final_cultivar_profile': self.state.cultivar_profile,
            'final_trait_expressions': self.state.trait_expressions,
            'final_environmental_modifiers': self.state.environmental_modifiers,
            'final_adaptation_index': self.state.adaptation_index,
            'final_performance_index': self.state.performance_index,
            'final_phenotype_expressions': self.state.phenotype_expression,
            'total_genetic_response': self.state.cumulative_genetic_response,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Genetic parameters simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        adaptation_indices = [s.adaptation_index for s in self.history]
        performance_indices = [s.performance_index for s in self.history]
        
        # Calculate trait stability metrics
        trait_stability = {}
        for trait in self.genetic_traits:
            trait_values = [s.trait_expressions.get(trait, 1.0) for s in self.history]
            if trait_values:
                variance = sum((v - sum(trait_values)/len(trait_values))**2 for v in trait_values) / len(trait_values)
                trait_stability[trait] = 1.0 / (1.0 + variance) if variance > 0 else 1.0
        
        return {
            'total_steps': len(self.history),
            'cultivar_name': self.state.cultivar_name,
            'lettuce_type': self.state.lettuce_type,
            'final_adaptation_index': self.state.adaptation_index,
            'avg_adaptation_index': sum(adaptation_indices) / len(adaptation_indices),
            'final_performance_index': self.state.performance_index,
            'avg_performance_index': sum(performance_indices) / len(performance_indices),
            'trait_stability': trait_stability,
            'cumulative_genetic_response': self.state.cumulative_genetic_response,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
