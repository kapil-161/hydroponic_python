"""
Configuration File Loader for Hydroponic Simulation
Loads user-friendly CSV configuration files
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

from ..data.hydroponic_system import HydroSystemConfig, CropParameters
from ..models.nutrient_models import NutrientParams


@dataclass
class ModelConstants:
    """Model constants loaded from file."""
    carbon_to_biomass_ratio: float = 0.45
    growth_respiration_fraction: float = 0.25
    vegetative_leaf_allocation: float = 0.60
    vegetative_stem_allocation: float = 0.20
    vegetative_root_allocation: float = 0.20
    reproductive_leaf_allocation: float = 0.40
    reproductive_stem_allocation: float = 0.35
    reproductive_root_allocation: float = 0.25
    optimal_light_intensity: float = 15.0
    optimal_ec_min: float = 2.0
    optimal_ec_max: float = 2.6
    optimal_vpd_min: float = 0.6
    optimal_vpd_max: float = 1.0
    optimal_root_temperature: float = 20.0
    root_temp_tolerance: float = 3.0
    vpd_stress_high_factor: float = 0.25
    vpd_stress_low_factor: float = 0.15
    ec_stress_high_factor: float = 0.2
    ec_stress_low_threshold: float = 0.8
    ec_stress_low_factor: float = 0.1


class ConfigFileLoader:
    """Load configuration from user-friendly CSV files."""
    
    def __init__(self, config_dir: str = "input", experiment_code: str = None):
        """
        Initialize config loader.
        
        Args:
            config_dir: Directory containing configuration files (defaults to 'input')
            experiment_code: Experiment code in format 'CROP_EXP###_YEAR' (e.g., 'LET_EXP001_2024')
        """
        self.config_dir = Path(config_dir)
        self.experiment_code = experiment_code
        
    def _get_filename(self, base_name: str) -> str:
        """Get filename with experiment code prefix if specified."""
        if self.experiment_code:
            # Require complete experiment file sets - no fallback
            return f"{self.experiment_code}_{base_name}"
        return base_name
    
    def load_nutrient_solution(self, filename: str = "nutrient_solution.csv") -> Dict[str, NutrientParams]:
        """Load nutrient solution configuration from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Nutrient solution file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        nutrients = {}
        
        for _, row in df.iterrows():
            # Determine charge based on nutrient type
            charge_map = {'N-NO3': -1, 'P-PO4': -3, 'K': 1, 'Ca': 2, 'Mg': 2}
            charge = charge_map.get(row['symbol'], 0)
            
            nutrient = NutrientParams(
                nutrient_id=row['symbol'],
                nutrient_name=row['nutrient_name'],
                chemical_form=row['symbol'],
                initial_conc=float(row['initial_ppm']),
                recharge_conc=float(row['optimal_ppm']),
                uptake_conc=float(row['initial_ppm']) * 0.9,  # 90% of initial as minimum
                sensitivity_coeff=1.0,  # Default sensitivity
                is_nutritive=True,
                min_conc=float(row.get('minimum_ppm', row['initial_ppm'] * 0.8)) if 'minimum_ppm' in row else float(row['initial_ppm']) * 0.8,
                max_conc=float(row['max_ppm']),
                charge=charge
            )
            nutrients[nutrient.nutrient_id] = nutrient
        
        return nutrients
    
    def load_system_settings(self, filename: str = "system_settings.csv") -> HydroSystemConfig:
        """Load system settings from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"System settings file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        settings = {row['setting_name']: row['value'] for _, row in df.iterrows()}
        
        return HydroSystemConfig(
            system_id="HYD1",
            crop_id="LETT",
            location_id="LAB",
            tank_volume=float(settings.get('tank_volume', 500)),
            flow_rate=float(settings.get('flow_rate', 50)),
            system_type=str(settings.get('system_type', 'NFT')),
            system_area=float(settings.get('system_area', 1.0)),
            n_plants=int(float(settings.get('number_of_plants', 12))),
            description=f"{settings.get('system_type', 'NFT')} - Lettuce production"
        )
    
    def load_crop_parameters(self, filename: str = "crop_parameters.csv") -> CropParameters:
        """Load crop parameters from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Crop parameters file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        params = {row['parameter_name']: row['value'] for _, row in df.iterrows()}
        
        return CropParameters(
            crop_id="LETT",
            crop_name=str(params.get('crop_name', 'Lettuce')),
            kcb=float(params.get('crop_coefficient', 0.90)),
            phi=float(params.get('plant_density', 0.85)),
            crop_height=float(params.get('maximum_height', 0.30)),
            root_zone_depth=float(params.get('root_depth', 0.15)),
            laid=float(params.get('leaf_area_index', 2.0))
        )
    
    def load_experiment_settings(self, filename: str = "experiment_settings.csv") -> Dict[str, Any]:
        """Load experiment settings from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Experiment settings file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        settings = {}
        
        for _, row in df.iterrows():
            value = row['value']
            # Convert boolean strings
            if str(value).lower() in ['true', 'false']:
                value = str(value).lower() == 'true'
            # Try to convert numeric strings
            elif str(value).replace('.', '', 1).isdigit():
                value = float(value) if '.' in str(value) else int(float(value))
            
            settings[row['setting_name']] = value
        
        return settings
    
    def load_stress_parameters(self, filename: str = "stress_parameters.csv") -> Dict[str, Any]:
        """Load stress parameters from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Stress parameters file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        return {row['parameter_name']: float(row['value']) for _, row in df.iterrows()}
    
    def load_environment_parameters(self, filename: str = "environment_parameters.csv") -> Dict[str, Any]:
        """Load environment parameters from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Environment parameters file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        return {row['parameter_name']: float(row['value']) for _, row in df.iterrows()}
    
    def load_model_constants(self, filename: str = "model_constants.csv") -> ModelConstants:
        """Load model constants from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Model constants file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        constants_dict = {row['constant_name']: float(row['value']) for _, row in df.iterrows()}
        
        # Create ModelConstants instance with loaded values
        return ModelConstants(
            carbon_to_biomass_ratio=constants_dict.get('carbon_to_biomass_ratio', 0.45),
            growth_respiration_fraction=constants_dict.get('growth_respiration_fraction', 0.25),
            vegetative_leaf_allocation=constants_dict.get('vegetative_leaf_allocation', 0.60),
            vegetative_stem_allocation=constants_dict.get('vegetative_stem_allocation', 0.20),
            vegetative_root_allocation=constants_dict.get('vegetative_root_allocation', 0.20),
            reproductive_leaf_allocation=constants_dict.get('reproductive_leaf_allocation', 0.40),
            reproductive_stem_allocation=constants_dict.get('reproductive_stem_allocation', 0.35),
            reproductive_root_allocation=constants_dict.get('reproductive_root_allocation', 0.25),
            optimal_light_intensity=constants_dict.get('optimal_light_intensity', 15.0),
            optimal_ec_min=constants_dict.get('optimal_ec_min', 2.0),
            optimal_ec_max=constants_dict.get('optimal_ec_max', 2.6),
            optimal_vpd_min=constants_dict.get('optimal_vpd_min', 0.6),
            optimal_vpd_max=constants_dict.get('optimal_vpd_max', 1.0),
            optimal_root_temperature=constants_dict.get('optimal_root_temperature', 20.0),
            root_temp_tolerance=constants_dict.get('root_temp_tolerance', 3.0),
            vpd_stress_high_factor=constants_dict.get('vpd_stress_high_factor', 0.25),
            vpd_stress_low_factor=constants_dict.get('vpd_stress_low_factor', 0.15),
            ec_stress_high_factor=constants_dict.get('ec_stress_high_factor', 0.2),
            ec_stress_low_threshold=constants_dict.get('ec_stress_low_threshold', 0.8),
            ec_stress_low_factor=constants_dict.get('ec_stress_low_factor', 0.1)
        )
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about available configuration files."""
        config_files = [
            'nutrient_solution.csv',
            'system_settings.csv', 
            'crop_parameters.csv',
            'experiment_settings.csv',
            'model_constants.csv'
        ]
        
        info = {
            'config_directory': str(self.config_dir),
            'files': {}
        }
        
        for filename in config_files:
            filepath = self.config_dir / filename
            info['files'][filename] = {
                'exists': filepath.exists(),
                'path': str(filepath),
                'size_bytes': filepath.stat().st_size if filepath.exists() else 0
            }
        
        return info
    
    def load_genetic_parameters(self, filename: str = "genetic_parameters.csv") -> Dict[str, Dict[str, Any]]:
        """Load genetic parameters from CSV."""
        filename = self._get_filename(filename)
        csv_path = self.config_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Genetic parameters file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        genetics = {}
        
        for _, row in df.iterrows():
            cultivar_id = row['cultivar_id']
            if cultivar_id not in genetics:
                genetics[cultivar_id] = {
                    'cultivar_name': row['cultivar_name'],
                    'parameters': {}
                }
            genetics[cultivar_id]['parameters'][row['parameter']] = float(row['value'])
        
        return genetics
    
    def load_complete_simulation_parameters(self) -> ModelConstants:
        """Load complete simulation parameters from all CSV files."""
        try:
            # Load all parameter sets
            constants = self.load_model_constants()
            stress_params = self.load_stress_parameters()
            env_params = self.load_environment_parameters()
            
            # Create comprehensive ModelConstants with all parameters
            return ModelConstants(
                carbon_to_biomass_ratio=constants.carbon_to_biomass_ratio,
                growth_respiration_fraction=constants.growth_respiration_fraction,
                vegetative_leaf_allocation=constants.vegetative_leaf_allocation,
                vegetative_stem_allocation=constants.vegetative_stem_allocation,
                vegetative_root_allocation=constants.vegetative_root_allocation,
                reproductive_leaf_allocation=constants.reproductive_leaf_allocation,
                reproductive_stem_allocation=constants.reproductive_stem_allocation,
                reproductive_root_allocation=constants.reproductive_root_allocation,
                optimal_light_intensity=env_params.get('optimal_light_intensity', constants.optimal_light_intensity),
                optimal_ec_min=env_params.get('optimal_ec', constants.optimal_ec_min),
                optimal_ec_max=env_params.get('max_ec', constants.optimal_ec_max),
                optimal_vpd_min=env_params.get('optimal_vpd_min', constants.optimal_vpd_min),
                optimal_vpd_max=env_params.get('optimal_vpd_max', constants.optimal_vpd_max),
                optimal_root_temperature=env_params.get('optimal_temperature', constants.optimal_root_temperature),
                root_temp_tolerance=stress_params.get('temp_stress_threshold', constants.root_temp_tolerance),
                vpd_stress_high_factor=stress_params.get('vpd_stress_high_factor', constants.vpd_stress_high_factor),
                vpd_stress_low_factor=stress_params.get('vpd_stress_low_factor', constants.vpd_stress_low_factor),
                ec_stress_high_factor=stress_params.get('ec_stress_high_factor', constants.ec_stress_high_factor),
                ec_stress_low_threshold=env_params.get('min_ec', constants.ec_stress_low_threshold),
                ec_stress_low_factor=stress_params.get('ec_stress_low_factor', constants.ec_stress_low_factor)
            )
        except FileNotFoundError:
            # Fallback to just model_constants.csv if other files don't exist
            return self.load_model_constants()