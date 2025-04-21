"""
Veramon Database Maintenance Script
Created: April 21, 2025

This script provides comprehensive validation and maintenance for the
consolidated Veramon database (veramon_database.json). It ensures consistency,
fixes common issues, and validates the database for use with the battle
and trading systems.
"""

import json
import os
import re
from pathlib import Path
import sys

def fix_types(veramon_data):
    """Ensure consistent type names"""
    type_mapping = {
        "Nature": "Grass",
        "Light": "Fairy"
    }
    
    valid_types = [
        "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", 
        "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", 
        "Dragon", "Dark", "Steel", "Fairy"
    ]
    
    changes_made = 0
    for name, veramon in veramon_data.items():
        if "type" in veramon:
            original_types = veramon["type"].copy() if isinstance(veramon["type"], list) else [veramon["type"]]
            new_types = [type_mapping.get(t, t) for t in original_types]
            
            # Filter out invalid types
            new_types = [t for t in new_types if t in valid_types]
            
            # Ensure at least one valid type
            if not new_types:
                new_types = ["Normal"]
                print(f"WARNING: {name} had no valid types, set to Normal")
            
            if new_types != original_types:
                veramon["type"] = new_types
                changes_made += 1
                print(f"Fixed types for {name}: {original_types} -> {new_types}")
    
    return changes_made

def fix_catch_and_shiny_rates(veramon_data):
    """Convert catch rates and shiny rates to appropriate decimals"""
    changes_made = 0
    for name, veramon in veramon_data.items():
        # Track if changes were made to this Veramon
        veramon_changed = False
        
        # Convert catch_rate from Pokemon style (0-255) to decimal (0.0-1.0)
        if isinstance(veramon.get("catch_rate"), int):
            old_rate = veramon["catch_rate"]
            veramon["catch_rate"] = round(min(veramon["catch_rate"] / 255, 1.0), 2)
            veramon_changed = True
            print(f"Fixed catch rate for {name}: {old_rate} -> {veramon['catch_rate']}")
        
        # Convert shiny_rate from denominator to actual rate
        if isinstance(veramon.get("shiny_rate"), int) and veramon["shiny_rate"] > 1:
            old_rate = veramon["shiny_rate"]
            veramon["shiny_rate"] = round(1 / veramon["shiny_rate"], 5)
            veramon_changed = True
            print(f"Fixed shiny rate for {name}: {old_rate} -> {veramon['shiny_rate']}")
        
        # Ensure shiny_rate is consistent with rarity
        rarity = veramon.get("rarity", "common").lower()
        expected_shiny_rate = {
            "common": 0.0005,
            "uncommon": 0.0005,
            "rare": 0.0005,
            "legendary": 0.001,
            "mythic": 0.002
        }.get(rarity, 0.0005)
        
        if veramon.get("shiny_rate") != expected_shiny_rate:
            old_rate = veramon.get("shiny_rate")
            veramon["shiny_rate"] = expected_shiny_rate
            veramon_changed = True
            print(f"Normalized shiny rate for {name} ({rarity}): {old_rate} -> {expected_shiny_rate}")
        
        if veramon_changed:
            changes_made += 1
    
    return changes_made

def fix_abilities(veramon_data):
    """Fix ability-related fields"""
    changes_made = 0
    for name, veramon in veramon_data.items():
        veramon_changed = False
        
        # Remove hidden_ability field if it exists
        if "hidden_ability" in veramon:
            del veramon["hidden_ability"]
            veramon_changed = True
            print(f"Removed hidden_ability field from {name}")
        
        # If 'moves' exists, merge it into abilities
        if "moves" in veramon:
            if "abilities" not in veramon:
                veramon["abilities"] = veramon["moves"]
                print(f"Moved 'moves' to 'abilities' for {name}")
            del veramon["moves"]
            veramon_changed = True
            print(f"Removed obsolete 'moves' field from {name}")
        
        # Ensure abilities is a list
        if "abilities" in veramon and not isinstance(veramon["abilities"], list):
            veramon["abilities"] = [veramon["abilities"]]
            veramon_changed = True
            print(f"Converted abilities to list format for {name}")
        
        if veramon_changed:
            changes_made += 1
    
    return changes_made

def fix_rarity(veramon_data):
    """Ensure rarity values are consistent"""
    valid_rarities = ["common", "uncommon", "rare", "legendary", "mythic"]
    changes_made = 0
    
    for name, veramon in veramon_data.items():
        if "rarity" in veramon:
            original_rarity = veramon["rarity"]
            # Convert to lowercase
            rarity = original_rarity.lower()
            
            # Fix common misspellings
            if rarity == "mythical":
                rarity = "mythic"
            elif rarity == "legend":
                rarity = "legendary"
            elif rarity == "ultra rare":
                rarity = "rare"
            
            # Validate rarity
            if rarity not in valid_rarities:
                rarity = "common"  # Default to common
            
            if rarity != original_rarity:
                veramon["rarity"] = rarity
                changes_made += 1
                print(f"Fixed rarity for {name}: {original_rarity} -> {rarity}")
        else:
            # No rarity specified, default to common
            veramon["rarity"] = "common"
            changes_made += 1
            print(f"Added missing rarity for {name}, set to common")
    
    return changes_made

def fix_base_stats(veramon_data):
    """Ensure base stats are properly formatted and balanced by rarity"""
    stat_fields = ["hp", "atk", "def", "sp_atk", "sp_def", "speed"]
    rarity_stat_ranges = {
        "common": (40, 70),
        "uncommon": (50, 80),
        "rare": (60, 90),
        "legendary": (70, 100),
        "mythic": (80, 110)
    }
    
    changes_made = 0
    for name, veramon in veramon_data.items():
        veramon_changed = False
        
        # Create base_stats if missing
        if "base_stats" not in veramon:
            veramon["base_stats"] = {stat: 50 for stat in stat_fields}
            veramon_changed = True
            print(f"Added missing base_stats for {name}")
        
        # Get rarity for stat balancing
        rarity = veramon.get("rarity", "common")
        min_stat, max_stat = rarity_stat_ranges.get(rarity, (40, 70))
        
        # Fix each stat
        for stat in stat_fields:
            # Add missing stat
            if stat not in veramon["base_stats"]:
                veramon["base_stats"][stat] = min_stat
                veramon_changed = True
                print(f"Added missing {stat} stat for {name}")
            
            # Convert strings to integers
            if isinstance(veramon["base_stats"][stat], str):
                try:
                    veramon["base_stats"][stat] = int(veramon["base_stats"][stat])
                    veramon_changed = True
                    print(f"Converted {stat} from string to int for {name}")
                except ValueError:
                    veramon["base_stats"][stat] = min_stat
                    veramon_changed = True
                    print(f"Replaced invalid {stat} value with {min_stat} for {name}")
            
            # Balance stats according to rarity
            current_stat = veramon["base_stats"][stat]
            if current_stat < min_stat:
                veramon["base_stats"][stat] = min_stat
                veramon_changed = True
                print(f"Adjusted {stat} from {current_stat} to minimum {min_stat} for {name} ({rarity})")
            elif current_stat > max_stat:
                veramon["base_stats"][stat] = max_stat
                veramon_changed = True
                print(f"Adjusted {stat} from {current_stat} to maximum {max_stat} for {name} ({rarity})")
        
        if veramon_changed:
            changes_made += 1
    
    return changes_made

def check_required_fields(veramon_data):
    """Ensure all Veramon have the required fields"""
    required_fields = ["name", "type", "rarity", "catch_rate", "shiny_rate", 
                       "base_stats", "biomes", "flavor", "abilities"]
    
    changes_made = 0
    for name, veramon in veramon_data.items():
        veramon_changed = False
        
        # Add missing fields
        for field in required_fields:
            if field not in veramon:
                if field == "name":
                    veramon["name"] = name
                elif field == "type":
                    veramon["type"] = ["Normal"]
                elif field == "rarity":
                    veramon["rarity"] = "common"
                elif field == "catch_rate":
                    veramon["catch_rate"] = 0.5
                elif field == "shiny_rate":
                    veramon["shiny_rate"] = 0.0005
                elif field == "abilities":
                    veramon["abilities"] = ["(No abilities defined)"]
                elif field == "flavor":
                    veramon["flavor"] = f"A mysterious {name} Veramon."
                elif field == "biomes":
                    veramon["biomes"] = ["unknown"]
                elif field == "base_stats":
                    veramon["base_stats"] = {"hp": 50, "atk": 50, "def": 50, "sp_atk": 50, "sp_def": 50, "speed": 50}
                
                veramon_changed = True
                print(f"Added missing {field} field to {name}")
        
        # Handle evolution field specially - not required but should be consistent if present
        if "evolution" in veramon:
            if not isinstance(veramon["evolution"], dict):
                veramon["evolution"] = {}
                veramon_changed = True
                print(f"Fixed invalid evolution field format for {name}")
            elif "evolves_to" in veramon["evolution"] and "evolution_level" not in veramon["evolution"]:
                veramon["evolution"]["evolution_level"] = 20  # Default level
                veramon_changed = True
                print(f"Added missing evolution_level for {name}")
        
        if veramon_changed:
            changes_made += 1
    
    return changes_made

def validate_for_battle_system(veramon_data):
    """Ensure all Veramon data is compatible with the battle system"""
    battle_required_fields = ["base_stats", "abilities", "type"]
    
    changes_made = 0
    for name, veramon in veramon_data.items():
        veramon_changed = False
        
        # Check base stats format for battle calculations
        if "base_stats" in veramon:
            for stat in ["hp", "atk", "def", "sp_atk", "sp_def", "speed"]:
                if stat not in veramon["base_stats"]:
                    veramon["base_stats"][stat] = 50
                    veramon_changed = True
                    print(f"Added missing battle stat {stat} for {name}")
        
        # Ensure abilities exist for battle moves
        if "abilities" in veramon:
            if not veramon["abilities"]:
                veramon["abilities"] = ["Tackle"]
                veramon_changed = True
                print(f"Added default ability for {name}")
        
        # Type is crucial for damage calculations
        if "type" in veramon:
            if not veramon["type"]:
                veramon["type"] = ["Normal"]
                veramon_changed = True
                print(f"Added default type for {name}")
        
        if veramon_changed:
            changes_made += 1
    
    return changes_made

def validate_for_trading_system(veramon_data):
    """Ensure all Veramon data is compatible with the trading system"""
    trading_required_fields = ["rarity", "name"]
    
    changes_made = 0
    for name, veramon in veramon_data.items():
        veramon_changed = False
        
        # Trading system needs proper rarity for value calculations
        if "rarity" in veramon:
            if veramon["rarity"] not in ["common", "uncommon", "rare", "legendary", "mythic"]:
                original_rarity = veramon["rarity"]
                veramon["rarity"] = "common"
                veramon_changed = True
                print(f"Fixed invalid rarity for trading: {name} ({original_rarity} -> common)")
        
        # Ensure name is consistent
        if "name" in veramon and veramon["name"] != name:
            veramon["name"] = name
            veramon_changed = True
            print(f"Synchronized name key and name field for trading consistency: {name}")
        
        if veramon_changed:
            changes_made += 1
    
    return changes_made

def maintain_veramon_database():
    """Process the consolidated Veramon database file"""
    print("=== Veramon Database Maintenance ===")
    
    # Get the database file path
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / 'data'
    database_path = data_dir / 'veramon_database.json'
    
    if not database_path.exists():
        print(f"ERROR: Database file not found: {database_path}")
        return False
    
    # Create a backup before making changes
    backup_dir = data_dir / 'backups'
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f'veramon_database_before_maintenance.json'
    
    try:
        import shutil
        shutil.copy2(database_path, backup_path)
        print(f"Created backup at {backup_path}")
    except Exception as e:
        print(f"ERROR: Failed to create backup: {e}")
        return False
    
    # Load the database
    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Loaded database with {len(data)} Veramon")
    except Exception as e:
        print(f"ERROR: Failed to load database: {e}")
        return False
    
    # Apply fixes and count changes
    total_changes = 0
    print("\nApplying fixes...")
    
    total_changes += fix_types(data)
    total_changes += fix_rarity(data)
    total_changes += fix_catch_and_shiny_rates(data)
    total_changes += fix_abilities(data)
    total_changes += fix_base_stats(data)
    total_changes += check_required_fields(data)
    
    # Validate for battle and trading systems
    print("\nValidating for battle system...")
    total_changes += validate_for_battle_system(data)
    
    print("\nValidating for trading system...")
    total_changes += validate_for_trading_system(data)
    
    # Save the updated database
    if total_changes > 0:
        print(f"\nMade {total_changes} changes to the database.")
        try:
            with open(database_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, sort_keys=True)
            print(f"Successfully updated {database_path}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to save database: {e}")
            return False
    else:
        print("\nNo changes needed. Database is already in good condition!")
        return True

if __name__ == "__main__":
    success = maintain_veramon_database()
    sys.exit(0 if success else 1)
