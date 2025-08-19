# Hydroponic Simulation Configuration Documentation

This document explains all configuration parameters in `sample_config.json` and provides guidance on what values can be modified.

## 🏗️ **SYSTEM_CONFIG** - Physical System Setup

| Parameter | Description | Default | Options/Range |
|-----------|-------------|---------|---------------|
| `system_id` | Unique identifier for this hydroponic system | "HYD1" | Any string (e.g., "GREENHOUSE_A", "LAB_SYSTEM_01") |
| `crop_id` | Crop type identifier | "LETT" | "LETT" (lettuce), "SPIN" (spinach), "BASIL", etc. |
| `location_id` | Location/climate identifier | "USGA" | "USGA", "EU", "TROP" (tropical), custom codes |
| `tank_volume` | Nutrient solution tank volume (L) | 1500.0 | 50.0-10000.0 (depends on system size) |
| `flow_rate` | Solution circulation rate (L/min) | 50.0 | 5.0-200.0 (NFT: 1-4 L/min per channel) |
| `system_type` | Hydroponic system type | "NFT" | "NFT", "DWC", "DRIP", "AERO", "WICK", "EBB_FLOW" |
| `system_area` | Growing area (m²) | 10.0 | 1.0-1000.0 (greenhouse area) |
| `n_plants` | Number of plants in system | 48 | 1-10000 (plant density: 4-6 plants/m² for lettuce) |

## 🌱 **CROP_PARAMETERS** - Plant-Specific Properties

| Parameter | Description | Default | Options/Range |
|-----------|-------------|---------|---------------|
| `kcb` | Basal crop coefficient | 0.90 | 0.7-1.2 (lettuce: 0.8-1.0, leafy greens: 0.7-1.1) |
| `phi` | Light use efficiency | 0.85 | 0.6-0.95 (species-dependent photosynthetic efficiency) |
| `crop_height` | Maximum plant height (m) | 0.30 | 0.1-2.0 (lettuce: 0.2-0.4m, tomato: 1.5-2.0m) |
| `root_zone_depth` | Effective root zone depth (m) | 0.15 | 0.05-0.5 (hydroponic: 0.1-0.3m) |
| `laid` | Leaf area index at maturity | 2.0 | 1.0-6.0 (lettuce: 1.5-3.0, leafy greens: 2.0-4.0) |

## ⚙️ **SIMULATION_SETTINGS** - Model Controls

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `simulation_days` | Number of days to simulate | 30 | 1-365 (crop cycle length) |
| `start_date` | Simulation start date | "2024-04-11" | Any valid date (YYYY-MM-DD) |
| `output_frequency` | Data output frequency | "daily" | "hourly", "daily", "weekly" |
| `use_dynamic_growth` | Enable dynamic growth modeling | true | true/false |
| `use_mechanistic_uptake` | Use Monod kinetics for uptake | true | true/false |
| `use_rzt_model` | Enable root zone temperature model | true | true/false |
| `use_leaf_model` | Enable detailed leaf development | true | true/false |
| `use_environmental_control` | Enable VPD/CO2 control | true | true/false |

## 🌤️ **WEATHER_SETTINGS** - Environmental Generation

| Parameter | Description | Default | Options/Range |
|-----------|-------------|---------|---------------|
| `source` | Weather data source | "generated" | "generated", "file", "api" |
| `base_temperature` | Average temperature (°C) | 22.0 | 15.0-30.0 (optimal: 18-24°C for lettuce) |
| `temperature_variation` | Daily temperature variation (°C) | 5.0 | 2.0-15.0 (greenhouse: 3-8°C) |
| `base_humidity` | Average relative humidity (%) | 70.0 | 50.0-90.0 (optimal: 60-75% for lettuce) |
| `base_solar_radiation` | Daily light integral (mol/m²/d) | 18.0 | 10.0-50.0 (lettuce needs: 12-17 mol/m²/d) |

## 💧 **NUTRIENT_PARAMETERS** - Individual Nutrient Properties

For each nutrient (N-NO3, P-PO4, K, Ca, Mg):

| Parameter | Description | Typical Range | Lettuce Optimal |
|-----------|-------------|---------------|-----------------|
| `initial_conc` | Starting concentration (mg/L) | Varies by nutrient | N:180-250, P:30-60, K:250-350 |
| `optimal_conc` | Target concentration (mg/L) | Species-dependent | Ca:120-180, Mg:40-60 |
| `minimum_conc` | Deficiency threshold (mg/L) | 50-80% of optimal | Monitor closely |
| `max_conc` | Upper safe limit (mg/L) | 120-150% of optimal | Avoid toxicity |
| `toxic_conc` | Toxicity threshold (mg/L) | 200-300% of optimal | System warning level |
| `uptake_rate` | Relative uptake speed | 0.5-2.0 | Nutrient-specific kinetics |

## 🌡️ **ROOT_ZONE_TEMPERATURE** - RZT Model Parameters

| Parameter | Description | Default | Options/Range |
|-----------|-------------|---------|---------------|
| `optimal_rzt_offset` | RZT above air temp (°C) | 3.0 | 2.0-5.0 (research-based optimal) |
| `min_effective_rzt` | Minimum RZT for growth (°C) | 15.0 | 10.0-20.0 (crop-dependent) |
| `max_effective_rzt` | Maximum RZT before stress (°C) | 35.0 | 30.0-40.0 (avoid root damage) |
| `linear_growth_slope` | Growth increase per °C below optimum | 0.08 | 0.05-0.15 (sensitivity tuning) |
| `rapid_decline_slope` | Growth decrease per °C above optimum | 0.15 | 0.10-0.25 (stress response) |
| `base_growth_factor` | Growth factor at optimal RZT | 1.0 | Fixed reference point |

## 🍃 **LEAF_DEVELOPMENT** - Leaf Growth Model

| Parameter | Description | Default | Options/Range |
|-----------|-------------|---------|---------------|
| `base_phyllochron` | Thermal time between leaves (°C-day) | 45.0 | 35-60 (lettuce: 40-50, faster crops: 25-35) |
| `min_temp` | Base temperature for development (°C) | 4.0 | 0-8 (crop-specific base temp) |
| `opt_temp_min` | Lower optimal temperature (°C) | 18.0 | 15-20 (lettuce optimal range) |
| `opt_temp_max` | Upper optimal temperature (°C) | 24.0 | 22-28 (before heat stress) |
| `max_temp` | Maximum temperature for growth (°C) | 35.0 | 30-40 (lethal temperature) |
| `max_leaf_number` | Maximum leaves per plant | 25.0 | 15-40 (lettuce: 20-30, varies by variety) |
| `initial_leaf_number` | Starting leaves (cotyledons + first) | 2.0 | 1-4 (seedling stage) |
| `max_individual_leaf_area` | Max single leaf area (m²) | 0.006 | 0.003-0.015 (60 cm² typical for lettuce) |
| `leaf_area_expansion_rate` | Daily expansion rate | 0.12 | 0.08-0.20 (12% per day at optimum) |
| `specific_leaf_area` | Leaf area per mass (cm²/g) | 250.0 | 200-350 (lettuce: 200-300) |

## 🏭 **ENVIRONMENTAL_CONTROL** - Climate Control Systems

### Setpoints (Target Conditions)
| Parameter | Description | Default | Optimal Range |
|-----------|-------------|---------|---------------|
| `target_vpd` | Vapor pressure deficit (kPa) | 0.8 | 0.6-1.2 (lettuce: 0.7-0.9) |
| `vpd_tolerance` | Acceptable VPD deviation (kPa) | 0.1 | 0.05-0.2 (control precision) |
| `min_humidity` | Minimum RH to prevent stress (%) | 60.0 | 50-70 (avoid wilting) |
| `max_humidity` | Maximum RH to prevent disease (%) | 80.0 | 75-85 (avoid fungal issues) |
| `day_temp` | Daytime temperature (°C) | 22.0 | 18-26 (photosynthesis optimum) |
| `night_temp` | Nighttime temperature (°C) | 18.0 | 14-22 (respiration balance) |
| `target_co2` | CO2 enrichment level (μmol/mol) | 1200.0 | 800-1500 (photosynthesis boost) |
| `ambient_co2` | Background CO2 level (μmol/mol) | 400.0 | 380-420 (atmospheric) |
| `light_hours` | Daily photoperiod (hours) | 16.0 | 12-18 (lettuce: 14-16h) |
| `light_intensity` | Light intensity (μmol/m²/s) | 200.0 | 150-400 (lettuce PPFD) |

### Equipment Specifications
| Parameter | Description | Default | Typical Range |
|-----------|-------------|---------|---------------|
| `humidifier_capacity` | Humidification rate (L/h) | 5.0 | 1-20 (system size dependent) |
| `dehumidifier_capacity` | Dehumidification rate (L/h) | 10.0 | 2-50 (climate dependent) |
| `co2_injection_rate` | Max CO2 injection (μmol/mol/min) | 50.0 | 20-100 (system volume) |
| `air_exchange_rate` | Air changes per hour | 0.5 | 0.1-2.0 (ventilation rate) |
| `electricity_cost` | Power cost ($/kWh) | 0.12 | 0.08-0.30 (regional rates) |

### PID Controller Tuning
| Controller | Kp | Ki | Kd | Tuning Notes |
|------------|----|----|----| -------------|
| `humidity` | 2.0 | 0.5 | 0.1 | Moderate response, avoid oscillation |
| `co2` | 1.5 | 0.3 | 0.05 | Slower response, gas mixing time |
| `temperature` | 3.0 | 0.8 | 0.2 | Faster response, thermal mass |

## 🔬 **PHOTOSYNTHESIS_MODEL** - Farquhar Model Parameters

| Parameter | Description | Default | Adjustment Notes |
|-----------|-------------|---------|------------------|
| `kc` | Michaelis-Menten constant for CO2 (μmol/mol) | 404.0 | Species-specific (C3 plants: 300-500) |
| `ko` | Michaelis-Menten constant for O2 (μmol/mol) | 248.0 | Temperature dependent (200-300) |
| `gamma_star` | CO2 compensation point (μmol/mol) | 36.9 | C3 plants: 30-45 |
| `jmax_25` | Max electron transport at 25°C (μmol/m²/s) | 500.0 | Lettuce: 400-600, adjust for variety |
| `vcmax_25` | Max carboxylation at 25°C (μmol/m²/s) | 250.0 | Lettuce: 200-300, nitrogen dependent |
| `theta` | Light response curvature | 0.85 | 0.7-0.9 (light acclimation) |
| `alpha` | Quantum efficiency (mol CO2/mol photons) | 0.2 | 0.15-0.25 (leaf efficiency) |
| `rd_25` | Dark respiration at 25°C (μmol/m²/s) | 0.1 | 0.05-0.15 (maintenance cost) |

## 🧬 **MECHANISTIC_UPTAKE** - Nutrient Uptake Kinetics

### Growth Parameters
| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `carbon_assimilation_rate` | Daily C fixation rate (g C/g biomass/day) | 0.12 | 0.08-0.20 |
| `nitrogen_assimilation_rate` | Daily N uptake rate (g N/g biomass/day) | 0.018 | 0.01-0.03 |
| `structural_growth_efficiency` | C to structure conversion | 0.75 | 0.6-0.9 |
| `respiration_rate` | Daily maintenance respiration | 0.02 | 0.01-0.05 |
| `fresh_to_dry_ratio` | Fresh:dry weight ratio | 12.0 | 8-15 (lettuce: 10-14) |

### Kinetic Parameters (per nutrient, per growth stage)
| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| `vmax` | Maximum uptake rate (mg/g biomass/day) | 0.05-1.5 (nutrient dependent) |
| `km` | Half-saturation constant (mg/L) | 5-30 (affinity parameter) |
| `min_conc` | Minimum uptake concentration (mg/L) | 2-15 (below this = no uptake) |
| `max_conc` | Maximum beneficial concentration (mg/L) | 50-400 (above this = luxury uptake) |
| `uptake_efficiency` | Stage-specific efficiency (0-1) | 0.6-0.95 (growth stage dependent) |

## 🧪 **NUTRIENT_CONCENTRATION** - Solution Chemistry

### EC Factors (Electrical Conductivity)
| Nutrient | EC Factor | Notes |
|----------|-----------|-------|
| Major nutrients (N, P, K) | 0.0008-0.0012 | Primary EC contributors |
| Secondary (Ca, Mg, S) | 0.0010-0.0015 | Moderate EC impact |
| Micronutrients (Fe, Mn, etc.) | 0.0018-0.002 | High EC per unit mass |

## 📊 **DEFAULT_VALUES** - System Defaults

| Parameter | Description | Default | Typical Range |
|-----------|-------------|---------|---------------|
| `initial_ph` | Starting pH | 6.0 | 5.5-6.5 (lettuce optimal) |
| `initial_ec` | Starting EC (dS/m) | 1.8 | 1.2-2.5 (lettuce range) |
| `initial_rzt` | Starting root zone temp (°C) | 22.0 | 18-26 |
| `dissolved_oxygen` | DO concentration (mg/L) | 6.0 | 5-8 (root health) |
| `par_conversion_factor` | Solar to PAR conversion | 23.6 | 20-25 (latitude dependent) |

## ⚠️ **STRESS_THRESHOLDS** - Plant Stress Limits

| Parameter | Description | Default | Critical Notes |
|-----------|-------------|---------|----------------|
| `water_stress_minimum` | Water stress threshold | 0.5 | Below this = drought stress |
| `nitrogen_stress_minimum` | N deficiency threshold | 0.6 | Below this = chlorosis |
| `lettuce_optimal_min` | Minimum optimal temp (°C) | 18.0 | Species-specific range |
| `lettuce_optimal_max` | Maximum optimal temp (°C) | 24.0 | Above this = heat stress |
| `absolute_min` | Lethal minimum temp (°C) | 4.0 | Crop failure threshold |
| `absolute_max` | Lethal maximum temp (°C) | 35.0 | Thermal death point |

---

## 🎯 **QUICK TUNING GUIDE**

### For Different Crops:
- **Spinach**: Increase `base_phyllochron` to 35-40, reduce `max_leaf_number` to 15-20
- **Basil**: Reduce `base_phyllochron` to 30-35, increase `max_individual_leaf_area` to 0.008-0.012
- **Kale**: Increase `max_leaf_number` to 35-50, `max_individual_leaf_area` to 0.010-0.020

### For Different Systems:
- **DWC**: Increase `dissolved_oxygen` to 7-8, reduce `flow_rate` to 5-20
- **Aeroponics**: Reduce `root_zone_depth` to 0.05-0.10, increase `humidity` setpoints
- **Media-based**: Increase `root_zone_depth` to 0.20-0.40

### For Different Climates:
- **Hot Climate**: Reduce `day_temp` to 20-22°C, increase `target_vpd` to 0.9-1.1
- **Cold Climate**: Increase `base_temperature` to 24-26°C, reduce `temperature_variation`
- **Humid Climate**: Increase `dehumidifier_capacity`, reduce `max_humidity` to 70-75%

### Performance Optimization:
- **Faster Growth**: Increase `leaf_area_expansion_rate` to 0.15-0.18, `carbon_assimilation_rate` to 0.15
- **Better Quality**: Optimize `target_co2` to 1000-1200, maintain `target_vpd` at 0.7-0.8
- **Energy Savings**: Reduce `light_hours` to 14, `light_intensity` to 180, optimize `target_co2` timing