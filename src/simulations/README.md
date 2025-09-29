# Distributed Hydroponic Simulation System

This directory contains a distributed simulation architecture where each of the 17 hydroponic models gets its own dedicated simulator with interconnected communication loops.

## 🏗️ Architecture Overview

### Core Components

1. **Communication Bus** (`communication_bus.py`)
   - Inter-simulator message passing system
   - Event-driven communication
   - Real-time data exchange between simulators

2. **Simulation Orchestrator** (`simulation_orchestrator.py`)
   - Central coordinator for all simulators
   - Manages timing and synchronization
   - Collects and aggregates results

3. **Individual Simulators** (17 files)
   - Each model gets its own simulator
   - Independent simulation loops
   - Interconnected through message bus

### Simulator List

| # | Simulator | Model File | Purpose |
|---|-----------|------------|---------|
| 1 | `photosynthesis_simulator.py` | `photosynthesis_model.py` | Carbon assimilation processes |
| 2 | `respiration_simulator.py` | `respiration_model.py` | Metabolic respiration |
| 3 | `biomass_allocation_simulator.py` | `biomass_allocation_model.py` | Biomass distribution |
| 4 | `canopy_architecture_simulator.py` | `canopy_architecture.py` | Canopy structure & light |
| 5 | `environmental_control_simulator.py` | `environmental_control.py` | Environmental management |
| 6 | `genetic_parameters_simulator.py` | `genetic_parameters.py` | Genetic trait expression |
| 7 | `leaf_development_simulator.py` | `leaf_development.py` | Leaf growth processes |
| 8 | `nitrogen_balance_simulator.py` | `nitrogen_balance.py` | Nitrogen uptake & allocation |
| 9 | `nutrient_models_simulator.py` | `nutrient_models.py` | Nutrient transport |
| 10 | `ph_model_simulator.py` | `ph_model.py` | pH dynamics |
| 11 | `phenology_simulator.py` | `phenology_model.py` | Growth stage progression |
| 12 | `root_system_simulator.py` | `root_system_model.py` | Root growth & architecture |
| 13 | `root_zone_temperature_simulator.py` | `root_zone_temperature.py` | Root zone thermal dynamics |
| 14 | `senescence_simulator.py` | `senescence_model.py` | Aging processes |
| 15 | `stress_models_simulator.py` | `stress_models.py` | Stress factor calculations |
| 16 | `water_uptake_simulator.py` | `water_uptake_model.py` | Water uptake & transpiration |
| 17 | `simulation_orchestrator.py` | N/A | Central coordination |

## 🔄 Communication Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Orchestrator  │◄──►│  Message Bus     │◄──►│   Simulators    │
│                 │    │                  │    │   (17 files)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Time Control   │    │  Event Routing   │    │  Data Exchange  │
│  Coordination   │    │  Message Queue   │    │  State Updates  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 Key Features

### 1. **Rules.md Compliance**
- ✅ No hardcoded values - all parameters from CSV
- ✅ No fallback/default values - raises errors if missing
- ✅ Uses daily weather file for simulation
- ✅ Uses all model files and their functions
- ✅ No duplicate code/parameters
- ✅ Minimal functional code

### 2. **Inter-Simulator Dependencies**
Each simulator declares its dependencies:
```python
self.dependencies = {
    'photosynthesis_simulator': ['net_assimilation_rate'],
    'biomass_allocation_simulator': ['leaf_biomass', 'stem_biomass'],
    'environmental_control': ['temperature', 'humidity']
}
```

### 3. **Event-Driven Communication**
Simulators communicate through events:
- `PHOTOSYNTHESIS_UPDATE` - Photosynthesis results
- `BIOMASS_UPDATE` - Biomass allocation results
- `ENVIRONMENT_UPDATE` - Environmental changes
- `SIMULATION_STEP` - Time step coordination

### 4. **Data Caching**
- Dependency data cached for performance
- Cache timeout prevents stale data
- Automatic cache invalidation

## 🚀 Usage

### Basic Usage
```python
from simulations.distributed_simulation_runner import DistributedSimulationRunner

# Initialize runner
runner = DistributedSimulationRunner(
    master_csv_path="input/master_parameters.csv",
    weather_csv_path="input/LET_EXP001_2024_weather.csv"
)

# Run simulation
output_path = runner.run_simulation()
print(f"Results saved to: {output_path}")

# Cleanup
runner.cleanup()
```

### Advanced Usage
```python
# Custom configuration
config = SimulationConfig(
    total_days=60,
    steps_per_day=24,
    synchronization_mode="parallel",  # or "sequential", "event_driven"
    enable_real_time=True
)

# Initialize orchestrator
orchestrator = SimulationOrchestrator(config)

# Register simulators manually
photosynthesis_sim = PhotosynthesisSimulator(params)
orchestrator.register_simulator(photosynthesis_sim)

# Run simulation
orchestrator.start_simulation(weather_data)
```

## 🔧 Synchronization Modes

### 1. **Sequential Mode**
- Simulators run one after another
- Deterministic execution order
- Easy debugging and validation

### 2. **Parallel Mode**
- Simulators run concurrently
- Faster execution
- Requires careful dependency management

### 3. **Event-Driven Mode**
- Simulators respond to events asynchronously
- Most flexible and realistic
- Complex but powerful

## 📊 Performance Monitoring

The system provides comprehensive performance metrics:

```python
# Get system status
status = runner.get_system_status()

# Get performance metrics
performance = orchestrator.get_performance_metrics()

# Per-simulator metrics
for simulator in simulators:
    metrics = simulator.get_performance_metrics()
    print(f"{simulator.simulator_id}: {metrics}")
```

## 🧪 Testing Strategy

### Unit Tests
Each simulator has unit tests for:
- Parameter loading from CSV
- Model function execution
- State management
- Error handling

### Integration Tests
- Inter-simulator communication
- Data flow validation
- End-to-end simulation runs

### Performance Tests
- Memory usage monitoring
- Execution time profiling
- Scalability testing

## 🛠️ Development Guidelines

### Adding New Simulators

1. **Create Simulator Class**
```python
class NewSimulator(BaseSimulator):
    def __init__(self, parameters):
        super().__init__("new_simulator")
        self.parameters = parameters
        self.model = NewModel(parameters)
    
    def on_simulation_step(self, data):
        # Implementation
        pass
```

2. **Define Dependencies**
```python
self.dependencies = {
    'other_simulator': ['required_data_key']
}
```

3. **Implement Required Methods**
- `daily_update()` - Main calculation
- `get_data()` - Provide data to others
- `handle_event()` - Handle incoming events

4. **Register with Orchestrator**
```python
orchestrator.register_simulator(new_simulator)
```

### Error Handling
- Per Rules.md: raise errors, no fallbacks
- Missing data raises `ValueError`
- Invalid parameters raise `ParameterError`
- Model errors propagate up

## 📁 File Structure

```
src/simulations/
├── __init__.py                          # Package initialization
├── README.md                            # This file
├── communication_bus.py                 # Message passing system
├── simulation_orchestrator.py           # Central coordinator
├── distributed_simulation_runner.py     # Main entry point
├── photosynthesis_simulator.py          # Photosynthesis processes
├── respiration_simulator.py             # Respiration processes
├── biomass_allocation_simulator.py      # Biomass distribution
├── canopy_architecture_simulator.py     # Canopy structure
├── environmental_control_simulator.py   # Environmental management
├── genetic_parameters_simulator.py      # Genetic traits
├── leaf_development_simulator.py        # Leaf growth
├── nitrogen_balance_simulator.py        # Nitrogen dynamics
├── nutrient_models_simulator.py         # Nutrient transport
├── ph_model_simulator.py                # pH dynamics
├── phenology_simulator.py               # Growth stages
├── root_system_simulator.py             # Root architecture
├── root_zone_temperature_simulator.py   # Root zone thermal
├── senescence_simulator.py              # Aging processes
├── stress_models_simulator.py           # Stress factors
└── water_uptake_simulator.py            # Water dynamics
```

## 🔍 Troubleshooting

### Common Issues

1. **Missing Parameters**
   - Error: "Parameter X missing from CSV"
   - Solution: Add parameter to master_parameters.csv

2. **Dependency Errors**
   - Error: "Missing required data from simulator Y"
   - Solution: Ensure simulator Y is running and providing data

3. **Performance Issues**
   - High memory usage: Reduce cache timeout
   - Slow execution: Use parallel mode
   - Queue overflow: Increase queue size

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with verbose output
runner = DistributedSimulationRunner()
runner.run_simulation()
```

## 📈 Future Enhancements

1. **Distributed Computing**
   - Run simulators on different machines
   - Network-based communication
   - Load balancing

2. **Real-Time Visualization**
   - Live dashboard
   - Real-time plots
   - Interactive controls

3. **Machine Learning Integration**
   - Parameter optimization
   - Predictive modeling
   - Adaptive simulation

4. **Database Integration**
   - Store simulation results
   - Historical data analysis
   - Performance benchmarking

## 📞 Support

For questions or issues:
1. Check this README
2. Review Rules.md for compliance
3. Examine existing simulator implementations
4. Run unit tests for validation

---

**Note**: This distributed simulation system strictly follows Rules.md requirements:
- No hardcoded values
- No fallback/default values  
- All parameters from CSV files
- Uses all model functions
- Minimal functional code
- Raises errors when data is missing
