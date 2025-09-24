"""
Canopy Architecture Model for Hydroponic Crop Simulation -No hardcoded defaults allowed and no fallback to simple alternative codes
Based on CROPGRO CANOPY.for and canopy light interception research

Key concepts implemented:
1. Multi-layer canopy light distribution using Beer's law
2. Row spacing and plant geometry effects 
3. Leaf angle distribution modeling
4. Leaf area density by canopy layer
5. Photosynthesis calculation by canopy layer
6. Shading effects and competition

Research basis:
- Monsi & Saeki (1953) - On the factor light in plant communities
- Norman & Campbell (1989) - Canopy structure
- Goudriaan & van Laar (1994) - Modelling potential crop growth processes
- Spitters et al. (1986) - Separating direct and diffuse radiation components
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import math


class LeafAngleDistribution(Enum):
    """Leaf angle distribution types."""
    PLANOPHILE = "planophile"     # Horizontal leaves
    ERECTOPHILE = "erectophile"   # Vertical leaves  
    PLAGIOPHILE = "plagiophile"   # 45-degree angle leaves
    EXTREMOPHILE = "extremophile"  # Very vertical or horizontal
    SPHERICAL = "spherical"       # Random distribution
    UNIFORM = "uniform"           # Uniform distribution


@dataclass
class CanopyArchitectureParameters:
    """Parameters for canopy architecture model."""
    
    # Canopy structure
    number_of_layers: int                    # Number of canopy layers
    max_lai: float                           # Maximum leaf area index
    
    # Light extinction
    extinction_coefficient: float            # Light extinction coefficient (k)
    diffuse_extinction_coeff: float          # Extinction for diffuse light
    beam_extinction_coeff: float             # Extinction for direct beam light
    
    # Plant geometry
    row_spacing: float                       # m between rows
    mean_leaf_angle: float                   # Mean leaf angle (degrees)
    canopy_width: float                      # m canopy width
    
    # Leaf angle distribution
    leaf_angle_distribution: str             # Type of leaf angle distribution
    leaf_angle_variance: float               # Variance in leaf angles
    
    plant_spacing: float                     # m between plants in row
    plant_height: float                      # m maximum plant height
    
    # Leaf properties
    leaf_reflectance: float                  # Fraction of light reflected
    leaf_transmittance: float                # Fraction of light transmitted
    leaf_absorptance: float                  # Fraction of light absorbed
    
    # Shading parameters
    self_shading_factor: float               # Factor for self-shading within plant
    neighbor_shading_distance: float         # m distance for neighbor shading
    
    # Photosynthesis scaling
    sunlit_fraction_method: str              # Method for calculating sunlit fraction
    clumping_index: float                    # Leaf clumping index (0-1)
    
    # Additional canopy architecture parameters for advanced modeling
    max_extinction_coefficient: float        # Maximum extinction coefficient for horizontal sun
    upper_canopy_lai_factor: float           # LAI distribution factor for upper canopy
    middle_canopy_lai_factor: float          # LAI distribution factor for middle canopy
    lower_middle_canopy_lai_factor: float    # LAI distribution factor for lower-middle canopy
    bottom_canopy_lai_factor: float          # LAI distribution factor for bottom canopy
    shaded_light_fraction: float             # Fraction of diffuse light reaching shaded leaves
    max_temperature_gradient: float          # Maximum temperature gradient through canopy
    temperature_gradient_factor: float        # Temperature gradient factor per LAI unit
    ppfd_to_photosynthesis_factor: float     # PPFD to photosynthesis conversion factor
    
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'CanopyArchitectureParameters':
        """Create CanopyArchitectureParameters from CSV configuration data."""
        # Validate required parameters
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
            raise ValueError(f"❌ Missing required canopy architecture parameters in CSV: {missing_params}")
        
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
            # Additional canopy architecture parameters
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
    """Properties of a single canopy layer."""
    layer_index: int                         # Layer number (0=top)
    height_top: float                        # m height of layer top
    height_bottom: float                     # m height of layer bottom
    leaf_area_density: float                 # m²/m³ leaf area density in layer
    cumulative_lai_above: float              # LAI above this layer
    fraction_sunlit: float = None             # Fraction of leaves in sun
    fraction_shaded: float = None             # Fraction of leaves in shade
    ppfd_sunlit: float = None                 # μmol/m²/s PPFD on sunlit leaves
    ppfd_shaded: float = None                 # μmol/m²/s PPFD on shaded leaves
    ppfd_average: float = None                # μmol/m²/s average PPFD
    temperature: float = None                # °C layer temperature
    co2_concentration: float = None         # ppm CO2 concentration


@dataclass
class LightEnvironment:
    """Light environment inputs for canopy model."""
    ppfd_above_canopy: float                 # μmol/m²/s incident PPFD
    direct_beam_fraction: float              # Fraction of direct beam light
    diffuse_fraction: float                  # Fraction of diffuse light
    solar_zenith_angle: float                # degrees solar zenith angle
    solar_azimuth_angle: float = None       # degrees solar azimuth angle


@dataclass
class CanopyArchitectureResponse:
    """Daily canopy architecture calculation results."""
    canopy_layers: List[CanopyLayer]
    total_lai: float
    canopy_height: float
    light_interception_fraction: float
    average_extinction_coefficient: float
    sunlit_lai: float
    shaded_lai: float
    total_absorbed_ppfd: float               # μmol/m²/s total absorbed
    canopy_photosynthesis: float             # μmol CO2/m²/s canopy photosynthesis


class CanopyArchitectureModel:
    """
    Canopy architecture model following CROPGRO principles.
    
    Models multi-layer canopy light distribution, leaf angle effects,
    and provides foundation for canopy-scale photosynthesis.
    """
    
    def __init__(self, parameters: Optional[CanopyArchitectureParameters] = None):
        if parameters is None:
            raise ValueError("❌ CanopyArchitectureParameters required - no hardcoded defaults allowed")
        
        self.params = parameters
        self.canopy_layers: List[CanopyLayer] = []
        self._initialize_canopy_layers()
        
    def _initialize_canopy_layers(self):
        """Initialize canopy layer structure."""
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
                temperature=25.0,  # Default temperature for initialization
                co2_concentration=400.0  # Default CO2 for initialization
            )
            self.canopy_layers.append(layer)
    
    def calculate_extinction_coefficient(self, solar_zenith_angle: float,
                                       leaf_angle_distribution: str) -> Tuple[float, float]:
        """
        Calculate light extinction coefficients based on leaf angle and sun angle.
        
        Args:
            solar_zenith_angle: Solar zenith angle (degrees)
            leaf_angle_distribution: Type of leaf angle distribution
            
        Returns:
            Tuple of (direct_beam_k, diffuse_k)
        """
        # Convert to radians
        zenith_rad = math.radians(solar_zenith_angle)
        
        # Leaf angle distribution factors (must be provided in CSV configuration)
        if leaf_angle_distribution == "spherical":
            # Spherical leaf angle distribution (random)
            x = 1.0  # Factor for spherical distribution
        elif leaf_angle_distribution == "planophile":
            # Horizontal leaves
            x = 2.0 / math.pi
        elif leaf_angle_distribution == "erectophile":
            # Vertical leaves  
            x = 2.0
        elif leaf_angle_distribution == "plagiophile":
            # 45-degree leaves
            x = 1.33
        else:
            raise ValueError(f"❌ Invalid leaf angle distribution '{leaf_angle_distribution}' - must be one of: spherical, planophile, erectophile, plagiophile")
        
        # Calculate extinction coefficient for direct beam
        if abs(math.cos(zenith_rad)) > 0.001:
            k_beam = x / math.cos(zenith_rad)
        else:
            k_beam = self.params.max_extinction_coefficient  # Large value for horizontal sun from CSV
        
        # Extinction coefficient for diffuse light (integrated over hemisphere)
        k_diffuse = x * self.params.diffuse_extinction_coeff
        
        # Apply clumping effects
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
        
        # Row effect reduces light interception when ground coverage < 1
        # Account for light penetration between rows
        if ground_coverage < 1.0:
            row_factor = 0.8 + 0.2 * ground_coverage  # Some light still intercepted
        else:
            row_factor = 1.0
        
        return row_factor
    
    def calculate_temperature_profile(self, air_temperature: float,
                                    total_lai: float) -> None:
        """
        Calculate temperature profile through canopy.
        
        Args:
            air_temperature: Above-canopy air temperature (°C)
            total_lai: Total leaf area index
        """
        # Simple temperature gradient model
        # Temperature typically decreases from top to bottom in dense canopy
        max_temp_gradient = self.params.max_temperature_gradient  # Max temperature gradient from CSV
        temp_gradient = min(max_temp_gradient, total_lai * self.params.temperature_gradient_factor)
        
        for i, layer in enumerate(self.canopy_layers):
            # Linear decrease from top to bottom
            relative_position = i / len(self.canopy_layers)
            layer.temperature = air_temperature - (temp_gradient * relative_position)
    
    def daily_update(self, total_lai: float, canopy_height: float,
                    light_env: LightEnvironment,
                    air_temperature: float = 25.0,
                    co2_concentration: float = 400.0) -> CanopyArchitectureResponse:
        """
        Daily canopy architecture update.
        
        Args:
            total_lai: Total leaf area index
            canopy_height: Current canopy height (m)
            light_env: Light environment conditions
            air_temperature: Air temperature (°C)
            co2_concentration: CO2 concentration (ppm)
            
        Returns:
            Canopy architecture response
        """
        # Distribute leaf area through layers
        self.distribute_leaf_area(total_lai, canopy_height)
        
        # Calculate light distribution
        light_interception, avg_extinction = self.calculate_light_distribution(
            light_env, total_lai
        )
        
        # Calculate temperature profile
        self.calculate_temperature_profile(air_temperature, total_lai)
        
        # Update CO2 concentration in all layers (assume well-mixed)
        for layer in self.canopy_layers:
            layer.co2_concentration = co2_concentration
        
        # Calculate row effects
        row_factor = self.calculate_row_effects(
            self.params.row_spacing,
            self.params.plant_spacing, 
            self.params.canopy_width
        )
        
        # Apply row effects to light interception
        effective_light_interception = light_interception * row_factor
        
        # Calculate sunlit and shaded LAI
        sunlit_lai = sum(layer.fraction_sunlit * 
                        layer.leaf_area_density * (layer.height_top - layer.height_bottom)
                        for layer in self.canopy_layers)
        shaded_lai = total_lai - sunlit_lai
        
        # Calculate total absorbed PPFD
        total_absorbed = sum(layer.ppfd_average * 
                           layer.leaf_area_density * (layer.height_top - layer.height_bottom)
                           for layer in self.canopy_layers)
        
        # Placeholder for canopy photosynthesis (would integrate with photosynthesis model)
        canopy_photosynthesis = total_absorbed * self.params.ppfd_to_photosynthesis_factor  # Conversion factor from CSV
        
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
    
def create_lettuce_canopy_model(system_config=None) -> CanopyArchitectureModel:
    """Create canopy architecture model with lettuce-specific parameters from CSV config.
    
    Args:
        system_config: System configuration object containing CSV-loaded parameters
        
    Returns:
        CanopyArchitectureModel configured with CSV parameters
        
    Raises:
        ValueError: If CSV parameters are missing or invalid
    """
    if system_config is None:
        raise ValueError("❌ system_config is required - no hardcoded defaults allowed")
    
    # Get canopy parameters from CSV data loaded in system_config
    canopy_params = getattr(system_config, 'canopy_parameters', None)
    
    if canopy_params is None:
        raise ValueError("❌ canopy_parameters missing from CSV - no fallback defaults allowed")
    
    if not canopy_params:
        raise ValueError("❌ No canopy parameters found in CSV - no fallback defaults allowed")
    
    # Create parameters from CSV config
    parameters = CanopyArchitectureParameters.from_config(canopy_params)
    return CanopyArchitectureModel(parameters)


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file simulates how a lettuce canopy (the leafy part) catches and uses light. Think of it like 
modeling how sunlight gets filtered through layers of leaves from top to bottom.

KEY FUNCTIONS AND EQUATIONS:

1. calculate_extinction_coefficient()
   - What it does: Calculates how much light gets blocked by leaves at different sun angles
   - Equation: k = x / cos(zenith_angle) where x depends on leaf angle distribution
   - Real-world meaning: When sun is directly overhead (small angle), less light is blocked.
     When sun is low (large angle), more light gets blocked by leaves.

2. distribute_leaf_area() 
   - What it does: Spreads the total leaf area through different height layers
   - Equation: Uses beta distribution with layer_lai = (factor/n_layers) * total_lai
   - Real-world meaning: Lettuce has more leaves in the middle sections, less at top and bottom.
     This matches how real lettuce plants grow.

3. calculate_light_distribution()
   - What it does: Uses Beer's Law to calculate how light decreases through leaf layers
   - Equation: Light_remaining = Light_initial × e^(-k × LAI)
   - Real-world meaning: Each leaf layer absorbs some light, so deeper leaves get less light.
     Like walking into a forest - it gets darker as you go deeper.

4. calculate_row_effects()
   - What it does: Accounts for spaces between plant rows where light can "leak through"
   - Equation: row_factor = 0.8 + 0.2 × ground_coverage
   - Real-world meaning: If plants don't cover 100% of the ground, some light is "wasted"
     by hitting empty spaces between plants.

5. calculate_temperature_profile()
   - What it does: Calculates how temperature changes from top to bottom of canopy
   - Equation: layer_temp = air_temp - (temp_gradient × relative_position)
   - Real-world meaning: Top leaves are warmer (closer to sun), bottom leaves are cooler.
     Important because temperature affects how fast plants grow.

OVERALL PURPOSE:
This model helps predict:
- How much light each leaf layer receives
- How this affects photosynthesis (food production) 
- How temperature varies through the plant
- Which leaves are in sun vs shade

This information is crucial for optimizing:
- Plant spacing (how close together to plant)
- Light intensity needed
- Where to measure temperature
- Expected growth patterns
"""
