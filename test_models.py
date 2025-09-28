#!/usr/bin/env python3
"""
Model Test Harness - Test individual models for realistic outputs
Goal: Ensure each model produces biologically realistic values using existing CSV parameters
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Change to src directory for imports
src_dir = os.path.join(project_root, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from cropgro_hydroponic_simulator import StrictParameterLoader

def test_photosynthesis_model():
    """Test photosynthesis model for realistic assimilation rates"""
    print("\n=== Testing Photosynthesis Model ===")

    try:
        from models.photosynthesis_model import PhotosynthesisModel

        # Load parameters from existing CSV
        param_loader = StrictParameterLoader("input/master_parameters.csv")
        photo_params = param_loader.create_photosynthesis_parameters()
        model = PhotosynthesisModel(photo_params)
        print("✅ Model loaded successfully")

        # Test scenarios using existing parameter ranges
        scenarios = [
            {
                "name": "Typical Day",
                "par_umol_m2_s": 1200,
                "co2_ppm": 800,
                "temp_c": 22,
                "humidity": 65,
                "lai": 1.0,
                "ec_factor": 1.0,
                "sunlit_lai": 0.6,
                "shaded_lai": 0.4
            },
            {
                "name": "Low Light",
                "par_umol_m2_s": 400,
                "co2_ppm": 400,
                "temp_c": 20,
                "humidity": 70,
                "lai": 0.5,
                "ec_factor": 1.0,
                "sunlit_lai": 0.3,
                "shaded_lai": 0.2
            },
            {
                "name": "High Light",
                "par_umol_m2_s": 1800,
                "co2_ppm": 1200,
                "temp_c": 25,
                "humidity": 60,
                "lai": 2.0,
                "ec_factor": 1.0,
                "sunlit_lai": 1.2,
                "shaded_lai": 0.8
            }
        ]

        for scenario in scenarios:
            print(f"\n--- {scenario['name']} ---")

            # Create config from existing parameters
            config = {
                'optimal_temp_min': param_loader.get_parameter('optimal_temp_min'),
                'optimal_temp_max': param_loader.get_parameter('optimal_temp_max'),
                'light_saturation': param_loader.get_parameter('light_saturation'),
                'optimal_vpd': param_loader.get_parameter('optimal_vpd'),
                'vpd_decline_rate': param_loader.get_parameter('vpd_decline_rate')
            }

            # Test the model
            photoperiod = param_loader.get_parameter('photoperiod_hours')
            inputs = {k: v for k, v in scenario.items() if k != 'name'}

            try:
                response = model.calculate_daily_assimilation(
                    photoperiod_hours=photoperiod,
                    config=config,
                    **inputs
                )

                assimilation = response.daily_assimilation
                print(f"  Daily assimilation: {assimilation:.3f} g C/m²/day")

                # Validation checks for realism
                if assimilation < 0:
                    print("  ❌ ISSUE: Negative assimilation")
                elif assimilation > 50:  # Unrealistically high for lettuce
                    print("  ⚠️  WARNING: Very high assimilation rate")
                elif assimilation < 0.1 and scenario['par_umol_m2_s'] > 800:  # Too low for good light
                    print("  ⚠️  WARNING: Very low assimilation despite good light")
                else:
                    print("  ✅ Realistic assimilation rate")

            except Exception as e:
                print(f"  ❌ ERROR: {e}")

    except Exception as e:
        print(f"❌ Model loading failed: {e}")

def test_respiration_model():
    """Test respiration model for realistic respiration rates"""
    print("\n=== Testing Respiration Model ===")

    try:
        from models.respiration_model import EnhancedRespirationModel, BiomassPool, TissueType

        param_loader = StrictParameterLoader("input/master_parameters.csv")
        resp_params = param_loader.create_respiration_parameters()
        model = EnhancedRespirationModel(resp_params)
        print("✅ Model loaded successfully")

        # Create test biomass pools
        leaf_pool = BiomassPool(
            total_mass=param_loader.get_parameter('initial_leaf_biomass'),
            structural_fraction=0.7,
            metabolic_fraction=0.3,
            tissue_type=TissueType.LEAF,
            age_days=10.0,
            temperature_history=[22.0] * 24
        )

        stem_pool = BiomassPool(
            total_mass=param_loader.get_parameter('initial_stem_biomass'),
            structural_fraction=0.8,
            metabolic_fraction=0.2,
            tissue_type=TissueType.STEM,
            age_days=15.0,
            temperature_history=[22.0] * 24
        )

        root_pool = BiomassPool(
            total_mass=param_loader.get_parameter('initial_root_biomass'),
            structural_fraction=0.6,
            metabolic_fraction=0.4,
            tissue_type=TissueType.ROOT,
            age_days=20.0,
            temperature_history=[22.0] * 24
        )

        biomass_pools = [leaf_pool, stem_pool, root_pool]

        # Test scenarios
        scenarios = [
            {"name": "Optimal Temp", "temperature": 22.0, "growth_rate": 5.0},
            {"name": "Cool Temp", "temperature": 15.0, "growth_rate": 2.0},
            {"name": "Warm Temp", "temperature": 30.0, "growth_rate": 3.0}
        ]

        for scenario in scenarios:
            print(f"\n--- {scenario['name']} ---")

            try:
                response = model.calculate_respiration(
                    biomass_pools=biomass_pools,
                    temperature=scenario['temperature'],
                    daily_growth_rate=scenario['growth_rate'],
                    stress_factors={'temperature': 0.0, 'water': 0.0, 'nutrient': 0.0},
                    n_concentration=param_loader.get_parameter('initial_n_content'),
                    day_length_hours=param_loader.get_parameter('photoperiod_hours')
                )

                total_resp = response.total_respiration_g_C_per_hour
                maintenance = response.maintenance_respiration_g_C_per_hour
                growth = response.growth_respiration_g_C_per_hour

                print(f"  Total respiration: {total_resp:.4f} g C/hour")
                print(f"  Maintenance: {maintenance:.4f} g C/hour")
                print(f"  Growth: {growth:.4f} g C/hour")

                # Validation checks
                if total_resp <= 0:
                    print("  ❌ ISSUE: Zero or negative respiration")
                elif total_resp > 1.0:  # Unrealistically high
                    print("  ⚠️  WARNING: Very high respiration rate")
                elif maintenance <= 0:
                    print("  ❌ ISSUE: Zero maintenance respiration")
                else:
                    print("  ✅ Realistic respiration rates")

            except Exception as e:
                print(f"  ❌ ERROR: {e}")

    except Exception as e:
        print(f"❌ Model loading failed: {e}")

def test_water_uptake_model():
    """Test water uptake model for realistic uptake rates"""
    print("\n=== Testing Water Uptake Model ===")

    try:
        from models.water_uptake_model import WaterUptakeModel

        param_loader = StrictParameterLoader("input/master_parameters.csv")
        water_params = param_loader.create_water_uptake_parameters()
        model = WaterUptakeModel(water_params)
        print("✅ Model loaded successfully")

        # Test scenarios
        scenarios = [
            {
                "name": "Normal Conditions",
                "lai": 1.0,
                "radiation": 1200,
                "temperature": 22,
                "humidity": 65,
                "wind_speed": 1.0
            },
            {
                "name": "High Demand",
                "lai": 2.0,
                "radiation": 1800,
                "temperature": 28,
                "humidity": 45,
                "wind_speed": 2.0
            },
            {
                "name": "Low Demand",
                "lai": 0.5,
                "radiation": 400,
                "temperature": 18,
                "humidity": 80,
                "wind_speed": 0.5
            }
        ]

        for scenario in scenarios:
            print(f"\n--- {scenario['name']} ---")

            try:
                response = model.calculate_realistic_water_uptake(
                    transpiration_input={
                        'lai': scenario['lai'],
                        'radiation': scenario['radiation'],
                        'temperature': scenario['temperature'],
                        'humidity': scenario['humidity'],
                        'wind_speed': scenario['wind_speed']
                    },
                    root_properties={
                        'root_biomass': param_loader.get_parameter('initial_root_biomass'),
                        'root_length_density': param_loader.get_parameter('root_length_density'),
                        'hydraulic_conductance': param_loader.get_parameter('hydraulic_conductance')
                    },
                    solution_properties={
                        'ec': param_loader.get_parameter('optimal_ec'),
                        'temperature': param_loader.get_parameter('initial_solution_temperature')
                    },
                    stress_factors={'water': 0.0, 'salinity': 0.0}
                )

                uptake = response.total_water_uptake_L
                transpiration = response.transpiration_L

                print(f"  Water uptake: {uptake:.4f} L/day")
                print(f"  Transpiration: {transpiration:.4f} L/day")

                # Validation checks for lettuce plant
                if uptake < 0:
                    print("  ❌ ISSUE: Negative water uptake")
                elif uptake > 5.0:  # Unrealistically high for small lettuce
                    print("  ⚠️  WARNING: Very high water uptake")
                elif uptake < 0.01 and scenario['lai'] > 0.5:  # Too low for established plant
                    print("  ⚠️  WARNING: Very low water uptake")
                else:
                    print("  ✅ Realistic water uptake")

            except Exception as e:
                print(f"  ❌ ERROR: {e}")

    except Exception as e:
        print(f"❌ Model loading failed: {e}")

def test_nutrient_model():
    """Test nutrient model for realistic uptake rates"""
    print("\n=== Testing Nutrient Model ===")

    try:
        from models.nutrient_models import NutrientModel

        param_loader = StrictParameterLoader("input/master_parameters.csv")
        nutrient_params = param_loader.create_nutrient_parameters()
        model = NutrientModel(nutrient_params)
        print("✅ Model loaded successfully")

        # Create test inputs
        concentrations = {
            'N-NO3': param_loader.get_parameter('initial_n_no3_conc'),
            'N-NH4': param_loader.get_parameter('initial_n_nh4_conc'),
            'P-PO4': param_loader.get_parameter('initial_p_po4_conc'),
            'K': param_loader.get_parameter('initial_k_conc')
        }

        plant_status = {
            'root_surface_area': param_loader.get_parameter('initial_root_biomass') * param_loader.get_parameter('root_specific_area'),
            'tank_volume_L': param_loader.get_parameter('tank_volume_L'),
            'plant_count': param_loader.get_parameter('plant_count'),
            'daily_growth_rate': 2.0,
            'growth_stage': 'vegetative',
            'stress_factors': {'temperature': 0.0, 'water': 0.0}
        }

        env_conditions = {
            'temperature': param_loader.get_parameter('initial_solution_temperature'),
            'ph': param_loader.get_parameter('initial_ph'),
            'optimal_ec': param_loader.get_parameter('optimal_ec')
        }

        organ_demands = {
            'leaves': {'nitrogen': 1.0, 'phosphorus': 0.2, 'potassium': 1.5},
            'roots': {'nitrogen': 0.5, 'phosphorus': 0.1, 'potassium': 0.8}
        }

        try:
            response = model.calculate_nutrient_dynamics(
                concentrations=concentrations,
                plant_status=plant_status,
                env_conditions=env_conditions,
                organ_demands=organ_demands,
                water_fluxes={'transpiration': 0.5},
                assimilate_fluxes={'photosynthesis': 10.0}
            )

            uptake_rates = response['uptake_rates_mg_per_plant_per_day']

            print(f"  N-NO3 uptake: {uptake_rates.get('N-NO3', 0):.3f} mg/day")
            print(f"  P-PO4 uptake: {uptake_rates.get('P-PO4', 0):.3f} mg/day")
            print(f"  K uptake: {uptake_rates.get('K', 0):.3f} mg/day")

            # Validation checks
            k_uptake = uptake_rates.get('K', 0)
            n_uptake = uptake_rates.get('N-NO3', 0) + uptake_rates.get('N-NH4', 0)

            if k_uptake < 0:
                print("  ❌ ISSUE: Negative K uptake")
            elif k_uptake > 100:  # Unrealistically high
                print("  ⚠️  WARNING: Very high K uptake")
            elif n_uptake < 0:
                print("  ❌ ISSUE: Negative N uptake")
            else:
                print("  ✅ Realistic nutrient uptake rates")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")

    except Exception as e:
        print(f"❌ Model loading failed: {e}")

def run_all_tests():
    """Run all model tests"""
    print("🧪 Starting Model Validation Tests")
    print("Goal: Verify each model produces biologically realistic outputs")

    test_photosynthesis_model()
    test_respiration_model()
    test_water_uptake_model()
    test_nutrient_model()

    print("\n🏁 Testing Complete!")
    print("Next step: Run full simulation and check final CSV for realistic values")

if __name__ == "__main__":
    run_all_tests()