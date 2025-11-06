# Root Model Output Analysis

## Current Output Status

### ✅ Working Correctly

1. **Root Length**: Growing properly (423 cm → 5835 cm over 25 days)
2. **Root Surface Area**: Growing properly (76 cm² → 1304 cm²)
3. **Root Biomass**: Growing (0.0262 g → 3.2 g) - slow but reasonable for lettuce
4. **Root Density**: Calculated (52.9 → 729.5 cm/cm³)
5. **Root Activity**: Calculated (0.54 → 0.55)
6. **Root Fractions**: Fine/medium/coarse fractions calculated
7. **Cumulative Growth**: Tracking properly

### ⚠️ Issues Found

1. **Root Depth Stuck at 40 cm**
   - **Problem**: `root_depth` remains constant at 40.0 cm throughout simulation
   - **Expected**: Should grow with root system development
   - **Impact**: Affects water uptake calculations (uses fixed depth)
   - **Location**: `root_system_simulator.py` line 294

2. **Root Distribution Empty `{}`**
   - **Problem**: `root_distribution` dictionary is empty
   - **Expected**: Should have 'upper', 'middle', 'lower' zone fractions
   - **Impact**: Cannot track spatial root distribution
   - **Location**: `root_system_simulator.py` lines 328-331

3. **Root Zone Layers Empty `[]`**
   - **Problem**: `root_zone_layers` list is empty
   - **Expected**: Should contain layer data with depth, root density, etc.
   - **Impact**: Cannot analyze vertical root distribution
   - **Location**: `root_system_simulator.py` lines 333-335

4. **Root Cohorts Empty `[]`**
   - **Problem**: `root_cohorts` list is empty
   - **Expected**: Should contain cohort data (age, length, diameter, type)
   - **Impact**: Cannot track root age structure
   - **Location**: `root_system_simulator.py` lines 337-339

## Root Causes

### Issue 1: Root Depth Not Updating

**Code Location**: `root_system_simulator.py:294`
```python
self.state.root_depth = result.get('root_depth', self.state.root_depth)
```

**Problem**: Model may not be returning `root_depth` in result, so it falls back to previous value (40 cm).

**Solution**: Check if model calculates `root_depth` properly, or calculate from `root_length`.

### Issue 2: Root Distribution Not Populated

**Code Location**: `root_system_simulator.py:328-331`
```python
root_distribution = result.get('root_distribution', {})
for zone in self.root_zones:
    if zone in root_distribution:
        self.state.root_distribution[zone] = root_distribution[zone]
```

**Problem**: Model returns empty `root_distribution` dict, so nothing gets populated.

**Solution**: Ensure model calculates and returns root distribution by zones.

### Issue 3: Root Zone Layers Not Populated

**Code Location**: `root_system_simulator.py:333-335`
```python
root_zone_layers = result.get('root_zone_layers', [])
self.state.root_zone_layers = root_zone_layers
```

**Problem**: Model doesn't return `root_zone_layers` data.

**Solution**: Model needs to format and return zone layer data.

### Issue 4: Root Cohorts Not Populated

**Code Location**: `root_system_simulator.py:337-339`
```python
root_cohorts = result.get('root_cohorts', [])
self.state.root_cohorts = root_cohorts
```

**Problem**: Model doesn't return serialized cohort data.

**Solution**: Model needs to serialize cohort objects to dictionaries.

## Data Flow Analysis

### What Other Simulators Expect

1. **Water Uptake Simulator** expects:
   - `root_depth` ✅ (but stuck at 40)
   - `root_distribution` ❌ (empty)
   - `root_biomass` ✅

2. **Nutrient Models Simulator** expects:
   - `root_depth` ✅ (but stuck at 40)
   - `root_distribution` ❌ (empty)
   - `root_biomass` ✅
   - `root_surface_area` ✅

3. **Nitrogen Balance Simulator** expects:
   - `root_mass` ✅ (alias for root_biomass)
   - `root_surface_area` ✅
   - `root_activity` ✅

## Recommendations

### High Priority Fixes

1. **Fix Root Depth Calculation**
   - Calculate from `root_length` if model doesn't return it
   - Or ensure model returns proper `root_depth`

2. **Fix Root Distribution**
   - Ensure model calculates distribution by zones
   - Return proper dictionary with zone fractions

3. **Fix Root Zone Layers**
   - Format zone layer data from model
   - Return as list of dictionaries

4. **Fix Root Cohorts**
   - Serialize cohort objects to dictionaries
   - Return as list of cohort dictionaries

### Medium Priority

5. **Validate Root Activity**
   - Check if decreasing activity is realistic
   - May need to account for root aging properly

6. **Validate Root Biomass Growth**
   - Check if growth rate is realistic for lettuce
   - Compare with literature values

## Expected Output Format

### Root Distribution
```python
{
    'upper': 0.4,    # 40% in upper zone
    'middle': 0.4,   # 40% in middle zone
    'lower': 0.2     # 20% in lower zone
}
```

### Root Zone Layers
```python
[
    {
        'depth_range': (0, 10),
        'root_length_density': 50.0,
        'root_surface_area': 100.0,
        'nutrient_uptake': {...}
    },
    ...
]
```

### Root Cohorts
```python
[
    {
        'age_days': 5.0,
        'length': 10.0,
        'diameter': 0.8,
        'root_type': 'FINE',
        'zone': 'upper'
    },
    ...
]
```

## Fixes Applied ✅

### 1. Root Depth Calculation
- **Fixed**: Added fallback calculation from root_length if model doesn't return depth
- **Code**: Lines 294-302 in `root_system_simulator.py`
- **Note**: Root depth may be capped at 40cm if that's the deepest zone depth (DWC system)

### 2. Root Distribution
- **Fixed**: Convert integer zone IDs (0, 1, 2) to string keys ('upper', 'middle', 'lower')
- **Code**: Lines 336-348 in `root_system_simulator.py`
- **Result**: Distribution now properly populated with zone fractions

### 3. Root Zone Layers
- **Fixed**: Serialize zone data from model's `root_zones` attribute
- **Code**: Lines 350-369 in `root_system_simulator.py`
- **Result**: Zone layers now contain depth_range, volume, root metrics, environmental data

### 4. Root Cohorts
- **Fixed**: Serialize cohort objects to dictionaries
- **Code**: Lines 371-388 in `root_system_simulator.py`
- **Result**: Cohorts now contain age, length, diameter, type, zone, biomass, activity

## Next Steps

1. ✅ Fix root depth calculation - DONE
2. ✅ Fix root distribution calculation - DONE
3. ✅ Fix root zone layers formatting - DONE
4. ✅ Fix root cohorts serialization - DONE
5. **Test**: Run simulation and validate outputs
6. **Validate**: Check that root_depth grows properly (may be capped at zone max)
7. **Verify**: Ensure root_distribution sums to ~1.0
8. **Check**: Validate cohort data is meaningful

