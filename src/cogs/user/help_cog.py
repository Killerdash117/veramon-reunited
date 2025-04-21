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
                        "name": "/veramon_details [capture_id]",
                        "description": "View details about a Veramon",
                        "example": "/veramon_details 42"
                    },
                    {
                        "name": "/evolve [capture_id]",
                        "description": "Evolve an eligible Veramon",
                        "example": "/evolve 42"
                    },
                    {
                        "name": "/nickname [capture_id] [nickname]",
                        "description": "Give a nickname to your Veramon",
                        "example": "/nickname 42 Sparky"
                    },
                    {
                        "name": "/transform [capture_id] [form_id]",
                        "description": "Transform Veramon into special form",
                        "example": "/transform 42 shadow"
                    },
                    {
                        "name": "/revert_form [capture_id]",
                        "description": "Revert Veramon to normal form",
                        "example": "/revert_form 42"
                    }
                ],
                "Battle": [
                    {
                        "name": "/battle_pve [difficulty]",
                        "description": "Battle an NPC trainer",
                        "example": "/battle_pve normal"
                    },
                    {
                        "name": "/battle_pvp [player]",
                        "description": "Challenge another player",
                        "example": "/battle_pvp @Username"
                    },
                    {
                        "name": "/battle_wild",
                        "description": "Battle a wild Veramon in current biome",
                        "example": "/battle_wild"
                    },
                    {
                        "name": "/battle_multi [type]",
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
                        "name": "/trade_create [player]",
                        "description": "Create a new trade with another player",
                        "example": "/trade_create @Username"
                    },
                    {
                        "name": "/trade_add [capture_id]",
                        "description": "Add a Veramon to your current trade",
                        "example": "/trade_add 42"
                    },
                    {
                        "name": "/trade_remove [capture_id]",
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
                        "name": "/explore [biome] [special_area]",
                        "description": "Explore a biome to encounter wild Veramon",
                        "example": "/explore forest hidden_grove"
                    },
                    {
                        "name": "/catch [item]",
                        "description": "Attempt to catch a wild Veramon",
                        "example": "/catch greatball"
                    },
                    {
                        "name": "/weather",
                        "description": "Check current weather in biomes",
                        "example": "/weather"
                    },
                    {
                        "name": "/special_areas [biome]",
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
                        "name": "/shop_buy [item_id] [quantity]",
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
                        "name": "/transfer [user] [amount] [message]",
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
                        "name": "/profile [user]",
                        "description": "View your or another player's profile",
                        "example": "/profile @Username"
                    },
                    {
                        "name": "/leaderboard [category] [timeframe]",
                        "description": "View game leaderboards",
                        "example": "/leaderboard tokens all"
                    },
                    {
                        "name": "/guild_create [name]",
                        "description": "Create a new guild",
                        "example": "/guild_create Dragon Tamers"
                    },
                    {
                        "name": "/guild_join [code]",
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
                        "name": "/guild_invite [user]",
                        "description": "Invite a player to your guild",
                        "example": "/guild_invite @Username"
                    },
                    {
                        "name": "/guild_promote [member] [role]",
                        "description": "Promote a guild member",
                        "example": "/guild_promote @Username officer"
                    },
                    {
                        "name": "/guild_kick [member]",
                        "description": "Remove a member from your guild",
                        "example": "/guild_kick @Username"
                    }
                ],
                "Team": [
                    {
                        "name": "/team [action] [team_name]",
                        "description": "Manage preset battle teams",
                        "example": "/team create FireTeam"
                    },
                    {
                        "name": "/team_add [team_name] [capture_id] [position]",
                        "description": "Add a Veramon to a team",
                        "example": "/team_add FireTeam 42 1"
                    },
                    {
                        "name": "/team_remove [team_name] [position]",
                        "description": "Remove a Veramon from a team",
                        "example": "/team_remove FireTeam 2"
                    },
                    {
                        "name": "/team_rename [team_name] [new_name]",
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
                        "name": "/settings_set [setting] [value]",
                        "description": "Change a specific setting",
                        "example": "/settings_set ui_animations true"
                    },
                    {
                        "name": "/settings_reset [setting]",
                        "description": "Reset settings to default values",
                        "example": "/settings_reset all"
                    },
                    {
                        "name": "/theme [theme_name]",
                        "description": "View available themes or set theme",
                        "example": "/theme dark"
                    },
                    {
                        "name": "/theme_preview [theme_name]",
                        "description": "Preview a theme without changing",
                        "example": "/theme_preview cosmic"
                    },
                    {
                        "name": "/theme_create [theme_name] [base_theme]",
                        "description": "Create a custom theme (VIP only)",
                        "example": "/theme_create MyTheme dark"
                    }
                ],
                "Admin": [
                    {
                        "name": "/admin_add_veramon [name] [types] [rarity]",
                        "description": "Add a new Veramon to the game",
                        "example": "/admin_add_veramon Fluffymon Fire,Flying rare"
                    },
                    {
                        "name": "/admin_edit_veramon [name] [field] [value]",
                        "description": "Edit an existing Veramon's data",
                        "example": "/admin_edit_veramon Fluffymon type Water,Flying"
                    },
                    {
                        "name": "/admin_add_ability [name] [details]",
                        "description": "Add a new ability to the game",
                        "example": "/admin_add_ability FireBlast Fire 80 0.85"
                    },
                    {
                        "name": "/admin_give_veramon [player] [veramon]",
                        "description": "Give a Veramon to a player",
                        "example": "/admin_give_veramon @Username Fluffymon 15 true"
                    },
                    {
                        "name": "/admin_spawn_rate [biome] [rarity] [percentage]",
                        "description": "Adjust spawn rates for a biome",
                        "example": "/admin_spawn_rate forest legendary 2.5"
                    }
                ]
            }
            
            # If a specific category was requested
            if category:
                category_lower = category.lower()
                found_category = False
                
                for cat_name, commands_list in commands_by_category.items():
                    if category_lower in cat_name.lower():
                        embed = discord.Embed(
                            title=f"📚 {cat_name} Commands",
                            description=f"List of all {cat_name.lower()} commands for Veramon Reunited.",
                            color=discord.Color.blue()
                        )
                        
                        for cmd in commands_list:
                            embed.add_field(
                                name=cmd["name"],
                                value=f"**Description**: {cmd['description']}\n**Example**: `{cmd['example']}`",
                                inline=False
                            )
                        
                        embed.set_footer(text="Use /help to see all categories | v0.34.0")
                        
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        found_category = True
                        break
                
                # If category not found
                if not found_category:
                    await interaction.response.send_message(
                        f"Category '{category}' not found. Use `/help` without parameters to see all categories.",
                        ephemeral=True
                    )
                return
            
            # If no category was specified, show the main help menu
            embed = discord.Embed(
                title="📚 Veramon Reunited Help",
                description="Welcome to Veramon Reunited! Here are all available command categories.\nUse `/help [category]` to see commands in a specific category.",
                color=discord.Color.blue()
            )
            
            for category in commands_by_category.keys():
                cmd_count = len(commands_by_category[category])
                embed.add_field(
                    name=f"{category} ({cmd_count})",
                    value=f"Use `/help {category.lower()}` to view",
                    inline=True
                )
            
            embed.set_footer(text="Veramon Reunited | v0.34.0")
            
            # Create view with buttons for each category
            view = discord.ui.View(timeout=180)
            
            # Add select menu for categories
            options = [
                discord.SelectOption(label=cat, description=f"View {cat} commands")
                for cat in commands_by_category.keys()
            ]
            
            select = discord.ui.Select(
                placeholder="Choose a category...",
                options=options,
                min_values=1,
                max_values=1
            )
            
            async def select_callback(interaction: discord.Interaction):
                try:
                    selected_category = select.values[0]
                    
                    category_embed = discord.Embed(
                        title=f"📚 {selected_category} Commands",
                        description=f"List of all {selected_category.lower()} commands for Veramon Reunited.",
                        color=discord.Color.blue()
                    )
                    
                    for cmd in commands_by_category[selected_category]:
                        category_embed.add_field(
                            name=cmd["name"],
                            value=f"**Description**: {cmd['description']}\n**Example**: `{cmd['example']}`",
                            inline=False
                        )
                    
                    category_embed.set_footer(text="Use /help to see all categories | v0.34.0")
                    
                    await interaction.response.edit_message(embed=category_embed, view=view)
                except Exception as e:
                    print(f"Error in help command select callback: {e}")
                    await interaction.response.send_message("An error occurred while processing your selection. Please try again.", ephemeral=True)
            
            select.callback = select_callback
            view.add_item(select)
            
            # Add a link to documentation
            docs_button = discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="📖 Documentation",
                url="https://github.com/killerdash117/veramon-reunited"
            )
            
            view.add_item(docs_button)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in help command: {e}")
            await interaction.response.send_message("An error occurred while processing the help command. Please try again later.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
