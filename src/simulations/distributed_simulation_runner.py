"""
Distributed Simulation Runner

Main entry point for running the distributed hydroponic simulation system
with all 17 interconnected simulators. Follows Rules.md strictly.
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

from .simulation_orchestrator import SimulationOrchestrator, SimulationConfig
from .communication_bus import message_bus

# Import all simulators
from .photosynthesis_simulator import PhotosynthesisSimulator
from .respiration_simulator import RespirationSimulator
from .biomass_allocation_simulator import BiomassAllocationSimulator
from .phenology_simulator import PhenologySimulator
from .stress_models_simulator import StressModelsSimulator
from .water_uptake_simulator import WaterUptakeSimulator
from .nutrient_models_simulator import NutrientModelsSimulator
from .canopy_architecture_simulator import CanopyArchitectureSimulator
from .ph_model_simulator import PHModelSimulator
from .root_system_simulator import RootSystemSimulator
from .environmental_control_simulator import EnvironmentalControlSimulator
from .genetic_parameters_simulator import GeneticParametersSimulator
from .leaf_development_simulator import LeafDevelopmentSimulator
from .nitrogen_balance_simulator import NitrogenBalanceSimulator
from .root_zone_temperature_simulator import RootZoneTemperatureSimulator
from .senescence_simulator import SenescenceSimulator

# Import parameter loaders
from utils.parameter_loader import StrictParameterLoader
from utils.weather_loader import WeatherDataLoader


class DistributedSimulationRunner:
    """Main runner for distributed hydroponic simulation"""
    
    def __init__(self, 
                 master_csv_path: str = "input/master_parameters.csv",
                 weather_csv_path: str = "input/LET_EXP001_2024_weather.csv"):
        """
        Initialize distributed simulation runner.
        
        Args:
            master_csv_path: Path to master parameters CSV file
            weather_csv_path: Path to daily weather CSV file
        """
        print("Initializing Distributed Hydroponic Simulation System")
        
        # Load parameters and weather data - all from CSV, no defaults per Rules.md
        print("Loading parameters from CSV files...")
        self.parameter_loader = StrictParameterLoader(master_csv_path)
        self.weather_loader = WeatherDataLoader(weather_csv_path)
        
        # Initialize simulation orchestrator
        # These values must come from CSV parameters, not hardcoded
        simulator_defaults = self.parameter_loader.get_category('simulator_defaults')
        self.config = SimulationConfig(
            total_days=30,  # Will be determined by weather data length
            steps_per_day=24,  # Hourly steps
            step_duration_seconds=float(simulator_defaults['step_duration_seconds']),
            enable_real_time=False,  # Batch processing
            synchronization_mode="sequential"  # Sequential for now, can be parallel
        )
        
        self.orchestrator = SimulationOrchestrator(self.config)
        
        # Initialize all simulators
        self.simulators: Dict[str, Any] = {}
        self._initialize_all_simulators()
        
        print(f"Distributed simulation system initialized with {len(self.simulators)} simulators")
    
    def _initialize_all_simulators(self):
        """Initialize all 17 simulators with parameters from CSV"""
        print("Initializing all simulators...")
        
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
            self.simulators['stress_models'] = StressModelsSimulator(stress_params)
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
            
            # 9. pH Model Simulator
            ph_params = self.parameter_loader.create_ph_parameters()
            self.simulators['ph_model'] = PHModelSimulator(ph_params)
            self.orchestrator.register_simulator(self.simulators['ph_model'])
            
            # 10. Root System Simulator
            root_params = self.parameter_loader.create_root_system_parameters()
            self.simulators['root_system'] = RootSystemSimulator(root_params)
            self.orchestrator.register_simulator(self.simulators['root_system'])
            
            # 11. Environmental Control Simulator
            env_setpoints = self.parameter_loader.create_environmental_setpoints()
            env_equipment = self.parameter_loader.create_control_equipment()
            self.simulators['environmental_control'] = EnvironmentalControlSimulator(env_setpoints, env_equipment)
            self.orchestrator.register_simulator(self.simulators['environmental_control'])
            
            # 12. Genetic Parameters Simulator
            genetic_db, cultivar_profile = self.parameter_loader.create_genetic_parameters()
            self.simulators['genetic_parameters'] = GeneticParametersSimulator(genetic_db, cultivar_profile)
            self.orchestrator.register_simulator(self.simulators['genetic_parameters'])
            
            # 13. Leaf Development Simulator
            leaf_params = self.parameter_loader.create_leaf_development_parameters()
            self.simulators['leaf_development'] = LeafDevelopmentSimulator(leaf_params)
            self.orchestrator.register_simulator(self.simulators['leaf_development'])
            
            # 14. Nitrogen Balance Simulator
            nitrogen_params = self.parameter_loader.create_nitrogen_balance_parameters()
            self.simulators['nitrogen_balance'] = NitrogenBalanceSimulator(nitrogen_params)
            self.orchestrator.register_simulator(self.simulators['nitrogen_balance'])
            
            # 15. Root Zone Temperature Simulator
            rzt_params = self.parameter_loader.create_rzt_parameters()
            self.simulators['root_zone_temperature'] = RootZoneTemperatureSimulator(rzt_params)
            self.orchestrator.register_simulator(self.simulators['root_zone_temperature'])
            
            # 16. Senescence Simulator
            senescence_params = self.parameter_loader.create_senescence_parameters()
            self.simulators['senescence'] = SenescenceSimulator(senescence_params)
            self.orchestrator.register_simulator(self.simulators['senescence'])
            
            # All 17 simulators now initialized!
            
            print(f"Initialized {len(self.simulators)} simulators successfully")
            
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
            print(f"Running simulation for {self.config.total_days} days")
            
            # Start simulation
            start_time = time.time()
            self.orchestrator.start_simulation(weather_data)
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
