#!/usr/bin/env python3
"""
Helper script to create new experiment file sets from existing templates.

Usage:
    python3 create_experiment.py LET_EXP003_2024 --from LET_EXP001_2024
    python3 create_experiment.py TOM_EXP001_2024 --from LET_EXP001_2024
"""

import argparse
import shutil
from pathlib import Path
import sys

def create_experiment(new_experiment: str, source_experiment: str = "LET_EXP001_2024", config_dir: str = "input"):
    """Create a complete experiment file set by copying from source experiment."""
    
    config_path = Path(config_dir)
    if not config_path.exists():
        print(f"❌ Config directory not found: {config_dir}")
        return False
    
    # List of parameter files that need to be copied
    parameter_files = [
        "canopy_parameters.csv",
        "crop_parameters.csv", 
        "environment_parameters.csv",
        "environmental_control_parameters.csv",
        "experiment_settings.csv",
        "genetic_parameters.csv",
        "genetic_stress_weights.csv",
        "model_constants.csv",
        "nitrogen_parameters.csv",
        "nutrient_solution.csv",
        "phenology_parameters.csv",
        "photosynthesis_parameters.csv",
        "respiration_parameters.csv",
        "root_zone_parameters.csv",
        "senescence_parameters.csv",
        "stress_parameters.csv",
        "system_parameters.csv",
        "system_settings.csv",
        "thermal_requirements.csv",
        "water_parameters.csv",
        "weather.csv"
    ]
    
    print(f"🧪 Creating experiment: {new_experiment}")
    print(f"📋 Copying from: {source_experiment}")
    print("=" * 50)
    
    copied_files = 0
    missing_files = []
    
    for param_file in parameter_files:
        source_file = config_path / f"{source_experiment}_{param_file}"
        target_file = config_path / f"{new_experiment}_{param_file}"
        
        if source_file.exists():
            try:
                shutil.copy2(source_file, target_file)
                print(f"✅ {param_file}")
                copied_files += 1
            except Exception as e:
                print(f"❌ Error copying {param_file}: {e}")
        else:
            print(f"⚠️  Missing source: {source_experiment}_{param_file}")
            missing_files.append(param_file)
    
    print("=" * 50)
    print(f"📊 Results: {copied_files}/{len(parameter_files)} files copied")
    
    if missing_files:
        print(f"⚠️  {len(missing_files)} files were missing from source experiment:")
        for file in missing_files:
            print(f"   - {file}")
        print("💡 You may need to create these files manually or use a different source experiment.")
    
    if copied_files == len(parameter_files):
        print(f"🎉 Experiment {new_experiment} created successfully!")
        print(f"💡 Now you can customize the files and run:")
        print(f"   python3 cropgro_cli.py --experiment {new_experiment} --weather-csv input/weather_2024_spring.csv")
        return True
    else:
        print(f"⚠️  Experiment created with {copied_files}/{len(parameter_files)} files")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Create new experiment file sets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 create_experiment.py LET_EXP003_2024 --from LET_EXP001_2024
  python3 create_experiment.py TOM_EXP001_2024 --from LET_EXP001_2024
  python3 create_experiment.py BAS_EXP001_2025 --from LET_EXP001_2024

Experiment Code Format: CROP_EXP###_YEAR
  CROP: LET (Lettuce), TOM (Tomato), BAS (Basil), SPI (Spinach), KAL (Kale)
  EXP###: EXP001, EXP002, etc.  
  YEAR: 2024, 2025, etc.
        """
    )
    
    parser.add_argument('experiment_code', help='New experiment code (e.g., LET_EXP003_2024)')
    parser.add_argument('--from', dest='source_experiment', default='LET_EXP001_2024',
                       help='Source experiment to copy from (default: LET_EXP001_2024)')
    parser.add_argument('--config-dir', default='input',
                       help='Configuration directory (default: input)')
    
    args = parser.parse_args()
    
    # Validate experiment code format
    parts = args.experiment_code.split('_')
    if len(parts) != 3:
        print("❌ Invalid experiment code format!")
        print("💡 Use format: CROP_EXP###_YEAR (e.g., LET_EXP001_2024)")
        sys.exit(1)
    
    crop_code, exp_code, year = parts
    if not exp_code.startswith('EXP'):
        print("❌ Experiment code must start with 'EXP' (e.g., EXP001)")
        sys.exit(1)
    
    success = create_experiment(args.experiment_code, args.source_experiment, args.config_dir)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()