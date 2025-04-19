import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Veramon Reunited - Version v0.25
# Created by Killerdash117

# Current version of the bot
VERSION = "v0.25"

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
        'cogs.enhanced_battle_cog',
        'cogs.economy_cog',
        'cogs.profile_cog',
        'cogs.faction_cog',
        'cogs.trading_cog',
        'cogs.guild_cog',
        'cogs.web_integration_cog',
        'cogs.admin_cog',
        'cogs.admin_game_settings',
        'cogs.admin_battle_system',
        'cogs.leaderboard_cog',
        'cogs.tournament_cog',
        'cogs.moderator_cog',   # Moderator commands
        'cogs.developer_cog',   # Developer commands
        'cogs.vip_cog',         # VIP features and shop
        'cogs.settings_cog'     # User settings and UI themes
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

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
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
