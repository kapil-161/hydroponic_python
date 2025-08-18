#!/usr/bin/env python3
"""
Batch Simulation Runner
Runs multiple hydroponic simulations with different parameters for research analysis
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict
import pandas as pd

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.hydroponic_simulator import HydroponicSimulator
from src.data.hydroponic_system import (
    HydroInputData, HydroSystemConfig, CropParameters, DefaultConfigurations
)
from src.utils.weather_generator import WeatherGenerator


class BatchSimulationRunner:
    """Manages and executes multiple hydroponic simulations."""
    
    def __init__(self, output_dir: str = "data/output/batch_results"):
        self.output_dir = output_dir
        self.results = []
        os.makedirs(output_dir, exist_ok=True)
    
    def create_temperature_study(self) -> List[Dict]:
        """Create temperature variation study parameters."""
        return [
            {"name": "Cold_Greenhouse", "base_temp": 15.0, "description": "Cool greenhouse conditions"},
            {"name": "Optimal_Greenhouse", "base_temp": 22.0, "description": "Optimal greenhouse conditions"},
            {"name": "Warm_Greenhouse", "base_temp": 28.0, "description": "Warm greenhouse conditions"},
        ]
    
    def create_tank_size_study(self) -> List[Dict]:
        """Create tank volume variation study parameters."""
        return [
            {"name": "Small_Tank", "tank_volume": 250.0, "description": "Small hydroponic system"},
            {"name": "Medium_Tank", "tank_volume": 500.0, "description": "Standard hydroponic system"},
            {"name": "Large_Tank", "tank_volume": 1000.0, "description": "Large hydroponic system"},
        ]
    
    def create_crop_density_study(self) -> List[Dict]:
        """Create crop density variation study parameters."""
        return [
            {"name": "Low_Density", "phi": 0.65, "description": "Low plant density"},
            {"name": "Medium_Density", "phi": 0.85, "description": "Standard plant density"},
            {"name": "High_Density", "phi": 1.05, "description": "High plant density"},
        ]
    
    def run_parameter_sweep(self, study_type: str = "temperature", days: int = 30):
        """Run parameter sweep study."""
        
        print(f"\n{'='*70}")
        print(f"    BATCH SIMULATION: {study_type.upper()} STUDY")
        print(f"    Running {days}-day simulations")
        print(f"{'='*70}")
        
        # Get study parameters
        if study_type == "temperature":
            studies = self.create_temperature_study()
        elif study_type == "tank_size":
            studies = self.create_tank_size_study()
        elif study_type == "crop_density":
            studies = self.create_crop_density_study()
        else:
            raise ValueError(f"Unknown study type: {study_type}")
        
        # Run simulations
        batch_results = []
        
        for i, study in enumerate(studies, 1):
            print(f"\nRunning simulation {i}/{len(studies)}: {study['name']}")
            print(f"Description: {study['description']}")
            
            # Create input data
            system_config = DefaultConfigurations.get_nft_lettuce_system()
            crop_params = DefaultConfigurations.get_lettuce_parameters()
            nutrient_params = DefaultConfigurations.get_default_nutrients()
            
            # Apply study-specific parameters
            if "base_temp" in study:
                generator = WeatherGenerator(base_temp=study["base_temp"])
            else:
                generator = WeatherGenerator()
            
            if "tank_volume" in study:
                system_config.tank_volume = study["tank_volume"]
            
            if "phi" in study:
                crop_params.phi = study["phi"]
            
            # Generate weather data
            weather_data = generator.generate_weather_series(
                datetime(2024, 4, 11), days
            )
            
            # Create input data
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
            
            # Save individual results
            output_file = f"{self.output_dir}/{study['name']}_simulation.csv"
            simulator.save_results_csv(output_file)
            
            # Extract summary statistics
            summary = {
                "study_name": study['name'],
                "description": study['description'],
                "total_water_consumption_L": results.summary_stats['total_water_consumption_L'],
                "avg_daily_consumption_L": results.summary_stats['average_daily_consumption_L'],
                "final_tank_volume_L": results.summary_stats['final_tank_volume_L'],
                "avg_eto_mm": results.summary_stats['average_eto_mm'],
                "avg_transpiration_mm": results.summary_stats['average_transpiration_mm'],
                "max_temp_C": results.summary_stats['max_temperature_C'],
                "min_temp_C": results.summary_stats['min_temperature_C'],
                "simulation_days": days
            }
            
            # Add study-specific parameters to summary
            for key, value in study.items():
                if key not in ["name", "description"]:
                    summary[f"param_{key}"] = value
            
            batch_results.append(summary)
            
            print(f"  Water consumption: {summary['total_water_consumption_L']:.1f} L")
            print(f"  Average daily: {summary['avg_daily_consumption_L']:.1f} L/day")
            print(f"  Final tank volume: {summary['final_tank_volume_L']:.1f} L")
        
        # Save batch summary
        summary_df = pd.DataFrame(batch_results)
        summary_file = f"{self.output_dir}/{study_type}_study_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        
        # Save batch configuration
        config_file = f"{self.output_dir}/{study_type}_study_config.json"
        with open(config_file, 'w') as f:
            json.dump({
                "study_type": study_type,
                "simulation_days": days,
                "studies": studies,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n{'='*70}")
        print(f"BATCH SIMULATION COMPLETED")
        print(f"Results saved to: {self.output_dir}")
        print(f"Summary file: {summary_file}")
        print(f"Configuration: {config_file}")
        print(f"{'='*70}")
        
        return batch_results
    
    def run_comparison_study(self, days: int = 30):
        """Run comprehensive comparison across multiple parameters."""
        
        print(f"\n{'='*70}")
        print(f"    COMPREHENSIVE COMPARISON STUDY")
        print(f"    Multiple parameter variations")
        print(f"{'='*70}")
        
        # Define parameter combinations
        combinations = [
            {"name": "Baseline", "base_temp": 22.0, "tank_volume": 500.0, "phi": 0.85},
            {"name": "Cold_Small", "base_temp": 18.0, "tank_volume": 250.0, "phi": 0.85},
            {"name": "Hot_Large", "base_temp": 26.0, "tank_volume": 1000.0, "phi": 0.85},
            {"name": "Optimal_Dense", "base_temp": 22.0, "tank_volume": 500.0, "phi": 1.0},
            {"name": "Cool_Sparse", "base_temp": 20.0, "tank_volume": 750.0, "phi": 0.7},
        ]
        
        batch_results = []
        
        for i, combo in enumerate(combinations, 1):
            print(f"\nRunning combination {i}/{len(combinations)}: {combo['name']}")
            
            # Setup simulation
            system_config = DefaultConfigurations.get_nft_lettuce_system()
            crop_params = DefaultConfigurations.get_lettuce_parameters()
            nutrient_params = DefaultConfigurations.get_default_nutrients()
            
            # Apply parameters
            system_config.tank_volume = combo["tank_volume"]
            crop_params.phi = combo["phi"]
            
            generator = WeatherGenerator(base_temp=combo["base_temp"])
            weather_data = generator.generate_weather_series(datetime(2024, 4, 11), days)
            
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
            
            # Save results
            output_file = f"{self.output_dir}/comparison_{combo['name']}.csv"
            simulator.save_results_csv(output_file)
            
            # Extract summary
            summary = {
                "combination": combo['name'],
                "base_temp": combo['base_temp'],
                "tank_volume": combo['tank_volume'], 
                "phi": combo['phi'],
                "total_water_L": results.summary_stats['total_water_consumption_L'],
                "water_per_day_L": results.summary_stats['average_daily_consumption_L'],
                "final_volume_L": results.summary_stats['final_tank_volume_L'],
                "avg_eto_mm": results.summary_stats['average_eto_mm'],
                "water_use_efficiency": results.summary_stats['average_wue_kg_m3']
            }
            
            batch_results.append(summary)
            print(f"  Total water: {summary['total_water_L']:.1f} L")
            print(f"  WUE: {summary['water_use_efficiency']:.2f} kg/m³")
        
        # Save comparison results
        comparison_df = pd.DataFrame(batch_results)
        comparison_file = f"{self.output_dir}/comparison_study_results.csv"
        comparison_df.to_csv(comparison_file, index=False)
        
        print(f"\n{'='*70}")
        print(f"COMPARISON STUDY COMPLETED")
        print(f"Results: {comparison_file}")
        print(f"{'='*70}")
        
        return batch_results


def main():
    """Main batch simulation interface."""
    print("HYDROPONIC BATCH SIMULATION SYSTEM")
    print("Advanced Parameter Study Tool")
    
    runner = BatchSimulationRunner()
    
    print("\nSelect study type:")
    print("1. Temperature Study (15°C, 22°C, 28°C)")
    print("2. Tank Size Study (250L, 500L, 1000L)")
    print("3. Crop Density Study (Low, Medium, High)")
    print("4. Comprehensive Comparison")
    print("5. Exit")
    
    while True:
        try:
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == "1":
                runner.run_parameter_sweep("temperature", 30)
                break
            elif choice == "2":
                runner.run_parameter_sweep("tank_size", 30)
                break
            elif choice == "3":
                runner.run_parameter_sweep("crop_density", 30)
                break
            elif choice == "4":
                runner.run_comparison_study(30)
                break
            elif choice == "5":
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()