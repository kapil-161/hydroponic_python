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
from src.data.hydroponic_system import HydroInputData
from src.utils.weather_loader import WeatherLoader
from src.utils.config_file_loader import ConfigFileLoader
from src.utils.csv_config_adapter import CSVConfigAdapter


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


def run_simulation(days: int, cultivar_id: str, system_type: str, print_daily: bool, weather_csv: str = None, config_dir: str = ".", experiment_code: str = None) -> Any:
    print("🌱 CROPGRO Hydroponic Simulator - CLI Version")
    print("=" * 50)

    # Load configurations from files
    config_loader = ConfigFileLoader(config_dir, experiment_code)
    
    try:
        system_config = config_loader.load_system_settings()
        crop_params = config_loader.load_crop_parameters()
        nutrient_params = config_loader.load_nutrient_solution()
        experiment_settings = config_loader.load_experiment_settings()
        model_constants = config_loader.load_complete_simulation_parameters()
        
        # Override system type if specified in command line
        if system_type and system_type.upper() != system_config.system_type:
            system_config.system_type = system_type.upper()
            
        print(f"✅ Loaded configuration from: {config_dir}")
        
    except FileNotFoundError as e:
        print(f"❌ Configuration file not found: {e}")
        print("💡 Please create the required CSV configuration files!")
        print("   Run with sample files or create your own configuration.")
        raise e

    # Load weather data from CSV or use fallback
    if weather_csv:
        loader = WeatherLoader(csv_path=weather_csv)
        # Load weather data without date filtering to use available data
        weather_list = loader.load_weather_data(days=days)
        print(f"✅ Loaded {len(weather_list)} weather records from CSV")
    elif experiment_code:
        loader = WeatherLoader(experiment_code=experiment_code, config_dir=config_dir)
        weather_list = loader.load_weather_data(days=days)
        print(f"✅ Loaded {len(weather_list)} weather records for experiment {experiment_code}")
    else:
        # Fallback: raise error if no weather CSV provided
        raise ValueError("Weather CSV file path is required. Use --weather-csv argument or --experiment with matching weather file.")

    # Create input data
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_list,
        nutrient_params=nutrient_params,
        simulation_days=days
    )

    # Create CSV config adapter with experiment code
    csv_config = CSVConfigAdapter(config_dir, experiment_code)
    
    # Create and run simulator with loaded configuration
    simulator = CROPGROHydroponicSimulator(
        cultivar_id=cultivar_id,
        system_type=system_type.upper() if system_type else 'NFT',
        model_constants=model_constants,
        config=csv_config
    )

    print(f"Starting simulation until harvest maturity...")
    print(f"Cultivar: {simulator.cultivar_profile.cultivar_name}")
    print(f"System: {system_config.system_type}")

    results = simulator.run_simulation(input_data, max_days=days, target_maturity='harvest')

    if print_daily:
        for dr in results.daily_results:
            print(simulator.display_detailed_results(dr))

    print(f"✅ Simulation completed successfully!")
    print(f"Duration: {len(results.daily_results)} days")
    print(f"Final stage: {getattr(results.daily_results[-1], 'growth_stage', 'Unknown')}")

    return results


def main():
    parser = argparse.ArgumentParser(description="CROPGRO Hydroponic Simulator CLI")
    parser.add_argument('--days', type=int, default=120, help='Max simulation days')
    parser.add_argument('--cultivar', type=str, default='HYDRO_001', help='Cultivar ID')
    parser.add_argument('--system', type=str, default='NFT', choices=['NFT', 'DWC', 'AEROPONICS'], help='Hydroponic system type')
    parser.add_argument('--output-csv', type=str, help='Path to write CSV of daily results')
    parser.add_argument('--output-json', type=str, help='Path to write JSON with all daily details')
    parser.add_argument('--daily-csv', action='store_true', help='Automatically save daily CSV with timestamp in outputs/ directory')
    parser.add_argument('--print-daily', action='store_true', help='Print detailed per-day results to stdout')
    parser.add_argument('--print-summary', action='store_true', help='Print summary stats to stdout')
    parser.add_argument('--weather-csv', type=str, help='Path to weather data CSV file (optional if --experiment is used)')
    parser.add_argument('--config-dir', type=str, default='input', help='Directory containing configuration files (default: input)')
    parser.add_argument('--experiment', type=str, help='Experiment code (e.g., LET_EXP001_2024) for multi-experiment setups')

    args = parser.parse_args()

    try:
        results = run_simulation(args.days, args.cultivar, args.system, args.print_daily, args.weather_csv, args.config_dir, args.experiment)

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