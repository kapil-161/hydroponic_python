"""
Biomass Allocation Model

Functional balance theory equations:
- allocation = base_fraction + stress_response
- stress_response = limitation_factor * response_factor
- total_allocation = normalize(Σ(organ_allocations) = 1.0)
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class BiomassAllocationParameters:
    vegetative_leaf_allocation: float
    vegetative_stem_allocation: float
    vegetative_root_allocation: float
    reproductive_leaf_allocation: float
    reproductive_stem_allocation: float
    reproductive_root_allocation: float
    light_response_factor: float
    nitrogen_response_factor: float
    water_response_factor: float
    minimum_organ_fraction: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'BiomassAllocationParameters':
        allocation_params = config['allocation_parameters']
        return cls(
            vegetative_leaf_allocation=allocation_params['vegetative_leaf_allocation'],
            vegetative_stem_allocation=allocation_params['vegetative_stem_allocation'],
            vegetative_root_allocation=allocation_params['vegetative_root_allocation'],
            reproductive_leaf_allocation=allocation_params['reproductive_leaf_allocation'],
            reproductive_stem_allocation=allocation_params['reproductive_stem_allocation'],
            reproductive_root_allocation=allocation_params['reproductive_root_allocation'],
            light_response_factor=allocation_params['light_response_factor'],
            nitrogen_response_factor=allocation_params['nitrogen_response_factor'],
            water_response_factor=allocation_params['water_response_factor'],
            minimum_organ_fraction=allocation_params['minimum_organ_fraction']
        )


class BiomassAllocationModel:
    def __init__(self, parameters: BiomassAllocationParameters):
        self.params = parameters

    def calculate_functional_balance_allocation(self,
                                              stress_factors: Dict[str, Any],
                                              stage_props: Dict[str, Any],
                                              env_conditions: Dict[str, Any]) -> Dict[str, float]:
        base_fractions = self._get_base_allocation_fractions(stage_props)
        resource_limitations = self._calculate_resource_limitations(stress_factors, env_conditions)
        allocation_shifts = self._calculate_allocation_shifts(resource_limitations)
        adjusted_fractions = self._apply_allocation_shifts(base_fractions, allocation_shifts)
        final_fractions = self._normalize_allocations(adjusted_fractions)
        return final_fractions

    def _get_base_allocation_fractions(self, stage_props: Dict[str, Any]) -> Dict[str, float]:
        if stage_props['is_vegetative']:
            return {
                'leaves': self.params.vegetative_leaf_allocation,
                'stems': self.params.vegetative_stem_allocation,
                'roots': self.params.vegetative_root_allocation
            }
        else:
            return {
                'leaves': self.params.reproductive_leaf_allocation,
                'stems': self.params.reproductive_stem_allocation,
                'roots': self.params.reproductive_root_allocation
            }

    def _calculate_resource_limitations(self,
                                      stress_factors: Dict[str, Any],
                                      env_conditions: Dict[str, Any]) -> Dict[str, float]:
        light_limitation = env_conditions['light_stress']
        nitrogen_limitation = stress_factors['nitrogen_stress_level']
        water_limitation = stress_factors['water_stress_level']

        return {
            'light': light_limitation,
            'nitrogen': nitrogen_limitation,
            'water': water_limitation
        }

    def _calculate_allocation_shifts(self, limitations: Dict[str, float]) -> Dict[str, float]:
        light_response = limitations['light'] * self.params.light_response_factor
        nitrogen_response = limitations['nitrogen'] * self.params.nitrogen_response_factor
        water_response = limitations['water'] * self.params.water_response_factor

        return {
            'leaf_shift': max(0.0, light_response),
            'root_shift': max(0.0, nitrogen_response + water_response)
        }

    def _apply_allocation_shifts(self,
                               base_fractions: Dict[str, float],
                               shifts: Dict[str, float]) -> Dict[str, float]:
        adjusted_fractions = base_fractions.copy()

        root_shift = shifts['root_shift']
        if root_shift > 0:
            adjusted_fractions['roots'] += root_shift
            shoot_reduction = root_shift
            shoot_total = base_fractions['leaves'] + base_fractions['stems']

            if shoot_total > 0:
                leaf_reduction = (base_fractions['leaves'] / shoot_total) * shoot_reduction
                stem_reduction = (base_fractions['stems'] / shoot_total) * shoot_reduction
                adjusted_fractions['leaves'] -= leaf_reduction
                adjusted_fractions['stems'] -= stem_reduction

        leaf_shift = shifts['leaf_shift']
        if leaf_shift > 0:
            adjusted_fractions['leaves'] += leaf_shift
            non_leaf_reduction = leaf_shift
            non_leaf_total = adjusted_fractions['roots'] + adjusted_fractions['stems']

            if non_leaf_total > 0:
                root_reduction = (adjusted_fractions['roots'] / non_leaf_total) * non_leaf_reduction
                stem_reduction = (adjusted_fractions['stems'] / non_leaf_total) * non_leaf_reduction
                adjusted_fractions['roots'] -= root_reduction
                adjusted_fractions['stems'] -= stem_reduction

        return adjusted_fractions

    def _normalize_allocations(self, fractions: Dict[str, float]) -> Dict[str, float]:
        for organ in fractions:
            fractions[organ] = max(self.params.minimum_organ_fraction, fractions[organ])

        total = sum(fractions.values())
        if total > 0:
            for organ in fractions:
                fractions[organ] /= total

        return fractions


def create_lettuce_biomass_allocation_model(system_config: Any) -> BiomassAllocationModel:
    config = {'allocation_parameters': getattr(system_config, 'allocation_parameters', {})}

    if not config['allocation_parameters']:
        raise ValueError("allocation_parameters section must be provided in CSV configuration")

    parameters = BiomassAllocationParameters.from_config(config)
    return BiomassAllocationModel(parameters)


"""
INPUT PARAMETERS (from CSV):
- vegetative_leaf_allocation: base leaf allocation fraction during vegetative stage
- vegetative_stem_allocation: base stem allocation fraction during vegetative stage
- vegetative_root_allocation: base root allocation fraction during vegetative stage
- reproductive_leaf_allocation: base leaf allocation fraction during reproductive stage
- reproductive_stem_allocation: base stem allocation fraction during reproductive stage
- reproductive_root_allocation: base root allocation fraction during reproductive stage
- light_response_factor: response strength to light limitation
- nitrogen_response_factor: response strength to nitrogen limitation
- water_response_factor: response strength to water limitation
- minimum_organ_fraction: minimum allocation fraction for any organ

INPUT VARIABLES:
- stress_factors['nitrogen_stress_level']: nitrogen stress level (0-1)
- stress_factors['water_stress_level']: water stress level (0-1)
- env_conditions['light_stress']: light stress level (0-1)
- stage_props['is_vegetative']: development stage flag

OUTPUT VARIABLES:
- final_fractions['leaves']: leaf biomass allocation fraction
- final_fractions['stems']: stem biomass allocation fraction
- final_fractions['roots']: root biomass allocation fraction
"""