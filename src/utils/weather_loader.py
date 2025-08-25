"""
Weather Data Loader for Hydroponic Simulation
Loads weather data from CSV files
"""

import pandas as pd
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from ..data.hydroponic_system import WeatherData


class WeatherLoader:
    """Load weather data from CSV files."""
    
    def __init__(self, csv_path: str = None, experiment_code: str = None, config_dir: str = "input"):
        """
        Initialize weather loader.
        
        Args:
            csv_path: Direct path to weather CSV file
            experiment_code: Experiment code (e.g., 'LET_EXP001_2024') - will look for {experiment_code}_weather.csv
            config_dir: Directory containing weather files
        """
        if csv_path:
            self.csv_path = Path(csv_path)
        elif experiment_code:
            self.csv_path = Path(config_dir) / f"{experiment_code}_weather.csv"
        else:
            raise ValueError("Must provide either csv_path or experiment_code")
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Weather CSV file not found: {self.csv_path}")
    
    def load_weather_data(self, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None,
                         days: Optional[int] = None) -> List[WeatherData]:
        """
        Load weather data from CSV file.
        
        Expected CSV columns:
        - date: Date in YYYY-MM-DD format
        - temp_avg: Average temperature (°C)  
        - temp_min: Minimum temperature (°C)
        - temp_max: Maximum temperature (°C)
        - solar_radiation: Solar radiation (MJ/m²/day)
        - rel_humidity: Relative humidity (%)
        - wind_speed: Wind speed (m/s)
        - rainfall: Rainfall (mm) - optional, defaults to 0.0
        
        Args:
            start_date: Starting date filter (optional)
            end_date: Ending date filter (optional)
            days: Number of days to load from start_date (optional)
            
        Returns:
            List of WeatherData objects
        """
        # Read CSV file
        df = pd.read_csv(self.csv_path)
        
        # Validate required columns
        required_cols = ['date', 'temp_avg', 'temp_min', 'temp_max', 
                        'solar_radiation', 'rel_humidity', 'wind_speed']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in CSV: {missing_cols}")
        
        # Parse date column
        df['date'] = pd.to_datetime(df['date'])
        
        # Add rainfall column if missing
        if 'rainfall' not in df.columns:
            df['rainfall'] = 0.0
        
        # Apply date filters
        if start_date:
            df = df[df['date'] >= start_date]
        
        if end_date:
            df = df[df['date'] <= end_date]
        elif days and start_date:
            end_date = start_date + pd.Timedelta(days=days)
            df = df[df['date'] < end_date]
        elif days:
            df = df.head(days)
        
        # Sort by date
        df = df.sort_values('date')
        
        # Convert to WeatherData objects
        weather_data = []
        for _, row in df.iterrows():
            weather_data.append(WeatherData(
                date=row['date'].to_pydatetime(),
                temp_avg=float(row['temp_avg']),
                temp_min=float(row['temp_min']),
                temp_max=float(row['temp_max']),
                solar_radiation=float(row['solar_radiation']),
                rel_humidity=float(row['rel_humidity']),
                wind_speed=float(row['wind_speed']),
                rainfall=float(row['rainfall'])
            ))
        
        return weather_data
    
    def get_weather_info(self) -> dict:
        """
        Get basic information about the weather dataset.
        
        Returns:
            Dictionary with dataset information
        """
        df = pd.read_csv(self.csv_path)
        df['date'] = pd.to_datetime(df['date'])
        
        return {
            'total_records': len(df),
            'date_range': {
                'start': df['date'].min().isoformat(),
                'end': df['date'].max().isoformat()
            },
            'columns': list(df.columns),
            'file_path': str(self.csv_path)
        }