"""
Canopy Architecture Model

Key equations:
- Light extinction: I = I₀ × e^(-k × LAI)
- Extinction coefficient: k = x / cos(zenith)
- Ground coverage: coverage = plant_area / available_area
- Temperature gradient: T = T_air - (gradient × position)
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import math


class LeafAngleDistribution(Enum):
    PLANOPHILE = "planophile"
    ERECTOPHILE = "erectophile"
    PLAGIOPHILE = "plagiophile"
    EXTREMOPHILE = "extremophile"
    SPHERICAL = "spherical"
    UNIFORM = "uniform"


@dataclass
class CanopyArchitectureParameters:
    number_of_layers: int
    max_lai: float
    extinction_coefficient: float
    diffuse_extinction_coeff: float
    beam_extinction_coeff: float
    row_spacing: float
    mean_leaf_angle: float
    canopy_width: float
    leaf_angle_distribution: str
    leaf_angle_variance: float
    plant_spacing: float
    plant_height: float
    leaf_reflectance: float
    leaf_transmittance: float
    leaf_absorptance: float
    self_shading_factor: float
    neighbor_shading_distance: float
    sunlit_fraction_method: str
    clumping_index: float
    max_extinction_coefficient: float
    upper_canopy_lai_factor: float
    middle_canopy_lai_factor: float
    lower_middle_canopy_lai_factor: float
    bottom_canopy_lai_factor: float
    shaded_light_fraction: float
    max_temperature_gradient: float
    temperature_gradient_factor: float
    ppfd_to_photosynthesis_factor: float
    
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'CanopyArchitectureParameters':
        required_params = [
            'number_of_layers', 'max_lai', 'extinction_coefficient', 'diffuse_extinction_coeff',
            'beam_extinction_coeff', 'leaf_angle_distribution', 'mean_leaf_angle', 'leaf_angle_variance',
            'row_spacing', 'plant_spacing', 'plant_height', 'canopy_width', 'leaf_reflectance',
            'leaf_transmittance', 'leaf_absorptance', 'self_shading_factor', 'neighbor_shading_distance',
            'sunlit_fraction_method', 'clumping_index', 'max_extinction_coefficient', 'upper_canopy_lai_factor',
            'middle_canopy_lai_factor', 'lower_middle_canopy_lai_factor', 'bottom_canopy_lai_factor',
            'shaded_light_fraction', 'max_temperature_gradient', 'temperature_gradient_factor',
            'ppfd_to_photosynthesis_factor'
        ]

        missing_params = [p for p in required_params if p not in config_dict]
        if missing_params:
            raise ValueError(f"Missing required canopy architecture parameters in CSV: {missing_params}")

        return cls(
            number_of_layers=int(config_dict['number_of_layers']),
            max_lai=float(config_dict['max_lai']),
            extinction_coefficient=float(config_dict['extinction_coefficient']),
            diffuse_extinction_coeff=float(config_dict['diffuse_extinction_coeff']),
            beam_extinction_coeff=float(config_dict['beam_extinction_coeff']),
            leaf_angle_distribution=config_dict['leaf_angle_distribution'],
            mean_leaf_angle=float(config_dict['mean_leaf_angle']),
            leaf_angle_variance=float(config_dict['leaf_angle_variance']),
            row_spacing=float(config_dict['row_spacing']),
            plant_spacing=float(config_dict['plant_spacing']),
            plant_height=float(config_dict['plant_height']),
            canopy_width=float(config_dict['canopy_width']),
            leaf_reflectance=float(config_dict['leaf_reflectance']),
            leaf_transmittance=float(config_dict['leaf_transmittance']),
            leaf_absorptance=float(config_dict['leaf_absorptance']),
            self_shading_factor=float(config_dict['self_shading_factor']),
            neighbor_shading_distance=float(config_dict['neighbor_shading_distance']),
            sunlit_fraction_method=config_dict['sunlit_fraction_method'],
            clumping_index=float(config_dict['clumping_index']),
            max_extinction_coefficient=float(config_dict['max_extinction_coefficient']),
            upper_canopy_lai_factor=float(config_dict['upper_canopy_lai_factor']),
            middle_canopy_lai_factor=float(config_dict['middle_canopy_lai_factor']),
            lower_middle_canopy_lai_factor=float(config_dict['lower_middle_canopy_lai_factor']),
            bottom_canopy_lai_factor=float(config_dict['bottom_canopy_lai_factor']),
            shaded_light_fraction=float(config_dict['shaded_light_fraction']),
            max_temperature_gradient=float(config_dict['max_temperature_gradient']),
            temperature_gradient_factor=float(config_dict['temperature_gradient_factor']),
            ppfd_to_photosynthesis_factor=float(config_dict['ppfd_to_photosynthesis_factor'])
        )


@dataclass
class CanopyLayer:
    layer_index: int
    height_top: float
    height_bottom: float
    leaf_area_density: float
    cumulative_lai_above: float
    fraction_sunlit: float
    fraction_shaded: float
    ppfd_sunlit: float
    ppfd_shaded: float
    ppfd_average: float
    temperature: float
    co2_concentration: float


@dataclass
class LightEnvironment:
    ppfd_above_canopy: float
    direct_beam_fraction: float
    diffuse_fraction: float
    solar_zenith_angle: float
    solar_azimuth_angle: float


@dataclass
class CanopyArchitectureResponse:
    canopy_layers: List[CanopyLayer]
    total_lai: float
    canopy_height: float
    light_interception_fraction: float
    average_extinction_coefficient: float
    sunlit_lai: float
    shaded_lai: float
    total_absorbed_ppfd: float
    canopy_photosynthesis: float


class CanopyArchitectureModel:
    def __init__(self, parameters: CanopyArchitectureParameters):
        self.params = parameters
        self.canopy_layers: List[CanopyLayer] = []
        self._initialize_canopy_layers()
        
    def _initialize_canopy_layers(self):
        n_layers = self.params.number_of_layers
        layer_height = self.params.plant_height / n_layers

        self.canopy_layers = []
        for i in range(n_layers):
            layer = CanopyLayer(
                layer_index=i,
                height_top=self.params.plant_height - (i * layer_height),
                height_bottom=self.params.plant_height - ((i + 1) * layer_height),
                leaf_area_density=0.0,
                cumulative_lai_above=0.0,
                fraction_sunlit=0.0,
                fraction_shaded=0.0,
                ppfd_sunlit=0.0,
                ppfd_shaded=0.0,
                ppfd_average=0.0,
                temperature=0.0,
                co2_concentration=0.0
            )
            self.canopy_layers.append(layer)
    
    def calculate_extinction_coefficient(self, solar_zenith_angle: float,
                                       leaf_angle_distribution: str) -> Tuple[float, float]:
        zenith_rad = math.radians(solar_zenith_angle)

        if leaf_angle_distribution == "spherical":
            x = 1.0
        elif leaf_angle_distribution == "planophile":
            x = 2.0 / math.pi
        elif leaf_angle_distribution == "erectophile":
            x = 2.0
        elif leaf_angle_distribution == "plagiophile":
            x = 1.33
        else:
            raise ValueError(f"Invalid leaf angle distribution '{leaf_angle_distribution}' - must be one of: spherical, planophile, erectophile, plagiophile")

        if abs(math.cos(zenith_rad)) > 0.001:
            k_beam = x / math.cos(zenith_rad)
        else:
            k_beam = self.params.max_extinction_coefficient

        k_diffuse = x * self.params.diffuse_extinction_coeff

        k_beam *= self.params.clumping_index
        k_diffuse *= self.params.clumping_index

        return k_beam, k_diffuse
    
    def distribute_leaf_area(self, total_lai: float, canopy_height: float):
        """
        Distribute leaf area vertically through canopy layers.
        
        Args:
            total_lai: Total leaf area index
            canopy_height: Current canopy height (m)
        """
        if total_lai <= 0 or canopy_height <= 0:
            # No leaf area to distribute
            for layer in self.canopy_layers:
                layer.leaf_area_density = 0.0
                layer.cumulative_lai_above = 0.0
            return
        
        # Update layer heights based on current canopy height
        n_layers = len(self.canopy_layers)
        layer_thickness = canopy_height / n_layers
        
        cumulative_lai = 0.0
        
        for i, layer in enumerate(self.canopy_layers):
            # Update layer boundaries
            layer.height_top = canopy_height - (i * layer_thickness)
            layer.height_bottom = canopy_height - ((i + 1) * layer_thickness)
            
            # Set cumulative LAI above this layer
            layer.cumulative_lai_above = cumulative_lai
            
            # Distribute LAI - common patterns for lettuce
            relative_height = (layer.height_top + layer.height_bottom) / (2.0 * canopy_height)
            
            # Beta distribution for lettuce (more leaf area in middle-upper canopy)
            # Use CSV-configurable distribution factors
            if relative_height > 0.8:
                # Upper canopy - moderate leaf density
                layer_lai_fraction = self.params.upper_canopy_lai_factor
            elif relative_height > 0.5:
                # Middle canopy - highest leaf density
                layer_lai_fraction = self.params.middle_canopy_lai_factor
            elif relative_height > 0.2:
                # Lower-middle canopy - moderate density
                layer_lai_fraction = self.params.lower_middle_canopy_lai_factor
            else:
                # Bottom canopy - lower density
                layer_lai_fraction = self.params.bottom_canopy_lai_factor
            
            # Normalize to ensure total adds up correctly
            layer_lai = (layer_lai_fraction / n_layers) * total_lai
            layer.leaf_area_density = layer_lai / layer_thickness
            
            cumulative_lai += layer_lai
    
    def calculate_light_distribution(self, light_env: LightEnvironment,
                                   total_lai: float) -> Tuple[float, float]:
        """
        Calculate light distribution through canopy using Beer's law.
        
        Args:
            light_env: Light environment conditions
            total_lai: Total leaf area index
            
        Returns:
            Tuple of (light_interception_fraction, average_extinction_coeff)
        """
        # Calculate extinction coefficients
        k_beam, k_diffuse = self.calculate_extinction_coefficient(
            light_env.solar_zenith_angle,
            self.params.leaf_angle_distribution
        )
        
        # Separate beam and diffuse light
        ppfd_beam = light_env.ppfd_above_canopy * light_env.direct_beam_fraction
        ppfd_diffuse = light_env.ppfd_above_canopy * light_env.diffuse_fraction
        
        total_absorbed_ppfd = 0.0
        
        for layer in self.canopy_layers:
            lai_above = layer.cumulative_lai_above
            
            # Light penetration using Beer's law
            beam_transmission = math.exp(-k_beam * lai_above)
            diffuse_transmission = math.exp(-k_diffuse * lai_above)
            
            # PPFD at top of layer
            ppfd_beam_layer = ppfd_beam * beam_transmission
            ppfd_diffuse_layer = ppfd_diffuse * diffuse_transmission
            
            # Calculate sunlit and shaded fractions
            if self.params.sunlit_fraction_method == "campbell":
                # Campbell & Norman method
                layer_lai = layer.leaf_area_density * (layer.height_top - layer.height_bottom)
                if layer_lai > 0:
                    sunlit_fraction = (1.0 - math.exp(-k_beam * layer_lai)) / (k_beam * layer_lai)
                else:
                    sunlit_fraction = 0.0
            else:
                # Simple method
                sunlit_fraction = math.exp(-k_beam * lai_above)
            
            layer.fraction_sunlit = sunlit_fraction
            layer.fraction_shaded = 1.0 - sunlit_fraction
            
            # PPFD on sunlit and shaded leaves
            layer.ppfd_sunlit = ppfd_beam_layer + ppfd_diffuse_layer
            layer.ppfd_shaded = ppfd_diffuse_layer * self.params.shaded_light_fraction  # Shaded leaves get scattered light from CSV
            
            # Average PPFD for the layer
            layer.ppfd_average = (layer.fraction_sunlit * layer.ppfd_sunlit + 
                                layer.fraction_shaded * layer.ppfd_shaded)
            
            # Account for light absorption in this layer
            layer_lai = layer.leaf_area_density * (layer.height_top - layer.height_bottom)
            absorbed_beam = ppfd_beam_layer * (1.0 - math.exp(-k_beam * layer_lai)) * self.params.leaf_absorptance
            absorbed_diffuse = ppfd_diffuse_layer * (1.0 - math.exp(-k_diffuse * layer_lai)) * self.params.leaf_absorptance
            
            total_absorbed_ppfd += absorbed_beam + absorbed_diffuse
        
        # Calculate total light interception
        if light_env.ppfd_above_canopy > 0:
            light_interception_fraction = total_absorbed_ppfd / light_env.ppfd_above_canopy
        else:
            light_interception_fraction = 0.0
        
        # Average extinction coefficient
        avg_k = (k_beam * light_env.direct_beam_fraction + 
                k_diffuse * light_env.diffuse_fraction)
        
        return light_interception_fraction, avg_k
    
    def calculate_row_effects(self, row_spacing: float, plant_spacing: float,
                            canopy_width: float) -> float:
        """
        Calculate effects of row spacing on light interception.
        
        Args:
            row_spacing: Distance between rows (m)
            plant_spacing: Distance between plants in row (m) 
            canopy_width: Width of individual plant canopy (m)
            
        Returns:
            Row effect factor (0-1, 1=no row effect)
        """
        # Calculate ground coverage fraction
        plant_area = canopy_width * canopy_width  # Assume square canopy
        available_area = row_spacing * plant_spacing
        
        if available_area > 0:
            ground_coverage = min(1.0, plant_area / available_area)
        else:
            ground_coverage = 1.0
        
        if ground_coverage < 1.0:
            row_factor = self.params.self_shading_factor + (1.0 - self.params.self_shading_factor) * ground_coverage
        else:
            row_factor = 1.0
        
        return row_factor
    
    def calculate_temperature_profile(self, air_temperature: float,
                                    total_lai: float) -> None:
        max_temp_gradient = self.params.max_temperature_gradient
        temp_gradient = min(max_temp_gradient, total_lai * self.params.temperature_gradient_factor)

        for i, layer in enumerate(self.canopy_layers):
            relative_position = i / len(self.canopy_layers)
            layer.temperature = air_temperature - (temp_gradient * relative_position)
    
    def daily_update(self, total_lai: float, canopy_height: float,
                    light_env: LightEnvironment,
                    air_temperature: float,
                    co2_concentration: float) -> CanopyArchitectureResponse:
        self.distribute_leaf_area(total_lai, canopy_height)

        light_interception, avg_extinction = self.calculate_light_distribution(
            light_env, total_lai
        )

        self.calculate_temperature_profile(air_temperature, total_lai)

        for layer in self.canopy_layers:
            layer.co2_concentration = co2_concentration

        row_factor = self.calculate_row_effects(
            self.params.row_spacing,
            self.params.plant_spacing,
            self.params.canopy_width
        )

        effective_light_interception = light_interception * row_factor

        sunlit_lai = sum(layer.fraction_sunlit *
                        layer.leaf_area_density * (layer.height_top - layer.height_bottom)
                        for layer in self.canopy_layers)
        shaded_lai = total_lai - sunlit_lai

        total_absorbed = sum(layer.ppfd_average *
                           layer.leaf_area_density * (layer.height_top - layer.height_bottom)
                           for layer in self.canopy_layers)

        canopy_photosynthesis = total_absorbed * self.params.ppfd_to_photosynthesis_factor
        
        return CanopyArchitectureResponse(
            canopy_layers=self.canopy_layers.copy(),
            total_lai=total_lai,
            canopy_height=canopy_height,
            light_interception_fraction=effective_light_interception,
            average_extinction_coefficient=avg_extinction,
            sunlit_lai=sunlit_lai,
            shaded_lai=shaded_lai,
            total_absorbed_ppfd=total_absorbed,
            canopy_photosynthesis=canopy_photosynthesis
        )
    
def create_lettuce_canopy_model(system_config) -> CanopyArchitectureModel:
    canopy_params = getattr(system_config, 'canopy_parameters', None)

    if canopy_params is None:
        raise ValueError("canopy_parameters missing from CSV")

    if not canopy_params:
        raise ValueError("No canopy parameters found in CSV")

    parameters = CanopyArchitectureParameters.from_config(canopy_params)
    return CanopyArchitectureModel(parameters)


"""
INPUT PARAMETERS (from CSV):
- number_of_layers: number of canopy layers
- max_lai: maximum leaf area index
- extinction_coefficient: light extinction coefficient
- diffuse_extinction_coeff: extinction coefficient for diffuse light
- beam_extinction_coeff: extinction coefficient for direct beam light
- row_spacing: distance between rows (m)
- mean_leaf_angle: mean leaf angle (degrees)
- canopy_width: canopy width (m)
- leaf_angle_distribution: type of leaf angle distribution
- leaf_angle_variance: variance in leaf angles
- plant_spacing: distance between plants in row (m)
- plant_height: maximum plant height (m)
- leaf_reflectance: fraction of light reflected
- leaf_transmittance: fraction of light transmitted
- leaf_absorptance: fraction of light absorbed
- self_shading_factor: factor for self-shading within plant
- neighbor_shading_distance: distance for neighbor shading (m)
- sunlit_fraction_method: method for calculating sunlit fraction
- clumping_index: leaf clumping index (0-1)
- max_extinction_coefficient: maximum extinction coefficient for horizontal sun
- upper_canopy_lai_factor: LAI distribution factor for upper canopy
- middle_canopy_lai_factor: LAI distribution factor for middle canopy
- lower_middle_canopy_lai_factor: LAI distribution factor for lower-middle canopy
- bottom_canopy_lai_factor: LAI distribution factor for bottom canopy
- shaded_light_fraction: fraction of diffuse light reaching shaded leaves
- max_temperature_gradient: maximum temperature gradient through canopy
- temperature_gradient_factor: temperature gradient factor per LAI unit
- ppfd_to_photosynthesis_factor: PPFD to photosynthesis conversion factor

INPUT VARIABLES:
- total_lai: total leaf area index
- canopy_height: current canopy height (m)
- light_env.ppfd_above_canopy: incident PPFD (μmol/m²/s)
- light_env.direct_beam_fraction: fraction of direct beam light
- light_env.diffuse_fraction: fraction of diffuse light
- light_env.solar_zenith_angle: solar zenith angle (degrees)
- light_env.solar_azimuth_angle: solar azimuth angle (degrees)
- air_temperature: air temperature (°C)
- co2_concentration: CO2 concentration (ppm)

OUTPUT VARIABLES:
- canopy_layers: list of CanopyLayer objects with layer properties
- light_interception_fraction: fraction of light intercepted
- average_extinction_coefficient: average extinction coefficient
- sunlit_lai: sunlit leaf area index
- shaded_lai: shaded leaf area index
- total_absorbed_ppfd: total absorbed PPFD (μmol/m²/s)
- canopy_photosynthesis: canopy photosynthesis (μmol CO2/m²/s)
"""
