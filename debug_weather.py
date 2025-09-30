"""Debug weather data loading"""
import sys
sys.path.insert(0, 'src')

from utils.weather_loader import WeatherDataLoader

loader = WeatherDataLoader("input/LET_EXP001_2024_weather.csv")
print("Weather data columns:", loader.weather_data.columns.tolist())
print("\nFirst row:")
print(loader.weather_data.iloc[0].to_dict())
print("\nFirst 3 rows:")
print(loader.weather_data.head(3))
