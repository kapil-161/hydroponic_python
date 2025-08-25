"""
Canopy Architecture Model for Hydroponic Crop Simulation
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
    number_of_layers: int = 10               # Number of canopy layers (model constant)
    max_lai: float = None                    # Maximum leaf area index
    
    # Light extinction
    extinction_coefficient: float = None     # Light extinction coefficient (k)
    diffuse_extinction_coeff: float = 0.7   # Extinction for diffuse light (model constant)
    beam_extinction_coeff: float = 0.4      # Extinction for direct beam light (model constant)
    
    # Leaf angle distribution
    leaf_angle_distribution: str = "spherical"  # Type of leaf angle distribution (model constant)
    mean_leaf_angle: float = 45.0            # Mean leaf angle (degrees) (model constant)
    leaf_angle_variance: float = 20.0        # Variance in leaf angles (model constant)
    
    # Plant geometry
    row_spacing: float = 0.30                # m between rows (model constant)
    plant_spacing: float = 0.25              # m between plants in row (model constant)
    plant_height: float = 0.25               # m maximum plant height (model constant)
    canopy_width: float = None               # m canopy width
    
    # Leaf properties
    leaf_reflectance: float = 0.10           # Fraction of light reflected (biochemical constant)
    leaf_transmittance: float = 0.05         # Fraction of light transmitted (biochemical constant)
    leaf_absorptance: float = 0.85           # Fraction of light absorbed (biochemical constant)
    
    # Shading parameters
    self_shading_factor: float = 0.8         # Factor for self-shading within plant (model constant)
    neighbor_shading_distance: float = 0.5   # m distance for neighbor shading (model constant)
    
    # Photosynthesis scaling
    sunlit_fraction_method: str = "campbell"  # Method for calculating sunlit fraction (model constant)
    clumping_index: float = 0.9              # Leaf clumping index (0-1) (model constant)
    
    def __post_init__(self):
        """Load parameters from JSON config if not provided."""
        try:
            from ..utils.config_loader import get_config_loader
            loader = get_config_loader()
            cfg = loader.get_canopy_architecture_parameters()

            if self.max_lai is None:
                self.max_lai = cfg.get('max_lai', float('inf'))  # Natural unlimited growth
            if self.extinction_coefficient is None:
                self.extinction_coefficient = cfg.get('extinction_coefficient', 0.69)
            if self.canopy_width is None:
                # Stored in meters in the JSON config
                self.canopy_width = cfg.get('canopy_width', 0.20)
        except Exception:
            # Leave values as provided
            pass
    
    @classmethod
    def from_config(cls, config_dict: dict) -> 'CanopyArchitectureParameters':
        """Create CanopyArchitectureParameters from configuration dictionary."""
        return cls(
            number_of_layers=config_dict.get('number_of_layers', 10),
            max_lai=config_dict.get('max_lai'),
            extinction_coefficient=config_dict.get('extinction_coefficient'),
            diffuse_extinction_coeff=config_dict.get('diffuse_extinction_coeff', 0.7),
            beam_extinction_coeff=config_dict.get('beam_extinction_coeff', 0.4),
            leaf_angle_distribution=config_dict.get('leaf_angle_distribution', 'spherical'),
            mean_leaf_angle=config_dict.get('mean_leaf_angle', 45.0),
            leaf_angle_variance=config_dict.get('leaf_angle_variance', 20.0),
            row_spacing=config_dict.get('row_spacing', 0.30),
            plant_spacing=config_dict.get('plant_spacing', 0.25),
            plant_height=config_dict.get('plant_height', 0.25),
            canopy_width=config_dict.get('canopy_width'),
            leaf_reflectance=config_dict.get('leaf_reflectance', 0.10),
            leaf_transmittance=config_dict.get('leaf_transmittance', 0.05),
            leaf_absorptance=config_dict.get('leaf_absorptance', 0.85),
            self_shading_factor=config_dict.get('self_shading_factor', 0.8),
            neighbor_shading_distance=config_dict.get('neighbor_shading_distance', 0.5),
            sunlit_fraction_method=config_dict.get('sunlit_fraction_method', 'campbell'),
            clumping_index=config_dict.get('clumping_index', 0.9),
        )


@dataclass
class CanopyLayer:
    """Properties of a single canopy layer."""
    layer_index: int                         # Layer number (0=top)
    height_top: float                        # m height of layer top
    height_bottom: float                     # m height of layer bottom
    leaf_area_density: float                 # m²/m³ leaf area density in layer
    cumulative_lai_above: float              # LAI above this layer
    fraction_sunlit: float = 0.0             # Fraction of leaves in sun
    fraction_shaded: float = 0.0             # Fraction of leaves in shade
    ppfd_sunlit: float = 0.0                 # μmol/m²/s PPFD on sunlit leaves
    ppfd_shaded: float = 0.0                 # μmol/m²/s PPFD on shaded leaves
    ppfd_average: float = 0.0                # μmol/m²/s average PPFD
    temperature: float = 25.0                # °C layer temperature
    co2_concentration: float = 400.0         # ppm CO2 concentration


@dataclass
class LightEnvironment:
    """Light environment inputs for canopy model."""
    ppfd_above_canopy: float                 # μmol/m²/s incident PPFD
    direct_beam_fraction: float              # Fraction of direct beam light
    diffuse_fraction: float                  # Fraction of diffuse light
    solar_zenith_angle: float                # degrees solar zenith angle
    solar_azimuth_angle: float = 180.0       # degrees solar azimuth angle


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
        self.params = parameters or CanopyArchitectureParameters()
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
                cumulative_lai_above=0.0
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
        
        # Leaf angle distribution factors
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
            x = 1.0  # Default to spherical
        
        # Calculate extinction coefficient for direct beam
        if abs(math.cos(zenith_rad)) > 0.001:
            k_beam = x / math.cos(zenith_rad)
        else:
            k_beam = 10.0  # Large value for horizontal sun
        
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
            if relative_height > 0.8:
                # Upper canopy - moderate leaf density
                layer_lai_fraction = 0.8
            elif relative_height > 0.5:
                # Middle canopy - highest leaf density
                layer_lai_fraction = 1.2
            elif relative_height > 0.2:
                # Lower-middle canopy - moderate density
                layer_lai_fraction = 0.9
            else:
                # Bottom canopy - lower density
                layer_lai_fraction = 0.6
            
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
            layer.ppfd_shaded = ppfd_diffuse_layer * 0.2  # Shaded leaves get scattered light
            
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
        temp_gradient = min(3.0, total_lai * 0.5)  # Max 3°C gradient
        
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
        canopy_photosynthesis = total_absorbed * 0.05  # Rough conversion factor
        
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
    
def create_lettuce_canopy_model(config=None) -> CanopyArchitectureModel:
    """Create canopy architecture model with lettuce-specific parameters from config."""
    if config is None:
        from ..utils.config_loader import get_config_loader
        config = get_config_loader()
    
    try:
        canopy_config = config.get_canopy_parameters()
        parameters = CanopyArchitectureParameters.from_config(canopy_config)
        return CanopyArchitectureModel(parameters)
    except (AttributeError, FileNotFoundError):
        # Fallback to default parameters for CSV config
        return CanopyArchitectureModel()


def demonstrate_canopy_architecture_model():
    """Demonstrate canopy architecture model capabilities."""
    model = create_lettuce_canopy_model()
    
    print("=" * 80)
    print("CANOPY ARCHITECTURE MODEL DEMONSTRATION")
    print("=" * 80)
    
    # Create light environment
    light_env = LightEnvironment(
        ppfd_above_canopy=1500.0,  # μmol/m²/s
        direct_beam_fraction=0.7,
        diffuse_fraction=0.3,
        solar_zenith_angle=30.0    # degrees
    )
    
    # Test different LAI values
    lai_values = [1.0, 2.5, 4.0, 5.5]
    canopy_height = 0.20  # 20 cm
    
    print(f"{'LAI':<6} {'LightInt':<9} {'SunlitLAI':<10} {'ShadedLAI':<10} {'AvgPPFD':<9} {'ExtCoeff':<9}")
    print("-" * 80)
    
    for lai in lai_values:
        response = model.daily_update(
            total_lai=lai,
            canopy_height=canopy_height,
            light_env=light_env,
            air_temperature=22.0,
            co2_concentration=1200.0
        )
        
        avg_ppfd = response.total_absorbed_ppfd / max(lai, 0.1)
        
        print(f"{lai:<6.1f} {response.light_interception_fraction:<9.3f} "
              f"{response.sunlit_lai:<10.2f} {response.shaded_lai:<10.2f} "
              f"{avg_ppfd:<9.0f} {response.average_extinction_coefficient:<9.3f}")
    
    # Show layer details for LAI = 4.0
    print(f"\nCanopy layer details (LAI = 4.0):")
    response = model.daily_update(4.0, canopy_height, light_env)
    
    print(f"{'Layer':<6} {'Height':<10} {'LAD':<8} {'Sunlit%':<8} {'PPFD_sun':<9} {'PPFD_sh':<8} {'Temp':<6}")
    print("-" * 80)
    
    for i, layer in enumerate(response.canopy_layers[:6]):  # Show top 6 layers
        height_str = f"{layer.height_bottom:.2f}-{layer.height_top:.2f}"
        print(f"{i:<6} {height_str:<10} {layer.leaf_area_density:<8.2f} "
              f"{layer.fraction_sunlit*100:<8.1f} {layer.ppfd_sunlit:<9.0f} "
              f"{layer.ppfd_shaded:<8.0f} {layer.temperature:<6.1f}")
    
    print(f"\nCanopy summary:")
    print(f"• Total light interception: {response.light_interception_fraction:.1%}")
    print(f"• Sunlit LAI: {response.sunlit_lai:.2f}")
    print(f"• Shaded LAI: {response.shaded_lai:.2f}")
    print(f"• Average extinction coefficient: {response.average_extinction_coefficient:.3f}")
    print(f"• Canopy photosynthesis: {response.canopy_photosynthesis:.1f} μmol CO2/m²/s")


if __name__ == "__main__":
    demonstrate_canopy_architecture_model()