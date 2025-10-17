"""
Simulation Orchestrator

Central coordinator for the distributed hydroponic simulation system.
Manages timing, synchronization, and coordination between all 16 simulators.
"""

import asyncio
import threading
import time
import math
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd

from simulations.communication_bus import (
    SimulationMessageBus, SimulationEvent, EventType, BaseSimulator,
    message_bus
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class SimulationConfig:
    """Configuration for the distributed simulation - per Rules.md: no hardcoded values"""
    total_days: int
    steps_per_day: int
    step_duration_seconds: float
    start_day: int
    start_hour: int
    enable_real_time: bool
    synchronization_mode: str  # sequential, parallel, event_driven
    data_collection_interval: int  # Collect data every N steps
    max_concurrent_simulators: int
    max_errors: int  # Maximum errors allowed before termination
    progress_report_interval: int  # Steps between progress reports
    initialization_wait_time: float  # Seconds to wait for initialization
    event_processing_wait_time: float  # Seconds between event processing
    initialization_cycles: int  # Number of initialization event cycles

    @classmethod
    def from_csv_parameters(cls, parameters: Dict[str, Any]) -> 'SimulationConfig':
        """Create configuration from CSV parameters - per Rules.md: all from CSV"""
        required_params = [
            'total_days', 'steps_per_day', 'step_duration_seconds', 'start_day', 'start_hour',
            'enable_real_time', 'synchronization_mode', 'data_collection_interval', 'max_concurrent_simulators', 'max_errors',
            'progress_report_interval', 'initialization_wait_time', 'event_processing_wait_time', 'initialization_cycles'
        ]

        for param in required_params:
            if param not in parameters:
                raise ValueError(f"Required simulation configuration parameter '{param}' missing from CSV parameters")

        return cls(
            total_days=int(parameters['total_days']),
            steps_per_day=int(parameters['steps_per_day']),
            step_duration_seconds=float(parameters['step_duration_seconds']),
            start_day=int(parameters['start_day']),
            start_hour=int(parameters['start_hour']),
            enable_real_time=bool(parameters['enable_real_time']),
            synchronization_mode=str(parameters['synchronization_mode']),
            data_collection_interval=int(parameters['data_collection_interval']),
            max_concurrent_simulators=int(parameters['max_concurrent_simulators']),
            max_errors=int(parameters['max_errors']),
            progress_report_interval=int(parameters['progress_report_interval']),
            initialization_wait_time=float(parameters['initialization_wait_time']),
            event_processing_wait_time=float(parameters['event_processing_wait_time']),
            initialization_cycles=int(parameters['initialization_cycles'])
        )


class SimulationOrchestrator(BaseSimulator):
    """Central orchestrator for distributed hydroponic simulation"""
    
    def __init__(self, config: SimulationConfig):
        super().__init__("orchestrator")
        # Per Rules.md: no default values, configuration must be provided from CSV
        if config is None:
            raise ValueError("SimulationConfig must be provided from CSV parameters - no defaults allowed per Rules.md")
        self.config = config
        self.simulators: Dict[str, BaseSimulator] = {}
        self.simulation_data: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Shared data cache for cross-simulator communication
        self.shared_data_cache: Dict[str, Dict[str, Any]] = {}
        self.current_step = 0
        self.current_day = self.config.start_day
        self.current_hour = self.config.start_hour
        self.is_running = False
        self.is_paused = False
        self.error_count = 0
        # max_errors comes from configuration parameters per Rules.md
        self.max_errors = config.max_errors
        
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
    
    def start_simulation(self, weather_data: pd.DataFrame = None, initial_state: Dict[str, Any] = None):
        """Start the distributed simulation with initial state from CSV"""
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

        # Send simulation start event with initial state from CSV
        self.publish_event(
            EventType.SIMULATION_START,
            data={
                'total_days': self.config.total_days,
                'steps_per_day': self.config.steps_per_day,
                'weather_data': weather_data.to_dict('records') if weather_data is not None else None,
                'initial_state': initial_state.get('initial_state', {}) if initial_state else {},
                'system_config': initial_state.get('system_config', {}) if initial_state else {}
            }
        )

        # Process all pending events to ensure all subscriptions are updated
        self.message_bus._process_pending_events()

        # Collect initial data from all simulators into shared cache
        self._collect_simulator_data_to_shared_cache()

        # Inject system_config from initials.csv into shared cache for simulators that depend on it
        if initial_state and 'system_config' in initial_state:
            system_config_seed = dict(initial_state['system_config'])
            # Provide daily_growth_rate from initials.csv strictly (no defaults)
            if 'daily_growth_rate' not in system_config_seed:
                # Look for relative_growth_rate under initial_state block
                try:
                    rel_gr = initial_state.get('initial_state', {}).get('relative_growth_rate')
                except Exception:
                    rel_gr = None
                if rel_gr is not None:
                    system_config_seed['daily_growth_rate'] = rel_gr
            self.shared_data_cache['system_config'] = system_config_seed


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

                # Start at configured start_hour only on first day, then 0 for subsequent days
                start_hour = self.config.start_hour if day == self.config.start_day else 0
                for hour in range(start_hour, self.config.steps_per_day):
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

                    # Execute simulation step based on synchronization mode
                    if self.config.synchronization_mode == "parallel":
                        self._execute_parallel_step(daily_weather)
                    else:
                        self._execute_dependency_ordered_step(daily_weather)

                    # Check for harvest maturity (adjusted for extended simulation)
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

                    # Skip real-time delays for faster simulation

                    # Skip progress reporting for faster simulation
            
            # Ensure final state is captured even if we broke early for harvest maturity
            # Refresh shared cache from simulators and collect a final step snapshot
            try:
                self._collect_simulator_data_to_shared_cache()
                self._collect_step_data()
            except Exception:
                pass

            # End simulation
            self.end_time = datetime.now()
            self.is_running = False
            
            self.publish_event(EventType.SIMULATION_END, data={
                'total_steps': self.current_step,
                'total_days': self.current_day,
                'duration': (self.end_time - self.start_time).total_seconds()
            })
            
            print(f"Simulation completed: {self.current_step} steps in {self.end_time - self.start_time}")
            
        except ValueError as e:
            # Configuration errors should halt simulation immediately
            print(f"Configuration error: {e}")
            self.terminate_simulation()
            raise
        except KeyError as e:
            # Missing required data should halt simulation
            print(f"Missing required data: {e}")
            self.terminate_simulation()
            raise
        except Exception as e:
            # Other exceptions can be logged and counted
            print(f"Simulation error: {e}")
            self.error_count += 1
            if self.error_count >= self.max_errors:
                print("Maximum errors reached, terminating simulation")
                self.terminate_simulation()

    def _collect_simulator_data_to_shared_cache(self):
        """Collect data from all simulators into shared cache for cross-simulator access"""
        for simulator_id, simulator in self.simulators.items():
            try:
                # Use publish_state_data() method if available to get correctly-keyed data
                if hasattr(simulator, 'publish_state_data') and callable(simulator.publish_state_data):
                    # Call publish_state_data() to get properly formatted dict
                    simulator.publish_state_data()

                    # Then retrieve from dependency_cache (where publish_state_data stores it)
                    if hasattr(simulator, 'dependency_cache') and simulator.simulator_id in simulator.dependency_cache:
                        state_dict = simulator.dependency_cache[simulator.simulator_id]
                        self.shared_data_cache[simulator_id] = state_dict
                    else:
                        # Fallback: Convert state to dict directly
                        state_dict = {}
                        for attr in dir(simulator.state):
                            if not attr.startswith('_'):
                                try:
                                    value = getattr(simulator.state, attr, None)
                                    if value is not None and not callable(value):
                                        state_dict[attr] = value
                                except AttributeError:
                                    # Skip attributes that can't be accessed
                                    continue
                        self.shared_data_cache[simulator_id] = state_dict
            except Exception as e:
                # Make collection non-fatal - simulator will work with partial data
                self.shared_data_cache[simulator_id] = {}

    def _execute_dependency_ordered_step(self, weather_data: Dict[str, Any]):
        """
        Execute simulators in dependency order to handle circular dependencies.

        IMPORTANT: This execution order is INTENTIONALLY HARDCODED to break circular
        dependencies in the biological feedback loops. Analysis revealed 31 circular
        dependencies representing real biological feedbacks (e.g., biomass → photosynthesis
        → canopy → biomass). Pure topological sort is impossible.

        This order creates one-step data lag, which is scientifically valid for daily timesteps.
        See CRITICAL_ARCHITECTURE_ANALYSIS.md for detailed explanation.

        Cycle-Breaking Strategy:
        - phenology before genetic_parameters (breaks phenology ↔ genetic cycle)
        - root_system before water_uptake (breaks root ↔ water cycle)
        - biomass before canopy (breaks biomass ↔ photosynthesis ↔ canopy cycle)
        """
        execution_order = [
            # Level 1: Independent simulators (weather data only or initial state from CSV)
            'phenology_simulator',
            'genetic_parameters_simulator',
            'root_system_simulator',

            # Level 2: Water, nutrients, and environmental before stress calculation
            'water_uptake_simulator',
            'nutrient_models_simulator',
            'leaf_development_simulator',

            # Level 3: Stress models (needs water, nutrients data)
            'stress_models',

            # Level 4: Canopy and biomass (needs stress data)
            'canopy_architecture_simulator',

            # Level 5: Photosynthesis and respiration (need canopy and stress)
            'photosynthesis_simulator',
            'respiration_simulator',

            # Level 6: Biomass allocation (needs photosynthesis and respiration)
            'biomass_allocation_simulator',

            # Level 7: Nitrogen balance
            'nitrogen_balance_simulator'
        ]
        
        # Execute simulators in dependency order
        for simulator_id in execution_order:
            if simulator_id in self.simulators:
                try:
                    simulator = self.simulators[simulator_id]
                    
                    # Create simulation step data with shared cache
                    step_data = {
                        'day': self.current_day,
                        'hour': self.current_hour,
                        'weather_data': weather_data,
                        'step': self.current_step,
                        'shared_data': self.shared_data_cache,  # Provide shared cache
                        'system_config': self.shared_data_cache.get('system_config', {})
                    }

                    # Inject shared data into simulator's dependency_cache before execution
                    if hasattr(simulator, 'dependency_cache'):
                        for dep_simulator_id, dep_data in self.shared_data_cache.items():
                            if dep_simulator_id != simulator_id:  # Don't inject self
                                simulator.dependency_cache[dep_simulator_id] = dep_data
                                # Update cache timestamp for freshness tracking
                                if hasattr(simulator, 'cache_timestamp'):
                                    simulator.cache_timestamp[dep_simulator_id] = datetime.now()

                    # Execute simulator step
                    simulator.on_simulation_step(step_data)

                    # Update shared cache after execution using publish_state_data()
                    if hasattr(simulator, 'publish_state_data') and callable(simulator.publish_state_data):
                        simulator.publish_state_data()
                        # Retrieve from dependency_cache where publish_state_data stores it
                        if hasattr(simulator, 'dependency_cache') and simulator.simulator_id in simulator.dependency_cache:
                            self.shared_data_cache[simulator_id] = simulator.dependency_cache[simulator.simulator_id]
                    elif hasattr(simulator, 'state'):
                        # Fallback: Convert state to dict directly
                        state_dict = {}
                        for attr in dir(simulator.state):
                            if not attr.startswith('_'):
                                value = getattr(simulator.state, attr, None)
                                if value is not None and not callable(value):
                                    state_dict[attr] = value
                        self.shared_data_cache[simulator_id] = state_dict
                    
                    # Process message bus events immediately
                    self.message_bus._process_pending_events()
                    
                except Exception as e:
                    self.error_count += 1
            
          
    
    def _execute_sequential_step(self, weather_data: Dict[str, Any] = None):
        """Execute simulation step sequentially"""
        # Per Rules.md: no hardcoded values, all data must come from weather data or CSV
        if weather_data is None:
            raise ValueError("Weather data required for simulation step - no hardcoded values allowed per Rules.md")

        for simulator_id, simulator in self.simulators.items():
            try:
                step_start = time.time()

                # Create daily update input from weather data - per Rules.md: no hardcoded values
                temperature = weather_data.get('temperature')
                humidity = weather_data.get('humidity')

                # Calculate VPD if not provided in weather data
                vpd = weather_data.get('vpd')
                if vpd is None and temperature is not None and humidity is not None:
                    from src.utils.core_utils import calculate_vpd
                    vpd = calculate_vpd(temperature, humidity)

                daily_input = DailyUpdateInput(
                    day=self.current_day,
                    date=datetime.now(),
                    temperature=temperature,
                    humidity=humidity,
                    solar_radiation=weather_data.get('solar_radiation'),
                    vpd=vpd,
                    co2_concentration=weather_data.get('co2_concentration'),
                    environmental_conditions=weather_data.copy(),
                    plant_state={},
                    system_state={}
                )

                # Validate required weather data
                if daily_input.temperature is None:
                    raise ValueError("Temperature data required from weather data")
                if daily_input.humidity is None:
                    raise ValueError("Humidity data required from weather data")
                if daily_input.solar_radiation is None:
                    raise ValueError("Solar radiation data required from weather data")
                if daily_input.vpd is None:
                    raise ValueError("VPD data required (calculated from temperature and humidity) from weather data")
                if daily_input.co2_concentration is None:
                    raise ValueError("CO2 concentration data required from weather data")
                
                # Execute simulator step
                if hasattr(simulator, 'daily_update'):
                    output = simulator.daily_update(daily_input)
                    self._process_simulator_output(simulator_id, output)
                
                # Track performance
                step_duration = time.time() - step_start
                self.simulator_performance[simulator_id].append(step_duration)
                
            except Exception as e:
                self.error_count += 1
    
    def _execute_parallel_step(self, weather_data: Dict[str, Any] = None):
        """Execute simulation step in parallel"""
        import concurrent.futures

        # Per Rules.md: no hardcoded values, weather data required
        if weather_data is None:
            raise ValueError("Weather data required for parallel simulation step - no hardcoded values allowed per Rules.md")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_concurrent_simulators) as executor:
            futures = {}

            for simulator_id, simulator in self.simulators.items():
                future = executor.submit(self._execute_simulator_step, simulator_id, simulator, weather_data)
                futures[future] = simulator_id
            
            # Wait for all simulators to complete
            for future in concurrent.futures.as_completed(futures):
                simulator_id = futures[future]
                try:
                    output = future.result()
                    if output:
                        self._process_simulator_output(simulator_id, output)
                except Exception as e:
                    self.error_count += 1
    
    def _execute_event_driven_step(self):
        """Execute simulation step using event-driven approach"""
        # In event-driven mode, simulators respond to events asynchronously
        # The orchestrator just publishes the step event and waits for responses
        pass
    
    def _execute_simulator_step(self, simulator_id: str, simulator: BaseSimulator, weather_data: Dict[str, Any] = None):
        """Execute a single simulator step"""
        try:
            # Per Rules.md: no hardcoded values, all data must come from weather data
            if weather_data is None:
                raise ValueError("Weather data required for simulator step - no hardcoded values allowed per Rules.md")

            # Per Rules.md: calculate VPD from temperature and humidity if not provided
            temperature = weather_data.get('temperature')
            humidity = weather_data.get('humidity')

            # Calculate VPD if not provided in weather data
            vpd = weather_data.get('vpd')
            if vpd is None and temperature is not None and humidity is not None:
                from src.utils.core_utils import calculate_vpd
                vpd = calculate_vpd(temperature, humidity)

            daily_input = DailyUpdateInput(
                day=self.current_day,
                date=datetime.now(),
                temperature=temperature,
                humidity=humidity,
                solar_radiation=weather_data.get('solar_radiation'),
                vpd=vpd,
                co2_concentration=weather_data.get('co2_concentration'),
                environmental_conditions=weather_data.copy(),
                plant_state={},
                system_state={}
            )

            # Validate required weather data
            if daily_input.temperature is None:
                raise ValueError(f"Temperature data required from weather data for {simulator_id}")
            if daily_input.humidity is None:
                raise ValueError(f"Humidity data required from weather data for {simulator_id}")
            if daily_input.solar_radiation is None:
                raise ValueError(f"Solar radiation data required from weather data for {simulator_id}")
            if daily_input.vpd is None:
                raise ValueError(f"VPD data required (calculated from temperature and humidity) from weather data for {simulator_id}")
            if daily_input.co2_concentration is None:
                raise ValueError(f"CO2 concentration data required from weather data for {simulator_id}")
            
            if hasattr(simulator, 'daily_update'):
                return simulator.daily_update(daily_input)
            
        except Exception as e:
            return None
    
    def _process_simulator_output(self, simulator_id: str, output: DailyUpdateOutput):
        """Process output from a simulator"""
        if output and hasattr(output, 'primary_results'):
            # Store simulator-specific data
            if simulator_id not in self.collected_data:
                self.collected_data[simulator_id] = []

            # Combine primary and secondary results for storage
            all_results = {}
            all_results.update(output.primary_results)
            all_results.update(output.secondary_results)

            self.collected_data[simulator_id].append({
                'step': self.current_step,
                'day': self.current_day,
                'hour': self.current_hour,
                'timestamp': datetime.now(),
                'success': output.success,
                'model_name': output.model_name,
                'data': all_results
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
                pass
        
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
        """Export simulation results to organized CSV files"""
        if not self.simulation_data:
            print("No simulation data to export")
            return ""

        if output_path is None:
            output_path = "output/simulation_results.csv"

        # Create output directory if it doesn't exist
        import os
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Export combined results
        flattened_data = []
        for step_data in self.simulation_data:
            base_record = {
                'step': step_data['step'],
                'day': step_data['day'],
                'hour': step_data['hour']
            }

            # Add simulator-specific data
            for simulator_id, simulator_data in step_data.get('simulators', {}).items():
                for key, value in simulator_data.items():
                    # Convert lists/dicts to string to avoid formatting errors
                    if isinstance(value, (list, dict)):
                        base_record[f"{simulator_id}_{key}"] = str(value)
                    else:
                        base_record[f"{simulator_id}_{key}"] = value

            flattened_data.append(base_record)

        # Create combined DataFrame and save
        df = pd.DataFrame(flattened_data)
        # Round numeric columns to 4 decimal places
        df = df.round(4)
        df.to_csv(output_path, index=False, float_format='%.4f')
        print(f"Combined results exported to: {output_path}")

        # Export separate CSV files for each simulator
        base_cols = ['step', 'day', 'hour']
        exported_files = []

        for simulator_id in self.simulators.keys():
            # Get columns for this simulator
            sim_cols = [col for col in df.columns if col.startswith(f"{simulator_id}_")]

            if sim_cols:
                # Create DataFrame with base columns + simulator columns
                sim_df = df[base_cols + sim_cols].copy()

                # Rename columns to remove simulator prefix
                rename_dict = {col: col.replace(f"{simulator_id}_", "") for col in sim_cols}
                sim_df.rename(columns=rename_dict, inplace=True)

                # Create clean, short filename
                short_name = simulator_id.replace("_simulator", "")
                sim_output_path = os.path.join(output_dir, f'{short_name}.csv')
                # Round numeric columns to 4 decimal places
                sim_df = sim_df.round(4)
                sim_df.to_csv(sim_output_path, index=False, float_format='%.4f')
                exported_files.append(sim_output_path)

        print(f"\nExported {len(exported_files)} individual simulator files:")
        for file_path in sorted(exported_files):
            print(f"  - {os.path.basename(file_path)}")

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
            
            # Check if harvest maturity has been reached (natural plant development)
            from models.phenology_model import LettuceGrowthStage
            harvest_maturity_reached = (current_stage == LettuceGrowthStage.HARVEST_MATURITY.value or
                                      str(current_stage) == "LettuceGrowthStage.HARVEST_MATURITY")

            if harvest_maturity_reached:
                print(f"Harvest maturity reached! Current stage: {current_stage} on day {self.current_day}")

            return harvest_maturity_reached
            
        except Exception as e:
            print(f"Error checking harvest maturity: {e}")
            return False
    
    def cleanup(self):
        """Cleanup orchestrator resources"""
        self.terminate_simulation()
        self.message_bus.stop()
        super().cleanup()
