"""
Setup Cog for Veramon Reunited

This module provides an interactive setup command for configuring the bot
with a step-by-step UI interface. Both admins and developers can use this
to easily configure all aspects of the bot's functionality.
"""

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
import json
import os

from src.core.security_integration import get_security_integration
from src.core.config_manager import get_config, save_config, get_config_value
from src.utils.setup_manager import SetupManager, setup_get_category_status
from src.ui.setup_views import (
    MainSetupView, 
    GeneralSettingsView,
    GameFeaturesView, 
    EconomySettingsView,
    SpawnSettingsView, 
    ChannelSetupView,
    RoleConfigView, 
    SecuritySettingsView
)

# Set up logging
logger = logging.getLogger("setup")

class SetupCog(commands.Cog):
    """
    Admin command for configuring the bot through an interactive UI.
    
    This cog provides the /setup command that presents a step-by-step
    configuration interface allowing administrators to easily set up all
    aspects of the bot.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.security = get_security_integration()
        self.setup_manager = SetupManager()
        
    @app_commands.command(name="setup", description="Configure the bot with an interactive setup wizard")
    @app_commands.default_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        """
        Run the interactive setup wizard to configure the bot.
        
        This command presents a user-friendly interface to configure all aspects
        of the bot, including general settings, game features, economy, channels,
        roles, and security settings.
        """
        # Validate admin or dev permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "setup", "admin"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Initialize setup session
        setup_data = self.setup_manager.initialize_setup(str(interaction.user.id), interaction.guild_id)
        
        # Check if setup has been run before
        config = get_config()
        setup_completed = config.get("setup_completed", False)
        
        # Create initial message
        if setup_completed:
            title = "Veramon Reunited Setup"
            description = (
                "Welcome to the setup wizard! This interface allows you to configure all aspects "
                "of the Veramon Reunited bot.\n\n"
                "You've already completed the initial setup, but you can modify any settings "
                "as needed. Choose a category below to get started."
            )
        else:
            title = "Welcome to Veramon Reunited!"
            description = (
                "Thank you for choosing Veramon Reunited! This setup wizard will guide you "
                "through configuring the bot for your server.\n\n"
                "We'll walk through several categories of settings. You can complete them "
                "in any order, and return to this wizard at any time using the `/setup` command."
            )
        
        # Get category completion status
        category_status = setup_get_category_status(config)
        
        # Create the main embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        
        # Add setup progress if applicable
        if setup_completed:
            embed.add_field(
                name="Current Configuration Status",
                value=self._format_category_status(category_status),
                inline=False
            )
        
        # Add bot info
        embed.add_field(
            name="Bot Information",
            value=(
                f"**Version**: {self.bot.VERSION}\n"
                f"**Server**: {interaction.guild.name}\n"
                f"**Setup By**: {interaction.user.mention}"
            ),
            inline=False
        )
        
        # Add footer
        embed.set_footer(text=f"Setup initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create the main setup view with buttons for each category
        view = MainSetupView(self.bot, self.setup_manager, interaction.user.id, category_status)
        
        # Send the initial setup message
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    def _format_category_status(self, status: Dict[str, bool]) -> str:
        """Format the category status dictionary into a readable string."""
        result = ""
        for category, completed in status.items():
            emoji = "✅" if completed else "⏳"
            # Convert snake_case to Title Case
            formatted_name = " ".join(word.capitalize() for word in category.split("_"))
            result += f"{emoji} **{formatted_name}**: {'Configured' if completed else 'Not Configured'}\n"
        return result

    @app_commands.command(name="setup_reset", description="Reset all bot configuration to defaults")
    @app_commands.default_permissions(administrator=True)
    async def setup_reset(self, interaction: discord.Interaction):
        """Reset all bot configuration settings to their default values."""
        # Validate dev permissions (dev only for complete reset)
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "setup_reset", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Confirm reset
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Configuration Reset",
            description=(
                "You are about to reset **ALL** bot configuration settings to their default values.\n\n"
                "This will affect:\n"
                "- General settings\n"
                "- Game features\n"
                "- Economy settings\n"
                "- Spawn settings\n"
                "- Channel configurations\n"
                "- Role assignments\n"
                "- Security settings\n\n"
                "**This action cannot be undone!** Are you sure you want to proceed?"
            ),
            color=discord.Color.red()
        )
        
        # Create confirmation buttons
        class ConfirmButtons(discord.ui.View):
            def __init__(self, timeout=60):
                super().__init__(timeout=timeout)
                self.value = None
            
            @discord.ui.button(label="Reset All Settings", style=discord.ButtonStyle.danger)
            async def confirm(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                await b_interaction.response.defer()
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, b_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                await b_interaction.response.defer()
                self.stop()
        
        view = ConfirmButtons()
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
        
        # Wait for confirmation
        await view.wait()
        
        if view.value is None:
            await interaction.followup.send("❌ Reset cancelled: Timed out", ephemeral=True)
            return
        elif view.value is False:
            await interaction.followup.send("✅ Reset cancelled", ephemeral=True)
            return
        
        # Perform the reset by loading default configuration
        try:
            # Create a backup of current config
            config = get_config()
            backup_path = "data/config_backup_before_reset.json"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            with open(backup_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Load the default configuration
            default_config_path = "src/defaults/default_config.json"
            
            if os.path.exists(default_config_path):
                with open(default_config_path, 'r') as f:
                    default_config = json.load(f)
            else:
                # Fallback to hardcoded minimal defaults
                default_config = {
                    "prefix": "!",
                    "setup_completed": False,
                    "general_settings": {"configured": False},
                    "game_features": {"configured": False},
                    "economy_settings": {"configured": False},
                    "spawn_settings": {"configured": False},
                    "channel_setup": {"configured": False},
                    "role_config": {"configured": False},
                    "security_settings": {"configured": False}
                }
            
            # Save the default configuration
            save_config(default_config)
            
            # Log the reset
            logger.warning(
                f"Configuration reset to defaults by {interaction.user.name} (ID: {interaction.user.id})"
            )
            
            # Notify user
            await interaction.followup.send(
                "✅ All configuration settings have been reset to defaults. "
                f"A backup of your previous configuration was saved to {backup_path}. "
                "Run `/setup` to configure the bot again.",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error during configuration reset: {e}")
            await interaction.followup.send(
                f"❌ An error occurred while resetting configuration: {e}",
                ephemeral=True
            )

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(SetupCog(bot))
