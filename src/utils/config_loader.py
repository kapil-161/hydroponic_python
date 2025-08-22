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
        