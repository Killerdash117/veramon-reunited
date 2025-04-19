import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel

class TournamentCog(commands.Cog):
    """Tournament system for Veramon Reunited."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_tournaments = {}
        self._initialize_tournament_db()
    
    def _initialize_tournament_db(self):
        """Initialize the tournament database tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create tournaments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            max_participants INTEGER DEFAULT 16,
            current_participants INTEGER DEFAULT 0,
            start_time TEXT,
            end_time TEXT,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            entry_fee INTEGER DEFAULT 0,
            token_prize_pool INTEGER DEFAULT 0,
            special_prize TEXT
        )
        """)
        
        # Create tournament_participants table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            user_id TEXT,
            registration_time TEXT,
            status TEXT DEFAULT 'active',
            eliminated_round INTEGER DEFAULT 0,
            eliminated_by TEXT,
            placement INTEGER DEFAULT 0,
            FOREIGN KEY(tournament_id) REFERENCES tournaments(id),
            UNIQUE(tournament_id, user_id)
        )
        """)
        
        # Create tournament_matches table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            round INTEGER,
            match_number INTEGER,
            player1_id TEXT,
            player2_id TEXT,
            winner_id TEXT,
            battle_id INTEGER,
            status TEXT DEFAULT 'pending',
            scheduled_time TEXT,
            completed_time TEXT,
            FOREIGN KEY(tournament_id) REFERENCES tournaments(id)
        )
        """)
        
        conn.commit()
        conn.close()
    
    @app_commands.command(name="tournament_create", description="Create a new tournament")
    @app_commands.describe(
        name="Name of the tournament",
        description="Description of the tournament",
        max_participants="Maximum number of participants (4, 8, 16, or 32)",
        entry_fee="Entry fee in tokens (0 for free)",
        start_time="When the tournament will start (hours from now)"
    )
    @require_permission_level(PermissionLevel.ADMIN)
    async def tournament_create(self, interaction: discord.Interaction, 
                                name: str, 
                                description: str, 
                                max_participants: app_commands.Range[int, 4, 32] = 16,
                                entry_fee: app_commands.Range[int, 0, 1000] = 0,
                                start_time: app_commands.Range[int, 1, 168] = 24):
        """Create a new tournament."""
        # Validate max_participants is a power of 2
        if max_participants not in (4, 8, 16, 32):
            await interaction.response.send_message(
                "Maximum participants must be 4, 8, 16, or 32.",
                ephemeral=True
            )
            return
        
        # Calculate token prize pool based on entry fee
        token_prize_pool = entry_fee * max_participants
        
        # Calculate start and end times
        now = datetime.now()
        start_time_dt = now + timedelta(hours=start_time)
        
        # Create tournament in database
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tournaments (
                name, description, status, max_participants, 
                start_time, created_by, created_at, updated_at,
                entry_fee, token_prize_pool
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, description, "registration", max_participants,
            start_time_dt.isoformat(), str(interaction.user.id),
            now.isoformat(), now.isoformat(),
            entry_fee, token_prize_pool
        ))
        
        tournament_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create and send tournament announcement
        embed = discord.Embed(
            title=f"New Tournament: {name}",
            description=description,
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Details",
            value=(
                f"**Max Participants**: {max_participants}\n"
                f"**Entry Fee**: {entry_fee} tokens\n"
                f"**Prize Pool**: {token_prize_pool} tokens\n"
                f"**Starts In**: {start_time} hours\n"
                f"**Registration**: Use `/tournament_join {tournament_id}`"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Tournament ID: {tournament_id}")
        
        await interaction.response.send_message(
            "Tournament created successfully!",
            embed=embed
        )
    
    @app_commands.command(name="tournament_join", description="Join a tournament")
    @app_commands.describe(
        tournament_id="ID of the tournament to join"
    )
    @require_permission_level(PermissionLevel.USER)
    async def tournament_join(self, interaction: discord.Interaction, tournament_id: int):
        """Join a tournament."""
        user_id = str(interaction.user.id)
        
        # Check if tournament exists and is in registration phase
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, status, max_participants, current_participants, entry_fee, start_time
            FROM tournaments
            WHERE id = ?
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            await interaction.response.send_message(
                "Tournament not found.",
                ephemeral=True
            )
            conn.close()
            return
        
        _, name, status, max_participants, current_participants, entry_fee, start_time = tournament
        
        # Check tournament status
        if status != "registration":
            await interaction.response.send_message(
                f"This tournament is not accepting registrations (current status: {status}).",
                ephemeral=True
            )
            conn.close()
            return
        
        # Check if tournament is full
        if current_participants >= max_participants:
            await interaction.response.send_message(
                "This tournament is already full.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Check if user is already registered
        cursor.execute("""
            SELECT id FROM tournament_participants
            WHERE tournament_id = ? AND user_id = ?
        """, (tournament_id, user_id))
        
        if cursor.fetchone():
            await interaction.response.send_message(
                "You are already registered for this tournament.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Check if user has enough tokens for entry fee
        if entry_fee > 0:
            cursor.execute("""
                SELECT tokens FROM users
                WHERE user_id = ?
            """, (user_id,))
            
            user_tokens = cursor.fetchone()
            
            if not user_tokens or user_tokens[0] < entry_fee:
                await interaction.response.send_message(
                    f"You don't have enough tokens to join this tournament. Required: {entry_fee}",
                    ephemeral=True
                )
                conn.close()
                return
            
            # Deduct entry fee
            cursor.execute("""
                UPDATE users
                SET tokens = tokens - ?
                WHERE user_id = ?
            """, (entry_fee, user_id))
        
        # Register user
        now = datetime.now()
        cursor.execute("""
            INSERT INTO tournament_participants (
                tournament_id, user_id, registration_time, status
            ) VALUES (?, ?, ?, ?)
        """, (tournament_id, user_id, now.isoformat(), "active"))
        
        # Update tournament participant count
        cursor.execute("""
            UPDATE tournaments
            SET current_participants = current_participants + 1,
                updated_at = ?
            WHERE id = ?
        """, (now.isoformat(), tournament_id))
        
        conn.commit()
        conn.close()
        
        # Send success message
        await interaction.response.send_message(
            f"You have successfully registered for the tournament **{name}**!\n"
            f"Tournament starts at: {start_time}"
        )
    
    @app_commands.command(name="tournament_list", description="List active tournaments")
    @require_permission_level(PermissionLevel.USER)
    async def tournament_list(self, interaction: discord.Interaction):
        """List active tournaments."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get active tournaments
        cursor.execute("""
            SELECT id, name, description, status, max_participants, 
                   current_participants, start_time, entry_fee, token_prize_pool
            FROM tournaments
            WHERE status IN ('registration', 'in_progress')
            ORDER BY start_time ASC
        """)
        
        tournaments = cursor.fetchall()
        conn.close()
        
        if not tournaments:
            await interaction.response.send_message(
                "There are no active tournaments at the moment.",
                ephemeral=True
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title="Active Tournaments",
            description="Here are the active tournaments you can join or view:",
            color=discord.Color.blue()
        )
        
        for tournament in tournaments:
            tid, name, description, status, max_participants, current_participants, start_time, entry_fee, prize_pool = tournament
            
            try:
                start_time_dt = datetime.fromisoformat(start_time)
                start_time_str = start_time_dt.strftime("%Y-%m-%d %H:%M")
            except:
                start_time_str = start_time
            
            embed.add_field(
                name=f"{name} (ID: {tid})",
                value=(
                    f"**Status**: {status}\n"
                    f"**Participants**: {current_participants}/{max_participants}\n"
                    f"**Entry Fee**: {entry_fee} tokens\n"
                    f"**Prize Pool**: {prize_pool} tokens\n"
                    f"**Starts At**: {start_time_str}\n"
                    f"**Description**: {description}\n"
                    f"**Join**: `/tournament_join {tid}`"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="tournament_start", description="Start a tournament")
    @app_commands.describe(
        tournament_id="ID of the tournament to start"
    )
    @require_permission_level(PermissionLevel.ADMIN)
    async def tournament_start(self, interaction: discord.Interaction, tournament_id: int):
        """Start a tournament."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if tournament exists and is in registration phase
        cursor.execute("""
            SELECT id, name, status, max_participants, current_participants
            FROM tournaments
            WHERE id = ?
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            await interaction.response.send_message(
                "Tournament not found.",
                ephemeral=True
            )
            conn.close()
            return
        
        _, name, status, max_participants, current_participants = tournament
        
        if status != "registration":
            await interaction.response.send_message(
                f"This tournament cannot be started (current status: {status}).",
                ephemeral=True
            )
            conn.close()
            return
        
        # Get participants
        cursor.execute("""
            SELECT user_id FROM tournament_participants
            WHERE tournament_id = ? AND status = 'active'
            ORDER BY registration_time ASC
        """, (tournament_id,))
        
        participants = [row[0] for row in cursor.fetchall()]
        
        # Check if we have enough participants (at least 4)
        if len(participants) < 4:
            await interaction.response.send_message(
                f"Not enough participants to start the tournament. Need at least 4, got {len(participants)}.",
                ephemeral=True
            )
            conn.close()
            return
        
        # If participants count is not a power of 2, remove excess participants
        valid_counts = [4, 8, 16, 32]
        target_count = max([c for c in valid_counts if c <= len(participants)])
        
        if len(participants) > target_count:
            # Refund entry fee for excess participants
            cursor.execute("""
                SELECT entry_fee FROM tournaments WHERE id = ?
            """, (tournament_id,))
            
            entry_fee = cursor.fetchone()[0]
            
            for user_id in participants[target_count:]:
                if entry_fee > 0:
                    cursor.execute("""
                        UPDATE users
                        SET tokens = tokens + ?
                        WHERE user_id = ?
                    """, (entry_fee, user_id))
                
                cursor.execute("""
                    UPDATE tournament_participants
                    SET status = 'withdrawn'
                    WHERE tournament_id = ? AND user_id = ?
                """, (tournament_id, user_id))
            
            participants = participants[:target_count]
        
        # Update tournament status
        now = datetime.now()
        cursor.execute("""
            UPDATE tournaments
            SET status = 'in_progress',
                current_participants = ?,
                updated_at = ?
            WHERE id = ?
        """, (len(participants), now.isoformat(), tournament_id))
        
        # Generate bracket matches
        random.shuffle(participants)  # Randomize participant order
        
        round_number = 1
        matches_in_round = len(participants) // 2
        
        # Create all first round matches
        for i in range(matches_in_round):
            player1 = participants[i*2]
            player2 = participants[i*2+1]
            
            cursor.execute("""
                INSERT INTO tournament_matches (
                    tournament_id, round, match_number, player1_id, player2_id, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (tournament_id, round_number, i+1, player1, player2, "pending"))
        
        conn.commit()
        conn.close()
        
        # Send success message with bracket
        await interaction.response.send_message(
            f"Tournament **{name}** has been started with {len(participants)} participants!\n"
            f"The first round matches have been generated. Use `/tournament_status {tournament_id}` to view the bracket."
        )
    
    @app_commands.command(name="tournament_status", description="View tournament status and bracket")
    @app_commands.describe(
        tournament_id="ID of the tournament to view"
    )
    @require_permission_level(PermissionLevel.USER)
    async def tournament_status(self, interaction: discord.Interaction, tournament_id: int):
        """View tournament status and bracket."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get tournament info
        cursor.execute("""
            SELECT id, name, description, status, max_participants, 
                   current_participants, start_time, entry_fee, token_prize_pool
            FROM tournaments
            WHERE id = ?
        """, (tournament_id,))
        
        tournament = cursor.fetchone()
        
        if not tournament:
            await interaction.response.send_message(
                "Tournament not found.",
                ephemeral=True
            )
            conn.close()
            return
        
        tid, name, description, status, max_participants, current_participants, start_time, entry_fee, prize_pool = tournament
        
        # Get matches
        cursor.execute("""
            SELECT id, round, match_number, player1_id, player2_id, winner_id, status
            FROM tournament_matches
            WHERE tournament_id = ?
            ORDER BY round ASC, match_number ASC
        """, (tournament_id,))
        
        matches = cursor.fetchall()
        
        # Get participants
        cursor.execute("""
            SELECT user_id, status, placement
            FROM tournament_participants
            WHERE tournament_id = ? AND status != 'withdrawn'
        """, (tournament_id,))
        
        participants = cursor.fetchall()
        
        conn.close()
        
        # Create tournament status embed
        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=description,
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Details",
            value=(
                f"**Status**: {status}\n"
                f"**Participants**: {current_participants}/{max_participants}\n"
                f"**Entry Fee**: {entry_fee} tokens\n"
                f"**Prize Pool**: {prize_pool} tokens\n"
                f"**Started At**: {start_time}"
            ),
            inline=False
        )
        
        # Format matches by round
        if matches:
            rounds = {}
            for match in matches:
                mid, round_num, match_num, player1, player2, winner, match_status = match
                
                if round_num not in rounds:
                    rounds[round_num] = []
                
                # Get usernames if possible
                try:
                    player1_name = f"<@{player1}>" if player1 else "TBD"
                    player2_name = f"<@{player2}>" if player2 else "TBD"
                    winner_name = f"<@{winner}>" if winner else "TBD"
                except:
                    player1_name = player1 or "TBD"
                    player2_name = player2 or "TBD"
                    winner_name = winner or "TBD"
                
                match_info = (
                    f"**Match {match_num}**: {player1_name} vs {player2_name}\n"
                    f"**Status**: {match_status}\n"
                    f"**Winner**: {winner_name if winner else 'TBD'}\n"
                )
                
                rounds[round_num].append(match_info)
            
            # Add rounds to embed
            round_names = {
                1: "First Round",
                2: "Quarter-Finals",
                3: "Semi-Finals",
                4: "Finals",
                5: "Grand Finals"
            }
            
            for round_num in sorted(rounds.keys()):
                round_name = round_names.get(round_num, f"Round {round_num}")
                round_text = "\n".join(rounds[round_num])
                
                embed.add_field(
                    name=round_name,
                    value=round_text,
                    inline=False
                )
        
        # Add final rankings if tournament is completed
        if status == "completed":
            # Sort participants by placement
            ranked_participants = sorted([p for p in participants if p[2] > 0], 
                                        key=lambda p: p[2])
            
            if ranked_participants:
                rankings_text = ""
                for user_id, _, placement in ranked_participants[:3]:
                    try:
                        rankings_text += f"**{placement}. <@{user_id}>**\n"
                    except:
                        rankings_text += f"**{placement}. User {user_id}**\n"
                
                embed.add_field(
                    name="Final Rankings",
                    value=rankings_text,
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TournamentCog(bot))
