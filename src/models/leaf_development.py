"""
Leaf Development Model for Hydroponic Lettuce
Based on DSSAT CROPGRO approach with adaptations for lettuce

Key concepts implemented:
1. Phyllochron - thermal time interval between successive leaf appearances
2. V-stage progression - number of fully expanded leaves 
3. Temperature-dependent leaf appearance rate
4. Water and nutrient stress effects on leaf development
5. Individual leaf area expansion
6. Total leaf area index (LAI) calculation
"""

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class LeafStage(Enum):
    """Leaf development stages."""
    PRIMORDIAL = "primordial"  # Leaf primordia formation
    EMERGING = "emerging"      # Leaf emergence visible
    EXPANDING = "expanding"    # Active leaf expansion
    MATURE = "mature"         # Fully expanded
    SENESCING = "senescing"   # Beginning senescence


@dataclass
class LeafParameters:
    """Parameters for leaf development model."""
    
    # Phyllochron and thermal time parameters
    base_phyllochron: float = 45.0      # Base phyllochron (°C-day) for lettuce
    min_temp: float = 4.0               # Base temperature for development (°C)
    opt_temp_min: float = 18.0          # Lower optimum temperature (°C)  
    opt_temp_max: float = 24.0          # Upper optimum temperature (°C)
    max_temp: float = 35.0              # Maximum temperature for development (°C)
    
    # Leaf appearance and expansion
    max_leaf_number: float = 25.0       # Maximum leaves for lettuce
    initial_leaf_number: float = 2.0    # Cotyledons + first true leaves
    leaf_appearance_rate: float = 1.0   # Leaves per phyllochron unit
    
    # Individual leaf parameters
    max_individual_leaf_area: float = 0.006  # m² per mature leaf (60 cm²)
    leaf_area_expansion_rate: float = 0.15   # Natural cellular expansion rate - no artificial limits
    specific_leaf_area: float = 250.0        # cm²/g dry weight
    
    # Stress response parameters
    water_stress_threshold: float = 0.5      # Below this, leaf development slows
    nitrogen_stress_threshold: float = 0.6   # Below this, leaf expansion reduces
    temperature_stress_sensitivity: float = 0.8  # Response to temp stress
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'LeafParameters':
        """Create LeafParameters from configuration dictionary."""
        return cls(
            base_phyllochron=config_dict.get('base_phyllochron', 45.0),
            min_temp=config_dict.get('min_temp', 4.0),
            opt_temp_min=config_dict.get('opt_temp_min', 18.0),
            opt_temp_max=config_dict.get('opt_temp_max', 24.0),
            max_temp=config_dict.get('max_temp', 35.0),
            max_leaf_number=config_dict.get('max_leaf_number', 25.0),
            initial_leaf_number=config_dict.get('initial_leaf_number', 2.0),
            leaf_appearance_rate=config_dict.get('leaf_appearance_rate', 1.0),
            max_individual_leaf_area=config_dict.get('max_individual_leaf_area', 0.006),
            leaf_area_expansion_rate=config_dict.get('leaf_area_expansion_rate', 0.12),
            specific_leaf_area=config_dict.get('specific_leaf_area', 250.0),
            water_stress_threshold=config_dict.get('water_stress_threshold', 0.5),
            nitrogen_stress_threshold=config_dict.get('nitrogen_stress_threshold', 0.6),
            temperature_stress_sensitivity=config_dict.get('temperature_stress_sensitivity', 0.8)
        )


@dataclass 
class LeafCohort:
    """Individual leaf cohort tracking."""
    cohort_id: int
    appearance_day: float          # Day when leaf appeared (V-stage)
    current_area: float           # Current leaf area (m²)
    max_potential_area: float     # Maximum potential area (m²)
    stage: LeafStage              # Current development stage
    thermal_time_since_appearance: float = 0.0
    senescence_rate: float = 0.0  # Daily senescence rate


class LeafDevelopmentModel:
    """
    Leaf development model following DSSAT CROPGRO principles.
    Calculates leaf number, individual leaf areas, and total LAI.
    """
    
    def __init__(self, parameters: Optional[LeafParameters] = None):
        self.params = parameters or LeafParameters()
        self.leaf_cohorts: Dict[int, LeafCohort] = {}
        self.current_v_stage: float = self.params.initial_leaf_number
        self.cumulative_thermal_time: float = 0.0
        self.next_cohort_id: int = 1
        
        # Initialize with initial leaves
        for i in range(int(self.params.initial_leaf_number)):
            self._create_initial_leaf_cohort(i + 1)
    
    def _create_initial_leaf_cohort(self, cohort_id: int):
        """Create initial leaf cohorts (cotyledons + first leaves)."""
        initial_area = self.params.max_individual_leaf_area * 0.3  # 30% of max
        cohort = LeafCohort(
            cohort_id=cohort_id,
            appearance_day=0.0,
            current_area=initial_area,
            max_potential_area=self.params.max_individual_leaf_area,
            stage=LeafStage.EXPANDING,
            thermal_time_since_appearance=20.0  # Some initial thermal time
        )
        self.leaf_cohorts[cohort_id] = cohort
    
    def calculate_thermal_time(self, temperature: float) -> float:
        """
        Calculate daily thermal time using cardinal temperature approach.
        Based on DSSAT CROPGRO temperature response function.
        """
        T = temperature
        Tmin = self.params.min_temp
        Topt1 = self.params.opt_temp_min  
        Topt2 = self.params.opt_temp_max
        Tmax = self.params.max_temp
        
        if T <= Tmin or T >= Tmax:
            return 0.0
        elif Tmin < T <= Topt1:
            # Linear increase from Tmin to Topt1
            return (T - Tmin) / (Topt1 - Tmin) * (Topt1 - Tmin)
        elif Topt1 < T <= Topt2:
            # Optimal range - maximum rate
            return T - Tmin
        else:  # Topt2 < T < Tmax
            # Linear decrease from Topt2 to Tmax
            factor = (Tmax - T) / (Tmax - Topt2)
            return factor * (T - Tmin)
    
    def calculate_stress_factors(self, water_stress: float = 1.0, 
                               nitrogen_stress: float = 1.0,
                               temperature_stress: float = 1.0) -> Dict[str, float]:
        """Calculate stress effects on leaf development."""
        
        # Water stress effect on leaf appearance
        water_factor = 1.0
        if water_stress < self.params.water_stress_threshold:
            water_factor = max(0.2, water_stress / self.params.water_stress_threshold)
        
        # Nitrogen stress effect on leaf expansion
        nitrogen_factor = 1.0 
        if nitrogen_stress < self.params.nitrogen_stress_threshold:
            nitrogen_factor = max(0.3, nitrogen_stress / self.params.nitrogen_stress_threshold)
        
        # Temperature stress effect
        temp_factor = max(0.1, 1.0 - (1.0 - temperature_stress) * self.params.temperature_stress_sensitivity)
        
        return {
            'water_factor': water_factor,
            'nitrogen_factor': nitrogen_factor, 
            'temperature_factor': temp_factor,
            'combined_appearance_factor': water_factor * temp_factor,
            'combined_expansion_factor': water_factor * nitrogen_factor * temp_factor
        }
    
    def update_v_stage(self, daily_thermal_time: float, stress_factors: Dict[str, float]) -> bool:
        """
        Update V-stage (leaf appearance) based on thermal time and stress.
        Returns True if new leaf appeared.
        """
        # Accumulate thermal time with stress effects
        effective_thermal_time = daily_thermal_time * stress_factors['combined_appearance_factor']
        self.cumulative_thermal_time += effective_thermal_time
        
        # Check if enough thermal time accumulated for new leaf
        thermal_time_for_next_leaf = self.params.base_phyllochron
        
        # Adjust phyllochron based on current development stage
        if self.current_v_stage > 15:  # Later leaves appear more slowly
            thermal_time_for_next_leaf *= 1.3
        elif self.current_v_stage > 20:  # Very late leaves
            thermal_time_for_next_leaf *= 1.6
        
        new_leaf_appeared = False
        
        # Check if we can add a new leaf
        if (self.cumulative_thermal_time >= thermal_time_for_next_leaf and 
            self.current_v_stage < self.params.max_leaf_number):
            
            # Create new leaf cohort
            self._create_new_leaf_cohort()
            
            # Update V-stage
            self.current_v_stage += 1.0
            self.cumulative_thermal_time = 0.0  # Reset for next leaf
            new_leaf_appeared = True
        
        return new_leaf_appeared
    
    def _create_new_leaf_cohort(self):
        """Create a new leaf cohort."""
        # Calculate potential leaf size based on position
        position_factor = self._calculate_leaf_position_factor(self.current_v_stage)
        max_area = self.params.max_individual_leaf_area * position_factor
        
        cohort = LeafCohort(
            cohort_id=self.next_cohort_id,
            appearance_day=self.current_v_stage,
            current_area=0.001,  # Very small initial area
            max_potential_area=max_area,
            stage=LeafStage.EMERGING
        )
        
        self.leaf_cohorts[self.next_cohort_id] = cohort
        self.next_cohort_id += 1
    
    def _calculate_leaf_position_factor(self, v_stage: float) -> float:
        """Calculate relative leaf size based on position on plant."""
        # Lettuce leaves generally increase in size toward middle, then decrease
        if v_stage <= 5:
            return 0.4 + (v_stage - 1) * 0.15  # Small early leaves
        elif v_stage <= 15:
            return 1.0  # Full size middle leaves  
        else:
            return max(0.6, 1.0 - (v_stage - 15) * 0.04)  # Smaller late leaves
    
    def update_leaf_areas(self, daily_thermal_time: float, 
                         stress_factors: Dict[str, float]) -> Dict[str, float]:
        """Update individual leaf areas for all cohorts."""
        
        expansion_factor = stress_factors['combined_expansion_factor']
        total_area = 0.0
        visible_leaves = 0  # Leaves that have appeared (V-stage counting)
        active_leaves = 0   # Leaves contributing significant area
        senesced_area = 0.0
        
        cohorts_to_remove = []  # Track completely dead leaves
        
        for cohort_id, cohort in self.leaf_cohorts.items():
            # Update thermal time for this cohort
            cohort.thermal_time_since_appearance += daily_thermal_time
            
            # Count all leaves that have appeared (for V-stage consistency)
            if cohort.stage != LeafStage.PRIMORDIAL:
                visible_leaves += 1
            
            # Calculate area expansion for this cohort
            if cohort.stage == LeafStage.EMERGING:
                # Transition to expanding after some thermal time
                if cohort.thermal_time_since_appearance > 5.0:
                    cohort.stage = LeafStage.EXPANDING
            
            elif cohort.stage == LeafStage.EXPANDING:
                # Calculate daily area increase based on cell biology
                base_expansion_rate = self.params.leaf_area_expansion_rate
                
                # Resource-limited expansion factors
                temperature_factor = stress_factors.get('temperature_factor', 1.0)
                nitrogen_factor = stress_factors.get('nitrogen_factor', 1.0)
                water_factor = stress_factors.get('water_factor', 1.0)
                
                # Cell division requires optimal temperature (Q10 response)
                cell_division_factor = temperature_factor
                
                # Cell expansion requires water for turgor pressure
                cell_expansion_factor = water_factor * nitrogen_factor
                
                # Natural cellular growth - both division and expansion operate independently
                cell_division_rate = base_expansion_rate * cell_division_factor
                cell_expansion_rate = base_expansion_rate * cell_expansion_factor
                
                # Pure cellular biology - growth continues as long as resources available
                relative_expansion_rate = cell_division_rate + cell_expansion_rate
                
                # No artificial size limits - cells keep dividing and expanding naturally
                size_factor = 1.0  # Natural growth continues
                
                # Carbon drives continuous growth
                carbon_limited_rate = relative_expansion_rate
                
                daily_increase = (cohort.current_area * carbon_limited_rate * size_factor)
                
                # Real-world cell wall mechanical limits
                # Cell walls have tensile strength limits - can't expand infinitely
                max_realistic_leaf_area = self.params.max_individual_leaf_area * 3.0  # 3x genetic maximum
                
                if cohort.current_area > max_realistic_leaf_area:
                    # Cell wall stress reduces expansion rate
                    wall_stress_factor = max_realistic_leaf_area / cohort.current_area
                    daily_increase *= wall_stress_factor ** 2  # Quadratic penalty
                
                # Physical constraint - leaves can't exceed structural limits
                proposed_area = cohort.current_area + max(0.0, daily_increase)
                max_physical_area = self.params.max_individual_leaf_area * 4.0  # Absolute physical limit
                
                cohort.current_area = min(proposed_area, max_physical_area)
                
                # Natural maturation based on thermal age, not artificial size limits
                if cohort.thermal_time_since_appearance > 300:  # Mature after natural cellular development
                    cohort.stage = LeafStage.MATURE
            
            elif cohort.stage == LeafStage.MATURE:
                # Check for senescence initiation (old leaves or stress)
                # Real lettuce leaf lifespan: 4-5 weeks (300-400 thermal time units)
                age_factor = cohort.thermal_time_since_appearance / 350.0  # Realistic lettuce leaf lifespan
                stress_senescence = (1.0 - expansion_factor) * 0.15
                
                # Natural senescence starts when leaves age
                if age_factor > 0.9 or stress_senescence > 0.08:  # Start at 90% of lifespan
                    cohort.stage = LeafStage.SENESCING
                    # Realistic senescence rate: 2-6% per day (10-25 days to senesce)
                    cohort.senescence_rate = max(0.02, age_factor * 0.04 + stress_senescence)
            
            elif cohort.stage == LeafStage.SENESCING:
                # Reduce leaf area due to senescence
                area_loss = cohort.current_area * cohort.senescence_rate
                cohort.current_area = max(0.0, cohort.current_area - area_loss)
                senesced_area += area_loss
                
                # Mark completely senesced leaves for removal
                if cohort.current_area < 0.0001:  # Essentially gone
                    cohorts_to_remove.append(cohort_id)
                    continue
            
            total_area += cohort.current_area
            
            # Count leaves with meaningful area contribution
            if cohort.current_area > 0.0005:  # 5 cm² minimum for active counting
                active_leaves += 1
        
        # Remove completely dead leaves from the cohort dictionary
        for cohort_id in cohorts_to_remove:
            if cohort_id in self.leaf_cohorts:
                del self.leaf_cohorts[cohort_id]
        
        # Calculate LAI (assuming 1 m² growing area per plant for base calculation)
        lai = total_area  # Will be scaled by plant density in main simulation
        
        return {
            'total_leaf_area_m2': total_area,
            'leaf_area_index': lai,
            'visible_leaf_count': visible_leaves,      # For V-stage consistency
            'active_leaf_count': active_leaves,        # For area calculations
            'senesced_area_daily': senesced_area,
            'average_leaf_area': total_area / max(1, active_leaves)
        }
    
    

def demonstrate_leaf_development_model():
    """Demonstrate leaf development dynamics over 30 days."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        ld_config = config_loader.get_leaf_development_parameters()
        model = LeafDevelopmentModel(LeafParameters.from_config(ld_config))
    except Exception:
        model = LeafDevelopmentModel()

    print("=" * 80)
    print("LEAF DEVELOPMENT MODEL DEMONSTRATION")
    print("=" * 80)

    print(f"{'Day':<4} {'Temp':<6} {'Leaves':<7} {'LAI':<6} {'Area(m2)':<9}")
    print("-" * 80)
    for day in range(1, 31):
        # Mildly varying temp and no stress
        temp = 22.0 + 2.0 * np.sin(day * np.pi / 15)
        daily_tt = model.calculate_thermal_time(temp)
        stress = model.calculate_stress_factors(1.0, 1.0, 1.0)
        _ = model.update_v_stage(daily_tt, stress)
        stats = model.update_leaf_areas(daily_tt, stress)
        if day % 3 == 1:
            print(f"{day:<4} {temp:<6.1f} {int(model.current_v_stage):<7} {stats['leaf_area_index']:<6.2f} {stats['total_leaf_area_m2']:<9.3f}")


if __name__ == "__main__":
    demonstrate_leaf_development_model()

