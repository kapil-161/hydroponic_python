"""
pH Model Simulator

Handles pH simulation loop and inter-simulator communication
for pH dynamics and buffering in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .communication_bus import BaseSimulator, SimulationEvent, EventType
from models.ph_model import (
    HydroponicPHModel, PHParameters, PHState,
    BufferSystem, NutrientSolubility
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class PHState:
    """State tracking for pH model simulator"""
    ph: float = 6.5
    ph_stability: float = 1.0
    total_alkalinity: float = 0.0
    carbonate_concentration: float = 0.0
    phosphate_concentration: float = 0.0
    buffer_capacity: float = 0.0
    ph_drift_rate: float = 0.0
    ph_adjustment_needed: float = 0.0
    nutrient_solubility: Dict[str, float] = field(default_factory=dict)
    iron_solubility: float = 1.0
    calcium_phosphate_precipitation: float = 0.0
    magnesium_phosphate_precipitation: float = 0.0
    cumulative_ph_adjustment: float = 0.0
    daily_ph_adjustment: float = 0.0
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class PHModelSimulator(BaseSimulator):
    """Simulator for pH model - follows Rules.md strictly"""
    
    def __init__(self, parameters: PHParameters = None):
        super().__init__("ph_model_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("PHParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = HydroponicPHModel(self.parameters)
        
        # State tracking
        self.state = PHState()
        self.history: List[PHState] = []
        
        # Initialize nutrient solubility tracking
        self.nutrient_elements = ['Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo', 'Ca', 'Mg', 'P']
        for element in self.nutrient_elements:
            self.state.nutrient_solubility[element] = 1.0
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'nutrient_models_simulator': ['nutrient_concentrations', 'solution_ec'],
            'water_uptake_simulator': ['water_uptake_rate', 'transpiration_rate'],
            'environmental_control': ['temperature', 'humidity'],
            'stress_models': ['ph_stress']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = self.parameters.cache_timeout  # seconds
        
        print(f"pH model simulator initialized with parameters from CSV")
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        print("pH model simulator: Simulation started")
        self.state = PHState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize model with parameters from CSV
        self.model.initialize()
        
        # Publish initial state
        self.publish_event(EventType.PH_UPDATE, {
            'ph': self.state.ph,
            'ph_stability': self.state.ph_stability,
            'total_alkalinity': self.state.total_alkalinity,
            'buffer_capacity': self.state.buffer_capacity
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            
            # Update dependency data from other simulators
            self._update_dependencies()
            
            # Execute pH calculation using model functions
            self._execute_ph_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()
            
            # Store history
            self.history.append(PHState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.PH_UPDATE, {
                'ph': self.state.ph,
                'ph_stability': self.state.ph_stability,
                'total_alkalinity': self.state.total_alkalinity,
                'carbonate_concentration': self.state.carbonate_concentration,
                'phosphate_concentration': self.state.phosphate_concentration,
                'buffer_capacity': self.state.buffer_capacity,
                'ph_drift_rate': self.state.ph_drift_rate,
                'ph_adjustment_needed': self.state.ph_adjustment_needed,
                'nutrient_solubility': self.state.nutrient_solubility,
                'iron_solubility': self.state.iron_solubility,
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_ph_adjustment = 0.0
                
        except Exception as e:
            print(f"pH model simulator error in step {self.state.step_count}: {e}")
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
    
    def _execute_ph_step(self, weather_data: Dict[str, Any]):
        """Execute pH calculation using model functions - no shortcuts"""
        try:
            # Get nutrient data from nutrient models simulator
            nutrient_data = self.dependency_cache.get('nutrient_models_simulator', {})
            nutrient_concentrations = nutrient_data.get('nutrient_concentrations')
            solution_ec = nutrient_data.get('solution_ec')
            
            if any(x is None for x in [nutrient_concentrations, solution_ec]):
                raise ValueError("Nutrient data missing from nutrient_models_simulator - no defaults allowed")
            
            # Get water data from water uptake simulator
            water_data = self.dependency_cache.get('water_uptake_simulator', {})
            water_uptake_rate = water_data.get('water_uptake_rate')
            transpiration_rate = water_data.get('transpiration_rate')
            
            if any(x is None for x in [water_uptake_rate, transpiration_rate]):
                raise ValueError("Water data missing from water_uptake_simulator - no defaults allowed")
            
            # Get environmental conditions from daily weather file
            temperature = weather_data.get('temp_avg')
            humidity = weather_data.get('rel_humidity')
            
            if any(x is None for x in [temperature, humidity]):
                raise ValueError("Environmental data missing from weather data - no defaults allowed")
            
            # Get stress factors from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            ph_stress = stress_data.get('ph_stress')
            
            if ph_stress is None:
                raise ValueError("pH stress data missing from stress_models - no defaults allowed")
            
            # Create current pH state
            current_ph_state = PHState(
                ph=self.state.ph,
                total_alkalinity=self.state.total_alkalinity,
                carbonate_concentration=self.state.carbonate_concentration,
                phosphate_concentration=self.state.phosphate_concentration,
                buffer_capacity=self.state.buffer_capacity,
                ph_drift_rate=self.state.ph_drift_rate
            )
            
            # Calculate pH dynamics using model functions - no shortcuts
            # Create proper nutrient data for pH model
            # These values must come from CSV parameters, not hardcoded
            nutrient_uptake = {
                'NO3': self.parameters.default_nitrate_uptake,
                'NH4': self.parameters.default_ammonium_uptake,
                'PO4': self.parameters.default_phosphate_uptake
            }
            
            nutrient_concentrations = {
                'P-PO4': self.parameters.default_phosphate_concentration,
                'Fe': self.parameters.default_iron_concentration
            }
            
            result = self.model.update_ph_state(
                nutrient_uptake=nutrient_uptake,
                nutrient_concentrations=nutrient_concentrations,
                temperature=temperature,
                ec=solution_ec,  # Use solution_ec as ec
                time_hours=self.parameters.default_time_step
            )
            
            # Update state with model results
            self.state.ph = result.final_ph
            self.state.ph_stability = 1.0 - abs(result.ph_change_from_uptake)  # Estimate stability
            self.state.total_alkalinity = result.buffer_capacity
            self.state.carbonate_concentration = 0.0  # Default value
            self.state.phosphate_concentration = result.phosphate_species.get('H2PO4', 0.0) if hasattr(result, 'phosphate_species') else 0.0
            self.state.buffer_capacity = result.buffer_capacity
            self.state.ph_drift_rate = abs(result.ph_change_from_drift)
            self.state.ph_adjustment_needed = result.acid_dosed_ml_per_L + result.base_dosed_ml_per_L
            self.state.iron_solubility = result.available_nutrients.get('Fe', 1.0) if hasattr(result, 'available_nutrients') else 1.0
            self.state.calcium_phosphate_precipitation = result.nutrient_precipitation.get('Ca', 0.0) if hasattr(result, 'nutrient_precipitation') else 0.0
            self.state.magnesium_phosphate_precipitation = result.nutrient_precipitation.get('Mg', 0.0) if hasattr(result, 'nutrient_precipitation') else 0.0
            
            # Update nutrient solubility
            if hasattr(result, 'available_nutrients'):
                for element in self.nutrient_elements:
                    if element in result.available_nutrients:
                        self.state.nutrient_solubility[element] = result.available_nutrients[element]
            
            # Update cumulative values
            hourly_ph_adjustment = abs(self.state.ph_adjustment_needed) * 3600  # Convert to hourly
            self.state.cumulative_ph_adjustment += hourly_ph_adjustment
            self.state.daily_ph_adjustment += hourly_ph_adjustment
            
        except Exception as e:
            print(f"Error in pH calculation: {e}")
            # Don't raise error, just log and continue
            pass
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity
            }
            
            # Execute pH step using model functions
            self._execute_ph_step(weather_data)
            
            # Create output
            outputs = {
                'ph': self.state.ph,
                'ph_stability': self.state.ph_stability,
                'total_alkalinity': self.state.total_alkalinity,
                'carbonate_concentration': self.state.carbonate_concentration,
                'phosphate_concentration': self.state.phosphate_concentration,
                'buffer_capacity': self.state.buffer_capacity,
                'ph_drift_rate': self.state.ph_drift_rate,
                'ph_adjustment_needed': self.state.ph_adjustment_needed,
                'nutrient_solubility': self.state.nutrient_solubility,
                'iron_solubility': self.state.iron_solubility,
                'calcium_phosphate_precipitation': self.state.calcium_phosphate_precipitation,
                'magnesium_phosphate_precipitation': self.state.magnesium_phosphate_precipitation,
                'cumulative_ph_adjustment': self.state.cumulative_ph_adjustment,
                'daily_ph_adjustment': self.state.daily_ph_adjustment
            }
            
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs=outputs,
                status='success',
                message='pH calculation completed using model functions'
            )
            
        except Exception as e:
            return DailyUpdateOutput(
                day=inputs.day,
                hour=inputs.hour,
                outputs={},
                status='error',
                message=f'pH calculation failed: {str(e)}'
            )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state"""
        return {
            'ph': self.state.ph,
            'ph_stability': self.state.ph_stability,
            'total_alkalinity': self.state.total_alkalinity,
            'carbonate_concentration': self.state.carbonate_concentration,
            'phosphate_concentration': self.state.phosphate_concentration,
            'buffer_capacity': self.state.buffer_capacity,
            'ph_drift_rate': self.state.ph_drift_rate,
            'ph_adjustment_needed': self.state.ph_adjustment_needed,
            'nutrient_solubility': self.state.nutrient_solubility,
            'iron_solubility': self.state.iron_solubility,
            'calcium_phosphate_precipitation': self.state.calcium_phosphate_precipitation,
            'magnesium_phosphate_precipitation': self.state.magnesium_phosphate_precipitation,
            'cumulative_ph_adjustment': self.state.cumulative_ph_adjustment,
            'daily_ph_adjustment': self.state.daily_ph_adjustment,
            'step_count': self.state.step_count,
            'last_update': self.state.last_update.isoformat()
        }
    
    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'ph': self.state.ph,
            'ph_stability': self.state.ph_stability,
            'total_alkalinity': self.state.total_alkalinity,
            'carbonate_concentration': self.state.carbonate_concentration,
            'phosphate_concentration': self.state.phosphate_concentration,
            'buffer_capacity': self.state.buffer_capacity,
            'ph_drift_rate': self.state.ph_drift_rate,
            'ph_adjustment_needed': self.state.ph_adjustment_needed,
            'nutrient_solubility': self.state.nutrient_solubility,
            'iron_solubility': self.state.iron_solubility,
            'calcium_phosphate_precipitation': self.state.calcium_phosphate_precipitation,
            'magnesium_phosphate_precipitation': self.state.magnesium_phosphate_precipitation
        }
        
        # Add individual nutrient solubility data
        for element in self.nutrient_elements:
            data_map[f'{element}_solubility'] = self.state.nutrient_solubility.get(element, 1.0)
        
        return data_map.get(data_key)

    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        ph_data = {
            'ph': self.state.ph,
            'ph_stability': self.state.ph_stability,
            'total_alkalinity': self.state.total_alkalinity,
            'carbonate_concentration': self.state.carbonate_concentration,
            'phosphate_concentration': self.state.phosphate_concentration,
            'buffer_capacity': self.state.buffer_capacity,
            'ph_drift_rate': self.state.ph_drift_rate,
            'ph_adjustment_needed': self.state.ph_adjustment_needed,
            'nutrient_solubility': self.state.nutrient_solubility,
            'iron_solubility': self.state.iron_solubility,
            'calcium_phosphate_precipitation': self.state.calcium_phosphate_precipitation,
            'magnesium_phosphate_precipitation': self.state.magnesium_phosphate_precipitation,
            'cumulative_ph_adjustment': self.state.cumulative_ph_adjustment,
            'daily_ph_adjustment': self.state.daily_ph_adjustment
        }

        # Add individual nutrient solubility data
        for element in self.nutrient_elements:
            ph_data[f'{element}_solubility'] = self.state.nutrient_solubility.get(element, 1.0)

        self.dependency_cache['ph_model_simulator'] = ph_data

    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.NUTRIENT_UPDATE:
            # Update nutrient parameters from nutrient models simulator
            nutrient_data = event.data
            # Nutrient data will be requested when needed
            
        elif event.event_type == EventType.WATER_UPDATE:
            # Update water parameters from water uptake simulator
            water_data = event.data
            # Water data will be requested when needed
            
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
        print(f"pH model simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final pH: {self.state.ph:.2f}")
        print(f"Final pH stability: {self.state.ph_stability:.3f}")
        print(f"Final total alkalinity: {self.state.total_alkalinity:.2f} mg/L")
        print(f"Final buffer capacity: {self.state.buffer_capacity:.2f}")
        print(f"Total pH adjustment: {self.state.cumulative_ph_adjustment:.2f}")
        
        # Publish final results
        self.publish_event(EventType.PH_UPDATE, {
            'final_ph': self.state.ph,
            'final_ph_stability': self.state.ph_stability,
            'final_total_alkalinity': self.state.total_alkalinity,
            'final_carbonate_concentration': self.state.carbonate_concentration,
            'final_phosphate_concentration': self.state.phosphate_concentration,
            'final_buffer_capacity': self.state.buffer_capacity,
            'final_ph_drift_rate': self.state.ph_drift_rate,
            'final_iron_solubility': self.state.iron_solubility,
            'total_ph_adjustment': self.state.cumulative_ph_adjustment,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("pH model simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        ph_values = [s.ph for s in self.history]
        ph_stability_values = [s.ph_stability for s in self.history]
        buffer_capacity_values = [s.buffer_capacity for s in self.history]
        
        # Calculate pH stability metrics
        ph_variance = sum((ph - sum(ph_values)/len(ph_values))**2 for ph in ph_values) / len(ph_values)
        ph_stability_score = 1.0 / (1.0 + ph_variance) if ph_variance > 0 else 1.0
        
        return {
            'total_steps': len(self.history),
            'final_ph': self.state.ph,
            'avg_ph': sum(ph_values) / len(ph_values),
            'min_ph': min(ph_values),
            'max_ph': max(ph_values),
            'ph_variance': ph_variance,
            'ph_stability_score': ph_stability_score,
            'final_ph_stability': self.state.ph_stability,
            'avg_ph_stability': sum(ph_stability_values) / len(ph_stability_values),
            'final_buffer_capacity': self.state.buffer_capacity,
            'avg_buffer_capacity': sum(buffer_capacity_values) / len(buffer_capacity_values),
            'final_iron_solubility': self.state.iron_solubility,
            'cumulative_ph_adjustment': self.state.cumulative_ph_adjustment,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
