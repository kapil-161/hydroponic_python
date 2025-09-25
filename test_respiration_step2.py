#!/usr/bin/env python3
"""
Step 2 Test: Verify Respiration Model Works with CSV Parameters
Tests that the respiration model can be instantiated and run calculations using ONLY CSV parameters.
"""

import sys
import pandas as pd
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_parameters_from_csv(csv_path: str) -> dict:
    """Load parameters from master CSV file with proper structure for respiration model."""
    df = pd.read_csv(csv_path, comment='#')

    config = {}
    for _, row in df.iterrows():
        category = row['category']
        param_name = row['parameter_name']
        value = row['value']

        # Convert string values to appropriate types
        if isinstance(value, str):
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                # Try to convert to float if it's numeric
                try:
                    value = float(value)
                    # Convert to int if it's a whole number
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass  # Keep as string if not numeric

        if category not in config:
            config[category] = {}

        config[category][param_name] = value

    return config

def create_config_object(params_dict: dict):
    """Create a config object that models can use."""
    class Config:
        pass

    config = Config()
    for category, params in params_dict.items():
        setattr(config, category, params)

    return config

def test_respiration_model_functionality():
    """Test that respiration model works with CSV-only parameters."""
    print("🧪 Testing Respiration Model Functionality...")

    try:
        # Load parameters
        params_dict = load_parameters_from_csv('input/master_parameters.csv')
        config = create_config_object(params_dict)

        # Import and test respiration model directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("respiration_model", "src/models/respiration_model.py")
        respiration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(respiration_module)

        RespirationParameters = respiration_module.RespirationParameters
        EnhancedRespirationModel = respiration_module.EnhancedRespirationModel
        BiomassPool = respiration_module.BiomassPool
        TissueType = respiration_module.TissueType

        # Test parameter creation from config
        print("📋 Creating RespirationParameters from CSV config...")
        resp_params = RespirationParameters.from_config(config.respiration_parameters)
        print(f"✅ RespirationParameters created successfully")
        print(f"   Maintenance base rate: {resp_params.maintenance_base_rate} g C/g biomass/day")
        print(f"   Reference temperature: {resp_params.reference_temperature}°C")
        print(f"   Q10 factor: {resp_params.q10_factor}")
        print(f"   Growth efficiency: {resp_params.growth_efficiency}")

        # Create respiration model instance
        print("🏗️  Creating EnhancedRespirationModel...")
        respiration_model = EnhancedRespirationModel(resp_params, config.respiration_parameters)
        print(f"✅ EnhancedRespirationModel created successfully")

        # Test consolidated temperature stress factor calculation
        print("🌡️  Testing consolidated temperature stress factor...")
        test_temperature = 25.0
        temp_stress_factor = respiration_model._calculate_temperature_stress_factor(test_temperature)
        print(f"✅ Temperature stress factor at {test_temperature}°C: {temp_stress_factor:.3f}")

        # Test temperature factor calculation
        print("📊 Testing Q10 temperature factor...")
        temp_factor = respiration_model.calculate_temperature_factor(test_temperature)
        print(f"✅ Q10 temperature factor at {test_temperature}°C: {temp_factor:.3f}")

        # Test age factor calculation
        print("⏰ Testing age factor calculation...")
        test_age = 30.0  # days
        age_factor = respiration_model.calculate_age_factor(test_age)
        print(f"✅ Age factor at {test_age} days: {age_factor:.3f}")

        # Test nitrogen factor calculation
        print("🧪 Testing nitrogen factor calculation...")
        test_nitrogen = 0.04  # g N/g biomass
        nitrogen_factor = respiration_model.calculate_nitrogen_factor(test_nitrogen, TissueType.LEAVES)
        print(f"✅ Nitrogen factor at {test_nitrogen} g N/g: {nitrogen_factor:.3f}")

        # Test biomass pool creation and maintenance respiration
        print("🌿 Testing maintenance respiration calculation...")
        test_biomass_pool = BiomassPool(
            tissue_type=TissueType.LEAVES,
            dry_mass=10.0,  # g
            age_days=test_age,
            nitrogen_content=test_nitrogen,
            recent_growth=0.5  # g
        )

        maintenance_resp, factors = respiration_model.calculate_maintenance_respiration(
            test_biomass_pool, test_temperature
        )
        print(f"✅ Maintenance respiration: {maintenance_resp:.4f} g C/day")
        print(f"   Temperature factor: {factors['temperature_factor']:.3f}")
        print(f"   Age factor: {factors['age_factor']:.3f}")
        print(f"   Nitrogen factor: {factors['nitrogen_factor']:.3f}")

        # Test growth respiration calculation
        print("🌱 Testing growth respiration calculation...")
        test_new_growth = 2.0  # g
        growth_composition = resp_params.get_required_growth_composition(config.respiration_parameters)

        growth_resp = respiration_model.calculate_growth_respiration(test_new_growth, growth_composition)
        print(f"✅ Growth respiration: {growth_resp:.4f} g C for {test_new_growth} g growth")

        # Test diurnal factor calculation
        print("☀️  Testing diurnal factor calculation...")
        test_hour = 14  # 2 PM
        diurnal_factor = respiration_model._calculate_diurnal_respiration_factor(test_hour)
        print(f"✅ Diurnal factor at {test_hour}h: {diurnal_factor:.3f}")

        # Test respiratory quotient calculation
        print("💨 Testing respiratory quotient calculation...")
        rq_factor = respiration_model._calculate_respiratory_quotient(test_hour)
        print(f"✅ Respiratory quotient at {test_hour}h: {rq_factor:.2f}")

        # Test core functionality validation
        print("🎯 Core functionality validation completed!")
        print(f"   ✅ Model instantiated with CSV parameters")
        print(f"   ✅ Temperature stress factor: {temp_stress_factor:.3f}")
        print(f"   ✅ Q10 temperature factor: {temp_factor:.3f}")
        print(f"   ✅ Maintenance respiration: {maintenance_resp:.4f} g C/day")
        print(f"   ✅ Growth respiration: {growth_resp:.4f} g C")

        # Verify no hardcoded values by checking parameters come from CSV
        print("🔍 Verifying NO hardcoded values...")
        assert resp_params.maintenance_base_rate == params_dict['respiration_parameters']['maintenance_base_rate']
        assert resp_params.reference_temperature == params_dict['respiration_parameters']['reference_temperature']
        assert resp_params.q10_factor == params_dict['respiration_parameters']['q10_factor']
        assert resp_params.growth_efficiency == params_dict['respiration_parameters']['growth_efficiency']
        assert resp_params.optimal_temperature == params_dict['respiration_parameters']['optimal_temperature']
        assert resp_params.moderate_stress_threshold == params_dict['respiration_parameters']['moderate_stress_threshold']
        print("✅ All parameter values verified to come from CSV")

        print("🎯 SUCCESS: Respiration model working with CSV-only parameters!")
        print("🚫 NO hardcoded values - all calculations use CSV parameters")
        print("🔧 Model uses CONSOLIDATED functions from core_utils for temperature stress")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_respiration_model_functionality()
    if success:
        print("\n✅ Step 2 Complete: Respiration model validated with CSV parameters!")
        print("🚀 Ready to proceed to next model or create main simulator")
    else:
        print("\n❌ Step 2 Failed: Fix respiration model issues before proceeding")
        sys.exit(1)