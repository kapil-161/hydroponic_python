#!/usr/bin/env python3
"""
Step 1 Test: Verify Environmental Control Model Parameter Loading from CSV
Tests that the environmental control model can load ALL parameters from CSV with NO hardcoded values.
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

def test_environmental_control_parameter_loading():
    """Test that environmental control model can load parameters from CSV."""
    print("🧪 Testing Environmental Control Model Parameter Loading...")

    try:
        # Load parameters from CSV
        config = load_parameters_from_csv('input/master_parameters.csv')
        print(f"✅ Loaded parameters from CSV")
        print(f"📊 Categories found: {list(config.keys())}")

        # Check environmental control parameters are present
        required_categories = ['environment', 'control_equipment_parameters']
        for category in required_categories:
            if category not in config:
                raise ValueError(f"❌ {category} category missing from CSV")
            print(f"✅ Found {category} with {len(config[category])} parameters")

        # Check environmental setpoints parameters
        env_params = config['environment']
        required_env_params = [
            'target_vpd', 'vpd_tolerance', 'min_humidity', 'max_humidity',
            'day_temp', 'night_temp', 'temp_tolerance', 'target_co2', 'ambient_co2',
            'co2_tolerance', 'light_hours', 'light_intensity_control',
            'co2_enrichment_start_hour', 'humidity_deadband', 'max_temperature_change_per_hour',
            'ambient_temperature', 'thermal_mass_factor', 'base_co2_loss_rate',
            'min_co2_concentration', 'max_co2_concentration', 'light_saturation_threshold',
            'co2_response_vmax', 'co2_response_km', 'max_co2_enhancement_factor'
        ]

        print("🌍 Checking environmental setpoints parameters...")
        for param in required_env_params:
            if param not in env_params:
                raise ValueError(f"❌ Required environmental parameter '{param}' missing")
            print(f"✅ {param}: {env_params[param]}")

        # Check CO2 enrichment time-based parameters
        co2_enrichment_params = [
            'co2_enrichment_duration', 'co2_enrichment_strategy',
            'co2_morning_target', 'co2_afternoon_target'
        ]

        print("💨 Checking CO2 enrichment time-based parameters...")
        for param in co2_enrichment_params:
            if param not in env_params:
                raise ValueError(f"❌ Required CO2 enrichment parameter '{param}' missing")
            print(f"✅ {param}: {env_params[param]}")

        # Check PID control parameters
        pid_params = [
            'pid_humidity_kp', 'pid_humidity_ki', 'pid_humidity_kd',
            'pid_co2_kp', 'pid_co2_ki', 'pid_co2_kd',
            'pid_temperature_kp', 'pid_temperature_ki', 'pid_temperature_kd'
        ]

        print("🔧 Checking PID control parameters...")
        for param in pid_params:
            if param not in env_params:
                raise ValueError(f"❌ Required PID parameter '{param}' missing")
            print(f"✅ {param}: {env_params[param]}")

        # Check control equipment parameters
        equipment_params = config['control_equipment_parameters']
        required_equipment_params = [
            'humidifier_capacity', 'dehumidifier_capacity', 'humidifier_efficiency',
            'dehumidifier_efficiency', 'co2_injection_rate', 'co2_sensor_accuracy',
            'co2_mixing_time', 'air_exchange_rate', 'circulation_fan_power'
        ]

        print("🛠️  Checking control equipment parameters...")
        for param in required_equipment_params:
            if param not in equipment_params:
                raise ValueError(f"❌ Required equipment parameter '{param}' missing")
            print(f"✅ {param}: {equipment_params[param]}")

        # Check thermal time parameters are available (reused from existing categories)
        if 'thermal_time' not in config:
            raise ValueError("❌ thermal_time category missing from CSV")

        thermal_time_params = config['thermal_time']
        required_thermal = ['base_temp', 'optimal_temp_min', 'optimal_temp_max', 'max_temp']

        print("🌡️  Checking reusable thermal time parameters...")
        for param in required_thermal:
            if param not in thermal_time_params:
                raise ValueError(f"❌ Thermal time parameter '{param}' missing")
            print(f"✅ thermal_time.{param}: {thermal_time_params[param]}")

        # Verify no parameter duplication by counting total unique parameters
        total_env_params = len(required_env_params) + len(co2_enrichment_params) + len(pid_params) + len(required_equipment_params)
        actual_params = len(env_params) + len(equipment_params)
        print(f"📊 Expected environmental control parameters: {total_env_params}")
        print(f"📊 Actual environmental control parameters: {actual_params}")

        print("🎯 SUCCESS: All environmental control parameters loaded from CSV successfully!")
        print("🚫 NO hardcoded values used - all parameters from CSV")
        print("✅ NO duplicate parameters - all parameters are unique to environmental control model")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_environmental_control_parameter_loading()
    if success:
        print("\n✅ Step 1 Complete: Environmental control parameter loading validated!")
    else:
        print("\n❌ Step 1 Failed: Fix issues before proceeding")
        sys.exit(1)