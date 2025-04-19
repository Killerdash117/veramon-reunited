import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Literal

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel, is_mod

class ModeratorCog(commands.Cog):
    """
    Moderator commands for Veramon Reunited.
    
    Includes commands for trade moderation, user management, battle moderation,
    monitoring, and guild/faction moderation.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    #-------------------------------------------------------------------
    # Trade Moderation
    #-------------------------------------------------------------------
    
    @app_commands.command(name="mod_trade_view", description="View details of any trade (Mod only)")
    @app_commands.describe(trade_id="ID of the trade to view")
    @is_mod()
    async def mod_trade_view(self, interaction: discord.Interaction, trade_id: int):
        """View details of any trade."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get trade details
        cursor.execute("""
            SELECT t.id, t.initiator_id, t.recipient_id, t.status, t.created_at, t.completed_at,
                   i.username AS initiator_name, r.username AS recipient_name
            FROM trades t
            LEFT JOIN users i ON t.initiator_id = i.user_id
            LEFT JOIN users r ON t.recipient_id = r.user_id
            WHERE t.id = ?
        """, (trade_id,))
        
        trade = cursor.fetchone()
        
        if not trade:
            await interaction.response.send_message(
                f"Trade #{trade_id} not found.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Get traded items
        cursor.execute("""
            SELECT ti.user_id, ti.veramon_id, ti.tokens, v.name AS veramon_name,
                   v.nickname, v.level, v.shiny
            FROM trade_items ti
            LEFT JOIN veramon_captures v ON ti.veramon_id = v.id
            WHERE ti.trade_id = ?
        """, (trade_id,))
        
        trade_items = cursor.fetchall()
        conn.close()
        
        # Create embed
        embed = discord.Embed(
            title=f"Trade #{trade_id} Details",
            description=f"Status: {trade['status'].capitalize()}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Initiator", value=f"<@{trade['initiator_id']}> ({trade['initiator_name']})", inline=True)
        embed.add_field(name="Recipient", value=f"<@{trade['recipient_id']}> ({trade['recipient_name']})", inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(datetime.fromisoformat(trade['created_at'])), inline=True)
        
        if trade['completed_at']:
            embed.add_field(name="Completed", value=discord.utils.format_dt(datetime.fromisoformat(trade['completed_at'])), inline=True)
        
        # Add items being traded
        initiator_items = [item for item in trade_items if str(item['user_id']) == trade['initiator_id']]
        recipient_items = [item for item in trade_items if str(item['user_id']) == trade['recipient_id']]
        
        # Format initiator's offerings
        initiator_offering = ""
        for item in initiator_items:
            if item['veramon_id']:
                shiny_text = "✨ " if item['shiny'] else ""
                veramon_text = f"{shiny_text}**{item['nickname'] or item['veramon_name']}** (Lvl {item['level']})"
                initiator_offering += f"• {veramon_text}\n"
            if item['tokens'] and item['tokens'] > 0:
                initiator_offering += f"• {item['tokens']} tokens\n"
                
        if not initiator_offering:
            initiator_offering = "Nothing"
            
        embed.add_field(name=f"{trade['initiator_name']} is offering:", value=initiator_offering, inline=False)
        
        # Format recipient's offerings
        recipient_offering = ""
        for item in recipient_items:
            if item['veramon_id']:
                shiny_text = "✨ " if item['shiny'] else ""
                veramon_text = f"{shiny_text}**{item['nickname'] or item['veramon_name']}** (Lvl {item['level']})"
                recipient_offering += f"• {veramon_text}\n"
            if item['tokens'] and item['tokens'] > 0:
                recipient_offering += f"• {item['tokens']} tokens\n"
                
        if not recipient_offering:
            recipient_offering = "Nothing"
            
        embed.add_field(name=f"{trade['recipient_name']} is offering:", value=recipient_offering, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="mod_trade_cancel", description="Cancel a suspicious trade (Mod only)")
    @app_commands.describe(
        trade_id="ID of the trade to cancel",
        reason="Reason for cancellation"
    )
    @is_mod()
    async def mod_trade_cancel(self, interaction: discord.Interaction, trade_id: int, reason: str):
        """Cancel a suspicious trade."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if trade exists and is active
        cursor.execute("""
            SELECT t.id, t.initiator_id, t.recipient_id, t.status,
                   i.username AS initiator_name, r.username AS recipient_name
            FROM trades t
            LEFT JOIN users i ON t.initiator_id = i.user_id
            LEFT JOIN users r ON t.recipient_id = r.user_id
            WHERE t.id = ?
        """, (trade_id,))
        
        trade = cursor.fetchone()
        
        if not trade:
            await interaction.response.send_message(
                f"Trade #{trade_id} not found.",
                ephemeral=True
            )
            conn.close()
            return
            
        if trade['status'] != 'pending':
            await interaction.response.send_message(
                f"Trade #{trade_id} cannot be cancelled as it is already {trade['status']}.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Update trade status
        cursor.execute("""
            UPDATE trades
            SET status = 'cancelled', completed_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), trade_id))
        
        # Log moderation action
        cursor.execute("""
            INSERT INTO moderation_log (moderator_id, action_type, target_id, reason, timestamp)
            VALUES (?, 'trade_cancel', ?, ?, ?)
        """, (
            str(interaction.user.id),
            trade_id,
            reason,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Notify users
        embed = discord.Embed(
            title="Trade Cancelled by Moderator",
            description=f"Trade #{trade_id} has been cancelled by a moderator.",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="If you believe this was in error, please contact the moderation team.")
        
        await interaction.response.send_message(embed=embed)
        
        # Try to notify both parties
        initiator = await self.bot.fetch_user(int(trade['initiator_id']))
        recipient = await self.bot.fetch_user(int(trade['recipient_id']))
        
        if initiator:
            try:
                await initiator.send(embed=embed)
            except:
                pass
                
        if recipient:
            try:
                await recipient.send(embed=embed)
            except:
                pass

    @app_commands.command(name="mod_trade_history", description="View a user's trade history (Mod only)")
    @app_commands.describe(user_id="ID of the user to check")
    @is_mod()
    async def mod_trade_history(self, interaction: discord.Interaction, user_id: str):
        """View a user's trade history."""
        # Convert mention to ID if needed
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
                
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            await interaction.response.send_message(
                f"User with ID {user_id} not found in the database.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Get recent trades (last 20)
        cursor.execute("""
            SELECT t.id, t.status, t.created_at, t.completed_at,
                   CASE WHEN t.initiator_id = ? THEN t.recipient_id ELSE t.initiator_id END AS other_user_id,
                   CASE WHEN t.initiator_id = ? THEN r.username ELSE i.username END AS other_username
            FROM trades t
            LEFT JOIN users i ON t.initiator_id = i.user_id
            LEFT JOIN users r ON t.recipient_id = r.user_id
            WHERE t.initiator_id = ? OR t.recipient_id = ?
            ORDER BY t.created_at DESC
            LIMIT 20
        """, (user_id, user_id, user_id, user_id))
        
        trades = cursor.fetchall()
        conn.close()
        
        if not trades:
            await interaction.response.send_message(
                f"No trade history found for user {user['username']} ({user_id}).",
                ephemeral=True
            )
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"Trade History for {user['username']}",
            description=f"Showing the last {len(trades)} trades",
            color=discord.Color.blue()
        )
        
        for trade in trades:
            created_time = discord.utils.format_dt(datetime.fromisoformat(trade['created_at']), style='R')
            
            if trade['status'] == 'completed':
                status = "✅ Completed"
            elif trade['status'] == 'cancelled':
                status = "❌ Cancelled"
            else:
                status = "⏳ Pending"
                
            with_text = f"with {trade['other_username']} (<@{trade['other_user_id']}>)"
            embed.add_field(
                name=f"Trade #{trade['id']} - {status}",
                value=f"{with_text}\n{created_time}",
                inline=True
            )
            
        await interaction.response.send_message(embed=embed)

    #-------------------------------------------------------------------
    # User Management
    #-------------------------------------------------------------------
    
    @app_commands.command(name="mod_warn", description="Issue a warning to a user (Mod only)")
    @app_commands.describe(
        user_id="ID of the user to warn",
        reason="Reason for the warning"
    )
    @is_mod()
    async def mod_warn(self, interaction: discord.Interaction, user_id: str, reason: str):
        """Issue a warning to a user."""
        # Convert mention to ID if needed
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
                
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            await interaction.response.send_message(
                f"User with ID {user_id} not found in the database.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Log warning
        cursor.execute("""
            INSERT INTO moderation_log (moderator_id, action_type, target_id, reason, timestamp)
            VALUES (?, 'warning', ?, ?, ?)
        """, (
            str(interaction.user.id),
            user_id,
            reason,
            datetime.utcnow().isoformat()
        ))
        
        # Get warning count
        cursor.execute("""
            SELECT COUNT(*) as warning_count
            FROM moderation_log
            WHERE action_type = 'warning' AND target_id = ?
        """, (user_id,))
        
        warning_count = cursor.fetchone()['warning_count']
        
        conn.commit()
        conn.close()
        
        # Create warning embed
        embed = discord.Embed(
            title="User Warning",
            description=f"A warning has been issued to <@{user_id}>.",
            color=discord.Color.yellow()
        )
        
        embed.add_field(name="User", value=f"{user['username']} (<@{user_id}>)", inline=True)
        embed.add_field(name="Warning #", value=str(warning_count), inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Repeated warnings may result in mutes or bans.")
        
        await interaction.response.send_message(embed=embed)
        
        # Try to DM the user
        try:
            target_user = await self.bot.fetch_user(int(user_id))
            if target_user:
                user_embed = discord.Embed(
                    title="Warning Notice",
                    description="You have received a warning in Veramon Reunited.",
                    color=discord.Color.yellow()
                )
                
                user_embed.add_field(name="Reason", value=reason, inline=False)
                user_embed.add_field(name="Warning #", value=str(warning_count), inline=True)
                user_embed.set_footer(text="Repeated warnings may result in mutes or bans. If you feel this warning was given in error, please contact server staff.")
                
                await target_user.send(embed=user_embed)
        except:
            # Failed to DM user, continue anyway
            pass

    @app_commands.command(name="mod_mute", description="Temporarily mute a user from using commands (Mod only)")
    @app_commands.describe(
        user_id="ID of the user to mute",
        duration="Duration in minutes (max 10080 = 1 week)",
        reason="Reason for the mute"
    )
    @is_mod()
    async def mod_mute(self, interaction: discord.Interaction, user_id: str, duration: int, reason: str):
        """Temporarily prevent a user from using commands."""
        # Cap duration at 1 week (10080 minutes)
        duration = min(duration, 10080)
        
        # Convert mention to ID if needed
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
                
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            await interaction.response.send_message(
                f"User with ID {user_id} not found in the database.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Set mute end time
        end_time = datetime.utcnow() + timedelta(minutes=duration)
        
        # Add or update mute in database
        cursor.execute("""
            INSERT OR REPLACE INTO user_restrictions
            (user_id, restriction_type, end_time, reason, moderator_id)
            VALUES (?, 'mute', ?, ?, ?)
        """, (
            user_id,
            end_time.isoformat(),
            reason,
            str(interaction.user.id)
        ))
        
        # Log moderation action
        cursor.execute("""
            INSERT INTO moderation_log (moderator_id, action_type, target_id, reason, timestamp)
            VALUES (?, 'mute', ?, ?, ?)
        """, (
            str(interaction.user.id),
            user_id,
            f"{reason} (Duration: {duration} minutes)",
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Format time strings
        time_until = discord.utils.format_dt(end_time, style='R')
        exact_time = discord.utils.format_dt(end_time)
        
        # Create mute embed
        embed = discord.Embed(
            title="User Muted",
            description=f"<@{user_id}> has been muted from using bot commands.",
            color=discord.Color.red()
        )
        
        embed.add_field(name="User", value=f"{user['username']} (<@{user_id}>)", inline=True)
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
        embed.add_field(name="Expires", value=f"{time_until} ({exact_time})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        # Try to DM the user
        try:
            target_user = await self.bot.fetch_user(int(user_id))
            if target_user:
                user_embed = discord.Embed(
                    title="You Have Been Muted",
                    description="You have been temporarily restricted from using Veramon Reunited commands.",
                    color=discord.Color.red()
                )
                
                user_embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
                user_embed.add_field(name="Expires", value=f"{time_until} ({exact_time})", inline=True)
                user_embed.add_field(name="Reason", value=reason, inline=False)
                user_embed.set_footer(text="If you feel this action was taken in error, please contact server staff.")
                
                await target_user.send(embed=user_embed)
        except:
            # Failed to DM user, continue anyway
            pass

    @app_commands.command(name="mod_unmute", description="Remove a command mute from a user (Mod only)")
    @app_commands.describe(user_id="ID of the user to unmute")
    @is_mod()
    async def mod_unmute(self, interaction: discord.Interaction, user_id: str):
        """Remove a command mute from a user."""
        # Convert mention to ID if needed
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
                
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user exists and is muted
        cursor.execute("""
            SELECT u.username, r.end_time, r.reason
            FROM users u
            JOIN user_restrictions r ON u.user_id = r.user_id
            WHERE u.user_id = ? AND r.restriction_type = 'mute'
        """, (user_id,))
        
        mute_info = cursor.fetchone()
        
        if not mute_info:
            await interaction.response.send_message(
                f"User with ID {user_id} is not currently muted.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Remove mute
        cursor.execute("""
            DELETE FROM user_restrictions
            WHERE user_id = ? AND restriction_type = 'mute'
        """, (user_id,))
        
        # Log moderation action
        cursor.execute("""
            INSERT INTO moderation_log (moderator_id, action_type, target_id, reason, timestamp)
            VALUES (?, 'unmute', ?, ?, ?)
        """, (
            str(interaction.user.id),
            user_id,
            "Manual unmute by moderator",
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Create unmute embed
        embed = discord.Embed(
            title="User Unmuted",
            description=f"<@{user_id}> has been unmuted and can use bot commands again.",
            color=discord.Color.green()
        )
        
        embed.add_field(name="User", value=f"{mute_info['username']} (<@{user_id}>)", inline=True)
        embed.add_field(name="Original Reason", value=mute_info['reason'], inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
        
        # Try to DM the user
        try:
            target_user = await self.bot.fetch_user(int(user_id))
            if target_user:
                user_embed = discord.Embed(
                    title="You Have Been Unmuted",
                    description="Your mute in Veramon Reunited has been removed. You can now use bot commands again.",
                    color=discord.Color.green()
                )
                
                await target_user.send(embed=user_embed)
        except:
            # Failed to DM user, continue anyway
            pass

    #-------------------------------------------------------------------
    # Battle Moderation
    #-------------------------------------------------------------------
    
    @app_commands.command(name="mod_battle_view", description="View details of any battle (Mod only)")
    @app_commands.describe(battle_id="ID of the battle to view")
    @is_mod()
    async def mod_battle_view(self, interaction: discord.Interaction, battle_id: int):
        """View details of any battle."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get battle details
        cursor.execute("""
            SELECT b.id, b.status, b.battle_type, b.start_time, b.end_time,
                   b.winner_id, b.current_turn
            FROM battles b
            WHERE b.id = ?
        """, (battle_id,))
        
        battle = cursor.fetchone()
        
        if not battle:
            await interaction.response.send_message(
                f"Battle #{battle_id} not found.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Get participants
        cursor.execute("""
            SELECT bp.user_id, u.username
            FROM battle_participants bp
            JOIN users u ON bp.user_id = u.user_id
            WHERE bp.battle_id = ?
        """, (battle_id,))
        
        participants = cursor.fetchall()
        
        # Get battle log entries
        cursor.execute("""
            SELECT log_text, timestamp
            FROM battle_logs
            WHERE battle_id = ?
            ORDER BY timestamp ASC
            LIMIT 15
        """, (battle_id,))
        
        log_entries = cursor.fetchall()
        conn.close()
        
        # Create embed
        embed = discord.Embed(
            title=f"Battle #{battle_id} Details",
            description=f"Type: {battle['battle_type'].replace('_', ' ').title()}\nStatus: {battle['status'].capitalize()}",
            color=discord.Color.blue()
        )
        
        # Add participants
        participants_text = "\n".join([f"• {p['username']} (<@{p['user_id']}>)" for p in participants])
        embed.add_field(name="Participants", value=participants_text or "None", inline=False)
        
        # Add timing information
        if battle['start_time']:
            start_time = datetime.fromisoformat(battle['start_time'])
            embed.add_field(name="Started", value=discord.utils.format_dt(start_time), inline=True)
            
        if battle['end_time']:
            end_time = datetime.fromisoformat(battle['end_time'])
            embed.add_field(name="Ended", value=discord.utils.format_dt(end_time), inline=True)
            
        # Add winner if applicable
        if battle['winner_id']:
            embed.add_field(name="Winner", value=f"<@{battle['winner_id']}>", inline=True)
            
        # Add current turn if battle is ongoing
        if battle['status'] == 'active' and battle['current_turn']:
            embed.add_field(name="Current Turn", value=f"<@{battle['current_turn']}>", inline=True)
            
        # Add battle log
        if log_entries:
            log_text = "\n".join([f"• {entry['log_text']}" for entry in log_entries[-10:]])
            if len(log_entries) > 10:
                log_text = f"*... {len(log_entries) - 10} earlier entries ...*\n" + log_text
            embed.add_field(name="Battle Log (Last 10 Entries)", value=log_text, inline=False)
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="mod_battle_end", description="Force-end a stuck battle (Mod only)")
    @app_commands.describe(
        battle_id="ID of the battle to end",
        winner_id="ID of the winner (optional)"
    )
    @is_mod()
    async def mod_battle_end(self, interaction: discord.Interaction, battle_id: int, winner_id: Optional[str] = None):
        """Force-end a stuck battle."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if battle exists and is active
        cursor.execute("""
            SELECT id, status, battle_type
            FROM battles
            WHERE id = ?
        """, (battle_id,))
        
        battle = cursor.fetchone()
        
        if not battle:
            await interaction.response.send_message(
                f"Battle #{battle_id} not found.",
                ephemeral=True
            )
            conn.close()
            return
            
        if battle['status'] != 'active':
            await interaction.response.send_message(
                f"Battle #{battle_id} is not active (current status: {battle['status']}).",
                ephemeral=True
            )
            conn.close()
            return
            
        # Convert winner_id from mention if provided
        if winner_id and winner_id.startswith('<@') and winner_id.endswith('>'):
            winner_id = winner_id[2:-1]
            if winner_id.startswith('!'):
                winner_id = winner_id[1:]
                
        # Update battle status
        end_time = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE battles
            SET status = 'completed', end_time = ?, winner_id = ?
            WHERE id = ?
        """, (end_time, winner_id, battle_id))
        
        # Add log entry
        cursor.execute("""
            INSERT INTO battle_logs (battle_id, log_text, timestamp)
            VALUES (?, ?, ?)
        """, (
            battle_id,
            f"Battle forcibly ended by moderator {interaction.user.display_name}.",
            end_time
        ))
        
        # Log moderation action
        cursor.execute("""
            INSERT INTO moderation_log (moderator_id, action_type, target_id, reason, timestamp)
            VALUES (?, 'battle_end', ?, ?, ?)
        """, (
            str(interaction.user.id),
            str(battle_id),
            "Force-ended stuck battle",
            end_time
        ))
        
        conn.commit()
        conn.close()
        
        # Create confirmation embed
        embed = discord.Embed(
            title="Battle Force-Ended",
            description=f"Battle #{battle_id} has been forcibly ended by a moderator.",
            color=discord.Color.orange()
        )
        
        if winner_id:
            embed.add_field(name="Winner", value=f"<@{winner_id}>", inline=True)
        else:
            embed.add_field(name="Outcome", value="No winner declared", inline=True)
            
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Note", value="This battle was manually ended by a moderator. If you have any questions, please contact the staff team.", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
async def setup(bot: commands.Bot):
    """Add the ModeratorCog to the bot."""
    await bot.add_cog(ModeratorCog(bot))
