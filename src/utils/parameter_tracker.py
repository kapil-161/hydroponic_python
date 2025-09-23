"""
Parameter Usage Tracking System

This module tracks which parameters from CSV files are actually used during simulation
and which parameters are loaded but never accessed.
"""

import logging
from typing import Dict, Set, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ParameterUsageInfo:
    """Information about a parameter's usage during simulation."""
    parameter_name: str
    category: str
    value: Any
    accessed_count: int = 0
    first_access_day: Optional[int] = None
    last_access_day: Optional[int] = None
    access_locations: List[str] = field(default_factory=list)
    is_used: bool = False


class ParameterTracker:
    """
    Tracks parameter usage during simulation to identify used vs unused parameters.
    """
    
    def __init__(self):
        self.loaded_parameters: Dict[str, ParameterUsageInfo] = {}
        self.accessed_parameters: Set[str] = set()
        self.access_log: List[Dict[str, Any]] = []
        self.simulation_day: int = 0
        self.equation_parameters: Set[str] = set()  # Parameters used in equations
        self.model_initialization_params: Set[str] = set()  # Parameters used during model initialization
        
    def register_loaded_parameters(self, parameter_categories: Dict[str, Dict[str, Any]]):
        """
        Register all parameters loaded from CSV files.
        
        Args:
            parameter_categories: Dictionary of category -> {param_name: value}
        """
        self.loaded_parameters.clear()
        
        for category, params in parameter_categories.items():
            for param_name, param_value in params.items():
                full_name = f"{category}.{param_name}"
                self.loaded_parameters[full_name] = ParameterUsageInfo(
                    parameter_name=param_name,
                    category=category,
                    value=param_value
                )
        
        logger.info(f"Registered {len(self.loaded_parameters)} parameters for tracking")
    
    def track_access(self, param_name: str, category: str = None, location: str = "unknown"):
        """
        Track when a parameter is accessed during simulation.
        
        Args:
            param_name: Name of the parameter being accessed
            category: Category of the parameter (optional)
            location: Location/code where parameter was accessed
        """
        # Try different naming patterns
        possible_names = [
            param_name,
            f"{category}.{param_name}" if category else None,
            param_name.replace('_parameters', '').replace('_', ''),
        ]
        
        accessed = False
        for name in possible_names:
            if name and name in self.loaded_parameters:
                info = self.loaded_parameters[name]
                info.accessed_count += 1
                info.is_used = True
                info.first_access_day = info.first_access_day or self.simulation_day
                info.last_access_day = self.simulation_day
                
                if location not in info.access_locations:
                    info.access_locations.append(location)
                
                self.accessed_parameters.add(name)
                accessed = True
                break
        
        # Log the access
        self.access_log.append({
            'day': self.simulation_day,
            'parameter': param_name,
            'category': category,
            'location': location,
            'found': accessed
        })
        
        if not accessed:
            logger.debug(f"Parameter '{param_name}' accessed but not found in loaded parameters")
    
    def set_simulation_day(self, day: int):
        """Set the current simulation day for tracking."""
        self.simulation_day = day
    
    def track_equation_parameters(self, param_names: List[str], equation_name: str = "unknown"):
        """
        Track parameters used in equations or calculations.
        
        Args:
            param_names: List of parameter names used in the equation
            equation_name: Name/description of the equation or calculation
        """
        for param_name in param_names:
            self.equation_parameters.add(param_name)
            self.track_access(param_name, location=f"equation_{equation_name}")
    
    def track_model_initialization(self, param_names: List[str], model_name: str = "unknown"):
        """
        Track parameters used during model initialization.
        
        Args:
            param_names: List of parameter names used during initialization
            model_name: Name of the model being initialized
        """
        for param_name in param_names:
            self.model_initialization_params.add(param_name)
            self.track_access(param_name, location=f"init_{model_name}")
    
    def track_parameter_usage_in_dict(self, param_dict: Dict[str, Any], category: str, usage_context: str = "dict_access"):
        """
        Track all parameters accessed from a dictionary.
        
        Args:
            param_dict: Dictionary containing parameters
            category: Category of parameters
            usage_context: Context where parameters are used
        """
        for param_name in param_dict.keys():
            self.track_access(param_name, category, usage_context)
    
    def get_usage_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive usage report.
        
        Returns:
            Dictionary containing usage statistics and lists of used/unused parameters
        """
        used_params = []
        unused_params = []
        
        for full_name, info in self.loaded_parameters.items():
            if info.is_used:
                used_params.append({
                    'name': info.parameter_name,
                    'category': info.category,
                    'value': info.value,
                    'access_count': info.accessed_count,
                    'first_access_day': info.first_access_day,
                    'last_access_day': info.last_access_day,
                    'access_locations': info.access_locations
                })
            else:
                unused_params.append({
                    'name': info.parameter_name,
                    'category': info.category,
                    'value': info.value
                })
        
        # Group by category
        used_by_category = defaultdict(list)
        unused_by_category = defaultdict(list)
        
        for param in used_params:
            used_by_category[param['category']].append(param)
        
        for param in unused_params:
            unused_by_category[param['category']].append(param)
        
        return {
            'summary': {
                'total_loaded': len(self.loaded_parameters),
                'total_used': len(used_params),
                'total_unused': len(unused_params),
                'usage_percentage': (len(used_params) / len(self.loaded_parameters) * 100) if self.loaded_parameters else 0,
                'equation_parameters': len(self.equation_parameters),
                'initialization_parameters': len(self.model_initialization_params)
            },
            'used_parameters': used_params,
            'unused_parameters': unused_params,
            'used_by_category': dict(used_by_category),
            'unused_by_category': dict(unused_by_category),
            'equation_parameters': list(self.equation_parameters),
            'initialization_parameters': list(self.model_initialization_params),
            'access_log': self.access_log
        }
    
    def print_usage_report(self, detailed: bool = False):
        """
        Print a formatted usage report to console.
        
        Args:
            detailed: If True, show detailed information including access locations
        """
        report = self.get_usage_report()
        
        print("\n" + "="*60)
        print("📊 PARAMETER USAGE REPORT")
        print("="*60)
        
        # Summary statistics
        summary = report['summary']
        print(f"📈 SUMMARY:")
        print(f"   Total parameters loaded: {summary['total_loaded']}")
        print(f"   Parameters used: {summary['total_used']}")
        print(f"   Parameters unused: {summary['total_unused']}")
        print(f"   Usage percentage: {summary['usage_percentage']:.1f}%")
        print(f"   Parameters used in equations: {summary['equation_parameters']}")
        print(f"   Parameters used in model initialization: {summary['initialization_parameters']}")
        
        # Used parameters by category
        print(f"\n✅ USED PARAMETERS ({summary['total_used']}):")
        for category, params in report['used_by_category'].items():
            print(f"   📁 {category} ({len(params)} parameters):")
            for param in params:
                if detailed:
                    locations = ", ".join(param['access_locations'][:3])  # Show first 3 locations
                    if len(param['access_locations']) > 3:
                        locations += f" (+{len(param['access_locations'])-3} more)"
                    print(f"      • {param['name']} (accessed {param['access_count']} times, locations: {locations})")
                else:
                    print(f"      • {param['name']} (accessed {param['access_count']} times)")
        
        # Unused parameters by category
        print(f"\n❌ UNUSED PARAMETERS ({summary['total_unused']}):")
        for category, params in report['unused_by_category'].items():
            print(f"   📁 {category} ({len(params)} parameters):")
            for param in params:
                print(f"      • {param['name']} = {param['value']}")
        
        # Recommendations
        if summary['total_unused'] > 0:
            print(f"\n💡 RECOMMENDATIONS:")
            print(f"   • Consider removing {summary['total_unused']} unused parameters to simplify calibration")
            print(f"   • Review unused parameters to ensure they're not needed for model accuracy")
            print(f"   • Consolidate parameters with similar names or functionality")
        
        print("="*60)


class TrackedSystemConfig:
    """
    A wrapper around system_config that tracks parameter access.
    """
    
    def __init__(self, original_config, parameter_tracker: ParameterTracker):
        self._original_config = original_config
        self._tracker = parameter_tracker
        # Store tracker reference for model initialization tracking
        self._tracker = parameter_tracker
    
    def __getattr__(self, name):
        """Intercept attribute access to track parameter usage."""
        # Get the original attribute
        attr = getattr(self._original_config, name)
        
        # If it's a dictionary (parameter category), wrap it
        if isinstance(attr, dict):
            return TrackedParameterDict(attr, name, self._tracker)
        
        return attr
    
    def __setattr__(self, name, value):
        """Set attributes, excluding our internal attributes."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            setattr(self._original_config, name, value)


class TrackedParameterDict:
    """
    A wrapper around parameter dictionaries that tracks access to individual parameters.
    """
    
    def __init__(self, original_dict: Dict[str, Any], category: str, tracker: ParameterTracker):
        self._original_dict = original_dict
        self._category = category
        self._tracker = tracker
    
    def __getitem__(self, key):
        """Track access to individual parameters."""
        self._tracker.track_access(key, self._category, "dict_access")
        return self._original_dict[key]
    
    def __setitem__(self, key, value):
        """Allow setting values."""
        self._original_dict[key] = value
    
    def __contains__(self, key):
        """Check if key exists."""
        return key in self._original_dict
    
    def __iter__(self):
        """Iterate over keys."""
        return iter(self._original_dict)
    
    def __len__(self):
        """Get length."""
        return len(self._original_dict)
    
    def keys(self):
        """Get keys."""
        return self._original_dict.keys()
    
    def values(self):
        """Get values."""
        return self._original_dict.values()
    
    def items(self):
        """Get items."""
        return self._original_dict.items()
    
    def get(self, key, default=None):
        """Get with default, tracking access."""
        if key in self._original_dict:
            self._tracker.track_access(key, self._category, "dict_get")
            return self._original_dict[key]
        return default
    
    def copy(self):
        """Create a copy of the dictionary."""
        return self._original_dict.copy()
    
    def update(self, other):
        """Update dictionary with another dictionary."""
        self._original_dict.update(other)
    
    def pop(self, key, default=None):
        """Pop item from dictionary."""
        return self._original_dict.pop(key, default)
    
    def clear(self):
        """Clear dictionary."""
        self._original_dict.clear()