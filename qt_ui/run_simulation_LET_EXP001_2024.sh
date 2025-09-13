#!/bin/bash
echo "Running Multi-Treatment Hydroponic Experiment..."
echo "Base Experiment: EXP001_2024"
echo "Crop Type: LET"
echo "Duration: 90 days"
echo "Total Treatments: 1"
echo "Output File: ../outputs/LET_EXP001_2024_combined_results.csv"
echo
cd "$(dirname "$0")"

mkdir -p temp_treatments

echo "[1/1] Running Treatment T01: CO2:1200_EC:1.5_Light:16_Nitrogen:200_RootZoneTemp:20_Temperature:23_Varieties:LET_EXP001_2024_pH:6.0"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_T01
cp -r ../input/* temp_input_T01/
echo "Creating treatment-specific master parameters for T01..."
cp ../input/LET_EXP001_2024_master_parameters.csv temp_input_T01/T01_master_parameters.csv
echo "Creating treatment-specific weather file for T01..."
cp ../input/LET_EXP001_2024_weather.csv temp_input_T01/T01_weather.csv
echo "Setting CO2 to 1200 ppm for treatment T01..."
sed -i '' 's/target_co2,.*/target_co2,1200,ppm,Target CO2 concentration for treatment T01,environment,UI Generated,1.0/' temp_input_T01/T01_master_parameters.csv
echo "Setting EC to 1.5 for treatment T01..."
sed -i '' 's/optimal_ec,.*/optimal_ec,1.5,dS_per_m,Optimal EC for treatment T01,environment,UI Generated,1.0/' temp_input_T01/T01_master_parameters.csv
echo "Setting Nitrogen to 200 ppm for treatment T01..."
sed -i '' 's/initial_n_no3,.*/initial_n_no3,200,mg_per_L,Initial NO3-N concentration for treatment T01,nutrient_concentrations,UI Generated,1.0/' temp_input_T01/T01_master_parameters.csv
echo "Setting root zone temperature to 20°C for treatment T01..."
sed -i '' 's/optimal_root_temperature,.*/optimal_root_temperature,20,celsius,Optimal root zone temperature for treatment T01,root_zone_temperature,UI Generated,1.0/' temp_input_T01/T01_master_parameters.csv
echo "Setting temperature to 23°C for treatment T01..."
sed -i '' 's/environment_optimal_temperature,.*/environment_optimal_temperature,23,celsius,Optimal temperature for treatment T01,environment,UI Generated,1.0/' temp_input_T01/T01_master_parameters.csv
echo "Setting pH to 6.0 for treatment T01..."
sed -i '' 's/current_ph,.*/current_ph,6.0,pH_units,Current pH for treatment T01,nutrient_parameters,UI Generated,1.0/' temp_input_T01/T01_master_parameters.csv
python3 ../cropgro_cli.py --cultivar LET_EXP001_2024 --days 90 --treatment-id T01 --input-dir temp_input_T01 --output-csv temp_treatments/treatment_T01.csv
if [ $? -ne 0 ]; then
    echo "Treatment T01 failed!"
    exit 1
fi
echo "Treatment T01 completed successfully!"
rm -rf temp_input_T01
echo

echo "Combining all treatments into single CSV file..."
echo "Date,Day,Treatment_ID,System_ID,Crop_ID,ETO_Ref_mm,ETC_Prime_mm,Transpiration_mm,Water_Total_L,Tank_Volume_L,Temp_C,Solar_Rad_MJ,VPD_kPa,WUE_kg_m3,pH,EC,RZT_C,RZT_Growth_Factor,RZT_Nutrient_Factor,V_Stage,Leaf_Number,Leaf_Area_m2,Avg_Leaf_Area_cm2,CO2_umol_mol,VPD_Actual_kPa,Env_Photo_Factor,Env_Transp_Factor,N-NO3_mg_L,P-PO4_mg_L,K_mg_L,Ca_mg_L,Mg_mg_L,LAI,Growth_Stage,Total_Biomass_g,Integrated_Stress,Temperature_Stress,Water_Stress,Nutrient_Stress,Nitrogen_Stress,Salinity_Stress" > ../outputs/LET_EXP001_2024_combined_results.csv
if [ -f temp_treatments/treatment_T01.csv ]; then
    tail -n +2 temp_treatments/treatment_T01.csv | while IFS=, read -r date day treatment_id system_id crop_id rest; do
        echo "$date,$day,T01_CO21200_EC1.5_LIGHT16_NITROGEN200_ROOTZONETEMP20_TEMPERATURE23_VARIETIESLET_PH6.0,$system_id,$crop_id,$rest" >> ../outputs/LET_EXP001_2024_combined_results.csv
    done
fi

echo "Cleaning up temporary files..."
rm -rf temp_treatments

echo "All treatments completed and combined successfully!"
echo "Combined results saved to: ../outputs/LET_EXP001_2024_combined_results.csv"
