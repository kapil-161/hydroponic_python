#!/usr/bin/env python3
"""
Main Entry Point for Hydroponic Simulation

This is the main entry point to run the distributed hydroponic simulation system.
All parameters are loaded from CSV files in the input/ directory.

USAGE:
    python3 main.py

REQUIREMENTS:
    - Python 3.8 or higher
    - All dependencies from requirements.txt installed
    - CSV parameter files in input/ directory

OUTPUT:
    - Combined results: output/simulation_results.csv
    - Individual simulator outputs: output/<simulator_name>.csv
    - Performance metrics displayed on completion

CONFIGURATION:
    All simulation parameters are configured via CSV files in input/:
    - constants.csv: Universal physical constants
    - stress.csv: Stress response parameters
    - roots.csv: Root system parameters
    - genetics.csv: Genetic trait parameters
    - photo.csv: Photosynthesis parameters
    - respiration.csv: Respiration parameters
    - allocation.csv: Biomass allocation parameters
    - phenology.csv: Growth stage parameters
    - nitrogen_balance.csv: Nitrogen cycle parameters
    - initials.csv: Initial state values
    - weather.csv: Daily weather data
"""

import sys
import os
import shutil

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from simulations.distributed_simulation_runner import DistributedSimulationRunner


def clear_cache():
    """Remove Python cache directories and bytecode files to ensure a clean run."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    removed_items = 0

    for root, dirs, files in os.walk(project_root):
        # Remove __pycache__ directories
        for directory_name in list(dirs):
            if directory_name == "__pycache__":
                cache_dir_path = os.path.join(root, directory_name)
                try:
                    shutil.rmtree(cache_dir_path, ignore_errors=True)
                    removed_items += 1
                except Exception:
                    # Non-fatal; continue cleaning other paths
                    pass

        # Remove stray .pyc files (in case any exist outside __pycache__)
        for file_name in files:
            if file_name.endswith(".pyc"):
                pyc_path = os.path.join(root, file_name)
                try:
                    os.remove(pyc_path)
                    removed_items += 1
                except Exception:
                    # Non-fatal; continue cleaning other paths
                    pass

    if removed_items > 0:
        print(f"Cleared Python cache artifacts: {removed_items} items removed")


def main():
    """Run the distributed hydroponic simulation"""
    print("=" * 80)
    print("Hydroponic Research Framework - Distributed Simulation")
    print("=" * 80)
    print()

    # Ensure a clean environment before starting
    clear_cache()

    # Create and run the simulation
    runner = DistributedSimulationRunner()

    print("Starting simulation...")
    print()

    # Run the simulation
    output_file = runner.run_simulation()

    print()
    print("=" * 80)
    print("Simulation completed successfully!")
    print(f"Results saved to: {output_file}")
    print("=" * 80)

    return output_file


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Simulation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
