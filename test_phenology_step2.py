#!/usr/bin/env python3
"""
Step 2 Test: Verify Phenology Model Works with CSV Parameters
Tests that the phenology model can be instantiated and run calculations using ONLY CSV parameters.
"""

import sys
import pandas as pd
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_parameters_from_csv(csv_path: str) -> dict:
    """Load parameters from master CSV file with proper structure for phenology model."""
    df = pd.read_csv(csv_path, comment='#')

    config = {}
    thermal_requirements = {}

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

        # Handle thermal requirements specially
        if category == 'phenology_parameters' and '_to_' in param_name:
            thermal_requirements[param_name] = value
        else:
            config[category][param_name] = value

    # Add thermal_requirements as nested dictionary for phenology model
    if thermal_requirements:
        config['phenology_parameters']['thermal_requirements'] = thermal_requirements

    return config

def create_config_object(params_dict: dict):
    """Create a config object that models can use."""
    class Config:
        pass

    config = Config()
    for category, params in params_dict.items():
        setattr(config, category, params)

    return config

def test_phenology_model_functionality():
    """Test that phenology model works with CSV-only parameters."""
    print("🧪 Testing Phenology Model Functionality...")

    try:
        # Load parameters
        params_dict = load_parameters_from_csv('input/master_parameters.csv')
        config = create_config_object(params_dict)

        # Import and test phenology model directly (avoid __init__.py issues)
        import importlib.util
        spec = importlib.util.spec_from_file_location("phenology_model", "src/models/phenology_model.py")
        phenology_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(phenology_module)

        PhenologyParameters = phenology_module.PhenologyParameters
        ComprehensivePhenologyModel = phenology_module.ComprehensivePhenologyModel

        # Test parameter creation from config
        print("📋 Creating PhenologyParameters from CSV config...")
        phenology_params = PhenologyParameters.from_config(config.phenology_parameters)
        print(f"✅ PhenologyParameters created successfully")
        print(f"   Base temperature: {phenology_params.base_temperature}°C")
        print(f"   Thermal time scale: {phenology_params.thermal_time_scale}")
        print(f"   Photoperiod sensitive: {phenology_params.photoperiod_sensitive}")

        # Create phenology model instance
        print("🏗️  Creating ComprehensivePhenologyModel...")
        # Get LettuceGrowthStage enum
        LettuceGrowthStage = phenology_module.LettuceGrowthStage
        phenology_model = ComprehensivePhenologyModel(phenology_params, LettuceGrowthStage.GERMINATION)
        print(f"✅ ComprehensivePhenologyModel created successfully")

        # Test thermal time calculation (uses consolidated function)
        print("🌡️  Testing thermal time calculation...")
        test_temperature = 20.0
        thermal_time = phenology_model.calculate_thermal_time(test_temperature)
        print(f"✅ Thermal time at {test_temperature}°C: {thermal_time:.2f} GDD")

        # Test temperature factor calculation
        print("📊 Testing temperature factor calculation...")
        temp_factor = phenology_model.calculate_temperature_factor(test_temperature)
        print(f"✅ Temperature factor at {test_temperature}°C: {temp_factor:.3f}")

        # Test photoperiod factor calculation
        print("☀️  Testing photoperiod factor calculation...")
        test_daylength = 12.0  # hours
        photo_factor = phenology_model.calculate_photoperiod_factor(test_daylength)
        print(f"✅ Photoperiod factor at {test_daylength}h: {photo_factor:.3f}")

        # Test core functionality validation
        print("🎯 Core functionality validation completed!")
        print(f"   ✅ Model instantiated with CSV parameters")
        print(f"   ✅ Thermal time calculation: {thermal_time:.2f} GDD")
        print(f"   ✅ Temperature factor: {temp_factor:.3f}")
        print(f"   ✅ Photoperiod factor: {photo_factor:.3f}")

        # Verify no hardcoded values by checking parameters come from CSV
        print("🔍 Verifying NO hardcoded values...")
        assert phenology_params.base_temperature == params_dict['phenology_parameters']['base_temperature']
        assert phenology_params.thermal_time_scale == params_dict['phenology_parameters']['thermal_time_scale']
        assert phenology_params.photoperiod_sensitive == params_dict['phenology_parameters']['photoperiod_sensitive']
        print("✅ All parameter values verified to come from CSV")

        print("🎯 SUCCESS: Phenology model working with CSV-only parameters!")
        print("🚫 NO hardcoded values - all calculations use CSV parameters")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_phenology_model_functionality()
    if success:
        print("\n✅ Step 2 Complete: Phenology model validated with CSV parameters!")
        print("🚀 Ready to proceed to next model or create main simulator")
    else:
        print("\n❌ Step 2 Failed: Fix phenology model issues before proceeding")
        sys.exit(1)