"""
Distributed Simulation Runner

Main entry point for running the distributed hydroponic simulation system
with all 16 interconnected simulators. Follows Rules.md strictly.
"""

import pandas as pd
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from simulations.simulation_orchestrator import SimulationOrchestrator, SimulationConfig
from simulations.communication_bus import message_bus

# Import all simulators
from simulations.photosynthesis_simulator import PhotosynthesisSimulator
from simulations.respiration_simulator import RespirationSimulator
from simulations.biomass_allocation_simulator import BiomassAllocationSimulator
from simulations.phenology_simulator import PhenologySimulator
from simulations.stress_models_simulator import StressModelsSimulator
from simulations.water_uptake_simulator import WaterUptakeSimulator
from simulations.nutrient_models_simulator import NutrientModelsSimulator
from simulations.canopy_architecture_simulator import CanopyArchitectureSimulator
from simulations.root_system_simulator import RootSystemSimulator
from simulations.genetic_parameters_simulator import GeneticParametersSimulator
from simulations.leaf_development_simulator import LeafDevelopmentSimulator
from simulations.nitrogen_balance_simulator import NitrogenBalanceSimulator

# Import parameter loaders
from utils.parameter_loader import StrictParameterLoader
from utils.weather_loader import WeatherDataLoader


class DistributedSimulationRunner:
    """Main runner for distributed hydroponic simulation"""
    
    def __init__(self,
                 master_csv_path: str = "input/master_parameters.csv",
                 constants_csv_path: str = "input/constants.csv",
                 stress_csv_path: str = "input/stress.csv",
                 roots_csv_path: str = "input/roots.csv",
                 genetics_csv_path: str = "input/genetics.csv",
                 photo_csv_path: str = "input/photo.csv",
                 respiration_csv_path: str = "input/respiration.csv",
                 allocation_csv_path: str = "input/allocation.csv",
                 phenology_csv_path: str = "input/phenology.csv",
                 nitrogen_balance_csv_path: str = "input/nitrogen_balance.csv",
                 canopy_csv_path: str = "input/canopy.csv",
                 leaf_csv_path: str = "input/leaf.csv",
                 water_csv_path: str = "input/water.csv",
                 nutrient_csv_path: str = "input/nutrient.csv",
                 weather_csv_path: str = "input/LET_EXP001_2024_weather.csv"):
        """
        Initialize distributed simulation runner.

        Args:
            master_csv_path: Path to master parameters CSV file
            constants_csv_path: Path to universal constants CSV file
            stress_csv_path: Path to stress parameters CSV file
            roots_csv_path: Path to root system parameters CSV file
            genetics_csv_path: Path to genetic parameters CSV file
            photo_csv_path: Path to photosynthesis parameters CSV file
            respiration_csv_path: Path to respiration parameters CSV file
            allocation_csv_path: Path to biomass allocation parameters CSV file
            phenology_csv_path: Path to phenology parameters CSV file
            nitrogen_balance_csv_path: Path to nitrogen balance parameters CSV file
            canopy_csv_path: Path to canopy architecture parameters CSV file
            leaf_csv_path: Path to leaf development parameters CSV file
            water_csv_path: Path to water uptake and transpiration parameters CSV file
            nutrient_csv_path: Path to nutrient uptake and transport parameters CSV file
            weather_csv_path: Path to daily weather CSV file
        """
        # Load parameters and weather data - all from CSV, no defaults per Rules.md
        self.parameter_loader = StrictParameterLoader(master_csv_path, constants_csv_path, stress_csv_path, roots_csv_path, genetics_csv_path, photo_csv_path, respiration_csv_path, allocation_csv_path, phenology_csv_path, nitrogen_balance_csv_path, canopy_csv_path, leaf_csv_path, water_csv_path, nutrient_csv_path)
        self.weather_loader = WeatherDataLoader(weather_csv_path)

        # Load initial state from initials.csv - all from CSV per Rules.md
        self.initial_state_data = self.parameter_loader.load_initial_state("input/initials.csv")
        
        # Initialize simulation orchestrator - ALL values from CSV per Rules.md
        simulator_defaults = self.parameter_loader.get_category('simulator_defaults')
        self.config = SimulationConfig(
            total_days=int(self.parameter_loader.get_parameter('simulator_defaults_total_days_default')),
            steps_per_day=int(self.parameter_loader.get_parameter('simulator_defaults_steps_per_day')),
            step_duration_seconds=float(simulator_defaults['step_duration_seconds']),
            start_day=int(self.parameter_loader.get_parameter('simulator_defaults_start_day')),
            start_hour=int(self.parameter_loader.get_parameter('simulator_defaults_start_hour')),
            enable_real_time=bool(self.parameter_loader.get_parameter('simulator_defaults_enable_real_time_default')),
            synchronization_mode=str(self.parameter_loader.get_parameter('simulator_defaults_synchronization_mode_default')),
            data_collection_interval=int(self.parameter_loader.get_parameter('simulator_defaults_data_collection_interval')),
            max_concurrent_simulators=int(self.parameter_loader.get_parameter('simulator_defaults_max_concurrent_simulators')),
            max_errors=int(self.parameter_loader.get_parameter('simulator_defaults_max_errors')),
            progress_report_interval=int(self.parameter_loader.get_parameter('simulator_defaults_progress_report_interval')),
            initialization_wait_time=float(self.parameter_loader.get_parameter('simulator_defaults_initialization_wait_time')),
            event_processing_wait_time=float(self.parameter_loader.get_parameter('simulator_defaults_event_processing_wait_time')),
            initialization_cycles=int(self.parameter_loader.get_parameter('simulator_defaults_initialization_cycles'))
        )
        
        self.orchestrator = SimulationOrchestrator(self.config)
        
        # Initialize all simulators
        self.simulators: Dict[str, Any] = {}
        self._initialize_all_simulators()
        
        print(f"Distributed simulation system initialized with {len(self.simulators)} simulators")
    
    def _initialize_all_simulators(self):
        """Initialize all 16 simulators with parameters from CSV"""
        
        try:
            # 1. Photosynthesis Simulator
            photosynthesis_params = self.parameter_loader.create_photosynthesis_parameters()
            self.simulators['photosynthesis'] = PhotosynthesisSimulator(photosynthesis_params)
            self.orchestrator.register_simulator(self.simulators['photosynthesis'])
            
            # 2. Respiration Simulator
            respiration_params = self.parameter_loader.create_respiration_parameters()
            self.simulators['respiration'] = RespirationSimulator(respiration_params)
            self.orchestrator.register_simulator(self.simulators['respiration'])
            
            # 3. Biomass Allocation Simulator
            biomass_params = self.parameter_loader.create_biomass_allocation_parameters()
            self.simulators['biomass_allocation'] = BiomassAllocationSimulator(biomass_params)
            self.orchestrator.register_simulator(self.simulators['biomass_allocation'])
            
            # 4. Phenology Simulator
            phenology_params = self.parameter_loader.create_phenology_parameters()
            self.simulators['phenology'] = PhenologySimulator(phenology_params)
            self.orchestrator.register_simulator(self.simulators['phenology'])
            
            # 5. Stress Models Simulator
            stress_params = self.parameter_loader.create_stress_parameters()
            ph_optimal_min = self.parameter_loader.get_parameter('stress_parameters_ph_optimal_min')
            ph_optimal_max = self.parameter_loader.get_parameter('stress_parameters_ph_optimal_max')
            ph_stress_range = self.parameter_loader.get_parameter('stress_parameters_ph_stress_range')
            temperature_optimal_min = self.parameter_loader.get_parameter('phenology_parameters_optimal_temperature_min')
            temperature_optimal_max = self.parameter_loader.get_parameter('phenology_parameters_optimal_temperature_max')
            temperature_stress_range = self.parameter_loader.get_parameter('phenology_parameters_maximum_temperature') - temperature_optimal_max
            light_compensation_point = self.parameter_loader.get_parameter('stress_parameters_light_compensation_point')
            light_saturation_point = self.parameter_loader.get_parameter('stress_parameters_light_saturation_point')
            self.simulators['stress_models'] = StressModelsSimulator(
                stress_params,
                ph_optimal_min=ph_optimal_min,
                ph_optimal_max=ph_optimal_max,
                ph_stress_range=ph_stress_range,
                temperature_optimal_min=temperature_optimal_min,
                temperature_optimal_max=temperature_optimal_max,
                temperature_stress_range=temperature_stress_range,
                light_compensation_point=light_compensation_point,
                light_saturation_point=light_saturation_point
            )
            self.orchestrator.register_simulator(self.simulators['stress_models'])
            
            # 6. Water Uptake Simulator
            water_params = self.parameter_loader.create_water_uptake_parameters()
            self.simulators['water_uptake'] = WaterUptakeSimulator(water_params)
            self.orchestrator.register_simulator(self.simulators['water_uptake'])
            
            # 7. Nutrient Models Simulator
            nutrient_params = self.parameter_loader.create_nutrient_parameters()
            self.simulators['nutrient_models'] = NutrientModelsSimulator(nutrient_params)
            self.orchestrator.register_simulator(self.simulators['nutrient_models'])
            
            # 8. Canopy Architecture Simulator
            canopy_params = self.parameter_loader.create_canopy_architecture_parameters()
            self.simulators['canopy_architecture'] = CanopyArchitectureSimulator(canopy_params)
            self.orchestrator.register_simulator(self.simulators['canopy_architecture'])
            
            
            # 9. Root System Simulator
            root_params = self.parameter_loader.create_root_system_parameters()
            self.simulators['root_system'] = RootSystemSimulator(root_params)
            self.orchestrator.register_simulator(self.simulators['root_system'])
            
            
            # 10. Genetic Parameters Simulator
            genetic_db, cultivar_profile = self.parameter_loader.create_genetic_parameters()
            self.simulators['genetic_parameters'] = GeneticParametersSimulator(genetic_db, cultivar_profile)
            self.orchestrator.register_simulator(self.simulators['genetic_parameters'])
            
            # 11. Leaf Development Simulator
            leaf_params = self.parameter_loader.create_leaf_development_parameters()
            self.simulators['leaf_development'] = LeafDevelopmentSimulator(leaf_params)
            self.orchestrator.register_simulator(self.simulators['leaf_development'])
            
            # 12. Nitrogen Balance Simulator
            nitrogen_params = self.parameter_loader.create_nitrogen_balance_parameters()
            self.simulators['nitrogen_balance'] = NitrogenBalanceSimulator(nitrogen_params)
            self.orchestrator.register_simulator(self.simulators['nitrogen_balance'])
            

            # All simulators now initialized!
            
            
        except Exception as e:
            print(f"Error initializing simulators: {e}")
            raise
    
    def run_simulation(self, output_path: str = None) -> str:
        """
        Run the complete distributed simulation.
        
        Args:
            output_path: Optional path for output file
            
        Returns:
            Path to output file
        """
        print("Starting distributed hydroponic simulation...")
        
        try:
            # Get weather data from daily weather file
            print("Loading weather data...")
            weather_data = self.weather_loader.weather_data
            
            if weather_data is None or weather_data.empty:
                raise ValueError("Weather data is empty - no defaults allowed per Rules.md")
            
            # Update config based on weather data length
            self.config.total_days = len(weather_data)
            print(f"Running simulation for {self.config.total_days} days (up to harvest maturity)")
            
            # Start simulation with initial state from CSV
            start_time = time.time()
            self.orchestrator.start_simulation(weather_data, initial_state=self.initial_state_data)
            end_time = time.time()
            
            # Get results
            results_path = self.orchestrator.export_results(output_path)
            
            # Print performance metrics
            self._print_performance_metrics(start_time, end_time)
            
            return results_path
            
        except Exception as e:
            print(f"Simulation failed: {e}")
            raise
    
    def _print_performance_metrics(self, start_time: float, end_time: float):
        """Print performance metrics for the simulation"""
        duration = end_time - start_time
        
        print("\n" + "="*60)
        print("SIMULATION PERFORMANCE METRICS")
        print("="*60)
        
        # Overall performance
        print(f"Total simulation time: {duration:.2f} seconds")
        if duration > 0:
            print(f"Steps per second: {self.orchestrator.current_step / duration:.2f}")
        print(f"Total steps executed: {self.orchestrator.current_step}")
        
        # System status
        status = self.orchestrator.get_simulation_status()
        print(f"Simulators registered: {status['total_simulators']}")
        print(f"Data points collected: {status['data_points_collected']}")
        
        # Per-simulator performance
        print("\nPer-Simulator Performance:")
        performance = self.orchestrator.get_performance_metrics()
        for simulator_id, metrics in performance.items():
            if simulator_id != 'overall':
                print(f"  {simulator_id}:")
                for metric, value in metrics.items():
                    if isinstance(value, float):
                        print(f"    {metric}: {value:.4f}")
                    elif isinstance(value, dict):
                        print(f"    {metric}:")
                        for k, v in value.items():
                            if isinstance(v, float):
                                print(f"      {k}: {v:.4f}")
                            else:
                                print(f"      {k}: {v}")
                    else:
                        print(f"    {metric}: {value}")
        
        # Message bus status
        bus_status = message_bus.get_system_status()
        print(f"\nMessage Bus Status:")
        print(f"  Queue size: {bus_status['queue_size']}")
        print(f"  Event handlers: {sum(bus_status['event_handlers'].values())}")
        print(f"  Registered simulators: {len(bus_status['registered_simulators'])}")
        
        # Data consistency validation results
        validation_summary = self.orchestrator.get_validation_summary()
        print(f"\nData Consistency Validation:")
        print(f"  Total validations: {validation_summary['total_validations']}")
        print(f"  Errors: {validation_summary['total_errors']}")
        print(f"  Warnings: {validation_summary['total_warnings']}")
        print(f"  Critical issues: {validation_summary['total_critical']}")
        print(f"  Validation enabled: {validation_summary['validation_enabled']}")
        
        if validation_summary['total_errors'] > 0 or validation_summary['total_critical'] > 0:
            print(f"  ⚠️  Data consistency issues detected!")
        elif validation_summary['total_warnings'] > 0:
            print(f"  ⚠️  Data consistency warnings detected")
        else:
            print(f"  ✅ All data consistency checks passed")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'orchestrator_status': self.orchestrator.get_simulation_status(),
            'bus_status': message_bus.get_system_status(),
            'simulators': list(self.simulators.keys()),
            'config': {
                'total_days': self.config.total_days,
                'steps_per_day': self.config.steps_per_day,
                'synchronization_mode': self.config.synchronization_mode
            }
        }
    
    def cleanup(self):
        """Cleanup all resources"""
        print("Cleaning up distributed simulation system...")
        
        # Cleanup simulators
        for simulator in self.simulators.values():
            if hasattr(simulator, 'cleanup'):
                simulator.cleanup()
        
        # Cleanup orchestrator
        self.orchestrator.cleanup()
        
        print("Cleanup completed")


def main():
    """Main entry point for distributed simulation"""
    try:
        # Initialize runner
        runner = DistributedSimulationRunner()
        
        # Run simulation
        output_path = runner.run_simulation()
        print(f"\nSimulation completed successfully!")
        print(f"Results saved to: {output_path}")
        
        # Print final status
        status = runner.get_system_status()
        print(f"\nFinal system status:")
        print(f"  Total simulators: {len(status['simulators'])}")
        print(f"  Total steps: {status['orchestrator_status']['current_step']}")
        
        # Cleanup
        runner.cleanup()
        
    except Exception as e:
        print(f"Distributed simulation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
