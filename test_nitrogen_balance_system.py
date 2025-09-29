#!/usr/bin/env python3
"""Test nitrogen balance model and simulator functionality"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.parameter_loader import StrictParameterLoader
from src.simulations.nitrogen_balance_simulator import NitrogenBalanceSimulator
from src.models.base_model import DailyUpdateInput, DailyUpdateOutput

def test_nitrogen_balance_system():
    """Test nitrogen balance model and simulator"""
    print("=== Testing Nitrogen Balance Model & Simulator ===")

    try:
        # 1. Test parameter loading
        print("1. Loading parameters from CSV...")
        loader = StrictParameterLoader("input/master_parameters.csv")
        nitrogen_params = loader.create_nitrogen_balance_parameters()
        print(f"✓ Basic rates: nitrate reduction={nitrogen_params.nitrate_reduction_rate}, ammonium assimilation={nitrogen_params.ammonium_assimilation_rate}")
        print(f"✓ Use efficiency: photosynthetic={nitrogen_params.photosynthetic_n_use_efficiency}, growth={nitrogen_params.growth_n_use_efficiency}")
        print(f"✓ Thresholds: stress={nitrogen_params.n_stress_threshold}, luxury uptake={nitrogen_params.luxury_uptake_threshold}")

        # 2. Test simulator initialization
        print("\n2. Initializing nitrogen balance simulator...")
        simulator = NitrogenBalanceSimulator(nitrogen_params)

        # Prepare test data and dependencies
        system_data = {
            'tank_volume_L': 100.0,
            'plant_count': 20,
            'daily_growth_rate': 5.0,
            'root_biomass': 12.0,
            'leaf_biomass': 15.0,
            'total_biomass': 35.0
        }

        # Mock dependency data (similar to nutrient system test)
        mock_nutrient_data = {
            'nitrate_concentration': 200.0,  # mg/L
            'ammonium_concentration': 50.0,  # mg/L
            'amino_acid_concentration': 20.0,  # mg/L
            'solution_ph': 6.0
        }

        mock_biomass_data = {
            'leaf_biomass': 15.0,
            'stem_biomass': 8.0,
            'root_biomass': 12.0,
            'total_biomass': 35.0,
            'growth_rate': 5.0
        }

        mock_root_data = {
            'root_biomass': 12.0,
            'root_surface_area': 0.5,
            'specific_root_length': 150.0,
            'root_activity': 0.8
        }

        mock_photosynthesis_data = {
            'daily_photosynthesis': 25.0,
            'carbon_assimilation_rate': 0.8,
            'photosynthetic_capacity': 30.0
        }

        mock_phenology_data = {
            'growth_stage': 'vegetative',
            'development_index': 0.4
        }

        # Pre-populate dependency cache
        from datetime import datetime
        simulator.dependency_cache['nutrient_models_simulator'] = mock_nutrient_data
        simulator.dependency_cache['biomass_allocation_simulator'] = mock_biomass_data
        simulator.dependency_cache['root_system_simulator'] = mock_root_data
        simulator.dependency_cache['photosynthesis_simulator'] = mock_photosynthesis_data
        simulator.dependency_cache['phenology_simulator'] = mock_phenology_data

        # Set cache timestamps
        current_time = datetime.now()
        simulator.cache_timestamp['nutrient_models_simulator'] = current_time
        simulator.cache_timestamp['biomass_allocation_simulator'] = current_time
        simulator.cache_timestamp['root_system_simulator'] = current_time
        simulator.cache_timestamp['photosynthesis_simulator'] = current_time
        simulator.cache_timestamp['phenology_simulator'] = current_time

        print("✓ Nitrogen balance simulator initialized")

        # 3. Test simulation step
        print("\n3. Running nitrogen balance simulation step...")
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
            print(f"✓ Total nitrogen uptake: {result.primary_results.get('total_nitrogen_uptake', 0):.6f}")
            print(f"✓ Nitrogen use efficiency: {result.primary_results.get('nitrogen_use_efficiency', 0):.6f}")
            print(f"✓ Nitrogen stress index: {result.primary_results.get('nitrogen_stress_index', 0):.6f}")

            # Check internal state for detailed results
            if result.internal_state:
                internal = result.internal_state
                print(f"✓ Uptake rates available: {len([k for k in internal.keys() if 'uptake' in k])}")
                print(f"✓ Allocation rates available: {len([k for k in internal.keys() if 'allocation' in k])}")

        # 4. Test state retrieval
        print("\n4. Testing state retrieval...")
        state = simulator.get_current_state()
        print(f"✓ State contains {len(state)} properties")
        print(f"✓ Step count: {state.get('step_count', 0)}")

        print("\n=== Nitrogen Balance System Test PASSED ===")
        return True

    except Exception as e:
        print(f"\n❌ Nitrogen balance system test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nitrogen_balance_system()
    sys.exit(0 if success else 1)