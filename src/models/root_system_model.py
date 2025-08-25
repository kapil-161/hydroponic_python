"""
Unified Root System Model

Combines:
- Enhanced Root Architecture Model (spatial, cohorts)
- Hydroponic Root Dynamics utilities
- Root Architecture Integration (Enhanced nutrient uptake)

This consolidation replaces:
- src/models/root_architecture.py
- src/models/hydroponic_root_dynamics.py
- src/models/root_architecture_integration.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional

import numpy as np


# =========================
# Root Architecture (from root_architecture.py)
# =========================

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
    # Aliases/extended systems to subsume hydroponic_root_dynamics variants
    AERO = "aeroponics"        # alias of AEROPONICS
    DRIP = "drip"
    WICK = "wick_system"
    EBB_FLOW = "ebb_flow"


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
        """Calculate age-dependent root activity factor (0-1).

        Use a half-life based decay with an early-life plateau and
        a higher minimum activity to avoid unrealistic rapid inactivity.
        """
        if self.root_type == RootType.FINE:
            half_life_days = 45.0
            min_activity = 0.20
        elif self.root_type == RootType.MEDIUM:
            half_life_days = 90.0
            min_activity = 0.25
        else:  # COARSE
            half_life_days = 180.0
            min_activity = 0.30

        # Early establishment plateau (no decline for first week)
        if self.age_days <= 7.0:
            base_activity = 1.0
        else:
            # Half-life decay: activity = 0.5 ** (age / half_life)
            base_activity = 0.5 ** (self.age_days / max(1e-6, half_life_days))

        # Clamp to biologically reasonable minimums
        return max(min_activity, base_activity)

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
            adjusted_rate = self.adjust_uptake_rate(base_rate)
            total_capacity += cohort.calculate_uptake_capacity(adjusted_rate)
        return total_capacity

    def adjust_uptake_rate(self, base_rate: float) -> float:
        """Adjust uptake rate based on environmental conditions"""
        # Temperature effect (Q10 ≈ 1.6 typical for root uptake)
        temp_factor = 1.6 ** ((self.temperature - 20.0) / 10.0)
        temp_factor = max(0.5, min(2.5, temp_factor))

        # Flow rate effect (optimal around 1-2 L/min)
        if self.flow_rate < 0.5:
            flow_factor = 0.5
        elif self.flow_rate > 4.0:
            flow_factor = 0.7
        else:
            flow_factor = min(1.0, self.flow_rate / 1.5)

        # Oxygen effect
        oxygen_factor = min(1.0, self.oxygen_level / 6.0)
        
        # pH effect - optimal range 5.5-6.5 for nutrient uptake
        current_ph = getattr(self, 'ph', 6.0)
        if 5.5 <= current_ph <= 6.5:
            ph_factor = 1.0
        else:
            ph_deviation = min(abs(current_ph - 5.5), abs(current_ph - 6.5))
            ph_factor = max(0.3, 1.0 - ph_deviation * 0.15)  # Less severe than growth effects

        return base_rate * temp_factor * flow_factor * oxygen_factor * ph_factor


@dataclass
class RootArchitectureParameters:
    """Parameters for root architecture model"""
    # System-specific parameters
    system_type: HydroponicSystemType = HydroponicSystemType.NFT
    container_volume: float = 1000.0    # cm³ (reservoir tank volume)
    
    # NFT-specific channel parameters
    channel_length: float = 100.0       # cm
    channel_width: float = 10.0         # cm  
    channel_depth: float = 5.0          # cm
    n_channels: int = 4                 # number of parallel channels
    root_zone_independent: bool = True   # root zone size independent of tank volume

    # Root growth parameters
    primary_root_growth_rate: float = 1.5      # cm/day
    lateral_root_density: float = 2.0          # roots/cm primary root
    branching_angle_mean: float = 45.0         # degrees
    branching_angle_std: float = 15.0          # degrees

    # Root type distributions (fractions)
    fine_root_fraction: float = 0.6
    medium_root_fraction: float = 0.3
    coarse_root_fraction: float = 0.1

    # Diameter distributions (mm)
    fine_diameter_mean: float = 0.15
    fine_diameter_std: float = 0.05
    medium_diameter_mean: float = 0.5
    medium_diameter_std: float = 0.2
    coarse_diameter_mean: float = 1.5
    coarse_diameter_std: float = 0.5

    # Turnover rates (fraction/day)
    fine_turnover_rate: float = 0.015
    medium_turnover_rate: float = 0.008
    coarse_turnover_rate: float = 0.003

    # System-specific adjustments
    system_multipliers: Dict[HydroponicSystemType, Dict[str, float]] = field(
        default_factory=lambda: {
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
            },
            # Extended systems use nearest equivalents
            HydroponicSystemType.DRIP: {
                'root_length_multiplier': 1.1,
                'surface_area_multiplier': 1.1,
                'branching_multiplier': 1.2
            },
            HydroponicSystemType.WICK: {
                'root_length_multiplier': 0.7,
                'surface_area_multiplier': 0.9,
                'branching_multiplier': 0.8
            },
            HydroponicSystemType.EBB_FLOW: {
                'root_length_multiplier': 1.0,
                'surface_area_multiplier': 1.2,
                'branching_multiplier': 1.3
            },
        }
    )


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
            # NFT: Root zone determined by channel dimensions, not tank volume
            channel_volume = (
                self.params.channel_length * 
                self.params.channel_width * 
                self.params.channel_depth * 
                self.params.n_channels
            )
            # Root development space in the channels
            effective_volume = channel_volume * 0.6  # 60% usable for roots
            
            self.root_zones = [
                RootZoneLayer((0, 2), effective_volume * 0.4),   # Upper channel zone
                RootZoneLayer((2, 4), effective_volume * 0.4),   # Middle channel zone  
                RootZoneLayer((4, 6), effective_volume * 0.2)    # Lower channel zone
            ]
        elif self.params.system_type == HydroponicSystemType.DWC:
            effective_volume = self.params.container_volume * 0.6
            self.root_zones = [
                RootZoneLayer((0, 5), effective_volume * 0.2),
                RootZoneLayer((5, 15), effective_volume * 0.5),
                RootZoneLayer((15, 25), effective_volume * 0.3)
            ]
        else:  # Aeroponics and others
            effective_volume = self.params.container_volume * 0.4
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
            zone.ph = environmental_conditions.get('ph', 6.0)
            zone.nutrient_concentrations = environmental_conditions.get('nutrient_concentrations', {})

        self.update_root_aging()
        new_growth = self.generate_new_roots(growth_factors, environmental_conditions)
        self.cumulative_root_growth += new_growth

        return self.calculate_architecture_metrics()

    def update_root_aging(self):
        """Age roots and remove those that have died"""
        for zone in self.root_zones:
            surviving_cohorts = []
            for cohort in zone.root_cohorts:
                cohort.age_days += 1.0
                cohort.activity_factor = cohort.calculate_activity_factor()

                if cohort.root_type == RootType.FINE:
                    survival_prob = 1.0 - self.params.fine_turnover_rate
                elif cohort.root_type == RootType.MEDIUM:
                    survival_prob = 1.0 - self.params.medium_turnover_rate
                else:
                    survival_prob = 1.0 - self.params.coarse_turnover_rate

                if np.random.random() < survival_prob:
                    surviving_cohorts.append(cohort)

            zone.root_cohorts = surviving_cohorts

    def generate_new_roots(self, growth_factors: Dict[str, float], environmental_conditions: Dict[str, float]) -> float:
        """Generate new root cohorts based on growth conditions"""
        base_growth = self.params.primary_root_growth_rate

        nitrogen_factor = growth_factors.get('nitrogen_stress', 1.0)
        water_factor = growth_factors.get('water_stress', 1.0)
        temperature_factor = growth_factors.get('temperature_stress', 1.0)

        effective_growth = base_growth * nitrogen_factor * water_factor * temperature_factor

        multipliers = self.params.system_multipliers.get(self.params.system_type, {})
        length_mult = multipliers.get('root_length_multiplier', 1.0)
        branching_mult = multipliers.get('branching_multiplier', 1.0)

        total_new_growth = 0.0

        for i, zone in enumerate(self.root_zones):
            # Root growth driven by auxin gradients and nutrient availability
            zone_growth_fraction = self._calculate_zone_growth_potential(
                zone, i, environmental_conditions, growth_factors
            )
            zone_growth = effective_growth * zone_growth_fraction * length_mult

            if zone_growth > 0.01:
                for root_type in RootType:
                    if root_type == RootType.FINE:
                        fraction = self.params.fine_root_fraction
                        diameter = max(0.05, np.random.normal(
                            self.params.fine_diameter_mean, self.params.fine_diameter_std))
                    elif root_type == RootType.MEDIUM:
                        fraction = self.params.medium_root_fraction
                        diameter = max(0.15, np.random.normal(
                            self.params.medium_diameter_mean, self.params.medium_diameter_std))
                    else:
                        fraction = self.params.coarse_root_fraction
                        diameter = max(0.8, np.random.normal(
                            self.params.coarse_diameter_mean, self.params.coarse_diameter_std))

                    cohort_length = zone_growth * fraction * branching_mult
                    if cohort_length > 0.1:
                        diameter_cm = diameter / 10.0
                        volume = math.pi * (diameter_cm/2)**2 * cohort_length
                        biomass = volume * 0.3

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

    def _calculate_zone_growth_potential(self, zone: 'RootZoneLayer', zone_index: int,
                                        environmental_conditions: Dict[str, float],
                                        growth_factors: Dict[str, float]) -> float:
        """
        Calculate root growth potential based on biological gradients.
        
        Root growth is driven by:
        1. Auxin transport from shoot (decreases with distance)
        2. Local nutrient availability (attracts root growth)
        3. Oxygen availability (essential for respiration)
        4. Root competition (density-dependent inhibition)
        """
        
        # 1. AUXIN GRADIENT EFFECT
        # Auxin concentration decreases exponentially from shoot
        # Hydroponic systems: auxin transport limited by root length, not soil impedance
        auxin_decay_rate = 0.15  # per zone index (biology-based)
        auxin_gradient = math.exp(-auxin_decay_rate * zone_index)
        
        # 2. NUTRIENT AVAILABILITY EFFECT  
        # Roots grow toward high nutrient concentrations (chemotropism)
        nutrient_concentrations = environmental_conditions.get('nutrient_concentrations', {})
        
        # Calculate nutrient attractiveness (weighted by plant demand)
        nutrient_demand_weights = {
            'N-NO3': 0.4,  # Nitrogen is primary growth driver
            'P-PO4': 0.25, # Phosphorus for energy metabolism
            'K': 0.2,      # Potassium for osmotic regulation  
            'Ca': 0.1,     # Calcium for cell walls
            'Mg': 0.05     # Magnesium for chlorophyll
        }
        
        nutrient_signal = 0.0
        for nutrient, weight in nutrient_demand_weights.items():
            conc = nutrient_concentrations.get(nutrient, 100.0)  # mg/L
            # Normalized to typical hydroponic concentrations
            normalized_conc = min(1.0, conc / 200.0)  # 200 mg/L as reference
            nutrient_signal += weight * normalized_conc
        
        # 3. OXYGEN AVAILABILITY EFFECT
        # Root respiration requires oxygen - critical in hydroponics
        oxygen_level = environmental_conditions.get('oxygen_level', 8.0)  # mg/L DO
        optimal_oxygen = 6.0  # mg/L minimum for healthy root growth
        
        if oxygen_level >= optimal_oxygen:
            oxygen_effect = 1.0
        else:
            # Linear decline below optimal (root death below 2 mg/L)
            oxygen_effect = max(0.1, oxygen_level / optimal_oxygen)
        
        # 4. ROOT DENSITY COMPETITION
        # Higher root density in zone reduces further growth (self-inhibition)
        zone_root_density = zone.calculate_root_length_density()
        optimal_density = 2.0  # cm/cm³ for efficient nutrient uptake
        
        if zone_root_density <= optimal_density:
            competition_effect = 1.0
        else:
            # Density-dependent growth reduction
            density_stress = (zone_root_density - optimal_density) / optimal_density
            competition_effect = max(0.2, 1.0 - 0.5 * density_stress)
        
        # 5. TEMPERATURE EFFECT ON ROOT ELONGATION
        temperature = environmental_conditions.get('temperature', 20.0)
        root_temp_optimum = 18.0  # °C optimal for lettuce roots  
        root_temp_max = 30.0      # °C maximum before damage
        
        if temperature <= root_temp_optimum:
            temp_effect = max(0.3, temperature / root_temp_optimum)
        else:
            # Heat stress reduces root growth
            heat_stress = (temperature - root_temp_optimum) / (root_temp_max - root_temp_optimum)
            temp_effect = max(0.1, 1.0 - heat_stress)
        
        # COMBINED GROWTH POTENTIAL
        # Multiplicative combination (all factors must be favorable)
        zone_growth_potential = (
            auxin_gradient *        # 0.0-1.0 (decreases with distance)
            nutrient_signal *       # 0.0-1.0 (higher where nutrients abundant)  
            oxygen_effect *         # 0.1-1.0 (essential for respiration)
            competition_effect *    # 0.2-1.0 (density-dependent inhibition)
            temp_effect            # 0.1-1.0 (temperature optimum)
        )
        
        # Normalize across zones (ensure total growth is conserved)
        return max(0.05, min(0.8, zone_growth_potential))

    def calculate_architecture_metrics(self) -> Dict[str, float]:
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

                diameter_cm = cohort.diameter / 10.0
                cohort_volume = math.pi * (diameter_cm/2)**2 * cohort.length
                total_volume += cohort_volume

                if cohort.root_type == RootType.FINE:
                    fine_length += cohort.length
                elif cohort.root_type == RootType.MEDIUM:
                    medium_length += cohort.length
                else:
                    coarse_length += cohort.length

                weighted_activity += cohort.activity_factor
                total_cohorts += 1

        total_zone_volume = sum(zone.volume for zone in self.root_zones)
        root_length_density = total_length / max(1.0, total_zone_volume)
        root_surface_area_density = total_surface_area / max(1.0, total_zone_volume)

        avg_activity = weighted_activity / max(1, total_cohorts)
        specific_root_length = total_length / max(0.001, total_biomass)

        return {
            'total_root_length': total_length,
            'total_root_surface_area': total_surface_area,
            'total_root_biomass': total_biomass,
            'total_root_volume': total_volume,
            'root_length_density': root_length_density,
            'root_surface_area_density': root_surface_area_density,
            'specific_root_length': specific_root_length,
            'average_root_activity': avg_activity,
            'fine_root_length': fine_length,
            'medium_root_length': medium_length,
            'coarse_root_length': coarse_length,
            'fine_root_fraction': fine_length / max(1.0, total_length),
            'root_age_days': self.total_age_days,
            'cumulative_growth': self.cumulative_root_growth
        }

    def get_root_distribution(self) -> Dict[str, Dict[str, float]]:
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


def create_lettuce_root_architecture_model(system_type: HydroponicSystemType = HydroponicSystemType.NFT, 
                                          tank_volume: float = 1500.0) -> RootArchitectureModel:
    """Create a root architecture model optimized for lettuce"""
    
    if system_type == HydroponicSystemType.NFT:
        # NFT: Root zone is independent of tank volume - determined by channel dimensions
        params = RootArchitectureParameters(
            system_type=system_type,
            container_volume=tank_volume,  # Tank volume for nutrient storage only
            # NFT channel configuration for 20 lettuce plants
            channel_length=200.0,    # cm (2 meters)
            channel_width=10.0,      # cm  
            channel_depth=8.0,       # cm
            n_channels=4,            # 4 channels, 5 plants each
            root_zone_independent=True,
            # Growth parameters
            primary_root_growth_rate=2.0,
            lateral_root_density=3.5,
            fine_root_fraction=0.65,
            medium_root_fraction=0.30,
            coarse_root_fraction=0.05,
            fine_diameter_mean=0.12,
            fine_diameter_std=0.04,
            medium_diameter_mean=0.4,
            medium_diameter_std=0.15,
            coarse_diameter_mean=1.2,
            coarse_diameter_std=0.4,
            fine_turnover_rate=0.02,
            medium_turnover_rate=0.01,
            coarse_turnover_rate=0.005,
        )
    else:
        # For other systems, use container volume-dependent approach
        params = RootArchitectureParameters(
            system_type=system_type,
            container_volume=tank_volume,
            root_zone_independent=False,
            primary_root_growth_rate=2.0,
            lateral_root_density=3.5,
            fine_root_fraction=0.65,
            medium_root_fraction=0.30,
            coarse_root_fraction=0.05,
            fine_diameter_mean=0.12,
            fine_diameter_std=0.04,
            medium_diameter_mean=0.4,
            medium_diameter_std=0.15,
            coarse_diameter_mean=1.2,
            coarse_diameter_std=0.4,
            fine_turnover_rate=0.02,
            medium_turnover_rate=0.01,
            coarse_turnover_rate=0.005,
        )
    
    return RootArchitectureModel(params)


# =========================
# Hydroponic Root Dynamics (from hydroponic_root_dynamics.py)
# =========================

@dataclass
class HydroponicRootZone:
    """Hydroponic root zone characteristics - replaces soil layers."""
    zone_type: str           # "solution", "media", "air"
    volume: float            # L
    solution_contact: float  # 0-1
    aeration_level: float    # 0-1
    flow_rate: float         # L/min
    nutrient_accessibility: float  # 0-1


@dataclass
class HydroponicRootSystem:
    """Complete hydroponic root system model."""
    total_root_mass: float              # g dry weight
    total_root_length: float            # cm
    root_surface_area: float            # cm²
    specific_root_length: float         # cm/g
    root_diameter: float                # cm

    # Hydroponic-specific parameters
    solution_root_fraction: float
    media_root_fraction: float
    air_root_fraction: float

    # Root zone distribution
    primary_zone_roots: float           # g
    secondary_zone_roots: float         # g
    feeder_root_density: float          # cm/cm³

    # Dynamic properties
    root_growth_rate: float             # g/day
    root_senescence_rate: float         # g/day
    uptake_efficiency: float            # 0-1
    system_type: HydroponicSystemType


class HydroponicRootModel:
    """Root dynamics model adapted for hydroponic systems."""

    def __init__(self, system_type: HydroponicSystemType):
        self.system_type = system_type
        self.system_params = self._initialize_system_parameters()
        self.growth_params = {
            'initial_srl': 800.0,
            'mature_srl': 600.0,
            'max_root_diameter': 0.05,
            'min_root_diameter': 0.01,
            'root_tissue_density': 0.15,
            'establishment_growth': 1.5,
            'vegetative_growth': 0.15,
            'reproductive_growth': 0.05,
            'natural_senescence': 0.02,
            'stress_senescence': 0.08,
            'minimum_root_mass': 0.5,
        }
        self.environmental_factors = {
            'optimal_solution_temp': 18.0,
            'temp_tolerance': 5.0,
            'optimal_dissolved_oxygen': 8.0,
            'min_dissolved_oxygen': 3.0,
            'optimal_ph': 6.0,
            'ph_tolerance': 1.0,
            'flow_rate_factor': 0.1,
        }

    def _initialize_system_parameters(self) -> Dict:
        system_configs = {
            HydroponicSystemType.NFT: {
                'root_zone_volume_factor': 0.5,
                'solution_contact_fraction': 0.3,
                'max_aeration': 0.9,
                'flow_dependency': 0.8,
                'media_support': False,
                'vertical_root_limit': 15.0,
            },
            HydroponicSystemType.DWC: {
                'root_zone_volume_factor': 3.0,
                'solution_contact_fraction': 0.8,
                'max_aeration': 0.7,
                'flow_dependency': 0.2,
                'media_support': False,
                'vertical_root_limit': 50.0,
            },
            HydroponicSystemType.AEROPONICS: {
                'root_zone_volume_factor': 2.0,
                'solution_contact_fraction': 0.2,
                'max_aeration': 1.0,
                'flow_dependency': 0.9,
                'media_support': False,
                'vertical_root_limit': 40.0,
            },
        }
        return system_configs.get(self.system_type, system_configs[HydroponicSystemType.NFT])

    def calculate_nutrient_uptake_capacity(self, root_system: HydroponicRootSystem,
                                           solution_volume: float) -> float:
        effective_surface = (
            root_system.root_surface_area *
            root_system.solution_root_fraction *
            root_system.uptake_efficiency
        )
        system_efficiency = self.system_params['solution_contact_fraction']
        base_uptake_rate = 0.05  # mg/cm²/day
        total_uptake_capacity = effective_surface * base_uptake_rate * system_efficiency
        return total_uptake_capacity

    def _calculate_health_score(self, root_system: HydroponicRootSystem) -> float:
        mass_score = min(100, (root_system.total_root_mass / self.growth_params['minimum_root_mass']) * 20)
        growth_score = max(0, min(100, root_system.root_growth_rate * 500))
        efficiency_score = root_system.uptake_efficiency * 100
        senescence_penalty = min(50, root_system.root_senescence_rate * 1000)
        health_score = (mass_score + growth_score + efficiency_score) / 3.0 - senescence_penalty
        return max(0, min(100, health_score))


# =========================
# Root Architecture Integration (from root_architecture_integration.py)
# =========================

@dataclass
class RootUptakeParameters:
    """Parameters for root-architecture-based nutrient uptake"""
    base_uptake_rates: Dict[str, float]
    fine_root_effectiveness: float = 1.0
    medium_root_effectiveness: float = 0.6
    coarse_root_effectiveness: float = 0.2
    optimal_temperature: float = 20.0
    q10_factor: float = 2.0
    optimal_flow_rate: float = 1.5
    flow_stress_threshold: float = 4.0
    michaelis_constants: Dict[str, float] = None


class EnhancedRootUptakeModel:
    """
    Enhanced nutrient uptake model using detailed root architecture
    """

    def __init__(self, system_type: HydroponicSystemType = HydroponicSystemType.NFT, 
                 tank_volume: float = 1500.0):
        self.root_architecture = create_lettuce_root_architecture_model(system_type, tank_volume)
        self.system_type = system_type
        self.tank_volume = tank_volume
        self.uptake_params = RootUptakeParameters(
            base_uptake_rates={
                'NO3': 0.15,    # mg/cm²/day - realistic for hydroponic lettuce
                'NH4': 0.09,    # mg/cm²/day - reduced from 3.6
                'PO4': 0.03,    # mg/cm²/day - reduced from 1.2
                'K': 0.12,      # mg/cm²/day - reduced from 4.8
                'Ca': 0.06,     # mg/cm²/day - reduced from 2.4
                'Mg': 0.05,     # mg/cm²/day - reduced from 1.9
                'SO4': 0.04,    # mg/cm²/day - reduced from 1.4
            },
            michaelis_constants={
                'NO3': 6.0,
                'NH4': 20.0,
                'PO4': 5.0,
                'K': 30.0,
                'Ca': 40.0,
                'Mg': 25.0,
                'SO4': 35.0,
            },
        )

    def daily_update(self,
                     environmental_conditions: Dict[str, float],
                     growth_factors: Dict[str, float],
                     solution_concentrations: Dict[str, float]) -> Dict[str, float]:
        architecture_metrics = self.root_architecture.daily_update(
            environmental_conditions, growth_factors
        )
        uptake_results = self.calculate_nutrient_uptake(
            architecture_metrics, environmental_conditions, solution_concentrations
        )
        return {
            **architecture_metrics,
            **uptake_results,
            'system_type': self.system_type.value
        }

    def calculate_nutrient_uptake(self,
                                  architecture_metrics: Dict[str, float],
                                  environmental_conditions: Dict[str, float],
                                  solution_concentrations: Dict[str, float]) -> Dict[str, float]:
        total_surface_area = architecture_metrics['total_root_surface_area']
        avg_activity = architecture_metrics['average_root_activity']

        temperature = environmental_conditions.get('temperature', 20.0)
        flow_rate = environmental_conditions.get('flow_rate', 1.5)

        temp_factor = self.calculate_temperature_factor(temperature)
        flow_factor = self.calculate_flow_factor(flow_rate)

        uptake_rates: Dict[str, float] = {}
        for nutrient, concentration in solution_concentrations.items():
            if nutrient in self.uptake_params.base_uptake_rates:
                
                # True Michaelis-Menten kinetics: V = Vmax * [S] / (Km + [S])
                vmax = self.uptake_params.base_uptake_rates[nutrient]  # mg/cm²/day (maximum rate)
                km = self.uptake_params.michaelis_constants.get(nutrient, 50.0) if self.uptake_params.michaelis_constants else 50.0
                
                # Michaelis-Menten equation
                michaelis_rate = (vmax * concentration) / (km + concentration)
                
                # Competitive inhibition between similar nutrients
                inhibition_factor = self._calculate_nutrient_competition(nutrient, solution_concentrations)
                
                # pH effects on nutrient speciation and uptake
                ph = environmental_conditions.get('ph', 6.0)
                ph_effect = self._calculate_ph_effect_on_uptake(nutrient, ph)
                
                # Temperature effects on carrier protein activity (Q10 = 2.5 for transport)
                transport_temp_effect = temp_factor ** 1.25  # Enhanced temperature sensitivity for transport
                
                # Root age effect (young roots have higher transporter density)
                root_age_effect = self._calculate_root_age_effect(architecture_metrics)
                
                effective_surface_area = self.calculate_effective_surface_area(architecture_metrics)
                
                # Final uptake rate with all biological factors
                uptake_rate = (
                    effective_surface_area * michaelis_rate * inhibition_factor * 
                    ph_effect * transport_temp_effect * flow_factor * avg_activity * root_age_effect
                )
                uptake_rates[f'{nutrient}_uptake_rate'] = uptake_rate

        total_uptake = sum(uptake_rates.values())
        return {
            **uptake_rates,
            'total_nutrient_uptake': total_uptake,
            'uptake_per_surface_area': total_uptake / max(1.0, total_surface_area),
            'uptake_temperature_factor': temp_factor,
            'uptake_flow_factor': flow_factor,
            'effective_root_surface_area': self.calculate_effective_surface_area(architecture_metrics),
            'total_uptake_g_per_day': total_uptake / 1000.0,
            'nitrogen_uptake_g_per_day': uptake_rates.get('NO3_uptake_rate', 0.0) / 1000.0,
        }

    def calculate_effective_surface_area(self, architecture_metrics: Dict[str, float]) -> float:
        # Get the actual surface areas by root type from the root architecture
        # The root architecture already properly calculates surface area from cohorts
        
        # Calculate surface area from root length using average diameters for each type
        fine_length = architecture_metrics.get('fine_root_length', 0)
        medium_length = architecture_metrics.get('medium_root_length', 0)
        coarse_length = architecture_metrics.get('coarse_root_length', 0)

        # Use correct diameter conversion: mean diameters from parameters are in mm, convert to cm
        fine_diameter_cm = self.root_architecture.params.fine_diameter_mean / 10.0  # 0.12mm -> 0.012cm
        medium_diameter_cm = self.root_architecture.params.medium_diameter_mean / 10.0  # 0.4mm -> 0.04cm
        coarse_diameter_cm = self.root_architecture.params.coarse_diameter_mean / 10.0  # 1.2mm -> 0.12cm

        fine_area = fine_length * math.pi * fine_diameter_cm
        medium_area = medium_length * math.pi * medium_diameter_cm
        coarse_area = coarse_length * math.pi * coarse_diameter_cm

        effective_area = (
            fine_area * self.uptake_params.fine_root_effectiveness +
            medium_area * self.uptake_params.medium_root_effectiveness +
            coarse_area * self.uptake_params.coarse_root_effectiveness
        )
        
        # Fallback: if architecture-based calculation fails, use total surface area as proxy
        if effective_area < 1e-6:
            total_surface = architecture_metrics.get('total_root_surface_area', 0)
            effective_area = total_surface * 0.7  # Assume 70% effectiveness
            
        return effective_area

    def calculate_temperature_factor(self, temperature: float) -> float:
        temp_diff = temperature - self.uptake_params.optimal_temperature
        factor = self.uptake_params.q10_factor ** (temp_diff / 10.0)
        return max(0.1, min(4.0, factor))

    def calculate_flow_factor(self, flow_rate: float) -> float:
        optimal_flow = self.uptake_params.optimal_flow_rate
        if flow_rate < 0.5:
            return 0.4
        elif flow_rate > self.uptake_params.flow_stress_threshold:
            return 0.6
        else:
            normalized_flow = flow_rate / optimal_flow
            return min(1.0, 0.5 + 0.5 * normalized_flow)

    def get_spatial_uptake_distribution(self) -> Dict[str, Dict[str, float]]:
        root_distribution = self.root_architecture.get_root_distribution()
        spatial_uptake: Dict[str, Dict[str, float]] = {}
        for zone_name, zone_data in root_distribution.items():
            zone_surface_area = zone_data['root_surface_area']
            zone_uptake: Dict[str, float] = {}
            for nutrient, base_rate in self.uptake_params.base_uptake_rates.items():
                zone_uptake[f'{nutrient}_capacity'] = zone_surface_area * base_rate
            zone_uptake['total_surface_area'] = zone_surface_area
            zone_uptake['total_capacity'] = sum(
                v for k, v in zone_uptake.items() if k.endswith('_capacity')
            )
            spatial_uptake[zone_name] = zone_uptake
        return spatial_uptake
    
    def _calculate_nutrient_competition(self, target_nutrient: str, 
                                       concentrations: Dict[str, float]) -> float:
        """
        Calculate competitive inhibition between nutrients.
        Similar nutrients compete for the same transport proteins.
        """
        # Define nutrient competition groups
        competition_groups = {
            'N-NO3': ['N-NO3', 'Cl'],  # Nitrate competes with chloride
            'N-NH4': ['N-NH4', 'K'],   # Ammonium competes with potassium  
            'P-PO4': ['P-PO4'],        # Phosphate has unique transporters
            'K': ['K', 'N-NH4'],       # Potassium competes with ammonium
            'Ca': ['Ca', 'Mg'],        # Calcium competes with magnesium
            'Mg': ['Mg', 'Ca']         # Magnesium competes with calcium
        }
        
        if target_nutrient not in competition_groups:
            return 1.0  # No competition
        
        competitors = competition_groups[target_nutrient]
        target_conc = concentrations.get(target_nutrient, 0.0)
        
        # Calculate competitive inhibition using classical enzyme kinetics
        total_competitor_conc = 0.0
        for competitor in competitors:
            if competitor != target_nutrient and competitor in concentrations:
                # Ki (inhibition constant) typically similar to Km
                ki = 50.0  # mg/L
                competitor_effect = concentrations[competitor] / ki
                total_competitor_conc += competitor_effect
        
        # Competitive inhibition factor: 1 / (1 + [I]/Ki)
        inhibition_factor = 1.0 / (1.0 + total_competitor_conc)
        
        return max(0.1, inhibition_factor)  # Minimum 10% activity
    
    def _calculate_ph_effect_on_uptake(self, nutrient: str, ph: float) -> float:
        """
        Calculate pH effects on nutrient speciation and transport protein activity.
        """
        # Optimal pH ranges for different nutrients
        ph_optima = {
            'N-NO3': (5.5, 7.0),   # Nitrate uptake optimal at slightly acidic
            'N-NH4': (5.0, 6.5),   # Ammonium prefers acidic conditions
            'P-PO4': (5.5, 6.5),   # Phosphate availability peaks at acidic pH
            'K': (5.5, 7.5),       # Potassium relatively pH insensitive
            'Ca': (6.0, 7.5),      # Calcium prefers neutral to slightly basic
            'Mg': (6.0, 7.5)       # Magnesium similar to calcium
        }
        
        if nutrient not in ph_optima:
            return 1.0
        
        optimal_min, optimal_max = ph_optima[nutrient]
        
        if optimal_min <= ph <= optimal_max:
            return 1.0  # Optimal pH range
        elif ph < optimal_min:
            # Too acidic - calculate linear decline
            stress_range = 2.0  # pH units below optimum before severe stress
            ph_stress = max(0.0, (optimal_min - ph) / stress_range)
            return max(0.2, 1.0 - ph_stress)
        else:  # ph > optimal_max
            # Too basic - calculate linear decline
            stress_range = 2.5  # pH units above optimum before severe stress
            ph_stress = max(0.0, (ph - optimal_max) / stress_range)
            return max(0.2, 1.0 - ph_stress)
    
    def _calculate_root_age_effect(self, architecture_metrics: Dict[str, float]) -> float:
        """
        Calculate effect of root age on transporter density.
        Young roots have higher transporter density than old roots.
        """
        # Assume fine roots are younger and more active
        fine_root_fraction = architecture_metrics.get('fine_root_fraction', 0.7)
        
        # Age distribution effect: young roots are 2x more active than old
        young_root_activity = 2.0
        old_root_activity = 0.8
        
        # Weighted average based on root age distribution
        weighted_activity = (fine_root_fraction * young_root_activity + 
                           (1.0 - fine_root_fraction) * old_root_activity)
        
        return max(0.1, weighted_activity)  # Natural root activity without caps
    

    def optimize_environmental_conditions(self,
                                          target_uptake_rates: Dict[str, float],
                                          current_concentrations: Dict[str, float]) -> Dict[str, float]:
        current_metrics = self.root_architecture.calculate_architecture_metrics()
        best_conditions = {'temperature': 20.0, 'flow_rate': 1.5}
        best_score = 0.0
        for temp in [16, 18, 20, 22, 24, 26]:
            for flow in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
                temp_factor = self.calculate_temperature_factor(temp)
                flow_factor = self.calculate_flow_factor(flow)
                score = 0.0
                for nutrient, target_rate in target_uptake_rates.items():
                    if nutrient in self.uptake_params.base_uptake_rates:
                        base_rate = self.uptake_params.base_uptake_rates[nutrient]
                        concentration = current_concentrations.get(nutrient, 100.0)
                        predicted_uptake = (
                            current_metrics['total_root_surface_area'] *
                            base_rate * temp_factor * flow_factor *
                            (concentration / (concentration + 50.0))
                        )
                        error = abs(predicted_uptake - target_rate)
                        score += 1.0 / (1.0 + error / max(1e-6, target_rate))
                if score > best_score:
                    best_score = score
                    best_conditions = {'temperature': temp, 'flow_rate': flow}
        return {
            **best_conditions,
            'optimization_score': best_score,
            'predicted_improvement': (best_score / max(1, len(target_uptake_rates))) * 100.0,
        }


def create_enhanced_root_uptake_model(system_type: HydroponicSystemType = HydroponicSystemType.NFT,
                                      tank_volume: float = 1500.0) -> EnhancedRootUptakeModel:
    return EnhancedRootUptakeModel(system_type, tank_volume)


# =========================
# Demonstration
# =========================

if __name__ == "__main__":
    print("Unified Root System Model - Demonstration")
    print("=" * 80)

    # 1) Root Architecture quick run
    arch = create_lettuce_root_architecture_model(HydroponicSystemType.NFT)
    metrics = arch.daily_update({'temperature': 20.0, 'flow_rate': 1.5, 'oxygen_level': 8.0},
                                {'nitrogen_stress': 0.9, 'water_stress': 0.95, 'temperature_stress': 0.9})
    print(f"Root length: {metrics['total_root_length']:.1f} cm, surface: {metrics['total_root_surface_area']:.0f} cm²")

    # 2) Enhanced uptake quick run
    model = create_enhanced_root_uptake_model(HydroponicSystemType.NFT)
    results = model.daily_update(
        {'temperature': 22.0, 'flow_rate': 1.5, 'oxygen_level': 8.0},
        {'nitrogen_stress': 0.95, 'water_stress': 0.95, 'temperature_stress': 0.95},
        {'NO3': 6.0, 'K': 120.0}
    )
    print(f"NO3 uptake: {results.get('NO3_uptake_rate', 0.0):.2f} mg/day, total: {results.get('total_nutrient_uptake', 0.0):.2f} mg/day")

    # 3) Hydroponic root dynamics utilities
    hrm = HydroponicRootModel(HydroponicSystemType.NFT)
    sample_roots = HydroponicRootSystem(
        total_root_mass=10.0,
        total_root_length=6000.0,
        root_surface_area=2500.0,
        specific_root_length=600.0,
        root_diameter=0.02,
        solution_root_fraction=0.6,
        media_root_fraction=0.2,
        air_root_fraction=0.2,
        primary_zone_roots=6.0,
        secondary_zone_roots=4.0,
        feeder_root_density=5.0,
        root_growth_rate=0.8,
        root_senescence_rate=0.03,
        uptake_efficiency=0.85,
        system_type=HydroponicSystemType.NFT,
    )
    capacity = hrm.calculate_nutrient_uptake_capacity(sample_roots, solution_volume=50.0)
    print(f"Capacity: {capacity:.1f} mg/day, Health: {hrm._calculate_health_score(sample_roots):.1f}")
