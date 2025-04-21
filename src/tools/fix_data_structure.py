"""
Veramon Data Structure Repair Tool
---------------------------------
This script fixes the structure issues found in the Veramon database:
1. Validates and corrects evolution references
2. Ensures all Veramon have correct structure for battle system compatibility
3. Normalizes types and ability formats
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("veramon_repair")

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
sys.path.insert(0, parent_dir)

class VeramonDataFixer:
    def __init__(self):
        """Initialize the data fixer with paths and reference data."""
        self.data_dir = os.path.join(parent_dir, 'src', 'data')
        self.database_path = os.path.join(self.data_dir, 'veramon_database.json')
        self.backup_path = os.path.join(self.data_dir, 'veramon_database_backup.json')
        
        # Valid reference data
        self.valid_types = [
            'Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting',
            'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost',
            'Dragon', 'Dark', 'Steel', 'Fairy'
        ]
        self.valid_rarities = ['common', 'uncommon', 'rare', 'legendary', 'mythic']
        
        # Default values for missing fields
        self.default_stats = {
            'hp': 50,
            'attack': 50,
            'defense': 50,
            'speed': 50
        }
        
        # Load the database
        self.load_database()
    
    def load_database(self):
        """Load the Veramon database."""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                self.veramon_data = json.load(f)
            logger.info(f"Loaded {len(self.veramon_data)} Veramon entries")
        except Exception as e:
            logger.error(f"Failed to load database: {e}")
            sys.exit(1)
    
    def backup_database(self):
        """Create a backup of the database before making changes."""
        try:
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.veramon_data, f, indent=2)
            logger.info(f"Created backup at {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def save_database(self):
        """Save the fixed database."""
        try:
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(self.veramon_data, f, indent=2)
            logger.info(f"Saved fixed database to {self.database_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save database: {e}")
            return False
    
    def fix_evolution_references(self):
        """Fix invalid evolution references."""
        logger.info("Fixing evolution references...")
        
        fixed_count = 0
        removed_count = 0
        
        for name, veramon in self.veramon_data.items():
            if 'evolution' in veramon:
                if isinstance(veramon['evolution'], dict):
                    # Dictionary format: {condition: target_name}
                    valid_evolutions = {}
                    for condition, target in veramon['evolution'].items():
                        if target in self.veramon_data:
                            valid_evolutions[condition] = target
                        else:
                            logger.warning(f"Removing invalid evolution reference: {name} -> {target}")
                            removed_count += 1
                    
                    if valid_evolutions:
                        veramon['evolution'] = valid_evolutions
                        fixed_count += 1
                    else:
                        # No valid evolutions, remove the field
                        del veramon['evolution']
                        removed_count += 1
                
                elif isinstance(veramon['evolution'], list):
                    # List format: [{condition: ..., evolves_to: target_name}]
                    valid_evolutions = []
                    for evo in veramon['evolution']:
                        if isinstance(evo, dict) and 'evolves_to' in evo:
                            if evo['evolves_to'] in self.veramon_data:
                                valid_evolutions.append(evo)
                            else:
                                logger.warning(f"Removing invalid evolution reference: {name} -> {evo['evolves_to']}")
                                removed_count += 1
                    
                    if valid_evolutions:
                        veramon['evolution'] = valid_evolutions
                        fixed_count += 1
                    else:
                        # No valid evolutions, remove the field
                        del veramon['evolution']
                        removed_count += 1
        
        logger.info(f"Fixed {fixed_count} evolution references, removed {removed_count} invalid references")
    
    def fix_veramon_structure(self):
        """Fix structure issues in Veramon entries."""
        logger.info("Fixing Veramon structure...")
        
        fixed_count = 0
        
        required_fields = [
            'name', 'type', 'rarity', 'catch_rate', 'shiny_rate', 
            'base_stats', 'biomes', 'flavor', 'abilities'
        ]
        
        for name, veramon in self.veramon_data.items():
            # Make sure name matches key
            if 'name' not in veramon or veramon['name'] != name:
                veramon['name'] = name
                fixed_count += 1
            
            # Fix type field
            if 'type' not in veramon or not isinstance(veramon['type'], list):
                veramon['type'] = ['Normal']
                fixed_count += 1
            else:
                # Validate types
                valid_types = [t for t in veramon['type'] if t in self.valid_types]
                if not valid_types:
                    valid_types = ['Normal']
                if len(valid_types) != len(veramon['type']):
                    veramon['type'] = valid_types
                    fixed_count += 1
            
            # Fix rarity
            if 'rarity' not in veramon or veramon['rarity'] not in self.valid_rarities:
                veramon['rarity'] = 'common'
                fixed_count += 1
            
            # Fix catch and shiny rates
            if 'catch_rate' not in veramon or not isinstance(veramon['catch_rate'], (int, float)):
                veramon['catch_rate'] = 0.3
                fixed_count += 1
            
            if 'shiny_rate' not in veramon or not isinstance(veramon['shiny_rate'], (int, float)):
                veramon['shiny_rate'] = 0.005
                fixed_count += 1
            
            # Fix base stats
            if 'base_stats' not in veramon or not isinstance(veramon['base_stats'], dict):
                veramon['base_stats'] = self.default_stats.copy()
                fixed_count += 1
            else:
                # Make sure all required stats are present
                for stat, default in self.default_stats.items():
                    if stat not in veramon['base_stats'] or not isinstance(veramon['base_stats'][stat], (int, float)):
                        veramon['base_stats'][stat] = default
                        fixed_count += 1
            
            # Fix biomes
            if 'biomes' not in veramon or not isinstance(veramon['biomes'], list):
                veramon['biomes'] = ['Grassland']
                fixed_count += 1
            
            # Fix flavor text
            if 'flavor' not in veramon or not isinstance(veramon['flavor'], str):
                veramon['flavor'] = f"A mysterious {veramon['type'][0]}-type Veramon."
                fixed_count += 1
            
            # Fix abilities
            if 'abilities' not in veramon or not isinstance(veramon['abilities'], dict) or not veramon['abilities']:
                # Create a default ability based on type
                default_ability = f"{veramon['type'][0]} Strike"
                veramon['abilities'] = {
                    default_ability: {
                        "power": 40,
                        "accuracy": 95,
                        "type": veramon['type'][0].lower(),
                        "description": f"A basic {veramon['type'][0]}-type attack."
                    }
                }
                fixed_count += 1
            else:
                # Validate each ability
                for ability_name, ability in list(veramon['abilities'].items()):
                    if not isinstance(ability, dict):
                        del veramon['abilities'][ability_name]
                        fixed_count += 1
                        continue
                    
                    # Make sure ability has required fields
                    if 'power' not in ability or not isinstance(ability['power'], (int, float)):
                        ability['power'] = 40
                        fixed_count += 1
                    
                    if 'accuracy' not in ability or not isinstance(ability['accuracy'], (int, float)):
                        ability['accuracy'] = 95
                        fixed_count += 1
                    
                    if 'type' not in ability or ability['type'].capitalize() not in self.valid_types:
                        ability['type'] = veramon['type'][0].lower()
                        fixed_count += 1
                    
                    if 'description' not in ability or not isinstance(ability['description'], str):
                        ability['description'] = f"A {ability['type']}-type attack."
                        fixed_count += 1
                
                # If all abilities were invalid and removed, create a default one
                if not veramon['abilities']:
                    default_ability = f"{veramon['type'][0]} Strike"
                    veramon['abilities'] = {
                        default_ability: {
                            "power": 40,
                            "accuracy": 95,
                            "type": veramon['type'][0].lower(),
                            "description": f"A basic {veramon['type'][0]}-type attack."
                        }
                    }
                    fixed_count += 1
        
        logger.info(f"Fixed {fixed_count} structure issues")
    
    def run(self):
        """Run all fixes."""
        # Create a backup first
        if not self.backup_database():
            logger.error("Aborting due to backup failure")
            return False
        
        # Run fixes
        self.fix_evolution_references()
        self.fix_veramon_structure()
        
        # Save fixed database
        return self.save_database()

if __name__ == "__main__":
    print("Veramon Data Structure Repair Tool")
    print("-" * 40)
    
    fixer = VeramonDataFixer()
    
    if fixer.run():
        print("\nRepair completed successfully! The database has been fixed.")
        print(f"A backup of the original database was created at: {fixer.backup_path}")
    else:
        print("\nRepair failed. Please check the logs for details.")
