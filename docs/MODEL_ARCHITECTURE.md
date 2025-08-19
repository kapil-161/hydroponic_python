# 🏗️ Model Architecture Documentation
## Complete System Design for Hydroponic CROPGRO Simulation

**Detailed documentation of model structure, integration patterns, and computational flow**

---

## 🎯 **SYSTEM OVERVIEW**

### **Architecture Hierarchy**
```
Hydroponic CROPGRO Simulation System
├── Core Hydroponic Models
│   ├── Photosynthesis Model
│   ├── Mechanistic Nutrient Uptake
│   ├── Root Zone Temperature
│   ├── Leaf Development
│   └── Environmental Control
├── CROPGRO Components
│   ├── Enhanced Respiration
│   ├── Comprehensive Phenology
│   ├── Advanced Senescence
│   ├── Canopy Architecture
│   ├── Nitrogen Balance
│   ├── Nutrient Mobility
│   ├── Integrated Stress
│   └── Temperature Stress
├── Support Systems
│   ├── Configuration Management
│   ├── Weather Generation
│   └── Data Management
└── Integration Framework
    ├── Model Coordination
    ├── Data Flow Management
    └── Validation Systems
```

### **Design Principles**
1. **Modular Architecture**: Each physiological process as independent module
2. **Configuration-Driven**: All parameters externalized to JSON files
3. **Type Safety**: Comprehensive Python type hints and dataclasses
4. **Scientific Accuracy**: Research-based implementations with literature validation
5. **Performance Optimization**: Efficient numerical computation
6. **Extensibility**: Easy addition of new models and crops

---

## 🌿 **CORE HYDROPONIC MODELS**

### **1. Photosynthesis Model**
**File**: `src/models/photosynthesis_model.py`

#### **Model Structure**:
```python
@dataclass
class PhotosynthesisParameters:
    # Biochemical parameters
    vcmax_25: float = 120.0          # RuBisCO carboxylation rate
    jmax_25: float = 210.0           # Electron transport rate
    rd_25: float = 1.2               # Dark respiration rate
    
    # Temperature response
    vcmax_ha: float = 65330.0        # Activation energy
    jmax_ha: float = 43540.0
    rd_ha: float = 46390.0
    
    # Environmental responses
    alpha: float = 0.24              # Quantum efficiency
    theta: float = 0.7               # Curvature factor
    
class PhotosynthesisModel:
    def calculate_photosynthesis(self, ppfd, co2, temperature, vpd) -> PhotosynthesisResponse
    def calculate_temperature_response(self, parameter, temperature) -> float
    def calculate_co2_response(self, ci, temperature) -> Tuple[float, float, float]
```

#### **Integration Points**:
- **Input**: PPFD from canopy model, CO₂ from environmental control
- **Output**: Gross photosynthesis rate to carbon balance
- **Dependencies**: Temperature from RZT model, VPD from environmental control

#### **Computational Flow**:
1. Calculate temperature-adjusted biochemical parameters
2. Determine CO₂ limitation factors (Wc, Wj, Wp)
3. Apply environmental stress factors (VPD, nitrogen)
4. Compute net photosynthesis rate

---

### **2. Mechanistic Nutrient Uptake Model**
**File**: `src/models/mechanistic_nutrient_uptake.py`

#### **Model Structure**:
```python
@dataclass
class NutrientUptakeParameters:
    # Michaelis-Menten kinetics
    vmax_no3: float = 15.0           # Maximum NO₃⁻ uptake rate
    km_no3: float = 50.0             # Half-saturation constant
    vmax_nh4: float = 8.0            # Maximum NH₄⁺ uptake rate
    km_nh4: float = 20.0
    
    # Environmental factors
    temperature_q10: float = 2.3
    ph_optimum: float = 6.0
    
class MechanisticNutrientUptake:
    def calculate_uptake_rate(self, concentrations, root_mass, temperature) -> Dict[str, float]
    def apply_competition_effects(self, individual_rates) -> Dict[str, float]
    def calculate_environmental_factors(self, temperature, ph) -> Dict[str, float]
```

#### **Integration Points**:
- **Input**: Solution concentrations from hydroponic system
- **Output**: Nutrient uptake rates to nitrogen balance model
- **Dependencies**: Root mass from biomass allocation, temperature from RZT

---

### **3. Root Zone Temperature Model**
**File**: `src/models/root_zone_temperature.py`

#### **Model Structure**:
```python
@dataclass
class RZTParameters:
    # Thermal properties
    solution_volume: float = 1500.0   # Tank volume (L)
    specific_heat: float = 4186.0     # Water specific heat (J/kg/K)
    heat_transfer_coeff: float = 25.0 # Heat transfer coefficient
    
    # System geometry
    surface_area: float = 2.5         # Exposed surface area (m²)
    insulation_factor: float = 0.8    # Insulation effectiveness

class RootZoneTemperatureModel:
    def update_temperature(self, ambient_temp, heating_power, duration) -> float
    def calculate_heat_loss(self, solution_temp, ambient_temp) -> float
    def calculate_thermal_mixing(self, volumes, temperatures) -> float
```

---

### **4. Environmental Control System**
**File**: `src/models/environmental_control.py`

#### **Model Structure**:
```python
@dataclass
class EnvironmentalControlParameters:
    # VPD control
    target_vpd: float = 0.8           # Target VPD (kPa)
    vpd_tolerance: float = 0.2        # Acceptable VPD range
    
    # CO₂ control
    target_co2: float = 1000.0        # Target CO₂ (ppm)
    co2_injection_rate: float = 50.0  # Injection rate (ppm/min)
    
    # PID parameters
    pid_kp: float = 1.0
    pid_ki: float = 0.1
    pid_kd: float = 0.05

class EnvironmentalControlModel:
    def update_vpd_control(self, current_vpd, target_vpd) -> VPDControlResponse
    def update_co2_control(self, current_co2, target_co2) -> CO2ControlResponse
    def calculate_equipment_response(self, control_signals) -> EquipmentResponse
```

---

## 🌾 **CROPGRO COMPONENTS**

### **5. Enhanced Respiration Model**
**File**: `src/models/respiration_model.py`

#### **Model Structure**:
```python
@dataclass
class RespirationParameters:
    # Maintenance respiration
    maintenance_base_rate: float = 0.015  # g C/g biomass/day at 25°C
    q10_factor: float = 2.3               # Temperature response
    
    # Growth respiration
    growth_efficiency: float = 0.75       # Conversion efficiency
    
    # Tissue-specific factors
    tissue_factors: Dict[str, float] = field(default_factory=lambda: {
        'leaves': 1.0, 'stems': 0.7, 'roots': 0.8
    })

@dataclass
class BiomassPool:
    tissue_type: TissueType
    dry_mass: float
    age_days: float
    nitrogen_content: float
    recent_growth: float

class EnhancedRespirationModel:
    def calculate_maintenance_respiration(self, biomass_pools, temperature) -> float
    def calculate_growth_respiration(self, new_growth, temperature) -> float
    def calculate_total_respiration(self, biomass_pools, temperature, growth) -> RespirationResponse
```

#### **Scientific Basis**:
- **Q₁₀ temperature response**: Based on Amthor (2000) and Ryan (1991)
- **Maintenance vs growth separation**: Following McCree (1970) paradigm
- **Tissue-specific rates**: From Thornley & Johnson (1990)

---

### **6. Comprehensive Phenology Model**
**File**: `src/models/phenology_model.py`

#### **Model Structure**:
```python
class LettuceGrowthStage(Enum):
    GERMINATION = "GE"
    EMERGENCE = "VE"
    FIRST_LEAF = "V1"
    SECOND_LEAF = "V2"
    # ... continuing through V15
    HEAD_FORMATION = "HF"
    HEAD_DEVELOPMENT = "HD"
    PHYSIOLOGICAL_MATURITY = "PM"

@dataclass
class PhenologyParameters:
    base_temperature: float = 4.0
    thermal_requirements: Dict[str, float] = field(default_factory=dict)
    photoperiod_sensitivity: float = 0.1
    vernalization_requirement: float = 0.0

class ComprehensivePhenologyModel:
    def daily_update(self, temperature, daylength, water_stress, temp_stress) -> PhenologyResponse
    def calculate_thermal_time(self, temperature) -> float
    def check_stage_transition(self) -> bool
    def get_stage_properties(self) -> Dict[str, Any]
```

#### **Growth Stage Properties**:
```python
stage_properties = {
    'GE': {'duration_gdd': 45, 'is_vegetative': True, 'growth_priority': 'root'},
    'VE': {'duration_gdd': 35, 'is_vegetative': True, 'growth_priority': 'shoot'},
    'V1': {'duration_gdd': 40, 'is_vegetative': True, 'growth_priority': 'leaf'},
    # ... detailed properties for each stage
}
```

---

### **7. Advanced Senescence Model**
**File**: `src/models/senescence_model.py`

#### **Model Structure**:
```python
@dataclass
class SenescenceParameters:
    # Age-based senescence
    natural_lifespan_gdd: float = 700.0
    age_senescence_rate: float = 0.02
    
    # Stress-induced senescence
    stress_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'water_stress_trigger': 0.4,
        'nitrogen_stress_trigger': 0.5,
        'temperature_stress_trigger': 0.6
    })
    
    # Nutrient remobilization
    remobilization_efficiency: Dict[str, float] = field(default_factory=lambda: {
        'nitrogen': 0.7, 'phosphorus': 0.6, 'potassium': 0.8
    })

class AdvancedSenescenceModel:
    def daily_update(self, cohort_data, environmental_stress, developmental_state) -> SenescenceResponse
    def calculate_age_senescence(self, cohort_age, thermal_time) -> float
    def calculate_stress_senescence(self, stress_levels) -> float
    def calculate_nutrient_remobilization(self, senescing_biomass) -> Dict[str, float]
```

---

### **8. Canopy Architecture Model**
**File**: `src/models/canopy_architecture.py`

#### **Model Structure**:
```python
@dataclass
class CanopyArchitectureParameters:
    light_extinction_coefficient: float = 0.65
    number_of_layers: int = 5
    leaf_angle_distribution: str = "spherical"
    plant_spacing: Dict[str, float] = field(default_factory=lambda: {
        'between_plants': 0.20, 'between_rows': 0.25
    })

@dataclass
class LightEnvironment:
    ppfd_above_canopy: float
    direct_beam_fraction: float
    diffuse_fraction: float
    solar_zenith_angle: float

class CanopyArchitectureModel:
    def daily_update(self, total_lai, canopy_height, light_env, temperature, co2) -> CanopyResponse
    def calculate_light_distribution(self, light_env, total_lai) -> Tuple[float, float]
    def calculate_layer_photosynthesis(self, ppfd_layers, lai_layers) -> List[float]
```

#### **Light Distribution Algorithm**:
```python
def calculate_light_extinction(self, ppfd_incident, lai_cumulative):
    """Beer's law implementation with multiple layers"""
    ppfd_transmitted = ppfd_incident * exp(-self.k * lai_cumulative)
    return ppfd_transmitted

def partition_sunlit_shaded(self, total_lai):
    """Sunlit/shaded leaf area partitioning"""
    lai_sunlit = (1 - exp(-self.k * total_lai)) / self.k
    lai_shaded = total_lai - lai_sunlit
    return lai_sunlit, lai_shaded
```

---

### **9. Nitrogen Balance Model**
**File**: `src/models/nitrogen_balance.py`

#### **Model Structure**:
```python
@dataclass
class NitrogenBalanceParameters:
    # Uptake kinetics for different N forms
    uptake_kinetics: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'NO3': {'vmax': 15.0, 'km': 50.0},
        'NH4': {'vmax': 8.0, 'km': 20.0},
        'AA': {'vmax': 5.0, 'km': 10.0},
        'UREA': {'vmax': 3.0, 'km': 15.0}
    })
    
    # Critical N concentrations by organ
    critical_n_concentrations: Dict[str, float] = field(default_factory=lambda: {
        'leaves': 0.045, 'stems': 0.020, 'roots': 0.028
    })

@dataclass
class OrganNitrogenState:
    dry_mass: float
    nitrogen_content: float
    nitrogen_concentration: float
    demand: float
    supply: float

class PlantNitrogenBalanceModel:
    def daily_update(self, root_mass, solution_concentrations, environmental_factors, 
                    organ_growth_rates, growth_stage, stress_factors, senescence_rates) -> NitrogenBalanceResponse
    def calculate_nitrogen_uptake(self, root_mass, solution_concentrations, environmental_factors) -> NitrogenUptakeResponse
    def calculate_nitrogen_demand(self, organ_growth_rates, growth_stage) -> Dict[str, float]
    def allocate_nitrogen(self, available_nitrogen, organ_demands) -> Dict[str, float]
```

---

### **10. Nutrient Mobility Model**
**File**: `src/models/nutrient_mobility.py`

#### **Model Structure**:
```python
@dataclass
class NutrientMobilityParameters:
    # Mobility coefficients for different nutrients
    mobility_coefficients: Dict[str, float] = field(default_factory=lambda: {
        'nitrogen': 0.8, 'phosphorus': 0.7, 'potassium': 0.9,
        'calcium': 0.1, 'magnesium': 0.6, 'sulfur': 0.5
    })
    
    # Transport capacities
    xylem_transport_capacity: float = 0.1
    phloem_transport_capacity: float = 0.05
    
    # Environmental effects
    temperature_q10: float = 2.0
    transpiration_coupling: float = 0.8

@dataclass
class OrganNutrientPools:
    organ_name: str
    nutrient_contents: Dict[str, float]
    dry_mass: float
    concentrations: Dict[str, float]

class NutrientMobilityModel:
    def daily_update(self, organ_demands, stress_factors, senescence_rates, growth_stage,
                    water_fluxes, assimilate_fluxes, temperature) -> NutrientMobilityResponse
    def calculate_transport_fluxes(self, sink_demands, source_supplies, transport_capacities) -> List[NutrientTransportFlux]
    def redistribute_nutrients(self, available_nutrients, sink_priorities) -> Dict[str, Dict[str, float]]
```

---

### **11. Integrated Stress Model**
**File**: `src/models/integrated_stress.py`

#### **Model Structure**:
```python
class StressType(Enum):
    WATER = "water"
    TEMPERATURE = "temperature"
    NUTRIENT = "nutrient"
    LIGHT = "light"
    SALINITY = "salinity"
    OXYGEN = "oxygen"
    PH = "ph"

@dataclass
class IntegratedStressParameters:
    # Stress interaction coefficients
    interaction_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Cumulative stress parameters
    stress_memory_duration: int = 7
    stress_accumulation_rate: float = 0.1
    stress_recovery_rate: float = 0.05
    
    # Process-specific sensitivities
    process_sensitivities: Dict[str, Dict[str, float]] = field(default_factory=dict)

class IntegratedStressModel:
    def daily_update(self, current_stress_levels) -> IntegratedStressResponse
    def calculate_stress_interactions(self, individual_stresses) -> Dict[str, float]
    def update_cumulative_stress(self, daily_stress_levels) -> None
    def calculate_process_effects(self, integrated_stress) -> Dict[str, float]
```

#### **Stress Interaction Matrix**:
```python
interaction_matrix = {
    'water': {'temperature': 1.2, 'nutrient': 1.1, 'salinity': 1.3},
    'temperature': {'water': 1.2, 'light': 1.1, 'nutrient': 1.05},
    'nutrient': {'water': 1.1, 'temperature': 1.05, 'ph': 1.15},
    # ... complete interaction matrix
}
```

---

### **12. Temperature Stress Model**
**File**: `src/models/temperature_stress.py`

#### **Model Structure**:
```python
class TemperatureStressType(Enum):
    HEAT = "heat"
    COLD = "cold"
    FROST = "frost"
    OPTIMAL = "optimal"

@dataclass
class TemperatureStressParameters:
    # Temperature thresholds
    optimal_temp_min: float = 18.0
    optimal_temp_max: float = 24.0
    heat_threshold_mild: float = 28.0
    heat_threshold_severe: float = 35.0
    cold_threshold_mild: float = 12.0
    cold_threshold_severe: float = 5.0
    frost_threshold: float = -1.0
    
    # Process sensitivities
    photosynthesis_heat_sensitivity: float = 0.85
    growth_heat_sensitivity: float = 0.90
    
    # Acclimation parameters
    acclimation_rate: float = 0.05
    max_acclimation_days: int = 14

class TemperatureStressModel:
    def daily_update(self, temperature, duration_hours=24.0) -> TemperatureStressResponse
    def classify_temperature_stress(self, temperature) -> TemperatureStressType
    def update_acclimation(self, temperature, stress_type) -> None
    def calculate_damage_and_recovery(self, stress_level, stress_type) -> None
```

---

## 🔧 **SUPPORT SYSTEMS**

### **Configuration Management**
**File**: `src/utils/config_loader.py`

#### **Configuration Architecture**:
```python
@dataclass
class SimulationConfig:
    system_config: Dict[str, Any]
    crop_parameters: Dict[str, Any]
    photosynthesis_model: Dict[str, Any]
    respiration_model: Dict[str, Any]
    phenology_model: Dict[str, Any]
    # ... all model configurations

class ConfigLoader:
    def __init__(self, config_path: Optional[str] = None)
    def get_photosynthesis_parameters(self) -> Dict[str, Any]
    def get_respiration_parameters(self) -> Dict[str, Any]
    # ... parameter getters for all models
    def validate_config(self) -> Dict[str, list]
```

#### **Configuration Hierarchy**:
```json
{
  "system_config": { "tank_volume": 1500.0, "flow_rate": 50.0 },
  "photosynthesis_model": { "vcmax_25": 120.0, "jmax_25": 210.0 },
  "respiration_model": { "maintenance_base_rate": 0.015, "q10_factor": 2.3 },
  "phenology_model": { "base_temperature": 4.0, "thermal_requirements": {...} },
  // ... all model configurations
}
```

---

### **Weather Generation**
**File**: `src/utils/weather_generator.py`

#### **Weather Model Structure**:
```python
@dataclass
class WeatherParameters:
    base_temperature: float = 22.0
    temperature_variation: float = 5.0
    base_humidity: float = 70.0
    base_solar_radiation: float = 18.0
    photoperiod_hours: float = 16.0

class WeatherGenerator:
    def generate_daily_weather(self, day_of_year) -> WeatherData
    def calculate_photoperiod(self, day_of_year, latitude=40.0) -> float
    def generate_temperature_profile(self, base_temp, variation) -> List[float]
```

---

## 🔄 **INTEGRATION FRAMEWORK**

### **Model Coordination**
**File**: `src/hydroponic_simulator.py`

#### **Main Simulator Architecture**:
```python
class AdvancedHydroponicSimulator:
    def __init__(self, config: SimulationConfig):
        # Core hydroponic models
        self.photosynthesis = PhotosynthesisModel(config)
        self.nutrient_uptake = MechanisticNutrientUptake(config)
        self.rzt_model = RootZoneTemperatureModel(config)
        self.environmental_control = EnvironmentalControlModel(config)
        
        # CROPGRO components
        self.respiration = EnhancedRespirationModel(config)
        self.phenology = ComprehensivePhenologyModel(config)
        self.senescence = AdvancedSenescenceModel(config)
        self.canopy = CanopyArchitectureModel(config)
        self.nitrogen_balance = PlantNitrogenBalanceModel(config)
        self.nutrient_mobility = NutrientMobilityModel(config)
        self.integrated_stress = IntegratedStressModel(config)
        self.temperature_stress = TemperatureStressModel(config)
        
    def run_simulation(self, start_date, end_date) -> SimulationResults
    def daily_update(self, weather_data) -> DailyResults
    def integrate_model_responses(self, model_outputs) -> IntegratedResponse
```

### **Data Flow Architecture**:
```
Weather Input → Environmental Control → Plant Models → Growth Integration → Output
     ↓              ↓                    ↓              ↓                ↓
Temperature    →  VPD/CO₂ Control    →  Photosynthesis → Carbon Balance → Biomass
Light          →  Equipment Response →  Nutrient Uptake → N Balance     → LAI
Humidity       →  System Feedback    →  Stress Responses → Allocation   → Development
```

### **Model Interaction Matrix**:
```python
model_dependencies = {
    'photosynthesis': ['environmental_control', 'canopy', 'nitrogen_balance'],
    'nutrient_uptake': ['rzt_model', 'root_dynamics'],
    'nitrogen_balance': ['nutrient_uptake', 'senescence', 'nutrient_mobility'],
    'senescence': ['phenology', 'integrated_stress', 'nitrogen_balance'],
    'canopy': ['phenology', 'leaf_development'],
    'integrated_stress': ['temperature_stress', 'nitrogen_balance'],
    # ... complete dependency mapping
}
```

---

## 📊 **VALIDATION ARCHITECTURE**

### **Testing Framework**
**Files**: `tests/test_*_integration.py`

#### **Test Structure**:
```python
class IntegrationTestSuite:
    def test_model_initialization(self) -> bool
    def test_parameter_validation(self) -> bool
    def test_mass_balance_conservation(self) -> bool
    def test_energy_balance_conservation(self) -> bool
    def test_model_coordination(self) -> bool
    def test_stress_integration(self) -> bool
    def validate_against_literature(self) -> bool
```

#### **Validation Metrics**:
```python
validation_metrics = {
    'mass_balance': {'biomass_error': '<10%', 'nitrogen_error': '<5%'},
    'energy_balance': {'carbon_error': '<8%', 'respiration_ratio': '0.15-0.25'},
    'stress_coordination': {'multi_stress_response': 'realistic'},
    'phenological_progression': {'gdd_accumulation': 'species_appropriate'},
    'nutrient_dynamics': {'uptake_patterns': 'literature_consistent'}
}
```

---

## ⚡ **PERFORMANCE OPTIMIZATION**

### **Computational Efficiency**:
1. **Vectorized Operations**: NumPy arrays for bulk calculations
2. **Caching**: Intermediate results for expensive computations
3. **Lazy Evaluation**: Only compute needed parameters
4. **Memory Management**: Efficient data structures
5. **Parallel Processing**: Independent model updates

### **Numerical Stability**:
1. **Bounded Parameters**: All inputs within realistic ranges
2. **Convergence Checking**: Iterative solutions with tolerance
3. **Error Handling**: Graceful degradation for edge cases
4. **Conservation Laws**: Mass and energy balance enforcement

---

## 🔮 **EXTENSIBILITY DESIGN**

### **Adding New Models**:
```python
# Template for new model integration
class NewPhysiologyModel:
    def __init__(self, parameters: NewModelParameters):
        self.params = parameters
        
    def daily_update(self, inputs: ModelInputs) -> ModelResponse:
        # Model implementation
        return response
        
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'NewPhysiologyModel':
        params = NewModelParameters.from_config(config)
        return cls(params)
```

### **Multi-Crop Adaptation**:
```python
crop_configurations = {
    'lettuce': 'lettuce_config.json',
    'tomato': 'tomato_config.json',
    'basil': 'basil_config.json'
}

class CropSpecificSimulator(AdvancedHydroponicSimulator):
    def __init__(self, crop_type: str, config_path: str):
        crop_config = load_crop_config(crop_type, config_path)
        super().__init__(crop_config)
```

---

## 📈 **FUTURE ARCHITECTURE ENHANCEMENTS**

### **Real-Time Integration**:
- **Sensor Data Ingestion**: Live environmental monitoring
- **Adaptive Control**: Real-time parameter adjustment
- **Predictive Analytics**: Machine learning integration
- **IoT Connectivity**: Edge computing capabilities

### **Cloud Architecture**:
- **Microservices**: Decomposed model services
- **API Gateway**: RESTful model access
- **Database Integration**: Time-series data storage
- **Scalability**: Horizontal scaling for multiple systems

### **Advanced Analytics**:
- **Digital Twin**: Virtual system representation
- **Optimization Engine**: Multi-objective optimization
- **Uncertainty Quantification**: Probabilistic modeling
- **Decision Support**: Automated recommendations

---

*This model architecture documentation provides the complete structural foundation for understanding, maintaining, and extending the Hydroponic CROPGRO Simulation System. The modular design ensures scientific accuracy while maintaining computational efficiency and extensibility for future enhancements.*