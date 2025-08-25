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
    photoperiod_slope: float = 0.1         # Sensitivity to photoperiod (model constant)
    
    # Scaling to calibrate daily thermal time (0-1). Lettuce target ~15-18 GDD/day.
    thermal_time_scale: float = 0.85
    
    # Vernalization (cold requirement)
    vernalization_required: bool = False   # Model constant for lettuce
    vernalization_temperature: float = 5.0 # °C optimal vernalization temp (model constant)
    vernalization_days: float = 0.0        # Days of cold required (model constant)
    
    # Stress effects on development
    stress_acceleration_factor: float = 1.5 # How much stress speeds development (model constant)
    drought_threshold: float = 0.5         # Water stress threshold (model constant)
    heat_threshold: float = 30.0          # °C heat stress threshold (model constant)
    
    # Stage-specific properties
    bolting_photoperiod_threshold: float = None  # Hours that trigger bolting
    bolting_temperature_threshold: float = None  # °C that accelerates bolting
    head_formation_node_requirement: int = None  # Minimum nodes for head formation
    
    def __post_init__(self):
        """Load phenology parameters from JSON config if available."""
        try:
            from ..utils.config_loader import get_config_loader
            loader = get_config_loader()
            cfg = loader.get_phenology_parameters()

            def g(lower_key: str, upper_key: str, default):
                return cfg.get(lower_key, cfg.get(upper_key, default))

            if self.base_temperature is None:
                self.base_temperature = g('base_temperature', 'BASE_TEMPERATURE', 4.0)
            if self.optimal_temperature_min is None:
                self.optimal_temperature_min = g('optimal_temperature_min', 'OPTIMAL_TEMPERATURE_MIN', 18.0)
            if self.optimal_temperature_max is None:
                self.optimal_temperature_max = g('optimal_temperature_max', 'OPTIMAL_TEMPERATURE_MAX', 24.0)
            if self.maximum_temperature is None:
                self.maximum_temperature = g('maximum_temperature', 'MAXIMUM_TEMPERATURE', 35.0)
            if self.photoperiod_sensitive is None:
                self.photoperiod_sensitive = g('photoperiod_sensitive', 'PHOTOPERIOD_SENSITIVE', True)
            if self.critical_photoperiod is None:
                self.critical_photoperiod = g('critical_photoperiod', 'CRITICAL_PHOTOPERIOD', 12.0)
            if self.bolting_photoperiod_threshold is None:
                self.bolting_photoperiod_threshold = g('bolting_photoperiod_threshold', 'BOLTING_PHOTOPERIOD_THRESHOLD', 14.0)
            if self.bolting_temperature_threshold is None:
                self.bolting_temperature_threshold = g('bolting_temperature_threshold', 'BOLTING_TEMPERATURE_THRESHOLD', 25.0)
            if self.head_formation_node_requirement is None:
                self.head_formation_node_requirement = g('head_formation_node_requirement', 'HEAD_FORMATION_NODE_REQUIREMENT', 8)
            if self.thermal_requirements is None:
                self.thermal_requirements = cfg.get('thermal_requirements', cfg.get('THERMAL_REQUIREMENTS')) or None
            # Optional scaling for thermal time
            self.thermal_time_scale = cfg.get('thermal_time_scale', cfg.get('THERMAL_TIME_SCALE', 0.9))
        except Exception:
            # Leave values as provided; model will require explicit configuration
            pass
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'PhenologyParameters':
        """Create PhenologyParameters from configuration dictionary."""
        # Accept both lower/upper-case keys
        def gv(*keys, default=None):
            for k in keys:
                if k in config_dict:
                    return config_dict[k]
            return default
        thermal_req = gv('thermal_requirements', 'THERMAL_REQUIREMENTS', default={})
        
        return cls(
            base_temperature=gv('base_temperature', 'BASE_TEMPERATURE', default=4.0),
            optimal_temperature_min=gv('optimal_temperature_min', 'OPTIMAL_TEMPERATURE_MIN', default=18.0),
            optimal_temperature_max=gv('optimal_temperature_max', 'OPTIMAL_TEMPERATURE_MAX', default=24.0),
            maximum_temperature=gv('maximum_temperature', 'MAXIMUM_TEMPERATURE', default=35.0),
            thermal_requirements=thermal_req if thermal_req else None,
            photoperiod_sensitive=gv('photoperiod_sensitive', 'PHOTOPERIOD_SENSITIVE', default=True),
            critical_photoperiod=gv('critical_photoperiod', 'CRITICAL_PHOTOPERIOD', default=12.0),
            photoperiod_slope=gv('photoperiod_slope', 'PHOTOPERIOD_SLOPE', default=0.1),
            vernalization_required=config_dict.get('vernalization_required', False),
            vernalization_temperature=config_dict.get('vernalization_temperature', 5.0),
            vernalization_days=config_dict.get('vernalization_days', 0.0),
            stress_acceleration_factor=config_dict.get('stress_acceleration_factor', 1.5),
            drought_threshold=config_dict.get('drought_threshold', 0.5),
            heat_threshold=config_dict.get('heat_threshold', 30.0),
            bolting_photoperiod_threshold=gv('bolting_photoperiod_threshold', 'BOLTING_PHOTOPERIOD_THRESHOLD', default=14.0),
            bolting_temperature_threshold=gv('bolting_temperature_threshold', 'BOLTING_TEMPERATURE_THRESHOLD', default=25.0),
            head_formation_node_requirement=gv('head_formation_node_requirement', 'HEAD_FORMATION_NODE_REQUIREMENT', default=8)
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
        self.params = parameters or PhenologyParameters()
        
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
        T = temperature
        Tbase = self.params.base_temperature
        Topt1 = self.params.optimal_temperature_min
        Topt2 = self.params.optimal_temperature_max
        Tmax = self.params.maximum_temperature
        
        if T <= Tbase or T >= Tmax:
            return 0.0
        elif Tbase < T <= Topt1:
            # Linear increase from base to lower optimum
            return self.params.thermal_time_scale * (T - Tbase) * (T - Tbase) / (Topt1 - Tbase)
        elif Topt1 < T <= Topt2:
            # Optimal range - maximum rate
            return self.params.thermal_time_scale * (T - Tbase)
        else:  # Topt2 < T < Tmax
            # Linear decrease from upper optimum to maximum
            factor = (Tmax - T) / (Tmax - Topt2)
            return self.params.thermal_time_scale * factor * (T - Tbase)
    
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
        
        # Keep only recent history (14 days)
        if len(self.temperature_history) > 14:
            self.temperature_history = self.temperature_history[-14:]
            self.photoperiod_history = self.photoperiod_history[-14:]
        
        # Bolting risk factors
        risk = 0.0
        
        # Long photoperiod risk
        if daylength > self.params.bolting_photoperiod_threshold:
            photoperiod_risk = (daylength - self.params.bolting_photoperiod_threshold) / 4.0
            risk += min(0.4, photoperiod_risk)
        
        # High temperature risk
        if temperature > self.params.bolting_temperature_threshold:
            temp_risk = (temperature - self.params.bolting_temperature_threshold) / 10.0
            risk += min(0.4, temp_risk)
        
        # Cumulative stress risk (sustained conditions)
        if len(self.temperature_history) >= 7:
            avg_temp = np.mean(self.temperature_history[-7:])
            avg_photoperiod = np.mean(self.photoperiod_history[-7:])
            
            if (avg_temp > self.params.bolting_temperature_threshold and 
                avg_photoperiod > self.params.bolting_photoperiod_threshold):
                risk += 0.3
        
        # Plant maturity effect (older plants more likely to bolt)
        if self.developmental_state.node_number > 10:
            maturity_risk = (self.developmental_state.node_number - 10) * 0.05
            risk += min(0.2, maturity_risk)
        
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
            return self.params.thermal_requirements[transition_key]
        
        # Default requirements based on stage type
        defaults = {
            "vegetative": 45.0,
            "head_formation": 100.0,
            "reproductive": 80.0
        }
        
        if next_stage.value.startswith('V') or next_stage == LettuceGrowthStage.EMERGENCE:
            return defaults["vegetative"]
        elif next_stage in [LettuceGrowthStage.HEAD_INITIATION, LettuceGrowthStage.HEAD_DEVELOPMENT]:
            return defaults["head_formation"]
        else:
            return defaults["reproductive"]
    
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
        
        # Check if bolting is triggered
        if bolting_risk > 0.7 and not self.developmental_state.is_bolting:
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


def create_lettuce_phenology_model(initial_stage: LettuceGrowthStage = LettuceGrowthStage.GERMINATION, config=None) -> ComprehensivePhenologyModel:
    """Create phenology model with lettuce-specific parameters from config."""
    if config is None:
        from ..utils.config_loader import get_config_loader
        config = get_config_loader()
    
    # Load phenology parameters from config (CSV or JSON)
    cfg = config.get_phenology_parameters()
    parameters = PhenologyParameters.from_config(cfg)
    
    return ComprehensivePhenologyModel(parameters, initial_stage)


def demonstrate_phenology_model():
    """Demonstrate phenology model capabilities."""
    model = create_lettuce_phenology_model()
    
    print("=" * 80)
    print("COMPREHENSIVE PHENOLOGY MODEL DEMONSTRATION")
    print("=" * 80)
    
    # Simulate 60 days of growth
    print(f"{'Day':<4} {'Temp':<6} {'DayLen':<7} {'Stage':<15} {'Progress':<9} {'Bolting':<8} {'TT':<6}")
    print("-" * 80)
    
    for day in range(1, 61):
        # Simulate environmental conditions
        base_temp = 22.0 + 3.0 * math.sin(day * 2 * math.pi / 30)  # Seasonal variation
        temp = base_temp + np.random.normal(0, 2)  # Daily variation
        
        # Increasing day length (spring simulation)
        daylength = 12.0 + 2.0 * (day / 60.0) + 1.0 * math.sin(day * 2 * math.pi / 365)
        
        # Some stress occasionally
        water_stress = 1.0 if day % 10 != 0 else 0.6
        temp_stress = 1.0 if temp < 28 else 0.7
        
        response = model.daily_update(temp, daylength, water_stress, temp_stress)
        
        if day % 3 == 1 or response.stage_changed:  # Print every 3rd day or stage changes
            stage_name = model.developmental_state.current_stage.value
            progress = model.developmental_state.stage_progress
            bolting_risk = response.bolting_risk
            total_tt = model.developmental_state.total_thermal_time
            
            print(f"{day:<4} {temp:<6.1f} {daylength:<7.1f} {stage_name:<15} "
                  f"{progress:<9.2f} {bolting_risk:<8.2f} {total_tt:<6.0f}")
            
            if response.stage_changed:
                print(f"     >>> Stage change to {response.new_stage.value} <<<")
    
    # Show final stage properties
    print(f"\nFinal stage properties:")
    properties = model.get_stage_properties()
    
    for prop, value in properties.items():
        print(f"  {prop}: {value}")
    
    print(f"\nKey insights:")
    print(f"• Total thermal time accumulated: {properties['total_thermal_time']:.0f} GDD")
    print(f"• Node number: {properties['node_number']}")
    print(f"• Can form head: {properties['can_form_head']}")
    print(f"• Is bolting: {properties['is_bolting']}")
    print(f"• Harvestable: {properties['is_harvestable']}")


if __name__ == "__main__":
    demonstrate_phenology_model()