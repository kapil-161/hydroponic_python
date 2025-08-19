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
    leaf_area_expansion_rate: float = 0.12   # Fraction of max area per day at optimum
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
        active_leaves = 0
        senesced_area = 0.0
        
        for cohort in self.leaf_cohorts.values():
            # Update thermal time for this cohort
            cohort.thermal_time_since_appearance += daily_thermal_time
            
            # Calculate area expansion for this cohort
            if cohort.stage == LeafStage.EMERGING:
                # Transition to expanding after some thermal time
                if cohort.thermal_time_since_appearance > 5.0:
                    cohort.stage = LeafStage.EXPANDING
            
            elif cohort.stage == LeafStage.EXPANDING:
                # Calculate daily area increase
                relative_expansion_rate = self.params.leaf_area_expansion_rate * expansion_factor
                
                # Slower expansion as leaf approaches max size
                size_factor = 1.0 - (cohort.current_area / cohort.max_potential_area) ** 2
                daily_increase = (cohort.max_potential_area * relative_expansion_rate * 
                                size_factor)
                
                cohort.current_area = min(
                    cohort.max_potential_area,
                    cohort.current_area + daily_increase
                )
                
                # Transition to mature when 95% of max area reached
                if cohort.current_area >= 0.95 * cohort.max_potential_area:
                    cohort.stage = LeafStage.MATURE
            
            elif cohort.stage == LeafStage.MATURE:
                # Check for senescence initiation (old leaves or stress)
                # Lettuce leaves should last 6-8 weeks (600-800 thermal time units)
                age_factor = cohort.thermal_time_since_appearance / 600.0  # More realistic lifespan
                stress_senescence = (1.0 - expansion_factor) * 0.1
                
                # Only start senescence if leaf is truly old (>600 TT) or under severe stress (>0.08)
                if age_factor > 1.0 or stress_senescence > 0.08:
                    cohort.stage = LeafStage.SENESCING
                    cohort.senescence_rate = max(0.01, age_factor * 0.005 + stress_senescence)
            
            elif cohort.stage == LeafStage.SENESCING:
                # Reduce leaf area due to senescence
                area_loss = cohort.current_area * cohort.senescence_rate
                cohort.current_area = max(0.0, cohort.current_area - area_loss)
                senesced_area += area_loss
            
            total_area += cohort.current_area
            if cohort.current_area > 0.001:  # Count as active leaf
                active_leaves += 1
        
        # Calculate LAI (assuming 1 m² growing area per plant for base calculation)
        lai = total_area  # Will be scaled by plant density in main simulation
        
        return {
            'total_leaf_area_m2': total_area,
            'leaf_area_index': lai,
            'active_leaf_count': active_leaves,
            'senesced_area_daily': senesced_area,
            'average_leaf_area': total_area / max(1, active_leaves)
        }
    
    def daily_update(self, temperature: float, water_stress: float = 1.0,
                    nitrogen_stress: float = 1.0, temperature_stress: float = 1.0) -> Dict[str, float]:
        """
        Complete daily update of leaf development.
        
        Args:
            temperature: Daily average temperature (°C)
            water_stress: Water stress factor (0-1, 1=no stress)
            nitrogen_stress: Nitrogen stress factor (0-1, 1=no stress)  
            temperature_stress: Temperature stress factor (0-1, 1=no stress)
            
        Returns:
            Dictionary with leaf development results
        """
        # Calculate thermal time
        daily_tt = self.calculate_thermal_time(temperature)
        
        # Calculate stress factors
        stress_factors = self.calculate_stress_factors(
            water_stress, nitrogen_stress, temperature_stress
        )
        
        # Update V-stage (leaf appearance)
        new_leaf_appeared = self.update_v_stage(daily_tt, stress_factors)
        
        # Update leaf areas
        leaf_metrics = self.update_leaf_areas(daily_tt, stress_factors)
        
        # Compile results - count leaves that are emerged and still viable
        active_leaf_count = len([c for c in self.leaf_cohorts.values() 
                               if c.stage in [LeafStage.EMERGING, LeafStage.EXPANDING, 
                                            LeafStage.MATURE, LeafStage.SENESCING] 
                               and c.current_area > 0.0001])
        
        results = {
            'v_stage': self.current_v_stage,
            'leaf_number': active_leaf_count,
            'new_leaf_appeared': new_leaf_appeared,
            'thermal_time_daily': daily_tt,
            'cumulative_thermal_time': self.cumulative_thermal_time,
            **leaf_metrics,
            **stress_factors
        }
        
        return results
    
    def get_leaf_cohort_details(self) -> Dict[int, Dict[str, float]]:
        """Get detailed information about all leaf cohorts."""
        details = {}
        for cohort_id, cohort in self.leaf_cohorts.items():
            details[cohort_id] = {
                'appearance_day': cohort.appearance_day,
                'current_area_m2': cohort.current_area,
                'max_area_m2': cohort.max_potential_area,
                'stage': cohort.stage.value,
                'thermal_time_age': cohort.thermal_time_since_appearance,
                'area_completion_percent': (cohort.current_area / cohort.max_potential_area) * 100
            }
        return details


def create_lettuce_leaf_model() -> LeafDevelopmentModel:
    """Create leaf development model with lettuce-specific parameters."""
    try:
        from ..utils.config_loader import get_config_loader
        config_loader = get_config_loader()
        leaf_config = config_loader.get_leaf_development_parameters()
        parameters = LeafParameters.from_config(leaf_config)
        return LeafDevelopmentModel(parameters)
    except ImportError:
        # Fallback to default values if config loader not available
        return LeafDevelopmentModel()


def demonstrate_leaf_development():
    """Demonstrate leaf development over a growing season."""
    model = create_lettuce_leaf_model()
    
    print("=" * 80)
    print("LETTUCE LEAF DEVELOPMENT SIMULATION")  
    print("=" * 80)
    
    # Simulate 45 days of growth
    temperatures = [20, 22, 24, 23, 25, 27, 26, 24, 22, 20] * 5  # Temperature cycle
    
    print(f"{'Day':<4} {'Temp':<5} {'V-Stage':<8} {'Leaves':<7} {'LAI':<6} {'Avg Leaf':<9} {'New?':<5}")
    print("-" * 80)
    
    for day in range(1, 46):
        temp = temperatures[day % len(temperatures)]
        
        # Simulate some stress conditions  
        water_stress = 1.0 if day < 30 else 0.8  # Water stress late in season
        nitrogen_stress = 1.0 if day < 20 else 0.9  # Mild N stress later
        temp_stress = 1.0 if 18 <= temp <= 26 else 0.8  # Temperature stress
        
        results = model.daily_update(temp, water_stress, nitrogen_stress, temp_stress)
        
        if day % 3 == 1:  # Print every 3rd day
            print(f"{day:<4} {temp:<5.1f} {results['v_stage']:<8.1f} "
                  f"{results['leaf_number']:<7} {results['leaf_area_index']:<6.3f} "
                  f"{results['average_leaf_area']*10000:<9.1f} {'Yes' if results['new_leaf_appeared'] else 'No':<5}")
    
    # Show final cohort details
    print(f"\nFinal leaf cohort details:")
    print(f"{'ID':<4} {'Stage':<10} {'Area(cm²)':<10} {'Complete%':<10}")
    print("-" * 40)
    
    details = model.get_leaf_cohort_details()
    for cohort_id, info in list(details.items())[:10]:  # Show first 10
        area_cm2 = info['current_area_m2'] * 10000
        print(f"{cohort_id:<4} {info['stage']:<10} {area_cm2:<10.1f} "
              f"{info['area_completion_percent']:<10.1f}")


if __name__ == "__main__":
    demonstrate_leaf_development()