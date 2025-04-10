import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Veramon Reunited is online as {bot.user}!")

async def main():
    await bot.load_extension("cogs.catching_cog")
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
