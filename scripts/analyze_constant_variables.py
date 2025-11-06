"""
Example: Analyze Constant Variables (excluding expected zeros/constants)

This script demonstrates how to analyze simulation outputs while filtering out
biologically expected zero and constant variables.
"""

import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.analysis_helpers import (
    filter_expected_variables,
    is_expected_zero,
    is_expected_constant
)


def analyze_constant_variables(csv_path: str, simulator_name: str = None):
    """
    Analyze which variables are constant, excluding expected zeros/constants.
    
    Args:
        csv_path: Path to CSV file with simulation results
        simulator_name: Name of simulator (e.g., 'nitrogen_balance')
    """
    df = pd.read_csv(csv_path)
    
    # Get all numeric columns (excluding metadata columns)
    metadata_cols = ['step', 'day', 'hour', 'timestamp']
    numeric_cols = [col for col in df.columns 
                   if col not in metadata_cols 
                   and df[col].dtype in ['float64', 'int64']]
    
    # Filter out expected zero and constant variables
    filtered_cols = filter_expected_variables(numeric_cols, simulator_name)
    
    print('=' * 80)
    print(f'Constant Variable Analysis: {Path(csv_path).name}')
    print('=' * 80)
    print()
    
    dynamic_vars = []
    constant_vars = []
    expected_zero_vars = []
    expected_const_vars = []
    
    for col in numeric_cols:
        numeric_values = pd.to_numeric(df[col], errors='coerce')
        non_null = numeric_values.dropna()
        
        if len(non_null) == 0:
            continue
            
        unique_count = non_null.nunique()
        
        if is_expected_zero(col, simulator_name):
            expected_zero_vars.append(col)
        elif is_expected_constant(col, simulator_name):
            expected_const_vars.append(col)
        elif col in filtered_cols:
            if unique_count > 1:
                dynamic_vars.append(col)
            else:
                constant_vars.append(col)
    
    print(f'✅ Dynamic variables ({len(dynamic_vars)}):')
    for var in dynamic_vars[:10]:  # Show first 10
        numeric_values = pd.to_numeric(df[var], errors='coerce')
        non_null = numeric_values.dropna()
        print(f'  {var}: {non_null.nunique()} unique values')
    if len(dynamic_vars) > 10:
        print(f'  ... and {len(dynamic_vars) - 10} more')
    
    print(f'\n⚠️  Constant variables ({len(constant_vars)}):')
    for var in constant_vars[:10]:  # Show first 10
        numeric_values = pd.to_numeric(df[var], errors='coerce')
        non_null = numeric_values.dropna()
        value = non_null.iloc[0]
        print(f'  {var}: {value}')
    if len(constant_vars) > 10:
        print(f'  ... and {len(constant_vars) - 10} more')
    
    print(f'\n📋 Expected zero variables (excluded from analysis) ({len(expected_zero_vars)}):')
    for var in expected_zero_vars:
        print(f'  {var}')
    
    print(f'\n📋 Expected constant variables (excluded from analysis) ({len(expected_const_vars)}):')
    for var in expected_const_vars:
        print(f'  {var}')
    
    print(f'\nSummary:')
    print(f'  Total variables analyzed: {len(filtered_cols)}')
    print(f'  Dynamic: {len(dynamic_vars)}')
    print(f'  Constant (needs investigation): {len(constant_vars)}')
    print(f'  Expected zeros (excluded): {len(expected_zero_vars)}')
    print(f'  Expected constants (excluded): {len(expected_const_vars)}')


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print('Usage: python analyze_constant_variables.py <csv_path> [simulator_name]')
        print('Example: python analyze_constant_variables.py output/nitrogen_balance.csv nitrogen_balance')
        sys.exit(1)
    
    csv_path = sys.argv[1]
    simulator_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    analyze_constant_variables(csv_path, simulator_name)

