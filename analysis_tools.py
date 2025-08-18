#!/usr/bin/env python3
"""
Analysis Tools for Hydroponic Simulation Results
Data analysis, visualization, and reporting utilities
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import json
from datetime import datetime

# Optional imports for visualization
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available. Visualization features disabled.")


class HydroponicAnalyzer:
    """Analysis tools for hydroponic simulation results."""
    
    def __init__(self, results_file: str):
        """Initialize analyzer with results CSV file."""
        self.results_file = results_file
        self.df = pd.read_csv(results_file)
        
        # Convert date column if present
        if 'Date' in self.df.columns:
            self.df['Date'] = pd.to_datetime(self.df['Date'])
    
    def generate_summary_report(self) -> Dict:
        """Generate comprehensive summary statistics."""
        
        summary = {
            "simulation_info": {
                "total_days": len(self.df),
                "start_date": self.df['Date'].min().strftime('%Y-%m-%d') if 'Date' in self.df.columns else "N/A",
                "end_date": self.df['Date'].max().strftime('%Y-%m-%d') if 'Date' in self.df.columns else "N/A",
                "system_id": self.df['System_ID'].iloc[0] if 'System_ID' in self.df.columns else "N/A",
                "crop_id": self.df['Crop_ID'].iloc[0] if 'Crop_ID' in self.df.columns else "N/A"
            },
            
            "water_management": {
                "total_consumption_L": self.df['Water_Total_L'].sum() if 'Water_Total_L' in self.df.columns else 0,
                "avg_daily_consumption_L": self.df['Water_Total_L'].mean() if 'Water_Total_L' in self.df.columns else 0,
                "peak_daily_consumption_L": self.df['Water_Total_L'].max() if 'Water_Total_L' in self.df.columns else 0,
                "min_daily_consumption_L": self.df['Water_Total_L'].min() if 'Water_Total_L' in self.df.columns else 0,
                "initial_tank_volume_L": self.df['Tank_Volume_L'].iloc[0] if 'Tank_Volume_L' in self.df.columns else 0,
                "final_tank_volume_L": self.df['Tank_Volume_L'].iloc[-1] if 'Tank_Volume_L' in self.df.columns else 0,
                "volume_reduction_L": self.df['Tank_Volume_L'].iloc[0] - self.df['Tank_Volume_L'].iloc[-1] if 'Tank_Volume_L' in self.df.columns else 0
            },
            
            "evapotranspiration": {
                "avg_eto_ref_mm": self.df['ETO_Ref_mm'].mean() if 'ETO_Ref_mm' in self.df.columns else 0,
                "avg_etc_prime_mm": self.df['ETC_Prime_mm'].mean() if 'ETC_Prime_mm' in self.df.columns else 0,
                "avg_transpiration_mm": self.df['Transpiration_mm'].mean() if 'Transpiration_mm' in self.df.columns else 0,
                "max_eto_ref_mm": self.df['ETO_Ref_mm'].max() if 'ETO_Ref_mm' in self.df.columns else 0,
                "min_eto_ref_mm": self.df['ETO_Ref_mm'].min() if 'ETO_Ref_mm' in self.df.columns else 0
            },
            
            "environmental_conditions": {
                "avg_temperature_C": self.df['Temp_C'].mean() if 'Temp_C' in self.df.columns else 0,
                "max_temperature_C": self.df['Temp_C'].max() if 'Temp_C' in self.df.columns else 0,
                "min_temperature_C": self.df['Temp_C'].min() if 'Temp_C' in self.df.columns else 0,
                "avg_solar_radiation_MJ": self.df['Solar_Rad_MJ'].mean() if 'Solar_Rad_MJ' in self.df.columns else 0,
                "avg_vpd_kPa": self.df['VPD_kPa'].mean() if 'VPD_kPa' in self.df.columns else 0
            },
            
            "performance_metrics": {
                "avg_water_use_efficiency": self.df['WUE_kg_m3'].mean() if 'WUE_kg_m3' in self.df.columns else 0,
                "water_productivity_kg_m3": self.df['WUE_kg_m3'].max() if 'WUE_kg_m3' in self.df.columns else 0
            }
        }
        
        # Add nutrient analysis if nutrient columns present
        nutrient_cols = [col for col in self.df.columns if col.endswith('_mg_L')]
        if nutrient_cols:
            summary["nutrients"] = {}
            for col in nutrient_cols:
                nutrient_name = col.replace('_mg_L', '')
                summary["nutrients"][nutrient_name] = {
                    "initial_conc_mg_L": self.df[col].iloc[0],
                    "final_conc_mg_L": self.df[col].iloc[-1],
                    "concentration_change_mg_L": self.df[col].iloc[-1] - self.df[col].iloc[0],
                    "avg_conc_mg_L": self.df[col].mean(),
                    "max_conc_mg_L": self.df[col].max(),
                    "min_conc_mg_L": self.df[col].min()
                }
        
        return summary
    
    def print_summary_report(self):
        """Print formatted summary report to console."""
        summary = self.generate_summary_report()
        
        print("\n" + "="*80)
        print("    HYDROPONIC SIMULATION ANALYSIS REPORT")
        print("="*80)
        
        # Simulation Info
        print(f"\nSIMULATION INFORMATION:")
        print(f"  Total Days: {summary['simulation_info']['total_days']}")
        print(f"  Period: {summary['simulation_info']['start_date']} to {summary['simulation_info']['end_date']}")
        print(f"  System: {summary['simulation_info']['system_id']}")
        print(f"  Crop: {summary['simulation_info']['crop_id']}")
        
        # Water Management
        print(f"\nWATER MANAGEMENT:")
        print(f"  Total Consumption: {summary['water_management']['total_consumption_L']:.1f} L")
        print(f"  Average Daily: {summary['water_management']['avg_daily_consumption_L']:.1f} L/day")
        print(f"  Peak Daily: {summary['water_management']['peak_daily_consumption_L']:.1f} L/day")
        print(f"  Tank Volume Change: {summary['water_management']['initial_tank_volume_L']:.1f} → {summary['water_management']['final_tank_volume_L']:.1f} L")
        print(f"  Volume Reduction: {summary['water_management']['volume_reduction_L']:.1f} L")
        
        # Evapotranspiration
        print(f"\nEVAPOTRANSPIRATION:")
        print(f"  Average Reference ET: {summary['evapotranspiration']['avg_eto_ref_mm']:.2f} mm/day")
        print(f"  Average Crop ET: {summary['evapotranspiration']['avg_etc_prime_mm']:.2f} mm/day")
        print(f"  Average Transpiration: {summary['evapotranspiration']['avg_transpiration_mm']:.2f} mm/day")
        print(f"  ET Range: {summary['evapotranspiration']['min_eto_ref_mm']:.2f} - {summary['evapotranspiration']['max_eto_ref_mm']:.2f} mm/day")
        
        # Environmental
        print(f"\nENVIRONMENTAL CONDITIONS:")
        print(f"  Temperature: {summary['environmental_conditions']['min_temperature_C']:.1f} - {summary['environmental_conditions']['max_temperature_C']:.1f} °C (avg {summary['environmental_conditions']['avg_temperature_C']:.1f})")
        print(f"  Average Solar Radiation: {summary['environmental_conditions']['avg_solar_radiation_MJ']:.1f} MJ/m²/day")
        print(f"  Average VPD: {summary['environmental_conditions']['avg_vpd_kPa']:.2f} kPa")
        
        # Performance
        print(f"\nPERFORMANCE METRICS:")
        print(f"  Water Use Efficiency: {summary['performance_metrics']['avg_water_use_efficiency']:.2f} kg/m³")
        
        # Nutrients
        if "nutrients" in summary:
            print(f"\nNUTRIENT ANALYSIS:")
            for nutrient, data in summary["nutrients"].items():
                print(f"  {nutrient}:")
                print(f"    Concentration Change: {data['initial_conc_mg_L']:.1f} → {data['final_conc_mg_L']:.1f} mg/L ({data['concentration_change_mg_L']:.1f})")
                print(f"    Average: {data['avg_conc_mg_L']:.1f} mg/L")
        
        print("="*80)
    
    def save_analysis_report(self, output_file: str):
        """Save analysis report to JSON file."""
        summary = self.generate_summary_report()
        
        # Add metadata
        summary["analysis_metadata"] = {
            "source_file": self.results_file,
            "analysis_timestamp": datetime.now().isoformat(),
            "analyzer_version": "1.0"
        }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"Analysis report saved to: {output_file}")
    
    def create_visualizations(self, output_dir: str = "data/output/plots"):
        """Create visualization plots if matplotlib is available."""
        
        if not HAS_MATPLOTLIB:
            print("Matplotlib not available. Skipping visualizations.")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up plot style
        plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
        
        # Plot 1: Daily water consumption and tank volume
        if 'Water_Total_L' in self.df.columns and 'Tank_Volume_L' in self.df.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Water consumption
            ax1.plot(self.df['Day'] if 'Day' in self.df.columns else range(len(self.df)), 
                    self.df['Water_Total_L'], 'b-', linewidth=2, marker='o', markersize=4)
            ax1.set_title('Daily Water Consumption', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Water Consumption (L/day)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            
            # Tank volume
            ax2.plot(self.df['Day'] if 'Day' in self.df.columns else range(len(self.df)), 
                    self.df['Tank_Volume_L'], 'r-', linewidth=2, marker='s', markersize=4)
            ax2.set_title('Tank Volume Over Time', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Day', fontsize=12)
            ax2.set_ylabel('Tank Volume (L)', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/water_analysis.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # Plot 2: Evapotranspiration components
        et_cols = ['ETO_Ref_mm', 'ETC_Prime_mm', 'Transpiration_mm']
        available_et_cols = [col for col in et_cols if col in self.df.columns]
        
        if available_et_cols:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            days = self.df['Day'] if 'Day' in self.df.columns else range(len(self.df))
            
            for col in available_et_cols:
                label = col.replace('_mm', '').replace('_', ' ')
                ax.plot(days, self.df[col], linewidth=2, marker='o', markersize=3, label=label)
            
            ax.set_title('Evapotranspiration Components', fontsize=14, fontweight='bold')
            ax.set_xlabel('Day', fontsize=12)
            ax.set_ylabel('Evapotranspiration (mm/day)', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/evapotranspiration.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # Plot 3: Nutrient concentrations
        nutrient_cols = [col for col in self.df.columns if col.endswith('_mg_L')]
        
        if nutrient_cols:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            days = self.df['Day'] if 'Day' in self.df.columns else range(len(self.df))
            
            for col in nutrient_cols[:5]:  # Limit to first 5 nutrients for readability
                nutrient_name = col.replace('_mg_L', '')
                ax.plot(days, self.df[col], linewidth=2, marker='o', markersize=3, label=nutrient_name)
            
            ax.set_title('Nutrient Concentrations Over Time', fontsize=14, fontweight='bold')
            ax.set_xlabel('Day', fontsize=12)
            ax.set_ylabel('Concentration (mg/L)', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/nutrient_concentrations.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # Plot 4: Environmental conditions
        if 'Temp_C' in self.df.columns and 'Solar_Rad_MJ' in self.df.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            days = self.df['Day'] if 'Day' in self.df.columns else range(len(self.df))
            
            # Temperature
            ax1.plot(days, self.df['Temp_C'], 'orange', linewidth=2, marker='o', markersize=4)
            ax1.set_title('Environmental Conditions', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Temperature (°C)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            
            # Solar radiation
            ax2.plot(days, self.df['Solar_Rad_MJ'], 'gold', linewidth=2, marker='s', markersize=4)
            ax2.set_xlabel('Day', fontsize=12)
            ax2.set_ylabel('Solar Radiation (MJ/m²/day)', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/environmental_conditions.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        print(f"Visualization plots saved to: {output_dir}")


def main():
    """Main analysis interface."""
    print("HYDROPONIC SIMULATION ANALYSIS TOOLS")
    print("Data Analysis and Reporting System")
    
    # Get results file
    results_file = input("\nEnter path to results CSV file: ").strip()
    
    if not os.path.exists(results_file):
        print(f"Error: File {results_file} not found.")
        return
    
    # Initialize analyzer
    try:
        analyzer = HydroponicAnalyzer(results_file)
        print(f"Loaded {len(analyzer.df)} data points from {results_file}")
    except Exception as e:
        print(f"Error loading file: {e}")
        return
    
    # Analysis options
    print("\nSelect analysis options:")
    print("1. Generate summary report")
    print("2. Create visualizations")
    print("3. Save analysis to JSON")
    print("4. All of the above")
    
    choice = input("Enter choice (1-4): ").strip()
    
    try:
        if choice in ["1", "4"]:
            analyzer.print_summary_report()
        
        if choice in ["2", "4"]:
            analyzer.create_visualizations()
        
        if choice in ["3", "4"]:
            output_file = "data/output/analysis_report.json"
            os.makedirs("data/output", exist_ok=True)
            analyzer.save_analysis_report(output_file)
        
        print("\nAnalysis completed successfully!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")


if __name__ == "__main__":
    main()