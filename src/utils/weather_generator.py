"""
Weather Data Generator for Hydroponic Simulation
Generates realistic weather data for testing and simulation
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List
import math

from ..data.hydroponic_system import WeatherData


class WeatherGenerator:
    """Generate synthetic weather data for hydroponic simulations."""
    
    def __init__(self, base_temp: float = 22.0, temp_variation: float = 5.0,
                 base_humidity: float = 70.0, base_solar: float = 18.0):
        """
        Initialize weather generator.
        
        Args:
            base_temp: Base temperature (°C)
            temp_variation: Temperature variation range (°C)
            base_humidity: Base relative humidity (%)
            base_solar: Base solar radiation (MJ/m²/day)
        """
        self.base_temp = base_temp
        self.temp_variation = temp_variation
        self.base_humidity = base_humidity
        self.base_solar = base_solar
        
    def generate_weather_series(self, start_date: datetime, days: int, 
                               location: str = "USGA") -> List[WeatherData]:
        """
        Generate a series of daily weather data.
        
        Args:
            start_date: Starting date for weather series
            days: Number of days to generate
            location: Location identifier
            
        Returns:
            List of WeatherData objects
        """
        weather_data = []
        
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            
            # Add seasonal variation (simplified sinusoidal)
            day_of_year = current_date.timetuple().tm_yday
            seasonal_factor = math.sin(2 * math.pi * (day_of_year - 80) / 365)
            
            # Temperature with daily and seasonal variation
            temp_avg = (self.base_temp + 
                       self.temp_variation * seasonal_factor + 
                       np.random.normal(0, 1.0))
            
            temp_min = temp_avg - np.random.uniform(2, 5)
            temp_max = temp_avg + np.random.uniform(3, 7)
            
            # Solar radiation with seasonal and random variation
            solar_rad = (self.base_solar + 
                        5 * seasonal_factor + 
                        np.random.normal(0, 2.0))
            solar_rad = max(5.0, solar_rad)  # Minimum solar radiation
            
            # Relative humidity with some variation
            rel_humidity = (self.base_humidity + 
                           np.random.normal(0, 5.0))
            rel_humidity = max(30.0, min(95.0, rel_humidity))  # Bound between 30-95%
            
            # Wind speed (typical greenhouse conditions)
            wind_speed = max(0.5, np.random.uniform(1.5, 3.0))
            
            # Minimal rainfall for greenhouse conditions
            rainfall = 0.0
            
            weather_data.append(WeatherData(
                date=current_date,
                temp_avg=temp_avg,
                temp_min=temp_min,
                temp_max=temp_max,
                solar_radiation=solar_rad,
                rel_humidity=rel_humidity,
                wind_speed=wind_speed,
                rainfall=rainfall
            ))
            
        return weather_data
    
    def generate_from_template(self, template_type: str = "spring",
                              start_date: datetime = None, days: int = 30) -> List[WeatherData]:
        """
        Generate weather data from predefined templates.
        
        Args:
            template_type: Type of weather template ('spring', 'summer', 'fall', 'winter')
            start_date: Starting date (default: today)
            days: Number of days to generate
            
        Returns:
            List of WeatherData objects
        """
        if start_date is None:
            start_date = datetime.now()
            
        templates = {
            'spring': {'base_temp': 18.0, 'temp_var': 4.0, 'humidity': 65.0, 'solar': 16.0},
            'summer': {'base_temp': 25.0, 'temp_var': 6.0, 'humidity': 60.0, 'solar': 22.0},
            'fall': {'base_temp': 15.0, 'temp_var': 5.0, 'humidity': 75.0, 'solar': 12.0},
            'winter': {'base_temp': 10.0, 'temp_var': 3.0, 'humidity': 80.0, 'solar': 8.0}
        }
        
        if template_type not in templates:
            template_type = 'spring'
            
        template = templates[template_type]
        
        # Temporarily adjust generator parameters
        original_params = (self.base_temp, self.temp_variation, 
                          self.base_humidity, self.base_solar)
        
        self.base_temp = template['base_temp']
        self.temp_variation = template['temp_var']
        self.base_humidity = template['humidity']
        self.base_solar = template['solar']
        
        # Generate weather data
        weather_data = self.generate_weather_series(start_date, days)
        
        # Restore original parameters
        (self.base_temp, self.temp_variation, 
         self.base_humidity, self.base_solar) = original_params
        
        return weather_data


