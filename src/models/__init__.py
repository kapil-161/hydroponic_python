"""Hydroponic Models Package"""

# Backwards-compat re-exports for unified root system
from .root_system_model import (
    RootType,
    HydroponicSystemType,
    RootCohort,
    RootZoneLayer,
    RootArchitectureParameters,
    RootArchitectureModel,
    create_lettuce_root_architecture_model,
    HydroponicRootZone,
    HydroponicRootSystem,
    HydroponicRootModel,
    RootUptakeParameters,
    EnhancedRootUptakeModel,
    create_enhanced_root_uptake_model,
)