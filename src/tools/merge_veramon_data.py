"""
Veramon Data Merge Tool
Created: April 21, 2025

This script consolidates all the veramon_data_part*.json files into a single 
comprehensive veramon_database.json file.
"""

import json
import os
import sys
from pathlib import Path

def merge_json_files():
    """Merge all veramon_data_part*.json files into a single file."""
    # Get the project root directory
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / 'data'
    
    # Output filename
    output_file = data_dir / 'veramon_database.json'
    
    # Get all veramon_data_part*.json files
    json_files = list(data_dir.glob('veramon_data_part*.json'))
    json_files.sort()  # Ensure files are processed in order
    
    # Initialize the combined dictionary
    combined_data = {}
    
    print(f"Found {len(json_files)} data part files to merge.")
    
    # Process each file
    for json_file in json_files:
        print(f"Processing {json_file.name}...")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Add the entries to the combined data
            for key, value in data.items():
                if key in combined_data:
                    print(f"Warning: Duplicate entry '{key}' found in {json_file.name}, overwriting.")
                combined_data[key] = value
                
            print(f"Added {len(data)} Veramon from {json_file.name}")
            
        except json.JSONDecodeError as e:
            print(f"Error: Could not parse {json_file.name}: {e}")
            continue
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
            continue
    
    # Check if the original veramon_data.json exists and contains unique entries
    original_file = data_dir / 'veramon_data.json'
    if original_file.exists():
        print(f"Processing original file {original_file.name}...")
        try:
            with open(original_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
                
            # Add unique entries to the combined data
            original_count = 0
            for key, value in original_data.items():
                if key not in combined_data:
                    combined_data[key] = value
                    original_count += 1
                    
            print(f"Added {original_count} unique Veramon from {original_file.name}")
            
        except Exception as e:
            print(f"Error processing {original_file.name}: {e}")
    
    # Write the combined data to the output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2)
            
        print(f"Successfully merged {len(combined_data)} Veramon into {output_file.name}")
        
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")
        return False
        
    return True

def create_backup(data_dir):
    """Create a backup of the original files."""
    backup_dir = data_dir / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    # Backup all veramon_data*.json files
    for json_file in data_dir.glob('veramon_data*.json'):
        backup_file = backup_dir / json_file.name
        print(f"Creating backup of {json_file.name}...")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as src, open(backup_file, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        except Exception as e:
            print(f"Error creating backup of {json_file.name}: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("=== Veramon Data Merge Tool ===")
    
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / 'data'
    
    # Create backups first
    if not create_backup(data_dir):
        print("Backup failed, aborting merge.")
        sys.exit(1)
    
    # Merge the files
    if merge_json_files():
        print("Merge completed successfully!")
    else:
        print("Merge failed!")
        sys.exit(1)
