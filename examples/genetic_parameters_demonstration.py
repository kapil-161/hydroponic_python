#!/usr/bin/env python3
"""
Advanced Genetic Parameters System - Comprehensive Demonstration

This script demonstrates the complete genetic parameter system for hydroponic lettuce:
- DSSAT-style cultivar coefficients 
- Genotype × Environment (G×E) interaction modeling
- Breeding applications and hybrid predictions
- Integration with existing CROPGRO models

Run this script to see the genetic modeling capabilities in action.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.genetic_parameters import (
    create_lettuce_genetic_system,
    LettuceType,
    GeneticTrait
)


def demonstrate_cultivar_database():
    """Demonstrate the cultivar database and genetic coefficients"""
    print("🧬 GENETIC PARAMETERS SYSTEM DEMONSTRATION")
    print("=" * 80)
    print("DSSAT-style cultivar modeling for hydroponic lettuce production")
    print("=" * 80)
    
    # Create genetic system
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    print(f"\n1. CULTIVAR DATABASE")
    print("-" * 50)
    print(f"Loaded {len(genetic_db.cultivars)} lettuce cultivars with genetic coefficients:")
    
    print(f"\n{'Cultivar':<25} {'Type':<12} {'Year':<6} {'Breeder':<20} {'Yield':<8} {'Commercial':<10}")
    print("-" * 90)
    
    for cultivar_id, cultivar in genetic_db.cultivars.items():
        print(f"{cultivar.cultivar_name:<25} {cultivar.lettuce_type.value:<12} "
              f"{cultivar.year_released:<6} {cultivar.breeder:<20} "
              f"{cultivar.yield_potential:<8.2f} {cultivar.commercial_rating:<10.2f}")
    
    # Show genetic coefficients for a sample cultivar
    sample_cultivar = genetic_db.get_cultivar('HYDRO_001')
    if sample_cultivar:
        print(f"\nSample Genetic Coefficients ({sample_cultivar.cultivar_name}):")
        coeffs = sample_cultivar.genetic_coefficients
        print(f"• LFMAX (Leaf photosynthesis): {coeffs.LFMAX} mg CO₂/m²/s")
        print(f"• SLAVR (Specific leaf area): {coeffs.SLAVR} cm²/g")
        print(f"• EC_TOLERANCE: {coeffs.EC_TOLERANCE} dS/m")
        print(f"• NITRATE_EFFICIENCY: {coeffs.NITRATE_EFFICIENCY}")
        print(f"• ROOT_ACTIVITY: {coeffs.ROOT_ACTIVITY}")
        print(f"• PHOTOSYNTHETIC_CAPACITY: {coeffs.PHOTOSYNTHETIC_CAPACITY}")


def demonstrate_genotype_environment_interactions():
    """Demonstrate G×E interaction modeling"""
    print(f"\n2. GENOTYPE × ENVIRONMENT INTERACTIONS")
    print("-" * 50)
    
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    # Define different environmental scenarios
    environments = {
        'Optimal Greenhouse': {
            'temperature_stress': 0.0,
            'light_intensity': 1.0, 
            'nitrogen_status': 1.0,
            'salinity_stress': 0.0
        },
        'High Temperature': {
            'temperature_stress': 0.6,
            'light_intensity': 1.2,
            'nitrogen_status': 0.9,
            'salinity_stress': 0.1
        },
        'Low Light Winter': {
            'temperature_stress': -0.2,
            'light_intensity': 0.6,
            'nitrogen_status': 0.8,
            'salinity_stress': 0.0
        },
        'Marginal Water Quality': {
            'temperature_stress': 0.1,
            'light_intensity': 1.0,
            'nitrogen_status': 0.7,
            'salinity_stress': 0.4
        }
    }
    
    print(f"Best cultivars for different environments:")
    print(f"{'Environment':<25} {'1st Choice':<25} {'2nd Choice':<25} {'3rd Choice':<20}")
    print("-" * 100)
    
    environment_recommendations = {}
    
    for env_name, env_factors in environments.items():
        best_cultivars = genetic_db.get_best_cultivars_for_conditions(env_factors, top_n=3)
        
        recommendations = []
        for cultivar_id, score in best_cultivars:
            cultivar = genetic_db.get_cultivar(cultivar_id)
            recommendations.append(f"{cultivar.cultivar_name} ({score:.3f})")
        
        environment_recommendations[env_name] = recommendations
        
        print(f"{env_name:<25} {recommendations[0]:<25} {recommendations[1]:<25} {recommendations[2]:<20}")
    
    # Show trait expression under different conditions
    print(f"\nTrait Expression Under Environmental Stress:")
    test_cultivar = 'HYDRO_001'
    cultivar = genetic_db.get_cultivar(test_cultivar)
    
    print(f"\n{cultivar.cultivar_name} trait expression:")
    print(f"{'Trait':<20} {'Optimal':<10} {'Heat Stress':<12} {'Cold Stress':<12} {'Salinity':<10}")
    print("-" * 70)
    
    key_traits = [GeneticTrait.HEAT_TOLERANCE, GeneticTrait.COLD_TOLERANCE, 
                  GeneticTrait.CHLOROPHYLL_CONTENT, GeneticTrait.NITRATE_ACCUMULATION]
    
    for trait in key_traits:
        optimal_expr = ge_model.calculate_phenotype_expression(test_cultivar, environments['Optimal Greenhouse'], trait)
        heat_expr = ge_model.calculate_phenotype_expression(test_cultivar, environments['High Temperature'], trait)
        cold_expr = ge_model.calculate_phenotype_expression(test_cultivar, environments['Low Light Winter'], trait)
        saline_expr = ge_model.calculate_phenotype_expression(test_cultivar, environments['Marginal Water Quality'], trait)
        
        print(f"{trait.value:<20} {optimal_expr:<10.3f} {heat_expr:<12.3f} {cold_expr:<12.3f} {saline_expr:<10.3f}")


def demonstrate_breeding_applications():
    """Demonstrate breeding assistant and hybrid predictions"""
    print(f"\n3. BREEDING APPLICATIONS")
    print("-" * 50)
    
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    # Define breeding objectives for hot climate production
    target_environment = {
        'temperature_stress': 0.5,
        'light_intensity': 1.1,
        'nitrogen_status': 0.9,
        'salinity_stress': 0.2
    }
    
    desired_traits = {
        GeneticTrait.HEAT_TOLERANCE: 0.9,
        GeneticTrait.BOLTING_TOLERANCE: 0.85,
        GeneticTrait.YIELD_POTENTIAL: 0.95,
        GeneticTrait.NITRATE_ACCUMULATION: 0.05,  # Lower is better
        GeneticTrait.CHLOROPHYLL_CONTENT: 0.9
    }
    
    print(f"Breeding Target: Heat-tolerant, high-yielding cultivar")
    print(f"Target Environment: High temperature, good nutrition, slight salinity")
    print(f"Desired Traits:")
    for trait, target in desired_traits.items():
        print(f"  - {trait.value.replace('_', ' ').title()}: {target:.2f}")
    
    # Get breeding recommendations
    breeding_analysis = breeding_assistant.identify_breeding_targets(target_environment, desired_traits)
    
    print(f"\nParent Selection Analysis:")
    print(f"{'Cultivar':<25} {'Complementary':<13} {'Performance':<12} {'Combined':<10} {'Key Traits':<15}")
    print("-" * 90)
    
    parent_candidates = []
    for candidate in breeding_analysis['parent_candidates'][:5]:
        cultivar = genetic_db.get_cultivar(candidate['cultivar_id'])
        combined_score = candidate['complementary_score'] + candidate['performance_score']
        
        # Identify key contributing traits
        strong_traits = []
        for trait, target in desired_traits.items():
            if trait.value == 'yield_potential':
                current_value = cultivar.yield_potential
            else:
                current_value = cultivar.trait_values.get(trait, 0.5)
            
            if current_value >= target * 0.8:  # Has at least 80% of target
                strong_traits.append(trait.value[:4])  # Abbreviate
        
        key_traits_str = ", ".join(strong_traits[:3])  # Show top 3
        parent_candidates.append((candidate['cultivar_id'], combined_score))
        
        print(f"{cultivar.cultivar_name:<25} {candidate['complementary_score']:<13.3f} "
              f"{candidate['performance_score']:<12.3f} {combined_score:<10.3f} {key_traits_str:<15}")
    
    # Predict hybrid performance
    if len(parent_candidates) >= 2:
        print(f"\nHybrid Predictions:")
        print(f"{'Cross':<50} {'Yield Index':<12} {'Heterosis':<10} {'Heat Tol.':<10} {'Quality':<10}")
        print("-" * 95)
        
        # Test top 3 crosses
        for i in range(min(3, len(parent_candidates))):
            for j in range(i+1, min(3, len(parent_candidates))):
                parent1_id = parent_candidates[i][0]
                parent2_id = parent_candidates[j][0]
                
                parent1 = genetic_db.get_cultivar(parent1_id)
                parent2 = genetic_db.get_cultivar(parent2_id)
                
                hybrid_performance = breeding_assistant.estimate_hybrid_performance(
                    parent1_id, parent2_id, target_environment
                )
                
                cross_name = f"{parent1.cultivar_name[:22]} × {parent2.cultivar_name[:22]}"
                yield_index = hybrid_performance.get('predicted_yield_index', 0.5)
                heterosis = hybrid_performance.get('heterosis_advantage', 0.0)
                heat_tolerance = hybrid_performance.get('heat_tolerance_expression', 0.5)
                quality_index = (
                    hybrid_performance.get('chlorophyll_content_expression', 0.5) +
                    (1.0 - hybrid_performance.get('nitrate_accumulation_expression', 0.5))
                ) / 2.0
                
                print(f"{cross_name:<50} {yield_index:<12.3f} {heterosis:<10.3f} "
                      f"{heat_tolerance:<10.3f} {quality_index:<10.3f}")


def demonstrate_cropgro_integration():
    """Demonstrate integration with CROPGRO models"""
    print(f"\n4. CROPGRO MODEL INTEGRATION")
    print("-" * 50)
    
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    print(f"Cultivar-specific model parameters:")
    print(f"{'Cultivar':<25} {'Phot. Cap.':<12} {'N Efficiency':<12} {'Root Act.':<10} {'EC Tol.':<8}")
    print("-" * 75)
    
    for cultivar_id in ['BUTT_001', 'HYDRO_001', 'ROM_001']:
        cultivar = genetic_db.get_cultivar(cultivar_id)
        if cultivar:
            coeffs = cultivar.genetic_coefficients
            print(f"{cultivar.cultivar_name:<25} {coeffs.PHOTOSYNTHETIC_CAPACITY:<12.2f} "
                  f"{coeffs.NITRATE_EFFICIENCY:<12.2f} {coeffs.ROOT_ACTIVITY:<10.2f} {coeffs.EC_TOLERANCE:<8.1f}")
    
    # Show how genetic coefficients modify CROPGRO model behavior
    print(f"\nModel Behavior Modification Examples:")
    
    # Photosynthesis model integration
    print(f"\n• Photosynthesis Model:")
    base_rate = 1.0  # Base photosynthesis rate
    for cultivar_id in ['BUTT_001', 'HYDRO_001']:
        cultivar = genetic_db.get_cultivar(cultivar_id)
        modified_rate = base_rate * cultivar.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY
        print(f"  {cultivar.cultivar_name}: {base_rate:.2f} → {modified_rate:.2f} "
              f"({(modified_rate/base_rate-1)*100:+.1f}%)")
    
    # Nitrogen uptake model integration
    print(f"\n• Nitrogen Uptake Model:")
    base_uptake = 10.0  # mg/day base uptake
    for cultivar_id in ['BUTT_001', 'HYDRO_001']:
        cultivar = genetic_db.get_cultivar(cultivar_id)
        modified_uptake = (base_uptake * 
                          cultivar.genetic_coefficients.NITRATE_EFFICIENCY *
                          cultivar.genetic_coefficients.ROOT_ACTIVITY)
        print(f"  {cultivar.cultivar_name}: {base_uptake:.1f} → {modified_uptake:.1f} mg/day "
              f"({(modified_uptake/base_uptake-1)*100:+.1f}%)")
    
    # Environmental tolerance
    print(f"\n• Environmental Tolerance:")
    stress_level = 0.3  # 30% environmental stress
    for cultivar_id in ['BUTT_001', 'HYDRO_001']:
        cultivar = genetic_db.get_cultivar(cultivar_id)
        adaptation_index = cultivar.calculate_adaptation_index({
            'temperature_stress': stress_level,
            'salinity_stress': stress_level * 0.5,
            'light_stress': 0.0,
            'nutrient_stress': 0.0
        })
        print(f"  {cultivar.cultivar_name}: Adaptation index = {adaptation_index:.3f}")


def demonstrate_configuration_integration():
    """Demonstrate configuration system integration"""
    print(f"\n5. CONFIGURATION SYSTEM INTEGRATION")
    print("-" * 50)
    
    try:
        from src.utils.config_loader import (
            get_genetic_parameter,
            get_cultivar_data,
            get_breeding_parameter
        )
        
        # Show configuration loading
        default_cultivar = get_genetic_parameter('default_cultivar', 'HYDRO_001')
        cultivar_data = get_cultivar_data(default_cultivar, {})
        heterosis_factor = get_breeding_parameter('heterosis_factor', 1.05)
        
        print(f"Configuration parameters loaded:")
        print(f"• Default cultivar: {default_cultivar}")
        print(f"• Cultivar name: {cultivar_data.get('cultivar_name', 'Unknown')}")
        print(f"• Breeding heterosis factor: {heterosis_factor}")
        
        # Show cultivar database in config
        cultivar_database = get_genetic_parameter('cultivar_database', {})
        print(f"• Cultivar database: {len(cultivar_database)} cultivars in configuration")
        
        for cultivar_id in list(cultivar_database.keys())[:3]:
            data = cultivar_database[cultivar_id]
            print(f"  - {cultivar_id}: {data.get('cultivar_name', 'Unknown')} "
                  f"({data.get('lettuce_type', 'unknown')} type)")
        
        print(f"\n✅ Configuration integration successful!")
        
    except Exception as e:
        print(f"⚠️  Configuration integration error: {e}")


def main():
    """Run comprehensive genetic parameters demonstration"""
    try:
        demonstrate_cultivar_database()
        demonstrate_genotype_environment_interactions()
        demonstrate_breeding_applications()
        demonstrate_cropgro_integration()
        demonstrate_configuration_integration()
        
        print(f"\n" + "=" * 80)
        print(f"🎉 GENETIC PARAMETERS SYSTEM DEMONSTRATION COMPLETE!")
        print(f"=" * 80)
        print(f"\nKey Capabilities Demonstrated:")
        print(f"✅ DSSAT-style cultivar genetic coefficients")
        print(f"✅ Genotype × Environment interaction modeling")
        print(f"✅ Breeding applications with hybrid predictions")
        print(f"✅ Integration with CROPGRO phenology and nutrition models")
        print(f"✅ Configuration-driven cultivar database")
        print(f"✅ Commercial cultivar selection optimization")
        
        print(f"\nBenefits for Hydroponic Production:")
        print(f"• Precision cultivar selection for specific environments")
        print(f"• Breeding program acceleration with predictive modeling")
        print(f"• Optimization of genetic resources for controlled environments")
        print(f"• Integration with existing crop modeling frameworks")
        print(f"• Evidence-based decision making for cultivar deployment")
        
        print(f"\nNext Steps:")
        print(f"• Validate models with experimental data")
        print(f"• Expand cultivar database with more varieties")
        print(f"• Integrate with complete hydroponic simulation system")
        print(f"• Develop breeding program management tools")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()