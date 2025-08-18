"""
Nutrient Concentration Submodel (NCS) for Hydroponic Systems
Implements ion concentration dynamics in nutrient solutions
Based on: [I]t+1 = [I]t + TrV⁻¹([I]R − [I]U) for nutritive ions
         [I]t+1 = ([I]t − [I]Rp⁻¹)exp(−pTrV⁻¹) + [I]Rp⁻¹ for non-nutritive ions
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class NutrientParams:
    """Parameters for a single nutrient."""
    nutrient_id: str
    nutrient_name: str
    chemical_form: str
    initial_conc: float  # mg/L
    recharge_conc: float  # mg/L
    uptake_conc: float  # mg/L
    sensitivity_coeff: float
    is_nutritive: bool
    min_conc: float  # mg/L
    max_conc: float  # mg/L


class NutrientConcentrationModel:
    """Nutrient Concentration Submodel for hydroponic systems."""
    
    def __init__(self):
        self.nutrients: Dict[str, NutrientParams] = {}
        self.warning_flags: Dict[str, int] = {}
        
    def add_nutrient(self, params: NutrientParams):
        """Add a nutrient to the model."""
        self.nutrients[params.nutrient_id] = params
        self.warning_flags[params.nutrient_id] = 0
        
    def calculate_concentration_change(self, nutrient_id: str, current_conc: float,
                                     transpiration_rate: float, tank_volume: float) -> float:
        """
        Calculate new ion concentration based on NCS equations.
        
        Args:
            nutrient_id: Nutrient identifier
            current_conc: Current ion concentration (mg/L)
            transpiration_rate: Transpiration rate (L/day)
            tank_volume: Solution tank volume (L)
            
        Returns:
            Updated ion concentration (mg/L)
        """
        if nutrient_id not in self.nutrients:
            raise ValueError(f"Nutrient {nutrient_id} not found in model")
            
        params = self.nutrients[nutrient_id]
        
        # Calculate transpiration to volume ratio
        if tank_volume <= 0.0:
            return current_conc
            
        tr_v_ratio = transpiration_rate / tank_volume
        
        if params.is_nutritive:
            # Equation (3): For nutritive ions
            # [I]t+1 = [I]t + Tr × V⁻¹ × ([I]R - [I]U)
            new_conc = current_conc + tr_v_ratio * (params.recharge_conc - params.uptake_conc)
        else:
            # Equation (4): For non-nutritive ions
            # [I]t+1 = ([I]t - [I]R × p⁻¹) × exp(-p × Tr × V⁻¹) + [I]R × p⁻¹
            
            # Calculate recharge term
            if params.sensitivity_coeff > 0.0:
                recharge_term = params.recharge_conc / params.sensitivity_coeff
            else:
                recharge_term = 0.0
                
            # Calculate exponential term
            exponential_term = np.exp(-params.sensitivity_coeff * tr_v_ratio)
            
            # Apply the equation
            new_conc = ((current_conc - recharge_term) * exponential_term + recharge_term)
        
        # Ensure non-negative concentrations
        new_conc = max(0.0, new_conc)
        
        # Check concentration limits
        self._check_nutrient_limits(nutrient_id, new_conc)
        
        return new_conc
    
    def calculate_nutrient_uptake_rate(self, old_conc: float, new_conc: float, 
                                     tank_volume: float) -> float:
        """
        Calculate daily nutrient uptake rate based on concentration change.
        
        Args:
            old_conc: Previous concentration (mg/L)
            new_conc: Current concentration (mg/L)
            tank_volume: Solution tank volume (L)
            
        Returns:
            Nutrient uptake rate (mg/day)
        """
        conc_change = old_conc - new_conc
        
        # Calculate uptake rate (negative change indicates uptake)
        if conc_change > 0.0:
            return conc_change * tank_volume
        else:
            return 0.0  # No uptake if concentration increased
    
    def calculate_nutrient_use_efficiency(self, total_uptake: float, 
                                        total_supply: float) -> float:
        """
        Calculate Nutrient Use Efficiency (NUE).
        NUE = (Total nutrient uptake / Total nutrient supply) × 100
        
        Args:
            total_uptake: Total nutrient uptake (mg)
            total_supply: Total nutrient supply (mg)
            
        Returns:
            Nutrient use efficiency (%)
        """
        if total_supply > 0.0:
            nue = (total_uptake / total_supply) * 100.0
            return min(nue, 100.0)  # Ensure NUE doesn't exceed 100%
        else:
            return 0.0
    
    def update_solution_volume(self, initial_volume: float, transpiration_rate: float,
                              recharge_volume: float = 0.0) -> float:
        """
        Update solution tank volume accounting for transpiration and recharge.
        
        Args:
            initial_volume: Initial tank volume (L)
            transpiration_rate: Daily transpiration rate (L/day)
            recharge_volume: Daily recharge volume (L/day)
            
        Returns:
            Updated tank volume (L)
        """
        new_volume = initial_volume - transpiration_rate + recharge_volume
        
        # Ensure minimum volume (10% of initial volume)
        return max(new_volume, initial_volume * 0.1)
    
    def calculate_electrical_conductivity(self, concentrations: Dict[str, float],
                                        ec_factors: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate total electrical conductivity from ion concentrations.
        EC (dS/m) = Σ(Ion_concentration × EC_factor)
        
        Args:
            concentrations: Dictionary of nutrient concentrations (mg/L)
            ec_factors: Dictionary of EC conversion factors
            
        Returns:
            Total electrical conductivity (dS/m)
        """
        if ec_factors is None:
            # Default EC factors (approximate values)
            ec_factors = {
                'N-NO3': 0.001, 'P-PO4': 0.0008, 'K': 0.0012,
                'Ca': 0.0015, 'Mg': 0.0014, 'S-SO4': 0.0010,
                'Fe': 0.002, 'Mn': 0.002, 'Zn': 0.002, 'Cu': 0.002,
                'B': 0.0018, 'Mo': 0.002, 'Na': 0.0016, 'Cl': 0.0018
            }
        
        total_ec = 0.0
        for nutrient_id, concentration in concentrations.items():
            if nutrient_id in ec_factors:
                total_ec += concentration * ec_factors[nutrient_id]
        
        return total_ec / 1000.0  # Convert to dS/m
    
    def _check_nutrient_limits(self, nutrient_id: str, concentration: float):
        """Check if nutrient concentrations are within acceptable limits."""
        params = self.nutrients[nutrient_id]
        
        if concentration < params.min_conc:
            self.warning_flags[nutrient_id] = 1  # Below minimum
            print(f"WARNING: {nutrient_id} concentration ({concentration:.2f}) "
                  f"below minimum ({params.min_conc:.2f})")
        elif concentration > params.max_conc:
            self.warning_flags[nutrient_id] = 2  # Above maximum
            print(f"WARNING: {nutrient_id} concentration ({concentration:.2f}) "
                  f"above maximum ({params.max_conc:.2f})")
        else:
            self.warning_flags[nutrient_id] = 0  # Within limits
    
    def get_all_concentrations(self, current_concentrations: Dict[str, float],
                              transpiration_rate: float, tank_volume: float) -> Dict[str, float]:
        """
        Calculate new concentrations for all nutrients.
        
        Args:
            current_concentrations: Current concentrations for all nutrients
            transpiration_rate: Transpiration rate (L/day)
            tank_volume: Solution tank volume (L)
            
        Returns:
            Dictionary of updated concentrations
        """
        new_concentrations = {}
        
        for nutrient_id in self.nutrients.keys():
            if nutrient_id in current_concentrations:
                new_concentrations[nutrient_id] = self.calculate_concentration_change(
                    nutrient_id, current_concentrations[nutrient_id],
                    transpiration_rate, tank_volume
                )
            else:
                new_concentrations[nutrient_id] = self.nutrients[nutrient_id].initial_conc
                
        return new_concentrations