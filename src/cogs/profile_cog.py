import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from src.db.db import get_connection  # Assuming get_connection() is defined in src/db/db.py

class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Display your profile including capture stats and additional info.")
    async def profile(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        try:
            # Get a database connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Retrieve total number of captures.
            cursor.execute("SELECT COUNT(*) FROM captures WHERE user_id = ?", (user_id,))
            total_captures_row = cursor.fetchone()
            total_captures = total_captures_row[0] if total_captures_row else 0

            # Retrieve number of shiny captures.
            cursor.execute("SELECT COUNT(*) FROM captures WHERE user_id = ? AND shiny = 1", (user_id,))
            shiny_captures_row = cursor.fetchone()
            shiny_captures = shiny_captures_row[0] if shiny_captures_row else 0

            # Retrieve the 5 most recent captures.
            cursor.execute(
                "SELECT veramon_name, caught_at, shiny, biome FROM captures WHERE user_id = ? ORDER BY caught_at DESC LIMIT 5",
                (user_id,)
            )
            recent_captures = cursor.fetchall()
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred while fetching your profile data: {e}", ephemeral=True
            )
            return
        finally:
            conn.close()
        
        # Format recent captures for embed display.
        recent_list = []
        for veramon_name, caught_at, shiny, biome in recent_captures:
            shiny_prefix = "✨ " if shiny else ""
            date_str = caught_at.split("T")[0]  # Show only the date portion
            recent_list.append(f"{shiny_prefix}{veramon_name} (Caught on {date_str} in {biome})")
        recent_text = "\n".join(recent_list) if recent_list else "No recent captures."

        # Create the embed for the profile.
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Profile",
            color=discord.Color.gold(),
            description="Here are your capture stats and other profile information."
        )
        embed.add_field(name="Total Captures", value=str(total_captures), inline=True)
        embed.add_field(name="Shiny Captures", value=str(shiny_captures), inline=True)
        embed.add_field(name="Recent Captures", value=recent_text, inline=False)
        # Placeholders for future integration (e.g., economy, XP, etc.)
        embed.add_field(name="Tokens", value="0", inline=True)
        embed.add_field(name="XP", value="0", inline=True)
        embed.set_footer(text="Keep training to become the ultimate Veramon Master!")

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
