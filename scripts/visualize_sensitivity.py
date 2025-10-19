"""
Visualization Tool for Sensitivity Analysis Results

Generates plots and charts from sensitivity analysis JSON/CSV outputs:
- Parameter sensitivity bar charts
- Response curves for each parameter
- Tornado diagrams
- Heatmaps for multi-parameter interactions

Usage:
    python scripts/visualize_sensitivity.py <results_file.json>
"""

import json
import sys
import csv
from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


class SensitivityVisualizer:
    """Visualize sensitivity analysis results"""

    def __init__(self, results_file: Path):
        self.results_file = results_file
        self.output_dir = results_file.parent / "plots"
        self.output_dir.mkdir(exist_ok=True)

        # Load results
        if results_file.suffix == '.json':
            with open(results_file, 'r') as f:
                self.results = json.load(f)
        else:
            raise ValueError("Only JSON results files supported")

        self.baseline = self.results['baseline']
        self.csv_name = self.results['csv_file']

    def plot_parameter_sensitivity_bars(self) -> None:
        """Create bar chart of parameter sensitivities"""
        # Calculate max sensitivity for each parameter
        sensitivities = []

        for param in self.results['parameters']:
            max_biomass_change = 0
            max_lai_change = 0

            for var in param['variations']:
                biomass_change = abs(var['relative_change'].get('total_biomass', 0))
                lai_change = abs(var['relative_change'].get('lai', 0))
                max_biomass_change = max(max_biomass_change, biomass_change)
                max_lai_change = max(max_lai_change, lai_change)

            sensitivities.append({
                'name': param['name'],
                'biomass': max_biomass_change,
                'lai': max_lai_change
            })

        # Sort by biomass sensitivity
        sensitivities.sort(key=lambda x: x['biomass'], reverse=True)

        # Create plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Biomass sensitivity
        names = [s['name'][:30] for s in sensitivities]
        biomass_vals = [s['biomass'] for s in sensitivities]

        ax1.barh(names, biomass_vals, color='steelblue')
        ax1.set_xlabel('Max % Change in Total Biomass', fontsize=12)
        ax1.set_title(f'Parameter Sensitivity - Biomass\n({self.csv_name})', fontsize=14, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)

        # LAI sensitivity
        sensitivities.sort(key=lambda x: x['lai'], reverse=True)
        names = [s['name'][:30] for s in sensitivities]
        lai_vals = [s['lai'] for s in sensitivities]

        ax2.barh(names, lai_vals, color='forestgreen')
        ax2.set_xlabel('Max % Change in LAI', fontsize=12)
        ax2.set_title(f'Parameter Sensitivity - LAI\n({self.csv_name})', fontsize=14, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)

        plt.tight_layout()
        output_file = self.output_dir / f"sensitivity_bars_{self.csv_name.replace('.csv', '')}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()

    def plot_response_curves(self) -> None:
        """Create response curves for each parameter"""
        num_params = len(self.results['parameters'])

        # Create subplots
        cols = 3
        rows = (num_params + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
        if num_params == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        for idx, param in enumerate(self.results['parameters']):
            ax = axes[idx]

            # Extract data
            multipliers = []
            biomass = []
            lai = []

            for var in sorted(param['variations'], key=lambda x: x['multiplier']):
                multipliers.append(var['multiplier'])
                biomass.append(var['metrics'].get('total_biomass', 0))
                lai.append(var['metrics'].get('lai', 0))

            # Plot
            ax2 = ax.twinx()

            line1 = ax.plot(multipliers, biomass, 'o-', color='steelblue', linewidth=2,
                          markersize=8, label='Total Biomass')
            line2 = ax2.plot(multipliers, lai, 's-', color='forestgreen', linewidth=2,
                           markersize=8, label='LAI')

            # Baseline lines
            ax.axhline(y=self.baseline.get('total_biomass', 0), color='steelblue',
                      linestyle='--', alpha=0.5, label='Baseline Biomass')
            ax2.axhline(y=self.baseline.get('lai', 0), color='forestgreen',
                       linestyle='--', alpha=0.5, label='Baseline LAI')

            # Labels
            ax.set_xlabel('Parameter Multiplier', fontsize=10)
            ax.set_ylabel('Total Biomass (g)', fontsize=10, color='steelblue')
            ax2.set_ylabel('LAI (m²/m²)', fontsize=10, color='forestgreen')
            ax.tick_params(axis='y', labelcolor='steelblue')
            ax2.tick_params(axis='y', labelcolor='forestgreen')

            # Title
            param_name = param['name']
            if len(param_name) > 35:
                param_name = param_name[:32] + '...'
            ax.set_title(f"{param_name}\n(baseline: {param['original_value']:.3f} {param['unit']})",
                        fontsize=10)

            # Legend
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax.legend(lines, labels, loc='best', fontsize=8)

            ax.grid(True, alpha=0.3)

        # Hide extra subplots
        for idx in range(num_params, len(axes)):
            axes[idx].set_visible(False)

        plt.suptitle(f'Parameter Response Curves - {self.csv_name}',
                    fontsize=16, fontweight='bold', y=1.00)
        plt.tight_layout()

        output_file = self.output_dir / f"response_curves_{self.csv_name.replace('.csv', '')}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()

    def plot_tornado_diagram(self) -> None:
        """Create tornado diagram showing parameter impacts"""
        # Calculate range of impacts for each parameter
        impacts = []

        for param in self.results['parameters']:
            biomass_values = []
            lai_values = []

            for var in param['variations']:
                biomass_values.append(var['relative_change'].get('total_biomass', 0))
                lai_values.append(var['relative_change'].get('lai', 0))

            biomass_range = max(biomass_values) - min(biomass_values)
            lai_range = max(lai_values) - min(lai_values)

            impacts.append({
                'name': param['name'],
                'biomass_min': min(biomass_values),
                'biomass_max': max(biomass_values),
                'biomass_range': biomass_range,
                'lai_min': min(lai_values),
                'lai_max': max(lai_values),
                'lai_range': lai_range
            })

        # Sort by biomass range
        impacts.sort(key=lambda x: x['biomass_range'], reverse=True)

        # Take top 10
        impacts = impacts[:10]

        # Create tornado diagram
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Biomass tornado
        y_pos = np.arange(len(impacts))
        names = [imp['name'][:30] for imp in impacts]

        for i, imp in enumerate(impacts):
            left = min(0, imp['biomass_min'])
            right = max(0, imp['biomass_max'])

            # Negative bar
            if imp['biomass_min'] < 0:
                ax1.barh(i, abs(imp['biomass_min']), left=imp['biomass_min'],
                        height=0.8, color='coral', alpha=0.7)

            # Positive bar
            if imp['biomass_max'] > 0:
                ax1.barh(i, imp['biomass_max'], left=0,
                        height=0.8, color='lightblue', alpha=0.7)

        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(names)
        ax1.set_xlabel('% Change in Total Biomass', fontsize=12)
        ax1.set_title(f'Tornado Diagram - Biomass\n({self.csv_name})',
                     fontsize=14, fontweight='bold')
        ax1.axvline(x=0, color='black', linewidth=1)
        ax1.grid(axis='x', alpha=0.3)

        # LAI tornado
        impacts.sort(key=lambda x: x['lai_range'], reverse=True)
        names = [imp['name'][:30] for imp in impacts]

        for i, imp in enumerate(impacts):
            # Negative bar
            if imp['lai_min'] < 0:
                ax2.barh(i, abs(imp['lai_min']), left=imp['lai_min'],
                        height=0.8, color='coral', alpha=0.7)

            # Positive bar
            if imp['lai_max'] > 0:
                ax2.barh(i, imp['lai_max'], left=0,
                        height=0.8, color='lightgreen', alpha=0.7)

        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(names)
        ax2.set_xlabel('% Change in LAI', fontsize=12)
        ax2.set_title(f'Tornado Diagram - LAI\n({self.csv_name})',
                     fontsize=14, fontweight='bold')
        ax2.axvline(x=0, color='black', linewidth=1)
        ax2.grid(axis='x', alpha=0.3)

        # Legend
        neg_patch = mpatches.Patch(color='coral', alpha=0.7, label='Decrease')
        pos_patch = mpatches.Patch(color='lightblue', alpha=0.7, label='Increase')
        ax1.legend(handles=[neg_patch, pos_patch], loc='best')

        neg_patch = mpatches.Patch(color='coral', alpha=0.7, label='Decrease')
        pos_patch = mpatches.Patch(color='lightgreen', alpha=0.7, label='Increase')
        ax2.legend(handles=[neg_patch, pos_patch], loc='best')

        plt.tight_layout()
        output_file = self.output_dir / f"tornado_{self.csv_name.replace('.csv', '')}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()

    def generate_all_plots(self) -> None:
        """Generate all visualization plots"""
        print(f"\nGenerating visualization plots...")

        self.plot_parameter_sensitivity_bars()
        self.plot_response_curves()
        self.plot_tornado_diagram()

        print(f"\nAll plots saved to: {self.output_dir}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/visualize_sensitivity.py <results_file.json>")
        print("\nAvailable results files:")

        sensitivity_dir = Path("output/sensitivity")
        if sensitivity_dir.exists():
            json_files = list(sensitivity_dir.glob("*.json"))
            for f in sorted(json_files):
                print(f"  {f}")
        else:
            print("  No results files found in output/sensitivity/")

        sys.exit(1)

    results_file = Path(sys.argv[1])

    if not results_file.exists():
        print(f"Error: File not found: {results_file}")
        sys.exit(1)

    visualizer = SensitivityVisualizer(results_file)
    visualizer.generate_all_plots()


if __name__ == "__main__":
    main()
