"""
Main Hydroponic Simulation Engine
Integrates all models to simulate hydroponic system behavior over time
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models.water_uptake import WaterUptakeModel
from .models.nutrient_concentration import NutrientConcentrationModel, NutrientParams
from .models.dynamic_growth import DynamicGrowthModel
from .models.mechanistic_nutrient_uptake import (
    MechanisticNutrientUptake, PlantBiomass, create_initial_biomass, GrowthStage
)
from .models.carbon_allocation import CarbonAllocationModel
from .models.hydroponic_root_dynamics import HydroponicRootModel
from .models.photosynthesis_model import PhotosynthesisModel
from .models.root_zone_temperature import RootZoneTemperatureModel
from .models.leaf_development import LeafDevelopmentModel
from .models.environmental_control import EnvironmentalControlSystem, ControlStrategy
from .data.hydroponic_system import (
    HydroInputData, SimulationResults, DailyResults,
    HydroSystemConfig, CropParameters, WeatherData, DefaultConfigurations
)
from .utils.weather_generator import WeatherGenerator


class HydroponicSimulator:
    """Main simulation engine for hydroponic systems."""
    
    def __init__(self, use_dynamic_growth: bool = False, use_mechanistic_uptake: bool = False, 
                 use_rzt_model: bool = False, use_leaf_model: bool = False, 
                 use_environmental_control: bool = False):
        self.water_model = WaterUptakeModel()
        self.nutrient_model = NutrientConcentrationModel()
        self.growth_model = DynamicGrowthModel() if use_dynamic_growth else None
        self.mechanistic_uptake = MechanisticNutrientUptake() if use_mechanistic_uptake else None
        self.carbon_allocation_model = CarbonAllocationModel()
        self.photosynthesis_model = PhotosynthesisModel()
        self.rzt_model = RootZoneTemperatureModel() if use_rzt_model else None
        self.leaf_model = LeafDevelopmentModel() if use_leaf_model else None
        self.environmental_control = EnvironmentalControlSystem() if use_environmental_control else None
        self.use_dynamic_growth = use_dynamic_growth
        self.use_mechanistic_uptake = use_mechanistic_uptake
        self.use_rzt_model = use_rzt_model
        self.use_leaf_model = use_leaf_model
        self.use_environmental_control = use_environmental_control
        self.results: Optional[SimulationResults] = None
        
        # Initialize biomass tracking
        self.current_biomass: Optional[PlantBiomass] = None
        self.current_ph: float = 6.0
        self.current_ec: float = 1.8
        self.current_rzt: float = 22.0  # Default root zone temperature (°C)
        self.current_co2: float = 400.0  # Default CO2 concentration (μmol/mol)
        self.current_vpd: float = 0.8  # Default VPD (kPa)

    def _calculate_ec(self, concentrations: Dict[str, float]) -> float:
        """Calculate EC using the Sonneveld et al. (1990) model."""
        # Calculate sum of cations in meq/L
        sum_cations_meql = 0
        for nutrient_id, conc_mg_l in concentrations.items():
            params = self.nutrient_model.nutrients.get(nutrient_id)
            if params and params.charge > 0: # It's a cation
                # mg/L to mol/L
                conc_mol_l = (conc_mg_l / 1000.0) / params.molar_mass
                # mol/L to eq/L
                conc_eq_l = conc_mol_l * params.charge
                # eq/L to meq/L
                conc_meq_l = conc_eq_l * 1000.0
                sum_cations_meql += conc_meq_l
        
        # EC = 0.19 + 0.095 * [C+]
        ec = 0.19 + 0.095 * sum_cations_meql
        return ec
        
    def setup_simulation(self, input_data: HydroInputData):
        """Set up the simulation with input data."""
        self.input_data = input_data
        
        # Initialize nutrient model with nutrient parameters
        for nutrient_id, params in input_data.nutrient_params.items():
            self.nutrient_model.add_nutrient(params)
    
    def run_simulation(self, input_data: HydroInputData) -> SimulationResults:
        """
        Run complete hydroponic simulation.
        
        Args:
            input_data: Complete input data for simulation
            
        Returns:
            SimulationResults object with daily results and summary
        """
        self.setup_simulation(input_data)
        
        # Initialize results storage
        daily_results = []
        
        # Initial conditions
        current_tank_volume = input_data.system_config.tank_volume
        current_concentrations = {
            nutrient_id: params.initial_conc 
            for nutrient_id, params in input_data.nutrient_params.items()
        }
        current_ph = self.current_ph
        current_ec = self.current_ec
        
        # Initialize biomass for mechanistic model
        if self.use_mechanistic_uptake:
            self.current_biomass = create_initial_biomass(
                input_data.system_config.n_plants, 
                initial_fresh_weight_per_plant=2.0,  # 2g per seedling
                system_type=input_data.system_config.system_type  # Pass hydroponic system type
            )
        
        # Initialize growth tracking
        lai_history = []
        nutrient_faults = []
        
        # Initialize biomass tracking
        cumulative_biomass = 0.0  # kg dry matter
        cumulative_fresh_weight = 0.0  # kg fresh weight
        
        # Run daily simulation loop
        for day, weather in enumerate(input_data.weather_data[:input_data.simulation_days]):
            current_day = day + 1  # Day numbering starts from 1
            
            # Get dynamic or static crop parameters
            if self.use_dynamic_growth and self.growth_model:
                growth_params = self.growth_model.calculate_dynamic_parameters(
                    current_day, weather.temp_avg, weather.solar_radiation
                )
                lai = growth_params['lai']
                height = growth_params['height'] 
                kcb = growth_params['kcb']
                phi = growth_params['phi']
                nutrient_factor = growth_params['nutrient_uptake_factor']
                
                # Track LAI for growth phase detection
                lai_history.append(lai)
                
                # Detect growth phase transitions
                if len(lai_history) >= 4:
                    transition = self.growth_model.detect_growth_phase_transition(lai_history)
                    if transition:
                        print(f"Day {current_day}: Growth phase transition detected - {transition}")
                
            else:
                # Use static parameters
                lai = input_data.crop_params.laid
                height = input_data.crop_params.crop_height
                kcb = input_data.crop_params.kcb
                phi = input_data.crop_params.phi
                nutrient_factor = 1.0
            
            # Update leaf development model if enabled
            leaf_results = {}
            if self.use_leaf_model and self.leaf_model:
                # Calculate stress factors for leaf development
                water_stress = 1.0  # Will be updated with actual stress calculation
                nitrogen_stress = 1.0  # Will be based on N concentration
                temperature_stress = 1.0  # Will be based on temperature conditions
                
                # Update N stress based on concentration
                if 'N-NO3' in current_concentrations:
                    optimal_n = 200.0  # mg/L optimal N concentration for lettuce
                    nitrogen_stress = min(1.0, current_concentrations['N-NO3'] / optimal_n)
                
                # Update temperature stress  
                optimal_temp_range = (18, 24)  # Optimal for lettuce
                if weather.temp_avg < optimal_temp_range[0] or weather.temp_avg > optimal_temp_range[1]:
                    if weather.temp_avg < optimal_temp_range[0]:
                        temperature_stress = max(0.2, (weather.temp_avg - 4) / (optimal_temp_range[0] - 4))
                    else:
                        temperature_stress = max(0.2, (35 - weather.temp_avg) / (35 - optimal_temp_range[1]))
                
                # Update leaf model
                leaf_results = self.leaf_model.daily_update(
                    weather.temp_avg, water_stress, nitrogen_stress, temperature_stress
                )
                
                # Override LAI with leaf model result if available
                if 'leaf_area_index' in leaf_results:
                    lai = leaf_results['leaf_area_index']
            
            # Initialize environmental control effects (will be updated if enabled)
            env_control_effects = {
                'vpd_transpiration_factor': 1.0,
                'vpd_photosynthesis_factor': 1.0,
                'co2_photosynthesis_factor': 1.0,
                'combined_photosynthesis_factor': 1.0
            }
            
            # Calculate net radiation
            net_radiation = self.water_model.calculate_net_radiation(
                weather.solar_radiation, weather.temp_max, weather.temp_min,
                weather.rel_humidity
            )
            
            # Calculate reference ET
            eto_ref = self.water_model.calculate_reference_et(
                net_radiation, weather.temp_avg, weather.temp_min,
                weather.temp_max, weather.wind_speed, weather.rel_humidity
            )
            
            # Calculate crop ET and transpiration using dynamic parameters
            etc_prime, transpiration_mm = self.water_model.calculate_crop_et(
                eto_ref, kcb, phi, lai, height
            )
            
            # Convert transpiration from mm/day to L/day
            # Assuming 1 m² growing area per calculation unit
            transpiration_l = transpiration_mm * input_data.system_config.system_area
            
            # Calculate nutrient uptake - mechanistic vs simplified
            if self.use_mechanistic_uptake and self.mechanistic_uptake and self.current_biomass:
                # Use Monod kinetics for realistic nutrient uptake
                stage = self._get_growth_stage_enum(growth_params.get('growth_stage', 'slow_growth') 
                                                  if self.use_dynamic_growth else 'rapid_growth')
                
                # Calculate RZT effects if enabled
                rzt_effects = {}
                if self.use_rzt_model and self.rzt_model:
                    # Update RZT based on air temperature (simplified control)
                    optimal_rzt = self.rzt_model.calculate_optimal_rzt(weather.temp_avg)
                    self.current_rzt = optimal_rzt  # Assume perfect temperature control for now
                    
                    # Calculate comprehensive RZT effects
                    rzt_effects = self.rzt_model.calculate_comprehensive_rzt_effects(
                        self.current_rzt, weather.temp_avg
                    )
                else:
                    # Default RZT effects (no impact)
                    rzt_effects = {
                        'growth_factor': 1.0,
                        'nutrient_uptake_factor': 1.0,
                        'water_uptake_factor': 1.0,
                        'photosynthesis_factor': 1.0,
                        'root_metabolism_factor': 1.0
                    }
                
                # Calculate environmental control effects if enabled
                env_control_effects = {}
                if self.use_environmental_control and self.environmental_control:
                    # Determine photoperiod (assuming 16h light cycle starting at 6 AM)
                    hour_of_day = (current_day - 1) * 24 % 24  # Simplified daily cycle
                    light_on = 6 <= hour_of_day <= 22  # 16-hour photoperiod
                    
                    # Current environmental conditions
                    current_conditions = {
                        'temperature': weather.temp_avg,
                        'humidity': weather.rel_humidity,
                        'co2': self.current_co2,
                        'light_intensity': 200.0 if light_on else 0.0
                    }
                    
                    light_schedule = {'light_on': light_on}
                    
                    # Calculate comprehensive environmental control
                    env_control_results = self.environmental_control.calculate_comprehensive_control(
                        current_conditions, light_schedule, ControlStrategy.PID
                    )
                    
                    # Extract environmental factors for plant models
                    env_control_effects = env_control_results['plant_factors']
                    
                    # Update system state based on control actions
                    self.current_vpd = env_control_results['current_conditions']['vpd_kPa']
                    if light_on:
                        # Apply CO2 control during photoperiod
                        co2_action = env_control_results['control_actions']['co2']
                        if co2_action['co2_injection_rate'] > 0:
                            # Increase CO2 based on injection rate
                            co2_increase = co2_action['co2_injection_rate'] * 0.5  # Simplified response
                            self.current_co2 = min(1800.0, self.current_co2 + co2_increase)
                        elif co2_action['ventilation_increase'] > 0:
                            # Decrease CO2 due to ventilation
                            co2_decrease = co2_action['ventilation_increase'] * 20.0
                            self.current_co2 = max(350.0, self.current_co2 - co2_decrease)
                    else:
                        # Gradual return to ambient CO2 during dark period
                        self.current_co2 = max(350.0, self.current_co2 - 10.0)
                # If not using environmental control, keep default values (already initialized)
                
                # Environmental conditions for uptake with RZT and environmental control integration
                base_growth_factor = growth_params.get('env_factor', 1.0) if self.use_dynamic_growth else 1.0
                combined_growth_factor = (base_growth_factor * rzt_effects['growth_factor'] * 
                                        env_control_effects['vpd_photosynthesis_factor'])
                
                env_conditions = {
                    'growth_factor': combined_growth_factor,
                    'dli_factor': growth_params.get('dli_factor', 1.0) if self.use_dynamic_growth else 1.0,
                    'temp_factor': growth_params.get('temp_factor', 1.0) if self.use_dynamic_growth else 1.0,
                    'temp_avg': weather.temp_avg,
                    'rzt': self.current_rzt,
                    'rzt_growth_factor': rzt_effects['growth_factor'],
                    'rzt_nutrient_factor': rzt_effects['nutrient_uptake_factor'],
                    'rzt_water_factor': rzt_effects['water_uptake_factor'],
                    'rzt_metabolism_factor': rzt_effects['root_metabolism_factor'],
                    'vpd_transpiration_factor': env_control_effects['vpd_transpiration_factor'],
                    'vpd_photosynthesis_factor': env_control_effects['vpd_photosynthesis_factor'],
                    'co2_photosynthesis_factor': env_control_effects['co2_photosynthesis_factor'],
                    'dissolved_oxygen': 6.0,  # Default hydroponic DO level
                    'ph': current_ph,
                    'flow_rate': input_data.system_config.flow_rate / 60.0  # Convert L/h to L/min
                }
                
                # Calculate mechanistic nutrient uptake for each nutrient
                nutrient_uptake = {}
                uptake_diagnostics = {}
                
                for nutrient_id, concentration in current_concentrations.items():
                    if nutrient_id in self.mechanistic_uptake.kinetic_params:
                        stage_kinetics = self.mechanistic_uptake.kinetic_params[nutrient_id][stage]
                        uptake_rate, diagnostics = self.mechanistic_uptake.calculate_monod_uptake(
                            concentration, stage_kinetics, self.current_biomass, 
                            env_conditions['growth_factor'], current_tank_volume
                        )
                        # Apply RZT nutrient uptake factor
                        uptake_rate *= rzt_effects['nutrient_uptake_factor']
                        nutrient_uptake[nutrient_id] = uptake_rate
                        uptake_diagnostics[nutrient_id] = diagnostics
                
                # Carbon and Nitrogen Assimilation
                # Convert solar radiation (MJ/m2/day) to PAR (umol photons/m2/s)
                # Approx conversion: 1 MJ/m2/day = 2.04 mol photons/m2/day = 2.04 * 1e6 umol / (24*3600) umol/m2/s = 23.6 umol/m2/s
                par_umol_m2_s = weather.solar_radiation * 23.6
                
                # Use current CO2 concentration from environmental control
                co2_concentration = self.current_co2

                carbon_assimilated = self.photosynthesis_model.calculate_daily_assimilation(
                    par_umol_m2_s, co2_concentration, weather.temp_avg, lai
                )
                # Apply RZT and environmental control photosynthesis factors
                carbon_assimilated *= rzt_effects['photosynthesis_factor']
                carbon_assimilated *= env_control_effects['combined_photosynthesis_factor']
                nitrogen_assimilated = nutrient_uptake.get('N-NO3', 0) / 1000.0 # g

                # Update biomass using the new carbon allocation model
                self.current_biomass = self.carbon_allocation_model.update_biomass(
                    self.current_biomass, carbon_assimilated, nitrogen_assimilated
                )
                biomass_partition = self.carbon_allocation_model.partition_biomass(self.current_biomass)
                self.current_biomass.shoot_mass = biomass_partition['shoot_mass']
                self.current_biomass.root_mass = biomass_partition['root_mass']

                # Update root system dynamics
                if self.current_biomass.root_system:
                    root_model = HydroponicRootModel(self.current_biomass.root_system.system_type)
                    self.current_biomass.root_system = root_model.calculate_daily_root_growth(
                        self.current_biomass.root_system,
                        self.current_biomass.get_total_dry_mass(),
                        stage.value,
                        env_conditions
                    )

                # Apply RZT and VPD factors to transpiration
                environmental_adjusted_transpiration = (transpiration_l * 
                                                       rzt_effects['water_uptake_factor'] * 
                                                       env_control_effects['vpd_transpiration_factor'])
                
                # Apply water balance constraint - cannot consume more than available
                max_available_water = max(0, current_tank_volume - 1.0)  # Keep 1L minimum for circulation
                actual_water_consumed = min(environmental_adjusted_transpiration, max_available_water)
                
                # Update tank volume with actual consumption
                new_tank_volume = current_tank_volume - actual_water_consumed
                
                # Update concentrations with both uptake and concentration effects
                new_concentrations = {}
                for nutrient_id, concentration in current_concentrations.items():
                    uptake_mg = nutrient_uptake.get(nutrient_id, 0)
                    
                    # Mass balance: uptake reduces total nutrient mass
                    old_total_mass = concentration * current_tank_volume  # mg total
                    new_total_mass = max(0, old_total_mass - uptake_mg)   # mg after uptake
                    
                    # Concentration effect: same mass in smaller volume increases concentration
                    if new_tank_volume > 0.1:
                        new_conc = new_total_mass / new_tank_volume  # mg/L
                    else:
                        new_conc = concentration  # Prevent division by zero
                    
                    new_concentrations[nutrient_id] = max(0.1, new_conc)

                # pH modeling
                total_charge_uptake = 0
                for nutrient_id, uptake_mg in nutrient_uptake.items():
                    params = self.nutrient_model.nutrients[nutrient_id]
                    if params.molar_mass > 0:
                        uptake_moles = (uptake_mg / 1000.0) / params.molar_mass
                        total_charge_uptake += uptake_moles * params.charge
                
                # Update pH based on charge balance
                if current_tank_volume > 0:
                    delta_h_moles = -total_charge_uptake 
                    delta_h_conc = delta_h_moles / current_tank_volume
                    
                    current_h_conc = 10**(-current_ph)
                    new_h_conc = current_h_conc + delta_h_conc

                    if new_h_conc > 0:
                        current_ph = -np.log10(new_h_conc)
                    else:
                        current_ph = 7.0

                # Apply water stress if insufficient water available
                if actual_water_consumed < environmental_adjusted_transpiration:
                    water_stress_factor = actual_water_consumed / (transpiration_l + 1e-6)
                    for nutrient_id in nutrient_uptake:
                        nutrient_uptake[nutrient_id] *= water_stress_factor
                    print(f"Day {current_day}: Water stress detected - {water_stress_factor:.2f} stress factor")
                else:
                    water_stress_factor = 1.0
                
                # Fault detection
                predicted_conc = {n: c - u/current_tank_volume 
                                for n, c, u in zip(current_concentrations.keys(), 
                                                  current_concentrations.values(),
                                                  [nutrient_uptake.get(n, 0) for n in current_concentrations.keys()])}
                faults = self.mechanistic_uptake.detect_nutrient_faults(
                    predicted_conc, new_concentrations, uptake_diagnostics
                )
                if faults:
                    nutrient_faults.extend([(current_day, faults)])
                
            else:
                # Use simplified model with dynamic uptake factor
                adjusted_transpiration = transpiration_l * nutrient_factor
                new_concentrations = self.nutrient_model.get_all_concentrations(
                    current_concentrations, adjusted_transpiration, current_tank_volume
                )
                
                # Update tank volume
                new_tank_volume = self.nutrient_model.update_solution_volume(
                    current_tank_volume, transpiration_l
                )
            
            # Calculate VPD for this day
            vpd = self._calculate_vpd(weather.temp_avg, weather.rel_humidity)
            
            # Calculate process-based water use efficiency
            wue = self._calculate_dynamic_wue(
                weather.solar_radiation, vpd, 
                current_concentrations, stage if self.use_dynamic_growth else 'rapid_growth',
                water_stress_factor if self.use_mechanistic_uptake else 1.0
            )
            
            # Calculate EC
            current_ec = self._calculate_ec(new_concentrations)

            # Store daily results with additional growth data
            daily_result = DailyResults(
                date=weather.date,
                day=current_day,
                eto_ref=eto_ref,
                etc_prime=etc_prime,
                transpiration=transpiration_mm,
                water_uptake_total=transpiration_l,
                tank_volume=new_tank_volume,
                nutrient_concentrations=new_concentrations.copy(),
                temp_avg=weather.temp_avg,
                solar_radiation=weather.solar_radiation,
                vpd=vpd,
                water_use_efficiency=wue,
                ph=current_ph,
                ec=current_ec,
                rzt=self.current_rzt,
                rzt_growth_factor=rzt_effects.get('growth_factor', 1.0) if self.use_mechanistic_uptake else 1.0,
                rzt_nutrient_factor=rzt_effects.get('nutrient_uptake_factor', 1.0) if self.use_mechanistic_uptake else 1.0,
                v_stage=leaf_results.get('v_stage', 0.0) if self.use_leaf_model else 0.0,
                leaf_number=leaf_results.get('leaf_number', 0) if self.use_leaf_model else 0,
                leaf_area_m2=leaf_results.get('total_leaf_area_m2', 0.0) if self.use_leaf_model else 0.0,
                average_leaf_area_cm2=leaf_results.get('average_leaf_area', 0.0) * 10000 if self.use_leaf_model else 0.0,
                co2_concentration=self.current_co2,
                vpd_actual=self.current_vpd,
                env_photosynthesis_factor=env_control_effects.get('combined_photosynthesis_factor', 1.0),
                env_transpiration_factor=env_control_effects.get('vpd_transpiration_factor', 1.0)
            )
            
            # Add dynamic growth data if available
            if self.use_dynamic_growth and self.growth_model:
                # Store growth parameters in daily result for analysis
                daily_result.lai = lai
                daily_result.height = height
                daily_result.kcb_dynamic = kcb
                daily_result.phi_dynamic = phi
                daily_result.growth_stage = growth_params['growth_stage']
                daily_result.nutrient_factor = nutrient_factor
            
            # Add mechanistic uptake data if available
            if self.use_mechanistic_uptake and self.current_biomass:
                daily_result.total_biomass = self.current_biomass.get_total_dry_mass()
                daily_result.fresh_weight = self.current_biomass.total_fresh_weight
                daily_result.structural_mass = self.current_biomass.structural_mass
                daily_result.uptake_capacity = self.current_biomass.get_uptake_capacity()
                
                # Store nutrient uptake diagnostics
                if 'nutrient_uptake' in locals():
                    daily_result.nutrient_uptake_rates = nutrient_uptake.copy()
                if 'uptake_diagnostics' in locals():
                    daily_result.uptake_diagnostics = uptake_diagnostics.copy()
            
            daily_results.append(daily_result)
            
            # Update state for next day
            current_tank_volume = new_tank_volume
            current_concentrations = new_concentrations
        
        # Create simulation results
        start_date = input_data.weather_data[0].date
        end_date = input_data.weather_data[input_data.simulation_days - 1].date
        
        results = SimulationResults(
            system_id=input_data.system_config.system_id,
            crop_id=input_data.system_config.crop_id,
            location_id=input_data.system_config.location_id,
            start_date=start_date,
            end_date=end_date,
            total_days=input_data.simulation_days,
            daily_results=daily_results
        )
        
        # Calculate summary statistics
        results.calculate_summary_stats()
        
        self.results = results
        return results
    
    def _calculate_vpd(self, temp: float, rel_humidity: float) -> float:
        """Calculate vapor pressure deficit."""
        # Saturation vapor pressure (kPa)
        es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
        # Actual vapor pressure (kPa)
        ea = es * rel_humidity / 100.0
        # VPD (kPa)
        return max(0.0, es - ea)
    
    def _get_growth_stage_enum(self, stage_string: str) -> GrowthStage:
        """Convert growth stage string to enum."""
        stage_mapping = {
            'slow_growth': GrowthStage.SLOW_GROWTH,
            'rapid_growth': GrowthStage.RAPID_GROWTH,
            'steady_growth': GrowthStage.STEADY_GROWTH
        }
        return stage_mapping.get(stage_string, GrowthStage.RAPID_GROWTH)
    
    def _calculate_dynamic_wue(self, solar_radiation: float, vpd: float, 
                              nutrient_concentrations: Dict[str, float], 
                              growth_stage: str, water_stress: float = 1.0) -> float:
        """Calculate process-based water use efficiency."""
        # Base WUE for lettuce (kg dry matter / m³ water)
        base_wue = 2.8  # kg/m³ typical for lettuce
        
        # Light efficiency factor (0.5 to 1.8)
        optimal_light = 18.0  # MJ/m²/day optimal for lettuce
        light_factor = min(1.8, max(0.5, solar_radiation / optimal_light))
        
        # VPD stress factor (0.4 to 1.2)
        optimal_vpd = 0.8  # kPa optimal VPD
        if vpd <= optimal_vpd:
            vpd_factor = 1.0 + (optimal_vpd - vpd) * 0.25  # Bonus for low VPD
        else:
            vpd_factor = max(0.4, 1.0 - (vpd - optimal_vpd) * 0.5)  # Penalty for high VPD
        
        # Nutrient status factor (0.6 to 1.3)
        n_status = nutrient_concentrations.get('N-NO3', 200) / 200.0  # Relative to optimal
        p_status = nutrient_concentrations.get('P-PO4', 50) / 50.0
        nutrient_factor = min(1.3, max(0.6, (n_status + p_status) / 2.0))
        
        # Growth stage factor
        stage_factors = {
            'slow_growth': 0.8,    # Lower WUE during establishment
            'rapid_growth': 1.1,   # Higher WUE during rapid growth
            'steady_growth': 0.9   # Moderate WUE at maturity
        }
        stage_factor = stage_factors.get(growth_stage, 1.0)
        
        # Water stress factor
        water_factor = max(0.3, water_stress)  # Severe penalty for water stress
        
        # Calculate final WUE
        dynamic_wue = (base_wue * light_factor * vpd_factor * 
                      nutrient_factor * stage_factor * water_factor)
        
        return max(0.5, min(6.0, dynamic_wue))  # Reasonable bounds
    
    def save_results_csv(self, filename: str):
        """Save simulation results to CSV file with a second row for units."""
        if self.results is None:
            raise ValueError("No simulation results to save. Run simulation first.")

        df = self.results.to_dataframe()

        units = {
            'Date': '(YYYY-MM-DD)',
            'Day': '(day)',
            'System_ID': '(id)',
            'Crop_ID': '(id)',
            'ETO_Ref_mm': '(mm/day)',
            'ETC_Prime_mm': '(mm/day)',
            'Transpiration_mm': '(mm/day)',
            'Water_Total_L': '(L/day)',
            'Tank_Volume_L': '(L)',
            'Temp_C': '(°C)',
            'Solar_Rad_MJ': '(MJ/m²/day)',
            'VPD_kPa': '(kPa)',
            'WUE_kg_m3': '(kg/m³)',
            'LAI': '(unitless)',
            'Height_m': '(m)',
            'Kcb_dynamic': '(unitless)',
            'Growth_Stage': '(stage)',
            'Total_Biomass_g': '(g)',
            'Fresh_Weight_g': '(g)',
            'pH': '(unitless)',
            'EC': '(dS/m)',
            'RZT_C': '(°C)',
            'RZT_Growth_Factor': '(unitless)',
            'RZT_Nutrient_Factor': '(unitless)',
            'V_Stage': '(unitless)',
            'Leaf_Number': '(count)',
            'Leaf_Area_m2': '(m²)',
            'Avg_Leaf_Area_cm2': '(cm²)',
            'CO2_umol_mol': '(μmol/mol)',
            'VPD_Actual_kPa': '(kPa)',
            'Env_Photo_Factor': '(unitless)',
            'Env_Transp_Factor': '(unitless)'
        }
        for col in df.columns:
            if col.endswith('_mg_L'):
                units[col] = '(mg/L)'

        with open(filename, 'w', newline='') as f:
            f.write(','.join(df.columns) + '\n')
            unit_row = [units.get(col, '') for col in df.columns]
            f.write(','.join(unit_row) + '\n')
            df.to_csv(f, header=False, index=False)

        print(f"Results saved to {filename}")
    
    def print_summary(self):
        """Print simulation summary to console."""
        if self.results is None:
            print("No simulation results available.")
            return
            
        print("\n" + "="*60)
        print("    HYDROPONIC SIMULATION SUMMARY")
        print("="*60)
        print(f"System: {self.results.system_id} | Crop: {self.results.crop_id} | Location: {self.results.location_id}")
        print(f"Simulation Period: {self.results.start_date.strftime('%Y-%m-%d')} to {self.results.end_date.strftime('%Y-%m-%d')}")
        print(f"Total Days: {self.results.total_days}")
        print("-"*60)
        
        stats = self.results.summary_stats
        print(f"Total Water Consumption:    {stats['total_water_consumption_L']:.1f} L")
        print(f"Average Daily Consumption:  {stats['average_daily_consumption_L']:.1f} L/day")
        print(f"Final Tank Volume:          {stats['final_tank_volume_L']:.1f} L")
        print(f"Volume Reduction:           {stats['volume_reduction_L']:.1f} L")
        print(f"Average Reference ET:       {stats['average_eto_mm']:.2f} mm/day")
        print(f"Average Transpiration:      {stats['average_transpiration_mm']:.2f} mm/day")
        print(f"Temperature Range:          {stats['min_temperature_C']:.1f}°C - {stats['max_temperature_C']:.1f}°C")
        print(f"Average Water Use Efficiency: {stats['average_wue_kg_m3']:.2f} kg/m³")
        print("="*60)


def create_demo_simulation() -> HydroInputData:
    """Create demonstration simulation data."""
    # Get default configurations
    system_config = DefaultConfigurations.get_nft_lettuce_system()
    crop_params = DefaultConfigurations.get_lettuce_parameters()
    nutrient_params = DefaultConfigurations.get_default_nutrients()
    
    # Generate weather data
    generator = WeatherGenerator()
    start_date = datetime(2024, 4, 11)
    weather_data = generator.generate_weather_series(start_date, 30)
    
    return HydroInputData(
        system_config=system_config,
        crop_params=crop_params,
        weather_data=weather_data,
        nutrient_params=nutrient_params,
        simulation_days=30
    )


def main():
    """Main function to run demonstration simulation."""
    print("Initializing Hydroponic Simulation...")
    
    # Create simulator
    simulator = HydroponicSimulator()
    
    # Create demo input data
    input_data = create_demo_simulation()
    
    # Run simulation
    print("Running 30-day simulation...")
    results = simulator.run_simulation(input_data)
    
    # Print results
    simulator.print_summary()
    
    # Save results
    output_file = "../data/output/hydroponic_simulation_results.csv"
    try:
        simulator.save_results_csv(output_file)
    except Exception as e:
        print(f"Could not save to {output_file}: {e}")
        print("Saving to current directory...")
        simulator.save_results_csv("hydroponic_results.csv")
    
    return results


if __name__ == "__main__":
    main()