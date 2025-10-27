"""
Flask backend for hydroponic UI
Serves model graph, parameters, and manages simulations
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
import os
from pathlib import Path
import subprocess
import threading
from datetime import datetime
from parameter_tracker import ParameterTracker
from advanced_ui_api import create_advanced_api

app = Flask(__name__)
CORS(app)

# Paths
PROJECT_ROOT = Path(__file__).parent
CSV_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
SIMULATIONS_DIR = PROJECT_ROOT / "simulations_history"
SIMULATIONS_DIR.mkdir(exist_ok=True)

# Model definitions - the 12 biological models with their relationships
MODELS = {
    "phenology": {
        "name": "Phenology",
        "description": "Plant development stages and growth phases",
        "category": "Growth",
        "inputs": ["temperature", "day_length"],
        "outputs": ["growth_stage", "development_rate"],
        "color": "#FF6B6B"
    },
    "root_system": {
        "name": "Root System",
        "description": "Root growth, distribution, and development",
        "category": "Structural",
        "inputs": ["soil_conditions", "water_availability", "growth_stage"],
        "outputs": ["root_length", "root_distribution", "root_density"],
        "color": "#8B4513"
    },
    "water_uptake": {
        "name": "Water Uptake",
        "description": "Water extraction from soil and transpiration",
        "category": "Resource",
        "inputs": ["root_system", "water_availability", "vpd"],
        "outputs": ["water_uptake", "transpiration"],
        "color": "#4ECDC4"
    },
    "nutrient_models": {
        "name": "Nutrient Models",
        "description": "Uptake and availability of macro/micronutrients",
        "category": "Resource",
        "inputs": ["water_uptake", "root_system", "nutrient_concentration"],
        "outputs": ["nutrient_uptake", "nutrient_availability"],
        "color": "#95E1D3"
    },
    "leaf_development": {
        "name": "Leaf Development",
        "description": "Leaf morphology, expansion, and senescence",
        "category": "Structural",
        "inputs": ["phenology", "nutrient_uptake", "stress_factors"],
        "outputs": ["leaf_area", "leaf_number", "leaf_morphology"],
        "color": "#90EE90"
    },
    "stress_models": {
        "name": "Stress Models",
        "description": "7 stress types: water, temperature, nutrient, light, salinity, O2, pH",
        "category": "Environmental",
        "inputs": ["water_uptake", "temperature", "nutrient_uptake", "light", "salinity"],
        "outputs": ["stress_factor", "damage_rate", "stress_index"],
        "color": "#FFD700"
    },
    "canopy": {
        "name": "Canopy Architecture",
        "description": "Leaf Area Index, light interception, and structure",
        "category": "Structural",
        "inputs": ["leaf_development", "stress_factors"],
        "outputs": ["lai", "light_interception", "canopy_structure"],
        "color": "#228B22"
    },
    "photosynthesis": {
        "name": "Photosynthesis",
        "description": "CO2 assimilation and light response curves",
        "category": "Growth",
        "inputs": ["canopy", "light", "temperature", "co2"],
        "outputs": ["assimilation_rate", "photosynthetic_output"],
        "color": "#FFB347"
    },
    "respiration": {
        "name": "Respiration",
        "description": "Maintenance and growth respiration",
        "category": "Growth",
        "inputs": ["biomass", "temperature", "phenology"],
        "outputs": ["respiration_rate", "respiration_cost"],
        "color": "#FFA07A"
    },
    "biomass_allocation": {
        "name": "Biomass Allocation",
        "description": "Partitioning of assimilates to organs",
        "category": "Growth",
        "inputs": ["photosynthesis", "respiration", "phenology", "stress_factors"],
        "outputs": ["shoot_biomass", "root_biomass", "leaf_biomass", "fruit_biomass"],
        "color": "#DEB887"
    },
    "nitrogen_balance": {
        "name": "Nitrogen Balance",
        "description": "N pool tracking and remobilization",
        "category": "Resource",
        "inputs": ["nutrient_uptake", "phenology", "biomass_allocation"],
        "outputs": ["n_uptake", "n_remobilization", "n_concentration"],
        "color": "#B0C4DE"
    }
}

# Data flow mapping - which models feed into which
CONNECTIONS = [
    ("phenology", "root_system"),
    ("phenology", "leaf_development"),
    ("phenology", "photosynthesis"),
    ("phenology", "respiration"),
    ("phenology", "biomass_allocation"),
    ("phenology", "nitrogen_balance"),
    ("root_system", "water_uptake"),
    ("root_system", "nutrient_models"),
    ("water_uptake", "stress_models"),
    ("water_uptake", "nutrient_models"),
    ("nutrient_models", "leaf_development"),
    ("nutrient_models", "stress_models"),
    ("nutrient_models", "nitrogen_balance"),
    ("leaf_development", "canopy"),
    ("leaf_development", "stress_models"),
    ("stress_models", "canopy"),
    ("stress_models", "leaf_development"),
    ("stress_models", "biomass_allocation"),
    ("canopy", "photosynthesis"),
    ("photosynthesis", "biomass_allocation"),
    ("respiration", "biomass_allocation"),
    ("biomass_allocation", "leaf_development"),
    ("biomass_allocation", "root_system"),
    ("nitrogen_balance", "nutrient_models"),
]

# ==================== API ENDPOINTS ====================

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get all models with their properties"""
    return jsonify(MODELS)

@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Get model dependency graph with rich connection data"""
    nodes = []
    edges = []

    # Calculate node depths (how many steps from input models)
    depths = {}
    input_models = set()
    output_models = set()

    # First pass: identify input and output nodes
    for source, target in CONNECTIONS:
        output_models.add(target)

    input_models = set(MODELS.keys()) - output_models

    # Calculate depths using BFS
    from collections import deque
    queue = deque([(model, 0) for model in input_models])
    visited = set(input_models)

    while queue:
        current, depth = queue.popleft()
        depths[current] = depth

        # Find all models this one connects to
        for source, target in CONNECTIONS:
            if source == current and target not in visited:
                visited.add(target)
                queue.append((target, depth + 1))

    # Create nodes with depth information
    x_pos = 0
    y_pos = 0
    for model_id, model_info in MODELS.items():
        depth = depths.get(model_id, 0)

        nodes.append({
            "id": model_id,
            "label": model_info["name"],
            "category": model_info["category"],
            "color": model_info["color"],
            "description": model_info["description"],
            "depth": depth,
            "x": x_pos,
            "y": y_pos,
            "is_input": model_id in input_models,
            "is_output": model_id in output_models,
            "input_count": sum(1 for s, t in CONNECTIONS if t == model_id),
            "output_count": sum(1 for s, t in CONNECTIONS if s == model_id)
        })
        x_pos += 200
        if x_pos > 1000:
            x_pos = 0
            y_pos += 200

    # Create edges with parameter flow information
    tracker = get_tracker()

    for source, target in CONNECTIONS:
        # Find parameters that flow from source to target
        source_params = tracker.model_usage.get(source, [])
        target_params = set(tracker.model_usage.get(target, []))
        flow_params = [p for p in source_params if p in target_params]

        # Count connections depth
        strength = len(flow_params)

        edges.append({
            "source": source,
            "target": target,
            "type": "arrow",
            "strength": strength,
            "parameter_count": len(flow_params),
            "parameters": flow_params[:5],  # Top 5 parameters
            "is_major": strength > 5  # Major connection if many parameters
        })

    return jsonify({
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_models": len(nodes),
            "total_connections": len(edges),
            "max_depth": max(depths.values()) if depths else 0,
            "input_models": len(input_models),
            "output_models": len(output_models)
        }
    })

@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """Get all parameters from CSV files"""
    parameters = {}

    # List of CSV files to load
    csv_files = [
        "master_parameters.csv",
        "constants.csv",
        "phenology.csv",
        "photo.csv",
        "respiration.csv",
        "allocation.csv",
        "stress.csv",
        "water.csv",
        "roots.csv",
        "canopy.csv",
        "leaf.csv",
        "nutrient.csv",
        "nitrogen_balance.csv",
        "initials.csv",
        "genetics.csv"
    ]

    for csv_file in csv_files:
        filepath = CSV_DIR / csv_file
        if filepath.exists():
            try:
                # Read CSV with comment handling and error tolerance
                df = pd.read_csv(filepath, comment='#', on_bad_lines='skip')

                # Convert to dictionary format
                file_params = {}
                for _, row in df.iterrows():
                    # Try different column names for parameter name
                    if 'parameter_name' in df.columns:
                        param_name = row.get('parameter_name', '')
                    elif 'constant_name' in df.columns:
                        param_name = row.get('constant_name', '')
                    else:
                        param_name = row.get('parameter', row.get('name', ''))

                    # Skip empty parameter names
                    if not param_name or pd.isna(param_name):
                        continue

                    param_value = row.get('value', '')
                    file_params[param_name] = {
                        'value': param_value,
                        'description': row.get('description', ''),
                        'unit': row.get('unit', ''),
                        'min': row.get('min', ''),
                        'max': row.get('max', ''),
                        'file': csv_file
                    }
                parameters[csv_file] = file_params
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")

    return jsonify(parameters)

@app.route('/api/parameters/<file_name>', methods=['GET'])
def get_parameters_by_file(file_name):
    """Get parameters from a specific CSV file"""
    filepath = CSV_DIR / file_name

    if not filepath.exists():
        return jsonify({"error": f"File {file_name} not found"}), 404

    try:
        # Read CSV with comment handling and error tolerance
        df = pd.read_csv(filepath, comment='#', on_bad_lines='skip')

        params = []
        for _, row in df.iterrows():
            # Determine parameter name column
            if 'parameter_name' in df.columns:
                param_name = row.get('parameter_name', '')
            elif 'constant_name' in df.columns:
                param_name = row.get('constant_name', '')
            else:
                param_name = row.get('parameter', row.get('name', ''))

            # Skip empty names
            if not param_name or pd.isna(param_name):
                continue

            params.append({
                'name': param_name,
                'value': row.get('value', ''),
                'description': row.get('description', ''),
                'unit': row.get('unit', ''),
                'min': row.get('min', ''),
                'max': row.get('max', '')
            })
        return jsonify(params)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parameters/<file_name>/<param_name>', methods=['PUT'])
def update_parameter(file_name, param_name):
    """Update a single parameter value"""
    filepath = CSV_DIR / file_name

    if not filepath.exists():
        return jsonify({"error": f"File {file_name} not found"}), 404

    try:
        data = request.json
        new_value = data.get('value')

        df = pd.read_csv(filepath)
        # Find and update the parameter
        param_col = 'parameter' if 'parameter' in df.columns else 'name'
        mask = df[param_col] == param_name

        if not mask.any():
            return jsonify({"error": f"Parameter {param_name} not found"}), 404

        df.loc[mask, 'value'] = new_value
        df.to_csv(filepath, index=False)

        return jsonify({
            "success": True,
            "message": f"Parameter {param_name} updated to {new_value}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulation/run', methods=['POST'])
def run_simulation():
    """Run simulation with current parameters"""
    try:
        # Create a new simulation run directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sim_dir = SIMULATIONS_DIR / f"sim_{timestamp}"
        sim_dir.mkdir(exist_ok=True)

        # Run the simulator
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / "main.py")],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": "Simulation completed successfully",
                "timestamp": timestamp,
                "output": result.stdout
            })
        else:
            return jsonify({
                "success": False,
                "error": result.stderr
            }), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Simulation timeout"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulation/results', methods=['GET'])
def get_simulation_results():
    """Get latest simulation results"""
    try:
        results = {}

        # Read output CSV files
        output_files = [
            "simulation_results.csv",
            "biomass_allocation.csv",
            "photosynthesis.csv",
            "water_uptake.csv",
            "nitrogen_balance.csv"
        ]

        for output_file in output_files:
            filepath = OUTPUT_DIR / output_file
            if filepath.exists():
                df = pd.read_csv(filepath)
                results[output_file] = df.head(50).to_dict('records')

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "models_count": len(MODELS),
        "csv_dir": str(CSV_DIR),
        "output_dir": str(OUTPUT_DIR)
    })

# ==================== UTILITY ENDPOINTS ====================

@app.route('/api/models/<model_id>', methods=['GET'])
def get_model_details(model_id):
    """Get detailed info about a specific model"""
    if model_id not in MODELS:
        return jsonify({"error": "Model not found"}), 404

    model = MODELS[model_id]

    # Find connected models
    connected_inputs = [s for s, t in CONNECTIONS if t == model_id]
    connected_outputs = [t for s, t in CONNECTIONS if s == model_id]

    return jsonify({
        **model,
        "connected_inputs": [MODELS[m]["name"] for m in connected_inputs],
        "connected_outputs": [MODELS[m]["name"] for m in connected_outputs]
    })

# ==================== PARAMETER TRACKING ENDPOINTS ====================

# Initialize parameter tracker (lazy load for performance)
_tracker = None

def get_tracker():
    global _tracker
    if _tracker is None:
        _tracker = ParameterTracker(str(PROJECT_ROOT))
        _tracker.extract_parameters_from_csv()
        _tracker.analyze_model_files()
        _tracker.trace_parameter_flow()
    return _tracker

@app.route('/api/parameter-tracking/trace/<param_name>', methods=['GET'])
def trace_parameter(param_name):
    """Get complete trace for a parameter"""
    try:
        tracker = get_tracker()
        trace = tracker.get_parameter_trace(param_name)
        return jsonify(trace)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parameter-tracking/impact/<param_name>', methods=['GET'])
def parameter_impact(param_name):
    """Get detailed impact analysis for a parameter"""
    try:
        tracker = get_tracker()
        analysis = tracker.get_parameter_impact_analysis(param_name)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parameter-tracking/model/<model_name>', methods=['GET'])
def model_parameters(model_name):
    """Get all parameters used by a specific model"""
    try:
        tracker = get_tracker()
        params = tracker.get_model_parameters(model_name)
        return jsonify(params)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parameter-tracking/summary', methods=['GET'])
def tracking_summary():
    """Get summary of parameter tracking"""
    try:
        tracker = get_tracker()

        used_params = [p for p in tracker.parameters.values() if p['used_by']]
        unused_params = [p for p in tracker.parameters.values() if not p['used_by']]

        return jsonify({
            'total_parameters': len(tracker.parameters),
            'used_parameters': len(used_params),
            'unused_parameters': len(unused_params),
            'total_models': len(tracker.model_usage),
            'models': list(tracker.model_usage.keys()),
            'unused_params_list': [p for p in tracker.parameters.keys() if not tracker.parameters[p]['used_by']]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parameter-tracking/search', methods=['GET'])
def search_parameters():
    """Search parameters by name or description"""
    try:
        query = request.args.get('q', '').lower()
        tracker = get_tracker()

        results = []
        for param_name, param_info in tracker.parameters.items():
            if (query in param_name.lower() or
                query in param_info['description'].lower()):
                results.append({
                    'name': param_name,
                    'file': param_info['file'],
                    'value': param_info['value'],
                    'description': param_info['description'],
                    'used_by': param_info['used_by'],
                    'usage_count': len(param_info['used_by'])
                })

        return jsonify({
            'query': query,
            'results': sorted(results, key=lambda x: x['usage_count'], reverse=True)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parameter-tracking/flow', methods=['GET'])
def parameter_flow():
    """Get parameter flow (input → model → output)"""
    try:
        tracker = get_tracker()

        flow_data = {}
        for param_name in sorted(tracker.parameters.keys()):
            trace = tracker.get_parameter_trace(param_name)
            flow_data[param_name] = {
                'source_file': trace['source']['file'],
                'value': trace['source']['value'],
                'models': trace['used_by_models'],
                'outputs': tracker._get_affected_outputs(param_name)
            }

        return jsonify(flow_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Initialize advanced API
print("Initializing advanced UI API...")
app = create_advanced_api(app, str(PROJECT_ROOT))

if __name__ == '__main__':
    print(f"Starting Hydroponic UI Backend")
    print(f"CSV Directory: {CSV_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Advanced API endpoints available at /api/advanced/")
    print(f"Backend running at http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
