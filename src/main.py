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

# Veramon Reunited - Version v0.34.0
# Created by killerdash117

# Current version of the bot
VERSION = "v0.34.0"

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
        'cogs.gameplay.battle_cog',    # Enhanced battle system
        'cogs.gameplay.catching_cog',  # Exploration and catching system
        'cogs.gameplay.trading_cog',   # Trading system
        'cogs.gameplay.team_cog',      # Team management system
        
        # Social cogs
        'cogs.social.profile_cog',
        'cogs.social.leaderboard_cog',
        'cogs.social.guild_cog',
        'cogs.social.faction_cog',
        
        # Economy cogs
        'cogs.economy.economy_cog',    # Updated path to economy cog
        
        # User cogs
        'cogs.user.accessibility_cog', # Accessibility features
        'cogs.user.help_cog',          # Help command system
        
        # Admin cogs
        'cogs.admin.admin_cog',
        'cogs.admin.developer_cog',
        'cogs.admin.admin_game_settings',
        'cogs.admin.admin_battle_system',
        'cogs.admin.db_admin_cog',     # Database administration commands
        'cogs.admin.setup_cog',        # Interactive setup wizard
        
        # Other cogs
        'cogs.web_integration_cog',
        'cogs.tournament_cog',
        'cogs.moderator_cog',      # Moderator commands
        'cogs.vip_cog',            # VIP features and shop
        'cogs.settings_cog',       # User settings and UI themes
        'cogs.interactive_cog',    # Interactive UI system and DM support
        'cogs.quest_cog',          # Quest & Achievement system
        'cogs.event_cog'           # Seasonal Events system
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

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

async def main():
    async with bot:
        await setup_database()
        await load_extensions()
        setup_shortcut_handler(bot)  # Initialize shortcut handler with bot parameter
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
