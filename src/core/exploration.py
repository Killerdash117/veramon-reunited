"""
Core Exploration System for Veramon Reunited

This module contains the core logic for the exploration system,
including biome mechanics, encounter generation, and special areas.
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from src.utils.config_manager import get_config
from src.core.weather import get_weather_system

class ExplorationSystem:
    """
    Core exploration system that handles all exploration logic independent
    of the Discord interface.
    """
    
    def __init__(self):
        """Initialize the exploration system."""
        self.biomes = {}
        self.biome_spawns = {}
        self.special_areas = {}
        self.last_encounter = {}
        self.weather_system = get_weather_system()
        self.spawn_cooldowns = {}
        
        # Load biome data
        self._load_biome_data()
        
    def _load_biome_data(self) -> None:
        """Load biome data from configuration files."""
        # In a real implementation, this would load from the database or JSON files
        # For now, we'll use a simplified representation
        default_biomes = {
            "forest": {
                "description": "A lush forest teeming with grass and bug Veramon.",
                "base_spawns": {
                    "Grass": 35,
                    "Bug": 30,
                    "Normal": 20,
                    "Flying": 15
                },
                "special_areas": ["ancient_grove", "mushroom_hollow"],
                "weather_effects": {
                    "clear": {
                        "description": "Clear skies in the forest.",
                        "spawn_modifiers": {}
                    },
                    "rainy": {
                        "description": "Rain falls through the forest canopy.",
                        "spawn_modifiers": {"Bug": 1.5, "Grass": 1.2}
                    },
                    "foggy": {
                        "description": "A mysterious fog weaves through the trees.",
                        "spawn_modifiers": {"Ghost": 2.0, "Dark": 1.5}
                    }
                }
            },
            "mountain": {
                "description": "Craggy peaks home to rock and fighting Veramon.",
                "base_spawns": {
                    "Rock": 35,
                    "Fighting": 25,
                    "Flying": 20,
                    "Ground": 20
                },
                "special_areas": ["summit", "crystal_cave"],
                "weather_effects": {
                    "clear": {
                        "description": "Clear mountain air.",
                        "spawn_modifiers": {}
                    },
                    "snowy": {
                        "description": "Snow blankets the mountain peaks.",
                        "spawn_modifiers": {"Ice": 2.0, "Rock": 0.8}
                    }
                }
            },
            "beach": {
                "description": "Sandy shores with water and ground Veramon.",
                "base_spawns": {
                    "Water": 40,
                    "Ground": 30,
                    "Normal": 20,
                    "Flying": 10
                },
                "special_areas": ["tide_pools", "coral_reef"],
                "weather_effects": {
                    "clear": {
                        "description": "Sunny day at the beach.",
                        "spawn_modifiers": {}
                    },
                    "stormy": {
                        "description": "A storm brews over the ocean.",
                        "spawn_modifiers": {"Electric": 2.0, "Water": 1.5}
                    }
                }
            }
        }
        
        # Store the biome data
        self.biomes = default_biomes
        
        # Load special area data
        default_special_areas = {
            "ancient_grove": {
                "description": "An ancient part of the forest with rare Veramon.",
                "unlock_requirement": "Catch 50 Grass-type Veramon",
                "spawn_modifiers": {"rare_modifier": 2.0, "level_modifier": 1.5}
            },
            "mushroom_hollow": {
                "description": "A dark hollow filled with glowing mushrooms.",
                "unlock_requirement": "Catch 30 Poison-type Veramon",
                "spawn_modifiers": {"Poison": 2.0, "Fairy": 1.5, "shiny_modifier": 1.2}
            },
            "summit": {
                "description": "The highest peak of the mountain range.",
                "unlock_requirement": "Catch 40 Flying-type Veramon",
                "spawn_modifiers": {"Flying": 2.0, "Dragon": 1.5, "level_modifier": 2.0}
            },
            "crystal_cave": {
                "description": "A cave filled with glowing crystals.",
                "unlock_requirement": "Catch 35 Rock-type Veramon",
                "spawn_modifiers": {"Rock": 1.5, "Electric": 1.5, "shiny_modifier": 1.3}
            },
            "tide_pools": {
                "description": "Shallow pools left by the retreating tide.",
                "unlock_requirement": "Catch 25 Water-type Veramon",
                "spawn_modifiers": {"Water": 1.5, "Bug": 1.2, "rare_modifier": 1.5}
            },
            "coral_reef": {
                "description": "A vibrant reef just offshore.",
                "unlock_requirement": "Complete the 'Ocean Explorer' quest",
                "spawn_modifiers": {"Water": 2.0, "Dragon": 1.3, "legendary_chance": 0.001}
            }
        }
        
        # Store the special area data
        self.special_areas = default_special_areas
        
    def get_biome_info(self, biome: str) -> Dict[str, Any]:
        """
        Get information about a biome.
        
        Args:
            biome: Name of the biome
            
        Returns:
            Dict: Biome information
        """
        return self.biomes.get(biome, {})
        
    def get_special_area_info(self, area_name: str) -> Dict[str, Any]:
        """
        Get information about a special area.
        
        Args:
            area_name: Name of the special area
            
        Returns:
            Dict: Special area information
        """
        return self.special_areas.get(area_name, {})
        
    def is_special_area_unlocked(self, user_id: str, area_name: str) -> bool:
        """
        Check if a special area is unlocked for a user.
        
        Args:
            user_id: ID of the user
            area_name: Name of the special area
            
        Returns:
            bool: True if the area is unlocked
        """
        # In actual implementation, this would check the database
        # for achievement records
        return True  # For testing purposes
        
    def get_spawn_cooldown(self, user_id: str, biome: str) -> int:
        """
        Get the remaining cooldown for a user in a biome.
        
        Args:
            user_id: ID of the user
            biome: Name of the biome
            
        Returns:
            int: Remaining cooldown in seconds
        """
        key = f"{user_id}:{biome}"
        
        if key not in self.spawn_cooldowns:
            return 0
            
        current_time = time.time()
        last_time, cooldown = self.spawn_cooldowns[key]
        
        remaining = max(0, cooldown - (current_time - last_time))
        return int(remaining)
        
    def set_spawn_cooldown(self, user_id: str, biome: str) -> int:
        """
        Set a spawn cooldown for a user in a biome.
        
        Args:
            user_id: ID of the user
            biome: Name of the biome
            
        Returns:
            int: Cooldown duration in seconds
        """
        base_cooldown = get_config("exploration", "base_spawn_cooldown", 60)
        cooldown_reduction = get_config("exploration", "vip_cooldown_reduction", 0.5)
        
        # In actual implementation, this would check if the user is VIP
        is_vip = False  # Placeholder
        
        if is_vip:
            cooldown = base_cooldown * cooldown_reduction
        else:
            cooldown = base_cooldown
            
        # Add some randomness
        cooldown = cooldown * random.uniform(0.9, 1.1)
        
        key = f"{user_id}:{biome}"
        self.spawn_cooldowns[key] = (time.time(), cooldown)
        
        return int(cooldown)
        
    async def generate_encounter(self, 
                                user_id: str, 
                                biome: str, 
                                special_area: str = None) -> Optional[Dict[str, Any]]:
        """
        Generate a Veramon encounter in a biome.
        
        Args:
            user_id: ID of the user
            biome: Name of the biome
            special_area: Name of the special area (optional)
            
        Returns:
            Dict: Encounter data if successful, None otherwise
        """
        # Check if biome exists
        if biome not in self.biomes:
            return None
            
        # Check cooldown
        remaining_cooldown = self.get_spawn_cooldown(user_id, biome)
        if remaining_cooldown > 0:
            return {"error": f"You must wait {remaining_cooldown} seconds before exploring again."}
            
        # Check if special area is valid and unlocked
        using_special_area = False
        special_area_data = None
        
        if special_area:
            if special_area not in self.special_areas:
                return {"error": f"Special area '{special_area}' does not exist."}
                
            if not self.is_special_area_unlocked(user_id, special_area):
                return {"error": f"You haven't unlocked the '{special_area}' area yet."}
                
            special_area_data = self.special_areas[special_area]
            using_special_area = True
            
        # Get biome data
        biome_data = self.biomes[biome]
        
        # Get current weather
        current_weather = self.weather_system.get_weather(biome)
        weather_effects = self.weather_system.get_weather_effects(biome, current_weather)
        
        # Generate Veramon spawn
        spawn_data = self._generate_spawn(biome_data, special_area_data, weather_effects)
        
        # Set cooldown
        cooldown = self.set_spawn_cooldown(user_id, biome)
        
        # Return encounter data
        return {
            "success": True,
            "biome": biome,
            "special_area": special_area if using_special_area else None,
            "weather": current_weather,
            "weather_effects": weather_effects,
            "spawn": spawn_data,
            "cooldown": cooldown
        }
        
    def _generate_spawn(self, 
                       biome_data: Dict[str, Any],
                       special_area_data: Optional[Dict[str, Any]],
                       weather_effects: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Veramon spawn based on biome, special area, and weather.
        
        Args:
            biome_data: Biome data
            special_area_data: Special area data (optional)
            weather_effects: Weather effects
            
        Returns:
            Dict: Spawn data
        """
        # Get base spawn rates
        base_spawns = biome_data.get("base_spawns", {})
        
        # Apply weather modifications
        spawn_modifiers = weather_effects.get("spawn_modifiers", {})
        modified_spawns = {}
        
        for type_name, weight in base_spawns.items():
            modifier = spawn_modifiers.get(type_name, 1.0)
            modified_spawns[type_name] = weight * modifier
            
        # Apply special area modifications if applicable
        if special_area_data:
            area_modifiers = special_area_data.get("spawn_modifiers", {})
            
            for type_name, modifier in area_modifiers.items():
                if type_name in modified_spawns:
                    modified_spawns[type_name] *= modifier
                elif type_name not in ["rare_modifier", "shiny_modifier", "level_modifier", "legendary_chance"]:
                    # Add new type with reduced weight
                    modified_spawns[type_name] = 10 * modifier
            
        # Create weighted list of types
        weighted_types = []
        for type_name, weight in modified_spawns.items():
            weighted_types.extend([type_name] * int(weight))
            
        # Select random type
        selected_type = random.choice(weighted_types) if weighted_types else "Normal"
        
        # Determine if shiny
        shiny_rate = get_config("exploration", "shiny_rate", 0.0005)  # Default: 1/2000
        
        # Apply weather or special area shiny boost
        shiny_boost = spawn_modifiers.get("shiny_boost", 1.0)
        if special_area_data:
            shiny_boost *= special_area_data.get("spawn_modifiers", {}).get("shiny_modifier", 1.0)
            
        is_shiny = random.random() < (shiny_rate * shiny_boost)
        
        # Determine level range
        base_min_level = get_config("exploration", "min_spawn_level", 1)
        base_max_level = get_config("exploration", "max_spawn_level", 50)
        
        level_modifier = 1.0
        if special_area_data:
            level_modifier = special_area_data.get("spawn_modifiers", {}).get("level_modifier", 1.0)
            
        min_level = max(1, int(base_min_level * level_modifier))
        max_level = max(min_level, int(base_max_level * level_modifier))
        
        level = random.randint(min_level, max_level)
        
        # Determine rarity
        rarity_weights = {
            "common": 60,
            "uncommon": 30,
            "rare": 9,
            "ultra_rare": 1
        }
        
        # Apply rare modifier from special areas
        if special_area_data:
            rare_modifier = special_area_data.get("spawn_modifiers", {}).get("rare_modifier", 1.0)
            rarity_weights["rare"] = int(rarity_weights["rare"] * rare_modifier)
            rarity_weights["ultra_rare"] = int(rarity_weights["ultra_rare"] * rare_modifier)
            
        # Legendary chance from special areas
        legendary_chance = 0
        if special_area_data:
            legendary_chance = special_area_data.get("spawn_modifiers", {}).get("legendary_chance", 0)
            
        if legendary_chance > 0 and random.random() < legendary_chance:
            rarity = "legendary"
        else:
            # Create weighted rarity list
            weighted_rarities = []
            for rarity_name, weight in rarity_weights.items():
                weighted_rarities.extend([rarity_name] * weight)
                
            rarity = random.choice(weighted_rarities)
        
        # In actual implementation, this would select a specific Veramon
        # based on type and rarity from the database
        return {
            "type": selected_type,
            "level": level,
            "rarity": rarity,
            "is_shiny": is_shiny,
            "weather_bonus": bool(spawn_modifiers.get(selected_type, 0) > 1.0)
        }
        
# Function to get a global instance of the exploration system
_exploration_system = None

def get_exploration_system() -> ExplorationSystem:
    """
    Get the global exploration system instance.
    
    Returns:
        ExplorationSystem: Global exploration system instance
    """
    global _exploration_system
    
    if _exploration_system is None:
        _exploration_system = ExplorationSystem()
        
    return _exploration_system
