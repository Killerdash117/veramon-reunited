"""
Configuration Manager for Veramon Reunited

This module provides utility functions to load, access, and update
configuration settings from the central config.json file.
"""

import os
import json
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, Optional, Union, List, Tuple

from src.utils.env_config import is_debug_mode

# Set up logging
logger = logging.getLogger(__name__)

# Global config cache
_config_cache = None
_config_path = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
_config_backup_dir = os.path.join(os.path.dirname(__file__), "..", "data", "config_backups")

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json file.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    global _config_cache
    
    try:
        with open(_config_path, 'r') as f:
            _config_cache = json.load(f)
        return _config_cache
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {_config_path}")
        # Create default config if file doesn't exist
        if create_default_config():
            return load_config()
        raise FileNotFoundError(f"Configuration file not found at {_config_path}")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in configuration file {_config_path}")
        # Backup the broken file
        backup_config()
        raise ValueError(f"Invalid JSON in configuration file {_config_path}")

def get_config(section: Optional[str] = None, key: Optional[str] = None, default: Any = None) -> Any:
    """
    Get configuration value from specified section and key.
    
    Args:
        section (str, optional): Configuration section (e.g., 'exploration', 'battle')
        key (str, optional): Configuration key within section
        default (Any, optional): Default value if key not found
        
    Returns:
        Any: Configuration value or default if not found
    """
    global _config_cache
    
    if _config_cache is None:
        _config_cache = load_config()
    
    # Return full config if no section specified
    if section is None:
        return _config_cache
    
    # Return section if no key specified
    if section in _config_cache and key is None:
        return _config_cache[section]
    
    # Return specific value or default
    if section in _config_cache and key in _config_cache[section]:
        return _config_cache[section][key]
    
    return default

def update_config(section: str, key: str, value: Any, save: bool = True) -> bool:
    """
    Update configuration value and optionally save to disk.
    
    Args:
        section (str): Configuration section
        key (str): Configuration key within section
        value (Any): New value to set
        save (bool): Whether to save to disk immediately
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _config_cache
    
    if _config_cache is None:
        _config_cache = load_config()
    
    # Ensure section exists
    if section not in _config_cache:
        _config_cache[section] = {}
    
    # Create backup before significant changes
    if save and key in ["version"]:
        backup_config()
    
    # Update value
    _config_cache[section][key] = value
    
    # Save to disk if requested
    if save:
        return save_config()
    
    return True

def update_config_batch(updates: List[Tuple[str, str, Any]]) -> bool:
    """
    Update multiple configuration values and save to disk.
    
    Args:
        updates: List of (section, key, value) tuples to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _config_cache
    
    if _config_cache is None:
        _config_cache = load_config()
    
    # Create backup before batch update
    backup_config()
    
    # Apply updates
    for section, key, value in updates:
        # Ensure section exists
        if section not in _config_cache:
            _config_cache[section] = {}
        
        # Update value
        _config_cache[section][key] = value
    
    # Save to disk
    return save_config()

def save_config() -> bool:
    """
    Save current configuration to disk.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global _config_cache
    
    if _config_cache is None:
        logger.error("Cannot save config - no configuration loaded")
        return False
    
    try:
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(_config_path), exist_ok=True)
        
        # Save with pretty formatting
        with open(_config_path, 'w') as f:
            json.dump(_config_cache, f, indent=2)
        
        # Print debug info if in debug mode
        if is_debug_mode():
            logger.debug(f"Configuration saved to {_config_path}")
            
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False

def reset_config_cache():
    """Reset the configuration cache, forcing reload on next access."""
    global _config_cache
    _config_cache = None

def backup_config() -> Optional[str]:
    """
    Create a backup of the current configuration file.
    
    Returns:
        Optional[str]: Backup file path if successful, None otherwise
    """
    if not os.path.exists(_config_path):
        return None
    
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(_config_backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(_config_backup_dir, f"config_{timestamp}.json")
        
        # Copy current config to backup
        shutil.copy2(_config_path, backup_path)
        
        # Clean up old backups (keep 10 most recent)
        cleanup_old_backups(10)
        
        logger.info(f"Configuration backup created at {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Error creating configuration backup: {e}")
        return None

def cleanup_old_backups(keep_count: int = 10):
    """
    Remove old configuration backups, keeping only the most recent ones.
    
    Args:
        keep_count: Number of most recent backups to keep
    """
    try:
        if not os.path.exists(_config_backup_dir):
            return
        
        # Get all backup files
        backups = [
            os.path.join(_config_backup_dir, f) 
            for f in os.listdir(_config_backup_dir) 
            if f.startswith("config_") and f.endswith(".json")
        ]
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Remove old backups
        for backup in backups[keep_count:]:
            os.remove(backup)
            logger.debug(f"Removed old configuration backup: {backup}")
    except Exception as e:
        logger.error(f"Error cleaning up old configuration backups: {e}")

def create_default_config() -> bool:
    """
    Create a default configuration file if one doesn't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global _config_cache
    
    try:
        # Create default configuration
        _config_cache = {
            "general": {
                "version": "0.31.003",
                "maintenance_mode": False,
                "debug": False
            },
            "exploration": {
                "base_spawn_cooldown": 60,
                "vip_spawn_cooldown": 30,
                "patron_spawn_cooldown": 15,
                "supporter_spawn_cooldown": 10,
                "dev_spawn_cooldown": 5,
                "default_catch_item": "standard_capsule",
                "shiny_rate": 0.0005,
                "weather_update_interval": 3600,
                "event_spawn_boost": 1.5
            },
            "battle": {
                "turn_timeout": 120,
                "base_xp_gain": 25,
                "base_token_reward": 10,
                "win_multiplier": 1.5,
                "type_advantage_multiplier": 1.5,
                "critical_hit_chance": 0.0625,
                "critical_hit_multiplier": 1.5
            },
            "evolution": {
                "base_evolution_xp": 100,
                "form_unlock_token_cost": 50,
                "xp_curve_exponent": 1.5
            },
            "trading": {
                "trade_expiry_minutes": 15,
                "max_trade_items": 6,
                "min_level_to_trade": 5
            },
            "economy": {
                "daily_token_bonus": 50,
                "daily_reset_hour": 0,
                "token_cap": 9999,
                "starter_tokens": 100
            },
            "quest": {
                "max_active_quests": 5,
                "daily_quest_count": 3,
                "weekly_quest_count": 1,
                "quest_refresh_hour": 0
            },
            "forms": {
                "stat_modifier_cap": 2.0,
                "retain_forms_on_evolution": True,
                "retain_forms_on_trade": True
            },
            "weather": {
                "update_interval": 3600,
                "extreme_weather_chance": 0.05,
                "weather_duration_variance": 0.2,
                "thunderstorm_shiny_boost": 2.0
            }
        }
        
        # Save to disk
        return save_config()
    except Exception as e:
        logger.error(f"Error creating default configuration: {e}")
        return False

def get_all_configurable_settings() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Get a dictionary of all configurable settings with their descriptions and types.
    This is useful for generating configuration UIs or documentation.
    
    Returns:
        Dict: Nested dictionary with all configurable settings
    """
    return {
        "general": {
            "description": "General bot settings",
            "settings": {
                "version": {
                    "type": "string",
                    "description": "Current version of the bot",
                    "editable": False
                },
                "maintenance_mode": {
                    "type": "boolean",
                    "description": "Whether the bot is in maintenance mode",
                    "editable": True
                },
                "debug": {
                    "type": "boolean",
                    "description": "Enable debug output",
                    "editable": True
                }
            }
        },
        "exploration": {
            "description": "Settings for exploration and encounter mechanics",
            "settings": {
                "base_spawn_cooldown": {
                    "type": "integer",
                    "description": "Base cooldown between spawns in seconds",
                    "editable": True,
                    "min": 5,
                    "max": 3600
                },
                "shiny_rate": {
                    "type": "float",
                    "description": "Chance of encountering a shiny Veramon (0-1)",
                    "editable": True,
                    "min": 0.0001,
                    "max": 0.1
                },
                "weather_update_interval": {
                    "type": "integer",
                    "description": "Time between weather updates in seconds",
                    "editable": True,
                    "min": 300,
                    "max": 86400
                }
                # Additional settings would be defined here
            }
        },
        "battle": {
            "description": "Battle system settings",
            "settings": {
                "turn_timeout": {
                    "type": "integer",
                    "description": "Seconds before a turn times out",
                    "editable": True,
                    "min": 30,
                    "max": 300
                },
                "critical_hit_chance": {
                    "type": "float",
                    "description": "Base chance for critical hits (0-1)",
                    "editable": True,
                    "min": 0.01,
                    "max": 0.25
                }
                # Additional settings would be defined here
            }
        },
        "trading": {
            "description": "Trading system settings",
            "settings": {
                "trade_expiry_minutes": {
                    "type": "integer",
                    "description": "Minutes before a trade expires",
                    "editable": True,
                    "min": 5,
                    "max": 60
                },
                "max_trade_items": {
                    "type": "integer",
                    "description": "Maximum items per trade",
                    "editable": True,
                    "min": 1,
                    "max": 12
                }
                # Additional settings would be defined here
            }
        }
        # Additional sections would be defined here
    }

# Initialize by loading config
try:
    load_config()
except Exception as e:
    logger.error(f"Failed to load initial configuration: {e}")
