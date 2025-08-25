"""
CSV Configuration Adapter
Provides compatibility with old config loader interface using CSV files
"""

from typing import Dict, Any
from .config_file_loader import ConfigFileLoader


class CSVConfigAdapter:
    """Adapter to make CSV config loader compatible with old JSON interface."""
    
    def __init__(self, config_dir: str = "input", experiment_code: str = None):
        self.loader = ConfigFileLoader(config_dir, experiment_code)
        self._genetic_params = None
        self._stress_params = None
        self._env_params = None
        self._model_constants = None
        
    def _load_all_params(self):
        """Lazy load all parameters when first needed."""
        if self._genetic_params is None:
            try:
                self._genetic_params = self.loader.load_genetic_parameters()
                self._stress_params = self.loader.load_stress_parameters()
                self._env_params = self.loader.load_environment_parameters()
                self._model_constants = self.loader.load_model_constants()
                self._respiration_params = self._load_csv_params("respiration_parameters.csv")
                self._photosynthesis_params = self._load_csv_params("photosynthesis_parameters.csv")
                self._canopy_params = self._load_csv_params("canopy_parameters.csv")
                self._nitrogen_params = self._load_csv_params("nitrogen_parameters.csv")
                self._senescence_params = self._load_csv_params("senescence_parameters.csv")
                self._phenology_params = self._load_csv_params("phenology_parameters.csv")
                self._water_params = self._load_csv_params("water_parameters.csv")
                self._system_params = self._load_csv_params("system_parameters.csv")
                self._env_control_params = self._load_csv_params("environmental_control_parameters.csv")
                self._root_zone_params = self._load_csv_params("root_zone_parameters.csv")
            except FileNotFoundError:
                # Use defaults if files don't exist
                self._genetic_params = self._get_default_genetics()
                self._stress_params = self._get_default_stress()
                self._env_params = self._get_default_environment()
                self._model_constants = self.loader.load_model_constants()
                self._respiration_params = self._get_default_respiration()
                self._photosynthesis_params = self._get_default_photosynthesis()
                self._canopy_params = self._get_default_canopy()
                self._nitrogen_params = self._get_default_nitrogen()
                self._senescence_params = self._get_default_senescence()
                self._phenology_params = self._get_default_phenology()
                self._water_params = self._get_default_water()
                self._system_params = self._get_default_system()
                self._env_control_params = self._get_default_env_control()
                self._root_zone_params = self._get_default_root_zone()
    
    def get_genetic_parameters(self) -> Dict[str, Any]:
        """Get genetic parameters compatible with old interface."""
        self._load_all_params()
        return self._genetic_params
    
    def get_stress_parameters(self) -> Dict[str, Any]:
        """Get stress parameters."""
        self._load_all_params()
        return {
            'VPD_STRESS_FACTOR_HIGH': self._stress_params.get('vpd_stress_high_factor', 0.25),
            'VPD_STRESS_FACTOR_LOW': self._stress_params.get('vpd_stress_low_factor', 0.15),
            'EC_STRESS_FACTOR_HIGH': self._stress_params.get('ec_stress_high_factor', 0.2),
            'EC_STRESS_FACTOR_LOW': self._stress_params.get('ec_stress_low_factor', 0.1),
            'TEMP_STRESS_THRESHOLD': self._stress_params.get('temp_stress_threshold', 3.0),
            'TEMP_STRESS_FACTOR': self._stress_params.get('temp_stress_factor', 0.05),
            'HEAT_STRESS_THRESHOLD': self._stress_params.get('heat_stress_threshold', 0.03),
            'COLD_STRESS_THRESHOLD': self._stress_params.get('cold_stress_threshold', 0.02),
            'WATER_STRESS_FACTOR': self._stress_params.get('water_stress_factor', 0.004)
        }
    
    def get_growth_parameters(self) -> Dict[str, Any]:
        """Get growth parameters."""
        self._load_all_params()
        return {
            'LEAF_GROWTH_RATIO': self._model_constants.vegetative_leaf_allocation,
            'STEM_GROWTH_RATIO': self._model_constants.vegetative_stem_allocation,
            'ROOT_GROWTH_RATIO': self._model_constants.vegetative_root_allocation
        }
    
    def get_environment_parameters(self) -> Dict[str, Any]:
        """Get environment parameters.""" 
        self._load_all_params()
        return {
            'OPTIMAL_LIGHT_INTENSITY': self._env_params.get('optimal_light_intensity', 15.0),
            'MIN_EC': self._env_params.get('min_ec', 0.8),
            'MAX_EC': self._env_params.get('max_ec', 2.6),
            'OPTIMAL_EC': self._env_params.get('optimal_ec', 2.0),
            'OPTIMAL_VPD_MIN': self._env_params.get('optimal_vpd_min', 0.6),
            'OPTIMAL_VPD_MAX': self._env_params.get('optimal_vpd_max', 1.0),
            'OPTIMAL_TEMPERATURE': self._env_params.get('optimal_temperature', 20.0),
            'OPTIMAL_TEMPERATURE_MAX': self._env_params.get('optimal_temperature_max', 26.0),
            'OPTIMAL_TEMPERATURE_MIN': self._env_params.get('optimal_temperature_min', 16.0),
            'MIN_HUMIDITY': self._env_params.get('min_humidity', 60.0)
        }
    
    def get_physiology_parameters(self) -> Dict[str, Any]:
        """Get physiology parameters."""
        self._load_all_params()
        return {
            'CARBON_TO_GLUCOSE_RATIO': self._model_constants.carbon_to_biomass_ratio,
            'GROWTH_RESPIRATION_RATE': self._model_constants.growth_respiration_fraction
        }
    
    def get_canopy_parameters(self) -> Dict[str, Any]:
        """Get canopy parameters."""
        self._load_all_params()
        return {
            'SPECIFIC_LEAF_AREA': self._canopy_params.get('specific_leaf_area', 275.0),
            'light_extinction': self._canopy_params.get('light_extinction', 0.65),
            'leaf_angle': self._canopy_params.get('leaf_angle', 45.0),
            'leaf_thickness': self._canopy_params.get('leaf_thickness', 0.3),
            'maximum_lai': self._canopy_params.get('maximum_lai', 8.0),
            'canopy_width': self._canopy_params.get('canopy_width', 0.3),
            'canopy_height': self._canopy_params.get('canopy_height', 0.25),
            'leaf_area_ratio': self._canopy_params.get('leaf_area_ratio', 0.8),
            'light_interception_efficiency': self._canopy_params.get('light_interception_efficiency', 0.95)
        }
    
    def get_water_parameters(self) -> Dict[str, Any]:
        """Get water parameters."""
        self._load_all_params()
        return {
            'LAI_WATER_DEMAND_FACTOR': self._water_params.get('lai_water_demand_factor', 0.2)
        }
    
    def get_nutrient_parameters(self) -> Dict[str, Any]:
        """Get nutrient parameters."""
        self._load_all_params()
        return {
            'NITROGEN_UPTAKE_EFFICIENCY': self._nitrogen_params.get('uptake_efficiency', 0.1)
        }
    
    def get_system_parameters(self) -> Dict[str, Any]:
        """Get system parameters."""
        self._load_all_params()
        return {
            'RESERVOIR_TOPUP_FRACTION': self._system_params.get('reservoir_topup_fraction', 0.3)
        }
    
    def _get_default_genetics(self) -> Dict[str, Any]:
        """Default genetic parameters if CSV not found."""
        return {
            'HYDRO_001': {
                'cultivar_name': 'Salanova Green Butter',
                'parameters': {
                    'EM': 0.85, 'P1': 120.0, 'P3': 0.52, 'P5': 850.0,
                    'G1': 7.5, 'G2': 0.0025, 'G3': 1.2, 'PHINT': 95.0,
                    'SLAVR': 275.0, 'SIZLF': 180.0, 'XFRT': 1.0, 'WTLF': 0.75,
                    'SFDUR': 25.0, 'SDPDV': 1.8, 'PODUR': 10.0, 'THRSH': 78.0,
                    'SDPRO': 0.42, 'SDLIP': 0.18
                }
            }
        }
    
    def _get_default_stress(self) -> Dict[str, Any]:
        """Default stress parameters."""
        return {
            'vpd_stress_high_factor': 0.25,
            'vpd_stress_low_factor': 0.15,
            'ec_stress_high_factor': 0.2,
            'ec_stress_low_factor': 0.1,
            'temp_stress_threshold': 3.0,
            'temp_stress_factor': 0.05,
            'heat_stress_threshold': 0.03,
            'cold_stress_threshold': 0.02,
            'water_stress_factor': 0.004
        }
    
    def _get_default_environment(self) -> Dict[str, Any]:
        """Default environment parameters."""
        return {
            'optimal_light_intensity': 15.0,
            'min_ec': 0.8, 'max_ec': 2.6, 'optimal_ec': 2.0,
            'optimal_vpd_min': 0.6, 'optimal_vpd_max': 1.0,
            'optimal_temperature': 20.0,
            'optimal_temperature_max': 26.0,
            'optimal_temperature_min': 16.0,
            'min_humidity': 60.0
        }
    
    def _load_csv_params(self, filename: str) -> Dict[str, Any]:
        """Load parameters from a CSV file."""
        try:
            import pandas as pd
            from pathlib import Path
            filename = self.loader._get_filename(filename)
            csv_path = Path(self.loader.config_dir) / filename
            df = pd.read_csv(csv_path)
            params = {}
            for _, row in df.iterrows():
                value = row['value']
                # Handle different data types
                if str(value).lower() in ['true', 'false']:
                    params[row['parameter_name']] = str(value).lower()
                elif str(value).replace('.', '', 1).replace('-', '', 1).isdigit():
                    params[row['parameter_name']] = float(value)
                else:
                    params[row['parameter_name']] = str(value)
            return params
        except FileNotFoundError:
            return {}
    
    def get_respiration_parameters(self) -> Dict[str, Any]:
        """Get respiration parameters."""
        self._load_all_params()
        return {
            'MAINTENANCE_COEFFICIENT': self._respiration_params.get('maintenance_coefficient', 0.015),
            'TEMPERATURE_COEFFICIENT': self._respiration_params.get('temperature_coefficient', 0.08),
            'BIOMASS_COEFFICIENT': self._respiration_params.get('biomass_coefficient', 0.02),
            'maintenance_base_rate': self._respiration_params.get('maintenance_base_rate', 0.02),
            'reference_temperature': self._respiration_params.get('reference_temperature', 25.0),
            'q10_factor': self._respiration_params.get('q10_factor', 2.0),
            'growth_efficiency': self._respiration_params.get('growth_efficiency', 0.75),
            'age_effect_coefficient': self._respiration_params.get('age_effect_coefficient', 0.001),
            'max_age_effect': self._respiration_params.get('max_age_effect', 2.0),
            'tissue_factors': {
                'leaves': self._respiration_params.get('tissue_factor_leaves', 1.0),
                'stems': self._respiration_params.get('tissue_factor_stems', 0.8),
                'roots': self._respiration_params.get('tissue_factor_roots', 1.2),
                'reproductive': self._respiration_params.get('tissue_factor_reproductive', 1.5)
            },
            'acclimation_rate': self._respiration_params.get('acclimation_rate', 0.05)
        }
    
    def get_photosynthesis_parameters(self) -> Dict[str, Any]:
        """Get photosynthesis parameters."""
        self._load_all_params()
        return {
            'LIGHT_USE_EFFICIENCY': self._photosynthesis_params.get('light_use_efficiency', 2.5),
            'CO2_COMPENSATION': self._photosynthesis_params.get('co2_compensation', 60.0),
            'MAX_CARBOXYLATION': self._photosynthesis_params.get('max_carboxylation', 120.0),
            'kc': self._photosynthesis_params.get('kc', 460.0),
            'ko': self._photosynthesis_params.get('ko', 330.0),
            'gamma_star': self._photosynthesis_params.get('gamma_star', 42.75),
            'jmax_25': self._photosynthesis_params.get('jmax_25', 110.0),
            'vcmax_25': self._photosynthesis_params.get('vcmax_25', 60.0),
            'theta': self._photosynthesis_params.get('theta', 0.7),
            'phi_psii': self._photosynthesis_params.get('phi_psii', 0.3),
            'alpha': self._photosynthesis_params.get('alpha', 0.24),
            'rd_25': self._photosynthesis_params.get('rd_25', 1.5),
            'eaj': self._photosynthesis_params.get('eaj', 37000.0),
            'eav': self._photosynthesis_params.get('eav', 65330.0),
            'ear': self._photosynthesis_params.get('ear', 46390.0),
            'r': self._photosynthesis_params.get('r', 8.314),
            'ci_fraction': self._photosynthesis_params.get('ci_fraction', 0.7)
        }
    
    def get_nitrogen_parameters(self) -> Dict[str, Any]:
        """Get nitrogen parameters."""
        self._load_all_params()
        return {
            'N_UPTAKE_EFFICIENCY': self._nitrogen_params.get('uptake_efficiency', 0.8),
            'N_TRANSLOCATION': self._nitrogen_params.get('translocation_rate', 0.4),
            'NITROGEN_UPTAKE_EFFICIENCY': self._nitrogen_params.get('uptake_efficiency', 0.1)
        }
    
    def get_senescence_parameters(self) -> Dict[str, Any]:
        """Get senescence parameters."""
        self._load_all_params()
        return {
            'SENESCENCE_RATE': self._senescence_params.get('senescence_rate', 0.02),
            'N_SENESCENCE': self._senescence_params.get('nitrogen_recovery', 0.6)
        }
    
    def get_environmental_control_parameters(self) -> Dict[str, Any]:
        """Get environmental control parameters."""
        self._load_all_params()
        return {
            'TARGET_VPD': self._env_control_params.get('target_vpd', 0.8),
            'CO2_SETPOINT': self._env_control_params.get('co2_setpoint', 400)
        }
    
    def get_root_zone_parameters(self) -> Dict[str, Any]:
        """Get root zone parameters.""" 
        self._load_all_params()
        return {
            'OPTIMAL_TEMPERATURE': self._root_zone_params.get('optimal_temperature', 20.0),
            'ROOT_CONDUCTIVITY': self._root_zone_params.get('root_conductivity', 0.1)
        }
    
    def _get_default_respiration(self) -> Dict[str, Any]:
        """Default respiration parameters."""
        return {
            'maintenance_coefficient': 0.015,
            'temperature_coefficient': 0.08,
            'biomass_coefficient': 0.02
        }
    
    def _get_default_photosynthesis(self) -> Dict[str, Any]:
        """Default photosynthesis parameters."""
        return {
            'light_use_efficiency': 2.5,
            'co2_compensation': 60.0,
            'max_carboxylation': 120.0
        }
    
    def _get_default_canopy(self) -> Dict[str, Any]:
        """Default canopy parameters."""
        return {
            'light_extinction': 0.65,
            'leaf_angle': 45.0
        }
    
    def _get_default_nitrogen(self) -> Dict[str, Any]:
        """Default nitrogen parameters."""
        return {
            'uptake_efficiency': 0.8,
            'translocation_rate': 0.4
        }
    
    def _get_default_senescence(self) -> Dict[str, Any]:
        """Default senescence parameters."""
        return {
            'senescence_rate': 0.02,
            'nitrogen_recovery': 0.6
        }
    
    def get_phenology_parameters(self) -> Dict[str, Any]:
        """Get phenology parameters."""
        self._load_all_params()
        return {
            'BASE_TEMPERATURE': self._phenology_params.get('base_temperature', 4.0),
            'OPTIMAL_TEMPERATURE_MIN': self._phenology_params.get('optimal_temperature_min', 15.0),
            'OPTIMAL_TEMPERATURE_MAX': self._phenology_params.get('optimal_temperature_max', 25.0),
            'MAXIMUM_TEMPERATURE': self._phenology_params.get('maximum_temperature', 35.0),
            'PHOTOPERIOD_SENSITIVE': self._phenology_params.get('photoperiod_sensitive', 'false') == 'true',
            'CRITICAL_PHOTOPERIOD': self._phenology_params.get('critical_photoperiod', 12.0),
            'BOLTING_PHOTOPERIOD_THRESHOLD': self._phenology_params.get('bolting_photoperiod_threshold', 14.0),
            'BOLTING_TEMPERATURE_THRESHOLD': self._phenology_params.get('bolting_temperature_threshold', 25.0),
            'COLD_REQUIREMENT_DAYS': self._phenology_params.get('cold_requirement_days', 0.0),
            'THERMAL_TIME_SCALE': self._phenology_params.get('thermal_time_scale', 0.85),
            'THERMAL_REQUIREMENTS': {
                "GE_to_VE": 80.0, "VE_to_V1": 45.0, "V1_to_V2": 35.0, "V2_to_V3": 35.0,
                "V3_to_V4": 35.0, "V4_to_V5": 35.0, "V5_to_V6": 35.0, "V6_to_V7": 35.0,
                "V7_to_V8": 35.0, "V8_to_V9": 35.0, "V9_to_V10": 35.0, "V10_to_V11+": 40.0,
                "V11+_to_HI": 120.0, "HI_to_HD": 180.0, "HD_to_HM": 200.0, "HM_to_PM": 100.0
            }
        }
    
    def _get_default_phenology(self) -> Dict[str, Any]:
        """Default phenology parameters."""
        return {
            'base_temperature': 4.0,
            'optimal_temperature_min': 15.0,
            'optimal_temperature_max': 25.0,
            'maximum_temperature': 35.0,
            'photoperiod_sensitive': 'false',
            'critical_photoperiod': 12.0,
            'bolting_photoperiod_threshold': 14.0,
            'bolting_temperature_threshold': 25.0,
            'cold_requirement_days': 0.0,
            'thermal_time_scale': 0.85
        }
    
    def _get_default_water(self) -> Dict[str, Any]:
        """Default water parameters."""
        return {
            'lai_water_demand_factor': 0.2
        }
    
    def _get_default_system(self) -> Dict[str, Any]:
        """Default system parameters."""
        return {
            'reservoir_topup_fraction': 0.3
        }
    
    def _get_default_env_control(self) -> Dict[str, Any]:
        """Default environmental control parameters."""
        return {
            'target_vpd': 0.8,
            'co2_setpoint': 400
        }
    
    def _get_default_root_zone(self) -> Dict[str, Any]:
        """Default root zone parameters."""
        return {
            'optimal_temperature': 20.0,
            'root_conductivity': 0.1
        }