"""
Dynamic Crop Growth Model for Hydroponic Systems
Implements 3-phase lettuce growth with stage-based parameter progression
Based on: Slow Growth → Rapid Growth → Steady Growth phases
"""

import numpy as np
from typing import Tuple, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class GrowthStage(Enum):
    """Lettuce growth stages based on physiological development."""
    SLOW_GROWTH = "slow_growth"      # Days 0-14: Establishment phase
    RAPID_GROWTH = "rapid_growth"    # Days 15-35: Exponential growth
    STEADY_GROWTH = "steady_growth"  # Days 35-45: Maturation phase


@dataclass
class GrowthParameters:
    """Stage-specific growth parameters."""
    lai_min: float
    lai_max: float
    height_min: float  # m
    height_max: float  # m
    kcb_base: float    # Base crop coefficient
    phi_base: float    # Base density index
    duration_days: int
    optimal_temp: float  # °C
    optimal_dli: float   # mol/m²/day
    nutrient_uptake_factor: float


class DynamicGrowthModel:
    """Dynamic growth model implementing 3-phase lettuce development."""
    
    def __init__(self):
        # Define stage-specific parameters from research
        self.stage_params = {
            GrowthStage.SLOW_GROWTH: GrowthParameters(
                lai_min=0.2, lai_max=1.5,
                height_min=0.05, height_max=0.15,
                kcb_base=0.70, phi_base=0.75,
                duration_days=14,
                optimal_temp=18.0, optimal_dli=12.0,
                nutrient_uptake_factor=0.6
            ),
            GrowthStage.RAPID_GROWTH: GrowthParameters(
                lai_min=1.5, lai_max=4.0,
                height_min=0.15, height_max=0.35,
                kcb_base=1.00, phi_base=0.90,
                duration_days=20,
                optimal_temp=22.0, optimal_dli=18.0,
                nutrient_uptake_factor=1.2
            ),
            GrowthStage.STEADY_GROWTH: GrowthParameters(
                lai_min=4.0, lai_max=3.5,
                height_min=0.35, height_max=0.30,
                kcb_base=0.85, phi_base=0.80,
                duration_days=10,
                optimal_temp=20.0, optimal_dli=15.0,
                nutrient_uptake_factor=0.8
            )
        }
        
        # Growth transition points
        self.stage_transitions = {
            GrowthStage.SLOW_GROWTH: 14,
            GrowthStage.RAPID_GROWTH: 35,
            GrowthStage.STEADY_GROWTH: 45
        }
        
        # Temperature response parameters
        self.temp_response = {
            'base_temp': 5.0,    # °C - base temperature for development
            'opt_temp': 20.0,    # °C - optimal temperature
            'max_temp': 35.0     # °C - maximum temperature
        }
        
    def determine_growth_stage(self, day: int) -> GrowthStage:
        """Determine current growth stage based on days after transplant."""
        if day <= 14:
            return GrowthStage.SLOW_GROWTH
        elif day <= 35:
            return GrowthStage.RAPID_GROWTH
        else:
            return GrowthStage.STEADY_GROWTH
    
    def calculate_temperature_factor(self, temp_avg: float, stage: GrowthStage) -> float:
        """Calculate temperature effect on growth rate (0.0 - 2.0)."""
        params = self.stage_params[stage]
        optimal = params.optimal_temp
        
        # Beta function for temperature response
        if temp_avg < self.temp_response['base_temp']:
            return 0.1
        elif temp_avg > self.temp_response['max_temp']:
            return 0.3
        else:
            # Optimized beta function centered on optimal temperature
            temp_range = self.temp_response['max_temp'] - self.temp_response['base_temp']
            normalized_temp = (temp_avg - self.temp_response['base_temp']) / temp_range
            optimal_norm = (optimal - self.temp_response['base_temp']) / temp_range
            
            # Beta distribution parameters for temperature response
            alpha = 2.0
            beta = 2.0
            
            if normalized_temp <= optimal_norm:
                factor = (normalized_temp / optimal_norm) ** alpha
            else:
                factor = ((1.0 - normalized_temp) / (1.0 - optimal_norm)) ** beta
                
            return max(0.1, min(2.0, factor))
    
    def calculate_dli_factor(self, solar_rad: float, stage: GrowthStage) -> float:
        """Calculate daily light integral effect on growth rate."""
        # Convert MJ/m²/day to approximate mol/m²/day (rough conversion)
        dli_approx = solar_rad * 2.1  # Approximate conversion factor
        
        params = self.stage_params[stage]
        optimal_dli = params.optimal_dli
        
        # Saturating response to light
        if dli_approx <= 0:
            return 0.1
        else:
            # Michaelis-Menten type response
            km = optimal_dli * 0.5  # Half-saturation constant
            factor = dli_approx / (dli_approx + km)
            return max(0.3, min(1.8, factor))
    
    def logistic_growth_function(self, day: int, stage: GrowthStage, 
                                parameter: str, temp_factor: float = 1.0) -> float:
        """Logistic growth function for smooth parameter transitions."""
        params = self.stage_params[stage]
        
        # Get parameter range
        if parameter == 'lai':
            min_val, max_val = params.lai_min, params.lai_max
        elif parameter == 'height':
            min_val, max_val = params.height_min, params.height_max
        elif parameter == 'kcb':
            min_val, max_val = params.kcb_base * 0.8, params.kcb_base
        elif parameter == 'phi':
            min_val, max_val = params.phi_base * 0.9, params.phi_base
        else:
            return 1.0
        
        # Stage-specific day calculation
        if stage == GrowthStage.SLOW_GROWTH:
            stage_day = day
            duration = 14
        elif stage == GrowthStage.RAPID_GROWTH:
            stage_day = day - 14
            duration = 20
        else:  # STEADY_GROWTH
            stage_day = day - 35
            duration = 10
        
        # Logistic function parameters
        if stage == GrowthStage.STEADY_GROWTH and parameter == 'lai':
            # Special case: LAI decreases in steady growth (senescence)
            # Reverse logistic for decline from 4.0 to 3.5
            midpoint = duration / 2
            steepness = 0.3
            progress = 1.0 / (1.0 + np.exp(-steepness * (stage_day - midpoint)))
            result = max_val - (max_val - min_val) * progress
        else:
            # Standard logistic growth
            midpoint = duration / 2
            steepness = 0.4 / temp_factor  # Temperature affects growth rate
            progress = 1.0 / (1.0 + np.exp(-steepness * (stage_day - midpoint)))
            result = min_val + (max_val - min_val) * progress
        
        return max(0.01, result)
    
    def calculate_dynamic_parameters(self, day: int, temp_avg: float, 
                                   solar_rad: float) -> Dict[str, float]:
        """Calculate all dynamic crop parameters for given day and conditions."""
        stage = self.determine_growth_stage(day)
        temp_factor = self.calculate_temperature_factor(temp_avg, stage)
        dli_factor = self.calculate_dli_factor(solar_rad, stage)
        
        # Environmental growth modifier
        env_factor = (temp_factor + dli_factor) / 2.0
        
        # Calculate dynamic parameters
        lai = self.logistic_growth_function(day, stage, 'lai', env_factor)
        height = self.logistic_growth_function(day, stage, 'height', env_factor)
        kcb = self.logistic_growth_function(day, stage, 'kcb', env_factor)
        phi = self.logistic_growth_function(day, stage, 'phi', env_factor)
        
        # Nutrient uptake factor based on stage and growth rate
        stage_params = self.stage_params[stage]
        nutrient_factor = stage_params.nutrient_uptake_factor * env_factor
        
        return {
            'lai': lai,
            'height': height,
            'kcb': kcb,
            'phi': phi,
            'growth_stage': stage.value,
            'temp_factor': temp_factor,
            'dli_factor': dli_factor,
            'env_factor': env_factor,
            'nutrient_uptake_factor': nutrient_factor,
            'stage_day': self.get_stage_day(day, stage)
        }
    
    def get_stage_day(self, day: int, stage: GrowthStage) -> int:
        """Get day within current growth stage."""
        if stage == GrowthStage.SLOW_GROWTH:
            return day
        elif stage == GrowthStage.RAPID_GROWTH:
            return day - 14
        else:  # STEADY_GROWTH
            return day - 35
    
    def detect_growth_phase_transition(self, lai_history: list, 
                                     days_window: int = 3) -> Optional[str]:
        """
        Detect growth phase transitions using derivative analysis.
        Returns transition type if detected.
        """
        if len(lai_history) < days_window + 1:
            return None
        
        # Calculate first derivative (growth rate)
        recent_lais = lai_history[-days_window-1:]
        growth_rates = np.diff(recent_lais)
        
        # Calculate second derivative (acceleration)
        if len(growth_rates) >= 2:
            accelerations = np.diff(growth_rates)
            
            # Transition detection criteria
            avg_growth_rate = np.mean(growth_rates)
            avg_acceleration = np.mean(accelerations) if len(accelerations) > 0 else 0
            
            # Slow to Rapid: Increasing growth rate and positive acceleration
            if avg_growth_rate > 0.05 and avg_acceleration > 0.01:
                return "slow_to_rapid"
            
            # Rapid to Steady: Decreasing growth rate and negative acceleration  
            if avg_growth_rate < 0.02 and avg_acceleration < -0.01:
                return "rapid_to_steady"
                
        return None
    
    def get_stage_summary(self, day: int) -> Dict[str, any]:
        """Get summary information for current growth stage."""
        stage = self.determine_growth_stage(day)
        params = self.stage_params[stage]
        stage_day = self.get_stage_day(day, stage)
        
        return {
            'stage_name': stage.value.replace('_', ' ').title(),
            'stage_day': stage_day,
            'total_stage_days': params.duration_days,
            'progress_percent': (stage_day / params.duration_days) * 100,
            'optimal_temperature': params.optimal_temp,
            'optimal_dli': params.optimal_dli,
            'expected_lai_range': f"{params.lai_min:.1f} - {params.lai_max:.1f}",
            'expected_height_range': f"{params.height_min:.2f} - {params.height_max:.2f} m"
        }


def create_growth_trajectory(days: int, temp_profile: list, 
                           solar_profile: list) -> Dict[str, list]:
    """
    Create complete growth trajectory for simulation period.
    
    Args:
        days: Number of simulation days
        temp_profile: Daily average temperatures
        solar_profile: Daily solar radiation values
        
    Returns:
        Dictionary with daily parameter values
    """
    model = DynamicGrowthModel()
    
    trajectory = {
        'day': [],
        'lai': [],
        'height': [],
        'kcb': [],
        'phi': [],
        'stage': [],
        'temp_factor': [],
        'dli_factor': [],
        'nutrient_factor': []
    }
    
    for day in range(1, days + 1):
        temp = temp_profile[day-1] if day-1 < len(temp_profile) else 22.0
        solar = solar_profile[day-1] if day-1 < len(solar_profile) else 18.0
        
        params = model.calculate_dynamic_parameters(day, temp, solar)
        
        trajectory['day'].append(day)
        trajectory['lai'].append(params['lai'])
        trajectory['height'].append(params['height'])
        trajectory['kcb'].append(params['kcb'])
        trajectory['phi'].append(params['phi'])
        trajectory['stage'].append(params['growth_stage'])
        trajectory['temp_factor'].append(params['temp_factor'])
        trajectory['dli_factor'].append(params['dli_factor'])
        trajectory['nutrient_factor'].append(params['nutrient_uptake_factor'])
    
    return trajectory