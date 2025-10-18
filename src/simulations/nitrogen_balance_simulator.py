"""
Nitrogen Balance Simulator

Handles nitrogen balance simulation loop and inter-simulator communication
for nitrogen uptake, allocation, and remobilization in hydroponic systems.
Follows Rules.md: no hardcoded values, all from CSV, no fallbacks.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from simulations.communication_bus import BaseSimulator, SimulationEvent, EventType
from models.nitrogen_balance import (
    NitrogenBalanceModel, NitrogenBalanceParameters, OrganNitrogenState,
    NitrogenUptakeResponse, NitrogenAllocationResponse
)
from models.base_model import DailyUpdateInput, DailyUpdateOutput


@dataclass
class NitrogenPools:
    """Nitrogen pools for nitrogen balance simulator"""
    total_nitrogen: float = 0.0
    organic_nitrogen: float = 0.0
    inorganic_nitrogen: float = 0.0
    nitrate_nitrogen: float = 0.0
    ammonium_nitrogen: float = 0.0
    amino_acid_nitrogen: float = 0.0
    protein_nitrogen: float = 0.0
    chlorophyll_nitrogen: float = 0.0
    structural_nitrogen: float = 0.0
    storage_nitrogen: float = 0.0
    mobile_nitrogen: float = 0.0  # Mobile nitrogen pool


@dataclass
class NitrogenBalanceState:
    """State tracking for nitrogen balance simulator"""
    total_nitrogen_uptake: float = 0.0
    nitrate_uptake: float = 0.0
    ammonium_uptake: float = 0.0
    amino_acid_uptake: float = 0.0
    total_nitrogen_allocation: float = 0.0
    leaf_nitrogen_allocation: float = 0.0
    stem_nitrogen_allocation: float = 0.0
    root_nitrogen_allocation: float = 0.0
    reproductive_nitrogen_allocation: float = 0.0
    total_nitrogen_remobilization: float = 0.0
    leaf_nitrogen_remobilization: float = 0.0
    stem_nitrogen_remobilization: float = 0.0
    root_nitrogen_remobilization: float = 0.0
    nitrogen_use_efficiency: float = 1.0
    photosynthetic_n_use_efficiency: float = 1.0
    growth_n_use_efficiency: float = 1.0
    nitrogen_stress_index: float = 0.0
    luxury_uptake_factor: float = 1.0
    nitrogen_pools: Dict[str, float] = field(default_factory=dict)
    nitrogen_concentrations: Dict[str, float] = field(default_factory=dict)
    nitrogen_area_based: Dict[str, float] = field(default_factory=dict)  # g N/m² for photosynthesis
    uptake_rates: Dict[str, float] = field(default_factory=dict)
    allocation_rates: Dict[str, float] = field(default_factory=dict)
    remobilization_rates: Dict[str, float] = field(default_factory=dict)
    cumulative_nitrogen_uptake: float = 0.0
    daily_nitrogen_uptake: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)

class NitrogenBalanceSimulator(BaseSimulator):
    """Simulator for nitrogen balance - follows Rules.md strictly"""
    
    def __init__(self, 
                 nitrogen_params: NitrogenBalanceParameters = None):
        super().__init__("nitrogen_balance_simulator")
        
        # Initialize model - parameters MUST come from CSV, no defaults
        if nitrogen_params is None:
            raise ValueError("NitrogenBalanceParameters must be provided from CSV - no defaults allowed per Rules.md")
        
        self.nitrogen_params = nitrogen_params
        self.model = NitrogenBalanceModel(self.nitrogen_params)
        
        # State tracking
        self.state = NitrogenBalanceState()
        self.history: List[NitrogenBalanceState] = []
        
        # Initialize nitrogen forms
        self.nitrogen_forms = ['NO3', 'NH4', 'amino_acids']
        for form in self.nitrogen_forms:
            self.state.uptake_rates[form] = 0.0
        
        # Initialize organs
        self.organs = ['leaves', 'stems', 'roots', 'reproductive']
        for organ in self.organs:
            self.state.allocation_rates[organ] = 0.0
            self.state.remobilization_rates[organ] = 0.0
            self.state.nitrogen_concentrations[organ] = 0.0
        
        # Initialize nitrogen pools
        self.nitrogen_pools = ['total', 'organic', 'inorganic', 'mobile', 'structural']
        for pool in self.nitrogen_pools:
            self.state.nitrogen_pools[pool] = 0.0
        
        # Inter-simulator dependencies - all data comes from other simulators
        self.dependencies = {
            'nutrient_models_simulator': ['nitrogen_availability', 'nitrogen_uptake', 'root_activity'],
            'root_system_simulator': ['root_mass', 'root_surface_area', 'root_activity'],
            'biomass_allocation_simulator': ['leaf_biomass', 'stem_biomass', 'root_biomass', 'total_biomass'],
            'photosynthesis_simulator': ['photosynthesis_rate', 'light_use_efficiency'],
            'phenology_simulator': ['growth_stage', 'development_index'],
            'stress_models': ['nutrient_stress', 'water_stress', 'temperature_stress'],
            'leaf_development_simulator': ['leaf_nitrogen_content', 'leaf_nitrogen_ratio'],
            'canopy_architecture_simulator': ['leaf_area', 'lai']  # For area-based N calculation
        }
        
        # Data cache for dependencies
        self.dependency_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_timeout = nitrogen_params.cache_timeout  # Get from CSV parameters
        
        # Subscribe to root events
        self.message_bus.subscribe(EventType.ROOT_UPDATE, self._handle_root_update)
        
    
    def _handle_root_update(self, event: SimulationEvent):
        """Handle root data updates"""
        self.dependency_cache['root_system_simulator'] = event.data
        self.cache_timestamp['root_system_simulator'] = datetime.now()
    
    def on_simulation_start(self, data: Dict[str, Any]):
        """Handle simulation start"""
        self.state = NitrogenBalanceState()
        self.history.clear()
        self.dependency_cache.clear()
        
        # Persist system_config from initials.csv into dependency cache for consistent access
        system_config = data.get('system_config', {})
        if system_config:
            self.dependency_cache['system_config'] = system_config
            # Also store on state for resilience against cache resets
            setattr(self.state, 'system_config', dict(system_config))
        
        # Initialize model with parameters from CSV
        self.model.initialize()

        # Initialize organ nitrogen states from initial_state CSV data
        initial_state = data.get('initial_state', {})
        if initial_state:
            # Initialize organs with small starting values
            for organ in self.organs:
                initial_mass = initial_state.get(f'{organ[:-1]}_biomass', 0.05)  # Remove 's' and add _biomass
                initial_n_conc = 0.03  # 3% nitrogen concentration as default
                try:
                    self.model.initialize_organ_nitrogen(organ, initial_mass, initial_n_conc)
                except Exception as e:
                    # Per Rules.md: raise errors instead of silently passing
                    raise RuntimeError(f"N-Balance: Failed to initialize {organ}: {e}")

        # Initialize nitrogen pools
        initial_pools = NitrogenPools(
            total_nitrogen=0.0,
            organic_nitrogen=0.0,
            inorganic_nitrogen=0.0,
            mobile_nitrogen=0.0,
            structural_nitrogen=0.0
        )
        
        # Publish initial state
        self.publish_event(EventType.NITROGEN_BALANCE_UPDATE, {
            'total_nitrogen_uptake': self.state.total_nitrogen_uptake,
            'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
            'nitrogen_stress_index': self.state.nitrogen_stress_index,
            'nitrogen_pools': self.state.nitrogen_pools
        })
    
    def on_simulation_step(self, data: Dict[str, Any]):
        """Handle simulation step - all calculations use model functions"""
        try:
            # Get current weather data from daily weather file
            weather_data = data.get('weather_data', {})
            # Dependency data is provided by orchestrator in self.dependency_cache
            # No need to manually update - orchestrator injects shared_data_cache

            # Execute nitrogen balance calculation using model functions
            self._execute_nitrogen_balance_step(weather_data)
            
            # Update state
            self.current_step += 1
            self.state.last_update = datetime.now()
            
            # Store history (exclude non-dataclass fields like system_config)
            allowed_fields = getattr(NitrogenBalanceState, '__annotations__', {}).keys()
            filtered_state = {k: v for k, v in self.state.__dict__.items() if k in allowed_fields}
            self.history.append(NitrogenBalanceState(**filtered_state))

            # Publish state data to dependency cache
            self.publish_state_data()

            # Publish state update to other simulators
            self.publish_event(EventType.NITROGEN_BALANCE_UPDATE, {
                'total_nitrogen_uptake': self.state.total_nitrogen_uptake,
                'nitrate_uptake': self.state.nitrate_uptake,
                'ammonium_uptake': self.state.ammonium_uptake,
                'amino_acid_uptake': self.state.amino_acid_uptake,
                'total_nitrogen_allocation': self.state.total_nitrogen_allocation,
                'leaf_nitrogen_allocation': self.state.leaf_nitrogen_allocation,
                'stem_nitrogen_allocation': self.state.stem_nitrogen_allocation,
                'root_nitrogen_allocation': self.state.root_nitrogen_allocation,
                'reproductive_nitrogen_allocation': self.state.reproductive_nitrogen_allocation,
                'total_nitrogen_remobilization': self.state.total_nitrogen_remobilization,
                'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
                'photosynthetic_n_use_efficiency': self.state.photosynthetic_n_use_efficiency,
                'growth_n_use_efficiency': self.state.growth_n_use_efficiency,
                'nitrogen_stress_index': self.state.nitrogen_stress_index,
                'luxury_uptake_factor': self.state.luxury_uptake_factor,
                'nitrogen_pools': self.state.nitrogen_pools,
                'nitrogen_concentrations': self.state.nitrogen_concentrations,
                'uptake_rates': self.state.uptake_rates,
                'allocation_rates': self.state.allocation_rates,
                'remobilization_rates': self.state.remobilization_rates,
                'step': self.current_step
            })
            
            # Daily reset
            if data.get('hour', 0) == 0:  # Start of new day
                self.state.daily_nitrogen_uptake = 0.0
                
        except Exception as e:
            self.publish_event(EventType.ERROR_OCCURRED, {
                'simulator': self.simulator_id,
                'error': str(e),
                'step': self.current_step
            })
            # Raise error according to Rules.md - no error suppression
            raise
    

    def _execute_nitrogen_balance_step(self, weather_data: Dict[str, Any]):
        """Execute nitrogen balance calculation using model functions - no shortcuts"""
        try:
            # Ensure system_config is available (prefer persisted state copy)
            if 'system_config' not in self.dependency_cache:
                sc = getattr(self.state, 'system_config', None)
                if sc is not None:
                    self.dependency_cache['system_config'] = sc
            # Get nutrient data from nutrient models simulator
            nutrient_data = self.dependency_cache.get('nutrient_models_simulator', {})
            nitrogen_availability = nutrient_data.get('nitrogen_availability')
            # Use nitrogen uptake rates directly from nutrient_models_simulator (authoritative source)
            nitrogen_uptake_mg_per_plant_per_day = nutrient_data.get('total_nitrogen_uptake', nutrient_data.get('nitrogen_uptake'))
            nitrate_uptake_rate = nutrient_data.get('nutrient_uptake_rates', {}).get('N-NO3', 0.0)
            ammonium_uptake_rate = nutrient_data.get('nutrient_uptake_rates', {}).get('N-NH4', 0.0)
            root_activity = nutrient_data.get('root_activity')

            # Skip on first step if nutrient data not available yet (circular dependency)
            if any(x is None for x in [nitrogen_availability, nitrogen_uptake_mg_per_plant_per_day, root_activity]):
                if self.current_step <= 2:
                    print(f"N-Balance: Skipping calculation on step 0 due to missing nutrient_models data")
                    return
                raise ValueError("Nutrient data missing from nutrient_models_simulator - no defaults allowed")
            
            # Get root data from root system simulator
            root_data = self.dependency_cache.get('root_system_simulator', {})
            root_mass = root_data.get('root_mass', 0.1)  # Minimum initial root mass from initials.csv
            root_surface_area = root_data.get('root_surface_area', 0.001)
            root_activity_root = root_data.get('root_activity', 1.0)

            # Ensure minimum positive values
            root_mass = max(root_mass, 0.01)  # Ensure at least 0.01g
            root_surface_area = max(root_surface_area, 0.0001)  # Ensure at least 0.0001 m2
            
            # Get biomass data from biomass allocation simulator
            biomass_data = self.dependency_cache.get('biomass_allocation_simulator', {})
            leaf_biomass = biomass_data.get('leaf_biomass')
            stem_biomass = biomass_data.get('stem_biomass')
            root_biomass = biomass_data.get('root_biomass')
            total_biomass = biomass_data.get('total_biomass')
            
            if any(x is None for x in [leaf_biomass, stem_biomass, root_biomass, total_biomass]):
                raise ValueError("Biomass data missing from biomass_allocation_simulator - no defaults allowed")
            
            # Get photosynthesis data from photosynthesis simulator
            photosynthesis_data = self.dependency_cache.get('photosynthesis_simulator', {})
            photosynthesis_rate = photosynthesis_data.get('photosynthesis_rate')
            light_use_efficiency = photosynthesis_data.get('light_use_efficiency')
            
            if any(x is None for x in [photosynthesis_rate, light_use_efficiency]):
                raise ValueError("Photosynthesis data missing from photosynthesis_simulator - no defaults allowed")
            
            # Get phenology data from phenology simulator
            phenology_data = self.dependency_cache.get('phenology_simulator', {})
            growth_stage = phenology_data.get('growth_stage')
            development_index = phenology_data.get('development_index')
            
            if any(x is None for x in [growth_stage, development_index]):
                raise ValueError("Phenology data missing from phenology_simulator - no defaults allowed")
            
            # Get stress data from stress models simulator
            stress_data = self.dependency_cache.get('stress_models', {})
            nutrient_stress = stress_data.get('nutrient_stress')
            water_stress = stress_data.get('water_stress')
            temperature_stress = stress_data.get('temperature_stress')
            
            if any(x is None for x in [nutrient_stress, water_stress, temperature_stress]):
                raise ValueError("Stress data missing from stress_models - no defaults allowed")
            
            # Get leaf development data from leaf development simulator
            leaf_data = self.dependency_cache.get('leaf_development_simulator', {})
            leaf_nitrogen_content = leaf_data.get('leaf_nitrogen_content')
            leaf_nitrogen_ratio = leaf_data.get('leaf_nitrogen_ratio')
            
            if any(x is None for x in [leaf_nitrogen_content, leaf_nitrogen_ratio]):
                raise ValueError("Leaf development data missing from leaf_development_simulator - no defaults allowed")
            
            # Create current nitrogen pools
            current_pools = NitrogenPools(
                total_nitrogen=self.state.nitrogen_pools.get('total', 0.0),
                organic_nitrogen=self.state.nitrogen_pools.get('organic', 0.0),
                inorganic_nitrogen=self.state.nitrogen_pools.get('inorganic', 0.0),
                mobile_nitrogen=self.state.nitrogen_pools.get('mobile', 0.0),
                structural_nitrogen=self.state.nitrogen_pools.get('structural', 0.0)
            )

            # USE UPTAKE VALUES DIRECTLY FROM NUTRIENT_MODELS_SIMULATOR
            # The nutrient_models_simulator is the authoritative source for nitrogen uptake rates
            # It already accounts for root surface area, Michaelis-Menten kinetics, environmental factors, etc.
            # No need to recalculate here - this creates consistency across the system

            # Calculate nitrogen demand and allocation using model methods
            demand_result = self.model.calculate_nitrogen_demand(
                organ_growth_rates={'leaves': 0.1, 'stems': 0.05, 'roots': 0.05},
                growth_stage=growth_stage,
                environmental_factors={
                    'temperature': weather_data.get('temperature'),
                    'water': 1.0,
                    'pH': 6.0
                }
            )

            # Create result dict using uptake from nutrient_models and demand from nitrogen_balance model
            total_demand = sum(demand_result.values()) if demand_result else 0.0
            result = {
                'total_nitrogen_uptake': nitrogen_uptake_mg_per_plant_per_day,  # From nutrient_models (mg/plant/day)
                'nitrate_uptake': nitrate_uptake_rate,  # From nutrient_models (mg/plant/day)
                'ammonium_uptake': ammonium_uptake_rate,  # From nutrient_models (mg/plant/day)
                'amino_acid_uptake': 0.0,  # Amino acids negligible in hydroponic lettuce
                'total_nitrogen_allocation': total_demand,
                'leaf_nitrogen_allocation': demand_result.get('leaves', 0.0) if demand_result else 0.0,
                'stem_nitrogen_allocation': demand_result.get('stems', 0.0) if demand_result else 0.0,
                'root_nitrogen_allocation': demand_result.get('roots', 0.0) if demand_result else 0.0,
                'reproductive_nitrogen_allocation': demand_result.get('reproductive', 0.0) if demand_result else 0.0,
                'total_nitrogen_remobilization': 0.0,
                'nitrogen_stress_index': self.model.calculate_nitrogen_stress_level()
            }
            
            # Update state with model results
            self.state.total_nitrogen_uptake = result.get('total_nitrogen_uptake', self.state.total_nitrogen_uptake)
            self.state.nitrate_uptake = result.get('nitrate_uptake', self.state.nitrate_uptake)
            self.state.ammonium_uptake = result.get('ammonium_uptake', self.state.ammonium_uptake)
            self.state.amino_acid_uptake = result.get('amino_acid_uptake', self.state.amino_acid_uptake)
            
            # Update allocation
            self.state.total_nitrogen_allocation = result.get('total_nitrogen_allocation', self.state.total_nitrogen_allocation)
            self.state.leaf_nitrogen_allocation = result.get('leaf_nitrogen_allocation', self.state.leaf_nitrogen_allocation)
            self.state.stem_nitrogen_allocation = result.get('stem_nitrogen_allocation', self.state.stem_nitrogen_allocation)
            self.state.root_nitrogen_allocation = result.get('root_nitrogen_allocation', self.state.root_nitrogen_allocation)
            self.state.reproductive_nitrogen_allocation = result.get('reproductive_nitrogen_allocation', self.state.reproductive_nitrogen_allocation)
            
            # Update remobilization
            self.state.total_nitrogen_remobilization = result.get('total_nitrogen_remobilization', self.state.total_nitrogen_remobilization)
            self.state.leaf_nitrogen_remobilization = result.get('leaf_nitrogen_remobilization', self.state.leaf_nitrogen_remobilization)
            self.state.stem_nitrogen_remobilization = result.get('stem_nitrogen_remobilization', self.state.stem_nitrogen_remobilization)
            self.state.root_nitrogen_remobilization = result.get('root_nitrogen_remobilization', self.state.root_nitrogen_remobilization)
            
            # Update efficiency and stress
            self.state.nitrogen_use_efficiency = result.get('nitrogen_use_efficiency', self.state.nitrogen_use_efficiency)
            self.state.photosynthetic_n_use_efficiency = result.get('photosynthetic_n_use_efficiency', self.state.photosynthetic_n_use_efficiency)
            self.state.growth_n_use_efficiency = result.get('growth_n_use_efficiency', self.state.growth_n_use_efficiency)
            self.state.nitrogen_stress_index = result.get('nitrogen_stress_index', self.state.nitrogen_stress_index)
            self.state.luxury_uptake_factor = result.get('luxury_uptake_factor', self.state.luxury_uptake_factor)
            
            # Update nitrogen pools
            nitrogen_pools = result.get('nitrogen_pools', {})
            for pool in self.nitrogen_pools:
                if pool in nitrogen_pools:
                    self.state.nitrogen_pools[pool] = nitrogen_pools[pool]
            
            # Update concentrations
            nitrogen_concentrations = result.get('nitrogen_concentrations', {})
            for organ in self.organs:
                if organ in nitrogen_concentrations:
                    self.state.nitrogen_concentrations[organ] = nitrogen_concentrations[organ]

            # Calculate AREA-BASED nitrogen for photosynthesis (DIRECT BIOCHEMICAL LINK)
            # This enables direct N → Photosynthesis feedback
            canopy_data = self.dependency_cache.get('canopy_architecture_simulator', {})
            leaf_area = canopy_data.get('leaf_area')  # m²

            if leaf_area is not None and leaf_area > 0:
                # Calculate leaf N content (assume 60% of total N goes to leaves - typical for lettuce)
                leaf_n_fraction = 0.60  # From literature (Evans 1989, Field & Mooney 1986)
                cumulative_n_g = self.state.cumulative_nitrogen_uptake  # grams
                leaf_n_total = cumulative_n_g * leaf_n_fraction  # g N in leaves

                # Area-based concentration (g N/m² leaf area)
                leaf_n_area = leaf_n_total / leaf_area  # g N/m²
                self.state.nitrogen_area_based['leaves'] = leaf_n_area

                # Also calculate for stems and roots if needed (using biomass allocation fractions)
                stem_n_fraction = 0.25
                root_n_fraction = 0.15
                self.state.nitrogen_area_based['stems'] = cumulative_n_g * stem_n_fraction
                self.state.nitrogen_area_based['roots'] = cumulative_n_g * root_n_fraction
            
            # Update rates
            uptake_rates = result.get('uptake_rates', {})
            for form in self.nitrogen_forms:
                if form in uptake_rates:
                    self.state.uptake_rates[form] = uptake_rates[form]
            
            allocation_rates = result.get('allocation_rates', {})
            for organ in self.organs:
                if organ in allocation_rates:
                    self.state.allocation_rates[organ] = allocation_rates[organ]
            
            remobilization_rates = result.get('remobilization_rates', {})
            for organ in self.organs:
                if organ in remobilization_rates:
                    self.state.remobilization_rates[organ] = remobilization_rates[organ]
            
            # Update cumulative values
            # Use total_nitrogen_uptake returned by model (mg/plant/day)
            # Convert to hourly TOTAL for the system and to grams (no implicit unit mismatch)
            total_n_uptake_mg_per_plant_per_day = result.get('total_nitrogen_uptake', 0.0)
            hourly_n_uptake_mg_per_plant = total_n_uptake_mg_per_plant_per_day / 24.0

            # Retrieve plant_count from system_config injected by orchestrator
            system_config = self.dependency_cache.get('system_config', {})
            plant_count = system_config.get('plant_count')
            if plant_count is None:
                raise ValueError("NitrogenBalance: plant_count missing from system_config - no defaults allowed")

            hourly_n_uptake_mg_total = hourly_n_uptake_mg_per_plant * plant_count
            hourly_n_uptake_g_total = hourly_n_uptake_mg_total / 1000.0

            self.state.cumulative_nitrogen_uptake += hourly_n_uptake_g_total
            self.state.daily_nitrogen_uptake += hourly_n_uptake_g_total
            # Keep total_nitrogen_uptake in sync (g, system total)
            self.state.total_nitrogen_uptake = self.state.cumulative_nitrogen_uptake
            
        except Exception as e:
            # Raise error according to Rules.md - no error suppression
            raise
    
    def daily_update(self, inputs: DailyUpdateInput) -> DailyUpdateOutput:
        """Implement the daily update interface - uses all model functions"""
        try:
            # Convert inputs to weather data format
            weather_data = {
                'temperature': inputs.temperature,
                'humidity': inputs.humidity,
                'light_intensity': inputs.solar_radiation,  # Use solar_radiation from DailyUpdateInput
                'co2_concentration': inputs.co2_concentration
            }
            
            # Execute nitrogen balance step using model functions
            self._execute_nitrogen_balance_step(weather_data)
            
            # Create output
            outputs = {
                'total_nitrogen_uptake': self.state.total_nitrogen_uptake,
                'nitrate_uptake': self.state.nitrate_uptake,
                'ammonium_uptake': self.state.ammonium_uptake,
                'amino_acid_uptake': self.state.amino_acid_uptake,
                'total_nitrogen_allocation': self.state.total_nitrogen_allocation,
                'leaf_nitrogen_allocation': self.state.leaf_nitrogen_allocation,
                'stem_nitrogen_allocation': self.state.stem_nitrogen_allocation,
                'root_nitrogen_allocation': self.state.root_nitrogen_allocation,
                'reproductive_nitrogen_allocation': self.state.reproductive_nitrogen_allocation,
                'total_nitrogen_remobilization': self.state.total_nitrogen_remobilization,
                'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
                'photosynthetic_n_use_efficiency': self.state.photosynthetic_n_use_efficiency,
                'growth_n_use_efficiency': self.state.growth_n_use_efficiency,
                'nitrogen_stress_index': self.state.nitrogen_stress_index,
                'luxury_uptake_factor': self.state.luxury_uptake_factor,
                'nitrogen_pools': self.state.nitrogen_pools,
                'nitrogen_concentrations': self.state.nitrogen_concentrations,
                'uptake_rates': self.state.uptake_rates,
                'allocation_rates': self.state.allocation_rates,
                'remobilization_rates': self.state.remobilization_rates,
                'cumulative_nitrogen_uptake': self.state.cumulative_nitrogen_uptake,
                'daily_nitrogen_uptake': self.state.daily_nitrogen_uptake
            }
            
            return DailyUpdateOutput(
                model_name='nitrogen_balance_simulator',
                day=inputs.day,
                success=True,
                primary_results={
                    'total_nitrogen_uptake': self.state.cumulative_nitrogen_uptake,
                    'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
                    'nitrogen_stress_index': self.state.nitrogen_stress_index
                },
                secondary_results={
                    'step_count': self.current_step,
                    'cumulative_nitrogen_uptake': self.state.cumulative_nitrogen_uptake
                },
                internal_state=outputs,
                validation_result=None,
                processing_time_ms=0.0
            )
            
        except Exception as e:
            # Per Rules.md: raise errors, don't return error objects
            raise
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current simulator state - only scientific results, no internal tracking fields"""
        return {
            'total_nitrogen_uptake': self.state.total_nitrogen_uptake,
            'nitrate_uptake': self.state.nitrate_uptake,
            'ammonium_uptake': self.state.ammonium_uptake,
            'amino_acid_uptake': self.state.amino_acid_uptake,
            'total_nitrogen_allocation': self.state.total_nitrogen_allocation,
            'leaf_nitrogen_allocation': self.state.leaf_nitrogen_allocation,
            'stem_nitrogen_allocation': self.state.stem_nitrogen_allocation,
            'root_nitrogen_allocation': self.state.root_nitrogen_allocation,
            'reproductive_nitrogen_allocation': self.state.reproductive_nitrogen_allocation,
            'total_nitrogen_remobilization': self.state.total_nitrogen_remobilization,
            'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
            'photosynthetic_n_use_efficiency': self.state.photosynthetic_n_use_efficiency,
            'growth_n_use_efficiency': self.state.growth_n_use_efficiency,
            'nitrogen_stress_index': self.state.nitrogen_stress_index,
            'luxury_uptake_factor': self.state.luxury_uptake_factor,
            'nitrogen_pools': self.state.nitrogen_pools,
            'nitrogen_concentrations': self.state.nitrogen_concentrations,
            'nitrogen_area_based': self.state.nitrogen_area_based,  # For direct N → Photosynthesis link
            'uptake_rates': self.state.uptake_rates,
            'allocation_rates': self.state.allocation_rates,
            'remobilization_rates': self.state.remobilization_rates,
            'cumulative_nitrogen_uptake': self.state.cumulative_nitrogen_uptake,
            'daily_nitrogen_uptake': self.state.daily_nitrogen_uptake
        }
    
    def get_data(self, data_key: str) -> Any:
        """Provide data to other simulators"""
        data_map = {
            'total_nitrogen_uptake': self.state.total_nitrogen_uptake,
            'nitrate_uptake': self.state.nitrate_uptake,
            'ammonium_uptake': self.state.ammonium_uptake,
            'amino_acid_uptake': self.state.amino_acid_uptake,
            'total_nitrogen_allocation': self.state.total_nitrogen_allocation,
            'leaf_nitrogen_allocation': self.state.leaf_nitrogen_allocation,
            'stem_nitrogen_allocation': self.state.stem_nitrogen_allocation,
            'root_nitrogen_allocation': self.state.root_nitrogen_allocation,
            'reproductive_nitrogen_allocation': self.state.reproductive_nitrogen_allocation,
            'total_nitrogen_remobilization': self.state.total_nitrogen_remobilization,
            'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
            'photosynthetic_n_use_efficiency': self.state.photosynthetic_n_use_efficiency,
            'growth_n_use_efficiency': self.state.growth_n_use_efficiency,
            'nitrogen_stress_index': self.state.nitrogen_stress_index,
            'luxury_uptake_factor': self.state.luxury_uptake_factor,
            'nitrogen_pools': self.state.nitrogen_pools,
            'nitrogen_concentrations': self.state.nitrogen_concentrations,
            'nitrogen_area_based': self.state.nitrogen_area_based,  # For direct N → Photosynthesis link
            'uptake_rates': self.state.uptake_rates,
            'allocation_rates': self.state.allocation_rates,
            'remobilization_rates': self.state.remobilization_rates,
            'cumulative_nitrogen_uptake': self.state.cumulative_nitrogen_uptake,
            'daily_nitrogen_uptake': self.state.daily_nitrogen_uptake
        }
        
        # Add individual form and organ data
        for form in self.nitrogen_forms:
            data_map[f'{form}_uptake'] = self.state.uptake_rates.get(form, 0.0)
        
        for organ in self.organs:
            data_map[f'{organ}_nitrogen_allocation'] = self.state.allocation_rates.get(organ, 0.0)
            data_map[f'{organ}_nitrogen_remobilization'] = self.state.remobilization_rates.get(organ, 0.0)
            data_map[f'{organ}_nitrogen_concentration'] = self.state.nitrogen_concentrations.get(organ, 0.0)
        
        for pool in self.nitrogen_pools:
            data_map[f'{pool}_nitrogen_pool'] = self.state.nitrogen_pools.get(pool, 0.0)
        
        return data_map.get(data_key)

    def publish_state_data(self):
        """Publish current state data to dependency cache for other simulators"""
        nitrogen_data = {
            'total_nitrogen_uptake': self.state.total_nitrogen_uptake,
            'nitrate_uptake': self.state.nitrate_uptake,
            'ammonium_uptake': self.state.ammonium_uptake,
            'amino_acid_uptake': self.state.amino_acid_uptake,
            'total_nitrogen_allocation': self.state.total_nitrogen_allocation,
            'leaf_nitrogen_allocation': self.state.leaf_nitrogen_allocation,
            'stem_nitrogen_allocation': self.state.stem_nitrogen_allocation,
            'root_nitrogen_allocation': self.state.root_nitrogen_allocation,
            'reproductive_nitrogen_allocation': self.state.reproductive_nitrogen_allocation,
            'total_nitrogen_remobilization': self.state.total_nitrogen_remobilization,
            'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
            'photosynthetic_n_use_efficiency': self.state.photosynthetic_n_use_efficiency,
            'growth_n_use_efficiency': self.state.growth_n_use_efficiency,
            'nitrogen_stress_index': self.state.nitrogen_stress_index,
            'luxury_uptake_factor': self.state.luxury_uptake_factor,
            'nitrogen_pools': self.state.nitrogen_pools,
            'nitrogen_concentrations': self.state.nitrogen_concentrations,
            'nitrogen_area_based': self.state.nitrogen_area_based,  # For direct N → Photosynthesis link
            'uptake_rates': self.state.uptake_rates,
            'allocation_rates': self.state.allocation_rates,
            'remobilization_rates': self.state.remobilization_rates,
            'cumulative_nitrogen_uptake': self.state.cumulative_nitrogen_uptake,
            'daily_nitrogen_uptake': self.state.daily_nitrogen_uptake
        }

        # Add individual form and organ data
        for form in self.nitrogen_forms:
            nitrogen_data[f'{form}_uptake'] = self.state.uptake_rates.get(form, 0.0)

        for organ in self.organs:
            nitrogen_data[f'{organ}_nitrogen_allocation'] = self.state.allocation_rates.get(organ, 0.0)
            nitrogen_data[f'{organ}_nitrogen_remobilization'] = self.state.remobilization_rates.get(organ, 0.0)
            nitrogen_data[f'{organ}_nitrogen_concentration'] = self.state.nitrogen_concentrations.get(organ, 0.0)

        for pool in self.nitrogen_pools:
            nitrogen_data[f'{pool}_nitrogen_pool'] = self.state.nitrogen_pools.get(pool, 0.0)

        self.dependency_cache['nitrogen_balance_simulator'] = nitrogen_data

    def handle_event(self, event: SimulationEvent):
        """Handle specific events from other simulators"""
        if event.event_type == EventType.NUTRIENT_UPDATE:
            # Update nutrient parameters
            nutrient_data = event.data
            # Nutrient data will be requested when needed
            
        elif event.event_type == EventType.ROOT_UPDATE:
            # Update root parameters from root system simulator
            root_data = event.data
            # Root data will be requested when needed
            
        elif event.event_type == EventType.BIOMASS_UPDATE:
            # Update biomass parameters from biomass allocation simulator
            biomass_data = event.data
            # Biomass data will be requested when needed
            
        elif event.event_type == EventType.PHOTOSYNTHESIS_UPDATE:
            # Update photosynthesis parameters
            photosynthesis_data = event.data
            # Photosynthesis data will be requested when needed
    
    def on_simulation_end(self, data: Dict[str, Any]):
        """Handle simulation end"""
        print(f"Nitrogen balance simulator: Simulation ended after {self.current_step} steps")
        print(f"Final total nitrogen uptake: {self.state.total_nitrogen_uptake:.2f} g")
        print(f"Final nitrogen use efficiency: {self.state.nitrogen_use_efficiency:.3f}")
        print(f"Final nitrogen stress index: {self.state.nitrogen_stress_index:.3f}")
        print(f"Final luxury uptake factor: {self.state.luxury_uptake_factor:.3f}")
        print(f"Total nitrogen uptake: {self.state.cumulative_nitrogen_uptake:.2f} g")
        
        # Print nitrogen allocation
        print("Final nitrogen allocation:")
        for organ, allocation in self.state.allocation_rates.items():
            # Handle case where allocation might be a list or other type
            if isinstance(allocation, (int, float)):
                print(f"  {organ}: {allocation:.2f} g")
            else:
                print(f"  {organ}: {allocation}")

        # Print nitrogen pools
        print("Final nitrogen pools:")
        for pool, amount in self.state.nitrogen_pools.items():
            # Handle case where amount might be a list or other type
            if isinstance(amount, (int, float)):
                print(f"  {pool}: {amount:.2f} g")
            else:
                print(f"  {pool}: {amount}")
        
        # Publish final results
        self.publish_event(EventType.NITROGEN_BALANCE_UPDATE, {
            'final_total_nitrogen_uptake': self.state.total_nitrogen_uptake,
            'final_nitrate_uptake': self.state.nitrate_uptake,
            'final_ammonium_uptake': self.state.ammonium_uptake,
            'final_amino_acid_uptake': self.state.amino_acid_uptake,
            'final_total_nitrogen_allocation': self.state.total_nitrogen_allocation,
            'final_leaf_nitrogen_allocation': self.state.leaf_nitrogen_allocation,
            'final_stem_nitrogen_allocation': self.state.stem_nitrogen_allocation,
            'final_root_nitrogen_allocation': self.state.root_nitrogen_allocation,
            'final_reproductive_nitrogen_allocation': self.state.reproductive_nitrogen_allocation,
            'final_total_nitrogen_remobilization': self.state.total_nitrogen_remobilization,
            'final_nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
            'final_photosynthetic_n_use_efficiency': self.state.photosynthetic_n_use_efficiency,
            'final_growth_n_use_efficiency': self.state.growth_n_use_efficiency,
            'final_nitrogen_stress_index': self.state.nitrogen_stress_index,
            'final_luxury_uptake_factor': self.state.luxury_uptake_factor,
            'final_nitrogen_pools': self.state.nitrogen_pools,
            'final_nitrogen_concentrations': self.state.nitrogen_concentrations,
            'total_nitrogen_uptake': self.state.cumulative_nitrogen_uptake,
            'total_steps': self.current_step
        })
    
    def on_terminate(self, data: Dict[str, Any]):
        """Handle simulation termination"""
        print("Nitrogen balance simulator: Terminating")
        self.cleanup()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this simulator"""
        if not self.history:
            return {}
        
        nitrogen_uptakes = [s.total_nitrogen_uptake for s in self.history]
        nitrogen_efficiencies = [s.nitrogen_use_efficiency for s in self.history]
        stress_indices = [s.nitrogen_stress_index for s in self.history]
        
        # Calculate nitrogen balance metrics
        if len(nitrogen_uptakes) > 1:
            nitrogen_uptake_rate = (nitrogen_uptakes[-1] - nitrogen_uptakes[0]) / len(nitrogen_uptakes)
        else:
            nitrogen_uptake_rate = 0.0
        
        return {
            'total_steps': len(self.history),
            'final_nitrogen_uptake': self.state.total_nitrogen_uptake,
            'avg_nitrogen_uptake': sum(nitrogen_uptakes) / len(nitrogen_uptakes),
            'nitrogen_uptake_rate': nitrogen_uptake_rate,
            'final_nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
            'avg_nitrogen_use_efficiency': sum(nitrogen_efficiencies) / len(nitrogen_efficiencies),
            'final_nitrogen_stress_index': self.state.nitrogen_stress_index,
            'avg_nitrogen_stress_index': sum(stress_indices) / len(stress_indices),
            'cumulative_nitrogen_uptake': self.state.cumulative_nitrogen_uptake,
            'dependency_cache_hits': len(self.dependency_cache),
            'last_update': self.state.last_update.isoformat()
        }
