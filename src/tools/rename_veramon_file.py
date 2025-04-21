"""
Veramon File Renaming Tool
Created: April 21, 2025

This script renames the veramon_database.json file to veramon_database.json
and updates all references in the codebase.
"""

import os
import sys
from pathlib import Path
import re
import glob
import shutil

def rename_file(data_dir: Path) -> bool:
    """
    Rename the veramon_database.json file to veramon_database.json.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        bool: True if rename succeeds, False otherwise
    """
    old_path = data_dir / 'veramon_database.json'
    new_path = data_dir / 'veramon_database.json'
    
    if not old_path.exists():
        print(f"Error: Source file not found: {old_path}")
        return False
    
    if new_path.exists():
        print(f"Warning: Destination file already exists: {new_path}")
        user_input = input("Overwrite? (y/n): ").lower()
        if user_input != 'y':
            return False
    
    try:
        # Create a backup first
        backup_dir = data_dir / 'backups'
        backup_dir.mkdir(exist_ok=True)
        shutil.copy2(old_path, backup_dir / old_path.name)
        
        # Rename the file
        shutil.copy2(old_path, new_path)
        os.remove(old_path)
        print(f"Renamed {old_path.name} to {new_path.name}")
        return True
    except Exception as e:
        print(f"Error renaming file: {e}")
        return False

def update_file_references(project_dir: Path) -> bool:
    """
    Update references to veramon_database.json in the codebase.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        bool: True if updates succeed, False otherwise
    """
    py_files = list(project_dir.glob('**/*.py'))
    json_files = list(project_dir.glob('**/*.json'))
    markdown_files = list(project_dir.glob('**/*.md'))
    
    # Combine all files
    all_files = py_files + json_files + markdown_files
    
    # Old and new filenames
    old_name = 'veramon_database.json'
    new_name = 'veramon_database.json'
    
    # Track changes
    modified_files = []
    
    # Process each file
    for file_path in all_files:
        # Skip certain directories
        if any(part in str(file_path) for part in ['/venv/', '/.git/', '/backups/', '/__pycache__/']):
            continue
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file contains references to old filename
            if old_name in content:
                # Replace references
                new_content = content.replace(old_name, new_name)
                
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                modified_files.append(file_path)
                print(f"Updated references in {file_path.relative_to(project_dir)}")
        except Exception as e:
            print(f"Error updating references in {file_path}: {e}")
    
    print(f"Updated references in {len(modified_files)} files.")
    return True

def main():
    """Main function to run the file renaming."""
    print("=== Veramon File Renaming Tool ===")
    
    # Get the project directories
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent.parent
    data_dir = script_dir.parent / 'data'
    
    # Rename the file
    if not rename_file(data_dir):
        print("Renaming file failed. Aborting.")
        return 1
    
    # Update file references
    if not update_file_references(project_dir):
        print("Updating file references failed.")
        return 1
    
    print("\nFile renaming completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
