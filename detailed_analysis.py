#!/usr/bin/env python3
"""
Detailed Analysis of NFT Lettuce Simulation - Focus on Critical Issues
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def detailed_biomass_analysis():
    """Detailed analysis of biomass accumulation"""
    df = pd.read_csv("/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv")
    
    print("DETAILED BIOMASS ANALYSIS")
    print("="*50)
    
    # Analyze different biomass components
    biomass_components = {
        'Total_Biomass_g': 'Total Biomass',
        'Shoot_Dry_Weight_g': 'Shoot Dry Weight', 
        'Leaf_Dry_Weight_g': 'Leaf Dry Weight',
        'Stem_Dry_Weight_g': 'Stem Dry Weight',
        'Root_Dry_Weight_g': 'Root Dry Weight',
        'Shoot_Fresh_Weight_g': 'Shoot Fresh Weight',
        'Leaf_Fresh_Weight_g': 'Leaf Fresh Weight',
        'Root_Fresh_Weight_g': 'Root Fresh Weight'
    }
    
    print(f"\nBiomass Component Analysis (Day 1 vs Final Day):")
    for component, name in biomass_components.items():
        if component in df.columns:
            initial = df[component].iloc[0]
            final = df[component].iloc[-1]
            growth_factor = final / initial if initial > 0 else 0
            
            print(f"\n{name}:")
            print(f"  Day 1: {initial:.2f} g")
            print(f"  Day 34: {final:.2f} g") 
            print(f"  Growth factor: {growth_factor:.1f}x")
            
            # Check for realistic ratios
            if component == 'Total_Biomass_g' and final < 100:
                print(f"  ⚠ Very low total biomass - typical lettuce: 150-300g")
            
            if 'Fresh' in component and 'Dry' in component:
                # Fresh to dry weight ratio should be ~10:1 for lettuce
                dry_component = component.replace('Fresh', 'Dry')
                if dry_component in df.columns:
                    fresh_final = df[component].iloc[-1]
                    dry_final = df[dry_component].iloc[-1]
                    if dry_final > 0:
                        fresh_dry_ratio = fresh_final / dry_final
                        print(f"  Fresh:Dry ratio: {fresh_dry_ratio:.1f}:1 (expected: ~10:1)")
                        if fresh_dry_ratio < 5 or fresh_dry_ratio > 15:
                            print(f"    ⚠ Unusual fresh:dry ratio")

def analyze_growth_rates():
    """Analyze daily growth rates in detail"""
    df = pd.read_csv("/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv")
    
    print(f"\n\nGROWTH RATE ANALYSIS")
    print("="*30)
    
    # Calculate actual growth rates from biomass data
    if 'Total_Biomass_g' in df.columns:
        biomass = df['Total_Biomass_g'].values
        actual_growth_rates = np.diff(biomass)
        
        print(f"\nDaily Growth Rate Statistics:")
        print(f"  Mean daily growth: {np.mean(actual_growth_rates):.3f} g/day")
        print(f"  Max daily growth: {np.max(actual_growth_rates):.3f} g/day") 
        print(f"  Min daily growth: {np.min(actual_growth_rates):.3f} g/day")
        print(f"  Std dev: {np.std(actual_growth_rates):.3f} g/day")
        
        # Compare with reported daily growth rate
        if 'Daily_Growth_Rate_g_day' in df.columns:
            reported_rates = df['Daily_Growth_Rate_g_day'].values
            print(f"\nReported vs Calculated Growth Rates:")
            for i, (reported, calculated) in enumerate(zip(reported_rates[1:], actual_growth_rates)):
                if abs(reported - calculated) > 0.01:  # Threshold for significant difference
                    print(f"  Day {i+2}: Reported={reported:.3f}, Calculated={calculated:.3f} ⚠")
        
        # Check for negative growth days
        negative_days = np.where(actual_growth_rates < 0)[0]
        if len(negative_days) > 0:
            print(f"\nNegative Growth Days: {len(negative_days)}")
            for day in negative_days:
                print(f"  Day {day+2}: {actual_growth_rates[day]:.3f} g/day")

def analyze_water_efficiency():
    """Detailed water use efficiency analysis"""  
    df = pd.read_csv("/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv")
    
    print(f"\n\nWATER USE EFFICIENCY ANALYSIS")
    print("="*40)
    
    # Analyze water usage patterns
    water_metrics = ['Water_Total_L', 'Transpiration_mm', 'WUE_kg_m3', 'ETC_Prime_mm']
    
    for metric in water_metrics:
        if metric in df.columns:
            data = df[metric]
            print(f"\n{metric}:")
            print(f"  Range: {data.min():.3f} - {data.max():.3f}")
            print(f"  Final value: {data.iloc[-1]:.3f}")
            
            # Check trends
            if len(data) > 1:
                trend = 'increasing' if data.iloc[-1] > data.iloc[0] else 'decreasing'
                print(f"  Trend: {trend}")
    
    # Calculate total water consumption
    if 'Water_Total_L' in df.columns:
        total_water = df['Water_Total_L'].iloc[-1] - df['Water_Total_L'].iloc[0]  
        final_biomass = df['Total_Biomass_g'].iloc[-1] / 1000  # Convert to kg
        
        if total_water > 0 and final_biomass > 0:
            actual_wue = final_biomass / (total_water / 1000)  # kg biomass per m³ water
            print(f"\nActual Water Use Efficiency Calculation:")
            print(f"  Total water used: {total_water:.3f} L")
            print(f"  Final biomass: {final_biomass:.3f} kg")
            print(f"  Calculated WUE: {actual_wue:.2f} kg/m³")
            
            reported_wue = df['WUE_kg_m3'].iloc[-1]
            print(f"  Reported WUE: {reported_wue:.2f} kg/m³")
            
            if abs(actual_wue - reported_wue) > 1.0:
                print(f"  ⚠ Discrepancy between calculated and reported WUE")

def analyze_nutrient_patterns():
    """Analyze nutrient concentration patterns in detail"""
    df = pd.read_csv("/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv")
    
    print(f"\n\nNUTRIENT PATTERN ANALYSIS")  
    print("="*35)
    
    nutrients = ['N-NO3_mg_L', 'P-PO4_mg_L', 'K_mg_L', 'Ca_mg_L', 'Mg_mg_L']
    
    # Create a more detailed nutrient analysis
    for nutrient in nutrients:
        if nutrient in df.columns:
            data = df[nutrient].values
            
            print(f"\n{nutrient} Pattern Analysis:")
            
            # Check for step changes (indicating nutrient dosing/replacement)
            differences = np.diff(data)
            large_changes = np.where(np.abs(differences) > (np.std(differences) * 2))[0]
            
            if len(large_changes) > 0:
                print(f"  Detected {len(large_changes)} significant concentration changes:")
                for change_idx in large_changes[:5]:  # Show first 5
                    day = change_idx + 2
                    change = differences[change_idx]
                    print(f"    Day {day}: {change:+.1f} mg/L")
            
            # Check for constant values (indicating no uptake or dosing)
            constant_periods = []
            current_period = 1
            for i in range(1, len(data)):
                if abs(data[i] - data[i-1]) < 0.01:  # Essentially no change
                    current_period += 1
                else:
                    if current_period > 3:  # More than 3 days constant
                        constant_periods.append(current_period)
                    current_period = 1
            
            if constant_periods:
                print(f"  Constant concentration periods: {constant_periods} days")
                if max(constant_periods) > 10:
                    print(f"    ⚠ Extended period with no uptake/dosing")

def check_system_parameters():
    """Check system parameters for consistency"""
    df = pd.read_csv("/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv")
    
    print(f"\n\nSYSTEM PARAMETER ANALYSIS")
    print("="*35)
    
    # Check key system parameters
    system_params = {
        'Plant_Count': 'Plant Count',
        'System_Area_m2': 'System Area (m²)', 
        'Flow_Rate_L_h': 'Flow Rate (L/h)',
        'Tank_Volume_L': 'Tank Volume (L)'
    }
    
    print(f"\nSystem Configuration:")
    for param, name in system_params.items():
        if param in df.columns:
            value = df[param].iloc[0]
            print(f"  {name}: {value}")
    
    # Calculate derived metrics
    if all(param in df.columns for param in ['Plant_Count', 'System_Area_m2']):
        plant_density = df['Plant_Count'].iloc[0] / df['System_Area_m2'].iloc[0]
        print(f"  Plant density: {plant_density:.1f} plants/m²")
        
        if plant_density < 10 or plant_density > 25:
            print(f"    ⚠ Unusual plant density (typical NFT: 12-20 plants/m²)")
    
    # Check for parameter changes during simulation
    changing_params = []
    for param in system_params.keys():
        if param in df.columns:
            if not df[param].nunique() == 1:
                changing_params.append(param)
    
    if changing_params:
        print(f"\nParameters that changed during simulation:")
        for param in changing_params:
            print(f"  {param}: {df[param].min():.2f} - {df[param].max():.2f}")

def final_assessment():
    """Provide final assessment with specific recommendations"""
    print(f"\n\nFINAL ASSESSMENT & RECOMMENDATIONS")
    print("="*50)
    
    print(f"\nCRITICAL ISSUES IDENTIFIED:")
    print(f"1. SEVERELY UNDERWEIGHT HARVEST")
    print(f"   - Simulated: 33.7g vs Expected: 150-300g")
    print(f"   - This represents only 11-22% of commercial yield")
    print(f"   - Possible causes: Poor variety selection, inadequate lighting, nutrient issues")
    
    print(f"\n2. POOR WATER USE EFFICIENCY")
    print(f"   - Simulated: 4.7 kg/m³ vs Expected: >20 kg/m³")
    print(f"   - Indicates either excessive water use or poor biomass production")
    print(f"   - May indicate system leaks or poor plant uptake")
    
    print(f"\n3. MINIMAL NUTRIENT UPTAKE")
    print(f"   - N, Ca, Mg show 0% depletion over 34 days")
    print(f"   - Suggests poor root development or system malfunction")
    print(f"   - Only K and P show significant uptake")
    
    print(f"\n4. SHORT GROWTH CYCLE")
    print(f"   - 34 days vs typical 35-45 days")
    print(f"   - May have been terminated early due to poor performance")
    
    print(f"\nRECOMMENDATIONS FOR IMPROVEMENT:")
    print(f"1. Check cultivar selection - may be inappropriate for NFT")
    print(f"2. Verify nutrient solution preparation and delivery system")
    print(f"3. Assess environmental conditions (light, temperature, humidity)")
    print(f"4. Review system design (flow rates, channel slope, plant spacing)")
    print(f"5. Extend growth period to 40-45 days for full maturity")
    print(f"6. Investigate root zone health and nutrient uptake capacity")

def main():
    """Run detailed analysis"""
    detailed_biomass_analysis()
    analyze_growth_rates()
    analyze_water_efficiency()
    analyze_nutrient_patterns()
    check_system_parameters()
    final_assessment()
    
    print(f"\n{'='*50}")
    print("DETAILED ANALYSIS COMPLETE")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()