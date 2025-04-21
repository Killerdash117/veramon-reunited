import os
import json
import glob

def load_all_veramon_data():
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
        return {}

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
