# Code Quality Rules

## Parameter Management
- dont put values on csv which should come out from each model file. 
- no fallback code
- dont make premature success claims 
- no default value in code
- no hardcoded values in code, only in csv
- all input data should come from one source, no confusion
- eliminate all duplicate parameters across CSV files
- consolidate parameters with different naming for same functionality
- remove parameters with reversed naming patterns (e.g., heat_damage_rate vs damage_rate_heat)
- map cross-category parameter references correctly
- dont add weather parameters again in masters parameter, weather daily parameter should be used
-strictly follows the "no shortcuts, no defaults, all 
  from CSV" rule. Every critical parameter comes from the CSV files
## for simulator
- should use daily weather file for simulation
- should use all model file and their functions 
- all parameters value should be in csv file 
- no default or hardcoded value in code file
- no fallback to simple formula instead of model file formula 
- no fallback to default value 
-should raise error if anything doesnot work
- should work according to plan
## Code Structure
- no duplicate code and parameters
- no two functions or codes for same calculation (like simple and complex)
- clean dead codes
- please search existing function before creating because we have all codes in our codebase
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
-src/cropgro_hydroponic_simulator.py should integrate all 17 specialized models
- confirm same performance metrics after cleanup
- validate all models work with consolidated parameters
- prioritize to reduce paramters, because it makes hard for calibration

## To do
    ☒Find and eliminate any hardcoded values in code, ensuring all data comes from CSV
    ☒ Remove any fallback/default code paths that bypass CSV parameters
    ☒ Identify and merge duplicate calculation functions across models
    ☒ Remove unused imports and variables throughout the codebase
    ☒ Update all model references after parameter consolidation
    ☒ Verify simulation runs correctly after parameter cleanup
    ☒ Confirm same performance metrics after cleanup