"""
Intelligent Parameter Calibration System for Hydroponic Simulation

This system automatically:
1. Analyzes observed data to determine which parameters need calibration
2. Maps observed variables to relevant input parameters
3. Optimizes parameters using advanced algorithms
4. Updates input CSV files with calibrated values
5. Validates results and reports improvements
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.optimize import differential_evolution, minimize
from typing import Dict, List, Tuple, Optional
import subprocess
import json
from datetime import datetime


class IntelligentCalibrator:
    """
    Intelligent calibration system that automatically identifies and calibrates
    parameters based on observed data type.
    """

    # Map observed variables to relevant parameters
    PARAMETER_MAPPINGS = {
        'biomass': {
            'primary': [
                ('photo.csv', 'vcmax_25'),
                ('photo.csv', 'jmax_25'),
                ('photo.csv', 'alpha'),
                ('allocation.csv', 'allocation_efficiency'),
            ],
            'secondary': [
                ('photo.csv', 'rd_25'),
                ('respiration.csv', 'growth_respiration_coefficient'),
                ('allocation.csv', 'vegetative_leaf_allocation'),
                ('allocation.csv', 'vegetative_root_allocation'),
            ]
        },
        'leaf_biomass': {
            'primary': [
                ('allocation.csv', 'vegetative_leaf_allocation'),
                ('allocation.csv', 'carbon_allocation_leaves'),
                ('photo.csv', 'vcmax_25'),
            ],
            'secondary': [
                ('leaf.csv', 'leaf_expansion_rate_base'),
                ('canopy.csv', 'sla_base'),
            ]
        },
        'root_biomass': {
            'primary': [
                ('allocation.csv', 'vegetative_root_allocation'),
                ('allocation.csv', 'carbon_allocation_roots'),
                ('roots.csv', 'root_growth_rate_max'),
            ],
            'secondary': [
                ('roots.csv', 'root_elongation_rate'),
            ]
        },
        'lai': {
            'primary': [
                ('canopy.csv', 'sla_base'),
                ('allocation.csv', 'vegetative_leaf_allocation'),
                ('leaf.csv', 'leaf_expansion_rate_base'),
            ],
            'secondary': [
                ('photo.csv', 'vcmax_25'),
            ]
        },
        'leaf_area': {
            'primary': [
                ('leaf.csv', 'leaf_expansion_rate_base'),
                ('canopy.csv', 'sla_base'),
            ],
            'secondary': [
                ('genetics.csv', 'SIZLF'),
            ]
        },
        'tissue_nitrogen': {
            'primary': [
                ('nutrient.csv', 'kinetics_n_no3_vmax'),
                ('nutrient.csv', 'kinetics_n_nh4_vmax'),
                ('nitrogen_balance.csv', 'allocation_fraction_leaves'),
            ],
            'secondary': [
                ('nutrient.csv', 'kinetics_n_no3_km'),
                ('nitrogen_balance.csv', 'nitrogen_use_efficiency_max'),
            ]
        },
        'nutrient_uptake_N': {
            'primary': [
                ('nutrient.csv', 'kinetics_n_no3_vmax'),
                ('nutrient.csv', 'kinetics_n_nh4_vmax'),
                ('nutrient.csv', 'kinetics_n_no3_km'),
            ],
            'secondary': [
                ('roots.csv', 'root_surface_area_specific'),
                ('nutrient.csv', 'temperature_q10'),
            ]
        },
        'nutrient_uptake_P': {
            'primary': [
                ('nutrient.csv', 'kinetics_p_po4_vmax'),
                ('nutrient.csv', 'kinetics_p_po4_km'),
            ],
            'secondary': [
                ('roots.csv', 'root_surface_area_specific'),
            ]
        },
        'nutrient_uptake_K': {
            'primary': [
                ('nutrient.csv', 'kinetics_k_vmax'),
                ('nutrient.csv', 'kinetics_k_km'),
            ],
            'secondary': [
                ('roots.csv', 'root_surface_area_specific'),
            ]
        },
    }

    # Parameter bounds for optimization (min, max multipliers of current value)
    PARAMETER_BOUNDS = {
        'vcmax_25': (0.1, 10.0),
        'jmax_25': (0.1, 10.0),
        'alpha': (0.5, 2.0),
        'rd_25': (0.1, 5.0),
        'allocation_efficiency': (0.2, 0.9),
        'vegetative_leaf_allocation': (0.3, 0.8),
        'vegetative_root_allocation': (0.1, 0.4),
        'carbon_allocation_leaves': (0.4, 0.8),
        'carbon_allocation_roots': (0.1, 0.4),
        'kinetics_n_no3_vmax': (0.1, 100.0),
        'kinetics_n_nh4_vmax': (0.1, 100.0),
        'kinetics_p_po4_vmax': (0.1, 100.0),
        'kinetics_k_vmax': (0.1, 100.0),
        'kinetics_n_no3_km': (0.1, 10.0),
        'kinetics_n_nh4_km': (0.1, 10.0),
        'kinetics_p_po4_km': (0.1, 10.0),
        'kinetics_k_km': (0.1, 10.0),
        'sla_base': (0.5, 2.0),
        'leaf_expansion_rate_base': (0.1, 10.0),
        'root_growth_rate_max': (0.1, 10.0),
        'growth_respiration_coefficient': (0.5, 2.0),
    }

    def __init__(self, input_dir: str = "input", output_dir: str = "output"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.current_params = {}
        self.param_files = {}
        self.best_params = None
        self.best_score = float('inf')

    def load_observed_data(self, observed_file: str) -> pd.DataFrame:
        """Load observed data from CSV file"""
        obs_df = pd.read_csv(observed_file, comment='#')
        print(f"Loaded {len(obs_df)} observed data points from {observed_file}")
        return obs_df

    def identify_calibration_targets(self, observed_df: pd.DataFrame) -> List[str]:
        """
        Automatically identify which variables need calibration based on
        available columns in observed data
        """
        targets = []
        column_mapping = {
            'plant_dry_weight_g': 'biomass',
            'total_biomass': 'biomass',
            'leaf_biomass': 'leaf_biomass',
            'root_biomass': 'root_biomass',
            'lai': 'lai',
            'leaf_area': 'leaf_area',
            'tissue_concentration_percent': 'tissue_nitrogen',
            'tissue_nitrogen': 'tissue_nitrogen',
            'n_uptake': 'nutrient_uptake_N',
            'p_uptake': 'nutrient_uptake_P',
            'k_uptake': 'nutrient_uptake_K',
        }

        for col in observed_df.columns:
            col_lower = col.lower()
            for key, target in column_mapping.items():
                if key in col_lower and target not in targets:
                    targets.append(target)
                    print(f"  ✓ Detected calibration target: {target} (from column '{col}')")

        return targets

    def get_parameters_for_targets(self, targets: List[str],
                                   use_secondary: bool = False) -> List[Tuple[str, str]]:
        """
        Get list of parameters to calibrate based on targets
        Returns list of (csv_file, parameter_name) tuples
        """
        params = set()

        for target in targets:
            if target in self.PARAMETER_MAPPINGS:
                # Add primary parameters
                for param in self.PARAMETER_MAPPINGS[target]['primary']:
                    params.add(param)

                # Optionally add secondary parameters
                if use_secondary:
                    for param in self.PARAMETER_MAPPINGS[target]['secondary']:
                        params.add(param)

        return sorted(list(params))

    def load_current_parameter_values(self, params: List[Tuple[str, str]]) -> Dict:
        """Load current values of parameters from CSV files"""
        current_values = {}

        for csv_file, param_name in params:
            file_path = self.input_dir / csv_file
            if not file_path.exists():
                print(f"  ⚠ Warning: {csv_file} not found, skipping {param_name}")
                continue

            df = pd.read_csv(file_path, comment='#')
            row = df[df['parameter_name'] == param_name]

            if row.empty:
                print(f"  ⚠ Warning: Parameter {param_name} not found in {csv_file}")
                continue

            value = float(row.iloc[0]['value'])
            current_values[(csv_file, param_name)] = value
            self.param_files[(csv_file, param_name)] = file_path

        print(f"\nLoaded {len(current_values)} parameter values")
        return current_values

    def run_simulation(self, params: Dict) -> Optional[pd.DataFrame]:
        """
        Update parameters and run simulation
        Returns simulation output dataframe
        """
        # Update CSV files with new parameter values
        self.update_csv_parameters(params)

        # Run simulation
        try:
            result = subprocess.run(
                ['python3', 'main.py'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                print(f"  ⚠ Simulation failed: {result.stderr[:200]}")
                return None

            # Load results
            results_file = self.output_dir / 'simulation_results.csv'
            if results_file.exists():
                return pd.read_csv(results_file)

        except subprocess.TimeoutExpired:
            print("  ⚠ Simulation timeout")
        except Exception as e:
            print(f"  ⚠ Simulation error: {e}")

        return None

    def calculate_fitness(self, params_array: np.ndarray, param_keys: List,
                         observed_df: pd.DataFrame, targets: List[str]) -> float:
        """
        Calculate fitness score (lower is better)
        Compares simulation output with observed data
        """
        # Convert array to parameter dictionary
        params = {param_keys[i]: params_array[i] for i in range(len(param_keys))}

        # Run simulation
        sim_df = self.run_simulation(params)
        if sim_df is None:
            return 1e10  # Penalize failed simulations

        # Calculate RMSE for each target
        total_rmse = 0
        n_targets = 0

        for target in targets:
            # Map target to simulation column
            sim_col = self._get_simulation_column(target)
            obs_col = self._get_observed_column(target, observed_df)

            if sim_col is None or obs_col is None:
                continue

            # Match days
            rmse = self._calculate_rmse(sim_df, observed_df, sim_col, obs_col)
            if rmse is not None:
                total_rmse += rmse
                n_targets += 1

        if n_targets == 0:
            return 1e10

        fitness = total_rmse / n_targets

        # Track best
        if fitness < self.best_score:
            self.best_score = fitness
            self.best_params = params.copy()
            print(f"    New best RMSE: {fitness:.4f}")

        return fitness

    def _get_simulation_column(self, target: str) -> Optional[str]:
        """Map target to simulation output column name"""
        mapping = {
            'biomass': 'total_biomass',
            'leaf_biomass': 'leaf_biomass',
            'root_biomass': 'root_biomass',
            'lai': 'lai',
            'leaf_area': 'leaf_area',
            'tissue_nitrogen': 'leaf_nitrogen_content',
            'nutrient_uptake_N': 'total_nitrogen_uptake',
            'nutrient_uptake_P': 'total_phosphorus_uptake',
            'nutrient_uptake_K': 'total_potassium_uptake',
        }
        return mapping.get(target)

    def _get_observed_column(self, target: str, observed_df: pd.DataFrame) -> Optional[str]:
        """Find observed data column for target"""
        possible_cols = {
            'biomass': ['plant_dry_weight_g', 'total_biomass', 'dry_weight'],
            'leaf_biomass': ['leaf_biomass', 'leaf_weight'],
            'root_biomass': ['root_biomass', 'root_weight'],
            'lai': ['lai', 'leaf_area_index'],
            'leaf_area': ['leaf_area'],
            'tissue_nitrogen': ['tissue_concentration_percent', 'tissue_nitrogen', 'n_concentration'],
        }

        if target not in possible_cols:
            return None

        for col in possible_cols[target]:
            if col in observed_df.columns:
                return col

        return None

    def _calculate_rmse(self, sim_df: pd.DataFrame, obs_df: pd.DataFrame,
                       sim_col: str, obs_col: str) -> Optional[float]:
        """Calculate RMSE between simulation and observed data"""
        if sim_col not in sim_df.columns or obs_col not in obs_df.columns:
            return None

        if 'days' not in obs_df.columns and 'day' not in sim_df.columns:
            return None

        obs_day_col = 'days' if 'days' in obs_df.columns else 'day'

        # Match by days
        errors = []
        for _, obs_row in obs_df.iterrows():
            day = obs_row[obs_day_col]
            sim_row = sim_df[sim_df['day'] == day]

            if not sim_row.empty:
                sim_val = sim_row.iloc[0][sim_col]
                obs_val = obs_row[obs_col]

                if pd.notna(sim_val) and pd.notna(obs_val):
                    errors.append((sim_val - obs_val) ** 2)

        if len(errors) == 0:
            return None

        return np.sqrt(np.mean(errors))

    def update_csv_parameters(self, params: Dict, backup: bool = True):
        """Update CSV files with new parameter values"""
        updated_files = set()

        for (csv_file, param_name), value in params.items():
            file_path = self.input_dir / csv_file

            if not file_path.exists():
                continue

            # Backup original file (only once per calibration)
            if backup and csv_file not in updated_files:
                backup_path = file_path.with_suffix('.csv.backup')
                if not backup_path.exists():
                    import shutil
                    shutil.copy(file_path, backup_path)

            # Update parameter value
            df = pd.read_csv(file_path, comment='#')
            mask = df['parameter_name'] == param_name
            if mask.any():
                df.loc[mask, 'value'] = value
                df.to_csv(file_path, index=False)
                updated_files.add(csv_file)

        return updated_files

    def calibrate(self, observed_file: str,
                 method: str = 'differential_evolution',
                 use_secondary_params: bool = False,
                 max_iterations: int = 100,
                 population_size: int = 15) -> Dict:
        """
        Main calibration method

        Args:
            observed_file: Path to observed data CSV
            method: Optimization method ('differential_evolution', 'scipy', or 'bayesian')
            use_secondary_params: Include secondary parameters in calibration
            max_iterations: Maximum optimization iterations
            population_size: Population size for evolutionary algorithm
        """
        print("="*80)
        print("INTELLIGENT PARAMETER CALIBRATION SYSTEM")
        print("="*80)
        print()

        # Load observed data
        observed_df = self.load_observed_data(observed_file)

        # Identify targets
        print("\nIdentifying calibration targets...")
        targets = self.identify_calibration_targets(observed_df)

        if not targets:
            print("  ⚠ No calibration targets identified!")
            return {}

        # Get parameters to calibrate
        print(f"\nSelecting parameters (use_secondary={use_secondary_params})...")
        params_to_calibrate = self.get_parameters_for_targets(targets, use_secondary_params)
        print(f"  → Selected {len(params_to_calibrate)} parameters for calibration")

        # Load current values
        self.current_params = self.load_current_parameter_values(params_to_calibrate)

        if not self.current_params:
            print("  ⚠ No parameters loaded!")
            return {}

        # Prepare optimization
        param_keys = list(self.current_params.keys())
        param_values = np.array([self.current_params[k] for k in param_keys])

        # Set bounds
        bounds = []
        for key in param_keys:
            _, param_name = key
            if param_name in self.PARAMETER_BOUNDS:
                min_mult, max_mult = self.PARAMETER_BOUNDS[param_name]
                current_val = self.current_params[key]
                bounds.append((current_val * min_mult, current_val * max_mult))
            else:
                # Default bounds
                current_val = self.current_params[key]
                bounds.append((current_val * 0.1, current_val * 10.0))

        print(f"\nStarting optimization using {method}...")
        print(f"  Max iterations: {max_iterations}")
        print(f"  Population size: {population_size}")
        print()

        # Run optimization
        if method == 'differential_evolution':
            result = differential_evolution(
                lambda x: self.calculate_fitness(x, param_keys, observed_df, targets),
                bounds,
                maxiter=max_iterations,
                popsize=population_size,
                strategy='best1bin',
                updating='deferred',
                workers=1,
                disp=True
            )
            optimal_params = {param_keys[i]: result.x[i] for i in range(len(param_keys))}

        elif method == 'scipy':
            result = minimize(
                lambda x: self.calculate_fitness(x, param_keys, observed_df, targets),
                param_values,
                bounds=bounds,
                method='L-BFGS-B',
                options={'maxiter': max_iterations, 'disp': True}
            )
            optimal_params = {param_keys[i]: result.x[i] for i in range(len(param_keys))}

        else:
            print(f"  ⚠ Unknown method: {method}")
            return {}

        # Use best found parameters
        if self.best_params:
            optimal_params = self.best_params

        print("\n" + "="*80)
        print("CALIBRATION COMPLETE!")
        print("="*80)
        print(f"\nFinal RMSE: {self.best_score:.4f}")
        print(f"\nCalibrated Parameters:")
        print("-"*80)

        for (csv_file, param_name), value in optimal_params.items():
            old_value = self.current_params[(csv_file, param_name)]
            change = ((value - old_value) / old_value) * 100
            print(f"  {param_name:<35} {old_value:>10.4f} → {value:>10.4f}  ({change:+.1f}%)")

        # Update CSVs with calibrated values
        print("\nUpdating input CSV files...")
        updated_files = self.update_csv_parameters(optimal_params, backup=True)
        print(f"  ✓ Updated {len(updated_files)} files")

        # Save calibration report
        self._save_calibration_report(optimal_params, targets, observed_file)

        return optimal_params

    def _save_calibration_report(self, optimal_params: Dict, targets: List[str],
                                observed_file: str):
        """Save calibration report to JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'observed_data_file': observed_file,
            'targets': targets,
            'final_rmse': self.best_score,
            'parameters': {
                f"{csv_file}/{param_name}": {
                    'old_value': self.current_params[(csv_file, param_name)],
                    'new_value': value,
                    'change_percent': ((value - self.current_params[(csv_file, param_name)]) /
                                     self.current_params[(csv_file, param_name)]) * 100
                }
                for (csv_file, param_name), value in optimal_params.items()
            }
        }

        report_file = Path('calibration_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n  ✓ Calibration report saved to: {report_file}")


def main():
    """Example usage"""
    import sys

    calibrator = IntelligentCalibrator()

    # Get observed data file from command line or use default
    observed_file = sys.argv[1] if len(sys.argv) > 1 else 'input/observed_data.csv'

    # Run calibration
    calibrator.calibrate(
        observed_file=observed_file,
        method='differential_evolution',
        use_secondary_params=False,
        max_iterations=50,
        population_size=10
    )


if __name__ == '__main__':
    main()
