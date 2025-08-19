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
    """Complete configuration for hydroponic simulation."""
    system_config: Dict[str, Any]
    crop_parameters: Dict[str, Any]
    simulation_settings: Dict[str, Any]
    weather_settings: Dict[str, Any]
    nutrient_parameters: Dict[str, Any]
    root_zone_temperature: Dict[str, Any]
    leaf_development: Dict[str, Any]
    environmental_control: Dict[str, Any]
    photosynthesis_model: Dict[str, Any]
    mechanistic_uptake: Dict[str, Any]
    nutrient_concentration: Dict[str, Any]
    respiration_model: Dict[str, Any]
    phenology_model: Dict[str, Any]
    senescence_model: Dict[str, Any]
    canopy_architecture: Dict[str, Any]
    nitrogen_balance: Dict[str, Any]
    nutrient_mobility: Dict[str, Any]
    temperature_stress: Dict[str, Any]
    root_architecture: Dict[str, Any]
    genetic_parameters: Dict[str, Any]
    default_values: Dict[str, Any]
    stress_thresholds: Dict[str, Any]


class ConfigLoader:
    """Loads and manages configuration from JSON files."""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Default to sample config in data/input directory
            self.config_path = Path(__file__).parent.parent.parent / "data" / "input" / "sample_config.json"
        else:
            self.config_path = Path(config_path)
        
        self.config: Optional[SimulationConfig] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            self.config = SimulationConfig(
                system_config=config_data.get('system_config', {}),
                crop_parameters=config_data.get('crop_parameters', {}),
                simulation_settings=config_data.get('simulation_settings', {}),
                weather_settings=config_data.get('weather_settings', {}),
                nutrient_parameters=config_data.get('nutrient_parameters', {}),
                root_zone_temperature=config_data.get('root_zone_temperature', {}),
                leaf_development=config_data.get('leaf_development', {}),
                environmental_control=config_data.get('environmental_control', {}),
                photosynthesis_model=config_data.get('photosynthesis_model', {}),
                mechanistic_uptake=config_data.get('mechanistic_uptake', {}),
                nutrient_concentration=config_data.get('nutrient_concentration', {}),
                respiration_model=config_data.get('respiration_model', {}),
                phenology_model=config_data.get('phenology_model', {}),
                senescence_model=config_data.get('senescence_model', {}),
                canopy_architecture=config_data.get('canopy_architecture', {}),
                nitrogen_balance=config_data.get('nitrogen_balance', {}),
                nutrient_mobility=config_data.get('nutrient_mobility', {}),
                temperature_stress=config_data.get('temperature_stress', {}),
                root_architecture=config_data.get('root_architecture', {}),
                genetic_parameters=config_data.get('genetic_parameters', {}),
                default_values=config_data.get('default_values', {}),
                stress_thresholds=config_data.get('stress_thresholds', {})
            )
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration."""
        return self.config.system_config if self.config else {}
    
    def get_crop_parameters(self) -> Dict[str, Any]:
        """Get crop parameters."""
        return self.config.crop_parameters if self.config else {}
    
    def get_simulation_settings(self) -> Dict[str, Any]:
        """Get simulation settings."""
        return self.config.simulation_settings if self.config else {}
    
    def get_weather_settings(self) -> Dict[str, Any]:
        """Get weather generation settings."""
        return self.config.weather_settings if self.config else {}
    
    def get_nutrient_parameters(self) -> Dict[str, Any]:
        """Get nutrient parameters."""
        return self.config.nutrient_parameters if self.config else {}
    
    def get_rzt_parameters(self) -> Dict[str, Any]:
        """Get root zone temperature parameters."""
        return self.config.root_zone_temperature if self.config else {}
    
    def get_leaf_development_parameters(self) -> Dict[str, Any]:
        """Get leaf development parameters."""
        return self.config.leaf_development if self.config else {}
    
    def get_environmental_control_config(self) -> Dict[str, Any]:
        """Get environmental control configuration."""
        return self.config.environmental_control if self.config else {}
    
    def get_default_values(self) -> Dict[str, Any]:
        """Get default system values."""
        return self.config.default_values if self.config else {}
    
    def get_stress_thresholds(self) -> Dict[str, Any]:
        """Get stress threshold parameters."""
        return self.config.stress_thresholds if self.config else {}
    
    def get_photosynthesis_parameters(self) -> Dict[str, Any]:
        """Get photosynthesis model parameters."""
        return self.config.photosynthesis_model if self.config else {}
    
    def get_mechanistic_uptake_config(self) -> Dict[str, Any]:
        """Get mechanistic uptake configuration."""
        return self.config.mechanistic_uptake if self.config else {}
    
    def get_nutrient_concentration_config(self) -> Dict[str, Any]:
        """Get nutrient concentration configuration."""
        return self.config.nutrient_concentration if self.config else {}
    
    def get_respiration_parameters(self) -> Dict[str, Any]:
        """Get respiration model parameters."""
        return self.config.respiration_model if self.config else {}
    
    def get_phenology_parameters(self) -> Dict[str, Any]:
        """Get phenology model parameters."""
        return self.config.phenology_model if self.config else {}
    
    def get_senescence_parameters(self) -> Dict[str, Any]:
        """Get senescence model parameters."""
        return self.config.senescence_model if self.config else {}
    
    def get_canopy_architecture_parameters(self) -> Dict[str, Any]:
        """Get canopy architecture model parameters."""
        return self.config.canopy_architecture if self.config else {}
    
    def get_nitrogen_balance_parameters(self) -> Dict[str, Any]:
        """Get nitrogen balance model parameters."""
        return self.config.nitrogen_balance if self.config else {}
    
    def get_nutrient_mobility_parameters(self) -> Dict[str, Any]:
        """Get nutrient mobility model parameters."""
        return self.config.nutrient_mobility if self.config else {}
    
    def get_temperature_stress_parameters(self) -> Dict[str, Any]:
        """Get temperature stress model parameters."""
        return self.config.temperature_stress if self.config else {}
    
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
        
        # Validate system config
        required_system_keys = ['system_id', 'tank_volume', 'flow_rate', 'system_area', 'n_plants']
        missing_system = [key for key in required_system_keys 
                         if key not in self.config.system_config]
        if missing_system:
            issues['system_config'] = [f'Missing required keys: {missing_system}']
        
        # Validate simulation settings
        sim_settings = self.config.simulation_settings
        if sim_settings.get('simulation_days', 0) <= 0:
            issues.setdefault('simulation_settings', []).append('simulation_days must be > 0')
        
        # Validate environmental control setpoints
        env_control = self.config.environmental_control.get('setpoints', {})
        if env_control.get('target_vpd', 0) <= 0:
            issues.setdefault('environmental_control', []).append('target_vpd must be > 0')
        
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
    return get_config_loader().get_value('default_values', key, default)


def get_rzt_parameter(key: str, default: Any = None) -> Any:
    """Get an RZT parameter from configuration."""
    return get_config_loader().get_value('root_zone_temperature', key, default)


def get_leaf_parameter(key: str, default: Any = None) -> Any:
    """Get a leaf development parameter from configuration."""
    return get_config_loader().get_value('leaf_development', key, default)


def get_root_architecture_parameter(key: str, default: Any = None) -> Any:
    """Get a root architecture parameter from configuration."""
    return get_config_loader().get_nested_value('root_architecture', 'parameters', key, default)


def get_root_uptake_parameter(key: str, default: Any = None) -> Any:
    """Get a root uptake parameter from configuration."""
    return get_config_loader().get_nested_value('root_architecture', 'uptake_parameters', key, default)


def get_genetic_parameter(key: str, default: Any = None) -> Any:
    """Get a genetic parameter from configuration."""
    return get_config_loader().get_value('genetic_parameters', key, default)


def get_cultivar_data(cultivar_id: str, default: Any = None) -> Any:
    """Get cultivar data from configuration."""
    return get_config_loader().get_nested_value('genetic_parameters', 'cultivar_database', cultivar_id, default)


def get_breeding_parameter(key: str, default: Any = None) -> Any:
    """Get a breeding parameter from configuration."""
    return get_config_loader().get_nested_value('genetic_parameters', 'breeding_parameters', key, default)


def get_environmental_setpoint(key: str, default: Any = None) -> Any:
    """Get an environmental control setpoint from configuration."""
    return get_config_loader().get_nested_value('environmental_control', 'setpoints', key, default)


def get_equipment_parameter(key: str, default: Any = None) -> Any:
    """Get an equipment parameter from configuration."""
    return get_config_loader().get_nested_value('environmental_control', 'equipment', key, default)


def get_pid_parameter(controller: str, key: str, default: Any = None) -> Any:
    """Get a PID controller parameter from configuration."""
    return get_config_loader().get_nested_value('environmental_control', 'pid_parameters', controller, {}).get(key, default)


if __name__ == "__main__":
    # Test configuration loading
    try:
        loader = get_config_loader()
        config = get_config()
        
        print("Configuration loaded successfully!")
        print(f"System ID: {config.system_config.get('system_id')}")
        print(f"Tank Volume: {config.system_config.get('tank_volume')} L")
        print(f"Target VPD: {get_environmental_setpoint('target_vpd')} kPa")
        print(f"Base Phyllochron: {get_leaf_parameter('base_phyllochron')} °C-day")
        
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
        