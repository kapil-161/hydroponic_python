"""
Environmental Control System

Key equations:
- VPD = saturated_vapor_pressure - actual_vapor_pressure
- optimal_humidity = (target_vapor_pressure / saturated_vapor_pressure) × 100
- CO2_factor = (Vmax × CO2) / (Km + CO2)
- PID_output = Kp×error + Ki×∫error + Kd×(d/dt)error
"""

import numpy as np
from typing import Dict, Tuple, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import math


class ParameterError(Exception):
    """Raised when required parameters are missing"""
    pass


def get_required_condition(conditions: Dict[str, Any], param_name: str) -> float:
    """Get required environmental condition or raise error if missing"""
    if param_name not in conditions or conditions[param_name] is None:
        raise ParameterError(f"Required environmental condition '{param_name}' missing from current conditions")
    return conditions[param_name]


def get_required_action_param(action: Dict[str, Any], param_name: str) -> float:
    """Get required action parameter or raise error if missing"""
    if param_name not in action or action[param_name] is None:
        raise ParameterError(f"Required action parameter '{param_name}' missing from control action")
    return action[param_name]
from src.utils.core_utils import calculate_vpd


class ControlStrategy(Enum):
    PASSIVE = "passive"
    BASIC = "basic"
    PROPORTIONAL = "proportional"
    PID = "pid"


@dataclass
class EnvironmentalSetpoints:
    target_vpd: float
    vpd_tolerance: float
    min_humidity: float
    max_humidity: float
    day_temp: float
    night_temp: float
    temp_tolerance: float
    target_co2: float
    ambient_co2: float
    co2_tolerance: float
    light_hours: float
    light_intensity: float
    co2_enrichment_start_hour: float
    humidity_deadband: float
    max_temperature_change_per_hour: float
    ambient_temperature: float
    thermal_mass_factor: float
    base_co2_loss_rate: float
    min_co2_concentration: float
    max_co2_concentration: float
    light_saturation_threshold: float
    co2_response_vmax: float
    co2_response_km: float
    max_co2_enhancement_factor: float
    pid_parameters: dict
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'EnvironmentalSetpoints':
        pid_parameters = {
            'humidity': {
                'kp': float(config_dict['pid_humidity_kp']),
                'ki': float(config_dict['pid_humidity_ki']),
                'kd': float(config_dict['pid_humidity_kd'])
            },
            'co2': {
                'kp': float(config_dict['pid_co2_kp']),
                'ki': float(config_dict['pid_co2_ki']),
                'kd': float(config_dict['pid_co2_kd'])
            },
            'temperature': {
                'kp': float(config_dict['pid_temperature_kp']),
                'ki': float(config_dict['pid_temperature_ki']),
                'kd': float(config_dict['pid_temperature_kd'])
            }
        }

        return cls(
            target_vpd=float(config_dict['target_vpd']),
            vpd_tolerance=float(config_dict['vpd_tolerance']),
            min_humidity=float(config_dict['min_humidity']),
            max_humidity=float(config_dict['max_humidity']),
            day_temp=float(config_dict['day_temp']),
            night_temp=float(config_dict['night_temp']),
            temp_tolerance=float(config_dict['temp_tolerance']),
            target_co2=float(config_dict['target_co2']),
            ambient_co2=float(config_dict['ambient_co2']),
            co2_tolerance=float(config_dict['co2_tolerance']),
            light_hours=float(config_dict['light_hours']),
            light_intensity=float(config_dict['light_intensity_control']),
            co2_enrichment_start_hour=float(config_dict['co2_enrichment_start_hour']),
            humidity_deadband=float(config_dict['humidity_deadband']),
            max_temperature_change_per_hour=float(config_dict['max_temperature_change_per_hour']),
            ambient_temperature=float(config_dict['ambient_temperature']),
            thermal_mass_factor=float(config_dict['thermal_mass_factor']),
            base_co2_loss_rate=float(config_dict['base_co2_loss_rate']),
            min_co2_concentration=float(config_dict['min_co2_concentration']),
            max_co2_concentration=float(config_dict['max_co2_concentration']),
            light_saturation_threshold=float(config_dict['light_saturation_threshold']),
            co2_response_vmax=float(config_dict['co2_response_vmax']),
            co2_response_km=float(config_dict['co2_response_km']),
            max_co2_enhancement_factor=float(config_dict['max_co2_enhancement_factor']),
            pid_parameters=pid_parameters
        )


@dataclass
class ControlEquipment:
    humidifier_capacity: float
    dehumidifier_capacity: float
    co2_injection_rate: float
    co2_sensor_accuracy: float
    co2_mixing_time: float
    circulation_fan_power: float
    humidifier_efficiency: float
    dehumidifier_efficiency: float
    air_exchange_rate: float
    
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'ControlEquipment':
        return cls(
            humidifier_capacity=float(config_dict['humidifier_capacity']),
            dehumidifier_capacity=float(config_dict['dehumidifier_capacity']),
            humidifier_efficiency=float(config_dict['humidifier_efficiency']),
            dehumidifier_efficiency=float(config_dict['dehumidifier_efficiency']),
            co2_injection_rate=float(config_dict['co2_injection_rate']),
            co2_sensor_accuracy=float(config_dict['co2_sensor_accuracy']),
            co2_mixing_time=float(config_dict['co2_mixing_time']),
            air_exchange_rate=float(config_dict['air_exchange_rate']),
            circulation_fan_power=float(config_dict['circulation_fan_power'])
        )


class EnvironmentalControlSystem:
    def __init__(self, setpoints: EnvironmentalSetpoints, equipment: ControlEquipment):
        self.setpoints = setpoints
        self.equipment = equipment

        self.pid_params = {
            'humidity': {'kp': None, 'ki': None, 'kd': None},
            'co2': {'kp': None, 'ki': None, 'kd': None},
            'temperature': {'kp': None, 'ki': None, 'kd': None}
        }

        self._load_pid_parameters(setpoints.pid_parameters)

        self.integral_errors = {'humidity': 0.0, 'co2': 0.0, 'temperature': 0.0}
        self.previous_errors = {'humidity': 0.0, 'co2': 0.0, 'temperature': 0.0}

        self.equipment_status = {
            'humidifier_active': False,
            'dehumidifier_active': False,
            'co2_injector_active': False,
            'ventilation_rate': 0.0,
            'total_energy_consumption': 0.0
        }
    
    def _load_pid_parameters(self, pid_config: dict):
        for control_type in ['humidity', 'co2', 'temperature']:
            for param in ['kp', 'ki', 'kd']:
                self.pid_params[control_type][param] = float(pid_config[control_type][param])
    
    
    def calculate_optimal_humidity(self, temperature: float, target_vpd: float) -> float:
        es = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
        ea = es - target_vpd
        rh = (ea / es) * 100.0
        return max(self.setpoints.min_humidity, min(self.setpoints.max_humidity, rh))
    
    def calculate_co2_photosynthesis_factor(self, co2_concentration: float, 
                                          temperature: float, light_intensity: float) -> float:
        """
        Calculate CO2 effect on photosynthesis using Michaelis-Menten kinetics.
        
        Args:
            co2_concentration: CO2 concentration (μmol/mol)
            temperature: Temperature (°C)
            light_intensity: Light intensity (μmol/m²/s)
            
        Returns:
            Photosynthesis enhancement factor (1.0 = baseline at 400 ppm)
        """
        # Temperature-dependent CO2 response parameters
        # At higher temperatures, CO2 response increases
        temp_factor = 1.0 + (temperature - 20.0) * 0.02
        temp_factor = max(0.5, min(1.5, temp_factor))
        
        # Light-dependent CO2 response
        # Higher light intensity increases CO2 utilization capacity
        light_saturation = self.setpoints.light_saturation_threshold  # μmol/m²/s for lettuce
        light_factor = light_intensity / (light_intensity + light_saturation)
        
        # Michaelis-Menten parameters for CO2 response (lettuce-specific)
        vmax = self.setpoints.co2_response_vmax * temp_factor * light_factor  # Maximum enhancement
        km = self.setpoints.co2_response_km * (1.0 - temp_factor * 0.2)   # Half-saturation concentration
        
        # Current enhancement at given CO2 level
        current_response = (vmax * co2_concentration) / (km + co2_concentration)
        
        # Baseline response at 400 ppm
        baseline_response = (vmax * 400.0) / (km + 400.0)
        
        # Return relative enhancement
        if baseline_response > 0:
            return current_response / baseline_response
        else:
            return 1.0
    
    def calculate_vpd_stress_factor(self, current_vpd: float) -> Tuple[float, float, str]:
        """
        Calculate plant stress factor based on VPD.
        
        Args:
            current_vpd: Current VPD (kPa)
            
        Returns:
            Tuple of (transpiration_factor, photosynthesis_factor, stress_level)
        """
        optimal_vpd = self.setpoints.target_vpd
        tolerance = self.setpoints.vpd_tolerance
        
        # Define VPD stress response curves
        if optimal_vpd - tolerance <= current_vpd <= optimal_vpd + tolerance:
            # Optimal range - no stress
            transpiration_factor = 1.0
            photosynthesis_factor = 1.0
            stress_level = "optimal"
            
        elif current_vpd < optimal_vpd - tolerance:
            # Too humid - reduced transpiration, potential disease risk
            deficit = (optimal_vpd - tolerance) - current_vpd
            transpiration_factor = max(0.4, 1.0 - deficit * 0.8)
            photosynthesis_factor = max(0.6, 1.0 - deficit * 0.5)
            if current_vpd < 0.3:
                stress_level = "severe_humidity"
            else:
                stress_level = "high_humidity"
                
        else:  # current_vpd > optimal_vpd + tolerance
            # Too dry - water stress, stomatal closure
            excess = current_vpd - (optimal_vpd + tolerance)
            transpiration_factor = max(0.3, 1.0 - excess * 1.2)
            photosynthesis_factor = max(0.4, 1.0 - excess * 0.8)
            if current_vpd > 1.5:
                stress_level = "severe_drought"
            else:
                stress_level = "water_stress"
        
        return transpiration_factor, photosynthesis_factor, stress_level
    
    def calculate_humidity_control_action(self, current_humidity: float, 
                                        target_humidity: float, 
                                        strategy: ControlStrategy = ControlStrategy.PID) -> Dict[str, float]:
        """
        Calculate humidity control actions.
        
        Args:
            current_humidity: Current RH (%)
            target_humidity: Target RH (%)
            strategy: Control strategy to use
            
        Returns:
            Dictionary with control actions and power consumption
        """
        error = target_humidity - current_humidity
        
        if strategy == ControlStrategy.PASSIVE:
            return {
                'humidifier_power': 0.0,
                'dehumidifier_power': 0.0,
                'energy_consumption_kWh': 0.0,
                'action': 'none'
            }
        
        elif strategy == ControlStrategy.BASIC:
            # Simple on/off control with deadband
            deadband = self.setpoints.humidity_deadband  # Deadband from CSV configuration
            
            if error > deadband:
                # Need more humidity
                return {
                    'humidifier_power': 100.0,
                    'dehumidifier_power': 0.0,
                    'energy_consumption_kWh': 0.5,
                    'action': 'humidify'
                }
            elif error < -deadband:
                # Need less humidity
                return {
                    'humidifier_power': 0.0,
                    'dehumidifier_power': 100.0,
                    'energy_consumption_kWh': 1.2,
                    'action': 'dehumidify'
                }
            else:
                return {
                    'humidifier_power': 0.0,
                    'dehumidifier_power': 0.0,
                    'energy_consumption_kWh': 0.0,
                    'action': 'maintain'
                }
        
        elif strategy == ControlStrategy.PID:
            # PID control implementation
            params = self.pid_params['humidity']
            
            # Update integral and derivative terms
            self.integral_errors['humidity'] += error
            derivative = error - self.previous_errors['humidity']
            self.previous_errors['humidity'] = error
            
            # PID output (-100 to +100)
            pid_output = (params['kp'] * error + 
                         params['ki'] * self.integral_errors['humidity'] +
                         params['kd'] * derivative)
            
            # Convert to equipment control signals
            if pid_output > 5.0:
                # Humidify
                power = min(100.0, pid_output)
                return {
                    'humidifier_power': power,
                    'dehumidifier_power': 0.0,
                    'energy_consumption_kWh': power * 0.005,
                    'action': f'humidify_{power:.1f}%'
                }
            elif pid_output < -5.0:
                # Dehumidify  
                power = min(100.0, abs(pid_output))
                return {
                    'humidifier_power': 0.0,
                    'dehumidifier_power': power,
                    'energy_consumption_kWh': power * 0.012,
                    'action': f'dehumidify_{power:.1f}%'
                }
            else:
                return {
                    'humidifier_power': 0.0,
                    'dehumidifier_power': 0.0,
                    'energy_consumption_kWh': 0.1,  # Baseline circulation
                    'action': 'maintain'
                }
        
        # Default return case for unhandled strategies
        return {
            'humidifier_power': 0.0,
            'dehumidifier_power': 0.0,
            'energy_consumption_kWh': 0.0,
            'action': 'no_control'
        }
    
    def _calculate_time_based_co2_target(self, base_target: float, photoperiod_time: float, 
                                       light_on: bool, config_dict: Optional[Dict[str, Any]] = None) -> float:
        """Calculate CO2 target based on time within photoperiod using CSV parameters."""
        if not light_on:
            return self.setpoints.ambient_co2
        
        if not config_dict:
            # Fallback to original behavior if no config
            return base_target
        
        # Load time-based parameters from CSV - ERROR if missing
        required_params = [
            'co2_enrichment_start_hour', 'co2_enrichment_duration', 
            'co2_enrichment_strategy', 'co2_morning_target', 'co2_afternoon_target'
        ]
        
        for param in required_params:
            if param not in config_dict:
                raise KeyError(f"Required CO2 enrichment parameter '{param}' not found in CSV configuration")
        
        start_hour = config_dict['co2_enrichment_start_hour']
        duration = config_dict['co2_enrichment_duration']
        strategy = config_dict['co2_enrichment_strategy']
        morning_target = config_dict['co2_morning_target']
        afternoon_target = config_dict['co2_afternoon_target']
        
        if strategy == "morning_only":
            # Enrichment only during specific morning hours
            enrichment_end = start_hour + duration
            if start_hour <= photoperiod_time < enrichment_end:
                return morning_target
            else:
                return afternoon_target
                
        elif strategy == "full_day":
            # Full day enrichment with different targets
            enrichment_end = start_hour + duration
            if start_hour <= photoperiod_time < enrichment_end:
                return morning_target
            else:
                return base_target  # Use original target for rest of day
                
        elif strategy == "adaptive":
            # Adaptive strategy based on photoperiod progress
            # Higher enrichment early, gradual reduction
            enrichment_end = start_hour + duration
            if start_hour <= photoperiod_time < enrichment_end:
                # Gradual reduction during enrichment period
                progress = (photoperiod_time - start_hour) / duration
                return morning_target * (1.0 - 0.3 * progress)  # 30% reduction over time
            else:
                return afternoon_target
        else:
            # Unknown strategy, use base target
            return base_target
    
    def calculate_photoperiod_time(self, current_hour: float, light_start_hour: float = 6.0) -> float:
        """
        Calculate hours elapsed since photoperiod started.
        
        Args:
            current_hour: Current hour of day (0.0-24.0)
            light_start_hour: Hour when lights turn on (default 6:00 AM)
            
        Returns:
            Hours elapsed since photoperiod started (0.0 = lights just turned on)
            Returns -1.0 if lights are currently off
        """
        light_end_hour = light_start_hour + self.setpoints.light_hours
        
        # Handle day rollover
        if light_end_hour > 24.0:
            # Photoperiod crosses midnight
            if current_hour >= light_start_hour or current_hour < (light_end_hour - 24.0):
                if current_hour >= light_start_hour:
                    return current_hour - light_start_hour
                else:
                    return (24.0 - light_start_hour) + current_hour
            else:
                return -1.0  # Lights off
        else:
            # Normal photoperiod within single day
            if light_start_hour <= current_hour < light_end_hour:
                return current_hour - light_start_hour
            else:
                return -1.0  # Lights off
    
    def calculate_co2_control_action(self, current_co2: float, target_co2: float,
                                   light_on: bool = True,
                                   strategy: ControlStrategy = ControlStrategy.PID,
                                   photoperiod_time: float = 0.0,
                                   config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Calculate CO2 control actions with intelligent time-based strategies.
        
        Args:
            current_co2: Current CO2 concentration (μmol/mol)
            target_co2: Target CO2 concentration (μmol/mol)
            light_on: Whether grow lights are currently on
            strategy: Control strategy to use
            photoperiod_time: Hours since photoperiod started (0.0 = start of light period)
            config_dict: Configuration parameters from CSV
            
        Returns:
            Dictionary with control actions and parameters
        """
        # Only enrich during photoperiod (when lights are on)
        if not light_on:
            target_co2 = self.setpoints.ambient_co2
        
        error = target_co2 - current_co2
        
        if strategy == ControlStrategy.PASSIVE:
            return {
                'co2_injection_rate': 0.0,
                'ventilation_increase': 0.0,
                'energy_consumption_kWh': 0.0,
                'co2_cost': 0.0,
                'action': 'ambient'
            }
        
        else:  # Default to PID for any other strategy
            # Time-based CO2 enrichment strategy using CSV parameters
            target_co2 = self._calculate_time_based_co2_target(
                target_co2, photoperiod_time, light_on, config_dict
            )
            error = target_co2 - current_co2
            
            # PID control with intelligent modifications
            params = self.pid_params['co2']
            
            self.integral_errors['co2'] += error
            derivative = error - self.previous_errors['co2']
            self.previous_errors['co2'] = error
            
            pid_output = (params['kp'] * error + 
                         params['ki'] * self.integral_errors['co2'] +
                         params['kd'] * derivative)
            
            # Convert to injection rate (μmol/mol/min)
            if error > self.setpoints.co2_tolerance and light_on:
                injection_rate = min(self.equipment.co2_injection_rate, 
                                   max(0.0, pid_output * 0.5))
                
                # Calculate costs
                co2_volume_L_per_min = injection_rate * 0.001  # Rough conversion
                co2_cost_per_hour = co2_volume_L_per_min * 60 * 0.002  # $0.002/L
                
                return {
                    'co2_injection_rate': injection_rate,
                    'ventilation_increase': 0.0,
                    'energy_consumption_kWh': 0.05,  # Injection system power
                    'co2_cost': co2_cost_per_hour,
                    'action': f'inject_{injection_rate:.1f}μmol/mol/min'
                }
            
            elif error < -self.setpoints.co2_tolerance:
                # Too much CO2 - increase ventilation
                ventilation_increase = min(2.0, abs(error) / 100.0)
                return {
                    'co2_injection_rate': 0.0,
                    'ventilation_increase': ventilation_increase,
                    'energy_consumption_kWh': ventilation_increase * 0.1,
                    'co2_cost': 0.0,
                    'action': f'ventilate_{ventilation_increase:.1f}x'
                }
            else:
                return {
                    'co2_injection_rate': 0.0,
                    'ventilation_increase': 0.0,
                    'energy_consumption_kWh': 0.02,
                    'co2_cost': 0.0,
                    'action': 'maintain'
                }
        
        # Default return case for unhandled strategies
        return {
            'co2_injection_rate': 0.0,
            'ventilation_increase': 0.0,
            'energy_consumption_kWh': 0.0,
            'co2_cost': 0.0,
            'action': 'no_control'
        }
    
    def hourly_update(self, current_conditions: Dict[str, float], hour: int, 
                     dt_hours: float = 1.0, strategy: ControlStrategy = ControlStrategy.PID) -> Dict[str, Any]:
        """
        Hourly environmental control update for DSSAT-style integration.
        
        Real HVAC systems respond within minutes/hours, not daily.
        
        Args:
            current_conditions: Current environmental conditions
            hour: Hour of day (0-23)  
            dt_hours: Time step in hours
            strategy: Control strategy
            
        Returns:
            Dict with control actions and environmental adjustments
        """
        # Determine light status and photoperiod time
        # Use CO2 enrichment start hour as light start hour
        light_start_hour = getattr(self.setpoints, 'co2_enrichment_start_hour', None)
        if light_start_hour is None:
            raise ValueError("❌ CO2 enrichment start hour must be provided in CSV configuration - no hardcoded defaults allowed")
        light_end_hour = light_start_hour + self.setpoints.light_hours
        
        # Handle day rollover for photoperiod
        if light_end_hour > 24.0:
            light_on = (hour >= light_start_hour) or (hour < (light_end_hour - 24.0))
        else:
            light_on = (light_start_hour <= hour < light_end_hour)
            
        photoperiod_time = self.calculate_photoperiod_time(float(hour), light_start_hour)
        
        # Current conditions
        temp = get_required_condition(current_conditions, 'temperature')
        humidity = get_required_condition(current_conditions, 'humidity')
        co2 = get_required_condition(current_conditions, 'co2')
        
        # Target conditions (day/night dependent)
        if light_on:
            target_temp = self.setpoints.day_temp
        else:
            target_temp = self.setpoints.night_temp
            
        # Calculate VPD and target humidity
        current_vpd = calculate_vpd(temp, humidity)
        target_humidity = self._calculate_target_humidity_from_vpd(temp, self.setpoints.target_vpd)
        
        # Control actions
        humidity_action = self.calculate_humidity_control_action(
            humidity, target_humidity, strategy
        )
        
        co2_action = self.calculate_co2_control_action(
            co2, self.setpoints.target_co2, light_on, strategy, 
            photoperiod_time if photoperiod_time >= 0 else 0.0
        )
        
        # Environmental adjustments (what actually happens)
        # Scale by dt_hours for sub-hourly timesteps
        temp_adjustment = self._calculate_temperature_adjustment(temp, target_temp, dt_hours)
        humidity_adjustment = self._apply_humidity_control(humidity, humidity_action, dt_hours)
        co2_adjustment = self._apply_co2_control(co2, co2_action, dt_hours)
        
        # Calculate total energy consumption
        total_energy = (get_required_action_param(humidity_action, 'energy_consumption_kWh') +
                       get_required_action_param(co2_action, 'energy_consumption_kWh')) * dt_hours
        
        return {
            'temperature': temp + temp_adjustment,
            'humidity': humidity + humidity_adjustment,  
            'co2': co2 + co2_adjustment,
            'vpd': calculate_vpd(temp + temp_adjustment, humidity + humidity_adjustment),
            'light_on': light_on,
            'photoperiod_time': photoperiod_time,
            'control_actions': {
                'humidity': humidity_action,
                'co2': co2_action
            },
            'energy_consumption_kWh': total_energy,
            'hourly_cost_usd': 0.0  # Energy cost removed
        }
    
    def _calculate_temperature_adjustment(self, current_temp: float, target_temp: float, dt_hours: float) -> float:
        """Calculate temperature adjustment from heating/cooling systems."""
        temp_error = target_temp - current_temp
        
        # Simple thermal response (would be more complex in real system)
        max_temp_change_per_hour = self.setpoints.max_temperature_change_per_hour  # °C/hour maximum HVAC capacity
        
        # Proportional response with rate limiting
        temp_change = np.sign(temp_error) * min(abs(temp_error), max_temp_change_per_hour * dt_hours)
        
        # Environmental heat gains/losses (passive)
        ambient_temp = self.setpoints.ambient_temperature  # External temperature
        thermal_mass_factor = self.setpoints.thermal_mass_factor  # Building thermal inertia
        passive_change = (ambient_temp - current_temp) * thermal_mass_factor * dt_hours
        
        return temp_change + passive_change
    
    def _apply_humidity_control(self, current_humidity: float, action: Dict[str, float], dt_hours: float) -> float:
        """Apply humidity control actions to calculate actual humidity change."""
        if action['action'] == 'humidify':
            # Humidifier effectiveness
            max_humidity_increase = action['humidifier_power'] * self.equipment.humidifier_efficiency * dt_hours
            return min(max_humidity_increase, 100.0 - current_humidity)
        elif action['action'] == 'dehumidify':
            # Dehumidifier effectiveness  
            max_humidity_decrease = action['dehumidifier_power'] * self.equipment.dehumidifier_efficiency * dt_hours
            return -min(max_humidity_decrease, current_humidity - 10.0)  # Don't go below 10% RH
        else:
            # Natural humidity drift
            return 0.0
    
    def _apply_co2_control(self, current_co2: float, action: Dict[str, float], dt_hours: float) -> float:
        """Apply CO2 control actions to calculate actual CO2 change."""
        injection_rate = get_required_action_param(action, 'co2_injection_rate')  # μmol/mol/min
        ventilation_increase = get_required_action_param(action, 'ventilation_increase')
        
        # CO2 injection effect
        co2_increase = injection_rate * 60.0 * dt_hours  # Convert min to hours
        
        # Natural CO2 losses (ventilation, plant uptake)
        base_loss_rate = self.setpoints.base_co2_loss_rate  # μmol/mol/hour baseline ventilation loss
        enhanced_loss_rate = base_loss_rate * (1.0 + ventilation_increase)
        co2_decrease = enhanced_loss_rate * dt_hours
        
        # Net change with bounds
        net_change = co2_increase - co2_decrease
        new_co2 = current_co2 + net_change
        
        # Clamp to realistic bounds from CSV configuration
        min_co2 = self.setpoints.min_co2_concentration
        max_co2 = self.setpoints.max_co2_concentration
        return max(min_co2, min(max_co2, new_co2)) - current_co2
    
    def _calculate_target_humidity_from_vpd(self, temperature: float, target_vpd: float) -> float:
        """
        Calculate target humidity from temperature and desired VPD.
        
        Args:
            temperature: Air temperature (°C)
            target_vpd: Target vapor pressure deficit (kPa)
            
        Returns:
            Target relative humidity (%)
        """
        # Ensure temperature is real (not complex)
        if isinstance(temperature, complex):
            temperature = temperature.real
        # Saturated vapor pressure using Magnus equation
        es = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
        
        # Target actual vapor pressure
        ea_target = es - target_vpd
        
        # Target relative humidity
        target_rh = (ea_target / es) * 100.0
        
        # Constrain to reasonable bounds
        return max(30.0, min(90.0, target_rh))

    def calculate_comprehensive_control(self, current_conditions: Dict[str, float],
                                      light_schedule: Dict[str, bool],
                                      strategy: ControlStrategy = ControlStrategy.PID) -> Dict[str, any]:
        """
        Calculate comprehensive environmental control actions.
        
        Args:
            current_conditions: Dict with temp, humidity, co2, light_intensity
            light_schedule: Dict with light_on status and timing
            strategy: Control strategy to use
            
        Returns:
            Comprehensive control recommendations and predictions
        """
        temp = current_conditions['temperature']
        rh = current_conditions['humidity']
        co2 = current_conditions['co2']
        light_intensity = get_required_condition(current_conditions, 'light_intensity')
        light_on = get_required_action_param(light_schedule, 'light_on')
        
        # Calculate current VPD
        current_vpd = calculate_vpd(temp, rh)
        
        # Calculate optimal humidity for target VPD
        optimal_rh = self.calculate_optimal_humidity(temp, self.setpoints.target_vpd)
        
        # Calculate plant stress factors
        transp_factor, photo_factor, stress_level = self.calculate_vpd_stress_factor(current_vpd)
        
        # Calculate CO2 photosynthesis enhancement
        co2_factor = self.calculate_co2_photosynthesis_factor(co2, temp, light_intensity)
        
        # Calculate control actions
        humidity_control = self.calculate_humidity_control_action(rh, optimal_rh, strategy)
        co2_control = self.calculate_co2_control_action(co2, self.setpoints.target_co2, light_on, strategy)
        
        # Calculate total energy consumption
        total_energy = (humidity_control['energy_consumption_kWh'] + 
                       co2_control['energy_consumption_kWh'])
        
        # Calculate environmental factors for plant models
        environmental_factors = {
            'vpd_transpiration_factor': transp_factor,
            'vpd_photosynthesis_factor': photo_factor,
            'co2_photosynthesis_factor': co2_factor,
            'combined_photosynthesis_factor': photo_factor * co2_factor,
            'environmental_stress_level': stress_level
        }
        
        # Compile comprehensive results
        return {
            'current_conditions': {
                'vpd_kPa': current_vpd,
                'vpd_optimal': current_vpd >= (self.setpoints.target_vpd - self.setpoints.vpd_tolerance) and 
                              current_vpd <= (self.setpoints.target_vpd + self.setpoints.vpd_tolerance),
                'co2_optimal': abs(co2 - self.setpoints.target_co2) <= self.setpoints.co2_tolerance
            },
            'control_actions': {
                'humidity': humidity_control,
                'co2': co2_control,
                'total_energy_kWh': total_energy,
                'total_operating_cost': co2_control['co2_cost']  # Energy cost removed
            },
            'plant_factors': environmental_factors,
            'recommendations': {
                'target_humidity': optimal_rh,
                'vpd_status': stress_level,
                'priority_action': self._determine_priority_action(current_vpd, co2, light_on),
                'estimated_improvement': self._estimate_growth_improvement(environmental_factors)
            }
        }
    
    def _determine_priority_action(self, current_vpd: float, current_co2: float, light_on: bool) -> str:
        """Determine the highest priority control action."""
        vpd_error = abs(current_vpd - self.setpoints.target_vpd)
        co2_error = abs(current_co2 - self.setpoints.target_co2) if light_on else 0
        
        if vpd_error > self.setpoints.vpd_tolerance * 2:
            return "vpd_control_critical"
        elif co2_error > self.setpoints.co2_tolerance * 2 and light_on:
            return "co2_enrichment_critical"
        elif vpd_error > self.setpoints.vpd_tolerance:
            return "vpd_optimization"
        elif co2_error > self.setpoints.co2_tolerance and light_on:
            return "co2_optimization"
        else:
            return "maintain_conditions"
    
    def _estimate_growth_improvement(self, factors: Dict[str, float]) -> float:
        """Estimate potential growth improvement from environmental optimization."""
        # Combine factors to estimate overall improvement potential
        current_efficiency = (factors['vpd_photosynthesis_factor'] * 
                             factors['co2_photosynthesis_factor'])
        
        # Theoretical maximum if all factors were optimal
        max_efficiency = self.setpoints.max_co2_enhancement_factor  # Max CO2 enhancement from CSV
        
        return min(50.0, (max_efficiency / current_efficiency - 1.0) * 100.0)


def create_lettuce_environmental_control_system(system_config) -> EnvironmentalControlSystem:
    env_setpoints = getattr(system_config, 'environment', {})
    env_params = getattr(system_config, 'environment', {})

    combined_params = env_setpoints.copy()
    combined_params.update(env_params)

    setpoints = EnvironmentalSetpoints.from_config(combined_params)

    env_equipment = getattr(system_config, 'control_equipment_parameters', {})
    equipment = ControlEquipment.from_config(env_equipment)

    return EnvironmentalControlSystem(setpoints, equipment)


"""
INPUT PARAMETERS (from CSV):
- target_vpd: target vapor pressure deficit (kPa)
- vpd_tolerance: acceptable VPD range (kPa)
- min_humidity: minimum relative humidity (%)
- max_humidity: maximum relative humidity (%)
- day_temp: optimal day temperature (°C)
- night_temp: optimal night temperature (°C)
- temp_tolerance: acceptable temperature range (°C)
- target_co2: optimal CO2 concentration (μmol/mol)
- ambient_co2: ambient CO2 level (μmol/mol)
- co2_tolerance: acceptable CO2 tolerance (μmol/mol)
- light_hours: photoperiod duration (hours)
- light_intensity_control: light intensity setpoint (μmol/m²/s)
- co2_enrichment_start_hour: hour to start CO2 enrichment
- humidity_deadband: humidity control deadband
- max_temperature_change_per_hour: maximum temperature change rate (°C/h)
- ambient_temperature: external ambient temperature (°C)
- thermal_mass_factor: building thermal inertia factor
- base_co2_loss_rate: baseline CO2 loss rate (μmol/mol/h)
- min_co2_concentration: minimum CO2 concentration (μmol/mol)
- max_co2_concentration: maximum CO2 concentration (μmol/mol)
- light_saturation_threshold: light saturation threshold (μmol/m²/s)
- co2_response_vmax: CO2 response maximum enhancement factor
- co2_response_km: CO2 response half-saturation constant (μmol/mol)
- max_co2_enhancement_factor: maximum CO2 enhancement factor
- pid_humidity_kp/ki/kd: PID parameters for humidity control
- pid_co2_kp/ki/kd: PID parameters for CO2 control
- pid_temperature_kp/ki/kd: PID parameters for temperature control
- humidifier_capacity: humidifier water addition rate (L/h)
- dehumidifier_capacity: dehumidifier water removal rate (L/h)
- humidifier_efficiency: humidifier efficiency factor
- dehumidifier_efficiency: dehumidifier efficiency factor
- co2_injection_rate: maximum CO2 injection rate (μmol/mol/min)
- co2_sensor_accuracy: CO2 sensor precision (±μmol/mol)
- co2_mixing_time: CO2 mixing time (minutes)
- air_exchange_rate: air changes per hour
- circulation_fan_power: fan power consumption (W)

INPUT VARIABLES:
- current_conditions['temperature']: current air temperature (°C)
- current_conditions['humidity']: current relative humidity (%)
- current_conditions['co2']: current CO2 concentration (μmol/mol)
- current_conditions['light_intensity']: current light intensity (μmol/m²/s)
- light_schedule['light_on']: light status (boolean)
- hour: current hour of day (0-23)
- dt_hours: time step duration (hours)
- strategy: control strategy (ControlStrategy enum)

OUTPUT VARIABLES:
- temperature: adjusted temperature (°C)
- humidity: adjusted humidity (%)
- co2: adjusted CO2 concentration (μmol/mol)
- vpd: calculated vapor pressure deficit (kPa)
- light_on: light status (boolean)
- photoperiod_time: hours elapsed since photoperiod start
- control_actions: dictionary of control actions and power consumption
- energy_consumption_kWh: total energy consumption (kWh)
- co2_photosynthesis_factor: CO2 enhancement factor for photosynthesis
- vpd_transpiration_factor: VPD effect on transpiration
- vpd_photosynthesis_factor: VPD effect on photosynthesis
- environmental_stress_level: plant stress level classification
"""
