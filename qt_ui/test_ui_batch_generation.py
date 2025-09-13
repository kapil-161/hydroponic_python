#!/usr/bin/env python3
"""
Test the UI batch generation logic to verify it produces working shell scripts
"""

def generate_treatment_combinations():
    """Replicate the Qt UI factorial design logic"""
    treatments = {
        "Varieties": ["LET_EXP001_2024", "LET_EXP002_2024"],
        "Temperature": ["23", "26"], 
        "RootZoneTemp": ["20", "22"],
        "Nitrogen": ["200"],
        "pH": ["6.0"],
        "Light": ["16"],
        "CO2": ["1200"],
        "EC": ["1.5", "1.8"]
    }
    
    categories = list(treatments.keys())
    combinations = []
    
    def generate_combos(category_index, current_combo):
        if category_index >= len(categories):
            combo_str = "_".join(f"{categories[i]}:{current_combo[i]}" for i in range(len(categories)))
            combinations.append(combo_str)
            return
        
        for value in treatments[categories[category_index]]:
            new_combo = current_combo + [value]
            generate_combos(category_index + 1, new_combo)
    
    generate_combos(0, [])
    return combinations

def create_ui_style_batch(combinations):
    """Create batch file using the updated UI logic"""
    experiment_name = "EXP001_2024"
    crop_type = "LET"
    duration = 5  # Short test
    
    batch_content = f"""#!/bin/bash
echo "Running Multi-Treatment Hydroponic Experiment..."
echo "Base Experiment: {experiment_name}"
echo "Crop Type: {crop_type}"
echo "Duration: {duration} days"
echo "Total Treatments: {len(combinations)}"
echo "Output File: ../outputs/{crop_type}_{experiment_name}_combined_results.csv"
echo
cd "$(dirname "$0")"

mkdir -p temp_treatments

"""
    
    for i, combo in enumerate(combinations):
        treatment_id = f"T{i+1:02d}"
        temp_output_file = f"temp_treatments/treatment_{treatment_id}.csv"
        
        batch_content += f"""echo "[{i+1}/{len(combinations)}] Running Treatment {treatment_id}: {combo}"
echo "Creating treatment-specific input files..."
mkdir -p temp_input_{treatment_id}
cp -r ../input/* temp_input_{treatment_id}/
echo "Creating treatment-specific master parameters for {treatment_id}..."
cp ../input/{crop_type}_{experiment_name}_master_parameters.csv temp_input_{treatment_id}/{crop_type}_{experiment_name}_master_parameters.csv
"""
        
        # Parse combination parameters (replicate UI logic)
        parts = combo.split("_")
        for part in parts:
            if ":" in part:
                key_value = part.split(":")
                if len(key_value) == 2:
                    category = key_value[0].lower()
                    value = key_value[1]
                    
                    if category == "temperature":
                        batch_content += f'echo "Setting temperature to {value}°C for treatment {treatment_id}..."\n'
                        batch_content += f"sed -i '' 's/environment_optimal_temperature,.*/environment_optimal_temperature,{value},celsius,Optimal temperature for treatment {treatment_id},environment,UI Generated,1.0/' temp_input_{treatment_id}/{crop_type}_{experiment_name}_master_parameters.csv\n"
                    elif category == "ec":
                        batch_content += f'echo "Setting EC to {value} for treatment {treatment_id}..."\n'
                        batch_content += f"sed -i '' 's/optimal_ec,.*/optimal_ec,{value},dS_per_m,Optimal EC for treatment {treatment_id},environment,UI Generated,1.0/' temp_input_{treatment_id}/{crop_type}_{experiment_name}_master_parameters.csv\n"
                    elif category == "rootzonetemp":
                        batch_content += f'echo "Setting root zone temperature to {value}°C for treatment {treatment_id}..."\n'
                        batch_content += f"sed -i '' 's/root_zone_optimal_temperature,.*/root_zone_optimal_temperature,{value},celsius,Optimal root zone temperature for treatment {treatment_id},root_zone_temperature,UI Generated,1.0/' temp_input_{treatment_id}/{crop_type}_{experiment_name}_master_parameters.csv\n"
        
        batch_content += f"""python3 ../cropgro_cli.py --cultivar {crop_type}_{experiment_name} --days {duration} --treatment-id {treatment_id} --input-dir temp_input_{treatment_id} --output-csv {temp_output_file}
if [ $? -ne 0 ]; then
    echo "Treatment {treatment_id} failed!"
    exit 1
fi
echo "Treatment {treatment_id} completed successfully!"
rm -rf temp_input_{treatment_id}
echo

"""
    
    # Add results combining logic
    batch_content += f"""echo "Combining all treatments into single CSV file..."
echo "Date,Day,Treatment_ID,System_ID,Crop_ID,DAS,DAT,Temp_C,EC,pH,Total_Biomass_g,LAI" > ../outputs/{crop_type}_{experiment_name}_combined_results.csv

"""
    
    for i, combo in enumerate(combinations):
        treatment_id = f"T{i+1:02d}"
        meaningful_id = f"{treatment_id}_{combo.replace(':', '').replace('_', '_')}"
        
        batch_content += f"""if [ -f temp_treatments/treatment_{treatment_id}.csv ]; then
    tail -n +2 temp_treatments/treatment_{treatment_id}.csv | while IFS=, read -r date day das dat old_treatment_id system_id crop_id rest; do
        echo "$date,$day,{meaningful_id},$system_id,$crop_id,$das,$dat,$rest" | head -c 1000 >> ../outputs/{crop_type}_{experiment_name}_combined_results.csv
        echo >> ../outputs/{crop_type}_{experiment_name}_combined_results.csv
    done
fi
"""
    
    batch_content += f"""
echo "Cleaning up temporary files..."
rm -rf temp_treatments

echo "All treatments completed and combined successfully!"
echo "Combined results saved to: ../outputs/{crop_type}_{experiment_name}_combined_results.csv"
"""
    
    return batch_content

def main():
    print("=== Testing UI Multi-Treatment Batch Generation ===")
    
    # Generate combinations using UI logic
    combinations = generate_treatment_combinations()
    print(f"Generated {len(combinations)} treatment combinations:")
    for i, combo in enumerate(combinations[:5], 1):
        print(f"  {i}. {combo}")
    if len(combinations) > 5:
        print(f"  ... and {len(combinations) - 5} more")
    
    # Create batch file
    batch_content = create_ui_style_batch(combinations)
    batch_file = "run_simulation_UI_test.sh"
    
    with open(batch_file, 'w') as f:
        f.write(batch_content)
    
    import os
    os.chmod(batch_file, 0o755)
    
    print(f"\n✅ UI-style batch file created: {batch_file}")
    print(f"📊 Total treatments: {len(combinations)}")
    print(f"📄 Batch file size: {len(batch_content)} characters")
    
    return batch_file

if __name__ == "__main__":
    batch_file = main()