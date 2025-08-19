"""
Carbon Allocation Model for Hydroponic Systems
Implements a simplified 3-compartment model for carbon and nitrogen allocation.
"""

from typing import Dict
from .mechanistic_nutrient_uptake import PlantBiomass

class CarbonAllocationModel:
    """Manages the allocation of carbon and nitrogen to plant biomass."""

    def __init__(self, psi: float = 0.6):
        self.psi = psi  # Partitioning coefficient for shoot vs. root

    def update_biomass(self, current_biomass: PlantBiomass, carbon_assimilated: float, nitrogen_assimilated: float) -> PlantBiomass:
        """Update plant biomass based on assimilated carbon and nitrogen."""

        # Add assimilated resources to storage
        current_biomass.carbon_storage += carbon_assimilated
        current_biomass.nitrogen_storage += nitrogen_assimilated

        # Growth is limited by the minimum of available C or N
        # This is a simplification of the growth process
        potential_growth_from_c = current_biomass.carbon_storage * 0.5 # Conversion efficiency
        potential_growth_from_n = current_biomass.nitrogen_storage * 10.0 # C:N ratio assumption

        # Actual growth is the minimum of the two potentials
        structural_growth = min(potential_growth_from_c, potential_growth_from_n)

        # Update storage based on what was used for growth
        carbon_used = structural_growth / 0.5
        nitrogen_used = structural_growth / 10.0
        current_biomass.carbon_storage -= carbon_used
        current_biomass.nitrogen_storage -= nitrogen_used

        # Update structural mass
        current_biomass.structural_mass += structural_growth

        return current_biomass

    def partition_biomass(self, biomass: PlantBiomass) -> Dict[str, float]:
        """Partition structural biomass into shoot and root mass."""
        shoot_mass = biomass.structural_mass * self.psi
        root_mass = biomass.structural_mass * (1 - self.psi)
        return {"shoot_mass": shoot_mass, "root_mass": root_mass}
