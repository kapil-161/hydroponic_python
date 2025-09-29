#!/usr/bin/env python3
"""Test nutrient model and simulator functionality"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.parameter_loader import StrictParameterLoader
from src.simulations.nutrient_models_simulator import NutrientModelsSimulator
from src.simulations.communication_bus import SimulationEvent, EventType
from src.models.base_model import DailyUpdateInput, DailyUpdateOutput

def test_nutrient_system():
    """Test nutrient model and simulator"""
    print("=== Testing Nutrient Model & Simulator ===")

    try:
        # 1. Test parameter loading
        print("1. Loading parameters from CSV...")
        loader = StrictParameterLoader("input/master_parameters.csv")
        nutrient_params = loader.create_nutrient_parameters()
        print(f"✓ EC factors: N-NO3={nutrient_params.ec_factor_n_no3}, P-PO4={nutrient_params.ec_factor_p_po4}")
        print(f"✓ Kinetics: N-NO3 Vmax={nutrient_params.kinetics_n_no3_vmax}, Km={nutrient_params.kinetics_n_no3_km}")
        print(f"✓ Transport: Xylem capacity={nutrient_params.xylem_transport_capacity}, Phloem capacity={nutrient_params.phloem_transport_capacity}")

        # Prepare test data
        system_data = {
            'tank_volume_L': 100.0,
            'plant_count': 20,
            'daily_growth_rate': 5.0,
            'optimal_ec': 1.2,
            'root_surface_area': 0.5,
            'temperature': 22.0,
            'solution_volume': 95.0
        }

        # Mock other simulator data
        mock_biomass_data = {
            'leaf_biomass': 15.0,
            'stem_biomass': 8.0,
            'root_biomass': 12.0,
            'total_biomass': 35.0
        }

        mock_photosynthesis_data = {
            'daily_photosynthesis': 25.0,
            'assimilate_production': 20.0,
            'photosynthetic_rate': 0.8,
            'carbon_assimilation_rate': 0.8  # What nutrient simulator expects
        }

        mock_water_data = {
            'water_uptake_rate': 12.0,  # This is what nutrient simulator expects
            'transpiration_rate': 0.5,
            'daily_water_uptake': 12.0,
            'root_water_uptake': 11.8
        }

        mock_root_data = {
            'root_depth': 0.3,  # 30 cm root depth
            'root_distribution': {'upper': 0.6, 'middle': 0.3, 'lower': 0.1},
            'root_biomass': 12.0,  # From biomass data
            'root_surface_area': 0.5  # From system data
        }

        mock_ph_data = {
            'ph': 6.0,  # Typical hydroponic pH
            'ph_stability': 0.95,
            'buffer_capacity': 5.0
        }

        mock_phenology_data = {
            'growth_stage': 'vegetative',  # Must match sink_strength_coefficients keys
            'development_index': 0.4
        }

        mock_stress_data = {
            'water_stress': 0.1,
            'nutrient_stress': 0.05,
            'temperature_stress': 0.02,
            'overall_stress': 0.15
        }

        mock_respiration_data = {
            'daily_respiration': 5.0,
            'maintenance_respiration': 3.0,
            'growth_respiration': 2.0,
            'respiration_rate': 0.3  # What nutrient simulator expects
        }

        # 2. Test simulator initialization
        print("\n2. Initializing nutrient simulator...")
        simulator = NutrientModelsSimulator(nutrient_params)

        # Pre-populate dependency cache with required data
        from datetime import datetime
        simulator.dependency_cache['biomass_allocation_simulator'] = mock_biomass_data
        simulator.dependency_cache['photosynthesis_simulator'] = mock_photosynthesis_data
        simulator.dependency_cache['water_uptake_simulator'] = mock_water_data
        simulator.dependency_cache['root_system_simulator'] = mock_root_data
        simulator.dependency_cache['ph_model_simulator'] = mock_ph_data
        simulator.dependency_cache['phenology_simulator'] = mock_phenology_data
        simulator.dependency_cache['stress_models'] = mock_stress_data
        simulator.dependency_cache['respiration_simulator'] = mock_respiration_data
        simulator.dependency_cache['system_config'] = system_data

        # Set cache timestamps to indicate fresh data
        current_time = datetime.now()
        simulator.cache_timestamp['biomass_allocation_simulator'] = current_time
        simulator.cache_timestamp['photosynthesis_simulator'] = current_time
        simulator.cache_timestamp['water_uptake_simulator'] = current_time
        simulator.cache_timestamp['root_system_simulator'] = current_time
        simulator.cache_timestamp['ph_model_simulator'] = current_time
        simulator.cache_timestamp['phenology_simulator'] = current_time
        simulator.cache_timestamp['stress_models'] = current_time
        simulator.cache_timestamp['respiration_simulator'] = current_time
        simulator.cache_timestamp['system_config'] = current_time

        print("✓ Nutrient simulator initialized")

        # 3. Test basic system data (minimal test data)
        print("\n3. Testing with basic system configuration...")

        # 4. Test simulation step
        print("\n4. Running nutrient simulation step...")
        from datetime import datetime
        inputs = DailyUpdateInput(
            day=5,
            date=datetime(2024, 1, 5),
            temperature=22.0,
            humidity=65.0,
            solar_radiation=400.0,
            vpd=1.2,
            co2_concentration=400.0,
            environmental_conditions={'wind_speed': 2.0, 'light_hours': 12.0},
            plant_state={'biomass': 35.0, 'lai': 2.5},
            system_state=system_data
        )

        result = simulator.daily_update(inputs)
        print(f"✓ Simulation result: {'success' if result.success else 'error'}")
        if not result.success:
            print(f"✗ Error: {result.secondary_results.get('error_message', 'Unknown error')}")

        if result.success:
            print(f"✓ Solution EC: {result.primary_results.get('solution_ec', 'N/A')}")
            print(f"✓ Solution pH: {result.primary_results.get('solution_ph', 'N/A')}")
            print(f"✓ Total nutrient uptake: {result.primary_results.get('total_nutrient_uptake', 0):.6f}")

            # Check internal state for more details
            if result.internal_state:
                print(f"✓ Nutrient concentrations available: {len(result.internal_state.get('nutrient_concentrations', {}))}")
                print(f"✓ Nutrient uptake rates available: {len(result.internal_state.get('nutrient_uptake_rates', {}))}")

        # 5. Test state retrieval
        print("\n5. Testing state retrieval...")
        state = simulator.get_current_state()
        print(f"✓ State contains {len(state)} properties")
        print(f"✓ Step count: {state.get('step_count', 0)}")

        print("\n=== Nutrient System Test PASSED ===")
        return True

    except Exception as e:
        print(f"\n❌ Nutrient system test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nutrient_system()
    sys.exit(0 if success else 1)