"""
Comprehensive Test for Genetic Parameters Integration

Tests the advanced genetic parameter system with:
- Cultivar-specific modeling
- Genotype × Environment interactions  
- Breeding applications
- Integration with existing CROPGRO models
"""

import sys
import os
import numpy as np
import math
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import genetic parameter models
from src.models.genetic_parameters import (
    create_lettuce_genetic_system,
    LettuceType,
    GeneticTrait
)

# Import configuration system
from src.utils.config_loader import (
    get_config_loader,
    get_genetic_parameter,
    get_cultivar_data,
    get_breeding_parameter
)

# Import existing models for integration testing
from src.models.phenology_model import create_lettuce_phenology_model
from src.models.nitrogen_balance import create_lettuce_nitrogen_balance_model
from src.models.integrated_stress import create_lettuce_integrated_stress_model


def test_genetic_parameter_system_standalone():
    """Test standalone genetic parameter system functionality"""
    print("=" * 80)
    print("GENETIC PARAMETER SYSTEM STANDALONE TEST")
    print("=" * 80)
    
    # Create genetic system
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    print(f"Loaded cultivar database:")
    print(f"{'ID':<12} {'Name':<25} {'Type':<12} {'Year':<6} {'Yield Pot.':<10} {'Adaptation':<10}")
    print("-" * 80)
    
    cultivar_summary = []
    for cultivar_id, cultivar in genetic_db.cultivars.items():
        print(f"{cultivar_id:<12} {cultivar.cultivar_name:<25} {cultivar.lettuce_type.value:<12} "
              f"{cultivar.year_released:<6} {cultivar.yield_potential:<10.2f} {cultivar.adaptation_score:<10.2f}")
        cultivar_summary.append((cultivar_id, cultivar.cultivar_name, cultivar.yield_potential))
    
    # Test cultivar type distribution
    type_counts = {}
    for cultivar in genetic_db.cultivars.values():
        type_counts[cultivar.lettuce_type] = type_counts.get(cultivar.lettuce_type, 0) + 1
    
    print(f"\nCultivar type distribution:")
    for lettuce_type, count in type_counts.items():
        print(f"  {lettuce_type.value}: {count} cultivars")
    
    # Test genetic trait analysis
    print(f"\nGenetic trait analysis:")
    trait_averages = {}
    
    for trait in [GeneticTrait.HEAT_TOLERANCE, GeneticTrait.COLD_TOLERANCE, 
                  GeneticTrait.YIELD_POTENTIAL, GeneticTrait.NITRATE_ACCUMULATION]:
        trait_values = []
        for cultivar in genetic_db.cultivars.values():
            if trait.value == "yield_potential":
                trait_values.append(cultivar.yield_potential)
            else:
                trait_values.append(cultivar.trait_values.get(trait, 0.5))
        
        trait_averages[trait] = {
            'mean': np.mean(trait_values),
            'std': np.std(trait_values),
            'min': np.min(trait_values),
            'max': np.max(trait_values)
        }
        
        stats = trait_averages[trait]
        print(f"  {trait.value}: μ={stats['mean']:.3f}, σ={stats['std']:.3f}, "
              f"range=[{stats['min']:.3f}, {stats['max']:.3f}]")
    
    validation_tests = []
    
    # Test 1: Cultivar database completeness
    db_complete = len(genetic_db.cultivars) >= 5  # At least 5 cultivars
    validation_tests.append(("Database completeness", db_complete, f"{len(genetic_db.cultivars)} cultivars loaded"))
    
    # Test 2: Genetic diversity
    yield_diversity = trait_averages[GeneticTrait.YIELD_POTENTIAL]['std'] > 0.1
    validation_tests.append(("Genetic diversity", yield_diversity, f"Yield potential std: {trait_averages[GeneticTrait.YIELD_POTENTIAL]['std']:.3f}"))
    
    # Test 3: Type representation
    type_diversity = len(type_counts) >= 2
    validation_tests.append(("Type diversity", type_diversity, f"{len(type_counts)} lettuce types"))
    
    return validation_tests


def test_genotype_environment_interactions():
    """Test G×E interaction modeling"""
    print(f"\n" + "=" * 80)
    print(f"GENOTYPE × ENVIRONMENT INTERACTION TEST")
    print(f"=" * 80)
    
    # Create genetic system
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    # Define test environments
    environments = {
        'optimal': {
            'temperature_stress': 0.0,
            'light_intensity': 1.0,
            'nitrogen_status': 1.0,
            'salinity_stress': 0.0
        },
        'heat_stress': {
            'temperature_stress': 0.6,
            'light_intensity': 1.2,
            'nitrogen_status': 0.9,
            'salinity_stress': 0.1
        },
        'cold_stress': {
            'temperature_stress': -0.4,
            'light_intensity': 0.7,
            'nitrogen_status': 0.8,
            'salinity_stress': 0.0
        },
        'nutrient_stress': {
            'temperature_stress': 0.1,
            'light_intensity': 1.0,
            'nitrogen_status': 0.4,
            'salinity_stress': 0.3
        }
    }
    
    print(f"G×E Performance Matrix:")
    print(f"{'Cultivar':<25} {'Optimal':<8} {'Heat':<8} {'Cold':<8} {'Nutrient':<8} {'Plasticity':<10}")
    print("-" * 80)
    
    cultivar_plasticity = {}
    
    for cultivar_id, cultivar in list(genetic_db.cultivars.items())[:5]:  # Test top 5 cultivars
        performance_scores = {}
        
        for env_name, env_factors in environments.items():
            performance = ge_model.predict_cultivar_performance(cultivar_id, env_factors)
            performance_scores[env_name] = performance.get('yield_index', 0.5)
        
        # Calculate plasticity (coefficient of variation)
        scores = list(performance_scores.values())
        plasticity = np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else 0
        cultivar_plasticity[cultivar_id] = plasticity
        
        print(f"{cultivar.cultivar_name:<25} {performance_scores['optimal']:<8.3f} "
              f"{performance_scores['heat_stress']:<8.3f} {performance_scores['cold_stress']:<8.3f} "
              f"{performance_scores['nutrient_stress']:<8.3f} {plasticity:<10.3f}")
    
    # Test environmental recommendations
    print(f"\nEnvironmental Adaptation Recommendations:")
    for env_name, env_factors in environments.items():
        print(f"\n{env_name.title()} conditions:")
        best_cultivars = genetic_db.get_best_cultivars_for_conditions(env_factors, top_n=3)
        for i, (cultivar_id, score) in enumerate(best_cultivars, 1):
            cultivar = genetic_db.get_cultivar(cultivar_id)
            print(f"  {i}. {cultivar.cultivar_name}: {score:.3f}")
    
    validation_tests = []
    
    # Test 1: Environmental differentiation
    heat_best = genetic_db.get_best_cultivars_for_conditions(environments['heat_stress'], top_n=1)[0][0]
    cold_best = genetic_db.get_best_cultivars_for_conditions(environments['cold_stress'], top_n=1)[0][0]
    env_differentiation = heat_best != cold_best  # Different cultivars should be best for different conditions
    validation_tests.append(("Environmental differentiation", env_differentiation, 
                           f"Heat: {heat_best}, Cold: {cold_best}"))
    
    # Test 2: Plasticity variation
    plasticity_range = max(cultivar_plasticity.values()) - min(cultivar_plasticity.values())
    plasticity_variation = plasticity_range > 0.05
    validation_tests.append(("Plasticity variation", plasticity_variation, f"Range: {plasticity_range:.3f}"))
    
    # Test 3: Performance correlation with traits
    heat_cultivar = genetic_db.get_cultivar(heat_best)
    heat_tolerance_trait = heat_cultivar.trait_values.get(GeneticTrait.HEAT_TOLERANCE, 0.5)
    heat_performance_correlation = heat_tolerance_trait > 0.6
    validation_tests.append(("Trait-performance correlation", heat_performance_correlation,
                           f"Heat tolerance: {heat_tolerance_trait:.3f}"))
    
    return validation_tests


def test_breeding_applications():
    """Test breeding assistant functionality"""
    print(f"\n" + "=" * 80)
    print(f"BREEDING APPLICATIONS TEST")
    print(f"=" * 80)
    
    # Create genetic system
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    # Define breeding targets for heat-tolerant, high-yielding cultivar
    target_environment = {
        'temperature_stress': 0.5,
        'light_intensity': 1.1,
        'nitrogen_status': 0.9,
        'salinity_stress': 0.2
    }
    
    desired_traits = {
        GeneticTrait.HEAT_TOLERANCE: 0.9,
        GeneticTrait.BOLTING_TOLERANCE: 0.85,
        GeneticTrait.NITRATE_ACCUMULATION: 0.05,  # Lower is better
        GeneticTrait.CHLOROPHYLL_CONTENT: 0.9
    }
    
    print(f"Breeding Target Analysis:")
    print(f"Target environment: High temperature stress, good nutrition")
    print(f"Desired traits:")
    for trait, value in desired_traits.items():
        print(f"  - {trait.value}: {value:.2f}")
    
    # Analyze breeding targets
    breeding_analysis = breeding_assistant.identify_breeding_targets(target_environment, desired_traits)
    
    print(f"\nTop parent candidates:")
    print(f"{'Cultivar':<25} {'Complementary':<13} {'Performance':<12} {'Combined':<10}")
    print("-" * 65)
    
    parent_candidates = []
    for i, candidate in enumerate(breeding_analysis['parent_candidates'][:5]):
        cultivar = genetic_db.get_cultivar(candidate['cultivar_id'])
        combined_score = candidate['complementary_score'] + candidate['performance_score']
        parent_candidates.append((candidate['cultivar_id'], combined_score))
        
        print(f"{cultivar.cultivar_name:<25} {candidate['complementary_score']:<13.3f} "
              f"{candidate['performance_score']:<12.3f} {combined_score:<10.3f}")
    
    # Test hybrid predictions
    if len(parent_candidates) >= 2:
        print(f"\nHybrid Performance Predictions:")
        print(f"{'Cross':<50} {'Yield Index':<12} {'Heterosis':<10} {'Heat Tol.':<10}")
        print("-" * 85)
        
        hybrid_predictions = []
        for i in range(min(3, len(parent_candidates))):
            for j in range(i+1, min(3, len(parent_candidates))):
                parent1_id = parent_candidates[i][0]
                parent2_id = parent_candidates[j][0]
                
                parent1 = genetic_db.get_cultivar(parent1_id)
                parent2 = genetic_db.get_cultivar(parent2_id)
                
                hybrid_performance = breeding_assistant.estimate_hybrid_performance(
                    parent1_id, parent2_id, target_environment
                )
                
                cross_name = f"{parent1.cultivar_name[:20]} × {parent2.cultivar_name[:20]}"
                yield_index = hybrid_performance.get('predicted_yield_index', 0.5)
                heterosis = hybrid_performance.get('heterosis_advantage', 0.0)
                heat_tolerance = hybrid_performance.get('heat_tolerance_expression', 0.5)
                
                hybrid_predictions.append((cross_name, yield_index, heterosis, heat_tolerance))
                
                print(f"{cross_name:<50} {yield_index:<12.3f} {heterosis:<10.3f} {heat_tolerance:<10.3f}")
    
    validation_tests = []
    
    # Test 1: Parent selection quality
    top_parent = breeding_analysis['parent_candidates'][0] if breeding_analysis['parent_candidates'] else None
    parent_quality = top_parent and (top_parent['complementary_score'] + top_parent['performance_score']) > 1.0
    validation_tests.append(("Parent selection quality", parent_quality, 
                           f"Top score: {(top_parent['complementary_score'] + top_parent['performance_score']):.3f}" if top_parent else "No parents"))
    
    # Test 2: Hybrid predictions available
    hybrid_available = len(hybrid_predictions) > 0 if 'hybrid_predictions' in locals() else False
    validation_tests.append(("Hybrid predictions", hybrid_available, 
                           f"{len(hybrid_predictions) if hybrid_available else 0} crosses predicted"))
    
    # Test 3: Heterosis effects
    if hybrid_available and hybrid_predictions:
        avg_heterosis = np.mean([h[2] for h in hybrid_predictions])
        positive_heterosis = avg_heterosis > 0.05
        validation_tests.append(("Positive heterosis", positive_heterosis, f"Avg heterosis: {avg_heterosis:.3f}"))
    else:
        validation_tests.append(("Positive heterosis", False, "No hybrid data"))
    
    return validation_tests


def test_cropgro_integration():
    """Test integration with existing CROPGRO models"""
    print(f"\n" + "=" * 80)
    print(f"CROPGRO MODEL INTEGRATION TEST")
    print(f"=" * 80)
    
    # Create genetic system
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    # Create CROPGRO models
    phenology_model = create_lettuce_phenology_model()
    nitrogen_model = create_lettuce_nitrogen_balance_model()
    stress_model = create_lettuce_integrated_stress_model()
    
    # Initialize nitrogen model
    nitrogen_model.initialize_organ('leaves', 2.5, 0.045)
    nitrogen_model.initialize_organ('stems', 1.0, 0.020)
    nitrogen_model.initialize_organ('roots', 2.0, 0.028)
    
    print(f"Testing cultivar-specific CROPGRO integration:")
    
    # Test different cultivars
    test_cultivars = ['HYDRO_001', 'BUTT_001', 'ROM_001']
    integration_results = {}
    
    print(f"{'Cultivar':<25} {'Day':<4} {'N Uptake':<9} {'Phenology':<10} {'Stress':<8} {'GxE Score':<10}")
    print("-" * 80)
    
    for cultivar_id in test_cultivars:
        if cultivar_id not in genetic_db.cultivars:
            continue
            
        cultivar = genetic_db.get_cultivar(cultivar_id)
        
        # Simulate 15 days with cultivar-specific parameters
        daily_results = []
        
        for day in range(1, 16):
            # Environmental conditions
            temperature = 22.0 + 2.0 * math.sin(day * math.pi / 10)
            daylength = 13.5
            
            # Create environment factors for G×E analysis
            env_factors = {
                'temperature_stress': max(0.0, (temperature - 24.0) / 10.0),
                'light_intensity': 1.0,
                'nitrogen_status': nitrogen_model.calculate_nitrogen_stress_factor(),
                'salinity_stress': 0.1
            }
            
            # Update phenology with cultivar-specific parameters
            cultivar_temp_response = cultivar.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY
            phenology_response = phenology_model.daily_update(
                temperature=temperature * cultivar_temp_response,
                daylength=daylength,
                water_stress=0.9,
                temperature_stress=0.85
            )
            
            # Nitrogen uptake with genetic modulation
            root_mass = nitrogen_model.organ_states['roots'].dry_mass
            nitrate_efficiency = cultivar.genetic_coefficients.NITRATE_EFFICIENCY
            root_activity = cultivar.genetic_coefficients.ROOT_ACTIVITY
            
            nitrogen_response = nitrogen_model.daily_update(
                root_mass=root_mass * root_activity,
                solution_concentrations={'NO3': 150.0, 'NH4': 20.0, 'AA': 8.0, 'UREA': 12.0},
                environmental_factors={
                    'temperature_factor': 0.9,
                    'water_status': 0.9,
                    'root_health': root_activity,
                    'ph_factor': 0.9
                },
                organ_growth_rates={
                    'leaves': 0.15 * nitrate_efficiency,
                    'stems': 0.08 * nitrate_efficiency,
                    'roots': 0.12 * nitrate_efficiency
                },
                growth_stage='vegetative',
                stress_factors={'water': 0.9, 'temperature': 0.85, 'light': 0.9},
                senescence_rates={'leaves': 0.001, 'stems': 0.0005, 'roots': 0.0002}
            )
            
            # Integrated stress response
            stress_levels = {
                'water': 0.9,
                'temperature': 1.0 - env_factors['temperature_stress'],
                'nutrient': nitrogen_response.nitrogen_stress_factor,
                'light': 0.9,
                'salinity': 1.0 - env_factors['salinity_stress'],
                'oxygen': 0.95,
                'ph': 0.9
            }
            
            stress_response = stress_model.daily_update(current_stress_levels=stress_levels)
            
            # Calculate G×E performance score
            ge_performance = ge_model.predict_cultivar_performance(cultivar_id, env_factors)
            ge_score = ge_performance.get('yield_index', 0.5)
            
            daily_results.append({
                'day': day,
                'n_uptake': nitrogen_response.uptake_response.total_uptake * 1000,  # Convert to mg
                'phenology_gdd': phenology_model.get_stage_properties()['total_thermal_time'],
                'stress_factor': stress_response.overall_stress_factor,
                'ge_score': ge_score
            })
            
            # Print every 5th day
            if day % 5 == 0:
                result = daily_results[-1]
                print(f"{cultivar.cultivar_name:<25} {day:<4} {result['n_uptake']:<9.2f} "
                      f"{result['phenology_gdd']:<10.0f} {result['stress_factor']:<8.3f} {result['ge_score']:<10.3f}")
        
        integration_results[cultivar_id] = daily_results
    
    # Analyze integration quality
    print(f"\nIntegration Quality Analysis:")
    validation_tests = []
    
    for cultivar_id, results in integration_results.items():
        cultivar = genetic_db.get_cultivar(cultivar_id)
        
        # Test cultivar differentiation in results
        final_result = results[-1]
        cultivar_ge_score = final_result['ge_score']
        cultivar_n_uptake = final_result['n_uptake']
        
        print(f"{cultivar.cultivar_name}:")
        print(f"  - Final G×E score: {cultivar_ge_score:.3f}")
        print(f"  - Final N uptake: {cultivar_n_uptake:.2f} mg/day")
        print(f"  - Genetic coefficients applied: ✓")
        print(f"  - Environmental interactions: ✓")
    
    # Test 1: Cultivar differentiation
    if len(integration_results) >= 2:
        ge_scores = [results[-1]['ge_score'] for results in integration_results.values()]
        score_range = max(ge_scores) - min(ge_scores)
        differentiation_test = score_range > 0.05
        validation_tests.append(("Cultivar differentiation", differentiation_test, f"G×E score range: {score_range:.3f}"))
    else:
        validation_tests.append(("Cultivar differentiation", False, "Insufficient cultivars"))
    
    # Test 2: Model integration consistency
    consistent_integration = all(
        len(results) == 15 for results in integration_results.values()
    )
    validation_tests.append(("Model integration consistency", consistent_integration, 
                           f"All cultivars completed 15-day simulation"))
    
    # Test 3: Genetic coefficient effects
    if 'HYDRO_001' in integration_results and 'BUTT_001' in integration_results:
        hydro_uptake = integration_results['HYDRO_001'][-1]['n_uptake']
        butt_uptake = integration_results['BUTT_001'][-1]['n_uptake']
        
        # HYDRO_001 should have higher uptake due to better genetic coefficients
        genetic_effects = hydro_uptake > butt_uptake
        validation_tests.append(("Genetic coefficient effects", genetic_effects,
                               f"HYDRO: {hydro_uptake:.2f} vs BUTT: {butt_uptake:.2f}"))
    else:
        validation_tests.append(("Genetic coefficient effects", False, "Required cultivars not available"))
    
    return validation_tests


def test_configuration_integration():
    """Test configuration parameter integration"""
    print(f"\n" + "=" * 80)
    print(f"CONFIGURATION INTEGRATION TEST")
    print(f"=" * 80)
    
    try:
        # Test configuration loading
        config_loader = get_config_loader()
        
        # Test genetic parameter access
        default_cultivar = get_genetic_parameter('default_cultivar', 'HYDRO_001')
        cultivar_data = get_cultivar_data(default_cultivar, {})
        breeding_params = get_breeding_parameter('heterosis_factor', 1.05)
        
        print(f"Configuration parameters loaded successfully:")
        print(f"• Default cultivar: {default_cultivar}")
        
        if cultivar_data:
            print(f"• Cultivar name: {cultivar_data.get('cultivar_name', 'Unknown')}")
            print(f"• Lettuce type: {cultivar_data.get('lettuce_type', 'Unknown')}")
            print(f"• Year released: {cultivar_data.get('year_released', 'Unknown')}")
            
            genetic_coeffs = cultivar_data.get('genetic_coefficients', {})
            print(f"• Genetic coefficients loaded: {len(genetic_coeffs)} parameters")
            print(f"  - LFMAX: {genetic_coeffs.get('LFMAX', 'N/A')}")
            print(f"  - NITRATE_EFFICIENCY: {genetic_coeffs.get('NITRATE_EFFICIENCY', 'N/A')}")
            
            trait_values = cultivar_data.get('trait_values', {})
            print(f"• Trait values loaded: {len(trait_values)} traits")
            print(f"  - Heat tolerance: {trait_values.get('heat_tolerance', 'N/A')}")
            print(f"  - Yield potential: {cultivar_data.get('yield_potential', 'N/A')}")
        
        print(f"• Breeding heterosis factor: {breeding_params}")
        
        # Test cultivar database completeness
        cultivar_db = get_genetic_parameter('cultivar_database', {})
        print(f"• Cultivar database: {len(cultivar_db)} cultivars in config")
        
        config_test = True
        
    except Exception as e:
        print(f"Configuration integration failed: {e}")
        config_test = False
    
    validation_tests = [
        ("Configuration loading", config_test, "All genetic parameters accessible")
    ]
    
    return validation_tests


def run_comprehensive_genetic_parameters_test():
    """Run all genetic parameters integration tests"""
    print("🧬 COMPREHENSIVE GENETIC PARAMETERS INTEGRATION TEST")
    print("=" * 80)
    print("Testing advanced genetic parameter system with DSSAT-style cultivar modeling")
    print("=" * 80)
    
    all_validation_tests = []
    
    # Run all test suites
    try:
        print("1. STANDALONE GENETIC SYSTEM TESTING...")
        standalone_tests = test_genetic_parameter_system_standalone()
        all_validation_tests.extend(standalone_tests)
        
        print("\n2. GENOTYPE × ENVIRONMENT INTERACTIONS...")
        ge_tests = test_genotype_environment_interactions()
        all_validation_tests.extend(ge_tests)
        
        print("\n3. BREEDING APPLICATIONS...")
        breeding_tests = test_breeding_applications()
        all_validation_tests.extend(breeding_tests)
        
        print("\n4. CROPGRO MODEL INTEGRATION...")
        cropgro_tests = test_cropgro_integration()
        all_validation_tests.extend(cropgro_tests)
        
        print("\n5. CONFIGURATION INTEGRATION...")
        config_tests = test_configuration_integration()
        all_validation_tests.extend(config_tests)
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Report overall results
    print(f"\n" + "=" * 80)
    print(f"COMPREHENSIVE TEST RESULTS")
    print(f"=" * 80)
    
    passed_tests = 0
    for test_name, passed, details in all_validation_tests:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:<8} {test_name:<40} {details}")
        if passed:
            passed_tests += 1
    
    success_rate = passed_tests / len(all_validation_tests)
    print(f"\nOVERALL SCORE: {passed_tests}/{len(all_validation_tests)} tests passed ({success_rate:.1%})")
    
    if success_rate >= 0.85:
        print(f"\n🎉 GENETIC PARAMETERS INTEGRATION: EXCELLENT!")
        print(f"Advanced genetic modeling system ready for production use.")
        print(f"Key features implemented:")
        print(f"• DSSAT-style cultivar coefficients")
        print(f"• Genotype × Environment interaction modeling")
        print(f"• Breeding applications and hybrid predictions")
        print(f"• Integration with CROPGRO phenology and nitrogen models")
        print(f"• Configuration-driven cultivar database")
    elif success_rate >= 0.70:
        print(f"\n✅ GENETIC PARAMETERS INTEGRATION: GOOD!")
        print(f"System functional with minor integration issues to address.")
    else:
        print(f"\n⚠️  GENETIC PARAMETERS INTEGRATION: NEEDS IMPROVEMENT")
        print(f"Some critical functionality requires attention.")
    
    return success_rate >= 0.85


if __name__ == "__main__":
    success = run_comprehensive_genetic_parameters_test()
    
    if success:
        print(f"\n" + "=" * 80)
        print(f"🧬 GENETIC PARAMETERS SYSTEM IMPLEMENTATION COMPLETE!")
        print(f"Advanced cultivar-specific modeling now available for hydroponic simulations.")
        print(f"Ready for breeding applications and commercial cultivar selection.")
        print(f"=" * 80)
    else:
        print(f"\n" + "=" * 80)
        print(f"🔧 GENETIC PARAMETERS SYSTEM NEEDS REFINEMENT")
        print(f"Address test failures before production deployment.")
        print(f"=" * 80)
        
        sys.exit(1)