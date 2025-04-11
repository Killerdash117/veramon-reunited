import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, sqlite3
from datetime import datetime
from src.utils.helpers import weighted_choice

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
VERAMON_FILE = os.path.join(DATA_DIR, "veramon_data.json")
VERAMON_DATA = load_json(VERAMON_FILE)

# Database configuration: SQLite connection
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "veramon.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def calculate_damage(attacker_atk, defender_def):
    base_damage = attacker_atk - (defender_def / 2)
    damage = max(1, int(base_damage * random.uniform(0.8, 1.2)))
    return damage

class BattleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="battle_wild", description="Challenge a wild Veramon in a turn-based battle.")
    async def battle_wild(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        # Retrieve player's captured Veramons from the 'captures' table
        cursor.execute("SELECT veramon_name FROM captures WHERE user_id = ?", (user_id,))
        records = cursor.fetchall()
        if not records:
            await interaction.response.send_message("You haven't caught any Veramons! Use `/explore` and `/catch` to build your team.", ephemeral=True)
            return

        # Randomly select a player's Veramon; load its detailed data
        player_choice = random.choice(records)[0]
        if player_choice not in VERAMON_DATA:
            await interaction.response.send_message("Your Veramon data is missing. Please contact an admin.", ephemeral=True)
            return

        player_veramon = VERAMON_DATA[player_choice]
        p_stats = player_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50})
        p_hp = p_stats.get("hp", 50)

        # Select a wild enemy from the global data
        enemy_veramon = random.choice(list(VERAMON_DATA.values()))
        e_stats = enemy_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50})
        e_hp = e_stats.get("hp", 50)

        battle_log = []
        battle_log.append("**Battle Start!**")
        battle_log.append(f"Your Veramon: **{player_veramon['name']}** (HP: {p_hp}, ATK: {p_stats.get('atk', 50)}, DEF: {p_stats.get('def',50)})")
        battle_log.append(f"Wild Veramon: **{enemy_veramon['name']}** (HP: {e_hp}, ATK: {e_stats.get('atk', 50)}, DEF: {e_stats.get('def',50)})")
        battle_log.append("--------")
        turn = 1

        while p_hp > 0 and e_hp > 0:
            battle_log.append(f"**Turn {turn}:**")
            if random.choice([True, False]):
                dmg = calculate_damage(p_stats.get("atk", 50), e_stats.get("def", 50))
                e_hp -= dmg
                battle_log.append(f"Your {player_veramon['name']} deals **{dmg}** damage! (Enemy HP: {max(e_hp,0)})")
            else:
                dmg = calculate_damage(e_stats.get("atk", 50), p_stats.get("def", 50))
                p_hp -= dmg
                battle_log.append(f"Wild {enemy_veramon['name']} deals **{dmg}** damage! (Your HP: {max(p_hp,0)})")
            battle_log.append("--------")
            turn += 1

        result = "**Victory!**" if p_hp > 0 else "**Defeat!**"
        battle_log.append(result)
        embed = discord.Embed(title="Wild Battle Result", description="\n".join(battle_log), color=0x3366ff)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BattleCog(bot))
