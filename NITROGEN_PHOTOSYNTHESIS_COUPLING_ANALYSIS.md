# Nitrogen Stress Impact on Photosynthesis - Analysis Results

## ❌ CRITICAL ISSUE: Nitrogen-Photosynthesis Coupling is NOT Working

### Summary

**Question**: How much is photosynthesis affected by nitrogen stress?

**Answer**: **Photosynthesis is NOT being affected by nitrogen stress** due to a bug in the nitrogen-photosynthesis coupling mechanism.

---

## Key Findings

### 1. Nitrogen Stress Values
- **Nutrient stress**: 0.58 - 0.73 (mean: 0.64) - **HIGH**
- **N-NO3 concentration**: 36.1 mg/L (optimal: 150-250 mg/L) - **DEFICIENT**
- **Nitrogen availability**: 0.27 - 0.42 (mean: 0.36) - **LOW**

### 2. Photosynthesis Rates
- **Net assimilation**: 0.0000 - 0.1326 g C/hour (mean: 0.0357)
- **Daytime photosynthesis**: 26/67 steps (38.8%) have positive values
- **Cumulative carbon**: 35.34 g C

### 3. Correlation Analysis
- **Net assimilation vs Nutrient stress**: **+0.89** (POSITIVE correlation)
- **Expected**: Negative correlation (higher stress → lower photosynthesis)
- **Actual**: Positive correlation (photosynthesis increases with stress)

**This is WRONG** - photosynthesis should DECREASE with increasing nitrogen stress.

---

## Root Cause: Broken Nitrogen-Photosynthesis Coupling

### The Problem

The `nitrogen_area_based` value used by the photosynthesis model is **CONSTANT** (28.59 g N/m²) and does NOT update during simulation.

### Details

1. **Calculation Code Exists** (line 691-692 in `nitrogen_balance_simulator.py`):
   ```python
   leaf_n_area = (cumulative_n_g * 0.60) / leaf_area  # g N/m²
   self.state.nitrogen_area_based['leaves'] = leaf_n_area
   ```

2. **But Output is Constant**:
   - All values: **28.59 g N/m²** (never changes)
   - Should range from: **0.07 - 28.61 g N/m²** (based on calculation)
   - Calculation should execute (leaf_area > 0 for all steps)

3. **Impact on Photosynthesis**:
   - Leaf N appears **HIGH** (28.59 g N/m²)
   - Converted to **19.06%** → clamped to **5%** (maximum)
   - Nitrogen factor: **1.67** (66% INCREASE in Vcmax/Jmax)
   - Photosynthesis model thinks N is **OPTIMAL**
   - But actual N availability is **LOW** (36 mg/L)
   - **Result**: Nitrogen stress NOT affecting photosynthesis

### Why This Happens

The calculation uses:
- `cumulative_nitrogen_uptake` (total N ever taken up)
- Assumes 60% goes to leaves
- Divides by current leaf area

**Problems**:
1. Uses **cumulative** N instead of **current** leaf N content
2. Assumes all cumulative N is still in leaves (ignores growth, remobilization, losses)
3. Value appears to be initialized but never updated correctly

---

## Expected vs Actual Behavior

### Expected:
- Low N availability → Low leaf N → Low photosynthesis
- High nutrient stress → Reduced photosynthetic capacity
- Negative correlation between stress and photosynthesis

### Actual:
- Leaf N is constant (28.59 g N/m²) - NOT updating
- Photosynthesis increases with LAI (plant growth)
- Positive correlation between stress and photosynthesis (WRONG)
- Nitrogen-photosynthesis coupling NOT working

---

## Impact Assessment

### Current Impact:
1. **Photosynthesis is NOT responding to N deficiency**
   - Model thinks N is optimal (5% clamped value)
   - Nitrogen factor increases capacity by 66%
   - But actual N is deficient (36 mg/L vs 150-250 mg/L optimal)

2. **Photosynthesis increases due to LAI growth, not N response**
   - Early steps: 0.0424 g C/hour
   - Late steps: 0.1274 g C/hour
   - LAI increases: 0.91 → 2.22
   - This masks the N deficiency effect

3. **Stress calculations are correct, but not affecting photosynthesis**
   - Nutrient stress: 0.64 (high)
   - Integrated stress: 0.84-0.90 (CRITICAL)
   - But photosynthesis doesn't respond to this stress

---

## Recommendations

### Immediate Fix:
1. **Fix `nitrogen_area_based` calculation**:
   - Use **current leaf N content** from nitrogen pools, not cumulative uptake
   - Calculate as: `leaf_n_area = (current_leaf_n_g) / leaf_area`
   - Update correctly each step

2. **Alternative approach**:
   - Use `nitrogen_concentrations['leaves']` (g N/g dry mass)
   - Convert to area-based: `leaf_n_area = concentration * leaf_biomass / leaf_area`
   - This uses actual current N status

### Long-term Fix:
1. **Improve nitrogen tracking**:
   - Track current N in leaves (not just cumulative uptake)
   - Account for N used in growth, remobilization, losses
   - Use nitrogen pools/concentrations from model

2. **Verify photosynthesis model**:
   - Ensure nitrogen factor calculation is correct
   - Check conversion factors (g N/m² → %)
   - Verify clamping doesn't mask deficiencies

---

## Conclusion

**Nitrogen stress is NOT affecting photosynthesis** due to a broken coupling mechanism. The `nitrogen_area_based` value is constant and incorrect, causing the photosynthesis model to think nitrogen is optimal when it's actually deficient.

**Impact**: Photosynthesis rates are likely **overestimated** because the model doesn't account for nitrogen limitation.

**Priority**: **HIGH** - This is a critical model coupling issue that affects simulation accuracy.

---

## Files Involved

1. `src/simulations/nitrogen_balance_simulator.py` (lines 679-698)
   - `nitrogen_area_based` calculation
   
2. `src/simulations/photosynthesis_simulator.py` (lines 209-226)
   - Uses `nitrogen_area_based` for photosynthesis

3. `src/models/photosynthesis_model.py` (lines 193-196)
   - Nitrogen factor calculation

4. `output/nitrogen_balance.csv`
   - `nitrogen_area_based` column (constant value)

5. `output/photosynthesis.csv`
   - Photosynthesis rates (not responding to N stress)

