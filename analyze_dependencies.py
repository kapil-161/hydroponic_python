"""
Analyze simulator dependencies and generate topological sort
"""
from typing import Dict, List, Set

# Extract dependencies from all simulators (from grep results)
SIMULATOR_DEPENDENCIES = {
    'photosynthesis_simulator': ['canopy_architecture_simulator', 'stress_models', 'environmental_control', 'leaf_development_simulator'],
    'respiration_simulator': [],  # Need to check
    'biomass_allocation_simulator': [],  # Need to check
    'phenology_simulator': [],  # Need to check
    'stress_models': [],  # Need to check
    'water_uptake_simulator': [],  # Need to check
    'nutrient_models_simulator': [],  # Need to check
    'canopy_architecture_simulator': [],  # Need to check
    'ph_model_simulator': [],  # Need to check
    'root_system_simulator': [],  # Need to check
    'environmental_control': [],  # Need to check
    'genetic_parameters_simulator': [],  # Need to check
    'leaf_development_simulator': [],  # Need to check
    'nitrogen_balance_simulator': [],  # Need to check
    'root_zone_temperature_simulator': [],  # Need to check
    'senescence_simulator': []  # Need to check
}

def topological_sort(dependencies: Dict[str, List[str]]) -> List[str]:
    """
    Perform topological sort on simulator dependencies.
    Returns execution order where dependencies come before dependents.
    """
    # Build in-degree map
    in_degree = {node: 0 for node in dependencies.keys()}

    # Count incoming edges
    for node, deps in dependencies.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[node] += 1

    # Queue of nodes with no dependencies
    queue = [node for node, degree in in_degree.items() if degree == 0]
    result = []

    while queue:
        # Sort to ensure deterministic order when multiple nodes have same priority
        queue.sort()
        node = queue.pop(0)
        result.append(node)

        # Remove this node and update in-degrees
        for other_node, deps in dependencies.items():
            if node in deps and other_node not in result:
                in_degree[other_node] -= 1
                if in_degree[other_node] == 0:
                    queue.append(other_node)

    # Check for cycles
    if len(result) != len(dependencies):
        remaining = set(dependencies.keys()) - set(result)
        raise ValueError(f"Circular dependency detected. Remaining nodes: {remaining}")

    return result


if __name__ == '__main__':
    print("Analyzing simulator dependencies...")
    print(f"Total simulators: {len(SIMULATOR_DEPENDENCIES)}")

    # We need to extract actual dependencies from each file
    print("\nNeed to extract dependencies from each simulator file...")
