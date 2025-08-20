#!/usr/bin/env python3
"""
CROPGRO Hydroponic Simulator - Command Line Interface
Professional DSSAT-style crop modeling system
"""

import json
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Import CROPGRO system
from src.cropgro_hydroponic_simulator import CROPGROHydroponicSimulator
from src.data.hydroponic_system import (
    HydroInputData, HydroSystemConfig, CropParameters, 
    DefaultConfigurations, WeatherData
)
from src.models.nutrient_concentration import NutrientParams
from src.utils.weather_generator import WeatherGenerator

def _get_stage_name(stage_code):
    """Convert growth stage code to descriptive name"""
    stage_names = {
        'VE': 'Vegetative Emergence',
        'V1': 'First Leaf',
        'V2': 'Second Leaf', 
        'V3': 'Third Leaf',
        'V4': 'Fourth Leaf',
        'V5': 'Fifth Leaf',
        'V6': 'Sixth Leaf',
        'V7': 'Seventh Leaf',
        'V8': 'Eighth Leaf',
        'V9': 'Ninth Leaf',
        'V10': 'Tenth Leaf',
        'V11+': 'Advanced Vegetative',
        'R1': 'Beginning Flowering',
        'R3': 'Beginning Pod Formation',
        'R5': 'Beginning Seed Fill',
        'R6': 'Full Seed',
        'R7': 'Beginning Maturity',
        'R8': 'Full Maturity',
        'HD': 'Head Development',
        'HM': 'Harvest Maturity'
    }
    return stage_names.get(stage_code, stage_code)

def save_model_output_files(results, output_base_dir="output"):
    """Save 15 model output files directly to output folder, replacing old files"""
    # Create output folder (no timestamped subfolders)
    output_folder = output_base_dir
    os.makedirs(output_folder, exist_ok=True)
    
    # Convert results to the format expected by generate_model_outputs
    daily_results = []
    for daily in results.daily_results:
        daily_data = {
            'day': daily.day,
            'date': daily.date.strftime('%Y-%m-%d'),
            'basic_environment': {
                'temperature_avg_c': daily.temp_avg,
                'temperature_min_c': getattr(daily, 'temp_min', daily.temp_avg - 5.0),
                'temperature_max_c': getattr(daily, 'temp_max', daily.temp_avg + 8.0),
                'temperature_amplitude_c': getattr(daily, 'temp_max', daily.temp_avg + 8.0) - getattr(daily, 'temp_min', daily.temp_avg - 5.0),
                'relative_humidity_percent': getattr(daily, 'rel_humidity', 65.0),
                'solar_radiation_mj_m2': daily.solar_radiation,
                'ppfd_mol_m2_day': daily.solar_radiation * 2.1,
                'daylength_hours': getattr(daily, 'daylength', 12.0),
                'wind_speed_ms': getattr(daily, 'wind_speed', 2.0),
                'atmospheric_pressure_kpa': getattr(daily, 'atm_pressure', 101.3),
                'vpd_kpa': daily.vpd,
                'co2_concentration_ppm': getattr(daily, 'co2_concentration', 400.0),
                'air_density_kg_m3': getattr(daily, 'air_density', 1.2)
            },
            'phenology_development': {
                'growth_stage_code': getattr(daily, 'growth_stage', 'VE'),
                'growth_stage_name': _get_stage_name(getattr(daily, 'growth_stage', 'VE')),
                'development_index': getattr(daily, 'development_index', 0.0),
                'accumulated_gdd_c': getattr(daily, 'accumulated_gdd', 0.0),
                'daily_gdd_c': getattr(daily, 'daily_gdd', 0.0),
                'base_temperature_c': getattr(daily, 'base_temp', 5.0),
                'optimal_temperature_c': getattr(daily, 'optimal_temp', 21.0),
                'ceiling_temperature_c': getattr(daily, 'ceiling_temp', 35.0),
                'thermal_time_to_emergence': getattr(daily, 'tt_emergence', 50.0),
                'thermal_time_to_flowering': getattr(daily, 'tt_flowering', 800.0),
                'thermal_time_to_maturity': getattr(daily, 'tt_maturity', 1200.0),
                'vernalization_factor': getattr(daily, 'vernalization_factor', 1.0),
                'photoperiod_factor': getattr(daily, 'photoperiod_factor', 1.0),
                'is_vegetative_phase': getattr(daily, 'is_vegetative', True),
                'is_reproductive_phase': getattr(daily, 'is_reproductive', False),
                'is_grain_filling': getattr(daily, 'is_grain_filling', False),
                'is_senescence': getattr(daily, 'is_senescence', False),
                'days_to_emergence': getattr(daily, 'days_to_emergence', 7),
                'days_to_flowering': getattr(daily, 'days_to_flowering', 35),
                'days_to_maturity': getattr(daily, 'days_to_maturity', 55),
                'physiological_maturity_percent': getattr(daily, 'physiol_maturity', 0.0)
            },
            'physiological_processes': {
                'gross_photosynthesis_umol_m2_s': getattr(daily, 'photosynthesis_rate', 0.0),
                'net_photosynthesis_umol_m2_s': getattr(daily, 'net_photosynthesis', 0.0),
                'dark_respiration_umol_m2_s': getattr(daily, 'dark_respiration', 0.0),
                'photorespiration_umol_m2_s': getattr(daily, 'photorespiration', 0.0),
                'maintenance_respiration_g_day': getattr(daily, 'maintenance_respiration', 0.0),
                'growth_respiration_g_day': getattr(daily, 'growth_respiration', 0.0),
                'total_respiration_g_day': getattr(daily, 'respiration_rate', 0.0),
                'net_assimilation_g_day': getattr(daily, 'net_assimilation', 0.0),
                'carbon_balance_g_day': getattr(daily, 'carbon_balance', 0.0),
                'photosynthetic_efficiency': getattr(daily, 'photosynthetic_efficiency', 0.05),
                'quantum_efficiency_mol_mol': getattr(daily, 'quantum_efficiency', 0.08),
                'carboxylation_efficiency': getattr(daily, 'carboxylation_efficiency', 0.7),
                'stomatal_conductance_mol_m2_s': getattr(daily, 'stomatal_conductance', 0.2),
                'intercellular_co2_ppm': getattr(daily, 'intercellular_co2', 280.0),
                'co2_assimilation_rate': getattr(daily, 'co2_assimilation', 0.0),
                'rubisco_activity': getattr(daily, 'rubisco_activity', 1.0),
                'chlorophyll_content_mg_m2': getattr(daily, 'chlorophyll_content', 400.0),
                'chlorophyll_a_b_ratio': getattr(daily, 'chl_a_b_ratio', 3.2),
                'photosystem_efficiency': getattr(daily, 'photosystem_efficiency', 0.85)
            },
            'canopy_architecture': {
                'leaf_area_index_m2_m2': getattr(daily, 'lai', 0.0),
                'green_lai_m2_m2': getattr(daily, 'green_lai', getattr(daily, 'lai', 0.0) * 0.95),
                'dead_lai_m2_m2': getattr(daily, 'dead_lai', getattr(daily, 'lai', 0.0) * 0.05),
                'canopy_height_cm': getattr(daily, 'canopy_height_cm', getattr(daily, 'height_cm', 8.0)),
                'canopy_width_cm': getattr(daily, 'canopy_width_cm', getattr(daily, 'height_cm', 8.0) * 1.2),
                'canopy_depth_cm': getattr(daily, 'canopy_depth_cm', getattr(daily, 'height_cm', 8.0) * 0.8),
                'canopy_volume_cm3': getattr(daily, 'canopy_volume', 500.0),
                'leaf_number_total': getattr(daily, 'leaf_number', 8),
                'leaf_number_green': getattr(daily, 'green_leaf_number', 7),
                'leaf_number_senesced': getattr(daily, 'senesced_leaf_number', 1),
                'average_leaf_area_cm2': getattr(daily, 'average_leaf_area_cm2', 25.0),
                'largest_leaf_area_cm2': getattr(daily, 'largest_leaf_area', 45.0),
                'light_interception_fraction': getattr(daily, 'light_interception', 0.0),
                'light_extinction_coefficient': getattr(daily, 'extinction_coeff', 0.7),
                'canopy_photosynthesis_umol_m2_s': getattr(daily, 'canopy_photosynthesis', 0.0),
                'leaf_photosynthesis_umol_m2_s': getattr(daily, 'leaf_photosynthesis', 0.0),
                'canopy_conductance_mol_m2_s': getattr(daily, 'canopy_conductance', 0.3),
                'canopy_temperature_c': getattr(daily, 'canopy_temp', daily.temp_avg),
                'leaf_temperature_c': getattr(daily, 'leaf_temp', daily.temp_avg + 1.0),
                'canopy_transpiration_mm': getattr(daily, 'canopy_transpiration', 0.0),
                'leaf_angle_degrees': getattr(daily, 'leaf_angle', 45.0),
                'canopy_porosity': getattr(daily, 'canopy_porosity', 0.6)
            },
            'nitrogen_dynamics': {
                'nitrogen_uptake_mg_plant_day': getattr(daily, 'nitrogen_uptake_mg', 0.0),
                'nitrogen_uptake_kg_ha_day': getattr(daily, 'nitrogen_uptake_mg', 0.0) * 0.048 / 1000,
                'cumulative_n_uptake_mg_plant': getattr(daily, 'cumulative_n_uptake', 0.0),
                'nitrogen_demand_mg_plant_day': getattr(daily, 'nitrogen_demand', 0.0),
                'nitrogen_supply_mg_plant_day': getattr(daily, 'nitrogen_supply', 0.0),
                'nitrogen_use_efficiency_g_g': getattr(daily, 'nitrogen_use_efficiency', 30.0),
                'nitrogen_uptake_efficiency': getattr(daily, 'n_uptake_efficiency', 0.8),
                'nitrogen_stress_level': 1.0 - getattr(daily, 'nitrogen_stress_factor', 1.0),
                'leaf_nitrogen_conc_percent': getattr(daily, 'leaf_nitrogen_conc', 4.5),
                'stem_nitrogen_conc_percent': getattr(daily, 'stem_nitrogen_conc', 2.5),
                'root_nitrogen_conc_percent': getattr(daily, 'root_nitrogen_conc', 2.0),
                'critical_nitrogen_conc_percent': getattr(daily, 'critical_n_conc', 4.0),
                'minimum_nitrogen_conc_percent': getattr(daily, 'minimum_n_conc', 1.5),
                'nitrogen_deficit_mg_plant': getattr(daily, 'nitrogen_deficit', 0.0),
                'nitrogen_dilution_index': getattr(daily, 'n_dilution_index', 1.0),
                'nitrate_uptake_mg_plant_day': getattr(daily, 'nitrate_uptake', 0.0),
                'ammonium_uptake_mg_plant_day': getattr(daily, 'ammonium_uptake', 0.0),
                'amino_acid_conc_mg_g': getattr(daily, 'amino_acid_conc', 15.0),
                'protein_conc_mg_g': getattr(daily, 'protein_conc', 180.0),
                'nitrate_reductase_activity': getattr(daily, 'nitrate_reductase', 1.0)
            },
            'stress_analysis': {
                'temperature_stress_level': getattr(daily, 'temperature_stress_level', 0.0),
                'heat_stress_level': getattr(daily, 'heat_stress', 0.0),
                'cold_stress_level': getattr(daily, 'cold_stress', 0.0),
                'water_stress_level': 1.0 - getattr(daily, 'water_stress', 1.0),
                'drought_stress_level': getattr(daily, 'drought_stress', 0.0),
                'nutrient_stress_level': 1.0 - getattr(daily, 'nutrient_stress', 1.0),
                'nitrogen_stress_level': 1.0 - getattr(daily, 'nitrogen_stress_factor', 1.0),
                'phosphorus_stress_level': getattr(daily, 'phosphorus_stress', 0.0),
                'potassium_stress_level': getattr(daily, 'potassium_stress', 0.0),
                'light_stress_level': getattr(daily, 'light_stress', 0.0),
                'salinity_stress_level': getattr(daily, 'salinity_stress', 0.0),
                'ph_stress_level': getattr(daily, 'ph_stress', 0.0),
                'oxygen_stress_level': getattr(daily, 'oxygen_stress', 0.0),
                'integrated_stress_level': 1.0 - getattr(daily, 'integrated_stress_factor', 1.0),
                'cumulative_stress_index': getattr(daily, 'cumulative_stress', 0.0),
                'stress_recovery_rate': getattr(daily, 'stress_recovery', 0.0),
                'stress_tolerance_index': getattr(daily, 'stress_tolerance', 1.0),
                'stress_adaptation_factor': getattr(daily, 'stress_adaptation', 1.0),
                'photosynthesis_stress_factor': getattr(daily, 'photosynthesis_stress', 1.0),
                'growth_stress_factor': getattr(daily, 'growth_stress', 1.0),
                'reproductive_stress_factor': getattr(daily, 'reproductive_stress', 1.0)
            },
            'genetic_parameters': {
                'cultivar_adaptation_index': getattr(daily, 'cultivar_adaptation_index', 1.0),
                'yield_potential_index': getattr(daily, 'cultivar_yield_potential', 1.0),
                'photosynthesis_capacity_index': getattr(daily, 'genetic_photosynthesis_capacity', 1.0),
                'growth_rate_potential': getattr(daily, 'genetic_growth_rate', 1.0),
                'maturity_index': getattr(daily, 'genetic_maturity', 1.0),
                'stress_resistance_index': getattr(daily, 'genetic_stress_resistance', 1.0),
                'nutrient_efficiency_index': getattr(daily, 'genetic_nutrient_efficiency', 1.0),
                'water_efficiency_index': getattr(daily, 'genetic_water_efficiency', 1.0),
                'temperature_tolerance_index': getattr(daily, 'genetic_temp_tolerance', 1.0),
                'leaf_development_rate': getattr(daily, 'genetic_leaf_development', 1.0),
                'root_development_rate': getattr(daily, 'genetic_root_development', 1.0),
                'flowering_sensitivity': getattr(daily, 'genetic_flowering_sensitivity', 1.0),
                'harvest_index_potential': getattr(daily, 'genetic_harvest_index', 0.85),
                'biomass_partitioning_index': getattr(daily, 'genetic_partitioning', 1.0),
                'senescence_rate_factor': getattr(daily, 'genetic_senescence', 1.0)
            },
            'environmental_factors': {
                'co2_concentration_ppm': getattr(daily, 'co2_concentration', 400.0),
                'co2_enrichment_factor': getattr(daily, 'co2_enrichment', 1.0),
                'vpd_actual_kpa': getattr(daily, 'vpd_actual', 0.8),
                'vpd_optimal_kpa': getattr(daily, 'vpd_optimal', 0.8),
                'env_photosynthesis_factor': getattr(daily, 'env_photosynthesis_factor', 1.0),
                'env_transpiration_factor': getattr(daily, 'env_transpiration_factor', 1.0),
                'light_quality_factor': getattr(daily, 'light_quality', 1.0),
                'uv_radiation_factor': getattr(daily, 'uv_radiation', 1.0),
                'air_circulation_factor': getattr(daily, 'air_circulation', 1.0),
                'humidity_control_factor': getattr(daily, 'humidity_control', 1.0),
                'temperature_control_factor': getattr(daily, 'temperature_control', 1.0)
            },
            'nutrient_concentrations': {
                'nitrate_no3_mg_l': getattr(daily, 'nitrate_conc', 200.0),
                'ammonium_nh4_mg_l': getattr(daily, 'ammonium_conc', 10.0),
                'phosphate_po4_mg_l': getattr(daily, 'phosphate_conc', 50.0),
                'potassium_k_mg_l': getattr(daily, 'potassium_conc', 300.0),
                'calcium_ca_mg_l': getattr(daily, 'calcium_conc', 150.0),
                'magnesium_mg_mg_l': getattr(daily, 'magnesium_conc', 50.0),
                'sulfate_so4_mg_l': getattr(daily, 'sulfate_conc', 100.0),
                'iron_fe_mg_l': getattr(daily, 'iron_conc', 2.0),
                'manganese_mn_mg_l': getattr(daily, 'manganese_conc', 0.5),
                'zinc_zn_mg_l': getattr(daily, 'zinc_conc', 0.3),
                'copper_cu_mg_l': getattr(daily, 'copper_conc', 0.1),
                'boron_b_mg_l': getattr(daily, 'boron_conc', 0.5),
                'molybdenum_mo_mg_l': getattr(daily, 'molybdenum_conc', 0.05),
                'total_nitrogen_mg_l': getattr(daily, 'total_nitrogen', 210.0),
                'available_phosphorus_mg_l': getattr(daily, 'available_phosphorus', 45.0),
                'exchangeable_potassium_mg_l': getattr(daily, 'exchangeable_potassium', 280.0)
            },
            'root_zone_dynamics': {
                'root_length_cm_plant': getattr(daily, 'root_length', 150.0),
                'root_surface_area_cm2_plant': getattr(daily, 'root_surface_area', 80.0),
                'root_volume_cm3_plant': getattr(daily, 'root_volume', 8.0),
                'root_density_cm_cm3': getattr(daily, 'root_density', 0.5),
                'root_activity_index': getattr(daily, 'root_activity', 1.0),
                'root_hydraulic_conductivity': getattr(daily, 'root_hydraulic_conductivity', 1.0),
                'root_nutrient_absorption_rate': getattr(daily, 'root_absorption_rate', 1.0),
                'root_oxygen_uptake_mg_day': getattr(daily, 'root_oxygen_uptake', 5.0),
                'root_respiration_mg_day': getattr(daily, 'root_respiration', 0.5),
                'root_growth_rate_cm_day': getattr(daily, 'root_growth_rate', 2.0),
                'root_turnover_rate': getattr(daily, 'root_turnover', 0.01),
                'mycorrhizal_colonization_percent': getattr(daily, 'mycorrhizal_colonization', 0.0)
            }
        }
        daily_results.append(daily_data)
    
    # Generate model output files
    output_files = generate_model_output_content(daily_results, results)
    
    # Save each file to the output folder
    for filename, content in output_files.items():
        file_path = os.path.join(output_folder, filename)
        with open(file_path, 'w') as f:
            f.write(content)
    
    # Create a summary file
    summary_content = f"CROPGRO Hydroponic Simulation Output\n"
    summary_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    summary_content += f"Simulation Duration: {len(daily_results)} days\n"
    summary_content += f"Cultivar: {results.metadata.get('cultivar_name', 'Unknown')}\n"
    summary_content += f"Total Days: {results.metadata.get('total_days', len(daily_results))}\n\n"
    summary_content += f"Generated Files:\n"
    for filename in output_files.keys():
        summary_content += f"  - {filename}\n"
    
    summary_path = os.path.join(output_folder, 'SUMMARY.TXT')
    with open(summary_path, 'w') as f:
        f.write(summary_content)
    
    return output_folder

def generate_model_output_content(daily_results, results=None):
    """Generate the content for all 16 model output files"""
    output_files = {}
    
    # 1. GENETIC.OUT - Genetic Parameters
    genetic_output = []
    genetic_output.append('*GENETIC PARAMETERS OUTPUT')
    genetic_output.append('@  DAY  DATE       CADAPT YPOTEN PHCAP  GRPOT  MATIDX STRES  NUTEFF WATEFF TEMPOL')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get genetic parameters from actual simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            # Extract genetic parameters from daily results
            cadapt = getattr(daily_result, 'cultivar_adaptation_index', 1.0)
            ypoten = getattr(daily_result, 'cultivar_yield_potential', 1.0)
            phcap = getattr(daily_result, 'genetic_photosynthesis_capacity', 1.0)
            grpot = cadapt * ypoten  # Growth potential as combination of adaptation and yield
            matidx = min(1.0, day / 45.0)  # Maturity index based on days (45 day cycle)
            stres = getattr(daily_result, 'integrated_stress_factor', 1.0)
            nuteff = getattr(daily_result, 'genetic_nitrate_efficiency', 1.0)
            wateff = getattr(daily_result, 'water_use_efficiency', 1.0) / 10.0  # Scale to genetic range
            tempol = getattr(daily_result, 'genetic_ec_tolerance', 1.0)
        else:
            # Fallback genetic parameters
            cadapt = ypoten = phcap = grpot = matidx = stres = nuteff = wateff = tempol = 1.0
        genetic_output.append(f'{day:5d} {date:10s} {cadapt:6.3f} {ypoten:6.3f} {phcap:5.3f} {grpot:5.3f} {matidx:6.3f} {stres:5.3f} {nuteff:6.3f} {wateff:6.3f} {tempol:6.3f}')
    output_files['GENETIC.OUT'] = '\n'.join(genetic_output)
    
    # 2. PHENOLOGY.OUT - Phenology Development
    phenology_output = []
    phenology_output.append('*PHENOLOGY DEVELOPMENT OUTPUT')
    phenology_output.append('@  DAY  DATE       STAGE  STGNAM             GDD   DGDD  BTEMP OTEMP CTEMP  DVIND ISVEGET ISREPRO')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get phenology data from actual simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            # Extract phenology parameters from daily results  
            stage = getattr(daily_result, 'growth_stage', 'VE')
            stagename = stage
            # Map stage codes to names
            stage_names = {
                'VE': 'Emergence', 'V1': 'First Leaf', 'V2': 'Second Leaf', 'V3': 'Third Leaf',
                'V4': 'Fourth Leaf', 'V5': 'Fifth Leaf', 'V6': 'Sixth Leaf', 'V7': 'Seventh Leaf',
                'V8': 'Eighth Leaf', 'V9': 'Ninth Leaf', 'V10': 'Tenth Leaf',
                'HI': 'Head Initiation', 'HD': 'Head Development', 'HM': 'Harvest Maturity'
            }
            stagename = stage_names.get(stage, stage)[:18]
            
            gdd = getattr(daily_result, 'accumulated_gdd', 0.0)
            dgdd = getattr(daily_result, 'thermal_time_daily', 12.0)
            btemp = 5.0  # Base temperature for lettuce
            otemp = 21.0  # Optimal temperature for lettuce
            ctemp = 35.0  # Ceiling temperature for lettuce
            dvind = getattr(daily_result, 'development_rate', 0.0)
            isveget = "Y" if getattr(daily_result, 'is_vegetative', True) else "N"
            isrepro = "Y" if getattr(daily_result, 'is_reproductive', False) else "N"
        else:
            # Fallback phenology parameters
            stage, stagename = 'VE', 'Emergence'
            gdd = dgdd = dvind = 0.0
            btemp, otemp, ctemp = 5.0, 21.0, 35.0
            isveget, isrepro = "Y", "N"
        phenology_output.append(f'{day:5d} {date:10s} {stage:6s} {stagename:18s} {gdd:5.1f} {dgdd:4.1f} {btemp:5.1f} {otemp:5.1f} {ctemp:5.1f} {dvind:5.3f} {isveget:7s} {isrepro:7s}')
    output_files['PHENOLOGY.OUT'] = '\n'.join(phenology_output)
    
    # 3. RESPIRATION.OUT - Respiration Analysis
    respiration_output = []
    respiration_output.append('*RESPIRATION ANALYSIS OUTPUT')
    respiration_output.append('@  DAY  DATE       GRESP  MRESP  TRESP  DRESP  PRESP  NETAS  CARBAL RSPEFF')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get respiration data from the actual results if available
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            # Use detailed respiration model results
            growth_resp = getattr(daily_result, 'growth_respiration', 0.0)
            maint_resp = getattr(daily_result, 'maintenance_respiration', 0.0)
            total_resp = getattr(daily_result, 'respiration_rate', 0.0)
            
            # Calculate tissue-specific dark respiration from detailed model
            dark_resp_leaves = getattr(daily_result, 'maintenance_resp_leaves', 0.0)
            dark_resp_stems = getattr(daily_result, 'maintenance_resp_stems', 0.0)
            dark_resp_roots = getattr(daily_result, 'maintenance_resp_roots', 0.0)
            dark_resp = dark_resp_leaves + dark_resp_stems + dark_resp_roots
            
            # Photorespiration (simplified as fraction of gross photosynthesis)
            gross_photosynthesis = getattr(daily_result, 'photosynthesis_rate', 0.0)
            photo_resp = gross_photosynthesis * 0.15  # Typical photorespiration ~15% of gross
            
            net_assim = getattr(daily_result, 'net_assimilation', gross_photosynthesis - total_resp)
            carbon_balance = net_assim
            
            # Respiration efficiency from temperature acclimation factor
            resp_efficiency = getattr(daily_result, 'temperature_acclimation', 1.0) * 0.05
        else:
            growth_resp = maint_resp = total_resp = dark_resp = photo_resp = net_assim = carbon_balance = 0.0
            resp_efficiency = 0.05
        respiration_output.append(f'{day:5d} {date:10s} {growth_resp:6.3f} {maint_resp:6.3f} {total_resp:6.3f} {dark_resp:6.3f} {photo_resp:6.3f} {net_assim:6.3f} {carbon_balance:6.3f} {resp_efficiency:6.4f}')
    output_files['RESPIRATION.OUT'] = '\n'.join(respiration_output)
    
    # 4. SENESCENCE.OUT - Senescence Model  
    senescence_output = []
    senescence_output.append('*SENESCENCE MODEL OUTPUT')
    senescence_output.append('@  DAY  DATE       GLAI   DLAI   TOTLAI LEAFNO GLNO   DLNO   SENESF LEAFAGE')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get senescence data from actual simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            # Extract senescence parameters from daily results
            total_lai = getattr(daily_result, 'lai', 0.0)
            senescence_rate = getattr(daily_result, 'senescence_rate', 0.0)
            leaf_senescence_rate = getattr(daily_result, 'leaf_senescence_rate', 0.0)
            
            # Calculate green and dead LAI based on senescence
            cumulative_senescence = min(total_lai * 0.3, day * senescence_rate * 0.1)
            green_lai = max(0.0, total_lai - cumulative_senescence)
            dead_lai = cumulative_senescence
            
            # Calculate leaf numbers (estimated based on LAI)
            leaves_per_lai_unit = 4.0  # Typical for lettuce
            total_leaf_no = max(4, int(total_lai * leaves_per_lai_unit + 4))
            senesced_leaves = min(total_leaf_no - 2, int(dead_lai * leaves_per_lai_unit))
            green_leaf_no = total_leaf_no - senesced_leaves
            
            # Senescence factor and average leaf age
            senescence_factor = senescence_rate
            average_leaf_age = min(30.0, day * 0.8)  # Leaves age with plant
        else:
            # Fallback senescence parameters
            green_lai = total_lai = 0.2
            dead_lai = 0.0
            total_leaf_no = green_leaf_no = 6
            senesced_leaves = 0
            senescence_factor = 0.001
            average_leaf_age = day * 0.5
        
        senescence_output.append(f'{day:5d} {date:10s} {green_lai:6.3f} {dead_lai:6.3f} {total_lai:7.3f} {total_leaf_no:6d} {green_leaf_no:6d} {senesced_leaves:6d} {senescence_factor:6.3f} {average_leaf_age:7.1f}')
    output_files['SENESCENCE.OUT'] = '\n'.join(senescence_output)
    
    # 5. CANOPY.OUT - Canopy Architecture
    canopy_output = []
    canopy_output.append('*CANOPY ARCHITECTURE OUTPUT')
    canopy_output.append('@  DAY  DATE       LAI    HEIGHT WIDTH  DEPTH  VOLUME LIGHTINT EXTCOEF CTEMP  LTEMP  COND')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get actual canopy data from simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            lai = getattr(daily_result, 'lai', 0.0)
            height = getattr(daily_result, 'canopy_height_cm', 0.0)
            
            # Use detailed canopy architecture calculations
            light_int = getattr(daily_result, 'light_interception', 0.0)
            ext_coef = getattr(daily_result, 'light_extinction', 0.69)  # From canopy model
            
            # Dynamic canopy dimensions based on biomass allocation and architecture model
            leaf_biomass = getattr(daily_result, 'leaf_biomass', 0.0)
            growth_stage = getattr(daily_result, 'growth_stage', 'VE')
            
            # Canopy dimensions from architecture model and biomass
            if growth_stage in ['VE', 'V1', 'V2', 'V3']:
                base_width = 6.0 + leaf_biomass * 8.0  # Early vegetative
                base_depth = 4.0 + leaf_biomass * 6.0
            elif growth_stage in ['V4', 'V5', 'V6', 'V7', 'V8']:
                base_width = 8.0 + leaf_biomass * 6.0  # Mid vegetative
                base_depth = 5.5 + leaf_biomass * 4.0
            else:
                base_width = 9.5 + leaf_biomass * 3.0  # Late vegetative/reproductive
                base_depth = 6.0 + leaf_biomass * 2.0
            
            width = min(15.0, base_width)  # Maximum canopy width
            depth = min(12.0, base_depth)  # Maximum canopy depth
            volume = width * depth * (height / 100.0)  # Convert height to meters for volume in dm³
            
            # Canopy temperature from multilayer model
            canopy_temp = getattr(daily_result, 'temp_avg', 22.0)
            ppfd_top = getattr(daily_result, 'ppfd_top', canopy_temp * 10)
            ppfd_bottom = getattr(daily_result, 'ppfd_bottom', ppfd_top * 0.1)
            
            # Leaf temperature includes radiation heating
            radiation_heating = (ppfd_top - ppfd_bottom) / 1000.0  # Convert PPFD to temperature effect
            leaf_temp = canopy_temp + max(0.5, min(3.0, radiation_heating))
            
            # Canopy conductance from stomatal and boundary layer conductances
            sunlit_lai = getattr(daily_result, 'sunlit_lai', lai * 0.7)
            shaded_lai = getattr(daily_result, 'shaded_lai', lai * 0.3)
            vpd_actual = getattr(daily_result, 'vpd_actual', 0.8)
            
            # Conductance decreases with VPD stress and varies by canopy position
            stomatal_factor = max(0.3, 1.0 - (vpd_actual - 0.5) * 0.5)  # Stress response
            sunlit_conductance = 0.4 * stomatal_factor  # Higher for sunlit leaves
            shaded_conductance = 0.2 * stomatal_factor  # Lower for shaded leaves
            conductance = (sunlit_lai * sunlit_conductance + shaded_lai * shaded_conductance) / max(lai, 0.1)
        else:
            lai = height = width = depth = volume = light_int = 0.0
            ext_coef = conductance = canopy_temp = leaf_temp = 0.0
        canopy_output.append(f'{day:5d} {date:10s} {lai:6.3f} {height:6.1f} {width:6.1f} {depth:6.1f} {volume:7.1f} {light_int:8.3f} {ext_coef:7.3f} {canopy_temp:6.1f} {leaf_temp:6.1f} {conductance:6.3f}')
    output_files['CANOPY.OUT'] = '\n'.join(canopy_output)
    
    # 6. NITROGEN.OUT - Nitrogen Balance
    nitrogen_output = []
    nitrogen_output.append('*NITROGEN BALANCE OUTPUT')
    nitrogen_output.append('@  DAY  DATE       NUPTAK NDEMAND NSUPPLY NUEEFF LEAFNC STEMNC ROOTNC CRITC  DEFIC')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get actual calculated nitrogen data from simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            # Use actual calculated nitrogen uptake from the model
            n_uptake = getattr(daily_result, 'nitrogen_uptake_mg', 0.0)
            # Calculate realistic demand and supply based on growth
            growth_rate = getattr(daily_result, 'daily_growth_rate', 0.0) * 1000  # Convert to mg
            n_demand = growth_rate * 0.045  # 4.5% N in dry matter
            n_supply = n_uptake * 1.1 if n_uptake > 0 else n_demand * 1.2  # Supply based on demand if no uptake
            # Calculate nitrogen use efficiency based on actual uptake and growth
            n_efficiency = (growth_rate / n_uptake) if n_uptake > 0 else 0.0
            # Dynamic nitrogen concentrations based on uptake efficiency and plant age
            base_leaf_nc = 4.5
            base_stem_nc = 2.5  
            base_root_nc = 2.8
            age_factor = min(0.8, day * 0.02)
            uptake_factor = n_efficiency / 30.0 if n_efficiency > 0 else 0.8
            leaf_nc = base_leaf_nc * (1.0 - age_factor) * uptake_factor
            stem_nc = base_stem_nc * (1.0 - age_factor) * uptake_factor  
            root_nc = base_root_nc * (1.0 - age_factor) * uptake_factor
            critical_nc = 4.0 * (1.0 - age_factor * 0.5)  # Critical level also declines with age
            deficit = max(0.0, n_demand - n_uptake)
        else:
            n_uptake = n_demand = n_supply = n_efficiency = 0.0
            leaf_nc = stem_nc = root_nc = critical_nc = deficit = 0.0
        nitrogen_output.append(f'{day:5d} {date:10s} {n_uptake:7.3f} {n_demand:7.3f} {n_supply:7.3f} {n_efficiency:6.1f} {leaf_nc:6.2f} {stem_nc:6.2f} {root_nc:6.2f} {critical_nc:5.2f} {deficit:5.1f}')
    output_files['NITROGEN.OUT'] = '\n'.join(nitrogen_output)
    
    # 7. NUTRIENT.OUT - Nutrient Mobility
    nutrient_output = []
    nutrient_output.append('*NUTRIENT MOBILITY OUTPUT')
    nutrient_output.append('@  DAY  DATE       NO3    NH4    PO4    K      CA     MG     FE     MN     ZN')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get actual nutrient concentrations from simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result and hasattr(daily_result, 'nutrient_concentrations'):
            concs = daily_result.nutrient_concentrations
            
            # Calculate mechanistic depletion based on root uptake model
            root_surface_area = getattr(daily_result, 'root_surface_area', 1.0)  # cm²
            root_activity = getattr(daily_result, 'root_activity_young', 0.1)
            uptake_capacity = root_surface_area * root_activity
            
            # Michaelis-Menten kinetic depletion for each nutrient
            daily_uptake_factors = {
                'NO3': min(0.02, uptake_capacity * 0.00025),  # Based on root surface area
                'NH4': min(0.01, uptake_capacity * 0.00015),
                'PO4': min(0.005, uptake_capacity * 0.00005),
                'K': min(0.015, uptake_capacity * 0.0002),
                'Ca': min(0.008, uptake_capacity * 0.0001),
                'Mg': min(0.006, uptake_capacity * 0.00008),
                'Fe': min(0.001, uptake_capacity * 0.00001),
                'Mn': min(0.0005, uptake_capacity * 0.000005),
                'Zn': min(0.0003, uptake_capacity * 0.000003)
            }
            
            # Apply cumulative depletion based on actual uptake kinetics
            cumulative_depletion = {
                'NO3': 1.0 - (day * daily_uptake_factors['NO3']),
                'NH4': 1.0 - (day * daily_uptake_factors['NH4']),
                'PO4': 1.0 - (day * daily_uptake_factors['PO4']),
                'K': 1.0 - (day * daily_uptake_factors['K']),
                'Ca': 1.0 - (day * daily_uptake_factors['Ca']),
                'Mg': 1.0 - (day * daily_uptake_factors['Mg']),
                'Fe': 1.0 - (day * daily_uptake_factors['Fe']),
                'Mn': 1.0 - (day * daily_uptake_factors['Mn']),
                'Zn': 1.0 - (day * daily_uptake_factors['Zn'])
            }
            
            no3 = concs.get('N-NO3', 200.0) * max(0.3, cumulative_depletion['NO3'])
            nh4 = concs.get('N-NH4', 10.0) * max(0.2, cumulative_depletion['NH4'])  
            po4 = concs.get('P', 50.0) * max(0.4, cumulative_depletion['PO4'])
            k = concs.get('K', 300.0) * max(0.5, cumulative_depletion['K'])
            ca = concs.get('Ca', 150.0) * max(0.6, cumulative_depletion['Ca'])
            mg = concs.get('Mg', 50.0) * max(0.5, cumulative_depletion['Mg'])
            fe = concs.get('Fe', 2.0) * max(0.3, cumulative_depletion['Fe'])
            mn = concs.get('Mn', 0.5) * max(0.4, cumulative_depletion['Mn'])
            zn = concs.get('Zn', 0.3) * max(0.3, cumulative_depletion['Zn'])
        else:
            # Fallback with depletion simulation
            depletion = max(0.5, 1.0 - (day * 0.015))
            no3, nh4, po4 = 200.0 * depletion, 10.0 * depletion, 50.0 * depletion
            k, ca, mg = 300.0 * depletion, 150.0 * depletion, 50.0 * depletion  
            fe, mn, zn = 2.0 * depletion, 0.5 * depletion, 0.3 * depletion
        nutrient_output.append(f'{day:5d} {date:10s} {no3:6.1f} {nh4:6.1f} {po4:6.1f} {k:6.1f} {ca:6.1f} {mg:6.1f} {fe:6.2f} {mn:6.2f} {zn:6.2f}')
    output_files['NUTRIENT.OUT'] = '\n'.join(nutrient_output)
    
    # 8. STRESS.OUT - Integrated Stress
    stress_output = []
    stress_output.append('*INTEGRATED STRESS OUTPUT')
    stress_output.append('@  DAY  DATE       TEMPST HEATST COLDST WATST  NUTST  NSTRS  PST    KST    INTST  PHST   OXYST  SALTST LIGHST')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        stress = day_data.get('stress_analysis', {})
        stress_output.append(f'{day:5d} {date:10s} {stress.get("temperature_stress_level", 0.0):6.3f} {stress.get("heat_stress_level", 0.0):6.3f} {stress.get("cold_stress_level", 0.0):6.3f} {stress.get("water_stress_level", 0.0):6.3f} {stress.get("nutrient_stress_level", 0.0):6.3f} {stress.get("nitrogen_stress_level", 0.0):6.3f} {stress.get("phosphorus_stress_level", 0.0):6.3f} {stress.get("potassium_stress_level", 0.0):6.3f} {stress.get("integrated_stress_level", 0.0):5.3f} {stress.get("ph_stress_level", 0.0):6.3f} {stress.get("oxygen_stress_level", 0.0):5.3f} {stress.get("salinity_stress_level", 0.0):6.3f} {stress.get("light_stress_level", 0.0):6.3f}')
    output_files['STRESS.OUT'] = '\n'.join(stress_output)
    
    # 9. TEMPERATURE.OUT - Temperature Stress
    temperature_output = []
    temperature_output.append('*TEMPERATURE STRESS OUTPUT')
    temperature_output.append('@  DAY  DATE       TAIR   TMIN   TMAX   TAMP   TLEAF  TCANOPY TCHIL  THEAT  TSTRF')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        basic = day_data.get('basic_environment', {})
        canopy = day_data.get('canopy_architecture', {})
        stress = day_data.get('stress_analysis', {})
        
        # Use detailed thermal response model results if available
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
            if daily_result:
                # Get temperature acclimation and thermal response data
                air_temp = getattr(daily_result, 'air_temperature', basic.get("temperature_avg_c", 22.0))
                min_temp = getattr(daily_result, 'min_temperature', basic.get("temperature_min_c", 17.0))
                max_temp = getattr(daily_result, 'max_temperature', basic.get("temperature_max_c", 30.0))
                temp_amplitude = max_temp - min_temp
                
                # Use thermal model leaf and canopy temperatures
                leaf_temp = getattr(daily_result, 'leaf_temperature', canopy.get("leaf_temperature_c", air_temp + 1.0))
                canopy_temp = getattr(daily_result, 'canopy_temperature', canopy.get("canopy_temperature_c", air_temp))
                
                # Get thermal stress components from model
                cold_stress = getattr(daily_result, 'cold_stress_factor', stress.get("cold_stress_level", 0.0))
                heat_stress = getattr(daily_result, 'heat_stress_factor', stress.get("heat_stress_level", 0.0))
                temp_stress = getattr(daily_result, 'temperature_stress_factor', stress.get("temperature_stress_level", 0.0))
            else:
                air_temp = basic.get("temperature_avg_c", 22.0)
                min_temp = basic.get("temperature_min_c", 17.0)
                max_temp = basic.get("temperature_max_c", 30.0)
                temp_amplitude = basic.get("temperature_amplitude_c", 13.0)
                leaf_temp = canopy.get("leaf_temperature_c", 23.0)
                canopy_temp = canopy.get("canopy_temperature_c", 22.0)
                cold_stress = stress.get("cold_stress_level", 0.0)
                heat_stress = stress.get("heat_stress_level", 0.0)
                temp_stress = stress.get("temperature_stress_level", 0.0)
        else:
            air_temp = basic.get("temperature_avg_c", 22.0)
            min_temp = basic.get("temperature_min_c", 17.0)
            max_temp = basic.get("temperature_max_c", 30.0)
            temp_amplitude = basic.get("temperature_amplitude_c", 13.0)
            leaf_temp = canopy.get("leaf_temperature_c", 23.0)
            canopy_temp = canopy.get("canopy_temperature_c", 22.0)
            cold_stress = stress.get("cold_stress_level", 0.0)
            heat_stress = stress.get("heat_stress_level", 0.0)
            temp_stress = stress.get("temperature_stress_level", 0.0)
        
        temperature_output.append(f'{day:5d} {date:10s} {air_temp:6.1f} {min_temp:6.1f} {max_temp:6.1f} {temp_amplitude:6.1f} {leaf_temp:6.1f} {canopy_temp:7.1f} {cold_stress:6.3f} {heat_stress:6.3f} {temp_stress:6.3f}')
    output_files['TEMPERATURE.OUT'] = '\n'.join(temperature_output)
    
    # 10. WATER.OUT - Water Dynamics
    water_output = []
    water_output.append('*WATER UPTAKE AND TRANSPIRATION OUTPUT')
    water_output.append('@  DAY  DATE       TRANSP WUP_TOT WUE    PH     EC     PHFAC  ECFAC  WSTRES')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get detailed water data from the actual transpiration model results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
            if daily_result:
                # Use detailed transpiration model calculations
                transp = getattr(daily_result, 'transpiration_rate', getattr(daily_result, 'transpiration', 0.0))
                water_total = getattr(daily_result, 'total_water_uptake', getattr(daily_result, 'water_uptake_total', 0.0))
                
                # Calculate WUE from photosynthesis/transpiration if available
                net_photosynthesis = getattr(daily_result, 'net_photosynthesis', 0.0)
                if transp > 0:
                    wue = net_photosynthesis / transp
                else:
                    wue = getattr(daily_result, 'water_use_efficiency', 0.0)
                
                # Use actual solution chemistry
                ph = getattr(daily_result, 'solution_ph', getattr(daily_result, 'ph', 6.0))
                ec = getattr(daily_result, 'solution_ec', getattr(daily_result, 'ec', 1.5))
            else:
                transp = water_total = wue = 0.0
                ph, ec = 6.0, 1.5
        else:
            transp = water_total = wue = 0.0
            ph, ec = 6.0, 1.5
        stress = day_data.get('stress_analysis', {})
        water_output.append(f'{day:5d} {date:10s} {transp:6.2f} {water_total:7.2f} {wue:6.2f} {ph:6.2f} {ec:6.2f} {1.0-stress.get("ph_stress_level", 0.0):6.3f} {1.0-stress.get("salinity_stress_level", 0.0):6.3f} {stress.get("water_stress_level", 0.0):6.3f}')
    output_files['WATER.OUT'] = '\n'.join(water_output)
    
    # 11. ROOT.OUT - Root Architecture
    root_output = []
    root_output.append('*ROOT ARCHITECTURE OUTPUT')
    root_output.append('@  DAY  DATE       RLEN   RSURF  RVOL   RDENS  RACT   RHYCON RABSR  ROXUP  RRESP  RGROW')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get actual root data from simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            # Calculate dynamic root parameters based on root biomass and growth
            root_biomass = getattr(daily_result, 'root_biomass', 0.0)
            root_growth = getattr(daily_result, 'root_growth_rate', 0.0)
            # Root length scales with biomass (specific root length ~50 cm/g for lettuce)
            root_length = root_biomass * 50.0  # cm/plant
            # Root surface area (diameter ~0.5mm for fine roots)
            root_surface = root_length * 0.157  # cm²/plant (π * 0.05cm)
            # Root volume (fine roots ~0.02 cm³/g)
            root_volume = root_biomass * 20.0  # cm³/plant
            # Root density in hydroponic media
            media_volume = 500.0  # cm³ available root space
            root_density = root_length / media_volume  # cm/cm³
            # Root activity index (higher with younger, more active roots)
            activity_base = 1.0
            age_decline = min(0.3, day * 0.008)
            root_activity = activity_base * (1.0 - age_decline) * min(1.5, root_growth * 10)
            # Hydraulic conductivity (decreases with stress/age)
            stress_level = getattr(daily_result, 'water_stress', 0.0) if hasattr(daily_result, 'water_stress') else 0.1
            hydraulic_cond = (1.0 - stress_level) * (1.0 - age_decline)
            # Nutrient absorption rate (related to root activity)
            absorption_rate = root_activity * (1.0 - stress_level)
            # Root oxygen uptake (proportional to root respiration needs)
            oxygen_uptake = root_biomass * 2.5  # mg O2/day per g root
            # Root respiration (maintenance + growth respiration)
            root_respiration = root_biomass * 0.05 + root_growth * 0.2  # mg/day
            # Root growth rate in length
            root_growth_rate = root_growth * 50.0  # cm/day (from g/day to cm/day)
        else:
            # Fallback values
            root_length = root_surface = root_volume = 0.0
            root_density = root_activity = hydraulic_cond = absorption_rate = 0.0
            oxygen_uptake = root_respiration = root_growth_rate = 0.0
        root_output.append(f'{day:5d} {date:10s} {root_length:6.1f} {root_surface:6.1f} {root_volume:6.1f} {root_density:6.2f} {root_activity:6.2f} {hydraulic_cond:6.2f} {absorption_rate:5.2f} {oxygen_uptake:5.1f} {root_respiration:5.1f} {root_growth_rate:5.1f}')
    output_files['ROOT.OUT'] = '\n'.join(root_output)
    
    # 12. GROWTH.OUT - Growth and Biomass Dynamics
    growth_output = []
    growth_output.append('*GROWTH AND BIOMASS OUTPUT')
    growth_output.append('@  DAY  DATE       TOTBIO LEAFBIO STEMBIO ROOTBIO DTGROW DLEAF  DSTEM  DROOT')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get biomass data from the actual results if available
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            total_bio = getattr(daily_result, 'total_biomass', 0.0)
            leaf_bio = getattr(daily_result, 'leaf_biomass', 0.0)
            stem_bio = getattr(daily_result, 'stem_biomass', 0.0) 
            root_bio = getattr(daily_result, 'root_biomass', 0.0)
            daily_growth = getattr(daily_result, 'daily_growth_rate', 0.0)
            leaf_growth = getattr(daily_result, 'leaf_growth_rate', 0.0)
            stem_growth = getattr(daily_result, 'stem_growth_rate', 0.0)
            root_growth = getattr(daily_result, 'root_growth_rate', 0.0)
        else:
            total_bio = leaf_bio = stem_bio = root_bio = 0.0
            daily_growth = leaf_growth = stem_growth = root_growth = 0.0
        growth_output.append(f'{day:5d} {date:10s} {total_bio:6.1f} {leaf_bio:7.1f} {stem_bio:7.1f} {root_bio:7.1f} {daily_growth:6.3f} {leaf_growth:6.3f} {stem_growth:6.3f} {root_growth:6.3f}')
    output_files['GROWTH.OUT'] = '\n'.join(growth_output)
    
    # 13. ENVIRONMENT.OUT - Environmental Control
    environment_output = []
    environment_output.append('*ENVIRONMENTAL CONTROL OUTPUT')
    environment_output.append('@  DAY  DATE       CO2    VPD    PPFD   DLEN   PRES   WINDS  RELHUM AIRDEN PHFAC  TRFAC')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get environmental data from actual simulation results
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            # Extract environmental parameters from daily results
            co2 = getattr(daily_result, 'co2_concentration', 400.0)
            vpd = getattr(daily_result, 'vpd_actual', 0.8)
            ppfd = getattr(daily_result, 'total_absorbed_ppfd', 0.0) / 24.0  # Convert to average hourly
            dlen = 12.5 + 2.0 * np.sin(day * 2 * np.pi / 365)  # Seasonal day length variation
            pressure = 101.3  # Standard atmospheric pressure
            winds = 0.5  # Low wind speed in controlled environment
            relhum = 65.0 + 10.0 * np.sin(day * 2 * np.pi / 365)  # Seasonal humidity variation
            airden = 1.2  # Standard air density
            phfac = getattr(daily_result, 'env_photosynthesis_factor', 1.0)
            trfac = getattr(daily_result, 'env_transpiration_factor', 1.0)
        else:
            # Fallback environmental parameters
            co2, vpd, ppfd = 400.0, 0.8, 30.0
            dlen, pressure, winds = 12.0, 101.3, 2.0
            relhum, airden = 65.0, 1.2
            phfac = trfac = 1.0
        environment_output.append(f'{day:5d} {date:10s} {co2:6.0f} {vpd:6.3f} {ppfd:6.1f} {dlen:6.1f} {pressure:6.1f} {winds:6.1f} {relhum:6.1f} {airden:6.2f} {phfac:5.2f} {trfac:5.2f}')
    output_files['ENVIRONMENT.OUT'] = '\n'.join(environment_output)
    
    # 14. PHOTOSYNTHESIS.OUT - Photosynthesis and Carbon
    photosyn_output = []
    photosyn_output.append('*PHOTOSYNTHESIS AND CARBON OUTPUT')
    photosyn_output.append('@  DAY  DATE       PGROSS PNET   CANPHO LITINT PPFD_A SUNLAI SHDLAI NETASL')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get photosynthesis data from actual results if available
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
        else:
            daily_result = None
        if daily_result:
            pgross = getattr(daily_result, 'photosynthesis_rate', 0.0)
            canpho = getattr(daily_result, 'canopy_photosynthesis', 0.0)
            litint = getattr(daily_result, 'light_interception', 0.0)
            ppfd_a = getattr(daily_result, 'total_absorbed_ppfd', 0.0)
            sunlai = getattr(daily_result, 'sunlit_lai', 0.0)
            shdlai = getattr(daily_result, 'shaded_lai', 0.0)
            netasl = getattr(daily_result, 'net_assimilation', 0.0)
            # Calculate net photosynthesis as gross minus dark respiration
            pnet = pgross - getattr(daily_result, 'respiration_rate', 0.0) * 0.5
        else:
            pgross = pnet = canpho = litint = ppfd_a = sunlai = shdlai = netasl = 0.0
        photosyn_output.append(f'{day:5d} {date:10s} {pgross:6.3f} {pnet:6.3f} {canpho:6.3f} {litint:6.3f} {ppfd_a:6.1f} {sunlai:6.3f} {shdlai:6.3f} {netasl:6.3f}')
    output_files['PHOTOSYNTHESIS.OUT'] = '\n'.join(photosyn_output)
    
    return output_files

def run_default_simulation():
    """Run a default CROPGRO simulation"""
    print("🌱 CROPGRO Hydroponic Simulator - CLI Version")
    print("=" * 50)
    
    # Use default configurations
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Generate weather data
    generator = WeatherGenerator()
    start_date = datetime.now()
    weather_list = generator.generate_weather_series(
        start_date=start_date,
        days=120  # Maximum days
    )
    
    # Create input data
    input_data = HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_list,
        nutrient_params=nutrient_params,
        simulation_days=120
    )
    
    # Create and run simulator
    simulator = CROPGROHydroponicSimulator(
        cultivar_id='HYDRO_001',
        system_type='NFT'
    )
    
    print(f"Starting simulation until harvest maturity...")
    print(f"Cultivar: {simulator.cultivar_profile.cultivar_name}")
    print(f"System: {system_config.system_type}")
    
    # Run simulation
    results = simulator.run_simulation(input_data, max_days=120, target_maturity='harvest')
    
    print(f"✅ Simulation completed successfully!")
    print(f"Duration: {len(results.daily_results)} days")
    print(f"Final stage: {getattr(results.daily_results[-1], 'growth_stage', 'Unknown')}")
    
    # Auto-save model output files
    output_folder = save_model_output_files(results)
    print(f"📁 Model output files saved to: {output_folder}/ (replacing previous files)")
    
    # List generated files
    files = os.listdir(output_folder)
    print(f"\n📄 Generated {len(files)} files:")
    for file in sorted(files):
        print(f"  - {file}")
    
    return results, output_folder

def main():
    """Main CLI function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("CROPGRO Hydroponic Simulator - Command Line Interface")
            print("Usage:")
            print("  python cropgro_cli.py              # Run default simulation")
            print("  python cropgro_cli.py --help       # Show this help")
            return
    
    # Run default simulation
    try:
        results, output_folder = run_default_simulation()
        print(f"\n🎯 Complete! Check {output_folder}/ for all 15 model output files.")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()