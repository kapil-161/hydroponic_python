"""
Comprehensive Phenology Model for Hydroponic Crop Simulation - No hardcoded defaults allowed and no fallback to simple alternative codes
Based on CROPGRO PHENOL.for and developmental physiology research

Key concepts implemented:
1. Complete growth stage progression (Germination → Maturity → Reproductive)
2. Thermal time accumulation with stress effects
3. Photoperiod sensitivity for bolting/flowering
4. Vernalization requirements for cold-requiring crops
5. Stage-specific physiological properties
6. Environmental effects on development rate

Research basis:
- McMaster & Wilhelm (1997) - Growing degree days
- Ritchie & NeSmith (1991) - Temperature and photoperiod in crop development
- Wang & Engel (1998) - Simulation of phenological development
- Summerfield et al. (1991) - Towards prediction of time to flowering
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import math
from src.utils.temperature_utils import calculate_thermal_time, calculate_temperature_stress_factor


class LettuceGrowthStage(Enum):
    """Comprehensive lettuce growth stages following CROPGRO approach."""
    
    # Pre-emergence
    GERMINATION = "GE"          # Seed to emergence
    
    # Vegetative stages (V-stages)
    EMERGENCE = "VE"            # Emergence (V0)
    FIRST_LEAF = "V1"           # First true leaf
    SECOND_LEAF = "V2"          # Second true leaf
    THIRD_LEAF = "V3"           # Third true leaf
    FOURTH_LEAF = "V4"          # Fourth true leaf
    FIFTH_LEAF = "V5"           # Fifth true leaf
    SIXTH_LEAF = "V6"           # Sixth leaf
    SEVENTH_LEAF = "V7"         # Seventh leaf
    EIGHTH_LEAF = "V8"          # Eighth leaf
    NINTH_LEAF = "V9"           # Ninth leaf
    TENTH_LEAF = "V10"          # Tenth leaf
    MATURE_VEGETATIVE = "V11+"  # Continued vegetative growth (V11-V15)
    
    # Head formation (lettuce-specific)
    HEAD_INITIATION = "HI"      # Head formation begins
    HEAD_DEVELOPMENT = "HD"     # Head filling and compaction
    
    # Harvest maturity
    HARVEST_MATURITY = "HM"     # Commercial harvest stage
    
    # Reproductive stages (if bolting occurs)
    BOLTING_INITIATION = "BI"   # Bolting begins (stem elongation)
    FLOWERING = "FL"            # Flower development
    ANTHESIS = "AN"             # Pollination period
    SEED_DEVELOPMENT = "SD"     # Seed filling
    PHYSIOLOGICAL_MATURITY = "PM" # Seed maturity


@dataclass
class PhenologyParameters:
    """Parameters for phenology model."""
    
    # Base temperatures for development
    base_temperature: float = None          # °C base temperature
    optimal_temperature_min: float = None  # °C lower optimum
    optimal_temperature_max: float = None  # °C upper optimum  
    maximum_temperature: float = None      # °C maximum for development
    
    # Thermal time requirements (Growing Degree Days)
    thermal_requirements: Dict[str, float] = None
    
    # Photoperiod sensitivity
    photoperiod_sensitive: bool = None
    critical_photoperiod: float = None     # Hours critical day length
    
    # Stage-specific properties
    bolting_photoperiod_threshold: float = None  # Hours that trigger bolting
    bolting_temperature_threshold: float = None  # °C that accelerates bolting
    head_formation_node_requirement: int = None  # Minimum nodes for head formation
    
    # Additional bolting risk parameters
    environmental_buffer_days: int = None
    bolting_photoperiod_divisor: float = None
    bolting_photoperiod_risk_max: float = None
    bolting_temperature_divisor: float = None
    bolting_temperature_risk_max: float = None
    environmental_history_days: int = None
    bolting_sustained_stress_risk: float = None
    bolting_maturity_risk_factor: float = None
    bolting_maturity_risk_max: float = None
    bolting_risk_threshold: float = None
    
    photoperiod_slope: float = None         # Sensitivity to photoperiod (model constant)
    
    # Scaling to calibrate daily thermal time (0-1). Lettuce target ~15-18 GDD/day.
    thermal_time_scale: float = None
    
    # Vernalization (cold requirement)
    vernalization_required: bool = None   # Model constant for lettuce
    vernalization_temperature: float = None # °C optimal vernalization temp (model constant)
    vernalization_days: float = None        # Days of cold required (model constant)
    
    # Stress effects on development
    stress_acceleration_factor: float = None # How much stress speeds development (model constant)
    drought_threshold: float = None         # Water stress threshold (model constant)
    heat_threshold: float = None          # °C heat stress threshold (model constant)
    
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'PhenologyParameters':
        """Create PhenologyParameters from CSV configuration data."""
        # Validate required parameters
        required_params = [
            'base_temperature', 'phenology_optimal_temperature_min', 'phenology_optimal_temperature_max', 'maximum_temperature',
            'photoperiod_sensitive', 'critical_photoperiod', 'photoperiod_slope',
            'bolting_photoperiod_threshold', 'bolting_temperature_threshold', 'head_formation_node_requirement',
            'environmental_buffer_days', 'bolting_photoperiod_divisor', 'bolting_photoperiod_risk_max',
            'bolting_temperature_divisor', 'bolting_temperature_risk_max', 'environmental_history_days',
            'bolting_sustained_stress_risk', 'bolting_maturity_risk_factor', 'bolting_maturity_risk_max',
            'bolting_risk_threshold', 'thermal_time_scale', 'vernalization_required', 'vernalization_temperature',
            'vernalization_days', 'stress_acceleration_factor', 'drought_threshold', 'heat_threshold'
        ]
        
        missing_params = [p for p in required_params if p not in config_dict]
        if missing_params:
            raise ValueError(f"❌ Missing required phenology parameters in CSV: {missing_params}")
        
        # Handle thermal requirements from CSV data
        thermal_requirements = config_dict.get('thermal_requirements')
        if thermal_requirements is None:
            raise ValueError("❌ thermal_requirements must be provided in CSV configuration - no hardcoded defaults allowed")
        
        # Validate thermal_time_scale parameter range
        thermal_time_scale_value = float(config_dict['thermal_time_scale'])
        if not (0.5 <= thermal_time_scale_value <= 2.0):
            raise ValueError(f"❌ thermal_time_scale must be between 0.5 and 2.0, got {thermal_time_scale_value}")
        
        return cls(
            # Temperature parameters
            base_temperature=float(config_dict['base_temperature']),
            optimal_temperature_min=float(config_dict['phenology_optimal_temperature_min']),
            optimal_temperature_max=float(config_dict['phenology_optimal_temperature_max']),
            maximum_temperature=float(config_dict['maximum_temperature']),
            
            # Thermal requirements (loaded from CSV)
            thermal_requirements=thermal_requirements,
            
            # Photoperiod parameters
            photoperiod_sensitive=bool(config_dict['photoperiod_sensitive']),
            critical_photoperiod=float(config_dict['critical_photoperiod']),
            photoperiod_slope=float(config_dict['photoperiod_slope']),
            
            # Bolting parameters
            bolting_photoperiod_threshold=float(config_dict['bolting_photoperiod_threshold']),
            bolting_temperature_threshold=float(config_dict['bolting_temperature_threshold']),
            head_formation_node_requirement=int(config_dict['head_formation_node_requirement']),
            
            # Additional bolting risk parameters
            environmental_buffer_days=int(config_dict['environmental_buffer_days']),
            bolting_photoperiod_divisor=float(config_dict['bolting_photoperiod_divisor']),
            bolting_photoperiod_risk_max=float(config_dict['bolting_photoperiod_risk_max']),
            bolting_temperature_divisor=float(config_dict['bolting_temperature_divisor']),
            bolting_temperature_risk_max=float(config_dict['bolting_temperature_risk_max']),
            environmental_history_days=int(config_dict['environmental_history_days']),
            bolting_sustained_stress_risk=float(config_dict['bolting_sustained_stress_risk']),
            bolting_maturity_risk_factor=float(config_dict['bolting_maturity_risk_factor']),
            bolting_maturity_risk_max=float(config_dict['bolting_maturity_risk_max']),
            bolting_risk_threshold=float(config_dict['bolting_risk_threshold']),
            
            # Model constants
            thermal_time_scale=thermal_time_scale_value,
            vernalization_required=bool(config_dict['vernalization_required']),
            vernalization_temperature=float(config_dict['vernalization_temperature']),
            vernalization_days=float(config_dict['vernalization_days']),
            stress_acceleration_factor=float(config_dict['stress_acceleration_factor']),
            drought_threshold=float(config_dict['drought_threshold']),
            heat_threshold=float(config_dict['heat_threshold'])
        )


@dataclass
class DevelopmentalState:
    """Current developmental state of the plant."""
    current_stage: LettuceGrowthStage
    thermal_time_accumulated: float        # GDD accumulated in current stage
    thermal_time_required: float          # GDD required to complete current stage
    total_thermal_time: float             # Total GDD since planting
    stage_progress: float                 # Fraction of current stage completed (0-1)
    days_in_stage: int                    # Days spent in current stage
    vernalization_days: float = 0.0       # Cumulative vernalization days
    is_bolting: bool = False              # Whether plant is bolting
    node_number: int = 0                  # Current number of nodes
    can_form_head: bool = False           # Whether plant can form head


@dataclass
class PhenologyResponse:
    """Daily phenology calculation results."""
    daily_thermal_time: float
    temperature_factor: float
    photoperiod_factor: float
    stress_factor: float
    development_rate: float
    stage_changed: bool
    new_stage: Optional[LettuceGrowthStage]
    bolting_risk: float                   # Risk of bolting (0-1)


class ComprehensivePhenologyModel:
    """
    Comprehensive phenology model following CROPGRO principles.
    
    Tracks complete plant development from germination through
    reproductive maturity with environmental responses.
    """
    
    def __init__(self, parameters: Optional[PhenologyParameters] = None, 
                 initial_stage: LettuceGrowthStage = LettuceGrowthStage.GERMINATION):
        if parameters is None:
            raise ValueError("❌ PhenologyParameters required - no hardcoded defaults allowed")
        self.params = parameters
        
        # Set initial stage based on starting point (seed vs transplant)
        if initial_stage == LettuceGrowthStage.GERMINATION:
            # Starting from seed
            thermal_accumulated = 0.0
            thermal_required = self.params.thermal_requirements["GE_to_VE"]
        else:
            # Starting from transplant - calculate accumulated thermal time up to current stage
            stage_transitions = {
                LettuceGrowthStage.EMERGENCE: ["GE_to_VE"],
                LettuceGrowthStage.FIRST_LEAF: ["GE_to_VE", "VE_to_V1"],
                LettuceGrowthStage.SECOND_LEAF: ["GE_to_VE", "VE_to_V1", "V1_to_V2"],
                LettuceGrowthStage.THIRD_LEAF: ["GE_to_VE", "VE_to_V1", "V1_to_V2", "V2_to_V3"],
                LettuceGrowthStage.FOURTH_LEAF: ["GE_to_VE", "VE_to_V1", "V1_to_V2", "V2_to_V3", "V3_to_V4"],
            }

            # Calculate accumulated thermal time for current stage
            if initial_stage in stage_transitions:
                thermal_accumulated = sum(self.params.thermal_requirements[transition]
                                        for transition in stage_transitions[initial_stage])
            else:
                thermal_accumulated = 0.0

            # Get thermal requirement for next stage transition
            next_stage = self.get_next_stage(initial_stage)
            thermal_required = self.get_thermal_requirement(initial_stage, next_stage)
            
        self.developmental_state = DevelopmentalState(
            current_stage=initial_stage,
            thermal_time_accumulated=thermal_accumulated,
            thermal_time_required=thermal_required,
            total_thermal_time=thermal_accumulated,
            stage_progress=0.0,
            days_in_stage=0
        )
        self.photoperiod_history: List[float] = []
        self.temperature_history: List[float] = []
        
    def calculate_thermal_time(self, temperature: float) -> float:
        """
        Calculate daily thermal time using cardinal temperature approach.
        
        Args:
            temperature: Daily average temperature (°C)
            
        Returns:
            Daily thermal time (Growing Degree Days)
        """
        T = float(temperature)  # Ensure temperature is numeric
        Tbase = self.params.base_temperature
        Topt1 = self.params.optimal_temperature_min
        Topt2 = self.params.optimal_temperature_max
        Tmax = self.params.maximum_temperature
        
        if T <= Tbase or T >= Tmax:
            return 0.0
        elif Tbase < T <= Topt1:
            # Linear increase from base to lower optimum - return actual GDD
            factor = (T - Tbase) / (Topt1 - Tbase)
            return (T - Tbase) * factor * self.params.thermal_time_scale
        elif Topt1 < T <= Topt2:
            # Optimal range - return full degree days
            return (T - Tbase) * self.params.thermal_time_scale
        else:  # Topt2 < T < Tmax
            # Linear decrease from upper optimum to maximum - return actual GDD
            factor = (Tmax - T) / (Tmax - Topt2)
            return (T - Tbase) * factor * self.params.thermal_time_scale
    
    def calculate_temperature_factor(self, temperature: float) -> float:
        """
        Calculate temperature effect on development rate.
        
        Args:
            temperature: Daily average temperature (°C)
            
        Returns:
            Temperature factor (0-1, 1=optimal)
        """
        thermal_time = self.calculate_thermal_time(temperature)
        max_thermal_time = self.params.optimal_temperature_min - self.params.base_temperature
        
        # from utils.math_utils import clamp_value, safe_divide  # Module deleted

        if max_thermal_time > 0:
            if max_thermal_time == 0:
                ratio = 0.0
            else:
                ratio = thermal_time / max_thermal_time
            return max(0.0, min(1.0, ratio))
        else:
            return 1.0 if thermal_time > 0 else 0.0
    
    def calculate_photoperiod_factor(self, daylength: float) -> float:
        """
        Calculate photoperiod effect on development.
        
        Args:
            daylength: Day length in hours
            
        Returns:
            Photoperiod factor (0.5-1.5, 1=neutral)
        """
        if not self.params.photoperiod_sensitive:
            return 1.0
        
        # Lettuce is a long-day plant for bolting, but day-neutral for vegetative growth
        if self.developmental_state.current_stage.value.startswith('V'):
            # Vegetative stages - minimal photoperiod effect
            return 1.0
        elif self.developmental_state.current_stage in [
            LettuceGrowthStage.BOLTING_INITIATION,
            LettuceGrowthStage.FLOWERING
        ]:
            # Reproductive stages accelerated by long days
            if daylength > self.params.critical_photoperiod:
                excess_hours = daylength - self.params.critical_photoperiod
                factor = 1.0 + (excess_hours * self.params.photoperiod_slope)
                return min(1.5, factor)
            else:
                return 0.8  # Slowed by short days
        else:
            return 1.0
    
    def calculate_stress_factor(self, water_stress: float, 
                              temperature_stress: float) -> float:
        """
        Calculate stress effects on development rate.
        
        Args:
            water_stress: Water stress level (0-1, 1=no stress)
            temperature_stress: Temperature stress level (0-1, 1=no stress)
            
        Returns:
            Stress factor (can be >1 if stress accelerates development)
        """
        # Water stress below threshold accelerates development (escape response)
        if water_stress < self.params.drought_threshold:
            water_factor = self.params.stress_acceleration_factor
        else:
            water_factor = 1.0
        
        # Heat stress accelerates development
        if temperature_stress < 0.8:  # Heat stress
            temp_factor = self.params.stress_acceleration_factor
        else:
            temp_factor = 1.0
        
        # Combined stress effect (take maximum acceleration)
        return max(water_factor, temp_factor)
    
    def calculate_bolting_risk(self, temperature: float, daylength: float) -> float:
        """
        Calculate risk of bolting based on environmental conditions.
        
        Args:
            temperature: Daily average temperature (°C)
            daylength: Day length in hours
            
        Returns:
            Bolting risk (0-1, 1=certain bolting)
        """
        # Track environmental history
        self.temperature_history.append(temperature)
        self.photoperiod_history.append(daylength)
        
        # Keep only recent history (from CSV parameter)
        buffer_days = self.params.environmental_buffer_days
        if len(self.temperature_history) > buffer_days:
            self.temperature_history = self.temperature_history[-buffer_days:]
            self.photoperiod_history = self.photoperiod_history[-buffer_days:]
        
        # Bolting risk factors
        risk = 0.0
        
        # Long photoperiod risk
        if daylength > self.params.bolting_photoperiod_threshold:
            divisor = self.params.bolting_photoperiod_divisor
            max_risk = self.params.bolting_photoperiod_risk_max
            photoperiod_risk = (daylength - self.params.bolting_photoperiod_threshold) / divisor
            risk += min(max_risk, photoperiod_risk)
        
        # High temperature risk
        if float(temperature) > self.params.bolting_temperature_threshold:
            divisor = self.params.bolting_temperature_divisor
            max_risk = self.params.bolting_temperature_risk_max
            temp_risk = (float(temperature) - self.params.bolting_temperature_threshold) / divisor
            risk += min(max_risk, temp_risk)
        
        # Cumulative stress risk (sustained conditions)
        history_days = self.params.environmental_history_days
        if len(self.temperature_history) >= history_days:
            avg_temp = np.mean(self.temperature_history[-history_days:])
            avg_photoperiod = np.mean(self.photoperiod_history[-history_days:])
            
            if (avg_temp > self.params.bolting_temperature_threshold and 
                avg_photoperiod > self.params.bolting_photoperiod_threshold):
                sustained_risk = self.params.bolting_sustained_stress_risk
                risk += sustained_risk
        
        # Plant maturity effect (older plants more likely to bolt)
        if self.developmental_state.node_number > 10:
            risk_factor = self.params.bolting_maturity_risk_factor
            max_risk = self.params.bolting_maturity_risk_max
            maturity_risk = (self.developmental_state.node_number - 10) * risk_factor
            risk += min(max_risk, maturity_risk)
        
        return min(1.0, risk)
    
    def get_next_stage(self, current_stage: LettuceGrowthStage, 
                      bolting_triggered: bool = False) -> LettuceGrowthStage:
        """
        Determine the next developmental stage.
        
        Args:
            current_stage: Current growth stage
            bolting_triggered: Whether bolting has been triggered
            
        Returns:
            Next growth stage
        """
        # Define stage progression
        stage_progression = {
            LettuceGrowthStage.GERMINATION: LettuceGrowthStage.EMERGENCE,
            LettuceGrowthStage.EMERGENCE: LettuceGrowthStage.FIRST_LEAF,
            LettuceGrowthStage.FIRST_LEAF: LettuceGrowthStage.SECOND_LEAF,
            LettuceGrowthStage.SECOND_LEAF: LettuceGrowthStage.THIRD_LEAF,
            LettuceGrowthStage.THIRD_LEAF: LettuceGrowthStage.FOURTH_LEAF,
            LettuceGrowthStage.FOURTH_LEAF: LettuceGrowthStage.FIFTH_LEAF,
            LettuceGrowthStage.FIFTH_LEAF: LettuceGrowthStage.SIXTH_LEAF,
            LettuceGrowthStage.SIXTH_LEAF: LettuceGrowthStage.SEVENTH_LEAF,
            LettuceGrowthStage.SEVENTH_LEAF: LettuceGrowthStage.EIGHTH_LEAF,
            LettuceGrowthStage.EIGHTH_LEAF: LettuceGrowthStage.NINTH_LEAF,
            LettuceGrowthStage.NINTH_LEAF: LettuceGrowthStage.TENTH_LEAF,
            LettuceGrowthStage.TENTH_LEAF: LettuceGrowthStage.MATURE_VEGETATIVE,
            LettuceGrowthStage.MATURE_VEGETATIVE: LettuceGrowthStage.HEAD_INITIATION,
            LettuceGrowthStage.HEAD_INITIATION: LettuceGrowthStage.HEAD_DEVELOPMENT,
            LettuceGrowthStage.HEAD_DEVELOPMENT: LettuceGrowthStage.HARVEST_MATURITY,
        }
        
        # Bolting pathway
        bolting_progression = {
            LettuceGrowthStage.HARVEST_MATURITY: LettuceGrowthStage.BOLTING_INITIATION,
            LettuceGrowthStage.BOLTING_INITIATION: LettuceGrowthStage.FLOWERING,
            LettuceGrowthStage.FLOWERING: LettuceGrowthStage.ANTHESIS,
            LettuceGrowthStage.ANTHESIS: LettuceGrowthStage.SEED_DEVELOPMENT,
            LettuceGrowthStage.SEED_DEVELOPMENT: LettuceGrowthStage.PHYSIOLOGICAL_MATURITY,
        }
        
        # Normal progression or bolting
        if bolting_triggered and current_stage == LettuceGrowthStage.HARVEST_MATURITY:
            return LettuceGrowthStage.BOLTING_INITIATION
        elif current_stage in bolting_progression:
            return bolting_progression[current_stage]
        elif current_stage in stage_progression:
            return stage_progression[current_stage]
        else:
            return current_stage  # Stay in final stage
    
    def get_thermal_requirement(self, current_stage: LettuceGrowthStage, 
                               next_stage: LettuceGrowthStage) -> float:
        """
        Get thermal time requirement for stage transition.
        
        Args:
            current_stage: Current growth stage
            next_stage: Next growth stage
            
        Returns:
            Thermal time requirement (GDD)
        """
        # Create transition key
        transition_key = f"{current_stage.value}_to_{next_stage.value}"
        
        # Check if exact transition exists
        if transition_key in self.params.thermal_requirements:
            return float(self.params.thermal_requirements[transition_key])
        
        # Get requirements from CSV thermal_requirements - no hardcoded defaults allowed
        if next_stage.value.startswith('V') or next_stage == LettuceGrowthStage.EMERGENCE:
            default_key = "transition_defaults_vegetative"
        elif next_stage in [LettuceGrowthStage.HEAD_INITIATION, LettuceGrowthStage.HEAD_DEVELOPMENT]:
            default_key = "transition_defaults_head_formation"
        else:
            default_key = "transition_defaults_reproductive"
        
        if default_key not in self.params.thermal_requirements:
            raise ValueError(f"❌ {default_key} must be provided in CSV thermal requirements - no hardcoded defaults allowed")
        
        return float(self.params.thermal_requirements[default_key])
    
    def daily_update(self, temperature: float, daylength: float,
                    water_stress: float = 1.0, temperature_stress: float = 1.0) -> PhenologyResponse:
        """
        Daily phenology update.
        
        Args:
            temperature: Daily average temperature (°C)
            daylength: Day length (hours)
            water_stress: Water stress factor (0-1, 1=no stress)
            temperature_stress: Temperature stress factor (0-1, 1=no stress)
            
        Returns:
            Daily phenology response
        """
        # Calculate daily thermal time
        daily_tt = self.calculate_thermal_time(temperature)
        
        # Calculate development factors
        temp_factor = self.calculate_temperature_factor(temperature)
        photoperiod_factor = self.calculate_photoperiod_factor(daylength)
        stress_factor = self.calculate_stress_factor(water_stress, temperature_stress)
        
        # Calculate bolting risk
        bolting_risk = self.calculate_bolting_risk(temperature, daylength)
        
        # Check if bolting is triggered - use CSV parameter
        bolting_threshold = self.params.bolting_risk_threshold
        if bolting_risk > bolting_threshold and not self.developmental_state.is_bolting:
            self.developmental_state.is_bolting = True
        
        # Combined development rate
        development_rate = daily_tt * photoperiod_factor * stress_factor
        
        # Update thermal time accumulation
        self.developmental_state.thermal_time_accumulated += development_rate
        self.developmental_state.total_thermal_time += development_rate
        self.developmental_state.days_in_stage += 1
        
        # Update stage progress
        if self.developmental_state.thermal_time_required > 0:
            self.developmental_state.stage_progress = (
                self.developmental_state.thermal_time_accumulated / 
                self.developmental_state.thermal_time_required
            )
        
        # Check for stage transition
        stage_changed = False
        new_stage = None
        
        if self.developmental_state.stage_progress >= 1.0:
            # Determine next stage
            next_stage = self.get_next_stage(
                self.developmental_state.current_stage,
                self.developmental_state.is_bolting
            )
            
            if next_stage != self.developmental_state.current_stage:
                # Stage transition
                self.developmental_state.current_stage = next_stage
                self.developmental_state.thermal_time_accumulated = 0.0
                self.developmental_state.thermal_time_required = self.get_thermal_requirement(
                    self.developmental_state.current_stage, 
                    self.get_next_stage(next_stage, self.developmental_state.is_bolting)
                )
                self.developmental_state.stage_progress = 0.0
                self.developmental_state.days_in_stage = 0
                
                stage_changed = True
                new_stage = next_stage
                
                # Update node number for V-stages
                if next_stage.value.startswith('V') and next_stage.value[1:].isdigit():
                    self.developmental_state.node_number = int(next_stage.value[1:])
                elif next_stage.value.startswith('V') and '+' in next_stage.value:
                    self.developmental_state.node_number += 1
                
                # Check head formation capability
                if (self.developmental_state.node_number >= 
                    self.params.head_formation_node_requirement):
                    self.developmental_state.can_form_head = True
        
        return PhenologyResponse(
            daily_thermal_time=daily_tt,
            temperature_factor=temp_factor,
            photoperiod_factor=photoperiod_factor,
            stress_factor=stress_factor,
            development_rate=development_rate,
            stage_changed=stage_changed,
            new_stage=new_stage,
            bolting_risk=bolting_risk
        )
    
    def get_stage_properties(self) -> Dict[str, Any]:
        """
        Get current stage properties for use by other models.
        
        Returns:
            Dictionary of stage-specific properties
        """
        stage = self.developmental_state.current_stage
        
        # Define stage-specific properties
        properties = {
            'stage_name': stage.value,
            'stage_code': stage.name,
            'is_vegetative': stage.value.startswith('V') or stage == LettuceGrowthStage.EMERGENCE,
            'is_reproductive': stage in [
                LettuceGrowthStage.BOLTING_INITIATION,
                LettuceGrowthStage.FLOWERING,
                LettuceGrowthStage.ANTHESIS,
                LettuceGrowthStage.SEED_DEVELOPMENT,
                LettuceGrowthStage.PHYSIOLOGICAL_MATURITY
            ],
            'is_head_forming': stage in [
                LettuceGrowthStage.HEAD_INITIATION,
                LettuceGrowthStage.HEAD_DEVELOPMENT
            ],
            'is_harvestable': stage in [
                LettuceGrowthStage.HEAD_DEVELOPMENT,
                LettuceGrowthStage.HARVEST_MATURITY
            ],
            'node_number': self.developmental_state.node_number,
            'can_form_head': self.developmental_state.can_form_head,
            'is_bolting': self.developmental_state.is_bolting,
            'stage_progress': self.developmental_state.stage_progress,
            'days_in_stage': self.developmental_state.days_in_stage,
            'total_thermal_time': self.developmental_state.total_thermal_time
        }
        
        return properties


def create_lettuce_phenology_model(system_config=None, initial_stage: LettuceGrowthStage = LettuceGrowthStage.GERMINATION) -> ComprehensivePhenologyModel:
    """Create phenology model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        initial_stage: Initial growth stage for the model
        
    Returns:
        ComprehensivePhenologyModel configured with CSV parameters
        
    Raises:
        ValueError: If CSV parameters are missing or invalid
    """
    if system_config is None:
        raise ValueError("❌ system_config is required - no hardcoded defaults allowed")
    
    # Get consolidated phenology parameters from CSV data loaded in system_config
    phenology_params = getattr(system_config, 'phenology_parameters', None)
    thermal_requirements = getattr(system_config, 'thermal_requirements', None)
    
    if phenology_params is None:
        raise ValueError("❌ phenology_parameters missing from CSV - no fallback defaults allowed")
    
    if thermal_requirements is None:
        raise ValueError("❌ thermal_requirements missing from CSV - no fallback defaults allowed")
    
    # Combine parameters (now both come from consolidated CSV)
    combined_params = phenology_params.copy()
    combined_params['thermal_requirements'] = thermal_requirements
    
    # Create parameters from CSV config
    parameters = PhenologyParameters.from_config(combined_params)
    return ComprehensivePhenologyModel(parameters, initial_stage)


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file models plant phenology - the timing of developmental events in a plant's life cycle. 
Think of it as modeling the plant's biological calendar, tracking when major life events happen 
like germination, leafing, flowering, and maturity. It's like having a detailed growth chart 
that predicts when each stage will occur based on environmental conditions.

KEY FUNCTIONS AND EQUATIONS:

1. calculate_thermal_time()
   - What it does: Converts daily temperature into "heat units" for plant development
   - Equation: Uses cardinal temperature model with base, optimal, and maximum temperatures
     * Below base temp: thermal_time = 0 (too cold for growth)
     * Base to optimal: thermal_time = (T - base) × factor × scale
     * Optimal range: thermal_time = (T - base) × scale
     * Above optimal: thermal_time = (T - base) × declining_factor × scale
   - Real-world meaning: Like how cooking time depends on oven temperature. Plants need a certain 
     amount of "heat cooking time" to complete each growth stage, but too much heat slows things down.

2. calculate_temperature_factor()
   - What it does: Determines how efficiently temperature drives development
   - Range: 0-1 where 1 = optimal temperature
   - Real-world meaning: Like performance efficiency at different temperatures. A car engine 
     runs best at optimal temperature - too cold and it's sluggish, too hot and it overheats.

3. calculate_photoperiod_factor()
   - What it does: Adjusts development rate based on day length (hours of sunlight)
   - Applies to: Mainly flowering/bolting stages (lettuce is day-neutral for vegetative growth)
   - Range: 0.5-1.5 where 1 = neutral effect
   - Real-world meaning: Like how some people need more/less daylight to feel energetic. Some 
     plants are programmed to flower only when days are long (summer) or short (fall).

4. calculate_stress_factor()
   - What it does: Shows how environmental stress affects development timing
   - Equation: stress_factor = max(water_acceleration, temperature_acceleration)
   - Key insight: Stress typically accelerates development (plants rush to reproduce before dying)
   - Real-world meaning: Like how people mature faster under hardship. Stressed plants "panic" 
     and try to complete their life cycle quickly to ensure survival.

5. calculate_bolting_risk()
   - What it does: Predicts probability of premature flowering (bolting) in lettuce
   - Factors considered:
     * Long daylight hours (>14 hours triggers bolting)
     * High temperatures (>25°C accelerates bolting)
     * Plant maturity (older plants more likely to bolt)
     * Sustained stress conditions
   - Equation: risk = photoperiod_risk + temperature_risk + maturity_risk + sustained_stress_risk
   - Real-world meaning: Like predicting when a teenager might rebel. Multiple stress factors 
     increase the chance that lettuce will "give up" on making leaves and start making flowers.

6. get_next_stage()
   - What it does: Determines what growth stage comes next in the plant's development
   - Logic: Normal progression (seed→leaves→head→harvest) OR bolting pathway (leaves→flowers→seeds)
   - Real-world meaning: Like a GPS navigation system for plant development, choosing the route 
     based on current conditions and destination (reproductive success vs harvest quality).

7. daily_update()
   - What it does: Advances the plant's development by one day
   - Process: Calculate thermal time → Apply environmental factors → Update stage progress → 
     Check for stage transitions → Update plant status
   - Real-world meaning: Like a daily diary entry tracking the plant's growth milestones and 
     predicting when the next major event will occur.

GROWTH STAGES EXPLAINED:

Early Stages (Germination to Emergence):
- Germination (GE): Seed absorbs water, starts sprouting
- Emergence (VE): Seedling breaks through soil surface
- Thermal time: 50-80 GDD depending on conditions
- Like a baby's first weeks - critical foundation period

Vegetative Stages (V1-V10+):
- V1-V10: Each number represents one new leaf pair
- Each V-stage: ~40-60 GDD (about 3-5 days at optimal temperature)
- Node number tracks developmental progress
- Like childhood growth spurts - each stage builds on the previous

Head Formation (Lettuce-Specific):
- Head Initiation (HI): Plant begins forming compact center
- Head Development (HD): Center leaves curl inward, head tightens
- Harvest Maturity (HM): Head reaches commercial size/firmness
- Like adolescent growth - rapid change in body shape

Reproductive Stages (If Bolting Occurs):
- Bolting Initiation (BI): Stem elongates rapidly
- Flowering (FL): Flower buds develop
- Anthesis (AN): Flowers open, pollination occurs
- Seed Development (SD): Seeds form and mature
- Like adulthood - energy shifts from growth to reproduction

ENVIRONMENTAL FACTORS AFFECTING DEVELOPMENT:

Temperature Effects (Cardinal Temperature Model):
- Base temperature (4-5°C): Minimum for any development
- Optimal range (15-20°C): Maximum development rate
- Maximum temperature (30-35°C): Development stops (heat damage)
- Below/above optimal: Development slows progressively

Thermal Time Accumulation:
- Growing Degree Days (GDD) = daily heat units above base temperature
- Total GDD needed varies by variety: 800-1200 for lettuce maturity
- Like a savings account - plant "deposits" daily heat units until it has 
  enough to "purchase" the next developmental stage

Photoperiod (Day Length) Effects:
- Most lettuce varieties are day-neutral for vegetative growth
- Long days (>14-16 hours) trigger bolting in sensitive varieties
- Short days may delay flowering in some types
- Like a biological alarm clock set by sunrise/sunset patterns

Stress Acceleration Effects:
- Water stress: Plants rush to reproduce before dying from drought
- Heat stress: Accelerated development to escape damaging conditions  
- Nutrient stress: Early reproduction when resources are limited
- Like emergency protocols - stress triggers "survival mode"

BOLTING BIOLOGY AND PREDICTION:

What is Bolting?
- Premature shift from vegetative growth to reproductive development
- Stem elongates rapidly, leaves become bitter, head quality deteriorates
- Natural response to stress or end-of-season cues
- Like a plant's "midlife crisis" - sudden change in priorities

Bolting Triggers:
1. Long photoperiods (>14-16 hours daylight)
2. High temperatures (>25-30°C sustained)
3. Plant maturity (>10-12 nodes developed)
4. Water/nutrient stress
5. Root binding or transplant shock

Bolting Risk Assessment:
- Daily risk calculation based on environmental history
- Risk accumulates over time with sustained stress
- Threshold typically 0.6-0.8 (60-80% probability)
- Early warning allows preventive action

PRACTICAL APPLICATIONS:

For Hydroponic Growers:
1. **Planting Schedule**: Use thermal time to predict harvest dates
2. **Environment Control**: Maintain optimal temperature (18-22°C) for fastest growth
3. **Bolting Prevention**: Monitor day length and temperature, provide shade/cooling
4. **Harvest Timing**: Track stage progress to optimize harvest window
5. **Variety Selection**: Choose day-neutral varieties for year-round production
6. **Succession Planting**: Plan new seedings based on predicted maturity dates

For System Design:
1. **Climate Control**: Design heating/cooling to maintain optimal temperature
2. **Lighting Systems**: Control photoperiod to prevent premature bolting
3. **Environmental Monitoring**: Track temperature and day length history
4. **Automation**: Program systems to respond to phenological predictions
5. **Production Planning**: Optimize facility utilization based on growth timing

THERMAL TIME CALCULATIONS:

Example Calculation (20°C average temperature):
- Base temperature: 5°C
- Daily thermal time: 20 - 5 = 15 GDD
- Weekly accumulation: 15 × 7 = 105 GDD
- Time to V5 stage: 300 GDD ÷ 15 GDD/day = 20 days

Cool Weather (15°C average):
- Daily thermal time: 15 - 5 = 10 GDD  
- Time to V5: 300 ÷ 10 = 30 days (50% longer)

Hot Weather (30°C average):
- Above optimal, efficiency drops to ~60%
- Effective thermal time: 9 GDD/day
- Time to V5: 300 ÷ 9 = 33 days (heat stress slows development)

KEY CONCEPTS FOR NON-CODERS:

Biological Calendar: Plants have internal calendars that track developmental progress using 
temperature and day length as timing cues, like how animals migrate based on seasons.

Thermal Time: The concept that plants need a specific amount of accumulated heat to complete 
each growth stage, like how bread needs total baking time regardless of daily variations.

Cardinal Temperatures: Each plant has minimum, optimal, and maximum temperatures for development,
like how humans perform best in comfortable temperature ranges.

Photoperiodism: Plant responses to day length that trigger specific developmental events,
like how shorter days in fall trigger leaf color changes in deciduous trees.

Stress Response: Environmental stress typically accelerates plant development as a survival
strategy, like how animals reproduce earlier when threatened.

Stage-Gate Development: Plants must complete each developmental stage before proceeding to
the next, like educational grade levels that build on previous learning.

This phenology model helps predict plant development timing, optimize growing conditions, 
and prevent problems like premature bolting, enabling more efficient and successful 
hydroponic crop production.
"""
