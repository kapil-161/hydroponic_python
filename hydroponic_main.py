#!/usr/bin/env python3
"""
Main Hydroponic Simulation Application
Professional entry point for hydroponic system simulation with menu interface
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.hydroponic_simulator import HydroponicSimulator, create_demo_simulation
from src.utils.weather_generator import WeatherGenerator
from src.data.hydroponic_system import DefaultConfigurations, HydroInputData


def run_demo_simulation():
    """Run demonstration simulation (5 days) equivalent to Fortran example."""
    print("\n" + "="*70)
    print("    HYDROPONIC DEMO SIMULATION")
    print("    5-Day Lettuce Production Example")
    print("="*70)
    
    # Create simulator
    simulator = HydroponicSimulator()
    
    # Create demo input data
    input_data = create_demo_simulation()
    input_data.simulation_days = 5
    
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
    
    # Print detailed daily results
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
    print("SIMULATION COMPLETED SUCCESSFULLY!")
    print("="*70)
    
    # Save results
    try:
        os.makedirs("data/output", exist_ok=True)
        simulator.save_results_csv("data/output/demo_simulation_results.csv")
    except Exception as e:
        print(f"Note: Could not save CSV: {e}")


def run_full_simulation():
    """Run full 30-day simulation with detailed analysis."""
    print("Running full 30-day hydroponic simulation...")
    
    # Create simulator
    simulator = HydroponicSimulator()
    
    # Create input data
    input_data = create_demo_simulation()
    input_data.simulation_days = 30
    
    # Run simulation
    results = simulator.run_simulation(input_data)
    
    # Print summary
    simulator.print_summary()
    
    # Save results
    output_file = "data/output/full_simulation_results.csv"
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
        print()
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
    
    # Save custom results
    output_file = f"data/output/custom_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    os.makedirs("data/output", exist_ok=True)
    simulator.save_results_csv(output_file)
    
    return results


def show_menu():
    """Display main application menu."""
    print("\n" + "="*70)
    print("    PYTHON HYDROPONIC SIMULATION SYSTEM")
    print("    Professional Agricultural Modeling Suite")
    print("="*70)
    print("\nSelect simulation type:")
    print("1. Demo Simulation (5 days) - Quick validation")
    print("2. Full Simulation (30 days) - Complete analysis")
    print("3. Custom Simulation - User-defined parameters")
    print("4. Help & Documentation")
    print("5. Exit")
    print("-" * 70)


def show_help():
    """Display help information."""
    print("\n" + "="*70)
    print("    HYDROPONIC SIMULATION HELP")
    print("="*70)
    print("""
ABOUT:
This simulation models hydroponic lettuce production systems using:
• Water Uptake Submodel (WUS): Modified Penman-Monteith equations
• Nutrient Concentration Submodel (NCS): Ion dynamics in solutions
• Complete system integration with weather, crop, and system parameters

SIMULATION TYPES:
1. Demo (5 days)    - Quick validation matching Fortran reference
2. Full (30 days)   - Complete production cycle analysis  
3. Custom          - User-defined parameters and duration

OUTPUT FILES:
• CSV files saved to data/output/ directory
• Contains daily results for analysis in Excel/Python/R
• Includes: ET rates, nutrient concentrations, tank volumes

TECHNICAL DETAILS:
• Based on FAO-56 Penman-Monteith methodology
• Implements equations from MDPI hydroponic research
• Validated against Fortran AMEI implementation
• Professional-grade scientific accuracy

REQUIREMENTS:
• Python 3.8+
• NumPy, Pandas, Matplotlib (see requirements.txt)

For more information, see README.md
    """)


def main():
    """Main application entry point."""
    while True:
        try:
            show_menu()
            choice = input("Enter choice (1-5): ").strip()
            
            if choice == "1":
                run_demo_simulation()
            elif choice == "2":
                run_full_simulation()
            elif choice == "3":
                run_custom_simulation()
            elif choice == "4":
                show_help()
            elif choice == "5":
                print("\nThank you for using the Hydroponic Simulation System!")
                print("Goodbye! 🌱")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
                
        except KeyboardInterrupt:
            print("\n\nExiting application...")
            sys.exit(0)
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or contact support.")


if __name__ == "__main__":
    main()