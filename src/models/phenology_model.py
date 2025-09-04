"""
Comprehensive Phenology Model for Hydroponic Crop Simulation
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
from ..utils.temperature_utils import calculate_thermal_time, calculate_temperature_stress_factor


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
            # Starting from transplant (typically V2-V3 stage with some thermal time accumulated)
            thermal_accumulated = self.params.thermal_requirements["GE_to_VE"] + self.params.thermal_requirements["VE_to_V1"]
            thermal_required = self.params.thermal_requirements["V1_to_V2"]
            
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
        
        from ..utils.math_utils import clamp_value, safe_divide
        
        if max_thermal_time > 0:
            return clamp_value(safe_divide(thermal_time, max_thermal_time), 0.0, 1.0)
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


