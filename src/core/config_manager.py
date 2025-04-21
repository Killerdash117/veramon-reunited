"""
Configuration Manager for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides utilities for loading, saving, and managing
the bot's configuration settings.
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List

# Set up logging
logger = logging.getLogger("config")

# Path to config file
CONFIG_PATH = "data/config.json"

# Ensure config directory exists
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

def get_config() -> Dict[str, Any]:
    """
    Load the current configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        else:
            # If no config exists, create one from defaults
            default_config_path = "src/defaults/default_config.json"
            
            if os.path.exists(default_config_path):
                with open(default_config_path, 'r') as f:
                    default_config = json.load(f)
                
                # Save the default config
                save_config(default_config)
                return default_config
            else:
                # Minimal fallback config
                logger.warning("Default config not found, using minimal config")
                return {"prefix": "!", "setup_completed": False}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {"prefix": "!", "setup_completed": False}

def save_config(config: Dict[str, Any]) -> bool:
    """
    Save the configuration to file.
    
    Args:
        config: Configuration dictionary to save
        
    Returns:
        bool: Success status
    """
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        key: Configuration key to retrieve
        default: Default value if key not found
        
    Returns:
        Any: The configuration value or default
    """
    config = get_config()
    
    # Handle nested keys with dot notation
    if "." in key:
        parts = key.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    
    return config.get(key, default)

def set_config_value(key: str, value: Any) -> bool:
    """
    Set a specific configuration value.
    
    Args:
        key: Configuration key to set
        value: Value to set
        
    Returns:
        bool: Success status
    """
    config = get_config()
    
    # Handle nested keys with dot notation
    if "." in key:
        parts = key.split(".")
        target = config
        for i, part in enumerate(parts[:-1]):
            if part not in target:
                target[part] = {}
            elif not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
    else:
        config[key] = value
    
    return save_config(config)

def get_feature_status(feature_name: str) -> bool:
    """
    Check if a specific feature is enabled.
    
    Args:
        feature_name: Name of the feature to check
        
    Returns:
        bool: Whether the feature is enabled
    """
    return get_config_value(f"features.{feature_name}", True)

def set_feature_status(feature_name: str, enabled: bool) -> bool:
    """
    Enable or disable a specific feature.
    
    Args:
        feature_name: Name of the feature to modify
        enabled: Whether to enable or disable the feature
        
    Returns:
        bool: Success status
    """
    return set_config_value(f"features.{feature_name}", enabled)
