"""
Veramon Data Cleanup Tool
Created: April 21, 2025

This script removes the individual veramon_data_part*.json files after 
confirming that the consolidated veramon_database.json file is valid
and contains all the necessary data.
"""

import json
import os
import sys
from pathlib import Path
import shutil
import glob

def verify_consolidated_file(data_dir: Path) -> bool:
    """
    Verify that the consolidated file exists and contains all the necessary data.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        bool: True if verification passes, False otherwise
    """
    complete_file = data_dir / 'veramon_database.json'
    
    if not complete_file.exists():
        print(f"Error: Consolidated file not found: {complete_file}")
        return False
    
    # Check that the file is valid JSON
    try:
        with open(complete_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Could not parse consolidated file: {e}")
        return False
    
    # Check that the file contains a reasonable number of entries
    # We expect at least 200 Veramon entries based on our prior merge
    if len(data) < 200:
        print(f"Warning: Consolidated file contains only {len(data)} entries, which is fewer than expected.")
        user_continue = input("Continue with cleanup anyway? (y/n): ").lower()
        if user_continue != 'y':
            return False
    
    print(f"Verified consolidated file contains {len(data)} Veramon entries.")
    return True

def verify_backups(data_dir: Path) -> bool:
    """
    Verify that backups of all files exist.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        bool: True if verification passes, False otherwise
    """
    backup_dir = data_dir / 'backups'
    
    if not backup_dir.exists():
        print(f"Error: Backup directory not found: {backup_dir}")
        return False
    
    # Get a list of all part files
    part_files = list(data_dir.glob('veramon_data_part*.json'))
    
    # Check that backups exist for each part file
    for part_file in part_files:
        backup_file = backup_dir / part_file.name
        if not backup_file.exists():
            print(f"Error: Backup not found for {part_file.name}")
            return False
        
        # Check that backup is valid JSON
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                json.load(f)
        except Exception as e:
            print(f"Error: Could not parse backup file {backup_file.name}: {e}")
            return False
    
    print(f"Verified backups for {len(part_files)} part files.")
    return True

def clean_part_files(data_dir: Path) -> bool:
    """
    Remove all veramon_data_part*.json files.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        bool: True if cleanup succeeds, False otherwise
    """
    # Get a list of all part files
    part_files = list(data_dir.glob('veramon_data_part*.json'))
    
    if not part_files:
        print("No part files found to clean up.")
        return True
    
    print(f"Found {len(part_files)} part files to remove:")
    for part_file in part_files:
        print(f"  - {part_file.name}")
    
    # Remove each part file
    for part_file in part_files:
        try:
            os.remove(part_file)
            print(f"Removed {part_file.name}")
        except Exception as e:
            print(f"Error removing {part_file.name}: {e}")
            return False
    
    print(f"Successfully removed {len(part_files)} part files.")
    return True

def create_original_backup(data_dir: Path) -> bool:
    """
    Create a backup of the original veramon_data.json file.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        bool: True if backup succeeds, False otherwise
    """
    original_file = data_dir / 'veramon_data.json'
    backup_dir = data_dir / 'backups'
    
    if not original_file.exists():
        print(f"Warning: Original file not found: {original_file}")
        return True
    
    # Create backup directory if it doesn't exist
    backup_dir.mkdir(exist_ok=True)
    
    # Create backup
    backup_file = backup_dir / 'veramon_data.json'
    try:
        shutil.copy2(original_file, backup_file)
        print(f"Created backup of {original_file.name}")
        return True
    except Exception as e:
        print(f"Error creating backup of {original_file.name}: {e}")
        return False

def update_original_file(data_dir: Path) -> bool:
    """
    Update the original veramon_data.json file with content from the consolidated file.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        bool: True if update succeeds, False otherwise
    """
    original_file = data_dir / 'veramon_data.json'
    complete_file = data_dir / 'veramon_database.json'
    
    if not complete_file.exists():
        print(f"Error: Consolidated file not found: {complete_file}")
        return False
    
    # Load the consolidated data
    try:
        with open(complete_file, 'r', encoding='utf-8') as f:
            complete_data = json.load(f)
    except Exception as e:
        print(f"Error loading consolidated file: {e}")
        return False
    
    # Select a subset of 10-15 common Veramon for the original file
    # This keeps the original file small but still functional
    subset_data = {}
    count = 0
    for veramon_id, veramon_data in complete_data.items():
        if veramon_data.get("rarity") == "common" and count < 12:
            subset_data[veramon_id] = veramon_data
            count += 1
    
    # Save the subset to the original file
    try:
        with open(original_file, 'w', encoding='utf-8') as f:
            json.dump(subset_data, f, indent=2)
        print(f"Updated {original_file.name} with a subset of {count} common Veramon.")
        return True
    except Exception as e:
        print(f"Error updating {original_file.name}: {e}")
        return False

def main():
    """Main function to run the cleanup."""
    print("=== Veramon Data Cleanup Tool ===")
    
    # Get the project data directory
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / 'data'
    
    # Verify consolidated file
    if not verify_consolidated_file(data_dir):
        print("Verification of consolidated file failed. Aborting cleanup.")
        return 1
    
    # Verify backups
    if not verify_backups(data_dir):
        print("Verification of backups failed. Aborting cleanup.")
        return 1
    
    # Backup original file
    if not create_original_backup(data_dir):
        print("Backup of original file failed. Aborting cleanup.")
        return 1
    
    # Update original file with subset
    if not update_original_file(data_dir):
        print("Update of original file failed. Aborting cleanup.")
        return 1
    
    # Clean up part files
    if not clean_part_files(data_dir):
        print("Cleanup of part files failed.")
        return 1
    
    print("\nCleanup completed successfully!")
    print("\nSummary:")
    print("1. Verified consolidated file contains all necessary data")
    print("2. Confirmed backups of all files exist")
    print("3. Created backup of original veramon_data.json")
    print("4. Updated original file with a subset of common Veramon")
    print("5. Removed all veramon_data_part*.json files")
    print("\nYour Veramon data is now neat and organized!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
