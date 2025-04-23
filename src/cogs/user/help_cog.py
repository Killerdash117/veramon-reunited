"""
Help System for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module implements a comprehensive help system that displays
all available bot commands organized by categories.
"""

import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from typing import Dict, List, Optional, Union
import asyncio

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel


class HelpCog(commands.Cog):
    """
    Help system for Veramon Reunited.
    
    Provides users with a comprehensive list of all available commands,
    organized by category with descriptions and usage examples.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="help", description="View all available bot commands")
    @app_commands.describe(
        category="Optional: Specific command category to view (e.g., 'battle', 'trading', 'veramon')"
    )
    @require_permission_level(PermissionLevel.USER)
    async def help_command(self, interaction: discord.Interaction, category: Optional[str] = None):
        """Display all available commands with descriptions."""
        try:
            # Define category icons and colors
            category_meta = {
                "Getting Started": {"icon": "🌱", "color": discord.Color.green()},
                "Veramon": {"icon": "🧬", "color": discord.Color.blue()},
                "Battle": {"icon": "⚔️", "color": discord.Color.red()},
                "Trading": {"icon": "🔄", "color": discord.Color.gold()},
                "Team": {"icon": "👥", "color": discord.Color.purple()},
                "Exploration": {"icon": "🗺️", "color": discord.Color.dark_teal()},
                "Achievements": {"icon": "🏆", "color": discord.Color.dark_gold()},
                "Events": {"icon": "🎉", "color": discord.Color.magenta()},
                "Social": {"icon": "💬", "color": discord.Color.light_grey()},
                "Economy": {"icon": "💰", "color": discord.Color(0xF1C40F)},  # Gold
                "Faction": {"icon": "🏰", "color": discord.Color.dark_red()},
                "Settings": {"icon": "⚙️", "color": discord.Color.dark_grey()},
                "Admin": {"icon": "🛡️", "color": discord.Color.dark_purple()},
            }
            
            # Define all command categories and their commands
            commands_by_category = {
                "Getting Started": [
                    {
                        "name": "/help",
                        "description": "View all available commands",
                        "example": "/help trading"
                    },
                    {
                        "name": "/start",
                        "description": "Begin your Veramon adventure",
                        "example": "/start"
                    },
                    {
                        "name": "/daily",
                        "description": "Claim your daily rewards",
                        "example": "/daily"
                    },
                    {
                        "name": "/profile",
                        "description": "View your trainer profile",
                        "example": "/profile"
                    }
                ],
                "Veramon": [
                    {
                        "name": "/collection",
                        "description": "View your captured Veramon",
                        "example": "/collection"
                    },
                    {
                        "name": "/veramon_details",
                        "description": "View details about a Veramon",
                        "example": "/veramon_details 42"
                    },
                    {
                        "name": "/evolve",
                        "description": "Evolve an eligible Veramon",
                        "example": "/evolve 42"
                    },
                    {
                        "name": "/nickname",
                        "description": "Give a nickname to your Veramon",
                        "example": "/nickname 42 Sparky"
                    },
                    {
                        "name": "/transform",
                        "description": "Transform Veramon into special form",
                        "example": "/transform 42 shadow"
                    },
                    {
                        "name": "/revert_form",
                        "description": "Revert Veramon to normal form",
                        "example": "/revert_form 42"
                    }
                ],
                "Battle": [
                    {
                        "name": "/battle_pve",
                        "description": "Battle an NPC trainer",
                        "example": "/battle_pve normal"
                    },
                    {
                        "name": "/battle_pvp",
                        "description": "Challenge another player",
                        "example": "/battle_pvp @Username"
                    },
                    {
                        "name": "/battle_wild",
                        "description": "Battle a wild Veramon in current biome",
                        "example": "/battle_wild"
                    },
                    {
                        "name": "/battle_multi",
                        "description": "Start a multi-player battle",
                        "example": "/battle_multi 2v2"
                    },
                    {
                        "name": "/battle_menu",
                        "description": "Open interactive battle menu",
                        "example": "/battle_menu"
                    }
                ],
                "Trading": [
                    {
                        "name": "/trade_create",
                        "description": "Create a new trade with another player",
                        "example": "/trade_create @Username"
                    },
                    {
                        "name": "/trade_add",
                        "description": "Add a Veramon to your current trade",
                        "example": "/trade_add 42"
                    },
                    {
                        "name": "/trade_remove",
                        "description": "Remove a Veramon from your trade",
                        "example": "/trade_remove 42"
                    },
                    {
                        "name": "/trade_cancel",
                        "description": "Cancel your current trade",
                        "example": "/trade_cancel"
                    },
                    {
                        "name": "/trade_list",
                        "description": "View your active and recent trades",
                        "example": "/trade_list"
                    },
                    {
                        "name": "/trade_menu",
                        "description": "Open the interactive trading menu",
                        "example": "/trade_menu"
                    }
                ],
                "Exploration": [
                    {
                        "name": "/explore",
                        "description": "Explore a biome to encounter wild Veramon",
                        "example": "/explore forest hidden_grove"
                    },
                    {
                        "name": "/catch",
                        "description": "Attempt to catch a wild Veramon",
                        "example": "/catch greatball"
                    },
                    {
                        "name": "/weather",
                        "description": "Check current weather in biomes",
                        "example": "/weather"
                    },
                    {
                        "name": "/special_areas",
                        "description": "View special exploration areas",
                        "example": "/special_areas forest"
                    },
                    {
                        "name": "/biomes",
                        "description": "View available biomes",
                        "example": "/biomes"
                    }
                ],
                "Economy": [
                    {
                        "name": "/balance",
                        "description": "Check your token balance and economy stats",
                        "example": "/balance"
                    },
                    {
                        "name": "/daily",
                        "description": "Claim your daily token reward",
                        "example": "/daily"
                    },
                    {
                        "name": "/shop",
                        "description": "Browse the item shop",
                        "example": "/shop"
                    },
                    {
                        "name": "/shop_buy",
                        "description": "Purchase an item from the shop",
                        "example": "/shop_buy greatball 5"
                    },
                    {
                        "name": "/inventory",
                        "description": "View your current inventory",
                        "example": "/inventory"
                    },
                    {
                        "name": "/quests",
                        "description": "View your active and completed quests",
                        "example": "/quests"
                    },
                    {
                        "name": "/transfer",
                        "description": "Transfer tokens to another player",
                        "example": "/transfer @Username 100 Here's your tokens!"
                    },
                    {
                        "name": "/transaction_history",
                        "description": "View your token transaction history",
                        "example": "/transaction_history"
                    }
                ],
                "Social": [
                    {
                        "name": "/profile",
                        "description": "View your or another player's profile",
                        "example": "/profile @Username"
                    },
                    {
                        "name": "/leaderboard",
                        "description": "View game leaderboards",
                        "example": "/leaderboard tokens all"
                    },
                    {
                        "name": "/guild_create",
                        "description": "Create a new guild",
                        "example": "/guild_create Dragon Tamers"
                    },
                    {
                        "name": "/guild_join",
                        "description": "Join a guild by invitation code",
                        "example": "/guild_join ABCD123"
                    },
                    {
                        "name": "/guild_info",
                        "description": "View information about your guild",
                        "example": "/guild_info"
                    },
                    {
                        "name": "/guild_leave",
                        "description": "Leave your current guild",
                        "example": "/guild_leave"
                    },
                    {
                        "name": "/guild_list",
                        "description": "List all guilds on the server",
                        "example": "/guild_list"
                    },
                    {
                        "name": "/guild_invite",
                        "description": "Invite a player to your guild",
                        "example": "/guild_invite @Username"
                    },
                    {
                        "name": "/guild_promote",
                        "description": "Promote a guild member",
                        "example": "/guild_promote @Username officer"
                    },
                    {
                        "name": "/guild_kick",
                        "description": "Remove a member from your guild",
                        "example": "/guild_kick @Username"
                    }
                ],
                "Team": [
                    {
                        "name": "/team",
                        "description": "Manage preset battle teams",
                        "example": "/team create FireTeam"
                    },
                    {
                        "name": "/team_add",
                        "description": "Add a Veramon to a team",
                        "example": "/team_add FireTeam 42 1"
                    },
                    {
                        "name": "/team_remove",
                        "description": "Remove a Veramon from a team",
                        "example": "/team_remove FireTeam 2"
                    },
                    {
                        "name": "/team_rename",
                        "description": "Rename an existing team",
                        "example": "/team_rename FireTeam WaterTeam"
                    }
                ],
                "Settings": [
                    {
                        "name": "/settings",
                        "description": "View your current settings",
                        "example": "/settings"
                    },
                    {
                        "name": "/settings_set",
                        "description": "Change a specific setting",
                        "example": "/settings_set ui_animations true"
                    },
                    {
                        "name": "/settings_reset",
                        "description": "Reset settings to default values",
                        "example": "/settings_reset all"
                    },
                    {
                        "name": "/theme",
                        "description": "View available themes or set theme",
                        "example": "/theme dark"
                    },
                    {
                        "name": "/theme_preview",
                        "description": "Preview a theme without changing",
                        "example": "/theme_preview cosmic"
                    },
                    {
                        "name": "/theme_create",
                        "description": "Create a custom theme (VIP only)",
                        "example": "/theme_create MyTheme dark"
                    }
                ],
                "Admin": [
                    {
                        "name": "/admin_add_veramon",
                        "description": "Add a new Veramon to the game",
                        "example": "/admin_add_veramon Fluffymon Fire,Flying rare"
                    },
                    {
                        "name": "/admin_edit_veramon",
                        "description": "Edit an existing Veramon's data",
                        "example": "/admin_edit_veramon Fluffymon type Water,Flying"
                    },
                    {
                        "name": "/admin_add_ability",
                        "description": "Add a new ability to the game",
                        "example": "/admin_add_ability FireBlast Fire 80 0.85"
                    },
                    {
                        "name": "/admin_give_veramon",
                        "description": "Give a Veramon to a player",
                        "example": "/admin_give_veramon @Username Fluffymon 15 true"
                    },
                    {
                        "name": "/admin_spawn_rate",
                        "description": "Adjust spawn rates for a biome",
                        "example": "/admin_spawn_rate forest legendary 2.5"
                    }
                ]
            }
            
            # If category was specified, show commands for that category
            if category:
                # Normalize category name for case-insensitive comparison
                normalized_category = category.lower()
                found_category = False
                
                for cat_name in commands_by_category.keys():
                    if cat_name.lower() == normalized_category:
                        meta = category_meta.get(cat_name, {"icon": "📄", "color": discord.Color.blue()})
                        
                        embed = discord.Embed(
                            title=f"{meta['icon']} {cat_name} Commands",
                            description=f"List of all {cat_name.lower()} commands for Veramon Reunited.",
                            color=meta['color']
                        )
                        
                        # Add thumbnail based on category
                        if cat_name == "Battle":
                            embed.set_thumbnail(url="https://i.imgur.com/JoqLzXD.png")  # Battle icon
                        elif cat_name == "Veramon":
                            embed.set_thumbnail(url="https://i.imgur.com/4z9HPWJ.png")  # Veramon icon
                        elif cat_name == "Trading":
                            embed.set_thumbnail(url="https://i.imgur.com/2Nx8JKz.png")  # Trading icon
                        
                        # Group commands by functionality
                        cmd_groups = {}
                        for cmd in commands_by_category[cat_name]:
                            # Extract the base command name without parameters
                            base_cmd = cmd["name"].split()[0]
                            if base_cmd not in cmd_groups:
                                cmd_groups[base_cmd] = []
                            cmd_groups[base_cmd].append(cmd)
                        
                        # Add fields for each command group
                        for base_cmd, cmds in cmd_groups.items():
                            for cmd in cmds:
                                # Format command name with syntax highlighting
                                cmd_format = f"`{cmd['name']}`"
                                
                                # Add example with proper formatting
                                example = f"`{cmd['example']}`"
                                
                                embed.add_field(
                                    name=cmd_format,
                                    value=f"{cmd['description']}\n**Example:** {example}",
                                    inline=False
                                )
                        
                        # Add a footer with navigation help
                        embed.set_footer(text=f"Use /help to see all categories • Veramon Reunited v0.44.0")
                        
                        # Create a "Back to Main Menu" button
                        view = discord.ui.View(timeout=180)
                        
                        back_button = discord.ui.Button(
                            style=discord.ButtonStyle.secondary,
                            label="Back to Main Menu",
                            emoji="↩️"
                        )
                        
                        async def back_callback(interaction: discord.Interaction):
                            await self.help_command(interaction)
                            
                        back_button.callback = back_callback
                        view.add_item(back_button)
                        
                        # Add a link to documentation if available
                        docs_button = discord.ui.Button(
                            style=discord.ButtonStyle.link,
                            label="📖 Documentation",
                            url="https://github.com/killerdash117/veramon-reunited"
                        )
                        view.add_item(docs_button)
                        
                        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                        found_category = True
                        break
                
                # If category not found
                if not found_category:
                    await interaction.response.send_message(
                        f"Category '{category}' not found. Use `/help` without parameters to see all categories.",
                        ephemeral=True
                    )
                return
            
            # If no category was specified, show the main help menu with rich formatting
            embed = discord.Embed(
                title="📚 Veramon Reunited Command Guide",
                description="Welcome to Veramon Reunited! Below are the command categories to help you on your journey.\nSelect a category to see detailed commands.",
                color=discord.Color.brand_green()
            )
            
            # Add logo/thumbnail
            embed.set_thumbnail(url="https://i.imgur.com/W5reXLn.png")
            
            # Organize categories in a visually pleasing way
            for category, commands_list in commands_by_category.items():
                meta = category_meta.get(category, {"icon": "📄", "color": discord.Color.blue()})
                cmd_count = len(commands_list)
                embed.add_field(
                    name=f"{meta['icon']} {category}",
                    value=f"`{cmd_count} commands` • `/help {category.lower()}`",
                    inline=True
                )
            
            # Add tips section at the bottom
            embed.add_field(
                name="💡 Quick Tips",
                value="• Use `/start` to begin your adventure\n• `/daily` rewards refresh every 24 hours\n• Need help with a specific command? Try `/help [command name]`",
                inline=False
            )
            
            embed.set_footer(text="Veramon Reunited v0.44.0 • Created by killerdash117")
            
            # Create view with buttons and select menu for categories
            view = discord.ui.View(timeout=180)
            
            # Add select menu for categories
            options = []
            for cat in commands_by_category.keys():
                meta = category_meta.get(cat, {"icon": "📄", "color": discord.Color.blue()})
                options.append(
                    discord.SelectOption(
                        label=cat,
                        description=f"View {cat.lower()} commands",
                        emoji=meta['icon']
                    )
                )
            
            select = discord.ui.Select(
                placeholder="Choose a command category...",
                options=options,
                min_values=1,
                max_values=1
            )
            
            async def select_callback(interaction: discord.Interaction):
                selected_category = select.values[0]
                
                # Call help command with selected category
                await self.help_command(interaction, category=selected_category)
            
            select.callback = select_callback
            view.add_item(select)
            
            # Add common action buttons for quick access to popular commands
            action_row = discord.ui.View(timeout=180)
            
            # Add buttons for most common commands
            start_button = discord.ui.Button(
                style=discord.ButtonStyle.success,
                label="Start Adventure",
                emoji="🌱",
                row=1
            )
            
            async def start_callback(interaction: discord.Interaction):
                # Simulate calling the /start command
                await interaction.response.send_message("Redirecting to the start command...", ephemeral=True)
                
                # Here you would typically call the actual start command logic
                # For now we'll just provide info
                start_embed = discord.Embed(
                    title="🌱 Starting Your Adventure",
                    description="To start your Veramon adventure, use the `/start` command. This will allow you to:",
                    color=discord.Color.green()
                )
                start_embed.add_field(name="1. Choose a starter Veramon", value="Select from a variety of starter Veramon to begin your journey", inline=False)
                start_embed.add_field(name="2. Get starter items", value="Receive essential items to help you catch and train Veramon", inline=False)
                start_embed.add_field(name="3. Begin your quest", value="Start your journey to become a Veramon Master", inline=False)
                
                await interaction.followup.send(embed=start_embed, ephemeral=True)
                
            start_button.callback = start_callback
            view.add_item(start_button)
            
            # Add a link to documentation if available
            docs_button = discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Documentation",
                emoji="📖",
                url="https://github.com/killerdash117/veramon-reunited",
                row=1
            )
            
            view.add_item(docs_button)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in help command: {e}")
            await interaction.response.send_message("An error occurred while processing the help command. Please try again later.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
