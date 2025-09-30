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
    GROWTH_RATE = "growth_rate"


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
    genetic_coefficients: GeneticCoefficients
    yield_potential: float
    adaptation_score: float
    trait_values: Dict[GeneticTrait, float]
    maturity_days: int = 60  # Days to harvest maturity
    
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
    
    def __init__(self, config: Dict[str, Any] = None):
        self.cultivars: Dict[str, CultivarProfile] = {}
        
        # Load default parameters from CSV
        if config:
            self.default_air_temperature = float(config.get('default_air_temperature', 20.0))
            self.default_humidity = float(config.get('default_humidity', 60.0))
            self.default_light_intensity = float(config.get('default_light_intensity', 200.0))
            self.cache_timeout = float(config.get('cache_timeout', 1.0))
        else:
            raise ValueError("GeneticParameterDatabase requires configuration with default parameters")
        
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
    
    def initialize(self):
        """Initialize the genetic parameters model"""
        pass
        
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


# Breeding functionality removed as requested


def create_lettuce_genetic_system(system_config, cultivar_id) -> Tuple[GeneticParameterDatabase, GenotypeEnvironmentModel]:
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

    cultivar_profile = CultivarProfile(
        cultivar_id=cultivar_id,
        cultivar_name=genetic_params['cultivar_name'],
        lettuce_type=LettuceType(genetic_params['lettuce_type']),
        genetic_coefficients=genetic_coeffs,
        yield_potential=genetic_params['yield_potential'],
        adaptation_score=genetic_params['adaptation_score'],
        trait_values=trait_values
    )

    genetic_db.add_cultivar(cultivar_profile)

    ge_model = GenotypeEnvironmentModel(genetic_db)

    return genetic_db, ge_model


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

