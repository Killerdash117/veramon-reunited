import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
from src.db.db import get_connection  # This function should return an SQLite connection

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
    conn.commit()
    conn.close()

class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_economy_db()  # Create/update the users table on load

    @app_commands.command(name="balance", description="Check your current token balance.")
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
    async def shop(self, interaction: discord.Interaction):
        # Load items from the JSON file
        items_path = os.path.join(os.path.dirname(__file__), "..", "data", "items.json")
        try:
            with open(items_path, "r") as f:
                items = json.load(f)
        except Exception as e:
            await interaction.response.send_message(f"Error loading shop data: {e}", ephemeral=True)
            return

        shop_items = []
        for item_id, item in items.items():
            shop_items.append(f"**{item['name']}** (ID: {item_id}) - {item['description']} | Multiplier: {item['multiplier']}")

        embed = discord.Embed(
            title="Shop Items",
            description="\n".join(shop_items),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))
