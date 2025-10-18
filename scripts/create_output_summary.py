"""Create a summary of all output CSV files"""
import pandas as pd
import os
from pathlib import Path

def load_config_param(df, param_name, default="N/A"):
    """Load parameter value from config dataframe"""
    try:
        row = df[df['parameter_name'] == param_name]
        if not row.empty:
            return row.iloc[0]['value']
    except KeyError as e:
        raise KeyError(f"Missing column in config dataframe while looking for '{param_name}': {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading config parameter '{param_name}': {e}")
    return default

def load_initial_param(df, param_name, default="N/A"):
    """Load parameter value from initials dataframe"""
    try:
        row = df[(df['category'] == 'system_config') | (df['category'] == 'initial_state')]
        row = row[row['parameter_name'] == param_name]
        if not row.empty:
            return row.iloc[0]['value']
    except KeyError as e:
        raise KeyError(f"Missing column in initials dataframe while looking for '{param_name}': {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading initial parameter '{param_name}': {e}")
    return default

# Load configuration files
input_dir = Path("input")
initials_df = pd.read_csv(input_dir / "initials.csv", comment='#')
genetics_df = pd.read_csv(input_dir / "genetics.csv", comment='#')
master_df = pd.read_csv(input_dir / "master_parameters.csv", comment='#')

output_dir = Path("output")
# Get all CSV files except the combined results file and summary
csv_files = sorted([f for f in output_dir.glob("*.csv")
                    if f.name not in ["simulation_results.csv", "output_files_summary.csv"]])

print("\n" + "=" * 100)
print(f"{'SIMULATION OUTPUT SUMMARY':^100}")
print("=" * 100 + "\n")

# Print experimental setup information dynamically from CSVs
print("EXPERIMENTAL SETUP")
print("-" * 100)

# Get values from config files
cultivar_name = load_config_param(genetics_df, 'cultivar_name', 'Unknown')
lettuce_type = load_config_param(genetics_df, 'lettuce_type', 'Unknown')
tank_volume = load_initial_param(initials_df, 'tank_volume_L', 'N/A')
solution_volume = load_initial_param(initials_df, 'solution_volume', 'N/A')
plant_count = load_initial_param(initials_df, 'plant_count', 'N/A')
grow_area = load_initial_param(initials_df, 'grow_area', 'N/A')
total_days = load_config_param(master_df, 'total_days_default', 'N/A')
steps_per_day = load_config_param(master_df, 'steps_per_day', 'N/A')
total_biomass = load_initial_param(initials_df, 'total_biomass', 'N/A')
leaf_biomass = load_initial_param(initials_df, 'leaf_biomass', 'N/A')
stem_biomass = load_initial_param(initials_df, 'stem_biomass', 'N/A')
root_biomass = load_initial_param(initials_df, 'root_biomass', 'N/A')
initial_lai = load_initial_param(initials_df, 'lai', 'N/A')
optimal_ec = load_initial_param(initials_df, 'optimal_ec', 'N/A')
solution_ph = load_initial_param(initials_df, 'solution_ph', 'N/A')

# Get nutrient concentrations
n_conc = load_initial_param(initials_df, 'solution_n_concentration', 'N/A')
p_conc = load_initial_param(initials_df, 'solution_p_concentration', 'N/A')
k_conc = load_initial_param(initials_df, 'solution_k_concentration', 'N/A')
ca_conc = load_initial_param(initials_df, 'solution_ca_concentration', 'N/A')
mg_conc = load_initial_param(initials_df, 'solution_mg_concentration', 'N/A')
s_conc = load_initial_param(initials_df, 'solution_s_concentration', 'N/A')
fe_conc = load_initial_param(initials_df, 'solution_fe_concentration', 'N/A')

print(f"Cultivar:                  Lactuca sativa '{cultivar_name}' ({lettuce_type.capitalize()} lettuce)")
print(f"System Type:               Deep Water Culture (DWC) Hydroponic System")
print(f"Tank Volume:               {tank_volume} L")
print(f"Solution Volume:           {solution_volume} L")
print(f"Plant Count:               {plant_count} plants")
print(f"Growing Area:              {grow_area} m²")
print(f"Growth Period:             {total_days} days from planting")
print(f"Timesteps:                 {steps_per_day} steps/day (hourly simulation)")
print(f"Initial Plant Biomass:     {total_biomass} g ({leaf_biomass} g leaf, {stem_biomass} g stem, {root_biomass} g root)")
print(f"Initial LAI:               {initial_lai} m²/m²")
print(f"Solution EC (optimal):     {optimal_ec} dS/m")
print(f"Solution pH (initial):     {solution_ph}")
print()
print("Initial Nutrient Concentrations (mg/L):")
print(f"  N: {n_conc}  |  P: {p_conc}  |  K: {k_conc}  |  Ca: {ca_conc}  |  Mg: {mg_conc}  |  S: {s_conc}  |  Fe: {fe_conc}")
print("=" * 100 + "\n")

summary_data = []

# Define key parameters to show for each simulator (only major non-zero ones)
# Format: parameter_name: (display_name, unit)
key_params = {
    'biomass_allocation': [
        ('total_biomass', 'g'),
        ('leaf_biomass', 'g'),
        ('stem_biomass', 'g'),
        ('root_biomass', 'g'),
        ('cumulative_biomass_gain', 'g'),
        ('daily_biomass_gain', 'g/day')
    ],
    'canopy_architecture': [
        ('lai', 'm²/m²'),
        ('leaf_area', 'm²'),
        ('canopy_height', 'm'),
        ('light_interception_efficiency', 'fraction'),
        ('cumulative_light_interception', 'MJ/m²')
    ],
    'leaf_development': [
        ('total_leaves', 'count'),
        ('total_leaf_area', 'm²'),
        ('cumulative_thermal_time', '°C·h')
    ],
    'nitrogen_balance': [
        ('nitrogen_stress_index', 'index'),
        ('nitrogen_use_efficiency', 'g/g')
    ],
    'nutrient_models': [
        ('solution_ec', 'dS/m'),
        ('solution_ph', 'pH'),
        ('cumulative_nutrient_uptake', 'g')
    ],
    'phenology': [
        ('current_growth_stage', 'stage'),
        ('thermal_time', '°C·h'),
        ('days_in_current_stage', 'days'),
        ('total_days_from_planting', 'days')
    ],
    'photosynthesis': [
        ('net_assimilation_rate', 'μmol/m²/s'),
        ('cumulative_carbon_gained', 'g'),
        ('daily_carbon_gained', 'g/day')
    ],
    'respiration': [
        ('total_respiration_rate', 'μmol/m²/s'),
        ('cumulative_respiration', 'g'),
        ('daily_respiration', 'g/day')
    ],
    'root_system': [
        ('root_depth', 'cm'),
        ('root_biomass', 'g'),
        ('root_length', 'cm'),
        ('root_surface_area', 'cm²')
    ],
    'stress_models': [
        ('integrated_stress', 'index'),
        ('stress_severity', 'level'),
        ('cumulative_stress', 'index·h')
    ],
    'water_uptake': [
        ('water_uptake_rate', 'L/h'),
        ('cumulative_water_uptake', 'L'),
        ('daily_water_uptake', 'L/day')
    ]
}

for csv_file in csv_files:
    simulator_name = csv_file.stem
    df = pd.read_csv(csv_file)

    # Remove base columns to show only simulator-specific columns
    base_cols = ['step', 'day', 'hour', 'timestamp']
    data_cols = [col for col in df.columns if col not in base_cols]

    print(f"┌{'─' * 98}┐")
    print(f"│ {simulator_name.upper().replace('_', ' '):^96} │")
    print(f"├{'─' * 98}┤")
    print(f"│ File: {csv_file.name:<88} │")
    print(f"│ Data Points: {len(df):<83} │")
    print(f"│ Parameters: {len(data_cols):<84} │")
    print(f"└{'─' * 98}┘")

    # Print final day values for key parameters only
    if len(df) > 0:
        final_row = df.iloc[-1]
        print(f"\n  Final Day Results:")
        print(f"  {'-' * 96}")

        # Get key parameters for this simulator
        key_cols_with_units = key_params.get(simulator_name, [])

        # Only show key parameters
        for param_name, unit in key_cols_with_units:
            if param_name not in data_cols:
                continue

            value = final_row[param_name]
            if pd.notna(value):
                # Try to parse string representations of dictionaries
                if isinstance(value, str) and value.startswith('{'):
                    try:
                        import ast
                        parsed_value = ast.literal_eval(value)
                        if isinstance(parsed_value, dict):
                            print(f"  ★ {param_name}:")
                            for k, v in parsed_value.items():
                                if isinstance(v, (int, float)):
                                    print(f"      - {str(k):<35} {v:>12.6f} {unit}")
                                else:
                                    print(f"      - {str(k):<35} {str(v):>12}")
                            continue
                    except (ValueError, SyntaxError) as e:
                        # Could not parse dictionary - skip and show as string
                        print(f"  WARNING: Could not parse dictionary for {param_name}: {e}")

                if isinstance(value, (int, float)):
                    print(f"  ★ {param_name:<40} {value:>12.4f}  {unit}")
                else:
                    val_str = str(value)
                    if len(val_str) > 50:
                        val_str = val_str[:47] + "..."
                    print(f"  ★ {param_name:<40} {val_str:>12}")
    print()

    summary_data.append({
        'simulator': simulator_name,
        'file': csv_file.name,
        'rows': len(df),
        'columns': len(data_cols),
        'data_columns': ', '.join(data_cols)
    })

# Create summary CSV
summary_df = pd.DataFrame(summary_data)
summary_df.to_csv(output_dir / "output_files_summary.csv", index=False)

print("=" * 100)
print(f"Total Output Files: {len(csv_files)}")
print(f"Summary CSV: output/output_files_summary.csv")
print("=" * 100 + "\n")
