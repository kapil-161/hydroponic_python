# Unit Inconsistency Report - Hydroponic Research Framework

**Generated:** 2025-10-22  
**Analysis Method:** Code trace + CSV verification + Execution flow analysis

---

## Executive Summary

Found **8 critical unit inconsistencies** that affect model calculations and data flow across the codebase. These inconsistencies violate the "Single Source of Truth" principle and create potential scientific accuracy issues.

---

## Critical Issues (Must Fix)

### 1. **DUPLICATE PARAMETERS WITH CONFLICTING UNITS**

#### 1.1 Nutrient Uptake Vmax - CRITICAL ⚠️

**Location:** `input/roots.csv` vs `input/nutrient.csv`

**Issue:** Same parameters defined twice with different units AND different values

| Parameter | File | Value | Unit | Line |
|-----------|------|-------|------|------|
| no3_uptake_vmax | roots.csv | 0.5 | mg_g_root_day | 89 |
| no3_uptake_vmax | roots.csv | 0.03 | mg_cm2_day | 245 |
| kinetics_n_no3_vmax | nutrient.csv | 0.051 | mg_cm2_day | - |
| nh4_uptake_vmax | roots.csv | 0.3 | mg_g_root_day | 90 |
| nh4_uptake_vmax | roots.csv | 0.02 | mg_cm2_day | 247 |
| kinetics_n_nh4_vmax | nutrient.csv | 0.020 | mg_cm2_day | - |
| po4_uptake_vmax | roots.csv | 0.2 | mg_g_root_day | 91 |
| po4_uptake_vmax | roots.csv | 0.08 | mg_cm2_day | 249 |
| kinetics_p_po4_vmax | nutrient.csv | 0.0008 | mg_cm2_day | - |
| k_uptake_vmax | roots.csv | 0.4 | mg_g_root_day | 92 |
| k_uptake_vmax | roots.csv | 0.10 | mg_cm2_day | 251 |
| kinetics_k_vmax | nutrient.csv | 0.006 | mg_cm2_day | - |
| ca_uptake_vmax | roots.csv | 0.3 | mg_g_root_day | 93 |
| ca_uptake_vmax | roots.csv | 0.06 | mg_cm2_day | 253 |
| kinetics_ca_vmax | nutrient.csv | 0.04 | mg_cm2_day | - |
| mg_uptake_vmax | roots.csv | 0.2 | mg_g_root_day | 94 |
| mg_uptake_vmax | roots.csv | 0.05 | mg_cm2_day | 255 |
| kinetics_mg_vmax | nutrient.csv | 0.02 | mg_cm2_day | - |
| so4_uptake_vmax | roots.csv | 0.1 | mg_g_root_day | 95 |
| so4_uptake_vmax | roots.csv | 0.04 | mg_cm2_day | 257 |
| kinetics_s_so4_vmax | nutrient.csv | 0.02 | mg_cm2_day | - |

**Code Impact:**
- `NutrientModel` (line 619): `uptake_per_cm2 = (k['vmax'] * concentration) / (k['km'] + concentration)`
- Uses `kinetics_*_vmax` from nutrient.csv in `mg_cm2_day`
- Multiplies by `root_surface_area` (cm²) to get `mg/day`
- BUT roots.csv has duplicate parameters that are not being used

**Scientific Impact:** CRITICAL - Three different values for same nutrient uptake rate creates ambiguity in which is scientifically correct

**Fix Required:** 
1. Determine which values are scientifically correct
2. Remove duplicates from roots.csv (lines 89-95 OR lines 245-257)
3. Keep only kinetics_* parameters in nutrient.csv

---

#### 1.2 Flow Rate Units - L_day vs L_min vs L/min vs L/day

**Location:** `input/roots.csv`

**Issue:** Same flow parameters with incompatible units (daily vs per-minute)

| Parameter | Line | Value | Unit | Notes |
|-----------|------|-------|------|-------|
| flow_stress_threshold | 41 | 0.5 | L_day | Daily rate |
| flow_stress_threshold | 231 | 4.0 | L_min | Per-minute rate |
| optimal_flow_rate | 42 | 1.0 | L_day | Daily rate |
| optimal_flow_rate | 230 | 1.5 | L_min | Per-minute rate |
| optimization_flow_min | 82 | 0.1 | L_day | Daily rate |
| optimization_flow_min | 294 | 0.5 | L/min | Per-minute rate (slash notation) |
| optimization_flow_max | 83 | 2.0 | L_day | Daily rate |
| optimization_flow_max | 295 | 3.0 | L/min | Per-minute rate (slash notation) |
| optimization_flow_step | 84 | 0.1 | L_day | Daily rate |
| optimization_flow_step | 296 | 0.5 | L/min | Per-minute rate (slash notation) |

**Code Impact:**
- Unclear which value is loaded by parameter loader
- Daily vs per-minute conversion factor is 1440x difference!
- 0.5 L/day ≠ 0.5 L/min (720 L/day)

**Fix Required:**
1. Standardize on one time unit (recommend L_day for consistency with water_uptake_rate)
2. Remove duplicate parameters
3. Convert values appropriately if needed

**Also Note:** Inconsistent notation - `L_min` vs `L/min` (underscore vs slash)

---

#### 1.3 Temperature Units - °C vs C vs K

**Location:** `input/initials.csv` vs other CSV files

**Issue:** Temperature units not standardized

| Parameter | File | Unit | Count |
|-----------|------|------|-------|
| root_zone_temperature | initials.csv | C | Missing degree symbol |
| canopy_temperature | initials.csv | C | Missing degree symbol |
| Most other temps | *.csv | °C | Standard notation |
| reference_temp_kelvin | constants.csv | K | Kelvin (correct) |
| vapor_pressure_base_temp | constants.csv | K | Should be °C! |
| vapor_pressure_base_temp | water.csv | °C | Correct unit |

**Scientific Impact:** 
- `vapor_pressure_base_temp` = 237.3 in Magnus equation
- Constants.csv says 237.3 K = -35.85°C (WRONG!)
- Should be 237.3 °C (as in water.csv)
- This affects vapor pressure calculations in photosynthesis and water uptake

**Code Impact:**
```python
# photosynthesis_model.py, water_uptake_model.py
# Magnus equation: es = 0.611 * exp(17.27*T/(T+237.3))
# Expects T in °C, not K
```

**Fix Required:**
1. Change vapor_pressure_base_temp unit in constants.csv from K to °C
2. Standardize temperature notation: Use °C consistently (not C)
3. Keep K only for Kelvin conversion and reference temperatures

---

#### 1.4 Temperature Sensitivity Units - per_°C vs °C_inverse vs per_C

**Location:** Multiple CSV files

**Issue:** Three different notations for same physical quantity (1/°C)

| Parameter | File | Unit | Line |
|-----------|------|------|------|
| temperature_decay_factor | roots.csv | per_°C | - |
| temperature_decay_factor | roots.csv | dimensionless | DUPLICATE |
| temperature_decay_factor | respiration.csv | °C_inverse | - |
| temperature_sensitivity | water.csv | °C_inverse | - |
| temperature_coefficient_alpha | nutrient.csv | per_C | - |
| water_uptake_sensitivity_low | water.csv | per_°C | - |
| water_uptake_sensitivity_high | water.csv | per_°C | - |

**Fix Required:**
1. Standardize on one notation: `per_°C` (most common)
2. Remove duplicate temperature_decay_factor in roots.csv
3. Change all `°C_inverse` and `per_C` to `per_°C`

---

#### 1.5 Penman-Monteith Constants - Dimensional vs Dimensionless

**Location:** `input/constants.csv` vs `input/water.csv`

**Issue:** Same parameters with different units

| Parameter | File | Unit | Value | Correct? |
|-----------|------|------|-------|----------|
| saturation_curve_slope_constant | constants.csv | kPa_K | 4098 | Wrong |
| saturation_curve_slope_constant | water.csv | dimensionless | 4098.0 | Wrong |
| penman_monteith_conversion | constants.csv | kPa_°C | 0.408 | Wrong |
| penman_monteith_conversion | water.csv | dimensionless | 0.408 | Wrong |
| aerodynamic_resistance_coefficient | constants.csv | s_m | 900.0 | Correct |
| aerodynamic_resistance_coefficient | water.csv | dimensionless | 900.0 | Wrong |
| wind_speed_coefficient | constants.csv | s_m | 0.34 | Correct |
| wind_speed_coefficient | water.csv | dimensionless | 0.34 | Wrong |

**Scientific Analysis:**
From FAO-56 Penman-Monteith equation:
- `saturation_curve_slope_constant`: Should be dimensionless (used in equation as coefficient)
- `penman_monteith_conversion`: 0.408 is MJ⁻¹·mm·m²·kPa (conversion factor), not dimensionless
- `aerodynamic_resistance_coefficient`: 900 s/m from FAO-56 equation numerator
- `wind_speed_coefficient`: 0.34 s/m from FAO-56 equation denominator

**Fix Required:**
1. Correct units in constants.csv based on FAO-56 specification
2. Remove duplicates from water.csv
3. Document actual units with references

---

### 2. **UNIT NOTATION INCONSISTENCIES**

#### 2.1 Underscore vs Slash Notation

**Issue:** Mixed notation style reduces readability

| Underscore Style | Slash Style |
|-----------------|-------------|
| L_day | L/day |
| L_min | L/min |
| mg_cm2_day | mg/cm²/day |
| mg_L | mg/L |
| per_°C | /°C |
| kPa_°C | kPa·°C |

**Current Usage:**
- Mostly underscore in CSV files: `L_day`, `mg_cm2_day`, `mg_L`
- Some slash in roots.csv: `L/min`
- One mixed: `mm/day` (water.csv minimum_et0_threshold)

**Recommendation:**
- Standardize on **underscore notation** throughout (easier to parse programmatically)
- Change `L/min` → `L_min` and `mm/day` → `mm_day`

---

### 3. **TIME UNIT INCONSISTENCIES**

#### 3.1 Daily vs Hourly Conversions

**Code Analysis:**

**Water Uptake:**
```python
# water_uptake_model.py returns DAILY values
transpiration_L: float  # L/day
total_water_uptake_L: float  # L/day

# water_uptake_simulator.py converts to hourly
self.state.water_uptake_rate = result.total_water_uptake_L / 24.0  # L/hour
self.state.transpiration_rate = result.transpiration_L / 24.0  # L/hour
```

**Nutrient Uptake:**
```python
# nutrient_models.py calculates DAILY rates
# vmax in mg_cm2_day × root_surface_area → mg/day
uptake_rates_mg_per_plant_per_day: Dict[str, float]

# nutrient_models.py line 640-641
daily_uptake_per_plant = uptake_rates[nutrient]  # mg/plant/day
hourly_uptake_per_plant = daily_uptake_per_plant / 24.0  # mg/plant/hour
```

**Issue:** 
- Models calculate daily rates
- Simulators convert to hourly rates
- State variables store hourly rates
- But CSV initial values are in daily rates

**CSV Examples:**
```
water_uptake_rate,0.01,L_day  (initials.csv) → Should be L_hour?
n_uptake_rate,0.5,mg_day  (initials.csv) → Should be mg_hour?
```

**Recommendation:**
1. Clarify unit in CSV: `L_day` for daily rates, use comments if stored as hourly
2. OR: Store initial values in same units as state variables (hourly)
3. Document conversion points clearly in code

---

### 4. **MISSING UNIT CONVERSIONS**

#### 4.1 Water Volume Conversion

**Code Location:** `water_uptake_model.py:352-355`

```python
# transpiration_mm (mm/day) × ground_area (m²) = volume (L/day)
# Unit conversion: mm × m² = L (because 1 mm × 1 m² = 0.001 m³ = 1 L)
transpiration_L = transpiration_mm * self.params.ground_area_per_plant
```

**Verification:**
- 1 mm rain over 1 m² = 0.001 m × 1 m² = 0.001 m³ = 1 L ✓ CORRECT
- ground_area_per_plant = 0.06 m² (from water.csv)
- transpiration_mm = 5 mm/day → transpiration_L = 5 × 0.06 = 0.3 L/day ✓

**Status:** ✓ Correct (verified)

---

## Summary of Required Fixes

### High Priority (Affects Calculations)

1. **Remove duplicate nutrient uptake vmax parameters from roots.csv**
   - Lines 89-95 OR lines 245-257
   - Keep only kinetics_*_vmax in nutrient.csv

2. **Fix vapor_pressure_base_temp unit in constants.csv**
   - Change from K to °C
   - Value 237.3 is in Celsius, not Kelvin

3. **Remove duplicate flow rate parameters from roots.csv**
   - Standardize on L_day units
   - Remove either daily or per-minute versions

4. **Fix Penman-Monteith constant units**
   - Remove duplicates from water.csv
   - Correct units in constants.csv per FAO-56

### Medium Priority (Affects Clarity)

5. **Standardize temperature notation**
   - Use °C consistently (not C)
   - Use per_°C for inverse temperature units

6. **Standardize unit notation**
   - Use underscore throughout (L_day not L/day)
   - Change mm/day → mm_day

7. **Fix temperature_decay_factor duplicate in roots.csv**
   - Remove dimensionless version, keep per_°C

### Low Priority (Documentation)

8. **Document time unit conversions**
   - Add comments where daily→hourly conversions occur
   - Consider renaming state variables to include time unit

---

## Verification Checklist

After fixes, verify:

- [ ] No duplicate parameters across CSV files
- [ ] All related parameters use same units
- [ ] All temperature parameters use °C (except Kelvin conversions)
- [ ] All time-based rates specify daily or hourly explicitly
- [ ] All unit notations use underscore style
- [ ] Vapor pressure calculations use correct temperature unit
- [ ] Nutrient uptake uses single set of kinetics parameters
- [ ] Flow rates use consistent time unit

---

## References

- FAO-56: Allen et al. (1998) Crop evapotranspiration guidelines
- Magnus equation: Temperature in °C, not K
- Michaelis-Menten kinetics: Vmax should be per surface area or per biomass (consistent)
- DSSAT documentation for unit conventions

---

**Analysis completed by systematic code trace and CSV verification**
