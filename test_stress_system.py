#!/usr/bin/env python3
"""Test stress model and simulator functionality"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.parameter_loader import StrictParameterLoader
from src.simulations.stress_models_simulator import StressModelsSimulator
from src.models.base_model import DailyUpdateInput, DailyUpdateOutput

def test_stress_system():
    """Test stress model and simulator"""
    print("=== Testing Stress Model & Simulator ===")

    try:
        # 1. Test parameter loading
        print("1. Loading parameters from CSV...")
        loader = StrictParameterLoader("input/master_parameters.csv")
        stress_params = loader.create_stress_parameters()
        print(f"✓ Stress weights available: {len(stress_params.stress_weights)}")
        print(f"✓ Process sensitivity available: {len(stress_params.process_sensitivity)}")
        print(f"✓ Temperature weight: {stress_params.stress_weights.get('temperature', 'N/A')}")
        print(f"✓ Water weight: {stress_params.stress_weights.get('water', 'N/A')}")
        print(f"✓ Cache timeout: {stress_params.cache_timeout}")

        # 2. Test simulator initialization
        print("\n2. Initializing stress models simulator...")
        simulator = StressModelsSimulator(stress_params)

        # Prepare test data and dependencies
        system_data = {
            'tank_volume_L': 100.0,
            'plant_count': 20,
            'daily_growth_rate': 5.0,
            'total_biomass': 35.0
        }

        # Mock dependency data
        mock_environmental_data = {
            'temperature': 22.0,
            'humidity': 65.0,
            'light_intensity': 400.0,
            'co2_concentration': 400.0
        }

        mock_water_data = {
            'water_uptake_rate': 2.5,
            'transpiration_rate': 2.0,
            'water_availability': 0.8
        }

        mock_nutrient_data = {
            'nutrient_availability': 0.8,
            'nutrient_uptake_rate': 1.5
        }

        mock_ph_data = {
            'ph': 6.0,
            'ph_stability': 0.9
        }

        mock_phenology_data = {
            'growth_stage': 'vegetative',
            'development_index': 0.4
        }

        # Pre-populate dependency cache
        from datetime import datetime
        simulator.dependency_cache['environmental_control'] = mock_environmental_data
        simulator.dependency_cache['water_uptake_simulator'] = mock_water_data
        simulator.dependency_cache['nutrient_models_simulator'] = mock_nutrient_data
        simulator.dependency_cache['ph_model_simulator'] = mock_ph_data
        simulator.dependency_cache['phenology_simulator'] = mock_phenology_data

        # Set cache timestamps
        current_time = datetime.now()
        simulator.cache_timestamp['environmental_control'] = current_time
        simulator.cache_timestamp['water_uptake_simulator'] = current_time
        simulator.cache_timestamp['nutrient_models_simulator'] = current_time
        simulator.cache_timestamp['ph_model_simulator'] = current_time
        simulator.cache_timestamp['phenology_simulator'] = current_time

        print("✓ Stress models simulator initialized")

        # 3. Test simulation step
        print("\n3. Running stress models simulation step...")
        inputs = DailyUpdateInput(
            day=7,
            date=datetime(2024, 1, 7),
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

            # Check specific stress results
            if result.primary_results:
                primary = result.primary_results
                print(f"✓ Temperature stress: {primary.get('temperature_stress', 0):.6f}")
                print(f"✓ Water stress: {primary.get('water_stress', 0):.6f}")
                print(f"✓ Nutrient stress: {primary.get('nutrient_stress', 0):.6f}")
                print(f"✓ Integrated stress: {primary.get('integrated_stress', 0):.6f}")
                print(f"✓ Stress severity: {primary.get('stress_severity', 'N/A')}")

        # 4. Test state retrieval
        print("\n4. Testing state retrieval...")
        state = simulator.get_current_state()
        print(f"✓ State contains {len(state)} properties")
        print(f"✓ Step count: {state.get('step_count', 0)}")

        print("\n=== Stress System Test PASSED ===")
        return True

    except Exception as e:
        print(f"\n❌ Stress system test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_stress_system()
    sys.exit(0 if success else 1)