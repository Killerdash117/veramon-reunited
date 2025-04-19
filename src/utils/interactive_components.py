import discord
from discord.ext import commands
from discord import ui
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
import asyncio
import json

from src.utils.ui_theme import theme_manager, ThemeColorType, create_themed_embed
from src.utils.user_settings import get_user_settings
from src.utils.interactive_ui import InteractiveView, NavigableView, NavigationType

class MainMenuView(NavigableView):
    """
    Main menu interface for the bot with quick access to all major features.
    """
    
    def __init__(self, user_id: str, **kwargs):
        super().__init__(
            user_id=user_id,
            navigation_type=NavigationType.DASHBOARD,
            ephemeral=True,
            **kwargs
        )
        
        # Add main menu buttons
        self._setup_dashboard()
        
    def _setup_dashboard(self):
        """Set up the dashboard buttons."""
        # Row 1: Main gameplay functions
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Explore",
            emoji="🌍",
            custom_id="explore_button",
            row=0
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Battle",
            emoji="⚔️",
            custom_id="battle_button",
            row=0
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Trade",
            emoji="🔄",
            custom_id="trade_button",
            row=0
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Collection",
            emoji="📦",
            custom_id="collection_button",
            row=0
        ))
        
        # Row 2: Secondary features
        self.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Profile",
            emoji="👤",
            custom_id="profile_button",
            row=1
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Shop",
            emoji="🛒",
            custom_id="shop_button",
            row=1
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Quests",
            emoji="📜",
            custom_id="quests_button",
            row=1
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Leaderboard",
            emoji="🏆",
            custom_id="leaderboard_button",
            row=1
        ))
        
        # Row 3: Settings and help
        self.add_item(ui.Button(
            style=discord.ButtonStyle.success,
            label="Daily Rewards",
            emoji="🎁",
            custom_id="daily_button",
            row=2
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.danger,
            label="Settings",
            emoji="⚙️",
            custom_id="settings_button",
            row=2
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Help",
            emoji="❓",
            custom_id="help_button",
            row=2
        ))
        
    @ui.button(custom_id="explore_button")
    async def explore_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Open the exploration menu."""
        await interaction.response.defer(ephemeral=True)
        # Create and send exploration view
        view = ExplorationView(user_id=str(interaction.user.id))
        embed = create_themed_embed(
            str(interaction.user.id),
            title="🌍 Exploration",
            description="Discover new Veramon across various biomes!",
            color_type=ThemeColorType.PRIMARY
        )
        await view.send_to(interaction, embed=embed)
        
    @ui.button(custom_id="battle_button")
    async def battle_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Open the battle menu."""
        await interaction.response.defer(ephemeral=True)
        # Create and send battle view
        view = BattleMenuView(user_id=str(interaction.user.id))
        embed = create_themed_embed(
            str(interaction.user.id),
            title="⚔️ Battle System",
            description="Test your skills against trainers and other players!",
            color_type=ThemeColorType.DANGER
        )
        await view.send_to(interaction, embed=embed)
        
    @ui.button(custom_id="trade_button")
    async def trade_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Open the trade menu."""
        await interaction.response.defer(ephemeral=True)
        # Create and send trade view
        view = TradeMenuView(user_id=str(interaction.user.id))
        embed = create_themed_embed(
            str(interaction.user.id),
            title="🔄 Trading System",
            description="Exchange Veramon with other players!",
            color_type=ThemeColorType.ACCENT
        )
        await view.send_to(interaction, embed=embed)
        
    @ui.button(custom_id="collection_button")
    async def collection_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Open the collection menu."""
        await interaction.response.defer(ephemeral=True)
        # Create and send collection view
        view = CollectionView(user_id=str(interaction.user.id))
        embed = create_themed_embed(
            str(interaction.user.id),
            title="📦 Your Collection",
            description="View and manage your Veramon collection!",
            color_type=ThemeColorType.SUCCESS
        )
        await view.send_to(interaction, embed=embed)
        
    @ui.button(custom_id="settings_button")
    async def settings_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Open the settings menu."""
        await interaction.response.defer(ephemeral=True)
        # Create and send settings view
        view = SettingsView(user_id=str(interaction.user.id))
        embed = create_themed_embed(
            str(interaction.user.id),
            title="⚙️ Settings",
            description="Customize your Veramon Reunited experience!",
            color_type=ThemeColorType.NEUTRAL
        )
        await view.send_to(interaction, embed=embed)
        
    @ui.button(custom_id="help_button")
    async def help_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Open the help menu."""
        await interaction.response.defer(ephemeral=True)
        # Create and send help view
        view = HelpView(user_id=str(interaction.user.id))
        embed = create_themed_embed(
            str(interaction.user.id),
            title="❓ Help & Information",
            description="Learn how to play Veramon Reunited!",
            color_type=ThemeColorType.INFO
        )
        await view.send_to(interaction, embed=embed)

class ExplorationView(NavigableView):
    """
    Interactive view for exploring and catching Veramon.
    """
    
    def __init__(self, user_id: str, **kwargs):
        super().__init__(
            user_id=user_id,
            navigation_type=NavigationType.TABS,
            **kwargs
        )
        
        # Set up tabs
        self.setup_tabs(["Biomes", "Exploration", "Encounters", "Catch Rates"])
        self._setup_biome_buttons()
        
    def _setup_biome_buttons(self):
        """Set up buttons for different biomes."""
        # Add biome buttons (first row)
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Forest",
            emoji="🌲",
            custom_id="forest_button",
            row=1
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Mountain",
            emoji="⛰️",
            custom_id="mountain_button",
            row=1
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Ocean",
            emoji="🌊",
            custom_id="ocean_button",
            row=1
        ))
        
        # Add more biome buttons (second row)
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Desert",
            emoji="🏜️",
            custom_id="desert_button",
            row=2
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Cave",
            emoji="🕳️",
            custom_id="cave_button",
            row=2
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Volcano",
            emoji="🌋",
            custom_id="volcano_button",
            row=2
        ))
        
        # Add action button
        self.add_item(ui.Button(
            style=discord.ButtonStyle.success,
            label="Explore Selected Biome",
            emoji="🔍",
            custom_id="start_explore_button",
            row=3
        ))
        
    async def update_view(self, interaction: discord.Interaction):
        """Update the view based on the current tab."""
        tab = self.get_current_tab()
        
        if tab == "Biomes":
            embed = create_themed_embed(
                self.user_id,
                title="🌍 Exploration - Biomes",
                description="Choose a biome to explore. Different biomes have different Veramon!",
                color_type=ThemeColorType.PRIMARY
            )
            
            # Add biome descriptions
            embed.add_field(
                name="🌲 Forest",
                value="A lush woodland teeming with grass, bug, and normal type Veramon.",
                inline=True
            )
            
            embed.add_field(
                name="⛰️ Mountain",
                value="Rocky peaks home to rock, fighting, and flying type Veramon.",
                inline=True
            )
            
            embed.add_field(
                name="🌊 Ocean",
                value="Vast waters filled with water, ice, and dragon type Veramon.",
                inline=True
            )
            
            embed.add_field(
                name="🏜️ Desert",
                value="Arid sands inhabited by ground, fire, and steel type Veramon.",
                inline=True
            )
            
            embed.add_field(
                name="🕳️ Cave",
                value="Dark caverns with rock, dark, and ghost type Veramon.",
                inline=True
            )
            
            embed.add_field(
                name="🌋 Volcano",
                value="Fiery mountains containing fire, rock, and dragon type Veramon.",
                inline=True
            )
            
        elif tab == "Exploration":
            embed = create_themed_embed(
                self.user_id,
                title="🔍 Exploration - Status",
                description="Your exploration status and cooldowns.",
                color_type=ThemeColorType.INFO
            )
            
            # Add exploration status info (this would be fetched from the database in a real implementation)
            embed.add_field(
                name="Last Exploration",
                value="10 minutes ago",
                inline=True
            )
            
            embed.add_field(
                name="Cooldown Status",
                value="Ready to explore!",
                inline=True
            )
            
            embed.add_field(
                name="Exploration Boosts",
                value="None active",
                inline=True
            )
            
        elif tab == "Encounters":
            embed = create_themed_embed(
                self.user_id,
                title="🔎 Recent Encounters",
                description="Your most recent Veramon encounters.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # This would show recent encounters from the database
            embed.add_field(
                name="No Recent Encounters",
                value="Go explore to find Veramon!",
                inline=False
            )
            
        elif tab == "Catch Rates":
            embed = create_themed_embed(
                self.user_id,
                title="📊 Catch Rate Information",
                description="Learn about catch rates and how to improve them.",
                color_type=ThemeColorType.ACCENT
            )
            
            embed.add_field(
                name="Base Catch Rate",
                value="Each Veramon has a base catch rate that depends on its rarity.\n"
                      "Common: 70%\nUncommon: 40%\nRare: 20%\nLegendary: 5%",
                inline=False
            )
            
            embed.add_field(
                name="Catch Items",
                value="Different items can improve your catch rate:\n"
                      "Basic Ball: x1.0 (base)\n"
                      "Great Ball: x1.5\n"
                      "Ultra Ball: x2.0\n"
                      "Master Ball: Guaranteed catch",
                inline=False
            )
            
            embed.add_field(
                name="VIP Bonuses",
                value="VIP members get a +10% catch rate bonus!",
                inline=False
            )
            
        await interaction.response.edit_message(embed=embed, view=self)
        
    @ui.button(custom_id="start_explore_button")
    async def start_explore_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Start exploration in the selected biome."""
        # In a real implementation, this would trigger an exploration
        # For now, we'll just show a message
        await interaction.response.defer(ephemeral=True)
        
        embed = create_themed_embed(
            self.user_id,
            title="🔍 Exploration Started!",
            description="You have started exploring! Click the buttons below to interact with any Veramon you find.",
            color_type=ThemeColorType.SUCCESS
        )
        
        # Here we would actually check the database and spawn a Veramon
        # For demonstration, we'll just show a mock encounter
        embed.add_field(
            name="You found a Veramon!",
            value="A wild Blazitar appeared! Level 12",
            inline=False
        )
        
        # Create a view for the encounter
        encounter_view = EncounterView(self.user_id, "Blazitar", 12, False)
        await encounter_view.send_to(interaction, embed=embed)

class EncounterView(InteractiveView):
    """View for handling a wild Veramon encounter."""
    
    def __init__(self, user_id: str, veramon_name: str, level: int, shiny: bool = False, **kwargs):
        super().__init__(user_id, **kwargs)
        self.veramon_name = veramon_name
        self.level = level
        self.shiny = shiny
        
    @ui.button(label="Catch", style=discord.ButtonStyle.success, emoji="🔴", row=1)
    async def catch_button(self, interaction: discord.Interaction, button: ui.Button):
        """Attempt to catch the Veramon."""
        await interaction.response.defer(ephemeral=True)
        
        # In a real implementation, this would calculate catch success
        # For demonstration, we'll just show a success message
        import random
        success = random.random() < 0.7  # 70% chance of success
        
        if success:
            embed = create_themed_embed(
                self.user_id,
                title="✅ Catch Successful!",
                description=f"You caught the {self.veramon_name}!",
                color_type=ThemeColorType.SUCCESS
            )
            
            embed.add_field(
                name="Veramon Details",
                value=f"Level: {self.level}\nShiny: {'Yes' if self.shiny else 'No'}",
                inline=False
            )
            
            embed.add_field(
                name="Added to Collection",
                value=f"{self.veramon_name} has been added to your collection!",
                inline=False
            )
        else:
            embed = create_themed_embed(
                self.user_id,
                title="❌ Catch Failed",
                description=f"The {self.veramon_name} broke free!",
                color_type=ThemeColorType.DANGER
            )
            
            embed.add_field(
                name="Try Again",
                value="You can try to catch it again or use a different Pokéball.",
                inline=False
            )
            
        # Disable catch button after attempt
        button.disabled = True
        await interaction.edit_original_response(embed=embed, view=self)
        
    @ui.button(label="Use Item", style=discord.ButtonStyle.primary, emoji="🎒", row=1)
    async def item_button(self, interaction: discord.Interaction, button: ui.Button):
        """Use an item during the encounter."""
        # Open item selection view
        await interaction.response.defer(ephemeral=True)
        
        embed = create_themed_embed(
            self.user_id,
            title="🎒 Select an Item",
            description="Choose an item to use during this encounter.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # In a real implementation, this would fetch items from the player's inventory
        embed.add_field(
            name="Poké Balls",
            value="Basic Ball (x10)\nGreat Ball (x5)\nUltra Ball (x2)",
            inline=True
        )
        
        embed.add_field(
            name="Berries",
            value="Razz Berry (x3)\nNanab Berry (x1)",
            inline=True
        )
        
        # Create a selection menu for items
        item_view = InteractiveView(self.user_id)
        item_view.add_item(ui.Select(
            placeholder="Select an item to use",
            custom_id="item_select",
            options=[
                discord.SelectOption(label="Basic Ball", emoji="🔴", description="Standard catch rate"),
                discord.SelectOption(label="Great Ball", emoji="🔵", description="1.5x catch rate"),
                discord.SelectOption(label="Ultra Ball", emoji="⚫", description="2x catch rate"),
                discord.SelectOption(label="Razz Berry", emoji="🍓", description="Makes Veramon easier to catch"),
                discord.SelectOption(label="Nanab Berry", emoji="🍌", description="Calms Veramon movement")
            ]
        ))
        
        await item_view.send_to(interaction, embed=embed)
        
    @ui.button(label="Run", style=discord.ButtonStyle.secondary, emoji="🏃", row=1)
    async def run_button(self, interaction: discord.Interaction, button: ui.Button):
        """Run from the encounter."""
        await interaction.response.defer(ephemeral=True)
        
        embed = create_themed_embed(
            self.user_id,
            title="🏃 Got Away Safely",
            description="You ran away from the encounter.",
            color_type=ThemeColorType.NEUTRAL
        )
        
        # Disable all buttons
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = True
                
        await interaction.edit_original_response(embed=embed, view=self)

# We would continue with implementing other views like BattleMenuView, 
# TradeMenuView, CollectionView, SettingsView, and HelpView
# These would be similar in structure to the ExplorationView
