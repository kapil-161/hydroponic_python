#!/usr/bin/env python3
"""
COMPREHENSIVE IN-DEPTH ANALYSIS of Hydroponic Simulation Results
Examines ALL aspects of the simulation for complete realism assessment
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_data():
    """Load the complete dataset"""
    file_path = "/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv"
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'])
    return df

def analyze_physiological_processes(df):
    """Deep dive into physiological processes"""
    print("="*80)
    print("🔬 COMPREHENSIVE PHYSIOLOGICAL PROCESS ANALYSIS")
    print("="*80)
    
    # Photosynthesis Analysis
    print("\n1. PHOTOSYNTHESIS ANALYSIS:")
    print("-" * 40)
    
    photo_cols = ['Photosynthesis_Rate', 'Net_Assimilation', 'Rubisco_Limited_umol_m2_s', 
                  'Light_Limited_umol_m2_s', 'Vcmax_25_umol_m2_s', 'Jmax_25_umol_m2_s']
    
    for col in photo_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                print(f"  Trend: {'Increasing' if data.iloc[-1] > data.iloc[0] else 'Decreasing'}")
                
                # Check for realistic values
                if 'Photosynthesis_Rate' in col:
                    if data.max() > 50:
                        print(f"    ⚠️ Unrealistically high photosynthesis rate")
                    elif data.max() < 0.1:
                        print(f"    ⚠️ Unrealistically low photosynthesis rate")
                
                if 'Vcmax' in col:
                    if data.max() > 200:
                        print(f"    ⚠️ Unrealistically high Vcmax")
                    elif data.max() < 10:
                        print(f"    ⚠️ Unrealistically low Vcmax")
    
    # Respiration Analysis
    print("\n2. RESPIRATION ANALYSIS:")
    print("-" * 40)
    
    resp_cols = ['Respiration_Rate', 'Maintenance_Respiration', 'Growth_Respiration',
                 'Maint_Resp_Leaves', 'Maint_Resp_Stems', 'Maint_Resp_Roots']
    
    for col in resp_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                
                # Check respiration/biomass ratio
                if 'Respiration_Rate' in col and 'Total_Biomass_g' in df.columns:
                    biomass = df['Total_Biomass_g'].dropna()
                    if len(biomass) > 0:
                        resp_biomass_ratio = data.iloc[-1] / biomass.iloc[-1] if biomass.iloc[-1] > 0 else 0
                        print(f"  Respiration/Biomass ratio: {resp_biomass_ratio:.3f}")
                        if resp_biomass_ratio > 0.5:
                            print(f"    ⚠️ Unrealistically high respiration relative to biomass")
                        elif resp_biomass_ratio < 0.01:
                            print(f"    ⚠️ Unrealistically low respiration relative to biomass")

def analyze_stress_factors(df):
    """Comprehensive stress analysis"""
    print("\n3. STRESS FACTOR ANALYSIS:")
    print("-" * 40)
    
    stress_cols = ['Integrated_Stress', 'Temperature_Stress', 'Water_Stress', 
                   'Nutrient_Stress', 'Nitrogen_Stress', 'Salinity_Stress',
                   'Cold_Stress_Factor', 'Heat_Stress_Factor']
    
    for col in stress_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                print(f"  Days > 0.5 (high stress): {(data > 0.5).sum()}")
                print(f"  Days > 0.8 (severe stress): {(data > 0.8).sum()}")
                
                # Analyze stress patterns
                if col == 'Integrated_Stress':
                    avg_stress = data.mean()
                    if avg_stress > 0.5:
                        print(f"    ⚠️ High average stress ({avg_stress:.3f}) - may explain poor growth")
                    elif avg_stress < 0.1:
                        print(f"    ✓ Low stress environment - good for growth")
                
                if 'Temperature_Stress' in col:
                    temp_stress_days = (data > 0.3).sum()
                    print(f"  Days with temperature stress: {temp_stress_days}/{len(data)}")

def analyze_nutrient_dynamics(df):
    """Deep nutrient analysis"""
    print("\n4. NUTRIENT DYNAMICS ANALYSIS:")
    print("-" * 40)
    
    # Nutrient concentrations
    nutrient_cols = ['N-NO3_mg_L', 'P-PO4_mg_L', 'K_mg_L', 'Ca_mg_L', 'Mg_mg_L']
    
    print("\nNutrient Concentrations:")
    for col in nutrient_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                initial = data.iloc[0]
                final = data.iloc[-1]
                change = final - initial
                change_pct = (change / initial * 100) if initial > 0 else 0
                
                print(f"\n{col}:")
                print(f"  Initial: {initial:.1f} mg/L")
                print(f"  Final: {final:.1f} mg/L")
                print(f"  Change: {change:.1f} mg/L ({change_pct:.1f}%)")
                
                # Check for depletion patterns
                if change_pct < -10:
                    print(f"    ⚠️ Significant depletion - good uptake")
                elif change_pct > 5:
                    print(f"    ⚠️ Concentration increased - possible over-fertilization")
                else:
                    print(f"    ⚠️ Minimal change - poor uptake")
    
    # Nutrient uptake rates
    uptake_cols = ['Nitrogen_Uptake_mg', 'Phosphorus_Uptake_mg']
    
    print("\nNutrient Uptake Rates:")
    for col in uptake_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f} mg/day")
                print(f"  Mean: {data.mean():.3f} mg/day")
                print(f"  Total uptake: {data.sum():.1f} mg")
                
                if data.max() < 0.1:
                    print(f"    ⚠️ Extremely low uptake rates")
                elif data.max() > 100:
                    print(f"    ⚠️ Unrealistically high uptake rates")

def analyze_water_dynamics(df):
    """Water and transpiration analysis"""
    print("\n5. WATER DYNAMICS ANALYSIS:")
    print("-" * 40)
    
    water_cols = ['Transpiration_mm', 'Water_Total_L', 'Tank_Volume_L', 'WUE_L_kg']
    
    for col in water_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                
                if col == 'Transpiration_mm':
                    if data.max() > 10:
                        print(f"    ⚠️ Unrealistically high transpiration")
                    elif data.max() < 0.1:
                        print(f"    ⚠️ Unrealistically low transpiration")
                
                if col == 'Tank_Volume_L':
                    initial_vol = data.iloc[0]
                    final_vol = data.iloc[-1]
                    volume_loss = initial_vol - final_vol
                    print(f"  Volume loss: {volume_loss:.1f} L ({volume_loss/initial_vol*100:.1f}%)")
                
                if col == 'WUE_L_kg':
                    if data.max() > 0.1:
                        print(f"    ⚠️ Unrealistically high WUE")
                    elif data.max() < 0.001:
                        print(f"    ⚠️ Unrealistically low WUE")

def analyze_root_architecture(df):
    """Root system analysis"""
    print("\n6. ROOT ARCHITECTURE ANALYSIS:")
    print("-" * 40)
    
    root_cols = ['Fine_Root_Length_cm', 'Coarse_Root_Length_cm', 'Root_Surface_Area_cm2',
                 'Root_Volume_cm3', 'Root_Length_Density_cm_cm3']
    
    for col in root_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                print(f"  Growth: {data.iloc[-1] - data.iloc[0]:.3f}")
                
                # Check root/shoot ratio
                if 'Root_Surface_Area' in col and 'Leaf_Area_m2' in df.columns:
                    root_area = data.iloc[-1] / 10000  # Convert cm² to m²
                    leaf_area = df['Leaf_Area_m2'].iloc[-1]
                    if leaf_area > 0:
                        root_shoot_ratio = root_area / leaf_area
                        print(f"  Root/Leaf area ratio: {root_shoot_ratio:.3f}")
                        if root_shoot_ratio > 2:
                            print(f"    ⚠️ Unrealistically high root/leaf ratio")
                        elif root_shoot_ratio < 0.1:
                            print(f"    ⚠️ Unrealistically low root/leaf ratio")

def analyze_canopy_development(df):
    """Canopy and leaf development analysis"""
    print("\n7. CANOPY DEVELOPMENT ANALYSIS:")
    print("-" * 40)
    
    canopy_cols = ['LAI', 'Leaf_Area_m2', 'Avg_Leaf_Area_cm2', 'Leaf_Number',
                   'Light_Interception', 'Sunlit_LAI', 'Shaded_LAI']
    
    for col in canopy_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                
                if col == 'LAI':
                    if data.max() > 2:
                        print(f"    ⚠️ Unrealistically high LAI for lettuce")
                    elif data.max() < 0.1:
                        print(f"    ⚠️ Unrealistically low LAI")
                
                if col == 'Leaf_Number':
                    if data.max() > 20:
                        print(f"    ⚠️ Unrealistically high leaf number")
                    elif data.max() < 5:
                        print(f"    ⚠️ Unrealistically low leaf number")
                
                if col == 'Light_Interception':
                    if data.max() > 1:
                        print(f"    ⚠️ Light interception > 100% (impossible)")
                    elif data.max() < 0.1:
                        print(f"    ⚠️ Very low light interception")

def analyze_environmental_control(df):
    """Environmental control system analysis"""
    print("\n8. ENVIRONMENTAL CONTROL ANALYSIS:")
    print("-" * 40)
    
    env_cols = ['Temp_C', 'VPD_kPa', 'Solar_Rad_MJ', 'CO2_umol_mol', 'pH', 'EC']
    
    for col in env_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                print(f"  Std Dev: {data.std():.3f}")
                
                # Check for stability
                cv = data.std() / data.mean() if data.mean() > 0 else 0
                if cv > 0.3:
                    print(f"    ⚠️ High variability (CV = {cv:.3f})")
                elif cv < 0.05:
                    print(f"    ⚠️ Unrealistically stable (CV = {cv:.3f})")
                
                # Check optimal ranges
                if col == 'Temp_C':
                    optimal_days = ((data >= 20) & (data <= 25)).sum()
                    print(f"  Days in optimal range (20-25°C): {optimal_days}/{len(data)} ({optimal_days/len(data)*100:.1f}%)")
                
                if col == 'VPD_kPa':
                    optimal_days = ((data >= 0.8) & (data <= 1.2)).sum()
                    print(f"  Days in optimal range (0.8-1.2 kPa): {optimal_days}/{len(data)} ({optimal_days/len(data)*100:.1f}%)")

def analyze_biomass_allocation(df):
    """Biomass allocation analysis"""
    print("\n9. BIOMASS ALLOCATION ANALYSIS:")
    print("-" * 40)
    
    biomass_cols = ['Total_Biomass_g', 'Leaf_Dry_Weight_g', 'Stem_Dry_Weight_g', 'Root_Dry_Weight_g']
    
    # Calculate allocation fractions
    if all(col in df.columns for col in biomass_cols):
        final_values = df[biomass_cols].iloc[-1]
        total_biomass = final_values['Total_Biomass_g']
        
        if total_biomass > 0:
            leaf_fraction = final_values['Leaf_Dry_Weight_g'] / total_biomass
            stem_fraction = final_values['Stem_Dry_Weight_g'] / total_biomass
            root_fraction = final_values['Root_Dry_Weight_g'] / total_biomass
            
            print(f"\nFinal Biomass Allocation:")
            print(f"  Leaf fraction: {leaf_fraction:.3f} ({leaf_fraction*100:.1f}%)")
            print(f"  Stem fraction: {stem_fraction:.3f} ({stem_fraction*100:.1f}%)")
            print(f"  Root fraction: {root_fraction:.3f} ({root_fraction*100:.1f}%)")
            print(f"  Total: {leaf_fraction + stem_fraction + root_fraction:.3f}")
            
            # Check realistic allocation
            if leaf_fraction < 0.3:
                print(f"    ⚠️ Unrealistically low leaf allocation")
            elif leaf_fraction > 0.8:
                print(f"    ⚠️ Unrealistically high leaf allocation")
            
            if root_fraction < 0.05:
                print(f"    ⚠️ Unrealistically low root allocation")
            elif root_fraction > 0.3:
                print(f"    ⚠️ Unrealistically high root allocation")

def analyze_growth_rates(df):
    """Growth rate analysis"""
    print("\n10. GROWTH RATE ANALYSIS:")
    print("-" * 40)
    
    if 'Total_Biomass_g' in df.columns:
        biomass = df['Total_Biomass_g'].dropna()
        
        # Calculate daily growth rates
        daily_growth = biomass.diff().dropna()
        
        print(f"\nDaily Growth Rates:")
        print(f"  Range: {daily_growth.min():.3f} - {daily_growth.max():.3f} g/day")
        print(f"  Mean: {daily_growth.mean():.3f} g/day")
        print(f"  Std Dev: {daily_growth.std():.3f} g/day")
        
        # Check for negative growth
        negative_days = (daily_growth < 0).sum()
        print(f"  Days with negative growth: {negative_days}")
        
        # Calculate relative growth rate
        if len(biomass) > 1:
            initial_biomass = biomass.iloc[0]
            final_biomass = biomass.iloc[-1]
            days = len(biomass) - 1
            rgr = (np.log(final_biomass) - np.log(initial_biomass)) / days
            print(f"  Relative Growth Rate: {rgr:.4f} g/g/day")
            
            if rgr > 0.1:
                print(f"    ⚠️ Unrealistically high RGR")
            elif rgr < 0.01:
                print(f"    ⚠️ Unrealistically low RGR")

def analyze_thermal_time(df):
    """Thermal time and development analysis"""
    print("\n11. THERMAL TIME ANALYSIS:")
    print("-" * 40)
    
    thermal_cols = ['Accumulated_GDD', 'Thermal_Time_Daily', 'Development_Rate']
    
    for col in thermal_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                
                if col == 'Accumulated_GDD':
                    final_gdd = data.iloc[-1]
                    print(f"  Final GDD: {final_gdd:.1f}")
                    
                    # Check against lettuce requirements
                    if final_gdd < 400:
                        print(f"    ⚠️ Low GDD accumulation - may explain slow development")
                    elif final_gdd > 1000:
                        print(f"    ⚠️ High GDD accumulation - may indicate heat stress")
                
                if col == 'Thermal_Time_Daily':
                    avg_daily_gdd = data.mean()
                    print(f"  Average daily GDD: {avg_daily_gdd:.1f}")
                    
                    if avg_daily_gdd < 10:
                        print(f"    ⚠️ Low daily thermal time - cool conditions")
                    elif avg_daily_gdd > 25:
                        print(f"    ⚠️ High daily thermal time - warm conditions")

def analyze_genetic_parameters(df):
    """Genetic parameter analysis"""
    print("\n12. GENETIC PARAMETER ANALYSIS:")
    print("-" * 40)
    
    genetic_cols = ['Cultivar_Adaptation_Index', 'Cultivar_Yield_Potential', 
                    'Genetic_Photosynthesis_Capacity', 'Genetic_EC_Tolerance']
    
    for col in genetic_cols:
        if col in df.columns:
            data = df[col].dropna()
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  Range: {data.min():.3f} - {data.max():.3f}")
                print(f"  Mean: {data.mean():.3f}")
                
                # Check for variation
                if data.std() > 0.1:
                    print(f"    ⚠️ High variation in genetic parameters (should be constant)")
                else:
                    print(f"    ✓ Stable genetic parameters")

def comprehensive_summary(df):
    """Generate comprehensive summary"""
    print("\n" + "="*80)
    print("🎯 COMPREHENSIVE REALISM ASSESSMENT SUMMARY")
    print("="*80)
    
    issues = []
    strengths = []
    
    # Check key metrics
    if 'Total_Biomass_g' in df.columns:
        final_biomass = df['Total_Biomass_g'].iloc[-1]
        if final_biomass < 50:
            issues.append(f"Severely low final biomass ({final_biomass:.1f}g vs expected 150-300g)")
        elif final_biomass > 500:
            issues.append(f"Unrealistically high final biomass ({final_biomass:.1f}g)")
        else:
            strengths.append(f"Realistic final biomass ({final_biomass:.1f}g)")
    
    # Check nutrient uptake
    if 'Nitrogen_Uptake_mg' in df.columns:
        total_n_uptake = df['Nitrogen_Uptake_mg'].sum()
        if total_n_uptake < 1:
            issues.append(f"Minimal nitrogen uptake ({total_n_uptake:.1f}mg total)")
        else:
            strengths.append(f"Active nitrogen uptake ({total_n_uptake:.1f}mg total)")
    
    # Check growth consistency
    if 'Total_Biomass_g' in df.columns:
        biomass = df['Total_Biomass_g'].dropna()
        daily_growth = biomass.diff().dropna()
        negative_days = (daily_growth < 0).sum()
        if negative_days == 0:
            strengths.append("Perfect monotonic growth (no negative growth days)")
        else:
            issues.append(f"Negative growth on {negative_days} days")
    
    # Check environmental stability
    if 'Temp_C' in df.columns:
        temp_cv = df['Temp_C'].std() / df['Temp_C'].mean()
        if temp_cv < 0.1:
            strengths.append("Stable temperature conditions")
        else:
            issues.append(f"High temperature variability (CV = {temp_cv:.3f})")
    
    print(f"\nSTRENGTHS ({len(strengths)}):")
    for i, strength in enumerate(strengths, 1):
        print(f"  {i}. {strength}")
    
    print(f"\nISSUES ({len(issues)}):")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    # Overall assessment
    total_checks = len(strengths) + len(issues)
    if total_checks > 0:
        realism_score = len(strengths) / total_checks * 100
        print(f"\nOVERALL REALISM SCORE: {realism_score:.1f}%")
        
        if realism_score >= 80:
            print("✅ EXCELLENT - Highly realistic simulation")
        elif realism_score >= 60:
            print("⚠️ GOOD - Mostly realistic with some concerns")
        elif realism_score >= 40:
            print("⚠️ FAIR - Several issues need attention")
        else:
            print("❌ POOR - Major realism issues")

def main():
    """Run comprehensive analysis"""
    try:
        df = load_data()
        
        print("🔍 COMPREHENSIVE IN-DEPTH ANALYSIS OF HYDROPONIC SIMULATION")
        print("="*80)
        print(f"Analyzing {len(df)} days of simulation data...")
        
        analyze_physiological_processes(df)
        analyze_stress_factors(df)
        analyze_nutrient_dynamics(df)
        analyze_water_dynamics(df)
        analyze_root_architecture(df)
        analyze_canopy_development(df)
        analyze_environmental_control(df)
        analyze_biomass_allocation(df)
        analyze_growth_rates(df)
        analyze_thermal_time(df)
        analyze_genetic_parameters(df)
        comprehensive_summary(df)
        
        print(f"\n{'='*80}")
        print("✅ COMPREHENSIVE ANALYSIS COMPLETE")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"❌ Error during comprehensive analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()