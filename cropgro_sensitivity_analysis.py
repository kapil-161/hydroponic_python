#!/usr/bin/env python3
"""
CROPGRO Hydroponic Simulator - Parameter Sensitivity Analysis
Professional DSSAT-style crop modeling system with sensitivity analysis
"""

import sys
import json
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple
from copy import deepcopy

# Import CROPGRO system
from src.cropgro_hydroponic_simulator import CROPGROHydroponicSimulator
from src.data.hydroponic_system import DefaultConfigurations, HydroInputData, WeatherData


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


def load_master_parameters(file_path: str) -> Dict[str, Any]:
    """Load parameters from master CSV file and return as dictionary"""
    df = pd.read_csv(file_path, comment='#')
    parameters = {}
    
    for _, row in df.iterrows():
        param_name = row['parameter_name']
        param_value = row['value']
        category = row.get('category', 'general')
        
        # Convert to appropriate type
        try:
            if pd.isna(param_value):
                continue
            elif str(param_value).lower() in ['true', 'false']:
                param_value = str(param_value).lower() == 'true'
            elif str(param_value).replace('.', '').replace('-', '').isdigit():
                param_value = float(param_value)
                if param_value.is_integer() and any(keyword in param_name.lower() for keyword in ['number', 'count', 'layers', 'plants']):
                    param_value = int(param_value)
            elif str(param_value).startswith('{') and str(param_value).endswith('}'):
                try:
                    import ast
                    param_value = ast.literal_eval(str(param_value))
                except (ValueError, SyntaxError):
                    pass
        except (ValueError, TypeError):
            pass
            
        parameters[param_name] = {
            'value': param_value,
            'category': category,
            'original_value': param_value
        }
    
    return parameters


def save_modified_parameters(parameters: Dict[str, Any], output_file: str):
    """Save modified parameters back to CSV format"""
    rows = []
    for param_name, param_data in parameters.items():
        rows.append({
            'parameter_name': param_name,
            'value': param_data['value'],
            'category': param_data['category']
        })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)


def run_single_simulation(days: int, cultivar_id: str, system_type: str, treatment_id: str, input_dir: str) -> Tuple[Any, float]:
    """Run a single simulation and return results with final biomass"""
    
    # Use default configurations as a base
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    if system_type and system_type.upper() != 'NFT':
        system_config.system_type = system_type.upper()
    
    # Load parameters from master file
    file_prefix = treatment_id if treatment_id else cultivar_id
    master_file = f'{input_dir}/{file_prefix}_master_parameters.csv'
    
    if not Path(master_file).exists():
        raise FileNotFoundError(f"Master parameters file not found: {master_file}")
    
    try:
        df = pd.read_csv(master_file, comment='#')
        parameter_categories = {}
        
        for _, row in df.iterrows():
            param_name = row['parameter_name']
            param_value = row['value']
            category = row.get('category', 'general')
            
            # Convert to appropriate type
            try:
                if pd.isna(param_value):
                    continue
                elif str(param_value).lower() in ['true', 'false']:
                    param_value = str(param_value).lower() == 'true'
                elif str(param_value).replace('.', '').replace('-', '').isdigit():
                    param_value = float(param_value)
                    if param_value.is_integer() and any(keyword in param_name.lower() for keyword in ['number', 'count', 'layers', 'plants']):
                        param_value = int(param_value)
                elif str(param_value).startswith('{') and str(param_value).endswith('}'):
                    try:
                        import ast
                        param_value = ast.literal_eval(str(param_value))
                    except (ValueError, SyntaxError):
                        pass
            except (ValueError, TypeError):
                pass
            
            if category not in parameter_categories:
                parameter_categories[category] = {}
            parameter_categories[category][param_name] = param_value
        
        # Assign categories to system_config
        for category, params in parameter_categories.items():
            if pd.isna(category) or not isinstance(category, str) or not category.replace('_', '').isalnum():
                continue
            setattr(system_config, f"{category}_parameters", params)
            setattr(system_config, category, params)
        
        # Set key system_config values for backward compatibility
        if 'environment' in parameter_categories:
            env_params = parameter_categories['environment']
            if 'environment_optimal_temperature' in env_params:
                system_config.temperature = env_params['environment_optimal_temperature']
            if 'min_humidity' in env_params:
                system_config.humidity = env_params['min_humidity']
            if 'optimal_light_intensity' in env_params:
                system_config.solar_radiation = env_params['optimal_light_intensity']
            if 'min_ec' in env_params:
                system_config.solution_ec = env_params['min_ec']
            if 'target_co2' in env_params:
                system_config.controlled_co2 = env_params['target_co2']
        
        if 'system' in parameter_categories:
            sys_params = parameter_categories['system']
            if 'tank_volume' in sys_params:
                system_config.tank_volume = sys_params['tank_volume']
            if 'system_area' in sys_params:
                system_config.system_area = sys_params['system_area']
            if 'number_of_plants' in sys_params:
                system_config.n_plants = sys_params['number_of_plants']
                
    except Exception as e:
        raise Exception(f"Error loading master parameters file: {e}")

    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Load all nutrient-related parameters from CSV (FIXED: removes buggy conditional)
    # Load from nutrient_concentrations, nutrient_management, and nutrient_parameters categories
    nutrient_categories = ['nutrient_concentrations', 'nutrient_management', 'nutrient_parameters']
    
    for category in nutrient_categories:
        if hasattr(system_config, category):
            category_data = getattr(system_config, category)
            if isinstance(category_data, dict):
                # Add all parameters from this category to nutrient_params
                nutrient_params.update(category_data)

    # Load weather data
    weather_data_file = f'{input_dir}/{file_prefix}_weather.csv'
    weather_list = []
    
    if not Path(weather_data_file).exists():
        raise FileNotFoundError(f"Weather data file not found: {weather_data_file}")
    
    try:
        df = pd.read_csv(weather_data_file)
        required_columns = ['date', 'temp_avg', 'temp_min', 'temp_max', 'solar_radiation', 'rel_humidity', 'wind_speed', 'rainfall']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Weather CSV missing required columns: {missing_columns}")
        
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
            
        system_config.weather_data = weather_list
        
        # VALIDATE: Weather data dates must match experiment dates
        # Get experiment dates from parameters
        transplanting_date_str = None
        
        # Extract dates from system config experiment settings
        if hasattr(system_config, 'experiment_settings'):
            experiment_settings = system_config.experiment_settings
            transplanting_date_str = experiment_settings.get('transplanting_date')
        
        if transplanting_date_str and weather_list:
            from datetime import datetime
            try:
                transplanting_date = datetime.strptime(transplanting_date_str, '%Y-%m-%d')
                
                # Get weather data date range
                weather_dates = []
                for weather_day in weather_list:
                    weather_date = datetime.strptime(weather_day.date, '%Y-%m-%d')
                    weather_dates.append(weather_date)
                
                weather_start = min(weather_dates)
                weather_end = max(weather_dates)
                
                # Check if transplanting date falls within weather data range
                if not (weather_start <= transplanting_date <= weather_end):
                    raise ValueError(f"Weather data dates don't match experiment schedule! "
                                   f"Transplanting date: {transplanting_date_str}, "
                                   f"Weather range: {weather_start.strftime('%Y-%m-%d')} to {weather_end.strftime('%Y-%m-%d')}")
                    
            except ValueError as e:
                raise ValueError(f"Date validation error: {e}")
        
    except Exception as e:
        raise Exception(f"Could not load weather data from {weather_data_file}: {e}")

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

    # Run simulation
    results = simulator.run_simulation(input_data, max_days=days, target_maturity='harvest', treatment_id=treatment_id)
    
    # Extract final biomass
    final_result = results.daily_results[-1]
    final_biomass = getattr(final_result, 'total_biomass', 0.0)
    
    return results, final_biomass


def get_allocation_groups():
    """Define allocation parameter groups that must sum to 1.0"""
    return {
        'vegetative_biomass': [
            'vegetative_leaf_allocation',
            'vegetative_stem_allocation', 
            'vegetative_root_allocation'
        ],
        'reproductive_biomass': [
            'reproductive_leaf_allocation',
            'reproductive_stem_allocation',
            'reproductive_root_allocation'
        ],
        'vegetative_nitrogen': [
            'allocation_coefficients_vegetative_leaves',
            'allocation_coefficients_vegetative_stems',
            'allocation_coefficients_vegetative_roots'
        ],
        'reproductive_nitrogen': [
            'allocation_coefficients_reproductive_leaves',
            'allocation_coefficients_reproductive_stems', 
            'allocation_coefficients_reproductive_roots',
            'allocation_coefficients_reproductive_reproductive'
        ]
    }


def get_parameter_bounds():
    """Define reasonable bounds for weather and environmental parameters"""
    return {
        # Temperature parameters (Celsius)
        'environment_optimal_temperature': (10, 35),
        'optimal_temperature_max': (20, 45),
        'optimal_temperature_min': (5, 25),
        'day_temp': (15, 35),
        'night_temp': (10, 30),
        'base_temperature': (0, 15),
        'maximum_temperature': (25, 50),
        'heat_lethal_temperature': (35, 50),
        'cold_lethal_temperature': (0, 10),
        
        # Humidity parameters (%)
        'min_humidity': (30, 90),
        'max_humidity': (50, 95),
        'target_humidity': (40, 90),
        
        # EC parameters (dS/m)
        'min_ec': (0.5, 3.0),
        'max_ec': (1.5, 4.0),
        'optimal_ec': (1.0, 3.0),
        
        # Light parameters (MJ/m²/day)
        'optimal_light_intensity': (10, 30),
        'max_solar_radiation': (15, 35),
        
        # VPD parameters (kPa)
        'optimal_vpd_min': (0.2, 1.5),
        'optimal_vpd_max': (0.8, 2.5),
        'target_vpd': (0.5, 2.0),
        
        # Wind speed (m/s)
        'wind_speed_2m': (0.5, 10.0),
        
        # CO2 (ppm)
        'target_co2': (300, 1500),
        'co2_concentration': (350, 1200)
    }


def apply_proportional_scaling(original_params: Dict[str, Any], target_param: str, change_percent: float) -> Dict[str, Any]:
    """Apply proportional scaling to allocation fractions and bounds checking for weather parameters
    
    Args:
        original_params: Dictionary of original parameters
        target_param: Parameter to modify
        change_percent: Percentage change (can be positive or negative)
    """
    allocation_groups = get_allocation_groups()
    parameter_bounds = get_parameter_bounds()
    modified_params = deepcopy(original_params)
    
    # Find which allocation group contains the target parameter
    target_group = None
    for group_name, param_list in allocation_groups.items():
        if target_param in param_list:
            target_group = param_list
            break
    
    if target_group is None:
        # Not an allocation parameter, modify normally with bounds checking
        original_value = original_params[target_param]['value']
        new_value = original_value * (1 + change_percent / 100.0)
        
        # Check bounds for weather/environmental parameters
        if target_param in parameter_bounds:
            min_bound, max_bound = parameter_bounds[target_param]
            if new_value < min_bound or new_value > max_bound:
                # Skip parameter if it would exceed realistic bounds
                return None
        
        # Check for negative values in parameters that should be positive
        if new_value < 0 and not any(word in target_param.lower() for word in ['min', 'offset', 'base', 'threshold']):
            return None
        
        modified_params[target_param]['value'] = new_value
        return modified_params
    
    # Handle allocation parameters with proportional scaling
    # Get current values for the group
    group_values = {}
    total_original = 0
    
    for param in target_group:
        if param in original_params:
            group_values[param] = original_params[param]['value']
            total_original += group_values[param]
    
    if total_original == 0:
        return modified_params  # Avoid division by zero
    
    # Modify target parameter
    original_target = group_values[target_param]
    new_target = original_target * (1 + change_percent / 100.0)
    
    # Check if new target value is valid (non-negative and not too large)
    if new_target < 0 or new_target > 1.0:
        return None
    
    # Calculate scaling factor for other parameters to maintain sum = 1.0
    remaining_original = total_original - original_target
    remaining_target = 1.0 - new_target
    
    if remaining_original <= 0 or remaining_target <= 0:
        # Can't scale proportionally, skip this parameter
        return None
    
    scaling_factor = remaining_target / remaining_original
    
    # Check if scaling would create negative values
    for param in target_group:
        if param != target_param and param in group_values:
            scaled_value = group_values[param] * scaling_factor
            if scaled_value < 0:
                return None
    
    # Apply changes
    modified_params[target_param]['value'] = new_target
    
    for param in target_group:
        if param != target_param and param in group_values:
            modified_params[param]['value'] = group_values[param] * scaling_factor
    
    return modified_params


def run_sensitivity_analysis(days: int, cultivar_id: str, system_type: str, treatment_id: str, input_dir: str, change_percent: float = 10.0):
    """Run two-sided sensitivity analysis by testing both increases and decreases for each parameter"""
    
    print("🔬 CROPGRO Two-Sided Parameter Sensitivity Analysis")
    print("=" * 70)
    
    # Load original parameters
    file_prefix = treatment_id if treatment_id else cultivar_id
    master_file = f'{input_dir}/{file_prefix}_master_parameters.csv'
    
    if not Path(master_file).exists():
        print(f"❌ Master parameters file not found: {master_file}")
        return
    
    original_params = load_master_parameters(master_file)
    
    # Run baseline simulation
    print(f"🏃 Running baseline simulation...")
    try:
        baseline_results, baseline_biomass = run_single_simulation(days, cultivar_id, system_type, treatment_id, input_dir)
        print(f"✅ Baseline biomass: {baseline_biomass:.3f} g")
    except Exception as e:
        print(f"❌ Baseline simulation failed: {e}")
        return
    
    # Results storage
    sensitivity_results = []
    failed_simulations = []
    skipped_params = []
    
    # Filter parameters that can be modified (numeric only)
    numeric_params = {}
    for param_name, param_data in original_params.items():
        if isinstance(param_data['value'], (int, float)) and not isinstance(param_data['value'], bool):
            numeric_params[param_name] = param_data
    
    print(f"📊 Found {len(numeric_params)} numeric parameters to analyze")
    print(f"🔄 Testing ±{change_percent}% change for each parameter (both increase and decrease)...")
    print("🔧 Using proportional scaling for allocation fractions")
    print("-" * 70)
    
    # Test each parameter with both positive and negative changes
    for i, (param_name, param_data) in enumerate(numeric_params.items(), 1):
        print(f"[{i}/{len(numeric_params)}] Testing parameter: {param_name}")
        
        original_value = param_data['value']
        
        # Test both positive and negative changes
        for direction, change_sign in [('increase', +1), ('decrease', -1)]:
            actual_change_percent = change_sign * change_percent
            
            print(f"  📈 Testing {direction} ({actual_change_percent:+.1f}%)...")
            
            # Apply proportional scaling for allocation parameters
            modified_params = apply_proportional_scaling(original_params, param_name, actual_change_percent)
            
            if modified_params is None:
                # Parameter couldn't be scaled or would exceed bounds
                allocation_groups = get_allocation_groups()
                parameter_bounds = get_parameter_bounds()
                
                # Determine reason for skipping
                reason = ""
                if any(param_name in param_list for param_list in allocation_groups.values()):
                    reason = f'Cannot scale proportionally for {direction}'
                elif param_name in parameter_bounds:
                    new_value = original_value * (1 + actual_change_percent / 100.0)
                    min_bound, max_bound = parameter_bounds[param_name]
                    reason = f'{direction.capitalize()} would exceed bounds ({new_value:.2f} outside {min_bound}-{max_bound})'
                else:
                    reason = f'{direction.capitalize()} creates invalid value'
                
                skipped_params.append({
                    'parameter_name': param_name,
                    'direction': direction,
                    'reason': reason
                })
                print(f"    ⏭️ Skipped {direction}: {reason}")
                continue
                
            modified_value = modified_params[param_name]['value']
            
            # Create temporary modified CSV file
            temp_master_file = f'{input_dir}/{file_prefix}_master_parameters_temp_{direction}.csv'
            save_modified_parameters(modified_params, temp_master_file)
            
            try:
                # Run simulation with modified parameter
                temp_treatment_id = f"{treatment_id}_{direction}" if treatment_id else f"{cultivar_id}_{direction}"
                
                # Temporarily rename the file for the simulation
                import shutil
                temp_sim_file = f'{input_dir}/{temp_treatment_id}_master_parameters.csv'
                shutil.copy2(temp_master_file, temp_sim_file)
                
                # Copy weather file for temp simulation
                original_weather = f'{input_dir}/{file_prefix}_weather.csv'
                temp_weather = f'{input_dir}/{temp_treatment_id}_weather.csv'
                shutil.copy2(original_weather, temp_weather)
                
                # For genetic parameters, use temp_treatment_id as cultivar_id to load modified genetic profile
                if param_data['category'] == 'genetic_parameters':
                    # Use temp_treatment_id as both cultivar and treatment to get modified genetic coefficients
                    results, final_biomass = run_single_simulation(days, temp_treatment_id, system_type, temp_treatment_id, input_dir)
                else:
                    # For non-genetic parameters, use original cultivar_id
                    results, final_biomass = run_single_simulation(days, cultivar_id, system_type, temp_treatment_id, input_dir)
                
                # Calculate sensitivity metrics
                biomass_change = final_biomass - baseline_biomass
                biomass_change_percent = (biomass_change / baseline_biomass) * 100 if baseline_biomass > 0 else 0
                sensitivity_ratio = biomass_change_percent / actual_change_percent if actual_change_percent != 0 else 0
                
                sensitivity_results.append({
                    'parameter_name': param_name,
                    'category': param_data['category'],
                    'original_value': original_value,
                    'modified_value': modified_value,
                    'direction': direction,
                    'parameter_change_percent': actual_change_percent,
                    'baseline_biomass': baseline_biomass,
                    'modified_biomass': final_biomass,
                    'biomass_change': biomass_change,
                    'biomass_change_percent': biomass_change_percent,
                    'sensitivity_ratio': sensitivity_ratio
                })
                
                print(f"    ✅ {original_value:.3f} → {modified_value:.3f}")
                print(f"    📊 Biomass: {baseline_biomass:.3f} → {final_biomass:.3f} g ({biomass_change_percent:+.2f}%)")
                print(f"    🎯 Sensitivity ratio: {sensitivity_ratio:.3f}")
                
                # Clean up temp files
                Path(temp_sim_file).unlink(missing_ok=True)
                Path(temp_weather).unlink(missing_ok=True)
                
            except Exception as e:
                failed_simulations.append({
                    'parameter_name': param_name,
                    'direction': direction,
                    'error': str(e)
                })
                print(f"    ❌ Failed {direction}: {e}")
                
                # Clean up temp files on failure
                Path(temp_sim_file).unlink(missing_ok=True)
                Path(temp_weather).unlink(missing_ok=True)
            
            # Clean up main temp file
            Path(temp_master_file).unlink(missing_ok=True)
        
        print()
    
    # Generate results summary
    print("=" * 90)
    print("🎯 TWO-SIDED SENSITIVITY ANALYSIS RESULTS")
    print("=" * 90)
    
    if sensitivity_results:
        # Group results by parameter for comparison
        parameter_groups = {}
        for result in sensitivity_results:
            param_name = result['parameter_name']
            if param_name not in parameter_groups:
                parameter_groups[param_name] = {'increase': None, 'decrease': None}
            parameter_groups[param_name][result['direction']] = result
        
        # Create comparison analysis
        comparison_results = []
        for param_name, directions in parameter_groups.items():
            increase_result = directions.get('increase')
            decrease_result = directions.get('decrease')
            
            if increase_result and decrease_result:
                # Calculate asymmetry metrics
                inc_ratio = increase_result['sensitivity_ratio']
                dec_ratio = decrease_result['sensitivity_ratio']
                
                # Asymmetry index: 0 = symmetric, >0 = more sensitive to increases, <0 = more sensitive to decreases
                asymmetry = (abs(inc_ratio) - abs(dec_ratio)) / max(abs(inc_ratio), abs(dec_ratio), 0.001)
                max_sensitivity = max(abs(inc_ratio), abs(dec_ratio))
                
                comparison_results.append({
                    'parameter_name': param_name,
                    'category': increase_result['category'],
                    'increase_sensitivity': inc_ratio,
                    'decrease_sensitivity': dec_ratio,
                    'max_sensitivity': max_sensitivity,
                    'asymmetry_index': asymmetry,
                    'increase_biomass_change': increase_result['biomass_change_percent'],
                    'decrease_biomass_change': decrease_result['biomass_change_percent']
                })
        
        # Sort by maximum sensitivity
        comparison_results.sort(key=lambda x: x['max_sensitivity'], reverse=True)
        
        print(f"\n📊 TWO-SIDED PARAMETER SENSITIVITY RANKING:")
        print(f"{'Rank':<4} {'Parameter':<25} {'Category':<12} {'Inc.Sens.':<9} {'Dec.Sens.':<9} {'Asymmetry':<10} {'Status':<12}")
        print("-" * 90)
        
        for rank, result in enumerate(comparison_results, 1):
            inc_sens = result['increase_sensitivity']
            dec_sens = result['decrease_sensitivity']
            asymmetry = result['asymmetry_index']
            max_sens = result['max_sensitivity']
            
            # Color coding based on maximum sensitivity
            if max_sens > 1.0:
                status = "🔴 HIGH"
            elif max_sens > 0.5:
                status = "🟡 MEDIUM"
            elif max_sens > 0.1:
                status = "🟢 LOW"
            else:
                status = "⚪ MINIMAL"
            
            # Asymmetry indicator
            if abs(asymmetry) > 0.3:
                if asymmetry > 0:
                    asym_indicator = "↗️ INC"
                else:
                    asym_indicator = "↘️ DEC"
            else:
                asym_indicator = "↔️ SYM"
            
            print(f"{rank:<4} {result['parameter_name']:<25} {result['category']:<12} "
                  f"{inc_sens:+8.3f} {dec_sens:+8.3f} {asym_indicator:<10} {status:<12}")
        
        # Identify highly asymmetric parameters
        asymmetric_params = [r for r in comparison_results if abs(r['asymmetry_index']) > 0.5]
        
        if asymmetric_params:
            print(f"\n🔄 HIGHLY ASYMMETRIC PARAMETERS (Non-linear Response):")
            print(f"{'Parameter':<30} {'Category':<12} {'Asymmetry':<12} {'Interpretation':<30}")
            print("-" * 95)
            
            for result in asymmetric_params:
                param_name = result['parameter_name']
                category = result['category']
                asymmetry = result['asymmetry_index']
                
                if asymmetry > 0:
                    interpretation = "More sensitive to increases"
                else:
                    interpretation = "More sensitive to decreases"
                
                print(f"{param_name:<30} {category:<12} {asymmetry:+8.3f} {interpretation:<30}")
        
        # Identify parameters with minimal effect
        minimal_params = [r for r in comparison_results if r['max_sensitivity'] < 0.01]
        
        if minimal_params:
            print(f"\n⚪ PARAMETERS WITH MINIMAL EFFECT ON BIOMASS:")
            print(f"{'Parameter':<30} {'Category':<12} {'Max Sensitivity':<15} {'Possible Reasons':<30}")
            print("-" * 95)
            
            for result in minimal_params:
                param_name = result['parameter_name']
                category = result['category']
                max_sens = result['max_sensitivity']
                
                # Analyze possible reasons for no effect
                reasons = []
                if 'co2' in param_name.lower():
                    reasons.append("CO2 not limiting")
                elif 'humidity' in param_name.lower() or 'vpd' in param_name.lower():
                    reasons.append("Humidity not stressed")
                elif 'nutrient' in param_name.lower() or 'ppm' in param_name.lower():
                    reasons.append("Nutrient not limiting")
                elif 'temperature' in param_name.lower():
                    reasons.append("Temperature optimal")
                elif 'light' in param_name.lower():
                    reasons.append("Light not limiting")
                elif 'ph' in param_name.lower():
                    reasons.append("pH in optimal range")
                else:
                    reasons.append("Parameter not active/limiting")
                
                reason_str = ", ".join(reasons) if reasons else "Unknown"
                print(f"{param_name:<30} {category:<12} {max_sens:8.3f} {reason_str:<30}")
        
        # Show symmetric vs asymmetric response summary
        symmetric_count = sum(1 for r in comparison_results if abs(r['asymmetry_index']) <= 0.3)
        asymmetric_count = len(comparison_results) - symmetric_count
        
        print(f"\n📈 RESPONSE SYMMETRY ANALYSIS:")
        print(f"  ↔️ Symmetric parameters (linear response): {symmetric_count}")
        print(f"  🔄 Asymmetric parameters (non-linear response): {asymmetric_count}")
        print(f"  🎯 Total parameters analyzed: {len(comparison_results)}")
        
        # Save detailed results
        results_file = f"outputs/two_sided_sensitivity_analysis_{file_prefix}.csv"
        
        Path("outputs").mkdir(exist_ok=True)
        
        # Save individual results
        individual_df = pd.DataFrame(sensitivity_results)
        individual_df.to_csv(results_file, index=False)
        
        # Save comparison results
        comparison_file = f"outputs/sensitivity_comparison_{file_prefix}.csv"
        comparison_df = pd.DataFrame(comparison_results)
        comparison_df.to_csv(comparison_file, index=False)
        
        print(f"\n💾 Detailed individual results saved to: {results_file}")
        print(f"💾 Comparison analysis saved to: {comparison_file}")
    
    if failed_simulations:
        print(f"\n❌ FAILED SIMULATIONS ({len(failed_simulations)}):")
        for failure in failed_simulations:
            direction = failure.get('direction', 'unknown')
            print(f"  • {failure['parameter_name']} ({direction}): {failure['error']}")
    
    if skipped_params:
        print(f"\n⏭️ SKIPPED PARAMETER TESTS ({len(skipped_params)}):")
        for skip in skipped_params:
            direction = skip.get('direction', 'unknown')
            print(f"  • {skip['parameter_name']} ({direction}): {skip['reason']}")
    
    print(f"\n✅ Two-sided sensitivity analysis completed!")
    print(f"📈 Tested {len(sensitivity_results)} parameter variations successfully")
    print(f"❌ Failed {len(failed_simulations)} parameter tests")
    print(f"⏭️ Skipped {len(skipped_params)} parameter variations")
    print(f"🔍 This analysis reveals both linear and non-linear parameter responses!")


def main():
    parser = argparse.ArgumentParser(description="CROPGRO Hydroponic Simulator - Parameter Sensitivity Analysis")
    parser.add_argument('--days', type=int, default=120, help='Max simulation days')
    parser.add_argument('--cultivar', type=str, default='LET_EXP001_2024', help='Cultivar ID')
    parser.add_argument('--system', type=str, default='NFT', choices=['NFT', 'DWC', 'AEROPONICS'], help='Hydroponic system type')
    parser.add_argument('--treatment-id', type=str, help='Treatment identifier (e.g., T01, T02)')
    parser.add_argument('--input-dir', type=str, default='input', help='Input directory containing CSV configuration files')
    parser.add_argument('--change-percent', type=float, default=10.0, help='Percentage to change each parameter (±, default: ±10%)')
    
    args = parser.parse_args()

    try:
        run_sensitivity_analysis(
            days=args.days,
            cultivar_id=args.cultivar,
            system_type=args.system,
            treatment_id=args.treatment_id,
            input_dir=args.input_dir,
            change_percent=args.change_percent
        )
    except Exception as e:
        print(f"❌ Sensitivity analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()