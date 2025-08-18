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
                'WUE_kg_m3': result.water_use_efficiency
            }
            
            # Add nutrient concentrations
            for nutrient, conc in result.nutrient_concentrations.items():
                row[f'{nutrient}_mg_L'] = conc
                
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
            tank_volume=500.0,
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
        from ..models.nutrient_concentration import NutrientParams
        
        nutrients = [
            NutrientParams("N-NO3", "Nitrogen-Nitrate", "NO3-", 200.0, 250.0, 180.0, 1.0, True, 150.0, 300.0),
            NutrientParams("P-PO4", "Phosphorus-Phosphate", "PO4-3", 50.0, 60.0, 45.0, 1.2, True, 30.0, 80.0),
            NutrientParams("K", "Potassium", "K+", 300.0, 350.0, 280.0, 1.1, True, 250.0, 400.0),
            NutrientParams("Ca", "Calcium", "Ca+2", 150.0, 180.0, 120.0, 1.5, True, 100.0, 200.0),
            NutrientParams("Mg", "Magnesium", "Mg+2", 50.0, 60.0, 40.0, 1.3, True, 30.0, 70.0),
        ]
        
        return {nutrient.nutrient_id: nutrient for nutrient in nutrients}