# Event-Driven Modular Architecture for Hydroponic Simulator

## Complete System Architecture Diagram

```
                    EVENT-DRIVEN HYDROPONIC SIMULATOR ARCHITECTURE
                               (All 17 Models + Support Systems)

    ┌─────────────────┐                                        ┌─────────────────┐
    │   MODEL         │                                        │   SIMULATION    │
    │   MANAGER       │◄──────────────────┐    ┌──────────────►│   CONTROLLER    │
    │                 │                   │    │               │                 │
    │ • Registry      │                   │    │               │ • Time Mgmt     │
    │ • Dependencies  │                   │    │               │ • State Coord   │
    │ • Lifecycle     │                   │    │               │ • Error Recovery│
    └─────────────────┘                   │    │               └─────────────────┘
                                          │    │
                                          ▼    ▼
    ┌─────────────┐    ┌─────────────┐  ┌─────────────────────┐  ┌─────────────┐
    │Environmental│    │Photosynthesis│  │                     │  │  Biomass    │
    │Control      │───►│Model        │──┤   CENTRAL EVENT BUS │◄─│ Allocation  │
    │             │    │             │  │                     │  │             │
    │• HVAC       │    │• Light      │  │ • Event Router      │  │• Partitioning│
    │• CO2        │    │• CO2 Fix    │  │ • Message Queue     │  │• Growth     │
    │• Humidity   │    │• Efficiency │  │ • Priority System   │  │             │
    └─────────────┘    └─────────────┘  │ • Event Logging     │  └─────────────┘
                                        │ • Dependency Mgmt   │
    ┌─────────────┐    ┌─────────────┐  └─────────────────────┘  ┌─────────────┐
    │Weather      │    │Respiration  │                           │Leaf         │
    │Interface    │───►│Model        │──────────────────────────►│Development  │
    │             │    │             │                           │             │
    │• External   │    │• Maintenance│                           │• Emergence  │
    │• APIs       │    │• Growth     │                           │• Expansion  │
    │• Real-time  │    │• Temperature│                           │• Maturation │
    └─────────────┘    └─────────────┘                           └─────────────┘

    ┌─────────────┐    ┌─────────────┐                          ┌─────────────┐
    │Root Zone    │    │Water Uptake │                          │Canopy       │
    │Temperature  │───►│Model        │─────────────────────────►│Architecture │
    │             │    │             │                          │             │
    │• RZT Effects│    │• Transpir.  │                          │• LAI        │
    │• Root Proc. │    │• Water Bal. │                          │• Light Int. │
    │• Thermal    │    │• VPD        │                          │• Structure  │
    └─────────────┘    └─────────────┘                          └─────────────┘

    ┌─────────────┐    ┌─────────────┐                          ┌─────────────┐
    │pH Control   │    │Root System  │                          │Senescence   │
    │System       │───►│Model        │─────────────────────────►│Model        │
    │             │    │             │                          │             │
    │• Buffering  │    │• Architecture│                          │• Aging      │
    │• Nutrient   │    │• Zones      │                          │• Stress     │
    │• Availability│    │• Uptake     │                          │• Remobilizat│
    └─────────────┘    └─────────────┘                          └─────────────┘

    ┌─────────────┐    ┌─────────────┐                          ┌─────────────┐
    │Stress Models│    │Nutrient     │                          │Nitrogen     │
    │(Integrated) │───►│Models       │─────────────────────────►│Balance      │
    │             │    │             │                          │             │
    │• Multi-Stress│   │• Uptake     │                          │• N Uptake   │
    │• Integration │    │• Kinetics   │                          │• Transloc.  │
    │• Interactions│    │• Deficiency │                          │• Allocation │
    └─────────────┘    └─────────────┘                          └─────────────┘

    ┌─────────────┐    ┌─────────────┐                          ┌─────────────┐
    │Genetic      │    │Transpiration│                          │Quality      │
    │Parameters   │───►│Model        │─────────────────────────►│Control      │
    │             │    │             │                          │             │
    │• Variety    │    │• Water Loss │                          │• Harvest    │
    │• Traits     │    │• Cooling    │                          │• Metrics    │
    │• Cultivar   │    │• Efficiency │                          │• Timing     │
    └─────────────┘    └─────────────┘                          └─────────────┘

                                          │    │
                                          ▼    ▼
    ┌─────────────────┐                                        ┌─────────────────┐
    │   DATA          │                                        │  CONFIGURATION  │
    │   MANAGER       │                                        │  MANAGER        │
    │                 │                                        │                 │
    │ • State Storage │                                        │ • CSV Loading   │
    │ • Result Aggreg │                                        │ • Validation    │
    │ • Export/Visual │                                        │ • Hot Reload    │
    └─────────────────┘                                        └─────────────────┘
              ▲                                                         ▲
              │                                                         │
    ┌─────────────────┐                                        ┌─────────────────┐
    │  EXTERNAL       │                                        │  CSV PARAMETERS │
    │  SYSTEMS        │                                        │  (900+ params)  │
    │                 │                                        │                 │
    │ • Weather APIs  │                                        │ • All Models    │
    │ • Sensors       │                                        │ • 18 Categories │
    │ • Monitoring    │                                        │ • No Hardcoded │
    └─────────────────┘                                        └─────────────────┘
```

## Event Flow Sequence Diagram

```
Daily Simulation Event Flow (Event-Driven Architecture)

Controller  Environment  Weather  Photosyn  Growth  Nutrients  Water  DataMgr
    |           |          |         |        |        |        |       |
    |─DailyStep─|          |         |        |        |        |       |
    |           |─UpdateWx─|         |        |        |        |       |
    |           |          |─WxReady─|        |        |        |       |
    |           |─EnvUpdt──|─────────|        |        |        |       |
    |           |          |         |─PhotoC─|        |        |       |
    |           |          |         |        |─GrowthF|        |       |
    |           |          |         |        |        |─NutDmd─|       |
    |           |          |         |        |        |        |─WtrUp─|
    |           |          |         |        |        |        |       |─LogRes
    |←─DailyCycleComplete───|─────────|────────|────────|────────|───────|

Timeline: ~50-200ms total (1-5ms per event)
```

## Model Dependency Graph

```
Model Dependencies & Event Relationships

Layer 0: Base Systems     Layer 1: Env-Dependent    Layer 2: Primary       Layer 3: Integration    Layer 4: Growth
┌─────────────┐          ┌─────────────┐           ┌─────────────┐        ┌─────────────┐         ┌─────────────┐
│Environmental│─────────►│Root Zone    │──────────►│Photosynthes│───────►│Stress Models│────────►│Biomass      │
│Control      │          │Temperature  │           │Model        │        │(Integrated) │         │Allocation   │
└─────────────┘          └─────────────┘           └─────────────┘        └─────────────┘         └─────────────┘
                                                            │                      │                      │
┌─────────────┐          ┌─────────────┐           ┌─────────────┐        ┌─────────────┐         ┌─────────────┐
│Weather      │─────────►│pH Control   │──────────►│Respiration  │───────►│Nutrient     │────────►│Leaf         │
│Interface    │          │System       │           │Model        │        │Models       │         │Development  │
└─────────────┘          └─────────────┘           └─────────────┘        └─────────────┘         └─────────────┘
                                                            │                      │                      │
┌─────────────┐          ┌─────────────┐           ┌─────────────┐        ┌─────────────┐         ┌─────────────┐
│Genetic      │─────────►│Phenology    │──────────►│Water Uptake │───────►│Transpiration│────────►│Canopy       │
│Parameters   │          │Model        │           │Model        │        │Model        │         │Architecture │
└─────────────┘          └─────────────┘           └─────────────┘        └─────────────┘         └─────────────┘
                                                            │                                              │
                                                   ┌─────────────┐                               ┌─────────────┐
                                                   │Root System  │──────────────────────────────►│Senescence   │
                                                   │Model        │                               │Model        │
                                                   └─────────────┘                               └─────────────┘
                                                                                                          │
                                                                                                 ┌─────────────┐
                                                                                                 │Nitrogen     │
                                                                                                 │Balance      │
                                                                                                 └─────────────┘

Event-Driven Execution: Models trigger when events received, not fixed order
Automatic dependency resolution through event bus
```

## Key Event Types

```
EVENT CATEGORIES & EXAMPLES:

🔴 CONTROL EVENTS:
• DailySimulationStep      • HourlyUpdate           • ModelStateChanged
• SimulationStart          • SimulationStop         • ErrorRecovery

🟢 DATA EVENTS:
• WeatherDataReady         • SensorDataUpdated      • ParameterChanged
• ConfigurationReloaded    • ValidationComplete     • StateSnapshot

🟠 TRIGGER EVENTS:
• EnvironmentUpdated       • ThresholdExceeded      • PhaseTransition
• StressDetected          • AlertGenerated         • CalibrationNeeded

🔵 PROCESS EVENTS:
• PhotosynthesisCalculated • GrowthFactorChanged    • NutrientUptakeComplete
• WaterBalance Updated     • BiomassAllocated       • LeafEmergence

🟣 RESULT EVENTS:
• DailyResultsReady        • ModelOutputGenerated   • ReportCreated
• ExportComplete          • VisualizationUpdated   • QualityAssessed
```

## Architecture Benefits

### ✅ **Loose Coupling**
- Models communicate only through events
- No direct dependencies between models
- Easy to modify individual models

### ✅ **Scalability**
- Add/remove models without code changes
- Dynamic model registration
- Hot-swappable components

### ✅ **Real-Time Response**
- Models react immediately to relevant events
- No polling or batch processing
- Natural feedback loops

### ✅ **Complete Observability**
- All model interactions logged
- Event replay for debugging
- Performance monitoring

### ✅ **Parallel Processing**
- Independent models can run concurrently
- Event-driven scheduling
- Optimal resource utilization

### ✅ **Flexibility**
- Easy to change simulation flow
- Configure event routing
- Support multiple simulation strategies

---

**Total Models: 17**
**Event Types: 20+**
**Processing Time: ~50-200ms per daily cycle**
**Memory Footprint: Minimal (event-driven)**
**Extensibility: Unlimited (plug-and-play models)**