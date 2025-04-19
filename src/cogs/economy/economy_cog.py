import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import json
from typing import Dict, List, Optional, Union, Literal
from src.db.db import get_connection  # This function should return an SQLite connection
from src.models.permissions import require_permission_level, PermissionLevel, is_admin, get_permission_level
from datetime import datetime
from src.core.security_integration import get_security_integration

def initialize_economy_db():
    """
    Ensure the economy-related tables exist in the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        tokens INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        achievements TEXT DEFAULT '[]',
        last_daily TEXT,
        tokens_multiplier REAL DEFAULT 1.0,
        xp_multiplier REAL DEFAULT 1.0,
        profile_theme TEXT DEFAULT 'default'
    )
    """)
    
    # Inventory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id TEXT,
        item_id TEXT,
        quantity INTEGER,
        PRIMARY KEY (user_id, item_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    # Active boosts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_boosts (
        user_id TEXT,
        boost_type TEXT, 
        multiplier REAL,
        expires_at TEXT,
        PRIMARY KEY (user_id, boost_type),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    # Daily streaks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_streaks (
        user_id TEXT PRIMARY KEY,
        current_streak INTEGER DEFAULT 0,
        max_streak INTEGER DEFAULT 0,
        last_claim_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    # Purchase history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        item_id TEXT,
        quantity INTEGER,
        total_price INTEGER,
        purchase_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    # Quests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quests (
        quest_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        requirements TEXT,
        token_reward INTEGER,
        xp_reward INTEGER,
        item_rewards TEXT,
        difficulty TEXT
    )
    """)
    
    # User quest progress
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_quests (
        user_id TEXT,
        quest_id INTEGER,
        progress TEXT,
        completed INTEGER DEFAULT 0,
        completion_date TEXT,
        PRIMARY KEY (user_id, quest_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (quest_id) REFERENCES quests (quest_id)
    )
    """)
    
    # Token transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS token_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id TEXT,
        recipient_id TEXT,
        amount INTEGER,
        transaction_time TEXT,
        message TEXT,
        transaction_type TEXT
    )
    """)
    
    conn.commit()
    conn.close()

class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_economy_db()  # Create/update the economy tables on load
        # Load items data
        items_path = os.path.join(os.path.dirname(__file__), "..", "data", "items.json")
        with open(items_path, "r") as f:
            self.items = json.load(f)
            
        # Load quests data
        quests_path = os.path.join(os.path.dirname(__file__), "..", "data", "quests.json")
        with open(quests_path, "r") as f:
            self.quests = json.load(f)
        
        # Cache for user multipliers
        self.token_multipliers = {}
        self.xp_multipliers = {}

    def get_user_token_multiplier(self, user_id: str) -> float:
        """Get a user's token multiplier, including VIP status and active boosts."""
        # Check if in cache first
        if user_id in self.token_multipliers:
            return self.token_multipliers[user_id]
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Base multiplier from user's permission level
        permission_level = get_permission_level(int(user_id))
        base_multiplier = 1.0  # Default for normal users
        
        if permission_level >= PermissionLevel.VIP:
            base_multiplier = 1.2  # VIP users get 1.2x tokens
        
        # Check for active boosts
        cursor.execute("""
            SELECT multiplier FROM active_boosts 
            WHERE user_id = ? AND boost_type = 'token' 
            AND datetime(expires_at) > datetime('now')
        """, (user_id,))
        
        boost_row = cursor.fetchone()
        boost_multiplier = boost_row[0] if boost_row else 1.0
        
        # Check for user's stored multiplier (from quests, etc)
        cursor.execute("SELECT tokens_multiplier FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        user_multiplier = user_row[0] if user_row else 1.0
        
        conn.close()
        
        # Combine all multipliers
        total_multiplier = base_multiplier * boost_multiplier * user_multiplier
        
        # Store in cache
        self.token_multipliers[user_id] = total_multiplier
        
        return total_multiplier
        
    def get_user_xp_multiplier(self, user_id: str) -> float:
        """Get a user's XP multiplier, including active boosts."""
        # Check if in cache first
        if user_id in self.xp_multipliers:
            return self.xp_multipliers[user_id]
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Base multiplier
        base_multiplier = 1.0
        
        # Check for active boosts
        cursor.execute("""
            SELECT multiplier FROM active_boosts 
            WHERE user_id = ? AND boost_type = 'xp' 
            AND datetime(expires_at) > datetime('now')
        """, (user_id,))
        
        boost_row = cursor.fetchone()
        boost_multiplier = boost_row[0] if boost_row else 1.0
        
        # Check for user's stored multiplier (from quests, etc)
        cursor.execute("SELECT xp_multiplier FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        user_multiplier = user_row[0] if user_row else 1.0
        
        conn.close()
        
        # Combine all multipliers
        total_multiplier = base_multiplier * boost_multiplier * user_multiplier
        
        # Store in cache
        self.xp_multipliers[user_id] = total_multiplier
        
        return total_multiplier

    @app_commands.command(name="balance", description="Check your current token balance and economy stats.")
    @require_permission_level(PermissionLevel.USER)
    async def balance(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tokens, xp FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            tokens, xp = row
        else:
            tokens, xp = 0, 0  # Default values if user is not in the table
            
        # Get streak info
        cursor.execute("""
            SELECT current_streak, max_streak
            FROM daily_streaks
            WHERE user_id = ?
        """, (user_id,))
        
        streak_row = cursor.fetchone()
        current_streak = streak_row[0] if streak_row else 0
        max_streak = streak_row[1] if streak_row else 0
        
        # Get active boosts
        cursor.execute("""
            SELECT boost_type, multiplier, expires_at
            FROM active_boosts
            WHERE user_id = ? AND datetime(expires_at) > datetime('now')
        """, (user_id,))
        
        active_boosts = cursor.fetchall()
        
        conn.close()
        
        # Get multipliers
        token_multiplier = self.get_user_token_multiplier(user_id)
        xp_multiplier = self.get_user_xp_multiplier(user_id)
        
        # Create response embed
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Economy Stats",
            description=f"View your current economic status and active bonuses.",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Tokens",
            value=f"**{tokens:,}** tokens\n*({token_multiplier:.2f}x multiplier)*",
            inline=True
        )
        
        embed.add_field(
            name="✨ Experience",
            value=f"**{xp:,}** XP\n*({xp_multiplier:.2f}x multiplier)*",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Daily Streak",
            value=f"Current: **{current_streak}** days\nBest: **{max_streak}** days",
            inline=True
        )
        
        # Show active boosts if any
        if active_boosts:
            boost_text = ""
            for boost_type, multiplier, expires_at in active_boosts:
                expires = datetime.fromisoformat(expires_at)
                now = datetime.now()
                hours_left = round((expires - now).total_seconds() / 3600, 1)
                
                boost_text += f"• **{boost_type.replace('_', ' ').title()}**: {multiplier:.1f}x ({hours_left}h left)\n"
                
            embed.add_field(
                name="⚡ Active Boosts",
                value=boost_text if boost_text else "None",
                inline=False
            )
            
        embed.set_footer(text="Use /shop to browse items and /daily to claim your daily reward")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop", description="Browse the item shop")
    @app_commands.describe(category="Filter items by category")
    @require_permission_level(PermissionLevel.USER)
    async def shop(self, interaction: discord.Interaction, category: Optional[str] = None):
        """Browse items available in the shop, optionally filtered by category."""
        user_id = str(interaction.user.id)
        
        # Get user's current balance
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        user_tokens = row[0] if row else 0
        conn.close()
        
        # Filter items by category if specified
        filtered_items = {}
        categories = set()
        
        for item_id, item_data in self.items.items():
            # Build set of all available categories
            if "category" in item_data:
                categories.add(item_data["category"])
                
            # Filter by category if specified
            if category and "category" in item_data:
                if item_data["category"].lower() == category.lower():
                    filtered_items[item_id] = item_data
            elif not category:
                filtered_items[item_id] = item_data
        
        # Create embed for shop
        embed = discord.Embed(
            title="Veramon Shop",
            description=f"Browse and purchase items with your tokens.\nYour balance: **{user_tokens:,}** tokens",
            color=discord.Color.blue()
        )
        
        # Group items by category
        items_by_category = {}
        for item_id, item_data in filtered_items.items():
            category = item_data.get("category", "miscellaneous")
            if category not in items_by_category:
                items_by_category[category] = []
            
            # Format price with a visual indicator if user can afford it
            price = item_data.get("price", 0)
            price_display = f"{price:,}" if user_tokens >= price else f"~~{price:,}~~"
            
            items_by_category[category].append(
                f"• **{item_data['name']}** - {price_display} tokens\n  *{item_data['description']}*\n  ID: `{item_id}`"
            )
        
        # Add categories to embed
        for category, items in items_by_category.items():
            category_name = category.replace("_", " ").title()
            embed.add_field(
                name=f"{category_name} Items",
                value="\n".join(items) if items else "No items available",
                inline=False
            )
            
        # If filtered and no results, show available categories
        if category and not filtered_items:
            embed.description += f"\n\nNo items found in category '{category}'. Available categories:"
            for cat in sorted(categories):
                embed.description += f"\n• {cat.replace('_', ' ').title()}"
                
        embed.set_footer(text="Use /shop_buy item_id:item_id quantity:amount to purchase items")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop_buy", description="Purchase an item from the shop using tokens")
    @app_commands.describe(
        item_id="The ID of the item to purchase",
        quantity="How many of the item to buy (default: 1)"
    )
    @require_permission_level(PermissionLevel.USER)
    async def shop_buy(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        """Purchase an item from the shop using tokens."""
        user_id = str(interaction.user.id)
        
        # Security validation for shop purchase
        security = get_security_integration()
        validation_result = await security.validate_shop_purchase(
            user_id, item_id, quantity
        )
        
        if not validation_result["valid"]:
            await interaction.response.send_message(
                validation_result["error"],
                ephemeral=True
            )
            return
            
        # Legacy validation - will be fully replaced by security system
        # Check if item exists
        if item_id not in self.items:
            await interaction.response.send_message(f"Item '{item_id}' not found in the shop.", ephemeral=True)
            return
            
        item = self.items[item_id]
        price = item.get("price", 0)
        total_price = price * quantity
        
        # Check if item is available in the shop
        if not item.get("available", True):
            await interaction.response.send_message(f"'{item['name']}' is not currently available for purchase.", ephemeral=True)
            return
        
        # Check if the quantity is valid
        if quantity <= 0:
            await interaction.response.send_message("Quantity must be a positive number.", ephemeral=True)
            return
        
        # Get user's current tokens
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            # Create user entry if not exists
            cursor.execute("INSERT INTO users (user_id, tokens, xp) VALUES (?, 0, 0)", (user_id,))
            conn.commit()
            user_tokens = 0
        else:
            user_tokens = user_row[0]
        
        # Check if user has enough tokens
        if user_tokens < total_price:
            await interaction.response.send_message(
                f"You don't have enough tokens for this purchase. Price: {total_price}, Your tokens: {user_tokens}",
                ephemeral=True
            )
            conn.close()
            return
            
        # Process the purchase
        cursor.execute("UPDATE users SET tokens = tokens - ? WHERE user_id = ?", (total_price, user_id))
        
        # Add item to inventory
        cursor.execute("""
            INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
        """, (user_id, item_id, quantity, quantity))
        
        # Record purchase in history
        cursor.execute("""
            INSERT INTO purchase_history (user_id, item_id, quantity, total_price, purchase_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, item_id, quantity, total_price, datetime.utcnow().isoformat()))
        
        conn.commit()
        
        # Handle any special effects for the item (boosters, etc.)
        await self._handle_special_item_effects(interaction, item_id, quantity)
        
        # Create a receipt embed
        embed = discord.Embed(
            title="Purchase Successful",
            description=f"You bought {quantity}x {item['name']} for {total_price} tokens.",
            color=discord.Color.green()
        )
        
        # Add remaining balance
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
        new_balance = cursor.fetchone()[0]
        embed.add_field(name="Remaining Balance", value=f"{new_balance} tokens", inline=False)
        
        # Add item details
        if "description" in item:
            embed.add_field(name="Description", value=item["description"], inline=False)
            
        if "effects" in item:
            effects_text = ""
            for effect, value in item["effects"].items():
                effects_text += f"{effect.replace('_', ' ').title()}: {value}\n"
            
            if effects_text:
                embed.add_field(name="Effects", value=effects_text, inline=False)
        
        conn.close()
        
        # Security logging for the transaction
        security.log_security_event(
            user_id=user_id,
            event_type="shop_purchase",
            details={
                "item_id": item_id,
                "quantity": quantity,
                "total_price": total_price
            }
        )
                
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="inventory", description="View your current inventory")
    @require_permission_level(PermissionLevel.USER)
    async def inventory(self, interaction: discord.Interaction):
        """View your current inventory of items."""
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id = ? ORDER BY item_id",
            (user_id,)
        )
        inventory_items = cursor.fetchall()
        conn.close()

        if not inventory_items:
            await interaction.response.send_message("Your inventory is empty. Purchase items with /shop_buy.", ephemeral=True)
            return

        inventory_list = []
        for item_id, quantity in inventory_items:
            if item_id in self.items:
                item = self.items[item_id]
                inventory_list.append(f"**{item['name']}** (ID: `{item_id}`) - {quantity}x | Multiplier: {item['multiplier']}")
            else:
                inventory_list.append(f"Unknown Item (ID: `{item_id}`) - {quantity}x")

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Inventory",
            description="\n".join(inventory_list),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use items with /catch item_id:item_id")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="award", description="Award tokens to a user (Admin only)")
    @app_commands.describe(user="User to receive tokens", amount="Amount of tokens to award", reason="Reason for the award")
    @is_admin()
    async def award(self, interaction: discord.Interaction, user: discord.Member, amount: int, reason: str = "No reason provided"):
        """Admin command to award tokens to users."""
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        target_id = str(user.id)
        conn = get_connection()
        cursor = conn.cursor()

        # Check if user exists in database
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (target_id,))
        row = cursor.fetchone()

        if row:
            new_balance = row[0] + amount
            cursor.execute("UPDATE users SET tokens = ? WHERE user_id = ?", (new_balance, target_id))
        else:
            new_balance = amount
            cursor.execute("INSERT INTO users (user_id, tokens, xp) VALUES (?, ?, 0)", (target_id, amount))

        conn.commit()
        conn.close()

        # Notify both admin and target user
        admin_embed = discord.Embed(
            title="Tokens Awarded",
            description=f"You awarded {amount} tokens to {user.display_name}.",
            color=discord.Color.green()
        )
        admin_embed.add_field(name="Reason", value=reason, inline=False)
        admin_embed.add_field(name="New Balance", value=f"{new_balance} tokens", inline=True)

        await interaction.response.send_message(embed=admin_embed)

        # Try to DM the user about their award
        try:
            user_embed = discord.Embed(
                title="You Received Tokens!",
                description=f"You were awarded {amount} tokens by {interaction.user.display_name}.",
                color=discord.Color.gold()
            )
            user_embed.add_field(name="Reason", value=reason, inline=False)
            user_embed.add_field(name="New Balance", value=f"{new_balance} tokens", inline=True)

            await user.send(embed=user_embed)
        except:
            # If we can't DM the user, just continue silently
            pass

    async def _handle_special_item_effects(self, interaction: discord.Interaction, item_id: str, quantity: int):
        """Handle immediate effects for special items."""
        item = self.items[item_id]
        user_id = str(interaction.user.id)
        
        # Apply boosts for appropriate items
        if item.get("effect") in ["token_boost", "xp_boost", "shiny_boost", "rarity_boost"]:
            boost_type = item.get("effect").replace("_boost", "")
            multiplier = item.get("multiplier", 1.0)
            
            # Default duration: 1 hour (3600 seconds)
            duration_hours = 1
            
            # Calculate expiration time
            expires_at = (datetime.datetime.now() + 
                         datetime.timedelta(hours=duration_hours * quantity)).isoformat()
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if boost already exists
            cursor.execute("""
                SELECT multiplier, expires_at FROM active_boosts
                WHERE user_id = ? AND boost_type = ?
            """, (user_id, boost_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # If existing boost, extend duration and take the higher multiplier
                existing_multiplier, existing_expires = existing
                existing_expiry = datetime.datetime.fromisoformat(existing_expires)
                
                # If new multiplier is higher, use it
                final_multiplier = max(existing_multiplier, multiplier)
                
                # If existing hasn't expired, add to that time
                if existing_expiry > datetime.datetime.now():
                    final_expires = (existing_expiry + 
                                   datetime.timedelta(hours=duration_hours * quantity)).isoformat()
                else:
                    final_expires = expires_at
                
                cursor.execute("""
                    UPDATE active_boosts 
                    SET multiplier = ?, expires_at = ?
                    WHERE user_id = ? AND boost_type = ?
                """, (final_multiplier, final_expires, user_id, boost_type))
                
            else:
                # Create new boost
                cursor.execute("""
                    INSERT INTO active_boosts (user_id, boost_type, multiplier, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, boost_type, multiplier, expires_at))
            
            conn.commit()
            conn.close()
            
            # Clear the multiplier cache for this user to force recalculation
            if boost_type == "token":
                if user_id in self.token_multipliers:
                    del self.token_multipliers[user_id]
            elif boost_type == "xp":
                if user_id in self.xp_multipliers:
                    del self.xp_multipliers[user_id]
                    
        # Handle other special item effects as needed
        # For example, nickname tags, shiny rerolls, etc.

    @app_commands.command(name="daily", description="Claim your daily token reward")
    @require_permission_level(PermissionLevel.USER)
    async def daily(self, interaction: discord.Interaction):
        """Claim daily token rewards with a streak bonus system."""
        user_id = str(interaction.user.id)
        now = datetime.datetime.now()
        today = now.date()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user already claimed today
        cursor.execute("""
            SELECT last_daily FROM users WHERE user_id = ?
        """, (user_id,))
        
        last_claim_row = cursor.fetchone()
        
        if last_claim_row and last_claim_row[0]:
            last_claim = datetime.datetime.fromisoformat(last_claim_row[0]).date()
            
            if last_claim == today:
                embed = discord.Embed(
                    title="Daily Reward Already Claimed",
                    description="You've already claimed your daily reward today. Come back tomorrow!",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Next claim available: Tomorrow")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                conn.close()
                return
        
        # Get streak information
        cursor.execute("""
            SELECT current_streak, max_streak, last_claim_date
            FROM daily_streaks
            WHERE user_id = ?
        """, (user_id,))
        
        streak_row = cursor.fetchone()
        
        current_streak = 0
        max_streak = 0
        streak_broken = False
        
        if streak_row:
            current_streak, max_streak, last_claim_date = streak_row
            
            if last_claim_date:
                last_date = datetime.datetime.fromisoformat(last_claim_date).date()
                yesterday = today - datetime.timedelta(days=1)
                
                if last_date == yesterday:
                    # Streak continues
                    current_streak += 1
                elif last_date != today:  # Ensure we're not double-counting today
                    # Streak broken
                    current_streak = 1
                    streak_broken = True
            else:
                # First time claiming
                current_streak = 1
        else:
            # First time claiming
            current_streak = 1
            
        # Update max streak if needed
        max_streak = max(current_streak, max_streak or 0)
        
        # Calculate reward
        base_reward = 100  # Base daily reward
        streak_bonus = min(current_streak * 10, 200)  # Cap streak bonus at 200 (20 days)
        
        # Apply token multiplier
        multiplier = self.get_user_token_multiplier(user_id)
        total_reward = int((base_reward + streak_bonus) * multiplier)
        
        # Update user's tokens
        cursor.execute("""
            SELECT tokens FROM users WHERE user_id = ?
        """, (user_id,))
        
        tokens_row = cursor.fetchone()
        
        if tokens_row:
            new_balance = tokens_row[0] + total_reward
            cursor.execute("""
                UPDATE users 
                SET tokens = ?, last_daily = ?
                WHERE user_id = ?
            """, (new_balance, now.isoformat(), user_id))
        else:
            new_balance = total_reward
            cursor.execute("""
                INSERT INTO users (user_id, tokens, xp, last_daily)
                VALUES (?, ?, 0, ?)
            """, (user_id, total_reward, now.isoformat()))
            
        # Update streak information
        if streak_row:
            cursor.execute("""
                UPDATE daily_streaks
                SET current_streak = ?, max_streak = ?, last_claim_date = ?
                WHERE user_id = ?
            """, (current_streak, max_streak, now.isoformat(), user_id))
        else:
            cursor.execute("""
                INSERT INTO daily_streaks (user_id, current_streak, max_streak, last_claim_date)
                VALUES (?, ?, ?, ?)
            """, (user_id, current_streak, max_streak, now.isoformat()))
            
        conn.commit()
        conn.close()
        
        # Create reward embed
        embed = discord.Embed(
            title="Daily Reward Claimed!",
            description="You've claimed your daily token reward.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="💰 Reward Breakdown",
            value=f"Base Reward: **{base_reward}** tokens\n" +
                  f"Streak Bonus: **{streak_bonus}** tokens\n" +
                  f"Multiplier: **{multiplier:.2f}x**\n" +
                  f"**Total: {total_reward} tokens**",
            inline=False
        )
        
        embed.add_field(
            name="🔄 Streak",
            value=f"Current: **{current_streak}** day{'s' if current_streak != 1 else ''}\n" +
                  f"Best: **{max_streak}** day{'s' if max_streak != 1 else ''}",
            inline=True
        )
        
        embed.add_field(
            name="💵 New Balance",
            value=f"**{new_balance:,}** tokens",
            inline=True
        )
        
        if streak_broken:
            embed.add_field(
                name="⚠️ Streak Reset",
                value="Your previous streak was broken because you missed a day.",
                inline=False
            )
            
        # Show streak milestone rewards if applicable
        if current_streak in [5, 10, 15, 30, 60, 90, 180, 365]:
            milestone_reward = None
            if current_streak == 5:
                milestone_reward = "**Bonus**: 1x XP Booster added to inventory!"
                await self._add_item_to_inventory(user_id, "xp_booster", 1)
            elif current_streak == 10:
                milestone_reward = "**Bonus**: 1x Token Magnet added to inventory!"
                await self._add_item_to_inventory(user_id, "token_magnet", 1)
            elif current_streak == 15:
                milestone_reward = "**Bonus**: 1x Rainbow Lure added to inventory!"
                await self._add_item_to_inventory(user_id, "rainbow_lure", 1)
            elif current_streak == 30:
                milestone_reward = "**Bonus**: 1x Shiny Reroller added to inventory!"
                await self._add_item_to_inventory(user_id, "shiny_reroll", 1)
            
            if milestone_reward:
                embed.add_field(
                    name="🏆 Streak Milestone!",
                    value=f"You've maintained a **{current_streak}-day** streak!\n{milestone_reward}",
                    inline=False
                )
        
        # Update leaderboard stats
        try:
            # Update login streak stat
            leaderboard_cog = self.bot.get_cog("LeaderboardCog")
            if leaderboard_cog:
                await leaderboard_cog.update_streak_stat(user_id, current_streak)
                
                # Also update token stat with the user's new balance
                await leaderboard_cog.update_stat(user_id, "tokens", new_balance, mode="set")
                
                # Update XP stat as well
                cursor.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,))
                xp_row = cursor.fetchone()
                if xp_row:
                    await leaderboard_cog.update_stat(user_id, "xp", xp_row[0], mode="set")
        except Exception as e:
            print(f"Error updating leaderboard stats: {e}")
                
        embed.set_footer(text=f"Come back tomorrow for your next daily reward!")
        
        await interaction.response.send_message(embed=embed)

    async def _add_item_to_inventory(self, user_id: str, item_id: str, quantity: int = 1):
        """Helper method to add an item to a user's inventory."""
        if item_id not in self.items:
            return False
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user already has this item
        cursor.execute("""
            SELECT quantity FROM inventory 
            WHERE user_id = ? AND item_id = ?
        """, (user_id, item_id))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update quantity
            new_quantity = existing[0] + quantity
            cursor.execute("""
                UPDATE inventory
                SET quantity = ?
                WHERE user_id = ? AND item_id = ?
            """, (new_quantity, user_id, item_id))
        else:
            # Add new inventory item
            cursor.execute("""
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES (?, ?, ?)
            """, (user_id, item_id, quantity))
            
        conn.commit()
        conn.close()
        return True

    @app_commands.command(name="quests", description="View your active and completed quests")
    @app_commands.describe(quest_type="Type of quests to view")
    @require_permission_level(PermissionLevel.USER)
    async def view_quests(self, interaction: discord.Interaction, 
                          quest_type: Optional[Literal["daily", "weekly", "achievement", "story", "all"]] = None):
        """View quests and track your progress."""
        user_id = str(interaction.user.id)
        
        # Get user's quests from database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all quests with progress
        if quest_type and quest_type != "all":
            cursor.execute("""
                SELECT q.quest_id, q.title, q.description, q.requirements, 
                       q.token_reward, q.xp_reward, q.item_rewards, q.difficulty,
                       uq.progress, uq.completed, uq.completion_date
                FROM quests q
                LEFT JOIN user_quests uq ON q.quest_id = uq.quest_id AND uq.user_id = ?
                WHERE q.quest_id LIKE ?
                ORDER BY uq.completed, q.difficulty
            """, (user_id, f"{quest_type}_%"))
        else:
            cursor.execute("""
                SELECT q.quest_id, q.title, q.description, q.requirements, 
                       q.token_reward, q.xp_reward, q.item_rewards, q.difficulty,
                       uq.progress, uq.completed, uq.completion_date
                FROM quests q
                LEFT JOIN user_quests uq ON q.quest_id = uq.quest_id AND uq.user_id = ?
                ORDER BY uq.completed, q.difficulty
            """, (user_id,))
            
        quest_rows = cursor.fetchall()
        conn.close()
        
        # If no quests found in DB, they haven't been initialized
        if not quest_rows:
            # Initialize quests from the quest file
            await self._initialize_quests_for_user(user_id)
            
            # Try again
            conn = get_connection()
            cursor = conn.cursor()
            if quest_type and quest_type != "all":
                cursor.execute("""
                    SELECT q.quest_id, q.title, q.description, q.requirements, 
                           q.token_reward, q.xp_reward, q.item_rewards, q.difficulty,
                           uq.progress, uq.completed, uq.completion_date
                    FROM quests q
                    LEFT JOIN user_quests uq ON q.quest_id = uq.quest_id AND uq.user_id = ?
                    WHERE q.quest_id LIKE ?
                    ORDER BY uq.completed, q.difficulty
                """, (user_id, f"{quest_type}_%"))
            else:
                cursor.execute("""
                    SELECT q.quest_id, q.title, q.description, q.requirements, 
                           q.token_reward, q.xp_reward, q.item_rewards, q.difficulty,
                           uq.progress, uq.completed, uq.completion_date
                    FROM quests q
                    LEFT JOIN user_quests uq ON q.quest_id = uq.quest_id AND uq.user_id = ?
                    ORDER BY uq.completed, q.difficulty
                """, (user_id,))
                
            quest_rows = cursor.fetchall()
            conn.close()
        
        # Group quests by category
        active_quests = {}
        completed_quests = {}
        
        for quest in quest_rows:
            quest_id, title, description, requirements, token_reward, xp_reward, item_rewards, difficulty, progress, completed, completion_date = quest
            
            # Determine category from quest_id prefix
            if "_" in quest_id:
                category = quest_id.split("_")[0]
            else:
                category = "other"
                
            # Parse JSON fields
            try:
                requirements = json.loads(requirements) if requirements else {}
                item_rewards = json.loads(item_rewards) if item_rewards else []
                progress = json.loads(progress) if progress else {"current": 0}
            except:
                requirements = {}
                item_rewards = []
                progress = {"current": 0}
            
            # Create formatted quest entry
            quest_entry = {
                "id": quest_id,
                "title": title,
                "description": description,
                "requirements": requirements,
                "token_reward": token_reward,
                "xp_reward": xp_reward,
                "item_rewards": item_rewards,
                "difficulty": difficulty,
                "progress": progress,
                "completed": completed == 1,
                "completion_date": completion_date
            }
            
            # Add to appropriate category
            if completed == 1:
                if category not in completed_quests:
                    completed_quests[category] = []
                completed_quests[category].append(quest_entry)
            else:
                if category not in active_quests:
                    active_quests[category] = []
                active_quests[category].append(quest_entry)
                
        # Create embeds for active and completed quests
        active_embed = discord.Embed(
            title="Active Quests",
            description="Your currently active quests and progress.",
            color=discord.Color.blue()
        )
        
        completed_embed = discord.Embed(
            title="Completed Quests",
            description="Quests you've already completed.",
            color=discord.Color.green()
        )
        
        # Add active quests to embed
        if not active_quests:
            active_embed.description = "You have no active quests. Try again tomorrow for new daily quests!"
        else:
            for category, quests in active_quests.items():
                category_name = category.capitalize()
                quest_text = ""
                
                for quest in quests:
                    req_type = quest["requirements"].get("type", "unknown")
                    req_count = quest["requirements"].get("count", 1)
                    current = quest["progress"].get("current", 0)
                    
                    # Create progress bar
                    progress_percent = min(int((current / req_count) * 10), 10)
                    progress_bar = "█" * progress_percent + "░" * (10 - progress_percent)
                    
                    # Format rewards
                    rewards = f"🪙 {quest['token_reward']} tokens | ✨ {quest['xp_reward']} XP"
                    if quest["item_rewards"]:
                        rewards += " | 🎁 Items"
                    
                    quest_text += f"**{quest['title']}** ({quest['difficulty']})\n"
                    quest_text += f"{quest['description']}\n"
                    quest_text += f"Progress: {current}/{req_count} {progress_bar} {int(current/req_count*100)}%\n"
                    quest_text += f"Rewards: {rewards}\n\n"
                    
                if quest_text:
                    active_embed.add_field(
                        name=f"{category_name} Quests",
                        value=quest_text,
                        inline=False
                    )
        
        # Add completed quests to embed
        if not completed_quests:
            completed_embed.description = "You haven't completed any quests yet."
        else:
            for category, quests in completed_quests.items():
                category_name = category.capitalize()
                quest_text = ""
                
                for quest in quests:
                    completion_date = quest.get("completion_date", "Unknown")
                    if completion_date and completion_date != "Unknown":
                        try:
                            completion_dt = datetime.datetime.fromisoformat(completion_date)
                            completion_date = completion_dt.strftime("%Y-%m-%d")
                        except:
                            pass
                    
                    quest_text += f"**{quest['title']}** ({quest['difficulty']})\n"
                    quest_text += f"{quest['description']}\n"
                    quest_text += f"Completed: {completion_date}\n\n"
                    
                if quest_text:
                    completed_embed.add_field(
                        name=f"{category_name} Quests",
                        value=quest_text,
                        inline=False
                    )
                    
        # Determine which embed to show based on active/completed count
        if quest_type == "all" or not quest_type:
            if active_quests:
                await interaction.response.send_message(embed=active_embed)
            else:
                await interaction.response.send_message(embed=completed_embed)
        elif quest_type in ["daily", "weekly", "achievement", "story"]:
            has_active = any(k.startswith(quest_type) for k in active_quests.keys())
            has_completed = any(k.startswith(quest_type) for k in completed_quests.keys())
            
            if has_active:
                await interaction.response.send_message(embed=active_embed)
            elif has_completed:
                await interaction.response.send_message(embed=completed_embed)
            else:
                await interaction.response.send_message(
                    f"You don't have any {quest_type} quests. Try checking other quest types.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "Invalid quest type specified.",
                ephemeral=True
            )

    async def _initialize_quests_for_user(self, user_id: str):
        """Initialize quests for a user from the quest data file."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # First check if we need to initialize the quests table
        cursor.execute("SELECT COUNT(*) FROM quests")
        quest_count = cursor.fetchone()[0]
        
        # If no quests in the table, initialize from quest data file
        if quest_count == 0:
            # For each quest type in the quest data
            for quest_category, quests in self.quests.items():
                for quest in quests:
                    quest_id = quest["id"]
                    requirements_json = json.dumps(quest.get("requirements", {}))
                    item_rewards_json = json.dumps(quest.get("item_rewards", []))
                    
                    # Insert quest into quests table
                    cursor.execute("""
                        INSERT INTO quests 
                        (quest_id, title, description, requirements, token_reward, xp_reward, item_rewards, difficulty)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        quest_id, 
                        quest["title"], 
                        quest["description"], 
                        requirements_json,
                        quest.get("token_reward", 0),
                        quest.get("xp_reward", 0),
                        item_rewards_json,
                        quest.get("difficulty", "normal")
                    ))
        
        # Now initialize user's quests
        # First get all quest IDs from the quests table
        cursor.execute("SELECT quest_id FROM quests")
        all_quests = cursor.fetchall()
        
        # For each quest, check if user already has it
        for (quest_id,) in all_quests:
            cursor.execute("""
                SELECT COUNT(*) FROM user_quests 
                WHERE user_id = ? AND quest_id = ?
            """, (user_id, quest_id))
            
            has_quest = cursor.fetchone()[0] > 0
            
            # If not, add it with default progress
            if not has_quest:
                # Add daily and weekly quests only if they're current
                if quest_id.startswith("daily_") or quest_id.startswith("weekly_"):
                    # For now, always add them
                    default_progress = json.dumps({"current": 0})
                    cursor.execute("""
                        INSERT INTO user_quests (user_id, quest_id, progress, completed)
                        VALUES (?, ?, ?, 0)
                    """, (user_id, quest_id, default_progress))
                else:
                    # For story and achievement quests, always add
                    default_progress = json.dumps({"current": 0})
                    cursor.execute("""
                        INSERT INTO user_quests (user_id, quest_id, progress, completed)
                        VALUES (?, ?, ?, 0)
                    """, (user_id, quest_id, default_progress))
        
        conn.commit()
        conn.close()

    async def update_quest_progress(self, user_id: str, quest_type: str, count: int = 1, **kwargs):
        """
        Update a user's progress on quests of a specific type.
        
        Args:
            user_id: The user's Discord ID
            quest_type: The type of action (catch, battle_win, etc.)
            count: How much to increment progress by
            **kwargs: Additional criteria for specific quest types
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all of the user's active quests of this type
        cursor.execute("""
            SELECT q.quest_id, q.requirements, uq.progress, q.token_reward, q.xp_reward, q.item_rewards
            FROM quests q
            JOIN user_quests uq ON q.quest_id = uq.quest_id
            WHERE uq.user_id = ? AND uq.completed = 0
        """, (user_id,))
        
        quest_rows = cursor.fetchall()
        completed_quests = []
        
        for quest_row in quest_rows:
            quest_id, requirements_json, progress_json, token_reward, xp_reward, item_rewards_json = quest_row
            
            try:
                requirements = json.loads(requirements_json)
                progress = json.loads(progress_json)
                item_rewards = json.loads(item_rewards_json) if item_rewards_json else []
            except:
                continue
                
            # Check if this quest matches the quest_type
            if requirements.get("type") == quest_type:
                # Check additional criteria if any
                matches_criteria = True
                
                # For rarity-specific quests
                if "min_rarity" in requirements and "rarity" in kwargs:
                    rarity_levels = ["common", "uncommon", "rare", "legendary", "mythic"]
                    min_index = rarity_levels.index(requirements["min_rarity"])
                    actual_index = rarity_levels.index(kwargs["rarity"]) if kwargs["rarity"] in rarity_levels else -1
                    
                    if actual_index < min_index:
                        matches_criteria = False
                
                # For type-specific quests
                if "type_name" in requirements and "type_name" in kwargs:
                    if requirements["type_name"] != "random" and requirements["type_name"] != kwargs["type_name"]:
                        matches_criteria = False
                
                # For biome-specific quests
                if "biome" in requirements and "biome" in kwargs:
                    if requirements["biome"] != kwargs["biome"]:
                        matches_criteria = False
                        
                # For battle type specific quests
                if "battle_type" in requirements and "battle_type" in kwargs:
                    if requirements["battle_type"] != kwargs["battle_type"]:
                        matches_criteria = False
                
                # If all criteria match, update progress
                if matches_criteria:
                    # Initialize current progress if not present
                    if "current" not in progress:
                        progress["current"] = 0
                    
                    # For biome exploration, track unique biomes
                    if quest_type == "explore_unique_biomes" and "biome" in kwargs:
                        if "biomes" not in progress:
                            progress["biomes"] = []
                            
                        if kwargs["biome"] not in progress["biomes"]:
                            progress["biomes"].append(kwargs["biome"])
                            progress["current"] = len(progress["biomes"])
                    else:
                        # For normal counters, just increment
                        progress["current"] += count
                    
                    # Check if quest is now complete
                    if progress["current"] >= requirements.get("count", 1):
                        # Mark as completed
                        completion_date = datetime.datetime.now().isoformat()
                        cursor.execute("""
                            UPDATE user_quests
                            SET progress = ?, completed = 1, completion_date = ?
                            WHERE user_id = ? AND quest_id = ?
                        """, (json.dumps(progress), completion_date, user_id, quest_id))
                        
                        # Add to list of completed quests to process rewards
                        completed_quests.append({
                            "quest_id": quest_id,
                            "token_reward": token_reward,
                            "xp_reward": xp_reward,
                            "item_rewards": item_rewards
                        })
                    else:
                        # Just update progress
                        cursor.execute("""
                            UPDATE user_quests
                            SET progress = ?
                            WHERE user_id = ? AND quest_id = ?
                        """, (json.dumps(progress), user_id, quest_id))
        
        # Process rewards for completed quests
        for quest in completed_quests:
            # Add tokens and XP
            cursor.execute("""
                UPDATE users 
                SET tokens = tokens + ?, xp = xp + ?
                WHERE user_id = ?
            """, (quest["token_reward"], quest["xp_reward"], user_id))
            
            # Add any item rewards
            for item_reward in quest["item_rewards"]:
                item_id = item_reward.get("item_id")
                quantity = item_reward.get("quantity", 1)
                
                if item_id in self.items:
                    await self._add_item_to_inventory(user_id, item_id, quantity)
        
        conn.commit()
        conn.close()
        
        # Return info about completed quests for notifications
        return completed_quests

    @app_commands.command(name="transfer", description="Transfer tokens to another player")
    @app_commands.describe(
        user="The user to transfer tokens to",
        amount="The amount of tokens to transfer",
        message="Optional message to include with the transfer"
    )
    @require_permission_level(PermissionLevel.USER)
    async def transfer(self, interaction: discord.Interaction, user: discord.Member, amount: int, message: Optional[str] = None):
        """Transfer tokens to another player."""
        sender_id = str(interaction.user.id)
        recipient_id = str(user.id)
        
        # Prevent self-transfers
        if sender_id == recipient_id:
            await interaction.response.send_message("You cannot transfer tokens to yourself.", ephemeral=True)
            return
            
        # Validate amount
        if amount <= 0:
            await interaction.response.send_message("Transfer amount must be positive.", ephemeral=True)
            return
            
        # Security validation through security system
        security = get_security_integration()
        validation_result = await security.validate_token_transaction(
            sender_id, amount, "transfer", recipient_id
        )
        
        if not validation_result["valid"]:
            await interaction.response.send_message(validation_result["error"], ephemeral=True)
            return
            
        # Process the transfer
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check sender balance
            cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (sender_id,))
            sender_row = cursor.fetchone()
            
            if not sender_row:
                await interaction.response.send_message("You don't have an account yet.", ephemeral=True)
                conn.close()
                return
                
            sender_balance = sender_row[0]
            if sender_balance < amount:
                await interaction.response.send_message(
                    f"Insufficient balance. You have {sender_balance:,} tokens, but tried to transfer {amount:,}.",
                    ephemeral=True
                )
                conn.close()
                return
                
            # Check if recipient exists, create if not
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (recipient_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (user_id, tokens, xp) VALUES (?, 0, 0)", (recipient_id,))
                
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Deduct from sender
            cursor.execute(
                "UPDATE users SET tokens = tokens - ? WHERE user_id = ?",
                (amount, sender_id)
            )
            
            # Add to recipient
            cursor.execute(
                "UPDATE users SET tokens = tokens + ? WHERE user_id = ?",
                (amount, recipient_id)
            )
            
            # Record the transaction
            transaction_time = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO token_transactions 
                (sender_id, recipient_id, amount, transaction_time, message, transaction_type)
                VALUES (?, ?, ?, ?, ?, 'transfer')
            """, (sender_id, recipient_id, amount, transaction_time, message))
            
            conn.execute("COMMIT")
            
            # Get new balances
            cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (sender_id,))
            new_sender_balance = cursor.fetchone()[0]
            
            # Security logging
            security.log_security_event(
                user_id=sender_id,
                event_type="token_transfer",
                details={
                    "recipient_id": recipient_id,
                    "amount": amount,
                    "timestamp": transaction_time
                }
            )
            
            # Create success embed
            embed = discord.Embed(
                title="Token Transfer Successful",
                description=f"Successfully transferred **{amount:,}** tokens to {user.mention}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="New Balance", value=f"{new_sender_balance:,} tokens", inline=True)
            
            if message:
                embed.add_field(name="Message", value=message, inline=False)
                
            embed.set_footer(text="Thank you for using Veramon Bank!")
            
            # Notify the recipient if they're online
            try:
                recipient_embed = discord.Embed(
                    title="Tokens Received!",
                    description=f"You received **{amount:,}** tokens from {interaction.user.mention}",
                    color=discord.Color.gold()
                )
                
                if message:
                    recipient_embed.add_field(name="Message", value=message, inline=False)
                    
                cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (recipient_id,))
                new_recipient_balance = cursor.fetchone()[0]
                recipient_embed.add_field(
                    name="New Balance", 
                    value=f"{new_recipient_balance:,} tokens", 
                    inline=True
                )
                
                # Only send DM if user is a member of the guild
                if isinstance(user, discord.Member):
                    await user.send(embed=recipient_embed)
            except Exception as e:
                # Silently fail if we can't message the recipient
                print(f"Error sending transfer notification to recipient: {e}")
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            # Rollback on error
            conn.execute("ROLLBACK")
            print(f"Error processing token transfer: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your transfer. Please try again later.",
                ephemeral=True
            )
        finally:
            conn.close()
            
    @app_commands.command(name="transaction_history", description="View your token transaction history")
    @app_commands.describe(
        transaction_type="Filter by transaction type",
        limit="Number of transactions to show (default: 10)"
    )
    @app_commands.choices(
        transaction_type=[
            app_commands.Choice(name="All", value="all"),
            app_commands.Choice(name="Transfers", value="transfer"),
            app_commands.Choice(name="Shop Purchases", value="purchase"),
            app_commands.Choice(name="Battle Rewards", value="battle_reward"),
            app_commands.Choice(name="Daily Bonuses", value="daily_bonus")
        ]
    )
    @require_permission_level(PermissionLevel.USER)
    async def transaction_history(
        self, 
        interaction: discord.Interaction, 
        transaction_type: str = "all", 
        limit: int = 10
    ):
        """View your token transaction history."""
        user_id = str(interaction.user.id)
        
        # Validate limit
        if limit <= 0 or limit > 25:
            await interaction.response.send_message(
                "Limit must be between 1 and 25 transactions.",
                ephemeral=True
            )
            return
            
        # Security validation
        security = get_security_integration()
        validation_result = await security.validate_transaction_history_view(user_id, transaction_type, limit)
        if not validation_result["valid"]:
            await interaction.response.send_message(validation_result["error"], ephemeral=True)
            return
            
        # Fetch transaction history
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            if transaction_type == "all":
                # Combined incoming and outgoing
                cursor.execute("""
                    SELECT 
                        'outgoing' as direction, 
                        sender_id, 
                        recipient_id, 
                        amount, 
                        transaction_time, 
                        message, 
                        transaction_type 
                    FROM token_transactions 
                    WHERE sender_id = ?
                    UNION ALL
                    SELECT 
                        'incoming' as direction, 
                        sender_id, 
                        recipient_id, 
                        amount, 
                        transaction_time, 
                        message, 
                        transaction_type 
                    FROM token_transactions 
                    WHERE recipient_id = ? AND sender_id != recipient_id
                    ORDER BY transaction_time DESC
                    LIMIT ?
                """, (user_id, user_id, limit))
            else:
                # Combined with type filter
                cursor.execute("""
                    SELECT 
                        'outgoing' as direction, 
                        sender_id, 
                        recipient_id, 
                        amount, 
                        transaction_time, 
                        message, 
                        transaction_type 
                    FROM token_transactions 
                    WHERE sender_id = ? AND transaction_type = ?
                    UNION ALL
                    SELECT 
                        'incoming' as direction, 
                        sender_id, 
                        recipient_id, 
                        amount, 
                        transaction_time, 
                        message, 
                        transaction_type 
                    FROM token_transactions 
                    WHERE recipient_id = ? AND sender_id != recipient_id AND transaction_type = ?
                    ORDER BY transaction_time DESC
                    LIMIT ?
                """, (user_id, transaction_type, user_id, transaction_type, limit))
                
            transactions = cursor.fetchall()
            
            # Get current balance
            cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
            balance_row = cursor.fetchone()
            current_balance = balance_row[0] if balance_row else 0
            
            # Create embed
            embed = discord.Embed(
                title="Token Transaction History",
                description=f"Your current balance: **{current_balance:,}** tokens",
                color=discord.Color.blue()
            )
            
            if transaction_type != "all":
                embed.description += f"\nFiltering by: **{transaction_type}**"
                
            # Format transactions
            for direction, sender_id, recipient_id, amount, transaction_time, message, tx_type in transactions:
                # Format transaction time
                try:
                    dt = datetime.fromisoformat(transaction_time)
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = transaction_time
                    
                # Get user display names
                try:
                    if direction == "outgoing":
                        recipient = await interaction.guild.fetch_member(int(recipient_id))
                        recipient_name = recipient.display_name if recipient else f"User {recipient_id}"
                        title = f"Sent {amount:,} tokens to {recipient_name}"
                    else:
                        sender = await interaction.guild.fetch_member(int(sender_id))
                        sender_name = sender.display_name if sender else f"User {sender_id}"
                        title = f"Received {amount:,} tokens from {sender_name}"
                except:
                    # Fallback if we can't resolve names
                    if direction == "outgoing":
                        title = f"Sent {amount:,} tokens"
                    else:
                        title = f"Received {amount:,} tokens"
                        
                # Format transaction type nicely
                type_display = tx_type.replace("_", " ").title()
                
                # Create field value
                value = f"**Type:** {type_display}\n**Time:** {time_str}"
                if message:
                    # Truncate long messages
                    if len(message) > 100:
                        message = message[:97] + "..."
                    value += f"\n**Message:** {message}"
                    
                embed.add_field(
                    name=title,
                    value=value,
                    inline=False
                )
                
            if not transactions:
                embed.add_field(
                    name="No transactions found",
                    value="You don't have any transactions matching the selected criteria.",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error fetching transaction history: {e}")
            await interaction.response.send_message(
                "An error occurred while fetching your transaction history.",
                ephemeral=True
            )
        finally:
            conn.close()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))
