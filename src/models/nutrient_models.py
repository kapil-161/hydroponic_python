"""
Unified Nutrient Models

Combines:
- Nutrient Concentration Submodel (solution ion dynamics and EC factors)
- Nutrient Mobility Model (in-plant transport and redistribution)

This consolidation replaces:
- src/models/nutrient_concentration.py
- src/models/nutrient_mobility.py
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import math

# =========================
# Nutrient Concentration Submodel
# =========================


@dataclass
class NutrientParams:
    """Parameters for a single nutrient."""
    nutrient_id: str
    nutrient_name: str
    chemical_form: str
    initial_conc: float  # mg/L
    recharge_conc: float  # mg/L
    uptake_conc: float  # mg/L
    sensitivity_coeff: float
    is_nutritive: bool
    min_conc: float  # mg/L
    max_conc: float  # mg/L
    charge: int = 0
    molar_mass: float = 0.0


class NutrientConcentrationModel:
    """Nutrient Concentration Submodel for hydroponic systems."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.nutrients: Dict[str, NutrientParams] = {}
        self.warning_flags: Dict[str, int] = {}

        # Load EC factors from CSV config
        self.ec_factors = self._load_ec_factors_from_config(config_dict)

        # Load minimum volume fraction
        if config_dict and "minimum_volume_fraction" in config_dict:
            self.minimum_volume_fraction = config_dict["minimum_volume_fraction"]
        else:
            self.minimum_volume_fraction = 0.1
    
    def _load_ec_factors_from_config(self, config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Load EC factors from CSV configuration."""
        if not config_dict:
            raise ValueError("Config dictionary is required for nutrient model - no CSV parameters loaded")
        
        # Load from CSV parameters - ERROR if missing
        required_ec_factors = [
            'ec_factor_n_no3', 'ec_factor_p_po4', 'ec_factor_k', 'ec_factor_ca',
            'ec_factor_mg', 'ec_factor_s_so4', 'ec_factor_fe'
        ]
        
        for param in required_ec_factors:
            if param not in config_dict:
                raise KeyError(f"Required EC factor parameter '{param}' not found in CSV configuration")
        
        return {
            "N-NO3": config_dict['ec_factor_n_no3'],
            "P-PO4": config_dict['ec_factor_p_po4'],
            "K": config_dict['ec_factor_k'],
            "Ca": config_dict['ec_factor_ca'],
            "Mg": config_dict['ec_factor_mg'],
            "S-SO4": config_dict['ec_factor_s_so4'],
            "Fe": config_dict['ec_factor_fe'],
            "Mn": config_dict.get('ec_factor_mn', 0.002),  # Optional parameters
            "Zn": config_dict.get('ec_factor_zn', 0.002),
            "Cu": config_dict.get('ec_factor_cu', 0.002),
            "B": config_dict.get('ec_factor_b', 0.0018),
            "Mo": config_dict.get('ec_factor_mo', 0.002),
        }
    
    def calculate_ec_from_concentrations(self, nutrient_concentrations: Dict[str, float]) -> float:
        """Calculate EC from individual nutrient concentrations using EC factors."""
        total_ec = 0.0
        for nutrient_id, concentration in nutrient_concentrations.items():
            ec_factor = self.ec_factors.get(nutrient_id)
            if ec_factor is None:
                raise ValueError(f"❌ EC factor for {nutrient_id} must be provided in CSV configuration - no hardcoded defaults allowed")
            total_ec += concentration * ec_factor
        return total_ec
    
    def calculate_ec_based_uptake_modifier(self, current_ec: float, optimal_ec: float, config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Calculate nutrient uptake modifiers based on EC levels using CSV parameters.
        
        Returns modifiers for different nutrients based on EC stress.
        High EC reduces uptake efficiency, low EC may indicate nutrient deficiency.
        """
        if not config_dict:
            raise ValueError("Config dictionary is required for EC uptake calculations - no CSV parameters loaded")
            
        ec_ratio = current_ec / optimal_ec if optimal_ec > 0 else 1.0
        
        # Load thresholds from CSV - ERROR if missing
        required_threshold_params = ['ec_uptake_high_threshold', 'ec_uptake_low_threshold']
        for param in required_threshold_params:
            if param not in config_dict:
                raise KeyError(f"Required EC threshold parameter '{param}' not found in CSV configuration")
        
        high_threshold = config_dict['ec_uptake_high_threshold']
        low_threshold = config_dict['ec_uptake_low_threshold']
        
        uptake_modifiers = {}
        
        if ec_ratio > high_threshold:  # High EC stress
            # Load high EC modifiers from CSV - ERROR if missing
            required_high_modifiers = [
                'ec_uptake_modifier_n_high', 'ec_uptake_modifier_p_high', 
                'ec_uptake_modifier_k_high', 'ec_uptake_modifier_ca_high'
            ]
            for param in required_high_modifiers:
                if param not in config_dict:
                    raise KeyError(f"Required EC modifier parameter '{param}' not found in CSV configuration")
            
            n_modifier = config_dict['ec_uptake_modifier_n_high']
            p_modifier = config_dict['ec_uptake_modifier_p_high']
            k_modifier = config_dict['ec_uptake_modifier_k_high']
            ca_modifier = config_dict['ec_uptake_modifier_ca_high']
            
            uptake_modifiers = {
                "N-NO3": max(0.3, 1.0 - (ec_ratio - 1.0) * n_modifier),
                "P-PO4": max(0.4, 1.0 - (ec_ratio - 1.0) * p_modifier),
                "K": max(0.5, 1.0 - (ec_ratio - 1.0) * k_modifier),
                "Ca": max(0.6, 1.0 - (ec_ratio - 1.0) * ca_modifier),
                "Mg": max(0.5, 1.0 - (ec_ratio - 1.0) * k_modifier),  # Similar to K
                "Fe": max(0.4, 1.0 - (ec_ratio - 1.0) * p_modifier),  # Similar to P
            }
        elif ec_ratio < low_threshold:  # Low EC - may indicate nutrient deficiency
            # Load low EC modifiers from CSV - ERROR if missing
            required_low_modifiers = [
                'ec_uptake_modifier_n_low', 'ec_uptake_modifier_p_low', 'ec_uptake_modifier_fe_low'
            ]
            for param in required_low_modifiers:
                if param not in config_dict:
                    raise KeyError(f"Required EC modifier parameter '{param}' not found in CSV configuration")
            
            n_modifier_low = config_dict['ec_uptake_modifier_n_low']
            p_modifier_low = config_dict['ec_uptake_modifier_p_low']
            fe_modifier_low = config_dict['ec_uptake_modifier_fe_low']
            
            uptake_modifiers = {
                "N-NO3": min(1.3, 1.0 + (low_threshold - ec_ratio) * n_modifier_low),
                "P-PO4": min(1.2, 1.0 + (low_threshold - ec_ratio) * p_modifier_low),
                "K": min(1.2, 1.0 + (low_threshold - ec_ratio) * p_modifier_low),
                "Ca": 1.0,  # Calcium uptake not affected by low EC
                "Mg": 1.0,  # Magnesium uptake not affected by low EC
                "Fe": min(1.4, 1.0 + (low_threshold - ec_ratio) * fe_modifier_low),
            }
        else:  # Optimal EC range
            uptake_modifiers = {nutrient: 1.0 for nutrient in self.ec_factors.keys()}
        
        # Apply default to any missing nutrients
        for nutrient in self.ec_factors.keys():
            if nutrient not in uptake_modifiers:
                uptake_modifiers[nutrient] = 1.0
        
        return uptake_modifiers


# =========================
# Nutrient Mobility Model (in-plant)
# =========================


class NutrientMobility(Enum):
    """Nutrient mobility classifications."""
    HIGHLY_MOBILE = "highly_mobile"  # N, P, K, Mg, Cl
    MODERATELY_MOBILE = "moderately_mobile"  # S, Fe, Zn, Mn
    POORLY_MOBILE = "poorly_mobile"  # Ca, B, Mo
    IMMOBILE = "immobile"  # Some forms of Fe, Ca


class TransportMechanism(Enum):
    """Nutrient transport mechanisms."""
    XYLEM_ONLY = "xylem_only"  # Ca, B, Mo - upward only
    PHLOEM_ONLY = "phloem_only"  # Some organic compounds
    BIDIRECTIONAL = "bidirectional"  # N, P, K, Mg - both directions
    COMPLEX = "complex"  # Fe, Zn, Mn - multiple forms


@dataclass
class NutrientMobilityParameters:
    """Parameters for nutrient mobility model."""

    xylem_transport_capacity: float = None
    phloem_transport_capacity: float = None
    temperature_q10: float = None
    transpiration_coupling: float = None
    mobility_classifications: Dict[str, Dict[str, Any]] = None
    xylem_transport_rates: Dict[str, float] = None
    phloem_transport_rates: Dict[str, float] = None
    buffering_capacities: Dict[str, Dict[str, float]] = None
    storage_pool_sizes: Dict[str, Dict[str, float]] = None
    redistribution_thresholds: Dict[str, float] = None
    stress_redistribution_rates: Dict[str, float] = None
    sink_strength_coefficients: Dict[str, Dict[str, float]] = None

    def __post_init__(self):
        if self.mobility_classifications is None:
            self.mobility_classifications = {
                "nitrogen": {
                    "mobility": NutrientMobility.HIGHLY_MOBILE.value,
                    "transport": TransportMechanism.BIDIRECTIONAL.value,
                    "remobilization_efficiency": 0.80,
                    "deficiency_mobility": "high",
                    "retranslocation_rate": 0.15,
                },
                "phosphorus": {
                    "mobility": NutrientMobility.HIGHLY_MOBILE.value,
                    "transport": TransportMechanism.BIDIRECTIONAL.value,
                    "remobilization_efficiency": 0.70,
                    "deficiency_mobility": "high",
                    "retranslocation_rate": 0.12,
                },
                "potassium": {
                    "mobility": NutrientMobility.HIGHLY_MOBILE.value,
                    "transport": TransportMechanism.BIDIRECTIONAL.value,
                    "remobilization_efficiency": 0.85,
                    "deficiency_mobility": "very_high",
                    "retranslocation_rate": 0.20,
                },
                "calcium": {
                    "mobility": NutrientMobility.POORLY_MOBILE.value,
                    "transport": TransportMechanism.XYLEM_ONLY.value,
                    "remobilization_efficiency": 0.05,
                    "deficiency_mobility": "very_low",
                    "retranslocation_rate": 0.01,
                },
                "magnesium": {
                    "mobility": NutrientMobility.MODERATELY_MOBILE.value,
                    "transport": TransportMechanism.BIDIRECTIONAL.value,
                    "remobilization_efficiency": 0.45,
                    "deficiency_mobility": "moderate",
                    "retranslocation_rate": 0.08,
                },
                "sulfur": {
                    "mobility": NutrientMobility.MODERATELY_MOBILE.value,
                    "transport": TransportMechanism.BIDIRECTIONAL.value,
                    "remobilization_efficiency": 0.60,
                    "deficiency_mobility": "moderate",
                    "retranslocation_rate": 0.10,
                },
                "iron": {
                    "mobility": NutrientMobility.POORLY_MOBILE.value,
                    "transport": TransportMechanism.COMPLEX.value,
                    "remobilization_efficiency": 0.15,
                    "deficiency_mobility": "low",
                    "retranslocation_rate": 0.03,
                },
                "manganese": {
                    "mobility": NutrientMobility.MODERATELY_MOBILE.value,
                    "transport": TransportMechanism.COMPLEX.value,
                    "remobilization_efficiency": 0.35,
                    "deficiency_mobility": "moderate",
                    "retranslocation_rate": 0.06,
                },
                "zinc": {
                    "mobility": NutrientMobility.MODERATELY_MOBILE.value,
                    "transport": TransportMechanism.COMPLEX.value,
                    "remobilization_efficiency": 0.40,
                    "deficiency_mobility": "moderate",
                    "retranslocation_rate": 0.07,
                },
                "copper": {
                    "mobility": NutrientMobility.MODERATELY_MOBILE.value,
                    "transport": TransportMechanism.COMPLEX.value,
                    "remobilization_efficiency": 0.25,
                    "deficiency_mobility": "low",
                    "retranslocation_rate": 0.04,
                },
                "boron": {
                    "mobility": NutrientMobility.POORLY_MOBILE.value,
                    "transport": TransportMechanism.XYLEM_ONLY.value,
                    "remobilization_efficiency": 0.08,
                    "deficiency_mobility": "very_low",
                    "retranslocation_rate": 0.01,
                },
                "molybdenum": {
                    "mobility": NutrientMobility.MODERATELY_MOBILE.value,
                    "transport": TransportMechanism.BIDIRECTIONAL.value,
                    "remobilization_efficiency": 0.50,
                    "deficiency_mobility": "moderate",
                    "retranslocation_rate": 0.09,
                },
            }
        if self.xylem_transport_rates is None:
            self.xylem_transport_rates = {
                "nitrogen": 0.25,
                "phosphorus": 0.15,
                "potassium": 0.30,
                "calcium": 0.20,
                "magnesium": 0.18,
                "sulfur": 0.12,
                "iron": 0.08,
                "manganese": 0.10,
                "zinc": 0.10,
                "copper": 0.08,
                "boron": 0.15,
                "molybdenum": 0.12,
            }
        if self.phloem_transport_rates is None:
            self.phloem_transport_rates = {
                "nitrogen": 0.20,
                "phosphorus": 0.18,
                "potassium": 0.25,
                "calcium": 0.01,
                "magnesium": 0.12,
                "sulfur": 0.15,
                "iron": 0.05,
                "manganese": 0.08,
                "zinc": 0.10,
                "copper": 0.06,
                "boron": 0.02,
                "molybdenum": 0.12,
            }
        if self.buffering_capacities is None:
            self.buffering_capacities = {
                "leaves": {"nitrogen": 0.30, "phosphorus": 0.25, "potassium": 0.35},
                "stems": {"nitrogen": 0.20, "phosphorus": 0.15, "potassium": 0.25},
                "roots": {"nitrogen": 0.15, "phosphorus": 0.20, "potassium": 0.20},
            }
        if self.storage_pool_sizes is None:
            self.storage_pool_sizes = {
                "leaves": {"nitrogen": 0.40, "phosphorus": 0.30, "potassium": 0.50},
                "stems": {"nitrogen": 0.60, "phosphorus": 0.50, "potassium": 0.70},
                "roots": {"nitrogen": 0.35, "phosphorus": 0.40, "potassium": 0.45},
            }
        if self.redistribution_thresholds is None:
            self.redistribution_thresholds = {
                "nitrogen": 0.7,
                "phosphorus": 0.6,
                "potassium": 0.8,
                "calcium": 0.4,
                "magnesium": 0.6,
                "sulfur": 0.6,
            }
        if self.stress_redistribution_rates is None:
            self.stress_redistribution_rates = {
                "nitrogen": 0.30,
                "phosphorus": 0.25,
                "potassium": 0.40,
                "magnesium": 0.20,
                "sulfur": 0.25,
            }
        if self.sink_strength_coefficients is None:
            self.sink_strength_coefficients = {
                "vegetative": {"leaves": 0.50, "stems": 0.25, "roots": 0.25},
                "reproductive": {"leaves": 0.30, "stems": 0.20, "roots": 0.15, "reproductive": 0.35},
                "senescence": {"leaves": 0.10, "stems": 0.30, "roots": 0.25, "reproductive": 0.35},
            }

    @classmethod
    def from_config(cls, config_dict: dict) -> "NutrientMobilityParameters":
        mobility_class = config_dict.get("mobility_classifications", {})
        xylem_rates = config_dict.get("xylem_transport_rates", {})
        phloem_rates = config_dict.get("phloem_transport_rates", {})
        buffering_cap = config_dict.get("buffering_capacities", {})
        storage_sizes = config_dict.get("storage_pool_sizes", {})
        redist_thresh = config_dict.get("redistribution_thresholds", {})
        stress_redist = config_dict.get("stress_redistribution_rates", {})
        sink_coeffs = config_dict.get("sink_strength_coefficients", {})
        return cls(
            mobility_classifications=mobility_class or None,
            xylem_transport_rates=xylem_rates or None,
            phloem_transport_rates=phloem_rates or None,
            buffering_capacities=buffering_cap or None,
            storage_pool_sizes=storage_sizes or None,
            redistribution_thresholds=redist_thresh or None,
            stress_redistribution_rates=stress_redist or None,
            sink_strength_coefficients=sink_coeffs or None,
            xylem_transport_capacity=config_dict.get("xylem_transport_capacity"),
            phloem_transport_capacity=config_dict.get("phloem_transport_capacity"),
            temperature_q10=config_dict.get("temperature_q10"),
            transpiration_coupling=config_dict.get("transpiration_coupling"),
        )


@dataclass
class NutrientTransportFlux:
    source_organ: str
    sink_organ: str
    nutrient: str
    transport_mechanism: str
    flux_rate: float
    driving_force: str
    efficiency: float


@dataclass
class OrganNutrientPools:
    organ_name: str
    nutrient_name: str
    metabolic_pool: float = 0.0
    storage_pool: float = 0.0
    transport_pool: float = 0.0
    buffer_pool: float = 0.0
    total_content: float = 0.0
    concentration: float = 0.0
    mobility_status: str = "optimal"
    available_for_export: float = 0.0
    demand_for_import: float = 0.0
    buffering_capacity: float = 0.0

    def __post_init__(self):
        self.total_content = self.metabolic_pool + self.storage_pool + self.transport_pool + self.buffer_pool


@dataclass
class NutrientMobilityResponse:
    transport_fluxes: List[NutrientTransportFlux]
    organ_pools: Dict[str, Dict[str, OrganNutrientPools]]
    total_redistribution: Dict[str, float]
    transport_limitations: List[str]
    sink_demands: Dict[str, Dict[str, float]]
    source_supplies: Dict[str, Dict[str, float]]
    mobility_efficiency: Dict[str, float]


class NutrientMobilityModel:
    def __init__(self, parameters: Optional[NutrientMobilityParameters] = None):
        self.params = parameters or NutrientMobilityParameters()
        self.organ_pools: Dict[str, Dict[str, OrganNutrientPools]] = {}
        self.transport_history: List[Dict[str, Any]] = []
        self.cumulative_redistribution: Dict[str, float] = {}

    def initialize_organ_pools(self, organ_name: str, nutrient_contents: Dict[str, float], dry_mass: float):
        if organ_name not in self.organ_pools:
            self.organ_pools[organ_name] = {}
        for nutrient, total_content in nutrient_contents.items():
            if nutrient in self.params.mobility_classifications:
                storage_fraction = self.params.storage_pool_sizes.get(organ_name, {}).get(nutrient, 0.3)
                buffer_fraction = self.params.buffering_capacities.get(organ_name, {}).get(nutrient, 0.2)
                storage_pool = total_content * storage_fraction
                buffer_pool = total_content * buffer_fraction
                transport_pool = total_content * 0.05
                metabolic_pool = total_content - storage_pool - buffer_pool - transport_pool
                pool = OrganNutrientPools(
                    organ_name=organ_name,
                    nutrient_name=nutrient,
                    metabolic_pool=max(0.0, metabolic_pool),
                    storage_pool=storage_pool,
                    transport_pool=transport_pool,
                    buffer_pool=buffer_pool,
                    total_content=total_content,
                    concentration=total_content / max(dry_mass, 0.001),
                    buffering_capacity=buffer_pool,
                )
                self.organ_pools[organ_name][nutrient] = pool
        for nutrient in nutrient_contents.keys():
            if nutrient not in self.cumulative_redistribution:
                self.cumulative_redistribution[nutrient] = 0.0

    def calculate_transport_capacity(self, source_organ: str, sink_organ: str, water_flux: float, assimilate_flux: float, temperature: float, organ_nutrient_status: Optional[Dict[str, float]] = None, environmental_conditions: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        # Base capacity constrained by physical fluxes
        base_xylem_capacity = water_flux * self.params.xylem_transport_capacity * self.params.transpiration_coupling
        base_phloem_capacity = assimilate_flux * self.params.phloem_transport_capacity
        
        # Dynamic feedback from organ nutrient status
        nutrient_feedback_factor = 1.0
        if organ_nutrient_status:
            # Higher nutrient status in source increases transport capacity
            # Lower nutrient status in sink increases transport capacity (demand signal)
            source_status = organ_nutrient_status.get(f"{source_organ}_nutrient_status", 1.0)
            sink_status = organ_nutrient_status.get(f"{sink_organ}_nutrient_status", 1.0)
            
            # Transport capacity increases when source is nutrient-rich or sink is nutrient-poor
            nutrient_feedback_factor = (source_status * 1.2 + (2.0 - sink_status) * 0.8) / 2.0
            nutrient_feedback_factor = max(0.5, min(2.0, nutrient_feedback_factor))
        
        # Environmental feedback
        environmental_factor = 1.0
        if environmental_conditions:
            # EC stress reduces transport efficiency
            ec_factor = environmental_conditions.get('ec_factor', 1.0)
            # Temperature stress affects transport kinetics
            temp_stress = environmental_conditions.get('temperature_stress_factor', 1.0)
            # VPD affects xylem transport through transpiration
            vpd_factor = environmental_conditions.get('vpd_factor', 1.0)
            
            environmental_factor = ec_factor * temp_stress
            # VPD specifically affects xylem transport
            xylem_environmental_factor = environmental_factor * vpd_factor
            phloem_environmental_factor = environmental_factor
        else:
            xylem_environmental_factor = environmental_factor
            phloem_environmental_factor = environmental_factor
        
        # Apply dynamic feedback to capacities
        xylem_capacity = base_xylem_capacity * nutrient_feedback_factor * xylem_environmental_factor
        phloem_capacity = base_phloem_capacity * nutrient_feedback_factor * phloem_environmental_factor
        
        return {"xylem": xylem_capacity, "phloem": phloem_capacity}

    def calculate_sink_demands(self, organ_demands: Dict[str, Dict[str, float]], growth_stage: str) -> Dict[str, Dict[str, float]]:
        adjusted: Dict[str, Dict[str, float]] = {}
        sink_coeffs = self.params.sink_strength_coefficients.get(growth_stage, self.params.sink_strength_coefficients["vegetative"])
        for organ_name, demands in organ_demands.items():
            adjusted[organ_name] = {}
            organ_sink_strength = sink_coeffs.get(organ_name, 0.25)
            for nutrient, demand in demands.items():
                adj = demand * organ_sink_strength
                if nutrient in self.params.mobility_classifications:
                    mobility_info = self.params.mobility_classifications[nutrient]
                    dm = mobility_info["deficiency_mobility"]
                    if dm == "very_high":
                        adj *= 1.2
                    elif dm == "high":
                        adj *= 1.1
                    elif dm == "low":
                        adj *= 0.8
                    elif dm == "very_low":
                        adj *= 0.6
                adjusted[organ_name][nutrient] = adj
        return adjusted

    def calculate_source_supplies(self, stress_factors: Dict[str, float], senescence_rates: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        supplies: Dict[str, Dict[str, float]] = {}
        for organ_name, nutrient_pools in self.organ_pools.items():
            supplies[organ_name] = {}
            overall_stress = 1.0 - min(stress_factors.values()) if stress_factors else 0.0
            organ_senescence = senescence_rates.get(organ_name, 0.0)
            for nutrient, pool in nutrient_pools.items():
                if nutrient in self.params.mobility_classifications:
                    mobility_info = self.params.mobility_classifications[nutrient]
                    base_supply = pool.storage_pool * 0.1 + pool.buffer_pool * 0.05
                    stress_supply = 0.0
                    if overall_stress > 0.3:
                        stress_threshold = self.params.redistribution_thresholds.get(nutrient, 0.7)
                        if overall_stress > (1.0 - stress_threshold):
                            stress_rate = self.params.stress_redistribution_rates.get(nutrient, 0.2)
                            stress_supply = pool.storage_pool * stress_rate * overall_stress
                    senescence_supply = 0.0
                    if organ_senescence > 0.01:
                        rem = mobility_info["remobilization_efficiency"]
                        senescence_supply = pool.metabolic_pool * organ_senescence * rem
                    total_supply = base_supply + stress_supply + senescence_supply
                    max_transportable = pool.total_content * 0.3
                    total_supply = min(total_supply, max_transportable)
                    supplies[organ_name][nutrient] = total_supply
                else:
                    supplies[organ_name][nutrient] = 0.0
        return supplies

    def calculate_transport_fluxes(self, sink_demands: Dict[str, Dict[str, float]], source_supplies: Dict[str, Dict[str, float]], transport_capacities: Dict[str, Dict[str, float]], temperature: float) -> List[NutrientTransportFlux]:
        fluxes: List[NutrientTransportFlux] = []
        # Apply Q10 temperature response to transport kinetics (rates), not to capacity
        temp_factor = self.params.temperature_q10 ** ((float(temperature) - 25.0) / 10.0)
        temp_factor = max(0.5, min(2.0, temp_factor))
        for nutrient in self.params.mobility_classifications:
            mobility_info = self.params.mobility_classifications[nutrient]
            transport_type = mobility_info["transport"]
            xylem_rate = self.params.xylem_transport_rates.get(nutrient, 0.1) * temp_factor
            phloem_rate = self.params.phloem_transport_rates.get(nutrient, 0.1) * temp_factor
            total_demand = sum(d.get(nutrient, 0.0) for d in sink_demands.values())
            total_supply = sum(s.get(nutrient, 0.0) for s in source_supplies.values())
            if total_demand > 0 and total_supply > 0:
                supply_demand_ratio = total_supply / total_demand
                transport_eff = min(1.0, supply_demand_ratio)
                for source_organ, supplies in source_supplies.items():
                    if supplies.get(nutrient, 0.0) > 0:
                        src_supply = supplies[nutrient]
                        for sink_organ, demands in sink_demands.items():
                            if demands.get(nutrient, 0.0) > 0 and source_organ != sink_organ:
                                sink_demand = demands[nutrient]
                                if transport_type == TransportMechanism.XYLEM_ONLY.value:
                                    if source_organ == "roots":
                                        max_flux = src_supply * xylem_rate
                                        cap = transport_capacities.get(source_organ, {}).get("xylem", 1.0)
                                        flux_rate = min(max_flux, sink_demand, cap)
                                        mechanism = "xylem"
                                    else:
                                        flux_rate = 0.0
                                        mechanism = "none"
                                elif transport_type == TransportMechanism.BIDIRECTIONAL.value:
                                    xylem_flux = src_supply * xylem_rate * 0.6
                                    phloem_flux = src_supply * phloem_rate * 0.4
                                    xcap = transport_capacities.get(source_organ, {}).get("xylem", 1.0)
                                    pcap = transport_capacities.get(source_organ, {}).get("phloem", 1.0)
                                    flux_rate = min(xylem_flux + phloem_flux, sink_demand, xcap + pcap)
                                    mechanism = "bidirectional"
                                elif transport_type == TransportMechanism.COMPLEX.value:
                                    base_flux = src_supply * min(xylem_rate, phloem_rate)
                                    total_cap = transport_capacities.get(source_organ, {}).get("xylem", 0.5) + transport_capacities.get(source_organ, {}).get("phloem", 0.5)
                                    flux_rate = min(base_flux, sink_demand, total_cap)
                                    mechanism = "complex"
                                else:
                                    flux_rate = 0.0
                                    mechanism = "none"
                                flux_rate *= transport_eff
                                if flux_rate > 0.001:
                                    fluxes.append(
                                        NutrientTransportFlux(
                                            source_organ=source_organ,
                                            sink_organ=sink_organ,
                                            nutrient=nutrient,
                                            transport_mechanism=mechanism,
                                            flux_rate=flux_rate,
                                            driving_force="demand",
                                            efficiency=transport_eff,
                                        )
                                    )
        return fluxes

    def update_organ_pools(self, transport_fluxes: List[NutrientTransportFlux]):
        net_fluxes: Dict[str, Dict[str, float]] = {}
        for flux in transport_fluxes:
            net_fluxes.setdefault(flux.source_organ, {}).setdefault(flux.nutrient, 0.0)
            net_fluxes.setdefault(flux.sink_organ, {}).setdefault(flux.nutrient, 0.0)
            net_fluxes[flux.source_organ][flux.nutrient] -= flux.flux_rate
            net_fluxes[flux.sink_organ][flux.nutrient] += flux.flux_rate
        for organ_name, nutrient_fluxes in net_fluxes.items():
            if organ_name in self.organ_pools:
                for nutrient, net_flux in nutrient_fluxes.items():
                    if nutrient in self.organ_pools[organ_name]:
                        pool = self.organ_pools[organ_name][nutrient]
                        if net_flux < 0:
                            outflow = abs(net_flux)
                            from_transport = min(outflow, pool.transport_pool)
                            pool.transport_pool -= from_transport
                            outflow -= from_transport
                            if outflow > 0:
                                from_storage = min(outflow, pool.storage_pool)
                                pool.storage_pool -= from_storage
                                outflow -= from_storage
                            if outflow > 0:
                                from_buffer = min(outflow, pool.buffer_pool)
                                pool.buffer_pool -= from_buffer
                                outflow -= from_buffer
                            if outflow > 0:
                                from_met = min(outflow, pool.metabolic_pool * 0.1)
                                pool.metabolic_pool -= from_met
                        else:
                            pool.transport_pool += net_flux
                            if pool.transport_pool > pool.total_content * 0.1:
                                excess = pool.transport_pool - pool.total_content * 0.05
                                pool.transport_pool -= excess
                                pool.metabolic_pool += excess * 0.6
                                pool.storage_pool += excess * 0.3
                                pool.buffer_pool += excess * 0.1
                        pool.total_content = pool.metabolic_pool + pool.storage_pool + pool.transport_pool + pool.buffer_pool
                        # Track signed net redistribution to capture direction and magnitude
                        if nutrient in self.cumulative_redistribution:
                            self.cumulative_redistribution[nutrient] += net_flux

    def calculate_mobility_efficiency(self, nutrient: str) -> float:
        if nutrient not in self.params.mobility_classifications:
            return 0.5
        mobility_info = self.params.mobility_classifications[nutrient]
        mobility_class = mobility_info["mobility"]
        if mobility_class == NutrientMobility.HIGHLY_MOBILE.value:
            base_eff = 0.8
        elif mobility_class == NutrientMobility.MODERATELY_MOBILE.value:
            base_eff = 0.6
        elif mobility_class == NutrientMobility.POORLY_MOBILE.value:
            base_eff = 0.3
        else:
            base_eff = 0.1
        transport_type = mobility_info["transport"]
        if transport_type == TransportMechanism.BIDIRECTIONAL.value:
            t_factor = 1.2
        elif transport_type == TransportMechanism.COMPLEX.value:
            t_factor = 0.9
        elif transport_type == TransportMechanism.XYLEM_ONLY.value:
            t_factor = 0.7
        else:
            t_factor = 1.0
        return min(1.0, base_eff * t_factor)

    def daily_update(self, organ_demands: Dict[str, Dict[str, float]], stress_factors: Dict[str, float], senescence_rates: Dict[str, float], growth_stage: str, water_fluxes: Dict[str, float], assimilate_fluxes: Dict[str, float], temperature: float, organ_nutrient_status: Optional[Dict[str, float]] = None, environmental_conditions: Optional[Dict[str, float]] = None) -> NutrientMobilityResponse:
        sink_demands = self.calculate_sink_demands(organ_demands, growth_stage)
        source_supplies = self.calculate_source_supplies(stress_factors, senescence_rates)
        transport_capacities: Dict[str, Dict[str, float]] = {}
        for organ in self.organ_pools.keys():
            water_flux = water_fluxes.get(organ, 0.1)
            assimilate_flux = assimilate_fluxes.get(organ, 0.05)
            # Use enhanced transport capacity calculation with dynamic feedback
            transport_capacities[organ] = self.calculate_transport_capacity(
                organ, "sink", water_flux, assimilate_flux, temperature,
                organ_nutrient_status, environmental_conditions
            )
        transport_fluxes = self.calculate_transport_fluxes(sink_demands, source_supplies, transport_capacities, temperature)
        self.update_organ_pools(transport_fluxes)
        total_redistribution: Dict[str, float] = {}
        for flux in transport_fluxes:
            total_redistribution[flux.nutrient] = total_redistribution.get(flux.nutrient, 0.0) + flux.flux_rate
        limitations: List[str] = []
        for nutrient in self.params.mobility_classifications:
            total_demand = sum(d.get(nutrient, 0.0) for d in sink_demands.values())
            total_flux = total_redistribution.get(nutrient, 0.0)
            if total_demand > 0 and total_flux < total_demand * 0.8:
                limitations.append(f"{nutrient}_transport_limited")
        mobility_efficiency: Dict[str, float] = {n: self.calculate_mobility_efficiency(n) for n in self.params.mobility_classifications}
        self.transport_history.append({
            "total_redistribution": sum(total_redistribution.values()),
            "transport_fluxes": len(transport_fluxes),
            "limitations": len(limitations),
        })
        return NutrientMobilityResponse(
            transport_fluxes=transport_fluxes,
            organ_pools=self.organ_pools.copy(),
            total_redistribution=total_redistribution,
            transport_limitations=limitations,
            sink_demands=sink_demands,
            source_supplies=source_supplies,
            mobility_efficiency=mobility_efficiency,
        )

    def get_mobility_summary(self) -> Dict[str, Any]:
        total_nutrients: Dict[str, float] = {}
        transport_pools: Dict[str, float] = {}
        for organ_name, nutrient_pools in self.organ_pools.items():
            for nutrient, pool in nutrient_pools.items():
                total_nutrients[nutrient] = total_nutrients.get(nutrient, 0.0) + pool.total_content
                transport_pools[nutrient] = transport_pools.get(nutrient, 0.0) + pool.transport_pool
        transport_fractions: Dict[str, float] = {}
        for nutrient, total in total_nutrients.items():
            transport_fractions[nutrient] = (transport_pools.get(nutrient, 0.0) / total) if total > 0 else 0.0
        return {
            "total_nutrients": total_nutrients,
            "transport_pool_fractions": transport_fractions,
            "cumulative_redistribution": self.cumulative_redistribution.copy(),
            "mobility_classifications": {n: info["mobility"] for n, info in self.params.mobility_classifications.items()},
            "transport_mechanisms": {n: info["transport"] for n, info in self.params.mobility_classifications.items()},
        }


def create_lettuce_nutrient_mobility_model(system_config=None) -> NutrientMobilityModel:
    """Create nutrient mobility model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        NutrientMobilityModel configured with CSV parameters
    """
    try:
        # Get nutrient mobility parameters from CSV data loaded in system_config
        nutrient_mobility_params = getattr(system_config, 'nutrient_mobility_parameters', {}).copy()
        
        # Map renamed parameters to expected parameter names
        param_mapping = {
            'nutrient_mobility_temperature_q10': 'temperature_q10',
            'nutrient_mobility_base_temperature': 'base_temperature'
        }
        
        # Apply parameter name mapping
        for csv_name, model_name in param_mapping.items():
            if csv_name in nutrient_mobility_params:
                nutrient_mobility_params[model_name] = nutrient_mobility_params[csv_name]
        
        # Create parameters from CSV config
        parameters = NutrientMobilityParameters.from_config(nutrient_mobility_params)
        return NutrientMobilityModel(parameters)
        
    except Exception as e:
        print(f"Warning: Could not load CSV nutrient parameters: {e}")
        print("Using default nutrient parameters")
        return NutrientMobilityModel()


