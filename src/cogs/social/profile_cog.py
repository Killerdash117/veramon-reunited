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
        
    @app_commands.command(name="profile", description="View your trainer profile or another player's")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Display the user's profile with Veramon stats, achievements, and more."""
        if user is None:
            user = interaction.user
            
        await interaction.response.defer(ephemeral=False)
        
        profile_data = fetch_user_profile(str(user.id))
        
        # Create a rich profile card
        embed = discord.Embed(
            title=f"🏆 Trainer Profile: {user.display_name}",
            description=f"A level {self._calculate_level(profile_data['xp'])} trainer on their Veramon journey!",
            color=self._get_profile_color(profile_data)
        )
        
        # Add user avatar if available
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
            
        # Add joined date
        member_since = discord.utils.format_dt(user.created_at, style='R')
        embed.set_footer(text=f"Trainer since {member_since}")
        
        # Progress to next level
        current_level = self._calculate_level(profile_data['xp'])
        next_level_xp = self._calculate_xp_for_level(current_level + 1)
        current_level_xp = self._calculate_xp_for_level(current_level)
        xp_progress = profile_data['xp'] - current_level_xp
        xp_needed = next_level_xp - current_level_xp
        progress_percent = min(100, int((xp_progress / max(1, xp_needed)) * 100))
        
        # Create XP progress bar
        progress_bar = self._create_progress_bar(progress_percent)
        
        # Collection completion progress bar
        collection_bar = self._create_progress_bar(profile_data['collection_completion'])
        
        # Add trainer stats
        embed.add_field(
            name="⭐ Trainer Stats",
            value=(
                f"**Level:** {current_level} {progress_bar} {progress_percent}%\n"
                f"**XP:** {profile_data['xp']:,}/{next_level_xp:,}\n"
                f"**Tokens:** {profile_data['tokens']:,} 🪙\n"
                f"**Collection:** {collection_bar} {profile_data['collection_completion']}%"
            ),
            inline=False
        )
        
        # Add battle stats
        total_battles = profile_data['battle_wins'] + profile_data['battle_losses']
        win_rate = (profile_data['battle_wins'] / max(1, total_battles)) * 100
        
        embed.add_field(
            name="⚔️ Battle Record",
            value=(
                f"**Wins:** {profile_data['battle_wins']} | **Losses:** {profile_data['battle_losses']}\n"
                f"**Win Rate:** {win_rate:.1f}%\n"
                f"**Trades:** {profile_data['trades_completed']} completed"
            ),
            inline=True
        )
        
        # Add Veramon stats
        embed.add_field(
            name="📊 Veramon Collection",
            value=(
                f"**Total Captured:** {profile_data['total_captures']:,}\n"
                f"**Shiny Veramon:** {profile_data['shiny_captures']} ✨\n"
                f"**Capture Rate:** {self._calculate_capture_rate(profile_data):.1f}%"
            ),
            inline=True
        )
        
        # Add recent captures
        if profile_data['recent_captures']:
            recent_text = format_recent_captures(profile_data['recent_captures'])
            embed.add_field(
                name="🔄 Recent Captures",
                value=recent_text,
                inline=False
            )
        
        # Add achievements if any
        if profile_data.get('achievements'):
            achievements_text = "\n".join([f"• {a}" for a in profile_data['achievements'][:3]])
            embed.add_field(
                name="🏅 Recent Achievements",
                value=achievements_text if achievements_text else "No achievements yet!",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    def _calculate_level(self, xp: int) -> int:
        """Calculate the trainer level based on XP."""
        # Simple level calculation: level = sqrt(xp / 100)
        import math
        return max(1, math.floor(math.sqrt(xp / 100)))
        
    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate the XP required for a given level."""
        return level * level * 100
        
    def _calculate_capture_rate(self, profile_data: dict) -> float:
        """Calculate the user's capture success rate."""
        # This would normally come from the database, but we'll use a placeholder
        return min(99.9, max(60.0, 75.0 + (profile_data['total_captures'] / 100)))
        
    def _create_progress_bar(self, percent: float) -> str:
        """Create a visual progress bar based on percentage."""
        bar_length = 10
        filled_bars = int((percent / 100) * bar_length)
        
        filled_char = "🟦"
        empty_char = "⬜"
        
        return filled_char * filled_bars + empty_char * (bar_length - filled_bars)
        
    def _get_profile_color(self, profile_data: dict) -> discord.Color:
        """Get a color based on the user's progress and achievements."""
        if profile_data['shiny_captures'] > 10:
            return discord.Color.gold()
        elif profile_data['total_captures'] > 100:
            return discord.Color.blue()
        elif profile_data['battle_wins'] > 50:
            return discord.Color.red()
        else:
            return discord.Color.green()
            
    @app_commands.command(name="leaderboard", description="View the Veramon leaderboard")
    @app_commands.choices(category=[
        app_commands.Choice(name="Token Balance", value="tokens"),
        app_commands.Choice(name="Collection Size", value="collection"),
        app_commands.Choice(name="Battle Wins", value="battles"),
        app_commands.Choice(name="Shiny Count", value="shinies"),
        app_commands.Choice(name="Trading Activity", value="trades")
    ])
    @app_commands.choices(timeframe=[
        app_commands.Choice(name="All Time", value="all"),
        app_commands.Choice(name="This Month", value="month"),
        app_commands.Choice(name="This Week", value="week")
    ])
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
            title=f"🏆 Leaderboard: {title_mapping.get(category, category.title())}",
            description=f"Showing top players ({timeframe_text.get(timeframe, 'All Time')})",
            color=self._get_leaderboard_color(category)
        )
        
        # Add leaderboard entries
        if not leaders:
            embed.add_field(name="No data", value="No players found for this category.", inline=False)
        else:
            value_format = {
                "tokens": lambda x: f"{x:,} tokens 🪙",
                "collection": lambda x, total: f"{x}/{total} Veramon ({(x/total*100):.1f}%)",
                "battles": lambda x: f"{x} wins ⚔️",
                "shinies": lambda x: f"{x} shinies ✨",
                "trades": lambda x: f"{x} trades 🔄"
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
                    
                    # Add medal emoji for top 3
                    medal = ""
                    if i == 1:
                        medal = "🥇 "
                    elif i == 2:
                        medal = "🥈 "
                    elif i == 3:
                        medal = "🥉 "
                        
                    leaderboard_text += f"{medal}**{i}. {name}**: {formatted_value}\n"
                except Exception as e:
                    log(f"Error formatting leaderboard entry: {e}")
                    leaderboard_text += f"{i}. **Unknown User**: {value}\n"
            
            embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        
        # Add a footer with instructions
        embed.set_footer(text=f"Use /leaderboard to view other categories • Updated {discord.utils.format_dt(interaction.created_at, style='R')}")
            
        conn.close()
        await interaction.followup.send(embed=embed)
        
    def _get_leaderboard_color(self, category: str) -> discord.Color:
        """Get a color based on the leaderboard category."""
        color_map = {
            "tokens": discord.Color.gold(),
            "collection": discord.Color.blue(),
            "battles": discord.Color.red(),
            "shinies": discord.Color(0xF8C8DC),  # Pink
            "trades": discord.Color.green()
        }
        return color_map.get(category, discord.Color.blurple())

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
