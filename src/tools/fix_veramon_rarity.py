"""
Veramon Data Fix Tool
Created: April 21, 2025

Quick script to fix the 'mythical' rarity value to be 'mythic' in the consolidated Veramon data.
"""

import json
import os
from pathlib import Path

def fix_rarity_values():
    """Fix rarity values in the Veramon data file."""
    # Get the project data directory
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / 'data'
    
    # Load the consolidated file
    data_path = data_dir / 'veramon_database.json'
    
    if not data_path.exists():
        print(f"Error: File not found: {data_path}")
        return False
    
    print(f"Loading data from: {data_path}")
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return False
    
    # Count of fixes made
    fixed_count = 0
    
    # Fix the rarity values
    for veramon_id, veramon_data in data.items():
        if "rarity" in veramon_data and veramon_data["rarity"] == "mythical":
            print(f"Fixing rarity for {veramon_id} from 'mythical' to 'mythic'")
            veramon_data["rarity"] = "mythic"
            fixed_count += 1
    
    # Save the fixed data
    if fixed_count > 0:
        try:
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Fixed {fixed_count} instances of 'mythical' rarity.")
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False
    else:
        print("No fixes needed.")
        return True

if __name__ == "__main__":
    print("=== Veramon Rarity Fix Tool ===")
    success = fix_rarity_values()
    print("Done!" if success else "Failed!")
