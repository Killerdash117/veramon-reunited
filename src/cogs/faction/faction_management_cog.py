"""
Faction Management Cog for Veramon Reunited

Provides interactive UI for managing factions, viewing faction details,
and handling faction members.
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal, Union, Any

from src.db.db import get_connection
from src.core.faction_economy import get_faction_economy
from src.models.permissions import require_permission_level, PermissionLevel, is_admin

class FactionManagementView(discord.ui.View):
    """Interactive view for faction management."""
    
    def __init__(self, cog, interaction, faction_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.original_interaction = interaction
        self.faction_id = faction_id
        self.user_id = str(interaction.user.id)
        
    async def on_timeout(self):
        """Handle timeout by disabling all buttons."""
        for item in self.children:
            item.disabled = True
        
        try:
            await self.message.edit(view=self)
        except:
            pass
            
    @discord.ui.button(label="Members", style=discord.ButtonStyle.primary, emoji="👥")
    async def members_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Display faction members."""
        await interaction.response.defer(ephemeral=False)
        embed = await self.cog.create_members_embed(self.faction_id, interaction.user)
        await interaction.followup.send(embed=embed, ephemeral=False)
        
    @discord.ui.button(label="Stats", style=discord.ButtonStyle.primary, emoji="📊")
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Display faction statistics."""
        await interaction.response.defer(ephemeral=False)
        embed = await self.cog.create_stats_embed(self.faction_id)
        await interaction.followup.send(embed=embed, ephemeral=False)
        
    @discord.ui.button(label="Buffs", style=discord.ButtonStyle.primary, emoji="⚡")
    async def buffs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Display active faction buffs."""
        await interaction.response.defer(ephemeral=False)
        embed = await self.cog.create_buffs_embed(self.faction_id)
        await interaction.followup.send(embed=embed, ephemeral=False)
        
    @discord.ui.button(label="History", style=discord.ButtonStyle.primary, emoji="📜")
    async def history_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Display faction history."""
        await interaction.response.defer(ephemeral=False)
        embed = await self.cog.create_history_embed(self.faction_id)
        await interaction.followup.send(embed=embed, ephemeral=False)

class FactionManagementCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.faction_economy = get_faction_economy()
        
    @app_commands.command(name="faction_info", description="View detailed information about your faction")
    async def faction_info(self, interaction: discord.Interaction):
        """View detailed information about your faction with an interactive UI."""
        user_id = str(interaction.user.id)
        
        # Check if user is in a faction
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.faction_id, f.name, f.description, f.color, f.faction_level, 
                   f.faction_xp, f.created_date, f.treasury, f.member_count, f.leader_id
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_data = cursor.fetchone()
        if not faction_data:
            await interaction.response.send_message(
                "You are not in a faction!",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, name, description, color, level, xp, created_date, treasury, member_count, leader_id = faction_data
        
        # Get level progress
        _, current_xp, xp_for_next = self.faction_economy.get_faction_level(faction_id)
        
        # Create main faction info embed
        embed = discord.Embed(
            title=f"🏰 {name}",
            description=description,
            color=int(color, 16) if color else 0x5865F2
        )
        
        # Add faction details
        embed.add_field(
            name="Level",
            value=f"**{level}** ({current_xp:,}/{xp_for_next:,} XP)",
            inline=True
        )
        
        embed.add_field(
            name="Treasury",
            value=f"{treasury:,} tokens",
            inline=True
        )
        
        embed.add_field(
            name="Members",
            value=f"{member_count} members",
            inline=True
        )
        
        # Calculate faction age
        created_dt = datetime.fromisoformat(created_date) if created_date else datetime.now()
        days_old = (datetime.now() - created_dt).days
        
        embed.add_field(
            name="Founded",
            value=f"<t:{int(created_dt.timestamp())}:R> ({days_old} days ago)",
            inline=True
        )
        
        # Get territory count
        cursor.execute("""
            SELECT COUNT(*) FROM faction_territories
            WHERE controlling_faction_id = ?
        """, (faction_id,))
        
        territory_count = cursor.fetchone()[0]
        
        embed.add_field(
            name="Territories",
            value=f"{territory_count} controlled",
            inline=True
        )
        
        # Get user's rank in the faction
        cursor.execute("""
            SELECT r.name, r.can_manage_members, r.can_manage_wars
            FROM faction_members m
            JOIN faction_ranks r ON m.faction_id = r.faction_id AND m.rank_id = r.rank_id
            WHERE m.user_id = ? AND m.faction_id = ?
        """, (user_id, faction_id))
        
        rank_data = cursor.fetchone()
        if rank_data:
            rank_name, can_manage_members, can_manage_wars = rank_data
            embed.add_field(
                name="Your Rank",
                value=f"{rank_name}",
                inline=True
            )
        
        # Get top contributor
        cursor.execute("""
            SELECT u.username, SUM(fc.amount) as total
            FROM faction_contributions fc
            JOIN users u ON fc.user_id = u.user_id
            WHERE fc.faction_id = ?
            GROUP BY fc.user_id
            ORDER BY total DESC
            LIMIT 1
        """, (faction_id,))
        
        top_contributor = cursor.fetchone()
        if top_contributor:
            contributor_name, contribution_amount = top_contributor
            embed.add_field(
                name="Top Contributor",
                value=f"{contributor_name} ({contribution_amount:,} tokens)",
                inline=False
            )
            
        # Add active buff count
        cursor.execute("""
            SELECT COUNT(*) FROM faction_shop_purchases
            WHERE faction_id = ? AND item_id LIKE 'faction_%_booster'
            AND timestamp + duration > datetime('now')
        """, (faction_id,))
        
        active_buffs = cursor.fetchone()[0]
        
        if active_buffs > 0:
            embed.add_field(
                name="Active Buffs",
                value=f"{active_buffs} faction-wide buffs active",
                inline=False
            )
            
        # Set footer with additional info
        embed.set_footer(text="Click the buttons below to view more information about your faction")
        
        conn.close()
        
        # Create interactive view
        view = FactionManagementView(self, interaction, faction_id)
        await interaction.response.send_message(embed=embed, view=view)
    
    async def create_members_embed(self, faction_id: int, user: discord.User) -> discord.Embed:
        """Create an embed showing faction members."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get faction info
        cursor.execute("""
            SELECT name, color FROM factions
            WHERE faction_id = ?
        """, (faction_id,))
        
        faction_name, color = cursor.fetchone()
        
        # Get members
        cursor.execute("""
            SELECT u.username, r.name as rank_name, fm.joined_date,
                   u.user_id = f.leader_id as is_leader,
                   u.last_active
            FROM faction_members fm
            JOIN users u ON fm.user_id = u.user_id
            JOIN faction_ranks r ON fm.faction_id = r.faction_id AND fm.rank_id = r.rank_id
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.faction_id = ?
            ORDER BY is_leader DESC, r.rank_id DESC, fm.joined_date ASC
        """, (faction_id,))
        
        members = cursor.fetchall()
        
        # Create embed
        embed = discord.Embed(
            title=f"👥 {faction_name} Members",
            description=f"This faction has {len(members)} members",
            color=int(color, 16) if color else 0x5865F2
        )
        
        # Format members list
        members_text = ""
        for i, (username, rank, joined_date, is_leader, last_active) in enumerate(members):
            # Format joined date
            joined_dt = datetime.fromisoformat(joined_date) if joined_date else datetime.now()
            joined_timestamp = int(joined_dt.timestamp())
            
            # Format last active
            active_text = ""
            if last_active:
                active_dt = datetime.fromisoformat(last_active)
                active_timestamp = int(active_dt.timestamp())
                active_text = f"• Active <t:{active_timestamp}:R>"
            
            # Add leader crown or member number
            prefix = "👑 " if is_leader else f"{i+1}. "
            
            members_text += f"{prefix}**{username}** ({rank})\n"
            members_text += f"Joined <t:{joined_timestamp}:R> {active_text}\n\n"
            
            # Split into multiple fields if too long
            if len(members_text) > 900 or i == len(members) - 1:
                embed.add_field(
                    name=f"Members {i-9 if i > 9 else 1}-{i+1}",
                    value=members_text,
                    inline=False
                )
                members_text = ""
                
        conn.close()
        return embed
        
    async def create_stats_embed(self, faction_id: int) -> discord.Embed:
        """Create an embed showing faction statistics."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get faction info
        cursor.execute("""
            SELECT name, color, faction_level, treasury, created_date
            FROM factions
            WHERE faction_id = ?
        """, (faction_id,))
        
        faction_name, color, level, treasury, created_date = cursor.fetchone()
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 {faction_name} Statistics",
            description="Detailed statistics about this faction",
            color=int(color, 16) if color else 0x5865F2
        )
        
        # Get total contribution
        cursor.execute("""
            SELECT SUM(amount) FROM faction_contributions
            WHERE faction_id = ?
        """, (faction_id,))
        
        total_contribution = cursor.fetchone()[0] or 0
        
        # Get territory stats
        cursor.execute("""
            SELECT COUNT(*), SUM(daily_token_bonus), SUM(daily_xp_bonus)
            FROM faction_territories
            WHERE controlling_faction_id = ?
        """, (faction_id,))
        
        territory_count, token_bonus, xp_bonus = cursor.fetchone()
        territory_count = territory_count or 0
        token_bonus = token_bonus or 0
        xp_bonus = xp_bonus or 0
        
        # Get war stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_wars,
                SUM(CASE WHEN winner_faction_id = ? THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN winner_faction_id IS NOT NULL AND winner_faction_id != ? THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN winner_faction_id IS NULL THEN 1 ELSE 0 END) as draws
            FROM faction_wars
            WHERE (attacker_faction_id = ? OR defender_faction_id = ?) AND status = 'ended'
        """, (faction_id, faction_id, faction_id, faction_id))
        
        war_stats = cursor.fetchone()
        total_wars = war_stats[0] or 0
        wins = war_stats[1] or 0
        losses = war_stats[2] or 0
        draws = war_stats[3] or 0
        
        # Add financial stats
        embed.add_field(
            name="Financial Stats",
            value=(
                f"**Current Treasury**: {treasury:,} tokens\n"
                f"**Total Contributions**: {total_contribution:,} tokens\n"
                f"**Daily Territory Income**: {token_bonus:,} tokens"
            ),
            inline=False
        )
        
        # Add level stats
        embed.add_field(
            name="Progression",
            value=(
                f"**Faction Level**: {level}\n"
                f"**Controlled Territories**: {territory_count}\n"
                f"**Daily XP from Territories**: {xp_bonus:,} XP"
            ),
            inline=False
        )
        
        # Add war stats
        win_rate = (wins / total_wars) * 100 if total_wars > 0 else 0
        
        embed.add_field(
            name="War Record",
            value=(
                f"**Wars Fought**: {total_wars}\n"
                f"**Victories**: {wins}\n"
                f"**Defeats**: {losses}\n"
                f"**Draws**: {draws}\n"
                f"**Win Rate**: {win_rate:.1f}%"
            ),
            inline=False
        )
        
        conn.close()
        return embed
        
    async def create_buffs_embed(self, faction_id: int) -> discord.Embed:
        """Create an embed showing active faction buffs."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get faction info
        cursor.execute("""
            SELECT name, color FROM factions
            WHERE faction_id = ?
        """, (faction_id,))
        
        faction_name, color = cursor.fetchone()
        
        # Create embed
        embed = discord.Embed(
            title=f"⚡ {faction_name} Active Buffs",
            description="Current faction-wide buffs and their effects",
            color=int(color, 16) if color else 0x5865F2
        )
        
        # Get active buffs
        cursor.execute("""
            SELECT i.name, i.effect, i.multiplier, i.icon,
                   p.timestamp, p.duration,
                   datetime(p.timestamp, '+' || p.duration || ' seconds') as expiry,
                   u.username as buyer
            FROM faction_shop_purchases p
            JOIN faction_shop_items i ON p.item_id = i.item_id
            JOIN users u ON p.user_id = u.user_id
            WHERE p.faction_id = ? 
            AND datetime(p.timestamp, '+' || p.duration || ' seconds') > datetime('now')
            AND i.category = 'buff'
            ORDER BY expiry ASC
        """, (faction_id,))
        
        buffs = cursor.fetchall()
        
        if not buffs:
            embed.add_field(
                name="No Active Buffs",
                value=(
                    "Your faction has no active buffs right now.\n"
                    "Purchase buff items from the faction shop with `/faction_shop`!"
                ),
                inline=False
            )
        else:
            # Add each buff to the embed
            for name, effect, multiplier, icon, timestamp, duration, expiry, buyer in buffs:
                # Calculate remaining time
                expiry_dt = datetime.fromisoformat(expiry)
                timestamp_dt = datetime.fromisoformat(timestamp)
                
                # Format effect description
                effect_desc = ""
                if effect == "faction_token_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% tokens for all members"
                elif effect == "faction_xp_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% XP for all members"
                elif effect == "faction_catch_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% catch rate for all members"
                elif effect == "faction_battle_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% battle rewards for all members"
                elif effect == "faction_shiny_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% shiny chance for all members"
                elif effect == "faction_rare_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% rare encounter rate"
                elif effect == "faction_skill_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% move effectiveness"
                elif effect == "donation_boost":
                    effect_desc = f"+{(multiplier-1)*100:.0f}% treasury donation XP"
                else:
                    effect_desc = f"Multiplier: {multiplier}x"
                
                embed.add_field(
                    name=f"{icon} {name}",
                    value=(
                        f"**Effect**: {effect_desc}\n"
                        f"**Expires**: <t:{int(expiry_dt.timestamp())}:R>\n"
                        f"**Activated by**: {buyer}"
                    ),
                    inline=False
                )
        
        conn.close()
        return embed
        
    async def create_history_embed(self, faction_id: int) -> discord.Embed:
        """Create an embed showing faction history."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get faction info
        cursor.execute("""
            SELECT name, color FROM factions
            WHERE faction_id = ?
        """, (faction_id,))
        
        faction_name, color = cursor.fetchone()
        
        # Create embed
        embed = discord.Embed(
            title=f"📜 {faction_name} History",
            description="Recent events and milestones",
            color=int(color, 16) if color else 0x5865F2
        )
        
        # Get recent history (last 15 events)
        cursor.execute("""
            SELECT h.event_type, h.description, h.timestamp, u.username
            FROM faction_history h
            LEFT JOIN users u ON h.user_id = u.user_id
            WHERE h.faction_id = ?
            ORDER BY h.timestamp DESC
            LIMIT 15
        """, (faction_id,))
        
        history = cursor.fetchall()
        
        if not history:
            embed.add_field(
                name="No History Found",
                value="No events have been recorded for this faction yet.",
                inline=False
            )
        else:
            # Group by event type
            events_by_type = {}
            for event_type, description, timestamp, username in history:
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                    
                # Format timestamp
                timestamp_dt = datetime.fromisoformat(timestamp) if timestamp else datetime.now()
                
                events_by_type[event_type].append({
                    "description": description,
                    "timestamp": timestamp_dt,
                    "username": username
                })
            
            # Add each event type
            for event_type, events in events_by_type.items():
                # Format event type
                title = event_type.replace("_", " ").title()
                
                # Format events text
                events_text = ""
                for event in events:
                    timestamp_str = f"<t:{int(event['timestamp'].timestamp())}:R>"
                    if event["username"]:
                        events_text += f"• {event['description']} by **{event['username']}** {timestamp_str}\n\n"
                    else:
                        events_text += f"• {event['description']} {timestamp_str}\n\n"
                
                embed.add_field(
                    name=title,
                    value=events_text,
                    inline=False
                )
        
        conn.close()
        return embed

async def setup(bot: commands.Bot):
    await bot.add_cog(FactionManagementCog(bot))
