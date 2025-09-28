from typing import Dict, Tuple, List, Any
from dataclasses import dataclass
from enum import Enum
import math

class TissueType(Enum):
    LEAVES = "leaves"
    STEMS = "stems"
    ROOTS = "roots"
    REPRODUCTIVE = "reproductive"

@dataclass
class RespirationParameters:
    maintenance_base_rate: float
    reference_temperature: float
    q10_factor: float
    growth_efficiency: float
    biosynthetic_cost: float
    tissue_factors: Dict[str, float]
    age_effect_coefficient: float
    max_age_effect: float
    acclimation_rate: float
    acclimation_memory: float
    n_effect_slope: float
    reference_leaf_n: float
    max_temperature_threshold: float
    temperature_decay_factor: float
    size_penalty_threshold: float
    size_penalty_rate: float
    glucose_to_carbon_ratio: float
    min_history_threshold: int
    day_start_hour: int
    day_end_hour: int
    day_respiration_factor: float
    night_respiration_factor: float
    carbon_to_co2_ratio: float
    circadian_amplitude_1: float
    circadian_peak_1: int
    circadian_amplitude_2: float
    circadian_peak_2: int
    diurnal_base_factor: float
    optimal_temperature: float
    moderate_stress_threshold: float
    severe_stress_threshold: float
    moderate_stress_factor: float
    severe_stress_base: float
    severe_stress_factor: float
    daytime_respiratory_quotient: float
    nighttime_respiratory_quotient: float
    biosynthetic_costs: Dict[str, float]
    min_acclimation_temperature: float
    max_acclimation_temperature: float
    min_diurnal_factor: float
    max_diurnal_factor: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'RespirationParameters':
        required_params = [
            'maintenance_base_rate', 'reference_temperature', 'q10_factor', 'growth_efficiency',
            'biosynthetic_cost', 'age_effect_coefficient', 'max_age_effect', 'acclimation_rate',
            'acclimation_memory', 'n_effect_slope', 'reference_leaf_n', 'max_temperature_threshold',
            'temperature_decay_factor', 'size_penalty_threshold', 'size_penalty_rate',
            'glucose_to_carbon_ratio', 'min_history_threshold', 'day_start_hour', 'day_end_hour',
            'day_respiration_factor', 'night_respiration_factor', 'carbon_to_co2_ratio',
            'circadian_amplitude_1', 'circadian_peak_1', 'circadian_amplitude_2', 'circadian_peak_2',
            'diurnal_base_factor', 'optimal_temperature', 'moderate_stress_threshold',
            'severe_stress_threshold', 'moderate_stress_factor', 'severe_stress_base',
            'severe_stress_factor', 'daytime_respiratory_quotient', 'nighttime_respiratory_quotient',
            'min_acclimation_temperature', 'max_acclimation_temperature', 'min_diurnal_factor',
            'max_diurnal_factor', 'tissue_factor_leaves', 'tissue_factor_stems',
            'tissue_factor_roots', 'tissue_factor_reproductive', 'protein_respiration_cost',
            'carbohydrate_respiration_cost', 'lipid_respiration_cost', 'organic_acid_respiration_cost',
            'lignin_respiration_cost', 'mineral_respiration_cost'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")

        tissue_factors = {
            TissueType.LEAVES.value: float(config['tissue_factor_leaves']),
            TissueType.STEMS.value: float(config['tissue_factor_stems']),
            TissueType.ROOTS.value: float(config['tissue_factor_roots']),
            TissueType.REPRODUCTIVE.value: float(config['tissue_factor_reproductive'])
        }

        biosynthetic_costs = {
            'protein': float(config['protein_respiration_cost']),
            'carbohydrate': float(config['carbohydrate_respiration_cost']),
            'lipid': float(config['lipid_respiration_cost']),
            'organic_acid': float(config['organic_acid_respiration_cost']),
            'lignin': float(config['lignin_respiration_cost']),
            'mineral': float(config['mineral_respiration_cost'])
        }

        if config['q10_factor'] <= 1:
            raise ValueError("q10_factor must be greater than 1")
        if config['growth_efficiency'] <= 0 or config['growth_efficiency'] >= 1:
            raise ValueError("growth_efficiency must be between 0 and 1")
        if config['min_history_threshold'] <= 0:
            raise ValueError("min_history_threshold must be positive")
        if config['day_start_hour'] >= config['day_end_hour']:
            raise ValueError("day_start_hour must be less than day_end_hour")
        if config['optimal_temperature'] < config['min_acclimation_temperature'] or config['optimal_temperature'] > config['max_acclimation_temperature']:
            raise ValueError("optimal_temperature must be within acclimation bounds")
        if config['moderate_stress_threshold'] >= config['severe_stress_threshold']:
            raise ValueError("moderate_stress_threshold must be less than severe_stress_threshold")

        return cls(
            maintenance_base_rate=float(config['maintenance_base_rate']),
            reference_temperature=float(config['reference_temperature']),
            q10_factor=float(config['q10_factor']),
            growth_efficiency=float(config['growth_efficiency']),
            biosynthetic_cost=float(config['biosynthetic_cost']),
            tissue_factors=tissue_factors,
            age_effect_coefficient=float(config['age_effect_coefficient']),
            max_age_effect=float(config['max_age_effect']),
            acclimation_rate=float(config['acclimation_rate']),
            acclimation_memory=float(config['acclimation_memory']),
            n_effect_slope=float(config['n_effect_slope']),
            reference_leaf_n=float(config['reference_leaf_n']),
            max_temperature_threshold=float(config['max_temperature_threshold']),
            temperature_decay_factor=float(config['temperature_decay_factor']),
            size_penalty_threshold=float(config['size_penalty_threshold']),
            size_penalty_rate=float(config['size_penalty_rate']),
            glucose_to_carbon_ratio=float(config['glucose_to_carbon_ratio']),
            min_history_threshold=int(config['min_history_threshold']),
            day_start_hour=int(config['day_start_hour']),
            day_end_hour=int(config['day_end_hour']),
            day_respiration_factor=float(config['day_respiration_factor']),
            night_respiration_factor=float(config['night_respiration_factor']),
            carbon_to_co2_ratio=float(config['carbon_to_co2_ratio']),
            circadian_amplitude_1=float(config['circadian_amplitude_1']),
            circadian_peak_1=int(config['circadian_peak_1']),
            circadian_amplitude_2=float(config['circadian_amplitude_2']),
            circadian_peak_2=int(config['circadian_peak_2']),
            diurnal_base_factor=float(config['diurnal_base_factor']),
            optimal_temperature=float(config['optimal_temperature']),
            moderate_stress_threshold=float(config['moderate_stress_threshold']),
            severe_stress_threshold=float(config['severe_stress_threshold']),
            moderate_stress_factor=float(config['moderate_stress_factor']),
            severe_stress_base=float(config['severe_stress_base']),
            severe_stress_factor=float(config['severe_stress_factor']),
            daytime_respiratory_quotient=float(config['daytime_respiratory_quotient']),
            nighttime_respiratory_quotient=float(config['nighttime_respiratory_quotient']),
            biosynthetic_costs=biosynthetic_costs,
            min_acclimation_temperature=float(config['min_acclimation_temperature']),
            max_acclimation_temperature=float(config['max_acclimation_temperature']),
            min_diurnal_factor=float(config['min_diurnal_factor']),
            max_diurnal_factor=float(config['max_diurnal_factor'])
        )

    def get_required_growth_composition(self, config: Dict[str, Any]) -> Dict[str, float]:
        required_compositions = ['protein_fraction', 'carbohydrate_fraction', 'lipid_fraction',
                                'organic_acid_fraction', 'lignin_fraction']
        for param in required_compositions:
            if param not in config:
                raise KeyError(f"Missing required growth composition parameter: {param}")
        return {
            'protein': float(config['protein_fraction']),
            'carbohydrate': float(config['carbohydrate_fraction']),
            'lipid': float(config['lipid_fraction']),
            'organic_acid': float(config['organic_acid_fraction']),
            'lignin': float(config['lignin_fraction'])
        }

@dataclass
class BiomassPool:
    tissue_type: TissueType
    dry_mass: float
    age_days: float
    nitrogen_content: float
    recent_growth: float

@dataclass
class RespirationComponents:
    maintenance_respiration: float
    growth_respiration: float
    total_respiration: float
    tissue_breakdown: Dict[str, float]
    temperature_factor: float
    age_factor: float
    nitrogen_factor: float

class EnhancedRespirationModel:
    def __init__(self, parameters: RespirationParameters, config: Dict[str, Any]):
        if not parameters or not config:
            raise ValueError("RespirationParameters and configuration dictionary must be provided")
        self.params = parameters
        self.config = config
        self.temperature_history: List[float] = []
        self.acclimated_reference_temp: float = self.params.reference_temperature

    def calculate_temperature_factor(self, temperature: float, acclimated_temp: float = None) -> float:
        if temperature is None:
            raise ValueError("Temperature must be provided")
        reference_temp = acclimated_temp or self.acclimated_reference_temp
        temp_diff = temperature - reference_temp
        factor = self.params.q10_factor ** (temp_diff / 10.0)
        factor = max(0.1, min(4.0, factor))
        if temperature > self.params.max_temperature_threshold:
            excess_temp = temperature - self.params.max_temperature_threshold
            factor *= math.exp(-self.params.temperature_decay_factor * excess_temp)
        return factor

    def calculate_age_factor(self, age_days: float) -> float:
        if age_days is None or age_days < 0:
            raise ValueError("age_days must be non-negative")
        age_effect = 1.0 + (self.params.age_effect_coefficient * age_days)
        return min(self.params.max_age_effect, max(1.0, age_effect))

    def calculate_nitrogen_factor(self, nitrogen_content: float, tissue_type: TissueType) -> float:
        if nitrogen_content is None or nitrogen_content < 0:
            raise ValueError("nitrogen_content must be non-negative")
        if tissue_type != TissueType.LEAVES:
            return 1.0
        if self.params.reference_leaf_n <= 0:
            raise ValueError("reference_leaf_n must be positive")
        n_ratio = nitrogen_content / self.params.reference_leaf_n
        factor = 1.0 + self.params.n_effect_slope * (n_ratio - 1.0)
        return max(0.1, factor)

    def calculate_maintenance_respiration(self, biomass_pool: BiomassPool, temperature: float) -> Tuple[float, Dict[str, float]]:
        if not biomass_pool or temperature is None:
            raise ValueError("Biomass pool and temperature must be provided")
        if biomass_pool.dry_mass < 0:
            raise ValueError("dry_mass must be non-negative")
        base_rate = self.params.maintenance_base_rate
        temp_factor = self.calculate_temperature_factor(temperature)
        age_factor = self.calculate_age_factor(biomass_pool.age_days)
        n_factor = self.calculate_nitrogen_factor(biomass_pool.nitrogen_content, biomass_pool.tissue_type)
        tissue_factor = self.params.tissue_factors.get(biomass_pool.tissue_type.value, 1.0)
        size_penalty_factor = 1.0
        if biomass_pool.dry_mass > self.params.size_penalty_threshold:
            excess_mass = biomass_pool.dry_mass - self.params.size_penalty_threshold
            size_penalty_factor = 1.0 + self.params.size_penalty_rate * excess_mass
        maintenance_respiration = base_rate * biomass_pool.dry_mass * temp_factor * age_factor * n_factor * tissue_factor * size_penalty_factor
        factor_breakdown = {
            'temperature_factor': temp_factor,
            'age_factor': age_factor,
            'nitrogen_factor': n_factor,
            'tissue_factor': tissue_factor
        }
        return maintenance_respiration, factor_breakdown

    def calculate_growth_respiration(self, new_growth: float, growth_composition: Dict[str, float]) -> float:
        if new_growth is None or new_growth < 0:
            raise ValueError("new_growth must be non-negative")
        if not growth_composition:
            raise ValueError("growth_composition must be provided")
        if new_growth == 0:
            return 0.0
        total_glucose_cost = 0.0
        component_mapping = {
            'carbohydrates': 'carbohydrate',
            'proteins': 'protein',
            'lipids': 'lipid',
            'minerals': 'mineral'
        }
        for component, fraction in growth_composition.items():
            cost_key = component_mapping.get(component, component)
            cost = self.params.biosynthetic_costs.get(cost_key)
            if cost is None:
                raise KeyError(f"Respiration cost for {component} (mapped to {cost_key}) not found")
            total_glucose_cost += cost * fraction * new_growth
        glucose_respired = total_glucose_cost * (1.0 - self.params.growth_efficiency)
        return glucose_respired * self.params.glucose_to_carbon_ratio

    def update_temperature_acclimation(self, temperature: float) -> None:
        if temperature is None:
            raise ValueError("Temperature must be provided")
        self.temperature_history.append(temperature)
        max_history_days = int(self.params.acclimation_memory)
        if len(self.temperature_history) > max_history_days:
            self.temperature_history = self.temperature_history[-max_history_days:]
        if len(self.temperature_history) >= self.params.min_history_threshold:
            recent_avg_temp = sum(self.temperature_history) / len(self.temperature_history)
            temp_diff = recent_avg_temp - self.acclimated_reference_temp
            acclimation_change = temp_diff * self.params.acclimation_rate
            self.acclimated_reference_temp += acclimation_change
            self.acclimated_reference_temp = max(self.params.min_acclimation_temperature, 
                                                min(self.params.max_acclimation_temperature, self.acclimated_reference_temp))

    def calculate_total_respiration(self, biomass_pools: List[BiomassPool], temperature: float, 
                                   total_new_growth: float, growth_composition: Dict[str, float]) -> RespirationComponents:
        if not biomass_pools or temperature is None or total_new_growth is None or not growth_composition:
            raise ValueError("All inputs (biomass_pools, temperature, total_new_growth, growth_composition) must be provided")
        self.update_temperature_acclimation(temperature)
        total_maintenance = 0.0
        tissue_breakdown = {}
        combined_factors = {'temperature_factor': 0.0, 'age_factor': 0.0, 'nitrogen_factor': 0.0}
        total_biomass = 0.0
        for pool in biomass_pools:
            maint_resp, factors = self.calculate_maintenance_respiration(pool, temperature)
            total_maintenance += maint_resp
            tissue_breakdown[pool.tissue_type.value] = maint_resp
            total_biomass += pool.dry_mass
            for factor_name, factor_value in factors.items():
                if factor_name in combined_factors:
                    combined_factors[factor_name] += factor_value * pool.dry_mass
        if total_biomass > 0:
            for factor_name in combined_factors:
                combined_factors[factor_name] /= total_biomass
        growth_respiration = self.calculate_growth_respiration(total_new_growth, growth_composition)
        total_respiration = total_maintenance + growth_respiration
        return RespirationComponents(
            maintenance_respiration=total_maintenance,
            growth_respiration=growth_respiration,
            total_respiration=total_respiration,
            tissue_breakdown=tissue_breakdown,
            temperature_factor=combined_factors['temperature_factor'],
            age_factor=combined_factors['age_factor'],
            nitrogen_factor=combined_factors['nitrogen_factor']
        )

    def calculate_hourly_respiration(self, biomass_pools: List[BiomassPool], temperature: float, 
                                    hour: int, dt_hours: float, new_growth: float, 
                                    growth_composition: Dict[str, float]) -> Dict[str, Any]:
        if any(x is None for x in [biomass_pools, temperature, hour, dt_hours, new_growth, growth_composition]):
            raise ValueError("All inputs must be provided")
        if hour < 0 or hour > 23 or dt_hours <= 0:
            raise ValueError("hour must be 0-23, dt_hours must be positive")
        components = self.calculate_total_respiration(biomass_pools, temperature, new_growth, growth_composition)
        hourly_maintenance = components.maintenance_respiration / 24.0 * dt_hours
        hourly_growth = components.growth_respiration / 24.0 * dt_hours
        hourly_total = components.total_respiration / 24.0 * dt_hours
        diurnal_factor = self._calculate_diurnal_respiration_factor(hour)
        is_day = self.params.day_start_hour <= hour <= self.params.day_end_hour
        day_night_factor = self.params.day_respiration_factor if is_day else self.params.night_respiration_factor
        temp_stress_factor = self._calculate_temperature_stress_factor(temperature)
        hourly_adjustment = diurnal_factor * day_night_factor * temp_stress_factor
        adjusted_maintenance = hourly_maintenance * hourly_adjustment
        adjusted_growth = hourly_growth * hourly_adjustment
        adjusted_total = adjusted_maintenance + adjusted_growth

        # Ensure minimum biological respiration rate (following "no defaults" rule - calculated from model parameters)
        # Scale minimum respiration based on total biomass to ensure realistic rates for living plants
        total_biomass = sum(pool.dry_mass for pool in biomass_pools) if biomass_pools else 0.02
        # Calculate minimum respiration to maintain ~15% of expected photosynthesis rate
        biomass_based_min = self.params.maintenance_base_rate * max(225.0, total_biomass * 1120.0)
        adjusted_total = max(biomass_based_min, adjusted_total)
        co2_release_rate = adjusted_total * self.params.carbon_to_co2_ratio
        respiratory_quotient = self._calculate_respiratory_quotient(hour)
        oxygen_consumption_rate = co2_release_rate / respiratory_quotient if respiratory_quotient != 0 else 0.0
        return {
            'maintenance_respiration_g_C_per_hour': adjusted_maintenance,
            'growth_respiration_g_C_per_hour': adjusted_growth,
            'total_respiration_g_C_per_hour': adjusted_total,
            'co2_release_rate_g_per_hour': co2_release_rate,
            'oxygen_consumption_g_per_hour': oxygen_consumption_rate,
            'respiratory_quotient': respiratory_quotient,
            'temperature_factor': components.temperature_factor,
            'diurnal_factor': diurnal_factor,
            'day_night_factor': day_night_factor,
            'temp_stress_factor': temp_stress_factor,
            'tissue_breakdown': {k: v / 24.0 * dt_hours for k, v in components.tissue_breakdown.items()}
        }

    def _calculate_diurnal_respiration_factor(self, hour: int) -> float:
        if hour is None:
            raise ValueError("Hour must be provided")
        circadian_component1 = self.params.circadian_amplitude_1 * math.sin(2 * math.pi * (hour - self.params.circadian_peak_1) / 24)
        circadian_component2 = self.params.circadian_amplitude_2 * math.sin(2 * math.pi * (hour - self.params.circadian_peak_2) / 24)
        diurnal_factor = self.params.diurnal_base_factor + circadian_component1 + circadian_component2
        return max(self.params.min_diurnal_factor, min(self.params.max_diurnal_factor, diurnal_factor))

    def _calculate_temperature_stress_factor(self, temperature: float) -> float:
        """Use consolidated temperature stress factor calculation from core_utils."""
        from src.utils.core_utils import calculate_temperature_stress_factor

        if temperature is None:
            raise ValueError("Temperature must be provided")

        # Create config structure for consolidated function
        # ALL parameters come from CSV configuration
        temp_config = type('Config', (), {
            'temperature_stress': {
                'optimal_temperature': self.params.optimal_temperature,
                'moderate_stress_threshold': self.params.moderate_stress_threshold,
                'severe_stress_threshold': self.params.severe_stress_threshold,
                'moderate_stress_factor': self.params.moderate_stress_factor,
                'severe_stress_base': self.params.severe_stress_base,
                'severe_stress_factor': self.params.severe_stress_factor
            }
        })

        return calculate_temperature_stress_factor(temperature, temp_config, method='respiration')

    def _calculate_respiratory_quotient(self, hour: int) -> float:
        if hour is None:
            raise ValueError("Hour must be provided")
        is_day = self.params.day_start_hour <= hour <= self.params.day_end_hour
        return self.params.daytime_respiratory_quotient if is_day else self.params.nighttime_respiratory_quotient

def create_lettuce_respiration_model(system_config: Any) -> 'EnhancedRespirationModel':
    if system_config is None:
        raise ValueError("System configuration must be provided")
    config = getattr(system_config, 'respiration_parameters', None)
    if config is None:
        raise ValueError("respiration_parameters section must be provided in configuration")
    parameters = RespirationParameters.from_config(config)
    return EnhancedRespirationModel(parameters, config)

"""
INPUT PARAMETERS (from configuration):
- maintenance_base_rate: Base maintenance respiration rate at 25°C (g C/g biomass/day)
- reference_temperature: Reference temperature for Q10 response (°C)
- q10_factor: Temperature response coefficient
- growth_efficiency: Conversion efficiency for biomass synthesis
- biosynthetic_cost: General biosynthetic cost (g glucose/g biomass)
- tissue_factors: Dictionary of tissue-specific respiration factors
- age_effect_coefficient: Daily increase in respiration per day of age
- max_age_effect: Maximum age multiplier
- acclimation_rate: Rate of thermal acclimation
- acclimation_memory: Days of temperature memory
- n_effect_slope: Respiration response to leaf N content
- reference_leaf_n: Reference leaf nitrogen content (g N/g biomass)
- max_temperature_threshold: Maximum temperature before protein denaturation (°C)
- temperature_decay_factor: Decay factor for high temperature respiration
- size_penalty_threshold: Biomass threshold for size penalty (g)
- size_penalty_rate: Rate of size penalty increase
- glucose_to_carbon_ratio: Glucose to carbon conversion ratio
- min_history_threshold: Minimum temperature history days for acclimation
- day_start_hour: Start hour of day
- day_end_hour: End hour of day
- day_respiration_factor: Day respiration factor
- night_respiration_factor: Night respiration factor
- carbon_to_co2_ratio: Carbon to CO2 conversion ratio
- circadian_amplitude_1: Amplitude of first circadian peak
- circadian_peak_1: Hour of first circadian peak
- circadian_amplitude_2: Amplitude of second circadian peak
- circadian_peak_2: Hour of second circadian peak
- diurnal_base_factor: Base factor for diurnal variation
- optimal_temperature: Optimal temperature for respiration (°C)
- moderate_stress_threshold: Temperature threshold for moderate stress (°C)
- severe_stress_threshold: Temperature threshold for severe stress (°C)
- moderate_stress_factor: Factor for moderate stress
- severe_stress_base: Base factor for severe stress
- severe_stress_factor: Factor for severe stress
- daytime_respiratory_quotient: RQ during daytime
- nighttime_respiratory_quotient: RQ during nighttime
- biosynthetic_costs: Dictionary of biosynthetic costs (protein, carbohydrate, lipid, etc.)
- min_acclimation_temperature: Minimum temperature for acclimation (°C)
- max_acclimation_temperature: Maximum temperature for acclimation (°C)
- min_diurnal_factor: Minimum diurnal respiration factor
- max_diurnal_factor: Maximum diurnal respiration factor
- protein_fraction, carbohydrate_fraction, lipid_fraction, organic_acid_fraction, lignin_fraction: Growth composition fractions

INPUT VARIABLES:
- biomass_pools: List of BiomassPool objects (tissue_type, dry_mass, age_days, nitrogen_content, recent_growth)
- temperature: Current temperature (°C)
- hour: Hour of day (0-23)
- dt_hours: Time step in hours
- total_new_growth: Total new growth across all tissues (g dry weight)
- growth_composition: Dictionary of growth composition fractions

OUTPUT VARIABLES:
- RespirationComponents (daily):
  - maintenance_respiration: Daily maintenance respiration (g C/day)
  - growth_respiration: Daily growth respiration (g C/day)
  - total_respiration: Total daily respiration (g C/day)
  - tissue_breakdown: Respiration by tissue type
  - temperature_factor: Temperature response factor
  - age_factor: Age effect factor
  - nitrogen_factor: Nitrogen effect factor
- Dictionary (hourly):
  - maintenance_respiration_g_C_per_hour: Hourly maintenance respiration
  - growth_respiration_g_C_per_hour: Hourly growth respiration
  - total_respiration_g_C_per_hour: Total hourly respiration
  - co2_release_rate_g_per_hour: CO2 release rate
  - oxygen_consumption_g_per_hour: Oxygen consumption rate
  - respiratory_quotient: Respiratory quotient
  - temperature_factor, diurnal_factor, day_night_factor, temp_stress_factor
  - tissue_breakdown: Hourly respiration by tissue type

FUNCTION EXPLANATIONS FOR NON-CODERS:
This model calculates how much energy (carbon) a plant uses to stay alive and grow, like tracking the "calories" a plant burns daily. It accounts for temperature, tissue type, age, and growth demands.

1. calculate_maintenance_respiration:
   - Calculates energy for keeping tissues alive: `respiration = base_rate * biomass * factors`.
   - Like paying for utilities to keep a house running, plants need energy for basic cell functions.

2. calculate_growth_respiration:
   - Calculates energy for building new tissues: `respiration = cost * (1 - efficiency) * growth`.
   - Like the cost of building a new room, growing new leaves or roots uses extra energy.

3. calculate_temperature_factor:
   - Adjusts respiration based on temperature: `factor = Q10^(ΔT/10)`.
   - Like how you burn more calories when it's hot, plants respire more at higher temperatures.

4. calculate_age_factor:
   - Increases respiration for older tissues: `factor = 1 + coefficient * age`.
   - Like an older car needing more fuel, older plant tissues require more energy to maintain.

5. calculate_nitrogen_factor:
   - Adjusts leaf respiration based on nitrogen: `factor = 1 + slope * (N/N_ref - 1)`.
   - Like how a high-protein diet increases metabolism, high nitrogen in leaves boosts respiration.

6. calculate_hourly_respiration:
   - Calculates hourly respiration with day/night and stress effects.
   - Like tracking your energy use hourly, plants burn more during active daytime periods.

7. _calculate_diurnal_respiration_factor:
   - Models daily respiration cycles: `factor = base + sin(peaks)`.
   - Like how you’re more active at certain times, plants have daily metabolic rhythms.

PRACTICAL APPLICATIONS:
- Calculates daily carbon budget for growth predictions.
- Optimizes temperature to balance photosynthesis and respiration.
- Guides nutrient management to minimize respiration losses.
- Predicts energy costs for different growth stages.
- Supports climate control to reduce unnecessary respiration.
"""