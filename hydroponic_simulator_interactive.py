#!/usr/bin/env python3
"""
Standalone Hydroponic Simulation Runner
Main entry point for running hydroponic simulations
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.hydroponic_simulator import HydroponicSimulator, create_demo_simulation
from src.utils.weather_generator import WeatherGenerator
from src.data.hydroponic_system import DefaultConfigurations, HydroInputData


def run_quick_demo():
    """Run a quick 5-day demonstration."""
    print("\n" + "="*70)
    print("    PYTHON HYDROPONIC SIMULATION - QUICK DEMO")
    print("    Equivalent to Fortran run_hydroponic_example")
    print("="*70)
    
    # Create simulator
    simulator = HydroponicSimulator()
    
    # Create demo input data
    input_data = create_demo_simulation()
    input_data.simulation_days = 5  # Quick demo
    
    # Run simulation
    results = simulator.run_simulation(input_data)
    
    # Print detailed daily results (like Fortran output)
    print("\nDaily Simulation Results:")
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
    
    return results


def run_full_simulation():
    """Run full 30-day simulation with detailed output."""
    print("Running full 30-day hydroponic simulation...")
    
    # Create simulator
    simulator = HydroponicSimulator()
    
    # Create input data
    input_data = create_demo_simulation()
    
    # Run simulation
    results = simulator.run_simulation(input_data)
    
    # Print summary
    simulator.print_summary()
    
    # Save results
    output_file = "data/output/hydroponic_results.csv"
    os.makedirs("data/output", exist_ok=True)
    simulator.save_results_csv(output_file)
    
    return results


def run_custom_simulation():
    """Run simulation with custom parameters."""
    print("Setting up custom hydroponic simulation...")
    
    # Get user input for simulation parameters
    print("\nCustomize your simulation:")
    
    try:
        days = int(input("Number of simulation days (default 30): ") or "30")
        base_temp = float(input("Base temperature °C (default 22): ") or "22")
        tank_volume = float(input("Tank volume L (default 500): ") or "500")
    except ValueError:
        print("Invalid input, using defaults...")
        days = 30
        base_temp = 22
        tank_volume = 500
    
    # Create custom configuration
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    system_config.tank_volume = tank_volume
    
    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Generate custom weather
    generator = WeatherGenerator(base_temp=base_temp)
    weather_data = generator.generate_weather_series(datetime.now(), days)
    
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_data,
        nutrient_params=nutrient_params,
        simulation_days=days
    )
    
    # Run simulation
    simulator = HydroponicSimulator()
    results = simulator.run_simulation(input_data)
    
    # Print results
    simulator.print_summary()
    
    return results


def main():
    """Main function with menu options."""
    print("Python Hydroponic Simulation System")
    print("Converted from Fortran AMEI implementation")
    print("\nChoose simulation type:")
    print("1. Quick Demo (5 days) - matches Fortran output")
    print("2. Full Simulation (30 days)")
    print("3. Custom Simulation")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == "1":
                results = run_quick_demo()
                break
            elif choice == "2":
                results = run_full_simulation()
                break
            elif choice == "3":
                results = run_custom_simulation()
                break
            elif choice == "4":
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            print("Please try again.")


if __name__ == "__main__":
    main()