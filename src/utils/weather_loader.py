"""
Weather Data Loader Utility

Loads daily weather data strictly - no defaults.
Follows Rules.md - no default values allowed.
"""

import pandas as pd
from typing import Dict, Any, Optional
import os


class WeatherDataError(Exception):
    """Exception raised when weather data loading fails"""
    pass


class WeatherDataLoader:
    """Loads daily weather data strictly - no defaults"""

    def __init__(self, weather_csv_path: str, simulation_start_date: str = None):
        self.weather_csv_path = weather_csv_path
        self.simulation_start_date = simulation_start_date
        self.weather_data = None
        self._load_weather_data()

    def _load_weather_data(self):
        """Load weather data from CSV file"""
        if not os.path.exists(self.weather_csv_path):
            raise WeatherDataError(f"Weather data file not found: {self.weather_csv_path}")
        
        try:
            self.weather_data = pd.read_csv(self.weather_csv_path)
            
            # Map actual column names to expected names
            column_mapping = {
                'temp_avg': 'temperature',
                'temp_min': 'temperature_min',
                'temp_max': 'temperature_max',
                'rel_humidity': 'humidity',
                'par': 'light_intensity',
                'co2_ppm': 'co2_concentration',
                'rainfall': 'precipitation'
            }

            # Rename columns to standard names
            self.weather_data = self.weather_data.rename(columns=column_mapping)

            # Add vpd and rzt to expected columns since they're in the CSV
            # These don't need mapping as they're already correctly named
            
            # Validate required columns
            required_columns = ['date', 'temperature', 'humidity', 'light_intensity', 'co2_concentration']
            missing_columns = [col for col in required_columns if col not in self.weather_data.columns]
            
            if missing_columns:
                raise WeatherDataError(f"Missing required weather columns: {missing_columns}")
            
            # Convert date column to datetime
            self.weather_data['date'] = pd.to_datetime(self.weather_data['date'])
            
            # Verify weather data dates align with simulation start date
            if self.simulation_start_date:
                self._verify_date_alignment()
            
            # Validate data quality
            if self.weather_data.empty:
                raise WeatherDataError("Weather data is empty - no defaults allowed")
            
            # Check for missing values
            missing_data = self.weather_data[required_columns].isnull().any()
            if missing_data.any():
                missing_cols = missing_data[missing_data].index.tolist()
                raise WeatherDataError(f"Missing weather data in columns: {missing_cols} - no defaults allowed")
            
        except Exception as e:
            raise WeatherDataError(f"Failed to load weather data from {self.weather_csv_path}: {e}")

    def _verify_date_alignment(self):
        """Verify that weather data dates align with simulation start date"""
        try:
            # Convert simulation start date to datetime
            simulation_start = pd.to_datetime(self.simulation_start_date)
            
            # Get first weather data date
            first_weather_date = self.weather_data['date'].iloc[0]
            
            # Check if first weather date matches simulation start date
            if first_weather_date.date() != simulation_start.date():
                raise WeatherDataError(
                    f"Weather data start date ({first_weather_date.date()}) does not match "
                    f"simulation start date ({simulation_start.date()}). "
                    f"Weather data must start from simulation start date."
                )
            
            # Verify weather data is sequential (no gaps or duplicates)
            date_diffs = self.weather_data['date'].diff().dt.days
            non_sequential_days = date_diffs[date_diffs != 1].dropna()
            
            if not non_sequential_days.empty:
                raise WeatherDataError(
                    f"Weather data contains non-sequential dates. "
                    f"Found gaps or duplicates at positions: {non_sequential_days.index.tolist()}"
                )
            
            print(f"✓ Weather data dates verified: {len(self.weather_data)} days starting from {simulation_start.date()}")
            
        except Exception as e:
            raise WeatherDataError(f"Date verification failed: {e}")

    def get_weather_for_day(self, day: int) -> Dict[str, Any]:
        """Get weather data for specific day"""
        if self.weather_data is None:
            raise WeatherDataError("Weather data not loaded")
        
        if day < 1 or day > len(self.weather_data):
            raise WeatherDataError(f"Day {day} out of range (1-{len(self.weather_data)})")
        
        row = self.weather_data.iloc[day - 1]  # Convert to 0-based index
        
        return {
            'date': row['date'],
            'temperature': float(row['temperature']),
            'temperature_min': float(row['temperature_min']),
            'temperature_max': float(row['temperature_max']),
            'humidity': float(row['humidity']),
            'light_intensity': float(row['light_intensity']),
            'solar_radiation': float(row['solar_radiation']),
            'co2_concentration': float(row['co2_concentration']),
            'wind_speed': float(row['wind_speed']),
            'precipitation': float(row['precipitation'])
        }

    def get_weather_for_hour(self, day: int, hour: int) -> Dict[str, Any]:
        """Get weather data for specific hour (interpolated from daily data using diurnal patterns)"""
        daily_weather = self.get_weather_for_day(day)
        
        # Use sophisticated diurnal patterns from core_utils
        from .core_utils import create_hourly_interpolation
        
        # Get daily values for interpolation
        temp_min = daily_weather.get('temperature_min')
        
        if temp_min is None:
            raise ValueError("Temperature minimum missing from weather data - no defaults allowed")
        temp_max = daily_weather.get('temperature_max')
        humidity = daily_weather['humidity']
        solar_radiation = daily_weather.get('solar_radiation')
        
        if temp_max is None or solar_radiation is None:
            raise ValueError("Required weather data missing from CSV - no defaults allowed")
        
        # Create hourly interpolation
        hourly_data = create_hourly_interpolation(temp_min, temp_max, humidity, solar_radiation)
        
        # Get the specific hour data
        hour_data = hourly_data[hour]
        
        return {
            'date': daily_weather['date'],
            'hour': hour,
            'temperature': hour_data['temperature'],
            'humidity': hour_data['humidity'],
            'light_intensity': daily_weather['light_intensity'] * self._get_hourly_light_factor(hour),
            'solar_radiation': hour_data['solar_radiation'],
            'vpd': hour_data['vpd'],
            'co2_concentration': daily_weather['co2_concentration'],
            'wind_speed': daily_weather['wind_speed'],
            'precipitation': daily_weather['precipitation']
        }

    def _get_hourly_light_factor(self, hour: int) -> float:
        """Get light intensity factor for specific hour (0-23)"""
        # Simple diurnal light pattern
        if 6 <= hour <= 18:  # Daylight hours
            # Peak at noon (hour 12)
            if hour <= 12:
                return (hour - 6) / 6.0  # 0 to 1 from 6am to noon
            else:
                return (18 - hour) / 6.0  # 1 to 0 from noon to 6pm
        else:
            return 0.0  # No light at night

    def get_total_days(self) -> int:
        """Get total number of days in weather data"""
        if self.weather_data is None:
            return 0
        return len(self.weather_data)

    def get_date_range(self) -> tuple:
        """Get date range of weather data"""
        if self.weather_data is None or self.weather_data.empty:
            return None, None
        
        return self.weather_data['date'].min(), self.weather_data['date'].max()

    def validate_weather_data(self) -> bool:
        """Validate weather data quality"""
        if self.weather_data is None or self.weather_data.empty:
            return False
        
        # Check for reasonable value ranges
        temp_range = (0, 50)  # Celsius
        humidity_range = (0, 100)  # Percentage
        light_range = (0, 2000)  # μmol/m²/s
        co2_range = (300, 1000)  # ppm
        
        checks = [
            self.weather_data['temperature'].between(*temp_range).all(),
            self.weather_data['humidity'].between(*humidity_range).all(),
            self.weather_data['light_intensity'].between(*light_range).all(),
            self.weather_data['co2_concentration'].between(*co2_range).all()
        ]
        
        return all(checks)
