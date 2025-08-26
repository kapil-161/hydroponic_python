# Hydroponic System Configuration Files

This folder contains all the configuration files for the hydroponic simulation system. All files are in CSV format and can be edited with Excel, Google Sheets, or any spreadsheet application.

## Configuration Files

### Basic System Setup
- `nutrient_solution.csv` - Nutrient concentrations (N, P, K, Ca, Mg, pH)
- `system_settings.csv` - Hydroponic system type and parameters
- `crop_parameters.csv` - Basic crop settings and growth parameters
- `experiment_settings.csv` - Experiment duration and conditions

### Plant Biology Parameters
- `genetic_parameters.csv` - Plant cultivar genetic traits
- `phenology_parameters.csv` - Plant development stages and timing
- `photosynthesis_parameters.csv` - How plants convert light to energy
- `respiration_parameters.csv` - How plants use energy for maintenance
- `canopy_parameters.csv` - Leaf structure and light interception
- `nitrogen_parameters.csv` - Nitrogen uptake and usage
- `senescence_parameters.csv` - Leaf aging and nutrient recovery

### Environmental Controls
- `environment_parameters.csv` - Optimal growing conditions (light, temperature, humidity)
- `environmental_control_parameters.csv` - Target setpoints for automation
- `stress_parameters.csv` - How plants respond to stress conditions
- `root_zone_parameters.csv` - Root temperature and water uptake

### System Management
- `water_parameters.csv` - Water consumption and demand factors
- `system_parameters.csv` - Reservoir and system management
- `model_constants.csv` - Scientific constants and conversion factors

### Advanced Parameters
- `genetic_stress_weights.csv` - How genetic traits respond to stress
- `thermal_requirements.csv` - Temperature requirements for development stages

## How to Edit

1. Open any CSV file in Excel, Google Sheets, or a text editor
2. Modify the `value` column - keep the parameter names unchanged
3. Save the file as CSV format
4. Run the simulation to see the effects of your changes

## Units

Each parameter includes its unit in the `unit` column. Common units:
- `celsius` - Temperature in degrees Celsius
- `ppm` - Parts per million (concentration)
- `kPa` - Kilopascals (pressure)
- `fraction` - Decimal between 0 and 1
- `multiplier` - Factor to multiply by
- `per_day` - Rate per day

## Support

For questions about specific parameters, see the `description` column in each CSV file for detailed explanations.