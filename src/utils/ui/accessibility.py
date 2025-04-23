"""
Accessibility Options for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides accessibility features and settings for the bot interface.
"""

import json
import os
import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Set up logging
logger = logging.getLogger('veramon.accessibility')

class TextSize(Enum):
    """Text size options for UI elements."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"

class UpdateFrequency(Enum):
    """Controls frequency of UI updates in Discord messages."""
    STANDARD = "standard"   # Regular UI updates for state changes
    REDUCED = "reduced"     # Only critical UI updates
    MINIMAL = "minimal"     # Only absolutely necessary UI updates

class ColorMode(Enum):
    """Color mode options."""
    NORMAL = "normal"             # Default colors
    HIGH_CONTRAST = "high_contrast"  # High contrast for visibility
    DEUTERANOPIA = "deuteranopia" # Green-blind friendly
    PROTANOPIA = "protanopia"     # Red-blind friendly
    TRITANOPIA = "tritanopia"     # Blue-blind friendly
    MONOCHROME = "monochrome"     # Grayscale mode

@dataclass
class AccessibilitySettings:
    """User accessibility settings."""
    user_id: str
    text_size: TextSize = TextSize.MEDIUM
    update_frequency: UpdateFrequency = UpdateFrequency.STANDARD
    color_mode: ColorMode = ColorMode.NORMAL
    screen_reader_support: bool = False
    simplified_ui: bool = False
    extra_button_spacing: bool = False
    extended_interaction_timeouts: bool = False
    always_include_alt_text: bool = True
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessibilitySettings':
        """Create settings from a dictionary."""
        # Extract basic fields with error handling
        user_id = data.get("user_id", "unknown")
        
        # Parse enums with fallbacks
        try:
            text_size = TextSize(data.get("text_size", TextSize.MEDIUM.value))
        except ValueError:
            text_size = TextSize.MEDIUM
            
        try:
            update_frequency = UpdateFrequency(data.get("update_frequency", UpdateFrequency.STANDARD.value))
        except ValueError:
            update_frequency = UpdateFrequency.STANDARD
            
        try:
            color_mode = ColorMode(data.get("color_mode", ColorMode.NORMAL.value))
        except ValueError:
            color_mode = ColorMode.NORMAL
        
        # Extract boolean settings with defaults
        screen_reader = data.get("screen_reader_support", False)
        simplified_ui = data.get("simplified_ui", False)
        extra_spacing = data.get("extra_button_spacing", False)
        extended_timeouts = data.get("extended_interaction_timeouts", False)
        include_alt_text = data.get("always_include_alt_text", True)
        
        # Extract custom settings
        custom = data.get("custom_settings", {})
        
        return cls(
            user_id=user_id,
            text_size=text_size,
            update_frequency=update_frequency,
            color_mode=color_mode,
            screen_reader_support=screen_reader,
            simplified_ui=simplified_ui,
            extra_button_spacing=extra_spacing,
            extended_interaction_timeouts=extended_timeouts,
            always_include_alt_text=include_alt_text,
            custom_settings=custom
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to a dictionary."""
        return {
            "user_id": self.user_id,
            "text_size": self.text_size.value,
            "update_frequency": self.update_frequency.value,
            "color_mode": self.color_mode.value,
            "screen_reader_support": self.screen_reader_support,
            "simplified_ui": self.simplified_ui,
            "extra_button_spacing": self.extra_button_spacing,
            "extended_interaction_timeouts": self.extended_interaction_timeouts,
            "always_include_alt_text": self.always_include_alt_text,
            "custom_settings": self.custom_settings
        }
    
    def update(self, settings: Dict[str, Any]) -> 'AccessibilitySettings':
        """Update settings with new values."""
        # Update text size if valid
        if "text_size" in settings:
            try:
                self.text_size = TextSize(settings["text_size"])
            except ValueError:
                logger.warning(f"Invalid text size: {settings['text_size']}")
        
        # Update update frequency if valid
        if "update_frequency" in settings:
            try:
                self.update_frequency = UpdateFrequency(settings["update_frequency"])
            except ValueError:
                logger.warning(f"Invalid update frequency: {settings['update_frequency']}")
        
        # Update color mode if valid
        if "color_mode" in settings:
            try:
                self.color_mode = ColorMode(settings["color_mode"])
            except ValueError:
                logger.warning(f"Invalid color mode: {settings['color_mode']}")
        
        # Update boolean settings
        for key in [
            "screen_reader_support", 
            "simplified_ui", 
            "extra_button_spacing",
            "extended_interaction_timeouts",
            "always_include_alt_text"
        ]:
            if key in settings:
                setattr(self, key, bool(settings[key]))
        
        # Update custom settings
        if "custom_settings" in settings and isinstance(settings["custom_settings"], dict):
            self.custom_settings.update(settings["custom_settings"])
        
        return self

class AccessibilityManager:
    """Manages accessibility settings for all users."""
    
    def __init__(self):
        """Initialize the accessibility manager."""
        self.settings: Dict[str, AccessibilitySettings] = {}
        self.settings_file = "data/accessibility.json"
        
        # Create default settings
        self._create_defaults()
        
        # Load settings from file
        self.load_settings()
    
    def _create_defaults(self):
        """Create default settings."""
        # Global default settings (not tied to a user)
        self.default_settings = AccessibilitySettings(
            user_id="default",
            text_size=TextSize.MEDIUM,
            update_frequency=UpdateFrequency.STANDARD,
            color_mode=ColorMode.NORMAL,
            screen_reader_support=False,
            simplified_ui=False,
            extra_button_spacing=False,
            extended_interaction_timeouts=False,
            always_include_alt_text=True
        )
    
    def load_settings(self):
        """Load settings from file."""
        try:
            if not os.path.exists(self.settings_file):
                # Create data directory if it doesn't exist
                os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
                self.save_settings()
                return
            
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
            
            for user_id, settings_data in data.items():
                self.settings[user_id] = AccessibilitySettings.from_dict(settings_data)
            
            logger.info(f"Loaded accessibility settings for {len(self.settings)} users")
        except Exception as e:
            logger.error(f"Error loading accessibility settings: {e}")
    
    def save_settings(self):
        """Save settings to file."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            data = {user_id: settings.to_dict() for user_id, settings in self.settings.items()}
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved accessibility settings for {len(self.settings)} users")
        except Exception as e:
            logger.error(f"Error saving accessibility settings: {e}")
    
    def get_settings(self, user_id: str) -> AccessibilitySettings:
        """Get settings for a user."""
        if user_id not in self.settings:
            # Create default settings for this user
            self.settings[user_id] = AccessibilitySettings(
                user_id=user_id,
                text_size=self.default_settings.text_size,
                update_frequency=self.default_settings.update_frequency,
                color_mode=self.default_settings.color_mode,
                screen_reader_support=self.default_settings.screen_reader_support,
                simplified_ui=self.default_settings.simplified_ui,
                extra_button_spacing=self.default_settings.extra_button_spacing,
                extended_interaction_timeouts=self.default_settings.extended_interaction_timeouts,
                always_include_alt_text=self.default_settings.always_include_alt_text
            )
            self.save_settings()
        
        return self.settings[user_id]
    
    def update_settings(self, user_id: str, settings: Dict[str, Any]) -> AccessibilitySettings:
        """Update settings for a user."""
        user_settings = self.get_settings(user_id)
        user_settings.update(settings)
        self.save_settings()
        return user_settings
    
    def reset_settings(self, user_id: str) -> AccessibilitySettings:
        """Reset settings to defaults for a user."""
        self.settings[user_id] = AccessibilitySettings(
            user_id=user_id,
            text_size=self.default_settings.text_size,
            update_frequency=self.default_settings.update_frequency,
            color_mode=self.default_settings.color_mode,
            screen_reader_support=self.default_settings.screen_reader_support,
            simplified_ui=self.default_settings.simplified_ui,
            extra_button_spacing=self.default_settings.extra_button_spacing,
            extended_interaction_timeouts=self.default_settings.extended_interaction_timeouts,
            always_include_alt_text=self.default_settings.always_include_alt_text
        )
        self.save_settings()
        return self.settings[user_id]

# Global instance
accessibility_manager = AccessibilityManager()

def get_accessibility_manager() -> AccessibilityManager:
    """Get the global accessibility manager instance."""
    return accessibility_manager

# Helper functions for UI components

def apply_text_size(text: str, text_size: TextSize) -> str:
    """Apply text size formatting to text."""
    if text_size == TextSize.SMALL:
        return text  # No change
    elif text_size == TextSize.MEDIUM:
        return text  # Default size
    elif text_size == TextSize.LARGE:
        return f"**{text}**"  # Bold for larger text
    elif text_size == TextSize.EXTRA_LARGE:
        return f"# {text}"  # Heading for extra large text
    return text

def apply_color_mode(hex_color: int, color_mode: ColorMode) -> int:
    """Adjust color based on color mode."""
    if color_mode == ColorMode.NORMAL:
        return hex_color  # No change
    
    # Extract RGB components
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    
    if color_mode == ColorMode.HIGH_CONTRAST:
        # Enhance contrast by pushing colors to extremes
        r = 255 if r > 127 else 0
        g = 255 if g > 127 else 0
        b = 255 if b > 127 else 0
    
    elif color_mode == ColorMode.DEUTERANOPIA:
        # Adjust for green-blindness
        r_new = int(0.625 * r + 0.375 * g)
        g_new = int(0.7 * r + 0.3 * g)
        b_new = b
        r, g, b = r_new, g_new, b_new
    
    elif color_mode == ColorMode.PROTANOPIA:
        # Adjust for red-blindness
        r_new = int(0.567 * r + 0.433 * g)
        g_new = int(0.558 * r + 0.442 * g)
        b_new = b
        r, g, b = r_new, g_new, b_new
    
    elif color_mode == ColorMode.TRITANOPIA:
        # Adjust for blue-blindness
        r_new = r
        g_new = int(0.7 * g + 0.3 * b)
        b_new = int(0.3 * g + 0.7 * b)
        r, g, b = r_new, g_new, b_new
    
    elif color_mode == ColorMode.MONOCHROME:
        # Convert to grayscale
        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
        r = g = b = gray
    
    # Ensure values are in valid range
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    
    # Recombine into hex
    return (r << 16) | (g << 8) | b

def get_alt_text(image_type: str, context: Dict[str, Any] = None) -> str:
    """Generate alt text for images based on context."""
    context = context or {}
    
    if image_type == "veramon":
        veramon_name = context.get("name", "Unknown Veramon")
        veramon_type = context.get("type", "Unknown type")
        return f"Image of {veramon_name}, a {veramon_type} type Veramon"
    
    elif image_type == "battle":
        attacker = context.get("attacker", "Unknown")
        defender = context.get("defender", "Unknown")
        return f"Battle scene between {attacker} and {defender}"
    
    elif image_type == "item":
        item_name = context.get("name", "Unknown item")
        return f"Image of {item_name} item"
    
    elif image_type == "location":
        location_name = context.get("name", "Unknown location")
        return f"Image of {location_name} location"
    
    return "Image"

def simplify_embed(embed_data: Dict[str, Any], simplified: bool = False) -> Dict[str, Any]:
    """Simplify an embed for better readability."""
    if not simplified:
        return embed_data
    
    # Make a copy to avoid modifying the original
    simplified_embed = embed_data.copy()
    
    # Simplify title and description
    if "title" in simplified_embed:
        simplified_embed["title"] = simplified_embed["title"].replace("*", "").replace("_", "")
    
    if "description" in simplified_embed:
        # Remove complex formatting
        desc = simplified_embed["description"]
        desc = desc.replace("*", "").replace("_", "")
        
        # Add spacing between sections
        desc = desc.replace(".\n", ".\n\n")
        
        simplified_embed["description"] = desc
    
    # Simplify fields
    if "fields" in simplified_embed:
        for field in simplified_embed["fields"]:
            if "name" in field:
                field["name"] = field["name"].replace("*", "").replace("_", "")
            if "value" in field:
                field["value"] = field["value"].replace("*", "").replace("_", "")
                field["value"] = field["value"].replace(".\n", ".\n\n")
    
    return simplified_embed
