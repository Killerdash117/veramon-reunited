import discord
from discord.ext import commands
from discord import app_commands
import json, random, os, sqlite3
from datetime import datetime
from src.utils.helpers import weighted_choice

# --- TYPE EFFECTIVENESS CHART (SAMPLE) ---
# This is a simplified type chart.
TYPE_EFFECTIVENESS = {
    "Fire": {"Water": 0.5, "Grass": 2.0, "Fire": 0.5, "Ice": 2.0, "Rock": 0.5},
    "Water": {"Fire": 2.0, "Grass": 0.5, "Water": 0.5, "Rock": 2.0, "Electric": 0.5},
    "Nature": {"Water": 2.0, "Fire": 0.5, "Nature": 0.5, "Rock": 1.0},
    # Add additional types as required.
}

def get_type_multiplier(attacker_types, defender_types):
    """Calculate the cumulative type multiplier given attacker's types and defender's types."""
    multiplier = 1.0
    for atype in attacker_types:
        for dtype in defender_types:
            multiplier *= TYPE_EFFECTIVENESS.get(atype, {}).get(dtype, 1.0)
    return multiplier

# --- DATA LOADING ---
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
VERAMON_FILE = os.path.join(DATA_DIR, "veramon_data.json")
# We assume that every Veramon in veramon_data.json includes:
# - "type": a list of types (e.g., ["Fire"] or ["Water", "Flying"])
# - "base_stats": a dict with keys "hp", "atk", "def", "sp_atk", "sp_def", "speed"
VERAMON_DATA = load_json(VERAMON_FILE)

# --- DATABASE SETUP ---
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

# --- UTILITY FUNCTIONS ---
def calculate_damage(attacker_atk, defender_def, type_multiplier=1.0, crit=1.0):
    """Calculate damage using attack and defense with a randomness factor, type multiplier, and critical multiplier."""
    base = max(1, attacker_atk - defender_def / 2)
    random_factor = random.uniform(0.8, 1.2)
    damage = int(base * random_factor * type_multiplier * crit)
    return damage

def is_critical_hit(chance=0.1):
    """Return 2.0 for a critical hit multiplier, or 1.0 normally."""
    return 2.0 if random.random() < chance else 1.0

# --- BATTLE SYSTEM COG ---
class BattleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="battle_wild", description="Challenge a wild Veramon in a turn-based battle.")
    async def battle_wild(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        # Fetch captured Veramons for the user from the database.
        cursor.execute("SELECT veramon_name FROM captures WHERE user_id = ?", (user_id,))
        records = cursor.fetchall()
        if not records:
            await interaction.response.send_message("You haven't captured any Veramons yet! Use `/explore` and `/catch` to build your team.", ephemeral=True)
            return

        # Randomly select one of the player's Veramons.
        player_choice = random.choice(records)[0]
        if player_choice not in VERAMON_DATA:
            await interaction.response.send_message("Error: Your chosen Veramon data could not be found.", ephemeral=True)
            return

        player_veramon = VERAMON_DATA[player_choice].copy()
        # Extract stats; default to some baseline values if missing.
        p_stats = player_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50, "speed": 50})
        p_hp = p_stats.get("hp", 50)
        p_atk = p_stats.get("atk", 50)
        p_def = p_stats.get("def", 50)
        p_speed = p_stats.get("speed", 50)

        # Choose a random wild enemy from the global pool.
        enemy_veramon = random.choice(list(VERAMON_DATA.values())).copy()
        e_stats = enemy_veramon.get("base_stats", {"hp": 50, "atk": 50, "def": 50, "speed": 50})
        e_hp = e_stats.get("hp", 50)
        e_atk = e_stats.get("atk", 50)
        e_def = e_stats.get("def", 50)
        e_speed = e_stats.get("speed", 50)

        # Calculate type effectiveness multiplier
        # For simplicity, we take the first type of the attacker and compare to each type of the defender.
        type_multiplier = get_type_multiplier(player_veramon.get("type", []), enemy_veramon.get("type", []))

        battle_log = []
        battle_log.append("**Battle Start!**")
        battle_log.append(f"Your Veramon: **{player_veramon['name']}** (HP: {p_hp}, ATK: {p_atk}, DEF: {p_def}, Speed: {p_speed})")
        battle_log.append(f"Wild Veramon: **{enemy_veramon['name']}** (HP: {e_hp}, ATK: {e_atk}, DEF: {e_def}, Speed: {e_speed})")
        battle_log.append("--------")
        turn = 1

        # Determine initial turn order based on speed.
        # If speeds are equal, order is decided randomly.
        if p_speed == e_speed:
            turn_order = random.sample(["player", "enemy"], k=2)
        else:
            turn_order = ["player", "enemy"] if p_speed > e_speed else ["enemy", "player"]

        # Battle loop: simulate rounds until one side's HP <= 0.
        while p_hp > 0 and e_hp > 0:
            battle_log.append(f"**Turn {turn}:**")
            for actor in turn_order:
                if p_hp <= 0 or e_hp <= 0:
                    break  # Battle has concluded

                if actor == "player":
                    # Simulate an attack; assume a basic move with no specific power value; use player's atk value.
                    crit_mult = is_critical_hit()
                    dmg = calculate_damage(p_atk, e_def, type_multiplier, crit_mult)
                    e_hp -= dmg
                    battle_log.append(f"Your {player_veramon['name']} attacks and deals **{dmg}** damage! (Enemy HP: {max(e_hp, 0)})")
                    if crit_mult > 1.0:
                        battle_log.append("**Critical hit!**")
                else:
                    # Enemy attacks with its basic move.
                    crit_mult = is_critical_hit()
                    dmg = calculate_damage(e_atk, p_def, 1.0, crit_mult)  # No type multiplier for enemy attack here
                    p_hp -= dmg
                    battle_log.append(f"Wild {enemy_veramon['name']} attacks and deals **{dmg}** damage! (Your HP: {max(p_hp, 0)})")
                    if crit_mult > 1.0:
                        battle_log.append("**Critical hit!**")
            battle_log.append("--------")
            turn += 1
            # Recalculate turn order each turn in case speed modifiers are applied (future expansion)

        # Determine final outcome
        outcome = f"**Victory!** Your {player_veramon['name']} wins!" if p_hp > 0 else f"**Defeat!** Wild {enemy_veramon['name']} wins!"
        battle_log.append(outcome)
        embed = discord.Embed(title="Wild Battle Result", description="\n".join(battle_log), color=0x3366ff)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BattleCog(bot))
