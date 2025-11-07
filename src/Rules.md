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

