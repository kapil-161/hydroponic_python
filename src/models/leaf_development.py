"""
Leaf Development Model

Key equations:
- thermal_time = f(temperature, Tmin, Topt1, Topt2, Tmax)
- leaf_appearance = cumulative_thermal_time >= phyllochron_adjusted
- leaf_growth = remaining_potential × growth_rate × stress_factors
- senescence_rate = f(age_factor, stress_senescence)
"""

from typing import Dict, Any
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
    base_phyllochron: float      # Base phyllochron (°C-day) for lettuce
    min_temp: float               # Base temperature for development (°C)
    opt_temp_min: float          # Lower optimum temperature (°C)  
    opt_temp_max: float          # Upper optimum temperature (°C)
    max_temp: float              # Maximum temperature for development (°C)
    
    # Leaf appearance and expansion
    max_leaf_number: float       # Maximum leaves for lettuce
    initial_leaf_number: float    # Cotyledons + first true leaves
    leaf_appearance_rate: float   # Leaves per phyllochron unit
    specific_leaf_area: float        # cm²/g dry weight
    
    # Individual leaf parameters
    max_individual_leaf_area: float  # m² per mature leaf
    leaf_area_expansion_rate: float   # Natural cellular expansion rate
    
    # Stress response parameters
    water_stress_threshold: float      # Below this, leaf development slows
    nitrogen_stress_threshold: float   # Below this, leaf expansion reduces
    temperature_stress_sensitivity: float  # Response to temp stress
    
    # Additional parameters for calculations
    initial_leaf_area_factor: float    # Factor for initial leaf area (from CSV)
    initial_thermal_time_factor: float  # Factor for initial thermal time (from CSV)
    emerging_to_expanding_factor: float  # Factor for emerging to expanding transition (from CSV)
    late_leaf_phyllochron_factor: float  # Factor for late leaf phyllochron (from CSV)
    very_late_leaf_phyllochron_factor: float  # Factor for very late leaf phyllochron (from CSV)
    early_leaf_size_factor: float     # Size factor for early leaves (from CSV)
    late_leaf_size_factor: float       # Size factor for late leaves (from CSV)
    leaf_maturation_thermal_time: float  # Thermal time for leaf maturation (from CSV)
    leaf_lifespan_thermal_time: float  # Thermal time for leaf lifespan (from CSV)
    senescence_threshold_age: float    # Age threshold for senescence initiation (from CSV)
    senescence_rate_base: float       # Base senescence rate (from CSV)
    minimum_active_leaf_area: float   # Minimum area for active leaf counting (from CSV)
    minimum_visible_leaf_area: float  # Minimum area for visible leaf counting (from CSV)

    # V-stage and position thresholds (from CSV)
    late_leaf_vstage_threshold: float       # V-stage threshold for late leaf classification
    very_late_leaf_vstage_threshold: float  # V-stage threshold for very late leaf classification
    early_leaf_position_threshold: float    # V-stage threshold for early leaf position classification
    middle_leaf_position_threshold: float   # V-stage threshold for middle leaf position classification
    early_position_scaling_factor: float    # Scaling factor for early leaf position calculation
    late_position_scaling_factor: float     # Scaling factor for late leaf position calculation

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LeafParameters':
        leaf_params = config['leaf_development']
        canopy_params = config['canopy_parameters']
        phenology_params = config.get('phenology', {})
        nitrogen_params = config.get('nitrogen_parameters', {})
        
        # Merge parameters from different sections, handling duplicates
        merged_params = leaf_params.copy()

        # Use existing SLAVR from genetic_parameters (avoid duplicate parameters)
        genetic_params = config.get('genetic_parameters', {})
        merged_params['specific_leaf_area'] = genetic_params['SLAVR']

        # Use existing thermal time parameters (avoid duplicate parameters)
        thermal_params = config.get('thermal_time', {})
        merged_params['min_temp'] = thermal_params['base_temp']
        merged_params['opt_temp_min'] = thermal_params['optimal_temp_min']
        merged_params['opt_temp_max'] = thermal_params['optimal_temp_max']
        merged_params['max_temp'] = thermal_params['max_temp']

        # Use leaf_development stress thresholds (specific to this model)
        # Note: drought_threshold exists in phenology_parameters but has different meaning
        merged_params['drought_threshold'] = leaf_params['drought_threshold']
        merged_params['n_stress_threshold'] = leaf_params['n_stress_threshold']
        
        return cls(
            base_phyllochron=merged_params['base_phyllochron'],
            min_temp=merged_params['min_temp'],
            opt_temp_min=merged_params['opt_temp_min'],
            opt_temp_max=merged_params['opt_temp_max'],
            max_temp=merged_params['max_temp'],
            max_leaf_number=merged_params['max_leaf_number'],
            initial_leaf_number=merged_params['initial_leaf_number'],
            leaf_appearance_rate=merged_params['leaf_appearance_rate'],
            max_individual_leaf_area=merged_params['max_individual_leaf_area'],
            leaf_area_expansion_rate=merged_params['leaf_area_expansion_rate'],
            specific_leaf_area=merged_params['specific_leaf_area'],
            water_stress_threshold=merged_params['drought_threshold'],
            nitrogen_stress_threshold=merged_params['n_stress_threshold'],
            temperature_stress_sensitivity=merged_params['temperature_stress_sensitivity'],
            initial_leaf_area_factor=merged_params['initial_leaf_area_factor'],
            initial_thermal_time_factor=merged_params['initial_thermal_time_factor'],
            emerging_to_expanding_factor=merged_params['emerging_to_expanding_factor'],
            late_leaf_phyllochron_factor=merged_params['late_leaf_phyllochron_factor'],
            very_late_leaf_phyllochron_factor=merged_params['very_late_leaf_phyllochron_factor'],
            early_leaf_size_factor=merged_params['early_leaf_size_factor'],
            late_leaf_size_factor=merged_params['late_leaf_size_factor'],
            leaf_maturation_thermal_time=merged_params['leaf_maturation_thermal_time'],
            leaf_lifespan_thermal_time=merged_params['leaf_lifespan_thermal_time'],
            senescence_threshold_age=merged_params['senescence_threshold_age'],
            senescence_rate_base=merged_params['senescence_rate_base'],
            minimum_active_leaf_area=merged_params['minimum_active_leaf_area'],
            minimum_visible_leaf_area=merged_params['minimum_visible_leaf_area'],
            late_leaf_vstage_threshold=merged_params['late_leaf_vstage_threshold'],
            very_late_leaf_vstage_threshold=merged_params['very_late_leaf_vstage_threshold'],
            early_leaf_position_threshold=merged_params['early_leaf_position_threshold'],
            middle_leaf_position_threshold=merged_params['middle_leaf_position_threshold'],
            early_position_scaling_factor=merged_params['early_position_scaling_factor'],
            late_position_scaling_factor=merged_params['late_position_scaling_factor']
        )


@dataclass 
class LeafCohort:
    """Individual leaf cohort tracking."""
    cohort_id: int
    appearance_day: float          # Day when leaf appeared (V-stage)
    current_area: float           # Current leaf area (m²)
    max_potential_area: float     # Maximum potential area (m²)
    stage: LeafStage              # Current development stage
    thermal_time_since_appearance: float
    senescence_rate: float


class LeafDevelopmentModel:
    """Leaf development model following DSSAT CROPGRO principles."""
    
    def __init__(self, parameters: LeafParameters):
        self.params = parameters
        self.leaf_cohorts: Dict[int, LeafCohort] = {}
        self.current_v_stage: float = self.params.initial_leaf_number
        self.cumulative_thermal_time: float = 0.0
        self.next_cohort_id: int = 1
        
        # Initialize with initial leaves
        for i in range(int(self.params.initial_leaf_number)):
            self._create_initial_leaf_cohort(i + 1)

        # Set next cohort ID to be after all initial cohorts
        self.next_cohort_id = int(self.params.initial_leaf_number) + 1
    
    def calculate_thermal_time(self, temperature_list: list) -> list:
        """Use consolidated thermal time calculation from core_utils."""
        from src.utils.core_utils import calculate_thermal_time_list

        # Create config structure for consolidated function
        thermal_config = type('Config', (), {
            'thermal_time': {
                'base_temp': self.params.min_temp,
                'optimal_temp_min': self.params.opt_temp_min,
                'optimal_temp_max': self.params.opt_temp_max,
                'max_temp': self.params.max_temp
            }
        })

        return calculate_thermal_time_list(temperature_list, thermal_config, method='cardinal')
    
    def calculate_stress_factors(self, water_stress_list: list, 
                               nitrogen_stress_list: list,
                               temperature_stress_list: list) -> Dict[str, list]:
        """
        Calculate stress effects on leaf development.
        Equations: 
        - water_factor = max(min_area, water_stress / threshold) if water_stress < threshold else 1.0
        - nitrogen_factor = max(min_visible, nitrogen_stress / threshold) if nitrogen_stress < threshold else 1.0
        - temp_factor = max(min_area, 1.0 - (1.0 - temp_stress) * sensitivity)
        """
        water_factors = []
        nitrogen_factors = []
        temp_factors = []
        combined_appearance_factors = []
        combined_expansion_factors = []
        
        for i in range(len(water_stress_list)):
            # Water stress effect on leaf appearance
            water_factor = 1.0
            if water_stress_list[i] < self.params.water_stress_threshold:
                water_factor = max(self.params.minimum_active_leaf_area, water_stress_list[i] / self.params.water_stress_threshold)
            
            # Nitrogen stress effect on leaf expansion
            nitrogen_factor = 1.0 
            if nitrogen_stress_list[i] < self.params.nitrogen_stress_threshold:
                nitrogen_factor = max(self.params.minimum_visible_leaf_area, nitrogen_stress_list[i] / self.params.nitrogen_stress_threshold)
            
            # Temperature stress effect
            temp_factor = max(self.params.minimum_active_leaf_area, 1.0 - temperature_stress_list[i] * self.params.temperature_stress_sensitivity)
            
            water_factors.append(water_factor)
            nitrogen_factors.append(nitrogen_factor)
            temp_factors.append(temp_factor)
            combined_appearance_factors.append(water_factor * temp_factor)
            combined_expansion_factors.append(water_factor * nitrogen_factor * temp_factor)
        
        return {
            'water_factor': water_factors,
            'nitrogen_factor': nitrogen_factors, 
            'temperature_factor': temp_factors,
            'combined_appearance_factor': combined_appearance_factors,
            'combined_expansion_factor': combined_expansion_factors
        }
    
    def update_v_stage(self, daily_thermal_time_list: list, stress_factors: Dict[str, list]) -> list:
        """
        Update V-stage (leaf appearance) based on thermal time and stress.
        Equation: new_leaf = cumulative_thermal_time >= phyllochron_adjusted
        """
        new_leaves_appeared = []
        
        for i in range(len(daily_thermal_time_list)):
            # Accumulate thermal time with stress effects
            effective_thermal_time = daily_thermal_time_list[i] * stress_factors['combined_appearance_factor'][i]
            self.cumulative_thermal_time += effective_thermal_time
            
            # Check if enough thermal time accumulated for new leaf
            thermal_time_for_next_leaf = self.params.base_phyllochron
            
            # Adjust phyllochron based on current development stage using CSV parameters
            if self.current_v_stage > self.params.very_late_leaf_vstage_threshold:  # Very late leaves (20+)
                thermal_time_for_next_leaf *= self.params.very_late_leaf_phyllochron_factor
            elif self.current_v_stage > self.params.late_leaf_vstage_threshold:  # Late leaves (15-20)
                thermal_time_for_next_leaf *= self.params.late_leaf_phyllochron_factor
            
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
            
            new_leaves_appeared.append(new_leaf_appeared)
        
        return new_leaves_appeared
    
    def calculate_leaf_position_factors(self, v_stage_list: list) -> list:
        """
        Calculate relative leaf size based on position on plant.
        Equation: position_factor = f(v_stage, early_factor, late_factor)
        """
        position_factors = []
        for v_stage in v_stage_list:
            if v_stage <= self.params.early_leaf_position_threshold:
                # Early leaves get progressively larger but stay below 1.0
                normalized_position = (v_stage - 1) / self.params.early_position_scaling_factor
                factor = self.params.early_leaf_size_factor + normalized_position * (0.95 - self.params.early_leaf_size_factor)
            elif v_stage <= self.params.middle_leaf_position_threshold:
                factor = 1.0  # Full size middle leaves
            else:
                factor = max(self.params.late_leaf_size_factor, 1.0 - (v_stage - self.params.middle_leaf_position_threshold) * (1.0 - self.params.late_leaf_size_factor) / self.params.late_position_scaling_factor)
            position_factors.append(factor)
        return position_factors
    
    def update_leaf_areas(self, daily_thermal_time_list: list, 
                         stress_factors: Dict[str, list]) -> Dict[str, list]:
        """
        Update individual leaf areas for all cohorts.
        Equations:
        - daily_increase = remaining_potential × growth_rate × stress_factors
        - final_area = min(current_area + daily_increase, genetic_maximum)
        - senescence_rate = f(age_factor, stress_senescence)
        """
        total_areas = []
        lai_values = []
        visible_leaf_counts = []
        active_leaf_counts = []
        senesced_areas = []
        average_leaf_areas = []
        
        for day_idx in range(len(daily_thermal_time_list)):
            expansion_factor = stress_factors['combined_expansion_factor'][day_idx]
            daily_thermal_time = daily_thermal_time_list[day_idx]
            
            total_area = 0.0
            visible_leaves = 0
            active_leaves = 0
            senesced_area = 0.0
            cohorts_to_remove = []
            
            for cohort_id, cohort in self.leaf_cohorts.items():
                # Update thermal time for this cohort
                cohort.thermal_time_since_appearance += daily_thermal_time
                
                # Count all leaves that have appeared
                if cohort.stage != LeafStage.PRIMORDIAL:
                    visible_leaves += 1
                
                # Calculate area expansion for this cohort
                if cohort.stage == LeafStage.EMERGING:
                    if cohort.thermal_time_since_appearance > self.params.leaf_maturation_thermal_time * self.params.emerging_to_expanding_factor:
                        cohort.stage = LeafStage.EXPANDING
                
                elif cohort.stage == LeafStage.EXPANDING:
                    base_expansion_rate = self.params.leaf_area_expansion_rate
                    
                    temperature_factor = stress_factors.get('temperature_factor', [1.0] * len(daily_thermal_time_list))[day_idx]
                    nitrogen_factor = stress_factors.get('nitrogen_factor', [1.0] * len(daily_thermal_time_list))[day_idx]
                    water_factor = stress_factors.get('water_factor', [1.0] * len(daily_thermal_time_list))[day_idx]
                    
                    cell_division_factor = temperature_factor
                    cell_expansion_factor = water_factor * nitrogen_factor
                    
                    cell_division_factor_applied = base_expansion_rate * cell_division_factor
                    cell_expansion_factor_applied = base_expansion_rate * cell_expansion_factor
                    
                    combined_growth_factor = min(cell_division_factor_applied, cell_expansion_factor_applied)
                    
                    remaining_growth_potential = max(0.0, cohort.max_potential_area - cohort.current_area)
                    daily_increase = remaining_growth_potential * combined_growth_factor
                    
                    proposed_area = cohort.current_area + max(0.0, daily_increase)
                    cohort.current_area = min(proposed_area, cohort.max_potential_area)
                    
                    if cohort.thermal_time_since_appearance > self.params.leaf_maturation_thermal_time:
                        cohort.stage = LeafStage.MATURE
                
                elif cohort.stage == LeafStage.MATURE:
                    age_factor = cohort.thermal_time_since_appearance / self.params.leaf_lifespan_thermal_time
                    stress_senescence = (1.0 - expansion_factor) * self.params.senescence_rate_base
                    
                    if age_factor > self.params.senescence_threshold_age or stress_senescence > self.params.senescence_rate_base:
                        cohort.stage = LeafStage.SENESCING
                        cohort.senescence_rate = max(self.params.minimum_active_leaf_area, age_factor * self.params.senescence_rate_base + stress_senescence)
                
                elif cohort.stage == LeafStage.SENESCING:
                    area_loss = cohort.current_area * cohort.senescence_rate
                    cohort.current_area = max(0.0, cohort.current_area - area_loss)
                    senesced_area += area_loss
                    
                    if cohort.current_area < self.params.minimum_visible_leaf_area:
                        cohorts_to_remove.append(cohort_id)
                        continue
                
                total_area += cohort.current_area
                
                if cohort.current_area > self.params.minimum_active_leaf_area:
                    active_leaves += 1
            
            # Remove completely dead leaves
            for cohort_id in cohorts_to_remove:
                if cohort_id in self.leaf_cohorts:
                    del self.leaf_cohorts[cohort_id]
            
            lai = total_area
            
            total_areas.append(total_area)
            lai_values.append(lai)
            visible_leaf_counts.append(visible_leaves)
            active_leaf_counts.append(active_leaves)
            senesced_areas.append(senesced_area)
            average_leaf_areas.append(total_area / max(1, active_leaves))
        
        return {
            'total_leaf_area_m2': total_areas,
            'leaf_area_index': lai_values,
            'visible_leaf_count': visible_leaf_counts,
            'active_leaf_count': active_leaf_counts,
            'senesced_area_daily': senesced_areas,
            'average_leaf_area': average_leaf_areas
        }
    
    def _create_initial_leaf_cohort(self, cohort_id: int):
        """Create initial leaf cohorts (cotyledons + first leaves)."""
        initial_area = self.params.max_individual_leaf_area * self.params.initial_leaf_area_factor
        cohort = LeafCohort(
            cohort_id=cohort_id,
            appearance_day=0.0,
            current_area=initial_area,
            max_potential_area=self.params.max_individual_leaf_area,
            stage=LeafStage.EXPANDING,
            thermal_time_since_appearance=self.params.leaf_maturation_thermal_time * self.params.initial_thermal_time_factor,
            senescence_rate=0.0
        )
        self.leaf_cohorts[cohort_id] = cohort
    
    def _create_new_leaf_cohort(self):
        """Create a new leaf cohort."""
        position_factors = self.calculate_leaf_position_factors([self.current_v_stage])
        max_area = self.params.max_individual_leaf_area * position_factors[0]
        
        cohort = LeafCohort(
            cohort_id=self.next_cohort_id,
            appearance_day=self.current_v_stage,
            current_area=self.params.minimum_visible_leaf_area,
            max_potential_area=max_area,
            stage=LeafStage.EMERGING,
            thermal_time_since_appearance=0.0,
            senescence_rate=0.0
        )
        
        self.leaf_cohorts[self.next_cohort_id] = cohort
        self.next_cohort_id += 1


def create_lettuce_leaf_development_model(system_config: Any) -> LeafDevelopmentModel:
    config = {
        'leaf_development': getattr(system_config, 'leaf_development', {}),
        'canopy_parameters': getattr(system_config, 'canopy_parameters', {}),
        'phenology': getattr(system_config, 'phenology_parameters', {}),  # Updated to match CSV
        'nitrogen_parameters': getattr(system_config, 'nitrogen_parameters', {}),
        'genetic_parameters': getattr(system_config, 'genetic_parameters', {}),
        'thermal_time': getattr(system_config, 'thermal_time', {})
    }

    if not config['leaf_development']:
        raise ValueError("leaf_development section must be provided in CSV configuration")

    if not config['canopy_parameters']:
        raise ValueError("canopy_parameters section must be provided in CSV configuration")

    parameters = LeafParameters.from_config(config)
    return LeafDevelopmentModel(parameters)


"""
INPUT PARAMETERS (from CSV):
- base_phyllochron: thermal time interval between leaf appearances (°C-day)
- min_temp: base temperature for development (°C)
- opt_temp_min: lower optimum temperature (°C)
- opt_temp_max: upper optimum temperature (°C)
- max_temp: maximum temperature for development (°C)
- max_leaf_number: maximum number of leaves
- initial_leaf_number: initial number of leaves (cotyledons + first true leaves)
- leaf_appearance_rate: leaves per phyllochron unit
- max_individual_leaf_area: maximum area per individual leaf (m²)
- leaf_area_expansion_rate: natural cellular expansion rate
- specific_leaf_area: leaf area per unit dry weight (cm²/g)
- drought_threshold: water stress threshold for leaf development
- n_stress_threshold: nitrogen stress threshold for leaf expansion
- temperature_stress_sensitivity: response to temperature stress
- initial_leaf_area_factor: factor for initial leaf area
- initial_thermal_time_factor: factor for initial thermal time
- emerging_to_expanding_factor: factor for emerging to expanding transition
- late_leaf_phyllochron_factor: factor for late leaf phyllochron
- very_late_leaf_phyllochron_factor: factor for very late leaf phyllochron
- early_leaf_size_factor: size factor for early leaves
- late_leaf_size_factor: size factor for late leaves
- leaf_maturation_thermal_time: thermal time for leaf maturation
- leaf_lifespan_thermal_time: thermal time for leaf lifespan
- senescence_threshold_age: age threshold for senescence initiation
- senescence_rate_base: base senescence rate
- minimum_active_leaf_area: minimum area for active leaf counting
- minimum_visible_leaf_area: minimum area for visible leaf counting

INPUT VARIABLES:
- temperature_list: daily temperatures (°C)
- water_stress_list: daily water stress levels (0-1)
- nitrogen_stress_list: daily nitrogen stress levels (0-1)
- temperature_stress_list: daily temperature stress levels (0-1)
- daily_thermal_time_list: daily thermal time values (°C-day)

OUTPUT VARIABLES:
- thermal_time_list: calculated thermal time values (°C-day)
- stress_factors: dictionary with water_factor, nitrogen_factor, temperature_factor, combined_appearance_factor, combined_expansion_factor lists
- new_leaves_appeared: list of boolean values indicating new leaf appearance each day
- position_factors: list of leaf size factors based on position
- leaf_areas: dictionary with total_leaf_area_m2, leaf_area_index, visible_leaf_count, active_leaf_count, senesced_area_daily, average_leaf_area lists
"""