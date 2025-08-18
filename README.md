# Python Hydroponic Simulation System

A complete Python implementation of the hydroponic water and nutrient uptake simulation, converted from the original Fortran AMEI (Agricultural Model Exchange Initiative) implementation.

## Overview

This simulation models hydroponic lettuce production systems using:
- **Water Uptake Submodel (WUS)**: Modified Penman-Monteith equations for crop evapotranspiration
- **Nutrient Concentration Submodel (NCS)**: Ion concentration dynamics in nutrient solutions
- **Complete system integration**: Weather data, crop parameters, and system configuration

## Features

### Core Models
- ✅ Penman-Monteith reference evapotranspiration calculation
- ✅ Crop coefficient adjustments for hydroponic systems
- ✅ Nutrient concentration dynamics (nutritive and non-nutritive ions)
- ✅ Tank volume updates and water balance
- ✅ Electrical conductivity calculations
- ✅ Water use efficiency metrics

### Data Management
- ✅ Structured data classes with validation
- ✅ CSV input/output capabilities
- ✅ Weather data generation and import
- ✅ Configurable system and crop parameters

### Analysis Tools
- ✅ Daily simulation results tracking
- ✅ Summary statistics calculation
- ✅ Pandas DataFrame integration for analysis
- ✅ CSV export for further analysis

## Installation

1. **Clone or download this directory**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### Run Demo Simulation
```bash
python run_simulation.py
```

Choose option 1 for a quick 5-day demo that matches the Fortran output.

### Python API Usage
```python
from src.hydroponic_simulator import HydroponicSimulator, create_demo_simulation

# Create simulator
simulator = HydroponicSimulator()

# Run with default demo data
input_data = create_demo_simulation()
results = simulator.run_simulation(input_data)

# Print summary
simulator.print_summary()

# Save results
simulator.save_results_csv("my_results.csv")
```

## Project Structure

```
hydroponic_python/
├── src/
│   ├── models/
│   │   ├── water_uptake.py          # Water Uptake Submodel (WUS)
│   │   └── nutrient_concentration.py # Nutrient Concentration Submodel (NCS)
│   ├── data/
│   │   └── hydroponic_system.py     # Data classes and configurations
│   ├── utils/
│   │   └── weather_generator.py     # Weather data generation
│   └── hydroponic_simulator.py      # Main simulation engine
├── data/
│   ├── input/                       # Input data files
│   └── output/                      # Simulation results
├── tests/                           # Unit tests
├── docs/                           # Documentation
├── requirements.txt                # Python dependencies
├── run_simulation.py              # Main execution script
└── README.md                      # This file
```

## Simulation Configuration

### System Configuration
```python
from src.data.hydroponic_system import HydroSystemConfig

system = HydroSystemConfig(
    system_id="HYD1",
    crop_id="LETT", 
    location_id="USGA",
    tank_volume=500.0,  # L
    flow_rate=50.0,     # L/h
    system_type="NFT",  # Nutrient Film Technique
    system_area=10.0,   # m²
    n_plants=48
)
```

### Crop Parameters
```python
from src.data.hydroponic_system import CropParameters

crop = CropParameters(
    crop_id="LETT",
    crop_name="Lettuce",
    kcb=0.90,           # Basal crop coefficient
    phi=0.85,           # Density index  
    crop_height=0.30,   # m
    root_zone_depth=0.15, # m
    laid=2.0            # Leaf area index
)
```

### Nutrient Configuration
```python
from src.models.nutrient_concentration import NutrientParams

nitrogen = NutrientParams(
    nutrient_id="N-NO3",
    nutrient_name="Nitrogen-Nitrate",
    chemical_form="NO3-",
    initial_conc=200.0,   # mg/L
    recharge_conc=250.0,  # mg/L
    uptake_conc=180.0,    # mg/L
    sensitivity_coeff=1.0,
    is_nutritive=True,
    min_conc=150.0,       # mg/L
    max_conc=300.0        # mg/L
)
```

## Comparison with Fortran Version

| Feature | Fortran | Python | Notes |
|---------|---------|---------|-------|
| Core Equations | ✅ | ✅ | Identical mathematical models |
| Weather Data | File-based | Generated + File support | More flexible input |
| Output Format | CSV | CSV + DataFrame | Enhanced analysis capabilities |
| Configuration | Hard-coded | Object-oriented | More maintainable |
| Extensibility | Limited | High | Modular design |
| Performance | Very Fast | Fast | ~10x slower but still efficient |
| Dependencies | None | NumPy, Pandas | Standard scientific stack |

## Key Equations Implemented

### Water Uptake Submodel (WUS)
```
ETc′ = Φ × Kcb × ETo′
Tr = A × ETc′
```

### Nutrient Concentration Submodel (NCS)

**Nutritive ions:**
```
[I]t+1 = [I]t + (Tr/V) × ([I]R - [I]U)
```

**Non-nutritive ions:**
```
[I]t+1 = ([I]t - [I]R/p) × exp(-p × Tr/V) + [I]R/p
```

## Example Output

```
================================================================
    HYDROPONIC SIMULATION SUMMARY
================================================================
System: HYD1 | Crop: LETT | Location: USGA
Simulation Period: 2024-04-11 to 2024-05-10
Total Days: 30
----------------------------------------------------------------
Total Water Consumption:    421.3 L
Average Daily Consumption:  14.0 L/day
Final Tank Volume:          478.7 L
Volume Reduction:           21.3 L
Average Reference ET:       3.24 mm/day
Average Transpiration:      2.18 mm/day
Temperature Range:          15.2°C - 28.9°C
Average Water Use Efficiency: 2.65 kg/m³
================================================================
```

## Advanced Features

### Custom Weather Generation
```python
from src.utils.weather_generator import WeatherGenerator

generator = WeatherGenerator(
    base_temp=25.0,      # °C
    temp_variation=6.0,  # °C
    base_humidity=65.0,  # %
    base_solar=20.0      # MJ/m²/day
)

weather = generator.generate_weather_series(start_date, 30)
```

### Results Analysis
```python
# Convert to pandas DataFrame
df = results.to_dataframe()

# Analyze trends
daily_consumption = df['Water_Total_L']
nutrient_trends = df[['N-NO3_mg_L', 'P-PO4_mg_L', 'K_mg_L']]

# Create plots
import matplotlib.pyplot as plt
df.plot(x='Day', y=['N-NO3_mg_L', 'K_mg_L'], title='Nutrient Concentrations')
plt.show()
```

## Contributing

This implementation maintains compatibility with the original Fortran equations while providing modern Python conveniences. Contributions welcome for:

- Additional crop models
- Enhanced weather data import
- Visualization tools
- Performance optimizations
- Unit tests

## License

Same as original AMEI project - open source for agricultural research and education.

## References

- Original Fortran implementation: AMEI (Agricultural Model Exchange Initiative)
- Scientific basis: MDPI paper on hydroponic modeling
- FAO-56 Penman-Monteith reference evapotranspiration methodology