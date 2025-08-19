# 🧮 Mathematical Formulations Reference
## Complete Equation Set for Hydroponic CROPGRO Simulation

**All mathematical equations, formulas, and computational methods used in the system**

---

## 📐 **PHOTOSYNTHESIS & CARBON ASSIMILATION**

### **Farquhar-von Caemmerer-Berry (FvCB) Model**

#### **Gross Photosynthesis Rate**
```
Ag = min(Wc, Wj, Wp) - Rd
```

#### **RuBisCO-limited Rate (Wc)**
```
Wc = (Vcmax × (Ci - Γ*)) / (Ci + Kc × (1 + O/Ko))

Where:
- Vcmax = Maximum RuBisCO carboxylation rate
- Ci = Intercellular CO₂ concentration
- Γ* = CO₂ compensation point
- Kc = Michaelis-Menten constant for CO₂
- Ko = Michaelis-Menten constant for O₂
- O = Oxygen concentration
```

#### **RuBP Regeneration-limited Rate (Wj)**
```
Wj = (J × (Ci - Γ*)) / (4 × (Ci + 2 × Γ*))

Where:
- J = Electron transport rate
```

#### **Electron Transport Rate**
```
J = (α×I + Jmax - √((α×I + Jmax)² - 4×θ×α×I×Jmax)) / (2×θ)

Where:
- α = Quantum efficiency of PSII
- I = Incident photosynthetically active radiation
- Jmax = Maximum electron transport rate
- θ = Curvature factor
```

#### **Triose Phosphate Utilization-limited Rate (Wp)**
```
Wp = 3 × TPU × (Ci - Γ*) / (Ci - (1 + 3×α_G)×Γ*)

Where:
- TPU = Triose phosphate utilization rate
- α_G = Fraction of glycolate carbon recycled
```

### **Temperature Dependencies**

#### **Arrhenius Function**
```
f(T) = exp((Ha/R) × (1/298.15 - 1/T))

Where:
- Ha = Activation energy (J mol⁻¹)
- R = Gas constant (8.314 J mol⁻¹ K⁻¹)
- T = Temperature (K)
```

#### **Peaked Temperature Response**
```
f(T) = exp((Ha/R) × (1/298.15 - 1/T)) / (1 + exp((S×T - Hd)/(R×T)))

Where:
- S = Entropy factor
- Hd = Deactivation energy
```

#### **Q₁₀ Temperature Response**
```
Rate(T) = Rate₂₅ × Q₁₀^((T-25)/10)

Where:
- Q₁₀ = Temperature coefficient (typically 2.0-2.5)
```

---

## 🌿 **NUTRIENT UPTAKE & TRANSPORT**

### **Michaelis-Menten Kinetics**

#### **Single Substrate Uptake**
```
V = (Vmax × [S]) / (Km + [S])

Where:
- V = Uptake rate
- Vmax = Maximum uptake rate
- [S] = Substrate concentration
- Km = Half-saturation constant
```

#### **Competitive Inhibition**
```
V = (Vmax × [S]) / (Km × (1 + [I]/Ki) + [S])

Where:
- [I] = Inhibitor concentration
- Ki = Inhibition constant
```

#### **Multi-substrate Competition**
```
Vi = (Vmax_i × [Si]) / (Km_i × (1 + Σⱼ([Sⱼ]/Km_j)) + [Si])
```

### **Ion Transport**

#### **Electrochemical Potential**
```
Δμ̃ = RT×ln([S]in/[S]out) + z×F×ΔΨ

Where:
- R = Gas constant
- T = Temperature
- z = Ion charge
- F = Faraday constant
- ΔΨ = Membrane potential
```

#### **Nernst Equation**
```
E = (RT/zF) × ln([S]out/[S]in)
```

### **Mass Flow and Diffusion**

#### **Fick's First Law**
```
J = -D × (dC/dx)

Where:
- J = Flux density
- D = Diffusion coefficient
- dC/dx = Concentration gradient
```

#### **Convective Flow**
```
J_convection = C × v

Where:
- C = Concentration
- v = Flow velocity
```

---

## 🌡️ **TEMPERATURE EFFECTS & STRESS**

### **Heat Stress Functions**

#### **Linear Heat Stress**
```
S_heat = max(0, (T - T_optimal) / (T_critical - T_optimal))
```

#### **Exponential Heat Stress**
```
S_heat = exp(β × (T - T_critical))
```

#### **Sigmoid Heat Response**
```
S_heat = 1 / (1 + exp(-k × (T - T₅₀)))
```

### **Cold Stress Functions**

#### **Linear Cold Stress**
```
S_cold = max(0, (T_optimal - T) / (T_optimal - T_critical))
```

#### **Frost Damage**
```
Damage = 1 - exp(-r × max(0, T_frost - T)²)
```

### **Temperature Acclimation**

#### **Acclimation Dynamics**
```
dA/dt = k_accl × (T_target - A_current) - k_decay × A_current

Where:
- A = Acclimation state
- k_accl = Acclimation rate constant
- k_decay = Decay rate constant
```

---

## 💧 **WATER RELATIONS & VPD**

### **Vapor Pressure Calculations**

#### **Saturation Vapor Pressure (Tetens Formula)**
```
es(T) = 0.6108 × exp(17.27 × T / (T + 237.3))

Where:
- T = Temperature (°C)
- es = Saturation vapor pressure (kPa)
```

#### **Vapor Pressure Deficit**
```
VPD = es(T) × (1 - RH/100)

Where:
- RH = Relative humidity (%)
```

#### **Magnus Formula (Alternative)**
```
es(T) = 6.1078 × exp(17.08085 × T / (234.175 + T))
```

### **Transpiration Models**

#### **Penman-Monteith Equation**
```
λE = (Δ×(Rn - G) + ρ×cp×VPD/ra) / (Δ + γ×(1 + rs/ra))

Where:
- λE = Latent heat flux
- Δ = Slope of saturation vapor pressure curve
- Rn = Net radiation
- G = Soil heat flux
- ρ = Air density
- cp = Specific heat of air
- ra = Aerodynamic resistance
- rs = Surface resistance
- γ = Psychrometric constant
```

---

## 🌱 **GROWTH & DEVELOPMENT**

### **Phenological Development**

#### **Growing Degree Days**
```
GDD = Σ max(0, (Tmax + Tmin)/2 - Tbase)
```

#### **Development Rate**
```
DVR = f(T) × f(P) × f(V) × f(N) × f(W)

Where:
- f(T) = Temperature function
- f(P) = Photoperiod function
- f(V) = Vernalization function
- f(N) = Nitrogen function
- f(W) = Water function
```

#### **Beta Temperature Function**
```
f(T) = ((T - Tmin)/(Topt - Tmin))^α × ((Tmax - T)/(Tmax - Topt))^β

Where:
- α, β = Shape parameters
- Tmin, Topt, Tmax = Cardinal temperatures
```

### **Biomass Accumulation**

#### **Potential Growth Rate**
```
PGR = RUE × PAR_intercepted × f(T) × f(CO₂) × f(VPD)

Where:
- RUE = Radiation use efficiency
- PAR = Photosynthetically active radiation
```

#### **Actual Growth Rate**
```
AGR = PGR × min(f(N), f(P), f(K), f(W)) × (1 - S_stress)
```

### **Biomass Partitioning**

#### **Sink Strength Model**
```
Partition_i = (SS_i / Σ SS_j) × Available_assimilate

Where:
- SS_i = Sink strength of organ i
```

#### **Allometric Partitioning**
```
Fraction_i = a_i × (Total_biomass)^(b_i - 1)
```

---

## 🍃 **LEAF AREA & CANOPY**

### **Leaf Area Development**

#### **Leaf Area Expansion**
```
LA = LAmax × (1 - exp(-k × TT))

Where:
- LAmax = Maximum leaf area
- k = Expansion rate constant
- TT = Thermal time
```

#### **Specific Leaf Area**
```
SLA = LA / Leaf_dry_weight
```

### **Canopy Light Distribution**

#### **Beer's Law**
```
I(LAI) = I₀ × exp(-k × LAI)

Where:
- I₀ = Incident light intensity
- k = Light extinction coefficient
- LAI = Leaf area index
```

#### **Light Extinction Coefficient**
```
k = √(x² + tan²(β))

Where:
- x = Leaf angle distribution parameter
- β = Solar elevation angle
```

#### **Sunlit/Shaded Leaf Areas**
```
LAI_sunlit = (1 - exp(-k×LAI)) / k
LAI_shaded = LAI - LAI_sunlit
```

---

## 🔄 **RESPIRATION MODELS**

### **Maintenance Respiration**

#### **Basic Maintenance Respiration**
```
Rm = Rmass × Biomass × Q₁₀^((T-25)/10)

Where:
- Rmass = Mass-specific respiration rate
```

#### **Age-dependent Maintenance**
```
Rm = Rmass × Biomass × Q₁₀^((T-25)/10) × (1 + k_age × Age)
```

### **Growth Respiration**

#### **Construction Respiration**
```
Rg = (1 - YG) / YG × Growth_rate

Where:
- YG = Growth efficiency
```

#### **Biochemical Construction Cost**
```
Construction_cost = Σ(Component_fraction × Component_cost)
```

---

## 🧪 **NUTRIENT DYNAMICS**

### **Nitrogen Balance**

#### **N Demand Calculation**
```
N_demand = Growth_rate × N_concentration_optimal
```

#### **N Stress Factor**
```
N_stress = min(1, N_supply / N_demand)
```

#### **Critical N Concentration**
```
N_critical = a × W^(-b)

Where:
- W = Plant dry weight
- a, b = Species-specific parameters
```

### **Nutrient Mobilization**

#### **Remobilization Rate**
```
Remob_rate = k_remob × (N_source - N_minimum) × Mobilization_efficiency
```

#### **Translocation Flux**
```
J_trans = Permeability × (C_source - C_sink) × Area
```

---

## ⚡ **ENVIRONMENTAL CONTROL**

### **PID Control**

#### **Standard PID**
```
u(t) = Kp×e(t) + Ki×∫₀ᵗe(τ)dτ + Kd×de(t)/dt

Where:
- Kp = Proportional gain
- Ki = Integral gain
- Kd = Derivative gain
- e(t) = Error signal
```

#### **Discrete PID**
```
u[n] = Kp×e[n] + Ki×Σᵢ₌₀ⁿe[i]×Δt + Kd×(e[n]-e[n-1])/Δt
```

### **Heat Transfer**

#### **Heat Balance**
```
m×Cp×dT/dt = Q_in - Q_out - Q_loss

Where:
- m = Mass
- Cp = Specific heat capacity
- Q = Heat flow rates
```

#### **Convective Heat Transfer**
```
Q = h × A × (T₁ - T₂)

Where:
- h = Heat transfer coefficient
- A = Surface area
```

---

## 📊 **STRESS INTEGRATION**

### **Multiple Stress Combination**

#### **Multiplicative Model**
```
S_combined = Π Sᵢ
```

#### **Additive Model**
```
S_combined = Σ(wᵢ × Sᵢ) / Σwᵢ
```

#### **Liebig's Law of Minimum**
```
S_combined = min(S₁, S₂, ..., Sₙ)
```

### **Stress Memory**

#### **Exponential Memory**
```
S_memory(t) = α×S_current + (1-α)×S_memory(t-1)
```

#### **Weighted Historical Average**
```
S_memory = Σ(wᵢ × Sᵢ(t-i)) / Σwᵢ
```

---

## 🔬 **VALIDATION STATISTICS**

### **Model Performance Metrics**

#### **Root Mean Square Error**
```
RMSE = √(Σ(Predicted - Observed)² / n)
```

#### **Mean Absolute Error**
```
MAE = Σ|Predicted - Observed| / n
```

#### **Nash-Sutcliffe Efficiency**
```
NSE = 1 - Σ(Observed - Predicted)² / Σ(Observed - Mean_observed)²
```

#### **Index of Agreement**
```
d = 1 - Σ(Predicted - Observed)² / Σ(|Predicted - Mean_obs| + |Observed - Mean_obs|)²
```

#### **Coefficient of Determination**
```
R² = (Σ(Observed - Mean_obs)(Predicted - Mean_pred))² / (Σ(Observed - Mean_obs)²×Σ(Predicted - Mean_pred)²)
```

---

## 🎛️ **NUMERICAL METHODS**

### **Differential Equation Solvers**

#### **Euler's Method**
```
y(t+h) = y(t) + h × f(t, y(t))
```

#### **Runge-Kutta 4th Order**
```
k₁ = h × f(t, y)
k₂ = h × f(t + h/2, y + k₁/2)
k₃ = h × f(t + h/2, y + k₂/2)
k₄ = h × f(t + h, y + k₃)
y(t+h) = y(t) + (k₁ + 2k₂ + 2k₃ + k₄)/6
```

### **Optimization Methods**

#### **Newton-Raphson**
```
x(n+1) = x(n) - f(x(n))/f'(x(n))
```

#### **Gradient Descent**
```
θ(n+1) = θ(n) - α × ∇J(θ(n))
```

---

## 🌐 **UNIT CONVERSIONS**

### **Common Conversions**

#### **Light Units**
```
PPFD (μmol m⁻² s⁻¹) = Solar_radiation (W m⁻²) / 4.6
DLI (mol m⁻² d⁻¹) = PPFD × photoperiod × 3.6
```

#### **Temperature**
```
T(K) = T(°C) + 273.15
T(°F) = T(°C) × 9/5 + 32
```

#### **Pressure**
```
1 kPa = 10 mbar = 0.01 MPa
1 bar = 100 kPa
```

#### **Concentration**
```
ppm = mg L⁻¹ (for solutions)
EC (dS m⁻¹) ≈ TDS (mg L⁻¹) / 640
```

---

*This mathematical reference provides all computational formulas used in the Hydroponic CROPGRO Simulation System. Each equation is presented with variable definitions and applicable units for precise implementation and validation.*