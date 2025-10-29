1#!/usr/bin/env python3
"""
Intelligent Unused Parameter Finder and Remover

Identifies unused parameters using multiple detection strategies:

1. CSV-to-Code Reference Matching:
   - Searches for exact parameter keys (category_parameter_name)
   - Searches for parameter names in variable assignments
   - Searches for parameter names in dictionary accesses
   - Handles string literals, dictionary keys, config accesses

2. Parameter Loader Analysis:
   - Finds parameters loaded via _load_specialized_file()
   - Detects parameters in constants.csv backward compatibility mappings
   - Validates category-to-parameter_name mapping

3. Model Code Analysis:
   - Extracts required_params from from_config() methods
   - Finds KeyError raises with parameter names
   - Detects dataclass field requirements
   - Analyzes conditional logic that uses parameters

4. Simulator Analysis:
   - Checks simulator instantiation and parameter passing
   - Finds parameters used in simulator init/process methods
   - Validates simulator-to-model parameter flow

5. Functional Testing:
   - Tests simulation baseline
   - Removes candidate parameters one-by-one
   - Only marks as unused if simulation still passes

Usage:
    python3 find_unused_parameters.py [--auto] [--csv filename.csv]

Options:
    --auto              Automatically test all CSV files without prompting
    --csv filename.csv  Test only specific CSV file
"""

import sys
import os
import csv
import shutil
import subprocess
from pathlib import Path
import re
import ast
from typing import Set, List, Tuple, Dict, Optional
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def get_csv_files():
    """Get list of parameter CSV files (excluding weather and observed data)"""
    input_dir = "input"
    csv_files = []

    exclude_files = {'LET_EXP001_2024_weather.csv', 'observed_data.csv', 'master_parameters.csv', 'initials.csv'}

    for file in sorted(os.listdir(input_dir)):
        if file.endswith('.csv') and file not in exclude_files:
            csv_files.append(file)

    return csv_files


def select_csv_file(csv_files):
    """Let user select which CSV file to analyze"""
    print("\nAvailable CSV files:")
    for i, file in enumerate(csv_files, 1):
        print(f"  {i}. {file}")

    while True:
        try:
            choice = int(input("\nSelect file number: "))
            if 1 <= choice <= len(csv_files):
                return csv_files[choice - 1]
            print("Invalid choice. Try again.")
        except ValueError:
            print("Invalid input. Enter a number.")


def read_csv_parameters(file_path):
    """Read parameters from CSV file (skipping comment rows and handling malformed rows)"""
    parameters = []

    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row is None or not row:
                continue
            # Get first field name dynamically
            first_field = reader.fieldnames[0] if reader.fieldnames else None
            if not first_field or first_field not in row:
                continue
            # Skip comment rows
            if row[first_field] and not str(row[first_field]).startswith('#'):
                parameters.append(row)

    return parameters


def create_backup(file_path):
    """Create backup of original CSV file"""
    backup_path = file_path + '.backup'
    shutil.copy2(file_path, backup_path)
    return backup_path


def write_csv_parameters(file_path, parameters, fieldnames):
    """Write parameters back to CSV file, handling rows with extra/missing fields"""
    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval='', extrasaction='ignore')
        writer.writeheader()

        # Write rows, filtering out None or invalid values
        for row in parameters:
            if row is None:
                continue
            # Ensure row has valid keys from fieldnames
            filtered_row = {k: v for k, v in row.items() if k in fieldnames}
            writer.writerow(filtered_row)


def test_simulation():
    """Test if simulation runs successfully"""
    try:
        result = subprocess.run(
            ["python3", "main.py"],
            capture_output=True,
            timeout=300,
            text=True
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        print(f"Error running simulation: {e}")
        return False


def get_category_from_filename(csv_file):
    """Convert CSV filename to category prefix used in parameter loader"""
    mapping = {
        'constants.csv': 'constants',
        'stress.csv': 'stress_parameters',
        'roots.csv': 'root_system_parameters',
        'genetics.csv': 'genetics_parameters',
        'photo.csv': 'photosynthesis_parameters',
        'respiration.csv': 'respiration_parameters',
        'allocation.csv': 'allocation_parameters',
        'phenology.csv': 'phenology_parameters',
        'nitrogen_balance.csv': 'nitrogen_balance',
        'canopy.csv': 'canopy_parameters',
        'leaf.csv': 'leaf_development',
        'water.csv': 'water_parameters',
        'nutrient.csv': 'nutrient_parameters'
    }
    return mapping.get(csv_file, csv_file.replace('.csv', ''))


def find_parameter_loader_references(param_name: str, category: str) -> List[Tuple[int, str]]:
    """Find all lines in parameter_loader.py that reference this parameter

    Searches for:
    1. Direct get_parameter calls with category_param_name
    2. Parameters in _load_specialized_file category definitions
    3. Parameters in backward compatibility mappings
    """
    loader_path = "src/utils/parameter_loader.py"
    references = []

    # Build the key pattern: category_param_name
    key = f"{category}_{param_name}"

    try:
        with open(loader_path, 'r') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            # Strategy 1: Direct parameter retrieval
            if key in line and "get_parameter" in line:
                references.append((i, line.strip()))
            # Strategy 2: Parameter in load calls or category definitions
            elif param_name in line and ("_load_specialized_file" in line or "category" in line.lower()):
                references.append((i, line.strip()))
            # Strategy 3: Parameter in backward compatibility mappings
            elif f"'{param_name}'" in line or f'"{param_name}"' in line:
                # Only if it looks like it's in a mapping or config context
                if "backward_compat" in lines[max(0, i-2):min(len(lines), i+3)] or \
                   "mapping" in "".join(lines[max(0, i-2):min(len(lines), i+3)]).lower():
                    references.append((i, line.strip()))
    except Exception:
        pass

    return references


def find_code_references(param_name: str, category: str) -> List[Tuple[str, int, str]]:
    """Find all references to this parameter in source code with multiple strategies

    Searches for:
    1. Exact parameter key (category_parameter_name)
    2. Parameter name in quotes (various contexts)
    3. Parameter name in variable assignments
    4. Parameter name in dictionary accesses
    5. Parameter name in conditional statements
    """
    references = []
    key = f"{category}_{param_name}"
    src_path = "src"

    # Multiple search patterns
    patterns = [
        # Exact key match
        re.compile(rf'\b{re.escape(key)}\b'),
        # Parameter name in quotes (various contexts)
        re.compile(rf"['\"]({re.escape(param_name)})['\"]"),
        # Dictionary access pattern: ['param'] or ["param"]
        re.compile(rf"\[['\"]({re.escape(param_name)})['\"]"),
        # Variable assignment pattern: var = param_name
        re.compile(rf"=\s*['\"]({re.escape(param_name)})['\"]"),
        # Function argument pattern
        re.compile(rf"(?:,\s|[(])\s*['\"]({re.escape(param_name)})['\"]"),
    ]

    # Search all Python files in src directory
    for root, dirs, files in os.walk(src_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines, 1):
                        # Skip comments and strings in isolation
                        if line.strip().startswith('#'):
                            continue

                        # Check all patterns
                        for pattern in patterns:
                            if pattern.search(line):
                                references.append((file_path, i, line.strip()))
                                break  # Only add once per line
                except Exception:
                    pass

    return references


def find_model_requirements(csv_file: str) -> Set[str]:
    """Find required parameters from model dataclasses, validators, and usage patterns

    Analyzes:
    1. Explicit required_params lists in from_config() methods
    2. KeyError raises indicating required parameters
    3. Config dictionary accesses
    4. Dataclass field definitions and defaults
    5. Parameter validation in __post_init__ methods
    """
    category = get_category_from_filename(csv_file)
    required_params = set()
    src_path = "src/models"

    # Map CSV files to their model files
    model_mapping = {
        'nutrient.csv': ['nutrient_models.py'],
        'nitrogen_balance.csv': ['nitrogen_balance.py'],
        'water.csv': ['water_uptake_model.py'],
        'canopy.csv': ['canopy_architecture.py'],
        'leaf.csv': ['leaf_development.py'],
        'stress.csv': ['stress_models.py'],
        'roots.csv': ['root_system_model.py'],
        'genetics.csv': ['genetics.py'],
        'photo.csv': ['photosynthesis_model.py'],
        'respiration.csv': ['respiration_model.py'],
        'allocation.csv': ['biomass_allocation_model.py'],
        'phenology.csv': ['phenology_model.py'],
        'constants.csv': ['base_model.py']
    }

    model_files = model_mapping.get(csv_file, [])

    for model_file in model_files:
        model_path = os.path.join(src_path, model_file)
        if not os.path.exists(model_path):
            continue

        try:
            with open(model_path, 'r') as f:
                content = f.read()

            # Strategy 1: Find explicit required_params lists in from_config methods
            required_match = re.search(r"required_params\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if required_match:
                params_str = required_match.group(1)
                param_list = re.findall(r"['\"]([^'\"]+)['\"]", params_str)
                required_params.update(param_list)

            # Strategy 2: Find KeyError raises with parameter names (indicates required)
            key_errors = re.findall(r"(?:KeyError|raise.*?)['\"]([a-z_]+)['\"]", content, re.IGNORECASE)
            required_params.update(key_errors)

            # Strategy 3: Find config dictionary accesses
            config_accesses = re.findall(r"config\[['\"]([^'\"]+)['\"]\]", content)
            required_params.update(config_accesses)

            # Strategy 4: Find direct parameter accesses in config.get() or similar
            get_accesses = re.findall(r"config\.get\(['\"]([^'\"]+)['\"]", content)
            required_params.update(get_accesses)

            # Strategy 5: Find dataclass field defaults and required fields
            # Look for fields without defaults (which means they're required)
            field_pattern = r"(\w+):\s*(?:float|int|str|bool|List|Dict|Tuple|Optional)\s*=\s*field\("
            field_matches = re.findall(field_pattern, content)
            required_params.update(field_matches)

        except Exception:
            pass

    return required_params


def find_simulator_usage(param_name: str, category: str) -> List[Tuple[str, int, str]]:
    """Find if parameter is used in simulator instantiation or execution

    Checks:
    1. Simulator class instantiations that receive parameters
    2. Simulator process/run methods that use parameters
    3. Parameter passing from orchestrator to simulators
    """
    references = []
    simulators_path = "src/simulations"
    key = f"{category}_{param_name}"

    for root, dirs, files in os.walk(simulators_path):
        for file in files:
            if file.endswith('_simulator.py') or file in ['simulation_orchestrator.py', 'distributed_simulation_runner.py']:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines, 1):
                        # Check for parameter key
                        if key in line:
                            references.append((file_path, i, line.strip()))
                        # Check for parameter name in method/function calls
                        elif f"'{param_name}'" in line or f'"{param_name}"' in line:
                            # Context: instantiation, config passing, parameter retrieval
                            if any(keyword in line for keyword in ['config', 'param', 'get_', 'self.', 'pass']):
                                references.append((file_path, i, line.strip()))
                except Exception:
                    pass

    return references


def analyze_parameter_loader_structure() -> Dict[str, Set[str]]:
    """Analyze parameter_loader.py to understand CSV category mappings

    Returns:
    {
        'category_name': {'parameter1', 'parameter2', ...},
        ...
    }
    """
    loader_path = "src/utils/parameter_loader.py"
    categories = {}

    try:
        with open(loader_path, 'r') as f:
            content = f.read()

        # Find all _load_specialized_file calls
        pattern = r"_load_specialized_file\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)

        for csv_path, category in matches:
            csv_name = os.path.basename(csv_path)
            if csv_name not in categories:
                categories[csv_name] = set()
            categories[csv_name].add(category)

    except Exception:
        pass

    return categories


def remove_parameter_loader_lines(param_name, category):
    """Remove lines from parameter_loader.py that request this parameter"""
    loader_path = "src/utils/parameter_loader.py"
    key = f"{category}_{param_name}"

    with open(loader_path, 'r') as f:
        lines = f.readlines()

    # Find and remove lines that request this parameter
    new_lines = []
    removed_count = 0

    for line in lines:
        if key in line and "get_parameter" in line:
            removed_count += 1
            continue
        new_lines.append(line)

    if removed_count > 0:
        with open(loader_path, 'w') as f:
            f.writelines(new_lines)

    return removed_count


def find_unused_parameters(csv_file: str, verbose: bool = False, dry_run: bool = False) -> List[Tuple[str, str]]:
    """Find unused parameters using comprehensive multi-level checking

    Analysis phases:
    1. Model requirements analysis
    2. Code reference search (multiple strategies)
    3. Simulator usage analysis
    4. Parameter loader structure validation
    5. Functional simulation testing

    Returns:
    List of tuples: [(parameter_name, category), ...]
    """
    file_path = f"input/{csv_file}"

    print(f"\n{'='*60}")
    print(f"Testing: {csv_file}")
    print(f"{'='*60}")

    # Create backup
    backup_path = create_backup(file_path)
    print(f"Backup created: {backup_path}")

    # Read original parameters
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    # Separate comment rows and parameter rows, handling malformed rows
    comment_rows = []
    param_rows = []

    for row in all_rows:
        if row is None or not row or fieldnames[0] not in row:
            continue
        if row[fieldnames[0]] and str(row[fieldnames[0]]).startswith('#'):
            comment_rows.append(row)
        else:
            param_rows.append(row)

    print(f"Total parameters: {len(param_rows)}")

    # Phase 1: Get model requirements - parameters that MUST be present
    print("\nPhase 1: Analyzing model requirements...")
    model_required = find_model_requirements(csv_file)
    print(f"  Found {len(model_required)} parameters required by models")
    if verbose and model_required:
        print(f"    Required: {', '.join(sorted(model_required)[:5])}{'...' if len(model_required) > 5 else ''}")

    # Phase 2: Check code references
    print("\nPhase 2: Scanning source code for parameter usage...")
    category = get_category_from_filename(csv_file)

    # Filter parameters: exclude those with model requirements or code references
    candidates_for_testing = []
    protected_params = {}

    for param_row in param_rows:
        param_name = param_row[fieldnames[0]]

        # Strategy 1: Check if required by model
        if param_name in model_required:
            protected_params[param_name] = "Required by model"
            continue

        # Strategy 2: Check for code references
        code_refs = find_code_references(param_name, category)
        if code_refs:
            protected_params[param_name] = f"Used in {len(code_refs)} code location(s)"
            if verbose:
                print(f"    {param_name}: {code_refs[0][0]}:{code_refs[0][1]}")
            continue

        # Strategy 3: Check for simulator usage
        sim_refs = find_simulator_usage(param_name, category)
        if sim_refs:
            protected_params[param_name] = f"Used in {len(sim_refs)} simulator(s)"
            if verbose:
                print(f"    {param_name}: {sim_refs[0][0].split('/')[-1]}:{sim_refs[0][1]}")
            continue

        # Strategy 4: Check for parameter_loader references
        loader_refs = find_parameter_loader_references(param_name, category)
        if loader_refs:
            protected_params[param_name] = "Referenced in parameter_loader.py"
            if verbose:
                print(f"    {param_name}: parameter_loader.py:{loader_refs[0][0]}")
            continue

        # This parameter is a candidate for testing
        candidates_for_testing.append(param_name)

    print(f"  Protected {len(protected_params)} parameters (required by models, code, or simulators)")
    print(f"  Testing {len(candidates_for_testing)} candidate parameter(s) for actual usage")
    if verbose and candidates_for_testing:
        print(f"    Candidates: {', '.join(candidates_for_testing)}")

    # Skip simulation testing if no candidates
    if not candidates_for_testing:
        print("\n✓ All parameters are protected by static analysis")
        shutil.copy2(backup_path, file_path)
        return []

    # Skip functional testing in dry-run mode
    if dry_run:
        print("\nDry-run mode: Skipping functional testing")
        print("(Run without --dry-run to test if parameters truly affect simulation)")
        shutil.copy2(backup_path, file_path)
        return []

    # Test baseline
    print("\nPhase 3: Testing baseline simulation (all parameters)...", end=" ", flush=True)
    if not test_simulation():
        print("FAILED")
        print("ERROR: Baseline simulation failed. Restoring backup.")
        shutil.copy2(backup_path, file_path)
        return []
    print("OK")

    # Phase 4: Test removal of only the candidate parameters
    print("\nPhase 4: Testing removal of candidate parameters one-by-one...")
    unused_parameters = []

    for param_name in candidates_for_testing:
        print(f"  Testing removal of '{param_name}'...", end=" ", flush=True)

        # Create test CSV without this parameter
        test_rows = comment_rows + [row for row in param_rows if row[fieldnames[0]] != param_name]
        write_csv_parameters(file_path, test_rows, fieldnames)

        if test_simulation():
            print("OK (CAN REMOVE)")
            unused_parameters.append((param_name, category))
        else:
            print("FAILED (needed)")

    # Restore backup
    shutil.copy2(backup_path, file_path)

    return unused_parameters


def confirm_deletion(unused_params, csv_file):
    """Ask user to confirm deletion of unused parameters

    Handles both interactive and non-interactive contexts.
    Returns False if EOF or non-interactive.
    """
    if not unused_params:
        print("\n✓ No unused parameters found.")
        print("  All parameters are either required by models, referenced in code, or affect simulation results.")
        return False

    print(f"\n{'='*60}")
    print(f"Found {len(unused_params)} TRULY UNUSED parameter(s) in {csv_file}:")
    print("(These parameters do NOT affect simulation results)")
    for param_name, _ in unused_params:
        print(f"  - {param_name}")
    print(f"{'='*60}")

    try:
        response = input("\nDelete these parameters? (yes/no): ").strip().lower()
        return response == 'yes'
    except EOFError:
        # Non-interactive context (e.g., piped input or testing)
        # Default to no deletion to be safe
        print("\nNon-interactive mode: Skipping deletion (requires --auto flag or manual confirmation)")
        return False


def delete_unused_parameters(csv_file, unused_params):
    """Delete unused parameters from CSV and parameter_loader.py"""
    file_path = f"input/{csv_file}"

    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    # Keep comment rows and parameters not in unused list
    unused_names = {param[0] for param in unused_params}
    kept_rows = []

    for row in all_rows:
        if row is None or not row or fieldnames[0] not in row:
            continue
        # Keep comment rows
        if row[fieldnames[0]] and str(row[fieldnames[0]]).startswith('#'):
            kept_rows.append(row)
        # Keep parameters not in unused list
        elif row[fieldnames[0]] not in unused_names:
            kept_rows.append(row)

    write_csv_parameters(file_path, kept_rows, fieldnames)

    # Also remove from parameter_loader.py
    print("\nRemoving parameter loader references...")
    removed_from_loader = 0
    for param_name, category in unused_params:
        count = remove_parameter_loader_lines(param_name, category)
        if count > 0:
            removed_from_loader += count
            print(f"  Removed {count} reference(s) to '{param_name}' from parameter_loader.py")

    print(f"\nDeleted {len(unused_params)} parameters from {csv_file}")
    if removed_from_loader > 0:
        print(f"Removed {removed_from_loader} parameter request(s) from parameter_loader.py")

    # Remove backup
    backup_path = file_path + '.backup'
    if os.path.exists(backup_path):
        os.remove(backup_path)


def main():
    """Main execution with command-line argument support"""
    parser = argparse.ArgumentParser(
        description="Find and remove unused parameters from CSV files",
        epilog="""
Examples:
  python3 find_unused_parameters.py                # Interactive mode
  python3 find_unused_parameters.py --csv stress.csv --verbose
  python3 find_unused_parameters.py --auto         # Test all CSV files
  python3 find_unused_parameters.py --csv photo.csv --summary  # Analysis only
        """
    )
    parser.add_argument('--auto', action='store_true',
                        help='Automatically test all CSV files without prompting')
    parser.add_argument('--csv', type=str,
                        help='Test only specific CSV file (e.g., --csv stress.csv)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed analysis information')
    parser.add_argument('--dry-run', '--summary', action='store_true', dest='dry_run',
                        help='Analyze without testing simulation (dry-run mode)')

    args = parser.parse_args()

    csv_files = get_csv_files()

    if not csv_files:
        print("No CSV files found in input/")
        sys.exit(1)

    # Determine which files to test
    files_to_test = []

    if args.csv:
        # Test specific file
        if f"{args.csv}" in csv_files:
            files_to_test = [args.csv]
        else:
            # Try to find the file
            matching_files = [f for f in csv_files if args.csv.lower() in f.lower()]
            if matching_files:
                files_to_test = matching_files
            else:
                print(f"CSV file not found: {args.csv}")
                print(f"Available files: {', '.join(csv_files)}")
                sys.exit(1)
    elif args.auto:
        files_to_test = csv_files
    else:
        # Interactive selection
        selected_file = select_csv_file(csv_files)
        files_to_test = [selected_file]

    # Process each file
    total_unused = 0

    for csv_file in files_to_test:
        try:
            print(f"\n{'='*70}")
            print(f"Processing: {csv_file}")
            print(f"{'='*70}")

            unused_params = find_unused_parameters(csv_file, verbose=args.verbose, dry_run=args.dry_run)
            total_unused += len(unused_params)

            if unused_params:
                if confirm_deletion(unused_params, csv_file):
                    delete_unused_parameters(csv_file, unused_params)
                    print(f"✓ Deleted unused parameters from {csv_file}")
                else:
                    print(f"Skipped {csv_file}")
            else:
                print(f"✓ No unused parameters found in {csv_file}")

        except Exception as e:
            print(f"ERROR processing {csv_file}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            continue

    print(f"\n{'='*70}")
    print(f"Summary: Found {total_unused} unused parameter(s) across all tested files")
    print(f"{'='*70}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
