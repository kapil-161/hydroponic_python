import math
from typing import Dict, Tuple, Any, List
from dataclasses import dataclass
from enum import Enum

class BufferSystem(Enum):
    CARBONATE = "carbonate"      # HCO3-/CO2
    PHOSPHATE = "phosphate"      # H2PO4-/HPO4--
    ORGANIC = "organic"          # Organic acids/salts

@dataclass
class PHParameters:
    ph_target_min: float
    ph_target_max: float
    ph_buffer_capacity: float
    ph_drift_rate: float
    nitrate_acidification_factor: float
    ammonium_alkalinization_factor: float
    phosphate_acidification_factor: float
    carbonate_buffer_pka: float
    phosphate_buffer_pka1: float
    phosphate_buffer_pka2: float
    phosphate_buffer_pka3: float
    ph_adjustment_rate: float
    ph_deadband: float
    temperature_correction_factor: float
    ec_buffer_factor: float
    proportional_control_factor: float
    hours_per_day: float
    current_ph: float
    total_alkalinity: float
    carbonate_conc: float
    phosphate_total: float
    ionic_strength: float
    ph_min_limit: float
    ph_max_limit: float
    phosphate_solubility_data: Dict[str, float]
    iron_solubility_data: Dict[str, float]
    calcium_phosphate_ksp: float
    magnesium_phosphate_ksp: float
    co2_molecular_weight: float
    n_molecular_weight: float
    no3_molecular_weight: float
    nh4_molecular_weight: float
    p_molecular_weight: float
    po4_molecular_weight: float
    unit_conversion_factor: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'PHParameters':
        required_params = [
            'ph_target_min', 'ph_target_max', 'ph_buffer_capacity', 'ph_drift_rate',
            'nitrate_acidification_factor', 'ammonium_alkalinization_factor',
            'phosphate_acidification_factor', 'carbonate_buffer_pka',
            'phosphate_buffer_pka1', 'phosphate_buffer_pka2', 'phosphate_buffer_pka3',
            'ph_adjustment_rate', 'ph_deadband', 'temperature_correction_factor',
            'ec_buffer_factor', 'proportional_control_factor', 'hours_per_day',
            'current_ph', 'total_alkalinity', 'carbonate_conc', 'phosphate_total',
            'ionic_strength', 'ph_min_limit', 'ph_max_limit',
            'calcium_phosphate_ksp', 'magnesium_phosphate_ksp',
            'co2_molecular_weight', 'nitrogen_atomic_weight', 'no3_molecular_weight',
            'nh4_molecular_weight', 'phosphorus_atomic_weight', 'po4_molecular_weight',
            'unit_conversion_factor'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")

        if 'phosphate_solubility_data' not in config or not config['phosphate_solubility_data']:
            raise KeyError("Phosphate solubility data must be provided")
        if 'iron_solubility_data' not in config or not config['iron_solubility_data']:
            raise KeyError("Iron solubility data must be provided")

        for pH in config['phosphate_solubility_data']:
            try:
                float(pH)
            except ValueError:
                raise ValueError(f"Phosphate solubility data keys must be valid pH values, got {pH}")
        for pH in config['iron_solubility_data']:
            try:
                float(pH)
            except ValueError:
                raise ValueError(f"Iron solubility data keys must be valid pH values, got {pH}")

        if config['ph_target_min'] >= config['ph_target_max']:
            raise ValueError("ph_target_min must be less than ph_target_max")
        if config['ph_min_limit'] >= config['ph_max_limit']:
            raise ValueError("ph_min_limit must be less than ph_max_limit")
        if config['ph_buffer_capacity'] <= 0:
            raise ValueError("ph_buffer_capacity must be positive")
        if config['hours_per_day'] <= 0:
            raise ValueError("hours_per_day must be positive")
        if config['ph_adjustment_rate'] <= 0:
            raise ValueError("ph_adjustment_rate must be positive")
        if config['ph_deadband'] < 0:
            raise ValueError("ph_deadband cannot be negative")

        return cls(
            ph_target_min=float(config['ph_target_min']),
            ph_target_max=float(config['ph_target_max']),
            ph_buffer_capacity=float(config['ph_buffer_capacity']),
            ph_drift_rate=float(config['ph_drift_rate']),
            nitrate_acidification_factor=float(config['nitrate_acidification_factor']),
            ammonium_alkalinization_factor=float(config['ammonium_alkalinization_factor']),
            phosphate_acidification_factor=float(config['phosphate_acidification_factor']),
            carbonate_buffer_pka=float(config['carbonate_buffer_pka']),
            phosphate_buffer_pka1=float(config['phosphate_buffer_pka1']),
            phosphate_buffer_pka2=float(config['phosphate_buffer_pka2']),
            phosphate_buffer_pka3=float(config['phosphate_buffer_pka3']),
            ph_adjustment_rate=float(config['ph_adjustment_rate']),
            ph_deadband=float(config['ph_deadband']),
            temperature_correction_factor=float(config['temperature_correction_factor']),
            ec_buffer_factor=float(config['ec_buffer_factor']),
            proportional_control_factor=float(config['proportional_control_factor']),
            hours_per_day=float(config['hours_per_day']),
            current_ph=float(config['current_ph']),
            total_alkalinity=float(config['total_alkalinity']),
            carbonate_conc=float(config['carbonate_conc']),
            phosphate_total=float(config['phosphate_total']),
            ionic_strength=float(config['ionic_strength']),
            ph_min_limit=float(config['ph_min_limit']),
            ph_max_limit=float(config['ph_max_limit']),
            phosphate_solubility_data=config['phosphate_solubility_data'],
            iron_solubility_data=config['iron_solubility_data'],
            calcium_phosphate_ksp=float(config['calcium_phosphate_ksp']),
            magnesium_phosphate_ksp=float(config['magnesium_phosphate_ksp']),
            co2_molecular_weight=float(config['co2_molecular_weight']),
            n_molecular_weight=float(config['nitrogen_atomic_weight']),  # Map from CSV name
            no3_molecular_weight=float(config['no3_molecular_weight']),
            nh4_molecular_weight=float(config['nh4_molecular_weight']),
            p_molecular_weight=float(config['phosphorus_atomic_weight']),  # Map from CSV name
            po4_molecular_weight=float(config['po4_molecular_weight']),
            unit_conversion_factor=float(config['unit_conversion_factor'])
        )

@dataclass
class PHState:
    current_ph: float
    buffer_capacity: float
    total_alkalinity: float
    carbonate_conc: float
    phosphate_total: float
    ionic_strength: float
    temperature: float
    acid_dosing_rate: float = 0.0
    base_dosing_rate: float = 0.0
    last_adjustment_time: float = 0.0

@dataclass
class NutrientSolubility:
    phosphate_solubility: Dict[str, float]
    iron_solubility: Dict[str, float]
    calcium_phosphate_ksp: float
    magnesium_phosphate_ksp: float

@dataclass
class PHUpdateResponse:
    final_ph: float
    ph_change_from_uptake: float
    ph_change_from_drift: float
    acid_dosed_ml_per_L: float
    base_dosed_ml_per_L: float
    buffer_capacity: float
    available_nutrients: Dict[str, float]
    phosphate_species: Dict[str, float]
    nutrient_precipitation: Dict[str, float]

class HydroponicPHModel:
    def __init__(self, parameters: PHParameters):
        if not parameters:
            raise ValueError("PHParameters must be provided")
        self.params = parameters
        self.ph_state = PHState(
            current_ph=parameters.current_ph,
            buffer_capacity=parameters.ph_buffer_capacity,
            total_alkalinity=parameters.total_alkalinity,
            carbonate_conc=parameters.carbonate_conc,
            phosphate_total=parameters.phosphate_total,
            ionic_strength=parameters.ionic_strength,
            temperature=None
        )
        self.nutrient_solubility = NutrientSolubility(
            phosphate_solubility=parameters.phosphate_solubility_data,
            iron_solubility=parameters.iron_solubility_data,
            calcium_phosphate_ksp=parameters.calcium_phosphate_ksp,
            magnesium_phosphate_ksp=parameters.magnesium_phosphate_ksp
        )

    def calculate_henderson_hasselbalch_ph(self, total_carbonate: float, free_co2: float, temperature: float) -> float:
        if total_carbonate <= 0:
            raise ValueError("Total carbonate must be positive")
        if free_co2 <= 0:
            raise ValueError("Free CO2 concentration must be positive")
        if temperature is None:
            raise ValueError("Temperature must be provided")

        pka_corrected = self.params.carbonate_buffer_pka - (temperature - 25.0) * self.params.temperature_correction_factor
        co2_molar = (free_co2 / self.params.co2_molecular_weight) / self.params.unit_conversion_factor
        hco3_molar = (total_carbonate / self.params.unit_conversion_factor)
        ph = pka_corrected + math.log10(hco3_molar / co2_molar)
        return max(self.params.ph_min_limit, min(self.params.ph_max_limit, ph))

    def calculate_phosphate_speciation(self, ph: float, total_phosphate: float) -> Dict[str, float]:
        if total_phosphate < 0:
            raise ValueError("Total phosphate cannot be negative")
        h = 10**(-ph)
        ka1 = 10**(-self.params.phosphate_buffer_pka1)
        ka2 = 10**(-self.params.phosphate_buffer_pka2)
        ka3 = 10**(-self.params.phosphate_buffer_pka3)
        denominator = h**3 + h**2 * ka1 + h * ka1 * ka2 + ka1 * ka2 * ka3
        if denominator <= 0:
            raise ValueError("Denominator in phosphate speciation must be positive")
        alpha0 = h**3 / denominator
        alpha1 = h**2 * ka1 / denominator
        alpha2 = h * ka1 * ka2 / denominator
        alpha3 = ka1 * ka2 * ka3 / denominator
        return {
            'H3PO4': total_phosphate * alpha0,
            'H2PO4': total_phosphate * alpha1,
            'HPO4': total_phosphate * alpha2,
            'PO4': total_phosphate * alpha3
        }

    def calculate_nutrient_uptake_ph_effect(self, nutrient_uptake: Dict[str, float]) -> float:
        required_nutrients = ['NO3', 'NH4', 'PO4']
        for nutrient in required_nutrients:
            if nutrient not in nutrient_uptake:
                raise KeyError(f"Missing nutrient uptake for {nutrient}")
        ph_change = 0.0
        no3_uptake_mg = nutrient_uptake['NO3']
        if no3_uptake_mg > 0:
            n_uptake_mg = no3_uptake_mg * (self.params.n_molecular_weight / self.params.no3_molecular_weight)
            ph_change -= n_uptake_mg * self.params.nitrate_acidification_factor
        nh4_uptake_mg = nutrient_uptake['NH4']
        if nh4_uptake_mg > 0:
            n_uptake_mg = nh4_uptake_mg * (self.params.n_molecular_weight / self.params.nh4_molecular_weight)
            ph_change += n_uptake_mg * self.params.ammonium_alkalinization_factor
        po4_uptake_mg = nutrient_uptake['PO4']
        if po4_uptake_mg > 0:
            p_uptake_mg = po4_uptake_mg * (self.params.p_molecular_weight / self.params.po4_molecular_weight)
            ph_change -= p_uptake_mg * self.params.phosphate_acidification_factor
        if self.ph_state.buffer_capacity <= 0:
            raise ValueError("Buffer capacity must be positive")
        return ph_change / self.ph_state.buffer_capacity

    def calculate_ph_dependent_solubility(self, ph: float, nutrient_concentrations: Dict[str, float]) -> Dict[str, float]:
        required_nutrients = ['P-PO4', 'Fe']
        for nutrient in required_nutrients:
            if nutrient not in nutrient_concentrations:
                raise KeyError(f"Missing nutrient concentration for {nutrient}")
        available_concentrations = nutrient_concentrations.copy()
        ph_points = [float(p) for p in self.nutrient_solubility.phosphate_solubility.keys()]
        ph_points.sort()
        if not ph_points:
            raise ValueError("Phosphate solubility data must contain at least one pH point")
        if ph <= ph_points[0]:
            max_po4 = self.nutrient_solubility.phosphate_solubility[str(ph_points[0])]
        elif ph >= ph_points[-1]:
            max_po4 = self.nutrient_solubility.phosphate_solubility[str(ph_points[-1])]
        else:
            for i in range(len(ph_points) - 1):
                if ph_points[i] <= ph <= ph_points[i + 1]:
                    ph_low, ph_high = ph_points[i], ph_points[i + 1]
                    sol_low = self.nutrient_solubility.phosphate_solubility[str(ph_low)]
                    sol_high = self.nutrient_solubility.phosphate_solubility[str(ph_high)]
                    fraction = (ph - ph_low) / (ph_high - ph_low)
                    max_po4 = sol_low + fraction * (sol_high - sol_low)
                    break
        current_po4 = available_concentrations['P-PO4']
        if current_po4 > max_po4:
            available_concentrations['P-PO4'] = max_po4
            precipitated = current_po4 - max_po4
            if precipitated > 1.0:
                print(f"pH {ph:.1f}: {precipitated:.1f} mg/L phosphate precipitated")
        ph_points = [float(p) for p in self.nutrient_solubility.iron_solubility.keys()]
        ph_points.sort()
        if not ph_points:
            raise ValueError("Iron solubility data must contain at least one pH point")
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
        current_fe = available_concentrations['Fe']
        if current_fe > max_fe:
            available_concentrations['Fe'] = max_fe
        return available_concentrations

    def simulate_ph_control_system(self, current_ph: float, time_hours: float) -> Tuple[float, float, float]:
        if time_hours <= 0:
            raise ValueError("Time step must be positive")
        target_ph = (self.params.ph_target_min + self.params.ph_target_max) / 2.0
        ph_error = current_ph - target_ph
        acid_dose = 0.0
        base_dose = 0.0
        if abs(ph_error) > self.params.ph_deadband:
            if ph_error > 0:
                max_acid_dose = self.params.ph_adjustment_rate * time_hours
                required_dose = min(max_acid_dose, abs(ph_error) * self.params.proportional_control_factor)
                acid_dose = required_dose
                ph_change = -required_dose / self.ph_state.buffer_capacity
            else:
                max_base_dose = self.params.ph_adjustment_rate * time_hours
                required_dose = min(max_base_dose, abs(ph_error) * self.params.proportional_control_factor)
                base_dose = required_dose
                ph_change = required_dose / self.ph_state.buffer_capacity
            new_ph = current_ph + ph_change
        else:
            new_ph = current_ph
        return new_ph, acid_dose, base_dose

    def update_ph_state(self, nutrient_uptake: Dict[str, float], nutrient_concentrations: Dict[str, float],
                       temperature: float, ec: float, time_hours: float = None) -> PHUpdateResponse:
        required_nutrients = ['NO3', 'NH4', 'PO4']
        for nutrient in required_nutrients:
            if nutrient not in nutrient_uptake:
                raise KeyError(f"Missing nutrient uptake for {nutrient}")
        required_concentrations = ['P-PO4', 'Fe']
        for nutrient in required_concentrations:
            if nutrient not in nutrient_concentrations:
                raise KeyError(f"Missing nutrient concentration for {nutrient}")
        if temperature is None:
            raise ValueError("Temperature must be provided")
        if ec is None or ec < 0:
            raise ValueError("Electrical conductivity (EC) must be provided and non-negative")
        if time_hours is None:
            time_hours = self.params.hours_per_day
        elif time_hours <= 0:
            raise ValueError("Time step must be positive")

        current_ph = self.ph_state.current_ph
        uptake_ph_change = self.calculate_nutrient_uptake_ph_effect(nutrient_uptake)
        natural_drift = self.params.ph_drift_rate * (time_hours / self.params.hours_per_day)
        self.ph_state.buffer_capacity = self.params.ph_buffer_capacity * (1.0 + self.params.ec_buffer_factor * ec)
        ph_before_control = current_ph + uptake_ph_change + natural_drift
        controlled_ph, acid_dosed, base_dosed = self.simulate_ph_control_system(ph_before_control, time_hours)
        available_nutrients = self.calculate_ph_dependent_solubility(controlled_ph, nutrient_concentrations)
        total_phosphate = available_nutrients.get('P-PO4', 0.0) * (self.params.p_molecular_weight / self.params.po4_molecular_weight)
        phosphate_species = self.calculate_phosphate_speciation(controlled_ph, total_phosphate)

        self.ph_state.current_ph = controlled_ph
        self.ph_state.temperature = temperature
        self.ph_state.acid_dosing_rate = acid_dosed / time_hours
        self.ph_state.base_dosing_rate = base_dosed / time_hours
        self.ph_state.last_adjustment_time += time_hours

        return PHUpdateResponse(
            final_ph=controlled_ph,
            ph_change_from_uptake=uptake_ph_change,
            ph_change_from_drift=natural_drift,
            acid_dosed_ml_per_L=acid_dosed,
            base_dosed_ml_per_L=base_dosed,
            buffer_capacity=self.ph_state.buffer_capacity,
            available_nutrients=available_nutrients,
            phosphate_species=phosphate_species,
            nutrient_precipitation={
                nutrient: max(0.0, original - available_nutrients.get(nutrient, original))
                for nutrient, original in nutrient_concentrations.items()
            }
        )

def create_lettuce_ph_model(system_config: Any) -> 'HydroponicPHModel':
    if system_config is None:
        raise ValueError("System configuration must be provided")

    # Get pH parameters
    ph_config = getattr(system_config, 'ph_parameters', None)
    if ph_config is None:
        raise ValueError("ph_parameters section must be provided in configuration")

    # Get additional parameters from other sections to avoid duplicates
    photosynthesis_config = getattr(system_config, 'photosynthesis_parameters', {})

    # Create merged config using existing parameters where available
    merged_config = dict(ph_config)

    # Use existing hours_per_day from photosynthesis_parameters instead of duplicate
    if 'hours_per_day' in photosynthesis_config:
        merged_config['hours_per_day'] = photosynthesis_config['hours_per_day']
    elif 'hours_per_day' not in merged_config:
        # Fallback if neither exists
        merged_config['hours_per_day'] = 24.0

    # Reconstruct nested dictionaries for solubility data
    phosphate_solubility_data = {}
    iron_solubility_data = {}

    # Extract phosphate solubility data
    for key, value in merged_config.items():
        if key.startswith('phosphate_solubility_ph_'):
            ph_value = key.replace('phosphate_solubility_ph_', '').replace('_', '.')
            phosphate_solubility_data[ph_value] = float(value)

    # Extract iron solubility data
    for key, value in merged_config.items():
        if key.startswith('iron_solubility_ph_'):
            ph_value = key.replace('iron_solubility_ph_', '').replace('_', '.')
            iron_solubility_data[ph_value] = float(value)

    merged_config['phosphate_solubility_data'] = phosphate_solubility_data
    merged_config['iron_solubility_data'] = iron_solubility_data

    parameters = PHParameters.from_config(merged_config)
    return HydroponicPHModel(parameters)

"""
INPUT PARAMETERS (from configuration):
- ph_target_min: Minimum target pH for control system
- ph_target_max: Maximum target pH for control system
- ph_buffer_capacity: Base buffer capacity (mEq/L)
- ph_drift_rate: Natural pH drift rate (pH units/day)
- nitrate_acidification_factor: pH change per mg N from nitrate uptake
- ammonium_alkalinization_factor: pH change per mg N from ammonium uptake
- phosphate_acidification_factor: pH change per mg P from phosphate uptake
- carbonate_buffer_pka: pKa for carbonate buffer system
- phosphate_buffer_pka1: First pKa for phosphate system
- phosphate_buffer_pka2: Second pKa for phosphate system
- phosphate_buffer_pka3: Third pKa for phosphate system
- ph_adjustment_rate: Maximum pH adjustment rate (pH units/hour)
- ph_deadband: pH control deadband (pH units)
- temperature_correction_factor: pH change per °C from 25°C
- ec_buffer_factor: Buffer capacity multiplier per EC unit (dS/m)
- proportional_control_factor: Proportional control multiplier for dosing
- hours_per_day: Hours per day for calculations
- current_ph: Initial pH of the solution
- total_alkalinity: Total alkalinity (mEq/L)
- carbonate_conc: Carbonate concentration (mg/L as HCO3-)
- phosphate_total: Total phosphate concentration (mg/L as P)
- ionic_strength: Ionic strength of solution (M)
- ph_min_limit: Minimum allowable pH
- ph_max_limit: Maximum allowable pH
- phosphate_solubility_data: Dictionary of phosphate solubility (mg/L) at different pH values
- iron_solubility_data: Dictionary of iron solubility (mg/L) at different pH values
- calcium_phosphate_ksp: Solubility product for Ca3(PO4)2
- magnesium_phosphate_ksp: Solubility product for Mg3(PO4)2

INPUT VARIABLES:
- total_carbonate: Total carbonate alkalinity (mEq/L)
- free_co2: Dissolved CO2 concentration (mg/L)
- temperature: Solution temperature (°C)
- nutrient_uptake: Nutrient uptake rates (mg/day) for NO3, NH4, PO4
- nutrient_concentrations: Current nutrient concentrations (mg/L) for P-PO4, Fe
- ec: Electrical conductivity (dS/m)
- time_hours: Time step for simulation (hours)

OUTPUT VARIABLES:
- PHUpdateResponse:
  - final_ph: Final pH after update
  - ph_change_from_uptake: pH change due to nutrient uptake
  - ph_change_from_drift: pH change due to natural drift
  - acid_dosed_ml_per_L: Amount of acid dosed (mL/L)
  - base_dosed_ml_per_L: Amount of base dosed (mL/L)
  - buffer_capacity: Updated buffer capacity (mEq/L)
  - available_nutrients: Nutrient concentrations after solubility effects (mg/L)
  - phosphate_species: Concentrations of phosphate species (mg/L)
  - nutrient_precipitation: Precipitated nutrients (mg/L)

FUNCTION EXPLANATIONS 
This model manages the pH (acidity/alkalinity) of a hydroponic nutrient solution, critical for plant nutrient uptake. Think of it as maintaining the perfect balance in a pool so plants can absorb nutrients effectively.

1. calculate_henderson_hasselbalch_ph:
   - Calculates pH using the Henderson-Hasselbalch equation: pH = pKa + log([HCO3-]/[H2CO3]).
   - Like a chemical recipe, it determines how acidic or basic the solution is based on carbonate and CO2 levels.

2. calculate_phosphate_speciation:
   - Determines the forms of phosphate (H3PO4, H2PO4-, HPO4--, PO4---) at the current pH.
   - Like how sugar dissolves differently in hot vs. cold water, phosphate changes forms with pH, affecting plant availability.

3. calculate_nutrient_uptake_ph_effect:
   - Calculates pH changes from nutrient uptake: nitrate lowers pH, ammonium raises it, phosphate slightly lowers it.
   - Like how eating certain foods affects your body's pH, plant nutrient uptake alters the solution's acidity.

4. calculate_ph_dependent_solubility:
   - Determines nutrient availability based on pH, accounting for precipitation: nutrients like phosphate and iron become unavailable at certain pH levels.
   - Like ingredients settling out of a soup if conditions aren't right, nutrients can form solids plants can't use.

5. simulate_ph_control_system:
   - Simulates automated pH adjustment by dosing acid or base: dose = error * proportional_factor.
   - Like a smart thermostat, it adjusts the solution to keep pH in the optimal range for plants.

6. update_ph_state:
   - Updates the pH system daily, integrating uptake effects, natural drift, and control system actions.
   - Like a daily checkup, it ensures the solution stays balanced for optimal plant growth.

PRACTICAL APPLICATIONS:
- Prevents nutrient lockout by maintaining optimal pH for nutrient absorption.
- Optimizes nutrient availability to maximize plant growth.
- Prevents precipitation that could clog hydroponic systems.
- Stabilizes pH despite changing plant uptake patterns.
- Guides growers on when to adjust nutrient solutions manually.
"""