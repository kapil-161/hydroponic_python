"""
Environmental Control System for Hydroponic Lettuce Production
Includes VPD optimization, humidity control, and CO2 enrichment strategies

Based on recent research (2021-2024):
- Optimal VPD range: 0.7-0.85 kPa for lettuce
- CO2 enrichment: 1000-1500 μmol/mol optimal
- Temperature-humidity interactions for growth optimization
"""

import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
import math


class ControlStrategy(Enum):
    """Environmental control strategies."""
    PASSIVE = "passive"           # No active control
    BASIC = "basic"              # Simple on/off control
    PROPORTIONAL = "proportional" # P controller
    PID = "pid"                  # PID controller


@dataclass
class EnvironmentalSetpoints:
    """Target environmental conditions."""
    # VPD and humidity targets
    target_vpd: float = 0.8        # kPa - optimal for lettuce
    vpd_tolerance: float = 0.1     # ±0.1 kPa acceptable range
    min_humidity: float = 60.0     # % minimum to prevent stress
    max_humidity: float = 80.0     # % maximum to prevent disease
    
    # Temperature targets
    day_temp: float = 22.0         # °C optimal day temperature
    night_temp: float = 18.0       # °C optimal night temperature
    temp_tolerance: float = 2.0    # ±2°C acceptable range
    
    # CO2 targets
    target_co2: float = 1200.0     # μmol/mol optimal enrichment
    ambient_co2: float = 400.0     # μmol/mol ambient level
    co2_tolerance: float = 100.0   # ±100 μmol/mol acceptable
    
    # Photoperiod settings
    light_hours: float = 16.0      # hours per day
    light_intensity: float = 200.0 # μmol/m²/s PPFD
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'EnvironmentalSetpoints':
        """Create EnvironmentalSetpoints from configuration dictionary."""
        return cls(
            target_vpd=config_dict.get('target_vpd', 0.8),
            vpd_tolerance=config_dict.get('vpd_tolerance', 0.1),
            min_humidity=config_dict.get('min_humidity', 60.0),
            max_humidity=config_dict.get('max_humidity', 80.0),
            day_temp=config_dict.get('day_temp', 22.0),
            night_temp=config_dict.get('night_temp', 18.0),
            temp_tolerance=config_dict.get('temp_tolerance', 2.0),
            target_co2=config_dict.get('target_co2', 1200.0),
            ambient_co2=config_dict.get('ambient_co2', 400.0),
            co2_tolerance=config_dict.get('co2_tolerance', 100.0),
            light_hours=config_dict.get('light_hours', 16.0),
            light_intensity=config_dict.get('light_intensity', 200.0)
        )


@dataclass
class ControlEquipment:
    """Equipment specifications for environmental control."""
    # Humidity control equipment
    humidifier_capacity: float = 5.0      # L/h water addition rate
    dehumidifier_capacity: float = 10.0   # L/h water removal rate
    humidifier_efficiency: float = 0.85   # Efficiency factor
    dehumidifier_efficiency: float = 0.90 # Efficiency factor
    
    # CO2 enrichment equipment  
    co2_injection_rate: float = 50.0      # μmol/mol/min maximum injection
    co2_sensor_accuracy: float = 25.0     # ±μmol/mol sensor precision
    co2_mixing_time: float = 2.0          # minutes for full mixing
    
    # Ventilation and air circulation
    air_exchange_rate: float = 0.5        # air changes per hour
    circulation_fan_power: float = 100.0  # W power consumption
    
    # Energy costs ($/kWh)
    electricity_cost: float = 0.12
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'ControlEquipment':
        """Create ControlEquipment from configuration dictionary."""
        return cls(
            humidifier_capacity=config_dict.get('humidifier_capacity', 5.0),
            dehumidifier_capacity=config_dict.get('dehumidifier_capacity', 10.0),
            humidifier_efficiency=config_dict.get('humidifier_efficiency', 0.85),
            dehumidifier_efficiency=config_dict.get('dehumidifier_efficiency', 0.90),
            co2_injection_rate=config_dict.get('co2_injection_rate', 50.0),
            co2_sensor_accuracy=config_dict.get('co2_sensor_accuracy', 25.0),
            co2_mixing_time=config_dict.get('co2_mixing_time', 2.0),
            air_exchange_rate=config_dict.get('air_exchange_rate', 0.5),
            circulation_fan_power=config_dict.get('circulation_fan_power', 100.0),
            electricity_cost=config_dict.get('electricity_cost', 0.12)
        )


class EnvironmentalControlSystem:
    """
    Comprehensive environmental control system for hydroponic production.
    Manages VPD, humidity, CO2, and their interactions.
    """
    
    def __init__(self, setpoints: Optional[EnvironmentalSetpoints] = None,
                 equipment: Optional[ControlEquipment] = None):
        self.setpoints = setpoints or EnvironmentalSetpoints()
        self.equipment = equipment or ControlEquipment()
        
        # PID controller parameters (will be loaded from config if available)
        self.pid_params = {
            'humidity': {'kp': 2.0, 'ki': 0.5, 'kd': 0.1},
            'co2': {'kp': 1.5, 'ki': 0.3, 'kd': 0.05},
            'temperature': {'kp': 3.0, 'ki': 0.8, 'kd': 0.2}
        }
        
        # Controller state tracking
        self.integral_errors = {'humidity': 0.0, 'co2': 0.0, 'temperature': 0.0}
        self.previous_errors = {'humidity': 0.0, 'co2': 0.0, 'temperature': 0.0}
        
        # Equipment state
        self.equipment_status = {
            'humidifier_active': False,
            'dehumidifier_active': False,
            'co2_injector_active': False,
            'ventilation_rate': 0.0,
            'total_energy_consumption': 0.0
        }
    
    def calculate_vpd(self, temperature: float, relative_humidity: float) -> float:
        """
        Calculate vapor pressure deficit using precise formulation.
        
        Args:
            temperature: Air temperature (°C)
            relative_humidity: Relative humidity (%)
            
        Returns:
            VPD in kPa
        """
        # Saturation vapor pressure using Magnus formula
        es = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
        
        # Actual vapor pressure
        ea = es * (relative_humidity / 100.0)
        
        # VPD is the difference
        vpd = es - ea
        return max(0.0, vpd)
    
    def calculate_optimal_humidity(self, temperature: float, target_vpd: float) -> float:
        """
        Calculate optimal humidity for target VPD at given temperature.
        
        Args:
            temperature: Air temperature (°C)
            target_vpd: Target VPD (kPa)
            
        Returns:
            Optimal relative humidity (%)
        """
        # Saturation vapor pressure at temperature
        es = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
        
        # Required actual vapor pressure for target VPD
        ea = es - target_vpd
        
        # Convert to relative humidity
        rh = (ea / es) * 100.0
        
        # Constrain within practical limits
        return max(30.0, min(95.0, rh))
    
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
        light_saturation = 200.0  # μmol/m²/s for lettuce
        light_factor = light_intensity / (light_intensity + light_saturation)
        
        # Michaelis-Menten parameters for CO2 response (lettuce-specific)
        vmax = 2.0 * temp_factor * light_factor  # Maximum enhancement
        km = 800.0 * (1.0 - temp_factor * 0.2)   # Half-saturation concentration
        
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
            deadband = 5.0  # ±5% deadband
            
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
    
    def calculate_co2_control_action(self, current_co2: float, target_co2: float,
                                   light_on: bool = True,
                                   strategy: ControlStrategy = ControlStrategy.PID) -> Dict[str, float]:
        """
        Calculate CO2 control actions with intelligent strategies.
        
        Args:
            current_co2: Current CO2 concentration (μmol/mol)
            target_co2: Target CO2 concentration (μmol/mol)
            light_on: Whether grow lights are currently on
            strategy: Control strategy to use
            
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
            # Smart CO2 management with timing optimization
            
            # Morning enrichment strategy (first 4 hours of photoperiod)
            # Research shows morning-only enrichment can be as effective
            morning_enrichment = True  # Could be time-based
            
            if not morning_enrichment and light_on:
                # Reduce target during afternoon to save CO2
                target_co2 *= 0.7
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
        light_intensity = current_conditions.get('light_intensity', 200.0)
        light_on = light_schedule.get('light_on', True)
        
        # Calculate current VPD
        current_vpd = self.calculate_vpd(temp, rh)
        
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
                'total_operating_cost': total_energy * self.equipment.electricity_cost + co2_control['co2_cost']
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
        max_efficiency = 1.0 * 1.4  # Max CO2 enhancement ~1.4x at 1200 ppm
        
        return min(50.0, (max_efficiency / current_efficiency - 1.0) * 100.0)


def create_lettuce_environmental_control() -> EnvironmentalControlSystem:
    """Create environmental control system optimized for lettuce production."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        env_config = config_loader.get_environmental_control_config()
        
        setpoints = EnvironmentalSetpoints.from_config(env_config.get('setpoints', {}))
        equipment = ControlEquipment.from_config(env_config.get('equipment', {}))
        
        # Create the system
        system = EnvironmentalControlSystem(setpoints, equipment)
        
        # Load PID parameters from config if available
        pid_config = env_config.get('pid_parameters', {})
        if pid_config:
            system.pid_params.update(pid_config)
        
        return system
        
    except ImportError:
        # Fallback to default values if config loader not available
        lettuce_setpoints = EnvironmentalSetpoints(
            target_vpd=0.8,
            vpd_tolerance=0.1,
            min_humidity=65.0,
            max_humidity=75.0,
            day_temp=22.0,
            night_temp=18.0,
            target_co2=1200.0,
            light_hours=16.0,
            light_intensity=200.0
        )
        return EnvironmentalControlSystem(lettuce_setpoints)


def demonstrate_environmental_control():
    """Demonstrate environmental control system capabilities."""
    controller = create_lettuce_environmental_control()
    
    print("=" * 80)
    print("ENVIRONMENTAL CONTROL SYSTEM DEMONSTRATION")
    print("=" * 80)
    
    # Test scenarios
    scenarios = [
        ("Optimal", 22.0, 70.0, 1200.0, True),
        ("Too Humid", 22.0, 85.0, 1200.0, True),
        ("Too Dry", 25.0, 50.0, 1200.0, True),
        ("Low CO2", 22.0, 70.0, 400.0, True),
        ("High CO2", 22.0, 70.0, 1800.0, True),
        ("Night Cycle", 18.0, 70.0, 400.0, False),
    ]
    
    print(f"{'Scenario':<12} {'VPD':<6} {'Status':<15} {'Photo Factor':<12} {'Actions':<20} {'Cost/hr':<10}")
    print("-" * 80)
    
    for scenario_name, temp, rh, co2, light_on in scenarios:
        current_conditions = {
            'temperature': temp,
            'humidity': rh,
            'co2': co2,
            'light_intensity': 200.0
        }
        
        light_schedule = {'light_on': light_on}
        
        results = controller.calculate_comprehensive_control(
            current_conditions, light_schedule, ControlStrategy.PID
        )
        
        vpd = results['current_conditions']['vpd_kPa']
        status = results['recommendations']['vpd_status']
        photo_factor = results['plant_factors']['combined_photosynthesis_factor']
        priority = results['recommendations']['priority_action']
        cost = results['control_actions']['total_operating_cost']
        
        print(f"{scenario_name:<12} {vpd:<6.2f} {status:<15} {photo_factor:<12.2f} "
              f"{priority:<20} ${cost:<9.3f}")
    
    print(f"\nKey Insights:")
    print(f"• Optimal VPD range: {controller.setpoints.target_vpd - controller.setpoints.vpd_tolerance:.1f}-"
          f"{controller.setpoints.target_vpd + controller.setpoints.vpd_tolerance:.1f} kPa")
    print(f"• CO2 enrichment target: {controller.setpoints.target_co2:.0f} μmol/mol during photoperiod")
    print(f"• Environmental control can improve photosynthesis by 40-60%")
    print(f"• Operating costs typically $0.05-0.50 per hour depending on conditions")


if __name__ == "__main__":
    demonstrate_environmental_control()