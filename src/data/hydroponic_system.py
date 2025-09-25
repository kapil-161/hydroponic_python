\from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import pandas as pd
import math

# =========================
# Hydroponic System Data Classes and Configuration
# =========================

class SystemType(Enum):
    """Enum for hydroponic system types."""
    NFT = "NFT"
    DWC = "DWC"
    AERO = "AERO"
    WICK = "WICK"
    EBB = "EBB"

@dataclass
class HydroSystemConfig:
    """Configuration for hydroponic system parameters."""
    system_id: str
    crop_id: str
    location_id: str
    tank_volume: float  # L
    flow_rate: float   # L/h
    system_type: str   # NFT, DWC, AERO, WICK, EBB
    system_area: float # m²
    n_plants: int
    description: str

    def __post_init__(self):
        """Validate system configuration parameters."""
        if not all(isinstance(x, str) and x.strip() for x in [self.system_id, self.crop_id, self.location_id, self.description]):
            raise ValueError("System ID, crop ID, location ID, and description must be non-empty strings")
        if self.tank_volume < 0:
            raise ValueError("Tank volume must be non-negative")
        if self.flow_rate < 0:
            raise ValueError("Flow rate must be non-negative")
        if self.system_area <= 0:
            raise ValueError("System area must be positive")
        if self.n_plants < 0:
            raise ValueError("Number of plants must be non-negative")
        if self.system_type not in [e.value for e in SystemType]:
            raise ValueError(f"System type must be one of {[e.value for e in SystemType]}")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'HydroSystemConfig':
        """Create configuration from dictionary."""
        required_fields = ['system_id', 'crop_id', 'location_id', 'tank_volume', 'flow_rate',
                          'system_type', 'system_area', 'n_plants', 'description']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required configuration field: {field}")
        return cls(
            system_id=str(config['system_id']),
            crop_id=str(config['crop_id']),
            location_id=str(config['location_id']),
            tank_volume=float(config['tank_volume']),
            flow_rate=float(config['flow_rate']),
            system_type=str(config['system_type']),
            system_area=float(config['system_area']),
            n_plants=int(config['n_plants']),
            description=str(config['description'])
        )

@dataclass
class CropParameters:
    """Crop-specific parameters."""
    crop_id: str
    crop_name: str
    kcb: float        # Basal crop coefficient
    phi: float        # Density index
    crop_height: float # m
    root_zone_depth: float # m
    lai: float        # Leaf area index

    def __post_init__(self):
        """Validate crop parameters."""
        if not all(isinstance(x, str) and x.strip() for x in [self.crop_id, self.crop_name]):
            raise ValueError("Crop ID and name must be non-empty strings")
        if self.kcb <= 0:
            raise ValueError("Basal crop coefficient must be positive")
        if self.phi <= 0:
            raise ValueError("Density index must be positive")
        if self.crop_height <= 0:
            raise ValueError("Crop height must be positive")
        if self.root_zone_depth <= 0:
            raise ValueError("Root zone depth must be positive")
        if self.lai < 0:
            raise ValueError("Leaf area index must be non-negative")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'CropParameters':
        """Create crop parameters from dictionary."""
        required_fields = ['crop_id', 'crop_name', 'kcb', 'phi', 'crop_height', 'root_zone_depth', 'lai']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required configuration field: {field}")
        return cls(
            crop_id=str(config['crop_id']),
            crop_name=str(config['crop_name']),
            kcb=float(config['kcb']),
            phi=float(config['phi']),
            crop_height=float(config['crop_height']),
            root_zone_depth=float(config['root_zone_depth']),
            lai=float(config['lai'])
        )

@dataclass
class WeatherData:
    """Daily weather data."""
    date: datetime
    temp_avg: float  # °C
    temp_min: float  # °C
    temp_max: float  # °C
    solar_radiation: float  # MJ/m²/day
    rel_humidity: float     # %
    wind_speed: float       # m/s
    rainfall: Optional[float] = None  # mm

    def __post_init__(self):
        """Validate weather data."""
        if not isinstance(self.date, datetime):
            raise ValueError("Date must be a datetime object")
        if not -50 <= self.temp_avg <= 60 or not -50 <= self.temp_min <= 60 or not -50 <= self.temp_max <= 60:
            raise ValueError("Temperatures must be between -50 and 60°C")
        if self.temp_min > self.temp_max:
            raise ValueError("Minimum temperature cannot exceed maximum temperature")
        if self.solar_radiation < 0:
            raise ValueError("Solar radiation must be non-negative")
        if not 0 <= self.rel_humidity <= 100:
            raise ValueError("Relative humidity must be between 0 and 100%")
        if self.wind_speed < 0:
            raise ValueError("Wind speed must be non-negative")
        if self.rainfall is not None and self.rainfall < 0:
            raise ValueError("Rainfall must be non-negative")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'WeatherData':
        """Create weather data from dictionary."""
        required_fields = ['date', 'temp_avg', 'temp_min', 'temp_max', 'solar_radiation', 'rel_humidity', 'wind_speed']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required weather data field: {field}")
        return cls(
            date=pd.to_datetime(config['date']),
            temp_avg=float(config['temp_avg']),
            temp_min=float(config['temp_min']),
            temp_max=float(config['temp_max']),
            solar_radiation=float(config['solar_radiation']),
            rel_humidity=float(config['rel_humidity']),
            wind_speed=float(config['wind_speed']),
            rainfall=float(config['rainfall']) if config.get('rainfall') is not None else None
        )

@dataclass
class HydroInputData:
    """Complete input data for hydroponic simulation."""
    system_config: HydroSystemConfig
    crop_params: CropParameters
    weather_data: List[WeatherData]
    nutrient_params: Dict[str, float] = field(default_factory=dict)
    simulation_days: int = field(default=30)

    def __post_init__(self):
        """Validate input data."""
        if not isinstance(self.system_config, HydroSystemConfig):
            raise ValueError("System config must be a HydroSystemConfig instance")
        if not isinstance(self.crop_params, CropParameters):
            raise ValueError("Crop parameters must be a CropParameters instance")
        if not self.weather_data or not all(isinstance(w, WeatherData) for w in self.weather_data):
            raise ValueError("Weather data must be a non-empty list of WeatherData instances")
        if not isinstance(self.nutrient_params, dict):
            raise ValueError("Nutrient parameters must be a dictionary")
        if self.simulation_days <= 0:
            raise ValueError("Simulation days must be positive")

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
    ph: Optional[float] = None  # Solution pH
    ec: Optional[float] = None  # dS/m
    rzt: Optional[float] = None  # Root zone temperature (°C)
    rzt_growth_factor: Optional[float] = None  # RZT growth effect
    rzt_nutrient_factor: Optional[float] = None  # RZT nutrient uptake effect
    v_stage: Optional[float] = None  # Vegetative stage (number of leaves)
    leaf_number: Optional[int] = None  # Current number of active leaves
    leaf_area_m2: Optional[float] = None  # Total leaf area per plant (m²)
    average_leaf_area_cm2: Optional[float] = None  # Average leaf area (cm²)
    co2_concentration: Optional[float] = None  # CO2 concentration (μmol/mol)
    vpd_actual: Optional[float] = None  # Actual VPD (kPa)
    env_photosynthesis_factor: Optional[float] = None  # Environmental photosynthesis enhancement
    env_transpiration_factor: Optional[float] = None  # Environmental transpiration factor
    # Photosynthesis model results
    vcmax_25: Optional[float] = None  # Maximum carboxylation rate at 25°C (μmol/m²/s)
    jmax_25: Optional[float] = None  # Maximum electron transport rate at 25°C (μmol/m²/s)
    quantum_efficiency: Optional[float] = None  # Quantum efficiency of photosystem II
    rubisco_limited: Optional[float] = None  # Rubisco-limited photosynthesis rate
    light_limited: Optional[float] = None  # Light-limited photosynthesis rate
    co2_compensation: Optional[float] = None  # CO2 compensation point (μmol/mol)
    intercellular_co2: Optional[float] = None  # Intercellular CO2 concentration
    # Respiration model results
    maintenance_resp_leaves: Optional[float] = None  # Leaf maintenance respiration
    maintenance_resp_stems: Optional[float] = None  # Stem maintenance respiration
    maintenance_resp_roots: Optional[float] = None  # Root maintenance respiration
    growth_resp_leaves: Optional[float] = None  # Leaf growth respiration
    growth_resp_stems: Optional[float] = None  # Stem growth respiration
    growth_resp_roots: Optional[float] = None  # Root growth respiration
    temperature_acclimation: Optional[float] = None  # Temperature acclimation factor
    age_factor: Optional[float] = None  # Age effects on respiration
    # Root architecture results
    fine_root_length: Optional[float] = None  # Fine root length (cm)
    coarse_root_length: Optional[float] = None  # Coarse root length (cm)
    root_cohorts: Optional[int] = None  # Number of active root cohorts
    root_activity_young: Optional[float] = None  # Activity of young roots
    root_activity_old: Optional[float] = None  # Activity of old roots
    root_surface_active: Optional[float] = None  # Active root surface area (cm²)
    root_turnover_rate: Optional[float] = None  # Daily root turnover rate
    # Canopy architecture results
    sunlit_lai: Optional[float] = None  # Sunlit leaf area index
    shaded_lai: Optional[float] = None  # Shaded leaf area index
    canopy_layers: Optional[int] = None  # Number of canopy layers
    ppfd_top: Optional[float] = None  # PPFD at top of canopy (μmol/m²/s)
    ppfd_bottom: Optional[float] = None  # PPFD at bottom of canopy (μmol/m²/s)
    light_extinction: Optional[float] = None  # Light extinction coefficient
    # Nitrogen dynamics results
    n_pool_structural: Optional[float] = None  # Structural nitrogen pool (g)
    n_pool_metabolic: Optional[float] = None  # Metabolic nitrogen pool (g)
    n_pool_storage: Optional[float] = None  # Storage nitrogen pool (g)
    n_pool_transport: Optional[float] = None  # Transport nitrogen pool (g)
    n_remobilization: Optional[float] = None  # Daily N remobilization (g)
    n_critical_conc: Optional[float] = None  # Critical nitrogen concentration
    # Stress integration results
    stress_interactions: Dict[str, float] = field(default_factory=dict)
    acclimation_levels: Dict[str, float] = field(default_factory=dict)
    cumulative_damage: Dict[str, float] = field(default_factory=dict)
    # Crop growth model results
    cultivar_adaptation_index: Optional[float] = None
    cultivar_yield_potential: Optional[float] = None
    genetic_photosynthesis_capacity: Optional[float] = None
    genetic_ec_tolerance: Optional[float] = None
    genetic_nitrate_efficiency: Optional[float] = None
    accumulated_gdd: Optional[float] = None
    development_rate: Optional[float] = None
    growth_stage: Optional[str] = None
    thermal_time_daily: Optional[float] = None
    is_vegetative: Optional[bool] = None
    is_reproductive: Optional[bool] = None
    total_biomass: Optional[float] = None
    leaf_biomass: Optional[float] = None
    stem_biomass: Optional[float] = None
    root_biomass: Optional[float] = None
    daily_growth_rate: Optional[float] = None
    leaf_growth_rate: Optional[float] = None
    stem_growth_rate: Optional[float] = None
    root_growth_rate: Optional[float] = None
    lai: Optional[float] = None
    canopy_height_cm: Optional[float] = None
    light_interception: Optional[float] = None
    total_absorbed_ppfd: Optional[float] = None
    canopy_photosynthesis: Optional[float] = None
    photosynthesis_rate: Optional[float] = None
    net_assimilation: Optional[float] = None
    maintenance_respiration: Optional[float] = None
    growth_respiration: Optional[float] = None
    respiration_rate: Optional[float] = None
    root_surface_area: Optional[float] = None
    root_length_density: Optional[float] = None
    root_volume: Optional[float] = None
    nitrogen_uptake_mg: Optional[float] = None
    nitrogen_demand_mg: Optional[float] = None
    nitrogen_stress_factor: Optional[float] = None
    leaf_nitrogen_conc: Optional[float] = None
    root_nitrogen_conc: Optional[float] = None
    nitrogen_remobilization: Optional[float] = None
    phosphorus_uptake_mg: Optional[float] = None
    potassium_uptake_mg: Optional[float] = None
    phosphorus_remobilization: Optional[float] = None
    potassium_remobilization: Optional[float] = None
    senescence_rate: Optional[float] = None
    leaf_senescence_rate: Optional[float] = None
    integrated_stress_factor: Optional[float] = None
    temperature_stress_level: Optional[float] = None
    temperature_stress_photosynthesis: Optional[float] = None
    temperature_stress_growth: Optional[float] = None
    water_stress: Optional[float] = None
    nutrient_stress: Optional[float] = None
    salinity_stress: Optional[float] = None
    controlled_temperature: Optional[float] = None
    controlled_humidity: Optional[float] = None
    controlled_co2: Optional[float] = None
    vpd_target: Optional[float] = None
    environmental_cost: Optional[float] = None
    cold_stress_factor: Optional[float] = None
    heat_stress_factor: Optional[float] = None
    temperature_stress_factor: Optional[float] = None
    solution_ph: Optional[float] = None
    ph_change_from_uptake: Optional[float] = None
    ph_change_from_drift: Optional[float] = None
    acid_dosed_ml_per_L: Optional[float] = None
    base_dosed_ml_per_L: Optional[float] = None
    buffer_capacity: Optional[float] = None
    phosphate_h2po4_mg_L: Optional[float] = None
    phosphate_hpo4_mg_L: Optional[float] = None
    phosphate_po4_mg_L: Optional[float] = None
    nutrient_precipitation_mg_L: Optional[float] = None
    solution_ec: Optional[float] = None
    rzt_water_factor: Optional[float] = None
    rzt_photosynthesis_factor: Optional[float] = None
    rzt_root_metabolism_factor: Optional[float] = None
    rzt_stress_factor: Optional[float] = None
    rzt_optimal_factor: Optional[float] = None
    rzt_daily_range: Optional[float] = None
    individual_rzt_factors: Dict[str, float] = field(default_factory=dict)
    root_temp_stress: Optional[float] = None
    senesced_area: Optional[float] = None
    senesced_biomass: Optional[float] = None
    average_senescence_stage: Optional[str] = None
    active_senescence_types: List[str] = field(default_factory=list)
    remobilization_pool: Dict[str, float] = field(default_factory=dict)
    ph_stress: Optional[float] = None
    oxygen_stress: Optional[float] = None
    stress_severity: Optional[str] = None
    dominant_stresses: List[str] = field(default_factory=list)
    stress_interactions_active: List[str] = field(default_factory=list)
    acclimation_active: List[str] = field(default_factory=list)
    recovery_active: List[str] = field(default_factory=list)
    total_damage: Optional[float] = None
    nutrient_transport_fluxes: Dict[str, float] = field(default_factory=dict)
    transport_limitations: List[str] = field(default_factory=list)
    mobility_efficiency: Dict[str, float] = field(default_factory=dict)
    nutrient_redistribution: Dict[str, float] = field(default_factory=dict)
    transport_pool_fractions: Dict[str, float] = field(default_factory=dict)
    cumulative_redistribution: Dict[str, float] = field(default_factory=dict)
    henderson_hasselbalch_ph: Optional[float] = None
    controlled_ph: Optional[float] = None
    acid_dosing_rate: Optional[float] = None
    base_dosing_rate: Optional[float] = None

    def __post_init__(self):
        """Validate core daily results fields."""
        if not isinstance(self.date, datetime):
            raise ValueError("Date must be a datetime object")
        if self.day < 0:
            raise ValueError("Day must be non-negative")
        if any(x < 0 for x in [self.eto_ref, self.etc_prime, self.transpiration, self.water_uptake_total, self.tank_volume] if x is not None):
            raise ValueError("Water-related fields must be non-negative")
        if not -50 <= self.temp_avg <= 60:
            raise ValueError("Average temperature must be between -50 and 60°C")
        if self.solar_radiation < 0:
            raise ValueError("Solar radiation must be non-negative")
        if self.vpd < 0:
            raise ValueError("VPD must be non-negative")
        if self.water_use_efficiency < 0:
            raise ValueError("Water use efficiency must be non-negative")
        if self.ph is not None and not 0 <= self.ph <= 14:
            raise ValueError("pH must be between 0 and 14")
        if self.ec is not None and self.ec < 0:
            raise ValueError("EC must be non-negative")
        if self.rzt is not None and not -10 <= self.rzt <= 50:
            raise ValueError("Root zone temperature must be between -10 and 50°C")

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
    transplanting_period_days: int
    treatment_id: Optional[str] = None
    summary_stats: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate simulation results."""
        if not all(isinstance(x, str) and x.strip() for x in [self.system_id, self.crop_id, self.location_id]):
            raise ValueError("System ID, crop ID, and location ID must be non-empty strings")
        if not isinstance(self.start_date, datetime) or not isinstance(self.end_date, datetime):
            raise ValueError("Start and end dates must be datetime objects")
        if self.start_date > self.end_date:
            raise ValueError("Start date must precede end date")
        if self.total_days <= 0:
            raise ValueError("Total days must be positive")
        if not self.daily_results or not all(isinstance(d, DailyResults) for d in self.daily_results):
            raise ValueError("Daily results must be a non-empty list of DailyResults instances")
        if self.transplanting_period_days < 0:
            raise ValueError("Transplanting period days must be non-negative")
        if self.treatment_id is not None and not isinstance(self.treatment_id, str):
            raise ValueError("Treatment ID must be a string or None")

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame for analysis."""
        data = []
        for result in self.daily_results:
            das = result.day + self.transplanting_period_days
            dat = result.day
            row = {
                # Experiment metadata
                'Date': result.date.strftime('%Y-%m-%d'),
                'Day': result.day,
                'DAS': das,
                'DAT': dat,
                'Treatment_ID': self.treatment_id or 'DEFAULT',
                'System_ID': self.system_id,
                'Crop_ID': self.crop_id,
                'Location_ID': self.location_id,
                # Environmental conditions
                'Temp_C': result.temp_avg,
                'Solar_Rad_MJ': result.solar_radiation,
                'VPD_kPa': result.vpd,
                'CO2_umol_mol': result.co2_concentration,
                # Water dynamics
                'ETO_Ref_mm': result.eto_ref,
                'ETC_Prime_mm': result.etc_prime,
                'Transpiration_mm': result.transpiration,
                'Water_Total_L': result.water_uptake_total,
                'Tank_Volume_L': result.tank_volume,
                'WUE_L_kg': result.water_use_efficiency,
                # Solution chemistry
                'pH': result.ph,
                'EC': result.ec,
                'pH_Change_Uptake': result.ph_change_from_uptake,
                'pH_Drift': result.ph_change_from_drift,
                'Acid_Dosed_mL_L': result.acid_dosed_ml_per_L,
                'Base_Dosed_mL_L': result.base_dosed_ml_per_L,
                'Buffer_Capacity': result.buffer_capacity,
                # Nutrient concentrations
                'N-NO3_mg_L': result.nutrient_concentrations.get('N-NO3', 0.0),
                'P-PO4_mg_L': result.nutrient_concentrations.get('P-PO4', 0.0),
                'K_mg_L': result.nutrient_concentrations.get('K', 0.0),
                'Ca_mg_L': result.nutrient_concentrations.get('Ca', 0.0),
                'Mg_mg_L': result.nutrient_concentrations.get('Mg', 0.0),
                # Root zone conditions
                'RZT_C': result.rzt,
                'RZT_Growth_Factor': result.rzt_growth_factor,
                'RZT_Nutrient_Factor': result.rzt_nutrient_factor,
                'Env_Photo_Factor': result.env_photosynthesis_factor,
                'Env_Transp_Factor': result.env_transpiration_factor,
                # Plant development
                'V_Stage': result.v_stage,
                'Leaf_Number': result.leaf_number,
                'Leaf_Area_m2': result.leaf_area_m2,
                'Avg_Leaf_Area_cm2': result.average_leaf_area_cm2,
                'Growth_Stage': result.growth_stage,
                'Total_Biomass_g': result.total_biomass,
                'LAI': result.lai,
                'Plant_Height_cm': result.canopy_height_cm,
                'Daily_Growth_Rate_g_day': result.daily_growth_rate,
                # Stress factors
                'Integrated_Stress': result.integrated_stress_factor,
                'Temperature_Stress': result.temperature_stress_level,
                'Water_Stress': result.water_stress,
                'Nutrient_Stress': result.nutrient_stress,
                'Nitrogen_Stress': result.nitrogen_stress_factor,
                'Salinity_Stress': result.salinity_stress,
                # Biomass components
                'Shoot_Dry_Weight_g': (result.leaf_biomass or 0.0) + (result.stem_biomass or 0.0),
                'Leaf_Dry_Weight_g': result.leaf_biomass,
                'Stem_Dry_Weight_g': result.stem_biomass,
                'Root_Dry_Weight_g': result.root_biomass,
                'Shoot_Fresh_Weight_g': ((result.leaf_biomass or 0.0) + (result.stem_biomass or 0.0)) / calculate_dynamic_dry_matter_content(result, 'shoot', strict_validation=True) if result.leaf_biomass and result.stem_biomass else None,
                'Leaf_Fresh_Weight_g': result.leaf_biomass / calculate_dynamic_dry_matter_content(result, 'leaf', strict_validation=True) if result.leaf_biomass else None,
                'Stem_Fresh_Weight_g': result.stem_biomass / calculate_dynamic_dry_matter_content(result, 'stem', strict_validation=True) if result.stem_biomass else None,
                'Root_Fresh_Weight_g': result.root_biomass / calculate_dynamic_dry_matter_content(result, 'root', strict_validation=True) if result.root_biomass else None,
                'Leaf_Growth_Rate_g_day': result.leaf_growth_rate,
                'Stem_Growth_Rate_g_day': result.stem_growth_rate,
                'Root_Growth_Rate_g_day': result.root_growth_rate,
                # Root architecture
                'Fine_Root_Length_cm': result.fine_root_length,
                'Coarse_Root_Length_cm': result.coarse_root_length,
                'Root_Length_Density_cm_cm3': result.root_length_density,
                'Root_Surface_Area_cm2': result.root_surface_area,
                'Root_Volume_cm3': result.root_volume,
                'Root_Cohorts': result.root_cohorts,
                'Root_Activity_Young': result.root_activity_young,
                'Root_Activity_Old': result.root_activity_old,
                'Root_Surface_Active_cm2': result.root_surface_active,
                'Root_Turnover_Rate': result.root_turnover_rate,
                # Photosynthesis
                'Vcmax_25_umol_m2_s': result.vcmax_25,
                'Jmax_25_umol_m2_s': result.jmax_25,
                'Quantum_Efficiency': result.quantum_efficiency,
                'Rubisco_Limited_umol_m2_s': result.rubisco_limited,
                'Light_Limited_umol_m2_s': result.light_limited,
                'CO2_Compensation_umol_mol': result.co2_compensation,
                'Intercellular_CO2_umol_mol': result.intercellular_co2,
                'Photosynthesis_Rate': result.photosynthesis_rate,
                'Net_Assimilation': result.net_assimilation,
                # Respiration
                'Maintenance_Respiration': result.maintenance_respiration,
                'Growth_Respiration': result.growth_respiration,
                'Respiration_Rate': result.respiration_rate,
                'Maint_Resp_Leaves': result.maintenance_resp_leaves,
                'Maint_Resp_Stems': result.maintenance_resp_stems,
                'Maint_Resp_Roots': result.maintenance_resp_roots,
                'Growth_Resp_Leaves': result.growth_resp_leaves,
                'Growth_Resp_Stems': result.growth_resp_stems,
                'Growth_Resp_Roots': result.growth_resp_roots,
                'Temperature_Acclimation': result.temperature_acclimation,
                'Age_Factor': result.age_factor,
                # Canopy
                'Light_Interception': result.light_interception,
                'Sunlit_LAI': result.sunlit_lai,
                'Shaded_LAI': result.shaded_lai,
                'Total_Absorbed_PPFD_umol_m2_s': result.total_absorbed_ppfd,
                'Canopy_Photosynthesis_umol_m2_s': result.canopy_photosynthesis,
                'Canopy_Layers': result.canopy_layers,
                'PPFD_Top_umol_m2_s': result.ppfd_top,
                'PPFD_Bottom_umol_m2_s': result.ppfd_bottom,
                'Light_Extinction_Coeff': result.light_extinction,
                # Nitrogen dynamics
                'N_Pool_Structural_g': result.n_pool_structural,
                'N_Pool_Metabolic_g': result.n_pool_metabolic,
                'N_Pool_Storage_g': result.n_pool_storage,
                'N_Pool_Transport_g': result.n_pool_transport,
                'N_Remobilization_g': result.n_remobilization,
                'N_Critical_Conc': result.n_critical_conc,
                'Nitrogen_Uptake_mg': result.nitrogen_uptake_mg,
                'Nitrogen_Demand_mg': result.nitrogen_demand_mg,
                'Leaf_Nitrogen_Conc': result.leaf_nitrogen_conc,
                'Root_Nitrogen_Conc': result.root_nitrogen_conc,
                'Nitrogen_Remobilization': result.nitrogen_remobilization,
                # Other nutrients
                'Phosphorus_Uptake_mg': result.phosphorus_uptake_mg,
                'Phosphorus_Remobilization': result.phosphorus_remobilization,
                'Potassium_Remobilization': result.potassium_remobilization,
                # Senescence
                'Senescence_Rate': result.senescence_rate,
                'Leaf_Senescence_Rate': result.leaf_senescence_rate,
                # Detailed stress
                'Temperature_Stress_Photosynthesis': result.temperature_stress_photosynthesis,
                'Temperature_Stress_Growth': result.temperature_stress_growth,
                'Cold_Stress_Factor': result.cold_stress_factor,
                'Heat_Stress_Factor': result.heat_stress_factor,
                'Temperature_Stress_Factor': result.temperature_stress_factor,
                # Environmental control
                'Controlled_Humidity_pct': result.controlled_humidity,
                'VPD_Target_kPa': result.vpd_target,
                'Environmental_Cost': result.environmental_cost,
                # pH modeling
                'Phosphate_H2PO4_mg_L': result.phosphate_h2po4_mg_L,
                'Phosphate_HPO4_mg_L': result.phosphate_hpo4_mg_L,
                'Nutrient_Precipitation_mg_L': result.nutrient_precipitation_mg_L
            }
            # Stress interactions
            for stress_type, value in result.stress_interactions.items():
                row[f'Stress_Interaction_{stress_type}'] = value
            for stress_type, value in result.acclimation_levels.items():
                row[f'Acclimation_{stress_type}'] = value
            for stress_type, value in result.cumulative_damage.items():
                row[f'Cumulative_Damage_{stress_type}'] = value
            # Round floats to 2 decimal places
            for key, value in row.items():
                if isinstance(value, float):
                    row[key] = round(value, 2) if value is not None else None
            data.append(row)

        df = pd.DataFrame(data)
        # Ensure consistent numeric formatting
        for col in df.columns:
            if df[col].dtype in ['float64', 'float32']:
                df[col] = df[col].round(2)
        return df

    def calculate_summary_stats(self) -> Dict[str, float]:
        """Calculate summary statistics for the simulation."""
        df = self.to_dataframe()
        self.summary_stats = {
            'total_water_consumption_L': df['Water_Total_L'].sum(),
            'average_daily_consumption_L': df['Water_Total_L'].mean(),
            'final_tank_volume_L': df['Tank_Volume_L'].iloc[-1] if len(df) > 0 else 0.0,
            'volume_reduction_L': df['Tank_Volume_L'].iloc[0] - df['Tank_Volume_L'].iloc[-1] if len(df) > 0 else 0.0,
            'average_eto_mm': df['ETO_Ref_mm'].mean(),
            'average_transpiration_mm': df['Transpiration_mm'].mean(),
            'max_temperature_C': df['Temp_C'].max(),
            'min_temperature_C': df['Temp_C'].min(),
            'average_wue_L_kg': df['WUE_L_kg'].mean(),
            'simulation_period_days': self.total_days
        }
        return self.summary_stats

def calculate_dynamic_dry_matter_content(result: DailyResults, plant_part: str, strict_validation: bool = True) -> float:
    """
    Calculate dynamic dry matter content based on plant development, environment, and plant part.

    Args:
        result: DailyResults object
        plant_part: Plant part ('leaf', 'stem', 'shoot', 'root')
        strict_validation: If True, raises errors for missing parameters

    Returns:
        Fraction (0.0-1.0) of dry matter in fresh weight
    """
    if plant_part not in ['leaf', 'stem', 'shoot', 'root']:
        raise ValueError("Plant part must be 'leaf', 'stem', 'shoot', or 'root'")

    # Required parameters
    day = result.day
    growth_stage = result.growth_stage
    total_biomass = result.total_biomass
    water_stress = result.water_stress
    temperature_stress = result.temperature_stress_factor
    integrated_stress = result.integrated_stress_factor

    # Strict validation
    if strict_validation:
        if day is None:
            raise ValueError("Day must be provided in DailyResults")
        if growth_stage is None:
            raise ValueError("Growth stage must be provided in DailyResults")
        if total_biomass is None:
            raise ValueError("Total biomass must be provided in DailyResults")
        if water_stress is None:
            raise ValueError("Water stress must be provided in DailyResults")
        if temperature_stress is None:
            raise ValueError("Temperature stress factor must be provided in DailyResults")
        if integrated_stress is None:
            raise ValueError("Integrated stress factor must be provided in DailyResults")
    else:
        day = day or 1
        growth_stage = growth_stage or 'V4'
        total_biomass = total_biomass or 1.0
        water_stress = water_stress or 0.0
        temperature_stress = temperature_stress or 0.0
        integrated_stress = integrated_stress or 0.0

    # Base dry matter content by plant part (mature, unstressed conditions)
    base_dry_matter = {
        'leaf': 0.06,    # 5-7% for lettuce leaves
        'stem': 0.05,    # 4-6% for lettuce stems/petioles
        'shoot': 0.055,  # Combined shoot
        'root': 0.09     # 8-10% for roots
    }

    # Development factor
    if day <= 10:
        development_factor = 0.7 + (day / 10) * 0.3
    elif day <= 30:
        development_factor = 1.0
    else:
        development_factor = 1.0 + min(0.2, (day - 30) * 0.005)

    # Growth stage factor
    stage_factors = {
        'VE': 0.6, 'V1': 0.7, 'V2': 0.8, 'V3': 0.85, 'V4': 0.9,
        'V5': 0.95, 'V6': 1.0, 'V7': 1.0, 'V8': 1.0, 'V9': 1.0, 'V10': 1.0,
        'V11+': 1.05, 'HI': 1.1, 'HD': 1.15, 'HM': 1.2
    }
    stage_factor = stage_factors.get(growth_stage, 1.0)

    # Stress effects
    water_stress_factor = 1.0 + water_stress * 0.3
    temp_stress_factor = 1.0 + temperature_stress * 0.2
    stress_factor = 1.0 + integrated_stress * 0.25

    # Growth rate factor
    biomass_growth_rate = total_biomass / max(1, day)
    growth_rate_factor = 0.9 if biomass_growth_rate > 3.0 else 1.1 if biomass_growth_rate < 1.0 else 1.0

    # Plant part adjustment
    part_adjustment = {
        'leaf': 1.0,
        'stem': 0.85,
        'shoot': 0.92,
        'root': 1.5
    }

    # Calculate final dry matter content
    base_dm = base_dry_matter.get(plant_part, 0.06)
    final_dry_matter = (base_dm * development_factor * stage_factor *
                        water_stress_factor * temp_stress_factor * stress_factor *
                        growth_rate_factor * part_adjustment.get(plant_part, 1.0))

    # Enforce biological limits
    if plant_part == 'root':
        final_dry_matter = max(0.07, min(0.15, final_dry_matter))
    else:
        final_dry_matter = max(0.035, min(0.10, final_dry_matter))

    return final_dry_matter

"""
=== FUNCTION EXPLANATIONS ===

This module defines data structures and configuration for hydroponic system simulations, providing a comprehensive framework for storing system specifications, crop parameters, weather data, and simulation results.

KEY DATA STRUCTURES:

1. HydroSystemConfig
   - Purpose: Stores physical specifications of the hydroponic system.
   - Fields: System ID, crop ID, location ID, tank volume (L), flow rate (L/h), system type (NFT/DWC/AERO/WICK/EBB), system area (m²), number of plants, description.
   - Real-world analogy: A specification sheet for your hydroponic setup, detailing tank size, pump capacity, and plant capacity.

2. CropParameters
   - Purpose: Stores crop-specific characteristics.
   - Fields: Crop ID, crop name, basal crop coefficient (kcb), density index (phi), crop height (m), root zone depth (m), leaf area index (LAI).
   - Real-world analogy: A profile card for the crop, describing its growth habits and water needs.

3. WeatherData
   - Purpose: Stores daily environmental conditions.
   - Fields: Date, average/min/max temperature (°C), solar radiation (MJ/m²/day), relative humidity (%), wind speed (m/s), optional rainfall (mm).
   - Real-world analogy: A weather station log driving plant growth calculations.

4. HydroInputData
   - Purpose: Combines all input data for the simulation.
   - Fields: System configuration, crop parameters, weather data, nutrient parameters, simulation days.
   - Real-world analogy: A complete setup package for running a grow cycle simulation.

5. DailyResults
   - Purpose: Stores comprehensive results for each simulation day.
   - Fields: Over 100 variables covering water dynamics, solution chemistry, plant development, stress factors, photosynthesis, respiration, root/canopy architecture, and nutrient dynamics.
   - Real-world analogy: A daily report card capturing all aspects of plant and system performance.

6. SimulationResults
   - Purpose: Aggregates all daily results with metadata and summary statistics.
   - Fields: System/crop/location IDs, start/end dates, total days, daily results, transplanting period, optional treatment ID, summary statistics.
   - Real-world analogy: A full grow cycle report with detailed analytics.

KEY FUNCTIONS:

7. to_dataframe()
   - Purpose: Converts simulation results to a pandas DataFrame for analysis.
   - Process: Organizes data into functional groups (metadata, environment, water, chemistry, development, stress, biomass, roots, photosynthesis, respiration, canopy, nutrients).
   - Real-world analogy: Converting daily logs into an organized spreadsheet for trend analysis and comparisons.

8. calculate_summary_stats()
   - Purpose: Calculates key performance indicators for the simulation.
   - Metrics: Total/average water consumption, tank volume changes, average ET0/transpiration, temperature extremes, water use efficiency, simulation duration.
   - Real-world analogy: A farm efficiency report summarizing resource use and performance.

9. calculate_dynamic_dry_matter_content()
   - Purpose: Calculates dry matter content (fraction of dry weight in fresh weight) based on plant part, development, and environmental conditions.
   - Factors: Plant age, growth stage, water/temperature/integrated stress, growth rate, plant part (leaf/stem/shoot/root).
   - Equation: final_dry_matter = base × development × stage × stress × growth_rate × part_adjustment
   - Real-world analogy: Determining that fresh lettuce is ~95% water, with variations based on growing conditions (e.g., young lettuce ~97% water, stressed ~90%).

SIMULATION DATA ORGANIZATION:
- Groups: Metadata, environmental conditions, water dynamics, solution chemistry, plant development, stress factors, biomass, root architecture, photosynthesis, respiration, canopy, nutrient dynamics.
- Units: Standardized (e.g., mg/L, cm, g, μmol/m²/s).
- Time series: Tracks daily progression from transplanting to harvest.
- Treatment comparison: Supports multiple treatments via treatment_id.
- Statistical readiness: Formatted for analysis in statistical software.

BIOLOGICAL ACCURACY:
- Dry matter: Lettuce typically 4-10% dry matter, varying with conditions.
- Growth: Reflects realistic lettuce development (vegetative to harvest).
- Stress: Models plant responses to temperature, water, and nutrient stress.
- Nutrients: Based on uptake kinetics and plant physiology.
- Water: Captures transpiration and water use efficiency accurately.

PRACTICAL APPLICATIONS:
- Growers: Track performance, diagnose issues, optimize conditions, predict yields, manage resources.
- Researchers: Design experiments, validate models, calibrate parameters, generate publication datasets.
- Designers: Size systems, predict performance, analyze costs, design automation, plan scale-up.

DATA VALIDATION:
- Ensures all required fields are provided via configuration (no hardcoded defaults).
- Validates ranges (e.g., temperatures, pH, EC) for physical realism.
- Supports strict validation to enforce configuration-driven inputs.

"""