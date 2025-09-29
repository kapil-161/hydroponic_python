"""
Simulation Orchestrator

Central coordinator for the distributed hydroponic simulation system.
Manages timing, synchronization, and coordination between all 17 simulators.
"""

import asyncio
import threading
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd

from .communication_bus import (
    SimulationMessageBus, SimulationEvent, EventType, BaseSimulator,
    message_bus
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class SimulationConfig:
    """Configuration for the distributed simulation"""
    total_days: int = 120  # Maximum days (safety limit), simulation stops at harvest maturity
    steps_per_day: int = 24  # hourly steps
    step_duration_seconds: float = 0.1  # Real-time duration of each step
    start_day: int = 1
    start_hour: int = 0
    enable_real_time: bool = False
    synchronization_mode: str = "sequential"  # sequential, parallel, event_driven
    data_collection_interval: int = 1  # Collect data every N steps
    max_concurrent_simulators: int = 17


class SimulationOrchestrator(BaseSimulator):
    """Central orchestrator for distributed hydroponic simulation"""
    
    def __init__(self, config: SimulationConfig = None):
        super().__init__("orchestrator")
        self.config = config or SimulationConfig()
        self.simulators: Dict[str, BaseSimulator] = {}
        self.simulation_data: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.current_step = 0
        self.current_day = self.config.start_day
        self.current_hour = self.config.start_hour
        self.is_running = False
        self.is_paused = False
        self.error_count = 0
        self.max_errors = 100  # Allow more errors during initial dependency building
        
        # Performance tracking
        self.step_times: List[float] = []
        self.simulator_performance: Dict[str, List[float]] = {}
        
        # Data collection
        self.collected_data: Dict[str, List[Dict[str, Any]]] = {}
        
    def register_simulator(self, simulator: BaseSimulator):
        """Register a simulator with the orchestrator"""
        self.simulators[simulator.simulator_id] = simulator
        self.simulator_performance[simulator.simulator_id] = []
        print(f"Orchestrator: Registered {simulator.simulator_id}")
    
    def unregister_simulator(self, simulator_id: str):
        """Unregister a simulator from the orchestrator"""
        if simulator_id in self.simulators:
            del self.simulators[simulator_id]
            if simulator_id in self.simulator_performance:
                del self.simulator_performance[simulator_id]
            print(f"Orchestrator: Unregistered {simulator_id}")
    
    def start_simulation(self, weather_data: pd.DataFrame = None):
        """Start the distributed simulation"""
        if self.is_running:
            print("Simulation is already running")
            return
        
        print(f"Starting distributed simulation with {len(self.simulators)} simulators")
        self.start_time = datetime.now()
        self.is_running = True
        self.is_paused = False
        self.current_step = 0
        self.error_count = 0
        
        # Initialize data collection
        self.collected_data = {sim_id: [] for sim_id in self.simulators.keys()}
        
        # Start message bus
        self.message_bus.start()
        
        # Send simulation start event
        self.publish_event(
            EventType.SIMULATION_START,
            data={
                'total_days': self.config.total_days,
                'steps_per_day': self.config.steps_per_day,
                'weather_data': weather_data.to_dict('records') if weather_data is not None else None
            }
        )
        
        # Start simulation loop
        self._run_simulation_loop(weather_data)
    
    def _run_simulation_loop(self, weather_data: pd.DataFrame = None):
        """Main simulation loop - stops at harvest maturity"""
        try:
            total_steps = self.config.total_days * self.config.steps_per_day
            harvest_maturity_reached = False
            
            for day in range(self.config.start_day, self.config.total_days + 1):
                if not self.is_running or harvest_maturity_reached:
                    break
                
                self.current_day = day
                
                # Get weather data for this day
                daily_weather = None
                if weather_data is not None and not weather_data.empty:
                    if day <= len(weather_data):
                        daily_weather = weather_data.iloc[day - 1].to_dict()
                
                for hour in range(self.config.start_hour, self.config.steps_per_day):
                    if not self.is_running:
                        break
                    
                    self.current_hour = hour
                    self.current_step += 1
                    
                    step_start_time = time.time()
                    
                    # Send simulation step event
                    self.publish_event(
                        EventType.SIMULATION_STEP,
                        data={
                            'step': self.current_step,
                            'day': self.current_day,
                            'hour': self.current_hour,
                            'weather_data': daily_weather,
                            'progress': (self.current_step / total_steps) * 100
                        }
                    )
                    
                    # Execute simulation step with dependency resolution
                    self._execute_dependency_ordered_step(daily_weather)
                    
                    # Check for harvest maturity
                    harvest_maturity_reached = self._check_harvest_maturity()
                    if harvest_maturity_reached:
                        print(f"Harvest maturity reached on day {self.current_day}, hour {self.current_hour}")
                        break
                    
                    # Collect data if needed
                    if self.current_step % self.config.data_collection_interval == 0:
                        self._collect_step_data()
                    
                    # Track performance
                    step_duration = time.time() - step_start_time
                    self.step_times.append(step_duration)
                    
                    # Real-time delay if enabled
                    if self.config.enable_real_time:
                        sleep_time = max(0, self.config.step_duration_seconds - step_duration)
                        time.sleep(sleep_time)
                    
                    # Progress reporting
                    if self.current_step % 24 == 0:  # Every day
                        progress = (self.current_step / total_steps) * 100
                        print(f"Day {self.current_day}: {progress:.1f}% complete")
            
            # End simulation
            self.end_time = datetime.now()
            self.is_running = False
            
            self.publish_event(EventType.SIMULATION_END, data={
                'total_steps': self.current_step,
                'total_days': self.current_day,
                'duration': (self.end_time - self.start_time).total_seconds()
            })
            
            print(f"Simulation completed: {self.current_step} steps in {self.end_time - self.start_time}")
            
        except Exception as e:
            print(f"Simulation error: {e}")
            self.error_count += 1
            if self.error_count >= self.max_errors:
                print("Maximum errors reached, terminating simulation")
                self.terminate_simulation()
    
    def _execute_dependency_ordered_step(self, weather_data: Dict[str, Any]):
        """Execute simulators in dependency order to avoid circular dependencies"""
        # Define execution order based on dependencies - PROPER SCIENTIFIC ORDER
        # Level 1: Independent simulators that can run with just weather data
        execution_order = [
            'genetic_parameters_simulator',
            'phenology_simulator',
            'environmental_control_simulator',
            'stress_models_simulator',
            'photosynthesis_simulator',
            'respiration_simulator',
            'water_uptake_simulator',
            'ph_model_simulator',
            'root_zone_temperature_simulator',
            'biomass_allocation_simulator',
            'root_system_simulator',
            'nutrient_models_simulator',
            'nitrogen_balance_simulator',
            'leaf_development_simulator',
            'canopy_architecture_simulator',
            'senescence_simulator'
        ]
        
        # Execute simulators in dependency order
        for simulator_id in execution_order:
            if simulator_id in self.simulators:
                try:
                    simulator = self.simulators[simulator_id]
                    
                    # Create simulation step data
                    step_data = {
                        'day': self.current_day,
                        'hour': self.current_hour,
                        'weather_data': weather_data,
                        'step': self.current_step
                    }
                    
                    # Execute simulator step
                    simulator.on_simulation_step(step_data)
                    
                    # Give time for data to be published to message bus
                    time.sleep(0.01)  # Increased delay to ensure data propagation
                    
                    # Force message bus to process any pending events
                    self.message_bus._process_pending_events()
                    
                except Exception as e:
                    print(f"Error in dependency-ordered execution of {simulator_id}: {e}")
                    self.error_count += 1
    
    def _execute_sequential_step(self):
        """Execute simulation step sequentially"""
        for simulator_id, simulator in self.simulators.items():
            try:
                step_start = time.time()
                
                # Create daily update input
                daily_input = DailyUpdateInput(
                    day=self.current_day,
                    hour=self.current_hour,
                    temperature=25.0,  # Default values - should come from weather data
                    humidity=60.0,
                    light_intensity=500.0,
                    co2_concentration=400.0,
                    nutrient_concentration={'N': 100, 'P': 50, 'K': 150}
                )
                
                # Execute simulator step
                if hasattr(simulator, 'daily_update'):
                    output = simulator.daily_update(daily_input)
                    self._process_simulator_output(simulator_id, output)
                
                # Track performance
                step_duration = time.time() - step_start
                self.simulator_performance[simulator_id].append(step_duration)
                
            except Exception as e:
                print(f"Error in simulator {simulator_id}: {e}")
                self.error_count += 1
    
    def _execute_parallel_step(self):
        """Execute simulation step in parallel"""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_concurrent_simulators) as executor:
            futures = {}
            
            for simulator_id, simulator in self.simulators.items():
                future = executor.submit(self._execute_simulator_step, simulator_id, simulator)
                futures[future] = simulator_id
            
            # Wait for all simulators to complete
            for future in concurrent.futures.as_completed(futures):
                simulator_id = futures[future]
                try:
                    output = future.result()
                    if output:
                        self._process_simulator_output(simulator_id, output)
                except Exception as e:
                    print(f"Error in parallel execution of {simulator_id}: {e}")
                    self.error_count += 1
    
    def _execute_event_driven_step(self):
        """Execute simulation step using event-driven approach"""
        # In event-driven mode, simulators respond to events asynchronously
        # The orchestrator just publishes the step event and waits for responses
        pass
    
    def _execute_simulator_step(self, simulator_id: str, simulator: BaseSimulator):
        """Execute a single simulator step"""
        try:
            daily_input = DailyUpdateInput(
                day=self.current_day,
                hour=self.current_hour,
                temperature=25.0,
                humidity=60.0,
                light_intensity=500.0,
                co2_concentration=400.0,
                nutrient_concentration={'N': 100, 'P': 50, 'K': 150}
            )
            
            if hasattr(simulator, 'daily_update'):
                return simulator.daily_update(daily_input)
            
        except Exception as e:
            print(f"Error executing step for {simulator_id}: {e}")
            return None
    
    def _process_simulator_output(self, simulator_id: str, output: DailyUpdateOutput):
        """Process output from a simulator"""
        if output and hasattr(output, 'outputs'):
            # Store simulator-specific data
            if simulator_id not in self.collected_data:
                self.collected_data[simulator_id] = []
            
            self.collected_data[simulator_id].append({
                'step': self.current_step,
                'day': self.current_day,
                'hour': self.current_hour,
                'timestamp': datetime.now(),
                'data': output.outputs
            })
    
    def _collect_step_data(self):
        """Collect data from all simulators for current step"""
        step_data = {
            'step': self.current_step,
            'day': self.current_day,
            'hour': self.current_hour,
            'timestamp': datetime.now(),
            'simulators': {}
        }
        
        for simulator_id, simulator in self.simulators.items():
            try:
                if hasattr(simulator, 'get_current_state'):
                    state = simulator.get_current_state()
                    step_data['simulators'][simulator_id] = state
            except Exception as e:
                print(f"Error collecting data from {simulator_id}: {e}")
        
        self.simulation_data.append(step_data)
    
    def pause_simulation(self):
        """Pause the simulation"""
        self.is_paused = True
        self.publish_event(EventType.PAUSE_SIMULATION)
        print("Simulation paused")
    
    def resume_simulation(self):
        """Resume the simulation"""
        self.is_paused = False
        self.publish_event(EventType.RESUME_SIMULATION)
        print("Simulation resumed")
    
    def terminate_simulation(self):
        """Terminate the simulation"""
        self.is_running = False
        self.publish_event(EventType.TERMINATE_SIMULATION)
        print("Simulation terminated")
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status"""
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'current_step': self.current_step,
            'current_day': self.current_day,
            'current_hour': self.current_hour,
            'total_simulators': len(self.simulators),
            'registered_simulators': list(self.simulators.keys()),
            'error_count': self.error_count,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'avg_step_time': sum(self.step_times) / len(self.step_times) if self.step_times else 0,
            'data_points_collected': len(self.simulation_data)
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all simulators"""
        metrics = {}
        
        # Overall performance
        if self.step_times:
            metrics['overall'] = {
                'avg_step_time': sum(self.step_times) / len(self.step_times),
                'min_step_time': min(self.step_times),
                'max_step_time': max(self.step_times),
                'total_steps': len(self.step_times)
            }
        
        # Per-simulator performance
        for simulator_id, times in self.simulator_performance.items():
            if times:
                metrics[simulator_id] = {
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'total_calls': len(times)
                }
        
        return metrics
    
    def export_results(self, output_path: str = None) -> str:
        """Export simulation results to CSV"""
        if not self.simulation_data:
            print("No simulation data to export")
            return ""
        
        if output_path is None:
            output_path = f"output/distributed_simulation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Flatten simulation data
        flattened_data = []
        for step_data in self.simulation_data:
            base_record = {
                'step': step_data['step'],
                'day': step_data['day'],
                'hour': step_data['hour'],
                'timestamp': step_data['timestamp']
            }
            
            # Add simulator-specific data
            for simulator_id, simulator_data in step_data.get('simulators', {}).items():
                for key, value in simulator_data.items():
                    base_record[f"{simulator_id}_{key}"] = value
            
            flattened_data.append(base_record)
        
        # Create DataFrame and save
        df = pd.DataFrame(flattened_data)
        df.to_csv(output_path, index=False)
        
        print(f"Results exported to: {output_path}")
        return output_path
    
    def _check_harvest_maturity(self) -> bool:
        """Check if harvest maturity has been reached by querying the phenology simulator"""
        try:
            # Get the phenology simulator from registered simulators
            phenology_simulator = None
            for simulator_id, simulator in self.simulators.items():
                if 'phenology' in simulator_id.lower():
                    phenology_simulator = simulator
                    break
            
            if phenology_simulator is None:
                print("Warning: Phenology simulator not found, cannot check harvest maturity")
                return False
            
            # Get current growth stage from phenology simulator
            current_stage = phenology_simulator.get_data('current_growth_stage')
            
            if current_stage is None:
                print("Warning: Could not get current growth stage from phenology simulator")
                return False
            
            # Check if harvest maturity has been reached
            from models.phenology_model import LettuceGrowthStage
            harvest_maturity_reached = (current_stage == LettuceGrowthStage.HARVEST_MATURITY.value or 
                                      str(current_stage) == "LettuceGrowthStage.HARVEST_MATURITY")
            
            if harvest_maturity_reached:
                print(f"Harvest maturity reached! Current stage: {current_stage}")
            
            return harvest_maturity_reached
            
        except Exception as e:
            print(f"Error checking harvest maturity: {e}")
            return False
    
    def cleanup(self):
        """Cleanup orchestrator resources"""
        self.terminate_simulation()
        self.message_bus.stop()
        super().cleanup()
