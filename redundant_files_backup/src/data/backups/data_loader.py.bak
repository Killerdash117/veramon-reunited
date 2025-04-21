import os
import json
import glob

def load_all_veramon_data():
    """
    Load and combine all Veramon data from all data files.
    
    Returns:
        dict: Combined dictionary of all Veramon data
    """
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.abspath(os.path.join(base_dir, '..', 'data'))
    
    # First try loading the consolidated file
    complete_data_path = os.path.join(data_dir, 'veramon_database.json')
    combined_data = {}
    
    if os.path.exists(complete_data_path):
        try:
            with open(complete_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading consolidated data file: {e}")
            print("Falling back to loading individual files.")
    
    # Fallback: load individual files
    # Start with the main veramon_data.json
    main_data_path = os.path.join(data_dir, 'veramon_data.json')
    
    if os.path.exists(main_data_path):
        with open(main_data_path, 'r', encoding='utf-8') as f:
            combined_data.update(json.load(f))
    
    # Find and load all additional veramon_data_part*.json files
    part_files = glob.glob(os.path.join(data_dir, 'veramon_data_part*.json'))
    
    for file_path in sorted(part_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                part_data = json.load(f)
                combined_data.update(part_data)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return combined_data

def load_biomes_data():
    """Load biomes data from the biomes.json file"""
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.abspath(os.path.join(base_dir, '..', 'data'))
    biomes_path = os.path.join(data_dir, 'biomes.json')
    
    with open(biomes_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_items_data():
    """Load items data from the items.json file"""
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.abspath(os.path.join(base_dir, '..', 'data'))
    items_path = os.path.join(data_dir, 'items.json')
    
    with open(items_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_abilities_data():
    """Load abilities data from the abilities.json file"""
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.abspath(os.path.join(base_dir, '..', 'data'))
    abilities_path = os.path.join(data_dir, 'abilities.json')
    
    with open(abilities_path, 'r', encoding='utf-8') as f:
        return json.load(f)
