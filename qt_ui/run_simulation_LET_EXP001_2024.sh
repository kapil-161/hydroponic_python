#!/bin/bash
echo "Running Multi-Treatment Hydroponic Experiment..."
echo "Base Experiment: EXP001_2024"
echo "Crop Type: LET"
echo "Duration: 90 days"
echo "Total Treatments: 2"
echo "Output File: ../outputs/LET_EXP001_2024_combined_results.csv"
echo
cd "$(dirname "$0")"

mkdir -p temp_treatments

echo "[1/2] Running Treatment T01: CO2:1200_EC:1.5_Light:16_Nitrogen:200_RootZoneTemp:20_Temperature:23_Varieties:LET_EXP001_2024_pH:6.0"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_T01
cp -r ../input/* temp_input_T01/
echo "Setting CO2 to 1200 ppm for treatment T01..."
sed -i '' 's/co2_concentration,.*/co2_concentration,1200/' temp_input_T01/LET_EXP001_2024_system_settings.csv
echo "Setting EC to 1.5 for treatment T01..."
sed -i '' 's/initial_ec,.*/initial_ec,1.5/' temp_input_T01/LET_EXP001_2024_system_settings.csv
echo "Setting light intensity to 16 MJ/m²/day for treatment T01..."
sed -i '' 's/optimal_light_intensity,.*/optimal_light_intensity,16/' temp_input_T01/LET_EXP001_2024_environment_parameters.csv
echo "Setting Nitrogen to 200 ppm for treatment T01..."
sed -i '' 's/N-NO3,200/N-NO3,200/' temp_input_T01/LET_EXP001_2024_nutrient_solution.csv
echo "Setting root zone temperature to 20°C for treatment T01..."
sed -i '' 's/optimal_temperature,.*/optimal_temperature,20/' temp_input_T01/LET_EXP001_2024_root_zone_parameters.csv
echo "Setting temperature to 23°C for treatment T01..."
sed -i '' 's/target_temperature,.*/target_temperature,23/' temp_input_T01/LET_EXP001_2024_system_settings.csv
echo "Setting pH to 6.0 for treatment T01..."
sed -i '' 's/initial_ph,.*/initial_ph,6.0/' temp_input_T01/LET_EXP001_2024_system_settings.csv
python3 ../cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T01 --input-dir temp_input_T01 --output-csv temp_treatments/treatment_T01.csv
if [ $? -ne 0 ]; then
    echo "Treatment T01 failed!"
    exit 1
fi
echo "Treatment T01 completed successfully!"
rm -rf temp_input_T01
echo

echo "[2/2] Running Treatment T02: CO2:1200_EC:1.5_Light:16_Nitrogen:200_RootZoneTemp:25_Temperature:23_Varieties:LET_EXP001_2024_pH:6.0"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_T02
cp -r ../input/* temp_input_T02/
echo "Setting CO2 to 1200 ppm for treatment T02..."
sed -i '' 's/co2_concentration,.*/co2_concentration,1200/' temp_input_T02/LET_EXP001_2024_system_settings.csv
echo "Setting EC to 1.5 for treatment T02..."
sed -i '' 's/initial_ec,.*/initial_ec,1.5/' temp_input_T02/LET_EXP001_2024_system_settings.csv
echo "Setting light intensity to 16 MJ/m²/day for treatment T02..."
sed -i '' 's/optimal_light_intensity,.*/optimal_light_intensity,16/' temp_input_T02/LET_EXP001_2024_environment_parameters.csv
echo "Setting Nitrogen to 200 ppm for treatment T02..."
sed -i '' 's/N-NO3,200/N-NO3,200/' temp_input_T02/LET_EXP001_2024_nutrient_solution.csv
echo "Setting root zone temperature to 25°C for treatment T02..."
sed -i '' 's/optimal_temperature,.*/optimal_temperature,25/' temp_input_T02/LET_EXP001_2024_root_zone_parameters.csv
echo "Setting temperature to 23°C for treatment T02..."
sed -i '' 's/target_temperature,.*/target_temperature,23/' temp_input_T02/LET_EXP001_2024_system_settings.csv
echo "Setting pH to 6.0 for treatment T02..."
sed -i '' 's/initial_ph,.*/initial_ph,6.0/' temp_input_T02/LET_EXP001_2024_system_settings.csv
python3 ../cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T02 --input-dir temp_input_T02 --output-csv temp_treatments/treatment_T02.csv
if [ $? -ne 0 ]; then
    echo "Treatment T02 failed!"
    exit 1
fi
echo "Treatment T02 completed successfully!"
rm -rf temp_input_T02
echo

echo "Combining all treatments into single CSV file..."
echo "Date,Day,Treatment_ID,System_ID,Crop_ID,ETO_Ref_mm,ETC_Prime_mm,Transpiration_mm,Water_Total_L,Tank_Volume_L,Temp_C,Solar_Rad_MJ,VPD_kPa,WUE_kg_m3,pH,EC,RZT_C,RZT_Growth_Factor,RZT_Nutrient_Factor,V_Stage,Leaf_Number,Leaf_Area_m2,Avg_Leaf_Area_cm2,CO2_umol_mol,VPD_Actual_kPa,Env_Photo_Factor,Env_Transp_Factor,N-NO3_mg_L,P-PO4_mg_L,K_mg_L,Ca_mg_L,Mg_mg_L,LAI,Growth_Stage,Total_Biomass_g,Integrated_Stress,Temperature_Stress,Water_Stress,Nutrient_Stress,Nitrogen_Stress,Salinity_Stress" > ../outputs/LET_EXP001_2024_combined_results.csv
if [ -f temp_treatments/treatment_T01.csv ]; then
    tail -n +2 temp_treatments/treatment_T01.csv | while IFS=, read -r date day treatment_id system_id crop_id rest; do
        echo "$date,$day,T01_CO21200_EC1.5_LIGHT16_NITROGEN200_ROOTZONETEMP20_TEMPERATURE23_VARIETIESLET_PH6.0,$system_id,$crop_id,$rest" >> ../outputs/LET_EXP001_2024_combined_results.csv
    done
fi
if [ -f temp_treatments/treatment_T02.csv ]; then
    tail -n +2 temp_treatments/treatment_T02.csv | while IFS=, read -r date day treatment_id system_id crop_id rest; do
        echo "$date,$day,T02_CO21200_EC1.5_LIGHT16_NITROGEN200_ROOTZONETEMP25_TEMPERATURE23_VARIETIESLET_PH6.0,$system_id,$crop_id,$rest" >> ../outputs/LET_EXP001_2024_combined_results.csv
    done
fi

echo "Cleaning up temporary files..."
rm -rf temp_treatments

echo "All treatments completed and combined successfully!"
echo "Combined results saved to: ../outputs/LET_EXP001_2024_combined_results.csv"
