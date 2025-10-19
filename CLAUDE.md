# Hydroponic Research Framework Rules

## Core Philosophy
**This is a research framework, not production software. Prioritize scientific accuracy over software engineering complexity.**

## Major Rules Summary

### 🚫 **ABSOLUTE PROHIBITIONS**
1. **NO HARDCODED VALUES** - All values must come from CSV files
2. **NO DEFAULT VALUES** - Missing parameters must raise errors, not use defaults
3. **NO FALLBACK CODE** - No temporary solutions or shortcuts
4. **NO DUPLICATES** - Each parameter must exist only once
5. **NO FABRICATED DATA** - All data must be scientifically valid

### ✅ **MANDATORY REQUIREMENTS**
1. **Single Source of Truth** - All parameters from CSV files only
2. **Scientific Accuracy** - All equations must be scientifically correct
3. **Model Integration** - All 17 specialized models must work together
4. **Error Handling** - Raise errors when parameters are missing
5. **Naming Consistency** - Follow standardized naming conventions
6. **Always use efficient way to improve code** - Generate short reports 
7. **Always use consistent name** The naming isn't consistent (initial_ vs default_)

## Parameter Management Rules

### Core Principles
- **Single Source of Truth**: All parameters must come from CSV files only
- **No Model Outputs in CSV**: Don't put calculated values in CSV that should come from model outputs
- **Model Chain**: One model's output can be another model's input (dynamic relationships)
- **No Shortcuts**: Strictly follow "no shortcuts, no defaults, all from CSV" rule

### Parameter Naming Standards
- **Use Full Words**: `temperature` not `temp`, `minimum` not `min`, `maximum` not `max`
- **Consistent Structure**: `category_property_type` (e.g., `stress_temperature_threshold`)
- **Standard Suffixes**: `_threshold`, `_rate`, `_factor`, `_sensitivity`
- **Standard Prefixes**: `stress_`, `damage_`, `optimal_`, `minimum_`, `maximum_`
- **No Abbreviations**: Except scientific standards (`ec`, `ph`, `vpd`, `lai`, `gdd`)

### Duplicate Elimination
- **Eliminate All Duplicates**: No parameters with different names for same functionality
- **Consolidate Naming**: Remove reversed naming patterns (e.g., `heat_damage_rate` vs `damage_rate_heat`)
- **Cross-Category Mapping**: Map parameter references correctly across categories
- **Weather Parameters**: Don't duplicate weather parameters in master file

### Parameter Validation
- **Missing Parameters**: Raise errors, don't create minimal defaults
- **Parameter Count**: Prioritize reducing parameters (easier calibration)
- **Functionality Verification**: Ensure no functionality loss during consolidation
## Simulator Requirements

### Model Integration
- **Use All Models**: Must integrate all 17 specialized models
- **Daily Weather Data**: Use daily weather file for simulation
- **Model Functions**: Use all model file functions, no shortcuts
- **Dynamic Relationships**: Models must work together with proper data flow

### Parameter Handling
- **CSV Only**: All parameter values must be in CSV files
- **No Code Values**: No default or hardcoded values in code files
- **No Fallbacks**: No fallback to simple formulas instead of model formulas
- **Error on Missing**: Raise errors when parameters are missing from CSV
- **No Minimal Defaults**: Don't create minimal defaults based on parameter type

### Scientific Accuracy
- **Scientifically Correct**: All equations must be scientifically accurate
- **Research Focus**: Prioritize scientific method over code modification for better results
- **No Fabricated Data**: All data must be real and scientifically valid
## Code Structure Rules

### Duplicate Elimination
- **No Duplicate Code**: No duplicate functions or parameters
- **No Duplicate Calculations**: No two functions for same calculation (simple vs complex)
- **Search Before Creating**: Always search existing functions before creating new ones
- **Clean Dead Code**: Remove unused variables, imports, and dead code

### Code Quality
- **Minimal Functional Code**: Reduce code volume, keep only essential functionality
- **Dynamic Relationships**: Code must mimic real plant growth with dynamic variables and interrelations
- **Model References**: Update all model references when parameters are consolidated
- **Consistent Style**: Use tools like black or ruff for consistent code style

### Model Integration
- **Model Cooperation**: Ensure different models work together correctly
- **Parameter Changes**: Changes to parameters must not break simulation
- **Correct Results**: Model must continue producing scientifically correct results

## Data Integrity Rules

### Scientific Standards
- **No Fabricated Data**: All data must be scientifically valid and real
- **Scientific Method Priority**: Prioritize scientific method over code modification for better results
- **Research Focus**: This is research software, not production - prioritize accuracy over complexity

### Data Validation
- **Functionality Verification**: Verify simulation functionality after parameter cleanup
- **No Functionality Loss**: Ensure no functionality loss during consolidation
- **Parameter Validation**: All parameters must be validated for scientific accuracy

## Testing Requirements

### Simulation Testing
- **Test After Changes**: Test simulation runs after parameter changes
- **Parameter Count**: Verify parameter count reduction (easier calibration)
- **Model Integration**: `src/cropgro_hydroponic_simulator.py` must integrate all 17 specialized models
- **Performance Metrics**: Confirm same performance metrics after cleanup
- **Model Validation**: Validate all models work with consolidated parameters

### Quality Assurance
- **No Premature Success**: Don't make premature success claims
- **Thorough Testing**: Test all functionality after any changes
- **Error Handling**: Ensure proper error handling for missing parameters

## AI Agent Rules

### Parameter Management
- **Search First**: Always search existing parameters before creating new ones
- **No Duplicates**: Never create parameters with different names for same functionality
- **Follow Naming Rules**: Strictly follow standardized naming conventions
- **Consolidate When Found**: Consolidate duplicates when discovered

### Code Development
- **No Hardcoded Values**: Never add hardcoded values to code
- **No Default Values**: Never create default values for missing parameters
- **No Fallback Code**: Never create temporary solutions or shortcuts
- **Scientific Accuracy**: All equations must be scientifically correct

## Completed Tasks ✅
- ☒ Find and eliminate any hardcoded values in code, ensuring all data comes from CSV
- ☒ Remove any fallback/default code paths that bypass CSV parameters
- ☒ Identify and merge duplicate calculation functions across models
- ☒ Remove unused imports and variables throughout the codebase
- ☒ Update all model references after parameter consolidation
- ☒ Verify simulation runs correctly after parameter cleanup
- ☒ Confirm same performance metrics after cleanup
- ☒ Standardize parameter naming conventions
- ☒ Eliminate duplicate parameters with conflicting values

## Research Framework Principles

**Remember: This is a research framework, not production software. The research framework should be strong and scientifically accurate, not complicated with unnecessary software engineering features.**


Analyze model data flow and dependencies

Check for circular dependencies

Verify model output compatibility

Check communication bus usage

Identify missing model connections

Generate integration recommendations