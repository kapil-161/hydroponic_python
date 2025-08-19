"""
Complete CROPGRO Integration Test
Tests all implemented CROPGRO components working together in a comprehensive simulation.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all models
from src.models.respiration_model import (
    create_lettuce_respiration_model, 
    BiomassPool, 
    TissueType
)
from src.models.phenology_model import (
    create_lettuce_phenology_model,
    LettuceGrowthStage
)
from src.models.senescence_model import create_lettuce_senescence_model
from src.models.canopy_architecture import (
    create_lettuce_canopy_model,
    LightEnvironment
)
from src.models.nitrogen_balance import (
    create_lettuce_nitrogen_balance_model,
    NitrogenBalanceParameters,
    PlantNitrogenBalanceModel
)
from src.models.nutrient_mobility import (
    create_lettuce_nutrient_mobility_model,
    NutrientMobilityParameters,
    NutrientMobilityModel
)


def test_complete_cropgro_integration():
    """Test complete CROPGRO system integration."""
    print("=" * 90)
    print("COMPLETE CROPGRO INTEGRATION TEST")
    print("Advanced Hydroponic Crop Simulation with Full Nutrient Dynamics")
    print("=" * 90)
    
    # Initialize all models
    print("Initializing complete CROPGRO model suite...")
    respiration_model = create_lettuce_respiration_model()
    phenology_model = create_lettuce_phenology_model()
    senescence_model = create_lettuce_senescence_model()
    canopy_model = create_lettuce_canopy_model()
    
    # Create nitrogen model with realistic parameters
    n_params = NitrogenBalanceParameters()
    for n_form in n_params.uptake_kinetics:
        n_params.uptake_kinetics[n_form]['vmax'] *= 0.03  # 3% for realistic rates
    nitrogen_model = PlantNitrogenBalanceModel(n_params)
    
    # Create nutrient mobility model
    mobility_model = create_lettuce_nutrient_mobility_model()
    
    print("✓ All 6 CROPGRO models initialized successfully")
    
    # Initialize plant state
    initial_nutrients = {
        'nitrogen': 0.15, 'phosphorus': 0.020, 'potassium': 0.12,
        'calcium': 0.08, 'magnesium': 0.025, 'sulfur': 0.018
    }
    
    # Initialize nitrogen model
    nitrogen_model.initialize_organ('leaves', 3.5, 0.045)
    nitrogen_model.initialize_organ('stems', 1.2, 0.020)
    nitrogen_model.initialize_organ('roots', 2.8, 0.028)
    
    # Initialize mobility model
    mobility_model.initialize_organ_pools('leaves', initial_nutrients, 3.5)
    mobility_model.initialize_organ_pools('stems', {k: v*0.35 for k, v in initial_nutrients.items()}, 1.2)
    mobility_model.initialize_organ_pools('roots', {k: v*0.80 for k, v in initial_nutrients.items()}, 2.8)
    
    # Create initial biomass pools for respiration
    biomass_pools = [
        BiomassPool(TissueType.LEAVES, 3.5, 2.0, 4.5, 0.0),
        BiomassPool(TissueType.STEMS, 1.2, 2.0, 2.0, 0.0),
        BiomassPool(TissueType.ROOTS, 2.8, 2.0, 2.8, 0.0)
    ]
    
    # Create light environment
    light_env = LightEnvironment(
        ppfd_above_canopy=1200.0,
        direct_beam_fraction=0.65,
        diffuse_fraction=0.35,
        solar_zenith_angle=35.0
    )
    
    # Simulation parameters
    total_lai = 1.2
    canopy_height = 0.12
    days_to_simulate = 30
    
    print(f"\nSimulating {days_to_simulate} days of complete CROPGRO dynamics:")
    print(f"{'Day':<4} {'Stage':<8} {'LAI':<6} {'Hght':<6} {'NUpt':<6} {'NMob':<6} {'Resp':<6} {'Sen%':<6} {'Light%':<7} {'GDD':<6}")
    print("-" * 90)
    
    for day in range(1, days_to_simulate + 1):
        # ============= ENVIRONMENTAL CONDITIONS =============
        # Daily temperature variation with seasonal trend
        base_temp = 20.0 + 4.0 * np.sin(day * 2 * np.pi / 30)  # 30-day cycle
        daily_temp = base_temp + 2.0 * np.sin(day * 2 * np.pi / 1) + np.random.normal(0, 1)
        daily_temp = max(15.0, min(30.0, daily_temp))  # Realistic bounds
        
        # Photoperiod variation
        daylength = 13.0 + 2.5 * np.sin(day * 2 * np.pi / 60)  # Seasonal variation
        
        # Solution concentrations with variation
        solution_concs = {
            'NO3': 170.0 + 30.0 * np.sin(day * 2 * np.pi / 12) + np.random.normal(0, 10),
            'NH4': 18.0 + 8.0 * np.sin(day * 2 * np.pi / 8) + np.random.normal(0, 3),
            'AA': 6.0 + 2.0 * np.sin(day * 2 * np.pi / 15),
            'UREA': 8.0 + 3.0 * np.sin(day * 2 * np.pi / 20)
        }
        
        # Environmental factors
        env_factors = {
            'temperature_factor': max(0.7, min(1.0, 0.85 + 0.15 * np.sin(day * 2 * np.pi / 7))),
            'water_status': max(0.8, min(1.0, 0.92 + 0.08 * np.sin(day * 2 * np.pi / 5))),
            'root_health': max(0.85, min(1.0, 0.95 + 0.05 * np.sin(day * 2 * np.pi / 10))),
            'ph_factor': max(0.85, min(1.0, 0.92 + 0.08 * np.sin(day * 2 * np.pi / 6)))
        }
        
        # ============= MODEL UPDATES =============
        
        # 1. PHENOLOGY UPDATE
        water_stress = env_factors['water_status']
        temp_stress = max(0.6, min(1.0, 1.0 - abs(daily_temp - 22.0) / 15.0))
        
        phenology_response = phenology_model.daily_update(
            temperature=daily_temp,
            daylength=daylength,
            water_stress=water_stress,
            temperature_stress=temp_stress
        )
        
        stage_props = phenology_model.get_stage_properties()
        current_stage = stage_props['stage_name']
        total_gdd = stage_props['total_thermal_time']
        
        # 2. NITROGEN BALANCE UPDATE
        prev_n_stress = nitrogen_model.calculate_nitrogen_stress_factor()
        
        # Calculate growth rates based on all factors
        base_growth = {
            'leaves': 0.20 if stage_props['is_vegetative'] else 0.12,
            'stems': 0.08 if stage_props['is_vegetative'] else 0.05,
            'roots': 0.12 if stage_props['is_vegetative'] else 0.08
        }
        
        # Apply environmental and nutritional modulation
        combined_stress = min(water_stress, temp_stress, prev_n_stress)
        growth_rates = {organ: rate * combined_stress for organ, rate in base_growth.items()}
        
        # Update biomass pools
        for i, pool in enumerate(biomass_pools):
            organ_names = ['leaves', 'stems', 'roots']
            organ_name = organ_names[i]
            
            pool.age_days += 1.0
            growth_rate = growth_rates.get(organ_name, 0.0)
            pool.recent_growth = growth_rate
            pool.dry_mass += growth_rate
            
            # Update N content from nitrogen model
            if organ_name in nitrogen_model.organ_states:
                n_state = nitrogen_model.organ_states[organ_name]
                pool.nitrogen_content = n_state.nitrogen_concentration * 100
        
        # Nitrogen balance update
        root_mass = nitrogen_model.organ_states['roots'].dry_mass
        nitrogen_response = nitrogen_model.daily_update(
            root_mass=root_mass,
            solution_concentrations=solution_concs,
            environmental_factors=env_factors,
            organ_growth_rates=growth_rates,
            growth_stage='vegetative' if stage_props['is_vegetative'] else 'reproductive',
            stress_factors={'water': water_stress, 'temperature': temp_stress, 'light': 0.9},
            senescence_rates={'leaves': 0.002, 'stems': 0.001, 'roots': 0.0005}
        )
        
        # 3. RESPIRATION UPDATE
        total_new_growth = sum(pool.recent_growth for pool in biomass_pools)
        respiration_response = respiration_model.calculate_total_respiration(
            biomass_pools, daily_temp, total_new_growth
        )
        
        # 4. SENESCENCE UPDATE
        cohort_data = {}
        for i, pool in enumerate(biomass_pools):
            organ_names = ['leaves', 'stems', 'roots']
            organ_name = organ_names[i]
            cohort_data[i] = {
                'age_gdd': pool.age_days * 12.0,
                'area': pool.dry_mass * 0.18,
                'biomass': pool.dry_mass,
                'canopy_position': 0.8 if organ_name == 'leaves' else 0.5,
                'nutrient_content': {
                    'nitrogen': pool.nitrogen_content / 100.0,
                    'phosphorus': 0.010, 'potassium': 0.028
                }
            }
        
        environmental_stress = {
            'water': water_stress, 'nitrogen': prev_n_stress, 
            'temperature': temp_stress, 'light': 0.9
        }
        
        developmental_state = {'is_reproductive': stage_props['is_reproductive']}
        
        senescence_response = senescence_model.daily_update(
            cohort_data, environmental_stress, developmental_state
        )
        
        # 5. NUTRIENT MOBILITY UPDATE
        # Calculate nutrient demands based on growth
        organ_demands = {}
        for organ, growth_rate in growth_rates.items():
            organ_demands[organ] = {
                'nitrogen': growth_rate * 0.045,   # 4.5% N
                'phosphorus': growth_rate * 0.008, # 0.8% P
                'potassium': growth_rate * 0.035,  # 3.5% K
                'calcium': growth_rate * 0.015,    # 1.5% Ca
                'magnesium': growth_rate * 0.006   # 0.6% Mg
            }
        
        # Calculate senescence rates
        senescence_rates = {
            'leaves': senescence_response.cohort_responses.get(0, type('obj', (object,), {'senescence_damage': 0.0})).senescence_damage * 0.1,
            'stems': senescence_response.cohort_responses.get(1, type('obj', (object,), {'senescence_damage': 0.0})).senescence_damage * 0.05,
            'roots': senescence_response.cohort_responses.get(2, type('obj', (object,), {'senescence_damage': 0.0})).senescence_damage * 0.02
        }
        
        mobility_response = mobility_model.daily_update(
            organ_demands=organ_demands,
            stress_factors={'water': water_stress, 'nitrogen': prev_n_stress, 'temperature': temp_stress},
            senescence_rates=senescence_rates,
            growth_stage='vegetative' if stage_props['is_vegetative'] else 'reproductive',
            water_fluxes={'leaves': 0.25, 'stems': 0.15, 'roots': 0.35},
            assimilate_fluxes={'leaves': 0.12, 'stems': 0.08, 'roots': 0.05},
            temperature=daily_temp
        )
        
        # 6. CANOPY ARCHITECTURE UPDATE
        # Update LAI based on growth, senescence, and nitrogen
        growth_factor = 1.0 + (total_new_growth * 0.12 * prev_n_stress)
        senescence_factor = 1.0 - (senescence_response.total_senescence_rate * 0.05)
        total_lai *= growth_factor * senescence_factor
        total_lai = max(0.2, min(6.0, total_lai))
        
        # Update canopy height
        if stage_props['is_vegetative']:
            height_growth = 0.004 * combined_stress  # 4mm per day under good conditions
            canopy_height += height_growth
        canopy_height = min(0.25, canopy_height)
        
        canopy_response = canopy_model.daily_update(
            total_lai=total_lai,
            canopy_height=canopy_height,
            light_env=light_env,
            air_temperature=daily_temp,
            co2_concentration=1100.0
        )
        
        # ============= PROGRESS REPORTING =============
        if day % 3 == 1 or phenology_response.stage_changed or prev_n_stress < 0.85:
            n_uptake = nitrogen_response.uptake_response.total_uptake
            n_mobility = sum(mobility_response.total_redistribution.values())
            respiration = respiration_response.total_respiration
            avg_senescence = sum(state.senescence_damage for state in senescence_response.cohort_responses.values()) / max(len(senescence_response.cohort_responses), 1)
            light_interception = canopy_response.light_interception_fraction
            
            print(f"{day:<4} {current_stage:<8} {total_lai:<6.2f} {canopy_height*100:<6.1f} "
                  f"{n_uptake:<6.3f} {n_mobility:<6.3f} {respiration:<6.2f} "
                  f"{avg_senescence*100:<6.1f} {light_interception*100:<7.1f} {total_gdd:<6.0f}")
            
            if phenology_response.stage_changed:
                print(f"     >>> STAGE TRANSITION: {phenology_response.new_stage.value} <<<")
            
            if prev_n_stress < 0.85:
                print(f"     >>> NITROGEN STRESS: {prev_n_stress:.2f} <<<")
    
    # ============= FINAL ANALYSIS =============
    print(f"\n" + "=" * 90)
    print(f"COMPLETE CROPGRO INTEGRATION ANALYSIS")
    print(f"=" * 90)
    
    # Get final summaries from all models
    n_summary = nitrogen_model.get_nitrogen_summary()
    mobility_summary = mobility_model.get_mobility_summary()
    
    print(f"\nPHENOLOGY & DEVELOPMENT:")
    print(f"• Final growth stage: {current_stage}")
    print(f"• Total growing degree days: {total_gdd:.0f}")
    print(f"• Plant developmental status: {'Reproductive' if stage_props['is_reproductive'] else 'Vegetative'}")
    print(f"• Canopy development: LAI {total_lai:.2f}, Height {canopy_height*100:.1f} cm")
    
    print(f"\nBIOMASS & GROWTH:")
    total_biomass = sum(pool.dry_mass for pool in biomass_pools)
    print(f"• Total plant biomass: {total_biomass:.1f} g")
    print(f"• Leaf biomass: {biomass_pools[0].dry_mass:.1f} g")
    print(f"• Stem biomass: {biomass_pools[1].dry_mass:.1f} g") 
    print(f"• Root biomass: {biomass_pools[2].dry_mass:.1f} g")
    print(f"• Daily respiration: {respiration_response.total_respiration:.2f} g C/day")
    
    print(f"\nNITROGEN DYNAMICS:")
    print(f"• Total plant nitrogen: {n_summary['total_plant_nitrogen']:.2f} g N")
    print(f"• Nitrogen use efficiency: {n_summary['nitrogen_use_efficiency']:.1f} g biomass/g N")
    print(f"• Cumulative N uptake: {n_summary['cumulative_uptake']:.2f} g N")
    print(f"• Final N stress factor: {n_summary['nitrogen_stress_factor']:.3f}")
    
    print(f"\nNUTRIENT MOBILITY:")
    print(f"• Mobile nutrients redistributed:")
    for nutrient, amount in mobility_summary['cumulative_redistribution'].items():
        if amount > 0:
            print(f"  - {nutrient}: {amount:.3f} g")
    
    print(f"\nCANOPY & LIGHT:")
    print(f"• Light interception: {canopy_response.light_interception_fraction:.1%}")
    print(f"• Sunlit LAI: {canopy_response.sunlit_lai:.2f}")
    print(f"• Shaded LAI: {canopy_response.shaded_lai:.2f}")
    
    print(f"\nSENESCENCE & AGING:")
    avg_senescence = sum(state.senescence_damage for state in senescence_response.cohort_responses.values()) / max(len(senescence_response.cohort_responses), 1)
    print(f"• Average senescence damage: {avg_senescence:.1%}")
    print(f"• Cumulative senescence remobilization: {n_summary['cumulative_remobilization']:.3f} g N")
    
    # Test integration quality
    print(f"\n" + "=" * 90)
    print(f"INTEGRATION QUALITY ASSESSMENT")
    print(f"=" * 90)
    
    integration_tests = []
    
    # Test 1: Mass balance
    expected_biomass = 8.0 + sum(growth_rates.values()) * days_to_simulate
    biomass_error = abs(total_biomass - expected_biomass) / expected_biomass
    integration_tests.append(("Mass balance", biomass_error < 0.3, f"Error: {biomass_error:.1%}"))
    
    # Test 2: Nitrogen balance
    n_balance_ratio = n_summary['cumulative_uptake'] / n_summary['total_plant_nitrogen']
    integration_tests.append(("N balance", 0.8 < n_balance_ratio < 1.5, f"Ratio: {n_balance_ratio:.2f}"))
    
    # Test 3: Phenological progression
    integration_tests.append(("Phenology", total_gdd > 300, f"GDD: {total_gdd:.0f}"))
    
    # Test 4: Stress coordination
    integration_tests.append(("Stress coordination", n_summary['nitrogen_stress_factor'] > 0.7, f"N stress: {n_summary['nitrogen_stress_factor']:.3f}"))
    
    # Test 5: Light interception scaling
    lai_light_ratio = canopy_response.light_interception_fraction / (total_lai / 6.0)  # Normalized
    integration_tests.append(("Light-LAI relationship", 0.5 < lai_light_ratio < 2.0, f"Ratio: {lai_light_ratio:.2f}"))
    
    # Report integration test results
    passed_tests = 0
    for test_name, passed, details in integration_tests:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:<8} {test_name:<25} {details}")
        if passed:
            passed_tests += 1
    
    print(f"\nINTEGRATION SCORE: {passed_tests}/{len(integration_tests)} tests passed")
    
    if passed_tests == len(integration_tests):
        print(f"\n🎉 COMPLETE CROPGRO INTEGRATION: EXCELLENT!")
        print(f"All subsystems working harmoniously in integrated simulation.")
    elif passed_tests >= len(integration_tests) * 0.8:
        print(f"\n✅ COMPLETE CROPGRO INTEGRATION: GOOD!")
        print(f"Most subsystems integrated successfully with minor issues.")
    else:
        print(f"\n⚠️  COMPLETE CROPGRO INTEGRATION: NEEDS IMPROVEMENT")
        print(f"Some integration issues detected - review model coordination.")
    
    return passed_tests == len(integration_tests)


if __name__ == "__main__":
    # Run the complete integration test
    success = test_complete_cropgro_integration()
    
    print(f"\n" + "=" * 90)
    if success:
        print(f"🌱 CROPGRO HYDROPONIC SIMULATION SYSTEM COMPLETE!")
        print(f"Advanced crop modeling system ready for research and production use.")
    else:
        print(f"🔧 CROPGRO SYSTEM NEEDS REFINEMENT")
        print(f"Integration testing revealed areas for improvement.")
    print(f"=" * 90)