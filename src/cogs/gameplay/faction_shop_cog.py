"""
Faction Shop Cog for Veramon Reunited

Provides commands for faction shop, purchasing faction items,
faction leveling, and treasury contributions.
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
from src.models.permissions import require_permission_level, PermissionLevel, is_admin
from src.db.faction_economy_db import initialize_faction_economy_db

class FactionShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_faction_economy_db()  # Initialize database tables
        self.faction_economy = get_faction_economy()
    
    @app_commands.command(name="faction_shop", description="Browse items in the faction shop")
    @app_commands.describe(
        category="Filter items by category (buffs, consumables, upgrades, all)"
    )
    async def faction_shop(
        self, 
        interaction: discord.Interaction,
        category: Optional[Literal["buffs", "consumables", "upgrades", "all"]] = "all"
    ):
        # Get user's faction ID and level
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is in a faction
        user_id = str(interaction.user.id)
        cursor.execute("""
            SELECT f.faction_id, f.name, f.faction_level, f.color, f.treasury
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_data = cursor.fetchone()
        if not faction_data:
            await interaction.response.send_message(
                "You need to be in a faction to access the faction shop!",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, faction_level, color, treasury = faction_data
        
        # Get shop items for this faction level
        shop_items = self.faction_economy.get_faction_shop_items(faction_level)
        
        # Filter by category if specified
        if category != "all":
            category_map = {
                "buffs": "buff",
                "consumables": "consumable",
                "upgrades": "upgrade"
            }
            shop_items = [item for item in shop_items if item["category"] == category_map.get(category, item["category"])]
        
        # Create embed for shop
        embed = discord.Embed(
            title=f"{faction_name} Faction Shop",
            description=f"Treasury: {treasury:,} tokens | Faction Level: {faction_level}\n\n"
                        f"Browse and purchase items for your faction. Some items require higher faction levels to unlock.",
            color=int(color, 16) if color else 0x0099ff
        )
        
        # Group items by category for display
        items_by_category = {}
        for item in shop_items:
            category = item["category"]
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append(item)
        
        # Add fields for each category
        category_names = {
            "buff": "📊 Temporary Buffs",
            "consumable": "🧪 Consumable Items",
            "upgrade": "⚙️ Permanent Upgrades"
        }
        
        for cat, cat_items in items_by_category.items():
            items_text = ""
            for item in cat_items:
                if item["available"]:
                    items_text += f"**{item['name']}** - {item['price']:,} tokens\n"
                    items_text += f"• {item['description']}\n"
                    items_text += f"• ID: `{item['item_id']}`\n\n"
                else:
                    items_text += f"**🔒 {item['name']}** - {item['price']:,} tokens\n"
                    items_text += f"• {item['locked_message']}\n\n"
            
            if items_text:
                embed.add_field(
                    name=category_names.get(cat, cat.capitalize()),
                    value=items_text,
                    inline=False
                )
        
        # Add instructions
        embed.set_footer(text="Use /faction_shop_buy item_id quantity to purchase an item")
        
        await interaction.response.send_message(embed=embed)
        conn.close()

    @app_commands.command(name="faction_shop_buy", description="Purchase an item from the faction shop")
    @app_commands.describe(
        item_id="ID of the item to purchase",
        quantity="Quantity to purchase (default: 1)"
    )
    async def faction_shop_buy(
        self,
        interaction: discord.Interaction,
        item_id: str,
        quantity: int = 1
    ):
        # Defer response since purchase might take time
        await interaction.response.defer(ephemeral=True)
        
        # Validate quantity
        if quantity <= 0:
            await interaction.followup.send("Quantity must be greater than 0!", ephemeral=True)
            return
            
        # Get user's faction
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.faction_id, f.name
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_data = cursor.fetchone()
        conn.close()
        
        if not faction_data:
            await interaction.followup.send(
                "You need to be in a faction to purchase items!",
                ephemeral=True
            )
            return
            
        faction_id, faction_name = faction_data
        
        # Process the purchase
        result = await self.faction_economy.purchase_faction_item(
            user_id=user_id,
            faction_id=faction_id,
            item_id=item_id,
            quantity=quantity
        )
        
        if not result["success"]:
            await interaction.followup.send(
                f"❌ Purchase failed: {result['error']}",
                ephemeral=True
            )
            return
        
        # Handle successful purchase
        item_name = result["item_name"]
        total_price = result["total_price"]
        category = result["category"]
        
        # Create success message
        success_embed = discord.Embed(
            title="Purchase Successful!",
            description=f"You purchased {quantity}x **{item_name}** for {total_price:,} tokens.",
            color=0x00ff00
        )
        
        # Add category-specific messages
        if category == "buff":
            success_embed.add_field(
                name="Buff Activated",
                value="The buff has been activated for your entire faction!",
                inline=False
            )
        elif category == "consumable":
            success_embed.add_field(
                name="Item Added to Inventory",
                value="The item has been added to your inventory. Use it with the appropriate command.",
                inline=False
            )
        elif category == "upgrade":
            success_embed.add_field(
                name="Upgrade Applied",
                value="The permanent upgrade has been applied to your faction!",
                inline=False
            )
            
        success_embed.add_field(
            name="Remaining Treasury",
            value=f"{result['remaining_treasury']:,} tokens",
            inline=False
        )
        
        await interaction.followup.send(embed=success_embed)
        
        # Send notification to faction channel if available
        try:
            # Get faction channel
            cursor = conn.cursor()
            cursor.execute("SELECT faction_channel_id FROM factions WHERE faction_id = ?", (faction_id,))
            channel_id = cursor.fetchone()
            conn.close()
            
            if channel_id and channel_id[0]:
                channel = self.bot.get_channel(int(channel_id[0]))
                if channel:
                    notification_embed = discord.Embed(
                        title="Faction Purchase",
                        description=f"{interaction.user.mention} purchased {quantity}x **{item_name}** for the faction!",
                        color=0x00ff00
                    )
                    await channel.send(embed=notification_embed)
        except Exception as e:
            # Silently fail if notification can't be sent
            pass

    @app_commands.command(name="faction_contribute", description="Contribute tokens to your faction's treasury")
    @app_commands.describe(
        amount="Amount of tokens to contribute"
    )
    async def faction_contribute(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message(
                "Contribution amount must be greater than 0!",
                ephemeral=True
            )
            return
            
        user_id = str(interaction.user.id)
        
        # Get user's faction
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.faction_id, f.name
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_data = cursor.fetchone()
        conn.close()
        
        if not faction_data:
            await interaction.response.send_message(
                "You are not in a faction!",
                ephemeral=True
            )
            return
            
        faction_id, faction_name = faction_data
        
        # Process contribution
        result = await self.faction_economy.contribute_to_treasury(
            user_id=user_id,
            faction_id=faction_id,
            amount=amount
        )
        
        if not result["success"]:
            await interaction.response.send_message(
                f"❌ Contribution failed: {result['error']}",
                ephemeral=True
            )
            return
            
        # Create success message
        embed = discord.Embed(
            title="Contribution Successful!",
            description=f"You contributed **{amount:,}** tokens to {faction_name}'s treasury.",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Your Token Balance",
            value=f"{result['new_user_balance']:,} tokens",
            inline=True
        )
        
        embed.add_field(
            name="Faction XP Gained",
            value=f"+{result['xp_gained']} XP",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Try to send notification to faction channel
        try:
            # Get faction channel
            cursor = conn.cursor()
            cursor.execute("SELECT faction_channel_id FROM factions WHERE faction_id = ?", (faction_id,))
            channel_id = cursor.fetchone()
            conn.close()
            
            if channel_id and channel_id[0]:
                channel = self.bot.get_channel(int(channel_id[0]))
                if channel:
                    notification_embed = discord.Embed(
                        title="Treasury Contribution",
                        description=f"{interaction.user.mention} contributed **{amount:,}** tokens to the faction treasury!",
                        color=0x00ff00
                    )
                    await channel.send(embed=notification_embed)
        except Exception as e:
            # Silently fail if notification can't be sent
            pass

    @app_commands.command(name="faction_level", description="View your faction's level and XP progress")
    async def faction_level(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user's faction
        cursor.execute("""
            SELECT f.faction_id, f.name, f.faction_level, f.faction_xp, f.color
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
        
        faction_id, faction_name, faction_level, faction_xp, color = faction_data
        
        # Calculate XP for next level
        next_level_xp = self.faction_economy.calculate_xp_for_level(faction_level + 1)
        
        # Calculate progress percentage
        progress_percentage = min(100, (faction_xp / next_level_xp) * 100)
        
        # Create progress bar
        progress_bar_length = 20
        filled_length = int(progress_bar_length * progress_percentage / 100)
        progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
        
        # Create embed
        embed = discord.Embed(
            title=f"{faction_name} - Faction Level",
            description=f"Current Level: **{faction_level}**\n"
                        f"XP: **{faction_xp:,}** / **{next_level_xp:,}**\n\n"
                        f"Progress to Level {faction_level + 1}:\n"
                        f"{progress_bar} {progress_percentage:.1f}%",
            color=int(color, 16) if color else 0x0099ff
        )
        
        # Get unlockable items at next level
        cursor.execute("""
            SELECT name 
            FROM faction_shop_items 
            WHERE required_level = ?
            LIMIT 3
        """, (faction_level + 1,))
        
        unlocks = cursor.fetchall()
        
        if unlocks:
            unlocks_text = "\n".join([f"• {name}" for name, in unlocks])
            embed.add_field(
                name=f"Unlocks at Level {faction_level + 1}",
                value=unlocks_text,
                inline=False
            )
            
        # Add info about how to gain faction XP
        embed.add_field(
            name="How to Gain Faction XP",
            value="• Members contributing tokens to treasury\n"
                  "• Winning faction wars\n"
                  "• Completing faction quests\n"
                  "• Claiming territory",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        conn.close()

    @app_commands.command(name="faction_contributions", description="View top contributors to your faction")
    async def faction_contributions(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # Get user's faction
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.faction_id, f.name, f.color
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
            
        faction_id, faction_name, color = faction_data
        
        # Get leaderboard
        leaderboard = self.faction_economy.get_faction_contribution_leaderboard(faction_id)
        
        if not leaderboard:
            await interaction.response.send_message(
                "No contributions have been made to your faction yet!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"{faction_name} - Top Contributors",
            description="These members have contributed the most to the faction treasury:",
            color=int(color, 16) if color else 0x0099ff
        )
        
        # Format leaderboard
        leaderboard_text = ""
        for i, member in enumerate(leaderboard):
            medal = ""
            if i == 0:
                medal = "🥇 "
            elif i == 1:
                medal = "🥈 "
            elif i == 2:
                medal = "🥉 "
            else:
                medal = f"{i+1}. "
                
            leaderboard_text += f"{medal}**{member['username']}** - {member['total_contribution']:,} tokens\n"
            leaderboard_text += f"• Rank: {member['rank']}\n\n"
            
        embed.add_field(
            name="Leaderboard",
            value=leaderboard_text,
            inline=False
        )
        
        # Add information about benefits
        embed.add_field(
            name="Benefits of Contributing",
            value="• Helps unlock higher faction levels\n"
                  "• Enables purchasing powerful faction items\n"
                  "• Improves faction's ability to win wars\n"
                  "• May result in rank promotions",
            inline=False
        )
        
        embed.set_footer(text="Use /faction_contribute to add to the treasury")
        
        await interaction.response.send_message(embed=embed)
        conn.close()

async def setup(bot: commands.Bot):
    await bot.add_cog(FactionShopCog(bot))
