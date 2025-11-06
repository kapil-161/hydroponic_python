"""
Analysis Helper Utilities

Helper functions and constants for analyzing simulation outputs.
"""

# Variables that are biologically expected to be zero or constant
# These should be excluded from constant variable analysis

EXPECTED_ZERO_VARIABLES = {
    'nitrogen_balance': [
        'amino_acid_uptake',  # Amino acids negligible in hydroponic lettuce
        'reproductive_nitrogen_allocation',  # Lettuce is in vegetative stage
        'total_nitrogen_remobilization',  # No remobilization in vegetative stage
    ],
    # Add other simulators' expected zero variables here as needed
}

EXPECTED_CONSTANT_VARIABLES = {
    'nitrogen_balance': [
        'photosynthetic_n_use_efficiency',  # Parameter from CSV (typically constant)
        'growth_n_use_efficiency',  # Parameter from CSV (typically constant)
        'luxury_uptake_factor',  # Hardcoded parameter (typically constant)
    ],
    # Add other simulators' expected constant variables here as needed
}


def get_expected_zero_variables(simulator_name: str = None) -> list:
    """
    Get list of variables that are biologically expected to be zero.
    
    Args:
        simulator_name: Name of simulator (e.g., 'nitrogen_balance'). 
                       If None, returns all expected zero variables.
    
    Returns:
        List of variable names that are expected to be zero.
    """
    if simulator_name:
        return EXPECTED_ZERO_VARIABLES.get(simulator_name, [])
    # Return all expected zero variables from all simulators
    all_vars = []
    for vars_list in EXPECTED_ZERO_VARIABLES.values():
        all_vars.extend(vars_list)
    return all_vars


def get_expected_constant_variables(simulator_name: str = None) -> list:
    """
    Get list of variables that are expected to be constant (parameters).
    
    Args:
        simulator_name: Name of simulator (e.g., 'nitrogen_balance'). 
                       If None, returns all expected constant variables.
    
    Returns:
        List of variable names that are expected to be constant.
    """
    if simulator_name:
        return EXPECTED_CONSTANT_VARIABLES.get(simulator_name, [])
    # Return all expected constant variables from all simulators
    all_vars = []
    for vars_list in EXPECTED_CONSTANT_VARIABLES.values():
        all_vars.extend(vars_list)
    return all_vars


def filter_expected_variables(variable_list: list, simulator_name: str = None) -> list:
    """
    Filter out expected zero and constant variables from a list.
    
    Args:
        variable_list: List of variable names to filter.
        simulator_name: Name of simulator to get expected variables for.
    
    Returns:
        Filtered list with expected zero and constant variables removed.
    """
    expected_zero = get_expected_zero_variables(simulator_name)
    expected_constant = get_expected_constant_variables(simulator_name)
    excluded = set(expected_zero + expected_constant)
    
    return [var for var in variable_list if var not in excluded]


def is_expected_zero(variable_name: str, simulator_name: str = None) -> bool:
    """
    Check if a variable is expected to be zero.
    
    Args:
        variable_name: Name of the variable to check.
        simulator_name: Name of simulator to check in.
    
    Returns:
        True if variable is expected to be zero, False otherwise.
    """
    expected_zero = get_expected_zero_variables(simulator_name)
    return variable_name in expected_zero


def is_expected_constant(variable_name: str, simulator_name: str = None) -> bool:
    """
    Check if a variable is expected to be constant.
    
    Args:
        variable_name: Name of the variable to check.
        simulator_name: Name of simulator to check in.
    
    Returns:
        True if variable is expected to be constant, False otherwise.
    """
    expected_constant = get_expected_constant_variables(simulator_name)
    return variable_name in expected_constant

