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


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file generates synthetic weather data for testing and simulation purposes. Think of it 
as a "weather machine" that creates realistic daily weather patterns when you don't have 
real weather data available. It's like having a sophisticated weather simulator that can 
create different seasonal patterns and realistic day-to-day variations for testing your 
hydroponic growing models.

PURPOSE OF SYNTHETIC WEATHER GENERATION:

When developing or testing hydroponic simulations, you often need:
- **Consistent test conditions**: Same weather patterns for comparing different treatments
- **Seasonal variations**: Test how systems perform across different seasons
- **Extreme scenarios**: Test system responses to unusual weather conditions
- **Long-term data**: Years of weather data for comprehensive testing
- **Controlled experiments**: Specific weather patterns to test particular hypotheses

WHAT THIS WEATHER GENERATOR DOES:

Instead of relying on unpredictable real weather data, this system creates:
- **Realistic daily patterns**: Temperature, humidity, solar radiation, wind
- **Seasonal variations**: Different patterns for spring, summer, fall, winter
- **Natural variability**: Day-to-day fluctuations like real weather
- **Controlled parameters**: Adjustable base conditions for different climates

KEY CLASS AND FUNCTIONS:

1. WeatherGenerator (Weather Simulation Engine)
   - What it does: Creates sequences of daily weather data with realistic patterns
   - Parameters: Base temperature, variation range, humidity levels, solar radiation
   - Real-world meaning: Like a sophisticated weather forecasting system that can 
     generate any type of climate pattern you need for testing purposes.

2. __init__() - Weather Pattern Setup
   - What it does: Sets the basic parameters for the type of weather to generate
   - Parameters:
     * base_temp: Average temperature around which daily values vary
     * temp_variation: How much daily temperatures swing above/below average
     * base_humidity: Typical humidity level with daily variations
     * base_solar: Average solar energy with seasonal and daily variations
   - Real-world meaning: Like setting the climate dial on a weather machine - 
     choose whether you want tropical, temperate, or cool conditions.

3. generate_weather_series() - Daily Weather Creation
   - What it does: Creates a sequence of daily weather readings over time
   - Process:
     a) Calculate seasonal effects (warmer in summer, cooler in winter)
     b) Add daily random variations (some days warmer/cooler than others)
     c) Generate coordinated weather patterns (sunny = warm, cloudy = cool)
     d) Ensure realistic bounds (humidity 30-95%, positive solar radiation)
   - Real-world meaning: Like creating a realistic weather journal for an entire 
     growing season, complete with natural ups and downs.

4. generate_from_template() - Seasonal Weather Patterns
   - What it does: Creates weather patterns typical of specific seasons
   - Templates available:
     * Spring: Mild temperatures, moderate humidity, increasing daylight
     * Summer: Warm temperatures, lower humidity, maximum solar radiation
     * Fall: Cooling temperatures, higher humidity, decreasing daylight  
     * Winter: Cool temperatures, high humidity, minimum solar radiation
   - Real-world meaning: Like having preset weather modes - choose "summer" 
     and get hot, sunny days; choose "winter" and get cool, dim conditions.

WEATHER PATTERN ALGORITHMS:

5. Seasonal Variation (Sinusoidal Pattern)
   - What it does: Models the natural yearly cycle of weather changes
   - Mathematics: Uses sine wave based on day of year (1-365)
   - Pattern: Warmer in summer (day 172), cooler in winter (day 355)
   - Real-world meaning: Like the natural rhythm of seasons - gradually warming 
     through spring to summer, then cooling through fall to winter.

6. Daily Temperature Calculation
   - What it does: Creates realistic daily high/low temperature patterns
   - Process: Base temperature + seasonal effect + random daily variation
   - Temperature spread: Daily lows 2-5°C below average, highs 3-7°C above
   - Real-world meaning: Like how actual weather works - some days warmer 
     or cooler than average, with natural daily temperature swings.

7. Solar Radiation Modeling
   - What it does: Creates realistic daily sunlight patterns
   - Factors: Seasonal variation (more sun in summer), daily weather variation
   - Range: Minimum 5 MJ/m²/day (very cloudy), up to 25+ MJ/m²/day (bright sun)
   - Real-world meaning: Like modeling how much solar energy is available 
     for plant photosynthesis on different days throughout the year.

8. Humidity and Environmental Coordination
   - What it does: Creates realistic humidity patterns that correlate with temperature
   - Pattern: Generally higher humidity in cooler seasons, lower in warmer seasons
   - Constraints: Kept within realistic bounds (30-95% relative humidity)
   - Real-world meaning: Like how real weather works - hot summer days are often 
     drier, while cool winter days are often more humid.

MATHEMATICAL PATTERNS:

Seasonal Sinusoidal Variation:
- **Equation**: seasonal_factor = sin(2π × (day_of_year - 80) / 365)
- **Phase Shift**: Day 80 ≈ March 21 (spring equinox) = 0 point
- **Peak**: Day 172 ≈ June 21 (summer solstice) = maximum
- **Trough**: Day 355 ≈ December 21 (winter solstice) = minimum

Random Variation:
- **Normal Distribution**: Most days near average, few days extreme
- **Standard Deviation**: Controls how much daily variation occurs
- **Realistic Bounds**: Prevents impossible weather (negative solar, 0% humidity)

Coordinated Parameters:
- **Temperature-Solar Correlation**: Sunny days tend to be warmer
- **Seasonal Consistency**: All parameters follow same seasonal rhythm
- **Realistic Constraints**: Values stay within physically possible ranges

PRACTICAL APPLICATIONS:

For Simulation Testing:
1. **Model Validation**: Test simulations against known weather patterns
2. **Sensitivity Analysis**: See how different weather affects plant growth
3. **Extreme Testing**: Generate unusual weather to test system robustness
4. **Reproducibility**: Same weather data for consistent test results

For Research Applications:
1. **Controlled Experiments**: Generate specific weather scenarios for testing
2. **Long-term Studies**: Create years of weather data for comprehensive analysis
3. **Climate Scenarios**: Model how different climates affect crop production
4. **Seasonal Planning**: Test growing strategies across different seasons

For Educational Use:
1. **Learning Tool**: Students can explore weather effects on plant growth
2. **Demonstration**: Show how seasonal changes affect hydroponic systems
3. **Experimentation**: Try different weather scenarios without waiting for seasons
4. **Understanding**: Visualize relationships between weather and plant response

WEATHER TEMPLATE CHARACTERISTICS:

Spring Template (Mild Growth Conditions):
- Base Temperature: 18°C (comfortable growing temperature)
- Temperature Variation: ±4°C (moderate daily swings)
- Humidity: 65% (moderate moisture levels)
- Solar Radiation: 16 MJ/m²/day (increasing daylight hours)

Summer Template (Peak Growth Conditions):
- Base Temperature: 25°C (warm growing conditions)
- Temperature Variation: ±6°C (larger daily temperature swings)
- Humidity: 60% (lower humidity due to warmth)
- Solar Radiation: 22 MJ/m²/day (maximum daylight and intensity)

Fall Template (Slowing Growth):
- Base Temperature: 15°C (cooling conditions)
- Temperature Variation: ±5°C (moderate swings)
- Humidity: 75% (increasing moisture)
- Solar Radiation: 12 MJ/m²/day (decreasing daylight)

Winter Template (Minimal Growth):
- Base Temperature: 10°C (cool conditions)
- Temperature Variation: ±3°C (smaller daily swings)
- Humidity: 80% (high moisture levels)
- Solar Radiation: 8 MJ/m²/day (minimum daylight)

QUALITY ASSURANCE:

Realistic Bounds:
- **Temperature**: Prevents impossible temperatures (like -50°C in summer)
- **Humidity**: Constrained to 30-95% (physically possible range)
- **Solar Radiation**: Minimum 5 MJ/m²/day (even cloudy days have some light)
- **Wind Speed**: Minimum 0.5 m/s (typical greenhouse air movement)

Natural Correlations:
- **Seasonal Consistency**: All parameters follow coordinated seasonal patterns
- **Daily Relationships**: Hot days tend to be sunny, cool days tend to be humid
- **Gradual Changes**: No sudden unrealistic jumps between days

Parameter Restoration:
- **Template Safety**: Temporary parameter changes don't affect main settings
- **Original State**: Generator returns to original configuration after template use
- **Reusability**: Can generate multiple different weather patterns

KEY CONCEPTS FOR NON-CODERS:

Synthetic Data: Computer-generated information that mimics real-world patterns, 
like creating artificial weather data that behaves like real weather.

Sinusoidal Patterns: Wave-like mathematical patterns that repeat regularly, 
like the seasonal temperature cycle that goes up and down each year.

Random Variation: Adding realistic unpredictability to patterns, like how real 
weather has some randomness even within seasonal trends.

Template-Based Generation: Using predefined patterns as starting points, like 
having weather "recipes" for different seasons that you can customize.

Parameter Coordination: Making sure different weather factors change together 
realistically, like how temperature and humidity are typically related.

This weather generator provides a flexible, realistic foundation for testing 
hydroponic simulations under various environmental conditions, enabling 
comprehensive evaluation of system performance across different climate 
scenarios without waiting for actual seasonal changes or traveling to 
different geographic locations.
"""
