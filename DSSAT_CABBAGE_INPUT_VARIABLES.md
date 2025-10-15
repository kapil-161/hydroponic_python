# DSSAT Cabbage Simulation - Complete Input Variables Reference

This document provides a comprehensive list of all input variables for the DSSAT cabbage simulation model (CRGRO048).

## Table of Contents
1. [Model Constants](#model-constants)
2. [Species Parameters (CBGRO048.SPE)](#species-parameters)
3. [Cultivar Parameters (CBGRO048.CUL)](#cultivar-parameters)
4. [Ecotype Parameters (CBGRO048.ECO)](#ecotype-parameters)
5. [Experiment File Variables (CBX)](#experiment-file-variables)
6. [Weather Data Variables (WTH)](#weather-data-variables)
7. [Soil Profile Variables (SOL)](#soil-profile-variables)
8. [Simulation Control Variables](#simulation-control-variables)

---

## Model Constants

### Global Constants (ModuleDefs.for)
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `NL` | 20 | - | Maximum number of soil layers |
| `TS` | 24 | - | Number of hourly time steps per day |
| `NAPPL` | 9000 | - | Maximum number of applications or operations |
| `NCOHORTS` | 300 | - | Maximum number of cohorts |
| `NELEM` | 3 | - | Number of elements modeled (N, P, K) |
| `NumOfDays` | 1000 | days | Maximum days in sugarcane run |
| `NumOfStalks` | 42 | - | Maximum stalks per sugarcane stubble |
| `EvaluateNum` | 40 | - | Number of evaluation variables |
| `MaxFiles` | 500 | - | Maximum number of output files |
| `MaxPest` | 500 | - | Maximum number of pest operations |

### Mathematical Constants
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `PI` | 3.14159265 | radians | Pi constant |
| `RAD` | π/180.0 | radians/degree | Conversion factor degrees to radians |

### Dynamic Variable Values
| Variable | Value | Description |
|----------|-------|-------------|
| `RUNINIT` | 1 | Run initialization |
| `INIT` | 2 | General initialization |
| `SEASINIT` | 2 | Seasonal initialization |
| `RATE` | 3 | Rate calculation |
| `EMERG` | 3 | Emergence phase |
| `INTEGR` | 4 | Integration |
| `OUTPUT` | 5 | Output |
| `SEASEND` | 6 | Season end |
| `ENDRUN` | 7 | Run end |

### Nutrient Array Positions
| Variable | Value | Description |
|----------|-------|-------------|
| `N` | 1 | Nitrogen position |
| `P` | 2 | Phosphorus position |
| `Kel` | 3 | Potassium position |

### Photosynthesis Constants
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `RGAS` | 8.314 | J/mol/K | Universal gas constant |
| `O2` | 210000 | µL/L | Atmospheric O2 concentration |
| `CICA` | 0.7 | - | Ci/Ca ratio for CO2=350 µL/L |
| `GAMST` | 0.5*O2/TAU | µL/L | CO2 compensation point |
| `TAU` | exp(-3.949 + 28990.0/RT) | - | CO2/O2 specificity factor |
| `7.179` | 7.179 | - | CO2 scaling factor at 30°C, 350 ppm |
| `6.225` | 6.225 | - | CO2 quantum efficiency scaling factor |
| `44.0` | 44.0 | g/mol | CO2 molecular weight |
| `1000.0` | 1000.0 | mg/g | Conversion factor mg to g |
| `0.16` | 0.16 | g N/g protein | Nitrogen content of protein |
| `273.0` | 273.0 | K | Absolute zero in Kelvin |
| `30.0` | 30.0 | °C | Reference temperature |
| `350.0` | 350.0 | µL/L | Reference CO2 concentration |

### Hydroponic System Constants
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `MXLAYR` | 10 | - | Maximum hydroponic layers |
| `HydroDepth` | 30.0 | cm | Standard hydroponic depth |
| `HydroBD` | 0.2 | g/cm³ | Hydroponic bulk density |
| `HydroVolume` | 1000.0 | L | Initial tank volume |
| `HydroFlowRate` | 5.0 | L/min | Initial flow rate |
| `MinTemp` | 15.0 | °C | Minimum hydroponic temperature |
| `MaxTemp` | 30.0 | °C | Maximum hydroponic temperature |
| `PO4Threshold` | 30.0 | - | PO4 concentration threshold |

### Soil Constants
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `TOL` | 0.5 | cm | Tolerance for water table level |
| `Kd` | 0.5 | fraction/day | Drawdown coefficient |
| `MAXIABS` | 0.6 | - | Maximum initial abstraction ratio |

### Error Handling Constants
| Variable | Value | Description |
|----------|-------|-------------|
| `ERRKEY` | Various | Error identification keys |
| `LUNIO` | 21 | Logical unit number for I/O |
| `BLANK` | ' ' | Blank character |

### Plant Stress Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `NSTRES` | 0.0-1.0 | - | Nitrogen stress factor (1=no stress, 0=max stress) |
| `PSTRES1` | 0.0-1.0 | - | Phosphorus stress for photosynthesis (1=no stress, 0=max stress) |
| `PSTRES2` | 0.0-1.0 | - | Phosphorus stress for partitioning (1=no stress, 0=max stress) |
| `SWFAC` | 0.0-1.0 | - | Soil water stress factor on photosynthesis (1=no stress, 0=max stress) |
| `TURFAC` | 0.0-1.0 | - | Turgor stress factor (1=no stress, 0=max stress) |
| `AGEFAC` | 0.0-1.0 | - | Leaf age stress factor (1=no stress, 0=max stress) |
| `CNSTRES` | 0.0-1.0 | - | Cumulative N stress (8-day moving average) |
| `CPSTRES` | 0.0-1.0 | - | Cumulative P stress (8-day moving average) |
| `PSTRESS_RATIO` | 0.0-1.0 | - | Ratio of P in tissue to optimum P (stress indicator) |
| `SATFAC` | 0.0-1.0 | - | Root water excess stress factor (0=no stress, 1=saturated stress) |
| `KSTRES` | 0.0-1.0 | - | Potassium stress factor |
| `LFAC` | 0.0-1.0 | - | Light stress factor |
| `TFAC` | 0.0-1.0 | - | Temperature stress factor |
| `WFAC` | 0.0-1.0 | - | Water stress factor |

### Stress Response Parameters
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `NSTFAC` | 1.0 | - | N stress threshold factor |
| `SRATPHOTO` | 0.8 | - | P stress ratio threshold for photosynthesis |
| `SRATPART` | 0.7 | - | P stress ratio threshold for partitioning |
| `XSWFAC(4)` | Various | - | X values for water stress function |
| `YSWFAC(4)` | Various | - | Y values for water stress function |
| `XRTFAC(4)` | Various | - | X values for root stress function |
| `YRTFAC(4)` | Various | - | Y values for root stress function |

### Environmental Stress Factors
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `WSENP(12)` | Various | - | Water stress sensitivity by growth stage |
| `NSENP(12)` | Various | - | Nitrogen stress sensitivity by growth stage |
| `PSENP(12)` | Various | - | Phosphorus stress sensitivity by growth stage |
| `COLDSTR` | 0.0-1.0 | - | Cold stress factor |
| `CUMSTR` | 0.0-1.0 | - | Cumulative stress factor |

### Mulch Stress Factors
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `EXTFAC` | 0.80 | - | Light extinction coefficient for mulch |
| `WATFAC` | 3.8 | kg H2O/kg DM | Saturation water content of residue |
| `MUL_EXTFAC` | 0.80 | - | Light extinction coefficient for mulch layer |
| `MUL_WATFAC` | 3.8 | mm water/ha/kg | Saturation water content for mulch |

### Nitrogen Dynamics Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `NSTRES` | 0.0-1.0 | - | Nitrogen stress factor (1=no stress, 0=max stress) |
| `NMOBR` | 0.0-1.0 | fraction/d | Nitrogen mobilization rate |
| `NMOBMX` | 0.074 | fraction/d | Maximum N mobilization rate |
| `NVSMOB` | 0.75 | - | N mobilization rate during vegetative stage |
| `NRCVR` | 0.20 | - | N recovery rate |
| `NMINEP` | 0.0+ | g N/m²/d | Potential N mobilization |
| `NMINEA` | 0.0+ | g N/m²/d | Actual N mobilized from tissue |
| `NMINER` | 0.0+ | g N/m²/d | N mobilization rate |
| `NDMNEW` | 0.0+ | g N/m²/d | New N demand |
| `TRNU` | 0.0+ | g N/m²/d | Total root N uptake |
| `TRNO3U` | 0.0+ | g N/m²/d | Total root NO3 uptake |
| `TRNH4U` | 0.0+ | g N/m²/d | Total root NH4 uptake |

### Plant Nitrogen Pools
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `WTNLF` | 0.0+ | g N/m² | Total N in leaves |
| `WTNST` | 0.0+ | g N/m² | Total N in stems |
| `WTNRT` | 0.0+ | g N/m² | Total N in roots |
| `WTNSH` | 0.0+ | g N/m² | Total N in shells |
| `WTNSD` | 0.0+ | g N/m² | Total N in seeds |
| `WTNLA` | 0.0+ | g N/m² | Total N in leaf area |
| `WTNLO` | 0.0+ | g N/m² | Total N in leaf output |
| `WTNNO` | 0.0+ | g N/m² | Total N in nodule output |
| `WTNRA` | 0.0+ | g N/m² | Total N in root area |
| `WTNRO` | 0.0+ | g N/m² | Total N in root output |
| `WTNCAN` | 0.0+ | g N/m² | Total N in canopy |
| `WTNUP` | 0.0+ | g N/m² | Total N uptake |
| `WTNMOB` | 0.0+ | g N/m² | Cumulative mobilized N |

### Nitrogen Mobilization Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `WNRLF` | 0.0+ | g N/m² | N available for mobilization from leaves |
| `WNRST` | 0.0+ | g N/m² | N available for mobilization from stems |
| `WNRRT` | 0.0+ | g N/m² | N available for mobilization from roots |
| `WNRSH` | 0.0+ | g N/m² | N available for mobilization from shells |
| `WNRSD` | 0.0+ | g N/m² | N available for mobilization from seeds |
| `NRUSLF` | 0.0+ | g N/m²/d | N actually mobilized from leaves |
| `NRUSST` | 0.0+ | g N/m²/d | N actually mobilized from stems |
| `NRUSRT` | 0.0+ | g N/m²/d | N actually mobilized from roots |
| `NRUSSH` | 0.0+ | g N/m²/d | N actually mobilized from shells |
| `NRUSSD` | 0.0+ | g N/m²/d | N actually mobilized from seeds |

### Nitrogen Growth Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `NGRLF` | 0.0+ | g N/m²/d | N accumulation rate in leaves |
| `NGRST` | 0.0+ | g N/m²/d | N accumulation rate in stems |
| `NGRRT` | 0.0+ | g N/m²/d | N accumulation rate in roots |
| `NGRSH` | 0.0+ | g N/m²/d | N accumulation rate in shells |
| `NGRSD` | 0.0+ | g N/m²/d | N accumulation rate in seeds |
| `NADLF` | 0.0+ | g N/m²/d | N added to leaves |
| `NADST` | 0.0+ | g N/m²/d | N added to stems |
| `NADRT` | 0.0+ | g N/m²/d | N added to roots |

### Soil Nitrogen Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `SNO3` | 0.0+ | µg N/g soil | Soil nitrate concentration |
| `SNH4` | 0.0+ | µg N/g soil | Soil ammonium concentration |
| `TNO3` | 0.0+ | kg N/ha | Total soil nitrate |
| `TNH4` | 0.0+ | kg N/ha | Total soil ammonium |
| `TUREA` | 0.0+ | kg N/ha | Total soil urea |
| `UNO3` | 0.0+ | g N/m²/d | NO3 uptake by plant |
| `UNH4` | 0.0+ | g N/m²/d | NH4 uptake by plant |
| `RNO3U` | 0.0+ | g N/m²/d | Root NO3 uptake |
| `RNH4U` | 0.0+ | g N/m²/d | Root NH4 uptake |

### Nitrogen Balance Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `ALGFIX` | 0.0+ | kg N/ha | Algal N fixation |
| `CIMMOBN` | 0.0+ | kg N/ha | Cumulative N immobilization |
| `CMINERN` | 0.0+ | kg N/ha | Cumulative N mineralization |
| `CUMFNRO` | 0.0+ | kg N/ha | Cumulative fertilizer N runoff |
| `CNUPTAKE` | 0.0+ | kg N/ha | Cumulative N uptake |
| `CLeach` | 0.0+ | kg N/ha | Cumulative N leaching |
| `CNTILEDR` | 0.0+ | kg N/ha | Cumulative N tile drainage |
| `TOTAML` | 0.0+ | kg N/ha | Total ammonia loss |
| `TOTFLOODN` | 0.0+ | kg N/ha | Total flood N |
| `AMTFER` | 0.0+ | kg N/ha | Amount of fertilizer applied |

### Nitrogen Concentration Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `PCNL` | 0.0+ | % | Percentage N in leaves |
| `PCNST` | 0.0+ | % | Percentage N in stems |
| `PCNRT` | 0.0+ | % | Percentage N in roots |
| `PCNSH` | 0.0+ | % | Percentage N in shells |
| `PCNSD` | 0.0+ | % | Percentage N in seeds |
| `PCNMIN` | 0.0+ | % | Minimum percentage N in leaves |
| `PROLFF` | 0.0+ | g protein/g tissue | Protein content in leaves |
| `PROSTF` | 0.0+ | g protein/g tissue | Protein content in stems |
| `PRORTF` | 0.0+ | g protein/g tissue | Protein content in roots |
| `PROSHF` | 0.0+ | g protein/g tissue | Protein content in shells |

### Nitrogen Process Rates
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `NITRIFICATION` | 0.0+ | kg N/ha/d | Nitrification rate |
| `DENITRIFICATION` | 0.0+ | kg N/ha/d | Denitrification rate |
| `LEACHING` | 0.0+ | kg N/ha/d | N leaching rate |
| `IMMOBILIZATION` | 0.0+ | kg N/ha/d | N immobilization rate |
| `MINERALIZATION` | 0.0+ | kg N/ha/d | N mineralization rate |
| `VOLATILIZATION` | 0.0+ | kg N/ha/d | N volatilization rate |

### Senescence Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `SENESCE` (ResidueType) | - | - | Construct holding senesced/harvest residue pools |
| `SENESCE.ResWt(0:NL)` | 0.0+ | kg/ha/d | Senesced dry matter to surface and soil layers |
| `SENESCE.ResLig(0:NL)` | 0.0+ | kg/ha/d | Senesced lignin mass |
| `SENESCE.ResE(0:NL,NELEM)` | 0.0+ | kg/ha/d | Senesced elements (N,P,...) |
| `WSDOT` | 0.0+ | g/m²/d | Daily structural dry matter senesced |
| `NLDOT` | 0.0+ | g N/m²/d | Leaf N senesced |
| `NSDOT` | 0.0+ | g N/m²/d | Stem N senesced |
| `SRDOT` | 0.0+ | g/m²/d | Daily senesced root dry matter |
| `NLOFF` | 0.0+ | g N/m²/d | N offloaded from leaves via senescence |
| `NSOFF` | 0.0+ | g N/m²/d | N offloaded from stems via senescence |
| `RLSENTOT` | 0.0+ | cm/cm² | Profile root length senescence (aggregate) |
| `SATFAC` | 0.0-1.0 | - | Excess water stress factor affecting root senescence |
| `SEN_AM` | 0.0+ | cm²/g | Surface coverage per unit senesced mass |
| `SEN_EXTFAC` | 0.0+ | - | Light extinction of senesced surface residue |
| `SEN_WATFAC` | 0.0+ | kg/kg | Saturation water content of senesced residue |

Notes:
- Soil organic matter routines (e.g., SENESADD_C.for) aggregate senesced flows into surface/soil residue pools and update mulch optical/water properties.
- Root senescence integrates water stress via `SATFAC`; leaf/stem senescence affect canopy and nutrient cycling.

### Biomass Allocation (Partitioning)
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `CARBO` | 0.0+ | g/m²/d | Available assimilate for growth |
| `PG` / `PGAVL` | 0.0+ | g/m²/d | Gross photosynthesis / available growth substrate |
| `FRLF` | 0.0-1.0 | fraction | Daily fraction of growth to leaves |
| `FRSTM` | 0.0-1.0 | fraction | Daily fraction of growth to stems |
| `FRRT` / `FRTEM` | 0.0-1.0 | fraction | Daily fraction of growth to roots |
| `XFRT` | 0.0-1.0 | fraction | Max fraction to reproductive sinks (seed+shell) |
| `PCARLF` / `PCARST` / `PCARRT` | 0.0-1.0 | g C/g | Carbon content of leaf/stem/root |
| `PCARSH` / `PCARSD` | 0.0-1.0 | g C/g | Carbon content of shell/seed |
| `PCARGR` | 0.0-1.0 | g C/g | Carbon content of generic growth tissue |
| `PStres2` | 0.0-1.0 | - | P stress factor affecting partitioning |
| `NSTRES` / `TURFAC` | 0.0-1.0 | - | N/turgor stress factors modifying allocation |
| `KEP` | 0.0-1.0 | - | Energy partition factor in growth energy balance |
| `TGRO` / `GROWTH` | 0.0+ | g/m²/d | Realized daily growth after constraints |

Notes:
- Partitioning uses stress scalars (`NSTRES`, `PStres2`, `TURFAC`) and stage to compute `FR*` fractions; `XFRT` caps reproductive allocation.
- `PCAR*` parameters convert between tissue mass and carbon pools for C balance.

### Canopy Architecture Variables
| Variable | Range | Units | Description |
|----------|-------|-------|-------------|
| `LAI` / `XLAI` | 0.0+ | m²/m² | Leaf area index (instantaneous/daily) |
| `XHLAI` | 0.0+ | m²/m² | Daily max or reported LAI (output contexts) |
| `LAIMX` | 0.0+ | m²/m² | Maximum attainable LAI |
| `CANHT` | 0.0+ | m | Canopy height |
| `CANWH` | 0.0+ | m | Canopy width (if computed) |
| `ROWSPC` | 0.0+ | cm | Row spacing |
| `PLTPOP` | 0.0+ | plants/m² | Plant population density |
| `KCAN` | 0.0-1.0 | - | Canopy light extinction coefficient (beam) |
| `KDIF` | 0.0-1.0 | - | Diffuse light extinction coefficient |
| `SCV` | 0.0-1.0 | - | Canopy scattering/reflectance coefficient |
| `LFANGB` | 0.0+ | - | Leaf angle beta parameter (controls sunlit/shaded fraction) |
| `SLWREF` | 0.0+ | g/cm² | Reference specific leaf weight (affects light response) |
| `SLWSLO` | any | - | Slope parameter for SLW vs. N/age |
| `SLA` | 0.0+ | cm²/g | Specific leaf area (state) |
| `SLAAD` | 0.0+ | cm²/g/d | Daily change in SLA |
| `KTRANS` | 0.0-1.0 | - | Canopy transpiration coefficient (used in energy/water calc) |
| `KSEVAP` | 0.0-1.0 | - | Soil/canopy evaporation coefficient (coupled with cover) |
| `LIsun` | 0.0-1.0 | - | Fraction radiation to sunlit leaves (if computed) |
| `LIshd` | 0.0-1.0 | - | Fraction radiation to shaded leaves (if computed) |

Notes:
- `KCAN`, `KDIF`, `SCV`, and `LFANGB` are read from species files and used by canopy photosynthesis routines to split sunlit/shaded leaves and attenuate light.
- `ROWSPC` and `PLTPOP` influence canopy cover, mutual shading, and interception.
- `SLA`, `SLWREF`, and `SLWSLO` control leaf optical/physiological capacity, indirectly impacting architecture and light use.

### Leaf Development Parameters
| Variable | Typical range | Units | Description |
|----------|----------------|-------|-------------|
| `PHINT` | species/cultivar | °C·d/leaf or d/leaf | Phyllochron: thermal time between leaf appearances |
| `LLIFA` | species/cultivar | d | Leaf life span (functional duration) |
| `LA1S` | species/cultivar | cm²/plant | Initial leaf area scalar at emergence |
| `LAFV` | species/cultivar | - | Leaf area expansion factor (vegetative) |
| `LAFR` | species/cultivar | - | Leaf area expansion factor (reproductive) |
| `LAXS` | species/cultivar | - | Leaf expansion sensitivity scalar |
| `LAXND` | species/cultivar | - | Leaf expansion nitrogen sensitivity (day) |
| `LAXN2` | species/cultivar | - | Secondary N sensitivity for leaf expansion |
| `SLASS` | species/cultivar | cm²/g | Specific leaf area at standard status |
| `LPEFR` | species/cultivar | - | Leaf expansion fraction with stress |
| `STFR` | species/cultivar | - | Stem:leaf growth fraction (dev-linked) |
| `PPS1` | species/cultivar | h | Photoperiod sensitivity for leaf development (1) |
| `PPS2` | species/cultivar | h | Photoperiod sensitivity for leaf development (2) |
| `SIZLF` | 40–60 | cm² | Maximum size of a full leaf |
| `SLAVR` | 210–240 | cm²/g | Specific leaf area under standard conditions |
| `SLA` | dynamic | cm²/g | Specific leaf area (state variable) |
| `SLAAD` | dynamic | cm²/g/d | Daily change in specific leaf area |
| `NDLEAF` | dynamic | day of year | Day when leaf expansion ceases |

Notes:
- `PHINT`, `LLIFA`, and `SIZLF` determine the rate and potential of leaf appearance and expansion; stress scalars (`NSTRES`, `PStres2`, `SWFAC`) modulate realized expansion.
- `SLA`/`SLAVR`/`SLASS` connect biomass to leaf area; `SLAAD` evolves with development and stress.
- `PPS1`/`PPS2` introduce photoperiod control on leaf development where used.

### Root Development Parameters
| Variable | Typical range | Units | Description |
|----------|----------------|-------|-------------|
| `RTDEPI` | 15.0 | cm | Initial root depth at emergence |
| `RTDEP` | dynamic | cm | Current root depth |
| `RLV` | dynamic | cm/cm³ | Root length density per soil layer |
| `RTWT` | dynamic | g/m² | Root dry weight |
| `WTRT` | dynamic | g/m² | Root dry weight (alternative naming) |
| `WTRTD` | dynamic | g/m²/d | Daily change in root dry weight |
| `RLDSM` | 0.1 | - | Root length density parameter (scaling) |
| `RFAC1` | 9990. | - | Root growth factor 1 (scaling parameter) |
| `RTSDF` | 0.015 | - | Root distribution factor (shape parameter) |
| `RTSEN` | 0.020 | - | Root senescence factor |
| `RTEXF` | 0.10 | - | Root extension factor |
| `RWUEP1` | 1.50 | - | Root water uptake efficiency parameter 1 |
| `RWUMX` | 0.04 | cm/d | Maximum root water uptake rate |
| `RTNO3` | 0.010 | - | Root NO3 uptake parameter |
| `RTNH4` | 0.010 | - | Root NH4 uptake parameter |
| `SRGF` | dynamic | - | Soil layer root growth factor |
| `RLSENTOT` | dynamic | cm/cm² | Profile root length senescence (aggregate) |
| `SRDOT` | dynamic | g/m²/d | Daily senesced root dry matter |
| `FRRT` / `FRTEM` | 0.0-1.0 | fraction | Daily fraction of growth to roots |
| `PCARRT` | 0.694 | g C/g | Carbon content of root tissue |

Notes:
- `RTDEPI` sets initial root depth; `RTDEP` tracks current depth; `RLV` distributes root length across soil layers.
- `RWUEP1`, `RWUMX`, `RTNO3`, `RTNH4` control root uptake efficiency for water and nutrients.
- `RTSEN`, `RLSENTOT`, `SRDOT` handle root senescence; `SRGF` modulates root growth by soil layer.
- `FRRT`/`FRTEM` controls root biomass allocation; stress factors (`SWFAC`, `NSTRES`) affect root growth.

---

## Species Parameters (CBGRO048.SPE)

### Photosynthesis Parameters
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `PARMAX` | 40.00 | µmol/m²/s | PAR value at 63% of maximum photosynthesis |
| `PHTMAX` | 68.00 | g CH2O/m²/d | Maximum canopy photosynthesis |
| `KCAN` | 0.50 | - | Canopy extinction coefficient |
| `CCMP` | 80.0 | - | CO2 effect parameter |
| `CCMAX` | 2.09 | - | Maximum CO2 effect |
| `CCEFF` | 0.0105 | - | CO2 efficiency factor |
| `QEREF` | 0.0541 | µmol CO2/µmol photons | Quantum efficiency reference |
| `LFANGB` | 2.0 | - | Leaf angle parameter |
| `SLWREF` | 0.0035 | g/cm² | Reference specific leaf weight |
| `SLWSLO` | 0.0001 | - | SLW slope parameter |
| `NSLOPE` | 0.5000 | - | Nitrogen slope parameter |
| `LNREF` | 3.50 | % | Reference leaf nitrogen concentration |
| `PGREF` | 1.030 | - | Reference photosynthesis value |

### Temperature Response Parameters
| Variable | Values | Description |
|----------|--------|-------------|
| `FNPGN(4)` | 1.20, 3.50, 20.0, 20.0 | Leaf N effect on photosynthesis |
| `FNPGT(4)` | 0.00, 15.0, 25.0, 45.0 | Temperature effect on canopy photosynthesis |
| `XLMAXT(6)` | -10.0, 0.0, 35.0, 39.0, 43.0, 55.0 | Temperature values for leaf max photosynthesis |
| `YLMAXT(6)` | 0.0, 0.0, 1.0, 0.8, 0.0, 0.0 | Temperature effects on leaf max photosynthesis |
| `FNPGL(4)` | -6.00, 10.00, 50.0, 60.0 | Minimum temperature effect on leaf photosynthesis |

### Respiration Parameters
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `RES30C` | 3.5E-04 | - | Respiration coefficient at 30°C |
| `R30C2` | 0.0040 | - | Respiration coefficient for photosynthesis |
| `RNO3C` | 2.556 | - | NO3 respiration coefficient |
| `RNH4C` | 2.556 | - | NH4 respiration coefficient |
| `RPRO` | 0.360 | - | Protein respiration coefficient |
| `RFIXN` | 2.830 | - | N fixation respiration coefficient |
| `RCH20` | 1.242 | - | CH2O respiration coefficient |
| `RLIP` | 3.106 | - | Lipid respiration coefficient |
| `RLIG` | 2.174 | - | Lignin respiration coefficient |
| `ROA` | 0.929 | - | Organic acid respiration coefficient |
| `RMIN` | 0.05 | - | Mineral respiration coefficient |
| `PCH2O` | 1.13 | - | CH2O parameter |

### Plant Composition Values
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `PROLFI` | 0.284 | g protein/g tissue | Protein in leaf, initial |
| `PROLFG` | 0.240 | g protein/g tissue | Protein in leaf, growth |
| `PROLFF` | 0.094 | g protein/g tissue | Protein in leaf, final |
| `PROSTI` | 0.178 | g protein/g tissue | Protein in stem, initial |
| `PROSTG` | 0.110 | g protein/g tissue | Protein in stem, growth |
| `PROSTF` | 0.035 | g protein/g tissue | Protein in stem, final |
| `PCARLF` | 0.502 | g carbon/g tissue | Carbon in leaf |
| `PCARST` | 0.675 | g carbon/g tissue | Carbon in stem |
| `PCARRT` | 0.694 | g carbon/g tissue | Carbon in root |
| `PCARSH` | 0.626 | g carbon/g tissue | Carbon in shell |
| `PCARSD` | 0.606 | g carbon/g tissue | Carbon in seed |
| `PLIPLF` | 0.024 | g lipid/g tissue | Lipid in leaf |
| `PLIGLF` | 0.111 | g lignin/g tissue | Lignin in leaf |

### Carbon and Nitrogen Mining Parameters
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `CMOBMX` | 0.030 | fraction/d | Maximum C mobilization rate |
| `CADSTF` | 0.75 | - | Carbon allocation to stem factor |
| `CADPR1` | 0.140 | - | Carbon allocation parameter 1 |
| `NMOBMX` | 0.074 | fraction/d | Maximum N mobilization rate |
| `NVSMOB` | 0.20 | - | Relative N mobilization in vegetative stage |
| `NRCVR` | 0.15 | - | Fractional value between min/max tissue N |
| `ALPHL` | 0.04 | fraction | Fraction of new leaf growth that is mobile C |
| `ALPHS` | 0.08 | fraction | Fraction of new seed growth that is mobile C |
| `ALPHR` | 0.04 | fraction | Fraction of new root growth that is mobile C |
| `ALPHSH` | 0.08 | fraction | Fraction of new shell growth that is mobile C |

### Root Parameters
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `RTDEPI` | 15.0 | cm | Initial root depth |
| `RFAC1` | 9990. | - | Root growth factor 1 |
| `RTSEN` | 0.020 | - | Root senescence factor |
| `RLDSM` | 0.1 | - | Root length density parameter |
| `RTSDF` | 0.015 | - | Root distribution factor |
| `RWUEP1` | 1.50 | - | Root water uptake parameter 1 |
| `RWUMX` | 0.04 | cm/d | Maximum root water uptake rate |
| `RTNO3` | 0.010 | - | Root NO3 uptake parameter |
| `RTNH4` | 0.010 | - | Root NH4 uptake parameter |
| `PORMIN` | 0.02 | - | Minimum porosity |
| `RTEXF` | 0.10 | - | Root extension factor |

### Phenology Parameters
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `TB` | 0.0 | °C | Base temperature for vegetative development |
| `TO1` | 18.0 | °C | Optimum temperature 1 |
| `TO2` | 28.0 | °C | Optimum temperature 2 |
| `TM` | 45.0 | °C | Maximum temperature |

### Evapotranspiration Parameters
| Variable | Value | Units | Description |
|----------|-------|-------|-------------|
| `KEP` | 0.75 | - | Extinction coefficient for solar radiation |
| `EORATIO` | 1.0 | - | Evapotranspiration ratio |
| `SSKC` | 0.50 | - | Soil surface crop coefficient |
| `SKCBmax` | 0.95 | - | Maximum soil crop coefficient (ASCE short) |
| `TSKC` | 0.50 | - | Tall crop coefficient |
| `TKCBmax` | 0.79 | - | Maximum tall crop coefficient (ASCE tall) |

---

## Cultivar Parameters (CBGRO048.CUL)

### Cultivar Variables
| Variable | Description | Units | Min | Max |
|----------|-------------|-------|-----|-----|
| `EXPNO` | Number of experiments used to estimate cultivar parameters | - | - | - |
| `ECO#` | Code for the ecotype to which this cultivar belongs | - | - | - |
| `CSDL` | Critical Short Day Length | hour | 12.33 | 12.33 |
| `PPSEN` | Slope of relative response of development to photoperiod | 1/hour | 0.000 | 0.000 |
| `EM-FL` | Time between plant emergence and flower appearance (R1) | photothermal days | 25.0 | 28.0 |
| `FL-SH` | Time between first flower and first pod (R3) | photothermal days | 4.0 | 6.0 |
| `FL-SD` | Time between first flower and first seed (R5) | photothermal days | 11.0 | 13.0 |
| `SD-PM` | Time between first seed (R5) and physiological maturity (R7) | photothermal days | 50.00 | 60.00 |
| `FL-LF` | Time between first flower (R1) and end of leaf expansion | photothermal days | 40.00 | 60.00 |
| `LFMAX` | Maximum leaf photosynthesis rate at 30°C, 350 vpm CO2, high light | mg CO2/m²/s | 1.000 | 1.100 |
| `SLAVR` | Specific leaf area under standard growth conditions | cm²/g | 210. | 240. |
| `SIZLF` | Maximum size of full leaf (three leaflets) | cm² | 40.0 | 60.0 |
| `XFRT` | Maximum fraction of daily growth partitioned to seed + shell | fraction | 0.550 | 0.800 |
| `WTPSD` | Maximum weight per seed | g | 0.19 | 0.25 |
| `SFDUR` | Seed filling duration for pod cohort at standard conditions | photothermal days | 23.0 | 23.0 |
| `SDPDV` | Average seed per pod under standard conditions | #/pod | 2.20 | 2.20 |
| `PODUR` | Time required to reach final pod load under optimal conditions | photothermal days | 10.0 | 40.0 |
| `THRSH` | Threshing percentage | fraction | 10.0 | 10.0 |
| `SDPRO` | Fraction protein in seeds | g protein/g seed | 0.180 | 0.180 |
| `SDLIP` | Fraction oil in seeds | g oil/g seed | 0.020 | 0.020 |

---

## Ecotype Parameters (CBGRO048.ECO)

### Ecotype Variables
| Variable | Description | Units | Min | Max |
|----------|-------------|-------|-----|-----|
| `MG` | Maturity group number | - | - | - |
| `TM` | Indicator of temperature adaptation | - | - | - |
| `PL-EM` | Time between planting and emergence (V0) | thermal days | 3.6 | 3.6 |
| `EM-V1` | Time from emergence to first true leaf (V1) | thermal days | 6.0 | 6.0 |
| `V1-JU` | Time from first true leaf to end of juvenile phase | thermal days | 0.0 | 0.0 |
| `JU-R0` | Time required for floral induction | photothermal days | 05.0 | 05.0 |
| `PM06` | Proportion of time between first flower and first pod for first peg | fraction | 0.0 | 0.0 |
| `PM09` | Proportion of time between first seed and maturity for last seed formation | fraction | 0.30 | 0.50 |
| `LNHSH` | Time required for growth of individual shells | photothermal days | 20.0 | 30.0 |
| `R7-R8` | Time between physiological (R7) and harvest maturity (R8) | days | 10.0 | 14.0 |
| `FL-VS` | Time from first flower to last leaf on main stem | photothermal days | 20.00 | 42.00 |
| `TRIFL` | Rate of appearance of leaves on mainstem | leaves/thermal day | 0.35 | 0.50 |
| `RWDTH` | Relative width compared to standard width per node | fraction | 0.9 | 1.8 |
| `RHGHT` | Relative height compared to standard height per node | fraction | 0.9 | 1.2 |
| `R1PPO` | Increase in daylength sensitivity after R1 | hour | 0.000 | 0.000 |
| `OPTBI` | Minimum daily temperature above which no effect on flowering | °C | 0.0 | 0.0 |
| `SLOBI` | Slope reducing progress toward flowering if TMIN < OPTBI | - | 0.000 | 0.000 |

---

## Experiment File Variables (CBX)

### General Information
| Variable | Description | Example |
|----------|-------------|---------|
| `PEOPLE` | Researcher names | Anne Uebelhoer, Sebastian Munz |
| `ADDRESS` | Institution address | University of Hohenheim |
| `SITE` | Location and coordinates | Ihinger Hof, Germany (48°44'N,8°55'E, 478 m a.s.l.) |
| `PAREA` | Plot area | -99 |
| `PRNO` | Plot number | -99 |
| `PLEN` | Plot length | -99 |
| `PLDR` | Plot direction | -99 |
| `PLSP` | Plot spacing | -99 |
| `PLAY` | Plot layout | -99 |
| `HAREA` | Harvest area | -99 |
| `HRNO` | Harvest row number | -99 |
| `HLEN` | Harvest length | -99 |
| `HARM` | Harvest arm | -99 |

### Treatments
| Variable | Description | Example |
|----------|-------------|---------|
| `R` | Replication number | 0 |
| `O` | Option number | 0 |
| `C` | Control number | 0 |
| `CU` | Cultivar code | 1 |
| `FL` | Field code | 1 |
| `SA` | Soil analysis code | 0 |
| `IC` | Initial conditions code | 1 |
| `MP` | Management practices code | 1 |
| `MI` | Management irrigation code | 1 |
| `MF` | Management fertilizer code | 1 |
| `MR` | Management residue code | 1 |
| `MC` | Management chemical code | 0 |
| `MT` | Management tillage code | 0 |
| `ME` | Management environment code | 1 |
| `MH` | Management harvest code | 0 |
| `SM` | Simulation code | 1 |

### Cultivars
| Variable | Description | Example |
|----------|-------------|---------|
| `C` | Cultivar number | 1 |
| `CR` | Crop code | CB |
| `INGENO` | International genotype code | 990003 |
| `CNAME` | Cultivar name | Kalorama 4 |

### Fields
| Variable | Description | Example |
|----------|-------------|---------|
| `ID_FIELD` | Field identification | UHIH0001 |
| `WSTA` | Weather station | UHIH |
| `FLSA` | Flood start date | -99 |
| `FLOB` | Flood end date | -99 |
| `FLDT` | Flood depth | -99 |
| `FLDD` | Flood duration | -99 |
| `FLDS` | Flood stress | -99 |
| `FLST` | Flood stage | -99 |
| `SLTX` | Soil texture | -99 |
| `SLDP` | Soil depth | -99 |
| `ID_SOIL` | Soil identification | UHIH150004 |
| `FLNAME` | Field name | IHO1 |

### Soil Analysis
| Variable | Description | Example |
|----------|-------------|---------|
| `SADAT` | Soil analysis date | 09228 |
| `SMHB` | Soil method bulk density | -99 |
| `SMPX` | Soil method porosity | -99 |
| `SMKE` | Soil method conductivity | -99 |
| `SANAME` | Soil analysis name | -99 |
| `SABL` | Soil analysis bulk density | 30 |
| `SADM` | Soil analysis dry matter | -99 |
| `SAOC` | Soil analysis organic carbon | -99 |
| `SANI` | Soil analysis nitrogen | -99 |
| `SAPHW` | Soil analysis pH water | -99 |
| `SAPHB` | Soil analysis pH buffer | -99 |
| `SAPX` | Soil analysis phosphorus | -99 |
| `SAKE` | Soil analysis potassium | -99 |
| `SASC` | Soil analysis sulfur | -99 |

### Initial Conditions
| Variable | Description | Example |
|----------|-------------|---------|
| `PCR` | Previous crop | BA |
| `ICDAT` | Initial conditions date | 12099 |
| `ICRT` | Initial crop residue type | -99 |
| `ICND` | Initial crop residue nitrogen | -99 |
| `ICRN` | Initial crop residue amount | 1 |
| `ICRE` | Initial crop residue efficiency | 1 |
| `ICWD` | Initial crop residue water | -99 |
| `ICRES` | Initial crop residue | -99 |
| `ICREN` | Initial crop residue nitrogen | -99 |
| `ICREP` | Initial crop residue phosphorus | -99 |
| `ICRIP` | Initial crop residue potassium | -99 |
| `ICRID` | Initial crop residue identification | -99 |
| `ICNAME` | Initial conditions name | -99 |
| `ICBL` | Initial conditions bottom layer | 30 |
| `SH2O` | Initial soil water content | -99 |
| `SNH4` | Initial soil NH4 content | -99 |
| `SNO3` | Initial soil NO3 content | 21.6 |

### Planting Details
| Variable | Description | Example |
|----------|-------------|---------|
| `PDATE` | Planting date | 12135 |
| `EDATE` | Emergence date | -99 |
| `PPOP` | Plant population | 4 |
| `PPOE` | Plant population emergence | 4 |
| `PLME` | Planting method | T |
| `PLDS` | Planting distribution | R |
| `PLRS` | Planting row spacing | 50 |
| `PLRD` | Planting row direction | 0 |
| `PLDP` | Planting depth | 5 |
| `PLWT` | Planting weight | 22 |
| `PAGE` | Planting age | 10 |
| `PENV` | Planting environment | 15 |
| `PLPH` | Planting photoperiod | -99 |
| `SPRL` | Spacing between plants | 5 |

### Irrigation and Water Management
| Variable | Description | Example |
|----------|-------------|---------|
| `EFIR` | Irrigation efficiency | 1 |
| `IDEP` | Irrigation depth | 30 |
| `ITHR` | Irrigation threshold | 50 |
| `IEPT` | Irrigation endpoint | 100 |
| `IOFF` | Irrigation offset | GS000 |
| `IAME` | Irrigation amount | IR001 |
| `IAMT` | Irrigation amount value | 10 |
| `IRNAME` | Irrigation name | -99 |
| `IDATE` | Irrigation date | 12135 |
| `IROP` | Irrigation operation | IR003 |
| `IRVAL` | Irrigation value | 30 |

### Fertilizers (Inorganic)
| Variable | Description | Example |
|----------|-------------|---------|
| `FDATE` | Fertilizer application date | 12134 |
| `FMCD` | Fertilizer material code | FE003 |
| `FACD` | Fertilizer application code | AP002 |
| `FDEP` | Fertilizer application depth | 10 |
| `FAMN` | Fertilizer amount nitrogen | 240 |
| `FAMP` | Fertilizer amount phosphorus | -99 |
| `FAMK` | Fertilizer amount potassium | -99 |
| `FAMC` | Fertilizer amount calcium | -99 |
| `FAMO` | Fertilizer amount organic | -99 |
| `FOCD` | Fertilizer organic code | -99 |
| `FERNAME` | Fertilizer name | -99 |

### Residues and Organic Fertilizer
| Variable | Description | Example |
|----------|-------------|---------|
| `RDATE` | Residue application date | 13001 |
| `RCOD` | Residue code | -99 |
| `RAMT` | Residue amount | -99 |
| `RESN` | Residue nitrogen | -99 |
| `RESP` | Residue phosphorus | -99 |
| `RESK` | Residue potassium | -99 |
| `RINP` | Residue incorporation | -99 |
| `RDEP` | Residue depth | -99 |
| `RMET` | Residue method | -99 |
| `RENAME` | Residue name | -99 |

### Chemical Applications
| Variable | Description | Example |
|----------|-------------|---------|
| `CDATE` | Chemical application date | 09228 |
| `CHCOD` | Chemical code | -99 |
| `CHAMT` | Chemical amount | -99 |
| `CHME` | Chemical method | -99 |
| `CHDEP` | Chemical depth | -99 |
| `CHT` | Chemical type | -99 |
| `CHNAME` | Chemical name | -99 |

### Tillage and Rotations
| Variable | Description | Example |
|----------|-------------|---------|
| `TDATE` | Tillage date | 12134 |
| `TIMPL` | Tillage implement | TI011 |
| `TDEP` | Tillage depth | 10 |
| `TNAME` | Tillage name | -99 |

### Harvest Details
| Variable | Description | Example |
|----------|-------------|---------|
| `HDATE` | Harvest date | 12275 |
| `HSTG` | Harvest stage | GS016 |
| `HCOM` | Harvest component | C |
| `HSIZE` | Harvest size | A |
| `HPC` | Harvest percentage | -99 |
| `HBPC` | Harvest biomass percentage | -99 |
| `HNAME` | Harvest name | Cabbage |

### Simulation Controls
| Variable | Description | Example |
|----------|-------------|---------|
| `GENERAL` | General controls | GE |
| `NYERS` | Number of years | 1 |
| `NREPS` | Number of replications | 1 |
| `START` | Start option | S |
| `SDATE` | Start date | 12001 |
| `RSEED` | Random seed | 2150 |
| `SNAME` | Simulation name | DEFAULT SIMULATION CONTR |
| `SMODEL` | Simulation model | CRGRO |

### Options
| Variable | Description | Example |
|----------|-------------|---------|
| `WATER` | Water simulation | Y |
| `NITRO` | Nitrogen simulation | N |
| `SYMBI` | Symbiosis simulation | N |
| `PHOSP` | Phosphorus simulation | N |
| `POTAS` | Potassium simulation | N |
| `DISES` | Disease simulation | N |
| `CHEM` | Chemical simulation | N |
| `TILL` | Tillage simulation | N |
| `CO2` | CO2 simulation | D |

### Methods
| Variable | Description | Example |
|----------|-------------|---------|
| `WTHER` | Weather method | M |
| `INCON` | Initial conditions method | M |
| `LIGHT` | Light interception method | E |
| `EVAPO` | Evapotranspiration method | R |
| `INFIL` | Infiltration method | S |
| `PHOTO` | Photosynthesis method | L |
| `HYDRO` | Hydrology method | R |
| `NSWIT` | Nitrogen switch | 1 |
| `MESOM` | Soil organic matter method | G |
| `MESEV` | Soil evaporation method | R |
| `MESOL` | Soil method | 2 |

### Management
| Variable | Description | Example |
|----------|-------------|---------|
| `PLANT` | Planting management | R |
| `IRRIG` | Irrigation management | N |
| `FERTI` | Fertilizer management | N |
| `RESID` | Residue management | N |
| `HARVS` | Harvest management | R |

### Outputs
| Variable | Description | Example |
|----------|-------------|---------|
| `FNAME` | File name | N |
| `OVVEW` | Overview output | Y |
| `SUMRY` | Summary output | Y |
| `FROPT` | Frontal output | 1 |
| `GROUT` | Growth output | Y |
| `CAOUT` | Carbon output | Y |
| `WAOUT` | Water output | Y |
| `NIOUT` | Nitrogen output | Y |
| `MIOUT` | Micro output | Y |
| `DIOUT` | Disease output | Y |
| `VBOSE` | Verbose output | N |
| `CHOUT` | Chemical output | Y |
| `OPOUT` | Operation output | N |
| `FMOPT` | Farm management output | A |

---

## Weather Data Variables (WTH)

### Weather Station Information
| Variable | Description | Example | Units |
|----------|-------------|---------|-------|
| `INSI` | Institute code | UHIH | - |
| `LAT` | Latitude | 48.750 | degrees |
| `LONG` | Longitude | 8.917 | degrees |
| `ELEV` | Elevation | 475 | m |
| `TAV` | Average air temperature | 9.6 | °C |
| `AMP` | Temperature amplitude | 17.3 | °C |
| `REFHT` | Reference height | 2.0 | m |
| `WNDHT` | Wind measurement height | -99.0 | m |

### Daily Weather Data
| Variable | Description | Example | Units |
|----------|-------------|---------|-------|
| `DATE` | Date (YYYYDDD format) | 2012001 | - |
| `SRAD` | Solar radiation | 1.9 | MJ/m²/d |
| `TMAX` | Maximum temperature | 10.8 | °C |
| `TMIN` | Minimum temperature | 7.7 | °C |
| `RAIN` | Rainfall | 1.2 | mm/d |
| `DEWP` | Dew point temperature | 8.1 | °C |
| `WIND` | Wind speed | 0.0 | km/d |
| `RHUM` | Relative humidity | 95.3 | % |

---

## Soil Profile Variables (SOL)

### Soil Profile Header
| Variable | Description | Example | Units |
|----------|-------------|---------|-------|
| `PEDON` | Soil pedon identification | UHIH150004 | - |
| `SLTXS` | Soil texture | -99 | - |
| `TAXON` | Soil taxonomic classification | -99 | - |
| `SLSOUR` | Soil source | -99 | - |
| `SSITE` | Soil site | -99 | - |
| `SCOUNT` | Soil county | -99 | - |
| `SLDESC` | Soil description | -99 | - |
| `SLNO` | Soil number | -99 | - |
| `SMHB` | Soil method bulk density | -99 | - |
| `SMPX` | Soil method porosity | -99 | - |
| `SMKE` | Soil method conductivity | -99 | - |
| `SGRP` | Soil group | -99 | - |
| `SCOM` | Soil component | -99 | - |

### Soil Layer Properties
| Variable | Description | Units |
|----------|-------------|-------|
| `SLLB` | Soil layer lower boundary | cm |
| `SLMH` | Soil layer material | - |
| `SLLL` | Soil layer lower limit (wilting point) | cm³/cm³ |
| `SDUL` | Soil layer drained upper limit (field capacity) | cm³/cm³ |
| `SSAT` | Soil layer saturated water content | cm³/cm³ |
| `SRGF` | Soil layer root growth factor | - |
| `SSKS` | Soil layer saturated hydraulic conductivity | cm/h |
| `SBDM` | Soil layer bulk density | g/cm³ |
| `SLOC` | Soil layer organic carbon | % |
| `SLCL` | Soil layer clay | % |
| `SLSI` | Soil layer silt | % |
| `SLCF` | Soil layer coarse fragments | % |
| `SLHW` | Soil layer hardness | - |
| `SLHB` | Soil layer hydraulic B | - |
| `SCEC` | Soil layer cation exchange capacity | cmol/kg |
| `SADC` | Soil layer anion exchange capacity | cmol/kg |

### Initial Soil Conditions
| Variable | Description | Units |
|----------|-------------|-------|
| `SICM` | Initial soil inorganic carbon | % |
| `SNIC` | Initial soil nitrate nitrogen | µg/g |
| `SNH4` | Initial soil ammonium nitrogen | µg/g |
| `SWCON` | Soil water conductivity | - |
| `CN2` | Curve number | - |
| `SALB` | Soil albedo | - |
| `DEPMAX` | Maximum depth | cm |

---

## Simulation Control Variables

### Control Numbers (DSCSM048.CTR)
| CTRNO | Description | Purpose |
|-------|-------------|---------|
| 00 | No change | Default settings |
| 01 | No changes | Use experiment file settings |
| 02 | Summary, evaluate files only | Minimal output for evaluation |
| 03 | Minimum output | Reduced output |
| 04 | Normal output | Standard output |
| 05 | Detail output | Detailed output |
| 06 | All output | Maximum output |
| 07 | CSV outputs | CSV format output |
| 08 | CSV outputs, only Summary.OUT | CSV summary only |
| 11 | Potential yield | No water or nutrient limitations |
| 12 | Potential yield, minimal output | Potential yield with minimal output |
| 24 | EPIC soil temperature method | Use EPIC soil temperature |
| 25 | DSSAT soil temperature method | Use DSSAT soil temperature |
| 31 | No water, no N, no P, no K simulation | No stress simulation |
| 32 | No N, no P, no K simulation | No nutrient stress |
| 33 | No P, no K simulation | No P or K stress |

### Automatic Management Parameters
| Variable | Description | Units |
|----------|-------------|-------|
| `PFRST` | First planting date | YYYYDDD |
| `PLAST` | Last planting date | YYYYDDD |
| `PH2OL` | Lower soil water threshold for planting | % |
| `PH2OU` | Upper soil water threshold for planting | % |
| `PH2OD` | Soil water depth for planting | cm |
| `PSTMX` | Maximum soil temperature for planting | °C |
| `PSTMN` | Minimum soil temperature for planting | °C |
| `IMDEP` | Irrigation management depth | cm |
| `ITHRL` | Irrigation threshold lower | % |
| `ITHRU` | Irrigation threshold upper | % |
| `IROFF` | Irrigation offset | - |
| `IMETH` | Irrigation method | - |
| `IRAMT` | Irrigation amount | mm |
| `IREFF` | Irrigation efficiency | fraction |
| `NMDEP` | Nitrogen management depth | cm |
| `NMTHR` | Nitrogen management threshold | % |
| `NAMNT` | Nitrogen application amount | kg/ha |
| `NCODE` | Nitrogen code | - |
| `NAOFF` | Nitrogen application offset | - |
| `RIPCN` | Residue incorporation percentage | % |
| `RTIME` | Residue time | days |
| `RIDEP` | Residue incorporation depth | cm |
| `HFRST` | First harvest date | YYYYDDD |
| `HLAST` | Last harvest date | YYYYDDD |
| `HPCNP` | Harvest percentage nitrogen | % |
| `HPCNR` | Harvest percentage nitrogen ratio | - |

---

## File Extensions and Formats

### Input File Types
| Extension | File Type | Description |
|-----------|-----------|-------------|
| `.SPE` | Species file | Plant species parameters |
| `.CUL` | Cultivar file | Cultivar-specific parameters |
| `.ECO` | Ecotype file | Ecotype parameters |
| `.CBX` | Experiment file | Complete experiment setup |
| `.WTH` | Weather file | Daily weather data |
| `.SOL` | Soil file | Soil profile properties |
| `.CTR` | Control file | Simulation control settings |
| `.V48` | Batch file | Multiple experiment runs |

### Output File Types
| Extension | File Type | Description |
|-----------|-----------|-------------|
| `.OUT` | Output file | Various simulation outputs |
| `Summary.OUT` | Summary | Overall simulation summary |
| `OVERVIEW.OUT` | Overview | Detailed simulation overview |
| `PlantGro.OUT` | Plant growth | Daily plant growth variables |
| `SoilWat.OUT` | Soil water | Soil water balance |
| `Weather.OUT` | Weather | Weather data used |
| `ET.OUT` | Evapotranspiration | ET calculations |
| `PlantC.OUT` | Plant carbon | Carbon dynamics |
| `PlantN.OUT` | Plant nitrogen | Nitrogen dynamics |
| `SoilCBal.OUT` | Soil carbon balance | Soil carbon balance |
| `SoilOrg.OUT` | Soil organic matter | Soil organic matter dynamics |

---

## Notes

1. **Units**: All units are as specified in the DSSAT documentation
2. **Missing Values**: -99 typically indicates missing or not applicable values
3. **Date Format**: YYYYDDD (year + day of year)
4. **File Locations**: Input files are typically stored in the `Data/` directory
5. **Model Code**: CRGRO048 is the cabbage-specific CROPGRO model
6. **Crop Code**: CB is the standard DSSAT code for cabbage

This reference provides all the input variables needed to run DSSAT cabbage simulations. For detailed explanations of parameter interactions and model behavior, refer to the DSSAT documentation and scientific literature.
