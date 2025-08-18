#!/usr/bin/env python3
"""
Scientific Hydroponic Simulation with Mechanistic Nutrient Uptake
Combines dynamic 3-phase growth with Monod kinetics for realistic nutrient modeling
Features: Monod/Michaelis-Menten uptake, biomass-dependent consumption, fault detection
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


def run_scientific_45day_simulation():
    """Run scientific 45-day simulation with mechanistic nutrient uptake."""
    
    print("\n" + "="*90)
    print("    SCIENTIFIC HYDROPONIC SIMULATION")
    print("    Mechanistic Nutrient Uptake with Dynamic Growth Modeling")
    print("    Based on: Monod Kinetics, NiCoLet Model, and Hydroponic Research")
    print("="*90)
    
    # Create simulator with both dynamic growth and mechanistic uptake
    simulator = HydroponicSimulator(
        use_dynamic_growth=True, 
        use_mechanistic_uptake=True
    )
    
    # Setup system configurations
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Generate optimized weather for lettuce growth
    generator = WeatherGenerator(
        base_temp=20.5,      # Near-optimal lettuce temperature  
        temp_variation=2.8,  # Reduced variation for controlled environment
        base_humidity=68.0,  # Optimal humidity for lettuce
        base_solar=16.5      # Good light levels for hydroponic lettuce
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
    
    print("Scientific Model Configuration:")
    print(f"  System: {input_data.system_config.description}")
    print(f"  Crop Model: Dynamic 3-phase lettuce growth")
    print(f"  Nutrient Model: Monod kinetics with saturation")
    print(f"  Biomass Model: NiCoLet-inspired 3-compartment")
    print(f"  Tank Volume: {input_data.system_config.tank_volume:.0f} L")
    print(f"  Growing Area: {input_data.system_config.system_area:.0f} m²")
    print(f"  Plants: {input_data.system_config.n_plants}")
    print(f"  Initial Biomass: ~{input_data.system_config.n_plants * 2.0:.0f} g fresh weight")
    print()
    
    print("Mechanistic Nutrient Uptake Parameters:")
    if hasattr(simulator, 'mechanistic_uptake') and simulator.mechanistic_uptake:
        print("  Nutrient    Slow Growth      Rapid Growth     Steady Growth")
        print("              Vmax    Km       Vmax    Km       Vmax    Km")
        print("  --------    ----   ----      ----   ----      ----   ----")
        
        # Import GrowthStage enum
        from src.models.mechanistic_nutrient_uptake import GrowthStage
        
        for nutrient in ['N-NO3', 'P-PO4', 'K', 'Ca', 'Mg']:
            if nutrient in simulator.mechanistic_uptake.kinetic_params:
                params = simulator.mechanistic_uptake.kinetic_params[nutrient]
                
                slow = params[GrowthStage.SLOW_GROWTH]
                rapid = params[GrowthStage.RAPID_GROWTH] 
                steady = params[GrowthStage.STEADY_GROWTH]
                
                print(f"  {nutrient:8s}    {slow.vmax:4.2f}   {slow.km:4.0f}      "
                      f"{rapid.vmax:4.2f}   {rapid.km:4.0f}      "
                      f"{steady.vmax:4.2f}   {steady.km:4.0f}")
    print()
    
    print("Running scientific 45-day simulation...")
    print("Features: Monod kinetics, biomass feedback, fault detection, growth stages")
    print("This may take longer due to mechanistic calculations...")
    print()
    
    # Run simulation with comprehensive error handling
    try:
        results = simulator.run_simulation(input_data)
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Detailed scientific analysis
    print("\n" + "="*90)
    print("    SCIENTIFIC SIMULATION RESULTS ANALYSIS")
    print("="*90)
    
    # Basic completion check
    total_days = len(results.daily_results)
    initial_tank = results.daily_results[0].tank_volume
    final_tank = results.daily_results[-1].tank_volume
    total_consumption = initial_tank - final_tank
    
    print(f"✅ Scientific simulation completed successfully!")
    print(f"  Days simulated: {total_days}")
    print(f"  Simulation period: {results.start_date.strftime('%Y-%m-%d')} to {results.end_date.strftime('%Y-%m-%d')}")
    print()
    
    # Biomass development analysis
    print("🌱 Biomass Development Analysis:")
    if hasattr(results.daily_results[0], 'total_biomass'):
        initial_biomass = results.daily_results[0].total_biomass
        final_biomass = results.daily_results[-1].total_biomass
        initial_fresh = results.daily_results[0].fresh_weight
        final_fresh = results.daily_results[-1].fresh_weight
        
        biomass_gain = final_biomass - initial_biomass
        fresh_gain = final_fresh - initial_fresh
        
        print(f"  Initial Dry Biomass:       {initial_biomass:.1f} g")
        print(f"  Final Dry Biomass:         {final_biomass:.1f} g") 
        print(f"  Biomass Gain:              {biomass_gain:.1f} g ({(biomass_gain/initial_biomass*100):.0f}% increase)")
        print(f"  Initial Fresh Weight:      {initial_fresh:.1f} g")
        print(f"  Final Fresh Weight:        {final_fresh:.1f} g")
        print(f"  Fresh Weight Gain:         {fresh_gain:.1f} g")
        print(f"  Fresh:Dry Ratio:           {final_fresh/final_biomass:.1f}:1")
        print(f"  Average per Plant:         {final_fresh/input_data.system_config.n_plants:.1f} g fresh/plant")
    else:
        print("  ⚠️ Biomass data not available (mechanistic model may not be active)")
    print()
    
    # Growth stage progression
    print("📈 Growth Stage Progression:")
    stages_encountered = []
    for result in results.daily_results:
        if hasattr(result, 'growth_stage'):
            stage = result.growth_stage
            if stage not in [s[0] for s in stages_encountered]:
                stages_encountered.append((stage, result.day))
    
    stage_names = {
        'slow_growth': 'Establishment Phase',
        'rapid_growth': 'Exponential Growth',
        'steady_growth': 'Maturation Phase'
    }
    
    for stage, start_day in stages_encountered:
        stage_name = stage_names.get(stage, stage.replace('_', ' ').title())
        # Find end day
        end_day = 45
        for i, (next_stage, next_start) in enumerate(stages_encountered):
            if next_start > start_day:
                end_day = next_start - 1
                break
        print(f"  {stage_name:20s}: Days {start_day:2d}-{end_day:2d}")
    print()
    
    # Nutrient uptake kinetics analysis
    print("🧪 Nutrient Uptake Kinetics Analysis:")
    
    # Check for nutrient limitation vs saturation
    nutrient_status = {}
    for day_idx in [7, 21, 35, 44]:  # Sample key days
        if day_idx < len(results.daily_results):
            result = results.daily_results[day_idx]
            if hasattr(result, 'uptake_diagnostics'):
                print(f"  Day {day_idx + 1:2d} Analysis:")
                for nutrient, diagnostics in result.uptake_diagnostics.items():
                    limitation = diagnostics.get('limitation_factor', 'unknown')
                    uptake_rate = diagnostics.get('uptake_rate_mg_day', 0)
                    saturation = diagnostics.get('saturation_factor', 0)
                    
                    status_symbol = {
                        'concentration_limited': '🔴',  # Limited by concentration
                        'biomass_limited': '🟡',       # Limited by biomass
                        'optimal': '🟢',               # Optimal uptake
                        'environment_limited': '🟠',   # Environmental stress
                        'minimum_threshold': '⚫',     # Below minimum
                        'luxury_consumption': '🔵'     # Above optimal
                    }.get(limitation, '❔')
                    
                    print(f"    {status_symbol} {nutrient:5s}: {uptake_rate:6.1f} mg/day, "
                          f"{saturation*100:3.0f}% saturated, {limitation}")
    print()
    
    # Water use efficiency
    print("💧 Water Use Efficiency:")
    print(f"  Initial Tank Volume:       {initial_tank:.1f} L")
    print(f"  Final Tank Volume:         {final_tank:.1f} L")
    print(f"  Total Water Consumed:      {total_consumption:.1f} L")
    print(f"  Average Daily Consumption: {total_consumption/total_days:.1f} L/day")
    
    # Check if tank was managed properly (shouldn't deplete completely)
    depletion_percent = (total_consumption / initial_tank) * 100
    if depletion_percent < 70:
        print(f"  ✅ Sustainable water use: {depletion_percent:.1f}% depletion")
    elif depletion_percent < 90:
        print(f"  ⚠️  High water use: {depletion_percent:.1f}% depletion")
    else:
        print(f"  🔴 Excessive depletion: {depletion_percent:.1f}% - needs replenishment")
    print()
    
    # Nutrient concentration stability
    print("⚖️  Nutrient Concentration Stability:")
    initial_nutrients = results.daily_results[0].nutrient_concentrations
    final_nutrients = results.daily_results[-1].nutrient_concentrations
    
    stable_nutrients = 0
    total_nutrients = 0
    
    for nutrient in ['N-NO3', 'P-PO4', 'K', 'Ca', 'Mg']:
        if nutrient in initial_nutrients and nutrient in final_nutrients:
            initial = initial_nutrients[nutrient]
            final = final_nutrients[nutrient]
            change_percent = ((final - initial) / initial) * 100
            
            # Check stability (realistic change < 50%)
            is_stable = abs(change_percent) < 50 and final > initial * 0.1
            status = "✅" if is_stable else "❌"
            if is_stable:
                stable_nutrients += 1
            total_nutrients += 1
            
            print(f"  {status} {nutrient:5s}: {initial:6.1f} → {final:6.1f} mg/L ({change_percent:+6.1f}%)")
    
    stability_percent = (stable_nutrients / total_nutrients * 100) if total_nutrients > 0 else 0
    print(f"  📊 Overall Stability: {stable_nutrients}/{total_nutrients} nutrients stable ({stability_percent:.0f}%)")
    print()
    
    # Environmental optimization
    print("🌡️  Environmental Response:")
    temps = [r.temp_avg for r in results.daily_results]
    et_values = [r.eto_ref for r in results.daily_results]
    transpiration = [r.transpiration for r in results.daily_results]
    
    print(f"  Temperature Range:         {min(temps):.1f} - {max(temps):.1f} °C")
    print(f"  Average Temperature:       {sum(temps)/len(temps):.1f} °C")
    print(f"  Reference ET Range:        {min(et_values):.1f} - {max(et_values):.1f} mm/day")
    print(f"  Transpiration Range:       {min(transpiration):.1f} - {max(transpiration):.1f} mm/day")
    
    # Temperature optimality check
    avg_temp = sum(temps) / len(temps)
    temp_optimality = "✅ Optimal" if 18 <= avg_temp <= 24 else "⚠️ Suboptimal"
    print(f"  Temperature Optimality:    {temp_optimality} for lettuce growth")
    print()
    
    # Production efficiency
    print("📊 Production Efficiency Metrics:")
    if hasattr(results.daily_results[-1], 'fresh_weight'):
        final_yield = results.daily_results[-1].fresh_weight / 1000  # Convert to kg
        water_use_efficiency = final_yield / (total_consumption / 1000)  # kg/L
        space_efficiency = final_yield / input_data.system_config.system_area  # kg/m²
        
        print(f"  Total Yield:               {final_yield:.2f} kg fresh weight")
        print(f"  Water Use Efficiency:      {water_use_efficiency:.3f} kg/L")
        print(f"  Space Efficiency:          {space_efficiency:.2f} kg/m²")
        print(f"  Average per Plant:         {final_yield*1000/input_data.system_config.n_plants:.0f} g/plant")
        
        # Compare to commercial benchmarks
        commercial_wue = 0.020  # kg/L typical for lettuce
        commercial_yield = 0.150  # kg/plant typical
        
        wue_performance = (water_use_efficiency / commercial_wue) * 100
        yield_performance = ((final_yield*1000/input_data.system_config.n_plants) / (commercial_yield*1000)) * 100
        
        print(f"  WUE vs Commercial:         {wue_performance:.0f}% of benchmark")
        print(f"  Yield vs Commercial:       {yield_performance:.0f}% of benchmark")
    print()
    
    # Save detailed results
    output_file = "data/output/scientific_hydroponic_45day.csv"
    os.makedirs("data/output", exist_ok=True)
    simulator.save_results_csv(output_file)
    
    print("💾 Output Files:")
    print(f"  Scientific Results: {output_file}")
    print(f"  Data Points:        {len(results.daily_results)}")
    print()
    
    print("="*90)
    print("🔬 SCIENTIFIC HYDROPONIC SIMULATION COMPLETED! 🔬")
    print("Advanced mechanistic modeling with Monod kinetics and biomass feedback")
    print("Demonstrates realistic nutrient uptake without mathematical instabilities")
    print("="*90)
    
    return results


if __name__ == "__main__":
    run_scientific_45day_simulation()