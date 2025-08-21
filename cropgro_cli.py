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
from src.data.hydroponic_system import DefaultConfigurations, HydroInputData
from src.utils.weather_generator import WeatherGenerator


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


def run_simulation(days: int, cultivar_id: str, system_type: str, print_daily: bool) -> Any:
    print("🌱 CROPGRO Hydroponic Simulator - CLI Version")
    print("=" * 50)

    # Use default configurations as a base
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    if system_type and system_type.upper() != 'NFT':
        # Only type affects the engine; keep other fields
        system_config.system_type = system_type.upper()

    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()

    # Generate weather data
    generator = WeatherGenerator()
    start_date = datetime.now()
    weather_list = generator.generate_weather_series(
        start_date=start_date,
        days=days
    )

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
        system_type=system_type.upper() if system_type else 'NFT'
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
    parser.add_argument('--print-daily', action='store_true', help='Print detailed per-day results to stdout')
    parser.add_argument('--print-summary', action='store_true', help='Print summary stats to stdout')

    args = parser.parse_args()

    try:
        results = run_simulation(args.days, args.cultivar, args.system, args.print_daily)

        # Output CSV via DataFrame (curated columns)
        if args.output_csv:
            df = results.to_dataframe()
            out_path = Path(args.output_csv)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(out_path, index=False)
            print(f"Saved CSV: {out_path}")

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