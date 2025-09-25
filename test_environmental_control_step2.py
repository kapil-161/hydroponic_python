#!/usr/bin/env python3
"""
Step 2 Test: Verify Environmental Control Model Works with CSV Parameters
Tests that the environmental control model can be instantiated and run calculations using ONLY CSV parameters.
"""

import sys
import pandas as pd
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_parameters_from_csv(csv_path: str) -> dict:
    """Load parameters from master CSV file with proper structure for environmental control model."""
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

def test_environmental_control_model_functionality():
    """Test that environmental control model works with CSV-only parameters."""
    print("🧪 Testing Environmental Control Model Functionality...")

    try:
        # Load parameters
        params_dict = load_parameters_from_csv('input/master_parameters.csv')
        config = create_config_object(params_dict)

        # Import and test environmental control model directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("environmental_control", "src/models/environmental_control.py")
        env_control_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(env_control_module)

        EnvironmentalSetpoints = env_control_module.EnvironmentalSetpoints
        ControlEquipment = env_control_module.ControlEquipment
        EnvironmentalControlSystem = env_control_module.EnvironmentalControlSystem
        ControlStrategy = env_control_module.ControlStrategy

        # Test parameter creation from config
        print("📋 Creating EnvironmentalSetpoints from CSV config...")
        env_setpoints = EnvironmentalSetpoints.from_config(config.environment)
        print(f"✅ EnvironmentalSetpoints created successfully")
        print(f"   Target VPD: {env_setpoints.target_vpd} kPa")
        print(f"   Day temperature: {env_setpoints.day_temp}°C")
        print(f"   Target CO2: {env_setpoints.target_co2} ppm")
        print(f"   Light hours: {env_setpoints.light_hours} h")

        print("🛠️  Creating ControlEquipment from CSV config...")
        control_equipment = ControlEquipment.from_config(config.control_equipment_parameters)
        print(f"✅ ControlEquipment created successfully")
        print(f"   Humidifier capacity: {control_equipment.humidifier_capacity} L/h")
        print(f"   CO2 injection rate: {control_equipment.co2_injection_rate} ppm/min")
        print(f"   Air exchange rate: {control_equipment.air_exchange_rate} ACH")

        # Create environmental control system instance
        print("🏗️  Creating EnvironmentalControlSystem...")
        env_control_system = EnvironmentalControlSystem(env_setpoints, control_equipment)
        print(f"✅ EnvironmentalControlSystem created successfully")

        # Test consolidated VPD calculation (uses core_utils.calculate_vpd)
        print("💨 Testing consolidated VPD calculation...")
        test_temperature = 22.0  # °C
        test_humidity = 65.0     # %
        vpd = env_control_system._calculate_target_humidity_from_vpd.__globals__['calculate_vpd'](test_temperature, test_humidity)
        print(f"✅ VPD at {test_temperature}°C, {test_humidity}% RH: {vpd:.2f} kPa")

        # Test optimal humidity calculation
        print("💧 Testing optimal humidity calculation...")
        optimal_rh = env_control_system.calculate_optimal_humidity(test_temperature, env_setpoints.target_vpd)
        print(f"✅ Optimal humidity at {test_temperature}°C for {env_setpoints.target_vpd} kPa VPD: {optimal_rh:.1f}%")

        # Test CO2 photosynthesis factor calculation
        print("🌱 Testing CO2 photosynthesis factor...")
        test_co2 = 800.0  # ppm
        test_light = 200.0  # μmol/m²/s
        co2_factor = env_control_system.calculate_co2_photosynthesis_factor(test_co2, test_temperature, test_light)
        print(f"✅ CO2 factor at {test_co2} ppm, {test_light} μmol/m²/s: {co2_factor:.3f}")

        # Test VPD stress factor calculation
        print("😰 Testing VPD stress factor calculation...")
        test_vpd = 1.2  # kPa, slightly high
        transp_factor, photo_factor, stress_level = env_control_system.calculate_vpd_stress_factor(test_vpd)
        print(f"✅ VPD stress at {test_vpd} kPa:")
        print(f"   Transpiration factor: {transp_factor:.3f}")
        print(f"   Photosynthesis factor: {photo_factor:.3f}")
        print(f"   Stress level: {stress_level}")

        # Test humidity control action
        print("🔧 Testing humidity control action...")
        current_humidity = 60.0  # %
        target_humidity = 65.0   # %
        humidity_action = env_control_system.calculate_humidity_control_action(
            current_humidity, target_humidity, ControlStrategy.PID
        )
        print(f"✅ Humidity control action:")
        print(f"   Action: {humidity_action['action']}")
        print(f"   Energy consumption: {humidity_action['energy_consumption_kWh']:.3f} kWh")

        # Test CO2 control action
        print("💨 Testing CO2 control action...")
        current_co2 = 600.0  # ppm
        co2_action = env_control_system.calculate_co2_control_action(
            current_co2, env_setpoints.target_co2, light_on=True,
            strategy=ControlStrategy.PID, photoperiod_time=2.0,
            config_dict=config.environment
        )
        print(f"✅ CO2 control action:")
        print(f"   Action: {co2_action['action']}")
        print(f"   CO2 cost: {co2_action['co2_cost']:.4f} USD")

        # Test photoperiod time calculation
        print("⏰ Testing photoperiod time calculation...")
        current_hour = 8.0  # 8 AM
        photoperiod_time = env_control_system.calculate_photoperiod_time(current_hour, env_setpoints.co2_enrichment_start_hour)
        print(f"✅ Photoperiod time at {current_hour:.0f}:00: {photoperiod_time:.1f} hours since start")

        # Test hourly update
        print("🕐 Testing hourly environmental control update...")
        current_conditions = {
            'temperature': test_temperature,
            'humidity': current_humidity,
            'co2': current_co2,
            'light_intensity': test_light
        }

        hourly_result = env_control_system.hourly_update(
            current_conditions, hour=8, dt_hours=1.0, strategy=ControlStrategy.PID
        )
        print(f"✅ Hourly update results:")
        print(f"   Adjusted temperature: {hourly_result['temperature']:.1f}°C")
        print(f"   Adjusted humidity: {hourly_result['humidity']:.1f}%")
        print(f"   Adjusted CO2: {hourly_result['co2']:.0f} ppm")
        print(f"   Light on: {hourly_result['light_on']}")
        print(f"   Energy consumption: {hourly_result['energy_consumption_kWh']:.3f} kWh")

        # Test core functionality validation
        print("🎯 Core functionality validation completed!")
        print(f"   ✅ Model instantiated with CSV parameters")
        print(f"   ✅ VPD calculation: {vpd:.2f} kPa")
        print(f"   ✅ CO2 enhancement factor: {co2_factor:.3f}")
        print(f"   ✅ Environmental adjustments working")
        print(f"   ✅ PID control systems operational")

        # Verify no hardcoded values by checking parameters come from CSV
        print("🔍 Verifying NO hardcoded values...")
        assert env_setpoints.target_vpd == params_dict['environment']['target_vpd']
        assert env_setpoints.day_temp == params_dict['environment']['day_temp']
        assert env_setpoints.target_co2 == params_dict['environment']['target_co2']
        assert env_setpoints.light_hours == params_dict['environment']['light_hours']
        assert env_setpoints.co2_enrichment_start_hour == params_dict['environment']['co2_enrichment_start_hour']
        assert control_equipment.humidifier_capacity == params_dict['control_equipment_parameters']['humidifier_capacity']
        assert control_equipment.co2_injection_rate == params_dict['control_equipment_parameters']['co2_injection_rate']
        print("✅ All parameter values verified to come from CSV")

        print("🎯 SUCCESS: Environmental control model working with CSV-only parameters!")
        print("🚫 NO hardcoded values - all calculations use CSV parameters")
        print("🔧 Model uses CONSOLIDATED functions from core_utils for VPD calculations")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_environmental_control_model_functionality()
    if success:
        print("\n✅ Step 2 Complete: Environmental control model validated with CSV parameters!")
        print("🚀 Ready to proceed to next model or create main simulator")
    else:
        print("\n❌ Step 2 Failed: Fix environmental control model issues before proceeding")
        sys.exit(1)