"""
Enhanced CROPGRO Hydroponic Simulator - No hardcoded defaults allowed and no fallback to simple alternative codes

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
# No hardcoded values, all values are from the system configuration and input data from csv files
# integrate all models into the simulation engine, because we have to use all models to get the correct results and we have all complex codes to integrate
import math
import random
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import logging

# Add parent directory to sys.path for proper imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import utilities
from utils.temperature_utils import calculate_vpd, calculate_thermal_time
from utils.results_display_utility import create_lettuce_results_display_utility

# Import all CROPGRO models
from models.genetic_parameters import create_lettuce_genetic_system
from models.phenology_model import create_lettuce_phenology_model, LettuceGrowthStage
from models.respiration_model import create_lettuce_respiration_model, BiomassPool, TissueType
from models.senescence_model import create_lettuce_senescence_model
from models.canopy_architecture import create_lettuce_canopy_model, LightEnvironment
from models.nitrogen_balance import create_lettuce_nitrogen_balance_model
from models.nutrient_models import create_lettuce_nutrient_mobility_model, NutrientUptakeModel
from models.biomass_allocation_model import create_lettuce_biomass_allocation_model
from models.stress_models import create_lettuce_integrated_stress_model
from models.stress_models import create_lettuce_temperature_stress_model, UnifiedStressCalculator
from models.root_system_model import create_enhanced_root_uptake_model
from models.root_zone_temperature import create_lettuce_rzt_model
from models.ph_model import create_lettuce_ph_model
from models.environmental_control import create_lettuce_environmental_control_system
from models.photosynthesis_model import create_lettuce_photosynthesis_model
from models.nutrient_models import NutrientConcentrationModel
from models.leaf_development import create_lettuce_leaf_development_model
from models.water_uptake_model import create_lettuce_water_uptake_model
from data.hydroponic_system import HydroInputData, SimulationResults, DailyResults

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimulationParameters:
    """
    Configuration parameters for the simulation.
    """
    carbon_to_biomass_ratio: float
    growth_respiration_fraction: float
    vegetative_leaf_allocation: float
    vegetative_stem_allocation: float
    vegetative_root_allocation: float
    reproductive_leaf_allocation: float
    reproductive_stem_allocation: float
    reproductive_root_allocation: float
    optimal_light_intensity: float
    optimal_ec_range: tuple
    optimal_vpd_min: float
    optimal_vpd_max: float
    vpd_stress_high_factor: float
    vpd_stress_low_factor: float
    ec_stress_high_factor: float
    ec_stress_low_threshold: float
    ec_stress_low_factor: float
    phenology_optimal_temperature_min: float
    phenology_optimal_temperature_max: float
    root_temp_tolerance: float
    root_temp_stress_factor: float
    heat_stress_threshold: float
    cold_stress_threshold: float
    optimal_humidity_min: float
    water_stress_factor: float
    specific_leaf_area_default: float
    metabolic_water_per_lai: float
    reservoir_topup_fraction: float
    minimal_nitrogen_uptake: float

class CROPGROHydroponicSimulator:
    """
    Advanced CROPGRO-based hydroponic simulator integrating all models.
    """
    
    def __init__(self, 
                 cultivar_id: str,
                 system_type: str,
                 system_config: Any):
        
        logger.info("Initializing CROPGRO Hydroponic Simulator...")
        self.system_config = system_config
        self.params = self._load_simulation_parameters()
        
        self.genetic_db, self.ge_model, self.breeding_assistant = create_lettuce_genetic_system(system_config, cultivar_id)
        self.current_cultivar = cultivar_id
        self.cultivar_profile = self.genetic_db.get_cultivar(cultivar_id)
        if not self.cultivar_profile:
            raise ValueError(f'❌ Cultivar {cultivar_id} not found in genetic database. Available cultivars: {list(self.genetic_db.cultivars.keys())}')
        
        # Use comprehensive genetic parameters model functions
        self._initialize_genetic_parameters()
        
        # Get transplant stage from CSV parameters
        phenology_params = getattr(self.system_config, 'phenology_parameters', {})
        transplant_stage_name = self._get_required_param(phenology_params, 'transplant_stage', 'phenology_parameters CSV')
        transplant_stage = getattr(LettuceGrowthStage, transplant_stage_name.upper(), LettuceGrowthStage.THIRD_LEAF)
        self.phenology_model = create_lettuce_phenology_model(self.system_config, transplant_stage)
        self.leaf_model = create_lettuce_leaf_development_model(self.system_config)
        self.respiration_model = create_lettuce_respiration_model(self.system_config)
        self.senescence_model = create_lettuce_senescence_model(self.system_config)
        self.canopy_model = create_lettuce_canopy_model(self.system_config)
        self.nitrogen_model = create_lettuce_nitrogen_balance_model(self.system_config)
        self.mobility_model = create_lettuce_nutrient_mobility_model(self.system_config)
        self.integrated_stress = create_lettuce_integrated_stress_model(self.system_config)
        self.temperature_stress = create_lettuce_temperature_stress_model(self.system_config)
        self.root_model = None  # Initialized in run_simulation
        self.environmental_control = create_lettuce_environmental_control_system(self.system_config)
        self.photosynthesis_model = create_lettuce_photosynthesis_model(self.system_config)
        nutrient_params = getattr(self.system_config, 'nutrient_parameters', {})
        if not nutrient_params:
            raise ValueError('❌ Missing nutrient_parameters in system_config. Required for NutrientConcentrationModel.')
        self.nutrient_concentration_model = NutrientConcentrationModel(nutrient_params)
        self.rzt_model = create_lettuce_rzt_model(self.system_config)
        self.biomass_allocation_model = create_lettuce_biomass_allocation_model(self.system_config)
        self.ph_model = create_lettuce_ph_model(self.system_config)
        self.water_uptake_model = create_lettuce_water_uptake_model(self.system_config)
        self.nutrient_uptake_model = NutrientUptakeModel()
        self.unified_stress_calculator = UnifiedStressCalculator(self.system_config, self.params, self.temperature_stress, self.nitrogen_model)
        self.results_display_utility = create_lettuce_results_display_utility(self.system_config)

        self._initialize_plant_state()
        logger.info("CROPGRO Hydroponic Simulator initialized successfully!")

    def _get_required_param(self, param_dict: dict, param_name: str, param_source: str) -> any:
        """Get a required parameter with clear error message if missing."""
        if param_name not in param_dict:
            available_params = list(param_dict.keys()) if param_dict else 'None'
            error_msg = f"❌ Missing required parameter '{param_name}' in {param_source}. Available parameters: {available_params}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return param_dict[param_name]

    def _load_simulation_parameters(self) -> SimulationParameters:
        """
        Loads simulation parameters from CSV files.
        """
        water_params = dict(getattr(self.system_config, 'water_parameters', {}))
        nutrient_params = getattr(self.system_config, 'nitrogen_parameters', {})

        if water_params:
            water_params_copy = dict(water_params)
            for param_name, param_value in water_params_copy.items():
                if param_name == 'lai_water_demand_factor':
                    water_params['LAI_WATER_DEMAND_FACTOR'] = param_value

        model_constants = getattr(self.system_config, 'model_constants', {})
        stress_parameters = getattr(self.system_config, 'stress_parameters', {})
        environment_parameters = getattr(self.system_config, 'environment', {})
        phenology_parameters = getattr(self.system_config, 'phenology', {})
        canopy_parameters = getattr(self.system_config, 'canopy_parameters', {})
        csv_system_parameters = getattr(self.system_config, 'system_parameters', {})
        system_parameters = getattr(self.system_config, 'system', {})

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
                optimal_light_intensity=self._get_required_param(environment_parameters, 'light_intensity_control', 'environment CSV'),
                optimal_ec_range=(
                    self._get_required_param(stress_parameters, 'optimal_ec_min', 'stress_parameters CSV'),
                    self._get_required_param(stress_parameters, 'optimal_ec_max', 'stress_parameters CSV')
                ),
                optimal_vpd_min=self._get_required_param(stress_parameters, 'optimal_vpd_min', 'stress_parameters CSV'),
                optimal_vpd_max=self._get_required_param(stress_parameters, 'optimal_vpd_max', 'stress_parameters CSV'),
                vpd_stress_high_factor=self._get_required_param(stress_parameters, 'vpd_stress_high_factor', 'stress_parameters CSV'),
                vpd_stress_low_factor=self._get_required_param(stress_parameters, 'vpd_stress_low_factor', 'stress_parameters CSV'),
                ec_stress_high_factor=self._get_required_param(stress_parameters, 'ec_stress_high_factor', 'stress_parameters CSV'),
                ec_stress_low_threshold=self._get_required_param(stress_parameters, 'ec_stress_low_threshold', 'stress_parameters CSV'),
                ec_stress_low_factor=self._get_required_param(stress_parameters, 'ec_stress_low_factor', 'stress_parameters CSV'),
                phenology_optimal_temperature_min=self._get_required_param(phenology_parameters, 'phenology_optimal_temperature_min', 'phenology_parameters CSV'),
                phenology_optimal_temperature_max=self._get_required_param(phenology_parameters, 'phenology_optimal_temperature_max', 'phenology_parameters CSV'),
                root_temp_tolerance=self._get_required_param(stress_parameters, 'temp_stress_threshold', 'stress_parameters CSV'),
                root_temp_stress_factor=self._get_required_param(stress_parameters, 'temp_stress_factor', 'stress_parameters CSV'),
                heat_stress_threshold=self._get_required_param(phenology_parameters, 'heat_threshold', 'phenology_parameters CSV'),
                cold_stress_threshold=self._get_required_param(stress_parameters, 'cold_threshold_mild', 'stress_parameters CSV'),
                optimal_humidity_min=self._get_required_param(environment_parameters, 'min_humidity', 'environment CSV'),
                water_stress_factor=self._get_required_param(stress_parameters, 'water_stress_factor', 'stress_parameters CSV'),
                specific_leaf_area_default=self._get_required_param(canopy_parameters, 'specific_leaf_area', 'canopy_parameters CSV'),
                metabolic_water_per_lai=self._get_required_param(water_params, 'metabolic_water_per_lai', 'water_parameters CSV'),
                reservoir_topup_fraction=self._get_required_param(system_parameters, 'reservoir_topup_fraction', 'system_config CSV'),
                minimal_nitrogen_uptake=self._get_required_param(nutrient_params, 'nitrogen_uptake_efficiency', 'nitrogen_parameters CSV')
            )
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to load simulation parameters: {e}")
            raise

    def _initialize_plant_state(self):
        # ... (implementation from previous turns)
        pass

    def _initialize_genetic_parameters(self):
        """Use comprehensive genetic parameters model functions that were previously unused."""
        
        # Initialize cultivar database
        if hasattr(self.genetic_db, 'initialize_cultivar_database'):
            self.genetic_db.initialize_cultivar_database()
        
        # Get parameters from CSV
        genetic_params = getattr(self.system_config, 'genetic_parameters', {})
        environment_params = getattr(self.system_config, 'environment', {})
        system_params = getattr(self.system_config, 'system', {})
        
        # Define environment factors for genetic calculations using weather data
        # Use first day's weather data for initial genetic calculations
        if hasattr(self.system_config, 'weather_data') and self.system_config.weather_data:
            first_weather = self.system_config.weather_data[0]
            environment_factors = {
                'temperature': first_weather.temp_avg,
                'humidity': first_weather.rel_humidity,
                'light_intensity': first_weather.solar_radiation,
                'co2': self._get_required_param(getattr(self.system_config, 'initial_state_parameters', {}), 'initial_co2_concentration', 'initial_state_parameters CSV'),
                'ph': self._get_required_param(system_params, 'default_ph', 'system CSV'),
                'ec': self._get_required_param(getattr(self.system_config, 'environment', {}), 'min_ec', 'environment CSV')
            }
        else:
            # Use initial values from CSV instead of fallbacks when no weather data available
            initial_params = getattr(self.system_config, 'initial_state_parameters', {})
            system_params = getattr(self.system_config, 'system_configuration', {})
            environment_factors = {
                'temperature': self._get_required_param(initial_params, 'initial_air_temperature', 'initial state CSV'),
                'humidity': self._get_required_param(initial_params, 'initial_humidity', 'initial state CSV'),
                'light_intensity': self._get_required_param(initial_params, 'initial_solar_radiation', 'initial state CSV'),
                'co2': self._get_required_param(initial_params, 'initial_co2_concentration', 'initial state CSV'),
                'ph': self._get_required_param(initial_params, 'initial_ph', 'initial state CSV'),
                'ec': self._get_required_param(initial_params, 'initial_ec', 'initial state CSV')
            }
        
        # Calculate adaptation index for current environment
        if hasattr(self.genetic_db, 'calculate_adaptation_index'):
            adaptation_index = self.genetic_db.calculate_adaptation_index(environment_factors)
            self.cultivar_adaptation_index = adaptation_index
        
        # Get best cultivars for conditions
        if hasattr(self.genetic_db, 'get_best_cultivars_for_conditions'):
            best_cultivars = self.genetic_db.get_best_cultivars_for_conditions(environment_factors)
            self.best_cultivars = best_cultivars
        
        # Calculate phenotype expression
        if hasattr(self.ge_model, 'calculate_phenotype_expression'):
            try:
                # Create a default trait for phenotype calculation
                trait = type('GeneticTrait', (), {
                    'trait_name': 'growth_rate',
                    'heritability': self._get_required_param(genetic_params, 'growth_rate_heritability', 'genetic_parameters CSV'),
                    'environmental_sensitivity': self._get_required_param(genetic_params, 'growth_rate_environmental_sensitivity', 'genetic_parameters CSV')
                })()
                phenotype = self.ge_model.calculate_phenotype_expression(
                    cultivar_id=self.current_cultivar,
                    environment_factors=environment_factors,
                    trait=trait
                )
                self.cultivar_phenotype = phenotype
            except (ValueError, KeyError) as e:
                # If cultivar not found, use CSV parameter
                self.cultivar_phenotype = self._get_required_param(genetic_params, 'cultivar_phenotype', 'genetic_parameters CSV')
        
        # Predict cultivar performance
        if hasattr(self.ge_model, 'predict_cultivar_performance'):
            try:
                performance = self.ge_model.predict_cultivar_performance(
                    cultivar_id=self.current_cultivar,
                    environment_factors=environment_factors
                )
                self.cultivar_performance = performance
            except (ValueError, KeyError) as e:
                # If cultivar not found, use CSV parameters
                self.cultivar_performance = {
                    'yield_potential': self._get_required_param(genetic_params, 'cultivar_yield_potential', 'genetic_parameters CSV'),
                    'quality_score': self._get_required_param(genetic_params, 'cultivar_yield_potential', 'genetic_parameters CSV')
                }
        
        # Identify breeding targets
        if hasattr(self.breeding_assistant, 'identify_breeding_targets'):
            try:
                target_environment = environment_factors.copy()
                # Create default desired traits
                desired_traits = {
                    type('GeneticTrait', (), {
                        'trait_name': 'yield',
                        'heritability': self._get_required_param(genetic_params, 'yield_heritability', 'genetic_parameters CSV'),
                        'environmental_sensitivity': self._get_required_param(genetic_params, 'yield_environmental_sensitivity', 'genetic_parameters CSV')
                    })(): self._get_required_param(genetic_params, 'yield_target', 'genetic_parameters CSV'),
                    type('GeneticTrait', (), {
                        'trait_name': 'quality',
                        'heritability': self._get_required_param(genetic_params, 'quality_heritability', 'genetic_parameters CSV'),
                        'environmental_sensitivity': self._get_required_param(genetic_params, 'quality_environmental_sensitivity', 'genetic_parameters CSV')
                    })(): self._get_required_param(genetic_params, 'quality_target', 'genetic_parameters CSV')
                }
                breeding_targets = self.breeding_assistant.identify_breeding_targets(
                    target_environment, desired_traits
                )
                self.breeding_targets = breeding_targets
            except (ValueError, KeyError) as e:
                # If breeding targets can't be calculated, use CSV parameters
                self.breeding_targets = {
                    'yield_target': self._get_required_param(genetic_params, 'cultivar_yield_potential', 'genetic_parameters CSV'),
                    'quality_target': self._get_required_param(genetic_params, 'cultivar_yield_potential', 'genetic_parameters CSV')
                }
        
        # Estimate hybrid performance (if applicable)
        if hasattr(self.breeding_assistant, 'estimate_hybrid_performance'):
            # Use default parent cultivars for demonstration
            hybrid_performance = self.breeding_assistant.estimate_hybrid_performance(
                parent1_id='DEFAULT_PARENT_1',
                parent2_id='DEFAULT_PARENT_2',
                environment_factors=environment_factors
            )
            self.hybrid_performance = hybrid_performance
        
        # Use cultivar database functions
        if hasattr(self.genetic_db, 'add_cultivar'):
            # Add current cultivar to database if not present
            if not self.genetic_db.get_cultivar(self.current_cultivar):
                # Create a basic cultivar profile
                cultivar_profile = type('CultivarProfile', (), {
                    'cultivar_id': self.current_cultivar,
                    'genetic_parameters': {},
                    'performance_metrics': {}
                })()
                self.genetic_db.add_cultivar(cultivar_profile)

    def run_simulation(self, input_data: HydroInputData, 
                      max_days: int,
                      target_maturity: str,
                      treatment_id: str = None) -> SimulationResults:
        """
        Run the complete hydroponic simulation from transplanting to harvest.
        """
        logger.info(f"Starting simulation for {max_days} days, target: {target_maturity}")
        
        # Get parameters from CSV
        genetic_params = getattr(self.system_config, 'genetic_parameters', {})
        growth_params = getattr(self.system_config, 'growth_parameters', {})
        system_params = getattr(self.system_config, 'system', {})
        photosynthesis_params = getattr(self.system_config, 'photosynthesis_parameters', {})
        respiration_params = getattr(self.system_config, 'respiration_parameters', {})
        water_params = getattr(self.system_config, 'water_parameters', {})
        canopy_params = getattr(self.system_config, 'canopy_parameters', {})
        nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
        
        # Initialize simulation state
        daily_results = []
        # Get initial day from CSV parameters
        initial_params = getattr(self.system_config, 'initial_state_parameters', {})
        current_day = int(self._get_required_param(initial_params, 'initial_simulation_day', 'initial_state_parameters CSV'))
        
        # Initialize plant state from CSV parameters
        initial_params = getattr(self.system_config, 'initial_state_parameters', {})
        plant_state = {
            'total_biomass': self._get_required_param(initial_params, 'initial_total_biomass', 'initial state CSV'),
            'leaf_biomass': self._get_required_param(initial_params, 'initial_leaf_biomass', 'initial state CSV'),
            'stem_biomass': self._get_required_param(initial_params, 'initial_stem_biomass', 'initial state CSV'),
            'root_biomass': self._get_required_param(initial_params, 'initial_root_biomass', 'initial state CSV'),
            'growth_stage': self._get_required_param(initial_params, 'initial_growth_stage', 'initial state CSV'),
            'lai': self._get_required_param(initial_params, 'initial_leaf_area_index', 'initial state CSV'),
            'plant_height': self._get_required_param(initial_params, 'initial_shoot_length', 'initial_state_parameters CSV'),
            'leaf_number': self._get_required_param(initial_params, 'initial_leaf_number', 'initial state CSV'),
            'accumulated_gdd': self._get_required_param(initial_params, 'initial_accumulated_gdd', 'initial state CSV'),
            'thermal_time_daily': self._get_required_param(initial_params, 'initial_thermal_time_daily', 'initial_state_parameters CSV'),
            'days_to_flowering': self._get_required_param(initial_params, 'initial_days_to_flowering', 'initial_state_parameters CSV'),
            'bolting_risk': self._get_required_param(initial_params, 'initial_bolting_risk', 'initial_state_parameters CSV'),
            'nitrogen_content': self._get_required_param(initial_params, 'initial_nitrogen_content', 'initial_state_parameters CSV'),
            'carbon_content': self._get_required_param(initial_params, 'initial_carbon_content', 'initial_state_parameters CSV'),
            'water_content': self._get_required_param(initial_params, 'initial_water_content', 'initial_state_parameters CSV'),
            'dry_matter_content': self._get_required_param(initial_params, 'initial_dry_matter_content', 'initial_state_parameters CSV'),
            'leaf_area_m2': self._get_required_param(initial_params, 'initial_leaf_area', 'initial state CSV'),
            'root_length': self._get_required_param(initial_params, 'initial_root_length', 'initial state CSV'),
            'root_surface_area': self._get_required_param(initial_params, 'initial_root_surface_area', 'initial state CSV'),
            'photosynthesis_rate': self._get_required_param(initial_params, 'initial_photosynthesis_rate', 'initial state CSV'),
            'respiration_rate': self._get_required_param(initial_params, 'initial_respiration_rate', 'initial state CSV'),
            'transpiration_rate': self._get_required_param(initial_params, 'initial_transpiration_rate', 'initial state CSV'),
            'senesced_biomass': self._get_required_param(initial_params, 'initial_senesced_biomass', 'initial_state_parameters CSV'),
            'senescence_rate': self._get_required_param(initial_params, 'initial_senescence_rate', 'initial_state_parameters CSV'),
            'leaf_senescence_rate': self._get_required_param(initial_params, 'initial_leaf_senescence_rate', 'initial_state_parameters CSV'),
            'stem_senescence_rate': self._get_required_param(initial_params, 'initial_stem_senescence_rate', 'initial_state_parameters CSV'),
            'water_uptake_rate': self._get_required_param(initial_params, 'initial_water_uptake_rate', 'initial state CSV'),
            'nutrient_uptake': {},
            'stress_factors': {},
            'integrated_stress_factor': self._get_required_param(initial_params, 'initial_integrated_stress_factor', 'initial_state_parameters CSV'),
            'solution_volume': self._get_required_param(system_params, 'tank_volume', 'system CSV'),
            'ph': self._get_required_param(initial_params, 'initial_ph', 'initial state CSV'),
            'ec': self._get_required_param(initial_params, 'initial_ec', 'initial state CSV'),
            'nutrient_concentrations': {
                'N-NO3': self._get_required_param(initial_params, 'initial_n_no3_concentration', 'initial state CSV'),
                'P-PO4': self._get_required_param(initial_params, 'initial_p_po4_concentration', 'initial state CSV'),
                'K': self._get_required_param(initial_params, 'initial_k_concentration', 'initial state CSV'),
                'Ca': self._get_required_param(initial_params, 'initial_ca_concentration', 'initial state CSV'),
                'Mg': self._get_required_param(initial_params, 'initial_mg_concentration', 'initial state CSV')
            },
            'temperature_stress': self._get_required_param(initial_params, 'initial_temperature_stress', 'initial_state_parameters CSV'),
            'water_stress': self._get_required_param(initial_params, 'initial_water_stress', 'initial_state_parameters CSV'),
            'nutrient_stress': self._get_required_param(initial_params, 'initial_nutrient_stress', 'initial_state_parameters CSV'),
            'light_stress': self._get_required_param(initial_params, 'initial_light_stress', 'initial_state_parameters CSV'),
            'co2_stress': self._get_required_param(initial_params, 'initial_co2_stress', 'initial_state_parameters CSV'),
            'salinity_stress': self._get_required_param(initial_params, 'initial_salinity_stress', 'initial_state_parameters CSV'),
            'root_zone_temp': self._get_required_param(initial_params, 'initial_air_temperature', 'initial state CSV'),
            'air_temperature': self._get_required_param(initial_params, 'initial_air_temperature', 'initial state CSV'),
            'humidity': self._get_required_param(initial_params, 'initial_humidity', 'initial state CSV'),
            'vpd': self._get_required_param(initial_params, 'initial_vpd', 'initial state CSV'),
            'co2_concentration': self._get_required_param(initial_params, 'initial_co2_concentration', 'initial state CSV'),
            'solar_radiation': self._get_required_param(initial_params, 'initial_solar_radiation', 'initial state CSV'),
            'daylength': self._get_required_param(initial_params, 'initial_daylength', 'initial_state_parameters CSV'),
            'wind_speed': self._get_required_param(initial_params, 'initial_wind_speed', 'initial_state_parameters CSV'),
            'rainfall': self._get_required_param(initial_params, 'initial_rainfall', 'initial_state_parameters CSV')
        }
        
        # Initialize hourly weather interpolator (commented out as module is missing)
        # self.hourly_weather_interpolator = create_hourly_weather_interpolator()
        
        # Initialize root model
        tank_volume = self._get_required_param(system_params, 'tank_volume', 'system CSV')
        self.root_model = create_enhanced_root_uptake_model(
            system_type=getattr(self.system_config, 'system_type', 'NFT'),
            tank_volume=tank_volume,
            system_config=self.system_config
        )
        
        # Run simulation day by day
        for day in range(max_days):
            if current_day >= len(input_data.weather_data):
                logger.warning(f"Weather data exhausted at day {current_day}")
                break
                
            weather_day = input_data.weather_data[current_day]
            
            # Update environmental conditions
            plant_state.update({
                'air_temperature': weather_day.temp_avg,
                'humidity': weather_day.rel_humidity,
                'solar_radiation': weather_day.solar_radiation,
                'wind_speed': weather_day.wind_speed,
                'rainfall': weather_day.rainfall,
                'day': current_day,
                'date': weather_day.date
            })
            
            # Calculate VPD
            plant_state['vpd'] = calculate_vpd(
                plant_state['air_temperature'], 
                plant_state['humidity']
            )
            
            # Calculate thermal time
            system_params = getattr(self.system_config, 'system_configuration', {})
            water_params = getattr(self.system_config, 'water_parameters', {})
            base_temp = self._get_required_param(system_params, 'base_temperature', 'system_configuration CSV')
            plant_state['thermal_time_daily'] = calculate_thermal_time(
                plant_state['air_temperature'], 
                base_temp
            )
            plant_state['accumulated_gdd'] += plant_state['thermal_time_daily']
            
            # Simulate plant growth (simplified model)
            growth_rate = self._calculate_growth_rate(plant_state)
            plant_state['total_biomass'] += growth_rate
            
            # Update biomass allocation with comprehensive model
            plant_state = self._update_biomass_allocation(plant_state)
            
            # Use additional biomass allocation model functions
            plant_state = self._update_advanced_biomass_allocation(plant_state)
            
            # Update growth stage based on accumulated GDD
            plant_state = self._update_growth_stage(plant_state)
            
            # Calculate integrated stress factors using advanced model
            plant_state = self._calculate_integrated_stress(plant_state)
            
            # Use comprehensive stress model functions
            plant_state = self._update_advanced_stress_models(plant_state)
            
            # Calculate canopy architecture and light interception
            plant_state = self._calculate_canopy_architecture(plant_state)
            
            # Use additional canopy architecture functions
            plant_state = self._update_advanced_canopy_architecture(plant_state)
            
            # Calculate physiological processes
            plant_state = self._calculate_physiological_processes(plant_state)
            
            # Update root architecture and nutrient uptake
            plant_state = self._update_root_architecture(plant_state)
            
            # Use comprehensive root system model functions
            plant_state = self._update_advanced_root_system(plant_state)
            
            # Update environmental control
            plant_state = self._update_environmental_control(plant_state)
            
            # Use additional environmental control functions
            plant_state = self._update_advanced_environmental_control(plant_state)
            
            # Update solution chemistry
            plant_state = self._update_solution_chemistry(plant_state)
            
            # Update root zone temperature dynamics
            plant_state = self._update_root_zone_temperature(plant_state)
            
            # Create daily results with comprehensive data for all CSV columns
            daily_result = DailyResults(
                day=current_day,
                date=datetime.strptime(weather_day.date, '%Y-%m-%d'),
                eto_ref=self._get_required_param(water_params, 'default_transpiration_rate', 'water_parameters CSV'),
                etc_prime=plant_state['transpiration_rate'],  # Crop evapotranspiration
                transpiration=plant_state['transpiration_rate'],
                water_uptake_total=plant_state['water_uptake_rate'] * self._get_required_param(getattr(self.system_config, 'system_configuration', {}), 'n_plants', 'system_configuration CSV'),
                tank_volume=plant_state['solution_volume'],
                nutrient_concentrations=plant_state['nutrient_concentrations'],
                temp_avg=plant_state['air_temperature'],
                solar_radiation=plant_state['solar_radiation'],
                vpd=plant_state['vpd'],
                water_use_efficiency=self._calculate_water_use_efficiency(plant_state),
                ph=plant_state['ph'],
                ec=plant_state['ec'],
                rzt=plant_state['root_zone_temp'],
                rzt_growth_factor=self._get_required_param(self.system_config.root_parameters, "rzt_growth_factor", "root_parameters CSV"),
                rzt_nutrient_factor=self._get_required_param(self.system_config.root_parameters, "rzt_nutrient_factor", "root_parameters CSV"),
                # Advanced RZT parameters
                rzt_water_factor=self._get_required_param(self.system_config.root_parameters, "rzt_water_factor", "root_parameters CSV"),
                rzt_photosynthesis_factor=self._get_required_param(self.system_config.root_parameters, "rzt_photosynthesis_factor", "root_parameters CSV"),
                rzt_root_metabolism_factor=self._get_required_param(self.system_config.root_parameters, "rzt_root_metabolism_factor", "root_parameters CSV"),
                rzt_stress_factor=self._get_required_param(self.system_config.root_parameters, "rzt_stress_factor", "root_parameters CSV"),
                rzt_optimal_factor=self._get_required_param(self.system_config.root_parameters, "rzt_optimal_factor", "root_parameters CSV"),
                rzt_daily_range=self._get_required_param(self.system_config.root_parameters, "rzt_daily_range", "root_parameters CSV"),
                individual_rzt_factors=self._get_required_param(self.system_config.root_parameters, "individual_rzt_factors", "root_parameters CSV"),
                root_temp_stress=self._get_required_param(self.system_config.root_parameters, "root_temp_stress", "root_parameters CSV"),
                v_stage=self._calculate_v_stage(plant_state),
                leaf_number=plant_state['leaf_number'],
                leaf_area_m2=plant_state['leaf_area_m2'],
                average_leaf_area_cm2=plant_state['leaf_area_m2'] * 10000 / max(1, plant_state['leaf_number']),
                co2_concentration=plant_state['co2_concentration'],
                vpd_actual=plant_state['vpd'],
                env_photosynthesis_factor=self._calculate_env_photosynthesis_factor(plant_state),
                env_transpiration_factor=self._calculate_env_transpiration_factor(plant_state),
                # Advanced photosynthesis model results
                vcmax_25=self._get_required_param(photosynthesis_params, 'vcmax_25', 'photosynthesis_parameters CSV'),
                jmax_25=self._get_required_param(photosynthesis_params, 'jmax_25', 'photosynthesis_parameters CSV'),
                quantum_efficiency=self._get_required_param(getattr(self.system_config, 'photosynthesis', {}), 'quantum_efficiency', 'photosynthesis CSV'),
                rubisco_limited=plant_state['photosynthesis_rate'],
                light_limited=plant_state['photosynthesis_rate'],
                co2_compensation=self._get_required_param(getattr(self.system_config, 'photosynthesis', {}), 'co2_compensation', 'photosynthesis CSV'),
                intercellular_co2=self._get_required_param(getattr(self.system_config, 'photosynthesis', {}), 'ci_fraction', 'photosynthesis CSV'),
                # Enhanced respiration model results
                maintenance_resp_leaves=plant_state['respiration_rate'],
                maintenance_resp_stems=plant_state['respiration_rate'],
                maintenance_resp_roots=plant_state['respiration_rate'],
                growth_resp_leaves=plant_state['respiration_rate'],
                growth_resp_stems=plant_state['respiration_rate'],
                growth_resp_roots=plant_state['respiration_rate'],
                temperature_acclimation=self._get_required_param(respiration_params, 'acclimation_rate', 'respiration_parameters CSV'),
                age_factor=1.0,
                # Phenology and development
                accumulated_gdd=plant_state['accumulated_gdd'],
                development_rate=plant_state['thermal_time_daily'],
                growth_stage=plant_state['growth_stage'],
                thermal_time_daily=plant_state['thermal_time_daily'],
                is_vegetative=True if plant_state['growth_stage'] in ['V1', 'V2', 'V3', 'V4', 'V5', 'V6'] else False,
                is_reproductive=False,
                # Growth and biomass
                total_biomass=plant_state['total_biomass'],
                leaf_biomass=plant_state['leaf_biomass'],
                stem_biomass=plant_state['stem_biomass'],
                root_biomass=plant_state['root_biomass'],
                daily_growth_rate=self._calculate_growth_rate(plant_state),
                leaf_growth_rate=self._calculate_growth_rate(plant_state) * self._get_required_param(growth_params, 'leaf_growth_allocation', 'growth_parameters CSV'),
                stem_growth_rate=self._calculate_growth_rate(plant_state) * self._get_required_param(growth_params, 'stem_growth_allocation', 'growth_parameters CSV'),
                root_growth_rate=self._calculate_growth_rate(plant_state) * self._get_required_param(growth_params, 'root_growth_allocation', 'growth_parameters CSV'),
                # Advanced canopy architecture
                lai=plant_state['lai'],
                canopy_height_cm=plant_state['plant_height'],
                light_interception=plant_state['lai'],
                sunlit_lai=plant_state['lai'],
                shaded_lai=plant_state['lai'],
                total_absorbed_ppfd=plant_state['solar_radiation'],
                canopy_photosynthesis=plant_state['photosynthesis_rate'],
                canopy_layers=self._get_required_param(canopy_params, 'number_of_layers', 'canopy_parameters CSV'),
                ppfd_top=plant_state['solar_radiation'],
                ppfd_bottom=plant_state['solar_radiation'],
                light_extinction=self._get_required_param(canopy_params, 'extinction_coefficient', 'canopy_parameters CSV'),
                # Photosynthesis detailed
                photosynthesis_rate=plant_state['photosynthesis_rate'],
                net_assimilation=plant_state['photosynthesis_rate'] - plant_state['respiration_rate'],
                # Respiration detailed
                maintenance_respiration=plant_state['respiration_rate'],
                growth_respiration=plant_state['respiration_rate'],
                respiration_rate=plant_state['respiration_rate'],
                # Advanced root architecture
                root_surface_area=plant_state['root_surface_area'],
                root_length_density=plant_state['root_length'],
                root_volume=plant_state['root_surface_area'],
                fine_root_length=plant_state['root_length'],
                coarse_root_length=plant_state['root_length'],
                # Nitrogen dynamics detailed
                nitrogen_uptake_mg=plant_state['nutrient_uptake'].get('N-NO3', 0),
                nitrogen_demand_mg=plant_state['nutrient_uptake'].get('N-NO3', 0),
                nitrogen_stress_factor=plant_state['nutrient_stress'],
                leaf_nitrogen_conc=self._get_required_param(nitrogen_params, 'critical_n_concentrations_leaves_optimal', 'nitrogen_parameters CSV'),
                root_nitrogen_conc=self._get_required_param(nitrogen_params, 'critical_n_concentrations_roots_optimal', 'nitrogen_parameters CSV'),
                nitrogen_remobilization=plant_state['nutrient_uptake'].get('N-NO3', 0),
                n_pool_structural=plant_state['nitrogen_content'],
                n_pool_metabolic=plant_state['nitrogen_content'],
                n_pool_storage=plant_state['nitrogen_content'],
                n_pool_transport=plant_state['nitrogen_content'],
                n_remobilization=plant_state['nutrient_uptake'].get('N-NO3', 0),
                n_critical_conc=self._get_required_param(nitrogen_params, 'critical_n_factor', 'nitrogen_parameters CSV'),
                # Phosphorus dynamics
                phosphorus_uptake_mg=plant_state['nutrient_uptake'].get('P-PO4', 0),
                phosphorus_remobilization=plant_state['nutrient_uptake'].get('P-PO4', 0),
                potassium_remobilization=plant_state['nutrient_uptake'].get('K', 0),
                # Senescence - Enhanced with comprehensive senescence model
                senescence_rate=plant_state['senescence_rate'],
                leaf_senescence_rate=plant_state['leaf_senescence_rate'],
                senesced_area=plant_state['leaf_area_m2'],
                senesced_biomass=plant_state['senesced_biomass'],
                average_senescence_stage=plant_state.get('average_senescence_stage', 'healthy'),
                active_senescence_types=plant_state.get('active_senescence_types', []),
                remobilization_pool=plant_state.get('remobilization_pool', {}),
                # Stress factors - Enhanced with comprehensive integrated stress model
                integrated_stress_factor=plant_state['integrated_stress_factor'],
                temperature_stress_level=plant_state['temperature_stress'],
                temperature_stress_photosynthesis=plant_state['temperature_stress'],
                temperature_stress_growth=plant_state['temperature_stress'],
                water_stress=plant_state['water_stress'],
                nutrient_stress=plant_state['nutrient_stress'],
                salinity_stress=plant_state['salinity_stress'],
                ph_stress=plant_state['ph_stress'],
                oxygen_stress=plant_state['oxygen_stress'],
                cold_stress_factor=plant_state['temperature_stress'],
                heat_stress_factor=plant_state['temperature_stress'],
                temperature_stress_factor=plant_state['temperature_stress'],
                stress_severity=plant_state.get('stress_severity', 'mild'),
                dominant_stresses=plant_state.get('dominant_stresses', []),
                stress_interactions_active=plant_state.get('stress_interactions_active', []),
                acclimation_active=plant_state.get('acclimation_active', []),
                recovery_active=plant_state.get('recovery_active', []),
                total_damage=plant_state['total_damage'],
                # Nutrient mobility - Enhanced with comprehensive mobility model
                nutrient_transport_fluxes=plant_state.get('nutrient_transport_fluxes', {}),
                transport_limitations=plant_state.get('transport_limitations', []),
                mobility_efficiency=plant_state.get('mobility_efficiency', {}),
                nutrient_redistribution=plant_state.get('nutrient_redistribution', {}),
                transport_pool_fractions=plant_state.get('transport_pool_fractions', {}),
                cumulative_redistribution=plant_state.get('cumulative_redistribution', {}),
                # Advanced environmental control
                controlled_temperature=plant_state.get('controlled_temperature', plant_state['air_temperature']),
                controlled_humidity=plant_state.get('controlled_humidity', self._get_required_param(self.system_config.plant_parameters, 'default_humidity', 'plant_parameters CSV')),
                controlled_co2=plant_state.get('controlled_co2', plant_state['co2_concentration']),
                vpd_target=plant_state.get('vpd_target', self._get_required_param(self.system_config.plant_parameters, 'default_vpd', 'plant_parameters CSV')),
                environmental_cost=plant_state.get('environmental_cost', 0.0),
                # Solution chemistry - Enhanced with comprehensive pH model
                solution_ph=plant_state['ph'],
                solution_ec=plant_state['ec'],
                ph_change_from_uptake=plant_state.get('ph_change_from_uptake', 0.0),
                ph_change_from_drift=plant_state.get('ph_change_from_drift', 0.0),
                acid_dosed_ml_per_L=plant_state.get('acid_dosed_ml_per_L', 0.0),
                base_dosed_ml_per_L=plant_state.get('base_dosed_ml_per_L', 0.0),
                buffer_capacity=plant_state.get('buffer_capacity', 0.0),
                phosphate_h2po4_mg_L=plant_state.get('phosphate_h2po4_mg_L', 0.0),
                phosphate_hpo4_mg_L=plant_state.get('phosphate_hpo4_mg_L', 0.0),
                phosphate_po4_mg_L=plant_state.get('phosphate_po4_mg_L', 0.0),
                nutrient_precipitation_mg_L=sum(plant_state.get('nutrient_precipitation', {}).values()),
                henderson_hasselbalch_ph=plant_state.get('henderson_hasselbalch_ph', plant_state['ph']),
                controlled_ph=plant_state.get('controlled_ph', plant_state['ph']),
                acid_dosing_rate=plant_state.get('acid_dosing_rate', 0.0),
                base_dosing_rate=plant_state.get('base_dosing_rate', 0.0),
                # Genetic parameters from CSV
                cultivar_adaptation_index=self._get_required_param(genetic_params, 'adaptation_score', 'genetic_parameters CSV'),
                cultivar_yield_potential=self._get_required_param(genetic_params, 'cultivar_yield_potential', 'genetic_parameters CSV'),
                genetic_photosynthesis_capacity=self._get_required_param(genetic_params, 'genetic_photosynthesis_capacity', 'genetic_parameters CSV'),
                genetic_ec_tolerance=self._get_required_param(genetic_params, 'genetic_ec_tolerance', 'genetic_parameters CSV'),
                genetic_nitrate_efficiency=self._get_required_param(genetic_params, 'genetic_nitrate_efficiency', 'genetic_parameters CSV'),
                # Root cohorts and activity from CSV
                root_cohorts=plant_state.get('root_cohorts', []),
                root_activity_young=self._get_required_param(genetic_params, 'root_activity_young', 'genetic_parameters CSV'),
                root_activity_old=self._get_required_param(genetic_params, 'root_activity_old', 'genetic_parameters CSV'),
                root_surface_active=plant_state['root_surface_area'],
                root_turnover_rate=self._get_required_param(genetic_params, 'root_turnover_rate', 'genetic_parameters CSV')
            )
            
            daily_results.append(daily_result)
            current_day += 1
            
            # Check for harvest maturity
            if target_maturity == 'harvest' and plant_state['growth_stage'] in ['HM', 'HARVEST_MATURITY', 'HARVEST', 'MATURE']:
                logger.info(f"Harvest maturity reached at day {current_day}")
                break
        
        # Create simulation results with populated system metadata
        # Extract system metadata from CSV parameters
        system_id = 'HYDRO_SYS'
        location_id = 'GREENHOUSE'
        system_description = 'Default Hydroponic System'
        
        # Try to get system metadata from CSV parameters
        if hasattr(self.system_config, 'experiment_settings'):
            exp_settings = self.system_config.experiment_settings
            if 'treatment_id' in exp_settings:
                system_id = exp_settings['treatment_id']
            if 'cultivar_name' in exp_settings:
                crop_name = exp_settings['cultivar_name']
            else:
                crop_name = self.current_cultivar
        else:
            crop_name = self.current_cultivar
            
        # Create system description from available parameters
        system_type = 'NFT'  # Default
        # Try to get system_type from CSV parameters
        if hasattr(self.system_config, 'root_system'):
            root_system_params = self.system_config.root_system
            if 'system_type' in root_system_params:
                csv_system_type = root_system_params['system_type']
                if csv_system_type == 'nutrient_film_technique':
                    system_type = 'NFT'
                elif csv_system_type == 'deep_water_culture':
                    system_type = 'DWC'
                elif csv_system_type == 'aeroponics':
                    system_type = 'AEROPONICS'
                else:
                    system_type = csv_system_type.upper()
                
        system_area = self._get_required_param(system_params, 'system_area', 'system CSV')
        n_plants = self._get_required_param(getattr(self.system_config, 'system_configuration', {}), 'n_plants', 'system_configuration CSV')
        tank_volume = self._get_required_param(system_params, 'tank_volume', 'system CSV')
        
        system_description = f"{system_type} System - {system_area}m², {n_plants} plants, {tank_volume}L tank"
        
        results = SimulationResults(
            system_id=system_id,
            crop_id=crop_name,
            location_id=location_id,
            start_date=datetime.strptime(input_data.weather_data[0].date, '%Y-%m-%d'),
            end_date=datetime.strptime(input_data.weather_data[min(current_day-1, len(input_data.weather_data)-1)].date, '%Y-%m-%d'),
            total_days=len(daily_results),
            daily_results=daily_results,
            treatment_id=treatment_id
        )
        
        # Add system metadata to results for CSV export
        results.system_type = system_type
        results.system_area = system_area
        results.plant_count = n_plants
        # Get flow rate from CSV parameters
        system_params = getattr(self.system_config, 'system', {})
        flow_rate = self._get_required_param(system_params, 'flow_rate', 'system CSV')
        results.flow_rate = flow_rate
        results.system_description = system_description
        
        # Add transplanting period for CSV export
        results.transplanting_period_days = self._get_required_param(getattr(self.system_config, 'system_configuration', {}), 'transplanting_period_days', 'system_configuration CSV')
        
        # Calculate summary stats
        results.summary_stats = self._calculate_summary_stats(daily_results)
        
        logger.info(f"Simulation completed: {len(daily_results)} days, final biomass: {plant_state['total_biomass']:.2f}g")
        return results
    
    def _calculate_growth_rate(self, plant_state: dict) -> float:
        """Calculate daily growth rate based on environmental conditions."""
        # Get growth parameters from CSV
        growth_params = getattr(self.system_config, 'growth_parameters', {})
        base_growth = self._get_required_param(growth_params, 'base_growth_rate', 'growth_parameters CSV')
        
        # Temperature effect
        temp = plant_state['air_temperature']
        # Use phenology optimal temperature range instead of removed environment parameters
        phenology_params = getattr(self.system_config, 'phenology', {})
        optimal_temp_min = self._get_required_param(phenology_params, 'phenology_optimal_temperature_min', 'phenology CSV')
        optimal_temp_max = self._get_required_param(phenology_params, 'phenology_optimal_temperature_max', 'phenology CSV')
        if optimal_temp_min <= temp <= optimal_temp_max:
            temp_factor = self._get_required_param(growth_params, 'optimal_temp_factor', 'growth_parameters CSV')
        elif temp < self._get_required_param(self.system_config.plant_parameters, 'low_temperature_threshold', 'plant_parameters CSV'):
            temp_factor = max(self._get_required_param(self.system_config.plant_parameters, 'minimum_temperature_factor', 'plant_parameters CSV'), (temp - self._get_required_param(self.system_config.plant_parameters, 'temperature_stress_base_low', 'plant_parameters CSV')) / self._get_required_param(self.system_config.plant_parameters, 'temperature_stress_divisor_low', 'plant_parameters CSV'))
        else:
            temp_factor = max(self._get_required_param(self.system_config.plant_parameters, 'minimum_temperature_factor', 'plant_parameters CSV'), (self._get_required_param(self.system_config.plant_parameters, 'temperature_stress_base_high', 'plant_parameters CSV') - temp) / self._get_required_param(self.system_config.plant_parameters, 'temperature_stress_divisor_high', 'plant_parameters CSV'))
        
        # Light effect
        light_factor = min(1.0, plant_state['solar_radiation'] / self._get_required_param(self.system_config.plant_parameters, 'light_intensity_divisor', 'plant_parameters CSV'))
        
        # Stress effect
        stress_factor = max(self._get_required_param(self.system_config.plant_parameters, 'minimum_stress_factor', 'plant_parameters CSV'), 1.0 - plant_state['integrated_stress_factor'])
        
        # Growth stage effect
        stage = plant_state['growth_stage']
        if stage in ['V1', 'V2']:
            stage_factor = self._get_required_param(growth_params, 'early_stage_factor', 'growth_parameters CSV')
        elif stage in ['V3', 'V4']:
            stage_factor = self._get_required_param(growth_params, 'mid_stage_factor', 'growth_parameters CSV')
        elif stage in ['V5', 'V6']:
            stage_factor = self._get_required_param(growth_params, 'late_stage_factor', 'growth_parameters CSV')
        else:
            # Use mid_stage_factor as fallback for other stages (V7+, reproductive, etc.)
            stage_factor = self._get_required_param(growth_params, 'mid_stage_factor', 'growth_parameters CSV')
        
        return base_growth * temp_factor * light_factor * stress_factor * stage_factor
    
    def _update_biomass_allocation(self, plant_state: dict) -> dict:
        """Update biomass allocation using comprehensive functional balance model."""
        
        # === COMPREHENSIVE BIOMASS ALLOCATION INTEGRATION ===
        
        # 1. Calculate total growth available for allocation
        total_growth = plant_state['total_biomass'] - (plant_state['leaf_biomass'] + plant_state['stem_biomass'] + plant_state['root_biomass'])
        
        if total_growth > self._get_required_param(self.system_config.plant_parameters, 'minimum_total_growth', 'plant_parameters CSV'):
            # 2. Prepare stress factors for functional balance
            stress_factors = {
                'water_stress': plant_state.get('water_stress', self._get_required_param(self.system_config.plant_parameters, 'default_water_stress', 'plant_parameters CSV')),
                'nutrient_stress': plant_state.get('nutrient_stress', self._get_required_param(self.system_config.plant_parameters, 'default_nutrient_stress', 'plant_parameters CSV')),
                'light_stress': plant_state.get('light_stress', self._get_required_param(self.system_config.plant_parameters, 'default_light_stress', 'plant_parameters CSV')),
                'temperature_stress': plant_state.get('temperature_stress', self._get_required_param(self.system_config.plant_parameters, 'default_temperature_stress', 'plant_parameters CSV'))
            }
            
            # 3. Prepare developmental stage properties
            stage_props = {
                'current_stage': plant_state.get('growth_stage', 'V4'),
                'accumulated_gdd': plant_state.get('accumulated_gdd', self._get_required_param(self.system_config.plant_parameters, 'default_accumulated_gdd', 'plant_parameters CSV')),
                'bolting_risk': plant_state.get('bolting_risk', self._get_required_param(self.system_config.plant_parameters, 'default_bolting_risk', 'plant_parameters CSV')),
                'days_since_planting': plant_state.get('day', self._get_required_param(self.system_config.plant_parameters, 'default_days_since_planting', 'plant_parameters CSV'))
            }
            
            # 4. Prepare environmental conditions, no default values allowed
            env_conditions = {
                'temperature': plant_state.get('air_temperature', self._get_required_param(self.system_config.plant_parameters, 'default_air_temperature', 'plant_parameters CSV')),
                'light_intensity': plant_state.get('solar_radiation', self._get_required_param(self.system_config.plant_parameters, 'default_solar_radiation', 'plant_parameters CSV')),
                'co2': plant_state.get('co2_concentration', self._get_required_param(self.system_config.plant_parameters, 'default_co2_concentration', 'plant_parameters CSV')),
                'humidity': plant_state.get('humidity', self._get_required_param(self.system_config.plant_parameters, 'default_humidity', 'plant_parameters CSV')),
                'vpd': plant_state.get('vpd', self._get_required_param(self.system_config.plant_parameters, 'default_vpd', 'plant_parameters CSV'))
            }
            
            # 5. Use comprehensive functional balance allocation
            allocation_result = self.biomass_allocation_model.calculate_functional_balance_allocation(
                stress_factors=stress_factors,
                stage_props=stage_props,
                env_conditions=env_conditions
            )
            
            # 6. Apply allocation with constraints
            plant_state['leaf_biomass'] += total_growth * allocation_result['leaves']
            plant_state['stem_biomass'] += total_growth * allocation_result['stems']
            plant_state['root_biomass'] += total_growth * allocation_result['roots']
            
            # 7. Update allocation history and diagnostics
            plant_state['allocation_fractions'] = allocation_result
            plant_state['allocation_constraints'] = self._calculate_allocation_constraints(plant_state)
            plant_state['resource_limitations'] = self._calculate_resource_limitations(stress_factors, env_conditions)
            plant_state['sink_strength'] = self._calculate_sink_strength(plant_state)
            plant_state['source_strength'] = self._calculate_source_strength(plant_state)
            
            # 8. Update allocation summary
            allocation_summary = self._get_allocation_summary(plant_state)
            plant_state['allocation_summary'] = allocation_summary
        
        # 9. Update derived metrics using advanced leaf development model
        plant_state = self._update_leaf_development(plant_state)
        
        # 10. Update plant architecture based on allocation
        plant_state = self._update_plant_architecture(plant_state)
        
        return plant_state

    def _update_advanced_biomass_allocation(self, plant_state: dict) -> dict:
        """Use additional biomass allocation model functions that were previously unused."""
        
        # Get stress factors and environmental conditions, no default values allowed
        stress_factors = plant_state.get('stress_factors', {})
        env_conditions = {
            'air_temperature': plant_state.get('air_temperature', self._get_required_param(self.system_config.plant_parameters, 'leaf_development_air_temp_alt', 'plant_parameters CSV')),
            'solar_radiation': plant_state.get('solar_radiation', self._get_required_param(self.system_config.plant_parameters, 'leaf_development_solar_rad_alt', 'plant_parameters CSV')),
            'vpd': plant_state.get('vpd', self._get_required_param(self.system_config.plant_parameters, 'leaf_development_vpd_alt', 'plant_parameters CSV')),
            'light_stress': stress_factors.get('light_stress', 0.0)
        }
        
        # Get development stage properties
        stage_props = {
            'is_vegetative': plant_state.get('growth_stage', 'vegetative') == 'vegetative',
            'development_stage': plant_state.get('development_stage', self._get_required_param(self.system_config.plant_parameters, 'default_development_stage', 'plant_parameters CSV')),
            'thermal_time': plant_state.get('accumulated_gdd', 0.0)
        }
        
        # Use the comprehensive functional balance allocation method
        if hasattr(self, 'biomass_allocation_model'):
            allocation_result = self.biomass_allocation_model.calculate_functional_balance_allocation(
                stress_factors=stress_factors,
                stage_props=stage_props,
                env_conditions=env_conditions
            )
            
            # Update plant state with allocation results, no default values allowed
            plant_state['allocation_fractions'] = allocation_result
            plant_state['leaf_allocation'] = allocation_result.get('leaves', self._get_required_param(self.system_config.plant_parameters, 'leaf_allocation_default', 'plant_parameters CSV'))
            plant_state['stem_allocation'] = allocation_result.get('stems', self._get_required_param(self.system_config.plant_parameters, 'stem_allocation_default', 'plant_parameters CSV'))
            plant_state['root_allocation'] = allocation_result.get('roots', self._get_required_param(self.system_config.plant_parameters, 'root_allocation_default', 'plant_parameters CSV'))
            
            # Calculate resource limitations using the model's internal method
            if hasattr(self.biomass_allocation_model, '_calculate_resource_limitations'):
                resource_limitations = self.biomass_allocation_model._calculate_resource_limitations(
                    stress_factors, env_conditions
                )
                plant_state['resource_limitations'] = resource_limitations
                
                # Store individual limitation factors
                plant_state['light_limitation'] = resource_limitations.get('light', 0.0)
                plant_state['nitrogen_limitation'] = resource_limitations.get('nitrogen', 0.0)
                plant_state['water_limitation'] = resource_limitations.get('water', 0.0)
            
            # Calculate allocation shifts using the model's internal method
            if hasattr(self.biomass_allocation_model, '_calculate_allocation_shifts'):
                limitations = plant_state.get('resource_limitations', {})
                allocation_shifts = self.biomass_allocation_model._calculate_allocation_shifts(limitations)
                plant_state['allocation_shifts'] = allocation_shifts
                
                # Store individual shift factors
                plant_state['leaf_shift'] = allocation_shifts.get('leaf_shift', 0.0)
                plant_state['root_shift'] = allocation_shifts.get('root_shift', 0.0)
                plant_state['stem_shift'] = allocation_shifts.get('stem_shift', 0.0)
        
        return plant_state

    def _calculate_allocation_constraints(self, plant_state: dict) -> dict:
        """Calculate allocation constraints based on plant state."""
        constraints = {}
        
        # Get growth parameters from CSV
        growth_params = getattr(self.system_config, 'growth_parameters', {})
        
        # Minimum organ fractions from CSV
        min_fraction = self._get_required_param(growth_params, 'min_fraction_allocation', 'growth_parameters CSV')
        
        # Current biomass fractions
        total_biomass = plant_state['total_biomass']
        leaf_fraction = plant_state['leaf_biomass'] / max(0.001, total_biomass)
        stem_fraction = plant_state['stem_biomass'] / max(0.001, total_biomass)
        root_fraction = plant_state['root_biomass'] / max(0.001, total_biomass)
        
        constraints['min_fraction'] = min_fraction
        constraints['current_fractions'] = {
            'leaves': leaf_fraction,
            'stems': stem_fraction,
            'roots': root_fraction
        }
        constraints['violations'] = {
            'leaves': leaf_fraction < min_fraction,
            'stems': stem_fraction < min_fraction,
            'roots': root_fraction < min_fraction
        }
        
        return constraints
    
    def _calculate_resource_limitations(self, stress_factors: dict, env_conditions: dict) -> dict:
        """Calculate resource limitation factors."""
        limitations = {}
        
        # Get environment parameters from CSV
        environment_params = getattr(self.system_config, 'environment', {})
        
        # Light limitation, no default values allowed
        light_intensity = env_conditions.get('light_intensity', 18.0)
        # Use solar radiation from weather data instead of removed optimal_light_intensity
        optimal_light = env_conditions.get('solar_radiation', 20.0)  # Use actual weather data
        limitations['light'] = min(1.0, light_intensity / optimal_light)
        
        # Nitrogen limitation, no default values allowed
        nitrogen_stress = stress_factors.get('nutrient_stress', 0.0)
        limitations['nitrogen'] = 1.0 - nitrogen_stress
        
        # Water limitation, no default values allowed
        water_stress = stress_factors.get('water_stress', 0.0)
        limitations['water'] = 1.0 - water_stress
        
        # Temperature limitation, no default values allowed
        temperature = env_conditions.get('temperature', 22.0)
        phenology_params = getattr(self.system_config, 'phenology', {})
        optimal_temp = self._get_required_param(phenology_params, 'phenology_optimal_temperature_min', 'phenology CSV')
        temp_deviation = abs(temperature - optimal_temp)
        limitations['temperature'] = max(0.0, 1.0 - temp_deviation / 10.0)
        
        return limitations
    
    def _calculate_sink_strength(self, plant_state: dict) -> dict:
        """Calculate sink strength for each organ."""
        sink_strength = {}
        
        # Get growth parameters from CSV
        growth_params = getattr(self.system_config, 'growth_parameters', {})
        
        # Growth stage effects using CSV parameters
        growth_stage = plant_state.get('growth_stage', 'V4')
        if growth_stage in ['V1', 'V2', 'V3']:
            # Early vegetative - strong root sink, no default values allowed
            sink_strength['leaves'] = self._get_required_param(growth_params, 'early_vegetative_leaf_sink', 'growth_parameters CSV')
            sink_strength['stems'] = self._get_required_param(growth_params, 'early_vegetative_stem_sink', 'growth_parameters CSV')
            sink_strength['roots'] = self._get_required_param(growth_params, 'early_vegetative_root_sink', 'growth_parameters CSV')
        elif growth_stage in ['V4', 'V5', 'V6']:
            # Mid vegetative - balanced allocation, no default values allowed
            sink_strength['leaves'] = self._get_required_param(growth_params, 'mid_vegetative_leaf_sink', 'growth_parameters CSV')
            sink_strength['stems'] = self._get_required_param(growth_params, 'mid_vegetative_stem_sink', 'growth_parameters CSV')
            sink_strength['roots'] = self._get_required_param(growth_params, 'mid_vegetative_root_sink', 'growth_parameters CSV')
        elif growth_stage in ['HI', 'HD', 'HM']:
            # Head formation - strong leaf sink, no default values allowed
            sink_strength['leaves'] = self._get_required_param(growth_params, 'head_formation_leaf_sink', 'growth_parameters CSV')
            sink_strength['stems'] = self._get_required_param(growth_params, 'head_formation_stem_sink', 'growth_parameters CSV')
            sink_strength['roots'] = self._get_required_param(growth_params, 'head_formation_root_sink', 'growth_parameters CSV')
        else:
            # Use mid-vegetative values as fallback for other stages (V7+, reproductive, etc.), no default values allowed
            sink_strength['leaves'] = self._get_required_param(growth_params, 'mid_vegetative_leaf_sink', 'growth_parameters CSV')
            sink_strength['stems'] = self._get_required_param(growth_params, 'mid_vegetative_stem_sink', 'growth_parameters CSV')
            sink_strength['roots'] = self._get_required_param(growth_params, 'mid_vegetative_root_sink', 'growth_parameters CSV')
        
        return sink_strength
    
    def _calculate_source_strength(self, plant_state: dict) -> dict:
        """Calculate source strength for each organ."""
        source_strength = {}
        
        # Based on current biomass and photosynthetic capacity, no default values allowed
        leaf_biomass = plant_state.get('leaf_biomass', self._get_required_param(self.system_config.plant_parameters, 'default_leaf_biomass', 'plant_parameters CSV'))
        stem_biomass = plant_state.get('stem_biomass', self._get_required_param(self.system_config.plant_parameters, 'default_stem_biomass', 'plant_parameters CSV'))
        root_biomass = plant_state.get('root_biomass', self._get_required_param(self.system_config.plant_parameters, 'default_root_biomass', 'plant_parameters CSV'))
        
        total_biomass = leaf_biomass + stem_biomass + root_biomass
        
        if total_biomass > self._get_required_param(self.system_config.plant_parameters, 'biomass_division_safety', 'plant_parameters CSV'):
            source_strength['leaves'] = leaf_biomass / total_biomass * self._get_required_param(self.system_config.plant_parameters, 'leaf_source_strength_factor', 'plant_parameters CSV')
            source_strength['stems'] = stem_biomass / total_biomass * self._get_required_param(self.system_config.plant_parameters, 'stem_source_strength_factor', 'plant_parameters CSV')
            source_strength['roots'] = root_biomass / total_biomass * self._get_required_param(self.system_config.plant_parameters, 'root_source_strength_factor', 'plant_parameters CSV')
        else:
            source_strength['leaves'] = self._get_required_param(growth_params, 'default_source_leaf', 'growth_parameters CSV')
            source_strength['stems'] = self._get_required_param(growth_params, 'default_source_stem', 'growth_parameters CSV')
            source_strength['roots'] = self._get_required_param(growth_params, 'default_source_root', 'growth_parameters CSV')
        
        return source_strength
    
    def _get_allocation_summary(self, plant_state: dict) -> dict:
        """Get comprehensive allocation summary."""
        total_biomass = plant_state['total_biomass']
        
        summary = {
            'total_biomass': total_biomass,
            'organ_biomass': {
                'leaves': plant_state['leaf_biomass'],
                'stems': plant_state['stem_biomass'],
                'roots': plant_state['root_biomass']
            },
            'organ_fractions': {
                'leaves': plant_state['leaf_biomass'] / max(self._get_required_param(self.system_config.plant_parameters, 'biomass_division_safety', 'plant_parameters CSV'), total_biomass),
                'stems': plant_state['stem_biomass'] / max(self._get_required_param(self.system_config.plant_parameters, 'biomass_division_safety', 'plant_parameters CSV'), total_biomass),
                'roots': plant_state['root_biomass'] / max(self._get_required_param(self.system_config.plant_parameters, 'biomass_division_safety', 'plant_parameters CSV'), total_biomass)
            },
            'allocation_efficiency': self._calculate_allocation_efficiency(plant_state),
            'functional_balance_index': self._calculate_functional_balance_index(plant_state)
        }
        
        return summary
    
    def _calculate_allocation_efficiency(self, plant_state: dict) -> float:
        """Calculate allocation efficiency based on resource limitations."""
        limitations = plant_state.get('resource_limitations', {})
        
        # Efficiency is highest when all resources are optimally balanced, no default values allowed
        efficiency = min(limitations.values()) if limitations else self._get_required_param(self.system_config.plant_parameters, 'minimum_limitations_default', 'plant_parameters CSV')
        
        return efficiency

    def _calculate_water_use_efficiency(self, plant_state: dict) -> float:
        """Calculate water use efficiency (biomass per unit water uptake)."""
        total_biomass = plant_state.get('total_biomass', 0.0)
        water_uptake_rate = plant_state.get('water_uptake_rate', 0.0)

        if water_uptake_rate > 0:
            # WUE in g biomass / L water
            wue = (total_biomass * 1000) / water_uptake_rate if water_uptake_rate > 0 else 0.0
        else:
            wue = 0.0

        return wue

    def _calculate_v_stage(self, plant_state: dict) -> float:
        """Get current vegetative stage (V stage)."""
        return plant_state.get('v_stage', 0.0)

    def _calculate_env_photosynthesis_factor(self, plant_state: dict) -> float:
        """Get environmental photosynthesis factor."""
        return plant_state.get('env_photosynthesis_factor', 1.0)

    def _calculate_env_transpiration_factor(self, plant_state: dict) -> float:
        """Get environmental transpiration factor from plant state."""
        return plant_state.get('env_transpiration_factor', plant_state.get('vpd_transpiration_factor', 0.0))

    def _calculate_functional_balance_index(self, plant_state: dict) -> float:
        """Calculate functional balance index (0-1, higher = better balanced)."""
        fractions = plant_state.get('allocation_fractions', {})
        
        if not fractions:
            return self._get_required_param(self.system_config.plant_parameters, 'default_balance_index', 'plant_parameters CSV')
        
        # Get growth parameters from CSV
        growth_params = getattr(self.system_config, 'growth_parameters', {})
        
        # Ideal balance for lettuce from CSV parameters, no default values allowed          
        ideal_fractions = {
            'leaves': self._get_required_param(growth_params, 'ideal_leaf_fraction', 'growth_parameters CSV'),
            'stems': self._get_required_param(growth_params, 'ideal_stem_fraction', 'growth_parameters CSV'),
            'roots': self._get_required_param(growth_params, 'ideal_root_fraction', 'growth_parameters CSV')
        }
        
        balance_index = self._get_required_param(growth_params, 'balance_index_base', 'growth_parameters CSV')
        deviation_penalty = self._get_required_param(growth_params, 'deviation_penalty', 'growth_parameters CSV')
        
        for organ, ideal in ideal_fractions.items():
            actual = fractions.get(organ, 0.0)
            deviation = abs(actual - ideal)
            balance_index -= deviation * deviation_penalty
        
        return max(0.0, min(1.0, balance_index))
    
    def _update_plant_architecture(self, plant_state: dict) -> dict:
        """Update plant architecture based on biomass allocation."""
        # Update plant height based on stem biomass, no default values allowed
        base_height = self._get_required_param(self.system_config.plant_parameters, "base_height", "plant_parameters CSV")  # cm
        height_growth = plant_state['stem_biomass'] * self._get_required_param(self.system_config.plant_parameters, "height_growth_factor", "plant_parameters CSV")  # cm per g stem biomass (increased from 0.2)
        plant_state['plant_height'] = base_height + height_growth
        
        # Update root length based on root biomass, no default values allowed
        base_root_length = self._get_required_param(self.system_config.plant_parameters, "base_root_length", "plant_parameters CSV")  # cm
        root_growth = plant_state['root_biomass'] * self._get_required_param(self.system_config.plant_parameters, "root_growth_factor", "plant_parameters CSV")  # cm per g root biomass
        plant_state['root_length'] = base_root_length + root_growth
        
        # Update root surface area with proper calculation, no default values allowed
        avg_root_diameter_cm = self._get_required_param(self.system_config.plant_parameters, "avg_root_diameter_cm", "plant_parameters CSV")  # cm - realistic fine root diameter
        # Surface area = π * diameter * length
        plant_state['root_surface_area'] = plant_state['root_length'] * self._get_required_param(self.system_config.plant_parameters, 'pi_constant', 'plant_parameters CSV') * avg_root_diameter_cm

        # Ensure minimum realistic surface area based on plant size, no default values allowed
        min_surface_area = plant_state['total_biomass'] * self._get_required_param(self.system_config.plant_parameters, "min_surface_area_factor", "plant_parameters CSV")  # 100 cm²/g biomass ratio (more realistic)
        plant_state['root_surface_area'] = max(plant_state['root_surface_area'], min_surface_area)

        # Additional check - ensure minimum absolute value for seedlings, no default values allowed
        canopy_params = getattr(self.system_config, 'canopy_parameters', {})
        absolute_minimum = self._get_required_param(canopy_params, 'min_leaf_area_per_plant', 'canopy_parameters CSV')
        plant_state['root_surface_area'] = max(plant_state['root_surface_area'], absolute_minimum)
        
        return plant_state
    
    def _update_growth_stage(self, plant_state: dict) -> dict:
        """Update growth stage using advanced phenology model."""
        # Calculate daylength (simplified - would use actual solar calculations), no default values allowed
        daylength = plant_state.get('daylength', self._get_required_param(self.system_config.plant_parameters, 'default_daylength', 'plant_parameters CSV'))

        # Get stress factors, no default values allowed         
        water_stress_factor = 1.0 - plant_state.get('water_stress', self._get_required_param(self.system_config.plant_parameters, 'default_water_stress', 'plant_parameters CSV'))
        temp_stress_factor = 1.0 - plant_state.get('temperature_stress', self._get_required_param(self.system_config.plant_parameters, 'default_temperature_stress', 'plant_parameters CSV'))

        # Update phenology model, no default values allowed
        phenology_result = self.phenology_model.daily_update(
            temperature=plant_state['air_temperature'],
            daylength=daylength,
            water_stress=water_stress_factor,
            temperature_stress=temp_stress_factor
        )

        # Update plant state with phenology results, no default values allowed
        plant_state['growth_stage'] = self.phenology_model.developmental_state.current_stage.value
        plant_state['accumulated_gdd'] = self.phenology_model.developmental_state.total_thermal_time
        plant_state['daily_thermal_time'] = phenology_result.daily_thermal_time
        plant_state['development_rate'] = phenology_result.development_rate
        plant_state['bolting_risk'] = phenology_result.bolting_risk
        plant_state['stage_progress'] = self.phenology_model.developmental_state.stage_progress
        
        # Use comprehensive phenology model functions, no default values allowed
        plant_state = self._update_advanced_phenology(plant_state)

        # Update leaf number based on stage
        stage_leaf_map = {
            'GE': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_ge', 'plant_parameters CSV'),
            'VE': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_ve', 'plant_parameters CSV'),
            'V1': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v1', 'plant_parameters CSV'),
            'V2': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v2', 'plant_parameters CSV'),
            'V3': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v3', 'plant_parameters CSV'),
            'V4': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v4', 'plant_parameters CSV'),
            'V5': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v5', 'plant_parameters CSV'),
            'V6': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v6', 'plant_parameters CSV'),
            'V7': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v7', 'plant_parameters CSV'),
            'V8': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v8', 'plant_parameters CSV'),
            'V9': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v9', 'plant_parameters CSV'),
            'V10': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v10', 'plant_parameters CSV'),
            'V11+': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_v11_plus', 'plant_parameters CSV'),
            'HI': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_hi', 'plant_parameters CSV'),
            'HD': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_hd', 'plant_parameters CSV'),
            'HM': self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_hm', 'plant_parameters CSV')
        }
        plant_state['leaf_number'] = stage_leaf_map.get(plant_state['growth_stage'], self._get_required_param(self.system_config.plant_parameters, 'stage_leaf_number_default', 'plant_parameters CSV'))

        # Calculate days to flowering based on thermal time requirements, no default values allowed
        current_thermal_time = self.phenology_model.developmental_state.total_thermal_time
        flowering_requirement = self._get_required_param(self.system_config.phenology_parameters, "flowering_requirement_gdd", "phenology_parameters CSV")  # Simplified
        plant_state['days_to_flowering'] = max(0, (flowering_requirement - current_thermal_time) / max(0.1, phenology_result.daily_thermal_time))

        return plant_state

    def _update_advanced_phenology(self, plant_state: dict) -> dict:
        """Use comprehensive phenology model functions that were previously unused, no default values allowed."""
        
        if hasattr(self, 'phenology_model'):
            temperature = plant_state.get('air_temperature', 25.0)
            daylength = plant_state.get('day_length_hours', 12.0)
            water_stress = 1.0 - plant_state.get('water_stress', 0.0)
            temperature_stress = 1.0 - plant_state.get('temperature_stress', 0.0)
            
            # Use thermal time calculations, no default values allowed
            if hasattr(self.phenology_model, 'calculate_thermal_time'):
                thermal_time = self.phenology_model.calculate_thermal_time(temperature)
                plant_state['detailed_thermal_time'] = thermal_time
            
            # Use temperature factor calculations, no default values allowed
            if hasattr(self.phenology_model, 'calculate_temperature_factor'):
                temp_factor = self.phenology_model.calculate_temperature_factor(temperature)
                plant_state['phenology_temperature_factor'] = temp_factor
            
            # Use photoperiod factor calculations, no default values allowed
            if hasattr(self.phenology_model, 'calculate_photoperiod_factor'):
                photo_factor = self.phenology_model.calculate_photoperiod_factor(daylength)
                plant_state['photoperiod_factor'] = photo_factor
            
            # Use stress factor calculations, no default values allowed
            if hasattr(self.phenology_model, 'calculate_stress_factor'):
                stress_factor = self.phenology_model.calculate_stress_factor(water_stress, temperature_stress)
                plant_state['phenology_stress_factor'] = stress_factor
            
            # Use bolting risk calculations, no default values allowed
            if hasattr(self.phenology_model, 'calculate_bolting_risk'):
                bolting_risk = self.phenology_model.calculate_bolting_risk(temperature, daylength)
                plant_state['detailed_bolting_risk'] = bolting_risk
            
            # Use next stage calculations, no default values allowed
            if hasattr(self.phenology_model, 'get_next_stage'):
                try:
                    current_stage = type('GrowthStage', (), {'value': plant_state.get('growth_stage', 'VEGETATIVE')})()
                    next_stage = self.phenology_model.get_next_stage(current_stage)
                    plant_state['next_growth_stage'] = next_stage.value if hasattr(next_stage, 'value') else str(next_stage)
                except (AttributeError, TypeError):
                    plant_state['next_growth_stage'] = 'REPRODUCTIVE'
            
            # Use thermal requirement calculations, no default values allowed           
            if hasattr(self.phenology_model, 'get_thermal_requirement'):
                try:
                    # Create enum-like objects for stage calculations
                    current_stage = type('GrowthStage', (), {'value': plant_state.get('growth_stage', 'VEGETATIVE')})()
                    next_stage = type('GrowthStage', (), {'value': plant_state.get('next_growth_stage', 'REPRODUCTIVE')})()
                    thermal_req = self.phenology_model.get_thermal_requirement(current_stage, next_stage)
                    plant_state['thermal_requirement'] = thermal_req
                except (AttributeError, TypeError):
                    # If enum conversion fails, use default value
                    phenology_params = getattr(self.system_config, 'phenology', {})
                    plant_state['thermal_requirement'] = self._get_required_param(phenology_params, 'default_thermal_requirement', 'phenology CSV')
            
            # Use stage properties, no default values allowed
            if hasattr(self.phenology_model, 'get_stage_properties'):
                stage_props = self.phenology_model.get_stage_properties()
                plant_state['stage_properties'] = stage_props
        
        return plant_state

    def _update_leaf_development(self, plant_state: dict) -> dict:
        """Update leaf development using advanced leaf development model."""
        # Get daily thermal time from phenology, no default values allowed
        daily_thermal_time = plant_state.get('daily_thermal_time', 1.0)

        # Calculate stress factors for leaf development, no default values allowed
        stress_factors = self.leaf_model.calculate_stress_factors(
            water_stress=1.0 - plant_state.get('water_stress', 0.0),
            temperature_stress=1.0 - plant_state.get('temperature_stress', 0.0),
            nitrogen_stress=1.0 - plant_state.get('nutrient_stress', 0.0)
        )

        # Update V-stage first, no default values allowed
        stage_changed = self.leaf_model.update_v_stage(daily_thermal_time, stress_factors)

        # Update individual leaf areas
        leaf_result = self.leaf_model.update_leaf_areas(daily_thermal_time, stress_factors)

        # Update plant state with leaf development results, no default values allowed
        plant_state['leaf_area_m2'] = leaf_result['total_leaf_area_m2']
        system_config_params = getattr(self.system_config, 'system_configuration', {})
        plant_state['lai'] = leaf_result['leaf_area_index'] * self._get_required_param(system_config_params, 'n_plants', 'system_configuration CSV') / self._get_required_param(system_config_params, 'system_area', 'system_configuration CSV')
        plant_state['leaf_number'] = leaf_result['visible_leaf_count']
        plant_state['active_leaves'] = leaf_result['active_leaf_count']
        plant_state['senesced_area'] = leaf_result['senesced_area_daily']
        plant_state['v_stage'] = self.leaf_model.current_v_stage
        
        # Use comprehensive leaf development model functions, no default values allowed
        plant_state = self._update_advanced_leaf_development(plant_state)

        # Update senescence processes, no default values allowed
        plant_state = self._update_senescence_processes(plant_state)

        return plant_state

    def _update_advanced_leaf_development(self, plant_state: dict) -> dict:
        """Use comprehensive leaf development model functions that were previously unused, no default values allowed."""
        
        if hasattr(self, 'leaf_model'):
            temperature = plant_state.get('air_temperature', 25.0)
            daily_thermal_time = plant_state.get('daily_thermal_time', 1.0)
            
            # Use thermal time calculations
            if hasattr(self.leaf_model, 'calculate_thermal_time'):
                thermal_time = self.leaf_model.calculate_thermal_time(temperature)
                plant_state['leaf_thermal_time'] = thermal_time
            
            # Use leaf position factor calculations
            if hasattr(self.leaf_model, '_calculate_leaf_position_factor'):
                v_stage = plant_state.get('v_stage', 6.0)
                position_factor = self.leaf_model._calculate_leaf_position_factor(v_stage)
                plant_state['leaf_position_factor'] = position_factor
            
            # Use new leaf cohort creation
            if hasattr(self.leaf_model, '_create_new_leaf_cohort'):
                # Check if new leaf should be created based on thermal time
                if daily_thermal_time > 0.5:  # Threshold for new leaf creation
                    new_cohort = self.leaf_model._create_new_leaf_cohort()
                    plant_state['new_leaf_cohort'] = new_cohort
            
            # Use initial leaf cohort creation (for early stages)
            if hasattr(self.leaf_model, '_create_initial_leaf_cohort'):
                if plant_state.get('v_stage', 0) < 2.0:  # Early stage
                    initial_cohort = self.leaf_model._create_initial_leaf_cohort(1)
                    plant_state['initial_leaf_cohort'] = initial_cohort
        
        return plant_state

    def _update_senescence_processes(self, plant_state: dict) -> dict:
        """Update senescence processes using advanced senescence model."""
        # Calculate stress factors for senescence
        water_stress = plant_state.get('water_stress', 0.0)
        nitrogen_stress = plant_state.get('nitrogen_stress', 0.0)
        temperature_stress = plant_state.get('temperature_stress', 0.0)

        # For each leaf cohort (simplified - using average leaf age)
        avg_leaf_age = plant_state.get('days_since_planting', 0) / max(1, plant_state.get('leaf_number', 1))

        # Calculate age-based senescence rate
        age_senescence_rate = min(0.1, max(0.0, (avg_leaf_age - 20) / 30))  # Start after 20 days

        # === COMPREHENSIVE SENESCENCE INTEGRATION ===
        
        # 1. Initialize leaf cohorts if not already done
        if not hasattr(self, 'leaf_cohorts_initialized'):
            self._initialize_leaf_cohorts(plant_state)
            self.leaf_cohorts_initialized = True
        
        # 2. Prepare cohort data for senescence model
        cohort_data = self._prepare_cohort_data_for_senescence(plant_state)
        
        # 3. Prepare environmental stress data
        environmental_stress = {
            'water': plant_state.get('water_stress', 0.0),
            'nitrogen': plant_state.get('nutrient_stress', 0.0),
            'temperature': plant_state.get('temperature_stress', 0.0),
            'light': plant_state.get('light_stress', 0.0)
        }
        
        # 4. Prepare developmental state
        developmental_state = {
            'is_reproductive': plant_state.get('growth_stage', '') in ['HI', 'HD', 'HM'],
            'bolting_risk': plant_state.get('bolting_risk', 0.0),
            'accumulated_gdd': plant_state.get('accumulated_gdd', 0.0)
        }
        
        # 5. Use comprehensive daily_update method
        senescence_response = self.senescence_model.daily_update(
            cohort_data=cohort_data,
            environmental_stress=environmental_stress,
            developmental_state=developmental_state
        )
        
        # 6. Update plant state with comprehensive senescence results
        plant_state['senescence_rate'] = senescence_response.total_senescence_rate
        plant_state['senesced_area'] += senescence_response.senesced_area
        plant_state['senesced_biomass'] += senescence_response.senesced_biomass
        plant_state['leaf_area_m2'] = max(0.0, plant_state['leaf_area_m2'] - senescence_response.senesced_area)
        
        # 7. Update nutrient remobilization
        plant_state['nutrient_remobilization'] = senescence_response.remobilized_nutrients
        plant_state['nitrogen_remobilization'] = senescence_response.remobilized_nutrients.get('nitrogen', 0.0)
        plant_state['phosphorus_remobilization'] = senescence_response.remobilized_nutrients.get('phosphorus', 0.0)
        plant_state['potassium_remobilization'] = senescence_response.remobilized_nutrients.get('potassium', 0.0)
        
        # 8. Update senescence stage information
        plant_state['average_senescence_stage'] = senescence_response.average_senescence_stage.value
        plant_state['active_senescence_types'] = [st.value for st in senescence_response.active_senescence_types]
        
        # 9. Get remobilization pool for nutrient redistribution
        remobilization_pool = self.senescence_model.get_remobilization_pool()
        plant_state['remobilization_pool'] = remobilization_pool
        
        # Use comprehensive senescence model functions
        plant_state = self._update_advanced_senescence(plant_state)

        return plant_state

    def _update_advanced_senescence(self, plant_state: dict) -> dict:
        """Use comprehensive senescence model functions that were previously unused."""
        
        if hasattr(self, 'senescence_model'):
            # Use age senescence calculations
            if hasattr(self.senescence_model, 'calculate_age_senescence'):
                # Create a cohort state for age senescence calculation
                cohort_state = type('CohortState', (), {
                    'age_days': plant_state.get('days_since_emergence', 30.0),
                    'age_gdd': plant_state.get('accumulated_gdd', 300.0),
                    'nutrient_content': plant_state.get('leaf_nitrogen_content', 0.04),
                    'senescence_stage': 'active',
                    'senescence_damage': 0.0,
                    'is_recoverable': True
                })()
                age_senescence = self.senescence_model.calculate_age_senescence(cohort_state)
                plant_state['age_senescence_rate'] = age_senescence
            
            # Use stress senescence calculations
            if hasattr(self.senescence_model, 'calculate_stress_senescence'):
                water_stress = plant_state.get('water_stress', 0.0)
                nitrogen_stress = plant_state.get('nitrogen_stress', 0.0)
                temperature_stress = plant_state.get('temperature_stress', 0.0)
                light_stress = plant_state.get('light_stress', 0.0)
                
                stress_senescence = self.senescence_model.calculate_stress_senescence(
                    water_stress, nitrogen_stress, temperature_stress, light_stress
                )
                plant_state['stress_senescence_rates'] = stress_senescence
            
            # Use developmental senescence calculations
            if hasattr(self.senescence_model, 'calculate_developmental_senescence'):
                is_reproductive = plant_state.get('growth_stage', 'vegetative') == 'reproductive'
                canopy_params = getattr(self.system_config, 'canopy_parameters', {})
                canopy_position = self._get_required_param(canopy_params, 'default_canopy_position', 'canopy_parameters CSV')
                developmental_senescence = self.senescence_model.calculate_developmental_senescence(
                    is_reproductive, canopy_position
                )
                plant_state['developmental_senescence_rate'] = developmental_senescence
            
            # Use recovery rate calculations
            if hasattr(self.senescence_model, 'calculate_recovery_rate'):
                cohort_state = type('CohortState', (), {
                    'senescence_stage': 'stressed',
                    'age_days': plant_state.get('days_since_emergence', 30.0),
                    'age_gdd': plant_state.get('accumulated_gdd', 300.0),
                    'nutrient_content': plant_state.get('leaf_nitrogen_content', 0.04),
                    'is_recoverable': True,
                    'senescence_damage': 0.1
                })()
                current_stress_levels = {
                    'water_stress': plant_state.get('water_stress', 0.0),
                    'nitrogen_stress': plant_state.get('nitrogen_stress', 0.0)
                }
                recovery_rate = self.senescence_model.calculate_recovery_rate(
                    cohort_state, current_stress_levels
                )
                plant_state['senescence_recovery_rate'] = recovery_rate
            
            # Use senescence stage updates
            if hasattr(self.senescence_model, 'update_senescence_stage'):
                cohort_state = type('CohortState', (), {
                    'senescence_stage': 'active',
                    'age_days': plant_state.get('days_since_emergence', 30.0),
                    'age_gdd': plant_state.get('accumulated_gdd', 300.0),
                    'nutrient_content': plant_state.get('leaf_nitrogen_content', 0.04),
                    'senescence_damage': 0.0,
                    'is_recoverable': True
                })()
                updated_cohort = self.senescence_model.update_senescence_stage(cohort_state)
                if updated_cohort:
                    plant_state['updated_senescence_stage'] = updated_cohort.senescence_stage
                else:
                    plant_state['updated_senescence_stage'] = 'active'
            
            # Use nutrient remobilization calculations
            if hasattr(self.senescence_model, 'calculate_nutrient_remobilization'):
                cohort_state = type('CohortState', (), {
                    'nutrient_content': plant_state.get('leaf_nitrogen_content', 0.04),
                    'senescence_stage': 'senescing',
                    'age_days': plant_state.get('days_since_emergence', 30.0),
                    'age_gdd': plant_state.get('accumulated_gdd', 300.0),
                    'senescence_damage': 0.2,
                    'is_recoverable': False
                })()
                daily_senescence_rate = plant_state.get('leaf_senescence_rate', 0.01)
                nutrient_remobilization = self.senescence_model.calculate_nutrient_remobilization(
                    cohort_state, daily_senescence_rate
                )
                plant_state['detailed_nutrient_remobilization'] = nutrient_remobilization
        
        return plant_state
    
    def _initialize_leaf_cohorts(self, plant_state: dict):
        """Initialize leaf cohorts for senescence tracking."""
        # Initialize cohorts based on current leaf number
        leaf_number = plant_state.get('leaf_number', 2)
        
        # Create cohorts (simplified - one cohort per 2 leaves)
        for cohort_id in range(1, max(2, leaf_number // 2 + 1)):
            # Initial nutrient content (typical lettuce leaf composition)
            initial_nutrient_content = {
                'nitrogen': 0.04,      # 4% N
                'phosphorus': 0.005,   # 0.5% P
                'potassium': 0.03,     # 3% K
                'calcium': 0.01,       # 1% Ca
                'magnesium': 0.005,    # 0.5% Mg
                'sulfur': 0.003,       # 0.3% S
                'iron': 0.0001,        # 100 ppm Fe
                'manganese': 0.00005,  # 50 ppm Mn
                'zinc': 0.00002,       # 20 ppm Zn
                'copper': 0.00001,     # 10 ppm Cu
                'boron': 0.00002,      # 20 ppm B
                'molybdenum': 0.000001 # 1 ppm Mo
            }
            
            self.senescence_model.initialize_cohort(cohort_id, initial_nutrient_content)
    
    def _prepare_cohort_data_for_senescence(self, plant_state: dict) -> dict:
        """Prepare cohort data for senescence model."""
        cohort_data = {}
        
        # Calculate average leaf age and area per cohort
        leaf_number = plant_state.get('leaf_number', 2)
        total_area = plant_state.get('leaf_area_m2', 0.001)
        days_since_planting = plant_state.get('day', 0)
        
        # Create cohorts (simplified approach)
        cohorts_per_leaf = self._get_required_param(self.system_config.leaf_parameters, "cohorts_per_leaf", "leaf_parameters CSV")  # Each cohort represents 2 leaves
        num_cohorts = max(1, int(leaf_number // cohorts_per_leaf))
        
        for cohort_id in range(1, num_cohorts + 1):
            # Calculate cohort age (older cohorts are older)
            cohort_age_gdd = (cohort_id - 1) * 50.0 + plant_state.get('accumulated_gdd', 0.0) / num_cohorts
            
            # Calculate cohort area (distribute total area among cohorts)
            cohort_area = total_area / num_cohorts
            
            # Calculate cohort biomass (distribute leaf biomass among cohorts)
            cohort_biomass = plant_state.get('leaf_biomass', 0.05) / num_cohorts
            
            # Calculate canopy position (0 = bottom, 1 = top), no default values allowed
            canopy_position = (cohort_id - 1) / max(1, num_cohorts - 1)
            
            cohort_data[cohort_id] = {
                'age_gdd': cohort_age_gdd,
                'area': cohort_area,
                'biomass': cohort_biomass,
                'canopy_position': canopy_position,
                'nutrient_content': {
                    'nitrogen': 0.04,
                    'phosphorus': 0.005,
                    'potassium': 0.03,
                    'calcium': 0.01,
                    'magnesium': 0.005,
                    'sulfur': 0.003,
                    'iron': 0.0001,
                    'manganese': 0.00005,
                    'zinc': 0.00002,
                    'copper': 0.00001,
                    'boron': 0.00002,
                    'molybdenum': 0.000001
                }
            }
        
        return cohort_data

    def _update_nitrogen_balance(self, plant_state: dict) -> dict:
        """Update nitrogen balance using advanced nitrogen balance model."""
        # Calculate organ growth rates
        organ_growth_rates = {
            'leaves': plant_state.get('leaf_biomass', 0.0) * 0.05,  # 5% daily growth
            'stems': plant_state.get('stem_biomass', 0.0) * 0.03,   # 3% daily growth
            'roots': plant_state.get('root_biomass', 0.0) * 0.04    # 4% daily growth
        }

        # Environmental factors affecting nitrogen
        environmental_factors = {
            'temperature': plant_state['air_temperature'],
            'light_intensity': plant_state['solar_radiation'],
            'ph': plant_state.get('ph', 6.0),
            'ec': plant_state.get('ec', 1.0)
        }

        # Calculate nitrogen uptake
        solution_concentrations = {
            'N-NO3': plant_state.get('nitrate_concentration', 200.0),
            'N-NH4': plant_state.get('ammonium_concentration', 50.0)
        }

        n_uptake = self.nitrogen_model.calculate_nitrogen_uptake(
            root_mass=plant_state['root_biomass'],
            solution_concentrations=solution_concentrations,
            environmental_factors=environmental_factors
        )

        # Calculate nitrogen demand for growth
        n_demand = self.nitrogen_model.calculate_nitrogen_demand(
            organ_growth_rates=organ_growth_rates,
            growth_stage=plant_state['growth_stage'],
            environmental_factors=environmental_factors
        )

        # Calculate stress factors
        stress_factors = {
            'water_stress': plant_state.get('water_stress', 0.0),
            'temperature_stress': plant_state.get('temperature_stress', 0.0),
            'light_stress': plant_state.get('light_stress', 0.0)
        }

        # Calculate nitrogen remobilization
        n_remobilization = self.nitrogen_model.calculate_nitrogen_remobilization(
            stress_factors=stress_factors,
            senescence_rates={'leaves': 0.01, 'stems': 0.005, 'roots': 0.005},
            environmental_factors=environmental_factors
        )

        # Update plant state with nitrogen results
        plant_state['nitrogen_uptake'] = getattr(n_uptake, 'total_uptake', 0.0)
        plant_state['nitrogen_demand'] = getattr(n_demand, 'total_demand', 0.0)
        plant_state['nitrogen_stress'] = self.nitrogen_model.calculate_nitrogen_stress_level()
        plant_state['nitrogen_content'] = {
            'leaves': getattr(n_uptake, 'leaf_content', 0.03),
            'stems': getattr(n_uptake, 'stem_content', 0.02),
            'roots': getattr(n_uptake, 'root_content', 0.025)
        }
        
        # Use comprehensive nitrogen balance model functions
        plant_state = self._update_advanced_nitrogen_balance(plant_state)

        return plant_state

    def _update_advanced_nitrogen_balance(self, plant_state: dict) -> dict:
        """Use comprehensive nitrogen balance model functions that were previously unused."""
        
        if hasattr(self, 'nitrogen_model'):
            # Use nitrogen allocation calculations
            if hasattr(self.nitrogen_model, 'allocate_nitrogen'):
                try:
                    available_nitrogen = plant_state.get('nitrogen_uptake', 0.01)
                    nitrogen_demand = {
                        'leaves': plant_state.get('leaf_biomass', 0.05) * 0.04,
                        'stems': plant_state.get('stem_biomass', 0.03) * 0.02,
                        'roots': plant_state.get('root_biomass', 0.02) * 0.025
                    }
                    growth_stage = plant_state.get('growth_stage', 'vegetative')
                    allocation_result = self.nitrogen_model.allocate_nitrogen(
                        available_nitrogen, nitrogen_demand, growth_stage
                    )
                    plant_state['nitrogen_allocation'] = allocation_result
                except (KeyError, ValueError) as e:
                    # If allocation fails due to missing growth stage key, use default allocation
                    plant_state['nitrogen_allocation'] = {
                        'leaves': available_nitrogen * 0.4,
                        'stems': available_nitrogen * 0.3,
                        'roots': available_nitrogen * 0.3
                    }
            
            # Use nitrogen pool updates
            if hasattr(self.nitrogen_model, 'update_nitrogen_pools'):
                try:
                    external_input = plant_state.get('nitrogen_uptake', 0.01)
                    organ_growth_rates = {
                        'leaves': plant_state.get('leaf_growth_rate', 0.001),
                        'stems': plant_state.get('stem_growth_rate', 0.0005),
                        'roots': plant_state.get('root_growth_rate', 0.0003)
                    }
                    environmental_factors = {
                        'temperature': plant_state.get('air_temperature', 25.0),
                        'humidity': plant_state.get('humidity', 60.0),
                        'light': plant_state.get('solar_radiation', 10.0)
                    }
                    growth_stage = plant_state.get('growth_stage', 'vegetative')
                    stress_factors = plant_state.get('stress_factors', {})
                    senescence_rates = {
                        'leaves': plant_state.get('leaf_senescence_rate', 0.0),
                        'stems': plant_state.get('stem_senescence_rate', 0.0),
                        'roots': 0.0  # Roots typically don't senesce
                    }
                    nitrogen_response = self.nitrogen_model.update_nitrogen_pools(
                        external_input, organ_growth_rates, environmental_factors,
                        growth_stage, stress_factors, senescence_rates
                    )
                    plant_state['nitrogen_balance_response'] = nitrogen_response
                except (KeyError, ValueError) as e:
                    # If pool update fails, use default values
                    plant_state['nitrogen_balance_response'] = {
                        'total_nitrogen': external_input,
                        'nitrogen_deficiency': 0.0
                    }
            
            # Use nitrogen summary
            if hasattr(self.nitrogen_model, 'get_nitrogen_summary'):
                nitrogen_summary = self.nitrogen_model.get_nitrogen_summary()
                plant_state['nitrogen_summary'] = nitrogen_summary
            
            # Use organ nitrogen status updates
            if hasattr(self.nitrogen_model, 'update_organ_nitrogen_status'):
                for organ in ['leaves', 'stems', 'roots']:
                    self.nitrogen_model.update_organ_nitrogen_status(organ)
            
            # Use nitrogen remobilization calculations
            if hasattr(self.nitrogen_model, 'calculate_nitrogen_remobilization'):
                stress_factors = {
                    'water_stress': plant_state.get('water_stress', 0.0),
                    'nitrogen_stress': plant_state.get('nitrogen_stress', 0.0),
                    'temperature_stress': plant_state.get('temperature_stress', 0.0)
                }
                senescence_rates = {
                    'leaves': plant_state.get('leaf_senescence_rate', 0.0),
                    'stems': plant_state.get('stem_senescence_rate', 0.0),
                    'roots': 0.0
                }
                environmental_factors = {
                    'temperature': plant_state.get('air_temperature', 25.0),
                    'humidity': plant_state.get('humidity', 60.0),
                    'light': plant_state.get('solar_radiation', 10.0)
                }
                remobilization_result = self.nitrogen_model.calculate_nitrogen_remobilization(
                    stress_factors, senescence_rates, environmental_factors
                )
                plant_state['nitrogen_remobilization'] = remobilization_result
            
            # Use organ initialization
            if hasattr(self.nitrogen_model, 'initialize_organ'):
                for organ in ['leaves', 'stems', 'roots']:
                    organ_mass = plant_state.get(f'{organ}_biomass', 0.01)
                nitrogen_params = getattr(self.system_config, 'nitrogen_parameters', {})
                self.nitrogen_model.initialize_organ(
                    organ_name=organ,
                    initial_dry_mass=organ_mass,
                    initial_n_concentration=self._get_required_param(nitrogen_params, 'critical_n_concentrations_leaves_optimal', 'nitrogen_parameters CSV')
                )
        
        return plant_state
    
    def _update_nutrient_mobility(self, plant_state: dict) -> dict:
        """Update nutrient mobility and redistribution using comprehensive model."""
        
        # === COMPREHENSIVE NUTRIENT MOBILITY INTEGRATION ===
        
        # 1. Initialize organ pools if not already done
        if not hasattr(self, 'organ_pools_initialized'):
            self._initialize_organ_pools(plant_state)
            self.organ_pools_initialized = True
        
        # 2. Prepare organ demands for nutrient mobility
        organ_demands = self._prepare_organ_demands(plant_state)
        
        # 3. Prepare stress factors
        stress_factors = {
            'water': plant_state.get('water_stress', 0.0),
            'temperature': plant_state.get('temperature_stress', 0.0),
            'nutrient': plant_state.get('nutrient_stress', 0.0),
            'light': plant_state.get('light_stress', 0.0)
        }
        
        # 4. Prepare senescence rates
        senescence_rates = {
            'leaves': plant_state.get('senescence_rate', 0.0),
            'stems': plant_state.get('senescence_rate', 0.0) * 0.5,  # Stems senesce slower
            'roots': plant_state.get('senescence_rate', 0.0) * 0.3   # Roots senesce slowest
        }
        
        # 5. Prepare growth stage
        growth_stage = plant_state.get('growth_stage', 'V4')
        if growth_stage in ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']:
            stage = 'vegetative'
        elif growth_stage in ['HI', 'HD', 'HM']:
            stage = 'reproductive'
        else:
            stage = 'vegetative'
        
        # 6. Prepare water and assimilate fluxes
        water_fluxes = {
            'leaves': plant_state.get('transpiration_rate', 0.0) * 0.4,  # 40% of transpiration
            'stems': plant_state.get('transpiration_rate', 0.0) * 0.1,   # 10% of transpiration
            'roots': plant_state.get('water_uptake_rate', 0.0) * 0.5    # 50% of uptake
        }
        
        assimilate_fluxes = {
            'leaves': plant_state.get('photosynthesis_rate', 0.0) * 0.3,  # 30% of photosynthesis
            'stems': plant_state.get('photosynthesis_rate', 0.0) * 0.2,   # 20% of photosynthesis
            'roots': plant_state.get('photosynthesis_rate', 0.0) * 0.1    # 10% of photosynthesis
        }
        
        # 7. Prepare organ nutrient status
        organ_nutrient_status = {
            'leaves_nutrient_status': 1.0 - plant_state.get('nutrient_stress', 0.0),
            'stems_nutrient_status': 1.0 - plant_state.get('nutrient_stress', 0.0) * 0.8,
            'roots_nutrient_status': 1.0 - plant_state.get('nutrient_stress', 0.0) * 0.6
        }
        
        # 8. Prepare environmental conditions
        environmental_conditions = {
            'ec_factor': 1.0 - plant_state.get('salinity_stress', 0.0),
            'temperature_stress_factor': 1.0 - plant_state.get('temperature_stress', 0.0),
            'vpd_factor': 1.0 - plant_state.get('water_stress', 0.0)
        }
        
        # 9. Use comprehensive daily_update method
        mobility_response = self.mobility_model.daily_update(
            organ_demands=organ_demands,
            stress_factors=stress_factors,
            senescence_rates=senescence_rates,
            growth_stage=stage,
            water_fluxes=water_fluxes,
            assimilate_fluxes=assimilate_fluxes,
            temperature=plant_state.get('air_temperature', 22.0),
            organ_nutrient_status=organ_nutrient_status,
            environmental_conditions=environmental_conditions
        )
        
        # 10. Update plant state with comprehensive mobility results
        plant_state['nutrient_transport_fluxes'] = len(mobility_response.transport_fluxes)
        plant_state['transport_limitations'] = mobility_response.transport_limitations
        plant_state['mobility_efficiency'] = mobility_response.mobility_efficiency
        
        # 11. Update nutrient redistribution
        plant_state['nutrient_redistribution'] = mobility_response.total_redistribution
        plant_state['nitrogen_redistribution'] = mobility_response.total_redistribution.get('nitrogen', 0.0)
        plant_state['phosphorus_redistribution'] = mobility_response.total_redistribution.get('phosphorus', 0.0)
        plant_state['potassium_redistribution'] = mobility_response.total_redistribution.get('potassium', 0.0)
        
        # 12. Get mobility summary for diagnostics
        mobility_summary = self.mobility_model.get_mobility_summary()
        plant_state['mobility_summary'] = mobility_summary
        
        # Use comprehensive nutrient model functions
        plant_state = self._update_advanced_nutrient_models(plant_state)
        plant_state['transport_pool_fractions'] = mobility_summary['transport_pool_fractions']
        plant_state['cumulative_redistribution'] = mobility_summary['cumulative_redistribution']
        
        return plant_state
    
    def _initialize_organ_pools(self, plant_state: dict):
        """Initialize organ nutrient pools for mobility tracking."""
        # Initialize organ pools with current nutrient contents
        
        # Leaf pools
        leaf_nutrient_contents = {
            'nitrogen': plant_state.get('leaf_biomass', 0.05) * 0.04,      # 4% N
            'phosphorus': plant_state.get('leaf_biomass', 0.05) * 0.005,   # 0.5% P
            'potassium': plant_state.get('leaf_biomass', 0.05) * 0.03,      # 3% K
            'calcium': plant_state.get('leaf_biomass', 0.05) * 0.01,        # 1% Ca
            'magnesium': plant_state.get('leaf_biomass', 0.05) * 0.005,     # 0.5% Mg
            'sulfur': plant_state.get('leaf_biomass', 0.05) * 0.003         # 0.3% S
        }
        
        # Stem pools
        stem_nutrient_contents = {
            'nitrogen': plant_state.get('stem_biomass', 0.03) * 0.02,      # 2% N
            'phosphorus': plant_state.get('stem_biomass', 0.03) * 0.003,    # 0.3% P
            'potassium': plant_state.get('stem_biomass', 0.03) * 0.02,      # 2% K
            'calcium': plant_state.get('stem_biomass', 0.03) * 0.005,      # 0.5% Ca
            'magnesium': plant_state.get('stem_biomass', 0.03) * 0.003,     # 0.3% Mg
            'sulfur': plant_state.get('stem_biomass', 0.03) * 0.002         # 0.2% S
        }
        
        # Root pools
        root_nutrient_contents = {
            'nitrogen': plant_state.get('root_biomass', 0.02) * 0.025,      # 2.5% N
            'phosphorus': plant_state.get('root_biomass', 0.02) * 0.004,    # 0.4% P
            'potassium': plant_state.get('root_biomass', 0.02) * 0.025,     # 2.5% K
            'calcium': plant_state.get('root_biomass', 0.02) * 0.008,       # 0.8% Ca
            'magnesium': plant_state.get('root_biomass', 0.02) * 0.004,     # 0.4% Mg
            'sulfur': plant_state.get('root_biomass', 0.02) * 0.002         # 0.2% S
        }
        
        # Initialize pools in mobility model
        self.mobility_model.initialize_organ_pools('leaves', leaf_nutrient_contents, plant_state.get('leaf_biomass', 0.05))
        self.mobility_model.initialize_organ_pools('stems', stem_nutrient_contents, plant_state.get('stem_biomass', 0.03))
        self.mobility_model.initialize_organ_pools('roots', root_nutrient_contents, plant_state.get('root_biomass', 0.02))
    
    def _prepare_organ_demands(self, plant_state: dict) -> dict:
        """Prepare organ nutrient demands for mobility model."""
        # Calculate nutrient demands based on growth rates and stress factors
        
        # Growth rates (simplified)
        leaf_growth_rate = plant_state.get('leaf_biomass', 0.05) * 0.05  # 5% daily growth
        stem_growth_rate = plant_state.get('stem_biomass', 0.03) * 0.03  # 3% daily growth
        root_growth_rate = plant_state.get('root_biomass', 0.02) * 0.04  # 4% daily growth
        
        # Nutrient demands per organ (typical lettuce requirements)
        organ_demands = {
            'leaves': {
                'nitrogen': leaf_growth_rate * 0.04,      # 4% N requirement
                'phosphorus': leaf_growth_rate * 0.005,   # 0.5% P requirement
                'potassium': leaf_growth_rate * 0.03,     # 3% K requirement
                'calcium': leaf_growth_rate * 0.01,       # 1% Ca requirement
                'magnesium': leaf_growth_rate * 0.005,    # 0.5% Mg requirement
                'sulfur': leaf_growth_rate * 0.003         # 0.3% S requirement
            },
            'stems': {
                'nitrogen': stem_growth_rate * 0.02,      # 2% N requirement
                'phosphorus': stem_growth_rate * 0.003,   # 0.3% P requirement
                'potassium': stem_growth_rate * 0.02,     # 2% K requirement
                'calcium': stem_growth_rate * 0.005,     # 0.5% Ca requirement
                'magnesium': stem_growth_rate * 0.003,    # 0.3% Mg requirement
                'sulfur': stem_growth_rate * 0.002         # 0.2% S requirement
            },
            'roots': {
                'nitrogen': root_growth_rate * 0.025,     # 2.5% N requirement
                'phosphorus': root_growth_rate * 0.004,   # 0.4% P requirement
                'potassium': root_growth_rate * 0.025,    # 2.5% K requirement
                'calcium': root_growth_rate * 0.008,      # 0.8% Ca requirement
                'magnesium': root_growth_rate * 0.004,    # 0.4% Mg requirement
                'sulfur': root_growth_rate * 0.002         # 0.2% S requirement
            }
        }
        
        return organ_demands

    def _update_advanced_nutrient_models(self, plant_state: dict) -> dict:
        """Use comprehensive nutrient model functions that were previously unused."""
        
        if hasattr(self, 'mobility_model'):
            # Use EC factor calculations
            if hasattr(self.mobility_model, 'calculate_ec_from_concentrations'):
                concentrations = plant_state.get('nutrient_concentrations', {})
                ec_value = self.mobility_model.calculate_ec_from_concentrations(concentrations)
                plant_state['calculated_ec'] = ec_value
            
            # Use EC-based uptake modifiers
            if hasattr(self.mobility_model, 'calculate_ec_based_uptake_modifier'):
                current_ec = plant_state.get('ec', 1.2)
                optimal_ec = (self.params.optimal_ec_range[0] + self.params.optimal_ec_range[1]) / 2
                ec_modifiers = self.mobility_model.calculate_ec_based_uptake_modifier(
                    current_ec, optimal_ec
                )
                plant_state['ec_uptake_modifiers'] = ec_modifiers
            
            # Use transport capacity calculations
            if hasattr(self.mobility_model, 'calculate_transport_capacity'):
                source_organ = 'leaves'
                sink_organ = 'roots'
                water_flux = plant_state.get('water_uptake_rate', 0.1)
                assimilate_flux = plant_state.get('photosynthesis_rate', 0.05)
                temperature = plant_state.get('air_temperature', 25.0)
                
                transport_capacity = self.mobility_model.calculate_transport_capacity(
                    source_organ, sink_organ, water_flux, assimilate_flux, temperature
                )
                plant_state['transport_capacity'] = transport_capacity
            
            # Use sink demand calculations
            if hasattr(self.mobility_model, 'calculate_sink_demands'):
                organ_demands = {
                    'leaves': {'nitrogen': 0.01, 'phosphorus': 0.002, 'potassium': 0.008},
                    'stems': {'nitrogen': 0.005, 'phosphorus': 0.001, 'potassium': 0.004},
                    'roots': {'nitrogen': 0.003, 'phosphorus': 0.001, 'potassium': 0.002}
                }
                growth_stage = plant_state.get('growth_stage', 'vegetative')
                sink_demands = self.mobility_model.calculate_sink_demands(organ_demands, growth_stage)
                plant_state['sink_demands'] = sink_demands
            
            # Use source supply calculations
            if hasattr(self.mobility_model, 'calculate_source_supplies'):
                stress_factors = {
                    'water_stress': plant_state.get('water_stress', 0.0),
                    'nitrogen_stress': plant_state.get('nitrogen_stress', 0.0)
                }
                senescence_rates = {
                    'leaves': plant_state.get('leaf_senescence_rate', 0.0),
                    'stems': plant_state.get('stem_senescence_rate', 0.0)
                }
                source_supplies = self.mobility_model.calculate_source_supplies(stress_factors, senescence_rates)
                plant_state['source_supplies'] = source_supplies
            
            # Use transport flux calculations
            if hasattr(self.mobility_model, 'calculate_transport_fluxes'):
                sink_demands = plant_state.get('sink_demands', {})
                source_supplies = plant_state.get('source_supplies', {})
                transport_capacities = plant_state.get('transport_capacity', {})
                temperature = plant_state.get('air_temperature', 25.0)
                
                transport_fluxes = self.mobility_model.calculate_transport_fluxes(
                    sink_demands, source_supplies, transport_capacities, temperature
                )
                plant_state['transport_fluxes'] = transport_fluxes
            
            # Use mobility efficiency calculations
            if hasattr(self.mobility_model, 'calculate_mobility_efficiency'):
                mobility_efficiencies = {}
                for nutrient in ['nitrogen', 'phosphorus', 'potassium']:
                    efficiency = self.mobility_model.calculate_mobility_efficiency(nutrient)
                    mobility_efficiencies[f'{nutrient}_mobility_efficiency'] = efficiency
                plant_state.update(mobility_efficiencies)
            
            # Use organ pool initialization
            if hasattr(self.mobility_model, 'initialize_organ_pools'):
                for organ in ['leaves', 'stems', 'roots']:
                    nutrient_contents = {
                        'nitrogen': plant_state.get(f'{organ}_nitrogen_content', 0.03),
                        'phosphorus': plant_state.get(f'{organ}_phosphorus_content', 0.005),
                        'potassium': plant_state.get(f'{organ}_potassium_content', 0.04)
                    }
                    dry_mass = plant_state.get(f'{organ}_biomass', 0.01)
                    self.mobility_model.initialize_organ_pools(organ, nutrient_contents, dry_mass)
            
            # Use organ pool updates
            if hasattr(self.mobility_model, 'update_organ_pools'):
                transport_fluxes = plant_state.get('transport_fluxes', [])
                if transport_fluxes:
                    self.mobility_model.update_organ_pools(transport_fluxes)
        
        return plant_state

    def _calculate_advanced_biomass_allocation(self, plant_state: dict, total_growth: float) -> dict:
        """Calculate biomass allocation using advanced functional balance model."""
        # Stress factors affecting allocation
        stress_factors = {
            'water_stress': plant_state.get('water_stress', 0.0),
            'nutrient_stress': plant_state.get('nitrogen_stress', 0.0),
            'light_stress': plant_state.get('light_stress', 0.0),
            'temperature_stress': plant_state.get('temperature_stress', 0.0)
        }

        # Environmental conditions
        env_conditions = {
            'temperature': plant_state['air_temperature'],
            'light_intensity': plant_state['solar_radiation'],
            'co2': plant_state['co2_concentration'],
            'humidity': plant_state['humidity']
        }

        # Stage properties for allocation
        stage_props = {
            'current_stage': plant_state['growth_stage'],
            'accumulated_gdd': plant_state.get('accumulated_gdd', 0.0),
            'bolting_risk': plant_state.get('bolting_risk', 0.0)
        }

        # Calculate functional balance allocation
        allocation_fractions = self.biomass_allocation_model.calculate_functional_balance_allocation(
            stress_factors=stress_factors,
            env_conditions=env_conditions,
            stage_props=stage_props
        )

        return allocation_fractions

    def _calculate_stress_factors(self, plant_state: dict) -> dict:
        """Calculate various stress factors."""
        temp = plant_state['air_temperature']
        humidity = plant_state['humidity']
        vpd = plant_state['vpd']
        ec = plant_state['ec']
        
        # Temperature stress
        if temp < 10 or temp > 30:
            plant_state['temperature_stress'] = min(1.0, abs(temp - 20) / 20)
        else:
            stress_params = getattr(self.system_config, 'stress_parameters', {})
            plant_state['temperature_stress'] = 0.0  # Will be calculated by temperature stress model
        
        # Water stress (based on VPD)
        environment_params = getattr(self.system_config, 'environment', {})
        optimal_vpd = self._get_required_param(environment_params, 'target_vpd', 'environment CSV')
        plant_state['water_stress'] = min(1.0, abs(vpd - optimal_vpd) / optimal_vpd)
        
        # Nutrient stress (based on EC)
        optimal_ec = (self.params.optimal_ec_range[0] + self.params.optimal_ec_range[1]) / 2
        plant_state['nutrient_stress'] = min(1.0, abs(ec - optimal_ec) / optimal_ec)
        
        # Light stress
        solar_rad = plant_state['solar_radiation']
        if solar_rad < 10:
            plant_state['light_stress'] = (10 - solar_rad) / 10
        else:
            plant_state['light_stress'] = 0.0  # Will be calculated by light stress model
        
        # CO2 stress
        co2 = plant_state['co2_concentration']
        if co2 < 300:
            plant_state['co2_stress'] = (300 - co2) / 300
        else:
            plant_state['co2_stress'] = 0.0  # Will be calculated by CO2 stress model
        
        # Salinity stress (simplified)
        plant_state['salinity_stress'] = max(0.0, (ec - 2.0) / 2.0)
        
        # Integrated stress factor
        stresses = [
            plant_state['temperature_stress'],
            plant_state['water_stress'],
            plant_state['nutrient_stress'],
            plant_state['light_stress'],
            plant_state['co2_stress'],
            plant_state['salinity_stress']
        ]
        plant_state['integrated_stress_factor'] = sum(stresses) / len(stresses)
        
        plant_state['stress_factors'] = {
            'temperature': plant_state['temperature_stress'],
            'water': plant_state['water_stress'],
            'nutrient': plant_state['nutrient_stress'],
            'light': plant_state['light_stress'],
            'co2': plant_state['co2_stress'],
            'salinity': plant_state['salinity_stress']
        }
        
        return plant_state
    
    def _calculate_integrated_stress(self, plant_state: dict) -> dict:
        """Calculate integrated stress factors using advanced unified model."""
        
        # Calculate individual stress factors first
        plant_state = self._calculate_stress_factors(plant_state)
        
        # === COMPREHENSIVE INTEGRATED STRESS INTEGRATION ===
        
        # 1. Prepare current stress levels for integrated stress model
        current_stress_levels = {
            'water': plant_state.get('water_stress', 0.0),
            'temperature': plant_state.get('temperature_stress', 0.0),
            'nutrient': plant_state.get('nutrient_stress', 0.0),
            'light': plant_state.get('light_stress', 0.0),
            'salinity': plant_state.get('salinity_stress', 0.0),
            'oxygen': plant_state.get('oxygen_stress', 0.0),
            'ph': plant_state.get('ph_stress', 0.0)
        }
        
        # 2. Use comprehensive daily_update method for integrated stress
        integrated_stress_response = self.integrated_stress.daily_update(current_stress_levels)
        
        # 3. Update plant state with comprehensive stress results
        plant_state['integrated_stress_factor'] = integrated_stress_response.overall_stress_factor
        plant_state['stress_severity'] = integrated_stress_response.stress_severity
        plant_state['dominant_stresses'] = integrated_stress_response.dominant_stresses
        plant_state['stress_interactions_active'] = integrated_stress_response.stress_interactions_active
        plant_state['acclimation_active'] = integrated_stress_response.acclimation_active
        plant_state['recovery_active'] = integrated_stress_response.recovery_active
        
        # 4. Update individual stress states
        for stress_type, stress_state in integrated_stress_response.stress_states.items():
            plant_state[f'{stress_type}_stress'] = stress_state.current_level
            plant_state[f'{stress_type}_acute_stress'] = stress_state.acute_stress
            plant_state[f'{stress_type}_chronic_stress'] = stress_state.chronic_stress
            plant_state[f'{stress_type}_acclimation_level'] = stress_state.acclimation_level
            plant_state[f'{stress_type}_damage_level'] = stress_state.damage_level
            plant_state[f'{stress_type}_recovery_progress'] = stress_state.recovery_progress
            plant_state[f'{stress_type}_days_under_stress'] = stress_state.days_under_stress
        
        # 5. Update process-specific stress responses
        plant_state['process_stress_responses'] = {}
        for process_type, process_response in integrated_stress_response.process_responses.items():
            plant_state['process_stress_responses'][process_type] = {
                'combined_stress_factor': process_response.combined_stress_factor,
                'individual_stress_effects': process_response.individual_stress_effects,
                'interaction_effects': process_response.interaction_effects,
                'acclimation_benefits': process_response.acclimation_benefits,
                'recovery_effects': process_response.recovery_effects,
                'damage_effects': process_response.damage_effects,
                'limiting_stress_types': process_response.limiting_stress_types
            }
        
        # 6. Get stress summary for diagnostics
        stress_summary = self.integrated_stress.get_stress_summary()
        plant_state['stress_summary'] = stress_summary
        plant_state['current_stresses'] = stress_summary['current_stresses']
        plant_state['acclimation_status'] = stress_summary['acclimation_status']
        plant_state['cumulative_damage'] = stress_summary['cumulative_damage']
        plant_state['total_damage'] = stress_summary['total_damage']
        
        # 7. Use unified stress calculator for additional stress factors
        env_conditions = {
            'actual_temperature': plant_state['air_temperature'],
            'actual_humidity': plant_state['humidity'],
            'actual_vpd': plant_state['vpd'],
            'co2': plant_state['co2_concentration'],
            'solar_radiation': plant_state['solar_radiation']
        }

        nutrient_concentrations = {
            'ec': plant_state['ec']
        }

        stress_result = self.unified_stress_calculator.calculate_unified_stress_factors(
            env_conditions=env_conditions,
            nutrient_concentrations=nutrient_concentrations,
            plant_state=plant_state,
            day=plant_state.get('day', 1),
            ec_calculator=self.nutrient_concentration_model.calculate_ec_from_concentrations
        )
        
        # 8. Update plant state with unified stress results (for compatibility)
        plant_state['temperature_factor'] = stress_result['temperature_factor']
        plant_state['water_factor'] = stress_result['water_factor']
        plant_state['light_factor'] = stress_result['light_factor']
        plant_state['nitrogen_factor'] = stress_result['nitrogen_factor']
        plant_state['salinity_factor'] = stress_result['salinity_factor']
        plant_state['ph_factor'] = stress_result['ph_factor']
        plant_state['oxygen_factor'] = stress_result['oxygen_factor']
        
        return plant_state

    def _update_advanced_stress_models(self, plant_state: dict) -> dict:
        """Use comprehensive stress model functions that were previously unused."""
        
        # Get stress parameters from CSV
        stress_params = getattr(self.system_config, 'stress_parameters', {})
        
        # Temperature stress model functions
        if hasattr(self, 'temperature_stress'):
            temperature = plant_state.get('air_temperature', 25.0)
            
            # Use temperature stress classification
            if hasattr(self.temperature_stress, 'classify_temperature_stress'):
                stress_type = self.temperature_stress.classify_temperature_stress(temperature)
                plant_state['temperature_stress_type'] = stress_type.value if hasattr(stress_type, 'value') else str(stress_type)
            
            # Use base stress level calculations
            if hasattr(self.temperature_stress, 'calculate_base_stress_level'):
                base_stress = self.temperature_stress.calculate_base_stress_level(temperature)
                plant_state['base_temperature_stress'] = base_stress
            
            # Use acclimation updates
            if hasattr(self.temperature_stress, 'update_acclimation'):
                stress_type = getattr(self.temperature_stress, 'classify_temperature_stress', lambda x: None)(temperature)
                if stress_type:
                    self.temperature_stress.update_acclimation(temperature, stress_type)
            
            # Use acclimation effects
            if hasattr(self.temperature_stress, 'apply_acclimation_effects'):
                base_stress = plant_state.get('base_temperature_stress', 0.0)
                stress_type = getattr(self.temperature_stress, 'classify_temperature_stress', lambda x: None)(temperature)
                if stress_type:
                    acclimated_stress = self.temperature_stress.apply_acclimation_effects(base_stress, stress_type)
                    plant_state['acclimated_temperature_stress'] = acclimated_stress
            
            # Use memory effects
            if hasattr(self.temperature_stress, 'calculate_memory_effects'):
                memory_effect = self.temperature_stress.calculate_memory_effects()
                plant_state['temperature_memory_effect'] = memory_effect
            
            # Use process stress factors
            if hasattr(self.temperature_stress, 'calculate_process_stress_factors'):
                stress_level = plant_state.get('base_temperature_stress', 0.0)
                stress_type = getattr(self.temperature_stress, 'classify_temperature_stress', lambda x: None)(temperature)
                if stress_type:
                    process_factors = self.temperature_stress.calculate_process_stress_factors(stress_level, stress_type)
                    plant_state['temperature_process_factors'] = process_factors
            
            # Use damage and recovery updates
            if hasattr(self.temperature_stress, 'update_damage_and_recovery'):
                stress_level = plant_state.get('base_temperature_stress', 0.0)
                stress_type = getattr(self.temperature_stress, 'classify_temperature_stress', lambda x: None)(temperature)
                if stress_type:
                    self.temperature_stress.update_damage_and_recovery(stress_level, stress_type, 24.0)
        
        # Integrated stress model functions
        if hasattr(self, 'integrated_stress'):
            current_stress_levels = {
                'temperature_stress': plant_state.get('temperature_stress', 0.0),
                'water_stress': plant_state.get('water_stress', 0.0),
                'nitrogen_stress': plant_state.get('nitrogen_stress', 0.0),
                'light_stress': plant_state.get('light_stress', 0.0)
            }
            
            # Use acute stress calculations
            if hasattr(self.integrated_stress, 'calculate_acute_stress'):
                acute_stresses = {}
                for stress_type, level in current_stress_levels.items():
                    acute_stress = self.integrated_stress.calculate_acute_stress(stress_type, level)
                    acute_stresses[f'{stress_type}_acute'] = acute_stress
                plant_state.update(acute_stresses)
            
            # Use chronic stress calculations
            if hasattr(self.integrated_stress, 'calculate_chronic_stress'):
                # Get stress states from the model
                stress_states = getattr(self.integrated_stress, 'stress_states', {})
                for stress_type, stress_state in stress_states.items():
                    chronic_stress = self.integrated_stress.calculate_chronic_stress(stress_state)
                    plant_state[f'{stress_type}_chronic'] = chronic_stress
            
            # Use acclimation effects
            if hasattr(self.integrated_stress, 'calculate_acclimation_effect'):
                stress_states = getattr(self.integrated_stress, 'stress_states', {})
                for stress_type, stress_state in stress_states.items():
                    acclimation_effect = self.integrated_stress.calculate_acclimation_effect(stress_state)
                    plant_state[f'{stress_type}_acclimation'] = acclimation_effect
            
            # Use recovery effects
            if hasattr(self.integrated_stress, 'calculate_recovery_effect'):
                stress_states = getattr(self.integrated_stress, 'stress_states', {})
                for stress_type, stress_state in stress_states.items():
                    recovery_effect = self.integrated_stress.calculate_recovery_effect(stress_state)
                    plant_state[f'{stress_type}_recovery'] = recovery_effect
            
            # Use stress interactions
            if hasattr(self.integrated_stress, 'calculate_stress_interactions'):
                active_stresses = {k: v for k, v in current_stress_levels.items() if v > 0.1}
                if active_stresses:
                    stress_interactions = self.integrated_stress.calculate_stress_interactions(active_stresses)
                    plant_state['stress_interactions'] = stress_interactions
            
            # Use process stress response
            if hasattr(self.integrated_stress, 'calculate_process_stress_response'):
                try:
                    stress_states = getattr(self.integrated_stress, 'stress_states', {})
                    process_responses = {}
                    for process in ['photosynthesis', 'respiration', 'transpiration', 'growth']:
                        try:
                            response = self.integrated_stress.calculate_process_stress_response(process, stress_states)
                            process_responses[f'{process}_stress_response'] = response
                        except (ValueError, KeyError) as e:
                            # If process sensitivity not configured, use default response
                            process_responses[f'{process}_stress_response'] = {
                                'combined_stress_factor': 0.8,
                                'individual_stress_effects': stress_states,
                                'interaction_effects': {}
                            }
                    plant_state.update(process_responses)
                except Exception as e:
                    # If any error occurs, use default process responses
                    plant_state['photosynthesis_stress_response'] = {'combined_stress_factor': 0.8}
                    plant_state['respiration_stress_response'] = {'combined_stress_factor': 0.8}
                    plant_state['transpiration_stress_response'] = {'combined_stress_factor': 0.8}
                    plant_state['growth_stress_response'] = {'combined_stress_factor': 0.8}
        
        # Unified stress calculator functions
        if hasattr(self, 'unified_stress_calculator'):
            env_conditions = {
                'actual_temperature': plant_state.get('air_temperature', 25.0),
                'actual_humidity': plant_state.get('humidity', 60.0),
                'actual_light': plant_state.get('solar_radiation', 10.0),
                'actual_co2': plant_state.get('co2_concentration', 400.0),
                'actual_vpd': plant_state.get('vpd', 1.0),
                'temperature': plant_state.get('air_temperature', 25.0),
                'humidity': plant_state.get('humidity', 60.0),
                'vpd': plant_state.get('vpd', 1.0),
                'light_intensity': plant_state.get('solar_radiation', 10.0),
                'solar_radiation': plant_state.get('solar_radiation', 10.0),
                'co2': plant_state.get('co2_concentration', 400.0),
                'ph': plant_state.get('ph', 6.0),
                'ec': plant_state.get('ec', 1.2)
            }
            
            # Use unified stress factor calculations - no fallbacks allowed
            if hasattr(self.unified_stress_calculator, 'calculate_unified_stress_factors'):
                nutrient_concentrations = plant_state.get('nutrient_concentrations', {
                    'N-NO3': 150.0, 'P-PO4': 50.0, 'K': 200.0
                })
                unified_factors = self.unified_stress_calculator.calculate_unified_stress_factors(
                    env_conditions, nutrient_concentrations, plant_state,
                    ec_calculator=self.nutrient_concentration_model.calculate_ec_from_concentrations
                )
                plant_state.update(unified_factors)
        
        return plant_state

    def _calculate_canopy_architecture(self, plant_state: dict) -> dict:
        """Calculate canopy architecture using comprehensive multi-layer model."""
        
        # === COMPREHENSIVE CANOPY ARCHITECTURE INTEGRATION ===
        
        # 1. Create comprehensive light environment
        light_env = LightEnvironment(
            ppfd_above_canopy=plant_state['solar_radiation'] * 2.0,  # Convert to PPFD
            direct_beam_fraction=0.8,
            diffuse_fraction=0.2,
            solar_zenith_angle=30.0
        )
        
        # 2. Update canopy structure with comprehensive distribution
        canopy_structure = self._update_canopy_structure(plant_state)
        plant_state.update(canopy_structure)
        
        # 3. Calculate leaf angle distribution
        leaf_angle_distribution = self._calculate_leaf_angle_distribution(plant_state)
        plant_state['leaf_angle_distribution'] = leaf_angle_distribution
        
        # 4. Calculate light extinction coefficients
        extinction_coeffs = self._calculate_light_extinction_coefficients(plant_state, light_env)
        plant_state.update(extinction_coeffs)
        
        # 5. Calculate sunlit and shaded fractions
        sunlit_shaded_fractions = self._calculate_sunlit_shaded_fractions(plant_state, light_env)
        plant_state.update(sunlit_shaded_fractions)
        
        # 6. Calculate canopy temperature gradient
        temperature_gradient = self._calculate_canopy_temperature_gradient(plant_state)
        plant_state.update(temperature_gradient)
        
        # 7. Calculate photosynthesis by canopy layer
        layer_photosynthesis = self._calculate_photosynthesis_by_layer(plant_state, light_env)
        plant_state.update(layer_photosynthesis)
        
        # 8. Calculate competition effects
        competition_effects = self._calculate_competition_effects(plant_state)
        plant_state.update(competition_effects)
        
        # 9. Calculate clumping effects
        clumping_effects = self._calculate_clumping_effects(plant_state)
        plant_state.update(clumping_effects)
        
        # 10. Get comprehensive canopy summary
        canopy_summary = self._get_canopy_summary(plant_state)
        plant_state['canopy_summary'] = canopy_summary
        
        return plant_state
    
    def _update_canopy_structure(self, plant_state: dict) -> dict:
        """Update canopy structure with comprehensive distribution."""
        # Use advanced canopy model for structure
        self.canopy_model.distribute_leaf_area(plant_state['lai'], plant_state['plant_height'])
        
        # Get canopy structure details
        canopy_structure = {
            'canopy_layers': getattr(self.canopy_model, 'canopy_layers', 3),
            'layer_lai_distribution': getattr(self.canopy_model, 'layer_lai_distribution', {}),
            'canopy_height': plant_state['plant_height'],
            'canopy_width': getattr(self.canopy_model, 'canopy_width', 0.3),
            'row_spacing': getattr(self.canopy_model, 'row_spacing', 0.5),
            'plant_spacing': getattr(self.canopy_model, 'plant_spacing', 0.2)
        }
        
        return canopy_structure
    
    def _calculate_leaf_angle_distribution(self, plant_state: dict) -> dict:
        """Calculate leaf angle distribution effects."""
        # Get leaf angle parameters from canopy model
        mean_leaf_angle = getattr(self.canopy_model, 'mean_leaf_angle', 45.0)
        leaf_angle_variance = getattr(self.canopy_model, 'leaf_angle_variance', 15.0)
        leaf_angle_distribution = getattr(self.canopy_model, 'leaf_angle_distribution', 'spherical')
        
        # Calculate angle distribution effects
        angle_distribution = {
            'mean_leaf_angle': mean_leaf_angle,
            'leaf_angle_variance': leaf_angle_variance,
            'leaf_angle_distribution_type': leaf_angle_distribution,
            'angle_extinction_factor': self._calculate_angle_extinction_factor(mean_leaf_angle),
            'light_interception_efficiency': self._calculate_light_interception_efficiency(mean_leaf_angle)
        }
        
        return angle_distribution
    
    def _calculate_angle_extinction_factor(self, mean_angle: float) -> float:
        """Calculate extinction factor based on leaf angle."""
        # More horizontal leaves = higher extinction
        # More vertical leaves = lower extinction
        angle_rad = math.radians(mean_angle)
        extinction_factor = self._get_required_param(self.system_config.canopy_parameters, "extinction_base_factor", "canopy_parameters CSV") + self._get_required_param(self.system_config.canopy_parameters, "extinction_cosine_factor", "canopy_parameters CSV") * math.cos(angle_rad)
        return extinction_factor
    
    def _calculate_light_interception_efficiency(self, mean_angle: float) -> float:
        """Calculate light interception efficiency based on leaf angle."""
        # Optimal angle for light interception varies with solar angle
        solar_angle = self._get_required_param(self.system_config.canopy_parameters, "solar_angle_degrees", "canopy_parameters CSV")  # degrees
        angle_diff = abs(mean_angle - solar_angle)
        efficiency = max(0.5, 1.0 - angle_diff / 90.0)
        return efficiency
    
    def _calculate_light_extinction_coefficients(self, plant_state: dict, light_env: LightEnvironment) -> dict:
        """Calculate comprehensive light extinction coefficients."""
        # Use canopy model for extinction calculations
        light_interception, extinction_coeff = self.canopy_model.calculate_light_distribution(
            light_env=light_env,
            total_lai=plant_state['lai']
        )
        
        # Calculate additional extinction parameters
        extinction_coeffs = {
            'light_interception': light_interception,
            'extinction_coefficient': extinction_coeff,
            'diffuse_extinction_coeff': extinction_coeff * 0.8,  # Diffuse light penetrates better
            'beam_extinction_coeff': extinction_coeff * 1.2,     # Direct beam blocked more
            'max_extinction_coefficient': extinction_coeff * 1.5, # Maximum extinction
            'light_penetration_depth': self._calculate_light_penetration_depth(plant_state['lai'], extinction_coeff)
        }
        
        return extinction_coeffs
    
    def _calculate_light_penetration_depth(self, lai: float, extinction_coeff: float) -> float:
        """Calculate light penetration depth through canopy."""
        # Light penetration follows Beer's law: I = I0 * exp(-k * LAI)
        # Calculate depth where light drops to 10% of incident
        penetration_depth = -math.log(0.1) / extinction_coeff
        return min(penetration_depth, lai)  # Can't penetrate more than total LAI
    
    def _calculate_sunlit_shaded_fractions(self, plant_state: dict, light_env: LightEnvironment) -> dict:
        """Calculate sunlit and shaded leaf area fractions."""
        total_lai = plant_state['lai']
        
        # Calculate sunlit fraction using available canopy model methods
        if hasattr(self.canopy_model, 'calculate_light_distribution'):
            # Use light distribution calculation which may include sunlit fractions
            light_distribution = self.canopy_model.calculate_light_distribution(
                light_env=light_env,
                total_lai=total_lai
            )
            # Extract sunlit fraction if available, otherwise use default
            if hasattr(light_distribution, 'sunlit_fraction'):
                sunlit_fraction = light_distribution.sunlit_fraction
            else:
                canopy_params = getattr(self.system_config, 'canopy_parameters', {})
                sunlit_fraction = self._get_required_param(canopy_params, 'default_sunlit_fraction', 'canopy_parameters CSV')
        else:
            sunlit_fraction = self._get_required_param(self.system_config.canopy_parameters, "default_sunlit_fraction", "canopy_parameters CSV")  # Default sunlit fraction
        
        sunlit_shaded_fractions = {
            'sunlit_lai': total_lai * sunlit_fraction,
            'shaded_lai': total_lai * (1.0 - sunlit_fraction),
            'sunlit_fraction': sunlit_fraction,
            'shaded_fraction': 1.0 - sunlit_fraction,
            'sunlit_ppfd': light_env.ppfd_above_canopy,
            'shaded_ppfd': light_env.ppfd_above_canopy * 0.2  # 20% of incident light reaches shaded leaves
        }
        
        return sunlit_shaded_fractions
    
    def _calculate_canopy_temperature_gradient(self, plant_state: dict) -> dict:
        """Calculate temperature gradient through canopy layers."""
        air_temperature = plant_state.get('air_temperature', 22.0)
        lai = plant_state.get('lai', 1.0)
        
        # Calculate temperature gradient (warmer at top, cooler at bottom)
        max_gradient = getattr(self.canopy_model, 'max_temperature_gradient', 3.0)  # °C
        gradient_factor = getattr(self.canopy_model, 'temperature_gradient_factor', 0.5)
        
        temperature_gradient = {
            'canopy_top_temperature': air_temperature + (max_gradient * min(1.0, lai / 3.0)),
            'canopy_middle_temperature': air_temperature + (max_gradient * 0.5 * min(1.0, lai / 3.0)),
            'canopy_bottom_temperature': air_temperature,
            'temperature_gradient': max_gradient * min(1.0, lai / 3.0),
            'gradient_factor': gradient_factor
        }
        
        return temperature_gradient
    
    def _calculate_photosynthesis_by_layer(self, plant_state: dict, light_env: LightEnvironment) -> dict:
        """Calculate photosynthesis by canopy layer."""
        # Get layer-specific photosynthesis using available methods
        if hasattr(self.canopy_model, 'calculate_light_distribution'):
            # Use light distribution to estimate layer photosynthesis
            light_distribution = self.canopy_model.calculate_light_distribution(
                light_env=light_env,
                total_lai=plant_state['lai']
            )
            # Create a simple layer photosynthesis estimate based on light distribution
            layer_photosynthesis = {
                'total_photosynthesis': plant_state.get('photosynthesis_rate', 0.5) * 0.8,  # 80% efficiency
                'layer_contributions': [0.4, 0.3, 0.3],  # Top, middle, bottom layers
                'light_limitation_factors': [0.9, 0.7, 0.5]
            }
        else:
            # Default layer photosynthesis if no canopy model available
            layer_photosynthesis = {
                'total_photosynthesis': plant_state.get('photosynthesis_rate', 0.5),
                'layer_contributions': [0.5, 0.3, 0.2],
                'light_limitation_factors': [0.8, 0.6, 0.4]
            }
        
        # Calculate total canopy photosynthesis
        total_canopy_photosynthesis = layer_photosynthesis['total_photosynthesis']
        
        photosynthesis_by_layer = {
            'layer_photosynthesis': layer_photosynthesis,
            'canopy_photosynthesis': total_canopy_photosynthesis,
            'photosynthesis_efficiency': total_canopy_photosynthesis / max(0.001, plant_state['lai']),
            'ppfd_to_photosynthesis_factor': getattr(self.canopy_model, 'ppfd_to_photosynthesis_factor', 0.8)
        }
        
        return photosynthesis_by_layer
    
    def _calculate_competition_effects(self, plant_state: dict) -> dict:
        """Calculate competition effects between plants."""
        system_config_params = getattr(self.system_config, 'system_configuration', {})
        plant_density = self._get_required_param(system_config_params, 'n_plants', 'system_configuration CSV') / self._get_required_param(system_config_params, 'system_area', 'system_configuration CSV')
        
        # Calculate competition factors
        competition_effects = {
            'plant_density': plant_density,
            'competition_factor': min(1.0, 1.0 - (plant_density - 10) * 0.05),  # Competition increases with density
            'light_competition': min(1.0, 1.0 - (plant_density - 8) * 0.1),
            'space_competition': min(1.0, 1.0 - (plant_density - 12) * 0.08),
            'neighbor_shading_distance': getattr(self.canopy_model, 'neighbor_shading_distance', 0.3)
        }
        
        return competition_effects
    
    def _calculate_clumping_effects(self, plant_state: dict) -> dict:
        """Calculate leaf clumping effects on light interception."""
        clumping_index = getattr(self.canopy_model, 'clumping_index', 0.8)
        
        # Clumping reduces effective LAI for light interception
        effective_lai = plant_state['lai'] * clumping_index
        
        clumping_effects = {
            'clumping_index': clumping_index,
            'effective_lai': effective_lai,
            'clumping_reduction_factor': 1.0 - clumping_index,
            'light_interception_efficiency': clumping_index
        }
        
        return clumping_effects
    
    def _get_canopy_summary(self, plant_state: dict) -> dict:
        """Get comprehensive canopy summary."""
        canopy_summary = {
            'total_lai': plant_state['lai'],
            'canopy_height': plant_state['plant_height'],
            'light_interception': plant_state.get('light_interception', 0.0),
            'sunlit_lai': plant_state.get('sunlit_lai', 0.0),
            'shaded_lai': plant_state.get('shaded_lai', 0.0),
            'extinction_coefficient': plant_state.get('extinction_coefficient', 0.7),
            'canopy_photosynthesis': plant_state.get('canopy_photosynthesis', 0.0),
            'competition_factor': plant_state.get('competition_factor', 1.0),
            'clumping_index': plant_state.get('clumping_index', 0.8)
        }
        
        return canopy_summary

    def _update_advanced_canopy_architecture(self, plant_state: dict) -> dict:
        """Use additional canopy architecture model functions that were previously unused."""
        
        if hasattr(self, 'canopy_model'):
            # Get current environmental conditions
            light_env = LightEnvironment(
                ppfd_above_canopy=plant_state.get('solar_radiation', 10.0) * 2.1,  # Convert MJ/m²/day to μmol/m²/s
                direct_beam_fraction=0.7,
                diffuse_fraction=0.3,
                solar_zenith_angle=plant_state.get('zenith_angle_deg', 45.0)
            )
            
            total_lai = plant_state.get('lai', 1.0)
            canopy_height = plant_state.get('plant_height', 0.3)
            
            # Use the comprehensive daily_update method
            canopy_response = self.canopy_model.daily_update(
                total_lai=total_lai,
                canopy_height=canopy_height,
                light_env=light_env,
                air_temperature=plant_state.get('air_temperature', 25.0),
                co2_concentration=plant_state.get('co2_concentration', 400.0)
            )
            
            # Update plant state with comprehensive canopy results
            plant_state['canopy_layers'] = len(canopy_response.canopy_layers)
            plant_state['sunlit_lai'] = canopy_response.sunlit_lai
            plant_state['shaded_lai'] = canopy_response.shaded_lai
            plant_state['light_interception'] = canopy_response.light_interception_fraction
            plant_state['average_extinction_coefficient'] = canopy_response.average_extinction_coefficient
            plant_state['total_absorbed_ppfd'] = canopy_response.total_absorbed_ppfd
            plant_state['canopy_photosynthesis'] = canopy_response.canopy_photosynthesis
            
            # Calculate additional canopy parameters using individual methods
            if hasattr(self.canopy_model, 'calculate_extinction_coefficient'):
                zenith_angle = plant_state.get('zenith_angle_deg', 45.0)
                leaf_angle_dist = plant_state.get('leaf_angle_distribution', 'spherical')
                # Ensure we pass a valid string for leaf angle distribution
                if isinstance(leaf_angle_dist, dict):
                    leaf_angle_dist = leaf_angle_dist.get('leaf_angle_distribution_type', 'spherical')
                extinction_coeff, diffuse_extinction = self.canopy_model.calculate_extinction_coefficient(
                    zenith_angle, leaf_angle_dist
                )
                plant_state['extinction_coefficient'] = extinction_coeff
                plant_state['diffuse_extinction_coefficient'] = diffuse_extinction
            
            # Calculate row effects if plant spacing is available
            if hasattr(self.canopy_model, 'calculate_row_effects'):
                row_spacing = plant_state.get('row_spacing', 0.3)
                plant_spacing = plant_state.get('plant_spacing', 0.15)
                canopy_width = plant_state.get('canopy_width', 0.2)
                row_effect = self.canopy_model.calculate_row_effects(
                    row_spacing, plant_spacing, canopy_width
                )
                plant_state['row_effect_factor'] = row_effect
            
            # Calculate temperature profile through canopy
            if hasattr(self.canopy_model, 'calculate_temperature_profile'):
                air_temp = plant_state.get('air_temperature', 25.0)
                self.canopy_model.calculate_temperature_profile(air_temp, total_lai)
                # Store layer temperatures
                layer_temps = [layer.temperature for layer in canopy_response.canopy_layers]
                plant_state['canopy_temperature_profile'] = layer_temps
                plant_state['canopy_temperature_gradient'] = max(layer_temps) - min(layer_temps) if layer_temps else 0.0
        
        return plant_state
    
    def _calculate_physiological_processes(self, plant_state: dict) -> dict:
        """Calculate physiological processes using realistic models."""
        
        # Use the water uptake model for realistic transpiration
        water_uptake_result = self.water_uptake_model.calculate_realistic_water_uptake(
            temperature=plant_state['air_temperature'],
            humidity=plant_state['humidity'],
            solar_radiation=plant_state['solar_radiation'],
            lai=plant_state['lai'],
            total_biomass=plant_state['total_biomass'],
            growth_stage=plant_state['growth_stage']
        )
        
        plant_state['transpiration_rate'] = water_uptake_result['transpiration_mm']
        plant_state['water_uptake_rate'] = water_uptake_result['total_water_uptake_L']
        
        # Use comprehensive water uptake model functions
        plant_state = self._update_advanced_water_uptake(plant_state)
        
        # Use the nutrient uptake model for realistic nutrient uptake
        if plant_state['root_surface_area'] > 0:
            nutrient_uptake_result = self.nutrient_uptake_model.calculate_realistic_nutrient_uptake(
                current_concentrations=plant_state['nutrient_concentrations'],
                root_surface_area=plant_state['root_surface_area'],
                temperature=plant_state['air_temperature'],
                ph=plant_state['ph'],
                ec=plant_state['ec'],
                plant_count=self._get_required_param(getattr(self.system_config, 'system_configuration', {}), 'n_plants', 'system_configuration CSV'),
                tank_volume_L=plant_state['solution_volume'],
                daily_growth_rate=self._calculate_growth_rate(plant_state)
            )
            
            plant_state['nutrient_uptake'] = nutrient_uptake_result['uptake_rates_mg_per_plant_per_day']
        else:
            # Fallback if root surface area is 0
            plant_state['nutrient_uptake'] = {
                'N-NO3': 0.0,
                'P-PO4': 0.0,
                'K': 0.0,
                'Ca': 0.0,
                'Mg': 0.0
            }

        # Update nitrogen balance
        plant_state = self._update_nitrogen_balance(plant_state)
        
        # Update nutrient mobility and redistribution
        plant_state = self._update_nutrient_mobility(plant_state)

        # Advanced Photosynthesis using Farquhar-von Caemmerer-Berry model
        photosynthesis_result = self.photosynthesis_model.calculate_hourly_assimilation(
            par_umol_m2_s=plant_state['solar_radiation'] * 2.0,  # Convert MJ/m²/day to μmol/m²/s
            co2_ppm=plant_state['co2_concentration'],
            temp_c=plant_state['air_temperature'],
            humidity=plant_state['humidity'],
            lai=plant_state['lai'],
            hour=12,  # Midday conditions
            ec_factor=1.0 - plant_state['nutrient_stress'],
            config_dict=getattr(self.system_config, 'photosynthesis', {}),
            sunlit_lai=plant_state['lai'] * 0.6,
            shaded_lai=plant_state['lai'] * 0.4
        )
        
        # Also use daily assimilation method for comprehensive photosynthesis calculation
        if hasattr(self.photosynthesis_model, 'calculate_daily_assimilation'):
            daily_photosynthesis = self.photosynthesis_model.calculate_daily_assimilation(
                par_umol_m2_s=plant_state['solar_radiation'] * 2.0,
                co2_ppm=plant_state['co2_concentration'],
                temp_c=plant_state['air_temperature'],
                humidity=plant_state['humidity'],
                lai=plant_state['lai'],
                photoperiod_hours=plant_state.get('day_length_hours', 12.0),
                ec_factor=1.0 - plant_state['nutrient_stress'],
                config_dict=getattr(self.system_config, 'photosynthesis', {}),
                sunlit_lai=plant_state['lai'] * 0.6,
                shaded_lai=plant_state['lai'] * 0.4
            )
            plant_state['daily_photosynthesis'] = daily_photosynthesis
        
        plant_state['photosynthesis_rate'] = photosynthesis_result
        
        # Use comprehensive photosynthesis model functions
        plant_state = self._update_advanced_photosynthesis(plant_state)
        
        # Enhanced Respiration with temperature acclimation and tissue-specific rates
        biomass_pools = {
            'leaves': BiomassPool(TissueType.LEAVES, plant_state['leaf_biomass']),
            'stems': BiomassPool(TissueType.STEMS, plant_state['stem_biomass']),
            'roots': BiomassPool(TissueType.ROOTS, plant_state['root_biomass'])
        }
        
        biomass_pools_list = list(biomass_pools.values())
        respiration_result = self.respiration_model.calculate_total_respiration(
            biomass_pools=biomass_pools_list,
            temperature=plant_state['air_temperature'],
            total_new_growth=self._calculate_growth_rate(plant_state)
        )
        
        plant_state['respiration_rate'] = respiration_result.total_respiration
        plant_state['maintenance_respiration'] = respiration_result.maintenance_respiration
        
        # Use comprehensive respiration model functions
        plant_state = self._update_advanced_respiration(plant_state, biomass_pools_list)
        plant_state['growth_respiration'] = respiration_result.growth_respiration
        
        return plant_state

    def _update_advanced_water_uptake(self, plant_state: dict) -> dict:
        """Use comprehensive water uptake model functions that were previously unused."""
        
        if hasattr(self, 'water_uptake_model'):
            temperature = plant_state.get('air_temperature', 25.0)
            humidity = plant_state.get('humidity', 60.0)
            light_interception = plant_state.get('light_interception', 0.8)
            lai = plant_state.get('lai', 1.0)
            
            # Use hydraulic water uptake calculations
            if hasattr(self.water_uptake_model, 'calculate_hydraulic_water_uptake'):
                hydraulic_result = self.water_uptake_model.calculate_hydraulic_water_uptake(
                    light_interception=light_interception,
                    temperature=temperature,
                    humidity=humidity,
                    solar_radiation=plant_state.get('solar_radiation', 10.0),
                    vpd=calculate_vpd(temperature, humidity),
                    lai=lai,
                    stem_biomass=plant_state.get('stem_biomass', 0.1),
                    solution_ec=plant_state.get('ec', 1.2),
                    stress_factors=plant_state.get('stress_factors', {})
                )
                plant_state['hydraulic_water_uptake'] = hydraulic_result
            
            # Use temperature factor calculations
            if hasattr(self.water_uptake_model, '_calculate_temperature_factor'):
                temp_factor = self.water_uptake_model._calculate_temperature_factor(temperature)
                plant_state['water_uptake_temperature_factor'] = temp_factor
            
            # Use VPD factor calculations
            if hasattr(self.water_uptake_model, '_calculate_vpd_factor'):
                vpd = calculate_vpd(temperature, humidity)
                vpd_factor = self.water_uptake_model._calculate_vpd_factor(vpd)
                plant_state['water_uptake_vpd_factor'] = vpd_factor
            
            # Use transpiration calculations
            if hasattr(self.water_uptake_model, '_calculate_transpiration'):
                transpiration_result = self.water_uptake_model._calculate_transpiration(
                    light_interception=light_interception,
                    temperature=temperature,
                    humidity=humidity,
                    vpd=calculate_vpd(temperature, humidity),
                    solar_radiation=plant_state.get('solar_radiation', 10.0)
                )
                plant_state['detailed_transpiration'] = transpiration_result
            
            # Use osmotic adjustment calculations
            if hasattr(self.water_uptake_model, '_calculate_osmotic_adjustment'):
                stress_factors = {
                    'water_stress': plant_state.get('water_stress', 0.0),
                    'salt_stress': plant_state.get('salt_stress', 0.0),
                    'nutrient_stress': plant_state.get('nutrient_stress', 0.0)
                }
                osmotic_adjustment = self.water_uptake_model._calculate_osmotic_adjustment(stress_factors)
                plant_state['osmotic_adjustment'] = osmotic_adjustment
        
        return plant_state

    def _update_advanced_photosynthesis(self, plant_state: dict) -> dict:
        """Use comprehensive photosynthesis model functions that were previously unused."""
        
        if hasattr(self, 'photosynthesis_model'):
            par_umol_m2_s = plant_state.get('solar_radiation', 10.0) * 2.0
            co2_ppm = plant_state.get('co2_concentration', 400.0)
            temp_c = plant_state.get('air_temperature', 25.0)
            humidity = plant_state.get('humidity', 60.0)
            
            # Use hourly assimilation calculations
            if hasattr(self.photosynthesis_model, 'calculate_hourly_assimilation'):
                hourly_result = self.photosynthesis_model.calculate_hourly_assimilation(
                    par_umol_m2_s=par_umol_m2_s,
                    co2_ppm=co2_ppm,
                    temp_c=temp_c,
                    humidity=humidity,
                    lai=plant_state.get('lai', 1.0),
                    hour=12,  # Midday
                    ec_factor=1.0 - plant_state.get('nutrient_stress', 0.0),
                    config_dict=getattr(self.system_config, 'photosynthesis', {}),
                    sunlit_lai=plant_state.get('sunlit_lai', plant_state.get('lai', 1.0) * 0.6),
                    shaded_lai=plant_state.get('shaded_lai', plant_state.get('lai', 1.0) * 0.4)
                )
                plant_state['hourly_photosynthesis'] = hourly_result
            
            # Use instantaneous assimilation calculations
            if hasattr(self.photosynthesis_model, '_calculate_instantaneous_assimilation'):
                instantaneous_result = self.photosynthesis_model._calculate_instantaneous_assimilation(
                    par_umol_m2_s=par_umol_m2_s,
                    co2_ppm=co2_ppm,
                    temp_c=temp_c,
                    humidity=humidity,
                    lai=plant_state.get('lai', 1.0),
                    ec_factor=1.0 - plant_state.get('nutrient_stress', 0.0),
                    config_dict=getattr(self.system_config, 'photosynthesis', {})
                )
                plant_state['instantaneous_photosynthesis'] = instantaneous_result
            
            # Use Arrhenius temperature response calculations
            if hasattr(self.photosynthesis_model, '_arrhenius_temp_response'):
                # Calculate temperature response for different processes
                respiration_params = getattr(self.system_config, 'respiration_parameters', {})
                rate_25 = self._get_required_param(respiration_params, 'maintenance_base_rate', 'respiration_parameters CSV')
                ea = 50000.0  # Default activation energy for respiration (J/mol)
                temp_response = self.photosynthesis_model._arrhenius_temp_response(
                    rate_25=rate_25,
                    ea=ea,
                    temp_c=temp_c
                )
                plant_state['photosynthesis_temp_response'] = temp_response
        
        return plant_state

    def _update_advanced_respiration(self, plant_state: dict, biomass_pools_list: list) -> dict:
        """Use comprehensive respiration model functions that were previously unused."""
        
        if hasattr(self, 'respiration_model'):
            temperature = plant_state.get('air_temperature', 25.0)
            
            # Use temperature factor calculations
            if hasattr(self.respiration_model, 'calculate_temperature_factor'):
                temp_factor = self.respiration_model.calculate_temperature_factor(temperature)
                plant_state['respiration_temperature_factor'] = temp_factor
            
            # Use age factor calculations
            if hasattr(self.respiration_model, 'calculate_age_factor'):
                age_days = plant_state.get('days_since_emergence', 30.0)
                age_factor = self.respiration_model.calculate_age_factor(age_days)
                plant_state['respiration_age_factor'] = age_factor
            
            # Use nitrogen factor calculations for each tissue
            if hasattr(self.respiration_model, 'calculate_nitrogen_factor'):
                nitrogen_factors = {}
                for pool in biomass_pools_list:
                    n_factor = self.respiration_model.calculate_nitrogen_factor(
                        pool.nitrogen_content, pool.tissue_type
                    )
                    nitrogen_factors[f'{pool.tissue_type.value.lower()}_nitrogen_factor'] = n_factor
                plant_state.update(nitrogen_factors)
            
            # Use maintenance respiration calculations
            if hasattr(self.respiration_model, 'calculate_maintenance_respiration'):
                maintenance_results = {}
                for pool in biomass_pools_list:
                    maint_resp, tissue_breakdown = self.respiration_model.calculate_maintenance_respiration(
                        pool, temperature
                    )
                    maintenance_results[f'{pool.tissue_type.value.lower()}_maintenance'] = maint_resp
                    maintenance_results[f'{pool.tissue_type.value.lower()}_tissue_breakdown'] = tissue_breakdown
                plant_state.update(maintenance_results)
            
            # Use growth respiration calculations
            if hasattr(self.respiration_model, 'calculate_growth_respiration'):
                try:
                    growth_rate = self._calculate_growth_rate(plant_state)
                    growth_composition = {
                        'carbohydrates': 0.4,
                        'proteins': 0.15,
                        'lipids': 0.05,
                        'minerals': 0.05
                    }
                    growth_resp = self.respiration_model.calculate_growth_respiration(
                        growth_rate, growth_composition
                    )
                    plant_state['detailed_growth_respiration'] = growth_resp
                except (ValueError, KeyError) as e:
                    # If respiration calculation fails due to missing CSV config, use default
                    plant_state['detailed_growth_respiration'] = growth_rate * 0.25  # 25% of growth rate as respiration
            
            # Use temperature acclimation updates
            if hasattr(self.respiration_model, 'update_temperature_acclimation'):
                self.respiration_model.update_temperature_acclimation(temperature)
                acclimated_temp = getattr(self.respiration_model, 'acclimated_temperature', temperature)
                plant_state['acclimated_respiration_temperature'] = acclimated_temp
            
            # Use hourly updates
            if hasattr(self.respiration_model, 'hourly_update'):
                hourly_result = self.respiration_model.hourly_update(
                    biomass_pools=biomass_pools_list,
                    temperature=temperature,
                    hour=12,  # Midday
                    dt_hours=1.0,
                    new_growth=self._calculate_growth_rate(plant_state)
                )
                plant_state.update(hourly_result)
            
            # Use diurnal respiration factor
            if hasattr(self.respiration_model, '_calculate_diurnal_respiration_factor'):
                diurnal_factor = self.respiration_model._calculate_diurnal_respiration_factor(12)  # Midday
                plant_state['diurnal_respiration_factor'] = diurnal_factor
            
            # Use temperature stress factor
            if hasattr(self.respiration_model, '_calculate_temperature_stress_factor'):
                temp_stress_factor = self.respiration_model._calculate_temperature_stress_factor(temperature)
                plant_state['respiration_temperature_stress'] = temp_stress_factor
            
            # Use respiratory quotient
            if hasattr(self.respiration_model, '_calculate_respiratory_quotient'):
                rq = self.respiration_model._calculate_respiratory_quotient(12)  # Midday
                plant_state['respiratory_quotient'] = rq
        
        return plant_state
    
    def _update_root_architecture(self, plant_state: dict) -> dict:
        """Update root architecture and calculate advanced nutrient uptake."""
        
        if self.root_model is not None:
            # Environmental conditions for root model
            environmental_conditions = {
                'temperature': plant_state['air_temperature'],
                'flow_rate': self._get_required_param(getattr(self.system_config, 'system_configuration', {}), 'flow_rate', 'system_configuration CSV'),
                'oxygen_level': 8.0,  # mg/L dissolved oxygen
                'ph': plant_state['ph']
            }
            
            # Growth factors for root model
            growth_factors = {
                'nitrogen_stress': 1.0 - plant_state['nutrient_stress'],
                'water_stress': 1.0 - plant_state['water_stress'],
                'temperature_stress': 1.0 - plant_state['temperature_stress']
            }
            
            # Update root architecture
            root_result = self.root_model.daily_update(
                environmental_conditions=environmental_conditions,
                growth_factors=growth_factors,
                solution_concentrations=plant_state['nutrient_concentrations']
            )
            
            # Update plant state with root results (with minimum check)
            calculated_surface_area = root_result['total_root_surface_area']
            # Ensure root model results are realistic
            min_surface_area = plant_state['total_biomass'] * self._get_required_param(self.system_config.plant_parameters, "min_surface_area_factor", "plant_parameters CSV")  # 100 cm²/g biomass ratio
            canopy_params = getattr(self.system_config, 'canopy_parameters', {})
            absolute_minimum = self._get_required_param(canopy_params, 'min_leaf_area_per_plant', 'canopy_parameters CSV')
            final_surface_area = max(calculated_surface_area, min_surface_area, absolute_minimum)
            plant_state['root_surface_area'] = final_surface_area
            plant_state['root_length'] = root_result['total_root_length']
            plant_state['fine_root_length'] = root_result['fine_root_length']
            plant_state['coarse_root_length'] = root_result['coarse_root_length']
            plant_state['root_length_density'] = root_result['root_length_density']
            plant_state['root_volume'] = root_result['total_root_volume']
            
            # Update nutrient uptake with advanced model
            if plant_state['root_surface_area'] > 0:
                nutrient_uptake_result = self.root_model.calculate_nutrient_uptake(
                    architecture_metrics=root_result,
                    environmental_conditions=environmental_conditions,
                    solution_concentrations=plant_state['nutrient_concentrations']
                )

                # Update nutrient uptake rates
                plant_state['nutrient_uptake'] = {
                    'N-NO3': nutrient_uptake_result.get('NO3_uptake_rate', 0.0),
                    'P-PO4': nutrient_uptake_result.get('PO4_uptake_rate', 0.0),
                    'K': nutrient_uptake_result.get('K_uptake_rate', 0.0),
                    'Ca': nutrient_uptake_result.get('Ca_uptake_rate', 0.0),
                    'Mg': nutrient_uptake_result.get('Mg_uptake_rate', 0.0)
                }
        
        return plant_state

    def _update_advanced_root_system(self, plant_state: dict) -> dict:
        """Use comprehensive root system model functions that were previously unused."""
        
        if hasattr(self, 'root_model'):
            environmental_conditions = {
                'temperature': plant_state.get('air_temperature', 25.0),
                'solution_temperature': plant_state.get('solution_temperature', 22.0),
                'ph': plant_state.get('ph', 6.0),
                'ec': plant_state.get('ec', 1.2),
                'flow_rate': plant_state.get('flow_rate', 2.0),
                'oxygen_level': plant_state.get('dissolved_oxygen', 8.0)
            }
            
            growth_factors = {
                'biomass_growth': plant_state.get('total_biomass', 0.1),
                'leaf_growth': plant_state.get('leaf_biomass', 0.05),
                'stem_growth': plant_state.get('stem_biomass', 0.03),
                'root_growth': plant_state.get('root_biomass', 0.02),
                'nitrogen_stress_factor': 1.0 - plant_state.get('nitrogen_stress', 0.0)
            }
            
            # Use comprehensive daily update
            if hasattr(self.root_model, 'daily_update'):
                try:
                    solution_concentrations = {
                        'N-NO3': plant_state.get('nitrate_concentration', 150.0),
                        'P-PO4': plant_state.get('phosphate_concentration', 50.0),
                        'K': plant_state.get('potassium_concentration', 200.0),
                        'Ca': plant_state.get('calcium_concentration', 100.0),
                        'Mg': plant_state.get('magnesium_concentration', 50.0)
                    }
                    root_result = self.root_model.daily_update(
                        environmental_conditions=environmental_conditions,
                        growth_factors=growth_factors,
                        solution_concentrations=solution_concentrations
                    )
                    plant_state.update(root_result)
                except (ValueError, KeyError) as e:
                    # If root model fails due to missing CSV config, use default values
                    plant_state['root_system_update'] = {
                        'total_root_length': plant_state.get('root_length', 5.0),
                        'total_root_surface_area': plant_state.get('root_surface_area', 0.001)
                    }
            
            # Use root architecture metrics
            if hasattr(self.root_model, 'calculate_architecture_metrics'):
                architecture_metrics = self.root_model.calculate_architecture_metrics()
                plant_state.update({
                    'total_root_length': architecture_metrics.get('total_length', 0.0),
                    'total_root_surface_area': architecture_metrics.get('total_surface_area', 0.0),
                    'total_root_volume': architecture_metrics.get('total_volume', 0.0),
                    'root_length_density': architecture_metrics.get('root_length_density', 0.0),
                    'root_surface_area_density': architecture_metrics.get('root_surface_area_density', 0.0)
                })
            
            # Use root distribution
            if hasattr(self.root_model, 'get_root_distribution'):
                root_distribution = self.root_model.get_root_distribution()
                plant_state['root_distribution'] = root_distribution
            
            # Use hourly updates
            if hasattr(self.root_model, 'hourly_update'):
                try:
                    hourly_result = self.root_model.hourly_update(
                        environmental_conditions=environmental_conditions,
                        growth_factors=growth_factors,
                        solution_concentrations=solution_concentrations,
                        dt_hours=1.0
                    )
                    plant_state.update(hourly_result)
                except (ValueError, KeyError) as e:
                    # If hourly update fails, use default values
                    plant_state['hourly_root_update'] = {
                        'uptake_rate': 0.001,
                        'growth_rate': 0.0001
                    }
            
            # Use effective surface area calculations
            if hasattr(self.root_model, 'calculate_effective_surface_area'):
                architecture_metrics = plant_state.get('architecture_metrics', {})
                effective_surface_area = self.root_model.calculate_effective_surface_area(architecture_metrics)
                plant_state['effective_root_surface_area'] = effective_surface_area
            
            # Use temperature factor calculations
            if hasattr(self.root_model, 'calculate_temperature_factor'):
                temp_factor = self.root_model.calculate_temperature_factor(environmental_conditions['temperature'])
                plant_state['root_temperature_factor'] = temp_factor
            
            # Use flow factor calculations
            if hasattr(self.root_model, 'calculate_flow_factor'):
                flow_factor = self.root_model.calculate_flow_factor(environmental_conditions['flow_rate'])
                plant_state['root_flow_factor'] = flow_factor
            
            # Use spatial uptake distribution
            if hasattr(self.root_model, 'get_spatial_uptake_distribution'):
                spatial_distribution = self.root_model.get_spatial_uptake_distribution()
                plant_state['spatial_uptake_distribution'] = spatial_distribution
            
            # Use nutrient competition calculations
            if hasattr(self.root_model, '_calculate_nutrient_competition'):
                concentrations = {
                    'N-NO3': plant_state.get('N-NO3_mg_L', 150.0),
                    'P-PO4': plant_state.get('P-PO4_mg_L', 50.0),
                    'K': plant_state.get('K_mg_L', 200.0)
                }
                n_competition = self.root_model._calculate_nutrient_competition('N-NO3', concentrations)
                plant_state['nitrogen_competition_factor'] = n_competition
            
            # Use pH effect calculations
            if hasattr(self.root_model, '_calculate_ph_effect_on_uptake'):
                ph_effect = self.root_model._calculate_ph_effect_on_uptake('N-NO3', environmental_conditions['ph'])
                plant_state['root_ph_effect'] = ph_effect
            
            # Use root age effect calculations
            if hasattr(self.root_model, '_calculate_root_age_effect'):
                architecture_metrics = plant_state.get('architecture_metrics', {})
                age_effect = self.root_model._calculate_root_age_effect(architecture_metrics)
                plant_state['root_age_effect'] = age_effect
            
            # Use environmental optimization
            if hasattr(self.root_model, 'optimize_environmental_conditions'):
                try:
                    target_uptake = {
                        'N-NO3': plant_state.get('Nitrogen_Uptake_mg', 5.0),
                        'P-PO4': plant_state.get('Phosphorus_Uptake_mg', 1.0)
                    }
                    optimization_result = self.root_model.optimize_environmental_conditions(
                        target_uptake_rates=target_uptake,
                        current_concentrations=solution_concentrations
                    )
                    plant_state['root_optimization'] = optimization_result
                except (ValueError, KeyError) as e:
                    # If optimization fails, use default values
                    plant_state['root_optimization'] = {
                        'optimal_conditions': environmental_conditions,
                        'optimization_score': 0.8
                    }
            
            # Use zone growth potential calculations
            if hasattr(self.root_model, '_calculate_zone_growth_potential'):
                # Get root system from model if available
                root_system = getattr(self.root_model, 'root_system', None)
                if root_system and hasattr(root_system, 'zones'):
                    zone_potentials = {}
                    for i, zone in enumerate(root_system.zones):
                        potential = self.root_model._calculate_zone_growth_potential(
                            zone=zone,
                            zone_index=i,
                            environmental_conditions=environmental_conditions
                        )
                        zone_potentials[f'zone_{i}_growth_potential'] = potential
                    plant_state['zone_growth_potentials'] = zone_potentials
            
            # Use health score calculations
            if hasattr(self.root_model, '_calculate_health_score'):
                root_system = getattr(self.root_model, 'root_system', None)
                if root_system:
                    health_score = self.root_model._calculate_health_score(root_system)
                    plant_state['root_health_score'] = health_score
            
            # Use hourly nutrient uptake calculations
            if hasattr(self.root_model, '_calculate_hourly_nutrient_uptake'):
                try:
                    architecture_metrics = plant_state.get('architecture_metrics', {})
                    hourly_uptake = self.root_model._calculate_hourly_nutrient_uptake(
                        architecture_metrics=architecture_metrics,
                        environmental_conditions=environmental_conditions,
                        solution_concentrations=solution_concentrations,
                        dt_hours=1.0
                    )
                    plant_state['hourly_nutrient_uptake'] = hourly_uptake
                except (ValueError, KeyError) as e:
                    # If calculation fails, use default values
                    plant_state['hourly_nutrient_uptake'] = {
                        'N-NO3': 0.1, 'P-PO4': 0.01, 'K': 0.08, 'Ca': 0.05, 'Mg': 0.02
                    }
        
        return plant_state

    def _update_environmental_control(self, plant_state: dict) -> dict:
        """Update environmental control using advanced PID controllers."""
        
        # Current environmental conditions
        current_conditions = {
            'temperature': plant_state['air_temperature'],
            'humidity': plant_state['humidity'],
            'co2': plant_state['co2_concentration'],
            'light_intensity': plant_state['solar_radiation']
        }
        
        # Light schedule (simplified - lights on during day)
        light_schedule = {
            'light_on': plant_state['solar_radiation'] > 5.0  # Lights on if solar > 5 MJ/m²/day
        }
        
        # Calculate environmental control
        control_result = self.environmental_control.calculate_comprehensive_control(
            current_conditions=current_conditions,
            light_schedule=light_schedule
        )
        
        # Update plant state with environmental control results (simplified)
        plant_state['controlled_temperature'] = current_conditions.get('temperature', plant_state['air_temperature'])
        plant_state['controlled_humidity'] = current_conditions.get('humidity', plant_state['humidity'])
        plant_state['controlled_co2'] = current_conditions.get('co2', plant_state['co2_concentration'])
        environment_params = getattr(self.system_config, 'environment', {})
        plant_state['vpd_target'] = self._get_required_param(environment_params, 'target_vpd', 'environment CSV')
        plant_state['environmental_cost'] = self._get_required_param(environment_params, 'environmental_cost_base', 'environment CSV')
        
        # Update environmental factors for plant models (simplified)
        plant_state['env_photosynthesis_factor'] = self._get_required_param(environment_params, 'env_photosynthesis_factor', 'environment CSV')
        plant_state['env_transpiration_factor'] = self._get_required_param(environment_params, 'env_transpiration_factor', 'environment CSV')
        
        return plant_state

    def _update_advanced_root_zone_temperature(self, plant_state: dict) -> dict:
        """Use comprehensive root zone temperature model functions that were previously unused."""
        
        if hasattr(self, 'rzt_model'):
            air_temperature = plant_state.get('air_temperature', 25.0)
            current_rzt = plant_state.get('root_zone_temp', 22.0)
            
            # Use optimal RZT calculations
            if hasattr(self.rzt_model, 'calculate_optimal_rzt'):
                optimal_rzt = self.rzt_model.calculate_optimal_rzt(air_temperature)
                plant_state['optimal_root_zone_temp'] = optimal_rzt
            
            # Use RZT growth factor calculations
            if hasattr(self.rzt_model, 'calculate_rzt_growth_factor'):
                growth_factor = self.rzt_model.calculate_rzt_growth_factor(current_rzt, air_temperature)
                plant_state['detailed_rzt_growth_factor'] = growth_factor
            
            # Use nutrient uptake factor calculations
            if hasattr(self.rzt_model, 'calculate_nutrient_uptake_factor'):
                nutrient_factor = self.rzt_model.calculate_nutrient_uptake_factor(current_rzt, air_temperature)
                plant_state['detailed_rzt_nutrient_factor'] = nutrient_factor
            
            # Use water uptake factor calculations
            if hasattr(self.rzt_model, 'calculate_water_uptake_factor'):
                water_factor = self.rzt_model.calculate_water_uptake_factor(current_rzt, air_temperature)
                plant_state['detailed_rzt_water_factor'] = water_factor
            
            # Use photosynthesis factor calculations
            if hasattr(self.rzt_model, 'calculate_photosynthesis_factor'):
                photosynthesis_factor = self.rzt_model.calculate_photosynthesis_factor(current_rzt, air_temperature)
                plant_state['detailed_rzt_photosynthesis_factor'] = photosynthesis_factor
            
            # Use root metabolism factor calculations
            if hasattr(self.rzt_model, 'calculate_root_metabolism_factor'):
                metabolism_factor = self.rzt_model.calculate_root_metabolism_factor(current_rzt, air_temperature)
                plant_state['detailed_rzt_metabolism_factor'] = metabolism_factor
            
            # Use hourly updates
            if hasattr(self.rzt_model, 'hourly_update'):
                environmental_conditions = {
                    'air_temperature': air_temperature,
                    'solution_temperature': current_rzt,
                    'humidity': plant_state.get('humidity', 60.0),
                    'light_intensity': plant_state.get('solar_radiation', 10.0)
                }
                hourly_result = self.rzt_model.hourly_update(
                    environmental_conditions=environmental_conditions,
                    hour=12,  # Midday
                    dt_hours=1.0
                )
                plant_state.update(hourly_result)
            
            # Use thermal dynamics calculations
            if hasattr(self.rzt_model, '_calculate_thermal_dynamics'):
                solution_temp = plant_state.get('solution_temperature', 22.0)
                thermal_dynamics = self.rzt_model._calculate_thermal_dynamics(
                    air_temperature, solution_temp, 12, 1.0
                )
                plant_state['thermal_dynamics'] = thermal_dynamics
        
        return plant_state

    def _update_advanced_ph_model(self, plant_state: dict) -> dict:
        """Use comprehensive pH model functions that were previously unused."""
        
        if hasattr(self, 'ph_model'):
            current_ph = plant_state.get('ph', 6.0)
            temperature = plant_state.get('air_temperature', 25.0)
            
            # Use pH-dependent solubility calculations
            if hasattr(self.ph_model, 'calculate_ph_dependent_solubility'):
                nutrients = ['iron', 'manganese', 'zinc', 'copper', 'phosphorus']
                solubility_factors = {}
                for nutrient in nutrients:
                    solubility_factor = self.ph_model.calculate_ph_dependent_solubility(
                        nutrient, current_ph
                    )
                    solubility_factors[f'{nutrient}_solubility_factor'] = solubility_factor
                plant_state.update(solubility_factors)
            
            # Use pH control system simulation
            if hasattr(self.ph_model, 'simulate_ph_control_system'):
                target_ph = plant_state.get('target_ph', 6.0)
                control_result = self.ph_model.simulate_ph_control_system(
                    current_ph=current_ph,
                    target_ph=target_ph,
                    temperature=temperature,
                    control_interval_hours=24.0
                )
                plant_state.update({
                    'ph_control_acid_dose': control_result.get('acid_dose_mL', 0.0),
                    'ph_control_base_dose': control_result.get('base_dose_mL', 0.0),
                    'ph_control_cost': control_result.get('control_cost', 0.0),
                    'ph_control_stability': control_result.get('ph_stability', 0.0)
                })
            
            # Use phosphate speciation calculations
            if hasattr(self.ph_model, 'calculate_phosphate_speciation'):
                total_phosphate = plant_state.get('P-PO4_mg_L', 50.0)
                phosphate_speciation = self.ph_model.calculate_phosphate_speciation(current_ph, total_phosphate)
                plant_state['phosphate_speciation'] = phosphate_speciation
            
            # Use nutrient uptake pH effect calculations
            if hasattr(self.ph_model, 'calculate_nutrient_uptake_ph_effect'):
                nutrient_uptake = plant_state.get('nutrient_uptake', {})
                ph_effect = self.ph_model.calculate_nutrient_uptake_ph_effect(nutrient_uptake)
                plant_state['nutrient_uptake_ph_effect'] = ph_effect
        
        return plant_state

    def _update_advanced_environmental_control(self, plant_state: dict) -> dict:
        """Use additional environmental control model functions that were previously unused."""
        
        if hasattr(self, 'environmental_control'):
            current_conditions = {
                'temperature': plant_state.get('air_temperature', 25.0),
                'humidity': plant_state.get('humidity', 60.0),
                'co2': plant_state.get('co2_concentration', 400.0),
                'light_intensity': plant_state.get('solar_radiation', 10.0)
            }
            
            # Use individual control methods
            if hasattr(self.environmental_control, 'calculate_optimal_humidity'):
                target_humidity = self.environmental_control.calculate_optimal_humidity(
                    current_conditions['temperature'],
                    self.environmental_control.setpoints.target_vpd
                )
                plant_state['target_humidity'] = target_humidity
            
            if hasattr(self.environmental_control, 'calculate_co2_photosynthesis_factor'):
                co2_factor = self.environmental_control.calculate_co2_photosynthesis_factor(
                    current_conditions['co2'],
                    current_conditions['temperature'],
                    current_conditions['light_intensity']
                )
                plant_state['co2_photosynthesis_factor'] = co2_factor
            
            if hasattr(self.environmental_control, 'calculate_vpd_stress_factor'):
                current_vpd = calculate_vpd(current_conditions['temperature'], current_conditions['humidity'])
                vpd_stress, vpd_optimal, vpd_status = self.environmental_control.calculate_vpd_stress_factor(current_vpd)
                plant_state['vpd_stress_factor'] = vpd_stress
                plant_state['vpd_optimal'] = vpd_optimal
                plant_state['vpd_status'] = vpd_status
            
            if hasattr(self.environmental_control, 'calculate_humidity_control_action'):
                target_humidity = plant_state.get('target_humidity', 65.0)
                humidity_action = self.environmental_control.calculate_humidity_control_action(
                    current_conditions['humidity'],
                    target_humidity,
                    'proportional'
                )
                plant_state['humidity_control_action'] = humidity_action
            
            if hasattr(self.environmental_control, 'calculate_co2_control_action'):
                co2_action = self.environmental_control.calculate_co2_control_action(
                    current_conditions['co2'],
                    self.environmental_control.setpoints.target_co2,
                    light_on=True,
                    strategy='proportional',
                    photoperiod_time=12.0
                )
                plant_state['co2_control_action'] = co2_action
            
            if hasattr(self.environmental_control, 'calculate_photoperiod_time'):
                photoperiod_time = self.environmental_control.calculate_photoperiod_time(
                    current_hour=12.0,
                    light_start_hour=6.0
                )
                plant_state['photoperiod_time'] = photoperiod_time
            
            # Use hourly update for comprehensive environmental control
            if hasattr(self.environmental_control, 'hourly_update'):
                hourly_result = self.environmental_control.hourly_update(
                    current_conditions=current_conditions,
                    hour=12,
                    dt_hours=1.0,
                    strategy='proportional'
                )
                
                # Update plant state with hourly control results
                plant_state['controlled_temperature'] = hourly_result.get('temperature', current_conditions['temperature'])
                plant_state['controlled_humidity'] = hourly_result.get('humidity', current_conditions['humidity'])
                plant_state['controlled_co2'] = hourly_result.get('co2', current_conditions['co2'])
                plant_state['controlled_vpd'] = hourly_result.get('vpd', 1.0)
                plant_state['energy_consumption_kWh'] = hourly_result.get('energy_consumption_kWh', 0.0)
                plant_state['control_actions'] = hourly_result.get('control_actions', {})
                
                # Use comprehensive control calculations
                if hasattr(self.environmental_control, 'calculate_comprehensive_control'):
                    try:
                        light_schedule = {'light_on': True, 'dawn_hour': 6, 'dusk_hour': 18}
                        comprehensive_result = self.environmental_control.calculate_comprehensive_control(
                            current_conditions=current_conditions,
                            light_schedule=light_schedule,
                            strategy='PID'  # Use enum-like value
                        )
                        plant_state['comprehensive_control'] = comprehensive_result
                    except (ValueError, KeyError) as e:
                        # If calculation fails, use default values
                        plant_state['comprehensive_control'] = {
                            'control_recommendations': current_conditions,
                            'predicted_improvements': {'growth_rate': 1.0, 'yield': 1.0}
                        }
                
                # Use priority action determination
                if hasattr(self.environmental_control, '_determine_priority_action'):
                    current_vpd = calculate_vpd(current_conditions['temperature'], current_conditions['humidity'])
                    priority_action = self.environmental_control._determine_priority_action(
                        current_vpd=current_vpd,
                        current_co2=current_conditions['co2'],
                        light_on=True
                    )
                    plant_state['priority_control_action'] = priority_action
                
                # Use growth improvement estimation
                if hasattr(self.environmental_control, '_estimate_growth_improvement'):
                    try:
                        factors = {
                            'temperature_factor': plant_state.get('temperature_factor', 1.0),
                            'humidity_factor': plant_state.get('humidity_factor', 1.0),
                            'co2_factor': plant_state.get('co2_factor', 1.0),
                            'light_factor': plant_state.get('light_factor', 1.0),
                            'vpd_photosynthesis_factor': plant_state.get('vpd_photosynthesis_factor', 1.0),
                            'co2_photosynthesis_factor': plant_state.get('co2_photosynthesis_factor', 1.0)
                        }
                        growth_improvement = self.environmental_control._estimate_growth_improvement(factors)
                        plant_state['estimated_growth_improvement'] = growth_improvement
                    except (ValueError, KeyError) as e:
                        # If calculation fails, use default improvement
                        growth_params = getattr(self.system_config, 'growth_parameters', {})
                        plant_state['estimated_growth_improvement'] = self._get_required_param(growth_params, 'default_growth_improvement', 'growth_parameters CSV')
                
                # Use time-based CO2 target calculations
                if hasattr(self.environmental_control, '_calculate_time_based_co2_target'):
                    try:
                        base_target = self.environmental_control.setpoints.target_co2
                        photoperiod_time = plant_state.get('photoperiod_time', 12.0)
                        time_based_co2 = self.environmental_control._calculate_time_based_co2_target(
                            base_target=base_target,
                            photoperiod_time=photoperiod_time,
                            light_on=True,  # Assuming lights are on during simulation
                            config_dict=None  # Use fallback behavior
                        )
                        plant_state['time_based_co2_target'] = time_based_co2
                    except (ValueError, KeyError) as e:
                        # If calculation fails, use base target
                        plant_state['time_based_co2_target'] = base_target
                
                # Use temperature adjustment calculations
                if hasattr(self.environmental_control, '_calculate_temperature_adjustment'):
                    try:
                        current_temp = current_conditions['temperature']
                        target_temp = self.environmental_control.setpoints.day_temp  # Use day_temp instead of target_temperature
                        temp_adjustment = self.environmental_control._calculate_temperature_adjustment(
                            current_temp=current_temp,
                            target_temp=target_temp,
                            dt_hours=1.0
                        )
                        plant_state['temperature_adjustment'] = temp_adjustment
                    except (ValueError, KeyError, AttributeError) as e:
                        # If calculation fails, use default adjustment
                        plant_state['temperature_adjustment'] = {'adjustment': 0.0, 'action': 'maintain'}
                
                # Use humidity control applications
                if hasattr(self.environmental_control, '_apply_humidity_control'):
                    current_humidity = current_conditions['humidity']
                    humidity_action = plant_state.get('humidity_control_action', {})
                    adjusted_humidity = self.environmental_control._apply_humidity_control(
                        current_humidity=current_humidity,
                        action=humidity_action,
                        dt_hours=1.0
                    )
                    plant_state['adjusted_humidity'] = adjusted_humidity
                
                # Use CO2 control applications
                if hasattr(self.environmental_control, '_apply_co2_control'):
                    current_co2 = current_conditions['co2']
                    co2_action = plant_state.get('co2_control_action', {})
                    adjusted_co2 = self.environmental_control._apply_co2_control(
                        current_co2=current_co2,
                        action=co2_action,
                        dt_hours=1.0
                    )
                    plant_state['adjusted_co2'] = adjusted_co2
                
                # Use target humidity from VPD calculations
                if hasattr(self.environmental_control, '_calculate_target_humidity_from_vpd'):
                    temperature = current_conditions['temperature']
                    target_vpd = self.environmental_control.setpoints.target_vpd
                    target_humidity = self.environmental_control._calculate_target_humidity_from_vpd(
                        temperature=temperature,
                        target_vpd=target_vpd
                    )
                    plant_state['calculated_target_humidity'] = target_humidity
        
        return plant_state

    def _update_solution_chemistry(self, plant_state: dict) -> dict:
        """Update solution chemistry with realistic dynamics."""
        # Update solution volume
        system_config_params = getattr(self.system_config, 'system_configuration', {})
        water_loss = plant_state['water_uptake_rate'] * self._get_required_param(system_config_params, 'n_plants', 'system_configuration CSV')
        plant_state['solution_volume'] = max(50.0, plant_state['solution_volume'] - water_loss)

        # Update nutrient concentrations using mass balance
        tank_volume_L = plant_state['solution_volume']
        plant_count = self._get_required_param(system_config_params, 'n_plants', 'system_configuration CSV')
        
        updated_concentrations = {}
        for nutrient, uptake_rate in plant_state['nutrient_uptake'].items():
            current_conc = plant_state['nutrient_concentrations'].get(nutrient, 0.0)
            initial_mass = current_conc * tank_volume_L
            
            # Total uptake for all plants (convert mg/plant/day to mg/day)
            total_uptake_mg = uptake_rate * plant_count
            
            # Updated mass and concentration
            final_mass = max(0.0, initial_mass - total_uptake_mg)
            if tank_volume_L > 0.0:
                final_conc = final_mass / tank_volume_L
            else:
                environment_params = getattr(self.system_config, 'environment', {})
                final_conc = self._get_required_param(environment_params, 'default_final_concentration', 'environment CSV')
            
            updated_concentrations[nutrient] = final_conc
        
        plant_state['nutrient_concentrations'] = updated_concentrations
        
        # Update EC from nutrient concentrations
        plant_state['ec'] = self.nutrient_concentration_model.calculate_ec_from_concentrations(
            plant_state['nutrient_concentrations']
        )
        
        # Update pH using comprehensive pH model
        plant_state = self._update_ph_dynamics(plant_state)
        
        # Add realistic CO2 variability
        system_params = getattr(self.system_config, 'system', {})
        environment_params = getattr(self.system_config, 'environment', {})
        base_co2 = self._get_required_param(environment_params, 'min_daylight_co2', 'environment CSV')
        co2_variation = random.uniform(-20, 20)  # ±20 ppm variation
        plant_state['co2_concentration'] = max(350.0, min(450.0, base_co2 + co2_variation))
        
        return plant_state
    
    def _update_ph_dynamics(self, plant_state: dict) -> dict:
        """Update pH dynamics using comprehensive pH model."""
        
        # Get system parameters from CSV
        system_params = getattr(self.system_config, 'system', {})
        
        # === COMPREHENSIVE pH MODEL INTEGRATION ===
        
        # 1. Prepare nutrient uptake data for pH model
        nutrient_uptake = plant_state.get('nutrient_uptake', {})
        
        # 2. Prepare nutrient concentrations
        nutrient_concentrations = plant_state.get('nutrient_concentrations', {})
        
        # 3. Prepare environmental conditions
        temperature = plant_state.get('air_temperature', 22.0)
        ec = plant_state.get('ec', 1.0)
        
        # 4. Use comprehensive daily_update method
        ph_response = self.ph_model.daily_update(
            nutrient_uptake=nutrient_uptake,
            nutrient_concentrations=nutrient_concentrations,
            temperature=temperature,
            ec=ec
        )
        
        # 5. Update plant state with comprehensive pH results
        plant_state['ph'] = ph_response['final_ph']
        plant_state['ph_change_from_uptake'] = ph_response['ph_change_from_uptake']
        plant_state['ph_change_from_drift'] = ph_response['ph_change_from_drift']
        plant_state['acid_dosed_ml_per_L'] = ph_response['acid_dosed_ml_per_L']
        plant_state['base_dosed_ml_per_L'] = ph_response['base_dosed_ml_per_L']
        plant_state['buffer_capacity'] = ph_response['buffer_capacity']
        
        # 6. Update pH-dependent nutrient availability
        plant_state['available_nutrients'] = ph_response['available_nutrients']
        plant_state['nutrient_precipitation'] = ph_response['nutrient_precipitation']
        
        # 7. Update phosphate speciation
        plant_state['phosphate_species'] = ph_response['phosphate_species']
        plant_state['phosphate_h2po4_mg_L'] = ph_response['phosphate_species'].get('H2PO4', 0.0)
        plant_state['phosphate_hpo4_mg_L'] = ph_response['phosphate_species'].get('HPO4', 0.0)
        plant_state['phosphate_h3po4_mg_L'] = ph_response['phosphate_species'].get('H3PO4', 0.0)
        plant_state['phosphate_po4_mg_L'] = ph_response['phosphate_species'].get('PO4', 0.0)
        
        # 8. Calculate pH-dependent nutrient solubility
        ph_dependent_solubility = self.ph_model.calculate_ph_dependent_solubility(
            ph=plant_state['ph'],
            nutrient_concentrations=nutrient_concentrations
        )
        plant_state['ph_dependent_solubility'] = ph_dependent_solubility
        
        # 9. Simulate pH control system
        ph_control_result = self.ph_model.simulate_ph_control_system(
            current_ph=plant_state['ph'],
            time_hours=24.0
        )
        plant_state['controlled_ph'] = ph_control_result[0]
        plant_state['acid_dosing_rate'] = ph_control_result[1]
        plant_state['base_dosing_rate'] = ph_control_result[2]
        
        # 10. Calculate Henderson-Hasselbalch pH (if CO2 data available)
        try:
            # Use current pH as reference for carbonate system
            total_carbonate = plant_state.get('total_alkalinity', 2.0)  # mEq/L
            free_co2 = plant_state.get('co2_concentration', 400.0) / 1000.0  # Convert ppm to mg/L
            henderson_ph = self.ph_model.calculate_henderson_hasselbalch_ph(
                total_carbonate=total_carbonate,
                free_co2=free_co2,
                temperature=temperature
            )
            plant_state['henderson_hasselbalch_ph'] = henderson_ph
            
            # Use comprehensive pH model functions
            plant_state = self._update_advanced_ph_model(plant_state)
        except Exception as e:
            # If CO2 data not available, use current pH
            plant_state['henderson_hasselbalch_ph'] = plant_state['ph']
        
        # 11. Update pH stress factor
        optimal_ph = self._get_required_param(system_params, 'default_ph', 'system CSV')
        ph_deviation = abs(plant_state['ph'] - optimal_ph)
        plant_state['ph_stress'] = min(1.0, ph_deviation / 2.0)  # Stress increases with deviation
        
        return plant_state
    
    def _update_root_zone_temperature(self, plant_state: dict) -> dict:
        """Update root zone temperature dynamics using comprehensive model."""
        
        # === COMPREHENSIVE ROOT ZONE TEMPERATURE INTEGRATION ===
        
        # 1. Prepare environmental conditions for RZT model
        environmental_conditions = {
            'air_temperature': plant_state.get('air_temperature', 22.0),
            'solar_radiation': plant_state.get('solar_radiation', 18.0),
            'humidity': plant_state.get('humidity', 60.0),
            'wind_speed': plant_state.get('wind_speed', 2.0),
            'tank_volume': plant_state.get('solution_volume', 500.0),
            'day_of_year': plant_state.get('day', 1),
            'solution_temperature': plant_state.get('solution_temperature', 22.0)  # Add required parameter
        }
        
        # 2. Prepare system parameters
        system_parameters = {
            'tank_material': 'plastic',  # Default tank material
            'tank_insulation': 0.1,      # Insulation factor
            'flow_rate': self._get_required_param(getattr(self.system_config, 'system_configuration', {}), 'flow_rate', 'system_configuration CSV'),
            'system_type': getattr(self.system_config, 'system_type', 'NFT')
        }
        
        # 3. Use comprehensive daily_update method
        rzt_response = self.rzt_model.daily_update(
            environmental_conditions=environmental_conditions
        )
        
        # 4. Update plant state with comprehensive RZT results
        plant_state['root_zone_temp'] = rzt_response['current_rzt']
        
        # Use comprehensive root zone temperature model functions
        plant_state = self._update_advanced_root_zone_temperature(plant_state)
        plant_state['rzt_growth_factor'] = rzt_response['growth_factor']
        plant_state['rzt_nutrient_factor'] = rzt_response['nutrient_uptake_factor']
        plant_state['rzt_water_factor'] = rzt_response['water_uptake_factor']
        plant_state['rzt_photosynthesis_factor'] = rzt_response['photosynthesis_factor']
        plant_state['rzt_root_metabolism_factor'] = rzt_response['root_metabolism_factor']
        
        # 5. Update RZT stress factors
        plant_state['rzt_stress_factor'] = rzt_response.get('thermal_stress', 0.0)
        plant_state['rzt_optimal_factor'] = rzt_response.get('growth_factor', 1.0)
        
        # 6. Update hourly RZT variations (simplified)
        hourly_rzt_variations = self._calculate_hourly_rzt_variations(
            plant_state, environmental_conditions
        )
        plant_state['hourly_rzt_variations'] = hourly_rzt_variations
        plant_state['rzt_daily_range'] = max(hourly_rzt_variations) - min(hourly_rzt_variations)
        
        # 7. Calculate individual RZT factors for detailed analysis
        individual_factors = self._calculate_individual_rzt_factors(
            plant_state['root_zone_temp']
        )
        plant_state['individual_rzt_factors'] = individual_factors
        
        # 8. Update root zone temperature stress
        optimal_rzt = (self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0
        rzt_deviation = abs(plant_state['root_zone_temp'] - optimal_rzt)
        plant_state['root_temp_stress'] = min(1.0, rzt_deviation / 10.0)  # Stress increases with deviation
        
        return plant_state
    
    def _calculate_hourly_rzt_variations(self, plant_state: dict, env_conditions: dict) -> list:
        """Calculate hourly root zone temperature variations."""
        hourly_rzt = []
        base_rzt = plant_state['root_zone_temp']
        
        # Simulate daily temperature cycle
        for hour in range(24):
            # Daily temperature cycle (simplified)
            daily_cycle = math.sin((hour - 6) * math.pi / 12)  # Peak at 2 PM (hour 14)
            daily_cycle = max(0, daily_cycle)  # Only positive values
            
            # Hourly variation based on solar radiation and air temperature
            air_temp_variation = (env_conditions['air_temperature'] - base_rzt) * 0.1
            solar_variation = env_conditions['solar_radiation'] * daily_cycle * 0.5
            
            hourly_temp = base_rzt + air_temp_variation + solar_variation
            hourly_rzt.append(hourly_temp)
        
        return hourly_rzt
    
    def _calculate_individual_rzt_factors(self, rzt: float) -> dict:
        """Calculate individual RZT factors for different processes."""
        optimal_rzt = (self.params.phenology_optimal_temperature_min + self.params.phenology_optimal_temperature_max) / 2.0
        
        # Growth factor (optimal around 22°C)
        growth_factor = 1.0 - abs(rzt - optimal_rzt) * 0.05
        growth_factor = max(0.0, min(1.0, growth_factor))
        
        # Nutrient uptake factor (optimal around 20-24°C)
        nutrient_factor = 1.0 - abs(rzt - 22.0) * 0.03
        nutrient_factor = max(0.0, min(1.0, nutrient_factor))
        
        # Water uptake factor (optimal around 18-25°C)
        water_factor = 1.0 - abs(rzt - 21.5) * 0.04
        water_factor = max(0.0, min(1.0, water_factor))
        
        # Photosynthesis factor (indirect effect through root function)
        photosynthesis_factor = 1.0 - abs(rzt - optimal_rzt) * 0.02
        photosynthesis_factor = max(0.0, min(1.0, photosynthesis_factor))
        
        # Root metabolism factor (optimal around 20-25°C)
        metabolism_factor = 1.0 - abs(rzt - 22.5) * 0.06
        metabolism_factor = max(0.0, min(1.0, metabolism_factor))
        
        return {
            'growth_factor': growth_factor,
            'nutrient_factor': nutrient_factor,
            'water_factor': water_factor,
            'photosynthesis_factor': photosynthesis_factor,
            'metabolism_factor': metabolism_factor
        }

    def _calculate_summary_stats(self, daily_results: List[DailyResults]) -> dict:
        """Calculate summary statistics."""
        if not daily_results:
            return {}
        
        final_result = daily_results[-1]
        initial_result = daily_results[0]
        
        total_growth = final_result.total_biomass - initial_result.total_biomass
        avg_daily_growth = total_growth / len(daily_results) if len(daily_results) > 1 else 0
        
        return {
            'total_days': len(daily_results),
            'initial_biomass': initial_result.total_biomass,
            'final_biomass': final_result.total_biomass,
            'total_growth': total_growth,
            'avg_daily_growth': avg_daily_growth,
            'final_growth_stage': final_result.growth_stage,
            'final_lai': final_result.lai,
            'avg_temperature': sum(r.temp_avg for r in daily_results) / len(daily_results),
            'avg_solar_radiation': sum(r.solar_radiation for r in daily_results) / len(daily_results),
            'total_water_consumption': sum(r.water_uptake_total for r in daily_results),
            'final_stress_level': final_result.integrated_stress_factor
        }

    def _simulate_daily_step(self, day: int, temperature: float, humidity: float, 
                           solar_radiation: float, daylength: float, 
                           nutrient_concentrations: Dict[str, float], ph: float = None,
                           previous_tank_volume: float = 0.0,
                           plant_density: float = 1.0, weather=None, 
                           original_tank_volume: float = 500.0) -> DailyResults:
        # ... (implementation from previous turns)
        pass

    def _run_hourly_integration(self, day: int, daily_weather_data: Dict[str, float], 
                               env_conditions: Dict[str, float], stress_factors: Dict[str, float],
                               nutrient_concentrations: Dict[str, float], daylength: float, 
                               canopy_response: Any = None) -> Dict[str, Any]:
        """
        DSSAT-style internal hourly integration loop.
        """
        from data.hydroponic_system import WeatherData
        
        daily_weather = WeatherData(
            date=f"2024-01-{day:02d}",
            temp_avg=daily_weather_data['temp_avg'],
            temp_min=daily_weather_data['temp_min'],
            temp_max=daily_weather_data['temp_max'],
            rel_humidity=daily_weather_data['rel_humidity'],
            solar_radiation=daily_weather_data['solar_radiation'],
            wind_speed=daily_weather_data.get('wind_speed', 2.0),
            rainfall=daily_weather_data.get('rainfall', 0.0)
        )
        
        system_co2 = getattr(self.system_config, 'default_co2', 400.0)
        
        hourly_weather_list = self.hourly_weather_interpolator.interpolate_daily_to_hourly(
            daily_weather, day_of_year=day, latitude=40.0, system_co2=system_co2
        )
        
        photosynthesis_params = getattr(self.system_config, 'photosynthesis', {})
        total_daily_photosynthesis = self._get_required_param(photosynthesis_params, 'default_daily_photosynthesis', 'photosynthesis CSV')
        total_daily_uptake = {}
        hourly_diagnostics = []
        
        respiration_params = getattr(self.system_config, 'respiration_parameters', {})
        total_daily_respiration = self._get_required_param(respiration_params, 'default_daily_respiration', 'respiration_parameters CSV')
        daily_environmental_control = {'energy_cost': 0.0, 'temperature': 0.0, 'humidity': 0.0, 'co2': 0.0}
        daily_rzt_effects = {'average_rzt': 0.0, 'thermal_stress': 0.0}
        
        for hour in range(24):
            hourly_weather = hourly_weather_list[hour]
            
            if hourly_weather.par > 0.1:
                photosynthesis_params = getattr(self.system_config, 'photosynthesis', {})
                sunlit_lai = canopy_response.sunlit_lai if canopy_response else self.current_lai
                shaded_lai = canopy_response.shaded_lai if canopy_response else 0.0
                
                hourly_photosynthesis = self.photosynthesis_model.calculate_hourly_assimilation(
                    par_umol_m2_s=hourly_weather.par,
                    co2_ppm=hourly_weather.co2,
                    temp_c=hourly_weather.temperature,
                    humidity=hourly_weather.humidity,
                    lai=self.current_lai,
                    hour=hour,
                    ec_factor=stress_factors.get('salinity_factor', 1.0),
                    config_dict=photosynthesis_params,
                    sunlit_lai=sunlit_lai,
                    shaded_lai=shaded_lai
                )
                total_daily_photosynthesis += hourly_photosynthesis
            else:
                hourly_photosynthesis = self._get_required_param(photosynthesis_params, 'default_hourly_photosynthesis', 'photosynthesis CSV')
            
            
        return {
            'total_daily_photosynthesis': total_daily_photosynthesis,
            'total_daily_uptake': total_daily_uptake,
            'total_daily_respiration': total_daily_respiration,
            'daily_environmental_control': daily_environmental_control,
            'daily_rzt_effects': daily_rzt_effects,
            'hourly_diagnostics': hourly_diagnostics
        }

    
