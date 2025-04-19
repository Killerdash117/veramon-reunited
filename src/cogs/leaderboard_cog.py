import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from typing import List, Optional, Dict, Literal
from datetime import datetime, timedelta

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel

class LeaderboardCog(commands.Cog):
    """Cog for managing leaderboards and rankings in Veramon Reunited."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._initialize_leaderboard_db()
    
    def _initialize_leaderboard_db(self):
        """Initialize the leaderboard database tables if they don't exist."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create leaderboard_stats table to track various statistics
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard_stats (
            user_id TEXT,
            stat_name TEXT,
            stat_value INTEGER DEFAULT 0,
            last_updated TEXT,
            PRIMARY KEY (user_id, stat_name)
        )
        """)
        
        # Create seasonal_rankings table for seasonal competitions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS seasonal_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id TEXT,
            user_id TEXT,
            points INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 0,
            UNIQUE(season_id, user_id)
        )
        """)
        
        # Create tournament_rankings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT,
            user_id TEXT,
            points INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 0,
            UNIQUE(tournament_id, user_id)
        )
        """)
        
        conn.commit()
        conn.close()
    
    async def update_stat(self, user_id: str, stat_name: str, value: int = 1, mode: str = "increment"):
        """
        Update a statistic for a user.
        
        Args:
            user_id: The user's Discord ID
            stat_name: The name of the stat to update
            value: The value to add/set
            mode: "increment" to add to existing value, "set" to replace
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if stat exists
        cursor.execute("""
            SELECT stat_value FROM leaderboard_stats
            WHERE user_id = ? AND stat_name = ?
        """, (user_id, stat_name))
        
        existing = cursor.fetchone()
        now = datetime.now().isoformat()
        
        if existing:
            if mode == "increment":
                new_value = existing[0] + value
            else:
                new_value = value
                
            cursor.execute("""
                UPDATE leaderboard_stats
                SET stat_value = ?, last_updated = ?
                WHERE user_id = ? AND stat_name = ?
            """, (new_value, now, user_id, stat_name))
        else:
            cursor.execute("""
                INSERT INTO leaderboard_stats (user_id, stat_name, stat_value, last_updated)
                VALUES (?, ?, ?, ?)
            """, (user_id, stat_name, value, now))
        
        conn.commit()
        conn.close()
        
        return value if mode == "set" else (existing[0] + value if existing else value)
    
    @app_commands.command(name="leaderboard", description="View the leaderboard for different categories")
    @app_commands.describe(category="The category to view leaderboard for", timeframe="Timeframe for the leaderboard")
    @require_permission_level(PermissionLevel.USER)
    async def leaderboard(self, interaction: discord.Interaction, 
                          category: Literal["battles", "catches", "trades", "tokens", "xp", "streak"] = "xp",
                          timeframe: Literal["all", "season", "month", "week"] = "all"):
        """View the leaderboard for different categories and timeframes."""
        
        # Map category to actual stat name
        stat_mapping = {
            "battles": "battles_won",
            "catches": "total_catches",
            "trades": "total_trades",
            "tokens": "tokens",
            "xp": "xp",
            "streak": "login_streak"
        }
        
        stat_name = stat_mapping.get(category, "xp")
        
        # Calculate date based on timeframe
        now = datetime.now()
        
        if timeframe == "week":
            start_date = (now - timedelta(days=7)).isoformat()
            title_timeframe = "Weekly"
        elif timeframe == "month":
            start_date = (now - timedelta(days=30)).isoformat()
            title_timeframe = "Monthly"
        elif timeframe == "season":
            # A season is roughly 3 months
            start_date = (now - timedelta(days=90)).isoformat()
            title_timeframe = "Seasonal"
        else:
            start_date = None
            title_timeframe = "All-time"
        
        # Get leaderboard data from database
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT user_id, stat_value 
            FROM leaderboard_stats
            WHERE stat_name = ?
        """
        
        params = [stat_name]
        
        if start_date:
            query += " AND last_updated >= ?"
            params.append(start_date)
            
        query += " ORDER BY stat_value DESC LIMIT 10"
        
        cursor.execute(query, tuple(params))
        leaderboard_rows = cursor.fetchall()
        
        # If there's no data for this specific timeframe/category, let the user know
        if not leaderboard_rows:
            await interaction.response.send_message(
                f"No data available for the {category} leaderboard ({title_timeframe}). "
                f"Be the first to get on this leaderboard!",
                ephemeral=True
            )
            conn.close()
            return
        
        # Create leaderboard embed
        category_display = category.capitalize()
        
        embed = discord.Embed(
            title=f"{title_timeframe} {category_display} Leaderboard",
            description=f"Top trainers ranked by {category_display}",
            color=discord.Color.gold()
        )
        
        # Format the leaderboard entries
        rank_emojis = {
            1: "🥇",
            2: "🥈", 
            3: "🥉"
        }
        
        leaderboard_text = ""
        
        for i, (user_id, stat_value) in enumerate(leaderboard_rows, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                display_name = user.display_name
            except:
                display_name = f"User {user_id[:6]}..."
            
            # Format based on category
            if category == "tokens":
                value_display = f"{stat_value:,} tokens"
            elif category == "streak":
                value_display = f"{stat_value} day streak"
            else:
                value_display = str(stat_value)
                
            rank_display = rank_emojis.get(i, f"{i}.")
            leaderboard_text += f"{rank_display} **{display_name}** - {value_display}\n"
            
            # Add a bit of spacing after top 3
            if i == 3:
                leaderboard_text += "\n"
        
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        
        # Add timeframe info in footer
        if timeframe != "all":
            embed.set_footer(text=f"Showing data from {start_date.split('T')[0]} to present")
        else:
            embed.set_footer(text="Showing all-time statistics")
        
        await interaction.response.send_message(embed=embed)
    
    async def update_battlewins_stat(self, user_id: str, count: int = 1):
        """Update the battle wins statistic."""
        return await self.update_stat(user_id, "battles_won", count)
    
    async def update_catches_stat(self, user_id: str, count: int = 1):
        """Update the total catches statistic."""
        return await self.update_stat(user_id, "total_catches", count)
    
    async def update_trades_stat(self, user_id: str, count: int = 1):
        """Update the total trades statistic."""
        return await self.update_stat(user_id, "total_trades", count)
    
    async def update_streak_stat(self, user_id: str, streak: int):
        """Update the login streak statistic."""
        return await self.update_stat(user_id, "login_streak", streak, mode="set")
        
    @app_commands.command(name="mystats", description="View your personal stats and rankings")
    @require_permission_level(PermissionLevel.USER)
    async def mystats(self, interaction: discord.Interaction):
        """View your personal stats and where you rank on the leaderboards."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all stats for this user
        cursor.execute("""
            SELECT stat_name, stat_value
            FROM leaderboard_stats
            WHERE user_id = ?
        """, (user_id,))
        
        user_stats = cursor.fetchall()
        
        # Get user's ranks for each stat
        stats_with_ranks = []
        
        for stat_name, stat_value in user_stats:
            # Get count of users with higher stat value
            cursor.execute("""
                SELECT COUNT(*) 
                FROM leaderboard_stats
                WHERE stat_name = ? AND stat_value > ?
            """, (stat_name, stat_value))
            
            count = cursor.fetchone()[0]
            rank = count + 1  # User's rank is count of users with higher value + 1
            
            stats_with_ranks.append((stat_name, stat_value, rank))
        
        conn.close()
        
        # Create user stats embed
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Stats",
            description="Your personal statistics and rankings",
            color=discord.Color.blue()
        )
        
        # Format stats in a nice way
        formatted_stats = {}
        
        for stat_name, stat_value, rank in stats_with_ranks:
            # Format stat name to be more readable
            if stat_name == "battles_won":
                display_name = "Battles Won"
                icon = "⚔️"
            elif stat_name == "total_catches":
                display_name = "Total Catches"
                icon = "🔴"
            elif stat_name == "total_trades":
                display_name = "Total Trades"
                icon = "🔄"
            elif stat_name == "tokens":
                display_name = "Tokens"
                icon = "🪙"
            elif stat_name == "xp":
                display_name = "XP"
                icon = "✨"
            elif stat_name == "login_streak":
                display_name = "Daily Streak"
                icon = "📅"
            else:
                display_name = stat_name.replace("_", " ").title()
                icon = "📊"
                
            formatted_stats[stat_name] = {
                "name": display_name,
                "value": stat_value,
                "rank": rank,
                "icon": icon
            }
        
        # Add fields for each stat category
        for category in ["battles_won", "total_catches", "total_trades", "tokens", "xp", "login_streak"]:
            if category in formatted_stats:
                stat = formatted_stats[category]
                embed.add_field(
                    name=f"{stat['icon']} {stat['name']}",
                    value=f"**{stat['value']:,}**\nRank: #{stat['rank']}",
                    inline=True
                )
            else:
                # If user doesn't have this stat yet
                if category == "battles_won":
                    display_name = "Battles Won"
                    icon = "⚔️"
                elif category == "total_catches":
                    display_name = "Total Catches"
                    icon = "🔴"
                elif category == "total_trades":
                    display_name = "Total Trades"
                    icon = "🔄"
                elif category == "tokens":
                    display_name = "Tokens"
                    icon = "🪙"
                elif category == "xp":
                    display_name = "XP"
                    icon = "✨"
                elif category == "login_streak":
                    display_name = "Daily Streak"
                    icon = "📅"
                    
                embed.add_field(
                    name=f"{icon} {display_name}",
                    value="None recorded yet",
                    inline=True
                )
        
        # Add footer
        embed.set_footer(text="Keep playing to improve your stats and rankings!")
        
        await interaction.response.send_message(embed=embed)
    
async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
