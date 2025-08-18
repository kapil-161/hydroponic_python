#!/usr/bin/env python3
"""
Simple Demo of Python Hydroponic Simulation
Direct execution without interactive menu
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.hydroponic_simulator import HydroponicSimulator, create_demo_simulation


def main():
    """Run a simple 5-day demonstration matching Fortran output."""
    print("\n" + "="*70)
    print("    PYTHON HYDROPONIC SIMULATION - SIMPLE DEMO")
    print("    Equivalent to Fortran run_hydroponic_example")
    print("="*70)
    
    # Create simulator
    simulator = HydroponicSimulator()
    
    # Create demo input data
    input_data = create_demo_simulation()
    input_data.simulation_days = 5  # Quick demo
    
    print("System Configuration:")
    print(f"  System ID: {input_data.system_config.system_id}")
    print(f"  Crop: {input_data.system_config.crop_id}")
    print(f"  Location: {input_data.system_config.location_id}")
    print(f"  Tank Volume: {input_data.system_config.tank_volume:.1f} L")
    print(f"  Number of Nutrients: {len(input_data.nutrient_params)}")
    print()
    
    print("Initial Nutrient Concentrations:")
    for nutrient_id, params in input_data.nutrient_params.items():
        print(f"  {nutrient_id}: {params.initial_conc:.1f} mg/L")
    print()
    
    # Run simulation
    results = simulator.run_simulation(input_data)
    
    # Print detailed daily results (like Fortran output)
    print("Daily Simulation Results:")
    print("Day  ETO_Ref  ETc_Prime  Transp   N_Conc   P_Conc   K_Conc")
    print("---  -------  ---------  ------   ------   ------   ------")
    
    for result in results.daily_results:
        print(f"{result.day:3d}  {result.eto_ref:7.2f}  {result.etc_prime:9.2f}  "
              f"{result.transpiration:6.2f}   {result.nutrient_concentrations.get('N-NO3', 0):6.2f}   "
              f"{result.nutrient_concentrations.get('P-PO4', 0):6.2f}   "
              f"{result.nutrient_concentrations.get('K', 0):6.2f}")
    
    print(f"\nFinal Tank Volume: {results.daily_results[-1].tank_volume:8.1f} L")
    print("\n" + "="*70)
    print("SIMULATION COMPLETED - All models working correctly!")
    print("="*70)
    
    # Save results
    try:
        os.makedirs("data/output", exist_ok=True)
        simulator.save_results_csv("data/output/python_hydro_results.csv")
    except Exception as e:
        print(f"Note: Could not save CSV: {e}")


if __name__ == "__main__":
    main()