#!/usr/bin/env python3
"""Test senescence model and simulator functionality"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.parameter_loader import StrictParameterLoader
from src.simulations.senescence_simulator import SenescenceSimulator
from src.models.base_model import DailyUpdateInput, DailyUpdateOutput

def test_senescence_system():
    """Test senescence model and simulator"""
    print("=== Testing Senescence Model & Simulator ===")

    try:
        # 1. Test parameter loading
        print("1. Loading parameters from CSV...")
        loader = StrictParameterLoader("input/master_parameters.csv")
        senescence_params = loader.create_senescence_parameters()
        print(f"✓ Natural lifespan GDD: {getattr(senescence_params, 'natural_lifespan_gdd', 'N/A')}")
        print(f"✓ Age senescence rate: {getattr(senescence_params, 'age_senescence_rate', 'N/A')}")
        print(f"✓ Water stress threshold: {getattr(senescence_params, 'water_stress_threshold', 'N/A')}")

        # 2. Test simulator initialization
        print("\n2. Initializing senescence simulator...")
        simulator = SenescenceSimulator(senescence_params)

        # Prepare test data and dependencies
        system_data = {
            'tank_volume_L': 100.0,
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
            'light_stress': 0.1
        }

        mock_leaf_data = {
            'leaf_age_distribution': [0.2, 0.3, 0.3, 0.2],
            'leaf_senescence_rate': 0.02
        }

        mock_biomass_data = {
            'leaf_biomass': 15.0,
            'total_biomass': 35.0
        }

        mock_nitrogen_data = {
            'nitrogen_remobilization_rate': 0.1,
            'nitrogen_stress_index': 0.15
        }

        mock_environmental_data = {
            'temperature': 22.0,
            'humidity': 65.0,
            'light_intensity': 400.0
        }

        # Pre-populate dependency cache
        from datetime import datetime
        simulator.dependency_cache['phenology_simulator'] = mock_phenology_data
        simulator.dependency_cache['stress_models'] = mock_stress_data
        simulator.dependency_cache['leaf_development_simulator'] = mock_leaf_data
        simulator.dependency_cache['biomass_allocation_simulator'] = mock_biomass_data
        simulator.dependency_cache['nitrogen_balance_simulator'] = mock_nitrogen_data
        simulator.dependency_cache['environmental_control'] = mock_environmental_data

        # Set cache timestamps
        current_time = datetime.now()
        simulator.cache_timestamp['phenology_simulator'] = current_time
        simulator.cache_timestamp['stress_models'] = current_time
        simulator.cache_timestamp['leaf_development_simulator'] = current_time
        simulator.cache_timestamp['biomass_allocation_simulator'] = current_time
        simulator.cache_timestamp['nitrogen_balance_simulator'] = current_time
        simulator.cache_timestamp['environmental_control'] = current_time

        print("✓ Senescence simulator initialized")

        # 3. Test simulation step
        print("\n3. Running senescence simulation step...")
        inputs = DailyUpdateInput(
            day=12,
            date=datetime(2024, 1, 12),
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

            # Check specific senescence results
            if result.primary_results:
                primary = result.primary_results
                print(f"✓ Total senescence rate: {primary.get('total_senescence_rate', 0):.6f}")
                print(f"✓ Age senescence rate: {primary.get('age_senescence_rate', 0):.6f}")
                print(f"✓ Stress senescence rate: {primary.get('stress_senescence_rate', 0):.6f}")
                print(f"✓ Total remobilization rate: {primary.get('total_remobilization_rate', 0):.6f}")

        # 4. Test state retrieval
        print("\n4. Testing state retrieval...")
        state = simulator.get_current_state()
        print(f"✓ State contains {len(state)} properties")
        print(f"✓ Step count: {state.get('step_count', 0)}")

        print("\n=== Senescence System Test PASSED ===")
        return True

    except Exception as e:
        print(f"\n❌ Senescence system test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_senescence_system()
    sys.exit(0 if success else 1)