import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel, is_admin, is_mod


class FactionCog(commands.Cog):
    """
    Advanced faction system for Veramon Reunited.
    
    Factions are large-scale organizations that players can join, with:
    - Hierarchical rank system
    - Shared resources and upgrades
    - Territory control
    - Faction wars
    - Raid events
    
    Unlike guilds (small parties), factions are meant to be few but powerful.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.setup_default_ranks()
        
    def setup_default_ranks(self):
        """Set up default ranks for new factions."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if any factions exist without ranks
        cursor.execute("""
            SELECT f.faction_id 
            FROM factions f 
            LEFT JOIN faction_ranks fr ON f.faction_id = fr.faction_id 
            WHERE fr.rank_id IS NULL
        """)
        
        factions_without_ranks = cursor.fetchall()
        
        for (faction_id,) in factions_without_ranks:
            # Create default ranks
            default_ranks = [
                (faction_id, "Leader", 5, json.dumps(["manage_faction", "manage_ranks", "manage_members", "manage_wars", "manage_territories", "manage_upgrades"])),
                (faction_id, "Officer", 4, json.dumps(["manage_members", "manage_wars", "manage_territories"])),
                (faction_id, "Veteran", 3, json.dumps(["participate_wars", "claim_territories"])),
                (faction_id, "Member", 2, json.dumps(["participate_wars"])),
                (faction_id, "Recruit", 1, json.dumps([]))
            ]
            
            for rank in default_ranks:
                cursor.execute("""
                    INSERT INTO faction_ranks (faction_id, name, level, permissions)
                    VALUES (?, ?, ?, ?)
                """, rank)
                
        conn.commit()
        conn.close()

    @app_commands.command(name="faction_create", description="Create a new faction (ADMIN ONLY - Very Expensive)")
    @app_commands.describe(
        name="Name of the new faction",
        description="Brief description of the faction",
        motto="The faction's motto",
        color="Color hex code (e.g., #FF0000 for red)"
    )
    @is_admin()  # Only admins can create factions
    async def faction_create(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        description: str, 
        motto: str, 
        color: str = "#0099ff"
    ):
        """Create a new faction. Restricted to ADMIN role due to cost and impact."""
        # Check if color is valid hex
        if not color.startswith("#"):
            color = f"#{color}"
        
        try:
            # Validate hex color
            int(color[1:], 16)
        except ValueError:
            await interaction.response.send_message(
                "Invalid color hex code. Use format #RRGGBB (e.g., #FF0000 for red).",
                ephemeral=True
            )
            return
            
        # Normalize color to 6 digits without # prefix for storage
        color = color[1:].lower()
        if len(color) == 3:
            color = ''.join(c + c for c in color)
        
        # Create faction in database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if name already exists
        cursor.execute("SELECT COUNT(*) FROM factions WHERE name = ?", (name,))
        if cursor.fetchone()[0] > 0:
            await interaction.response.send_message(
                f"A faction named '{name}' already exists. Please choose another name.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Create the faction
        cursor.execute("""
            INSERT INTO factions (name, leader_id, description, motto, color)
            VALUES (?, ?, ?, ?, ?)
        """, (name, str(interaction.user.id), description, motto, color))
        
        faction_id = cursor.lastrowid
        
        # Set up default ranks
        default_ranks = [
            (faction_id, "Leader", 5, json.dumps(["manage_faction", "manage_ranks", "manage_members", "manage_wars", "manage_territories", "manage_upgrades"])),
            (faction_id, "Officer", 4, json.dumps(["manage_members", "manage_wars", "manage_territories"])),
            (faction_id, "Veteran", 3, json.dumps(["participate_wars", "claim_territories"])),
            (faction_id, "Member", 2, json.dumps(["participate_wars"])),
            (faction_id, "Recruit", 1, json.dumps([]))
        ]
        
        for rank in default_ranks:
            cursor.execute("""
                INSERT INTO faction_ranks (faction_id, name, level, permissions)
                VALUES (?, ?, ?, ?)
            """, rank)
            
        # Get the leader rank ID
        cursor.execute("""
            SELECT rank_id FROM faction_ranks 
            WHERE faction_id = ? AND name = 'Leader'
        """, (faction_id,))
        
        leader_rank_id = cursor.fetchone()[0]
        
        # Add the admin as the faction leader
        cursor.execute("""
            INSERT INTO faction_members (faction_id, user_id, rank_id)
            VALUES (?, ?, ?)
        """, (faction_id, str(interaction.user.id), leader_rank_id))
        
        # Update user record to show faction membership
        cursor.execute("""
            UPDATE users SET faction_id = ? WHERE user_id = ?
        """, (faction_id, str(interaction.user.id)))
        
        conn.commit()
        conn.close()
        
        # Create an embed to show the faction details
        embed = discord.Embed(
            title=f"Faction Created: {name}",
            description=description,
            color=int(color, 16)
        )
        embed.add_field(name="Motto", value=motto, inline=False)
        embed.add_field(name="Leader", value=interaction.user.display_name, inline=True)
        embed.add_field(name="Members", value="1/50", inline=True)
        embed.add_field(name="ID", value=str(faction_id), inline=True)
        embed.set_footer(text="Use /faction_info to see faction details")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="faction_info", description="View information about a faction")
    @app_commands.describe(faction_name="Name of the faction (leave blank for your own faction)")
    @require_permission_level(PermissionLevel.USER)
    async def faction_info(self, interaction: discord.Interaction, faction_name: Optional[str] = None):
        """View detailed information about a faction."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # If no faction name provided, look up user's faction
        if not faction_name:
            cursor.execute("""
                SELECT faction_id FROM users WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row or not row[0]:
                await interaction.response.send_message(
                    "You are not a member of any faction. Specify a faction name or join a faction first.",
                    ephemeral=True
                )
                conn.close()
                return
                
            faction_id = row[0]
        else:
            # Look up faction by name
            cursor.execute("""
                SELECT faction_id FROM factions WHERE name = ?
            """, (faction_name,))
            
            row = cursor.fetchone()
            if not row:
                await interaction.response.send_message(
                    f"No faction found with name '{faction_name}'.",
                    ephemeral=True
                )
                conn.close()
                return
                
            faction_id = row[0]
            
        # Get faction details
        cursor.execute("""
            SELECT name, leader_id, description, motto, level, experience, tokens,
                   member_capacity, color, created_at
            FROM factions WHERE faction_id = ?
        """, (faction_id,))
        
        faction = cursor.fetchone()
        if not faction:
            await interaction.response.send_message(
                "Error: Faction data not found.",
                ephemeral=True
            )
            conn.close()
            return
            
        name, leader_id, description, motto, level, exp, tokens, capacity, color, created_at = faction
        
        # Get member count
        cursor.execute("""
            SELECT COUNT(*) FROM faction_members WHERE faction_id = ?
        """, (faction_id,))
        
        member_count = cursor.fetchone()[0]
        
        # Get upgrades
        cursor.execute("""
            SELECT fu.name, fpu.level, fu.max_level
            FROM faction_purchased_upgrades fpu
            JOIN faction_upgrades fu ON fpu.upgrade_id = fu.upgrade_id
            WHERE fpu.faction_id = ?
        """, (faction_id,))
        
        upgrades = cursor.fetchall()
        
        # Get territories
        cursor.execute("""
            SELECT COUNT(*) FROM faction_territories
            WHERE controlling_faction_id = ?
        """, (faction_id,))
        
        territory_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Format created date
        created_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d")
        
        # Create embed with faction details
        embed = discord.Embed(
            title=f"Faction: {name}",
            description=description,
            color=int(color, 16) if color else 0x0099ff
        )
        
        # Add faction basics
        embed.add_field(name="Motto", value=motto, inline=False)
        embed.add_field(name="Level", value=f"{level} ({exp} XP)", inline=True)
        embed.add_field(name="Members", value=f"{member_count}/{capacity}", inline=True)
        embed.add_field(name="Treasury", value=f"{tokens} tokens", inline=True)
        
        # Add upgrades if any
        if upgrades:
            upgrades_text = "\n".join([f"• {name} (Level {level}/{max_level})" for name, level, max_level in upgrades])
            embed.add_field(name="Upgrades", value=upgrades_text, inline=False)
        else:
            embed.add_field(name="Upgrades", value="No upgrades purchased yet", inline=False)
            
        # Add territories if any
        if territory_count > 0:
            embed.add_field(name="Territories", value=f"Controlling {territory_count} territories", inline=True)
            
        embed.set_footer(text=f"Created on {created_date} • ID: {faction_id}")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="faction_join", description="Request to join a faction")
    @app_commands.describe(faction_name="Name of the faction to join")
    @require_permission_level(PermissionLevel.USER)
    async def faction_join(self, interaction: discord.Interaction, faction_name: str):
        """Request to join a faction."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is already in a faction
        cursor.execute("""
            SELECT f.name FROM factions f
            JOIN users u ON f.faction_id = u.faction_id
            WHERE u.user_id = ? AND u.faction_id IS NOT NULL
        """, (user_id,))
        
        existing_faction = cursor.fetchone()
        if existing_faction:
            await interaction.response.send_message(
                f"You are already a member of faction '{existing_faction[0]}'. Leave that faction first.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Find the requested faction
        cursor.execute("""
            SELECT faction_id, member_capacity FROM factions WHERE name = ?
        """, (faction_name,))
        
        faction = cursor.fetchone()
        if not faction:
            await interaction.response.send_message(
                f"No faction found with name '{faction_name}'.",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, capacity = faction
        
        # Check if faction is full
        cursor.execute("""
            SELECT COUNT(*) FROM faction_members WHERE faction_id = ?
        """, (faction_id,))
        
        member_count = cursor.fetchone()[0]
        if member_count >= capacity:
            await interaction.response.send_message(
                f"Faction '{faction_name}' is full ({member_count}/{capacity} members).",
                ephemeral=True
            )
            conn.close()
            return
            
        # Get the Recruit rank
        cursor.execute("""
            SELECT rank_id FROM faction_ranks 
            WHERE faction_id = ? AND name = 'Recruit'
        """, (faction_id,))
        
        rank_row = cursor.fetchone()
        if not rank_row:
            await interaction.response.send_message(
                "Error: Faction rank structure is corrupted.",
                ephemeral=True
            )
            conn.close()
            return
            
        recruit_rank_id = rank_row[0]
        
        # Add user to faction with Recruit rank
        cursor.execute("""
            INSERT INTO faction_members (faction_id, user_id, rank_id)
            VALUES (?, ?, ?)
        """, (faction_id, user_id, recruit_rank_id))
        
        # Update user record
        cursor.execute("""
            UPDATE users SET faction_id = ? WHERE user_id = ?
        """, (faction_id, user_id))
        
        # Get faction details for confirmation message
        cursor.execute("""
            SELECT name, color, motto FROM factions WHERE faction_id = ?
        """, (faction_id,))
        
        faction_details = cursor.fetchone()
        name, color, motto = faction_details
        
        conn.commit()
        conn.close()
        
        # Create confirmation embed
        embed = discord.Embed(
            title=f"Welcome to {name}!",
            description=f"You have joined the faction as a Recruit.\n\n*{motto}*",
            color=int(color, 16) if color else 0x0099ff
        )
        
        embed.add_field(name="Rank", value="Recruit (Level 1)", inline=True)
        embed.add_field(name="Members", value=f"{member_count + 1}/{capacity}", inline=True)
        embed.set_footer(text="Use /faction_info to see faction details")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="faction_leave", description="Leave your current faction")
    @require_permission_level(PermissionLevel.USER)
    async def faction_leave(self, interaction: discord.Interaction):
        """Leave your current faction."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is in a faction
        cursor.execute("""
            SELECT f.faction_id, f.name, f.leader_id 
            FROM factions f
            JOIN users u ON f.faction_id = u.faction_id
            WHERE u.user_id = ? AND u.faction_id IS NOT NULL
        """, (user_id,))
        
        faction = cursor.fetchone()
        if not faction:
            await interaction.response.send_message(
                "You are not a member of any faction.",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, leader_id = faction
        
        # Check if user is the faction leader
        if leader_id == user_id:
            await interaction.response.send_message(
                "You are the leader of this faction. Transfer leadership to another member with `/faction_promote_leader` before leaving.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Remove from faction
        cursor.execute("""
            DELETE FROM faction_members WHERE faction_id = ? AND user_id = ?
        """, (faction_id, user_id))
        
        # Update user record
        cursor.execute("""
            UPDATE users SET faction_id = NULL WHERE user_id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="Faction Membership Ended",
            description=f"You have left the faction '{faction_name}'.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="faction_upgrade", description="Purchase a faction upgrade")
    @app_commands.describe(
        upgrade_name="Name of the upgrade to purchase"
    )
    @require_permission_level(PermissionLevel.USER)
    async def faction_upgrade(self, interaction: discord.Interaction, upgrade_name: str):
        """Purchase a faction upgrade. Requires faction officer rank or higher."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check user's faction and rank permissions
        cursor.execute("""
            SELECT f.faction_id, f.name, f.tokens, fr.permissions
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            JOIN faction_ranks fr ON fm.rank_id = fr.rank_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_row = cursor.fetchone()
        if not faction_row:
            await interaction.response.send_message(
                "You are not a member of any faction.",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, faction_tokens, permissions = faction_row
        permissions = json.loads(permissions)
        
        # Check if user has permission
        if "manage_upgrades" not in permissions:
            await interaction.response.send_message(
                "You don't have permission to manage faction upgrades. This requires Officer rank or higher.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Find the upgrade
        cursor.execute("""
            SELECT upgrade_id, name, description, cost, max_level, effect_per_level
            FROM faction_upgrades
            WHERE name LIKE ?
        """, (f"%{upgrade_name}%",))
        
        upgrades = cursor.fetchall()
        
        if not upgrades:
            await interaction.response.send_message(
                f"No upgrade found matching '{upgrade_name}'. Use `/faction_upgrades` to see available upgrades.",
                ephemeral=True
            )
            conn.close()
            return
            
        if len(upgrades) > 1:
            # Multiple matches, show options
            options = "\n".join([f"• {u[1]}" for u in upgrades])
            await interaction.response.send_message(
                f"Multiple upgrades found matching '{upgrade_name}'. Please be more specific:\n{options}",
                ephemeral=True
            )
            conn.close()
            return
            
        upgrade_id, name, description, cost, max_level, effect = upgrades[0]
        
        # Check if already purchased and current level
        cursor.execute("""
            SELECT level FROM faction_purchased_upgrades
            WHERE faction_id = ? AND upgrade_id = ?
        """, (faction_id, upgrade_id))
        
        existing = cursor.fetchone()
        current_level = existing[0] if existing else 0
        
        if current_level >= max_level:
            await interaction.response.send_message(
                f"Your faction already has {name} at maximum level ({max_level}).",
                ephemeral=True
            )
            conn.close()
            return
            
        # Calculate current cost (increases with level)
        current_cost = cost * (current_level + 1)
        
        # Check if faction has enough tokens
        if faction_tokens < current_cost:
            await interaction.response.send_message(
                f"Your faction doesn't have enough tokens for this upgrade. Required: {current_cost}, Available: {faction_tokens}",
                ephemeral=True
            )
            conn.close()
            return
            
        # Confirm purchase with user
        next_level = current_level + 1
        effect_value = effect * next_level
        
        embed = discord.Embed(
            title=f"Confirm Faction Upgrade: {name}",
            description=f"**Cost:** {current_cost} tokens\n**New Level:** {next_level}/{max_level}\n\n{description}\n\nEffect at Level {next_level}: +{effect_value:.0%}",
            color=discord.Color.gold()
        )
        
        embed.set_footer(text=f"Faction Treasury: {faction_tokens} tokens → {faction_tokens - current_cost} tokens after purchase")
        
        # Create confirm/cancel buttons
        class ConfirmView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=60)
                self.cog = cog
                self.value = None
                
            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()
                
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()
                
        view = ConfirmView(self)
        await interaction.response.send_message(embed=embed, view=view)
        
        # Wait for user response
        await view.wait()
        
        if not view.value:
            await interaction.followup.send("Upgrade purchase canceled.", ephemeral=True)
            conn.close()
            return
            
        # Process the purchase
        if existing:
            # Update existing upgrade
            cursor.execute("""
                UPDATE faction_purchased_upgrades
                SET level = ?
                WHERE faction_id = ? AND upgrade_id = ?
            """, (next_level, faction_id, upgrade_id))
        else:
            # Insert new upgrade
            cursor.execute("""
                INSERT INTO faction_purchased_upgrades (faction_id, upgrade_id, level)
                VALUES (?, ?, ?)
            """, (faction_id, upgrade_id, 1))
            
        # Deduct tokens from faction
        cursor.execute("""
            UPDATE factions SET tokens = tokens - ?
            WHERE faction_id = ?
        """, (current_cost, faction_id))
        
        conn.commit()
        conn.close()
        
        # Confirmation message
        success_embed = discord.Embed(
            title=f"Upgrade Purchased: {name}",
            description=f"Your faction now has {name} at Level {next_level}/{max_level}\n\nEffect: +{effect_value:.0%}",
            color=discord.Color.green()
        )
        
        success_embed.set_footer(text=f"Faction Treasury: {faction_tokens - current_cost} tokens")
        
        await interaction.followup.send(embed=success_embed)
        
    @app_commands.command(name="faction_upgrades", description="View available faction upgrades")
    @require_permission_level(PermissionLevel.USER)
    async def faction_upgrades(self, interaction: discord.Interaction):
        """View all available faction upgrades and their costs."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check user's faction
        cursor.execute("""
            SELECT f.faction_id, f.name, f.tokens, f.color
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_row = cursor.fetchone()
        if not faction_row:
            await interaction.response.send_message(
                "You are not a member of any faction.",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, faction_tokens, color = faction_row
        
        # Get all available upgrades
        cursor.execute("""
            SELECT upgrade_id, name, description, cost, max_level, upgrade_type, effect_per_level
            FROM faction_upgrades
            ORDER BY cost
        """)
        
        upgrades = cursor.fetchall()
        
        # Get faction's purchased upgrades
        cursor.execute("""
            SELECT upgrade_id, level
            FROM faction_purchased_upgrades
            WHERE faction_id = ?
        """, (faction_id,))
        
        purchased = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        # Create embed
        embed = discord.Embed(
            title=f"{faction_name} - Available Upgrades",
            description=f"Faction Treasury: **{faction_tokens} tokens**\n\nUse `/faction_upgrade <name>` to purchase an upgrade.",
            color=int(color, 16) if color else 0x0099ff
        )
        
        # Group upgrades by category
        categories = {}
        for upgrade in upgrades:
            upgrade_id, name, description, cost, max_level, upgrade_type, effect = upgrade
            
            current_level = purchased.get(upgrade_id, 0)
            next_level = current_level + 1 if current_level < max_level else None
            
            status = f"Level {current_level}/{max_level}"
            if next_level:
                next_cost = cost * next_level
                can_afford = "✅" if faction_tokens >= next_cost else "❌"
                status += f" | Next: {next_cost} tokens {can_afford}"
            else:
                status += " (MAX)"
                
            category = upgrade_type.replace("_", " ").title()
            if category not in categories:
                categories[category] = []
                
            categories[category].append(f"**{name}** - {status}\n{description}")
            
        # Add each category to embed
        for category, items in categories.items():
            embed.add_field(
                name=f"{category} Upgrades",
                value="\n\n".join(items),
                inline=False
            )
            
        embed.set_footer(text="Upgrades provide benefits to all faction members")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="faction_list", description="View all factions on the server")
    @require_permission_level(PermissionLevel.USER)
    async def faction_list(self, interaction: discord.Interaction):
        """List all factions on the server with basic information."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all factions with member counts
        cursor.execute("""
            SELECT f.faction_id, f.name, f.level, f.description, f.motto, 
                   COUNT(fm.user_id) as member_count, f.member_capacity, f.color
            FROM factions f
            LEFT JOIN faction_members fm ON f.faction_id = fm.faction_id
            GROUP BY f.faction_id
            ORDER BY f.level DESC, member_count DESC
        """)
        
        factions = cursor.fetchall()
        conn.close()
        
        if not factions:
            await interaction.response.send_message(
                "There are no factions on this server yet. Administrators can create factions with `/faction_create`.",
                ephemeral=True
            )
            return
            
        embed = discord.Embed(
            title="Veramon Reunited - Factions",
            description=f"There are {len(factions)} factions on this server.\nJoin a faction to access exclusive content and bonuses!",
            color=discord.Color.blue()
        )
        
        for faction in factions:
            faction_id, name, level, description, motto, members, capacity, color = faction
            
            embed.add_field(
                name=f"{name} (Level {level})",
                value=f"{motto}\n👥 {members}/{capacity} members\n\n*{description[:100]}{'...' if len(description) > 100 else ''}*",
                inline=False
            )
            
        embed.set_footer(text="Use /faction_join <name> to join a faction")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="faction_war", description="Declare war on another faction")
    @app_commands.describe(target_faction="Name of the faction to declare war on")
    @require_permission_level(PermissionLevel.USER)
    async def faction_war(self, interaction: discord.Interaction, target_faction: str):
        """Declare war on another faction. Requires officer rank or higher."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check user's faction and permissions
        cursor.execute("""
            SELECT f.faction_id, f.name, fr.permissions
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            JOIN faction_ranks fr ON fm.rank_id = fr.rank_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_row = cursor.fetchone()
        if not faction_row:
            await interaction.response.send_message(
                "You are not a member of any faction.",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, permissions = faction_row
        permissions = json.loads(permissions)
        
        # Check permission to declare war
        if "manage_wars" not in permissions:
            await interaction.response.send_message(
                "You don't have permission to declare faction wars. This requires Officer rank or higher.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Check if the target faction exists
        cursor.execute("""
            SELECT faction_id, name, level FROM factions WHERE name = ?
        """, (target_faction,))
        
        target = cursor.fetchone()
        if not target:
            await interaction.response.send_message(
                f"No faction found with name '{target_faction}'.",
                ephemeral=True
            )
            conn.close()
            return
            
        target_id, target_name, target_level = target
        
        # Can't declare war on your own faction
        if target_id == faction_id:
            await interaction.response.send_message(
                "You can't declare war on your own faction!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Check if already at war
        cursor.execute("""
            SELECT war_id FROM faction_wars 
            WHERE (attacker_id = ? AND defender_id = ?) OR (attacker_id = ? AND defender_id = ?)
            AND status = 'active'
        """, (faction_id, target_id, target_id, faction_id))
        
        existing_war = cursor.fetchone()
        if existing_war:
            await interaction.response.send_message(
                f"Your faction is already at war with {target_name}!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Get faction levels to determine war costs and rewards
        cursor.execute("SELECT level, tokens FROM factions WHERE faction_id = ?", (faction_id,))
        attacker_level, attacker_tokens = cursor.fetchone()
        
        # War declaration costs tokens
        war_cost = 500 * attacker_level
        
        # Check if faction has enough tokens
        if attacker_tokens < war_cost:
            await interaction.response.send_message(
                f"Your faction doesn't have enough tokens to declare war. Required: {war_cost}, Available: {attacker_tokens}",
                ephemeral=True
            )
            conn.close()
            return
            
        # Calculate war duration and rewards based on level difference
        level_diff = abs(attacker_level - target_level)
        duration_days = 3 + level_diff  # wars last longer when level gap is bigger
        end_date = (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
        
        # Rewards scale with defender level
        territory_reward = max(1, target_level // 2)
        token_reward = 1000 * target_level
        
        # Create the war
        cursor.execute("""
            INSERT INTO faction_wars (
                attacker_id, defender_id, start_date, end_date, 
                status, territory_reward, token_reward
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            faction_id, target_id, datetime.utcnow().isoformat(), end_date,
            'active', territory_reward, token_reward
        ))
        
        # Deduct war cost from attacker faction
        cursor.execute("""
            UPDATE factions SET tokens = tokens - ? WHERE faction_id = ?
        """, (war_cost, faction_id))
        
        conn.commit()
        conn.close()
        
        # Prepare war declaration embed
        embed = discord.Embed(
            title="⚔️ Faction War Declared! ⚔️",
            description=f"{faction_name} has declared war on {target_name}!",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
        embed.add_field(name="War Cost", value=f"{war_cost} tokens", inline=True)
        embed.add_field(name="Status", value="Active", inline=True)
        
        embed.add_field(name="Territory Reward", value=f"{territory_reward} territories", inline=True)
        embed.add_field(name="Token Reward", value=f"{token_reward} tokens", inline=True)
        
        embed.set_footer(text="Use /faction_war_status to check ongoing wars")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="faction_buff", description="Activate a temporary faction buff")
    @app_commands.describe(
        buff_type="Type of buff to activate",
        duration="Duration in hours (costs more for longer duration)"
    )
    @app_commands.choices(buff_type=[
        app_commands.Choice(name="XP Boost (25% more XP)", value="xp"),
        app_commands.Choice(name="Catch Rate (15% higher catch rate)", value="catch"),
        app_commands.Choice(name="Token Boost (20% more tokens)", value="token"),
        app_commands.Choice(name="Shiny Boost (2x shiny chance)", value="shiny"),
        app_commands.Choice(name="Evolution Boost (50% less evolution cost)", value="evolution")
    ])
    @require_permission_level(PermissionLevel.USER)
    async def faction_buff(self, interaction: discord.Interaction, buff_type: str, duration: int = 24):
        """Activate a temporary faction-wide buff. Requires faction officer or higher."""
        if duration < 1 or duration > 72:
            await interaction.response.send_message(
                "Duration must be between 1 and 72 hours.",
                ephemeral=True
            )
            return
            
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check user's faction and permissions
        cursor.execute("""
            SELECT f.faction_id, f.name, f.tokens, fr.permissions
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            JOIN faction_ranks fr ON fm.rank_id = fr.rank_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_row = cursor.fetchone()
        if not faction_row:
            await interaction.response.send_message(
                "You are not a member of any faction.",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, faction_tokens, permissions = faction_row
        permissions = json.loads(permissions)
        
        # Check permission to manage buffs
        if "manage_upgrades" not in permissions:
            await interaction.response.send_message(
                "You don't have permission to activate faction buffs. This requires Officer rank or higher.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Buff costs scale with duration
        base_cost = {
            "xp": 200,
            "catch": 300,
            "token": 250,
            "shiny": 500,
            "evolution": 350
        }
        
        buff_name = {
            "xp": "XP Boost",
            "catch": "Catch Rate Boost",
            "token": "Token Boost",
            "shiny": "Shiny Chance Boost",
            "evolution": "Evolution Cost Reduction"
        }
        
        buff_effect = {
            "xp": "25% more XP for all members",
            "catch": "15% higher catch rate",
            "token": "20% more tokens from activities",
            "shiny": "Double chance to find shiny Veramon",
            "evolution": "50% reduced evolution costs"
        }
        
        # Calculate cost based on duration
        cost = base_cost[buff_type] * (duration // 12 + 1)
        
        # Check for active buff of same type
        cursor.execute("""
            SELECT end_time FROM faction_buffs
            WHERE faction_id = ? AND buff_type = ? AND end_time > ?
        """, (faction_id, buff_type, datetime.utcnow().isoformat()))
        
        active_buff = cursor.fetchone()
        if active_buff:
            end_time = datetime.fromisoformat(active_buff[0])
            hours_left = int((end_time - datetime.utcnow()).total_seconds() / 3600)
            
            await interaction.response.send_message(
                f"Your faction already has an active {buff_name[buff_type]} with {hours_left} hours remaining.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Check if faction has enough tokens
        if faction_tokens < cost:
            await interaction.response.send_message(
                f"Your faction doesn't have enough tokens. Required: {cost}, Available: {faction_tokens}",
                ephemeral=True
            )
            conn.close()
            return
            
        # Create confirmation view
        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.value = None
                
            @discord.ui.button(label="Activate Buff", style=discord.ButtonStyle.green)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()
                
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()
                
        # Confirmation message
        embed = discord.Embed(
            title=f"Activate Faction Buff: {buff_name[buff_type]}",
            description=f"This will activate a {duration}-hour buff for all faction members.",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="Effect", value=buff_effect[buff_type], inline=False)
        embed.add_field(name="Cost", value=f"{cost} faction tokens", inline=True)
        embed.add_field(name="Duration", value=f"{duration} hours", inline=True)
        embed.set_footer(text=f"Faction Treasury: {faction_tokens} tokens")
        
        view = ConfirmView()
        await interaction.response.send_message(embed=embed, view=view)
        
        # Wait for confirmation
        await view.wait()
        
        if not view.value:
            await interaction.followup.send("Buff activation cancelled.", ephemeral=True)
            conn.close()
            return
            
        # Calculate end time
        end_time = (datetime.utcnow() + timedelta(hours=duration)).isoformat()
        
        # Add the buff
        cursor.execute("""
            INSERT INTO faction_buffs (faction_id, buff_type, start_time, end_time, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (faction_id, buff_type, datetime.utcnow().isoformat(), end_time, user_id))
        
        # Deduct tokens from faction
        cursor.execute("""
            UPDATE factions SET tokens = tokens - ? WHERE faction_id = ?
        """, (cost, faction_id))
        
        conn.commit()
        conn.close()
        
        # Confirmation message
        success_embed = discord.Embed(
            title=f"Faction Buff Activated: {buff_name[buff_type]}",
            description=f"All members of {faction_name} now have {buff_effect[buff_type]} for {duration} hours!",
            color=discord.Color.green()
        )
        
        success_embed.add_field(name="Expires", value=f"<t:{int(datetime.fromisoformat(end_time).timestamp())}:R>", inline=True)
        success_embed.set_footer(text=f"Faction Treasury: {faction_tokens - cost} tokens")
        
        await interaction.followup.send(embed=success_embed)

    @app_commands.command(name="faction_buffs", description="View active faction buffs")
    @require_permission_level(PermissionLevel.USER)
    async def faction_buffs(self, interaction: discord.Interaction):
        """View all active buffs for your faction."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check user's faction
        cursor.execute("""
            SELECT f.faction_id, f.name, f.color
            FROM faction_members fm
            JOIN factions f ON fm.faction_id = f.faction_id
            WHERE fm.user_id = ?
        """, (user_id,))
        
        faction_row = cursor.fetchone()
        if not faction_row:
            await interaction.response.send_message(
                "You are not a member of any faction.",
                ephemeral=True
            )
            conn.close()
            return
            
        faction_id, faction_name, color = faction_row
        
        # Get active buffs
        cursor.execute("""
            SELECT buff_type, start_time, end_time
            FROM faction_buffs
            WHERE faction_id = ? AND end_time > ?
            ORDER BY end_time
        """, (faction_id, datetime.utcnow().isoformat()))
        
        buffs = cursor.fetchall()
        
        # Get permanent upgrades
        cursor.execute("""
            SELECT fu.name, fu.effect_per_level, fpu.level
            FROM faction_purchased_upgrades fpu
            JOIN faction_upgrades fu ON fpu.upgrade_id = fu.upgrade_id
            WHERE fpu.faction_id = ?
        """, (faction_id,))
        
        upgrades = cursor.fetchall()
        
        conn.close()
        
        # Create embed for buffs
        embed = discord.Embed(
            title=f"{faction_name} - Active Buffs & Upgrades",
            description="Currently active temporary buffs and permanent upgrades for your faction.",
            color=int(color, 16) if color else 0x0099ff
        )
        
        # Add temporary buffs section
        if buffs:
            buffs_text = ""
            
            buff_name = {
                "xp": "XP Boost (+25%)",
                "catch": "Catch Rate Boost (+15%)",
                "token": "Token Boost (+20%)",
                "shiny": "Shiny Chance Boost (2x)",
                "evolution": "Evolution Cost Reduction (-50%)"
            }
            
            for buff_type, start_time, end_time in buffs:
                end_timestamp = int(datetime.fromisoformat(end_time).timestamp())
                buffs_text += f"**{buff_name.get(buff_type, buff_type)}**\n"
                buffs_text += f"• Expires: <t:{end_timestamp}:R>\n\n"
                
            embed.add_field(name="📊 Temporary Buffs", value=buffs_text, inline=False)
        else:
            embed.add_field(
                name="📊 Temporary Buffs", 
                value="No active temporary buffs. Use `/faction_buff` to activate one!", 
                inline=False
            )
            
        # Add permanent upgrades section
        if upgrades:
            upgrades_text = ""
            
            for name, effect_per_level, level in upgrades:
                total_effect = effect_per_level * level
                upgrades_text += f"**{name}** (Level {level})\n"
                upgrades_text += f"• Effect: +{total_effect:.0%}\n\n"
                
            embed.add_field(name="🔧 Permanent Upgrades", value=upgrades_text, inline=False)
        else:
            embed.add_field(
                name="🔧 Permanent Upgrades", 
                value="No upgrades purchased yet. Use `/faction_upgrade` to buy one!", 
                inline=False
            )
            
        embed.set_footer(text="Buffs stack with upgrades for maximum effect!")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(FactionCog(bot))
