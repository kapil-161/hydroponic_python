from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

@dataclass
class NutrientParameters:
    ec_factor_n_no3: float
    ec_factor_n_nh4: float
    ec_factor_p_po4: float
    ec_factor_k: float
    ec_factor_ca: float
    ec_factor_mg: float
    ec_factor_s_so4: float
    ec_factor_fe: float
    ec_factor_mn: float
    ec_factor_zn: float
    ec_factor_cu: float
    ec_factor_b: float
    ec_factor_mo: float
    minimum_volume_fraction: float
    xylem_transport_capacity: float
    phloem_transport_capacity: float
    temperature_q10: float
    transpiration_coupling: float
    ec_uptake_high_threshold: float
    ec_uptake_low_threshold: float
    ec_uptake_modifier_n_high: float
    ec_uptake_modifier_p_high: float
    ec_uptake_modifier_k_high: float
    ec_uptake_modifier_ca_high: float
    ec_uptake_modifier_n_low: float
    ec_uptake_modifier_p_low: float
    ec_uptake_modifier_fe_low: float
    kinetics_n_no3_vmax: float
    kinetics_n_no3_km: float
    kinetics_n_no3_min_conc: float
    kinetics_n_nh4_vmax: float
    kinetics_n_nh4_km: float
    kinetics_n_nh4_min_conc: float
    kinetics_p_po4_vmax: float
    kinetics_p_po4_km: float
    kinetics_p_po4_min_conc: float
    kinetics_k_vmax: float
    kinetics_k_km: float
    kinetics_k_min_conc: float
    kinetics_ca_vmax: float
    kinetics_ca_km: float
    kinetics_ca_min_conc: float
    kinetics_mg_vmax: float
    kinetics_mg_km: float
    kinetics_mg_min_conc: float
    kinetics_s_so4_vmax: float
    kinetics_s_so4_km: float
    kinetics_s_so4_min_conc: float
    kinetics_fe_vmax: float
    kinetics_fe_km: float
    kinetics_fe_min_conc: float
    kinetics_mn_vmax: float
    kinetics_mn_km: float
    kinetics_mn_min_conc: float
    kinetics_zn_vmax: float
    kinetics_zn_km: float
    kinetics_zn_min_conc: float
    kinetics_cu_vmax: float
    kinetics_cu_km: float
    kinetics_cu_min_conc: float
    kinetics_b_vmax: float
    kinetics_b_km: float
    kinetics_b_min_conc: float
    kinetics_mo_vmax: float
    kinetics_mo_km: float
    kinetics_mo_min_conc: float
    mobility_classifications: Dict[str, Dict[str, Any]]
    xylem_transport_rates: Dict[str, float]
    phloem_transport_rates: Dict[str, float]
    buffering_capacities: Dict[str, Dict[str, float]]
    storage_pool_sizes: Dict[str, Dict[str, float]]
    redistribution_thresholds: Dict[str, float]
    stress_redistribution_rates: Dict[str, float]
    sink_strength_coefficients: Dict[str, Dict[str, float]]
    cache_timeout: float

    # Hardcoded value replacements (from CSV)
    ec_stress_min_threshold: float
    ec_boost_max_n: float
    ec_boost_max_p: float
    ec_boost_max_k: float
    ec_boost_max_fe: float
    temperature_factor_base: float
    ph_factor_base: float
    reference_daily_growth_rate: float
    rhizosphere_thickness_cm: float
    minimum_root_zone_volume_L: float
    transport_pool_fraction_multiplier: float
    deficiency_mobility_very_high_factor: float
    deficiency_mobility_high_factor: float
    deficiency_mobility_low_factor: float
    deficiency_mobility_very_low_factor: float
    base_supply_storage_pool_fraction: float
    base_supply_buffer_pool_fraction: float
    stress_redistribution_threshold: float
    max_transportable_nutrient_fraction: float
    transport_reference_temperature: float
    bidirectional_xylem_fraction: float
    bidirectional_phloem_fraction: float
    metabolic_pool_export_limit_fraction: float
    transport_pool_max_fraction: float
    transport_pool_target_fraction: float
    excess_to_metabolic_fraction: float
    excess_to_storage_fraction: float
    excess_to_buffer_fraction: float
    highly_mobile_base_efficiency: float
    moderately_mobile_base_efficiency: float
    poorly_mobile_base_efficiency: float
    immobile_base_efficiency: float
    bidirectional_transport_factor: float
    complex_transport_factor: float
    xylem_only_transport_factor: float
    phloem_only_transport_factor: float
    transport_limitation_threshold: float

    # Ion properties for scientific EC calculation (CSV-driven)
    ion_molar_mass: Dict[str, float]
    ion_lambda0_25C: Dict[str, float]
    ion_valence: Dict[str, float]
    temperature_coefficient_alpha: float

    # Tissue composition parameters - NO HARDCODED VALUES (Rules.md)
    tissue_nitrogen_content_fraction: float
    tissue_phosphorus_content_fraction: float
    tissue_potassium_content_fraction: float

    # Organ allocation fractions - NO HARDCODED VALUES (Rules.md)
    organ_allocation_no3_roots: float
    organ_allocation_nh4_roots: float
    organ_allocation_po4_roots: float
    organ_allocation_k_roots: float
    organ_allocation_no3_leaves: float
    organ_allocation_nh4_leaves: float
    organ_allocation_po4_leaves: float
    organ_allocation_k_leaves: float
    organ_allocation_no3_stems: float
    organ_allocation_nh4_stems: float
    organ_allocation_po4_stems: float
    organ_allocation_k_stems: float

    # Carbon assimilate allocation fractions - NO HARDCODED VALUES (Rules.md)
    carbon_assimilate_allocation_roots: float
    carbon_assimilate_allocation_leaves: float
    carbon_assimilate_allocation_stems: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'NutrientParameters':
        required_params = [
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
            'kinetics_ca_min_conc', 'kinetics_mg_vmax', 'kinetics_mg_km', 'kinetics_mg_min_conc',
            'kinetics_s_so4_vmax', 'kinetics_s_so4_km', 'kinetics_s_so4_min_conc', 'kinetics_fe_vmax', 'kinetics_fe_km', 'kinetics_fe_min_conc',
            'kinetics_mn_vmax', 'kinetics_mn_km', 'kinetics_mn_min_conc', 'kinetics_zn_vmax', 'kinetics_zn_km', 'kinetics_zn_min_conc',
            'kinetics_cu_vmax', 'kinetics_cu_km', 'kinetics_cu_min_conc', 'kinetics_b_vmax', 'kinetics_b_km', 'kinetics_b_min_conc',
            'kinetics_mo_vmax', 'kinetics_mo_km', 'kinetics_mo_min_conc',
            # Hardcoded value replacements
            'ec_stress_min_threshold', 'ec_boost_max_n', 'ec_boost_max_p', 'ec_boost_max_k', 'ec_boost_max_fe',
            'temperature_factor_base', 'ph_factor_base', 'reference_daily_growth_rate',
            'rhizosphere_thickness_cm', 'minimum_root_zone_volume_L', 'transport_pool_fraction_multiplier',
            'deficiency_mobility_very_high_factor', 'deficiency_mobility_high_factor',
            'deficiency_mobility_low_factor', 'deficiency_mobility_very_low_factor',
            'base_supply_storage_pool_fraction', 'base_supply_buffer_pool_fraction',
            'stress_redistribution_threshold', 'max_transportable_nutrient_fraction',
            'transport_reference_temperature', 'bidirectional_xylem_fraction', 'bidirectional_phloem_fraction',
            'metabolic_pool_export_limit_fraction', 'transport_pool_max_fraction', 'transport_pool_target_fraction',
            'excess_to_metabolic_fraction', 'excess_to_storage_fraction', 'excess_to_buffer_fraction',
            'highly_mobile_base_efficiency', 'moderately_mobile_base_efficiency',
            'poorly_mobile_base_efficiency', 'immobile_base_efficiency',
            'bidirectional_transport_factor', 'complex_transport_factor',
            'xylem_only_transport_factor', 'phloem_only_transport_factor', 'transport_limitation_threshold',
            # Tissue composition and organ allocation - NO HARDCODED VALUES (Rules.md)
            'tissue_nitrogen_content_fraction', 'tissue_phosphorus_content_fraction', 'tissue_potassium_content_fraction',
            'organ_allocation_no3_roots', 'organ_allocation_nh4_roots', 'organ_allocation_po4_roots', 'organ_allocation_k_roots',
            'organ_allocation_no3_leaves', 'organ_allocation_nh4_leaves', 'organ_allocation_po4_leaves', 'organ_allocation_k_leaves',
            'organ_allocation_no3_stems', 'organ_allocation_nh4_stems', 'organ_allocation_po4_stems', 'organ_allocation_k_stems',
            # Carbon assimilate allocation - NO HARDCODED VALUES (Rules.md)
            'carbon_assimilate_allocation_roots', 'carbon_assimilate_allocation_leaves', 'carbon_assimilate_allocation_stems'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Required parameter '{param}' not found in configuration")

        nutrients = ["N-NO3", "N-NH4", "P-PO4", "K", "Ca", "Mg", "S-SO4",
                     "Fe", "Mn", "Zn", "Cu", "B", "Mo"]
        mobility_class = {}
        xylem_rates = {}
        phloem_rates = {}
        buffering_cap = {"leaves": {}, "stems": {}, "roots": {}}
        storage_sizes = {"leaves": {}, "stems": {}, "roots": {}}
        redist_thresh = {}
        stress_redist = {}
        sink_coeffs = {"vegetative": {}, "reproductive": {}, "senescence": {}}

        for nutrient in nutrients:
            mobility_key = f"mobility_classifications_{nutrient}_mobility"
            transport_key = f"mobility_classifications_{nutrient}_transport"
            remob_key = f"mobility_classifications_{nutrient}_remobilization_efficiency"
            def_key = f"mobility_classifications_{nutrient}_deficiency_mobility"
            retrans_key = f"mobility_classifications_{nutrient}_retranslocation_rate"
            if not all(key in config for key in [mobility_key, transport_key, remob_key, def_key, retrans_key]):
                raise KeyError(f"Missing mobility parameters for {nutrient}")
            mobility_class[nutrient] = {
                "mobility": config[mobility_key],
                "transport": config[transport_key],
                "remobilization_efficiency": float(config[remob_key]),
                "deficiency_mobility": config[def_key],
                "retranslocation_rate": float(config[retrans_key]),
            }
            xylem_key = f"xylem_transport_rates_{nutrient}"
            phloem_key = f"phloem_transport_rates_{nutrient}"
            if xylem_key not in config or phloem_key not in config:
                raise KeyError(f"Missing transport rates for {nutrient}")
            xylem_rates[nutrient] = float(config[xylem_key])
            phloem_rates[nutrient] = float(config[phloem_key])

        organs = ["leaves", "stems", "roots"]
        for organ in organs:
            for nutrient in ["N-NO3", "N-NH4", "P-PO4", "K"]:
                buffer_key = f"buffering_capacities_{organ}_{nutrient}"
                storage_key = f"storage_pool_sizes_{organ}_{nutrient}"
                if buffer_key not in config or storage_key not in config:
                    raise KeyError(f"Missing buffering/storage parameters for {organ} {nutrient}")
                buffering_cap[organ][nutrient] = float(config[buffer_key])
                storage_sizes[organ][nutrient] = float(config[storage_key])

        for nutrient in ["N-NO3", "N-NH4", "P-PO4", "K", "Ca", "Mg", "S-SO4"]:
            key = f"redistribution_thresholds_{nutrient}"
            if key not in config:
                raise KeyError(f"Missing redistribution threshold for {nutrient}")
            redist_thresh[nutrient] = float(config[key])
            key = f"stress_redistribution_rates_{nutrient}"
            if key not in config:
                raise KeyError(f"Missing stress redistribution rate for {nutrient}")
            stress_redist[nutrient] = float(config[key])

        stages = ["vegetative", "reproductive", "senescence"]
        for stage in stages:
            for organ in ["leaves", "stems", "roots"]:
                key = f"sink_strength_coefficients_{stage}_{organ}"
                if key not in config:
                    raise KeyError(f"Missing sink strength coefficient for {stage} {organ}")
                sink_coeffs[stage][organ] = float(config[key])
            if stage == "reproductive":
                key = f"sink_strength_coefficients_{stage}_reproductive"
                if key not in config:
                    raise KeyError(f"Missing sink strength coefficient for {stage} reproductive")
                sink_coeffs[stage]["reproductive"] = float(config[key])

        # Ion properties required for ion-based EC
        ion_molar_mass: Dict[str, float] = {}
        ion_lambda0_25C: Dict[str, float] = {}
        ion_valence: Dict[str, float] = {}
        for nutrient in nutrients:
            mm_key = f"molar_mass_{nutrient}"
            lam_key = f"lambda0_25C_{nutrient}"
            val_key = f"valence_{nutrient}"
            if mm_key not in config or lam_key not in config or val_key not in config:
                raise KeyError(f"Missing ion property for {nutrient}: require {mm_key}, {lam_key}, {val_key}")
            ion_molar_mass[nutrient] = float(config[mm_key])
            ion_lambda0_25C[nutrient] = float(config[lam_key])
            ion_valence[nutrient] = float(config[val_key])

        if 'temperature_coefficient_alpha' not in config:
            raise KeyError("Missing temperature_coefficient_alpha in nutrient parameters")

        return cls(
            ec_factor_n_no3=float(config['ec_factor_n_no3']),
            ec_factor_n_nh4=float(config['ec_factor_n_nh4']),
            ec_factor_p_po4=float(config['ec_factor_p_po4']),
            ec_factor_k=float(config['ec_factor_k']),
            ec_factor_ca=float(config['ec_factor_ca']),
            ec_factor_mg=float(config['ec_factor_mg']),
            ec_factor_s_so4=float(config['ec_factor_s_so4']),
            ec_factor_fe=float(config['ec_factor_fe']),
            ec_factor_mn=float(config['ec_factor_mn']),
            ec_factor_zn=float(config['ec_factor_zn']),
            ec_factor_cu=float(config['ec_factor_cu']),
            ec_factor_b=float(config['ec_factor_b']),
            ec_factor_mo=float(config['ec_factor_mo']),
            minimum_volume_fraction=float(config['minimum_volume_fraction']),
            xylem_transport_capacity=float(config['xylem_transport_capacity']),
            phloem_transport_capacity=float(config['phloem_transport_capacity']),
            temperature_q10=float(config['temperature_q10']),
            transpiration_coupling=float(config['transpiration_coupling']),
            ec_uptake_high_threshold=float(config['ec_uptake_high_threshold']),
            ec_uptake_low_threshold=float(config['ec_uptake_low_threshold']),
            ec_uptake_modifier_n_high=float(config['ec_uptake_modifier_n_high']),
            ec_uptake_modifier_p_high=float(config['ec_uptake_modifier_p_high']),
            ec_uptake_modifier_k_high=float(config['ec_uptake_modifier_k_high']),
            ec_uptake_modifier_ca_high=float(config['ec_uptake_modifier_ca_high']),
            ec_uptake_modifier_n_low=float(config['ec_uptake_modifier_n_low']),
            ec_uptake_modifier_p_low=float(config['ec_uptake_modifier_p_low']),
            ec_uptake_modifier_fe_low=float(config['ec_uptake_modifier_fe_low']),
            kinetics_n_no3_vmax=float(config['kinetics_n_no3_vmax']),
            kinetics_n_no3_km=float(config['kinetics_n_no3_km']),
            kinetics_n_no3_min_conc=float(config['kinetics_n_no3_min_conc']),
            kinetics_n_nh4_vmax=float(config['kinetics_n_nh4_vmax']),
            kinetics_n_nh4_km=float(config['kinetics_n_nh4_km']),
            kinetics_n_nh4_min_conc=float(config['kinetics_n_nh4_min_conc']),
            kinetics_p_po4_vmax=float(config['kinetics_p_po4_vmax']),
            kinetics_p_po4_km=float(config['kinetics_p_po4_km']),
            kinetics_p_po4_min_conc=float(config['kinetics_p_po4_min_conc']),
            kinetics_k_vmax=float(config['kinetics_k_vmax']),
            kinetics_k_km=float(config['kinetics_k_km']),
            kinetics_k_min_conc=float(config['kinetics_k_min_conc']),
            kinetics_ca_vmax=float(config['kinetics_ca_vmax']),
            kinetics_ca_km=float(config['kinetics_ca_km']),
            kinetics_ca_min_conc=float(config['kinetics_ca_min_conc']),
            kinetics_mg_vmax=float(config['kinetics_mg_vmax']),
            kinetics_mg_km=float(config['kinetics_mg_km']),
            kinetics_mg_min_conc=float(config['kinetics_mg_min_conc']),
            kinetics_s_so4_vmax=float(config['kinetics_s_so4_vmax']),
            kinetics_s_so4_km=float(config['kinetics_s_so4_km']),
            kinetics_s_so4_min_conc=float(config['kinetics_s_so4_min_conc']),
            kinetics_fe_vmax=float(config['kinetics_fe_vmax']),
            kinetics_fe_km=float(config['kinetics_fe_km']),
            kinetics_fe_min_conc=float(config['kinetics_fe_min_conc']),
            kinetics_mn_vmax=float(config['kinetics_mn_vmax']),
            kinetics_mn_km=float(config['kinetics_mn_km']),
            kinetics_mn_min_conc=float(config['kinetics_mn_min_conc']),
            kinetics_zn_vmax=float(config['kinetics_zn_vmax']),
            kinetics_zn_km=float(config['kinetics_zn_km']),
            kinetics_zn_min_conc=float(config['kinetics_zn_min_conc']),
            kinetics_cu_vmax=float(config['kinetics_cu_vmax']),
            kinetics_cu_km=float(config['kinetics_cu_km']),
            kinetics_cu_min_conc=float(config['kinetics_cu_min_conc']),
            kinetics_b_vmax=float(config['kinetics_b_vmax']),
            kinetics_b_km=float(config['kinetics_b_km']),
            kinetics_b_min_conc=float(config['kinetics_b_min_conc']),
            kinetics_mo_vmax=float(config['kinetics_mo_vmax']),
            kinetics_mo_km=float(config['kinetics_mo_km']),
            kinetics_mo_min_conc=float(config['kinetics_mo_min_conc']),
            mobility_classifications=mobility_class,
            xylem_transport_rates=xylem_rates,
            phloem_transport_rates=phloem_rates,
            buffering_capacities=buffering_cap,
            storage_pool_sizes=storage_sizes,
            redistribution_thresholds=redist_thresh,
            stress_redistribution_rates=stress_redist,
            sink_strength_coefficients=sink_coeffs,
            cache_timeout=float(config['cache_timeout']),
            # Hardcoded value replacements
            ec_stress_min_threshold=float(config['ec_stress_min_threshold']),
            ec_boost_max_n=float(config['ec_boost_max_n']),
            ec_boost_max_p=float(config['ec_boost_max_p']),
            ec_boost_max_k=float(config['ec_boost_max_k']),
            ec_boost_max_fe=float(config['ec_boost_max_fe']),
            temperature_factor_base=float(config['temperature_factor_base']),
            ph_factor_base=float(config['ph_factor_base']),
            reference_daily_growth_rate=float(config['reference_daily_growth_rate']),
            rhizosphere_thickness_cm=float(config['rhizosphere_thickness_cm']),
            minimum_root_zone_volume_L=float(config['minimum_root_zone_volume_L']),
            transport_pool_fraction_multiplier=float(config['transport_pool_fraction_multiplier']),
            deficiency_mobility_very_high_factor=float(config['deficiency_mobility_very_high_factor']),
            deficiency_mobility_high_factor=float(config['deficiency_mobility_high_factor']),
            deficiency_mobility_low_factor=float(config['deficiency_mobility_low_factor']),
            deficiency_mobility_very_low_factor=float(config['deficiency_mobility_very_low_factor']),
            base_supply_storage_pool_fraction=float(config['base_supply_storage_pool_fraction']),
            base_supply_buffer_pool_fraction=float(config['base_supply_buffer_pool_fraction']),
            stress_redistribution_threshold=float(config['stress_redistribution_threshold']),
            max_transportable_nutrient_fraction=float(config['max_transportable_nutrient_fraction']),
            transport_reference_temperature=float(config['transport_reference_temperature']),
            bidirectional_xylem_fraction=float(config['bidirectional_xylem_fraction']),
            bidirectional_phloem_fraction=float(config['bidirectional_phloem_fraction']),
            metabolic_pool_export_limit_fraction=float(config['metabolic_pool_export_limit_fraction']),
            transport_pool_max_fraction=float(config['transport_pool_max_fraction']),
            transport_pool_target_fraction=float(config['transport_pool_target_fraction']),
            excess_to_metabolic_fraction=float(config['excess_to_metabolic_fraction']),
            excess_to_storage_fraction=float(config['excess_to_storage_fraction']),
            excess_to_buffer_fraction=float(config['excess_to_buffer_fraction']),
            highly_mobile_base_efficiency=float(config['highly_mobile_base_efficiency']),
            moderately_mobile_base_efficiency=float(config['moderately_mobile_base_efficiency']),
            poorly_mobile_base_efficiency=float(config['poorly_mobile_base_efficiency']),
            immobile_base_efficiency=float(config['immobile_base_efficiency']),
            bidirectional_transport_factor=float(config['bidirectional_transport_factor']),
            complex_transport_factor=float(config['complex_transport_factor']),
            xylem_only_transport_factor=float(config['xylem_only_transport_factor']),
            phloem_only_transport_factor=float(config['phloem_only_transport_factor']),
            transport_limitation_threshold=float(config['transport_limitation_threshold']),
            # Ion properties for scientific EC
            ion_molar_mass=ion_molar_mass,
            ion_lambda0_25C=ion_lambda0_25C,
            ion_valence=ion_valence,
            temperature_coefficient_alpha=float(config['temperature_coefficient_alpha']),
            # Tissue composition and organ allocation - NO HARDCODED VALUES (Rules.md)
            tissue_nitrogen_content_fraction=float(config['tissue_nitrogen_content_fraction']),
            tissue_phosphorus_content_fraction=float(config['tissue_phosphorus_content_fraction']),
            tissue_potassium_content_fraction=float(config['tissue_potassium_content_fraction']),
            organ_allocation_no3_roots=float(config['organ_allocation_no3_roots']),
            organ_allocation_nh4_roots=float(config['organ_allocation_nh4_roots']),
            organ_allocation_po4_roots=float(config['organ_allocation_po4_roots']),
            organ_allocation_k_roots=float(config['organ_allocation_k_roots']),
            organ_allocation_no3_leaves=float(config['organ_allocation_no3_leaves']),
            organ_allocation_nh4_leaves=float(config['organ_allocation_nh4_leaves']),
            organ_allocation_po4_leaves=float(config['organ_allocation_po4_leaves']),
            organ_allocation_k_leaves=float(config['organ_allocation_k_leaves']),
            organ_allocation_no3_stems=float(config['organ_allocation_no3_stems']),
            organ_allocation_nh4_stems=float(config['organ_allocation_nh4_stems']),
            organ_allocation_po4_stems=float(config['organ_allocation_po4_stems']),
            organ_allocation_k_stems=float(config['organ_allocation_k_stems']),
            # Carbon assimilate allocation - NO HARDCODED VALUES (Rules.md)
            carbon_assimilate_allocation_roots=float(config['carbon_assimilate_allocation_roots']),
            carbon_assimilate_allocation_leaves=float(config['carbon_assimilate_allocation_leaves']),
            carbon_assimilate_allocation_stems=float(config['carbon_assimilate_allocation_stems'])
        )

class NutrientMobility(Enum):
    HIGHLY_MOBILE = "highly_mobile"
    MODERATELY_MOBILE = "moderately_mobile"
    POORLY_MOBILE = "poorly_mobile"
    IMMOBILE = "immobile"

class TransportMechanism(Enum):
    XYLEM_ONLY = "xylem_only"
    PHLOEM_ONLY = "phloem_only"
    BIDIRECTIONAL = "bidirectional"
    COMPLEX = "complex"

@dataclass
class NutrientTransportFlux:
    source_organ: str
    sink_organ: str
    nutrient: str
    transport_mechanism: str
    flux_rate: float
    driving_force: str
    efficiency: float

@dataclass
class OrganNutrientPools:
    organ_name: str
    nutrient_name: str
    metabolic_pool: float = 0.0
    storage_pool: float = 0.0
    transport_pool: float = 0.0
    buffer_pool: float = 0.0
    total_content: float = 0.0
    concentration: float = 0.0
    mobility_status: str = "optimal"
    available_for_export: float = 0.0
    demand_for_import: float = 0.0
    buffering_capacity: float = 0.0

    def __post_init__(self):
        self.total_content = self.metabolic_pool + self.storage_pool + self.transport_pool + self.buffer_pool

@dataclass
class NutrientMobilityResponse:
    transport_fluxes: List[NutrientTransportFlux]
    organ_pools: Dict[str, Dict[str, OrganNutrientPools]]
    total_redistribution: Dict[str, float]
    transport_limitations: List[str]
    sink_demands: Dict[str, Dict[str, float]]
    source_supplies: Dict[str, Dict[str, float]]
    mobility_efficiency: Dict[str, float]

class NutrientModel:
    def __init__(self, parameters: NutrientParameters):
        self.params = parameters
        self.ec_factors = self._get_ec_factors()
        self.kinetics = self._get_uptake_kinetics()
        self.organ_pools: Dict[str, Dict[str, OrganNutrientPools]] = {}
        self.transport_history: List[Dict[str, Any]] = []
        self.cumulative_redistribution: Dict[str, float] = {}
        # Ion property caches for EC calculation
        self.ion_molar_mass = self.params.ion_molar_mass
        self.ion_lambda0_25C = self.params.ion_lambda0_25C
        self.ion_valence = self.params.ion_valence
        self.temp_alpha = self.params.temperature_coefficient_alpha
    
    def initialize(self):
        """Initialize the nutrient model"""
        pass

    def _get_ec_factors(self) -> Dict[str, float]:
        return {
            "N-NO3": self.params.ec_factor_n_no3,
            "N-NH4": self.params.ec_factor_n_nh4,
            "P-PO4": self.params.ec_factor_p_po4,
            "K": self.params.ec_factor_k,
            "Ca": self.params.ec_factor_ca,
            "Mg": self.params.ec_factor_mg,
            "S-SO4": self.params.ec_factor_s_so4,
            "Fe": self.params.ec_factor_fe,
            "Mn": self.params.ec_factor_mn,
            "Zn": self.params.ec_factor_zn,
            "Cu": self.params.ec_factor_cu,
            "B": self.params.ec_factor_b,
            "Mo": self.params.ec_factor_mo
        }

    def _get_uptake_kinetics(self) -> Dict[str, Dict[str, float]]:
        return {
            'N-NO3': {'vmax': self.params.kinetics_n_no3_vmax, 'km': self.params.kinetics_n_no3_km, 'min_conc': self.params.kinetics_n_no3_min_conc},
            'N-NH4': {'vmax': self.params.kinetics_n_nh4_vmax, 'km': self.params.kinetics_n_nh4_km, 'min_conc': self.params.kinetics_n_nh4_min_conc},
            'P-PO4': {'vmax': self.params.kinetics_p_po4_vmax, 'km': self.params.kinetics_p_po4_km, 'min_conc': self.params.kinetics_p_po4_min_conc},
            'K': {'vmax': self.params.kinetics_k_vmax, 'km': self.params.kinetics_k_km, 'min_conc': self.params.kinetics_k_min_conc},
            'Ca': {'vmax': self.params.kinetics_ca_vmax, 'km': self.params.kinetics_ca_km, 'min_conc': self.params.kinetics_ca_min_conc},
            'Mg': {'vmax': self.params.kinetics_mg_vmax, 'km': self.params.kinetics_mg_km, 'min_conc': self.params.kinetics_mg_min_conc},
            'S-SO4': {'vmax': self.params.kinetics_s_so4_vmax, 'km': self.params.kinetics_s_so4_km, 'min_conc': self.params.kinetics_s_so4_min_conc},
            'Fe': {'vmax': self.params.kinetics_fe_vmax, 'km': self.params.kinetics_fe_km, 'min_conc': self.params.kinetics_fe_min_conc},
            'Mn': {'vmax': self.params.kinetics_mn_vmax, 'km': self.params.kinetics_mn_km, 'min_conc': self.params.kinetics_mn_min_conc},
            'Zn': {'vmax': self.params.kinetics_zn_vmax, 'km': self.params.kinetics_zn_km, 'min_conc': self.params.kinetics_zn_min_conc},
            'Cu': {'vmax': self.params.kinetics_cu_vmax, 'km': self.params.kinetics_cu_km, 'min_conc': self.params.kinetics_cu_min_conc},
            'B': {'vmax': self.params.kinetics_b_vmax, 'km': self.params.kinetics_b_km, 'min_conc': self.params.kinetics_b_min_conc},
            'Mo': {'vmax': self.params.kinetics_mo_vmax, 'km': self.params.kinetics_mo_km, 'min_conc': self.params.kinetics_mo_min_conc}
        }

    def calculate_nutrient_dynamics(self, concentrations: Dict[str, float], plant_status: Dict[str, Any],
                                  env_conditions: Dict[str, Any], organ_demands: Dict[str, Dict[str, float]],
                                  water_fluxes: Dict[str, float], assimilate_fluxes: Dict[str, float]) -> Dict[str, Any]:
        required_status = ['root_surface_area', 'tank_volume_L', 'plant_count', 'daily_growth_rate', 'growth_stage', 'senescence_rates', 'stress_factors', 'organ_nutrient_status']
        required_env = ['temperature', 'ph', 'optimal_ec']
        for key in required_status:
            if key not in plant_status:
                raise KeyError(f"Missing plant_status key: {key}")
        for key in required_env:
            if key not in env_conditions:
                raise KeyError(f"Missing env_conditions key: {key}")

        ec_value = self._calculate_ec_from_concentrations(concentrations, env_conditions['temperature'])
        uptake_modifiers = self._calculate_uptake_modifiers(ec_value, env_conditions)
        uptake_rates = self._calculate_uptake_rates(concentrations, plant_status, env_conditions, uptake_modifiers)
        updated_concentrations = self._update_concentrations(concentrations, uptake_rates, plant_status)
        mobility_response = self._calculate_nutrient_mobility(organ_demands, plant_status, env_conditions, water_fluxes, assimilate_fluxes)
        return {
            'calculated_ec': ec_value,
            'uptake_rates_mg_per_plant_per_day': uptake_rates,
            'updated_concentrations': updated_concentrations,
            'transport_fluxes': mobility_response.transport_fluxes,
            'organ_pools': mobility_response.organ_pools,
            'mobility_efficiency': mobility_response.mobility_efficiency,
            'transport_limitations': mobility_response.transport_limitations
        }

    def _calculate_ec_from_concentrations(self, concentrations: Dict[str, float], temperature: float) -> float:
        """Calculate EC using ion chemistry (Kohlrausch's law) with CSV-driven properties.
        Returns EC in dS/m.
        """
        kappa_S_per_cm = 0.0
        for ion, conc_mg_per_L in concentrations.items():
            if ion not in self.ion_molar_mass or ion not in self.ion_lambda0_25C:
                raise KeyError(f"Missing ion properties for {ion} in parameters")
            molar_mass = self.ion_molar_mass[ion]  # g/mol
            lambda0 = self.ion_lambda0_25C[ion]    # S·cm^2/mol at 25°C
            # Convert mg/L -> mol/L, then to mol/cm^3
            conc_mol_per_L = (conc_mg_per_L / 1000.0) / molar_mass
            conc_mol_per_cm3 = conc_mol_per_L / 1000.0
            # Conductivity contribution in S/cm
            kappa_i = lambda0 * conc_mol_per_cm3
            kappa_S_per_cm += kappa_i
        # Temperature correction relative to 25°C
        delta_t = temperature - 25.0
        kappa_S_per_cm *= (1.0 + self.temp_alpha * delta_t)
        # Convert S/cm to dS/m (1 S/cm = 1000 dS/m)
        ec_dS_per_m = kappa_S_per_cm * 1000.0
        return ec_dS_per_m

    def _calculate_uptake_modifiers(self, current_ec: float, env_conditions: Dict[str, Any]) -> Dict[str, float]:
        ec_ratio = current_ec / env_conditions['optimal_ec']
        modifiers = {}
        if ec_ratio > self.params.ec_uptake_high_threshold:
            modifiers = {
                "N-NO3": max(self.params.ec_stress_min_threshold, 1.0 - (ec_ratio - 1.0) * self.params.ec_uptake_modifier_n_high),
                "P-PO4": max(self.params.ec_stress_min_threshold, 1.0 - (ec_ratio - 1.0) * self.params.ec_uptake_modifier_p_high),
                "K": max(self.params.ec_stress_min_threshold, 1.0 - (ec_ratio - 1.0) * self.params.ec_uptake_modifier_k_high),
                "Ca": max(self.params.ec_stress_min_threshold, 1.0 - (ec_ratio - 1.0) * self.params.ec_uptake_modifier_ca_high),
                "Mg": max(self.params.ec_stress_min_threshold, 1.0 - (ec_ratio - 1.0) * self.params.ec_uptake_modifier_ca_high),
                "Fe": max(self.params.ec_stress_min_threshold, 1.0 - (ec_ratio - 1.0) * self.params.ec_uptake_modifier_p_high),
            }
        elif ec_ratio < self.params.ec_uptake_low_threshold:
            modifiers = {
                "N-NO3": min(self.params.ec_boost_max_n, 1.0 + (self.params.ec_uptake_low_threshold - ec_ratio) * self.params.ec_uptake_modifier_n_low),
                "P-PO4": min(self.params.ec_boost_max_p, 1.0 + (self.params.ec_uptake_low_threshold - ec_ratio) * self.params.ec_uptake_modifier_p_low),
                "K": min(self.params.ec_boost_max_k, 1.0 + (self.params.ec_uptake_low_threshold - ec_ratio) * self.params.ec_uptake_modifier_p_low),
                "Ca": self.params.ph_factor_base,
                "Mg": self.params.ph_factor_base,
                "Fe": min(self.params.ec_boost_max_fe, 1.0 + (self.params.ec_uptake_low_threshold - ec_ratio) * self.params.ec_uptake_modifier_fe_low),
            }
        else:
            modifiers = {nutrient: 1.0 for nutrient in self.ec_factors.keys()}
        for nutrient in self.ec_factors.keys():
            if nutrient not in modifiers:
                modifiers[nutrient] = 1.0
        return modifiers

    def _calculate_uptake_rates(self, concentrations: Dict[str, float], plant_status: Dict[str, Any],
                              env_conditions: Dict[str, Any], uptake_modifiers: Dict[str, float]) -> Dict[str, float]:
        uptake_rates = {}
        temperature = env_conditions['temperature']
        ph = env_conditions['ph']
        root_surface_area = plant_status['root_surface_area']
        daily_growth_rate = plant_status['daily_growth_rate']

        temp_factor = self.params.temperature_q10 ** ((temperature - 22.0) / 10.0)
        temp_factor = max(0.1, min(3.0, temp_factor))
        ph_factor = max(0.2, 1.0 - abs(ph - 6.0) * 0.5)
        demand_factor = max(0.5, min(2.0, daily_growth_rate / 1.0))

        for nutrient, concentration in concentrations.items():
            if nutrient in self.kinetics and concentration > self.kinetics[nutrient]['min_conc']:
                k = self.kinetics[nutrient]
                uptake_per_cm2 = (k['vmax'] * concentration) / (k['km'] + concentration)
                base_uptake = uptake_per_cm2 * root_surface_area
                env_adjusted_uptake = base_uptake * temp_factor * ph_factor * uptake_modifiers.get(nutrient, 1.0)
                uptake_rates[nutrient] = max(0.0, env_adjusted_uptake * demand_factor)
            else:
                uptake_rates[nutrient] = 0.0
        return uptake_rates

    def _update_concentrations(self, concentrations: Dict[str, float], uptake_rates: Dict[str, float],
                             plant_status: Dict[str, Any]) -> Dict[str, float]:
        updated = {}
        plant_count = plant_status['plant_count']
        tank_volume_L = plant_status['tank_volume_L']

        # IMPORTANT: uptake_rates are in mg/plant/DAY but simulation runs HOURLY
        # Convert daily uptake to hourly uptake
        hourly_conversion_factor = 1.0 / 24.0

        for nutrient, initial_conc in concentrations.items():
            if nutrient in uptake_rates:
                # Convert daily uptake rate to hourly
                daily_uptake_per_plant = uptake_rates[nutrient]  # mg/plant/day
                hourly_uptake_per_plant = daily_uptake_per_plant * hourly_conversion_factor  # mg/plant/hour

                # Calculate total hourly uptake for all plants
                total_hourly_uptake = hourly_uptake_per_plant * plant_count  # mg/hour

                # Calculate concentration change in the tank
                # Concentration change = uptake / tank volume
                concentration_change = total_hourly_uptake / tank_volume_L  # mg/L per hour

                # Update concentration
                updated[nutrient] = max(0.0, initial_conc - concentration_change)
            else:
                updated[nutrient] = initial_conc
        return updated

    def initialize_organ_pools(self, organ_name: str, nutrient_contents: Dict[str, float], dry_mass: float):
        if dry_mass <= 0:
            raise ValueError("Dry mass must be positive")
        if organ_name not in self.organ_pools:
            self.organ_pools[organ_name] = {}
        for nutrient, total_content in nutrient_contents.items():
            if nutrient not in self.params.mobility_classifications:
                raise KeyError(f"Nutrient {nutrient} not found in mobility classifications")
            storage_fraction = self.params.storage_pool_sizes[organ_name][nutrient]
            buffer_fraction = self.params.buffering_capacities[organ_name][nutrient]
            storage_pool = total_content * storage_fraction
            buffer_pool = total_content * buffer_fraction
            transport_pool = total_content * (1.0 - storage_fraction - buffer_fraction) * 0.2
            metabolic_pool = total_content - storage_pool - buffer_pool - transport_pool
            pool = OrganNutrientPools(
                organ_name=organ_name,
                nutrient_name=nutrient,
                metabolic_pool=max(0.0, metabolic_pool),
                storage_pool=storage_pool,
                transport_pool=transport_pool,
                buffer_pool=buffer_pool,
                concentration=total_content / dry_mass,
                buffering_capacity=buffer_pool,
            )
            self.organ_pools[organ_name][nutrient] = pool
        for nutrient in nutrient_contents.keys():
            if nutrient not in self.cumulative_redistribution:
                self.cumulative_redistribution[nutrient] = 0.0

    def _calculate_transport_capacity(self, source_organ: str, water_flux: float, assimilate_flux: float,
                                    temperature: float, organ_nutrient_status: Dict[str, float]) -> Dict[str, float]:
        if f"{source_organ}_nutrient_status" not in organ_nutrient_status:
            raise KeyError(f"Missing nutrient status for {source_organ}")
        base_xylem_capacity = water_flux * self.params.xylem_transport_capacity * self.params.transpiration_coupling
        base_phloem_capacity = assimilate_flux * self.params.phloem_transport_capacity
        nutrient_feedback_factor = organ_nutrient_status[f"{source_organ}_nutrient_status"]
        nutrient_feedback_factor = max(0.5, min(2.0, nutrient_feedback_factor))
        return {
            "xylem": base_xylem_capacity * nutrient_feedback_factor,
            "phloem": base_phloem_capacity * nutrient_feedback_factor
        }

    def _calculate_sink_demands(self, organ_demands: Dict[str, Dict[str, float]], growth_stage: str) -> Dict[str, Dict[str, float]]:
        # Map growth stages to sink strength coefficients stages
        stage_map = {'mature': 'reproductive', 'head_formation': 'reproductive'}
        mapped_stage = stage_map.get(growth_stage, growth_stage)

        if mapped_stage not in self.params.sink_strength_coefficients:
            raise KeyError(f"Invalid growth stage: {growth_stage}")
        adjusted = {}
        sink_coeffs = self.params.sink_strength_coefficients[mapped_stage]
        for organ_name, demands in organ_demands.items():
            adjusted[organ_name] = {}
            if organ_name not in sink_coeffs:
                raise KeyError(f"Missing sink strength for {organ_name} in {growth_stage}")
            organ_sink_strength = sink_coeffs[organ_name]
            for nutrient, demand in demands.items():
                if nutrient not in self.params.mobility_classifications:
                    raise KeyError(f"Nutrient {nutrient} not found in mobility classifications")
                adj = demand * organ_sink_strength
                mobility_info = self.params.mobility_classifications[nutrient]
                dm = mobility_info["deficiency_mobility"]
                if dm not in ["very_high", "high", "low", "very_low"]:
                    raise ValueError(f"Invalid deficiency mobility for {nutrient}: {dm}")
                adj *= {"very_high": 1.2, "high": 1.1, "low": 0.8, "very_low": 0.6}[dm]
                adjusted[organ_name][nutrient] = adj
        return adjusted

    def _calculate_source_supplies(self, stress_factors: Dict[str, float], senescence_rates: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        supplies = {}
        for organ_name, nutrient_pools in self.organ_pools.items():
            supplies[organ_name] = {}
            if organ_name not in senescence_rates:
                raise KeyError(f"Missing senescence rate for {organ_name}")
            overall_stress = 1.0 - min(stress_factors.values())
            organ_senescence = senescence_rates[organ_name]
            for nutrient, pool in nutrient_pools.items():
                if nutrient not in self.params.mobility_classifications:
                    raise KeyError(f"Nutrient {nutrient} not found in mobility classifications")
                mobility_info = self.params.mobility_classifications[nutrient]
                base_supply = pool.storage_pool * 0.1 + pool.buffer_pool * 0.05
                stress_supply = 0.0
                if overall_stress > 0.3:
                    if nutrient not in self.params.redistribution_thresholds:
                        raise KeyError(f"Missing redistribution threshold for {nutrient}")
                    stress_threshold = self.params.redistribution_thresholds[nutrient]
                    if overall_stress > (1.0 - stress_threshold):
                        if nutrient not in self.params.stress_redistribution_rates:
                            raise KeyError(f"Missing stress redistribution rate for {nutrient}")
                        stress_rate = self.params.stress_redistribution_rates[nutrient]
                        stress_supply = pool.storage_pool * stress_rate * overall_stress
                senescence_supply = pool.metabolic_pool * organ_senescence * mobility_info["remobilization_efficiency"]
                total_supply = base_supply + stress_supply + senescence_supply
                max_transportable = pool.total_content * 0.3
                supplies[organ_name][nutrient] = min(total_supply, max_transportable)
        return supplies

    def _calculate_transport_fluxes(self, sink_demands: Dict[str, Dict[str, float]], source_supplies: Dict[str, Dict[str, float]],
                                  transport_capacities: Dict[str, Dict[str, float]], temperature: float) -> List[NutrientTransportFlux]:
        fluxes = []
        temp_factor = self.params.temperature_q10 ** ((temperature - 25.0) / 10.0)
        temp_factor = max(0.5, min(2.0, temp_factor))
        for nutrient in self.params.mobility_classifications:
            mobility_info = self.params.mobility_classifications[nutrient]
            transport_type = mobility_info["transport"]
            if nutrient not in self.params.xylem_transport_rates or nutrient not in self.params.phloem_transport_rates:
                raise KeyError(f"Missing transport rates for {nutrient}")
            xylem_rate = self.params.xylem_transport_rates[nutrient] * temp_factor
            phloem_rate = self.params.phloem_transport_rates[nutrient] * temp_factor
            total_demand = sum(d.get(nutrient, 0.0) for d in sink_demands.values())
            total_supply = sum(s.get(nutrient, 0.0) for s in source_supplies.values())
            if total_demand > 0 and total_supply > 0:
                supply_demand_ratio = total_supply / total_demand
                transport_eff = min(1.0, supply_demand_ratio)
                for source_organ, supplies in source_supplies.items():
                    if source_organ not in transport_capacities:
                        raise KeyError(f"Missing transport capacities for {source_organ}")
                    if supplies.get(nutrient, 0.0) > 0:
                        src_supply = supplies[nutrient]
                        for sink_organ, demands in sink_demands.items():
                            if demands.get(nutrient, 0.0) > 0 and source_organ != sink_organ:
                                sink_demand = demands[nutrient]
                                if transport_type == TransportMechanism.XYLEM_ONLY.value:
                                    if source_organ == "roots":
                                        max_flux = src_supply * xylem_rate
                                        cap = transport_capacities[source_organ]["xylem"]
                                        flux_rate = min(max_flux, sink_demand, cap)
                                        mechanism = "xylem"
                                    else:
                                        flux_rate = 0.0
                                        mechanism = "none"
                                elif transport_type == TransportMechanism.BIDIRECTIONAL.value:
                                    xylem_flux = src_supply * xylem_rate * 0.6
                                    phloem_flux = src_supply * phloem_rate * 0.4
                                    xcap = transport_capacities[source_organ]["xylem"]
                                    pcap = transport_capacities[source_organ]["phloem"]
                                    flux_rate = min(xylem_flux + phloem_flux, sink_demand, xcap + pcap)
                                    mechanism = "bidirectional"
                                elif transport_type == TransportMechanism.COMPLEX.value:
                                    base_flux = src_supply * min(xylem_rate, phloem_rate)
                                    total_cap = transport_capacities[source_organ]["xylem"] + transport_capacities[source_organ]["phloem"]
                                    flux_rate = min(base_flux, sink_demand, total_cap)
                                    mechanism = "complex"
                                else:
                                    flux_rate = 0.0
                                    mechanism = "none"
                                flux_rate *= transport_eff
                                if flux_rate > 0.001:
                                    fluxes.append(
                                        NutrientTransportFlux(
                                            source_organ=source_organ,
                                            sink_organ=sink_organ,
                                            nutrient=nutrient,
                                            transport_mechanism=mechanism,
                                            flux_rate=flux_rate,
                                            driving_force="demand",
                                            efficiency=transport_eff,
                                        )
                                    )
        return fluxes

    def _update_organ_pools(self, transport_fluxes: List[NutrientTransportFlux]):
        net_fluxes: Dict[str, Dict[str, float]] = {}
        for flux in transport_fluxes:
            net_fluxes.setdefault(flux.source_organ, {}).setdefault(flux.nutrient, 0.0)
            net_fluxes.setdefault(flux.sink_organ, {}).setdefault(flux.nutrient, 0.0)
            net_fluxes[flux.source_organ][flux.nutrient] -= flux.flux_rate
            net_fluxes[flux.sink_organ][flux.nutrient] += flux.flux_rate
        for organ_name, nutrient_fluxes in net_fluxes.items():
            if organ_name in self.organ_pools:
                for nutrient, net_flux in nutrient_fluxes.items():
                    if nutrient in self.organ_pools[organ_name]:
                        pool = self.organ_pools[organ_name][nutrient]
                        if net_flux < 0:
                            outflow = abs(net_flux)
                            from_transport = min(outflow, pool.transport_pool)
                            pool.transport_pool -= from_transport
                            outflow -= from_transport
                            if outflow > 0:
                                from_storage = min(outflow, pool.storage_pool)
                                pool.storage_pool -= from_storage
                                outflow -= from_storage
                            if outflow > 0:
                                from_buffer = min(outflow, pool.buffer_pool)
                                pool.buffer_pool -= from_buffer
                                outflow -= from_buffer
                            if outflow > 0:
                                from_met = min(outflow, pool.metabolic_pool * 0.1)
                                pool.metabolic_pool -= from_met
                        else:
                            pool.transport_pool += net_flux
                            if pool.transport_pool > pool.total_content * 0.1:
                                excess = pool.transport_pool - pool.total_content * 0.05
                                pool.transport_pool -= excess
                                pool.metabolic_pool += excess * 0.6
                                pool.storage_pool += excess * 0.3
                                pool.buffer_pool += excess * 0.1
                        pool.total_content = pool.metabolic_pool + pool.storage_pool + pool.transport_pool + pool.buffer_pool
                        self.cumulative_redistribution[nutrient] += net_flux

    def _calculate_mobility_efficiency(self, nutrient: str) -> float:
        if nutrient not in self.params.mobility_classifications:
            raise KeyError(f"Nutrient {nutrient} not found in mobility classifications")
        mobility_info = self.params.mobility_classifications[nutrient]
        mobility_class = mobility_info["mobility"]
        if mobility_class not in [e.value for e in NutrientMobility]:
            raise ValueError(f"Invalid mobility class for {nutrient}: {mobility_class}")
        base_eff = {
            NutrientMobility.HIGHLY_MOBILE.value: 0.8,
            NutrientMobility.MODERATELY_MOBILE.value: 0.6,
            NutrientMobility.POORLY_MOBILE.value: 0.3,
            NutrientMobility.IMMOBILE.value: 0.1
        }[mobility_class]
        transport_type = mobility_info["transport"]
        if transport_type not in [e.value for e in TransportMechanism]:
            raise ValueError(f"Invalid transport type for {nutrient}: {transport_type}")
        t_factor = {
            TransportMechanism.BIDIRECTIONAL.value: 1.2,
            TransportMechanism.COMPLEX.value: 0.9,
            TransportMechanism.XYLEM_ONLY.value: 0.7,
            TransportMechanism.PHLOEM_ONLY.value: 1.0
        }[transport_type]
        return min(1.0, base_eff * t_factor)

    def _calculate_nutrient_mobility(self, organ_demands: Dict[str, Dict[str, float]], plant_status: Dict[str, Any],
                                   env_conditions: Dict[str, Any], water_fluxes: Dict[str, float],
                                   assimilate_fluxes: Dict[str, float]) -> NutrientMobilityResponse:
        growth_stage = plant_status['growth_stage']
        senescence_rates = plant_status['senescence_rates']
        stress_factors = plant_status['stress_factors']
        temperature = env_conditions['temperature']
        organ_nutrient_status = plant_status['organ_nutrient_status']

        sink_demands = self._calculate_sink_demands(organ_demands, growth_stage)
        source_supplies = self._calculate_source_supplies(stress_factors, senescence_rates)
        transport_capacities = {}
        for organ in self.organ_pools.keys():
            if organ not in water_fluxes or organ not in assimilate_fluxes:
                raise KeyError(f"Missing flux data for {organ}")
            water_flux = water_fluxes[organ]
            assimilate_flux = assimilate_fluxes[organ]
            transport_capacities[organ] = self._calculate_transport_capacity(
                organ, water_flux, assimilate_flux, temperature, organ_nutrient_status
            )
        transport_fluxes = self._calculate_transport_fluxes(sink_demands, source_supplies, transport_capacities, temperature)
        self._update_organ_pools(transport_fluxes)

        total_redistribution = {}
        for flux in transport_fluxes:
            total_redistribution[flux.nutrient] = total_redistribution.get(flux.nutrient, 0.0) + flux.flux_rate

        limitations = []
        for nutrient in self.params.mobility_classifications:
            total_demand = sum(d.get(nutrient, 0.0) for d in sink_demands.values())
            total_flux = total_redistribution.get(nutrient, 0.0)
            if total_demand > 0 and total_flux < total_demand * 0.8:
                limitations.append(f"{nutrient}_transport_limited")

        mobility_efficiency = {n: self._calculate_mobility_efficiency(n) for n in self.params.mobility_classifications}
        self.transport_history.append({
            "total_redistribution": sum(total_redistribution.values()),
            "transport_fluxes": len(transport_fluxes),
            "limitations": len(limitations),
        })

        return NutrientMobilityResponse(
            transport_fluxes=transport_fluxes,
            organ_pools=self.organ_pools.copy(),
            total_redistribution=total_redistribution,
            transport_limitations=limitations,
            sink_demands=sink_demands,
            source_supplies=source_supplies,
            mobility_efficiency=mobility_efficiency
        )

def create_lettuce_nutrient_model(system_config: Any) -> NutrientModel:
    config = getattr(system_config, 'nutrient_parameters', {})
    if not config:
        raise ValueError("nutrient_parameters section must be provided in configuration")
    parameters = NutrientParameters.from_config(config)
    return NutrientModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- ec_factor_n_no3: EC contribution factor for nitrate nitrogen
- ec_factor_n_nh4: EC contribution factor for ammonium nitrogen
- ec_factor_p_po4: EC contribution factor for phosphate phosphorus
- ec_factor_k: EC contribution factor for potassium
- ec_factor_ca: EC contribution factor for calcium
- ec_factor_mg: EC contribution factor for magnesium
- ec_factor_s_so4: EC contribution factor for sulfate sulfur
- ec_factor_fe: EC contribution factor for iron
- ec_factor_mn: EC contribution factor for manganese
- ec_factor_zn: EC contribution factor for zinc
- ec_factor_cu: EC contribution factor for copper
- ec_factor_b: EC contribution factor for boron
- ec_factor_mo: EC contribution factor for molybdenum
- minimum_volume_fraction: minimum solution volume fraction
- xylem_transport_capacity: maximum xylem transport rate
- phloem_transport_capacity: maximum phloem transport rate
- temperature_q10: temperature response coefficient
- transpiration_coupling: coupling factor for transpiration-driven transport
- ec_uptake_high_threshold: high EC threshold for uptake modification
- ec_uptake_low_threshold: low EC threshold for uptake modification
- ec_uptake_modifier_n_high: nitrogen uptake modifier under high EC
- ec_uptake_modifier_p_high: phosphorus uptake modifier under high EC
- ec_uptake_modifier_k_high: potassium uptake modifier under high EC
- ec_uptake_modifier_ca_high: calcium uptake modifier under high EC
- ec_uptake_modifier_n_low: nitrogen uptake modifier under low EC
- ec_uptake_modifier_p_low: phosphorus uptake modifier under low EC
- ec_uptake_modifier_fe_low: iron uptake modifier under low EC
- kinetics_n_no3_vmax: maximum uptake rate for nitrate nitrogen
- kinetics_n_no3_km: Michaelis constant for nitrate nitrogen
- kinetics_n_no3_min_conc: minimum concentration for nitrate nitrogen uptake
- kinetics_n_nh4_vmax: maximum uptake rate for ammonium nitrogen
- kinetics_n_nh4_km: Michaelis constant for ammonium nitrogen
- kinetics_n_nh4_min_conc: minimum concentration for ammonium nitrogen uptake
- kinetics_p_po4_vmax: maximum uptake rate for phosphate phosphorus
- kinetics_p_po4_km: Michaelis constant for phosphate phosphorus
- kinetics_p_po4_min_conc: minimum concentration for phosphate phosphorus uptake
- kinetics_k_vmax: maximum uptake rate for potassium
- kinetics_k_km: Michaelis constant for potassium
- kinetics_k_min_conc: minimum concentration for potassium uptake
- kinetics_ca_vmax: maximum uptake rate for calcium
- kinetics_ca_km: Michaelis constant for calcium
- kinetics_ca_min_conc: minimum concentration for calcium uptake
- kinetics_mg_vmax: maximum uptake rate for magnesium
- kinetics_mg_km: Michaelis constant for magnesium
- kinetics_mg_min_conc: minimum concentration for magnesium uptake
- mobility_classifications_[nutrient]_mobility: mobility classification (highly_mobile, moderately_mobile, poorly_mobile, immobile)
- mobility_classifications_[nutrient]_transport: transport mechanism (xylem_only, phloem_only, bidirectional, complex)
- mobility_classifications_[nutrient]_remobilization_efficiency: efficiency of nutrient remobilization
- mobility_classifications_[nutrient]_deficiency_mobility: mobility under deficiency (very_high, high, low, very_low)
- mobility_classifications_[nutrient]_retranslocation_rate: rate of nutrient retranslocation
- xylem_transport_rates_[nutrient]: xylem transport rate for nutrient
- phloem_transport_rates_[nutrient]: phloem transport rate for nutrient
- buffering_capacities_[organ]_[nutrient]: buffering capacity for nutrient in organ
- storage_pool_sizes_[organ]_[nutrient]: storage pool size for nutrient in organ
- redistribution_thresholds_[nutrient]: threshold for stress-induced redistribution
- stress_redistribution_rates_[nutrient]: rate of stress-induced redistribution
- sink_strength_coefficients_[stage]_[organ]: sink strength coefficient for organ in stage

INPUT VARIABLES:
- concentrations: current solution concentrations (mg/L)
- plant_status: dict with root_surface_area (cm²), tank_volume_L (L), plant_count, daily_growth_rate (g/day),
                growth_stage, senescence_rates, stress_factors, organ_nutrient_status
- env_conditions: dict with temperature (°C), ph, optimal_ec (dS/m)
- organ_demands: nutrient demand by plant organ (mg)
- water_fluxes: water flux by organ (L/day)
- assimilate_fluxes: assimilate flux by organ (g/day)

OUTPUT VARIABLES:
- calculated_ec: computed electrical conductivity (dS/m)
- uptake_rates_mg_per_plant_per_day: nutrient uptake rates (mg/plant/day)
- updated_concentrations: solution concentrations after uptake (mg/L)
- transport_fluxes: nutrient movement between organs
- organ_pools: nutrient storage in plant organs
- mobility_efficiency: transport effectiveness by nutrient
- transport_limitations: list of transport-limited nutrients
"""