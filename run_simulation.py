#!/usr/bin/env python3
"""
Simple Hydroponic Simulation Runner

This is the main file to run the hydroponic simulation.
It uses the existing distributed simulation runner approach.
"""

import sys
import os

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from simulations.distributed_simulation_runner import DistributedSimulationRunner


def main():
    """Main entry point for the hydroponic simulation"""
    try:
        print("🌱 Hydroponic Simulation System")
        print("=" * 50)
        
        # Initialize and run the simulation
        runner = DistributedSimulationRunner()
        results_path = runner.run_simulation()
        
        print("=" * 50)
        print("✅ Simulation completed successfully!")
        print(f"📁 Results saved to: {results_path}")
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
