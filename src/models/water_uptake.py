"""
Water Uptake Submodel (WUS) for Hydroponic Systems
Implements modified Penman-Monteith equations for crop evapotranspiration
Based on: ETc′ = Φ × Kcb × ETo′ and Tr ≈ A × ETc′
"""

import numpy as np
from typing import Tuple


class WaterUptakeModel:
    """Water Uptake Submodel for hydroponic systems."""
    
    def __init__(self):
        # Constants
        self.LAMBDA = 2.45  # Latent heat of vaporization (MJ/kg)
        self.CP = 1.013     # Specific heat at constant pressure (MJ/kg/°C)
        self.EPSILON = 0.622  # Ratio molecular weight of water/dry air
        
    def calculate_crop_et(self, eto_ref: float, kcb: float, phi: float, 
                         laid: float, crop_height: float) -> Tuple[float, float]:
        """
        Calculate crop evapotranspiration and transpiration rate.
        
        Args:
            eto_ref: Reference ET (mm/day)
            kcb: Basal crop coefficient
            phi: Density index
            laid: Leaf area index
            crop_height: Crop height (m)
            
        Returns:
            Tuple of (crop_et, transpiration_rate) in mm/day
        """
        # Dynamic LAI adjustment factor (updated for realistic LAI range 0.2-4.0)
        if laid > 0.0:
            lai_factor = min(1.2, laid / 4.0)  # Normalized to maximum LAI of 4.0
        else:
            lai_factor = 0.05  # Minimum factor for very low LAI
            
        # Dynamic height adjustment factor
        height_factor = 1.0 + (crop_height * 0.15)  # 15% increase per meter
        
        # Equation (1): ETc′ = Φ × Kcb × ETo′
        etc_prime = phi * kcb * eto_ref
        
        # Calculate adjustment factor based on dynamic plant characteristics
        adjustment_factor = lai_factor * height_factor
        
        # Stage-sensitive bounds (allows for higher transpiration during rapid growth)
        if laid > 2.5:  # Rapid growth stage
            adjustment_factor = max(0.3, min(adjustment_factor, 2.0))
        else:  # Slow or steady growth
            adjustment_factor = max(0.1, min(adjustment_factor, 1.5))
        
        # Equation (2): Tr ≈ A × ETc′
        transpiration_rate = adjustment_factor * etc_prime
        
        return max(0.0, etc_prime), max(0.0, transpiration_rate)
    
    def calculate_reference_et(self, net_rad: float, temp_avg: float, temp_min: float, 
                              temp_max: float, wind_speed: float, rel_humidity: float, 
                              elevation: float = 100.0) -> float:
        """
        Calculate reference evapotranspiration using Penman-Monteith equation.
        FAO-56 standard method adapted for hydroponic systems.
        
        Args:
            net_rad: Net radiation (MJ/m²/day)
            temp_avg: Average air temperature (°C)
            temp_min: Minimum air temperature (°C)
            temp_max: Maximum air temperature (°C)
            wind_speed: Wind speed at 2m height (m/s)
            rel_humidity: Relative humidity (%)
            elevation: Elevation above sea level (m)
            
        Returns:
            Reference ET (mm/day)
        """
        # Calculate atmospheric pressure based on elevation
        pressure = 101.3 * ((293.0 - 0.0065 * elevation) / 293.0) ** 5.26
        
        # Calculate psychrometric constant
        gamma = (self.CP * pressure) / (self.EPSILON * self.LAMBDA)
        
        # Calculate slope of saturation vapor pressure curve at average temperature
        delta = (4098.0 * (0.6108 * np.exp(17.27 * temp_avg / (temp_avg + 237.3))) / 
                ((temp_avg + 237.3) ** 2))
        
        # Calculate saturation vapor pressures
        es_tmax = 0.6108 * np.exp(17.27 * temp_max / (temp_max + 237.3))
        es_tmin = 0.6108 * np.exp(17.27 * temp_min / (temp_min + 237.3))
        es = (es_tmax + es_tmin) / 2.0
        
        # Calculate actual vapor pressure
        ea = es * rel_humidity / 100.0
        
        # Calculate vapor pressure deficit
        vpd = es - ea
        
        # Calculate radiation term
        radiation_term = 0.408 * delta * net_rad
        
        # Calculate aerodynamic term
        aerodynamic_term = gamma * 900.0 / (temp_avg + 273.0) * wind_speed * vpd
        
        # Calculate denominator
        denominator = delta + gamma * (1.0 + 0.34 * wind_speed)
        
        # Calculate reference evapotranspiration (FAO-56 Penman-Monteith)
        eto_ref = (radiation_term + aerodynamic_term) / denominator
        
        return max(0.0, eto_ref)
    
    def calculate_net_radiation(self, srad: float, temp_max: float, temp_min: float, 
                               rel_humidity: float, elevation: float = 100.0, 
                               albedo: float = 0.23) -> float:
        """
        Calculate net radiation from solar radiation and other meteorological data.
        
        Args:
            srad: Solar radiation (MJ/m²/day)
            temp_max: Maximum temperature (°C)
            temp_min: Minimum temperature (°C)
            rel_humidity: Relative humidity (%)
            elevation: Elevation (m)
            albedo: Crop albedo (default 0.23 for reference crop)
            
        Returns:
            Net radiation (MJ/m²/day)
        """
        # Stefan-Boltzmann constant (MJ/K⁴/m²/day)
        stefan_boltzmann = 4.903e-09
        
        # Calculate actual vapor pressure
        ea = 0.6108 * np.exp(17.27 * temp_min / (temp_min + 237.3)) * rel_humidity / 100.0
        
        # Calculate clear-sky solar radiation (simplified)
        rso = srad * 1.35  # Approximation for clear-sky radiation
        
        # Calculate cloudiness factor
        if rso > 0.0:
            cloudiness_factor = min(1.0, srad / rso)
        else:
            cloudiness_factor = 1.0
            
        # Calculate net shortwave radiation
        rns = (1.0 - albedo) * srad
        
        # Calculate net longwave radiation
        rnl = (stefan_boltzmann * 
               (((temp_max + 273.16)**4 + (temp_min + 273.16)**4) / 2.0) * 
               (0.34 - 0.14 * np.sqrt(ea)) * 
               (1.35 * cloudiness_factor - 0.35))
        
        # Calculate net radiation
        net_rad = rns - rnl
        
        return max(0.0, net_rad)