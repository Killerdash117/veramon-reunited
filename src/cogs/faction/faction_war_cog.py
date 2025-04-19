"""
Faction War and Territory Management Cog for Veramon Reunited

Provides commands for declaring faction wars, managing territories,
and viewing war status.
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal, Union, Any

from src.db.db import get_connection
from src.core.faction_economy import get_faction_economy
from src.core.faction_war import get_faction_war, FactionWar
from src.models.permissions import require_permission_level, PermissionLevel

class FactionWarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.faction_war = get_faction_war()
        self.faction_economy = get_faction_economy()
        
    async def cog_load(self):
        """Initialize database when cog loads."""
        await self.faction_war.initialize_database()

    @app_commands.command(name="faction_territories", description="View all territories and their controlling factions")
    async def faction_territories(self, interaction: discord.Interaction):
        """View all territories and their controlling factions."""
        # Check if user is in a faction
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.faction_id, f.name, f.color
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        user_faction = cursor.fetchone()
        
        # Get all territories
        territories = await self.faction_war.get_territories()
        
        if not territories:
            await interaction.response.send_message(
                "There are no territories available at this time.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Create embed
        embed = discord.Embed(
            title="📍 Faction Territories",
            description="These territories provide resources and bonuses to controlling factions.",
            color=int(user_faction[2], 16) if user_faction else 0x5865F2
        )
        
        # Group territories by controlling faction
        controlled_territories = {}
        uncontrolled_territories = []
        
        for territory in territories:
            if territory["controlling_faction"]:
                faction_id = territory["controlling_faction"]["faction_id"]
                if faction_id not in controlled_territories:
                    controlled_territories[faction_id] = []
                controlled_territories[faction_id].append(territory)
            else:
                uncontrolled_territories.append(territory)
        
        # Add territories controlled by user's faction first
        if user_faction and user_faction[0] in controlled_territories:
            faction_id = user_faction[0]
            faction_territories = controlled_territories[faction_id]
            
            territory_text = ""
            for territory in faction_territories:
                capture_time = territory["capture_date"]
                if capture_time:
                    capture_time = f"Captured <t:{int(datetime.fromisoformat(capture_time).timestamp())}:R>"
                else:
                    capture_time = "Recently captured"
                    
                territory_text += f"**{territory['name']}** - {territory['description']}\n"
                territory_text += f"• Daily Bonuses: {territory['daily_token_bonus']} tokens, {territory['daily_xp_bonus']} XP\n"
                territory_text += f"• {capture_time}\n\n"
            
            embed.add_field(
                name=f"🏆 Your Faction's Territories",
                value=territory_text if territory_text else "None",
                inline=False
            )
            
            # Remove these from the display list
            del controlled_territories[faction_id]
        
        # Add other controlled territories
        for faction_id, faction_territories in controlled_territories.items():
            faction_name = faction_territories[0]["controlling_faction"]["name"]
            territory_text = ""
            
            for territory in faction_territories:
                territory_text += f"**{territory['name']}** - {territory['description']}\n"
                territory_text += f"• Daily Bonuses: {territory['daily_token_bonus']} tokens, {territory['daily_xp_bonus']} XP\n\n"
            
            embed.add_field(
                name=f"🏰 {faction_name}'s Territories",
                value=territory_text,
                inline=False
            )
        
        # Add uncontrolled territories
        if uncontrolled_territories:
            territory_text = ""
            for territory in uncontrolled_territories:
                territory_text += f"**{territory['name']}** - {territory['description']}\n"
                territory_text += f"• Daily Bonuses: {territory['daily_token_bonus']} tokens, {territory['daily_xp_bonus']} XP\n\n"
            
            embed.add_field(
                name="⚔️ Unclaimed Territories",
                value=territory_text,
                inline=False
            )
        
        # Add information about claiming territories
        embed.add_field(
            name="📌 How to Claim Territories",
            value="1. Purchase a Territory Banner from the faction shop\n"
                  "2. Use `/faction_claim_territory` to claim an unclaimed territory\n"
                  "3. Defend your territory from rival factions\n"
                  "4. Collect daily rewards based on controlled territories",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        conn.close()
        
    @app_commands.command(name="faction_declare_war", description="Declare war on another faction")
    @app_commands.describe(
        target_faction="ID number of the faction to declare war on",
        territory="ID number of the territory to fight over (optional)"
    )
    async def faction_declare_war(
        self, 
        interaction: discord.Interaction, 
        target_faction: int,
        territory: Optional[int] = None
    ):
        """Declare war on another faction, optionally fighting over a territory."""
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is in a faction and has permission to declare war
        cursor.execute("""
            SELECT f.faction_id, f.name, f.color, fm.rank_id
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        user_faction = cursor.fetchone()
        if not user_faction:
            await interaction.response.send_message(
                "You need to be in a faction to declare war!",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, faction_color, rank_id = user_faction
        
        # Check if user has permission to declare war
        cursor.execute("""
            SELECT can_manage_wars FROM faction_ranks
            WHERE faction_id = ? AND rank_id = ?
        """, (faction_id, rank_id))
        
        rank_permissions = cursor.fetchone()
        if not rank_permissions or rank_permissions[0] != 1:
            await interaction.response.send_message(
                "You don't have permission to declare war. Only faction leaders and officers can do this.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Check if target faction exists
        cursor.execute("SELECT name FROM factions WHERE faction_id = ?", (target_faction,))
        target_faction_data = cursor.fetchone()
        
        if not target_faction_data:
            await interaction.response.send_message(
                f"Faction ID {target_faction} doesn't exist.",
                ephemeral=True
            )
            conn.close()
            return
            
        target_faction_name = target_faction_data[0]
        
        # Check if territory exists if specified
        territory_name = None
        if territory:
            cursor.execute("SELECT name FROM faction_territories WHERE territory_id = ?", (territory,))
            territory_data = cursor.fetchone()
            
            if not territory_data:
                await interaction.response.send_message(
                    f"Territory ID {territory} doesn't exist.",
                    ephemeral=True
                )
                conn.close()
                return
                
            territory_name = territory_data[0]
            
            # Check if faction has the required item (War Banner)
            has_banner = False
            cursor.execute("""
                SELECT COUNT(*) FROM faction_shop_purchases
                WHERE faction_id = ? AND item_id = 'faction_war_banner' AND uses_remaining > 0
            """, (faction_id,))
            
            banner_count = cursor.fetchone()[0]
            if banner_count == 0:
                await interaction.response.send_message(
                    "Your faction needs to purchase a War Banner from the faction shop before declaring war.",
                    ephemeral=True
                )
                conn.close()
                return
            
            # Use one charge of the War Banner
            cursor.execute("""
                UPDATE faction_shop_purchases
                SET uses_remaining = uses_remaining - 1
                WHERE faction_id = ? AND item_id = 'faction_war_banner' AND uses_remaining > 0
                LIMIT 1
            """, (faction_id,))
        
        conn.close()
        
        # Declare war
        result = await self.faction_war.declare_war(faction_id, target_faction, territory)
        
        if not result["success"]:
            await interaction.response.send_message(
                f"Failed to declare war: {result['error']}",
                ephemeral=True
            )
            return
        
        # Create embed notification
        embed = discord.Embed(
            title="⚔️ Faction War Declared!",
            description=f"**{faction_name}** has declared war on **{target_faction_name}**!",
            color=int(faction_color, 16) if faction_color else 0xFF0000
        )
        
        embed.add_field(
            name="War Details",
            value=(
                f"• **Attacker**: {faction_name}\n"
                f"• **Defender**: {target_faction_name}\n"
                f"• **Started**: <t:{int(datetime.fromisoformat(result['start_time']).timestamp())}:F>\n"
                f"• **Ends**: <t:{int(datetime.fromisoformat(result['end_time']).timestamp())}:F>\n"
                f"• **Duration**: <t:{int(datetime.fromisoformat(result['end_time']).timestamp())}:R>\n"
                f"• **Territory**: {territory_name if territory_name else 'None (Honor War)'}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="How to Participate",
            value=(
                "Members can contribute to their faction's war effort by:\n"
                "• Winning battles against members of the opposing faction\n"
                "• Completing PvE battles while the war is active\n"
                "• Participating in raid battles\n"
                "All these activities award war points to your faction!"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"War ID: {result['war_id']} • Use /faction_war_status to check ongoing wars")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="faction_war_status", description="Check the status of active faction wars")
    async def faction_war_status(self, interaction: discord.Interaction):
        """Check the status of all active faction wars."""
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is in a faction
        cursor.execute("""
            SELECT f.faction_id, f.name, f.color
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        user_faction = cursor.fetchone()
        conn.close()
        
        # Get active wars
        active_wars = await self.faction_war.get_active_wars()
        
        if not active_wars:
            await interaction.response.send_message(
                "There are no active faction wars at this time.",
                ephemeral=True
            )
            return
            
        # Create embed
        embed = discord.Embed(
            title="⚔️ Active Faction Wars",
            description="Current ongoing conflicts between factions.",
            color=int(user_faction[2], 16) if user_faction else 0x5865F2
        )
        
        # Process each war
        for war in active_wars:
            # Highlight user's faction's war if applicable
            is_user_war = False
            if user_faction:
                if user_faction[0] == war["attacker"]["faction_id"] or user_faction[0] == war["defender"]["faction_id"]:
                    is_user_war = True
            
            # Calculate time remaining
            end_time = datetime.fromisoformat(war["end_time"])
            time_remaining = end_time - datetime.now()
            hours_remaining = int(time_remaining.total_seconds() / 3600)
            minutes_remaining = int((time_remaining.total_seconds() % 3600) / 60)
            
            title_prefix = "🔥 " if is_user_war else ""
            territory_text = f"Fighting for: **{war['territory']['name']}**\n" if war["territory"] else "Honor War (No Territory)\n"
            
            embed.add_field(
                name=f"{title_prefix}{war['attacker']['name']} vs {war['defender']['name']}",
                value=(
                    f"{territory_text}"
                    f"**Score**: {war['attacker']['score']} - {war['defender']['score']}\n"
                    f"**Time Remaining**: {hours_remaining}h {minutes_remaining}m\n"
                    f"**End Time**: <t:{int(end_time.timestamp())}:R>\n"
                    f"**War ID**: {war['war_id']}"
                ),
                inline=False
            )
        
        # Add helpful information about contributing to wars
        embed.add_field(
            name="📋 How to Contribute",
            value=(
                "• **Battle PvP**: Win battles against opposing faction members (+10 points)\n"
                "• **Battle PvE**: Complete trainer battles during wars (+5 points)\n"
                "• **Join Raids**: Participate in faction raids (+15 points)\n"
                "• **Contribute Resources**: Donate to your faction's war effort"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="faction_claim_territory", description="Claim an uncontrolled territory for your faction")
    @app_commands.describe(
        territory_id="ID number of the territory to claim"
    )
    async def faction_claim_territory(self, interaction: discord.Interaction, territory_id: int):
        """Claim an uncontrolled territory for your faction."""
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is in a faction and has permission
        cursor.execute("""
            SELECT f.faction_id, f.name, f.color, fm.rank_id
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        user_faction = cursor.fetchone()
        if not user_faction:
            await interaction.response.send_message(
                "You need to be in a faction to claim territories!",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, faction_color, rank_id = user_faction
        
        # Check if user has permission
        cursor.execute("""
            SELECT can_manage_wars FROM faction_ranks
            WHERE faction_id = ? AND rank_id = ?
        """, (faction_id, rank_id))
        
        rank_permissions = cursor.fetchone()
        if not rank_permissions or rank_permissions[0] != 1:
            await interaction.response.send_message(
                "You don't have permission to claim territories. Only faction leaders and officers can do this.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Check if territory exists and is unclaimed
        cursor.execute("""
            SELECT name, controlling_faction_id 
            FROM faction_territories 
            WHERE territory_id = ?
        """, (territory_id,))
        
        territory_data = cursor.fetchone()
        if not territory_data:
            await interaction.response.send_message(
                f"Territory ID {territory_id} doesn't exist.",
                ephemeral=True
            )
            conn.close()
            return
            
        territory_name, controlling_faction = territory_data
        
        if controlling_faction is not None:
            cursor.execute("SELECT name FROM factions WHERE faction_id = ?", (controlling_faction,))
            controller_name = cursor.fetchone()[0]
            
            await interaction.response.send_message(
                f"Territory '{territory_name}' is already controlled by {controller_name}. "
                f"You need to declare war to capture it from them.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Check if the faction has the required item (Territory Banner)
        cursor.execute("""
            SELECT COUNT(*) FROM faction_shop_purchases
            WHERE faction_id = ? AND item_id = 'faction_territory_banner' AND uses_remaining > 0
        """, (faction_id,))
        
        banner_count = cursor.fetchone()[0]
        if banner_count == 0:
            await interaction.response.send_message(
                "Your faction needs to purchase a Territory Banner from the faction shop before claiming a territory.",
                ephemeral=True
            )
            conn.close()
            return
        
        # All checks passed, claim the territory
        try:
            # Use one charge of the Territory Banner
            cursor.execute("""
                UPDATE faction_shop_purchases
                SET uses_remaining = uses_remaining - 1
                WHERE faction_id = ? AND item_id = 'faction_territory_banner' AND uses_remaining > 0
                LIMIT 1
            """, (faction_id,))
            
            # Update territory ownership
            cursor.execute("""
                UPDATE faction_territories
                SET controlling_faction_id = ?, capture_date = datetime('now')
                WHERE territory_id = ?
            """, (faction_id, territory_id))
            
            # Add faction XP reward for claiming territory
            xp_reward = 2000
            await self.faction_economy.add_faction_xp(faction_id, xp_reward)
            
            # Add record to faction history
            cursor.execute("""
                INSERT INTO faction_history (faction_id, event_type, description, timestamp)
                VALUES (?, 'territory_claimed', ?, datetime('now'))
            """, (faction_id, f"Claimed territory '{territory_name}'"))
            
            conn.commit()
            
            # Create success embed
            embed = discord.Embed(
                title="🏁 Territory Claimed!",
                description=f"**{faction_name}** has successfully claimed **{territory_name}**!",
                color=int(faction_color, 16) if faction_color else 0x00FF00
            )
            
            # Get territory details
            cursor.execute("""
                SELECT daily_token_bonus, daily_xp_bonus, biome_type, exclusive_veramon
                FROM faction_territories
                WHERE territory_id = ?
            """, (territory_id,))
            
            territory_details = cursor.fetchone()
            token_bonus, xp_bonus, biome_type, exclusive_veramon = territory_details
            
            embed.add_field(
                name="Territory Benefits",
                value=(
                    f"• Daily Token Bonus: **{token_bonus} tokens**\n"
                    f"• Daily XP Bonus: **{xp_bonus} XP**\n"
                    f"• Biome Type: **{biome_type}**\n"
                    f"• Exclusive Veramon: **{exclusive_veramon.replace(',', ', ')}**\n"
                    f"• Faction XP Earned: **{xp_reward} XP**"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Next Steps",
                value=(
                    "• Your faction will receive daily rewards from this territory\n"
                    "• Strengthen your defenses with Territory Defenders\n"
                    "• Be prepared to defend against rival factions\n"
                    "• Explore this territory to find its exclusive Veramon"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            conn.rollback()
            await interaction.response.send_message(
                f"Failed to claim territory: {str(e)}",
                ephemeral=True
            )
        finally:
            conn.close()
        
    @app_commands.command(name="faction_end_war", description="End a war between factions (Admin Only)")
    @require_permission_level(PermissionLevel.ADMIN)
    @app_commands.describe(
        war_id="ID of the war to end"
    )
    async def faction_end_war(self, interaction: discord.Interaction, war_id: int):
        """End a faction war and determine the winner (Admin Only)."""
        result = await self.faction_war.end_war(war_id)
        
        if not result["success"]:
            await interaction.response.send_message(
                f"Failed to end war: {result['error']}",
                ephemeral=True
            )
            return
        
        # Create embed to show results
        embed = discord.Embed(
            title="🏆 Faction War Concluded",
            description="A faction war has ended!",
            color=0xFFD700  # Gold
        )
        
        # War details
        embed.add_field(
            name="War Summary",
            value=(
                f"**{result['attacker']['name']}** ({result['attacker']['score']} points) vs "
                f"**{result['defender']['name']}** ({result['defender']['score']} points)"
            ),
            inline=False
        )
        
        # Winner details
        if result["winner"]:
            embed.add_field(
                name="Winner",
                value=f"**{result['winner_name']}** is victorious!",
                inline=False
            )
            
            # Rewards
            if result["rewards"]:
                embed.add_field(
                    name="Rewards",
                    value=(
                        f"• Treasury Bonus: **{result['rewards']['token_reward']:,} tokens**\n"
                        f"• Faction XP: **{result['rewards']['xp_reward']:,} XP**"
                        f"{' (Level Up!)' if result['rewards']['level_up'] else ''}"
                    ),
                    inline=False
                )
            
            # Territory changes
            if result["territory"]:
                embed.add_field(
                    name="Territory Control",
                    value=(
                        f"**{result['winner_name']}** now controls **{result['territory']['name']}**\n"
                        f"• Daily Token Bonus: {result['territory']['daily_token_bonus']:,} tokens\n"
                        f"• Daily XP Bonus: {result['territory']['daily_xp_bonus']:,} XP"
                    ),
                    inline=False
                )
        else:
            embed.add_field(
                name="Result",
                value="The war ended in a **draw**! No rewards or territory changes have occurred.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
        
        # Also send to a public channel for announcement
        try:
            # Get announcement channel from config
            announcement_channel_id = interaction.channel_id  # Default to current channel
            
            channel = self.bot.get_channel(announcement_channel_id)
            if channel:
                await channel.send(embed=embed)
        except Exception:
            # Silently fail if announcement can't be sent
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(FactionWarCog(bot))
