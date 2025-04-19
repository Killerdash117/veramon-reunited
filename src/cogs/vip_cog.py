import discord
from discord.ext import commands
from discord import app_commands
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel, is_vip
from src.utils.cache import cache, cached, invalidate_cache

class VIPCog(commands.Cog):
    """
    VIP features for Veramon Reunited.
    
    Provides premium features for VIP users, including exclusive items,
    cosmetic customizations, and quality of life improvements.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="vip_shop", description="Browse the VIP exclusive shop")
    @is_vip()
    async def vip_shop(self, interaction: discord.Interaction):
        """Browse the VIP exclusive shop with premium items."""
        # Load VIP items
        vip_items = self._load_vip_items()
        
        # Create an embed to display the VIP shop
        embed = discord.Embed(
            title="✨ VIP Exclusive Shop ✨",
            description="Welcome to the VIP shop! Here you'll find exclusive items only available to VIP members.",
            color=discord.Color.gold()
        )
        
        # Group items by category
        categories = {}
        for item_id, item in vip_items.items():
            category = item.get("category", "Miscellaneous")
            if category not in categories:
                categories[category] = []
            categories[category].append((item_id, item))
            
        # Add each category to the embed
        for category, items in categories.items():
            # Create a field for each category
            items_text = ""
            for item_id, item in items:
                name = item.get("name", item_id)
                price = item.get("price", 0)
                description = item.get("description", "")
                items_text += f"**{name}** - {price} tokens\n{description}\nID: `{item_id}`\n\n"
                
            embed.add_field(
                name=f"📦 {category}",
                value=items_text,
                inline=False
            )
            
        # Add footer with instructions
        embed.set_footer(text="Use /vip_shop_buy [item_id] [quantity] to purchase items")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="vip_shop_buy", description="Buy an item from the VIP shop")
    @app_commands.describe(
        item_id="ID of the item to purchase",
        quantity="Number of items to purchase (default: 1)"
    )
    @is_vip()
    async def vip_shop_buy(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        """Purchase an item from the VIP exclusive shop."""
        # Validate quantity
        if quantity <= 0:
            await interaction.response.send_message(
                "Quantity must be at least 1.",
                ephemeral=True
            )
            return
            
        # Load VIP items
        vip_items = self._load_vip_items()
        
        # Check if item exists
        if item_id not in vip_items:
            await interaction.response.send_message(
                f"Item with ID '{item_id}' not found in the VIP shop.",
                ephemeral=True
            )
            return
            
        # Get item details
        item = vip_items[item_id]
        item_name = item.get("name", item_id)
        item_price = item.get("price", 0)
        total_price = item_price * quantity
        
        # Get user's token balance
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (str(interaction.user.id),))
        user_data = cursor.fetchone()
        
        if not user_data:
            await interaction.response.send_message(
                "You don't have an account yet. Please use other commands first to create one.",
                ephemeral=True
            )
            conn.close()
            return
            
        user_tokens = user_data["tokens"]
        
        # Check if user has enough tokens
        if user_tokens < total_price:
            await interaction.response.send_message(
                f"You don't have enough tokens. Required: {total_price}, Available: {user_tokens}",
                ephemeral=True
            )
            conn.close()
            return
            
        # Process the purchase transaction
        try:
            # Deduct tokens
            cursor.execute(
                "UPDATE users SET tokens = tokens - ? WHERE user_id = ?",
                (total_price, str(interaction.user.id))
            )
            
            # Add item to inventory
            cursor.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) 
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET 
                quantity = quantity + ?
            """, (
                str(interaction.user.id), 
                item_id, 
                quantity,
                quantity
            ))
            
            # Add purchase to transaction log
            cursor.execute("""
                INSERT INTO token_transactions 
                (user_id, amount, reason, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                str(interaction.user.id),
                -total_price,
                f"VIP shop purchase: {quantity}x {item_name}",
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            
            # Success message
            embed = discord.Embed(
                title="Purchase Successful!",
                description=f"You've purchased {quantity}x **{item_name}**.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Cost",
                value=f"{total_price} tokens",
                inline=True
            )
            
            embed.add_field(
                name="Remaining Balance",
                value=f"{user_tokens - total_price} tokens",
                inline=True
            )
            
            # Add information about the item's effect
            item_effect = item.get("effect", None)
            if item_effect:
                embed.add_field(
                    name="Effect",
                    value=item.get("description", "Special VIP item"),
                    inline=False
                )
                
                # Apply immediate effects if applicable
                if item.get("apply_on_purchase", False):
                    result = self._apply_item_effect(interaction.user.id, item_id, item)
                    if result:
                        embed.add_field(
                            name="Applied Effect",
                            value=result,
                            inline=False
                        )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            await interaction.response.send_message(
                f"Error processing purchase: {str(e)}",
                ephemeral=True
            )
        finally:
            conn.close()
    
    @app_commands.command(name="daily_vip", description="Claim your enhanced daily VIP rewards")
    @is_vip()
    async def daily_vip(self, interaction: discord.Interaction):
        """Claim enhanced daily rewards for VIP users."""
        user_id = str(interaction.user.id)
        
        # Get user's last claim time
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT last_daily_vip, vip_daily_streak
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            await interaction.response.send_message(
                "You don't have an account yet. Please use other commands first to create one.",
                ephemeral=True
            )
            conn.close()
            return
            
        last_claim = user_data["last_daily_vip"]
        current_streak = user_data.get("vip_daily_streak", 0)
        
        now = datetime.utcnow()
        
        # Check if user has already claimed today
        if last_claim:
            last_claim_date = datetime.fromisoformat(last_claim)
            time_since_claim = now - last_claim_date
            
            # Check if 24 hours have passed since last claim
            if time_since_claim.total_seconds() < 24 * 60 * 60:
                next_claim_time = last_claim_date + timedelta(days=1)
                time_until_next = next_claim_time - now
                hours, remainder = divmod(time_until_next.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                await interaction.response.send_message(
                    f"You've already claimed your VIP daily reward today.\nNext claim available in {hours}h {minutes}m {seconds}s.",
                    ephemeral=True
                )
                conn.close()
                return
                
            # Check if streak should continue or reset
            if time_since_claim.total_seconds() > 48 * 60 * 60:  # More than 48 hours
                # Reset streak if more than 48 hours have passed
                current_streak = 0
                
        # Calculate rewards
        base_tokens = 150  # Base tokens for VIP daily
        streak_bonus = min(current_streak * 25, 250)  # 25 tokens per streak day, max 250
        total_tokens = base_tokens + streak_bonus
        
        # Increment streak
        new_streak = current_streak + 1
        
        # Update user data
        cursor.execute("""
            UPDATE users
            SET tokens = tokens + ?,
                last_daily_vip = ?,
                vip_daily_streak = ?
            WHERE user_id = ?
        """, (
            total_tokens,
            now.isoformat(),
            new_streak,
            user_id
        ))
        
        # Add to transaction log
        cursor.execute("""
            INSERT INTO token_transactions 
            (user_id, amount, reason, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            total_tokens,
            f"VIP daily claim (streak: {new_streak})",
            now.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Create reward embed
        embed = discord.Embed(
            title="✨ VIP Daily Reward Claimed! ✨",
            description="You've successfully claimed your enhanced VIP daily reward.",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Base Reward",
            value=f"{base_tokens} tokens",
            inline=True
        )
        
        embed.add_field(
            name="Streak",
            value=f"{new_streak} {'day' if new_streak == 1 else 'days'}",
            inline=True
        )
        
        if streak_bonus > 0:
            embed.add_field(
                name="Streak Bonus",
                value=f"+{streak_bonus} tokens",
                inline=True
            )
            
        embed.add_field(
            name="Total Reward",
            value=f"**{total_tokens} tokens**",
            inline=False
        )
        
        # Add streak milestone messages
        if new_streak == 7:
            embed.add_field(
                name="Milestone Reached!",
                value="You've reached a 7-day streak! Keep it up!",
                inline=False
            )
        elif new_streak == 30:
            embed.add_field(
                name="Amazing Dedication!",
                value="30-day streak achieved! You're a true VIP!",
                inline=False
            )
            
        embed.set_footer(text="Come back tomorrow for another reward!")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="nickname_color", description="Change your nickname color in bot embeds")
    @app_commands.describe(color="Color in hex format (e.g. #FF5500)")
    @is_vip()
    async def nickname_color(self, interaction: discord.Interaction, color: str):
        """Change the color of your nickname in bot embeds."""
        user_id = str(interaction.user.id)
        
        # Validate hex color
        import re
        if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
            await interaction.response.send_message(
                "Invalid color format. Please use hex format (e.g. #FF5500).",
                ephemeral=True
            )
            return
            
        # Update user's color preference
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users
            SET nickname_color = ?
            WHERE user_id = ?
        """, (color, user_id))
        
        conn.commit()
        conn.close()
        
        # Create a preview of the color
        embed = discord.Embed(
            title="Nickname Color Updated!",
            description=f"Your nickname will now appear with this color in bot embeds.",
            color=int(color.lstrip('#'), 16)  # Convert hex to int
        )
        
        embed.add_field(
            name="Preview",
            value=f"<@{user_id}>",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="cooldown_refresh", description="Reset your exploration cooldown once per day")
    @is_vip()
    async def cooldown_refresh(self, interaction: discord.Interaction):
        """Reset exploration cooldown once per day (VIP only)."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if the user has already used this today
        cursor.execute("""
            SELECT last_cooldown_refresh
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            await interaction.response.send_message(
                "You don't have an account yet. Please use other commands first to create one.",
                ephemeral=True
            )
            conn.close()
            return
            
        now = datetime.utcnow()
        last_refresh = user_data["last_cooldown_refresh"]
        
        # Check if user has already used refresh today
        if last_refresh:
            last_refresh_date = datetime.fromisoformat(last_refresh)
            time_since_refresh = now - last_refresh_date
            
            # Check if 24 hours have passed
            if time_since_refresh.total_seconds() < 24 * 60 * 60:
                next_refresh_time = last_refresh_date + timedelta(days=1)
                time_until_next = next_refresh_time - now
                hours, remainder = divmod(time_until_next.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                await interaction.response.send_message(
                    f"You've already used your cooldown refresh today.\nNext refresh available in {hours}h {minutes}m {seconds}s.",
                    ephemeral=True
                )
                conn.close()
                return
                
        # Reset the exploration cooldown
        cursor.execute("""
            UPDATE users
            SET last_explore = NULL,
                last_cooldown_refresh = ?
            WHERE user_id = ?
        """, (now.isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="Cooldown Refreshed!",
            description="Your exploration cooldown has been reset. You can explore immediately!",
            color=discord.Color.green()
        )
        
        embed.set_footer(text="This VIP perk can be used once every 24 hours.")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="profile_background", description="Change your profile background")
    @app_commands.describe(background_id="ID of the background to use")
    @is_vip()
    async def profile_background(self, interaction: discord.Interaction, background_id: str):
        """Change your profile background to a VIP exclusive one."""
        user_id = str(interaction.user.id)
        
        # Load available backgrounds
        backgrounds = self._load_backgrounds()
        
        # Check if background exists
        if background_id not in backgrounds:
            await interaction.response.send_message(
                f"Background with ID '{background_id}' not found.",
                ephemeral=True
            )
            return
            
        background = backgrounds[background_id]
        
        # Check if user has purchased this background
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT quantity
            FROM inventory
            WHERE user_id = ? AND item_id = ?
        """, (user_id, background_id))
        
        inventory_item = cursor.fetchone()
        
        if not inventory_item or inventory_item["quantity"] <= 0:
            await interaction.response.send_message(
                f"You don't own this background. Purchase it from the VIP shop first.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Update user's profile background
        cursor.execute("""
            UPDATE users
            SET profile_background = ?
            WHERE user_id = ?
        """, (background_id, user_id))
        
        conn.commit()
        conn.close()
        
        # Create a preview
        embed = discord.Embed(
            title="Profile Background Updated!",
            description=f"Your profile background has been changed to **{background['name']}**.",
            color=discord.Color.blurple()
        )
        
        if "image_url" in background:
            embed.set_image(url=background["image_url"])
            
        embed.set_footer(text="This will be displayed on your profile.")
        
        await interaction.response.send_message(embed=embed)
        
    # Helper methods
    
    def _load_vip_items(self) -> Dict[str, Any]:
        """Load VIP shop items from data file."""
        # Use cache to avoid repeated file reads
        return cache.get_or_set("vip:shop_items", self._read_vip_items, ttl=3600)
        
    def _read_vip_items(self) -> Dict[str, Any]:
        """Read VIP shop items from data file."""
        import os
        import json
        
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vip_items.json")
        try:
            with open(data_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return empty dict if file doesn't exist or is invalid
            return {}
            
    def _load_backgrounds(self) -> Dict[str, Any]:
        """Load profile backgrounds from data file."""
        # Use cache to avoid repeated file reads
        return cache.get_or_set("vip:backgrounds", self._read_backgrounds, ttl=3600)
        
    def _read_backgrounds(self) -> Dict[str, Any]:
        """Read profile backgrounds from data file."""
        import os
        import json
        
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "backgrounds.json")
        try:
            with open(data_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return empty dict if file doesn't exist or is invalid
            return {}
            
    def _apply_item_effect(self, user_id: str, item_id: str, item: Dict[str, Any]) -> Optional[str]:
        """Apply an item's effect if applicable."""
        effect_type = item.get("effect", {}).get("type")
        
        if not effect_type:
            return None
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            if effect_type == "exp_boost":
                # Apply experience boost
                duration = item.get("effect", {}).get("duration", 24)  # Hours
                multiplier = item.get("effect", {}).get("multiplier", 1.5)
                
                expiry = datetime.utcnow() + timedelta(hours=duration)
                
                cursor.execute("""
                    INSERT INTO user_buffs (user_id, buff_type, value, expires_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, buff_type) DO UPDATE SET
                    value = ?, expires_at = ?
                """, (
                    user_id, "exp_boost", multiplier, expiry.isoformat(),
                    multiplier, expiry.isoformat()
                ))
                
                conn.commit()
                return f"Experience gain multiplier of {multiplier}x for {duration} hours"
                
            elif effect_type == "catch_boost":
                # Apply catch rate boost
                duration = item.get("effect", {}).get("duration", 24)  # Hours
                multiplier = item.get("effect", {}).get("multiplier", 1.3)
                
                expiry = datetime.utcnow() + timedelta(hours=duration)
                
                cursor.execute("""
                    INSERT INTO user_buffs (user_id, buff_type, value, expires_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, buff_type) DO UPDATE SET
                    value = ?, expires_at = ?
                """, (
                    user_id, "catch_boost", multiplier, expiry.isoformat(),
                    multiplier, expiry.isoformat()
                ))
                
                conn.commit()
                return f"Catch rate multiplier of {multiplier}x for {duration} hours"
                
            elif effect_type == "token_boost":
                # Apply token gain boost
                duration = item.get("effect", {}).get("duration", 24)  # Hours
                multiplier = item.get("effect", {}).get("multiplier", 1.2)
                
                expiry = datetime.utcnow() + timedelta(hours=duration)
                
                cursor.execute("""
                    INSERT INTO user_buffs (user_id, buff_type, value, expires_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, buff_type) DO UPDATE SET
                    value = ?, expires_at = ?
                """, (
                    user_id, "token_boost", multiplier, expiry.isoformat(),
                    multiplier, expiry.isoformat()
                ))
                
                conn.commit()
                return f"Token gain multiplier of {multiplier}x for {duration} hours"
                
            # Add more effect types as needed
            
        except Exception as e:
            conn.rollback()
            print(f"Error applying item effect: {e}")
            return None
        finally:
            conn.close()
            
        return None

async def setup(bot: commands.Bot):
    """Add the VIPCog to the bot."""
    await bot.add_cog(VIPCog(bot))
