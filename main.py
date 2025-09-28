#!/usr/bin/env python3
"""
Main entry point for the hydroponic simulation.
Run this file directly to start the simulation.
"""

if __name__ == "__main__":
    import sys
    import os

    # Add the project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Import and run the simulator
    from src.cropgro_hydroponic_simulator import HydroponicSimulator

    # Create and run simulation
    simulator = HydroponicSimulator()
    simulator.run_simulation()