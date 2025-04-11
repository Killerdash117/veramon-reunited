async def load_extensions():
    await bot.load_extension("cogs.catching_cog")
    await bot.load_extension("cogs.battle_cog")  # Load the battle system cog
    # Future modules: factions, profiles, etc.
