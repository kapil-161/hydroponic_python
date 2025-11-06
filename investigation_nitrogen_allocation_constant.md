# Investigation Report: Constant Nitrogen Allocation Variables

## Problem
5 nitrogen balance variables are constant:
- `total_nitrogen_allocation`: 0.0007 g/plant/day
- `leaf_nitrogen_allocation`: 0.0002 g/plant/day
- `stem_nitrogen_allocation`: 0.0001 g/plant/day
- `root_nitrogen_allocation`: 0.0004 g/plant/day
- `nitrogen_stress_index`: 0.1

## Root Cause Analysis

### Chain of Causality
1. **Net carbon gain is always negative** (0/67 positive values)
   - Range: -0.073400 to -0.003200 g C/hour
   - Photosynthesis < Respiration at all data collection times

2. **Biomass is constant** (1 unique value in CSV)
   - `leaf_biomass`: 0.015 g (constant)
   - `stem_biomass`: 0.005 g (constant)
   - `root_biomass`: 0.0262 g (constant)
   - Biomass only updates when `hourly_biomass_gain > 0`
   - Since net carbon is negative, biomass never increases

3. **Growth rates are constant** (always 0 or estimated from nitrogen)
   - Growth rates = (biomass - prev_biomass) * 24
   - Since biomass is constant, growth rates = 0
   - Fallback: estimate from nitrogen uptake
   - But nitrogen uptake is similar at data collection times → similar estimates

4. **Allocation values are constant**
   - Nitrogen allocation depends on growth rates
   - Constant growth rates → constant allocation values

## Conclusion

**The nitrogen balance simulator is working correctly.** The constant allocation values are a symptom, not the cause. The root issue is:

**Photosynthesis < Respiration** → No biomass growth → Constant allocation

## Next Steps

This is a **photosynthesis/respiration balance issue**, not a nitrogen balance issue. To fix:

1. **Investigate photosynthesis model:**
   - Why is net assimilation so low (max 0.1281 g C/hour)?
   - Check light intensity, CO2 concentration, LAI, stress factors

2. **Investigate respiration model:**
   - Why is respiration so high (0.0032-0.2009 g C/hour)?
   - Check maintenance respiration, growth respiration, temperature

3. **Check environmental conditions:**
   - Light intensity at data collection times (hours 0, 12, 23)
   - Temperature (affects both photosynthesis and respiration)
   - CO2 concentration

4. **Verify data collection timing:**
   - Data collected at hours 0, 12, 23
   - Hour 0 and 23 are nighttime (no photosynthesis)
   - Only hour 12 has daylight
   - Net carbon might be positive at other hours not captured

## Status

✅ **Nitrogen balance simulator: Working correctly**
- Model state updates properly
- Growth stage conversion working
- Environmental factors normalized correctly
- Allocation values calculated correctly from model

⚠️ **Upstream issue: Photosynthesis/Respiration balance**
- Net carbon gain is negative
- Biomass not growing
- This causes constant allocation values

## Recommendation

Address the photosynthesis/respiration balance issue first. Once biomass starts growing, allocation values should become dynamic.

