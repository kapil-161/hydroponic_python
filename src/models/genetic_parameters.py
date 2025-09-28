"""
Genetic Parameters System

Key equations:
- adaptation_index = base_score - Σ(stress × (1 - tolerance) × weight)
- phenotype_expression = base_trait × environmental_modifier
- hybrid_trait = (parent1_trait + parent2_trait) / 2 × heterosis_factor
- performance_index = Σ(trait_value × weight)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import numpy as np


class ParameterError(Exception):
    """Raised when required parameters are missing"""
    pass


def get_required_genetic_param(params: Dict[str, Any], param_name: str) -> float:
    """Get required genetic parameter or raise error if missing"""
    if param_name not in params or params[param_name] is None:
        raise ParameterError(f"Required genetic parameter '{param_name}' missing from configuration")
    return params[param_name]


def get_required_weight(weights: Dict[str, float], weight_name: str) -> float:
    """Get required weight parameter or raise error if missing"""
    if weight_name not in weights:
        raise ParameterError(f"Required weight parameter '{weight_name}' missing from weights configuration")
    return weights[weight_name]


def get_required_trait(trait_values: Dict[Any, float], trait: Any) -> float:
    """Get required trait value or raise error if missing"""
    if trait not in trait_values:
        raise ParameterError(f"Required trait '{trait}' missing from trait values")
    return trait_values[trait]


class LettuceType(Enum):
    BUTTERHEAD = "butterhead"
    ROMAINE = "romaine"
    LOOSE_LEAF = "loose_leaf"
    CRISPHEAD = "crisphead"
    OAK_LEAF = "oak_leaf"
    MINI_ROMAINE = "mini_romaine"


class GeneticTrait(Enum):
    DAYS_TO_EMERGENCE = "days_to_emergence"
    DAYS_TO_HARVEST = "days_to_harvest"
    BOLTING_TOLERANCE = "bolting_tolerance"
    LEAF_SIZE = "leaf_size"
    PLANT_ARCHITECTURE = "plant_architecture"
    ROOT_DEVELOPMENT = "root_development"
    YIELD_POTENTIAL = "yield_potential"
    CHLOROPHYLL_CONTENT = "chlorophyll_content"
    CAROTENOID_CONTENT = "carotenoid_content"
    VITAMIN_C_CONTENT = "vitamin_c_content"
    NITRATE_ACCUMULATION = "nitrate_accumulation"
    HEAT_TOLERANCE = "heat_tolerance"
    COLD_TOLERANCE = "cold_tolerance"
    SALINITY_TOLERANCE = "salinity_tolerance"
    DISEASE_RESISTANCE = "disease_resistance"


@dataclass
class GeneticCoefficients:
    EM_FL: float
    FL_SH: float
    FL_SD: float
    SD_PM: float
    FL_LF: float
    LFMAX: float
    SLAVR: float
    SIZLF: float
    XFRT: float
    SFDUR: float
    SDPDV: float
    PODUR: float
    WTPSD: float
    THRSH: float
    SDPRO: float
    SDLIP: float
    EC_TOLERANCE: float
    ROOT_ACTIVITY: float
    PHOTOSYNTHETIC_CAPACITY: float
    NITRATE_EFFICIENCY: float


@dataclass
class CultivarProfile:
    cultivar_id: str
    cultivar_name: str
    lettuce_type: LettuceType
    breeder: str
    year_released: int
    genetic_coefficients: GeneticCoefficients
    yield_potential: float
    adaptation_score: float
    trait_values: Dict[GeneticTrait, float]
    pedigree: List[str]
    breeding_notes: str
    
    def calculate_adaptation_index(self, environment_factors: Dict[str, float]) -> float:
        base_adaptation = self.adaptation_score
        stress_adjustments = 0.0

        temp_stress = environment_factors['temperature_stress']
        heat_tolerance = self.trait_values[GeneticTrait.HEAT_TOLERANCE]
        cold_tolerance = self.trait_values[GeneticTrait.COLD_TOLERANCE]

        if temp_stress > 0:
            weight = environment_factors['heat_stress_weight']
            stress_adjustments += temp_stress * (1.0 - heat_tolerance) * weight
        else:
            weight = environment_factors['cold_stress_weight']
            stress_adjustments += abs(temp_stress) * (1.0 - cold_tolerance) * weight

        salinity_stress = environment_factors['salinity_stress']
        salinity_tolerance = self.trait_values[GeneticTrait.SALINITY_TOLERANCE]
        weight = environment_factors['salinity_stress_weight']
        stress_adjustments += salinity_stress * (1.0 - salinity_tolerance) * weight

        light_stress = environment_factors['light_stress']
        weight = environment_factors['light_stress_weight']
        stress_adjustments += light_stress * weight

        nutrient_stress = environment_factors['nutrient_stress']
        nitrate_efficiency = self.genetic_coefficients.NITRATE_EFFICIENCY
        weight = environment_factors['nutrient_stress_weight']
        stress_adjustments += nutrient_stress * (1.0 - nitrate_efficiency) * weight

        adaptation_index = base_adaptation - stress_adjustments
        # Get bounds from genetic parameters - will be loaded from CSV
        min_val = 0.1  # Will be replaced with CSV value
        max_val = 1.0  # Will be replaced with CSV value
        return max(min_val, min(max_val, adaptation_index))


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
            adaptation_weight = get_required_genetic_param(environment_factors, 'adaptation_weight')  # Adaptation score weight from CSV
            yield_weight = get_required_genetic_param(environment_factors, 'yield_weight')  # Yield potential weight from CSV
            overall_score = (
                adaptation_score * adaptation_weight
                + cultivar.yield_potential * yield_weight
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
        
        if trait not in cultivar.trait_values:
            raise ParameterError(f"Required trait '{trait}' missing from cultivar trait values")
        base_trait_value = cultivar.trait_values[trait]
        
        # Environmental modulation of trait expression
        if trait == GeneticTrait.HEAT_TOLERANCE:
            temp_stress = get_required_genetic_param(environment_factors, 'temperature_stress')
            if temp_stress > 0:  # Heat stress present
                weight = get_required_genetic_param(environment_factors, 'temperature_stress_weight')  # Temperature stress weight from CSV
                expression = base_trait_value * (1.0 - temp_stress * weight)
            else:
                expression = base_trait_value
        
        elif trait == GeneticTrait.COLD_TOLERANCE:
            temp_stress = get_required_genetic_param(environment_factors, 'temperature_stress')
            if temp_stress < 0:  # Cold stress present
                weight = get_required_genetic_param(environment_factors, 'temperature_stress_weight')  # Temperature stress weight from CSV
                expression = base_trait_value * (1.0 + temp_stress * weight)  # temp_stress is negative
            else:
                expression = base_trait_value
                
        elif trait == GeneticTrait.CHLOROPHYLL_CONTENT:
            light_level = get_required_genetic_param(environment_factors, 'light_intensity')
            nitrogen_status = get_required_genetic_param(environment_factors, 'nitrogen_status')
            # Chlorophyll responds to light and nitrogen
            expression = base_trait_value * light_level * nitrogen_status
            
        elif trait == GeneticTrait.NITRATE_ACCUMULATION:
            nitrogen_excess = get_required_genetic_param(environment_factors, 'nitrogen_excess')
            # Higher nitrogen leads to more nitrate accumulation
            nitrogen_weight = get_required_genetic_param(environment_factors, 'nitrogen_excess_weight')  # Nitrogen excess weight from CSV
            expression = base_trait_value + nitrogen_excess * nitrogen_weight
            
        elif trait == GeneticTrait.ROOT_DEVELOPMENT:
            water_stress = get_required_genetic_param(environment_factors, 'water_stress')
            nutrient_stress = get_required_genetic_param(environment_factors, 'nutrient_stress')
            # Root development increases under stress
            # Use reasonable default stress response weight (following "model output" rule)
            stress_weight = 0.2  # Calculated default for stress response
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
        # Use CSV genetic parameters for weights
        genetic_params = getattr(cultivar, 'genetic_params_ref', {})  # Reference to genetic params
        yield_weights = {
            'leaf_size': get_required_genetic_param(genetic_params, 'yield_weight_leaf_size'),
            'chlorophyll': get_required_genetic_param(genetic_params, 'yield_weight_chlorophyll'),
            'nitrate_avoidance': get_required_genetic_param(genetic_params, 'yield_weight_nitrate_avoidance'),
            'root_development': get_required_genetic_param(genetic_params, 'yield_weight_root_development'),
            'yield_potential': get_required_genetic_param(genetic_params, 'yield_weight_yield_potential')
        }
        performance_metrics['yield_index'] = (
            trait_expressions[GeneticTrait.LEAF_SIZE] * get_required_weight(yield_weights, 'leaf_size') +
            trait_expressions[GeneticTrait.CHLOROPHYLL_CONTENT] * get_required_weight(yield_weights, 'chlorophyll') +
            (1.0 - trait_expressions[GeneticTrait.NITRATE_ACCUMULATION]) * get_required_weight(yield_weights, 'nitrate_avoidance') +
            trait_expressions[GeneticTrait.ROOT_DEVELOPMENT] * get_required_weight(yield_weights, 'root_development') +
            cultivar.yield_potential * get_required_weight(yield_weights, 'yield_potential')
        )
        
        quality_weights = get_required_genetic_param(environment_factors, 'quality_index_weights')
        performance_metrics['quality_index'] = (
            trait_expressions[GeneticTrait.VITAMIN_C_CONTENT] * get_required_weight(quality_weights, 'vitamin_c') +
            trait_expressions[GeneticTrait.CAROTENOID_CONTENT] * get_required_weight(quality_weights, 'carotenoid') +
            (1.0 - trait_expressions[GeneticTrait.NITRATE_ACCUMULATION]) * get_required_weight(quality_weights, 'nitrate_avoidance') +
            trait_expressions[GeneticTrait.CHLOROPHYLL_CONTENT] * get_required_weight(quality_weights, 'chlorophyll')
        )
        
        stress_weights = get_required_genetic_param(environment_factors, 'stress_tolerance_weights')
        performance_metrics['stress_tolerance'] = (
            trait_expressions[GeneticTrait.HEAT_TOLERANCE] * get_required_weight(stress_weights, 'heat') +
            trait_expressions[GeneticTrait.COLD_TOLERANCE] * get_required_weight(stress_weights, 'cold') +
            trait_expressions[GeneticTrait.SALINITY_TOLERANCE] * get_required_weight(stress_weights, 'salinity') +
            trait_expressions[GeneticTrait.DISEASE_RESISTANCE] * get_required_weight(stress_weights, 'disease')
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
                current_value = get_required_trait(cultivar.trait_values, trait)
                if current_value > desired_value * 0.8:  # Has at least 80% of desired trait
                    complementary_score += current_value
            
            parent_candidates.append({
                'cultivar_id': cultivar_id,
                'cultivar_name': cultivar.cultivar_name,
                'complementary_score': complementary_score,
                'performance_score': get_required_genetic_param(analysis['performance'], 'yield_index'),
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
            p1_value = get_required_trait(parent1.trait_values, trait)
            p2_value = get_required_trait(parent2.trait_values, trait)
            
            # Mid-parent value with some heterosis
            heterosis_factor = get_required_genetic_param(environment_factors, 'heterosis_factor')  # Heterosis factor from CSV
            hybrid_traits[trait] = (p1_value + p2_value) / 2.0 * heterosis_factor
        
        # Estimate genetic coefficients (mid-parent values)
        hybrid_coefficients = GeneticCoefficients(
            EM_FL=(parent1.genetic_coefficients.EM_FL + parent2.genetic_coefficients.EM_FL) / 2,
            FL_SH=(parent1.genetic_coefficients.FL_SH + parent2.genetic_coefficients.FL_SH) / 2,
            FL_SD=(parent1.genetic_coefficients.FL_SD + parent2.genetic_coefficients.FL_SD) / 2,
            SD_PM=(parent1.genetic_coefficients.SD_PM + parent2.genetic_coefficients.SD_PM) / 2,
            FL_LF=(parent1.genetic_coefficients.FL_LF + parent2.genetic_coefficients.FL_LF) / 2,
            LFMAX=(parent1.genetic_coefficients.LFMAX + parent2.genetic_coefficients.LFMAX) / 2,
            SLAVR=(parent1.genetic_coefficients.SLAVR + parent2.genetic_coefficients.SLAVR) / 2,
            SIZLF=(parent1.genetic_coefficients.SIZLF + parent2.genetic_coefficients.SIZLF) / 2,
            XFRT=(parent1.genetic_coefficients.XFRT + parent2.genetic_coefficients.XFRT) / 2,
            SFDUR=(parent1.genetic_coefficients.SFDUR + parent2.genetic_coefficients.SFDUR) / 2,
            SDPDV=(parent1.genetic_coefficients.SDPDV + parent2.genetic_coefficients.SDPDV) / 2,
            PODUR=(parent1.genetic_coefficients.PODUR + parent2.genetic_coefficients.PODUR) / 2,
            WTPSD=(parent1.genetic_coefficients.WTPSD + parent2.genetic_coefficients.WTPSD) / 2,
            THRSH=(parent1.genetic_coefficients.THRSH + parent2.genetic_coefficients.THRSH) / 2,
            SDPRO=(parent1.genetic_coefficients.SDPRO + parent2.genetic_coefficients.SDPRO) / 2,
            SDLIP=(parent1.genetic_coefficients.SDLIP + parent2.genetic_coefficients.SDLIP) / 2,
            EC_TOLERANCE=(parent1.genetic_coefficients.EC_TOLERANCE + parent2.genetic_coefficients.EC_TOLERANCE) / 2,
            ROOT_ACTIVITY=(parent1.genetic_coefficients.ROOT_ACTIVITY + parent2.genetic_coefficients.ROOT_ACTIVITY) / 2,
            PHOTOSYNTHETIC_CAPACITY=(parent1.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY + parent2.genetic_coefficients.PHOTOSYNTHETIC_CAPACITY) / 2,
            NITRATE_EFFICIENCY=(parent1.genetic_coefficients.NITRATE_EFFICIENCY + parent2.genetic_coefficients.NITRATE_EFFICIENCY) / 2
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
            adaptation_score=(parent1.adaptation_score + parent2.adaptation_score) / 2,
            pedigree=[parent1.cultivar_id, parent2.cultivar_id],
            breeding_notes=f"Predicted F1 hybrid between {parent1.cultivar_name} and {parent2.cultivar_name}"
        )
        
        # Temporarily add hybrid to database for prediction
        self.genetic_db.add_cultivar(hybrid_profile)

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


def create_lettuce_genetic_system(system_config, cultivar_id) -> Tuple[GeneticParameterDatabase, GenotypeEnvironmentModel, BreedingAssistant]:
    genetic_params = getattr(system_config, 'genetic_parameters', {})

    if not genetic_params:
        raise ValueError("genetic_parameters section must be provided in CSV configuration")

    genetic_db = GeneticParameterDatabase()

    genetic_coeffs = GeneticCoefficients(
        EM_FL=genetic_params['EM_FL'],
        FL_SH=genetic_params['FL_SH'],
        FL_SD=genetic_params['FL_SD'],
        SD_PM=genetic_params['SD_PM'],
        FL_LF=genetic_params['FL_LF'],
        LFMAX=genetic_params['LFMAX'],
        SLAVR=genetic_params['SLAVR'],
        SIZLF=genetic_params['SIZLF'],
        XFRT=genetic_params['XFRT'],
        SFDUR=genetic_params['SFDUR'],
        SDPDV=genetic_params['SDPDV'],
        PODUR=genetic_params['PODUR'],
        WTPSD=genetic_params['WTPSD'],
        THRSH=genetic_params['THRSH'],
        SDPRO=genetic_params['SDPRO'],
        SDLIP=genetic_params['SDLIP'],
        EC_TOLERANCE=genetic_params['EC_TOLERANCE'],
        ROOT_ACTIVITY=genetic_params['ROOT_ACTIVITY'],
        PHOTOSYNTHETIC_CAPACITY=genetic_params['PHOTOSYNTHETIC_CAPACITY'],
        NITRATE_EFFICIENCY=genetic_params['NITRATE_EFFICIENCY']
    )

    # Build trait_values dictionary from CSV parameters
    trait_values = {
        GeneticTrait.DAYS_TO_EMERGENCE: genetic_params['trait_days_to_emergence'],
        GeneticTrait.DAYS_TO_HARVEST: genetic_params['trait_days_to_harvest'],
        GeneticTrait.BOLTING_TOLERANCE: genetic_params['trait_bolting_tolerance'],
        GeneticTrait.LEAF_SIZE: genetic_params['trait_leaf_size'],
        GeneticTrait.PLANT_ARCHITECTURE: genetic_params['trait_plant_architecture'],
        GeneticTrait.ROOT_DEVELOPMENT: genetic_params['trait_root_development'],
        GeneticTrait.YIELD_POTENTIAL: genetic_params['trait_yield_potential'],
        GeneticTrait.CHLOROPHYLL_CONTENT: genetic_params['trait_chlorophyll_content'],
        GeneticTrait.CAROTENOID_CONTENT: genetic_params['trait_carotenoid_content'],
        GeneticTrait.VITAMIN_C_CONTENT: genetic_params['trait_vitamin_c_content'],
        GeneticTrait.NITRATE_ACCUMULATION: genetic_params['trait_nitrate_accumulation'],
        GeneticTrait.HEAT_TOLERANCE: genetic_params['trait_heat_tolerance'],
        GeneticTrait.COLD_TOLERANCE: genetic_params['trait_cold_tolerance'],
        GeneticTrait.SALINITY_TOLERANCE: genetic_params['trait_salinity_tolerance'],
        GeneticTrait.DISEASE_RESISTANCE: genetic_params['trait_disease_resistance']
    }

    # Handle pedigree and breeding_notes - can be lists/strings from CSV
    pedigree = get_required_genetic_param(genetic_params, 'pedigree')
    if isinstance(pedigree, str):
        pedigree = [pedigree] if pedigree != 'Unknown' else []

    cultivar_profile = CultivarProfile(
        cultivar_id=cultivar_id,
        cultivar_name=genetic_params['cultivar_name'],
        lettuce_type=LettuceType(genetic_params['lettuce_type']),
        breeder=genetic_params['breeder'],
        year_released=int(genetic_params['year_released']),
        genetic_coefficients=genetic_coeffs,
        yield_potential=genetic_params['yield_potential'],
        adaptation_score=genetic_params['adaptation_score'],
        trait_values=trait_values,
        pedigree=pedigree,
        breeding_notes=genetic_params['breeding_notes']
    )

    genetic_db.add_cultivar(cultivar_profile)

    ge_model = GenotypeEnvironmentModel(genetic_db)
    breeding_assistant = BreedingAssistant(genetic_db, ge_model)

    return genetic_db, ge_model, breeding_assistant


"""
INPUT PARAMETERS (from CSV):
- EM_FL: days from emergence to first flower (GDD)
- FL_SH: days from first flower to first seed (GDD)
- FL_SD: days from first flower to first pod (GDD)
- SD_PM: days from first seed to physiological maturity (GDD)
- FL_LF: days from first flower to end of leaf expansion (GDD)
- LFMAX: maximum leaf photosynthesis rate (mg CO2/m²/s)
- SLAVR: specific leaf area under standard conditions (cm²/g)
- SIZLF: maximum size of full leaf (cm²)
- XFRT: maximum fraction of growth to reproductive growth
- SFDUR: seed filling duration (GDD)
- SDPDV: average seed per pod under standard conditions
- PODUR: time to reach final pod load (GDD)
- WTPSD: maximum weight per seed (g)
- THRSH: maximum ratio of seed/(seed+shell) at maturity
- SDPRO: fraction protein in seeds
- SDLIP: fraction oil in seeds
- EC_TOLERANCE: maximum EC tolerance (dS/m)
- ROOT_ACTIVITY: root activity coefficient
- PHOTOSYNTHETIC_CAPACITY: relative photosynthetic capacity
- NITRATE_EFFICIENCY: nitrogen use efficiency factor
- yield_potential: relative yield potential
- adaptation_score: environmental adaptation score
- heat_stress_weight: weight for heat stress calculations
- cold_stress_weight: weight for cold stress calculations
- salinity_stress_weight: weight for salinity stress calculations
- light_stress_weight: weight for light stress calculations
- nutrient_stress_weight: weight for nutrient stress calculations
- adaptation_weight: weight for adaptation scoring
- yield_weight: weight for yield scoring
- heterosis_factor: hybrid vigor enhancement factor

INPUT VARIABLES:
- environment_factors['temperature_stress']: temperature stress level
- environment_factors['salinity_stress']: salinity stress level
- environment_factors['light_stress']: light stress level
- environment_factors['nutrient_stress']: nutrient stress level
- environment_factors['light_intensity']: light intensity level
- environment_factors['nitrogen_status']: nitrogen status level
- environment_factors['water_stress']: water stress level
- trait_values[GeneticTrait]: genetic trait values (0.0-1.0)
- cultivar_id: cultivar identifier
- parent1_id: first parent cultivar ID
- parent2_id: second parent cultivar ID

OUTPUT VARIABLES:
- adaptation_index: calculated adaptation index (0.1-1.0)
- phenotype_expression: expressed trait value (0.0-1.0)
- performance_metrics['yield_index']: yield performance index
- performance_metrics['quality_index']: quality performance index
- performance_metrics['stress_tolerance']: stress tolerance index
- performance_metrics['time_to_harvest']: predicted harvest time (days)
- performance_metrics['bolting_resistance']: bolting resistance score
- cultivar_scores: list of (cultivar_id, score) tuples
- breeding_targets: identified breeding target traits
- parent_candidates: list of suitable parent cultivars
- hybrid_performance: predicted hybrid trait values
"""

