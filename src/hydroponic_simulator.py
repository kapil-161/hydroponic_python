"""
Main Hydroponic Simulation Engine
Integrates all models to simulate hydroponic system behavior over time
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models.water_uptake import WaterUptakeModel
from .models.nutrient_concentration import NutrientConcentrationModel, NutrientParams
from .models.dynamic_growth import DynamicGrowthModel
from .models.mechanistic_nutrient_uptake import (
    MechanisticNutrientUptake, PlantBiomass, create_initial_biomass, GrowthStage
)
from .data.hydroponic_system import (
    HydroInputData, SimulationResults, DailyResults,
    HydroSystemConfig, CropParameters, WeatherData, DefaultConfigurations
)
from .utils.weather_generator import WeatherGenerator


class HydroponicSimulator:
    """Main simulation engine for hydroponic systems."""
    
    def __init__(self, use_dynamic_growth: bool = False, use_mechanistic_uptake: bool = False):
        self.water_model = WaterUptakeModel()
        self.nutrient_model = NutrientConcentrationModel()
        self.growth_model = DynamicGrowthModel() if use_dynamic_growth else None
        self.mechanistic_uptake = MechanisticNutrientUptake() if use_mechanistic_uptake else None
        self.use_dynamic_growth = use_dynamic_growth
        self.use_mechanistic_uptake = use_mechanistic_uptake
        self.results: Optional[SimulationResults] = None
        
        # Initialize biomass tracking
        self.current_biomass: Optional[PlantBiomass] = None
        
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
                
                # Environmental conditions for uptake
                env_conditions = {
                    'growth_factor': growth_params.get('env_factor', 1.0) if self.use_dynamic_growth else 1.0,
                    'dli_factor': growth_params.get('dli_factor', 1.0) if self.use_dynamic_growth else 1.0,
                    'temp_factor': growth_params.get('temp_factor', 1.0) if self.use_dynamic_growth else 1.0,
                    'temp_avg': weather.temp_avg,
                    'dissolved_oxygen': 6.0,  # Default hydroponic DO level
                    'ph': 6.0,                # Default hydroponic pH
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
                        nutrient_uptake[nutrient_id] = uptake_rate
                        uptake_diagnostics[nutrient_id] = diagnostics
                
                # Update biomass based on nutrient uptake
                self.current_biomass = self.mechanistic_uptake.update_biomass(
                    self.current_biomass, nutrient_uptake, env_conditions, stage
                )
                
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
                
                # Apply water balance constraint - cannot consume more than available
                max_available_water = max(0, current_tank_volume - 1.0)  # Keep 1L minimum for circulation
                actual_water_consumed = min(transpiration_l, max_available_water)
                
                # Update tank volume with actual consumption
                new_tank_volume = current_tank_volume - actual_water_consumed
                
                # Apply water stress if insufficient water available
                if actual_water_consumed < transpiration_l:
                    water_stress_factor = actual_water_consumed / (transpiration_l + 1e-6)
                    # Reduce nutrient uptake proportionally due to water stress
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
                water_use_efficiency=wue
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
        """Save simulation results to CSV file."""
        if self.results is None:
            raise ValueError("No simulation results to save. Run simulation first.")
            
        df = self.results.to_dataframe()
        df.to_csv(filename, index=False)
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