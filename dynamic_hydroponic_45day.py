#!/usr/bin/env python3
"""
Dynamic 45-Day Hydroponic Simulation
Implements realistic lettuce growth with 3-phase development model
Features: Stage-based LAI progression, temperature/DLI effects, growth phase detection
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.hydroponic_simulator import HydroponicSimulator
from src.data.hydroponic_system import (
    HydroInputData, DefaultConfigurations
)
from src.utils.weather_generator import WeatherGenerator
from src.models.dynamic_growth import create_growth_trajectory


def run_dynamic_45day_simulation():
    """Run 45-day simulation with dynamic lettuce growth model."""
    
    print("\n" + "="*80)
    print("    DYNAMIC 45-DAY HYDROPONIC SIMULATION")
    print("    3-Phase Lettuce Growth Model with Environmental Response")
    print("="*80)
    
    # Create simulator with dynamic growth enabled
    simulator = HydroponicSimulator(use_dynamic_growth=True)
    
    # Setup system configurations
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Generate 45 days of realistic weather data
    generator = WeatherGenerator(
        base_temp=21.0,      # Optimal lettuce temperature
        temp_variation=3.5,  # Moderate temperature swings
        base_humidity=65.0,  # Good humidity for lettuce
        base_solar=17.0      # Adequate light levels
    )
    
    start_date = datetime(2024, 4, 11)
    weather_data = generator.generate_weather_series(start_date, 45)
    
    # Create input data
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_data,
        nutrient_params=nutrient_params,
        simulation_days=45
    )
    
    print("System Configuration:")
    print(f"  System: {input_data.system_config.system_id} - {input_data.system_config.description}")
    print(f"  Crop: {input_data.crop_params.crop_name}")
    print(f"  Tank Volume: {input_data.system_config.tank_volume:.0f} L")
    print(f"  Growing Area: {input_data.system_config.system_area:.0f} m²")
    print(f"  Number of Plants: {input_data.system_config.n_plants}")
    print()
    
    # Show expected growth trajectory
    print("Expected Growth Trajectory:")
    temp_profile = [w.temp_avg for w in weather_data]
    solar_profile = [w.solar_radiation for w in weather_data]
    trajectory = create_growth_trajectory(45, temp_profile, solar_profile)
    
    print("Day  Stage           LAI   Height  Kcb   Phi   Temp_Factor")
    print("---  -------------  ----  ------  ----  ----  -----------")
    sample_days = [1, 7, 14, 21, 28, 35, 42, 45]
    
    for day in sample_days:
        idx = day - 1
        stage_name = trajectory['stage'][idx].replace('_', ' ').title()
        print(f"{day:3d}  {stage_name:13s}  {trajectory['lai'][idx]:4.1f}  "
              f"{trajectory['height'][idx]:6.3f}  {trajectory['kcb'][idx]:4.2f}  "
              f"{trajectory['phi'][idx]:4.2f}  {trajectory['temp_factor'][idx]:11.2f}")
    print()
    
    print("Running dynamic 45-day simulation...")
    print("This includes real-time growth phase detection and parameter adjustment...")
    print()
    
    # Run simulation with error handling
    try:
        results = simulator.run_simulation(input_data)
    except Exception as e:
        print(f"Simulation error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Comprehensive results analysis
    print("\n" + "="*80)
    print("    DYNAMIC GROWTH SIMULATION RESULTS")
    print("="*80)
    
    # Basic statistics
    total_days = len(results.daily_results)
    initial_tank = results.daily_results[0].tank_volume
    final_tank = results.daily_results[-1].tank_volume
    total_consumption = initial_tank - final_tank
    
    print(f"✅ Simulation completed successfully!")
    print(f"  Total days simulated: {total_days}")
    print(f"  Start date: {results.start_date.strftime('%Y-%m-%d')}")
    print(f"  End date: {results.end_date.strftime('%Y-%m-%d')}")
    print()
    
    # Growth phase summary
    print("Growth Phase Analysis:")
    stages_encountered = set()
    stage_transitions = []
    
    for i, result in enumerate(results.daily_results):
        if hasattr(result, 'growth_stage'):
            stage = result.growth_stage
            stages_encountered.add(stage)
            
            # Detect transitions
            if i > 0 and hasattr(results.daily_results[i-1], 'growth_stage'):
                prev_stage = results.daily_results[i-1].growth_stage
                if stage != prev_stage:
                    stage_transitions.append((result.day, prev_stage, stage))
    
    for stage in sorted(stages_encountered):
        stage_name = stage.replace('_', ' ').title()
        stage_days = [r.day for r in results.daily_results if hasattr(r, 'growth_stage') and r.growth_stage == stage]
        if stage_days:
            print(f"  {stage_name:15s}: Days {min(stage_days):2d}-{max(stage_days):2d} ({len(stage_days)} days)")
    
    if stage_transitions:
        print("\n  Stage Transitions Detected:")
        for day, from_stage, to_stage in stage_transitions:
            from_name = from_stage.replace('_', ' ').title()
            to_name = to_stage.replace('_', ' ').title()
            print(f"    Day {day:2d}: {from_name} → {to_name}")
    print()
    
    # Water management analysis  
    print("Water Management Performance:")
    print(f"  Initial Tank Volume:        {initial_tank:.1f} L")
    print(f"  Final Tank Volume:          {final_tank:.1f} L")
    print(f"  Total Water Consumed:       {total_consumption:.1f} L")
    print(f"  Average Daily Consumption:  {total_consumption/total_days:.1f} L/day")
    print(f"  Water per Plant:            {total_consumption/input_data.system_config.n_plants:.2f} L/plant")
    print(f"  Water Use Efficiency:       {total_consumption/input_data.system_config.system_area:.1f} L/m²")
    
    # Check for realistic water consumption (should not deplete tank completely)
    water_depletion_percent = (total_consumption / initial_tank) * 100
    if water_depletion_percent > 90:
        print(f"  ⚠️  High water depletion: {water_depletion_percent:.1f}%")
    else:
        print(f"  ✅ Realistic water usage: {water_depletion_percent:.1f}% tank depletion")
    print()
    
    # Nutrient stability analysis
    print("Nutrient Concentration Stability:")
    initial_nutrients = results.daily_results[0].nutrient_concentrations
    final_nutrients = results.daily_results[-1].nutrient_concentrations
    
    all_stable = True
    for nutrient in ['N-NO3', 'P-PO4', 'K', 'Ca', 'Mg']:
        if nutrient in initial_nutrients and nutrient in final_nutrients:
            initial = initial_nutrients[nutrient]
            final = final_nutrients[nutrient]
            change_percent = ((final - initial) / initial) * 100
            
            # Check if concentrations are realistic (not extreme)
            is_stable = abs(change_percent) < 200 and final < initial * 5
            status = "✅" if is_stable else "⚠️"
            if not is_stable:
                all_stable = False
            
            print(f"  {status} {nutrient:5s}: {initial:6.1f} → {final:6.1f} mg/L ({change_percent:+6.1f}%)")
    
    if all_stable:
        print("  ✅ All nutrients remained within realistic ranges")
    else:
        print("  ⚠️  Some nutrients showed extreme concentrations")
    print()
    
    # Environmental conditions summary
    temps = [r.temp_avg for r in results.daily_results]
    et_values = [r.eto_ref for r in results.daily_results]
    transpiration = [r.transpiration for r in results.daily_results]
    
    print("Environmental Conditions:")
    print(f"  Temperature Range:         {min(temps):.1f} - {max(temps):.1f} °C")
    print(f"  Average Temperature:       {sum(temps)/len(temps):.1f} °C")
    print(f"  Reference ET Range:        {min(et_values):.1f} - {max(et_values):.1f} mm/day")
    print(f"  Average Reference ET:      {sum(et_values)/len(et_values):.1f} mm/day")
    print(f"  Average Transpiration:     {sum(transpiration)/len(transpiration):.1f} mm/day")
    print()
    
    # Growth progression analysis
    if hasattr(results.daily_results[0], 'lai'):
        lais = [getattr(r, 'lai', 0) for r in results.daily_results]
        heights = [getattr(r, 'height', 0) for r in results.daily_results]
        
        print("Crop Development Progression:")
        print(f"  LAI Progression:           {min(lais):.1f} → {max(lais):.1f}")
        print(f"  Height Progression:        {min(heights):.3f} → {max(heights):.3f} m")
        print(f"  Final Canopy Coverage:     {lais[-1]*25:.0f}% (assuming 4.0 = 100%)")
        print()
    
    # Weekly consumption patterns
    print("Weekly Consumption Patterns:")
    for week in range(0, min(7, total_days // 7 + 1)):
        start_day = week * 7
        end_day = min((week + 1) * 7 - 1, total_days - 1)
        
        if start_day < len(results.daily_results):
            start_vol = results.daily_results[start_day].tank_volume
            end_vol = results.daily_results[end_day].tank_volume
            week_consumption = start_vol - end_vol
            days_in_week = end_day - start_day + 1
            avg_daily = week_consumption / days_in_week
            
            # Determine growth phase for this week
            mid_day = (start_day + end_day) // 2
            if hasattr(results.daily_results[mid_day], 'growth_stage'):
                phase = results.daily_results[mid_day].growth_stage.replace('_', ' ').title()
            else:
                phase = "Static Model"
                
            print(f"  Week {week+1} ({phase:13s}): {week_consumption:5.1f} L total, {avg_daily:4.1f} L/day avg")
    print()
    
    # Save detailed results
    output_file = "data/output/dynamic_hydroponic_45day_complete.csv"
    os.makedirs("data/output", exist_ok=True)
    simulator.save_results_csv(output_file)
    
    # Production efficiency analysis
    print("Production Efficiency Analysis:")
    estimated_plants = input_data.system_config.n_plants
    estimated_yield_per_plant = 0.18  # kg - realistic lettuce head weight
    total_estimated_yield = estimated_plants * estimated_yield_per_plant
    water_per_kg = (total_consumption * 1000) / total_estimated_yield if total_estimated_yield > 0 else 0
    
    print(f"  Number of Plants:          {estimated_plants}")
    print(f"  Estimated Yield per Plant: {estimated_yield_per_plant:.2f} kg")
    print(f"  Total Estimated Yield:     {total_estimated_yield:.1f} kg fresh weight")
    print(f"  Water Use per kg Produce:  {water_per_kg:.0f} g/kg")
    print(f"  Production Density:        {total_estimated_yield/input_data.system_config.system_area:.2f} kg/m²")
    print(f"  Space Efficiency:          {estimated_plants/input_data.system_config.system_area:.1f} plants/m²")
    print()
    
    print("Output Files:")
    print(f"  Detailed Results: {output_file}")
    print(f"  Data Points:      {len(results.daily_results)}")
    print()
    
    print("="*80)
    print("🌱 DYNAMIC HYDROPONIC SIMULATION COMPLETED SUCCESSFULLY! 🌱")
    print("Realistic 3-phase lettuce growth model with environmental response")
    print("="*80)
    
    return results


if __name__ == "__main__":
    run_dynamic_45day_simulation()