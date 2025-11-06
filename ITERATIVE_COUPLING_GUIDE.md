# Iterative Nitrogen-Photosynthesis Coupling

## Overview

The iterative coupling feature improves the accuracy of the nitrogen-photosynthesis feedback loop by using **current timestep** nitrogen status instead of the previous timestep. This eliminates the one-step lag that occurs in the standard execution order.

## How It Works

### Standard Execution (One-Step Lag)

```
Hour N:
1. Photosynthesis uses N status from Hour N-1
2. Nitrogen balance calculates new N status based on Hour N photosynthesis
3. Hour N+1: Photosynthesis uses Hour N N status
```

### Iterative Coupling (Current Timestep)

```
Hour N:
1. Photosynthesis uses initial N status
2. Nitrogen balance calculates N status based on photosynthesis
3. Photosynthesis recalculates with updated N status
4. Nitrogen balance recalculates with updated photosynthesis
5. Iterate until convergence (or max iterations)
6. Final values use current timestep data
```

## Configuration

Add these parameters to your `master_parameters.csv` under `simulator_defaults`:

```csv
simulator_defaults_enable_iterative_coupling,True
simulator_defaults_max_iterations,5
simulator_defaults_convergence_threshold,0.01
```

### Parameters

- **`enable_iterative_coupling`** (bool): Enable/disable iterative coupling
  - Default: `False` (backward compatible)
  - Set to `True` to enable iterative coupling

- **`max_iterations`** (int): Maximum number of iterations
  - Default: `5`
  - Typical convergence: 2-3 iterations
  - Increase for tighter convergence tolerance

- **`convergence_threshold`** (float): Relative change threshold for convergence
  - Default: `0.01` (1% relative change)
  - Convergence when: `|current_rate - previous_rate| / |previous_rate| < threshold`
  - Decrease for tighter convergence (e.g., 0.001 = 0.1%)

## Convergence Criteria

The iterative loop converges when:

```
|net_assimilation_rate[i] - net_assimilation_rate[i-1]| / |net_assimilation_rate[i-1]| < convergence_threshold
```

Where:
- `net_assimilation_rate[i]` = photosynthesis rate at iteration `i`
- `convergence_threshold` = configured threshold (default 0.01 = 1%)

## Benefits

1. **Higher Accuracy**: Uses current timestep N status instead of previous timestep
2. **Better N-Photosynthesis Coupling**: Properly captures the feedback loop
3. **Scientifically Sound**: Matches real plant physiology where N status affects photosynthesis immediately
4. **Configurable**: Can be enabled/disabled and tuned via parameters

## Performance Impact

- **Additional Computation**: 2-5 iterations per timestep (typically 2-3)
- **Convergence**: Usually converges in 2-3 iterations
- **Overhead**: ~2-5x computation time for photosynthesis + nitrogen balance steps
- **Recommendation**: Enable for accuracy-critical simulations, disable for faster runs

## Example Usage

### Enable in CSV

```csv
# In input/master_parameters.csv
simulator_defaults_enable_iterative_coupling,True
simulator_defaults_max_iterations,5
simulator_defaults_convergence_threshold,0.01
```

### Programmatic Usage

```python
from simulations.distributed_simulation_runner import DistributedSimulationRunner
from simulations.simulation_orchestrator import SimulationConfig

# Create config with iterative coupling enabled
config = SimulationConfig(
    # ... other parameters ...
    enable_iterative_coupling=True,
    max_iterations=5,
    convergence_threshold=0.01
)

# Use in runner
runner = DistributedSimulationRunner()
runner.orchestrator.config.enable_iterative_coupling = True
runner.orchestrator.config.max_iterations = 5
runner.orchestrator.config.convergence_threshold = 0.01
```

## Monitoring

The system logs convergence information:

```
[Iterative Coupling] Converged after 3 iterations (relative change: 0.003456)
```

If max iterations reached without convergence:

```
[Iterative Coupling] Max iterations (5) reached. Final relative change: 0.015234
```

## When to Use

### ✅ Use Iterative Coupling When:

- High accuracy requirements
- Studying N-photosynthesis interactions
- Fine-tuning N management strategies
- Comparing with experimental data
- Sub-daily timestep simulations

### ❌ Skip Iterative Coupling When:

- Fast exploratory runs
- Daily timestep simulations (one-step lag acceptable)
- Large parameter sweeps
- Performance-critical applications

## Scientific Background

In real plants, nitrogen status affects photosynthesis **immediately** through:
- Rubisco enzyme concentration (N-dependent)
- Chlorophyll content (N-dependent)
- Leaf N content (area-based)

The iterative coupling properly captures this immediate feedback, making the model more physiologically realistic.

## References

- Crop modeling best practices (DSSAT, APSIM)
- Nitrogen-photosynthesis coupling literature
- Iterative solution methods for coupled systems

