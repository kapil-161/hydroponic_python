"""
Nutrient Mobility Model for Hydroponic Crop Simulation
Based on CROPGRO nutrient transport and plant physiology research

Key concepts implemented:
1. Phloem and xylem transport mechanisms
2. Nutrient-specific mobility characteristics
3. Source-sink relationships for nutrient allocation
4. Nutrient buffering and storage pools
5. Redistribution during stress and senescence
6. Integration with plant hydraulics

Research basis:
- Marschner (2012) - Mineral nutrition of higher plants
- White & Brown (2010) - Plant nutrition for sustainable development
- Hocking (1994) - The physiology of plants under stress
- Waters & Sankaran (2011) - Moving micronutrients from the soil to the seeds
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import math


class NutrientMobility(Enum):
    """Nutrient mobility classifications."""
    HIGHLY_MOBILE = "highly_mobile"       # N, P, K, Mg, Cl
    MODERATELY_MOBILE = "moderately_mobile"  # S, Fe, Zn, Mn
    POORLY_MOBILE = "poorly_mobile"       # Ca, B, Mo
    IMMOBILE = "immobile"                 # Some forms of Fe, Ca


class TransportMechanism(Enum):
    """Nutrient transport mechanisms."""
    XYLEM_ONLY = "xylem_only"             # Ca, B, Mo - upward only
    PHLOEM_ONLY = "phloem_only"           # Some organic compounds
    BIDIRECTIONAL = "bidirectional"       # N, P, K, Mg - both directions
    COMPLEX = "complex"                   # Fe, Zn, Mn - multiple forms


@dataclass
class NutrientMobilityParameters:
    """Parameters for nutrient mobility model."""
    
    # Nutrient-specific mobility characteristics
    mobility_classifications: Dict[str, Dict[str, Any]] = None
    
    # Transport rates (fraction/day)
    xylem_transport_rates: Dict[str, float] = None
    phloem_transport_rates: Dict[str, float] = None
    
    # Buffering and storage
    buffering_capacities: Dict[str, Dict[str, float]] = None
    storage_pool_sizes: Dict[str, Dict[str, float]] = None
    
    # Redistribution parameters
    redistribution_thresholds: Dict[str, float] = None
    stress_redistribution_rates: Dict[str, float] = None
    
    # Source-sink relationships
    sink_strength_coefficients: Dict[str, Dict[str, float]] = None
    
    # Transport limitations
    xylem_transport_capacity: float = 0.1     # g nutrient/g water/day
    phloem_transport_capacity: float = 0.05   # g nutrient/g assimilate/day
    
    # Environmental effects
    temperature_q10: float = 2.0              # Temperature effect on transport
    transpiration_coupling: float = 0.8       # Coupling with water transport
    
    def __post_init__(self):
        if self.mobility_classifications is None:
            # Default mobility characteristics for major nutrients
            self.mobility_classifications = {
                'nitrogen': {
                    'mobility': NutrientMobility.HIGHLY_MOBILE.value,
                    'transport': TransportMechanism.BIDIRECTIONAL.value,
                    'remobilization_efficiency': 0.80,
                    'deficiency_mobility': 'high',
                    'retranslocation_rate': 0.15
                },
                'phosphorus': {
                    'mobility': NutrientMobility.HIGHLY_MOBILE.value,
                    'transport': TransportMechanism.BIDIRECTIONAL.value,
                    'remobilization_efficiency': 0.70,
                    'deficiency_mobility': 'high',
                    'retranslocation_rate': 0.12
                },
                'potassium': {
                    'mobility': NutrientMobility.HIGHLY_MOBILE.value,
                    'transport': TransportMechanism.BIDIRECTIONAL.value,
                    'remobilization_efficiency': 0.85,
                    'deficiency_mobility': 'very_high',
                    'retranslocation_rate': 0.20
                },
                'calcium': {
                    'mobility': NutrientMobility.POORLY_MOBILE.value,
                    'transport': TransportMechanism.XYLEM_ONLY.value,
                    'remobilization_efficiency': 0.05,
                    'deficiency_mobility': 'very_low',
                    'retranslocation_rate': 0.01
                },
                'magnesium': {
                    'mobility': NutrientMobility.MODERATELY_MOBILE.value,
                    'transport': TransportMechanism.BIDIRECTIONAL.value,
                    'remobilization_efficiency': 0.45,
                    'deficiency_mobility': 'moderate',
                    'retranslocation_rate': 0.08
                },
                'sulfur': {
                    'mobility': NutrientMobility.MODERATELY_MOBILE.value,
                    'transport': TransportMechanism.BIDIRECTIONAL.value,
                    'remobilization_efficiency': 0.60,
                    'deficiency_mobility': 'moderate',
                    'retranslocation_rate': 0.10
                },
                'iron': {
                    'mobility': NutrientMobility.POORLY_MOBILE.value,
                    'transport': TransportMechanism.COMPLEX.value,
                    'remobilization_efficiency': 0.15,
                    'deficiency_mobility': 'low',
                    'retranslocation_rate': 0.03
                },
                'manganese': {
                    'mobility': NutrientMobility.MODERATELY_MOBILE.value,
                    'transport': TransportMechanism.COMPLEX.value,
                    'remobilization_efficiency': 0.35,
                    'deficiency_mobility': 'moderate',
                    'retranslocation_rate': 0.06
                },
                'zinc': {
                    'mobility': NutrientMobility.MODERATELY_MOBILE.value,
                    'transport': TransportMechanism.COMPLEX.value,
                    'remobilization_efficiency': 0.40,
                    'deficiency_mobility': 'moderate',
                    'retranslocation_rate': 0.07
                },
                'copper': {
                    'mobility': NutrientMobility.MODERATELY_MOBILE.value,
                    'transport': TransportMechanism.COMPLEX.value,
                    'remobilization_efficiency': 0.25,
                    'deficiency_mobility': 'low',
                    'retranslocation_rate': 0.04
                },
                'boron': {
                    'mobility': NutrientMobility.POORLY_MOBILE.value,
                    'transport': TransportMechanism.XYLEM_ONLY.value,
                    'remobilization_efficiency': 0.08,
                    'deficiency_mobility': 'very_low',
                    'retranslocation_rate': 0.01
                },
                'molybdenum': {
                    'mobility': NutrientMobility.MODERATELY_MOBILE.value,
                    'transport': TransportMechanism.BIDIRECTIONAL.value,
                    'remobilization_efficiency': 0.50,
                    'deficiency_mobility': 'moderate',
                    'retranslocation_rate': 0.09
                }
            }
        
        if self.xylem_transport_rates is None:
            # Transport rates in xylem (fraction of pool/day)
            self.xylem_transport_rates = {
                'nitrogen': 0.25,      # Fast transport
                'phosphorus': 0.15,    # Moderate transport
                'potassium': 0.30,     # Very fast transport
                'calcium': 0.20,       # Moderate (only upward)
                'magnesium': 0.18,     # Moderate transport
                'sulfur': 0.12,        # Moderate transport
                'iron': 0.08,          # Slow transport
                'manganese': 0.10,     # Moderate transport
                'zinc': 0.10,          # Moderate transport
                'copper': 0.08,        # Slow transport
                'boron': 0.15,         # Moderate (only upward)
                'molybdenum': 0.12     # Moderate transport
            }
        
        if self.phloem_transport_rates is None:
            # Transport rates in phloem (fraction of pool/day)
            self.phloem_transport_rates = {
                'nitrogen': 0.20,      # High transport
                'phosphorus': 0.18,    # High transport
                'potassium': 0.25,     # Very high transport
                'calcium': 0.01,       # Very limited
                'magnesium': 0.12,     # Moderate transport
                'sulfur': 0.15,        # Moderate transport
                'iron': 0.05,          # Limited transport
                'manganese': 0.08,     # Limited transport
                'zinc': 0.10,          # Moderate transport
                'copper': 0.06,        # Limited transport
                'boron': 0.02,         # Very limited
                'molybdenum': 0.12     # Moderate transport
            }
        
        if self.buffering_capacities is None:
            # Buffering capacity by organ (fraction of total content)
            self.buffering_capacities = {
                'leaves': {'nitrogen': 0.30, 'phosphorus': 0.25, 'potassium': 0.35},
                'stems': {'nitrogen': 0.20, 'phosphorus': 0.15, 'potassium': 0.25},
                'roots': {'nitrogen': 0.15, 'phosphorus': 0.20, 'potassium': 0.20}
            }
        
        if self.storage_pool_sizes is None:
            # Storage pool sizes relative to metabolic pools
            self.storage_pool_sizes = {
                'leaves': {'nitrogen': 0.40, 'phosphorus': 0.30, 'potassium': 0.50},
                'stems': {'nitrogen': 0.60, 'phosphorus': 0.50, 'potassium': 0.70},
                'roots': {'nitrogen': 0.35, 'phosphorus': 0.40, 'potassium': 0.45}
            }
        
        if self.redistribution_thresholds is None:
            # Stress thresholds that trigger redistribution
            self.redistribution_thresholds = {
                'nitrogen': 0.7,       # Below 70% optimal triggers redistribution
                'phosphorus': 0.6,     # Below 60% optimal
                'potassium': 0.8,      # Below 80% optimal
                'calcium': 0.4,        # Below 40% optimal (limited mobility)
                'magnesium': 0.6,      # Below 60% optimal
                'sulfur': 0.6,         # Below 60% optimal
            }
        
        if self.stress_redistribution_rates is None:
            # Enhanced redistribution rates under stress
            self.stress_redistribution_rates = {
                'nitrogen': 0.30,      # 30% increase under stress
                'phosphorus': 0.25,    # 25% increase
                'potassium': 0.40,     # 40% increase
                'magnesium': 0.20,     # 20% increase
                'sulfur': 0.25,        # 25% increase
            }
        
        if self.sink_strength_coefficients is None:
            # Sink strength for different organs and growth stages
            self.sink_strength_coefficients = {
                'vegetative': {
                    'leaves': 0.50,      # Strong sink during vegetative growth
                    'stems': 0.25,       # Moderate sink
                    'roots': 0.25        # Moderate sink
                },
                'reproductive': {
                    'leaves': 0.30,      # Reduced sink
                    'stems': 0.20,       # Reduced sink
                    'roots': 0.15,       # Reduced sink
                    'reproductive': 0.35  # Strong sink for reproductive organs
                },
                'senescence': {
                    'leaves': 0.10,      # Weak sink (source)
                    'stems': 0.30,       # Storage sink
                    'roots': 0.25,       # Maintenance sink
                    'reproductive': 0.35  # Priority sink
                }
            }
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'NutrientMobilityParameters':
        """Create NutrientMobilityParameters from configuration dictionary."""
        mobility_class = config_dict.get('mobility_classifications', {})
        xylem_rates = config_dict.get('xylem_transport_rates', {})
        phloem_rates = config_dict.get('phloem_transport_rates', {})
        buffering_cap = config_dict.get('buffering_capacities', {})
        storage_sizes = config_dict.get('storage_pool_sizes', {})
        redist_thresh = config_dict.get('redistribution_thresholds', {})
        stress_redist = config_dict.get('stress_redistribution_rates', {})
        sink_coeffs = config_dict.get('sink_strength_coefficients', {})
        
        return cls(
            mobility_classifications=mobility_class if mobility_class else None,
            xylem_transport_rates=xylem_rates if xylem_rates else None,
            phloem_transport_rates=phloem_rates if phloem_rates else None,
            buffering_capacities=buffering_cap if buffering_cap else None,
            storage_pool_sizes=storage_sizes if storage_sizes else None,
            redistribution_thresholds=redist_thresh if redist_thresh else None,
            stress_redistribution_rates=stress_redist if stress_redist else None,
            sink_strength_coefficients=sink_coeffs if sink_coeffs else None,
            xylem_transport_capacity=config_dict.get('xylem_transport_capacity', 0.1),
            phloem_transport_capacity=config_dict.get('phloem_transport_capacity', 0.05),
            temperature_q10=config_dict.get('temperature_q10', 2.0),
            transpiration_coupling=config_dict.get('transpiration_coupling', 0.8)
        )


@dataclass
class NutrientTransportFlux:
    """Nutrient transport flux between organs."""
    source_organ: str
    sink_organ: str
    nutrient: str
    transport_mechanism: str
    flux_rate: float                    # g nutrient/day
    driving_force: str                  # 'concentration', 'demand', 'stress'
    efficiency: float                   # Transport efficiency (0-1)


@dataclass
class OrganNutrientPools:
    """Nutrient pools within an organ."""
    organ_name: str
    nutrient_name: str
    
    # Pool sizes (g nutrient)
    metabolic_pool: float = 0.0         # Active metabolic pool
    storage_pool: float = 0.0           # Storage pool
    transport_pool: float = 0.0         # In transit
    buffer_pool: float = 0.0            # Buffering pool
    
    # Pool characteristics
    total_content: float = 0.0          # Total nutrient content
    concentration: float = 0.0          # g nutrient/g dry mass
    mobility_status: str = "optimal"    # optimal, limiting, excess
    
    # Transport properties
    available_for_export: float = 0.0   # Available for transport out
    demand_for_import: float = 0.0      # Demand for transport in
    buffering_capacity: float = 0.0     # Current buffering capacity
    
    def __post_init__(self):
        self.total_content = (self.metabolic_pool + self.storage_pool + 
                            self.transport_pool + self.buffer_pool)


@dataclass
class NutrientMobilityResponse:
    """Daily nutrient mobility calculation results."""
    transport_fluxes: List[NutrientTransportFlux]
    organ_pools: Dict[str, Dict[str, OrganNutrientPools]]  # [organ][nutrient]
    total_redistribution: Dict[str, float]      # Total redistributed by nutrient
    transport_limitations: List[str]            # Limiting factors
    sink_demands: Dict[str, Dict[str, float]]   # [organ][nutrient] demands
    source_supplies: Dict[str, Dict[str, float]] # [organ][nutrient] supplies
    mobility_efficiency: Dict[str, float]       # Overall mobility efficiency by nutrient


class NutrientMobilityModel:
    """
    Comprehensive nutrient mobility model following CROPGRO principles.
    
    Models nutrient transport, redistribution, and buffering throughout
    the plant system with nutrient-specific characteristics.
    """
    
    def __init__(self, parameters: Optional[NutrientMobilityParameters] = None):
        self.params = parameters or NutrientMobilityParameters()
        self.organ_pools: Dict[str, Dict[str, OrganNutrientPools]] = {}
        self.transport_history: List[Dict[str, Any]] = []
        self.cumulative_redistribution: Dict[str, float] = {}
        
    def initialize_organ_pools(self, organ_name: str, 
                             nutrient_contents: Dict[str, float],
                             dry_mass: float):
        """
        Initialize nutrient pools for an organ.
        
        Args:
            organ_name: Name of the organ
            nutrient_contents: Total nutrient contents by nutrient (g)
            dry_mass: Organ dry mass (g)
        """
        if organ_name not in self.organ_pools:
            self.organ_pools[organ_name] = {}
        
        for nutrient, total_content in nutrient_contents.items():
            if nutrient in self.params.mobility_classifications:
                # Distribute total content among pools
                storage_fraction = self.params.storage_pool_sizes.get(organ_name, {}).get(nutrient, 0.3)
                buffer_fraction = self.params.buffering_capacities.get(organ_name, {}).get(nutrient, 0.2)
                
                storage_pool = total_content * storage_fraction
                buffer_pool = total_content * buffer_fraction
                transport_pool = total_content * 0.05  # 5% in transport
                metabolic_pool = total_content - storage_pool - buffer_pool - transport_pool
                
                # Create nutrient pool
                pool = OrganNutrientPools(
                    organ_name=organ_name,
                    nutrient_name=nutrient,
                    metabolic_pool=max(0.0, metabolic_pool),
                    storage_pool=storage_pool,
                    transport_pool=transport_pool,
                    buffer_pool=buffer_pool,
                    total_content=total_content,
                    concentration=total_content / max(dry_mass, 0.001),
                    buffering_capacity=buffer_pool
                )
                
                self.organ_pools[organ_name][nutrient] = pool
        
        # Initialize cumulative tracking
        for nutrient in nutrient_contents.keys():
            if nutrient not in self.cumulative_redistribution:
                self.cumulative_redistribution[nutrient] = 0.0
    
    def calculate_transport_capacity(self, source_organ: str, sink_organ: str,
                                   water_flux: float, assimilate_flux: float,
                                   temperature: float) -> Dict[str, float]:
        """
        Calculate transport capacity between organs.
        
        Args:
            source_organ: Source organ name
            sink_organ: Sink organ name
            water_flux: Water flux rate (g water/day)
            assimilate_flux: Assimilate flux rate (g/day)
            temperature: Temperature (°C)
            
        Returns:
            Transport capacity by mechanism (g nutrient/day)
        """
        # Temperature effect on transport
        temp_factor = self.params.temperature_q10 ** ((temperature - 25.0) / 10.0)
        temp_factor = max(0.5, min(2.0, temp_factor))  # Limit range
        
        # Xylem transport capacity (coupled with water flow)
        xylem_capacity = (water_flux * self.params.xylem_transport_capacity * 
                         self.params.transpiration_coupling * temp_factor)
        
        # Phloem transport capacity (coupled with assimilate flow)
        phloem_capacity = (assimilate_flux * self.params.phloem_transport_capacity * 
                          temp_factor)
        
        return {
            'xylem': xylem_capacity,
            'phloem': phloem_capacity
        }
    
    def calculate_sink_demands(self, organ_demands: Dict[str, Dict[str, float]],
                             growth_stage: str) -> Dict[str, Dict[str, float]]:
        """
        Calculate nutrient demands for each organ based on sink strength.
        
        Args:
            organ_demands: Raw nutrient demands by organ and nutrient
            growth_stage: Current growth stage
            
        Returns:
            Adjusted demands based on sink strength
        """
        adjusted_demands = {}
        
        # Get sink strength coefficients for current stage
        if growth_stage in self.params.sink_strength_coefficients:
            sink_coeffs = self.params.sink_strength_coefficients[growth_stage]
        else:
            sink_coeffs = self.params.sink_strength_coefficients['vegetative']
        
        for organ_name, demands in organ_demands.items():
            adjusted_demands[organ_name] = {}
            
            organ_sink_strength = sink_coeffs.get(organ_name, 0.25)
            
            for nutrient, demand in demands.items():
                # Adjust demand based on sink strength
                adjusted_demand = demand * organ_sink_strength
                
                # Further adjust based on nutrient mobility
                if nutrient in self.params.mobility_classifications:
                    mobility_info = self.params.mobility_classifications[nutrient]
                    if mobility_info['deficiency_mobility'] == 'very_high':
                        adjusted_demand *= 1.2
                    elif mobility_info['deficiency_mobility'] == 'high':
                        adjusted_demand *= 1.1
                    elif mobility_info['deficiency_mobility'] == 'low':
                        adjusted_demand *= 0.8
                    elif mobility_info['deficiency_mobility'] == 'very_low':
                        adjusted_demand *= 0.6
                
                adjusted_demands[organ_name][nutrient] = adjusted_demand
        
        return adjusted_demands
    
    def calculate_source_supplies(self, stress_factors: Dict[str, float],
                                senescence_rates: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        Calculate nutrient supplies available from each organ.
        
        Args:
            stress_factors: Stress levels by type (0-1, 1=no stress)
            senescence_rates: Senescence rates by organ
            
        Returns:
            Available supplies by organ and nutrient
        """
        supplies = {}
        
        for organ_name, nutrient_pools in self.organ_pools.items():
            supplies[organ_name] = {}
            
            # Get organ-specific factors
            overall_stress = 1.0 - min(stress_factors.values()) if stress_factors else 0.0
            organ_senescence = senescence_rates.get(organ_name, 0.0)
            
            for nutrient, pool in nutrient_pools.items():
                if nutrient in self.params.mobility_classifications:
                    mobility_info = self.params.mobility_classifications[nutrient]
                    
                    # Base supply from storage and buffer pools
                    base_supply = pool.storage_pool * 0.1 + pool.buffer_pool * 0.05
                    
                    # Stress-induced supply
                    stress_supply = 0.0
                    if overall_stress > 0.3:  # Significant stress
                        stress_threshold = self.params.redistribution_thresholds.get(nutrient, 0.7)
                        if overall_stress > (1.0 - stress_threshold):
                            stress_rate = self.params.stress_redistribution_rates.get(nutrient, 0.2)
                            stress_supply = pool.storage_pool * stress_rate * overall_stress
                    
                    # Senescence-induced supply
                    senescence_supply = 0.0
                    if organ_senescence > 0.01:  # Active senescence
                        remob_efficiency = mobility_info['remobilization_efficiency']
                        senescence_supply = (pool.metabolic_pool * organ_senescence * 
                                           remob_efficiency)
                    
                    # Total available supply
                    total_supply = base_supply + stress_supply + senescence_supply
                    
                    # Limit by transport pool capacity
                    max_transportable = pool.total_content * 0.3  # Max 30% can be mobilized daily
                    total_supply = min(total_supply, max_transportable)
                    
                    supplies[organ_name][nutrient] = total_supply
                else:
                    supplies[organ_name][nutrient] = 0.0
        
        return supplies
    
    def calculate_transport_fluxes(self, sink_demands: Dict[str, Dict[str, float]],
                                 source_supplies: Dict[str, Dict[str, float]],
                                 transport_capacities: Dict[str, Dict[str, float]],
                                 temperature: float) -> List[NutrientTransportFlux]:
        """
        Calculate actual nutrient transport fluxes between organs.
        
        Args:
            sink_demands: Nutrient demands by organ and nutrient
            source_supplies: Available supplies by organ and nutrient
            transport_capacities: Transport capacities between organs
            temperature: Temperature (°C)
            
        Returns:
            List of transport fluxes
        """
        fluxes = []
        
        # Process each nutrient separately
        for nutrient in self.params.mobility_classifications:
            mobility_info = self.params.mobility_classifications[nutrient]
            transport_type = mobility_info['transport']
            
            # Get transport rates for this nutrient
            xylem_rate = self.params.xylem_transport_rates.get(nutrient, 0.1)
            phloem_rate = self.params.phloem_transport_rates.get(nutrient, 0.1)
            
            # Calculate total demand and supply for this nutrient
            total_demand = sum(demands.get(nutrient, 0.0) for demands in sink_demands.values())
            total_supply = sum(supplies.get(nutrient, 0.0) for supplies in source_supplies.values())
            
            if total_demand > 0 and total_supply > 0:
                # Determine transport efficiency
                supply_demand_ratio = total_supply / total_demand
                transport_efficiency = min(1.0, supply_demand_ratio)
                
                # Create fluxes from sources to sinks
                for source_organ, supplies in source_supplies.items():
                    if supplies.get(nutrient, 0.0) > 0:
                        source_supply = supplies[nutrient]
                        
                        for sink_organ, demands in sink_demands.items():
                            if (demands.get(nutrient, 0.0) > 0 and 
                                source_organ != sink_organ):
                                
                                sink_demand = demands[nutrient]
                                
                                # Calculate flux based on transport mechanism
                                if transport_type == TransportMechanism.XYLEM_ONLY.value:
                                    # Only upward transport (roots to shoots)
                                    if source_organ == 'roots':
                                        max_flux = source_supply * xylem_rate
                                        transport_cap = transport_capacities.get(source_organ, {}).get('xylem', 1.0)
                                        flux_rate = min(max_flux, sink_demand, transport_cap)
                                        mechanism = 'xylem'
                                    else:
                                        flux_rate = 0.0
                                        mechanism = 'none'
                                
                                elif transport_type == TransportMechanism.BIDIRECTIONAL.value:
                                    # Both xylem and phloem transport
                                    xylem_flux = source_supply * xylem_rate * 0.6  # 60% via xylem
                                    phloem_flux = source_supply * phloem_rate * 0.4  # 40% via phloem
                                    
                                    xylem_cap = transport_capacities.get(source_organ, {}).get('xylem', 1.0)
                                    phloem_cap = transport_capacities.get(source_organ, {}).get('phloem', 1.0)
                                    
                                    total_flux = min(xylem_flux + phloem_flux, sink_demand, 
                                                   xylem_cap + phloem_cap)
                                    flux_rate = total_flux
                                    mechanism = 'bidirectional'
                                
                                elif transport_type == TransportMechanism.COMPLEX.value:
                                    # Complex transport (depends on conditions)
                                    base_flux = source_supply * min(xylem_rate, phloem_rate)
                                    total_cap = (transport_capacities.get(source_organ, {}).get('xylem', 0.5) + 
                                               transport_capacities.get(source_organ, {}).get('phloem', 0.5))
                                    flux_rate = min(base_flux, sink_demand, total_cap)
                                    mechanism = 'complex'
                                
                                else:
                                    flux_rate = 0.0
                                    mechanism = 'none'
                                
                                # Apply transport efficiency
                                flux_rate *= transport_efficiency
                                
                                # Create flux if significant
                                if flux_rate > 0.001:  # Minimum threshold
                                    flux = NutrientTransportFlux(
                                        source_organ=source_organ,
                                        sink_organ=sink_organ,
                                        nutrient=nutrient,
                                        transport_mechanism=mechanism,
                                        flux_rate=flux_rate,
                                        driving_force='demand',
                                        efficiency=transport_efficiency
                                    )
                                    fluxes.append(flux)
        
        return fluxes
    
    def update_organ_pools(self, transport_fluxes: List[NutrientTransportFlux]):
        """
        Update organ nutrient pools based on transport fluxes.
        
        Args:
            transport_fluxes: List of nutrient transport fluxes
        """
        # Track net fluxes by organ and nutrient
        net_fluxes = {}
        
        # Calculate net fluxes
        for flux in transport_fluxes:
            # Initialize if needed
            if flux.source_organ not in net_fluxes:
                net_fluxes[flux.source_organ] = {}
            if flux.sink_organ not in net_fluxes:
                net_fluxes[flux.sink_organ] = {}
            
            if flux.nutrient not in net_fluxes[flux.source_organ]:
                net_fluxes[flux.source_organ][flux.nutrient] = 0.0
            if flux.nutrient not in net_fluxes[flux.sink_organ]:
                net_fluxes[flux.sink_organ][flux.nutrient] = 0.0
            
            # Source loses nutrient, sink gains nutrient
            net_fluxes[flux.source_organ][flux.nutrient] -= flux.flux_rate
            net_fluxes[flux.sink_organ][flux.nutrient] += flux.flux_rate
        
        # Apply net fluxes to organ pools
        for organ_name, nutrient_fluxes in net_fluxes.items():
            if organ_name in self.organ_pools:
                for nutrient, net_flux in nutrient_fluxes.items():
                    if nutrient in self.organ_pools[organ_name]:
                        pool = self.organ_pools[organ_name][nutrient]
                        
                        if net_flux < 0:  # Net outflow
                            # Remove from storage and transport pools first
                            outflow = abs(net_flux)
                            
                            # From transport pool
                            from_transport = min(outflow, pool.transport_pool)
                            pool.transport_pool -= from_transport
                            outflow -= from_transport
                            
                            # From storage pool
                            if outflow > 0:
                                from_storage = min(outflow, pool.storage_pool)
                                pool.storage_pool -= from_storage
                                outflow -= from_storage
                            
                            # From buffer pool if necessary
                            if outflow > 0:
                                from_buffer = min(outflow, pool.buffer_pool)
                                pool.buffer_pool -= from_buffer
                                outflow -= from_buffer
                            
                            # From metabolic pool as last resort
                            if outflow > 0:
                                from_metabolic = min(outflow, pool.metabolic_pool * 0.1)  # Max 10%
                                pool.metabolic_pool -= from_metabolic
                        
                        else:  # Net inflow
                            # Add to transport pool first, then distribute
                            pool.transport_pool += net_flux
                            
                            # Redistribute from transport pool to other pools
                            if pool.transport_pool > pool.total_content * 0.1:  # If >10% in transport
                                excess = pool.transport_pool - pool.total_content * 0.05
                                pool.transport_pool -= excess
                                
                                # Distribute excess
                                pool.metabolic_pool += excess * 0.6
                                pool.storage_pool += excess * 0.3
                                pool.buffer_pool += excess * 0.1
                        
                        # Update total content
                        pool.total_content = (pool.metabolic_pool + pool.storage_pool + 
                                           pool.transport_pool + pool.buffer_pool)
                        
                        # Update cumulative redistribution tracking
                        if nutrient in self.cumulative_redistribution:
                            self.cumulative_redistribution[nutrient] += abs(net_flux)
    
    def calculate_mobility_efficiency(self, nutrient: str) -> float:
        """
        Calculate overall mobility efficiency for a nutrient.
        
        Args:
            nutrient: Nutrient name
            
        Returns:
            Mobility efficiency (0-1)
        """
        if nutrient not in self.params.mobility_classifications:
            return 0.5
        
        mobility_info = self.params.mobility_classifications[nutrient]
        
        # Base efficiency from mobility classification
        mobility_class = mobility_info['mobility']
        if mobility_class == NutrientMobility.HIGHLY_MOBILE.value:
            base_efficiency = 0.8
        elif mobility_class == NutrientMobility.MODERATELY_MOBILE.value:
            base_efficiency = 0.6
        elif mobility_class == NutrientMobility.POORLY_MOBILE.value:
            base_efficiency = 0.3
        else:  # IMMOBILE
            base_efficiency = 0.1
        
        # Adjust for transport mechanism
        transport_type = mobility_info['transport']
        if transport_type == TransportMechanism.BIDIRECTIONAL.value:
            transport_factor = 1.2
        elif transport_type == TransportMechanism.COMPLEX.value:
            transport_factor = 0.9
        elif transport_type == TransportMechanism.XYLEM_ONLY.value:
            transport_factor = 0.7
        else:
            transport_factor = 1.0
        
        return min(1.0, base_efficiency * transport_factor)
    
    def daily_update(self, organ_demands: Dict[str, Dict[str, float]],
                    stress_factors: Dict[str, float],
                    senescence_rates: Dict[str, float],
                    growth_stage: str,
                    water_fluxes: Dict[str, float],
                    assimilate_fluxes: Dict[str, float],
                    temperature: float) -> NutrientMobilityResponse:
        """
        Daily nutrient mobility update.
        
        Args:
            organ_demands: Nutrient demands by organ and nutrient
            stress_factors: Stress levels by type
            senescence_rates: Senescence rates by organ
            growth_stage: Current growth stage
            water_fluxes: Water flux rates between organs
            assimilate_fluxes: Assimilate flux rates between organs
            temperature: Temperature (°C)
            
        Returns:
            Complete nutrient mobility response
        """
        # Calculate sink demands based on growth stage
        sink_demands = self.calculate_sink_demands(organ_demands, growth_stage)
        
        # Calculate source supplies based on stress and senescence
        source_supplies = self.calculate_source_supplies(stress_factors, senescence_rates)
        
        # Calculate transport capacities
        transport_capacities = {}
        for organ in self.organ_pools.keys():
            water_flux = water_fluxes.get(organ, 0.1)
            assimilate_flux = assimilate_fluxes.get(organ, 0.05)
            transport_capacities[organ] = self.calculate_transport_capacity(
                organ, 'sink', water_flux, assimilate_flux, temperature
            )
        
        # Calculate transport fluxes
        transport_fluxes = self.calculate_transport_fluxes(
            sink_demands, source_supplies, transport_capacities, temperature
        )
        
        # Update organ pools
        self.update_organ_pools(transport_fluxes)
        
        # Calculate total redistribution by nutrient
        total_redistribution = {}
        for flux in transport_fluxes:
            if flux.nutrient not in total_redistribution:
                total_redistribution[flux.nutrient] = 0.0
            total_redistribution[flux.nutrient] += flux.flux_rate
        
        # Identify transport limitations
        limitations = []
        for nutrient in self.params.mobility_classifications:
            total_demand = sum(demands.get(nutrient, 0.0) for demands in sink_demands.values())
            total_flux = total_redistribution.get(nutrient, 0.0)
            
            if total_demand > 0 and total_flux < total_demand * 0.8:
                limitations.append(f'{nutrient}_transport_limited')
        
        # Calculate mobility efficiency by nutrient
        mobility_efficiency = {}
        for nutrient in self.params.mobility_classifications:
            mobility_efficiency[nutrient] = self.calculate_mobility_efficiency(nutrient)
        
        # Store daily record
        daily_record = {
            'total_redistribution': sum(total_redistribution.values()),
            'transport_fluxes': len(transport_fluxes),
            'limitations': len(limitations)
        }
        self.transport_history.append(daily_record)
        
        return NutrientMobilityResponse(
            transport_fluxes=transport_fluxes,
            organ_pools=self.organ_pools.copy(),
            total_redistribution=total_redistribution,
            transport_limitations=limitations,
            sink_demands=sink_demands,
            source_supplies=source_supplies,
            mobility_efficiency=mobility_efficiency
        )
    
    def get_mobility_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive nutrient mobility summary.
        
        Returns:
            Dictionary with mobility summary
        """
        total_nutrients = {}
        transport_pools = {}
        
        for organ_name, nutrient_pools in self.organ_pools.items():
            for nutrient, pool in nutrient_pools.items():
                if nutrient not in total_nutrients:
                    total_nutrients[nutrient] = 0.0
                    transport_pools[nutrient] = 0.0
                
                total_nutrients[nutrient] += pool.total_content
                transport_pools[nutrient] += pool.transport_pool
        
        # Calculate transport pool fractions
        transport_fractions = {}
        for nutrient in total_nutrients:
            if total_nutrients[nutrient] > 0:
                transport_fractions[nutrient] = transport_pools[nutrient] / total_nutrients[nutrient]
            else:
                transport_fractions[nutrient] = 0.0
        
        summary = {
            'total_nutrients': total_nutrients,
            'transport_pool_fractions': transport_fractions,
            'cumulative_redistribution': self.cumulative_redistribution.copy(),
            'mobility_classifications': {
                nutrient: info['mobility'] 
                for nutrient, info in self.params.mobility_classifications.items()
            },
            'transport_mechanisms': {
                nutrient: info['transport']
                for nutrient, info in self.params.mobility_classifications.items()
            }
        }
        
        return summary


def create_lettuce_nutrient_mobility_model() -> NutrientMobilityModel:
    """Create nutrient mobility model with lettuce-specific parameters."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        mobility_config = config_loader.get_nutrient_mobility_parameters()
        parameters = NutrientMobilityParameters.from_config(mobility_config)
        return NutrientMobilityModel(parameters)
    except ImportError:
        # Fallback to default values if config loader not available
        return NutrientMobilityModel()


def demonstrate_nutrient_mobility_model():
    """Demonstrate nutrient mobility model capabilities."""
    model = create_lettuce_nutrient_mobility_model()
    
    print("=" * 80)
    print("NUTRIENT MOBILITY MODEL DEMONSTRATION")
    print("=" * 80)
    
    # Initialize organ pools
    nutrient_contents = {
        'nitrogen': 0.12,    # 12% of total plant N
        'phosphorus': 0.015, # 1.5% of total plant P
        'potassium': 0.10,   # 10% of total plant K
        'calcium': 0.05,     # 5% of total plant Ca
        'magnesium': 0.02    # 2% of total plant Mg
    }
    
    model.initialize_organ_pools('leaves', nutrient_contents, 4.0)
    model.initialize_organ_pools('stems', {k: v*0.4 for k, v in nutrient_contents.items()}, 1.5)
    model.initialize_organ_pools('roots', {k: v*0.6 for k, v in nutrient_contents.items()}, 2.5)
    
    print("Initial nutrient distribution:")
    for organ in ['leaves', 'stems', 'roots']:
        print(f"  {organ}:")
        if organ in model.organ_pools:
            for nutrient, pool in model.organ_pools[organ].items():
                print(f"    {nutrient}: {pool.total_content:.3f}g (Met: {pool.metabolic_pool:.3f}, "
                      f"Stor: {pool.storage_pool:.3f}, Buf: {pool.buffer_pool:.3f})")
    
    # Simulate mobility responses under different scenarios
    print(f"\nTesting mobility scenarios:")
    print(f"{'Scenario':<20} {'N_Redist':<9} {'P_Redist':<9} {'K_Redist':<9} {'Limits':<8}")
    print("-" * 80)
    
    scenarios = [
        ("Normal growth", 
         {'leaves': {'nitrogen': 0.02, 'phosphorus': 0.003, 'potassium': 0.015},
          'stems': {'nitrogen': 0.01, 'phosphorus': 0.001, 'potassium': 0.008},
          'roots': {'nitrogen': 0.015, 'phosphorus': 0.002, 'potassium': 0.012}},
         {'water': 0.9, 'temperature': 0.9, 'light': 0.9},
         {'leaves': 0.0, 'stems': 0.0, 'roots': 0.0}),
        
        ("N deficiency stress",
         {'leaves': {'nitrogen': 0.035, 'phosphorus': 0.002, 'potassium': 0.010},
          'stems': {'nitrogen': 0.020, 'phosphorus': 0.001, 'potassium': 0.005},
          'roots': {'nitrogen': 0.025, 'phosphorus': 0.001, 'potassium': 0.008}},
         {'water': 0.9, 'nitrogen': 0.5, 'temperature': 0.9, 'light': 0.9},
         {'leaves': 0.0, 'stems': 0.0, 'roots': 0.0}),
        
        ("Senescence onset",
         {'leaves': {'nitrogen': 0.010, 'phosphorus': 0.001, 'potassium': 0.005},
          'stems': {'nitrogen': 0.008, 'phosphorus': 0.001, 'potassium': 0.004},
          'roots': {'nitrogen': 0.012, 'phosphorus': 0.001, 'potassium': 0.006}},
         {'water': 0.8, 'temperature': 0.8, 'light': 0.7},
         {'leaves': 0.05, 'stems': 0.02, 'roots': 0.01}),
        
        ("Multi-stress",
         {'leaves': {'nitrogen': 0.025, 'phosphorus': 0.004, 'potassium': 0.020},
          'stems': {'nitrogen': 0.015, 'phosphorus': 0.002, 'potassium': 0.012},
          'roots': {'nitrogen': 0.020, 'phosphorus': 0.002, 'potassium': 0.015}},
         {'water': 0.6, 'nitrogen': 0.4, 'temperature': 0.7, 'light': 0.6},
         {'leaves': 0.02, 'stems': 0.01, 'roots': 0.005})
    ]
    
    for scenario_name, demands, stress, senescence in scenarios:
        # Simulate transport
        response = model.daily_update(
            organ_demands=demands,
            stress_factors=stress,
            senescence_rates=senescence,
            growth_stage='vegetative',
            water_fluxes={'leaves': 0.2, 'stems': 0.1, 'roots': 0.3},
            assimilate_fluxes={'leaves': 0.1, 'stems': 0.05, 'roots': 0.02},
            temperature=22.0
        )
        
        n_redist = response.total_redistribution.get('nitrogen', 0.0)
        p_redist = response.total_redistribution.get('phosphorus', 0.0)
        k_redist = response.total_redistribution.get('potassium', 0.0)
        n_limits = len(response.transport_limitations)
        
        print(f"{scenario_name:<20} {n_redist:<9.4f} {p_redist:<9.4f} "
              f"{k_redist:<9.4f} {n_limits:<8}")
        
        # Show mobility characteristics for first scenario
        if scenario_name == "Normal growth":
            print(f"\n  Mobility efficiency by nutrient:")
            for nutrient, efficiency in response.mobility_efficiency.items():
                mobility_class = model.params.mobility_classifications[nutrient]['mobility']
                print(f"    {nutrient}: {efficiency:.2f} ({mobility_class})")
    
    # Final summary
    summary = model.get_mobility_summary()
    print(f"\nMobility model summary:")
    print(f"• Transport pool fractions:")
    for nutrient, fraction in summary['transport_pool_fractions'].items():
        print(f"  {nutrient}: {fraction:.1%}")
    
    print(f"• Cumulative redistribution:")
    for nutrient, amount in summary['cumulative_redistribution'].items():
        print(f"  {nutrient}: {amount:.4f} g")


if __name__ == "__main__":
    demonstrate_nutrient_mobility_model()