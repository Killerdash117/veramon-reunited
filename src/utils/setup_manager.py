"""
Setup Manager for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module manages the setup process, tracking setup state and providing
utilities for configuring the bot through the setup wizard.
"""

import json
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging

from src.core.config_manager import get_config, save_config

# Set up logging
logger = logging.getLogger("setup")

# Default configuration values
DEFAULT_CONFIG = {
    # General settings
    "prefix": "!",
    "bot_status": "online",
    "bot_status_message": "Veramon Reunited | Use /help",
    "timezone": "UTC",
    "language": "en",
    
    # Game features
    "features": {
        "battle_system": True,
        "trading_system": True,
        "quest_system": True,
        "factions": True,
        "events": True,
        "leaderboards": True,
        "achievements": True,
        "daily_rewards": True
    },
    
    # Economy settings
    "economy": {
        "starting_tokens": 100,
        "daily_tokens": 50,
        "catch_reward": 10,
        "battle_win_reward": 25,
        "quest_reward_multiplier": 1.0,
        "max_transfer_amount": 1000,
        "shop_refresh_hours": 12
    },
    
    # Spawn settings
    "spawns": {
        "spawn_rate_minutes": 15,
        "spawn_rate_messages": 25,
        "max_active_spawns": 5,
        "common_rate": 65,
        "uncommon_rate": 25,
        "rare_rate": 8,
        "epic_rate": 2,
        "shiny_rate": 0.1,
        "enabled_biomes": ["forest", "beach", "mountain", "city", "desert"]
    },
    
    # Channel settings
    "channels": {
        "spawn_channels": [],
        "announcement_channel": None,
        "leaderboard_channel": None,
        "support_channel": None,
        "log_channel": None
    },
    
    # Role settings
    "roles": {
        "admin_role": None,
        "moderator_role": None,
        "vip_role": None
    },
    
    # Security settings
    "security": {
        "max_daily_catches": 100,
        "max_daily_battles": 50,
        "max_token_transfers": 10,
        "catch_cooldown_seconds": 30,
        "battle_cooldown_seconds": 60,
        "trade_cooldown_seconds": 120,
        "ip_rate_limit": True,
        "logging_level": "INFO"
    },
    
    # Setup tracking
    "setup_completed": False,
    "general_settings": {"configured": False},
    "game_features": {"configured": False},
    "economy_settings": {"configured": False},
    "spawn_settings": {"configured": False},
    "channel_setup": {"configured": False},
    "role_config": {"configured": False},
    "security_settings": {"configured": False}
}

class SetupManager:
    """
    Manages the setup wizard process for configuring the bot.
    
    This class provides utilities for tracking setup progress, storing temporary
    setup data, and applying configuration changes.
    """
    
    def __init__(self):
        self.active_setups = {}  # track active setup sessions
    
    def initialize_setup(self, user_id: str, guild_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Initialize a new setup session for a user.
        
        Args:
            user_id: ID of the user starting setup
            guild_id: ID of the guild where setup is being performed
            
        Returns:
            Dict: The initial setup data
        """
        # Load current config
        current_config = get_config()
        
        # Create new setup session
        setup_data = {
            "user_id": user_id,
            "guild_id": guild_id,
            "started_at": datetime.now().isoformat(),
            "current_step": "main",
            "temp_config": current_config.copy(),
            "modified_categories": []
        }
        
        # Store in active setups
        self.active_setups[user_id] = setup_data
        
        # Log setup initiation
        logger.info(f"Setup initiated by user {user_id} for guild {guild_id}")
        
        return setup_data
    
    def get_setup_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the setup data for a specific user."""
        return self.active_setups.get(user_id)
    
    def update_setup_data(self, user_id: str, data: Dict[str, Any]) -> None:
        """Update the setup data for a user."""
        if user_id in self.active_setups:
            self.active_setups[user_id].update(data)
    
    def update_temp_config(self, user_id: str, category: str, settings: Dict[str, Any]) -> bool:
        """
        Update temporary configuration for a category.
        
        Args:
            user_id: ID of the user
            category: Configuration category to update
            settings: New settings to apply
            
        Returns:
            bool: Success status
        """
        if user_id not in self.active_setups:
            return False
        
        setup_data = self.active_setups[user_id]
        
        # Update the temporary configuration
        if category in ["general", "features", "economy", "spawns", "channels", "roles", "security"]:
            # For top-level categories, update directly
            setup_data["temp_config"][category] = settings
        else:
            # For other settings, update specific values
            for key, value in settings.items():
                setup_data["temp_config"][key] = value
        
        # Add to modified categories if not already there
        if category not in setup_data["modified_categories"]:
            setup_data["modified_categories"].append(category)
        
        # Mark category as configured
        category_key = f"{category}_settings" if category not in ["channels", "roles"] else f"{category}_setup" if category == "channels" else f"{category}_config"
        setup_data["temp_config"][category_key] = {"configured": True}
        
        return True
    
    def save_config_changes(self, user_id: str) -> bool:
        """
        Save configuration changes from temporary storage to actual config.
        
        Args:
            user_id: ID of the user who made changes
            
        Returns:
            bool: Success status
        """
        if user_id not in self.active_setups:
            return False
        
        try:
            setup_data = self.active_setups[user_id]
            
            # Get the temporary configuration
            new_config = setup_data["temp_config"]
            
            # Update setup completion status if all categories are configured
            all_configured = True
            for category in ["general_settings", "game_features", "economy_settings", 
                            "spawn_settings", "channel_setup", "role_config", "security_settings"]:
                if not new_config.get(category, {}).get("configured", False):
                    all_configured = False
                    break
            
            if all_configured:
                new_config["setup_completed"] = True
            
            # Add metadata
            new_config["last_updated"] = datetime.now().isoformat()
            new_config["last_updated_by"] = user_id
            
            # Save the configuration
            save_config(new_config)
            
            # Log changes
            categories_changed = ", ".join(setup_data["modified_categories"])
            logger.info(f"Configuration updated by user {user_id}. Categories changed: {categories_changed}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration changes: {e}")
            return False
    
    def discard_changes(self, user_id: str) -> bool:
        """
        Discard unsaved configuration changes.
        
        Args:
            user_id: ID of the user
            
        Returns:
            bool: Success status
        """
        if user_id in self.active_setups:
            # Remove the setup session
            del self.active_setups[user_id]
            return True
        return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration values."""
        return DEFAULT_CONFIG.copy()


def setup_get_category_status(config: Dict[str, Any]) -> Dict[str, bool]:
    """
    Get the configuration status of each setup category.
    
    Args:
        config: Current configuration dictionary
        
    Returns:
        Dict[str, bool]: Dictionary mapping categories to completion status
    """
    return {
        "general_settings": config.get("general_settings", {}).get("configured", False),
        "game_features": config.get("game_features", {}).get("configured", False),
        "economy_settings": config.get("economy_settings", {}).get("configured", False),
        "spawn_settings": config.get("spawn_settings", {}).get("configured", False),
        "channel_setup": config.get("channel_setup", {}).get("configured", False),
        "role_config": config.get("role_config", {}).get("configured", False),
        "security_settings": config.get("security_settings", {}).get("configured", False)
    }
