"""
Biomass Allocation Model

This module implements functional balance theory for biomass allocation:
- Plants allocate biomass to overcome the most limiting resource
- Light limitation → more leaves (increase light capture)
- Nitrogen limitation → more roots (increase N uptake)
- Water limitation → more roots (increase water uptake)
- Developmental stage → sink strength effects

Scientific basis:
- Shipley, B. & Meziane, D. (2002). The balanced-growth hypothesis and the allometry of leaf and root biomass allocation.
- Thornley, J.H.M. (1972). A balanced quantitative model for root:shoot ratios in vegetative plants.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class BiomassAllocationParameters:
    """Parameters for biomass allocation calculations."""

    # Base allocation fractions by growth stage
    vegetative_leaf_allocation: float
    vegetative_stem_allocation: float
    vegetative_root_allocation: float

    reproductive_leaf_allocation: float
    reproductive_stem_allocation: float
    reproductive_root_allocation: float

    # Functional balance response factors
    light_response_factor: float       # Response strength to light limitation
    nitrogen_response_factor: float    # Response strength to N limitation
    water_response_factor: float       # Response strength to water limitation

    # Allocation constraints
    minimum_organ_fraction: float      # Minimum allocation to any organ (e.g., 0.05 = 5%)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'BiomassAllocationParameters':
        """Create parameters from configuration dictionary."""
        allocation_params = config.get('allocation_parameters', {})

        return cls(
            # Vegetative stage allocations
            vegetative_leaf_allocation=allocation_params['vegetative_leaf_allocation'],
            vegetative_stem_allocation=allocation_params['vegetative_stem_allocation'],
            vegetative_root_allocation=allocation_params['vegetative_root_allocation'],

            # Reproductive stage allocations
            reproductive_leaf_allocation=allocation_params['reproductive_leaf_allocation'],
            reproductive_stem_allocation=allocation_params['reproductive_stem_allocation'],
            reproductive_root_allocation=allocation_params['reproductive_root_allocation'],

            # Response factors
            light_response_factor=allocation_params['light_response_factor'],
            nitrogen_response_factor=allocation_params['nitrogen_response_factor'],
            water_response_factor=allocation_params['water_response_factor'],

            # Constraints
            minimum_organ_fraction=allocation_params['minimum_organ_fraction']
        )


class BiomassAllocationModel:
    """
    Functional balance model for biomass allocation.

    Implements the principle that plants allocate biomass to overcome
    the most limiting resource according to functional balance theory.
    """

    def __init__(self, parameters: BiomassAllocationParameters):
        """Initialize biomass allocation model with parameters."""
        self.params = parameters

    def calculate_functional_balance_allocation(self,
                                              stress_factors: Dict[str, Any],
                                              stage_props: Dict[str, Any],
                                              env_conditions: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate biomass allocation using functional balance theory.

        Args:
            stress_factors: Current stress levels (higher = more stressed)
            stage_props: Development stage properties
            env_conditions: Environmental conditions

        Returns:
            Dictionary with allocation fractions for each organ
        """

        # Get base allocation fractions based on development stage
        base_fractions = self._get_base_allocation_fractions(stage_props)

        # Calculate resource limitation factors
        resource_limitations = self._calculate_resource_limitations(stress_factors, env_conditions)

        # Calculate functional balance responses
        allocation_shifts = self._calculate_allocation_shifts(resource_limitations)

        # Apply shifts while maintaining mass balance
        adjusted_fractions = self._apply_allocation_shifts(base_fractions, allocation_shifts)

        # Ensure constraints and normalize
        final_fractions = self._normalize_allocations(adjusted_fractions)

        return final_fractions

    def _get_base_allocation_fractions(self, stage_props: Dict[str, Any]) -> Dict[str, float]:
        """Get base allocation fractions based on development stage."""
        if stage_props.get('is_vegetative', True):
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
        """Calculate limitation factors for different resources."""

        # Light limitation (0 = no limitation, 1 = severe limitation)
        light_stress = env_conditions.get('light_stress', 0.0)
        light_limitation = light_stress

        # Nitrogen limitation (higher stress = more limitation)
        nitrogen_limitation = stress_factors.get('nitrogen_stress_level', 0.0)

        # Water limitation (higher stress = more limitation)
        water_limitation = stress_factors.get('water_stress_level', 0.0)

        return {
            'light': light_limitation,
            'nitrogen': nitrogen_limitation,
            'water': water_limitation
        }

    def _calculate_allocation_shifts(self, limitations: Dict[str, float]) -> Dict[str, float]:
        """Calculate how much to shift allocation based on limitations."""

        # Light limitation drives leaf allocation
        light_response = limitations['light'] * self.params.light_response_factor

        # Nitrogen limitation drives root allocation
        nitrogen_response = limitations['nitrogen'] * self.params.nitrogen_response_factor

        # Water limitation drives root allocation
        water_response = limitations['water'] * self.params.water_response_factor

        return {
            'leaf_shift': max(0.0, light_response),
            'root_shift': max(0.0, nitrogen_response + water_response)
        }

    def _apply_allocation_shifts(self,
                               base_fractions: Dict[str, float],
                               shifts: Dict[str, float]) -> Dict[str, float]:
        """Apply allocation shifts while maintaining mass balance."""

        adjusted_fractions = base_fractions.copy()

        # Increase roots in response to nutrient/water limitation
        root_shift = shifts['root_shift']
        if root_shift > 0:
            adjusted_fractions['roots'] += root_shift
            # Reduce leaves and stems proportionally
            shoot_reduction = root_shift
            shoot_total = base_fractions['leaves'] + base_fractions['stems']

            if shoot_total > 0:
                leaf_reduction = (base_fractions['leaves'] / shoot_total) * shoot_reduction
                stem_reduction = (base_fractions['stems'] / shoot_total) * shoot_reduction

                adjusted_fractions['leaves'] -= leaf_reduction
                adjusted_fractions['stems'] -= stem_reduction

        # Increase leaves in response to light limitation
        leaf_shift = shifts['leaf_shift']
        if leaf_shift > 0:
            adjusted_fractions['leaves'] += leaf_shift
            # Reduce roots and stems proportionally
            non_leaf_reduction = leaf_shift
            non_leaf_total = adjusted_fractions['roots'] + adjusted_fractions['stems']

            if non_leaf_total > 0:
                root_reduction = (adjusted_fractions['roots'] / non_leaf_total) * non_leaf_reduction
                stem_reduction = (adjusted_fractions['stems'] / non_leaf_total) * non_leaf_reduction

                adjusted_fractions['roots'] -= root_reduction
                adjusted_fractions['stems'] -= stem_reduction

        return adjusted_fractions

    def _normalize_allocations(self, fractions: Dict[str, float]) -> Dict[str, float]:
        """Ensure all fractions are positive and sum to 1.0."""

        # Ensure minimum fractions
        for organ in fractions:
            fractions[organ] = max(self.params.minimum_organ_fraction, fractions[organ])

        # Normalize to sum to 1.0
        total = sum(fractions.values())
        if total > 0:
            for organ in fractions:
                fractions[organ] /= total

        return fractions


def create_lettuce_biomass_allocation_model(system_config: Any) -> BiomassAllocationModel:
    """
    Create biomass allocation model for lettuce using system configuration.

    Args:
        system_config: System configuration containing parameters

    Returns:
        Configured BiomassAllocationModel instance
    """

    # Extract configuration
    config = {
        'allocation_parameters': getattr(system_config, 'allocation_parameters', {})
    }

    # Validate required parameters exist
    if not config['allocation_parameters']:
        raise ValueError("❌ allocation_parameters section must be provided in CSV configuration")

    parameters = BiomassAllocationParameters.from_config(config)

    return BiomassAllocationModel(parameters)