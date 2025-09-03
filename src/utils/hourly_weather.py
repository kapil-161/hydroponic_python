"""
Hourly Weather Interpolation Utilities
Implements DSSAT-style hourly weather interpolation from daily data
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
from ..data.hydroponic_system import WeatherData


@dataclass
class HourlyWeather:
    """Hourly weather conditions interpolated from daily data."""
    hour: int                    # Hour of day (0-23)
    temperature: float          # Air temperature (°C)
    humidity: float             # Relative humidity (%)
    par: float                  # Photosynthetic active radiation (μmol/m²/s)
    solar_radiation: float      # Solar radiation (MJ/m²/h)
    vpd: float                  # Vapor pressure deficit (kPa)
    wind_speed: float           # Wind speed (m/s)
    co2: float                  # CO2 concentration (ppm)


class HourlyWeatherInterpolator:
    """
    Converts daily weather data to hourly using DSSAT-style interpolation methods.
    
    Based on DSSAT's approach for generating realistic diurnal cycles
    from daily weather inputs.
    """
    
    def __init__(self):
        # Diurnal curve parameters (based on DSSAT algorithms)
        self.temp_curve_params = {
            'min_hour': 6.0,      # Hour of minimum temperature
            'max_hour': 14.0,     # Hour of maximum temperature
            'curve_shape': 0.8    # Shape parameter for temperature curve
        }
        
        self.solar_curve_params = {
            'sunrise_offset': -1.0,  # Hours before sunrise for light start
            'sunset_offset': 1.0,    # Hours after sunset for light end
            'curve_shape': 1.2       # Shape parameter for solar curve
        }
        
        self.humidity_curve_params = {
            'phase_offset': 12.0,    # Phase offset from temperature (hours)
            'amplitude_factor': 0.6   # Amplitude factor for RH variation
        }
    
    def interpolate_daily_to_hourly(self, daily_weather: WeatherData, 
                                   day_of_year: int, latitude: float = 40.0, 
                                   system_co2: float = 400.0) -> List[HourlyWeather]:
        """
        Interpolate daily weather to 24 hourly values using DSSAT approach.
        
        Args:
            daily_weather: Daily weather data
            day_of_year: Day of year (1-365)
            latitude: Latitude in degrees for daylength calculation
            
        Returns:
            List of 24 HourlyWeather objects
        """
        hourly_data = []
        
        # Calculate daylength and sun angles
        daylength, sunrise_hour, sunset_hour = self._calculate_daylength(day_of_year, latitude)
        
        for hour in range(24):
            # Temperature interpolation (DSSAT algorithm)
            temp = self._interpolate_temperature(hour, daily_weather.temp_avg, 
                                                daily_weather.temp_min, daily_weather.temp_max)
            
            # Solar radiation and PAR (DSSAT algorithm)
            solar_rad, par = self._interpolate_solar_radiation(
                hour, daily_weather.solar_radiation, sunrise_hour, sunset_hour, daylength
            )
            
            # Humidity interpolation (inverse temperature relationship)
            humidity = self._interpolate_humidity(hour, daily_weather.rel_humidity, temp, 
                                                 daily_weather.temp_avg)
            
            # Calculate VPD from temperature and humidity
            vpd = self._calculate_vpd(temp, humidity)
            
            # Wind speed (simple diurnal variation)
            wind_speed = self._interpolate_wind_speed(hour, getattr(daily_weather, 'wind_speed', 2.0))
            
            # CO2 comes from system configuration
            co2 = system_co2
            
            hourly_weather = HourlyWeather(
                hour=hour,
                temperature=temp,
                humidity=humidity,
                par=par,
                solar_radiation=solar_rad,
                vpd=vpd,
                wind_speed=wind_speed,
                co2=co2
            )
            
            hourly_data.append(hourly_weather)
        
        return hourly_data
    
    def _calculate_daylength(self, day_of_year: int, latitude: float) -> Tuple[float, float, float]:
        """
        Calculate daylength, sunrise, and sunset hours.
        Based on astronomical calculations used in DSSAT.
        """
        # Solar declination angle
        declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
        
        # Hour angle at sunrise/sunset
        lat_rad = math.radians(latitude)
        dec_rad = math.radians(declination)
        
        # Calculate hour angle
        try:
            # Clamp the argument to prevent complex numbers from acos
            acos_arg = -math.tan(lat_rad) * math.tan(dec_rad)
            acos_arg = max(-1.0, min(1.0, acos_arg))  # Ensure valid range for acos
            hour_angle = math.acos(acos_arg)
            hour_angle_deg = math.degrees(hour_angle)
        except ValueError:
            # Handle polar day/night cases
            if latitude * declination > 0:
                hour_angle_deg = 180.0  # Polar day
            else:
                hour_angle_deg = 0.0    # Polar night
        
        # Convert to hours
        daylength = 2.0 * hour_angle_deg / 15.0  # 15 degrees per hour
        sunrise_hour = 12.0 - daylength / 2.0
        sunset_hour = 12.0 + daylength / 2.0
        
        # Constrain to realistic bounds
        daylength = max(0.0, min(24.0, daylength))
        sunrise_hour = max(0.0, min(24.0, sunrise_hour))
        sunset_hour = max(0.0, min(24.0, sunset_hour))
        
        return daylength, sunrise_hour, sunset_hour
    
    def _interpolate_temperature(self, hour: int, temp_avg: float, 
                                temp_min: float, temp_max: float) -> float:
        """
        Interpolate hourly temperature using DSSAT's temperature curve.
        
        Based on sinusoidal approximation with phase shift.
        """
        # Phase shift for temperature curve (minimum at ~6 AM, maximum at ~2 PM)
        phase_shift = (self.temp_curve_params['min_hour'] - 6.0) / 24.0 * 2.0 * math.pi
        hour_angle = (hour / 24.0) * 2.0 * math.pi + phase_shift
        
        # Temperature amplitude
        temp_amplitude = (temp_max - temp_min) / 2.0
        temp_mean = (temp_max + temp_min) / 2.0
        
        # Sinusoidal temperature variation
        temperature = temp_mean - temp_amplitude * math.cos(hour_angle)
        
        # Ensure temperature is real (not complex)
        if isinstance(temperature, complex):
            temperature = temperature.real
        
        # Apply curve shaping to make more realistic
        shape_factor = self.temp_curve_params['curve_shape']
        if shape_factor != 1.0:
            normalized_temp = (temperature - temp_min) / max(0.1, temp_max - temp_min)
            shaped_temp = normalized_temp ** shape_factor
            temperature = temp_min + shaped_temp * (temp_max - temp_min)
        
        return temperature
    
    def _interpolate_solar_radiation(self, hour: int, daily_solar: float, 
                                   sunrise_hour: float, sunset_hour: float, 
                                   daylength: float) -> Tuple[float, float]:
        """
        Interpolate hourly solar radiation and PAR using DSSAT approach.
        
        Returns:
            Tuple of (solar_radiation_MJ/m²/h, PAR_μmol/m²/s)
        """
        if hour < sunrise_hour or hour > sunset_hour:
            return 0.0, 0.0
        
        if daylength <= 0:
            return 0.0, 0.0
        
        # Solar angle calculation (simplified sine curve)
        solar_noon = (sunrise_hour + sunset_hour) / 2.0
        hour_from_noon = hour - solar_noon
        max_hour_angle = daylength / 2.0
        
        if abs(hour_from_noon) > max_hour_angle:
            return 0.0, 0.0
        
        # Sine curve for solar radiation
        angle_fraction = abs(hour_from_noon) / max_hour_angle
        sine_elevation = math.sin(math.pi * (1.0 - angle_fraction) / 2.0)
        
        # Apply curve shaping
        shaped_elevation = sine_elevation ** self.solar_curve_params['curve_shape']
        
        # Hourly solar radiation (MJ/m²/h)
        # Convert daily to hourly assuming all radiation during daylight hours
        peak_hourly_solar = daily_solar * math.pi / (2.0 * daylength)  # Peak value
        hourly_solar = peak_hourly_solar * shaped_elevation
        
        # Convert to PAR (μmol/m²/s)
        # 1 MJ/m²/h = 277.8 W/m²
        # Assume 50% of solar radiation is PAR
        # 1 W/m² PAR ≈ 4.6 μmol/m²/s
        solar_watts = hourly_solar * 277.8
        par_fraction = 0.45  # Fraction of solar radiation that is PAR
        par_umol = solar_watts * par_fraction * 4.6
        
        return hourly_solar, par_umol
    
    def _interpolate_humidity(self, hour: int, daily_humidity: float, 
                            hourly_temp: float, daily_temp_avg: float) -> float:
        """
        Interpolate hourly relative humidity.
        
        RH typically varies inversely with temperature during the day.
        """
        # Base humidity variation (typically higher at night, lower during day)
        hour_angle = (hour / 24.0) * 2.0 * math.pi
        phase_shift = (self.humidity_curve_params['phase_offset'] / 24.0) * 2.0 * math.pi
        
        # Humidity amplitude based on temperature variation
        humidity_amplitude = self.humidity_curve_params['amplitude_factor'] * 15.0  # ±15% variation
        
        # Sinusoidal variation (opposite phase to temperature)
        humidity_variation = humidity_amplitude * math.cos(hour_angle + phase_shift)
        
        # Temperature effect on humidity (approximate)
        temp_effect = -(hourly_temp - daily_temp_avg) * 2.0  # ~2% RH per °C
        
        # Combine effects
        hourly_humidity = daily_humidity + humidity_variation + temp_effect
        
        # Ensure hourly_humidity is real (not complex) before constraining
        if isinstance(hourly_humidity, complex):
            hourly_humidity = hourly_humidity.real
        
        # Constrain to realistic bounds
        hourly_humidity = max(10.0, min(100.0, hourly_humidity))
        
        return hourly_humidity
    
    def _interpolate_wind_speed(self, hour: int, daily_wind: float) -> float:
        """
        Simple diurnal wind speed variation.
        Generally higher during day, lower at night.
        """
        # Simple diurnal pattern - higher during day
        hour_angle = (hour / 24.0) * 2.0 * math.pi
        diurnal_factor = 0.8 + 0.4 * math.sin(hour_angle - math.pi/2)  # Peak at noon
        
        return daily_wind * diurnal_factor
    
    def _calculate_vpd(self, temperature: float, humidity: float) -> float:
        """
        Calculate vapor pressure deficit from temperature and humidity.
        Uses centralized utility function to avoid duplication.
        
        Args:
            temperature: Air temperature (°C)
            humidity: Relative humidity (%)
            
        Returns:
            VPD in kPa
        """
        from ..utils.temperature_utils import calculate_vpd
        return calculate_vpd(temperature, humidity)


def create_hourly_weather_interpolator() -> HourlyWeatherInterpolator:
    """Create an hourly weather interpolator with default parameters."""
    return HourlyWeatherInterpolator()