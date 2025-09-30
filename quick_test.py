"""Quick test with just a few steps"""
import sys
sys.path.insert(0, 'src')

from simulations.distributed_simulation_runner import DistributedSimulationRunner

# Test initialization
print("Initializing...")
runner = DistributedSimulationRunner()

# Override to run just 1 day with fewer steps
runner.config.total_days = 1
runner.config.steps_per_day = 2  # Just 2 steps per day for testing
print(f"Running {runner.config.total_days} day with {runner.config.steps_per_day} steps")

# Run
try:
    output_path = runner.run_simulation()
    print(f"\n✓ Test completed! Output: {output_path}")
    runner.cleanup()
except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
