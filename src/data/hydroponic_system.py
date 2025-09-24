"""
Hydroponic System Data Classes and Configuration - No hardcoded defaults allowed and no fallback to simple alternative codes
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import math


@dataclass
class HydroSystemConfig:
    """Configuration for hydroponic system parameters."""
    system_id: str
    crop_id: str
    location_id: str
    tank_volume: float  # L
    flow_rate: float  # L/h
    system_type: str  # NFT, DWC, AERO, WICK, EBB
    system_area: float  # m²
    n_plants: int
    description: str


@dataclass
class CropParameters:
    """Crop-specific parameters."""
    crop_id: str
    crop_name: str
    kcb: float  # Basal crop coefficient
    phi: float  # Density index
    crop_height: float  # m
    root_zone_depth: float  # m
    laid: float  # Leaf area index


@dataclass
class WeatherData:
    """Daily weather data."""
    date: datetime
    temp_avg: float  # °C
    temp_min: float  # °C
    temp_max: float  # °C
    solar_radiation: float  # MJ/m²/day
    rel_humidity: float  # %
    wind_speed: float  # m/s
    rainfall: float = None  # mm


@dataclass
class HydroInputData:
    """Complete input data for hydroponic simulation."""
    system_config: HydroSystemConfig
    crop_params: CropParameters
    weather_data: List[WeatherData]
    nutrient_params: Dict = field(default_factory=dict)
    simulation_days: int = 30


@dataclass
class DailyResults:
    """Results for a single simulation day."""
    date: datetime
    day: int
    eto_ref: float  # mm/day
    etc_prime: float  # mm/day
    transpiration: float  # mm/day
    water_uptake_total: float  # L/day
    tank_volume: float  # L
    nutrient_concentrations: Dict[str, float]  # mg/L
    temp_avg: float  # °C
    solar_radiation: float  # MJ/m²/day
    vpd: float  # kPa
    water_use_efficiency: float  # L/kg
    ph: float = None
    ec: float = None
    rzt: float = None  # Root zone temperature (°C)
    rzt_growth_factor: float = None  # RZT growth effect
    rzt_nutrient_factor: float = None  # RZT nutrient uptake effect
    v_stage: float = None  # Vegetative stage (number of leaves)
    leaf_number: int = None  # Current number of active leaves
    leaf_area_m2: float = None  # Total leaf area per plant (m²)
    average_leaf_area_cm2: float = None  # Average leaf area (cm²)
    co2_concentration: float = None  # CO2 concentration (μmol/mol) - will be overridden by simulation
    vpd_actual: float = None  # Actual VPD (kPa) - will be overridden by simulation
    env_photosynthesis_factor: float = None  # Environmental photosynthesis enhancement
    env_transpiration_factor: float = None  # Environmental transpiration factor
    
    # === DETAILED PHOTOSYNTHESIS MODEL RESULTS ===
    vcmax_25: float = None  # Maximum carboxylation rate at 25°C (μmol/m²/s)
    jmax_25: float = None   # Maximum electron transport rate at 25°C (μmol/m²/s)
    quantum_efficiency: float = None  # Quantum efficiency of photosystem II
    rubisco_limited: float = None  # Rubisco-limited photosynthesis rate
    light_limited: float = None    # Light-limited photosynthesis rate
    co2_compensation: float = None  # CO2 compensation point (μmol/mol)
    intercellular_co2: float = None  # Intercellular CO2 concentration
    
    # === DETAILED RESPIRATION MODEL RESULTS ===
    maintenance_resp_leaves: float = None  # Leaf maintenance respiration
    maintenance_resp_stems: float = None   # Stem maintenance respiration  
    maintenance_resp_roots: float = None   # Root maintenance respiration
    growth_resp_leaves: float = None       # Leaf growth respiration
    growth_resp_stems: float = None        # Stem growth respiration
    growth_resp_roots: float = None        # Root growth respiration
    temperature_acclimation: float = None   # Temperature acclimation factor
    age_factor: float = None               # Age effects on respiration
    
    # === DETAILED ROOT ARCHITECTURE RESULTS ===
    fine_root_length: float = None    # Fine root length (cm)
    coarse_root_length: float = None  # Coarse root length (cm) 
    root_cohorts: int = None            # Number of active root cohorts
    root_activity_young: float = None # Activity of young roots
    root_activity_old: float = None   # Activity of old roots
    root_surface_active: float = None # Active root surface area
    root_turnover_rate: float = None  # Daily root turnover rate
    
    # === DETAILED CANOPY ARCHITECTURE RESULTS ===
    sunlit_lai: float = None          # Sunlit leaf area index
    shaded_lai: float = None          # Shaded leaf area index
    canopy_layers: int = None           # Number of canopy layers
    ppfd_top: float = None           # PPFD at top of canopy
    ppfd_bottom: float = None        # PPFD at bottom of canopy
    light_extinction: float = None    # Light extinction coefficient
    
    # === DETAILED NITROGEN DYNAMICS RESULTS ===
    n_pool_structural: float = None   # Structural nitrogen pool (g)
    n_pool_metabolic: float = None    # Metabolic nitrogen pool (g)
    n_pool_storage: float = None      # Storage nitrogen pool (g)
    n_pool_transport: float = None    # Transport nitrogen pool (g)
    n_remobilization: float = None    # Daily N remobilization (g)
    n_critical_conc: float = None     # Critical nitrogen concentration
    
    # === DETAILED STRESS INTEGRATION RESULTS ===
    stress_interactions: Dict[str, float] = field(default_factory=dict)  # Stress interaction effects
    acclimation_levels: Dict[str, float] = field(default_factory=dict)   # Acclimation to each stress
    cumulative_damage: Dict[str, float] = field(default_factory=dict)    # Cumulative damage by stress type
    
    # === ADDITIONAL CROPGRO MODEL RESULTS ===
    # Genetic parameters
    cultivar_adaptation_index: float = None
    cultivar_yield_potential: float = None
    genetic_photosynthesis_capacity: float = None
    genetic_ec_tolerance: float = None
    genetic_nitrate_efficiency: float = None
    
    # Phenology
    accumulated_gdd: float = None
    development_rate: float = None
    growth_stage: str = None
    thermal_time_daily: float = None
    is_vegetative: bool = None
    is_reproductive: bool = None
    
    # Growth and biomass
    total_biomass: float = None
    leaf_biomass: float = None
    stem_biomass: float = None
    root_biomass: float = None
    daily_growth_rate: float = None
    leaf_growth_rate: float = None
    stem_growth_rate: float = None
    root_growth_rate: float = None
    
    # Canopy architecture
    lai: float = None
    canopy_height_cm: float = None
    light_interception: float = None
    total_absorbed_ppfd: float = None
    canopy_photosynthesis: float = None
    
    # Photosynthesis detailed
    photosynthesis_rate: float = None
    net_assimilation: float = None
    
    # Respiration detailed
    maintenance_respiration: float = None
    growth_respiration: float = None
    respiration_rate: float = None
    
    # Root architecture detailed
    root_surface_area: float = None
    root_length_density: float = None
    root_volume: float = None
    
    # Nitrogen dynamics detailed
    nitrogen_uptake_mg: float = None
    nitrogen_demand_mg: float = None
    nitrogen_stress_factor: float = None
    leaf_nitrogen_conc: float = None
    root_nitrogen_conc: float = None
    nitrogen_remobilization: float = None
    
    # Phosphorus dynamics detailed
    phosphorus_uptake_mg: float = None
    
    # Nutrient remobilization
    phosphorus_remobilization: float = None
    potassium_remobilization: float = None
    
    # Senescence 
    senescence_rate: float = None
    leaf_senescence_rate: float = None
    
    # Stress factors (0 = no stress, 1 = full stress)
    integrated_stress_factor: float = None
    temperature_stress_level: float = None
    temperature_stress_photosynthesis: float = None
    temperature_stress_growth: float = None
    water_stress: float = None
    nutrient_stress: float = None
    salinity_stress: float = None
    
    # Environmental control
    controlled_temperature: float = None
    controlled_humidity: float = None
    controlled_co2: float = None
    vpd_target: float = None
    environmental_cost: float = None
    
    # Temperature stress (implemented)
    cold_stress_factor: float = None  # 0 = no cold stress, 1 = severe cold stress
    heat_stress_factor: float = None  # 0 = no heat stress, 1 = severe heat stress
    temperature_stress_factor: float = None  # 0 = no temperature stress, 1 = severe temperature stress
    solution_ph: float = None
    
    # Comprehensive pH modeling results
    ph_change_from_uptake: float = None
    ph_change_from_drift: float = None
    acid_dosed_ml_per_L: float = None
    base_dosed_ml_per_L: float = None
    buffer_capacity: float = None
    phosphate_h2po4_mg_L: float = None
    phosphate_hpo4_mg_L: float = None
    phosphate_po4_mg_L: float = None
    nutrient_precipitation_mg_L: float = None
    solution_ec: float = None
    
    # === ADVANCED ROOT ZONE TEMPERATURE PARAMETERS ===
    rzt_water_factor: float = None
    rzt_photosynthesis_factor: float = None
    rzt_root_metabolism_factor: float = None
    rzt_stress_factor: float = None
    rzt_optimal_factor: float = None
    rzt_daily_range: float = None
    individual_rzt_factors: Dict[str, float] = field(default_factory=dict)
    root_temp_stress: float = None
    
    # === ADVANCED SENESCENCE PARAMETERS ===
    senesced_area: float = None
    senesced_biomass: float = None
    average_senescence_stage: str = None
    active_senescence_types: List[str] = field(default_factory=list)
    remobilization_pool: Dict[str, float] = field(default_factory=dict)
    
    # === ADVANCED STRESS INTERACTION PARAMETERS ===
    ph_stress: float = None
    oxygen_stress: float = None
    stress_severity: str = None
    dominant_stresses: List[str] = field(default_factory=list)
    stress_interactions_active: List[str] = field(default_factory=list)
    acclimation_active: List[str] = field(default_factory=list)
    recovery_active: List[str] = field(default_factory=list)
    total_damage: float = None
    
    # === ADVANCED NUTRIENT TRANSPORT PARAMETERS ===
    nutrient_transport_fluxes: Dict[str, float] = field(default_factory=dict)
    transport_limitations: List[str] = field(default_factory=list)
    mobility_efficiency: Dict[str, float] = field(default_factory=dict)
    nutrient_redistribution: Dict[str, float] = field(default_factory=dict)
    transport_pool_fractions: Dict[str, float] = field(default_factory=dict)
    cumulative_redistribution: Dict[str, float] = field(default_factory=dict)
    
    # === ADVANCED PH CONTROL PARAMETERS ===
    henderson_hasselbalch_ph: float = None
    controlled_ph: float = None
    acid_dosing_rate: float = None
    base_dosing_rate: float = None


@dataclass
class SimulationResults:
    """Complete simulation results."""
    system_id: str
    crop_id: str
    location_id: str
    start_date: datetime
    end_date: datetime
    total_days: int
    daily_results: List[DailyResults]
    summary_stats: Dict = field(default_factory=dict)
    treatment_id: str = None  # Added for batch experiment tracking
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame for analysis."""
        data = []
        for result in self.daily_results:
            # Calculate DAS (Days After Sowing) and DAT (Days After Transplanting)
            # Get transplanting period from the simulation (passed dynamically)
            if not hasattr(self, 'transplanting_period_days'):
                raise AttributeError("transplanting_period_days not found in results - check experiment settings CSV")
            
            das = result.day + self.transplanting_period_days  # Add transplanting period
            dat = result.day  # Days since transplanting (simulation starts from transplant)
            
            # === ORGANIZED ROW WITH FUNCTIONAL GROUPS ===
            row = {}
            
            # === GROUP 1: EXPERIMENT METADATA ===
            row.update({
                'Date': result.date.strftime('%Y-%m-%d'),
                'Day': result.day,
                'DAS': das,
                'DAT': dat,
                'Treatment_ID': self.treatment_id if self.treatment_id else 'DEFAULT',
                'System_ID': self.system_id,
                'Crop_ID': self.crop_id,
                'Location_ID': self.location_id,
                'System_Type': getattr(self, 'system_type', 'Unknown'),
                'System_Area_m2': getattr(self, 'system_area', 0.0),
                'Plant_Count': getattr(self, 'plant_count', 0),
                'Flow_Rate_L_h': getattr(self, 'flow_rate', 0.0),
                'System_Description': getattr(self, 'system_description', ''),
                '': '',  # Separator
            })
            
            # === GROUP 2: ENVIRONMENTAL CONDITIONS ===
            row.update({
                'Temp_C': result.temp_avg,
                'Solar_Rad_MJ': result.solar_radiation,
                'VPD_kPa': result.vpd,
                'CO2_umol_mol': result.co2_concentration,
                ' ': '',  # Separator
            })
            
            # === GROUP 3: WATER DYNAMICS ===
            row.update({
                'ETO_Ref_mm': result.eto_ref,
                'ETC_Prime_mm': result.etc_prime,
                'Transpiration_mm': result.transpiration,
                'Water_Total_L': result.water_uptake_total,
                'Tank_Volume_L': result.tank_volume,
                'WUE_L_kg': result.water_use_efficiency,
                '  ': '',  # Separator
            })
            
            # === GROUP 4: SOLUTION CHEMISTRY ===
            row.update({
                'pH': result.ph,
                'EC': result.ec,
                'pH_Change_Uptake': result.ph_change_from_uptake,
                'pH_Drift': result.ph_change_from_drift,
                'Acid_Dosed_mL_L': result.acid_dosed_ml_per_L,
                'Base_Dosed_mL_L': result.base_dosed_ml_per_L,
                'Buffer_Capacity': result.buffer_capacity,
                '   ': '',  # Separator
            })
            
            # === GROUP 5: NUTRIENT CONCENTRATIONS ===
            row.update({
                'N-NO3_mg_L': result.nutrient_concentrations.get('N-NO3', 0.0),
                'P-PO4_mg_L': result.nutrient_concentrations.get('P-PO4', 0.0),
                'K_mg_L': result.nutrient_concentrations.get('K', 0.0),
                'Ca_mg_L': result.nutrient_concentrations.get('Ca', 0.0),
                'Mg_mg_L': result.nutrient_concentrations.get('Mg', 0.0),
                '    ': '',  # Separator
            })
            
            # === GROUP 6: ROOT ZONE CONDITIONS ===
            row.update({
                'RZT_C': result.rzt,
                'RZT_Growth_Factor': result.rzt_growth_factor,
                'RZT_Nutrient_Factor': result.rzt_nutrient_factor,
                'Env_Photo_Factor': result.env_photosynthesis_factor,
                'Env_Transp_Factor': result.env_transpiration_factor,
                '     ': '',  # Separator
            })
            
            # === GROUP 7: PLANT DEVELOPMENT ===
            row.update({
                'V_Stage': result.v_stage,
                'Leaf_Number': result.leaf_number,
                'Leaf_Area_m2': result.leaf_area_m2,
                'Avg_Leaf_Area_cm2': result.average_leaf_area_cm2,
                '      ': '',  # Separator
            })
            
            # === GROUP 8: GROWTH & BIOMASS ===
            biomass_group = {}
            if hasattr(result, 'growth_stage'):
                biomass_group['Growth_Stage'] = result.growth_stage
            if hasattr(result, 'total_biomass'):
                biomass_group['Total_Biomass_g'] = result.total_biomass
            if hasattr(result, 'lai'):
                biomass_group['LAI'] = result.lai
            if hasattr(result, 'canopy_height_cm'):
                biomass_group['Plant_Height_cm'] = result.canopy_height_cm
            if hasattr(result, 'daily_growth_rate'):
                biomass_group['Daily_Growth_Rate_g_day'] = result.daily_growth_rate
            biomass_group['       '] = ''  # Separator
            row.update(biomass_group)
            
            # === GROUP 9: STRESS FACTORS ===
            stress_group = {}
            if hasattr(result, 'integrated_stress_factor'):
                stress_group['Integrated_Stress'] = result.integrated_stress_factor
            if hasattr(result, 'temperature_stress_level'):
                stress_group['Temperature_Stress'] = result.temperature_stress_level
            if hasattr(result, 'water_stress'):
                stress_group['Water_Stress'] = result.water_stress
            if hasattr(result, 'nutrient_stress'):
                stress_group['Nutrient_Stress'] = result.nutrient_stress
            if hasattr(result, 'nitrogen_stress_factor'):
                stress_group['Nitrogen_Stress'] = result.nitrogen_stress_factor
            if hasattr(result, 'salinity_stress'):
                stress_group['Salinity_Stress'] = result.salinity_stress
            stress_group['        '] = ''  # Separator
            row.update(stress_group)
            
            # === GROUP 10: BIOMASS COMPONENTS ===
            biomass_detail_group = {}
            if hasattr(result, 'leaf_biomass'):
                biomass_detail_group['Shoot_Dry_Weight_g'] = getattr(result, 'leaf_biomass', 0.0) + getattr(result, 'stem_biomass', 0.0)
                biomass_detail_group['Leaf_Dry_Weight_g'] = result.leaf_biomass
                biomass_detail_group['Stem_Dry_Weight_g'] = getattr(result, 'stem_biomass', 0.0)
                # Calculate fresh weight using dynamic dry matter content
                shoot_dry_matter = calculate_dynamic_dry_matter_content(result, 'shoot')
                leaf_dry_matter = calculate_dynamic_dry_matter_content(result, 'leaf')
                stem_dry_matter = calculate_dynamic_dry_matter_content(result, 'stem')
                biomass_detail_group['Shoot_Fresh_Weight_g'] = biomass_detail_group['Shoot_Dry_Weight_g'] / shoot_dry_matter
                biomass_detail_group['Leaf_Fresh_Weight_g'] = result.leaf_biomass / leaf_dry_matter
                biomass_detail_group['Stem_Fresh_Weight_g'] = getattr(result, 'stem_biomass', 0.0) / stem_dry_matter
            if hasattr(result, 'root_biomass'):
                biomass_detail_group['Root_Dry_Weight_g'] = result.root_biomass
                root_dry_matter = calculate_dynamic_dry_matter_content(result, 'root')
                biomass_detail_group['Root_Fresh_Weight_g'] = result.root_biomass / root_dry_matter
            if hasattr(result, 'leaf_growth_rate'):
                biomass_detail_group['Leaf_Growth_Rate_g_day'] = result.leaf_growth_rate
            if hasattr(result, 'stem_growth_rate'):
                biomass_detail_group['Stem_Growth_Rate_g_day'] = result.stem_growth_rate
            if hasattr(result, 'root_growth_rate'):
                biomass_detail_group['Root_Growth_Rate_g_day'] = result.root_growth_rate
            biomass_detail_group['         '] = ''  # Separator
            row.update(biomass_detail_group)
            
            # === GROUP 11: ROOT ARCHITECTURE ===
            root_group = {}
            if hasattr(result, 'fine_root_length'):
                root_group['Fine_Root_Length_cm'] = result.fine_root_length
            if hasattr(result, 'coarse_root_length'):
                root_group['Coarse_Root_Length_cm'] = result.coarse_root_length
            if hasattr(result, 'root_length_density'):
                root_group['Root_Length_Density_cm_cm3'] = result.root_length_density
            if hasattr(result, 'root_surface_area'):
                root_group['Root_Surface_Area_cm2'] = result.root_surface_area
            if hasattr(result, 'root_volume'):
                root_group['Root_Volume_cm3'] = result.root_volume
            root_group['          '] = ''  # Separator
            row.update(root_group)

            # === GROUP 12: PHOTOSYNTHESIS ===
            photo_group = {}
            if hasattr(result, 'vcmax_25'):
                photo_group['Vcmax_25_umol_m2_s'] = result.vcmax_25
            if hasattr(result, 'jmax_25'):
                row['Jmax_25_umol_m2_s'] = result.jmax_25
            if hasattr(result, 'quantum_efficiency'):
                row['Quantum_Efficiency'] = result.quantum_efficiency
            if hasattr(result, 'rubisco_limited'):
                row['Rubisco_Limited_umol_m2_s'] = result.rubisco_limited
            if hasattr(result, 'light_limited'):
                row['Light_Limited_umol_m2_s'] = result.light_limited
            if hasattr(result, 'co2_compensation'):
                row['CO2_Compensation_umol_mol'] = result.co2_compensation
            if hasattr(result, 'intercellular_co2'):
                row['Intercellular_CO2_umol_mol'] = result.intercellular_co2
            if hasattr(result, 'photosynthesis_rate'):
                row['Photosynthesis_Rate'] = result.photosynthesis_rate
            if hasattr(result, 'net_assimilation'):
                row['Net_Assimilation'] = result.net_assimilation

            # === RESPIRATION DETAIL ===
            if hasattr(result, 'maintenance_respiration'):
                row['Maintenance_Respiration'] = result.maintenance_respiration
            if hasattr(result, 'growth_respiration'):
                row['Growth_Respiration'] = result.growth_respiration
            if hasattr(result, 'respiration_rate'):
                row['Respiration_Rate'] = result.respiration_rate
            if hasattr(result, 'maintenance_resp_leaves'):
                row['Maint_Resp_Leaves'] = result.maintenance_resp_leaves
            if hasattr(result, 'maintenance_resp_stems'):
                row['Maint_Resp_Stems'] = result.maintenance_resp_stems
            if hasattr(result, 'maintenance_resp_roots'):
                row['Maint_Resp_Roots'] = result.maintenance_resp_roots
            if hasattr(result, 'growth_resp_leaves'):
                row['Growth_Resp_Leaves'] = result.growth_resp_leaves
            if hasattr(result, 'growth_resp_stems'):
                row['Growth_Resp_Stems'] = result.growth_resp_stems
            if hasattr(result, 'growth_resp_roots'):
                row['Growth_Resp_Roots'] = result.growth_resp_roots
            if hasattr(result, 'temperature_acclimation'):
                row['Temperature_Acclimation'] = result.temperature_acclimation
            if hasattr(result, 'age_factor'):
                row['Age_Factor'] = result.age_factor

            # === CANOPY DETAIL ===
            if hasattr(result, 'light_interception'):
                row['Light_Interception'] = result.light_interception
            if hasattr(result, 'sunlit_lai'):
                row['Sunlit_LAI'] = result.sunlit_lai
            if hasattr(result, 'shaded_lai'):
                row['Shaded_LAI'] = result.shaded_lai
            if hasattr(result, 'total_absorbed_ppfd'):
                row['Total_Absorbed_PPFD_umol_m2_s'] = result.total_absorbed_ppfd
            if hasattr(result, 'canopy_photosynthesis'):
                row['Canopy_Photosynthesis_umol_m2_s'] = result.canopy_photosynthesis
            if hasattr(result, 'canopy_layers'):
                row['Canopy_Layers'] = result.canopy_layers
            if hasattr(result, 'ppfd_top'):
                row['PPFD_Top_umol_m2_s'] = result.ppfd_top
            if hasattr(result, 'ppfd_bottom'):
                row['PPFD_Bottom_umol_m2_s'] = result.ppfd_bottom
            if hasattr(result, 'light_extinction'):
                row['Light_Extinction_Coeff'] = result.light_extinction

            # === NITROGEN DYNAMICS ===
            if hasattr(result, 'n_pool_structural'):
                row['N_Pool_Structural_g'] = result.n_pool_structural
            if hasattr(result, 'n_pool_metabolic'):
                row['N_Pool_Metabolic_g'] = result.n_pool_metabolic
            if hasattr(result, 'n_pool_storage'):
                row['N_Pool_Storage_g'] = result.n_pool_storage
            if hasattr(result, 'n_pool_transport'):
                row['N_Pool_Transport_g'] = result.n_pool_transport
            if hasattr(result, 'n_remobilization'):
                row['N_Remobilization_g'] = result.n_remobilization
            if hasattr(result, 'n_critical_conc'):
                row['N_Critical_Conc'] = result.n_critical_conc
            if hasattr(result, 'nitrogen_uptake_mg'):
                row['Nitrogen_Uptake_mg'] = result.nitrogen_uptake_mg
            if hasattr(result, 'nitrogen_demand_mg'):
                row['Nitrogen_Demand_mg'] = result.nitrogen_demand_mg
            if hasattr(result, 'leaf_nitrogen_conc'):
                row['Leaf_Nitrogen_Conc'] = result.leaf_nitrogen_conc
            if hasattr(result, 'root_nitrogen_conc'):
                row['Root_Nitrogen_Conc'] = result.root_nitrogen_conc
            if hasattr(result, 'nitrogen_remobilization'):
                row['Nitrogen_Remobilization'] = result.nitrogen_remobilization

            # === GROWTH RATES ===
            if hasattr(result, 'daily_growth_rate'):
                row['Daily_Growth_Rate_g_day'] = result.daily_growth_rate
            if hasattr(result, 'leaf_growth_rate'):
                row['Leaf_Growth_Rate_g_day'] = result.leaf_growth_rate
            if hasattr(result, 'stem_growth_rate'):
                row['Stem_Growth_Rate_g_day'] = result.stem_growth_rate
            if hasattr(result, 'root_growth_rate'):
                row['Root_Growth_Rate_g_day'] = result.root_growth_rate

            # === PHENOLOGY DETAIL ===
            if hasattr(result, 'accumulated_gdd'):
                row['Accumulated_GDD'] = result.accumulated_gdd
            if hasattr(result, 'thermal_time_daily'):
                row['Thermal_Time_Daily'] = result.thermal_time_daily
            if hasattr(result, 'development_rate'):
                row['Development_Rate'] = result.development_rate
            if hasattr(result, 'is_vegetative'):
                row['Is_Vegetative'] = result.is_vegetative
            if hasattr(result, 'is_reproductive'):
                row['Is_Reproductive'] = result.is_reproductive

            # === ROOT ARCHITECTURE DETAIL ===
            if hasattr(result, 'root_surface_area'):
                row['Root_Surface_Area_cm2'] = result.root_surface_area
            if hasattr(result, 'root_volume'):
                row['Root_Volume_cm3'] = result.root_volume
            if hasattr(result, 'root_cohorts'):
                row['Root_Cohorts'] = result.root_cohorts
            if hasattr(result, 'root_activity_young'):
                row['Root_Activity_Young'] = result.root_activity_young
            if hasattr(result, 'root_activity_old'):
                row['Root_Activity_Old'] = result.root_activity_old
            if hasattr(result, 'root_surface_active'):
                row['Root_Surface_Active_cm2'] = result.root_surface_active
            if hasattr(result, 'root_turnover_rate'):
                row['Root_Turnover_Rate'] = result.root_turnover_rate

            # === GENETIC PARAMETERS ===
            if hasattr(result, 'cultivar_adaptation_index'):
                row['Cultivar_Adaptation_Index'] = result.cultivar_adaptation_index
            if hasattr(result, 'cultivar_yield_potential'):
                row['Cultivar_Yield_Potential'] = result.cultivar_yield_potential
            if hasattr(result, 'genetic_photosynthesis_capacity'):
                row['Genetic_Photosynthesis_Capacity'] = result.genetic_photosynthesis_capacity
            if hasattr(result, 'genetic_ec_tolerance'):
                row['Genetic_EC_Tolerance'] = result.genetic_ec_tolerance
            if hasattr(result, 'genetic_nitrate_efficiency'):
                row['Genetic_Nitrate_Efficiency'] = result.genetic_nitrate_efficiency

            # === NUTRIENT REMOBILIZATION ===
            if hasattr(result, 'phosphorus_uptake_mg'):
                row['Phosphorus_Uptake_mg'] = result.phosphorus_uptake_mg
            if hasattr(result, 'phosphorus_remobilization'):
                row['Phosphorus_Remobilization'] = result.phosphorus_remobilization
            if hasattr(result, 'potassium_remobilization'):
                row['Potassium_Remobilization'] = result.potassium_remobilization

            # === SENESCENCE ===
            if hasattr(result, 'senescence_rate'):
                row['Senescence_Rate'] = result.senescence_rate
            if hasattr(result, 'leaf_senescence_rate'):
                row['Leaf_Senescence_Rate'] = result.leaf_senescence_rate

            # === DETAILED STRESS FACTORS ===
            if hasattr(result, 'temperature_stress_photosynthesis'):
                row['Temperature_Stress_Photosynthesis'] = result.temperature_stress_photosynthesis
            if hasattr(result, 'temperature_stress_growth'):
                row['Temperature_Stress_Growth'] = result.temperature_stress_growth
            if hasattr(result, 'cold_stress_factor'):
                row['Cold_Stress_Factor'] = result.cold_stress_factor
            if hasattr(result, 'heat_stress_factor'):
                row['Heat_Stress_Factor'] = result.heat_stress_factor
            if hasattr(result, 'temperature_stress_factor'):
                row['Temperature_Stress_Factor'] = result.temperature_stress_factor

            # === ENVIRONMENTAL CONTROL ===
            # Controlled_Temperature_C removed - using main Temp_C column instead
            if hasattr(result, 'controlled_humidity'):
                row['Controlled_Humidity_pct'] = result.controlled_humidity
            # Controlled_CO2_umol_mol removed - using main CO2_umol_mol column instead
            if hasattr(result, 'vpd_target'):
                row['VPD_Target_kPa'] = result.vpd_target
            if hasattr(result, 'environmental_cost'):
                row['Environmental_Cost'] = result.environmental_cost

            # === TEMPERATURE DETAIL ===
            if hasattr(result, 'air_temperature'):
                row['Air_Temperature_C'] = result.air_temperature
            if hasattr(result, 'min_temperature'):
                row['Min_Temperature_C'] = result.min_temperature
            if hasattr(result, 'max_temperature'):
                row['Max_Temperature_C'] = result.max_temperature
            if hasattr(result, 'leaf_temperature'):
                row['Leaf_Temperature_C'] = result.leaf_temperature
            if hasattr(result, 'canopy_temperature'):
                row['Canopy_Temperature_C'] = result.canopy_temperature

            # === WATER DYNAMICS ===
            if hasattr(result, 'transpiration_rate'):
                row['Transpiration_Rate'] = result.transpiration_rate
            if hasattr(result, 'total_water_uptake'):
                row['Total_Water_Uptake'] = result.total_water_uptake
            # Solution_pH removed - using main pH column instead

            # === COMPREHENSIVE pH MODELING ===
            if hasattr(result, 'phosphate_h2po4_mg_L'):
                row['Phosphate_H2PO4_mg_L'] = result.phosphate_h2po4_mg_L
            if hasattr(result, 'phosphate_hpo4_mg_L'):
                row['Phosphate_HPO4_mg_L'] = result.phosphate_hpo4_mg_L
            if hasattr(result, 'nutrient_precipitation_mg_L'):
                row['Nutrient_Precipitation_mg_L'] = result.nutrient_precipitation_mg_L
            # Solution_EC_dS_m removed - using main EC column instead

            # === STRESS INTERACTIONS ===
            if hasattr(result, 'stress_interactions'):
                for stress_type, interaction_value in result.stress_interactions.items():
                    row[f'Stress_Interaction_{stress_type}'] = interaction_value
            if hasattr(result, 'acclimation_levels'):
                for stress_type, acclimation_value in result.acclimation_levels.items():
                    row[f'Acclimation_{stress_type}'] = acclimation_value
            if hasattr(result, 'cumulative_damage'):
                for stress_type, damage_value in result.cumulative_damage.items():
                    row[f'Cumulative_Damage_{stress_type}'] = damage_value

            # Round floats with field-specific precision to preserve signal
            precision_overrides = {
                'WUE_kg_m3': 3,
                'Leaf_Area_m2': 3,
                'LAI': 3,
                'EC': 2,
                'pH': 2,
                'Water_Total_L': 2,
                'Tank_Volume_L': 2,
                'Fine_Root_Length_cm': 1,
                'Coarse_Root_Length_cm': 1,
                'Root_Length_Density_cm_cm3': 3,
                'Shoot_Dry_Weight_g': 2,
                'Shoot_Fresh_Weight_g': 1,
                'Leaf_Dry_Weight_g': 2,
                'Leaf_Fresh_Weight_g': 1,
                'Stem_Dry_Weight_g': 2,
                'Stem_Fresh_Weight_g': 1,
                'Root_Dry_Weight_g': 2,
                'Root_Fresh_Weight_g': 1,
                'Plant_Height_cm': 1,
            }
            # Convert complex numbers to real values and round all numeric values to 2 decimal places
            for key, value in row.items():
                if isinstance(value, complex):
                    row[key] = round(value.real, 2)
                elif isinstance(value, float):
                    row[key] = round(value, 2)

            data.append(row)
            
        df = pd.DataFrame(data)
        
        # Format all numeric columns to 2 decimal places
        for col in df.columns:
            if df[col].dtype in ['float64', 'float32']:
                df[col] = df[col].round(2)
        
        return df
    
    def calculate_summary_stats(self):
        """Calculate summary statistics for the simulation."""
        df = self.to_dataframe()
        
        self.summary_stats = {
            'total_water_consumption_L': df['Water_Total_L'].sum(),
            'average_daily_consumption_L': df['Water_Total_L'].mean(),
            'final_tank_volume_L': df['Tank_Volume_L'].iloc[-1],
            'volume_reduction_L': df['Tank_Volume_L'].iloc[0] - df['Tank_Volume_L'].iloc[-1],
            'average_eto_mm': df['ETO_Ref_mm'].mean(),
            'average_transpiration_mm': df['Transpiration_mm'].mean(),
            'max_temperature_C': df['Temp_C'].max(),
            'min_temperature_C': df['Temp_C'].min(),
            'average_wue_kg_m3': df['WUE_kg_m3'].mean(),
            'simulation_period_days': self.total_days
        }


class DefaultConfigurations:
    """Default configurations for common hydroponic systems - CSV data required."""
    
    @staticmethod
    def get_nft_lettuce_system() -> HydroSystemConfig:
        """Create empty system config - CSV data will be loaded separately."""
        return HydroSystemConfig(
            system_id="",
            crop_id="",
            location_id="",
            tank_volume=0.0,
            flow_rate=0.0,
            system_type="",
            system_area=0.0,
            n_plants=0,
            description=""
        )
    
    @staticmethod
    def get_lettuce_parameters() -> CropParameters:
        """Create empty crop parameters - CSV data will be loaded separately."""
        return CropParameters(
            crop_id="",
            crop_name="",
            kcb=0.0,
            phi=0.0,
            crop_height=0.0,
            root_zone_depth=0.0,
            laid=0.0
        )
    
    @staticmethod
    def get_default_nutrients():
        """Return empty dict - nutrient parameters will be loaded from CSV only."""
        return {}


def calculate_dynamic_dry_matter_content(result, plant_part: str, strict_validation: bool = False) -> float:
    """
    Calculate dynamic dry matter content based on plant development, environment, and plant part.
    Dry matter content varies with:
    1. Plant development stage (young vs mature)
    2. Environmental stress (water, temperature, salinity)
    3. Plant part (leaves, stems, roots have different water contents)
    4. Growth rate (fast growth = higher water content)
    
    Args:
        result: Simulation result object
        plant_part: Plant part ('leaf', 'stem', 'shoot', 'root')
        strict_validation: If True, raises errors for missing parameters. If False, uses defaults for output.
    
    Returns fraction (0.0-1.0) of dry matter in fresh weight.
    """
    
    # Get development stage information
    day = getattr(result, 'day', None)
    growth_stage = getattr(result, 'growth_stage', None)
    total_biomass = getattr(result, 'total_biomass', None)
    
    # Get stress factors if available
    water_stress = getattr(result, 'water_stress', None)
    temperature_stress = getattr(result, 'temperature_stress_factor', None)
    integrated_stress = getattr(result, 'integrated_stress_factor', None)
    
    # For output purposes, use defaults if parameters are missing
    if not strict_validation:
        day = day if day is not None else 1
        growth_stage = growth_stage if growth_stage is not None else 'V4'
        total_biomass = total_biomass if total_biomass is not None else 1.0
        water_stress = water_stress if water_stress is not None else 0.0
        temperature_stress = temperature_stress if temperature_stress is not None else 0.0
        integrated_stress = integrated_stress if integrated_stress is not None else 0.0
    else:
        # Validate that required parameters are provided
        if day is None:
            raise ValueError("❌ 'day' parameter must be provided in CSV configuration - no hardcoded defaults allowed")
        if growth_stage is None:
            raise ValueError("❌ 'growth_stage' parameter must be provided in CSV configuration - no hardcoded defaults allowed")
        if total_biomass is None:
            raise ValueError("❌ 'total_biomass' parameter must be provided in CSV configuration - no hardcoded defaults allowed")
        if water_stress is None:
            raise ValueError("❌ 'water_stress' parameter must be provided in CSV configuration - no hardcoded defaults allowed")
        if temperature_stress is None:
            raise ValueError("❌ 'temperature_stress_factor' parameter must be provided in CSV configuration - no hardcoded defaults allowed")
        if integrated_stress is None:
            raise ValueError("❌ 'integrated_stress_factor' parameter must be provided in CSV configuration - no hardcoded defaults allowed")
    
    # Base dry matter content by plant part (mature, unstressed conditions)
    base_dry_matter = {
        'leaf': 0.06,    # Young lettuce leaves: 5-7%
        'stem': 0.05,    # Lettuce stems/petioles: 4-6% 
        'shoot': 0.055,  # Combined shoot
        'root': 0.09     # Root tissue: 8-10%
    }
    
    # Development factor: young plants have higher water content (lower dry matter)
    if day <= 10:
        development_factor = 0.7 + (day / 10) * 0.3  # 70-100% of mature dry matter
    elif day <= 30:
        development_factor = 1.0  # Peak dry matter content
    else:
        development_factor = 1.0 + min(0.2, (day - 30) * 0.005)  # Slight increase with age
    
    # Growth stage factor: different stages accumulate water differently
    stage_factors = {
        'VE': 0.6, 'V1': 0.7, 'V2': 0.8, 'V3': 0.85, 'V4': 0.9,
        'V5': 0.95, 'V6': 1.0, 'V7': 1.0, 'V8': 1.0, 'V9': 1.0, 'V10': 1.0,
        'V11+': 1.05, 'HI': 1.1, 'HD': 1.15, 'HM': 1.2  # Head formation increases dry matter
    }
    stage_factor = stage_factors.get(growth_stage, 1.0)
    
    # Stress effects on water content
    # Water stress increases dry matter content (less water uptake)
    water_stress_factor = 1.0 + water_stress * 0.3  # Up to 30% increase in dry matter
    
    # Temperature stress affects cellular water content
    temp_stress_factor = 1.0 + temperature_stress * 0.2  # Up to 20% increase
    
    # Integrated stress combines all factors
    stress_factor = 1.0 + integrated_stress * 0.25  # Up to 25% increase
    
    # Growth rate factor: fast growing tissue has more water
    biomass_growth_rate = total_biomass / max(1, day)  # g/day
    if biomass_growth_rate > 3.0:  # Fast growth
        growth_rate_factor = 0.9
    elif biomass_growth_rate < 1.0:  # Slow growth
        growth_rate_factor = 1.1
    else:
        growth_rate_factor = 1.0
    
    # Plant part specific adjustments
    part_adjustment = {
        'leaf': 1.0,     # Base reference
        'stem': 0.85,    # Stems have more water (petioles, midribs)
        'shoot': 0.92,   # Combined shoot average
        'root': 1.5      # Roots have much higher dry matter content
    }
    
    # Calculate final dry matter content
    base_dm = base_dry_matter.get(plant_part, 0.06)
    
    final_dry_matter = (base_dm * 
                       development_factor * 
                       stage_factor * 
                       water_stress_factor * 
                       temp_stress_factor * 
                       stress_factor * 
                       growth_rate_factor * 
                       part_adjustment.get(plant_part, 1.0))
    
    # Biological limits: lettuce dry matter content ranges
    if plant_part == 'root':
        final_dry_matter = max(0.07, min(0.15, final_dry_matter))  # 7-15% for roots
    else:
        final_dry_matter = max(0.035, min(0.10, final_dry_matter))  # 3.5-10% for shoots
    
    return final_dry_matter


"""
=== FUNCTION EXPLANATIONS ===

This file defines the data structures and configuration for the hydroponic simulation system. 
Think of it as the digital blueprint and result storage system for your hydroponic farm. 
It's like having a comprehensive logbook that records every detail about your growing system, 
from the physical setup to daily plant measurements.

KEY DATA STRUCTURES AND THEIR PURPOSE:

1. HydroSystemConfig
   - What it does: Stores the physical specifications of your hydroponic system
   - Contains: tank size, flow rate, system type, growing area, number of plants
   - Real-world meaning: Like the specifications sheet for your hydroponic system - tells you 
     the tank capacity, pump flow rate, whether it's NFT/DWC/Aeroponics, and how many plants 
     it can grow.

2. CropParameters
   - What it does: Stores plant-specific characteristics for the crop being grown
   - Contains: crop coefficients, plant height, root depth, leaf area index
   - Real-world meaning: Like a plant profile card that describes how big the plant gets, 
     how much water it needs, and its growing characteristics. Different crops (lettuce, 
     tomatoes, herbs) have different profiles.

3. WeatherData
   - What it does: Stores daily environmental conditions
   - Contains: temperature (min/max/average), solar radiation, humidity, wind speed
   - Real-world meaning: Like a weather station log that records all the environmental 
     conditions that affect plant growth. This data drives the simulation calculations.

4. DailyResults
   - What it does: Stores all the calculated results for each day of simulation
   - Contains: Over 100+ different measurements and calculations
   - Real-world meaning: Like a comprehensive daily report card for your plants, recording 
     everything from how much water they drank to how much they grew, their stress levels, 
     and nutrient concentrations.

5. SimulationResults
   - What it does: Combines all daily results into a complete simulation report
   - Contains: All daily data plus summary statistics and metadata
   - Real-world meaning: Like a complete grow cycle report that documents the entire 
     journey from planting to harvest, with detailed analytics and summaries.

KEY FUNCTIONS AND CALCULATIONS:

6. to_dataframe()
   - What it does: Converts simulation results into a spreadsheet format for analysis
   - Process: Takes all daily results and organizes them into logical groups
   - Groups created:
     * Experiment metadata (dates, system info, treatment IDs)
     * Environmental conditions (temperature, light, humidity)
     * Water dynamics (consumption, transpiration, tank levels)
     * Solution chemistry (pH, EC, nutrient concentrations)
     * Plant development (growth stages, leaf number, biomass)
     * Stress factors (temperature, water, nutrient stress)
     * Root architecture (root length, surface area, activity)
     * Photosynthesis details (carbon fixation rates, efficiency)
     * Respiration details (energy consumption by plant parts)
   - Real-world meaning: Like converting a messy pile of daily logs into an organized 
     spreadsheet where you can easily analyze trends, compare treatments, and identify 
     optimal growing conditions.

7. calculate_summary_stats()
   - What it does: Calculates key performance indicators for the entire grow cycle
   - Metrics calculated:
     * Total water consumption
     * Average daily consumption
     * Tank volume changes
     * Temperature extremes
     * Water use efficiency
   - Real-world meaning: Like calculating your farm's efficiency report card - how much 
     water did you use per kilogram of crop produced? What were the temperature extremes? 
     How efficiently did your system operate?

8. calculate_dynamic_dry_matter_content()
   - What it does: Calculates what percentage of the plant is dry matter vs. water
   - Factors considered:
     * Plant age (young plants have more water)
     * Growth stage (different stages accumulate water differently)
     * Environmental stress (stress increases dry matter concentration)
     * Plant part (leaves vs stems vs roots have different water content)
     * Growth rate (fast growth = more water content)
   - Equation: final_dry_matter = base × development × stage × stress × growth_rate × part_adjustment
   - Real-world meaning: Like knowing that fresh lettuce is about 95% water and 5% dry matter, 
     but this ratio changes based on growing conditions. Young, fast-growing lettuce under 
     ideal conditions might be 97% water, while stressed, mature lettuce might be 90% water.

SIMULATION DATA ORGANIZATION:

The simulation tracks over 100 different variables organized into functional groups:

**Environmental Monitoring:**
- Air temperature, humidity, CO2 levels
- Solar radiation and light conditions
- VPD (Vapor Pressure Deficit) - the "thirst" of the air

**Plant Development:**
- Growth stages (V1, V2, V3... through harvest)
- Leaf number and size
- Plant height and biomass accumulation
- Root development and architecture

**Physiological Processes:**
- Photosynthesis rates and efficiency
- Respiration (energy consumption)
- Transpiration (water loss through leaves)
- Nutrient uptake rates

**Solution Chemistry:**
- pH levels and automatic control
- EC (electrical conductivity) - nutrient concentration
- Individual nutrient concentrations (N, P, K, Ca, Mg, etc.)
- Buffer capacity and chemical changes

**Stress Monitoring:**
- Temperature stress (heat and cold)
- Water stress (drought conditions)
- Nutrient stress (deficiencies)
- Integrated stress interactions

**System Performance:**
- Water consumption and efficiency
- Tank level changes
- Flow rates and circulation
- Energy costs for environmental control

PRACTICAL APPLICATIONS:

For Hydroponic Growers:
1. **Performance Tracking**: Monitor daily plant growth and system efficiency
2. **Problem Diagnosis**: Identify stress factors and their impacts on growth
3. **Optimization**: Compare different growing conditions to find optimal settings
4. **Yield Prediction**: Predict harvest timing and expected yields
5. **Resource Management**: Track water and nutrient consumption
6. **Quality Control**: Monitor factors affecting crop quality

For Researchers:
1. **Experiment Design**: Set up controlled experiments with different treatments
2. **Data Analysis**: Export data to spreadsheets for statistical analysis
3. **Model Validation**: Compare simulation results with real measurements
4. **Parameter Calibration**: Adjust model parameters based on experimental data
5. **Publication**: Generate comprehensive datasets for scientific papers

For System Designers:
1. **Sizing Systems**: Determine optimal tank size, pump capacity, growing area
2. **Performance Prediction**: Predict how systems will perform under different conditions
3. **Cost Analysis**: Calculate operational costs for water, nutrients, energy
4. **Automation Design**: Design control systems based on plant response patterns
5. **Scale-up Planning**: Use small-scale data to design larger commercial systems

DATA EXPORT AND ANALYSIS:

The system exports data with intelligent column organization:
- **Grouped by function**: Related measurements are grouped together
- **Standardized units**: Consistent units throughout (mg/L, cm, g, etc.)
- **Time series**: Daily progression from planting to harvest
- **Treatment comparison**: Multiple treatments can be compared side-by-side
- **Statistical ready**: Data formatted for statistical analysis software

BIOLOGICAL ACCURACY:

The simulation captures realistic plant responses:
- **Dry matter content**: Lettuce typically 4-6% dry matter, varies with conditions
- **Growth patterns**: Follows real lettuce development from seedling to harvest
- **Stress responses**: Models how plants actually respond to environmental stress
- **Nutrient dynamics**: Based on real nutrient uptake kinetics and plant physiology
- **Water use**: Reflects actual transpiration patterns and water use efficiency

KEY CONCEPTS FOR NON-CODERS:

Data Structure: The organized way information is stored in the computer, like filing 
cabinets with specific folders for different types of information.

Metadata: Information about information - like writing the date, location, and 
experimental conditions on a research notebook page.

Time Series Data: Information collected over time, like daily temperature readings 
or weekly plant measurements, that shows how things change.

Data Validation: Checking that all required information is present and makes sense, 
like proofreading a form before submitting it.

Export Format: Converting computer data into formats (like spreadsheets) that 
humans can easily read and analyze.

Dynamic Calculation: Values that change based on current conditions rather than 
being fixed constants, like how your car's fuel efficiency changes with driving 
conditions.

This hydroponic system data structure provides a comprehensive framework for 
recording, analyzing, and understanding every aspect of plant growth in controlled 
environment agriculture, enabling precise management and optimization of growing 
conditions for maximum productivity and resource efficiency.
"""