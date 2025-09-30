"""Quick test of distributed simulation runner with minimal days"""
import sys
sys.path.insert(0, 'src')

from simulations.distributed_simulation_runner import DistributedSimulationRunner
from utils.parameter_loader import StrictParameterLoader

# Test initialization
print("Testing initialization...")
runner = DistributedSimulationRunner()

# Override config to run just 1 day for testing
runner.config.total_days = 1
print(f"Set simulation to run for {runner.config.total_days} day(s)")

# Run simulation
print("\nRunning simulation...")
output_path = runner.run_simulation()

print(f"\nTest completed! Output: {output_path}")
runner.cleanup()
