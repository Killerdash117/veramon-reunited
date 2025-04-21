"""
Veramon Data Redundancy Remover
Created: April 21, 2025

This script removes the redundant veramon_data.json file and updates
the codebase to only use the comprehensive veramon_database.json file.
"""

import os
import sys
import shutil
from pathlib import Path
import re

def create_backups():
    """Create backups of important files before modifying them."""
    print("Creating backups of important files...")
    
    script_dir = Path(__file__).resolve().parent
    src_dir = script_dir.parent
    data_dir = src_dir / 'data'
    backup_dir = data_dir / 'backups'
    
    # Ensure backup directory exists
    backup_dir.mkdir(exist_ok=True)
    
    # Files to backup
    files_to_backup = [
        data_dir / 'veramon_data.json',
        src_dir / 'utils' / 'data_loader.py',
        src_dir / 'utils' / 'cache.py',
        src_dir / 'utils' / 'autocomplete.py'
    ]
    
    # Create backups
    for file_path in files_to_backup:
        if file_path.exists():
            backup_path = backup_dir / f"{file_path.name}.bak"
            try:
                shutil.copy2(file_path, backup_path)
                print(f"  Backed up {file_path.name} to {backup_path}")
            except Exception as e:
                print(f"ERROR: Failed to create backup of {file_path.name}: {e}")
                return False
    
    return True

def remove_data_file():
    """Move the redundant data file to backups."""
    print("\nMoving redundant data file...")
    
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / 'data'
    backup_dir = data_dir / 'backups'
    data_path = data_dir / 'veramon_data.json'
    
    if not data_path.exists():
        print(f"  Data file {data_path.name} not found, nothing to remove")
        return True
    
    try:
        # Move the file to backups instead of deleting
        move_path = backup_dir / f"removed_{data_path.name}"
        shutil.move(data_path, move_path)
        print(f"  Moved {data_path.name} to {move_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to move data file: {e}")
        return False

def update_data_loader():
    """Update the data_loader.py file to only use the database file."""
    print("\nUpdating data_loader.py...")
    
    script_dir = Path(__file__).resolve().parent
    data_loader_path = script_dir.parent / 'utils' / 'data_loader.py'
    
    if not data_loader_path.exists():
        print(f"ERROR: data_loader.py not found at {data_loader_path}")
        return False
    
    try:
        with open(data_loader_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a simplified version that only loads from the database file
        new_content = re.sub(
            r'def load_all_veramon_data\(\):.*?return combined_data',
            '''def load_all_veramon_data():
    """
    Load Veramon data from the database file.
    
    Returns:
        dict: Dictionary of all Veramon data
    """
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.abspath(os.path.join(base_dir, '..', 'data'))
    database_path = os.path.join(data_dir, 'veramon_database.json')
    
    # Load the database file
    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading Veramon database: {e}")
        return {}''',
            content,
            flags=re.DOTALL
        )
        
        with open(data_loader_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  Updated {data_loader_path.name} to use only the database file")
        return True
    except Exception as e:
        print(f"ERROR: Failed to update data_loader.py: {e}")
        return False

def update_cache():
    """Update the cache.py file to only use the database file."""
    print("\nUpdating cache.py...")
    
    script_dir = Path(__file__).resolve().parent
    cache_path = script_dir.parent / 'utils' / 'cache.py'
    
    if not cache_path.exists():
        print(f"ERROR: cache.py not found at {cache_path}")
        return False
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and replace the load_veramon_data function
        pattern = r'def load_veramon_data\(\):.*?return json\.load\(f\)'
        replacement = '''def load_veramon_data():
        import os
        import json
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        database_path = os.path.join(data_dir, "veramon_database.json")
        
        with open(database_path, 'r') as f:
            return json.load(f)'''
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  Updated {cache_path.name} to use only the database file")
        return True
    except Exception as e:
        print(f"ERROR: Failed to update cache.py: {e}")
        return False

def update_autocomplete():
    """Update the autocomplete.py file to only use the database file."""
    print("\nUpdating autocomplete.py...")
    
    script_dir = Path(__file__).resolve().parent
    autocomplete_path = script_dir.parent / 'utils' / 'autocomplete.py'
    
    if not autocomplete_path.exists():
        print(f"ERROR: autocomplete.py not found at {autocomplete_path}")
        return False
    
    try:
        with open(autocomplete_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a simplified version that only loads from the database file
        pattern = r'data_dir = os\.path\.join.*?veramon_data = json\.load\(f\)'
        replacement = '''data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        database_path = os.path.join(data_dir, "veramon_database.json")
        
        with open(database_path, 'r') as f:
            veramon_data = json.load(f)'''
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open(autocomplete_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  Updated {autocomplete_path.name} to use only the database file")
        return True
    except Exception as e:
        print(f"ERROR: Failed to update autocomplete.py: {e}")
        return False

def main():
    """Main function to run the redundancy remover."""
    print("=== Veramon Data Redundancy Remover ===")
    
    # Create backups
    if not create_backups():
        print("ERROR: Failed to create backups, aborting.")
        return 1
    
    # Update data loader
    if not update_data_loader():
        print("ERROR: Failed to update data loader, aborting.")
        return 1
    
    # Update cache
    if not update_cache():
        print("ERROR: Failed to update cache, aborting.")
        return 1
    
    # Update autocomplete
    if not update_autocomplete():
        print("ERROR: Failed to update autocomplete, aborting.")
        return 1
    
    # Remove redundant data file
    if not remove_data_file():
        print("ERROR: Failed to remove redundant data file, aborting.")
        return 1
    
    print("\n=== Redundancy Removal Complete ===")
    print("The codebase now only uses the veramon_database.json file.")
    print("Backups of all modified files have been created in the backups directory.")
    print("\nTo revert these changes, copy the backup files back to their original locations.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
