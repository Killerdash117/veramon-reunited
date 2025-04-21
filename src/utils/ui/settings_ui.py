"""
Settings UI Components for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides UI components for user settings, including theme selection.
"""

import discord
from discord import ui
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union

from src.utils.ui.interactive_ui import InteractiveView, EnhancedSelectionView, NavigableView, NavigationType
from src.utils.ui_theme import theme_manager, ThemeColorType, Theme

# Set up logging
logger = logging.getLogger('veramon.settings_ui')

class UserSettingsView(NavigableView):
    """
    User settings interface with tabbed navigation.
    
    Features:
    - Theme selection
    - Notification preferences
    - Game settings
    - UI customization
    """
    
    def __init__(
        self,
        user_id: str,
        **kwargs
    ):
        super().__init__(
            user_id=user_id,
            navigation_type=NavigationType.TABS,
            **kwargs
        )
        
        # Set up tabs
        self.setup_tabs([
            "Themes",
            "Notifications",
            "Game Settings",
            "UI Options"
        ])
        
        # Theme settings
        self.theme = theme_manager.get_user_theme(user_id)
        
        # Tab content
        self._setup_theme_tab()
    
    def _setup_theme_tab(self):
        """Set up the theme selection tab."""
        # Create theme selection dropdown
        theme_select = ui.Select(
            placeholder="Select a theme",
            min_values=1,
            max_values=1,
            row=1
        )
        
        # Add theme options
        available_themes = theme_manager.themes.values()
        user_theme_id = theme_manager.user_themes.get(self.user_id, "default")
        
        for theme in available_themes:
            theme_select.add_option(
                label=theme.name,
                value=theme.id,
                description=theme.description,
                default=theme.id == user_theme_id
            )
        
        # Add callback
        theme_select.callback = self._on_theme_selected
        
        # Add to view
        self.add_item(theme_select)
        
        # Add theme preview button
        preview_button = ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Preview Theme",
            row=2
        )
        preview_button.callback = self._on_preview_theme
        self.add_item(preview_button)
    
    async def _on_theme_selected(self, interaction: discord.Interaction):
        """Handle theme selection."""
        # Get selected theme
        select = interaction.data["components"][0]["components"][0]
        theme_id = select["values"][0]
        
        # Save user preference
        success = theme_manager.set_user_theme(self.user_id, theme_id)
        
        if success:
            # Update the view with new theme
            self.theme = theme_manager.get_theme(theme_id)
            
            # Update embed
            embed = self._create_settings_embed()
            
            # Send confirmation
            await interaction.response.edit_message(
                embed=embed,
                view=self
            )
        else:
            # Something went wrong
            await interaction.response.send_message(
                "Failed to update theme preference. Please try again.",
                ephemeral=True
            )
    
    async def _on_preview_theme(self, interaction: discord.Interaction):
        """Show a preview of the selected theme."""
        # Get current theme
        theme = self.theme
        
        # Create preview embeds
        embeds = self._create_theme_preview_embeds(theme)
        
        # Send preview
        await interaction.response.send_message(
            content="Theme Preview (this message will delete in 30 seconds)",
            embeds=embeds,
            ephemeral=True,
            delete_after=30
        )
    
    def _create_settings_embed(self) -> discord.Embed:
        """Create the settings embed."""
        # Get current tab
        current_tab = self.get_current_tab()
        
        if current_tab == "Themes":
            # Create themes tab embed
            embed = self.theme.create_embed(
                title="User Settings - Themes",
                description="Customize the appearance of your Veramon bot interface.",
                color_type=ThemeColorType.PRIMARY
            )
            
            # Add current theme info
            embed.add_field(
                name="Current Theme",
                value=f"{self.theme.name}\n{self.theme.description}",
                inline=False
            )
            
            # Add instructions
            embed.add_field(
                name="Instructions",
                value="Select a theme from the dropdown menu to change your interface appearance.",
                inline=False
            )
            
            return embed
        
        elif current_tab == "Notifications":
            # Create notifications tab embed
            embed = self.theme.create_embed(
                title="User Settings - Notifications",
                description="Manage notifications from the Veramon bot.",
                color_type=ThemeColorType.INFO
            )
            
            # Add notification settings
            embed.add_field(
                name="Coming Soon",
                value="Notification settings will be available in a future update.",
                inline=False
            )
            
            return embed
        
        elif current_tab == "Game Settings":
            # Create game settings tab embed
            embed = self.theme.create_embed(
                title="User Settings - Game Settings",
                description="Customize your gameplay experience.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Add game settings
            embed.add_field(
                name="Coming Soon",
                value="Game settings will be available in a future update.",
                inline=False
            )
            
            return embed
        
        elif current_tab == "UI Options":
            # Create UI options tab embed
            embed = self.theme.create_embed(
                title="User Settings - UI Options",
                description="Customize how the bot UI appears to you.",
                color_type=ThemeColorType.ACCENT
            )
            
            # Add UI options
            embed.add_field(
                name="Coming Soon",
                value="UI customization options will be available in a future update.",
                inline=False
            )
            
            return embed
        
        # Default embed
        return self.theme.create_embed(
            title="User Settings",
            description="Customize your Veramon experience.",
            color_type=ThemeColorType.PRIMARY
        )
    
    def _create_theme_preview_embeds(self, theme: Theme) -> List[discord.Embed]:
        """Create preview embeds for the theme."""
        embeds = []
        
        # Main preview
        main_embed = theme.create_embed(
            title="Theme Preview - Main",
            description="This is what regular messages will look like.",
            color_type=ThemeColorType.PRIMARY
        )
        
        main_embed.add_field(
            name="Regular Field",
            value="This is a standard embed field",
            inline=True
        )
        
        main_embed.add_field(
            name="Another Field",
            value="This is another standard embed field",
            inline=True
        )
        
        main_embed.set_footer(text="This is a footer")
        embeds.append(main_embed)
        
        # Battle preview
        battle_embed = theme.create_embed(
            title="Theme Preview - Battle",
            description="This is what battle screens will look like.",
            color_type=ThemeColorType.DANGER
        )
        
        battle_embed.add_field(
            name="Your Veramon (Lv.25)",
            value=f"HP: 80/100\n{'█' * 8}{'░' * 2} 80%",
            inline=True
        )
        
        battle_embed.add_field(
            name="Opponent's Veramon (Lv.27)",
            value=f"HP: 60/90\n{'█' * 6}{'░' * 4} 67%",
            inline=True
        )
        
        battle_embed.add_field(
            name="Battle Log",
            value="Turn 3\nYour Veramon used Water Blast!\nIt's super effective!\nOpponent's Veramon takes 20 damage.",
            inline=False
        )
        
        embeds.append(battle_embed)
        
        # Trading preview
        trade_embed = theme.create_embed(
            title="Theme Preview - Trading",
            description="This is what trading screens will look like.",
            color_type=ThemeColorType.SUCCESS
        )
        
        trade_embed.add_field(
            name="Your Offer",
            value="• Aquadrake (Lv.30)\n• Fire Gem\n• 500 Coins",
            inline=True
        )
        
        trade_embed.add_field(
            name="Their Offer",
            value="• Volcanix (Lv.28)\n• Water Stone\n• 200 Coins",
            inline=True
        )
        
        embeds.append(trade_embed)
        
        # Success/error previews
        success_embed = theme.create_embed(
            title="Theme Preview - Success",
            description="This is what success messages will look like.",
            color_type=ThemeColorType.SUCCESS
        )
        
        embeds.append(success_embed)
        
        error_embed = theme.create_embed(
            title="Theme Preview - Error",
            description="This is what error messages will look like.",
            color_type=ThemeColorType.DANGER
        )
        
        embeds.append(error_embed)
        
        return embeds
    
    async def update_view(self, interaction: discord.Interaction):
        """Update the view when navigation changes."""
        # Create embed based on current tab
        embed = self._create_settings_embed()
        
        # Send the updated view
        await interaction.response.edit_message(embed=embed, view=self)

class ThemeSelectionView(EnhancedSelectionView):
    """Specialized view for theme selection."""
    
    def __init__(
        self,
        user_id: str,
        **kwargs
    ):
        super().__init__(
            user_id=user_id,
            placeholder="Select a theme",
            min_values=1,
            max_values=1,
            **kwargs
        )
        
        # Add theme options
        available_themes = theme_manager.themes.values()
        user_theme_id = theme_manager.user_themes.get(user_id, "default")
        
        for theme in available_themes:
            self.add_option(
                label=theme.name,
                value=theme.id,
                description=theme.description,
                default=theme.id == user_theme_id
            )
        
        # Add preview button
        preview_button = ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Preview Selected",
            row=1
        )
        preview_button.callback = self._on_preview
        self.add_item(preview_button)
    
    async def _on_preview(self, interaction: discord.Interaction):
        """Show a preview of the selected theme."""
        # Get selected theme
        if not self.selected_values:
            await interaction.response.send_message(
                "Please select a theme first!",
                ephemeral=True
            )
            return
        
        theme_id = self.selected_values[0]
        theme = theme_manager.get_theme(theme_id)
        
        # Create a sample embed
        embed = theme.create_embed(
            title="Theme Preview",
            description="This is how your interface will look with this theme.",
            color_type=ThemeColorType.PRIMARY
        )
        
        embed.add_field(
            name="Sample Field",
            value="This is a sample field with some text.",
            inline=True
        )
        
        embed.add_field(
            name="Another Field",
            value="This is another field with some text.",
            inline=True
        )
        
        embed.set_footer(text="This is a footer")
        
        # Send preview
        await interaction.response.send_message(
            content="Theme Preview (this message will delete in 15 seconds)",
            embed=embed,
            ephemeral=True,
            delete_after=15
        )
