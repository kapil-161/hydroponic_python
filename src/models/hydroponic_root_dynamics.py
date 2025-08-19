"""
Hydroponic Root Dynamics Model
Adapts CROPGRO root modeling principles for soilless cultivation systems
Key differences from soil: unlimited root expansion, solution contact, no soil layers
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class HydroponicSystemType(Enum):
    """Types of hydroponic systems affecting root development."""
    NFT = "nft"              # Nutrient Film Technique
    DWC = "dwc"              # Deep Water Culture  
    DRIP = "drip"            # Drip irrigation
    AERO = "aero"            # Aeroponics
    WICK = "wick"            # Wick system
    EBB_FLOW = "ebb_flow"    # Ebb and flow


@dataclass
class HydroponicRootZone:
    """Hydroponic root zone characteristics - replaces soil layers."""
    zone_type: str           # "solution", "media", "air"
    volume: float            # L - available root space
    solution_contact: float  # fraction (0-1) - root surface in contact with solution
    aeration_level: float    # fraction (0-1) - oxygen availability
    flow_rate: float         # L/min - solution flow through zone
    nutrient_accessibility: float  # fraction (0-1) - how easily roots access nutrients


@dataclass
class HydroponicRootSystem:
    """Complete hydroponic root system model."""
    total_root_mass: float              # g dry weight
    total_root_length: float            # cm total root length
    root_surface_area: float            # cm² total surface area
    specific_root_length: float         # cm/g - length per unit mass
    root_diameter: float                # cm average root diameter
    
    # Hydroponic-specific parameters
    solution_root_fraction: float       # fraction of roots in direct solution contact
    media_root_fraction: float          # fraction of roots in growing media
    air_root_fraction: float            # fraction of roots in air (aeroponics)
    
    # Root zone distribution
    primary_zone_roots: float           # g - roots in main nutrient zone
    secondary_zone_roots: float         # g - roots in media/support zone
    feeder_root_density: float          # cm/cm³ - fine root density for uptake
    
    # Dynamic properties
    root_growth_rate: float             # g/day - daily root mass increase
    root_senescence_rate: float         # g/day - daily root mass loss
    uptake_efficiency: float            # fraction (0-1) - current uptake efficiency
    system_type: HydroponicSystemType


class HydroponicRootModel:
    """Root dynamics model adapted for hydroponic systems."""
    
    def __init__(self, system_type: HydroponicSystemType):
        self.system_type = system_type
        
        # System-specific parameters
        self.system_params = self._initialize_system_parameters()
        
        # Root growth parameters (adapted from CROPGRO)
        self.growth_params = {
            'initial_srl': 800.0,          # cm/g - initial specific root length
            'mature_srl': 600.0,           # cm/g - mature specific root length  
            'max_root_diameter': 0.05,     # cm - maximum root diameter
            'min_root_diameter': 0.01,     # cm - minimum root diameter
            'root_tissue_density': 0.15,   # g/cm³ - root tissue density
            
            # Growth rates by stage
            'establishment_growth': 1.5,    # g/g/day - rapid early root growth
            'vegetative_growth': 0.15,      # g/g/day - steady vegetative growth
            'reproductive_growth': 0.05,    # g/g/day - slow reproductive growth
            
            # Senescence parameters
            'natural_senescence': 0.02,     # fraction/day - natural death rate
            'stress_senescence': 0.08,      # fraction/day - stress-induced death
            'minimum_root_mass': 0.5,       # g - minimum viable root mass
        }
        
        # Environmental response parameters
        self.environmental_factors = {
            'optimal_solution_temp': 18.0,  # °C - optimal root zone temperature
            'temp_tolerance': 5.0,          # °C - temperature tolerance range
            'optimal_dissolved_oxygen': 8.0, # mg/L - optimal DO level
            'min_dissolved_oxygen': 3.0,    # mg/L - minimum viable DO
            'optimal_ph': 6.0,              # optimal pH for root function
            'ph_tolerance': 1.0,            # pH tolerance range
            'flow_rate_factor': 0.1,        # flow rate effect on root development
        }
    
    def _initialize_system_parameters(self) -> Dict:
        """Initialize system-specific parameters for different hydroponic types."""
        
        system_configs = {
            HydroponicSystemType.NFT: {
                'root_zone_volume_factor': 0.5,      # Limited root space in channels
                'solution_contact_fraction': 0.3,    # Partial contact with thin film
                'max_aeration': 0.9,                 # Good aeration in channels
                'flow_dependency': 0.8,              # Highly dependent on flow
                'media_support': False,              # No growing media
                'vertical_root_limit': 15.0,         # cm - channel depth limit
            },
            
            HydroponicSystemType.DWC: {
                'root_zone_volume_factor': 3.0,      # Large solution reservoir
                'solution_contact_fraction': 0.8,    # High solution contact
                'max_aeration': 0.7,                 # Depends on air stones
                'flow_dependency': 0.2,              # Low flow dependency
                'media_support': False,              # Roots suspended in solution
                'vertical_root_limit': 50.0,         # cm - deep reservoir
            },
            
            HydroponicSystemType.DRIP: {
                'root_zone_volume_factor': 1.5,      # Media-filled containers
                'solution_contact_fraction': 0.5,    # Intermittent contact
                'max_aeration': 0.8,                 # Good drainage/aeration
                'flow_dependency': 0.6,              # Moderate flow dependency
                'media_support': True,               # Growing media present
                'vertical_root_limit': 30.0,         # cm - container depth
            },
            
            HydroponicSystemType.AERO: {
                'root_zone_volume_factor': 2.0,      # Large air space
                'solution_contact_fraction': 0.2,    # Misting contact only
                'max_aeration': 1.0,                 # Maximum aeration
                'flow_dependency': 0.9,              # Critical misting dependency
                'media_support': False,              # Roots in air
                'vertical_root_limit': 40.0,         # cm - chamber height
            }
        }
        
        return system_configs.get(self.system_type, system_configs[HydroponicSystemType.NFT])
    
    def initialize_root_system(self, plant_count: int, seedling_weight: float = 2.0, system_enum: HydroponicSystemType = HydroponicSystemType.NFT) -> HydroponicRootSystem:
        """Initialize root system for transplanted seedlings."""
        
        # Initial root mass (typically 15-20% of total seedling weight)
        initial_root_fraction = 0.18
        total_initial_root_mass = plant_count * seedling_weight * initial_root_fraction  # seedling_weight is in g
        
        # Calculate initial root parameters
        initial_srl = self.growth_params['initial_srl']
        initial_root_length = total_initial_root_mass * initial_srl
        
        # Root diameter starts small and increases with age
        initial_diameter = self.growth_params['min_root_diameter']
        initial_surface_area = initial_root_length * np.pi * initial_diameter
        
        # Distribution based on hydroponic system type
        sys_params = self.system_params
        solution_fraction = sys_params['solution_contact_fraction']
        
        return HydroponicRootSystem(
            total_root_mass=total_initial_root_mass,
            total_root_length=initial_root_length,
            root_surface_area=initial_surface_area,
            specific_root_length=initial_srl,
            root_diameter=initial_diameter,
            
            # System-specific distribution
            solution_root_fraction=solution_fraction,
            media_root_fraction=1.0 - solution_fraction if sys_params['media_support'] else 0.0,
            air_root_fraction=1.0 - solution_fraction if not sys_params['media_support'] else 0.0,
            
            # Zone distribution
            primary_zone_roots=total_initial_root_mass * 0.8,  # Most roots in primary zone
            secondary_zone_roots=total_initial_root_mass * 0.2,
            feeder_root_density=initial_root_length / (sys_params['root_zone_volume_factor'] * 1000),  # cm/cm³
            
            # Initial growth rates
            root_growth_rate=0.0,
            root_senescence_rate=0.0,
            uptake_efficiency=0.7,  # Initial efficiency
            system_type=system_enum
        )
    
    def calculate_daily_root_growth(self, root_system: HydroponicRootSystem, 
                                  total_biomass: float, growth_stage: str,
                                  environmental_conditions: Dict) -> HydroponicRootSystem:
        """Calculate daily root growth adapted for hydroponic conditions."""
        
        # Environmental stress factors
        temp_factor = self._calculate_temperature_factor(environmental_conditions.get('temp_avg', 20.0))
        oxygen_factor = self._calculate_oxygen_factor(environmental_conditions.get('dissolved_oxygen', 6.0))
        ph_factor = self._calculate_ph_factor(environmental_conditions.get('ph', 6.0))
        flow_factor = self._calculate_flow_factor(environmental_conditions.get('flow_rate', 1.0))
        
        # Combined environmental factor
        env_factor = min(temp_factor, oxygen_factor, ph_factor) * flow_factor
        env_factor = max(0.1, min(env_factor, 1.0))
        
        # Growth rate based on stage (similar to CROPGRO RFAC2)
        stage_growth_rates = {
            'slow_growth': self.growth_params['establishment_growth'],
            'rapid_growth': self.growth_params['vegetative_growth'],  
            'steady_growth': self.growth_params['reproductive_growth']
        }
        base_growth_rate = stage_growth_rates.get(growth_stage, self.growth_params['vegetative_growth'])
        
        # Root growth allocation (typically 15-25% of total growth goes to roots)
        root_allocation = self._calculate_root_allocation(growth_stage, env_factor)
        
        # Daily root mass increase
        daily_growth = root_system.total_root_mass * base_growth_rate * env_factor * root_allocation
        
        # Senescence calculation (adapted from CROPGRO RTSEN)
        natural_senescence = root_system.total_root_mass * self.growth_params['natural_senescence']
        stress_senescence = root_system.total_root_mass * self.growth_params['stress_senescence'] * (1.0 - env_factor)
        total_senescence = natural_senescence + stress_senescence
        
        # Prevent total root mass from dropping below minimum
        min_mass = self.growth_params['minimum_root_mass']
        if root_system.total_root_mass + daily_growth - total_senescence < min_mass:
            total_senescence = max(0, root_system.total_root_mass + daily_growth - min_mass)
        
        # Update root mass
        new_root_mass = root_system.total_root_mass + daily_growth - total_senescence
        
        # Update specific root length (decreases with age as roots thicken)
        age_factor = min(1.0, new_root_mass / (self.growth_params['minimum_root_mass'] * 10))
        new_srl = (self.growth_params['initial_srl'] * (1 - age_factor) + 
                   self.growth_params['mature_srl'] * age_factor)
        
        # Update root length and surface area
        new_root_length = new_root_mass * new_srl
        
        # Root diameter increases with age and system type
        diameter_range = self.growth_params['max_root_diameter'] - self.growth_params['min_root_diameter']
        new_diameter = self.growth_params['min_root_diameter'] + diameter_range * age_factor
        new_surface_area = new_root_length * np.pi * new_diameter
        
        # Update feeder root density (for nutrient uptake calculations)
        system_volume = self.system_params['root_zone_volume_factor'] * 1000  # cm³
        new_feeder_density = new_root_length * 0.7 / system_volume  # 70% are feeder roots
        
        # Update uptake efficiency based on system health
        base_efficiency = 0.8
        efficiency_factor = env_factor * min(1.0, new_surface_area / (root_system.root_surface_area + 1e-6))
        new_uptake_efficiency = base_efficiency * efficiency_factor
        new_uptake_efficiency = max(0.3, min(new_uptake_efficiency, 1.0))
        
        # Create updated root system
        updated_root_system = HydroponicRootSystem(
            total_root_mass=new_root_mass,
            total_root_length=new_root_length,
            root_surface_area=new_surface_area,
            specific_root_length=new_srl,
            root_diameter=new_diameter,
            
            # Maintain system-specific distributions
            solution_root_fraction=root_system.solution_root_fraction,
            media_root_fraction=root_system.media_root_fraction,
            air_root_fraction=root_system.air_root_fraction,
            
            # Update zone distribution
            primary_zone_roots=new_root_mass * 0.8,
            secondary_zone_roots=new_root_mass * 0.2,
            feeder_root_density=new_feeder_density,
            
            # Store growth rates
            root_growth_rate=daily_growth,
            root_senescence_rate=total_senescence,
            uptake_efficiency=new_uptake_efficiency,
            system_type=root_system.system_type
        )
        
        return updated_root_system
    
    def _calculate_temperature_factor(self, temperature: float) -> float:
        """Calculate temperature stress factor for roots."""
        optimal = self.environmental_factors['optimal_solution_temp']
        tolerance = self.environmental_factors['temp_tolerance']
        
        if abs(temperature - optimal) <= tolerance:
            return 1.0
        elif temperature < optimal - tolerance:
            return max(0.1, 1.0 - (optimal - tolerance - temperature) / tolerance)
        else:  # temperature > optimal + tolerance
            return max(0.1, 1.0 - (temperature - optimal - tolerance) / (tolerance * 2))
    
    def _calculate_oxygen_factor(self, dissolved_oxygen: float) -> float:
        """Calculate oxygen stress factor for roots."""
        optimal = self.environmental_factors['optimal_dissolved_oxygen']
        minimum = self.environmental_factors['min_dissolved_oxygen']
        
        if dissolved_oxygen >= optimal:
            return 1.0
        elif dissolved_oxygen >= minimum:
            return (dissolved_oxygen - minimum) / (optimal - minimum)
        else:
            return 0.1  # Severe stress but not death
    
    def _calculate_ph_factor(self, ph: float) -> float:
        """Calculate pH stress factor for roots."""
        optimal = self.environmental_factors['optimal_ph']
        tolerance = self.environmental_factors['ph_tolerance']
        
        deviation = abs(ph - optimal)
        if deviation <= tolerance:
            return 1.0
        else:
            return max(0.3, 1.0 - (deviation - tolerance) / tolerance)
    
    def _calculate_flow_factor(self, flow_rate: float) -> float:
        """Calculate flow rate factor for root health."""
        flow_dependency = self.system_params['flow_dependency']
        
        if flow_rate <= 0:
            return 0.1  # No flow is critical for most systems
        
        # Optimal flow rate is system-dependent
        optimal_flow = 2.0 if self.system_type == HydroponicSystemType.NFT else 0.5
        
        flow_factor = min(1.0, flow_rate / optimal_flow)
        return 1.0 - flow_dependency * (1.0 - flow_factor)
    
    def _calculate_root_allocation(self, growth_stage: str, env_factor: float) -> float:
        """Calculate fraction of growth allocated to roots."""
        
        # Base allocation by growth stage
        stage_allocations = {
            'slow_growth': 0.35,    # High root development during establishment
            'rapid_growth': 0.20,   # Balanced root/shoot during vegetative growth
            'steady_growth': 0.15   # Lower root priority during reproduction
        }
        
        base_allocation = stage_allocations.get(growth_stage, 0.20)
        
        # Increase root allocation under stress (similar to CROPGRO response)
        stress_factor = 1.0 - env_factor
        stress_allocation_increase = stress_factor * 0.15  # Up to 15% increase under stress
        
        total_allocation = base_allocation + stress_allocation_increase
        return min(0.5, total_allocation)  # Cap at 50% allocation to roots
    
    def calculate_nutrient_uptake_capacity(self, root_system: HydroponicRootSystem,
                                         solution_volume: float) -> float:
        """
        Calculate nutrient uptake capacity based on root surface area in contact with solution.
        This replaces soil-layer based calculations with hydroponic-specific approach.
        """
        
        # Effective root surface area in contact with solution
        effective_surface = (root_system.root_surface_area * 
                           root_system.solution_root_fraction * 
                           root_system.uptake_efficiency)
        
        # Uptake capacity scales with surface area and system efficiency
        system_efficiency = self.system_params['solution_contact_fraction']
        
        # Base uptake capacity (mg/cm²/day) - typical for hydroponic systems
        base_uptake_rate = 0.05  # mg/cm²/day
        
        total_uptake_capacity = effective_surface * base_uptake_rate * system_efficiency
        
        return total_uptake_capacity  # mg/day total system capacity
    
    def get_root_diagnostics(self, root_system: HydroponicRootSystem) -> Dict:
        """Get comprehensive root system diagnostics for monitoring."""
        
        return {
            'total_root_mass_g': root_system.total_root_mass,
            'total_root_length_m': root_system.total_root_length / 100.0,
            'root_surface_area_m2': root_system.root_surface_area / 10000.0,
            'specific_root_length': root_system.specific_root_length,
            'average_root_diameter_mm': root_system.root_diameter * 10,
            'solution_contact_percent': root_system.solution_root_fraction * 100,
            'feeder_root_density': root_system.feeder_root_density,
            'daily_growth_rate': root_system.root_growth_rate,
            'daily_senescence_rate': root_system.root_senescence_rate,
            'uptake_efficiency_percent': root_system.uptake_efficiency * 100,
            'root_health_score': self._calculate_health_score(root_system)
        }
    
    def _calculate_health_score(self, root_system: HydroponicRootSystem) -> float:
        """Calculate overall root health score (0-100)."""
        
        # Factors contributing to root health
        mass_score = min(100, (root_system.total_root_mass / self.growth_params['minimum_root_mass']) * 20)
        growth_score = max(0, min(100, root_system.root_growth_rate * 500))  # Scale daily growth
        efficiency_score = root_system.uptake_efficiency * 100
        
        # Balance score with senescence
        senescence_penalty = min(50, root_system.root_senescence_rate * 1000)
        
        health_score = (mass_score + growth_score + efficiency_score) / 3.0 - senescence_penalty
        return max(0, min(100, health_score))