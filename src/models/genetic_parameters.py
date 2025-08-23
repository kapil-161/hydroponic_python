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
# Import centralized JSON config via config_loader
from ..utils.config_loader import get_config_loader


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
    EM_FL: float = 30.0      # Days from emergence to first flower (GDD)
    FL_SH: float = 15.0      # Days from first flower to first seed (GDD)  
    FL_SD: float = 25.0      # Days from first flower to first pod (GDD)
    SD_PM: float = 35.0      # Days from first seed to physiological maturity (GDD)
    FL_LF: float = 10.0      # Days from first flower to end of leaf expansion (GDD)
    
    # Temperature response parameters
    LFMAX: float = 1.2       # Maximum leaf photosynthesis rate (mg CO2/m²/s)
    SLAVR: float = 180.0     # Specific leaf area of cultivar under standard growth conditions (cm²/g)
    SIZLF: float = 25.0      # Maximum size of full leaf (three leaflets) (cm²)
    XFRT: float = 1.0        # Maximum fraction of daily growth that is partitioned to reproductive growth
    WTPSD: float = 0.15      # Maximum weight per seed (g)
    SFDUR: float = 20.0      # Seed filling duration for cultivar (GDD)
    SDPDV: float = 2.5       # Average seed per pod under standard growing conditions
    PODUR: float = 8.0       # Time required for cultivar to reach final pod load (GDD)
    
    # Stress tolerance coefficients
    THRSH: float = 78.0      # The maximum ratio of seed/(seed+shell) at maturity
    SDPRO: float = 0.40      # Fraction protein in seeds
    SDLIP: float = 0.20      # Fraction oil in seeds
    
    # Hydroponic-specific parameters
    EC_TOLERANCE: float = 1.3    # Maximum EC tolerance (dS/m)
    NITRATE_EFFICIENCY: float = 0.85  # Nitrogen use efficiency factor
    ROOT_ACTIVITY: float = 1.5   # Root activity coefficient
    PHOTOSYNTHETIC_CAPACITY: float = 2.0  # Relative photosynthetic capacity


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
    
    # Trait values (0.0-1.0 scale, 1.0 = excellent)
    trait_values: Dict[GeneticTrait, float] = field(default_factory=dict)
    
    # Performance characteristics
    yield_potential: float = 1.0      # Relative yield potential
    adaptation_score: float = 1.0     # Environmental adaptation score
    commercial_rating: float = 1.0    # Commercial viability rating
    
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
            genetics_cfg = get_config_loader().get_genetics_parameters()
            weight = genetics_cfg.get('HEAT_STRESS_WEIGHT', 0.3)
            stress_adjustments += temp_stress * (1.0 - heat_tolerance) * weight
        else:  # Cold stress
            genetics_cfg = get_config_loader().get_genetics_parameters()
            weight = genetics_cfg.get('COLD_STRESS_WEIGHT', 0.25)
            stress_adjustments += abs(temp_stress) * (1.0 - cold_tolerance) * weight
        
        # Salinity stress
        salinity_stress = environment_factors.get('salinity_stress', 0.0)
        salinity_tolerance = self.trait_values.get(GeneticTrait.SALINITY_TOLERANCE, 0.5)
        genetics_cfg = get_config_loader().get_genetics_parameters()
        stress_adjustments += salinity_stress * (1.0 - salinity_tolerance) * genetics_cfg.get('SALINITY_STRESS_WEIGHT', 0.2)
        
        # Light stress
        light_stress = environment_factors.get('light_stress', 0.0)
        stress_adjustments += light_stress * genetics_cfg.get('LIGHT_STRESS_WEIGHT', 0.15)
        
        # Nutrient stress
        nutrient_stress = environment_factors.get('nutrient_stress', 0.0)
        nitrate_efficiency = self.genetic_coefficients.NITRATE_EFFICIENCY
        stress_adjustments += nutrient_stress * (1.0 - nitrate_efficiency) * genetics_cfg.get('NUTRIENT_STRESS_WEIGHT', 0.25)
        
        # Calculate final adaptation index
        adaptation_index = base_adaptation - stress_adjustments
        return max(0.1, min(1.0, adaptation_index))


class GeneticParameterDatabase:
    """Database of lettuce cultivar genetic parameters"""
    
    def __init__(self):
        self.cultivars: Dict[str, CultivarProfile] = {}
        self.initialize_cultivar_database()
    
    def initialize_cultivar_database(self):
        """Initialize database with common lettuce cultivars"""
        
        # Butterhead cultivars
        self.add_cultivar(CultivarProfile(
            cultivar_id="BUTT_001",
            cultivar_name="Buttercrunch",
            lettuce_type=LettuceType.BUTTERHEAD,
            breeder="Burpee Seeds",
            year_released=1963,
            genetic_coefficients=GeneticCoefficients(
                EM_FL=32.0, FL_SH=18.0, FL_SD=28.0, SD_PM=40.0,
                LFMAX=1.1, SLAVR=175.0, SIZLF=22.0,
                EC_TOLERANCE=1.2, NITRATE_EFFICIENCY=0.82,
                ROOT_ACTIVITY=0.95, PHOTOSYNTHETIC_CAPACITY=0.95
            ),
            trait_values={
                GeneticTrait.DAYS_TO_EMERGENCE: 0.8,
                GeneticTrait.DAYS_TO_HARVEST: 0.7,
                GeneticTrait.BOLTING_TOLERANCE: 0.6,
                GeneticTrait.LEAF_SIZE: 0.8,
                GeneticTrait.YIELD_POTENTIAL: 0.85,
                GeneticTrait.CHLOROPHYLL_CONTENT: 0.7,
                GeneticTrait.HEAT_TOLERANCE: 0.5,
                GeneticTrait.COLD_TOLERANCE: 0.8,
                GeneticTrait.SALINITY_TOLERANCE: 0.6,
                GeneticTrait.NITRATE_ACCUMULATION: 0.3  # Lower is better
            },
            yield_potential=0.85,
            adaptation_score=0.9,
            commercial_rating=0.9,
            pedigree=["Butterhead landrace selections"],
            breeding_notes="Classic butterhead, excellent for cool conditions"
        ))
        
        self.add_cultivar(CultivarProfile(
            cultivar_id="BUTT_002", 
            cultivar_name="Green Butter",
            lettuce_type=LettuceType.BUTTERHEAD,
            breeder="Johnny's Selected Seeds",
            year_released=2010,
            genetic_coefficients=GeneticCoefficients(
                EM_FL=28.0, FL_SH=16.0, FL_SD=26.0, SD_PM=38.0,
                LFMAX=1.25, SLAVR=185.0, SIZLF=26.0,
                EC_TOLERANCE=1.4, NITRATE_EFFICIENCY=0.88,
                ROOT_ACTIVITY=1.05, PHOTOSYNTHETIC_CAPACITY=1.02
            ),
            trait_values={
                GeneticTrait.DAYS_TO_EMERGENCE: 0.9,
                GeneticTrait.DAYS_TO_HARVEST: 0.8,
                GeneticTrait.BOLTING_TOLERANCE: 0.7,
                GeneticTrait.LEAF_SIZE: 0.9,
                GeneticTrait.YIELD_POTENTIAL: 0.95,
                GeneticTrait.CHLOROPHYLL_CONTENT: 0.8,
                GeneticTrait.HEAT_TOLERANCE: 0.7,
                GeneticTrait.COLD_TOLERANCE: 0.75,
                GeneticTrait.SALINITY_TOLERANCE: 0.7,
                GeneticTrait.NITRATE_ACCUMULATION: 0.2
            },
            yield_potential=0.95,
            adaptation_score=0.92,
            commercial_rating=0.95,
            breeding_notes="Improved hydroponic performance, heat tolerance"
        ))
        
        # Romaine cultivars
        self.add_cultivar(CultivarProfile(
            cultivar_id="ROM_001",
            cultivar_name="Parris Island Cos",
            lettuce_type=LettuceType.ROMAINE,
            breeder="Southern Exposure",
            year_released=1952,
            genetic_coefficients=GeneticCoefficients(
                EM_FL=35.0, FL_SH=20.0, FL_SD=30.0, SD_PM=45.0,
                LFMAX=1.3, SLAVR=160.0, SIZLF=35.0,
                EC_TOLERANCE=1.5, NITRATE_EFFICIENCY=0.90,
                ROOT_ACTIVITY=1.1, PHOTOSYNTHETIC_CAPACITY=1.1
            ),
            trait_values={
                GeneticTrait.DAYS_TO_EMERGENCE: 0.75,
                GeneticTrait.DAYS_TO_HARVEST: 0.6,
                GeneticTrait.BOLTING_TOLERANCE: 0.8,
                GeneticTrait.LEAF_SIZE: 1.0,
                GeneticTrait.CHLOROPHYLL_CONTENT: 0.9,
                GeneticTrait.VITAMIN_C_CONTENT: 0.95,
                GeneticTrait.HEAT_TOLERANCE: 0.8,
                GeneticTrait.COLD_TOLERANCE: 0.7,
                GeneticTrait.SALINITY_TOLERANCE: 0.8,
                GeneticTrait.NITRATE_ACCUMULATION: 0.15
            },
            yield_potential=1.0,
            adaptation_score=0.88,
            commercial_rating=0.85,
            breeding_notes="Heat tolerant, excellent nutritional profile"
        ))
        
        # Loose leaf cultivars
        self.add_cultivar(CultivarProfile(
            cultivar_id="LOOSE_001",
            cultivar_name="Black Seeded Simpson",
            lettuce_type=LettuceType.LOOSE_LEAF,
            breeder="Heirloom variety",
            year_released=1850,
            genetic_coefficients=GeneticCoefficients(
                EM_FL=25.0, FL_SH=14.0, FL_SD=22.0, SD_PM=32.0,
                LFMAX=1.15, SLAVR=195.0, SIZLF=18.0,
                EC_TOLERANCE=1.1, NITRATE_EFFICIENCY=0.80,
                ROOT_ACTIVITY=0.9, PHOTOSYNTHETIC_CAPACITY=0.98
            ),
            trait_values={
                GeneticTrait.DAYS_TO_EMERGENCE: 0.95,
                GeneticTrait.DAYS_TO_HARVEST: 0.9,
                GeneticTrait.BOLTING_TOLERANCE: 0.5,
                GeneticTrait.LEAF_SIZE: 0.6,
                GeneticTrait.CHLOROPHYLL_CONTENT: 0.6,
                GeneticTrait.HEAT_TOLERANCE: 0.4,
                GeneticTrait.COLD_TOLERANCE: 0.9,
                GeneticTrait.SALINITY_TOLERANCE: 0.5,
                GeneticTrait.NITRATE_ACCUMULATION: 0.4
            },
            yield_potential=0.75,
            adaptation_score=0.8,
            commercial_rating=0.7,
            breeding_notes="Fast growing, cool season variety"
        ))
        
        # Modern hydroponic cultivars
        self.add_cultivar(CultivarProfile(
            cultivar_id="HYDRO_001",
            cultivar_name="Salanova Green Butter",
            lettuce_type=LettuceType.BUTTERHEAD,
            breeder="Rijk Zwaan",
            year_released=2018,
            genetic_coefficients=GeneticCoefficients(
                EM_FL=26.0, FL_SH=15.0, FL_SD=24.0, SD_PM=35.0,
                LFMAX=1.35, SLAVR=190.0, SIZLF=28.0,
                EC_TOLERANCE=1.6, NITRATE_EFFICIENCY=0.92,
                ROOT_ACTIVITY=25.0, PHOTOSYNTHETIC_CAPACITY=6.0
            ),
            trait_values={
                GeneticTrait.DAYS_TO_EMERGENCE: 0.95,
                GeneticTrait.DAYS_TO_HARVEST: 0.9,
                GeneticTrait.BOLTING_TOLERANCE: 0.85,
                GeneticTrait.LEAF_SIZE: 0.85,
                GeneticTrait.CHLOROPHYLL_CONTENT: 0.9,
                GeneticTrait.HEAT_TOLERANCE: 0.8,
                GeneticTrait.COLD_TOLERANCE: 0.8,
                GeneticTrait.SALINITY_TOLERANCE: 0.85,
                GeneticTrait.NITRATE_ACCUMULATION: 0.1
            },
            yield_potential=1.1,
            adaptation_score=0.95,
            commercial_rating=1.0,
            breeding_notes="Optimized for hydroponic systems, multi-harvest"
        ))
        
        self.add_cultivar(CultivarProfile(
            cultivar_id="HYDRO_002",
            cultivar_name="Rex Butterhead",
            lettuce_type=LettuceType.BUTTERHEAD,
            breeder="Rijk Zwaan", 
            year_released=2020,
            genetic_coefficients=GeneticCoefficients(
                EM_FL=24.0, FL_SH=14.0, FL_SD=23.0, SD_PM=33.0,
                LFMAX=1.4, SLAVR=195.0, SIZLF=30.0,
                EC_TOLERANCE=1.7, NITRATE_EFFICIENCY=0.94,
                ROOT_ACTIVITY=1.2, PHOTOSYNTHETIC_CAPACITY=1.12
            ),
            trait_values={
                GeneticTrait.DAYS_TO_EMERGENCE: 0.98,
                GeneticTrait.DAYS_TO_HARVEST: 0.95,
                GeneticTrait.BOLTING_TOLERANCE: 0.9,
                GeneticTrait.LEAF_SIZE: 0.9,
                GeneticTrait.CHLOROPHYLL_CONTENT: 0.95,
                GeneticTrait.HEAT_TOLERANCE: 0.85,
                GeneticTrait.COLD_TOLERANCE: 0.8,
                GeneticTrait.SALINITY_TOLERANCE: 0.9,
                GeneticTrait.NITRATE_ACCUMULATION: 0.05
            },
            yield_potential=1.15,
            adaptation_score=0.98,
            commercial_rating=1.0,
            breeding_notes="Latest generation hydroponic variety, premium quality"
        ))
    
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
            genetics_cfg = get_config_loader().get_genetics_parameters()
            overall_score = (
                adaptation_score * genetics_cfg.get('ADAPTATION_SCORE_WEIGHT', 0.6)
                + cultivar.yield_potential * genetics_cfg.get('YIELD_POTENTIAL_BREEDING_WEIGHT', 0.25)
                + cultivar.commercial_rating * genetics_cfg.get('COMMERCIAL_RATING_WEIGHT', 0.15)
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
            return 0.5  # Default value
        
        base_trait_value = cultivar.trait_values.get(trait, 0.5)
        
        # Environmental modulation of trait expression
        if trait == GeneticTrait.HEAT_TOLERANCE:
            temp_stress = environment_factors.get('temperature_stress', 0.0)
            if temp_stress > 0:  # Heat stress present
                weight = get_config_loader().get_genetics_parameters().get('TEMPERATURE_STRESS_WEIGHT', 0.5)
                expression = base_trait_value * (1.0 - temp_stress * weight)
            else:
                expression = base_trait_value
        
        elif trait == GeneticTrait.COLD_TOLERANCE:
            temp_stress = environment_factors.get('temperature_stress', 0.0)
            if temp_stress < 0:  # Cold stress present
                weight = get_config_loader().get_genetics_parameters().get('TEMPERATURE_STRESS_WEIGHT', 0.5)
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
            expression = base_trait_value + nitrogen_excess * get_config_loader().get_genetics_parameters().get('NITROGEN_EXCESS_WEIGHT', 0.3)
            
        elif trait == GeneticTrait.ROOT_DEVELOPMENT:
            water_stress = environment_factors.get('water_stress', 0.0)
            nutrient_stress = environment_factors.get('nutrient_stress', 0.0)
            # Root development increases under stress
            stress_response = max(water_stress, nutrient_stress) * get_config_loader().get_genetics_parameters().get('STRESS_RESPONSE_WEIGHT', 0.2)
            expression = base_trait_value + stress_response
            
        else:
            # Default environmental modulation
            overall_stress = np.mean([abs(v) for v in environment_factors.values() if isinstance(v, (int, float))])
            expression = base_trait_value * (1.0 - overall_stress * get_config_loader().get_genetics_parameters().get('OVERALL_STRESS_WEIGHT', 0.1))
        
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
        
        # Aggregate performance metrics
        performance_metrics['yield_index'] = (
            trait_expressions[GeneticTrait.LEAF_SIZE] * 0.3 +
            trait_expressions[GeneticTrait.CHLOROPHYLL_CONTENT] * 0.2 +
            (1.0 - trait_expressions[GeneticTrait.NITRATE_ACCUMULATION]) * 0.2 +
            trait_expressions[GeneticTrait.ROOT_DEVELOPMENT] * 0.15 +
            cultivar.yield_potential * 0.15
        )
        
        performance_metrics['quality_index'] = (
            trait_expressions[GeneticTrait.VITAMIN_C_CONTENT] * 0.3 +
            trait_expressions[GeneticTrait.CAROTENOID_CONTENT] * 0.25 +
            (1.0 - trait_expressions[GeneticTrait.NITRATE_ACCUMULATION]) * 0.25 +
            trait_expressions[GeneticTrait.CHLOROPHYLL_CONTENT] * 0.2
        )
        
        performance_metrics['stress_tolerance'] = (
            trait_expressions[GeneticTrait.HEAT_TOLERANCE] * 0.3 +
            trait_expressions[GeneticTrait.COLD_TOLERANCE] * 0.25 +
            trait_expressions[GeneticTrait.SALINITY_TOLERANCE] * 0.25 +
            trait_expressions[GeneticTrait.DISEASE_RESISTANCE] * 0.2
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
            heterosis_factor = 1.05  # 5% heterosis
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


def create_lettuce_genetic_system() -> Tuple[GeneticParameterDatabase, GenotypeEnvironmentModel, BreedingAssistant]:
    """Create complete genetic parameter system for lettuce"""
    genetic_db = GeneticParameterDatabase()
    ge_model = GenotypeEnvironmentModel(genetic_db)
    breeding_assistant = BreedingAssistant(genetic_db, ge_model)
    
    return genetic_db, ge_model, breeding_assistant


if __name__ == "__main__":
    # Demonstration of genetic parameter system
    print("Advanced Genetic Parameters System - Lettuce Cultivar Modeling")
    print("=" * 80)
    
    # Create system
    genetic_db, ge_model, breeding_assistant = create_lettuce_genetic_system()
    
    print(f"Loaded {len(genetic_db.cultivars)} lettuce cultivars:")
    for cultivar_id, cultivar in genetic_db.cultivars.items():
        print(f"  {cultivar_id}: {cultivar.cultivar_name} ({cultivar.lettuce_type.value})")
    
    # Test environmental conditions
    print(f"\nTesting G×E interactions:")
    
    # High temperature environment
    hot_environment = {
        'temperature_stress': 0.4,  # Moderate heat stress
        'light_intensity': 1.2,    # High light
        'nitrogen_status': 0.9,    # Good nutrition
        'salinity_stress': 0.2     # Slight salinity
    }
    
    print(f"\nHot Environment Adaptation:")
    best_cultivars = genetic_db.get_best_cultivars_for_conditions(hot_environment, top_n=3)
    for cultivar_id, score in best_cultivars:
        cultivar = genetic_db.get_cultivar(cultivar_id)
        performance = ge_model.predict_cultivar_performance(cultivar_id, hot_environment)
        print(f"  {cultivar.cultivar_name}: Score={score:.3f}, "
              f"Yield Index={performance['yield_index']:.3f}, "
              f"Heat Tolerance={performance['stress_tolerance']:.3f}")
    
    # Breeding target analysis
    print(f"\nBreeding Target Analysis:")
    desired_traits = {
        GeneticTrait.HEAT_TOLERANCE: 0.9,
        GeneticTrait.YIELD_POTENTIAL: 0.95,
        GeneticTrait.NITRATE_ACCUMULATION: 0.05,  # Lower is better
        GeneticTrait.BOLTING_TOLERANCE: 0.85
    }
    
    breeding_targets = breeding_assistant.identify_breeding_targets(hot_environment, desired_traits)
    print(f"Top parent candidates:")
    for candidate in breeding_targets['parent_candidates'][:3]:
        print(f"  {candidate['cultivar_name']}: "
              f"Score={candidate['complementary_score'] + candidate['performance_score']:.2f}")
    
    # Hybrid prediction
    print(f"\nHybrid Performance Prediction:")
    if len(breeding_targets['parent_candidates']) >= 2:
        parent1_id = breeding_targets['parent_candidates'][0]['cultivar_id']
        parent2_id = breeding_targets['parent_candidates'][1]['cultivar_id']
        
        hybrid_performance = breeding_assistant.estimate_hybrid_performance(
            parent1_id, parent2_id, hot_environment
        )
        
        parent1 = genetic_db.get_cultivar(parent1_id)
        parent2 = genetic_db.get_cultivar(parent2_id)
        
        print(f"  Cross: {parent1.cultivar_name} × {parent2.cultivar_name}")
        print(f"  Predicted yield index: {hybrid_performance['predicted_yield_index']:.3f}")
        print(f"  Heterosis advantage: {hybrid_performance['heterosis_advantage']:.3f}")
        print(f"  Heat tolerance: {hybrid_performance['heat_tolerance_expression']:.3f}")
    
    print(f"\n🧬 Genetic Parameter System Ready!")
    print(f"Advanced cultivar selection and breeding tools available.")