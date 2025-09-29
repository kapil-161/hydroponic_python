"""
Simulator Range Validation

Validates that each simulator produces scientifically reasonable output ranges
based on plant physiology literature and hydroponic system constraints.
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import math

@dataclass
class RangeValidation:
    """Validation range for a simulator output"""
    parameter_name: str
    expected_min: float
    expected_max: float
    units: str
    description: str
    warning_threshold: float = 0.1  # 10% tolerance

class SimulatorRangeValidator:
    """Validates simulator output ranges against scientific literature"""
    
    def __init__(self):
        self.validation_ranges = self._initialize_validation_ranges()
    
    def _initialize_validation_ranges(self) -> Dict[str, List[RangeValidation]]:
        """Initialize expected ranges for each simulator based on plant physiology"""
        
        return {
            'photosynthesis_simulator': [
                RangeValidation('net_assimilation_rate', 0.0, 50.0, 'μmol CO₂/m²/s', 
                               'Net CO₂ assimilation rate for lettuce under optimal conditions'),
                RangeValidation('gross_photosynthesis_rate', 5.0, 60.0, 'μmol CO₂/m²/s',
                               'Gross photosynthesis rate including respiration'),
                RangeValidation('light_use_efficiency', 0.0, 0.5, 'mol CO₂/mol photons',
                               'Light use efficiency - typically 0.05-0.1 for C3 plants'),
                RangeValidation('co2_uptake_rate', 0.0, 50.0, 'μmol CO₂/m²/s',
                               'CO₂ uptake rate during photosynthesis'),
                RangeValidation('light_stress_factor', 0.0, 1.0, 'dimensionless',
                               'Light stress factor (1.0 = no stress)'),
                RangeValidation('temperature_stress_factor', 0.0, 1.0, 'dimensionless',
                               'Temperature stress factor (1.0 = no stress)'),
            ],
            
            'respiration_simulator': [
                RangeValidation('maintenance_respiration_rate', 0.1, 10.0, 'μmol CO₂/m²/s',
                               'Maintenance respiration rate'),
                RangeValidation('growth_respiration_rate', 0.0, 5.0, 'μmol CO₂/m²/s',
                               'Growth respiration rate'),
                RangeValidation('total_respiration_rate', 0.1, 15.0, 'μmol CO₂/m²/s',
                               'Total respiration rate'),
                RangeValidation('respiratory_quotient', 0.7, 1.3, 'dimensionless',
                               'Respiratory quotient (CO₂ produced/O₂ consumed)'),
                RangeValidation('q10_factor', 1.5, 3.5, 'dimensionless',
                               'Q10 temperature coefficient for respiration'),
            ],
            
            'biomass_allocation_simulator': [
                RangeValidation('leaf_allocation_fraction', 0.3, 0.8, 'dimensionless',
                               'Fraction of biomass allocated to leaves'),
                RangeValidation('stem_allocation_fraction', 0.1, 0.4, 'dimensionless',
                               'Fraction of biomass allocated to stems'),
                RangeValidation('root_allocation_fraction', 0.1, 0.6, 'dimensionless',
                               'Fraction of biomass allocated to roots'),
                RangeValidation('allocation_efficiency', 0.7, 1.0, 'dimensionless',
                               'Biomass allocation efficiency'),
                RangeValidation('total_biomass', 0.0, 1000.0, 'g',
                               'Total plant biomass in grams'),
            ],
            
            'phenology_simulator': [
                RangeValidation('thermal_time', 0.0, 2000.0, '°C-day',
                               'Cumulative thermal time for lettuce'),
                RangeValidation('development_index', 0.0, 1.0, 'dimensionless',
                               'Phenological development index'),
                RangeValidation('bolting_risk', 0.0, 1.0, 'dimensionless',
                               'Risk of bolting (1.0 = high risk)'),
                RangeValidation('growth_stage_duration', 1.0, 100.0, 'days',
                               'Duration of current growth stage'),
                RangeValidation('node_number', 0.0, 30.0, 'count',
                               'Number of nodes developed'),
            ],
            
            'stress_models_simulator': [
                RangeValidation('temperature_stress', 0.0, 1.0, 'dimensionless',
                               'Temperature stress index (1.0 = severe stress)'),
                RangeValidation('water_stress', 0.0, 1.0, 'dimensionless',
                               'Water stress index (1.0 = severe stress)'),
                RangeValidation('nutrient_stress', 0.0, 1.0, 'dimensionless',
                               'Nutrient stress index (1.0 = severe stress)'),
                RangeValidation('light_stress', 0.0, 1.0, 'dimensionless',
                               'Light stress index (1.0 = severe stress)'),
                RangeValidation('integrated_stress', 0.0, 1.0, 'dimensionless',
                               'Integrated stress factor'),
                RangeValidation('acclimation_factor', 0.5, 1.0, 'dimensionless',
                               'Stress acclimation factor'),
            ],
            
            'water_uptake_simulator': [
                RangeValidation('water_uptake_rate', 0.0, 50.0, 'g/m²/s',
                               'Water uptake rate from roots'),
                RangeValidation('transpiration_rate', 0.0, 40.0, 'g/m²/s',
                               'Transpiration rate from leaves'),
                RangeValidation('water_use_efficiency', 0.5, 5.0, 'g biomass/g water',
                               'Water use efficiency'),
                RangeValidation('leaf_water_potential', -3.0, -0.5, 'MPa',
                               'Leaf water potential'),
                RangeValidation('root_water_potential', -2.0, -0.1, 'MPa',
                               'Root water potential'),
            ],
            
            'nutrient_models_simulator': [
                RangeValidation('nitrogen_uptake_rate', 0.0, 0.5, 'g N/m²/day',
                               'Nitrogen uptake rate'),
                RangeValidation('phosphorus_uptake_rate', 0.0, 0.1, 'g P/m²/day',
                               'Phosphorus uptake rate'),
                RangeValidation('potassium_uptake_rate', 0.0, 0.8, 'g K/m²/day',
                               'Potassium uptake rate'),
                RangeValidation('nutrient_use_efficiency', 0.3, 1.0, 'dimensionless',
                               'Nutrient use efficiency'),
                RangeValidation('nutrient_availability', 0.0, 1.0, 'dimensionless',
                               'Relative nutrient availability'),
            ],
            
            'canopy_architecture_simulator': [
                RangeValidation('leaf_area_index', 0.0, 8.0, 'm²/m²',
                               'Leaf area index'),
                RangeValidation('canopy_height', 0.0, 1.0, 'm',
                               'Canopy height in meters'),
                RangeValidation('light_interception', 0.0, 0.95, 'dimensionless',
                               'Fraction of light intercepted'),
                RangeValidation('leaf_angle', 0.0, 90.0, 'degrees',
                               'Average leaf angle'),
                RangeValidation('canopy_closure', 0.0, 1.0, 'dimensionless',
                               'Fraction of ground covered by canopy'),
            ],
            
            'ph_model_simulator': [
                RangeValidation('ph', 4.0, 9.0, 'pH units',
                               'Solution pH level'),
                RangeValidation('ph_stability', 0.0, 1.0, 'dimensionless',
                               'pH stability factor'),
                RangeValidation('buffer_capacity', 0.0, 50.0, 'mmol/L/pH',
                               'Buffer capacity'),
                RangeValidation('nutrient_solubility_factor', 0.0, 1.0, 'dimensionless',
                               'Effect of pH on nutrient solubility'),
            ],
            
            'root_system_simulator': [
                RangeValidation('root_mass', 0.0, 100.0, 'g',
                               'Root system mass'),
                RangeValidation('root_length', 0.0, 1000.0, 'm',
                               'Total root length'),
                RangeValidation('root_surface_area', 0.0, 2.0, 'm²',
                               'Root surface area'),
                RangeValidation('root_density', 0.0, 10.0, 'cm/cm³',
                               'Root length density'),
                RangeValidation('root_activity', 0.0, 1.0, 'dimensionless',
                               'Root activity factor'),
            ],
            
            'environmental_control_simulator': [
                RangeValidation('air_temperature', 15.0, 35.0, '°C',
                               'Controlled air temperature'),
                RangeValidation('humidity', 40.0, 90.0, '%',
                               'Relative humidity'),
                RangeValidation('light_intensity', 0.0, 2000.0, 'μmol/m²/s',
                               'Photosynthetic photon flux density'),
                RangeValidation('co2_concentration', 300.0, 2000.0, 'ppm',
                               'CO₂ concentration'),
                RangeValidation('control_efficiency', 0.7, 1.0, 'dimensionless',
                               'Environmental control efficiency'),
                RangeValidation('energy_consumption', 0.0, 50.0, 'kWh/day',
                               'Daily energy consumption'),
            ],
            
            'genetic_parameters_simulator': [
                RangeValidation('adaptation_index', 0.0, 1.0, 'dimensionless',
                               'Genetic adaptation index'),
                RangeValidation('performance_index', 0.0, 1.0, 'dimensionless',
                               'Genetic performance index'),
                RangeValidation('trait_expressions', 0.5, 1.5, 'dimensionless',
                               'Genetic trait expressions (relative to reference)'),
                RangeValidation('heritability', 0.0, 1.0, 'dimensionless',
                               'Trait heritability'),
                RangeValidation('genetic_variance', 0.0, 0.5, 'dimensionless',
                               'Genetic variance'),
            ],
            
            'leaf_development_simulator': [
                RangeValidation('total_leaves', 0.0, 50.0, 'count',
                               'Total number of leaves'),
                RangeValidation('leaf_appearance_rate', 0.0, 2.0, 'leaves/day',
                               'Rate of leaf appearance'),
                RangeValidation('total_leaf_area', 0.0, 2.0, 'm²',
                               'Total leaf area'),
                RangeValidation('leaf_area_index', 0.0, 8.0, 'm²/m²',
                               'Leaf area index'),
                RangeValidation('phyllochron_adjusted', 50.0, 200.0, '°C-day',
                               'Adjusted phyllochron'),
                RangeValidation('cumulative_thermal_time', 0.0, 2000.0, '°C-day',
                               'Cumulative thermal time'),
            ],
            
            'nitrogen_balance_simulator': [
                RangeValidation('total_nitrogen_uptake', 0.0, 10.0, 'g N/day',
                               'Daily nitrogen uptake'),
                RangeValidation('nitrogen_use_efficiency', 0.3, 1.0, 'dimensionless',
                               'Nitrogen use efficiency'),
                RangeValidation('nitrogen_stress_index', 0.0, 1.0, 'dimensionless',
                               'Nitrogen stress index'),
                RangeValidation('luxury_uptake_factor', 0.5, 2.0, 'dimensionless',
                               'Luxury nitrogen uptake factor'),
                RangeValidation('remobilization_efficiency', 0.0, 1.0, 'dimensionless',
                               'Nitrogen remobilization efficiency'),
            ],
            
            'root_zone_temperature_simulator': [
                RangeValidation('root_zone_temperature', 15.0, 35.0, '°C',
                               'Root zone temperature'),
                RangeValidation('temperature_deviation', -10.0, 10.0, '°C',
                               'Deviation from optimal temperature'),
                RangeValidation('growth_factor', 0.0, 1.5, 'dimensionless',
                               'Temperature effect on growth'),
                RangeValidation('nutrient_uptake_factor', 0.0, 1.5, 'dimensionless',
                               'Temperature effect on nutrient uptake'),
                RangeValidation('thermal_stress_factor', 0.0, 1.0, 'dimensionless',
                               'Thermal stress factor'),
            ],
            
            'senescence_simulator': [
                RangeValidation('total_senescence_rate', 0.0, 1.0, 'day⁻¹',
                               'Total senescence rate'),
                RangeValidation('age_senescence_rate', 0.0, 0.5, 'day⁻¹',
                               'Age-related senescence rate'),
                RangeValidation('stress_senescence_rate', 0.0, 1.0, 'day⁻¹',
                               'Stress-induced senescence rate'),
                RangeValidation('remobilization_efficiency', 0.0, 1.0, 'dimensionless',
                               'Nutrient remobilization efficiency'),
                RangeValidation('recovery_rate', 0.0, 0.5, 'day⁻¹',
                               'Recovery rate from senescence'),
            ]
        }
    
    def validate_simulator_outputs(self, simulator_id: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate outputs from a specific simulator"""
        if simulator_id not in self.validation_ranges:
            return {
                'simulator_id': simulator_id,
                'status': 'error',
                'message': f'No validation ranges defined for {simulator_id}',
                'validations': []
            }
        
        validations = []
        warnings = []
        errors = []
        
        for range_def in self.validation_ranges[simulator_id]:
            param_name = range_def.parameter_name
            
            if param_name not in outputs:
                warnings.append(f"Missing parameter: {param_name}")
                continue
            
            value = outputs[param_name]
            
            # Handle different data types
            if isinstance(value, (list, dict)):
                # Skip complex data structures for now
                continue
            
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                warnings.append(f"Cannot convert {param_name} to numeric: {value}")
                continue
            
            # Check range
            if numeric_value < range_def.expected_min:
                error_msg = f"{param_name} ({numeric_value:.3f} {range_def.units}) below minimum ({range_def.expected_min} {range_def.units})"
                errors.append(error_msg)
            elif numeric_value > range_def.expected_max:
                error_msg = f"{param_name} ({numeric_value:.3f} {range_def.units}) above maximum ({range_def.expected_max} {range_def.units})"
                errors.append(error_msg)
            else:
                # Check if within warning threshold
                range_span = range_def.expected_max - range_def.expected_min
                tolerance = range_span * range_def.warning_threshold
                
                if (numeric_value < range_def.expected_min + tolerance or 
                    numeric_value > range_def.expected_max - tolerance):
                    warning_msg = f"{param_name} ({numeric_value:.3f} {range_def.units}) near range limits"
                    warnings.append(warning_msg)
            
            validations.append({
                'parameter': param_name,
                'value': numeric_value,
                'expected_min': range_def.expected_min,
                'expected_max': range_def.expected_max,
                'units': range_def.units,
                'description': range_def.description,
                'status': 'valid' if range_def.expected_min <= numeric_value <= range_def.expected_max else 'invalid'
            })
        
        return {
            'simulator_id': simulator_id,
            'status': 'error' if errors else ('warning' if warnings else 'valid'),
            'validations': validations,
            'warnings': warnings,
            'errors': errors,
            'summary': {
                'total_parameters': len(validations),
                'valid_parameters': len([v for v in validations if v['status'] == 'valid']),
                'invalid_parameters': len([v for v in validations if v['status'] == 'invalid']),
                'warning_count': len(warnings),
                'error_count': len(errors)
            }
        }
    
    def validate_all_simulators(self, simulator_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Validate outputs from all simulators"""
        results = {}
        overall_status = 'valid'
        total_warnings = 0
        total_errors = 0
        
        for simulator_id, outputs in simulator_outputs.items():
            result = self.validate_simulator_outputs(simulator_id, outputs)
            results[simulator_id] = result
            
            if result['status'] == 'error':
                overall_status = 'error'
            elif result['status'] == 'warning' and overall_status == 'valid':
                overall_status = 'warning'
            
            total_warnings += result['summary']['warning_count']
            total_errors += result['summary']['error_count']
        
        return {
            'overall_status': overall_status,
            'total_simulators': len(results),
            'total_warnings': total_warnings,
            'total_errors': total_errors,
            'simulator_results': results,
            'summary': {
                'valid_simulators': len([r for r in results.values() if r['status'] == 'valid']),
                'warning_simulators': len([r for r in results.values() if r['status'] == 'warning']),
                'error_simulators': len([r for r in results.values() if r['status'] == 'error'])
            }
        }
    
    def get_expected_ranges_summary(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get a summary of expected ranges for all simulators"""
        summary = {}
        
        for simulator_id, ranges in self.validation_ranges.items():
            summary[simulator_id] = [
                {
                    'parameter': r.parameter_name,
                    'min': r.expected_min,
                    'max': r.expected_max,
                    'units': r.units,
                    'description': r.description
                }
                for r in ranges
            ]
        
        return summary

def validate_simulation_results(simulator_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function to validate simulation results"""
    validator = SimulatorRangeValidator()
    return validator.validate_all_simulators(simulator_outputs)

if __name__ == "__main__":
    # Example usage
    validator = SimulatorRangeValidator()
    
    # Print expected ranges for all simulators
    print("Expected Ranges for All Simulators:")
    print("=" * 50)
    
    for simulator_id, ranges in validator.get_expected_ranges_summary().items():
        print(f"\n{simulator_id.upper()}:")
        for range_info in ranges:
            print(f"  {range_info['parameter']}: {range_info['min']}-{range_info['max']} {range_info['units']}")
            print(f"    {range_info['description']}")
