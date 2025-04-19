import discord
from discord.ext import commands
from discord import app_commands
import json
import sqlite3
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel
from src.utils.data_loader import load_all_veramon_data

class TradeView(discord.ui.View):
    """Interactive view for trade offers."""
    
    def __init__(self, initiator_id: int, recipient_id: int, trade_id: int, cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.initiator_id = initiator_id
        self.recipient_id = recipient_id
        self.trade_id = trade_id
        self.cog = cog
        
    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only the recipient can accept the trade
        if interaction.user.id != self.recipient_id:
            await interaction.response.send_message("Only the trade recipient can accept this trade.", ephemeral=True)
            return
            
        await interaction.response.defer()
        await self.cog.execute_trade(interaction, self.trade_id)
        self.stop()
        
    @discord.ui.button(label="Decline Trade", style=discord.ButtonStyle.red)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Both parties can decline
        if interaction.user.id not in [self.initiator_id, self.recipient_id]:
            await interaction.response.send_message("You are not part of this trade.", ephemeral=True)
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update trade status
        cursor.execute("""
            UPDATE trades 
            SET status = 'declined', 
                updated_at = ? 
            WHERE trade_id = ?
        """, (datetime.utcnow().isoformat(), self.trade_id))
        
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"Trade #{self.trade_id} has been declined.")
        self.stop()

class TradingCog(commands.Cog):
    """
    Trading system for Veramon Reunited.
    
    Allows players to trade their captured Veramon with other players.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_trade_views = {}
        
    @app_commands.command(name="trade_create", description="Create a new trade with another player")
    @app_commands.describe(
        player="The player to trade with"
    )
    @require_permission_level(PermissionLevel.USER)
    async def trade_create(self, interaction: discord.Interaction, player: discord.Member):
        """Create a new trade with another player."""
        initiator_id = str(interaction.user.id)
        recipient_id = str(player.id)
        
        # Validate user is not trading with themselves
        if initiator_id == recipient_id:
            await interaction.response.send_message(
                "You cannot trade with yourself.",
                ephemeral=True
            )
            return
            
        # Check if user already has an active trade
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT trade_id FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) 
            AND status = 'pending'
        """, (initiator_id, initiator_id))
        
        existing_trade = cursor.fetchone()
        
        if existing_trade:
            await interaction.response.send_message(
                f"You already have an active trade (Trade #{existing_trade[0]}). "
                f"Complete or cancel that trade before starting a new one.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Check if target user already has an active trade
        cursor.execute("""
            SELECT trade_id FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) 
            AND status = 'pending'
        """, (recipient_id, recipient_id))
        
        if cursor.fetchone():
            await interaction.response.send_message(
                f"{player.display_name} already has an active trade. "
                f"Try again after they've completed their current trade.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Create new trade
        cursor.execute("""
            INSERT INTO trades (
                initiator_id, recipient_id, created_at, updated_at, status
            ) VALUES (?, ?, ?, ?, 'pending')
        """, (
            initiator_id, 
            recipient_id, 
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create and send trade notification
        embed = discord.Embed(
            title=f"New Trade Request (#{trade_id})",
            description=f"{interaction.user.display_name} wants to trade with {player.display_name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Instructions",
            value=(
                "1. Use `/trade_add [capture_id]` to add Veramon to the trade\n"
                "2. Use `/trade_remove [capture_id]` to remove Veramon\n"
                "3. Both players must add at least one Veramon\n"
                "4. Recipient can use the buttons below to accept or decline"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Initiator's Offer",
            value="No Veramon added yet",
            inline=True
        )
        
        embed.add_field(
            name="Recipient's Offer",
            value="No Veramon added yet",
            inline=True
        )
        
        embed.set_footer(text=f"Trade will expire in 5 minutes if not completed")
        
        # Create view with buttons
        view = TradeView(int(initiator_id), int(recipient_id), trade_id, self)
        self.active_trade_views[trade_id] = view
        
        # Send the message and store the view
        await interaction.response.send_message(
            content=f"{player.mention} - You've received a trade request!",
            embed=embed,
            view=view
        )
        
    @app_commands.command(name="trade_add", description="Add a Veramon to your current trade")
    @app_commands.describe(
        capture_id="The ID of the Veramon to add to the trade"
    )
    @require_permission_level(PermissionLevel.USER)
    async def trade_add(self, interaction: discord.Interaction, capture_id: int):
        """Add a Veramon to your current trade."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user has an active trade
        cursor.execute("""
            SELECT trade_id, initiator_id, recipient_id 
            FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) 
            AND status = 'pending'
        """, (user_id, user_id))
        
        trade = cursor.fetchone()
        
        if not trade:
            await interaction.response.send_message(
                "You don't have any active trades. Use `/trade_create` to start one.",
                ephemeral=True
            )
            conn.close()
            return
            
        trade_id, initiator_id, recipient_id = trade
        
        # Verify the Veramon belongs to the user
        cursor.execute("""
            SELECT id, veramon_name, shiny, nickname, level, active_form 
            FROM captures 
            WHERE id = ? AND user_id = ?
        """, (capture_id, user_id))
        
        veramon = cursor.fetchone()
        
        if not veramon:
            await interaction.response.send_message(
                f"You don't own a Veramon with ID {capture_id}.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Check if already in trade
        cursor.execute("""
            SELECT 1 FROM trade_items 
            WHERE trade_id = ? AND capture_id = ?
        """, (trade_id, capture_id))
        
        if cursor.fetchone():
            await interaction.response.send_message(
                f"This Veramon is already in the trade.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Determine user's role in trade
        user_role = "initiator" if user_id == initiator_id else "recipient"
        
        # Add to trade
        cursor.execute("""
            INSERT INTO trade_items (
                trade_id, capture_id, owner_id, added_at
            ) VALUES (?, ?, ?, ?)
        """, (
            trade_id,
            capture_id,
            user_id,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        
        # Get all items in the trade to update UI
        cursor.execute("""
            SELECT ti.capture_id, c.veramon_name, c.shiny, c.nickname, c.level, c.active_form, ti.owner_id
            FROM trade_items ti
            JOIN captures c ON ti.capture_id = c.id
            WHERE ti.trade_id = ?
            ORDER BY ti.added_at
        """, (trade_id,))
        
        trade_items = cursor.fetchall()
        
        # Group by owner
        initiator_items = [item for item in trade_items if item[5] == initiator_id]
        recipient_items = [item for item in trade_items if item[5] == recipient_id]
        
        conn.close()
        
        # Format Veramon lists
        def format_veramon_list(items):
            if not items:
                return "No Veramon added yet"
                
            result = ""
            for capture_id, name, shiny, nickname, level, active_form, _ in items:
                display_name = nickname if nickname else name
                shiny_star = "✨ " if shiny else ""
                result += f"• {shiny_star}**{display_name}** (Lvl {level}, ID: {capture_id}, Form: {active_form})\n"
            return result
        
        # Update the embed
        embed = discord.Embed(
            title=f"Trade Request (#{trade_id})",
            description=f"Trade between <@{initiator_id}> and <@{recipient_id}>",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Instructions",
            value=(
                "1. Use `/trade_add [capture_id]` to add Veramon to the trade\n"
                "2. Use `/trade_remove [capture_id]` to remove Veramon\n"
                "3. Both players must add at least one Veramon\n"
                "4. Recipient can use the buttons below to accept or decline"
            ),
            inline=False
        )
        
        embed.add_field(
            name=f"<@{initiator_id}>'s Offer",
            value=format_veramon_list(initiator_items),
            inline=True
        )
        
        embed.add_field(
            name=f"<@{recipient_id}>'s Offer",
            value=format_veramon_list(recipient_items),
            inline=True
        )
        
        embed.set_footer(text=f"Trade will expire in 5 minutes if not completed")
        
        # Needed to check if there's a valid view
        view = self.active_trade_views.get(trade_id)
        
        await interaction.response.send_message(
            f"Added Veramon to Trade #{trade_id}",
            embed=embed,
            view=view if view else None
        )
        
        # Trigger quest progress update
        try:
            quest_cog = self.bot.get_cog("QuestCog")
            if quest_cog:
                await quest_cog.update_quest_progress(
                    user_id, 
                    "TRADE_ADD", 
                    1, 
                    {
                        "veramon_name": veramon[1],
                        "shiny": bool(veramon[2]),
                        "level": veramon[4],
                        "active_form": veramon[5]
                    }
                )
        except Exception as e:
            print(f"Error updating quest progress: {e}")
        
    @app_commands.command(name="trade_remove", description="Remove a Veramon from your current trade")
    @app_commands.describe(
        capture_id="The ID of the Veramon to remove from the trade"
    )
    @require_permission_level(PermissionLevel.USER)
    async def trade_remove(self, interaction: discord.Interaction, capture_id: int):
        """Remove a Veramon from your current trade."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user has an active trade
        cursor.execute("""
            SELECT trade_id, initiator_id, recipient_id 
            FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) 
            AND status = 'pending'
        """, (user_id, user_id))
        
        trade = cursor.fetchone()
        
        if not trade:
            await interaction.response.send_message(
                "You don't have any active trades.",
                ephemeral=True
            )
            conn.close()
            return
            
        trade_id, initiator_id, recipient_id = trade
        
        # Verify the item is in the trade and belongs to the user
        cursor.execute("""
            SELECT 1 FROM trade_items 
            WHERE trade_id = ? AND capture_id = ? AND owner_id = ?
        """, (trade_id, capture_id, user_id))
        
        if not cursor.fetchone():
            await interaction.response.send_message(
                f"You don't have a Veramon with ID {capture_id} in this trade.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Remove from trade
        cursor.execute("""
            DELETE FROM trade_items 
            WHERE trade_id = ? AND capture_id = ?
        """, (trade_id, capture_id))
        
        conn.commit()
        
        # Get all items in the trade to update UI
        cursor.execute("""
            SELECT ti.capture_id, c.veramon_name, c.shiny, c.nickname, c.level, c.active_form, ti.owner_id
            FROM trade_items ti
            JOIN captures c ON ti.capture_id = c.id
            WHERE ti.trade_id = ?
            ORDER BY ti.added_at
        """, (trade_id,))
        
        trade_items = cursor.fetchall()
        
        # Group by owner
        initiator_items = [item for item in trade_items if item[5] == initiator_id]
        recipient_items = [item for item in trade_items if item[5] == recipient_id]
        
        conn.close()
        
        # Format Veramon lists
        def format_veramon_list(items):
            if not items:
                return "No Veramon added yet"
                
            result = ""
            for capture_id, name, shiny, nickname, level, active_form, _ in items:
                display_name = nickname if nickname else name
                shiny_star = "✨ " if shiny else ""
                result += f"• {shiny_star}**{display_name}** (Lvl {level}, ID: {capture_id}, Form: {active_form})\n"
            return result
        
        # Update the embed
        embed = discord.Embed(
            title=f"Trade Request (#{trade_id})",
            description=f"Trade between <@{initiator_id}> and <@{recipient_id}>",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Instructions",
            value=(
                "1. Use `/trade_add [capture_id]` to add Veramon to the trade\n"
                "2. Use `/trade_remove [capture_id]` to remove Veramon\n"
                "3. Both players must add at least one Veramon\n"
                "4. Recipient can use the buttons below to accept or decline"
            ),
            inline=False
        )
        
        embed.add_field(
            name=f"<@{initiator_id}>'s Offer",
            value=format_veramon_list(initiator_items),
            inline=True
        )
        
        embed.add_field(
            name=f"<@{recipient_id}>'s Offer",
            value=format_veramon_list(recipient_items),
            inline=True
        )
        
        embed.set_footer(text=f"Trade will expire in 5 minutes if not completed")
        
        # Needed to check if there's a valid view
        view = self.active_trade_views.get(trade_id)
        
        await interaction.response.send_message(
            f"Removed Veramon from Trade #{trade_id}",
            embed=embed,
            view=view if view else None
        )
        
    @app_commands.command(name="trade_cancel", description="Cancel your current trade")
    @require_permission_level(PermissionLevel.USER)
    async def trade_cancel(self, interaction: discord.Interaction):
        """Cancel your current trade."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user has an active trade
        cursor.execute("""
            SELECT trade_id, initiator_id 
            FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) 
            AND status = 'pending'
        """, (user_id, user_id))
        
        trade = cursor.fetchone()
        
        if not trade:
            await interaction.response.send_message(
                "You don't have any active trades to cancel.",
                ephemeral=True
            )
            conn.close()
            return
            
        trade_id, initiator_id = trade
        
        # Update trade status
        cursor.execute("""
            UPDATE trades 
            SET status = 'cancelled', 
                updated_at = ? 
            WHERE trade_id = ?
        """, (datetime.utcnow().isoformat(), trade_id))
        
        conn.commit()
        conn.close()
        
        # Clean up view if it exists
        if trade_id in self.active_trade_views:
            view = self.active_trade_views.pop(trade_id)
            view.stop()
        
        await interaction.response.send_message(f"Trade #{trade_id} has been cancelled.")
        
    @app_commands.command(name="trade_list", description="View your active and recent trades")
    @require_permission_level(PermissionLevel.USER)
    async def trade_list(self, interaction: discord.Interaction):
        """View your active and recent trades."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get active trade
        cursor.execute("""
            SELECT trade_id, initiator_id, recipient_id, created_at, status
            FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) 
            AND status = 'pending'
        """, (user_id, user_id))
        
        active_trade = cursor.fetchone()
        
        # Get recent trades (completed, declined, cancelled) - limit to last 5
        cursor.execute("""
            SELECT trade_id, initiator_id, recipient_id, created_at, updated_at, status
            FROM trades 
            WHERE (initiator_id = ? OR recipient_id = ?) 
            AND status != 'pending'
            ORDER BY updated_at DESC
            LIMIT 5
        """, (user_id, user_id))
        
        recent_trades = cursor.fetchall()
        
        conn.close()
        
        # Create embed
        embed = discord.Embed(
            title="Your Trades",
            description="Active and recent trade history",
            color=discord.Color.blue()
        )
        
        # Active trade section
        if active_trade:
            trade_id, initiator_id, recipient_id, created_at, status = active_trade
            
            # Format timestamp
            created_timestamp = int(datetime.fromisoformat(created_at).timestamp())
            
            # Format initiator/recipient info
            is_initiator = initiator_id == user_id
            partner_id = recipient_id if is_initiator else initiator_id
            role = "Initiator" if is_initiator else "Recipient"
            
            embed.add_field(
                name="Active Trade",
                value=(
                    f"**Trade #{trade_id}**\n"
                    f"• Status: **{status.capitalize()}**\n"
                    f"• Role: **{role}**\n"
                    f"• Partner: <@{partner_id}>\n"
                    f"• Created: <t:{created_timestamp}:R>\n"
                    f"• Use `/trade_add` or `/trade_remove` to modify."
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="Active Trade",
                value="You have no active trades. Use `/trade_create` to start one.",
                inline=False
            )
            
        # Recent trades section
        if recent_trades:
            recent_text = ""
            
            for trade_id, initiator_id, recipient_id, created_at, updated_at, status in recent_trades:
                # Format timestamp
                updated_timestamp = int(datetime.fromisoformat(updated_at).timestamp())
                
                # Format initiator/recipient info
                is_initiator = initiator_id == user_id
                partner_id = recipient_id if is_initiator else initiator_id
                
                recent_text += (
                    f"**Trade #{trade_id}** with <@{partner_id}>\n"
                    f"• Status: **{status.capitalize()}**\n"
                    f"• Completed: <t:{updated_timestamp}:R>\n\n"
                )
                
            embed.add_field(
                name="Recent Trades",
                value=recent_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Recent Trades",
                value="You have no recent trade history.",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)
        
    async def execute_trade(self, interaction: discord.Interaction, trade_id: int):
        """Execute a trade when accepted."""
        # Get the trade details
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT initiator_id, recipient_id, status
            FROM trades
            WHERE trade_id = ?
        """, (trade_id,))
        
        trade = cursor.fetchone()
        
        if not trade:
            await interaction.followup.send("Trade not found.")
            conn.close()
            return
            
        initiator_id, recipient_id, status = trade
        
        if status != 'pending':
            await interaction.followup.send(f"This trade is already {status}.")
            conn.close()
            return
            
        # Verify both sides have at least one item
        cursor.execute("""
            SELECT owner_id, COUNT(*)
            FROM trade_items
            WHERE trade_id = ?
            GROUP BY owner_id
        """, (trade_id,))
        
        item_counts = cursor.fetchall()
        item_counts_dict = {owner_id: count for owner_id, count in item_counts}
        
        if initiator_id not in item_counts_dict or recipient_id not in item_counts_dict:
            await interaction.followup.send("Both traders must add at least one Veramon to complete the trade.")
            conn.close()
            return
            
        # Get trade items
        cursor.execute("""
            SELECT capture_id, owner_id
            FROM trade_items
            WHERE trade_id = ?
        """, (trade_id,))
        
        trade_items = cursor.fetchall()
        
        # Begin transaction
        try:
            # Transfer ownership of all Veramon
            for capture_id, owner_id in trade_items:
                new_owner_id = recipient_id if owner_id == initiator_id else initiator_id
                
                cursor.execute("""
                    UPDATE captures
                    SET user_id = ?, 
                        active = 0  -- Reset active status when traded
                    WHERE id = ?
                """, (new_owner_id, capture_id))
                
            # Update trade status
            cursor.execute("""
                UPDATE trades 
                SET status = 'completed', 
                    updated_at = ? 
                WHERE trade_id = ?
            """, (datetime.utcnow().isoformat(), trade_id))
            
            conn.commit()
            
            # Get traded Veramon details for the success message
            cursor.execute("""
                SELECT c.id, c.veramon_name, c.shiny, c.nickname, c.level, c.active_form, ti.owner_id
                FROM trade_items ti
                JOIN captures c ON ti.capture_id = c.id
                WHERE ti.trade_id = ?
            """, (trade_id,))
            
            traded_veramon = cursor.fetchall()
            
            # Group by original owner
            initiator_gave = [v for v in traded_veramon if v[5] == initiator_id]
            recipient_gave = [v for v in traded_veramon if v[5] == recipient_id]
            
            conn.close()
            
            # Format traded Veramon lists
            def format_veramon_list(items):
                result = ""
                for capture_id, name, shiny, nickname, level, active_form, _ in items:
                    display_name = nickname if nickname else name
                    shiny_star = "✨ " if shiny else ""
                    result += f"• {shiny_star}**{display_name}** (Lvl {level}, ID: {capture_id}, Form: {active_form})\n"
                return result
            
            # Create success embed
            embed = discord.Embed(
                title=f"Trade #{trade_id} Complete!",
                description="The trade was successful! Veramon ownership has been transferred.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name=f"<@{initiator_id}> Received",
                value=format_veramon_list(recipient_gave),
                inline=True
            )
            
            embed.add_field(
                name=f"<@{recipient_id}> Received",
                value=format_veramon_list(initiator_gave),
                inline=True
            )
            
            # Clean up any active view
            if trade_id in self.active_trade_views:
                view = self.active_trade_views.pop(trade_id)
                view.stop()
            
            # Update quest progress for both participants
            quest_updates = []
            try:
                economy_cog = self.bot.get_cog("EconomyCog")
                if economy_cog:
                    # Update trade quests for initiator
                    initiator_quests = await economy_cog.update_quest_progress(
                        initiator_id, "trade", 1
                    )
                    if initiator_quests:
                        quest_updates.append((initiator_id, initiator_quests))
                    
                    # Update trade quests for recipient
                    recipient_quests = await economy_cog.update_quest_progress(
                        recipient_id, "trade", 1
                    )
                    if recipient_quests:
                        quest_updates.append((recipient_id, recipient_quests))
            except Exception as e:
                print(f"Error updating quest progress: {e}")
            
            # Update leaderboard stats
            try:
                leaderboard_cog = self.bot.get_cog("LeaderboardCog")
                if leaderboard_cog:
                    # Update trade count for both participants
                    await leaderboard_cog.update_trades_stat(initiator_id, 1)
                    await leaderboard_cog.update_trades_stat(recipient_id, 1)
            except Exception as e:
                print(f"Error updating leaderboard stats: {e}")
                
            # If any quests were completed, add to the embed
            if quest_updates:
                for user_id, completed_quests in quest_updates:
                    quest_text = ""
                    for quest in completed_quests:
                        quest_text += f"• {quest['quest_id']}: +{quest['token_reward']} tokens, +{quest['xp_reward']} XP\n"
                    
                    if quest_text:
                        embed.add_field(
                            name=f"🎯 <@{user_id}> Completed Quests!",
                            value=quest_text,
                            inline=False
                        )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            # Roll back on error
            conn.rollback()
            conn.close()
            await interaction.followup.send(f"Error during trade: {str(e)}")
        
async def setup(bot: commands.Bot):
    await bot.add_cog(TradingCog(bot))
