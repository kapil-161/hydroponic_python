import pandas as pd
import sys

try:
    df = pd.read_csv('output/simulation_results.csv')
    print(f"Shape: {df.shape}")
    print(f"Expected columns: 205")
    print(f"Actual columns: {len(df.columns)}")
    print(f"\nChecking for problematic columns...")
    
    problem_cols = []
    for col in df.columns:
        sample = str(df[col].iloc[0]) if len(df) > 0 else ''
        if ',' in sample and len(sample) > 30:
            problem_cols.append((col, sample[:150]))
    
    if problem_cols:
        print(f"\nFound {len(problem_cols)} columns with comma-containing values:")
        for col, sample in problem_cols[:10]:
            print(f"\n{col}:")
            print(f"  {sample}...")
    else:
        print("No obvious comma issues found in column values")
        
    # Check file size
    import os
    size = os.path.getsize('output/simulation_results.csv')
    print(f"\nFile size: {size / (1024*1024):.2f} MB")
    print(f"Expected size (68 rows * 205 cols * ~10 chars): ~{68 * 205 * 10 / (1024*1024):.2f} MB")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

