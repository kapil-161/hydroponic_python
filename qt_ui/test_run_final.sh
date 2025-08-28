#!/bin/bash
echo "Running Multi-Treatment Hydroponic Experiment..."
echo "Base Experiment: EXP001_2024"
echo "Crop Type: LET"
echo "Duration: 90 days"
echo "Total Treatments: 2"
echo "Output File: outputs/LET_EXP001_2024_combined_results.csv"
echo
cd "$(dirname "$0")"

mkdir -p temp_treatments

echo "[1/2] Running Treatment T01: CO2:1200_EC:1.2_Light:16_Nitrogen:200_Temperature:23_Varieties:EXP001_2024_pH:6.0"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_T01
cp -r ../input/* temp_input_T01/
echo "Setting EC to 1.2 for treatment T01..."
sed -i '' 's/EC,.*/EC,1.2/' temp_input_T01/LET_EXP001_2024_nutrient_solution.csv
python3 ../cropgro_cli.py --cultivar LET_EXP001_2024 --days 5 --treatment-id T01 --input-dir temp_input_T01 --output-csv temp_treatments/treatment_T01.csv
if [ $? -ne 0 ]; then
    echo "Treatment T01 failed!"
    exit 1
fi
echo "Treatment T01 completed successfully!"
rm -rf temp_input_T01
echo

echo "[2/2] Running Treatment T02: CO2:1200_EC:1.5_Light:16_Nitrogen:200_Temperature:23_Varieties:EXP001_2024_pH:6.0"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_T02
cp -r ../input/* temp_input_T02/
echo "Setting EC to 1.5 for treatment T02..."
sed -i '' 's/EC,.*/EC,1.5/' temp_input_T02/LET_EXP001_2024_nutrient_solution.csv
python3 ../cropgro_cli.py --cultivar LET_EXP001_2024 --days 5 --treatment-id T02 --input-dir temp_input_T02 --output-csv temp_treatments/treatment_T02.csv
if [ $? -ne 0 ]; then
    echo "Treatment T02 failed!"
    exit 1
fi
echo "Treatment T02 completed successfully!"
rm -rf temp_input_T02
echo

echo "Combining all treatments into single CSV file..."
echo "Date,Day,Treatment_ID,System_ID,Crop_ID,ETO_Ref_mm,ETC_Prime_mm,Transpiration_mm,Water_Total_L,Tank_Volume_L,Temp_C,Solar_Rad_MJ,VPD_kPa,WUE_kg_m3,pH,EC,RZT_C,RZT_Growth_Factor,RZT_Nutrient_Factor,V_Stage,Leaf_Number,Leaf_Area_m2,Avg_Leaf_Area_cm2,CO2_umol_mol,VPD_Actual_kPa,Env_Photo_Factor,Env_Transp_Factor,N-NO3_mg_L,P-PO4_mg_L,K_mg_L,Ca_mg_L,Mg_mg_L,LAI,Growth_Stage,Total_Biomass_g,Integrated_Stress,Temperature_Stress,Water_Stress,Nutrient_Stress,Nitrogen_Stress,Salinity_Stress" > outputs/LET_EXP001_2024_combined_results.csv
for file in temp_treatments/treatment_*.csv; do
    treatment_id=$(basename "$file" .csv | sed 's/treatment_//')
    tail -n +2 "$file" | while IFS=, read -r date day treatment_id system_id crop_id rest; do
        echo "$date,$day,LET_EXP001_2024_${treatment_id},$system_id,$crop_id,$rest" >> outputs/LET_EXP001_2024_combined_results.csv
    done
done

echo "Cleaning up temporary files..."
rm -rf temp_treatments

echo "All treatments completed and combined successfully!"
echo "Combined results saved to: outputs/LET_EXP001_2024_combined_results.csv"
