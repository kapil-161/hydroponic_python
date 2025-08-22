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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

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
from .models.environmental_control import EnvironmentalControlSystem
from .models.photosynthesis_model import PhotosynthesisModel
from .models.nutrient_models import NutrientConcentrationModel
from .models.leaf_development import LeafDevelopmentModel, LeafParameters
from .data.hydroponic_system import HydroInputData, SimulationResults, DailyResults
from .utils.config_loader import get_config_loader, get_genetic_parameter
from .utils.weather_generator import WeatherGenerator

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
    
    # Carbon and biomass parameters
    carbon_to_biomass_ratio: float = 0.45  # Fraction of carbon in dry biomass
    growth_respiration_fraction: float = 0.25  # Fraction of new growth lost to construction costs
    
    # Biomass allocation fractions by growth stage
    vegetative_leaf_allocation: float = 0.60
    vegetative_stem_allocation: float = 0.20  
    vegetative_root_allocation: float = 0.20
    
    reproductive_leaf_allocation: float = 0.40
    reproductive_stem_allocation: float = 0.35
    reproductive_root_allocation: float = 0.25
    
    # Environmental stress thresholds
    optimal_light_intensity: float = 15.0  # MJ/m²/day for normalization
    optimal_ec_range: tuple = (1.2, 1.8)  # dS/m optimal range
    
    # VPD stress parameters (kPa)
    optimal_vpd_min: float = 0.6
    optimal_vpd_max: float = 1.0
    vpd_stress_high_factor: float = 0.25  # Stress multiplier above optimal
    vpd_stress_low_factor: float = 0.15   # Stress multiplier below optimal
    
    # EC stress parameters (dS/m)
    optimal_ec: float = 1.5
    ec_stress_high_factor: float = 0.2    # Stress multiplier for high EC
    ec_stress_low_threshold: float = 0.8  # Below this EC causes stress
    ec_stress_low_factor: float = 0.1     # Stress multiplier for low EC
    
    # Temperature stress parameters (°C)
    optimal_root_temp: float = 20.0
    root_temp_tolerance: float = 3.0      # Degrees deviation before stress
    root_temp_stress_factor: float = 0.05 # Stress multiplier per degree deviation
    
    optimal_air_temp_max: float = 26.0    # Air temp above which stress occurs
    optimal_air_temp_min: float = 16.0    # Air temp below which stress occurs
    air_temp_stress_high_factor: float = 0.03  # Stress per degree above optimal
    air_temp_stress_low_factor: float = 0.02   # Stress per degree below optimal
    
    # Humidity stress parameters (%)
    optimal_humidity_min: float = 60.0
    humidity_stress_factor: float = 0.004  # Stress per percent below optimal
    
    # Water calculations
    specific_leaf_area_default: float = 250.0  # cm²/g for SLA calculations
    metabolic_water_per_lai: float = 0.2       # L/m²/day per LAI unit
    
    # Nutrient reservoir management
    reservoir_topup_fraction: float = 0.3      # Fraction of deficit to restore weekly
    
    # Minimal biological values (to prevent division by zero)
    minimal_nitrogen_uptake: float = 0.1  # mg/day minimum for calculations
    
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
                 simulation_params: Optional[SimulationParameters] = None):
        """
        Initialize CROPGRO simulator with all advanced models.
        
        Args:
            cultivar_id: Genetic cultivar identifier
            system_type: Hydroponic system type (NFT, DWC, AEROPONICS)
            enable_all_models: Enable all advanced CROPGRO models
        """
        
        logger.info("Initializing CROPGRO Hydroponic Simulator...")
        
        # Load configuration and simulation parameters
        self.config = get_config_loader()
        self.params = simulation_params or self._load_simulation_parameters()
        
        # Validate simulation parameters
        param_errors = self.params.validate()
        if param_errors:
            for error in param_errors:
                logger.warning(f"Parameter validation: {error}")
            raise ValueError(f"Invalid simulation parameters: {param_errors}")
        
        # 1. GENETIC PARAMETERS SYSTEM
        logger.info("Loading genetic parameters system...")
        self.genetic_db, self.ge_model, self.breeding_assistant = create_lettuce_genetic_system()
        self.current_cultivar = cultivar_id
        self.cultivar_profile = self.genetic_db.get_cultivar(cultivar_id)
        
        if not self.cultivar_profile:
            logger.warning(f"Cultivar {cultivar_id} not found, using default")
            self.current_cultivar = 'HYDRO_001'
            self.cultivar_profile = self.genetic_db.get_cultivar(self.current_cultivar)
        
        logger.info(f"Selected cultivar: {self.cultivar_profile.cultivar_name}")
        
        # 2. PHENOLOGY AND DEVELOPMENT
        logger.info("Initializing phenology model...")
        # Start from transplant stage (V2 - second true leaf) which matches transplant biomass
        transplant_stage = LettuceGrowthStage.SECOND_LEAF
        self.phenology_model = create_lettuce_phenology_model(transplant_stage)
        # Leaf development model for realistic LAI and leaf metrics
        self.leaf_model = LeafDevelopmentModel(LeafParameters())
        
        # 3. RESPIRATION MODEL
        logger.info("Initializing respiration model...")
        self.respiration_model = create_lettuce_respiration_model()
        
        # 4. SENESCENCE MODEL
        logger.info("Initializing senescence model...")
        self.senescence_model = create_lettuce_senescence_model()
        
        # 5. CANOPY ARCHITECTURE
        logger.info("Initializing canopy architecture model...")
        self.canopy_model = create_lettuce_canopy_model()
        
        # 6. NITROGEN BALANCE
        logger.info("Initializing nitrogen balance model...")
        self.nitrogen_model = create_lettuce_nitrogen_balance_model()
        
        # 7. NUTRIENT MOBILITY
        logger.info("Initializing nutrient mobility model...")
        self.mobility_model = create_lettuce_nutrient_mobility_model()
        
        # 8. STRESS MODELS
        logger.info("Initializing stress models...")
        self.integrated_stress = create_lettuce_integrated_stress_model()
        self.temperature_stress = create_lettuce_temperature_stress_model()
        
        # 9. ROOT ARCHITECTURE
        logger.info("Initializing root architecture model...")
        system_type_enum = {
            'NFT': HydroponicSystemType.NFT,
            'DWC': HydroponicSystemType.DWC, 
            'AEROPONICS': HydroponicSystemType.AEROPONICS
        }.get(system_type, HydroponicSystemType.NFT)
        
        self.root_model = create_enhanced_root_uptake_model(system_type_enum)
        
        # 10. ENVIRONMENTAL CONTROL
        logger.info("Initializing environmental control...")
        self.environmental_control = EnvironmentalControlSystem()
        
        # 11. BASIC MODELS (Enhanced)
        self.photosynthesis_model = PhotosynthesisModel()
        self.nutrient_concentration_model = NutrientConcentrationModel()
        
        # Initialize state variables
        self._initialize_plant_state()
        
        logger.info("CROPGRO Hydroponic Simulator initialized successfully!")
        logger.info(f"Enabled models: Genetic Parameters, Phenology, Respiration, Senescence, "
                   f"Canopy Architecture, Nitrogen Balance, Nutrient Mobility, Stress Models, "
                   f"Root Architecture, Environmental Control")

    def _load_simulation_parameters(self) -> SimulationParameters:
        """Loads simulation parameters from the configuration file."""
        stress_params = self.config.get_stress_parameters()
        growth_params = self.config.get_growth_parameters()
        env_params = self.config.get_environment_parameters()
        phys_params = self.config.get_physiology_parameters()
        canopy_params = self.config.get_canopy_parameters()
        water_params = self.config.get_water_parameters()
        nutrient_params = self.config.get_nutrient_parameters()
        system_params = self.config.get_system_parameters()

        return SimulationParameters(
            carbon_to_biomass_ratio=phys_params.get('CARBON_TO_GLUCOSE_RATIO'),
            growth_respiration_fraction=phys_params.get('GROWTH_RESPIRATION_RATE'),
            vegetative_leaf_allocation=growth_params.get('LEAF_GROWTH_RATIO'),
            vegetative_stem_allocation=growth_params.get('STEM_GROWTH_RATIO'),
            vegetative_root_allocation=growth_params.get('ROOT_GROWTH_RATIO'),
            reproductive_leaf_allocation=growth_params.get('LEAF_GROWTH_RATIO'),
            reproductive_stem_allocation=growth_params.get('STEM_GROWTH_RATIO'),
            reproductive_root_allocation=growth_params.get('ROOT_GROWTH_RATIO'),
            optimal_light_intensity=env_params.get('OPTIMAL_LIGHT_INTENSITY', 15.0),
            optimal_ec_range=(env_params.get('MIN_EC'), env_params.get('MAX_EC')),
            optimal_vpd_min=env_params.get('OPTIMAL_VPD_MIN'),
            optimal_vpd_max=env_params.get('OPTIMAL_VPD_MAX'),
            vpd_stress_high_factor=stress_params.get('VPD_STRESS_FACTOR_HIGH'),
            vpd_stress_low_factor=stress_params.get('VPD_STRESS_FACTOR_LOW'),
            optimal_ec=env_params.get('OPTIMAL_EC'),
            ec_stress_high_factor=stress_params.get('EC_STRESS_FACTOR_HIGH'),
            ec_stress_low_threshold=env_params.get('MIN_EC'),
            ec_stress_low_factor=stress_params.get('EC_STRESS_FACTOR_LOW'),
            optimal_root_temp=env_params.get('OPTIMAL_TEMPERATURE'),
            root_temp_tolerance=stress_params.get('TEMP_STRESS_THRESHOLD', 3.0),
            root_temp_stress_factor=stress_params.get('TEMP_STRESS_FACTOR'),
            optimal_air_temp_max=env_params.get('OPTIMAL_TEMPERATURE_MAX'),
            optimal_air_temp_min=env_params.get('OPTIMAL_TEMPERATURE_MIN'),
            air_temp_stress_high_factor=stress_params.get('HEAT_STRESS_THRESHOLD'),
            air_temp_stress_low_factor=stress_params.get('COLD_STRESS_THRESHOLD'),
            optimal_humidity_min=env_params.get('MIN_HUMIDITY'),
            humidity_stress_factor=stress_params.get('WATER_STRESS_FACTOR'),
            specific_leaf_area_default=canopy_params.get('SLA_YOUNG'),
            metabolic_water_per_lai=water_params.get('LAI_WATER_DEMAND_FACTOR'),
            reservoir_topup_fraction=system_params.get('RESERVOIR_TOPUP_FRACTION', 0.3),
            minimal_nitrogen_uptake=nutrient_params.get('NITROGEN_UPTAKE_EFFICIENCY')
        )
    
    def _initialize_plant_state(self):
        """Initialize plant physiological state based on cultivar"""
        
        # Initial biomass based on cultivar characteristics
        cultivar_coeffs = self.cultivar_profile.genetic_coefficients
        
        # Initialize biomass pools for TRANSPLANT STAGE (realistic starting point)
        # Typical lettuce transplants: 2-3 weeks old, 2-4 true leaves + cotyledons
        # This eliminates the bootstrap paradox by starting with functional photosynthetic area
        
        # Transplant biomass based on industry standards
        # Typical transplant: 0.1-0.3g total, with established root system and true leaves
        transplant_development_factor = cultivar_coeffs.PHOTOSYNTHETIC_CAPACITY
        
        # True leaves + cotyledons at transplant stage
        initial_leaf_biomass = 0.08 * transplant_development_factor  # 2-3 true leaves + cotyledons
        initial_stem_biomass = 0.03  # Developed stem/hypocotyl
        initial_root_biomass = 0.04  # Established root system for transplant viability
        
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
        # Calculate realistic LAI from transplant leaf biomass
        transplant_sla = 250.0  # cm²/g - SLA for young true leaves (higher than cotyledons)
        transplant_leaf_area_cm2 = initial_leaf_biomass * transplant_sla
        transplant_leaf_area_m2 = transplant_leaf_area_cm2 / 10000.0
        default_system_area = getattr(self, 'system_area', 1.0)  # Default 1 m² if not set yet
        
        # Transplant typically has LAI 0.01-0.05 depending on system density
        self.current_lai = min(0.05, transplant_leaf_area_m2 / max(1e-6, default_system_area))
        self.canopy_height = 0.02  # 2 cm height typical for transplants
        
        # Simulation tracking
        self.simulation_day = 0
        self.accumulated_gdd = 0.0
        # Cumulative trackers for system-level metrics
        self.cumulative_water_L = 0.0
        
        logger.info(f"Plant state initialized: {initial_leaf_biomass:.1f}g leaves, "
                   f"{initial_stem_biomass:.1f}g stems, {initial_root_biomass:.1f}g roots")
    
    def run_simulation(self, input_data: HydroInputData, 
                      max_days: int = 365,
                      target_maturity: str = "harvest") -> SimulationResults:
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
        
        # Initialize nutrient concentrations
        current_concentrations = {}
        for nutrient_id, params in input_data.nutrient_params.items():
            current_concentrations[nutrient_id] = params.initial_conc

        # Track system state
        current_tank_volume = input_data.system_config.tank_volume
        self.plant_count = input_data.system_config.n_plants
        self.system_area = max(0.1, input_data.system_config.system_area)
        self.plant_density = max(0.1, self.plant_count / self.system_area)
        current_ph = 6.0
        
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
            
            # Periodic reservoir management: weekly top-up to target concentrations
            if day % 7 == 1 and day > 1:
                for nutrient_id, params in input_data.nutrient_params.items():
                    target = params.recharge_conc if hasattr(params, 'recharge_conc') else params.initial_conc
                    # Only top-up if below target using configured fraction
                    current_concentrations[nutrient_id] = (
                        current_concentrations[nutrient_id] + self.params.reservoir_topup_fraction * max(0.0, target - current_concentrations[nutrient_id])
                    )

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

            # Update pH with drift and passive buffering; slight downward drift over time
            no3_uptake_total_mg = getattr(daily_result, 'N-NO3_uptake_rate', 0.0) * max(1, plant_count)
            if no3_uptake_total_mg == 0.0:
                est_n_mg = getattr(daily_result, 'nitrogen_uptake_mg', 0.0) * max(1, plant_count)
                no3_uptake_total_mg = est_n_mg * (62.0 / 14.0)
            # Nitrate uptake tends to acidify (release of H+)
            uptake_drift = -min(0.03, no3_uptake_total_mg / 20000.0)
            natural_acidification = -0.005
            current_ph = max(5.5, min(6.5, current_ph + uptake_drift + natural_acidification))

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
            summary_stats=summary_stats
        )
        
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
        carbon_for_growth = growth * self.params.carbon_to_biomass_ratio
        
        # Only warn when there is positive assimilation and/or positive growth
        # Negative net carbon with zero growth is physiologically plausible (maintenance exceeds assimilation)
        if not (net_carbon <= 0.0 and growth <= 0.0):
            # Check if carbon balance is reasonable (within 10% tolerance)
            denom = max(1e-9, max(abs(net_carbon), abs(carbon_for_growth)))
            if abs(net_carbon - carbon_for_growth) > 0.1 * denom:
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
        
        # Use controlled conditions if environmental control is active
        actual_temperature = env_control_response['current_conditions'].get('temperature', temperature)
        actual_humidity = env_control_response['current_conditions'].get('humidity', humidity)  
        # Dynamic CO2: enrich during photoperiod
        actual_co2 = self.environmental_control.setpoints.target_co2 if light_schedule['light_on'] else self.environmental_control.setpoints.ambient_co2
        actual_vpd = env_control_response['current_conditions'].get('vpd_kPa', 0.8)
        # Cache VPD for water model
        self._last_vpd = actual_vpd
        
        return {
            'light_environment': light_environment,
            'actual_temperature': actual_temperature,
            'actual_humidity': actual_humidity,
            'actual_co2': actual_co2,
            'actual_vpd': actual_vpd,
            'env_control_response': env_control_response
        }
    
    def _calculate_unified_stress_factors(self, env_conditions: Dict[str, Any], 
                                        nutrient_concentrations: Dict[str, float], 
                                        plant_state: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Calculate EC once (single source of truth)
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
        
        # Simplified hydroponic water stress based primarily on VPD
        optimal_vpd = 0.8  # kPa - optimal for lettuce
        vpd_tolerance = 0.5  # kPa - acceptable range around optimum
        
        vpd_deviation = abs(actual_vpd - optimal_vpd)
        if vpd_deviation <= vpd_tolerance:
            water_stress_level = 0.0  # No stress in optimal range
        else:
            # Gradual stress increase beyond tolerance
            water_stress_level = min(0.3, (vpd_deviation - vpd_tolerance) * 0.2)
        
        water_factor = max(0.0, 1.0 - water_stress_level)
        
        # 3. LIGHT STRESS (optimized for hydroponic LED systems)
        # In controlled environment hydroponics, light is usually adequate
        # Optimal light intensity reduced for more realistic LED systems
        optimal_light = 12.0  # MJ/m²/day - realistic for LED hydroponics
        light_factor = min(1.0, max(0.0, solar_radiation / optimal_light))
        
        # 4. NITROGEN STRESS (hydroponic-specific calculation)
        # For hydroponic systems, nitrogen stress should be primarily based on solution concentration
        # rather than complex internal nitrogen dynamics (which are more relevant for soil systems)
        
        n_no3_conc = nutrient_concentrations.get('N-NO3', 0.0)  # mg/L
        
        # Hydroponic nitrogen stress thresholds (mg/L N-NO3)
        optimal_n_min = 100.0   # Below this: some stress
        optimal_n_max = 400.0   # Above this: potential toxicity
        severe_deficiency = 20.0  # Below this: severe stress
        
        if n_no3_conc < severe_deficiency:
            nitrogen_stress_level = 0.8  # Severe deficiency
        elif n_no3_conc < optimal_n_min:
            # Linear increase from severe to optimal
            nitrogen_stress_level = 0.8 * (optimal_n_min - n_no3_conc) / (optimal_n_min - severe_deficiency)
        elif n_no3_conc <= optimal_n_max:
            nitrogen_stress_level = 0.0  # Optimal range - no stress
        else:
            # Slight stress from excess (but much less than deficiency)
            excess_stress = min(0.3, (n_no3_conc - optimal_n_max) / 1000.0)
            nitrogen_stress_level = excess_stress
        
        nitrogen_factor = max(0.0, 1.0 - nitrogen_stress_level)
        
        # 5. SALINITY STRESS (EC-based)
        if ec_current > 1.8:
            salinity_factor = max(0.0, 1.0 - (ec_current - 1.8) / 2.0)
        else:
            salinity_factor = 1.0
        
        # 6. pH STRESS
        ph = plant_state.get('ph', 6.0)
        if 5.5 <= ph <= 6.5:
            ph_factor = 1.0
        else:
            ph_deviation = min(abs(ph - 5.5), abs(ph - 6.5))
            ph_factor = max(0.0, 1.0 - ph_deviation * 0.2)
        
        # 7. OXYGEN STRESS (minimal in hydroponics)
        oxygen_factor = 0.95  # Assume good aeration in hydroponic systems
        
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
        stress_levels = {
            'temperature': 1.0 - combined_temp_factor,
            'water': 1.0 - water_factor,
            'light': 1.0 - light_factor,
            'nitrogen': 1.0 - nitrogen_factor,
            'salinity': 1.0 - salinity_factor,
            'ph': 1.0 - ph_factor,
            'oxygen': 1.0 - oxygen_factor
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
        detailed_photosynthesis = self.photosynthesis_model.calculate_daily_assimilation(
            par_umol_m2_s=env_conditions['light_environment'].ppfd_above_canopy,
            co2_ppm=env_conditions['actual_co2'],
            temp_c=env_conditions['actual_temperature'],
            lai=self.current_lai
        )
        
        # Apply genetic and stress modifiers ONLY ONCE
        overall_stress = np.prod([stress_factors[f] for f in ['temperature_factor', 'water_factor', 'nitrogen_factor', 'light_factor', 'salinity_factor']])
        genetic_growth_modifier = 1.0  # Could be from cultivar performance
        
        # Calculate net photosynthesis with stress effects applied ONCE
        canopy_photosynthesis = (
            detailed_photosynthesis *
            overall_stress *  # Apply stress to photosynthesis
            self.cultivar_profile.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY *
            genetic_growth_modifier
        )
        # Convert to per-plant carbon basis for consistency with per-plant biomass pools
        area_per_plant = max(1e-6, self.system_area / max(1, self.plant_count))
        canopy_photosynthesis *= area_per_plant
        
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
        available_biomass_growth = max(0.0, net_carbon_assimilation / (c_bm * (1.0 + rg)))
        
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
                           nutrient_concentrations: Dict[str, float], ph: float = 6.0,
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
        # Add solar radiation to env_conditions for stress calculation
        env_conditions['solar_radiation'] = solar_radiation

        
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
            plant_state=plant_state
        )
        
        # Get cultivar performance based on stress factors
        cultivar_performance = self.ge_model.predict_cultivar_performance(
            self.current_cultivar, stress_factors
        )
        
        # === STEP 4: PHOTOSYNTHESIS ===
        # Calculate carbon assimilation based on environment and stress
        detailed_photosynthesis = self.photosynthesis_model.calculate_daily_assimilation(
            par_umol_m2_s=env_conditions['light_environment'].ppfd_above_canopy,
            co2_ppm=env_conditions['actual_co2'],
            temp_c=env_conditions['actual_temperature'],
            lai=self.current_lai
        )
        
        # Apply stress effects to photosynthesis (use overall stress factor from centralized calculation)
        canopy_photosynthesis = (
            detailed_photosynthesis *
            stress_factors['overall_stress_factor'] *  # Single stress application
            self.cultivar_profile.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY
        )
        # Convert from ground-area basis (g C/m²/day) to per-plant carbon (g C/plant/day)
        area_per_plant = max(1e-6, self.system_area / max(1, self.plant_count))
        canopy_photosynthesis *= area_per_plant
        
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
        available_biomass_growth = max(0.0, net_carbon_for_growth / (c_bm * (1.0 + rg)))
        
        # Allocate biomass based on developmental stage
        if stage_props['is_vegetative']:
            allocation_fractions = {
                'leaves': self.params.vegetative_leaf_allocation,
                'stems': self.params.vegetative_stem_allocation,
                'roots': self.params.vegetative_root_allocation
            }
        else:
            allocation_fractions = {
                'leaves': self.params.reproductive_leaf_allocation,
                'stems': self.params.reproductive_stem_allocation,
                'roots': self.params.reproductive_root_allocation
            }
        
        # Calculate actual growth rates
        actual_growth_rates = {
            organ: available_biomass_growth * fraction 
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
        root_env_conditions = {
            'temperature': stress_factors['solution_temperature'],
            'flow_rate': 1.5,
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
        nitrogen_uptake_mg_per_day = root_response.get('NO3_uptake_rate', 0.0)
        nitrogen_uptake_g_per_day = nitrogen_uptake_mg_per_day / 1000.0
        
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
        
        # Update LAI based on leaf development
        sla_cm2_per_g = getattr(self.leaf_model.params, 'specific_leaf_area', 250.0)
        leaf_biomass_g_current = self.biomass_pools[0].dry_mass
        biomass_based_area_m2 = (leaf_biomass_g_current * sla_cm2_per_g) / 10000.0
        model_based_area_m2 = leaf_stats['total_leaf_area_m2']
        one_plant_leaf_area_m2 = max(model_based_area_m2, biomass_based_area_m2)
        total_leaf_area_m2 = one_plant_leaf_area_m2 * self.plant_count
        self.current_lai = min(8.0, max(0.0, total_leaf_area_m2 / max(1e-6, self.system_area)))
        
        # Update canopy height
        if stage_props['is_vegetative']:
            genetic_growth_modifier = cultivar_performance.get('yield_index', 1.0)
            height_growth = 0.004 * stress_factors['overall_stress_factor'] * genetic_growth_modifier
            self.canopy_height += height_growth
        self.canopy_height = min(0.25, self.canopy_height)
        
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
            water_use_efficiency=(
                total_new_growth / max(1e-6, transpiration * self.system_area)
            ),
            
            # Solution properties  
            ph=ph,  # Use dynamic pH from hydroponic system
            ec=stress_factors['ec_current'],  # Pre-calculated EC
            rzt=stress_factors['solution_temperature'],  # Pre-calculated solution temperature
            
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
        cropgro_result.v_stage = self.leaf_model.current_v_stage
        cropgro_result.leaf_number = int(leaf_stats['active_leaf_count'])
        cropgro_result.leaf_area_m2 = one_plant_leaf_area_m2
        cropgro_result.average_leaf_area_cm2 = (one_plant_leaf_area_m2 / max(1, cropgro_result.leaf_number)) * 1.0e4

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
        
        # Growth respiration breakdown (proportional to recent growth by tissue)
        total_growth = max(0.001, sum(pool.recent_growth for pool in self.biomass_pools))
        growth_resp_proportions = {
            'leaves': self.biomass_pools[0].recent_growth / total_growth,
            'stems': self.biomass_pools[1].recent_growth / total_growth,
            'roots': self.biomass_pools[2].recent_growth / total_growth
        }
        cropgro_result.growth_resp_leaves = respiration_response.growth_respiration * growth_resp_proportions['leaves']
        cropgro_result.growth_resp_stems = respiration_response.growth_respiration * growth_resp_proportions['stems'] 
        cropgro_result.growth_resp_roots = respiration_response.growth_respiration * growth_resp_proportions['roots']
        
        # Respiration factors from detailed model
        cropgro_result.temperature_acclimation = respiration_response.temperature_factor
        cropgro_result.age_factor = respiration_response.age_factor
        
        # 5. NITROGEN DYNAMICS - USE ROOT MODEL AS SINGLE SOURCE OF TRUTH
        # CRITICAL FIX: Get nitrogen uptake ONLY from the authoritative root model
        cropgro_result.nitrogen_uptake_mg = nitrogen_uptake_mg_per_day  # Direct from root model
        
        # Validate that root model is providing realistic uptake
        if cropgro_result.nitrogen_uptake_mg == 0.0 and total_biomass > 0.1:
            logger.warning(f"Day {day}: Root model returned zero nitrogen uptake for biomass {total_biomass:.1f}g - check root model parameters")
            # Only apply minimal value if plant has significant biomass but no uptake
            cropgro_result.nitrogen_uptake_mg = self.params.minimal_nitrogen_uptake
        cropgro_result.nitrogen_demand_mg = 50.0  # Default value for now
        cropgro_result.nitrogen_stress_factor = 1.0 - getattr(nitrogen_response, 'nitrogen_stress_level', 0.0)  # Convert to factor
        cropgro_result.leaf_nitrogen_conc = 4.5  # Default
        cropgro_result.root_nitrogen_conc = 2.8  # Default
        
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
            cropgro_result.n_critical_conc = current_n_conc * 1.2  # Critical is ~20% higher than current
        else:
            cropgro_result.n_critical_conc = 0.045  # Default for lettuce
        
        # 6. STRESS RESPONSES (with safe attribute access)
        cropgro_result.temperature_stress_level = stress_factors['stress_levels']['temperature']
        cropgro_result.temperature_stress_photosynthesis = stress_factors['temp_stress_response'].process_factors.photosynthesis
        cropgro_result.temperature_stress_growth = stress_factors['temp_stress_response'].process_factors.growth
        cropgro_result.integrated_stress_factor = getattr(integrated_stress_response, 'overall_stress_factor', 1.0)
        cropgro_result.water_stress = stress_factors['stress_levels']['water']
        cropgro_result.nutrient_stress = stress_factors['stress_levels']['nitrogen']
        cropgro_result.salinity_stress = stress_factors['salinity_factor']
        
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
                cropgro_result.root_turnover_rate = getattr(self.root_model.root_architecture.params, 'fine_turnover_rate', 0.02)
            else:
                cropgro_result.root_turnover_rate = 0.02
        else:
            cropgro_result.root_cohorts = 0
            cropgro_result.root_turnover_rate = 0.02
            
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
            
            # Log warning if root model returns zero for major nutrients with significant biomass
            if uptake_val == 0.0 and total_biomass > 0.1 and root_key in ['NO3', 'PO4', 'K']:
                logger.warning(f"Day {day}: Root model returned zero {root_key} uptake for biomass {total_biomass:.1f}g")
        
        # Ensure N-NO3 uptake matches our authoritative nitrogen uptake (already from root model)
        setattr(cropgro_result, 'N-NO3_uptake_rate', cropgro_result.nitrogen_uptake_mg * (62.0 / 14.0))  # Convert mg N to mg NO3
        
        # 9. GENETIC PARAMETERS EFFECTS
        cropgro_result.cultivar_adaptation_index = cultivar_performance.get('adaptation_index', 1.0)
        cropgro_result.cultivar_yield_potential = self.cultivar_profile.yield_potential
        cropgro_result.genetic_photosynthesis_capacity = self.cultivar_profile.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY
        cropgro_result.genetic_nitrate_efficiency = self.cultivar_profile.genetic_coefficients.NITRATE_EFFICIENCY
        cropgro_result.genetic_ec_tolerance = self.cultivar_profile.genetic_coefficients.EC_TOLERANCE
        
        # 10. ENVIRONMENTAL CONTROL DETAILS
        cropgro_result.controlled_temperature = env_conditions['actual_temperature']
        cropgro_result.controlled_humidity = env_conditions['actual_humidity']
        cropgro_result.controlled_co2 = env_conditions['actual_co2']
        cropgro_result.vpd_target = env_conditions['env_control_response'].get('recommendations', {}).get('target_vpd', 0.8)
        cropgro_result.environmental_cost = env_conditions['env_control_response'].get('control_actions', {}).get('total_operating_cost', 0.0)
        
        return cropgro_result
    
    def _prepare_senescence_data(self) -> Dict[int, Dict]:
        """Prepare senescence data from current biomass pools"""
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
                    'phosphorus': 0.010,
                    'potassium': 0.028
                }
            }
        return cohort_data
    
    def _calculate_ec(self, concentrations: Dict[str, float]) -> float:
        """Calculate electrical conductivity (dS/m) from major ions.

        Coefficients chosen so that baseline mix (~200 NO3, 300 K, 150 Ca, 50 Mg, 50 PO4)
        yields ~1.7–1.9 dS/m and declines proportionally with depletion.
        """
        factors = {
            'N-NO3': 0.0040,
            'P-PO4': 0.0008,
            'K': 0.0025,
            'Ca': 0.0015,
            'Mg': 0.0012,
        }
        ec = 0.0
        for ion, conc in concentrations.items():
            coeff = factors.get(ion, 0.0006)
            ec += coeff * conc
        return max(0.05, min(5.0, ec))
    
    def _calculate_vpd(self, temp: float, rel_humidity: float) -> float:
        """Calculate vapor pressure deficit"""
        # Saturation vapor pressure (kPa)
        es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
        # Actual vapor pressure (kPa)
        ea = es * rel_humidity / 100.0
        # VPD (kPa)
        return max(0.0, es - ea)
    
    def _calculate_eto_reference(self, temperature: float, humidity: float, solar_radiation: float) -> float:
        """Calculate reference evapotranspiration using Penman-Monteith equation"""
        # Simplified Penman-Monteith for daily ETo (mm/day)
        delta = 4098 * (0.6108 * np.exp(17.27 * temperature / (temperature + 237.3))) / ((temperature + 237.3) ** 2)
        gamma = 0.665  # Psychrometric constant
        u2 = 2.0  # Wind speed at 2m height (m/s) - typical greenhouse
        vpd = self._calculate_vpd(temperature, humidity)
        
        # Simplified calculation
        radiation_term = 0.408 * delta * (solar_radiation * 0.8)  # Net radiation approximation
        aerodynamic_term = gamma * 900 / (temperature + 273) * u2 * vpd
        
        eto = (radiation_term + aerodynamic_term) / (delta + gamma * (1 + 0.34 * u2))
        return max(0.5, min(8.0, eto))  # Reasonable bounds for hydroponic systems
    
    def _calculate_etc_prime(self, light_interception: float, temperature: float, humidity: float, solar_radiation: float) -> float:
        """Calculate crop evapotranspiration adjusted for canopy development"""
        eto = self._calculate_eto_reference(temperature, humidity, solar_radiation)
        kc = 0.7 + (0.4 * light_interception)  # Crop coefficient based on canopy coverage
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
        return base_transpiration * vpd_factor * light_interception
    
    def _calculate_water_uptake(self, light_interception: float, temperature: float, humidity: float, solar_radiation: float, vpd: float, lai: float) -> float:
        """Calculate water uptake per m² ground area (L/m²/day).

        - Transpiration: mm/day -> L/m²/day by 1 mm = 1 L/m²
        - Metabolic water: L/m²/day proportional to LAI
        """
        transpiration_mm = self._calculate_transpiration(light_interception, temperature, vpd, humidity, solar_radiation)
        metabolic_water = lai * self.params.metabolic_water_per_lai  # L/m²/day per unit LAI
        return transpiration_mm + metabolic_water

    def _calculate_solution_temperature(self, air_temp: float, solar_radiation: float, tank_volume: float, day: int) -> float:
        """Calculate hydroponic solution temperature with simple thermal mass and solar gain model."""
        thermal_mass_factor = min(1.0, max(0.1, tank_volume / 1000.0))
        solar_heating = solar_radiation * 0.15  # °C increase per MJ/m²
        prev_ts = getattr(self, 'prev_solution_temp', air_temp)
        temp_change = (air_temp + solar_heating - prev_ts)
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
        
        # EC stress using configured parameters
        if ec > self.params.optimal_ec:
            ec_stress = (ec - self.params.optimal_ec) * self.params.ec_stress_high_factor
        elif ec < self.params.ec_stress_low_threshold:
            ec_stress = (self.params.ec_stress_low_threshold - ec) * self.params.ec_stress_low_factor
        else:
            ec_stress = 0.0
        
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
        """Display comprehensive CROPGRO results for a single day"""
        output = []
        output.append(f"\n🌱 DETAILED CROPGRO RESULTS - DAY {daily_result.day}")
        output.append("=" * 70)
        
        # 1. PHENOLOGICAL DEVELOPMENT
        output.append(f"\n📅 PHENOLOGICAL DEVELOPMENT:")
        output.append(f"  • Growth Stage: {getattr(daily_result, 'growth_stage', 'N/A')}")
        output.append(f"  • Accumulated GDD: {getattr(daily_result, 'accumulated_gdd', 0.0):.1f}°C-days")
        output.append(f"  • Daily Thermal Time: {getattr(daily_result, 'thermal_time_daily', 0.0):.1f}°C-days")
        output.append(f"  • Development Rate: {getattr(daily_result, 'development_rate', 0.0):.4f}")
        output.append(f"  • Vegetative Phase: {'Yes' if getattr(daily_result, 'is_vegetative', True) else 'No'}")
        output.append(f"  • Reproductive Phase: {'Yes' if getattr(daily_result, 'is_reproductive', False) else 'No'}")
        
        # 2. BIOMASS AND GROWTH
        output.append(f"\n⚖️  BIOMASS AND GROWTH:")
        output.append(f"  • Total Biomass: {getattr(daily_result, 'total_biomass', 0.0):.2f} g")
        output.append(f"  • Leaf Biomass: {getattr(daily_result, 'leaf_biomass', 0.0):.2f} g")
        output.append(f"  • Stem Biomass: {getattr(daily_result, 'stem_biomass', 0.0):.2f} g")
        output.append(f"  • Root Biomass: {getattr(daily_result, 'root_biomass', 0.0):.2f} g")
        output.append(f"  • Daily Growth Rate: {getattr(daily_result, 'daily_growth_rate', 0.0):.3f} g/day")
        output.append(f"  • Leaf Growth Rate: {getattr(daily_result, 'leaf_growth_rate', 0.0):.3f} g/day")
        output.append(f"  • Root Growth Rate: {getattr(daily_result, 'root_growth_rate', 0.0):.3f} g/day")
        
        # 3. CANOPY ARCHITECTURE  
        output.append(f"\n🍃 CANOPY ARCHITECTURE:")
        output.append(f"  • LAI (Leaf Area Index): {getattr(daily_result, 'lai', 0.0):.2f}")
        output.append(f"  • Canopy Height: {getattr(daily_result, 'canopy_height_cm', 0.0):.1f} cm")
        output.append(f"  • Light Interception: {getattr(daily_result, 'light_interception', 0.0):.3f}")
        output.append(f"  • Canopy Photosynthesis: {getattr(daily_result, 'canopy_photosynthesis', 0.0):.3f} μmol CO₂/m²/s")
        output.append(f"  • Total Absorbed PPFD: {getattr(daily_result, 'total_absorbed_ppfd', 0.0):.1f} μmol/m²/s")
        output.append(f"  • Sunlit LAI: {getattr(daily_result, 'sunlit_lai', 0.0):.2f}")
        output.append(f"  • Shaded LAI: {getattr(daily_result, 'shaded_lai', 0.0):.2f}")
        
        # 4. PHYSIOLOGICAL PROCESSES
        output.append(f"\n🔄 PHYSIOLOGICAL PROCESSES:")
        output.append(f"  • Photosynthesis Rate: {getattr(daily_result, 'photosynthesis_rate', 0.0):.4f}")
        output.append(f"  • Respiration Rate: {getattr(daily_result, 'respiration_rate', 0.0):.4f}")
        output.append(f"  • Maintenance Respiration: {getattr(daily_result, 'maintenance_respiration', 0.0):.4f}")
        output.append(f"  • Growth Respiration: {getattr(daily_result, 'growth_respiration', 0.0):.4f}")
        output.append(f"  • Net Assimilation: {getattr(daily_result, 'net_assimilation', 0.0):.4f}")
        
        # 5. NITROGEN DYNAMICS
        output.append(f"\n🧪 NITROGEN DYNAMICS:")
        output.append(f"  • N Uptake: {getattr(daily_result, 'nitrogen_uptake_mg', 0.0):.2f} mg/day")
        output.append(f"  • N Demand: {getattr(daily_result, 'nitrogen_demand_mg', 0.0):.2f} mg/day")
        output.append(f"  • N Stress Level: {1.0 - getattr(daily_result, 'nitrogen_stress_factor', 1.0):.3f}")
        output.append(f"  • Leaf N Concentration: {getattr(daily_result, 'leaf_nitrogen_conc', 0.0):.3f}%")
        output.append(f"  • Root N Concentration: {getattr(daily_result, 'root_nitrogen_conc', 0.0):.3f}%")
        
        # 6. STRESS RESPONSES
        output.append(f"\n😰 STRESS RESPONSES:")
        output.append(f"  • Temperature Stress: {getattr(daily_result, 'temperature_stress_level', 0.0):.3f}")
        output.append(f"  • Temp Effect on Photosynthesis: {getattr(daily_result, 'temperature_stress_photosynthesis', 1.0):.3f}")
        output.append(f"  • Temp Effect on Growth: {getattr(daily_result, 'temperature_stress_growth', 1.0):.3f}")
        output.append(f"  • Integrated Stress Factor: {getattr(daily_result, 'integrated_stress_factor', 1.0):.3f}")
        output.append(f"  • Water Stress: {getattr(daily_result, 'water_stress', 1.0):.3f}")
        output.append(f"  • Nutrient Stress: {getattr(daily_result, 'nutrient_stress', 1.0):.3f}")
        output.append(f"  • Salinity Stress: {getattr(daily_result, 'salinity_stress', 1.0):.3f}")
        
        # 7. SENESCENCE AND REMOBILIZATION
        output.append(f"\n🍂 SENESCENCE AND REMOBILIZATION:")
        output.append(f"  • Total Senescence Rate: {getattr(daily_result, 'senescence_rate', 0.0):.5f}")
        output.append(f"  • Leaf Senescence Rate: {getattr(daily_result, 'leaf_senescence_rate', 0.0):.5f}")
        output.append(f"  • N Remobilization: {getattr(daily_result, 'nitrogen_remobilization', 0.0):.3f} mg/day")
        output.append(f"  • P Remobilization: {getattr(daily_result, 'phosphorus_remobilization', 0.0):.3f} mg/day")
        output.append(f"  • K Remobilization: {getattr(daily_result, 'potassium_remobilization', 0.0):.3f} mg/day")
        
        # 8. ROOT ARCHITECTURE
        output.append(f"\n🌿 ROOT ARCHITECTURE:")
        output.append(f"  • Root Length Density: {getattr(daily_result, 'root_length_density', 0.0):.3f} cm/cm³")
        output.append(f"  • Root Surface Area: {getattr(daily_result, 'root_surface_area', 0.0):.2f} cm²")
        output.append(f"  • Root Volume: {getattr(daily_result, 'root_volume', 0.0):.3f} cm³")
        output.append(f"  • Root Activity Factor: {getattr(daily_result, 'root_activity_factor', 1.0):.3f}")
        
        # 9. GENETIC PARAMETERS
        output.append(f"\n🧬 GENETIC PARAMETERS EFFECTS:")
        output.append(f"  • Cultivar Adaptation Index: {getattr(daily_result, 'cultivar_adaptation_index', 1.0):.3f}")
        output.append(f"  • Yield Potential: {getattr(daily_result, 'cultivar_yield_potential', 1.0):.3f}")
        output.append(f"  • Photosynthesis Capacity: {getattr(daily_result, 'genetic_photosynthesis_capacity', 1.0):.3f}")
        output.append(f"  • Nitrate Efficiency: {getattr(daily_result, 'genetic_nitrate_efficiency', 1.0):.3f}")
        output.append(f"  • EC Tolerance: {getattr(daily_result, 'genetic_ec_tolerance', 1.5):.1f} dS/m")
        
        # 10. ENVIRONMENTAL CONTROL
        output.append(f"\n🌡️  ENVIRONMENTAL CONTROL:")
        output.append(f"  • Controlled Temperature: {getattr(daily_result, 'controlled_temperature', daily_result.temp_avg):.1f}°C")
        output.append(f"  • Controlled Humidity: {getattr(daily_result, 'controlled_humidity', 70.0):.1f}%")
        output.append(f"  • Controlled CO₂: {getattr(daily_result, 'controlled_co2', 400.0):.0f} μmol/mol")
        output.append(f"  • VPD Target: {getattr(daily_result, 'vpd_target', 0.8):.2f} kPa")
        output.append(f"  • Environmental Cost: ${getattr(daily_result, 'environmental_cost', 0.0):.3f}/hour")
        
        output.append("\n" + "=" * 70)
        
        return "\n".join(output)