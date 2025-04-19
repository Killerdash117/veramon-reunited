"""
Core Weather System for Veramon Reunited

This module contains the core logic for the dynamic weather system,
affecting Veramon spawns, battle mechanics, and evolution conditions.
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from src.utils.config_manager import get_config

class WeatherSystem:
    """
    Core weather system that handles all weather logic independent
    of the Discord interface.
    """
    
    def __init__(self):
        """Initialize the weather system."""
        self.biome_weather = {}
        self.weather_cache = {}
        self.last_update = {}
        self.default_weathers = {
            "forest": "clear",
            "mountain": "clear",
            "cave": "humid",
            "beach": "sunny",
            "volcano": "heatwave",
            "ocean": "clear",
            "tundra": "snowy",
            "desert": "sandstorm",
            "grassland": "clear"
        }
        
    def get_weather(self, biome: str) -> str:
        """
        Get the current weather for a biome.
        
        Args:
            biome: Name of the biome
            
        Returns:
            str: Current weather condition
        """
        if biome not in self.biome_weather:
            self._update_biome_weather(biome)
            
        return self.biome_weather.get(biome, self.default_weathers.get(biome, "clear"))
        
    def _update_biome_weather(self, biome: str) -> None:
        """
        Update the weather for a specific biome.
        
        Args:
            biome: Name of the biome to update
        """
        current_time = time.time()
        weather_update_interval = get_config("weather", "update_interval", 3600)  # Default: 1 hour
        
        # Check if update is needed
        if biome in self.last_update and current_time - self.last_update[biome] < weather_update_interval:
            return
            
        # Load biome data from cache if available
        if biome in self.weather_cache:
            biome_data = self.weather_cache[biome]
        else:
            # In actual implementation, this would load from the database
            # For now, we'll use hardcoded defaults
            biome_data = {
                "weather": {
                    "clear": {"weight": 40, "spawn_modifiers": {}},
                    "rainy": {"weight": 25, "spawn_modifiers": {"Water": 1.5}},
                    "stormy": {"weight": 10, "spawn_modifiers": {"Electric": 1.8}},
                    "foggy": {"weight": 15, "spawn_modifiers": {"Ghost": 1.5, "Dark": 1.3}},
                    "sunny": {"weight": 25, "spawn_modifiers": {"Fire": 1.3, "Grass": 1.2}},
                    "windy": {"weight": 20, "spawn_modifiers": {"Flying": 1.5}}
                }
            }
            
            # Special biome-specific weather
            if biome == "desert":
                biome_data["weather"]["sandstorm"] = {"weight": 35, "spawn_modifiers": {"Ground": 1.5, "Rock": 1.5}}
            elif biome == "tundra":
                biome_data["weather"]["snowy"] = {"weight": 35, "spawn_modifiers": {"Ice": 1.8}}
            elif biome == "volcano":
                biome_data["weather"]["heatwave"] = {"weight": 35, "spawn_modifiers": {"Fire": 2.0}}
            elif biome == "cave":
                biome_data["weather"]["humid"] = {"weight": 35, "spawn_modifiers": {"Bug": 1.3, "Poison": 1.3}}
                
            self.weather_cache[biome] = biome_data
            
        # Calculate weather based on weights
        weather_options = biome_data.get("weather", {})
        weather_list = []
        
        for weather, data in weather_options.items():
            weight = data.get("weight", 10)
            # Add the weather to the list multiple times based on its weight
            weather_list.extend([weather] * weight)
            
        # Randomly select a weather from the weighted list
        if weather_list:
            selected_weather = random.choice(weather_list)
        else:
            selected_weather = self.default_weathers.get(biome, "clear")
            
        # Special chance for extreme weather events
        extreme_weather_chance = get_config("weather", "extreme_weather_chance", 0.05)  # 5% by default
        if random.random() < extreme_weather_chance:
            special_events = {
                "forest": "thunderstorm",
                "mountain": "blizzard",
                "beach": "hurricane",
                "ocean": "tsunami",
                "tundra": "blizzard",
                "desert": "dust storm",
                "volcano": "volcanic activity"
            }
            
            if biome in special_events:
                selected_weather = special_events[biome]
                
        # Update weather
        self.biome_weather[biome] = selected_weather
        self.last_update[biome] = current_time
        
    def update_all_biomes(self) -> Dict[str, str]:
        """
        Update weather for all known biomes.
        
        Returns:
            Dict[str, str]: Dictionary mapping biome names to weather conditions
        """
        for biome in list(self.biome_weather.keys()) + list(self.default_weathers.keys()):
            self._update_biome_weather(biome)
            
        return self.biome_weather
        
    def get_weather_effects(self, biome: str, weather: str = None) -> Dict[str, Any]:
        """
        Get the effects of the current weather.
        
        Args:
            biome: Name of the biome
            weather: Override weather to check (if None, uses current weather)
            
        Returns:
            Dict: Weather effects including spawn modifiers and descriptions
        """
        if weather is None:
            weather = self.get_weather(biome)
            
        # Get biome data from cache
        biome_data = self.weather_cache.get(biome, {})
        weather_data = biome_data.get("weather", {}).get(weather, {})
        
        if not weather_data:
            # Default effects for standard weather types
            default_effects = {
                "clear": {
                    "description": "Clear weather with no special effects.",
                    "spawn_modifiers": {},
                    "battle_modifiers": {}
                },
                "rainy": {
                    "description": "Rain increases the power of Water-type moves and decreases Fire-type moves.",
                    "spawn_modifiers": {"Water": 1.5},
                    "battle_modifiers": {"Water": 1.2, "Fire": 0.8}
                },
                "stormy": {
                    "description": "Thunderstorms boost Electric-type moves and spawn rates.",
                    "spawn_modifiers": {"Electric": 1.8},
                    "battle_modifiers": {"Electric": 1.3}
                },
                "foggy": {
                    "description": "Fog reduces accuracy and boosts Ghost and Dark types.",
                    "spawn_modifiers": {"Ghost": 1.5, "Dark": 1.3},
                    "battle_modifiers": {"accuracy_modifier": 0.9, "Ghost": 1.2, "Dark": 1.2}
                },
                "sunny": {
                    "description": "Sunny weather boosts Fire and Grass types.",
                    "spawn_modifiers": {"Fire": 1.3, "Grass": 1.2},
                    "battle_modifiers": {"Fire": 1.2, "Grass": 1.1, "Water": 0.8}
                },
                "windy": {
                    "description": "Wind boosts Flying-type moves and increases critical hit chance.",
                    "spawn_modifiers": {"Flying": 1.5},
                    "battle_modifiers": {"Flying": 1.2, "critical_hit_bonus": 0.05}
                },
                "sandstorm": {
                    "description": "Sandstorms boost Ground and Rock types and damage other types each turn.",
                    "spawn_modifiers": {"Ground": 1.5, "Rock": 1.5},
                    "battle_modifiers": {"Ground": 1.2, "Rock": 1.2, "damage_per_turn": 0.05}
                },
                "snowy": {
                    "description": "Snow boosts Ice-type moves and Veramon.",
                    "spawn_modifiers": {"Ice": 1.8},
                    "battle_modifiers": {"Ice": 1.3, "Fire": 0.8}
                },
                "heatwave": {
                    "description": "Extreme heat boosts Fire types and reduces Water effectiveness.",
                    "spawn_modifiers": {"Fire": 2.0},
                    "battle_modifiers": {"Fire": 1.5, "Water": 0.7}
                },
                "humid": {
                    "description": "Humidity increases Bug and Poison spawn rates.",
                    "spawn_modifiers": {"Bug": 1.3, "Poison": 1.3},
                    "battle_modifiers": {"Bug": 1.1, "Poison": 1.1}
                },
                "thunderstorm": {
                    "description": "Severe thunderstorms greatly boost Electric types and shiny chances.",
                    "spawn_modifiers": {"Electric": 2.0, "shiny_boost": 2.0},
                    "battle_modifiers": {"Electric": 1.5, "critical_hit_bonus": 0.1}
                },
                "blizzard": {
                    "description": "Blizzards greatly boost Ice types and can freeze opponents.",
                    "spawn_modifiers": {"Ice": 2.0},
                    "battle_modifiers": {"Ice": 1.5, "freeze_chance": 0.15}
                },
                "hurricane": {
                    "description": "Hurricanes boost Water and Flying types significantly.",
                    "spawn_modifiers": {"Water": 1.8, "Flying": 1.8},
                    "battle_modifiers": {"Water": 1.4, "Flying": 1.4}
                },
                "dust storm": {
                    "description": "Extreme dust storms greatly boost Ground types and reduce accuracy.",
                    "spawn_modifiers": {"Ground": 2.0},
                    "battle_modifiers": {"Ground": 1.5, "accuracy_modifier": 0.8}
                },
                "volcanic activity": {
                    "description": "Volcanic activity greatly boosts Fire and Rock types.",
                    "spawn_modifiers": {"Fire": 2.0, "Rock": 1.5},
                    "battle_modifiers": {"Fire": 1.5, "Rock": 1.3}
                }
            }
            
            return default_effects.get(weather, default_effects["clear"])
            
        # If we have custom data for this weather, use it
        return {
            "description": weather_data.get("description", f"{weather.capitalize()} weather"),
            "spawn_modifiers": weather_data.get("spawn_modifiers", {}),
            "battle_modifiers": weather_data.get("battle_modifiers", {})
        }
        
    def get_weather_evolution_effects(self, weather: str) -> Dict[str, Any]:
        """
        Get evolution effects for specific weather conditions.
        
        Args:
            weather: Weather condition to check
            
        Returns:
            Dict: Weather evolution effects including eligible forms and evolutions
        """
        # Default evolution requirements for weather-based evolutions and forms
        weather_evolution_effects = {
            "thunderstorm": {
                "forms": ["electric", "storm", "thunder"],
                "evolutions": ["storm_evolution"]
            },
            "rainy": {
                "forms": ["rain", "water", "aquatic"],
                "evolutions": ["rain_evolution"]
            },
            "sunny": {
                "forms": ["sun", "solar", "light"],
                "evolutions": ["sun_evolution"]
            },
            "foggy": {
                "forms": ["mist", "ghost", "shadow"],
                "evolutions": ["mist_evolution"]
            },
            "snowy": {
                "forms": ["ice", "frost", "winter"],
                "evolutions": ["frost_evolution"]
            },
            "sandstorm": {
                "forms": ["sand", "desert", "dune"],
                "evolutions": ["sand_evolution"]
            },
            "heatwave": {
                "forms": ["heat", "molten", "magma"],
                "evolutions": ["heat_evolution"]
            }
        }
        
        return weather_evolution_effects.get(weather, {"forms": [], "evolutions": []})
        
# Function to get a global instance of the weather system
_weather_system = None

def get_weather_system() -> WeatherSystem:
    """
    Get the global weather system instance.
    
    Returns:
        WeatherSystem: Global weather system instance
    """
    global _weather_system
    
    if _weather_system is None:
        _weather_system = WeatherSystem()
        
    return _weather_system
