"""
Settings Cog for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This cog provides user settings commands including theme customization.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List, Dict, Any

from src.utils.ui.settings_ui import UserSettingsView, ThemeSelectionView
from src.utils.ui_theme import theme_manager, ThemeColorType
from src.utils.ui.ui_registry import get_ui_registry

# Set up logging
logger = logging.getLogger('veramon.settings_cog')

class SettingsCog(commands.Cog):
    """Commands for user settings and customization."""
    
    def __init__(self, bot):
        self.bot = bot
        self.ui_registry = get_ui_registry()
    
    @app_commands.command(
        name="settings",
        description="Open your user settings menu"
    )
    async def settings_command(self, interaction: discord.Interaction):
        """Open the user settings interface."""
        user_id = str(interaction.user.id)
        
        # Create settings view
        settings_view = UserSettingsView(user_id=user_id)
        
        # Create initial embed
        theme = theme_manager.get_user_theme(user_id)
        embed = theme.create_embed(
            title="User Settings",
            description="Customize your Veramon experience.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add current theme info
        embed.add_field(
            name="Current Theme",
            value=f"{theme.name}\n{theme.description}",
            inline=False
        )
        
        # Add instructions
        embed.add_field(
            name="Instructions",
            value="Use the tabs at the top to navigate different settings categories.",
            inline=False
        )
        
        # Send settings menu
        await interaction.response.send_message(
            embed=embed,
            view=settings_view,
            ephemeral=True
        )
    
    @app_commands.command(
        name="theme",
        description="Change or view your theme settings"
    )
    async def theme_command(self, interaction: discord.Interaction):
        """Change your theme preferences."""
        user_id = str(interaction.user.id)
        
        # Create theme selection view
        theme_view = ThemeSelectionView(user_id=user_id)
        
        # Create embed
        current_theme = theme_manager.get_user_theme(user_id)
        embed = current_theme.create_embed(
            title="Theme Settings",
            description="Select a theme to customize the appearance of your Veramon bot interface.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add current theme
        embed.add_field(
            name="Current Theme",
            value=f"{current_theme.name}\n{current_theme.description}",
            inline=False
        )
        
        # Send theme selector
        await interaction.response.send_message(
            embed=embed,
            view=theme_view,
            ephemeral=True
        )
        
        # Wait for selection
        theme_id = await theme_view.wait_for_selection()
        
        if theme_id:
            # User selected a theme
            success = theme_manager.set_user_theme(user_id, theme_id)
            
            if success:
                # Get the new theme
                new_theme = theme_manager.get_theme(theme_id)
                
                # Send confirmation
                confirm_embed = new_theme.create_embed(
                    title="Theme Updated",
                    description=f"Your theme has been updated to **{new_theme.name}**.",
                    color_type=ThemeColorType.SUCCESS
                )
                
                confirm_embed.add_field(
                    name="Theme Description",
                    value=new_theme.description,
                    inline=False
                )
                
                confirm_embed.add_field(
                    name="Note",
                    value="This theme will be applied to all future interactions with the bot.",
                    inline=False
                )
                
                if interaction.response.is_done():
                    await interaction.followup.send(
                        embed=confirm_embed,
                        ephemeral=True
                    )
            else:
                # Failed to set theme
                if interaction.response.is_done():
                    await interaction.followup.send(
                        "Failed to update theme. Please try again.",
                        ephemeral=True
                    )
    
    @app_commands.command(
        name="ui_preview",
        description="Preview the different UI components"
    )
    async def ui_preview_command(self, interaction: discord.Interaction):
        """Show a preview of UI components."""
        user_id = str(interaction.user.id)
        theme = theme_manager.get_user_theme(user_id)
        
        # Create initial embed
        embed = theme.create_embed(
            title="UI Components Preview",
            description="This command shows previews of various UI components used by the Veramon bot.",
            color_type=ThemeColorType.INFO
        )
        
        # Create selection view for choosing component to preview
        selection_view = self.ui_registry.create_selection_menu(
            user_id=user_id,
            placeholder="Select a component to preview",
            min_values=1,
            max_values=1
        )
        
        # Add component options
        selection_view.add_options([
            {
                "label": "Battle UI",
                "value": "battle",
                "description": "Preview the enhanced battle interface",
                "emoji": "⚔️"
            },
            {
                "label": "Trading UI",
                "value": "trading",
                "description": "Preview the enhanced trading interface",
                "emoji": "🔄"
            },
            {
                "label": "Carousel",
                "value": "carousel",
                "description": "Preview the image/card carousel",
                "emoji": "🔄"
            },
            {
                "label": "Selection Menu",
                "value": "selection",
                "description": "Preview the enhanced selection menu",
                "emoji": "📋"
            },
            {
                "label": "Themed Embeds",
                "value": "embeds",
                "description": "Preview themed embed styles",
                "emoji": "🎨"
            }
        ])
        
        # Send selection menu
        await interaction.response.send_message(
            embed=embed,
            view=selection_view,
            ephemeral=True
        )
        
        # Wait for selection
        component = await selection_view.wait_for_selection()
        
        if component:
            # Show preview based on selection
            if component == "battle":
                await self._show_battle_preview(interaction, user_id)
            elif component == "trading":
                await self._show_trading_preview(interaction, user_id)
            elif component == "carousel":
                await self._show_carousel_preview(interaction, user_id)
            elif component == "selection":
                await self._show_selection_preview(interaction, user_id)
            elif component == "embeds":
                await self._show_embeds_preview(interaction, user_id)
    
    async def _show_battle_preview(self, interaction: discord.Interaction, user_id: str):
        """Show a preview of the battle UI."""
        theme = theme_manager.get_user_theme(user_id)
        
        # Create sample battle embed
        embed = theme.create_embed(
            title="Battle: Player vs Wild Volcanix",
            description="Turn 3\nYour turn!",
            color_type=ThemeColorType.DANGER
        )
        
        # Add player veramon
        hp_bar = "█" * 8 + "░" * 2
        embed.add_field(
            name="Your Aquadrake (Lv.30)",
            value=f"HP: 80/100\n🟩 {hp_bar} 80%",
            inline=True
        )
        
        # Add opponent veramon
        hp_bar = "█" * 6 + "░" * 4
        embed.add_field(
            name="Wild Volcanix (Lv.28)",
            value=f"HP: 60/90\n🟨 {hp_bar} 67%",
            inline=True
        )
        
        # Add battle log
        embed.add_field(
            name="Battle Log",
            value="• Volcanix used Flame Burst!\n• Your Aquadrake resisted the attack\n• Aquadrake takes 10 damage\n• Your Aquadrake used Water Blast!\n• It's super effective!",
            inline=False
        )
        
        # Create dummy battle buttons
        preview_view = discord.ui.View(timeout=120)
        
        # Move buttons
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Water Blast",
            disabled=False,
            row=0
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Tail Whip",
            disabled=False,
            row=0
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Dive",
            disabled=False,
            row=1
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Bubble Beam",
            disabled=False,
            row=1
        ))
        
        # Veramon buttons
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Aquadrake",
            disabled=True,  # Active Veramon
            row=2
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Zapfox",
            disabled=False,
            row=2
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Leafling",
            disabled=True,  # Fainted
            row=2
        ))
        
        # Action buttons
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Item",
            row=3
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Flee",
            row=3
        ))
        
        # Send preview
        await interaction.followup.send(
            content="**Battle UI Preview**\nThis is how the enhanced battle UI will appear. In a real battle, these buttons would be functional.",
            embed=embed,
            view=preview_view,
            ephemeral=True
        )
    
    async def _show_trading_preview(self, interaction: discord.Interaction, user_id: str):
        """Show a preview of the trading UI."""
        theme = theme_manager.get_user_theme(user_id)
        
        # Create sample trade embed
        embed = theme.create_embed(
            title="Trade: Player ⟷ Trainer123",
            description="Status: Negotiating",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add player's offer
        embed.add_field(
            name="Your Offer",
            value="• Aquadrake (Lv.30)\n• Fire Gem\n• 500 Coins",
            inline=True
        )
        
        # Add other player's offer
        embed.add_field(
            name="Trainer123's Offer",
            value="• Volcanix (Lv.28)\n• Water Stone\n• 200 Coins",
            inline=True
        )
        
        # Add instructions
        embed.add_field(
            name="Instructions",
            value="Add items to your offer, then click 'Confirm Trade' when ready.\nBoth parties must confirm for the trade to complete.",
            inline=False
        )
        
        # Create dummy trade buttons
        preview_view = discord.ui.View(timeout=120)
        
        # Add trade action buttons
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Add Item",
            row=0
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Remove Item",
            row=0
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Confirm Trade",
            row=1
        ))
        
        preview_view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Cancel Trade",
            row=1
        ))
        
        # Send preview
        await interaction.followup.send(
            content="**Trading UI Preview**\nThis is how the enhanced trading UI will appear. In a real trade, these buttons would be functional.",
            embed=embed,
            view=preview_view,
            ephemeral=True
        )
    
    async def _show_carousel_preview(self, interaction: discord.Interaction, user_id: str):
        """Show a preview of the carousel component."""
        theme = theme_manager.get_user_theme(user_id)
        
        # Create sample carousel with Veramon cards
        carousel_view = self.ui_registry.create_carousel(
            user_id=user_id,
            timeout=180.0,
            indicator_style="numbers"
        )
        
        # Add sample pages (Veramon cards)
        for veramon_data in [
            {
                "name": "Aquadrake",
                "level": 30,
                "type": "Water",
                "description": "A powerful drake that calls the ocean depths home. Its water attacks can wash away enemies.",
                "moves": ["Water Blast", "Tail Whip", "Dive", "Bubble Beam"],
                "stats": {"HP": 100, "Attack": 75, "Defense": 60, "Speed": 80}
            },
            {
                "name": "Volcanix",
                "level": 28,
                "type": "Fire",
                "description": "A volcanic creature with magma for blood. Its fire attacks are devastatingly hot.",
                "moves": ["Flame Burst", "Ember", "Heat Wave", "Fire Fang"],
                "stats": {"HP": 90, "Attack": 85, "Defense": 50, "Speed": 70}
            },
            {
                "name": "Zapfox",
                "level": 25,
                "type": "Electric",
                "description": "A quick and cunning fox with electricity crackling through its fur.",
                "moves": ["Thunder Shock", "Quick Attack", "Spark", "Volt Switch"],
                "stats": {"HP": 75, "Attack": 65, "Defense": 45, "Speed": 95}
            },
            {
                "name": "Leafling",
                "level": 27,
                "type": "Grass",
                "description": "A peaceful creature with leaves growing from its body. It thrives in forests.",
                "moves": ["Vine Whip", "Growth", "Razor Leaf", "Solar Beam"],
                "stats": {"HP": 85, "Attack": 60, "Defense": 70, "Speed": 55}
            }
        ]:
            # Create an embed for each Veramon
            veramon_embed = theme.create_embed(
                title=f"{veramon_data['name']} (Lv.{veramon_data['level']})",
                description=veramon_data["description"],
                color_type=ThemeColorType.PRIMARY
            )
            
            # Add type
            veramon_embed.add_field(
                name="Type",
                value=veramon_data["type"],
                inline=True
            )
            
            # Add stats
            stats_text = ""
            for stat_name, stat_value in veramon_data["stats"].items():
                stats_text += f"{stat_name}: {stat_value}\n"
            
            veramon_embed.add_field(
                name="Stats",
                value=stats_text,
                inline=True
            )
            
            # Add moves
            moves_text = ""
            for move in veramon_data["moves"]:
                moves_text += f"• {move}\n"
            
            veramon_embed.add_field(
                name="Moves",
                value=moves_text,
                inline=False
            )
            
            # Add to carousel
            carousel_view.add_page(veramon_embed)
        
        # Send carousel
        await interaction.followup.send(
            content="**Carousel Preview**\nUse the buttons below to navigate through your Veramon collection:",
            view=carousel_view,
            ephemeral=True
        )
    
    async def _show_selection_preview(self, interaction: discord.Interaction, user_id: str):
        """Show a preview of the enhanced selection menu."""
        theme = theme_manager.get_user_theme(user_id)
        
        # Create embed
        embed = theme.create_embed(
            title="Enhanced Selection Menu Preview",
            description="This shows how the enhanced selection menu works with multi-select capabilities and categorized options.",
            color_type=ThemeColorType.INFO
        )
        
        # Create selection view
        selection_view = self.ui_registry.create_selection_menu(
            user_id=user_id,
            placeholder="Select Veramon to add to your team",
            min_values=1,
            max_values=3,  # Multi-select
            timeout=180.0
        )
        
        # Add categorized options
        categories = {
            "Fire Types": [
                discord.SelectOption(
                    label="Volcanix",
                    value="volcanix",
                    description="Lv.28 Fire Type",
                    emoji="🔥"
                ),
                discord.SelectOption(
                    label="Embercub",
                    value="embercub",
                    description="Lv.15 Fire Type",
                    emoji="🔥"
                ),
            ],
            "Water Types": [
                discord.SelectOption(
                    label="Aquadrake",
                    value="aquadrake",
                    description="Lv.30 Water Type",
                    emoji="💧"
                ),
                discord.SelectOption(
                    label="Bubbler",
                    value="bubbler",
                    description="Lv.12 Water Type",
                    emoji="💧"
                ),
            ],
            "Electric Types": [
                discord.SelectOption(
                    label="Zapfox",
                    value="zapfox",
                    description="Lv.25 Electric Type",
                    emoji="⚡"
                ),
                discord.SelectOption(
                    label="Voltbug",
                    value="voltbug",
                    description="Lv.10 Electric Type",
                    emoji="⚡"
                ),
            ],
            "Grass Types": [
                discord.SelectOption(
                    label="Leafling",
                    value="leafling",
                    description="Lv.27 Grass Type",
                    emoji="🌿"
                ),
                discord.SelectOption(
                    label="Sproutling",
                    value="sproutling",
                    description="Lv.8 Grass Type",
                    emoji="🌿"
                ),
            ]
        }
        
        selection_view.categorize_options(categories)
        
        # Add instructions
        embed.add_field(
            name="Instructions",
            value="Select up to 3 Veramon to add to your team. Use the dropdown menu to browse by type.",
            inline=False
        )
        
        # Send selection view
        await interaction.followup.send(
            embed=embed,
            view=selection_view,
            ephemeral=True
        )
    
    async def _show_embeds_preview(self, interaction: discord.Interaction, user_id: str):
        """Show a preview of themed embeds."""
        theme = theme_manager.get_user_theme(user_id)
        
        # Create embeds for different color types
        embeds = []
        
        # Primary embed
        primary_embed = theme.create_embed(
            title="Primary Theme Color",
            description="This embed uses the primary theme color.",
            color_type=ThemeColorType.PRIMARY
        )
        embeds.append(primary_embed)
        
        # Secondary embed
        secondary_embed = theme.create_embed(
            title="Secondary Theme Color",
            description="This embed uses the secondary theme color.",
            color_type=ThemeColorType.SECONDARY
        )
        embeds.append(secondary_embed)
        
        # Success embed
        success_embed = theme.create_embed(
            title="Success Theme Color",
            description="This embed uses the success theme color, typically for positive outcomes.",
            color_type=ThemeColorType.SUCCESS
        )
        embeds.append(success_embed)
        
        # Danger embed
        danger_embed = theme.create_embed(
            title="Danger Theme Color",
            description="This embed uses the danger theme color, typically for errors or warnings.",
            color_type=ThemeColorType.DANGER
        )
        embeds.append(danger_embed)
        
        # Info embed
        info_embed = theme.create_embed(
            title="Info Theme Color",
            description="This embed uses the info theme color, typically for informational messages.",
            color_type=ThemeColorType.INFO
        )
        embeds.append(info_embed)
        
        # Accent embed
        accent_embed = theme.create_embed(
            title="Accent Theme Color",
            description="This embed uses the accent theme color, for highlighted content.",
            color_type=ThemeColorType.ACCENT
        )
        embeds.append(accent_embed)
        
        # Create carousel with embeds
        carousel_view = self.ui_registry.create_carousel(
            user_id=user_id,
            timeout=180.0,
            indicator_style="text"
        )
        
        # Add embeds to carousel
        for embed in embeds:
            carousel_view.add_page(embed)
        
        # Send embeds carousel
        await interaction.followup.send(
            content="**Themed Embeds Preview**\nUse the buttons below to see different theme colors:",
            view=carousel_view,
            ephemeral=True
        )

async def setup(bot):
    """Add the settings cog to the bot."""
    await bot.add_cog(SettingsCog(bot))
