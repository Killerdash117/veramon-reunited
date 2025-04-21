#!/usr/bin/env python
"""
Configuration Usage Example for Veramon Reunited

This script demonstrates how to use the new config_manager system in your code.
Run this file to see the configuration values loaded and used.
"""

import os
import sys
import json
from datetime import datetime

# Add the src directory to the system path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.config_manager import get_config, update_config, save_config

def show_config_usage():
    """
    Demonstrate proper usage of the configuration system.
    """
    print("\n" + "="*80)
    print("VERAMON REUNITED CONFIGURATION SYSTEM EXAMPLE")
    print("="*80 + "\n")
    
    # Example 1: Get basic configuration values
    version = get_config("general", "version")
    print(f"Current Version: {version}")
    
    # Example 2: Get exploration settings with defaults
    cooldown = get_config("exploration", "base_spawn_cooldown", 60)
    print(f"Base Spawn Cooldown: {cooldown} seconds")
    
    # Example 3: Get entire section
    battle_config = get_config("battle")
    print("\nBattle Configuration:")
    for key, value in battle_config.items():
        print(f"  {key}: {value}")
    
    # Example 4: Weather configuration
    print("\nWeather Configuration:")
    weather_config = get_config("weather")
    for key, value in weather_config.items():
        print(f"  {key}: {value}")
    
    # Example 5: How weather affects shiny chance
    base_shiny_rate = get_config("exploration", "shiny_rate", 0.0005)
    thunderstorm_boost = get_config("weather", "thunderstorm_shiny_boost", 2.0)
    print(f"\nShiny Chance Calculation:")
    print(f"  Base shiny rate: {base_shiny_rate} (0.05%)")
    print(f"  During thunderstorm: {base_shiny_rate * thunderstorm_boost} ({base_shiny_rate * thunderstorm_boost * 100}%)")
    
    # Example 6: Evolution settings
    evolution_xp = get_config("evolution", "base_evolution_xp", 100)
    xp_curve = get_config("evolution", "xp_curve_exponent", 1.5)
    print(f"\nEvolution System:")
    print(f"  Base XP needed for evolution: {evolution_xp}")
    print(f"  XP curve exponent: {xp_curve}")
    
    # Calculate XP needed for different levels
    print("\nXP required for evolution at different levels:")
    for level in [1, 5, 10, 20, 50, 100]:
        xp_needed = evolution_xp * (level ** xp_curve)
        print(f"  Level {level}: {int(xp_needed)} XP")
    
    print("\n" + "="*80)
    print("END OF EXAMPLE")
    print("="*80 + "\n")

if __name__ == "__main__":
    show_config_usage()
