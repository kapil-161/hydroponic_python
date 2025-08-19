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
        genetics = day_data.get('genetic_parameters', {})
        genetic_output.append(f'{day:5d} {date:10s} {genetics.get("cultivar_adaptation_index", 1.0):6.3f} {genetics.get("yield_potential_index", 1.0):6.3f} {genetics.get("photosynthesis_capacity_index", 1.0):5.3f} {genetics.get("growth_rate_potential", 1.0):5.3f} {genetics.get("maturity_index", 1.0):6.3f} {genetics.get("stress_resistance_index", 1.0):5.3f} {genetics.get("nutrient_efficiency_index", 1.0):6.3f} {genetics.get("water_efficiency_index", 1.0):6.3f} {genetics.get("temperature_tolerance_index", 1.0):6.3f}')
    output_files['GENETIC.OUT'] = '\n'.join(genetic_output)
    
    # 2. PHENOLOGY.OUT - Phenology Development
    phenology_output = []
    phenology_output.append('*PHENOLOGY DEVELOPMENT OUTPUT')
    phenology_output.append('@  DAY  DATE       STAGE  STGNAM             GDD   DGDD  BTEMP OTEMP CTEMP  DVIND ISVEGET ISREPRO')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        pheno = day_data.get('phenology_development', {})
        phenology_output.append(f'{day:5d} {date:10s} {pheno.get("growth_stage_code", "VE"):6s} {pheno.get("growth_stage_name", "Emergence")[:18]:18s} {pheno.get("accumulated_gdd_c", 0.0):5.1f} {pheno.get("daily_gdd_c", 0.0):4.1f} {pheno.get("base_temperature_c", 5.0):5.1f} {pheno.get("optimal_temperature_c", 21.0):5.1f} {pheno.get("ceiling_temperature_c", 35.0):5.1f} {pheno.get("development_index", 0.0):5.3f} {"Y" if pheno.get("is_vegetative_phase", True) else "N":7s} {"Y" if pheno.get("is_reproductive_phase", False) else "N":7s}')
    output_files['PHENOLOGY.OUT'] = '\n'.join(phenology_output)
    
    # 3. RESPIRATION.OUT - Respiration Analysis
    respiration_output = []
    respiration_output.append('*RESPIRATION ANALYSIS OUTPUT')
    respiration_output.append('@  DAY  DATE       GRESP  MRESP  TRESP  DRESP  PRESP  NETAS  CARBAL RSPEFF')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        physio = day_data.get('physiological_processes', {})
        respiration_output.append(f'{day:5d} {date:10s} {physio.get("growth_respiration_g_day", 0.0):6.3f} {physio.get("maintenance_respiration_g_day", 0.0):6.3f} {physio.get("total_respiration_g_day", 0.0):6.3f} {physio.get("dark_respiration_umol_m2_s", 0.0):6.3f} {physio.get("photorespiration_umol_m2_s", 0.0):6.3f} {physio.get("net_assimilation_g_day", 0.0):6.3f} {physio.get("carbon_balance_g_day", 0.0):6.3f} {physio.get("photosynthetic_efficiency", 0.05):6.4f}')
    output_files['RESPIRATION.OUT'] = '\n'.join(respiration_output)
    
    # 4. SENESCENCE.OUT - Senescence Model  
    senescence_output = []
    senescence_output.append('*SENESCENCE MODEL OUTPUT')
    senescence_output.append('@  DAY  DATE       GLAI   DLAI   TOTLAI LEAFNO GLNO   DLNO   SENESF LEAFAGE')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        canopy = day_data.get('canopy_architecture', {})
        senescence_output.append(f'{day:5d} {date:10s} {canopy.get("green_lai_m2_m2", 0.0):6.3f} {canopy.get("dead_lai_m2_m2", 0.0):6.3f} {canopy.get("leaf_area_index_m2_m2", 0.0):7.3f} {canopy.get("leaf_number_total", 8):6d} {canopy.get("leaf_number_green", 7):6d} {canopy.get("leaf_number_senesced", 1):6d} {day_data.get("genetic_parameters", {}).get("senescence_rate_factor", 1.0):6.3f} {day * 1.0:7.1f}')
    output_files['SENESCENCE.OUT'] = '\n'.join(senescence_output)
    
    # 5. CANOPY.OUT - Canopy Architecture
    canopy_output = []
    canopy_output.append('*CANOPY ARCHITECTURE OUTPUT')
    canopy_output.append('@  DAY  DATE       LAI    HEIGHT WIDTH  DEPTH  VOLUME LIGHTINT EXTCOEF CTEMP  LTEMP  COND')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        canopy = day_data.get('canopy_architecture', {})
        canopy_output.append(f'{day:5d} {date:10s} {canopy.get("leaf_area_index_m2_m2", 0.0):6.3f} {canopy.get("canopy_height_cm", 8.0):6.1f} {canopy.get("canopy_width_cm", 9.6):6.1f} {canopy.get("canopy_depth_cm", 6.4):6.1f} {canopy.get("canopy_volume_cm3", 500.0):7.1f} {canopy.get("light_interception_fraction", 0.0):8.3f} {canopy.get("light_extinction_coefficient", 0.7):7.3f} {canopy.get("canopy_temperature_c", 22.0):6.1f} {canopy.get("leaf_temperature_c", 23.0):6.1f} {canopy.get("canopy_conductance_mol_m2_s", 0.3):6.3f}')
    output_files['CANOPY.OUT'] = '\n'.join(canopy_output)
    
    # 6. NITROGEN.OUT - Nitrogen Balance
    nitrogen_output = []
    nitrogen_output.append('*NITROGEN BALANCE OUTPUT')
    nitrogen_output.append('@  DAY  DATE       NUPTAK NDEMAND NSUPPLY NUEEFF LEAFNC STEMNC ROOTNC CRITC  DEFIC')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        nitrogen = day_data.get('nitrogen_dynamics', {})
        nitrogen_output.append(f'{day:5d} {date:10s} {nitrogen.get("nitrogen_uptake_mg_plant_day", 0.0):7.3f} {nitrogen.get("nitrogen_demand_mg_plant_day", 0.0):7.3f} {nitrogen.get("nitrogen_supply_mg_plant_day", 0.0):7.3f} {nitrogen.get("nitrogen_use_efficiency_g_g", 30.0):6.1f} {nitrogen.get("leaf_nitrogen_conc_percent", 4.5):6.2f} {nitrogen.get("stem_nitrogen_conc_percent", 2.5):6.2f} {nitrogen.get("root_nitrogen_conc_percent", 2.0):6.2f} {nitrogen.get("critical_nitrogen_conc_percent", 4.0):5.2f} {nitrogen.get("nitrogen_deficit_mg_plant", 0.0):5.1f}')
    output_files['NITROGEN.OUT'] = '\n'.join(nitrogen_output)
    
    # 7. NUTRIENT.OUT - Nutrient Mobility
    nutrient_output = []
    nutrient_output.append('*NUTRIENT MOBILITY OUTPUT')
    nutrient_output.append('@  DAY  DATE       NO3    NH4    PO4    K      CA     MG     FE     MN     ZN')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        nutrients = day_data.get('nutrient_concentrations', {})
        nutrient_output.append(f'{day:5d} {date:10s} {nutrients.get("nitrate_no3_mg_l", 200.0):6.1f} {nutrients.get("ammonium_nh4_mg_l", 10.0):6.1f} {nutrients.get("phosphate_po4_mg_l", 50.0):6.1f} {nutrients.get("potassium_k_mg_l", 300.0):6.1f} {nutrients.get("calcium_ca_mg_l", 150.0):6.1f} {nutrients.get("magnesium_mg_mg_l", 50.0):6.1f} {nutrients.get("iron_fe_mg_l", 2.0):6.2f} {nutrients.get("manganese_mn_mg_l", 0.5):6.2f} {nutrients.get("zinc_zn_mg_l", 0.3):6.2f}')
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
        temperature_output.append(f'{day:5d} {date:10s} {basic.get("temperature_avg_c", 22.0):6.1f} {basic.get("temperature_min_c", 17.0):6.1f} {basic.get("temperature_max_c", 30.0):6.1f} {basic.get("temperature_amplitude_c", 13.0):6.1f} {canopy.get("leaf_temperature_c", 23.0):6.1f} {canopy.get("canopy_temperature_c", 22.0):7.1f} {stress.get("cold_stress_level", 0.0):6.3f} {stress.get("heat_stress_level", 0.0):6.3f} {stress.get("temperature_stress_level", 0.0):6.3f}')
    output_files['TEMPERATURE.OUT'] = '\n'.join(temperature_output)
    
    # 10. WATER.OUT - Water Dynamics
    water_output = []
    water_output.append('*WATER UPTAKE AND TRANSPIRATION OUTPUT')
    water_output.append('@  DAY  DATE       TRANSP WUP_TOT WUE    PH     EC     PHFAC  ECFAC  WSTRES')
    for day_data in daily_results:
        day = day_data['day']
        date = day_data['date']
        # Get water data from the actual results if available
        if results and hasattr(results, 'daily_results'):
            daily_result = next((r for r in results.daily_results if r.day == day), None)
            if daily_result:
                transp = getattr(daily_result, 'transpiration', 0.0)
                water_total = getattr(daily_result, 'water_uptake_total', 0.0)
                wue = getattr(daily_result, 'water_use_efficiency', 0.0)
                ph = getattr(daily_result, 'ph', 6.0)
                ec = getattr(daily_result, 'ec', 1.5)
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
        root = day_data.get('root_zone_dynamics', {})
        root_output.append(f'{day:5d} {date:10s} {root.get("root_length_cm_plant", 150.0):6.1f} {root.get("root_surface_area_cm2_plant", 80.0):6.1f} {root.get("root_volume_cm3_plant", 8.0):6.1f} {root.get("root_density_cm_cm3", 0.5):6.2f} {root.get("root_activity_index", 1.0):6.2f} {root.get("root_hydraulic_conductivity", 1.0):6.2f} {root.get("root_nutrient_absorption_rate", 1.0):5.2f} {root.get("root_oxygen_uptake_mg_day", 5.0):5.1f} {root.get("root_respiration_mg_day", 0.5):5.1f} {root.get("root_growth_rate_cm_day", 2.0):5.1f}')
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
        basic = day_data.get('basic_environment', {})
        env = day_data.get('environmental_factors', {})
        environment_output.append(f'{day:5d} {date:10s} {basic.get("co2_concentration_ppm", 400.0):6.0f} {basic.get("vpd_kpa", 0.8):6.3f} {basic.get("ppfd_mol_m2_day", 30.0):6.1f} {basic.get("daylength_hours", 12.0):6.1f} {basic.get("atmospheric_pressure_kpa", 101.3):6.1f} {basic.get("wind_speed_ms", 2.0):6.1f} {basic.get("relative_humidity_percent", 65.0):6.1f} {basic.get("air_density_kg_m3", 1.2):6.2f} {env.get("env_photosynthesis_factor", 1.0):5.2f} {env.get("env_transpiration_factor", 1.0):5.2f}')
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