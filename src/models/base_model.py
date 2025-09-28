"""
Base Model Architecture for Hydroponic Simulation Models

Provides standardized interfaces and common functionality for all simulation models,
eliminating duplicate code and ensuring consistent behavior across the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum
import math
from datetime import datetime

class ParameterError(Exception):
    """Raised when required parameters are missing"""
    pass


def get_required_weather_param(weather_data: Dict[str, Any], param_name: str) -> float:
    """Get required weather parameter or raise error if missing"""
    if param_name not in weather_data or weather_data[param_name] is None:
        raise ParameterError(f"Required weather parameter '{param_name}' missing from weather data")
    return weather_data[param_name]


from src.utils.core_utils import (
    get_strict_param,
    ParameterAccessError,
    validate_parameter_range
)


class ModelState(Enum):
    """Standard model states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ModelValidationResult:
    """Result of model validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def add_error(self, message: str) -> None:
        """Add validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add validation warning."""
        self.warnings.append(message)


@dataclass
class DailyUpdateInput:
    """Standardized input structure for daily updates."""
    day: int
    date: datetime
    temperature: float
    humidity: float
    solar_radiation: float
    vpd: float
    co2_concentration: float
    environmental_conditions: Dict[str, float]
    plant_state: Dict[str, float]
    system_state: Dict[str, float]

    def validate(self) -> ModelValidationResult:
        """Validate input parameters."""
        result = ModelValidationResult(is_valid=True, errors=[], warnings=[])

        if self.day < 0:
            result.add_error("Day must be non-negative")

        # Temperature validation
        if not -50 <= self.temperature <= 60:
            result.add_error(f"Temperature {self.temperature}°C outside realistic range [-50, 60]")

        # Humidity validation
        if not 0 <= self.humidity <= 100:
            result.add_error(f"Humidity {self.humidity}% outside range [0, 100]")

        # Solar radiation validation
        if self.solar_radiation < 0:
            result.add_error("Solar radiation must be non-negative")
        if self.solar_radiation > 50:
            result.add_warning(f"Solar radiation {self.solar_radiation} MJ/m²/day is very high")

        # VPD validation
        if self.vpd < 0:
            result.add_error("VPD must be non-negative")
        if self.vpd > 8:
            result.add_warning(f"VPD {self.vpd} kPa is very high")

        # CO2 validation
        if not 200 <= self.co2_concentration <= 2000:
            result.add_warning(f"CO2 {self.co2_concentration} μmol/mol outside typical range [200, 2000]")

        return result


@dataclass
class DailyUpdateOutput:
    """Standardized output structure for daily updates."""
    model_name: str
    day: int
    success: bool
    primary_results: Dict[str, float]
    secondary_results: Dict[str, float]
    internal_state: Dict[str, Any]
    validation_result: Optional[ModelValidationResult]
    processing_time_ms: float

    def get_result(self, key: str, default: Any = None) -> Any:
        """Get result with fallback to secondary results."""
        return self.primary_results.get(key, self.secondary_results.get(key, default))


@runtime_checkable
class DailyUpdateProtocol(Protocol):
    """Protocol defining the daily update interface."""

    def daily_update(self, input_data: DailyUpdateInput) -> DailyUpdateOutput:
        """Perform daily model update."""
        ...

    def validate_input(self, input_data: DailyUpdateInput) -> ModelValidationResult:
        """Validate input data."""
        ...


class BaseHydroponicModel(ABC):
    """
    Abstract base class for all hydroponic simulation models.

    Provides common functionality and enforces consistent interfaces
    across all models in the simulation system.
    """

    def __init__(self, model_name: str, config: Any):
        """
        Initialize base model.

        Args:
            model_name: Unique identifier for this model
            config: Configuration object with model parameters

        Raises:
            ParameterAccessError: If required configuration is missing
        """
        self.model_name = model_name
        self.config = config
        self.state = ModelState.UNINITIALIZED
        self.day = 0
        self.initialization_errors: List[str] = []
        self.daily_history: List[DailyUpdateOutput] = []

        # Validate configuration exists
        if not config:
            raise ParameterAccessError(f"Configuration required for {model_name}")

        # Initialize model
        try:
            self._initialize_model()
            self.state = ModelState.INITIALIZED
        except Exception as e:
            self.state = ModelState.ERROR
            self.initialization_errors.append(str(e))
            raise

    @abstractmethod
    def _initialize_model(self) -> None:
        """Initialize model-specific parameters and state."""
        pass

    @abstractmethod
    def _perform_daily_update(self, input_data: DailyUpdateInput) -> Dict[str, Any]:
        """Perform model-specific daily calculations."""
        pass

    @abstractmethod
    def get_required_inputs(self) -> List[str]:
        """Return list of required input parameters."""
        pass

    @abstractmethod
    def get_output_variables(self) -> List[str]:
        """Return list of output variables produced by this model."""
        pass

    def validate_input(self, input_data: DailyUpdateInput) -> ModelValidationResult:
        """
        Validate input data for this model.

        Args:
            input_data: Daily update input data

        Returns:
            Validation result with errors and warnings
        """
        # Base validation
        result = input_data.validate()

        # Check required inputs
        required_inputs = self.get_required_inputs()
        for req_input in required_inputs:
            if req_input not in input_data.environmental_conditions and \
               req_input not in input_data.plant_state and \
               req_input not in input_data.system_state:
                if not hasattr(input_data, req_input):
                    result.add_error(f"Required input '{req_input}' missing")

        # Model-specific validation
        model_result = self._validate_model_inputs(input_data)
        result.errors.extend(model_result.errors)
        result.warnings.extend(model_result.warnings)
        if model_result.errors:
            result.is_valid = False

        return result

    def _validate_model_inputs(self, input_data: DailyUpdateInput) -> ModelValidationResult:
        """Override in subclasses for model-specific validation."""
        return ModelValidationResult(is_valid=True, errors=[], warnings=[])

    def daily_update(self, input_data: DailyUpdateInput) -> DailyUpdateOutput:
        """
        Standardized daily update method for all models.

        Args:
            input_data: Standardized daily input data

        Returns:
            Standardized daily output data

        Raises:
            ValueError: If model is not in valid state or input is invalid
        """
        import time
        start_time = time.time()

        # Validate state
        if self.state != ModelState.INITIALIZED and self.state != ModelState.RUNNING:
            raise ValueError(f"Model {self.model_name} not ready for updates. State: {self.state}")

        # Validate input
        validation_result = self.validate_input(input_data)
        if not validation_result.is_valid:
            return DailyUpdateOutput(
                model_name=self.model_name,
                day=input_data.day,
                success=False,
                primary_results={},
                secondary_results={},
                internal_state={},
                validation_result=validation_result,
                processing_time_ms=(time.time() - start_time) * 1000
            )

        try:
            self.state = ModelState.RUNNING
            self.day = input_data.day

            # Perform model-specific calculations
            results = self._perform_daily_update(input_data)

            # Separate primary and secondary results
            primary_results = {k: v for k, v in results.items() if k in self.get_output_variables()}
            secondary_results = {k: v for k, v in results.items() if k not in self.get_output_variables()}

            # Create output
            output = DailyUpdateOutput(
                model_name=self.model_name,
                day=input_data.day,
                success=True,
                primary_results=primary_results,
                secondary_results=secondary_results,
                internal_state=self._get_internal_state(),
                validation_result=validation_result,
                processing_time_ms=(time.time() - start_time) * 1000
            )

            # Store history
            self.daily_history.append(output)

            return output

        except Exception as e:
            self.state = ModelState.ERROR
            validation_result.add_error(f"Model execution failed: {str(e)}")

            return DailyUpdateOutput(
                model_name=self.model_name,
                day=input_data.day,
                success=False,
                primary_results={},
                secondary_results={},
                internal_state={},
                validation_result=validation_result,
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _get_internal_state(self) -> Dict[str, Any]:
        """Get internal model state for debugging. Override in subclasses."""
        return {
            "model_name": self.model_name,
            "state": self.state.value,
            "day": self.day
        }

    def reset_model(self) -> None:
        """Reset model to initial state."""
        self.day = 0
        self.daily_history.clear()
        self.state = ModelState.INITIALIZED
        self._reset_model_state()

    def _reset_model_state(self) -> None:
        """Reset model-specific state. Override in subclasses."""
        pass

    def get_parameter(self, category: str, parameter: str) -> Any:
        """Get parameter using strict validation."""
        return get_strict_param(self.config, category, parameter)

    def validate_parameter_range(self, value: float, min_val: float, max_val: float, param_name: str) -> None:
        """Validate parameter is within range."""
        validate_parameter_range(value, min_val, max_val, f"{self.model_name}.{param_name}")


class ModelRegistry:
    """Registry for managing model instances and dependencies."""

    def __init__(self):
        self.models: Dict[str, BaseHydroponicModel] = {}
        self.model_dependencies: Dict[str, List[str]] = {}
        self.update_order: List[str] = []

    def register_model(self, model: BaseHydroponicModel, dependencies: Optional[List[str]] = None) -> None:
        """Register a model with optional dependencies."""
        self.models[model.model_name] = model
        self.model_dependencies[model.model_name] = dependencies or []
        self._update_execution_order()

    def _update_execution_order(self) -> None:
        """Calculate topological order for model updates."""
        # Simple topological sort
        visited = set()
        temp_visited = set()
        order = []

        def visit(model_name: str):
            if model_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {model_name}")
            if model_name in visited:
                return

            temp_visited.add(model_name)
            for dep in self.model_dependencies.get(model_name, []):
                if dep in self.models:
                    visit(dep)
            temp_visited.remove(model_name)
            visited.add(model_name)
            order.append(model_name)

        for model_name in self.models.keys():
            if model_name not in visited:
                visit(model_name)

        self.update_order = order

    def update_all_models(self, input_data: DailyUpdateInput) -> Dict[str, DailyUpdateOutput]:
        """Update all models in dependency order."""
        results = {}

        for model_name in self.update_order:
            model = self.models[model_name]

            # Enhance input with results from dependency models
            enhanced_input = self._enhance_input_with_dependencies(
                input_data, results, model_name
            )

            # Update model
            output = model.daily_update(enhanced_input)
            results[model_name] = output

            # Check for failures
            if not output.success:
                print(f"Warning: Model {model_name} failed on day {input_data.day}")
                if output.validation_result:
                    for error in output.validation_result.errors:
                        print(f"  Error: {error}")

        return results

    def _enhance_input_with_dependencies(self,
                                       base_input: DailyUpdateInput,
                                       model_results: Dict[str, DailyUpdateOutput],
                                       current_model: str) -> DailyUpdateInput:
        """Enhance input data with results from dependency models."""
        enhanced_plant_state = base_input.plant_state.copy()
        enhanced_system_state = base_input.system_state.copy()
        enhanced_env = base_input.environmental_conditions.copy()

        # Add results from dependency models
        for dep_name in self.model_dependencies.get(current_model, []):
            if dep_name in model_results:
                dep_output = model_results[dep_name]
                if dep_output.success:
                    # Merge results into appropriate categories
                    for key, value in dep_output.primary_results.items():
                        if key.startswith('plant_'):
                            enhanced_plant_state[key] = value
                        elif key.startswith('system_'):
                            enhanced_system_state[key] = value
                        else:
                            enhanced_env[key] = value

        return DailyUpdateInput(
            day=base_input.day,
            date=base_input.date,
            temperature=base_input.temperature,
            humidity=base_input.humidity,
            solar_radiation=base_input.solar_radiation,
            vpd=base_input.vpd,
            co2_concentration=base_input.co2_concentration,
            environmental_conditions=enhanced_env,
            plant_state=enhanced_plant_state,
            system_state=enhanced_system_state
        )


# Utility functions for common model patterns

def create_daily_input(day: int, date: datetime, weather_data: Dict[str, float],
                      plant_data: Dict[str, float] = None,
                      system_data: Dict[str, float] = None) -> DailyUpdateInput:
    """Create standardized daily input from basic data."""
    return DailyUpdateInput(
        day=day,
        date=date,
        temperature=weather_data['temperature'],
        humidity=get_required_weather_param(weather_data, 'humidity'),
        solar_radiation=weather_data['solar_radiation'],
        vpd=get_required_weather_param(weather_data, 'vpd'),
        co2_concentration=get_required_weather_param(weather_data, 'co2'),
        environmental_conditions=weather_data,
        plant_state=plant_data or {},
        system_state=system_data or {}
    )


def validate_model_compatibility(model1: BaseHydroponicModel,
                               model2: BaseHydroponicModel) -> ModelValidationResult:
    """Check if two models are compatible (output/input matching)."""
    result = ModelValidationResult(is_valid=True, errors=[], warnings=[])

    model1_outputs = set(model1.get_output_variables())
    model2_inputs = set(model2.get_required_inputs())

    # Find potential connections
    connections = model1_outputs.intersection(model2_inputs)
    if not connections:
        result.add_warning(f"No direct connections found between {model1.model_name} and {model2.model_name}")

    return result