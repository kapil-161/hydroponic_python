"""
Parameter Tracking System
Tracks where each parameter is used, how it's used, and what outputs it produces
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
import ast
import inspect
from collections import defaultdict

class ParameterTracker:
    """
    Analyzes parameter usage across models and CSV files
    """

    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = Path(__file__).parent
        else:
            project_root = Path(project_root)

        self.project_root = project_root
        self.input_dir = project_root / "input"
        self.models_dir = project_root / "src" / "models"
        self.simulators_dir = project_root / "src" / "simulations"

        # Parameter usage database
        self.parameters: Dict[str, Dict[str, Any]] = {}
        self.model_usage: Dict[str, List[str]] = defaultdict(list)
        self.parameter_flow: Dict[str, List[str]] = defaultdict(list)
        self.backward_compat_mappings: Dict[str, List[str]] = {}

    def load_all_parameters(self) -> Dict[str, pd.DataFrame]:
        """Load all parameters from CSV files"""
        parameters = {}

        for csv_file in self.input_dir.glob("*.csv"):
            try:
                # Read CSV with comment handling and error tolerance
                df = pd.read_csv(csv_file, comment='#', on_bad_lines='skip')

                # Skip if no columns
                if df.empty or len(df.columns) == 0:
                    continue

                # Find parameter_name column (some CSVs use constant_name)
                param_col = None
                if 'parameter_name' in df.columns:
                    param_col = 'parameter_name'
                elif 'constant_name' in df.columns:
                    param_col = 'constant_name'

                # Clean up comments if parameter name column exists
                if param_col:
                    df = df[~df[param_col].astype(str).str.startswith('#')]

                parameters[csv_file.name] = df
            except Exception as e:
                print(f"Error loading {csv_file.name}: {e}")

        return parameters

    def load_backward_compatibility_mappings(self):
        """Load backward compatibility mappings from parameter_loader.py"""
        loader_path = self.project_root / "src" / "utils" / "parameter_loader.py"

        try:
            with open(loader_path, 'r') as f:
                content = f.read()

            # Find backward_compat_mappings dictionary
            import re
            pattern = r"backward_compat_mappings\s*=\s*\{([^}]+)\}"
            match = re.search(pattern, content, re.DOTALL)

            if match:
                mappings_str = match.group(1)
                # Parse each line like: 'atmospheric_o2': ['photosynthesis_parameters_o2_mmol_mol']
                line_pattern = r"'([^']+)':\s*\[([^\]]+)\]"
                for line_match in re.finditer(line_pattern, mappings_str):
                    param_name = line_match.group(1)
                    mapped_keys_str = line_match.group(2)
                    mapped_keys = [k.strip().strip("'\"") for k in mapped_keys_str.split(',')]
                    self.backward_compat_mappings[param_name] = mapped_keys
        except Exception as e:
            print(f"Warning: Could not load backward compatibility mappings: {e}")

    def extract_parameters_from_csv(self):
        """Extract all parameters from CSV files"""
        csv_files = self.load_all_parameters()

        for csv_file, df in csv_files.items():
            for _, row in df.iterrows():
                # Try different column names for parameter name
                if 'parameter_name' in df.columns:
                    param_name = str(row.get('parameter_name', '')).strip()
                elif 'constant_name' in df.columns:
                    param_name = str(row.get('constant_name', '')).strip()
                else:
                    param_name = str(row.get('parameter', row.get('name', ''))).strip()

                if param_name and not param_name.startswith('#'):
                    self.parameters[param_name] = {
                        'file': csv_file,
                        'value': row.get('value', ''),
                        'unit': row.get('unit', ''),
                        'description': row.get('description', ''),
                        'used_by': [],
                        'produces': [],
                        'equations': []
                    }

    def analyze_model_files(self):
        """Analyze model and simulator files to find parameter usage"""
        # Combine both model files and simulator files
        python_files = []
        for model_file in self.models_dir.glob("*.py"):
            if model_file.name != '__init__.py' and model_file.name != 'base_model.py':
                python_files.append(model_file)
        for simulator_file in self.simulators_dir.glob("*.py"):
            if simulator_file.name != '__init__.py':
                python_files.append(simulator_file)

        for model_file in python_files:
            if model_file.name == '__init__.py' or model_file.name == 'base_model.py':
                continue

            try:
                with open(model_file, 'r') as f:
                    content = f.read()
                    model_name = model_file.stem

                    # Find all parameters used in this model
                    for param_name in self.parameters.keys():
                        # Check direct parameter name usage
                        found_usage = param_name in content

                        # Check if parameter is used through backward compatibility mappings
                        if not found_usage and param_name in self.backward_compat_mappings:
                            for mapped_key in self.backward_compat_mappings[param_name]:
                                # Check for full mapped key: photosynthesis_parameters_o2_mmol_mol
                                if mapped_key in content:
                                    found_usage = True
                                    break
                                # Also check for shortened form used in models: o2_mmol_mol
                                # Extract the part after the category prefix (e.g., photosynthesis_parameters_)
                                if 'parameters_' in mapped_key:
                                    short_form = mapped_key.split('parameters_', 1)[1]
                                    if short_form and short_form in content:
                                        found_usage = True
                                        break

                        if found_usage:
                            self.parameters[param_name]['used_by'].append(model_name)
                            self.model_usage[model_name].append(param_name)

                            # Find the line where it's used
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                # Check both direct usage and mapped keys
                                line_has_param = param_name in line
                                if not line_has_param and param_name in self.backward_compat_mappings:
                                    for mapped_key in self.backward_compat_mappings[param_name]:
                                        # Check full key
                                        if mapped_key in line:
                                            line_has_param = True
                                            break
                                        # Check shortened form
                                        if 'parameters_' in mapped_key:
                                            short_form = mapped_key.split('parameters_', 1)[1]
                                            if short_form and short_form in line:
                                                line_has_param = True
                                                break

                                if line_has_param and not line.strip().startswith('#'):
                                    self.parameters[param_name]['equations'].append({
                                        'model': model_name,
                                        'line': i + 1,
                                        'code': line.strip()
                                    })
            except Exception as e:
                print(f"Error analyzing {model_file.name}: {e}")

    def trace_parameter_flow(self):
        """
        Build parameter flow: input → model → output
        """
        # Model execution order (from simulator)
        execution_order = [
            'phenology_model',
            'root_system_model',
            'water_uptake_model',
            'nutrient_models',
            'leaf_development',
            'stress_models',
            'canopy_architecture',
            'photosynthesis_model',
            'respiration_model',
            'biomass_allocation_model',
            'nitrogen_balance'
        ]

        # Map outputs to models (based on typical output names)
        model_outputs = {
            'phenology_model': ['growth_stage', 'development_index', 'thermal_time'],
            'root_system_model': ['root_length', 'root_distribution', 'root_depth'],
            'water_uptake_model': ['water_uptake', 'transpiration', 'water_stress'],
            'nutrient_models': ['nutrient_uptake', 'nutrient_concentration', 'nutrient_availability'],
            'leaf_development': ['leaf_area', 'leaf_number', 'leaf_morphology'],
            'stress_models': ['stress_factor', 'stress_index', 'damage_rate'],
            'canopy_architecture': ['lai', 'light_interception', 'canopy_height'],
            'photosynthesis_model': ['assimilation_rate', 'photosynthetic_rate', 'co2_fixation'],
            'respiration_model': ['respiration_rate', 'maintenance_respiration', 'growth_respiration'],
            'biomass_allocation_model': ['shoot_biomass', 'root_biomass', 'leaf_biomass'],
            'nitrogen_balance': ['n_uptake', 'n_concentration', 'n_remobilization']
        }

        # Build flow: param → models that use it → outputs they produce
        for param_name, param_info in self.parameters.items():
            flow = []
            for model in param_info.get('used_by', []):
                if model in model_outputs:
                    for output in model_outputs[model]:
                        if param_name not in flow:
                            flow.append({
                                'model': model,
                                'input_param': param_name,
                                'outputs': model_outputs[model]
                            })
            self.parameter_flow[param_name] = flow

    def get_parameter_trace(self, param_name: str) -> Dict[str, Any]:
        """
        Get complete trace for a parameter:
        - Where it comes from (CSV file)
        - Which models use it
        - What equations use it
        - What outputs it produces
        """
        if param_name not in self.parameters:
            return {
                'error': f'Parameter {param_name} not found',
                'available_params': list(self.parameters.keys())
            }

        param = self.parameters[param_name]

        return {
            'parameter_name': param_name,
            'source': {
                'file': param['file'],
                'value': param['value'],
                'unit': param['unit'],
                'description': param['description']
            },
            'used_by_models': list(set(param['used_by'])),
            'equations': param['equations'],
            'produces': self.parameter_flow.get(param_name, []),
            'impact_chain': self._build_impact_chain(param_name)
        }

    def _build_impact_chain(self, param_name: str) -> List[Dict[str, Any]]:
        """
        Build the impact chain: how changing this parameter affects the system
        """
        chain = []
        visited = set()

        def traverse(param, depth=0):
            if depth > 5 or param in visited:  # Prevent infinite loops
                return
            visited.add(param)

            param_info = self.parameters.get(param)
            if not param_info:
                return

            for model in param_info.get('used_by', []):
                chain.append({
                    'depth': depth,
                    'parameter': param,
                    'model': model,
                    'description': f"{param} is used by {model}"
                })

        traverse(param_name)
        return chain

    def get_model_parameters(self, model_name: str) -> Dict[str, Any]:
        """Get all parameters used by a specific model"""
        params = self.model_usage.get(model_name, [])
        return {
            'model': model_name,
            'parameter_count': len(params),
            'parameters': [
                {
                    'name': p,
                    'file': self.parameters[p]['file'],
                    'value': self.parameters[p]['value'],
                    'unit': self.parameters[p]['unit'],
                    'description': self.parameters[p]['description']
                }
                for p in params
            ]
        }

    def get_parameter_impact_analysis(self, param_name: str) -> Dict[str, Any]:
        """
        Detailed analysis of parameter impact:
        - Which models it influences
        - What outputs change as a result
        - Sensitivity level
        """
        trace = self.get_parameter_trace(param_name)

        if 'error' in trace:
            return trace

        return {
            'parameter': param_name,
            'csv_source': trace['source']['file'],
            'current_value': trace['source']['value'],
            'unit': trace['source']['unit'],
            'description': trace['source']['description'],

            'direct_impact': {
                'models_using': trace['used_by_models'],
                'model_count': len(trace['used_by_models'])
            },

            'affected_outputs': self._get_affected_outputs(param_name),

            'execution_flow': self._get_execution_flow(trace['used_by_models']),

            'estimated_sensitivity': self._estimate_sensitivity(param_name),

            'relationships': self._find_parameter_relationships(param_name)
        }

    def _get_affected_outputs(self, param_name: str) -> List[str]:
        """Get all output variables affected by this parameter"""
        affected = set()
        flow = self.parameter_flow.get(param_name, [])
        for item in flow:
            affected.update(item.get('outputs', []))
        return list(affected)

    def _get_execution_flow(self, models: List[str]) -> List[str]:
        """Get the execution order of affected models"""
        execution_order = [
            'phenology_model',
            'root_system_model',
            'water_uptake_model',
            'nutrient_models',
            'leaf_development',
            'stress_models',
            'canopy_architecture',
            'photosynthesis_model',
            'respiration_model',
            'biomass_allocation_model',
            'nitrogen_balance'
        ]

        affected_models = [m for m in execution_order if m in models]
        return affected_models

    def _estimate_sensitivity(self, param_name: str) -> str:
        """Estimate parameter sensitivity based on usage"""
        if param_name not in self.parameters:
            return 'unknown'

        param = self.parameters[param_name]
        usage_count = len(param['used_by']) + len(param['equations'])

        if usage_count == 0:
            return 'unused'
        elif usage_count <= 2:
            return 'low'
        elif usage_count <= 5:
            return 'medium'
        else:
            return 'high'

    def _find_parameter_relationships(self, param_name: str) -> Dict[str, List[str]]:
        """Find other parameters used together with this one"""
        if param_name not in self.parameters:
            return {}

        related_models = self.parameters[param_name]['used_by']
        relationships = defaultdict(set)

        for model in related_models:
            model_params = self.model_usage.get(model, [])
            for other_param in model_params:
                if other_param != param_name:
                    relationships[model].add(other_param)

        return {
            model: list(params)
            for model, params in relationships.items()
        }

    def export_tracking_report(self, output_file: str = None) -> str:
        """Export complete tracking report as JSON"""
        if output_file is None:
            output_file = self.project_root / "parameter_tracking_report.json"

        report = {
            'total_parameters': len(self.parameters),
            'total_models': len(self.model_usage),
            'parameters': {},
            'model_usage': dict(self.model_usage),
            'parameter_flow': dict(self.parameter_flow)
        }

        # Add detailed tracking for each parameter
        for param_name in sorted(self.parameters.keys()):
            report['parameters'][param_name] = self.get_parameter_trace(param_name)

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        return str(output_file)

    def generate_html_report(self, output_file: str = None) -> str:
        """Generate an interactive HTML report"""
        if output_file is None:
            output_file = self.project_root / "parameter_tracking_report.html"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Parameter Tracking Report</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: Arial, sans-serif; background: #f5f5f5; color: #333; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2ecc71; margin-bottom: 20px; }}
                .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-value {{ font-size: 32px; font-weight: bold; color: #2ecc71; }}
                .stat-label {{ font-size: 12px; color: #999; margin-top: 8px; text-transform: uppercase; }}
                .search-box {{ margin: 20px 0; }}
                .search-box input {{ width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px; }}
                .search-box input:focus {{ outline: none; border-color: #2ecc71; }}
                .parameter-card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #2ecc71; }}
                .param-name {{ font-size: 18px; font-weight: bold; color: #2ecc71; margin-bottom: 8px; }}
                .param-meta {{ display: grid; grid-template-columns: 2fr 2fr 2fr; gap: 15px; margin: 10px 0; }}
                .meta-item {{ font-size: 13px; }}
                .meta-label {{ color: #999; font-weight: bold; text-transform: uppercase; }}
                .meta-value {{ color: #333; margin-top: 4px; }}
                .models-list {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0; }}
                .model-tag {{ background: #e8f5e9; color: #2ecc71; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .output-tag {{ background: #e3f2fd; color: #1976d2; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
                .equations {{ background: #f5f5f5; padding: 15px; border-radius: 6px; margin: 10px 0; }}
                .equation {{ font-family: monospace; font-size: 12px; color: #666; margin: 5px 0; border-left: 2px solid #ddd; padding-left: 10px; }}
                .sensitivity {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
                .sensitivity.high {{ background: #ffebee; color: #c62828; }}
                .sensitivity.medium {{ background: #fff3e0; color: #e65100; }}
                .sensitivity.low {{ background: #e8f5e9; color: #2e7d32; }}
                .footer {{ text-align: center; color: #999; margin-top: 40px; padding: 20px; border-top: 1px solid #ddd; }}
                @media (max-width: 768px) {{
                    .stats {{ grid-template-columns: 2fr 2fr; }}
                    .param-meta {{ grid-template-columns: 1fr; }}
                }}
            </style>
            <script>
                function filterParameters() {{
                    const query = document.getElementById('search').value.toLowerCase();
                    const cards = document.querySelectorAll('.parameter-card');
                    cards.forEach(card => {{
                        const text = card.textContent.toLowerCase();
                        card.style.display = text.includes(query) ? 'block' : 'none';
                    }});
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Parameter Tracking Report</h1>
                    <p>Complete analysis of parameter usage, flow, and impact across all models</p>
                </div>

                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">{len(self.parameters)}</div>
                        <div class="stat-label">Total Parameters</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(self.model_usage)}</div>
                        <div class="stat-label">Models</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len([p for p in self.parameters.values() if p['used_by']])}</div>
                        <div class="stat-label">Used Parameters</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len([p for p in self.parameters.values() if not p['used_by']])}</div>
                        <div class="stat-label">Unused Parameters</div>
                    </div>
                </div>

                <div class="search-box">
                    <input type="text" id="search" placeholder="Search parameters by name or description..." onkeyup="filterParameters()">
                </div>
        """

        # Add parameter cards
        for param_name in sorted(self.parameters.keys()):
            trace = self.get_parameter_trace(param_name)
            source = trace['source']
            sensitivity = self._estimate_sensitivity(param_name)

            models = trace['used_by_models']
            outputs = self._get_affected_outputs(param_name)

            html_content += f"""
                <div class="parameter-card">
                    <div class="param-name">{param_name}</div>

                    <div class="param-meta">
                        <div class="meta-item">
                            <div class="meta-label">Source</div>
                            <div class="meta-value">{source['file']}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Current Value</div>
                            <div class="meta-value">{source['value']} {source['unit']}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Sensitivity</div>
                            <div class="sensitivity {sensitivity}">{sensitivity.upper()}</div>
                        </div>
                    </div>

                    <div class="meta-item">
                        <div class="meta-label">Description</div>
                        <div class="meta-value">{source['description']}</div>
                    </div>

                    {'<div><div class="meta-label">Used By Models</div><div class="models-list">' + ''.join([f'<span class="model-tag">{m}</span>' for m in models]) + '</div></div>' if models else ''}

                    {'<div><div class="meta-label">Produces Outputs</div><div class="models-list">' + ''.join([f'<span class="output-tag">{o}</span>' for o in outputs]) + '</div></div>' if outputs else ''}

                    {'<div class="equations"><div class="meta-label">Usage in Code</div>' + ''.join([f'<div class="equation"><strong>{eq["model"]}:{eq["line"]}</strong> {eq["code"][:80]}</div>' for eq in trace["equations"][:3]]) + '</div>' if trace["equations"] else ''}
                </div>
            """

        html_content += """
                <div class="footer">
                    <p>Generated by Parameter Tracking System</p>
                    <p>This report shows where each parameter is used, how it's used, and what outputs it produces</p>
                </div>
            </div>
        </body>
        </html>
        """

        with open(output_file, 'w') as f:
            f.write(html_content)

        return str(output_file)


def main():
    """Run parameter tracking analysis"""
    tracker = ParameterTracker()

    print("🔍 Loading parameters from CSV files...")
    tracker.extract_parameters_from_csv()
    print(f"✅ Loaded {len(tracker.parameters)} parameters")

    print("\n🔗 Loading backward compatibility mappings...")
    tracker.load_backward_compatibility_mappings()
    print(f"✅ Loaded {len(tracker.backward_compat_mappings)} backward compatibility mappings")

    print("\n📊 Analyzing model files...")
    tracker.analyze_model_files()
    print(f"✅ Analyzed {len(tracker.model_usage)} models")

    print("\n🔗 Building parameter flow...")
    tracker.trace_parameter_flow()

    print("\n📈 Generating reports...")
    json_file = tracker.export_tracking_report()
    print(f"✅ JSON report: {json_file}")

    html_file = tracker.generate_html_report()
    print(f"✅ HTML report: {html_file}")

    print("\n" + "="*60)
    print("PARAMETER TRACKING COMPLETE")
    print("="*60)
    print(f"Total Parameters: {len(tracker.parameters)}")
    print(f"Total Models: {len(tracker.model_usage)}")

    # Show some example traces
    print("\n📍 Example Parameter Traces:")
    print("-" * 60)

    sample_params = list(tracker.parameters.keys())[:3]
    for param in sample_params:
        trace = tracker.get_parameter_trace(param)
        print(f"\n{param}:")
        print(f"  Value: {trace['source']['value']} {trace['source']['unit']}")
        print(f"  Used by: {', '.join(trace['used_by_models'])}")
        print(f"  Produces: {', '.join(tracker._get_affected_outputs(param))}")


if __name__ == '__main__':
    main()
