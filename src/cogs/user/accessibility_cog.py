"""
Accessibility Commands for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides commands for users to customize accessibility settings.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List

from src.utils.ui.accessibility import (
    get_accessibility_manager, 
    AccessibilitySettings,
    TextSize, 
    UpdateFrequency, 
    ColorMode
)
from src.utils.ui.accessibility_ui import AccessibilitySettingsView
from src.utils.ui_theme import theme_manager, ThemeColorType

# Set up logging
logger = logging.getLogger('veramon.accessibility_cog')

class AccessibilityCog(commands.Cog):
    """Commands for accessibility features."""
    
    def __init__(self, bot):
        self.bot = bot
        self.accessibility_manager = get_accessibility_manager()
    
    @app_commands.command(
        name="accessibility",
        description="Open the accessibility settings menu to customize your experience"
    )
    async def accessibility_settings(self, interaction: discord.Interaction):
        """Open the accessibility settings menu."""
        user_id = str(interaction.user.id)
        
        # Get current settings
        settings = self.accessibility_manager.get_settings(user_id)
        
        # Get user's theme
        theme = theme_manager.get_user_theme(user_id)
        
        # Create an embed to display current settings
        embed = theme.create_embed(
            title="Accessibility Settings",
            description="Customize your experience with accessibility options. Use the tabs below to navigate through different settings categories.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add summary of current settings
        embed.add_field(
            name="Current Settings",
            value=(
                f"**Text Size:** {settings.text_size.value}\n"
                f"**Visual Update Frequency:** {settings.update_frequency.value}\n"
                f"**Color Mode:** {settings.color_mode.value}\n"
                f"**Screen Reader Support:** {'Enabled' if settings.screen_reader_support else 'Disabled'}\n"
                f"**Simplified UI:** {'Enabled' if settings.simplified_ui else 'Disabled'}"
            ),
            inline=False
        )
        
        # Add navigation instructions
        embed.add_field(
            name="Navigation",
            value="Use the tabs below to navigate between different categories of settings.",
            inline=False
        )
        
        # Create settings view
        view = AccessibilitySettingsView(user_id=user_id)
        
        # Send the embed with the view
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
    
    @app_commands.command(
        name="text_size",
        description="Quickly change your text size setting"
    )
    @app_commands.choices(size=[
        app_commands.Choice(name="Small", value="small"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Large", value="large"),
        app_commands.Choice(name="Extra Large", value="extra_large")
    ])
    async def set_text_size(
        self, 
        interaction: discord.Interaction, 
        size: app_commands.Choice[str]
    ):
        """Quickly change text size setting."""
        user_id = str(interaction.user.id)
        
        try:
            # Update the setting
            self.accessibility_manager.update_settings(
                user_id,
                {"text_size": size.value}
            )
            
            # Get user's theme
            theme = theme_manager.get_user_theme(user_id)
            
            # Create confirmation embed
            embed = theme.create_embed(
                title="Text Size Updated",
                description=f"Your text size has been set to **{size.name}**.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Add example of the text size
            if size.value == "small":
                example = "This is an example of small text."
            elif size.value == "medium":
                example = "This is an example of medium text."
            elif size.value == "large":
                example = "**This is an example of large text.**"
            else:  # extra_large
                example = "# This is an example of extra large text"
            
            embed.add_field(
                name="Example",
                value=example,
                inline=False
            )
            
            # Send confirmation
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting text size: {e}")
            await interaction.response.send_message(
                "There was an error updating your text size. Please try again or use the /accessibility command.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="color_mode",
        description="Quickly change your color mode setting"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Normal", value="normal"),
        app_commands.Choice(name="High Contrast", value="high_contrast"),
        app_commands.Choice(name="Deuteranopia (Green-blind friendly)", value="deuteranopia"),
        app_commands.Choice(name="Protanopia (Red-blind friendly)", value="protanopia"),
        app_commands.Choice(name="Tritanopia (Blue-blind friendly)", value="tritanopia"),
        app_commands.Choice(name="Monochrome", value="monochrome")
    ])
    async def set_color_mode(
        self, 
        interaction: discord.Interaction, 
        mode: app_commands.Choice[str]
    ):
        """Quickly change color mode setting."""
        user_id = str(interaction.user.id)
        
        try:
            # Update the setting
            self.accessibility_manager.update_settings(
                user_id,
                {"color_mode": mode.value}
            )
            
            # Get user's theme
            theme = theme_manager.get_user_theme(user_id)
            
            # Create confirmation embed
            embed = theme.create_embed(
                title="Color Mode Updated",
                description=f"Your color mode has been set to **{mode.name}**.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Add recommended theme if applicable
            recommended_theme = None
            if mode.value == "high_contrast":
                recommended_theme = "high_contrast"
            elif mode.value == "monochrome":
                recommended_theme = "retro"
            
            if recommended_theme:
                embed.add_field(
                    name="Recommended Theme",
                    value=f"For the best experience with this color mode, we recommend the '{recommended_theme}' theme. Use `/theme {recommended_theme}` to apply it.",
                    inline=False
                )
            
            # Send confirmation
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting color mode: {e}")
            await interaction.response.send_message(
                "There was an error updating your color mode. Please try again or use the /accessibility command.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="toggle_simplified_ui",
        description="Toggle simplified UI mode for better readability"
    )
    async def toggle_simplified_ui(self, interaction: discord.Interaction):
        """Toggle simplified UI mode."""
        user_id = str(interaction.user.id)
        
        try:
            # Get current settings
            settings = self.accessibility_manager.get_settings(user_id)
            
            # Toggle the setting
            new_value = not settings.simplified_ui
            
            # Update the setting
            self.accessibility_manager.update_settings(
                user_id,
                {"simplified_ui": new_value}
            )
            
            # Get user's theme
            theme = theme_manager.get_user_theme(user_id)
            
            # Create confirmation embed
            embed = theme.create_embed(
                title="Simplified UI Setting Updated",
                description=f"Simplified UI mode has been {'enabled' if new_value else 'disabled'}.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Add description
            if new_value:
                embed.add_field(
                    name="What Changed",
                    value="UI elements will now be simplified for better readability. Complex formatting will be removed, and extra spacing will be added between sections.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="What Changed",
                    value="UI elements will now use standard formatting and layout.",
                    inline=False
                )
            
            # Send confirmation
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error toggling simplified UI: {e}")
            await interaction.response.send_message(
                "There was an error updating your simplified UI setting. Please try again or use the /accessibility command.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="toggle_visual_updates",
        description="Toggle visual update frequency on or off"
    )
    @app_commands.choices(frequency=[
        app_commands.Choice(name="Standard Updates", value="standard"),
        app_commands.Choice(name="Reduced Updates", value="reduced"),
        app_commands.Choice(name="Minimal Updates", value="minimal")
    ])
    async def toggle_visual_updates(
        self, 
        interaction: discord.Interaction, 
        frequency: app_commands.Choice[str]
    ):
        """Set visual update frequency."""
        user_id = str(interaction.user.id)
        
        try:
            # Update the setting
            self.accessibility_manager.update_settings(
                user_id,
                {"update_frequency": frequency.value}
            )
            
            # Get user's theme
            theme = theme_manager.get_user_theme(user_id)
            
            # Create confirmation embed
            embed = theme.create_embed(
                title="Visual Update Frequency Updated",
                description=f"Visual update frequency has been set to **{frequency.name}**.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Add explanation
            if frequency.value == "standard":
                description = "Visual updates will be sent at the standard rate, providing a more dynamic experience."
            elif frequency.value == "reduced":
                description = "Visual updates will be sent at a reduced rate, providing a balance between performance and visual feedback."
            else:  # minimal
                description = "Visual updates will be sent at a minimal rate, prioritizing performance over visual feedback."
            
            embed.add_field(
                name="What Changed",
                value=description,
                inline=False
            )
            
            # Send confirmation
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting visual update frequency: {e}")
            await interaction.response.send_message(
                "There was an error updating your visual update frequency. Please try again or use the /accessibility command.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="toggle_extended_timeouts",
        description="Toggle extended interaction timeouts for more time to respond"
    )
    async def toggle_extended_timeouts(self, interaction: discord.Interaction):
        """Toggle extended interaction timeouts."""
        user_id = str(interaction.user.id)
        
        try:
            # Get current settings
            settings = self.accessibility_manager.get_settings(user_id)
            
            # Toggle the setting
            new_value = not settings.extended_interaction_timeouts
            
            # Update the setting
            self.accessibility_manager.update_settings(
                user_id,
                {"extended_interaction_timeouts": new_value}
            )
            
            # Get user's theme
            theme = theme_manager.get_user_theme(user_id)
            
            # Create confirmation embed
            embed = theme.create_embed(
                title="Extended Timeouts Setting Updated",
                description=f"Extended interaction timeouts have been {'enabled' if new_value else 'disabled'}.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Add description
            if new_value:
                embed.add_field(
                    name="What Changed",
                    value="You will now have more time to respond to interactions such as battles and trades. Buttons and menus will stay active longer before timing out.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="What Changed",
                    value="Interaction timeouts have been set to the default duration.",
                    inline=False
                )
            
            # Send confirmation
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error toggling extended timeouts: {e}")
            await interaction.response.send_message(
                "There was an error updating your extended timeouts setting. Please try again or use the /accessibility command.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="accessibility_reset",
        description="Reset all accessibility settings to default values"
    )
    async def reset_accessibility_settings(self, interaction: discord.Interaction):
        """Reset all accessibility settings to default values."""
        user_id = str(interaction.user.id)
        
        # Create confirmation button
        view = discord.ui.View(timeout=60)
        
        confirm_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Reset All Settings",
            row=0
        )
        
        cancel_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Cancel",
            row=0
        )
        
        async def confirm_callback(confirm_interaction):
            try:
                # Reset all settings
                self.accessibility_manager.reset_settings(user_id)
                
                # Get user's theme
                theme = theme_manager.get_user_theme(user_id)
                
                # Create confirmation embed
                embed = theme.create_embed(
                    title="Accessibility Settings Reset",
                    description="All accessibility settings have been reset to their default values.",
                    color_type=ThemeColorType.SUCCESS
                )
                
                # Send confirmation
                await confirm_interaction.response.edit_message(
                    content=None,
                    embed=embed,
                    view=None
                )
            except Exception as e:
                logger.error(f"Error resetting accessibility settings: {e}")
                await confirm_interaction.response.edit_message(
                    content="There was an error resetting your accessibility settings. Please try again.",
                    view=None
                )
        
        async def cancel_callback(cancel_interaction):
            # Get user's theme
            theme = theme_manager.get_user_theme(user_id)
            
            # Create cancellation embed
            embed = theme.create_embed(
                title="Reset Cancelled",
                description="Your accessibility settings have not been changed.",
                color_type=ThemeColorType.PRIMARY
            )
            
            # Send cancellation
            await cancel_interaction.response.edit_message(
                content=None,
                embed=embed,
                view=None
            )
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        # Get user's theme
        theme = theme_manager.get_user_theme(user_id)
        
        # Create confirmation embed
        embed = theme.create_embed(
            title="Reset Accessibility Settings",
            description="Are you sure you want to reset all accessibility settings to their default values? This cannot be undone.",
            color_type=ThemeColorType.WARNING
        )
        
        # Send confirmation
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(AccessibilityCog(bot))
