# DSSAT Cabbage Simulation - Complete Mathematical Equations (Final Comprehensive)

This document contains ALL mathematical equations and formulas extracted from the entire DSSAT cabbage simulation codebase, including biomass allocation, stress factors, senescence, and nutrient mobility.

## Table of Contents
1. [Plant Growth Equations](#plant-growth-equations)
2. [Biomass Allocation Equations](#biomass-allocation-equations)
3. [Stress Factor Equations](#stress-factor-equations)
4. [Senescence Equations](#senescence-equations)
5. [Nutrient Mobility Equations](#nutrient-mobility-equations)
6. [Soil Water Balance Equations](#soil-water-balance-equations)
7. [Evapotranspiration Equations](#evapotranspiration-equations)
8. [Nutrient Uptake Equations](#nutrient-uptake-equations)
9. [Soil Temperature Equations](#soil-temperature-equations)
10. [Hydroponic System Equations](#hydroponic-system-equations)
11. [Weather and Solar Radiation Equations](#weather-and-solar-radiation-equations)
12. [Soil Chemistry Equations](#soil-chemistry-equations)
13. [Plant Phosphorus Equations](#plant-phosphorus-equations)
14. [Soil Water Retention Equations](#soil-water-retention-equations)
15. [Root Growth Equations](#root-growth-equations)
16. [Seed and Pod Growth Equations](#seed-and-pod-growth-equations)
17. [Constants and Conversion Factors](#constants-and-conversion-factors)

---

## Plant Growth Equations

### Photosynthesis Equations
```fortran
! Maximum photosynthesis as function of PAR
PTSMAX = PHTMAX * (1.0 - EXP(-(1.0 / PARMAX) * PAR))

! Reduction in photosynthesis due to incomplete canopy
IF (BETN .LE. ROWSPC) THEN
  SPACNG = BETN / ROWSPC
ELSE
  SPACNG = ROWSPC / BETN
ENDIF
KCANR = KCAN - (1. - SPACNG) * KC_SLOPE
PGFAC = 1. - EXP(-KCANR * XHLAI)

! Temperature factor for photosynthesis
TPGFAC = CURV(TYPPGT,FNPGT(1),FNPGT(2),FNPGT(3),FNPGT(4),TDAY)

! Nitrogen factor for photosynthesis
AGEFAC = CURV(TYPPGN,FNPGN(1),FNPGN(2),FNPGN(3),FNPGN(4),RNITP)
AGEREF = CURV(TYPPGN,FNPGN(1),FNPGN(2),FNPGN(3),FNPGN(4),LNREF)
AGEFAC = AGEFAC / AGEREF

! Scaled nitrogen effect
AGEFCC = (1.0 - EXP(-2.0 * AGEFAC)) / (1. - EXP(-2.0 * 1.0))

! Specific leaf weight
IF (SLAAD .GT. 0.0) THEN
  SLW = 1. / SLAAD
ELSE
  SLW = 0.0099
ENDIF
PGSLW = TABEX(YPGSLW, XPGSLW, SLW, 10)

! CO2 effect on photosynthesis
CCK = CCEFF / CCMAX
A0 = -CCMAX * (1. - EXP(-CCK * CCMP))
PRATIO = A0 + CCMAX * (1. - EXP(-CCK * CO2))

! Daily gross photosynthesis
IF (AGEFCC .GE. 1.0) THEN
  E_FAC = AGEFCC * PStres1
ELSE
  E_FAC = MIN(AGEFCC, PStres1)
ENDIF

PG = PTSMAX * SLPF * PGFAC * TPGFAC * E_FAC * PGSLW * PRATIO * PGLFMX * SWFAC

! Cumulative stress effect after R5
IF (DAS .GT. NR5) THEN
  CUMSTR = CUMSTR + DXR57 * (1.0 - SWFAC) * XPOD / PHTHRS10
  COLDSTR = 0.0
  PG = PG * (1.0 - 0.3 * CUMSTR)
ELSE
  CUMSTR = 0.0
  COLDSTR = 0.0
ENDIF

PG = PG * EXCESS
```

---

## Biomass Allocation Equations

### Vegetative Partitioning
```fortran
! Partitioning factors based on development stage
IF (DAS .EQ. NR1) THEN
  FRLFM = TABEX (YLEAF, XLEAF, VSTAGE, 8)
  FRSTMM = TABEX (YSTEM, XLEAF, VSTAGE, 8)
  YY = FRLFM - FRLFF 
  XX = FRSTMM - FRSTMF
ENDIF

! Calculate pattern of vegetative partitioning
IF (DAS .LT. NR1) THEN
  FRLF = TABEX(YLEAF,XLEAF,VSTAGE,8)
  FRSTM = TABEX(YSTEM,XLEAF,VSTAGE,8)
ELSE
  FRLF = FRLFM - YY * FRACDN
  FRSTM = FRSTMM - XX * FRACDN
  IF (DAS .GE. NDLEAF) THEN
    FRLF = FRLFF
    FRSTM = FRSTMF
  ENDIF
ENDIF

! Root partitioning
FRRT = 1. - FRLF - FRSTM

! Stress effects on partitioning
FRRT = ATOP * (1.0 - (MIN(TURFAC, NSTRES, PStres2))) * (1.0 - FRRT) + FRRT

! Cumulative turgor factor
CUMTUR = 0.95*CUMTUR + 0.05*TURFAC
IF (CUMTUR < 1.E-7) CUMTUR = 0.0

! Leaf partitioning with stress effects
FRLF = (1.0 + 0.6*(1.0-CUMTUR))*(1.-FRRT)*FRLF/(FRLF + FRSTM)
FRLF = MIN(FRLF, 0.90*(1. - FRRT))
FRSTM = 1.0 - FRRT - FRLF

! Prevent negative partitioning
FRLF = MIN(FRLF,FRLF*0.98/(MAX(0.001,FRLF+FRSTM)))
FRSTM = MIN(FRSTM,FRSTM*0.98/(MAX(0.001,FRLF+FRSTM)))
FRRT = 1.0 - FRLF - FRSTM

! Vegetative growth demand
VGRDEM = PGAVL / AGRVG
WLDOTN = FRLF * VGRDEM
WSDOTN = FRSTM * VGRDEM
WRDOTN = FRRT * VGRDEM
```

### Reproductive Partitioning
```fortran
! Temperature effect on partitioning to pods
TEMXFR = 0.
DO I = 1,TS
  TEMXFR = TEMXFR + TABEX(YXFTEM,XXFTEM,TGRO(I),6)
ENDDO
TEMXFR = TEMXFR/REAL(TS)

! Drought stress effect on partitioning
TURXFR = XFRMAX * (1. - TURFAC)
TURXFR = MIN(TURXFR,1.0)
TURXFR = MAX(TURXFR,0.0)

! Fruit partitioning factor
XFRT = XFRUIT * TEMXFR + XFRUIT * TURXFR
XFRT = MIN(XFRT,1.0)
XFRT = MAX(XFRT,0.0)

! Available carbon for reproductive growth
CAVTOT = PGAVL * XFRT
CDMREP = CDMSH + CDMSD

! Adjust demand if carbon is limiting
IF (CDMREP .GT. CAVTOT) THEN
  IF (CDMSD .GT. CAVTOT) THEN
    CDMSH = 0.0
    GDMSH = 0.0
    CDMSD = CAVTOT
    IF (CDMSDR .GT. CAVTOT) THEN
      CDMSDR = CAVTOT
    ENDIF
    GDMSD = (MAX(0.0,(CDMSD-CDMSDR)))/AGRSD2 + CDMSDR/(AGRSD1+FNINSD*6.25*RPRO)
    NDMSDR = GDMSDR * FNINSD
  ELSE
    CDMSH = CAVTOT - CDMSD
    GDMSH = CDMSH/AGRSH2
  ENDIF
  CDMREP = CDMSD + CDMSH
ENDIF
```

### Specific Leaf Area (SLA) Calculations
```fortran
! Temperature effect on SLA
TPHFAC = 0.
DO I = 1,TS
  TPHFAC = TPHFAC + TABEX (YSLATM,XSLATM,TGRO(I),5)
ENDDO
TPHFAC = TPHFAC/REAL(TS)

! PAR effect on SLA
PARSLA = (SLAMN+(SLAMX-SLAMN)*EXP(SLAPAR*PAR))/SLAMX

! Turgor effect on SLA
TURFSL = MAX(0.1, (1.0 - (1.0 - TURFAC)*TURSLA))

! Nitrogen effect on SLA
IF (NSLA .GT. 1.2) THEN
  NSLA = 1.2 
ENDIF
NFSL = MAX(0.1, (1.0 - (1.0 - NSTRES)*NSLA))       
CUMNSF = 0.75*CUMNSF + 0.25*NFSL  

! Overall SLA calculation
FFVEG = FVEG * TPHFAC * PARSLA * TURFSL * CUMNSF
F = FFVEG
IF (XFRT*FRACDN .GE. 0.05) F = FFVEG * (1.0 - XFRT * FRACDN)

! For determinate plants
IF (XFRUIT .GT. 0.9999 .AND. DAS .GE. NDLEAF) F = 0.0
```

---

## Stress Factor Equations

### Water Stress
```fortran
! Water stress factor
SWFAC = 1.0
IF (EOP .GT. 1.E-4 .AND. ISWWAT .EQ. 'Y') THEN
  IF ((EOP * 0.1) .GE. TRWUP) THEN
    SWFAC = TRWUP / (EOP * 0.1)
  ENDIF
ENDIF

! Turgor stress factor
TURFAC = TABEX(YTURFAC, XTURFAC, SWFAC, 4)

! Water stress effect on photosynthesis
PG = PG * SWFAC * PSTRES1
```

### Nitrogen Stress
```fortran
! Nitrogen supply
SUPPN = NFIXN + TRNU + NMINEA

! Nitrogen stress factor
NSTFAC = MIN(NSTFAC,1.0) 
NSTFAC = MAX(NSTFAC,0.1)

! Running average for nitrogen stress
PNSTRES = XNSTRES
IF (SUPPN .LT. NSTFAC * NDMNEW .AND. NDMNEW .GT. 0. .AND. YRDOY .NE. YREMRG) THEN
  XNSTRES = MIN(1.0,SUPPN/(NDMNEW * NSTFAC))
ELSE
  XNSTRES = 1.0
ENDIF

NSTRES = XNSTRES * 0.5 + PNSTRES * 0.5
```

### Phosphorus Stress
```fortran
! Phosphorus stress ratio
PSTRESS_RATIO = MIN(1.0, (PConc_Shut - PConc_Shut_Min) / (PConc_Shut_opt - PConc_Shut_Min))

! Phosphorus stress for photosynthesis
IF (PSTRESS_RATIO .GE. SRATPHOTO) THEN
  PStres1 = 1.0
ELSEIF (PSTRESS_RATIO < SRATPHOTO .AND. PSTRESS_RATIO > 1.E-6) THEN
  PStres1 = PSTRESS_RATIO / SRATPHOTO
ELSE
  PStres1 = 0.0
ENDIF

! Phosphorus stress for partitioning
IF (PSTRESS_RATIO .GE. SRATPART) THEN
  PStres2 = 1.0
ELSEIF (PSTRESS_RATIO < SRATPART .AND. PSTRESS_RATIO > 1.E-6) THEN
  PStres2 = PSTRESS_RATIO / SRATPART
ELSE
  PStres2 = 0.0
ENDIF
```

### Temperature Stress
```fortran
! Temperature stress factor
TFAC = TABEX(YTFAC, XTFAC, TAVG, 4)

! Cold stress
COLDSTR = 0.0
IF (TMIN .LT. TMIN_STRESS) THEN
  COLDSTR = (TMIN_STRESS - TMIN) / TMIN_STRESS
ENDIF
```

### Light Stress
```fortran
! Light stress factor
LFAC = TABEX(YLFAC, XLFAC, PAR, 4)

! Light compensation point
LCMP = -(1. / KCAN) * ALOG(ICMP / PAR)
```

---

## Senescence Equations

### Natural Senescence
```fortran
! Natural senescence prior to seed growth
IF (VSTAGE .GE. 5.0) THEN
  PORLFT = 1.0 - TABEX(SENPOR,XSTAGE,VSTAGE,4)
  IF ((WTLF * ( 1.0 - RHOL)) .GT. CLW*PORLFT) THEN
    SLDOT = WTLF * ( 1.0 - RHOL) - CLW * PORLFT
  ENDIF
ENDIF
```

### Nitrogen Mobilization Senescence
```fortran
! Leaf senescence due to N mobilization
LFSEN = SENRTE * NRUSLF / 0.16
LFSEN = MIN(WTLF,LFSEN)
SLDOT = SLDOT + LFSEN
SLDOT = MIN(WTLF,SLDOT)
```

### Light Stress Senescence
```fortran
! Senescence due to low light in lower canopy
LTSEN = 0.0
IF (PAR .GT. 0.) THEN
  LCMP = -(1. / KCAN) * ALOG(ICMP / PAR)
  LTSEN = DTX * (XLAI - LCMP) / TCMP
  LTSEN = MAX(0.0, LTSEN)
ENDIF

! Convert area loss to biomass
SLDOT = SLDOT + LTSEN * 10000. / SLAAD
```

### Water Stress Senescence
```fortran
! Senescence due to water stress
WSLOSS = SENDAY * (1. - RATTP) * WTLF
IF (WSLOSS .GT. 0.0) THEN
  PORLFT = 1.0 - TABEX(SENMAX, XSENMX, VSTAGE, 4)
  WSLOSS = MIN(WSLOSS, WTLF - CLW * PORLFT)
  WSLOSS = MAX(WSLOSS, 0.0)
  SLNDOT = WSLOSS
ENDIF
SLDOT = SLDOT + SLNDOT
SSDOT = SLDOT * PORPT
SSDOT = MIN(SSDOT,0.1*STMWT)
SSNDOT = SLNDOT * PORPT
SSNDOT = MIN(SSDOT,SSNDOT)
```

### Post-R7 Senescence
```fortran
! Senescence after R7
IF (DAS .GT. NR7) THEN
  IF (WTLF .GT. 0.0001) THEN
    SLDOT = WTLF * SENRT2
    SLNDOT = SLDOT
    SSDOT = SLDOT * PORPT
    SSNDOT = SSDOT
  ELSE
    SLDOT = 0.0
    SSDOT = 0.0
    SLNDOT = 0.0
    SSNDOT = 0.0
  ENDIF
  IF (STMWT .LT. 0.0001) THEN
    SLNDOT = 0.0
    SSNDOT = 0.0
  ENDIF
ENDIF
```

---

## Nutrient Mobility Equations

### Nitrogen Mobilization
```fortran
! Nitrogen mobilization rate
NMOBR = NVSMOB * NMOBMX * TDUMX
IF (DAS .GT. NR5) THEN
  NMOBR = NMOBMX * TDUMX2 * (1.0 + 0.5*(1.0 - SWFAC)) * 
          (1.0 + 0.3*(1.0 - NSTRES)) * (NVSMOB + (1. - NVSMOB) * 
          MAX(XPOD,DXR57**2.))
ENDIF

! Potential nitrogen mobilization
NMINEP = NMOBR * (WNRLF + WNRST + WNRRT + WNRSH)

! Actual nitrogen mobilization
IF (NDMNEW - TRNU > 1.E-5 .AND. NMINEP .GT. 1.E-4) THEN
  NMINEA = NDMNEW - TRNU
  IF (NMINEA .GT. NMINEP) NMINEA = NMINEP
  NMINER = NMINEA/NMINEP * NMOBR
  NRUSLF = NMINER * WNRLF
  NRUSST = NMINER * WNRST
  NRUSRT = NMINER * WNRRT
  NRUSSH = NMINER * WNRSH
  CNMINE = NMINEA / 0.16 * RPRO
ENDIF
```

### Phosphorus Mobilization
```fortran
! Phosphorus available for mining
ShutPMin = PConc_Shut_min * Shut_kg 
PRootMin = PConc_Root_min * Root_kg
PShelMin = PConc_Shel_min * Shel_kg

PMine_Avail = PShut_kg + PRoot_kg + PShel_kg - ShutPMin - PRootMin - PShelMin

! Maximum phosphorus mobilization
P_Mobil_max = MAX(0.0, FracPMobil * PMine_Avail)

! Fraction of mined P from different components
IF (PMine_Avail > 0.0) THEN
  ShutMineFrac = (PShut_kg - ShutPMin) / PMine_Avail
  RootMineFrac = (PRoot_kg - PRootMin) / PMine_Avail
  ShelMineFrac = 1.0 - ShutMineFrac - RootMineFrac
ENDIF

! Phosphorus mobilization pools
PShutMobPool = AMAX1(0.0, ShutMob * PConc_Shut) + PShutMobPool
PShutMobToday = AMIN1(PShutMobPool, PShut_kg - ShutPMin)

PRootMobPool = AMAX1(0.0, RootMob * PConc_Root) + PRootMobPool
PRootMobToday = AMIN1(PRootMobPool, PRoot_kg - RootPMin)

PShelMobPool = AMAX1(0.0, ShelMob * PConc_Shel) + PShelMobPool
PShelMobToday = AMIN1(PShelMobPool, PShel_kg - ShelPMin)
```

### Carbon Mobilization
```fortran
! Carbon mobilization due to N shortage
IF (NAVL .LT. NGRVGG) THEN
  IF (NGRVGG .GT. 0.0) THEN
    NRATIO = NAVL / NGRVGG
    WLDOTN = WLDOTN * NRATIO
    WSDOTN = WSDOTN * NRATIO
    WRDOTN = WRDOTN * NRATIO
    NGRLF = NGRLFG * NRATIO
    NGRST = NGRSTG * NRATIO
    NGRRT = NGRRTG * NRATIO
  ENDIF
ENDIF

! Excess carbon calculation
IF (PG .GT. 0.0001 .AND. PGLEFT .GT. 0.00001) THEN
  EXCESS = (1.20 - MIN(1.0, MAX(PGLEFT/PG,0.20)))**0.5
ELSE
  EXCESS = 1.00
ENDIF
```

---

## Soil Water Balance Equations

### Water Balance Components
```fortran
! Daily water balance
WBALAN = + IRRAMT + RAIN                    ! Inflows
         + RESWATADD_T                      ! Inflows
         + netLatFlow                       ! Net lateral flow
         - MULCHEVAP                        ! Outflows
         - DRAIN - RUNOFF - FRUNOFF         ! Outflows
         - ES - EP - EF - (TDFD*10.)       ! Outflows
         - (TSW * 10.) + (TSWY * 10.)      ! Change in soil water
         - FLOOD + FLOODY                   ! Change in flood water
         - SNOW + SNOWY                     ! Change in snow accumulation
         - MULCHWAT + MWY                   ! Change in mulch water

! Soil water integration
SW_mm_NEW(L) = SW_mm(L) + SWDELTS_mm(L) + SWDELTU_mm(L) + 
                SWDELTL_mm(L) + SWDELTX_mm(L) + SWDELTT_mm(L) + 
                SWDELTW_mm(L)

! Convert to volumetric content
SW(L) = SW_mm_NEW(L) / DLAYR(L) / 10.

! Round to 5 decimal places
NewSW = ANINT(SW(L) * 1.e6)/ 1.e6
IF (abs(NewSW) < 1.e-4) NewSW = 0.0
SW(L) = NewSW
```

### Infiltration and Runoff
```fortran
! Available water for infiltration
WINF = WATAVL - RUNOFF + IRRAMT

! Infiltration amount
PINF = WINF * 0.1

! Runoff calculation
PB = WATAVL - IABS * SMX
RUNOFF = WATAVL * PMFRACTION + RUNOFF * (1 - PMFRACTION)
```

### Drainage
```fortran
! Drainage rate
DRCM = 0.9 * SWCON * (SAT(L) - DUL(L)) * DLAYR(L)
DRAIN = PINF * 10.0
```

---

## Evapotranspiration Equations

### ASCE Standardized Reference Evapotranspiration
```fortran
! Average temperature
TAVG = (TMAX + TMIN) / 2.0

! Atmospheric pressure
PATM = 101.3 * ((293.0 - 0.0065 * XELEV)/293.0) ** 5.26

! Psychrometric constant
PSYCON = 0.000665 * PATM

! Slope of saturation vapor pressure curve
UDELTA = 2503.0*EXP(17.27*TAVG/(TAVG+237.3))/(TAVG+237.3)**2.0

! Saturation vapor pressure
EMAX = 0.6108*EXP((17.27*TMAX)/(TMAX+237.3))
EMIN = 0.6108*EXP((17.27*TMIN)/(TMIN+237.3))
ES = (EMAX + EMIN) / 2.0

! Actual vapor pressure
IF (VAPR.GT.1.E-6) THEN
  EA = VAPR
ELSEIF (.NOT.NOTDEW) THEN
  EA = 0.6108*EXP((17.27*TDEW)/(TDEW+237.3))
ELSEIF (RHUM.GT.1.E-6) THEN
  EA = EMIN * RHUM / 100.
ELSE
  EA = 0.6108*EXP((17.27*(TMIN-2.0))/((TMIN-2.0)+237.3))
ENDIF

! RHmin calculation
RHMIN = MAX(20.0, MIN(80.0, EA/EMAX*100.0))
```

### Priestley-Taylor Evapotranspiration
```fortran
! Solar radiation conversion
SLANG = (RADHR(hour)*3.6/1000.)*23.923

! Equilibrium evaporation
EEQ = SLANG*(2.04E-4-1.83E-4*ALBEDO)*(TAIRHR(hour)+29.0)

! Hourly evapotranspiration
ET0(hour) = EEQ*1.1

! Temperature adjustments
IF (TMAX .GT. 35.0) THEN
  ET0(hour) = EEQ*((TMAX-35.0)*0.05+1.1)
ELSE IF (TMAX .LT. 5.0) THEN
  ET0(hour) = EEQ*0.01*EXP(0.18*(TMAX+20.0))
ENDIF

! Daily total
EO = EO + ET0(hour)
EO = MAX(EO,0.0001)
```

### Transpiration
```fortran
! Fraction of intercepted radiation
FDINT = 1.0 - EXP(-(KTRANS) * XHLAI)

! Actual transpiration
EP = MIN(EOP, TRWUP*10.)
```

---

## Nutrient Uptake Equations

### Nitrogen Uptake
```fortran
! Nitrogen uptake factors
FNH4 = 1.0 - EXP(-0.08 * NH4(L))
FNO3 = 1.0 - EXP(-0.08 * NO3(L))

! Root uptake factor
RFAC = RLV(L) * SQRT(SMDFR) * DLAYR(L) * 100.0

! Nitrogen uptake rates
RNO3U(L) = RFAC * FNO3 * RTNO3
RNH4U(L) = RFAC * FNH4 * RTNH4

! Total nitrogen uptake
TRNU = TRNU + RNO3U(L) + RNH4U(L)

! Nitrogen uptake factor
NUF = ANDEM / TRNU

! Maximum uptake
MXNO3U = MAX(0.0,(SNO3(L) - XMIN))
MXNH4U = MAX(0.0,(SNH4(L) - XMIN))

! Minimum nitrogen concentration
XMIN = 0.25 / KG2PPM(L)
XMIN = 0.5 / KG2PPM(L)
```

### Phosphorus and Potassium Uptake
```fortran
! Phosphorus uptake rate
Uptake_Rate_P = Uptake_Rate_N * 0.3

! Potassium uptake rate
Uptake_Rate_K = Uptake_Rate_N * 1.2

! Calcium uptake rate
Uptake_Rate_Ca = Uptake_Rate_N * 0.8

! Magnesium uptake rate
Uptake_Rate_Mg = Uptake_Rate_N * 0.4

! Plant uptake calculations
Plant_Uptake_N = Uptake_Rate_N * (HydroPROP % NO3_Conc + HydroPROP % NH4_Conc) / 100.0
Plant_Uptake_P = Uptake_Rate_P * HydroPROP % PO4_Conc / 100.0
Plant_Uptake_K = Uptake_Rate_K * HydroPROP % K_Conc / 100.0
Plant_Uptake_Ca = Uptake_Rate_Ca * HydroPROP % Ca_Conc / 100.0
Plant_Uptake_Mg = Uptake_Rate_Mg * HydroPROP % Mg_Conc / 100.0
```

---

## Soil Temperature Equations

### Soil Temperature Profile
```fortran
! Water factor for soil temperature
WATERFactor = THETA1 / ((1 + (THETA2 * (EXP(-1 * THETA3 * SWL1Rel)))) ** (1 / THETA4))

! Soil temperature at 2cm depth
TSOIL2cm = 4.5 + (0.188 * SRAD) + (0.24 * TMAX) + (0.38 * TMIN) + 
           (0.248 * TMEAN) - (3.09 * waterFactor)

! Lower boundary temperature
ST(NLAYR+1) = TAV+0.008*(CUMDPT+5.)+TAMP*(1.-0.0172*sqrt(CUMDPT+5.))* 
              sin(pi*(DoyNH-(105.+0.212*(CUMDPT+5.)))/182.5)

! Thermal conductivity
LMBD(L) = (CC1(L)+C2(L)*SW_A2DAY(L)-(CC1(L)-C4(L))* 
          exp(-(C3(L)*SW_A2DAY(L))**4))*864.0

! Heat capacity
CP(L) = CD(L)+4.186*SW_A2DAY(L)
CV(L) = CD(L)+4.186*SW_Yest(L)

! Average bulk density
ABD = TBD / DS(NLAYR)

! Damping depth
FX = ABD/(ABD+686.0*EXP(-5.63*ABD))
DP = 1000.0 + 2500.0*FX

! Water content
WW = 0.356 - 0.144*ABD
B = ALOG(500.0/DP)

! Water content function
WC = AMAX1(0.01, PESW) / (WW * CUMDPT) * 10.0

! Damping depth calculation
FX = EXP(B * ((1.0 - WC) / (1.0 + WC))**2)
DD = FX * DP

! Soil temperature calculation
ALX = (FLOAT(DOY) - HDAY) * 0.0174
TA = TAV + TAMP * COS(ALX) / 2.0
DT = ATOT / 5.0 - TA

DO L = 1, NLAYR
  ZD = -DSMID(L) / DD
  ST(L) = TAV + (TAMP / 2.0 * COS(ALX + ZD) + DT) * EXP(ZD)
END DO

! Surface temperature
SRFTEMP = TAV + (TAMP / 2. * COS(ALX) + DT)
```

---

## Hydroponic System Equations

### Temperature Control
```fortran
! Temperature change calculation
Temperature_Change = Air_Temp_Effect + Insulation_Effect

! Temperature adjustment
Temperature_Adjustment = Temp_Lower_Limit - HydroPROP % Temperature

! Temperature limits
HydroPROP % Temperature = MAX(15.0, MIN(30.0, HydroPROP % Temperature))
```

### Electrical Conductivity
```fortran
! EC change
EC_Change = Nutrient_Contribution * Temperature_Effect + 
            Aeration_Effect + pH_Effect

! EC correction
EC_Correction = EC_Lower_Limit - HydroPROP % EC

! EC limits
HydroPROP % EC = MAX(0.5, MIN(3.0, HydroPROP % EC))
```

### pH Control
```fortran
! pH drift
pH_Drift = Temperature_Effect + Nutrient_Effect + Aeration_Effect + 
           Plant_Uptake_Effect + Buffer_Effect

! pH limits
HydroPROP % pH = MAX(5.0, MIN(7.5, HydroPROP % pH))
```

### Water Management
```fortran
! Transpiration
Transpiration = XHLAI * Temperature_Effect * Humidity_Effect * 2.0

! Evaporation
Evaporation = 0.1 * Temperature_Effect * (1.0 - XHLAI/5.0)

! Water uptake
Water_Uptake = Transpiration + Evaporation

! Volume change
Volume_Change = Water_Uptake - Solution_Flow * (1.0 - HydroPROP % Recirculating)

! Tank volume limits
HydroPROP % TankVolume = MAX(100.0, HydroPROP % TankVolume)
```

### Nutrient Uptake
```fortran
! Root activity
Root_Activity = Root_Activity + RLV(L) * FracRts(L)

! Temperature effect
Temperature_Effect = MAX(0.5, MIN(2.0, Temperature_Effect))

! Nutrient uptake rates
Uptake_Rate_N = Root_Activity * Temperature_Effect * Volume_Effect

! Nutrient concentration limits
HydroPROP % NO3_Conc = MAX(50.0, HydroPROP % NO3_Conc)
HydroPROP % NH4_Conc = MAX(5.0, HydroPROP % NH4_Conc)
HydroPROP % PO4_Conc = MAX(15.0, HydroPROP % PO4_Conc)
HydroPROP % K_Conc = MAX(100.0, HydroPROP % K_Conc)
HydroPROP % Ca_Conc = MAX(80.0, HydroPROP % Ca_Conc)
HydroPROP % Mg_Conc = MAX(20.0, HydroPROP % Mg_Conc)
```

---

## Weather and Solar Radiation Equations

### Solar Declination
```fortran
! Solar declination
DECLIN = 0.397-22.980*COS(RDATE)+3.631*SIN(RDATE)-0.388*COS(2*RDATE)
DECLIN = DECLIN+0.039*SIN(2*RDATE)-0.160*COS(3*RDATE)

! Solar angle calculations
COCO = COS(LAT*CFDGTR)*COS(DECLIN*CFDGTR)
SISI = SIN(LAT*CFDGTR)*SIN(DECLIN*CFDGTR)
HAS = ACOS(AMAX1(-1.,(COS(ANGLE*CFDGTR)-SISI)/COCO))

! Day length
DAYL = 2.*HAS*CFRATH
```

### Vapor Pressure
```fortran
! Saturation vapor pressure
CSVPSAT = 610.78 * EXP(17.269*T/(T+237.30))
```

---

## Soil Chemistry Equations

### Nitrogen Transformations
```fortran
! Temperature factor for denitrification
TFACTOR = EXP(-6572 / TKELVIN + 21.4)

! Water factor for denitrification
WF2 = 3.15 * WFPL - 0.1

! Nitrification rate
TLAG = 0.075 * T2**2

! Ammonium equilibrium
EFFC = AMIN1 (4.0,0.225*SURCEC**0.65)
B = 4.1 - EFFC
B = AMAX1 (B,0.001)
BP1 = 30.0*(1.0-EXP(-0.065*SURCEC))
C = (SPPM-SMINC)/14.0*PBD
A = 1.83
ALNSOL = B*ALOG(C)-A
SOLN = EXP(ALNSOL)
SOILC = SOLN*14.0
BP = C/SOLN
BP = AMAX1 (BP,1.0)
```

### Phosphorus Transformations
```fortran
! Phosphorus immobilization
IMMOBP = 0.10 * IMMOBN

! Phosphorus fraction
FRAC = 20. / DLAYR(L)
```

### Organic Matter
```fortran
! Carbon content
CumResC = 0.40 * OMAData % CumResWt

! Soil organic matter effects
dDUL_SOM = 0.004966 * dOC - 0.2423 * dBD_SOM
dLL_SOM = 0.002228 * dOC + 0.02671 * dBD_SOM

! Humus fraction
HUMFRAC = DMINR * TFSOM * CMF * DMOD1 * PHMIN
```

---

## Plant Phosphorus Equations

### Phosphorus Concentrations
```fortran
! Optimum P concentration in vegetative matter
IF (UseShoots) THEN
  PConc_Shut_opt = PCShutOpt(1)
ELSE
  PConc_Shut_opt = (PCLeafOpt(1)*Leaf_kg + PCStemOpt(1)*Stem_kg) / Shut_kg
ENDIF
PConc_Root_opt = PCRootOpt(1)
PConc_Shel_opt = PCShelOpt(1)
PConc_Seed_opt = PCSeedOpt(1)

! Plant weights
Plant_kg = Shut_kg + Root_kg + Shel_kg + Seed_kg

! Plant P content
PShut_kg = PConc_Shut * Shut_kg
PRoot_kg = PConc_Root * Root_kg
PShel_kg = PConc_Shel * Shel_kg
PSeed_kg = PConc_Seed * Seed_kg
PPlant_kg = PShut_kg + PRoot_kg + PShel_kg + PSeed_kg

! P concentrations
IF (Seed_kg > 0.) THEN
  PConc_Seed = PSeed_kg / Seed_kg
ELSE
  PConc_Seed = 0.
ENDIF

IF (Shel_kg > 0.) THEN
  PConc_Shel = PShel_kg / Shel_kg
ELSE
  PConc_Shel = 0.
ENDIF

IF (Shut_kg > 0.) THEN
  PConc_Shut = PShut_kg / Shut_kg
ELSE
  PConc_Shut = 0.
ENDIF

IF (Root_kg > 0.) THEN
  PConc_Root = PRoot_kg / Root_kg
ELSE
  PConc_Root = 0.
ENDIF

IF (Plant_kg > 0.) THEN
  PConc_Plant = PPlant_kg / Plant_kg
ELSE
  PConc_Plant = 0.0
ENDIF

! Vegetative P concentration
IF (Shut_kg + Root_kg > 1.E-6) THEN
  PConc_Veg = (PConc_Shut * Shut_kg + PConc_Root * Root_kg) / 
              (Shut_kg + Root_kg) * 100.
ENDIF

! P stress ratio
PSTRESS_RATIO = MIN(1.0, (PConc_Shut - PConc_Shut_Min) / 
                    (PConc_Shut_opt - PConc_Shut_Min))

! P stress factors
IF (PSTRESS_RATIO .GE. SRATPHOTO) THEN
  PStres1 = 1.0
ELSEIF (PSTRESS_RATIO < SRATPHOTO .AND. PSTRESS_RATIO > 1.E-6) THEN
  PStres1 = PSTRESS_RATIO / SRATPHOTO
ELSE
  PStres1 = 0.0
ENDIF

IF (PSTRESS_RATIO .GE. SRATPART) THEN
  PStres2 = 1.0
ELSEIF (PSTRESS_RATIO < SRATPART .AND. PSTRESS_RATIO > 1.E-6) THEN
  PStres2 = PSTRESS_RATIO / SRATPART
ELSE
  PStres2 = 0.0
ENDIF
```

---

## Soil Water Retention Equations

### Van Genuchten Model
```fortran
! Water content calculation
RWC = (X(I)-WCR)/(WCS-WCR)
Y(I) = WCR + (WCS-WCR) * RWC

! Conductivity calculation
IF (RWC.GT.1.D-10) THEN
  DLGW = DLOG10(RWC)
  DLGC = DLG2 * DLGW + DLG4
  DLGD = DLGC-DLG3-(RMN + 1) * DLGW/RMN
  
  IF (MTYPE.GT.4) THEN
    DLGD = DLG4-DLG3 + (2.0-RMT + EXPO + 1./RN) * DLGW
  ELSE
    DW = RWC**(1./RM)
    IF (MTYPE.GT.2) THEN
      A = DMIN1(0.999999D0,DMAX1(1.D-7,1.-DW))
      TERM = 1.D0-A**RM
      IF (DW.LT.1.D-04) TERM = RM * DW * (1.-0.5 * (RM-1.) * DW)
    ELSE
      IF (RWC-WCL) 36,36,38
      36 TERM = BINC(DW,AA,BB,BETA)
      38 TERM = 1.-BINC(1.-DW,BB,AA,BETA)
    ENDIF
    RELK = RWC**EXPO * TERM
    IF (RMT.LT.1.5) RELK = RELK * TERM
    DLGC = DLOG10(RELK) + DLG4
    DLGD = DLGC-DLG3-(RMN + 1.) * DLGW/RMN-(RN-1.) * DLOG10(1.-DW)/RN
  ENDIF
ELSE
  DLGC = -30
  DLGD = -30
  COND = 1.D-30
  DIF = 1.D-30
ENDIF

! Final values
DLGC = DMAX1(-30.D0,DLGC)
DLGD = DMAX1(-30.D0,DLGD)
DLGD = DMIN1(30.D0,DLGD)
COND = 10.**DLGC
DIF = 10.**DLGD
```

---

## Root Growth Equations

### Root Depth
```fortran
! Root depth increment
RTDEP = RTDEP + DTX * RFAC2 * MIN(SWDF,SWEXF) * 
        (1.0 - EXP(-0.5 * (TMAX - TMIN))) * 
        (1.0 - EXP(-0.1 * (TMAX - TMIN)))

! Root length initialization
RLINIT = WTNEW * FRRT * PLTPOP * RFAC1 * DEP / (RTDEP * DLAYR(L))
```

---

## Seed and Pod Growth Equations

### Seed Growth
```fortran
! Temperature factor for seed growth
TMPFAC = 0.
TMPFCS = 0.
DO I = 1,TS
  TMPFAC = CURV(TYPSDT,FNSDT(1),FNSDT(2),FNSDT(3),FNSDT(4),TGRO(I))
  TMPFCS = TMPFCS + TMPFAC
ENDDO
TMPFAC = TMPFCS / REAL(TS)

! Puncture damage effect
IF (PUNCSD .GT. 0.0) THEN
  REDPUN = 1.0 - (PUNCTR/PUNCSD) * RPRPUN
  REDPUN = MAX(0.0,REDPUN)
ELSE
  REDPUN = 1.0
ENDIF

! Water stress effect
TURADD = TABEX (YTRFAC,XTRFAC,TURFAC,4)

! Maximum seed growth rate
SDGR = SDVAR * TMPFAC * REDPUN * (1.-(1.-DRPP)*SRMAX) * (1. + TURADD)

! Shell damage effect
REDSHL = 0
IF (SDDES(NPP).GT.0) THEN
  REDSHL = WTSHE(NPP)*SDDES(NPP)/(SDDES(NPP)+SDNO(NPP))
ENDIF

! Maximum seed weight
SDMAX = (WTSHE(NPP)-REDSHL)*THRESH/(100.-THRESH)-WTSD(NPP)
SDMAX = MAX(0.0,SDMAX)

! Seed growth demand
GDMSD = GDMSD + MIN(SDGR*SDNO(NPP)*REDPUN, SDMAX)

! Nitrogen demand for seeds
NDMSD = FNINSD * GDMSD

! Mobilized nitrogen for seed growth
IF (NDMSD .GT. NMINEP) THEN
  NDMSDR = NMINEP
ELSE
  NDMSDR = NDMSD
ENDIF
GDMSDR = NDMSDR/FNINSD
CDMSDR = GDMSDR * (AGRSD1 + FNINSD*6.25 * RPRO)

! Total carbohydrate demand
CDMSD = (MAX(0.0,(GDMSD - GDMSDR))) * AGRSD2 + CDMSDR
```

### Shell Growth
```fortran
! Shell growth rate
GRRAT1 = SHVAR * TMPFAC * (1.- (1.-DRPP) * SRMAX) * (1.0 + TURADD)

! Shell growth demand
IF (PAGE .LE. LNGSH .AND. SHELN(NPP) .GT. 0.0 .AND. GRRAT1 .GT. 0.0) THEN
  IF (PAGE .GE. LNGPEG) THEN
    ADDSHL = GRRAT1 * SHELN(NPP)
  ELSE
    ADDSHL = GRRAT1 * SHELN(NPP) * SHLAG
  ENDIF
ENDIF
GDMSH = GDMSH + ADDSHL

! Shell nitrogen and carbon demand
NDMSH = FNINSH * GDMSH
CDMSH = GDMSH * AGRSH2
```

---

## Constants and Conversion Factors

### Mathematical Constants
```fortran
PI = 3.14159265                    ! Pi constant
RAD = PI/180.0                     ! Conversion factor degrees to radians
CFDATR = 2.*PI/365.                ! Day of year conversion
CFDGTR = 2.*PI/360.                ! Degree conversion
CFRATH = 12./PI                    ! Hour angle conversion
```

### Physical Constants
```fortran
RGAS = 8.314                       ! Universal gas constant (J/mol/K)
O2 = 210000                        ! Atmospheric O2 concentration (µL/L)
CICA = 0.7                         ! Ci/Ca ratio for CO2=350 µL/L
GAMST = 0.5*O2/TAU                 ! CO2 compensation point
TAU = exp(-3.949 + 28990.0/RT)     ! CO2/O2 specificity factor
44.0 = 44.0                        ! CO2 molecular weight (g/mol)
1000.0 = 1000.0                    ! Conversion factor mg to g
0.16 = 0.16                        ! Nitrogen content of protein (g N/g protein)
273.0 = 273.0                      ! Absolute zero in Kelvin
30.0 = 30.0                        ! Reference temperature (°C)
350.0 = 350.0                      ! Reference CO2 concentration (µL/L)
```

### Soil Constants
```fortran
TOL = 0.5                          ! Tolerance for water table level (cm)
Kd = 0.5                           ! Drawdown coefficient (fraction/day)
MAXIABS = 0.6                      ! Maximum initial abstraction ratio
```

### Hydroponic Constants
```fortran
MXLAYR = 10                        ! Maximum hydroponic layers
HydroDepth = 30.0                  ! Standard hydroponic depth (cm)
HydroBD = 0.2                      ! Hydroponic bulk density (g/cm³)
HydroVolume = 1000.0               ! Initial tank volume (L)
HydroFlowRate = 5.0                ! Initial flow rate (L/min)
MinTemp = 15.0                     ! Minimum hydroponic temperature (°C)
MaxTemp = 30.0                     ! Maximum hydroponic temperature (°C)
PO4Threshold = 30.0                ! PO4 concentration threshold
```

### Array Dimensions
```fortran
NL = 20                            ! Maximum number of soil layers
TS = 24                            ! Number of hourly time steps per day
NAPPL = 9000                       ! Maximum number of applications or operations
NCOHORTS = 300                     ! Maximum number of cohorts
NELEM = 3                          ! Number of elements modeled (N, P, K)
NumOfDays = 1000                   ! Maximum days in sugarcane run
NumOfStalks = 42                   ! Maximum stalks per sugarcane stubble
EvaluateNum = 40                   ! Number of evaluation variables
MaxFiles = 500                     ! Maximum number of output files
MaxPest = 500                      ! Maximum number of pest operations
```

---

## Notes

This comprehensive collection represents the complete mathematical framework of the DSSAT cabbage simulation model, covering all major processes including:

1. **Biomass Allocation**: Complete partitioning equations for vegetative and reproductive growth
2. **Stress Factors**: Water, nitrogen, phosphorus, temperature, and light stress calculations
3. **Senescence**: Natural, stress-induced, and developmental senescence equations
4. **Nutrient Mobility**: Nitrogen and phosphorus mobilization and remobilization
5. **Plant Growth**: Photosynthesis, respiration, and growth integration
6. **Soil Processes**: Water balance, temperature, chemistry, and nutrient cycling
7. **Hydroponic Systems**: Complete nutrient solution management
8. **Weather**: Solar radiation, vapor pressure, and atmospheric calculations

All equations use the units specified in the DSSAT documentation and follow Fortran naming conventions. The mathematical functions include EXP, SIN, COS, SQRT, LOG, TAN, ALOG, DLOG10, and many others. This represents the most complete collection of equations from the DSSAT cabbage simulation model.