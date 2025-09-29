"""
Distributed Hydroponic Simulation System

This package contains 17 interconnected simulation modules, each responsible for
simulating a specific aspect of hydroponic plant growth. Each simulator runs
its own simulation loop and communicates with other simulators through a
centralized message bus system.

Simulation Modules:
1. biomass_allocation_simulator - Biomass distribution and allocation
2. canopy_architecture_simulator - Canopy structure and light interception
3. environmental_control_simulator - Environmental parameter management
4. genetic_parameters_simulator - Genetic trait expression and variation
5. leaf_development_simulator - Leaf growth and development processes
6. nitrogen_balance_simulator - Nitrogen uptake and allocation
7. nutrient_models_simulator - Nutrient transport and availability
8. ph_model_simulator - pH dynamics and buffering
9. phenology_simulator - Growth stage progression and timing
10. photosynthesis_simulator - Carbon assimilation processes
11. respiration_simulator - Metabolic respiration processes
12. root_system_simulator - Root growth and architecture
13. root_zone_temperature_simulator - Root zone thermal dynamics
14. senescence_simulator - Aging and senescence processes
15. stress_models_simulator - Stress factor calculations
16. water_uptake_simulator - Water uptake and transpiration
17. simulation_orchestrator - Central coordination and timing
"""

# Import only when needed to avoid circular imports
# from .simulation_orchestrator import SimulationOrchestrator
# from .communication_bus import SimulationMessageBus, SimulationEvent

__all__ = [
    'SimulationOrchestrator',
    'SimulationMessageBus', 
    'SimulationEvent'
]
