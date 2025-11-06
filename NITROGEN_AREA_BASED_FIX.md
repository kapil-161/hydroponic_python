# Nitrogen Area-Based Calculation Fix

## Summary

Fixed the `nitrogen_area_based` calculation to use **current leaf N content** instead of cumulative N uptake, enabling proper nitrogen-photosynthesis coupling.

## Changes Made

### File: `src/simulations/nitrogen_balance_simulator.py`

**Location**: Lines 679-723

**Before**:
```python
# Calculate leaf N content (assume 60% of total N goes to leaves)
leaf_n_fraction = 0.60
cumulative_n_g = self.state.cumulative_nitrogen_uptake  # grams
leaf_n_total = cumulative_n_g * leaf_n_fraction  # g N in leaves
leaf_n_area = leaf_n_total / leaf_area  # g N/m²
```

**After**:
```python
# Get current leaf N content from organ_states (updated by update_nitrogen_pools)
# This represents actual current N in leaves, accounting for allocation, remobilization, and growth
leaf_organ_state = balance_response.organ_states.get('leaves')
if leaf_organ_state is not None and leaf_organ_state.total_nitrogen > 0:
    # Use current leaf N content (g N) divided by leaf area (m²)
    leaf_n_total = leaf_organ_state.total_nitrogen  # g N in leaves (current)
    leaf_n_area = leaf_n_total / leaf_area  # g N/m² leaf area
    self.state.nitrogen_area_based['leaves'] = leaf_n_area
else:
    # Fallback: use nitrogen concentration * leaf biomass / leaf area
    # This handles cases where organ_states might not be initialized yet
    if leaf_biomass > 0:
        leaf_n_conc = self.state.nitrogen_concentrations.get('leaves', 0.0)
        if leaf_n_conc > 0:
            leaf_n_total = leaf_biomass * leaf_n_conc  # g N
            leaf_n_area = leaf_n_total / leaf_area  # g N/m²
            self.state.nitrogen_area_based['leaves'] = leaf_n_area
        else:
            self.state.nitrogen_area_based['leaves'] = 2.5  # g N/m² (typical optimal)
    else:
        self.state.nitrogen_area_based['leaves'] = 2.5  # g N/m²
```

## Key Improvements

1. **Uses Current N Content**: Now uses `balance_response.organ_states['leaves'].total_nitrogen` which represents the **actual current N in leaves** after accounting for:
   - N allocation
   - N remobilization
   - Growth (which dilutes N concentration)
   - N losses

2. **Fallback Mechanisms**: Includes multiple fallback options:
   - Primary: Use organ_states from model (most accurate)
   - Secondary: Use nitrogen_concentrations * leaf_biomass (if organ_states not available)
   - Tertiary: Use default value (2.5 g N/m²) if no data available

3. **Proper Timing**: Calculation happens **after** `update_nitrogen_pools()` is called, ensuring organ_states are up-to-date

## Expected Impact

### Before Fix:
- `nitrogen_area_based['leaves']` was constant (28.59 g N/m²)
- Used cumulative N uptake (total ever taken up)
- Didn't account for N used in growth, remobilization, losses
- Photosynthesis model thought N was optimal (clamped to 5%)
- Nitrogen stress NOT affecting photosynthesis

### After Fix:
- `nitrogen_area_based['leaves']` will vary with actual leaf N content
- Uses current N in leaves (after allocation, growth, remobilization)
- Accurately reflects N deficiency conditions
- Photosynthesis model will correctly respond to N stress
- **Expected**: Negative correlation between N stress and photosynthesis

## Testing Recommendations

1. **Run simulation** and check `output/nitrogen_balance.csv`:
   - Verify `nitrogen_area_based` column varies over time
   - Check values are in reasonable range (2.5-4.0 g N/m² optimal)

2. **Check photosynthesis response**:
   - Verify `output/photosynthesis.csv` shows reduced rates under N stress
   - Check correlation between `nutrient_stress` and `net_assimilation_rate` is **negative**

3. **Verify nitrogen factor**:
   - Check that photosynthesis model receives varying leaf N values
   - Verify nitrogen factor decreases with N deficiency

## Related Files

- `src/simulations/photosynthesis_simulator.py` - Uses `nitrogen_area_based` for photosynthesis
- `src/models/photosynthesis_model.py` - Calculates nitrogen factor from leaf N
- `src/models/nitrogen_balance.py` - Provides `organ_states` with current N content

## Status

✅ **Fix Complete** - Ready for testing

