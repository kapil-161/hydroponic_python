#!/usr/bin/env python3
"""
Simplified Realism Analysis for Hydroponic Simulation Results
Analyzes LET_EXP001_2024_results.csv for agricultural accuracy and realistic ranges
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_and_analyze_data():
    """Load the CSV file and analyze realism"""
    file_path = "/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv"
    
    # Read CSV file
    df = pd.read_csv(file_path)
    
    # Convert Date column to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    return df

def analyze_key_metrics(df):
    """Analyze key metrics with range analysis"""
    
    print("="*80)
    print("NFT LETTUCE SIMULATION - REALISM ANALYSIS")
    print("="*80)
    
    # Basic info
    print(f"\nSIMULATION OVERVIEW:")
    print(f"- Simulation period: {df['Date'].min()} to {df['Date'].max()}")
    print(f"- Duration: {df['Day'].max()} days")
    print(f"- Data points: {len(df)}")
    print(f"- System type: {df['System_Type'].iloc[0]}")
    print(f"- Plant count: {df['Plant_Count'].iloc[0]}")
    print(f"- System area: {df['System_Area_m2'].iloc[0]} m²")
    
    # Key metrics to analyze
    key_metrics = {
        'Total_Biomass_g': {'name': 'Total Biomass', 'unit': 'g', 'expected_range': (0, 300)},
        'Plant_Height_cm': {'name': 'Plant Height', 'unit': 'cm', 'expected_range': (5, 20)},
        'LAI': {'name': 'Leaf Area Index', 'unit': '', 'expected_range': (0, 4.0)},
        'Shoot_Fresh_Weight_g': {'name': 'Shoot Fresh Weight', 'unit': 'g', 'expected_range': (0, 250)},
        'Leaf_Fresh_Weight_g': {'name': 'Leaf Fresh Weight', 'unit': 'g', 'expected_range': (0, 200)},
        'Root_Fresh_Weight_g': {'name': 'Root Fresh Weight', 'unit': 'g', 'expected_range': (0, 50)},
        'Daily_Growth_Rate_g_day': {'name': 'Daily Growth Rate', 'unit': 'g/day', 'expected_range': (0, 15)},
        'WUE_L_kg': {'name': 'Water Use Efficiency', 'unit': 'L/kg', 'expected_range': (0.01, 0.1)},
        'N-NO3_mg_L': {'name': 'Nitrogen Concentration', 'unit': 'mg/L', 'expected_range': (50, 300)},
        'P-PO4_mg_L': {'name': 'Phosphorus Concentration', 'unit': 'mg/L', 'expected_range': (10, 100)},
        'K_mg_L': {'name': 'Potassium Concentration', 'unit': 'mg/L', 'expected_range': (100, 400)},
        'Ca_mg_L': {'name': 'Calcium Concentration', 'unit': 'mg/L', 'expected_range': (40, 150)},
        'Mg_mg_L': {'name': 'Magnesium Concentration', 'unit': 'mg/L', 'expected_range': (10, 50)},
        'pH': {'name': 'pH', 'unit': '', 'expected_range': (5.5, 7.0)},
        'EC': {'name': 'Electrical Conductivity', 'unit': 'dS/m', 'expected_range': (1.0, 5.0)},
        'Temp_C': {'name': 'Temperature', 'unit': '°C', 'expected_range': (17, 30)},
        'VPD_kPa': {'name': 'Vapor Pressure Deficit', 'unit': 'kPa', 'expected_range': (0.4, 1.5)},
    }
    
    print(f"\n1. RANGE ANALYSIS FOR KEY METRICS:")
    print("="*50)
    
    analysis_results = {}
    
    for metric, info in key_metrics.items():
        if metric in df.columns:
            data = df[metric].dropna()
            
            if len(data) > 0:
                min_val = data.min()
                max_val = data.max()
                mean_val = data.mean()
                std_val = data.std()
                
                expected_min, expected_max = info['expected_range']
                
                # Check if values are within expected range
                within_range = (min_val >= expected_min) and (max_val <= expected_max)
                
                # Check for outliers (values beyond 3 standard deviations)
                outliers = data[(data < (mean_val - 3*std_val)) | (data > (mean_val + 3*std_val))]
                
                analysis_results[metric] = {
                    'min': min_val,
                    'max': max_val,
                    'mean': mean_val,
                    'std': std_val,
                    'within_range': within_range,
                    'outliers': len(outliers),
                    'expected_range': info['expected_range']
                }
                
                print(f"\n{info['name']} ({info['unit']}):")
                print(f"  Range: {min_val:.3f} - {max_val:.3f}")
                print(f"  Mean ± Std: {mean_val:.3f} ± {std_val:.3f}")
                print(f"  Expected: {expected_min} - {expected_max}")
                print(f"  Within expected range: {'✓' if within_range else '✗'}")
                if not within_range:
                    if min_val < expected_min:
                        print(f"    ⚠ Minimum value ({min_val:.3f}) below expected ({expected_min})")
                    if max_val > expected_max:
                        print(f"    ⚠ Maximum value ({max_val:.3f}) above expected ({expected_max})")
                if len(outliers) > 0:
                    print(f"  Outliers detected: {len(outliers)} values")
    
    return analysis_results

def analyze_growth_progression(df):
    """Analyze growth progression over time"""
    print(f"\n2. GROWTH PROGRESSION ANALYSIS:")
    print("="*40)
    
    # Check for monotonic increase in key growth metrics
    growth_metrics = ['Total_Biomass_g', 'Plant_Height_cm', 'LAI', 'Shoot_Fresh_Weight_g']
    
    for metric in growth_metrics:
        if metric in df.columns:
            data = df[metric].dropna()
            
            # Check for monotonic increase
            is_increasing = all(data.iloc[i] >= data.iloc[i-1] for i in range(1, len(data)))
            
            # Calculate growth rate consistency
            growth_rates = data.diff().dropna()
            negative_growth_days = (growth_rates < 0).sum()
            
            print(f"\n{metric}:")
            print(f"  Initial value: {data.iloc[0]:.3f}")
            print(f"  Final value: {data.iloc[-1]:.3f}")
            print(f"  Total growth: {data.iloc[-1] - data.iloc[0]:.3f}")
            print(f"  Monotonic increase: {'✓' if is_increasing else '✗'}")
            if negative_growth_days > 0:
                print(f"  Days with negative growth: {negative_growth_days}")

def analyze_harvest_metrics(df):
    """Analyze final harvest metrics against commercial standards"""
    print(f"\n3. HARVEST METRICS vs COMMERCIAL STANDARDS:")
    print("="*50)
    
    final_day = df.iloc[-1]
    
    # Commercial standards for NFT lettuce
    standards = {
        'Final fresh weight': {
            'simulated': final_day['Shoot_Fresh_Weight_g'] if 'Shoot_Fresh_Weight_g' in df.columns else 0,
            'expected_range': (150, 300),
            'unit': 'g'
        },
        'Plant height': {
            'simulated': final_day['Plant_Height_cm'] if 'Plant_Height_cm' in df.columns else 0,
            'expected_range': (12, 15),
            'unit': 'cm'
        },
        'Growth cycle duration': {
            'simulated': df['Day'].max(),
            'expected_range': (35, 45),
            'unit': 'days'
        },
        'Water use efficiency': {
            'simulated': final_day['WUE_L_kg'] if 'WUE_L_kg' in df.columns else 0,
            'expected_range': (0.02, 0.08),
            'unit': 'L/kg'
        },
        'Leaf area index': {
            'simulated': final_day['LAI'] if 'LAI' in df.columns else 0,
            'expected_range': (0.8, 1.2),
            'unit': ''
        }
    }
    
    for metric, data in standards.items():
        simulated = data['simulated']
        expected_min, expected_max = data['expected_range']
        within_standard = expected_min <= simulated <= expected_max
        
        print(f"\n{metric}:")
        print(f"  Simulated: {simulated:.2f} {data['unit']}")
        print(f"  Commercial standard: {expected_min}-{expected_max} {data['unit']}")
        print(f"  Meets standard: {'✓' if within_standard else '✗'}")
        
        if not within_standard:
            if simulated < expected_min:
                print(f"    ⚠ Below commercial standard ({simulated:.2f} < {expected_min})")
            else:
                print(f"    ⚠ Above commercial standard ({simulated:.2f} > {expected_max})")

def analyze_nutrient_depletion(df):
    """Analyze nutrient depletion patterns"""
    print(f"\n4. NUTRIENT DEPLETION ANALYSIS:")
    print("="*40)
    
    nutrients = ['N-NO3_mg_L', 'P-PO4_mg_L', 'K_mg_L', 'Ca_mg_L', 'Mg_mg_L']
    
    for nutrient in nutrients:
        if nutrient in df.columns:
            initial = df[nutrient].iloc[0]
            final = df[nutrient].iloc[-1]
            depletion = initial - final
            depletion_pct = (depletion / initial) * 100 if initial > 0 else 0
            
            print(f"\n{nutrient}:")
            print(f"  Initial: {initial:.1f} mg/L")
            print(f"  Final: {final:.1f} mg/L")
            print(f"  Depletion: {depletion:.1f} mg/L ({depletion_pct:.1f}%)")
            
            # Check for realistic depletion patterns
            if depletion_pct > 90:
                print(f"    ⚠ Excessive depletion (>{depletion_pct:.1f}%)")
            elif depletion_pct < 5:
                print(f"    ⚠ Minimal depletion (<{depletion_pct:.1f}%) - may indicate poor uptake")

def identify_issues(df):
    """Identify potential issues with simulation accuracy"""
    print(f"\n5. POTENTIAL ISSUES IDENTIFIED:")
    print("="*40)
    
    issues = []
    
    # Check for unrealistic values
    if 'Total_Biomass_g' in df.columns:
        max_biomass = df['Total_Biomass_g'].max()
        if max_biomass > 500:
            issues.append(f"Unrealistically high biomass: {max_biomass:.1f}g (typical NFT lettuce: 150-300g)")
        elif max_biomass < 50:
            issues.append(f"Unrealistically low biomass: {max_biomass:.1f}g (typical NFT lettuce: 150-300g)")
    
    # Check growth rates
    if 'Daily_Growth_Rate_g_day' in df.columns:
        max_growth_rate = df['Daily_Growth_Rate_g_day'].max()
        if max_growth_rate > 20:
            issues.append(f"Unrealistically high daily growth rate: {max_growth_rate:.1f}g/day")
    
    # Check water use efficiency
    if 'WUE_L_kg' in df.columns:
        wue_values = df['WUE_L_kg'].dropna()
        if len(wue_values) > 0:
            max_wue = wue_values.max()
            min_wue = wue_values.min()
            if max_wue > 0.2:
                issues.append(f"Unrealistically high WUE: {max_wue:.3f} L/kg")
            if min_wue < 0.001:
                issues.append(f"Unrealistically low WUE: {min_wue:.3f} L/kg")
    
    # Check for missing data
    total_rows = len(df)
    for col in ['Total_Biomass_g', 'Plant_Height_cm', 'LAI']:
        if col in df.columns:
            missing = df[col].isna().sum()
            if missing > 0:
                issues.append(f"Missing data in {col}: {missing}/{total_rows} values")
    
    # Check simulation duration
    duration = df['Day'].max()
    if duration < 25:
        issues.append(f"Short simulation duration: {duration} days (typical: 35-45 days)")
    elif duration > 60:
        issues.append(f"Long simulation duration: {duration} days (typical: 35-45 days)")
    
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    else:
        print("No major issues identified.")

def analyze_environmental_factors(df):
    """Analyze environmental factor ranges"""
    print(f"\n6. ENVIRONMENTAL FACTOR ANALYSIS:")
    print("="*40)
    
    env_factors = {
        'Temp_C': {'name': 'Temperature', 'unit': '°C', 'optimal_range': (20, 25)},
        'VPD_kPa': {'name': 'VPD', 'unit': 'kPa', 'optimal_range': (0.8, 1.2)},
        'Solar_Rad_MJ': {'name': 'Solar Radiation', 'unit': 'MJ/m²/day', 'optimal_range': (15, 30)},
        'pH': {'name': 'pH', 'unit': '', 'optimal_range': (5.5, 6.5)},
        'EC': {'name': 'EC', 'unit': 'dS/m', 'optimal_range': (1.5, 2.5)}
    }
    
    for factor, info in env_factors.items():
        if factor in df.columns:
            data = df[factor].dropna()
            if len(data) > 0:
                mean_val = data.mean()
                min_val = data.min()
                max_val = data.max()
                optimal_min, optimal_max = info['optimal_range']
                
                print(f"\n{info['name']} ({info['unit']}):")
                print(f"  Range: {min_val:.2f} - {max_val:.2f}")
                print(f"  Mean: {mean_val:.2f}")
                print(f"  Optimal range: {optimal_min} - {optimal_max}")
                
                # Check if mostly within optimal range
                within_optimal = ((data >= optimal_min) & (data <= optimal_max)).sum()
                pct_optimal = (within_optimal / len(data)) * 100
                print(f"  Within optimal: {pct_optimal:.1f}% of time")

def generate_summary_report(df):
    """Generate overall assessment summary"""
    print(f"\n7. OVERALL ASSESSMENT:")
    print("="*30)
    
    final_values = df.iloc[-1]
    
    # Calculate overall score based on multiple factors
    score_components = []
    
    # Harvest weight score (use fresh weight, not dry weight)
    if 'Shoot_Fresh_Weight_g' in df.columns:
        final_weight = final_values['Shoot_Fresh_Weight_g']
        if 150 <= final_weight <= 300:
            score_components.append(('Harvest weight', 10))
        elif 100 <= final_weight < 150 or 300 < final_weight <= 400:
            score_components.append(('Harvest weight', 7))
        else:
            score_components.append(('Harvest weight', 3))
    
    # Growth duration score
    duration = df['Day'].max()
    if 35 <= duration <= 45:
        score_components.append(('Growth duration', 10))
    elif 30 <= duration < 35 or 45 < duration <= 50:
        score_components.append(('Growth duration', 7))
    else:
        score_components.append(('Growth duration', 3))
    
    # Water efficiency score
    if 'WUE_L_kg' in df.columns:
        final_wue = final_values['WUE_L_kg']
        if final_wue >= 0.02:
            score_components.append(('Water efficiency', 10))
        elif final_wue >= 0.01:
            score_components.append(('Water efficiency', 7))
        else:
            score_components.append(('Water efficiency', 3))
    
    # Growth consistency score
    if 'Total_Biomass_g' in df.columns:
        biomass_data = df['Total_Biomass_g'].dropna()
        growth_rates = biomass_data.diff().dropna()
        negative_days = (growth_rates < 0).sum()
        if negative_days == 0:
            score_components.append(('Growth consistency', 10))
        elif negative_days <= 2:
            score_components.append(('Growth consistency', 7))
        else:
            score_components.append(('Growth consistency', 3))
    
    # Calculate overall score
    if score_components:
        total_score = sum(score for _, score in score_components)
        max_score = len(score_components) * 10
        overall_score = (total_score / max_score) * 100
        
        print(f"\nSCORE BREAKDOWN:")
        for component, score in score_components:
            print(f"  {component}: {score}/10")
        
        print(f"\nOVERALL SIMULATION ACCURACY: {overall_score:.1f}%")
        
        if overall_score >= 80:
            print("✓ EXCELLENT - Simulation represents realistic NFT lettuce production")
        elif overall_score >= 60:
            print("⚠ GOOD - Simulation mostly realistic with some concerns")
        else:
            print("✗ POOR - Simulation has significant accuracy issues")

def main():
    """Main analysis function"""
    try:
        # Load data
        df = load_and_analyze_data()
        
        # Perform comprehensive analysis
        analysis_results = analyze_key_metrics(df)
        analyze_growth_progression(df)
        analyze_harvest_metrics(df)
        analyze_nutrient_depletion(df)
        analyze_environmental_factors(df)
        identify_issues(df)
        generate_summary_report(df)
        
        print(f"\n{'='*80}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    main()