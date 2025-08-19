"""
Enhanced Root Architecture Model for Hydroponic Systems

Based on literature review findings, implements:
- Root zone stratification (spatial distribution)
- Root age structure and turnover
- Fine vs coarse root dynamics
- Flow rate and temperature effects
- Integration with nutrient uptake models

References:
- Postma et al. (2017) OpenSimRoot framework
- Schnepf et al. (2018) CRootBox modeling
- Zhang et al. (2024) Hybrid ML-physics models
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import numpy as np


class RootType(Enum):
    """Root classification based on diameter and function"""
    FINE = "fine"           # <0.2mm, high activity
    MEDIUM = "medium"       # 0.2-1.0mm, moderate activity  
    COARSE = "coarse"       # >1.0mm, transport/structural


class HydroponicSystemType(Enum):
    """Hydroponic system types with different root architectures"""
    NFT = "nutrient_film_technique"
    DWC = "deep_water_culture"
    AEROPONICS = "aeroponics"
    WICK = "wick_system"


@dataclass
class RootCohort:
    """Represents a cohort of roots of similar age and characteristics"""
    age_days: float
    length: float                    # cm
    diameter: float                  # mm
    root_type: RootType
    zone_depth: float               # cm from root collar
    biomass: float                  # g dry weight
    
    def __post_init__(self):
        self.surface_area = self.calculate_surface_area()
        self.activity_factor = self.calculate_activity_factor()
        self.specific_length = self.length / max(0.001, self.biomass)  # cm/g
    
    def calculate_surface_area(self) -> float:
        """Calculate root surface area (cm²)"""
        diameter_cm = self.diameter / 10.0  # mm to cm
        return math.pi * diameter_cm * self.length
    
    def calculate_activity_factor(self) -> float:
        """Calculate age-dependent root activity factor (0-1)"""
        if self.root_type == RootType.FINE:
            # Fine roots have shorter lifespan but higher activity
            max_age = 45.0  # days
            decline_rate = 0.03
        elif self.root_type == RootType.MEDIUM:
            max_age = 90.0
            decline_rate = 0.02
        else:  # COARSE
            max_age = 180.0
            decline_rate = 0.01
        
        # Exponential decline with age
        activity = math.exp(-decline_rate * self.age_days)
        return max(0.05, activity)  # Minimum 5% activity
    
    def calculate_uptake_capacity(self, base_uptake_rate: float) -> float:
        """Calculate nutrient uptake capacity (mg/day)"""
        return self.surface_area * self.activity_factor * base_uptake_rate


@dataclass  
class RootZoneLayer:
    """Represents a spatial layer in the root zone"""
    depth_range: Tuple[float, float]    # cm from surface
    volume: float                       # cm³
    root_cohorts: List[RootCohort] = field(default_factory=list)
    
    # Environmental conditions
    temperature: float = 20.0           # °C
    flow_rate: float = 1.0             # L/min
    oxygen_level: float = 8.0          # mg/L
    nutrient_concentrations: Dict[str, float] = field(default_factory=dict)
    
    def calculate_root_length_density(self) -> float:
        """Calculate root length density (cm/cm³)"""
        total_length = sum(cohort.length for cohort in self.root_cohorts)
        return total_length / max(1.0, self.volume)
    
    def calculate_root_surface_area_density(self) -> float:
        """Calculate root surface area density (cm²/cm³)"""
        total_area = sum(cohort.surface_area for cohort in self.root_cohorts)
        return total_area / max(1.0, self.volume)
    
    def calculate_total_uptake_capacity(self, nutrient: str, base_rate: float) -> float:
        """Calculate total nutrient uptake capacity for this layer"""
        total_capacity = 0.0
        for cohort in self.root_cohorts:
            # Adjust base rate by temperature and flow effects
            adjusted_rate = self.adjust_uptake_rate(base_rate)
            total_capacity += cohort.calculate_uptake_capacity(adjusted_rate)
        return total_capacity
    
    def adjust_uptake_rate(self, base_rate: float) -> float:
        """Adjust uptake rate based on environmental conditions"""
        # Temperature effect (Q10 = 2.0)
        temp_factor = 2.0 ** ((self.temperature - 20.0) / 10.0)
        temp_factor = max(0.1, min(4.0, temp_factor))  # Reasonable bounds
        
        # Flow rate effect (optimal around 1-2 L/min)
        if self.flow_rate < 0.5:
            flow_factor = 0.5  # Too low, stagnant conditions
        elif self.flow_rate > 4.0:
            flow_factor = 0.7  # Too high, mechanical stress
        else:
            flow_factor = min(1.0, self.flow_rate / 1.5)  # Optimal range
        
        # Oxygen effect
        oxygen_factor = min(1.0, self.oxygen_level / 6.0)  # Optimal > 6 mg/L
        
        return base_rate * temp_factor * flow_factor * oxygen_factor


@dataclass
class RootArchitectureParameters:
    """Parameters for root architecture model"""
    # System-specific parameters
    system_type: HydroponicSystemType = HydroponicSystemType.NFT
    container_volume: float = 1000.0    # cm³
    
    # Root growth parameters
    primary_root_growth_rate: float = 1.5      # cm/day
    lateral_root_density: float = 2.0          # roots/cm primary root
    branching_angle_mean: float = 45.0         # degrees
    branching_angle_std: float = 15.0          # degrees
    
    # Root type distributions (fractions)
    fine_root_fraction: float = 0.6    # 60% fine roots
    medium_root_fraction: float = 0.3  # 30% medium roots
    coarse_root_fraction: float = 0.1  # 10% coarse roots
    
    # Diameter distributions (mm)
    fine_diameter_mean: float = 0.15
    fine_diameter_std: float = 0.05
    medium_diameter_mean: float = 0.5
    medium_diameter_std: float = 0.2
    coarse_diameter_mean: float = 1.5
    coarse_diameter_std: float = 0.5
    
    # Turnover rates (fraction/day)
    fine_turnover_rate: float = 0.015   # 1.5%/day
    medium_turnover_rate: float = 0.008 # 0.8%/day  
    coarse_turnover_rate: float = 0.003 # 0.3%/day
    
    # System-specific adjustments
    system_multipliers: Dict[HydroponicSystemType, Dict[str, float]] = field(default_factory=lambda: {
        HydroponicSystemType.NFT: {
            'root_length_multiplier': 1.0,
            'surface_area_multiplier': 1.0,
            'branching_multiplier': 1.0
        },
        HydroponicSystemType.DWC: {
            'root_length_multiplier': 0.8,
            'surface_area_multiplier': 1.1,
            'branching_multiplier': 1.2
        },
        HydroponicSystemType.AEROPONICS: {
            'root_length_multiplier': 1.5,
            'surface_area_multiplier': 2.0,
            'branching_multiplier': 3.0
        }
    })


class RootArchitectureModel:
    """Enhanced root architecture model for hydroponic systems"""
    
    def __init__(self, parameters: RootArchitectureParameters):
        self.params = parameters
        self.root_zones: List[RootZoneLayer] = []
        self.total_age_days = 0.0
        self.cumulative_root_growth = 0.0
        self.initialize_root_zones()
        
    def initialize_root_zones(self):
        """Initialize root zone layers based on system type"""
        if self.params.system_type == HydroponicSystemType.NFT:
            # NFT: Shallow root zone, concentrated at bottom
            # Use smaller effective volumes for realistic density calculations
            effective_volume = self.params.container_volume * 0.3  # Only 30% of container volume is active root zone
            self.root_zones = [
                RootZoneLayer((0, 2), effective_volume * 0.3),    # Upper zone
                RootZoneLayer((2, 5), effective_volume * 0.4),    # Middle zone  
                RootZoneLayer((5, 8), effective_volume * 0.3)     # Bottom zone
            ]
        elif self.params.system_type == HydroponicSystemType.DWC:
            # DWC: Deep root zone, more uniform distribution
            effective_volume = self.params.container_volume * 0.6  # 60% of container volume is active
            self.root_zones = [
                RootZoneLayer((0, 5), effective_volume * 0.2),    # Surface zone
                RootZoneLayer((5, 15), effective_volume * 0.5),   # Main zone
                RootZoneLayer((15, 25), effective_volume * 0.3)   # Deep zone
            ]
        else:  # AEROPONICS
            # Aeroponics: Vertical root development, maximum surface area
            effective_volume = self.params.container_volume * 0.4  # 40% effective volume but high density
            self.root_zones = [
                RootZoneLayer((0, 3), effective_volume * 0.25),
                RootZoneLayer((3, 8), effective_volume * 0.35),
                RootZoneLayer((8, 15), effective_volume * 0.25),
                RootZoneLayer((15, 20), effective_volume * 0.15)
            ]
    
    def daily_update(self, environmental_conditions: Dict[str, float], 
                    growth_factors: Dict[str, float]) -> Dict[str, float]:
        """Update root architecture for one day"""
        self.total_age_days += 1.0
        
        # Update environmental conditions in each zone
        for zone in self.root_zones:
            zone.temperature = environmental_conditions.get('temperature', 20.0)
            zone.flow_rate = environmental_conditions.get('flow_rate', 1.0)
            zone.oxygen_level = environmental_conditions.get('oxygen_level', 8.0)
            zone.nutrient_concentrations = environmental_conditions.get('nutrient_concentrations', {})
        
        # Age existing roots and remove dead ones
        self.update_root_aging()
        
        # Generate new root growth
        new_growth = self.generate_new_roots(growth_factors)
        self.cumulative_root_growth += new_growth
        
        # Calculate current architecture metrics
        return self.calculate_architecture_metrics()
    
    def update_root_aging(self):
        """Age roots and remove those that have died"""
        for zone in self.root_zones:
            surviving_cohorts = []
            for cohort in zone.root_cohorts:
                cohort.age_days += 1.0
                
                # Update activity factor
                cohort.activity_factor = cohort.calculate_activity_factor()
                
                # Check if root survives (stochastic turnover)
                if cohort.root_type == RootType.FINE:
                    survival_prob = 1.0 - self.params.fine_turnover_rate
                elif cohort.root_type == RootType.MEDIUM:
                    survival_prob = 1.0 - self.params.medium_turnover_rate
                else:
                    survival_prob = 1.0 - self.params.coarse_turnover_rate
                
                if np.random.random() < survival_prob:
                    surviving_cohorts.append(cohort)
                    
            zone.root_cohorts = surviving_cohorts
    
    def generate_new_roots(self, growth_factors: Dict[str, float]) -> float:
        """Generate new root cohorts based on growth conditions"""
        # Base growth rate modified by environmental and nutritional factors
        base_growth = self.params.primary_root_growth_rate
        
        # Apply growth factors
        nitrogen_factor = growth_factors.get('nitrogen_stress', 1.0)
        water_factor = growth_factors.get('water_stress', 1.0)
        temperature_factor = growth_factors.get('temperature_stress', 1.0)
        
        effective_growth = base_growth * nitrogen_factor * water_factor * temperature_factor
        
        # System-specific multipliers
        multipliers = self.params.system_multipliers.get(self.params.system_type, {})
        length_mult = multipliers.get('root_length_multiplier', 1.0)
        branching_mult = multipliers.get('branching_multiplier', 1.0)
        
        total_new_growth = 0.0
        
        # Distribute new growth among zones (deeper zones get less new growth)
        for i, zone in enumerate(self.root_zones):
            # Exponential decay with depth for new growth
            zone_growth_fraction = 0.4 * math.exp(-0.3 * i)
            zone_growth = effective_growth * zone_growth_fraction * length_mult
            
            if zone_growth > 0.01:  # Only create cohorts for significant growth
                # Create new cohorts for each root type
                for root_type in RootType:
                    if root_type == RootType.FINE:
                        fraction = self.params.fine_root_fraction
                        diameter = max(0.05, np.random.normal(
                            self.params.fine_diameter_mean, self.params.fine_diameter_std))
                    elif root_type == RootType.MEDIUM:
                        fraction = self.params.medium_root_fraction  
                        diameter = max(0.15, np.random.normal(
                            self.params.medium_diameter_mean, self.params.medium_diameter_std))
                    else:  # COARSE
                        fraction = self.params.coarse_root_fraction
                        diameter = max(0.8, np.random.normal(
                            self.params.coarse_diameter_mean, self.params.coarse_diameter_std))
                    
                    cohort_length = zone_growth * fraction * branching_mult
                    if cohort_length > 0.1:  # Minimum viable cohort size
                        # Calculate biomass (rough approximation)
                        diameter_cm = diameter / 10.0
                        volume = math.pi * (diameter_cm/2)**2 * cohort_length
                        biomass = volume * 0.3  # ~0.3 g/cm³ dry density (more realistic for roots)
                        
                        new_cohort = RootCohort(
                            age_days=0.0,
                            length=cohort_length,
                            diameter=diameter,
                            root_type=root_type,
                            zone_depth=sum(zone.depth_range) / 2,
                            biomass=biomass
                        )
                        
                        zone.root_cohorts.append(new_cohort)
                        total_new_growth += cohort_length
        
        return total_new_growth
    
    def calculate_architecture_metrics(self) -> Dict[str, float]:
        """Calculate current root architecture metrics"""
        total_length = 0.0
        total_surface_area = 0.0
        total_biomass = 0.0
        total_volume = 0.0
        
        fine_length = 0.0
        medium_length = 0.0
        coarse_length = 0.0
        
        weighted_activity = 0.0
        total_cohorts = 0
        
        for zone in self.root_zones:
            for cohort in zone.root_cohorts:
                total_length += cohort.length
                total_surface_area += cohort.surface_area
                total_biomass += cohort.biomass
                
                # Volume calculation
                diameter_cm = cohort.diameter / 10.0
                cohort_volume = math.pi * (diameter_cm/2)**2 * cohort.length
                total_volume += cohort_volume
                
                # Type-specific lengths
                if cohort.root_type == RootType.FINE:
                    fine_length += cohort.length
                elif cohort.root_type == RootType.MEDIUM:
                    medium_length += cohort.length
                else:
                    coarse_length += cohort.length
                
                weighted_activity += cohort.activity_factor
                total_cohorts += 1
        
        # Calculate densities
        total_zone_volume = sum(zone.volume for zone in self.root_zones)
        root_length_density = total_length / max(1.0, total_zone_volume)
        root_surface_area_density = total_surface_area / max(1.0, total_zone_volume)
        
        # Calculate average metrics
        avg_activity = weighted_activity / max(1, total_cohorts)
        specific_root_length = total_length / max(0.001, total_biomass)  # cm/g
        
        return {
            'total_root_length': total_length,              # cm
            'total_root_surface_area': total_surface_area,  # cm²
            'total_root_biomass': total_biomass,            # g
            'total_root_volume': total_volume,              # cm³
            'root_length_density': root_length_density,    # cm/cm³
            'root_surface_area_density': root_surface_area_density,  # cm²/cm³
            'specific_root_length': specific_root_length,  # cm/g
            'average_root_activity': avg_activity,         # 0-1
            'fine_root_length': fine_length,               # cm
            'medium_root_length': medium_length,           # cm  
            'coarse_root_length': coarse_length,           # cm
            'fine_root_fraction': fine_length / max(1.0, total_length),
            'root_age_days': self.total_age_days,
            'cumulative_growth': self.cumulative_root_growth
        }
    
    def calculate_nutrient_uptake_capacity(self, nutrient: str, 
                                         base_uptake_rate: float) -> Dict[str, float]:
        """Calculate nutrient uptake capacity by zone and total"""
        zone_capacities = {}
        total_capacity = 0.0
        
        for i, zone in enumerate(self.root_zones):
            zone_name = f"zone_{i+1}"
            capacity = zone.calculate_total_uptake_capacity(nutrient, base_uptake_rate)
            zone_capacities[zone_name] = capacity
            total_capacity += capacity
        
        zone_capacities['total_capacity'] = total_capacity
        return zone_capacities
    
    def get_root_distribution(self) -> Dict[str, Dict[str, float]]:
        """Get spatial distribution of roots by zone"""
        distribution = {}
        
        for i, zone in enumerate(self.root_zones):
            zone_name = f"zone_{i+1}_depth_{zone.depth_range[0]}-{zone.depth_range[1]}cm"
            
            total_length = sum(cohort.length for cohort in zone.root_cohorts)
            total_area = sum(cohort.surface_area for cohort in zone.root_cohorts)
            total_biomass = sum(cohort.biomass for cohort in zone.root_cohorts)
            
            distribution[zone_name] = {
                'root_length': total_length,
                'root_surface_area': total_area,
                'root_biomass': total_biomass,
                'root_length_density': zone.calculate_root_length_density(),
                'root_surface_area_density': zone.calculate_root_surface_area_density(),
                'num_cohorts': len(zone.root_cohorts)
            }
        
        return distribution


def create_lettuce_root_architecture_model(system_type: HydroponicSystemType = HydroponicSystemType.NFT) -> RootArchitectureModel:
    """Create a root architecture model optimized for lettuce"""
    params = RootArchitectureParameters(
        system_type=system_type,
        container_volume=1500.0,  # cm³, typical lettuce root zone
        
        # Lettuce-specific parameters
        primary_root_growth_rate=2.0,  # cm/day
        lateral_root_density=3.5,      # roots/cm
        
        # Lettuce root type distribution
        fine_root_fraction=0.65,       # Higher fine root fraction
        medium_root_fraction=0.30,
        coarse_root_fraction=0.05,
        
        # Lettuce-specific diameters (mm)
        fine_diameter_mean=0.12,
        fine_diameter_std=0.04,
        medium_diameter_mean=0.4,
        medium_diameter_std=0.15,
        coarse_diameter_mean=1.2,
        coarse_diameter_std=0.4,
        
        # Lettuce turnover rates (faster than perennial crops)
        fine_turnover_rate=0.02,       # 2%/day
        medium_turnover_rate=0.01,     # 1%/day
        coarse_turnover_rate=0.005     # 0.5%/day
    )
    
    return RootArchitectureModel(params)


if __name__ == "__main__":
    # Demonstration
    print("Enhanced Root Architecture Model - Demonstration")
    print("=" * 60)
    
    # Test different systems
    systems = [HydroponicSystemType.NFT, HydroponicSystemType.DWC, HydroponicSystemType.AEROPONICS]
    
    for system in systems:
        print(f"\n{system.value.upper()} System:")
        print("-" * 40)
        
        model = create_lettuce_root_architecture_model(system)
        
        # Simulate 30 days
        for day in range(1, 31):
            env_conditions = {
                'temperature': 20.0 + 2.0 * math.sin(day * math.pi / 15),
                'flow_rate': 1.5,
                'oxygen_level': 8.0,
                'nutrient_concentrations': {'NO3': 150.0, 'NH4': 20.0}
            }
            
            growth_factors = {
                'nitrogen_stress': 0.9,
                'water_stress': 0.95,
                'temperature_stress': 0.85
            }
            
            metrics = model.daily_update(env_conditions, growth_factors)
            
            if day % 10 == 0:
                print(f"Day {day:2}: Length={metrics['total_root_length']:.1f}cm, "
                      f"Area={metrics['total_root_surface_area']:.0f}cm², "
                      f"Biomass={metrics['total_root_biomass']:.2f}g")
        
        # Final distribution
        print(f"\nFinal Root Distribution:")
        distribution = model.get_root_distribution()
        for zone, data in distribution.items():
            print(f"  {zone}: {data['root_length']:.1f}cm length, "
                  f"{data['root_surface_area']:.0f}cm² area")