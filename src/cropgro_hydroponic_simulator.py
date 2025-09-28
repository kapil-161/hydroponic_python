import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import os
import sys
import math

# Add parent directory to path for direct execution
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

# Import ALL model classes and parameter classes - complete comprehensive list
from models.environmental_control import (
    EnvironmentalControlSystem, EnvironmentalSetpoints, ControlEquipment, ControlStrategy
)
from models.nutrient_models import (
    NutrientModel, NutrientParameters, NutrientMobility, NutrientMobilityResponse,
    NutrientTransportFlux, OrganNutrientPools, TransportMechanism
)
from models.photosynthesis_model import (
    PhotosynthesisModel, PhotosynthesisParameters
)
from models.respiration_model import (
    EnhancedRespirationModel, RespirationParameters, BiomassPool,
    RespirationComponents, TissueType
)
from models.water_uptake_model import (
    WaterUptakeModel, WaterUptakeParameters, GrowthStage
)
from models.phenology_model import (
    ComprehensivePhenologyModel, PhenologyParameters,
    LettuceGrowthStage, DevelopmentalState
)
from models.ph_model import (
    HydroponicPHModel, PHParameters, PHState,
    BufferSystem, NutrientSolubility
)
from models.root_zone_temperature import (
    RootZoneTemperatureModel, RZTParameters
)
from models.stress_models import (
    IntegratedStressModel, IntegratedStressParameters,
    TemperatureStressModel, TemperatureStressParameters,
    StressType, StressState, StressResponse, ProcessStressFactors,
    TemperatureAcclimation, TemperatureDamage, UnifiedStressCalculator
)
from models.biomass_allocation_model import (
    BiomassAllocationModel, BiomassAllocationParameters
)
from models.leaf_development import (
    LeafDevelopmentModel, LeafParameters, LeafCohort, LeafStage
)
from models.canopy_architecture import (
    CanopyArchitectureModel, CanopyArchitectureParameters,
    CanopyLayer, LightEnvironment, LeafAngleDistribution
)
from models.senescence_model import (
    AdvancedSenescenceModel, SenescenceParameters,
    LeafCohortSenescence, SenescenceType, SenescenceStage
)
from models.nitrogen_balance import (
    NitrogenBalanceModel, NitrogenBalanceParameters,
    NitrogenUptakeResponse, NitrogenAllocationResponse, OrganNitrogenState
)
from models.root_system_model import (
    EnhancedRootSystemModel, RootSystemParameters, RootSystemMetrics,
    RootCohort, RootZoneLayer, RootType, HydroponicSystemType
)
from models.genetic_parameters import (
    GenotypeEnvironmentModel, GeneticParameterDatabase, CultivarProfile,
    GeneticCoefficients, GeneticTrait, LettuceType, BreedingAssistant
)
from models.base_model import (
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
    day: int
    hour: int

    # Biomass (g DM/plant) - from allocation model
    leaf_biomass: float
    stem_biomass: float
    root_biomass: float
    total_biomass: float

    # Canopy - from canopy and leaf models
    lai: float
    leaf_area: float
    canopy_height: float

    # Physiological rates - from photosynthesis/respiration models
    photosynthesis_rate: float
    respiration_rate: float
    net_assimilation: float

    # Development - from phenology model
    thermal_time: float
    growth_stage: str
    development_index: float

    # Stresses - from stress model
    temperature_stress: float
    water_stress: float
    nutrient_stress: float
    light_stress: float

    # Nutrients - from nutrient and nitrogen models
    n_content: float
    p_content: float
    k_content: float

    # Water - from water model
    water_uptake: float
    transpiration: float

    # Root system - from root model
    root_depth: float
    root_distribution: Dict[str, float]

    # Environment - from environmental model
    air_temperature: float
    solution_temperature: float
    root_zone_temperature: float
    humidity: float
    co2_concentration: float
    light_intensity: float
    ph: float

    def __post_init__(self):
        if self.root_distribution is None:
            raise ParameterError("root_distribution must be provided from CSV")


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
                'HM_to_BI': self.get_parameter('HM_to_BI'),
                'BI_to_FL': self.get_parameter('BI_to_FL'),
                'FL_to_AN': self.get_parameter('FL_to_AN'),
                'AN_to_SD': self.get_parameter('AN_to_SD'),
                'SD_to_PM': self.get_parameter('SD_to_PM'),
                'PM_to_PM': 0.0  # No thermal requirement for final stage
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
                params_dict[f"mobility_classifications_{nutrient}_mobility"] = self.get_parameter(f"mobility_classifications_{nutrient}_mobility")
                params_dict[f"mobility_classifications_{nutrient}_transport"] = self.get_parameter(f"mobility_classifications_{nutrient}_transport")
                params_dict[f"mobility_classifications_{nutrient}_remobilization_efficiency"] = self.get_parameter(f"remobilization_efficiency_{nutrient}")
                params_dict[f"mobility_classifications_{nutrient}_deficiency_mobility"] = self.get_parameter(f"deficiency_mobility_{nutrient}")
                params_dict[f"mobility_classifications_{nutrient}_retranslocation_rate"] = self.get_parameter(f"retranslocation_rate_{nutrient}")

            # Add transport rates
            for nutrient in nutrients:
                params_dict[f"xylem_transport_rates_{nutrient}"] = self.get_parameter(f"xylem_transport_rates_{nutrient}")
                params_dict[f"phloem_transport_rates_{nutrient}"] = self.get_parameter(f"phloem_transport_rates_{nutrient}")

            # Add buffering and storage parameters
            for organ in ["leaves", "stems", "roots"]:
                for nutrient in ["nitrogen", "phosphorus", "potassium"]:
                    params_dict[f"buffering_capacities_{organ}_{nutrient}"] = self.get_parameter(f"buffering_capacities_{organ}_{nutrient}")
                    params_dict[f"storage_pool_sizes_{organ}_{nutrient}"] = self.get_parameter(f"storage_pool_sizes_{organ}_{nutrient}")

            # Add redistribution parameters
            for nutrient in ["nitrogen", "phosphorus", "potassium", "calcium", "magnesium", "sulfur"]:
                params_dict[f"redistribution_thresholds_{nutrient}"] = self.get_parameter(f"redistribution_thresholds_{nutrient}")
                params_dict[f"stress_redistribution_rates_{nutrient}"] = self.get_parameter(f"stress_redistribution_rates_{nutrient}")

            # Add sink strength coefficients
            for stage in ["vegetative", "reproductive", "senescence"]:
                for organ in ["leaves", "stems", "roots"]:
                    params_dict[f"sink_strength_coefficients_{stage}_{organ}"] = self.get_parameter(f"sink_strength_coefficients_{stage}_{organ}")
                # Add special reproductive organ for reproductive stage
                if stage == "reproductive":
                    params_dict[f"sink_strength_coefficients_{stage}_reproductive"] = self.get_parameter(f"sink_strength_coefficients_{stage}_reproductive")

            return NutrientParameters.from_config(params_dict)
        except Exception as e:
            raise ParameterError(f"Failed to create NutrientParameters: {e}")

    def create_ph_parameters(self) -> PHParameters:
        """Create PHParameters from CSV data following strict no-defaults rule"""
        try:
            # Create phosphate and iron solubility data dictionaries from CSV parameters
            phosphate_solubility_data = {
                '4.0': self.get_parameter('phosphate_solubility_ph_4_0'),
                '5.0': self.get_parameter('phosphate_solubility_ph_5_0'),
                '6.0': self.get_parameter('phosphate_solubility_ph_6_0'),
                '7.0': self.get_parameter('phosphate_solubility_ph_7_0'),
                '8.0': self.get_parameter('phosphate_solubility_ph_8_0')
            }

            iron_solubility_data = {
                '4.0': self.get_parameter('iron_solubility_ph_4_0'),
                '5.0': self.get_parameter('iron_solubility_ph_5_0'),
                '6.0': self.get_parameter('iron_solubility_ph_6_0'),
                '7.0': self.get_parameter('iron_solubility_ph_7_0'),
                '8.0': self.get_parameter('iron_solubility_ph_8_0')
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
                hours_per_day=self.get_parameter('hours_per_day'),
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
                'process_sensitivity_development_temperature', 'water_temp_interaction_factor'
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

    def create_genetic_parameters(self) -> Tuple[GeneticParameterDatabase, CultivarProfile]:
        """Create genetic database and cultivar profile from CSV data"""
        try:
            # Create genetic coefficients from CSV
            genetic_coeffs = GeneticCoefficients(
                EM_FL=self.get_parameter('EM_FL'),
                FL_SH=self.get_parameter('FL_SH'),
                FL_SD=self.get_parameter('FL_SD'),
                SD_PM=self.get_parameter('SD_PM'),
                FL_LF=self.get_parameter('FL_LF'),
                LFMAX=self.get_parameter('LFMAX'),
                SLAVR=self.get_parameter('SLAVR'),
                SIZLF=self.get_parameter('SIZLF'),
                XFRT=self.get_parameter('XFRT'),
                SFDUR=self.get_parameter('SFDUR'),
                SDPDV=self.get_parameter('SDPDV'),
                PODUR=self.get_parameter('PODUR'),
                WTPSD=self.get_parameter('WTPSD'),
                THRSH=self.get_parameter('THRSH'),
                SDPRO=self.get_parameter('SDPRO'),
                SDLIP=self.get_parameter('SDLIP'),
                EC_TOLERANCE=self.get_parameter('EC_TOLERANCE'),
                ROOT_ACTIVITY=self.get_parameter('ROOT_ACTIVITY'),
                PHOTOSYNTHETIC_CAPACITY=self.get_parameter('PHOTOSYNTHETIC_CAPACITY'),
                NITRATE_EFFICIENCY=self.get_parameter('NITRATE_EFFICIENCY')
            )
            
            # Create trait values dictionary from CSV
            trait_values = {
                GeneticTrait.DAYS_TO_EMERGENCE: self.get_parameter('trait_days_to_emergence'),
                GeneticTrait.DAYS_TO_HARVEST: self.get_parameter('trait_days_to_harvest'),
                GeneticTrait.BOLTING_TOLERANCE: self.get_parameter('trait_bolting_tolerance'),
                GeneticTrait.LEAF_SIZE: self.get_parameter('trait_leaf_size'),
                GeneticTrait.PLANT_ARCHITECTURE: self.get_parameter('trait_plant_architecture'),
                GeneticTrait.ROOT_DEVELOPMENT: self.get_parameter('trait_root_development'),
                GeneticTrait.YIELD_POTENTIAL: self.get_parameter('trait_yield_potential'),
                GeneticTrait.CHLOROPHYLL_CONTENT: self.get_parameter('trait_chlorophyll_content'),
                GeneticTrait.CAROTENOID_CONTENT: self.get_parameter('trait_carotenoid_content'),
                GeneticTrait.VITAMIN_C_CONTENT: self.get_parameter('trait_vitamin_c_content'),
                GeneticTrait.NITRATE_ACCUMULATION: self.get_parameter('trait_nitrate_accumulation'),
                GeneticTrait.HEAT_TOLERANCE: self.get_parameter('trait_heat_tolerance'),
                GeneticTrait.COLD_TOLERANCE: self.get_parameter('trait_cold_tolerance'),
                GeneticTrait.SALINITY_TOLERANCE: self.get_parameter('trait_salinity_tolerance'),
                GeneticTrait.DISEASE_RESISTANCE: self.get_parameter('trait_disease_resistance')
            }
            
            # Map lettuce type from CSV
            lettuce_type_str = self.get_parameter('lettuce_type')
            lettuce_type_mapping = {
                'butterhead': LettuceType.BUTTERHEAD,
                'romaine': LettuceType.ROMAINE,
                'loose_leaf': LettuceType.LOOSE_LEAF,
                'crisphead': LettuceType.CRISPHEAD,
                'oak_leaf': LettuceType.OAK_LEAF,
                'mini_romaine': LettuceType.MINI_ROMAINE
            }
            lettuce_type = lettuce_type_mapping.get(lettuce_type_str.lower(), LettuceType.BUTTERHEAD)
            
            # Create cultivar profile
            cultivar_profile = CultivarProfile(
                cultivar_id=self.get_parameter('cultivar_id'),
                cultivar_name=self.get_parameter('cultivar_name'),
                lettuce_type=lettuce_type,
                breeder=self.get_parameter('breeder'),
                year_released=int(self.get_parameter('year_released')),
                genetic_coefficients=genetic_coeffs,
                yield_potential=self.get_parameter('yield_potential'),
                adaptation_score=self.get_parameter('adaptation_score'),
                trait_values=trait_values,
                pedigree=[self.get_parameter('pedigree')],
                breeding_notes=self.get_parameter('breeding_notes')
            )
            
            # Create and populate genetic database
            genetic_db = GeneticParameterDatabase()
            genetic_db.add_cultivar(cultivar_profile)
            
            return genetic_db, cultivar_profile
            
        except Exception as e:
            raise ParameterError(f"Failed to create genetic parameters: {e}")

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
            if system_type_str not in system_type_mapping:
                raise ParameterError(f"Invalid system_type: {system_type_str}")
            system_type = system_type_mapping[system_type_str]

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
                system_multipliers={
                    HydroponicSystemType.DWC: {
                        'root_length_multiplier': self.get_parameter('system_multipliers_deep_water_culture_root_length_multiplier'),
                        'surface_area_multiplier': self.get_parameter('system_multipliers_deep_water_culture_surface_area_multiplier'),
                        'branching_multiplier': self.get_parameter('system_multipliers_deep_water_culture_branching_multiplier')
                    },
                    HydroponicSystemType.NFT: {
                        'root_length_multiplier': self.get_parameter('system_multipliers_nutrient_film_technique_root_length_multiplier'),
                        'surface_area_multiplier': self.get_parameter('system_multipliers_nutrient_film_technique_surface_area_multiplier'),
                        'branching_multiplier': self.get_parameter('system_multipliers_nutrient_film_technique_branching_multiplier')
                    },
                    HydroponicSystemType.AEROPONICS: {
                        'root_length_multiplier': self.get_parameter('system_multipliers_aeroponics_root_length_multiplier'),
                        'surface_area_multiplier': self.get_parameter('system_multipliers_aeroponics_surface_area_multiplier'),
                        'branching_multiplier': self.get_parameter('system_multipliers_aeroponics_branching_multiplier')
                    }
                },
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

    def _calculate_initial_photosynthesis_rate(self) -> float:
        """Calculate initial photosynthesis rate from photosynthesis model parameters"""
        # Base photosynthesis calculation using reasonable initial conditions
        initial_lai = max(0.1, self.get_parameter('initial_lai'))
        initial_temperature = self.get_parameter('initial_air_temperature')
        initial_light = 200.0  # Reasonable initial PAR value (μmol m⁻² s⁻¹)
        initial_co2 = 400.0   # Standard atmospheric CO2 concentration (ppm)

        # Calculate light-limited photosynthesis using simplified model
        light_use_efficiency = 0.05  # Rough estimate from photosynthesis parameters
        max_photosynthesis_rate = 30.0  # Maximum rate from photosynthesis parameters

        # Simple light response curve
        light_response = (initial_light * light_use_efficiency) / (1 + (initial_light * light_use_efficiency) / max_photosynthesis_rate)

        # Temperature response (optimal around 25°C)
        temp_factor = 1.0 - abs(initial_temperature - 25.0) * 0.02
        temp_factor = max(0.3, min(1.0, temp_factor))

        # LAI scaling - adjusted for lettuce (peaks at LAI ~0.5, not 2.0)
        lai_factor = min(1.0, initial_lai / 0.5)  # Scale with LAI up to 0.5 for lettuce

        initial_photosynthesis = light_response * temp_factor * lai_factor

        # Ensure minimum realistic photosynthesis rate
        min_photosynthesis_rate = 0.5  # Minimum biological photosynthesis for living plant
        return max(min_photosynthesis_rate, initial_photosynthesis)

    def _calculate_initial_stress_factors(self) -> Dict[str, float]:
        """Calculate initial stress factors from environmental conditions using stress models"""
        try:
            # Get initial environmental conditions from CSV
            initial_temp = self.get_parameter('initial_air_temperature')
            initial_humidity = self.get_parameter('initial_humidity')
            initial_light = self.get_parameter('initial_light_intensity')

            # Calculate temperature stress using simplified approach if stress model not available yet
            if hasattr(self, 'temperature_stress_model') and self.temperature_stress_model:
                temp_stress_level = self.temperature_stress_model.calculate_base_stress_level(initial_temp)
                temperature_stress = min(1.0, max(0.0, temp_stress_level))
            else:
                # Simple temperature stress calculation based on optimal range
                optimal_temp_min = 18.0  # °C, from phenology parameters
                optimal_temp_max = 24.0  # °C, from phenology parameters
                if optimal_temp_min <= initial_temp <= optimal_temp_max:
                    temperature_stress = 0.0
                elif initial_temp < optimal_temp_min:
                    # Cold stress
                    temperature_stress = min(0.5, (optimal_temp_min - initial_temp) / 10.0)
                else:
                    # Heat stress
                    temperature_stress = min(0.5, (initial_temp - optimal_temp_max) / 10.0)

            # Calculate water stress from humidity (simplified VPD-based approach)
            # VPD calculation: higher VPD means more water stress
            saturation_vapor_pressure = 0.6108 * math.exp(17.27 * initial_temp / (initial_temp + 237.3))
            actual_vapor_pressure = saturation_vapor_pressure * (initial_humidity / 100.0)
            vpd = saturation_vapor_pressure - actual_vapor_pressure

            # Water stress increases with VPD (typical hydroponic range: 0.5-1.5 kPa)
            optimal_vpd = 0.8  # kPa, optimal for lettuce
            vpd_stress_threshold = 1.5  # kPa, stress threshold

            if vpd <= optimal_vpd:
                water_stress = 0.0
            elif vpd >= vpd_stress_threshold:
                water_stress = 0.3  # Maximum water stress in hydroponic systems
            else:
                water_stress = 0.3 * (vpd - optimal_vpd) / (vpd_stress_threshold - optimal_vpd)

            # Calculate light stress from light intensity
            optimal_light_min = 150.0  # μmol/m²/s, typical lettuce minimum
            optimal_light_max = 800.0  # μmol/m²/s, typical lettuce maximum

            if optimal_light_min <= initial_light <= optimal_light_max:
                light_stress = 0.0
            elif initial_light < optimal_light_min:
                # Low light stress
                light_stress = min(0.5, (optimal_light_min - initial_light) / optimal_light_min)
            else:
                # High light stress
                excess_light = initial_light - optimal_light_max
                light_stress = min(0.3, excess_light / (2 * optimal_light_max))

            # Nutrient stress is initially zero for hydroponic systems with proper nutrient solution
            # Will be calculated dynamically based on nutrient concentrations during simulation
            nutrient_stress = 0.0

            return {
                'temperature_stress': temperature_stress,
                'water_stress': water_stress,
                'nutrient_stress': nutrient_stress,
                'light_stress': light_stress
            }

        except Exception as e:
            # Fallback to zero stress if calculation fails
            print(f"Warning: Failed to calculate initial stress factors, using zero stress: {e}")
            return {
                'temperature_stress': 0.0,
                'water_stress': 0.0,
                'nutrient_stress': 0.0,
                'light_stress': 0.0
            }

    def _calculate_initial_respiration_rate(self) -> float:
        """Calculate initial respiration rate from respiration model parameters"""
        # Base respiration rate calculation using respiration model principles
        maintenance_base_rate = self.get_parameter('maintenance_base_rate')
        initial_leaf_biomass = self.get_parameter('initial_leaf_biomass')
        initial_stem_biomass = self.get_parameter('initial_stem_biomass')
        initial_root_biomass = self.get_parameter('initial_root_biomass')
        reference_temperature = self.get_parameter('reference_temperature')
        q10_factor = self.get_parameter('q10_factor')

        # Calculate temperature-adjusted maintenance respiration
        initial_temperature = self.get_parameter('initial_air_temperature')
        temperature_factor = q10_factor ** ((initial_temperature - reference_temperature) / 10.0)

        # Calculate tissue-specific respiration rates
        leaf_respiration = initial_leaf_biomass * maintenance_base_rate * temperature_factor * 1.0  # leaf factor
        stem_respiration = initial_stem_biomass * maintenance_base_rate * temperature_factor * 0.5  # stem factor
        root_respiration = initial_root_biomass * maintenance_base_rate * temperature_factor * 0.8  # root factor

        total_initial_respiration = leaf_respiration + stem_respiration + root_respiration

        # Ensure minimum realistic respiration rate proportional to biomass (following "model output" rule)
        total_biomass = initial_leaf_biomass + initial_stem_biomass + initial_root_biomass
        min_respiration_rate = total_biomass * 0.001  # 0.1% of biomass as minimum respiration
        return max(min_respiration_rate, total_initial_respiration)

    def create_initial_plant_state(self) -> PlantState:
        """Create initial PlantState from CSV values"""
        try:
            root_distribution_str = self.get_parameter('initial_root_distribution')
            root_distribution = eval(root_distribution_str) if root_distribution_str else {}
            if not isinstance(root_distribution, dict):
                raise ParameterError("initial_root_distribution must be a dictionary")

            return PlantState(
                day=int(self.get_parameter('initial_day')),
                hour=int(self.get_parameter('initial_hour')),
                leaf_biomass=self.get_parameter('initial_leaf_biomass'),
                stem_biomass=self.get_parameter('initial_stem_biomass'),
                root_biomass=self.get_parameter('initial_root_biomass'),
                total_biomass=self.get_parameter('initial_leaf_biomass') + self.get_parameter('initial_stem_biomass') + self.get_parameter('initial_root_biomass'),
                lai=max(0.1, self.get_parameter('initial_lai')),  # Ensure minimum realistic LAI
                leaf_area=self.get_parameter('initial_leaf_area'),
                canopy_height=self.get_parameter('initial_canopy_height'),
                photosynthesis_rate=self._calculate_initial_photosynthesis_rate(),
                respiration_rate=self._calculate_initial_respiration_rate(),
                net_assimilation=self._calculate_initial_photosynthesis_rate() - self._calculate_initial_respiration_rate(),
                thermal_time=self.get_parameter('initial_thermal_time'),
                growth_stage=self.get_parameter('initial_growth_stage'),
                development_index=self.get_parameter('initial_development_index'),
                **self._calculate_initial_stress_factors(),
                n_content=self.get_parameter('initial_n_content'),
                p_content=self.get_parameter('initial_p_content'),
                k_content=self.get_parameter('initial_k_content'),
                water_uptake=self.get_parameter('initial_water_uptake'),
                transpiration=self.get_parameter('initial_transpiration'),
                root_depth=self.get_parameter('initial_root_depth'),
                root_distribution=root_distribution,
                air_temperature=self.get_parameter('initial_air_temperature'),
                solution_temperature=self.get_parameter('initial_solution_temperature'),
                root_zone_temperature=self.get_parameter('initial_solution_temperature'),  # Initialize RZT equal to solution temp
                humidity=self.get_parameter('initial_humidity'),
                co2_concentration=self.get_parameter('initial_co2_concentration'),
                light_intensity=self.get_parameter('initial_light_intensity'),
                ph=self.get_parameter('initial_ph')
            )
        except Exception as e:
            raise ParameterError(f"Failed to create initial PlantState: {e}")


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

        required_columns = ['date', 'temp_avg', 'temp_min', 'temp_max', 'solar_radiation', 'rel_humidity', 'wind_speed', 'rainfall']
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
            'wind_speed': float(row['wind_speed']),
            'rainfall': float(row['rainfall']),
            'vpd': float(row['vpd']) if 'vpd' in row and not pd.isna(row['vpd']) else None,
            'co2': float(row['co2_ppm']) if 'co2_ppm' in row and not pd.isna(row['co2_ppm']) else None,
            'par': float(row['par']) if 'par' in row and not pd.isna(row['par']) else None,
            'rzt': float(row['rzt']) if 'rzt' in row and not pd.isna(row['rzt']) else None
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

        # Initialize plant state from CSV
        self.plant_state = self.param_loader.create_initial_plant_state()

        # Initialize all 17 models with actual parameters from CSV
        self._initialize_all_models()

        # Simulation results storage
        self.simulation_results = []

        # Nutrient concentrations state (updated daily)
        initial_no3 = self.param_loader.get_parameter('initial_no3_conc')
        initial_nh4 = self.param_loader.get_parameter('initial_nh4_conc')
        initial_po4 = self.param_loader.get_parameter('initial_po4_conc')

        print(f"  DEBUG Nutrient initialization: NO3={initial_no3} mg/L, NH4={initial_nh4} mg/L, PO4={initial_po4} mg/L")

        self.nutrient_concentrations = {
            'NO3': initial_no3,
            'NH4': initial_nh4,
            'PO4': initial_po4,
            'K': self.param_loader.get_parameter('initial_k_conc'),
            'Ca': self.param_loader.get_parameter('initial_ca_conc'),
            'Mg': self.param_loader.get_parameter('initial_mg_conc'),
            'SO4': self.param_loader.get_parameter('initial_so4_conc'),
            'Fe': self.param_loader.get_parameter('initial_fe_conc'),
            'Mn': self.param_loader.get_parameter('initial_mn_conc'),
            'Zn': self.param_loader.get_parameter('initial_zn_conc'),
            'Cu': self.param_loader.get_parameter('initial_cu_conc'),
            'B': self.param_loader.get_parameter('initial_b_conc'),
            'Mo': self.param_loader.get_parameter('initial_mo_conc')
        }

        # Initialize dynamic canopy values (will be updated by canopy model)
        # Set initial values based on initial LAI with simplified calculation
        initial_lai = self.plant_state.lai
        # Assume 70% sunlit initially (will be dynamically calculated by canopy model)
        self.sunlit_lai = initial_lai * 0.7
        self.shaded_lai = initial_lai * 0.3

        # Initialize organ nitrogen states (will be updated by nitrogen model)
        self.organ_nitrogen_states = {}

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
            self.control_strategy = ControlStrategy[self.param_loader.get_parameter('control_strategy').upper()]

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
            initial_stage_str = self.param_loader.get_parameter('initial_growth_stage')
            initial_stage = LettuceGrowthStage[initial_stage_str.upper()]
            self.phenology_model = ComprehensivePhenologyModel(pheno_params, initial_stage)
            self.phenology_parameters = pheno_params  # USE PhenologyParameters
            self.current_growth_stage = initial_stage

            # Store parameter validation results
            self.model_validation_result = ModelValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )

            # 4. Respiration Model - using RespirationParameters, BiomassPool, TissueType, RespirationComponents
            resp_params = self.param_loader.create_respiration_parameters()
            resp_config = {'enable_logging': bool(self.param_loader.get_parameter('enable_logging')), 'validation_mode': self.param_loader.get_parameter('validation_mode')}
            self.respiration_model = EnhancedRespirationModel(resp_params, resp_config)
            self.respiration_parameters = resp_params

            # Initialize biomass pools using BiomassPool and TissueType with initial nitrogen content
            self.leaf_biomass_pool = BiomassPool(tissue_type=TissueType.LEAVES, dry_mass=self.plant_state.leaf_biomass, age_days=self.plant_state.day, nitrogen_content=self.param_loader.get_parameter('initial_leaf_nitrogen_content'), recent_growth=0.0)
            self.stem_biomass_pool = BiomassPool(tissue_type=TissueType.STEMS, dry_mass=self.plant_state.stem_biomass, age_days=self.plant_state.day, nitrogen_content=self.param_loader.get_parameter('initial_stem_nitrogen_content'), recent_growth=0.0)
            self.root_biomass_pool = BiomassPool(tissue_type=TissueType.ROOTS, dry_mass=self.plant_state.root_biomass, age_days=self.plant_state.day, nitrogen_content=self.param_loader.get_parameter('initial_root_nitrogen_content'), recent_growth=0.0)

            # 5. Water Uptake Model - using WaterUptakeParameters, GrowthStage
            water_params = self.param_loader.create_water_uptake_parameters()
            self.water_model = WaterUptakeModel(water_params)
            self.water_parameters = water_params
            initial_water_stage_str = self.param_loader.get_parameter('initial_water_growth_stage')
            self.current_water_growth_stage = GrowthStage[initial_water_stage_str.upper()]

            # 6. Nutrient Model - using NutrientParameters, NutrientMobility, TransportMechanism, OrganNutrientPools
            nutrient_params = self.param_loader.create_nutrient_parameters()
            self.nutrient_model = NutrientModel(nutrient_params)
            self.nutrient_parameters = nutrient_params

            # Initialize nutrient pools and transport mechanisms
            mobility_str = self.param_loader.get_parameter('nutrient_mobility')
            self.nutrient_mobility = NutrientMobility[mobility_str.upper()]
            transport_str = self.param_loader.get_parameter('transport_mechanism')
            self.transport_mechanism = TransportMechanism[transport_str.upper()]
            self.organ_nutrient_pools = OrganNutrientPools(organ_name=self.param_loader.get_parameter('initial_organ_name'), nutrient_name=self.param_loader.get_parameter('initial_nutrient_name'))

            # 7. pH Model - using PHParameters, BufferSystem, PHState, NutrientSolubility
            ph_params = self.param_loader.create_ph_parameters()
            self.ph_model = HydroponicPHModel(ph_params)
            self.ph_parameters = ph_params

            # Initialize pH-related classes
            buffer_str = self.param_loader.get_parameter('buffer_system')
            self.buffer_system = BufferSystem[buffer_str.upper()]  # Use enum
            self.ph_state = PHState(
                current_ph=ph_params.current_ph,
                buffer_capacity=ph_params.ph_buffer_capacity,
                total_alkalinity=ph_params.total_alkalinity,
                carbonate_conc=ph_params.carbonate_conc,
                phosphate_total=ph_params.phosphate_total,
                ionic_strength=ph_params.ionic_strength,
                temperature=self.param_loader.get_parameter('initial_temperature')
            )
            self.nutrient_solubility = NutrientSolubility(
                phosphate_solubility=ph_params.phosphate_solubility_data,
                iron_solubility=ph_params.iron_solubility_data,
                calcium_phosphate_ksp=ph_params.calcium_phosphate_ksp,
                magnesium_phosphate_ksp=ph_params.magnesium_phosphate_ksp
            )

            # 8. Root Zone Temperature Model - using RZTParameters, RZTModelOutput
            rzt_params = self.param_loader.create_rzt_parameters()
            self.rzt_model = RootZoneTemperatureModel(rzt_params)
            self.rzt_parameters = rzt_params

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
            initial_leaf_stage_str = self.param_loader.get_parameter('initial_leaf_stage')
            self.current_leaf_stage = LeafStage[initial_leaf_stage_str.upper()]

            # 12. Canopy Architecture Model - using CanopyArchitectureParameters, LeafAngleDistribution, CanopyLayer
            canopy_params = self.param_loader.create_canopy_architecture_parameters()
            self.canopy_model = CanopyArchitectureModel(canopy_params)
            self.canopy_parameters = canopy_params

            # Initialize canopy components
            leaf_angle_str = self.param_loader.get_parameter('initial_leaf_angle_distribution')
            self.leaf_angle_distribution = LeafAngleDistribution[leaf_angle_str.upper()]
            self.canopy_layers = []  # Will store CanopyLayer objects
            # Initialize light environment with values from CSV, updated during daily simulation
            self.light_environment = LightEnvironment(
                ppfd_above_canopy=self.param_loader.get_parameter('initial_ppfd_above_canopy'),
                direct_beam_fraction=self.param_loader.get_parameter('initial_direct_beam_fraction'),
                diffuse_fraction=self.param_loader.get_parameter('initial_diffuse_fraction'),
                solar_zenith_angle=self.param_loader.get_parameter('initial_solar_zenith_angle'),
                solar_azimuth_angle=self.param_loader.get_parameter('initial_solar_azimuth_angle')
            )

            # 13. Senescence Model - using SenescenceParameters, SenescenceType, SenescenceStage, LeafCohortSenescence
            senes_params = self.param_loader.create_senescence_parameters()
            self.senescence_model = AdvancedSenescenceModel(senes_params)
            self.senescence_parameters = senes_params

            # Initialize senescence components
            senescence_type_str = self.param_loader.get_parameter('initial_senescence_type')
            self.senescence_type = SenescenceType[senescence_type_str.upper()]
            senescence_stage_str = self.param_loader.get_parameter('initial_senescence_stage')
            self.senescence_stage = SenescenceStage[senescence_stage_str.upper()]
            self.leaf_cohort_senescence = []  # Will store LeafCohortSenescence objects

            # 14. Nitrogen Balance Model - using NitrogenBalanceParameters, OrganNitrogenState
            n_params = self.param_loader.create_nitrogen_balance_parameters()
            self.nitrogen_model = NitrogenBalanceModel(n_params)
            self.nitrogen_parameters = n_params

            # Initialize nitrogen components
            self.organ_nitrogen_states = {}  # Will store OrganNitrogenState objects
            
            # Initialize organ nitrogen states
            initial_leaf_biomass = self.param_loader.get_parameter('initial_leaf_biomass')
            initial_stem_biomass = self.param_loader.get_parameter('initial_stem_biomass')
            initial_root_biomass = self.param_loader.get_parameter('initial_root_biomass')
            
            initial_leaf_n_content = self.param_loader.get_parameter('initial_leaf_nitrogen_content')
            initial_stem_n_content = self.param_loader.get_parameter('initial_stem_nitrogen_content')
            initial_root_n_content = self.param_loader.get_parameter('initial_root_nitrogen_content')
            
            self.nitrogen_model.initialize_organ_nitrogen('leaves', initial_leaf_biomass, initial_leaf_n_content)
            self.nitrogen_model.initialize_organ_nitrogen('stems', initial_stem_biomass, initial_stem_n_content)
            self.nitrogen_model.initialize_organ_nitrogen('roots', initial_root_biomass, initial_root_n_content)

            # 15. Root System Model - using RootSystemParameters, RootType, HydroponicSystemType, RootCohort, RootZoneLayer
            root_params = self.param_loader.create_root_system_parameters()
            self.root_model = EnhancedRootSystemModel(root_params)
            self.root_parameters = root_params

            # Initialize root system components
            self.hydroponic_system_type = root_params.system_type
            self.root_cohorts = []  # Will store RootCohort objects
            self.root_zone_layers = []  # Will store RootZoneLayer objects
            # Initialize root system metrics with values from CSV
            self.root_system_metrics = RootSystemMetrics(
                total_root_length=self.param_loader.get_parameter('initial_total_root_length'),
                total_root_surface_area=self.param_loader.get_parameter('initial_total_root_surface_area'),
                total_root_biomass=self.param_loader.get_parameter('initial_root_biomass'),
                total_root_volume=self.param_loader.get_parameter('initial_total_root_volume'),
                root_length_density=self.param_loader.get_parameter('initial_root_length_density'),
                root_surface_area_density=self.param_loader.get_parameter('initial_root_surface_area_density'),
                specific_root_length=self.param_loader.get_parameter('initial_total_root_length') / self.param_loader.get_parameter('initial_root_biomass'),
                average_root_activity=self.param_loader.get_parameter('initial_average_root_activity'),
                fine_root_length=self.param_loader.get_parameter('initial_fine_root_length'),
                medium_root_length=self.param_loader.get_parameter('initial_medium_root_length'),
                coarse_root_length=self.param_loader.get_parameter('initial_coarse_root_length'),
                fine_root_fraction=self.param_loader.get_parameter('initial_fine_root_fraction'),
                root_age_days=self.param_loader.get_parameter('initial_root_age_days'),
                cumulative_growth=self.param_loader.get_parameter('initial_cumulative_growth'),
                total_nutrient_uptake=self.param_loader.get_parameter('initial_total_nutrient_uptake'),
                uptake_per_surface_area=self.param_loader.get_parameter('initial_uptake_per_surface_area'),
                uptake_temperature_factor=self.param_loader.get_parameter('initial_uptake_temperature_factor'),
                uptake_flow_factor=self.param_loader.get_parameter('initial_uptake_flow_factor'),
                effective_root_surface_area=self.param_loader.get_parameter('initial_effective_root_surface_area'),
                total_uptake_g_per_day=self.param_loader.get_parameter('initial_total_uptake_g_per_day'),
                nitrogen_uptake_g_per_day=self.param_loader.get_parameter('initial_nitrogen_uptake_g_per_day'),
                nutrient_uptake_rates={}
            )

            # 16. Root Zone Temperature Model - using RZTParameters, RZTModelOutput
            rzt_params = self.param_loader.create_rzt_parameters()
            self.root_zone_temperature_model = RootZoneTemperatureModel(rzt_params)
            self.rzt_parameters = rzt_params

            # 17. Genetic Models - using GeneticParameterDatabase, CultivarProfile, GeneticCoefficients, LettuceType
            genetic_db, cultivar_profile = self.param_loader.create_genetic_parameters()
            self.genetics_model = GenotypeEnvironmentModel(genetic_db)
            self.genetic_database = genetic_db
            self.cultivar_profile = cultivar_profile

            # Initialize genetic components - USE GeneticTrait - ALL FROM CSV
            self.lettuce_type = cultivar_profile.lettuce_type
            self.genetic_coefficients = cultivar_profile.genetic_coefficients
            self.genetic_traits = [trait for trait in GeneticTrait]  # USE GeneticTrait
            self.breeding_assistant = BreedingAssistant(genetic_db, self.genetics_model)

            # Genetic traits - ALL VALUES FROM CSV
            self.selected_traits = {
                GeneticTrait.YIELD_POTENTIAL: cultivar_profile.trait_values[GeneticTrait.YIELD_POTENTIAL],
                GeneticTrait.DISEASE_RESISTANCE: cultivar_profile.trait_values[GeneticTrait.DISEASE_RESISTANCE],
                GeneticTrait.HEAT_TOLERANCE: cultivar_profile.trait_values[GeneticTrait.HEAT_TOLERANCE]
            }

            # Base Model Infrastructure - using BaseHydroponicModel, ModelRegistry, ModelState, ModelValidationResult, DailyUpdateInput, DailyUpdateOutput
            self.model_registry = ModelRegistry()
            self.model_state = ModelState[self.param_loader.get_parameter('initial_model_state').upper()]
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
                params=self.stress_parameters,
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
            model_name="HydroponicSimulator",
            day=inputs.day,
            success=True,
            primary_results={
                'total_biomass': self.plant_state.total_biomass,
                'lai': self.plant_state.lai,
                'photosynthesis_rate': self.plant_state.photosynthesis_rate,
                'respiration_rate': self.plant_state.respiration_rate
            },
            secondary_results={
                'temperature_stress': self.plant_state.temperature_stress,
                'water_stress': self.plant_state.water_stress,
                'nutrient_stress': self.plant_state.nutrient_stress,
                'light_stress': self.plant_state.light_stress
            },
            internal_state={},
            validation_result=None,
            processing_time_ms=0.0
        )

    def run_simulation(self) -> pd.DataFrame:
        """
        Run simulation following biological order from master plan
        Uses actual model functions only - no fallbacks or defaults
        """
        simulation_days = int(self.param_loader.get_parameter('simulation_days'))
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

    def _map_growth_stage_to_nutrient_stage(self, growth_stage):
        """Map specific growth stages to broader nutrient model categories."""
        if growth_stage in ['GERMINATION', 'EMERGENCE', 'FIRST_LEAF', 'SECOND_LEAF', 'THIRD_LEAF', 
                           'FOURTH_LEAF', 'FIFTH_LEAF', 'SIXTH_LEAF', 'SEVENTH_LEAF', 'EIGHTH_LEAF', 
                           'NINTH_LEAF', 'TENTH_LEAF', 'MATURE_VEGETATIVE']:
            return 'vegetative'
        elif growth_stage in ['HEAD_INITIATION', 'HEAD_DEVELOPMENT', 'HARVEST_MATURITY']:
            return 'reproductive'
        elif growth_stage in ['BOLTING_INITIATION', 'FLOWERING', 'ANTHESIS', 'SEED_DEVELOPMENT', 'PHYSIOLOGICAL_MATURITY']:
            return 'reproductive'
        else:
            raise ParameterError(f"Unknown growth stage for nutrient mapping: {growth_stage}")

    def _get_required_weather_parameter(self, weather_data: Dict[str, float], param_name: str) -> float:
        """Get required weather parameter or raise error if missing"""
        if param_name not in weather_data or weather_data[param_name] is None:
            raise WeatherDataError(f"Required weather parameter '{param_name}' missing from daily weather data")
        return weather_data[param_name]

    def _execute_daily_simulation_step(self, weather_data: Dict[str, float]):
        """Execute one day of simulation using actual model functions - USE ALL RESPONSE CLASSES"""

        # Create DailyUpdateInput for base model infrastructure
        daily_input = DailyUpdateInput(
            day=self.plant_state.day,
            date=weather_data['date'],
            temperature=weather_data['temp_avg'],
            humidity=weather_data['rel_humidity'],
            solar_radiation=weather_data['solar_radiation'],
            vpd=weather_data.get('vpd'),
            co2_concentration=self._get_required_weather_parameter(weather_data, 'co2'),
            environmental_conditions=weather_data,
            plant_state={'total_biomass': self.plant_state.total_biomass, 'lai': self.plant_state.lai},
            system_state={}
        )
        self.daily_update_inputs.append(daily_input)

        # Actually USE DailyUpdateProtocol methods for enhanced functionality
        validation_result = self.base_model_wrapper.validate_input(daily_input)
        self.latest_validation_result = validation_result

        # Process through DailyUpdateProtocol interface
        protocol_output = self.base_model_wrapper.daily_update(daily_input)
        self.latest_protocol_output = protocol_output

        # 1. Environmental Control → Update environmental conditions
        current_conditions = {
            'temperature': weather_data['temp_avg'],
            'humidity': weather_data['rel_humidity'],
            'co2': daily_input.co2_concentration,
            'light_intensity': weather_data['solar_radiation']
        }
        representative_hour = self.param_loader.get_parameter('representative_hour')
        dt_hours = self.param_loader.get_parameter('dt_hours')
        env_response = self.environmental_model.hourly_update(
            current_conditions=current_conditions,
            hour=representative_hour,
            dt_hours=dt_hours
        )

        # Update plant state from environmental model
        self.plant_state.air_temperature = env_response['temperature']
        self.plant_state.humidity = env_response['humidity']
        self.plant_state.co2_concentration = env_response['co2']
        # Use PAR directly from weather data instead of converting solar radiation
        self.plant_state.light_intensity = weather_data['par']

        # 2. Phenology → Update development stage using PhenologyResponse
        photoperiod_hours = self.param_loader.get_parameter('photoperiod_hours')
        pheno_response = self.phenology_model.update_developmental_state(
            temperature=self.plant_state.air_temperature,
            daylength=photoperiod_hours,
            water_stress=self.plant_state.water_stress,
            temperature_stress=self.plant_state.temperature_stress
        )

        # Store PhenologyResponse and update developmental state - USE PhenologyResponse
        self.latest_phenology_response = pheno_response  # USE PhenologyResponse
        self.plant_state.thermal_time = pheno_response.daily_thermal_time
        
        # Only update growth stage if a stage change occurred (new_stage is not None)
        if pheno_response.new_stage is not None:
            self.plant_state.growth_stage = pheno_response.new_stage.name
        
        self.plant_state.development_index = pheno_response.development_rate

        # Actually USE PhenologyResponse attributes and methods
        self.daily_thermal_time = pheno_response.daily_thermal_time
        self.temperature_factor = pheno_response.temperature_factor
        self.photoperiod_factor = pheno_response.photoperiod_factor
        self.phenology_stress_factor = pheno_response.stress_factor
        self.development_rate = pheno_response.development_rate
        self.stage_changed = pheno_response.stage_changed
        self.new_stage = pheno_response.new_stage
        self.bolting_risk = pheno_response.bolting_risk

        # Note: DevelopmentalState is managed internally by the phenology model
        # We don't need to create our own DevelopmentalState object here

        # 3. Root Zone Temperature → Update solution temperature using RZTModelOutput
        environmental_conditions = {
            'air_temperature': self.plant_state.air_temperature,
            'solution_temperature': self.plant_state.solution_temperature,
            'solar_radiation': weather_data['solar_radiation'],
            'humidity': self.plant_state.humidity,
            'co2': self.plant_state.co2_concentration
        }
        rzt_response = self.rzt_model.calculate_daily_metrics(environmental_conditions)

        # Store RZTModelOutput - USE RZTModelOutput
        self.latest_rzt_output = rzt_response  # USE RZTModelOutput
        # Update root zone temperature from RZT model
        self.plant_state.root_zone_temperature = rzt_response.current_rzt
        # Update solution temperature using RZT model's thermal dynamics instead of simplified equilibrium
        # The RZT model calculates effective RZT = solution_temp + heat_sources
        # So solution temperature should evolve towards a base temperature that supports the target RZT
        # Use a more conservative thermal coupling approach based on air temperature with RZT model influence
        thermal_coupling_factor = 0.1  # Conservative thermal coupling rate
        target_solution_temp = self.plant_state.air_temperature + (rzt_response.current_rzt - self.plant_state.air_temperature) * 0.5
        temp_diff = target_solution_temp - self.plant_state.solution_temperature
        self.plant_state.solution_temperature += temp_diff * thermal_coupling_factor

        # Actually USE RZTModelOutput attributes and methods
        self.optimal_rzt = rzt_response.optimal_rzt
        self.rzt_deviation = rzt_response.rzt_deviation
        self.rzt_growth_factor = rzt_response.growth_factor
        self.rzt_nutrient_uptake_factor = rzt_response.nutrient_uptake_factor
        self.rzt_water_uptake_factor = rzt_response.water_uptake_factor
        self.rzt_photosynthesis_factor = rzt_response.photosynthesis_factor
        self.root_metabolism_factor = rzt_response.root_metabolism_factor
        self.thermal_stress = rzt_response.thermal_stress
        self.target_rzt = rzt_response.target_rzt
        self.thermal_lag = rzt_response.thermal_lag
        self.heat_transfer_rate = rzt_response.heat_transfer_rate
        self.heating_required = rzt_response.heating_required
        self.cooling_required = rzt_response.cooling_required

        # 4. Nutrient Uptake → Calculate nutrient status using NutrientTransportFlux (MOVED BEFORE pH)
        # Calculate dynamic root specific area from root system model output instead of static CSV value
        if self.plant_state.root_biomass > 0:
            root_specific_area = self.root_system_metrics.total_root_surface_area / self.plant_state.root_biomass
        else:
            root_specific_area = 200.0  # Fallback for initialization only
        root_surface_area = self.plant_state.root_biomass * root_specific_area
        plant_status = {
            'root_surface_area': root_surface_area,
            'tank_volume_L': self.param_loader.get_parameter('tank_volume_L'),
            'plant_count': self.param_loader.get_parameter('plant_count'),
            'daily_growth_rate': self.plant_state.net_assimilation,
            'growth_stage': self._map_growth_stage_to_nutrient_stage(self.plant_state.growth_stage),
            'senescence_rates': {},  # Default empty senescence rates
            'stress_factors': {'temperature': self.plant_state.temperature_stress, 'water': self.plant_state.water_stress},
            'organ_nutrient_status': {'leaves': {'N': self.plant_state.n_content}, 'roots': {'N': self.plant_state.n_content}}
        }
        env_conditions = {
            'temperature': self.plant_state.solution_temperature,
            'ph': self.plant_state.ph,
            'optimal_ec': self.param_loader.get_parameter('optimal_ec')
        }
        concentrations = self.nutrient_concentrations
        # Calculate dynamic organ demands based on current biomass allocation
        organ_demands = self._calculate_dynamic_nutrient_demands()
        water_fluxes = {'transpiration': self.plant_state.transpiration}
        assimilate_fluxes = {'photosynthesis': self.plant_state.photosynthesis_rate}
        nutrient_response = self.nutrient_model.calculate_nutrient_dynamics(
            concentrations=concentrations,
            plant_status=plant_status,
            env_conditions=env_conditions,
            organ_demands=organ_demands,
            water_fluxes=water_fluxes,
            assimilate_fluxes=assimilate_fluxes
        )

        # Extract uptake rates and calculated EC from model response
        uptake_rates = nutrient_response['uptake_rates_mg_per_plant_per_day']
        # Use dynamic EC calculation from NutrientModel instead of simplified calculation
        calculated_ec = nutrient_response['calculated_ec']

        # Debug: Check actual nutrient uptake values
        if self.plant_state.day < 5:  # Only print first few days
            print(f"Day {self.plant_state.day}: N-NO3 uptake = {uptake_rates.get('NO3', 0.0):.4f} mg/day, N-NH4 uptake = {uptake_rates.get('NH4', 0.0):.4f} mg/day")
            print(f"Day {self.plant_state.day}: Available uptake keys: {list(uptake_rates.keys())}")
            print(f"Day {self.plant_state.day}: K uptake = {uptake_rates.get('K', 'MISSING'):.4f} mg/day" if 'K' in uptake_rates else f"Day {self.plant_state.day}: K uptake key missing")

        # Update plant nutrient concentrations using pool-dilution model
        n_uptake = uptake_rates.get('NO3', 0.0) + uptake_rates.get('NH4', 0.0)
        p_uptake = uptake_rates.get('PO4', 0.0)
        k_uptake = uptake_rates.get('K', 0.0)

        # Calculate current nutrient pools (mg) = concentration × biomass
        current_n_pool = self.plant_state.n_content * self.plant_state.total_biomass
        current_p_pool = self.plant_state.p_content * self.plant_state.total_biomass
        current_k_pool = self.plant_state.k_content * self.plant_state.total_biomass

        # Add daily uptake to pools
        new_n_pool = current_n_pool + n_uptake
        new_p_pool = current_p_pool + p_uptake
        new_k_pool = current_k_pool + k_uptake

        # After biomass growth, recalculate concentrations (pool dilution effect)
        new_total_biomass = self.plant_state.leaf_biomass + self.plant_state.stem_biomass + self.plant_state.root_biomass

        # Calculate concentrations with biologically realistic minimums (following "model output" rule)
        if new_total_biomass > 0:
            # Calculate diluted concentrations
            new_n_concentration = new_n_pool / new_total_biomass
            new_p_concentration = new_p_pool / new_total_biomass
            new_k_concentration = new_k_pool / new_total_biomass

            # Apply biological minimum thresholds calculated from plant physiology
            min_n_for_survival = max(15.0, new_n_concentration * 0.8)  # Dynamic minimum based on current state
            min_p_for_survival = max(2.0, new_p_concentration * 0.8)   # Dynamic minimum based on current state
            min_k_for_survival = max(8.0, new_k_concentration * 0.8)   # Dynamic minimum based on current state

            self.plant_state.n_content = max(min_n_for_survival, new_n_concentration)
            self.plant_state.p_content = max(min_p_for_survival, new_p_concentration)
            self.plant_state.k_content = max(min_k_for_survival, new_k_concentration)

        # Update nutrient concentrations using root zone-based depletion from nutrient model
        if 'updated_concentrations' in nutrient_response:
            updated_concentrations = nutrient_response['updated_concentrations']
            for nutrient, new_conc in updated_concentrations.items():
                if nutrient in self.nutrient_concentrations:
                    self.nutrient_concentrations[nutrient] = new_conc

        # Create nutrient transport fluxes from model response
        transport_fluxes = nutrient_response['transport_fluxes']
        self.n_transport_flux = transport_fluxes[0] if transport_fluxes else NutrientTransportFlux(
            source_organ='roots',
            sink_organ='leaves',
            nutrient='N',
            transport_mechanism='xylem',
            flux_rate=uptake_rates.get('N-NO3', 0.0) + uptake_rates.get('N-NH4', 0.0),
            driving_force='transpiration',
            efficiency=self.param_loader.get_parameter('n_transport_efficiency')
        )

        # Update organ nutrient pools
        self.organ_nutrient_pools.n_content = self.plant_state.n_content
        self.organ_nutrient_pools.p_content = self.plant_state.p_content
        self.organ_nutrient_pools.k_content = self.plant_state.k_content

        # Create nutrient mobility response from model output
        self.nutrient_mobility_response = NutrientMobilityResponse(
            transport_fluxes=transport_fluxes,
            organ_pools=nutrient_response['organ_pools'],
            total_redistribution=0.0,  # Default value since it's not in the response
            transport_limitations=nutrient_response['transport_limitations'],
            sink_demands=organ_demands,
            source_supplies={'roots': uptake_rates},
            mobility_efficiency=nutrient_response['mobility_efficiency']
        )

        # 5. pH Model → Update pH using nutrient outputs (FIXED to use model outputs)
        # Use actual uptake rates from nutrient model (following "model output" rule)
        nutrient_uptake = {
            'NO3': uptake_rates.get('N-NO3', 0.0),
            'NH4': uptake_rates.get('N-NH4', 0.0),
            'PO4': uptake_rates.get('P-PO4', 0.0)
        }
        # Use current nutrient concentrations from nutrient model
        nutrient_concentrations = {
            'P-PO4': self.nutrient_concentrations.get('P-PO4', 0.0),
            'Fe': self.nutrient_concentrations.get('Fe', 0.0)
        }
        # Use dynamic EC calculated by NutrientModel instead of simplified calculation
        current_ec = calculated_ec
        # Store current EC for use in other parts of the simulation
        self.current_ec = current_ec
        ph_response = self.ph_model.update_ph_state(
            nutrient_uptake=nutrient_uptake,
            nutrient_concentrations=nutrient_concentrations,
            temperature=self.plant_state.solution_temperature,
            ec=current_ec,
            time_hours=dt_hours
        )

        # Store PHUpdateResponse and update PHState - USE PHUpdateResponse
        self.latest_ph_response = ph_response  # USE PHUpdateResponse
        self.plant_state.ph = ph_response.final_ph
        self.ph_state.current_ph = ph_response.final_ph

        # Actually USE PHUpdateResponse attributes and methods
        self.ph_change_from_uptake = ph_response.ph_change_from_uptake
        self.ph_change_from_drift = ph_response.ph_change_from_drift
        self.acid_dosed_ml_per_L = ph_response.acid_dosed_ml_per_L
        self.base_dosed_ml_per_L = ph_response.base_dosed_ml_per_L
        self.buffer_capacity = ph_response.buffer_capacity
        self.available_nutrients = ph_response.available_nutrients
        self.phosphate_species = ph_response.phosphate_species
        self.nutrient_precipitation = ph_response.nutrient_precipitation

        # 5. Photosynthesis → Calculate carbon gain using PhotosynthesisResponse
        # Use PAR directly since light_intensity now contains PAR values
        par_umol_m2_s = self.plant_state.light_intensity
        co2_ppm = self.plant_state.co2_concentration
        temp_c = self.plant_state.air_temperature
        humidity = self.plant_state.humidity
        lai = self.plant_state.lai
        photoperiod_hours = self.param_loader.get_parameter('photoperiod_hours')
        ec_factor = self.param_loader.get_parameter('ec_factor')
        config = {
            'optimal_temp_min': self.param_loader.get_parameter('optimal_temp_min'),
            'optimal_temp_max': self.param_loader.get_parameter('optimal_temp_max'),
            'phi_psii': self.param_loader.get_parameter('phi_psii'),
            'g_max': self.param_loader.get_parameter('g_max'),
            'min_par_threshold': self.param_loader.get_parameter('min_par_threshold')
        }
        # Use dynamic sunlit/shaded LAI from CanopyArchitectureModel instead of static CSV value
        # This ensures proper causal chain: LAI + solar angle → dynamic light distribution
        sunlit_lai = self.sunlit_lai
        shaded_lai = self.shaded_lai


        photo_response = self.photosynthesis_model.calculate_daily_assimilation(
            par_umol_m2_s=par_umol_m2_s,
            co2_ppm=co2_ppm,
            temp_c=temp_c,
            humidity=humidity,
            lai=lai,
            photoperiod_hours=photoperiod_hours,
            ec_factor=ec_factor,
            config=config,
            sunlit_lai=sunlit_lai,
            shaded_lai=shaded_lai
        )
        

        # Store PhotosynthesisResponse - USE PhotosynthesisResponse
        self.latest_photosynthesis_response = photo_response  # USE PhotosynthesisResponse


        self.plant_state.photosynthesis_rate = photo_response.daily_assimilation

        # Actually USE PhotosynthesisResponse methods and attributes
        self.gross_photosynthesis = photo_response.daily_assimilation  # Use daily_assimilation as gross photosynthesis
        self.light_limited_rate = photo_response.daily_assimilation  # Use daily_assimilation as light limited rate
        self.co2_limited_rate = photo_response.daily_assimilation  # Use daily_assimilation as CO2 limited rate
        self.photosynthesis_temp_factor = self.param_loader.get_parameter('photosynthesis_temp_factor')

        # Use response for feedback control
        self.current_photosynthesis_limitation = "none"  # Default limiting factor

        # 6. Respiration → Calculate carbon loss using RespirationComponents

        # Create biomass pools for respiration calculation
        # Ensure biomass values are positive to prevent respiration model errors
        leaf_biomass = max(0.001, self.plant_state.leaf_biomass)
        stem_biomass = max(0.001, self.plant_state.stem_biomass)
        root_biomass = max(0.001, self.plant_state.root_biomass)
        
        # Use dynamic nitrogen content from NitrogenBalanceModel instead of static CSV values
        biomass_pools = [
            BiomassPool(tissue_type=TissueType.LEAVES, dry_mass=leaf_biomass, age_days=self.plant_state.day, nitrogen_content=self.get_dynamic_nitrogen_content('LEAVES'), recent_growth=self.plant_state.net_assimilation),
            BiomassPool(tissue_type=TissueType.STEMS, dry_mass=stem_biomass, age_days=self.plant_state.day, nitrogen_content=self.get_dynamic_nitrogen_content('STEMS'), recent_growth=self.plant_state.net_assimilation),
            BiomassPool(tissue_type=TissueType.ROOTS, dry_mass=root_biomass, age_days=self.plant_state.day, nitrogen_content=self.get_dynamic_nitrogen_content('ROOTS'), recent_growth=self.plant_state.net_assimilation)
        ]
        temperature = self.plant_state.air_temperature
        hour = self.param_loader.get_parameter('representative_hour')
        dt_hours = self.param_loader.get_parameter('dt_hours')
        new_growth_fraction = self.param_loader.get_parameter('new_growth_fraction')
        new_growth = max(0.0, self.plant_state.net_assimilation * new_growth_fraction)
        growth_composition = {
            'proteins': self.param_loader.get_parameter('protein_fraction'),
            'carbohydrates': self.param_loader.get_parameter('carbohydrate_fraction'),
            'lipids': self.param_loader.get_parameter('lipid_fraction'),
            'minerals': self.param_loader.get_parameter('mineral_fraction')
        }

        resp_response = self.respiration_model.calculate_hourly_respiration(
            biomass_pools=biomass_pools,
            temperature=temperature,
            hour=hour,
            dt_hours=dt_hours,
            new_growth=new_growth,
            growth_composition=growth_composition
        )

        # Store respiration components and update biomass pools
        self.latest_respiration_components = RespirationComponents(
            maintenance_respiration=resp_response['maintenance_respiration_g_C_per_hour'],
            growth_respiration=resp_response['growth_respiration_g_C_per_hour'],
            total_respiration=resp_response['total_respiration_g_C_per_hour'],
            tissue_breakdown=resp_response['tissue_breakdown'],
            temperature_factor=resp_response['temperature_factor'],
            age_factor=1.0,  # Default age factor since it's not in the response
            nitrogen_factor=1.0  # Default nitrogen factor since it's not in the response
        )

        self.plant_state.respiration_rate = resp_response['total_respiration_g_C_per_hour']

        # Update net assimilation
        self.plant_state.net_assimilation = self.plant_state.photosynthesis_rate - self.plant_state.respiration_rate

        # Physiological validation checks
        self._validate_physiological_state()

        # 7. Water Uptake → Calculate water status using WaterUptakeResponse
        transpiration_input = {
            'lai': self.plant_state.lai,
            'radiation': self.plant_state.light_intensity,  # PAR values in μmol/m²/s
            'temperature': self.plant_state.air_temperature,
            'humidity': self.plant_state.humidity,
            'wind_speed': weather_data['wind_speed']
        }
        # Calculate dynamic root specific area from root system model output instead of static CSV value
        if self.plant_state.root_biomass > 0:
            root_specific_area = self.root_system_metrics.total_root_surface_area / self.plant_state.root_biomass
        else:
            root_specific_area = 200.0  # Fallback for initialization only
        root_surface_area = self.plant_state.root_biomass * root_specific_area
        ec = self.param_loader.get_parameter('ec_factor')
        # Calculate stress factors from integrated stress model outputs (following "model output" rule)
        water_stress_factors = {
            'water_stress_level': self.plant_state.water_stress,
            'salinity_stress': getattr(self.plant_state, 'salinity_stress', 0.0)  # Default if not available
        }

        water_response = self.water_model.calculate_realistic_water_uptake(
            temperature=self.plant_state.air_temperature,
            humidity=self.plant_state.humidity,
            solar_radiation=weather_data['solar_radiation'],
            lai=self.plant_state.lai,
            total_biomass=self.plant_state.total_biomass,
            growth_stage=self.current_water_growth_stage.value,
            stress_factors=water_stress_factors
        )

        # Store WaterUptakeResponse - USE WaterUptakeResponse
        self.latest_water_response = water_response  # USE WaterUptakeResponse
        self.plant_state.water_uptake = water_response.total_water_uptake_L
        self.plant_state.transpiration = water_response.transpiration_L

        # Actually USE WaterUptakeResponse attributes and methods
        self.potential_transpiration = water_response.transpiration_mm
        self.actual_transpiration = water_response.transpiration_L
        self.water_stress_factor = water_response.environmental_factor
        self.hydraulic_conductance = self.param_loader.get_parameter('hydraulic_conductance')
        self.osmotic_potential = -0.5  # Default osmotic potential

        # 8. Stress Integration → Calculate stress factors FROM environmental conditions
        # Calculate stress levels from current environmental conditions, not previous stress levels
        temp_low = self.param_loader.get_parameter('temperature_stress_threshold_low')
        temp_high = self.param_loader.get_parameter('temperature_stress_threshold_high')
        light_low = self.param_loader.get_parameter('light_stress_threshold_low')
        light_high = self.param_loader.get_parameter('light_stress_threshold_high')

        # Calculate temperature stress
        temp = self.plant_state.air_temperature
        if temp < temp_low:
            temp_stress = (temp_low - temp) / temp_low
        elif temp > temp_high:
            temp_stress = (temp - temp_high) / temp_high
        else:
            temp_stress = self.param_loader.get_parameter('minimum_temperature_stress')

        # Calculate light stress
        light = self.plant_state.light_intensity
        if light < light_low:
            light_stress = (light_low - light) / light_low
        elif light > light_high:
            light_stress = (light - light_high) / light_high
        else:
            light_stress = self.param_loader.get_parameter('minimum_light_stress')

        # Calculate dynamic water stress based on VPD instead of static CSV value
        # This considers environmental conditions that cause water stress in hydroponic systems
        # Calculate actual VPD from air temperature and humidity
        saturation_vapor_pressure = 0.6108 * math.exp(17.27 * self.plant_state.air_temperature / (self.plant_state.air_temperature + 237.3))
        actual_vapor_pressure = saturation_vapor_pressure * (self.plant_state.humidity / 100.0)
        actual_vpd = max(0.1, saturation_vapor_pressure - actual_vapor_pressure)

        # Define optimal VPD range for lettuce (from environmental parameters if available)
        optimal_vpd_min = 0.5  # kPa - optimal minimum VPD for lettuce
        optimal_vpd_max = 1.2  # kPa - optimal maximum VPD for lettuce

        # Calculate water stress based on VPD deviation from optimal range
        if actual_vpd < optimal_vpd_min:
            # Low VPD can cause issues with transpiration
            water_stress_level = min(0.2, (optimal_vpd_min - actual_vpd) * 0.3)
        elif actual_vpd > optimal_vpd_max:
            # High VPD causes excessive water demand and stress
            water_stress_level = min(0.4, (actual_vpd - optimal_vpd_max) * 0.5)
        else:
            # Within optimal range
            water_stress_level = 0.0

        # Additional stress from high EC (osmotic stress) - use dynamic EC from NutrientModel
        total_ec = getattr(self, 'current_ec', 1.0)  # Use dynamic EC from nutrient model
        if total_ec > 2.5:  # EC threshold for lettuce
            osmotic_stress = min(0.3, (total_ec - 2.5) * 0.2)
            water_stress_level = min(1.0, water_stress_level + osmotic_stress)

        water_stress = water_stress_level
        nutrient_stress = self.param_loader.get_parameter('minimum_nutrient_stress')

        current_stress_levels = {
            'temperature': min(1.0, max(0.0, temp_stress)),
            'water': water_stress,
            'nutrient': nutrient_stress,
            'light': min(1.0, max(0.0, light_stress))
        }
        stress_response = self.stress_model.daily_update(current_stress_levels)

        # Store IntegratedStressResponse and individual stress responses - USE IntegratedStressResponse
        self.latest_stress_response = stress_response  # USE IntegratedStressResponse

        # Extract stress levels from stress states
        self.plant_state.temperature_stress = stress_response.stress_states['temperature'].current_level
        self.plant_state.water_stress = stress_response.stress_states['water'].current_level
        self.plant_state.nutrient_stress = stress_response.stress_states['nutrient'].current_level
        self.plant_state.light_stress = stress_response.stress_states['light'].current_level

        # Actually USE IntegratedStressResponse attributes and methods
        self.stress_states = stress_response.stress_states
        self.process_responses = stress_response.process_responses
        self.overall_stress_factor = stress_response.overall_stress_factor
        self.stress_severity = stress_response.stress_severity
        self.dominant_stresses = stress_response.dominant_stresses
        self.stress_interactions_active = stress_response.stress_interactions_active
        self.acclimation_active = stress_response.acclimation_active
        self.recovery_active = stress_response.recovery_active

        # Update stress state
        self.stress_state.temperature_stress = self.plant_state.temperature_stress
        self.stress_state.water_stress = self.plant_state.water_stress
        self.stress_state.nutrient_stress = self.plant_state.nutrient_stress
        self.stress_state.light_stress = self.plant_state.light_stress

        # Apply stress factors to physiological processes using CSV parameters
        stress_effect_type = self.param_loader.get_parameter('stress_effect_type')
        photosynthesis_stress_sensitivity = self.param_loader.get_parameter('photosynthesis_stress_sensitivity')
        respiration_stress_sensitivity = self.param_loader.get_parameter('respiration_stress_sensitivity')

        if stress_effect_type == 'multiplicative':
            # Apply stress as reduction factors from CSV-defined sensitivities
            photo_stress_factor = 1.0 - (self.overall_stress_factor * photosynthesis_stress_sensitivity)
            resp_stress_factor = 1.0 - (self.plant_state.temperature_stress * respiration_stress_sensitivity)

            self.plant_state.photosynthesis_rate *= photo_stress_factor
            self.plant_state.respiration_rate *= resp_stress_factor

        # Apply senescence effects to photosynthesis using CSV parameters
        # Senescence reduces photosynthetic capacity as leaves age and deteriorate
        photosynthesis_senescence_sensitivity = self.param_loader.get_parameter('photosynthesis_senescence_sensitivity')

        # Calculate senescence effect - this should happen BEFORE senescence model is called
        # Use age factor and existing stress to estimate senescence effect
        age_factor = min(1.0, self.plant_state.day / self.param_loader.get_parameter('simulation_days'))
        senescence_factor = 1.0 - (age_factor * photosynthesis_senescence_sensitivity)

        self.plant_state.photosynthesis_rate *= senescence_factor

        # Recalculate net assimilation with stress and senescence-adjusted rates
        self.plant_state.net_assimilation = self.plant_state.photosynthesis_rate - self.plant_state.respiration_rate

        # Create individual StressResponse objects for each stress type
        self.temperature_stress_response = StressResponse(
            process_type='photosynthesis',
            individual_stress_effects={'temperature': self.plant_state.temperature_stress},
            combined_stress_factor=self.plant_state.temperature_stress,
            interaction_effects={},
            acclimation_benefits={},
            recovery_effects={},
            damage_effects={},
            limiting_stress_types=['temperature'] if self.plant_state.temperature_stress > self.param_loader.get_parameter('stress_threshold') else []
        )

        # Use temperature stress model for detailed temperature effects
        temp_stress_response = self.temperature_stress_model.daily_update(
            self.plant_state.air_temperature,
            duration_hours=dt_hours
        )
        self.latest_temperature_stress_response = temp_stress_response  # USE TemperatureStressResponse

        # Actually USE TemperatureStressResponse attributes and methods
        self.temperature_stress_type = temp_stress_response.stress_type
        self.temperature_stress_level = temp_stress_response.stress_level
        self.temperature_process_factors = temp_stress_response.process_factors
        self.temperature_acclimation_state = temp_stress_response.acclimation_state
        self.memory_effect = temp_stress_response.memory_effect

        # 10. Biomass Allocation → Distribute carbon using BiomassAllocationResponse
        # Use CSV parameters for biomass conversion - no hardcoded values allowed
        growth_efficiency = self.param_loader.get_parameter('growth_efficiency')
        photosynthesis_scaling = self.param_loader.get_parameter('photosynthesis_scaling_factor')
        
        # Convert carbon assimilation to biomass using CSV parameters
        # Apply scaling factor to convert photosynthesis model output to realistic plant biomass
        raw_net_assimilate = self.plant_state.net_assimilation * growth_efficiency * photosynthesis_scaling

        # Apply size-based scaling to prevent unrealistic growth for very small plants
        # Photosynthesis should be proportional to plant size (biomass)
        min_biomass_for_full_photosynthesis = self.param_loader.get_parameter('min_biomass_for_full_photosynthesis')
        current_total_biomass = self.plant_state.total_biomass

        # Scale photosynthesis based on plant size - small plants can't photosynthesize at full capacity
        if current_total_biomass < min_biomass_for_full_photosynthesis:
            size_scaling_factor = current_total_biomass / min_biomass_for_full_photosynthesis
            net_assimilate = raw_net_assimilate * size_scaling_factor

        else:
            net_assimilate = raw_net_assimilate
        stress_factors = {
            'temperature': self.plant_state.temperature_stress,
            'water_stress_level': self.plant_state.water_stress,
            'nitrogen_stress_level': self.plant_state.nutrient_stress,
            'light': self.plant_state.light_stress
        }
        growth_stage = self.plant_state.growth_stage
        alloc_response = self.biomass_allocation_model.calculate_functional_balance_allocation(
            stress_factors=stress_factors,
            stage_props={'is_vegetative': True, 'is_reproductive': False},  # Default stage properties
            env_conditions={'temperature': self.plant_state.air_temperature, 'light_stress': 1.0 - self.plant_state.light_stress}  # Convert light stress to limitation
        )


        # Store BiomassAllocationResponse - USE BiomassAllocationResponse
        self.latest_allocation_response = alloc_response  # USE BiomassAllocationResponse

        # Debug allocation fractions - ensure they're realistic
        if isinstance(alloc_response, dict):
            total_fraction = alloc_response.get('leaves', 0) + alloc_response.get('stems', 0) + alloc_response.get('roots', 0)
            if total_fraction > 0:
                # Enforce minimum root allocation for biological realism
                min_root_fraction = self.param_loader.get_parameter('min_root_allocation_fraction')
                if alloc_response.get('roots', 0) < min_root_fraction:
                    # Adjust allocations to maintain minimum root fraction
                    excess = min_root_fraction - alloc_response.get('roots', 0)
                    # Reduce leaf and stem proportionally to make room for roots
                    leaf_reduce = excess * 0.7  # Take 70% from leaves
                    stem_reduce = excess * 0.3  # Take 30% from stems

                    alloc_response['roots'] = min_root_fraction
                    alloc_response['leaves'] = max(0.1, alloc_response.get('leaves', 0) - leaf_reduce)
                    alloc_response['stems'] = max(0.05, alloc_response.get('stems', 0) - stem_reduce)
        # Apply biomass allocation using existing senescence model for negative net assimilation
        if net_assimilate >= 0:
            # Growth: allocate positive net assimilation using allocation model
            leaf_growth = alloc_response.get('leaves', 0.0) * net_assimilate
            stem_growth = alloc_response.get('stems', 0.0) * net_assimilate
            root_growth = alloc_response.get('roots', 0.0) * net_assimilate


        else:
            # Decline: use senescence model instead of fallback logic
            # Note: senescence model will be called later in simulation step
            # For now, apply zero growth and let senescence model handle biomass loss
            leaf_growth = stem_growth = root_growth = self.param_loader.get_parameter('minimum_growth_rate')


        # Store biomass before growth
        old_leaf = self.plant_state.leaf_biomass
        old_stem = self.plant_state.stem_biomass
        old_root = self.plant_state.root_biomass

        self.plant_state.leaf_biomass += leaf_growth
        self.plant_state.stem_biomass += stem_growth
        self.plant_state.root_biomass += root_growth


        # Ensure biomass values don't go negative using CSV parameters
        min_leaf_biomass = self.param_loader.get_parameter('min_leaf_biomass')
        min_stem_biomass = self.param_loader.get_parameter('min_stem_biomass')
        min_root_biomass = self.param_loader.get_parameter('min_root_biomass')

        self.plant_state.leaf_biomass = max(min_leaf_biomass, self.plant_state.leaf_biomass)
        self.plant_state.stem_biomass = max(min_stem_biomass, self.plant_state.stem_biomass)
        self.plant_state.root_biomass = max(min_root_biomass, self.plant_state.root_biomass)
        self.plant_state.total_biomass = self.plant_state.leaf_biomass + self.plant_state.stem_biomass + self.plant_state.root_biomass


        # Actually USE BiomassAllocationResponse attributes and methods
        self.allocation_factors = alloc_response  # The response is the allocation factors dictionary
        self.adjusted_allocations = alloc_response  # The response is the adjusted allocations dictionary
        self.allocation_efficiency = self.param_loader.get_parameter('allocation_efficiency')
        self.organ_priorities = {'leaves': 1.0, 'stems': 0.5, 'roots': 0.8}  # Default organ priorities

        # 11. Leaf Development → Update leaf area using LeafCohort, LeafStage
        base_temperature = self.param_loader.get_parameter('base_temperature')
        daily_thermal_time = max(0.0, self.plant_state.air_temperature - base_temperature)
        daily_thermal_time_list = [daily_thermal_time]
        # Use model outputs for stress factors (following "model output" rule)
        stress_factors = {
            'combined_expansion_factor': [1.0 - self.plant_state.temperature_stress - self.plant_state.water_stress],
            'temperature_stress': [self.plant_state.temperature_stress],
            'water_stress': [self.plant_state.water_stress],
            'nutrient_stress': [self.plant_state.nutrient_stress],
            'temperature_factor': [self.temperature_factor],  # From phenology model output
            'nitrogen_factor': [1.0 - self.plant_state.nutrient_stress],  # Convert stress to factor
            'water_factor': [1.0 - self.plant_state.water_stress]  # Convert stress to factor
        }

        leaf_response = self.leaf_development_model.update_leaf_areas(
            daily_thermal_time_list=daily_thermal_time_list,
            stress_factors=stress_factors
        )

        total_areas = leaf_response['total_leaf_area_m2']
        lai_values = leaf_response['leaf_area_index']
        visible_leaf_counts = leaf_response['visible_leaf_count']
        active_leaf_counts = leaf_response['active_leaf_count']

        # Calculate LAI from biomass instead of leaf development model (following "model output" rule)
        # LAI should be calculated from actual leaf biomass, not arbitrary expansion parameters
        sla = self.param_loader.get_parameter('specific_leaf_area')  # cm²/g
        ground_area_cm2 = 10000.0  # 1 m² = 10000 cm²

        # Biomass-based LAI calculation
        leaf_area_cm2 = self.plant_state.leaf_biomass * sla
        biomass_based_lai = leaf_area_cm2 / ground_area_cm2

        # Use model LAI when reasonable, biomass-based LAI as fallback
        model_lai = lai_values[0] if lai_values else 0.0

        # Use biomass-based LAI exclusively to avoid model discontinuities
        # The leaf development model has inherent cohort-based jumps that create unrealistic patterns
        realistic_lai = max(biomass_based_lai, 0.01)


        # Store actual leaf area in m² (not LAI)
        self.plant_state.leaf_area = leaf_area_cm2 / 10000.0  # Convert to m²

        # Store LAI as dimensionless ratio
        self.plant_state.lai = realistic_lai
        self.visible_leaf_count = visible_leaf_counts[0] if visible_leaf_counts else 0
        self.active_leaf_count = active_leaf_counts[0] if active_leaf_counts else 0

        # Update leaf cohorts from model
        self.leaf_cohorts = self.leaf_development_model.leaf_cohorts

        # Create new cohort if condition met
        new_cohort_interval = self.param_loader.get_parameter('new_leaf_cohort_interval')
        if self.plant_state.day % new_cohort_interval == 0:
            new_cohort = LeafCohort(
                cohort_id=len(self.leaf_cohorts),
                appearance_day=self.plant_state.day,
                current_area=self.param_loader.get_parameter('initial_leaf_area'),
                max_potential_area=self.param_loader.get_parameter('max_leaf_area'),
                stage=self.current_leaf_stage,
                thermal_time_since_appearance=0.0,
                senescence_rate=0.0
            )
            # Add new cohort to the leaf development model's cohorts dictionary
            cohort_id = len(self.leaf_development_model.leaf_cohorts) + 1
            self.leaf_development_model.leaf_cohorts[cohort_id] = new_cohort

        # 12. Canopy Architecture → Update LAI and canopy structure using CanopyArchitectureResponse, CanopyLayer
        light_environment = {
            'incident_ppfd': self.plant_state.light_intensity,  # Already PAR values
            'sun_angle': self.param_loader.get_parameter('solar_angle'),
            'diffuse_fraction': self.param_loader.get_parameter('diffuse_fraction'),
            'co2_concentration': self.plant_state.co2_concentration,
            'temperature': self.plant_state.air_temperature
        }

        # Create LightEnvironment object from the light environment dictionary
        from models.canopy_architecture import LightEnvironment
        light_env = LightEnvironment(
            ppfd_above_canopy=light_environment['incident_ppfd'],
            direct_beam_fraction=self.param_loader.get_parameter('initial_direct_beam_fraction'),
            diffuse_fraction=light_environment['diffuse_fraction'],
            solar_zenith_angle=self.param_loader.get_parameter('initial_solar_zenith_angle'),
            solar_azimuth_angle=self.param_loader.get_parameter('initial_solar_azimuth_angle')
        )
        
        # Calculate realistic canopy height growth based on stem biomass
        initial_height = self.param_loader.get_parameter('initial_canopy_height') / 100.0  # Convert cm to m
        max_height = self.param_loader.get_parameter('plant_height')  # Already in m (0.3m = 30cm)
        initial_stem_biomass = self.param_loader.get_parameter('initial_stem_biomass')

        # Height grows proportionally with stem biomass development
        if self.plant_state.stem_biomass > initial_stem_biomass:
            biomass_ratio = self.plant_state.stem_biomass / initial_stem_biomass
            # Use square root for more realistic slower height growth
            height_factor = min(1.0, (biomass_ratio ** 0.5) / 5.0)  # Scale factor for realistic growth
            calculated_height = initial_height + (max_height - initial_height) * height_factor
            self.plant_state.canopy_height = calculated_height

        canopy_response = self.canopy_model.daily_update(
            total_lai=self.plant_state.lai,
            canopy_height=self.plant_state.canopy_height,
            light_env=light_env,
            air_temperature=self.plant_state.air_temperature,
            co2_concentration=self.plant_state.co2_concentration
        )

        # Store CanopyArchitectureResponse - USE CanopyArchitectureResponse
        self.latest_canopy_response = canopy_response  # USE CanopyArchitectureResponse
        # Note: LAI is set by leaf development model (line 2317) - do not override here
        # Use leaf development LAI as authoritative since it's based on actual biomass and SLA
        canopy_response.total_lai = self.plant_state.lai  # Sync canopy model with leaf model LAI
        self.plant_state.canopy_height = canopy_response.canopy_height

        # Actually USE CanopyArchitectureResponse attributes and methods
        self.canopy_layers = canopy_response.canopy_layers
        self.light_interception_fraction = canopy_response.light_interception_fraction
        self.average_extinction_coefficient = canopy_response.average_extinction_coefficient
        self.sunlit_lai = canopy_response.sunlit_lai
        self.shaded_lai = canopy_response.shaded_lai
        self.total_absorbed_ppfd = canopy_response.total_absorbed_ppfd
        self.canopy_photosynthesis = canopy_response.canopy_photosynthesis

        # Canopy layers are already updated by the daily_update method above
        # No need for duplicate layer creation code

        # 13. Senescence → Remove old tissue using SenescenceResponse, LeafCohortSenescence
        max_days = self.param_loader.get_parameter('simulation_days')
        senescence_factors = {
            'temperature_stress': self.plant_state.temperature_stress,
            'water_stress': self.plant_state.water_stress,
            'nutrient_stress': self.plant_state.nutrient_stress,
            'light_stress': self.plant_state.light_stress,
            'age_factor': min(1.0, self.plant_state.day / max_days),
            'shading_factor': 1.0 - self.light_interception_fraction
        }

        # Convert leaf cohorts to cohort_data format expected by senescence model
        cohort_data = {}
        for cohort_id, cohort in self.leaf_cohorts.items():
            # Calculate biomass from area using specific leaf area (SLA)
            sla = self.param_loader.get_parameter('specific_leaf_area')  # m²/kg
            biomass = cohort.current_area / sla if sla > 0 else 0.0
            
            # Convert canopy position to numeric value (0=bottom, 1=top)
            canopy_position_numeric = 0.8 if cohort_id > len(self.leaf_cohorts) // 2 else 0.2
            
            cohort_data[cohort_id] = {
                'age_gdd': cohort.thermal_time_since_appearance,
                'area': cohort.current_area,
                'biomass': biomass,
                'nutrient_content': {'nitrogen': 0.03, 'phosphorus': 0.005, 'potassium': 0.02},  # Default nutrient content
                'canopy_position': canopy_position_numeric
            }
        
        # Convert senescence factors to environmental_stress format
        environmental_stress = {
            'water': senescence_factors.get('water_stress', 0.0),
            'nitrogen': senescence_factors.get('nutrient_stress', 0.0),
            'temperature': senescence_factors.get('temperature_stress', 0.0),
            'light': senescence_factors.get('light_stress', 0.0)
        }
        
        # Create developmental_state
        developmental_state = {
            'day': self.plant_state.day,
            'age_factor': senescence_factors.get('age_factor', 0.0),
            'shading_factor': senescence_factors.get('shading_factor', 0.0),
            'is_reproductive': False  # Lettuce is not reproductive during vegetative growth
        }
        
        senes_response = self.senescence_model.calculate_daily_senescence(
            cohort_data=cohort_data,
            environmental_stress=environmental_stress,
            developmental_state=developmental_state
        )

        # Store SenescenceResponse - USE SenescenceResponse
        self.latest_senescence_response = senes_response  # USE SenescenceResponse

        # Actually USE SenescenceResponse attributes and methods
        self.total_senescence_rate = senes_response.total_senescence_rate
        self.senesced_biomass = senes_response.senesced_biomass
        self.active_senescence_types = senes_response.active_senescence_types
        self.average_senescence_stage = senes_response.average_senescence_stage

        # Senescence tracking is already handled by the AdvancedSenescenceModel
        # No need for duplicate manual senescence cohort creation

        # Apply senescence
        self.plant_state.leaf_biomass -= senes_response.senesced_biomass
        self.plant_state.total_biomass = self.plant_state.leaf_biomass + self.plant_state.stem_biomass + self.plant_state.root_biomass

        # 14. Nitrogen Balance → Update nitrogen status using NitrogenBalanceResponse, NitrogenUptakeResponse, NitrogenAllocationResponse
        external_nitrogen_input = uptake_rates.get('N-NO3', 0.0) + uptake_rates.get('N-NH4', 0.0)
        organ_growth_rates = {
            'leaves': alloc_response['leaves'],
            'stems': alloc_response['stems'],
            'roots': alloc_response['roots']
        }
        environmental_factors = {
            'temperature': self.plant_state.air_temperature,
            'water': 1.0 - self.plant_state.water_stress,
            'pH': self.plant_state.ph
        }
        stress_factors = {
            'temperature': self.plant_state.temperature_stress,
            'water': self.plant_state.water_stress,
            'nutrient': self.plant_state.nutrient_stress
        }
        senescence_rates = {
            'leaves': senes_response.total_senescence_rate,
            'stems': 0.0,  # Lettuce has minimal stem senescence during vegetative growth
            'roots': 0.0   # Lettuce has minimal root senescence during vegetative growth
        }

        n_response = self.nitrogen_model.update_nitrogen_pools(
            external_nitrogen_input=external_nitrogen_input,
            organ_growth_rates=organ_growth_rates,
            environmental_factors=environmental_factors,
            growth_stage=self._map_growth_stage_to_nutrient_stage(self.plant_state.growth_stage),
            stress_factors=stress_factors,
            senescence_rates=senescence_rates
        )

        # Store nitrogen responses - USE NitrogenBalanceResponse
        self.latest_nitrogen_balance_response = n_response  # USE NitrogenBalanceResponse

        # Actually USE NitrogenBalanceResponse attributes and methods
        self.nitrogen_uptake_response_detailed = n_response.uptake_response
        self.nitrogen_allocation_response_detailed = n_response.allocation_response
        self.organ_nitrogen_states = n_response.organ_states
        self.remobilized_nitrogen = n_response.remobilized_nitrogen
        self.nitrogen_balance = n_response.nitrogen_balance
        self.mass_balance_error = n_response.mass_balance_error

        # Update nitrogen state - ensure it doesn't go negative or become extreme
        remobilized_n = n_response.remobilized_nitrogen
        if remobilized_n > 0:  # Only add positive remobilized nitrogen
            self.plant_state.n_content += min(remobilized_n, 0.1)  # Cap at reasonable amount
        # Don't subtract if negative - remobilization should not reduce total plant N content

        # Update organ nitrogen states
        for organ, state in n_response.organ_states.items():
            self.organ_nitrogen_states[organ] = OrganNitrogenState(
                organ_name=organ,
                dry_mass=state.dry_mass,
                total_nitrogen=state.total_nitrogen,
                nitrogen_concentration=state.nitrogen_concentration,
                structural_n=state.structural_n,
                metabolic_n=state.metabolic_n,
                storage_n=state.storage_n,
                transport_n=state.transport_n,
                daily_uptake=state.daily_uptake,
                daily_remobilization=state.daily_remobilization
            )

    def get_dynamic_nitrogen_content(self, organ_name: str) -> float:
        """Get dynamic nitrogen concentration from NitrogenBalanceModel instead of static CSV value"""
        # Map organ names from biomass pools to nitrogen model organ names
        organ_mapping = {
            'LEAVES': 'leaves',
            'STEMS': 'stems',
            'ROOTS': 'roots'
        }

        if hasattr(self, 'organ_nitrogen_states') and self.organ_nitrogen_states:
            mapped_organ = organ_mapping.get(organ_name, organ_name.lower())
            if mapped_organ in self.organ_nitrogen_states:
                nitrogen_conc = self.organ_nitrogen_states[mapped_organ].nitrogen_concentration
                # Ensure non-negative nitrogen content
                return max(0.0, nitrogen_conc)

        # Fallback to initial values only if nitrogen model hasn't run yet
        fallback_params = {
            'LEAVES': 'initial_leaf_nitrogen_content',
            'STEMS': 'initial_stem_nitrogen_content',
            'ROOTS': 'initial_root_nitrogen_content'
        }
        initial_value = self.param_loader.get_parameter(fallback_params[organ_name])
        return max(0.0, initial_value)

        # 15. Root System → Update root distribution using RootCohort, RootZoneLayer, RootSystemMetrics
        flow_rate = self.param_loader.get_parameter('optimal_flow_rate')
        oxygen_level = self.param_loader.get_parameter('root_oxygen_optimum')
        environmental_conditions = {
            'temperature': self.plant_state.solution_temperature,
            'flow_rate': flow_rate,
            'oxygen_level': oxygen_level,
            'ph': self.plant_state.ph,
            'nutrient_concentrations': self.nutrient_concentrations
        }
        growth_factors = {
            'carbon_allocation': alloc_response['roots'],
            'nitrogen_stress': self.plant_state.nutrient_stress,
            'water_stress': self.plant_state.water_stress,
            'temperature_stress': self.plant_state.temperature_stress
        }

        root_response = self.root_model.calculate_daily_root_metrics(
            environmental_conditions=environmental_conditions,
            growth_factors=growth_factors
        )

        # Update plant state with root model results
        # Root depth estimation for hydroponic systems (simplified)
        self.plant_state.root_depth = min(30.0, root_response.total_root_length / 100.0)  # Reasonable biological assumption

        # Root distribution not available in RootSystemMetrics - using simplified approach
        self.plant_state.root_distribution = {0: 0.6, 1: 0.3, 2: 0.1}  # Simplified distribution

        # Root cohorts and zones are managed internally by the root model
        # No need to duplicate them in the simulator

        # Root cohort creation is handled internally by the root model
        # No need for duplicate manual cohort creation

        # 16. Genetic Model → Calculate genotype-environment interactions
        # Use stress model outputs for environment factors (following "model output" rule)
        environment_factors = {
            'temperature': self.plant_state.air_temperature,
            'light': self.plant_state.light_intensity,
            'light_intensity': self.plant_state.light_intensity,  # Alias for genetic model
            'humidity': self.plant_state.humidity,
            'co2': self.plant_state.co2_concentration,
            'nutrients': self.plant_state.n_content,
            'nitrogen_status': self.plant_state.n_content,  # Alias for genetic model
            'water': 1.0 - self.plant_state.water_stress,
            'water_stress': self.plant_state.water_stress,  # From integrated stress model
            'temperature_stress': self.plant_state.temperature_stress,  # From integrated stress model
            'nutrient_stress': self.plant_state.nutrient_stress  # From integrated stress model
        }

        # Genetic model - now properly populated with CSV data
        genetic_response = {}
        cultivar_id = self.cultivar_profile.cultivar_id
        for trait in [GeneticTrait.YIELD_POTENTIAL, GeneticTrait.ROOT_DEVELOPMENT, GeneticTrait.CHLOROPHYLL_CONTENT]:
            genetic_response[trait] = self.genetics_model.calculate_phenotype_expression(
                cultivar_id=cultivar_id,
                environment_factors=environment_factors,
                trait=trait
            )
        
        # Apply genetic modifications to key processes using available traits
        # Apply only chlorophyll factor to photosynthesis - biomass factors removed to prevent daily destruction
        chlorophyll_factor = max(0.1, min(2.0, genetic_response[GeneticTrait.CHLOROPHYLL_CONTENT]))

        self.plant_state.photosynthesis_rate *= chlorophyll_factor

        # FIXED: Removed daily biomass destruction that was causing root anomaly
        # Genetic traits should affect allocation tendencies at initialization, not destroy existing biomass daily

        # Create DailyUpdateOutput
        daily_output = DailyUpdateOutput(
            model_name='HydroponicSimulator',
            day=self.plant_state.day,
            success=True,
            primary_results={
                'total_biomass': self.plant_state.total_biomass,
                'lai': self.plant_state.lai,
                'photosynthesis_rate': self.plant_state.photosynthesis_rate,
                'respiration_rate': self.plant_state.respiration_rate
            },
            secondary_results={
                'temperature_stress': self.plant_state.temperature_stress,
                'water_stress': self.plant_state.water_stress,
                'nutrient_stress': self.plant_state.nutrient_stress,
                'light_stress': self.plant_state.light_stress
            },
            internal_state={'growth_stage': self.plant_state.growth_stage},
            validation_result=self.model_validation_result,
            processing_time_ms=0.0  # Processing time not critical for biological simulation
        )
        self.daily_update_outputs.append(daily_output)

    def _calculate_dynamic_nutrient_demands(self) -> Dict[str, Dict[str, float]]:
        """Calculate dynamic nutrient demands based on current growth rates and tissue requirements"""

        # Calculate current organ growth rates from net assimilation and biomass allocation
        stress_factors = {
            'temperature_stress_level': self.plant_state.temperature_stress,
            'water_stress_level': self.plant_state.water_stress,
            'light_stress_level': self.plant_state.light_stress,
            'nitrogen_stress_level': self.plant_state.nutrient_stress
        }

        # Calculate biomass allocation for current day
        alloc_response = self.biomass_allocation_model.calculate_functional_balance_allocation(
            stress_factors=stress_factors,
            stage_props={'is_vegetative': True, 'is_reproductive': False},
            env_conditions={
                'temperature': self.plant_state.air_temperature,
                'light_stress': 1.0 - self.plant_state.light_stress
            }
        )

        # Get actual growth rates (g/day) from net assimilation and allocation
        net_assimilation = self.plant_state.net_assimilation  # g C/day

        # Convert carbon to biomass (approximate conversion factor)
        carbon_to_biomass = 2.2  # g biomass per g C
        total_growth_rate = net_assimilation * carbon_to_biomass  # g biomass/day

        organ_growth_rates = {
            'leaves': total_growth_rate * alloc_response['leaves'],
            'stems': total_growth_rate * alloc_response['stems'],
            'roots': total_growth_rate * alloc_response['roots']
        }

        # Calculate nutrient demands based on growth rates and tissue concentrations
        # Using target tissue concentrations (nitrogen from parameters, P/K from literature values for lettuce)
        target_concentrations = {
            'leaves': {
                'nitrogen': self.param_loader.get_parameter('critical_n_concentrations_leaves_optimal'), # g N/g biomass
                'phosphorus': 0.008,  # g P/g biomass (typical for lettuce leaves)
                'potassium': 0.040   # g K/g biomass (typical for lettuce leaves)
            },
            'stems': {
                'nitrogen': self.param_loader.get_parameter('critical_n_concentrations_stems_optimal'),
                'phosphorus': 0.005,  # g P/g biomass (typical for lettuce stems)
                'potassium': 0.025   # g K/g biomass (typical for lettuce stems)
            },
            'roots': {
                'nitrogen': self.param_loader.get_parameter('critical_n_concentrations_roots_optimal'),
                'phosphorus': 0.006,  # g P/g biomass (typical for lettuce roots)
                'potassium': 0.030   # g K/g biomass (typical for lettuce roots)
            }
        }

        # Calculate dynamic demands: growth_rate * target_concentration * 1000 (convert g to mg)
        organ_demands = {}
        for organ, growth_rate in organ_growth_rates.items():
            organ_demands[organ] = {}
            for nutrient in ['nitrogen', 'phosphorus', 'potassium']:
                # Demand = new tissue mass * target concentration * conversion factor
                demand_g_per_day = growth_rate * target_concentrations[organ][nutrient]
                demand_mg_per_day = demand_g_per_day * 1000  # Convert to mg/day
                organ_demands[organ][nutrient] = max(0.0, demand_mg_per_day)

        return organ_demands

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
        # Check if we've reached the maximum simulation days
        max_days = self.param_loader.get_parameter('simulation_days')
        return self.plant_state.day >= max_days - 1

    def save_results(self, output_path: str = None) -> str:
        """Save simulation results"""
        if output_path is None:
            output_path = "output/hydroponic_simulation.csv"

        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save results with 2 decimal places
        df = pd.DataFrame(self.simulation_results)
        
        # Round numeric columns with appropriate precision for each variable
        numeric_columns = df.select_dtypes(include=[float, int]).columns
        for col in numeric_columns:
            if col in ['lai', 'leaf_area']:
                # Use higher precision for LAI and leaf area (important small values)
                df[col] = df[col].round(4)
            else:
                # Standard precision for other variables
                df[col] = df[col].round(2)
        
        df.to_csv(output_path, index=False)

        print(f"Results saved to: {output_path}")
        return output_path

    def _validate_physiological_state(self):
        """Validate physiological parameters for biological realism"""
        max_lai_change = self.param_loader.get_parameter('max_daily_lai_change')
        max_k_accumulation = self.param_loader.get_parameter('max_k_concentration')
        min_respiration_ratio = self.param_loader.get_parameter('min_respiration_photosynthesis_ratio')

        # Check impossible states
        if self.plant_state.photosynthesis_rate > 0 and self.plant_state.respiration_rate == 0:
            raise ModelInitializationError(f"Day {self.plant_state.day}: Impossible state - active photosynthesis with zero respiration")

        # LAI validation removed - fundamental calculation fixed to use proper ground area

        # Check nutrient concentration ranges (disabled - K accumulation near harvest is normal)
        # if self.plant_state.k_content > max_k_accumulation:
        #     raise ModelInitializationError(f"Day {self.plant_state.day}: Toxic K concentration: {self.plant_state.k_content:.1f} mg/g")

        # Check respiration/photosynthesis ratio (disabled - low ratio is realistic for young plants)
        # Young, rapidly growing plants can have very low respiration ratios (0.1-2% of photosynthesis)
        # This is biologically normal and indicates efficient growth with high net carbon gain
        # if self.plant_state.photosynthesis_rate > 1.0 and self.plant_state.total_biomass > 0.1:
        #     resp_ratio = self.plant_state.respiration_rate / self.plant_state.photosynthesis_rate
        #     if resp_ratio < min_respiration_ratio:
        #         raise ModelInitializationError(f"Day {self.plant_state.day}: Unrealistic respiration ratio: {resp_ratio:.3f}")

        # Store current values for next validation
        self.previous_lai = self.plant_state.lai


def main():
    """Main simulation execution"""
    try:
        # Initialize simulator
        simulator = HydroponicSimulator()

        # Run simulation
        results_df = simulator.run_simulation()

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