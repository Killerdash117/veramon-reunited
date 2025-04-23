"""
UI Theme System for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides theme management for all UI components,
allowing for consistent styling across the bot's interface.
"""

import discord
from enum import Enum
from typing import Dict, Any, Optional, List
import json
import os
import logging
from dataclasses import dataclass, field

# Set up logging
logger = logging.getLogger('veramon.ui_theme')

class ThemeColorType(Enum):
    """Types of colors used in themes."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"
    NEUTRAL = "neutral"
    ACCENT = "accent"
    BACKGROUND = "background"
    TEXT = "text"
    MUTED = "muted"
    HIGHLIGHT = "highlight"

@dataclass
class ButtonStyle:
    """Styling for buttons."""
    primary: discord.ButtonStyle = discord.ButtonStyle.primary
    secondary: discord.ButtonStyle = discord.ButtonStyle.secondary
    success: discord.ButtonStyle = discord.ButtonStyle.success
    danger: discord.ButtonStyle = discord.ButtonStyle.danger
    link: discord.ButtonStyle = discord.ButtonStyle.link

@dataclass
class Theme:
    """Theme configuration for UI elements."""
    id: str
    name: str
    description: str
    colors: Dict[ThemeColorType, int]
    button_style: ButtonStyle = field(default_factory=ButtonStyle)
    embed_style: Dict[str, Any] = field(default_factory=dict)
    icon_set: str = "default"
    font_family: str = "default"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """Create a Theme from a dictionary."""
        # Convert color strings to integers
        colors = {}
        for color_type, color_value in data.get("colors", {}).items():
            try:
                # Handle both integer and hex string representations
                if isinstance(color_value, str) and color_value.startswith("#"):
                    colors[ThemeColorType(color_type)] = int(color_value[1:], 16)
                else:
                    colors[ThemeColorType(color_type)] = int(color_value)
            except (ValueError, KeyError):
                logger.warning(f"Invalid color value for {color_type}: {color_value}")
                # Use a default color
                colors[ThemeColorType(color_type)] = 0x5865F2  # Discord blue
        
        # Create button style
        button_style = ButtonStyle()
        
        # Create and return the theme
        return cls(
            id=data.get("id", "default"),
            name=data.get("name", "Default"),
            description=data.get("description", "Default theme"),
            colors=colors,
            button_style=button_style,
            embed_style=data.get("embed_style", {}),
            icon_set=data.get("icon_set", "default"),
            font_family=data.get("font_family", "default")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the theme to a dictionary for serialization."""
        colors_dict = {}
        for color_type, color_value in self.colors.items():
            colors_dict[color_type.value] = f"#{color_value:06x}"
        
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "colors": colors_dict,
            "embed_style": self.embed_style or {},
            "icon_set": self.icon_set,
            "font_family": self.font_family
        }
    
    def get_color(self, color_type: ThemeColorType) -> discord.Color:
        """Get a Discord Color object for the specified color type."""
        color_value = self.colors.get(color_type)
        if color_value is None:
            logger.warning(f"Color type {color_type} not found in theme {self.id}, using default")
            return discord.Color.blurple()
        
        return discord.Color(color_value)
    
    def get_button_style(self, style_name: str) -> discord.ButtonStyle:
        """Get the appropriate button style."""
        if style_name == "primary":
            return self.button_style.primary
        elif style_name == "secondary":
            return self.button_style.secondary
        elif style_name == "success":
            return self.button_style.success
        elif style_name == "danger":
            return self.button_style.danger
        elif style_name == "link":
            return self.button_style.link
        else:
            return discord.ButtonStyle.secondary
    
    def create_embed(self, title: str = None, description: str = None, 
                    color_type: ThemeColorType = ThemeColorType.PRIMARY) -> discord.Embed:
        """Create a themed embed."""
        color = self.get_color(color_type)
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        # Apply theme style if specified
        if self.embed_style:
            if "author_name" in self.embed_style:
                embed.set_author(
                    name=self.embed_style["author_name"],
                    icon_url=self.embed_style.get("author_icon_url")
                )
            
            if "footer_text" in self.embed_style:
                embed.set_footer(
                    text=self.embed_style["footer_text"],
                    icon_url=self.embed_style.get("footer_icon_url")
                )
            
            if "thumbnail_url" in self.embed_style:
                embed.set_thumbnail(url=self.embed_style["thumbnail_url"])
        
        return embed

class ThemeManager:
    """Manages themes for UI components."""
    
    def __init__(self):
        """Initialize the theme manager."""
        self.themes: Dict[str, Theme] = {}
        self.user_themes: Dict[str, str] = {}  # Maps user IDs to theme IDs
        self.default_theme_id = "default"
        self.themes_file = "data/themes.json"
        self.user_themes_file = "data/user_themes.json"
        
        # Create default themes
        self._create_default_themes()
        
        # Load themes from file
        self.load_themes()
        self.load_user_themes()
    
    def _create_default_themes(self):
        """Create default themes."""
        # Default theme - Discord-like
        default_theme = Theme(
            id="default",
            name="Discord Default",
            description="Standard Discord-like theme",
            colors={
                ThemeColorType.PRIMARY: 0x5865F2,    # Blurple
                ThemeColorType.SECONDARY: 0x2D3136,  # Dark gray
                ThemeColorType.SUCCESS: 0x57F287,    # Green
                ThemeColorType.DANGER: 0xED4245,     # Red
                ThemeColorType.WARNING: 0xFEE75C,    # Yellow
                ThemeColorType.INFO: 0x5865F2,       # Blurple
                ThemeColorType.NEUTRAL: 0x4F545C,    # Gray
                ThemeColorType.ACCENT: 0xEB459E,     # Pink
                ThemeColorType.BACKGROUND: 0x36393F, # Dark background
                ThemeColorType.TEXT: 0xFFFFFF,       # White text
                ThemeColorType.MUTED: 0x95A5A6,      # Muted text
                ThemeColorType.HIGHLIGHT: 0xFAA61A   # Orange highlight
            }
        )
        
        # Dark theme
        dark_theme = Theme(
            id="dark",
            name="Dark Mode",
            description="A sleek, dark theme with high contrast",
            colors={
                ThemeColorType.PRIMARY: 0x7289DA,    # Discord blue
                ThemeColorType.SECONDARY: 0x2C2F33,  # Dark gray
                ThemeColorType.SUCCESS: 0x43B581,    # Green
                ThemeColorType.DANGER: 0xF04747,     # Red
                ThemeColorType.WARNING: 0xFAA61A,    # Orange
                ThemeColorType.INFO: 0x00B0F4,       # Light blue
                ThemeColorType.NEUTRAL: 0x747F8D,    # Gray
                ThemeColorType.ACCENT: 0xFF73FA,     # Pink
                ThemeColorType.BACKGROUND: 0x23272A, # Darker background
                ThemeColorType.TEXT: 0xFFFFFF,       # White text
                ThemeColorType.MUTED: 0x72767D,      # Muted text
                ThemeColorType.HIGHLIGHT: 0xFFD700   # Gold highlight
            }
        )
        
        # Veramon theme
        veramon_theme = Theme(
            id="veramon",
            name="Veramon Style",
            description="Themed after the Veramon universe",
            colors={
                ThemeColorType.PRIMARY: 0x3498DB,    # Blue
                ThemeColorType.SECONDARY: 0x2C3E50,  # Dark blue
                ThemeColorType.SUCCESS: 0x2ECC71,    # Green
                ThemeColorType.DANGER: 0xE74C3C,     # Red
                ThemeColorType.WARNING: 0xF39C12,    # Yellow
                ThemeColorType.INFO: 0x3498DB,       # Blue
                ThemeColorType.NEUTRAL: 0x7F8C8D,    # Gray
                ThemeColorType.ACCENT: 0x9B59B6,     # Purple
                ThemeColorType.BACKGROUND: 0x34495E, # Dark blue
                ThemeColorType.TEXT: 0xECF0F1,       # Light gray
                ThemeColorType.MUTED: 0x95A5A6,      # Muted text
                ThemeColorType.HIGHLIGHT: 0xE67E22   # Orange highlight
            }
        )
        
        # High Contrast theme for accessibility
        high_contrast_theme = Theme(
            id="high_contrast",
            name="High Contrast",
            description="High contrast theme for improved accessibility",
            colors={
                ThemeColorType.PRIMARY: 0xFFFFFF,    # White
                ThemeColorType.SECONDARY: 0x000000,  # Black
                ThemeColorType.SUCCESS: 0x00FF00,    # Pure Green
                ThemeColorType.DANGER: 0xFF0000,     # Pure Red
                ThemeColorType.WARNING: 0xFFFF00,    # Yellow
                ThemeColorType.INFO: 0x00FFFF,       # Cyan
                ThemeColorType.NEUTRAL: 0x888888,    # Gray
                ThemeColorType.ACCENT: 0xFF00FF,     # Magenta
                ThemeColorType.BACKGROUND: 0x000000, # Black background
                ThemeColorType.TEXT: 0xFFFFFF,       # White text
                ThemeColorType.MUTED: 0xCCCCCC,      # Light gray
                ThemeColorType.HIGHLIGHT: 0xFFFF00   # Yellow highlight
            }
        )
        
        # Retro Gaming theme
        retro_theme = Theme(
            id="retro",
            name="Retro Gaming",
            description="Classic 8-bit inspired gaming theme",
            colors={
                ThemeColorType.PRIMARY: 0x209CEE,    # Blue
                ThemeColorType.SECONDARY: 0x333333,  # Dark gray
                ThemeColorType.SUCCESS: 0x92CC41,    # NES green
                ThemeColorType.DANGER: 0xE76E55,     # Retro red
                ThemeColorType.WARNING: 0xF7D51D,    # Gold
                ThemeColorType.INFO: 0x209CEE,       # Blue
                ThemeColorType.NEUTRAL: 0x606060,    # Gray
                ThemeColorType.ACCENT: 0xA285E3,     # Purple
                ThemeColorType.BACKGROUND: 0x2A2A2A, # Dark gray
                ThemeColorType.TEXT: 0xF8F8F8,       # Off-white
                ThemeColorType.MUTED: 0x9A9A9A,      # Light gray
                ThemeColorType.HIGHLIGHT: 0xF7D51D   # Gold
            }
        )
        
        # Nature theme
        nature_theme = Theme(
            id="nature",
            name="Natural World",
            description="Earthy tones inspired by nature",
            colors={
                ThemeColorType.PRIMARY: 0x4CAF50,    # Green
                ThemeColorType.SECONDARY: 0x795548,  # Brown
                ThemeColorType.SUCCESS: 0x8BC34A,    # Light green
                ThemeColorType.DANGER: 0xFF5722,     # Deep orange
                ThemeColorType.WARNING: 0xFFC107,    # Amber
                ThemeColorType.INFO: 0x03A9F4,       # Light blue
                ThemeColorType.NEUTRAL: 0x9E9E9E,    # Gray
                ThemeColorType.ACCENT: 0x009688,     # Teal
                ThemeColorType.BACKGROUND: 0x33691E, # Dark green
                ThemeColorType.TEXT: 0xFFFFFF,       # White
                ThemeColorType.MUTED: 0xDCEDC8,      # Light green-gray
                ThemeColorType.HIGHLIGHT: 0xFFEB3B   # Yellow
            }
        )
        
        # Ocean theme
        ocean_theme = Theme(
            id="ocean",
            name="Ocean Depths",
            description="Cool blues inspired by the sea",
            colors={
                ThemeColorType.PRIMARY: 0x0288D1,    # Blue
                ThemeColorType.SECONDARY: 0x263238,  # Dark blue-gray
                ThemeColorType.SUCCESS: 0x26A69A,    # Teal
                ThemeColorType.DANGER: 0xF44336,     # Red
                ThemeColorType.WARNING: 0xFFB74D,    # Orange
                ThemeColorType.INFO: 0x29B6F6,       # Light blue
                ThemeColorType.NEUTRAL: 0x78909C,    # Blue-gray
                ThemeColorType.ACCENT: 0x00BCD4,     # Cyan
                ThemeColorType.BACKGROUND: 0x01579B, # Deep blue
                ThemeColorType.TEXT: 0xE1F5FE,       # Very light blue
                ThemeColorType.MUTED: 0xB3E5FC,      # Lighter blue
                ThemeColorType.HIGHLIGHT: 0x40C4FF   # Light blue accent
            }
        )
        
        # Add themes to the manager
        self.themes["default"] = default_theme
        self.themes["dark"] = dark_theme
        self.themes["veramon"] = veramon_theme
        self.themes["high_contrast"] = high_contrast_theme
        self.themes["retro"] = retro_theme
        self.themes["nature"] = nature_theme
        self.themes["ocean"] = ocean_theme
    
    def load_themes(self):
        """Load themes from file."""
        try:
            if not os.path.exists(self.themes_file):
                # Create themes directory if it doesn't exist
                os.makedirs(os.path.dirname(self.themes_file), exist_ok=True)
                
                # Save default themes
                self.save_themes()
                return
            
            with open(self.themes_file, 'r') as f:
                themes_data = json.load(f)
                
            for theme_data in themes_data:
                theme = Theme.from_dict(theme_data)
                self.themes[theme.id] = theme
                
            logger.info(f"Loaded {len(self.themes)} themes")
        except Exception as e:
            logger.error(f"Error loading themes: {e}")
    
    def save_themes(self):
        """Save themes to file."""
        try:
            # Create themes directory if it doesn't exist
            os.makedirs(os.path.dirname(self.themes_file), exist_ok=True)
            
            themes_data = [theme.to_dict() for theme in self.themes.values()]
            
            with open(self.themes_file, 'w') as f:
                json.dump(themes_data, f, indent=2)
                
            logger.info(f"Saved {len(self.themes)} themes")
        except Exception as e:
            logger.error(f"Error saving themes: {e}")
    
    def load_user_themes(self):
        """Load user theme preferences."""
        try:
            if not os.path.exists(self.user_themes_file):
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.user_themes_file), exist_ok=True)
                return
            
            with open(self.user_themes_file, 'r') as f:
                self.user_themes = json.load(f)
                
            logger.info(f"Loaded {len(self.user_themes)} user theme preferences")
        except Exception as e:
            logger.error(f"Error loading user themes: {e}")
    
    def save_user_themes(self):
        """Save user theme preferences."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.user_themes_file), exist_ok=True)
            
            with open(self.user_themes_file, 'w') as f:
                json.dump(self.user_themes, f, indent=2)
                
            logger.info(f"Saved {len(self.user_themes)} user theme preferences")
        except Exception as e:
            logger.error(f"Error saving user themes: {e}")
    
    def get_theme(self, theme_id: str) -> Theme:
        """Get a theme by ID."""
        return self.themes.get(theme_id, self.themes[self.default_theme_id])
    
    def get_user_theme(self, user_id: str) -> Theme:
        """Get a user's preferred theme."""
        theme_id = self.user_themes.get(str(user_id), self.default_theme_id)
        return self.get_theme(theme_id)
    
    def set_user_theme(self, user_id: str, theme_id: str) -> bool:
        """Set a user's preferred theme."""
        if theme_id not in self.themes:
            return False
        
        self.user_themes[str(user_id)] = theme_id
        self.save_user_themes()
        return True
    
    def create_theme(self, theme: Theme) -> bool:
        """Create a new theme."""
        if theme.id in self.themes:
            return False
        
        self.themes[theme.id] = theme
        self.save_themes()
        return True
    
    def update_theme(self, theme: Theme) -> bool:
        """Update an existing theme."""
        if theme.id not in self.themes:
            return False
        
        self.themes[theme.id] = theme
        self.save_themes()
        return True
    
    def delete_theme(self, theme_id: str) -> bool:
        """Delete a theme."""
        if theme_id == self.default_theme_id:
            return False  # Can't delete default theme
        
        if theme_id not in self.themes:
            return False
        
        del self.themes[theme_id]
        
        # Update users who were using this theme
        for user_id, user_theme_id in self.user_themes.items():
            if user_theme_id == theme_id:
                self.user_themes[user_id] = self.default_theme_id
        
        self.save_themes()
        self.save_user_themes()
        return True
    
    def get_themed_embed(self, user_id: str, title: str = None, description: str = None, 
                        color_type: ThemeColorType = ThemeColorType.PRIMARY) -> discord.Embed:
        """Create a themed embed for a user."""
        theme = self.get_user_theme(user_id)
        return theme.create_embed(title, description, color_type)

# Create global instance
theme_manager = ThemeManager()

def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return theme_manager
