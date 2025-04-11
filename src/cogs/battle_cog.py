import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, sqlite3
from datetime import datetime
from src.utils.helpers import weighted_choice

# --- Type Effectiveness Chart (Sample) ---
# You can expand this chart to include all relevant types.
TYPE_EFFECTIVENESS = {
    "Fire": {"Water": 0.5, "Grass": 2.0, "Fire": 0.5, "Rock": 0.5},
    "Water": {"Fire": 2.0, "Grass": 0.5, "Water": 0.5, "Electric": 0.5},
    "Nature": {"Water": 2.0, "Fire": 0.5, "Nature": 0.5},
    # Extend with additional types as needed.
}

def get_type_multiplier(attacker_types, defender_types):
    multiplier = 1.0
    for atype in attacker_types:
        for dtype in defender_types:
            multiplier *= TYPE_EFFECTIVENESS.get(atype, {}).get(dtype, 1.0)
    return multiplier

# --- Data Loading ---
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
VERAMON_FILE = os.path.join(DATA_DIR, "veramon_data.json")
VERAMON_DATA = load_json(VERAMON_FILE)  # Ensure each creature has "base_stats" with keys: hp, atk, def, speed.
# Note: For battle purposes, you can later differentiate between physical and special stats.
 
# --- Database Setup ---
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "veramon.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    veramon_name TEXT NOT NULL,
    caught_at TEXT NOT NULL,
    shiny INTEGER NOT NULL,
    biome TEXT NOT NULL
)
""")
conn.commit()

# --- Helper Functions for Battle ---
def calculate_damage(attacker_atk, defender_def, type_multiplier=1.0, crit_mult=1.0, accuracy=0.9):
    """
    Calculate damage using:
    - Base damage formula: (Attacker ATK - Defender DEF/2)
    - Random factor between 0.8 and 1.2
    - Type multiplier
    - Critical hit multiplier
    - Accuracy factor (chance to hit)
    Returns damage (minimum 0) and whether the attack hit.
    """
    if random.random() > accuracy:
        return 0, False  # Missed attack
    base_damage = max(1, attacker_atk - (defender_def / 2))
    random_factor = random.uniform(0.8, 1.2)
    damage = int(base_damage * random_factor * type_multiplier * crit_mult)
    return damage, True

def is_critical_hit(chance=0.1):
    """Return the critical multiplier (2.0 if critical, otherwise 1.0)."""
    return 2.0 if random.random() < chance else 1.0

def decide_turn_order(player_speed, enemy_speed):
    """Determine turn order based on speed; if equal, decide randomly."""
    if player_speed == enemy_speed:
        return random.sample(["player", "enemy"], 2)
    return ["player", "enemy"] if player_speed > enemy_speed else ["enemy", "player"]

# --- Battle System Cog ---
class BattleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="battle_wild", description="Challenge a wild Veramon in an advanced turn-based battle.")
    async def battle_wild(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Fetch the player's captured Veramons from the database.
        cursor.execute("SELECT veramon_name FROM captures WHERE user_id = ?", (user_id,))
        records = cursor.fetchall()
        if not records:
            await interaction.response.send_message("You haven't captured any Veramons yet! Use `/explore` and `/catch` first.", ephemeral=True)
            return

        # Randomly select a player's creature.
        player_choice = random.choice(records)[0]
        if player_choice not in VERAMON_DATA:
            await interaction.response.send_message("Error: Your captured Veramon is missing from global data.", ephemeral=True)
            return

        player_veramon = VERAMON_DATA[player_choice].copy()
        # Extract battle stats; if any stat is missing, use defaults.
        p_stats = player_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50, "speed": 50})
        p_hp = p_stats.get("hp", 50)
        p_atk = p_stats.get("atk", 50)
        p_def = p_stats.get("def", 50)
        p_speed = p_stats.get("speed", 50)

        # For a wild enemy, randomly select any Veramon from global data.
        enemy_veramon = random.choice(list(VERAMON_DATA.values())).copy()
        e_stats = enemy_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50, "speed": 50})
        e_hp = e_stats.get("hp", 50)
        e_atk = e_stats.get("atk", 50)
        e_def = e_stats.get("def", 50)
        e_speed = e_stats.get("speed", 50)

        # Calculate type multiplier: player's creature attacking enemy.
        player_types = player_veramon.get("type", [])
        enemy_types = enemy_veramon.get("type", [])
        type_multiplier = get_type_multiplier(player_types, enemy_types)

        # Create battle log.
        battle_log = []
        battle_log.append("**Battle Start!**")
        battle_log.append(f"Your Veramon: **{player_veramon['name']}** | HP: {p_hp} | ATK: {p_atk} | DEF: {p_def} | Speed: {p_speed}")
        battle_log.append(f"Wild Veramon: **{enemy_veramon['name']}** | HP: {e_hp} | ATK: {e_atk} | DEF: {e_def} | Speed: {e_speed}")
        battle_log.append("--------")

        # Determine initial turn order.
        turn_order = decide_turn_order(p_speed, e_speed)
        battle_log.append(f"Turn Order: {turn_order[0]} goes first.")

        turn = 1
        while p_hp > 0 and e_hp > 0:
            battle_log.append(f"**Turn {turn}:**")
            for actor in turn_order:
                if p_hp <= 0 or e_hp <= 0:
                    break

                if actor == "player":
                    crit_mult = is_critical_hit()
                    damage, hit = calculate_damage(p_atk, e_def, type_multiplier, crit_mult, accuracy=0.95)
                    if not hit:
                        battle_log.append(f"Your {player_veramon['name']} missed the attack!")
                    else:
                        e_hp -= damage
                        battle_log.append(f"Your {player_veramon['name']} attacks and deals **{damage}** damage! (Enemy HP: {max(e_hp, 0)})")
                        if crit_mult > 1.0:
                            battle_log.append("**Critical hit!**")
                else:
                    crit_mult = is_critical_hit()
                    damage, hit = calculate_damage(e_atk, p_def, 1.0, crit_mult, accuracy=0.9)
                    if not hit:
                        battle_log.append(f"Wild {enemy_veramon['name']} missed the attack!")
                    else:
                        p_hp -= damage
                        battle_log.append(f"Wild {enemy_veramon['name']} attacks and deals **{damage}** damage! (Your HP: {max(p_hp, 0)})")
                        if crit_mult > 1.0:
                            battle_log.append("**Critical hit!**")
            battle_log.append("--------")
            turn += 1
            # Optionally, re-calculate turn order per turn if abilities modify speed.

        if p_hp > 0:
            outcome = f"**Victory!** Your {player_veramon['name']} wins!"
        else:
            outcome = f"**Defeat!** Wild {enemy_veramon['name']} wins!"
        battle_log.append(outcome)

        embed = discord.Embed(title="Wild Battle Result", description="\n".join(battle_log), color=0x3366ff)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BattleCog(bot))
