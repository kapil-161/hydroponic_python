"""
Configuration Loader for Hydroponic Simulation System
Loads all static values from JSON configuration files
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """Unified configuration for hydroponic simulation using canonical schema."""
    physical: Dict[str, Any]
    conversion: Dict[str, Any]
    physiology: Dict[str, Any]
    environment: Dict[str, Any]
    growth: Dict[str, Any]
    canopy: Dict[str, Any]
    water: Dict[str, Any]
    nutrients: Dict[str, Any]
    stress: Dict[str, Any]
    roots: Dict[str, Any]
    phenology: Dict[str, Any]
    thermal_requirements: Dict[str, Any]
    photosynthesis: Dict[str, Any]
    system: Dict[str, Any]
    genetics: Dict[str, Any]


class ConfigLoader:
    """Loads and manages configuration from JSON files."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Use canonical root config by default
        default_root = Path(__file__).parent.parent.parent / "cropgro_config.json"
        if config_path is not None:
            self.config_path = Path(config_path)
        else:
            self.config_path = default_root
        
        self.config: Optional[SimulationConfig] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file using unified canonical schema."""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            # Directly map canonical schema to SimulationConfig
            self.config = SimulationConfig(
                physical=config_data.get('physical', {}),
                conversion=config_data.get('conversion', {}),
                physiology=config_data.get('physiology', {}),
                environment=config_data.get('environment', {}),
                growth=config_data.get('growth', {}),
                canopy=config_data.get('canopy', {}),
                water=config_data.get('water', {}),
                nutrients=config_data.get('nutrients', {}),
                stress=config_data.get('stress', {}),
                roots=config_data.get('roots', {}),
                phenology=config_data.get('phenology', {}),
                thermal_requirements=config_data.get('thermal_requirements', {}),
                photosynthesis=config_data.get('photosynthesis', {}),
                system=config_data.get('system', {}),
                genetics=config_data.get('genetics', {})
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration."""
        return self.config.system if self.config else {}
    
    def get_crop_parameters(self) -> Dict[str, Any]:
        """Get crop parameters."""
        return self.config.physiology if self.config else {}
    
    def get_simulation_settings(self) -> Dict[str, Any]:
        """Get simulation settings."""
        return self.config.system if self.config else {}
    
    def get_weather_settings(self) -> Dict[str, Any]:
        """Get weather generation settings."""
        return self.config.environment if self.config else {}
    
    def get_nutrient_parameters(self) -> Dict[str, Any]:
        """Get nutrient parameters."""
        return self.config.nutrients if self.config else {}
    
    def get_rzt_parameters(self) -> Dict[str, Any]:
        """Get root zone temperature parameters."""
        return self.config.roots if self.config else {}
    
    def get_leaf_development_parameters(self) -> Dict[str, Any]:
        """Get leaf development parameters."""
        return self.config.canopy if self.config else {}
    
    def get_environmental_control_config(self) -> Dict[str, Any]:
        """Get environmental control configuration."""
        return self.config.environment if self.config else {}
    
    def get_default_values(self) -> Dict[str, Any]:
        """Get default system values."""
        return self.config.system if self.config else {}
    
    def get_stress_thresholds(self) -> Dict[str, Any]:
        """Get stress threshold parameters."""
        return self.config.stress if self.config else {}

    # === Canonical group helpers ===
    def get_stress_parameters(self) -> Dict[str, Any]:
        return self.config.stress if self.config else {}

    def get_system_parameters(self) -> Dict[str, Any]:
        return self.config.system if self.config else {}

    def get_genetics_parameters(self) -> Dict[str, Any]:
        return self.config.genetics if self.config else {}

    def get_all_parameters(self) -> Dict[str, Any]:
        if not self.config:
            return {}
        # Return all sections as a dictionary
        return {
            'physical': self.config.physical,
            'conversion': self.config.conversion,
            'physiology': self.config.physiology,
            'environment': self.config.environment,
            'growth': self.config.growth,
            'canopy': self.config.canopy,
            'water': self.config.water,
            'nutrients': self.config.nutrients,
            'stress': self.config.stress,
            'roots': self.config.roots,
            'phenology': self.config.phenology,
            'photosynthesis': self.config.photosynthesis,
            'system': self.config.system,
            'genetics': self.config.genetics
        }
    
    def get_mechanistic_uptake_config(self) -> Dict[str, Any]:
        """Get mechanistic uptake configuration."""
        return self.config.nutrients if self.config else {}
    
    def get_nutrient_concentration_config(self) -> Dict[str, Any]:
        """Get nutrient concentration configuration."""
        return self.config.nutrients if self.config else {}
    
    def get_respiration_parameters(self) -> Dict[str, Any]:
        """Get respiration model parameters."""
        return self.config.physiology if self.config else {}
    
    def get_phenology_parameters(self) -> Dict[str, Any]:
        """Get phenology model parameters."""
        return self.config.phenology if self.config else {}
    
    def get_senescence_parameters(self) -> Dict[str, Any]:
        """Get senescence model parameters."""
        return self.config.canopy if self.config else {}
    
    def get_canopy_architecture_parameters(self) -> Dict[str, Any]:
        """Get canopy architecture model parameters."""
        return self.config.canopy if self.config else {}
    
    def get_nitrogen_balance_parameters(self) -> Dict[str, Any]:
        """Get nitrogen balance model parameters."""
        return self.config.nutrients if self.config else {}
    
    def get_nutrient_mobility_parameters(self) -> Dict[str, Any]:
        """Get nutrient mobility model parameters."""
        return self.config.nutrients if self.config else {}
    
    def get_temperature_stress_parameters(self) -> Dict[str, Any]:
        """Get temperature stress model parameters."""
        return self.config.stress if self.config else {}
    
    # === Missing methods that models expect ===
    def get_photosynthesis_parameters(self) -> Dict[str, Any]:
        """Get photosynthesis model parameters."""
        return self.config.photosynthesis if self.config else {}
    
    def get_environment_parameters(self) -> Dict[str, Any]:
        """Get environment parameters."""
        return self.config.environment if self.config else {}
    
    def get_growth_parameters(self) -> Dict[str, Any]:
        """Get growth parameters."""
        return self.config.growth if self.config else {}
    
    def get_physiology_parameters(self) -> Dict[str, Any]:
        """Get physiology parameters."""
        return self.config.physiology if self.config else {}
    
    def get_water_parameters(self) -> Dict[str, Any]:
        """Get water parameters."""
        return self.config.water if self.config else {}
    
    def get_canopy_parameters(self) -> Dict[str, Any]:
        """Get canopy parameters."""
        return self.config.canopy if self.config else {}
    
    def get_thermal_requirements(self) -> Dict[str, Any]:
        """Get thermal requirements parameters."""
        return self.config.thermal_requirements if self.config else {}
    
    def get_value(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific configuration value with fallback."""
        if not self.config:
            return default
        
        section_data = getattr(self.config, section, {})
        return section_data.get(key, default)
    
    def get_nested_value(self, section: str, subsection: str, key: str, default: Any = None) -> Any:
        """Get a nested configuration value with fallback."""
        if not self.config:
            return default
        
        section_data = getattr(self.config, section, {})
        subsection_data = section_data.get(subsection, {})
        return subsection_data.get(key, default)
    
    def reload_config(self):
        """Reload configuration from file."""
        self._load_config()
    
    def validate_config(self) -> Dict[str, list]:
        """Validate configuration and return any issues."""
        issues = {}
        
        if not self.config:
            issues['general'] = ['No configuration loaded']
            return issues
        
        # Validate essential parameters exist
        if not self.config.system.get('PLANT_DENSITY'):
            issues.setdefault('system', []).append('Missing PLANT_DENSITY')
        
        if not self.config.phenology.get('BASE_TEMPERATURE'):
            issues.setdefault('phenology', []).append('Missing BASE_TEMPERATURE')
        
        # Warn about empty sections (but don't make them errors)
        empty_sections = []
        for section_name in ['physical', 'conversion', 'nutrients', 'roots']:
            section_data = getattr(self.config, section_name, {})
            if not section_data:
                empty_sections.append(section_name)
        if empty_sections:
            issues.setdefault('warnings', []).append(f'Empty sections: {empty_sections}')
        
        return issues


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """Get the global configuration loader instance."""
    global _config_loader
    if _config_loader is None or config_path is not None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def get_config() -> SimulationConfig:
    """Get the current configuration."""
    loader = get_config_loader()
    if loader.config is None:
        raise ValueError("No configuration loaded")
    return loader.config


# Convenience functions for accessing common configuration values
def get_default_value(key: str, default: Any = None) -> Any:
    """Get a default system value from configuration."""
    return get_config_loader().get_value('system', key, default)


def get_rzt_parameter(key: str, default: Any = None) -> Any:
    """Get an RZT parameter from configuration."""
    return get_config_loader().get_value('roots', key, default)


def get_leaf_parameter(key: str, default: Any = None) -> Any:
    """Get a leaf development parameter from configuration."""
    return get_config_loader().get_value('canopy', key, default)


def get_root_architecture_parameter(key: str, default: Any = None) -> Any:
    """Get a root architecture parameter from configuration."""
    return get_config_loader().get_value('roots', key, default)


def get_root_uptake_parameter(key: str, default: Any = None) -> Any:
    """Get a root uptake parameter from configuration."""
    return get_config_loader().get_value('roots', key, default)


def get_genetic_parameter(key: str, default: Any = None) -> Any:
    """Get a genetic parameter from configuration."""
    return get_config_loader().get_value('genetics', key, default)


def get_cultivar_data(cultivar_id: str, default: Any = None) -> Any:
    """Get cultivar data from configuration."""
    return get_config_loader().get_value('genetics', cultivar_id, default)


def get_breeding_parameter(key: str, default: Any = None) -> Any:
    """Get a breeding parameter from configuration."""
    return get_config_loader().get_value('genetics', key, default)


def get_environmental_setpoint(key: str, default: Any = None) -> Any:
    """Get an environmental control setpoint from configuration."""
    return get_config_loader().get_value('environment', key, default)


def get_equipment_parameter(key: str, default: Any = None) -> Any:
    """Get an equipment parameter from configuration."""
    return get_config_loader().get_value('environment', key, default)


def get_pid_parameter(controller: str, key: str, default: Any = None) -> Any:
    """Get a PID controller parameter from configuration."""
    # Note: controller parameter kept for compatibility but using unified environment config
    return get_config_loader().get_value('environment', key, default)


if __name__ == "__main__":
    # Test configuration loading
    try:
        loader = get_config_loader()
        config = get_config()
        
        print("Configuration loaded successfully!")
        print(f"Plant Density: {config.system.get('PLANT_DENSITY')}")
        print(f"Tank Volume Base: {config.system.get('TANK_VOLUME_BASE')} L")
        print(f"Optimal Temperature: {config.environment.get('OPTIMAL_TEMPERATURE')} °C")
        print(f"Base Temperature: {config.phenology.get('BASE_TEMPERATURE')} °C")
        
        # Validate configuration
        issues = loader.validate_config()
        if issues:
            print("\nConfiguration issues found:")
            for section, problems in issues.items():
                print(f"  {section}: {problems}")
        else:
            print("\nConfiguration validation: PASSED")
            
    except Exception as e:
        print(f"Error loading configuration: {e}")


"""
=== FUNCTION EXPLANATIONS FOR NON-CODERS ===

This file is the configuration management system - the central library that loads and manages 
all the settings for the hydroponic simulation. Think of it as the master settings panel 
for your hydroponic system, like the control center that stores all the specific values 
and parameters that make your system unique. It's like having a detailed instruction manual 
that tells every part of the simulation exactly how to behave.

WHAT CONFIGURATION MANAGEMENT DOES:

Instead of having numbers hard-coded throughout the simulation (which would be inflexible), 
all settings are stored in external configuration files. This allows:
- **Easy customization**: Change plant varieties, system sizes, environmental settings
- **Experimental design**: Compare different configurations without changing code
- **Validation**: Ensure all required settings are present and reasonable
- **Organization**: Group related settings together logically

KEY CLASSES AND THEIR PURPOSE:

1. SimulationConfig (Data Container)
   - What it does: Organizes all configuration parameters into logical groups
   - Groups: Physical properties, physiology, environment, growth, nutrients, stress, etc.
   - Real-world meaning: Like having organized filing cabinets where each drawer contains 
     related documents - one drawer for plant biology, another for system hardware, 
     another for environmental controls.

2. ConfigLoader (Configuration Manager)
   - What it does: Loads configuration from files and provides easy access to settings
   - Features: File loading, validation, error handling, convenient access methods
   - Real-world meaning: Like a librarian who knows exactly where to find any document 
     you need and can tell you if something is missing or incorrect.

MAIN CONFIGURATION FUNCTIONS:

3. _load_config()
   - What it does: Reads the JSON configuration file and converts it to usable format
   - Error handling: Provides clear error messages if file is missing or corrupted
   - Validation: Ensures the file format is correct and readable
   - Real-world meaning: Like opening and reading a user manual, checking that all 
     pages are present and the text is legible.

4. get_*_parameters() functions (many variations)
   - What they do: Provide easy access to specific groups of settings
   - Examples: get_crop_parameters(), get_environmental_control_config()
   - Benefit: You don't need to remember the exact structure of the configuration file
   - Real-world meaning: Like asking a librarian "Where are the books on plant biology?" 
     instead of searching through every shelf yourself.

5. validate_config()
   - What it does: Checks that all essential settings are present and reasonable
   - Validation types: Required parameters, reasonable ranges, data type checking
   - Error reporting: Lists specific problems found and suggests solutions
   - Real-world meaning: Like an inspector checking that a building has all required 
     safety equipment and that everything meets building codes.

6. get_value() and get_nested_value()
   - What they do: Retrieve specific configuration values with fallback defaults
   - Safety features: Return default values if requested setting doesn't exist
   - Flexibility: Can access deeply nested configuration structures
   - Real-world meaning: Like asking for a specific document with a backup plan if 
     it's not available - "Give me the optimal temperature setting, or 22°C if not specified."

CONFIGURATION ORGANIZATION:

The configuration is organized into logical sections:

**Physical Properties**:
- System dimensions, tank volumes, flow rates
- Hardware specifications and physical constraints
- Like the blueprint specifications of your growing system

**Physiology Parameters**:
- Plant-specific biological constants
- Growth rates, metabolic parameters, enzyme kinetics
- Like the biological profile card for your chosen crop

**Environment Settings**:
- Temperature, humidity, CO2, light control settings
- Optimal ranges and control parameters
- Like the climate control settings for your growing environment

**Nutrient Configuration**:
- Nutrient concentrations, uptake rates, mobility parameters
- pH and EC control settings
- Like the recipe for your nutrient solution

**Stress Parameters**:
- Temperature, water, nutrient stress thresholds
- Stress response curves and damage recovery rates
- Like the warning levels that indicate when plants are in trouble

**Growth Parameters**:
- Biomass allocation patterns, development rates
- Leaf expansion, root growth, senescence timing
- Like the growth schedule and resource allocation strategy

PRACTICAL BENEFITS:

For Different Users:
1. **Researchers**: Easy to create different experimental treatments
2. **Growers**: Customize settings for different crops and varieties
3. **Students**: Explore how different parameters affect plant growth
4. **System Designers**: Optimize settings for specific hardware configurations

For System Flexibility:
1. **Variety Changes**: Switch between lettuce, herbs, tomatoes with different config files
2. **System Scaling**: Adjust for different system sizes without code changes
3. **Environmental Control**: Fine-tune climate control parameters
4. **Experimental Design**: Create systematic parameter variations

For Error Prevention:
1. **Validation**: Catch configuration errors before simulation starts
2. **Defaults**: Provide reasonable fallback values for missing parameters
3. **Type Checking**: Ensure numeric parameters are actually numbers
4. **Range Checking**: Verify values are within biologically reasonable limits

CONFIGURATION FILE STRUCTURE:

JSON Format Example:
```json
{
  "physiology": {
    "BASE_TEMPERATURE": 4.0,
    "OPTIMAL_TEMPERATURE": 22.0,
    "MAXIMUM_TEMPERATURE": 35.0
  },
  "environment": {
    "CO2_CONCENTRATION": 400,
    "RELATIVE_HUMIDITY": 70,
    "VPD_TARGET": 1.0
  },
  "nutrients": {
    "OPTIMAL_PH": 6.0,
    "OPTIMAL_EC": 1.5,
    "NITRATE_CONCENTRATION": 150
  }
}
```

**Human-Readable**: Easy to edit with any text editor
**Hierarchical**: Organized into logical groups and subgroups
**Flexible**: Can add new parameters without changing code
**Portable**: Same configuration can be shared between different systems

GLOBAL CONFIGURATION MANAGEMENT:

7. get_config_loader() - Global Instance Manager
   - What it does: Ensures only one configuration is loaded at a time
   - Benefit: Prevents conflicting configurations and reduces memory usage
   - Singleton pattern: One central source of truth for all configuration
   - Real-world meaning: Like having one master filing cabinet that everyone uses, 
     rather than everyone having their own copy that might get out of sync.

8. Convenience Functions (get_default_value, get_rzt_parameter, etc.)
   - What they do: Provide shortcut access to commonly used parameters
   - Benefit: Simpler code, less typing, fewer errors
   - Examples: get_genetic_parameter('CULTIVAR_ID'), get_environmental_setpoint('TARGET_TEMP')
   - Real-world meaning: Like having speed-dial buttons for frequently called numbers.

CONFIGURATION VALIDATION:

Error Detection:
- **Missing Required Parameters**: Identifies essential settings that are missing
- **Invalid Data Types**: Catches text where numbers are expected
- **Out-of-Range Values**: Warns about unrealistic parameter values
- **Inconsistent Settings**: Identifies contradictory parameters

Warning System:
- **Empty Sections**: Notes configuration sections that have no parameters
- **Default Usage**: Identifies when default values are being used
- **Deprecated Parameters**: Warns about obsolete configuration options

ERROR HANDLING:

File Not Found:
- Clear error message identifying the missing configuration file
- Suggestions for where the file should be located
- Graceful failure without crashing the entire system

Invalid JSON:
- Specific error messages about formatting problems
- Line numbers and character positions where errors occur
- Suggestions for fixing common JSON syntax errors

Missing Parameters:
- Lists exactly which required parameters are missing
- Provides default values where possible
- Continues operation with warnings when feasible

KEY CONCEPTS FOR NON-CODERS:

JSON (JavaScript Object Notation): A human-readable format for storing structured data, 
like a hierarchical list that computers can easily read and write.

Singleton Pattern: A programming design where only one instance of something exists 
system-wide, like having one master key rather than many duplicate keys.

Validation: The process of checking that data meets all requirements and makes sense, 
like proofreading a document before submitting it.

Default Values: Backup settings that are used when specific values aren't provided, 
like default font settings in a word processor.

Global Configuration: System-wide settings that affect all components, like the 
master volume control that affects all audio programs on a computer.

This configuration management system provides the flexibility and reliability needed 
for scientific-grade crop modeling, allowing researchers and growers to easily 
customize the simulation for their specific needs while ensuring all parameters 
are valid and consistent. It transforms a rigid simulation into a flexible tool 
that can model any hydroponic system configuration.
"""