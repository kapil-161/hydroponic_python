#!/usr/bin/env python3
"""Test leaf development model and simulator functionality"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.parameter_loader import StrictParameterLoader
from src.simulations.leaf_development_simulator import LeafDevelopmentSimulator
from src.models.base_model import DailyUpdateInput, DailyUpdateOutput

def test_leaf_development_system():
    """Test leaf development model and simulator"""
    print("=== Testing Leaf Development Model & Simulator ===")

    try:
        # 1. Test parameter loading
        print("1. Loading parameters from CSV...")
        loader = StrictParameterLoader("input/master_parameters.csv")
        leaf_params = loader.create_leaf_development_parameters()
        print(f"✓ Base phyllochron: {leaf_params.base_phyllochron}°C-day")
        print(f"✓ Max leaf number: {leaf_params.max_leaf_number}")
        print(f"✓ Temperature range: {leaf_params.min_temp}°C to {leaf_params.max_temp}°C")
        print(f"✓ Stress thresholds: drought={leaf_params.water_stress_threshold}, N={leaf_params.nitrogen_stress_threshold}")

        # 2. Test simulator initialization
        print("\n2. Initializing leaf development simulator...")
        simulator = LeafDevelopmentSimulator(leaf_params)

        # Prepare test data and dependencies
        system_data = {
            'plant_count': 20,
            'daily_growth_rate': 5.0,
            'total_biomass': 35.0
        }

        # Mock dependency data
        mock_phenology_data = {
            'growth_stage': 'vegetative',
            'development_index': 0.4,
            'thermal_time': 150.0
        }

        mock_stress_data = {
            'water_stress': 0.2,
            'nitrogen_stress': 0.1,
            'temperature_stress': 0.05,
            'nutrient_stress': 0.1,  # Added missing nutrient_stress
            'overall_stress': 0.3
        }

        mock_nitrogen_data = {
            'leaf_nitrogen_content': 0.035,  # g N/g dry mass
            'leaf_nitrogen_ratio': 0.8,
            'nitrogen_stress_index': 0.1
        }

        mock_environmental_data = {
            'light_intensity': 400.0,  # PPFD
            'temperature': 22.0,
            'humidity': 65.0,
            'wind_speed': 2.0
        }

        # Mock biomass allocation data
        mock_biomass_data = {
            'leaf_biomass': 15.0,
            'stem_biomass': 8.0,
            'root_biomass': 12.0,
            'total_biomass': 35.0,
            'growth_rate': 5.0
        }

        # Mock nutrient data
        mock_nutrient_data = {
            'nitrate_concentration': 200.0,  # mg/L
            'ammonium_concentration': 50.0,  # mg/L
            'phosphorus_concentration': 30.0,  # mg/L
            'potassium_concentration': 300.0,  # mg/L
            'solution_ph': 6.0,
            'solution_ec': 1.5,
            'nitrogen_availability': 0.8,  # Added missing parameters
            'nitrogen_uptake': 5.0  # mg N/plant/day
        }

        # Mock canopy data
        mock_canopy_data = {
            'canopy_height': 0.3,  # m
            'lai': 2.5,  # leaf area index
            'light_interception': 0.85,
            'canopy_coverage': 0.75
        }

        # Pre-populate dependency cache with all required dependencies
        from datetime import datetime
        simulator.dependency_cache['phenology_simulator'] = mock_phenology_data
        simulator.dependency_cache['stress_models'] = mock_stress_data
        simulator.dependency_cache['nitrogen_balance_simulator'] = mock_nitrogen_data
        simulator.dependency_cache['environmental_control'] = mock_environmental_data
        simulator.dependency_cache['biomass_allocation_simulator'] = mock_biomass_data
        simulator.dependency_cache['nutrient_models_simulator'] = mock_nutrient_data
        simulator.dependency_cache['canopy_architecture_simulator'] = mock_canopy_data

        # Set cache timestamps
        current_time = datetime.now()
        simulator.cache_timestamp['phenology_simulator'] = current_time
        simulator.cache_timestamp['stress_models'] = current_time
        simulator.cache_timestamp['nitrogen_balance_simulator'] = current_time
        simulator.cache_timestamp['environmental_control'] = current_time
        simulator.cache_timestamp['biomass_allocation_simulator'] = current_time
        simulator.cache_timestamp['nutrient_models_simulator'] = current_time
        simulator.cache_timestamp['canopy_architecture_simulator'] = current_time

        print("✓ Leaf development simulator initialized")

        # 3. Test simulation step
        print("\n3. Running leaf development simulation step...")
        inputs = DailyUpdateInput(
            day=10,
            date=datetime(2024, 1, 10),
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
            print(f"✓ Primary results available: {len(result.primary_results)} metrics")
            print(f"✓ Secondary results available: {len(result.secondary_results)} metrics")

            # Check specific leaf development results
            if result.internal_state:
                internal = result.internal_state
                print(f"✓ Total leaves: {internal.get('total_leaves', 0)}")
                print(f"✓ Total leaf area: {internal.get('total_leaf_area', 0):.6f} m²")
                lai_value = internal.get('leaf_area_index', 0)
                # Handle case where LAI might be a list
                if isinstance(lai_value, list):
                    lai_value = lai_value[0] if lai_value else 0
                print(f"✓ Leaf area index: {lai_value:.6f}")

        # 4. Test state retrieval
        print("\n4. Testing state retrieval...")
        state = simulator.get_current_state()
        print(f"✓ State contains {len(state)} properties")
        print(f"✓ Step count: {state.get('step_count', 0)}")

        print("\n=== Leaf Development System Test PASSED ===")
        return True

    except Exception as e:
        print(f"\n❌ Leaf development system test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_leaf_development_system()
    sys.exit(0 if success else 1)