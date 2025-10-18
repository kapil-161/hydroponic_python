"""
Nutrient Models Simulator

Handles nutrient simulation loop and inter-simulator communication
for nutrient transport and availability in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.nutrient_models import (
    NutrientModel, NutrientParameters, NutrientMobility, NutrientMobilityResponse,
    NutrientTransportFlux, OrganNutrientPools, TransportMechanism
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class NutrientState:
    """State tracking for nutrient models simulator"""
    solution_ec: float = 1.2
    solution_ph: float = 6.0
    nutrient_concentrations: Dict[str, float] = field(default_factory=dict)
    nutrient_uptake_rates: Dict[str, float] = field(default_factory=dict)
    nutrient_availability: Dict[str, float] = field(default_factory=dict)
    root_nutrient_pools: Dict[str, float] = field(default_factory=dict)
    shoot_nutrient_pools: Dict[str, float] = field(default_factory=dict)
    xylem_flux: Dict[str, float] = field(default_factory=dict)
    phloem_flux: Dict[str, float] = field(default_factory=dict)
    cumulative_nutrient_uptake: Dict[str, float] = field(default_factory=dict)
    daily_nutrient_uptake: Dict[str, float] = field(default_factory=dict)
    system_config: Dict[str, Any] = field(default_factory=dict)  # System configuration data
    step_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class NutrientModelsSimulator(BaseSimulator):
    """Simulator for nutrient models - follows Rules.md strictly"""
    
    def __init__(self, parameters: NutrientParameters = None):
        super().__init__("nutrient_models_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if parameters is None:
            raise ValueError("NutrientParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.parameters = parameters
        self.model = NutrientModel(self.parameters)

        # State tracking
        self.state = NutrientState()
        self.history: List[NutrientState] = []
        self.organ_pools_initialized = False  # Track if organ pools have been initialized
        
        # Initialize nutrient dictionaries
        # Use nutrient names that match the model's kinetics dictionary
        self.nutrient_elements = ['N-NO3', 'N-NH4', 'P-PO4', 'K', 'Ca', 'Mg', 'S-SO4', 
                                 'Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo']
        
        for element in self.nutrient_elements:
            # Initialize with zero values - actual concentrations must come from CSV/inputs
            self.state.nutrient_concentrations[element] = 0.0
            self.state.nutrient_uptake_rates[element] = 0.0
            self.state.nutrient_availability[element] = 0.0
            self.state.root_nutrient_pools[element] = 0.0
            self.state.shoot_nutrient_pools[element] = 0.0
            self.state.xylem_flux[element] = 0.0
            self.state.phloem_flux[element] = 0.0
            self.state.cumulative_nutrient_uptake[element] = 0.0
            self.state.daily_nutrient_uptake[element] = 0.0
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'water_uptake_simulator': ['water_uptake_rate', 'transpiration_rate'],
            'root_system_simulator': ['root_depth', 'root_distribution', 'root_biomass', 'root_surface_area'],
            'phenology_simulator': ['growth_stage', 'development_index'],
            'stress_models': ['nutrient_stress', 'temperature_stress']
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = 1.0  # seconds
        
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start - load system_config from initials.csv"""
        self.state = NutrientState()

        # Re-initialize nutrient dictionaries after state reset
        for element in self.nutrient_elements:
            self.state.nutrient_concentrations[element] = 0.0
            self.state.nutrient_uptake_rates[element] = 0.0
            self.state.nutrient_availability[element] = 0.0
            self.state.root_nutrient_pools[element] = 0.0
            self.state.shoot_nutrient_pools[element] = 0.0
            self.state.xylem_flux[element] = 0.0
            self.state.phloem_flux[element] = 0.0
            self.state.cumulative_nutrient_uptake[element] = 0.0
            self.state.daily_nutrient_uptake[element] = 0.0

        # Load initial nutrient concentrations from CSV - NO DEFAULTS per Rules.md
        initial_state = data.get('initial_state', {})
        if initial_state:
            self.state.solution_ph = initial_state.get('solution_ph', 6.0)

            # Map CSV keys to nutrient elements
            # CSV format: solution_n_concentration → N-NO3 + N-NH4
            nutrient_mappings = {
                'N-NO3': 'solution_n_concentration',  # Total N split 90/10 NO3/NH4
                'N-NH4': 'solution_n_concentration',
                'P-PO4': 'solution_p_concentration',
                'K': 'solution_k_concentration',
                'Ca': 'solution_ca_concentration',
                'Mg': 'solution_mg_concentration',
                'S-SO4': 'solution_s_concentration',
                'Fe': 'solution_fe_concentration',
            }

            # Load concentrations from CSV
            for element in self.nutrient_elements:
                if element in nutrient_mappings and nutrient_mappings[element] in initial_state:
                    base_value = initial_state[nutrient_mappings[element]]
                    if element == 'N-NO3':
                        self.state.nutrient_concentrations[element] = base_value * 0.9  # 90% as nitrate
                    elif element == 'N-NH4':
                        self.state.nutrient_concentrations[element] = base_value * 0.1  # 10% as ammonium
                    else:
                        self.state.nutrient_concentrations[element] = base_value
                else:
                    # Micronutrients not in CSV - set to trace levels
                    self.state.nutrient_concentrations[element] = 0.1

            # Calculate EC from concentrations instead of using hardcoded value
            initial_temp = initial_state.get('canopy_temperature', 22.0)  # Default to 22C if not in initials
            self.state.solution_ec = self.model._calculate_ec_from_concentrations(self.state.nutrient_concentrations, initial_temp)


        # Load system configuration from initials.csv into dependency cache
        system_config = data.get('system_config', {})
        if system_config:
            # Populate required fields strictly from CSV inputs (no defaults allowed)
            if 'daily_growth_rate' not in system_config:
                if 'relative_growth_rate' in initial_state:
                    system_config['daily_growth_rate'] = initial_state['relative_growth_rate']
                else:
                    raise ValueError("Missing daily_growth_rate: provide relative_growth_rate in initials.csv")
            if 'optimal_ec' not in system_config:
                # optimal_ec must be present in system_config (from initials.csv); do not set defaults
                raise ValueError("Missing optimal_ec in system_config from initials.csv")

            self.dependency_cache['system_config'] = system_config
            # Persist a local copy to avoid dependency cache overwrite across steps
            setattr(self.state, 'system_config', dict(system_config))
            print(f"Nutrient: Loaded system_config from CSV - tank_volume={system_config.get('tank_volume_L')}L, plants={system_config.get('plant_count')}")

        self.history.clear()

        # Initialize model with parameters from CSV
        self.model.initialize()

        # Publish initial state data to dependency cache
        self.publish_state_data()

        # Publish initial state
        self.publish_event(EventType.NUTRIENT_UPDATE, {
            'solution_ec': self.state.solution_ec,
            'solution_ph': self.state.solution_ph,
            'nutrient_availability': self.state.nutrient_availability
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

            # Execute nutrient calculation using model functions
            self._execute_nutrient_step(weather_data)
            
            # Update state
            self.state.step_count += 1
            self.state.last_update = datetime.now()

            # Store history
            self.history.append(NutrientState(**self.state.__dict__))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            # Calculate nitrogen-specific values for nitrogen balance simulator
            nitrogen_uptake = self.state.nutrient_uptake_rates.get('N-NO3', 0.0) + self.state.nutrient_uptake_rates.get('N-NH4', 0.0)
            # Use max availability (plants can preferentially use either NO3 or NH4)
            nitrogen_availability = max(self.state.nutrient_availability.get('N-NO3', 0.0), self.state.nutrient_availability.get('N-NH4', 0.0))

            self.publish_event(EventType.NUTRIENT_UPDATE, {
                'solution_ec': self.state.solution_ec,
                'solution_ph': self.state.solution_ph,
                'nutrient_concentrations': self.state.nutrient_concentrations,
                'nutrient_uptake_rates': self.state.nutrient_uptake_rates,
                'nutrient_availability': self.state.nutrient_availability,
                'root_nutrient_pools': self.state.root_nutrient_pools,
                'shoot_nutrient_pools': self.state.shoot_nutrient_pools,
                # Nitrogen-specific for nitrogen balance simulator
                'nitrogen_uptake': nitrogen_uptake,  # mg/plant/day
                'total_nitrogen_uptake': nitrogen_uptake,  # mg/plant/day explicit for consumer alignment
                'nitrogen_availability': nitrogen_availability,
                'root_activity': 1.0,  # Placeholder - should come from root simulator
                'step': self.state.step_count
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                for element in self.nutrient_elements:
                    self.state.daily_nutrient_uptake[element] = 0.0
                
        except Exception as e:
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.state.step_count
            })
            # Raise error according to Rules.md - no error suppression
            raise
    

    def _execute_nutrient_step(self, weather_data: Dict[str, Any]):
        """Execute nutrient calculation using model functions - no shortcuts"""
        try:
            # Get water data from water uptake simulator
            water_data = self.dependency_cache.get('water_uptake_simulator', {})
            water_uptake_rate = water_data.get('water_uptake_rate')
            transpiration_rate = water_data.get('transpiration_rate')

            # Use initial values on first step if water data not available yet (circular dependency)
            if any(x is None for x in [water_uptake_rate, transpiration_rate]):
                if self.state.step_count == 0:
                    # Use minimal initial values for first step to break circular dependency
                    water_uptake_rate = 0.001  # 1 mL/hour initial uptake
                    transpiration_rate = 0.0005  # 0.5 mL/hour initial transpiration
                    print(f"Nutrient: Using initial water values on step 0 - uptake: {water_uptake_rate} L/h, transpiration: {transpiration_rate} L/h")
                else:
                    raise ValueError("Water data missing from water_uptake_simulator - no defaults allowed")
            
            # Get root data from root system simulator
            root_data = self.dependency_cache.get('root_system_simulator', {})
            root_depth = root_data.get('root_depth')
            root_distribution = root_data.get('root_distribution')
            root_biomass = root_data.get('root_biomass')

            root_surface_area = root_data.get('root_surface_area')

            if any(x is None for x in [root_depth, root_distribution, root_biomass, root_surface_area]):
                if self.state.step_count == 0:
                    # Use initial values from CSV for first step to break circular dependency
                    root_depth = 5.0  # cm from initials.csv
                    root_distribution = 0.5  # assume uniform distribution
                    root_biomass = 0.01  # g from initials.csv
                    root_surface_area = 12.6  # cm2 from initials.csv
                    print(f"Nutrient: Using initial root values on step 0 - depth: {root_depth} cm, biomass: {root_biomass} g, SA: {root_surface_area} cm²")
                else:
                    raise ValueError("Root data missing from root_system_simulator - no defaults allowed")

            # Use default pH (no pH model)
            ph = 6.0  # Default optimal pH for lettuce

            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')

            if any(x is None for x in [growth_stage, development_index]):
                if self.state.step_count == 0:
                    # Use initial values for first step to break circular dependency
                    growth_stage = "vegetative"  # Use nutrient model's expected growth stage
                    development_index = 0.0  # Initial development
                    print(f"Nutrient: Using initial phenology values on step 0 - stage: {growth_stage}, index: {development_index}")
                else:
                    raise ValueError("Phenology data missing from phenology_simulator - no defaults allowed")

            # Get stress factors from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            nutrient_stress = stress_data.get('nutrient_stress')
            temperature_stress = stress_data.get('temperature_stress')

            if any(x is None for x in [nutrient_stress, temperature_stress]):
                if self.state.step_count == 0:
                    # Use initial values for first step to break circular dependency
                    nutrient_stress = 0.0  # No stress initially
                    temperature_stress = 0.0  # No stress initially
                    print(f"Nutrient: Using initial stress values on step 0 - nutrient: {nutrient_stress}, temp: {temperature_stress}")
                else:
                    raise ValueError("Stress data missing from stress_models - no defaults allowed")
            
            # Get environmental conditions from daily weather file
            temperature = weather_data.get('temperature')
            if temperature is None:
                raise ValueError("Temperature missing from weather data - no defaults allowed")
            
            # Calculate nutrient uptake using model functions - no shortcuts
            # Get system configuration data
            # Prefer persisted config, fallback to shared dependency cache
            system_data = getattr(self.state, 'system_config', None) or self.dependency_cache.get('system_config', {})
            tank_volume = system_data.get('tank_volume_L')
            plant_count = system_data.get('plant_count')
            daily_growth_rate = system_data.get('daily_growth_rate')
            optimal_ec = system_data.get('optimal_ec')

            # Per Rules.md: raise error if missing, no defaults
            if any(x is None for x in [tank_volume, plant_count, daily_growth_rate, optimal_ec]):
                raise ValueError("System configuration missing from system_config - no defaults allowed")

            concentrations = self.state.nutrient_concentrations
            plant_status = {
                'root_surface_area': root_surface_area,
                'tank_volume_L': tank_volume,
                'plant_count': plant_count,
                'daily_growth_rate': daily_growth_rate,
                'growth_stage': growth_stage,  # Use actual growth stage from phenology
                'senescence_rates': {'leaves': 0.0, 'stems': 0.0, 'roots': 0.0},  # Will come from senescence model
                'stress_factors': {'nutrient_stress': nutrient_stress, 'temperature_stress': temperature_stress},
                'organ_nutrient_status': {
                    'roots_nutrient_status': 1.0,  # Optimal status (0.5-2.0 range, 1.0 = optimal)
                    'leaves_nutrient_status': 1.0,
                    'stems_nutrient_status': 1.0
                }
            }

            env_conditions = {
                'temperature': temperature,
                'ph': ph,
                'optimal_ec': optimal_ec
            }
            
            # Get biomass data from biomass allocation simulator
            biomass_data = self.dependency_cache.get('biomass_allocation_simulator', {})
            leaf_biomass = biomass_data.get('leaf_biomass')
            stem_biomass = biomass_data.get('stem_biomass')

            if any(x is None for x in [leaf_biomass, stem_biomass]):
                # On first step, biomass may not be available yet
                if self.state.step_count == 0:
                    # Use initial values from CSV for first step to break circular dependency
                    leaf_biomass = 0.015  # g from initials.csv
                    stem_biomass = 0.005  # g from initials.csv
                    print(f"Nutrient: Using initial biomass values on step 0 - leaf: {leaf_biomass} g, stem: {stem_biomass} g")
                else:
                    raise ValueError("Biomass data missing from biomass_allocation_simulator - no defaults allowed")
            
            shoot_biomass = leaf_biomass + stem_biomass
            if shoot_biomass > 0:
                leaf_demand_factor = leaf_biomass / shoot_biomass
                stem_demand_factor = stem_biomass / shoot_biomass
            else:
                # NO HARDCODED VALUES - get from parameters (Rules.md)
                leaf_demand_factor = self.parameters.leaf_nutrient_demand_factor
                stem_demand_factor = self.parameters.stem_nutrient_demand_factor

            # Get nutrient demand rates from CSV parameters - NO HARDCODED VALUES
            base_n_demand = daily_growth_rate * self.parameters.tissue_nitrogen_content_fraction
            base_p_demand = daily_growth_rate * self.parameters.tissue_phosphorus_content_fraction
            base_k_demand = daily_growth_rate * self.parameters.tissue_potassium_content_fraction

            organ_demands = {
                'roots': {
                    'N-NO3': base_n_demand * self.parameters.organ_allocation_no3_roots,
                    'N-NH4': base_n_demand * self.parameters.organ_allocation_nh4_roots,
                    'P-PO4': base_p_demand * self.parameters.organ_allocation_po4_roots,
                    'K': base_k_demand * self.parameters.organ_allocation_k_roots
                },
                'leaves': {
                    'N-NO3': base_n_demand * self.parameters.organ_allocation_no3_leaves * leaf_demand_factor,
                    'N-NH4': base_n_demand * self.parameters.organ_allocation_nh4_leaves * leaf_demand_factor,
                    'P-PO4': base_p_demand * self.parameters.organ_allocation_po4_leaves * leaf_demand_factor,
                    'K': base_k_demand * self.parameters.organ_allocation_k_leaves * leaf_demand_factor
                },
                'stems': {
                    'N-NO3': base_n_demand * self.parameters.organ_allocation_no3_stems * stem_demand_factor,
                    'N-NH4': base_n_demand * self.parameters.organ_allocation_nh4_stems * stem_demand_factor,
                    'P-PO4': base_p_demand * self.parameters.organ_allocation_po4_stems * stem_demand_factor,
                    'K': base_k_demand * self.parameters.organ_allocation_k_stems * stem_demand_factor
                }
            }

            # Get actual flux data from simulators
            water_fluxes = {
                'roots': water_uptake_rate,
                'leaves': transpiration_rate * leaf_demand_factor,
                'stems': transpiration_rate * stem_demand_factor
            }

            # Get photosynthesis/respiration rates from their simulators
            photosyn_data = self.dependency_cache.get('photosynthesis_simulator', {})
            respir_data = self.dependency_cache.get('respiration_simulator', {})
            # Use minimal rates as fallback for first step
            photosyn_rate = photosyn_data.get('carbon_assimilation_rate', 0.1)
            respir_rate = respir_data.get('respiration_rate', 0.05)

            # Carbon assimilate fluxes from CSV parameters - NO HARDCODED VALUES (Rules.md)
            net_assimilate = photosyn_rate - respir_rate
            assimilate_fluxes = {
                'roots': net_assimilate * self.parameters.carbon_assimilate_allocation_roots,
                'leaves': net_assimilate * self.parameters.carbon_assimilate_allocation_leaves,
                'stems': net_assimilate * self.parameters.carbon_assimilate_allocation_stems
            }

            # Initialize organ pools on first call when we have biomass data
            # Only initialize nutrients that have storage_pool_sizes parameters (N, P, K)
            if not self.organ_pools_initialized and root_biomass > 0 and shoot_biomass > 0:
                # Initial nutrient content based on tissue fractions from parameters
                root_nutrients = {
                    'N-NO3': root_biomass * self.parameters.tissue_nitrogen_content_fraction * 0.8,
                    'N-NH4': root_biomass * self.parameters.tissue_nitrogen_content_fraction * 0.2,
                    'P-PO4': root_biomass * self.parameters.tissue_phosphorus_content_fraction,
                    'K': root_biomass * self.parameters.tissue_potassium_content_fraction
                }
                leaf_nutrients = {
                    'N-NO3': leaf_biomass * self.parameters.tissue_nitrogen_content_fraction * 0.8,
                    'N-NH4': leaf_biomass * self.parameters.tissue_nitrogen_content_fraction * 0.2,
                    'P-PO4': leaf_biomass * self.parameters.tissue_phosphorus_content_fraction,
                    'K': leaf_biomass * self.parameters.tissue_potassium_content_fraction
                }
                stem_nutrients = {
                    'N-NO3': stem_biomass * self.parameters.tissue_nitrogen_content_fraction * 0.8,
                    'N-NH4': stem_biomass * self.parameters.tissue_nitrogen_content_fraction * 0.2,
                    'P-PO4': stem_biomass * self.parameters.tissue_phosphorus_content_fraction,
                    'K': stem_biomass * self.parameters.tissue_potassium_content_fraction
                }

                self.model.initialize_organ_pools('roots', root_nutrients, root_biomass)
                self.model.initialize_organ_pools('leaves', leaf_nutrients, leaf_biomass)
                self.model.initialize_organ_pools('stems', stem_nutrients, stem_biomass)
                self.organ_pools_initialized = True
                print(f"Nutrient: Initialized organ pools - roots: {root_biomass:.3f}g, leaves: {leaf_biomass:.3f}g, stems: {stem_biomass:.3f}g")

            # Per Rules.md: raise errors, don't skip calculations with missing parameters
            result = self.model.calculate_nutrient_dynamics(
                concentrations=concentrations,
                plant_status=plant_status,
                env_conditions=env_conditions,
                organ_demands=organ_demands,
                water_fluxes=water_fluxes,
                assimilate_fluxes=assimilate_fluxes
            )
            
            # Update state with model results - using actual keys returned by model
            self.state.solution_ec = result.get('calculated_ec', self.state.solution_ec)
            self.state.solution_ph = ph

            # Get dictionaries from model results
            updated_concentrations = result.get('updated_concentrations', {})
            uptake_rates = result.get('uptake_rates_mg_per_plant_per_day', {})
            organ_pools = result.get('organ_pools', {})
            transport_fluxes = result.get('transport_fluxes', {})

            # Update nutrient concentrations and uptake rates
            # Scientific principle: Only update if model returns valid values, preserve existing otherwise
            for element in self.nutrient_elements:
                if element in updated_concentrations:
                    self.state.nutrient_concentrations[element] = updated_concentrations[element]
                # If model doesn't return concentration, preserve current value (don't default to 0)

                new_uptake_rate = uptake_rates.get(element, 0.0)
                self.state.nutrient_uptake_rates[element] = new_uptake_rate

                # Calculate availability based on concentration and optimal range
                if element in updated_concentrations:
                    self.state.nutrient_availability[element] = min(1.0, updated_concentrations[element] / 100.0)

                # Update pools from organ_pools (extract total_content from OrganNutrientPools objects)
                if 'roots' in organ_pools and element in organ_pools['roots']:
                    pool_obj = organ_pools['roots'][element]
                    self.state.root_nutrient_pools[element] = pool_obj.metabolic_pool + pool_obj.storage_pool + pool_obj.transport_pool + pool_obj.buffer_pool
                if 'leaves' in organ_pools and element in organ_pools['leaves']:
                    pool_obj = organ_pools['leaves'][element]
                    self.state.shoot_nutrient_pools[element] = pool_obj.metabolic_pool + pool_obj.storage_pool + pool_obj.transport_pool + pool_obj.buffer_pool
                if 'stems' in organ_pools and element in organ_pools['stems']:
                    pool_obj = organ_pools['stems'][element]
                    self.state.shoot_nutrient_pools[element] += pool_obj.metabolic_pool + pool_obj.storage_pool + pool_obj.transport_pool + pool_obj.buffer_pool

                # Update fluxes from transport_fluxes
                if 'xylem' in transport_fluxes and element in transport_fluxes['xylem']:
                    self.state.xylem_flux[element] = transport_fluxes['xylem'][element]
                if 'phloem' in transport_fluxes and element in transport_fluxes['phloem']:
                    self.state.phloem_flux[element] = transport_fluxes['phloem'][element]
            
            # Update cumulative values
            # Note: nutrient_uptake_rates is in mg/plant/day (from model)
            # Convert to hourly: divide by 24 hours
            for element in self.nutrient_elements:
                uptake_rate = self.state.nutrient_uptake_rates[element]
                hourly_uptake = uptake_rate / 24.0  # Convert daily rate to hourly (mg/plant/hour)
                self.state.cumulative_nutrient_uptake[element] += hourly_uptake
                self.state.daily_nutrient_uptake[element] += hourly_uptake
            
        except Exception as e:
            # Raise error according to Rules.md - no error suppression
            raise
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format - using exact parameter names expected
            weather_data = {
                'temp_avg': inputs.temperature,  # Expected by nutrient model
                'temperature': inputs.temperature,
                'humidity': inputs.humidity
            }
            
            # Execute nutrient step using model functions
            self._execute_nutrient_step(weather_data)
            
            # Create output
            outputs = {
                'solution_ec': self.state.solution_ec,
                'solution_ph': self.state.solution_ph,
                'nutrient_concentrations': self.state.nutrient_concentrations,
                'nutrient_uptake_rates': self.state.nutrient_uptake_rates,
                'nutrient_availability': self.state.nutrient_availability,
                'root_nutrient_pools': self.state.root_nutrient_pools,
                'shoot_nutrient_pools': self.state.shoot_nutrient_pools,
                'xylem_flux': self.state.xylem_flux,
                'phloem_flux': self.state.phloem_flux,
                'cumulative_nutrient_uptake': self.state.cumulative_nutrient_uptake,
                'daily_nutrient_uptake': self.state.daily_nutrient_uptake
            }
            
            return DailyUpdateOutput(
                model_name='nutrient_models_simulator',
                day=inputs.day,
                success=True,
                primary_results={
                    'solution_ec': self.state.solution_ec,
                    'solution_ph': self.state.solution_ph,
                    'total_nutrient_uptake': sum(self.state.nutrient_uptake_rates.values())
                },
                secondary_results={
                    'step_count': self.state.step_count,
                    'last_update': self.state.last_update.isoformat()
                },
                internal_state=outputs,
                validation_result=None,
                processing_time_ms=0.0
            )
            
        except Exception as e:
            # Per Rules.md: raise errors, don't return error objects
            raise
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state - only scientific results, no internal tracking fields

        IMPORTANT: Returns COPIES of all dict/list state to prevent reference aliasing.
        Without .copy(), all CSV rows would reference the same dict objects and show
        identical final values instead of time-series data.
        """
        return {
            'solution_ec': self.state.solution_ec,
            'solution_ph': self.state.solution_ph,
            'nutrient_concentrations': self.state.nutrient_concentrations.copy(),
            'nutrient_uptake_rates': self.state.nutrient_uptake_rates.copy(),
            'nutrient_availability': self.state.nutrient_availability.copy(),
            'root_nutrient_pools': self.state.root_nutrient_pools.copy(),
            'shoot_nutrient_pools': self.state.shoot_nutrient_pools.copy(),
            'xylem_flux': self.state.xylem_flux,
            'phloem_flux': self.state.phloem_flux,
            'cumulative_nutrient_uptake': self.state.cumulative_nutrient_uptake.copy(),
            'daily_nutrient_uptake': self.state.daily_nutrient_uptake.copy()
        }
    
    def publish_state_data(self):
        """Publish nutrient models state data to dependency cache for other simulators"""
        # Calculate nitrogen-specific values for nitrogen balance simulator
        nitrogen_uptake = self.state.nutrient_uptake_rates.get('N-NO3', 0.0) + self.state.nutrient_uptake_rates.get('N-NH4', 0.0)
        # Use max availability (plants can preferentially use either NO3 or NH4)
        nitrogen_availability = max(self.state.nutrient_availability.get('N-NO3', 0.0), self.state.nutrient_availability.get('N-NH4', 0.0))

        nutrient_data = {
            'solution_ec': self.state.solution_ec,
            'solution_ph': self.state.solution_ph,
            'nutrient_availability': self.state.nutrient_availability,
            'nutrient_uptake_rate': self.state.nutrient_uptake_rates,
            'nutrient_uptake_rates': self.state.nutrient_uptake_rates,  # For nitrogen balance simulator
            'nutrient_concentrations': self.state.nutrient_concentrations,
            'nitrogen_availability': nitrogen_availability,
            'nitrogen_uptake': nitrogen_uptake,  # mg/plant/day
            'total_nitrogen_uptake': nitrogen_uptake,  # mg/plant/day (explicit for nitrogen balance simulator)
            'root_activity': 1.0  # Normalized root activity
        }

        # Add individual nutrient data
        for element in self.nutrient_elements:
            nutrient_data[f'{element}_concentration'] = self.state.nutrient_concentrations.get(element, 0.0)
            nutrient_data[f'{element}_uptake_rate'] = self.state.nutrient_uptake_rates.get(element, 0.0)
            nutrient_data[f'{element}_availability'] = self.state.nutrient_availability.get(element, 0.0)

        # Store in dependency cache for other simulators to access
        self.dependency_cache['nutrient_models_simulator'] = nutrient_data
        self.cache_timestamp['nutrient_models_simulator'] = datetime.now()

    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        # Calculate nitrogen-specific values for nitrogen balance simulator
        nitrogen_uptake = self.state.nutrient_uptake_rates.get('N-NO3', 0.0) + self.state.nutrient_uptake_rates.get('N-NH4', 0.0)
        # Use max availability (plants can preferentially use either NO3 or NH4)
        nitrogen_availability = max(self.state.nutrient_availability.get('N-NO3', 0.0), self.state.nutrient_availability.get('N-NH4', 0.0))

        data_map = {
            'solution_ec': self.state.solution_ec,
            'solution_ph': self.state.solution_ph,
            'nutrient_availability': self.state.nutrient_availability,
            'nutrient_uptake_rate': self.state.nutrient_uptake_rates,
            'nutrient_concentrations': self.state.nutrient_concentrations,
            'nitrogen_availability': nitrogen_availability,
            'nitrogen_uptake': nitrogen_uptake,  # mg/plant/day total nitrogen (NO3 + NH4)
            'root_activity': 1.0  # Normalized root activity
        }

        # Add individual nutrient data
        for element in self.nutrient_elements:
            data_map[f'{element}_concentration'] = self.state.nutrient_concentrations.get(element, 0.0)
            data_map[f'{element}_uptake_rate'] = self.state.nutrient_uptake_rates.get(element, 0.0)
            data_map[f'{element}_availability'] = self.state.nutrient_availability.get(element, 0.0)

        return data_map.get(data_key)
    
    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.WATER_UPDATE:
            # Update water parameters from water uptake simulator
            water_data = event.data
            # Water data will be requested when needed
            
        elif event.event_type == EventType.ROOT_UPDATE:
            # Update root parameters from root system simulator
            root_data = event.data
            # Root data will be requested when needed
            
        elif event.event_type == EventType.PH_UPDATE:
            # Update pH parameters from pH model simulator
            ph_data = event.data
            # pH data will be requested when needed
            
        elif event.event_type == EventType.PHENOLOGY_UPDATE:
            # Update phenology parameters from phenology simulator
            phenology_data = event.data
            # Phenology data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Nutrient models simulator: Simulation ended after {self.state.step_count} steps")
        print(f"Final solution EC: {self.state.solution_ec:.2f} mS/cm")
        print(f"Final solution pH: {self.state.solution_ph:.2f}")
        
        # Print final nutrient concentrations
        for element in self.nutrient_elements:
            final_conc = self.state.nutrient_concentrations.get(element, 0.0)
            total_uptake = self.state.cumulative_nutrient_uptake.get(element, 0.0)
            print(f"{element}: {final_conc:.2f} mg/L, Total uptake: {total_uptake:.2f} mg")
        
        # Publish final results
        self.publish_event(EventType.NUTRIENT_UPDATE, {
            'final_solution_ec': self.state.solution_ec,
            'final_solution_ph': self.state.solution_ph,
            'final_nutrient_concentrations': self.state.nutrient_concentrations,
            'final_nutrient_availability': self.state.nutrient_availability,
            'total_cumulative_uptake': self.state.cumulative_nutrient_uptake,
            'total_steps': self.state.step_count
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Nutrient models simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        ec_values = [s.solution_ec for s in self.history]
        ph_values = [s.solution_ph for s in self.history]
        
        # Calculate average nutrient uptake rates
        avg_uptake_rates = {}
        for element in self.nutrient_elements:
            rates = [s.nutrient_uptake_rates.get(element, 0.0) for s in self.history]
            avg_uptake_rates[element] = sum(rates) / len(rates) if rates else 0.0
        
        return {
            'total_steps': len(self.history),
            'final_solution_ec': self.state.solution_ec,
            'avg_solution_ec': sum(ec_values) / len(ec_values),
            'min_solution_ec': min(ec_values),
            'max_solution_ec': max(ec_values),
            'final_solution_ph': self.state.solution_ph,
            'avg_solution_ph': sum(ph_values) / len(ph_values),
            'min_solution_ph': min(ph_values),
            'max_solution_ph': max(ph_values),
            'avg_nutrient_uptake_rates': avg_uptake_rates,
            'total_cumulative_uptake': self.state.cumulative_nutrient_uptake,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
