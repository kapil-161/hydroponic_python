"""
Integrated Stress Model for Hydroponic Crop Simulation
Based on CROPGRO stress integration and plant stress physiology research

Key concepts implemented:
1. Multiple stress type integration (water, temperature, nutrient, light, salinity)
2. Stress interaction effects (multiplicative, additive, synergistic)
3. Cumulative stress and memory effects
4. Stress acclimation and recovery dynamics
5. Process-specific stress sensitivity
6. Temporal stress patterns and thresholds

Research basis:
- Tardieu et al. (2018) - Plant response to environmental stress
- Chaves et al. (2009) - Stress combination effects
- Mittler (2006) - Abiotic stress, the field environment and stress combination
- Boyer (1982) - Plant productivity and environment
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import math


class StressType(Enum):
    """Types of environmental stresses."""
    WATER = "water"                    # Drought and flooding stress
    TEMPERATURE = "temperature"        # Heat and cold stress
    NUTRIENT = "nutrient"             # Deficiency and toxicity stress
    LIGHT = "light"                   # Low and high light stress
    SALINITY = "salinity"             # Salt stress
    OXYGEN = "oxygen"                 # Root zone oxygen stress
    PH = "ph"                         # pH stress
    MECHANICAL = "mechanical"         # Wind, physical damage
    PATHOGEN = "pathogen"             # Disease stress


class StressInteractionType(Enum):
    """Types of stress interactions."""
    MULTIPLICATIVE = "multiplicative"  # Effects multiply (most common)
    ADDITIVE = "additive"             # Effects add linearly
    SYNERGISTIC = "synergistic"       # Combined effect > individual effects
    ANTAGONISTIC = "antagonistic"     # One stress reduces effect of another
    THRESHOLD = "threshold"           # No effect until threshold exceeded


class ProcessType(Enum):
    """Plant processes affected by stress."""
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
    """Parameters for integrated stress model."""
    
    # Stress weights and importance
    stress_weights: Dict[str, float] = None
    
    # Stress interaction matrices
    stress_interactions: Dict[str, Dict[str, Dict[str, float]]] = None
    
    # Process sensitivity to different stresses
    process_sensitivity: Dict[str, Dict[str, float]] = None
    
    # Cumulative stress parameters
    stress_memory_duration: Dict[str, float] = None
    cumulative_threshold: Dict[str, float] = None
    damage_accumulation_rate: Dict[str, float] = None
    
    # Recovery parameters
    recovery_rates: Dict[str, float] = None
    recovery_thresholds: Dict[str, float] = None
    full_recovery_time: Dict[str, float] = None
    
    # Acclimation parameters
    acclimation_rates: Dict[str, float] = None
    acclimation_capacity: Dict[str, float] = None
    acclimation_memory: Dict[str, float] = None
    
    # Stress thresholds
    stress_onset_thresholds: Dict[str, float] = None
    damage_thresholds: Dict[str, float] = None
    lethal_thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        if self.stress_weights is None:
            # Relative importance of different stress types
            self.stress_weights = {
                StressType.WATER.value: 0.25,        # High impact
                StressType.TEMPERATURE.value: 0.20,  # High impact
                StressType.NUTRIENT.value: 0.20,     # High impact
                StressType.LIGHT.value: 0.15,        # Moderate impact
                StressType.SALINITY.value: 0.10,     # Moderate impact
                StressType.OXYGEN.value: 0.05,       # Lower impact in hydroponics
                StressType.PH.value: 0.03,           # Lower impact (usually controlled)
                StressType.MECHANICAL.value: 0.01,   # Low impact in controlled environment
                StressType.PATHOGEN.value: 0.01      # Low impact (prevention focused)
            }
        
        if self.stress_interactions is None:
            # How different stress types interact
            self.stress_interactions = {
                StressType.WATER.value: {
                    StressType.TEMPERATURE.value: {"type": "synergistic", "factor": 1.3},
                    StressType.SALINITY.value: {"type": "synergistic", "factor": 1.4},
                    StressType.NUTRIENT.value: {"type": "multiplicative", "factor": 1.2}
                },
                StressType.TEMPERATURE.value: {
                    StressType.WATER.value: {"type": "synergistic", "factor": 1.3},
                    StressType.LIGHT.value: {"type": "additive", "factor": 1.1},
                    StressType.OXYGEN.value: {"type": "multiplicative", "factor": 1.2}
                },
                StressType.NUTRIENT.value: {
                    StressType.WATER.value: {"type": "multiplicative", "factor": 1.2},
                    StressType.PH.value: {"type": "synergistic", "factor": 1.5},
                    StressType.SALINITY.value: {"type": "multiplicative", "factor": 1.1}
                },
                StressType.LIGHT.value: {
                    StressType.TEMPERATURE.value: {"type": "additive", "factor": 1.1},
                    StressType.WATER.value: {"type": "multiplicative", "factor": 1.1}
                },
                StressType.SALINITY.value: {
                    StressType.WATER.value: {"type": "synergistic", "factor": 1.4},
                    StressType.NUTRIENT.value: {"type": "multiplicative", "factor": 1.1},
                    StressType.OXYGEN.value: {"type": "multiplicative", "factor": 1.2}
                }
            }
        
        if self.process_sensitivity is None:
            # How sensitive each process is to different stresses (0-1, 1=highly sensitive)
            self.process_sensitivity = {
                ProcessType.PHOTOSYNTHESIS.value: {
                    StressType.WATER.value: 0.9,
                    StressType.TEMPERATURE.value: 0.8,
                    StressType.LIGHT.value: 0.9,
                    StressType.NUTRIENT.value: 0.7,
                    StressType.SALINITY.value: 0.6
                },
                ProcessType.GROWTH.value: {
                    StressType.WATER.value: 0.8,
                    StressType.TEMPERATURE.value: 0.7,
                    StressType.NUTRIENT.value: 0.9,
                    StressType.LIGHT.value: 0.6,
                    StressType.SALINITY.value: 0.7
                },
                ProcessType.NUTRIENT_UPTAKE.value: {
                    StressType.WATER.value: 0.6,
                    StressType.TEMPERATURE.value: 0.5,
                    StressType.SALINITY.value: 0.9,
                    StressType.OXYGEN.value: 0.8,
                    StressType.PH.value: 0.7
                },
                ProcessType.DEVELOPMENT.value: {
                    StressType.TEMPERATURE.value: 0.9,
                    StressType.WATER.value: 0.7,
                    StressType.LIGHT.value: 0.6,
                    StressType.NUTRIENT.value: 0.5
                },
                ProcessType.SENESCENCE.value: {
                    StressType.WATER.value: 0.8,
                    StressType.NUTRIENT.value: 0.7,
                    StressType.TEMPERATURE.value: 0.6,
                    StressType.LIGHT.value: 0.5
                }
            }
        
        if self.stress_memory_duration is None:
            # How long stress effects persist (days)
            self.stress_memory_duration = {
                StressType.WATER.value: 3.0,        # Quick recovery
                StressType.TEMPERATURE.value: 5.0,  # Moderate recovery
                StressType.NUTRIENT.value: 7.0,     # Slow recovery
                StressType.LIGHT.value: 2.0,        # Very quick recovery
                StressType.SALINITY.value: 10.0,    # Very slow recovery
                StressType.OXYGEN.value: 1.0,       # Immediate recovery
                StressType.PH.value: 2.0            # Quick recovery
            }
        
        if self.recovery_rates is None:
            # Daily recovery rates when stress is removed (fraction/day)
            self.recovery_rates = {
                StressType.WATER.value: 0.3,        # 30% recovery per day
                StressType.TEMPERATURE.value: 0.2,  # 20% recovery per day
                StressType.NUTRIENT.value: 0.1,     # 10% recovery per day
                StressType.LIGHT.value: 0.5,        # 50% recovery per day
                StressType.SALINITY.value: 0.05,    # 5% recovery per day
                StressType.OXYGEN.value: 0.8,       # 80% recovery per day
                StressType.PH.value: 0.4            # 40% recovery per day
            }
        
        if self.acclimation_rates is None:
            # Rate of acclimation to stress (fraction/day)
            self.acclimation_rates = {
                StressType.WATER.value: 0.1,        # Slow acclimation
                StressType.TEMPERATURE.value: 0.15, # Moderate acclimation
                StressType.LIGHT.value: 0.2,        # Fast acclimation
                StressType.SALINITY.value: 0.05,    # Very slow acclimation
                StressType.NUTRIENT.value: 0.08     # Slow acclimation
            }
        
        if self.stress_onset_thresholds is None:
            # Stress levels below which no stress occurs (0-1, 1=optimal)
            self.stress_onset_thresholds = {
                StressType.WATER.value: 0.8,        # Stress below 80% optimal
                StressType.TEMPERATURE.value: 0.9,  # Stress below 90% optimal
                StressType.NUTRIENT.value: 0.7,     # Stress below 70% optimal
                StressType.LIGHT.value: 0.6,        # Stress below 60% optimal
                StressType.SALINITY.value: 0.9,     # Stress below 90% optimal
                StressType.OXYGEN.value: 0.8,       # Stress below 80% optimal
                StressType.PH.value: 0.8            # Stress below 80% optimal
            }
        
        if self.damage_thresholds is None:
            # Stress levels above which permanent damage occurs
            self.damage_thresholds = {
                StressType.WATER.value: 0.3,        # Damage below 30% optimal
                StressType.TEMPERATURE.value: 0.2,  # Damage below 20% optimal
                StressType.NUTRIENT.value: 0.4,     # Damage below 40% optimal
                StressType.LIGHT.value: 0.2,        # Damage below 20% optimal
                StressType.SALINITY.value: 0.4,     # Damage below 40% optimal
                StressType.OXYGEN.value: 0.3,       # Damage below 30% optimal
                StressType.PH.value: 0.3            # Damage below 30% optimal
            }
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'IntegratedStressParameters':
        """Create IntegratedStressParameters from configuration dictionary."""
        stress_weights = config_dict.get('stress_weights', {})
        stress_interactions = config_dict.get('stress_interactions', {})
        process_sensitivity = config_dict.get('process_sensitivity', {})
        memory_duration = config_dict.get('stress_memory_duration', {})
        recovery_rates = config_dict.get('recovery_rates', {})
        acclimation_rates = config_dict.get('acclimation_rates', {})
        onset_thresholds = config_dict.get('stress_onset_thresholds', {})
        damage_thresholds = config_dict.get('damage_thresholds', {})
        
        return cls(
            stress_weights=stress_weights if stress_weights else None,
            stress_interactions=stress_interactions if stress_interactions else None,
            process_sensitivity=process_sensitivity if process_sensitivity else None,
            stress_memory_duration=memory_duration if memory_duration else None,
            recovery_rates=recovery_rates if recovery_rates else None,
            acclimation_rates=acclimation_rates if acclimation_rates else None,
            stress_onset_thresholds=onset_thresholds if onset_thresholds else None,
            damage_thresholds=damage_thresholds if damage_thresholds else None
        )


@dataclass
class StressState:
    """Current stress state for a specific stress type."""
    stress_type: str
    current_level: float                # Current stress level (0-1, 1=optimal)
    acute_stress: float = 0.0           # Immediate stress effect
    chronic_stress: float = 0.0         # Cumulative/memory stress effect
    acclimation_level: float = 0.0      # Level of acclimation (0-1)
    damage_level: float = 0.0           # Permanent damage (0-1)
    recovery_progress: float = 0.0      # Recovery progress (0-1)
    days_under_stress: int = 0          # Consecutive days under stress
    stress_history: List[float] = None  # Recent stress history
    
    def __post_init__(self):
        if self.stress_history is None:
            self.stress_history = []


@dataclass
class StressResponse:
    """Calculated stress response for a plant process."""
    process_type: str
    individual_stress_effects: Dict[str, float]  # Effect of each stress type
    combined_stress_factor: float               # Overall stress factor (0-1)
    interaction_effects: Dict[str, float]       # Stress interaction contributions
    acclimation_benefits: Dict[str, float]      # Benefit from acclimation
    recovery_effects: Dict[str, float]          # Recovery contributions
    damage_effects: Dict[str, float]            # Permanent damage effects
    limiting_stress_types: List[str]            # Most limiting stress types


@dataclass
class IntegratedStressResponse:
    """Daily integrated stress calculation results."""
    stress_states: Dict[str, StressState]       # Current state of each stress type
    process_responses: Dict[str, StressResponse] # Response for each process
    overall_stress_factor: float                # Plant-wide stress factor
    stress_severity: str                        # mild, moderate, severe, critical
    dominant_stresses: List[str]                # Most impactful stress types
    stress_interactions_active: List[str]       # Active stress interactions
    acclimation_active: List[str]               # Stresses being acclimated to
    recovery_active: List[str]                  # Stresses being recovered from


class IntegratedStressModel:
    """
    Comprehensive integrated stress model following CROPGRO principles.
    
    Models multiple stress types, their interactions, cumulative effects,
    acclimation, and recovery dynamics.
    """
    
    def __init__(self, parameters: Optional[IntegratedStressParameters] = None):
        self.params = parameters or IntegratedStressParameters()
        self.stress_states: Dict[str, StressState] = {}
        self.stress_history: List[Dict[str, Any]] = []
        self.cumulative_damage: Dict[str, float] = {}
        
        # Initialize stress states
        for stress_type in self.params.stress_weights.keys():
            self.stress_states[stress_type] = StressState(
                stress_type=stress_type,
                current_level=1.0  # Start optimal
            )
            self.cumulative_damage[stress_type] = 0.0
    
    def calculate_acute_stress(self, stress_type: str, current_level: float) -> float:
        """
        Calculate immediate stress effect.
        
        Args:
            stress_type: Type of stress
            current_level: Current stress level (0-1, 1=optimal)
            
        Returns:
            Acute stress factor (0-1, 1=no stress)
        """
        threshold = self.params.stress_onset_thresholds.get(stress_type, 0.8)
        
        if current_level >= threshold:
            return 1.0  # No stress
        
        # Calculate stress intensity
        stress_intensity = (threshold - current_level) / threshold
        
        # Apply stress curve (exponential for severe stress)
        if current_level < 0.5:
            # Severe stress region - exponential response
            stress_factor = current_level / 0.5
            stress_factor = stress_factor ** 2
        else:
            # Moderate stress region - linear response
            stress_factor = current_level
        
        return max(0.1, stress_factor)  # Minimum 10% function
    
    def calculate_chronic_stress(self, stress_state: StressState) -> float:
        """
        Calculate cumulative/memory stress effect.
        
        Args:
            stress_state: Current stress state
            
        Returns:
            Chronic stress factor (0-1, 1=no chronic stress)
        """
        if not stress_state.stress_history:
            return 1.0
        
        stress_type = stress_state.stress_type
        memory_duration = self.params.stress_memory_duration.get(stress_type, 5.0)
        
        # Calculate weighted average of recent stress
        recent_history = stress_state.stress_history[-int(memory_duration):]
        if not recent_history:
            return 1.0
        
        # Weight recent stress more heavily
        weights = np.exp(-np.arange(len(recent_history)) / (memory_duration / 3))
        weights = weights[::-1]  # Recent values get higher weights
        
        weighted_stress = np.average(recent_history, weights=weights)
        
        # Chronic stress builds up over time
        if stress_state.days_under_stress > memory_duration:
            chronic_factor = 1.0 - (1.0 - weighted_stress) * 1.5  # 50% amplification
        else:
            chronic_factor = weighted_stress
        
        return max(0.1, min(1.0, chronic_factor))
    
    def calculate_acclimation_effect(self, stress_state: StressState) -> float:
        """
        Calculate acclimation benefit.
        
        Args:
            stress_state: Current stress state
            
        Returns:
            Acclimation benefit factor (0-1, 0=no benefit, 1=full acclimation)
        """
        stress_type = stress_state.stress_type
        
        if stress_state.days_under_stress < 3:
            return 0.0  # No acclimation for short-term stress
        
        acclimation_rate = self.params.acclimation_rates.get(stress_type, 0.1)
        max_acclimation = 0.3  # Maximum 30% stress reduction through acclimation
        
        # Acclimation builds gradually
        potential_acclimation = min(max_acclimation, 
                                  stress_state.days_under_stress * acclimation_rate)
        
        # Acclimation is less effective for severe stress
        stress_severity = 1.0 - stress_state.current_level
        acclimation_efficiency = max(0.2, 1.0 - stress_severity)
        
        return potential_acclimation * acclimation_efficiency
    
    def calculate_recovery_effect(self, stress_state: StressState) -> float:
        """
        Calculate recovery progress.
        
        Args:
            stress_state: Current stress state
            
        Returns:
            Recovery factor (0-1, 1=full recovery)
        """
        stress_type = stress_state.stress_type
        
        # Only recover when stress is reduced
        if stress_state.current_level < 0.8:
            return 0.0  # Still under stress, no recovery
        
        recovery_rate = self.params.recovery_rates.get(stress_type, 0.2)
        
        # Recovery is faster for less severe prior stress
        if stress_state.chronic_stress > 0.7:
            # Mild prior stress - fast recovery
            daily_recovery = recovery_rate
        elif stress_state.chronic_stress > 0.4:
            # Moderate prior stress - normal recovery
            daily_recovery = recovery_rate * 0.7
        else:
            # Severe prior stress - slow recovery
            daily_recovery = recovery_rate * 0.3
        
        return min(1.0, stress_state.recovery_progress + daily_recovery)
    
    def calculate_stress_interactions(self, active_stresses: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate interactions between multiple stresses.
        
        Args:
            active_stresses: Dictionary of stress types and their levels
            
        Returns:
            Dictionary of interaction effects
        """
        interaction_effects = {}
        
        stress_types = list(active_stresses.keys())
        
        for i, stress1 in enumerate(stress_types):
            for stress2 in stress_types[i+1:]:
                
                # Check if interaction is defined
                if (stress1 in self.params.stress_interactions and 
                    stress2 in self.params.stress_interactions[stress1]):
                    
                    interaction = self.params.stress_interactions[stress1][stress2]
                    interaction_type = interaction["type"]
                    interaction_factor = interaction["factor"]
                    
                    stress1_level = 1.0 - active_stresses[stress1]  # Convert to stress intensity
                    stress2_level = 1.0 - active_stresses[stress2]
                    
                    if interaction_type == "multiplicative":
                        combined_effect = stress1_level * stress2_level * interaction_factor
                    elif interaction_type == "synergistic":
                        combined_effect = (stress1_level + stress2_level) * interaction_factor
                    elif interaction_type == "additive":
                        combined_effect = (stress1_level + stress2_level) * interaction_factor
                    else:
                        combined_effect = max(stress1_level, stress2_level) * interaction_factor
                    
                    interaction_key = f"{stress1}_{stress2}"
                    interaction_effects[interaction_key] = min(1.0, combined_effect)
        
        return interaction_effects
    
    def calculate_process_stress_response(self, process_type: str, 
                                        stress_states: Dict[str, StressState]) -> StressResponse:
        """
        Calculate stress response for a specific plant process.
        
        Args:
            process_type: Type of plant process
            stress_states: Current stress states
            
        Returns:
            Process-specific stress response
        """
        individual_effects = {}
        acclimation_benefits = {}
        recovery_effects = {}
        damage_effects = {}
        
        # Get process sensitivity
        process_sensitivities = self.params.process_sensitivity.get(process_type, {})
        
        active_stresses = {}
        
        for stress_type, stress_state in stress_states.items():
            sensitivity = process_sensitivities.get(stress_type, 0.5)
            
            if sensitivity > 0:
                # Calculate individual stress effect
                acute_effect = stress_state.acute_stress
                chronic_effect = stress_state.chronic_stress
                
                # Combine acute and chronic effects
                combined_stress = min(acute_effect, chronic_effect * 0.8 + acute_effect * 0.2)
                
                # Apply process sensitivity
                process_stress = 1.0 - ((1.0 - combined_stress) * sensitivity)
                individual_effects[stress_type] = process_stress
                
                if process_stress < 0.9:  # Only track significant stresses
                    active_stresses[stress_type] = process_stress
                
                # Calculate acclimation benefit
                acclimation_benefit = stress_state.acclimation_level * 0.3  # Max 30% benefit
                acclimation_benefits[stress_type] = acclimation_benefit
                
                # Calculate recovery effect
                recovery_effects[stress_type] = stress_state.recovery_progress
                
                # Calculate damage effect
                damage_effects[stress_type] = self.cumulative_damage.get(stress_type, 0.0)
        
        # Calculate stress interactions
        interaction_effects = self.calculate_stress_interactions(active_stresses)
        
        # Calculate combined stress factor
        if not individual_effects:
            combined_stress_factor = 1.0
        else:
            # Start with the most limiting individual stress
            base_stress = min(individual_effects.values())
            
            # Add interaction effects
            interaction_penalty = sum(interaction_effects.values()) * 0.1  # 10% penalty per interaction
            
            # Apply acclimation benefits
            acclimation_bonus = sum(acclimation_benefits.values()) * 0.1
            
            # Apply recovery benefits
            recovery_bonus = sum(recovery_effects.values()) * 0.05
            
            # Apply damage penalties
            damage_penalty = sum(damage_effects.values()) * 0.2
            
            combined_stress_factor = (base_stress - interaction_penalty + 
                                   acclimation_bonus + recovery_bonus - damage_penalty)
            combined_stress_factor = max(0.1, min(1.0, combined_stress_factor))
        
        # Identify limiting stresses
        limiting_stresses = [stress for stress, effect in individual_effects.items() 
                           if effect < 0.8]
        limiting_stresses.sort(key=lambda x: individual_effects[x])
        
        return StressResponse(
            process_type=process_type,
            individual_stress_effects=individual_effects,
            combined_stress_factor=combined_stress_factor,
            interaction_effects=interaction_effects,
            acclimation_benefits=acclimation_benefits,
            recovery_effects=recovery_effects,
            damage_effects=damage_effects,
            limiting_stress_types=limiting_stresses[:3]  # Top 3 limiting
        )
    
    def update_stress_states(self, current_stress_levels: Dict[str, float]):
        """
        Update stress states based on current environmental conditions.
        
        Args:
            current_stress_levels: Current stress levels by type (0-1, 1=optimal)
        """
        for stress_type, current_level in current_stress_levels.items():
            if stress_type in self.stress_states:
                stress_state = self.stress_states[stress_type]
                
                # Update current level
                stress_state.current_level = current_level
                
                # Update stress history
                stress_state.stress_history.append(current_level)
                memory_duration = self.params.stress_memory_duration.get(stress_type, 5.0)
                if len(stress_state.stress_history) > memory_duration:
                    stress_state.stress_history = stress_state.stress_history[-int(memory_duration):]
                
                # Update days under stress
                threshold = self.params.stress_onset_thresholds.get(stress_type, 0.8)
                if current_level < threshold:
                    stress_state.days_under_stress += 1
                else:
                    stress_state.days_under_stress = max(0, stress_state.days_under_stress - 1)
                
                # Calculate stress components
                stress_state.acute_stress = self.calculate_acute_stress(stress_type, current_level)
                stress_state.chronic_stress = self.calculate_chronic_stress(stress_state)
                stress_state.acclimation_level = self.calculate_acclimation_effect(stress_state)
                stress_state.recovery_progress = self.calculate_recovery_effect(stress_state)
                
                # Update cumulative damage
                damage_threshold = self.params.damage_thresholds.get(stress_type, 0.3)
                if current_level < damage_threshold:
                    damage_rate = (damage_threshold - current_level) / damage_threshold * 0.01
                    self.cumulative_damage[stress_type] += damage_rate
                    self.cumulative_damage[stress_type] = min(0.5, self.cumulative_damage[stress_type])  # Max 50% damage
                
                stress_state.damage_level = self.cumulative_damage[stress_type]
    
    def daily_update(self, current_stress_levels: Dict[str, float]) -> IntegratedStressResponse:
        """
        Daily integrated stress update.
        
        Args:
            current_stress_levels: Current environmental stress levels
            
        Returns:
            Complete integrated stress response
        """
        # Update all stress states
        self.update_stress_states(current_stress_levels)
        
        # Calculate process responses
        process_responses = {}
        for process_type in self.params.process_sensitivity.keys():
            response = self.calculate_process_stress_response(process_type, self.stress_states)
            process_responses[process_type] = response
        
        # Calculate overall plant stress factor
        if process_responses:
            process_factors = [resp.combined_stress_factor for resp in process_responses.values()]
            overall_stress_factor = np.mean(process_factors)
        else:
            overall_stress_factor = 1.0
        
        # Determine stress severity
        if overall_stress_factor > 0.8:
            severity = "mild"
        elif overall_stress_factor > 0.6:
            severity = "moderate"
        elif overall_stress_factor > 0.3:
            severity = "severe"
        else:
            severity = "critical"
        
        # Identify dominant stresses
        stress_impacts = {}
        for stress_type, stress_state in self.stress_states.items():
            impact = (1.0 - stress_state.acute_stress) * self.params.stress_weights.get(stress_type, 0.1)
            stress_impacts[stress_type] = impact
        
        dominant_stresses = sorted(stress_impacts.keys(), 
                                 key=lambda x: stress_impacts[x], reverse=True)[:3]
        
        # Identify active processes
        stress_interactions_active = []
        for process_resp in process_responses.values():
            stress_interactions_active.extend(process_resp.interaction_effects.keys())
        stress_interactions_active = list(set(stress_interactions_active))
        
        acclimation_active = [st for st, state in self.stress_states.items() 
                            if state.acclimation_level > 0.1]
        
        recovery_active = [st for st, state in self.stress_states.items() 
                         if state.recovery_progress > 0.1]
        
        # Store daily record
        daily_record = {
            'overall_stress_factor': overall_stress_factor,
            'severity': severity,
            'dominant_stresses': dominant_stresses,
            'active_interactions': len(stress_interactions_active)
        }
        self.stress_history.append(daily_record)
        
        return IntegratedStressResponse(
            stress_states=self.stress_states.copy(),
            process_responses=process_responses,
            overall_stress_factor=overall_stress_factor,
            stress_severity=severity,
            dominant_stresses=dominant_stresses,
            stress_interactions_active=stress_interactions_active,
            acclimation_active=acclimation_active,
            recovery_active=recovery_active
        )
    
    def get_stress_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive stress summary.
        
        Returns:
            Dictionary with stress summary
        """
        current_stresses = {}
        acclimation_status = {}
        cumulative_damage_total = 0.0
        
        for stress_type, stress_state in self.stress_states.items():
            current_stresses[stress_type] = {
                'current_level': stress_state.current_level,
                'acute_stress': stress_state.acute_stress,
                'chronic_stress': stress_state.chronic_stress,
                'days_under_stress': stress_state.days_under_stress
            }
            
            acclimation_status[stress_type] = stress_state.acclimation_level
            cumulative_damage_total += self.cumulative_damage.get(stress_type, 0.0)
        
        summary = {
            'current_stresses': current_stresses,
            'acclimation_status': acclimation_status,
            'cumulative_damage': self.cumulative_damage.copy(),
            'total_damage': cumulative_damage_total,
            'stress_history_length': len(self.stress_history)
        }
        
        return summary


def create_lettuce_integrated_stress_model() -> IntegratedStressModel:
    """Create integrated stress model with lettuce-specific parameters."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        stress_config = config_loader.get_value('integrated_stress', '', {})
        parameters = IntegratedStressParameters.from_config(stress_config)
        return IntegratedStressModel(parameters)
    except ImportError:
        # Fallback to default values if config loader not available
        return IntegratedStressModel()


def demonstrate_integrated_stress_model():
    """Demonstrate integrated stress model capabilities."""
    model = create_lettuce_integrated_stress_model()
    
    print("=" * 80)
    print("INTEGRATED STRESS MODEL DEMONSTRATION")
    print("=" * 80)
    
    # Define stress scenarios
    scenarios = [
        ("Optimal conditions", {
            'water': 1.0, 'temperature': 1.0, 'nutrient': 1.0, 
            'light': 1.0, 'salinity': 1.0
        }),
        ("Mild water stress", {
            'water': 0.7, 'temperature': 1.0, 'nutrient': 1.0, 
            'light': 1.0, 'salinity': 1.0
        }),
        ("Heat + water stress", {
            'water': 0.6, 'temperature': 0.5, 'nutrient': 1.0, 
            'light': 1.0, 'salinity': 1.0
        }),
        ("Multiple stress", {
            'water': 0.5, 'temperature': 0.6, 'nutrient': 0.7, 
            'light': 0.8, 'salinity': 0.8
        }),
        ("Severe stress", {
            'water': 0.3, 'temperature': 0.4, 'nutrient': 0.5, 
            'light': 0.6, 'salinity': 0.6
        }),
        ("Recovery phase", {
            'water': 0.9, 'temperature': 0.9, 'nutrient': 0.8, 
            'light': 0.9, 'salinity': 0.9
        })
    ]
    
    print(f"Simulating stress scenarios over time:")
    print(f"{'Day':<4} {'Scenario':<15} {'Overall':<8} {'Severity':<9} {'Dominant':<15} {'Interactions':<12}")
    print("-" * 80)
    
    day = 0
    for cycle in range(2):  # Run scenarios twice to show acclimation
        for scenario_name, stress_levels in scenarios:
            day += 1
            
            response = model.daily_update(stress_levels)
            
            dominant_str = ', '.join(response.dominant_stresses[:2])
            interactions_str = f"{len(response.stress_interactions_active)} active"
            
            print(f"{day:<4} {scenario_name:<15} {response.overall_stress_factor:<8.3f} "
                  f"{response.stress_severity:<9} {dominant_str:<15} {interactions_str:<12}")
    
    # Show detailed stress analysis
    print(f"\nDetailed Process Stress Analysis:")
    final_response = response
    
    print(f"{'Process':<15} {'Stress Factor':<13} {'Limiting Stresses':<25}")
    print("-" * 60)
    
    for process, resp in final_response.process_responses.items():
        limiting_str = ', '.join(resp.limiting_stress_types[:2])
        print(f"{process:<15} {resp.combined_stress_factor:<13.3f} {limiting_str:<25}")
    
    # Show stress interactions
    if final_response.stress_interactions_active:
        print(f"\nActive Stress Interactions:")
        for interaction in final_response.stress_interactions_active:
            print(f"  • {interaction}")
    
    # Show acclimation and recovery
    if final_response.acclimation_active:
        print(f"\nActive Acclimation:")
        for stress in final_response.acclimation_active:
            acclim_level = model.stress_states[stress].acclimation_level
            print(f"  • {stress}: {acclim_level:.2f}")
    
    if final_response.recovery_active:
        print(f"\nActive Recovery:")
        for stress in final_response.recovery_active:
            recovery_level = model.stress_states[stress].recovery_progress
            print(f"  • {stress}: {recovery_level:.2f}")
    
    # Final summary
    summary = model.get_stress_summary()
    print(f"\nStress Model Summary:")
    print(f"• Overall stress factor: {final_response.overall_stress_factor:.3f}")
    print(f"• Stress severity: {final_response.stress_severity}")
    print(f"• Total cumulative damage: {summary['total_damage']:.3f}")
    print(f"• Dominant stresses: {', '.join(final_response.dominant_stresses)}")


if __name__ == "__main__":
    demonstrate_integrated_stress_model()