# Code Quality Rules

## Parameter Management
- no fallback code
- no default value in code
- no hardcoded values in code, only in csv
- all input data should come from one source, no confusion
- eliminate all duplicate parameters across CSV files
- consolidate parameters with different naming for same functionality
- remove parameters with reversed naming patterns (e.g., heat_damage_rate vs damage_rate_heat)
- map cross-category parameter references correctly

## Code Structure
- no duplicate code and parameters
- no two functions or codes for same calculation
- clean dead codes
- remove unused variables and imports
- remember to reduce code volume, i want minimal functional code
- update all model references when parameters are consolidated

## Data Integrity
- No fabricated or fake data
- prioritize scientific method rather than code modification for better result
- verify simulation functionality after parameter cleanup
- ensure no functionality loss during consolidation

## Testing Requirements
- test simulation runs after parameter changes
- verify parameter count reduction
- confirm same performance metrics after cleanup
- validate all models work with consolidated parameters
- prioritize to reduce paramters, because it makes hard for calibration