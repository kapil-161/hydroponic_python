"""
Flexible Sensitivity Analysis Tool for Hydroponic Simulation

This tool allows users to:
1. Select which CSV parameter file to analyze
2. Choose specific parameters within that file
3. Define sensitivity ranges (±% or absolute ranges)
4. Run simulations across parameter variations
5. Analyze and visualize results

Features:
- One-factor-at-a-time (OFAT) sensitivity analysis
- Multi-parameter sensitivity analysis
- Automatic result visualization
- Statistical analysis of parameter impacts
- CSV export of results

Usage:
    python scripts/sensitivity_analysis.py
"""

import os
import sys
import csv
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
from datetime import datetime

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SensitivityAnalyzer:
    """Main sensitivity analysis class"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.input_dir = self.project_root / "input"
        self.output_dir = self.project_root / "output"
        self.sensitivity_dir = self.project_root / "output" / "sensitivity"
        self.sensitivity_dir.mkdir(exist_ok=True)

        # Available CSV files
        self.csv_files = self._discover_csv_files()

        # Results storage
        self.results = []

    def _discover_csv_files(self) -> List[Path]:
        """Find all CSV parameter files in input directory"""
        csv_files = list(self.input_dir.glob("*.csv"))
        # Exclude weather and observed data
        exclude = ['weather', 'observed', 'constants']
        csv_files = [f for f in csv_files if not any(ex in f.name for ex in exclude)]
        return sorted(csv_files)

    def _read_csv_parameters(self, csv_file: Path) -> List[Dict[str, Any]]:
        """Read parameters from a CSV file"""
        parameters = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('parameter_name'):
                    try:
                        value = float(row['value'])
                        parameters.append({
                            'name': row['parameter_name'],
                            'value': value,
                            'unit': row.get('unit', ''),
                            'description': row.get('description', '')
                        })
                    except (ValueError, KeyError):
                        # Skip non-numeric parameters
                        pass
        return parameters

    def _modify_parameter(self, csv_file: Path, param_name: str, new_value: float) -> None:
        """Modify a parameter value in a CSV file"""
        rows = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['parameter_name'] == param_name:
                    row['value'] = str(new_value)
                rows.append(row)

        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _backup_csv(self, csv_file: Path) -> Path:
        """Create backup of CSV file"""
        backup_file = csv_file.with_suffix('.csv.backup')
        shutil.copy2(csv_file, backup_file)
        return backup_file

    def _restore_csv(self, csv_file: Path, backup_file: Path) -> None:
        """Restore CSV file from backup"""
        shutil.copy2(backup_file, csv_file)
        backup_file.unlink()

    def _run_simulation(self) -> Dict[str, float]:
        """Run the hydroponic simulation and extract key outputs"""
        try:
            # Run simulation
            result = subprocess.run(
                ['python3', 'main.py'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )

            if result.returncode != 0:
                print(f"{Colors.FAIL}Simulation failed!{Colors.ENDC}")
                return None

            # Extract key metrics from output files
            metrics = {}

            # Biomass metrics
            biomass_file = self.output_dir / "biomass_allocation.csv"
            if biomass_file.exists():
                with open(biomass_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_line = lines[-1].strip().split(',')
                        metrics['total_biomass'] = float(last_line[3])
                        metrics['leaf_biomass'] = float(last_line[4])
                        metrics['stem_biomass'] = float(last_line[5])
                        metrics['root_biomass'] = float(last_line[6])

            # LAI metrics
            canopy_file = self.output_dir / "canopy_architecture.csv"
            if canopy_file.exists():
                with open(canopy_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_line = lines[-1].strip().split(',')
                        metrics['lai'] = float(last_line[3])
                        metrics['leaf_area'] = float(last_line[4])
                        metrics['canopy_height'] = float(last_line[5])

            # Water metrics
            water_file = self.output_dir / "water_uptake.csv"
            if water_file.exists():
                with open(water_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_line = lines[-1].strip().split(',')
                        metrics['cumulative_water'] = float(last_line[11])
                        metrics['water_availability'] = float(last_line[6])

            # Photosynthesis metrics
            photo_file = self.output_dir / "photosynthesis.csv"
            if photo_file.exists():
                with open(photo_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_line = lines[-1].strip().split(',')
                        metrics['cumulative_carbon'] = float(last_line[8])

            # Leaf development metrics
            leaf_file = self.output_dir / "leaf_development.csv"
            if leaf_file.exists():
                with open(leaf_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_line = lines[-1].strip().split(',')
                        metrics['total_leaves'] = int(last_line[3])

            return metrics

        except subprocess.TimeoutExpired:
            print(f"{Colors.FAIL}Simulation timeout!{Colors.ENDC}")
            return None
        except Exception as e:
            print(f"{Colors.FAIL}Error running simulation: {e}{Colors.ENDC}")
            return None

    def display_menu(self) -> None:
        """Display main menu"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}HYDROPONIC SIMULATION - SENSITIVITY ANALYSIS{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

        print(f"{Colors.OKBLUE}Available CSV Parameter Files:{Colors.ENDC}\n")
        for i, csv_file in enumerate(self.csv_files, 1):
            print(f"  {Colors.OKGREEN}{i:2d}.{Colors.ENDC} {csv_file.name:30s}")

        print(f"\n{Colors.WARNING}0. Exit{Colors.ENDC}\n")

    def select_csv_file(self) -> Path:
        """Let user select a CSV file"""
        while True:
            try:
                choice = input(f"{Colors.OKCYAN}Select CSV file (0 to exit): {Colors.ENDC}")
                choice = int(choice)

                if choice == 0:
                    return None
                if 1 <= choice <= len(self.csv_files):
                    return self.csv_files[choice - 1]
                else:
                    print(f"{Colors.FAIL}Invalid choice. Please try again.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.FAIL}Please enter a number.{Colors.ENDC}")

    def display_parameters(self, parameters: List[Dict]) -> None:
        """Display parameters from selected CSV"""
        print(f"\n{Colors.OKBLUE}Available Parameters:{Colors.ENDC}\n")
        print(f"  {'#':>3}  {'Parameter Name':<40}  {'Value':>12}  {'Unit':<10}")
        print(f"  {'-'*3}  {'-'*40}  {'-'*12}  {'-'*10}")

        for i, param in enumerate(parameters, 1):
            print(f"  {i:3d}. {param['name']:<40}  {param['value']:>12.4f}  {param['unit']:<10}")

    def select_parameters(self, parameters: List[Dict]) -> List[int]:
        """Let user select parameters for sensitivity analysis"""
        print(f"\n{Colors.OKCYAN}Select parameters for sensitivity analysis{Colors.ENDC}")
        print(f"{Colors.OKCYAN}(Enter comma-separated numbers, e.g., 1,3,5 or 'all' for all parameters){Colors.ENDC}")

        while True:
            try:
                choice = input(f"{Colors.OKCYAN}Your selection: {Colors.ENDC}").strip()

                if choice.lower() == 'all':
                    return list(range(len(parameters)))

                indices = [int(x.strip()) - 1 for x in choice.split(',')]

                # Validate indices
                if all(0 <= i < len(parameters) for i in indices):
                    return indices
                else:
                    print(f"{Colors.FAIL}Invalid parameter numbers. Please try again.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.FAIL}Invalid input. Please enter comma-separated numbers.{Colors.ENDC}")

    def get_sensitivity_range(self) -> Tuple[str, List[float]]:
        """Get sensitivity range from user"""
        print(f"\n{Colors.OKBLUE}Sensitivity Range Configuration:{Colors.ENDC}")
        print(f"  1. Percentage variation (e.g., ±10%, ±20%, ±50%)")
        print(f"  2. Custom multipliers (e.g., 0.5×, 1.0×, 1.5×, 2.0×)")

        while True:
            try:
                choice = input(f"{Colors.OKCYAN}Select range type (1 or 2): {Colors.ENDC}").strip()

                if choice == '1':
                    percentages = input(f"{Colors.OKCYAN}Enter percentages (e.g., -50,-20,0,20,50): {Colors.ENDC}")
                    percentages = [float(x.strip()) for x in percentages.split(',')]
                    multipliers = [1.0 + (p / 100.0) for p in percentages]
                    return ('percentage', multipliers)

                elif choice == '2':
                    mults = input(f"{Colors.OKCYAN}Enter multipliers (e.g., 0.5,0.75,1.0,1.5,2.0): {Colors.ENDC}")
                    multipliers = [float(x.strip()) for x in mults.split(',')]
                    return ('multiplier', multipliers)

                else:
                    print(f"{Colors.FAIL}Invalid choice. Please enter 1 or 2.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.FAIL}Invalid input. Please enter valid numbers.{Colors.ENDC}")

    def run_ofat_analysis(self, csv_file: Path, parameters: List[Dict],
                          param_indices: List[int], multipliers: List[float]) -> None:
        """Run One-Factor-At-a-Time sensitivity analysis"""

        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}Running OFAT Sensitivity Analysis{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

        # Create backup
        backup_file = self._backup_csv(csv_file)

        try:
            # Get baseline results
            print(f"{Colors.OKBLUE}Running baseline simulation...{Colors.ENDC}")
            baseline_metrics = self._run_simulation()

            if baseline_metrics is None:
                print(f"{Colors.FAIL}Baseline simulation failed. Aborting.{Colors.ENDC}")
                return

            print(f"{Colors.OKGREEN}✓ Baseline complete{Colors.ENDC}")
            print(f"  Total biomass: {baseline_metrics.get('total_biomass', 0):.2f} g")
            print(f"  LAI: {baseline_metrics.get('lai', 0):.2f} m²/m²")

            # Results storage
            analysis_results = {
                'csv_file': csv_file.name,
                'baseline': baseline_metrics,
                'parameters': []
            }

            # Analyze each parameter
            for idx in param_indices:
                param = parameters[idx]
                param_name = param['name']
                original_value = param['value']

                print(f"\n{Colors.OKCYAN}Analyzing: {param_name}{Colors.ENDC}")
                print(f"  Original value: {original_value:.4f} {param['unit']}")

                param_results = {
                    'name': param_name,
                    'original_value': original_value,
                    'unit': param['unit'],
                    'variations': []
                }

                # Test each multiplier
                for mult in multipliers:
                    new_value = original_value * mult

                    print(f"    Testing {mult:.2f}× ({new_value:.4f})...", end=' ')

                    # Modify parameter
                    self._modify_parameter(csv_file, param_name, new_value)

                    # Run simulation
                    metrics = self._run_simulation()

                    if metrics:
                        print(f"{Colors.OKGREEN}✓{Colors.ENDC}")

                        # Calculate relative changes
                        relative_change = {}
                        for key, value in metrics.items():
                            baseline_val = baseline_metrics.get(key, 0)
                            if baseline_val != 0:
                                relative_change[key] = ((value - baseline_val) / baseline_val) * 100
                            else:
                                relative_change[key] = 0

                        param_results['variations'].append({
                            'multiplier': mult,
                            'value': new_value,
                            'metrics': metrics,
                            'relative_change': relative_change
                        })
                    else:
                        print(f"{Colors.FAIL}✗{Colors.ENDC}")

                    # Restore original value
                    self._restore_csv(csv_file, backup_file)
                    backup_file = self._backup_csv(csv_file)

                analysis_results['parameters'].append(param_results)

            # Save results
            self._save_results(analysis_results)
            self._display_summary(analysis_results)

        finally:
            # Restore original CSV
            self._restore_csv(csv_file, backup_file)
            print(f"\n{Colors.OKGREEN}CSV file restored to original state{Colors.ENDC}")

    def _save_results(self, results: Dict) -> None:
        """Save sensitivity analysis results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_file = self.sensitivity_dir / f"sensitivity_{results['csv_file']}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n{Colors.OKGREEN}Results saved to: {json_file}{Colors.ENDC}")

        # Save CSV summary
        csv_file = self.sensitivity_dir / f"sensitivity_{results['csv_file']}_{timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(['Parameter', 'Multiplier', 'Value', 'Total_Biomass_g',
                           'LAI_m2_m2', 'Cumulative_Water_L', 'Biomass_Change_%', 'LAI_Change_%'])

            # Baseline
            baseline = results['baseline']
            writer.writerow(['BASELINE', 1.0, '-',
                           baseline.get('total_biomass', 0),
                           baseline.get('lai', 0),
                           baseline.get('cumulative_water', 0),
                           0, 0])

            # Parameters
            for param_result in results['parameters']:
                for var in param_result['variations']:
                    writer.writerow([
                        param_result['name'],
                        var['multiplier'],
                        var['value'],
                        var['metrics'].get('total_biomass', 0),
                        var['metrics'].get('lai', 0),
                        var['metrics'].get('cumulative_water', 0),
                        var['relative_change'].get('total_biomass', 0),
                        var['relative_change'].get('lai', 0)
                    ])

        print(f"{Colors.OKGREEN}CSV summary saved to: {csv_file}{Colors.ENDC}")

    def _display_summary(self, results: Dict) -> None:
        """Display summary of sensitivity analysis"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}SENSITIVITY ANALYSIS SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

        baseline = results['baseline']

        # Find most sensitive parameters
        sensitivities = []

        for param_result in results['parameters']:
            max_biomass_change = 0
            max_lai_change = 0

            for var in param_result['variations']:
                biomass_change = abs(var['relative_change'].get('total_biomass', 0))
                lai_change = abs(var['relative_change'].get('lai', 0))

                max_biomass_change = max(max_biomass_change, biomass_change)
                max_lai_change = max(max_lai_change, lai_change)

            sensitivities.append({
                'name': param_result['name'],
                'biomass_sensitivity': max_biomass_change,
                'lai_sensitivity': max_lai_change
            })

        # Sort by biomass sensitivity
        sensitivities.sort(key=lambda x: x['biomass_sensitivity'], reverse=True)

        print(f"{Colors.OKBLUE}All Parameters Ranked by Biomass Sensitivity:{Colors.ENDC}\n")
        print(f"  {'Rank':<6} {'Parameter':<40} {'Max Change':<15}")
        print(f"  {'-'*6} {'-'*40} {'-'*15}")

        for i, sens in enumerate(sensitivities, 1):
            print(f"  {i:<6} {sens['name']:<40} {sens['biomass_sensitivity']:>10.2f}%")

        print(f"\n{Colors.OKBLUE}All Parameters Ranked by LAI Sensitivity:{Colors.ENDC}\n")
        sensitivities.sort(key=lambda x: x['lai_sensitivity'], reverse=True)

        print(f"  {'Rank':<6} {'Parameter':<40} {'Max Change':<15}")
        print(f"  {'-'*6} {'-'*40} {'-'*15}")

        for i, sens in enumerate(sensitivities, 1):
            print(f"  {i:<6} {sens['name']:<40} {sens['lai_sensitivity']:>10.2f}%")

    def run(self) -> None:
        """Main run loop"""
        while True:
            self.display_menu()

            # Select CSV file
            csv_file = self.select_csv_file()
            if csv_file is None:
                print(f"\n{Colors.OKGREEN}Exiting sensitivity analysis. Goodbye!{Colors.ENDC}\n")
                break

            print(f"\n{Colors.OKGREEN}Selected: {csv_file.name}{Colors.ENDC}")

            # Read parameters
            parameters = self._read_csv_parameters(csv_file)

            if not parameters:
                print(f"{Colors.FAIL}No numeric parameters found in {csv_file.name}{Colors.ENDC}")
                continue

            # Display parameters
            self.display_parameters(parameters)

            # Select parameters
            param_indices = self.select_parameters(parameters)

            print(f"\n{Colors.OKGREEN}Selected {len(param_indices)} parameter(s) for analysis{Colors.ENDC}")

            # Get sensitivity range
            range_type, multipliers = self.get_sensitivity_range()

            print(f"\n{Colors.OKGREEN}Will test {len(multipliers)} variations per parameter{Colors.ENDC}")
            print(f"{Colors.OKGREEN}Total simulations: {1 + len(param_indices) * len(multipliers)}{Colors.ENDC}")

            # Confirm
            confirm = input(f"\n{Colors.WARNING}Proceed with analysis? (y/n): {Colors.ENDC}")
            if confirm.lower() != 'y':
                print(f"{Colors.WARNING}Analysis cancelled{Colors.ENDC}")
                continue

            # Run analysis
            self.run_ofat_analysis(csv_file, parameters, param_indices, multipliers)

            # Ask if user wants to continue
            another = input(f"\n{Colors.OKCYAN}Analyze another file? (y/n): {Colors.ENDC}")
            if another.lower() != 'y':
                print(f"\n{Colors.OKGREEN}Exiting sensitivity analysis. Goodbye!{Colors.ENDC}\n")
                break


def main():
    """Main entry point"""
    print(f"\n{Colors.HEADER}Hydroponic Simulation - Sensitivity Analysis Tool{Colors.ENDC}\n")

    analyzer = SensitivityAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
