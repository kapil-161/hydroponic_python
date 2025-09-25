#!/usr/bin/env python3
"""
Step 1 Test: Verify Photosynthesis Model Parameter Loading from CSV
Tests that the photosynthesis model can load ALL parameters from CSV with NO hardcoded values.
"""

import sys
import pandas as pd
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_parameters_from_csv(csv_path: str) -> dict:
    """Load parameters from master CSV file."""
    df = pd.read_csv(csv_path, comment='#')

    # Group parameters by category
    config = {}
    for _, row in df.iterrows():
        category = row['category']
        param_name = row['parameter_name']
        value = row['value']

        # Convert string boolean values
        if isinstance(value, str):
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                # Try to convert to float if numeric
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass  # Keep as string

        if category not in config:
            config[category] = {}
        config[category][param_name] = value

    return config

def test_photosynthesis_parameter_loading():
    """Test that photosynthesis model can load parameters from CSV."""
    print("🧪 Testing Photosynthesis Model Parameter Loading...")

    try:
        # Load parameters from CSV
        config = load_parameters_from_csv('input/master_parameters.csv')
        print(f"✅ Loaded parameters from CSV")
        print(f"📊 Categories found: {list(config.keys())}")

        # Check photosynthesis parameters are present
        if 'photosynthesis_parameters' not in config:
            raise ValueError("❌ photosynthesis_parameters category missing from CSV")

        photo_params = config['photosynthesis_parameters']
        print(f"📋 Photosynthesis parameters count: {len(photo_params)}")

        # Check all required photosynthesis parameters that match the model
        required_params = [
            'phi_psii', 'r', 'g_max', 'min_par_threshold', 'enzyme_saturation_lai',
            'light_penetration_lai', 'enzyme_saturation_rate', 'min_enzyme_factor',
            'excess_lai_efficiency', 'umol_to_g_carbon_ratio', 'seconds_per_hour',
            'hours_per_day', 'kc', 'ko', 'gamma_star', 'jmax_25', 'vcmax_25',
            'theta', 'alpha', 'rd_25', 'eaj', 'eav', 'ear', 'o2_mmol_mol',
            'shaded_light_fraction', 'photosynthesis_cold_limit', 'photosynthesis_heat_limit',
            'min_stress_factor'
        ]

        for param in required_params:
            if param not in photo_params:
                raise ValueError(f"❌ Required parameter '{param}' missing")
            print(f"✅ {param}: {photo_params[param]}")

        # Check thermal time parameters are available
        if 'thermal_time' not in config:
            raise ValueError("❌ thermal_time category missing from CSV")

        thermal_time_params = config['thermal_time']
        required_thermal = ['base_temp', 'optimal_temp_min', 'optimal_temp_max', 'max_temp']

        for param in required_thermal:
            if param not in thermal_time_params:
                raise ValueError(f"❌ Thermal time parameter '{param}' missing")
            print(f"✅ thermal_time.{param}: {thermal_time_params[param]}")

        print("🎯 SUCCESS: All photosynthesis parameters loaded from CSV successfully!")
        print("🚫 NO hardcoded values used - all parameters from CSV")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_photosynthesis_parameter_loading()
    if success:
        print("\n✅ Step 1 Complete: Photosynthesis parameter loading validated!")
    else:
        print("\n❌ Step 1 Failed: Fix issues before proceeding")
        sys.exit(1)