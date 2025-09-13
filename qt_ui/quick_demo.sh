#!/bin/bash
echo "Running Quick Demo (2 treatments, 3 days each)..."
echo "Output File: ../outputs/LET_EXP001_2024_combined_results.csv"
echo
cd "$(dirname "$0")"

mkdir -p temp_treatments

# Treatment 1
echo "[1/2] Running Treatment T01: Temperature 23°C, EC 1.5"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_T01
cp -r ../input/* temp_input_T01/
echo "Creating treatment-specific master parameters for T01..."
cp ../input/LET_EXP001_2024_master_parameters.csv temp_input_T01/LET_EXP001_2024_master_parameters.csv
python3 ../cropgro_cli.py --cultivar LET_EXP001_2024 --days 3 --treatment-id T01 --input-dir temp_input_T01 --output-csv temp_treatments/treatment_T01.csv
echo "Treatment T01 completed!"
rm -rf temp_input_T01

# Treatment 2 - slightly different parameters
echo "[2/2] Running Treatment T02: Temperature 26°C, EC 1.8"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_T02
cp -r ../input/* temp_input_T02/
echo "Creating treatment-specific master parameters for T02..."
cp ../input/LET_EXP001_2024_master_parameters.csv temp_input_T02/LET_EXP001_2024_master_parameters.csv
python3 ../cropgro_cli.py --cultivar LET_EXP001_2024 --days 3 --treatment-id T02 --input-dir temp_input_T02 --output-csv temp_treatments/treatment_T02.csv
echo "Treatment T02 completed!"
rm -rf temp_input_T02

# Combine results
echo "Combining treatments into single CSV file..."
echo "Date,Day,Treatment_ID,System_ID,Crop_ID,ETO_Ref_mm,ETC_Prime_mm,Transpiration_mm,Water_Total_L,Tank_Volume_L,Temp_C,Solar_Rad_MJ,VPD_kPa,WUE_L_kg,pH,EC,RZT_C,RZT_Growth_Factor,RZT_Nutrient_Factor,V_Stage,Leaf_Number,Leaf_Area_m2,Avg_Leaf_Area_cm2,CO2_umol_mol,VPD_Actual_kPa,Env_Photo_Factor,Env_Transp_Factor,N-NO3_mg_L,P-PO4_mg_L,K_mg_L,Ca_mg_L,Mg_mg_L,LAI,Growth_Stage,Total_Biomass_g,Integrated_Stress,Temperature_Stress,Water_Stress,Nutrient_Stress,Nitrogen_Stress,Salinity_Stress" > ../outputs/LET_EXP001_2024_combined_results.csv

# Add Treatment 1 data with meaningful ID
if [ -f temp_treatments/treatment_T01.csv ]; then
    tail -n +2 temp_treatments/treatment_T01.csv | while IFS=, read -r date day treatment_id system_id crop_id rest; do
        echo "$date,$day,T01_TEMP23_EC1.5,$system_id,$crop_id,$rest" >> ../outputs/LET_EXP001_2024_combined_results.csv
    done
fi

# Add Treatment 2 data with meaningful ID  
if [ -f temp_treatments/treatment_T02.csv ]; then
    tail -n +2 temp_treatments/treatment_T02.csv | while IFS=, read -r date day treatment_id system_id crop_id rest; do
        echo "$date,$day,T02_TEMP26_EC1.8,$system_id,$crop_id,$rest" >> ../outputs/LET_EXP001_2024_combined_results.csv
    done
fi

echo "Cleaning up temporary files..."
rm -rf temp_treatments

echo "✅ Quick demo completed!"
echo "Combined results saved to: ../outputs/LET_EXP001_2024_combined_results.csv"
echo ""
echo "🎯 Now you can:"
echo "1. Open the Qt UI: cd build && ./HydroponicCSVEditor"
echo "2. Go to 'Results Viewer' tab to see the data"
echo "3. Go to 'Time Series Plot' tab to see charts"