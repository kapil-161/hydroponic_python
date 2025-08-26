#!/bin/bash
echo "Running Multi-Treatment Hydroponic Experiment..."
echo "Base Experiment: EXP001_2024"
echo "Crop Type: LET"
echo "Duration: 90 days"
echo "Total Treatments: 8"
echo
cd "$(dirname "$0")"

echo "[1/8] Running Treatment: :EXP001_2024"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T01_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :EXP001_2024 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :EXP001_2024 completed successfully!"
echo

echo "[2/8] Running Treatment: :23"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T02_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :23 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :23 completed successfully!"
echo

echo "[3/8] Running Treatment: :200"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T03_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :200 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :200 completed successfully!"
echo

echo "[4/8] Running Treatment: :6.0"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T04_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :6.0 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :6.0 completed successfully!"
echo

echo "[5/8] Running Treatment: :16"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T05_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :16 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :16 completed successfully!"
echo

echo "[6/8] Running Treatment: :1200"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T06_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :1200 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :1200 completed successfully!"
echo

echo "[7/8] Running Treatment: :1.2"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T07_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :1.2 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :1.2 completed successfully!"
echo

echo "[8/8] Running Treatment: :1.5"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --output-csv outputs/LET_EXP001_2024_T08_results.csv
if [ $? -ne 0 ]; then
    echo "Treatment :1.5 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment :1.5 completed successfully!"
echo

echo "All treatments completed successfully!"
read -p "Press Enter to continue..."
