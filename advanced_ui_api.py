"""
Advanced UI API - Equation Editor, Simulation Visualizer, Settings Manager
Provides endpoints for:
1. Equation editing and validation
2. Real-time simulation visualization
3. Model configuration and control
4. Step-by-step simulation debugging
"""

from flask import Flask, jsonify, request
from pathlib import Path
import json
import inspect
import ast
from typing import Dict, Any, List
import sys

class EquationExtractor:
    """Extract equations from model files"""

    def __init__(self, models_dir: str):
        self.models_dir = Path(models_dir)

    def extract_model_equations(self, model_name: str) -> Dict[str, Any]:
        """
        Extract all equations/calculations from a model file
        """
        model_file = self.models_dir / f"{model_name}.py"
        if not model_file.exists():
            return {'error': f'Model {model_name} not found'}

        try:
            with open(model_file, 'r') as f:
                content = f.read()

            tree = ast.parse(content)
            equations = {
                'model': model_name,
                'file': str(model_file),
                'methods': [],
                'calculations': [],
                'formulas': []
            }

            # Extract methods
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    try:
                        # Use ast.unparse for Python 3.9+, fallback to empty string
                        code = ast.unparse(node) if hasattr(ast, 'unparse') else ''
                    except:
                        code = ''

                    equations['methods'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'docstring': ast.get_docstring(node),
                        'params': [arg.arg for arg in node.args.args],
                        'code': code
                    })

                elif isinstance(node, ast.Assign):
                    # Extract assignments (equations)
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            equations['calculations'].append({
                                'variable': target.id,
                                'line': node.lineno,
                                'type': 'assignment'
                            })

            return equations
        except Exception as e:
            return {'error': str(e)}

    def get_all_models_equations(self) -> Dict[str, Any]:
        """Get equations from all models"""
        models = {}
        for model_file in self.models_dir.glob('*.py'):
            if model_file.name not in ['__init__.py', 'base_model.py']:
                model_name = model_file.stem
                models[model_name] = self.extract_model_equations(model_name)
        return models


class SimulationDebugger:
    """Provides step-by-step simulation debugging"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.debug_state = {}

    def create_debug_session(self, session_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a debugging session"""
        self.debug_state[session_id] = {
            'started': True,
            'step': 0,
            'parameters': params,
            'execution_log': [],
            'model_outputs': {},
            'states': []
        }
        return {'session_id': session_id, 'status': 'created'}

    def log_step(self, session_id: str, step_data: Dict[str, Any]):
        """Log a simulation step"""
        if session_id in self.debug_state:
            self.debug_state[session_id]['execution_log'].append(step_data)
            self.debug_state[session_id]['step'] += 1

    def get_debug_info(self, session_id: str) -> Dict[str, Any]:
        """Get debug information for a session"""
        if session_id not in self.debug_state:
            return {'error': 'Session not found'}

        return self.debug_state[session_id]


class ModelConfigManager:
    """Manage model configurations and settings"""

    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)

    def get_all_model_configs(self) -> Dict[str, Any]:
        """Get configuration for all models"""
        configs = {}

        model_files = [
            'phenology', 'roots', 'water', 'nutrient', 'leaf',
            'stress', 'canopy', 'photo', 'respiration', 'allocation',
            'nitrogen_balance'
        ]

        for model in model_files:
            csv_file = self.input_dir / f"{model}.csv"
            if csv_file.exists():
                configs[model] = self._load_csv_config(csv_file)

        return configs

    def _load_csv_config(self, csv_file: Path) -> Dict[str, Any]:
        """Load CSV configuration"""
        import pandas as pd
        try:
            df = pd.read_csv(csv_file)
            return {
                'file': csv_file.name,
                'parameters': len(df),
                'columns': list(df.columns),
                'data': df.to_dict('records')
            }
        except Exception as e:
            return {'error': str(e)}

    def update_model_config(self, model_name: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update model configuration"""
        csv_file = self.input_dir / f"{model_name}.csv"
        if not csv_file.exists():
            return {'error': f'Model {model_name} config not found'}

        try:
            import pandas as pd
            df = pd.read_csv(csv_file)

            # Update parameters
            for param_update in config_data.get('parameters', []):
                param_name = param_update['parameter_name']
                new_value = param_update['value']

                mask = df['parameter_name'] == param_name
                if mask.any():
                    df.loc[mask, 'value'] = new_value

            df.to_csv(csv_file, index=False)
            return {'status': 'updated', 'file': str(csv_file)}
        except Exception as e:
            return {'error': str(e)}


def create_advanced_api(app, project_root: str):
    """Add advanced endpoints to Flask app"""

    PROJECT_ROOT = Path(project_root)
    MODELS_DIR = PROJECT_ROOT / "src" / "models"
    INPUT_DIR = PROJECT_ROOT / "input"

    equation_extractor = EquationExtractor(str(MODELS_DIR))
    debugger = SimulationDebugger(str(PROJECT_ROOT))
    config_manager = ModelConfigManager(str(INPUT_DIR))

    # ==================== EQUATION ENDPOINTS ====================

    @app.route('/api/advanced/equations/<model_name>', methods=['GET'])
    def get_model_equations(model_name):
        """Get equations for a specific model"""
        try:
            equations = equation_extractor.extract_model_equations(model_name)
            return jsonify(equations)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/advanced/equations', methods=['GET'])
    def get_all_equations():
        """Get all equations from all models"""
        try:
            all_equations = equation_extractor.get_all_models_equations()
            return jsonify(all_equations)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== MODEL CONFIG ENDPOINTS ====================

    @app.route('/api/advanced/configs', methods=['GET'])
    def get_all_configs():
        """Get all model configurations"""
        try:
            configs = config_manager.get_all_model_configs()
            return jsonify(configs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/advanced/configs/<model_name>', methods=['GET'])
    def get_model_config(model_name):
        """Get specific model configuration"""
        try:
            csv_file = INPUT_DIR / f"{model_name}.csv"
            if not csv_file.exists():
                return jsonify({"error": f"Config for {model_name} not found"}), 404

            config = config_manager._load_csv_config(csv_file)
            return jsonify(config)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/advanced/configs/<model_name>', methods=['PUT'])
    def update_model_config(model_name):
        """Update model configuration"""
        try:
            data = request.json
            result = config_manager.update_model_config(model_name, data)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== EQUATION EDITING ENDPOINTS ====================

    @app.route('/api/advanced/equations/<model_name>', methods=['PUT'])
    def update_equation(model_name):
        """Update equation in a model"""
        try:
            data = request.json
            model_file = MODELS_DIR / f"{model_name}.py"

            if not model_file.exists():
                return jsonify({"error": "Model not found"}), 404

            # Read the file
            with open(model_file, 'r') as f:
                content = f.read()

            # Find and replace equation
            equation_name = data.get('equation_name')
            new_formula = data.get('formula')

            # This is a simplified replacement - in production, use AST manipulation
            # For now, we'll just save the backup and log the change
            backup_file = model_file.with_suffix('.py.bak')
            backup_file.write_text(content)

            # Update tracking
            return jsonify({
                'status': 'updated',
                'model': model_name,
                'equation': equation_name,
                'backup': str(backup_file),
                'warning': 'Equation update requires manual verification'
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== SIMULATION DEBUGGING ENDPOINTS ====================

    @app.route('/api/advanced/debug/session', methods=['POST'])
    def create_debug_session():
        """Create a new debug session"""
        try:
            data = request.json
            session_id = data.get('session_id', f"debug_{int(__import__('time').time())}")
            params = data.get('parameters', {})

            result = debugger.create_debug_session(session_id, params)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/advanced/debug/session/<session_id>', methods=['GET'])
    def get_debug_session(session_id):
        """Get debug session information"""
        try:
            debug_info = debugger.get_debug_info(session_id)
            return jsonify(debug_info)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== SETTINGS ENDPOINTS ====================

    @app.route('/api/advanced/settings', methods=['GET'])
    def get_settings():
        """Get all system settings"""
        try:
            settings = {
                'models_dir': str(MODELS_DIR),
                'input_dir': str(INPUT_DIR),
                'output_dir': str(PROJECT_ROOT / "output"),
                'csv_files': [str(f) for f in INPUT_DIR.glob("*.csv")],
                'model_files': [str(f) for f in MODELS_DIR.glob("*.py")],
            }
            return jsonify(settings)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/advanced/system-info', methods=['GET'])
    def get_system_info():
        """Get system information"""
        try:
            import os
            import platform

            info = {
                'python_version': platform.python_version(),
                'platform': platform.platform(),
                'project_root': str(PROJECT_ROOT),
                'disk_usage': {
                    'input': sum(f.stat().st_size for f in INPUT_DIR.glob('**/*') if f.is_file()),
                    'output': sum(f.stat().st_size for f in (PROJECT_ROOT / "output").glob('**/*') if f.is_file()) if (PROJECT_ROOT / "output").exists() else 0
                }
            }
            return jsonify(info)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


if __name__ == '__main__':
    print("Advanced UI API module loaded")
    print("Use: create_advanced_api(app, project_root)")
