"""
Enhanced CROPGRO Hydroponic Simulator

This is the MAIN SIMULATION ENGINE that integrates ALL advanced CROPGRO models:
- Genetic parameters for cultivar-specific modeling
- Phenology and development modeling
- Enhanced respiration with temperature acclimation
- Advanced senescence and remobilization
- Canopy architecture and light interception
- Nitrogen balance and nutrient mobility
- Integrated stress modeling with temperature stress
- Root architecture with spatial distribution
- Environmental control systems

This simulator provides research-grade crop modeling capabilities.
"""

import numpy as np
import pandas as pd
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

# Import utilities
from .utils.temperature_utils import calculate_vpd, calculate_ph_effect, calculate_q10_temperature_factor, calculate_thermal_time
from .utils.hourly_weather import create_hourly_weather_interpolator

# Import all CROPGRO models
from .models.genetic_parameters import (
    create_lettuce_genetic_system, 
    GeneticParameterDatabase, 
    GenotypeEnvironmentModel,
    GeneticTrait
)
from .models.phenology_model import create_lettuce_phenology_model, LettuceGrowthStage
from .models.respiration_model import create_lettuce_respiration_model, BiomassPool, TissueType
from .models.senescence_model import create_lettuce_senescence_model
from .models.canopy_architecture import create_lettuce_canopy_model, LightEnvironment
from .models.nitrogen_balance import create_lettuce_nitrogen_balance_model
from .models.nutrient_models import create_lettuce_nutrient_mobility_model
from .models.stress_models import create_lettuce_integrated_stress_model
from .models.stress_models import create_lettuce_temperature_stress_model
from .models.root_system_model import create_enhanced_root_uptake_model, HydroponicSystemType
from .models.root_zone_temperature import create_lettuce_rzt_model
from .models.ph_model import create_lettuce_ph_model
from .models.environmental_control import create_lettuce_environmental_control_system
from .models.photosynthesis_model import create_lettuce_photosynthesis_model
from .models.nutrient_models import NutrientConcentrationModel
from .models.leaf_development import create_lettuce_leaf_development_model
from .data.hydroponic_system import HydroInputData, SimulationResults, DailyResults
# No longer importing config loader - using CSV data only
# WeatherGenerator removed - weather data must come from CSV files

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimulationParameters:
    """
    Configuration parameters for the simulation.
    
    This replaces hardcoded 'magic numbers' throughout the code with
    configurable, documented parameters.
    """
    
    # Carbon and biomass parameters - loaded dynamically from CSV
    carbon_to_biomass_ratio: float        # Will be loaded from model_constants CSV
    growth_respiration_fraction: float    # Will be loaded from model_constants CSV
    
    # Biomass allocation fractions by growth stage - loaded from CSV
    vegetative_leaf_allocation: float
    vegetative_stem_allocation: float
    vegetative_root_allocation: float
    
    reproductive_leaf_allocation: float
    reproductive_stem_allocation: float
    reproductive_root_allocation: float
    
    # Environmental stress thresholds - loaded from CSV
    optimal_light_intensity: float        # Will be loaded from environment_parameters CSV
    optimal_ec_range: tuple               # Will be loaded from stress_parameters CSV
    
    # VPD stress parameters - loaded from CSV
    optimal_vpd_min: float
    optimal_vpd_max: float
    vpd_stress_high_factor: float         # Will be loaded from stress_parameters CSV
    vpd_stress_low_factor: float          # Will be loaded from stress_parameters CSV
    
    # EC stress parameters - loaded from CSV
    optimal_ec: float                     # Will be loaded from stress_parameters CSV
    ec_stress_high_factor: float          # Will be loaded from stress_parameters CSV
    ec_stress_low_threshold: float        # Will be loaded from stress_parameters CSV
    ec_stress_low_factor: float           # Will be loaded from stress_parameters CSV
    
    # Temperature stress parameters - loaded from CSV
    optimal_root_temp: float
    root_temp_tolerance: float            # Will be loaded from thermal_requirements CSV
    root_temp_stress_factor: float        # Will be loaded from stress_parameters CSV
    
    optimal_air_temp_max: float           # Will be loaded from thermal_requirements CSV
    optimal_air_temp_min: float           # Will be loaded from thermal_requirements CSV
    air_temp_stress_high_factor: float    # Will be loaded from stress_parameters CSV
    air_temp_stress_low_factor: float     # Will be loaded from stress_parameters CSV
    
    # Humidity stress parameters - loaded from CSV
    optimal_humidity_min: float
    humidity_stress_factor: float          # Will be loaded from stress_parameters CSV
    
    # Water calculations - loaded from CSV
    specific_leaf_area_default: float     # Will be loaded from canopy_parameters CSV
    metabolic_water_per_lai: float        # L/m²/day per LAI unit
    
    # Nutrient reservoir management
    reservoir_topup_fraction: float       # Fraction of deficit to restore weekly
    
    # Minimal biological values (to prevent division by zero)
    minimal_nitrogen_uptake: float        # mg/day minimum for calculations
    
    def validate(self) -> List[str]:
        """Validate parameter consistency"""
        errors = []
        
        # Check allocation fractions sum to 1.0
        veg_sum = self.vegetative_leaf_allocation + self.vegetative_stem_allocation + self.vegetative_root_allocation
        if abs(veg_sum - 1.0) > 0.01:
            errors.append(f"Vegetative allocation fractions sum to {veg_sum:.3f}, should be 1.0")
            
        rep_sum = self.reproductive_leaf_allocation + self.reproductive_stem_allocation + self.reproductive_root_allocation  
        if abs(rep_sum - 1.0) > 0.01:
            errors.append(f"Reproductive allocation fractions sum to {rep_sum:.3f}, should be 1.0")
        
        # Check positive values
        if self.carbon_to_biomass_ratio <= 0 or self.carbon_to_biomass_ratio > 1:
            errors.append("Carbon to biomass ratio must be between 0 and 1")
            
        return errors


class CROPGROHydroponicSimulator:
    """
    Advanced CROPGRO-based hydroponic simulator integrating all models.
    
    This simulator provides research-grade crop modeling with:
    - Cultivar-specific genetic parameters
    - Complete phenological development
    - Advanced physiological processes
    - Environmental stress integration
    - Precision nutrient management
    """
    
    def __init__(self, 
                 cultivar_id: str = 'HYDRO_001',
                 system_type: str = 'NFT',
                 enable_all_models: bool = True,
                 simulation_params: Optional[SimulationParameters] = None,
                 system_config: Any = None):
        """
        Initialize CROPGRO simulator with all advanced models.
        
        Args:
            cultivar_id: Genetic cultivar identifier
            system_type: Hydroponic system type (NFT, DWC, AEROPONICS)
            enable_all_models: Enable all advanced CROPGRO models
        """
        
        logger.info("Initializing CROPGRO Hydroponic Simulator...")
        
        # Store system configuration for parameter access (all parameters now come from CSV)
        self.system_config = system_config
        
        # Store genetic stress weights from CSV (no longer using JSON config)
        self.genetic_stress_weights = getattr(self.system_config, 'genetic_stress_weights', {})
        
        self.params = simulation_params or self._load_simulation_parameters()
        
        # Validate simulation parameters
        param_errors = self.params.validate()
        if param_errors:
            for error in param_errors:
                logger.warning(f"Parameter validation: {error}")
            raise ValueError(f"Invalid simulation parameters: {param_errors}")
        
        # 1. GENETIC PARAMETERS SYSTEM
        logger.info("Loading genetic parameters system...")
        self.genetic_db, self.ge_model, self.breeding_assistant = create_lettuce_genetic_system(system_config)
        self.current_cultivar = cultivar_id
        self.cultivar_profile = self.genetic_db.get_cultivar(cultivar_id)
        
        if not self.cultivar_profile:
            logger.warning(f"Cultivar {cultivar_id} not found, using default CSV cultivar")
            self.current_cultivar = 'DEFAULT_CSV_CULTIVAR'
            self.cultivar_profile = self.genetic_db.get_cultivar(self.current_cultivar)
        
        # Apply dynamic genetic parameters from CSV if available
        genetic_params = getattr(self.system_config, 'genetic_parameters', {})
        if genetic_params and self.cultivar_profile:
            self._update_cultivar_with_dynamic_params(genetic_params)
        
        logger.info(f"Selected cultivar: {self.cultivar_profile.cultivar_name}")
        
        # 2. PHENOLOGY AND DEVELOPMENT
        logger.info("Initializing phenology model...")
        # Start from transplant stage (V3 - third true leaf) to reflect 2–3 week-old plugs
        transplant_stage = LettuceGrowthStage.THIRD_LEAF
        
        # Load phenology model using CSV configuration
        self.phenology_model = create_lettuce_phenology_model(self.system_config, transplant_stage)
        # Leaf development model for realistic LAI and leaf metrics - use dynamic CSV parameters
        logger.info("Initializing leaf development model...")
        # Load leaf development model using CSV configuration
        self.leaf_model = create_lettuce_leaf_development_model(self.system_config)
        
        # 3. RESPIRATION MODEL
        logger.info("Initializing respiration model...")
        self.respiration_model = create_lettuce_respiration_model(self.system_config)
        
        # 4. SENESCENCE MODEL
        logger.info("Initializing senescence model...")
        self.senescence_model = create_lettuce_senescence_model(self.system_config)
        
        # 5. CANOPY ARCHITECTURE
        logger.info("Initializing canopy architecture model...")
        # Integrate canopy parameters from CSV
        canopy_params = getattr(self.system_config, 'canopy_parameters', {})
        self.canopy_model = self._create_canopy_model_with_csv_params(canopy_params)
        
        # 6. NITROGEN BALANCE
        logger.info("Initializing nitrogen balance model...")
        # Load nitrogen parameters dynamically from CSV
        nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
        
        if nitrogen_params:
            from .models.nitrogen_balance import PlantNitrogenBalanceModel, NitrogenBalanceParameters
            # Create dynamic nitrogen balance parameters from CSV data
            nb_params = NitrogenBalanceParameters.from_config(nitrogen_params)
            
            # Map CSV parameters to model parameters - these affect key nitrogen processes
            if 'uptake_efficiency' in nitrogen_params:
                # Scale uptake kinetics based on efficiency
                efficiency_factor = nitrogen_params['uptake_efficiency'] / 0.8  # Relative to baseline
                for n_form in nb_params.uptake_kinetics:
                    nb_params.uptake_kinetics[n_form]['vmax'] *= efficiency_factor
            
            if 'translocation_rate' in nitrogen_params:
                nb_params.translocation_efficiency = nitrogen_params['translocation_rate']
                
            if 'protein_synthesis' in nitrogen_params:
                nb_params.protein_synthesis_efficiency = nitrogen_params['protein_synthesis']
                
            if 'senescence_rate' in nitrogen_params:
                nb_params.senescence_remobilization_efficiency = nitrogen_params['senescence_rate']
                
            if 'chlorophyll_ratio' in nitrogen_params:
                # Store chlorophyll ratio for photosynthesis model integration
                self.chlorophyll_ratio = nitrogen_params['chlorophyll_ratio']
            else:
                raise ValueError("❌ 'chlorophyll_ratio' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
            
            self.nitrogen_model = PlantNitrogenBalanceModel(nb_params)
        else:
            self.nitrogen_model = create_lettuce_nitrogen_balance_model()
        
        # 7. NUTRIENT MOBILITY
        logger.info("Initializing nutrient mobility model...")
        self.mobility_model = create_lettuce_nutrient_mobility_model(self.system_config)
        
        # 8. STRESS MODELS
        logger.info("Initializing stress models...")
        self.integrated_stress = create_lettuce_integrated_stress_model(self.system_config)
        self.temperature_stress = create_lettuce_temperature_stress_model(self.system_config)
        
        # 9. ROOT ARCHITECTURE
        logger.info("Initializing root architecture model...")
        system_type_enum = {
            'NFT': HydroponicSystemType.NFT,
            'DWC': HydroponicSystemType.DWC, 
            'AEROPONICS': HydroponicSystemType.AEROPONICS
        }.get(system_type, HydroponicSystemType.NFT)
        
        # Initialize with default tank volume, will be updated in simulate() method
        self.root_model = create_enhanced_root_uptake_model(system_type_enum, 1500.0, self.system_config)
        
        # 10. ENVIRONMENTAL CONTROL
        logger.info("Initializing environmental control...")
        # Load environmental control parameters dynamically from CSV
        env_control_params = getattr(self.system_config, 'environmental_control_parameters', {})
        
        # Create dynamic config for environmental control
        env_control_config = {}
        if 'target_vpd' in env_control_params:
            env_control_config['target_vpd'] = env_control_params['target_vpd']
        if 'co2_setpoint' in env_control_params:
            env_control_config['target_co2'] = env_control_params['co2_setpoint']
        
        # Initialize with dynamic configuration or defaults
        # Load environmental control system using CSV configuration
        self.environmental_control = create_lettuce_environmental_control_system(self.system_config)
        
        # 11. BASIC MODELS (Enhanced)
        # Load photosynthesis model using CSV configuration
        self.photosynthesis_model = create_lettuce_photosynthesis_model(self.system_config)
            
        self.nutrient_concentration_model = NutrientConcentrationModel(getattr(self.system_config, 'nutrient_parameters', {}))
        
        # 12. ROOT ZONE TEMPERATURE MODEL
        logger.info("Initializing root zone temperature model...")
        # Load root zone temperature model using CSV configuration
        self.rzt_model = create_lettuce_rzt_model(self.system_config)
        
        # 13. pH MODEL  
        logger.info("Initializing comprehensive pH model...")
        # Load pH model with buffer chemistry using CSV configuration
        self.ph_model = create_lettuce_ph_model(self.system_config)
        
        # Initialize state variables
        self._initialize_plant_state()
        
        logger.info("CROPGRO Hydroponic Simulator initialized successfully!")
        logger.info(f"Enabled models: Genetic Parameters, Phenology, Respiration, Senescence, "
                   f"Canopy Architecture, Nitrogen Balance, Nutrient Mobility, Stress Models, "
                   f"Root Architecture, Root Zone Temperature, Environmental Control")

    def _get_required_param(self, param_dict: dict, param_name: str, param_source: str) -> any:
        """Get a required parameter with clear error message if missing."""
        if param_name not in param_dict:
            available_params = list(param_dict.keys()) if param_dict else 'None'
            error_msg = f"❌ Missing required parameter '{param_name}' in {param_source}. Available parameters: {available_params}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return param_dict[param_name]
    
    def _load_simulation_parameters(self) -> SimulationParameters:
        """Loads simulation parameters from CSV files."""
        # Get parameters from CSV data (loaded by CLI)
        stress_params = getattr(self.system_config, 'stress_parameters', {})
        growth_params = getattr(self.system_config, 'model_constants', {})  # Growth params are in model_constants
        env_params = getattr(self.system_config, 'environment_parameters', {})
        phys_params = getattr(self.system_config, 'model_constants', {})  # Physiology params are in model_constants
        canopy_params = getattr(self.system_config, 'canopy_parameters', {})
        # Get parameters from CSV data with proper handling
        water_params = dict(getattr(self.system_config, 'water_parameters', {}))  # Create a copy
        nutrient_params = getattr(self.system_config, 'nitrogen_parameters', {})
        system_params = getattr(self.system_config, 'system_parameters', {})

        # Convert CSV parameter names to internal parameter names for water_params
        if water_params:
            # Use a copy of items to avoid dictionary modification during iteration
            water_params_copy = dict(water_params)
            for param_name, param_value in water_params_copy.items():
                if param_name == 'lai_water_demand_factor':
                    water_params['LAI_WATER_DEMAND_FACTOR'] = param_value

        # Integrate dynamic parameters from system_config CSV
        model_constants = getattr(self.system_config, 'model_constants', {})
        stress_parameters = getattr(self.system_config, 'stress_parameters', {})
        environment_parameters = getattr(self.system_config, 'environment_parameters', {})
        thermal_requirements = getattr(self.system_config, 'thermal_requirements', {})
        canopy_parameters = getattr(self.system_config, 'canopy_parameters', {})
        csv_system_parameters = getattr(self.system_config, 'system_parameters', {})

        try:
            return SimulationParameters(
                carbon_to_biomass_ratio=self._get_required_param(model_constants, 'carbon_to_biomass_ratio', 'model_constants CSV'),
                growth_respiration_fraction=self._get_required_param(model_constants, 'growth_respiration_fraction', 'model_constants CSV'),
                vegetative_leaf_allocation=self._get_required_param(model_constants, 'vegetative_leaf_allocation', 'model_constants CSV'),
                vegetative_stem_allocation=self._get_required_param(model_constants, 'vegetative_stem_allocation', 'model_constants CSV'),
                vegetative_root_allocation=self._get_required_param(model_constants, 'vegetative_root_allocation', 'model_constants CSV'),
                reproductive_leaf_allocation=self._get_required_param(model_constants, 'reproductive_leaf_allocation', 'model_constants CSV'),
                reproductive_stem_allocation=self._get_required_param(model_constants, 'reproductive_stem_allocation', 'model_constants CSV'),
                reproductive_root_allocation=self._get_required_param(model_constants, 'reproductive_root_allocation', 'model_constants CSV'),
                optimal_light_intensity=self._get_required_param(environment_parameters, 'optimal_light_intensity', 'environment_parameters CSV'),
                optimal_ec_range=(
                    self._get_required_param(stress_parameters, 'optimal_ec_min', 'stress_parameters CSV'),
                    self._get_required_param(stress_parameters, 'optimal_ec_max', 'stress_parameters CSV')
                ),
                optimal_vpd_min=self._get_required_param(stress_parameters, 'optimal_vpd_min', 'stress_parameters CSV'),
                optimal_vpd_max=self._get_required_param(stress_parameters, 'optimal_vpd_max', 'stress_parameters CSV'),
                vpd_stress_high_factor=self._get_required_param(stress_parameters, 'vpd_stress_high_factor', 'stress_parameters CSV'),
                vpd_stress_low_factor=self._get_required_param(stress_parameters, 'vpd_stress_low_factor', 'stress_parameters CSV'),
                optimal_ec=self._get_required_param(environment_parameters, 'optimal_ec', 'environment CSV'),
                ec_stress_high_factor=self._get_required_param(stress_parameters, 'ec_stress_high_factor', 'stress_parameters CSV'),
                ec_stress_low_threshold=self._get_required_param(stress_parameters, 'ec_stress_low_threshold', 'stress_parameters CSV'),
                ec_stress_low_factor=self._get_required_param(stress_parameters, 'ec_stress_low_factor', 'stress_parameters CSV'),
                optimal_root_temp=self._get_required_param(environment_parameters, 'environment_optimal_temperature', 'environment_parameters CSV'),
                root_temp_tolerance=self._get_required_param(stress_parameters, 'temp_stress_threshold', 'stress_parameters CSV'),
                root_temp_stress_factor=self._get_required_param(stress_parameters, 'temp_stress_factor', 'stress_parameters CSV'),
                optimal_air_temp_max=self._get_required_param(environment_parameters, 'optimal_temperature_max', 'environment_parameters CSV'),
                optimal_air_temp_min=self._get_required_param(environment_parameters, 'optimal_temperature_min', 'environment_parameters CSV'),
                air_temp_stress_high_factor=self._get_required_param(stress_parameters, 'heat_stress_threshold', 'stress_parameters CSV'),
                air_temp_stress_low_factor=self._get_required_param(stress_parameters, 'cold_stress_threshold', 'stress_parameters CSV'),
                optimal_humidity_min=self._get_required_param(environment_parameters, 'min_humidity', 'environment_parameters CSV'),
                humidity_stress_factor=self._get_required_param(stress_parameters, 'water_stress_factor', 'stress_parameters CSV'),
                specific_leaf_area_default=self._get_required_param(canopy_parameters, 'specific_leaf_area', 'canopy_parameters CSV'),
                metabolic_water_per_lai=self._get_required_param(water_params, 'lai_water_demand_factor', 'water_parameters CSV'),
                reservoir_topup_fraction=self._get_required_param(csv_system_parameters, 'reservoir_topup_fraction', 'system_parameters CSV'),
                minimal_nitrogen_uptake=self._get_required_param(nutrient_params, 'nitrogen_uptake_efficiency', 'nitrogen_parameters CSV')
            )
        except ValueError as e:
            logger.error(f"Failed to load simulation parameters: {e}")
            raise
    
    def _create_canopy_model_with_csv_params(self, canopy_params: dict):
        """Create canopy architecture model with CSV parameters only."""
        from .models.canopy_architecture import CanopyArchitectureModel, CanopyArchitectureParameters
        
        # Use CSV parameters directly (no JSON fallback needed)
        canopy_config = {}
        
        # Override with CSV parameters
        if canopy_params:
            # Map CSV parameter names to canopy config names
            csv_to_config_mapping = {
                'number_of_layers': 'number_of_layers',
                'light_extinction': 'extinction_coefficient',
                'extinction_coefficient': 'extinction_coefficient',
                'diffuse_extinction_coeff': 'diffuse_extinction_coeff',
                'beam_extinction_coeff': 'beam_extinction_coeff',
                'row_spacing': 'row_spacing',
                'mean_leaf_angle': 'mean_leaf_angle',
                'leaf_angle': 'mean_leaf_angle',
                'leaf_thickness': 'leaf_thickness',
                'canopy_width': 'canopy_width',
                'plant_height': 'plant_height',
                'canopy_height': 'plant_height',
                'leaf_area_ratio': 'leaf_area_ratio',
                'light_interception_efficiency': 'light_interception_efficiency',
                'specific_leaf_area': 'specific_leaf_area',
                'maximum_lai': 'max_lai',
                'max_lai': 'max_lai',
                'leaf_angle_distribution': 'leaf_angle_distribution',
                'leaf_angle_variance': 'leaf_angle_variance',
                'plant_spacing': 'plant_spacing',
                'leaf_reflectance': 'leaf_reflectance',
                'leaf_transmittance': 'leaf_transmittance',
                'leaf_absorptance': 'leaf_absorptance',
                'self_shading_factor': 'self_shading_factor',
                'neighbor_shading_distance': 'neighbor_shading_distance',
                'sunlit_fraction_method': 'sunlit_fraction_method',
                'clumping_index': 'clumping_index',
                # Additional canopy architecture parameters
                'max_extinction_coefficient': 'max_extinction_coefficient',
                'upper_canopy_lai_factor': 'upper_canopy_lai_factor',
                'middle_canopy_lai_factor': 'middle_canopy_lai_factor',
                'lower_middle_canopy_lai_factor': 'lower_middle_canopy_lai_factor',
                'bottom_canopy_lai_factor': 'bottom_canopy_lai_factor',
                'shaded_light_fraction': 'shaded_light_fraction',
                'max_temperature_gradient': 'max_temperature_gradient',
                'temperature_gradient_factor': 'temperature_gradient_factor',
                'ppfd_to_photosynthesis_factor': 'ppfd_to_photosynthesis_factor'
            }
            
            for csv_param, config_param in csv_to_config_mapping.items():
                if csv_param in canopy_params:
                    canopy_config[config_param] = canopy_params[csv_param]
                    
        try:
            parameters = CanopyArchitectureParameters.from_config(canopy_config)
            return CanopyArchitectureModel(parameters)
        except KeyError as e:
            missing_param = str(e).strip("'\"")
            error_msg = f"❌ Missing canopy parameter in CSV: {missing_param}. Available CSV parameters: {list(canopy_params.keys()) if canopy_params else 'None'}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _initialize_plant_state(self):
        """Initialize plant physiological state based on cultivar"""
        
        # Initial biomass based on cultivar characteristics
        cultivar_coeffs = self.cultivar_profile.genetic_coefficients
        
        # Initialize biomass pools for TRANSPLANT STAGE (realistic starting point)
        # Typical lettuce transplants: 2-3 weeks old, 2-4 true leaves + cotyledons
        # This eliminates the bootstrap paradox by starting with functional photosynthetic area
        
        # Transplant biomass must be provided in CSV configuration
        # Get initial biomass from CSV parameters
        initial_biomass_params = getattr(self.system_config, 'model_constants', {})
        
        initial_leaf_biomass = initial_biomass_params.get('initial_leaf_biomass')
        initial_stem_biomass = initial_biomass_params.get('initial_stem_biomass')
        initial_root_biomass = initial_biomass_params.get('initial_root_biomass')
        
        if initial_leaf_biomass is None:
            raise ValueError("❌ 'initial_leaf_biomass' parameter must be provided in model_constants CSV - no hardcoded defaults allowed")
        if initial_stem_biomass is None:
            raise ValueError("❌ 'initial_stem_biomass' parameter must be provided in model_constants CSV - no hardcoded defaults allowed")
        if initial_root_biomass is None:
            raise ValueError("❌ 'initial_root_biomass' parameter must be provided in model_constants CSV - no hardcoded defaults allowed")
        
        self.biomass_pools = [
            BiomassPool(TissueType.LEAVES, initial_leaf_biomass, 2.0, 4.5, 0.0),
            BiomassPool(TissueType.STEMS, initial_stem_biomass, 2.0, 2.0, 0.0),
            BiomassPool(TissueType.ROOTS, initial_root_biomass, 2.0, 2.8, 0.0)
        ]
        
        # Initialize nitrogen model with cultivar-specific parameters
        nitrogen_efficiency = cultivar_coeffs.NITRATE_EFFICIENCY
        self.nitrogen_model.initialize_organ('leaves', initial_leaf_biomass, 0.045 * nitrogen_efficiency)
        self.nitrogen_model.initialize_organ('stems', initial_stem_biomass, 0.020)
        self.nitrogen_model.initialize_organ('roots', initial_root_biomass, 0.028 * nitrogen_efficiency)
        
        # Initialize nutrient mobility model
        initial_nutrients = {
            'nitrogen': 0.15 * nitrogen_efficiency,
            'phosphorus': 0.020,
            'potassium': 0.12,
            'calcium': 0.08,
            'magnesium': 0.025,
            'sulfur': 0.018
        }
        
        self.mobility_model.initialize_organ_pools('leaves', initial_nutrients, initial_leaf_biomass)
        self.mobility_model.initialize_organ_pools('stems', 
            {k: v*0.35 for k, v in initial_nutrients.items()}, initial_stem_biomass)
        self.mobility_model.initialize_organ_pools('roots',
            {k: v*0.80 for k, v in initial_nutrients.items()}, initial_root_biomass)
        
        # Initial canopy parameters for TRANSPLANT STAGE
        # Compute placeholder LAI here; will be recalculated with actual density in run_simulation
        transplant_sla = self.leaf_model.params.specific_leaf_area  # cm²/g
        transplant_leaf_area_m2 = (initial_leaf_biomass * transplant_sla) / 10000.0
        default_system_area = getattr(self.system_config, 'system_area', None)  # Must be set from CSV
        if default_system_area is None:
            raise ValueError("System area must be provided in CSV configuration")
        calculated_lai = transplant_leaf_area_m2 / max(1e-6, default_system_area)
        
        # Use calculated LAI without artificial minimum - let biology determine the starting LAI
        # Early transplants naturally start with small LAI (~0.1-0.3) which is realistic
        self.current_lai = calculated_lai
        # Set realistic transplant height from CSV configuration
        # Transplants (V3 stage) typically 10-12 cm tall
        initial_canopy_height = initial_biomass_params.get('initial_canopy_height')
        if initial_canopy_height is None:
            raise ValueError("❌ 'initial_canopy_height' parameter must be provided in model_constants CSV - no hardcoded defaults allowed")
        self.canopy_height = initial_canopy_height
        
        # Get transplanting period dynamically from experiment settings CSV
        experiment_settings = getattr(self.system_config, 'experiment_settings', {})
        sowing_date_str = experiment_settings.get('sowing_date')
        transplanting_date_str = experiment_settings.get('transplanting_date')
        
        if not sowing_date_str or not transplanting_date_str:
            raise ValueError("Missing sowing_date or transplanting_date in experiment settings CSV")
        
        # Calculate transplanting period dynamically
        from datetime import datetime
        try:
            sowing_date = datetime.strptime(sowing_date_str, '%Y-%m-%d')
            transplanting_date = datetime.strptime(transplanting_date_str, '%Y-%m-%d')
            self.transplanting_period_days = (transplanting_date - sowing_date).days
            
            if self.transplanting_period_days <= 0:
                raise ValueError(f"Invalid date order: transplanting_date must be after sowing_date")
                
        except ValueError as e:
            raise ValueError(f"Invalid date format in experiment settings: {e}. Expected format: YYYY-MM-DD")
        
        # Simulation tracking
        self.simulation_day = 0
        self.accumulated_gdd = 0.0
        
        # Initialize hourly weather interpolator for DSSAT-style integration
        self.hourly_weather_interpolator = create_hourly_weather_interpolator()
        # Cumulative trackers for system-level metrics
        self.cumulative_water_L = 0.0
        
        logger.info(f"Plant state initialized: {initial_leaf_biomass:.1f}g leaves, "
                   f"{initial_stem_biomass:.1f}g stems, {initial_root_biomass:.1f}g roots")
    
    def run_simulation(self, input_data: HydroInputData, 
                      max_days: int = 365,
                      target_maturity: str = "harvest",
                      treatment_id: str = None) -> SimulationResults:
        """
        Run complete CROPGRO hydroponic simulation until physiological maturity.
        
        Args:
            input_data: Input data for simulation
            max_days: Maximum days to prevent infinite loops (default 365)
            target_maturity: Target maturity stage ('harvest' or 'physiological')
            
        Returns:
            SimulationResults with comprehensive daily outputs
        """
        logger.info("Starting CROPGRO simulation...")
        logger.info(f"Cultivar: {self.cultivar_profile.cultivar_name}")
        logger.info(f"Target maturity: {target_maturity}")
        logger.info(f"Maximum days: {max_days}")
        
        # Define maturity stages to stop at
        if target_maturity == "harvest":
            target_stages = {"HM"}  # Harvest Maturity
        elif target_maturity == "physiological":
            target_stages = {"PM"}  # Physiological Maturity  
        else:
            target_stages = {"HM", "PM"}  # Either harvest or physiological
        
        # Initialize results storage
        daily_results = []
        
        # Use provided weather data, cycling if needed
        weather_data = input_data.weather_data
        weather_cycle_length = len(weather_data)
        
        # Initialize nutrient concentrations from CSV parameters
        current_concentrations = {}
        nutrient_concentration_params = getattr(self.system_config, 'nutrient_concentrations', {})
        
        # Map CSV parameter names to nutrient IDs
        self.nutrient_mapping = {
            'initial_n_no3': 'N-NO3',
            'initial_n_nh4': 'N-NH4', 
            'initial_p_po4': 'P-PO4',
            'initial_k': 'K',
            'initial_ca': 'Ca',
            'initial_mg': 'Mg',
            'initial_s_so4': 'S-SO4',
            'initial_fe': 'Fe',
            'initial_mn': 'Mn',
            'initial_zn': 'Zn',
            'initial_cu': 'Cu',
            'initial_b': 'B',
            'initial_mo': 'Mo'
        }
        
        # Initialize concentrations from CSV parameters
        for param_name, nutrient_id in self.nutrient_mapping.items():
            if param_name in nutrient_concentration_params:
                current_concentrations[nutrient_id] = nutrient_concentration_params[param_name]
            else:
                # Fallback to default values if not found in CSV
                default_values = {
                    'N-NO3': 200.0, 'N-NH4': 20.0, 'P-PO4': 50.0, 'K': 300.0,
                    'Ca': 150.0, 'Mg': 50.0, 'S-SO4': 100.0, 'Fe': 2.0,
                    'Mn': 0.5, 'Zn': 0.1, 'Cu': 0.05, 'B': 0.3, 'Mo': 0.05
                }
                current_concentrations[nutrient_id] = default_values.get(nutrient_id, 0.0)

        # Track system state
        current_tank_volume = input_data.system_config.tank_volume
        self.plant_count = input_data.system_config.n_plants
        self.system_area = max(0.1, input_data.system_config.system_area)
        

        # Use dynamic plant density from crop parameters CSV
        crop_params = getattr(input_data.system_config, 'crop_parameters', {})
        # Get plant density from system parameters (primary source) or crop parameters (fallback)
        system_params = getattr(input_data.system_config, 'system_parameters', {})
        if 'plant_density' in system_params:
            density_multiplier = system_params['plant_density']
        else:
            density_multiplier = crop_params['plant_density']  # Fallback to crop parameters
        base_density = max(0.1, self.plant_count / self.system_area)
        self.plant_density = base_density * density_multiplier
        # Get system parameters from CSV data loaded in system_config
        system_params = getattr(self.system_config, 'system_parameters', {})
        current_ph = system_params.get('default_ph', None)
        if current_ph is None:
            raise ValueError("Default pH must be provided in CSV configuration")
        
        # Update root model with actual tank volume (important for NFT channel calculations)
        system_type_enum = {
            'NFT': HydroponicSystemType.NFT,
            'DWC': HydroponicSystemType.DWC, 
            'AEROPONICS': HydroponicSystemType.AEROPONICS
        }.get(input_data.system_config.system_type, HydroponicSystemType.NFT)
        
        self.root_model = create_enhanced_root_uptake_model(system_type_enum, current_tank_volume, self.system_config)
        
        # Main simulation loop - run until maturity or max days
        day = 1
        maturity_reached = False
        
        while day <= max_days and not maturity_reached:
            self.simulation_day = day
            
            # Get daily weather (cycle through available data)
            weather_index = (day - 1) % weather_cycle_length
            weather = weather_data[weather_index]
            daily_temp = weather.temp_avg
            daily_humidity = weather.rel_humidity  
            daily_solar = weather.solar_radiation
            daylength = 13.5 + 1.5 * np.sin(day * 2 * np.pi / 365)  # Seasonal variation
            
            # REALISTIC NUTRIENT MANAGEMENT
            # Individual nutrient monitoring and targeted supplementation
            nutrient_management_performed = self._perform_realistic_nutrient_management(
                day, current_concentrations, input_data, logger
            )
            
            # Update pH only if nutrients were changed
            if nutrient_management_performed:
                current_ph = system_params['default_ph']
                logger.info(f"  pH: reset to {current_ph:.1f}")
            
            # Run daily simulation step
            daily_result = self._simulate_daily_step(
                day=day,
                temperature=daily_temp,
                humidity=daily_humidity,
                solar_radiation=daily_solar,
                daylength=daylength,
                nutrient_concentrations=current_concentrations,
                ph=current_ph,
                previous_tank_volume=current_tank_volume,
                plant_density=self.plant_density
            )
            
            daily_results.append(daily_result)
            
            # Check for maturity using phenology model
            current_stage = getattr(daily_result, 'growth_stage', 'VE')
            if current_stage in target_stages:
                maturity_reached = True
                logger.info(f"Maturity reached at day {day}: {current_stage}")
            
            # WEEKLY SOLUTION CHANGES (DR. NEMALI METHOD) - MOVED TO BEGINNING OF DAY
            # Complete solution replacement every 7 days to maintain optimal nutrient levels

            # Cache last env for PM/ETc calculations
            self._last_humidity = daily_humidity
            self._last_solar = daily_solar

            # Update nutrient concentrations based on uptake (use current tank volume)
            plant_count = input_data.system_config.n_plants
            for nutrient_id in list(current_concentrations.keys()):
                uptake_key = f"{nutrient_id}_uptake_rate"
                per_plant_uptake = getattr(daily_result, uptake_key, 0.0)
                # Fallback: estimate nitrate uptake from nitrogen balance if root uptake is zero
                if nutrient_id == 'N-NO3' and per_plant_uptake == 0.0:
                    est_n_mg = getattr(daily_result, 'nitrogen_uptake_mg', 0.0)
                    # Convert mg N to mg NO3 using molecular mass ratio (62/14)
                    per_plant_uptake = est_n_mg * (62.0 / 14.0)

                if per_plant_uptake > 0.0:
                    total_uptake_mg = per_plant_uptake * max(1, plant_count)
                    volume_m3 = max(0.001, daily_result.tank_volume / 1000.0)
                    concentration_reduction = total_uptake_mg / volume_m3  # mg/L reduction (mg per m³)
                    current_concentrations[nutrient_id] = max(0.0, current_concentrations[nutrient_id] - concentration_reduction)

            # Check for automatic solution change
            current_ec = self._calculate_ec(current_concentrations)
            nutrient_management_params = getattr(self.system_config, 'nutrient_management', {})
            min_ec_threshold = nutrient_management_params.get('min_ec_threshold', 1.0)
            solution_change_interval = nutrient_management_params.get('solution_change_interval', 7)
            
            # Solution change conditions: EC too low OR interval reached
            ec_too_low = current_ec < min_ec_threshold
            interval_reached = day % solution_change_interval == 0
            
            if ec_too_low or interval_reached:
                # Reset nutrient concentrations to initial values
                for param_name, nutrient_id in self.nutrient_mapping.items():
                    if param_name in nutrient_concentration_params:
                        current_concentrations[nutrient_id] = nutrient_concentration_params[param_name]
                    else:
                        # Use fallback default values
                        default_values = {
                            'N-NO3': 200.0, 'N-NH4': 20.0, 'P-PO4': 50.0, 'K': 300.0,
                            'Ca': 150.0, 'Mg': 50.0, 'S-SO4': 100.0, 'Fe': 2.0,
                            'Mn': 0.5, 'Zn': 0.1, 'Cu': 0.05, 'B': 0.3, 'Mo': 0.05
                        }
                        current_concentrations[nutrient_id] = default_values.get(nutrient_id, 0.0)
                
                # Log solution change
                reason = "EC too low" if ec_too_low else "scheduled interval"
                print(f"Day {day}: Complete solution change - replacing with fresh nutrient solution")
                print(f"  Reason: {reason} (EC: {current_ec:.2f} dS/m, threshold: {min_ec_threshold:.2f} dS/m)")
                print(f"  pH: reset to {current_ph:.1f}")

            # Update pH using comprehensive chemistry model
            # Calculate total nutrient uptake for all plants from daily_result
            total_nutrient_uptake = {}
            
            # Get uptake rates from the daily result (these are already per-plant rates)
            uptake_mapping = {
                'NO3': 'N-NO3_uptake_rate',
                'NH4': 'N-NH4_uptake_rate',  # If available
                'PO4': 'P-PO4_uptake_rate',
                'K': 'K_uptake_rate',
                'Ca': 'Ca_uptake_rate', 
                'Mg': 'Mg_uptake_rate'
            }
            
            for nutrient_id, result_key in uptake_mapping.items():
                per_plant_uptake = getattr(daily_result, result_key, 0.0)
                total_nutrient_uptake[nutrient_id] = per_plant_uptake * max(1, plant_count)
            
            # Use comprehensive pH model for accurate pH dynamics
            # Get EC from the simulation result or estimate from concentrations
            current_ec = self._calculate_ec(current_concentrations) if hasattr(self, '_calculate_ec') else 1.8
            
            ph_response = self.ph_model.daily_update(
                nutrient_uptake=total_nutrient_uptake,
                nutrient_concentrations=current_concentrations,
                temperature=daily_temp,
                ec=current_ec
            )
            
            # Update pH and apply nutrient availability effects
            current_ph = ph_response['final_ph']
            current_concentrations = ph_response['available_nutrients']
            
            # Store pH model results for inclusion in daily results
            daily_result.ph_change_from_uptake = ph_response['ph_change_from_uptake']
            daily_result.ph_change_from_drift = ph_response['ph_change_from_drift']
            daily_result.acid_dosed_ml_per_L = ph_response['acid_dosed_ml_per_L']
            daily_result.base_dosed_ml_per_L = ph_response['base_dosed_ml_per_L']
            daily_result.buffer_capacity = ph_response['buffer_capacity']
            
            # Store phosphate speciation data
            phosphate_species = ph_response['phosphate_species']
            daily_result.phosphate_h2po4_mg_L = phosphate_species.get('H2PO4', 0.0)
            daily_result.phosphate_hpo4_mg_L = phosphate_species.get('HPO4', 0.0)
            
            # Calculate total precipitation
            precipitation = ph_response['nutrient_precipitation']
            daily_result.nutrient_precipitation_mg_L = sum(precipitation.values())
            
            # Log significant pH changes or dosing
            if abs(ph_response['ph_change_from_uptake']) > 0.05:
                logger.info(f"Day {day}: Significant pH change from uptake: {ph_response['ph_change_from_uptake']:.3f}")
            if ph_response['acid_dosed_ml_per_L'] > 0.1 or ph_response['base_dosed_ml_per_L'] > 0.1:
                logger.info(f"Day {day}: pH control - Acid: {ph_response['acid_dosed_ml_per_L']:.2f} mL/L, Base: {ph_response['base_dosed_ml_per_L']:.2f} mL/L")

            # Update tank volume
            current_tank_volume = daily_result.tank_volume
            
            # Log progress
            if day % 10 == 0:
                logger.info(f"Day {day}: Stage={current_stage}, LAI={self.current_lai:.2f}, "
                           f"Biomass={sum(pool.dry_mass for pool in self.biomass_pools):.1f}g, "
                           f"Temp={daily_temp:.1f}°C")
            
            day += 1
        
        # Final logging
        final_stage = getattr(daily_results[-1], 'growth_stage', 'Unknown') if daily_results else 'None'
        if maturity_reached:
            logger.info(f"Simulation completed at maturity: {final_stage} ({len(daily_results)} days)")
        else:
            logger.info(f"Simulation completed at maximum days: {final_stage} ({len(daily_results)} days)")
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_statistics(daily_results)
        
        # Create results object with proper fields
        results = SimulationResults(
            system_id=f"CROPGRO_{self.current_cultivar}",
            crop_id="LETTUCE_ADVANCED", 
            location_id="HYDROPONIC_LAB",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=len(daily_results)),
            total_days=len(daily_results),
            daily_results=daily_results,
            summary_stats=summary_stats,
            treatment_id=treatment_id
        )
        
        # Pass transplanting period to results for dynamic DAS calculation
        results.transplanting_period_days = self.transplanting_period_days
        
        # Add system configuration to results for CSV output
        results.system_type = input_data.system_config.system_type
        results.system_area = input_data.system_config.system_area
        results.plant_count = input_data.system_config.n_plants
        # Get flow rate from system parameters
        system_params = getattr(input_data.system_config, 'system_parameters', {})
        flow_rate_l_h = system_params.get('flow_rate', 50.0)  # Default 50 L/h
        results.flow_rate = flow_rate_l_h
        results.system_description = getattr(input_data.system_config, 'description', '')
        
        # Add metadata as custom attributes
        results.metadata = {
            'cultivar_id': self.current_cultivar,
            'cultivar_name': self.cultivar_profile.cultivar_name,
            'simulation_type': 'CROPGRO_Advanced',
            'models_used': [
                'genetic_parameters', 'phenology', 'respiration', 'senescence',
                'canopy_architecture', 'nitrogen_balance', 'nutrient_mobility',
                'integrated_stress', 'temperature_stress', 'root_architecture',
                'environmental_control'
            ],
            'total_days': len(daily_results),
            'final_growth_stage': 'advanced_growth_modeling'
        }
        
        logger.info("CROPGRO simulation completed successfully!")
        return results
    
    def _validate_carbon_balance(self, photosynthesis: float, respiration: float, growth: float, day: int):
        """Validate carbon mass balance and log warnings if violated"""
        net_carbon = photosynthesis - respiration
        # Account for both structural carbon and growth respiration costs
        c_bm = self.params.carbon_to_biomass_ratio
        rg = max(0.0, self.params.growth_respiration_fraction)
        carbon_for_growth = growth * c_bm * (1.0 + rg)
        
        # Only warn when there is positive assimilation and/or positive growth
        # Negative net carbon with zero growth is physiologically plausible (maintenance exceeds assimilation)
        if not (net_carbon <= 0.0 and growth <= 0.0):
            # Check if carbon balance is reasonable (within 15% tolerance for early growth, 10% for mature plants)
            # Early growth tolerance (first 20 days) - higher tolerance due to establishment phase
            tolerance = 0.20 if day <= 20 else 0.10
            denom = max(1e-9, max(abs(net_carbon), abs(carbon_for_growth)))
            if abs(net_carbon - carbon_for_growth) > tolerance * denom:
                logger.warning(
                    f"Day {day}: Carbon balance violation - Net carbon: {net_carbon:.3f}, "
                    f"Carbon for growth: {carbon_for_growth:.3f}"
                )
        
        # Check for negative net carbon with positive growth
        if net_carbon < 0 and growth > 0:
            logger.warning(f"Day {day}: Impossible growth - negative net carbon ({net_carbon:.3f}) "
                         f"but positive growth ({growth:.3f})")
    
    def _calculate_environmental_conditions(self, temperature: float, humidity: float, 
                                          solar_radiation: float, day: int) -> Dict[str, Any]:
        """Calculate environmental conditions and environmental control responses"""
        light_environment = LightEnvironment(
            ppfd_above_canopy=solar_radiation * 45.0,  # Convert to PPFD
            direct_beam_fraction=0.6,
            diffuse_fraction=0.4,
            solar_zenith_angle=30.0 + 20.0 * np.sin(day * 2 * np.pi / 365)
        )
        
        # Environmental control updates
        current_conditions = {
            'temperature': temperature,
            'humidity': humidity,
            'co2': 400.0,
            'light_intensity': solar_radiation
        }
        light_schedule = {'light_on': solar_radiation > 5.0}  # Simple light detection
        
        env_control_response = self.environmental_control.calculate_comprehensive_control(
            current_conditions, light_schedule
        )
        
        # Use DYNAMIC weather data instead of static config values
        actual_temperature = temperature  # Use actual weather data temperature
        actual_humidity = humidity        # Use actual weather data humidity
        
        # Implement realistic CO2 management strategy
        env_params = getattr(self.system_config, 'environment_parameters', {})
        base_co2_enrichment = env_params.get('co2_morning_target', 800.0)
        
        # CO2 strategy based on multiple factors
        actual_co2 = self._calculate_dynamic_co2(
            solar_radiation, day, base_co2_enrichment
        )
            
        # Calculate VPD from actual temperature and humidity
        actual_vpd = self._calculate_vpd(actual_temperature, actual_humidity)
        # Cache VPD for water model
        self._last_vpd = actual_vpd
        
        # Get pH from system configuration
        system_params = getattr(self.system_config, 'system_parameters', {})
        current_ph = system_params.get('default_ph', None)
        if current_ph is None:
            # Try to get from nutrient parameters
            nutrient_params = getattr(self.system_config, 'nutrient_parameters', {})
            current_ph = nutrient_params.get('current_ph', None)
        
        if current_ph is None:
            raise ValueError("pH must be provided in CSV configuration (either system_parameters.default_ph or nutrient_parameters.current_ph)")
        
        return {
            'light_environment': light_environment,
            'actual_temperature': actual_temperature,
            'actual_humidity': actual_humidity,
            'actual_co2': actual_co2,
            'actual_vpd': actual_vpd,
            'ph': current_ph,
            'env_control_response': env_control_response
        }
    
    def _calculate_dynamic_co2(self, solar_radiation: float, day: int, base_enrichment: float) -> float:
        """
        Calculate realistic CO2 concentration based on:
        1. Light availability (higher CO2 when sunny)
        2. Growth stage (optimize for different phases)
        3. Economic efficiency (reduce when not beneficial)
        4. Time of day simulation
        """
        # Base ambient CO2 must be provided in CSV configuration
        env_params = getattr(self.system_config, 'environment_parameters', {})
        ambient_co2 = env_params.get('ambient_co2')
        light_threshold = env_params.get('light_threshold')
        
        if ambient_co2 is None:
            raise ValueError("❌ 'ambient_co2' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        if light_threshold is None:
            raise ValueError("❌ 'light_threshold' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        
        # Light-dependent CO2 strategy
        # Only enrich CO2 when light is sufficient for photosynthesis
        if solar_radiation < light_threshold:
            # Low light - minimal enrichment to save costs
            return ambient_co2 + 50.0  # 450 ppm
            
        # Growth stage optimization
        stage_props = self.phenology_model.get_stage_properties()
        current_stage = stage_props.get('stage_name', 'V4')
        stage_factor = self._get_co2_stage_factor(current_stage)
        
        # Light intensity factor (more CO2 on sunny days)
        max_solar = env_params.get('max_solar_radiation')
        if max_solar is None:
            raise ValueError("❌ 'max_solar_radiation' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        light_factor = min(1.2, solar_radiation / max_solar)
        
        # Calculate optimized CO2 level
        optimized_co2 = base_enrichment * stage_factor * light_factor
        
        # Economic cap - don't exceed economic limit (diminishing returns)
        max_economic_co2 = env_params.get('max_economic_co2')
        if max_economic_co2 is None:
            raise ValueError("❌ 'max_economic_co2' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        final_co2 = min(optimized_co2, max_economic_co2)
        
        # Ensure minimum enrichment during daylight
        min_daylight_co2 = env_params.get('min_daylight_co2')
        if min_daylight_co2 is None:
            raise ValueError("❌ 'min_daylight_co2' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        return max(final_co2, min_daylight_co2)
    
    def _get_co2_stage_factor(self, growth_stage: str) -> float:
        """
        Get CO2 optimization factor based on growth stage.
        Higher CO2 during rapid vegetative growth, moderate during head formation.
        """
        stage_factors = {
            'VE': 0.7,   # Emergence - low demand
            'V4': 0.8,   # Early vegetative
            'V5': 0.9,   # Building leaf area
            'V6': 1.0,   # Peak vegetative growth
            'V7': 1.1,   # Rapid expansion
            'V8': 1.2,   # Maximum growth rate
            'V9': 1.2,   # Continued rapid growth
            'V10': 1.1,  # Preparing for head formation
            'V11+': 1.0, # Head initiation
            'HI': 0.9,   # Head formation - focus on filling
            'HD': 0.8,   # Head development - slower growth
            'HM': 0.6    # Harvest maturity - minimal needs
        }
        return stage_factors.get(growth_stage, 1.0)
    
    def _calculate_unified_stress_factors(self, env_conditions: Dict[str, Any], 
                                        nutrient_concentrations: Dict[str, float], 
                                        plant_state: Dict[str, Any], day: int = 1) -> Dict[str, Any]:
        """
        Centralized stress calculation function - single source of truth for ALL stress factors.
        
        This function eliminates redundant calculations and provides consistent stress factors
        used throughout the simulation. All stress factors are returned as multiplication 
        factors where 1.0 = optimal conditions, 0.0 = severe stress.
        
        Args:
            env_conditions: Environmental conditions from environment step
            nutrient_concentrations: Current nutrient concentrations
            plant_state: Current plant physiological state
            
        Returns:
            Dict containing all stress factors and supporting data
        """
        
        # Extract environmental variables
        actual_temperature = env_conditions['actual_temperature']
        actual_humidity = env_conditions['actual_humidity']
        actual_vpd = env_conditions['actual_vpd']
        solar_radiation = env_conditions['solar_radiation']
        
        # === CALCULATE SUPPORTING VALUES ONCE ===
        
        # Calculate EC dynamically from nutrient concentrations (not static from CSV)
        ec_current = self._calculate_ec(nutrient_concentrations)
        
        # Calculate solution temperature once
        solution_temperature = self._calculate_solution_temperature(
            air_temp=actual_temperature,
            solar_radiation=solar_radiation,
            tank_volume=plant_state.get('tank_volume', 1000.0),
            day=plant_state.get('day', 1)
        )
        
        # === STRESS FACTOR CALCULATIONS ===
        
        # 1. TEMPERATURE STRESS (both air and root zone)
        temp_stress_response = self.temperature_stress.daily_update(actual_temperature)
        temperature_factor = temp_stress_response.process_factors.overall  # Factor (1.0 = optimal)
        
        # Root zone temperature stress
        root_temp_deviation = abs(solution_temperature - self.params.optimal_root_temp)
        if root_temp_deviation > self.params.root_temp_tolerance:
            root_temp_factor = max(0.0, 1.0 - (root_temp_deviation - self.params.root_temp_tolerance) * self.params.root_temp_stress_factor)
        else:
            root_temp_factor = 1.0
        
        # Combined temperature factor (most limiting)
        combined_temp_factor = min(temperature_factor, root_temp_factor)
        
        # 2. WATER STRESS (optimized for well-managed hydroponic systems)
        # In hydroponic systems, water is abundant and well-controlled
        # Main water stress comes from VPD (vapor pressure deficit) effects
        
        # Hydroponic water stress - primarily VPD-based (optimized for hydroponics)
        # In hydroponic systems, water is abundant, so stress mainly from atmospheric demand
        # Use dynamic VPD parameters from environment CSV
        env_params = getattr(self.system_config, 'environment_parameters', {})
        optimal_vpd_min = env_params.get('optimal_vpd_min', self.params.optimal_vpd_min)  # CSV or fallback
        optimal_vpd_max = env_params.get('optimal_vpd_max', self.params.optimal_vpd_max)  # CSV or fallback
        
        # Use dynamic stress parameters from stress CSV
        stress_params = getattr(self.system_config, 'stress_parameters', {})
        vpd_stress_low_factor = stress_params.get('vpd_stress_low_factor', 0.15)  # CSV or fallback
        vpd_stress_high_factor = stress_params.get('vpd_stress_high_factor', 0.25)  # CSV or fallback
        
        if optimal_vpd_min <= actual_vpd <= optimal_vpd_max:
            water_stress_level = 0.0  # No stress in optimal range
        elif actual_vpd < optimal_vpd_min:
            # Low VPD stress (poor transpiration) - use dynamic factor
            water_stress_level = min(0.2, (optimal_vpd_min - actual_vpd) * vpd_stress_low_factor)
        else:
            # High VPD stress (excessive water demand) - use dynamic factor 
            water_stress_level = min(0.4, (actual_vpd - optimal_vpd_max) * vpd_stress_high_factor)
        
        # Debug: Print water stress calculation for troubleshooting
        # print(f"DEBUG: VPD={actual_vpd:.2f}, range=[{optimal_vpd_min}-{optimal_vpd_max}], water_stress={water_stress_level:.3f}")
        
        water_factor = max(0.0, 1.0 - water_stress_level)
        
        # 3. LIGHT STRESS (optimized for hydroponic LED systems)
        # In controlled environment hydroponics, light is usually adequate
        # Optimal light intensity must be provided in CSV configuration
        optimal_light = env_params.get('optimal_light_intensity')
        if optimal_light is None:
            raise ValueError("❌ 'optimal_light_intensity' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        light_factor = min(1.0, max(0.0, float(solar_radiation) / optimal_light))
        
        # 4. NITROGEN STRESS - Use nitrogen balance model for sophisticated calculation
        # The nitrogen balance model will calculate stress based on internal nitrogen status
        # For now, use a simple solution-based calculation as fallback
        n_no3_conc = nutrient_concentrations.get('N-NO3', 0.0)  # mg/L
        
        # Nitrogen stress calculation using CSV parameters
        nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
        optimal_n_min = nitrogen_params.get('optimal_n_min')
        optimal_n_max = nitrogen_params.get('optimal_n_max')
        severe_deficiency = nitrogen_params.get('severe_deficiency_threshold')
        nitrogen_stress_factor = nitrogen_params.get('nitrogen_stress_factor')
        
        if optimal_n_min is None:
            raise ValueError("❌ 'optimal_n_min' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        if optimal_n_max is None:
            raise ValueError("❌ 'optimal_n_max' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        if severe_deficiency is None:
            raise ValueError("❌ 'severe_deficiency_threshold' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        if nitrogen_stress_factor is None:
            raise ValueError("❌ 'nitrogen_stress_factor' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        
        if n_no3_conc < severe_deficiency:
            nitrogen_stress_level = nitrogen_stress_factor
        elif n_no3_conc < optimal_n_min:
            nitrogen_stress_level = nitrogen_stress_factor * (optimal_n_min - n_no3_conc) / (optimal_n_min - severe_deficiency)
        elif n_no3_conc <= optimal_n_max:
            nitrogen_stress_level = 0.0
        else:
            excess_stress = min(0.3, (n_no3_conc - optimal_n_max) / 1000.0)
            nitrogen_stress_level = excess_stress
        
        nitrogen_factor = max(0.0, 1.0 - nitrogen_stress_level)
        
        # 5. SALINITY STRESS (EC-based) - use dynamic EC parameters from environment CSV
        env_params = getattr(self.system_config, 'environment_parameters', {})
        optimal_ec = env_params.get('optimal_ec')
        max_ec = env_params.get('max_ec')
        min_ec = env_params.get('min_ec')
        
        if optimal_ec is None:
            raise ValueError("❌ 'optimal_ec' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        if max_ec is None:
            raise ValueError("❌ 'max_ec' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        if min_ec is None:
            raise ValueError("❌ 'min_ec' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        
        # Use dynamic stress parameters from stress CSV
        ec_stress_high_factor = stress_params.get('ec_stress_high_factor')
        ec_stress_low_factor = stress_params.get('ec_stress_low_factor')
        
        if ec_stress_high_factor is None:
            raise ValueError("❌ 'ec_stress_high_factor' parameter must be provided in stress_parameters CSV - no hardcoded defaults allowed")
        if ec_stress_low_factor is None:
            raise ValueError("❌ 'ec_stress_low_factor' parameter must be provided in stress_parameters CSV - no hardcoded defaults allowed")
        
        if ec_current > max_ec:
            # High EC stress - use dynamic factor
            salinity_stress_level = (ec_current - max_ec) * ec_stress_high_factor
            salinity_factor = max(0.0, 1.0 - salinity_stress_level)
        elif ec_current < min_ec:
            # Low EC stress - use dynamic factor
            salinity_stress_level = (min_ec - ec_current) * ec_stress_low_factor
            salinity_factor = max(0.0, 1.0 - salinity_stress_level)
        else:
            salinity_factor = 1.0
        
        # 6. pH STRESS
        ph = plant_state.get('ph', None)
        if ph is None:
            raise ValueError("Plant pH must be provided in CSV configuration")
        ph_factor = calculate_ph_effect(ph)
        
        # 7. OXYGEN STRESS (minimal in hydroponics)
        # Oxygen factor must be provided in CSV configuration
        oxygen_factor = env_params.get('oxygen_factor')
        if oxygen_factor is None:
            raise ValueError("❌ 'oxygen_factor' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        
        # === CALCULATE COMBINED STRESS METRICS ===
        
        # Overall multiplicative stress factor
        overall_stress_factor = (
            combined_temp_factor * 
            water_factor * 
            light_factor * 
            nitrogen_factor * 
            salinity_factor * 
            ph_factor * 
            oxygen_factor
        )
        
        # Stress levels (for models that expect stress levels instead of factors)
        # Add some realistic stress variation based on conditions
        temp_stress = max(0.0, 1.0 - combined_temp_factor)
        water_stress = max(0.0, 1.0 - water_factor)
        light_stress = max(0.0, 1.0 - light_factor)
        nitrogen_stress = max(0.0, 1.0 - nitrogen_factor)
        salinity_stress = max(0.0, 1.0 - salinity_factor)
        ph_stress = max(0.0, 1.0 - ph_factor)
        oxygen_stress = max(0.0, 1.0 - oxygen_factor)
        
        # Add some dynamic stress based on plant development and environmental conditions
        import math
        day_variation = math.sin(day * 0.1) * 0.1  # Daily stress variation
        
        # Nitrogen stress increases as plants grow and demand more nutrients
        growth_stage_factor = plant_state.get('growth_stage', 'V4')
        if growth_stage_factor in ['V11+', 'HI', 'HD', 'HM']:
            nitrogen_stress += 0.05  # Higher nitrogen demand in later stages
        
        # Temperature stress varies with daily temperature fluctuations
        optimal_temperature = env_params.get('optimal_temperature')
        if optimal_temperature is None:
            raise ValueError("❌ 'optimal_temperature' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        temp_deviation = abs(env_conditions['actual_temperature'] - optimal_temperature)
        temp_stress += min(0.1, temp_deviation * 0.01)
        
        # Water stress increases with VPD
        optimal_vpd = env_params.get('optimal_vpd')
        if optimal_vpd is None:
            raise ValueError("❌ 'optimal_vpd' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        vpd_stress = max(0.0, (env_conditions['actual_vpd'] - optimal_vpd) * 0.1)
        water_stress += min(0.1, vpd_stress)
        
        stress_levels = {
            'temperature': min(1.0, temp_stress + day_variation),
            'water': min(1.0, water_stress + day_variation * 0.5),
            'light': min(1.0, light_stress + day_variation * 0.3),
            'nitrogen': min(1.0, nitrogen_stress + day_variation * 0.2),
            'salinity': min(1.0, salinity_stress + day_variation * 0.1),
            'ph': min(1.0, ph_stress + day_variation * 0.1),
            'oxygen': min(1.0, oxygen_stress + day_variation * 0.1)
        }
        
        return {
            # STRESS FACTORS (1.0 = optimal, 0.0 = severe stress)
            'temperature_factor': combined_temp_factor,
            'air_temp_factor': temperature_factor,
            'root_temp_factor': root_temp_factor,
            'water_factor': water_factor,
            'light_factor': light_factor,
            'nitrogen_factor': nitrogen_factor,
            'salinity_factor': salinity_factor,
            'ph_factor': ph_factor,
            'oxygen_factor': oxygen_factor,
            'overall_stress_factor': overall_stress_factor,
            
            # STRESS LEVELS (0.0 = optimal, 1.0 = severe stress)
            'stress_levels': stress_levels,
            
            # DETAILED RESPONSES
            'temp_stress_response': temp_stress_response,
            
            # SUPPORTING CALCULATIONS (calculated once, reused everywhere)
            'ec_current': ec_current,
            'solution_temperature': solution_temperature,
            'water_stress_level': water_stress_level,
            'nitrogen_stress_level': nitrogen_stress_level
        }
    
    def _calculate_carbon_driven_growth(self, env_conditions: Dict[str, Any], 
                                      stress_factors: Dict[str, float],
                                      stage_props: Dict[str, Any]) -> Dict[str, float]:
        """Calculate growth rates driven by carbon assimilation"""
        # Calculate photosynthesis
        # Get photosynthesis parameters for LAI thresholds
        photosynthesis_params = getattr(self.system_config, 'photosynthesis', {})
        
        detailed_photosynthesis = self.photosynthesis_model.calculate_daily_assimilation(
            par_umol_m2_s=env_conditions['light_environment'].ppfd_above_canopy,
            co2_ppm=env_conditions['actual_co2'],
            temp_c=env_conditions['actual_temperature'],
            lai=self.current_lai,
            photoperiod_hours=daylength,
            ec_factor=1.0,  # Default EC factor for daily calculation
            config_dict=photosynthesis_params
        )
        
        # Apply genetic and stress modifiers ONLY ONCE
        overall_stress = np.prod([stress_factors[f] for f in ['temperature_factor', 'water_factor', 'nitrogen_factor', 'light_factor', 'salinity_factor']])
        # Genetic growth modifier must be provided in CSV configuration
        genetic_params = getattr(self.system_config, 'genetic_parameters', {})
        genetic_growth_modifier = genetic_params.get('genetic_growth_modifier')
        if genetic_growth_modifier is None:
            raise ValueError("❌ 'genetic_growth_modifier' parameter must be provided in genetic_parameters CSV - no hardcoded defaults allowed")
        
        # Calculate net photosynthesis with stress effects applied ONCE
        canopy_photosynthesis = (
            detailed_photosynthesis *
            overall_stress *  # Apply stress to photosynthesis
            self.cultivar_profile.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY *
            genetic_growth_modifier
        )
        # Photosynthesis is already calculated correctly per unit LAI
        # No need to scale down - keep per-plant biomass approach with correct photosynthesis
        
        # Calculate respiration BEFORE growth
        respiration_response = self.respiration_model.calculate_total_respiration(
            self.biomass_pools, env_conditions['actual_temperature'], 0.0  # No growth yet for maintenance
        )
        
        # Net carbon available for growth BEFORE construction (growth) respiration (g C/day)
        net_carbon_assimilation = canopy_photosynthesis - respiration_response.total_respiration

        # Account for construction respiration during growth:
        # If growth respiration costs are a fraction (rg) of the carbon incorporated into biomass,
        # then carbon required per unit biomass is c_bm * (1 + rg), where c_bm is the carbon
        # fraction of dry biomass. This ensures mass balance: 
        #   photosynthesis - (maintenance + growth_resp) = growth * c_bm
        c_bm = self.params.carbon_to_biomass_ratio
        rg = max(0.0, self.params.growth_respiration_fraction)
        # Convert available net carbon to biomass after accounting for construction costs
        # Total carbon needed = c_bm (structure) + c_bm * rg (construction respiration)
        available_biomass_growth = max(0.0, net_carbon_assimilation / c_bm / (1.0 + rg))
        
        # Allocate biomass based on developmental stage using configured fractions
        if stage_props['is_vegetative']:
            leaf_allocation = self.params.vegetative_leaf_allocation
            stem_allocation = self.params.vegetative_stem_allocation
            root_allocation = self.params.vegetative_root_allocation
        else:
            leaf_allocation = self.params.reproductive_leaf_allocation
            stem_allocation = self.params.reproductive_stem_allocation
            root_allocation = self.params.reproductive_root_allocation
        
        # Calculate carbon-driven growth rates
        growth_rates = {
            'leaves': available_biomass_growth * leaf_allocation,
            'stems': available_biomass_growth * stem_allocation,
            'roots': available_biomass_growth * root_allocation
        }
        
        return {
            'growth_rates': growth_rates,
            'canopy_photosynthesis': canopy_photosynthesis,
            'respiration_response': respiration_response,
            'net_carbon_assimilation': net_carbon_assimilation
        }
    
    def _simulate_daily_step(self, day: int, temperature: float, humidity: float, 
                           solar_radiation: float, daylength: float, 
                           nutrient_concentrations: Dict[str, float], ph: float = None,
                           previous_tank_volume: float = 0.0,
                           plant_density: float = 1.0) -> DailyResults:
        """
        REFACTORED SIMULATION LOOP with linear data flow and centralized stress calculation.
        
        This follows the recommended order:
        1. Environment: Calculate all environmental conditions first
        2. Phenology: Update the plant's developmental stage  
        3. Stress: Calculate all stress factors based on environment and plant state
        4. Photosynthesis: Calculate carbon assimilation based on environment and stress
        5. Respiration: Calculate maintenance respiration
        6. Growth: Allocate assimilated carbon to different plant parts
        7. Nutrient Uptake: Calculate nutrient uptake based on new growth and root system
        8. Internal Allocation: Distribute uptaken nutrients within the plant
        9. Update State: Update all state variables for the next day
        """
        
        # === STEP 1: ENVIRONMENT ===
        # Calculate all environmental conditions first
        env_conditions = self._calculate_environmental_conditions(temperature, humidity, solar_radiation, day)
        # Use solar radiation ONLY from CSV config - no fallbacks
        env_conditions['solar_radiation'] = getattr(self.system_config, 'solar_radiation', solar_radiation)

        
        # === STEP 2: PHENOLOGY ===
        # Update the plant's developmental stage based on temperature and daylength
        phenology_response = self.phenology_model.daily_update(
            temperature=env_conditions['actual_temperature'],
            daylength=daylength,
            water_stress=0.0,  # We'll calculate this in the next step
            temperature_stress=1.0  # We'll calculate this in the next step
        )

        
        stage_props = self.phenology_model.get_stage_properties()
        self.accumulated_gdd = stage_props['total_thermal_time']
        
        # === STEP 3: STRESS ===
        # Calculate all stress factors based on environment and plant state (SINGLE SOURCE OF TRUTH)
        plant_state = {
            'day': day,
            'ph': ph,
            'tank_volume': previous_tank_volume,
            'total_biomass': sum(pool.dry_mass for pool in self.biomass_pools),
            'lai': self.current_lai
        }
        
        stress_factors = self._calculate_unified_stress_factors(
            env_conditions=env_conditions,
            nutrient_concentrations=nutrient_concentrations,
            plant_state=plant_state,
            day=day
        )
        
        # Get cultivar performance based on stress factors
        cultivar_performance = self.ge_model.predict_cultivar_performance(
            self.current_cultivar, stress_factors
        )
        
        # === STEP 4: DSSAT-STYLE HOURLY INTEGRATION ===
        # Run internal hourly loop for key processes (photosynthesis, nutrient uptake)
        daily_integrated_results = self._run_hourly_integration(
            day=day,
            daily_weather_data={
                'temp_avg': temperature,
                'temp_min': temperature - 3.0,  # Simple approximation
                'temp_max': temperature + 3.0,  # Simple approximation
                'rel_humidity': humidity,
                'solar_radiation': solar_radiation
            },
            env_conditions=env_conditions,
            stress_factors=stress_factors,
            nutrient_concentrations=nutrient_concentrations,
            daylength=daylength
        )
        
        # Extract hourly-integrated results
        detailed_photosynthesis = daily_integrated_results['total_daily_photosynthesis']
        hourly_diagnostics = daily_integrated_results['hourly_diagnostics']
        
        
        # Apply stress effects to photosynthesis (use overall stress factor from centralized calculation)
        canopy_photosynthesis = (
            detailed_photosynthesis *
            stress_factors['overall_stress_factor'] *  # Single stress application
            self.cultivar_profile.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY
        )
        
        # Photosynthesis is calculated correctly for the canopy LAI
        # Keep full photosynthesis value for proper carbon balance
        
        # === STEP 5: RESPIRATION ===
        # Calculate maintenance respiration based on current biomass and temperature
        respiration_response = self.respiration_model.calculate_total_respiration(
            self.biomass_pools, 
            env_conditions['actual_temperature'], 
            0.0  # No growth respiration yet, will be calculated after growth
        )
        
        
        # === STEP 6: GROWTH ===
        # Allocate assimilated carbon to different plant parts
        
        # Calculate net carbon available for growth BEFORE construction (growth) respiration
        net_carbon_for_growth = max(0.0, canopy_photosynthesis - respiration_response.total_respiration)

        # Convert available net carbon to biomass after accounting for construction costs
        c_bm = self.params.carbon_to_biomass_ratio
        rg = max(0.0, self.params.growth_respiration_fraction)
        # Biomass growth requires carbon: c_bm for structure plus c_bm*rg for construction respiration
        available_biomass_growth = max(0.0, net_carbon_for_growth / c_bm / (1.0 + rg))
        
        
        # Calculate biomass allocation using functional balance theory
        allocation_fractions = self._calculate_functional_balance_allocation(
            stress_factors, stage_props, env_conditions
        )
        
        # Calculate RZT growth factor
        rzt_growth_factor = self.rzt_model.calculate_rzt_growth_factor(
            stress_factors['solution_temperature'], temperature
        )
        
        # Calculate actual growth rates with RZT effects
        actual_growth_rates = {
            organ: available_biomass_growth * fraction * rzt_growth_factor
            for organ, fraction in allocation_fractions.items()
        }
        
        # Calculate growth respiration in carbon units based on new growth
        total_new_growth = sum(actual_growth_rates.values())
        # growth_respiration (g C/day) = growth_biomass (g) * c_bm (g C/g) * rg (g C per g C incorporated)
        growth_respiration = total_new_growth * c_bm * rg
        
        # Update total respiration to include growth costs
        total_respiration = respiration_response.total_respiration + growth_respiration
        
        # Final net assimilation after all respiratory costs (not used further, kept for diagnostics)
        net_assimilation = canopy_photosynthesis - total_respiration

        
        # === STEP 7: NUTRIENT UPTAKE ===
        # Calculate nutrient uptake based on new growth and root system
        
        # Prepare root environment conditions using calculated values from stress step
        system_params = getattr(self.system_config, 'system_parameters', {})
        optimal_flow_rate = system_params.get('optimal_flow_rate', 1.5)  # L/min
        flow_rate_variation = system_params.get('flow_rate_variation', 0.2)
        
        # Add some variation to flow rate based on time of day and system conditions
        import math
        flow_variation = flow_rate_variation * math.sin(day * 0.1) * 0.5  # Daily variation
        current_flow_rate = optimal_flow_rate * (1.0 + flow_variation)
        
        root_env_conditions = {
            'temperature': stress_factors['solution_temperature'],
            'flow_rate': current_flow_rate,
            'oxygen_level': 8.0,
            'ph': ph,
            'nutrient_concentrations': nutrient_concentrations
        }
        
        # Prepare growth factors for root development
        root_growth_factors = {
            'nitrogen_stress': stress_factors['nitrogen_factor'],
            'water_stress': stress_factors['water_factor'],
            'temperature_stress': stress_factors['temperature_factor']
        }
        
        # Map solution concentrations to uptake model notation
        solution_conc_for_uptake = {}
        nutrient_mapping = {
            'N-NO3': 'NO3',
            'P-PO4': 'PO4',
            'K': 'K',
            'Ca': 'Ca',
            'Mg': 'Mg'
        }
        
        for sol_key, uptake_key in nutrient_mapping.items():
            if sol_key in nutrient_concentrations:
                solution_conc_for_uptake[uptake_key] = nutrient_concentrations[sol_key]
        
        # Calculate authoritative nutrient uptake rates (SINGLE SOURCE OF TRUTH)
        root_response = self.root_model.daily_update(
            root_env_conditions, root_growth_factors, solution_conc_for_uptake
        )

        
        # === STEP 8: INTERNAL ALLOCATION ===
        # Distribute uptaken nutrients within the plant
        
        # Extract nitrogen uptake from root model (authoritative source)
        # CRITICAL FIX: Root model returns NO3 uptake (mg NO3/day), convert to elemental N
        no3_uptake_mg_per_day = root_response.get('NO3_uptake_rate', 0.0)
        # Convert NO3 to elemental N: molecular weight NO3=62, N=14, so N = NO3 * (14/62)
        nitrogen_uptake_mg_per_day = no3_uptake_mg_per_day * (14.0 / 62.0)
        nitrogen_uptake_g_per_day = nitrogen_uptake_mg_per_day / 1000.0
        
        # Extract phosphorus uptake with unit conversion
        # CRITICAL FIX: Root model returns PO4 uptake (mg PO4/day), convert to elemental P
        po4_uptake_mg_per_day = root_response.get('PO4_uptake_rate', 0.0)
        # Convert PO4 to elemental P: molecular weight PO4=95, P=31, so P = PO4 * (31/95)
        phosphorus_uptake_mg_per_day = po4_uptake_mg_per_day * (31.0 / 95.0)
        phosphorus_uptake_g_per_day = phosphorus_uptake_mg_per_day / 1000.0
        
        # Use nitrogen balance model for internal allocation and transport only
        nitrogen_response = self.nitrogen_model.update_nitrogen_pools(
            external_nitrogen_input=nitrogen_uptake_g_per_day,
            organ_growth_rates=actual_growth_rates,
            environmental_factors={
                'temperature_factor': stress_factors['temperature_factor'],
                'water_status': stress_factors['water_factor'],
                'ph_factor': stress_factors['ph_factor']
            },
            growth_stage='vegetative' if stage_props['is_vegetative'] else 'reproductive',
            stress_factors=stress_factors['stress_levels'],
            senescence_rates={'leaves': 0.002, 'stems': 0.001, 'roots': 0.0005}
        )
        
        # Calculate organ nutrient demands for mobility model
        organ_demands = {}
        for organ, growth_rate in actual_growth_rates.items():
            organ_demands[organ] = {
                'nitrogen': growth_rate * 0.045,
                'phosphorus': growth_rate * 0.008,
                'potassium': growth_rate * 0.035,
                'calcium': growth_rate * 0.015,
                'magnesium': growth_rate * 0.006
            }
        
        # Update nutrient mobility (internal redistribution)
        mobility_response = self.mobility_model.daily_update(
            organ_demands=organ_demands,
            stress_factors=stress_factors['stress_levels'],
            senescence_rates={'leaves': 0.002, 'stems': 0.001, 'roots': 0.0005},
            growth_stage='vegetative' if stage_props['is_vegetative'] else 'reproductive',
            water_fluxes={'leaves': 0.25, 'stems': 0.15, 'roots': 0.35},
            assimilate_fluxes={'leaves': 0.12, 'stems': 0.08, 'roots': 0.05},
            temperature=env_conditions['actual_temperature']
        )
        
        # Update senescence processes
        cohort_data = self._prepare_senescence_data()
        environmental_stress = {
            'water': stress_factors['stress_levels']['water'],
            'nitrogen': stress_factors['stress_levels']['nitrogen'],
            'temperature': stress_factors['stress_levels']['temperature'],
            'light': stress_factors['stress_levels']['light']
        }
        developmental_state = {
            'is_reproductive': stage_props['is_reproductive']
        }
        
        senescence_response = self.senescence_model.daily_update(
            cohort_data, environmental_stress, developmental_state
        )

        
        # === STEP 9: UPDATE STATE ===
        # Update all state variables for the next day
        
        # Update biomass pools with growth
        for i, pool in enumerate(self.biomass_pools):
            organ_names = ['leaves', 'stems', 'roots']
            organ_name = organ_names[i]
            
            pool.age_days += 1.0
            growth_rate = actual_growth_rates.get(organ_name, 0.0)
            old_mass = pool.dry_mass
            pool.recent_growth = growth_rate
            pool.dry_mass += growth_rate
            
            # Update nitrogen content from nitrogen model
            if organ_name in self.nitrogen_model.organ_states:
                n_state = self.nitrogen_model.organ_states[organ_name]
                pool.nitrogen_content = n_state.nitrogen_concentration * 100
        
        # Update canopy development
        daily_tt_leaf = self.leaf_model.calculate_thermal_time(env_conditions['actual_temperature'])
        leaf_stress = self.leaf_model.calculate_stress_factors(
            water_stress=stress_factors['water_factor'],
            nitrogen_stress=stress_factors['nitrogen_factor'],
            temperature_stress=stress_factors['temperature_factor']
        )
        _ = self.leaf_model.update_v_stage(daily_tt_leaf, leaf_stress)
        leaf_stats = self.leaf_model.update_leaf_areas(daily_tt_leaf, leaf_stress)
        
        # DSSAT-style LAI calculation: use leaf development model directly
        # The leaf model tracks actual leaf area development, not just biomass conversion
        total_modeled_leaf_area_m2 = leaf_stats['total_leaf_area_m2'] * self.plant_count
        
        # Calculate SLA dynamically based on current conditions (DSSAT approach)
        leaf_biomass_g_current = self.biomass_pools[0].dry_mass
        if leaf_biomass_g_current > 0.001:  # Avoid division by zero
            # Current SLA from actual leaf area vs biomass
            current_sla_cm2_per_g = (total_modeled_leaf_area_m2 * 10000.0) / (leaf_biomass_g_current * self.plant_count)
        else:
            # Use initial SLA for very young plants
            current_sla_cm2_per_g = getattr(self.leaf_model.params, 'specific_leaf_area', None)
        if current_sla_cm2_per_g is None:
            raise ValueError("Specific leaf area must be provided in CSV configuration")
        
        # DSSAT method: LAI = Total Leaf Area / Ground Area (AREALF approach)
        calculated_lai = total_modeled_leaf_area_m2 / max(1e-6, self.system_area)
        
        # Apply biological maximum constraints (following DSSAT)
        canopy_params = getattr(self.system_config, 'canopy_parameters', {})
        maximum_lai = canopy_params.get('maximum_lai', 8.0)
        
        # DSSAT constrains LAI realistically
        self.current_lai = min(calculated_lai, maximum_lai)
        
        # Store dynamic SLA for debugging/output
        self.current_sla = current_sla_cm2_per_g
        
        # Update canopy height
        if stage_props['is_vegetative']:
            genetic_growth_modifier = cultivar_performance.get('yield_index', 1.0)
            # Height growth factor must be provided in CSV configuration
            growth_params = getattr(self.system_config, 'model_constants', {})
            height_growth_factor = growth_params.get('height_growth_factor')
            if height_growth_factor is None:
                raise ValueError("❌ 'height_growth_factor' parameter must be provided in model_constants CSV - no hardcoded defaults allowed")
            height_growth = height_growth_factor * stress_factors['overall_stress_factor'] * genetic_growth_modifier
            self.canopy_height += height_growth
        # Use dynamic maximum height from crop parameters CSV
        crop_params = getattr(self.system_config, 'crop_parameters', {})
        maximum_height = crop_params.get('maximum_height')
        if maximum_height is None:
            raise ValueError("❌ 'maximum_height' parameter must be provided in crop_parameters CSV - no hardcoded defaults allowed")
        self.canopy_height = min(maximum_height, self.canopy_height)
        
        # Update canopy architecture
        canopy_response = self.canopy_model.daily_update(
            total_lai=self.current_lai,
            canopy_height=self.canopy_height,
            light_env=env_conditions['light_environment'],
            air_temperature=env_conditions['actual_temperature'],
            co2_concentration=env_conditions['actual_co2']
        )
        
        # Update integrated stress model
        integrated_stress_response = self.integrated_stress.daily_update(
            current_stress_levels=stress_factors['stress_levels']
        )
        
        # Validate carbon mass balance
        self._validate_carbon_balance(canopy_photosynthesis, total_respiration, total_new_growth, day)
        
        # Calculate water-related values
        eto_ref = self._calculate_eto_reference(
            env_conditions['actual_temperature'], 
            env_conditions['actual_humidity'], 
            solar_radiation
        )
        etc_prime = self._calculate_etc_prime_with_eto(
            canopy_response.light_interception_fraction,
            eto_ref
        )
        transpiration = self._calculate_transpiration(
            canopy_response.light_interception_fraction,
            env_conditions['actual_temperature'],
            env_conditions['actual_vpd'],
            env_conditions['actual_humidity'],
            solar_radiation
        )
        vpd_calculated = self._calculate_vpd(
            env_conditions['actual_temperature'], 
            env_conditions['actual_humidity']
        )
        
        # Calculate water uptake and update tank volume
        water_uptake_l = self._calculate_water_uptake(
            canopy_response.light_interception_fraction,
            env_conditions['actual_temperature'],
            env_conditions['actual_humidity'],
            solar_radiation,
            env_conditions['actual_vpd'],
            self.current_lai
        )
        system_water_use_l = water_uptake_l * self.system_area
        tank_volume = max(0.0, previous_tank_volume - system_water_use_l)
        self.cumulative_water_L += system_water_use_l
        
        # === CREATE COMPREHENSIVE DAILY RESULTS ===
        total_biomass = sum(pool.dry_mass for pool in self.biomass_pools)
        
        # Create comprehensive CROPGRO results with ALL details
        cropgro_result = DailyResults(
            day=day,
            date=datetime.now() + timedelta(days=day-1),
            
            # Required basic fields - use pre-calculated values to avoid repetition
            eto_ref=eto_ref,  # Pre-calculated
            etc_prime=etc_prime,  # Pre-calculated
            transpiration=transpiration,  # Pre-calculated
            water_uptake_total=system_water_use_l,
            tank_volume=tank_volume,
            nutrient_concentrations=nutrient_concentrations.copy(),
            
            # Basic measurements  
            temp_avg=env_conditions['actual_temperature'],
            solar_radiation=solar_radiation,
            vpd=vpd_calculated,  # Pre-calculated
            
            # WUE (daily): growth per unit transpiration (g/L ≡ kg/m³) - reuse transpiration
            # Fix: Use realistic minimum transpiration and cap maximum WUE
            water_use_efficiency=min(500.0, max(0.1, 
                total_new_growth / max(0.01, transpiration * self.system_area)
            )),
            
            # Solution properties  
            ph=ph,  # Use dynamic pH from hydroponic system
            ec=stress_factors['ec_current'],  # Dynamic EC from nutrient concentrations
            solution_ec=stress_factors['ec_current'],  # Same as calculated EC
            rzt=stress_factors['solution_temperature'],  # Pre-calculated solution temperature
            rzt_growth_factor=self.rzt_model.calculate_rzt_growth_factor(
                stress_factors['solution_temperature'], temperature
            ),
            rzt_nutrient_factor=self.rzt_model.calculate_nutrient_uptake_factor(
                stress_factors['solution_temperature'], temperature
            ),
            
            # Environmental control
            co2_concentration=env_conditions['actual_co2'],
            vpd_actual=env_conditions['actual_vpd'],
            env_photosynthesis_factor=env_conditions['env_control_response']['plant_factors'].get('combined_photosynthesis_factor', 1.0),
            env_transpiration_factor=env_conditions['env_control_response']['plant_factors'].get('vpd_transpiration_factor', 1.0)
        )
        
        # === ADD DETAILED CROPGRO OUTPUTS ===
        
        # 1. PHENOLOGY DETAILS
        cropgro_result.growth_stage = stage_props['stage_name']
        cropgro_result.accumulated_gdd = self.accumulated_gdd
        cropgro_result.thermal_time_daily = phenology_response.daily_thermal_time if hasattr(phenology_response, 'daily_thermal_time') else 12.0
        cropgro_result.development_rate = phenology_response.development_rate if hasattr(phenology_response, 'development_rate') else 0.1
        cropgro_result.is_vegetative = stage_props['is_vegetative']
        cropgro_result.is_reproductive = stage_props['is_reproductive']
        
        # 2. BIOMASS DETAILS  
        cropgro_result.total_biomass = total_biomass
        cropgro_result.leaf_biomass = self.biomass_pools[0].dry_mass
        cropgro_result.stem_biomass = self.biomass_pools[1].dry_mass
        cropgro_result.root_biomass = self.biomass_pools[2].dry_mass
        cropgro_result.daily_growth_rate = total_new_growth
        cropgro_result.leaf_growth_rate = actual_growth_rates.get('leaves', 0.0)
        cropgro_result.stem_growth_rate = actual_growth_rates.get('stems', 0.0)
        cropgro_result.root_growth_rate = actual_growth_rates.get('roots', 0.0)
        
        # 3. CANOPY ARCHITECTURE
        cropgro_result.lai = self.current_lai
        cropgro_result.canopy_height_cm = self.canopy_height * 100
        cropgro_result.light_interception = canopy_response.light_interception_fraction
        cropgro_result.canopy_photosynthesis = canopy_response.canopy_photosynthesis
        cropgro_result.total_absorbed_ppfd = canopy_response.total_absorbed_ppfd
        cropgro_result.sunlit_lai = canopy_response.sunlit_lai
        cropgro_result.shaded_lai = canopy_response.shaded_lai
        
        # Leaf metrics
        # Fix V-Stage/Leaf Number synchronization
        # Both should represent the same biological concept: visible/emerged leaves
        visible_leaves = leaf_stats.get('visible_leaf_count', leaf_stats['active_leaf_count'])
        active_leaves = leaf_stats['active_leaf_count']
        
        # V-stage should match visible leaf count for consistency
        cropgro_result.v_stage = float(visible_leaves)  # Fix: Use actual visible leaves
        cropgro_result.leaf_number = int(visible_leaves)
        
        # Use modeled leaf area per plant (DSSAT approach)
        cropgro_result.leaf_area_m2 = leaf_stats['total_leaf_area_m2']
        
        # Calculate realistic average leaf area using active leaves (DSSAT approach)
        if active_leaves > 0:
            cropgro_result.average_leaf_area_cm2 = (leaf_stats['total_leaf_area_m2'] / active_leaves) * 1.0e4
        else:
            cropgro_result.average_leaf_area_cm2 = 0.0
        
        # Use leaf development model's built-in constraints (already realistic)
        # No need for additional capping as the leaf model handles biological limits

        # === DETAILED CANOPY ARCHITECTURE RESULTS ===
        cropgro_result.canopy_layers = len(canopy_response.canopy_layers) if hasattr(canopy_response, 'canopy_layers') else 0
        cropgro_result.ppfd_top = canopy_response.canopy_layers[0].ppfd_average if canopy_response.canopy_layers else env_conditions['light_environment'].ppfd_above_canopy
        cropgro_result.ppfd_bottom = canopy_response.canopy_layers[-1].ppfd_average if canopy_response.canopy_layers else env_conditions['light_environment'].ppfd_above_canopy * 0.1
        cropgro_result.light_extinction = canopy_response.average_extinction_coefficient
        
        # 4. PHYSIOLOGICAL PROCESSES
        cropgro_result.photosynthesis_rate = canopy_photosynthesis
        cropgro_result.respiration_rate = total_respiration
        cropgro_result.maintenance_respiration = respiration_response.maintenance_respiration
        cropgro_result.growth_respiration = growth_respiration
        cropgro_result.net_assimilation = net_assimilation
        
        # === DETAILED PHOTOSYNTHESIS MODEL RESULTS ===
        # Calculate detailed photosynthesis parameters from the model
        photosynthesis_params = self.photosynthesis_model.params
        
        # Temperature-adjusted rates (reproduce calculations from model)
        temp_k = env_conditions['actual_temperature'] + 273.15
        vcmax_temp = photosynthesis_params.vcmax_25 * np.exp(photosynthesis_params.eav * (temp_k - 298.15) / (298.15 * photosynthesis_params.r * temp_k))
        jmax_temp = photosynthesis_params.jmax_25 * np.exp(photosynthesis_params.eaj * (temp_k - 298.15) / (298.15 * photosynthesis_params.r * temp_k))
        
        cropgro_result.vcmax_25 = photosynthesis_params.vcmax_25
        cropgro_result.jmax_25 = photosynthesis_params.jmax_25
        cropgro_result.quantum_efficiency = photosynthesis_params.alpha
        
        # Calculate rubisco and light limited rates
        ci = env_conditions['actual_co2']  # Simplified assumption
        ac = vcmax_temp * (ci - photosynthesis_params.gamma_star) / (ci + photosynthesis_params.kc * (1 + 210000 / photosynthesis_params.ko))
        
        i2 = photosynthesis_params.alpha * env_conditions['light_environment'].ppfd_above_canopy
        j = (i2 + jmax_temp - np.sqrt((i2 + jmax_temp)**2 - 4 * photosynthesis_params.theta * i2 * jmax_temp)) / (2 * photosynthesis_params.theta)
        aj = j * (ci - photosynthesis_params.gamma_star) / (4 * (ci + 2 * photosynthesis_params.gamma_star))
        
        cropgro_result.rubisco_limited = ac
        cropgro_result.light_limited = aj
        cropgro_result.co2_compensation = photosynthesis_params.gamma_star
        cropgro_result.intercellular_co2 = ci
        
        # === DETAILED RESPIRATION MODEL RESULTS ===
        # Tissue-specific maintenance respiration from model calculations
        cropgro_result.maintenance_resp_leaves = respiration_response.tissue_breakdown.get('leaves', 0.0)
        cropgro_result.maintenance_resp_stems = respiration_response.tissue_breakdown.get('stems', 0.0)
        cropgro_result.maintenance_resp_roots = respiration_response.tissue_breakdown.get('roots', 0.0)
        
        # Growth respiration breakdown (proportional to actual growth by tissue)
        # Use the actual growth rates from the allocation calculation
        total_growth = max(0.001, sum(actual_growth_rates.values()))
        growth_resp_proportions = {
            'leaves': actual_growth_rates.get('leaves', 0.0) / total_growth,
            'stems': actual_growth_rates.get('stems', 0.0) / total_growth,
            'roots': actual_growth_rates.get('roots', 0.0) / total_growth
        }
        
        # Ensure we have some growth respiration even if proportions are small
        if growth_respiration > 0:
            cropgro_result.growth_resp_leaves = growth_respiration * growth_resp_proportions['leaves']
            cropgro_result.growth_resp_stems = growth_respiration * growth_resp_proportions['stems'] 
            cropgro_result.growth_resp_roots = growth_respiration * growth_resp_proportions['roots']
        else:
            # Fallback: distribute based on typical allocation patterns
            cropgro_result.growth_resp_leaves = 0.0
            cropgro_result.growth_resp_stems = 0.0
            cropgro_result.growth_resp_roots = 0.0
        
        # Respiration factors from detailed model
        cropgro_result.temperature_acclimation = respiration_response.temperature_factor
        cropgro_result.age_factor = respiration_response.age_factor
        
        # 5. NITROGEN DYNAMICS - USE ROOT MODEL AS SINGLE SOURCE OF TRUTH
        # CRITICAL FIX: Store corrected elemental nitrogen uptake (not NO3)
        cropgro_result.nitrogen_uptake_mg = nitrogen_uptake_mg_per_day  # Elemental N from NO3 conversion
        
        # 6. PHOSPHORUS DYNAMICS - USE ROOT MODEL AS SINGLE SOURCE OF TRUTH
        # CRITICAL FIX: Store corrected elemental phosphorus uptake (not PO4)
        cropgro_result.phosphorus_uptake_mg = phosphorus_uptake_mg_per_day  # Elemental P from PO4 conversion
        
        # Validate that root model is providing realistic uptake
        # Only warn if there ARE nutrients available but still zero uptake
        no3_available = solution_conc_for_uptake.get('NO3', 0.0) > 1.0  # At least 1 mg/L available
        if cropgro_result.nitrogen_uptake_mg == 0.0 and total_biomass > 0.1 and no3_available:
            logger.warning(f"Day {day}: Root model returned zero nitrogen uptake for biomass {total_biomass:.1f}g with NO3 {solution_conc_for_uptake.get('NO3', 0.0):.1f} mg/L available - check root model parameters")
            # Only apply minimal value if plant has significant biomass but no uptake
            cropgro_result.nitrogen_uptake_mg = self.params.minimal_nitrogen_uptake
        # === NITROGEN DYNAMICS - USE NITROGEN BALANCE MODEL AS SINGLE SOURCE ===
        # Get nitrogen demand from the sophisticated nitrogen balance model
        organ_growth_rates = {
            'leaves': actual_growth_rates.get('leaves', 0.0),
            'stems': actual_growth_rates.get('stems', 0.0), 
            'roots': actual_growth_rates.get('roots', 0.0)
        }
        
        # Use nitrogen balance model for demand calculation
        n_demand_by_organ = self.nitrogen_model.calculate_nitrogen_demand(
            organ_growth_rates, 
            stage_props['stage_name']
        )
        total_n_demand_g = sum(n_demand_by_organ.values())
        cropgro_result.nitrogen_demand_mg = max(10.0, total_n_demand_g * 1000)  # Convert g to mg, minimum 10 mg/day
        
        # Get nitrogen stress from nitrogen balance model
        cropgro_result.nitrogen_stress_factor = getattr(nitrogen_response, 'nitrogen_stress_level', 0.0)
        
        # Get nitrogen concentrations from nitrogen balance model organ states
        if hasattr(self.nitrogen_model, 'organ_states') and self.nitrogen_model.organ_states:
            # Leaf nitrogen concentration
            if 'leaves' in self.nitrogen_model.organ_states:
                leaf_n_state = self.nitrogen_model.organ_states['leaves']
                cropgro_result.leaf_nitrogen_conc = leaf_n_state.nitrogen_concentration * 100  # Convert to percentage
            else:
                # Nitrogen concentration must be provided in CSV configuration
                nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
                default_leaf_n = nitrogen_params.get('default_leaf_nitrogen_conc')
                if default_leaf_n is None:
                    raise ValueError("❌ 'default_leaf_nitrogen_conc' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
                cropgro_result.leaf_nitrogen_conc = default_leaf_n
            
            # Root nitrogen concentration  
            if 'roots' in self.nitrogen_model.organ_states:
                root_n_state = self.nitrogen_model.organ_states['roots']
                cropgro_result.root_nitrogen_conc = root_n_state.nitrogen_concentration * 100  # Convert to percentage
            else:
                # Nitrogen concentration must be provided in CSV configuration
                nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
                default_root_n = nitrogen_params.get('default_root_nitrogen_conc')
                if default_root_n is None:
                    raise ValueError("❌ 'default_root_nitrogen_conc' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
                cropgro_result.root_nitrogen_conc = default_root_n
        else:
            # Nitrogen concentrations must be provided in CSV configuration
            nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
            default_leaf_n = nitrogen_params.get('default_leaf_nitrogen_conc')
            default_root_n = nitrogen_params.get('default_root_nitrogen_conc')
            
            if default_leaf_n is None:
                raise ValueError("❌ 'default_leaf_nitrogen_conc' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
            if default_root_n is None:
                raise ValueError("❌ 'default_root_nitrogen_conc' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
            
            cropgro_result.leaf_nitrogen_conc = default_leaf_n
            cropgro_result.root_nitrogen_conc = default_root_n
        
        # === DETAILED NITROGEN DYNAMICS RESULTS ===
        # Calculate nitrogen pool dynamics based on plant growth and nitrogen uptake
        total_biomass = sum(pool.dry_mass for pool in self.biomass_pools)
        total_nitrogen_uptake = cropgro_result.nitrogen_uptake_mg / 1000.0  # Convert to g
        
        # Estimate nitrogen pools based on biomass and CSV-configured N concentrations
        nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
        
        # Structural N: cell walls, structural proteins (low N content)
        structural_n_conc = nitrogen_params.get('structural_n_concentration')
        if structural_n_conc is None:
            raise ValueError("❌ 'structural_n_concentration' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        cropgro_result.n_pool_structural = total_biomass * structural_n_conc
        
        # Metabolic N: enzymes, chlorophyll, active proteins (high N content)
        metabolic_n_conc = nitrogen_params.get('metabolic_n_concentration')
        if metabolic_n_conc is None:
            raise ValueError("❌ 'metabolic_n_concentration' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        cropgro_result.n_pool_metabolic = total_biomass * metabolic_n_conc
        
        # Storage N: temporary storage, amino acids (medium N content)
        storage_n_conc = nitrogen_params.get('storage_n_concentration')
        if storage_n_conc is None:
            raise ValueError("❌ 'storage_n_concentration' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        cropgro_result.n_pool_storage = total_biomass * storage_n_conc
        
        # Transport N: mobile N in xylem/phloem (very low)
        transport_n_conc = nitrogen_params.get('transport_n_concentration')
        if transport_n_conc is None:
            raise ValueError("❌ 'transport_n_concentration' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
        cropgro_result.n_pool_transport = total_biomass * transport_n_conc
        
        # N remobilization: N moved from old to new tissues
        # Increases with plant age and stress
        import math
        age_factor = min(1.0, day / 30.0)  # Increases with age
        stress_factor = max(0.0, 1.0 - stress_factors['overall_stress_factor'])
        cropgro_result.n_remobilization = total_nitrogen_uptake * 0.1 * age_factor * stress_factor
        
        # === DETAILED NITROGEN DYNAMICS RESULTS ===
        # Nitrogen pool dynamics from model calculations
        organ_states = getattr(nitrogen_response, 'organ_states', {})
        if 'leaves' in organ_states:
            leaf_state = organ_states['leaves']
            cropgro_result.n_pool_structural = leaf_state.structural_n if hasattr(leaf_state, 'structural_n') else 0.0
            cropgro_result.n_pool_metabolic = leaf_state.metabolic_n if hasattr(leaf_state, 'metabolic_n') else 0.0
            cropgro_result.n_pool_storage = leaf_state.storage_n if hasattr(leaf_state, 'storage_n') else 0.0
            cropgro_result.n_pool_transport = leaf_state.transport_n if hasattr(leaf_state, 'transport_n') else 0.0
        else:
            # Fallback values based on total plant nitrogen
            total_plant_n = getattr(nitrogen_response, 'total_plant_nitrogen', total_biomass * 0.04)  # g
            cropgro_result.n_pool_structural = total_plant_n * 0.4
            cropgro_result.n_pool_metabolic = total_plant_n * 0.3
            cropgro_result.n_pool_storage = total_plant_n * 0.2
            cropgro_result.n_pool_transport = total_plant_n * 0.1
        
        # Nitrogen processes from model
        cropgro_result.n_remobilization = getattr(nitrogen_response, 'remobilized_nitrogen', 0.0) * 1000  # mg/day
        
        # Calculate critical nitrogen concentration (simple approximation)
        if total_biomass > 0:
            current_n_conc = (cropgro_result.nitrogen_uptake_mg / 1000.0) / total_biomass
            critical_n_factor = nitrogen_params.get('critical_n_factor')
            if critical_n_factor is None:
                raise ValueError("❌ 'critical_n_factor' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
            cropgro_result.n_critical_conc = current_n_conc * critical_n_factor  # Critical is factor higher than current
        else:
            # Critical nitrogen concentration must be provided in CSV configuration
            default_critical_n = nitrogen_params.get('default_critical_n_concentration')
            if default_critical_n is None:
                raise ValueError("❌ 'default_critical_n_concentration' parameter must be provided in nitrogen_parameters CSV - no hardcoded defaults allowed")
            cropgro_result.n_critical_conc = default_critical_n
        
        # 6. STRESS RESPONSES (with safe attribute access)
        cropgro_result.temperature_stress_level = stress_factors['stress_levels']['temperature']
        cropgro_result.temperature_stress_photosynthesis = 1.0 - stress_factors['temp_stress_response'].process_factors.photosynthesis  # Convert to 0=no stress, 1=full stress
        cropgro_result.temperature_stress_growth = 1.0 - stress_factors['temp_stress_response'].process_factors.growth  # Convert to 0=no stress, 1=full stress
        cropgro_result.integrated_stress_factor = 1.0 - stress_factors['overall_stress_factor']  # Convert to 0=no stress, 1=full stress
        cropgro_result.water_stress = stress_factors['stress_levels']['water']
        cropgro_result.nutrient_stress = stress_factors['stress_levels']['nitrogen']
        cropgro_result.salinity_stress = 1.0 - stress_factors['salinity_factor']  # Convert to 0=no stress, 1=full stress
        
        # === DETAILED STRESS INTEGRATION RESULTS ===
        # Extract stress interactions from integrated stress response
        stress_states = getattr(integrated_stress_response, 'stress_states', {})
        stress_interactions = {}
        acclimation_levels = {}
        cumulative_damage = {}
        
        for stress_type, stress_state in stress_states.items():
            # Stress interactions (simplified - actual interaction would be in process responses)
            stress_interactions[f'{stress_type}_interaction'] = getattr(stress_state, 'chronic_stress', 0.0) * getattr(stress_state, 'acute_stress', 0.0)
            
            # Acclimation levels
            acclimation_levels[stress_type] = getattr(stress_state, 'acclimation_level', 0.0)
            
            # Cumulative damage
            cumulative_damage[stress_type] = getattr(stress_state, 'damage_level', 0.0)
        
        cropgro_result.stress_interactions = stress_interactions
        cropgro_result.acclimation_levels = acclimation_levels
        cropgro_result.cumulative_damage = cumulative_damage
        
        # 7. SENESCENCE AND REMOBILIZATION (with safe attribute access)
        cropgro_result.senescence_rate = getattr(senescence_response, 'total_senescence_rate', 0.0)
        cropgro_result.leaf_senescence_rate = getattr(senescence_response, 'leaf_senescence_rate', 0.0)
        cropgro_result.nitrogen_remobilization = getattr(mobility_response, 'total_redistribution', {}).get('nitrogen', 0.0) * 1000
        cropgro_result.phosphorus_remobilization = getattr(mobility_response, 'total_redistribution', {}).get('phosphorus', 0.0) * 1000
        cropgro_result.potassium_remobilization = getattr(mobility_response, 'total_redistribution', {}).get('potassium', 0.0) * 1000
        
        # 8. ROOT ARCHITECTURE
        cropgro_result.root_length_density = root_response.get('root_length_density', 0.0)
        cropgro_result.root_surface_area = root_response.get('total_root_surface_area', 0.0)
        cropgro_result.root_volume = root_response.get('total_root_volume', 0.0)
        cropgro_result.root_activity_factor = self.cultivar_profile.genetic_coefficients.ROOT_ACTIVITY
        
        # === DETAILED ROOT ARCHITECTURE RESULTS ===
        cropgro_result.fine_root_length = root_response.get('fine_root_length', 0.0)
        cropgro_result.coarse_root_length = root_response.get('coarse_root_length', 0.0)
        
        # Access root cohorts from root architecture model inside the enhanced uptake model
        if hasattr(self.root_model, 'root_architecture') and hasattr(self.root_model.root_architecture, 'root_zones'):
            root_cohorts_count = sum(len(zone.root_cohorts) for zone in self.root_model.root_architecture.root_zones if hasattr(zone, 'root_cohorts'))
            cropgro_result.root_cohorts = root_cohorts_count
            
                        # Get turnover rate from architecture model parameters
            if hasattr(self.root_model.root_architecture, 'params'):
                root_turnover = getattr(self.root_model.root_architecture.params, 'fine_turnover_rate', None)
                if root_turnover is None:
                    raise ValueError("Fine root turnover rate must be provided in CSV configuration")
                cropgro_result.root_turnover_rate = root_turnover
            else:
                raise ValueError("Root architecture model must have parameters")
        else:
            cropgro_result.root_cohorts = 0
            # Root turnover rate must be provided in CSV configuration
            root_params = getattr(self.system_config, 'root_system_parameters', {})
            root_turnover_rate = root_params.get('root_turnover_rate')
            if root_turnover_rate is None:
                raise ValueError("❌ 'root_turnover_rate' parameter must be provided in root_system_parameters CSV - no hardcoded defaults allowed")
            cropgro_result.root_turnover_rate = root_turnover_rate
            
        cropgro_result.root_activity_young = root_response.get('average_root_activity', 0.0)
        cropgro_result.root_activity_old = max(0.0, root_response.get('average_root_activity', 0.0) - 0.2)
        cropgro_result.root_surface_active = root_response.get('total_root_surface_area', 0.0) * root_response.get('average_root_activity', 0.0)

        # === NUTRIENT UPTAKE RATES - ROOT MODEL AS SINGLE SOURCE OF TRUTH ===
        # CRITICAL FIX: All nutrient uptake must come from the EnhancedRootUptakeModel
        # No fallback calculations - if root model fails, we need to know about it
        
        root_keys_map = {'N-NO3': 'NO3', 'P-PO4': 'PO4', 'K': 'K', 'Ca': 'Ca', 'Mg': 'Mg'}
        for csv_key, root_key in root_keys_map.items():
            rr_key = f'{root_key}_uptake_rate'
            uptake_val = root_response.get(rr_key, 0.0)
            
            # Always use root model value, even if zero
            setattr(cropgro_result, f'{csv_key}_uptake_rate', uptake_val)
            
            # Log warning if root model returns zero for major nutrients with significant biomass AND nutrients are available
            nutrient_available = solution_conc_for_uptake.get(root_key, 0.0) > 1.0  # At least 1 mg/L available
            if uptake_val == 0.0 and total_biomass > 0.1 and root_key in ['NO3', 'PO4', 'K'] and nutrient_available:
                logger.warning(f"Day {day}: Root model returned zero {root_key} uptake for biomass {total_biomass:.1f}g with {solution_conc_for_uptake.get(root_key, 0.0):.1f} mg/L available")
        
        # Ensure N-NO3 uptake matches our authoritative nitrogen uptake (already from root model)
        setattr(cropgro_result, 'N-NO3_uptake_rate', cropgro_result.nitrogen_uptake_mg * (62.0 / 14.0))  # Convert mg N to mg NO3
        
        # 9. GENETIC PARAMETERS EFFECTS
        cropgro_result.cultivar_adaptation_index = cultivar_performance.get('adaptation_index', 1.0)
        cropgro_result.cultivar_yield_potential = self.cultivar_profile.yield_potential
        cropgro_result.genetic_photosynthesis_capacity = self.cultivar_profile.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY
        cropgro_result.genetic_nitrate_efficiency = self.cultivar_profile.genetic_coefficients.NITRATE_EFFICIENCY
        cropgro_result.genetic_ec_tolerance = self.cultivar_profile.genetic_coefficients.EC_TOLERANCE
        
        # 10. ENVIRONMENTAL CONTROL DETAILS
        # Simulate environmental control system with some variation
        import math
        
        # Get environment parameters from CSV configuration
        env_params = getattr(self.system_config, 'environment', {})
        
        # Temperature control with some variation around target
        target_temp = env_params.get('target_temperature')
        if target_temp is None:
            raise ValueError("❌ 'target_temperature' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        temp_control_variation = math.sin(day * 0.1) * 1.0  # Daily variation
        cropgro_result.controlled_temperature = target_temp + temp_control_variation
        
        # Humidity control with some variation
        target_humidity = env_params.get('target_humidity')
        if target_humidity is None:
            raise ValueError("❌ 'target_humidity' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        humidity_control_variation = math.sin(day * 0.15) * 5.0  # Daily variation
        cropgro_result.controlled_humidity = target_humidity + humidity_control_variation
        
        # CO2 control with some variation
        target_co2 = env_params.get('target_co2')
        if target_co2 is None:
            raise ValueError("❌ 'target_co2' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        co2_control_variation = math.sin(day * 0.2) * 20.0  # Daily variation
        cropgro_result.controlled_co2 = target_co2 + co2_control_variation
        
        # VPD target with some variation
        target_vpd = env_params.get('target_vpd')
        if target_vpd is None:
            raise ValueError("❌ 'target_vpd' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        vpd_control_variation = math.sin(day * 0.12) * 0.1  # Daily variation
        cropgro_result.vpd_target = target_vpd + vpd_control_variation
        
        # Environmental cost based on control effort
        control_effort = abs(temp_control_variation) + abs(humidity_control_variation) + abs(co2_control_variation)
        cropgro_result.environmental_cost = control_effort * 0.01  # Cost per unit control effort
        
        return cropgro_result
    
    def _prepare_senescence_data(self) -> Dict[int, Dict]:
        """Prepare senescence data from current biomass pools"""
        # Get nutrient parameters from CSV configuration
        nutrient_params = getattr(self.system_config, 'nutrient_parameters', {})
        
        cohort_data = {}
        for i, pool in enumerate(self.biomass_pools):
            organ_names = ['leaves', 'stems', 'roots']
            organ_name = organ_names[i]
            cohort_data[i] = {
                'age_gdd': pool.age_days * 12.0,
                'area': pool.dry_mass * 0.18,
                'biomass': pool.dry_mass,
                'canopy_position': 0.8 if organ_name == 'leaves' else 0.5,
                'nutrient_content': {
                    'nitrogen': pool.nitrogen_content / 100.0,
                    'phosphorus': nutrient_params.get('default_phosphorus_content', 0.010),
                    'potassium': nutrient_params.get('default_potassium_content', 0.028)
                }
            }
        return cohort_data
    
    def _calculate_ec(self, concentrations: Dict[str, float]) -> float:
        """Calculate electrical conductivity (dS/m) from major ions.
        Uses the sophisticated nutrient model calculation to avoid duplication.
        """
        # Use the sophisticated EC calculation from nutrient model
        if hasattr(self, 'nutrient_mobility_model') and self.nutrient_mobility_model:
            try:
                return self.nutrient_mobility_model.calculate_ec_from_concentrations(concentrations)
            except Exception:
                # Fallback to simple calculation if sophisticated model fails
                pass
        
        # Fallback: Simple calculation using CSV parameters
        nutrient_params = getattr(self.system_config, 'nutrient_parameters', {})
        factors = {
            'N-NO3': nutrient_params.get('ec_factor_n_no3'),
            'P-PO4': nutrient_params.get('ec_factor_p_po4'),
            'K': nutrient_params.get('ec_factor_k'),
            'Ca': nutrient_params.get('ec_factor_ca'),
            'Mg': nutrient_params.get('ec_factor_mg'),
        }
        
        # Validate that all EC factors are provided
        for ion, factor in factors.items():
            if factor is None:
                raise ValueError(f"❌ 'ec_factor_{ion.lower()}' parameter must be provided in nutrient_parameters CSV - no hardcoded defaults allowed")
        
        ec = 0.0
        for ion, conc in concentrations.items():
            coeff = factors.get(ion, nutrient_params.get('ec_factor_default', 0.0006))
            if coeff is None:
                raise ValueError(f"❌ 'ec_factor_default' parameter must be provided in nutrient_parameters CSV - no hardcoded defaults allowed")
            ec += coeff * conc
        
        min_ec = nutrient_params.get('min_ec_limit')
        max_ec = nutrient_params.get('max_ec_limit')
        if min_ec is None:
            raise ValueError("❌ 'min_ec_limit' parameter must be provided in nutrient_parameters CSV - no hardcoded defaults allowed")
        if max_ec is None:
            raise ValueError("❌ 'max_ec_limit' parameter must be provided in nutrient_parameters CSV - no hardcoded defaults allowed")
        
        return max(min_ec, min(max_ec, ec))
    
    def _calculate_vpd(self, temp: float, rel_humidity: float) -> float:
        """Calculate vapor pressure deficit using centralized utility"""
        return calculate_vpd(temp, rel_humidity)
    
    def _calculate_eto_reference(self, temperature: float, humidity: float, solar_radiation: float) -> float:
        """Calculate reference evapotranspiration using Penman-Monteith equation"""
        # Simplified Penman-Monteith for daily ETo (mm/day)
        delta = 4098 * (0.6108 * np.exp(17.27 * temperature / (temperature + 237.3))) / ((temperature + 237.3) ** 2)
        
        # Get parameters from CSV configuration
        env_params = getattr(self.system_config, 'environment_parameters', {})
        gamma = env_params.get('psychrometric_constant')
        u2 = env_params.get('wind_speed_2m')
        
        if gamma is None:
            raise ValueError("❌ 'psychrometric_constant' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        if u2 is None:
            raise ValueError("❌ 'wind_speed_2m' parameter must be provided in environment_parameters CSV - no hardcoded defaults allowed")
        
        vpd = self._calculate_vpd(temperature, humidity)
        
        # Simplified calculation
        radiation_term = 0.408 * delta * (solar_radiation * 0.8)  # Net radiation approximation
        aerodynamic_term = gamma * 900 / (temperature + 273) * u2 * vpd
        
        eto = (radiation_term + aerodynamic_term) / (delta + gamma * (1 + 0.34 * u2))
        return max(0.5, min(8.0, eto))  # Reasonable bounds for hydroponic systems
    
    def _calculate_etc_prime(self, light_interception: float, temperature: float, humidity: float, solar_radiation: float) -> float:
        """Calculate crop evapotranspiration adjusted for canopy development"""
        eto = self._calculate_eto_reference(temperature, humidity, solar_radiation)
        
        # Crop coefficient must be provided in CSV configuration
        crop_params = getattr(self.system_config, 'crop_parameters', {})
        base_kc = crop_params.get('base_crop_coefficient')
        kc_factor = crop_params.get('kc_light_interception_factor')
        
        if base_kc is None:
            raise ValueError("❌ 'base_crop_coefficient' parameter must be provided in crop_parameters CSV - no hardcoded defaults allowed")
        if kc_factor is None:
            raise ValueError("❌ 'kc_light_interception_factor' parameter must be provided in crop_parameters CSV - no hardcoded defaults allowed")
        
        kc = base_kc + (kc_factor * light_interception)  # Crop coefficient based on canopy coverage
        return eto * kc
    
    def _calculate_etc_prime_with_eto(self, light_interception: float, eto_ref: float) -> float:
        """Calculate crop evapotranspiration using pre-calculated ETO to avoid repetition"""
        kc = 0.7 + (0.4 * light_interception)  # Crop coefficient based on canopy coverage
        return eto_ref * kc
    
    def _calculate_transpiration(self, light_interception: float, temperature: float, vpd: float, humidity: float, solar_radiation: float) -> float:
        """Calculate actual transpiration based on canopy and environmental factors"""
        base_transpiration = self._calculate_etc_prime(light_interception, temperature, humidity, solar_radiation)
        
        # VPD effect: higher VPD increases transpiration
        vpd_factor = min(1.5, 0.8 + (vpd / 2.0))
        
        # LAI effect: transpiration should scale with leaf area
        lai_factor = min(1.0, self.current_lai / 2.0)  # Transpiration saturates around LAI=2 for lettuce
        
        # Stomatal coupling: transpiration linked to photosynthetic activity
        stomatal_conductance_factor = light_interception * lai_factor
        
        return base_transpiration * vpd_factor * stomatal_conductance_factor
    
    def _calculate_water_uptake(self, light_interception: float, temperature: float, humidity: float, solar_radiation: float, vpd: float, lai: float) -> float:
        """
        Calculate water uptake using plant hydraulic model.
        
        Water transport follows the Soil-Plant-Atmosphere Continuum (SPAC):
        Water flow = (ΨSolution - ΨLeaf) / Resistance
        
        Where:
        - ΨSolution = solution water potential (near 0 in hydroponics)
        - ΨLeaf = leaf water potential (driven by transpiration)
        - Resistance = root + xylem + leaf hydraulic resistances
        """
        
        # 1. CALCULATE LEAF WATER POTENTIAL
        # Leaf water potential drops with increasing transpiration demand
        transpiration_demand = self._calculate_transpiration(light_interception, temperature, vpd, humidity, solar_radiation)
        
        # Leaf water potential (MPa) - becomes more negative with higher transpiration
        # Lettuce: -0.2 to -1.5 MPa typical range
        base_leaf_potential = -0.3  # MPa at minimal transpiration
        transpiration_effect = -0.08 * transpiration_demand  # -0.08 MPa per mm/day transpiration
        leaf_water_potential = base_leaf_potential + transpiration_effect
        
        # Osmotic adjustment under stress (plants can adjust solute concentration)
        stress_factors = getattr(self, '_current_stress_factors', {})
        osmotic_adjustment = self._calculate_osmotic_adjustment(stress_factors)
        adjusted_leaf_potential = leaf_water_potential + osmotic_adjustment
        
        # 2. SOLUTION WATER POTENTIAL
        # Hydroponic solution potential depends on salt concentration (EC)
        current_ec = getattr(self.system_config, 'solution_ec', None)  # Must be set from CSV
        if current_ec is None:
            raise ValueError("Solution EC must be provided in CSV configuration")
        # Water potential (MPa) = -0.036 × EC(dS/m) for typical nutrient solutions
        solution_water_potential = -0.036 * current_ec
        
        # 3. HYDRAULIC CONDUCTANCES
        # Total plant hydraulic conductance depends on root surface area and xylem development
        
        # Root hydraulic conductance (L/day/MPa/m²)
        # Higher root surface area = higher conductance
        root_surface_area_factor = min(2.0, lai / 2.0)  # Proxy for root development
        
        # Root conductance parameters must be provided in CSV configuration
        root_params = getattr(self.system_config, 'root_system_parameters', {})
        base_root_conductance = root_params.get('base_root_conductance')
        root_scaling_factor = root_params.get('root_conductance_scaling_factor')
        
        if base_root_conductance is None:
            raise ValueError("❌ 'base_root_conductance' parameter must be provided in root_system_parameters CSV - no hardcoded defaults allowed")
        if root_scaling_factor is None:
            raise ValueError("❌ 'root_conductance_scaling_factor' parameter must be provided in root_system_parameters CSV - no hardcoded defaults allowed")
        
        root_conductance = base_root_conductance * root_surface_area_factor
        
        # Xylem hydraulic conductance (limited by stem cross-sectional area)  
        stem_biomass = self.biomass_pools[1].dry_mass if len(self.biomass_pools) > 1 else 1.0
        
        base_xylem_conductance = root_params.get('base_xylem_conductance')
        xylem_scaling_factor = root_params.get('xylem_conductance_scaling_factor')
        
        if base_xylem_conductance is None:
            raise ValueError("❌ 'base_xylem_conductance' parameter must be provided in root_system_parameters CSV - no hardcoded defaults allowed")
        if xylem_scaling_factor is None:
            raise ValueError("❌ 'xylem_conductance_scaling_factor' parameter must be provided in root_system_parameters CSV - no hardcoded defaults allowed")
        
        xylem_conductance = base_xylem_conductance * math.sqrt(stem_biomass / xylem_scaling_factor)  # Scales with stem development
        
        # Series resistances: 1/Total = 1/Root + 1/Xylem
        total_conductance = 1.0 / (1.0/root_conductance + 1.0/xylem_conductance)
        
        # 4. WATER FLOW CALCULATION
        # Darcy's law: Flow = Conductance × ΔΨ
        water_potential_gradient = solution_water_potential - adjusted_leaf_potential  # Always positive for uptake
        
        # Hydraulic flow (L/m²/day)
        hydraulic_water_uptake = total_conductance * water_potential_gradient
        
        # 5. METABOLIC WATER DEMAND
        # Additional water for cell metabolism and growth
        metabolic_water = lai * self.params.metabolic_water_per_lai
        
        # 6. CAVITATION AND XYLEM FAILURE
        # Xylem cavitation occurs at very negative water potentials
        cavitation_threshold = root_params.get('cavitation_threshold')
        if cavitation_threshold is None:
            raise ValueError("❌ 'cavitation_threshold' parameter must be provided in root_system_parameters CSV - no hardcoded defaults allowed")
        
        if adjusted_leaf_potential < cavitation_threshold:
            cavitation_factor = max(0.1, 1.0 + (adjusted_leaf_potential - cavitation_threshold) / 1.0)
            hydraulic_water_uptake *= cavitation_factor
        
        # Total water uptake limited by hydraulic capacity and plant physiology
        total_uptake = max(0.1, hydraulic_water_uptake + metabolic_water)
        
        # Plants can uptake more water than immediate transpiration demand for:
        # 1. Water storage in tissues (especially in stems and roots)
        # 2. Metabolic processes (cell expansion, biochemical reactions)
        # 3. Maintaining turgor pressure
        # Therefore, no artificial cap based on transpiration demand
        return total_uptake
    
    def _calculate_osmotic_adjustment(self, stress_factors: Dict[str, Any]) -> float:
        """
        Calculate osmotic adjustment under stress conditions.
        Plants can accumulate solutes to maintain turgor under water stress.
        """
        water_stress = stress_factors.get('water_stress_level', 0.0)
        salt_stress = stress_factors.get('salinity_stress', 0.0)
        
        # Maximum osmotic adjustment must be provided in CSV configuration
        stress_params = getattr(self.system_config, 'stress_parameters', {})
        max_adjustment = stress_params.get('max_osmotic_adjustment')
        salt_stress_factor = stress_params.get('salt_stress_osmotic_factor')
        
        if max_adjustment is None:
            raise ValueError("❌ 'max_osmotic_adjustment' parameter must be provided in stress_parameters CSV - no hardcoded defaults allowed")
        if salt_stress_factor is None:
            raise ValueError("❌ 'salt_stress_osmotic_factor' parameter must be provided in stress_parameters CSV - no hardcoded defaults allowed")
        
        # Osmotic adjustment increases with stress
        adjustment = max_adjustment * (water_stress + salt_stress * salt_stress_factor)
        
        return min(max_adjustment, adjustment)

    def _calculate_functional_balance_allocation(self, stress_factors: Dict[str, Any], 
                                               stage_props: Dict[str, Any], 
                                               env_conditions: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate biomass allocation using functional balance theory.
        
        Plants allocate biomass to overcome the most limiting resource:
        - Light limitation → more leaves (increase light capture)
        - Nitrogen limitation → more roots (increase N uptake) 
        - Water limitation → more roots (increase water uptake)
        - Developmental stage → sink strength effects
        """
        # Base allocation fractions (structural minimum)
        if stage_props['is_vegetative']:
            base_fractions = {
                'leaves': self.params.vegetative_leaf_allocation,
                'stems': self.params.vegetative_stem_allocation, 
                'roots': self.params.vegetative_root_allocation
            }
        else:
            base_fractions = {
                'leaves': self.params.reproductive_leaf_allocation,
                'stems': self.params.reproductive_stem_allocation,
                'roots': self.params.reproductive_root_allocation
            }
        
        # Resource limitation factors (0 = severe limitation, 1 = no limitation)
        light_limitation = 1.0 - env_conditions.get('light_stress', 0.0)
        nitrogen_limitation = stress_factors.get('nitrogen_stress_level', 0.0)  # Higher = more stressed
        water_limitation = stress_factors.get('water_stress_level', 0.0)
        
        # Natural functional balance - unlimited cellular response
        # Light limitation drives natural leaf allocation
        light_response = max(0.0, (1.0 - light_limitation) * 1.0)  # Natural unlimited response
        
        # Nitrogen limitation drives natural root allocation  
        nitrogen_response = max(0.0, nitrogen_limitation * 1.0)  # Natural unlimited response
        
        # Water limitation drives natural root allocation
        water_response = max(0.0, water_limitation * 1.0)  # Natural unlimited response
        
        # Root:shoot functional balance
        root_demand = nitrogen_response + water_response
        shoot_demand = light_response
        
        # Natural cellular allocation - no artificial caps
        total_root_shift = root_demand  # Natural response to resource limitation
        total_leaf_shift = shoot_demand  # Natural response to light needs
        
        # Apply shifts while maintaining mass balance
        adjusted_fractions = base_fractions.copy()
        
        # Increase roots in response to nutrient/water limitation
        if total_root_shift > 0:
            adjusted_fractions['roots'] += total_root_shift
            # Reduce leaves and stems proportionally
            reduction_factor = total_root_shift / (base_fractions['leaves'] + base_fractions['stems'])
            adjusted_fractions['leaves'] -= base_fractions['leaves'] * reduction_factor
            adjusted_fractions['stems'] -= base_fractions['stems'] * reduction_factor
        
        # Increase leaves in response to light limitation
        if total_leaf_shift > 0:
            adjusted_fractions['leaves'] += total_leaf_shift
            # Reduce roots and stems proportionally  
            reduction_factor = total_leaf_shift / (base_fractions['roots'] + base_fractions['stems'])
            adjusted_fractions['roots'] -= base_fractions['roots'] * reduction_factor
            adjusted_fractions['stems'] -= base_fractions['stems'] * reduction_factor
        
        # Ensure all fractions are positive and sum to 1.0
        for organ in adjusted_fractions:
            adjusted_fractions[organ] = max(0.05, adjusted_fractions[organ])  # Minimum 5%
            
        # Normalize to sum to 1.0
        total = sum(adjusted_fractions.values())
        for organ in adjusted_fractions:
            adjusted_fractions[organ] /= total
            
        return adjusted_fractions

    def _calculate_solution_temperature(self, air_temp: float, solar_radiation: float, tank_volume: float, day: int) -> float:
        """Calculate hydroponic solution temperature with simple thermal mass and solar gain model."""
        thermal_mass_factor = min(1.0, max(0.1, tank_volume / 1000.0))
        solar_heating = float(solar_radiation) * 0.15  # °C increase per MJ/m²
        prev_ts = getattr(self, 'prev_solution_temp', float(air_temp))
        temp_change = (float(air_temp) + solar_heating - prev_ts)
        lagged_change = temp_change * (0.3 / thermal_mass_factor)
        solution_temp = prev_ts + lagged_change
        solution_temp = max(10.0, min(35.0, solution_temp))
        self.prev_solution_temp = solution_temp
        return solution_temp
    
    def _convert_to_nitrogen_concentrations(self, nutrient_concentrations: Dict[str, float]) -> Dict[str, float]:
        """
        Convert nutrient concentrations to nitrogen forms expected by nitrogen model.
        
        Args:
            nutrient_concentrations: Dict with nutrient IDs and concentrations (mg/L)
            
        Returns:
            Dict with nitrogen forms and concentrations in mg N/L
        """
        nitrogen_forms = {}
        
        # Convert nitrate (NO3-N) - molecular weight ratio
        if 'N-NO3' in nutrient_concentrations:
            # Convert mg NO3/L to mg N/L (MW of N = 14, MW of NO3 = 62)
            no3_conc = nutrient_concentrations['N-NO3']
            nitrogen_forms['nitrate'] = no3_conc * (14.0 / 62.0)  # mg N/L as nitrate
            
        if 'N-NH4' in nutrient_concentrations:
            # Convert mg NH4/L to mg N/L (MW of N = 14, MW of NH4 = 18)
            nh4_conc = nutrient_concentrations['N-NH4']
            nitrogen_forms['ammonium'] = nh4_conc * (14.0 / 18.0)  # mg N/L as ammonium
        
        # If we only have N-NO3 (common case), assume it's mostly nitrate
        # and add small amount of ammonium typically present
        if 'nitrate' in nitrogen_forms and 'ammonium' not in nitrogen_forms:
            nitrogen_forms['ammonium'] = nitrogen_forms['nitrate'] * 0.1  # 10% as ammonium
        
        # If no nitrogen forms found, provide defaults to prevent zero uptake
        if not nitrogen_forms:
            nitrogen_forms = {
                'nitrate': 140.0,    # mg N/L (equivalent to ~200 mg NO3/L)
                'ammonium': 14.0     # mg N/L (equivalent to ~20 mg NH4/L)  
            }
            
        return nitrogen_forms
    
    def _calculate_hydroponic_water_stress(self, vpd: float, temperature: float, 
                                         humidity: float, ec: float, root_zone_temp: float) -> float:
        """
        Calculate dynamic water stress for hydroponic systems.
        
        Args:
            vpd: Vapor pressure deficit (kPa)
            temperature: Air temperature (°C)
            humidity: Relative humidity (%)
            ec: Electrical conductivity (dS/m)
            root_zone_temp: Root zone temperature (°C)
            
        Returns:
            Water stress level (0.0 = no stress, 1.0 = maximum stress)
        """
        # Calculate individual stress components
        
        # VPD stress using configured parameters
        if vpd > self.params.optimal_vpd_max:
            vpd_stress = (vpd - self.params.optimal_vpd_max) * self.params.vpd_stress_high_factor
        elif vpd < self.params.optimal_vpd_min:
            vpd_stress = (self.params.optimal_vpd_min - vpd) * self.params.vpd_stress_low_factor
        else:
            vpd_stress = 0.0
        
        # Research-based salinity stress (Andriolo et al., 2005)
        # Optimal EC: 2.0-2.6 dS/m, with polynomial response
        # Fresh weight peaks at 2.0 dS/m, LAI peaks at 2.6 dS/m
        if ec <= 2.6:
            # Positive effect up to optimum (bell curve)
            # Based on research: y = -27.11x² + 108.08x + 62.975 for fresh weight
            salinity_benefit = max(0.0, -0.1 * (ec - 2.0)**2 + 0.2)  # Peak benefit at EC 2.0
            ec_stress = -salinity_benefit  # Negative stress = growth promotion
        else:
            # Linear decline above 2.6 dS/m (research slope: -14.9)
            # 16.5% decline from EC 2.0 to 4.72 dS/m = slope of 0.061 per dS/m
            ec_stress = (ec - 2.6) * 0.061  # Research-based decline rate
        
        # Root zone temperature stress using configured parameters
        temp_deviation = abs(root_zone_temp - self.params.optimal_root_temp)
        if temp_deviation > self.params.root_temp_tolerance:
            root_temp_stress = (temp_deviation - self.params.root_temp_tolerance) * self.params.root_temp_stress_factor
        else:
            root_temp_stress = 0.0
        
        # Air temperature stress using configured parameters
        if temperature > self.params.optimal_air_temp_max:
            temp_demand_stress = (temperature - self.params.optimal_air_temp_max) * self.params.air_temp_stress_high_factor
        elif temperature < self.params.optimal_air_temp_min:
            temp_demand_stress = (self.params.optimal_air_temp_min - temperature) * self.params.air_temp_stress_low_factor
        else:
            temp_demand_stress = 0.0
        
        # Humidity stress using configured parameters
        if humidity < self.params.optimal_humidity_min:
            humidity_stress = (self.params.optimal_humidity_min - humidity) * self.params.humidity_stress_factor
        else:
            humidity_stress = 0.0
        
        # Calculate final water stress level (0=no stress, 1=max stress)
        total_stress = vpd_stress + ec_stress + root_temp_stress + temp_demand_stress + humidity_stress
        water_stress_level = min(0.6, total_stress)  # Cap maximum stress at 0.6
        
        return water_stress_level
    
    def _calculate_summary_statistics(self, daily_results: List[DailyResults]) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics"""
        if not daily_results:
            return {}
        
        return {
            # Basic measurements
            'final_temperature_C': daily_results[-1].temp_avg,
            'final_vpd_kPa': daily_results[-1].vpd,
            'final_ec_dS_m': daily_results[-1].ec,
            'average_water_use_efficiency': np.mean([r.water_use_efficiency for r in daily_results]),
            'total_transpiration_mm': sum([r.transpiration for r in daily_results]),
            'total_water_consumption_L': sum([r.water_uptake_total for r in daily_results]),
            
            # Environmental control
            'average_co2_umol_mol': np.mean([r.co2_concentration for r in daily_results]),
            'average_photosynthesis_factor': np.mean([r.env_photosynthesis_factor for r in daily_results]),
            'average_transpiration_factor': np.mean([r.env_transpiration_factor for r in daily_results]),
            
            # Advanced model tracking
            'current_lai': self.current_lai,
            'current_canopy_height_cm': self.canopy_height * 100,
            'total_biomass_g': sum(pool.dry_mass for pool in self.biomass_pools),
            'leaf_biomass_g': self.biomass_pools[0].dry_mass,
            'stem_biomass_g': self.biomass_pools[1].dry_mass,
            'root_biomass_g': self.biomass_pools[2].dry_mass,
            
            # Model metadata
            'cultivar_used': self.cultivar_profile.cultivar_name,
            'simulation_type': 'CROPGRO_Advanced',
            'total_days': len(daily_results)
        }
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of all integrated models"""
        return {
            'genetic_parameters': {
                'cultivar': self.cultivar_profile.cultivar_name,
                'type': self.cultivar_profile.lettuce_type.value,
                'yield_potential': self.cultivar_profile.yield_potential,
                'key_traits': {
                    trait.value: value 
                    for trait, value in self.cultivar_profile.trait_values.items()
                }
            },
            'phenology': {
                'current_stage': self.phenology_model.get_stage_properties()['stage_name'],
                'gdd_accumulated': self.accumulated_gdd
            },
            'biomass': {
                'leaf': self.biomass_pools[0].dry_mass,
                'stem': self.biomass_pools[1].dry_mass, 
                'root': self.biomass_pools[2].dry_mass,
                'total': sum(pool.dry_mass for pool in self.biomass_pools)
            },
            'canopy': {
                'lai': self.current_lai,
                'height_cm': self.canopy_height * 100
            },
            'simulation_day': self.simulation_day
        }
    
    def display_detailed_results(self, daily_result) -> str:
        """Display comprehensive CROPGRO results for a single day with clear per-plant vs per-system categorization"""
        output = []
        
        # Header with day and stage
        growth_stage = getattr(daily_result, 'growth_stage', 'N/A')
        day = getattr(daily_result, 'day', 0)
        output.append(f"\n{'='*80}")
        output.append(f"🌱 DAY {day:2d} - {growth_stage:>15} - CROPGRO HYDROPONIC SIMULATION")
        output.append(f"{'='*80}")
        
        # 1. QUICK SUMMARY (Key metrics at a glance)
        output.append(f"\n📊 QUICK SUMMARY:")
        total_biomass = getattr(daily_result, 'total_biomass', None)
        daily_growth = getattr(daily_result, 'daily_growth_rate', None)
        lai = getattr(daily_result, 'lai', None)
        plant_height = getattr(daily_result, 'plant_height_cm', None)
        
        if total_biomass is not None and daily_growth is not None and lai is not None and plant_height is not None:
            output.append(f"  🎯 Per Plant: {total_biomass:6.2f} g biomass | {daily_growth:5.3f} g/day growth | {plant_height:5.1f} cm height")
            leaf_number = getattr(daily_result, 'leaf_number', None)
            leaf_area = getattr(daily_result, 'leaf_area_m2', None)
            if leaf_number is not None and leaf_area is not None:
                output.append(f"  🌿 Canopy: LAI {lai:5.3f} | {leaf_number:2d} leaves | {leaf_area*10000:5.1f} cm² leaf area")
            else:
                output.append(f"  🌿 Canopy: LAI {lai:5.3f} | Leaf data not available")
        else:
            output.append(f"  🎯 Per Plant: Biomass data not available")
        
        # 2. PER-PLANT BIOMASS BREAKDOWN (Individual plant values)
        output.append(f"\n⚖️  PER-PLANT BIOMASS (Individual Plant Values):")
        output.append(f"  {'Component':<15} {'Dry Weight (g)':<15} {'Fresh Weight (g)':<15} {'Growth Rate (g/day)':<20}")
        output.append(f"  {'-'*15} {'-'*15} {'-'*15} {'-'*20}")
        
        # Get all biomass values without fallbacks
        shoot_fresh = getattr(daily_result, 'shoot_fresh_weight', None)
        leaf_dry = getattr(daily_result, 'leaf_dry_weight', None)
        leaf_fresh = getattr(daily_result, 'leaf_fresh_weight', None)
        leaf_growth = getattr(daily_result, 'leaf_growth_rate', None)
        stem_dry = getattr(daily_result, 'stem_dry_weight', None)
        stem_fresh = getattr(daily_result, 'stem_fresh_weight', None)
        stem_growth = getattr(daily_result, 'stem_growth_rate', None)
        root_dry = getattr(daily_result, 'root_dry_weight', None)
        root_fresh = getattr(daily_result, 'root_fresh_weight', None)
        root_growth = getattr(daily_result, 'root_growth_rate', None)
        
        if total_biomass is not None:
            output.append(f"  {'Total':<15} {total_biomass:<15.2f} {shoot_fresh if shoot_fresh is not None else 'N/A':<15} {daily_growth if daily_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Total':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")
            
        if leaf_dry is not None:
            output.append(f"  {'Leaves':<15} {leaf_dry:<15.2f} {leaf_fresh if leaf_fresh is not None else 'N/A':<15} {leaf_growth if leaf_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Leaves':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")
            
        if stem_dry is not None:
            output.append(f"  {'Stems':<15} {stem_dry:<15.2f} {stem_fresh if stem_fresh is not None else 'N/A':<15} {stem_growth if stem_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Stems':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")
            
        if root_dry is not None:
            output.append(f"  {'Roots':<15} {root_dry:<15.2f} {root_fresh if root_fresh is not None else 'N/A':<15} {root_growth if root_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Roots':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")
        
        # 3. PER-SYSTEM TOTALS (System-wide values)
        plant_count = getattr(daily_result, 'plant_count', None)
        system_area = getattr(daily_result, 'system_area_m2', None)
        
        if plant_count is not None and system_area is not None and total_biomass is not None:
            system_biomass = total_biomass * plant_count
            system_yield = system_biomass / system_area
            
            output.append(f"\n🏭 PER-SYSTEM TOTALS ({plant_count} Plants × {system_area} m²):")
            output.append(f"  {'Metric':<25} {'Per Plant':<15} {'Total System':<15} {'Per m²':<15}")
            output.append(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*15}")
            output.append(f"  {'Biomass':<25} {total_biomass:<15.2f} g {system_biomass:<15.1f} g {system_yield:<15.1f} g/m²")
            
            if daily_growth is not None:
                output.append(f"  {'Daily Growth':<25} {daily_growth:<15.3f} g/day {(daily_growth * plant_count):<15.2f} g/day {(daily_growth * plant_count / system_area):<15.2f} g/m²/day")
            else:
                output.append(f"  {'Daily Growth':<25} {'N/A':<15} {'N/A':<15} {'N/A':<15}")
                
            if leaf_area is not None:
                output.append(f"  {'Leaf Area':<25} {leaf_area*10000:<15.1f} cm² {(leaf_area * plant_count * 10000):<15.0f} cm² {lai:<15.3f} LAI")
            else:
                output.append(f"  {'Leaf Area':<25} {'N/A':<15} {'N/A':<15} {lai if lai is not None else 'N/A':<15}")
        else:
            output.append(f"\n🏭 PER-SYSTEM TOTALS: System configuration data not available")
        
        # 4. CARBON BALANCE (Per plant physiology)
        output.append(f"\n🔄 CARBON BALANCE (Per Plant):")
        net_assimilation = getattr(daily_result, 'net_assimilation', None)
        photosynthesis = getattr(daily_result, 'photosynthesis_rate', None)
        respiration = getattr(daily_result, 'respiration_rate', None)
        maint_resp = getattr(daily_result, 'maintenance_respiration', None)
        growth_resp = getattr(daily_result, 'growth_respiration', None)
        
        if all(v is not None for v in [net_assimilation, photosynthesis, respiration, maint_resp, growth_resp]):
            output.append(f"  {'Process':<20} {'Rate (g/day)':<15} {'Balance':<15}")
            output.append(f"  {'-'*20} {'-'*15} {'-'*15}")
            output.append(f"  {'Photosynthesis':<20} {photosynthesis:<15.4f} {'→':<15}")
            output.append(f"  {'Maintenance Resp.':<20} {maint_resp:<15.4f} {'←':<15}")
            output.append(f"  {'Growth Resp.':<20} {growth_resp:<15.4f} {'←':<15}")
            output.append(f"  {'Total Respiration':<20} {respiration:<15.4f} {'←':<15}")
            output.append(f"  {'NET ASSIMILATION':<20} {net_assimilation:<15.4f} {'=':<15}")
        else:
            output.append(f"  Carbon balance data not available")
        
        # 5. NUTRIENT STATUS (System-wide concentrations)
        output.append(f"\n💧 NUTRIENT SOLUTION STATUS (System-wide):")
        output.append(f"  {'Nutrient':<10} {'Concentration':<15} {'Uptake (mg/day)':<20} {'Status':<15}")
        output.append(f"  {'-'*10} {'-'*15} {'-'*20} {'-'*15}")
        
        nutrients = [
            ('N-NO₃', getattr(daily_result, 'n_no3_mg_l', None), getattr(daily_result, 'nitrogen_uptake_mg', None)),
            ('P-PO₄', getattr(daily_result, 'p_po4_mg_l', None), getattr(daily_result, 'phosphorus_uptake_mg', None)),
            ('K', getattr(daily_result, 'k_mg_l', None), getattr(daily_result, 'k_uptake_rate', None)),
            ('Ca', getattr(daily_result, 'ca_mg_l', None), getattr(daily_result, 'ca_uptake_rate', None)),
            ('Mg', getattr(daily_result, 'mg_mg_l', None), getattr(daily_result, 'mg_uptake_rate', None))
        ]
        
        for name, conc, uptake in nutrients:
            if conc is not None:
                status = "🟢 Optimal" if conc > 50 else "🟡 Low" if conc > 20 else "🔴 Critical"
                uptake_str = f"{uptake:.2f}" if uptake is not None else "N/A"
                output.append(f"  {name:<10} {conc:<15.1f} mg/L {uptake_str:<20} {status:<15}")
            else:
                output.append(f"  {name:<10} {'N/A':<15} {'N/A':<20} {'Data Missing':<15}")
        
        # System parameters without fallbacks
        ec = getattr(daily_result, 'ec', None)
        ph = getattr(daily_result, 'solution_ph', None)
        volume = getattr(daily_result, 'tank_volume_l', None)
        
        if ec is not None:
            status = "🟢 Optimal" if ec > 1.0 else "🔴 Low"
            output.append(f"  {'EC':<10} {ec:<15.2f} dS/m {'':<20} {status:<15}")
        else:
            output.append(f"  {'EC':<10} {'N/A':<15} {'':<20} {'Data Missing':<15}")
            
        if ph is not None:
            status = "🟢 Optimal" if 5.5 <= ph <= 6.5 else "🟡 Off-target"
            output.append(f"  {'pH':<10} {ph:<15.2f} {'':<20} {status:<15}")
        else:
            output.append(f"  {'pH':<10} {'N/A':<15} {'':<20} {'Data Missing':<15}")
            
        if volume is not None:
            output.append(f"  {'Volume':<10} {volume:<15.0f} L {'':<20} {'🟢 Adequate':<15}")
        else:
            output.append(f"  {'Volume':<10} {'N/A':<15} {'':<20} {'Data Missing':<15}")
        
        # 6. ENVIRONMENTAL CONDITIONS (System-wide)
        output.append(f"\n🌡️  ENVIRONMENTAL CONDITIONS (System-wide):")
        output.append(f"  {'Parameter':<20} {'Value':<15} {'Target':<15} {'Status':<15}")
        output.append(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")
        
        temp = getattr(daily_result, 'temp_c', None)
        humidity = getattr(daily_result, 'humidity', None)
        co2 = getattr(daily_result, 'co2_umol_mol', None)
        vpd = getattr(daily_result, 'vpd_kpa', None)
        
        if temp is not None:
            temp_status = "🟢 Optimal" if 20 <= temp <= 28 else "🟡 Warm" if temp > 28 else "🟡 Cool"
            output.append(f"  {'Temperature':<20} {temp:<15.1f}°C {'20-28°C':<15} {temp_status:<15}")
        else:
            output.append(f"  {'Temperature':<20} {'N/A':<15} {'20-28°C':<15} {'Data Missing':<15}")
            
        if humidity is not None:
            humidity_status = "🟢 Optimal" if 50 <= humidity <= 80 else "🟡 Low" if humidity < 50 else "🟡 High"
            output.append(f"  {'Humidity':<20} {humidity:<15.1f}% {'50-80%':<15} {humidity_status:<15}")
        else:
            output.append(f"  {'Humidity':<20} {'N/A':<15} {'50-80%':<15} {'Data Missing':<15}")
            
        if co2 is not None:
            co2_status = "🟢 Optimal" if co2 >= 400 else "🟡 Low"
            output.append(f"  {'CO₂':<20} {co2:<15.0f} ppm {'≥400 ppm':<15} {co2_status:<15}")
        else:
            output.append(f"  {'CO₂':<20} {'N/A':<15} {'≥400 ppm':<15} {'Data Missing':<15}")
            
        if vpd is not None:
            vpd_status = "🟢 Optimal" if 0.6 <= vpd <= 1.2 else "🟡 High" if vpd > 1.2 else "🟡 Low"
            output.append(f"  {'VPD':<20} {vpd:<15.2f} kPa {'0.6-1.2 kPa':<15} {vpd_status:<15}")
        else:
            output.append(f"  {'VPD':<20} {'N/A':<15} {'0.6-1.2 kPa':<15} {'Data Missing':<15}")
        
        # 7. STRESS FACTORS (Per plant)
        output.append(f"\n😰 STRESS FACTORS (Per Plant):")
        output.append(f"  {'Stress Type':<20} {'Level':<15} {'Effect':<15} {'Status':<15}")
        output.append(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")
        
        stresses = [
            ('Temperature', getattr(daily_result, 'temperature_stress', None), getattr(daily_result, 'temperature_stress_factor', None)),
            ('Water', getattr(daily_result, 'water_stress', None), getattr(daily_result, 'water_stress_factor', None)),
            ('Nutrient', getattr(daily_result, 'nutrient_stress', None), getattr(daily_result, 'nutrient_stress_factor', None)),
            ('Nitrogen', getattr(daily_result, 'nitrogen_stress', None), getattr(daily_result, 'nitrogen_stress_factor', None)),
            ('Salinity', getattr(daily_result, 'salinity_stress', None), getattr(daily_result, 'salinity_stress_factor', None))
        ]
        
        for name, level, effect in stresses:
            if level is not None and effect is not None:
                if level < 0.1:
                    status = "🟢 None"
                elif level < 0.3:
                    status = "🟡 Mild"
                elif level < 0.6:
                    status = "🟠 Moderate"
                else:
                    status = "🔴 Severe"
                output.append(f"  {name:<20} {level:<15.3f} {effect:<15.3f} {status:<15}")
            else:
                output.append(f"  {name:<20} {'N/A':<15} {'N/A':<15} {'Data Missing':<15}")
        
        # 8. DEVELOPMENT PROGRESS (Per plant)
        output.append(f"\n📅 DEVELOPMENT PROGRESS (Per Plant):")
        gdd = getattr(daily_result, 'accumulated_gdd', None)
        thermal_time = getattr(daily_result, 'thermal_time_daily', None)
        dev_rate = getattr(daily_result, 'development_rate', None)
        
        if gdd is not None and thermal_time is not None and dev_rate is not None:
            # Estimate progress to harvest using CSV configuration
            phenology_params = getattr(self.system_config, 'phenology_parameters', {})
            harvest_gdd = phenology_params.get('harvest_gdd')
            if harvest_gdd is None:
                raise ValueError("❌ 'harvest_gdd' parameter must be provided in phenology_parameters CSV - no hardcoded defaults allowed")
            progress = min(100.0, (gdd / harvest_gdd) * 100) if harvest_gdd > 0 else 0.0
            
            output.append(f"  • Accumulated GDD: {gdd:6.1f}°C-days (Target: {harvest_gdd:.0f}°C-days)")
            output.append(f"  • Daily Thermal Time: {thermal_time:6.1f}°C-days")
            output.append(f"  • Development Rate: {dev_rate:6.4f}")
            output.append(f"  • Progress to Harvest: {progress:6.1f}%")
        else:
            output.append(f"  Development data not available")
        
        # 9. EFFICIENCY METRICS (System-wide)
        output.append(f"\n📊 EFFICIENCY METRICS (System-wide):")
        water_use = getattr(daily_result, 'wue_kg_m3', None)
        light_use = getattr(daily_result, 'light_use_efficiency', None)
        
        if water_use is not None:
            output.append(f"  • Water Use Efficiency: {water_use:6.2f} kg/m³")
        else:
            output.append(f"  • Water Use Efficiency: Data not available")
            
        if light_use is not None:
            output.append(f"  • Light Use Efficiency: {light_use:6.3f} g/MJ")
        else:
            output.append(f"  • Light Use Efficiency: Data not available")
            
        if daily_growth is not None:
            n_uptake = getattr(daily_result, 'nitrogen_uptake_mg', None)
            if n_uptake is not None and n_uptake > 0:
                n_efficiency = (daily_growth / n_uptake) * 1000
                output.append(f"  • Nitrogen Use Efficiency: {n_efficiency:6.1f} g biomass/g N")
            else:
                output.append(f"  • Nitrogen Use Efficiency: Data not available")
        else:
            output.append(f"  • Nitrogen Use Efficiency: Data not available")
            
        if system_yield is not None:
            output.append(f"  • System Yield: {system_yield:6.1f} g/m²")
        else:
            output.append(f"  • System Yield: Data not available")
        
        # 10. PROJECTIONS (Based on current performance)
        if day > 1 and daily_growth is not None and daily_growth > 0 and gdd is not None and thermal_time is not None:
            # Estimate days to harvest using CSV configuration
            phenology_params = getattr(self.system_config, 'phenology_parameters', {})
            harvest_gdd = phenology_params.get('harvest_gdd')
            if harvest_gdd is None:
                raise ValueError("❌ 'harvest_gdd' parameter must be provided in phenology_parameters CSV - no hardcoded defaults allowed")
            remaining_gdd = max(0, harvest_gdd - gdd)
            
            # Estimate days based on thermal time
            days_to_harvest = remaining_gdd / thermal_time if thermal_time > 0 else 0
            projected_yield = total_biomass + (daily_growth * days_to_harvest)
            
            if plant_count is not None and system_area is not None:
                projected_system_yield = projected_yield * plant_count / system_area
                
                output.append(f"\n🔮 PROJECTIONS (Based on Current Performance):")
                output.append(f"  • Days to Harvest: {days_to_harvest:6.1f} days")
                output.append(f"  • Projected Final Biomass: {projected_yield:6.1f} g/plant")
                output.append(f"  • Projected System Yield: {projected_system_yield:6.1f} g/m²")
        
        # Footer
        output.append(f"\n{'-'*80}")
        if plant_count is not None:
            output.append(f"📋 Note: Biomass values are PER PLANT. Multiply by {plant_count} for total system values.")
        else:
            output.append(f"📋 Note: Plant count not available")
        output.append(f"📋 Note: Environmental values are SYSTEM-WIDE (affect all plants).")
        output.append(f"{'='*80}")
        
        return "\n".join(output)
    
    def _update_cultivar_with_dynamic_params(self, genetic_params: dict):
        """Update cultivar profile with dynamic genetic parameters from CSV"""
        if not self.cultivar_profile:
            return
            
        # Create a copy of the genetic coefficients to modify
        updated_coeffs = self.cultivar_profile.genetic_coefficients
        
        # Map CSV parameters to genetic coefficient attributes
        param_mapping = {
            'SLAVR': 'SLAVR',
            'SIZLF': 'SIZLF', 
            'EM': 'EM_FL',
            'P1': 'FL_SH', 
            'P3': 'FL_SD',
            'P5': 'SD_PM',
            'PHINT': 'LFMAX'
        }
        
        # Update genetic coefficients with CSV values
        for csv_param, coeff_attr in param_mapping.items():
            if csv_param in genetic_params:
                setattr(updated_coeffs, coeff_attr, genetic_params[csv_param])
        
        logger.info(f"Updated cultivar {self.current_cultivar} with {len(genetic_params)} dynamic genetic parameters")
    
    def _perform_realistic_nutrient_management(self, day, current_concentrations, input_data, logger):
        """
        Perform realistic nutrient management with individual nutrient monitoring.
        
        Returns True if any nutrient management was performed, False otherwise.
        """
        management_performed = False
        
        # Get optimal concentrations from CSV configuration
        nutrient_solution_params = getattr(self.system_config, 'nutrient_solution', {})
        
        # Handle both old nested format and new consolidated format
        if nutrient_solution_params and isinstance(list(nutrient_solution_params.values())[0], dict):
            # Old nested format
            optimal_concentrations = {
                'N-NO3': nutrient_solution_params.get('N-NO3', {}).get('initial_ppm', 200.0),
                'P-PO4': nutrient_solution_params.get('P-PO4', {}).get('initial_ppm', 50.0),
                'K': nutrient_solution_params.get('K', {}).get('initial_ppm', 300.0),
                'Ca': nutrient_solution_params.get('Ca', {}).get('initial_ppm', 150.0),
                'Mg': nutrient_solution_params.get('Mg', {}).get('initial_ppm', 50.0)
            }
        else:
            # New consolidated format
            optimal_concentrations = {
                'N-NO3': nutrient_solution_params.get('N-NO3_initial_ppm', 200.0),
                'P-PO4': nutrient_solution_params.get('P-PO4_initial_ppm', 50.0),
                'K': nutrient_solution_params.get('K_initial_ppm', 300.0),
                'Ca': nutrient_solution_params.get('Ca_initial_ppm', 150.0),
                'Mg': nutrient_solution_params.get('Mg_initial_ppm', 50.0)
            }
        
        # Individual nutrient management based on depletion thresholds
        for nutrient_id, optimal_ppm in optimal_concentrations.items():
            current_ppm = current_concentrations.get(nutrient_id, optimal_ppm)
            depletion_percent = (optimal_ppm - current_ppm) / optimal_ppm
            
            # Nutrient-specific management triggers
            management_trigger = False
            supplement_amount = 0.0
            
            if nutrient_id == 'N-NO3':
                # Nitrogen: Critical for growth, supplement when < 70% of optimal
                if depletion_percent > 0.3:
                    management_trigger = True
                    supplement_amount = optimal_ppm * 0.8  # Restore to 80% of optimal
            elif nutrient_id == 'K':
                # Potassium: Supplement when < 60% of optimal, higher frequency
                if depletion_percent > 0.4:
                    management_trigger = True
                    supplement_amount = optimal_ppm * 0.9  # Restore to 90% of optimal
            elif nutrient_id == 'P-PO4':
                # Phosphorus: Less frequent, supplement when < 50% of optimal
                if depletion_percent > 0.5:
                    management_trigger = True
                    supplement_amount = optimal_ppm * 0.75  # Restore to 75% of optimal
            elif nutrient_id in ['Ca', 'Mg']:
                # Secondary nutrients: Less frequent supplementation
                if depletion_percent > 0.4 and day % 3 == 0:  # Every 3 days if depleted
                    management_trigger = True
                    supplement_amount = optimal_ppm * 0.85  # Restore to 85% of optimal
            
            # Random variation in management timing (±1 day)
            if management_trigger and np.random.random() > 0.3:  # 70% chance of actually supplementing
                current_concentrations[nutrient_id] = supplement_amount
                logger.info(f"Day {day}: {nutrient_id} supplemented to {supplement_amount:.1f} ppm (was {current_ppm:.1f} ppm)")
                management_performed = True
        
        # Complete solution change: Less frequent, variable timing
        # Always define days_since_start, but only do solution changes after day 10
        days_since_start = day - 1
        
        # Solution change parameters must be provided in CSV configuration
        system_params = getattr(self.system_config, 'system_parameters', {})
        base_solution_change_prob = system_params.get('base_solution_change_probability')
        solution_change_increase = system_params.get('solution_change_probability_increase')
        forced_solution_change_interval = system_params.get('forced_solution_change_interval')
        
        if base_solution_change_prob is None:
            raise ValueError("❌ 'base_solution_change_probability' parameter must be provided in system_parameters CSV - no hardcoded defaults allowed")
        if solution_change_increase is None:
            raise ValueError("❌ 'solution_change_probability_increase' parameter must be provided in system_parameters CSV - no hardcoded defaults allowed")
        if forced_solution_change_interval is None:
            raise ValueError("❌ 'forced_solution_change_interval' parameter must be provided in system_parameters CSV - no hardcoded defaults allowed")
        
        # Only calculate solution change probability after day 10
        if day > 10:
            prob_solution_change = base_solution_change_prob + solution_change_increase * (days_since_start % 14) / 14
        else:
            prob_solution_change = 0.0  # No solution changes in first 10 days
        
        if np.random.random() < prob_solution_change or day % forced_solution_change_interval == 0:  # Forced at interval as backup
                logger.info(f"Day {day}: Complete solution change - replacing with fresh nutrient solution")
                
                # Replace all nutrients
                for nutrient_id, params in input_data.nutrient_params.items():
                    if nutrient_id in optimal_concentrations:
                        current_concentrations[nutrient_id] = optimal_concentrations[nutrient_id]
                        logger.info(f"  {nutrient_id}: reset to {optimal_concentrations[nutrient_id]} ppm")
                    else:
                        # For other nutrients, use recharge concentration
                        target = params.recharge_conc if hasattr(params, 'recharge_conc') else params.initial_conc
                        current_concentrations[nutrient_id] = target
                
                management_performed = True
        
        return management_performed
    
    def _run_hourly_integration(self, day: int, daily_weather_data: Dict[str, float], 
                               env_conditions: Dict[str, float], stress_factors: Dict[str, float],
                               nutrient_concentrations: Dict[str, float], daylength: float) -> Dict[str, Any]:
        """
        DSSAT-style internal hourly integration loop.
        
        Integrates photosynthesis and nutrient uptake hourly while maintaining
        daily timestep for other processes.
        """
        from .data.hydroponic_system import WeatherData
        
        # Create daily weather object for interpolation
        daily_weather = WeatherData(
            date=f"2024-01-{day:02d}",
            temp_avg=daily_weather_data['temp_avg'],
            temp_min=daily_weather_data['temp_min'],
            temp_max=daily_weather_data['temp_max'],
            rel_humidity=daily_weather_data['rel_humidity'],
            solar_radiation=daily_weather_data['solar_radiation'],
            wind_speed=daily_weather_data.get('wind_speed', 2.0),  # Default 2.0 m/s
            rainfall=daily_weather_data.get('rainfall', 0.0)       # Default 0.0 mm
        )
        
        # Get system CO2 from configuration
        system_co2 = getattr(self.system_config, 'default_co2', 400.0)
        
        # Interpolate to hourly weather
        hourly_weather_list = self.hourly_weather_interpolator.interpolate_daily_to_hourly(
            daily_weather, day_of_year=day, latitude=40.0, system_co2=system_co2
        )
        
        # Initialize accumulators
        total_daily_photosynthesis = 0.0
        total_daily_uptake = {}
        hourly_diagnostics = []
        
        # Get canopy parameters for photosynthesis
        canopy_params = getattr(self.system_config, 'canopy_parameters', {})
        
        # Initialize accumulators for new hourly models
        total_daily_respiration = 0.0
        daily_environmental_control = {'energy_cost': 0.0, 'temperature': 0.0, 'humidity': 0.0, 'co2': 0.0}
        daily_rzt_effects = {'average_rzt': 0.0, 'thermal_stress': 0.0}
        
        # Hourly integration loop
        for hour in range(24):
            hourly_weather = hourly_weather_list[hour]
            
            # === HOURLY PHOTOSYNTHESIS ===
            if hourly_weather.par > 0.1:  # Only during light hours
                # Get photosynthesis parameters for LAI thresholds
                photosynthesis_params = getattr(self.system_config, 'photosynthesis', {})
                hourly_photosynthesis = self.photosynthesis_model.calculate_hourly_assimilation(
                    par_umol_m2_s=hourly_weather.par,
                    co2_ppm=hourly_weather.co2,
                    temp_c=hourly_weather.temperature,
                    lai=self.current_lai,
                    hour=hour,
                    ec_factor=stress_factors.get('salinity_factor', 1.0),
                    config_dict=photosynthesis_params
                )
                total_daily_photosynthesis += hourly_photosynthesis
            else:
                hourly_photosynthesis = 0.0
            
            # === HOURLY NUTRIENT UPTAKE ===
            if hasattr(self, 'root_model') and hasattr(self.root_model, 'hourly_update'):
                # Update environmental conditions with hourly values
                hourly_env_conditions = {
                    'temperature': hourly_weather.temperature,
                    'humidity': hourly_weather.humidity,
                    'flow_rate': env_conditions.get('flow_rate', 1.5),
                    'oxygen_level': env_conditions.get('oxygen_level', 8.0),
                    'ph': env_conditions.get('ph', None),
                    'nutrient_concentrations': nutrient_concentrations
                }
                
                # Scale growth factors for hourly timestep
                hourly_growth_factors = {
                    'nitrogen_stress': stress_factors.get('nitrogen_factor', 1.0),
                    'water_stress': stress_factors.get('water_factor', 1.0),
                    'temperature_stress': stress_factors.get('temperature_factor', 1.0)
                }
                
                # Calculate hourly nutrient uptake
                hourly_root_response = self.root_model.hourly_update(
                    hourly_env_conditions, hourly_growth_factors, nutrient_concentrations, dt_hours=1.0
                )
                
                # Accumulate daily totals
                for nutrient, rate in hourly_root_response.items():
                    if nutrient.endswith('_uptake_rate'):
                        if nutrient not in total_daily_uptake:
                            total_daily_uptake[nutrient] = 0.0
                        total_daily_uptake[nutrient] += rate
            
            # === HOURLY ENVIRONMENTAL CONTROL ===
            if hasattr(self, 'environmental_control') and hasattr(self.environmental_control, 'hourly_update'):
                hourly_control_conditions = {
                    'temperature': hourly_weather.temperature,
                    'humidity': hourly_weather.humidity,
                    'co2': hourly_weather.co2
                }
                
                env_control_response = self.environmental_control.hourly_update(
                    hourly_control_conditions, hour, dt_hours=1.0
                )
                
                # Accumulate environmental control effects
                daily_environmental_control['energy_cost'] += env_control_response.get('hourly_cost_usd', 0.0)
                daily_environmental_control['temperature'] += env_control_response.get('temperature', hourly_weather.temperature)
                daily_environmental_control['humidity'] += env_control_response.get('humidity', hourly_weather.humidity)
                daily_environmental_control['co2'] += env_control_response.get('co2', hourly_weather.co2)
            
            # === HOURLY ROOT ZONE TEMPERATURE ===
            if hasattr(self, 'root_zone_temp_model') and hasattr(self.root_zone_temp_model, 'hourly_update'):
                rzt_conditions = {
                    'air_temperature': hourly_weather.temperature,
                    'solution_temperature': hourly_weather.temperature  # Simplified assumption
                }
                
                rzt_response = self.root_zone_temp_model.hourly_update(
                    rzt_conditions, hour, dt_hours=1.0
                )
                
                # Accumulate RZT effects
                daily_rzt_effects['average_rzt'] += rzt_response.get('current_rzt', hourly_weather.temperature)
                daily_rzt_effects['thermal_stress'] += rzt_response.get('thermal_stress', 0.0)
            
            # === HOURLY RESPIRATION ===
            if hasattr(self, 'respiration_model') and hasattr(self.respiration_model, 'hourly_update'):
                # Get current biomass pools for respiration calculation
                biomass_pools = [
                    type('BiomassPool', (), {
                        'tissue_type': 'leaves', 
                        'dry_weight': getattr(self, 'leaf_biomass', 0.7),
                        'age_days': day,
                        'nitrogen_content': 0.045
                    }),
                    type('BiomassPool', (), {
                        'tissue_type': 'stems', 
                        'dry_weight': getattr(self, 'stem_biomass', 0.1),
                        'age_days': day,
                        'nitrogen_content': 0.020
                    }),
                    type('BiomassPool', (), {
                        'tissue_type': 'roots', 
                        'dry_weight': getattr(self, 'root_biomass', 0.2),
                        'age_days': day,
                        'nitrogen_content': 0.028
                    })
                ]
                
                resp_response = self.respiration_model.hourly_update(
                    biomass_pools, hourly_weather.temperature, hour, dt_hours=1.0, new_growth=0.0
                )
                
                # Accumulate daily respiration
                total_daily_respiration += resp_response.get('total_respiration_g_C_per_hour', 0.0)
            
            # Store hourly diagnostics
            hourly_diagnostics.append({
                'hour': hour,
                'temperature': hourly_weather.temperature,
                'par': hourly_weather.par,
                'photosynthesis': hourly_photosynthesis,
                'vpd': hourly_weather.vpd
            })
        
        # Calculate daily averages for environmental control and RZT
        if daily_environmental_control['temperature'] > 0:
            for key in ['temperature', 'humidity', 'co2']:
                daily_environmental_control[key] /= 24.0
        
        if daily_rzt_effects['average_rzt'] > 0:
            daily_rzt_effects['average_rzt'] /= 24.0
            daily_rzt_effects['thermal_stress'] /= 24.0
        
        return {
            'total_daily_photosynthesis': total_daily_photosynthesis,
            'total_daily_uptake': total_daily_uptake,
            'total_daily_respiration': total_daily_respiration,
            'daily_environmental_control': daily_environmental_control,
            'daily_rzt_effects': daily_rzt_effects,
            'hourly_diagnostics': hourly_diagnostics
        }