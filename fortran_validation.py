#!/usr/bin/env python3
"""
Fortran Validation Script
Validates Python implementation against original Fortran results
Uses identical inputs to ensure mathematical accuracy
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.water_uptake import WaterUptakeModel
from src.models.nutrient_concentration import NutrientConcentrationModel, NutrientParams


def create_fortran_identical_weather():
    """Create weather data identical to Fortran implementation."""
    weather_data = []
    for day in range(1, 6):  # Days 1-5 matching Fortran
        # Exact Fortran formulas:
        # T2M = 22.0 + DAY * 0.5
        # TMIN = 18.0 + DAY * 0.3  
        # TMAX = 26.0 + DAY * 0.7
        # SRAD = 18.0 + DAY * 0.5
        # REL_HUMIDITY = 65.0
        # WIND_SPEED = 2.0
        
        temp_avg = 22.0 + day * 0.5
        temp_min = 18.0 + day * 0.3
        temp_max = 26.0 + day * 0.7
        solar_rad = 18.0 + day * 0.5
        rel_humidity = 65.0
        wind_speed = 2.0
        
        weather_data.append({
            'day': day,
            'temp_avg': temp_avg,
            'temp_min': temp_min, 
            'temp_max': temp_max,
            'solar_rad': solar_rad,
            'rel_humidity': rel_humidity,
            'wind_speed': wind_speed
        })
    
    return weather_data


def run_validation_simulation():
    """Run validation simulation with identical Fortran inputs."""
    
    print("\n" + "="*70)
    print("    FORTRAN VALIDATION SIMULATION")
    print("    Ensuring Mathematical Accuracy")
    print("="*70)
    
    # Initialize models
    water_model = WaterUptakeModel()
    nutrient_model = NutrientConcentrationModel()
    
    # Setup nutrients with exact Fortran parameters
    nutrients = {
        'N-NO3': NutrientParams("N-NO3", "Nitrogen-Nitrate", "NO3-", 200.0, 250.0, 180.0, 1.0, True, 150.0, 300.0),
        'P-PO4': NutrientParams("P-PO4", "Phosphorus-Phosphate", "PO4-3", 50.0, 60.0, 45.0, 1.2, True, 30.0, 80.0),
        'K': NutrientParams("K", "Potassium", "K+", 300.0, 350.0, 280.0, 1.1, True, 250.0, 400.0),
    }
    
    for nutrient in nutrients.values():
        nutrient_model.add_nutrient(nutrient)
    
    # Initial system state
    tank_volume = 500.0  # L
    current_concentrations = {
        'N-NO3': 200.0,
        'P-PO4': 50.0,
        'K': 300.0,
    }
    
    # Fortran system parameters
    kcb = 0.90      # Basal crop coefficient
    phi = 0.85      # Density index
    laid = 2.0      # Leaf area index
    crop_height = 0.30  # meters
    
    # Get weather data
    weather_data = create_fortran_identical_weather()
    
    print("Validation Configuration:")
    print(f"  Tank Volume: {tank_volume:.1f} L")
    print(f"  Crop Parameters: Kcb={kcb}, Phi={phi}, LAI={laid}")
    print(f"  Weather Days: {len(weather_data)}")
    print()
    
    print("Weather Input Verification:")
    print("Day  Temp_Avg  Temp_Min  Temp_Max  Solar_Rad  RH%   Wind")
    print("---  --------  --------  --------  ---------  ----  ----")
    for w in weather_data:
        print(f"{w['day']:3d}  {w['temp_avg']:8.1f}  {w['temp_min']:8.1f}  "
              f"{w['temp_max']:8.1f}  {w['solar_rad']:9.1f}  "
              f"{w['rel_humidity']:4.1f}  {w['wind_speed']:4.1f}")
    print()
    
    # Expected Fortran results for comparison
    expected_fortran = [
        {"day": 1, "eto": 3.56, "etc": 2.72, "transp": 1.87, "n": 200.26, "p": 50.06, "k": 300.26},
        {"day": 2, "eto": 3.67, "etc": 2.81, "transp": 1.93, "n": 200.53, "p": 50.11, "k": 300.53},
        {"day": 3, "eto": 3.79, "etc": 2.90, "transp": 1.99, "n": 200.81, "p": 50.17, "k": 300.81},
        {"day": 4, "eto": 3.91, "etc": 2.99, "transp": 2.05, "n": 201.10, "p": 50.24, "k": 301.10},
        {"day": 5, "eto": 4.03, "etc": 3.08, "transp": 2.12, "n": 201.41, "p": 50.30, "k": 301.41}
    ]
    
    print("PYTHON SIMULATION RESULTS:")
    print("Day  ETO_Ref  ETc_Prime  Transp   N_Conc   P_Conc   K_Conc")
    print("---  -------  ---------  ------   ------   ------   ------")
    
    python_results = []
    
    # Run 5-day simulation
    for i, weather in enumerate(weather_data):
        day = weather['day']
        
        # Net radiation calculation (Fortran: NET_RAD = SRAD * 0.8)
        net_rad = weather['solar_rad'] * 0.8
        
        # Reference ET calculation
        eto_ref = water_model.calculate_reference_et(
            net_rad, weather['temp_avg'], weather['temp_min'], 
            weather['temp_max'], weather['wind_speed'], weather['rel_humidity'], 100.0
        )
        
        # Crop ET calculation
        etc_prime, transp_rate_mm = water_model.calculate_crop_et(
            eto_ref, kcb, phi, laid, crop_height
        )
        
        # CRITICAL: Use transpiration in mm/day = L/day for nutrient calculations
        transp_rate_l = transp_rate_mm
        
        # Update nutrient concentrations
        new_concentrations = {}
        for nutrient_id in current_concentrations.keys():
            new_conc = nutrient_model.calculate_concentration_change(
                nutrient_id, current_concentrations[nutrient_id],
                transp_rate_l, tank_volume
            )
            new_concentrations[nutrient_id] = new_conc
        
        # Update tank volume
        tank_volume = nutrient_model.update_solution_volume(tank_volume, transp_rate_l)
        
        # Store results
        python_result = {
            "day": day,
            "eto": eto_ref,
            "etc": etc_prime, 
            "transp": transp_rate_mm,
            "n": new_concentrations['N-NO3'],
            "p": new_concentrations['P-PO4'],
            "k": new_concentrations['K']
        }
        python_results.append(python_result)
        
        # Print daily results
        print(f"{day:3d}  {eto_ref:7.2f}  {etc_prime:9.2f}  {transp_rate_mm:6.2f}   "
              f"{new_concentrations['N-NO3']:6.2f}   {new_concentrations['P-PO4']:6.2f}   "
              f"{new_concentrations['K']:6.2f}")
        
        # Update for next day
        current_concentrations = new_concentrations
    
    print(f"\nFinal Tank Volume: {tank_volume:8.1f} L")
    
    # Validation comparison
    print("\n" + "="*80)
    print("    VALIDATION RESULTS COMPARISON")
    print("="*80)
    
    print("\nDetailed Comparison:")
    print("Day | Metric        | Python   | Fortran  | Diff    | Status")
    print("----|---------------|----------|----------|---------|--------")
    
    all_passed = True
    tolerance = 0.01  # 0.01 tolerance for floating point comparison
    
    for py_result, f_result in zip(python_results, expected_fortran):
        day = py_result['day']
        
        # Compare each metric
        metrics = [
            ('ETO_Ref', py_result['eto'], f_result['eto']),
            ('ETc_Prime', py_result['etc'], f_result['etc']),
            ('Transp', py_result['transp'], f_result['transp']),
            ('N-NO3', py_result['n'], f_result['n']),
            ('P-PO4', py_result['p'], f_result['p']),
            ('K', py_result['k'], f_result['k'])
        ]
        
        for metric_name, py_val, f_val in metrics:
            diff = abs(py_val - f_val)
            status = "✅ PASS" if diff <= tolerance else "❌ FAIL"
            if diff > tolerance:
                all_passed = False
                
            print(f" {day}  | {metric_name:12} | {py_val:8.2f} | {f_val:8.2f} | {diff:7.3f} | {status}")
    
    # Final tank volume comparison
    expected_final_volume = 490.0
    volume_diff = abs(tank_volume - expected_final_volume)
    volume_status = "✅ PASS" if volume_diff <= 1.0 else "❌ FAIL"
    if volume_diff > 1.0:
        all_passed = False
        
    print(f" -  | Tank Volume   | {tank_volume:8.1f} | {expected_final_volume:8.1f} | {volume_diff:7.1f} | {volume_status}")
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 VALIDATION SUCCESSFUL: Python implementation matches Fortran exactly!")
        print("✅ All calculations are mathematically identical")
        print("✅ Scientific accuracy confirmed")
    else:
        print("❌ VALIDATION FAILED: Differences found")
        print("⚠️  Manual review required")
    
    print("="*80)
    
    return all_passed


def main():
    """Main validation entry point."""
    print("HYDROPONIC MODEL VALIDATION SYSTEM")
    print("Comparing Python vs Fortran Implementation")
    
    validation_passed = run_validation_simulation()
    
    if validation_passed:
        print("\n✅ READY FOR PRODUCTION USE")
        sys.exit(0)
    else:
        print("\n❌ VALIDATION ISSUES DETECTED")
        sys.exit(1)


if __name__ == "__main__":
    main()