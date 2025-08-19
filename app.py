#!/usr/bin/env python3
"""
CROPGRO Hydroponic Simulator - Web Application
Comprehensive web interface for advanced hydroponic crop modeling
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import traceback
import io
import csv
from datetime import datetime, timedelta
import pandas as pd

# Import CROPGRO system
from src.cropgro_hydroponic_simulator import CROPGROHydroponicSimulator
from src.data.hydroponic_system import (
    HydroInputData, HydroSystemConfig, CropParameters, 
    DefaultConfigurations, WeatherData
)
from src.models.nutrient_concentration import NutrientParams
from src.utils.weather_generator import WeatherGenerator

app = Flask(__name__)
app.secret_key = 'cropgro_hydroponic_simulator_2024'

@app.route('/')
def index():
    """Main page with input forms"""
    return render_template('index.html')

@app.route('/api/defaults')
def get_defaults():
    """Get default configuration values"""
    try:
        # Get default system config
        system_config = DefaultConfigurations.get_nft_lettuce_system()
        crop_params = DefaultConfigurations.get_lettuce_parameters()
        nutrient_params = DefaultConfigurations.get_default_nutrients()
        
        defaults = {
            'system': {
                'system_id': system_config.system_id,
                'crop_id': system_config.crop_id,
                'location_id': system_config.location_id,
                'tank_volume': system_config.tank_volume,
                'flow_rate': system_config.flow_rate,
                'system_type': system_config.system_type,
                'system_area': system_config.system_area,
                'n_plants': system_config.n_plants,
                'description': system_config.description
            },
            'crop': {
                'crop_id': crop_params.crop_id,
                'crop_name': crop_params.crop_name,
                'kcb': crop_params.kcb,
                'phi': crop_params.phi,
                'crop_height': crop_params.crop_height,
                'root_zone_depth': crop_params.root_zone_depth,
                'laid': crop_params.laid
            },
            'nutrients': {
                nutrient_id: {
                    'initial_conc': params.initial_conc,
                    'molar_mass': params.molar_mass,
                    'charge': params.charge
                }
                for nutrient_id, params in nutrient_params.items()
            },
            'cultivars': [
                'HYDRO_001', 'HYDRO_002', 'BUTT_001', 'BUTT_002', 
                'ROM_001', 'LOOSE_001'
            ],
            'system_types': ['NFT', 'DWC', 'AEROPONICS']
        }
        
        return jsonify(defaults)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulate', methods=['POST'])
def run_simulation():
    """Run CROPGRO simulation with user inputs"""
    try:
        data = request.json
        
        # Parse inputs
        system_data = data['system']
        crop_data = data['crop']
        weather_data_input = data['weather']
        nutrient_data = data['nutrients']
        simulation_config = data['simulation']
        
        # Get simulation mode early
        simulation_mode = simulation_config.get('simulation_mode', 'days')
        
        print("Received simulation request:", {
            'cultivar': simulation_config.get('cultivar_id', 'HYDRO_001'),
            'days': simulation_config.get('simulation_days', 7),
            'system_type': system_data.get('system_type', 'NFT')
        })
        
        # Create system configuration
        system_config = HydroSystemConfig(
            system_id=system_data['system_id'],
            crop_id=system_data['crop_id'],
            location_id=system_data['location_id'],
            tank_volume=float(system_data['tank_volume']),
            flow_rate=float(system_data['flow_rate']),
            system_type=system_data['system_type'],
            system_area=float(system_data['system_area']),
            n_plants=int(system_data['n_plants']),
            description=system_data['description']
        )
        
        # Create crop parameters
        crop_params = CropParameters(
            crop_id=crop_data['crop_id'],
            crop_name=crop_data['crop_name'],
            kcb=float(crop_data['kcb']),
            phi=float(crop_data['phi']),
            crop_height=float(crop_data['crop_height']),
            root_zone_depth=float(crop_data['root_zone_depth']),
            laid=float(crop_data['laid'])
        )
        
        # Create weather data
        weather_list = []
        if weather_data_input['type'] == 'generate':
            # Generate weather
            generator = WeatherGenerator()
            start_date = datetime.strptime(weather_data_input['start_date'], '%Y-%m-%d')
            # Determine how many days of weather to generate
            if simulation_mode == 'maturity':
                weather_days = simulation_config.get('max_days', 120)
            else:
                weather_days = simulation_config['simulation_days']
                
            weather_list = generator.generate_weather_series(
                start_date=start_date,
                days=weather_days
            )
        else:
            # Use custom weather data
            for day_data in weather_data_input['daily_data']:
                weather = WeatherData(
                    date=datetime.strptime(day_data['date'], '%Y-%m-%d'),
                    temp_avg=float(day_data['temp_avg']),
                    temp_min=float(day_data['temp_min']),
                    temp_max=float(day_data['temp_max']),
                    solar_radiation=float(day_data['solar_radiation']),
                    rel_humidity=float(day_data['rel_humidity']),
                    wind_speed=float(day_data['wind_speed']),
                    rainfall=float(day_data.get('rainfall', 0.0))
                )
                weather_list.append(weather)
        
        # Create nutrient parameters
        nutrient_params = {}
        for nutrient_id, nutrient_info in nutrient_data.items():
            try:
                initial_conc = float(nutrient_info.get('initial_conc', 100.0))
                molar_mass = float(nutrient_info.get('molar_mass', 50.0))
                charge = int(nutrient_info.get('charge', 1))
                
                nutrient_params[nutrient_id] = NutrientParams(
                    nutrient_id=nutrient_id,
                    nutrient_name=nutrient_id,
                    chemical_form=nutrient_id,
                    initial_conc=initial_conc,
                    recharge_conc=initial_conc * 1.2,  # 20% higher for recharge
                    uptake_conc=initial_conc * 0.8,    # 20% lower for uptake
                    sensitivity_coeff=1.0,
                    is_nutritive=True,
                    min_conc=initial_conc * 0.1,       # 10% minimum
                    max_conc=initial_conc * 2.0,       # 200% maximum
                    charge=charge,
                    molar_mass=molar_mass
                )
            except (ValueError, TypeError, KeyError) as e:
                print(f"Error processing nutrient {nutrient_id}: {e}")
                # Use default values
                nutrient_params[nutrient_id] = NutrientParams(
                    nutrient_id=nutrient_id,
                    nutrient_name=nutrient_id,
                    chemical_form=nutrient_id,
                    initial_conc=100.0,
                    recharge_conc=120.0,
                    uptake_conc=80.0,
                    sensitivity_coeff=1.0,
                    is_nutritive=True,
                    min_conc=10.0,
                    max_conc=200.0,
                    charge=1,
                    molar_mass=50.0
                )
        
        # Create input data  
        # Set simulation_days for input_data (used for weather data preparation)
        if simulation_mode == 'maturity':
            simulation_days_param = simulation_config.get('max_days', 120)
        else:
            simulation_days_param = simulation_config['simulation_days']
            
        input_data = HydroInputData(
            system_config=system_config,
            crop_params=crop_params,
            weather_data=weather_list,
            nutrient_params=nutrient_params,
            simulation_days=simulation_days_param
        )
        
        # Create and run simulator
        simulator = CROPGROHydroponicSimulator(
            cultivar_id=simulation_config.get('cultivar_id', 'HYDRO_001'),
            system_type=system_data['system_type']
        )
        
        # Check if maturity-based or fixed-day simulation
        
        if simulation_mode == 'maturity':
            target_maturity = simulation_config.get('target_maturity', 'harvest')
            max_days = simulation_config.get('max_days', 120)
            print(f"Running simulation until {target_maturity} maturity (max {max_days} days)...")
            results = simulator.run_simulation(input_data, max_days=max_days, target_maturity=target_maturity)
        else:
            # Legacy fixed-day simulation for compatibility
            print(f"Running {simulation_config['simulation_days']}-day simulation...")
            # For fixed days, we'll still use the new function but with a high max_days limit
            results = simulator.run_simulation(input_data, max_days=simulation_config['simulation_days'], target_maturity="none")
        
        print("Simulation completed successfully!")
        
        # Prepare response data
        response_data = {
            'success': True,
            'metadata': {
                'cultivar_id': results.metadata['cultivar_id'],
                'cultivar_name': results.metadata['cultivar_name'],
                'simulation_type': results.metadata['simulation_type'],
                'models_used': results.metadata['models_used'],
                'total_days': len(results.daily_results)
            },
            'summary': results.summary_stats,
            'daily_results': []
        }
        
        # Process daily results
        for daily in results.daily_results:
            daily_data = {
                'day': daily.day,
                'date': daily.date.strftime('%Y-%m-%d'),
                'basic': {
                    'temperature': daily.temp_avg,
                    'humidity': getattr(daily, 'rel_humidity', 65.0),
                    'solar_radiation': daily.solar_radiation,
                    'vpd': daily.vpd,
                    'co2_concentration': getattr(daily, 'co2_concentration', 400.0),
                    'ec': daily.ec,
                    'ph': daily.ph
                },
                'phenology': {
                    'growth_stage': getattr(daily, 'growth_stage', 'VE'),
                    'accumulated_gdd': getattr(daily, 'accumulated_gdd', 0.0),
                    'is_vegetative': getattr(daily, 'is_vegetative', True),
                    'is_reproductive': getattr(daily, 'is_reproductive', False)
                },
                'biomass': {
                    'total_biomass': getattr(daily, 'total_biomass', 0.0),
                    'leaf_biomass': getattr(daily, 'leaf_biomass', 0.0),
                    'stem_biomass': getattr(daily, 'stem_biomass', 0.0),
                    'root_biomass': getattr(daily, 'root_biomass', 0.0),
                    'daily_growth_rate': getattr(daily, 'daily_growth_rate', 0.0)
                },
                'canopy': {
                    'lai': getattr(daily, 'lai', 0.0),
                    'height_cm': getattr(daily, 'canopy_height_cm', getattr(daily, 'height_cm', 8.0)),
                    'light_interception': getattr(daily, 'light_interception', 0.0),
                    'canopy_photosynthesis': getattr(daily, 'canopy_photosynthesis', 0.0)
                },
                'physiology': {
                    'photosynthesis_rate': getattr(daily, 'photosynthesis_rate', 0.0),
                    'respiration_rate': getattr(daily, 'respiration_rate', 0.0),
                    'net_assimilation': getattr(daily, 'net_assimilation', 0.0)
                },
                'nitrogen': {
                    'nitrogen_uptake_mg': getattr(daily, 'nitrogen_uptake_mg', 0.0),
                    'nitrogen_stress_factor': getattr(daily, 'nitrogen_stress_factor', 1.0),
                    'leaf_nitrogen_conc': getattr(daily, 'leaf_nitrogen_conc', 4.5)
                },
                'water': {
                    'total_uptake_L': getattr(daily, 'water_uptake_total', 0.0),
                    'transpiration_mm': getattr(daily, 'transpiration', 0.0),
                    'eto_ref_mm': getattr(daily, 'eto_ref', 0.0),
                    'etc_prime_mm': getattr(daily, 'etc_prime', 0.0),
                    'water_use_efficiency': getattr(daily, 'water_use_efficiency', 0.0)
                },
                'stress': {
                    'temperature_stress': getattr(daily, 'temperature_stress_level', 0.0),
                    'integrated_stress': getattr(daily, 'integrated_stress_factor', 1.0),
                    'water_stress': getattr(daily, 'water_stress', 1.0),
                    'nutrient_stress': getattr(daily, 'nutrient_stress', 1.0)
                },
                'genetics': {
                    'cultivar_adaptation_index': getattr(daily, 'cultivar_adaptation_index', 1.0),
                    'yield_potential': getattr(daily, 'cultivar_yield_potential', 1.0),
                    'photosynthesis_capacity': getattr(daily, 'genetic_photosynthesis_capacity', 1.0)
                },
                'environment': {
                    'co2_concentration': daily.co2_concentration,
                    'vpd_actual': daily.vpd_actual,
                    'env_photosynthesis_factor': daily.env_photosynthesis_factor
                }
            }
            response_data['daily_results'].append(daily_data)
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Simulation error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/export/<format>')
def export_results(format):
    """Export simulation results"""
    try:
        # Get results from session or request
        # This is a placeholder - in a real app you'd store results
        return jsonify({'message': f'Export to {format} not implemented yet'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌱 Starting CROPGRO Hydroponic Simulator Web Application")
    print("🌐 Access at: http://localhost:5001")
    print("🔬 Advanced crop modeling with comprehensive input/output")
    
    app.run(host='0.0.0.0', port=5001, debug=True)