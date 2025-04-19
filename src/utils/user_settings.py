import discord
from typing import Dict, Any, Optional, List, Union
import json
import os
from enum import Enum

# Constants
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_settings")

# Ensure settings directory exists
os.makedirs(SETTINGS_DIR, exist_ok=True)

class NotificationLevel(Enum):
    """User notification preference levels"""
    ALL = "all"           # All notifications
    IMPORTANT = "important"  # Only important notifications
    MINIMAL = "minimal"   # Minimal notifications
    NONE = "none"         # No notifications

class PrivacyLevel(Enum):
    """User privacy preference levels"""
    PUBLIC = "public"     # All information is public
    FRIENDS = "friends"   # Only friends can see information
    PRIVATE = "private"   # Information is private

class BattleAnimationSpeed(Enum):
    """Battle animation speed preferences"""
    SLOW = "slow"         # Slow animations
    NORMAL = "normal"     # Normal speed animations
    FAST = "fast"         # Fast animations
    INSTANT = "instant"   # No animations

class UserSettings:
    """
    A class to manage user settings and preferences.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.settings = {
            # UI Settings
            "theme": "default",
            "compact_mode": False,
            "show_animations": True,
            "show_tips": True,
            "show_veramon_images": True,
            "embed_style": "default",
            
            # Notification Settings
            "notification_level": NotificationLevel.ALL.value,
            "trade_notifications": True,
            "battle_notifications": True,
            "event_notifications": True,
            "friend_notifications": True,
            
            # Privacy Settings
            "profile_privacy": PrivacyLevel.PUBLIC.value,
            "collection_privacy": PrivacyLevel.PUBLIC.value,
            "activity_privacy": PrivacyLevel.PUBLIC.value,
            "hide_online_status": False,
            
            # Gameplay Settings
            "battle_animation_speed": BattleAnimationSpeed.NORMAL.value,
            "auto_claim_rewards": False,
            "confirm_trades": True,
            "default_battle_team": 1,
            "auto_heal": False,
            
            # Accessibility Settings
            "high_contrast_mode": False,
            "text_size": "medium",
            "use_screen_reader_hints": False,
            "reduce_animations": False,
            
            # Advanced Settings
            "show_detailed_stats": False,
            "developer_mode": False,
            "experimental_features": False
        }
        
        # Load existing settings if available
        self.load()
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
        
    def set(self, key: str, value: Any) -> bool:
        """Set a setting value and save."""
        if key in self.settings:
            self.settings[key] = value
            return self.save()
        return False
        
    def reset(self, key: str = None) -> bool:
        """Reset settings to default values."""
        if key:
            # Reset specific setting
            default_settings = UserSettings("temp").settings
            if key in default_settings:
                self.settings[key] = default_settings[key]
        else:
            # Reset all settings
            default_settings = UserSettings("temp").settings
            self.settings = default_settings.copy()
            
        return self.save()
        
    def save(self) -> bool:
        """Save settings to file."""
        try:
            settings_file = os.path.join(SETTINGS_DIR, f"{self.user_id}.json")
            with open(settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
            
    def load(self) -> bool:
        """Load settings from file."""
        try:
            settings_file = os.path.join(SETTINGS_DIR, f"{self.user_id}.json")
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    loaded_settings = json.load(f)
                    
                    # Update settings with loaded values
                    # Only update keys that already exist in the default settings
                    for key, value in loaded_settings.items():
                        if key in self.settings:
                            self.settings[key] = value
                            
                return True
            return False
        except Exception as e:
            print(f"Error loading settings: {e}")
            return False
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return self.settings.copy()
        
    def from_dict(self, settings_dict: Dict[str, Any]) -> bool:
        """Update settings from dictionary."""
        for key, value in settings_dict.items():
            if key in self.settings:
                self.settings[key] = value
                
        return self.save()
        
    def get_notification_settings(self) -> Dict[str, Any]:
        """Get notification-related settings."""
        return {
            "notification_level": self.get("notification_level"),
            "trade_notifications": self.get("trade_notifications"),
            "battle_notifications": self.get("battle_notifications"),
            "event_notifications": self.get("event_notifications"),
            "friend_notifications": self.get("friend_notifications")
        }
        
    def get_ui_settings(self) -> Dict[str, Any]:
        """Get UI-related settings."""
        return {
            "theme": self.get("theme"),
            "compact_mode": self.get("compact_mode"),
            "show_animations": self.get("show_animations"),
            "show_tips": self.get("show_tips"),
            "show_veramon_images": self.get("show_veramon_images"),
            "embed_style": self.get("embed_style")
        }
        
    def get_privacy_settings(self) -> Dict[str, Any]:
        """Get privacy-related settings."""
        return {
            "profile_privacy": self.get("profile_privacy"),
            "collection_privacy": self.get("collection_privacy"),
            "activity_privacy": self.get("activity_privacy"),
            "hide_online_status": self.get("hide_online_status")
        }
        
    def get_gameplay_settings(self) -> Dict[str, Any]:
        """Get gameplay-related settings."""
        return {
            "battle_animation_speed": self.get("battle_animation_speed"),
            "auto_claim_rewards": self.get("auto_claim_rewards"),
            "confirm_trades": self.get("confirm_trades"),
            "default_battle_team": self.get("default_battle_team"),
            "auto_heal": self.get("auto_heal")
        }
        
    def get_accessibility_settings(self) -> Dict[str, Any]:
        """Get accessibility-related settings."""
        return {
            "high_contrast_mode": self.get("high_contrast_mode"),
            "text_size": self.get("text_size"),
            "use_screen_reader_hints": self.get("use_screen_reader_hints"),
            "reduce_animations": self.get("reduce_animations")
        }

# Helper function to get a user's settings
def get_user_settings(user_id: str) -> UserSettings:
    """Get a user's settings."""
    return UserSettings(user_id)
