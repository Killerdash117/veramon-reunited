import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from typing import Tuple, List, Dict, Any, Optional
from src.db.db import get_connection  # This should return an SQLite connection object
from src.models.permissions import require_permission_level, PermissionLevel
from src.core.security_integration import get_security_integration
from datetime import datetime, timedelta

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
        "recent_captures": [],  # List of tuples: (veramon_name, caught_at, shiny, biome)
        "tokens": 0,
        "xp": 0,
        "battle_wins": 0,
        "battle_losses": 0,
        "trades_completed": 0,
        "achievements": [],
        "collection_completion": 0
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
        
        # Get user tokens and XP
        cursor.execute("SELECT tokens, xp FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        if user_row:
            profile_data["tokens"] = user_row[0]
            profile_data["xp"] = user_row[1]
            
        # Get battle stats
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN winner_id = ? THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN (participant1_id = ? OR participant2_id = ?) AND winner_id != ? THEN 1 ELSE 0 END) as losses
            FROM battles
            WHERE participant1_id = ? OR participant2_id = ?
        """, (user_id, user_id, user_id, user_id, user_id, user_id))
        battle_row = cursor.fetchone()
        if battle_row:
            profile_data["battle_wins"] = battle_row[0] or 0
            profile_data["battle_losses"] = battle_row[1] or 0
            
        # Get trade statistics
        cursor.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) AND status = 'completed'
        """, (user_id, user_id))
        trade_row = cursor.fetchone()
        profile_data["trades_completed"] = trade_row[0] if trade_row else 0
        
        # Calculate collection completion (based on total unique Veramon caught vs total available)
        cursor.execute("""
            SELECT COUNT(DISTINCT veramon_name) FROM captures WHERE user_id = ?
        """, (user_id,))
        unique_captures = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM veramon_data")
        total_veramon = cursor.fetchone()[0] or 1  # Avoid division by zero
        
        profile_data["collection_completion"] = round((unique_captures / total_veramon) * 100, 1)

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
    ProfileCog displays the player's profile including:
      - Total captures
      - Shiny captures
      - Recent capture history
      - Additional placeholders for achievements, challenges, tokens, and XP.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log("ProfileCog initialized.")

    @app_commands.command(name="profile", description="View your or another player's profile")
    @app_commands.describe(user="The user whose profile to view (leave empty to view your own)")
    @require_permission_level(PermissionLevel.USER)
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        target_user = user or interaction.user
        user_id = str(interaction.user.id)
        target_id = str(target_user.id)
        
        # Security validation when viewing another user's profile
        if user and user != interaction.user:
            security = get_security_integration()
            validation_result = await security.validate_profile_view(user_id, target_id)
            if not validation_result["valid"]:
                await interaction.response.send_message(validation_result["error"], ephemeral=True)
                return
                
        log(f"Fetching profile for user {target_id}")
        profile = fetch_user_profile(target_id)

        # Format recent captures.
        recent_text = format_recent_captures(profile.get("recent_captures", []))

        # Battle record calculation
        total_battles = profile["battle_wins"] + profile["battle_losses"]
        win_rate = (profile["battle_wins"] / total_battles * 100) if total_battles > 0 else 0
        battle_record = f"{profile['battle_wins']}W - {profile['battle_losses']}L ({win_rate:.1f}% win rate)"

        # Build the embed.
        embed = discord.Embed(
            title=f"{target_user.display_name}'s Profile",
            description="Stats and achievements in Veramon Reunited.",
            color=discord.Color.gold()
        )
        
        # Add user avatar if available
        if target_user.avatar:
            embed.set_thumbnail(url=target_user.avatar.url)
            
        # Collection stats
        embed.add_field(name="Collection", value=f"{profile['collection_completion']}% complete", inline=True)
        embed.add_field(name="Total Captures", value=str(profile["total_captures"]), inline=True)
        embed.add_field(name="Shiny Captures", value=str(profile["shiny_captures"]), inline=True)
        
        # Battle & Economy stats
        embed.add_field(name="Battle Record", value=battle_record, inline=True)
        embed.add_field(name="Trades Completed", value=str(profile["trades_completed"]), inline=True)
        embed.add_field(name="Tokens", value=f"{profile['tokens']:,}", inline=True)
        
        # XP Progress
        current_level = profile["xp"] // 1000  # For example, 1 level per 1000 XP
        xp_to_next = ((current_level + 1) * 1000) - profile["xp"]
        embed.add_field(
            name=f"Level {current_level}", 
            value=f"XP: {profile['xp']:,} (Need {xp_to_next:,} for next level)", 
            inline=False
        )
        
        # Recent activity
        embed.add_field(name="Recent Captures", value=recent_text, inline=False)
        
        embed.set_footer(text="Keep training to become the ultimate Veramon Master!")

        try:
            await interaction.response.send_message(embed=embed)
            log("Profile sent successfully.")
        except Exception as e:
            log(f"Error sending profile embed: {e}")
            await interaction.response.send_message("An error occurred while generating the profile.", ephemeral=True)
            
    @app_commands.command(name="leaderboard", description="View game leaderboards")
    @app_commands.describe(
        category="The leaderboard category to view",
        timeframe="The timeframe for the leaderboard"
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Tokens", value="tokens"),
            app_commands.Choice(name="Collection", value="collection"),
            app_commands.Choice(name="Battle Wins", value="battles"),
            app_commands.Choice(name="Shinies", value="shinies"),
            app_commands.Choice(name="Trades", value="trades")
        ],
        timeframe=[
            app_commands.Choice(name="All Time", value="all"),
            app_commands.Choice(name="This Month", value="month"),
            app_commands.Choice(name="This Week", value="week")
        ]
    )
    @require_permission_level(PermissionLevel.USER)
    async def leaderboard(self, interaction: discord.Interaction, category: str, timeframe: str = "all"):
        """View leaderboards for different game statistics."""
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        
        # Security validation for leaderboard viewing
        security = get_security_integration()
        validation_result = await security.validate_leaderboard_view(user_id, category, timeframe)
        if not validation_result["valid"]:
            await interaction.followup.send(validation_result["error"], ephemeral=True)
            return
            
        # Calculate date filters based on timeframe
        date_filter = ""
        if timeframe == "week":
            one_week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            date_filter = f" AND caught_at >= '{one_week_ago}'"
        elif timeframe == "month":
            one_month_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
            date_filter = f" AND caught_at >= '{one_month_ago}'"
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch leaderboard data based on category
        leaders = []
        try:
            if category == "tokens":
                cursor.execute("""
                    SELECT user_id, tokens FROM users
                    ORDER BY tokens DESC LIMIT 10
                """)
                leaders = [(row[0], row[1], None) for row in cursor.fetchall()]
                
            elif category == "collection":
                cursor.execute("""
                    SELECT user_id, COUNT(DISTINCT veramon_name) as unique_count, 
                           (SELECT COUNT(*) FROM veramon_data) as total
                    FROM captures
                    GROUP BY user_id
                    ORDER BY unique_count DESC
                    LIMIT 10
                """)
                leaders = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
                
            elif category == "battles":
                cursor.execute("""
                    SELECT winner_id, COUNT(*) as wins
                    FROM battles
                    GROUP BY winner_id
                    ORDER BY wins DESC
                    LIMIT 10
                """)
                leaders = [(row[0], row[1], None) for row in cursor.fetchall()]
                
            elif category == "shinies":
                cursor.execute(f"""
                    SELECT user_id, COUNT(*) as shiny_count
                    FROM captures
                    WHERE shiny = 1{date_filter}
                    GROUP BY user_id
                    ORDER BY shiny_count DESC
                    LIMIT 10
                """)
                leaders = [(row[0], row[1], None) for row in cursor.fetchall()]
                
            elif category == "trades":
                cursor.execute("""
                    SELECT initiator_id, COUNT(*) as trade_count
                    FROM trades
                    WHERE status = 'completed'
                    GROUP BY initiator_id
                    ORDER BY trade_count DESC
                    LIMIT 10
                """)
                # Also count trades as recipient
                recipient_counts = {}
                cursor.execute("""
                    SELECT recipient_id, COUNT(*) as trade_count
                    FROM trades
                    WHERE status = 'completed'
                    GROUP BY recipient_id
                """)
                for row in cursor.fetchall():
                    recipient_counts[row[0]] = row[1]
                    
                # Combine initiator and recipient counts
                combined_leaders = {}
                for user_id, count, _ in leaders:
                    combined_leaders[user_id] = count
                    
                for user_id, count in recipient_counts.items():
                    if user_id in combined_leaders:
                        combined_leaders[user_id] += count
                    else:
                        combined_leaders[user_id] = count
                        
                # Convert back to list and sort
                leaders = [(user_id, count, None) for user_id, count in 
                           sorted(combined_leaders.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        except Exception as e:
            log(f"Error fetching leaderboard data: {e}")
            await interaction.followup.send(
                "An error occurred while generating the leaderboard.", 
                ephemeral=True
            )
            conn.close()
            return
            
        # Format the leaderboard embed
        title_mapping = {
            "tokens": "Top Token Holders",
            "collection": "Top Collectors",
            "battles": "Top Battle Winners",
            "shinies": "Top Shiny Hunters",
            "trades": "Most Active Traders"
        }
        
        timeframe_text = {
            "all": "All Time",
            "month": "This Month",
            "week": "This Week"
        }
        
        embed = discord.Embed(
            title=f"Leaderboard: {title_mapping.get(category, category.title())}",
            description=f"Showing top players ({timeframe_text.get(timeframe, 'All Time')})",
            color=discord.Color.blue()
        )
        
        # Add leaderboard entries
        if not leaders:
            embed.add_field(name="No data", value="No players found for this category.", inline=False)
        else:
            value_format = {
                "tokens": lambda x: f"{x:,} tokens",
                "collection": lambda x, total: f"{x}/{total} Veramon ({(x/total*100):.1f}%)",
                "battles": lambda x: f"{x} wins",
                "shinies": lambda x: f"{x} shinies",
                "trades": lambda x: f"{x} trades"
            }
            
            leaderboard_text = ""
            for i, (leader_id, value, total) in enumerate(leaders, 1):
                try:
                    # Get the Discord user name
                    member = await interaction.guild.fetch_member(int(leader_id))
                    name = member.display_name if member else f"User {leader_id}"
                    
                    # Format the value based on category
                    if category == "collection" and total:
                        formatted_value = value_format[category](value, total)
                    else:
                        formatted_value = value_format.get(category, lambda x: str(x))(value)
                        
                    leaderboard_text += f"{i}. **{name}**: {formatted_value}\n"
                except Exception as e:
                    log(f"Error formatting leaderboard entry: {e}")
                    leaderboard_text += f"{i}. **Unknown User**: {value}\n"
            
            embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
            
        conn.close()
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
