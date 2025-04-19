import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Dict, Any, Optional, List, Union

from src.utils.ui_theme import theme_manager, ThemeColorType, create_themed_embed
from src.utils.user_settings import get_user_settings
from src.utils.interactive_ui import InteractiveView, NavigableView, NavigationType
from src.utils.interactive_components import MainMenuView, ExplorationView, EncounterView
from src.utils.dm_handler import dm_handler
from src.models.permissions import require_permission_level, PermissionLevel, is_vip, is_admin

logger = logging.getLogger('veramon.interactive')

class InteractiveCog(commands.Cog):
    """
    Interactive command interface for Veramon Reunited.
    Provides a GUI-like experience using Discord's UI components.
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="menu", description="Open the interactive Veramon Reunited menu")
    async def menu(self, interaction: discord.Interaction):
        """
        Open the main interactive menu for Veramon Reunited.
        This serves as the hub for all bot features through buttons.
        """
        # Check if user is allowed to use this in DMs
        if isinstance(interaction.channel, discord.DMChannel):
            allowed = await dm_handler.is_dm_allowed(interaction, "menu")
            if not allowed:
                await interaction.response.send_message(
                    "This command cannot be used in DMs unless you are a VIP or Admin.",
                    ephemeral=True
                )
                return
                
        # Create and send the main menu
        user_id = str(interaction.user.id)
        
        # Create embed for the main menu
        embed = create_themed_embed(
            user_id,
            title="🌟 Veramon Reunited Interactive Menu",
            description="Welcome to Veramon Reunited! Click the buttons below to navigate.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add some helpful information
        embed.add_field(
            name="🎮 Interactive Controls",
            value="Use the buttons below to access different features without typing commands!",
            inline=False
        )
        
        # Add quick stats if available
        # In a real implementation, this would fetch from the database
        embed.add_field(
            name="📊 Your Stats",
            value="Veramon Caught: 0\nBattle Record: 0W-0L\nTokens: 0",
            inline=True
        )
        
        embed.add_field(
            name="📅 Daily Rewards",
            value="Daily Rewards: Available Now!\nStreak: 0 days",
            inline=True
        )
        
        # Create a note about DM mode for VIP/Admin users
        if await is_vip().predicate(interaction):
            # User is VIP or higher, inform about DM capabilities
            embed.set_footer(text="✨ VIP Feature: You can use /menu in DMs for private access!")
        
        # Create main menu view
        view = MainMenuView(
            user_id=user_id, 
            allow_dm=isinstance(interaction.channel, discord.DMChannel)
        )
        
        # Send the menu
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @app_commands.command(name="battle_menu", description="Open the interactive battle menu")
    async def battle_menu(self, interaction: discord.Interaction):
        """
        Open the interactive battle menu for easy battle management.
        Integrates with the enhanced battle system.
        """
        # Check for DM permission
        if isinstance(interaction.channel, discord.DMChannel):
            allowed = await dm_handler.is_dm_allowed(interaction, "battle_menu")
            if not allowed:
                await interaction.response.send_message(
                    "This command cannot be used in DMs unless you are a VIP or Admin.",
                    ephemeral=True
                )
                return
                
        user_id = str(interaction.user.id)
        
        # Create embed for battle menu
        embed = create_themed_embed(
            user_id,
            title="⚔️ Battle System",
            description="Challenge trainers and other players to test your skill!",
            color_type=ThemeColorType.DANGER
        )
        
        embed.add_field(
            name="🤖 PvE Battles",
            value="Battle against AI trainers of varying difficulty",
            inline=True
        )
        
        embed.add_field(
            name="👥 PvP Battles",
            value="Challenge other players to prove your strength",
            inline=True
        )
        
        embed.add_field(
            name="👥👥 Multi Battles",
            value="Team up or battle in groups of up to 4 players",
            inline=True
        )
        
        # Create Battle Menu view (this would be fully implemented to integrate
        # with the existing battle system from the memory)
        view = InteractiveView(user_id=user_id)
        
        # PvE Battle Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="PvE Battle",
            emoji="🤖",
            custom_id="pve_battle_button",
            row=0
        ))
        
        # PvP Battle Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="PvP Battle",
            emoji="👥",
            custom_id="pvp_battle_button",
            row=0
        ))
        
        # Multi Battle Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Multi Battle",
            emoji="👥👥",
            custom_id="multi_battle_button",
            row=0
        ))
        
        # Battle History Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Battle History",
            emoji="📜",
            custom_id="battle_history_button",
            row=1
        ))
        
        # Battle Teams Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Manage Teams",
            emoji="📋",
            custom_id="battle_teams_button",
            row=1
        ))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @app_commands.command(name="trade_menu", description="Open the interactive trading menu")
    async def trade_menu(self, interaction: discord.Interaction):
        """
        Open the interactive trading menu for easy trade management.
        Integrates with the existing trading system.
        """
        # Check for DM permission
        if isinstance(interaction.channel, discord.DMChannel):
            allowed = await dm_handler.is_dm_allowed(interaction, "trade_menu")
            if not allowed:
                await interaction.response.send_message(
                    "This command cannot be used in DMs unless you are a VIP or Admin.",
                    ephemeral=True
                )
                return
                
        user_id = str(interaction.user.id)
        
        # Create embed for trade menu
        embed = create_themed_embed(
            user_id,
            title="🔄 Trading System",
            description="Exchange Veramon with other players safely and easily!",
            color_type=ThemeColorType.ACCENT
        )
        
        embed.add_field(
            name="📤 Create Trade",
            value="Start a new trade with another player",
            inline=True
        )
        
        embed.add_field(
            name="📋 Active Trades",
            value="View and manage your current trades",
            inline=True
        )
        
        embed.add_field(
            name="📜 Trade History",
            value="View your past trades",
            inline=True
        )
        
        # Create Trading Menu view (integrates with the existing trading system from memory)
        view = InteractiveView(user_id=user_id)
        
        # Create Trade Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Create Trade",
            emoji="📤",
            custom_id="create_trade_button",
            row=0
        ))
        
        # Active Trades Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Active Trades",
            emoji="📋",
            custom_id="active_trades_button",
            row=0
        ))
        
        # Trade History Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Trade History",
            emoji="📜",
            custom_id="trade_history_button",
            row=0
        ))
        
        # Trade Guide Button
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Trading Guide",
            emoji="❓",
            custom_id="trade_guide_button",
            row=1
        ))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @app_commands.command(name="dm_mode", description="Enable or disable DM mode (VIP+ only)")
    @require_permission_level(PermissionLevel.VIP)
    async def dm_mode(self, interaction: discord.Interaction, enable: bool = True):
        """
        Enable or disable DM mode for VIP and Admin users.
        This allows them to interact with the bot in Direct Messages.
        """
        user_id = str(interaction.user.id)
        
        if enable:
            # Start a DM session
            success = await dm_handler.start_dm_session(user_id)
            
            if success:
                # Send a DM to the user
                embed = create_themed_embed(
                    user_id,
                    title="✨ DM Mode Enabled",
                    description="You can now use Veramon Reunited commands in DMs!",
                    color_type=ThemeColorType.SUCCESS
                )
                
                embed.add_field(
                    name="Available Commands",
                    value="Use `/menu` in DMs to access the interactive interface!\n"
                          "You can also use many other commands directly in DMs.",
                    inline=False
                )
                
                await dm_handler.send_dm(user_id, embed=embed)
                
                # Respond in the channel
                await interaction.response.send_message(
                    "✅ DM Mode enabled! Check your Direct Messages for more information.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "DM Mode is already enabled. Check your Direct Messages!",
                    ephemeral=True
                )
        else:
            # End the DM session
            success = dm_handler.end_dm_session(user_id)
            
            if success:
                await interaction.response.send_message(
                    "✅ DM Mode disabled. You will no longer receive DMs from the bot.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "DM Mode was not active.",
                    ephemeral=True
                )

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command):
        """
        Listen for command completions to handle DM mode and other interactive features.
        This helps facilitate seamless DM interactions for VIP+ users.
        """
        # If this is a DM and the command was successful, update session
        if isinstance(interaction.channel, discord.DMChannel):
            user_id = str(interaction.user.id)
            
            # Make sure we have an active session
            context = dm_handler.get_session_context(user_id)
            if context is not None:
                # Update the last command
                dm_handler.update_session_context(user_id, {
                    "last_command": command.name,
                    "last_command_time": discord.utils.utcnow().isoformat()
                })

async def setup(bot):
    """Add the InteractiveCog to the bot."""
    await bot.add_cog(InteractiveCog(bot))
    
    # Initialize the DM handler
    from src.utils.dm_handler import setup_dm_handler
    setup_dm_handler(bot)
