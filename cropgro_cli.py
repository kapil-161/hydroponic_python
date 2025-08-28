#!/usr/bin/env python3
"""
CROPGRO Hydroponic Simulator - Command Line Interface
Professional DSSAT-style crop modeling system
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

# Import CROPGRO system
from src.cropgro_hydroponic_simulator import CROPGROHydroponicSimulator
from src.data.hydroponic_system import DefaultConfigurations, HydroInputData, WeatherData
from src.utils.weather_generator import WeatherGenerator


def to_serializable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        import numpy as np
        if isinstance(value, (np.floating, np.integer)):
            return float(value)
    except Exception:
        pass
    return value


def daily_result_to_dict(dr: Any) -> Dict[str, Any]:
    data = {}
    for k, v in vars(dr).items():
        if isinstance(v, dict):
            data[k] = {sk: to_serializable(sv) for sk, sv in v.items()}
        elif isinstance(v, list):
            data[k] = [to_serializable(it) for it in v]
        else:
            data[k] = to_serializable(v)
    return data


def run_simulation(days: int, cultivar_id: str, system_type: str, print_daily: bool, treatment_id: str = None, input_dir: str = 'input') -> Any:
    print("🌱 CROPGRO Hydroponic Simulator - CLI Version")
    print("=" * 50)

    # Use default configurations as a base
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    if system_type and system_type.upper() != 'NFT':
        # Only type affects the engine; keep other fields
        system_config.system_type = system_type.upper()
    
    # Load parameters from CSV files - NO FALLBACKS TO HARDCODED VALUES
    try:
        import pandas as pd
        
        # Simple direct parameter loading from specific files
        params_loaded = []
        
        # 1. Load environmental control parameters comprehensively
        env_control_file = f'{input_dir}/LET_EXP001_2024_environmental_control_parameters.csv'
        if Path(env_control_file).exists():
            try:
                df = pd.read_csv(env_control_file)
                # Store all environmental control parameters dynamically
                env_control_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = float(row['value'])
                    env_control_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                    
                    # Also set key system_config values for backward compatibility
                    if param_name == 'co2_setpoint':
                        system_config.controlled_co2 = param_value
                        print(f"✓ CO2 loaded: {param_value} ppm")
                    elif param_name == 'target_vpd':
                        print(f"✓ Target VPD loaded: {param_value} kPa")
                
                # Add all environmental control parameters to system_config
                system_config.environmental_control_parameters = env_control_params
                print(f"✓ Environmental control parameters loaded: {len(env_control_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load environmental control: {e}")
        
        # 2. Try to load EC from environment parameters (min_ec, max_ec)
        # Using min_ec as the baseline EC value
        try:
            df = pd.read_csv(f'{input_dir}/LET_EXP001_2024_environment_parameters.csv')
            for _, row in df.iterrows():
                if row['parameter_name'] == 'min_ec':
                    system_config.solution_ec = float(row['value'])
                    params_loaded.append(f"EC={row['value']}")
                    print(f"✓ EC loaded: {row['value']} dS/m (from min_ec)")
        except Exception as e:
            print(f"⚠️  Could not load EC: {e}")
        
        # 3. Try to load pH from system settings
        system_file = f'{input_dir}/LET_EXP001_2024_system_settings.csv'
        if Path(system_file).exists():
            try:
                df = pd.read_csv(system_file)
                for _, row in df.iterrows():
                    if row['setting_name'] == 'initial_ph':
                        system_config.solution_ph = float(row['value'])
                        params_loaded.append(f"pH={row['value']}")
                        print(f"✓ pH loaded: {row['value']}")
            except Exception as e:
                print(f"⚠️  Could not load pH: {e}")
        
        # 4. Load all environment parameters comprehensively
        env_file = f'{input_dir}/LET_EXP001_2024_environment_parameters.csv'
        if Path(env_file).exists():
            try:
                df = pd.read_csv(env_file)
                # Store all environment parameters dynamically
                env_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = float(row['value'])
                    env_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                    
                    # Also set key system_config values for backward compatibility
                    if param_name == 'optimal_temperature':
                        system_config.temperature = param_value
                        print(f"✓ Temperature loaded: {param_value}°C")
                    elif param_name == 'min_humidity':
                        system_config.humidity = param_value
                        print(f"✓ Humidity loaded: {param_value}%")
                    elif param_name == 'optimal_light_intensity':
                        system_config.solar_radiation = param_value
                        print(f"✓ Light loaded: {param_value} MJ/m²/day")
                
                # Add all environment parameters to system_config
                system_config.environment_parameters = env_params
                print(f"✓ Environment parameters loaded: {len(env_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load environment: {e}")
        
        # 5. Load canopy parameters
        canopy_file = f'{input_dir}/LET_EXP001_2024_canopy_parameters.csv'
        if Path(canopy_file).exists():
            try:
                df = pd.read_csv(canopy_file)
                # Store all canopy parameters dynamically
                canopy_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = float(row['value'])
                    canopy_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add canopy parameters to system_config
                system_config.canopy_parameters = canopy_params
                print(f"✓ Canopy parameters loaded: {len(canopy_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load canopy parameters: {e}")

        # 6. Load crop parameters
        crop_file = f'{input_dir}/LET_EXP001_2024_crop_parameters.csv'
        if Path(crop_file).exists():
            try:
                df = pd.read_csv(crop_file)
                # Store all crop parameters dynamically
                crop_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    crop_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add crop parameters to system_config
                system_config.crop_parameters = crop_params
                print(f"✓ Crop parameters loaded: {len(crop_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load crop parameters: {e}")

        # 7. Load genetic parameters
        genetic_file = f'{input_dir}/LET_EXP001_2024_genetic_parameters.csv'
        if Path(genetic_file).exists():
            try:
                df = pd.read_csv(genetic_file)
                # Store all genetic parameters dynamically
                genetic_params = {}
                for _, row in df.iterrows():
                    if row['cultivar_id'] == cultivar_id:  # Filter by current cultivar
                        param_name = row['parameter']
                        param_value = row['value']
                        # Convert to appropriate type
                        try:
                            if param_value != param_value:  # Check for NaN
                                param_value = ""
                            elif str(param_value).replace('.', '').isdigit():
                                param_value = float(param_value)
                        except:
                            pass  # Keep as string
                        genetic_params[param_name] = param_value
                        params_loaded.append(f"{param_name}={param_value}")
                
                # Add genetic parameters to system_config
                system_config.genetic_parameters = genetic_params
                print(f"✓ Genetic parameters loaded: {len(genetic_params)} parameters for {cultivar_id}")
            except Exception as e:
                print(f"⚠️  Could not load genetic parameters: {e}")

        # 8. Load photosynthesis parameters
        photosynthesis_file = f'{input_dir}/LET_EXP001_2024_photosynthesis_parameters.csv'
        if Path(photosynthesis_file).exists():
            try:
                df = pd.read_csv(photosynthesis_file)
                # Store all photosynthesis parameters dynamically
                photosynthesis_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    photosynthesis_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add photosynthesis parameters to system_config
                system_config.photosynthesis_parameters = photosynthesis_params
                print(f"✓ Photosynthesis parameters loaded: {len(photosynthesis_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load photosynthesis parameters: {e}")

        # 9. Load nitrogen parameters
        nitrogen_file = f'{input_dir}/LET_EXP001_2024_nitrogen_parameters.csv'
        if Path(nitrogen_file).exists():
            try:
                df = pd.read_csv(nitrogen_file)
                # Store all nitrogen parameters dynamically
                nitrogen_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    nitrogen_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add nitrogen parameters to system_config
                system_config.nitrogen_parameters = nitrogen_params
                print(f"✓ Nitrogen parameters loaded: {len(nitrogen_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load nitrogen parameters: {e}")

        # 10. Load stress parameters
        stress_file = f'{input_dir}/LET_EXP001_2024_stress_parameters.csv'
        if Path(stress_file).exists():
            try:
                df = pd.read_csv(stress_file)
                # Store all stress parameters dynamically
                stress_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    stress_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add stress parameters to system_config
                system_config.stress_parameters = stress_params
                print(f"✓ Stress parameters loaded: {len(stress_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load stress parameters: {e}")

        # 11. Load respiration parameters
        respiration_file = f'{input_dir}/LET_EXP001_2024_respiration_parameters.csv'
        if Path(respiration_file).exists():
            try:
                df = pd.read_csv(respiration_file)
                # Store all respiration parameters dynamically
                respiration_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    respiration_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add respiration parameters to system_config
                system_config.respiration_parameters = respiration_params
                print(f"✓ Respiration parameters loaded: {len(respiration_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load respiration parameters: {e}")

        # 12. Load phenology parameters
        phenology_file = f'{input_dir}/LET_EXP001_2024_phenology_parameters.csv'
        if Path(phenology_file).exists():
            try:
                df = pd.read_csv(phenology_file)
                # Store all phenology parameters dynamically
                phenology_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).lower() in ['true', 'false']:
                            param_value = str(param_value).lower() == 'true'
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    phenology_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add phenology parameters to system_config
                system_config.phenology_parameters = phenology_params
                print(f"✓ Phenology parameters loaded: {len(phenology_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load phenology parameters: {e}")

        # 13. Load senescence parameters
        senescence_file = f'{input_dir}/LET_EXP001_2024_senescence_parameters.csv'
        if Path(senescence_file).exists():
            try:
                df = pd.read_csv(senescence_file)
                # Store all senescence parameters dynamically
                senescence_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    senescence_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add senescence parameters to system_config
                system_config.senescence_parameters = senescence_params
                print(f"✓ Senescence parameters loaded: {len(senescence_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load senescence parameters: {e}")

        # 14. Load root zone parameters
        root_zone_file = f'{input_dir}/LET_EXP001_2024_root_zone_parameters.csv'
        if Path(root_zone_file).exists():
            try:
                df = pd.read_csv(root_zone_file)
                # Store all root zone parameters dynamically
                root_zone_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    root_zone_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add root zone parameters to system_config
                system_config.root_zone_parameters = root_zone_params
                print(f"✓ Root zone parameters loaded: {len(root_zone_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load root zone parameters: {e}")

        # 15. Load system parameters
        system_params_file = f'{input_dir}/LET_EXP001_2024_system_parameters.csv'
        if Path(system_params_file).exists():
            try:
                df = pd.read_csv(system_params_file)
                # Store all system parameters dynamically
                system_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            param_value = ""
                        elif str(param_value).replace('.', '').isdigit():
                            param_value = float(param_value)
                    except:
                        pass  # Keep as string
                    system_params[param_name] = param_value
                    params_loaded.append(f"{param_name}={param_value}")
                
                # Add system parameters to system_config
                system_config.system_parameters = system_params
                print(f"✓ System parameters loaded: {len(system_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load system parameters: {e}")

        # 16. Load water parameters
        water_params_file = f'{input_dir}/LET_EXP001_2024_water_parameters.csv'
        if Path(water_params_file).exists():
            try:
                df = pd.read_csv(water_params_file)
                # Store all water parameters dynamically
                water_params = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            continue
                        water_params[param_name] = float(param_value)
                        params_loaded.append(f"{param_name}={float(param_value)}")
                    except (ValueError, TypeError):
                        try:
                            water_params[param_name] = str(param_value)
                            params_loaded.append(f"{param_name}={param_value}")
                        except Exception:
                            continue
                
                # Add water parameters to system_config
                system_config.water_parameters = water_params
                print(f"✓ Water parameters loaded: {len(water_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load water parameters: {e}")

        # 17. Load thermal requirements
        thermal_params_file = f'{input_dir}/LET_EXP001_2024_thermal_requirements.csv'
        if Path(thermal_params_file).exists():
            try:
                df = pd.read_csv(thermal_params_file)
                # Store all thermal requirement parameters dynamically
                thermal_params = {}
                for _, row in df.iterrows():
                    stage_transition = row['stage_transition']
                    thermal_time = row['thermal_time_gdd']
                    # Convert to appropriate type
                    try:
                        if thermal_time != thermal_time:  # Check for NaN
                            continue
                        thermal_params[stage_transition] = float(thermal_time)
                        params_loaded.append(f"{stage_transition}={float(thermal_time)}")
                    except (ValueError, TypeError):
                        try:
                            thermal_params[stage_transition] = str(thermal_time)
                            params_loaded.append(f"{stage_transition}={thermal_time}")
                        except Exception:
                            continue
                
                # Add thermal requirements to system_config
                system_config.thermal_requirements = thermal_params
                print(f"✓ Thermal requirements loaded: {len(thermal_params)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load thermal requirements: {e}")

        # 18. Load model constants
        model_constants_file = f'{input_dir}/LET_EXP001_2024_model_constants.csv'
        if Path(model_constants_file).exists():
            try:
                df = pd.read_csv(model_constants_file)
                # Store all model constants dynamically
                model_constants = {}
                for _, row in df.iterrows():
                    constant_name = row['constant_name']
                    constant_value = row['value']
                    # Convert to appropriate type
                    try:
                        if constant_value != constant_value:  # Check for NaN
                            continue
                        model_constants[constant_name] = float(constant_value)
                        params_loaded.append(f"{constant_name}={float(constant_value)}")
                    except (ValueError, TypeError):
                        try:
                            model_constants[constant_name] = str(constant_value)
                            params_loaded.append(f"{constant_name}={constant_value}")
                        except Exception:
                            continue
                
                # Add model constants to system_config
                system_config.model_constants = model_constants
                print(f"✓ Model constants loaded: {len(model_constants)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load model constants: {e}")

        # 19. Load nutrient solution parameters
        nutrient_solution_file = f'{input_dir}/LET_EXP001_2024_nutrient_solution.csv'
        if Path(nutrient_solution_file).exists():
            try:
                df = pd.read_csv(nutrient_solution_file)
                # Store all nutrient solution parameters dynamically
                nutrient_solution = {}
                for _, row in df.iterrows():
                    nutrient_name = row['nutrient_name']
                    nutrient_symbol = row['symbol']
                    # Store each nutrient with its parameters
                    nutrient_solution[nutrient_symbol] = {
                        'name': nutrient_name,
                        'initial_ppm': float(row['initial_ppm']),
                        'optimal_ppm': float(row['optimal_ppm']),
                        'minimum_ppm': float(row['minimum_ppm']),
                        'max_ppm': float(row['max_ppm']),
                        'description': row['description']
                    }
                    # Add to params_loaded for counting
                    for param in ['initial_ppm', 'optimal_ppm', 'minimum_ppm', 'max_ppm']:
                        params_loaded.append(f"{nutrient_symbol}_{param}={row[param]}")
                
                # Add nutrient solution to system_config
                system_config.nutrient_solution = nutrient_solution
                print(f"✓ Nutrient solution loaded: {len(nutrient_solution) * 4} parameters for {len(nutrient_solution)} nutrients")
            except Exception as e:
                print(f"⚠️  Could not load nutrient solution: {e}")

        # 20. Load genetic stress weights
        genetic_stress_file = f'{input_dir}/LET_EXP001_2024_genetic_stress_weights.csv'
        if Path(genetic_stress_file).exists():
            try:
                df = pd.read_csv(genetic_stress_file)
                # Store all genetic stress weight parameters dynamically
                genetic_stress_weights = {}
                for _, row in df.iterrows():
                    param_name = row['parameter_name']
                    param_value = row['value']
                    # Convert to appropriate type
                    try:
                        if param_value != param_value:  # Check for NaN
                            continue
                        genetic_stress_weights[param_name] = float(param_value)
                        params_loaded.append(f"{param_name}={float(param_value)}")
                    except (ValueError, TypeError):
                        try:
                            genetic_stress_weights[param_name] = str(param_value)
                            params_loaded.append(f"{param_name}={param_value}")
                        except Exception:
                            continue
                
                # Add genetic stress weights to system_config
                system_config.genetic_stress_weights = genetic_stress_weights
                print(f"✓ Genetic stress weights loaded: {len(genetic_stress_weights)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load genetic stress weights: {e}")

        # 21. Load system settings
        system_settings_file = f'{input_dir}/LET_EXP001_2024_system_settings.csv'
        if Path(system_settings_file).exists():
            try:
                df = pd.read_csv(system_settings_file)
                # Store all system settings dynamically
                system_settings = {}
                for _, row in df.iterrows():
                    setting_name = row['setting_name']
                    setting_value = row['value']
                    # Convert to appropriate type
                    try:
                        if pd.isna(setting_value):  # Check for NaN
                            continue
                        # Try to convert to float first
                        try:
                            system_settings[setting_name] = float(setting_value)
                            params_loaded.append(f"{setting_name}={float(setting_value)}")
                        except (ValueError, TypeError):
                            # Keep as string if not numeric
                            system_settings[setting_name] = str(setting_value)
                            params_loaded.append(f"{setting_name}={setting_value}")
                    except Exception:
                        continue
                
                # Add system settings to system_config
                system_config.system_settings = system_settings
                print(f"✓ System settings loaded: {len(system_settings)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load system settings: {e}")

        # 22. Load experiment settings
        experiment_settings_file = f'{input_dir}/LET_EXP001_2024_experiment_settings.csv'
        if Path(experiment_settings_file).exists():
            try:
                df = pd.read_csv(experiment_settings_file)
                # Store all experiment settings dynamically
                experiment_settings = {}
                for _, row in df.iterrows():
                    setting_name = row['setting_name']
                    setting_value = row['value']
                    # Convert to appropriate type
                    try:
                        if pd.isna(setting_value):  # Check for NaN
                            continue
                        # Handle boolean values
                        if isinstance(setting_value, str) and setting_value.lower() in ['true', 'false']:
                            experiment_settings[setting_name] = setting_value.lower() == 'true'
                            params_loaded.append(f"{setting_name}={setting_value}")
                        else:
                            # Try to convert to float first
                            try:
                                experiment_settings[setting_name] = float(setting_value)
                                params_loaded.append(f"{setting_name}={float(setting_value)}")
                            except (ValueError, TypeError):
                                # Keep as string if not numeric
                                experiment_settings[setting_name] = str(setting_value)
                                params_loaded.append(f"{setting_name}={setting_value}")
                    except Exception:
                        continue
                
                # Add experiment settings to system_config
                system_config.experiment_settings = experiment_settings
                print(f"✓ Experiment settings loaded: {len(experiment_settings)} parameters")
            except Exception as e:
                print(f"⚠️  Could not load experiment settings: {e}")

        if params_loaded:
            print(f"📊 Successfully loaded {len(params_loaded)} parameters from CSV files")
        else:
            print("❌ NO parameters loaded from CSV - check file paths and contents")
            
    except Exception as e:
        print(f"❌ CSV loading failed: {e}")
        import traceback
        traceback.print_exc()

    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Update nutrient_params with dynamic nutrient solution values from CSV
    if hasattr(system_config, 'nutrient_solution'):
        from src.models.nutrient_models import NutrientParams
        for nutrient_id, nutrient_data in system_config.nutrient_solution.items():
            if nutrient_id in nutrient_params:
                # Update the existing nutrient parameter with CSV values
                original_param = nutrient_params[nutrient_id]
                nutrient_params[nutrient_id] = NutrientParams(
                    nutrient_id=original_param.nutrient_id,
                    nutrient_name=original_param.nutrient_name,
                    chemical_form=original_param.chemical_form,
                    initial_conc=nutrient_data['initial_ppm'],  # Use CSV value
                    recharge_conc=nutrient_data['optimal_ppm'], # Use CSV value
                    uptake_conc=original_param.uptake_conc,
                    sensitivity_coeff=original_param.sensitivity_coeff,
                    is_nutritive=original_param.is_nutritive,
                    min_conc=nutrient_data['minimum_ppm'],     # Use CSV value
                    max_conc=nutrient_data['max_ppm'],         # Use CSV value
                    charge=original_param.charge,
                    molar_mass=original_param.molar_mass
                )

    # Update system_config with dynamic system settings from CSV
    if hasattr(system_config, 'system_settings'):
        system_settings = system_config.system_settings
        # Map CSV parameter names to system_config attributes
        setting_mapping = {
            'system_type': 'system_type',
            'tank_volume': 'tank_volume',
            'system_area': 'system_area', 
            'number_of_plants': 'n_plants',
            'initial_ph': 'initial_ph',
            'initial_ec': 'initial_ec',
            'target_temperature': 'target_temperature',
            'target_humidity': 'target_humidity',
            'co2_concentration': 'co2_setpoint'
        }
        
        for csv_param, config_attr in setting_mapping.items():
            if csv_param in system_settings:
                setattr(system_config, config_attr, system_settings[csv_param])
                print(f"✓ Updated {config_attr} = {system_settings[csv_param]} from CSV")

    # 23. Load weather data
    weather_data_file = f'{input_dir}/LET_EXP001_2024_weather.csv'
    weather_list = []
    if Path(weather_data_file).exists():
        try:
            df = pd.read_csv(weather_data_file)
            print(f"✓ Weather data loaded: {len(df)} days")
            
            # Convert weather data to WeatherData objects
            for _, row in df.iterrows():
                weather_day = WeatherData(
                    date=row['date'],
                    temp_avg=row['temp_avg'],
                    temp_min=row['temp_min'],
                    temp_max=row['temp_max'],
                    solar_radiation=row['solar_radiation'],
                    rel_humidity=row['rel_humidity'],
                    wind_speed=row['wind_speed'],
                    rainfall=row['rainfall']
                )
                weather_list.append(weather_day)
                
            # Store weather data in system_config for access
            system_config.weather_data = weather_list
            params_loaded.append(f"weather_days={len(weather_list)}")
            
        except Exception as e:
            print(f"⚠️  Could not load weather data: {e}")
            # Fallback to generated weather data
            generator = WeatherGenerator()
            start_date = datetime.now()
            weather_list = generator.generate_weather_series(
                start_date=start_date,
                days=days
            )
    else:
        # Generate weather data as fallback
        generator = WeatherGenerator()
        start_date = datetime.now()
        weather_list = generator.generate_weather_series(
            start_date=start_date,
            days=days
        )

    # Create input data
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_list,
        nutrient_params=nutrient_params,
        simulation_days=days
    )

    # Create and run simulator
    simulator = CROPGROHydroponicSimulator(
        cultivar_id=cultivar_id,
        system_type=system_type.upper() if system_type else 'NFT',
        system_config=system_config
    )

    print(f"Starting simulation until harvest maturity...")
    print(f"Cultivar: {simulator.cultivar_profile.cultivar_name}")
    print(f"System: {system_config.system_type}")

    # treatment_id parameter is passed directly to the function
    results = simulator.run_simulation(input_data, max_days=days, target_maturity='harvest', treatment_id=treatment_id)

    if print_daily:
        for dr in results.daily_results:
            print(simulator.display_detailed_results(dr))

    print(f"✅ Simulation completed successfully!")
    print(f"Duration: {len(results.daily_results)} days")
    print(f"Final stage: {getattr(results.daily_results[-1], 'growth_stage', 'Unknown')}")

    return results


def main():
    parser = argparse.ArgumentParser(description="CROPGRO Hydroponic Simulator CLI")
    parser.add_argument('--days', type=int, default=120, help='Max simulation days')
    parser.add_argument('--cultivar', type=str, default='HYDRO_001', help='Cultivar ID')
    parser.add_argument('--system', type=str, default='NFT', choices=['NFT', 'DWC', 'AEROPONICS'], help='Hydroponic system type')
    parser.add_argument('--output-csv', type=str, help='Path to write CSV of daily results')
    parser.add_argument('--output-json', type=str, help='Path to write JSON with all daily details')
    parser.add_argument('--daily-csv', action='store_true', help='Automatically save daily CSV with timestamp in outputs/ directory')
    parser.add_argument('--print-daily', action='store_true', help='Print detailed per-day results to stdout')
    parser.add_argument('--print-summary', action='store_true', help='Print summary stats to stdout')
    
    # Treatment identifier for batch processing
    parser.add_argument('--treatment-id', type=str, help='Treatment identifier (e.g., T01, T02)')
    parser.add_argument('--input-dir', type=str, default='input', help='Input directory containing CSV configuration files')

    args = parser.parse_args()

    try:
        results = run_simulation(args.days, args.cultivar, args.system, args.print_daily, args.treatment_id, args.input_dir)

        # Output CSV via DataFrame (curated columns)
        if args.output_csv:
            df = results.to_dataframe()
            out_path = Path(args.output_csv)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(out_path, index=False)
            print(f"Saved CSV: {out_path}")

        # Auto-generate daily CSV with timestamp
        if args.daily_csv:
            df = results.to_dataframe()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"hydroponic_daily_results_{args.cultivar}_{args.system}_{timestamp}.csv"
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)
            out_path = outputs_dir / filename
            df.to_csv(out_path, index=False)
            print(f"Saved daily CSV: {out_path}")

        # Output full JSON with all attributes per day
        if args.output_json:
            out = {
                'metadata': getattr(results, 'metadata', {}),
                'summary_stats': results.summary_stats,
                'daily_results': [daily_result_to_dict(dr) for dr in results.daily_results],
            }
            out_path = Path(args.output_json)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'w') as f:
                json.dump(out, f, indent=2)
            print(f"Saved JSON: {out_path}")

        if args.print_summary:
            print("\nSummary stats:")
            for k, v in results.summary_stats.items():
                print(f"- {k}: {v}")

        print(f"\n🎯 Simulation completed successfully!")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()