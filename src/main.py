"""
Veramon Reunited - Discord Bot
 2025 killerdash117 | https://github.com/killerdash117

This file is part of Veramon Reunited, a Discord bot created by killerdash117.
All rights reserved. See OWNERSHIP.md for usage terms.
"""

import os
import asyncio
import sys
from discord.ext import commands
from dotenv import load_dotenv
from src.utils.ui.accessibility_shortcuts import setup_shortcut_handler
import traceback
import discord
from datetime import datetime

# Veramon Reunited - Version v0.44.0
# Created by killerdash117

# Current version of the bot
VERSION = "v0.44.0"

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = commands.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_extensions():
    """Load all extension cogs."""
    # Add all extension cogs here:
    extensions = [
        # Gameplay cogs
        'src.cogs.gameplay.battle_cog',    # Enhanced battle system
        'src.cogs.gameplay.catching_cog',  # Exploration and catching system
        'src.cogs.gameplay.trading_cog',   # Trading system
        'src.cogs.gameplay.team_cog',      # Team management system
        
        # Social cogs
        'src.cogs.social.profile_cog',
        'src.cogs.social.leaderboard_cog',
        'src.cogs.social.guild_cog',
        'src.cogs.social.faction_cog',
        
        # Economy cogs
        'src.cogs.economy.economy_cog',    # Updated path to economy cog
        
        # User cogs
        'src.cogs.user.accessibility_cog', # Accessibility features
        'src.cogs.user.help_cog',          # Help command system
        
        # Admin cogs
        'src.cogs.admin.admin_cog',
        'src.cogs.admin.developer_cog',
        'src.cogs.admin.admin_game_settings',
        'src.cogs.admin.admin_battle_system',
        'src.cogs.admin.db_admin_cog',     # Database administration commands
        'src.cogs.admin.setup_cog',        # Interactive setup wizard
        
        # Other cogs
        'src.cogs.web_integration_cog',
        'src.cogs.tournament_cog',
        'src.cogs.moderator_cog',      # Moderator commands
        'src.cogs.vip_cog',            # VIP features and shop
        'src.cogs.settings_cog',       # User settings and UI themes
        'src.cogs.interactive_cog',    # Interactive UI system and DM support
        'src.cogs.quest_cog',          # Quest & Achievement system
        'src.cogs.event_cog'           # Seasonal Events system
    ]
    
    # Keep track of load status
    load_status = {
        "successful": [],
        "failed": []
    }
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"✅ Loaded extension: {extension}")
            load_status["successful"].append(extension)
        except Exception as e:
            print(f"❌ Failed to load extension {extension}: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            load_status["failed"].append((extension, str(e)))
            
            # Try to create fallback versions for critical cogs
            if any(crit in extension for crit in ["battle_cog", "help_cog", "admin_cog", "trading_cog"]):
                await create_fallback_cog(extension.split('.')[-1])
    
    # Print a summary of the loading results
    print(f"\n===== EXTENSION LOADING SUMMARY =====")
    print(f"✅ Successfully loaded: {len(load_status['successful'])}/{len(extensions)}")
    
    if load_status["failed"]:
        print(f"❌ Failed to load:")
        for ext, err in load_status["failed"]:
            print(f"  - {ext}: {err}")
    
    return load_status

async def create_fallback_cog(cog_type):
    """Create a basic fallback version of a critical cog if the main one fails to load."""
    print(f"🔄 Creating fallback version for {cog_type}...")
    
    if "battle" in cog_type:
        class FallbackBattleCog(commands.Cog):
            def __init__(self, bot):
                self.bot = bot
                
            @commands.command(name="battle")
            async def battle(self, ctx):
                await ctx.send("⚠️ Battle system is currently undergoing maintenance. Please try again later.")
                
        await bot.add_cog(FallbackBattleCog(bot))
        print(f"✅ Created fallback battle cog")
        
    elif "help" in cog_type:
        class FallbackHelpCog(commands.Cog):
            def __init__(self, bot):
                self.bot = bot
                bot.remove_command('help')  # Remove default help
                
            @commands.command(name="help")
            async def help(self, ctx):
                embed = discord.Embed(
                    title="Veramon Reunited Help",
                    description="The help system is currently in maintenance mode. Basic commands:\n!start - Begin your adventure\n!battle - Battle system\n!trade - Trading system",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                
        await bot.add_cog(FallbackHelpCog(bot))
        print(f"✅ Created fallback help cog")
        
    elif "admin" in cog_type:
        class FallbackAdminCog(commands.Cog):
            def __init__(self, bot):
                self.bot = bot
                
            @commands.command(name="admin")
            @commands.is_owner()
            async def admin(self, ctx):
                await ctx.send("Admin system is in maintenance mode. Only basic functions available.")
                
        await bot.add_cog(FallbackAdminCog(bot))
        print(f"✅ Created fallback admin cog")
        
    elif "trading" in cog_type:
        class FallbackTradingCog(commands.Cog):
            def __init__(self, bot):
                self.bot = bot
                
            @commands.command(name="trade")
            async def trade(self, ctx):
                await ctx.send("⚠️ Trading system is currently undergoing maintenance. Please try again later.")
                
        await bot.add_cog(FallbackTradingCog(bot))
        print(f"✅ Created fallback trading cog")

async def setup_database():
    """Initialize the database with required tables."""
    from src.db.db_manager import get_db_manager
    
    print("Setting up database...")
    
    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/backups", exist_ok=True)
    os.makedirs("data/quests", exist_ok=True)
    os.makedirs("data/quests/daily", exist_ok=True)
    os.makedirs("data/quests/weekly", exist_ok=True)
    os.makedirs("data/quests/story", exist_ok=True)
    os.makedirs("data/quests/achievements", exist_ok=True)
    os.makedirs("data/quests/events", exist_ok=True)
    os.makedirs("data/events", exist_ok=True)
    
    # Get the database manager and initialize all tables
    db_manager = get_db_manager()
    db_manager.initialize_database()
    
    print(f"Database setup complete. Version: {db_manager.get_db_version()}")

@bot.event
async def on_ready():
    print(f" Veramon Reunited is online as {bot.user}!")
    print("Created by Killerdash117")
    try:
        await bot.tree.sync()
        print(" Slash commands synced.")
    except Exception as e:
        print("Error syncing slash commands:", e)

@bot.event
async def on_guild_join(guild):
    """Event triggered when the bot joins a new guild (server)."""
    try:
        print(f"🚀 Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Get the owner of the server
        owner = guild.owner
        
        if owner:
            # Add the server owner as a developer automatically
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if owner is already in the developers table
            cursor.execute("SELECT * FROM developers WHERE user_id = ?", (str(owner.id),))
            existing_dev = cursor.fetchone()
            
            if not existing_dev:
                # Add the server owner as a developer
                cursor.execute(
                    "INSERT INTO developers (user_id, permission_level, added_at, added_by) VALUES (?, ?, ?, ?)",
                    (str(owner.id), "ADMIN", datetime.now().isoformat(), "SYSTEM")
                )
                conn.commit()
                print(f"✅ Added server owner {owner.name} (ID: {owner.id}) as a developer with ADMIN permissions")
                
                # Send a welcome message to the owner
                try:
                    embed = discord.Embed(
                        title="🎉 Welcome to Veramon Reunited!",
                        description=f"Hello {owner.name}, thank you for adding Veramon Reunited to your server!\n\nAs the server owner, you have been automatically granted ADMIN permissions for the bot.",
                        color=discord.Color.green()
                    )
                    
                    embed.add_field(
                        name="🛡️ Admin Commands",
                        value="You can use `/admin_help` to see all available admin commands.",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="🔧 Setup",
                        value="Use `/setup` to configure the bot for your server.",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="📚 Documentation",
                        value="Check out our [documentation](https://github.com/killerdash117/veramon-reunited) for more information.",
                        inline=False
                    )
                    
                    await owner.send(embed=embed)
                except Exception as e:
                    print(f"⚠️ Could not send welcome message to owner: {e}")
            
            conn.close()
        
        # Create a default welcome channel message
        try:
            # Find the first text channel the bot can send to
            welcome_channel = None
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    welcome_channel = channel
                    break
            
            if welcome_channel:
                embed = discord.Embed(
                    title="🎮 Veramon Reunited has joined the server!",
                    description="Hello everyone! I'm Veramon Reunited, a Discord bot that brings a monster collecting and battling experience to your server!",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Getting Started",
                    value="Type `/start` to begin your adventure!",
                    inline=False
                )
                
                embed.add_field(
                    name="Help",
                    value="Use `/help` to see all available commands.",
                    inline=False
                )
                
                await welcome_channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ Could not send welcome message to guild channel: {e}")
            
    except Exception as e:
        print(f"⚠️ Error in on_guild_join event: {e}")

async def main():
    async with bot:
        await setup_database()
        await load_extensions()
        setup_shortcut_handler(bot)  # Initialize shortcut handler with bot parameter
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
