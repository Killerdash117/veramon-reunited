"""
Settings Editor Cog for Veramon Reunited

This cog provides commands for editing the bot configuration through Discord commands.
It allows server admins to modify game settings without needing developer access.
"""

import discord
import logging
import json
from typing import Dict, Any, Optional, List, Union
from discord import app_commands
from discord.ext import commands

from src.utils.config_manager import (
    get_config, update_config, update_config_batch, 
    backup_config, get_all_configurable_settings
)
from src.models.permissions import PermissionLevel, require_permission_level

logger = logging.getLogger(__name__)

class SettingsEditorCog(commands.Cog):
    """Settings editor commands for modifying bot configuration."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="config_view", description="View current configuration settings")
    @app_commands.describe(section="Configuration section to view")
    @require_permission_level(PermissionLevel.ADMIN)
    async def config_view(self, interaction: discord.Interaction, section: Optional[str] = None):
        """View the current configuration settings."""
        if section:
            section_config = get_config(section)
            if not section_config:
                await interaction.response.send_message(f"Section '{section}' not found in configuration.", ephemeral=True)
                return
                
            # Format the section config as a readable string
            config_str = f"## {section.capitalize()} Configuration\n\n"
            for key, value in section_config.items():
                config_str += f"**{key}**: `{value}`\n"
                
            embed = discord.Embed(
                title=f"{section.capitalize()} Configuration",
                description=config_str,
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show a list of available sections
            config = get_config()
            sections = list(config.keys())
            
            embed = discord.Embed(
                title="Available Configuration Sections",
                description="Use `/config_view [section]` to view a specific section.",
                color=discord.Color.blue()
            )
            
            for section in sections:
                setting_count = len(config[section])
                embed.add_field(
                    name=section.capitalize(),
                    value=f"{setting_count} settings",
                    inline=True
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="config_edit", description="Edit a configuration setting")
    @app_commands.describe(
        section="Configuration section",
        key="Configuration key",
        value="New value (use 'true'/'false' for booleans, numbers for numeric values)"
    )
    @require_permission_level(PermissionLevel.ADMIN)
    async def config_edit(self, interaction: discord.Interaction, section: str, key: str, value: str):
        """Edit a configuration setting."""
        # Get the current value for comparison
        current_value = get_config(section, key)
        
        if current_value is None:
            await interaction.response.send_message(
                f"Setting '{key}' not found in section '{section}'.", 
                ephemeral=True
            )
            return
            
        # Convert the string value to the appropriate type
        try:
            # Check value type
            if isinstance(current_value, bool):
                value = value.lower() in ("true", "yes", "1", "t", "y")
            elif isinstance(current_value, int):
                value = int(value)
            elif isinstance(current_value, float):
                value = float(value)
            # Keep strings as is
                
            # Create a backup before making changes
            backup_path = backup_config()
            
            # Update the config
            success = update_config(section, key, value)
            
            if success:
                embed = discord.Embed(
                    title="Configuration Updated",
                    description=f"Successfully updated {section}.{key}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Old Value", value=f"`{current_value}`", inline=True)
                embed.add_field(name="New Value", value=f"`{value}`", inline=True)
                
                if backup_path:
                    embed.set_footer(text=f"Backup created before change")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Failed to update configuration.", 
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message(
                f"Invalid value format. Expected a {type(current_value).__name__}.", 
                ephemeral=True
            )
    
    @app_commands.command(name="config_reset", description="Reset a configuration section to defaults")
    @app_commands.describe(section="Configuration section to reset")
    @require_permission_level(PermissionLevel.ADMIN)
    async def config_reset(self, interaction: discord.Interaction, section: str):
        """Reset a configuration section to its default values."""
        # Check if section exists
        if get_config(section) is None:
            await interaction.response.send_message(
                f"Section '{section}' not found in configuration.", 
                ephemeral=True
            )
            return
            
        # Get default configuration
        default_config = {
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
            # Add more default sections as needed
        }
        
        if section not in default_config:
            await interaction.response.send_message(
                f"No default configuration available for section '{section}'.", 
                ephemeral=True
            )
            return
            
        # Create a backup before making changes
        backup_path = backup_config()
        
        # Update each key in the section
        updates = []
        for key, value in default_config[section].items():
            updates.append((section, key, value))
            
        success = update_config_batch(updates)
        
        if success:
            embed = discord.Embed(
                title="Configuration Reset",
                description=f"Successfully reset {section} to default values.",
                color=discord.Color.green()
            )
            
            # Show the reset values
            reset_values = ""
            for key, value in default_config[section].items():
                reset_values += f"**{key}**: `{value}`\n"
                
            embed.add_field(name="Reset Values", value=reset_values)
            
            if backup_path:
                embed.set_footer(text=f"Backup created before reset")
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Failed to reset configuration.", 
                ephemeral=True
            )
    
    @app_commands.command(name="config_export", description="Export the current configuration to a JSON file")
    @require_permission_level(PermissionLevel.ADMIN)
    async def config_export(self, interaction: discord.Interaction):
        """Export the current configuration to a JSON file."""
        config = get_config()
        
        # Convert to JSON string with pretty formatting
        config_json = json.dumps(config, indent=2)
        
        # Create a Discord file attachment
        file = discord.File(
            fp=discord.utils.to_file(config_json.encode('utf-8')),
            filename="veramon_config.json"
        )
        
        embed = discord.Embed(
            title="Configuration Export",
            description="Here is your current configuration file.",
            color=discord.Color.blue()
        )
        
        # Send the file as an attachment
        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
    
    @app_commands.command(name="config_import", description="Import configuration from a JSON file")
    @require_permission_level(PermissionLevel.ADMIN)
    async def config_import(self, interaction: discord.Interaction):
        """
        Import configuration from a JSON file.
        
        This uses a modal to accept the JSON content since we can't directly
        accept file uploads through slash commands.
        """
        # Respond with a modal to paste JSON content
        modal = ConfigImportModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="config_list_settings", description="List all available settings with descriptions")
    @app_commands.describe(section="Configuration section to list settings for")
    @require_permission_level(PermissionLevel.ADMIN)
    async def config_list_settings(self, interaction: discord.Interaction, section: Optional[str] = None):
        """List all available settings with their descriptions."""
        all_settings = get_all_configurable_settings()
        
        if section:
            if section not in all_settings:
                await interaction.response.send_message(
                    f"Section '{section}' not found.", 
                    ephemeral=True
                )
                return
                
            # Show settings for the specific section
            section_data = all_settings[section]
            section_desc = section_data.get("description", "No description available")
            
            embed = discord.Embed(
                title=f"{section.capitalize()} Settings",
                description=section_desc,
                color=discord.Color.blue()
            )
            
            for key, setting in section_data.get("settings", {}).items():
                setting_type = setting.get("type", "unknown")
                description = setting.get("description", "No description available")
                editable = "Yes" if setting.get("editable", True) else "No"
                
                value = f"**Type:** {setting_type}\n"
                value += f"**Description:** {description}\n"
                value += f"**Editable:** {editable}\n"
                
                if "min" in setting and "max" in setting:
                    value += f"**Range:** {setting['min']} to {setting['max']}\n"
                
                embed.add_field(name=key, value=value, inline=False)
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show a list of available sections
            embed = discord.Embed(
                title="Available Configuration Sections",
                description="Use `/config_list_settings [section]` to view settings in a specific section.",
                color=discord.Color.blue()
            )
            
            for section_name, section_data in all_settings.items():
                section_desc = section_data.get("description", "No description available")
                setting_count = len(section_data.get("settings", {}))
                
                embed.add_field(
                    name=section_name.capitalize(),
                    value=f"{section_desc}\n{setting_count} settings",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfigImportModal(discord.ui.Modal, title="Import Configuration"):
    """Modal for importing configuration JSON."""
    
    config_json = discord.ui.TextInput(
        label="Configuration JSON",
        placeholder="Paste JSON content here...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Try to parse the JSON
        try:
            config = json.loads(self.config_json.value)
            
            # Validate the config structure
            if not isinstance(config, dict):
                await interaction.response.send_message(
                    "Invalid configuration format. Expected a JSON object.",
                    ephemeral=True
                )
                return
                
            # Create a backup before making changes
            backup_path = backup_config()
            
            # Prepare batch updates
            updates = []
            for section, section_data in config.items():
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        updates.append((section, key, value))
            
            # Apply updates
            success = update_config_batch(updates)
            
            if success:
                embed = discord.Embed(
                    title="Configuration Imported",
                    description=f"Successfully imported {len(updates)} settings.",
                    color=discord.Color.green()
                )
                
                if backup_path:
                    embed.set_footer(text=f"Backup created before import")
                    
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "Failed to import configuration.",
                    ephemeral=True
                )
        except json.JSONDecodeError:
            await interaction.response.send_message(
                "Invalid JSON format. Please check your input.",
                ephemeral=True
            )

async def setup(bot):
    """Add the SettingsEditorCog to the bot."""
    await bot.add_cog(SettingsEditorCog(bot))
