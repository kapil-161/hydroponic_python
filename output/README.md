# Simulation Output Files

This directory contains the organized output from the hydroponic crop simulation system.

## File Organization

### Combined Results
- **`simulation_results.csv`**: Combined results from all simulators with 259 columns
  - Contains all simulator outputs in a single file
  - Columns are prefixed with simulator names (e.g., `photosynthesis_simulator_net_assimilation_rate`)

### Individual Simulator Results
Each simulator has its own CSV file with only relevant columns:

#### 1. **Biomass Allocation** (`simulation_results_biomass_allocation_simulator.csv`)
- Total, leaf, stem, and root biomass
- Allocation fractions and efficiency
- Cumulative and daily biomass gains

#### 2. **Canopy Architecture** (`simulation_results_canopy_architecture_simulator.csv`)
- LAI (Leaf Area Index)
- Canopy height, width, and coverage
- Light interception and distribution
- Microclimate gradients

#### 3. **Environmental Control** (`simulation_results_environmental_control.csv`)
- Air temperature, humidity, CO2
- Light intensity and photoperiod
- VPD (Vapor Pressure Deficit)
- Energy consumption and control efficiency

#### 4. **Genetic Parameters** (`simulation_results_genetic_parameters_simulator.csv`)
- Cultivar characteristics
- Genetic coefficients and trait expressions
- Environmental modifiers
- Performance indices

#### 5. **Leaf Development** (`simulation_results_leaf_development_simulator.csv`)
- Leaf appearance and expansion rates
- Total leaves and leaf area
- Leaf nitrogen content
- Age and size distributions

#### 6. **Nitrogen Balance** (`simulation_results_nitrogen_balance_simulator.csv`)
- Nitrogen uptake (nitrate, ammonium, amino acids)
- Allocation by organ
- Nitrogen use efficiency
- Stress indices

#### 7. **Nutrient Models** (`simulation_results_nutrient_models_simulator.csv`)
- Solution EC and pH
- Nutrient concentrations and uptake rates
- Root and shoot nutrient pools
- Xylem and phloem flux

#### 8. **pH Model** (`simulation_results_ph_model_simulator.csv`)
- pH and stability
- Buffer capacity
- Nutrient solubility
- Precipitation risks

#### 9. **Phenology** (`simulation_results_phenology_simulator.csv`)
- Growth stage progression
- Thermal time accumulation
- Developmental indices
- Bolting risk

#### 10. **Photosynthesis** (`simulation_results_photosynthesis_simulator.csv`)
- Net and gross photosynthesis rates
- Light use efficiency
- CO2 uptake
- Temperature and light stress factors

#### 11. **Respiration** (`simulation_results_respiration_simulator.csv`)
- Total, maintenance, and growth respiration
- Organ-specific respiration (leaf, stem, root)
- Temperature and biomass factors

#### 12. **Root System** (`simulation_results_root_system_simulator.csv`)
- Root depth, biomass, length, surface area
- Root distribution and density
- Fine, medium, and coarse root fractions

#### 13. **Root Zone Temperature** (`simulation_results_root_zone_temperature_simulator.csv`)
- Root zone temperature
- Growth and nutrient uptake factors
- Heat generation and exchange
- Thermal stress

#### 14. **Senescence** (`simulation_results_senescence_simulator.csv`)
- Age, stress, and developmental senescence rates
- Nutrient remobilization (N, C, P, K)
- Senescence stage distribution
- Recovery rates

#### 15. **Stress Models** (`simulation_results_stress_models.csv`)
- Temperature, water, nutrient stress
- Light, pH, salinity stress
- Integrated stress index
- Acclimation and damage levels

#### 16. **Water Uptake** (`simulation_results_water_uptake_simulator.csv`)
- Water uptake and transpiration rates
- Evapotranspiration
- Water potentials (root, leaf)
- Hydraulic conductance

## Common Columns
All files include these base columns:
- `step`: Simulation step number
- `day`: Day number
- `hour`: Hour of day
- `timestamp`: Simulation timestamp
- `step_count`: Internal step counter
- `last_update`: Last update timestamp

## File Summary
See `output_files_summary.csv` for a complete list of all output files with column counts and descriptions.

## Usage
- **For analysis of specific processes**: Use individual simulator CSV files
- **For comprehensive analysis**: Use the combined `simulation_results.csv` file
- **For quick reference**: Check `output_files_summary.csv`

## Data Format
- All files are in CSV format with headers
- Numeric values are in scientific notation where appropriate
- Missing values are represented as empty cells
- All timestamps are in ISO 8601 format
