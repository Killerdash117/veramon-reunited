
import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os

VERAMON_FILE = "data/veramon_data.json"
BIOMES_FILE = "data/biomes.json"
active_encounters = {}

def load_veramons():
    with open(VERAMON_FILE) as f:
        return json.load(f)

def load_biomes():
    with open(BIOMES_FILE) as f:
        return json.load(f)

class Catching(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="explore", description="Explore a biome and encounter a wild Veramon.")
    @app_commands.describe(biome="The biome to explore (e.g., forest)")
    async def explore(self, interaction: discord.Interaction, biome: str):
        biomes = load_biomes()
        if biome not in biomes:
            await interaction.response.send_message("Invalid biome. Use one of: " + ", ".join(biomes.keys()), ephemeral=True)
            return

        veramons = load_veramons()
        spawn_pool = []
        for rarity, names in biomes[biome]["spawn_table"].items():
            for name in names:
                spawn_pool.append(veramons[name])

        wild = random.choice(spawn_pool)
        shiny = random.random() < 0.0005
        wild["shiny"] = shiny

        display_name = f"✨ Shiny {wild['name']} ✨" if shiny else wild["name"]
        type_str = "/".join(wild["type"])
        rarity = wild["rarity"].capitalize()
        flavor = wild.get("flavor", "")

        embed = discord.Embed(title="🌿 Wild Veramon Encountered!", color=0x88ff88)
        embed.add_field(name="Name", value=display_name, inline=True)
        embed.add_field(name="Type", value=type_str, inline=True)
        embed.add_field(name="Rarity", value=rarity, inline=True)
        embed.add_field(name="Catch Rate", value=f"{int(wild['catch_rate']*100)}%", inline=True)
        embed.set_footer(text=flavor)

        active_encounters[interaction.user.id] = wild
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="catch", description="Try to catch the Veramon you encountered.")
    async def catch(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid not in active_encounters:
            await interaction.response.send_message("❌ You haven’t encountered a Veramon yet. Use `/explore` first.", ephemeral=True)
            return

        veramon = active_encounters.pop(uid)
        success = random.random() < veramon["catch_rate"]
        name_display = f"✨ Shiny {veramon['name']} ✨" if veramon.get("shiny") else veramon["name"]

        if success:
            await interaction.response.send_message(f"✅ You successfully caught **{name_display}**!")
            # Save to database/inventory in future
        else:
            await interaction.response.send_message(f"❌ The **{name_display}** escaped!")

async def setup(bot):
    await bot.add_cog(Catching(bot))
