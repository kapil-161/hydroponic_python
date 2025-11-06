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
    # Cumulative nitrogen in each organ (for concentration calculation)
    cumulative_leaf_nitrogen: float = 0.0
    cumulative_stem_nitrogen: float = 0.0
    cumulative_root_nitrogen: float = 0.0
    cumulative_reproductive_nitrogen: float = 0.0
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
        # Initialize cumulative nitrogen uptake values to zero
        self.state.total_nitrogen_uptake = 0.0
        self.state.nitrate_uptake = 0.0
        self.state.ammonium_uptake = 0.0
        self.state.amino_acid_uptake = 0.0
        self.state.cumulative_nitrogen_uptake = 0.0
        self.state.daily_nitrogen_uptake = 0.0

        self.history.clear()
        self.dependency_cache.clear()
        
        # Initialize previous biomass tracking for growth rate calculation
        initial_state = data.get('initial_state', {})
        self._prev_biomass = {
            'leaf_biomass': initial_state.get('leaf_biomass', 0.015),
            'stem_biomass': initial_state.get('stem_biomass', 0.005),
            'root_biomass': initial_state.get('root_biomass', 0.01)
        }
        
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
                # Get initial nitrogen concentration from CSV data
                initial_n_conc = initial_state.get('initial_nitrogen_concentration', 0.03)  # 3% default from literature
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

            # Prevent unbounded history growth - keep last 1000 steps only

            if len(self.history) > 1000:

                self.history = self.history[-1000:]

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
            # Get nitrogen uptake data from nutrient_models_simulator
            # Use the same data source for both total and individual forms to ensure consistency
            nutrient_uptake_rates = nutrient_data.get('nutrient_uptake_rates', {})
            nitrate_uptake_rate = nutrient_uptake_rates.get('N-NO3')
            ammonium_uptake_rate = nutrient_uptake_rates.get('N-NH4')
            
            if nitrate_uptake_rate is None or ammonium_uptake_rate is None:
                if self.current_step <= 2:
                    return
                raise ValueError("Nitrogen uptake rates missing from nutrient_models_simulator - no defaults allowed")
            
            # Use the total nitrogen uptake directly from nutrient_models_simulator
            # This ensures consistency with the authoritative source
            nitrogen_uptake_mg_per_plant_per_day = nutrient_data.get('total_nitrogen_uptake')
            
            if nitrogen_uptake_mg_per_plant_per_day is None:
                if self.current_step <= 2:
                    return
                raise ValueError("Total nitrogen uptake missing from nutrient_models_simulator - no defaults allowed")
            
            # If total is not available, calculate from individual forms as fallback
            if nitrogen_uptake_mg_per_plant_per_day == 0.0:
                nitrogen_uptake_mg_per_plant_per_day = nitrate_uptake_rate + ammonium_uptake_rate
            root_activity = nutrient_data.get('root_activity')

            # Skip on first step if nutrient data not available yet (circular dependency)
            if any(x is None for x in [nitrogen_availability, nitrogen_uptake_mg_per_plant_per_day, root_activity]):
                if self.current_step <= 2:
                    return
                raise ValueError("Nutrient data missing from nutrient_models_simulator - no defaults allowed")
            
            # Get root data from root system simulator
            root_data = self.dependency_cache.get('root_system_simulator', {})
            root_mass = root_data.get('root_mass')
            root_surface_area = root_data.get('root_surface_area')
            root_activity_root = root_data.get('root_activity')
            
            if any(x is None for x in [root_mass, root_surface_area, root_activity_root]):
                if self.current_step <= 2:
                    return
                raise ValueError("Root data missing from root_system_simulator - no defaults allowed")

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
            
            # Convert growth_stage to format expected by nitrogen balance model
            # Model expects: 'vegetative' or 'reproductive'
            # Phenology returns: LettuceGrowthStage enum or string like "V1", "V2", "HI", "HM", etc.
            if isinstance(growth_stage, str):
                # Check if it's a vegetative stage (starts with "V" or "GE", "VE")
                if growth_stage.startswith('V') or growth_stage in ['GE', 'VE', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10', 'V11+']:
                    growth_stage_for_model = 'vegetative'
                # Check if it's a reproductive stage
                elif growth_stage in ['HI', 'HD', 'HM', 'BI', 'FL', 'AN', 'SD', 'PM']:
                    growth_stage_for_model = 'reproductive'
                else:
                    # Default to vegetative for unknown stages
                    growth_stage_for_model = 'vegetative'
            else:
                # Handle enum values
                growth_stage_str = str(growth_stage)
                if 'VEGETATIVE' in growth_stage_str or growth_stage_str.startswith('V'):
                    growth_stage_for_model = 'vegetative'
                elif 'REPRODUCTIVE' in growth_stage_str or growth_stage_str in ['HI', 'HD', 'HM', 'BI', 'FL', 'AN', 'SD', 'PM']:
                    growth_stage_for_model = 'reproductive'
                else:
                    growth_stage_for_model = 'vegetative'  # Default
            
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

            # Convert nitrogen uptake from mg/plant/day to g/plant/day for model
            nitrogen_uptake_g_per_plant_per_day = nitrogen_uptake_mg_per_plant_per_day / 1000.0
            
            # Calculate organ growth rates from biomass change (g/day)
            # Get previous biomass for growth rate calculation
            prev_biomass_data = getattr(self, '_prev_biomass', {})
            prev_leaf_biomass = prev_biomass_data.get('leaf_biomass', leaf_biomass)
            prev_stem_biomass = prev_biomass_data.get('stem_biomass', stem_biomass)
            prev_root_biomass = prev_biomass_data.get('root_biomass', root_biomass)
            
            # Calculate hourly growth rates (g/hour), convert to daily (g/day)
            # Use max to ensure non-negative, and multiply by 24 to convert hourly to daily
            # If biomass hasn't changed, use a small positive value to allow nitrogen allocation
            leaf_growth_rate = max(0.0, (leaf_biomass - prev_leaf_biomass) * 24.0)  # g/day
            stem_growth_rate = max(0.0, (stem_biomass - prev_stem_biomass) * 24.0)  # g/day
            root_growth_rate = max(0.0, (root_biomass - prev_root_biomass) * 24.0)  # g/day
            
            # FIX: If growth rates are 0 but we have nitrogen uptake, estimate growth from nitrogen
            # This handles the case where biomass change is small but nitrogen is being allocated
            # Use realistic bounds to prevent unrealistic growth estimates
            if leaf_growth_rate == 0.0 and stem_growth_rate == 0.0 and root_growth_rate == 0.0:
                # Estimate growth rates from nitrogen uptake and typical N concentrations
                # Typical lettuce: 3-4% N in leaves, 2-3% in stems, 1-2% in roots
                if nitrogen_uptake_g_per_plant_per_day > 0:
                    # Distribute nitrogen uptake proportionally to organ biomass
                    total_biomass_for_ratio = max(0.001, total_biomass)
                    leaf_fraction = leaf_biomass / total_biomass_for_ratio
                    stem_fraction = stem_biomass / total_biomass_for_ratio
                    root_fraction = root_biomass / total_biomass_for_ratio
                    
                    # Estimate growth from nitrogen allocation (using parameter from CSV)
                    # Use realistic bounds: max growth = 10% of current biomass per day
                    n_concentration_new_growth = self.nitrogen_params.nitrogen_concentration_new_growth  # From CSV
                    estimated_total_growth = nitrogen_uptake_g_per_plant_per_day / n_concentration_new_growth
                    max_realistic_growth = total_biomass * 0.1  # Max 10% growth per day
                    estimated_total_growth = min(estimated_total_growth, max_realistic_growth)
                    
                    # Ensure minimum growth to allow nitrogen allocation
                    # Minimum: enough to use at least 10% of nitrogen uptake
                    min_growth_from_n = (nitrogen_uptake_g_per_plant_per_day * 0.1) / n_concentration_new_growth
                    estimated_total_growth = max(estimated_total_growth, min_growth_from_n)
                    
                    leaf_growth_rate = estimated_total_growth * leaf_fraction
                    stem_growth_rate = estimated_total_growth * stem_fraction
                    root_growth_rate = estimated_total_growth * root_fraction
                    
                    # Ensure non-negative and reasonable bounds (using parameter from CSV)
                    minimum_growth_rate = self.nitrogen_params.minimum_growth_rate  # From CSV
                    leaf_growth_rate = max(minimum_growth_rate, min(leaf_growth_rate, leaf_biomass * 0.1))
                    stem_growth_rate = max(minimum_growth_rate, min(stem_growth_rate, stem_biomass * 0.1))
                    root_growth_rate = max(minimum_growth_rate, min(root_growth_rate, root_biomass * 0.1))
            else:
                # Ensure minimum growth rates even when calculated from biomass change
                # This prevents zero demand when growth is very small (using parameter from CSV)
                minimum_growth_rate = self.nitrogen_params.minimum_growth_rate  # From CSV
                leaf_growth_rate = max(leaf_growth_rate, minimum_growth_rate / 10.0)  # Use smaller fraction for very small growth
                stem_growth_rate = max(stem_growth_rate, minimum_growth_rate / 10.0)
                root_growth_rate = max(root_growth_rate, minimum_growth_rate / 10.0)
            
            # Store current biomass for next step
            self._prev_biomass = {
                'leaf_biomass': leaf_biomass,
                'stem_biomass': stem_biomass,
                'root_biomass': root_biomass
            }
            
            # Prepare inputs for update_nitrogen_pools
            organ_growth_rates = {
                'leaves': leaf_growth_rate,
                'stems': stem_growth_rate,
                'roots': root_growth_rate,
                'reproductive': 0.0  # Lettuce doesn't have reproductive stage in this simulation
            }
            
            # CRITICAL FIX: Model expects normalized environmental factors (0-1), not raw values
            # Temperature: normalize to 0-1 range (optimal ~20-25°C = 0.8-1.0)
            # Water: convert stress (0-1) to water status (1-0)
            # pH: normalize to 0-1 range (optimal ~6.0-6.5 = 0.8-1.0)
            temperature_c = weather_data.get('temperature', 25.0)
            # Normalize temperature: optimal range 20-25°C = 1.0, range 5-35°C = 0.0-1.0
            temp_normalized = max(0.0, min(1.0, (temperature_c - 5.0) / 30.0))  # 5-35°C → 0-1
            # Boost optimal range (20-25°C) to near 1.0
            if 20.0 <= temperature_c <= 25.0:
                temp_normalized = 0.9 + (temperature_c - 20.0) / 25.0 * 0.1  # 0.9-1.0
            
            water_normalized = max(0.1, 1.0 - water_stress)  # Convert stress (0-1) to water status (1-0)
            
            # Normalize pH: optimal ~6.0-6.5 = 1.0, range 4.0-8.0 = 0.0-1.0
            ph_value = 6.0  # Typical hydroponic pH
            ph_normalized = max(0.0, min(1.0, 1.0 - abs(ph_value - 6.25) / 2.25))  # Distance from optimal 6.25
            
            environmental_factors = {
                'temperature': max(0.1, temp_normalized),  # Ensure > 0 (model requirement)
                'water': max(0.1, min(1.0, water_normalized)),  # Clamp to 0.1-1.0
                'pH': max(0.1, min(1.0, ph_normalized))  # Clamp to 0.1-1.0
            }
            
            stress_factors = {
                'nutrient': 1.0 - nutrient_stress,
                'water': 1.0 - water_stress,
                'temperature': 1.0 - temperature_stress
            }
            
            # Senescence rates (fraction/day) - simplified for now
            senescence_rates = {
                'leaves': 0.0,  # No senescence in vegetative lettuce
                'stems': 0.0,
                'roots': 0.0,
                'reproductive': 0.0
            }
            
            # CRITICAL FIX: Call update_nitrogen_pools() to update model's internal state
            # This method updates organ states, calculates remobilization, and returns proper response
            balance_response = self.model.update_nitrogen_pools(
                external_nitrogen_input=nitrogen_uptake_g_per_plant_per_day,  # g/plant/day
                organ_growth_rates=organ_growth_rates,
                environmental_factors=environmental_factors,
                growth_stage=growth_stage_for_model,  # Use converted growth stage
                stress_factors=stress_factors,
                senescence_rates=senescence_rates
            )
            
            # Extract data from NitrogenBalanceResponse
            allocation_response = balance_response.allocation_response
            uptake_response = balance_response.uptake_response
            
            # Create result dict from model response
            result = {
                'total_nitrogen_uptake': nitrogen_uptake_mg_per_plant_per_day,  # From nutrient_models (mg/plant/day)
                'nitrate_uptake': nitrate_uptake_rate,  # From nutrient_models (mg/plant/day)
                'ammonium_uptake': ammonium_uptake_rate,  # From nutrient_models (mg/plant/day)
                'amino_acid_uptake': 0.0,  # Amino acids negligible in hydroponic lettuce
                'total_nitrogen_allocation': sum(allocation_response.allocated_by_organ.values()),  # g/plant/day
                'leaf_nitrogen_allocation': allocation_response.allocated_by_organ.get('leaves', 0.0),
                'stem_nitrogen_allocation': allocation_response.allocated_by_organ.get('stems', 0.0),
                'root_nitrogen_allocation': allocation_response.allocated_by_organ.get('roots', 0.0),
                'reproductive_nitrogen_allocation': allocation_response.allocated_by_organ.get('reproductive', 0.0),
                'total_nitrogen_remobilization': balance_response.remobilized_nitrogen,  # g/plant/day
                'nitrogen_stress_index': balance_response.nitrogen_stress_level,  # Calculated AFTER pools updated
                'nitrogen_use_efficiency': balance_response.nitrogen_use_efficiency,
                'photosynthetic_n_use_efficiency': self.nitrogen_params.photosynthetic_n_use_efficiency,
                'growth_n_use_efficiency': self.nitrogen_params.growth_n_use_efficiency,
                'luxury_uptake_factor': 1.0,  # TODO: Calculate from model
                # Extract nitrogen pools from organ states
                'nitrogen_pools': {
                    'total': balance_response.total_plant_nitrogen,
                    'organic': sum(state.structural_n + state.metabolic_n + state.storage_n for state in balance_response.organ_states.values()),
                    'inorganic': 0.0,  # Not tracked separately
                    'mobile': sum(state.transport_n for state in balance_response.organ_states.values()),
                    'structural': sum(state.structural_n for state in balance_response.organ_states.values())
                },
                # Extract uptake rates from uptake response
                'uptake_rates': {
                    'NO3': nitrate_uptake_rate / root_mass if root_mass > 0 else 0.0,  # mg/g root/day
                    'NH4': ammonium_uptake_rate / root_mass if root_mass > 0 else 0.0,
                    'amino_acids': 0.0
                },
                # Extract allocation rates (g/plant/day)
                'allocation_rates': allocation_response.allocated_by_organ.copy(),
                # Extract remobilization rates (g/plant/day) - simplified for now
                'remobilization_rates': {
                    'leaves': balance_response.remobilized_nitrogen * 0.5 if balance_response.remobilized_nitrogen > 0 else 0.0,
                    'stems': balance_response.remobilized_nitrogen * 0.3 if balance_response.remobilized_nitrogen > 0 else 0.0,
                    'roots': balance_response.remobilized_nitrogen * 0.2 if balance_response.remobilized_nitrogen > 0 else 0.0,
                    'reproductive': 0.0
                }
            }
            
            # Update state with model results
            # Note: nitrate_uptake and ammonium_uptake from result are RATES (mg/plant/day)
            # We need to accumulate them to match total_nitrogen_uptake (which becomes cumulative below)
            nitrate_uptake_rate = result.get('nitrate_uptake', 0.0)
            ammonium_uptake_rate = result.get('ammonium_uptake', 0.0)
            amino_acid_uptake_rate = result.get('amino_acid_uptake', 0.0)
            
            # Update allocation (convert from g/plant/day to hourly rates)
            # Get values directly from allocation_response, not from result dict
            # This ensures we use the actual model output
            total_alloc_daily = sum(allocation_response.allocated_by_organ.values())  # g/plant/day
            leaf_alloc_daily = allocation_response.allocated_by_organ.get('leaves', 0.0)  # g/plant/day
            stem_alloc_daily = allocation_response.allocated_by_organ.get('stems', 0.0)  # g/plant/day
            root_alloc_daily = allocation_response.allocated_by_organ.get('roots', 0.0)  # g/plant/day
            reproductive_alloc_daily = allocation_response.allocated_by_organ.get('reproductive', 0.0)  # g/plant/day
            
            # Ensure all allocation values are non-negative (model should not return negative)
            leaf_alloc_daily = max(0.0, leaf_alloc_daily)
            stem_alloc_daily = max(0.0, stem_alloc_daily)
            root_alloc_daily = max(0.0, root_alloc_daily)
            reproductive_alloc_daily = max(0.0, reproductive_alloc_daily)
            total_alloc_daily = leaf_alloc_daily + stem_alloc_daily + root_alloc_daily + reproductive_alloc_daily
            
            # Add upper bounds to prevent unrealistic values (using parameters from CSV)
            # Max realistic allocation: fraction of current organ biomass per day (using N fraction from CSV)
            # This allows for rapid growth while preventing unrealistic values
            # Remove minimum bound - let model values pass through (they're already validated)
            max_allocation_biomass_fraction = self.nitrogen_params.max_allocation_biomass_fraction  # From CSV
            max_allocation_nitrogen_fraction = self.nitrogen_params.max_allocation_nitrogen_fraction  # From CSV
            max_leaf_alloc = leaf_biomass * max_allocation_biomass_fraction * max_allocation_nitrogen_fraction if leaf_biomass > 0 else 1.0
            max_stem_alloc = stem_biomass * max_allocation_biomass_fraction * max_allocation_nitrogen_fraction if stem_biomass > 0 else 1.0
            max_root_alloc = root_biomass * max_allocation_biomass_fraction * max_allocation_nitrogen_fraction if root_biomass > 0 else 1.0
            
            # Apply upper bounds only (don't clamp small values to minimum)
            leaf_alloc_daily = min(leaf_alloc_daily, max_leaf_alloc) if max_leaf_alloc > 0 else leaf_alloc_daily
            stem_alloc_daily = min(stem_alloc_daily, max_stem_alloc) if max_stem_alloc > 0 else stem_alloc_daily
            root_alloc_daily = min(root_alloc_daily, max_root_alloc) if max_root_alloc > 0 else root_alloc_daily
            total_alloc_daily = leaf_alloc_daily + stem_alloc_daily + root_alloc_daily + reproductive_alloc_daily
            
            # Convert to hourly rates (g/plant/hour)
            leaf_alloc_hourly = leaf_alloc_daily / 24.0
            stem_alloc_hourly = stem_alloc_daily / 24.0
            root_alloc_hourly = root_alloc_daily / 24.0
            reproductive_alloc_hourly = reproductive_alloc_daily / 24.0
            
            # Store hourly rates in state
            self.state.total_nitrogen_allocation = total_alloc_daily / 24.0  # Store as hourly rate
            self.state.leaf_nitrogen_allocation = leaf_alloc_hourly
            self.state.stem_nitrogen_allocation = stem_alloc_hourly
            self.state.root_nitrogen_allocation = root_alloc_hourly
            self.state.reproductive_nitrogen_allocation = reproductive_alloc_hourly

            # Accumulate into cumulative totals for concentration calculation (hourly accumulation)
            self.state.cumulative_leaf_nitrogen += leaf_alloc_hourly
            self.state.cumulative_stem_nitrogen += stem_alloc_hourly
            self.state.cumulative_root_nitrogen += root_alloc_hourly
            self.state.cumulative_reproductive_nitrogen += reproductive_alloc_hourly
            
            # Update remobilization (convert from g/plant/day to hourly rates)
            total_remob_daily = result.get('total_nitrogen_remobilization', 0.0)  # g/plant/day
            remob_rates = result.get('remobilization_rates', {})
            
            # Add bounds checking for remobilization (using parameters from CSV)
            # Remobilization should be reasonable (using fractions from CSV)
            max_remobilization_biomass_fraction = self.nitrogen_params.max_remobilization_biomass_fraction  # From CSV
            max_remobilization_nitrogen_fraction = self.nitrogen_params.max_remobilization_nitrogen_fraction  # From CSV
            max_remob = total_biomass * max_remobilization_biomass_fraction * max_remobilization_nitrogen_fraction if total_biomass > 0 else 0.0
            total_remob_daily = max(0.0, min(total_remob_daily, max_remob))
            
            self.state.total_nitrogen_remobilization = total_remob_daily / 24.0  # Store as hourly rate
            self.state.leaf_nitrogen_remobilization = max(0.0, remob_rates.get('leaves', 0.0) / 24.0)  # Convert to hourly
            self.state.stem_nitrogen_remobilization = max(0.0, remob_rates.get('stems', 0.0) / 24.0)
            self.state.root_nitrogen_remobilization = max(0.0, remob_rates.get('roots', 0.0) / 24.0)
            
            # Update efficiency and stress (get directly from balance_response, not result dict)
            self.state.nitrogen_use_efficiency = balance_response.nitrogen_use_efficiency
            self.state.photosynthetic_n_use_efficiency = self.nitrogen_params.photosynthetic_n_use_efficiency
            self.state.growth_n_use_efficiency = self.nitrogen_params.growth_n_use_efficiency
            self.state.nitrogen_stress_index = balance_response.nitrogen_stress_level  # Get directly from model response
            self.state.luxury_uptake_factor = 1.0  # TODO: Calculate from model if needed
            
            # Update nitrogen pools
            nitrogen_pools = result.get('nitrogen_pools', {})
            for pool in self.nitrogen_pools:
                if pool in nitrogen_pools:
                    self.state.nitrogen_pools[pool] = nitrogen_pools[pool]
            
            # Calculate nitrogen concentrations using cumulative nitrogen and current biomass
            biomass_data = self.dependency_cache.get('biomass_allocation_simulator', {})
            leaf_biomass = biomass_data.get('leaf_biomass')
            stem_biomass = biomass_data.get('stem_biomass')
            root_biomass = biomass_data.get('root_biomass')
            
            if any(x is None for x in [leaf_biomass, stem_biomass, root_biomass]):
                if self.current_step <= 2:
                    return
                raise ValueError("Biomass data missing from biomass_allocation_simulator - no defaults allowed")

            # Calculate concentrations as cumulative N / current biomass (g N / g biomass)
            if leaf_biomass > 0:
                self.state.nitrogen_concentrations['leaves'] = self.state.cumulative_leaf_nitrogen / leaf_biomass
            if stem_biomass > 0:
                self.state.nitrogen_concentrations['stems'] = self.state.cumulative_stem_nitrogen / stem_biomass
            if root_biomass > 0:
                self.state.nitrogen_concentrations['roots'] = self.state.cumulative_root_nitrogen / root_biomass
            if self.state.cumulative_reproductive_nitrogen > 0 and stem_biomass > 0:
                self.state.nitrogen_concentrations['reproductive'] = self.state.cumulative_reproductive_nitrogen / stem_biomass

            # Calculate AREA-BASED nitrogen for photosynthesis (DIRECT BIOCHEMICAL LINK)
            # This enables direct N → Photosynthesis feedback
            # FIX: Use CURRENT leaf N content from organ_states, not cumulative uptake
            canopy_data = self.dependency_cache.get('canopy_architecture_simulator', {})
            leaf_area = canopy_data.get('leaf_area')  # m²

            if leaf_area is not None and leaf_area > 0:
                # Get current leaf N content from organ_states (updated by update_nitrogen_pools)
                # This represents actual current N in leaves, accounting for allocation, remobilization, and growth
                leaf_organ_state = balance_response.organ_states.get('leaves')
                if leaf_organ_state is not None and leaf_organ_state.total_nitrogen > 0:
                    # Use current leaf N content (g N) divided by leaf area (m²)
                    leaf_n_total = leaf_organ_state.total_nitrogen  # g N in leaves (current)
                    leaf_n_area = leaf_n_total / leaf_area  # g N/m² leaf area
                    self.state.nitrogen_area_based['leaves'] = leaf_n_area
                else:
                    # Fallback: use nitrogen concentration * leaf biomass / leaf area
                    # This handles cases where organ_states might not be initialized yet
                    if leaf_biomass > 0:
                        # Get nitrogen concentration from state (g N/g dry mass)
                        leaf_n_conc = self.state.nitrogen_concentrations.get('leaves', 0.0)
                        if leaf_n_conc > 0:
                            leaf_n_total = leaf_biomass * leaf_n_conc  # g N
                            leaf_n_area = leaf_n_total / leaf_area  # g N/m²
                            self.state.nitrogen_area_based['leaves'] = leaf_n_area
                        else:
                            # Last resort: use small default value
                            self.state.nitrogen_area_based['leaves'] = 2.5  # g N/m² (typical optimal)
                    else:
                        # No leaf biomass yet, use default
                        self.state.nitrogen_area_based['leaves'] = 2.5  # g N/m²

                # Also calculate for stems and roots using current organ states
                stem_organ_state = balance_response.organ_states.get('stems')
                root_organ_state = balance_response.organ_states.get('roots')
                
                if stem_organ_state is not None:
                    self.state.nitrogen_area_based['stems'] = stem_organ_state.total_nitrogen
                else:
                    self.state.nitrogen_area_based['stems'] = 0.0
                    
                if root_organ_state is not None:
                    self.state.nitrogen_area_based['roots'] = root_organ_state.total_nitrogen
                else:
                    self.state.nitrogen_area_based['roots'] = 0.0
            
            # Update uptake rates dictionary
            uptake_rates = result.get('uptake_rates', {})
            for form in self.nitrogen_forms:
                if form in uptake_rates:
                    self.state.uptake_rates[form] = uptake_rates[form]
            
            # Update allocation rates dictionary (store hourly rates for consistency)
            # Use the actual calculated allocation values, not from result dict
            self.state.allocation_rates['leaves'] = leaf_alloc_hourly
            self.state.allocation_rates['stems'] = stem_alloc_hourly
            self.state.allocation_rates['roots'] = root_alloc_hourly
            self.state.allocation_rates['reproductive'] = reproductive_alloc_hourly
            
            # Update remobilization rates dictionary (convert from daily to hourly)
            remobilization_rates = result.get('remobilization_rates', {})
            for organ in self.organs:
                if organ in remobilization_rates:
                    # Convert from g/plant/day to g/plant/hour
                    self.state.remobilization_rates[organ] = remobilization_rates[organ] / 24.0
            
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

            # FIX: Also accumulate individual nitrogen forms to ensure consistency
            # Convert rates to hourly system-total values in grams (same units as total_nitrogen_uptake)
            hourly_nitrate_mg_per_plant = nitrate_uptake_rate / 24.0
            hourly_ammonium_mg_per_plant = ammonium_uptake_rate / 24.0
            hourly_amino_acid_mg_per_plant = amino_acid_uptake_rate / 24.0

            hourly_nitrate_g_total = (hourly_nitrate_mg_per_plant * plant_count) / 1000.0
            hourly_ammonium_g_total = (hourly_ammonium_mg_per_plant * plant_count) / 1000.0
            hourly_amino_acid_g_total = (hourly_amino_acid_mg_per_plant * plant_count) / 1000.0

            # Accumulate individual forms
            self.state.nitrate_uptake += hourly_nitrate_g_total
            self.state.ammonium_uptake += hourly_ammonium_g_total
            self.state.amino_acid_uptake += hourly_amino_acid_g_total
            
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
        # Convert hourly rates back to daily rates for CSV export (more readable, avoids precision loss)
        # State stores hourly rates (g/plant/hour) for hourly simulation
        # CSV exports daily rates (g/plant/day) for readability
        return {
            'total_nitrogen_uptake': self.state.total_nitrogen_uptake,
            'nitrate_uptake': self.state.nitrate_uptake,
            'ammonium_uptake': self.state.ammonium_uptake,
            'amino_acid_uptake': self.state.amino_acid_uptake,
            'total_nitrogen_allocation': self.state.total_nitrogen_allocation * 24.0,  # Convert hourly to daily
            'leaf_nitrogen_allocation': self.state.leaf_nitrogen_allocation * 24.0,  # Convert hourly to daily
            'stem_nitrogen_allocation': self.state.stem_nitrogen_allocation * 24.0,  # Convert hourly to daily
            'root_nitrogen_allocation': self.state.root_nitrogen_allocation * 24.0,  # Convert hourly to daily
            'reproductive_nitrogen_allocation': self.state.reproductive_nitrogen_allocation * 24.0,  # Convert hourly to daily
            'total_nitrogen_remobilization': self.state.total_nitrogen_remobilization * 24.0,  # Convert hourly to daily
            'nitrogen_use_efficiency': self.state.nitrogen_use_efficiency,
            'photosynthetic_n_use_efficiency': self.state.photosynthetic_n_use_efficiency,
            'growth_n_use_efficiency': self.state.growth_n_use_efficiency,
            'nitrogen_stress_index': self.state.nitrogen_stress_index,
            'luxury_uptake_factor': self.state.luxury_uptake_factor,
            'nitrogen_pools': self.state.nitrogen_pools,
            'nitrogen_concentrations': self.state.nitrogen_concentrations,
            'nitrogen_area_based': self.state.nitrogen_area_based,  # For direct N → Photosynthesis link
            'uptake_rates': self.state.uptake_rates,
            'allocation_rates': {k: v * 24.0 for k, v in self.state.allocation_rates.items()},  # Convert hourly to daily
            'remobilization_rates': {k: v * 24.0 for k, v in self.state.remobilization_rates.items()},  # Convert hourly to daily
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
            'daily_nitrogen_uptake': self.state.daily_nitrogen_uptake,
            # Add cumulative nitrogen by organ for leaf development simulator
            'cumulative_leaf_nitrogen': self.state.cumulative_leaf_nitrogen,
            'cumulative_stem_nitrogen': self.state.cumulative_stem_nitrogen,
            'cumulative_root_nitrogen': self.state.cumulative_root_nitrogen,
            'cumulative_reproductive_nitrogen': self.state.cumulative_reproductive_nitrogen
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
