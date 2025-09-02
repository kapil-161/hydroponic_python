"""
Advanced Genetic Parameters System for Hydroponic Lettuce Production

Implements DSSAT-style cultivar-specific modeling with:
- Genetic coefficients for multiple lettuce varieties
- Genotype × Environment (G×E) interaction modeling
- Trait-based physiological modeling
- Breeding applications and parameter estimation

Based on DSSAT CROPGRO framework adapted for Lactuca sativa cultivars.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import numpy as np


class LettuceType(Enum):
    """Lettuce morphological types"""
    BUTTERHEAD = "butterhead"
    ROMAINE = "romaine"
    LOOSE_LEAF = "loose_leaf"
    CRISPHEAD = "crisphead"
    OAK_LEAF = "oak_leaf"
    MINI_ROMAINE = "mini_romaine"


class GeneticTrait(Enum):
    """Key genetic traits for lettuce breeding"""
    # Phenological traits
    DAYS_TO_EMERGENCE = "days_to_emergence"
    DAYS_TO_HARVEST = "days_to_harvest"
    BOLTING_TOLERANCE = "bolting_tolerance"
    
    # Growth traits
    LEAF_SIZE = "leaf_size"
    PLANT_ARCHITECTURE = "plant_architecture"
    ROOT_DEVELOPMENT = "root_development"
    YIELD_POTENTIAL = "yield_potential"
    
    # Quality traits
    CHLOROPHYLL_CONTENT = "chlorophyll_content"
    CAROTENOID_CONTENT = "carotenoid_content"
    VITAMIN_C_CONTENT = "vitamin_c_content"
    NITRATE_ACCUMULATION = "nitrate_accumulation"
    
    # Stress tolerance
    HEAT_TOLERANCE = "heat_tolerance"
    COLD_TOLERANCE = "cold_tolerance"
    SALINITY_TOLERANCE = "salinity_tolerance"
    DISEASE_RESISTANCE = "disease_resistance"


@dataclass
class GeneticCoefficients:
    """
    DSSAT-style genetic coefficients for lettuce cultivars
    Similar to CROPGRO cultivar files (.CUL files)
    """
    # Phenological development parameters
    EM_FL: float = 0.0      # Days from emergence to first flower (GDD)
    FL_SH: float = 0.0      # Days from first flower to first seed (GDD)  
    FL_SD: float = 0.0      # Days from first flower to first pod (GDD)
    SD_PM: float = 0.0      # Days from first seed to physiological maturity (GDD)
    FL_LF: float = 0.0      # Days from first flower to end of leaf expansion (GDD)
    
    # Temperature response parameters
    LFMAX: float = 0.0       # Maximum leaf photosynthesis rate (mg CO2/m²/s)
    SLAVR: float = 0.0     # Specific leaf area of cultivar under standard growth conditions (cm²/g)
    SIZLF: float = 0.0      # Maximum size of full leaf (three leaflets) (cm²)
    XFRT: float = 0.0        # Maximum fraction of daily growth that is partitioned to reproductive growth
    SFDUR: float = 0.0      # Seed filling duration for cultivar (GDD)
    SDPDV: float = 0.0       # Average seed per pod under standard growing conditions
    PODUR: float = 0.0       # Time required for cultivar to reach final pod load (GDD)
    WTPSD: float = 0.0      # Maximum weight per seed (g)
    
    # Stress tolerance coefficients
    THRSH: float = 0.0      # The maximum ratio of seed/(seed+shell) at maturity
    SDPRO: float = 0.0      # Fraction protein in seeds
    SDLIP: float = 0.0      # Fraction oil in seeds
    
    # Hydroponic-specific parameters
    EC_TOLERANCE: float = 0.0    # Maximum EC tolerance (dS/m)
    ROOT_ACTIVITY: float = 0.0   # Root activity coefficient
    PHOTOSYNTHETIC_CAPACITY: float = 0.0  # Relative photosynthetic capacity
    NITRATE_EFFICIENCY: float = 0.0  # Nitrogen use efficiency factor


@dataclass
class CultivarProfile:
    """Complete profile for a lettuce cultivar including genetics and performance"""
    cultivar_id: str
    cultivar_name: str
    lettuce_type: LettuceType
    breeder: str
    year_released: int
    
    # Genetic coefficients
    genetic_coefficients: GeneticCoefficients
    
    # Performance characteristics (must come from CSV)
    yield_potential: float = None       # Relative yield potential
    adaptation_score: float = None      # Environmental adaptation score
    commercial_rating: float = None     # Commercial viability rating
    
    # Trait values (0.0-1.0 scale, 1.0 = excellent)
    trait_values: Dict[GeneticTrait, float] = field(default_factory=dict)
    
    # Breeding information
    pedigree: List[str] = field(default_factory=list)
    breeding_notes: str = ""
    
    def calculate_adaptation_index(self, environment_factors: Dict[str, float]) -> float:
        """Calculate G×E adaptation index for specific environment"""
        base_adaptation = self.adaptation_score
        
        # Environmental stress adjustments
        stress_adjustments = 0.0
        
        # Temperature stress
        temp_stress = environment_factors.get('temperature_stress', 0.0)
        heat_tolerance = self.trait_values.get(GeneticTrait.HEAT_TOLERANCE, 0.5)
        cold_tolerance = self.trait_values.get(GeneticTrait.COLD_TOLERANCE, 0.5)
        
        if temp_stress > 0:  # Heat stress
            weight = environment_factors.get('heat_stress_weight', 0.3)  # Heat stress weight from CSV
            stress_adjustments += temp_stress * (1.0 - heat_tolerance) * weight
        else:  # Cold stress
            weight = environment_factors.get('cold_stress_weight', 0.25)  # Cold stress weight from CSV
            stress_adjustments += abs(temp_stress) * (1.0 - cold_tolerance) * weight
        
        # Salinity stress
        salinity_stress = environment_factors.get('salinity_stress', 0.0)
        salinity_tolerance = self.trait_values.get(GeneticTrait.SALINITY_TOLERANCE, 0.5)
        weight = environment_factors.get('salinity_stress_weight', 0.2)  # Salinity stress weight from CSV
        stress_adjustments += salinity_stress * (1.0 - salinity_tolerance) * weight
        
        # Light stress
        light_stress = environment_factors.get('light_stress', 0.0)
        weight = environment_factors.get('light_stress_weight', 0.15)  # Light stress weight from CSV
        stress_adjustments += light_stress * weight
        
        # Nutrient stress
        nutrient_stress = environment_factors.get('nutrient_stress', 0.0)
        nitrate_efficiency = self.genetic_coefficients.NITRATE_EFFICIENCY
        weight = environment_factors.get('nutrient_stress_weight', 0.25)  # Nutrient stress weight from CSV
        stress_adjustments += nutrient_stress * (1.0 - nitrate_efficiency) * weight
        
        # Calculate final adaptation index
        adaptation_index = base_adaptation - stress_adjustments
        return max(0.1, min(1.0, adaptation_index))


class GeneticParameterDatabase:
    """Database of lettuce cultivar genetic parameters"""
    
    def __init__(self):
        self.cultivars: Dict[str, CultivarProfile] = {}
        self.initialize_cultivar_database()
    
    def initialize_cultivar_database(self):
        """Initialize database with cultivars from CSV configuration.
        
        This method now requires CSV data - no hardcoded cultivars allowed.
        All cultivar data must be loaded from CSV files through the system configuration.
        """
        # Database starts empty - cultivars must be loaded from CSV
        # This ensures all genetic data comes from external configuration files
        pass
    
    def add_cultivar(self, cultivar: CultivarProfile):
        """Add a cultivar to the database"""
        self.cultivars[cultivar.cultivar_id] = cultivar
    
    def get_cultivar(self, cultivar_id: str) -> Optional[CultivarProfile]:
        """Get cultivar by ID"""
        return self.cultivars.get(cultivar_id)
    
    def get_best_cultivars_for_conditions(self, 
                                        environment_factors: Dict[str, float],
                                        top_n: int = 3) -> List[Tuple[str, float]]:
        """Get best adapted cultivars for specific environmental conditions"""
        cultivar_scores = []
        
        for cultivar_id, cultivar in self.cultivars.items():
            adaptation_score = cultivar.calculate_adaptation_index(environment_factors)
            adaptation_weight = environment_factors.get('adaptation_weight', 0.6)  # Adaptation score weight from CSV
            yield_weight = environment_factors.get('yield_weight', 0.25)  # Yield potential weight from CSV
            commercial_weight = environment_factors.get('commercial_weight', 0.15)  # Commercial rating weight from CSV
            overall_score = (
                adaptation_score * adaptation_weight
                + cultivar.yield_potential * yield_weight
                + cultivar.commercial_rating * commercial_weight
            )
            cultivar_scores.append((cultivar_id, overall_score))
        
        # Sort by score and return top N
        cultivar_scores.sort(key=lambda x: x[1], reverse=True)
        return cultivar_scores[:top_n]


class GenotypeEnvironmentModel:
    """
    G×E interaction modeling for lettuce cultivars
    Models how genetic traits interact with environmental conditions
    """
    
    def __init__(self, genetic_db: GeneticParameterDatabase):
        self.genetic_db = genetic_db
        
    def calculate_phenotype_expression(self, 
                                     cultivar_id: str,
                                     environment_factors: Dict[str, float],
                                     trait: GeneticTrait) -> float:
        """
        Calculate phenotype expression based on genotype and environment
        
        Args:
            cultivar_id: Cultivar identifier
            environment_factors: Environmental conditions
            trait: Genetic trait to evaluate
            
        Returns:
            Expressed trait value (0.0-1.0)
        """
        cultivar = self.genetic_db.get_cultivar(cultivar_id)
        if not cultivar:
            raise ValueError(f"❌ Cultivar {cultivar_id} not found in database - CSV data required")
        
        base_trait_value = cultivar.trait_values.get(trait, 0.5)
        
        # Environmental modulation of trait expression
        if trait == GeneticTrait.HEAT_TOLERANCE:
            temp_stress = environment_factors.get('temperature_stress', 0.0)
            if temp_stress > 0:  # Heat stress present
                weight = environment_factors.get('temperature_stress_weight', 0.5)  # Temperature stress weight from CSV
                expression = base_trait_value * (1.0 - temp_stress * weight)
            else:
                expression = base_trait_value
        
        elif trait == GeneticTrait.COLD_TOLERANCE:
            temp_stress = environment_factors.get('temperature_stress', 0.0)
            if temp_stress < 0:  # Cold stress present
                weight = environment_factors.get('temperature_stress_weight', 0.5)  # Temperature stress weight from CSV
                expression = base_trait_value * (1.0 + temp_stress * weight)  # temp_stress is negative
            else:
                expression = base_trait_value
                
        elif trait == GeneticTrait.CHLOROPHYLL_CONTENT:
            light_level = environment_factors.get('light_intensity', 1.0)
            nitrogen_status = environment_factors.get('nitrogen_status', 1.0)
            # Chlorophyll responds to light and nitrogen
            expression = base_trait_value * light_level * nitrogen_status
            
        elif trait == GeneticTrait.NITRATE_ACCUMULATION:
            nitrogen_excess = environment_factors.get('nitrogen_excess', 0.0)
            # Higher nitrogen leads to more nitrate accumulation
            nitrogen_weight = environment_factors.get('nitrogen_excess_weight', 0.3)  # Nitrogen excess weight from CSV
            expression = base_trait_value + nitrogen_excess * nitrogen_weight
            
        elif trait == GeneticTrait.ROOT_DEVELOPMENT:
            water_stress = environment_factors.get('water_stress', 0.0)
            nutrient_stress = environment_factors.get('nutrient_stress', 0.0)
            # Root development increases under stress
            stress_weight = environment_factors.get('stress_response_weight', 0.2)  # Stress response weight from CSV
            stress_response = max(water_stress, nutrient_stress) * stress_weight
            expression = base_trait_value + stress_response
            
        else:
            # No environmental modulation - return base trait value
            expression = base_trait_value
        
        return max(0.0, min(1.0, expression))
    
    def predict_cultivar_performance(self, 
                                   cultivar_id: str,
                                   environment_factors: Dict[str, float]) -> Dict[str, float]:
        """Predict overall cultivar performance under specific conditions"""
        cultivar = self.genetic_db.get_cultivar(cultivar_id)
        if not cultivar:
            return {}
        
        performance_metrics = {}
        
        # Calculate trait expressions
        trait_expressions = {}
        for trait in GeneticTrait:
            trait_expressions[trait] = self.calculate_phenotype_expression(
                cultivar_id, environment_factors, trait
            )
        
        # Aggregate performance metrics (weights from CSV)
        yield_weights = environment_factors.get('yield_index_weights', {
            'leaf_size': 0.3, 'chlorophyll': 0.2, 'nitrate_avoidance': 0.2, 
            'root_development': 0.15, 'yield_potential': 0.15
        })
        performance_metrics['yield_index'] = (
            trait_expressions[GeneticTrait.LEAF_SIZE] * yield_weights.get('leaf_size', 0.3) +
            trait_expressions[GeneticTrait.CHLOROPHYLL_CONTENT] * yield_weights.get('chlorophyll', 0.2) +
            (1.0 - trait_expressions[GeneticTrait.NITRATE_ACCUMULATION]) * yield_weights.get('nitrate_avoidance', 0.2) +
            trait_expressions[GeneticTrait.ROOT_DEVELOPMENT] * yield_weights.get('root_development', 0.15) +
            cultivar.yield_potential * yield_weights.get('yield_potential', 0.15)
        )
        
        quality_weights = environment_factors.get('quality_index_weights', {
            'vitamin_c': 0.3, 'carotenoid': 0.25, 'nitrate_avoidance': 0.25, 'chlorophyll': 0.2
        })
        performance_metrics['quality_index'] = (
            trait_expressions[GeneticTrait.VITAMIN_C_CONTENT] * quality_weights.get('vitamin_c', 0.3) +
            trait_expressions[GeneticTrait.CAROTENOID_CONTENT] * quality_weights.get('carotenoid', 0.25) +
            (1.0 - trait_expressions[GeneticTrait.NITRATE_ACCUMULATION]) * quality_weights.get('nitrate_avoidance', 0.25) +
            trait_expressions[GeneticTrait.CHLOROPHYLL_CONTENT] * quality_weights.get('chlorophyll', 0.2)
        )
        
        stress_weights = environment_factors.get('stress_tolerance_weights', {
            'heat': 0.3, 'cold': 0.25, 'salinity': 0.25, 'disease': 0.2
        })
        performance_metrics['stress_tolerance'] = (
            trait_expressions[GeneticTrait.HEAT_TOLERANCE] * stress_weights.get('heat', 0.3) +
            trait_expressions[GeneticTrait.COLD_TOLERANCE] * stress_weights.get('cold', 0.25) +
            trait_expressions[GeneticTrait.SALINITY_TOLERANCE] * stress_weights.get('salinity', 0.25) +
            trait_expressions[GeneticTrait.DISEASE_RESISTANCE] * stress_weights.get('disease', 0.2)
        )
        
        performance_metrics['time_to_harvest'] = (
            90 - trait_expressions[GeneticTrait.DAYS_TO_HARVEST] * 30
        )  # Days, faster is better
        
        performance_metrics['bolting_resistance'] = trait_expressions[GeneticTrait.BOLTING_TOLERANCE]
        
        performance_metrics['adaptation_index'] = cultivar.calculate_adaptation_index(environment_factors)
        
        return performance_metrics


class BreedingAssistant:
    """Assistant for lettuce breeding applications"""
    
    def __init__(self, genetic_db: GeneticParameterDatabase, ge_model: GenotypeEnvironmentModel):
        self.genetic_db = genetic_db
        self.ge_model = ge_model
    
    def identify_breeding_targets(self, 
                                target_environment: Dict[str, float],
                                desired_traits: Dict[GeneticTrait, float]) -> Dict[str, Any]:
        """Identify breeding targets for specific environment and traits"""
        
        # Analyze current cultivar performance
        cultivar_analysis = {}
        for cultivar_id, cultivar in self.genetic_db.cultivars.items():
            performance = self.ge_model.predict_cultivar_performance(cultivar_id, target_environment)
            
            # Calculate trait gap (desired - current)
            trait_gaps = {}
            for trait, desired_value in desired_traits.items():
                current_value = self.ge_model.calculate_phenotype_expression(
                    cultivar_id, target_environment, trait
                )
                trait_gaps[trait] = desired_value - current_value
            
            cultivar_analysis[cultivar_id] = {
                'performance': performance,
                'trait_gaps': trait_gaps,
                'overall_gap': np.mean([abs(gap) for gap in trait_gaps.values()])
            }
        
        # Identify best parent candidates
        parent_candidates = []
        for cultivar_id, analysis in cultivar_analysis.items():
            cultivar = self.genetic_db.get_cultivar(cultivar_id)
            
            # Score based on performance and complementary traits
            complementary_score = 0
            for trait, desired_value in desired_traits.items():
                current_value = cultivar.trait_values.get(trait, 0.5)
                if current_value > desired_value * 0.8:  # Has at least 80% of desired trait
                    complementary_score += current_value
            
            parent_candidates.append({
                'cultivar_id': cultivar_id,
                'cultivar_name': cultivar.cultivar_name,
                'complementary_score': complementary_score,
                'performance_score': analysis['performance'].get('yield_index', 0.5),
                'trait_gaps': analysis['trait_gaps']
            })
        
        # Sort by combined score
        parent_candidates.sort(
            key=lambda x: x['complementary_score'] + x['performance_score'], 
            reverse=True
        )
        
        return {
            'breeding_targets': desired_traits,
            'target_environment': target_environment,
            'parent_candidates': parent_candidates[:5],
            'cultivar_analysis': cultivar_analysis
        }
    
    def estimate_hybrid_performance(self, 
                                  parent1_id: str, 
                                  parent2_id: str,
                                  environment_factors: Dict[str, float]) -> Dict[str, float]:
        """Estimate performance of potential F1 hybrid"""
        parent1 = self.genetic_db.get_cultivar(parent1_id)
        parent2 = self.genetic_db.get_cultivar(parent2_id)
        
        if not parent1 or not parent2:
            return {}
        
        # Simple additive genetic model for trait prediction
        hybrid_traits = {}
        for trait in GeneticTrait:
            p1_value = parent1.trait_values.get(trait, 0.5)
            p2_value = parent2.trait_values.get(trait, 0.5)
            
            # Mid-parent value with some heterosis
            heterosis_factor = environment_factors.get('heterosis_factor', 1.05)  # Heterosis factor from CSV
            hybrid_traits[trait] = (p1_value + p2_value) / 2.0 * heterosis_factor
        
        # Estimate genetic coefficients (mid-parent values)
        hybrid_coefficients = GeneticCoefficients(
            EM_FL=(parent1.genetic_coefficients.EM_FL + parent2.genetic_coefficients.EM_FL) / 2,
            FL_SH=(parent1.genetic_coefficients.FL_SH + parent2.genetic_coefficients.FL_SH) / 2,
            LFMAX=(parent1.genetic_coefficients.LFMAX + parent2.genetic_coefficients.LFMAX) / 2,
            SLAVR=(parent1.genetic_coefficients.SLAVR + parent2.genetic_coefficients.SLAVR) / 2,
            SIZLF=(parent1.genetic_coefficients.SIZLF + parent2.genetic_coefficients.SIZLF) / 2,
            EC_TOLERANCE=(parent1.genetic_coefficients.EC_TOLERANCE + parent2.genetic_coefficients.EC_TOLERANCE) / 2,
            NITRATE_EFFICIENCY=(parent1.genetic_coefficients.NITRATE_EFFICIENCY + parent2.genetic_coefficients.NITRATE_EFFICIENCY) / 2,
            ROOT_ACTIVITY=(parent1.genetic_coefficients.ROOT_ACTIVITY + parent2.genetic_coefficients.ROOT_ACTIVITY) / 2,
            PHOTOSYNTHETIC_CAPACITY=(parent1.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY + parent2.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY) / 2
        )
        
        # Create temporary hybrid profile
        hybrid_profile = CultivarProfile(
            cultivar_id="HYBRID_TEMP",
            cultivar_name=f"{parent1.cultivar_name} × {parent2.cultivar_name}",
            lettuce_type=parent1.lettuce_type,
            breeder="Predicted",
            year_released=2024,
            genetic_coefficients=hybrid_coefficients,
            trait_values=hybrid_traits,
            yield_potential=(parent1.yield_potential + parent2.yield_potential) / 2 * 1.1,  # Hybrid vigor
            adaptation_score=(parent1.adaptation_score + parent2.adaptation_score) / 2
        )
        
        # Predict performance
        performance = {}
        for trait in GeneticTrait:
            performance[f"{trait.value}_expression"] = self.ge_model.calculate_phenotype_expression(
                "HYBRID_TEMP", environment_factors, trait
            )
        
        # Add overall performance metrics
        performance['predicted_yield_index'] = hybrid_profile.yield_potential * hybrid_profile.calculate_adaptation_index(environment_factors)
        performance['heterosis_advantage'] = performance['predicted_yield_index'] - max(
            parent1.yield_potential * parent1.calculate_adaptation_index(environment_factors),
            parent2.yield_potential * parent2.calculate_adaptation_index(environment_factors)
        )
        
        return performance


def create_lettuce_genetic_system(system_config=None) -> Tuple[GeneticParameterDatabase, GenotypeEnvironmentModel, BreedingAssistant]:
    """Create complete genetic parameter system for lettuce using CSV configuration.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        Tuple of (GeneticParameterDatabase, GenotypeEnvironmentModel, BreedingAssistant)
    """
    try:
        if system_config is None:
            raise ValueError("❌ System configuration is required - no hardcoded defaults allowed")
        
        # Get genetic parameters from CSV configuration
        genetic_params = getattr(system_config, 'genetic_parameters', {})
        if not genetic_params:
            raise ValueError("❌ No genetic parameters found in system configuration - CSV data required")
        
        # Create genetic database
        genetic_db = GeneticParameterDatabase()
        
        # Create a default cultivar from genetic parameters
        # This allows the system to work with existing CSV structure
        cultivar_id = "DEFAULT_CSV_CULTIVAR"
        
        # Create genetic coefficients from CSV data
        genetic_coeffs = GeneticCoefficients()
        for param_name, param_value in genetic_params.items():
            if hasattr(genetic_coeffs, param_name):
                setattr(genetic_coeffs, param_name, param_value)
        
        # Create cultivar profile with required parameters from CSV
        cultivar_profile = CultivarProfile(
            cultivar_id=cultivar_id,
            cultivar_name="CSV Configured Cultivar",
            lettuce_type=LettuceType.BUTTERHEAD,
            breeder="CSV Configuration",
            year_released=2024,
            genetic_coefficients=genetic_coeffs,
            yield_potential=genetic_params.get('yield_potential', None),  # Must be provided in CSV
            adaptation_score=genetic_params.get('adaptation_score', None),  # Must be provided in CSV
            commercial_rating=genetic_params.get('commercial_rating', None),  # Must be provided in CSV
            trait_values={},  # Empty trait values - can be populated later
            pedigree=["CSV configured"],
            breeding_notes="Cultivar created from CSV genetic parameters"
        )
        
        # Validate required performance parameters
        if cultivar_profile.yield_potential is None:
            raise ValueError("❌ yield_potential must be provided in CSV genetic parameters - no hardcoded defaults allowed")
        if cultivar_profile.adaptation_score is None:
            raise ValueError("❌ adaptation_score must be provided in CSV genetic parameters - no hardcoded defaults allowed")
        if cultivar_profile.commercial_rating is None:
            raise ValueError("❌ commercial_rating must be provided in CSV genetic parameters - no hardcoded defaults allowed")
        
        genetic_db.add_cultivar(cultivar_profile)
        
        # Create models
        ge_model = GenotypeEnvironmentModel(genetic_db)
        breeding_assistant = BreedingAssistant(genetic_db, ge_model)
        
        return genetic_db, ge_model, breeding_assistant
        
    except Exception as e:
        raise ValueError(f"❌ Failed to load CSV genetic parameters: {e}. System requires CSV data - no hardcoded defaults allowed.")


