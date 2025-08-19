#!/usr/bin/env python3
"""
Test script for CROPGRO Web API
Tests the web interface functionality without opening a browser
"""

import requests
import json
from datetime import datetime, timedelta

def test_defaults_api():
    """Test the defaults API endpoint"""
    print("🧪 Testing defaults API...")
    
    response = requests.get('http://localhost:5001/api/defaults')
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Defaults API working!")
        print(f"  • Available cultivars: {len(data['cultivars'])}")
        print(f"  • Default nutrients: {len(data['nutrients'])}")
        print(f"  • System type: {data['system']['system_type']}")
        return True
    else:
        print(f"❌ Defaults API failed: {response.status_code}")
        return False

def test_simulation_api():
    """Test the simulation API endpoint"""
    print("🧪 Testing simulation API...")
    
    # Create minimal test data
    test_data = {
        "simulation": {
            "cultivar_id": "HYDRO_001",
            "simulation_days": 3
        },
        "system": {
            "system_id": "TEST_001",
            "crop_id": "LETTUCE_001",
            "location_id": "GREENHOUSE_001",
            "tank_volume": 1500.0,
            "flow_rate": 50.0,
            "system_type": "NFT",
            "system_area": 10.0,
            "n_plants": 48,
            "description": "API Test System"
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
        print("  • Sending simulation request...")
        response = requests.post(
            'http://localhost:5001/api/simulate',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=60  # 60 second timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success', False):
                print("✅ Simulation API working!")
                print(f"  • Cultivar: {result['metadata']['cultivar_name']}")
                print(f"  • Total days: {result['metadata']['total_days']}")
                print(f"  • Models used: {len(result['metadata']['models_used'])}")
                print(f"  • Final biomass: {result['summary'].get('total_biomass_g', 0):.2f} g")
                print(f"  • Daily results: {len(result['daily_results'])} entries")
                return True
            else:
                print(f"❌ Simulation failed: {result.get('error', 'Unknown error')}")
                return False
                
        else:
            print(f"❌ Simulation API failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  • Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"  • Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Simulation timed out (this might be normal for complex simulations)")
        return False
    except Exception as e:
        print(f"❌ Simulation API error: {e}")
        return False

def main():
    """Run all API tests"""
    print("🌱 CROPGRO Web API Test Suite")
    print("=" * 50)
    
    # Test defaults first
    defaults_ok = test_defaults_api()
    
    if not defaults_ok:
        print("❌ Defaults API failed - skipping simulation test")
        return
    
    print()
    
    # Test simulation
    simulation_ok = test_simulation_api()
    
    print()
    print("=" * 50)
    
    if defaults_ok and simulation_ok:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Web UI is ready for use at http://localhost:5001")
        print("📋 Features available:")
        print("  • Comprehensive input forms")
        print("  • Real-time simulation")
        print("  • Advanced CROPGRO modeling")
        print("  • Interactive charts and visualizations")
        print("  • Detailed scientific outputs")
        print("  • Export functionality (CSV/JSON)")
    else:
        print("⚠️  Some tests failed - check the application")

if __name__ == "__main__":
    main()