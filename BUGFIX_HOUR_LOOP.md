# Bug Fix: Simulation Hour Loop Incorrect Start Time

## Issue
**File**: `src/simulations/simulation_orchestrator.py`
**Line**: 185 (before fix)
**Severity**: **CRITICAL** - Data Loss Bug

## Problem Description

The inner hour loop incorrectly started at `self.config.start_hour` for **every day** of the simulation, not just the first day. This caused the simulation to skip hours 0 through `start_hour-1` on all days after the first day.

### Example
If simulation starts at:
- `start_day = 1`
- `start_hour = 6`
- `steps_per_day = 24` (24 hours)

**Buggy Behavior:**
- Day 1: Hours 6-23 ✅ (18 hours)
- Day 2: Hours 6-23 ❌ (18 hours - **missing hours 0-5**)
- Day 3: Hours 6-23 ❌ (18 hours - **missing hours 0-5**)

**Expected Behavior:**
- Day 1: Hours 6-23 ✅ (18 hours - starts mid-day as intended)
- Day 2: Hours 0-23 ✅ (24 hours - full day)
- Day 3: Hours 0-23 ✅ (24 hours - full day)

## Impact

### Data Loss
With `start_hour=6`, the bug caused:
- **18.2% of simulation data missing** (12 out of 66 hours lost)
- Hours 0-5 completely skipped on all days except the first
- Missing data affects all 16 simulators

### Scientific Impact
- **Photosynthesis**: Early morning light response missing
- **Respiration**: Night-to-day transition data lost
- **Water uptake**: Morning transpiration spike not captured
- **Nutrient uptake**: Early day dynamics missing
- **All time-dependent processes**: Incomplete diurnal cycles

### Reproducibility Issues
- Results varied based on `start_hour` configuration
- Multi-day simulations had systematically incomplete data
- No error/warning indicated data was missing

## Root Cause

```python
# BUGGY CODE (line 185)
for hour in range(self.config.start_hour, self.config.steps_per_day):
    # This uses start_hour for EVERY day iteration
```

The `range(self.config.start_hour, ...)` was outside the day-specific logic, causing it to apply to all days instead of just the first day.

## Fix

```python
# FIXED CODE (lines 185-187)
# Start at configured start_hour only on first day, then 0 for subsequent days
start_hour = self.config.start_hour if day == self.config.start_day else 0
for hour in range(start_hour, self.config.steps_per_day):
    # Now correctly starts at 0 for days after the first
```

**Logic:**
1. Check if current day is the first day (`day == self.config.start_day`)
2. If yes: use `self.config.start_hour` (allows mid-day start)
3. If no: use `0` (full day from hour 0)

## Testing

### Unit Test Results
```
OLD (BUGGY): 54 hours executed over 3 days
NEW (FIXED): 66 hours executed over 3 days
Missing data in buggy version: 12 hours (18.2%)
```

### Integration Test
✅ Full simulation runs successfully with fix
✅ All 16 simulators execute correctly
✅ No errors or warnings
✅ Output files generated correctly

## Verification

To verify the fix is working:
```python
# Check simulation output for day transitions
# Day 1 should start at start_hour
# Days 2+ should start at hour 0

# Example check in output CSV:
df = pd.read_csv('output/simulation_results.csv')
day2_hours = df[df['day'] == 2]['hour'].unique()
assert 0 in day2_hours, "Day 2 should include hour 0"
```

## Historical Impact

All simulations run before this fix had incomplete data for days 2+. If analyzing previous results:
1. Check `start_hour` configuration used
2. Account for missing hours 0 through `start_hour-1` on days 2+
3. Consider re-running critical experiments with fixed version

## Commit Details

- **Date**: 2025-10-01
- **File Modified**: `src/simulations/simulation_orchestrator.py`
- **Lines Changed**: 185-187
- **Lines Added**: 2
- **Lines Removed**: 1
- **Test Status**: ✅ Passed
- **Simulation Status**: ✅ Runs successfully

## Related Issues

This bug would have been caught earlier with:
1. Unit tests for the simulation loop
2. Assertions checking expected hour counts per day
3. Data validation in output (checking for gaps)

## Recommendation

Add validation in future to detect missing hours:
```python
def validate_simulation_hours(results_df):
    """Ensure no hours are missing in multi-day simulations"""
    for day in results_df['day'].unique()[1:]:  # Skip first day
        day_hours = results_df[results_df['day'] == day]['hour'].unique()
        assert 0 in day_hours, f"Day {day} missing hour 0"
        assert len(day_hours) == 24, f"Day {day} has incomplete hours"
```

---

**Status**: ✅ **FIXED AND VERIFIED**
**Priority**: **CRITICAL** - Affects all multi-day simulations
**Impact**: Restores 18.2% of missing simulation data
