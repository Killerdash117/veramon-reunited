"""
Veramon Data Validation Tool
Created: April 21, 2025

This script validates the consolidated Veramon data to ensure consistency and completeness.
It checks for required fields, type correctness, and other data integrity issues.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

# Define the required fields and their expected types
REQUIRED_FIELDS = {
    "name": str,
    "type": list,
    "rarity": str,
    "catch_rate": float,
    "shiny_rate": float,
    "base_stats": dict,
    "biomes": list,
    "flavor": str,
    "abilities": list
}

# Optional fields and their expected types
OPTIONAL_FIELDS = {
    "evolution": dict
}

# Valid values for enum-like fields
VALID_VALUES = {
    "rarity": [
        "common", "uncommon", "rare", "legendary", "mythic"
    ],
    "type": [
        "Fire", "Water", "Grass", "Electric", "Ice", "Fighting", "Poison", 
        "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", 
        "Dark", "Steel", "Fairy", "Normal"
    ]
}

# Required fields for nested objects
NESTED_REQUIRED_FIELDS = {
    "base_stats": {
        "hp": int,
        "atk": int,
        "def": int,
        "sp_atk": int, 
        "sp_def": int,
        "speed": int
    },
    "evolution": {
        "evolves_to": str,
        "level_required": int
    }
}

def validate_veramon_data(data_path: str) -> Tuple[bool, List[str]]:
    """
    Validate the Veramon data file.
    
    Args:
        data_path: Path to the Veramon data file
        
    Returns:
        Tuple containing:
        - Boolean indicating whether validation passed
        - List of error messages
    """
    # Load the data
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Error loading data file: {e}"]
    
    # Validate the data
    errors = []
    veramon_names = set()
    evolution_targets = set()
    
    for veramon_id, veramon_data in data.items():
        # Check if the key matches the name field
        if "name" in veramon_data and veramon_id != veramon_data["name"]:
            errors.append(f"Veramon {veramon_id}: Key doesn't match name field ({veramon_data.get('name')})")
        
        # Keep track of names for evolution validation
        if "name" in veramon_data:
            veramon_names.add(veramon_data["name"])
        
        # Keep track of evolution targets
        if "evolution" in veramon_data and "evolves_to" in veramon_data["evolution"]:
            evolution_targets.add(veramon_data["evolution"]["evolves_to"])
        
        # Check required fields
        for field, expected_type in REQUIRED_FIELDS.items():
            if field not in veramon_data:
                errors.append(f"Veramon {veramon_id}: Missing required field '{field}'")
            elif not isinstance(veramon_data[field], expected_type):
                errors.append(f"Veramon {veramon_id}: Field '{field}' has wrong type. Expected {expected_type.__name__}, got {type(veramon_data[field]).__name__}")
        
        # Check optional fields if present
        for field, expected_type in OPTIONAL_FIELDS.items():
            if field in veramon_data and not isinstance(veramon_data[field], expected_type):
                errors.append(f"Veramon {veramon_id}: Field '{field}' has wrong type. Expected {expected_type.__name__}, got {type(veramon_data[field]).__name__}")
        
        # Check valid values for enum-like fields
        for field, valid_values in VALID_VALUES.items():
            if field in veramon_data:
                if field == "type":
                    for type_value in veramon_data[field]:
                        if type_value not in valid_values:
                            errors.append(f"Veramon {veramon_id}: Invalid '{field}' value '{type_value}'. Valid values: {', '.join(valid_values)}")
                elif veramon_data[field] not in valid_values:
                    errors.append(f"Veramon {veramon_id}: Invalid '{field}' value '{veramon_data[field]}'. Valid values: {', '.join(valid_values)}")
        
        # Check nested fields
        for parent_field, required_subfields in NESTED_REQUIRED_FIELDS.items():
            if parent_field in veramon_data:
                for subfield, expected_type in required_subfields.items():
                    if parent_field == "evolution" and parent_field in veramon_data:
                        if subfield not in veramon_data[parent_field]:
                            errors.append(f"Veramon {veramon_id}: Missing required subfield '{parent_field}.{subfield}'")
                        elif not isinstance(veramon_data[parent_field][subfield], expected_type):
                            errors.append(f"Veramon {veramon_id}: Subfield '{parent_field}.{subfield}' has wrong type. Expected {expected_type.__name__}, got {type(veramon_data[parent_field][subfield]).__name__}")
                    elif parent_field in veramon_data:
                        if subfield not in veramon_data[parent_field]:
                            errors.append(f"Veramon {veramon_id}: Missing required subfield '{parent_field}.{subfield}'")
                        elif not isinstance(veramon_data[parent_field][subfield], expected_type):
                            errors.append(f"Veramon {veramon_id}: Subfield '{parent_field}.{subfield}' has wrong type. Expected {expected_type.__name__}, got {type(veramon_data[parent_field][subfield]).__name__}")
    
    # Validate evolution targets
    for target in evolution_targets:
        if target not in veramon_names:
            errors.append(f"Invalid evolution target: '{target}' is not a valid Veramon name")
    
    # Return results
    return len(errors) == 0, errors

def print_validation_report(errors: List[str], show_all: bool = False) -> None:
    """Print a validation report with error summary."""
    if not errors:
        print("PASS: Validation successful! No errors found.")
        return
    
    print(f"FAIL: Validation failed with {len(errors)} errors:")
    
    if show_all or len(errors) <= 10:
        for error in errors:
            print(f"  • {error}")
    else:
        # Show first 5 and last 5 errors
        for error in errors[:5]:
            print(f"  • {error}")
        print(f"  ... {len(errors) - 10} more errors ...")
        for error in errors[-5:]:
            print(f"  • {error}")

def main():
    """Main function to run the validation."""
    print("=== Veramon Data Validation Tool ===")
    
    # Get the project data directory
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / 'data'
    
    # Check for the consolidated file first
    consolidated_path = data_dir / 'veramon_database.json'
    
    if consolidated_path.exists():
        print(f"Validating consolidated file: {consolidated_path}")
        success, errors = validate_veramon_data(str(consolidated_path))
        print_validation_report(errors)
        
        if not success:
            # Ask if user wants to see all errors
            if len(errors) > 10 and input("Show all errors? (y/n): ").lower() == 'y':
                print_validation_report(errors, show_all=True)
            
            # Create a detailed report file
            report_path = script_dir / "veramon_validation_report.txt"
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write("VERAMON DATA VALIDATION REPORT\n")
                    f.write("============================\n\n")
                    f.write(f"Total errors: {len(errors)}\n\n")
                    for i, error in enumerate(errors, 1):
                        f.write(f"{i}. {error}\n")
                print(f"\nDetailed report saved to: {report_path}")
            except Exception as e:
                print(f"Error saving report: {e}")
    else:
        print(f"Consolidated file not found: {consolidated_path}")
        print("Checking for individual files...")
        
        original_path = data_dir / 'veramon_data.json'
        if original_path.exists():
            print(f"Validating original file: {original_path}")
            success, errors = validate_veramon_data(str(original_path))
            print_validation_report(errors)
        else:
            print("No Veramon data files found to validate.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
