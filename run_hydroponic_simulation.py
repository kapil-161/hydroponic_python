#!/usr/bin/env python3
"""
Main Hydroponic Simulation Runner

This is the main entry point for running the hydroponic simulation.
It properly registers all 17 individual simulators with the orchestrator.
"""

import sys
import os
import pandas as pd
from typing import Dict, Any

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import simulation components
from simulations.simulation_orchestrator import SimulationOrchestrator, SimulationConfig

# Import all individual simulators
from simulations.photosynthesis_simulator import PhotosynthesisSimulator
from simulations.respiration_simulator import RespirationSimulator
from simulations.biomass_allocation_simulator import BiomassAllocationSimulator
from simulations.phenology_simulator import PhenologySimulator
from simulations.stress_models_simulator import StressModelsSimulator
from simulations.water_uptake_simulator import WaterUptakeSimulator
from simulations.nutrient_models_simulator import NutrientModelsSimulator
from simulations.canopy_architecture_simulator import CanopyArchitectureSimulator
from simulations.ph_model_simulator import PHModelSimulator
from simulations.root_system_simulator import RootSystemSimulator
from simulations.environmental_control_simulator import EnvironmentalControlSimulator
from simulations.genetic_parameters_simulator import GeneticParametersSimulator
from simulations.leaf_development_simulator import LeafDevelopmentSimulator
from simulations.nitrogen_balance_simulator import NitrogenBalanceSimulator
from simulations.root_zone_temperature_simulator import RootZoneTemperatureSimulator
from simulations.senescence_simulator import SenescenceSimulator

# Import parameter loaders
from utils.parameter_loader import StrictParameterLoader
from utils.weather_loader import WeatherDataLoader


class HydroponicSimulationRunner:
    """Main simulation runner that properly registers all simulators"""
    
    def __init__(self, 
                 master_csv_path: str = "input/master_parameters.csv",
                 weather_csv_path: str = "input/LET_EXP001_2024_weather.csv"):
        """
        Initialize the hydroponic simulation runner.
        
        Args:
            master_csv_path: Path to master parameters CSV file
            weather_csv_path: Path to daily weather CSV file
        """
        print("🌱 Initializing Hydroponic Simulation System")
        print("=" * 50)
        
        # Load weather data
        print("📊 Loading weather data...")
        try:
            self.weather_loader = WeatherDataLoader(weather_csv_path)
            self.weather_data = self.weather_loader.weather_data
            print(f"   ✅ Weather data loaded: {len(self.weather_data)} days")
        except Exception as e:
            print(f"   ❌ Failed to load weather data: {e}")
            raise
        
        # Load parameters
        print("⚙️  Loading parameters...")
        try:
            self.parameter_loader = StrictParameterLoader(master_csv_path)
            print(f"   ✅ Parameters loaded successfully")
        except Exception as e:
            print(f"   ❌ Failed to load parameters: {e}")
            raise
        
        # Initialize simulation orchestrator
        print("🎯 Initializing simulation orchestrator...")
        self.config = SimulationConfig(
            total_days=len(self.weather_data),
            steps_per_day=24,  # Hourly steps
            step_duration_seconds=0.1,  # Fast execution
            enable_real_time=False,  # Batch processing
            synchronization_mode="sequential"
        )
        
        self.orchestrator = SimulationOrchestrator(self.config)
        
        # Initialize and register all simulators
        print("🔧 Registering simulators...")
        self.simulators: Dict[str, Any] = {}
        self._register_all_simulators()
        
        print(f"   ✅ {len(self.simulators)} simulators registered successfully")
        print("=" * 50)
    
    def _register_all_simulators(self):
        """Register all 17 simulators with the orchestrator"""
        try:
            # 1. Photosynthesis Simulator
            photosynthesis_params = self.parameter_loader.create_photosynthesis_parameters()
            self.simulators['photosynthesis_simulator'] = PhotosynthesisSimulator(photosynthesis_params)
            self.orchestrator.register_simulator(self.simulators['photosynthesis_simulator'])
            
            # 2. Respiration Simulator
            respiration_params = self.parameter_loader.create_respiration_parameters()
            self.simulators['respiration_simulator'] = RespirationSimulator(respiration_params)
            self.orchestrator.register_simulator(self.simulators['respiration_simulator'])
            
            # 3. Biomass Allocation Simulator
            biomass_params = self.parameter_loader.create_biomass_allocation_parameters()
            self.simulators['biomass_allocation_simulator'] = BiomassAllocationSimulator(biomass_params)
            self.orchestrator.register_simulator(self.simulators['biomass_allocation_simulator'])
            
            # 4. Phenology Simulator
            phenology_params = self.parameter_loader.create_phenology_parameters()
            self.simulators['phenology_simulator'] = PhenologySimulator(phenology_params)
            self.orchestrator.register_simulator(self.simulators['phenology_simulator'])
            
            # 5. Stress Models Simulator
            stress_params = self.parameter_loader.create_stress_parameters()
            self.simulators['stress_models'] = StressModelsSimulator(stress_params)
            self.orchestrator.register_simulator(self.simulators['stress_models'])
            
            # 6. Water Uptake Simulator
            water_params = self.parameter_loader.create_water_uptake_parameters()
            self.simulators['water_uptake_simulator'] = WaterUptakeSimulator(water_params)
            self.orchestrator.register_simulator(self.simulators['water_uptake_simulator'])
            
            # 7. Nutrient Models Simulator
            nutrient_params = self.parameter_loader.create_nutrient_parameters()
            self.simulators['nutrient_models_simulator'] = NutrientModelsSimulator(nutrient_params)
            self.orchestrator.register_simulator(self.simulators['nutrient_models_simulator'])
            
            # 8. Canopy Architecture Simulator
            canopy_params = self.parameter_loader.create_canopy_architecture_parameters()
            self.simulators['canopy_architecture_simulator'] = CanopyArchitectureSimulator(canopy_params)
            self.orchestrator.register_simulator(self.simulators['canopy_architecture_simulator'])
            
            # 9. pH Model Simulator
            ph_params = self.parameter_loader.create_ph_parameters()
            self.simulators['ph_model_simulator'] = PHModelSimulator(ph_params)
            self.orchestrator.register_simulator(self.simulators['ph_model_simulator'])
            
            # 10. Root System Simulator
            root_params = self.parameter_loader.create_root_system_parameters()
            self.simulators['root_system_simulator'] = RootSystemSimulator(root_params)
            self.orchestrator.register_simulator(self.simulators['root_system_simulator'])
            
            # 11. Environmental Control Simulator
            env_setpoints, env_equipment = self.parameter_loader.create_environmental_control_parameters()
            self.simulators['environmental_control'] = EnvironmentalControlSimulator(env_setpoints, env_equipment)
            self.orchestrator.register_simulator(self.simulators['environmental_control'])
            
            # 12. Genetic Parameters Simulator
            genetic_db, cultivar_profile = self.parameter_loader.create_genetic_parameters()
            self.simulators['genetic_parameters_simulator'] = GeneticParametersSimulator(genetic_db, cultivar_profile)
            self.orchestrator.register_simulator(self.simulators['genetic_parameters_simulator'])
            
            # 13. Leaf Development Simulator
            leaf_params = self.parameter_loader.create_leaf_development_parameters()
            self.simulators['leaf_development_simulator'] = LeafDevelopmentSimulator(leaf_params)
            self.orchestrator.register_simulator(self.simulators['leaf_development_simulator'])
            
            # 14. Nitrogen Balance Simulator
            nitrogen_params = self.parameter_loader.create_nitrogen_balance_parameters()
            self.simulators['nitrogen_balance_simulator'] = NitrogenBalanceSimulator(nitrogen_params)
            self.orchestrator.register_simulator(self.simulators['nitrogen_balance_simulator'])
            
            # 15. Root Zone Temperature Simulator
            rzt_params = self.parameter_loader.create_root_zone_temperature_parameters()
            self.simulators['root_zone_temperature_simulator'] = RootZoneTemperatureSimulator(rzt_params)
            self.orchestrator.register_simulator(self.simulators['root_zone_temperature_simulator'])
            
            # 16. Senescence Simulator
            senescence_params = self.parameter_loader.create_senescence_parameters()
            self.simulators['senescence_simulator'] = SenescenceSimulator(senescence_params)
            self.orchestrator.register_simulator(self.simulators['senescence_simulator'])
            
            print(f"   ✅ All {len(self.simulators)} simulators registered successfully")
            
        except Exception as e:
            print(f"   ❌ Error registering simulators: {e}")
            raise
    
    def run_simulation(self, output_path: str = None) -> str:
        """
        Run the complete hydroponic simulation.
        
        Args:
            output_path: Optional path for output file
            
        Returns:
            Path to output file
        """
        print("\n🚀 Starting Hydroponic Simulation")
        print("=" * 50)
        
        try:
            # Start simulation
            self.orchestrator.start_simulation(self.weather_data)
            
            # Get results
            results_path = self.orchestrator.export_results(output_path)
            
            print("=" * 50)
            print("✅ Simulation completed successfully!")
            print(f"📁 Results saved to: {results_path}")
            print("=" * 50)
            
            return results_path
            
        except Exception as e:
            print(f"❌ Simulation failed: {e}")
            raise
    
    def cleanup(self):
        """Cleanup all resources"""
        print("\n🧹 Cleaning up simulation resources...")
        
        # Cleanup simulators
        for name, simulator in self.simulators.items():
            try:
                if hasattr(simulator, 'cleanup'):
                    simulator.cleanup()
            except Exception as e:
                print(f"   Warning: Error cleaning up {name}: {e}")
        
        # Cleanup orchestrator
        try:
            self.orchestrator.cleanup()
        except Exception as e:
            print(f"   Warning: Error cleaning up orchestrator: {e}")
        
        print("✅ Cleanup completed")


def main():
    """Main entry point for the hydroponic simulation"""
    try:
        print("🌱 Hydroponic Simulation System")
        print("=" * 50)
        
        # Initialize runner
        runner = HydroponicSimulationRunner()
        
        # Run simulation
        output_path = runner.run_simulation()
        
        # Cleanup
        runner.cleanup()
        
        print(f"\n🎉 Simulation completed successfully!")
        print(f"📁 Results: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
