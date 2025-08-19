#!/usr/bin/env python3
"""
CROPGRO Hydroponic Simulator - User Guide
How to give input and get output from the advanced CROPGRO system

This guide shows you exactly how to:
1. Set up input data
2. Configure the simulator
3. Run simulations
4. Get detailed outputs
5. Save and analyze results
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cropgro_hydroponic_simulator import CROPGROHydroponicSimulator
from src.data.hydroponic_system import (
    HydroInputData, HydroSystemConfig, CropParameters, 
    DefaultConfigurations, WeatherData
)
from src.utils.weather_generator import WeatherGenerator


def example_1_basic_usage():
    """Example 1: Basic usage with default settings"""
    print("=" * 80)
    print("EXAMPLE 1: BASIC USAGE")
    print("=" * 80)
    
    # STEP 1: Create the simulator
    print("Step 1: Creating CROPGRO simulator...")
    simulator = CROPGROHydroponicSimulator(
        cultivar_id='HYDRO_001',  # Advanced hydroponic cultivar
        system_type='NFT'         # Nutrient Film Technique
    )
    
    # STEP 2: Set up input data using defaults
    print("Step 2: Setting up input data...")
    
    # Use default configurations (easiest way to start)
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Generate weather data
    weather_gen = WeatherGenerator()
    weather_data = weather_gen.generate_weather_series(
        start_date=datetime(2024, 4, 15),
        num_days=7  # 7-day simulation
    )
    
    # Combine into input data object
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_data,
        nutrient_params=nutrient_params,
        simulation_days=7
    )
    
    # STEP 3: Run the simulation
    print("Step 3: Running simulation...")
    results = simulator.run_simulation(input_data)
    
    # STEP 4: Get outputs
    print("Step 4: Getting outputs...")
    
    # Basic summary statistics
    summary = results.summary_stats
    print(f"\n📊 BASIC RESULTS:")
    print(f"  • Final LAI: {summary['current_lai']:.2f}")
    print(f"  • Total Biomass: {summary['total_biomass_g']:.1f} g")
    print(f"  • Water Use: {summary['total_water_consumption_L']:.1f} L")
    print(f"  • Average CO₂: {summary['average_co2_umol_mol']:.0f} μmol/mol")
    
    # Detailed results for final day
    final_day = results.daily_results[-1]
    print(f"\n📈 FINAL DAY DETAILS:")
    print(f"  • Growth Stage: {getattr(final_day, 'growth_stage', 'VE')}")
    print(f"  • Leaf Biomass: {getattr(final_day, 'leaf_biomass', 0.0):.2f} g")
    print(f"  • Root Biomass: {getattr(final_day, 'root_biomass', 0.0):.2f} g")
    print(f"  • Photosynthesis: {getattr(final_day, 'photosynthesis_rate', 0.0):.4f}")
    
    print("✅ Basic usage complete!")
    return results


def example_2_custom_inputs():
    """Example 2: Custom inputs and configuration"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: CUSTOM INPUTS")
    print("=" * 80)
    
    # STEP 1: Custom system configuration
    print("Step 1: Creating custom system configuration...")
    
    custom_system = HydroSystemConfig(
        system_id="MY_SYSTEM_001",
        crop_id="LETTUCE_PREMIUM", 
        location_id="MY_GREENHOUSE",
        tank_volume=2000.0,      # 2000L tank
        flow_rate=75.0,          # 75 L/h flow rate
        system_type="NFT",
        system_area=15.0,        # 15 m² growing area
        n_plants=60,             # 60 plants
        description="Premium lettuce production system"
    )
    
    # STEP 2: Custom crop parameters
    print("Step 2: Setting custom crop parameters...")
    
    custom_crop = CropParameters(
        crop_id="LETTUCE_PREMIUM",
        crop_name="Premium Butterhead Lettuce",
        kcb=1.1,                 # Higher crop coefficient
        phi=0.85,                # Density index
        crop_height=0.25,        # 25 cm target height
        root_zone_depth=0.15,    # 15 cm root zone
        laid=3.5                 # Target LAI
    )
    
    # STEP 3: Custom weather data
    print("Step 3: Creating custom weather...")
    
    # Create specific weather conditions
    custom_weather = []
    base_date = datetime(2024, 5, 1)
    
    for day in range(10):
        weather = WeatherData(
            date=base_date + datetime.timedelta(days=day),
            temp_avg=22.0 + day * 0.5,  # Gradually warming
            temp_min=18.0 + day * 0.3,
            temp_max=26.0 + day * 0.7,
            solar_radiation=18.0 + day * 0.2,  # Increasing light
            rel_humidity=65.0,
            wind_speed=1.5,
            rainfall=0.0
        )
        custom_weather.append(weather)
    
    # STEP 4: Custom nutrient concentrations
    print("Step 4: Setting custom nutrient levels...")
    
    # Get default nutrients and modify
    custom_nutrients = DefaultConfigurations.get_default_nutrients()
    
    # Increase nitrogen for faster growth
    custom_nutrients['N-NO3'].initial_conc = 220.0  # Higher nitrogen
    custom_nutrients['K'].initial_conc = 250.0      # Higher potassium
    
    # STEP 5: Create simulator with different cultivar
    print("Step 5: Creating simulator with different cultivar...")
    
    simulator = CROPGROHydroponicSimulator(
        cultivar_id='HYDRO_002',  # Different cultivar
        system_type='NFT'
    )
    
    # STEP 6: Combine and run
    print("Step 6: Running custom simulation...")
    
    input_data = HydroInputData(
        system_config=custom_system,
        crop_params=custom_crop,
        weather_data=custom_weather,
        nutrient_params=custom_nutrients,
        simulation_days=10
    )
    
    results = simulator.run_simulation(input_data)
    
    # STEP 7: Custom output analysis
    print("Step 7: Analyzing custom results...")
    
    print(f"\n📊 CUSTOM SIMULATION RESULTS:")
    print(f"  • System: {results.system_id}")
    print(f"  • Cultivar: {results.metadata['cultivar_name']}")
    print(f"  • Final Biomass: {results.summary_stats['total_biomass_g']:.1f} g")
    print(f"  • Water Efficiency: {results.summary_stats['average_water_use_efficiency']:.2f} kg/m³")
    
    print("✅ Custom inputs example complete!")
    return results


def example_3_detailed_outputs():
    """Example 3: Getting comprehensive detailed outputs"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: DETAILED OUTPUTS")
    print("=" * 80)
    
    # Quick simulation setup
    simulator = CROPGROHydroponicSimulator(cultivar_id='HYDRO_001', system_type='NFT')
    
    # Generate 5 days of weather
    weather_gen = WeatherGenerator()
    weather_data = weather_gen.generate_weather_series(datetime(2024, 6, 1), 5)
    
    input_data = HydroInputData(
        system_config=DefaultConfigurations.get_nft_lettuce_system(),
        crop_params=DefaultConfigurations.get_lettuce_parameters(),
        weather_data=weather_data,
        nutrient_params=DefaultConfigurations.get_default_nutrients(),
        simulation_days=5
    )
    
    print("Running simulation for detailed analysis...")
    results = simulator.run_simulation(input_data)
    
    print("Getting comprehensive detailed outputs...")
    
    # METHOD 1: Use the built-in detailed display
    final_day = results.daily_results[-1]
    detailed_report = simulator.display_detailed_results(final_day)
    
    # Show just a portion (it's very comprehensive!)
    lines = detailed_report.split('\n')
    print('\n'.join(lines[:25]))  # First 25 lines
    print("... (detailed report continues with all 10 categories)")
    
    # METHOD 2: Access specific details programmatically
    print(f"\n🔬 ACCESSING SPECIFIC DETAILS:")
    
    for day_idx, daily in enumerate(results.daily_results):
        print(f"\nDay {daily.day}:")
        print(f"  • Growth Stage: {getattr(daily, 'growth_stage', 'N/A')}")
        print(f"  • Biomass: {getattr(daily, 'total_biomass', 0.0):.2f} g")
        print(f"  • LAI: {getattr(daily, 'lai', 0.0):.2f}")
        print(f"  • Stress Factor: {getattr(daily, 'integrated_stress_factor', 1.0):.3f}")
        print(f"  • N Uptake: {getattr(daily, 'nitrogen_uptake_mg', 0.0):.2f} mg/day")
    
    # METHOD 3: Create custom analysis
    print(f"\n📈 GROWTH TREND ANALYSIS:")
    biomass_trend = [getattr(d, 'total_biomass', 0.0) for d in results.daily_results]
    lai_trend = [getattr(d, 'lai', 0.0) for d in results.daily_results]
    
    print(f"  • Biomass growth rate: {(biomass_trend[-1] - biomass_trend[0])/(len(biomass_trend)-1):.3f} g/day")
    print(f"  • LAI development rate: {(lai_trend[-1] - lai_trend[0])/(len(lai_trend)-1):.3f} /day")
    print(f"  • Final harvest index: {getattr(results.daily_results[-1], 'cultivar_yield_potential', 1.0):.3f}")
    
    print("✅ Detailed outputs example complete!")
    return results


def example_4_save_and_export():
    """Example 4: Saving and exporting results"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: SAVING AND EXPORTING")
    print("=" * 80)
    
    # Run a quick simulation
    simulator = CROPGROHydroponicSimulator(cultivar_id='HYDRO_001', system_type='NFT')
    
    weather_gen = WeatherGenerator()
    weather_data = weather_gen.generate_weather_series(datetime(2024, 7, 1), 14)  # 2 weeks
    
    input_data = HydroInputData(
        system_config=DefaultConfigurations.get_nft_lettuce_system(),
        crop_params=DefaultConfigurations.get_lettuce_parameters(),
        weather_data=weather_data,
        nutrient_params=DefaultConfigurations.get_default_nutrients(),
        simulation_days=14
    )
    
    print("Running 14-day simulation...")
    results = simulator.run_simulation(input_data)
    
    # METHOD 1: Save to CSV (if available)
    print("Saving results to CSV...")
    try:
        df = results.to_dataframe()
        csv_filename = "/Users/kapilbhattarai/hydroponic_python/data/output/cropgro_results.csv"
        df.to_csv(csv_filename, index=False)
        print(f"✅ Results saved to: {csv_filename}")
    except Exception as e:
        print(f"CSV save note: {e}")
    
    # METHOD 2: Create custom export
    print("Creating custom export...")
    
    export_data = {
        'simulation_info': {
            'cultivar': results.metadata['cultivar_name'],
            'system_type': results.metadata['simulation_type'],
            'total_days': len(results.daily_results),
            'models_used': results.metadata['models_used']
        },
        'summary_statistics': results.summary_stats,
        'daily_data': []
    }
    
    # Export key daily data
    for daily in results.daily_results:
        daily_export = {
            'day': daily.day,
            'date': daily.date.strftime('%Y-%m-%d'),
            'temperature': daily.temp_avg,
            'biomass_total': getattr(daily, 'total_biomass', 0.0),
            'lai': getattr(daily, 'lai', 0.0),
            'growth_stage': getattr(daily, 'growth_stage', 'VE'),
            'photosynthesis': getattr(daily, 'photosynthesis_rate', 0.0),
            'stress_factor': getattr(daily, 'integrated_stress_factor', 1.0)
        }
        export_data['daily_data'].append(daily_export)
    
    # Save as JSON
    import json
    json_filename = "/Users/kapilbhattarai/hydroponic_python/data/output/cropgro_export.json"
    try:
        with open(json_filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        print(f"✅ Custom export saved to: {json_filename}")
    except Exception as e:
        print(f"JSON save note: {e}")
    
    # METHOD 3: Print summary report
    print(f"\n📋 SUMMARY REPORT:")
    print(f"  • Simulation Period: {len(results.daily_results)} days")
    print(f"  • Cultivar: {results.metadata['cultivar_name']}")
    print(f"  • Final Biomass: {results.summary_stats['total_biomass_g']:.1f} g")
    print(f"  • Growth Rate: {results.summary_stats['total_biomass_g']/len(results.daily_results):.3f} g/day")
    print(f"  • Water Use: {results.summary_stats['total_water_consumption_L']:.1f} L total")
    print(f"  • WUE: {results.summary_stats['average_water_use_efficiency']:.2f} kg/m³")
    
    print("✅ Save and export example complete!")
    return results, export_data


def main():
    """Run all examples to demonstrate complete usage"""
    print("🌱 CROPGRO HYDROPONIC SIMULATOR - COMPLETE USER GUIDE")
    print("=" * 80)
    print("This guide shows you exactly how to use the advanced CROPGRO system")
    print("=" * 80)
    
    try:
        # Run all examples
        results1 = example_1_basic_usage()
        results2 = example_2_custom_inputs() 
        results3 = example_3_detailed_outputs()
        results4, export_data = example_4_save_and_export()
        
        print("\n" + "=" * 80)
        print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        print("\n📖 QUICK REFERENCE:")
        print("1. Basic Usage: Use defaults, run simulation, get results")
        print("2. Custom Inputs: Modify system, weather, nutrients as needed")
        print("3. Detailed Outputs: Access comprehensive CROPGRO analysis")
        print("4. Save/Export: Get data in CSV, JSON, or custom formats")
        
        print("\n🔧 KEY CLASSES:")
        print("• CROPGROHydroponicSimulator: Main simulation engine")
        print("• HydroInputData: Input data container")
        print("• DefaultConfigurations: Easy defaults")
        print("• WeatherGenerator: Create weather data")
        
        print("\n🚀 YOU'RE READY TO USE THE SYSTEM!")
        print("Modify any example above for your specific needs.")
        
    except Exception as e:
        print(f"\n❌ Error in examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()