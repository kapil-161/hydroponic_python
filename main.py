#!/usr/bin/env python3
"""
Main Hydroponic Simulation

Simple approach: Run the simulation orchestrator directly with individual simulators.
"""

import sys
import os
import pandas as pd

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from simulations.simulation_orchestrator import SimulationOrchestrator, SimulationConfig

# Import individual simulators
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


def main():
    """Main entry point for the hydroponic simulation"""
    try:
        print("🌱 Hydroponic Simulation System")
        print("=" * 50)
        
        # Load weather data
        print("📊 Loading weather data...")
        weather_data = pd.read_csv("input/LET_EXP001_2024_weather.csv")
        print(f"   ✅ Weather data loaded: {len(weather_data)} days")
        
        # Load parameters
        print("⚙️  Loading parameters...")
        parameter_loader = StrictParameterLoader("input/master_parameters.csv")
        print("   ✅ Parameters loaded successfully")
        
        # Initialize simulation orchestrator
        print("🎯 Initializing simulation orchestrator...")
        config = SimulationConfig(
            total_days=min(30, len(weather_data)),  # Limit to 30 days for testing
            steps_per_day=24,  # Hourly steps
            step_duration_seconds=0.1,  # Fast execution
            enable_real_time=False,  # Batch processing
            synchronization_mode="sequential"
        )
        
        orchestrator = SimulationOrchestrator(config)
        
        # Register individual simulators
        print("🔧 Registering simulators...")
        simulators = {}
        
        try:
            # 1. Photosynthesis Simulator
            photosynthesis_params = parameter_loader.create_photosynthesis_parameters()
            simulators['photosynthesis_simulator'] = PhotosynthesisSimulator(photosynthesis_params)
            orchestrator.register_simulator(simulators['photosynthesis_simulator'])
            
            # 2. Respiration Simulator  
            respiration_params = parameter_loader.create_respiration_parameters()
            simulators['respiration_simulator'] = RespirationSimulator(respiration_params)
            orchestrator.register_simulator(simulators['respiration_simulator'])
            
            # 3. Biomass Allocation Simulator
            biomass_params = parameter_loader.create_biomass_allocation_parameters()
            simulators['biomass_allocation_simulator'] = BiomassAllocationSimulator(biomass_params)
            orchestrator.register_simulator(simulators['biomass_allocation_simulator'])
            
            # 4. Phenology Simulator
            phenology_params = parameter_loader.create_phenology_parameters()
            simulators['phenology_simulator'] = PhenologySimulator(phenology_params)
            orchestrator.register_simulator(simulators['phenology_simulator'])
            
            # 5. Stress Models Simulator
            stress_params = parameter_loader.create_stress_parameters()
            simulators['stress_models'] = StressModelsSimulator(stress_params)
            orchestrator.register_simulator(simulators['stress_models'])
            
            # 6. Water Uptake Simulator
            water_params = parameter_loader.create_water_uptake_parameters()
            simulators['water_uptake_simulator'] = WaterUptakeSimulator(water_params)
            orchestrator.register_simulator(simulators['water_uptake_simulator'])
            
            # 7. Nutrient Models Simulator
            nutrient_params = parameter_loader.create_nutrient_parameters()
            simulators['nutrient_models_simulator'] = NutrientModelsSimulator(nutrient_params)
            orchestrator.register_simulator(simulators['nutrient_models_simulator'])
            
            # 8. Canopy Architecture Simulator
            canopy_params = parameter_loader.create_canopy_architecture_parameters()
            simulators['canopy_architecture_simulator'] = CanopyArchitectureSimulator(canopy_params)
            orchestrator.register_simulator(simulators['canopy_architecture_simulator'])
            
            # 9. pH Model Simulator
            ph_params = parameter_loader.create_ph_parameters()
            simulators['ph_model_simulator'] = PHModelSimulator(ph_params)
            orchestrator.register_simulator(simulators['ph_model_simulator'])
            
            # 10. Root System Simulator
            root_params = parameter_loader.create_root_system_parameters()
            simulators['root_system_simulator'] = RootSystemSimulator(root_params)
            orchestrator.register_simulator(simulators['root_system_simulator'])
            
            # 11. Environmental Control Simulator
            env_setpoints, env_equipment = parameter_loader.create_environmental_control_parameters()
            simulators['environmental_control'] = EnvironmentalControlSimulator(env_setpoints, env_equipment)
            orchestrator.register_simulator(simulators['environmental_control'])
            
            # 12. Genetic Parameters Simulator
            genetic_db, cultivar_profile = parameter_loader.create_genetic_parameters()
            simulators['genetic_parameters_simulator'] = GeneticParametersSimulator(genetic_db, cultivar_profile)
            orchestrator.register_simulator(simulators['genetic_parameters_simulator'])
            
            # 13. Leaf Development Simulator
            leaf_params = parameter_loader.create_leaf_development_parameters()
            simulators['leaf_development_simulator'] = LeafDevelopmentSimulator(leaf_params)
            orchestrator.register_simulator(simulators['leaf_development_simulator'])
            
            # 14. Nitrogen Balance Simulator
            nitrogen_params = parameter_loader.create_nitrogen_balance_parameters()
            simulators['nitrogen_balance_simulator'] = NitrogenBalanceSimulator(nitrogen_params)
            orchestrator.register_simulator(simulators['nitrogen_balance_simulator'])
            
            # 15. Root Zone Temperature Simulator
            rzt_params = parameter_loader.create_root_zone_temperature_parameters()
            simulators['root_zone_temperature_simulator'] = RootZoneTemperatureSimulator(rzt_params)
            orchestrator.register_simulator(simulators['root_zone_temperature_simulator'])
            
            # 16. Senescence Simulator
            senescence_params = parameter_loader.create_senescence_parameters()
            simulators['senescence_simulator'] = SenescenceSimulator(senescence_params)
            orchestrator.register_simulator(simulators['senescence_simulator'])
            
            print(f"   ✅ {len(simulators)} simulators registered successfully")
            
        except Exception as e:
            print(f"   ❌ Error registering simulators: {e}")
            print("   Continuing with available simulators...")
        
        print("🚀 Starting simulation...")
        orchestrator.start_simulation(weather_data)
        
        # Get results
        results_path = orchestrator.export_results()
        
        print("=" * 50)
        print("✅ Simulation completed successfully!")
        print(f"📁 Results saved to: {results_path}")
        print("=" * 50)
        
        # Cleanup
        orchestrator.cleanup()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
