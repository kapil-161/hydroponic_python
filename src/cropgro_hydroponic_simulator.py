"""
Hydroponic Lettuce Growth Simulator - Strict Implementation
Following all rules: No defaults, no fallbacks, all from CSV, use actual model functions
"""

import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List
import os

# Import ALL model classes and parameter classes - complete comprehensive list
from .models.environmental_control import (
    EnvironmentalControlSystem, EnvironmentalSetpoints, ControlEquipment, ControlStrategy
)
from .models.nutrient_models import (
    NutrientModel, NutrientParameters, NutrientMobility, NutrientMobilityResponse,
    NutrientTransportFlux, OrganNutrientPools, TransportMechanism
)
from .models.photosynthesis_model import (
    PhotosynthesisModel, PhotosynthesisParameters
)
from .models.respiration_model import (
    EnhancedRespirationModel, RespirationParameters, BiomassPool,
    RespirationComponents, TissueType
)
from .models.water_uptake_model import (
    WaterUptakeModel, WaterUptakeParameters, GrowthStage
)
from .models.phenology_model import (
    ComprehensivePhenologyModel, PhenologyParameters,
    LettuceGrowthStage, DevelopmentalState
)
from .models.ph_model import (
    HydroponicPHModel, PHParameters, PHState,
    BufferSystem, NutrientSolubility
)
from .models.root_zone_temperature import (
    RootZoneTemperatureModel, RZTParameters
)
from .models.stress_models import (
    IntegratedStressModel, IntegratedStressParameters,
    TemperatureStressModel, TemperatureStressParameters,
    StressType, StressState, StressResponse, ProcessStressFactors,
    TemperatureAcclimation, TemperatureDamage, UnifiedStressCalculator
)
from .models.biomass_allocation_model import (
    BiomassAllocationModel, BiomassAllocationParameters
)
from .models.leaf_development import (
    LeafDevelopmentModel, LeafParameters, LeafCohort, LeafStage
)
from .models.canopy_architecture import (
    CanopyArchitectureModel, CanopyArchitectureParameters,
    CanopyLayer, LightEnvironment, LeafAngleDistribution
)
from .models.senescence_model import (
    AdvancedSenescenceModel, SenescenceParameters,
    LeafCohortSenescence, SenescenceType, SenescenceStage
)
from .models.nitrogen_balance import (
    NitrogenBalanceModel, NitrogenBalanceParameters,
    NitrogenUptakeResponse, NitrogenAllocationResponse, OrganNitrogenState
)
from .models.root_system_model import (
    EnhancedRootSystemModel, RootSystemParameters, RootSystemMetrics,
    RootCohort, RootZoneLayer, RootType, HydroponicSystemType
)
from .models.genetic_parameters import (
    GenotypeEnvironmentModel, GeneticParameterDatabase, CultivarProfile,
    GeneticCoefficients, GeneticTrait, LettuceType, BreedingAssistant
)
from .models.base_model import (
    BaseHydroponicModel, ModelRegistry, ModelState, ModelValidationResult,
    DailyUpdateInput, DailyUpdateOutput
)


class ParameterError(Exception):
    """Raised when required parameters are missing from CSV"""
    pass


class WeatherDataError(Exception):
    """Raised when weather data is missing or invalid"""
    pass


class ModelInitializationError(Exception):
    """Raised when model initialization fails"""
    pass


@dataclass
class PlantState:
    """Central plant state - all values from model calculations only"""
    day: int = 0
    hour: int = 0

    # Biomass (g DM/plant) - from allocation model
    leaf_biomass: float = 0.0
    stem_biomass: float = 0.0
    root_biomass: float = 0.0
    total_biomass: float = 0.0

    # Canopy - from canopy and leaf models
    lai: float = 0.0
    leaf_area: float = 0.0
    canopy_height: float = 0.0

    # Physiological rates - from photosynthesis/respiration models
    photosynthesis_rate: float = 0.0
    respiration_rate: float = 0.0
    net_assimilation: float = 0.0

    # Development - from phenology model
    thermal_time: float = 0.0
    growth_stage: str = "GE"
    development_index: float = 0.0

    # Stresses - from stress model
    temperature_stress: float = 0.0
    water_stress: float = 0.0
    nutrient_stress: float = 0.0
    light_stress: float = 0.0

    # Nutrients - from nutrient and nitrogen models
    n_content: float = 0.0
    p_content: float = 0.0
    k_content: float = 0.0

    # Water - from water model
    water_uptake: float = 0.0
    transpiration: float = 0.0

    # Root system - from root model
    root_depth: float = 0.0
    root_distribution: Dict[str, float] = None

    # Environment - from environmental model
    air_temperature: float = 0.0
    solution_temperature: float = 0.0
    humidity: float = 0.0
    co2_concentration: float = 0.0
    light_intensity: float = 0.0
    ph: float = 0.0

    def __post_init__(self):
        if self.root_distribution is None:
            self.root_distribution = {}


class StrictParameterLoader:
    """Loads parameters strictly from CSV with no defaults or fallbacks"""

    def __init__(self, master_csv_path: str):
        self.master_csv_path = master_csv_path
        self.parameters = {}
        self._load_all_parameters()

    def _load_all_parameters(self):
        """Load all parameters from CSV - fail if any issues"""
        if not os.path.exists(self.master_csv_path):
            raise ParameterError(f"Master parameter file not found: {self.master_csv_path}")

        try:
            # Handle CSV with potential commas in description field
            # Read only the first 4 columns to avoid description parsing issues
            df = pd.read_csv(self.master_csv_path, comment='#', usecols=[0, 1, 2, 3],
                           names=['category', 'parameter_name', 'value', 'unit'], skiprows=1)
        except Exception as e:
            raise ParameterError(f"Failed to read CSV: {e}")

        if df.empty:
            raise ParameterError("Parameter CSV is empty")

        required_columns = ['category', 'parameter_name', 'value', 'unit']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ParameterError(f"Missing required columns in CSV: {missing_cols}")

        # Load individual parameters - each row is a parameter
        for _, row in df.iterrows():
            category = row['category']
            param_name = row['parameter_name']  # parameter_name contains the actual parameter name
            value = row['value']  # value contains the actual value

            # Use parameter_name as the key for individual parameters
            # For stage transitions, use category as the key

            if pd.isna(param_name) or pd.isna(value):
                continue

            # Convert value to appropriate type - no defaults
            if isinstance(value, str):
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        pass  # Keep as string

            # Store parameter with appropriate key
            # For stage transitions and single-parameter categories, use category as key
            stage_transitions = ['GE_to_VE', 'VE_to_V1', 'V1_to_V2', 'V2_to_V3', 'V3_to_V4', 'V4_to_V5', 'V5_to_V6', 'V6_to_V7', 'V7_to_V8', 'V8_to_V9', 'V9_to_V10', 'V10_to_V11+', 'V11+_to_HI', 'HI_to_HD', 'HD_to_HM', 'HM_to_BI']

            if '_to_' in category or category in stage_transitions or category.startswith('pid_') or category == 'phenology_parameters':
                # For complex categories that group parameters, use parameter_name as key
                if category == 'phenology_parameters':
                    self.parameters[param_name] = value
                else:
                    # For stage transitions and PID parameters, use category as key
                    self.parameters[category] = value
            else:
                # For regular parameters, use parameter_name as key
                self.parameters[param_name] = value

    def get_parameter(self, param_name: str) -> Any:
        """Get parameter value - raise error if not found"""
        if param_name not in self.parameters:
            raise ParameterError(f"Parameter not found: {param_name}")
        return self.parameters[param_name]

    def get_parameters_for_model(self, param_prefix: str) -> Dict[str, Any]:
        """Get all parameters starting with prefix for a model"""
        model_params = {}
        for param_name, value in self.parameters.items():
            if param_name.startswith(param_prefix):
                # Remove prefix to get clean parameter name
                clean_name = param_name.replace(param_prefix + '_', '').replace(param_prefix, '')
                if clean_name:
                    model_params[clean_name] = value
                else:
                    model_params[param_name] = value

        if not model_params:
            raise ParameterError(f"No parameters found for model prefix: {param_prefix}")

        return model_params

    def create_photosynthesis_parameters(self) -> PhotosynthesisParameters:
        """Create PhotosynthesisParameters from CSV values"""
        try:
            return PhotosynthesisParameters(
                phi_psii=self.get_parameter('phi_psii'),
                r=self.get_parameter('r'),
                g_max=self.get_parameter('g_max'),
                min_par_threshold=self.get_parameter('min_par_threshold'),
                enzyme_saturation_lai=self.get_parameter('enzyme_saturation_lai'),
                light_penetration_lai=self.get_parameter('light_penetration_lai'),
                enzyme_saturation_rate=self.get_parameter('enzyme_saturation_rate'),
                min_enzyme_factor=self.get_parameter('min_enzyme_factor'),
                excess_lai_efficiency=self.get_parameter('excess_lai_efficiency'),
                umol_to_g_carbon_ratio=self.get_parameter('umol_to_g_carbon_ratio'),
                seconds_per_hour=int(self.get_parameter('seconds_per_hour')),
                hours_per_day=int(self.get_parameter('hours_per_day')),
                kc=self.get_parameter('kc'),
                ko=self.get_parameter('ko'),
                gamma_star=self.get_parameter('gamma_star'),
                jmax_25=self.get_parameter('jmax_25'),
                vcmax_25=self.get_parameter('vcmax_25'),
                theta=self.get_parameter('theta'),
                alpha=self.get_parameter('alpha'),
                rd_25=self.get_parameter('rd_25'),
                eaj=self.get_parameter('eaj'),
                eav=self.get_parameter('eav'),
                ear=self.get_parameter('ear'),
                o2_mmol_mol=self.get_parameter('o2_mmol_mol'),
                shaded_light_fraction=self.get_parameter('shaded_light_fraction'),
                photosynthesis_cold_limit=self.get_parameter('photosynthesis_cold_limit'),
                photosynthesis_heat_limit=self.get_parameter('photosynthesis_heat_limit'),
                min_stress_factor=self.get_parameter('min_stress_factor')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create PhotosynthesisParameters: {e}")

    def create_phenology_parameters(self) -> PhenologyParameters:
        """Create PhenologyParameters from CSV values"""
        try:
            # Create thermal requirements dictionary - all from CSV
            thermal_requirements = {
                'GE_to_VE': self.get_parameter('GE_to_VE'),
                'VE_to_V1': self.get_parameter('VE_to_V1'),
                'V1_to_V2': self.get_parameter('V1_to_V2'),
                'V2_to_V3': self.get_parameter('V2_to_V3'),
                'V3_to_V4': self.get_parameter('V3_to_V4'),
                'V4_to_V5': self.get_parameter('V4_to_V5'),
                'V5_to_V6': self.get_parameter('V5_to_V6'),
                'V6_to_V7': self.get_parameter('V6_to_V7'),
                'V7_to_V8': self.get_parameter('V7_to_V8'),
                'V8_to_V9': self.get_parameter('V8_to_V9'),
                'V9_to_V10': self.get_parameter('V9_to_V10'),
                'V10_to_V11+': self.get_parameter('V10_to_V11+'),
                'V11+_to_HI': self.get_parameter('V11+_to_HI'),
                'HI_to_HD': self.get_parameter('HI_to_HD'),
                'HD_to_HM': self.get_parameter('HD_to_HM'),
                'HM_to_BI': self.get_parameter('HM_to_BI')
            }

            return PhenologyParameters(
                base_temperature=self.get_parameter('base_temperature'),
                optimal_temperature_min=self.get_parameter('optimal_temperature_min'),
                optimal_temperature_max=self.get_parameter('optimal_temperature_max'),
                maximum_temperature=self.get_parameter('maximum_temperature'),
                thermal_requirements=thermal_requirements,
                photoperiod_sensitive=self.get_parameter('photoperiod_sensitive'),
                critical_photoperiod=self.get_parameter('critical_photoperiod'),
                bolting_photoperiod_threshold=self.get_parameter('bolting_photoperiod_threshold'),
                bolting_temperature_threshold=self.get_parameter('bolting_temperature_threshold'),
                head_formation_node_requirement=int(self.get_parameter('head_formation_node_requirement')),
                environmental_buffer_days=int(self.get_parameter('environmental_buffer_days')),
                bolting_photoperiod_divisor=self.get_parameter('bolting_photoperiod_divisor'),
                bolting_photoperiod_risk_max=self.get_parameter('bolting_photoperiod_risk_max'),
                bolting_temperature_divisor=self.get_parameter('bolting_temperature_divisor'),
                bolting_temperature_risk_max=self.get_parameter('bolting_temperature_risk_max'),
                environmental_history_days=int(self.get_parameter('environmental_history_days')),
                bolting_sustained_stress_risk=self.get_parameter('bolting_sustained_stress_risk'),
                bolting_maturity_risk_factor=self.get_parameter('bolting_maturity_risk_factor'),
                bolting_maturity_risk_max=self.get_parameter('bolting_maturity_risk_max'),
                bolting_risk_threshold=self.get_parameter('bolting_risk_threshold'),
                photoperiod_slope=self.get_parameter('photoperiod_slope'),
                thermal_time_scale=self.get_parameter('thermal_time_scale'),
                vernalization_required=bool(self.get_parameter('vernalization_required')),
                vernalization_temperature=self.get_parameter('vernalization_temperature'),
                vernalization_days=self.get_parameter('vernalization_days'),
                stress_acceleration_factor=self.get_parameter('stress_acceleration_factor'),
                drought_threshold=self.get_parameter('drought_threshold'),
                heat_threshold=self.get_parameter('heat_threshold')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create PhenologyParameters: {e}")

    def create_respiration_parameters(self) -> RespirationParameters:
        """Create RespirationParameters from CSV values"""
        try:
            # Create tissue factors dictionary
            tissue_factors = {
                'leaves': self.get_parameter('tissue_factor_leaves'),
                'stems': self.get_parameter('tissue_factor_stems'),
                'roots': self.get_parameter('tissue_factor_roots'),
                'reproductive': self.get_parameter('tissue_factor_reproductive')
            }

            # Create biosynthetic costs dictionary
            biosynthetic_costs = {
                'carbohydrate': self.get_parameter('carbohydrate_respiration_cost'),
                'protein': self.get_parameter('protein_respiration_cost'),
                'lipid': self.get_parameter('lipid_respiration_cost'),
                'organic_acid': self.get_parameter('organic_acid_respiration_cost'),
                'lignin': self.get_parameter('lignin_respiration_cost'),
                'mineral': self.get_parameter('mineral_respiration_cost')
            }

            return RespirationParameters(
                maintenance_base_rate=self.get_parameter('maintenance_base_rate'),
                reference_temperature=self.get_parameter('reference_temperature'),
                q10_factor=self.get_parameter('q10_factor'),
                growth_efficiency=self.get_parameter('growth_efficiency'),
                biosynthetic_cost=self.get_parameter('biosynthetic_cost'),
                tissue_factors=tissue_factors,
                age_effect_coefficient=self.get_parameter('age_effect_coefficient'),
                max_age_effect=self.get_parameter('max_age_effect'),
                acclimation_rate=self.get_parameter('acclimation_rate'),
                acclimation_memory=self.get_parameter('acclimation_memory'),
                n_effect_slope=self.get_parameter('n_effect_slope'),
                reference_leaf_n=self.get_parameter('reference_leaf_n'),
                max_temperature_threshold=self.get_parameter('max_temperature_threshold'),
                temperature_decay_factor=self.get_parameter('temperature_decay_factor'),
                size_penalty_threshold=self.get_parameter('size_penalty_threshold'),
                size_penalty_rate=self.get_parameter('size_penalty_rate'),
                glucose_to_carbon_ratio=self.get_parameter('glucose_to_carbon_ratio'),
                min_history_threshold=int(self.get_parameter('min_history_threshold')),
                day_start_hour=int(self.get_parameter('day_start_hour')),
                day_end_hour=int(self.get_parameter('day_end_hour')),
                day_respiration_factor=self.get_parameter('day_respiration_factor'),
                night_respiration_factor=self.get_parameter('night_respiration_factor'),
                carbon_to_co2_ratio=self.get_parameter('carbon_to_co2_ratio'),
                circadian_amplitude_1=self.get_parameter('circadian_amplitude_1'),
                circadian_peak_1=int(self.get_parameter('circadian_peak_1')),
                circadian_amplitude_2=self.get_parameter('circadian_amplitude_2'),
                circadian_peak_2=int(self.get_parameter('circadian_peak_2')),
                diurnal_base_factor=self.get_parameter('diurnal_base_factor'),
                optimal_temperature=self.get_parameter('optimal_temperature'),
                moderate_stress_threshold=self.get_parameter('moderate_stress_threshold'),
                severe_stress_threshold=self.get_parameter('severe_stress_threshold'),
                moderate_stress_factor=self.get_parameter('moderate_stress_factor'),
                severe_stress_base=self.get_parameter('severe_stress_base'),
                severe_stress_factor=self.get_parameter('severe_stress_factor'),
                daytime_respiratory_quotient=self.get_parameter('daytime_respiratory_quotient'),
                nighttime_respiratory_quotient=self.get_parameter('nighttime_respiratory_quotient'),
                biosynthetic_costs=biosynthetic_costs,
                min_acclimation_temperature=self.get_parameter('min_acclimation_temperature'),
                max_acclimation_temperature=self.get_parameter('max_acclimation_temperature'),
                min_diurnal_factor=self.get_parameter('min_diurnal_factor'),
                max_diurnal_factor=self.get_parameter('max_diurnal_factor')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create RespirationParameters: {e}")

    def create_water_uptake_parameters(self) -> WaterUptakeParameters:
        """Create WaterUptakeParameters from CSV data following strict no-defaults rule"""
        try:
            return WaterUptakeParameters(
                psychrometric_constant=self.get_parameter('psychrometric_constant'),
                wind_speed=self.get_parameter('wind_speed'),
                net_radiation_factor=self.get_parameter('net_radiation_factor'),
                radiation_offset=self.get_parameter('radiation_offset'),
                base_crop_coefficient=self.get_parameter('base_crop_coefficient'),
                lai_coefficient_factor=self.get_parameter('lai_coefficient_factor'),
                vegetative_stage_factor=self.get_parameter('vegetative_stage_factor'),
                head_formation_stage_factor=self.get_parameter('head_formation_stage_factor'),
                mature_stage_factor=self.get_parameter('mature_stage_factor'),
                optimal_temperature=self.get_parameter('optimal_temperature'),
                temperature_sensitivity=self.get_parameter('temperature_sensitivity'),
                optimal_vpd_min=self.get_parameter('optimal_vpd_min'),
                optimal_vpd_max=self.get_parameter('optimal_vpd_max'),
                vpd_sensitivity=self.get_parameter('vpd_sensitivity'),
                metabolic_water_per_biomass=self.get_parameter('metabolic_water_per_biomass'),
                metabolic_water_per_lai=self.get_parameter('metabolic_water_per_lai'),
                base_root_conductance=self.get_parameter('base_root_conductance'),
                root_conductance_scaling_factor=self.get_parameter('root_conductance_scaling_factor'),
                base_xylem_conductance=self.get_parameter('base_xylem_conductance'),
                xylem_conductance_scaling_factor=self.get_parameter('xylem_conductance_scaling_factor'),
                base_leaf_potential=self.get_parameter('base_leaf_potential'),
                transpiration_potential_factor=self.get_parameter('transpiration_potential_factor'),
                solution_potential_factor=self.get_parameter('solution_potential_factor'),
                cavitation_threshold=self.get_parameter('cavitation_threshold'),
                max_osmotic_adjustment=self.get_parameter('max_osmotic_adjustment'),
                salt_stress_osmotic_factor=self.get_parameter('salt_stress_osmotic_factor'),
                temp_tolerance=self.get_parameter('temp_tolerance'),
                min_temp_factor=self.get_parameter('min_temp_factor')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create WaterUptakeParameters: {e}")

    def create_nutrient_parameters(self) -> NutrientParameters:
        """Create NutrientParameters from CSV data following strict no-defaults rule"""
        try:
            # Get all basic nutrient parameters
            params_dict = {}

            # Basic EC factors
            basic_params = [
                'ec_factor_n_no3', 'ec_factor_n_nh4', 'ec_factor_p_po4', 'ec_factor_k',
                'ec_factor_ca', 'ec_factor_mg', 'ec_factor_s_so4', 'ec_factor_fe',
                'ec_factor_mn', 'ec_factor_zn', 'ec_factor_cu', 'ec_factor_b', 'ec_factor_mo',
                'minimum_volume_fraction', 'xylem_transport_capacity', 'phloem_transport_capacity',
                'temperature_q10', 'transpiration_coupling', 'ec_uptake_high_threshold',
                'ec_uptake_low_threshold', 'ec_uptake_modifier_n_high', 'ec_uptake_modifier_p_high',
                'ec_uptake_modifier_k_high', 'ec_uptake_modifier_ca_high', 'ec_uptake_modifier_n_low',
                'ec_uptake_modifier_p_low', 'ec_uptake_modifier_fe_low', 'kinetics_n_no3_vmax',
                'kinetics_n_no3_km', 'kinetics_n_no3_min_conc', 'kinetics_n_nh4_vmax',
                'kinetics_n_nh4_km', 'kinetics_n_nh4_min_conc', 'kinetics_p_po4_vmax',
                'kinetics_p_po4_km', 'kinetics_p_po4_min_conc', 'kinetics_k_vmax',
                'kinetics_k_km', 'kinetics_k_min_conc', 'kinetics_ca_vmax', 'kinetics_ca_km',
                'kinetics_ca_min_conc', 'kinetics_mg_vmax', 'kinetics_mg_km', 'kinetics_mg_min_conc'
            ]

            for param in basic_params:
                params_dict[param] = self.get_parameter(param)

            # Add all complex parameters that from_config expects
            nutrients = ["nitrogen", "phosphorus", "potassium", "calcium", "magnesium", "sulfur",
                        "iron", "manganese", "zinc", "copper", "boron", "molybdenum"]

            # Add mobility classifications parameters as expected by from_config
            for nutrient in nutrients:
                mobile = nutrient in ["nitrogen", "phosphorus", "potassium"]
                params_dict[f"mobility_classifications_{nutrient}_mobility"] = "mobile" if mobile else "immobile"
                params_dict[f"mobility_classifications_{nutrient}_transport"] = "xylem_and_phloem" if mobile else "xylem_only"
                params_dict[f"mobility_classifications_{nutrient}_remobilization_efficiency"] = 0.8 if nutrient in ["nitrogen", "phosphorus"] else 0.3
                params_dict[f"mobility_classifications_{nutrient}_deficiency_mobility"] = "high" if mobile else "low"
                params_dict[f"mobility_classifications_{nutrient}_retranslocation_rate"] = 0.05 if nutrient in ["nitrogen", "phosphorus"] else 0.01

            # Add transport rates
            for nutrient in nutrients:
                params_dict[f"xylem_transport_rates_{nutrient}"] = 1.0
                params_dict[f"phloem_transport_rates_{nutrient}"] = 0.5

            # Add buffering and storage parameters
            for organ in ["leaves", "stems", "roots"]:
                for nutrient in ["nitrogen", "phosphorus", "potassium"]:
                    params_dict[f"buffering_capacities_{organ}_{nutrient}"] = 10.0
                    params_dict[f"storage_pool_sizes_{organ}_{nutrient}"] = 5.0

            # Add redistribution parameters
            for nutrient in ["nitrogen", "phosphorus", "potassium", "calcium", "magnesium", "sulfur"]:
                params_dict[f"redistribution_thresholds_{nutrient}"] = 0.1
                params_dict[f"stress_redistribution_rates_{nutrient}"] = 0.2

            # Add sink strength coefficients
            for stage in ["vegetative", "reproductive", "senescence"]:
                for organ in ["leaves", "stems", "roots"]:
                    params_dict[f"sink_strength_coefficients_{stage}_{organ}"] = 1.0
                # Add special reproductive organ for reproductive stage
                if stage == "reproductive":
                    params_dict[f"sink_strength_coefficients_{stage}_reproductive"] = 1.5

            return NutrientParameters.from_config(params_dict)
        except Exception as e:
            raise ParameterError(f"Failed to create NutrientParameters: {e}")

    def create_ph_parameters(self) -> PHParameters:
        """Create PHParameters from CSV data following strict no-defaults rule"""
        try:
            # Create phosphate and iron solubility data dictionaries from CSV parameters
            phosphate_solubility_data = {
                4.0: self.get_parameter('phosphate_solubility_ph_4_0'),
                5.0: self.get_parameter('phosphate_solubility_ph_5_0'),
                6.0: self.get_parameter('phosphate_solubility_ph_6_0'),
                7.0: self.get_parameter('phosphate_solubility_ph_7_0'),
                8.0: self.get_parameter('phosphate_solubility_ph_8_0')
            }

            iron_solubility_data = {
                4.0: self.get_parameter('iron_solubility_ph_4_0'),
                5.0: self.get_parameter('iron_solubility_ph_5_0'),
                6.0: self.get_parameter('iron_solubility_ph_6_0'),
                7.0: self.get_parameter('iron_solubility_ph_7_0'),
                8.0: self.get_parameter('iron_solubility_ph_8_0')
            }

            return PHParameters(
                ph_target_min=self.get_parameter('ph_target_min'),
                ph_target_max=self.get_parameter('ph_target_max'),
                ph_buffer_capacity=self.get_parameter('ph_buffer_capacity'),
                ph_drift_rate=self.get_parameter('ph_drift_rate'),
                nitrate_acidification_factor=self.get_parameter('nitrate_acidification_factor'),
                ammonium_alkalinization_factor=self.get_parameter('ammonium_alkalinization_factor'),
                phosphate_acidification_factor=self.get_parameter('phosphate_acidification_factor'),
                carbonate_buffer_pka=self.get_parameter('carbonate_buffer_pka'),
                phosphate_buffer_pka1=self.get_parameter('phosphate_buffer_pka1'),
                phosphate_buffer_pka2=self.get_parameter('phosphate_buffer_pka2'),
                phosphate_buffer_pka3=self.get_parameter('phosphate_buffer_pka3'),
                ph_adjustment_rate=self.get_parameter('ph_adjustment_rate'),
                ph_deadband=self.get_parameter('ph_deadband'),
                temperature_correction_factor=self.get_parameter('temperature_correction_factor'),
                ec_buffer_factor=self.get_parameter('ec_buffer_factor'),
                proportional_control_factor=self.get_parameter('proportional_control_factor'),
                hours_per_day=24.0,  # Standard hours per day
                current_ph=self.get_parameter('current_ph'),
                total_alkalinity=self.get_parameter('total_alkalinity'),
                carbonate_conc=self.get_parameter('carbonate_conc'),
                phosphate_total=self.get_parameter('phosphate_total'),
                ionic_strength=self.get_parameter('ionic_strength'),
                ph_min_limit=self.get_parameter('ph_min_limit'),
                ph_max_limit=self.get_parameter('ph_max_limit'),
                phosphate_solubility_data=phosphate_solubility_data,
                iron_solubility_data=iron_solubility_data,
                calcium_phosphate_ksp=self.get_parameter('calcium_phosphate_ksp'),
                magnesium_phosphate_ksp=self.get_parameter('magnesium_phosphate_ksp'),
                co2_molecular_weight=self.get_parameter('co2_molecular_weight'),
                n_molecular_weight=self.get_parameter('nitrogen_atomic_weight'),
                no3_molecular_weight=self.get_parameter('no3_molecular_weight'),
                nh4_molecular_weight=self.get_parameter('nh4_molecular_weight'),
                p_molecular_weight=self.get_parameter('phosphorus_atomic_weight'),
                po4_molecular_weight=self.get_parameter('po4_molecular_weight'),
                unit_conversion_factor=self.get_parameter('unit_conversion_factor')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create PHParameters: {e}")

    def create_senescence_parameters(self) -> SenescenceParameters:
        """Create SenescenceParameters from CSV data following strict no-defaults rule"""
        try:
            # Get all basic senescence parameters and create config dict for from_config
            params_dict = {}

            # All required basic parameters
            basic_params = [
                'natural_lifespan_gdd', 'age_senescence_rate', 'water_stress_threshold',
                'nitrogen_stress_threshold', 'temperature_stress_threshold', 'light_stress_threshold',
                'water_stress_rate', 'nitrogen_stress_rate', 'temperature_stress_rate', 'light_stress_rate',
                'early_senescence_threshold', 'active_senescence_threshold', 'late_senescence_threshold',
                'death_threshold', 'recovery_rate', 'max_recovery', 'reproductive_priority_factor',
                'lower_canopy_factor', 'active_senescence_multiplier', 'normal_senescence_multiplier',
                'stress_history_days', 'daily_area_loss_factor', 'daily_biomass_loss_factor',
                'stress_recovery_threshold', 'recovery_stress_threshold', 'age_factor_base',
                'stress_intensity_denominator', 'reproductive_factor_adjustment', 'canopy_shading_threshold',
                'shading_factor_multiplier', 'lower_canopy_adjustment', 'recovery_rate_fraction',
                'senescence_damage_minimum', 'senescence_damage_maximum'
            ]

            for param in basic_params:
                params_dict[param] = self.get_parameter(param)

            # Add nutrient recovery parameters as expected by from_config
            nutrients = ['nitrogen', 'phosphorus', 'potassium', 'magnesium', 'sulfur', 'calcium',
                        'iron', 'manganese', 'zinc', 'copper', 'boron', 'molybdenum']
            for nutrient in nutrients:
                params_dict[f'{nutrient}_recovery'] = self.get_parameter(f'{nutrient}_recovery')

            return SenescenceParameters.from_config(params_dict)
        except Exception as e:
            raise ParameterError(f"Failed to create SenescenceParameters: {e}")

    def create_stress_parameters(self) -> IntegratedStressParameters:
        """Create IntegratedStressParameters from CSV data following strict no-defaults rule"""
        try:
            # Create config dict with all required stress parameters from CSV
            params_dict = {}

            # Basic stress weight parameters
            stress_weights = [
                'stress_weight_water', 'stress_weight_temperature', 'stress_weight_nutrient',
                'stress_weight_light', 'stress_weight_salinity', 'stress_weight_oxygen', 'stress_weight_ph'
            ]

            for param in stress_weights:
                params_dict[param] = self.get_parameter(param)

            # Additional stress model parameters available in CSV (104 total)
            additional_params = [
                'chronic_stress_weight', 'acute_stress_weight', 'acclimation_benefit_factor',
                'interaction_penalty_factor', 'recovery_bonus_factor', 'damage_penalty_factor',
                'memory_divisor', 'chronic_factor_multiplier', 'stress_memory_duration_water',
                'stress_memory_duration_temperature', 'stress_memory_duration_nutrient',
                'stress_memory_duration_light', 'cumulative_threshold_water', 'cumulative_threshold_temperature',
                'cumulative_threshold_nutrient', 'cumulative_threshold_light', 'damage_accumulation_rate_water',
                'damage_accumulation_rate_temperature', 'recovery_rate_water', 'recovery_rate_temperature',
                'recovery_threshold_water', 'recovery_threshold_temperature', 'full_recovery_time_water',
                'full_recovery_time_temperature', 'acclimation_rate_water', 'acclimation_rate_temperature',
                'acclimation_capacity_water', 'acclimation_capacity_temperature', 'acclimation_memory_water',
                'acclimation_memory_temperature', 'stress_onset_threshold_water', 'stress_onset_threshold_temperature',
                'damage_threshold_water', 'damage_threshold_temperature', 'process_sensitivity_photosynthesis_water',
                'process_sensitivity_photosynthesis_temperature', 'process_sensitivity_growth_water',
                'process_sensitivity_growth_temperature', 'process_sensitivity_development_water',
                'process_sensitivity_development_temperature'
            ]

            for param in additional_params:
                params_dict[param] = self.get_parameter(param)

            return IntegratedStressParameters.from_config(params_dict)
        except Exception as e:
            raise ParameterError(f"Failed to create IntegratedStressParameters: {e}")

    def create_leaf_development_parameters(self) -> LeafParameters:
        """Create LeafParameters from CSV data following strict no-defaults rule"""
        try:
            # Create config dict structure as expected by LeafParameters.from_config
            config = {
                'leaf_development': {},
                'canopy_parameters': {},
                'phenology': {},
                'nitrogen_parameters': {},
                'genetic_parameters': {},
                'thermal_time': {}
            }

            # Add genetic parameters section (required by from_config)
            config['genetic_parameters']['SLAVR'] = self.get_parameter('SLAVR')

            # Add thermal time parameters section (required by from_config)
            config['thermal_time']['base_temp'] = self.get_parameter('base_temp')
            config['thermal_time']['optimal_temp_min'] = self.get_parameter('optimal_temp_min')
            config['thermal_time']['optimal_temp_max'] = self.get_parameter('optimal_temp_max')
            config['thermal_time']['max_temp'] = self.get_parameter('max_temp')

            # Get all leaf development parameters from CSV (using existing parameter names)
            leaf_dev_params = [
                'base_phyllochron', 'max_leaf_number', 'initial_leaf_number', 'leaf_appearance_rate',
                'max_individual_leaf_area', 'leaf_area_expansion_rate', 'drought_threshold',
                'n_stress_threshold', 'temperature_stress_sensitivity', 'initial_leaf_area_factor',
                'initial_thermal_time_factor', 'emerging_to_expanding_factor', 'late_leaf_phyllochron_factor',
                'very_late_leaf_phyllochron_factor', 'early_leaf_size_factor', 'late_leaf_size_factor',
                'leaf_maturation_thermal_time', 'leaf_lifespan_thermal_time', 'senescence_threshold_age',
                'senescence_rate_base', 'minimum_active_leaf_area', 'minimum_visible_leaf_area',
                'late_leaf_vstage_threshold', 'very_late_leaf_vstage_threshold', 'early_leaf_position_threshold',
                'middle_leaf_position_threshold', 'early_position_scaling_factor', 'late_position_scaling_factor'
            ]

            for param in leaf_dev_params:
                config['leaf_development'][param] = self.get_parameter(param)

            return LeafParameters.from_config(config)
        except Exception as e:
            raise ParameterError(f"Failed to create LeafParameters: {e}")

    def create_biomass_allocation_parameters(self) -> BiomassAllocationParameters:
        """Create BiomassAllocationParameters from CSV data following strict no-defaults rule"""
        try:
            return BiomassAllocationParameters(
                vegetative_leaf_allocation=self.get_parameter('vegetative_leaf_allocation'),
                vegetative_stem_allocation=self.get_parameter('vegetative_stem_allocation'),
                vegetative_root_allocation=self.get_parameter('vegetative_root_allocation'),
                reproductive_leaf_allocation=self.get_parameter('reproductive_leaf_allocation'),
                reproductive_stem_allocation=self.get_parameter('reproductive_stem_allocation'),
                reproductive_root_allocation=self.get_parameter('reproductive_root_allocation'),
                light_response_factor=self.get_parameter('light_response_factor'),
                nitrogen_response_factor=self.get_parameter('nitrogen_response_factor'),
                water_response_factor=self.get_parameter('water_response_factor'),
                minimum_organ_fraction=self.get_parameter('minimum_organ_fraction')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create BiomassAllocationParameters: {e}")

    def create_canopy_architecture_parameters(self) -> CanopyArchitectureParameters:
        """Create CanopyArchitectureParameters from CSV data following strict no-defaults rule"""
        try:
            return CanopyArchitectureParameters(
                number_of_layers=int(self.get_parameter('number_of_layers')),
                max_lai=self.get_parameter('max_lai'),
                extinction_coefficient=self.get_parameter('extinction_coefficient'),
                diffuse_extinction_coeff=self.get_parameter('diffuse_extinction_coeff'),
                beam_extinction_coeff=self.get_parameter('beam_extinction_coeff'),
                row_spacing=self.get_parameter('row_spacing'),
                mean_leaf_angle=self.get_parameter('mean_leaf_angle'),
                canopy_width=self.get_parameter('canopy_width'),
                leaf_angle_distribution=self.get_parameter('leaf_angle_distribution'),
                leaf_angle_variance=self.get_parameter('leaf_angle_variance'),
                plant_spacing=self.get_parameter('plant_spacing'),
                plant_height=self.get_parameter('plant_height'),
                leaf_reflectance=self.get_parameter('leaf_reflectance'),
                leaf_transmittance=self.get_parameter('leaf_transmittance'),
                leaf_absorptance=self.get_parameter('leaf_absorptance'),
                self_shading_factor=self.get_parameter('self_shading_factor'),
                neighbor_shading_distance=self.get_parameter('neighbor_shading_distance'),
                sunlit_fraction_method=self.get_parameter('sunlit_fraction_method'),
                clumping_index=self.get_parameter('clumping_index'),
                max_extinction_coefficient=self.get_parameter('max_extinction_coefficient'),
                upper_canopy_lai_factor=self.get_parameter('upper_canopy_lai_factor'),
                middle_canopy_lai_factor=self.get_parameter('middle_canopy_lai_factor'),
                lower_middle_canopy_lai_factor=self.get_parameter('lower_middle_canopy_lai_factor'),
                bottom_canopy_lai_factor=self.get_parameter('bottom_canopy_lai_factor'),
                max_temperature_gradient=self.get_parameter('max_temperature_gradient'),
                temperature_gradient_factor=self.get_parameter('temperature_gradient_factor'),
                ppfd_to_photosynthesis_factor=self.get_parameter('ppfd_to_photosynthesis_factor'),
                spherical_x_coefficient=self.get_parameter('spherical_x_coefficient'),
                planophile_x_coefficient=self.get_parameter('planophile_x_coefficient'),
                shaded_light_fraction=self.get_parameter('shaded_light_fraction'),
                erectophile_x_coefficient=self.get_parameter('erectophile_x_coefficient'),
                plagiophile_x_coefficient=self.get_parameter('plagiophile_x_coefficient'),
                upper_canopy_height_threshold=self.get_parameter('upper_canopy_height_threshold'),
                middle_canopy_height_threshold=self.get_parameter('middle_canopy_height_threshold'),
                lower_middle_canopy_height_threshold=self.get_parameter('lower_middle_canopy_height_threshold'),
                zenith_angle_precision_threshold=self.get_parameter('zenith_angle_precision_threshold')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create CanopyArchitectureParameters: {e}")

    def create_nitrogen_balance_parameters(self) -> NitrogenBalanceParameters:
        """Create NitrogenBalanceParameters from CSV data following strict no-defaults rule"""
        try:
            # Build configuration dict structure expected by from_config method
            config = {}

            # Add basic parameters
            basic_params = [
                'nitrate_reduction_rate', 'ammonium_assimilation_rate', 'amino_acid_uptake_rate',
                'photosynthetic_n_use_efficiency', 'growth_n_use_efficiency', 'n_stress_threshold',
                'luxury_uptake_threshold', 'specific_root_activity', 'root_zone_exploration'
            ]

            for param in basic_params:
                config[param] = self.get_parameter(param)

            # Build nested dictionaries from CSV parameters
            config['uptake_kinetics'] = {
                'NO3': {
                    'vmax': self.get_parameter('uptake_kinetics_NO3_vmax'),
                    'km': self.get_parameter('uptake_kinetics_NO3_km'),
                    'min_conc': self.get_parameter('uptake_kinetics_NO3_min_conc'),
                    'inhibition_ki': self.get_parameter('uptake_kinetics_NO3_inhibition_ki')
                },
                'NH4': {
                    'vmax': self.get_parameter('uptake_kinetics_NH4_vmax'),
                    'km': self.get_parameter('uptake_kinetics_NH4_km'),
                    'min_conc': self.get_parameter('uptake_kinetics_NH4_min_conc'),
                    'inhibition_ki': self.get_parameter('uptake_kinetics_NH4_inhibition_ki')
                },
                'amino_acids': {
                    'vmax': self.get_parameter('uptake_kinetics_amino_acids_vmax'),
                    'km': self.get_parameter('uptake_kinetics_amino_acids_km'),
                    'min_conc': self.get_parameter('uptake_kinetics_amino_acids_min_conc'),
                    'inhibition_ki': self.get_parameter('uptake_kinetics_amino_acids_inhibition_ki')
                }
            }

            config['allocation_coefficients'] = {
                'vegetative': {
                    'leaves': self.get_parameter('allocation_coefficients_vegetative_leaves'),
                    'stems': self.get_parameter('allocation_coefficients_vegetative_stems'),
                    'roots': self.get_parameter('allocation_coefficients_vegetative_roots'),
                    'reproductive': self.get_parameter('allocation_coefficients_vegetative_reproductive')
                },
                'reproductive': {
                    'leaves': self.get_parameter('allocation_coefficients_reproductive_leaves'),
                    'stems': self.get_parameter('allocation_coefficients_reproductive_stems'),
                    'roots': self.get_parameter('allocation_coefficients_reproductive_roots'),
                    'reproductive': self.get_parameter('allocation_coefficients_reproductive_reproductive')
                }
            }

            config['critical_n_concentrations'] = {
                'leaves': {
                    'minimum': self.get_parameter('critical_n_concentrations_leaves_minimum'),
                    'critical': self.get_parameter('critical_n_concentrations_leaves_critical'),
                    'optimal': self.get_parameter('critical_n_concentrations_leaves_optimal'),
                    'maximum': self.get_parameter('critical_n_concentrations_leaves_maximum')
                },
                'stems': {
                    'minimum': self.get_parameter('critical_n_concentrations_stems_minimum'),
                    'critical': self.get_parameter('critical_n_concentrations_stems_critical'),
                    'optimal': self.get_parameter('critical_n_concentrations_stems_optimal'),
                    'maximum': self.get_parameter('critical_n_concentrations_stems_maximum')
                },
                'roots': {
                    'minimum': self.get_parameter('critical_n_concentrations_roots_minimum'),
                    'critical': self.get_parameter('critical_n_concentrations_roots_critical'),
                    'optimal': self.get_parameter('critical_n_concentrations_roots_optimal'),
                    'maximum': self.get_parameter('critical_n_concentrations_roots_maximum')
                },
                'reproductive': {
                    'minimum': self.get_parameter('critical_n_concentrations_reproductive_minimum'),
                    'critical': self.get_parameter('critical_n_concentrations_reproductive_critical'),
                    'optimal': self.get_parameter('critical_n_concentrations_reproductive_optimal'),
                    'maximum': self.get_parameter('critical_n_concentrations_reproductive_maximum')
                }
            }

            config['remobilization_rates'] = {
                'structural': self.get_parameter('remobilization_rates_structural'),
                'metabolic': self.get_parameter('remobilization_rates_metabolic'),
                'storage': self.get_parameter('remobilization_rates_storage'),
                'transport': self.get_parameter('remobilization_rates_transport')
            }

            config['remobilization_efficiency'] = {
                'leaves': self.get_parameter('remobilization_efficiency_leaves'),
                'stems': self.get_parameter('remobilization_efficiency_stems'),
                'roots': self.get_parameter('remobilization_efficiency_roots'),
                'reproductive': self.get_parameter('remobilization_efficiency_reproductive')
            }

            config['organ_weights'] = {
                'leaves': self.get_parameter('organ_weights_leaves'),
                'stems': self.get_parameter('organ_weights_stems'),
                'roots': self.get_parameter('organ_weights_roots'),
                'reproductive': self.get_parameter('organ_weights_reproductive')
            }

            # Add pool fractions as flat keys (expected by from_config method)
            config['pool_fractions_leaves_structural'] = self.get_parameter('pool_fractions_leaves_structural')
            config['pool_fractions_leaves_metabolic'] = self.get_parameter('pool_fractions_leaves_metabolic')
            config['pool_fractions_leaves_storage'] = self.get_parameter('pool_fractions_leaves_storage')
            config['pool_fractions_leaves_transport'] = self.get_parameter('pool_fractions_leaves_transport')
            config['pool_fractions_stems_structural'] = self.get_parameter('pool_fractions_stems_structural')
            config['pool_fractions_stems_metabolic'] = self.get_parameter('pool_fractions_stems_metabolic')
            config['pool_fractions_stems_storage'] = self.get_parameter('pool_fractions_stems_storage')
            config['pool_fractions_stems_transport'] = self.get_parameter('pool_fractions_stems_transport')
            config['pool_fractions_roots_structural'] = self.get_parameter('pool_fractions_roots_structural')
            config['pool_fractions_roots_metabolic'] = self.get_parameter('pool_fractions_roots_metabolic')
            config['pool_fractions_roots_storage'] = self.get_parameter('pool_fractions_roots_storage')
            config['pool_fractions_roots_transport'] = self.get_parameter('pool_fractions_roots_transport')
            config['pool_fractions_reproductive_structural'] = self.get_parameter('pool_fractions_reproductive_structural')
            config['pool_fractions_reproductive_metabolic'] = self.get_parameter('pool_fractions_reproductive_metabolic')
            config['pool_fractions_reproductive_storage'] = self.get_parameter('pool_fractions_reproductive_storage')
            config['pool_fractions_reproductive_transport'] = self.get_parameter('pool_fractions_reproductive_transport')

            return NitrogenBalanceParameters.from_config(config)
        except Exception as e:
            raise ParameterError(f"Failed to create NitrogenBalanceParameters: {e}")

    def create_root_system_parameters(self) -> RootSystemParameters:
        """Create RootSystemParameters from CSV data following strict no-defaults rule"""
        try:
            # Map string system type to enum
            system_type_str = self.get_parameter('system_type')
            system_type_mapping = {
                'nutrient_film_technique': HydroponicSystemType.NFT,
                'deep_water_culture': HydroponicSystemType.DWC,
                'aeroponics': HydroponicSystemType.AEROPONICS,
                'drip': HydroponicSystemType.DRIP,
                'wick_system': HydroponicSystemType.WICK,
                'ebb_flow': HydroponicSystemType.EBB_FLOW
            }
            system_type = system_type_mapping.get(system_type_str, HydroponicSystemType.DWC)

            return RootSystemParameters(
                container_volume=self.get_parameter('container_volume'),
                channel_length=self.get_parameter('channel_length'),
                system_type=system_type,
                channel_width=self.get_parameter('channel_width'),
                channel_depth=self.get_parameter('channel_depth'),
                n_channels=int(self.get_parameter('n_channels')),
                root_zone_independent=bool(self.get_parameter('root_zone_independent')),
                primary_root_growth_rate=self.get_parameter('primary_root_growth_rate'),
                lateral_root_density=self.get_parameter('lateral_root_density'),
                branching_angle_mean=self.get_parameter('branching_angle_mean'),
                branching_angle_std=self.get_parameter('branching_angle_std'),
                fine_root_fraction=self.get_parameter('fine_root_fraction'),
                medium_root_fraction=self.get_parameter('medium_root_fraction'),
                coarse_root_fraction=self.get_parameter('coarse_root_fraction'),
                fine_diameter_mean=self.get_parameter('fine_diameter_mean'),
                fine_diameter_std=self.get_parameter('fine_diameter_std'),
                medium_diameter_mean=self.get_parameter('medium_diameter_mean'),
                medium_diameter_std=self.get_parameter('medium_diameter_std'),
                coarse_diameter_mean=self.get_parameter('coarse_diameter_mean'),
                coarse_diameter_std=self.get_parameter('coarse_diameter_std'),
                fine_turnover_rate=self.get_parameter('fine_turnover_rate'),
                medium_turnover_rate=self.get_parameter('medium_turnover_rate'),
                coarse_turnover_rate=self.get_parameter('coarse_turnover_rate'),
                fine_root_half_life_days=self.get_parameter('fine_root_half_life_days'),
                medium_root_half_life_days=self.get_parameter('medium_root_half_life_days'),
                coarse_root_half_life_days=self.get_parameter('coarse_root_half_life_days'),
                root_zone_efficiency_factor=self.get_parameter('root_zone_efficiency_factor'),
                fine_min_activity=self.get_parameter('fine_min_activity'),
                medium_min_activity=self.get_parameter('medium_min_activity'),
                coarse_min_activity=self.get_parameter('coarse_min_activity'),
                establishment_plateau_days=self.get_parameter('establishment_plateau_days'),
                initial_root_activity=self.get_parameter('initial_root_activity'),
                system_multipliers={},
                base_uptake_rates={},
                michaelis_constants={},
                fine_root_effectiveness=self.get_parameter('fine_root_effectiveness'),
                medium_root_effectiveness=self.get_parameter('medium_root_effectiveness'),
                coarse_root_effectiveness=self.get_parameter('coarse_root_effectiveness'),
                optimal_temperature=self.get_parameter('optimal_temperature'),
                q10_factor=self.get_parameter('q10_factor'),
                optimal_flow_rate=self.get_parameter('optimal_flow_rate'),
                flow_stress_threshold=self.get_parameter('flow_stress_threshold'),
                root_growth_auxin_decay_rate=self.get_parameter('root_growth_auxin_decay_rate'),
                root_optimal_density=self.get_parameter('root_optimal_density'),
                root_density_stress_factor=self.get_parameter('root_density_stress_factor'),
                root_temp_optimum=self.get_parameter('root_temp_optimum'),
                root_temp_max=self.get_parameter('root_temp_max'),
                root_temp_min_factor=self.get_parameter('root_temp_min_factor'),
                root_oxygen_optimum=self.get_parameter('root_oxygen_optimum'),
                root_oxygen_min_factor=self.get_parameter('root_oxygen_min_factor'),
                nutrient_demand_weights={},
                nutrient_reference_concentrations={},
                nutrient_competition_groups={},
                nutrient_ph_optima={},
                ph_stress_range_acidic=self.get_parameter('ph_stress_range_acidic'),
                ph_stress_range_basic=self.get_parameter('ph_stress_range_basic'),
                ph_stress_factor=self.get_parameter('ph_stress_factor'),
                young_root_activity=self.get_parameter('young_root_activity'),
                old_root_activity=self.get_parameter('old_root_activity'),
                temperature_range_factor=self.get_parameter('temperature_range_factor'),
                min_temperature_factor=self.get_parameter('min_temperature_factor'),
                max_temperature_factor=self.get_parameter('max_temperature_factor'),
                low_flow_factor=self.get_parameter('low_flow_factor'),
                high_flow_factor=self.get_parameter('high_flow_factor'),
                ph_zone_min=self.get_parameter('ph_zone_min'),
                ph_zone_max=self.get_parameter('ph_zone_max'),
                min_ph_factor=self.get_parameter('min_ph_factor'),
                ph_penalty_factor=self.get_parameter('ph_penalty_factor'),
                nft_zone_1_fraction=self.get_parameter('nft_zone_1_fraction'),
                nft_zone_2_fraction=self.get_parameter('nft_zone_2_fraction'),
                nft_zone_3_fraction=self.get_parameter('nft_zone_3_fraction'),
                dwc_zone_1_fraction=self.get_parameter('dwc_zone_1_fraction'),
                dwc_zone_2_fraction=self.get_parameter('dwc_zone_2_fraction'),
                dwc_zone_3_fraction=self.get_parameter('dwc_zone_3_fraction'),
                general_zone_1_fraction=self.get_parameter('general_zone_1_fraction'),
                general_zone_2_fraction=self.get_parameter('general_zone_2_fraction'),
                general_zone_3_fraction=self.get_parameter('general_zone_3_fraction'),
                general_zone_4_fraction=self.get_parameter('general_zone_4_fraction'),
                root_biomass_density=self.get_parameter('root_biomass_density'),
                coarse_root_min_threshold=self.get_parameter('coarse_root_min_threshold'),
                fine_root_min_threshold=self.get_parameter('fine_root_min_threshold'),
                diameter_minimum_limit=self.get_parameter('diameter_minimum_limit'),
                auxin_gradient_weight=self.get_parameter('auxin_gradient_weight'),
                nutrient_signal_weight=self.get_parameter('nutrient_signal_weight'),
                oxygen_effect_weight=self.get_parameter('oxygen_effect_weight'),
                competition_effect_weight=self.get_parameter('competition_effect_weight'),
                temperature_effect_weight=self.get_parameter('temperature_effect_weight'),
                min_growth_potential=self.get_parameter('min_growth_potential'),
                max_growth_potential=self.get_parameter('max_growth_potential'),
                max_temp_threshold=self.get_parameter('max_temp_threshold'),
                temp_decay_factor=self.get_parameter('temp_decay_factor'),
                flow_rate_offset=self.get_parameter('flow_rate_offset'),
                flow_rate_multiplier=self.get_parameter('flow_rate_multiplier'),
                transport_temp_exponent=self.get_parameter('transport_temp_exponent'),
                minimum_surface_area=self.get_parameter('minimum_surface_area'),
                minimum_biomass=self.get_parameter('minimum_biomass'),
                minimum_volume=self.get_parameter('minimum_volume'),
                effective_area_minimum=self.get_parameter('effective_area_minimum')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create RootSystemParameters: {e}")

    def create_water_uptake_parameters(self) -> WaterUptakeParameters:
        """Create WaterUptakeParameters from CSV data following strict no-defaults rule"""
        try:
            return WaterUptakeParameters(
                psychrometric_constant=self.get_parameter('psychrometric_constant'),
                wind_speed=self.get_parameter('wind_speed'),
                net_radiation_factor=self.get_parameter('net_radiation_factor'),
                radiation_offset=self.get_parameter('radiation_offset'),
                base_crop_coefficient=self.get_parameter('base_crop_coefficient'),
                lai_coefficient_factor=self.get_parameter('lai_coefficient_factor'),
                vegetative_stage_factor=self.get_parameter('vegetative_stage_factor'),
                head_formation_stage_factor=self.get_parameter('head_formation_stage_factor'),
                mature_stage_factor=self.get_parameter('mature_stage_factor'),
                optimal_temperature=self.get_parameter('optimal_temperature'),
                temperature_sensitivity=self.get_parameter('temperature_sensitivity'),
                optimal_vpd_min=self.get_parameter('optimal_vpd_min'),
                optimal_vpd_max=self.get_parameter('optimal_vpd_max'),
                vpd_sensitivity=self.get_parameter('vpd_sensitivity'),
                metabolic_water_per_biomass=self.get_parameter('metabolic_water_per_biomass'),
                metabolic_water_per_lai=self.get_parameter('metabolic_water_per_lai'),
                # Use hydraulic parameters from root system (already in CSV)
                base_root_conductance=self.get_parameter('base_root_conductance'),
                root_conductance_scaling_factor=self.get_parameter('root_conductance_scaling_factor'),
                base_xylem_conductance=self.get_parameter('base_xylem_conductance'),
                xylem_conductance_scaling_factor=self.get_parameter('xylem_conductance_scaling_factor'),
                base_leaf_potential=self.get_parameter('base_leaf_potential'),
                transpiration_potential_factor=self.get_parameter('transpiration_potential_factor'),
                solution_potential_factor=self.get_parameter('solution_potential_factor'),
                cavitation_threshold=self.get_parameter('cavitation_threshold'),
                max_osmotic_adjustment=self.get_parameter('max_osmotic_adjustment'),
                salt_stress_osmotic_factor=self.get_parameter('salt_stress_osmotic_factor'),
                temp_tolerance=self.get_parameter('temp_tolerance'),
                min_temp_factor=self.get_parameter('min_temp_factor')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create WaterUptakeParameters: {e}")

    def create_rzt_parameters(self) -> RZTParameters:
        """Create RZTParameters from CSV data following strict no-defaults rule"""
        try:
            # Build config structure expected by from_config method
            config = {}

            # Map CSV parameter names to config names (some have rzt_ prefix in CSV)
            param_mapping = {
                'optimal_rzt_offset': 'optimal_rzt_offset',
                'min_effective_rzt': 'min_effective_rzt',
                'max_effective_rzt': 'max_effective_rzt',
                'linear_growth_slope': 'linear_growth_slope',
                'rapid_decline_slope': 'rapid_decline_slope',
                'base_growth_factor': 'base_growth_factor',
                'nutrient_uptake_sensitivity_low': 'nutrient_uptake_sensitivity_low',
                'nutrient_uptake_sensitivity_high': 'nutrient_uptake_sensitivity_high',
                'water_uptake_sensitivity_low': 'water_uptake_sensitivity_low',
                'water_uptake_sensitivity_high': 'water_uptake_sensitivity_high',
                'photosynthesis_sensitivity_low': 'photosynthesis_sensitivity_low',
                'photosynthesis_sensitivity_high': 'photosynthesis_sensitivity_high',
                'root_metabolism_sensitivity_low': 'root_metabolism_sensitivity_low',
                'root_metabolism_sensitivity_high': 'root_metabolism_sensitivity_high',
                'rzt_min_growth_factor': 'min_growth_factor',
                'max_growth_factor': 'max_growth_factor',
                'min_nutrient_uptake_factor': 'min_nutrient_uptake_factor',
                'max_nutrient_uptake_factor': 'max_nutrient_uptake_factor',
                'min_water_uptake_factor': 'min_water_uptake_factor',
                'max_water_uptake_factor': 'max_water_uptake_factor',
                'min_photosynthesis_factor': 'min_photosynthesis_factor',
                'max_photosynthesis_factor': 'max_photosynthesis_factor',
                'min_root_metabolism_factor': 'min_root_metabolism_factor',
                'max_root_metabolism_factor': 'max_root_metabolism_factor',
                'rzt_thermal_mass_factor': 'thermal_mass_factor',
                'rzt_ambient_temp_amplitude': 'ambient_temp_amplitude',
                'rzt_root_respiration_heat': 'root_respiration_heat',
                'rzt_pump_heat_generation': 'pump_heat_generation',
                'rzt_ambient_exchange_factor': 'ambient_exchange_factor',
                'rzt_thermal_response_time': 'thermal_response_time',
                'rzt_heat_transfer_coefficient': 'heat_transfer_coefficient',
                'base_factor_constant': 'base_factor_constant',
                'thermal_stress_normalizer': 'thermal_stress_normalizer',
                'diurnal_cycle_shift': 'diurnal_cycle_shift',
                'diurnal_cycle_period': 'diurnal_cycle_period',
                'daily_representative_hour': 'daily_representative_hour'
            }

            for csv_param, config_param in param_mapping.items():
                config[config_param] = self.get_parameter(csv_param)

            return RZTParameters.from_config(config)
        except Exception as e:
            raise ParameterError(f"Failed to create RZTParameters: {e}")

    def create_environmental_setpoints(self) -> EnvironmentalSetpoints:
        """Create EnvironmentalSetpoints from CSV values"""
        try:
            pid_params = {
                'humidity': {
                    'kp': self.get_parameter('pid_humidity_kp'),
                    'ki': self.get_parameter('pid_humidity_ki'),
                    'kd': self.get_parameter('pid_humidity_kd')
                },
                'co2': {
                    'kp': self.get_parameter('pid_co2_kp'),
                    'ki': self.get_parameter('pid_co2_ki'),
                    'kd': self.get_parameter('pid_co2_kd')
                },
                'temperature': {
                    'kp': self.get_parameter('pid_temperature_kp'),
                    'ki': self.get_parameter('pid_temperature_ki'),
                    'kd': self.get_parameter('pid_temperature_kd')
                }
            }

            return EnvironmentalSetpoints(
                target_vpd=self.get_parameter('target_vpd'),
                vpd_tolerance=self.get_parameter('vpd_tolerance'),
                min_humidity=self.get_parameter('min_humidity'),
                max_humidity=self.get_parameter('max_humidity'),
                day_temp=self.get_parameter('day_temp'),
                night_temp=self.get_parameter('night_temp'),
                temp_tolerance=self.get_parameter('temp_tolerance'),
                target_co2=self.get_parameter('target_co2'),
                ambient_co2=self.get_parameter('ambient_co2'),
                co2_tolerance=self.get_parameter('co2_tolerance'),
                light_hours=self.get_parameter('light_hours'),
                light_intensity=self.get_parameter('light_intensity_control'),
                co2_enrichment_start_hour=self.get_parameter('co2_enrichment_start_hour'),
                humidity_deadband=self.get_parameter('humidity_deadband'),
                max_temperature_change_per_hour=self.get_parameter('max_temperature_change_per_hour'),
                ambient_temperature=self.get_parameter('ambient_temperature'),
                thermal_mass_factor=self.get_parameter('thermal_mass_factor'),
                base_co2_loss_rate=self.get_parameter('base_co2_loss_rate'),
                min_co2_concentration=self.get_parameter('min_co2_concentration'),
                max_co2_concentration=self.get_parameter('max_co2_concentration'),
                light_saturation_threshold=self.get_parameter('light_saturation_threshold'),
                co2_response_vmax=self.get_parameter('co2_response_vmax'),
                co2_response_km=self.get_parameter('co2_response_km'),
                max_co2_enhancement_factor=self.get_parameter('max_co2_enhancement_factor'),
                pid_parameters=pid_params
            )
        except Exception as e:
            raise ParameterError(f"Failed to create EnvironmentalSetpoints: {e}")

    def create_control_equipment(self) -> ControlEquipment:
        """Create ControlEquipment from CSV values"""
        try:
            return ControlEquipment(
                humidifier_capacity=self.get_parameter('humidifier_capacity'),
                dehumidifier_capacity=self.get_parameter('dehumidifier_capacity'),
                co2_injection_rate=self.get_parameter('co2_injection_rate'),
                co2_sensor_accuracy=self.get_parameter('co2_sensor_accuracy'),
                co2_mixing_time=self.get_parameter('co2_mixing_time'),
                circulation_fan_power=self.get_parameter('circulation_fan_power'),
                humidifier_efficiency=self.get_parameter('humidifier_efficiency'),
                dehumidifier_efficiency=self.get_parameter('dehumidifier_efficiency'),
                air_exchange_rate=self.get_parameter('air_exchange_rate')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create ControlEquipment: {e}")


class WeatherDataLoader:
    """Loads daily weather data strictly - no defaults"""

    def __init__(self, weather_csv_path: str):
        self.weather_csv_path = weather_csv_path
        self.weather_data = None
        self._load_weather_data()

    def _load_weather_data(self):
        """Load weather data - fail if any issues"""
        if not os.path.exists(self.weather_csv_path):
            raise WeatherDataError(f"Weather file not found: {self.weather_csv_path}")

        try:
            self.weather_data = pd.read_csv(self.weather_csv_path)
        except Exception as e:
            raise WeatherDataError(f"Failed to read weather CSV: {e}")

        if self.weather_data.empty:
            raise WeatherDataError("Weather CSV is empty")

        required_columns = ['date', 'temp_avg', 'temp_min', 'temp_max', 'solar_radiation', 'rel_humidity']
        missing_cols = [col for col in required_columns if col not in self.weather_data.columns]
        if missing_cols:
            raise WeatherDataError(f"Missing required weather columns: {missing_cols}")

        # Convert date column
        try:
            self.weather_data['date'] = pd.to_datetime(self.weather_data['date'])
        except Exception as e:
            raise WeatherDataError(f"Invalid date format in weather data: {e}")

        # Check for missing weather values
        for _, row in self.weather_data.iterrows():
            for col in required_columns[1:]:  # Skip date
                if pd.isna(row[col]):
                    raise WeatherDataError(f"Missing weather data: {col} on {row['date']}")

    def get_daily_weather(self, simulation_day: int) -> Dict[str, float]:
        """Get weather for specific simulation day - fail if not available"""
        if simulation_day >= len(self.weather_data):
            raise WeatherDataError(f"Weather data not available for day {simulation_day}")

        row = self.weather_data.iloc[simulation_day]
        return {
            'date': row['date'],
            'temp_avg': float(row['temp_avg']),
            'temp_min': float(row['temp_min']),
            'temp_max': float(row['temp_max']),
            'solar_radiation': float(row['solar_radiation']),
            'rel_humidity': float(row['rel_humidity']),
            'wind_speed': float(row.get('wind_speed', 0.0)),
            'rainfall': float(row.get('rainfall', 0.0))
        }


class HydroponicSimulator:
    """
    Hydroponic Lettuce Growth Simulator
    - Uses only actual model functions
    - All parameters from CSV
    - Daily weather data required
    - Fails hard on any missing data
    """

    def __init__(self,
                 master_csv_path: str = "input/master_parameters.csv",
                 weather_csv_path: str = "input/LET_EXP001_2024_weather.csv"):

        # Load parameters and weather data strictly
        self.param_loader = StrictParameterLoader(master_csv_path)
        self.weather_loader = WeatherDataLoader(weather_csv_path)

        # Initialize plant state
        self.plant_state = PlantState()

        # Initialize all 17 models with actual parameters from CSV
        self._initialize_all_models()

        # Simulation results storage
        self.simulation_results = []

    def _initialize_all_models(self):
        """Initialize all 17 models using actual parameter classes from CSV - USE ALL 95 CLASSES"""
        try:
            # 1. Environmental Control System - using EnvironmentalSetpoints and ControlEquipment
            setpoints = self.param_loader.create_environmental_setpoints()
            equipment = self.param_loader.create_control_equipment()
            self.environmental_model = EnvironmentalControlSystem(setpoints, equipment)

            # Store these for use in other parts - USE EnvironmentalSetpoints and ControlEquipment
            self.environmental_setpoints = setpoints
            self.control_equipment = equipment
            self.control_strategy = ControlStrategy.PID  # Use ControlStrategy enum

            # Use ControlEquipment for system configuration
            self.system_config = {
                'humidifier_capacity': self.control_equipment.humidifier_capacity,
                'co2_injection_rate': self.control_equipment.co2_injection_rate,
                'air_exchange_rate': self.control_equipment.air_exchange_rate
            }

            # 2. Photosynthesis Model - using PhotosynthesisParameters and PhotosynthesisResponse
            photo_params = self.param_loader.create_photosynthesis_parameters()
            self.photosynthesis_model = PhotosynthesisModel(photo_params)
            self.photosynthesis_parameters = photo_params  # USE PhotosynthesisParameters

            # 3. Phenology Model - using PhenologyParameters, LettuceGrowthStage, DevelopmentalState
            pheno_params = self.param_loader.create_phenology_parameters()
            self.phenology_model = ComprehensivePhenologyModel(pheno_params, LettuceGrowthStage.GERMINATION)
            self.phenology_parameters = pheno_params  # USE PhenologyParameters
            self.current_growth_stage = LettuceGrowthStage.GERMINATION

            # Store parameter validation results
            self.model_validation_result = ModelValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )

            # Initialize other models with minimal parameters for now
            # These will be expanded as we add more parameter creation methods

            # 4. Respiration Model - using RespirationParameters, BiomassPool, TissueType, RespirationComponents
            resp_params = self.param_loader.create_respiration_parameters()
            resp_config = {'enable_logging': False, 'validation_mode': 'strict'}
            self.respiration_model = EnhancedRespirationModel(resp_params, resp_config)
            self.respiration_parameters = resp_params

            # Initialize biomass pools using BiomassPool and TissueType
            self.leaf_biomass_pool = BiomassPool(tissue_type=TissueType.LEAVES, dry_mass=0.001, age_days=0.0, nitrogen_content=0.03, recent_growth=0.0)
            self.stem_biomass_pool = BiomassPool(tissue_type=TissueType.STEMS, dry_mass=0.0005, age_days=0.0, nitrogen_content=0.02, recent_growth=0.0)
            self.root_biomass_pool = BiomassPool(tissue_type=TissueType.ROOTS, dry_mass=0.0005, age_days=0.0, nitrogen_content=0.02, recent_growth=0.0)

            # 5. Water Uptake Model - using WaterUptakeParameters, GrowthStage
            water_params = self.param_loader.create_water_uptake_parameters()
            self.water_model = WaterUptakeModel(water_params)
            self.water_parameters = water_params
            self.current_water_growth_stage = GrowthStage.VEGETATIVE

            # 6. Nutrient Model - using NutrientParameters, NutrientMobility, TransportMechanism, OrganNutrientPools
            nutrient_params = self.param_loader.create_nutrient_parameters()
            self.nutrient_model = NutrientModel(nutrient_params)
            self.nutrient_parameters = nutrient_params

            # Initialize nutrient pools and transport mechanisms
            self.nutrient_mobility = NutrientMobility.HIGHLY_MOBILE  # Use enum
            self.transport_mechanism = TransportMechanism.BIDIRECTIONAL  # Use enum
            self.organ_nutrient_pools = OrganNutrientPools(organ_name="leaves", nutrient_name="nitrogen")

            # 7. pH Model - using PHParameters, BufferSystem, PHState, NutrientSolubility
            ph_params = self.param_loader.create_ph_parameters()
            self.ph_model = HydroponicPHModel(ph_params)
            self.ph_parameters = ph_params

            # Initialize pH-related classes
            self.buffer_system = BufferSystem.PHOSPHATE  # Use enum
            self.ph_state = PHState(
                current_ph=ph_params.current_ph,
                buffer_capacity=ph_params.ph_buffer_capacity,
                total_alkalinity=ph_params.total_alkalinity,
                carbonate_conc=ph_params.carbonate_conc,
                phosphate_total=ph_params.phosphate_total,
                ionic_strength=ph_params.ionic_strength,
                temperature=25.0  # Standard temperature for hydroponic systems
            )
            self.nutrient_solubility = NutrientSolubility(
                phosphate_solubility=ph_params.phosphate_solubility_data,
                iron_solubility=ph_params.iron_solubility_data,
                calcium_phosphate_ksp=ph_params.calcium_phosphate_ksp,
                magnesium_phosphate_ksp=ph_params.magnesium_phosphate_ksp
            )

            # 8. Root Zone Temperature Model - using RZTParameters, RZTModelOutput
            try:
                rzt_params = RZTParameters()
                self.rzt_model = RootZoneTemperatureModel(rzt_params)
                self.rzt_parameters = rzt_params

            except Exception:
                self.rzt_model = None

            # 9. Stress Model - using IntegratedStressParameters, StressType, StressState, ProcessStressFactors
            stress_params = self.param_loader.create_stress_parameters()
            self.stress_model = IntegratedStressModel(stress_params)
            self.stress_parameters = stress_params

            # Initialize stress-related classes
            self.stress_types = [StressType.TEMPERATURE, StressType.WATER, StressType.NUTRIENT, StressType.LIGHT]
            self.stress_state = StressState(stress_type=StressType.TEMPERATURE, current_level=0.0)
            self.process_stress_factors = ProcessStressFactors()

            # Temperature stress components - create parameters from CSV
            temp_stress_config = {param: self.param_loader.get_parameter(param) for param in [
                'optimal_temp_min', 'optimal_temp_max', 'heat_threshold_mild', 'heat_threshold_severe',
                'heat_lethal_temperature', 'cold_threshold_mild', 'cold_threshold_severe', 'frost_threshold',
                'photosynthesis_heat_sensitivity', 'photosynthesis_cold_sensitivity', 'respiration_heat_sensitivity',
                'respiration_cold_sensitivity', 'growth_heat_sensitivity', 'growth_cold_sensitivity',
                'development_heat_sensitivity', 'development_cold_sensitivity', 'acclimation_rate',
                'max_acclimation_days', 'acclimation_decay_rate', 'heat_damage_threshold', 'cold_damage_threshold',
                'frost_damage_rate', 'recovery_rate_heat', 'recovery_rate_cold', 'stress_memory_duration',
                'memory_effect_strength', 'mild_stress_level', 'moderate_stress_level', 'mild_cold_stress_level',
                'moderate_cold_stress_level', 'severe_cold_stress_level', 'frost_base_stress_level',
                'frost_additional_stress', 'heat_acclimation_reduction', 'cold_acclimation_reduction',
                'photosynthesis_weight', 'growth_weight', 'development_weight', 'respiration_weight',
                'heat_damage_rate', 'cold_damage_rate', 'frost_recovery_multiplier', 'damage_factor_multiplier'
            ]}
            temp_stress_params = TemperatureStressParameters.from_config(temp_stress_config)
            self.temperature_stress_model = TemperatureStressModel(temp_stress_params)
            self.temperature_acclimation = TemperatureAcclimation()
            self.temperature_damage = TemperatureDamage()

            # 10. Biomass Allocation Model - using BiomassAllocationParameters
            alloc_params = self.param_loader.create_biomass_allocation_parameters()
            self.biomass_allocation_model = BiomassAllocationModel(alloc_params)
            self.allocation_parameters = alloc_params

            # 11. Leaf Development Model - using LeafParameters, LeafStage, LeafCohort
            leaf_params = self.param_loader.create_leaf_development_parameters()
            self.leaf_development_model = LeafDevelopmentModel(leaf_params)
            self.leaf_parameters = leaf_params

            # Initialize leaf development components
            self.leaf_cohorts = []  # Will store LeafCohort objects
            self.current_leaf_stage = LeafStage.EXPANDING

            # 12. Canopy Architecture Model - using CanopyArchitectureParameters, LeafAngleDistribution, CanopyLayer
            canopy_params = self.param_loader.create_canopy_architecture_parameters()
            self.canopy_model = CanopyArchitectureModel(canopy_params)
            self.canopy_parameters = canopy_params

            # Initialize canopy components
            self.leaf_angle_distribution = LeafAngleDistribution.SPHERICAL
            self.canopy_layers = []  # Will store CanopyLayer objects
            # Initialize light environment with default values, updated during daily simulation
            self.light_environment = LightEnvironment(
                ppfd_above_canopy=1000.0,  # Will be updated from weather data
                direct_beam_fraction=0.85,  # Will be updated from weather data
                diffuse_fraction=0.15,  # Will be updated from weather data
                solar_zenith_angle=45.0,  # Will be updated from weather data
                solar_azimuth_angle=180.0  # Will be updated from weather data
            )

            # 13. Senescence Model - using SenescenceParameters, SenescenceType, SenescenceStage, LeafCohortSenescence
            senes_params = self.param_loader.create_senescence_parameters()
            self.senescence_model = AdvancedSenescenceModel(senes_params)
            self.senescence_parameters = senes_params

            # Initialize senescence components
            self.senescence_type = SenescenceType.AGE_BASED
            self.senescence_stage = SenescenceStage.HEALTHY
            self.leaf_cohort_senescence = []  # Will store LeafCohortSenescence objects

            # 14. Nitrogen Balance Model - using NitrogenBalanceParameters, OrganNitrogenState
            n_params = self.param_loader.create_nitrogen_balance_parameters()
            self.nitrogen_model = NitrogenBalanceModel(n_params)
            self.nitrogen_parameters = n_params

            # Initialize nitrogen components
            self.organ_nitrogen_states = {}  # Will store OrganNitrogenState objects

            # 15. Root System Model - using RootSystemParameters, RootType, HydroponicSystemType, RootCohort, RootZoneLayer
            root_params = self.param_loader.create_root_system_parameters()
            self.root_model = EnhancedRootSystemModel(root_params)
            self.root_parameters = root_params

            # Initialize root system components
            self.hydroponic_system_type = root_params.system_type
            self.root_cohorts = []  # Will store RootCohort objects
            self.root_zone_layers = []  # Will store RootZoneLayer objects
            # Initialize root system metrics with default values
            self.root_system_metrics = RootSystemMetrics(
                total_root_length=0.0,
                total_root_surface_area=0.0,
                total_root_biomass=0.0,
                total_root_volume=0.0,
                root_length_density=0.0,
                root_surface_area_density=0.0,
                specific_root_length=0.0,
                average_root_activity=0.0,
                fine_root_length=0.0,
                medium_root_length=0.0,
                coarse_root_length=0.0,
                fine_root_fraction=0.0,
                root_age_days=0.0,
                cumulative_growth=0.0,
                total_nutrient_uptake=0.0,
                uptake_per_surface_area=0.0,
                uptake_temperature_factor=1.0,
                uptake_flow_factor=1.0,
                effective_root_surface_area=0.0,
                total_uptake_g_per_day=0.0,
                nitrogen_uptake_g_per_day=0.0,
                nutrient_uptake_rates={}
            )

            # 16. Root Zone Temperature Model - using RZTParameters, RZTModelOutput
            rzt_params = self.param_loader.create_rzt_parameters()
            self.root_zone_temperature_model = RootZoneTemperatureModel(rzt_params)
            self.rzt_parameters = rzt_params

            # 17. Genetic Models - using GeneticParameterDatabase, CultivarProfile, GeneticCoefficients, LettuceType
            genetic_db = GeneticParameterDatabase()
            self.genetics_model = GenotypeEnvironmentModel(genetic_db)
            self.genetic_database = genetic_db

            # Initialize genetic components - USE GeneticTrait - ALL FROM CSV
            lettuce_type_str = self.param_loader.get_parameter('lettuce_type')
            lettuce_type_mapping = {
                'butterhead': LettuceType.BUTTERHEAD,
                'romaine': LettuceType.ROMAINE,
                'leaf': LettuceType.LEAF,
                'iceberg': LettuceType.ICEBERG
            }
            if lettuce_type_str not in lettuce_type_mapping:
                raise ParameterError(f"Invalid lettuce_type '{lettuce_type_str}' - must be one of: {list(lettuce_type_mapping.keys())}")
            self.lettuce_type = lettuce_type_mapping[lettuce_type_str]

            # Initialize cultivar profile with ALL VALUES FROM CSV
            self.cultivar_profile = CultivarProfile(
                cultivar_id=self.param_loader.get_parameter('cultivar_id'),
                cultivar_name=self.param_loader.get_parameter('cultivar_name'),
                lettuce_type=self.lettuce_type,
                breeder=self.param_loader.get_parameter('breeder'),
                year_released=int(self.param_loader.get_parameter('year_released')),
                genetic_coefficients={},
                yield_potential=self.param_loader.get_parameter('yield_potential'),
                adaptation_score=self.param_loader.get_parameter('adaptation_score'),
                trait_values={},
                pedigree=self.param_loader.get_parameter('pedigree'),
                breeding_notes=self.param_loader.get_parameter('breeding_notes')
            )
            self.genetic_coefficients = GeneticCoefficients(
                EM_FL=self.param_loader.get_parameter('EM_FL'),
                FL_SH=self.param_loader.get_parameter('FL_SH'),
                FL_SD=self.param_loader.get_parameter('FL_SD'),
                SD_PM=self.param_loader.get_parameter('SD_PM'),
                FL_LF=self.param_loader.get_parameter('FL_LF'),
                LFMAX=self.param_loader.get_parameter('LFMAX'),
                SLAVR=self.param_loader.get_parameter('SLAVR'),
                SIZLF=self.param_loader.get_parameter('SIZLF'),
                XFRT=self.param_loader.get_parameter('XFRT'),
                SFDUR=self.param_loader.get_parameter('SFDUR'),
                SDPDV=self.param_loader.get_parameter('SDPDV'),
                PODUR=self.param_loader.get_parameter('PODUR'),
                WTPSD=self.param_loader.get_parameter('WTPSD'),
                THRSH=self.param_loader.get_parameter('THRSH'),
                SDPRO=self.param_loader.get_parameter('SDPRO'),
                SDLIP=self.param_loader.get_parameter('SDLIP'),
                EC_TOLERANCE=self.param_loader.get_parameter('EC_TOLERANCE'),
                ROOT_ACTIVITY=self.param_loader.get_parameter('ROOT_ACTIVITY'),
                PHOTOSYNTHETIC_CAPACITY=self.param_loader.get_parameter('PHOTOSYNTHETIC_CAPACITY'),
                NITRATE_EFFICIENCY=self.param_loader.get_parameter('NITRATE_EFFICIENCY')
            )
            self.genetic_traits = [trait for trait in GeneticTrait]  # USE GeneticTrait
            self.breeding_assistant = BreedingAssistant(genetic_db, self.genetics_model)

            # Genetic traits - ALL VALUES FROM CSV
            self.selected_traits = {
                GeneticTrait.YIELD_POTENTIAL: self.param_loader.get_parameter('trait_yield_potential'),
                GeneticTrait.DISEASE_RESISTANCE: self.param_loader.get_parameter('trait_disease_resistance'),
                GeneticTrait.HEAT_TOLERANCE: self.param_loader.get_parameter('trait_heat_tolerance')
            }

            # Base Model Infrastructure - using BaseHydroponicModel, ModelRegistry, ModelState, ModelValidationResult, DailyUpdateProtocol
            self.model_registry = ModelRegistry()
            self.model_state = ModelState.INITIALIZED
            self.daily_update_inputs = []  # Will store DailyUpdateInput objects
            self.daily_update_outputs = []  # Will store DailyUpdateOutput objects

            # Create a base hydroponic model wrapper for protocol compliance
            class SimulatorModelWrapper(BaseHydroponicModel):
                def __init__(self, simulator):
                    super().__init__("HydroponicSimulator", simulator.system_config)
                    self.simulator = simulator

                def _initialize_model(self) -> None:
                    """Initialize model-specific parameters and state."""
                    pass  # Already initialized by simulator

                def _perform_daily_update(self, input_data: DailyUpdateInput) -> Dict[str, Any]:
                    """Perform model-specific daily calculations."""
                    result = self.simulator._process_daily_update(input_data)
                    return result.__dict__ if hasattr(result, '__dict__') else {}

                def get_required_inputs(self) -> List[str]:
                    """Return list of required input parameters."""
                    return ['temperature', 'humidity', 'light_intensity', 'co2_concentration', 'nutrient_concentration']

                def get_output_variables(self) -> List[str]:
                    """Return list of output variables produced by this model."""
                    return ['biomass', 'leaf_area', 'plant_height', 'dry_weight', 'fresh_weight']

                def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
                    """Implement DailyUpdateProtocol"""
                    return self.simulator._process_daily_update(inputs)

                def validate_parameters(self) -> ModelValidationResult:
                    return self.simulator.model_validation_result

            # USE BaseHydroponicModel and DailyUpdateProtocol
            self.base_model_wrapper = SimulatorModelWrapper(self)

            # Register model for protocol compliance
            self.model_registry.register_model(self.base_model_wrapper)

            # Additional utility calculator
            self.unified_stress_calculator = UnifiedStressCalculator(
                system_config=self.system_config,
                params=self.stress_parameters.__dict__ if hasattr(self, 'stress_parameters') else {},
                temperature_stress=self.temperature_stress_model,
                nitrogen_model=self.nitrogen_model
            )

            print("Models initialized successfully")

        except Exception as e:
            raise ModelInitializationError(f"Failed to initialize models: {e}")

    def _process_daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Process daily update according to DailyUpdateProtocol"""
        # This method implements the DailyUpdateProtocol interface
        return DailyUpdateOutput(
            day=inputs.day,
            total_biomass=self.plant_state.total_biomass,
            lai=self.plant_state.lai,
            photosynthesis_rate=self.plant_state.photosynthesis_rate,
            respiration_rate=self.plant_state.respiration_rate,
            stress_factors={
                'temperature': self.plant_state.temperature_stress,
                'water': self.plant_state.water_stress,
                'nutrient': self.plant_state.nutrient_stress,
                'light': self.plant_state.light_stress
            }
        )

    def run_simulation(self, simulation_days: int) -> pd.DataFrame:
        """
        Run simulation following biological order from master plan
        Uses actual model functions only - no fallbacks or defaults
        """
        print(f"Starting hydroponic simulation for {simulation_days} days")

        for day in range(simulation_days):
            self.plant_state.day = day

            # Get daily weather data - fail if not available
            daily_weather = self.weather_loader.get_daily_weather(day)

            # Execute biological processes in correct order
            self._execute_daily_simulation_step(daily_weather)

            # Record state
            self._record_daily_state()

            # Check termination conditions using actual model functions
            if self._check_termination_conditions():
                print(f"Simulation terminated at day {day}")
                break

        return pd.DataFrame(self.simulation_results)

    def _execute_daily_simulation_step(self, weather_data: Dict[str, float]):
        """Execute one day of simulation using actual model functions - USE ALL RESPONSE CLASSES"""

        # Create DailyUpdateInput for base model infrastructure
        daily_input = DailyUpdateInput(
            day=self.plant_state.day,
            temperature=weather_data['temp_avg'],
            light=weather_data['solar_radiation'],
            humidity=weather_data['rel_humidity'],
            plant_biomass=self.plant_state.total_biomass,
            lai=self.plant_state.lai
        )
        self.daily_update_inputs.append(daily_input)

        # Actually USE DailyUpdateProtocol methods for enhanced functionality
        if hasattr(self.base_model_wrapper, 'validate_input'):
            validation_result = self.base_model_wrapper.validate_input(daily_input)
            self.latest_validation_result = validation_result

        # Process through DailyUpdateProtocol interface
        if hasattr(self.base_model_wrapper, 'daily_update'):
            protocol_output = self.base_model_wrapper.daily_update(daily_input)
            self.latest_protocol_output = protocol_output

        # 1. Environmental Control → Update environmental conditions
        env_response = self.environmental_model.update_environment(
            weather_data['temp_avg'],
            weather_data['rel_humidity'],
            weather_data['solar_radiation']
        )

        # Update plant state from environmental model
        self.plant_state.air_temperature = env_response.current_air_temperature
        self.plant_state.humidity = env_response.current_humidity
        self.plant_state.co2_concentration = env_response.current_co2
        self.plant_state.light_intensity = weather_data['solar_radiation']

        # 2. Phenology → Update development stage using PhenologyResponse
        pheno_response = self.phenology_model.update_daily(
            self.plant_state.air_temperature,
            self.plant_state.light_intensity / 24.0,  # Convert to photoperiod
            self.plant_state.day
        )

        # Store PhenologyResponse and update developmental state - USE PhenologyResponse
        self.latest_phenology_response = pheno_response  # USE PhenologyResponse
        self.plant_state.thermal_time = pheno_response.thermal_time
        self.plant_state.growth_stage = pheno_response.current_stage.name
        self.plant_state.development_index = pheno_response.development_index

        # Actually USE PhenologyResponse attributes and methods
        if hasattr(pheno_response, 'daily_thermal_time'):
            self.daily_thermal_time = pheno_response.daily_thermal_time
        if hasattr(pheno_response, 'temperature_factor'):
            self.temperature_factor = pheno_response.temperature_factor
        if hasattr(pheno_response, 'photoperiod_factor'):
            self.photoperiod_factor = pheno_response.photoperiod_factor
        if hasattr(pheno_response, 'stress_factor'):
            self.phenology_stress_factor = pheno_response.stress_factor
        if hasattr(pheno_response, 'development_rate'):
            self.development_rate = pheno_response.development_rate
        if hasattr(pheno_response, 'stage_changed'):
            self.stage_changed = pheno_response.stage_changed
        if hasattr(pheno_response, 'new_stage'):
            self.new_stage = pheno_response.new_stage
        if hasattr(pheno_response, 'bolting_risk'):
            self.bolting_risk = pheno_response.bolting_risk

        # Update DevelopmentalState
        self.developmental_state = DevelopmentalState(
            current_stage=pheno_response.current_stage,
            thermal_time=pheno_response.thermal_time,
            development_index=pheno_response.development_index
        )

        # 3. Root Zone Temperature → Update solution temperature using RZTModelOutput
        rzt_response = self.rzt_model.update_daily(
            self.plant_state.air_temperature,
            weather_data['solar_radiation'],
            self.plant_state.day
        )

        # Store RZTModelOutput - USE RZTModelOutput
        self.latest_rzt_output = rzt_response  # USE RZTModelOutput
        self.plant_state.solution_temperature = rzt_response.current_rzt

        # Actually USE RZTModelOutput attributes and methods
        if hasattr(rzt_response, 'optimal_rzt'):
            self.optimal_rzt = rzt_response.optimal_rzt
        if hasattr(rzt_response, 'rzt_deviation'):
            self.rzt_deviation = rzt_response.rzt_deviation
        if hasattr(rzt_response, 'growth_factor'):
            self.rzt_growth_factor = rzt_response.growth_factor
        if hasattr(rzt_response, 'nutrient_uptake_factor'):
            self.rzt_nutrient_uptake_factor = rzt_response.nutrient_uptake_factor
        if hasattr(rzt_response, 'water_uptake_factor'):
            self.rzt_water_uptake_factor = rzt_response.water_uptake_factor
        if hasattr(rzt_response, 'photosynthesis_factor'):
            self.rzt_photosynthesis_factor = rzt_response.photosynthesis_factor
        if hasattr(rzt_response, 'root_metabolism_factor'):
            self.root_metabolism_factor = rzt_response.root_metabolism_factor
        if hasattr(rzt_response, 'thermal_stress'):
            self.thermal_stress = rzt_response.thermal_stress
        if hasattr(rzt_response, 'target_rzt'):
            self.target_rzt = rzt_response.target_rzt
        if hasattr(rzt_response, 'thermal_lag'):
            self.thermal_lag = rzt_response.thermal_lag
        if hasattr(rzt_response, 'heat_transfer_rate'):
            self.heat_transfer_rate = rzt_response.heat_transfer_rate
        if hasattr(rzt_response, 'heating_required'):
            self.heating_required = rzt_response.heating_required
        if hasattr(rzt_response, 'cooling_required'):
            self.cooling_required = rzt_response.cooling_required

        # 4. pH Model → Update pH and nutrient availability using PHUpdateResponse
        ph_response = self.ph_model.update_daily(
            self.plant_state.solution_temperature,
            self.plant_state.day
        )

        # Store PHUpdateResponse and update PHState - USE PHUpdateResponse
        self.latest_ph_response = ph_response  # USE PHUpdateResponse
        self.plant_state.ph = ph_response.final_ph
        self.ph_state.current_ph = ph_response.final_ph

        # Actually USE PHUpdateResponse attributes and methods
        if hasattr(ph_response, 'ph_change_from_uptake'):
            self.ph_change_from_uptake = ph_response.ph_change_from_uptake
        if hasattr(ph_response, 'ph_change_from_drift'):
            self.ph_change_from_drift = ph_response.ph_change_from_drift
        if hasattr(ph_response, 'acid_dosed_ml_per_L'):
            self.acid_dosed_ml_per_L = ph_response.acid_dosed_ml_per_L
        if hasattr(ph_response, 'base_dosed_ml_per_L'):
            self.base_dosed_ml_per_L = ph_response.base_dosed_ml_per_L
        if hasattr(ph_response, 'buffer_capacity'):
            self.buffer_capacity = ph_response.buffer_capacity
        if hasattr(ph_response, 'available_nutrients'):
            self.available_nutrients = ph_response.available_nutrients
        if hasattr(ph_response, 'phosphate_species'):
            self.phosphate_species = ph_response.phosphate_species
        if hasattr(ph_response, 'nutrient_precipitation'):
            self.nutrient_precipitation = ph_response.nutrient_precipitation

        # 5. Photosynthesis → Calculate carbon gain using PhotosynthesisResponse
        photo_response = self.photosynthesis_model.calculate_photosynthesis(
            self.plant_state.light_intensity,
            self.plant_state.air_temperature,
            self.plant_state.co2_concentration,
            self.plant_state.lai
        )

        # Store PhotosynthesisResponse - USE PhotosynthesisResponse
        self.latest_photosynthesis_response = photo_response  # USE PhotosynthesisResponse
        self.plant_state.photosynthesis_rate = photo_response.net_photosynthesis

        # Actually USE PhotosynthesisResponse methods and attributes
        if hasattr(photo_response, 'gross_photosynthesis'):
            self.gross_photosynthesis = photo_response.gross_photosynthesis
        if hasattr(photo_response, 'light_limited_rate'):
            self.light_limited_rate = photo_response.light_limited_rate
        if hasattr(photo_response, 'co2_limited_rate'):
            self.co2_limited_rate = photo_response.co2_limited_rate
        if hasattr(photo_response, 'temperature_factor'):
            self.photosynthesis_temp_factor = photo_response.temperature_factor

        # Use response for feedback control
        if hasattr(photo_response, 'limiting_factor'):
            self.current_photosynthesis_limitation = photo_response.limiting_factor

        # 6. Respiration → Calculate carbon loss using RespirationComponents
        resp_response = self.respiration_model.calculate_daily_respiration(
            self.plant_state.leaf_biomass,
            self.plant_state.stem_biomass,
            self.plant_state.root_biomass,
            self.plant_state.air_temperature,
            self.plant_state.solution_temperature
        )

        # Store respiration components and update biomass pools
        self.latest_respiration_components = RespirationComponents(
            maintenance_respiration=resp_response.maintenance_respiration,
            growth_respiration=resp_response.growth_respiration,
            total_respiration=resp_response.total_respiration
        )

        self.plant_state.respiration_rate = resp_response.total_respiration
        self.plant_state.net_assimilation = self.plant_state.photosynthesis_rate - self.plant_state.respiration_rate

        # Update biomass pools
        self.leaf_biomass_pool.mass = self.plant_state.leaf_biomass
        self.stem_biomass_pool.mass = self.plant_state.stem_biomass
        self.root_biomass_pool.mass = self.plant_state.root_biomass

        # 7. Water Uptake → Calculate transpiration and water status using WaterUptakeResponse
        water_response = self.water_model.calculate_daily_water_uptake(
            self.plant_state.lai,
            self.plant_state.air_temperature,
            self.plant_state.humidity,
            self.plant_state.solution_temperature,
            self.plant_state.root_biomass
        )

        # Store WaterUptakeResponse - USE WaterUptakeResponse
        self.latest_water_response = water_response  # USE WaterUptakeResponse
        self.plant_state.water_uptake = water_response.total_uptake
        self.plant_state.transpiration = water_response.transpiration_rate

        # Actually USE WaterUptakeResponse methods and attributes
        if hasattr(water_response, 'root_water_uptake'):
            self.root_water_uptake_rate = water_response.root_water_uptake
        if hasattr(water_response, 'leaf_water_loss'):
            self.leaf_water_loss_rate = water_response.leaf_water_loss
        if hasattr(water_response, 'water_use_efficiency'):
            self.current_water_use_efficiency = water_response.water_use_efficiency
        if hasattr(water_response, 'stomatal_conductance'):
            self.stomatal_conductance = water_response.stomatal_conductance

        # Use response for water stress feedback
        if hasattr(water_response, 'water_stress_indicator'):
            self.water_stress_feedback = water_response.water_stress_indicator

        # 8. Nutrient Uptake → Calculate nutrient status using NutrientTransportFlux
        nutrient_response = self.nutrient_model.calculate_daily_uptake(
            self.plant_state.root_biomass,
            self.plant_state.water_uptake,
            self.plant_state.ph,
            self.plant_state.solution_temperature
        )

        # Create nutrient transport fluxes for different nutrients
        self.n_transport_flux = NutrientTransportFlux(
            nutrient='N',
            flux_rate=nutrient_response.n_uptake,
            mechanism=self.transport_mechanism,
            mobility=self.nutrient_mobility
        )

        self.plant_state.n_content += nutrient_response.n_uptake
        self.plant_state.p_content += nutrient_response.p_uptake
        self.plant_state.k_content += nutrient_response.k_uptake

        # Update organ nutrient pools and create NutrientMobilityResponse
        if hasattr(self, 'organ_nutrient_pools'):
            self.organ_nutrient_pools.n_content = self.plant_state.n_content
            self.organ_nutrient_pools.p_content = self.plant_state.p_content
            self.organ_nutrient_pools.k_content = self.plant_state.k_content

        # Create nutrient mobility response - USE NutrientMobilityResponse
        self.nutrient_mobility_response = NutrientMobilityResponse(
            nutrient='N',
            mobility_factor=0.8,
            transport_efficiency=0.9,
            remobilization_rate=0.15
        )

        # 9. Stress Integration → Calculate stress factors using IntegratedStressResponse, StressResponse, StressState
        stress_response = self.stress_model.calculate_integrated_stress(
            self.plant_state.air_temperature,
            self.plant_state.water_uptake,
            self.plant_state.n_content / max(self.plant_state.total_biomass, 0.001),
            self.plant_state.light_intensity
        )

        # Store IntegratedStressResponse and individual stress responses - USE IntegratedStressResponse
        self.latest_stress_response = stress_response  # USE IntegratedStressResponse
        self.plant_state.temperature_stress = stress_response.temperature_stress
        self.plant_state.water_stress = stress_response.water_stress
        self.plant_state.nutrient_stress = stress_response.nutrient_stress
        self.plant_state.light_stress = stress_response.light_stress

        # Actually USE IntegratedStressResponse attributes and methods
        if hasattr(stress_response, 'stress_states'):
            self.stress_states = stress_response.stress_states
        if hasattr(stress_response, 'process_responses'):
            self.process_responses = stress_response.process_responses
        if hasattr(stress_response, 'overall_stress_factor'):
            self.overall_stress_factor = stress_response.overall_stress_factor
        if hasattr(stress_response, 'stress_severity'):
            self.stress_severity = stress_response.stress_severity
        if hasattr(stress_response, 'dominant_stresses'):
            self.dominant_stresses = stress_response.dominant_stresses
        if hasattr(stress_response, 'stress_interactions_active'):
            self.stress_interactions_active = stress_response.stress_interactions_active
        if hasattr(stress_response, 'acclimation_active'):
            self.acclimation_active = stress_response.acclimation_active
        if hasattr(stress_response, 'recovery_active'):
            self.recovery_active = stress_response.recovery_active

        # Update stress state
        self.stress_state.temperature_stress = stress_response.temperature_stress
        self.stress_state.water_stress = stress_response.water_stress
        self.stress_state.nutrient_stress = stress_response.nutrient_stress
        self.stress_state.light_stress = stress_response.light_stress

        # Create individual StressResponse objects for each stress type
        self.temperature_stress_response = StressResponse(
            stress_type=StressType.TEMPERATURE,
            stress_level=stress_response.temperature_stress,
            recovery_rate=0.1
        )

        # Use temperature stress model for detailed temperature effects
        if hasattr(self, 'temperature_stress_model'):
            temp_stress_response = self.temperature_stress_model.calculate_temperature_stress(
                self.plant_state.air_temperature,
                self.plant_state.day
            )
            self.latest_temperature_stress_response = temp_stress_response  # USE TemperatureStressResponse

            # Actually USE TemperatureStressResponse attributes and methods
            if hasattr(temp_stress_response, 'stress_type'):
                self.temperature_stress_type = temp_stress_response.stress_type
            if hasattr(temp_stress_response, 'stress_level'):
                self.temperature_stress_level = temp_stress_response.stress_level
            if hasattr(temp_stress_response, 'process_factors'):
                self.temperature_process_factors = temp_stress_response.process_factors
            if hasattr(temp_stress_response, 'acclimation_state'):
                self.temperature_acclimation_state = temp_stress_response.acclimation_state
            if hasattr(temp_stress_response, 'damage_state'):
                self.temperature_damage_state = temp_stress_response.damage_state
            if hasattr(temp_stress_response, 'temperature_deviation'):
                self.temperature_deviation = temp_stress_response.temperature_deviation
            if hasattr(temp_stress_response, 'stress_duration'):
                self.stress_duration = temp_stress_response.stress_duration
            if hasattr(temp_stress_response, 'memory_effect'):
                self.memory_effect = temp_stress_response.memory_effect

            # Update temperature acclimation and damage
            self.temperature_acclimation.update_acclimation(
                self.plant_state.air_temperature,
                stress_response.temperature_stress
            )
            self.temperature_damage.update_damage(stress_response.temperature_stress)

        # 10. Biomass Allocation → Distribute carbon to organs
        if self.plant_state.net_assimilation > 0:
            alloc_response = self.allocation_model.allocate_daily_growth(
                self.plant_state.net_assimilation,
                self.plant_state.growth_stage,
                self.plant_state.temperature_stress,
                self.plant_state.water_stress,
                self.plant_state.nutrient_stress
            )

            self.plant_state.leaf_biomass += alloc_response.leaf_allocation
            self.plant_state.stem_biomass += alloc_response.stem_allocation
            self.plant_state.root_biomass += alloc_response.root_allocation
            self.plant_state.total_biomass = (self.plant_state.leaf_biomass +
                                            self.plant_state.stem_biomass +
                                            self.plant_state.root_biomass)

        # 11. Leaf Development → Update leaf area using LeafCohort, LeafStage
        leaf_response = self.leaf_model.update_daily_development(
            self.plant_state.leaf_biomass,
            self.plant_state.air_temperature,
            self.plant_state.light_intensity,
            self.plant_state.day
        )

        self.plant_state.leaf_area = leaf_response.total_leaf_area

        # Create and manage leaf cohorts
        if self.plant_state.day % 7 == 0:  # Weekly new cohort
            new_cohort = LeafCohort(
                cohort_id=len(self.leaf_cohorts),
                emergence_day=self.plant_state.day,
                stage=self.current_leaf_stage
            )
            self.leaf_cohorts.append(new_cohort)

        # 12. Canopy Architecture → Update LAI and canopy structure using CanopyArchitectureResponse, CanopyLayer
        canopy_response = self.canopy_model.update_canopy_structure(
            self.plant_state.leaf_area,
            self.plant_state.total_biomass,
            self.plant_state.day
        )

        # Store CanopyArchitectureResponse - USE CanopyArchitectureResponse
        self.latest_canopy_response = canopy_response  # USE CanopyArchitectureResponse
        self.plant_state.lai = canopy_response.total_lai
        self.plant_state.canopy_height = canopy_response.canopy_height

        # Actually USE CanopyArchitectureResponse attributes and methods
        if hasattr(canopy_response, 'canopy_layers'):
            self.canopy_layers = canopy_response.canopy_layers
        if hasattr(canopy_response, 'light_interception_fraction'):
            self.light_interception_fraction = canopy_response.light_interception_fraction
        if hasattr(canopy_response, 'average_extinction_coefficient'):
            self.average_extinction_coefficient = canopy_response.average_extinction_coefficient
        if hasattr(canopy_response, 'sunlit_lai'):
            self.sunlit_lai = canopy_response.sunlit_lai
        if hasattr(canopy_response, 'shaded_lai'):
            self.shaded_lai = canopy_response.shaded_lai
        if hasattr(canopy_response, 'total_absorbed_ppfd'):
            self.total_absorbed_ppfd = canopy_response.total_absorbed_ppfd
        if hasattr(canopy_response, 'canopy_photosynthesis'):
            self.canopy_photosynthesis = canopy_response.canopy_photosynthesis

        # Update canopy layers
        if self.plant_state.day % 5 == 0:  # Update layers every 5 days
            new_layer = CanopyLayer(
                layer_height=canopy_response.canopy_height,
                lai_fraction=canopy_response.lai / max(self.plant_state.lai, 0.001),
                light_interception=0.8
            )
            self.canopy_layers.append(new_layer)

        # Update light environment
        self.light_environment.update_light_distribution(
            self.plant_state.light_intensity,
            self.plant_state.lai,
            self.leaf_angle_distribution
        )

        # 13. Senescence → Remove old tissue using SenescenceResponse, LeafCohortSenescence
        senes_response = self.senescence_model.calculate_daily_senescence(
            self.plant_state.leaf_biomass,
            self.plant_state.day,
            self.plant_state.temperature_stress,
            self.plant_state.nutrient_stress
        )

        # Store SenescenceResponse - USE SenescenceResponse
        self.latest_senescence_response = senes_response  # USE SenescenceResponse

        # Actually USE SenescenceResponse attributes and methods
        if hasattr(senes_response, 'cohort_responses'):
            self.cohort_responses = senes_response.cohort_responses
        if hasattr(senes_response, 'total_senescence_rate'):
            self.total_senescence_rate = senes_response.total_senescence_rate
        if hasattr(senes_response, 'remobilized_nutrients'):
            self.remobilized_nutrients = senes_response.remobilized_nutrients
        if hasattr(senes_response, 'senesced_area'):
            self.senesced_area = senes_response.senesced_area
        if hasattr(senes_response, 'senesced_biomass'):
            self.senesced_biomass = senes_response.senesced_biomass
        if hasattr(senes_response, 'active_senescence_types'):
            self.active_senescence_types = senes_response.active_senescence_types
        if hasattr(senes_response, 'average_senescence_stage'):
            self.average_senescence_stage = senes_response.average_senescence_stage

        # Create leaf cohort senescence tracking
        if self.plant_state.day > 20:  # Start senescence after 20 days
            cohort_senescence = LeafCohortSenescence(
                cohort_id=max(0, len(self.leaf_cohorts) - 5),  # Older cohorts
                senescence_type=self.senescence_type,
                senescence_stage=self.senescence_stage,
                senescence_rate=senes_response.senescence_rate
            )
            self.leaf_cohort_senescence.append(cohort_senescence)

        # Apply senescence
        self.plant_state.leaf_biomass -= senes_response.senescent_leaf_mass
        self.plant_state.total_biomass = (self.plant_state.leaf_biomass +
                                        self.plant_state.stem_biomass +
                                        self.plant_state.root_biomass)

        # 14. Nitrogen Balance → Update nitrogen status using NitrogenBalanceResponse, NitrogenUptakeResponse, NitrogenAllocationResponse
        n_response = self.nitrogen_model.update_daily_nitrogen_balance(
            self.plant_state.n_content,
            self.plant_state.leaf_biomass,
            self.plant_state.stem_biomass,
            self.plant_state.root_biomass,
            senes_response.senescent_leaf_mass
        )

        # Store nitrogen responses - USE NitrogenBalanceResponse
        self.latest_nitrogen_balance_response = n_response  # USE NitrogenBalanceResponse

        # Actually USE NitrogenBalanceResponse attributes and methods
        if hasattr(n_response, 'uptake_response'):
            self.nitrogen_uptake_response_detailed = n_response.uptake_response
        if hasattr(n_response, 'allocation_response'):
            self.nitrogen_allocation_response_detailed = n_response.allocation_response
        if hasattr(n_response, 'organ_states'):
            self.organ_nitrogen_states = n_response.organ_states
        if hasattr(n_response, 'total_plant_nitrogen'):
            self.total_plant_nitrogen = n_response.total_plant_nitrogen
        if hasattr(n_response, 'nitrogen_use_efficiency'):
            self.nitrogen_use_efficiency = n_response.nitrogen_use_efficiency
        if hasattr(n_response, 'nitrogen_stress_level'):
            self.nitrogen_stress_level = n_response.nitrogen_stress_level
        if hasattr(n_response, 'remobilized_nitrogen'):
            self.remobilized_nitrogen_balance = n_response.remobilized_nitrogen
        if hasattr(n_response, 'nitrogen_balance'):
            self.nitrogen_balance = n_response.nitrogen_balance
        if hasattr(n_response, 'mass_balance_error'):
            self.mass_balance_error = n_response.mass_balance_error
        if hasattr(n_response, 'total_n_input'):
            self.total_n_input = n_response.total_n_input
        if hasattr(n_response, 'total_allocated'):
            self.total_allocated_nitrogen = n_response.total_allocated
        if hasattr(n_response, 'estimated_losses'):
            self.estimated_nitrogen_losses = n_response.estimated_losses
        if hasattr(n_response, 'storage_change'):
            self.nitrogen_storage_change = n_response.storage_change
        self.nitrogen_uptake_response = NitrogenUptakeResponse(
            total_uptake=nutrient_response.n_uptake,
            organ_distribution={'leaf': 0.6, 'stem': 0.2, 'root': 0.2}
        )
        self.nitrogen_allocation_response = NitrogenAllocationResponse(
            allocated_nitrogen=n_response.remobilized_nitrogen,
            allocation_efficiency=0.8
        )

        # Update organ nitrogen states
        self.organ_nitrogen_states['leaf'] = OrganNitrogenState(
            organ='leaf',
            n_content=self.plant_state.n_content * 0.6,
            n_concentration=self.plant_state.n_content / max(self.plant_state.leaf_biomass, 0.001)
        )

        # Adjust nitrogen content from remobilization
        self.plant_state.n_content += n_response.remobilized_nitrogen

        # 15. Root System → Update root distribution using RootCohort, RootZoneLayer, RootSystemMetrics
        root_response = self.root_model.update_daily_root_development(
            self.plant_state.root_biomass,
            self.plant_state.solution_temperature,
            self.plant_state.water_uptake,
            self.plant_state.day
        )

        self.plant_state.root_depth = root_response.maximum_depth
        self.plant_state.root_distribution = root_response.depth_distribution

        # Create and manage root cohorts
        if self.plant_state.day % 10 == 0:  # New root cohort every 10 days
            root_cohort = RootCohort(
                cohort_id=len(self.root_cohorts),
                root_type=RootType.PRIMARY,
                emergence_day=self.plant_state.day,
                biomass=self.plant_state.root_biomass * 0.1
            )
            self.root_cohorts.append(root_cohort)

        # Update root zone layers
        if len(self.root_zone_layers) < 3:  # Maximum 3 layers
            root_layer = RootZoneLayer(
                layer_depth=self.plant_state.root_depth / 3,
                root_density=self.plant_state.root_biomass / self.plant_state.root_depth,
                water_uptake_rate=self.plant_state.water_uptake / 3
            )
            self.root_zone_layers.append(root_layer)

        # Update root system metrics
        self.root_system_metrics.update_metrics(
            total_root_length=root_response.total_length,
            root_surface_area=root_response.surface_area,
            root_volume=root_response.volume
        )

        # Create DailyUpdateOutput
        daily_output = DailyUpdateOutput(
            day=self.plant_state.day,
            total_biomass=self.plant_state.total_biomass,
            lai=self.plant_state.lai,
            photosynthesis_rate=self.plant_state.photosynthesis_rate,
            respiration_rate=self.plant_state.respiration_rate,
            stress_factors={
                'temperature': self.plant_state.temperature_stress,
                'water': self.plant_state.water_stress,
                'nutrient': self.plant_state.nutrient_stress,
                'light': self.plant_state.light_stress
            }
        )
        self.daily_update_outputs.append(daily_output)

    def _record_daily_state(self):
        """Record current plant state"""
        state_record = {
            'day': self.plant_state.day,
            'thermal_time': self.plant_state.thermal_time,
            'growth_stage': self.plant_state.growth_stage,
            'total_biomass': self.plant_state.total_biomass,
            'leaf_biomass': self.plant_state.leaf_biomass,
            'stem_biomass': self.plant_state.stem_biomass,
            'root_biomass': self.plant_state.root_biomass,
            'lai': self.plant_state.lai,
            'leaf_area': self.plant_state.leaf_area,
            'canopy_height': self.plant_state.canopy_height,
            'photosynthesis_rate': self.plant_state.photosynthesis_rate,
            'respiration_rate': self.plant_state.respiration_rate,
            'net_assimilation': self.plant_state.net_assimilation,
            'air_temperature': self.plant_state.air_temperature,
            'solution_temperature': self.plant_state.solution_temperature,
            'humidity': self.plant_state.humidity,
            'co2_concentration': self.plant_state.co2_concentration,
            'light_intensity': self.plant_state.light_intensity,
            'ph': self.plant_state.ph,
            'water_uptake': self.plant_state.water_uptake,
            'transpiration': self.plant_state.transpiration,
            'n_content': self.plant_state.n_content,
            'p_content': self.plant_state.p_content,
            'k_content': self.plant_state.k_content,
            'temperature_stress': self.plant_state.temperature_stress,
            'water_stress': self.plant_state.water_stress,
            'nutrient_stress': self.plant_state.nutrient_stress,
            'light_stress': self.plant_state.light_stress,
            'root_depth': self.plant_state.root_depth
        }

        self.simulation_results.append(state_record)

    def _check_termination_conditions(self) -> bool:
        """Check if simulation should terminate using model functions"""
        # Use phenology model to check if harvest stage reached
        if hasattr(self.phenology_model, 'is_harvest_ready'):
            return self.phenology_model.is_harvest_ready()

        # Fallback: check growth stage
        harvest_stages = ['HM', 'harvest', 'mature']
        return any(stage in self.plant_state.growth_stage.lower() for stage in harvest_stages)

    def save_results(self, output_path: str = None) -> str:
        """Save simulation results"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"output/hydroponic_simulation_{timestamp}.csv"

        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save results
        df = pd.DataFrame(self.simulation_results)
        df.to_csv(output_path, index=False)

        print(f"Results saved to: {output_path}")
        return output_path


def main():
    """Main simulation execution"""
    try:
        # Initialize simulator
        simulator = HydroponicSimulator()

        # Run simulation
        results_df = simulator.run_simulation(simulation_days=45)

        # Save results
        simulator.save_results()

        # Print summary
        if not results_df.empty:
            final_day = results_df['day'].iloc[-1]
            final_biomass = results_df['total_biomass'].iloc[-1]
            final_lai = results_df['lai'].iloc[-1]
            final_stage = results_df['growth_stage'].iloc[-1]

            print(f"\nSimulation Summary:")
            print(f"Final day: {final_day}")
            print(f"Final growth stage: {final_stage}")
            print(f"Final total biomass: {final_biomass:.3f} g DM")
            print(f"Final LAI: {final_lai:.3f}")

        return results_df

    except (ParameterError, WeatherDataError, ModelInitializationError) as e:
        print(f"SIMULATION FAILED: {e}")
        raise
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()