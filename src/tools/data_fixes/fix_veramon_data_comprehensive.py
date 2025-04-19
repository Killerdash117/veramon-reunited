import json
import os
import glob
import re

def fix_types(veramon_data):
    """Ensure consistent type names (e.g., 'Nature' should be 'Grass')"""
    type_mapping = {
        "Nature": "Grass",
        "Light": "Fairy"  # If there are any "Light" types, map them to "Fairy"
    }
    
    for name, veramon in veramon_data.items():
        if "type" in veramon:
            veramon["type"] = [type_mapping.get(t, t) for t in veramon["type"]]

def fix_catch_and_shiny_rates(veramon_data):
    """Convert catch rates and shiny rates to appropriate decimals"""
    for veramon in veramon_data.values():
        # Convert catch_rate from Pokemon style (0-255) to decimal (0.0-1.0)
        if isinstance(veramon.get("catch_rate"), int):
            veramon["catch_rate"] = round(min(veramon["catch_rate"] / 255, 1.0), 2)
        
        # Convert shiny_rate from denominator to actual rate
        if isinstance(veramon.get("shiny_rate"), int) and veramon["shiny_rate"] > 1:
            veramon["shiny_rate"] = round(1 / veramon["shiny_rate"], 5)
        
        # Ensure shiny_rate is consistent with the original format
        if veramon.get("shiny_rate") != 0.001 and veramon.get("rarity") != "legendary" and veramon.get("rarity") != "mythic":
            veramon["shiny_rate"] = 0.0005  # Default shiny rate

        # Set legendary/mythic shiny rates
        if veramon.get("rarity") == "legendary":
            veramon["shiny_rate"] = 0.001
        elif veramon.get("rarity") == "mythic":
            veramon["shiny_rate"] = 0.002

def fix_abilities(veramon_data):
    """Fix ability-related fields"""
    for veramon in veramon_data.values():
        # Remove hidden_ability field if it exists
        if "hidden_ability" in veramon:
            del veramon["hidden_ability"]
        
        # If 'moves' exists, merge it into abilities
        if "moves" in veramon:
            # Keep original abilities if they exist, otherwise use moves
            if "abilities" not in veramon:
                veramon["abilities"] = veramon["moves"]
            del veramon["moves"]

def fix_rarity_and_catch_rates(veramon_data):
    """Ensure catch rates match rarity"""
    rarity_catch_rates = {
        "common": 0.75,
        "uncommon": 0.4,
        "rare": 0.15,
        "legendary": 0.05,
        "mythic": 0.01
    }
    
    for veramon in veramon_data.values():
        if "rarity" in veramon:
            # Set catch rate based on rarity
            veramon["catch_rate"] = rarity_catch_rates.get(veramon["rarity"], veramon["catch_rate"])

def check_required_fields(veramon_data):
    """Ensure all Veramon have the required fields"""
    required_fields = ["name", "type", "rarity", "catch_rate", "shiny_rate", 
                       "base_stats", "biomes", "flavor", "abilities"]
    
    for name, veramon in veramon_data.items():
        for field in required_fields:
            if field not in veramon:
                if field == "abilities":
                    veramon["abilities"] = ["(No abilities defined)"]
                elif field == "flavor":
                    veramon["flavor"] = f"A mysterious {name} Veramon."
                elif field == "biomes":
                    veramon["biomes"] = ["unknown"]
                elif field == "base_stats":
                    veramon["base_stats"] = {"hp": 50, "atk": 50, "def": 50, "sp_atk": 50, "sp_def": 50, "speed": 50}

def fix_all_veramon_files():
    """Process all veramon data files"""
    data_files = glob.glob(os.path.join('src', 'data', 'veramon_data*.json'))
    
    for file_path in data_files:
        print(f"Processing {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Apply fixes
            fix_types(data)
            fix_catch_and_shiny_rates(data)
            fix_abilities(data)
            fix_rarity_and_catch_rates(data)
            check_required_fields(data)
            
            # Write the updated data back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            print(f"Successfully updated {file_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    fix_all_veramon_files()
    print("All Veramon files have been processed and fixed!")
