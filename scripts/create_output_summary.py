"""Create a summary of all output CSV files"""
import pandas as pd
import os
from pathlib import Path

output_dir = Path("output")
# Get all CSV files except the combined results file and summary
csv_files = sorted([f for f in output_dir.glob("*.csv")
                    if f.name not in ["simulation_results.csv", "output_files_summary.csv"]])

print("=" * 80)
print("SIMULATION OUTPUT FILES SUMMARY")
print("=" * 80)
print()

summary_data = []

for csv_file in csv_files:
    simulator_name = csv_file.stem
    df = pd.read_csv(csv_file)

    # Remove base columns to show only simulator-specific columns
    base_cols = ['step', 'day', 'hour', 'timestamp']
    data_cols = [col for col in df.columns if col not in base_cols]

    print(f"File: {csv_file.name}")
    print(f"Simulator: {simulator_name}")
    print(f"Rows: {len(df)}")
    print(f"Data columns ({len(data_cols)}): {', '.join(data_cols)}")
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

print("=" * 80)
print(f"Total simulator output files: {len(csv_files)}")
print(f"Summary saved to: output/output_files_summary.csv")
print("=" * 80)
