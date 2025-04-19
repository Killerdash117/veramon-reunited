import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from typing import Tuple, List, Dict, Any
from src.db.db import get_connection  # This should return an SQLite connection object

# Optional: Use a logging framework for production; for demo purposes, we'll use print.
def log(message: str) -> None:
    print(f"[ProfileCog] {message}")

def fetch_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch the profile data for a given user from the SQLite database.
    Returns a dictionary containing total captures, shiny count, and recent captures.
    """
    profile_data = {
        "total_captures": 0,
        "shiny_captures": 0,
        "recent_captures": []  # List of tuples: (veramon_name, caught_at, shiny, biome)
    }
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Total captures
        cursor.execute("SELECT COUNT(*) FROM captures WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        profile_data["total_captures"] = row[0] if row else 0

        # Shiny captures
        cursor.execute("SELECT COUNT(*) FROM captures WHERE user_id = ? AND shiny = 1", (user_id,))
        row = cursor.fetchone()
        profile_data["shiny_captures"] = row[0] if row else 0

        # Recent captures (most recent 5)
        cursor.execute("""
            SELECT veramon_name, caught_at, shiny, biome 
            FROM captures 
            WHERE user_id = ? 
            ORDER BY caught_at DESC LIMIT 5
        """, (user_id,))
        profile_data["recent_captures"] = cursor.fetchall()

    except Exception as e:
        log(f"Error in fetch_user_profile: {e}")
    finally:
        try:
            conn.close()
        except Exception as e:
            log(f"Error closing connection: {e}")
    return profile_data

def format_recent_captures(recent: List[Tuple]) -> str:
    """
    Format a list of recent captures into a user-friendly string.
    Each capture tuple should be (veramon_name, caught_at, shiny, biome).
    """
    capture_lines = []
    for veramon_name, caught_at, shiny, biome in recent:
        shiny_prefix = "✨ " if shiny else ""
        date_str = caught_at.split("T")[0]  # Display only the date portion
        capture_lines.append(f"{shiny_prefix}{veramon_name} (Caught on {date_str} in {biome})")
    return "\n".join(capture_lines) if capture_lines else "No recent captures."

class ProfileCog(commands.Cog):
    """
    ProfileCog displays the player’s profile including:
      - Total captures
      - Shiny captures
      - Recent capture history
      - Additional placeholders for achievements, challenges, tokens, and XP.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log("ProfileCog initialized.")

    @app_commands.command(name="profile", description="Display your profile with capture statistics and additional data.")
    async def profile(self, interaction: discord.Interaction) -> None:
        user_id = str(interaction.user.id)
        log(f"Fetching profile for user {user_id}")
        profile = fetch_user_profile(user_id)

        # Format recent captures.
        recent_text = format_recent_captures(profile.get("recent_captures", []))

        # Placeholders; integrate with other systems later.
        achievements = 0          # e.g., number of achievement badges earned.
        challenges_completed = 0  # e.g., number of challenges completed.
        tokens = 0                # e.g., in-game currency.
        xp = 0                    # e.g., experience points.

        # Build the embed.
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Profile",
            description="Your current stats and achievements in Veramon Reunited.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Total Captures", value=str(profile["total_captures"]), inline=True)
        embed.add_field(name="Shiny Captures", value=str(profile["shiny_captures"]), inline=True)
        embed.add_field(name="Recent Captures", value=recent_text, inline=False)
        embed.add_field(name="Achievements", value=str(achievements), inline=True)
        embed.add_field(name="Challenges Completed", value=str(challenges_completed), inline=True)
        embed.add_field(name="Tokens", value=str(tokens), inline=True)
        embed.add_field(name="XP", value=str(xp), inline=True)
        embed.set_footer(text="Keep training to become the ultimate Veramon Master!")

        try:
            await interaction.response.send_message(embed=embed)
            log("Profile sent successfully.")
        except Exception as e:
            log(f"Error sending profile embed: {e}")
            await interaction.response.send_message("An error occurred while generating your profile.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
