import discord
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Union
import json
import os
import colorsys
from datetime import datetime

# Constants
DEFAULT_THEME = "default"
USER_THEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_themes")

# Ensure user themes directory exists
os.makedirs(USER_THEMES_DIR, exist_ok=True)

class ThemeColorType(Enum):
    """Types of colors used in the theme system."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"
    NEUTRAL = "neutral"
    ACCENT = "accent"
    BACKGROUND = "background"
    FOREGROUND = "foreground"

class Theme:
    """
    Represents a UI theme for the bot.
    Includes color scheme, fonts, and layout preferences.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.colors = {}
        self.layout = {}
        self.fonts = {}
        self.metadata = {
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        # Initialize with default values
        self._set_default_values()
        
    def _set_default_values(self):
        """Set default values for the theme."""
        # Default color palette
        self.colors = {
            ThemeColorType.PRIMARY.value: 0x3498db,    # Blue
            ThemeColorType.SECONDARY.value: 0x2ecc71,  # Green
            ThemeColorType.SUCCESS.value: 0x2ecc71,    # Green
            ThemeColorType.DANGER.value: 0xe74c3c,     # Red
            ThemeColorType.WARNING.value: 0xf39c12,    # Orange
            ThemeColorType.INFO.value: 0x3498db,       # Blue
            ThemeColorType.NEUTRAL.value: 0x95a5a6,    # Gray
            ThemeColorType.ACCENT.value: 0x9b59b6,     # Purple
            ThemeColorType.BACKGROUND.value: 0x34495e,  # Dark blue
            ThemeColorType.FOREGROUND.value: 0xecf0f1   # Light gray
        }
        
        # Default layout preferences
        self.layout = {
            "compact_mode": False,
            "show_timestamps": True,
            "show_thumbnails": True,
            "embed_border_thickness": 1,
            "rounded_corners": True,
            "use_separators": True,
            "show_footer_text": True,
            "show_author_icon": True,
            "progress_bar_style": "gradient",
            "field_alignment": "auto",
            "image_position": "bottom"
        }
        
        # Default font preferences (Discord handles actual fonts)
        self.fonts = {
            "use_bold_headings": True,
            "use_italics_for_flavor": True,
            "use_code_blocks_for_data": True,
            "emoji_frequency": "medium"  # low, medium, high
        }
        
    def get_color(self, color_type: Union[ThemeColorType, str]) -> int:
        """Get a color value from the theme by its type."""
        if isinstance(color_type, ThemeColorType):
            color_key = color_type.value
        else:
            color_key = color_type
            
        return self.colors.get(color_key, self.colors[ThemeColorType.PRIMARY.value])
        
    def get_color_as_hex(self, color_type: Union[ThemeColorType, str]) -> str:
        """Get a color value as a hex string."""
        color_int = self.get_color(color_type)
        return f"#{color_int:06x}"
        
    def set_color(self, color_type: Union[ThemeColorType, str], color_value: Union[int, str]) -> None:
        """Set a color value in the theme."""
        if isinstance(color_type, ThemeColorType):
            color_key = color_type.value
        else:
            color_key = color_type
            
        # Convert hex string to int if needed
        if isinstance(color_value, str):
            # Remove leading # if present
            if color_value.startswith('#'):
                color_value = color_value[1:]
            color_value = int(color_value, 16)
            
        self.colors[color_key] = color_value
        self.metadata["updated_at"] = datetime.utcnow().isoformat()
        
    def get_layout_option(self, option_key: str) -> Any:
        """Get a layout option from the theme."""
        return self.layout.get(option_key)
        
    def set_layout_option(self, option_key: str, value: Any) -> None:
        """Set a layout option in the theme."""
        self.layout[option_key] = value
        self.metadata["updated_at"] = datetime.utcnow().isoformat()
        
    def get_font_option(self, option_key: str) -> Any:
        """Get a font option from the theme."""
        return self.fonts.get(option_key)
        
    def set_font_option(self, option_key: str, value: Any) -> None:
        """Set a font option in the theme."""
        self.fonts[option_key] = value
        self.metadata["updated_at"] = datetime.utcnow().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the theme to a dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "colors": self.colors,
            "layout": self.layout,
            "fonts": self.fonts,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """Create a theme from a dictionary."""
        theme = cls(data["name"], data.get("description", ""))
        
        # Load values from dictionary
        theme.colors = data.get("colors", theme.colors)
        theme.layout = data.get("layout", theme.layout)
        theme.fonts = data.get("fonts", theme.fonts)
        theme.metadata = data.get("metadata", theme.metadata)
        
        return theme
        
    def create_embed(self, 
                    title: str, 
                    description: str = None, 
                    color_type: Union[ThemeColorType, str] = ThemeColorType.PRIMARY,
                    **kwargs) -> discord.Embed:
        """
        Create a themed embed using this theme's settings.
        
        Args:
            title: The title of the embed
            description: The description of the embed
            color_type: The color type to use for the embed
            **kwargs: Additional arguments to pass to the Embed constructor
            
        Returns:
            A Discord Embed object with theme applied
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=self.get_color(color_type),
            **kwargs
        )
        
        # Apply theme layout options
        if not self.get_layout_option("show_footer_text"):
            embed.set_footer(text="")
            
        return embed
        
    def save(self) -> bool:
        """
        Save the theme to a file.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            theme_file = os.path.join(USER_THEMES_DIR, f"{self.name.lower()}.json")
            with open(theme_file, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving theme: {e}")
            return False
            
    @classmethod
    def load(cls, theme_name: str) -> Optional['Theme']:
        """
        Load a theme from a file.
        
        Args:
            theme_name: The name of the theme to load
            
        Returns:
            A Theme object if successful, None otherwise
        """
        try:
            theme_file = os.path.join(USER_THEMES_DIR, f"{theme_name.lower()}.json")
            if not os.path.exists(theme_file):
                # Try to load from built-in themes
                theme_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                          "data", "themes", f"{theme_name.lower()}.json")
                                          
            if not os.path.exists(theme_file):
                return None
                
            with open(theme_file, 'r') as f:
                theme_data = json.load(f)
                
            return cls.from_dict(theme_data)
        except Exception as e:
            print(f"Error loading theme: {e}")
            return None

class ThemeManager:
    """
    Manages themes for the bot and users.
    """
    
    def __init__(self):
        self.built_in_themes = {}
        self.user_themes = {}
        self.user_preferences = {}
        
        # Load built-in themes
        self._load_built_in_themes()
        
    def _load_built_in_themes(self):
        """Load built-in themes from the themes directory."""
        # Create the default theme
        default_theme = Theme(DEFAULT_THEME, "Default Veramon theme")
        self.built_in_themes[DEFAULT_THEME] = default_theme
        
        # Create a dark theme
        dark_theme = Theme("dark", "Dark mode theme")
        dark_theme.set_color(ThemeColorType.PRIMARY, 0x3498db)  # Blue
        dark_theme.set_color(ThemeColorType.BACKGROUND, 0x2c3e50)  # Dark blue/black
        dark_theme.set_color(ThemeColorType.FOREGROUND, 0xecf0f1)  # White/light gray
        self.built_in_themes["dark"] = dark_theme
        
        # Create a light theme
        light_theme = Theme("light", "Light mode theme")
        light_theme.set_color(ThemeColorType.PRIMARY, 0x3498db)  # Blue
        light_theme.set_color(ThemeColorType.BACKGROUND, 0xecf0f1)  # White/light gray
        light_theme.set_color(ThemeColorType.FOREGROUND, 0x2c3e50)  # Dark blue/black
        self.built_in_themes["light"] = light_theme
        
        # Create a nature theme
        nature_theme = Theme("nature", "Nature-inspired theme")
        nature_theme.set_color(ThemeColorType.PRIMARY, 0x27ae60)  # Green
        nature_theme.set_color(ThemeColorType.SECONDARY, 0xf39c12)  # Orange
        nature_theme.set_color(ThemeColorType.ACCENT, 0x8e44ad)  # Purple
        nature_theme.set_color(ThemeColorType.BACKGROUND, 0x2c3e50)  # Dark blue
        self.built_in_themes["nature"] = nature_theme
        
        # Create a tech theme
        tech_theme = Theme("tech", "Tech-inspired theme")
        tech_theme.set_color(ThemeColorType.PRIMARY, 0x3498db)  # Blue
        tech_theme.set_color(ThemeColorType.SECONDARY, 0x1abc9c)  # Turquoise
        tech_theme.set_color(ThemeColorType.ACCENT, 0xe74c3c)  # Red
        tech_theme.set_color(ThemeColorType.BACKGROUND, 0x34495e)  # Dark navy
        self.built_in_themes["tech"] = tech_theme
        
        # Create a fire theme
        fire_theme = Theme("fire", "Fire-inspired theme")
        fire_theme.set_color(ThemeColorType.PRIMARY, 0xe74c3c)  # Red
        fire_theme.set_color(ThemeColorType.SECONDARY, 0xf39c12)  # Orange
        fire_theme.set_color(ThemeColorType.ACCENT, 0xd35400)  # Dark orange
        fire_theme.set_color(ThemeColorType.BACKGROUND, 0x2c3e50)  # Dark blue
        self.built_in_themes["fire"] = fire_theme
        
        # Create a water theme
        water_theme = Theme("water", "Water-inspired theme")
        water_theme.set_color(ThemeColorType.PRIMARY, 0x3498db)  # Blue
        water_theme.set_color(ThemeColorType.SECONDARY, 0x1abc9c)  # Turquoise
        water_theme.set_color(ThemeColorType.ACCENT, 0x2980b9)  # Dark blue
        water_theme.set_color(ThemeColorType.BACKGROUND, 0x2c3e50)  # Dark navy
        self.built_in_themes["water"] = water_theme
        
    def get_theme(self, theme_name: str = DEFAULT_THEME) -> Theme:
        """
        Get a theme by name. Checks built-in themes first, then user themes.
        
        Args:
            theme_name: The name of the theme to get
            
        Returns:
            The requested Theme or the default theme if not found
        """
        # Check built-in themes first
        if theme_name in self.built_in_themes:
            return self.built_in_themes[theme_name]
            
        # Check user themes next
        if theme_name in self.user_themes:
            return self.user_themes[theme_name]
            
        # Try to load from file
        theme = Theme.load(theme_name)
        if theme:
            self.user_themes[theme_name] = theme
            return theme
            
        # Fall back to default theme
        return self.built_in_themes[DEFAULT_THEME]
        
    def get_user_theme(self, user_id: str) -> Theme:
        """
        Get a user's preferred theme.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            The user's preferred theme or the default theme
        """
        if user_id in self.user_preferences:
            theme_name = self.user_preferences[user_id].get("theme", DEFAULT_THEME)
            return self.get_theme(theme_name)
        return self.get_theme()
        
    def set_user_theme(self, user_id: str, theme_name: str) -> bool:
        """
        Set a user's preferred theme.
        
        Args:
            user_id: The Discord user ID
            theme_name: The name of the theme to use
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure the theme exists
        theme = self.get_theme(theme_name)
        if theme.name != theme_name and theme.name == DEFAULT_THEME:
            return False  # Theme not found
            
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
            
        self.user_preferences[user_id]["theme"] = theme_name
        self._save_user_preferences(user_id)
        return True
        
    def create_user_theme(self, user_id: str, theme_name: str, base_theme: str = DEFAULT_THEME) -> Optional[Theme]:
        """
        Create a new user theme based on an existing theme.
        
        Args:
            user_id: The Discord user ID
            theme_name: The name for the new theme
            base_theme: The name of the theme to base the new theme on
            
        Returns:
            The new Theme if successful, None otherwise
        """
        # Check if the theme name is already taken
        if theme_name in self.built_in_themes or theme_name in self.user_themes:
            return None
            
        # Get the base theme
        base = self.get_theme(base_theme)
        
        # Create a new theme based on the base theme
        new_theme = Theme(theme_name, f"Custom theme created by user {user_id}")
        new_theme.colors = base.colors.copy()
        new_theme.layout = base.layout.copy()
        new_theme.fonts = base.fonts.copy()
        
        # Add to user themes and save
        self.user_themes[theme_name] = new_theme
        new_theme.save()
        
        return new_theme
        
    def list_available_themes(self) -> Dict[str, List[str]]:
        """
        List all available themes.
        
        Returns:
            Dict with built-in and user themes
        """
        return {
            "built_in": list(self.built_in_themes.keys()),
            "user": list(self.user_themes.keys())
        }
        
    def _save_user_preferences(self, user_id: str) -> bool:
        """
        Save a user's preferences to a file.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            prefs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    "data", "user_preferences")
            os.makedirs(prefs_dir, exist_ok=True)
            
            prefs_file = os.path.join(prefs_dir, f"{user_id}.json")
            with open(prefs_file, 'w') as f:
                json.dump(self.user_preferences[user_id], f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving user preferences: {e}")
            return False
            
    def load_user_preferences(self, user_id: str) -> bool:
        """
        Load a user's preferences from a file.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            prefs_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "data", "user_preferences", f"{user_id}.json")
                                     
            if not os.path.exists(prefs_file):
                self.user_preferences[user_id] = {}
                return True
                
            with open(prefs_file, 'r') as f:
                self.user_preferences[user_id] = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading user preferences: {e}")
            self.user_preferences[user_id] = {}
            return False

    def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        Get a user preference.
        
        Args:
            user_id: The Discord user ID
            key: The preference key
            default: Default value if preference doesn't exist
            
        Returns:
            The preference value or default
        """
        if user_id not in self.user_preferences:
            self.load_user_preferences(user_id)
            
        return self.user_preferences.get(user_id, {}).get(key, default)
        
    def set_user_preference(self, user_id: str, key: str, value: Any) -> bool:
        """
        Set a user preference.
        
        Args:
            user_id: The Discord user ID
            key: The preference key
            value: The preference value
            
        Returns:
            True if successful
        """
        if user_id not in self.user_preferences:
            self.load_user_preferences(user_id)
            
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
            
        self.user_preferences[user_id][key] = value
        return self._save_user_preferences(user_id)
        
    def generate_theme_preview(self, theme_name: str) -> discord.Embed:
        """
        Generate a preview embed for a theme.
        
        Args:
            theme_name: The name of the theme to preview
            
        Returns:
            Discord Embed showing the theme colors and appearance
        """
        theme = self.get_theme(theme_name)
        
        embed = theme.create_embed(
            title=f"Theme Preview: {theme.name}",
            description=theme.description or "Theme preview showing colors and appearance."
        )
        
        # Add color swatches
        color_field = ""
        for color_type in ThemeColorType:
            color_hex = theme.get_color_as_hex(color_type)
            color_field += f"**{color_type.value.title()}**: `{color_hex}`\n"
            
        embed.add_field(
            name="Color Palette",
            value=color_field,
            inline=False
        )
        
        # Add layout preview
        layout_field = ""
        for key, value in theme.layout.items():
            layout_field += f"**{key.replace('_', ' ').title()}**: `{value}`\n"
            
        embed.add_field(
            name="Layout Settings",
            value=layout_field,
            inline=False
        )
        
        embed.set_footer(text="This is how your footer text will appear")
        
        return embed

# Create a global theme manager instance
theme_manager = ThemeManager()

# Helper functions for easily creating themed embeds
def create_themed_embed(user_id: str, title: str, description: str = None, 
                       color_type: Union[ThemeColorType, str] = ThemeColorType.PRIMARY,
                       **kwargs) -> discord.Embed:
    """
    Create an embed using the user's preferred theme.
    
    Args:
        user_id: The Discord user ID
        title: The title of the embed
        description: The description of the embed
        color_type: The color type to use for the embed
        **kwargs: Additional arguments to pass to the Embed constructor
        
    Returns:
        A Discord Embed object with the user's theme applied
    """
    theme = theme_manager.get_user_theme(user_id)
    return theme.create_embed(title, description, color_type, **kwargs)
