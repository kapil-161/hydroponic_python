#!/usr/bin/env python3
"""
CROPGRO Hydroponic Simulator - Command Line Interface
Professional DSSAT-style crop modeling system
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

# Import CROPGRO system
from src.cropgro_hydroponic_simulator import CROPGROHydroponicSimulator
from src.data.hydroponic_system import DefaultConfigurations, HydroInputData, WeatherData
# WeatherGenerator removed - weather data must come from CSV files


def to_serializable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        import numpy as np
        if isinstance(value, (np.floating, np.integer)):
            return float(value)
    except Exception:
        pass
    return value


def daily_result_to_dict(dr: Any) -> Dict[str, Any]:
    data = {}
    for k, v in vars(dr).items():
        if isinstance(v, dict):
            data[k] = {sk: to_serializable(sv) for sk, sv in v.items()}
        elif isinstance(v, list):
            data[k] = [to_serializable(it) for it in v]
        else:
            data[k] = to_serializable(v)
    return data


def run_simulation(days: int, cultivar_id: str, system_type: str, print_daily: bool, treatment_id: str = None, input_dir: str = 'input') -> Any:
    print("🌱 CROPGRO Hydroponic Simulator - CLI Version")
    print("=" * 50)

    # Use default configurations as a base
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    if system_type and system_type.upper() != 'NFT':
        # Only type affects the engine; keep other fields
        system_config.system_type = system_type.upper()
    
    # Load parameters from SINGLE MASTER FILE - NO CONFLICTS ALLOWED
    try:
        import pandas as pd
        
        # Use treatment_id for file paths, fall back to cultivar_id if treatment_id not provided
        file_prefix = treatment_id if treatment_id else cultivar_id
        
        # Load from master parameters file (single source of truth)
        master_file = f'{input_dir}/{file_prefix}_master_parameters.csv'
        if not Path(master_file).exists():
            print(f"❌ Master parameters file not found: {master_file}")
            print("Please ensure you have a master_parameters.csv file with all parameters")
            return
        
        print(f"📋 Loading parameters from master file: {master_file}")
        
        # Load all parameters from single master file
        try:
            df = pd.read_csv(master_file, comment='#')
            params_loaded = []
            
            # Check for duplicate parameter names across all categories
            all_param_names = df['parameter_name'].tolist()
            duplicate_params = []
            seen_params = set()
            
            for param_name in all_param_names:
                if param_name in seen_params:
                    duplicate_params.append(param_name)
                else:
                    seen_params.add(param_name)
            
            if duplicate_params:
                print(f"❌ ERROR: Duplicate parameter names found in CSV file:")
                for dup_param in set(duplicate_params):  # Remove duplicates from error list
                    dup_rows = df[df['parameter_name'] == dup_param]
                    print(f"   • '{dup_param}' appears {len(dup_rows)} times:")
                    for idx, row in dup_rows.iterrows():
                        category = row.get('category', 'unknown')
                        value = row.get('value', 'unknown')
                        print(f"     - Row {idx+2}: category='{category}', value='{value}'")
                print(f"\n💡 Please remove duplicate entries to avoid parameter loading issues.")
                print(f"   Duplicate parameters can cause values to be loaded as lists instead of scalars.")
                return
            
            # Group parameters by category
            parameter_categories = {}
            for _, row in df.iterrows():
                param_name = row['parameter_name']
                param_value = row['value']
                category = row.get('category', 'general')
                priority = row.get('priority', 1)
                
                # Convert to appropriate type
                try:
                    if pd.isna(param_value):
                        continue
                    elif str(param_value).lower() in ['true', 'false']:
                        param_value = str(param_value).lower() == 'true'
                    elif str(param_value).replace('.', '').replace('-', '').isdigit():
                        # Convert to float first, then check if it should be int
                        param_value = float(param_value)
                        # Convert to int if it's a whole number and the parameter name suggests it should be int
                        if param_value.is_integer() and any(keyword in param_name.lower() for keyword in ['number', 'count', 'layers', 'plants']):
                            param_value = int(param_value)
                    elif str(param_value).startswith('{') and str(param_value).endswith('}'):
                        # Try to parse as dictionary
                        try:
                            import ast
                            param_value = ast.literal_eval(str(param_value))
                        except (ValueError, SyntaxError):
                            pass  # Keep as string if parsing fails
                except (ValueError, TypeError):
                    pass  # Keep as string
                
                # Store in category
                if category not in parameter_categories:
                    parameter_categories[category] = {}
                parameter_categories[category][param_name] = param_value
                params_loaded.append(f"{param_name}={param_value}")
            
            # Assign categories to system_config
            for category, params in parameter_categories.items():
                # Skip invalid categories (must be valid Python identifiers)
                if pd.isna(category) or not isinstance(category, str) or not category.replace('_', '').isalnum():
                    continue
                # Set both with and without _parameters suffix for compatibility
                setattr(system_config, f"{category}_parameters", params)
                setattr(system_config, category, params)
            
            # Set key system_config values for backward compatibility
            if 'environment' in parameter_categories:
                env_params = parameter_categories['environment']
                if 'environment_optimal_temperature' in env_params:
                    system_config.temperature = env_params['environment_optimal_temperature']
                    print(f"✓ Temperature loaded: {env_params['environment_optimal_temperature']}°C")
                if 'min_humidity' in env_params:
                    system_config.humidity = env_params['min_humidity']
                    print(f"✓ Humidity loaded: {env_params['min_humidity']}%")
                if 'optimal_light_intensity' in env_params:
                    system_config.solar_radiation = env_params['optimal_light_intensity']
                    print(f"✓ Light loaded: {env_params['optimal_light_intensity']} MJ/m²/day")
                if 'min_ec' in env_params:
                    system_config.solution_ec = env_params['min_ec']
                    print(f"✓ EC loaded: {env_params['min_ec']} dS/m")
                if 'target_vpd' in env_params:
                    print(f"✓ Target VPD loaded: {env_params['target_vpd']} kPa")
                if 'target_co2' in env_params:
                    system_config.controlled_co2 = env_params['target_co2']
                    print(f"✓ CO2 loaded: {env_params['target_co2']} ppm")
            
            if 'system' in parameter_categories:
                sys_params = parameter_categories['system']
                if 'tank_volume' in sys_params:
                    system_config.tank_volume = sys_params['tank_volume']
                    print(f"✓ Tank volume loaded: {sys_params['tank_volume']} L")
                if 'system_area' in sys_params:
                    system_config.system_area = sys_params['system_area']
                    print(f"✓ System area loaded: {sys_params['system_area']} m²")
                if 'number_of_plants' in sys_params:
                    system_config.n_plants = sys_params['number_of_plants']
                    print(f"✓ Number of plants loaded: {sys_params['number_of_plants']}")
            
            print(f"📊 Successfully loaded {len(params_loaded)} parameters from master file")
            print(f"📋 Categories loaded: {list(parameter_categories.keys())}")
            
        except Exception as e:
            print(f"❌ Error loading master parameters file: {e}")
            return
            
    except Exception as e:
        print(f"❌ CSV loading failed: {e}")
        import traceback
        traceback.print_exc()

    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Update nutrient_params with dynamic nutrient solution values from CSV
    if hasattr(system_config, 'nutrient_solution'):
        from src.models.nutrient_models import NutrientParams
        for nutrient_id, nutrient_data in system_config.nutrient_solution.items():
            if nutrient_id in nutrient_params:
                # Update the existing nutrient parameter with CSV values
                original_param = nutrient_params[nutrient_id]
                nutrient_params[nutrient_id] = NutrientParams(
                    nutrient_id=original_param.nutrient_id,
                    nutrient_name=original_param.nutrient_name,
                    chemical_form=original_param.chemical_form,
                    initial_conc=nutrient_data['initial_ppm'],  # Use CSV value
                    recharge_conc=nutrient_data['optimal_ppm'], # Use CSV value
                    uptake_conc=original_param.uptake_conc,
                    sensitivity_coeff=original_param.sensitivity_coeff,
                    is_nutritive=original_param.is_nutritive,
                    min_conc=nutrient_data['minimum_ppm'],     # Use CSV value
                    max_conc=nutrient_data['max_ppm'],         # Use CSV value
                    charge=original_param.charge,
                    molar_mass=original_param.molar_mass
                )

    # Update system_config with dynamic system settings from CSV
    if hasattr(system_config, 'system_settings'):
        system_settings = system_config.system_settings
        # Map CSV parameter names to system_config attributes
        setting_mapping = {
            'system_type': 'system_type',
            'tank_volume': 'tank_volume',
            'system_area': 'system_area', 
            'number_of_plants': 'n_plants',
            'initial_ph': 'initial_ph',
            'initial_ec': 'initial_ec',
            'target_temperature': 'target_temperature',
            'target_humidity': 'target_humidity',
            'co2_concentration': 'co2_setpoint'
        }
        
        for csv_param, config_attr in setting_mapping.items():
            if csv_param in system_settings:
                setattr(system_config, config_attr, system_settings[csv_param])
                print(f"✓ Updated {config_attr} = {system_settings[csv_param]} from CSV")

    # 22. Load weather data - REQUIRED CSV FILE
    weather_data_file = f'{input_dir}/{file_prefix}_weather.csv'
    weather_list = []
    
    if not Path(weather_data_file).exists():
        print(f"❌ ERROR: Weather data file not found: {weather_data_file}")
        print(f"   Expected format: {file_prefix}_weather.csv")
        print(f"   Required columns: date, temp_avg, temp_min, temp_max, solar_radiation, rel_humidity, wind_speed, rainfall")
        print(f"   Please create the weather CSV file with daily weather data.")
        return None, None
    
    try:
        df = pd.read_csv(weather_data_file)
        print(f"✓ Weather data loaded: {len(df)} days from {weather_data_file}")
        
        # Validate required columns
        required_columns = ['date', 'temp_avg', 'temp_min', 'temp_max', 'solar_radiation', 'rel_humidity', 'wind_speed', 'rainfall']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ ERROR: Weather CSV missing required columns: {missing_columns}")
            print(f"   Required columns: {required_columns}")
            return None, None
        
        # Convert weather data to WeatherData objects
        for _, row in df.iterrows():
            weather_day = WeatherData(
                date=row['date'],
                temp_avg=row['temp_avg'],
                temp_min=row['temp_min'],
                temp_max=row['temp_max'],
                solar_radiation=row['solar_radiation'],
                rel_humidity=row['rel_humidity'],
                wind_speed=row['wind_speed'],
                rainfall=row['rainfall']
            )
            weather_list.append(weather_day)
            
        # Store weather data in system_config for access
        system_config.weather_data = weather_list
        params_loaded.append(f"weather_days={len(weather_list)}")
        
    except Exception as e:
        print(f"❌ ERROR: Could not load weather data from {weather_data_file}: {e}")
        print(f"   Please check the CSV file format and try again.")
        return None, None

    # Create input data
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_list,
        nutrient_params=nutrient_params,
        simulation_days=days
    )

    # Create and run simulator
    simulator = CROPGROHydroponicSimulator(
        cultivar_id=cultivar_id,
        system_type=system_type.upper() if system_type else 'NFT',
        system_config=system_config
    )

    print(f"Starting simulation until harvest maturity...")
    print(f"Cultivar: {simulator.cultivar_profile.cultivar_name}")
    print(f"System: {system_config.system_type}")

    # treatment_id parameter is passed directly to the function
    results = simulator.run_simulation(input_data, max_days=days, target_maturity='harvest', treatment_id=treatment_id)

    if print_daily and not args.summary_only:
        for dr in results.daily_results:
            print(simulator.display_detailed_results(dr))

    # Print final summary
    print("\n" + "="*80)
    print("🎯 FINAL SIMULATION SUMMARY")
    print("="*80)
    
    final_result = results.daily_results[-1]
    total_days = len(results.daily_results)
    final_biomass = getattr(final_result, 'total_biomass', None)
    final_stage = getattr(final_result, 'growth_stage', 'Unknown')
    
    # Get system configuration from the simulator's system_config
    # These values should be available from the CSV parameters
    plant_count = getattr(simulator.system_config, 'n_plants', None)
    system_area = getattr(simulator.system_config, 'system_area', None)
    
    if final_biomass is None:
        print("❌ ERROR: Biomass data missing. Cannot generate summary.")
        return results, file_prefix
        
    if plant_count is None or system_area is None:
        print("❌ ERROR: System configuration missing (plant count or system area). Cannot generate summary.")
        return results, file_prefix
    
    # Calculate totals
    total_system_biomass = final_biomass * plant_count
    system_yield = total_system_biomass / system_area
    
    # Calculate growth rates
    if total_days > 1:
        initial_biomass = getattr(results.daily_results[0], 'total_biomass', None)
        if initial_biomass is not None:
            total_growth = final_biomass - initial_biomass
            avg_daily_growth = total_growth / (total_days - 1)
            total_system_growth = total_growth * plant_count
            avg_system_growth = total_system_growth / (total_days - 1)
        else:
            total_growth = None
            avg_daily_growth = None
            total_system_growth = None
            avg_system_growth = None
    else:
        total_growth = None
        avg_daily_growth = None
        total_system_growth = None
        avg_system_growth = None
    
    print(f"\n📊 SIMULATION OVERVIEW:")
    print(f"  • Duration: {total_days} days")
    print(f"  • Final Stage: {final_stage}")
    print(f"  • System: {plant_count} plants × {system_area} m² = {plant_count/system_area:.1f} plants/m²")
    
    print(f"\n⚖️  FINAL BIOMASS RESULTS:")
    print(f"  {'Metric':<25} {'Per Plant':<15} {'Total System':<15} {'Per m²':<15}")
    print(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*15}")
    print(f"  {'Final Biomass':<25} {final_biomass:<15.2f} g {total_system_biomass:<15.1f} g {system_yield:<15.1f} g/m²")
    
    if total_growth is not None:
        print(f"  {'Total Growth':<25} {total_growth:<15.2f} g {total_system_growth:<15.1f} g {(total_system_growth/system_area):<15.1f} g/m²")
    else:
        print(f"  {'Total Growth':<25} {'Data Missing':<15} {'Data Missing':<15} {'Data Missing':<15}")
        
    if avg_daily_growth is not None:
        print(f"  {'Avg Daily Growth':<25} {avg_daily_growth:<15.3f} g/day {avg_system_growth:<15.2f} g/day {(avg_system_growth/system_area):<15.2f} g/m²/day")
    else:
        print(f"  {'Avg Daily Growth':<25} {'Data Missing':<15} {'Data Missing':<15} {'Data Missing':<15}")
    
    # Show efficiency metrics
    final_lai = getattr(final_result, 'lai', None)
    final_leaf_area = getattr(final_result, 'leaf_area_m2', None)
    
    if final_lai is not None and final_leaf_area is not None:
        total_leaf_area = final_leaf_area * plant_count
        
        print(f"\n🌿 FINAL CANOPY STATUS:")
        print(f"  • Per Plant: {final_leaf_area*10000:.1f} cm² leaf area")
        print(f"  • Total System: {total_leaf_area*10000:.0f} cm² leaf area")
        print(f"  • System LAI: {final_lai:.3f}")
    else:
        print(f"\n🌿 FINAL CANOPY STATUS:")
        print(f"  • Canopy data not available")
    
    # Show environmental summary
    final_temp = getattr(final_result, 'temp_avg', None)
    final_ec = getattr(final_result, 'ec', None)
    final_ph = getattr(final_result, 'solution_ph', None)
    
    print(f"\n🌡️  FINAL ENVIRONMENTAL STATUS:")
    if final_temp is not None:
        print(f"  • Temperature: {final_temp:.1f}°C")
    else:
        print(f"  • Temperature: Data not available")
        
    if final_ec is not None:
        print(f"  • EC: {final_ec:.2f} dS/m")
    else:
        print(f"  • EC: Data not available")
        
    if final_ph is not None:
        print(f"  • pH: {final_ph:.2f}")
    else:
        print(f"  • pH: Data not available")
    
    # Show stress summary
    final_stress = getattr(final_result, 'integrated_stress', None)
    if final_stress is not None:
        if final_stress < 0.1:
            stress_status = "🟢 None"
        elif final_stress < 0.3:
            stress_status = "🟡 Mild"
        elif final_stress < 0.6:
            stress_status = "🟠 Moderate"
        else:
            stress_status = "🔴 Severe"
        
        print(f"  • Integrated Stress: {final_stress:.3f} {stress_status}")
    else:
        print(f"  • Integrated Stress: Data not available")
    
    # Show projections if growth is positive
    if avg_daily_growth is not None and avg_daily_growth > 0:
        # Estimate days to harvest (assuming ~800 GDD for lettuce)
        final_gdd = getattr(final_result, 'accumulated_gdd', None)
        if final_gdd is not None:
            harvest_gdd = 800.0
            remaining_gdd = max(0, harvest_gdd - final_gdd)
            
            # Estimate days based on thermal time
            avg_thermal_time = getattr(final_result, 'thermal_time_daily', None)
            if avg_thermal_time is not None and avg_thermal_time > 0:
                days_to_harvest = remaining_gdd / avg_thermal_time
                projected_final_biomass = final_biomass + (avg_daily_growth * days_to_harvest)
                projected_system_yield = projected_final_biomass * plant_count / system_area
                
                print(f"\n🔮 HARVEST PROJECTIONS:")
                print(f"  • Days to Harvest: {days_to_harvest:.1f} days")
                print(f"  • Projected Final Biomass: {projected_final_biomass:.1f} g/plant")
                print(f"  • Projected System Yield: {projected_system_yield:.1f} g/m²")
            else:
                print(f"\n🔮 HARVEST PROJECTIONS:")
                print(f"  • Thermal time data not available for projections")
        else:
            print(f"\n🔮 HARVEST PROJECTIONS:")
            print(f"  • GDD data not available for projections")
    
    print(f"\n{'-'*80}")
    print(f"📋 Note: All biomass values shown are PER PLANT. Multiply by {plant_count} for total system values.")
    print(f"📋 Note: System yield is calculated as total system biomass ÷ system area.")
    print(f"{'='*80}")

    print(f"✅ Simulation completed successfully!")
    print(f"Duration: {len(results.daily_results)} days")
    print(f"Final stage: {getattr(results.daily_results[-1], 'growth_stage', 'Unknown')}")

    return results, file_prefix


def main():
    parser = argparse.ArgumentParser(description="CROPGRO Hydroponic Simulator CLI")
    parser.add_argument('--days', type=int, default=120, help='Max simulation days')
    parser.add_argument('--cultivar', type=str, default='LET_EXP001_2024', help='Cultivar ID')
    parser.add_argument('--system', type=str, default='NFT', choices=['NFT', 'DWC', 'AEROPONICS'], help='Hydroponic system type')
    parser.add_argument('--output-csv', type=str, help='Path to write CSV of daily results')
    parser.add_argument('--output-json', type=str, help='Path to write JSON with all daily details')
    parser.add_argument('--daily-csv', action='store_true', help='Automatically save daily CSV with timestamp in outputs/ directory')
    parser.add_argument('--print-daily', action='store_true', help='Print detailed per-day results to stdout')
    parser.add_argument('--print-summary', action='store_true', help='Print summary stats to stdout')
    parser.add_argument('--summary-only', action='store_true', help='Show only final summary (no daily details)')
    
    # Add help text about output options
    parser.add_argument('--help-output', action='store_true', help='Show detailed help about output options')
    
    # Treatment identifier for batch processing
    parser.add_argument('--treatment-id', type=str, help='Treatment identifier (e.g., T01, T02)')
    parser.add_argument('--input-dir', type=str, default='input', help='Input directory containing CSV configuration files')

    args = parser.parse_args()

    # Handle help output option
    if args.help_output:
        print("""
🌱 CROPGRO HYDROPONIC SIMULATOR - OUTPUT OPTIONS HELP
========================================================

📊 OUTPUT FORMATS:

1. DEFAULT OUTPUT (no flags):
   • Shows basic simulation completion message
   • Auto-saves results to CSV file
   • Minimal console output

2. --print-daily:
   • Shows detailed daily results for each day
   • Includes per-plant vs per-system categorization
   • Shows carbon balance, nutrient status, stress factors
   • Best for debugging and detailed analysis

3. --summary-only:
   • Shows only the final summary table
   • No daily details
   • Quick overview of final results
   • Good for batch processing

4. --print-summary:
   • Shows basic summary statistics
   • Minimal formatting
   • Good for scripting and automation

5. --daily-csv:
   • Auto-saves detailed CSV with timestamp
   • Useful for data analysis and plotting

6. --output-csv <path>:
   • Saves results to specified CSV path
   • Custom file location

7. --output-json <path>:
   • Saves full results to JSON format
   • Includes all simulation data
   • Good for programmatic access

📋 PER-PLANT vs PER-SYSTEM VALUES:

• PER-PLANT: Individual plant biomass, growth rates, stress levels
• PER-SYSTEM: Total system biomass, environmental conditions, nutrient concentrations
• System yield = Total system biomass ÷ System area (g/m²)

🔍 EXAMPLE USAGE:

# Quick simulation with auto-save
python3 cropgro_cli.py --days 30 --cultivar LET_EXP001_2024

# Detailed daily output
python3 cropgro_cli.py --days 30 --cultivar LET_EXP001_2024 --print-daily

# Summary only (no daily details)
python3 cropgro_cli.py --days 30 --cultivar LET_EXP001_2024 --summary-only

# Save to custom location
python3 cropgro_cli.py --days 30 --cultivar LET_EXP001_2024 --output-csv my_results.csv
        """)
        return

    try:
        results, detected_file_prefix = run_simulation(args.days, args.cultivar, args.system, args.print_daily, args.treatment_id, args.input_dir)

        # Output CSV via DataFrame (curated columns)
        if args.output_csv:
            df = results.to_dataframe()
            out_path = Path(args.output_csv)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(out_path, index=False)
            print(f"Saved CSV: {out_path}")

        # Auto-generate daily CSV with timestamp
        if args.daily_csv:
            df = results.to_dataframe()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"hydroponic_daily_results_{args.cultivar}_{args.system}_{timestamp}.csv"
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)
            out_path = outputs_dir / filename
            df.to_csv(out_path, index=False)
            print(f"Saved daily CSV: {out_path}")

        # Output full JSON with all attributes per day
        if args.output_json:
            out = {
                'metadata': getattr(results, 'metadata', {}),
                'summary_stats': results.summary_stats,
                'daily_results': [daily_result_to_dict(dr) for dr in results.daily_results],
            }
            out_path = Path(args.output_json)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'w') as f:
                json.dump(out, f, indent=2)
            print(f"Saved JSON: {out_path}")

        # Auto-save results if no output options were specified
        if not args.output_csv and not args.daily_csv and not args.output_json:
            df = results.to_dataframe()
            # Use the detected file prefix from the simulation
            filename = f"{detected_file_prefix}_results.csv"
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)
            out_path = outputs_dir / filename
            df.to_csv(out_path, index=False)
            print(f"📄 Auto-saved results: {out_path}")

        if args.print_summary:
            print("\nSummary stats:")
            for k, v in results.summary_stats.items():
                print(f"- {k}: {v}")

        print(f"\n🎯 Simulation completed successfully!")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()