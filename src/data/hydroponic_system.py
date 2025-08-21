"""
Hydroponic System Data Classes and Configuration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd


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
    rainfall: float = 0.0  # mm


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
    water_use_efficiency: float  # kg/m³
    ph: float = 0.0
    ec: float = 0.0
    rzt: float = 0.0  # Root zone temperature (°C)
    rzt_growth_factor: float = 1.0  # RZT growth effect
    rzt_nutrient_factor: float = 1.0  # RZT nutrient uptake effect
    v_stage: float = 0.0  # Vegetative stage (number of leaves)
    leaf_number: int = 0  # Current number of active leaves
    leaf_area_m2: float = 0.0  # Total leaf area per plant (m²)
    average_leaf_area_cm2: float = 0.0  # Average leaf area (cm²)
    co2_concentration: float = 400.0  # CO2 concentration (μmol/mol)
    vpd_actual: float = 0.8  # Actual VPD (kPa)
    env_photosynthesis_factor: float = 1.0  # Environmental photosynthesis enhancement
    env_transpiration_factor: float = 1.0  # Environmental transpiration factor
    
    # === DETAILED PHOTOSYNTHESIS MODEL RESULTS ===
    vcmax_25: float = 0.0  # Maximum carboxylation rate at 25°C (μmol/m²/s)
    jmax_25: float = 0.0   # Maximum electron transport rate at 25°C (μmol/m²/s)
    quantum_efficiency: float = 0.0  # Quantum efficiency of photosystem II
    rubisco_limited: float = 0.0  # Rubisco-limited photosynthesis rate
    light_limited: float = 0.0    # Light-limited photosynthesis rate
    co2_compensation: float = 0.0  # CO2 compensation point (μmol/mol)
    intercellular_co2: float = 0.0  # Intercellular CO2 concentration
    
    # === DETAILED RESPIRATION MODEL RESULTS ===
    maintenance_resp_leaves: float = 0.0  # Leaf maintenance respiration
    maintenance_resp_stems: float = 0.0   # Stem maintenance respiration  
    maintenance_resp_roots: float = 0.0   # Root maintenance respiration
    growth_resp_leaves: float = 0.0       # Leaf growth respiration
    growth_resp_stems: float = 0.0        # Stem growth respiration
    growth_resp_roots: float = 0.0        # Root growth respiration
    temperature_acclimation: float = 1.0   # Temperature acclimation factor
    age_factor: float = 1.0               # Age effects on respiration
    
    # === DETAILED ROOT ARCHITECTURE RESULTS ===
    fine_root_length: float = 0.0    # Fine root length (cm)
    coarse_root_length: float = 0.0  # Coarse root length (cm) 
    root_cohorts: int = 0            # Number of active root cohorts
    root_activity_young: float = 0.0 # Activity of young roots
    root_activity_old: float = 0.0   # Activity of old roots
    root_surface_active: float = 0.0 # Active root surface area
    root_turnover_rate: float = 0.0  # Daily root turnover rate
    
    # === DETAILED CANOPY ARCHITECTURE RESULTS ===
    sunlit_lai: float = 0.0          # Sunlit leaf area index
    shaded_lai: float = 0.0          # Shaded leaf area index
    canopy_layers: int = 0           # Number of canopy layers
    ppfd_top: float = 0.0           # PPFD at top of canopy
    ppfd_bottom: float = 0.0        # PPFD at bottom of canopy
    light_extinction: float = 0.0    # Light extinction coefficient
    
    # === DETAILED NITROGEN DYNAMICS RESULTS ===
    n_pool_structural: float = 0.0   # Structural nitrogen pool (g)
    n_pool_metabolic: float = 0.0    # Metabolic nitrogen pool (g)
    n_pool_storage: float = 0.0      # Storage nitrogen pool (g)
    n_pool_transport: float = 0.0    # Transport nitrogen pool (g)
    n_remobilization: float = 0.0    # Daily N remobilization (g)
    n_critical_conc: float = 0.0     # Critical nitrogen concentration
    
    # === DETAILED STRESS INTEGRATION RESULTS ===
    stress_interactions: Dict[str, float] = field(default_factory=dict)  # Stress interaction effects
    acclimation_levels: Dict[str, float] = field(default_factory=dict)   # Acclimation to each stress
    cumulative_damage: Dict[str, float] = field(default_factory=dict)    # Cumulative damage by stress type
    
    # === ADDITIONAL CROPGRO MODEL RESULTS ===
    # Genetic parameters
    cultivar_adaptation_index: float = 1.0
    cultivar_yield_potential: float = 1.0
    genetic_photosynthesis_capacity: float = 1.0
    genetic_ec_tolerance: float = 1.0
    genetic_nitrate_efficiency: float = 1.0
    
    # Phenology
    accumulated_gdd: float = 0.0
    development_rate: float = 0.0
    growth_stage: str = "VE"
    thermal_time_daily: float = 0.0
    is_vegetative: bool = True
    is_reproductive: bool = False
    
    # Growth and biomass
    total_biomass: float = 0.0
    leaf_biomass: float = 0.0
    stem_biomass: float = 0.0
    root_biomass: float = 0.0
    daily_growth_rate: float = 0.0
    leaf_growth_rate: float = 0.0
    stem_growth_rate: float = 0.0
    root_growth_rate: float = 0.0
    
    # Canopy architecture
    lai: float = 0.0
    canopy_height_cm: float = 0.0
    light_interception: float = 0.0
    total_absorbed_ppfd: float = 0.0
    canopy_photosynthesis: float = 0.0
    
    # Photosynthesis detailed
    photosynthesis_rate: float = 0.0
    net_assimilation: float = 0.0
    
    # Respiration detailed
    maintenance_respiration: float = 0.0
    growth_respiration: float = 0.0
    respiration_rate: float = 0.0
    
    # Root architecture detailed
    root_surface_area: float = 0.0
    root_length_density: float = 0.0
    root_volume: float = 0.0
    
    # Nitrogen dynamics detailed
    nitrogen_uptake_mg: float = 0.0
    nitrogen_demand_mg: float = 0.0
    nitrogen_stress_factor: float = 1.0
    leaf_nitrogen_conc: float = 0.0
    root_nitrogen_conc: float = 0.0
    nitrogen_remobilization: float = 0.0
    phosphorus_remobilization: float = 0.0
    potassium_remobilization: float = 0.0
    
    # Senescence 
    senescence_rate: float = 0.0
    leaf_senescence_rate: float = 0.0
    
    # Stress factors
    integrated_stress_factor: float = 1.0
    temperature_stress_level: float = 0.0
    temperature_stress_photosynthesis: float = 1.0
    temperature_stress_growth: float = 1.0
    water_stress: float = 0.0
    nutrient_stress: float = 0.0
    salinity_stress: float = 1.0
    
    # Environmental control
    controlled_temperature: float = 0.0
    controlled_humidity: float = 0.0
    controlled_co2: float = 400.0
    vpd_target: float = 0.8
    environmental_cost: float = 0.0
    
    # Temperature data
    air_temperature: float = 0.0
    min_temperature: float = 0.0
    max_temperature: float = 0.0
    leaf_temperature: float = 0.0
    canopy_temperature: float = 0.0
    cold_stress_factor: float = 0.0
    heat_stress_factor: float = 0.0
    temperature_stress_factor: float = 0.0
    
    # Water dynamics
    transpiration_rate: float = 0.0
    total_water_uptake: float = 0.0
    solution_ph: float = 6.0
    solution_ec: float = 1.5


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
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame for analysis."""
        data = []
        for result in self.daily_results:
            row = {
                'Date': result.date.strftime('%Y-%m-%d'),
                'Day': result.day,
                'System_ID': self.system_id,
                'Crop_ID': self.crop_id,
                'ETO_Ref_mm': result.eto_ref,
                'ETC_Prime_mm': result.etc_prime,
                'Transpiration_mm': result.transpiration,
                'Water_Total_L': result.water_uptake_total,
                'Tank_Volume_L': result.tank_volume,
                'Temp_C': result.temp_avg,
                'Solar_Rad_MJ': result.solar_radiation,
                'VPD_kPa': result.vpd,
                'WUE_kg_m3': result.water_use_efficiency,
                'pH': result.ph,
                'EC': result.ec,
                'RZT_C': result.rzt,
                'RZT_Growth_Factor': result.rzt_growth_factor,
                'RZT_Nutrient_Factor': result.rzt_nutrient_factor,
                'V_Stage': result.v_stage,
                'Leaf_Number': result.leaf_number,
                'Leaf_Area_m2': result.leaf_area_m2,
                'Avg_Leaf_Area_cm2': result.average_leaf_area_cm2,
                'CO2_umol_mol': result.co2_concentration,
                'VPD_Actual_kPa': result.vpd_actual,
                'Env_Photo_Factor': result.env_photosynthesis_factor,
                'Env_Transp_Factor': result.env_transpiration_factor
            }
            
            # Add nutrient concentrations
            for nutrient, conc in result.nutrient_concentrations.items():
                row[f'{nutrient}_mg_L'] = conc

            # Add dynamic crop variables if they exist
            if hasattr(result, 'lai'):
                row['LAI'] = result.lai
            if hasattr(result, 'height'):
                row['Height_m'] = result.height
            if hasattr(result, 'kcb_dynamic'):
                row['Kcb_dynamic'] = result.kcb_dynamic
            if hasattr(result, 'growth_stage'):
                row['Growth_Stage'] = result.growth_stage
            if hasattr(result, 'total_biomass'):
                row['Total_Biomass_g'] = result.total_biomass
            if hasattr(result, 'fresh_weight'):
                row['Fresh_Weight_g'] = result.fresh_weight

            # Round all float values to 2 decimal places
            for key, value in row.items():
                if isinstance(value, float):
                    row[key] = round(value, 2)

            data.append(row)
            
        return pd.DataFrame(data)
    
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
    """Default configurations for common hydroponic systems."""
    
    @staticmethod
    def get_nft_lettuce_system() -> HydroSystemConfig:
        """Get default NFT lettuce system configuration."""
        return HydroSystemConfig(
            system_id="HYD1",
            crop_id="LETT",
            location_id="USGA",
            tank_volume=1500.0,
            flow_rate=50.0,
            system_type="NFT",
            system_area=10.0,
            n_plants=48,
            description="Nutrient Film Technique - Lettuce production"
        )
    
    @staticmethod
    def get_lettuce_parameters() -> CropParameters:
        """Get default lettuce crop parameters."""
        return CropParameters(
            crop_id="LETT",
            crop_name="Lettuce",
            kcb=0.90,
            phi=0.85,
            crop_height=0.30,
            root_zone_depth=0.15,
            laid=2.0
        )
    
    @staticmethod
    def get_default_nutrients():
        """Get default nutrient parameters."""
        from ..models.nutrient_models import NutrientParams
        
        nutrients = [
            NutrientParams("N-NO3", "Nitrogen-Nitrate", "NO3-", 200.0, 250.0, 180.0, 1.0, True, 150.0, 300.0, charge=-1, molar_mass=14.01),
            NutrientParams("P-PO4", "Phosphorus-Phosphate", "PO4-3", 50.0, 60.0, 45.0, 1.2, True, 30.0, 80.0, charge=-1, molar_mass=30.97),
            NutrientParams("K", "Potassium", "K+", 300.0, 350.0, 280.0, 1.1, True, 250.0, 400.0, charge=1, molar_mass=39.10),
            NutrientParams("Ca", "Calcium", "Ca+2", 150.0, 180.0, 120.0, 1.5, True, 100.0, 200.0, charge=2, molar_mass=40.08),
            NutrientParams("Mg", "Magnesium", "Mg+2", 50.0, 60.0, 40.0, 1.3, True, 30.0, 70.0, charge=2, molar_mass=24.31),
        ]
        
        return {nutrient.nutrient_id: nutrient for nutrient in nutrients}