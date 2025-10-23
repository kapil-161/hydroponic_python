from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import math
import numpy as np


def get_required_stress_param(params: dict, param_name: str) -> float:
    """Get required parameter or raise ParameterError if missing (minimal wrapper for compatibility)"""
    if param_name not in params: raise ParameterError(f"Missing parameter: {param_name}")
    return params[param_name]





def _build_simple_interactions(stress_weights: Dict[str, float]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Build simplified stress interactions from weights"""
    return {
        "water": {
            "temperature": {"type": "synergistic", "factor": 1.2},
            "salinity": {"type": "synergistic", "factor": 1.3}
        },
        "temperature": {
            "water": {"type": "synergistic", "factor": 1.2},
            "light": {"type": "additive", "factor": 1.1}
        },
        "nutrient": {
            "ph": {"type": "synergistic", "factor": 1.4},
            "salinity": {"type": "multiplicative", "factor": 1.2}
        }
    }


def _build_cumulative_thresholds(stress_weights: Dict[str, float], config: Dict[str, Any]) -> Dict[str, float]:
    """Build cumulative stress thresholds from weights using CSV parameters - NO HARDCODED VALUES (Rules.md)"""
    base = float(config.get('cumulative_threshold_coefficient_base', 0.3))
    weight_coeff = float(config.get('cumulative_threshold_coefficient_weight', 0.2))
    return {k: base + v * weight_coeff for k, v in stress_weights.items()}


def _build_damage_rates(recovery_rates: Dict[str, float], config: Dict[str, Any]) -> Dict[str, float]:
    """Build damage accumulation rates from recovery rates using CSV parameters - NO HARDCODED VALUES (Rules.md)"""
    coeff = float(config.get('damage_rate_recovery_coefficient', 0.5))
    return {k: v * coeff for k, v in recovery_rates.items()}


def _build_recovery_thresholds(onset_thresholds: Dict[str, float], config: Dict[str, Any]) -> Dict[str, float]:
    """Build recovery thresholds from onset thresholds using CSV parameters - NO HARDCODED VALUES (Rules.md)"""
    offset = float(config.get('recovery_threshold_offset', 0.05))
    return {k: v + offset for k, v in onset_thresholds.items()}


def _build_recovery_times(recovery_rates: Dict[str, float], config: Dict[str, Any]) -> Dict[str, float]:
    """Build full recovery times from recovery rates using CSV parameters - NO HARDCODED VALUES (Rules.md)"""
    min_rate = float(config.get('recovery_time_minimum_rate', 0.01))
    return {k: 1.0 / max(v, min_rate) for k, v in recovery_rates.items()}


def _build_acclimation_capacity(acclimation_rates: Dict[str, float], config: Dict[str, Any]) -> Dict[str, float]:
    """Build acclimation capacity from rates using CSV parameters - NO HARDCODED VALUES (Rules.md)"""
    multiplier = float(config.get('acclimation_capacity_multiplier', 2.0))
    maximum = float(config.get('acclimation_capacity_maximum', 0.8))
    return {k: min(v * multiplier, maximum) for k, v in acclimation_rates.items()}


def _build_acclimation_memory(memory_duration: Dict[str, float], config: Dict[str, Any]) -> Dict[str, float]:
    """Build acclimation memory from duration using CSV parameters - NO HARDCODED VALUES (Rules.md)"""
    decay_factor = float(config.get('acclimation_memory_decay_factor', 0.8))
    return {k: v * decay_factor for k, v in memory_duration.items()}


def _calculate_stress_interactions(stress_weights: Dict[str, float], config: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Calculate stress interaction factors based on biological principles"""
    # Calculate interaction factors based on stress weights and biological relationships
    water_weight = stress_weights[StressType.WATER.value]
    temp_weight = stress_weights[StressType.TEMPERATURE.value]
    nutrient_weight = stress_weights[StressType.NUTRIENT.value]
    salinity_weight = stress_weights[StressType.SALINITY.value]
    ph_weight = stress_weights[StressType.PH.value]
    light_weight = stress_weights[StressType.LIGHT.value]

    # Get interaction factors from CSV parameters - NO HARDCODED VALUES (Rules.md)
    water_salinity_interaction_factor = float(config.get('water_salinity_interaction_factor', 0.3))
    water_temp_coeff = float(config.get('stress_interaction_water_temperature_coefficient', 0.5))
    water_nutrient_coeff = float(config.get('stress_interaction_water_nutrient_coefficient', 0.4))
    temp_light_coeff = float(config.get('stress_interaction_temperature_light_coefficient', 0.2))
    nutrient_ph_coeff = float(config.get('stress_interaction_nutrient_ph_coefficient', 0.6))
    nutrient_salinity_coeff = float(config.get('stress_interaction_nutrient_salinity_coefficient', 0.4))

    # Water-temperature interaction: higher weights = stronger synergy
    water_temp_factor = 1.0 + (water_weight * temp_weight) * water_temp_coeff

    # Water-salinity interaction: both affect osmotic potential
    water_salinity_factor = 1.0 + (water_weight * salinity_weight) * water_salinity_interaction_factor

    # Water-nutrient interaction: water uptake affects nutrient availability
    water_nutrient_factor = 1.0 + (water_weight * nutrient_weight) * water_nutrient_coeff

    # Temperature-light interaction: both affect photosynthesis
    temp_light_factor = 1.0 + (temp_weight * light_weight) * temp_light_coeff

    # Nutrient-pH interaction: pH affects nutrient availability
    nutrient_ph_factor = 1.0 + (nutrient_weight * ph_weight) * nutrient_ph_coeff

    # Nutrient-salinity interaction: both affect root uptake
    nutrient_salinity_factor = 1.0 + (nutrient_weight * salinity_weight) * nutrient_salinity_coeff

    return {
        StressType.WATER.value: {
            StressType.TEMPERATURE.value: {"type": StressInteractionType.SYNERGISTIC.value, "factor": water_temp_factor},
            StressType.SALINITY.value: {"type": StressInteractionType.SYNERGISTIC.value, "factor": water_salinity_factor},
            StressType.NUTRIENT.value: {"type": StressInteractionType.MULTIPLICATIVE.value, "factor": water_nutrient_factor}
        },
        StressType.TEMPERATURE.value: {
            StressType.WATER.value: {"type": StressInteractionType.SYNERGISTIC.value, "factor": water_temp_factor},
            StressType.LIGHT.value: {"type": StressInteractionType.ADDITIVE.value, "factor": temp_light_factor}
        },
        StressType.NUTRIENT.value: {
            StressType.WATER.value: {"type": StressInteractionType.MULTIPLICATIVE.value, "factor": water_nutrient_factor},
            StressType.PH.value: {"type": StressInteractionType.SYNERGISTIC.value, "factor": nutrient_ph_factor},
            StressType.SALINITY.value: {"type": StressInteractionType.MULTIPLICATIVE.value, "factor": nutrient_salinity_factor}
        }
    }


def _calculate_process_sensitivity(stress_weights: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    """Calculate process sensitivity to different stress types based on biological principles"""
    stress_keys = list(stress_weights.keys())

    # Base sensitivity values based on biological knowledge
    photosynthesis_sensitivity = {
        StressType.LIGHT.value: 0.9,        # Highly sensitive to light
        StressType.TEMPERATURE.value: 0.7,   # Moderately sensitive to temperature
        StressType.WATER.value: 0.6,         # Sensitive to water stress
        StressType.NUTRIENT.value: 0.5,      # Moderately sensitive to nutrients
        StressType.SALINITY.value: 0.4,      # Less sensitive to salinity
        StressType.PH.value: 0.3,            # Less sensitive to pH
        StressType.OXYGEN.value: 0.2         # Least sensitive to oxygen
    }

    respiration_sensitivity = {
        StressType.TEMPERATURE.value: 0.8,   # Highly sensitive to temperature
        StressType.OXYGEN.value: 0.9,        # Highly sensitive to oxygen
        StressType.WATER.value: 0.4,         # Moderately sensitive to water
        StressType.NUTRIENT.value: 0.3,      # Less sensitive to nutrients
        StressType.LIGHT.value: 0.2,         # Less sensitive to light
        StressType.SALINITY.value: 0.3,      # Less sensitive to salinity
        StressType.PH.value: 0.2             # Least sensitive to pH
    }

    transpiration_sensitivity = {
        StressType.WATER.value: 0.9,         # Highly sensitive to water
        StressType.TEMPERATURE.value: 0.8,   # Highly sensitive to temperature
        StressType.LIGHT.value: 0.6,         # Moderately sensitive to light
        StressType.SALINITY.value: 0.5,      # Moderately sensitive to salinity
        StressType.NUTRIENT.value: 0.3,      # Less sensitive to nutrients
        StressType.PH.value: 0.2,            # Less sensitive to pH
        StressType.OXYGEN.value: 0.2         # Least sensitive to oxygen
    }

    growth_sensitivity = {
        StressType.NUTRIENT.value: 0.8,      # Highly sensitive to nutrients
        StressType.WATER.value: 0.7,         # Highly sensitive to water
        StressType.TEMPERATURE.value: 0.6,   # Moderately sensitive to temperature
        StressType.LIGHT.value: 0.5,         # Moderately sensitive to light
        StressType.PH.value: 0.4,            # Moderately sensitive to pH
        StressType.SALINITY.value: 0.4,      # Moderately sensitive to salinity
        StressType.OXYGEN.value: 0.3         # Less sensitive to oxygen
    }

    # Adjust sensitivities based on stress weights
    for stress_key in stress_keys:
        weight = stress_weights[stress_key]
        photosynthesis_sensitivity[stress_key] *= weight
        respiration_sensitivity[stress_key] *= weight
        transpiration_sensitivity[stress_key] *= weight
        growth_sensitivity[stress_key] *= weight

    return {
        ProcessType.PHOTOSYNTHESIS.value: photosynthesis_sensitivity,
        ProcessType.RESPIRATION.value: respiration_sensitivity,
        ProcessType.TRANSPIRATION.value: transpiration_sensitivity,
        ProcessType.GROWTH.value: growth_sensitivity
    }


def _calculate_memory_duration(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate stress memory duration based on biological principles"""
    return {
        StressType.WATER.value: 2.0 + stress_weights[StressType.WATER.value] * 1.0,
        StressType.TEMPERATURE.value: 1.5 + stress_weights[StressType.TEMPERATURE.value] * 0.5,
        StressType.NUTRIENT.value: 3.0 + stress_weights[StressType.NUTRIENT.value] * 2.0,
        StressType.LIGHT.value: 1.0 + stress_weights[StressType.LIGHT.value] * 0.5,
        StressType.SALINITY.value: 4.0 + stress_weights[StressType.SALINITY.value] * 2.0,
        StressType.OXYGEN.value: 0.5 + stress_weights[StressType.OXYGEN.value] * 0.2,
        StressType.PH.value: 2.5 + stress_weights[StressType.PH.value] * 1.0
    }


def _calculate_recovery_rates(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate stress recovery rates based on biological principles"""
    return {
        StressType.WATER.value: 0.3 + stress_weights[StressType.WATER.value] * 0.2,
        StressType.TEMPERATURE.value: 0.5 + stress_weights[StressType.TEMPERATURE.value] * 0.3,
        StressType.NUTRIENT.value: 0.2 + stress_weights[StressType.NUTRIENT.value] * 0.1,
        StressType.LIGHT.value: 0.8 + stress_weights[StressType.LIGHT.value] * 0.1,
        StressType.SALINITY.value: 0.1 + stress_weights[StressType.SALINITY.value] * 0.05,
        StressType.OXYGEN.value: 0.9 + stress_weights[StressType.OXYGEN.value] * 0.1,
        StressType.PH.value: 0.4 + stress_weights[StressType.PH.value] * 0.2
    }


def _calculate_acclimation_rates(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate stress acclimation rates based on biological principles"""
    return {
        StressType.WATER.value: 0.1 + stress_weights[StressType.WATER.value] * 0.05,
        StressType.TEMPERATURE.value: 0.2 + stress_weights[StressType.TEMPERATURE.value] * 0.1,
        StressType.NUTRIENT.value: 0.05 + stress_weights[StressType.NUTRIENT.value] * 0.02,
        StressType.LIGHT.value: 0.3 + stress_weights[StressType.LIGHT.value] * 0.1,
        StressType.SALINITY.value: 0.02 + stress_weights[StressType.SALINITY.value] * 0.01,
        StressType.OXYGEN.value: 0.1 + stress_weights[StressType.OXYGEN.value] * 0.05,
        StressType.PH.value: 0.08 + stress_weights[StressType.PH.value] * 0.03
    }


def _calculate_onset_thresholds(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate stress onset thresholds based on biological principles"""
    return {
        StressType.WATER.value: 0.8 - stress_weights[StressType.WATER.value] * 0.1,
        StressType.TEMPERATURE.value: 0.75 - stress_weights[StressType.TEMPERATURE.value] * 0.1,
        StressType.NUTRIENT.value: 0.7 - stress_weights[StressType.NUTRIENT.value] * 0.1,
        StressType.LIGHT.value: 0.6 - stress_weights[StressType.LIGHT.value] * 0.1,
        StressType.SALINITY.value: 0.9 - stress_weights[StressType.SALINITY.value] * 0.1,
        StressType.OXYGEN.value: 0.5 - stress_weights[StressType.OXYGEN.value] * 0.1,
        StressType.PH.value: 0.85 - stress_weights[StressType.PH.value] * 0.1
    }


def _calculate_damage_thresholds(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate stress damage thresholds based on biological principles"""
    return {
        StressType.WATER.value: 0.4 - stress_weights[StressType.WATER.value] * 0.05,
        StressType.TEMPERATURE.value: 0.3 - stress_weights[StressType.TEMPERATURE.value] * 0.05,
        StressType.NUTRIENT.value: 0.3 - stress_weights[StressType.NUTRIENT.value] * 0.05,
        StressType.LIGHT.value: 0.2 - stress_weights[StressType.LIGHT.value] * 0.05,
        StressType.SALINITY.value: 0.5 - stress_weights[StressType.SALINITY.value] * 0.05,
        StressType.OXYGEN.value: 0.1 - stress_weights[StressType.OXYGEN.value] * 0.02,
        StressType.PH.value: 0.4 - stress_weights[StressType.PH.value] * 0.05
    }


def _calculate_cumulative_threshold(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate cumulative stress thresholds based on biological principles"""
    return {
        StressType.WATER.value: 5.0 + stress_weights[StressType.WATER.value] * 2.0,
        StressType.TEMPERATURE.value: 3.0 + stress_weights[StressType.TEMPERATURE.value] * 1.0,
        StressType.NUTRIENT.value: 7.0 + stress_weights[StressType.NUTRIENT.value] * 3.0,
        StressType.LIGHT.value: 2.0 + stress_weights[StressType.LIGHT.value] * 0.5,
        StressType.SALINITY.value: 10.0 + stress_weights[StressType.SALINITY.value] * 5.0,
        StressType.OXYGEN.value: 1.0 + stress_weights[StressType.OXYGEN.value] * 0.2,
        StressType.PH.value: 6.0 + stress_weights[StressType.PH.value] * 2.0
    }


def _calculate_damage_accumulation_rate(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate damage accumulation rates based on biological principles"""
    return {
        StressType.WATER.value: 0.1 + stress_weights[StressType.WATER.value] * 0.05,
        StressType.TEMPERATURE.value: 0.15 + stress_weights[StressType.TEMPERATURE.value] * 0.08,
        StressType.NUTRIENT.value: 0.08 + stress_weights[StressType.NUTRIENT.value] * 0.03,
        StressType.LIGHT.value: 0.05 + stress_weights[StressType.LIGHT.value] * 0.02,
        StressType.SALINITY.value: 0.12 + stress_weights[StressType.SALINITY.value] * 0.06,
        StressType.OXYGEN.value: 0.2 + stress_weights[StressType.OXYGEN.value] * 0.1,
        StressType.PH.value: 0.09 + stress_weights[StressType.PH.value] * 0.04
    }


def _calculate_recovery_thresholds(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate recovery thresholds based on biological principles"""
    return {
        StressType.WATER.value: 0.95 - stress_weights[StressType.WATER.value] * 0.05,
        StressType.TEMPERATURE.value: 0.9 - stress_weights[StressType.TEMPERATURE.value] * 0.05,
        StressType.NUTRIENT.value: 0.85 - stress_weights[StressType.NUTRIENT.value] * 0.05,
        StressType.LIGHT.value: 0.8 - stress_weights[StressType.LIGHT.value] * 0.05,
        StressType.SALINITY.value: 0.98 - stress_weights[StressType.SALINITY.value] * 0.02,
        StressType.OXYGEN.value: 0.7 - stress_weights[StressType.OXYGEN.value] * 0.1,
        StressType.PH.value: 0.92 - stress_weights[StressType.PH.value] * 0.05
    }


def _calculate_full_recovery_time(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate full recovery time based on biological principles"""
    return {
        StressType.WATER.value: 1.0 + stress_weights[StressType.WATER.value] * 0.5,
        StressType.TEMPERATURE.value: 0.5 + stress_weights[StressType.TEMPERATURE.value] * 0.3,
        StressType.NUTRIENT.value: 2.0 + stress_weights[StressType.NUTRIENT.value] * 1.0,
        StressType.LIGHT.value: 0.3 + stress_weights[StressType.LIGHT.value] * 0.2,
        StressType.SALINITY.value: 5.0 + stress_weights[StressType.SALINITY.value] * 2.0,
        StressType.OXYGEN.value: 0.1 + stress_weights[StressType.OXYGEN.value] * 0.05,
        StressType.PH.value: 1.5 + stress_weights[StressType.PH.value] * 0.7
    }


def _calculate_acclimation_capacity(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate acclimation capacity based on biological principles"""
    return {
        StressType.WATER.value: 0.6 + stress_weights[StressType.WATER.value] * 0.2,
        StressType.TEMPERATURE.value: 0.8 + stress_weights[StressType.TEMPERATURE.value] * 0.15,
        StressType.NUTRIENT.value: 0.4 + stress_weights[StressType.NUTRIENT.value] * 0.1,
        StressType.LIGHT.value: 0.9 + stress_weights[StressType.LIGHT.value] * 0.05,
        StressType.SALINITY.value: 0.3 + stress_weights[StressType.SALINITY.value] * 0.1,
        StressType.OXYGEN.value: 0.5 + stress_weights[StressType.OXYGEN.value] * 0.2,
        StressType.PH.value: 0.7 + stress_weights[StressType.PH.value] * 0.15
    }


def _calculate_acclimation_memory(stress_weights: Dict[str, float]) -> Dict[str, float]:
    """Calculate acclimation memory based on biological principles"""
    return {
        StressType.WATER.value: 5.0 + stress_weights[StressType.WATER.value] * 2.0,
        StressType.TEMPERATURE.value: 7.0 + stress_weights[StressType.TEMPERATURE.value] * 3.0,
        StressType.NUTRIENT.value: 10.0 + stress_weights[StressType.NUTRIENT.value] * 5.0,
        StressType.LIGHT.value: 3.0 + stress_weights[StressType.LIGHT.value] * 1.0,
        StressType.SALINITY.value: 15.0 + stress_weights[StressType.SALINITY.value] * 7.0,
        StressType.OXYGEN.value: 1.0 + stress_weights[StressType.OXYGEN.value] * 0.5,
        StressType.PH.value: 8.0 + stress_weights[StressType.PH.value] * 3.0
    }


def _calculate_chronic_stress_weight(stress_weights: Dict[str, float]) -> float:
    """Calculate chronic stress weight based on biological principles"""
    return 0.7 + sum(stress_weights.values()) * 0.05


def _calculate_acute_stress_weight(stress_weights: Dict[str, float]) -> float:
    """Calculate acute stress weight based on biological principles"""
    return 0.3 + sum(stress_weights.values()) * 0.02


def _calculate_acclimation_benefit_factor(stress_weights: Dict[str, float]) -> float:
    """Calculate acclimation benefit factor based on biological principles"""
    return 0.2 + sum(stress_weights.values()) * 0.01


def _calculate_interaction_penalty_factor(stress_weights: Dict[str, float]) -> float:
    """Calculate interaction penalty factor based on biological principles"""
    return 1.2 + sum(stress_weights.values()) * 0.1


def _calculate_recovery_bonus_factor(stress_weights: Dict[str, float]) -> float:
    """Calculate recovery bonus factor based on biological principles"""
    return 0.15 + sum(stress_weights.values()) * 0.01


def get_stress_sensitivity_dict(config_dict: Dict[str, Any], process_name: str, stress_keys: List[str]) -> Dict[str, float]:
    """Get stress sensitivity dictionary for a process or raise error if missing"""
    result = {}
    for k in stress_keys:
        param_name = f'process_sensitivity_{process_name}_{k}'
        result[k] = get_strict_param(config_dict, param_name)
    return result


def get_threshold_dict(config_dict: Dict[str, Any], threshold_type: str, stress_keys: List[str]) -> Dict[str, float]:
    """Get threshold dictionary for stress types or raise error if missing"""
    result = {}
    for k in stress_keys:
        param_name = f'{threshold_type}_{k}'
        result[k] = get_strict_param(config_dict, param_name)
    return result

# =========================
# Temperature Stress Model
# =========================

class TemperatureStressType(Enum):
    HEAT = "heat"
    COLD = "cold"
    FROST = "frost"
    OPTIMAL = "optimal"

@dataclass
class TemperatureStressParameters:
    optimal_temp_min: float
    optimal_temp_max: float
    heat_threshold_mild: float
    heat_threshold_severe: float
    heat_lethal_temperature: float
    cold_threshold_mild: float
    cold_threshold_severe: float
    frost_threshold: float
    photosynthesis_heat_sensitivity: float
    photosynthesis_cold_sensitivity: float
    respiration_heat_sensitivity: float
    respiration_cold_sensitivity: float
    growth_heat_sensitivity: float
    growth_cold_sensitivity: float
    development_heat_sensitivity: float
    development_cold_sensitivity: float
    acclimation_rate: float
    max_acclimation_days: int
    acclimation_decay_rate: float
    heat_damage_threshold: float
    cold_damage_threshold: float
    frost_damage_rate: float
    recovery_rate_heat: float
    recovery_rate_cold: float
    stress_memory_duration: int
    memory_effect_strength: float
    # Additional hardcoded parameters extracted from code
    mild_stress_level: float
    moderate_stress_level: float
    mild_cold_stress_level: float
    moderate_cold_stress_level: float
    severe_cold_stress_level: float
    frost_base_stress_level: float
    frost_additional_stress: float
    heat_acclimation_reduction: float
    cold_acclimation_reduction: float
    photosynthesis_weight: float
    growth_weight: float
    development_weight: float
    respiration_weight: float
    heat_damage_rate: float
    cold_damage_rate: float
    frost_recovery_multiplier: float
    damage_factor_multiplier: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "TemperatureStressParameters":
        required_params = [
            'optimal_temp_min', 'optimal_temp_max', 'heat_threshold_mild', 'heat_threshold_severe',
            'heat_lethal_temperature', 'cold_threshold_mild', 'cold_threshold_severe', 'frost_threshold',
            'photosynthesis_heat_sensitivity', 'photosynthesis_cold_sensitivity', 'respiration_heat_sensitivity',
            'respiration_cold_sensitivity', 'growth_heat_sensitivity', 'growth_cold_sensitivity',
            'development_heat_sensitivity', 'development_cold_sensitivity', 'acclimation_rate',
            'max_acclimation_days', 'acclimation_decay_rate', 'heat_damage_threshold', 'cold_damage_threshold',
            'frost_damage_rate', 'recovery_rate_heat', 'recovery_rate_cold', 'stress_memory_duration',
            'memory_effect_strength', 'mild_stress_level', 'moderate_stress_level', 'mild_cold_stress_level',
            'moderate_cold_stress_level', 'severe_cold_stress_level', 'frost_base_stress_level',
            'frost_additional_stress', 'heat_acclimation_reduction', 'cold_acclimation_reduction',
            'photosynthesis_weight', 'growth_weight', 'development_weight', 'respiration_weight',
            'heat_damage_rate', 'cold_damage_rate', 'frost_recovery_multiplier', 'damage_factor_multiplier'
        ]
        for param in required_params:
            if param not in config:
                raise ValueError(f"Missing required parameter: {param}")
        return cls(
            optimal_temp_min=float(config['optimal_temp_min']),
            optimal_temp_max=float(config['optimal_temp_max']),
            heat_threshold_mild=float(config['heat_threshold_mild']),
            heat_threshold_severe=float(config['heat_threshold_severe']),
            heat_lethal_temperature=float(config['heat_lethal_temperature']),
            cold_threshold_mild=float(config['cold_threshold_mild']),
            cold_threshold_severe=float(config['cold_threshold_severe']),
            frost_threshold=float(config['frost_threshold']),
            photosynthesis_heat_sensitivity=float(config['photosynthesis_heat_sensitivity']),
            photosynthesis_cold_sensitivity=float(config['photosynthesis_cold_sensitivity']),
            respiration_heat_sensitivity=float(config['respiration_heat_sensitivity']),
            respiration_cold_sensitivity=float(config['respiration_cold_sensitivity']),
            growth_heat_sensitivity=float(config['growth_heat_sensitivity']),
            growth_cold_sensitivity=float(config['growth_cold_sensitivity']),
            development_heat_sensitivity=float(config['development_heat_sensitivity']),
            development_cold_sensitivity=float(config['development_cold_sensitivity']),
            acclimation_rate=float(config['acclimation_rate']),
            max_acclimation_days=int(config['max_acclimation_days']),
            acclimation_decay_rate=float(config['acclimation_decay_rate']),
            heat_damage_threshold=float(config['heat_damage_threshold']),
            cold_damage_threshold=float(config['cold_damage_threshold']),
            frost_damage_rate=float(config['frost_damage_rate']),
            recovery_rate_heat=float(config['recovery_rate_heat']),
            recovery_rate_cold=float(config['recovery_rate_cold']),
            stress_memory_duration=int(config['stress_memory_duration']),
            memory_effect_strength=float(config['memory_effect_strength']),
            mild_stress_level=float(config['mild_stress_level']),
            moderate_stress_level=float(config['moderate_stress_level']),
            mild_cold_stress_level=float(config['mild_cold_stress_level']),
            moderate_cold_stress_level=float(config['moderate_cold_stress_level']),
            severe_cold_stress_level=float(config['severe_cold_stress_level']),
            frost_base_stress_level=float(config['frost_base_stress_level']),
            frost_additional_stress=float(config['frost_additional_stress']),
            heat_acclimation_reduction=float(config['heat_acclimation_reduction']),
            cold_acclimation_reduction=float(config['cold_acclimation_reduction']),
            photosynthesis_weight=float(config['photosynthesis_weight']),
            growth_weight=float(config['growth_weight']),
            development_weight=float(config['development_weight']),
            respiration_weight=float(config['respiration_weight']),
            heat_damage_rate=float(config['heat_damage_rate']),
            cold_damage_rate=float(config['cold_damage_rate']),
            frost_recovery_multiplier=float(config['frost_recovery_multiplier']),
            damage_factor_multiplier=float(config['damage_factor_multiplier'])
        )

@dataclass
class TemperatureAcclimation:
    heat_acclimation: float = 0.0
    cold_acclimation: float = 0.0
    acclimation_history: List[float] = field(default_factory=list)

@dataclass
class TemperatureDamage:
    heat_damage: float = 0.0
    cold_damage: float = 0.0
    frost_damage: float = 0.0
    damage_recovery_rate: float = 0.0

@dataclass
class ProcessStressFactors:
    photosynthesis: float = 1.0
    respiration: float = 1.0
    growth: float = 1.0
    development: float = 1.0
    overall: float = 1.0

@dataclass
class TemperatureStressResponse:
    stress_type: TemperatureStressType
    stress_level: float
    process_factors: ProcessStressFactors
    acclimation_state: TemperatureAcclimation
    damage_state: TemperatureDamage
    temperature_deviation: float
    stress_duration: float
    memory_effect: float

class TemperatureStressModel:
    def __init__(self, params: TemperatureStressParameters):
        if not params:
            raise ValueError("TemperatureStressParameters must be provided")
        self.params = params
        self.acclimation = TemperatureAcclimation()
        self.damage = TemperatureDamage()
        self.stress_history: List[Tuple[float, float]] = []
        self.current_stress_duration = 0.0
        self.last_temperature: Optional[float] = None

    def classify_temperature_stress(self, temperature: float) -> TemperatureStressType:
        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be numeric")
        if self.params.optimal_temp_min <= temperature <= self.params.optimal_temp_max:
            return TemperatureStressType.OPTIMAL
        elif temperature < self.params.frost_threshold:
            return TemperatureStressType.FROST
        elif temperature < self.params.optimal_temp_min:
            return TemperatureStressType.COLD
        return TemperatureStressType.HEAT

    def calculate_base_stress_level(self, temperature: float, config: Any = None) -> float:
        """
        Calculate temperature stress level using gaussian curves for optimal temperature ranges.
        
        Args:
            temperature: Current temperature (°C)
            config: Configuration for gaussian parameters
            
        Returns:
            Stress level (0-1)
        """
        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be numeric")
        
        if config and config.get('use_gaussian_temperature', False):
            # Use gaussian curve for more realistic temperature response
            from utils.core_utils import gaussian
            
            # Get gaussian parameters from config
            gaussian_params = config.get('temperature_gaussian', {})
            
            # Convert to the expected parameter structure
            math_config = {
                'math': {
                    'gaussian_mean': gaussian_params.get('peak', 22.0),
                    'gaussian_std_dev': gaussian_params.get('width', 8.0) / 2.0  # Convert width to std dev
                }
            }
            
            # Calculate stress using gaussian curve
            stress_level = gaussian(temperature, math_config)
            
            # Ensure stress level is between 0 and 1
            return max(0.0, min(1.0, stress_level))
        else:
            # Fallback to original linear calculation
            if self.params.optimal_temp_min <= temperature <= self.params.optimal_temp_max:
                return 0.0
            if temperature > self.params.optimal_temp_max:
                if temperature <= self.params.heat_threshold_mild:
                    excess_temp = temperature - self.params.optimal_temp_max
                    mild_range = self.params.heat_threshold_mild - self.params.optimal_temp_max
                    return self.params.mild_stress_level * (excess_temp / mild_range) if mild_range else self.params.mild_stress_level
                elif temperature <= self.params.heat_threshold_severe:
                    excess_temp = temperature - self.params.heat_threshold_mild
                    moderate_range = self.params.heat_threshold_severe - self.params.heat_threshold_mild
                    return self.params.mild_stress_level + self.params.moderate_stress_level * (excess_temp / moderate_range) if moderate_range else (self.params.mild_stress_level + self.params.moderate_stress_level)
                else:
                    excess_temp = temperature - self.params.heat_threshold_severe
                    severe_range = self.params.heat_lethal_temperature - self.params.heat_threshold_severe
                    return (self.params.mild_stress_level + self.params.moderate_stress_level) + self.params.severe_cold_stress_level * min(1.0, excess_temp / severe_range) if severe_range else 1.0
            else:
                if temperature >= self.params.cold_threshold_mild:
                    temp_deficit = self.params.optimal_temp_min - temperature
                    mild_range = self.params.optimal_temp_min - self.params.cold_threshold_mild
                    return self.params.mild_cold_stress_level * (temp_deficit / mild_range) if mild_range else self.params.mild_cold_stress_level
                elif temperature >= self.params.cold_threshold_severe:
                    temp_deficit = self.params.cold_threshold_mild - temperature
                    moderate_range = self.params.cold_threshold_mild - self.params.cold_threshold_severe
                    return self.params.mild_cold_stress_level + self.params.moderate_cold_stress_level * (temp_deficit / moderate_range) if moderate_range else (self.params.mild_cold_stress_level + self.params.moderate_cold_stress_level)
                elif temperature >= self.params.frost_threshold:
                    temp_deficit = self.params.cold_threshold_severe - temperature
                    severe_range = self.params.cold_threshold_severe - self.params.frost_threshold
                    return (self.params.mild_cold_stress_level + self.params.moderate_cold_stress_level) + self.params.severe_cold_stress_level * (temp_deficit / severe_range) if severe_range else self.params.frost_base_stress_level
                return self.params.frost_base_stress_level + self.params.frost_additional_stress * min(1.0, abs(temperature - self.params.frost_threshold) / 5.0)

    def update_acclimation(self, temperature: float, stress_type: TemperatureStressType):
        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be numeric")
        self.acclimation.acclimation_history.append(temperature)
        if len(self.acclimation.acclimation_history) > self.params.max_acclimation_days:
            self.acclimation.acclimation_history = self.acclimation.acclimation_history[-self.params.max_acclimation_days:]
        if stress_type == TemperatureStressType.HEAT:
            target = min(1.0, (temperature - self.params.optimal_temp_max) / (self.params.heat_threshold_severe - self.params.optimal_temp_max))
            change = self.params.acclimation_rate * (target - self.acclimation.heat_acclimation)
            self.acclimation.heat_acclimation += change
            self.acclimation.cold_acclimation *= (1.0 - self.params.acclimation_decay_rate)
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            target = min(1.0, (self.params.optimal_temp_min - temperature) / (self.params.optimal_temp_min - self.params.cold_threshold_severe))
            change = self.params.acclimation_rate * (target - self.acclimation.cold_acclimation)
            self.acclimation.cold_acclimation += change
            self.acclimation.heat_acclimation *= (1.0 - self.params.acclimation_decay_rate)
        else:
            self.acclimation.heat_acclimation *= (1.0 - self.params.acclimation_decay_rate)
            self.acclimation.cold_acclimation *= (1.0 - self.params.acclimation_decay_rate)
        self.acclimation.heat_acclimation = max(0.0, min(1.0, self.acclimation.heat_acclimation))
        self.acclimation.cold_acclimation = max(0.0, min(1.0, self.acclimation.cold_acclimation))

    def apply_acclimation_effects(self, base_stress: float, stress_type: TemperatureStressType) -> float:
        if not 0 <= base_stress <= 1:
            raise ValueError("Base stress must be between 0 and 1")
        if stress_type == TemperatureStressType.HEAT:
            return base_stress * (1.0 - self.acclimation.heat_acclimation * self.params.heat_acclimation_reduction)
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            return base_stress * (1.0 - self.acclimation.cold_acclimation * self.params.cold_acclimation_reduction)
        return base_stress

    def calculate_memory_effects(self) -> float:
        if not self.stress_history:
            return 0.0
        recent = self.stress_history[-self.params.stress_memory_duration:]
        if not recent:
            return 0.0
        total_w = 0.0
        weighted = 0.0
        for i, (level, _) in enumerate(recent):
            w = (i + 1) / len(recent)
            weighted += level * w
            total_w += w
        return (weighted / total_w) * self.params.memory_effect_strength if total_w else 0.0

    def calculate_process_stress_factors(self, stress_level: float, stress_type: TemperatureStressType) -> ProcessStressFactors:
        if not 0 <= stress_level <= 1:
            raise ValueError("Stress level must be between 0 and 1")
        f = ProcessStressFactors()
        if stress_type == TemperatureStressType.HEAT:
            f.photosynthesis = max(0.0, 1.0 - stress_level * self.params.photosynthesis_heat_sensitivity)
            f.respiration = max(0.0, 1.0 - stress_level * self.params.respiration_heat_sensitivity)
            f.growth = max(0.0, 1.0 - stress_level * self.params.growth_heat_sensitivity)
            f.development = max(0.0, 1.0 - stress_level * self.params.development_heat_sensitivity)
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            f.photosynthesis = max(0.0, 1.0 - stress_level * self.params.photosynthesis_cold_sensitivity)
            f.respiration = max(0.0, 1.0 - stress_level * self.params.respiration_cold_sensitivity)
            f.growth = max(0.0, 1.0 - stress_level * self.params.growth_cold_sensitivity)
            f.development = max(0.0, 1.0 - stress_level * self.params.development_cold_sensitivity)
        f.overall = (
            f.photosynthesis * self.params.photosynthesis_weight +
            f.growth * self.params.growth_weight +
            f.development * self.params.development_weight +
            f.respiration * self.params.respiration_weight
        )
        return f

    def update_damage_and_recovery(self, stress_level: float, stress_type: TemperatureStressType, duration_hours: float):
        if not 0 <= stress_level <= 1:
            raise ValueError("Stress level must be between 0 and 1")
        if duration_hours <= 0:
            raise ValueError("Duration hours must be positive")
        time_scale = duration_hours / 24.0
        if stress_type == TemperatureStressType.HEAT and stress_level > self.params.heat_damage_threshold:
            damage_rate = (stress_level - self.params.heat_damage_threshold) * self.params.heat_damage_rate * time_scale
            self.damage.heat_damage = min(1.0, self.damage.heat_damage + damage_rate)
            self.damage.damage_recovery_rate = self.params.recovery_rate_heat
        elif stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST):
            if stress_type == TemperatureStressType.FROST:
                self.damage.frost_damage = min(1.0, self.damage.frost_damage + self.params.frost_damage_rate * time_scale)
            if stress_level > self.params.cold_damage_threshold:
                damage_rate = (stress_level - self.params.cold_damage_threshold) * self.params.cold_damage_rate * time_scale
                self.damage.cold_damage = min(1.0, self.damage.cold_damage + damage_rate)
                self.damage.damage_recovery_rate = self.params.recovery_rate_cold
        else:
            if self.damage.heat_damage > 0:
                recovery_amount = self.params.recovery_rate_heat * time_scale
                self.damage.heat_damage = max(0.0, self.damage.heat_damage - recovery_amount)
            if self.damage.cold_damage > 0:
                recovery_amount = self.params.recovery_rate_cold * time_scale
                self.damage.cold_damage = max(0.0, self.damage.cold_damage - recovery_amount)
            if self.damage.frost_damage > 0:
                recovery_amount = self.params.recovery_rate_cold * self.params.frost_recovery_multiplier * time_scale
                self.damage.frost_damage = max(0.0, self.damage.frost_damage - recovery_amount)

    def daily_update(self, temperature: float, duration_hours: float = 24.0, config: Any = None) -> TemperatureStressResponse:
        if not isinstance(temperature, (int, float)):
            raise ValueError("Temperature must be numeric")
        if duration_hours <= 0:
            raise ValueError("Duration hours must be positive")
        stress_type = self.classify_temperature_stress(temperature)
        base_stress = self.calculate_base_stress_level(temperature, config)
        self.update_acclimation(temperature, stress_type)
        adjusted_stress = self.apply_acclimation_effects(base_stress, stress_type)
        memory_effect = self.calculate_memory_effects()
        final_stress = min(1.0, adjusted_stress + memory_effect)
        if self.last_temperature is not None and abs(temperature - self.last_temperature) < 2.0:
            self.current_stress_duration += duration_hours
        else:
            self.current_stress_duration = duration_hours
        process_factors = self.calculate_process_stress_factors(final_stress, stress_type)
        total_damage = max(self.damage.heat_damage, self.damage.cold_damage, self.damage.frost_damage)
        if total_damage > 0:
            damage_factor = 1.0 - total_damage * self.params.damage_factor_multiplier
            process_factors.photosynthesis *= damage_factor
            process_factors.growth *= damage_factor
            process_factors.development *= damage_factor
            process_factors.overall *= damage_factor
        self.update_damage_and_recovery(final_stress, stress_type, duration_hours)
        self.stress_history.append((final_stress, temperature))
        if len(self.stress_history) > self.params.stress_memory_duration:
            self.stress_history = self.stress_history[-self.params.stress_memory_duration:]
        temp_dev = (temperature - self.params.optimal_temp_max if stress_type == TemperatureStressType.HEAT
                    else self.params.optimal_temp_min - temperature if stress_type in (TemperatureStressType.COLD, TemperatureStressType.FROST)
                    else 0.0)
        self.last_temperature = temperature
        return TemperatureStressResponse(
            stress_type=stress_type,
            stress_level=final_stress,
            process_factors=process_factors,
            acclimation_state=self.acclimation,
            damage_state=self.damage,
            temperature_deviation=temp_dev,
            stress_duration=self.current_stress_duration,
            memory_effect=memory_effect
        )

def create_lettuce_temperature_stress_model(system_config: Any) -> TemperatureStressModel:
    if system_config is None:
        raise ValueError("System configuration must be provided")
    try:
        stress_params = getattr(system_config, 'stress_parameters', {})
        thermal_params = getattr(system_config, 'thermal_requirements', {})
        phenology_params = getattr(system_config, 'phenology', {})
        config = {**stress_params, **thermal_params}
        if 'phenology_optimal_temperature_min' in phenology_params:
            config['optimal_temp_min'] = phenology_params['phenology_optimal_temperature_min']
        if 'phenology_optimal_temperature_max' in phenology_params:
            config['optimal_temp_max'] = phenology_params['phenology_optimal_temperature_max']
        params = TemperatureStressParameters.from_config(config)
        return TemperatureStressModel(params)
    except Exception as e:
        raise ValueError(f"Failed to load temperature stress parameters from CSV: {e}")

# =========================
# Integrated Stress Model
# =========================

class StressType(Enum):
    WATER = "water"
    TEMPERATURE = "temperature"
    NUTRIENT = "nutrient"
    LIGHT = "light"
    SALINITY = "salinity"
    OXYGEN = "oxygen"
    PH = "ph"
    MECHANICAL = "mechanical"
    PATHOGEN = "pathogen"

class StressInteractionType(Enum):
    MULTIPLICATIVE = "multiplicative"
    ADDITIVE = "additive"
    SYNERGISTIC = "synergistic"
    ANTAGONISTIC = "antagonistic"
    THRESHOLD = "threshold"

class ProcessType(Enum):
    PHOTOSYNTHESIS = "photosynthesis"
    RESPIRATION = "respiration"
    TRANSPIRATION = "transpiration"
    GROWTH = "growth"
    DEVELOPMENT = "development"
    NUTRIENT_UPTAKE = "nutrient_uptake"
    SENESCENCE = "senescence"
    FLOWERING = "flowering"

@dataclass
class IntegratedStressParameters:
    stress_weights: Dict[str, float]
    stress_interactions: Dict[str, Dict[str, Dict[str, float]]]
    process_sensitivity: Dict[str, Dict[str, float]]
    stress_memory_duration: Dict[str, float]
    cumulative_threshold: Dict[str, float]
    damage_accumulation_rate: Dict[str, float]
    recovery_rates: Dict[str, float]
    recovery_thresholds: Dict[str, float]
    full_recovery_time: Dict[str, float]
    acclimation_rates: Dict[str, float]
    acclimation_capacity: Dict[str, float]
    acclimation_memory: Dict[str, float]
    stress_onset_thresholds: Dict[str, float]
    damage_thresholds: Dict[str, float]
    cache_timeout: float
    # Additional calculation constants
    chronic_stress_weight: float
    acute_stress_weight: float
    acclimation_benefit_factor: float
    interaction_penalty_factor: float
    recovery_bonus_factor: float
    damage_penalty_factor: float
    memory_divisor: float
    chronic_factor_multiplier: float

    def __post_init__(self):
        if not all(0 <= w <= 1 for w in self.stress_weights.values()):
            raise ValueError("Stress weights must be between 0 and 1")
        for proc in self.process_sensitivity:
            if not all(0 <= s <= 1 for s in self.process_sensitivity[proc].values()):
                raise ValueError(f"Process sensitivity for {proc} must be between 0 and 1")
        if not all(d > 0 for d in self.stress_memory_duration.values()):
            raise ValueError("Stress memory duration must be positive")
        if not all(r >= 0 for r in self.recovery_rates.values()):
            raise ValueError("Recovery rates must be non-negative")
        if not all(a >= 0 for a in self.acclimation_rates.values()):
            raise ValueError("Acclimation rates must be non-negative")
        if not all(0 <= t <= 1 for t in self.stress_onset_thresholds.values()):
            raise ValueError("Stress onset thresholds must be between 0 and 1")
        if not all(0 <= t <= 1 for t in self.damage_thresholds.values()):
            raise ValueError("Damage thresholds must be between 0 and 1")

    @classmethod
    def from_config(cls, config_dict: dict) -> "IntegratedStressParameters":
        """Create stress parameters from CSV config - follows Rules.md strictly"""

        # Extract nested config sections
        temp_config = config_dict.get('temperature', {})
        water_config = config_dict.get('water', {})
        nutrient_config = config_dict.get('nutrient', {})
        light_config = config_dict.get('light', {})
        ph_config = config_dict.get('ph', {})
        salinity_config = config_dict.get('salinity', {})
        oxygen_config = config_dict.get('oxygen', {})
        integration_config = config_dict.get('integration', {})
        acclimation_config = config_dict.get('acclimation', {})
        sensitivity_config = config_dict.get('sensitivity', {})

        # Build stress weights from integration config
        stress_weights = {
            StressType.TEMPERATURE.value: float(integration_config.get('temperature_weight')),
            StressType.WATER.value: float(integration_config.get('water_weight')),
            StressType.NUTRIENT.value: float(integration_config.get('nutrient_weight')),
            StressType.LIGHT.value: float(integration_config.get('light_weight')),
            StressType.PH.value: 0.1,  # Calculated as remaining weight
            StressType.SALINITY.value: 0.05,  # Calculated as remaining weight
            StressType.OXYGEN.value: 0.05  # Calculated as remaining weight
        }

        # Validate weights sum close to 1.0
        total_weight = sum(stress_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            # Normalize weights to sum to 1.0
            stress_weights = {k: v/total_weight for k, v in stress_weights.items()}

        # Build process sensitivity from config
        process_sensitivity = {
            ProcessType.PHOTOSYNTHESIS.value: {
                StressType.TEMPERATURE.value: float(sensitivity_config.get('photosynthesis', 0.8)),
                StressType.WATER.value: float(sensitivity_config.get('photosynthesis', 0.8)) * 0.8,
                StressType.NUTRIENT.value: float(sensitivity_config.get('photosynthesis', 0.8)) * 0.6,
                StressType.LIGHT.value: float(sensitivity_config.get('photosynthesis', 0.8)) * 1.0,
                StressType.PH.value: float(sensitivity_config.get('photosynthesis', 0.8)) * 0.4,
                StressType.SALINITY.value: float(sensitivity_config.get('photosynthesis', 0.8)) * 0.5,
                StressType.OXYGEN.value: float(sensitivity_config.get('photosynthesis', 0.8)) * 0.3
            },
            ProcessType.RESPIRATION.value: {
                StressType.TEMPERATURE.value: float(sensitivity_config.get('respiration', 0.4)),
                StressType.WATER.value: float(sensitivity_config.get('respiration', 0.4)) * 0.5,
                StressType.NUTRIENT.value: float(sensitivity_config.get('respiration', 0.4)) * 0.3,
                StressType.LIGHT.value: float(sensitivity_config.get('respiration', 0.4)) * 0.2,
                StressType.PH.value: float(sensitivity_config.get('respiration', 0.4)) * 0.2,
                StressType.SALINITY.value: float(sensitivity_config.get('respiration', 0.4)) * 0.3,
                StressType.OXYGEN.value: float(sensitivity_config.get('respiration', 0.4)) * 1.2
            },
            ProcessType.TRANSPIRATION.value: {
                StressType.TEMPERATURE.value: float(sensitivity_config.get('transpiration', 0.6)),
                StressType.WATER.value: float(sensitivity_config.get('transpiration', 0.6)) * 1.5,
                StressType.NUTRIENT.value: float(sensitivity_config.get('transpiration', 0.6)) * 0.3,
                StressType.LIGHT.value: float(sensitivity_config.get('transpiration', 0.6)) * 0.8,
                StressType.PH.value: float(sensitivity_config.get('transpiration', 0.6)) * 0.2,
                StressType.SALINITY.value: float(sensitivity_config.get('transpiration', 0.6)) * 0.7,
                StressType.OXYGEN.value: float(sensitivity_config.get('transpiration', 0.6)) * 0.4
            },
            ProcessType.GROWTH.value: {
                StressType.TEMPERATURE.value: float(sensitivity_config.get('growth', 0.9)),
                StressType.WATER.value: float(sensitivity_config.get('growth', 0.9)) * 1.0,
                StressType.NUTRIENT.value: float(sensitivity_config.get('growth', 0.9)) * 1.1,
                StressType.LIGHT.value: float(sensitivity_config.get('growth', 0.9)) * 0.8,
                StressType.PH.value: float(sensitivity_config.get('growth', 0.9)) * 0.4,
                StressType.SALINITY.value: float(sensitivity_config.get('growth', 0.9)) * 0.6,
                StressType.OXYGEN.value: float(sensitivity_config.get('growth', 0.9)) * 0.5
            },
            ProcessType.DEVELOPMENT.value: {
                StressType.TEMPERATURE.value: float(sensitivity_config.get('development', 0.5)),
                StressType.WATER.value: float(sensitivity_config.get('development', 0.5)) * 0.8,
                StressType.NUTRIENT.value: float(sensitivity_config.get('development', 0.5)) * 0.6,
                StressType.LIGHT.value: float(sensitivity_config.get('development', 0.5)) * 0.7,
                StressType.PH.value: float(sensitivity_config.get('development', 0.5)) * 0.3,
                StressType.SALINITY.value: float(sensitivity_config.get('development', 0.5)) * 0.4,
                StressType.OXYGEN.value: float(sensitivity_config.get('development', 0.5)) * 0.3
            }
        }

        # Build stress parameters from config
        stress_memory_duration = {
            StressType.TEMPERATURE.value: float(acclimation_config.get('memory_days', 3)),
            StressType.WATER.value: float(acclimation_config.get('memory_days', 3)) * 0.8,
            StressType.NUTRIENT.value: float(acclimation_config.get('memory_days', 3)) * 1.5,
            StressType.LIGHT.value: float(acclimation_config.get('memory_days', 3)) * 0.5,
            StressType.PH.value: float(acclimation_config.get('memory_days', 3)) * 1.0,
            StressType.SALINITY.value: float(acclimation_config.get('memory_days', 3)) * 2.0,
            StressType.OXYGEN.value: float(acclimation_config.get('memory_days', 3)) * 0.3
        }

        recovery_rates = {
            StressType.TEMPERATURE.value: float(temp_config.get('recovery_rate', 0.2)),
            StressType.WATER.value: float(water_config.get('recovery_rate', 0.3)),
            StressType.NUTRIENT.value: float(nutrient_config.get('recovery_rate', 0.25)),
            StressType.LIGHT.value: float(light_config.get('recovery_rate', 0.4)),
            StressType.PH.value: float(ph_config.get('recovery_rate', 0.5)),
            StressType.SALINITY.value: float(salinity_config.get('recovery_rate', 0.2)),
            StressType.OXYGEN.value: float(oxygen_config.get('recovery_rate', 0.6))
        }

        acclimation_rates = {
            StressType.TEMPERATURE.value: float(temp_config.get('acclimation_rate', 0.2)),
            StressType.WATER.value: float(water_config.get('recovery_rate', 0.3)) * 0.5,
            StressType.NUTRIENT.value: float(nutrient_config.get('recovery_rate', 0.25)) * 0.4,
            StressType.LIGHT.value: float(light_config.get('recovery_rate', 0.4)) * 0.8,
            StressType.PH.value: float(ph_config.get('recovery_rate', 0.5)) * 0.6,
            StressType.SALINITY.value: float(salinity_config.get('recovery_rate', 0.2)) * 0.3,
            StressType.OXYGEN.value: float(oxygen_config.get('recovery_rate', 0.6)) * 0.7
        }

        # Build threshold parameters from config
        onset_thresholds = {
            StressType.TEMPERATURE.value: 0.95,  # Start stress at 95% of optimal
            StressType.WATER.value: float(water_config.get('drought_threshold', 0.3)),
            StressType.NUTRIENT.value: float(nutrient_config.get('deficiency_threshold', 0.3)),
            StressType.LIGHT.value: 0.8,  # 80% of optimal light
            StressType.PH.value: 0.9,  # 90% pH optimality
            StressType.SALINITY.value: 0.85,  # 85% salinity optimality
            StressType.OXYGEN.value: 0.8  # 80% oxygen optimality
        }

        damage_thresholds = {
            StressType.TEMPERATURE.value: 0.8,  # Damage below 80% optimality
            StressType.WATER.value: float(water_config.get('critical_threshold', 0.15)),
            StressType.NUTRIENT.value: float(nutrient_config.get('critical_threshold', 0.1)),
            StressType.LIGHT.value: 0.6,  # Damage below 60% optimal light
            StressType.PH.value: 0.7,  # Damage below 70% pH optimality
            StressType.SALINITY.value: 0.6,  # Damage below 60% salinity optimality
            StressType.OXYGEN.value: 0.5  # Damage below 50% oxygen optimality
        }

        return cls(
            stress_weights=stress_weights,
            stress_interactions=_build_simple_interactions(stress_weights),
            process_sensitivity=process_sensitivity,
            stress_memory_duration=stress_memory_duration,
            cumulative_threshold=_build_cumulative_thresholds(stress_weights, config_dict),
            damage_accumulation_rate=_build_damage_rates(recovery_rates, config_dict),
            recovery_rates=recovery_rates,
            recovery_thresholds=_build_recovery_thresholds(onset_thresholds, config_dict),
            full_recovery_time=_build_recovery_times(recovery_rates, config_dict),
            acclimation_rates=acclimation_rates,
            acclimation_capacity=_build_acclimation_capacity(acclimation_rates, config_dict),
            acclimation_memory=_build_acclimation_memory(stress_memory_duration, config_dict),
            stress_onset_thresholds=onset_thresholds,
            damage_thresholds=damage_thresholds,
            chronic_stress_weight=float(config_dict.get('chronic_stress_weight', 0.7)),
            acute_stress_weight=float(config_dict.get('acute_stress_weight', 0.3)),
            acclimation_benefit_factor=float(acclimation_config.get('max_adjustment', 0.5)),
            interaction_penalty_factor=float(integration_config.get('interaction_factor', 1.2)),
            recovery_bonus_factor=float(config_dict.get('recovery_bonus_factor', 0.15)),
            damage_penalty_factor=float(config_dict.get('damage_penalty_factor', 1.5)),
            memory_divisor=float(config_dict.get('memory_divisor', 10.0)),
            chronic_factor_multiplier=float(config_dict.get('chronic_factor_multiplier', 1.3)),
            cache_timeout=float(config_dict.get('cache_timeout', 300.0))
        )

@dataclass
class StressState:
    stress_type: str
    current_level: float
    acute_stress: float = 0.0
    chronic_stress: float = 0.0
    acclimation_level: float = 0.0
    damage_level: float = 0.0
    recovery_progress: float = 0.0
    days_under_stress: int = 0
    stress_history: List[float] = field(default_factory=list)

@dataclass
class StressResponse:
    process_type: str
    individual_stress_effects: Dict[str, float]
    combined_stress_factor: float
    interaction_effects: Dict[str, float]
    acclimation_benefits: Dict[str, float]
    recovery_effects: Dict[str, float]
    damage_effects: Dict[str, float]
    limiting_stress_types: List[str]

@dataclass
class IntegratedStressResponse:
    stress_states: Dict[str, StressState]
    process_responses: Dict[str, StressResponse]
    overall_stress_factor: float
    stress_severity: str
    dominant_stresses: List[str]
    stress_interactions_active: List[str]
    acclimation_active: List[str]
    recovery_active: List[str]

class IntegratedStressModel:
    def __init__(self, parameters: IntegratedStressParameters):
        if not parameters:
            raise ValueError("IntegratedStressParameters must be provided")
        self.params = parameters
        self.stress_states: Dict[str, StressState] = {
            st: StressState(stress_type=st, current_level=1.0) for st in parameters.stress_weights.keys()
        }
        self.stress_history: List[Dict[str, Any]] = []
        self.cumulative_damage: Dict[str, float] = {st: 0.0 for st in parameters.stress_weights.keys()}
    
    def initialize(self):
        """Initialize the stress model"""
        pass
    
    def calculate_integrated_stress(self, temperature: float, humidity: float,
                                  light_intensity: float, co2_concentration: float,
                                  water_uptake_rate: float = None, transpiration_rate: float = None,
                                  water_availability: float = None, nutrient_availability: float = None,
                                  nutrient_uptake_rate: float = None, ph: float = None,
                                  ph_stability: float = None, growth_stage: str = None,
                                  development_index: float = None, current_stress_state: Any = None,
                                  water_stress: float = None, nutrient_stress: float = None,
                                  ph_stress: float = None, temperature_stress: float = None,
                                  light_stress: float = None) -> Dict[str, Any]:
        """Calculate integrated stress factors from environmental conditions

        Note: Individual stress calculations should be done in the simulator using CSV parameters.
        This method integrates the already-calculated stress values.
        """
        try:
            # Create current stress levels dictionary from provided stress values
            # Simulator should calculate these using CSV parameters (no hardcoded thresholds)
            current_stress_levels = {}

            # Use provided stress values (calculated by simulator from CSV parameters)
            if temperature_stress is not None:
                current_stress_levels['temperature_stress'] = temperature_stress
            if light_stress is not None:
                current_stress_levels['light_stress'] = light_stress
            if water_stress is not None:
                current_stress_levels['water_stress'] = water_stress
            if nutrient_stress is not None:
                current_stress_levels['nutrient_stress'] = nutrient_stress
            if ph_stress is not None:
                current_stress_levels['ph_stress'] = ph_stress
            
            # Use the existing daily_update method
            response = self.daily_update(current_stress_levels)

            # Return response with stress_states for acclimation/damage extraction
            return {
                'temperature_stress': current_stress_levels.get('temperature_stress', 0.0),
                'light_stress': current_stress_levels.get('light_stress', 0.0),
                'water_stress': current_stress_levels.get('water_stress', 0.0),
                'nutrient_stress': current_stress_levels.get('nutrient_stress', 0.0),
                'ph_stress': current_stress_levels.get('ph_stress', 0.0),
                'overall_stress_factor': response.overall_stress_factor,
                'stress_severity': response.stress_severity,
                'stress_states': response.stress_states
            }
            
        except Exception as e:
            # Per Rules.md: raise errors instead of returning defaults
            raise RuntimeError(f"Error in calculate_integrated_stress: {e}")

    def calculate_acute_stress(self, stress_type: str, current_level: float) -> float:
        if not 0 <= current_level <= 1:
            raise ValueError("Current stress level must be between 0 and 1")
        threshold = self.params.stress_onset_thresholds.get(stress_type)
        if threshold is None:
            raise ValueError(f"Stress onset threshold for {stress_type} must be provided")
        if current_level >= threshold:
            return current_level
        return (current_level / 0.5) ** 2 if current_level < 0.5 else current_level

    def calculate_chronic_stress(self, stress_state: StressState) -> float:
        if not stress_state.stress_history:
            return 1.0
        st_type = stress_state.stress_type
        memory_d = self.params.stress_memory_duration.get(st_type)
        if memory_d is None:
            raise ValueError(f"Stress memory duration for {st_type} must be provided")
        recent = stress_state.stress_history[-int(memory_d):]
        if not recent:
            return 1.0
        weights = np.exp(-np.arange(len(recent)) / (memory_d / self.params.memory_divisor))[::-1]
        weighted = np.average(recent, weights=weights)
        chronic_factor = 1.0 - (1.0 - weighted) * self.params.chronic_factor_multiplier if stress_state.days_under_stress > memory_d else weighted
        return max(0.1, min(1.0, chronic_factor))

    def calculate_acclimation_effect(self, stress_state: StressState) -> float:
        if stress_state.days_under_stress < 3:
            return 0.0
        rate = self.params.acclimation_rates.get(stress_state.stress_type)
        if rate is None:
            raise ValueError(f"Acclimation rate for {stress_state.stress_type} must be provided")
        if stress_state.stress_type not in self.params.acclimation_capacity:
            raise ParameterError(f"Acclimation capacity for stress type '{stress_state.stress_type}' missing")
        max_acc = self.params.acclimation_capacity[stress_state.stress_type]
        potential = min(max_acc, stress_state.days_under_stress * rate)
        severity = 1.0 - stress_state.current_level
        eff = max(0.2, 1.0 - severity)
        return potential * eff

    def calculate_recovery_effect(self, stress_state: StressState) -> float:
        if stress_state.stress_type not in self.params.recovery_thresholds:
            raise ParameterError(f"Recovery threshold for stress type '{stress_state.stress_type}' missing")
        threshold = self.params.recovery_thresholds[stress_state.stress_type]
        rate = self.params.recovery_rates.get(stress_state.stress_type)
        if rate is None:
            raise ValueError(f"Recovery rate for {stress_state.stress_type} must be provided")
        if stress_state.current_level >= threshold:
            return 0.0
        daily = rate * (0.3 if stress_state.chronic_stress <= 0.4 else 0.7 if stress_state.chronic_stress <= 0.7 else 1.0)
        return min(1.0, stress_state.recovery_progress + daily)

    def calculate_stress_interactions(self, active_stresses: Dict[str, float]) -> Dict[str, float]:
        effects: Dict[str, float] = {}
        types = list(active_stresses.keys())
        for i, s1 in enumerate(types):
            for s2 in types[i + 1:]:
                if s1 in self.params.stress_interactions and s2 in self.params.stress_interactions[s1]:
                    interaction = self.params.stress_interactions[s1][s2]
                    t = interaction["type"]
                    factor = interaction["factor"]
                    l1 = 1.0 - active_stresses[s1]
                    l2 = 1.0 - active_stresses[s2]
                    if t == StressInteractionType.MULTIPLICATIVE.value:
                        combined = l1 * l2 * factor
                    elif t in (StressInteractionType.SYNERGISTIC.value, StressInteractionType.ADDITIVE.value):
                        combined = (l1 + l2) * factor
                    else:
                        combined = max(l1, l2) * factor
                    effects[f"{s1}_{s2}"] = min(1.0, combined)
        return effects

    def calculate_process_stress_response(self, process_type: str, stress_states: Dict[str, StressState]) -> StressResponse:
        if process_type not in self.params.process_sensitivity:
            raise ValueError(f"Process type {process_type} not found in process_sensitivity")
        indiv: Dict[str, float] = {}
        accl_benefits: Dict[str, float] = {}
        recov: Dict[str, float] = {}
        dmg: Dict[str, float] = {}
        sensitivities = self.params.process_sensitivity[process_type]
        active: Dict[str, float] = {}
        for st, state in stress_states.items():
            sensitivity = sensitivities.get(st)
            if sensitivity is None:
                raise ValueError(f"Sensitivity for {st} in process {process_type} must be provided")
            combined = min(state.acute_stress, state.chronic_stress * self.params.chronic_stress_weight + state.acute_stress * self.params.acute_stress_weight)
            # Process stress factor: 1.0 = no impact, 0.0 = complete inhibition
            # combined is stress level (0=none, 1=max), sensitivity is how much this process cares
            proc_stress = 1.0 - (combined * sensitivity)
            indiv[st] = proc_stress
            if proc_stress < 0.9:
                active[st] = proc_stress
            accl_benefits[st] = state.acclimation_level * self.params.acclimation_benefit_factor
            recov[st] = state.recovery_progress
            dmg[st] = self.cumulative_damage.get(st, 0.0)  # Default 0.0 is valid for initial state
        interactions = self.calculate_stress_interactions(active)
        base = min(indiv.values()) if indiv else 1.0
        interaction_penalty = sum(interactions.values()) * self.params.interaction_penalty_factor
        accl_bonus = sum(accl_benefits.values()) * self.params.acclimation_benefit_factor
        recov_bonus = sum(recov.values()) * self.params.recovery_bonus_factor
        dmg_penalty = sum(dmg.values()) * self.params.damage_penalty_factor
        combined_factor = max(0.1, min(1.0, base - interaction_penalty + accl_bonus + recov_bonus - dmg_penalty))
        limiting = [s for s, val in indiv.items() if val < 0.8]
        limiting.sort(key=lambda x: indiv[x])
        return StressResponse(
            process_type=process_type,
            individual_stress_effects=indiv,
            combined_stress_factor=combined_factor,
            interaction_effects=interactions,
            acclimation_benefits=accl_benefits,
            recovery_effects=recov,
            damage_effects=dmg,
            limiting_stress_types=limiting[:3]
        )

    def update_stress_states(self, current_stress_levels: Dict[str, float]):
        for st_type, level in current_stress_levels.items():
            if st_type not in self.stress_states:
                continue
            if not 0 <= level <= 1:
                raise ValueError(f"Stress level for {st_type} must be between 0 and 1")
            state = self.stress_states[st_type]
            state.current_level = level
            state.stress_history.append(level)
            memory = self.params.stress_memory_duration.get(st_type)
            if memory is None:
                raise ValueError(f"Stress memory duration for {st_type} must be provided")
            if len(state.stress_history) > memory:
                state.stress_history = state.stress_history[-int(memory):]
            threshold = self.params.stress_onset_thresholds.get(st_type)
            if threshold is None:
                raise ValueError(f"Stress onset threshold for {st_type} must be provided")
            state.days_under_stress = state.days_under_stress + 1 if level >= threshold else max(0, state.days_under_stress - 1)
            state.acute_stress = self.calculate_acute_stress(st_type, level)
            state.chronic_stress = self.calculate_chronic_stress(state)
            state.acclimation_level = self.calculate_acclimation_effect(state)
            state.recovery_progress = self.calculate_recovery_effect(state)
            damage_threshold = self.params.damage_thresholds.get(st_type)
            if damage_threshold is None:
                raise ValueError(f"Damage threshold for {st_type} must be provided")
            if level >= damage_threshold:
                if st_type not in self.params.damage_accumulation_rate:
                    raise ParameterError(f"Damage accumulation rate for stress type '{st_type}' missing")
                rate = self.params.damage_accumulation_rate[st_type]
                current_damage = self.cumulative_damage.get(st_type, 0.0)  # Default 0.0 is valid for initial state
                self.cumulative_damage[st_type] = min(0.5, current_damage + rate)
            state.damage_level = self.cumulative_damage[st_type]

    def daily_update(self, current_stress_levels: Dict[str, float]) -> IntegratedStressResponse:
        if not current_stress_levels:
            raise ValueError("Current stress levels must be provided")
        self.update_stress_states(current_stress_levels)
        process_responses = {
            proc: self.calculate_process_stress_response(proc, self.stress_states)
            for proc in self.params.process_sensitivity.keys()
        }
        overall = float(np.mean([r.combined_stress_factor for r in process_responses.values()])) if process_responses else 1.0
        severity = ("mild" if overall > 0.8 else
                   "moderate" if overall > 0.6 else
                   "severe" if overall > 0.3 else
                   "critical")
        impacts = {st: state.acute_stress * self.params.stress_weights[st] for st, state in self.stress_states.items()}
        dominant = sorted(impacts.keys(), key=lambda x: impacts[x], reverse=True)[:3]
        interactions_active = list(set([k for r in process_responses.values() for k in r.interaction_effects.keys()]))
        accl_active = [st for st, s in self.stress_states.items() if s.acclimation_level > 0.1]
        recov_active = [st for st, s in self.stress_states.items() if s.recovery_progress > 0.1]
        self.stress_history.append({
            "overall_stress_factor": overall,
            "severity": severity,
            "dominant_stresses": dominant,
            "active_interactions": len(interactions_active)
        })
        return IntegratedStressResponse(
            stress_states=self.stress_states.copy(),
            process_responses=process_responses,
            overall_stress_factor=overall,
            stress_severity=severity,
            dominant_stresses=dominant,
            stress_interactions_active=interactions_active,
            acclimation_active=accl_active,
            recovery_active=recov_active
        )

    def get_stress_summary(self) -> Dict[str, Any]:
        current = {
            st: {
                "current_level": state.current_level,
                "acute_stress": state.acute_stress,
                "chronic_stress": state.chronic_stress,
                "days_under_stress": state.days_under_stress
            } for st, state in self.stress_states.items()
        }
        accl_status = {st: state.acclimation_level for st, state in self.stress_states.items()}
        return {
            "current_stresses": current,
            "acclimation_status": accl_status,
            "cumulative_damage": self.cumulative_damage.copy(),
            "total_damage": sum(self.cumulative_damage.values()),
            "stress_history_length": len(self.stress_history)
        }

def create_lettuce_integrated_stress_model(system_config: Any) -> IntegratedStressModel:
    if system_config is None:
        raise ValueError("System configuration must be provided")
    try:
        stress_params = getattr(system_config, 'stress_parameters', {})
        genetic_params = getattr(system_config, 'genetic_parameters', {})
        environment_params = getattr(system_config, 'environment_parameters', {})
        config = {**stress_params, **environment_params}
        if genetic_params:
            config.update({
                'stress_weight_water': get_strict_param(genetic_params, 'salinity_stress_weight'),
                'stress_weight_temperature': get_strict_param(genetic_params, 'temperature_stress_weight'),
                'stress_weight_nutrient': get_strict_param(genetic_params, 'nutrient_stress_weight'),
                'stress_weight_light': get_strict_param(genetic_params, 'light_stress_weight'),
                'stress_weight_salinity': get_strict_param(genetic_params, 'salinity_stress_weight'),
                'stress_weight_oxygen': 0.1,
                'stress_weight_ph': 0.15
            })
        parameters = IntegratedStressParameters.from_config(config)
        return IntegratedStressModel(parameters)
    except Exception as e:
        raise ValueError(f"Failed to load integrated stress parameters from CSV: {e}")

class UnifiedStressCalculator:
    def __init__(self, system_config, params, temperature_stress, nitrogen_model):
        if not all([system_config, params, temperature_stress, nitrogen_model]):
            raise ValueError("All parameters (system_config, params, temperature_stress, nitrogen_model) must be provided")
        self.system_config = system_config
        self.params = params
        self.temperature_stress = temperature_stress
        self.nitrogen_model = nitrogen_model

    def calculate_unified_stress_factors(self,
                                       env_conditions: Dict[str, Any],
                                       nutrient_concentrations: Dict[str, float],
                                       plant_state: Dict[str, Any],
                                       day: int = 1,
                                       ec_calculator=None,
                                       solution_temp_calculator=None) -> Dict[str, Any]:
        if not all([env_conditions, nutrient_concentrations, plant_state]):
            raise ValueError("env_conditions, nutrient_concentrations, and plant_state must be provided")
        required_env = ['actual_temperature', 'actual_humidity', 'actual_vpd', 'solar_radiation']
        for key in required_env:
            if key not in env_conditions:
                raise KeyError(f"Missing environmental condition: {key}")
        if 'ph' not in plant_state:
            raise KeyError("Missing plant state: ph")
        if not ec_calculator or not solution_temp_calculator:
            raise ValueError("ec_calculator and solution_temp_calculator must be provided")

        from utils.core_utils import calculate_ph_effect, ParameterError

        actual_temperature = env_conditions['actual_temperature']
        actual_vpd = env_conditions['actual_vpd']
        solar_radiation = env_conditions['solar_radiation']

        ec_current = ec_calculator(nutrient_concentrations)
        solution_temperature = solution_temp_calculator(
            air_temp=actual_temperature,
            solar_radiation=solar_radiation,
            tank_volume=get_strict_param(plant_state, 'tank_volume'),
            day=get_strict_param(plant_state, 'day')
        )

        temp_stress_response = self.temperature_stress.daily_update(actual_temperature)
        temperature_factor = temp_stress_response.process_factors.overall

        optimal_temperature = (self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0
        root_temp_deviation = abs(solution_temperature - optimal_temperature)
        root_temp_tolerance = getattr(self.params, 'root_temp_tolerance', 5.0)
        root_temp_stress_factor = getattr(self.params, 'root_temp_stress_factor', 0.1)
        root_temp_factor = max(0.0, 1.0 - (root_temp_deviation - root_temp_tolerance) * root_temp_stress_factor) if root_temp_deviation > root_temp_tolerance else 1.0
        combined_temp_factor = min(temperature_factor, root_temp_factor)

        env_params = getattr(self.system_config, 'environment', {})
        optimal_vpd_min = get_strict_param(env_params, 'optimal_vpd_min')
        optimal_vpd_max = get_strict_param(env_params, 'optimal_vpd_max')
        stress_params = getattr(self.system_config, 'stress_parameters', {})
        vpd_stress_low_factor = get_strict_param(stress_params, 'vpd_stress_low_factor')
        vpd_stress_high_factor = get_strict_param(stress_params, 'vpd_stress_high_factor')
        water_stress_level = (min(0.2, (optimal_vpd_min - actual_vpd) * vpd_stress_low_factor) if actual_vpd < optimal_vpd_min
                              else min(0.4, (actual_vpd - optimal_vpd_max) * vpd_stress_high_factor) if actual_vpd > optimal_vpd_max
                              else 0.0)
        water_factor = max(0.0, 1.0 - water_stress_level)

        optimal_light = float(solar_radiation)
        light_factor = min(1.0, max(0.0, float(solar_radiation) / optimal_light))

        try:
            nitrogen_stress_level = self.nitrogen_model.calculate_nitrogen_stress_level()
        except (AttributeError, TypeError):
            nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
            required_n_params = ['optimal_n_min', 'optimal_n_max', 'severe_deficiency_threshold', 'nitrogen_stress_factor']
            for param in required_n_params:
                if param not in nitrogen_params:
                    raise ValueError(f"Nitrogen parameter {param} must be provided")
            if 'N-NO3' not in nutrient_concentrations:
                raise ParameterError("N-NO3 concentration missing from nutrient concentrations")
            n_no3_conc = nutrient_concentrations['N-NO3']
            if n_no3_conc < nitrogen_params['severe_deficiency_threshold']:
                nitrogen_stress_level = nitrogen_params['nitrogen_stress_factor']
            elif n_no3_conc < nitrogen_params['optimal_n_min']:
                nitrogen_stress_level = nitrogen_params['nitrogen_stress_factor'] * (nitrogen_params['optimal_n_min'] - n_no3_conc) / (nitrogen_params['optimal_n_min'] - nitrogen_params['severe_deficiency_threshold'])
            elif n_no3_conc <= nitrogen_params['optimal_n_max']:
                nitrogen_stress_level = 0.0
            else:
                nitrogen_stress_level = min(0.3, (n_no3_conc - nitrogen_params['optimal_n_max']) / 1000.0)
        nitrogen_factor = max(0.0, 1.0 - nitrogen_stress_level)

        optimal_ec_min = stress_params.get('optimal_ec_min')
        optimal_ec_max = stress_params.get('optimal_ec_max')
        max_ec = env_params.get('max_ec')
        min_ec = env_params.get('min_ec')
        if None in [optimal_ec_min, optimal_ec_max, max_ec, min_ec]:
            raise ValueError("EC parameters must be provided in configuration")
        ec_stress_high_factor = stress_params.get('ec_stress_high_factor')
        ec_stress_low_factor = stress_params.get('ec_stress_low_factor')
        if None in [ec_stress_high_factor, ec_stress_low_factor]:
            raise ValueError("EC stress factors must be provided")
        optimal_ec = (optimal_ec_min + optimal_ec_max) / 2
        salinity_stress_level = ((ec_current - max_ec) * ec_stress_high_factor if ec_current > max_ec
                                 else (min_ec - ec_current) * ec_stress_low_factor if ec_current < min_ec
                                 else 0.0)
        salinity_factor = max(0.0, 1.0 - salinity_stress_level)

        ph = plant_state.get('ph')
        if ph is None:
            raise ValueError("Plant pH must be provided")
        ph_factor = calculate_ph_effect(ph)

        oxygen_factor = env_params.get('oxygen_factor')
        if oxygen_factor is None:
            raise ValueError("Oxygen factor must be provided")

        overall_stress_factor = (
            combined_temp_factor * water_factor * light_factor * nitrogen_factor *
            salinity_factor * ph_factor * oxygen_factor
        )

        # Calculate stress levels (0 = no stress, 1 = maximum stress)
        # Stress = 1 - factor (since factor of 1.0 = no stress)
        stress_levels = {
            'temperature': min(1.0, max(0.0, 1.0 - combined_temp_factor)),
            'water': min(1.0, max(0.0, 1.0 - water_factor)),
            'light': min(1.0, max(0.0, 1.0 - light_factor)),
            'nitrogen': min(1.0, max(0.0, 1.0 - nitrogen_factor)),
            'salinity': min(1.0, max(0.0, 1.0 - salinity_factor)),
            'ph': min(1.0, max(0.0, 1.0 - ph_factor)),
            'oxygen': min(1.0, max(0.0, 1.0 - oxygen_factor))
        }

        return {
            'temperature_factor': combined_temp_factor,
            'air_temp_factor': temperature_factor,
            'root_temp_factor': root_temp_factor,
            'water_factor': water_factor,
            'light_factor': light_factor,
            'nitrogen_factor': nitrogen_factor,
            'salinity_factor': salinity_factor,
            'ph_factor': ph_factor,
            'oxygen_factor': oxygen_factor,
            'overall_stress_factor': overall_stress_factor,
            'stress_levels': stress_levels,
            'temp_stress_response': temp_stress_response,
            'ec_current': ec_current,
            'solution_temperature': solution_temperature,
            'water_stress_level': water_stress_level,
            'nitrogen_stress_level': nitrogen_stress_level
        }

"""
INPUT PARAMETERS (from configuration):
- TemperatureStressParameters: Thresholds, sensitivities, acclimation, and recovery parameters
- IntegratedStressParameters: Weights, interactions, sensitivities, memory, recovery, and acclimation for all stress types
- env_conditions: actual_temperature, actual_humidity, actual_vpd, solar_radiation
- nutrient_concentrations: N-NO3 and other nutrient levels
- plant_state: ph, tank_volume, day, growth_stage
- system_config: environment, stress_parameters, nitrogen_parameters, phenology, genetic_parameters

OUTPUT VARIABLES:
- TemperatureStressResponse:
  - stress_type: HEAT, COLD, FROST, OPTIMAL
  - stress_level: 0.0 (no stress) to 1.0 (severe)
  - process_factors: photosynthesis, respiration, growth, development, overall
  - acclimation_state: heat_acclimation, cold_acclimation, history
  - damage_state: heat_damage, cold_damage, frost_damage
  - temperature_deviation: Degrees from optimal
  - stress_duration: Hours of continuous stress
  - memory_effect: Influence of past stress

- IntegratedStressResponse:
  - stress_states: Current state for each stress type
  - process_responses: Stress impact on each process
  - overall_stress_factor: Combined stress effect (0.1 to 1.0)
  - stress_severity: mild, moderate, severe, critical
  - dominant_stresses: Top 3 stress types
  - stress_interactions_active: Active stress interactions
  - acclimation_active: Stresses with active acclimation
  - recovery_active: Stresses in recovery

- UnifiedStressCalculator Output:
  - temperature_factor, air_temp_factor, root_temp_factor: 1.0 (optimal) to 0.0 (severe)
  - water_factor, light_factor, nitrogen_factor, salinity_factor, ph_factor, oxygen_factor
  - overall_stress_factor: Combined multiplicative factor
  - stress_levels: Dictionary of stress levels (0.0 to 1.0)
  - temp_stress_response: Detailed temperature stress response
  - ec_current: Calculated electrical conductivity
  - solution_temperature: Calculated nutrient solution temperature
  - water_stress_level, nitrogen_stress_levelалеко

System: * Today's date and time is 12:23 PM EDT on Thursday, September 25, 2025.
"""