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

    def __init__(self,
                 master_csv_path: str,
                 constants_csv_path: Optional[str] = None,
                 stress_csv_path: Optional[str] = None,
                 roots_csv_path: Optional[str] = None,
                 genetics_csv_path: Optional[str] = None,
                 photo_csv_path: Optional[str] = None,
                 respiration_csv_path: Optional[str] = None,
                 allocation_csv_path: Optional[str] = None,
                 phenology_csv_path: Optional[str] = None,
                 nitrogen_balance_csv_path: Optional[str] = None,
                 canopy_csv_path: Optional[str] = None,
                 leaf_csv_path: Optional[str] = None,
                 water_csv_path: Optional[str] = None,
                 nutrient_csv_path: Optional[str] = None):
        self.master_csv_path = master_csv_path
        self.constants_csv_path = constants_csv_path
        self.stress_csv_path = stress_csv_path
        self.roots_csv_path = roots_csv_path
        self.genetics_csv_path = genetics_csv_path
        self.photo_csv_path = photo_csv_path
        self.respiration_csv_path = respiration_csv_path
        self.allocation_csv_path = allocation_csv_path
        self.phenology_csv_path = phenology_csv_path
        self.nitrogen_balance_csv_path = nitrogen_balance_csv_path
        self.canopy_csv_path = canopy_csv_path
        self.leaf_csv_path = leaf_csv_path
        self.water_csv_path = water_csv_path
        self.nutrient_csv_path = nutrient_csv_path
        self.parameters = {}
        self.constants = {}

        # Load constants first if path provided
        if self.constants_csv_path:
            self._load_constants()

        # Load stress parameters if path provided
        if self.stress_csv_path:
            self._load_specialized_file(self.stress_csv_path, 'stress_parameters')

        # Load root system parameters if path provided
        if self.roots_csv_path:
            self._load_specialized_file(self.roots_csv_path, 'root_system_parameters')

        # Load genetic parameters if path provided
        if self.genetics_csv_path:
            self._load_specialized_file(self.genetics_csv_path, 'genetic_parameters')

        # Senescence parameters removed

        # Load photosynthesis parameters if path provided
        if self.photo_csv_path:
            self._load_specialized_file(self.photo_csv_path, 'photosynthesis_parameters')

        # Load respiration parameters if path provided
        if self.respiration_csv_path:
            self._load_specialized_file(self.respiration_csv_path, 'respiration_parameters')

        # Load allocation parameters if path provided
        if self.allocation_csv_path:
            self._load_specialized_file(self.allocation_csv_path, 'allocation_parameters')

        # Load phenology parameters if path provided
        if self.phenology_csv_path:
            self._load_specialized_file(self.phenology_csv_path, 'phenology_parameters')

        # Load nitrogen balance parameters if path provided
        if self.nitrogen_balance_csv_path:
            self._load_specialized_file(self.nitrogen_balance_csv_path, 'nitrogen_balance')

        # Load canopy parameters if path provided
        if self.canopy_csv_path:
            self._load_specialized_file(self.canopy_csv_path, 'canopy_parameters')

        # Load leaf development parameters if path provided
        if self.leaf_csv_path:
            self._load_specialized_file(self.leaf_csv_path, 'leaf_development')

        # Load water uptake parameters if path provided
        if self.water_csv_path:
            self._load_specialized_file(self.water_csv_path, 'water_parameters')

        # Load nutrient parameters if path provided
        if self.nutrient_csv_path:
            self._load_specialized_file(self.nutrient_csv_path, 'nutrient_parameters')

        # Load parameters from master file
        self._load_parameters()

    def _load_constants(self):
        """Load universal constants from constants.csv"""
        if not os.path.exists(self.constants_csv_path):
            raise ParameterError(f"Constants file not found: {self.constants_csv_path}")

        try:
            df = pd.read_csv(self.constants_csv_path, comment='#')

            for _, row in df.iterrows():
                if pd.isna(row['constant_name']):
                    continue

                constant_name = str(row['constant_name']).strip()
                value = row['value']
                unit = str(row['unit']).strip() if not pd.isna(row['unit']) else ''
                description = str(row['description']).strip() if not pd.isna(row['description']) else ''
                reference = str(row['reference']).strip() if not pd.isna(row['reference']) else ''

                # Convert value to appropriate type
                converted_value = self._convert_value_type(value)

                # Store constant
                self.constants[constant_name] = {
                    'value': converted_value,
                    'unit': unit,
                    'description': description,
                    'reference': reference
                }

                # Also store in parameters dict for backward compatibility
                # Use 'constants' as category
                key = f"constants_{constant_name}"
                self.parameters[key] = {
                    'value': converted_value,
                    'unit': unit,
                    'description': description,
                    'category': 'constants',
                    'parameter': constant_name
                }

                # Add backward compatibility mappings for old parameter names
                backward_compat_mappings = {
                    'gas_constant': ['photosynthesis_parameters_r', 'respiration_parameters_r'],
                    'atmospheric_o2': ['photosynthesis_parameters_o2_mmol_mol'],
                    'seconds_per_hour': ['photosynthesis_parameters_seconds_per_hour'],
                    'hours_per_day': ['photosynthesis_parameters_hours_per_day'],
                    'glucose_to_carbon_ratio': ['respiration_parameters_glucose_to_carbon_ratio'],
                    'carbon_to_co2_ratio': ['respiration_parameters_carbon_to_co2_ratio'],
                    'lai_to_light_interception_factor': ['water_parameters_lai_to_light_interception_factor'],
                    'ppfd_to_photosynthesis_factor': ['canopy_parameters_ppfd_to_photosynthesis_factor'],
                    'co2_molecular_weight': ['ph_parameters_co2_molecular_weight'],
                    'no3_molecular_weight': ['ph_parameters_no3_molecular_weight'],
                    'nh4_molecular_weight': ['ph_parameters_nh4_molecular_weight'],
                    'po4_molecular_weight': ['ph_parameters_po4_molecular_weight'],
                    'mg_to_g_factor': ['ph_parameters_unit_conversion_factor'],
                    'umol_to_g_carbon_ratio': ['photosynthesis_parameters_umol_to_g_carbon_ratio']
                }

                if constant_name in backward_compat_mappings:
                    for old_key in backward_compat_mappings[constant_name]:
                        self.parameters[old_key] = {
                            'value': converted_value,
                            'unit': unit,
                            'description': f"{description} (from constants.csv)",
                            'category': old_key.rsplit('_', 1)[0],
                            'parameter': old_key.split('_', 1)[1] if '_' in old_key else old_key
                        }

            print(f"Loaded {len(self.constants)} universal constants from {self.constants_csv_path}")
        except Exception as e:
            raise ParameterError(f"Failed to load constants from {self.constants_csv_path}: {e}")

    def _load_specialized_file(self, file_path: str, category_name: str):
        """Load parameters from specialized parameter file (e.g., stress.csv)"""
        if not os.path.exists(file_path):
            raise ParameterError(f"Specialized parameter file not found: {file_path}")

        try:
            df = pd.read_csv(file_path, comment='#')
            param_count = 0

            for _, row in df.iterrows():
                if pd.isna(row['parameter_name']):
                    continue

                parameter = str(row['parameter_name']).strip()
                value = row['value']
                unit = str(row['unit']).strip() if not pd.isna(row['unit']) else ''
                description = str(row['description']).strip() if not pd.isna(row['description']) else ''

                # Use category from CSV if available, otherwise use provided category_name
                actual_category = str(row['category']).strip() if 'category' in row and not pd.isna(row['category']) else category_name

                # Convert value to appropriate type
                converted_value = self._convert_value_type(value)

                # Store parameter with category prefix
                key = f"{actual_category}_{parameter}"
                self.parameters[key] = {
                    'value': converted_value,
                    'unit': unit,
                    'description': description,
                    'category': actual_category,
                    'parameter': parameter
                }
                param_count += 1

            print(f"Loaded {param_count} parameters from {file_path} (category: {category_name})")
        except Exception as e:
            raise ParameterError(f"Failed to load specialized parameters from {file_path}: {e}")

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
            # Try float first (handles both regular numbers and scientific notation like 1e-9)
            float_value = float(value)
            # Check if it's actually an integer (no decimal part)
            if float_value.is_integer() and 'e' not in str(value).lower():
                return int(float_value)
            else:
                return float_value
        except (ValueError, TypeError):
            # If not numeric, return as string
            return str(value)

    def get_parameter(self, key: str) -> Any:
        """Get parameter value by key"""
        if key not in self.parameters:
            raise ParameterError(f"Parameter '{key}' not found in CSV - no defaults allowed")
        return self.parameters[key]['value']

    def get_initial(self, key: str, default: Any = None) -> Any:
        """Get initial state value - try parameters first, then use default if provided"""
        if key in self.parameters:
            return self.parameters[key]['value']
        if default is not None:
            return default
        raise ParameterError(f"Initial value '{key}' not found in CSV and no default provided")

    def get_parameter_with_unit(self, key: str) -> Dict[str, Any]:
        """Get parameter with unit and description"""
        if key not in self.parameters:
            raise ParameterError(f"Parameter '{key}' not found in CSV - no defaults allowed")
        return self.parameters[key]

    def get_constant(self, constant_name: str) -> Any:
        """Get universal constant value by name"""
        if constant_name in self.constants:
            return self.constants[constant_name]['value']
        # Try with constants_ prefix for backward compatibility
        key = f"constants_{constant_name}"
        if key in self.parameters:
            return self.parameters[key]['value']
        raise ParameterError(f"Constant '{constant_name}' not found - no defaults allowed")

    def get_constant_with_info(self, constant_name: str) -> Dict[str, Any]:
        """Get constant with unit, description, and reference"""
        if constant_name not in self.constants:
            raise ParameterError(f"Constant '{constant_name}' not found - no defaults allowed")
        return self.constants[constant_name]

    def get_category(self, category: str) -> Dict[str, Any]:
        """Get all parameters for a category"""
        result = {}
        for key, param in self.parameters.items():
            if param['category'] == category:
                # Remove category prefix from parameter name for dict key
                param_name = param['parameter']
                result[param_name] = param['value']
        return result

    def load_initial_state(self, initials_csv_path: str = "input/initials.csv") -> Dict[str, Any]:
        """Load initial state values from initials.csv - follows Rules.md strictly"""
        if not os.path.exists(initials_csv_path):
            raise ParameterError(f"Initials CSV file not found: {initials_csv_path}")

        initial_state = {}
        system_config = {}

        try:
            df = pd.read_csv(initials_csv_path, comment='#', on_bad_lines='skip')

            for _, row in df.iterrows():
                if pd.isna(row['category']) or pd.isna(row['parameter_name']):
                    continue

                category = str(row['category']).strip()
                parameter = str(row['parameter_name']).strip()
                value = self._convert_value_type(row['value'])

                # Organize by category
                if category == 'initial_state':
                    initial_state[parameter] = value
                elif category == 'system_config':
                    system_config[parameter] = value

            return {
                'initial_state': initial_state,
                'system_config': system_config
            }

        except Exception as e:
            raise ParameterError(f"Failed to load initial state from CSV: {e}")

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

        # Sunlit fraction calculation parameters - NO HARDCODED VALUES (Rules.md)
        params_dict['sunlit_fraction_lai_coefficient'] = self.get_parameter('canopy_parameters_sunlit_fraction_lai_coefficient')
        params_dict['sunlit_fraction_minimum'] = self.get_parameter('canopy_parameters_sunlit_fraction_minimum')

        # Physical constants (shared across models)
        params_dict['kelvin_conversion'] = self.get_constant('kelvin_conversion')
        params_dict['reference_temp_kelvin'] = self.get_constant('reference_temp_kelvin')
        params_dict['saturation_vapor_pressure_constant'] = self.get_constant('saturation_vapor_pressure_constant')
        params_dict['vapor_pressure_temp_coefficient'] = self.get_constant('vapor_pressure_temp_coefficient')
        params_dict['vapor_pressure_base_temp'] = self.get_constant('vapor_pressure_base_temp')

        # Model-specific constants
        params_dict['initial_ci_fraction'] = self.get_parameter('photosynthesis_parameters_initial_ci_fraction')
        params_dict['ci_convergence_max_iterations'] = self.get_parameter('photosynthesis_parameters_ci_convergence_max_iterations')
        params_dict['ci_convergence_tolerance_ppm'] = self.get_parameter('photosynthesis_parameters_ci_convergence_tolerance_ppm')
        params_dict['stomatal_conductance_co2_diffusion_ratio'] = self.get_parameter('photosynthesis_parameters_stomatal_conductance_co2_diffusion_ratio')
        params_dict['minimum_stomatal_conductance_threshold'] = self.get_parameter('photosynthesis_parameters_minimum_stomatal_conductance_threshold')
        params_dict['minimum_vpd_threshold'] = self.get_parameter('photosynthesis_parameters_minimum_vpd_threshold')
        params_dict['reference_leaf_nitrogen'] = self.get_parameter('photosynthesis_parameters_reference_leaf_nitrogen')
        params_dict['nitrogen_sensitivity'] = self.get_parameter('photosynthesis_parameters_nitrogen_sensitivity')
        params_dict['water_stress_sensitivity'] = self.get_parameter('photosynthesis_parameters_water_stress_sensitivity')

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

        # Hardcoded value replacements
        params_dict['max_temperature_factor'] = self.get_parameter('respiration_parameters_max_temperature_factor')
        params_dict['minimum_temperature_factor'] = self.get_parameter('respiration_parameters_minimum_temperature_factor')
        params_dict['minimum_respiration_rate_fraction'] = self.get_parameter('respiration_parameters_minimum_respiration_rate_fraction')
        params_dict['default_total_biomass_g'] = self.get_parameter('respiration_parameters_default_total_biomass_g')

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
        params_dict['carbon_content_fraction'] = self.get_parameter('allocation_parameters_carbon_content_fraction')
        params_dict['allocation_efficiency'] = self.get_parameter('allocation_parameters_allocation_efficiency')

        # Carbon allocation fractions - NO HARDCODED VALUES (Rules.md)
        params_dict['carbon_allocation_roots'] = self.get_parameter('allocation_parameters_carbon_allocation_roots')
        params_dict['carbon_allocation_leaves'] = self.get_parameter('allocation_parameters_carbon_allocation_leaves')
        params_dict['carbon_allocation_stems'] = self.get_parameter('allocation_parameters_carbon_allocation_stems')

        # Tissue water content fractions - NO HARDCODED VALUES (Rules.md)
        params_dict['leaf_water_content'] = self.get_parameter('allocation_parameters_leaf_water_content')
        params_dict['stem_water_content'] = self.get_parameter('allocation_parameters_stem_water_content')
        params_dict['root_water_content'] = self.get_parameter('allocation_parameters_root_water_content')

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

        # Build thermal_requirements dictionary from CSV parameters
        thermal_requirements = {}
        transitions = [
            'GE_to_VE', 'VE_to_V1', 'V1_to_V2', 'V2_to_V3', 'V3_to_V4', 'V4_to_V5',
            'V5_to_V6', 'V6_to_V7', 'V7_to_V8', 'V8_to_V9', 'V9_to_V10', 'V10_to_V11+',
            'V11+_to_HI', 'HI_to_HD', 'HD_to_HM', 'HM_to_BI', 'BI_to_FL', 'FL_to_AN',
            'AN_to_SD', 'SD_to_PM'
        ]

        # Load all thermal requirements from CSV - no hardcoded values
        for transition in transitions:
            param_name = f'phenology_parameters_thermal_transition_{transition}'
            thermal_requirements[transition] = self.get_parameter(param_name)

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

        # Development index normalization parameters - NO HARDCODED VALUES (Rules.md)
        params_dict['development_index_thermal_time_denominator'] = self.get_parameter('phenology_parameters_development_index_thermal_time_denominator')
        params_dict['stage_progress_thermal_time_denominator'] = self.get_parameter('phenology_parameters_stage_progress_thermal_time_denominator')

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
        config['temperature']['lethal_min'] = self.get_parameter('stress_parameters_temperature_lethal_min')
        config['temperature']['lethal_max'] = self.get_parameter('phenology_parameters_maximum_temperature')
        config['temperature']['stress_factor_slope'] = self.get_parameter('photosynthesis_parameters_min_stress_factor')
        config['temperature']['acclimation_rate'] = self.get_parameter('phenology_parameters_stress_acceleration_factor')
        config['temperature']['recovery_rate'] = self.get_parameter('stress_parameters_temperature_recovery_rate')

        # Water stress parameters
        config['water'] = {}
        config['water']['drought_threshold'] = self.get_parameter('phenology_parameters_drought_threshold')
        config['water']['critical_threshold'] = self.get_parameter('stress_parameters_water_critical_threshold')
        config['water']['osmotic_adjustment_max'] = self.get_parameter('stress_parameters_max_osmotic_adjustment')
        config['water']['salt_stress_factor'] = self.get_parameter('stress_parameters_salt_stress_osmotic_factor')
        config['water']['recovery_rate'] = self.get_parameter('stress_parameters_water_recovery_rate')

        # Nutrient stress parameters (using N stress as representative)
        config['nutrient'] = {}
        config['nutrient']['deficiency_threshold'] = self.get_parameter('leaf_development_n_stress_threshold')
        config['nutrient']['critical_threshold'] = self.get_parameter('stress_parameters_nutrient_critical_threshold')
        config['nutrient']['toxicity_threshold'] = self.get_parameter('stress_parameters_nutrient_toxicity_threshold')
        config['nutrient']['recovery_rate'] = self.get_parameter('stress_parameters_nutrient_recovery_rate')

        # Light stress parameters
        config['light'] = {}
        config['light']['min_ppfd'] = self.get_parameter('leaf_development_initial_ppfd_above_canopy')
        config['light']['optimal_ppfd'] = self.get_parameter('environment_light_saturation_threshold')
        config['light']['max_ppfd'] = self.get_parameter('stress_parameters_light_max_ppfd')
        config['light']['photoinhibition_threshold'] = self.get_parameter('stress_parameters_light_photoinhibition_threshold')
        config['light']['recovery_rate'] = self.get_parameter('stress_parameters_light_recovery_rate')


        # Salinity/EC stress parameters
        config['salinity'] = {}
        config['salinity']['threshold_ec'] = self.get_parameter('stress_parameters_salinity_threshold_ec')
        config['salinity']['critical_ec'] = self.get_parameter('stress_parameters_salinity_critical_ec')
        config['salinity']['osmotic_factor'] = self.get_parameter('stress_parameters_salt_stress_osmotic_factor')
        config['salinity']['recovery_rate'] = self.get_parameter('stress_parameters_salinity_recovery_rate')

        # Oxygen stress parameters
        config['oxygen'] = {}
        config['oxygen']['critical_min'] = self.get_parameter('stress_parameters_oxygen_critical_min')
        config['oxygen']['optimal_min'] = self.get_parameter('stress_parameters_oxygen_optimal_min')
        config['oxygen']['recovery_rate'] = self.get_parameter('stress_parameters_oxygen_recovery_rate')

        # pH stress parameters
        config['ph'] = {}
        config['ph']['optimal_min'] = self.get_parameter('stress_parameters_ph_optimal_min')
        config['ph']['optimal_max'] = self.get_parameter('stress_parameters_ph_optimal_max')
        config['ph']['stress_range'] = self.get_parameter('stress_parameters_ph_stress_range')
        config['ph']['recovery_rate'] = self.get_parameter('stress_parameters_ph_recovery_rate')

        # Integrated stress parameters
        config['integration'] = {}
        config['integration']['temperature_weight'] = self.get_parameter('genetic_parameters_default_temperature_stress_weight')
        config['integration']['water_weight'] = self.get_parameter('stress_parameters_integration_water_weight')
        config['integration']['nutrient_weight'] = self.get_parameter('stress_parameters_integration_nutrient_weight')
        config['integration']['light_weight'] = self.get_parameter('stress_parameters_integration_light_weight')
        config['integration']['interaction_factor'] = self.get_parameter('stress_parameters_integration_interaction_factor')
        config['integration']['threshold_severe'] = self.get_parameter('stress_parameters_integration_threshold_severe')
        config['integration']['threshold_critical'] = self.get_parameter('stress_parameters_integration_threshold_critical')

        # Memory and acclimation parameters
        config['acclimation'] = {}
        config['acclimation']['temperature_rate'] = self.get_parameter('phenology_parameters_stress_acceleration_factor')
        config['acclimation']['memory_days'] = self.get_parameter('phenology_parameters_environmental_buffer_days')
        config['acclimation']['max_adjustment'] = self.get_parameter('stress_parameters_acclimation_max_adjustment')
        config['acclimation']['decay_rate'] = self.get_parameter('stress_parameters_acclimation_decay_rate')

        # Process sensitivity parameters
        config['sensitivity'] = {}
        config['sensitivity']['photosynthesis'] = self.get_parameter('stress_parameters_sensitivity_photosynthesis')
        config['sensitivity']['respiration'] = self.get_parameter('stress_parameters_sensitivity_respiration')
        config['sensitivity']['transpiration'] = self.get_parameter('stress_parameters_sensitivity_transpiration')
        config['sensitivity']['growth'] = self.get_parameter('stress_parameters_sensitivity_growth')
        config['sensitivity']['development'] = self.get_parameter('stress_parameters_sensitivity_development')

        # Cache timeout
        config['cache_timeout'] = self.get_parameter('simulator_defaults_cache_timeout_global')

        # Stress interaction coefficients - NO HARDCODED VALUES (Rules.md)
        config['stress_interaction_water_temperature_coefficient'] = self.get_parameter('stress_parameters_stress_interaction_water_temperature_coefficient')
        config['stress_interaction_water_nutrient_coefficient'] = self.get_parameter('stress_parameters_stress_interaction_water_nutrient_coefficient')
        config['stress_interaction_temperature_light_coefficient'] = self.get_parameter('stress_parameters_stress_interaction_temperature_light_coefficient')
        config['stress_interaction_nutrient_ph_coefficient'] = self.get_parameter('stress_parameters_stress_interaction_nutrient_ph_coefficient')
        config['stress_interaction_nutrient_salinity_coefficient'] = self.get_parameter('stress_parameters_stress_interaction_nutrient_salinity_coefficient')

        # Stress calculation parameters - NO HARDCODED VALUES (Rules.md)
        config['chronic_stress_weight'] = self.get_parameter('stress_parameters_chronic_stress_weight')
        config['acute_stress_weight'] = self.get_parameter('stress_parameters_acute_stress_weight')
        config['recovery_bonus_factor'] = self.get_parameter('stress_parameters_recovery_bonus_factor')
        config['damage_penalty_factor'] = self.get_parameter('stress_parameters_damage_penalty_factor')
        config['memory_divisor'] = self.get_parameter('stress_parameters_memory_divisor')
        config['chronic_factor_multiplier'] = self.get_parameter('stress_parameters_chronic_factor_multiplier')

        # Threshold calculation coefficients - NO HARDCODED VALUES (Rules.md)
        config['cumulative_threshold_coefficient_base'] = self.get_parameter('stress_parameters_cumulative_threshold_coefficient_base')
        config['cumulative_threshold_coefficient_weight'] = self.get_parameter('stress_parameters_cumulative_threshold_coefficient_weight')
        config['damage_rate_recovery_coefficient'] = self.get_parameter('stress_parameters_damage_rate_recovery_coefficient')
        config['recovery_threshold_offset'] = self.get_parameter('stress_parameters_recovery_threshold_offset')
        config['recovery_time_minimum_rate'] = self.get_parameter('stress_parameters_recovery_time_minimum_rate')
        config['acclimation_capacity_multiplier'] = self.get_parameter('stress_parameters_acclimation_capacity_multiplier')
        config['acclimation_capacity_maximum'] = self.get_parameter('stress_parameters_acclimation_capacity_maximum')
        config['acclimation_memory_decay_factor'] = self.get_parameter('stress_parameters_acclimation_memory_decay_factor')

        return IntegratedStressParameters.from_config(config)

    def create_water_uptake_parameters(self):
        """Create water uptake parameters from CSV"""
        from models.water_uptake_model import WaterUptakeParameters

        # Create config structure for WaterUptakeParameters.from_config()
        config = {
            'water_parameters': {},
            'stress_parameters': {},
            'root_system_parameters': {},
            'phenology_parameters': {}
        }

        # Water parameters
        config['water_parameters']['psychrometric_constant'] = self.get_parameter('water_parameters_psychrometric_constant')
        config['water_parameters']['net_radiation_factor'] = self.get_parameter('water_parameters_net_radiation_factor')
        config['water_parameters']['radiation_offset'] = self.get_parameter('water_parameters_radiation_offset')
        config['water_parameters']['base_crop_coefficient'] = self.get_parameter('water_parameters_base_crop_coefficient')
        config['water_parameters']['lai_coefficient_factor'] = self.get_parameter('water_parameters_lai_coefficient_factor')
        config['water_parameters']['vegetative_stage_factor'] = self.get_parameter('water_parameters_vegetative_stage_factor')
        config['water_parameters']['head_formation_stage_factor'] = self.get_parameter('water_parameters_head_formation_stage_factor')
        config['water_parameters']['mature_stage_factor'] = self.get_parameter('water_parameters_mature_stage_factor')
        # Note: optimal_temperature consolidated into phenology_parameters
        config['water_parameters']['optimal_temperature'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        config['water_parameters']['temperature_sensitivity'] = self.get_parameter('water_parameters_temperature_sensitivity')
        config['water_parameters']['optimal_vpd_min'] = self.get_parameter('water_parameters_optimal_vpd_min')
        config['water_parameters']['optimal_vpd_max'] = self.get_parameter('water_parameters_optimal_vpd_max')
        config['water_parameters']['vpd_sensitivity'] = self.get_parameter('water_parameters_vpd_sensitivity')
        config['water_parameters']['metabolic_water_per_biomass'] = self.get_parameter('water_parameters_metabolic_water_per_biomass')
        config['water_parameters']['metabolic_water_per_lai'] = self.get_parameter('water_parameters_metabolic_water_per_lai')
        config['water_parameters']['temp_tolerance'] = self.get_parameter('water_parameters_temperature_tolerance')
        config['water_parameters']['min_temp_factor'] = self.get_parameter('water_parameters_minimum_temperature_factor')
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

        # Physical constants (shared across models)
        config['water_parameters']['kelvin_conversion'] = self.get_constant('kelvin_conversion')
        config['water_parameters']['saturation_vapor_pressure_constant'] = self.get_constant('saturation_vapor_pressure_constant')
        config['water_parameters']['vapor_pressure_temp_coefficient'] = self.get_constant('vapor_pressure_temp_coefficient')
        config['water_parameters']['vapor_pressure_base_temp'] = self.get_constant('vapor_pressure_base_temp')
        config['water_parameters']['saturation_curve_slope_constant'] = self.get_constant('saturation_curve_slope_constant')
        config['water_parameters']['penman_monteith_conversion'] = self.get_constant('penman_monteith_conversion')
        config['water_parameters']['aerodynamic_resistance_coefficient'] = self.get_constant('aerodynamic_resistance_coefficient')
        config['water_parameters']['wind_speed_coefficient'] = self.get_constant('wind_speed_coefficient')

        # Hardcoded value replacements
        config['water_parameters']['minimum_vpd_threshold'] = self.get_parameter('water_parameters_minimum_vpd_threshold')
        config['water_parameters']['minimum_et0_threshold'] = self.get_parameter('water_parameters_minimum_et0_threshold')
        config['water_parameters']['ground_area_per_plant'] = self.get_parameter('water_parameters_ground_area_per_plant')
        config['water_parameters']['max_lai_coverage_factor'] = self.get_parameter('water_parameters_max_lai_coverage_factor')
        config['water_parameters']['max_root_surface_area_factor'] = self.get_parameter('water_parameters_max_root_surface_area_factor')
        config['water_parameters']['cavitation_gradient_denominator'] = self.get_parameter('water_parameters_cavitation_gradient_denominator')
        config['water_parameters']['lai_to_light_interception_factor'] = self.get_parameter('water_parameters_lai_to_light_interception_factor')
        config['water_parameters']['temperature_response_exponent_denominator'] = self.get_parameter('water_parameters_temperature_response_exponent_denominator')
        config['water_parameters']['vpd_effect_divisor'] = self.get_parameter('water_parameters_vpd_effect_divisor')
        config['water_parameters']['transpiration_base_rate_scale_factor'] = self.get_parameter('water_parameters_transpiration_base_rate_scale_factor')
        config['water_parameters']['transpiration_scaling_multiplier'] = self.get_parameter('water_parameters_transpiration_scaling_multiplier')
        config['water_parameters']['lai_coefficient_threshold'] = self.get_parameter('water_parameters_lai_coefficient_threshold')
        config['water_parameters']['minimum_coverage_factor'] = self.get_parameter('water_parameters_minimum_coverage_factor')
        config['water_parameters']['minimum_cavitation_factor'] = self.get_parameter('water_parameters_minimum_cavitation_factor')
        config['water_parameters']['maximum_vpd_effect'] = self.get_parameter('water_parameters_maximum_vpd_effect')

        return WaterUptakeParameters.from_config(config)

    def create_nutrient_parameters(self):
        """Create nutrient parameters from CSV"""
        from models.nutrient_models import NutrientParameters

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

        # Kinetic parameters - Sulfate
        config['kinetics_s_so4_vmax'] = self.get_parameter('nutrient_parameters_kinetics_s_so4_vmax')
        config['kinetics_s_so4_km'] = self.get_parameter('nutrient_parameters_kinetics_s_so4_km')
        config['kinetics_s_so4_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_s_so4_min_conc')

        # Kinetic parameters - Iron
        config['kinetics_fe_vmax'] = self.get_parameter('nutrient_parameters_kinetics_fe_vmax')
        config['kinetics_fe_km'] = self.get_parameter('nutrient_parameters_kinetics_fe_km')
        config['kinetics_fe_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_fe_min_conc')

        # Kinetic parameters - Manganese
        config['kinetics_mn_vmax'] = self.get_parameter('nutrient_parameters_kinetics_mn_vmax')
        config['kinetics_mn_km'] = self.get_parameter('nutrient_parameters_kinetics_mn_km')
        config['kinetics_mn_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_mn_min_conc')

        # Kinetic parameters - Zinc
        config['kinetics_zn_vmax'] = self.get_parameter('nutrient_parameters_kinetics_zn_vmax')
        config['kinetics_zn_km'] = self.get_parameter('nutrient_parameters_kinetics_zn_km')
        config['kinetics_zn_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_zn_min_conc')

        # Kinetic parameters - Copper
        config['kinetics_cu_vmax'] = self.get_parameter('nutrient_parameters_kinetics_cu_vmax')
        config['kinetics_cu_km'] = self.get_parameter('nutrient_parameters_kinetics_cu_km')
        config['kinetics_cu_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_cu_min_conc')

        # Kinetic parameters - Boron
        config['kinetics_b_vmax'] = self.get_parameter('nutrient_parameters_kinetics_b_vmax')
        config['kinetics_b_km'] = self.get_parameter('nutrient_parameters_kinetics_b_km')
        config['kinetics_b_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_b_min_conc')

        # Kinetic parameters - Molybdenum
        config['kinetics_mo_vmax'] = self.get_parameter('nutrient_parameters_kinetics_mo_vmax')
        config['kinetics_mo_km'] = self.get_parameter('nutrient_parameters_kinetics_mo_km')
        config['kinetics_mo_min_conc'] = self.get_parameter('nutrient_parameters_kinetics_mo_min_conc')

        # Load mobility parameters for nutrients that have them in CSV
        # Map specific nutrient forms to their general element names (consolidated parameters)
        nutrient_csv_mapping = {
            "N-NO3": "nitrogen",      # NO3 and NH4 both use nitrogen parameters
            "N-NH4": "nitrogen",
            "P-PO4": "phosphorus",    # PO4 uses phosphorus parameters
            "K": "potassium",
            "Ca": "calcium",
            "Mg": "magnesium",
            "S-SO4": "sulfur",        # SO4 uses sulfur parameters
            "Fe": "iron",
            "Mn": "manganese",
            "Zn": "zinc",
            "Cu": "copper",
            "B": "boron",
            "Mo": "molybdenum"
        }

        nutrients = ["N-NO3", "N-NH4", "P-PO4", "K", "Ca", "Mg", "S-SO4", "Fe", "Mn", "Zn", "Cu", "B", "Mo"]
        for nutrient in nutrients:
            csv_key = nutrient_csv_mapping[nutrient]

            # Load the consolidated parameters from CSV (one set per element, not per form)
            config[f'mobility_classifications_{nutrient}_mobility'] = self.get_parameter(f'nutrient_parameters_mobility_classifications_{csv_key}_mobility')
            config[f'mobility_classifications_{nutrient}_transport'] = self.get_parameter(f'nutrient_parameters_mobility_classifications_{csv_key}_transport')
            config[f'mobility_classifications_{nutrient}_remobilization_efficiency'] = self.get_parameter(f'nutrient_parameters_remobilization_efficiency_{csv_key}')
            config[f'mobility_classifications_{nutrient}_deficiency_mobility'] = self.get_parameter(f'nutrient_parameters_deficiency_mobility_{csv_key}')
            config[f'mobility_classifications_{nutrient}_retranslocation_rate'] = self.get_parameter(f'nutrient_parameters_retranslocation_rate_{csv_key}')
            config[f'xylem_transport_rates_{nutrient}'] = self.get_parameter(f'nutrient_parameters_xylem_transport_rates_{csv_key}')

            # Calculate phloem rates as fraction of xylem rates from CSV parameter
            phloem_factor = self.get_parameter('nutrient_parameters_phloem_transport_factor')
            config[f'phloem_transport_rates_{nutrient}'] = config[f'xylem_transport_rates_{nutrient}'] * phloem_factor

        # Ion properties for EC calculation (literature-based, CSV-driven)
        # Global temperature coefficient
        config['temperature_coefficient_alpha'] = self.get_parameter('nutrient_parameters_temperature_coefficient_alpha')

        # Per-ion properties: molar mass, limiting molar conductivity at 25C, valence
        for nutrient in nutrients:
            config[f'molar_mass_{nutrient}'] = self.get_parameter(f'nutrient_parameters_molar_mass_{nutrient}')
            config[f'lambda0_25C_{nutrient}'] = self.get_parameter(f'nutrient_parameters_lambda0_25C_{nutrient}')
            config[f'valence_{nutrient}'] = self.get_parameter(f'nutrient_parameters_valence_{nutrient}')

        # Provide minimal required parameters for complex data structures
        # Load base values from CSV - per Rules.md: no hardcoded values
        base_buffering = self.get_parameter('nitrogen_balance_buffering_capacity_base')
        base_storage = self.get_parameter('nitrogen_balance_storage_pool_size_base')
        redistribution_threshold = self.get_parameter('nitrogen_balance_redistribution_threshold')
        redistribution_rate = self.get_parameter('nitrogen_balance_redistribution_rate')
        sink_strength_base = self.get_parameter('nitrogen_balance_sink_strength_base')
        sink_strength_repro = self.get_parameter('nitrogen_balance_sink_strength_reproductive')

        organs = ["leaves", "stems", "roots"]
        major_nutrients = ["N-NO3", "N-NH4", "P-PO4", "K"]
        for organ in organs:
            for nutrient in major_nutrients:
                config[f'buffering_capacities_{organ}_{nutrient}'] = base_buffering
                config[f'storage_pool_sizes_{organ}_{nutrient}'] = base_storage

        for nutrient in ["N-NO3", "N-NH4", "P-PO4", "K", "Ca", "Mg", "S-SO4"]:
            config[f'redistribution_thresholds_{nutrient}'] = redistribution_threshold
            config[f'stress_redistribution_rates_{nutrient}'] = redistribution_rate

        stages = ["vegetative", "reproductive", "senescence"]
        for stage in stages:
            for organ in ["leaves", "stems", "roots"]:
                config[f'sink_strength_coefficients_{stage}_{organ}'] = sink_strength_base
            if stage == "reproductive":
                config[f'sink_strength_coefficients_{stage}_reproductive'] = sink_strength_repro

        config['cache_timeout'] = self.get_parameter('simulator_defaults_cache_timeout_global')

        # Hardcoded value replacements
        config['ec_stress_min_threshold'] = self.get_parameter('nutrient_parameters_ec_stress_min_threshold')
        config['ec_boost_max_n'] = self.get_parameter('nutrient_parameters_ec_boost_max_n')
        config['ec_boost_max_p'] = self.get_parameter('nutrient_parameters_ec_boost_max_p')
        config['ec_boost_max_k'] = self.get_parameter('nutrient_parameters_ec_boost_max_k')
        config['ec_boost_max_fe'] = self.get_parameter('nutrient_parameters_ec_boost_max_fe')
        config['temperature_factor_base'] = self.get_parameter('nutrient_parameters_temperature_factor_base')
        config['ph_factor_base'] = self.get_parameter('nutrient_parameters_ph_factor_base')
        config['reference_daily_growth_rate'] = self.get_parameter('nutrient_parameters_reference_daily_growth_rate')
        config['rhizosphere_thickness_cm'] = self.get_parameter('nutrient_parameters_rhizosphere_thickness_cm')
        config['minimum_root_zone_volume_L'] = self.get_parameter('nutrient_parameters_minimum_root_zone_volume_L')
        config['transport_pool_fraction_multiplier'] = self.get_parameter('nutrient_parameters_transport_pool_fraction_multiplier')
        config['deficiency_mobility_very_high_factor'] = self.get_parameter('nutrient_parameters_deficiency_mobility_very_high_factor')
        config['deficiency_mobility_high_factor'] = self.get_parameter('nutrient_parameters_deficiency_mobility_high_factor')
        config['deficiency_mobility_low_factor'] = self.get_parameter('nutrient_parameters_deficiency_mobility_low_factor')
        config['deficiency_mobility_very_low_factor'] = self.get_parameter('nutrient_parameters_deficiency_mobility_very_low_factor')
        config['base_supply_storage_pool_fraction'] = self.get_parameter('nutrient_parameters_base_supply_storage_pool_fraction')
        config['base_supply_buffer_pool_fraction'] = self.get_parameter('nutrient_parameters_base_supply_buffer_pool_fraction')
        config['stress_redistribution_threshold'] = self.get_parameter('nutrient_parameters_stress_redistribution_threshold')
        config['max_transportable_nutrient_fraction'] = self.get_parameter('nutrient_parameters_max_transportable_nutrient_fraction')
        config['transport_reference_temperature'] = self.get_parameter('nutrient_parameters_transport_reference_temperature')
        config['bidirectional_xylem_fraction'] = self.get_parameter('nutrient_parameters_bidirectional_xylem_fraction')
        config['bidirectional_phloem_fraction'] = self.get_parameter('nutrient_parameters_bidirectional_phloem_fraction')
        config['metabolic_pool_export_limit_fraction'] = self.get_parameter('nutrient_parameters_metabolic_pool_export_limit_fraction')
        config['transport_pool_max_fraction'] = self.get_parameter('nutrient_parameters_transport_pool_max_fraction')
        config['transport_pool_target_fraction'] = self.get_parameter('nutrient_parameters_transport_pool_target_fraction')
        config['excess_to_metabolic_fraction'] = self.get_parameter('nutrient_parameters_excess_to_metabolic_fraction')
        config['excess_to_storage_fraction'] = self.get_parameter('nutrient_parameters_excess_to_storage_fraction')
        config['excess_to_buffer_fraction'] = self.get_parameter('nutrient_parameters_excess_to_buffer_fraction')
        config['highly_mobile_base_efficiency'] = self.get_parameter('nutrient_parameters_highly_mobile_base_efficiency')
        config['moderately_mobile_base_efficiency'] = self.get_parameter('nutrient_parameters_moderately_mobile_base_efficiency')
        config['poorly_mobile_base_efficiency'] = self.get_parameter('nutrient_parameters_poorly_mobile_base_efficiency')
        config['immobile_base_efficiency'] = self.get_parameter('nutrient_parameters_immobile_base_efficiency')
        config['bidirectional_transport_factor'] = self.get_parameter('nutrient_parameters_bidirectional_transport_factor')
        config['complex_transport_factor'] = self.get_parameter('nutrient_parameters_complex_transport_factor')
        config['xylem_only_transport_factor'] = self.get_parameter('nutrient_parameters_xylem_only_transport_factor')
        config['phloem_only_transport_factor'] = self.get_parameter('nutrient_parameters_phloem_only_transport_factor')
        config['transport_limitation_threshold'] = self.get_parameter('nutrient_parameters_transport_limitation_threshold')

        # Tissue composition parameters - NO HARDCODED VALUES
        config['tissue_nitrogen_content_fraction'] = self.get_parameter('nutrient_parameters_tissue_nitrogen_content_fraction')
        config['tissue_phosphorus_content_fraction'] = self.get_parameter('nutrient_parameters_tissue_phosphorus_content_fraction')
        config['tissue_potassium_content_fraction'] = self.get_parameter('nutrient_parameters_tissue_potassium_content_fraction')

        # Organ allocation fractions - NO HARDCODED VALUES
        config['organ_allocation_no3_roots'] = self.get_parameter('nutrient_parameters_organ_allocation_no3_roots')
        config['organ_allocation_nh4_roots'] = self.get_parameter('nutrient_parameters_organ_allocation_nh4_roots')
        config['organ_allocation_po4_roots'] = self.get_parameter('nutrient_parameters_organ_allocation_po4_roots')
        config['organ_allocation_k_roots'] = self.get_parameter('nutrient_parameters_organ_allocation_k_roots')
        config['organ_allocation_no3_leaves'] = self.get_parameter('nutrient_parameters_organ_allocation_no3_leaves')
        config['organ_allocation_nh4_leaves'] = self.get_parameter('nutrient_parameters_organ_allocation_nh4_leaves')
        config['organ_allocation_po4_leaves'] = self.get_parameter('nutrient_parameters_organ_allocation_po4_leaves')
        config['organ_allocation_k_leaves'] = self.get_parameter('nutrient_parameters_organ_allocation_k_leaves')
        config['organ_allocation_no3_stems'] = self.get_parameter('nutrient_parameters_organ_allocation_no3_stems')
        config['organ_allocation_nh4_stems'] = self.get_parameter('nutrient_parameters_organ_allocation_nh4_stems')
        config['organ_allocation_po4_stems'] = self.get_parameter('nutrient_parameters_organ_allocation_po4_stems')
        config['organ_allocation_k_stems'] = self.get_parameter('nutrient_parameters_organ_allocation_k_stems')

        # Carbon assimilate allocation - NO HARDCODED VALUES (Rules.md)
        config['carbon_assimilate_allocation_roots'] = self.get_parameter('nutrient_parameters_carbon_assimilate_allocation_roots')
        config['carbon_assimilate_allocation_leaves'] = self.get_parameter('nutrient_parameters_carbon_assimilate_allocation_leaves')
        config['carbon_assimilate_allocation_stems'] = self.get_parameter('nutrient_parameters_carbon_assimilate_allocation_stems')

        return NutrientParameters.from_config(config)

    def create_canopy_architecture_parameters(self):
        """Create canopy architecture parameters from CSV"""
        from models.canopy_architecture import CanopyArchitectureParameters

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


    def create_root_system_parameters(self):
        """Create root system parameters from CSV"""
        from models.root_system_model import RootSystemParameters, HydroponicSystemType

        # Create configuration sections required by from_config
        config = {}

        # Core root system parameters - ALL from CSV per Rules.md
        config['container_volume'] = self.get_parameter('root_system_parameters_container_volume_default')
        config['channel_length'] = self.get_parameter('root_system_parameters_channel_length_default')
        config['system_type'] = self.get_parameter('root_system_parameters_system_type')
        config['channel_width'] = self.get_parameter('root_system_parameters_channel_width_default')
        config['channel_depth'] = self.get_parameter('root_system_parameters_channel_depth_default')
        config['n_channels'] = self.get_parameter('root_system_parameters_n_channels_default')
        config['root_zone_independent'] = bool(self.get_parameter('root_system_parameters_root_zone_independent'))

        # Initial root state parameters - ALL from CSV per Rules.md
        config['initial_root_biomass'] = self.get_parameter('root_system_parameters_initial_root_biomass')
        config['initial_root_length'] = self.get_parameter('root_system_parameters_initial_root_length')
        config['initial_root_diameter'] = self.get_parameter('root_system_parameters_initial_root_diameter')

        # Root growth parameters - ALL from CSV per Rules.md
        config['primary_root_growth_rate'] = self.get_parameter('root_system_parameters_primary_root_growth_rate')
        config['lateral_root_density'] = self.get_parameter('root_system_parameters_lateral_root_density')
        config['branching_angle_mean'] = self.get_parameter('root_system_parameters_branching_angle_mean')
        config['branching_angle_std'] = self.get_parameter('root_system_parameters_branching_angle_std')

        # Root type fractions - ALL from CSV per Rules.md
        config['fine_root_fraction'] = self.get_parameter('root_system_parameters_fine_root_fraction')
        config['medium_root_fraction'] = self.get_parameter('root_system_parameters_medium_root_fraction')
        config['coarse_root_fraction'] = self.get_parameter('root_system_parameters_coarse_root_fraction')

        # Root diameter parameters
        config['fine_diameter_mean'] = self.get_parameter('root_system_parameters_fine_diameter_mean')
        config['fine_diameter_std'] = self.get_parameter('root_system_parameters_fine_diameter_std')
        config['medium_diameter_mean'] = self.get_parameter('root_system_parameters_medium_diameter_mean')
        config['medium_diameter_std'] = self.get_parameter('root_system_parameters_medium_diameter_std')
        config['coarse_diameter_mean'] = self.get_parameter('root_system_parameters_coarse_diameter_mean')
        config['coarse_diameter_std'] = self.get_parameter('root_system_parameters_coarse_diameter_std')

        # Root turnover and longevity
        config['fine_turnover_rate'] = self.get_parameter('root_system_parameters_fine_turnover_rate')
        config['medium_turnover_rate'] = self.get_parameter('root_system_parameters_medium_turnover_rate')
        config['coarse_turnover_rate'] = self.get_parameter('root_system_parameters_coarse_turnover_rate')
        config['fine_root_half_life_days'] = self.get_parameter('root_system_parameters_fine_half_life_days')
        config['medium_root_half_life_days'] = self.get_parameter('root_system_parameters_medium_half_life_days')
        config['coarse_root_half_life_days'] = self.get_parameter('root_system_parameters_coarse_half_life_days')

        # Root activity parameters
        config['root_zone_efficiency_factor'] = self.get_parameter('root_system_parameters_zone_efficiency_factor')
        config['fine_min_activity'] = self.get_parameter('root_system_parameters_fine_min_activity')
        config['medium_min_activity'] = self.get_parameter('root_system_parameters_medium_min_activity')
        config['coarse_min_activity'] = self.get_parameter('root_system_parameters_coarse_min_activity')
        config['establishment_plateau_days'] = self.get_parameter('root_system_parameters_establishment_plateau_days')
        config['initial_root_activity'] = self.get_parameter('root_system_parameters_initial_activity')

        # Root effectiveness parameters
        config['fine_root_effectiveness'] = self.get_parameter('root_system_parameters_fine_effectiveness')
        config['medium_root_effectiveness'] = self.get_parameter('root_system_parameters_medium_effectiveness')
        config['coarse_root_effectiveness'] = self.get_parameter('root_system_parameters_coarse_effectiveness')

        # Temperature parameters - use consolidated from phenology
        config['optimal_temperature_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        config['optimal_temperature_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')
        config['q10_factor'] = self.get_parameter('root_system_parameters_q10_factor')

        # Phenology parameters sub-dict (required by RootSystemParameters.from_config)
        config['phenology_parameters'] = {
            'optimal_temperature_min': self.get_parameter('phenology_parameters_optimal_temperature_min'),
            'optimal_temperature_max': self.get_parameter('phenology_parameters_optimal_temperature_max')
        }

        # Flow and environmental parameters
        config['optimal_flow_rate'] = self.get_parameter('root_system_parameters_optimal_flow_rate')
        config['flow_stress_threshold'] = self.get_parameter('root_system_parameters_flow_stress_threshold')
        config['root_growth_auxin_decay_rate'] = self.get_parameter('root_system_parameters_auxin_decay_rate')
        config['root_optimal_density'] = self.get_parameter('root_system_parameters_optimal_density')
        config['root_density_stress_factor'] = self.get_parameter('root_system_parameters_density_stress_factor')
        config['root_temp_optimum'] = self.get_parameter('root_system_parameters_root_temperature_optimum')
        config['root_temp_max'] = self.get_parameter('root_system_parameters_root_temperature_maximum')
        config['root_temp_min_factor'] = self.get_parameter('root_system_parameters_root_temperature_minimum_factor')
        config['root_oxygen_optimum'] = self.get_parameter('root_system_parameters_oxygen_optimum')
        config['root_oxygen_min_factor'] = self.get_parameter('root_system_parameters_root_oxygen_minimum_factor')

        # pH and stress parameters
        config['ph_stress_range_acidic'] = self.get_parameter('root_system_parameters_ph_stress_range_acidic')
        config['ph_stress_range_basic'] = self.get_parameter('root_system_parameters_ph_stress_range_basic')
        config['ph_stress_factor'] = self.get_parameter('root_system_parameters_ph_stress_factor')
        config['young_root_activity'] = self.get_parameter('root_system_parameters_young_root_activity')
        config['old_root_activity'] = self.get_parameter('root_system_parameters_old_root_activity')

        # Additional hardcoded parameters extracted from code
        config['temperature_range_factor'] = self.get_parameter('root_system_parameters_temperature_range_factor')
        config['min_temperature_factor'] = self.get_parameter('root_system_parameters_minimum_temperature_factor')
        config['max_temperature_factor'] = self.get_parameter('root_system_parameters_max_temperature_factor')
        config['low_flow_factor'] = self.get_parameter('root_system_parameters_low_flow_factor')
        config['high_flow_factor'] = self.get_parameter('root_system_parameters_high_flow_factor')
        config['ph_zone_min'] = self.get_parameter('root_system_parameters_ph_zone_min')
        config['ph_zone_max'] = self.get_parameter('root_system_parameters_ph_zone_max')
        config['min_ph_factor'] = self.get_parameter('root_system_parameters_min_ph_factor')
        config['ph_penalty_factor'] = self.get_parameter('root_system_parameters_ph_penalty_factor')

        # Zone fraction parameters
        config['nft_zone_1_fraction'] = self.get_parameter('root_system_parameters_nft_zone_1_fraction')
        config['nft_zone_2_fraction'] = self.get_parameter('root_system_parameters_nft_zone_2_fraction')
        config['nft_zone_3_fraction'] = self.get_parameter('root_system_parameters_nft_zone_3_fraction')
        config['dwc_zone_1_fraction'] = self.get_parameter('root_system_parameters_dwc_zone_1_fraction')
        config['dwc_zone_2_fraction'] = self.get_parameter('root_system_parameters_dwc_zone_2_fraction')
        config['dwc_zone_3_fraction'] = self.get_parameter('root_system_parameters_dwc_zone_3_fraction')
        config['general_zone_1_fraction'] = self.get_parameter('root_system_parameters_general_zone_1_fraction')
        config['general_zone_2_fraction'] = self.get_parameter('root_system_parameters_general_zone_2_fraction')
        config['general_zone_3_fraction'] = self.get_parameter('root_system_parameters_general_zone_3_fraction')
        config['general_zone_4_fraction'] = self.get_parameter('root_system_parameters_general_zone_4_fraction')

        # Root biomass and threshold parameters
        config['root_biomass_density'] = self.get_parameter('root_system_parameters_biomass_density')
        config['coarse_root_min_threshold'] = self.get_parameter('root_system_parameters_coarse_min_threshold')
        config['fine_root_min_threshold'] = self.get_parameter('root_system_parameters_fine_min_threshold')
        config['diameter_minimum_limit'] = self.get_parameter('root_system_parameters_diameter_minimum_limit')

        # Growth potential weights
        config['auxin_gradient_weight'] = self.get_parameter('root_system_parameters_auxin_gradient_weight')
        config['nutrient_signal_weight'] = self.get_parameter('root_system_parameters_nutrient_signal_weight')
        config['oxygen_effect_weight'] = self.get_parameter('root_system_parameters_oxygen_effect_weight')
        config['competition_effect_weight'] = self.get_parameter('root_system_parameters_competition_effect_weight')
        config['temperature_effect_weight'] = self.get_parameter('root_system_parameters_temperature_effect_weight')
        config['min_growth_potential'] = self.get_parameter('root_system_parameters_min_growth_potential')
        config['max_growth_potential'] = self.get_parameter('root_system_parameters_max_growth_potential')
        config['max_temp_threshold'] = self.get_parameter('root_system_parameters_maximum_temperature_threshold')
        config['temp_decay_factor'] = self.get_parameter('root_system_parameters_temperature_decay_factor')

        # Flow and transport parameters
        config['flow_rate_offset'] = self.get_parameter('root_system_parameters_flow_rate_offset')
        config['flow_rate_multiplier'] = self.get_parameter('root_system_parameters_flow_rate_multiplier')
        config['transport_temp_exponent'] = self.get_parameter('root_system_parameters_transport_temperature_exponent')

        # Minimum value parameters
        config['minimum_surface_area'] = self.get_parameter('root_system_parameters_minimum_surface_area')
        config['minimum_biomass'] = self.get_parameter('root_system_parameters_minimum_biomass')
        config['minimum_volume'] = self.get_parameter('root_system_parameters_minimum_volume')
        config['effective_area_minimum'] = self.get_parameter('root_system_parameters_effective_area_minimum')

        # Nutrient uptake parameters (required by model)
        nutrients = ['NO3', 'NH4', 'PO4', 'K', 'Ca', 'Mg', 'SO4']
        for nutrient in nutrients:
            config[f'{nutrient.lower()}_uptake_vmax'] = self.get_parameter(f'root_system_parameters_{nutrient.lower()}_uptake_vmax')
            config[f'{nutrient.lower()}_uptake_km'] = self.get_parameter(f'root_system_parameters_{nutrient.lower()}_uptake_km')

        # System multipliers for each hydroponic system type
        system_types = ['nutrient_film_technique', 'deep_water_culture', 'aeroponics', 'drip', 'wick_system', 'ebb_flow']
        for sys_type in system_types:
            config[f'system_multipliers_{sys_type}_root_length_multiplier'] = self.get_parameter(f'root_system_parameters_multipliers_{sys_type}_root_length_multiplier')
            config[f'system_multipliers_{sys_type}_surface_area_multiplier'] = self.get_parameter(f'root_system_parameters_multipliers_{sys_type}_surface_area_multiplier')
            config[f'system_multipliers_{sys_type}_branching_multiplier'] = self.get_parameter(f'root_system_parameters_multipliers_{sys_type}_branching_multiplier')

        # Nutrient demand weights
        config['nutrient_demand_weight_no3'] = self.get_parameter('root_system_parameters_nutrient_demand_weight_no3')
        config['nutrient_demand_weight_po4'] = self.get_parameter('root_system_parameters_nutrient_demand_weight_po4')
        config['nutrient_demand_weight_k'] = self.get_parameter('root_system_parameters_nutrient_demand_weight_k')
        config['nutrient_demand_weight_ca'] = self.get_parameter('root_system_parameters_nutrient_demand_weight_ca')
        config['nutrient_demand_weight_mg'] = self.get_parameter('root_system_parameters_nutrient_demand_weight_mg')

        # Nutrient reference concentrations
        config['nutrient_ref_concentration_no3'] = self.get_parameter('root_system_parameters_nutrient_ref_concentration_no3')
        config['nutrient_ref_concentration_po4'] = self.get_parameter('root_system_parameters_nutrient_ref_concentration_po4')
        config['nutrient_ref_concentration_k'] = self.get_parameter('root_system_parameters_nutrient_ref_concentration_k')
        config['nutrient_ref_concentration_ca'] = self.get_parameter('root_system_parameters_nutrient_ref_concentration_ca')
        config['nutrient_ref_concentration_mg'] = self.get_parameter('root_system_parameters_nutrient_ref_concentration_mg')

        # Nutrient competition groups (comma-separated strings)
        config['nutrient_competition_no3'] = self.get_parameter('root_system_parameters_nutrient_competition_no3')
        config['nutrient_competition_nh4'] = self.get_parameter('root_system_parameters_nutrient_competition_nh4')
        config['nutrient_competition_po4'] = self.get_parameter('root_system_parameters_nutrient_competition_po4')
        config['nutrient_competition_k'] = self.get_parameter('root_system_parameters_nutrient_competition_k')
        config['nutrient_competition_ca'] = self.get_parameter('root_system_parameters_nutrient_competition_ca')
        config['nutrient_competition_mg'] = self.get_parameter('root_system_parameters_nutrient_competition_mg')

        # pH optima for nutrients
        config['ph_optimum_no3_min'] = self.get_parameter('root_system_parameters_ph_optimum_no3_min')
        config['ph_optimum_no3_max'] = self.get_parameter('root_system_parameters_ph_optimum_no3_max')
        config['ph_optimum_nh4_min'] = self.get_parameter('root_system_parameters_ph_optimum_nh4_min')
        config['ph_optimum_nh4_max'] = self.get_parameter('root_system_parameters_ph_optimum_nh4_max')
        config['ph_optimum_po4_min'] = self.get_parameter('root_system_parameters_ph_optimum_po4_min')
        config['ph_optimum_po4_max'] = self.get_parameter('root_system_parameters_ph_optimum_po4_max')
        config['ph_optimum_k_min'] = self.get_parameter('root_system_parameters_ph_optimum_k_min')
        config['ph_optimum_k_max'] = self.get_parameter('root_system_parameters_ph_optimum_k_max')
        config['ph_optimum_ca_min'] = self.get_parameter('root_system_parameters_ph_optimum_ca_min')
        config['ph_optimum_ca_max'] = self.get_parameter('root_system_parameters_ph_optimum_ca_max')
        config['ph_optimum_mg_min'] = self.get_parameter('root_system_parameters_ph_optimum_mg_min')
        config['ph_optimum_mg_max'] = self.get_parameter('root_system_parameters_ph_optimum_mg_max')

        # Cache timeout
        config['cache_timeout'] = self.get_parameter('root_system_parameters_cache_timeout')

        # Hardcoded value replacements
        config['min_flow_rate_multiplier'] = self.get_parameter('root_system_parameters_min_flow_rate_multiplier')
        config['default_michaelis_constant'] = self.get_parameter('root_system_parameters_default_michaelis_constant')
        config['default_reference_nutrient_concentration'] = self.get_parameter('root_system_parameters_default_reference_nutrient_concentration')
        config['nutrient_inhibition_minimum_factor'] = self.get_parameter('root_system_parameters_nutrient_inhibition_minimum_factor')
        config['competition_effect_minimum_factor'] = self.get_parameter('root_system_parameters_competition_effect_minimum_factor')
        config['heat_stress_minimum_factor'] = self.get_parameter('root_system_parameters_heat_stress_minimum_factor')
        config['optimization_temp_min'] = self.get_parameter('root_system_parameters_optimization_temp_min')
        config['optimization_temp_max'] = self.get_parameter('root_system_parameters_optimization_temp_max')
        config['optimization_temp_step'] = self.get_parameter('root_system_parameters_optimization_temp_step')
        config['optimization_flow_min'] = self.get_parameter('root_system_parameters_optimization_flow_min')
        config['optimization_flow_max'] = self.get_parameter('root_system_parameters_optimization_flow_max')
        config['optimization_flow_step'] = self.get_parameter('root_system_parameters_optimization_flow_step')

        return RootSystemParameters.from_config(config)


    def create_genetic_parameters(self):
        """Create genetic parameters from CSV - follows Rules.md strictly"""
        from models.genetic_parameters import (
            GeneticParameterDatabase, CultivarProfile, GeneticCoefficients,
            LettuceType, GeneticTrait
        )

        # Build configuration from CSV parameters - ALL from CSV per Rules.md
        config = {
            'default_air_temperature': self.get_parameter('simulator_defaults_default_air_temperature'),
            'default_humidity': self.get_parameter('simulator_defaults_default_humidity'),
            'default_light_intensity': self.get_parameter('simulator_defaults_default_light_intensity'),
            'cache_timeout': self.get_parameter('simulator_defaults_cache_timeout_global')
        }

        # Create genetic database with CSV config
        genetic_db = GeneticParameterDatabase(config)

        # Build genetic coefficients from CSV
        genetic_coeffs = GeneticCoefficients(
            EM_FL=self.get_parameter('genetic_parameters_EM_FL'),
            FL_SH=self.get_parameter('genetic_parameters_FL_SH'),
            FL_SD=self.get_parameter('genetic_parameters_FL_SD'),
            SD_PM=self.get_parameter('genetic_parameters_SD_PM'),
            FL_LF=self.get_parameter('genetic_parameters_FL_LF'),
            LFMAX=self.get_parameter('genetic_parameters_LFMAX'),
            SLAVR=self.get_parameter('genetic_parameters_SLAVR'),
            SIZLF=self.get_parameter('genetic_parameters_SIZLF'),
            XFRT=self.get_parameter('genetic_parameters_XFRT'),
            SFDUR=self.get_parameter('genetic_parameters_SFDUR'),
            SDPDV=self.get_parameter('genetic_parameters_SDPDV'),
            PODUR=self.get_parameter('genetic_parameters_PODUR'),
            WTPSD=self.get_parameter('genetic_parameters_WTPSD'),
            THRSH=self.get_parameter('genetic_parameters_THRSH'),
            SDPRO=self.get_parameter('genetic_parameters_SDPRO'),
            SDLIP=self.get_parameter('genetic_parameters_SDLIP'),
            EC_TOLERANCE=self.get_parameter('genetic_parameters_EC_TOLERANCE'),
            ROOT_ACTIVITY=self.get_parameter('genetic_parameters_ROOT_ACTIVITY'),
            PHOTOSYNTHETIC_CAPACITY=self.get_parameter('genetic_parameters_PHOTOSYNTHETIC_CAPACITY'),
            NITRATE_EFFICIENCY=self.get_parameter('genetic_parameters_NITRATE_EFFICIENCY')
        )

        # Build trait values from CSV
        trait_values = {
            GeneticTrait.DAYS_TO_EMERGENCE: self.get_parameter('genetic_parameters_trait_days_to_emergence'),
            GeneticTrait.DAYS_TO_HARVEST: self.get_parameter('genetic_parameters_trait_days_to_harvest'),
            GeneticTrait.BOLTING_TOLERANCE: self.get_parameter('genetic_parameters_trait_bolting_tolerance'),
            GeneticTrait.LEAF_SIZE: self.get_parameter('genetic_parameters_trait_leaf_size'),
            GeneticTrait.PLANT_ARCHITECTURE: self.get_parameter('genetic_parameters_trait_plant_architecture'),
            GeneticTrait.ROOT_DEVELOPMENT: self.get_parameter('genetic_parameters_trait_root_development'),
            GeneticTrait.YIELD_POTENTIAL: self.get_parameter('genetic_parameters_trait_yield_potential'),
            GeneticTrait.CHLOROPHYLL_CONTENT: self.get_parameter('genetic_parameters_trait_chlorophyll_content'),
            GeneticTrait.CAROTENOID_CONTENT: self.get_parameter('genetic_parameters_trait_carotenoid_content'),
            GeneticTrait.VITAMIN_C_CONTENT: self.get_parameter('genetic_parameters_trait_vitamin_c_content'),
            GeneticTrait.NITRATE_ACCUMULATION: self.get_parameter('genetic_parameters_trait_nitrate_accumulation'),
            GeneticTrait.HEAT_TOLERANCE: self.get_parameter('genetic_parameters_trait_heat_tolerance'),
            GeneticTrait.COLD_TOLERANCE: self.get_parameter('genetic_parameters_trait_cold_tolerance'),
            GeneticTrait.SALINITY_TOLERANCE: self.get_parameter('genetic_parameters_trait_salinity_tolerance'),
            GeneticTrait.DISEASE_RESISTANCE: self.get_parameter('genetic_parameters_trait_disease_resistance'),
            GeneticTrait.GROWTH_RATE: self.get_parameter('genetic_parameters_trait_growth_rate')
        }

        # Create cultivar profile from CSV
        cultivar_profile = CultivarProfile(
            cultivar_id=self.get_parameter('genetic_parameters_cultivar_id'),
            cultivar_name=self.get_parameter('genetic_parameters_cultivar_name'),
            lettuce_type=LettuceType(self.get_parameter('genetic_parameters_lettuce_type')),
            genetic_coefficients=genetic_coeffs,
            yield_potential=self.get_parameter('genetic_parameters_yield_potential'),
            adaptation_score=self.get_parameter('genetic_parameters_adaptation_score'),
            trait_values=trait_values,
            maturity_days=int(self.get_parameter('genetic_parameters_maturity_days'))
        )

        # Add cultivar to database
        genetic_db.add_cultivar(cultivar_profile)

        return genetic_db, cultivar_profile

    def create_leaf_development_parameters(self):
        """Create leaf development parameters from CSV"""
        from models.leaf_development import LeafParameters

        config = {}

        # Leaf development parameters
        config['leaf_development'] = {}
        leaf_dev_params = [
            'base_phyllochron', 'max_leaf_number', 'initial_leaf_number', 'leaf_appearance_rate',
            'max_individual_leaf_area', 'leaf_area_expansion_rate', 'daily_thermal_time_equivalent', 'drought_threshold', 'n_stress_threshold',
            'temperature_stress_sensitivity', 'initial_leaf_area_factor', 'initial_thermal_time_factor',
            'emerging_to_expanding_factor', 'late_leaf_phyllochron_factor', 'very_late_leaf_phyllochron_factor',
            'early_leaf_size_factor', 'late_leaf_size_factor', 'leaf_maturation_thermal_time',
            'leaf_lifespan_thermal_time', 'senescence_threshold_age', 'senescence_rate_base',
            'minimum_active_leaf_area', 'minimum_visible_leaf_area', 'late_leaf_vstage_threshold',
            'very_late_leaf_vstage_threshold', 'early_leaf_position_threshold', 'middle_leaf_position_threshold',
            'early_position_scaling_factor', 'late_position_scaling_factor', 'minimum_temperature', 'maximum_temperature', 'specific_leaf_area'
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
        config['thermal_time']['base_temp'] = self.get_parameter('leaf_development_minimum_temperature')
        config['thermal_time']['optimal_temp_min'] = self.get_parameter('phenology_parameters_optimal_temperature_min')
        config['thermal_time']['optimal_temp_max'] = self.get_parameter('phenology_parameters_optimal_temperature_max')
        config['thermal_time']['max_temp'] = self.get_parameter('leaf_development_maximum_temperature')

        # Cache timeout
        config['leaf_development']['cache_timeout'] = self.get_parameter('simulator_defaults_cache_timeout_global')

        return LeafParameters.from_config(config)

    def create_nitrogen_balance_parameters(self):
        """Create nitrogen balance parameters from CSV"""
        from models.nitrogen_balance import NitrogenBalanceParameters

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

        # Critical N concentrations for all organs (now in nutrient.csv)
        config['critical_n_concentrations'] = {}
        concentration_levels = ['minimum', 'critical', 'optimal', 'maximum']
        for organ in organs:
            config['critical_n_concentrations'][organ] = {}
            for level in concentration_levels:
                config['critical_n_concentrations'][organ][level] = self.get_parameter(
                    f'nutrient_parameters_critical_n_concentrations_{organ}_{level}')

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
        config['cache_timeout'] = self.get_parameter('simulator_defaults_cache_timeout_global')

        return NitrogenBalanceParameters.from_config(config)


