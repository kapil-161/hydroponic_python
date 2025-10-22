# Hydroponic Simulation Framework - Quick Reference Card

## 📊 Project Statistics
```
Total Code:           ~18,756 lines
Models:               12 biological models
Simulators:           11 independent simulators  
Parameters:           ~544 in 17 CSV files
Architecture:         Event-driven distributed
```

## 🏗️ Architecture Components

### Core Layers
1. **Parameter System** (17 CSV files) → StrictParameterLoader
2. **Model Layer** (12 models, 8,395 LOC) → Stateless calculations
3. **Simulator Layer** (11 simulators, 7,512 LOC) → State management
4. **Orchestration** (771 LOC) → Coordination & timing
5. **Communication** (360 LOC) → Message bus

### The 11 Simulators (Execution Order)
```
1. phenology_simulator         → Growth stages
2. root_system_simulator       → Root dynamics
3. water_uptake_simulator      → Transpiration
4. nutrient_models_simulator   → Multi-nutrient
5. leaf_development_simulator  → Leaf growth
6. stress_models_simulator     → 7 stress types
7. canopy_architecture_simulator → Light interception
8. photosynthesis_simulator    → Carbon assimilation
9. respiration_simulator       → Carbon costs
10. biomass_allocation_simulator → Organ partitioning
11. nitrogen_balance_simulator  → N dynamics
```

## �� Directory Structure
```
hydroponic_python/
├── main.py                    # Entry point
├── src/
│   ├── models/               # 12 biological models
│   ├── simulations/          # 11 simulators + orchestrator
│   └── utils/                # Loaders & utilities
├── input/                    # 17 CSV parameter files
├── output/                   # Simulation results
└── scripts/                  # Analysis tools
```

## 🔄 Execution Flow
```
main.py
  → Load 17 CSV files (strict, no defaults)
  → Load weather data
  → Create 11 simulators
  → Register with orchestrator
  → Simulation loop:
      For each day (until harvest):
        For each hour (24 timesteps):
          Execute in dependency order
          Update shared cache
          Collect data
          Check harvest maturity
  → Export 12 CSV result files
  → Display metrics
```

## 📝 Key Files

### Input (17 CSV)
- **Core:** constants, genetics, initials
- **Models:** phenology, photo, respiration, allocation, canopy, leaf, roots, water, nitrogen_balance, nutrient, stress
- **System:** master_parameters, weather, observed_data

### Output (12 CSV)
- simulation_results.csv (combined)
- 11 individual simulator CSVs

### Code
- **Entry:** main.py (118 LOC)
- **Runner:** distributed_simulation_runner.py (342 LOC)
- **Orchestrator:** simulation_orchestrator.py (771 LOC)
- **Bus:** communication_bus.py (360 LOC)

## 🎯 Design Patterns Used
```
✓ Event-Driven Architecture   (Message bus)
✓ Microservices               (Independent simulators)
✓ Dependency Injection        (CSV parameters)
✓ State Pattern               (Simulator states)
✓ Observer Pattern            (Event subscriptions)
✓ Strategy Pattern            (Execution modes)
✓ Singleton Pattern           (Global message bus)
```

## 🔧 Running the Simulation
```bash
# Activate environment
source hydroponic_env/bin/activate

# Run
python3 main.py

# Results in: output/simulation_results.csv + 11 individual files
```

## 📊 Model Complexity (Top 5)
```
1. stress_models.py      1,485 LOC  ⭐⭐⭐⭐⭐
2. root_system_model.py  1,277 LOC  ⭐⭐⭐⭐⭐
3. nutrient_models.py    1,014 LOC  ⭐⭐⭐⭐
4. nitrogen_balance.py     692 LOC  ⭐⭐⭐
5. water_uptake_model.py   591 LOC  ⭐⭐⭐
```

## 🎓 Framework Rules (CLAUDE.md)
```
✅ No hardcoded values      → All from CSV
✅ No default values        → Raise errors
✅ No fallback code         → No shortcuts
✅ Single source of truth   → CSV only
✅ Scientific accuracy      → DSSAT-based
✅ Model integration        → All 11 work together
✅ Error on missing params  → Strict validation
```

## 🔄 Circular Dependencies (31 total)
```
Biomass ←→ Photosynthesis ←→ Canopy ←→ Light
    ↕
Roots ←→ Water ←→ Transpiration ←→ Stomata
    ↕
Nitrogen ←→ Photosynthesis ←→ Biomass ←→ N Dilution

Solution: Dependency-ordered execution (one-step lag)
```

## 📈 Performance
```
Timestep:     Hourly (24 steps/day)
Duration:     Until harvest (~40-90 days)
Total steps:  ~1,000-2,000
Runtime:      ~1-5 minutes (estimated)
```

## ✅ Strengths
```
✅ Scientific foundation (DSSAT)
✅ Clean modular architecture
✅ Strict parameter management
✅ Event-driven coordination
✅ Comprehensive models
✅ Real validation data
```

## ⚠️ Gaps
```
⚠️ No unit tests
⚠️ No API documentation
⚠️ Not performance profiled
⚠️ Some parameter duplication
```

## 🎯 Top Recommendations
```
1. Add unit tests for all models
2. Add integration tests for coordination
3. Profile and optimize performance
4. Generate API documentation (Sphinx)
5. Add parameter range validation
```

## 📚 Documentation Generated
```
1. PROJECT_ANALYSIS_REPORT.md  (621 lines) - Comprehensive
2. ARCHITECTURE_DIAGRAM.txt    (182 lines) - Visual
3. EXAMINATION_SUMMARY.md      (260 lines) - Concise
4. QUICK_REFERENCE.md          (This file)  - Quick ref
```

## 🔍 Key Insights

**What makes this unique:**
- Strict "no defaults, all CSV" rule for research integrity
- Distributed architecture mimics biological modularity
- Handles 31 circular dependencies elegantly
- Prioritizes scientific accuracy over software complexity

**Primary strength:** Scientific rigor with clean architecture

**Primary gap:** Testing infrastructure

**Assessment:** Production-ready for research with testing additions

---
**Generated:** $(date +%Y-%m-%d)
**Examination by:** GitHub Copilot CLI
