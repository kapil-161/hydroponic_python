#!/usr/bin/env python3
"""
Simulation Output Validator
Analyzes the final CSV output for biologically unrealistic values
"""

import pandas as pd
import numpy as np

def validate_simulation_output(csv_path="output/hydroponic_simulation.csv"):
    """Validate the simulation output for biological realism"""

    print("🔍 Validating Simulation Output for Biological Realism")
    print(f"Reading: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Loaded {len(df)} days of data")
    except Exception as e:
        print(f"❌ Could not read CSV: {e}")
        return False

    issues_found = []
    warnings_found = []

    # 1. Basic sanity checks
    print("\n=== Basic Sanity Checks ===")

    # Check for negative values where they shouldn't be
    negative_checks = {
        'total_biomass': 'Total biomass cannot be negative',
        'leaf_biomass': 'Leaf biomass cannot be negative',
        'stem_biomass': 'Stem biomass cannot be negative',
        'root_biomass': 'Root biomass cannot be negative',
        'lai': 'LAI cannot be negative',
        'photosynthesis_rate': 'Photosynthesis rate cannot be negative',
        'k_content': 'K content cannot be negative',
        'n_content': 'N content cannot be negative',
        'p_content': 'P content cannot be negative'
    }

    for col, message in negative_checks.items():
        if col in df.columns:
            negative_count = (df[col] < 0).sum()
            if negative_count > 0:
                issues_found.append(f"{message} (found {negative_count} negative values)")
                print(f"❌ {message}")
            else:
                print(f"✅ {col}: No negative values")

    # 2. Biomass growth realism
    print("\n=== Biomass Growth Realism ===")

    if 'total_biomass' in df.columns:
        initial_biomass = df['total_biomass'].iloc[0]
        final_biomass = df['total_biomass'].iloc[-1]
        growth_factor = final_biomass / initial_biomass if initial_biomass > 0 else 0

        print(f"Initial biomass: {initial_biomass:.4f} g")
        print(f"Final biomass: {final_biomass:.4f} g")
        print(f"Growth factor: {growth_factor:.2f}x")

        if growth_factor < 0.5:
            issues_found.append("Plant lost >50% biomass (unrealistic decline)")
            print("❌ Plant lost >50% biomass")
        elif growth_factor > 100:
            issues_found.append("Plant grew >100x initial size (unrealistic growth)")
            print("❌ Plant grew >100x initial size")
        elif growth_factor < 1.0:
            warnings_found.append("Plant lost biomass over simulation")
            print("⚠️  Plant lost biomass over simulation")
        else:
            print("✅ Biomass growth is reasonable")

    # 3. LAI realism
    print("\n=== LAI Realism ===")

    if 'lai' in df.columns:
        max_lai = df['lai'].max()
        print(f"Maximum LAI: {max_lai:.3f}")

        if max_lai > 6.0:
            issues_found.append(f"LAI too high ({max_lai:.3f}) for lettuce")
            print(f"❌ LAI too high for lettuce")
        elif max_lai < 0.001:
            warnings_found.append("LAI very low throughout simulation")
            print("⚠️  LAI very low throughout simulation")
        else:
            print("✅ LAI values are reasonable")

        # Check for unrealistic LAI jumps
        if len(df) > 1:
            lai_changes = df['lai'].diff().abs()
            max_lai_change = lai_changes.max()
            if max_lai_change > 1.0:
                issues_found.append(f"Unrealistic LAI jump ({max_lai_change:.3f}) between days")
                print(f"❌ Unrealistic LAI jump: {max_lai_change:.3f}")
            else:
                print("✅ No unrealistic LAI jumps")

    # 4. Nutrient content realism
    print("\n=== Nutrient Content Realism ===")

    nutrient_ranges = {
        'n_content': (10, 80, 'mg/g'),  # N: 1-8% dry weight
        'p_content': (1, 15, 'mg/g'),   # P: 0.1-1.5% dry weight
        'k_content': (5, 100, 'mg/g')   # K: 0.5-10% dry weight
    }

    for nutrient, (min_val, max_val, units) in nutrient_ranges.items():
        if nutrient in df.columns:
            final_content = df[nutrient].iloc[-1]
            max_content = df[nutrient].max()

            print(f"{nutrient}: final={final_content:.1f} {units}, max={max_content:.1f} {units}")

            if max_content > max_val:
                issues_found.append(f"{nutrient} too high ({max_content:.1f} {units} > {max_val} {units})")
                print(f"❌ {nutrient} too high")
            elif final_content < min_val:
                warnings_found.append(f"{nutrient} very low ({final_content:.1f} {units})")
                print(f"⚠️  {nutrient} very low")
            else:
                print(f"✅ {nutrient} in realistic range")

    # 5. Photosynthesis and respiration balance
    print("\n=== Carbon Balance Realism ===")

    if 'photosynthesis_rate' in df.columns and 'respiration_rate' in df.columns:
        photo_mean = df['photosynthesis_rate'].mean()
        resp_mean = df['respiration_rate'].mean()
        net_mean = photo_mean - resp_mean

        print(f"Mean photosynthesis: {photo_mean:.3f} g C/day")
        print(f"Mean respiration: {resp_mean:.3f} g C/day")
        print(f"Mean net assimilation: {net_mean:.3f} g C/day")

        if photo_mean <= 0:
            issues_found.append("Zero or negative photosynthesis")
            print("❌ Zero or negative photosynthesis")
        elif resp_mean <= 0:
            issues_found.append("Zero or negative respiration")
            print("❌ Zero or negative respiration")
        elif net_mean < -0.5:
            warnings_found.append("Net carbon loss is high")
            print("⚠️  High net carbon loss")
        else:
            print("✅ Carbon balance is reasonable")

    # 6. Growth stage progression
    print("\n=== Growth Stage Progression ===")

    if 'growth_stage' in df.columns:
        stages = df['growth_stage'].unique()
        print(f"Growth stages: {list(stages)}")

        # Check if plant progresses through stages
        if len(stages) == 1:
            warnings_found.append("Plant never changed growth stage")
            print("⚠️  Plant never changed growth stage")
        else:
            print("✅ Plant progressed through growth stages")

    # 7. Environmental conditions
    print("\n=== Environmental Conditions ===")

    env_ranges = {
        'air_temperature': (10, 40, '°C'),
        'solution_temperature': (10, 35, '°C'),
        'humidity': (30, 90, '%'),
        'ph': (5.0, 8.0, 'pH units')
    }

    for param, (min_val, max_val, units) in env_ranges.items():
        if param in df.columns:
            param_min = df[param].min()
            param_max = df[param].max()

            if param_max > max_val or param_min < min_val:
                warnings_found.append(f"{param} outside typical range ({param_min:.1f}-{param_max:.1f} {units})")
                print(f"⚠️  {param} outside typical range")
            else:
                print(f"✅ {param} in reasonable range")

    # Summary
    print("\n" + "="*50)
    print("🏁 VALIDATION SUMMARY")
    print("="*50)

    if issues_found:
        print("\n❌ CRITICAL ISSUES FOUND:")
        for issue in issues_found:
            print(f"  • {issue}")
    else:
        print("\n✅ No critical issues found")

    if warnings_found:
        print("\n⚠️  WARNINGS:")
        for warning in warnings_found:
            print(f"  • {warning}")
    else:
        print("\n✅ No warnings")

    if not issues_found and not warnings_found:
        print("\n🎉 All validation checks passed! Simulation output appears biologically realistic.")
        return True
    else:
        print(f"\nFound {len(issues_found)} critical issues and {len(warnings_found)} warnings.")
        return False

if __name__ == "__main__":
    validate_simulation_output()