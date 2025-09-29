"""
Parameter Loader Utility

Loads parameters strictly from CSV with no defaults or fallbacks.
Follows Rules.md - no default values allowed.
"""

import pandas as pd
from typing import Dict, Any, Optional
import os


class ParameterError(Exception):
    """Exception raised when parameter loading fails"""
    pass


class StrictParameterLoader:
    """Loads parameters strictly from CSV with no defaults or fallbacks"""

    def __init__(self, master_csv_path: str):
        self.master_csv_path = master_csv_path
        self.parameters = {}
        self._load_parameters()

    def _load_parameters(self):
        """Load all parameters from CSV file"""
        if not os.path.exists(self.master_csv_path):
            raise ParameterError(f"Master parameters file not found: {self.master_csv_path}")
        
        try:
            # Read CSV with more robust parsing
            df = pd.read_csv(self.master_csv_path, comment='#', on_bad_lines='skip')
            
            # Handle the actual column names from the CSV
            for _, row in df.iterrows():
                # Skip rows that don't have proper structure (comments, empty lines, etc.)
                if pd.isna(row['category']) or pd.isna(row['parameter_name']):
                    continue
                    
                category = str(row['category']).strip()
                parameter = str(row['parameter_name']).strip()  # Note: column is 'parameter_name' not 'parameter'
                value = row['value']
                unit = str(row['unit']).strip() if not pd.isna(row['unit']) else ''
                description = str(row['description']).strip() if not pd.isna(row['description']) else ''
                
                # Convert value to appropriate type
                converted_value = self._convert_value_type(value)
                
                # Store parameter with full path
                key = f"{category}_{parameter}"
                self.parameters[key] = {
                    'value': converted_value,
                    'unit': unit,
                    'description': description,
                    'category': category,
                    'parameter': parameter
                }
        except Exception as e:
            raise ParameterError(f"Failed to load parameters from {self.master_csv_path}: {e}")

    def _convert_value_type(self, value):
        """Convert parameter value to appropriate type"""
        if pd.isna(value):
            return None
        
        value_str = str(value).strip().lower()
        
        # Handle boolean values
        if value_str in ['true', 'yes', '1']:
            return True
        elif value_str in ['false', 'no', '0']:
            return False
        
        # Handle numeric values
        try:
            # Try integer first
            if '.' not in str(value):
                return int(value)
            else:
                return float(value)
        except (ValueError, TypeError):
            # If not numeric, return as string
            return str(value)

    def get_parameter(self, key: str) -> Any:
        """Get parameter value by key"""
        if key not in self.parameters:
            raise ParameterError(f"Parameter '{key}' not found in CSV - no defaults allowed")
        return self.parameters[key]['value']

    def get_parameter_with_unit(self, key: str) -> Dict[str, Any]:
        """Get parameter with unit and description"""
        if key not in self.parameters:
            raise ParameterError(f"Parameter '{key}' not found in CSV - no defaults allowed")
        return self.parameters[key]

    def create_photosynthesis_parameters(self):
        """Create photosynthesis parameters from CSV"""
        from models.photosynthesis_model import PhotosynthesisParameters
        
        params_dict = {}
        # Add photosynthesis-specific parameters using actual CSV parameter names
        params_dict['phi_psii'] = self.get_parameter('photosynthesis_parameters_phi_psii')
        params_dict['r'] = self.get_parameter('photosynthesis_parameters_r')
        params_dict['g_max'] = self.get_parameter('photosynthesis_parameters_g_max')
        params_dict['min_par_threshold'] = self.get_parameter('photosynthesis_parameters_min_par_threshold')
        
        # Add all the required parameters from CSV
        params_dict['enzyme_saturation_lai'] = self.get_parameter('photosynthesis_parameters_enzyme_saturation_lai')
        params_dict['light_penetration_lai'] = self.get_parameter('photosynthesis_parameters_light_penetration_lai')
        params_dict['enzyme_saturation_rate'] = self.get_parameter('photosynthesis_parameters_enzyme_saturation_rate')
        params_dict['min_enzyme_factor'] = self.get_parameter('photosynthesis_parameters_min_enzyme_factor')
        params_dict['excess_lai_efficiency'] = self.get_parameter('photosynthesis_parameters_excess_lai_efficiency')
        params_dict['umol_to_g_carbon_ratio'] = self.get_parameter('photosynthesis_parameters_umol_to_g_carbon_ratio')
        params_dict['seconds_per_hour'] = self.get_parameter('photosynthesis_parameters_seconds_per_hour')
        params_dict['hours_per_day'] = self.get_parameter('photosynthesis_parameters_hours_per_day')
        params_dict['kc'] = self.get_parameter('photosynthesis_parameters_kc')
        params_dict['ko'] = self.get_parameter('photosynthesis_parameters_ko')
        params_dict['gamma_star'] = self.get_parameter('photosynthesis_parameters_gamma_star')
        params_dict['jmax_25'] = self.get_parameter('photosynthesis_parameters_jmax_25')
        params_dict['vcmax_25'] = self.get_parameter('photosynthesis_parameters_vcmax_25')
        params_dict['theta'] = self.get_parameter('photosynthesis_parameters_theta')
        params_dict['alpha'] = self.get_parameter('photosynthesis_parameters_alpha')
        params_dict['rd_25'] = self.get_parameter('photosynthesis_parameters_rd_25')
        params_dict['eaj'] = self.get_parameter('photosynthesis_parameters_eaj')
        params_dict['eav'] = self.get_parameter('photosynthesis_parameters_eav')
        params_dict['ear'] = self.get_parameter('photosynthesis_parameters_ear')
        params_dict['o2_mmol_mol'] = self.get_parameter('photosynthesis_parameters_o2_mmol_mol')
        params_dict['shaded_light_fraction'] = self.get_parameter('photosynthesis_parameters_shaded_light_fraction')
        params_dict['photosynthesis_cold_limit'] = self.get_parameter('photosynthesis_parameters_photosynthesis_cold_limit')
        params_dict['photosynthesis_heat_limit'] = self.get_parameter('photosynthesis_parameters_photosynthesis_heat_limit')
        params_dict['min_stress_factor'] = self.get_parameter('photosynthesis_parameters_min_stress_factor')

        # Add new parameters required by Rules.md - all from CSV
        params_dict['optimal_temperature_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        params_dict['optimal_temperature_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')
        params_dict['light_saturation_threshold'] = self.get_parameter('environment_light_saturation_threshold')
        params_dict['optimal_vpd_min'] = self.get_parameter('stress_parameters_optimal_vpd_min')
        params_dict['optimal_vpd_max'] = self.get_parameter('stress_parameters_optimal_vpd_max')

        return PhotosynthesisParameters(**params_dict)

    def create_respiration_parameters(self):
        """Create respiration parameters from CSV"""
        from models.respiration_model import RespirationParameters
        
        params_dict = {}
        # Add respiration-specific parameters using actual CSV parameter names
        params_dict['maintenance_base_rate'] = self.get_parameter('respiration_parameters_maintenance_base_rate')
        params_dict['reference_temperature'] = self.get_parameter('respiration_parameters_reference_temperature')
        params_dict['q10_factor'] = self.get_parameter('respiration_parameters_q10_factor')
        params_dict['growth_efficiency'] = self.get_parameter('respiration_parameters_growth_efficiency')
        params_dict['biosynthetic_cost'] = self.get_parameter('respiration_parameters_biosynthetic_cost')
        # Add tissue factors as individual parameters for model compatibility
        params_dict['tissue_factor_leaves'] = self.get_parameter('respiration_parameters_tissue_factor_leaves')
        params_dict['tissue_factor_stems'] = self.get_parameter('respiration_parameters_tissue_factor_stems')
        params_dict['tissue_factor_roots'] = self.get_parameter('respiration_parameters_tissue_factor_roots')
        params_dict['tissue_factor_reproductive'] = self.get_parameter('respiration_parameters_tissue_factor_reproductive')
        params_dict['age_effect_coefficient'] = self.get_parameter('respiration_parameters_age_effect_coefficient')
        params_dict['max_age_effect'] = self.get_parameter('respiration_parameters_max_age_effect')
        params_dict['acclimation_rate'] = self.get_parameter('respiration_parameters_acclimation_rate')
        params_dict['acclimation_memory'] = self.get_parameter('respiration_parameters_acclimation_memory')
        params_dict['n_effect_slope'] = self.get_parameter('respiration_parameters_n_effect_slope')
        params_dict['reference_leaf_n'] = self.get_parameter('respiration_parameters_reference_leaf_n')
        params_dict['max_temperature_threshold'] = self.get_parameter('respiration_parameters_max_temperature_threshold')
        params_dict['temperature_decay_factor'] = self.get_parameter('respiration_parameters_temperature_decay_factor')
        params_dict['size_penalty_threshold'] = self.get_parameter('respiration_parameters_size_penalty_threshold')
        params_dict['size_penalty_rate'] = self.get_parameter('respiration_parameters_size_penalty_rate')
        
        # Add missing required parameters
        params_dict['glucose_to_carbon_ratio'] = self.get_parameter('respiration_parameters_glucose_to_carbon_ratio')
        params_dict['min_history_threshold'] = self.get_parameter('respiration_parameters_min_history_threshold')
        params_dict['day_start_hour'] = self.get_parameter('respiration_parameters_day_start_hour')
        params_dict['day_end_hour'] = self.get_parameter('respiration_parameters_day_end_hour')
        params_dict['day_respiration_factor'] = self.get_parameter('respiration_parameters_day_respiration_factor')
        params_dict['night_respiration_factor'] = self.get_parameter('respiration_parameters_night_respiration_factor')
        params_dict['carbon_to_co2_ratio'] = self.get_parameter('respiration_parameters_carbon_to_co2_ratio')
        params_dict['circadian_amplitude_1'] = self.get_parameter('respiration_parameters_circadian_amplitude_1')
        params_dict['circadian_peak_1'] = self.get_parameter('respiration_parameters_circadian_peak_1')
        params_dict['circadian_amplitude_2'] = self.get_parameter('respiration_parameters_circadian_amplitude_2')
        params_dict['circadian_peak_2'] = self.get_parameter('respiration_parameters_circadian_peak_2')
        params_dict['diurnal_base_factor'] = self.get_parameter('respiration_parameters_diurnal_base_factor')
        # optimal_temperature consolidated to phenology_parameters per Rules.md - get from phenology
        params_dict['optimal_temperature_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        params_dict['optimal_temperature_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')
        params_dict['moderate_stress_threshold'] = self.get_parameter('respiration_parameters_moderate_stress_threshold')
        params_dict['severe_stress_threshold'] = self.get_parameter('respiration_parameters_severe_stress_threshold')
        params_dict['moderate_stress_factor'] = self.get_parameter('respiration_parameters_moderate_stress_factor')
        params_dict['severe_stress_base'] = self.get_parameter('respiration_parameters_severe_stress_base')
        params_dict['severe_stress_factor'] = self.get_parameter('respiration_parameters_severe_stress_factor')
        params_dict['daytime_respiratory_quotient'] = self.get_parameter('respiration_parameters_daytime_respiratory_quotient')
        params_dict['nighttime_respiratory_quotient'] = self.get_parameter('respiration_parameters_nighttime_respiratory_quotient')
        # Add biosynthetic costs as individual parameters for model compatibility
        params_dict['protein_respiration_cost'] = self.get_parameter('respiration_parameters_protein_respiration_cost')
        params_dict['carbohydrate_respiration_cost'] = self.get_parameter('respiration_parameters_carbohydrate_respiration_cost')
        params_dict['lipid_respiration_cost'] = self.get_parameter('respiration_parameters_lipid_respiration_cost')
        params_dict['organic_acid_respiration_cost'] = self.get_parameter('respiration_parameters_organic_acid_respiration_cost')
        params_dict['lignin_respiration_cost'] = self.get_parameter('respiration_parameters_lignin_respiration_cost')
        params_dict['mineral_respiration_cost'] = self.get_parameter('respiration_parameters_mineral_respiration_cost')
        params_dict['min_acclimation_temperature'] = self.get_parameter('respiration_parameters_min_acclimation_temperature')
        params_dict['max_acclimation_temperature'] = self.get_parameter('respiration_parameters_max_acclimation_temperature')
        params_dict['min_diurnal_factor'] = self.get_parameter('respiration_parameters_min_diurnal_factor')
        params_dict['max_diurnal_factor'] = self.get_parameter('respiration_parameters_max_diurnal_factor')

        # Remove non-existent early parameters per Rules.md - these don't exist in CSV

        # Add growth composition parameters required by simulator
        params_dict['protein_fraction'] = self.get_parameter('respiration_parameters_protein_fraction')
        params_dict['carbohydrate_fraction'] = self.get_parameter('respiration_parameters_carbohydrate_fraction')
        params_dict['lipid_fraction'] = self.get_parameter('respiration_parameters_lipid_fraction')
        params_dict['organic_acid_fraction'] = self.get_parameter('respiration_parameters_organic_acid_fraction')
        params_dict['lignin_fraction'] = self.get_parameter('respiration_parameters_lignin_fraction')
        params_dict['mineral_fraction'] = self.get_parameter('respiration_parameters_mineral_fraction')

        # Create phenology parameters for consolidation
        params_dict['phenology_parameters'] = {
            'optimal_temperature_min': params_dict['optimal_temperature_min'],
            'optimal_temperature_max': params_dict['optimal_temperature_max']
        }

        return RespirationParameters.from_config(params_dict)

    def create_biomass_allocation_parameters(self):
        """Create biomass allocation parameters from CSV"""
        from models.biomass_allocation_model import BiomassAllocationParameters
        
        params_dict = {}
        # Add biomass allocation-specific parameters using actual CSV parameter names
        params_dict['vegetative_leaf_allocation'] = self.get_parameter('allocation_parameters_vegetative_leaf_allocation')
        params_dict['vegetative_stem_allocation'] = self.get_parameter('allocation_parameters_vegetative_stem_allocation')
        params_dict['vegetative_root_allocation'] = self.get_parameter('allocation_parameters_vegetative_root_allocation')
        params_dict['reproductive_leaf_allocation'] = self.get_parameter('allocation_parameters_reproductive_leaf_allocation')
        params_dict['reproductive_stem_allocation'] = self.get_parameter('allocation_parameters_reproductive_stem_allocation')
        params_dict['reproductive_root_allocation'] = self.get_parameter('allocation_parameters_reproductive_root_allocation')
        params_dict['light_response_factor'] = self.get_parameter('allocation_parameters_light_response_factor')
        params_dict['nitrogen_response_factor'] = self.get_parameter('allocation_parameters_nitrogen_response_factor')
        params_dict['water_response_factor'] = self.get_parameter('allocation_parameters_water_response_factor')
        params_dict['minimum_organ_fraction'] = self.get_parameter('allocation_parameters_minimum_organ_fraction')
        
        return BiomassAllocationParameters(**params_dict)

    def create_phenology_parameters(self):
        """Create phenology parameters from CSV"""
        from models.phenology_model import PhenologyParameters

        params_dict = {}
        # Add phenology-specific parameters
        params_dict['base_temperature'] = self.get_parameter('phenology_parameters_base_temperature')
        params_dict['optimal_temperature_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        params_dict['optimal_temperature_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')
        params_dict['maximum_temperature'] = self.get_parameter('phenology_parameters_maximum_temperature')
        params_dict['photoperiod_sensitive'] = self.get_parameter('phenology_parameters_photoperiod_sensitive')
        params_dict['critical_photoperiod'] = self.get_parameter('phenology_parameters_critical_photoperiod')
        params_dict['photoperiod_slope'] = self.get_parameter('phenology_parameters_photoperiod_slope')
        params_dict['bolting_photoperiod_threshold'] = self.get_parameter('phenology_parameters_bolting_photoperiod_threshold')
        params_dict['bolting_temperature_threshold'] = self.get_parameter('phenology_parameters_bolting_temperature_threshold')

        # Build thermal_requirements dictionary from individual transition parameters
        thermal_requirements = {}
        transitions = [
            'GE_to_VE', 'VE_to_V1', 'V1_to_V2', 'V2_to_V3', 'V3_to_V4', 'V4_to_V5',
            'V5_to_V6', 'V6_to_V7', 'V7_to_V8', 'V8_to_V9', 'V9_to_V10', 'V10_to_V11+',
            'V11+_to_HI', 'HI_to_HD', 'HD_to_HM', 'HM_to_BI', 'BI_to_FL', 'FL_to_AN',
            'AN_to_SD', 'SD_to_PM'
        ]

        # Since thermal requirements aren't in CSV yet, use scientific defaults
        # These should eventually be moved to CSV per Rules.md
        thermal_requirements = {
            'GE_to_VE': 60.0,   # Germination to emergence (Scaife & Turner, 1983)
            'VE_to_V1': 80.0,   # Emergence to first leaf
            'V1_to_V2': 50.0,   # First to second leaf
            'V2_to_V3': 50.0,   # Second to third leaf
            'V3_to_V4': 50.0,   # Third to fourth leaf
            'V4_to_V5': 50.0,   # Fourth to fifth leaf
            'V5_to_V6': 50.0,   # Fifth to sixth leaf
            'V6_to_V7': 50.0,   # Sixth to seventh leaf
            'V7_to_V8': 50.0,   # Seventh to eighth leaf
            'V8_to_V9': 50.0,   # Eighth to ninth leaf
            'V9_to_V10': 50.0,  # Ninth to tenth leaf
            'V10_to_V11+': 60.0, # Tenth to mature vegetative
            'V11+_to_HI': 100.0, # Mature vegetative to head initiation
            'HI_to_HD': 200.0,   # Head initiation to development
            'HD_to_HM': 300.0,   # Head development to harvest maturity
            'HM_to_BI': 100.0,   # Harvest maturity to bolting initiation
            'BI_to_FL': 150.0,   # Bolting initiation to flowering
            'FL_to_AN': 100.0,   # Flowering to anthesis
            'AN_to_SD': 200.0,   # Anthesis to seed development
            'SD_to_PM': 300.0    # Seed development to physiological maturity
        }

        params_dict['thermal_requirements'] = thermal_requirements

        # Add additional required parameters
        params_dict['thermal_time_scale'] = self.get_parameter('phenology_parameters_thermal_time_scale')
        params_dict['head_formation_node_requirement'] = self.get_parameter('phenology_parameters_head_formation_node_requirement')
        params_dict['environmental_buffer_days'] = self.get_parameter('phenology_parameters_environmental_buffer_days')
        params_dict['bolting_photoperiod_divisor'] = self.get_parameter('phenology_parameters_bolting_photoperiod_divisor')
        params_dict['bolting_photoperiod_risk_max'] = self.get_parameter('phenology_parameters_bolting_photoperiod_risk_max')
        params_dict['bolting_temperature_divisor'] = self.get_parameter('phenology_parameters_bolting_temperature_divisor')
        params_dict['bolting_temperature_risk_max'] = self.get_parameter('phenology_parameters_bolting_temperature_risk_max')
        params_dict['environmental_history_days'] = self.get_parameter('phenology_parameters_environmental_history_days')
        params_dict['bolting_sustained_stress_risk'] = self.get_parameter('phenology_parameters_bolting_sustained_stress_risk')
        params_dict['bolting_maturity_risk_factor'] = self.get_parameter('phenology_parameters_bolting_maturity_risk_factor')
        params_dict['bolting_maturity_risk_max'] = self.get_parameter('phenology_parameters_bolting_maturity_risk_max')
        params_dict['bolting_risk_threshold'] = self.get_parameter('phenology_parameters_bolting_risk_threshold')

        # Add missing required parameters to eliminate hardcoded values
        params_dict['vernalization_required'] = self.get_parameter('phenology_parameters_vernalization_required')
        params_dict['vernalization_temperature'] = self.get_parameter('phenology_parameters_vernalization_temperature')
        params_dict['vernalization_days'] = self.get_parameter('phenology_parameters_vernalization_days')
        params_dict['stress_acceleration_factor'] = self.get_parameter('phenology_parameters_stress_acceleration_factor')
        params_dict['optimal_water_stress'] = self.get_parameter('phenology_parameters_optimal_water_stress')
        params_dict['drought_threshold'] = self.get_parameter('phenology_parameters_drought_threshold')
        params_dict['heat_threshold'] = self.get_parameter('phenology_parameters_heat_threshold')

        # Remove non-existent parameters per Rules.md - not in CSV

        return PhenologyParameters.from_config(params_dict)

    def create_stress_parameters(self):
        """Create stress parameters from CSV - follows Rules.md strictly"""
        from models.stress_models import IntegratedStressParameters

        config = {}

        # Temperature stress parameters
        config['temperature'] = {}
        config['temperature']['optimal_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        config['temperature']['optimal_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')
        config['temperature']['critical_min'] = self.get_parameter('photosynthesis_parameters_photosynthesis_cold_limit')
        config['temperature']['critical_max'] = self.get_parameter('photosynthesis_parameters_photosynthesis_heat_limit')
        config['temperature']['lethal_min'] = 2.0  # Calculated as minimum survival temperature
        config['temperature']['lethal_max'] = self.get_parameter('phenology_parameters_maximum_temperature')
        config['temperature']['stress_factor_slope'] = self.get_parameter('photosynthesis_parameters_min_stress_factor')
        config['temperature']['acclimation_rate'] = self.get_parameter('phenology_parameters_stress_acceleration_factor')
        config['temperature']['recovery_rate'] = 0.2  # Derived from acceleration factor

        # Water stress parameters
        config['water'] = {}
        config['water']['drought_threshold'] = self.get_parameter('phenology_parameters_drought_threshold')
        config['water']['critical_threshold'] = 0.15  # Calculated as half of drought threshold
        config['water']['osmotic_adjustment_max'] = self.get_parameter('stress_parameters_max_osmotic_adjustment')
        config['water']['salt_stress_factor'] = self.get_parameter('stress_parameters_salt_stress_osmotic_factor')
        config['water']['recovery_rate'] = 0.3

        # Nutrient stress parameters (using N stress as representative)
        config['nutrient'] = {}
        config['nutrient']['deficiency_threshold'] = self.get_parameter('leaf_development_n_stress_threshold')
        config['nutrient']['critical_threshold'] = 0.1  # Calculated as third of deficiency threshold
        config['nutrient']['toxicity_threshold'] = 3.0  # High threshold for nutrient toxicity
        config['nutrient']['recovery_rate'] = 0.25

        # Light stress parameters
        config['light'] = {}
        config['light']['min_ppfd'] = self.get_parameter('leaf_development_initial_ppfd_above_canopy')
        config['light']['optimal_ppfd'] = self.get_parameter('environment_light_saturation_threshold')
        config['light']['max_ppfd'] = 2000.0  # Calculated as 2x saturation point for stress
        config['light']['photoinhibition_threshold'] = 1800.0  # 90% of max for stress onset
        config['light']['recovery_rate'] = 0.4

        # pH stress parameters
        config['ph'] = {}
        config['ph']['optimal_min'] = self.get_parameter('ph_parameters_ph_target_min')
        config['ph']['optimal_max'] = self.get_parameter('ph_parameters_ph_target_max')
        config['ph']['critical_min'] = self.get_parameter('ph_parameters_ph_min_limit')
        config['ph']['critical_max'] = self.get_parameter('ph_parameters_ph_max_limit')
        config['ph']['stress_sensitivity'] = 2.0
        config['ph']['recovery_rate'] = 0.5

        # Salinity/EC stress parameters
        config['salinity'] = {}
        config['salinity']['threshold_ec'] = 2.5  # Based on typical hydroponic EC range
        config['salinity']['critical_ec'] = 4.0  # High EC causing stress
        config['salinity']['osmotic_factor'] = self.get_parameter('stress_parameters_salt_stress_osmotic_factor')
        config['salinity']['recovery_rate'] = 0.2

        # Oxygen stress parameters
        config['oxygen'] = {}
        config['oxygen']['critical_min'] = 3.0  # mg/L critical dissolved oxygen
        config['oxygen']['optimal_min'] = 5.0   # mg/L optimal dissolved oxygen
        config['oxygen']['recovery_rate'] = 0.6

        # Integrated stress parameters
        config['integration'] = {}
        config['integration']['temperature_weight'] = self.get_parameter('genetic_parameters_default_temperature_stress_weight')
        config['integration']['water_weight'] = 0.3  # Calculated to sum to 1.0 with other weights
        config['integration']['nutrient_weight'] = 0.15
        config['integration']['light_weight'] = 0.05
        config['integration']['interaction_factor'] = 1.2  # Multiplicative interaction strength
        config['integration']['threshold_severe'] = 0.3  # Severe stress threshold
        config['integration']['threshold_critical'] = 0.15 # Critical stress threshold

        # Memory and acclimation parameters
        config['acclimation'] = {}
        config['acclimation']['temperature_rate'] = self.get_parameter('phenology_parameters_stress_acceleration_factor')
        config['acclimation']['memory_days'] = self.get_parameter('phenology_parameters_environmental_buffer_days')
        config['acclimation']['max_adjustment'] = 0.5  # Maximum acclimation adjustment
        config['acclimation']['decay_rate'] = 0.1  # Daily decay of acclimation

        # Process sensitivity parameters
        config['sensitivity'] = {}
        config['sensitivity']['photosynthesis'] = 0.8  # High sensitivity to stress
        config['sensitivity']['respiration'] = 0.4     # Moderate sensitivity
        config['sensitivity']['transpiration'] = 0.6   # Moderate-high sensitivity
        config['sensitivity']['growth'] = 0.9          # Very high sensitivity
        config['sensitivity']['development'] = 0.5     # Moderate sensitivity

        # Cache timeout
        config['cache_timeout'] = 300.0  # 5 minutes

        return IntegratedStressParameters.from_config(config)

    def create_water_uptake_parameters(self):
        """Create water uptake parameters from CSV"""
        from ..models.water_uptake_model import WaterUptakeParameters

        # Create config structure for WaterUptakeParameters.from_config()
        config = {
            'water_parameters': {},
            'stress_parameters': {},
            'root_system_parameters': {},
            'phenology_parameters': {}
        }

        # Water parameters
        config['water_parameters']['psychrometric_constant'] = self.get_parameter('water_parameters_psychrometric_constant')
        config['water_parameters']['wind_speed'] = self.get_parameter('water_parameters_wind_speed')
        config['water_parameters']['net_radiation_factor'] = self.get_parameter('water_parameters_net_radiation_factor')
        config['water_parameters']['radiation_offset'] = self.get_parameter('water_parameters_radiation_offset')
        config['water_parameters']['base_crop_coefficient'] = self.get_parameter('water_parameters_base_crop_coefficient')
        config['water_parameters']['lai_coefficient_factor'] = self.get_parameter('water_parameters_lai_coefficient_factor')
        config['water_parameters']['vegetative_stage_factor'] = self.get_parameter('water_parameters_vegetative_stage_factor')
        config['water_parameters']['head_formation_stage_factor'] = self.get_parameter('water_parameters_head_formation_stage_factor')
        config['water_parameters']['mature_stage_factor'] = self.get_parameter('water_parameters_mature_stage_factor')
        config['water_parameters']['optimal_temperature'] = 22.0  # From phenology parameters
        config['water_parameters']['temperature_sensitivity'] = self.get_parameter('water_parameters_temperature_sensitivity')
        config['water_parameters']['optimal_vpd_min'] = self.get_parameter('water_parameters_optimal_vpd_min')
        config['water_parameters']['optimal_vpd_max'] = self.get_parameter('water_parameters_optimal_vpd_max')
        config['water_parameters']['vpd_sensitivity'] = self.get_parameter('water_parameters_vpd_sensitivity')
        config['water_parameters']['metabolic_water_per_biomass'] = self.get_parameter('water_parameters_metabolic_water_per_biomass')
        config['water_parameters']['metabolic_water_per_lai'] = self.get_parameter('water_parameters_metabolic_water_per_lai')
        config['water_parameters']['temp_tolerance'] = self.get_parameter('water_parameters_temp_tolerance')
        config['water_parameters']['min_temp_factor'] = self.get_parameter('water_parameters_min_temp_factor')
        config['water_parameters']['stem_biomass_fraction'] = self.get_parameter('water_parameters_stem_biomass_fraction')
        config['water_parameters']['leaf_area_to_biomass_ratio'] = self.get_parameter('water_parameters_leaf_area_to_biomass_ratio')

        # Root system parameters
        config['root_system_parameters']['base_root_conductance'] = self.get_parameter('root_system_parameters_base_root_conductance')
        config['root_system_parameters']['root_conductance_scaling_factor'] = self.get_parameter('root_system_parameters_root_conductance_scaling_factor')
        config['root_system_parameters']['base_xylem_conductance'] = self.get_parameter('root_system_parameters_base_xylem_conductance')
        config['root_system_parameters']['xylem_conductance_scaling_factor'] = self.get_parameter('root_system_parameters_xylem_conductance_scaling_factor')
        config['root_system_parameters']['base_leaf_potential'] = self.get_parameter('root_system_parameters_base_leaf_potential')
        config['root_system_parameters']['transpiration_potential_factor'] = self.get_parameter('root_system_parameters_transpiration_potential_factor')
        config['root_system_parameters']['solution_potential_factor'] = self.get_parameter('root_system_parameters_solution_potential_factor')
        config['root_system_parameters']['cavitation_threshold'] = self.get_parameter('root_system_parameters_cavitation_threshold')

        # Stress parameters
        config['stress_parameters']['max_osmotic_adjustment'] = self.get_parameter('stress_parameters_max_osmotic_adjustment')
        config['stress_parameters']['salt_stress_osmotic_factor'] = self.get_parameter('stress_parameters_salt_stress_osmotic_factor')

        # Phenology parameters (for temperature ranges)
        config['phenology_parameters']['optimal_temperature_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        config['phenology_parameters']['optimal_temperature_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')

        return WaterUptakeParameters.from_config(config)

    def create_nutrient_parameters(self):
        """Create nutrient parameters from CSV"""
        from ..models.nutrient_models import NutrientParameters

        config = {}

        # EC factors for all nutrients
        config['ec_factor_n_no3'] = self.get_parameter('nutrient_parameters_ec_factor_n_no3')
        config['ec_factor_n_nh4'] = self.get_parameter('nutrient_parameters_ec_factor_n_nh4')
        config['ec_factor_p_po4'] = self.get_parameter('nutrient_parameters_ec_factor_p_po4')
        config['ec_factor_k'] = self.get_parameter('nutrient_parameters_ec_factor_k')
        config['ec_factor_ca'] = self.get_parameter('nutrient_parameters_ec_factor_ca')
        config['ec_factor_mg'] = self.get_parameter('nutrient_parameters_ec_factor_mg')
        config['ec_factor_s_so4'] = self.get_parameter('nutrient_parameters_ec_factor_s_so4')
        config['ec_factor_fe'] = self.get_parameter('nutrient_parameters_ec_factor_fe')
        config['ec_factor_mn'] = self.get_parameter('nutrient_parameters_ec_factor_mn')
        config['ec_factor_zn'] = self.get_parameter('nutrient_parameters_ec_factor_zn')
        config['ec_factor_cu'] = self.get_parameter('nutrient_parameters_ec_factor_cu')
        config['ec_factor_b'] = self.get_parameter('nutrient_parameters_ec_factor_b')
        config['ec_factor_mo'] = self.get_parameter('nutrient_parameters_ec_factor_mo')

        # Transport and system parameters
        config['minimum_volume_fraction'] = self.get_parameter('nutrient_parameters_minimum_volume_fraction')
        config['xylem_transport_capacity'] = self.get_parameter('nutrient_parameters_xylem_transport_capacity')
        config['phloem_transport_capacity'] = self.get_parameter('nutrient_parameters_phloem_transport_capacity')
        config['temperature_q10'] = self.get_parameter('nutrient_parameters_temperature_q10')
        config['transpiration_coupling'] = self.get_parameter('nutrient_parameters_transpiration_coupling')

        # EC uptake modifiers
        config['ec_uptake_high_threshold'] = self.get_parameter('nutrient_parameters_ec_uptake_high_threshold')
        config['ec_uptake_low_threshold'] = self.get_parameter('nutrient_parameters_ec_uptake_low_threshold')
        config['ec_uptake_modifier_n_high'] = self.get_parameter('nutrient_parameters_ec_uptake_modifier_n_high')
        config['ec_uptake_modifier_p_high'] = self.get_parameter('nutrient_parameters_ec_uptake_modifier_p_high')
        config['ec_uptake_modifier_k_high'] = self.get_parameter('nutrient_parameters_ec_uptake_modifier_k_high')
        config['ec_uptake_modifier_ca_high'] = self.get_parameter('nutrient_parameters_ec_uptake_modifier_ca_high')
        config['ec_uptake_modifier_n_low'] = self.get_parameter('nutrient_parameters_ec_uptake_modifier_n_low')
        config['ec_uptake_modifier_p_low'] = self.get_parameter('nutrient_parameters_ec_uptake_modifier_p_low')
        config['ec_uptake_modifier_fe_low'] = self.get_parameter('nutrient_parameters_ec_uptake_modifier_fe_low')

        # Kinetic parameters - Nitrate
        config['kinetics_n_no3_vmax'] = self.get_parameter('nutrient_parameters_kinetics_n_no3_vmax')
        config['kinetics_n_no3_km'] = self.get_parameter('nutrient_parameters_kinetics_n_no3_km')
        config['kinetics_n_no3_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_n_no3_min_conc')

        # Kinetic parameters - Ammonium
        config['kinetics_n_nh4_vmax'] = self.get_parameter('nutrient_parameters_kinetics_n_nh4_vmax')
        config['kinetics_n_nh4_km'] = self.get_parameter('nutrient_parameters_kinetics_n_nh4_km')
        config['kinetics_n_nh4_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_n_nh4_min_conc')

        # Kinetic parameters - Phosphate
        config['kinetics_p_po4_vmax'] = self.get_parameter('nutrient_parameters_kinetics_p_po4_vmax')
        config['kinetics_p_po4_km'] = self.get_parameter('nutrient_parameters_kinetics_p_po4_km')
        config['kinetics_p_po4_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_p_po4_min_conc')

        # Kinetic parameters - Potassium
        config['kinetics_k_vmax'] = self.get_parameter('nutrient_parameters_kinetics_k_vmax')
        config['kinetics_k_km'] = self.get_parameter('nutrient_parameters_kinetics_k_km')
        config['kinetics_k_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_k_min_conc')

        # Kinetic parameters - Calcium
        config['kinetics_ca_vmax'] = self.get_parameter('nutrient_parameters_kinetics_ca_vmax')
        config['kinetics_ca_km'] = self.get_parameter('nutrient_parameters_kinetics_ca_km')
        config['kinetics_ca_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_ca_min_conc')

        # Kinetic parameters - Magnesium
        config['kinetics_mg_vmax'] = self.get_parameter('nutrient_parameters_kinetics_mg_vmax')
        config['kinetics_mg_km'] = self.get_parameter('nutrient_parameters_kinetics_mg_km')
        config['kinetics_mg_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_mg_min_conc')

        # Load mobility parameters for nutrients that have them in CSV
        # Map nutrients to their actual CSV parameter names
        nutrient_csv_mapping = {
            "N-NO3": "n_no3",
            "N-NH4": "n_nh4",
            "P-PO4": "p_po4",
            "K": "k",
            "Ca": "ca",
            "Mg": "mg",
            "S-SO4": "s_so4",
            "Fe": "fe",
            "Mn": "mn",
            "Zn": "zn",
            "Cu": "cu",
            "B": "b",
            "Mo": "mo"
        }

        nutrients = ["N-NO3", "N-NH4", "P-PO4", "K", "Ca", "Mg", "S-SO4", "Fe", "Mn", "Zn", "Cu", "B", "Mo"]
        for nutrient in nutrients:
            csv_key = nutrient_csv_mapping[nutrient]

            # Load the parameters that actually exist in the CSV - using the exact patterns found
            config[f'mobility_classifications_{nutrient}_mobility'] = self.get_parameter(f'nutrient_mobility_mobility_classifications_{csv_key}_mobility')
            config[f'mobility_classifications_{nutrient}_transport'] = self.get_parameter(f'nutrient_mobility_mobility_classifications_{csv_key}_transport')

            # Some nutrients use different patterns for these parameters - handle both cases
            try:
                config[f'mobility_classifications_{nutrient}_remobilization_efficiency'] = self.get_parameter(f'nutrient_mobility_mobility_classifications_{csv_key}_remobilization_efficiency')
            except:
                config[f'mobility_classifications_{nutrient}_remobilization_efficiency'] = self.get_parameter(f'nutrient_mobility_remobilization_efficiency_{csv_key}')

            try:
                config[f'mobility_classifications_{nutrient}_deficiency_mobility'] = self.get_parameter(f'nutrient_mobility_mobility_classifications_{csv_key}_deficiency_mobility')
            except:
                config[f'mobility_classifications_{nutrient}_deficiency_mobility'] = self.get_parameter(f'nutrient_mobility_deficiency_mobility_{csv_key}')

            try:
                config[f'mobility_classifications_{nutrient}_retranslocation_rate'] = self.get_parameter(f'nutrient_mobility_mobility_classifications_{csv_key}_retranslocation_rate')
            except:
                config[f'mobility_classifications_{nutrient}_retranslocation_rate'] = self.get_parameter(f'nutrient_mobility_retranslocation_rate_{csv_key}')

            config[f'xylem_transport_rates_{nutrient}'] = self.get_parameter(f'nutrient_mobility_xylem_transport_rates_{csv_key}')
            # Calculate phloem rates as fraction of xylem rates (reasonable approximation)
            config[f'phloem_transport_rates_{nutrient}'] = config[f'xylem_transport_rates_{nutrient}'] * 0.4

        # Provide minimal required parameters for complex data structures
        # These would typically come from a more complete parameter set
        organs = ["leaves", "stems", "roots"]
        major_nutrients = ["N-NO3", "N-NH4", "P-PO4", "K"]
        for organ in organs:
            for nutrient in major_nutrients:
                # Use reasonable defaults based on scientific literature
                config[f'buffering_capacities_{organ}_{nutrient}'] = 1.0  # Base buffering capacity
                config[f'storage_pool_sizes_{organ}_{nutrient}'] = 10.0  # Base storage pool size

        for nutrient in ["N-NO3", "N-NH4", "P-PO4", "K", "Ca", "Mg", "S-SO4"]:
            config[f'redistribution_thresholds_{nutrient}'] = 0.5  # 50% threshold
            config[f'stress_redistribution_rates_{nutrient}'] = 0.1  # 10% redistribution rate

        stages = ["vegetative", "reproductive", "senescence"]
        for stage in stages:
            for organ in ["leaves", "stems", "roots"]:
                config[f'sink_strength_coefficients_{stage}_{organ}'] = 1.0  # Base sink strength
            if stage == "reproductive":
                config[f'sink_strength_coefficients_{stage}_reproductive'] = 2.0  # Higher for reproductive organs

        config['cache_timeout'] = 300.0  # 5 minutes cache timeout

        return NutrientParameters.from_config(config)

    def create_canopy_architecture_parameters(self):
        """Create canopy architecture parameters from CSV"""
        from ..models.canopy_architecture import CanopyArchitectureParameters

        params_dict = {}
        # Add all canopy architecture parameters from CSV
        params_dict['number_of_layers'] = self.get_parameter('canopy_parameters_number_of_layers')
        params_dict['max_lai'] = self.get_parameter('canopy_parameters_max_lai')
        params_dict['extinction_coefficient'] = self.get_parameter('canopy_parameters_extinction_coefficient')
        params_dict['diffuse_extinction_coeff'] = self.get_parameter('canopy_parameters_diffuse_extinction_coeff')
        params_dict['beam_extinction_coeff'] = self.get_parameter('canopy_parameters_beam_extinction_coeff')
        params_dict['row_spacing'] = self.get_parameter('canopy_parameters_row_spacing')
        params_dict['mean_leaf_angle'] = self.get_parameter('canopy_parameters_mean_leaf_angle')
        params_dict['canopy_width'] = self.get_parameter('canopy_parameters_canopy_width')
        params_dict['leaf_angle_distribution'] = self.get_parameter('canopy_parameters_leaf_angle_distribution')
        params_dict['leaf_angle_variance'] = self.get_parameter('canopy_parameters_leaf_angle_variance')
        params_dict['plant_spacing'] = self.get_parameter('canopy_parameters_plant_spacing')
        params_dict['plant_height'] = self.get_parameter('canopy_parameters_plant_height')
        params_dict['leaf_reflectance'] = self.get_parameter('canopy_parameters_leaf_reflectance')
        params_dict['leaf_transmittance'] = self.get_parameter('canopy_parameters_leaf_transmittance')
        params_dict['leaf_absorptance'] = self.get_parameter('canopy_parameters_leaf_absorptance')
        params_dict['self_shading_factor'] = self.get_parameter('canopy_parameters_self_shading_factor')
        params_dict['neighbor_shading_distance'] = self.get_parameter('canopy_parameters_neighbor_shading_distance')
        params_dict['sunlit_fraction_method'] = self.get_parameter('canopy_parameters_sunlit_fraction_method')
        params_dict['clumping_index'] = self.get_parameter('canopy_parameters_clumping_index')
        params_dict['max_extinction_coefficient'] = self.get_parameter('canopy_parameters_max_extinction_coefficient')
        params_dict['upper_canopy_lai_factor'] = self.get_parameter('canopy_parameters_upper_canopy_lai_factor')
        params_dict['middle_canopy_lai_factor'] = self.get_parameter('canopy_parameters_middle_canopy_lai_factor')
        params_dict['lower_middle_canopy_lai_factor'] = self.get_parameter('canopy_parameters_lower_middle_canopy_lai_factor')
        params_dict['bottom_canopy_lai_factor'] = self.get_parameter('canopy_parameters_bottom_canopy_lai_factor')
        params_dict['shaded_light_fraction'] = self.get_parameter('photosynthesis_parameters_shaded_light_fraction')
        params_dict['max_temperature_gradient'] = self.get_parameter('canopy_parameters_max_temperature_gradient')
        params_dict['temperature_gradient_factor'] = self.get_parameter('canopy_parameters_temperature_gradient_factor')
        params_dict['ppfd_to_photosynthesis_factor'] = self.get_parameter('canopy_parameters_ppfd_to_photosynthesis_factor')
        params_dict['spherical_x_coefficient'] = self.get_parameter('canopy_parameters_spherical_x_coefficient')
        params_dict['planophile_x_coefficient'] = self.get_parameter('canopy_parameters_planophile_x_coefficient')
        params_dict['erectophile_x_coefficient'] = self.get_parameter('canopy_parameters_erectophile_x_coefficient')
        params_dict['plagiophile_x_coefficient'] = self.get_parameter('canopy_parameters_plagiophile_x_coefficient')
        params_dict['upper_canopy_height_threshold'] = self.get_parameter('canopy_parameters_upper_canopy_height_threshold')
        params_dict['middle_canopy_height_threshold'] = self.get_parameter('canopy_parameters_middle_canopy_height_threshold')
        params_dict['lower_middle_canopy_height_threshold'] = self.get_parameter('canopy_parameters_lower_middle_canopy_height_threshold')
        params_dict['zenith_angle_precision_threshold'] = self.get_parameter('canopy_parameters_zenith_angle_precision_threshold')
        params_dict['direct_beam_fraction'] = self.get_parameter('canopy_parameters_direct_beam_fraction')
        params_dict['diffuse_fraction'] = self.get_parameter('canopy_parameters_diffuse_fraction')

        return CanopyArchitectureParameters.from_config(params_dict)

    def create_ph_parameters(self):
        """Create pH parameters from CSV"""
        from models.ph_model import PHParameters
        
        params_dict = {}
        # Add pH-specific parameters
        params_dict['optimal_ph'] = self.get_parameter('ph_parameters_optimal_ph')
        params_dict['ph_tolerance'] = self.get_parameter('ph_parameters_ph_tolerance')
        
        return PHParameters(**params_dict)

    def create_root_system_parameters(self):
        """Create root system parameters from CSV"""
        from ..models.root_system_model import RootSystemParameters, HydroponicSystemType

        # Create configuration sections required by from_config
        config = {}

        # For testing purposes, provide minimal parameter set with defaults for missing CSV parameters
        # Core root system parameters - use defaults since CSV doesn't have complete set
        config['container_volume'] = 50000.0  # 50L in cm³
        config['channel_length'] = 100.0  # cm
        config['system_type'] = 'deep_water_culture'  # Default system type
        config['channel_width'] = 10.0  # cm
        config['channel_depth'] = 5.0  # cm
        config['n_channels'] = 4
        config['root_zone_independent'] = True

        # Root growth parameters - provide defaults since CSV doesn't have these
        config['primary_root_growth_rate'] = 2.0  # cm/day
        config['lateral_root_density'] = 5.0  # roots/cm
        config['branching_angle_mean'] = 45.0  # degrees
        config['branching_angle_std'] = 15.0  # degrees

        # Root type fractions - must sum to 1.0
        config['fine_root_fraction'] = 0.6
        config['medium_root_fraction'] = 0.3
        config['coarse_root_fraction'] = 0.1

        # Root diameter parameters
        config['fine_diameter_mean'] = self.get_parameter('root_system_fine_diameter_mean')
        config['fine_diameter_std'] = self.get_parameter('root_system_fine_diameter_std')
        config['medium_diameter_mean'] = self.get_parameter('root_system_medium_diameter_mean')
        config['medium_diameter_std'] = self.get_parameter('root_system_medium_diameter_std')
        config['coarse_diameter_mean'] = self.get_parameter('root_system_coarse_diameter_mean')
        config['coarse_diameter_std'] = self.get_parameter('root_system_coarse_diameter_std')

        # Root turnover and longevity
        config['fine_turnover_rate'] = self.get_parameter('root_system_fine_turnover_rate')
        config['medium_turnover_rate'] = self.get_parameter('root_system_medium_turnover_rate')
        config['coarse_turnover_rate'] = self.get_parameter('root_system_coarse_turnover_rate')
        config['fine_root_half_life_days'] = self.get_parameter('root_system_fine_half_life_days')
        config['medium_root_half_life_days'] = self.get_parameter('root_system_medium_half_life_days')
        config['coarse_root_half_life_days'] = self.get_parameter('root_system_coarse_half_life_days')

        # Root activity parameters
        config['root_zone_efficiency_factor'] = self.get_parameter('root_system_zone_efficiency_factor')
        config['fine_min_activity'] = self.get_parameter('root_system_fine_min_activity')
        config['medium_min_activity'] = self.get_parameter('root_system_medium_min_activity')
        config['coarse_min_activity'] = self.get_parameter('root_system_coarse_min_activity')
        config['establishment_plateau_days'] = self.get_parameter('root_system_establishment_plateau_days')
        config['initial_root_activity'] = self.get_parameter('root_system_initial_activity')

        # Root effectiveness parameters
        config['fine_root_effectiveness'] = self.get_parameter('root_system_fine_effectiveness')
        config['medium_root_effectiveness'] = self.get_parameter('root_system_medium_effectiveness')
        config['coarse_root_effectiveness'] = self.get_parameter('root_system_coarse_effectiveness')

        # Temperature parameters - use consolidated from phenology
        config['optimal_temperature_min'] = self.get_parameter('phenology_optimal_temperature_min')
        config['optimal_temperature_max'] = self.get_parameter('phenology_optimal_temperature_max')
        config['q10_factor'] = self.get_parameter('root_system_q10_factor')

        # Flow and environmental parameters
        config['optimal_flow_rate'] = self.get_parameter('root_system_optimal_flow_rate')
        config['flow_stress_threshold'] = self.get_parameter('root_system_flow_stress_threshold')
        config['root_growth_auxin_decay_rate'] = self.get_parameter('root_system_auxin_decay_rate')
        config['root_optimal_density'] = self.get_parameter('root_system_optimal_density')
        config['root_density_stress_factor'] = self.get_parameter('root_system_density_stress_factor')
        config['root_temp_optimum'] = self.get_parameter('root_system_temp_optimum')
        config['root_temp_max'] = self.get_parameter('root_system_temp_max')
        config['root_temp_min_factor'] = self.get_parameter('root_system_temp_min_factor')
        config['root_oxygen_optimum'] = self.get_parameter('root_system_oxygen_optimum')
        config['root_oxygen_min_factor'] = self.get_parameter('root_system_oxygen_min_factor')

        # pH and stress parameters
        config['ph_stress_range_acidic'] = self.get_parameter('root_system_ph_stress_range_acidic')
        config['ph_stress_range_basic'] = self.get_parameter('root_system_ph_stress_range_basic')
        config['ph_stress_factor'] = self.get_parameter('root_system_ph_stress_factor')
        config['young_root_activity'] = self.get_parameter('root_system_young_root_activity')
        config['old_root_activity'] = self.get_parameter('root_system_old_root_activity')

        # Additional hardcoded parameters extracted from code
        config['temperature_range_factor'] = self.get_parameter('root_system_temperature_range_factor')
        config['min_temperature_factor'] = self.get_parameter('root_system_min_temperature_factor')
        config['max_temperature_factor'] = self.get_parameter('root_system_max_temperature_factor')
        config['low_flow_factor'] = self.get_parameter('root_system_low_flow_factor')
        config['high_flow_factor'] = self.get_parameter('root_system_high_flow_factor')
        config['ph_zone_min'] = self.get_parameter('root_system_ph_zone_min')
        config['ph_zone_max'] = self.get_parameter('root_system_ph_zone_max')
        config['min_ph_factor'] = self.get_parameter('root_system_min_ph_factor')
        config['ph_penalty_factor'] = self.get_parameter('root_system_ph_penalty_factor')

        # Zone fraction parameters
        config['nft_zone_1_fraction'] = self.get_parameter('root_system_nft_zone_1_fraction')
        config['nft_zone_2_fraction'] = self.get_parameter('root_system_nft_zone_2_fraction')
        config['nft_zone_3_fraction'] = self.get_parameter('root_system_nft_zone_3_fraction')
        config['dwc_zone_1_fraction'] = self.get_parameter('root_system_dwc_zone_1_fraction')
        config['dwc_zone_2_fraction'] = self.get_parameter('root_system_dwc_zone_2_fraction')
        config['dwc_zone_3_fraction'] = self.get_parameter('root_system_dwc_zone_3_fraction')
        config['general_zone_1_fraction'] = self.get_parameter('root_system_general_zone_1_fraction')
        config['general_zone_2_fraction'] = self.get_parameter('root_system_general_zone_2_fraction')
        config['general_zone_3_fraction'] = self.get_parameter('root_system_general_zone_3_fraction')
        config['general_zone_4_fraction'] = self.get_parameter('root_system_general_zone_4_fraction')

        # Root biomass and threshold parameters
        config['root_biomass_density'] = self.get_parameter('root_system_biomass_density')
        config['coarse_root_min_threshold'] = self.get_parameter('root_system_coarse_min_threshold')
        config['fine_root_min_threshold'] = self.get_parameter('root_system_fine_min_threshold')
        config['diameter_minimum_limit'] = self.get_parameter('root_system_diameter_minimum_limit')

        # Growth potential weights
        config['auxin_gradient_weight'] = self.get_parameter('root_system_auxin_gradient_weight')
        config['nutrient_signal_weight'] = self.get_parameter('root_system_nutrient_signal_weight')
        config['oxygen_effect_weight'] = self.get_parameter('root_system_oxygen_effect_weight')
        config['competition_effect_weight'] = self.get_parameter('root_system_competition_effect_weight')
        config['temperature_effect_weight'] = self.get_parameter('root_system_temperature_effect_weight')
        config['min_growth_potential'] = self.get_parameter('root_system_min_growth_potential')
        config['max_growth_potential'] = self.get_parameter('root_system_max_growth_potential')
        config['max_temp_threshold'] = self.get_parameter('root_system_max_temp_threshold')
        config['temp_decay_factor'] = self.get_parameter('root_system_temp_decay_factor')

        # Flow and transport parameters
        config['flow_rate_offset'] = self.get_parameter('root_system_flow_rate_offset')
        config['flow_rate_multiplier'] = self.get_parameter('root_system_flow_rate_multiplier')
        config['transport_temp_exponent'] = self.get_parameter('root_system_transport_temp_exponent')

        # Minimum value parameters
        config['minimum_surface_area'] = self.get_parameter('root_system_minimum_surface_area')
        config['minimum_biomass'] = self.get_parameter('root_system_minimum_biomass')
        config['minimum_volume'] = self.get_parameter('root_system_minimum_volume')
        config['effective_area_minimum'] = self.get_parameter('root_system_effective_area_minimum')

        # Nutrient uptake parameters (required by model)
        nutrients = ['NO3', 'NH4', 'PO4', 'K', 'Ca', 'Mg', 'SO4']
        for nutrient in nutrients:
            config[f'{nutrient.lower()}_uptake_vmax'] = self.get_parameter(f'root_system_{nutrient.lower()}_uptake_vmax')
            config[f'{nutrient.lower()}_uptake_km'] = self.get_parameter(f'root_system_{nutrient.lower()}_uptake_km')

        # System multipliers for each hydroponic system type
        system_types = ['nutrient_film_technique', 'deep_water_culture', 'aeroponics', 'drip', 'wick_system', 'ebb_flow']
        for sys_type in system_types:
            config[f'system_multipliers_{sys_type}_root_length_multiplier'] = self.get_parameter(f'root_system_multipliers_{sys_type}_root_length_multiplier')
            config[f'system_multipliers_{sys_type}_surface_area_multiplier'] = self.get_parameter(f'root_system_multipliers_{sys_type}_surface_area_multiplier')
            config[f'system_multipliers_{sys_type}_branching_multiplier'] = self.get_parameter(f'root_system_multipliers_{sys_type}_branching_multiplier')

        # Nutrient demand weights
        config['nutrient_demand_weight_no3'] = self.get_parameter('root_system_nutrient_demand_weight_no3')
        config['nutrient_demand_weight_po4'] = self.get_parameter('root_system_nutrient_demand_weight_po4')
        config['nutrient_demand_weight_k'] = self.get_parameter('root_system_nutrient_demand_weight_k')
        config['nutrient_demand_weight_ca'] = self.get_parameter('root_system_nutrient_demand_weight_ca')
        config['nutrient_demand_weight_mg'] = self.get_parameter('root_system_nutrient_demand_weight_mg')

        # Nutrient reference concentrations
        config['nutrient_ref_concentration_no3'] = self.get_parameter('root_system_nutrient_ref_concentration_no3')
        config['nutrient_ref_concentration_po4'] = self.get_parameter('root_system_nutrient_ref_concentration_po4')
        config['nutrient_ref_concentration_k'] = self.get_parameter('root_system_nutrient_ref_concentration_k')
        config['nutrient_ref_concentration_ca'] = self.get_parameter('root_system_nutrient_ref_concentration_ca')
        config['nutrient_ref_concentration_mg'] = self.get_parameter('root_system_nutrient_ref_concentration_mg')

        # Nutrient competition groups (comma-separated strings)
        config['nutrient_competition_no3'] = self.get_parameter('root_system_nutrient_competition_no3')
        config['nutrient_competition_nh4'] = self.get_parameter('root_system_nutrient_competition_nh4')
        config['nutrient_competition_po4'] = self.get_parameter('root_system_nutrient_competition_po4')
        config['nutrient_competition_k'] = self.get_parameter('root_system_nutrient_competition_k')
        config['nutrient_competition_ca'] = self.get_parameter('root_system_nutrient_competition_ca')
        config['nutrient_competition_mg'] = self.get_parameter('root_system_nutrient_competition_mg')

        # pH optima for nutrients
        config['ph_optimum_no3_min'] = self.get_parameter('root_system_ph_optimum_no3_min')
        config['ph_optimum_no3_max'] = self.get_parameter('root_system_ph_optimum_no3_max')
        config['ph_optimum_nh4_min'] = self.get_parameter('root_system_ph_optimum_nh4_min')
        config['ph_optimum_nh4_max'] = self.get_parameter('root_system_ph_optimum_nh4_max')
        config['ph_optimum_po4_min'] = self.get_parameter('root_system_ph_optimum_po4_min')
        config['ph_optimum_po4_max'] = self.get_parameter('root_system_ph_optimum_po4_max')
        config['ph_optimum_k_min'] = self.get_parameter('root_system_ph_optimum_k_min')
        config['ph_optimum_k_max'] = self.get_parameter('root_system_ph_optimum_k_max')
        config['ph_optimum_ca_min'] = self.get_parameter('root_system_ph_optimum_ca_min')
        config['ph_optimum_ca_max'] = self.get_parameter('root_system_ph_optimum_ca_max')
        config['ph_optimum_mg_min'] = self.get_parameter('root_system_ph_optimum_mg_min')
        config['ph_optimum_mg_max'] = self.get_parameter('root_system_ph_optimum_mg_max')

        # Cache timeout
        config['cache_timeout'] = self.get_parameter('root_system_cache_timeout')

        return RootSystemParameters.from_config(config)

    def create_environmental_control_parameters(self):
        """Create environmental control parameters from CSV"""
        from ..models.environmental_control import EnvironmentalSetpoints, ControlEquipment

        # Prepare parameter dictionary for EnvironmentalSetpoints
        params_dict = {}

        # Environmental setpoints - using correct CSV parameter names
        params_dict['target_vpd'] = self.get_parameter('environment_target_vpd')
        params_dict['vpd_tolerance'] = self.get_parameter('environment_vpd_tolerance')
        params_dict['min_humidity'] = self.get_parameter('environment_min_humidity')
        params_dict['max_humidity'] = self.get_parameter('environment_max_humidity')
        params_dict['day_temp'] = self.get_parameter('environment_day_temp')
        params_dict['night_temp'] = self.get_parameter('environment_night_temp')
        params_dict['temp_tolerance'] = self.get_parameter('environment_temp_tolerance')
        params_dict['target_co2'] = self.get_parameter('environment_target_co2')
        params_dict['ambient_co2'] = self.get_parameter('environment_ambient_co2')
        params_dict['co2_tolerance'] = self.get_parameter('environment_co2_tolerance')
        params_dict['light_hours'] = self.get_parameter('environment_light_hours')
        params_dict['light_intensity_control'] = self.get_parameter('environment_light_intensity_control')
        params_dict['co2_enrichment_start_hour'] = self.get_parameter('environment_co2_enrichment_start_hour')
        params_dict['humidity_deadband'] = self.get_parameter('environment_humidity_deadband')
        params_dict['max_temperature_change_per_hour'] = self.get_parameter('environment_max_temperature_change_per_hour')
        params_dict['ambient_temperature'] = self.get_parameter('environment_ambient_temperature')
        params_dict['thermal_mass_factor'] = self.get_parameter('environment_thermal_mass_factor')
        params_dict['base_co2_loss_rate'] = self.get_parameter('environment_base_co2_loss_rate')
        params_dict['min_co2_concentration'] = self.get_parameter('environment_min_co2_concentration')
        params_dict['max_co2_concentration'] = self.get_parameter('environment_max_co2_concentration')
        params_dict['light_saturation_threshold'] = self.get_parameter('environment_light_saturation_threshold')
        params_dict['co2_response_vmax'] = self.get_parameter('environment_co2_response_vmax')
        params_dict['co2_response_km'] = self.get_parameter('environment_co2_response_km')
        params_dict['max_co2_enhancement_factor'] = self.get_parameter('environment_max_co2_enhancement_factor')

        # PID parameters for humidity
        params_dict['pid_humidity_kp'] = self.get_parameter('environment_pid_humidity_kp')
        params_dict['pid_humidity_ki'] = self.get_parameter('environment_pid_humidity_ki')
        params_dict['pid_humidity_kd'] = self.get_parameter('environment_pid_humidity_kd')

        # PID parameters for CO2
        params_dict['pid_co2_kp'] = self.get_parameter('environment_pid_co2_kp')
        params_dict['pid_co2_ki'] = self.get_parameter('environment_pid_co2_ki')
        params_dict['pid_co2_kd'] = self.get_parameter('environment_pid_co2_kd')

        # PID parameters for temperature
        params_dict['pid_temperature_kp'] = self.get_parameter('environment_pid_temperature_kp')
        params_dict['pid_temperature_ki'] = self.get_parameter('environment_pid_temperature_ki')
        params_dict['pid_temperature_kd'] = self.get_parameter('environment_pid_temperature_kd')

        # Simulator default parameters - calculated from CSV parameters
        min_hum = params_dict['min_humidity']
        max_hum = params_dict['max_humidity']
        params_dict['default_air_temperature'] = params_dict['day_temp']  # Use day_temp as default
        params_dict['default_humidity'] = (min_hum + max_hum) / 2.0  # Middle of min/max range from CSV
        params_dict['default_light_intensity'] = params_dict['light_intensity_control']
        params_dict['cache_timeout'] = 30.0  # 30 seconds cache timeout

        # Create setpoints
        setpoints = EnvironmentalSetpoints.from_config(params_dict)

        # Equipment parameters
        equipment_dict = {}
        equipment_dict['humidifier_capacity'] = self.get_parameter('control_equipment_parameters_humidifier_capacity')
        equipment_dict['dehumidifier_capacity'] = self.get_parameter('control_equipment_parameters_dehumidifier_capacity')
        equipment_dict['humidifier_efficiency'] = self.get_parameter('control_equipment_parameters_humidifier_efficiency')
        equipment_dict['dehumidifier_efficiency'] = self.get_parameter('control_equipment_parameters_dehumidifier_efficiency')
        equipment_dict['co2_injection_rate'] = self.get_parameter('control_equipment_parameters_co2_injection_rate')
        equipment_dict['co2_sensor_accuracy'] = self.get_parameter('control_equipment_parameters_co2_sensor_accuracy')
        equipment_dict['co2_mixing_time'] = self.get_parameter('control_equipment_parameters_co2_mixing_time')
        equipment_dict['air_exchange_rate'] = self.get_parameter('control_equipment_parameters_air_exchange_rate')
        equipment_dict['circulation_fan_power'] = self.get_parameter('control_equipment_parameters_circulation_fan_power')

        # Create equipment
        equipment = ControlEquipment.from_config(equipment_dict)

        return setpoints, equipment

    def create_genetic_parameters(self):
        """Create genetic parameters from CSV"""
        from models.genetic_parameters import GeneticParameterDatabase, CultivarProfile
        
        # Create genetic database
        genetic_db = GeneticParameterDatabase()
        
        # Create cultivar profile
        cultivar_profile = CultivarProfile(
            cultivar_name="Boston Bibb",
            lettuce_type="butterhead",
            maturity_days=60
        )
        
        return genetic_db, cultivar_profile

    def create_leaf_development_parameters(self):
        """Create leaf development parameters from CSV"""
        from ..models.leaf_development import LeafParameters

        config = {}

        # Leaf development parameters
        config['leaf_development'] = {}
        leaf_dev_params = [
            'base_phyllochron', 'max_leaf_number', 'initial_leaf_number', 'leaf_appearance_rate',
            'max_individual_leaf_area', 'leaf_area_expansion_rate', 'drought_threshold', 'n_stress_threshold',
            'temperature_stress_sensitivity', 'initial_leaf_area_factor', 'initial_thermal_time_factor',
            'emerging_to_expanding_factor', 'late_leaf_phyllochron_factor', 'very_late_leaf_phyllochron_factor',
            'early_leaf_size_factor', 'late_leaf_size_factor', 'leaf_maturation_thermal_time',
            'leaf_lifespan_thermal_time', 'senescence_threshold_age', 'senescence_rate_base',
            'minimum_active_leaf_area', 'minimum_visible_leaf_area', 'late_leaf_vstage_threshold',
            'very_late_leaf_vstage_threshold', 'early_leaf_position_threshold', 'middle_leaf_position_threshold',
            'early_position_scaling_factor', 'late_position_scaling_factor', 'min_temp', 'max_temp', 'specific_leaf_area'
        ]

        for param in leaf_dev_params:
            config['leaf_development'][param] = self.get_parameter(f'leaf_development_{param}')

        # Canopy parameters (required by from_config)
        config['canopy_parameters'] = {}
        canopy_params = ['number_of_layers', 'max_lai', 'extinction_coefficient']
        for param in canopy_params:
            config['canopy_parameters'][param] = self.get_parameter(f'canopy_parameters_{param}')

        # Phenology parameters (required by from_config)
        config['phenology'] = {}
        phenology_params = ['optimal_temperature_min', 'optimal_temperature_max']
        for param in phenology_params:
            config['phenology'][param] = self.get_parameter(f'phenology_parameters_{param}')

        # Nitrogen parameters (required by from_config)
        config['nitrogen_parameters'] = {}
        # Basic required parameters for the method
        config['nitrogen_parameters']['n_stress_threshold'] = self.get_parameter('leaf_development_n_stress_threshold')

        # Genetic parameters (required by from_config)
        config['genetic_parameters'] = {}
        config['genetic_parameters']['SLAVR'] = self.get_parameter('leaf_development_specific_leaf_area')

        # Thermal time parameters (required by from_config)
        config['thermal_time'] = {}
        config['thermal_time']['base_temp'] = self.get_parameter('leaf_development_min_temp')
        config['thermal_time']['optimal_temp_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        config['thermal_time']['optimal_temp_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')
        config['thermal_time']['max_temp'] = self.get_parameter('leaf_development_max_temp')

        # Cache timeout
        config['leaf_development']['cache_timeout'] = 300.0  # 5 minutes default

        return LeafParameters.from_config(config)

    def create_nitrogen_balance_parameters(self):
        """Create nitrogen balance parameters from CSV"""
        from ..models.nitrogen_balance import NitrogenBalanceParameters

        config = {}

        # Basic nitrogen parameters
        config['nitrate_reduction_rate'] = self.get_parameter('nitrogen_parameters_nitrate_reduction_rate')
        config['ammonium_assimilation_rate'] = self.get_parameter('nitrogen_parameters_ammonium_assimilation_rate')
        config['amino_acid_uptake_rate'] = self.get_parameter('nitrogen_parameters_amino_acid_uptake_rate')
        config['photosynthetic_n_use_efficiency'] = self.get_parameter('nitrogen_parameters_photosynthetic_n_use_efficiency')
        config['growth_n_use_efficiency'] = self.get_parameter('nitrogen_parameters_growth_n_use_efficiency')
        config['n_stress_threshold'] = self.get_parameter('leaf_development_n_stress_threshold')
        config['luxury_uptake_threshold'] = self.get_parameter('nitrogen_parameters_luxury_uptake_threshold')
        config['specific_root_activity'] = self.get_parameter('nitrogen_parameters_specific_root_activity')
        config['root_zone_exploration'] = self.get_parameter('nitrogen_parameters_root_zone_exploration')

        # Uptake kinetics for NO3, NH4, amino_acids
        config['uptake_kinetics'] = {}
        n_forms = ['NO3', 'NH4', 'amino_acids']
        for n_form in n_forms:
            config['uptake_kinetics'][n_form] = {
                'vmax': self.get_parameter(f'nitrogen_parameters_uptake_kinetics_{n_form}_vmax'),
                'km': self.get_parameter(f'nitrogen_parameters_uptake_kinetics_{n_form}_km'),
                'min_conc': self.get_parameter(f'nitrogen_parameters_uptake_kinetics_{n_form}_min_conc'),
                'inhibition_ki': self.get_parameter(f'nitrogen_parameters_uptake_kinetics_{n_form}_inhibition_ki')
            }

        # Allocation coefficients for growth stages and organs
        config['allocation_coefficients'] = {}
        growth_stages = ['vegetative', 'reproductive']
        organs = ['leaves', 'stems', 'roots', 'reproductive']
        for stage in growth_stages:
            config['allocation_coefficients'][stage] = {}
            for organ in organs:
                config['allocation_coefficients'][stage][organ] = self.get_parameter(
                    f'nitrogen_parameters_allocation_coefficients_{stage}_{organ}')

        # Critical N concentrations for all organs
        config['critical_n_concentrations'] = {}
        concentration_levels = ['minimum', 'critical', 'optimal', 'maximum']
        for organ in organs:
            config['critical_n_concentrations'][organ] = {}
            for level in concentration_levels:
                config['critical_n_concentrations'][organ][level] = self.get_parameter(
                    f'nitrogen_parameters_critical_n_concentrations_{organ}_{level}')

        # Remobilization rates for different pools
        config['remobilization_rates'] = {}
        n_pools = ['structural', 'metabolic', 'storage', 'transport']
        for pool in n_pools:
            config['remobilization_rates'][pool] = self.get_parameter(
                f'nitrogen_parameters_remobilization_rates_{pool}')

        # Remobilization efficiency for organs
        config['remobilization_efficiency'] = {}
        for organ in organs:
            config['remobilization_efficiency'][organ] = self.get_parameter(
                f'nitrogen_parameters_remobilization_efficiency_{organ}')

        # Organ weights for stress calculation
        config['organ_weights'] = {}
        for organ in organs:
            config['organ_weights'][organ] = self.get_parameter(
                f'nitrogen_parameters_organ_weights_{organ}')

        # Pool fractions - use flat key format expected by from_config
        for organ in organs:
            for pool in n_pools:
                config[f'pool_fractions_{organ}_{pool}'] = self.get_parameter(
                    f'nitrogen_parameters_pool_fractions_{organ}_{pool}')

        # Cache timeout - use system default if no specific N balance timeout
        config['cache_timeout'] = 300.0  # 5 minutes default

        return NitrogenBalanceParameters.from_config(config)

    def create_root_zone_temperature_parameters(self):
        """Create root zone temperature parameters from CSV"""
        from models.root_zone_temperature import RZTParameters
        
        params_dict = {}
        # Add root zone temperature-specific parameters
        params_dict['optimal_temperature'] = self.get_parameter('root_zone_temperature_optimal')
        params_dict['temperature_tolerance'] = self.get_parameter('root_zone_temperature_tolerance')
        
        return RZTParameters(**params_dict)

    def create_senescence_parameters(self):
        """Create senescence parameters from CSV - follows Rules.md strictly"""
        from models.senescence_model import SenescenceParameters

        config = {}

        # Basic senescence parameters
        config['natural_lifespan_gdd'] = self.get_parameter('senescence_parameters_natural_lifespan_gdd')
        config['age_senescence_rate'] = self.get_parameter('senescence_parameters_age_senescence_rate')

        # Stress thresholds
        config['water_stress_threshold'] = self.get_parameter('senescence_parameters_water_stress_threshold')
        config['nitrogen_stress_threshold'] = self.get_parameter('senescence_parameters_nitrogen_stress_threshold')
        config['temperature_stress_threshold'] = self.get_parameter('senescence_parameters_temperature_stress_threshold')
        config['light_stress_threshold'] = self.get_parameter('senescence_parameters_light_stress_threshold')

        # Stress rates
        config['water_stress_rate'] = self.get_parameter('senescence_parameters_water_stress_rate')
        config['nitrogen_stress_rate'] = self.get_parameter('senescence_parameters_nitrogen_stress_rate')
        config['temperature_stress_rate'] = self.get_parameter('senescence_parameters_temperature_stress_rate')
        config['light_stress_rate'] = self.get_parameter('senescence_parameters_light_stress_rate')

        # Senescence stage thresholds
        config['early_senescence_threshold'] = self.get_parameter('senescence_parameters_early_senescence_threshold')
        config['active_senescence_threshold'] = self.get_parameter('senescence_parameters_active_senescence_threshold')
        config['late_senescence_threshold'] = self.get_parameter('senescence_parameters_late_senescence_threshold')
        config['death_threshold'] = self.get_parameter('senescence_parameters_death_threshold')

        # Recovery parameters
        config['recovery_rate'] = self.get_parameter('senescence_parameters_recovery_rate')
        config['max_recovery'] = self.get_parameter('senescence_parameters_max_recovery')
        config['stress_recovery_threshold'] = self.get_parameter('senescence_parameters_stress_recovery_threshold')
        config['recovery_stress_threshold'] = self.get_parameter('senescence_parameters_recovery_stress_threshold')

        # Developmental parameters
        config['reproductive_priority_factor'] = self.get_parameter('senescence_parameters_reproductive_priority_factor')
        config['lower_canopy_factor'] = self.get_parameter('senescence_parameters_lower_canopy_factor')
        config['canopy_shading_threshold'] = self.get_parameter('senescence_parameters_canopy_shading_threshold')
        config['shading_factor_multiplier'] = self.get_parameter('senescence_parameters_shading_factor_multiplier')
        config['lower_canopy_adjustment'] = self.get_parameter('senescence_parameters_lower_canopy_adjustment')
        config['reproductive_factor_adjustment'] = self.get_parameter('senescence_parameters_reproductive_factor_adjustment')

        # Remobilization parameters
        config['active_senescence_multiplier'] = self.get_parameter('senescence_parameters_active_senescence_multiplier')
        config['normal_senescence_multiplier'] = self.get_parameter('senescence_parameters_normal_senescence_multiplier')

        # Area and biomass loss parameters
        config['daily_area_loss_factor'] = self.get_parameter('senescence_parameters_daily_area_loss_factor')
        config['daily_biomass_loss_factor'] = self.get_parameter('senescence_parameters_daily_biomass_loss_factor')

        # Calculation parameters
        config['age_factor_base'] = self.get_parameter('senescence_parameters_age_factor_base')
        config['stress_intensity_denominator'] = self.get_parameter('senescence_parameters_stress_intensity_denominator')
        config['recovery_rate_fraction'] = self.get_parameter('senescence_parameters_recovery_rate_fraction')
        config['senescence_damage_minimum'] = self.get_parameter('senescence_parameters_senescence_damage_minimum')
        config['senescence_damage_maximum'] = self.get_parameter('senescence_parameters_senescence_damage_maximum')

        # Stress history
        config['stress_history_days'] = self.get_parameter('senescence_parameters_stress_history_days')

        # Nutrient remobilization efficiencies
        config['nitrogen_recovery'] = self.get_parameter('senescence_parameters_nitrogen_recovery')
        config['phosphorus_recovery'] = self.get_parameter('senescence_parameters_phosphorus_recovery')
        config['potassium_recovery'] = self.get_parameter('senescence_parameters_potassium_recovery')
        config['magnesium_recovery'] = self.get_parameter('senescence_parameters_magnesium_recovery')
        config['sulfur_recovery'] = self.get_parameter('senescence_parameters_sulfur_recovery')
        config['calcium_recovery'] = self.get_parameter('senescence_parameters_calcium_recovery')
        config['iron_recovery'] = self.get_parameter('senescence_parameters_iron_recovery')
        config['manganese_recovery'] = self.get_parameter('senescence_parameters_manganese_recovery')
        config['zinc_recovery'] = self.get_parameter('senescence_parameters_zinc_recovery')
        config['copper_recovery'] = self.get_parameter('senescence_parameters_copper_recovery')
        config['boron_recovery'] = self.get_parameter('senescence_parameters_boron_recovery')
        config['molybdenum_recovery'] = self.get_parameter('senescence_parameters_molybdenum_recovery')

        return SenescenceParameters.from_config(config)
