#!/bin/bash
echo "Running Multi-Treatment Hydroponic Experiment..."
echo "Base Experiment: EXP001_2024"
echo "Crop Type: LET"
echo "Duration: 90 days"
echo "Total Treatments: 8"
echo "Output File: outputs/LET_EXP001_2024_combined_results.csv"
echo
cd "$(dirname "$0")"

mkdir -p temp_treatments

echo "[1/8] Running Treatment T01: :EXP001_2024"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T01 --output-csv temp_treatments/treatment_T01.csv
if [ $? -ne 0 ]; then
    echo "Treatment T01 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T01 completed successfully!"
echo

echo "[2/8] Running Treatment T02: :23"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T02 --output-csv temp_treatments/treatment_T02.csv
if [ $? -ne 0 ]; then
    echo "Treatment T02 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T02 completed successfully!"
echo

echo "[3/8] Running Treatment T03: :200"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T03 --output-csv temp_treatments/treatment_T03.csv
if [ $? -ne 0 ]; then
    echo "Treatment T03 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T03 completed successfully!"
echo

echo "[4/8] Running Treatment T04: :6.0"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T04 --output-csv temp_treatments/treatment_T04.csv
if [ $? -ne 0 ]; then
    echo "Treatment T04 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T04 completed successfully!"
echo

echo "[5/8] Running Treatment T05: :16"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T05 --output-csv temp_treatments/treatment_T05.csv
if [ $? -ne 0 ]; then
    echo "Treatment T05 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T05 completed successfully!"
echo

echo "[6/8] Running Treatment T06: :1200"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T06 --output-csv temp_treatments/treatment_T06.csv
if [ $? -ne 0 ]; then
    echo "Treatment T06 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T06 completed successfully!"
echo

echo "[7/8] Running Treatment T07: :1.2"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T07 --output-csv temp_treatments/treatment_T07.csv
if [ $? -ne 0 ]; then
    echo "Treatment T07 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T07 completed successfully!"
echo

echo "[8/8] Running Treatment T08: :1.5"
python3 cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T08 --output-csv temp_treatments/treatment_T08.csv
if [ $? -ne 0 ]; then
    echo "Treatment T08 failed!"
    read -p "Press Enter to continue..."
    exit 1
fi
echo "Treatment T08 completed successfully!"
echo

echo "Combining all treatments into single CSV file..."
echo "Date,Day,System_ID,Crop_ID,Treatment_ID,ETO_Ref_mm,ETC_Prime_mm,Transpiration_mm,Water_Total_L,Tank_Volume_L,Temp_C,Solar_Rad_MJ,VPD_kPa,WUE_kg_m3,pH,EC,RZT_C,RZT_Growth_Factor,RZT_Nutrient_Factor,V_Stage,Leaf_Number,Leaf_Area_m2,Avg_Leaf_Area_cm2,CO2_umol_mol,VPD_Actual_kPa,Env_Photo_Factor,Env_Transp_Factor,N-NO3_mg_L,P-PO4_mg_L,K_mg_L,Ca_mg_L,Mg_mg_L,LAI,Growth_Stage,Total_Biomass_g,Integrated_Stress,Temperature_Stress,Water_Stress,Nutrient_Stress,Nitrogen_Stress,Salinity_Stress" > outputs/LET_EXP001_2024_combined_results.csv
for file in temp_treatments/treatment_*.csv; do
    treatment_id=$(basename "$file" .csv | sed 's/treatment_//')
    tail -n +2 "$file" | while IFS=, read -r date day system_id crop_id rest; do
        echo "$date,$day,$system_id,$crop_id,LET_EXP001_2024_${treatment_id},$rest" >> outputs/LET_EXP001_2024_combined_results.csv
    done
done

echo "Cleaning up temporary files..."
rm -rf temp_treatments

echo "All treatments completed and combined successfully!"
echo "Combined results saved to: outputs/LET_EXP001_2024_combined_results.csv"
read -p "Press Enter to continue..."
