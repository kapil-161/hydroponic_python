"""Trace the N-NO3 error"""
import sys
import traceback
sys.path.insert(0, 'src')

from simulations.distributed_simulation_runner import DistributedSimulationRunner

runner = DistributedSimulationRunner()
runner.config.total_days = 1
runner.config.steps_per_day = 1

try:
    output_path = runner.run_simulation()
except Exception as e:
    print(f"\n{'='*60}")
    print("FULL TRACEBACK:")
    print('='*60)
    traceback.print_exc()
    print('='*60)
