#!/usr/bin/env python3
"""
Parameter Validation Script
Detects duplicate parameters across CSV files and ensures single source of truth
"""

import pandas as pd
import glob
from pathlib import Path
from collections import defaultdict
import sys

def find_parameter_conflicts(input_dir="input"):
    """Find parameters that appear in multiple CSV files with different values."""
    
    print("🔍 PARAMETER CONFLICT DETECTION")
    print("=" * 50)
    
    # Find all CSV files
    csv_files = glob.glob(f"{input_dir}/LET_EXP001_2024_*.csv")
    
    # Dictionary to store parameter values from each file
    parameter_sources = defaultdict(dict)
    conflicts = []
    
    # Load parameters from each file
    for file_path in csv_files:
        file_name = Path(file_path).name
        try:
            df = pd.read_csv(file_path)
            if 'parameter_name' in df.columns and 'value' in df.columns:
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    parameter_sources[param_name][file_name] = param_value
        except Exception as e:
            print(f"⚠️  Error reading {file_name}: {e}")
    
    # Check for conflicts
    for param_name, sources in parameter_sources.items():
        if len(sources) > 1:
            # Check if values are different
            values = list(sources.values())
            if len(set(str(v) for v in values)) > 1:
                conflicts.append({
                    'parameter': param_name,
                    'sources': sources,
                    'values': values
                })
    
    # Report results
    if conflicts:
        print(f"❌ FOUND {len(conflicts)} PARAMETER CONFLICTS:")
        print()
        for conflict in conflicts:
            print(f"Parameter: {conflict['parameter']}")
            for file_name, value in conflict['sources'].items():
                print(f"  {file_name}: {value}")
            print()
        
        print("🚨 RECOMMENDATION:")
        print("Use the master_parameters.csv file as single source of truth")
        print("Remove duplicate parameters from other CSV files")
        return False
    else:
        print("✅ NO PARAMETER CONFLICTS FOUND")
        return True

def validate_master_file(input_dir="input"):
    """Validate that master parameters file exists and is complete."""
    
    master_file = f"{input_dir}/LET_EXP001_2024_master_parameters.csv"
    
    if not Path(master_file).exists():
        print("❌ Master parameters file not found!")
        return False
    
    try:
        df = pd.read_csv(master_file)
        required_columns = ['parameter_name', 'value', 'unit', 'description', 'category', 'reference', 'priority']
        
        for col in required_columns:
            if col not in df.columns:
                print(f"❌ Missing required column: {col}")
                return False
        
        print(f"✅ Master parameters file validated: {len(df)} parameters")
        return True
        
    except Exception as e:
        print(f"❌ Error validating master file: {e}")
        return False

def check_parameter_completeness(input_dir="input"):
    """Check if all required parameters are present in master file."""
    
    master_file = f"{input_dir}/LET_EXP001_2024_master_parameters.csv"
    
    try:
        df = pd.read_csv(master_file)
        
        # Essential parameters that must be present
        essential_params = [
            'optimal_temperature', 'base_temperature', 'optimal_vpd_min', 'optimal_vpd_max',
            'vcmax_25', 'jmax_25', 'rd_25', 'uptake_efficiency', 'senescence_rate',
            'water_stress_threshold', 'nitrogen_stress_threshold', 'system_type', 'tank_volume'
        ]
        
        missing_params = []
        for param in essential_params:
            if param not in df['parameter_name'].values:
                missing_params.append(param)
        
        if missing_params:
            print(f"❌ Missing essential parameters: {missing_params}")
            return False
        else:
            print("✅ All essential parameters present")
            return True
            
    except Exception as e:
        print(f"❌ Error checking completeness: {e}")
        return False

def main():
    """Main validation function."""
    
    print("🔬 HYDROPONIC SIMULATION PARAMETER VALIDATION")
    print("=" * 60)
    print()
    
    # Check 1: Parameter conflicts
    no_conflicts = find_parameter_conflicts()
    print()
    
    # Check 2: Master file validation
    master_valid = validate_master_file()
    print()
    
    # Check 3: Parameter completeness
    complete = check_parameter_completeness()
    print()
    
    # Summary
    print("📊 VALIDATION SUMMARY")
    print("=" * 30)
    print(f"Parameter conflicts: {'✅ PASS' if no_conflicts else '❌ FAIL'}")
    print(f"Master file valid: {'✅ PASS' if master_valid else '❌ FAIL'}")
    print(f"Parameters complete: {'✅ PASS' if complete else '❌ FAIL'}")
    print()
    
    if no_conflicts and master_valid and complete:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("Your parameter system is ready for simulation.")
        return 0
    else:
        print("⚠️  VALIDATION ISSUES DETECTED")
        print("Please fix the issues above before running simulations.")
        return 1

if __name__ == "__main__":
    sys.exit(main())