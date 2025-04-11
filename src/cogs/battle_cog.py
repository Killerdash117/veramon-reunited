import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, sqlite3
from datetime import datetime
from src.utils.helpers import weighted_choice

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

# Define paths for data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
VERAMON_FILE = os.path.join(DATA_DIR, "veramon_data.json")
# We'll reuse veramon_data for enemy selection as well.
VERAMON_DATA = load_json(VERAMON_FILE)

# Database setup for captures (to fetch player's creatures)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "veramon.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Utility: Generate a random speed for battle (simulate with random int, as a placeholder)
def get_speed():
    return random.randint(1, 100)

# Utility: Damage formula – a simple function
def calculate_damage(attacker_atk, defender_def):
    # Damage is (attacker_atk minus half of defender_def) times a random factor between 0.8 and 1.2; minimum of 1.
    base_damage = attacker_atk - (defender_def / 2)
    random_factor = random.uniform(0.8, 1.2)
    damage = max(1, int(base_damage * random_factor))
    return damage

class BattleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="battle_wild", description="Challenge a wild Veramon in a turn-based battle.")
    async def battle_wild(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        # Fetch user's captured Veramons from the 'captures' table
        cursor.execute("SELECT veramon_name FROM captures WHERE user_id = ?", (user_id,))
        records = cursor.fetchall()
        if not records:
            await interaction.response.send_message("You don't have any Veramons to battle with! Catch one first using `/explore` and `/catch`.", ephemeral=True)
            return

        # Choose a player's Veramon at random from the captures
        player_choice = random.choice(records)[0]
        if player_choice not in VERAMON_DATA:
            await interaction.response.send_message("Your captured Veramon data seems to be missing from the system.", ephemeral=True)
            return
        player_veramon = VERAMON_DATA[player_choice].copy()  # copy to avoid modifying global data
        
        # For battle simulation, assign HP, atk, def from base_stats; if missing, use defaults.
        p_stats = player_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50})
        player_hp = p_stats.get("hp", 50)
        player_atk = p_stats.get("atk", 50)
        player_def = p_stats.get("def", 50)
        player_speed = get_speed()

        # Select a wild enemy from the global Veramon data.
        enemy_veramon = random.choice(list(VERAMON_DATA.values())).copy()
        e_stats = enemy_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50})
        enemy_hp = e_stats.get("hp", 50)
        enemy_atk = e_stats.get("atk", 50)
        enemy_def = e_stats.get("def", 50)
        enemy_speed = get_speed()

        # Battle simulation log
        battle_log = []
        battle_log.append(f"**Battle Start!**")
        battle_log.append(f"Your Veramon: **{player_veramon['name']}** (HP: {player_hp}, ATK: {player_atk}, DEF: {player_def}, Speed: {player_speed})")
        battle_log.append(f"Wild Veramon: **{enemy_veramon['name']}** (HP: {enemy_hp}, ATK: {enemy_atk}, DEF: {enemy_def}, Speed: {enemy_speed})")
        battle_log.append("--------")
        
        # Determine turn order based on speed; if equal, choose randomly.
        if player_speed >= enemy_speed:
            turn_order = ["player", "enemy"]
        else:
            turn_order = ["enemy", "player"]

        # Simulate turns until one HP falls below or equal to 0
        turn = 1
        while player_hp > 0 and enemy_hp > 0:
            battle_log.append(f"**Turn {turn}:**")
            for actor in turn_order:
                if player_hp <= 0 or enemy_hp <= 0:
                    break  # battle over

                if actor == "player":
                    damage = calculate_damage(player_atk, enemy_def)
                    enemy_hp -= damage
                    battle_log.append(f"Your **{player_veramon['name']}** attacks and deals **{damage}** damage!")
                    battle_log.append(f"Wild **{enemy_veramon['name']}** HP: {max(enemy_hp, 0)}")
                else:  # enemy's turn
                    damage = calculate_damage(enemy_atk, player_def)
                    player_hp -= damage
                    battle_log.append(f"Wild **{enemy_veramon['name']}** attacks and deals **{damage}** damage!")
                    battle_log.append(f"Your **{player_veramon['name']}** HP: {max(player_hp, 0)}")
            battle_log.append("--------")
            turn += 1

        # Determine the outcome
        if player_hp > 0:
            result = f"**Victory!** Your {player_veramon['name']} wins!"
        else:
            result = f"**Defeat!** Wild {enemy_veramon['name']} wins!"

        battle_log.append(result)
        # Create an embed to display the battle log
        embed = discord.Embed(title="Wild Battle Result", description="\n".join(battle_log), color=0x3366ff)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BattleCog(bot))
