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
    carbon_content_fraction: float
    allocation_efficiency: float  # Quantum use efficiency (g/J) - from CSV
    # Carbon allocation fractions - NO HARDCODED VALUES (Rules.md)
    carbon_allocation_roots: float
    carbon_allocation_leaves: float
    carbon_allocation_stems: float
    # Tissue water content fractions - NO HARDCODED VALUES (Rules.md)
    leaf_water_content: float
    stem_water_content: float
    root_water_content: float

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'BiomassAllocationParameters':
        # Per Rules.md: all parameters come directly from CSV via parameter loader
        required_params = [
            'vegetative_leaf_allocation', 'vegetative_stem_allocation', 'vegetative_root_allocation',
            'reproductive_leaf_allocation', 'reproductive_stem_allocation', 'reproductive_root_allocation',
            'light_response_factor', 'nitrogen_response_factor', 'water_response_factor',
            'minimum_organ_fraction', 'carbon_content_fraction', 'allocation_efficiency',
            # Carbon allocation fractions - NO HARDCODED VALUES (Rules.md)
            'carbon_allocation_roots', 'carbon_allocation_leaves', 'carbon_allocation_stems',
            # Tissue water content fractions - NO HARDCODED VALUES (Rules.md)
            'leaf_water_content', 'stem_water_content', 'root_water_content'
        ]
        for param in required_params:
            if param not in config:
                raise KeyError(f"Missing required parameter: {param}")

        return cls(
            vegetative_leaf_allocation=float(config['vegetative_leaf_allocation']),
            vegetative_stem_allocation=float(config['vegetative_stem_allocation']),
            vegetative_root_allocation=float(config['vegetative_root_allocation']),
            reproductive_leaf_allocation=float(config['reproductive_leaf_allocation']),
            reproductive_stem_allocation=float(config['reproductive_stem_allocation']),
            reproductive_root_allocation=float(config['reproductive_root_allocation']),
            light_response_factor=float(config['light_response_factor']),
            nitrogen_response_factor=float(config['nitrogen_response_factor']),
            water_response_factor=float(config['water_response_factor']),
            minimum_organ_fraction=float(config['minimum_organ_fraction']),
            carbon_content_fraction=float(config['carbon_content_fraction']),
            allocation_efficiency=float(config['allocation_efficiency']),
            # Carbon allocation fractions - NO HARDCODED VALUES (Rules.md)
            carbon_allocation_roots=float(config['carbon_allocation_roots']),
            carbon_allocation_leaves=float(config['carbon_allocation_leaves']),
            carbon_allocation_stems=float(config['carbon_allocation_stems']),
            # Tissue water content fractions - NO HARDCODED VALUES (Rules.md)
            leaf_water_content=float(config['leaf_water_content']),
            stem_water_content=float(config['stem_water_content']),
            root_water_content=float(config['root_water_content'])
        )


class BiomassAllocationModel:
    def __init__(self, parameters: BiomassAllocationParameters):
        self.params = parameters
    
    def initialize(self):
        """Initialize the biomass allocation model"""
        pass

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
        # First normalize to sum to 1.0
        total = sum(fractions.values())
        if total > 0:
            for organ in fractions:
                fractions[organ] /= total

        # Then enforce minimum constraints and renormalize if needed
        for organ in fractions:
            fractions[organ] = max(self.params.minimum_organ_fraction, fractions[organ])

        # Check if we need to renormalize after applying minimum constraints
        total_after_min = sum(fractions.values())
        if abs(total_after_min - 1.0) > 0.001:
            # Renormalize while preserving minimums
            excess = total_after_min - 1.0
            adjustable_organs = [organ for organ in fractions
                               if fractions[organ] > self.params.minimum_organ_fraction]

            if adjustable_organs and excess > 0:
                # Proportionally reduce organs above minimum
                adjustable_total = sum(fractions[organ] - self.params.minimum_organ_fraction
                                     for organ in adjustable_organs)
                if adjustable_total > 0:
                    for organ in adjustable_organs:
                        adjustable_fraction = fractions[organ] - self.params.minimum_organ_fraction
                        reduction = (adjustable_fraction / adjustable_total) * excess
                        fractions[organ] -= reduction

        return fractions

    def calculate_tissue_water_retention(self,
                                        biomass_growth: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate tissue water retained in growing biomass.

        Scientific basis: Fresh weight = Dry matter / (1 - water_content)
        Tissue water = Fresh weight - Dry matter

        Args:
            biomass_growth: Dictionary with organ dry matter growth (g)
                          {'leaves': g, 'stems': g, 'roots': g}

        Returns:
            Dictionary with tissue water retention per organ (L)
            {'leaves': L, 'stems': L, 'roots': L, 'total': L}
        """
        water_content_map = {
            'leaves': self.params.leaf_water_content,
            'stems': self.params.stem_water_content,
            'roots': self.params.root_water_content
        }

        tissue_water = {}
        total_water = 0.0

        for organ, dry_matter_growth in biomass_growth.items():
            if organ in water_content_map:
                water_content = water_content_map[organ]
                # Fresh weight = Dry matter / (1 - water_content)
                # Tissue water = Fresh weight - Dry matter
                # Simplified: Tissue water = Dry matter × (water_content / (1 - water_content))
                tissue_water_g = dry_matter_growth * (water_content / (1.0 - water_content))
                tissue_water_L = tissue_water_g / 1000.0  # Convert g to L (1g water = 1mL = 0.001L)
                tissue_water[organ] = tissue_water_L
                total_water += tissue_water_L
            else:
                tissue_water[organ] = 0.0

        tissue_water['total'] = total_water
        return tissue_water


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