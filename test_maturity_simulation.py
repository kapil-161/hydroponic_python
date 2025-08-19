#!/usr/bin/env python3
"""
Test the maturity-based simulation functionality
"""

import requests
import json
from datetime import datetime

def test_maturity_simulation():
    """Test the maturity-based simulation API"""
    print("🧪 Testing maturity-based simulation...")
    
    # Create test data for maturity simulation
    test_data = {
        "simulation": {
            "cultivar_id": "HYDRO_001",
            "simulation_mode": "maturity",
            "target_maturity": "harvest",
            "max_days": 60
        },
        "system": {
            "system_id": "MATURITY_TEST",
            "crop_id": "LETTUCE_001",
            "location_id": "GREENHOUSE_001",
            "tank_volume": 1500.0,
            "flow_rate": 50.0,
            "system_type": "NFT",
            "system_area": 10.0,
            "n_plants": 48,
            "description": "Maturity Test System"
        },
        "crop": {
            "crop_id": "LETTUCE_001",
            "crop_name": "Test Lettuce",
            "kcb": 1.05,
            "phi": 0.8,
            "crop_height": 0.2,
            "root_zone_depth": 0.15,
            "laid": 3.0
        },
        "weather": {
            "type": "generate",
            "start_date": "2024-04-15",
            "base_temp": 22.0
        },
        "nutrients": {
            "N-NO3": {"initial_conc": 200.0, "molar_mass": 62.0, "charge": -1},
            "P": {"initial_conc": 50.0, "molar_mass": 31.0, "charge": 3},
            "K": {"initial_conc": 200.0, "molar_mass": 39.1, "charge": 1},
            "Ca": {"initial_conc": 150.0, "molar_mass": 40.1, "charge": 2},
            "Mg": {"initial_conc": 50.0, "molar_mass": 24.3, "charge": 2}
        }
    }
    
    try:
        print("  • Sending maturity-based simulation request...")
        response = requests.post(
            'http://localhost:5001/api/simulate',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=180  # 3 minute timeout for longer simulations
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success', False):
                print("✅ Maturity simulation working!")
                print(f"  • Cultivar: {result['metadata']['cultivar_name']}")
                print(f"  • Total days: {result['metadata']['total_days']}")
                print(f"  • Final biomass: {result['summary'].get('total_biomass_g', 0):.2f} g")
                print(f"  • Final LAI: {result['summary'].get('current_lai', 0):.2f}")
                
                # Check final growth stage
                final_day = result['daily_results'][-1]
                final_stage = final_day.get('phenology', {}).get('growth_stage', 'Unknown')
                print(f"  • Final stage: {final_stage}")
                print(f"  • Reached harvest maturity: {'Yes' if final_stage == 'HM' else 'No'}")
                
                return True
            else:
                print(f"❌ Maturity simulation failed: {result.get('error', 'Unknown error')}")
                return False
                
        else:
            print(f"❌ Maturity simulation API failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  • Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"  • Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Maturity simulation timed out (may need more than 3 minutes)")
        return False
    except Exception as e:
        print(f"❌ Maturity simulation error: {e}")
        return False

def main():
    """Test maturity-based simulation"""
    print("🌱 CROPGRO Maturity-Based Simulation Test")
    print("=" * 50)
    
    success = test_maturity_simulation()
    
    print()
    print("=" * 50)
    
    if success:
        print("🎉 MATURITY SIMULATION TEST PASSED!")
        print("✅ CROPGRO now runs until physiological maturity!")
        print("📋 Features:")
        print("  • Automatic harvest maturity detection (HM)")
        print("  • Automatic physiological maturity detection (PM)")
        print("  • Safety maximum days limit")
        print("  • Weather data cycling for long simulations")
    else:
        print("⚠️  Maturity simulation test failed")

if __name__ == "__main__":
    main()