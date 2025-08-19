"""
Root Architecture Integration Module

Integrates the enhanced root architecture model with existing CROPGRO components:
- Mechanistic nutrient uptake model
- Nitrogen balance model  
- Root zone temperature model
- Environmental stress models

This module serves as the bridge between the detailed root architecture
and the existing nutrient uptake calculations.
"""

from typing import Dict, Tuple, Optional
import math
from dataclasses import dataclass

from .root_architecture import (
    RootArchitectureModel, 
    create_lettuce_root_architecture_model,
    HydroponicSystemType
)


@dataclass
class RootUptakeParameters:
    """Parameters for root-architecture-based nutrient uptake"""
    # Base uptake rates per unit surface area (mg/cm²/day)
    base_uptake_rates: Dict[str, float]
    
    # Surface area effectiveness factors by root type
    fine_root_effectiveness: float = 1.0      # Fine roots most active
    medium_root_effectiveness: float = 0.6    # Medium roots moderate
    coarse_root_effectiveness: float = 0.2    # Coarse roots mainly transport
    
    # Temperature response parameters
    optimal_temperature: float = 20.0         # °C
    q10_factor: float = 2.0                   # Temperature sensitivity
    
    # Flow rate optimization parameters  
    optimal_flow_rate: float = 1.5            # L/min
    flow_stress_threshold: float = 4.0        # L/min
    
    # Concentration-dependent parameters
    michaelis_constants: Dict[str, float] = None  # Km values for each nutrient


class EnhancedRootUptakeModel:
    """
    Enhanced nutrient uptake model using detailed root architecture
    
    Replaces simple root mass-based calculations with:
    - Root surface area-based uptake
    - Spatial distribution effects
    - Root age and activity factors
    - Environmental condition responses
    """
    
    def __init__(self, system_type: HydroponicSystemType = HydroponicSystemType.NFT):
        self.root_architecture = create_lettuce_root_architecture_model(system_type)
        self.system_type = system_type
        
        # Default uptake parameters for lettuce
        self.uptake_params = RootUptakeParameters(
            base_uptake_rates={
                'NO3': 0.25,    # mg/cm²/day
                'NH4': 0.15,    # mg/cm²/day  
                'PO4': 0.05,    # mg/cm²/day
                'K': 0.20,      # mg/cm²/day
                'Ca': 0.10,     # mg/cm²/day
                'Mg': 0.08,     # mg/cm²/day
                'SO4': 0.06     # mg/cm²/day
            },
            michaelis_constants={
                'NO3': 50.0,    # mg/L
                'NH4': 20.0,    # mg/L
                'PO4': 5.0,     # mg/L
                'K': 30.0,      # mg/L
                'Ca': 40.0,     # mg/L
                'Mg': 25.0,     # mg/L
                'SO4': 35.0     # mg/L
            }
        )
    
    def daily_update(self, 
                    environmental_conditions: Dict[str, float],
                    growth_factors: Dict[str, float],
                    solution_concentrations: Dict[str, float]) -> Dict[str, float]:
        """
        Update root architecture and calculate nutrient uptake
        
        Args:
            environmental_conditions: Temperature, flow rate, oxygen, etc.
            growth_factors: Stress factors affecting root growth
            solution_concentrations: Nutrient concentrations in mg/L
            
        Returns:
            Dictionary with uptake rates and root architecture metrics
        """
        # Update root architecture
        architecture_metrics = self.root_architecture.daily_update(
            environmental_conditions, growth_factors
        )
        
        # Calculate nutrient uptake using enhanced architecture
        uptake_results = self.calculate_nutrient_uptake(
            architecture_metrics, environmental_conditions, solution_concentrations
        )
        
        # Combine results
        results = {
            **architecture_metrics,
            **uptake_results,
            'system_type': self.system_type.value
        }
        
        return results
    
    def calculate_nutrient_uptake(self,
                                architecture_metrics: Dict[str, float],
                                environmental_conditions: Dict[str, float], 
                                solution_concentrations: Dict[str, float]) -> Dict[str, float]:
        """Calculate nutrient uptake based on root architecture"""
        
        total_surface_area = architecture_metrics['total_root_surface_area']  # cm²
        avg_activity = architecture_metrics['average_root_activity']
        
        # Environmental modifiers
        temperature = environmental_conditions.get('temperature', 20.0)
        flow_rate = environmental_conditions.get('flow_rate', 1.5)
        
        temp_factor = self.calculate_temperature_factor(temperature)
        flow_factor = self.calculate_flow_factor(flow_rate)
        
        uptake_rates = {}
        
        for nutrient, concentration in solution_concentrations.items():
            if nutrient in self.uptake_params.base_uptake_rates:
                # Base uptake rate per unit surface area
                base_rate = self.uptake_params.base_uptake_rates[nutrient]
                
                # Michaelis-Menten kinetics for concentration dependence
                if self.uptake_params.michaelis_constants:
                    km = self.uptake_params.michaelis_constants.get(nutrient, 50.0)
                    conc_factor = concentration / (concentration + km)
                else:
                    conc_factor = 1.0
                
                # Calculate effective uptake surface area by root type
                effective_surface_area = self.calculate_effective_surface_area(architecture_metrics)
                
                # Total uptake calculation
                uptake_rate = (
                    effective_surface_area *     # cm² effective
                    base_rate *                  # mg/cm²/day base
                    conc_factor *                # concentration effect
                    temp_factor *                # temperature effect
                    flow_factor *                # flow rate effect
                    avg_activity                 # root activity factor
                )
                
                uptake_rates[f'{nutrient}_uptake_rate'] = uptake_rate  # mg/day
        
        # Calculate uptake efficiency metrics
        total_uptake = sum(uptake_rates.values())
        uptake_results = {
            **uptake_rates,
            'total_nutrient_uptake': total_uptake,
            'uptake_per_surface_area': total_uptake / max(1.0, total_surface_area),
            'uptake_temperature_factor': temp_factor,
            'uptake_flow_factor': flow_factor,
            'effective_root_surface_area': self.calculate_effective_surface_area(architecture_metrics),
            # Add conversion factors for integration with other models
            'total_uptake_g_per_day': total_uptake / 1000.0,  # Convert mg to g for CROPGRO compatibility
            'nitrogen_uptake_g_per_day': uptake_rates.get('NO3_uptake_rate', 0) / 1000.0
        }
        
        return uptake_results
    
    def calculate_effective_surface_area(self, architecture_metrics: Dict[str, float]) -> float:
        """Calculate effective root surface area weighted by root type activity"""
        
        fine_length = architecture_metrics['fine_root_length']
        medium_length = architecture_metrics['medium_root_length']
        coarse_length = architecture_metrics['coarse_root_length']
        
        # Estimate surface area by root type (rough approximation)
        # Fine roots: 0.15mm diameter, Medium: 0.5mm, Coarse: 1.5mm
        fine_area = fine_length * math.pi * 0.015  # cm²
        medium_area = medium_length * math.pi * 0.05  # cm²
        coarse_area = coarse_length * math.pi * 0.15  # cm²
        
        # Weight by effectiveness factors
        effective_area = (
            fine_area * self.uptake_params.fine_root_effectiveness +
            medium_area * self.uptake_params.medium_root_effectiveness +
            coarse_area * self.uptake_params.coarse_root_effectiveness
        )
        
        return effective_area
    
    def calculate_temperature_factor(self, temperature: float) -> float:
        """Calculate temperature effect on uptake rate"""
        temp_diff = temperature - self.uptake_params.optimal_temperature
        factor = self.uptake_params.q10_factor ** (temp_diff / 10.0)
        
        # Reasonable bounds for temperature effects
        return max(0.1, min(4.0, factor))
    
    def calculate_flow_factor(self, flow_rate: float) -> float:
        """Calculate flow rate effect on uptake rate"""
        optimal_flow = self.uptake_params.optimal_flow_rate
        
        if flow_rate < 0.5:
            # Too low: stagnant conditions, poor nutrient delivery
            return 0.4
        elif flow_rate > self.uptake_params.flow_stress_threshold:
            # Too high: mechanical stress on roots
            return 0.6
        else:
            # Optimal range: sigmoid response around optimal flow rate
            normalized_flow = flow_rate / optimal_flow
            return min(1.0, 0.5 + 0.5 * normalized_flow)
    
    def get_spatial_uptake_distribution(self) -> Dict[str, Dict[str, float]]:
        """Get nutrient uptake capacity by root zone"""
        
        # Get current root distribution
        root_distribution = self.root_architecture.get_root_distribution()
        
        spatial_uptake = {}
        
        for zone_name, zone_data in root_distribution.items():
            zone_surface_area = zone_data['root_surface_area']
            
            # Calculate zone-specific uptake capacity for each nutrient
            zone_uptake = {}
            for nutrient, base_rate in self.uptake_params.base_uptake_rates.items():
                zone_capacity = zone_surface_area * base_rate
                zone_uptake[f'{nutrient}_capacity'] = zone_capacity
            
            zone_uptake['total_surface_area'] = zone_surface_area
            zone_uptake['total_capacity'] = sum(
                v for k, v in zone_uptake.items() if k.endswith('_capacity')
            )
            
            spatial_uptake[zone_name] = zone_uptake
        
        return spatial_uptake
    
    def optimize_environmental_conditions(self, 
                                        target_uptake_rates: Dict[str, float],
                                        current_concentrations: Dict[str, float]) -> Dict[str, float]:
        """
        Optimize environmental conditions to achieve target uptake rates
        
        Returns recommended temperature and flow rate adjustments
        """
        
        current_metrics = self.root_architecture.calculate_architecture_metrics()
        
        # Simple optimization: find temperature and flow rate that maximize uptake
        best_conditions = {'temperature': 20.0, 'flow_rate': 1.5}
        best_score = 0.0
        
        # Grid search over reasonable ranges
        for temp in [16, 18, 20, 22, 24, 26]:
            for flow in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
                temp_factor = self.calculate_temperature_factor(temp)
                flow_factor = self.calculate_flow_factor(flow)
                
                # Score based on how close we get to target uptake rates
                score = 0.0
                for nutrient, target_rate in target_uptake_rates.items():
                    if nutrient in self.uptake_params.base_uptake_rates:
                        base_rate = self.uptake_params.base_uptake_rates[nutrient]
                        concentration = current_concentrations.get(nutrient, 100.0)
                        
                        # Simple uptake prediction
                        predicted_uptake = (
                            current_metrics['total_root_surface_area'] *
                            base_rate * temp_factor * flow_factor *
                            (concentration / (concentration + 50.0))  # Simplified MM
                        )
                        
                        # Score inversely proportional to error
                        error = abs(predicted_uptake - target_rate)
                        score += 1.0 / (1.0 + error / target_rate)
                
                if score > best_score:
                    best_score = score
                    best_conditions = {'temperature': temp, 'flow_rate': flow}
        
        return {
            **best_conditions,
            'optimization_score': best_score,
            'predicted_improvement': (best_score / len(target_uptake_rates)) * 100  # %
        }


def create_enhanced_root_uptake_model(system_type: HydroponicSystemType = HydroponicSystemType.NFT) -> EnhancedRootUptakeModel:
    """Factory function for creating enhanced root uptake model"""
    return EnhancedRootUptakeModel(system_type)


def integrate_with_mechanistic_uptake(enhanced_model: EnhancedRootUptakeModel,
                                    mechanistic_uptake_results: Dict[str, float],
                                    blend_factor: float = 0.7) -> Dict[str, float]:
    """
    Blend enhanced root architecture uptake with existing mechanistic model
    
    Args:
        enhanced_model: The enhanced root uptake model
        mechanistic_uptake_results: Results from existing mechanistic model
        blend_factor: Weight for enhanced model (0=mechanistic only, 1=enhanced only)
        
    Returns:
        Blended uptake results
    """
    
    # Get current enhanced model results (would need to be called after daily_update)
    # This is a template for integration - actual implementation would depend on usage context
    
    blended_results = {}
    
    for key, mechanistic_value in mechanistic_uptake_results.items():
        if key.endswith('_uptake_rate') or key.endswith('_uptake'):
            # For uptake rates, blend the values
            enhanced_key = f'enhanced_{key}'
            if enhanced_key in mechanistic_uptake_results:  # If enhanced result exists
                enhanced_value = mechanistic_uptake_results[enhanced_key]
                blended_value = (
                    (1 - blend_factor) * mechanistic_value +
                    blend_factor * enhanced_value
                )
                blended_results[key] = blended_value
            else:
                blended_results[key] = mechanistic_value
        else:
            # For other metrics, keep original
            blended_results[key] = mechanistic_value
    
    return blended_results


if __name__ == "__main__":
    # Demonstration of enhanced root uptake model
    print("Enhanced Root Architecture Integration - Demonstration")
    print("=" * 70)
    
    # Create model for NFT system
    model = create_enhanced_root_uptake_model(HydroponicSystemType.NFT)
    
    print(f"\nTesting {model.system_type.value.upper()} system:")
    
    # Simulate 20 days with varying conditions
    for day in range(1, 21):
        # Varying environmental conditions
        env_conditions = {
            'temperature': 20.0 + 3.0 * math.sin(day * math.pi / 10),
            'flow_rate': 1.2 + 0.5 * math.sin(day * math.pi / 7),
            'oxygen_level': 8.0,
        }
        
        # Growth factors (improving over time as plant establishes)
        growth_factors = {
            'nitrogen_stress': min(1.0, 0.6 + day * 0.02),
            'water_stress': 0.95,
            'temperature_stress': 0.85
        }
        
        # Nutrient solution concentrations
        solution_concs = {
            'NO3': 150.0 - day * 2.0,  # Decreasing over time
            'NH4': 20.0,
            'PO4': 30.0,
            'K': 120.0
        }
        
        # Update model
        results = model.daily_update(env_conditions, growth_factors, solution_concs)
        
        if day % 5 == 0:
            print(f"\nDay {day:2}:")
            print(f"  Root length: {results['total_root_length']:.1f} cm")
            print(f"  Root surface area: {results['total_root_surface_area']:.0f} cm²")
            print(f"  NO3 uptake: {results['NO3_uptake_rate']:.2f} mg/day")
            print(f"  Total uptake: {results['total_nutrient_uptake']:.2f} mg/day")
            print(f"  Temperature factor: {results['uptake_temperature_factor']:.2f}")
    
    # Test spatial distribution
    print(f"\nSpatial Uptake Distribution (Day 20):")
    spatial_uptake = model.get_spatial_uptake_distribution()
    for zone, data in spatial_uptake.items():
        if data['total_surface_area'] > 0:
            print(f"  {zone}: {data['total_surface_area']:.0f} cm², "
                  f"{data['total_capacity']:.1f} mg/day capacity")
    
    # Test optimization
    print(f"\nOptimization Test:")
    target_rates = {'NO3': 15.0, 'K': 8.0}
    current_concs = {'NO3': 120.0, 'K': 100.0}
    
    optimal_conditions = model.optimize_environmental_conditions(target_rates, current_concs)
    print(f"  Optimal temperature: {optimal_conditions['temperature']:.1f}°C")
    print(f"  Optimal flow rate: {optimal_conditions['flow_rate']:.1f} L/min")
    print(f"  Predicted improvement: {optimal_conditions['predicted_improvement']:.1f}%")