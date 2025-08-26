#!/bin/bash
echo "Running Hydroponic Simulation..."
echo "Experiment: EXP001_2024"
echo "Crop Type: LET"
echo "Duration: 90 days"
echo
cd "$(dirname "$0")"
python3 cropgro_cli.py --experiment LET_EXP001_2024 --days 90 --output-csv LET_EXP001_2024_results.csv
if [ $? -eq 0 ]; then
    echo "Simulation completed successfully!"
else
    echo "Simulation failed with error code $?"
fi
read -p "Press Enter to continue..."
