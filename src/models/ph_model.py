"""
Comprehensive pH Model for Hydroponic Systems

Implements scientifically accurate pH dynamics including:
1. Henderson-Hasselbalch buffer chemistry
2. Nutrient uptake effects on pH
3. pH-dependent nutrient solubility
4. Automated pH control systems
5. Buffer capacity modeling

Based on:
- Sonneveld & Voogt (2009) - Plant Nutrition of Greenhouse Crops
- Jones (2005) - Hydroponics: A Practical Guide
- Bugbee (2004) - Nutrient Management in Recirculating Hydroponic Culture
"""

import math
import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class BufferSystem(Enum):
    """Types of buffer systems in hydroponic solutions."""
    CARBONATE = "carbonate"      # HCO3-/CO2
    PHOSPHATE = "phosphate"      # H2PO4-/HPO4--
    ORGANIC = "organic"          # Organic acids/salts


@dataclass
class PHParameters:
    """Parameters for pH model from CSV configuration."""
    # Target pH range
    ph_target_min: float = None
    ph_target_max: float = None
    
    # Buffer system
    ph_buffer_capacity: float = None    # mEq/L
    ph_drift_rate: float = None         # pH units/day
    
    # Nutrient uptake effects
    nitrate_acidification_factor: float = None    # pH change per mg N
    ammonium_alkalinization_factor: float = None  # pH change per mg N
    
    # Buffer chemistry constants
    carbonate_buffer_pka: float = None
    phosphate_buffer_pka1: float = None
    phosphate_buffer_pka2: float = None  
    phosphate_buffer_pka3: float = None
    
    # Control system
    ph_adjustment_rate: float = None     # pH units/hour
    ph_deadband: float = None           # pH units
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'PHParameters':
        """Create PHParameters from CSV configuration data."""
        return cls(
            ph_target_min=config_dict['ph_target_min'],
            ph_target_max=config_dict['ph_target_max'],
            ph_buffer_capacity=config_dict['ph_buffer_capacity'],
            ph_drift_rate=config_dict['ph_drift_rate'],
            nitrate_acidification_factor=config_dict['nitrate_acidification_factor'],
            ammonium_alkalinization_factor=config_dict['ammonium_alkalinization_factor'],
            carbonate_buffer_pka=config_dict['carbonate_buffer_pka'],
            phosphate_buffer_pka1=config_dict['phosphate_buffer_pka1'],
            phosphate_buffer_pka2=config_dict['phosphate_buffer_pka2'],
            phosphate_buffer_pka3=config_dict['phosphate_buffer_pka3'],
            ph_adjustment_rate=config_dict['ph_adjustment_rate'],
            ph_deadband=config_dict['ph_deadband']
        )


@dataclass
class PHState:
    """Current pH system state."""
    current_ph: float = 6.0
    buffer_capacity: float = 2.5        # mEq/L
    total_alkalinity: float = 2.0       # mEq/L as HCO3-
    carbonate_conc: float = 50.0        # mg/L as HCO3-
    phosphate_total: float = 60.0       # mg/L total P
    ionic_strength: float = 0.02        # M
    temperature: float = 20.0           # °C
    
    # Control system state
    acid_dosing_rate: float = 0.0       # mL/L/hour
    base_dosing_rate: float = 0.0       # mL/L/hour
    last_adjustment_time: float = 0.0   # hours


@dataclass
class NutrientSolubility:
    """pH-dependent nutrient solubility data."""
    phosphate_solubility: Dict[str, float]     # mg/L at different pH
    iron_solubility: Dict[str, float]          # mg/L at different pH  
    calcium_phosphate_ksp: float = 2.07e-33    # Solubility product Ca3(PO4)2
    magnesium_phosphate_ksp: float = 1.04e-24  # Solubility product Mg3(PO4)2


class HydroponicPHModel:
    """
    Comprehensive pH model for hydroponic systems with proper buffer chemistry.
    """
    
    def __init__(self, parameters: Optional[PHParameters] = None):
        self.params = parameters or PHParameters()
        self.ph_state = PHState()
        self.nutrient_solubility = NutrientSolubility(
            phosphate_solubility={
                "4.0": 1200.0, "5.0": 800.0, "5.5": 400.0, "6.0": 200.0,
                "6.5": 120.0, "7.0": 80.0, "7.5": 60.0, "8.0": 45.0
            },
            iron_solubility={
                "4.0": 50.0, "5.0": 20.0, "5.5": 8.0, "6.0": 3.0,
                "6.5": 1.0, "7.0": 0.3, "7.5": 0.1, "8.0": 0.03
            }
        )
    
    def calculate_henderson_hasselbalch_ph(self, total_carbonate: float, 
                                          free_co2: float, temperature: float) -> float:
        """
        Calculate pH using Henderson-Hasselbalch equation for carbonate system.
        
        pH = pKa + log([HCO3-]/[H2CO3])
        
        Args:
            total_carbonate: Total carbonate alkalinity (mEq/L)
            free_co2: Dissolved CO2 concentration (mg/L)
            temperature: Solution temperature (°C)
            
        Returns:
            Calculated pH
        """
        # Temperature-corrected pKa for carbonic acid
        pka = self.params.carbonate_buffer_pka
        temp_correction = (temperature - 25.0) * 0.0055  # 0.0055 per °C
        pka_corrected = pka - temp_correction
        
        # Convert CO2 to molar concentration
        co2_molar = (free_co2 / 44.0) / 1000.0  # mg/L to mol/L
        
        # Calculate bicarbonate concentration from total alkalinity
        hco3_molar = (total_carbonate / 1000.0)  # mEq/L to mol/L
        
        if co2_molar > 1e-10:  # Avoid division by zero
            ph = pka_corrected + math.log10(hco3_molar / co2_molar)
        else:
            ph = pka_corrected + 2.0  # Default if no CO2
            
        return max(4.0, min(9.0, ph))  # Physically reasonable limits
    
    def calculate_phosphate_speciation(self, ph: float, total_phosphate: float) -> Dict[str, float]:
        """
        Calculate phosphate species distribution using Henderson-Hasselbalch equations.
        
        H3PO4 ⇌ H2PO4- ⇌ HPO4-- ⇌ PO4---
        
        Args:
            ph: Current pH
            total_phosphate: Total phosphate concentration (mg/L as P)
            
        Returns:
            Dictionary with concentrations of each species (mg/L)
        """
        pka1 = self.params.phosphate_buffer_pka1  # 2.15
        pka2 = self.params.phosphate_buffer_pka2  # 7.20
        pka3 = self.params.phosphate_buffer_pka3  # 12.35
        
        # Calculate alpha values (fraction of each species)
        h = 10**(-ph)
        ka1 = 10**(-pka1)
        ka2 = 10**(-pka2)  
        ka3 = 10**(-pka3)
        
        denominator = h**3 + h**2 * ka1 + h * ka1 * ka2 + ka1 * ka2 * ka3
        
        alpha0 = h**3 / denominator                    # H3PO4
        alpha1 = h**2 * ka1 / denominator              # H2PO4-
        alpha2 = h * ka1 * ka2 / denominator           # HPO4--
        alpha3 = ka1 * ka2 * ka3 / denominator         # PO4---
        
        return {
            'H3PO4': total_phosphate * alpha0,
            'H2PO4': total_phosphate * alpha1,
            'HPO4': total_phosphate * alpha2, 
            'PO4': total_phosphate * alpha3
        }
    
    def calculate_nutrient_uptake_ph_effect(self, nutrient_uptake: Dict[str, float]) -> float:
        """
        Calculate pH change from nutrient uptake based on ion exchange.
        
        Args:
            nutrient_uptake: Nutrient uptake rates (mg/day) by form
            
        Returns:
            pH change (positive = increase, negative = decrease)
        """
        ph_change = 0.0
        
        # Nitrate uptake acidifies (charge balance requires H+ release)
        no3_uptake_mg = nutrient_uptake.get('NO3', 0.0)
        if no3_uptake_mg > 0:
            # Convert NO3 to elemental N for accurate stoichiometry
            n_uptake_mg = no3_uptake_mg * (14.0 / 62.0)
            ph_change -= n_uptake_mg * self.params.nitrate_acidification_factor
        
        # Ammonium uptake alkalinizes (NH4+ uptake releases OH-)
        nh4_uptake_mg = nutrient_uptake.get('NH4', 0.0)
        if nh4_uptake_mg > 0:
            n_uptake_mg = nh4_uptake_mg * (14.0 / 18.0)
            ph_change += n_uptake_mg * self.params.ammonium_alkalinization_factor
        
        # Phosphate uptake slightly acidifies
        po4_uptake_mg = nutrient_uptake.get('PO4', 0.0) 
        if po4_uptake_mg > 0:
            p_uptake_mg = po4_uptake_mg * (31.0 / 95.0)
            ph_change -= p_uptake_mg * 0.0005  # Small acidification
        
        # Buffer capacity moderates changes
        buffered_change = ph_change / self.ph_state.buffer_capacity
        
        return buffered_change
    
    def calculate_ph_dependent_solubility(self, ph: float, 
                                        nutrient_concentrations: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate pH-dependent nutrient availability and precipitation.
        
        Args:
            ph: Current pH
            nutrient_concentrations: Current concentrations (mg/L)
            
        Returns:
            Available concentrations after pH effects (mg/L)
        """
        available_concentrations = nutrient_concentrations.copy()
        
        # Interpolate phosphate solubility
        ph_points = [float(p) for p in self.nutrient_solubility.phosphate_solubility.keys()]
        ph_points.sort()
        
        if ph <= ph_points[0]:
            max_po4 = self.nutrient_solubility.phosphate_solubility[str(ph_points[0])]
        elif ph >= ph_points[-1]:
            max_po4 = self.nutrient_solubility.phosphate_solubility[str(ph_points[-1])]
        else:
            # Linear interpolation
            for i in range(len(ph_points) - 1):
                if ph_points[i] <= ph <= ph_points[i + 1]:
                    ph_low, ph_high = ph_points[i], ph_points[i + 1]
                    sol_low = self.nutrient_solubility.phosphate_solubility[str(ph_low)]
                    sol_high = self.nutrient_solubility.phosphate_solubility[str(ph_high)]
                    fraction = (ph - ph_low) / (ph_high - ph_low)
                    max_po4 = sol_low + fraction * (sol_high - sol_low)
                    break
        
        # Limit phosphate concentration by solubility
        current_po4 = available_concentrations.get('P-PO4', 0.0)
        if current_po4 > max_po4:
            available_concentrations['P-PO4'] = max_po4
            # Log precipitation
            precipitated = current_po4 - max_po4
            if precipitated > 1.0:  # Only log significant precipitation
                print(f"pH {ph:.1f}: {precipitated:.1f} mg/L phosphate precipitated")
        
        # Iron solubility (critical at high pH)
        ph_points = [float(p) for p in self.nutrient_solubility.iron_solubility.keys()]
        ph_points.sort()
        
        if ph <= ph_points[0]:
            max_fe = self.nutrient_solubility.iron_solubility[str(ph_points[0])]
        elif ph >= ph_points[-1]:
            max_fe = self.nutrient_solubility.iron_solubility[str(ph_points[-1])]
        else:
            for i in range(len(ph_points) - 1):
                if ph_points[i] <= ph <= ph_points[i + 1]:
                    ph_low, ph_high = ph_points[i], ph_points[i + 1]
                    sol_low = self.nutrient_solubility.iron_solubility[str(ph_low)]
                    sol_high = self.nutrient_solubility.iron_solubility[str(ph_high)]
                    fraction = (ph - ph_low) / (ph_high - ph_low)
                    max_fe = sol_low + fraction * (sol_high - sol_low)
                    break
        
        # Apply iron limitation if Fe is tracked
        current_fe = available_concentrations.get('Fe', 0.0)
        if current_fe > max_fe:
            available_concentrations['Fe'] = max_fe
        
        return available_concentrations
    
    def simulate_ph_control_system(self, current_ph: float, time_hours: float = 1.0) -> Tuple[float, float, float]:
        """
        Simulate automated pH control system with acid/base dosing.
        
        Args:
            current_ph: Current pH value
            time_hours: Time step for simulation (hours)
            
        Returns:
            Tuple of (new_ph, acid_dosed_ml_per_L, base_dosed_ml_per_L)
        """
        target_ph = (self.params.ph_target_min + self.params.ph_target_max) / 2.0
        ph_error = current_ph - target_ph
        
        acid_dose = 0.0
        base_dose = 0.0
        
        # Only act if outside deadband
        if abs(ph_error) > self.params.ph_deadband:
            if ph_error > 0:  # pH too high, dose acid
                max_acid_dose = self.params.ph_adjustment_rate * time_hours
                required_dose = min(max_acid_dose, abs(ph_error) * 2.0)  # Proportional control
                acid_dose = required_dose
                ph_change = -required_dose / self.ph_state.buffer_capacity
            else:  # pH too low, dose base
                max_base_dose = self.params.ph_adjustment_rate * time_hours
                required_dose = min(max_base_dose, abs(ph_error) * 2.0)
                base_dose = required_dose
                ph_change = required_dose / self.ph_state.buffer_capacity
            
            new_ph = current_ph + ph_change
        else:
            new_ph = current_ph
        
        return new_ph, acid_dose, base_dose
    
    def daily_update(self, nutrient_uptake: Dict[str, float], 
                    nutrient_concentrations: Dict[str, float],
                    temperature: float, ec: float) -> Dict[str, Any]:
        """
        Daily pH system update with comprehensive chemistry.
        
        Args:
            nutrient_uptake: Daily nutrient uptake (mg/day)
            nutrient_concentrations: Current concentrations (mg/L)  
            temperature: Solution temperature (°C)
            ec: Electrical conductivity (dS/m)
            
        Returns:
            Dictionary with pH results and system state
        """
        current_ph = self.ph_state.current_ph
        
        # 1. Calculate pH changes from nutrient uptake
        uptake_ph_change = self.calculate_nutrient_uptake_ph_effect(nutrient_uptake)
        
        # 2. Natural pH drift (CO2 outgassing, etc.)
        natural_drift = self.params.ph_drift_rate / 24.0  # Per hour
        
        # 3. Update buffer capacity based on EC (higher ionic strength = more buffering)
        self.ph_state.buffer_capacity = self.params.ph_buffer_capacity * (1.0 + 0.1 * ec)
        
        # 4. Calculate new pH before control
        ph_before_control = current_ph + uptake_ph_change + natural_drift
        
        # 5. Apply pH control system (simulates 24 hours of control)
        controlled_ph, acid_dosed, base_dosed = self.simulate_ph_control_system(
            ph_before_control, time_hours=24.0
        )
        
        # 6. Calculate pH-dependent nutrient availability
        available_nutrients = self.calculate_ph_dependent_solubility(
            controlled_ph, nutrient_concentrations
        )
        
        # 7. Calculate phosphate speciation
        total_phosphate = available_nutrients.get('P-PO4', 0.0) * (31.0 / 95.0)  # Convert to P
        phosphate_species = self.calculate_phosphate_speciation(controlled_ph, total_phosphate)
        
        # 8. Update system state
        self.ph_state.current_ph = controlled_ph
        self.ph_state.temperature = temperature
        self.ph_state.acid_dosing_rate = acid_dosed / 24.0  # mL/L/hour
        self.ph_state.base_dosing_rate = base_dosed / 24.0
        
        return {
            'final_ph': controlled_ph,
            'ph_change_from_uptake': uptake_ph_change,
            'ph_change_from_drift': natural_drift,
            'acid_dosed_ml_per_L': acid_dosed,
            'base_dosed_ml_per_L': base_dosed,
            'buffer_capacity': self.ph_state.buffer_capacity,
            'available_nutrients': available_nutrients,
            'phosphate_species': phosphate_species,
            'nutrient_precipitation': {
                nutrient: max(0.0, original - available_nutrients.get(nutrient, original))
                for nutrient, original in nutrient_concentrations.items()
            }
        }


def create_lettuce_ph_model(system_config=None) -> HydroponicPHModel:
    """Create pH model with lettuce-specific parameters from CSV config."""
    
    try:
        # Get pH parameters from CSV data loaded in system_config
        nutrient_params = getattr(system_config, 'nutrient_parameters', {}) if system_config else {}
        
        # Create parameters from CSV config
        parameters = PHParameters.from_config(nutrient_params)
        return HydroponicPHModel(parameters)
        
    except KeyError as e:
        raise KeyError(f"Required pH parameter '{e.args[0]}' not found in CSV configuration. Add to nutrient_parameters_consolidated.csv")
    except Exception as e:
        print(f"Warning: Could not load CSV pH parameters: {e}")
        print("Using default pH parameters")
        return HydroponicPHModel()