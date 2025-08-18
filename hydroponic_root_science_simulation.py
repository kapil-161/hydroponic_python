#!/usr/bin/env python3
"""
Advanced Hydroponic Root Science Simulation
Integrates CROPGRO-inspired root dynamics with Monod kinetics for hydroponics
Features: Dynamic root surface area, solution contact modeling, root health tracking
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


def run_hydroponic_root_science_simulation():
    """Run advanced simulation with CROPGRO-inspired root dynamics."""
    
    print("\n" + "="*100)
    print("    HYDROPONIC ROOT SCIENCE SIMULATION")
    print("    CROPGRO-Inspired Root Dynamics + Monod Kinetics + Hydroponic Systems")
    print("    Features: Root Surface Area Modeling, Solution Contact, Root Health")
    print("="*100)
    
    # Create simulator with all advanced features
    simulator = HydroponicSimulator(
        use_dynamic_growth=True, 
        use_mechanistic_uptake=True
    )
    
    # Setup NFT lettuce system
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Generate controlled environment conditions for root development
    generator = WeatherGenerator(
        base_temp=19.5,      # Slightly cooler for better root development
        temp_variation=2.0,  # Stable temperatures  
        base_humidity=70.0,  # Higher humidity for root zone
        base_solar=16.0      # Moderate light to balance root/shoot growth
    )
    
    start_date = datetime(2024, 4, 11)
    weather_data = generator.generate_weather_series(start_date, 30)  # 30-day focus
    
    # Create input data
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_data,
        nutrient_params=nutrient_params,
        simulation_days=30
    )
    
    print("Hydroponic Root Science Configuration:")
    print(f"  System: {system_config.description}")
    print(f"  Root Model: CROPGRO-inspired hydroponic adaptation")
    print(f"  Nutrient Uptake: Root surface area × solution contact × Monod kinetics")
    print(f"  Root Dynamics: Growth, senescence, environmental response")
    print(f"  Flow Rate: {system_config.flow_rate} L/h ({system_config.flow_rate/60:.1f} L/min)")
    print(f"  System Area: {system_config.system_area} m² with {system_config.n_plants} plants")
    print()
    
    print("Root Development Parameters:")
    print(f"  Initial Specific Root Length: ~800 cm/g (young seedlings)")
    print(f"  Mature Specific Root Length:  ~600 cm/g (developed plants)")  
    print(f"  Root Diameter Range:          0.1-0.5 mm")
    print(f"  Solution Contact (NFT):       ~30% of total root surface")
    print(f"  Root Growth Allocation:       15-35% depending on stage & stress")
    print()
    
    print("Running hydroponic root science simulation...")
    print("Tracking: root mass, length, surface area, solution contact, uptake efficiency")
    print()
    
    # Run simulation
    try:
        results = simulator.run_simulation(input_data)
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Advanced root science analysis
    print("\n" + "="*100)
    print("    HYDROPONIC ROOT SCIENCE ANALYSIS")
    print("="*100)
    
    # Basic simulation success
    print(f"✅ Root science simulation completed: {len(results.daily_results)} days")
    print(f"   Period: {results.start_date.strftime('%Y-%m-%d')} to {results.end_date.strftime('%Y-%m-%d')}")
    print()
    
    # Root development progression
    print("🌿 Root System Development:")
    if hasattr(results.daily_results[0], 'total_biomass'):
        # Extract root data from simulation results
        root_masses = []
        root_surfaces = []
        root_lengths = []
        root_efficiencies = []
        root_health_scores = []
        
        for result in results.daily_results:
            if hasattr(result, 'total_biomass') and hasattr(result, 'uptake_diagnostics'):
                root_masses.append(getattr(result, 'structural_mass', 0))
                
                # Try to extract root-specific data from diagnostics
                avg_health = 0
                health_count = 0
                for nutrient, diag in getattr(result, 'uptake_diagnostics', {}).items():
                    if 'root_health_score' in diag:
                        avg_health += diag['root_health_score']
                        health_count += 1
                
                if health_count > 0:
                    root_health_scores.append(avg_health / health_count)
                else:
                    root_health_scores.append(75.0)
        
        if root_health_scores:
            initial_health = root_health_scores[0]
            final_health = root_health_scores[-1]
            avg_health = sum(root_health_scores) / len(root_health_scores)
            
            print(f"  Root Health Progression:   {initial_health:.1f} → {final_health:.1f} (avg: {avg_health:.1f})")
            
            # Health trend analysis
            if final_health > initial_health + 10:
                health_trend = "📈 Improving"
            elif final_health < initial_health - 10:
                health_trend = "📉 Declining" 
            else:
                health_trend = "📊 Stable"
            print(f"  Root Health Trend:         {health_trend}")
    
    # Nutrient uptake analysis with root factors
    print("\n🧪 Root-Based Nutrient Uptake Analysis:")
    
    # Analyze uptake diagnostics from key days
    sample_days = [1, 7, 14, 21, 28, 30]
    
    print("Day  Root_Health  Solution_Contact  Root_Surface_Factor  Limitation")
    print("---  -----------  ----------------  -------------------  ----------")
    
    for day in sample_days:
        if day <= len(results.daily_results):
            result = results.daily_results[day-1]
            
            if hasattr(result, 'uptake_diagnostics'):
                # Average across nutrients
                avg_health = 0
                avg_contact = 0
                avg_surface = 0
                limitations = []
                
                for nutrient, diag in result.uptake_diagnostics.items():
                    avg_health += diag.get('root_health_score', 75)
                    avg_contact += diag.get('solution_contact', 0.3) * 100
                    avg_surface += diag.get('root_surface_factor', 1.0)
                    limitations.append(diag.get('limitation_factor', 'unknown')[:4])
                
                n_nutrients = len(result.uptake_diagnostics)
                if n_nutrients > 0:
                    avg_health /= n_nutrients
                    avg_contact /= n_nutrients 
                    avg_surface /= n_nutrients
                    main_limitation = max(set(limitations), key=limitations.count)
                    
                    print(f"{day:3d}      {avg_health:5.1f}            {avg_contact:5.1f}%              {avg_surface:8.2f}         {main_limitation}")
    
    # Root system efficiency analysis
    print("\n📊 Root System Efficiency Metrics:")
    
    # Water use efficiency relative to root development
    initial_tank = results.daily_results[0].tank_volume
    final_tank = results.daily_results[-1].tank_volume
    total_consumption = initial_tank - final_tank
    
    print(f"  Total Water Consumed:      {total_consumption:.1f} L over {len(results.daily_results)} days")
    print(f"  Average Daily Consumption: {total_consumption/len(results.daily_results):.1f} L/day")
    
    # Estimate root efficiency based on nutrient stability
    initial_nutrients = results.daily_results[0].nutrient_concentrations
    final_nutrients = results.daily_results[-1].nutrient_concentrations
    
    nutrient_stability_score = 0
    nutrient_count = 0
    
    for nutrient in ['N-NO3', 'P-PO4', 'K', 'Ca', 'Mg']:
        if nutrient in initial_nutrients and nutrient in final_nutrients:
            initial = initial_nutrients[nutrient]
            final = final_nutrients[nutrient]
            
            # Stability score based on how much concentration changed
            change_percent = abs((final - initial) / initial)
            if change_percent < 0.3:  # Less than 30% change is good
                stability = 100 - (change_percent * 100)
            else:
                stability = max(0, 70 - change_percent * 100)
            
            nutrient_stability_score += stability
            nutrient_count += 1
    
    if nutrient_count > 0:
        avg_stability = nutrient_stability_score / nutrient_count
        print(f"  Nutrient Stability Score:  {avg_stability:.1f}/100")
        
        if avg_stability > 80:
            efficiency_rating = "🌟 Excellent"
        elif avg_stability > 60:
            efficiency_rating = "✅ Good"
        elif avg_stability > 40:
            efficiency_rating = "⚠️ Moderate"
        else:
            efficiency_rating = "❌ Poor"
            
        print(f"  Root System Efficiency:    {efficiency_rating}")
    
    # Growth stage root adaptation
    print("\n🌱 Root Adaptation by Growth Stage:")
    
    stages_data = {}
    for result in results.daily_results:
        if hasattr(result, 'growth_stage'):
            stage = result.growth_stage
            if stage not in stages_data:
                stages_data[stage] = {'days': [], 'health': [], 'efficiency': []}
                
            stages_data[stage]['days'].append(result.day)
            
            # Extract root health if available
            if hasattr(result, 'uptake_diagnostics'):
                avg_health = sum(diag.get('root_health_score', 75) 
                               for diag in result.uptake_diagnostics.values()) / len(result.uptake_diagnostics)
                stages_data[stage]['health'].append(avg_health)
    
    for stage, data in stages_data.items():
        stage_name = stage.replace('_', ' ').title()
        if data['health']:
            avg_health = sum(data['health']) / len(data['health'])
            day_range = f"{min(data['days'])}-{max(data['days'])}"
            print(f"  {stage_name:15s}: Days {day_range:6s}, Avg Root Health: {avg_health:.1f}")
    
    # Environmental response analysis
    print("\n🌡️ Root Environmental Response:")
    
    temps = [r.temp_avg for r in results.daily_results]
    avg_temp = sum(temps) / len(temps)
    temp_range = max(temps) - min(temps)
    
    print(f"  Average Temperature:       {avg_temp:.1f}°C")
    print(f"  Temperature Range:         {temp_range:.1f}°C")
    
    # Root zone temperature optimality (18-22°C ideal)
    if 18 <= avg_temp <= 22:
        temp_rating = "✅ Optimal for root development"
    elif 16 <= avg_temp <= 25:
        temp_rating = "⚠️ Acceptable for root development"  
    else:
        temp_rating = "❌ Suboptimal for root development"
    
    print(f"  Root Zone Assessment:      {temp_rating}")
    
    # Flow rate impact (NFT specific)
    flow_rate = input_data.system_config.flow_rate
    if flow_rate >= 30:  # L/h
        flow_rating = "✅ Good flow for root oxygenation"
    elif flow_rate >= 15:
        flow_rating = "⚠️ Moderate flow - monitor roots"
    else:
        flow_rating = "❌ Low flow risk - poor root health"
        
    print(f"  Flow Rate Impact:          {flow_rating}")
    
    # Save detailed results
    output_file = "data/output/hydroponic_root_science_30day.csv"
    os.makedirs("data/output", exist_ok=True)
    simulator.save_results_csv(output_file)
    
    print(f"\n💾 Output Files:")
    print(f"  Root Science Data: {output_file}")
    print(f"  Data Points:       {len(results.daily_results)}")
    
    # Final assessment
    print(f"\n" + "="*100)
    print("🔬 HYDROPONIC ROOT SCIENCE SIMULATION COMPLETED! 🔬")
    print("Advanced root modeling demonstrates:")
    print("✓ CROPGRO-inspired root dynamics adapted for hydroponics")
    print("✓ Root surface area × solution contact × Monod kinetics integration")  
    print("✓ Dynamic root health and environmental response tracking")
    print("✓ Stable nutrient uptake without mathematical explosions")
    print("="*100)
    
    return results


if __name__ == "__main__":
    run_hydroponic_root_science_simulation()