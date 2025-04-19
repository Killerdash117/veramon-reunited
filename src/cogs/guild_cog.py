import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional
import json
import os
import sqlite3
from datetime import datetime

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel, is_mod, is_admin


class GuildCog(commands.Cog):
    """Guild system for creating and managing Veramon trainer guilds."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="guild_create", description="Create a new guild")
    @app_commands.describe(name="The name of your new guild")
    @require_permission_level(PermissionLevel.USER)
    async def guild_create(self, interaction: discord.Interaction, name: str):
        """Create a new guild with the current user as leader."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is already in a guild
        cursor.execute("SELECT g.name FROM guilds g JOIN guild_members gm ON g.guild_id = gm.guild_id WHERE gm.user_id = ?", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            await interaction.response.send_message(f"You are already a member of the guild '{existing[0]}'. Leave that guild first.", ephemeral=True)
            conn.close()
            return
            
        # Check if guild name already exists
        cursor.execute("SELECT name FROM guilds WHERE name = ?", (name,))
        if cursor.fetchone():
            await interaction.response.send_message(f"A guild named '{name}' already exists. Please choose a different name.", ephemeral=True)
            conn.close()
            return
            
        # Create the guild
        cursor.execute(
            "INSERT INTO guilds (name, leader_id, created_at) VALUES (?, ?, ?)",
            (name, user_id, datetime.utcnow().isoformat())
        )
        guild_id = cursor.lastrowid
        
        # Add the creator as leader
        cursor.execute(
            "INSERT INTO guild_members (guild_id, user_id, joined_at, role) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, datetime.utcnow().isoformat(), 'leader')
        )
        
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="Guild Created!",
            description=f"Congratulations! You've created the guild '{name}'.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Leader", value=interaction.user.display_name, inline=True)
        embed.add_field(name="Members", value="1/5", inline=True)
        embed.add_field(name="Created", value=datetime.utcnow().strftime("%Y-%m-%d"), inline=True)
        embed.set_footer(text="Invite others with /guild_invite")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="guild_join", description="Join a guild by invitation code")
    @app_commands.describe(code="The invitation code for the guild")
    @require_permission_level(PermissionLevel.USER)
    async def guild_join(self, interaction: discord.Interaction, code: str):
        """Join a guild using an invitation code."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is already in a guild
        cursor.execute("SELECT g.name FROM guilds g JOIN guild_members gm ON g.guild_id = gm.guild_id WHERE gm.user_id = ?", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            await interaction.response.send_message(f"You are already a member of the guild '{existing[0]}'. Leave that guild first.", ephemeral=True)
            conn.close()
            return
            
        # Placeholder for invitation code system
        # In a real implementation, you'd have a table tracking invitation codes
        # For now, we'll assume the code is the guild_id for simplicity
        try:
            guild_id = int(code)
            cursor.execute("SELECT name, max_members FROM guilds WHERE guild_id = ?", (guild_id,))
            guild = cursor.fetchone()
            
            if not guild:
                await interaction.response.send_message("Invalid invitation code.", ephemeral=True)
                conn.close()
                return
                
            # Check if guild is full
            cursor.execute("SELECT COUNT(*) FROM guild_members WHERE guild_id = ?", (guild_id,))
            current_members = cursor.fetchone()[0]
            
            if current_members >= guild[1]:  # guild[1] is max_members
                await interaction.response.send_message(f"The guild '{guild[0]}' is full.", ephemeral=True)
                conn.close()
                return
                
            # Add user to guild
            cursor.execute(
                "INSERT INTO guild_members (guild_id, user_id, joined_at, role) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, datetime.utcnow().isoformat(), 'member')
            )
            
            conn.commit()
            
            embed = discord.Embed(
                title="Guild Joined!",
                description=f"You have joined the guild '{guild[0]}'!",
                color=discord.Color.green()
            )
            embed.set_footer(text="Use /guild_info to see details about your guild")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("Invalid invitation code format.", ephemeral=True)
        finally:
            conn.close()
            
    @app_commands.command(name="guild_info", description="View information about your guild")
    @require_permission_level(PermissionLevel.USER)
    async def guild_info(self, interaction: discord.Interaction):
        """View information about your current guild."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user's guild
        cursor.execute("""
            SELECT g.guild_id, g.name, g.leader_id, g.level, g.experience, g.max_members, g.created_at 
            FROM guilds g 
            JOIN guild_members gm ON g.guild_id = gm.guild_id 
            WHERE gm.user_id = ?
        """, (user_id,))
        
        guild = cursor.fetchone()
        
        if not guild:
            await interaction.response.send_message("You are not a member of any guild.", ephemeral=True)
            conn.close()
            return
            
        guild_id, name, leader_id, level, exp, max_members, created_at = guild
        
        # Get guild members
        cursor.execute("""
            SELECT user_id, role FROM guild_members WHERE guild_id = ? ORDER BY role DESC
        """, (guild_id,))
        
        members = cursor.fetchall()
        conn.close()
        
        # Format member list
        member_list = []
        for member_id, role in members:
            user = interaction.guild.get_member(int(member_id))
            display_name = user.display_name if user else f"Unknown User ({member_id})"
            role_icon = "👑" if role == "leader" else "🛡️" if role == "officer" else "👤"
            member_list.append(f"{role_icon} {display_name}")
            
        embed = discord.Embed(
            title=f"Guild: {name}",
            description=f"Level {level} Guild • {len(members)}/{max_members} Members",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Experience", value=f"{exp} XP", inline=True)
        embed.add_field(name="Created", value=datetime.fromisoformat(created_at).strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Invitation Code", value=str(guild_id), inline=True)
        embed.add_field(name="Members", value="\n".join(member_list) or "No members", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="guild_leave", description="Leave your current guild")
    @require_permission_level(PermissionLevel.USER)
    async def guild_leave(self, interaction: discord.Interaction):
        """Leave your current guild."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user's guild and role
        cursor.execute("""
            SELECT g.guild_id, g.name, gm.role 
            FROM guilds g 
            JOIN guild_members gm ON g.guild_id = gm.guild_id 
            WHERE gm.user_id = ?
        """, (user_id,))
        
        guild = cursor.fetchone()
        
        if not guild:
            await interaction.response.send_message("You are not a member of any guild.", ephemeral=True)
            conn.close()
            return
            
        guild_id, guild_name, role = guild
        
        if role == 'leader':
            # Check if there are other members
            cursor.execute("SELECT COUNT(*) FROM guild_members WHERE guild_id = ?", (guild_id,))
            member_count = cursor.fetchone()[0]
            
            if member_count > 1:
                await interaction.response.send_message(
                    "You are the leader of this guild. Transfer leadership to another member with `/guild_promote` before leaving.",
                    ephemeral=True
                )
                conn.close()
                return
        
        # Remove user from guild
        cursor.execute("DELETE FROM guild_members WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        
        # If leader and sole member, delete the guild
        if role == 'leader':
            cursor.execute("DELETE FROM guilds WHERE guild_id = ?", (guild_id,))
            await interaction.response.send_message(f"As the last member, you have disbanded the guild '{guild_name}'.")
        else:
            await interaction.response.send_message(f"You have left the guild '{guild_name}'.")
            
        conn.commit()
        conn.close()
        
    @app_commands.command(name="guild_list", description="List all guilds on the server")
    @require_permission_level(PermissionLevel.USER)
    async def guild_list(self, interaction: discord.Interaction):
        """List all guilds on the server."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT g.guild_id, g.name, g.level, COUNT(gm.user_id) as member_count, g.max_members
            FROM guilds g
            JOIN guild_members gm ON g.guild_id = gm.guild_id
            GROUP BY g.guild_id
            ORDER BY g.level DESC, member_count DESC
        """)
        
        guilds = cursor.fetchall()
        conn.close()
        
        if not guilds:
            await interaction.response.send_message("There are no guilds on this server yet. Create one with `/guild_create`!")
            return
            
        embed = discord.Embed(
            title="Server Guilds",
            description=f"{len(guilds)} guilds found",
            color=discord.Color.blue()
        )
        
        for guild_id, name, level, member_count, max_members in guilds:
            embed.add_field(
                name=f"{name} (Level {level})",
                value=f"Members: {member_count}/{max_members}\nJoin Code: {guild_id}",
                inline=True
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guild_invite", description="Invite a player to your guild")
    @app_commands.describe(user="The user to invite to your guild")
    @require_permission_level(PermissionLevel.USER)
    async def guild_invite(self, interaction: discord.Interaction, user: discord.Member):
        """Invite a player to join your guild."""
        leader_id = str(interaction.user.id)
        invited_id = str(user.id)
        
        # Don't invite yourself
        if leader_id == invited_id:
            await interaction.response.send_message("You can't invite yourself to a guild you're already in!", ephemeral=True)
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if inviter is in a guild and is leader or officer
        cursor.execute("""
            SELECT g.guild_id, g.name, gm.role 
            FROM guilds g 
            JOIN guild_members gm ON g.guild_id = gm.guild_id 
            WHERE gm.user_id = ?
        """, (leader_id,))
        
        inviter_guild = cursor.fetchone()
        if not inviter_guild:
            await interaction.response.send_message("You need to be in a guild to invite others.", ephemeral=True)
            conn.close()
            return
            
        guild_id, guild_name, role = inviter_guild
        if role not in ['leader', 'officer']:
            await interaction.response.send_message("Only guild leaders and officers can invite new members.", ephemeral=True)
            conn.close()
            return
            
        # Check if guild is full
        cursor.execute("SELECT COUNT(*), g.max_members FROM guild_members gm JOIN guilds g ON gm.guild_id = g.guild_id WHERE gm.guild_id = ?", (guild_id,))
        member_count, max_members = cursor.fetchone()
        if member_count >= max_members:
            await interaction.response.send_message(f"Your guild is full! ({member_count}/{max_members} members)", ephemeral=True)
            conn.close()
            return
            
        # Check if invited user is already in a guild
        cursor.execute("SELECT g.name FROM guilds g JOIN guild_members gm ON g.guild_id = gm.guild_id WHERE gm.user_id = ?", (invited_id,))
        existing = cursor.fetchone()
        if existing:
            await interaction.response.send_message(f"{user.display_name} is already in the guild '{existing[0]}'.", ephemeral=True)
            conn.close()
            return
            
        # Create invitation with a unique code in the invitations table
        import uuid
        invite_code = str(uuid.uuid4())[:8]  # Generate a short unique code
        
        cursor.execute("""
            INSERT INTO guild_invitations (guild_id, invited_user_id, inviter_id, code, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (guild_id, invited_id, leader_id, invite_code, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Create an embed with the invitation
        embed = discord.Embed(
            title=f"Guild Invitation: {guild_name}",
            description=f"{interaction.user.display_name} has invited you to join their guild!",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Guild", value=guild_name, inline=True)
        embed.add_field(name="Members", value=f"{member_count}/{max_members}", inline=True)
        embed.add_field(name="Invitation Code", value=invite_code, inline=False)
        embed.set_footer(text=f"Use /guild_join {invite_code} to accept this invitation")
        
        # Send to the invited user
        try:
            await user.send(embed=embed)
            await interaction.response.send_message(f"Invitation sent to {user.display_name}!", ephemeral=True)
        except discord.Forbidden:
            # User has DMs disabled
            await interaction.response.send_message(
                f"I couldn't send a DM to {user.display_name}. Please ask them to enable DMs or give them this invitation code: `{invite_code}`",
                ephemeral=True
            )
    
    @app_commands.command(name="guild_promote", description="Promote a guild member to officer or transfer leadership")
    @app_commands.describe(
        member="The member to promote",
        role="The new role to assign to the member"
    )
    @app_commands.choices(role=[
        app_commands.Choice(name="Officer", value="officer"),
        app_commands.Choice(name="Leader (transfers leadership)", value="leader")
    ])
    @require_permission_level(PermissionLevel.USER)
    async def guild_promote(self, interaction: discord.Interaction, member: discord.Member, role: str):
        """Promote a guild member or transfer leadership."""
        leader_id = str(interaction.user.id)
        target_id = str(member.id)
        
        # Don't promote yourself
        if leader_id == target_id:
            await interaction.response.send_message("You can't promote yourself!", ephemeral=True)
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if promoter is in a guild and is leader
        cursor.execute("""
            SELECT g.guild_id, g.name, gm.role 
            FROM guilds g 
            JOIN guild_members gm ON g.guild_id = gm.guild_id 
            WHERE gm.user_id = ?
        """, (leader_id,))
        
        promoter_guild = cursor.fetchone()
        if not promoter_guild:
            await interaction.response.send_message("You need to be in a guild to promote members.", ephemeral=True)
            conn.close()
            return
            
        guild_id, guild_name, promoter_role = promoter_guild
        
        # Only leaders can promote to officer, and only leaders can transfer leadership
        if promoter_role != 'leader':
            await interaction.response.send_message("Only guild leaders can promote members.", ephemeral=True)
            conn.close()
            return
            
        # Check if target is in the same guild
        cursor.execute("""
            SELECT role FROM guild_members WHERE guild_id = ? AND user_id = ?
        """, (guild_id, target_id))
        
        target_data = cursor.fetchone()
        if not target_data:
            await interaction.response.send_message(f"{member.display_name} is not a member of your guild.", ephemeral=True)
            conn.close()
            return
            
        target_role = target_data[0]
        
        # Can't promote leaders
        if target_role == 'leader':
            await interaction.response.send_message(f"{member.display_name} is already the leader of this guild.", ephemeral=True)
            conn.close()
            return
            
        # Can't promote officers to officer
        if role == 'officer' and target_role == 'officer':
            await interaction.response.send_message(f"{member.display_name} is already an officer in this guild.", ephemeral=True)
            conn.close()
            return
            
        # Process the promotion
        if role == 'leader':
            # Transfer leadership - update both users
            cursor.execute("UPDATE guild_members SET role = 'member' WHERE guild_id = ? AND user_id = ?", (guild_id, leader_id))
            cursor.execute("UPDATE guild_members SET role = 'leader' WHERE guild_id = ? AND user_id = ?", (guild_id, target_id))
            cursor.execute("UPDATE guilds SET leader_id = ? WHERE guild_id = ?", (target_id, guild_id))
            
            await interaction.response.send_message(f"Leadership transferred to {member.display_name}!")
        else:
            # Promote to officer
            cursor.execute("UPDATE guild_members SET role = 'officer' WHERE guild_id = ? AND user_id = ?", (guild_id, target_id))
            await interaction.response.send_message(f"{member.display_name} has been promoted to Officer!")
            
        conn.commit()
        conn.close()

    @app_commands.command(name="guild_kick", description="Remove a member from your guild")
    @app_commands.describe(member="The member to remove from the guild")
    @require_permission_level(PermissionLevel.USER)
    async def guild_kick(self, interaction: discord.Interaction, member: discord.Member):
        """Remove a member from your guild."""
        leader_id = str(interaction.user.id)
        target_id = str(member.id)
        
        # Can't kick yourself
        if leader_id == target_id:
            await interaction.response.send_message("Use `/guild_leave` to leave your guild.", ephemeral=True)
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if kicker is in a guild and is leader or officer
        cursor.execute("""
            SELECT g.guild_id, g.name, gm.role 
            FROM guilds g 
            JOIN guild_members gm ON g.guild_id = gm.guild_id 
            WHERE gm.user_id = ?
        """, (leader_id,))
        
        kicker_guild = cursor.fetchone()
        if not kicker_guild:
            await interaction.response.send_message("You need to be in a guild to kick members.", ephemeral=True)
            conn.close()
            return
            
        guild_id, guild_name, kicker_role = kicker_guild
        
        # Only leaders and officers can kick
        if kicker_role not in ['leader', 'officer']:
            await interaction.response.send_message("Only guild leaders and officers can remove members.", ephemeral=True)
            conn.close()
            return
            
        # Check if target is in the same guild
        cursor.execute("""
            SELECT role FROM guild_members WHERE guild_id = ? AND user_id = ?
        """, (guild_id, target_id))
        
        target_data = cursor.fetchone()
        if not target_data:
            await interaction.response.send_message(f"{member.display_name} is not a member of your guild.", ephemeral=True)
            conn.close()
            return
            
        target_role = target_data[0]
        
        # Can't kick leaders
        if target_role == 'leader':
            await interaction.response.send_message(f"You cannot remove the guild leader.", ephemeral=True)
            conn.close()
            return
            
        # Officers can't kick other officers
        if kicker_role == 'officer' and target_role == 'officer':
            await interaction.response.send_message(f"As an officer, you cannot remove other officers. Ask the guild leader.", ephemeral=True)
            conn.close()
            return
            
        # Process the kick
        cursor.execute("DELETE FROM guild_members WHERE guild_id = ? AND user_id = ?", (guild_id, target_id))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"{member.display_name} has been removed from the guild.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GuildCog(bot))
