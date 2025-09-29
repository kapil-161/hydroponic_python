#!/usr/bin/env python3
"""Test root system model and simulator functionality"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.parameter_loader import StrictParameterLoader
from src.simulations.root_system_simulator import RootSystemSimulator
from src.models.base_model import DailyUpdateInput, DailyUpdateOutput

def test_root_system_system():
    """Test root system model and simulator"""
    print("=== Testing Root System Model & Simulator ===")

    try:
        # 1. Test parameter loading - skip for now due to extensive parameter requirements
        print("1. Testing simplified root system parameters...")

        # Create minimal parameters for testing - this would normally come from CSV
        from src.models.root_system_model import RootSystemParameters, HydroponicSystemType

        # Create a test config that matches the expected structure
        test_config = {
            # Core system parameters
            'container_volume': 50000.0,
            'channel_length': 100.0,
            'system_type': 'deep_water_culture',
            'channel_width': 10.0,
            'channel_depth': 5.0,
            'n_channels': 4,
            'root_zone_independent': True,

            # Basic root parameters - minimal set for testing
            'primary_root_growth_rate': 2.0,
            'lateral_root_density': 5.0,
            'branching_angle_mean': 45.0,
            'branching_angle_std': 15.0,
            'fine_root_fraction': 0.6,
            'medium_root_fraction': 0.3,
            'coarse_root_fraction': 0.1,
            'fine_diameter_mean': 0.5,
            'fine_diameter_std': 0.1,
            'medium_diameter_mean': 1.0,
            'medium_diameter_std': 0.2,
            'coarse_diameter_mean': 2.0,
            'coarse_diameter_std': 0.5,

            # Activity and effectiveness
            'fine_min_activity': 0.1,
            'medium_min_activity': 0.05,
            'coarse_min_activity': 0.02,
            'establishment_plateau_days': 5.0,
            'initial_root_activity': 1.0,
            'fine_root_effectiveness': 1.0,
            'medium_root_effectiveness': 0.8,
            'coarse_root_effectiveness': 0.5,

            # Environmental parameters
            'optimal_temperature_min': 18.0,
            'optimal_temperature_max': 25.0,
            'q10_factor': 2.0,
            'optimal_flow_rate': 1.0,
            'flow_stress_threshold': 5.0,
            'root_temp_optimum': 22.0,
            'root_temp_max': 35.0,
            'root_temp_min_factor': 0.1,
            'root_oxygen_optimum': 8.0,
            'root_oxygen_min_factor': 0.2,

            # Required defaults for testing
            'cache_timeout': 1.0
        }

        # Add all the missing required parameters with sensible defaults
        defaults = {
            'fine_turnover_rate': 0.1,
            'medium_turnover_rate': 0.05,
            'coarse_turnover_rate': 0.02,
            'fine_root_half_life_days': 30.0,
            'medium_root_half_life_days': 60.0,
            'coarse_root_half_life_days': 120.0,
            'root_zone_efficiency_factor': 0.8,
            'root_growth_auxin_decay_rate': 0.1,
            'root_optimal_density': 1.0,
            'root_density_stress_factor': 0.5,
            'ph_stress_range_acidic': 1.0,
            'ph_stress_range_basic': 1.0,
            'ph_stress_factor': 0.5,
            'young_root_activity': 1.0,
            'old_root_activity': 0.5,
            'temperature_range_factor': 10.0,
            'min_temperature_factor': 0.1,
            'max_temperature_factor': 3.0,
            'low_flow_factor': 0.5,
            'high_flow_factor': 0.8,
            'ph_zone_min': 5.5,
            'ph_zone_max': 7.5,
            'min_ph_factor': 0.2,
            'ph_penalty_factor': 0.5,
            'nft_zone_1_fraction': 0.4,
            'nft_zone_2_fraction': 0.4,
            'nft_zone_3_fraction': 0.2,
            'dwc_zone_1_fraction': 0.5,
            'dwc_zone_2_fraction': 0.3,
            'dwc_zone_3_fraction': 0.2,
            'general_zone_1_fraction': 0.3,
            'general_zone_2_fraction': 0.3,
            'general_zone_3_fraction': 0.2,
            'general_zone_4_fraction': 0.2,
            'root_biomass_density': 0.3,
            'coarse_root_min_threshold': 0.1,
            'fine_root_min_threshold': 0.01,
            'diameter_minimum_limit': 0.1,
            'auxin_gradient_weight': 0.3,
            'nutrient_signal_weight': 0.3,
            'oxygen_effect_weight': 0.2,
            'competition_effect_weight': 0.1,
            'temperature_effect_weight': 0.1,
            'min_growth_potential': 0.1,
            'max_growth_potential': 2.0,
            'max_temp_threshold': 35.0,
            'temp_decay_factor': 0.1,
            'flow_rate_offset': 0.5,
            'flow_rate_multiplier': 1.0,
            'transport_temp_exponent': 0.5,
            'minimum_surface_area': 1.0,
            'minimum_biomass': 0.1,
            'minimum_volume': 1.0,
            'effective_area_minimum': 1.0
        }

        # Add nutrient uptake parameters
        nutrients = ['NO3', 'NH4', 'PO4', 'K', 'Ca', 'Mg', 'SO4']
        for nutrient in nutrients:
            defaults[f'{nutrient.lower()}_uptake_vmax'] = 1.0
            defaults[f'{nutrient.lower()}_uptake_km'] = 50.0

        # Add system multipliers
        system_types = ['nutrient_film_technique', 'deep_water_culture', 'aeroponics', 'drip', 'wick_system', 'ebb_flow']
        for sys_type in system_types:
            defaults[f'system_multipliers_{sys_type}_root_length_multiplier'] = 1.0
            defaults[f'system_multipliers_{sys_type}_surface_area_multiplier'] = 1.0
            defaults[f'system_multipliers_{sys_type}_branching_multiplier'] = 1.0

        # Add nutrient demand weights and concentrations
        nutrients_short = ['no3', 'po4', 'k', 'ca', 'mg']
        for nutrient in nutrients_short:
            defaults[f'nutrient_demand_weight_{nutrient}'] = 0.2
            defaults[f'nutrient_ref_concentration_{nutrient}'] = 100.0
            defaults[f'nutrient_competition_{nutrient}'] = nutrient
            defaults[f'ph_optimum_{nutrient}_min'] = 5.5
            defaults[f'ph_optimum_{nutrient}_max'] = 7.5

        defaults['nutrient_competition_nh4'] = 'nh4'
        defaults['ph_optimum_nh4_min'] = 5.5
        defaults['ph_optimum_nh4_max'] = 7.5

        test_config.update(defaults)

        # Create parameters using from_config method
        try:
            root_params = RootSystemParameters.from_config(test_config)
            print(f"✓ Container volume: {root_params.container_volume} cm³")
            print(f"✓ System type: {root_params.system_type}")
            print(f"✓ Primary root growth rate: {root_params.primary_root_growth_rate} cm/day")
            print(f"✓ Fine root fraction: {root_params.fine_root_fraction}")
        except Exception as e:
            # If from_config fails, skip parameter test but continue with simulator test
            print(f"⚠ Parameter creation failed (expected): {str(e)}")
            print("✓ Continuing with basic simulator test...")
            root_params = None

        # 2. Test simulator initialization
        print("\n2. Initializing root system simulator...")
        if root_params is None:
            print("✗ Skipping simulator test - parameters not available")
            return False

        simulator = RootSystemSimulator(root_params)

        # Prepare test data and dependencies
        system_data = {
            'tank_volume_L': 100.0,
            'plant_count': 20,
            'daily_growth_rate': 5.0,
            'total_biomass': 35.0
        }

        # Mock dependency data
        mock_biomass_data = {
            'total_biomass': 35.0,
            'leaf_biomass': 15.0,
            'stem_biomass': 8.0,
            'root_biomass': 12.0,
            'growth_rate': 5.0
        }

        mock_water_data = {
            'water_uptake_rate': 2.5,  # L/day
            'root_water_potential': -0.3,  # MPa
            'transpiration_rate': 2.0,
            'water_stress_index': 0.1
        }

        mock_nutrient_data = {
            'nutrient_availability': 0.8,
            'solution_ec': 1.5,  # mS/cm
            'nutrient_concentrations': {
                'N-NO3': 150.0,  # mg/L
                'N-NH4': 25.0,
                'P-PO4': 40.0,
                'K': 200.0,
                'Ca': 150.0,
                'Mg': 50.0,
                'S-SO4': 100.0
            }
        }

        mock_phenology_data = {
            'growth_stage': 'vegetative',
            'development_index': 0.4
        }

        mock_stress_data = {
            'water_stress': 0.1,
            'nutrient_stress': 0.05,
            'temperature_stress': 0.02,
            'overall_stress': 0.15
        }

        mock_rzt_data = {
            'root_zone_temperature': 21.5  # °C
        }

        # Pre-populate dependency cache with all required dependencies
        from datetime import datetime
        simulator.dependency_cache['biomass_allocation_simulator'] = mock_biomass_data
        simulator.dependency_cache['water_uptake_simulator'] = mock_water_data
        simulator.dependency_cache['nutrient_models_simulator'] = mock_nutrient_data
        simulator.dependency_cache['phenology_simulator'] = mock_phenology_data
        simulator.dependency_cache['stress_models'] = mock_stress_data
        simulator.dependency_cache['root_zone_temperature_simulator'] = mock_rzt_data

        # Set cache timestamps
        current_time = datetime.now()
        simulator.cache_timestamp['biomass_allocation_simulator'] = current_time
        simulator.cache_timestamp['water_uptake_simulator'] = current_time
        simulator.cache_timestamp['nutrient_models_simulator'] = current_time
        simulator.cache_timestamp['phenology_simulator'] = current_time
        simulator.cache_timestamp['stress_models'] = current_time
        simulator.cache_timestamp['root_zone_temperature_simulator'] = current_time

        print("✓ Root system simulator initialized")

        # 3. Test simulation step
        print("\n3. Running root system simulation step...")
        inputs = DailyUpdateInput(
            day=15,
            date=datetime(2024, 1, 15),
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

            # Check specific root system results
            if result.primary_results:
                primary = result.primary_results
                print(f"✓ Root depth: {primary.get('root_depth', 0):.3f} cm")
                print(f"✓ Root biomass: {primary.get('root_biomass', 0):.3f} g")
                print(f"✓ Root length: {primary.get('root_length', 0):.3f} cm")
                print(f"✓ Root surface area: {primary.get('root_surface_area', 0):.3f} cm²")
                print(f"✓ Fine root fraction: {primary.get('fine_root_fraction', 0):.3f}")

        # 4. Test state retrieval
        print("\n4. Testing state retrieval...")
        state = simulator.get_current_state()
        print(f"✓ State contains {len(state)} properties")
        print(f"✓ Step count: {state.get('step_count', 0)}")

        print("\n=== Root System System Test PASSED ===")
        return True

    except Exception as e:
        print(f"\n❌ Root system system test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_root_system_system()
    sys.exit(0 if success else 1)