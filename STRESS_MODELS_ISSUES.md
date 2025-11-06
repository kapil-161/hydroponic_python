# Stress Models Issues Found

## Critical Issues

### 1. ❌ INTEGRATED STRESS ALWAYS 1.0

**Problem**: `integrated_stress` is always 1.0, indicating no stress, but individual stresses show significant values:
- Temperature stress: 0.05-0.69 (mean: 0.40)
- Water stress: 0.015-0.12 (mean: 0.04)
- Nutrient stress: 0.58-0.73 (mean: 0.64)

**Root Cause**: Key mismatch in `calculate_integrated_stress()` method.

**Location**: `src/models/stress_models.py` lines 1078-1090

**Issue Details**:
- `current_stress_levels` dictionary uses keys like `'temperature_stress'`, `'water_stress'`, etc.
- But `self.stress_states` uses keys from `parameters.stress_weights.keys()` which are `'temperature'`, `'water'`, etc. (without `_stress` suffix)
- When `update_stress_states()` is called, it checks `if st_type not in self.stress_states:` and skips all updates because keys don't match
- Stress states remain at initial value of 1.0 (no stress)
- All process responses calculate with stress_level=1.0 → no impact → `combined_stress_factor=1.0` → `overall_stress_factor=1.0`

**Fix Required**: Map keys correctly before calling `daily_update()`:

```python
# In calculate_integrated_stress(), before calling daily_update():
# Map keys from 'temperature_stress' to 'temperature'
key_mapping = {
    'temperature_stress': 'temperature',
    'water_stress': 'water',
    'nutrient_stress': 'nutrient',
    'light_stress': 'light',
    'ph_stress': 'ph',
    'salinity_stress': 'salinity'
}

mapped_stress_levels = {}
for key, value in current_stress_levels.items():
    mapped_key = key_mapping.get(key, key.replace('_stress', ''))
    mapped_stress_levels[mapped_key] = value

response = self.daily_update(mapped_stress_levels)
```

### 2. ❌ STRESS SEVERITY ALWAYS "MILD"

**Problem**: All entries show `stress_severity = "MILD"` even with significant individual stresses.

**Root Cause**: Same as issue #1 - because `overall_stress_factor=1.0`, severity calculation always results in "MILD":
```python
severity = ("mild" if overall > 0.8 else ...)  # overall=1.0 → always "mild"
```

**Fix**: Will be fixed when issue #1 is resolved.

### 3. ⚠️ CUMULATIVE STRESS VALUES TOO LARGE

**Problem**: `cumulative_stress` values are in millions (9,000 - 5,706,000), suggesting incorrect accumulation.

**Location**: `src/simulations/stress_models_simulator.py` line 356

**Issue Details**:
```python
hourly_stress = self.state.integrated_stress * 3600
self.state.cumulative_stress += hourly_stress
```

This multiplies stress by seconds (3600), which is incorrect. Should accumulate stress directly, not multiply by time.

**Fix Required**:
```python
# Change from:
hourly_stress = self.state.integrated_stress * 3600
self.state.cumulative_stress += hourly_stress

# To:
self.state.cumulative_stress += self.state.integrated_stress
```

## Working Correctly ✅

1. **Individual stress calculations**: Temperature, water, and nutrient stresses are varying correctly
2. **Light, pH, salinity stresses**: All 0.0 (probably correct for optimal conditions)
3. **Stress value ranges**: All within expected 0.0-1.0 range

## Summary

**Critical Fix Needed**: Key mapping in `calculate_integrated_stress()` to match stress state keys.

**Minor Fix Needed**: Cumulative stress accumulation (remove time multiplication).

**Impact**: Once fixed, `integrated_stress` will properly reflect combined stress levels, and severity classification will work correctly.

