import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import json
from src.db.db import get_connection  # This function should return an SQLite connection
from src.models.permissions import require_permission_level, PermissionLevel, is_admin

def initialize_economy_db():
    """
    Ensure the 'users' table exists in the database.
    The table stores user_id, tokens, and XP.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        tokens INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id TEXT,
        item_id TEXT,
        quantity INTEGER,
        PRIMARY KEY (user_id, item_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    conn.commit()
    conn.close()

class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_economy_db()  # Create/update the users table on load
        # Load items data
        items_path = os.path.join(os.path.dirname(__file__), "..", "data", "items.json")
        with open(items_path, "r") as f:
            self.items = json.load(f)

    @app_commands.command(name="balance", description="Check your current token balance.")
    @require_permission_level(PermissionLevel.USER)
    async def balance(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tokens, xp FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            tokens, xp = row
        else:
            tokens, xp = 0, 0  # Default values if user is not in the table
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Balance",
            description=f"You have **{tokens} tokens** and **{xp} XP**.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="earn", description="Simulate earning tokens (for testing purposes).")
    @app_commands.describe(amount="Amount of tokens to earn (must be positive)")
    @require_permission_level(PermissionLevel.USER)
    async def earn(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()
        # Check if the user already exists in the database.
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            new_balance = row[0] + amount
            cursor.execute("UPDATE users SET tokens = ? WHERE user_id = ?", (new_balance, user_id))
        else:
            new_balance = amount
            cursor.execute("INSERT INTO users (user_id, tokens, xp) VALUES (?, ?, ?)", (user_id, new_balance, 0))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ You earned {amount} tokens! Your new balance is **{new_balance} tokens**.")

    @app_commands.command(name="transfer", description="Transfer tokens to another user.")
    @app_commands.describe(recipient="The user to receive tokens", amount="Amount to transfer (must be positive)")
    @require_permission_level(PermissionLevel.USER)
    async def transfer(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        sender_id = str(interaction.user.id)
        recipient_id = str(recipient.id)
        conn = get_connection()
        cursor = conn.cursor()

        # Check sender's balance
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (sender_id,))
        sender_row = cursor.fetchone()
        if not sender_row or sender_row[0] < amount:
            await interaction.response.send_message("Insufficient token balance.", ephemeral=True)
            conn.close()
            return

        sender_new_balance = sender_row[0] - amount
        cursor.execute("UPDATE users SET tokens = ? WHERE user_id = ?", (sender_new_balance, sender_id))

        # Update or insert for recipient
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (recipient_id,))
        recipient_row = cursor.fetchone()
        if recipient_row:
            recipient_new_balance = recipient_row[0] + amount
            cursor.execute("UPDATE users SET tokens = ? WHERE user_id = ?", (recipient_new_balance, recipient_id))
        else:
            recipient_new_balance = amount
            cursor.execute("INSERT INTO users (user_id, tokens, xp) VALUES (?, ?, ?)", (recipient_id, recipient_new_balance, 0))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ Transferred {amount} tokens from {interaction.user.display_name} to {recipient.display_name}.")

    @app_commands.command(name="shop", description="Display available catch items in the shop.")
    @require_permission_level(PermissionLevel.USER)
    async def shop(self, interaction: discord.Interaction):
        shop_items = []
        for item_id, item in self.items.items():
            price = item.get("price", 100)  # Default price if not specified
            shop_items.append(f"**{item['name']}** (ID: `{item_id}`) - {item['description']} | Multiplier: {item['multiplier']} | Price: **{price} tokens**")

        embed = discord.Embed(
            title="Shop Items",
            description="\n".join(shop_items),
            color=discord.Color.green()
        )
        embed.set_footer(text="Use /shop_buy item_id:item_id to purchase an item")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop_buy", description="Purchase an item from the shop")
    @app_commands.describe(item_id="The ID of the item to purchase", quantity="Number of items to buy (default: 1)")
    @require_permission_level(PermissionLevel.USER)
    async def shop_buy(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        """Purchase an item from the shop using tokens."""
        if quantity <= 0:
            await interaction.response.send_message("Quantity must be positive.", ephemeral=True)
            return

        # Check if item exists
        if item_id not in self.items:
            await interaction.response.send_message(f"Item with ID '{item_id}' not found in shop.", ephemeral=True)
            return

        item = self.items[item_id]
        price = item.get("price", 100) * quantity

        user_id = str(interaction.user.id)
        conn = get_connection()
        cursor = conn.cursor()

        # Check user's token balance
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row or row[0] < price:
            await interaction.response.send_message(
                f"Insufficient tokens. You need {price} tokens to buy {quantity}x {item['name']}.", 
                ephemeral=True
            )
            conn.close()
            return

        # Deduct tokens
        new_balance = row[0] - price
        cursor.execute("UPDATE users SET tokens = ? WHERE user_id = ?", (new_balance, user_id))

        # Add item to inventory
        cursor.execute(
            "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", 
            (user_id, item_id)
        )
        inv_row = cursor.fetchone()

        if inv_row:
            new_quantity = inv_row[0] + quantity
            cursor.execute(
                "UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?",
                (new_quantity, user_id, item_id)
            )
        else:
            cursor.execute(
                "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)",
                (user_id, item_id, quantity)
            )

        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="Purchase Successful!",
            description=f"You purchased {quantity}x **{item['name']}** for **{price} tokens**.",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"{new_balance} tokens", inline=True)
        embed.add_field(name="Item Effect", value=f"Catch rate multiplier: {item['multiplier']}", inline=True)
        embed.set_footer(text="Use this item with /catch item_id:item_id")

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
            cursor.execute("INSERT INTO users (user_id, tokens, xp) VALUES (?, ?, ?)", (target_id, amount, 0))

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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))
