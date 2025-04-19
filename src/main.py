import os
import asyncio
import sys
from discord.ext import commands
from dotenv import load_dotenv

# Veramon Reunited - Version v0.31
# Created by Killerdash117

# Current version of the bot
VERSION = "v0.31"

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
        'cogs.gameplay.battle_cog',  # Enhanced battle system
        'cogs.gameplay.catching_cog', # Exploration and catching system
        'cogs.gameplay.trading_cog',  # Trading system
        
        # Social cogs
        'cogs.social.profile_cog',
        'cogs.social.leaderboard_cog',
        'cogs.social.guild_cog',
        'cogs.social.faction_cog',
        
        # Admin cogs
        'cogs.admin.admin_cog',
        'cogs.admin.developer_cog',
        'cogs.admin.admin_game_settings',
        'cogs.admin.admin_battle_system',
        
        # Other cogs
        'cogs.economy_cog',
        'cogs.web_integration_cog',
        'cogs.tournament_cog',
        'cogs.moderator_cog',   # Moderator commands
        'cogs.vip_cog',         # VIP features and shop
        'cogs.settings_cog',    # User settings and UI themes
        'cogs.interactive_cog',  # Interactive UI system and DM support
        'cogs.quest_cog',       # Quest & Achievement system
        'cogs.event_cog'        # Seasonal Events system
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

async def setup_database():
    """Initialize the database with required tables."""
    db = Database()
    
    # Create database directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/quests", exist_ok=True)
    os.makedirs("data/quests/daily", exist_ok=True)
    os.makedirs("data/quests/weekly", exist_ok=True)
    os.makedirs("data/quests/story", exist_ok=True)
    os.makedirs("data/quests/achievements", exist_ok=True)
    os.makedirs("data/quests/events", exist_ok=True)
    os.makedirs("data/events", exist_ok=True)
    
    # Ensure all required tables exist
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            tokens INTEGER DEFAULT 0,
            last_daily_claim REAL DEFAULT 0,
            daily_streak INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            settings TEXT
        )
    """)
    
    # Other existing tables...
    
    # Quest system tables
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_quests (
            user_id TEXT PRIMARY KEY,
            quest_data TEXT NOT NULL,
            last_updated REAL DEFAULT (strftime('%s', 'now'))
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (
            user_id TEXT,
            badge_id TEXT,
            earned_at REAL,
            PRIMARY KEY (user_id, badge_id)
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_titles (
            user_id TEXT,
            title_id TEXT,
            is_active INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, title_id)
        )
    """)
    
    # Event system tables
    await db.execute("""
        CREATE TABLE IF NOT EXISTS event_reminders (
            user_id TEXT,
            event_id TEXT,
            remind_at REAL,
            reminded INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, event_id)
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS event_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            event_id TEXT,
            item_id TEXT,
            quantity INTEGER,
            price INTEGER,
            purchased_at REAL
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS event_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            event_id TEXT,
            contribution INTEGER,
            contribution_type TEXT,
            contributed_at REAL
        )
    """)
    
    # Create indices for improved performance
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_user_id ON user_quests(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_event_reminders_remind_at ON event_reminders(remind_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_event_contributions_event_id ON event_contributions(event_id)")
    
    logger.info("Database initialized")

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
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
