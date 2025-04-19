import discord
from discord.ext import commands
from discord import app_commands
import json
from typing import Dict, Any, Optional, List, Union
import os

from src.utils.user_settings import UserSettings, get_user_settings
from src.utils.ui_theme import theme_manager, ThemeColorType, create_themed_embed
from src.models.permissions import require_permission_level, PermissionLevel, is_vip

class SettingsView(discord.ui.View):
    """
    View for managing user settings through interactive buttons.
    """
    
    def __init__(self, settings: UserSettings, category: str = "ui"):
        super().__init__(timeout=180)  # 3 minute timeout
        self.settings = settings
        self.current_category = category
        
    @discord.ui.button(label="UI Settings", style=discord.ButtonStyle.primary)
    async def ui_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show UI settings."""
        await self.show_category(interaction, "ui")
        
    @discord.ui.button(label="Gameplay", style=discord.ButtonStyle.primary)
    async def gameplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show gameplay settings."""
        await self.show_category(interaction, "gameplay")
        
    @discord.ui.button(label="Notifications", style=discord.ButtonStyle.primary)
    async def notifications_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show notification settings."""
        await self.show_category(interaction, "notifications")
        
    @discord.ui.button(label="Privacy", style=discord.ButtonStyle.primary)
    async def privacy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show privacy settings."""
        await self.show_category(interaction, "privacy")
        
    @discord.ui.button(label="Accessibility", style=discord.ButtonStyle.primary)
    async def accessibility_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show accessibility settings."""
        await self.show_category(interaction, "accessibility")
        
    async def show_category(self, interaction: discord.Interaction, category: str):
        """Show settings for a specific category."""
        self.current_category = category
        
        # Create embed based on category
        if category == "ui":
            settings_data = self.settings.get_ui_settings()
            title = "UI Settings"
            description = "Customize how Veramon Reunited looks"
        elif category == "gameplay":
            settings_data = self.settings.get_gameplay_settings()
            title = "Gameplay Settings"
            description = "Customize your gameplay experience"
        elif category == "notifications":
            settings_data = self.settings.get_notification_settings()
            title = "Notification Settings"
            description = "Control what notifications you receive"
        elif category == "privacy":
            settings_data = self.settings.get_privacy_settings()
            title = "Privacy Settings"
            description = "Control who can see your information"
        elif category == "accessibility":
            settings_data = self.settings.get_accessibility_settings()
            title = "Accessibility Settings"
            description = "Customize for better accessibility"
        else:
            settings_data = {}
            title = "Settings"
            description = "Select a category above"
            
        # Create the embed
        embed = create_themed_embed(
            str(interaction.user.id),
            title=title,
            description=description,
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add settings as fields
        for key, value in settings_data.items():
            # Convert the key to a more readable format
            display_key = key.replace("_", " ").title()
            
            # Format the value for display
            if isinstance(value, bool):
                display_value = "✅ Enabled" if value else "❌ Disabled"
            else:
                display_value = str(value).title()
                
            embed.add_field(
                name=display_key,
                value=f"`{display_value}`",
                inline=True
            )
            
        # Add instructions
        embed.add_field(
            name="How to Change Settings",
            value="Use `/settings set [setting] [value]` to change a setting\n"
                  "Example: `/settings set theme dark`",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

class SettingsCog(commands.Cog):
    """
    Commands for managing user settings and preferences.
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="settings", description="View and manage your personal settings")
    async def settings(self, interaction: discord.Interaction):
        """View your current settings."""
        settings = get_user_settings(str(interaction.user.id))
        
        # Create the embed
        embed = create_themed_embed(
            str(interaction.user.id),
            title="Veramon Reunited Settings",
            description="Customize your experience with the settings below.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add sections overview
        embed.add_field(
            name="UI Settings",
            value="Theme, layout, animations, and visual preferences",
            inline=False
        )
        
        embed.add_field(
            name="Gameplay Settings",
            value="Battle animation speed, auto-heal, confirmation prompts",
            inline=False
        )
        
        embed.add_field(
            name="Notification Settings",
            value="Control what notifications you receive",
            inline=False
        )
        
        embed.add_field(
            name="Privacy Settings",
            value="Control who can see your information",
            inline=False
        )
        
        embed.add_field(
            name="Accessibility Settings",
            value="High contrast mode, text size, screen reader support",
            inline=False
        )
        
        # Create and send view
        view = SettingsView(settings)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @app_commands.command(name="theme", description="View and change your theme")
    @app_commands.describe(
        theme_name="The name of the theme to preview or set as your theme"
    )
    async def theme(self, interaction: discord.Interaction, theme_name: Optional[str] = None):
        """View available themes or set your theme."""
        user_id = str(interaction.user.id)
        
        if theme_name:
            # Try to set the theme
            success = theme_manager.set_user_theme(user_id, theme_name)
            
            if success:
                # Show preview of the new theme
                embed = theme_manager.generate_theme_preview(theme_name)
                embed.title = f"Theme Changed to {theme_name.title()}"
                embed.description = "Your theme has been updated."
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Theme '{theme_name}' not found. Use `/theme` to see available themes.",
                    ephemeral=True
                )
        else:
            # Show available themes
            themes = theme_manager.list_available_themes()
            
            embed = create_themed_embed(
                user_id,
                title="Available Themes",
                description="Choose a theme to customize your Veramon Reunited experience.",
                color_type=ThemeColorType.PRIMARY
            )
            
            # Add built-in themes
            built_in_themes = "\n".join([f"• `{theme}`" for theme in themes["built_in"]])
            embed.add_field(
                name="Built-in Themes",
                value=built_in_themes or "No built-in themes available",
                inline=False
            )
            
            # Add user themes if any
            if themes["user"]:
                user_themes = "\n".join([f"• `{theme}`" for theme in themes["user"]])
                embed.add_field(
                    name="Custom Themes",
                    value=user_themes,
                    inline=False
                )
                
            # Add instructions
            embed.add_field(
                name="How to Change Theme",
                value="Use `/theme [theme_name]` to set your theme\n"
                      "Example: `/theme dark`",
                inline=False
            )
            
            # If user is VIP, add info about custom themes
            settings = get_user_settings(user_id)
            if await is_vip().predicate(interaction):
                embed.add_field(
                    name="VIP Feature: Custom Themes",
                    value="VIP users can create custom themes with `/theme_create`",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="settings_set", description="Change a specific setting")
    @app_commands.describe(
        setting="The setting to change",
        value="The new value for the setting"
    )
    async def settings_set(self, interaction: discord.Interaction, setting: str, value: str):
        """Change a specific setting."""
        user_id = str(interaction.user.id)
        settings = get_user_settings(user_id)
        
        # Check if setting exists
        if setting not in settings.settings:
            await interaction.response.send_message(
                f"Setting '{setting}' not found. Use `/settings` to see available settings.",
                ephemeral=True
            )
            return
            
        # Convert value to appropriate type
        current_value = settings.get(setting)
        
        if isinstance(current_value, bool):
            if value.lower() in ["true", "yes", "on", "1", "enable", "enabled"]:
                new_value = True
            elif value.lower() in ["false", "no", "off", "0", "disable", "disabled"]:
                new_value = False
            else:
                await interaction.response.send_message(
                    f"Invalid value for boolean setting. Use true/false, yes/no, on/off, or enable/disable.",
                    ephemeral=True
                )
                return
        elif isinstance(current_value, int):
            try:
                new_value = int(value)
            except ValueError:
                await interaction.response.send_message(
                    f"Invalid value for integer setting. Please provide a number.",
                    ephemeral=True
                )
                return
        else:
            # String or enum value
            new_value = value
            
        # Update the setting
        success = settings.set(setting, new_value)
        
        if success:
            # Special case for theme setting
            if setting == "theme":
                theme_manager.set_user_theme(user_id, new_value)
                
            embed = create_themed_embed(
                user_id,
                title="Setting Updated",
                description=f"Your setting has been updated.",
                color_type=ThemeColorType.SUCCESS
            )
            
            embed.add_field(
                name="Setting",
                value=setting.replace("_", " ").title(),
                inline=True
            )
            
            embed.add_field(
                name="New Value",
                value=str(new_value),
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Failed to update setting. Please try again later.",
                ephemeral=True
            )
            
    @app_commands.command(name="theme_preview", description="Preview a theme")
    @app_commands.describe(
        theme_name="The name of the theme to preview"
    )
    async def theme_preview(self, interaction: discord.Interaction, theme_name: str):
        """Preview a theme without changing your settings."""
        # Get the theme preview
        embed = theme_manager.generate_theme_preview(theme_name)
        
        # Add instructions
        embed.add_field(
            name="Apply This Theme",
            value=f"Use `/theme {theme_name}` to apply this theme",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="theme_create", description="Create a custom theme (VIP Only)")
    @app_commands.describe(
        theme_name="Name for your custom theme",
        base_theme="Theme to use as a starting point"
    )
    @is_vip()
    async def theme_create(self, interaction: discord.Interaction, theme_name: str, base_theme: str = "default"):
        """Create a custom theme (VIP only)."""
        user_id = str(interaction.user.id)
        
        # Create the theme
        new_theme = theme_manager.create_user_theme(user_id, theme_name, base_theme)
        
        if new_theme:
            embed = create_themed_embed(
                user_id,
                title="Custom Theme Created",
                description=f"Your custom theme '{theme_name}' has been created based on the {base_theme} theme.",
                color_type=ThemeColorType.SUCCESS
            )
            
            embed.add_field(
                name="Next Steps",
                value="Use `/theme_edit` to customize your theme colors and settings",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Failed to create theme. The name '{theme_name}' may already be in use.",
                ephemeral=True
            )
            
    @app_commands.command(name="settings_reset", description="Reset your settings to default values")
    @app_commands.describe(
        setting="Specific setting to reset, or 'all' to reset everything"
    )
    async def settings_reset(self, interaction: discord.Interaction, setting: str = "all"):
        """Reset settings to default values."""
        user_id = str(interaction.user.id)
        settings = get_user_settings(user_id)
        
        if setting.lower() == "all":
            # Reset all settings
            success = settings.reset()
            message = "All settings have been reset to default values."
        else:
            # Reset specific setting
            if setting not in settings.settings:
                await interaction.response.send_message(
                    f"Setting '{setting}' not found. Use `/settings` to see available settings.",
                    ephemeral=True
                )
                return
                
            success = settings.reset(setting)
            message = f"The setting '{setting}' has been reset to its default value."
            
        if success:
            embed = create_themed_embed(
                user_id,
                title="Settings Reset",
                description=message,
                color_type=ThemeColorType.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Failed to reset settings. Please try again later.",
                ephemeral=True
            )

async def setup(bot):
    """Add the SettingsCog to the bot."""
    await bot.add_cog(SettingsCog(bot))
