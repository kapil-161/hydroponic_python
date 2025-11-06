# Model Dependency Graph: Visual Representation

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WEATHER DATA (Hourly)                            │
│  Temperature, Humidity, Light, CO2, VPD                                   │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  1. PHENOLOGY          │
        │  Growth stage, DVI     │
        └───────────┬────────────┘
                    │
        ┌───────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐      ┌──────────────────┐
│  2. ROOT      │      │  5. LEAF DEV     │
│  Root biomass │      │  Leaf area, N     │
│  Root depth   │      │  Leaf number     │
└───────┬───────┘      └────────┬─────────┘
        │                        │
        │                        │
        ▼                        │
┌───────────────┐                │
│  3. WATER     │                │
│  Transpiration│                │
│  Water uptake │                │
└───────┬───────┘                │
        │                        │
        │                        │
        ▼                        │
┌───────────────┐                │
│  4. NUTRIENT  │                │
│  N availability│                │
│  Uptake rates │                │
└───────┬───────┘                │
        │                        │
        └──────────┬─────────────┘
                   │
                   ▼
        ┌──────────────────┐
        │  6. STRESS       │
        │  Temp, water,    │
        │  nutrient stress │
        └──────────┬───────┘
                    │
                    ▼
        ┌──────────────────┐
        │  7. CANOPY       │
        │  LAI, height     │
        │  Sunlit/shaded   │
        └──────────┬───────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐    ┌──────────────────┐
│  8. PHOTO     │    │  9. RESPIRATION  │
│  Net/gross Pn │    │  Respiration rate│
│  Carbon gain  │    │  Maintenance     │
└───────┬───────┘    └────────┬─────────┘
        │                      │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────┐
        │ 10. BIOMASS      │
        │  Organ biomass    │
        │  Allocation       │
        │  Sink strength    │
        └──────────┬───────┘
                    │
                    ▼
        ┌──────────────────┐
        │ 11. NITROGEN     │
        │  N uptake        │
        │  N allocation    │
        │  N remobilization│
        └──────────────────┘
```

## Circular Dependencies (Feedback Loops)

### Loop 1: Biomass ↔ Photosynthesis ↔ Canopy
```
Biomass → Canopy Structure → LAI → Photosynthesis → Carbon → Biomass
   ▲                                                              │
   └────────────────────────────────────────────────────────────┘
```
**Handled by:** Executing biomass before canopy, using one-step lag

### Loop 2: Roots ↔ Water ↔ Transpiration
```
Roots → Water Uptake → Transpiration → Root Growth → Roots
   ▲                                                    │
   └────────────────────────────────────────────────────┘
```
**Handled by:** Executing roots before water uptake

### Loop 3: Nitrogen ↔ Photosynthesis ↔ Growth
```
N Uptake → N Allocation → Photosynthesis → Growth → N Demand → N Uptake
   ▲                                                              │
   └────────────────────────────────────────────────────────────┘
```
**Handled by:** Executing photosynthesis before nitrogen balance

### Loop 4: Stress ↔ All Processes
```
Stress → Reduced Performance → Reduced Growth → Stress
   ▲                                        │
   └────────────────────────────────────────┘
```
**Handled by:** Executing stress after resource models

## Key Data Exchanges

### Photosynthesis Receives:
- **From Canopy**: LAI, leaf area, sunlit/shaded fractions
- **From Stress**: Temperature, light, water stress factors
- **From Nitrogen**: Nitrogen area-based (g N/m²)
- **From Biomass**: Sink strength (source-sink feedback)
- **From Respiration**: Total respiration (for gross Pn)

### Biomass Allocation Receives:
- **From Photosynthesis**: Net assimilation rate, carbon gain
- **From Respiration**: Respiration costs
- **From Phenology**: Growth stage (controls allocation)
- **From Stress**: Stress factors (affect efficiency)
- **From Roots**: Root biomass (for root allocation)

### Nitrogen Balance Receives:
- **From Nutrients**: N availability, uptake rates
- **From Roots**: Root mass, surface area
- **From Biomass**: Organ biomass (for N concentration)
- **From Photosynthesis**: Photosynthesis rate (N-use efficiency)
- **From Canopy**: Leaf area (for area-based N)

### Stress Models Receives:
- **From Water**: Water uptake, transpiration
- **From Nutrients**: Nutrient availability
- **From Phenology**: Growth stage
- **From Weather**: Temperature, light, humidity

## Execution Timeline (One Hour)

```
Hour N:
├─ 1. Phenology: Calculate growth stage
├─ 2. Root System: Calculate root growth
├─ 3. Water Uptake: Calculate transpiration (uses root data from step 2)
├─ 4. Nutrient Models: Calculate nutrient uptake (uses water data from step 3)
├─ 5. Leaf Development: Calculate leaf growth
├─ 6. Stress Models: Calculate stress factors (uses water + nutrient data)
├─ 7. Canopy Architecture: Calculate LAI (uses biomass from Hour N-1)
├─ 8. Photosynthesis: Calculate carbon gain (uses canopy from step 7)
├─ 9. Respiration: Calculate respiration costs
├─ 10. Biomass Allocation: Calculate biomass gain (uses photo from step 8)
└─ 11. Nitrogen Balance: Calculate N dynamics (uses biomass from step 10)

Hour N+1:
└─ Uses updated data from Hour N (one-step lag for circular dependencies)
```

## Data Cache Flow

```
Orchestrator.shared_data_cache
    │
    ├─→ Simulator 1.dependency_cache (injected before execution)
    │   └─→ Simulator 1 executes
    │       └─→ Simulator 1 publishes state
    │           └─→ Orchestrator.shared_data_cache updated
    │
    ├─→ Simulator 2.dependency_cache (injected before execution)
    │   └─→ Simulator 2 executes
    │       └─→ Simulator 2 publishes state
    │           └─→ Orchestrator.shared_data_cache updated
    │
    └─→ ... (continues for all 11 simulators)
```

## Critical Paths

### Path 1: Carbon Flow
```
Weather → Canopy → Photosynthesis → Respiration → Biomass → Canopy
```

### Path 2: Nitrogen Flow
```
Weather → Nutrients → N Uptake → N Allocation → Photosynthesis → Growth → N Demand
```

### Path 3: Water Flow
```
Weather → Roots → Water Uptake → Transpiration → Stress → Growth
```

### Path 4: Stress Response
```
Weather → Stress → All Processes → Reduced Performance → Stress
```

