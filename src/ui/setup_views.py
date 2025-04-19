"""
Setup UI Views for Veramon Reunited

This module provides Discord UI components for the interactive setup wizard,
including views, buttons, dropdowns, and modals for configuring the bot.
"""

import discord
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Dict, List, Optional, Any, Union, Callable
import asyncio
import logging

from src.core.config_manager import get_config, save_config

# Set up logging
logger = logging.getLogger("setup")

class MainSetupView(discord.ui.View):
    """
    Main setup view with buttons for each configuration category.
    """
    
    def __init__(self, bot, setup_manager, user_id: int, category_status: Dict[str, bool]):
        super().__init__(timeout=900)  # 15 minute timeout
        self.bot = bot
        self.setup_manager = setup_manager
        self.user_id = user_id
        self.category_status = category_status
        
        # Add individual category buttons
        self._add_category_buttons()
        
    def _add_category_buttons(self):
        """Add buttons for each configuration category."""
        # General Settings
        self.add_item(SetupCategoryButton(
            "General Settings", 
            discord.ButtonStyle.primary, 
            "🛠️",
            self.category_status.get("general_settings", False),
            GeneralSettingsView
        ))
        
        # Game Features
        self.add_item(SetupCategoryButton(
            "Game Features", 
            discord.ButtonStyle.primary, 
            "🎮",
            self.category_status.get("game_features", False),
            GameFeaturesView
        ))
        
        # Economy Settings
        self.add_item(SetupCategoryButton(
            "Economy Settings", 
            discord.ButtonStyle.primary, 
            "💰",
            self.category_status.get("economy_settings", False),
            EconomySettingsView
        ))
        
        # Spawn Settings
        self.add_item(SetupCategoryButton(
            "Spawn Settings", 
            discord.ButtonStyle.primary, 
            "🦄",
            self.category_status.get("spawn_settings", False),
            SpawnSettingsView
        ))
        
        # Channel Setup
        self.add_item(SetupCategoryButton(
            "Channel Setup", 
            discord.ButtonStyle.primary, 
            "📝",
            self.category_status.get("channel_setup", False),
            ChannelSetupView
        ))
        
        # Role Configuration
        self.add_item(SetupCategoryButton(
            "Role Config", 
            discord.ButtonStyle.primary, 
            "👑",
            self.category_status.get("role_config", False),
            RoleConfigView
        ))
        
        # Security Settings
        self.add_item(SetupCategoryButton(
            "Security Settings", 
            discord.ButtonStyle.primary, 
            "🔒",
            self.category_status.get("security_settings", False),
            SecuritySettingsView
        ))
        
        # Save All Changes
        save_button = discord.ui.Button(
            label="Save All Changes",
            style=discord.ButtonStyle.success,
            emoji="💾",
            row=4
        )
        save_button.callback = self.save_all_changes
        self.add_item(save_button)
        
        # Discard Changes
        discard_button = discord.ui.Button(
            label="Discard Changes",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=4
        )
        discard_button.callback = self.discard_changes
        self.add_item(discard_button)
    
    async def save_all_changes(self, interaction: discord.Interaction):
        """Save all configuration changes."""
        # Ensure the interaction user is the setup initiator
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the user who initiated setup can save changes.",
                ephemeral=True
            )
            return
        
        # Save changes
        success = self.setup_manager.save_config_changes(str(self.user_id))
        
        if success:
            await interaction.response.send_message(
                "✅ All configuration changes have been saved successfully!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to save configuration changes. Please try again.",
                ephemeral=True
            )
    
    async def discard_changes(self, interaction: discord.Interaction):
        """Discard all unsaved configuration changes."""
        # Ensure the interaction user is the setup initiator
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the user who initiated setup can discard changes.",
                ephemeral=True
            )
            return
        
        # Ask for confirmation
        confirm_view = ConfirmView("Are you sure you want to discard all unsaved changes?")
        await interaction.response.send_message(
            "⚠️ This will discard all unsaved configuration changes. Are you sure?",
            view=confirm_view,
            ephemeral=True
        )
        
        # Wait for confirmation
        await confirm_view.wait()
        
        if confirm_view.value is True:
            # Discard changes
            self.setup_manager.discard_changes(str(self.user_id))
            await interaction.followup.send(
                "✅ All unsaved changes have been discarded.",
                ephemeral=True
            )
        elif confirm_view.value is False:
            await interaction.followup.send(
                "✅ Operation cancelled. Your changes are still pending.",
                ephemeral=True
            )
        else:  # None - timed out
            await interaction.followup.send(
                "❌ Confirmation timed out. Your changes are still pending.",
                ephemeral=True
            )
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the setup initiator can interact with the view."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the user who initiated setup can interact with these controls.",
                ephemeral=True
            )
            return False
        return True


class SetupCategoryButton(discord.ui.Button):
    """Button for a setup category that opens the corresponding view."""
    
    def __init__(self, label: str, style: discord.ButtonStyle, emoji: str, 
                 configured: bool, view_class: Any, row: int = None):
        """
        Initialize a category button.
        
        Args:
            label: Button label text
            style: Button style
            emoji: Button emoji
            configured: Whether this category is already configured
            view_class: View class to instantiate when clicked
            row: Button row (optional)
        """
        # Add checkmark to label if configured
        display_label = f"{label} ✓" if configured else label
        
        super().__init__(
            label=display_label,
            style=style,
            emoji=emoji,
            row=row
        )
        self.original_label = label
        self.view_class = view_class
        self.configured = configured
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click to open category view."""
        # Get the setup manager from the parent view
        setup_manager = self.view.setup_manager
        
        # Create and send the category-specific view
        category_view = self.view_class(self.view.bot, setup_manager, interaction.user.id)
        
        # Create embed for this category
        embed = discord.Embed(
            title=f"{self.original_label} Setup",
            description=f"Configure {self.original_label.lower()} for Veramon Reunited.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=category_view,
            ephemeral=True
        )


class BaseSetupView(discord.ui.View):
    """Base class for all setup category views."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(timeout=600)  # 10 minute timeout
        self.bot = bot
        self.setup_manager = setup_manager
        self.user_id = user_id
        self.category = "base"  # Override in subclasses
        
        # Add back button
        back_button = discord.ui.Button(
            label="Back to Main Menu",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=4
        )
        back_button.callback = self.return_to_main
        self.add_item(back_button)
        
        # Add save button
        save_button = discord.ui.Button(
            label="Save Changes",
            style=discord.ButtonStyle.success,
            emoji="💾",
            row=4
        )
        save_button.callback = self.save_changes
        self.add_item(save_button)
    
    async def return_to_main(self, interaction: discord.Interaction):
        """Return to the main setup menu."""
        # Load current config to get category status
        config = get_config()
        category_status = {
            "general_settings": config.get("general_settings", {}).get("configured", False),
            "game_features": config.get("game_features", {}).get("configured", False),
            "economy_settings": config.get("economy_settings", {}).get("configured", False),
            "spawn_settings": config.get("spawn_settings", {}).get("configured", False),
            "channel_setup": config.get("channel_setup", {}).get("configured", False),
            "role_config": config.get("role_config", {}).get("configured", False),
            "security_settings": config.get("security_settings", {}).get("configured", False)
        }
        
        # Create new main view
        main_view = MainSetupView(self.bot, self.setup_manager, self.user_id, category_status)
        
        # Create main embed
        embed = discord.Embed(
            title="Veramon Reunited Setup",
            description=(
                "Welcome back to the main setup menu. Choose a category to configure, "
                "or save/discard your changes using the buttons below."
            ),
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(
            embed=embed,
            view=main_view
        )
    
    async def save_changes(self, interaction: discord.Interaction):
        """Save changes for this specific category."""
        # This should be implemented by subclasses to gather and save settings
        await interaction.response.send_message(
            "❌ Save not implemented for this category.",
            ephemeral=True
        )
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the setup initiator can interact with the view."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the user who initiated setup can interact with these controls.",
                ephemeral=True
            )
            return False
        return True


class ConfirmView(discord.ui.View):
    """Simple confirmation view with Yes/No buttons."""
    
    def __init__(self, confirm_message: str = "Are you sure?"):
        super().__init__(timeout=60)
        self.value = None
        self.confirm_message = confirm_message
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm the action."""
        self.value = True
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the action."""
        self.value = False
        await interaction.response.defer()
        self.stop()


class GeneralSettingsView(BaseSetupView):
    """View for configuring general bot settings."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(bot, setup_manager, user_id)
        self.category = "general"
        
        # Load current settings
        setup_data = setup_manager.get_setup_data(str(user_id))
        if not setup_data:
            # Fallback to current config if no setup session
            self.current_settings = get_config()
        else:
            self.current_settings = setup_data["temp_config"]
        
        # Add setting controls
        self._add_setting_controls()
    
    def _add_setting_controls(self):
        # Bot Prefix
        prefix_button = discord.ui.Button(
            label=f"Bot Prefix: {self.current_settings.get('prefix', '!')}",
            style=discord.ButtonStyle.secondary,
            row=0
        )
        prefix_button.callback = self.change_prefix
        self.add_item(prefix_button)
        
        # Bot Status
        status_options = [
            discord.SelectOption(
                label="Online",
                value="online",
                emoji="🟢",
                default=self.current_settings.get("bot_status") == "online"
            ),
            discord.SelectOption(
                label="Idle",
                value="idle",
                emoji="🟡",
                default=self.current_settings.get("bot_status") == "idle"
            ),
            discord.SelectOption(
                label="Do Not Disturb",
                value="dnd",
                emoji="🔴",
                default=self.current_settings.get("bot_status") == "dnd"
            )
        ]
        
        status_select = discord.ui.Select(
            placeholder="Bot Status",
            options=status_options,
            row=1
        )
        status_select.callback = self.update_status
        self.add_item(status_select)
        
        # Status Message
        status_msg_button = discord.ui.Button(
            label="Set Status Message",
            style=discord.ButtonStyle.secondary,
            row=2
        )
        status_msg_button.callback = self.change_status_message
        self.add_item(status_msg_button)
        
        # Timezone
        timezone_button = discord.ui.Button(
            label=f"Timezone: {self.current_settings.get('timezone', 'UTC')}",
            style=discord.ButtonStyle.secondary,
            row=3
        )
        timezone_button.callback = self.change_timezone
        self.add_item(timezone_button)
    
    async def change_prefix(self, interaction: discord.Interaction):
        """Open modal to change bot prefix."""
        modal = discord.ui.Modal(title="Change Bot Prefix")
        
        prefix_input = discord.ui.TextInput(
            label="New Prefix",
            placeholder="Enter new prefix (e.g., !, /, $)",
            default=self.current_settings.get("prefix", "!"),
            min_length=1,
            max_length=5,
            required=True
        )
        modal.add_item(prefix_input)
        
        async def on_submit(interaction: discord.Interaction):
            new_prefix = prefix_input.value
            
            # Update button text
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label.startswith("Bot Prefix:"):
                    child.label = f"Bot Prefix: {new_prefix}"
                    break
            
            # Update temp settings
            setup_data = self.setup_manager.get_setup_data(str(self.user_id))
            if setup_data:
                setup_data["temp_config"]["prefix"] = new_prefix
            
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("✅ Prefix updated!", ephemeral=True)
        
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    
    async def update_status(self, interaction: discord.Interaction):
        """Update bot status setting."""
        selected_status = interaction.data["values"][0]
        
        # Update temp settings
        setup_data = self.setup_manager.get_setup_data(str(self.user_id))
        if setup_data:
            setup_data["temp_config"]["bot_status"] = selected_status
        
        await interaction.response.defer()
        await interaction.followup.send(f"✅ Bot status set to: {selected_status}", ephemeral=True)
    
    async def change_status_message(self, interaction: discord.Interaction):
        """Open modal to change bot status message."""
        modal = discord.ui.Modal(title="Change Status Message")
        
        message_input = discord.ui.TextInput(
            label="Status Message",
            placeholder="Enter status message",
            default=self.current_settings.get("bot_status_message", "Veramon Reunited | Use /help"),
            min_length=1,
            max_length=100,
            required=True
        )
        modal.add_item(message_input)
        
        async def on_submit(interaction: discord.Interaction):
            new_message = message_input.value
            
            # Update temp settings
            setup_data = self.setup_manager.get_setup_data(str(self.user_id))
            if setup_data:
                setup_data["temp_config"]["bot_status_message"] = new_message
            
            await interaction.response.defer()
            await interaction.followup.send(f"✅ Status message updated to: {new_message}", ephemeral=True)
        
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    
    async def change_timezone(self, interaction: discord.Interaction):
        """Open selection for timezone."""
        # Common timezones
        timezones = [
            "UTC", "US/Eastern", "US/Central", "US/Pacific", "US/Mountain",
            "Europe/London", "Europe/Berlin", "Europe/Paris", "Europe/Moscow",
            "Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore", "Australia/Sydney"
        ]
        
        # Create options for dropdown
        options = []
        current_tz = self.current_settings.get("timezone", "UTC")
        
        for tz in timezones:
            options.append(discord.SelectOption(
                label=tz,
                value=tz,
                default=(tz == current_tz)
            ))
        
        # Create the select menu
        select = discord.ui.Select(
            placeholder="Select Timezone",
            options=options
        )
        
        # Create a temporary view just for the timezone selection
        temp_view = discord.ui.View()
        temp_view.add_item(select)
        
        async def select_callback(interaction: discord.Interaction):
            selected_timezone = interaction.data["values"][0]
            
            # Update the timezone button
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label.startswith("Timezone:"):
                    child.label = f"Timezone: {selected_timezone}"
                    break
            
            # Update temp settings
            setup_data = self.setup_manager.get_setup_data(str(self.user_id))
            if setup_data:
                setup_data["temp_config"]["timezone"] = selected_timezone
            
            # Re-display the main settings view
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"✅ Timezone set to: {selected_timezone}", ephemeral=True)
        
        select.callback = select_callback
        
        await interaction.response.send_message(
            "Select a timezone:",
            view=temp_view,
            ephemeral=True
        )
    
    async def save_changes(self, interaction: discord.Interaction):
        """Save general settings changes."""
        setup_data = self.setup_manager.get_setup_data(str(self.user_id))
        if not setup_data:
            await interaction.response.send_message(
                "❌ No active setup session found.",
                ephemeral=True
            )
            return
        
        # Extract general settings
        general_settings = {
            "prefix": setup_data["temp_config"].get("prefix", "!"),
            "bot_status": setup_data["temp_config"].get("bot_status", "online"),
            "bot_status_message": setup_data["temp_config"].get("bot_status_message", "Veramon Reunited | Use /help"),
            "timezone": setup_data["temp_config"].get("timezone", "UTC"),
            "language": setup_data["temp_config"].get("language", "en")
        }
        
        # Update temp config
        success = self.setup_manager.update_temp_config(str(self.user_id), "general", general_settings)
        
        if success:
            await interaction.response.send_message(
                "✅ General settings saved successfully!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to save general settings.",
                ephemeral=True
            )


# Placeholder classes for other setup categories
# These would be fully implemented similar to GeneralSettingsView
class GameFeaturesView(BaseSetupView):
    """View for enabling/disabling game features."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(bot, setup_manager, user_id)
        self.category = "features"
        # Placeholder - would implement toggles for various game features


class EconomySettingsView(BaseSetupView):
    """View for configuring economy settings."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(bot, setup_manager, user_id)
        self.category = "economy"
        # Placeholder - would implement controls for token amounts, rewards, etc.


class SpawnSettingsView(BaseSetupView):
    """View for configuring Veramon spawn settings."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(bot, setup_manager, user_id)
        self.category = "spawns"
        # Placeholder - would implement controls for spawn rates, rarities, etc.


class ChannelSetupView(BaseSetupView):
    """View for configuring channel settings."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(bot, setup_manager, user_id)
        self.category = "channels"
        # Placeholder - would implement channel selection for various functions


class RoleConfigView(BaseSetupView):
    """View for configuring role settings."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(bot, setup_manager, user_id)
        self.category = "roles"
        # Placeholder - would implement role selection for permissions


class SecuritySettingsView(BaseSetupView):
    """View for configuring security settings."""
    
    def __init__(self, bot, setup_manager, user_id: int):
        super().__init__(bot, setup_manager, user_id)
        self.category = "security"
        # Placeholder - would implement security options, rate limits, etc.
