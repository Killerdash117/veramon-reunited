import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
import json
from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel
from src.core.security_integration import get_security_integration

def log(message: str) -> None:
    """Simple logging function."""
    print(f"[TeamCog] {message}")

def initialize_team_db():
    """Initialize database tables needed for team management."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Teams table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        team_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_modified TEXT NOT NULL,
        UNIQUE(user_id, team_name)
    )
    """)
    
    # Team members table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER NOT NULL,
        capture_id INTEGER NOT NULL,
        position INTEGER NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
        UNIQUE(team_id, position)
    )
    """)
    
    conn.commit()
    conn.close()

def get_user_teams(user_id: str) -> List[Dict[str, Any]]:
    """Get all teams for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    teams = []
    try:
        # Get all teams for this user
        cursor.execute("""
            SELECT id, team_name, created_at, last_modified 
            FROM teams 
            WHERE user_id = ?
            ORDER BY last_modified DESC
        """, (user_id,))
        
        team_rows = cursor.fetchall()
        
        for team_id, team_name, created_at, last_modified in team_rows:
            # Get team members for this team
            cursor.execute("""
                SELECT tm.capture_id, tm.position, c.veramon_name, c.level, c.shiny
                FROM team_members tm
                JOIN captures c ON tm.capture_id = c.id
                WHERE tm.team_id = ?
                ORDER BY tm.position
            """, (team_id,))
            
            members = []
            for capture_id, position, veramon_name, level, shiny in cursor.fetchall():
                members.append({
                    "capture_id": capture_id,
                    "position": position,
                    "veramon_name": veramon_name,
                    "level": level,
                    "shiny": bool(shiny)
                })
            
            teams.append({
                "id": team_id,
                "name": team_name,
                "created_at": created_at,
                "last_modified": last_modified,
                "members": members
            })
    except Exception as e:
        log(f"Error fetching user teams: {e}")
    finally:
        conn.close()
        
    return teams

def get_team_by_name(user_id: str, team_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific team by name."""
    conn = get_connection()
    cursor = conn.cursor()
    
    team = None
    try:
        # Get the team
        cursor.execute("""
            SELECT id, created_at, last_modified 
            FROM teams 
            WHERE user_id = ? AND team_name = ?
        """, (user_id, team_name))
        
        team_row = cursor.fetchone()
        if not team_row:
            return None
            
        team_id, created_at, last_modified = team_row
        
        # Get team members
        cursor.execute("""
            SELECT tm.capture_id, tm.position, c.veramon_name, c.level, c.shiny
            FROM team_members tm
            JOIN captures c ON tm.capture_id = c.id
            WHERE tm.team_id = ?
            ORDER BY tm.position
        """, (team_id,))
        
        members = []
        for capture_id, position, veramon_name, level, shiny in cursor.fetchall():
            members.append({
                "capture_id": capture_id,
                "position": position,
                "veramon_name": veramon_name,
                "level": level,
                "shiny": bool(shiny)
            })
        
        team = {
            "id": team_id,
            "name": team_name,
            "created_at": created_at,
            "last_modified": last_modified,
            "members": members
        }
    except Exception as e:
        log(f"Error fetching team by name: {e}")
    finally:
        conn.close()
        
    return team

def create_team_embed(team: Dict[str, Any], user: discord.Member = None) -> discord.Embed:
    """Create an embed to display team information."""
    embed = discord.Embed(
        title=f"Team: {team['name']}",
        color=discord.Color.blue()
    )
    
    if user and user.avatar:
        embed.set_author(name=user.display_name, icon_url=user.avatar.url)
    
    # Add team members
    if team["members"]:
        team_text = ""
        for member in team["members"]:
            shiny_star = "✨ " if member["shiny"] else ""
            team_text += f"{member['position']}. {shiny_star}{member['veramon_name']} (Lvl {member['level']})\n"
        embed.add_field(name="Team Members", value=team_text, inline=False)
    else:
        embed.add_field(name="Team Members", value="No Veramon added to this team yet.", inline=False)
    
    # Add creation date
    try:
        created_date = team["created_at"].split("T")[0]  # Format as YYYY-MM-DD
        embed.set_footer(text=f"Created: {created_date}")
    except:
        pass
        
    return embed

class TeamCog(commands.Cog):
    """
    TeamCog allows players to create and manage teams of Veramon for battles.
    Features:
    - Create teams with custom names
    - Add/remove Veramon from teams
    - View all teams
    - Edit existing teams
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_team_db()
        log("TeamCog initialized.")
    
    @app_commands.command(name="team", description="Manage your battle teams")
    @app_commands.describe(
        action="The team action to perform",
        team_name="Name of the team to create, edit, view, or delete"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Create", value="create"),
            app_commands.Choice(name="Edit", value="edit"),
            app_commands.Choice(name="View", value="view"),
            app_commands.Choice(name="List", value="list"),
            app_commands.Choice(name="Delete", value="delete")
        ]
    )
    @require_permission_level(PermissionLevel.USER)
    async def team(self, interaction: discord.Interaction, action: str, team_name: Optional[str] = None):
        """Create and manage preset battle teams."""
        user_id = str(interaction.user.id)
        
        # Security validation
        security = get_security_integration()
        validation_result = await security.validate_team_action(user_id, action, team_name)
        if not validation_result["valid"]:
            await interaction.response.send_message(validation_result["error"], ephemeral=True)
            return
            
        if action == "list":
            # List all teams
            teams = get_user_teams(user_id)
            
            if not teams:
                await interaction.response.send_message(
                    "You don't have any teams yet. Create one with `/team create <team_name>`.", 
                    ephemeral=True
                )
                return
                
            embed = discord.Embed(
                title="Your Veramon Teams",
                description=f"You have {len(teams)} team(s)",
                color=discord.Color.blue()
            )
            
            for team in teams:
                # Count team members
                member_count = len(team["members"])
                
                # Format team members summary
                if member_count > 0:
                    member_text = ", ".join([m["veramon_name"] for m in team["members"]])
                    if len(member_text) > 50:
                        member_text = member_text[:47] + "..."
                else:
                    member_text = "No members"
                    
                embed.add_field(
                    name=team["name"],
                    value=f"Members: {member_count}\n{member_text}",
                    inline=False
                )
                
            embed.set_footer(text="Use /team view <team_name> to see details for a specific team")
            await interaction.response.send_message(embed=embed)
            
        elif action == "view":
            # View a specific team
            if not team_name:
                await interaction.response.send_message(
                    "Please specify a team name to view.", 
                    ephemeral=True
                )
                return
                
            team = get_team_by_name(user_id, team_name)
            
            if not team:
                await interaction.response.send_message(
                    f"Team '{team_name}' not found. Use `/team list` to see your teams.", 
                    ephemeral=True
                )
                return
                
            embed = create_team_embed(team, interaction.user)
            await interaction.response.send_message(embed=embed)
            
        elif action == "create":
            if not team_name:
                await interaction.response.send_message(
                    "Please specify a name for your new team.", 
                    ephemeral=True
                )
                return
                
            # Check team name length
            if len(team_name) > 32:
                await interaction.response.send_message(
                    "Team name cannot exceed 32 characters.", 
                    ephemeral=True
                )
                return
                
            # Check if team already exists
            existing_team = get_team_by_name(user_id, team_name)
            if existing_team:
                await interaction.response.send_message(
                    f"You already have a team named '{team_name}'. Choose a different name.", 
                    ephemeral=True
                )
                return
                
            # Create the team
            from datetime import datetime
            now = datetime.utcnow().isoformat()
            
            conn = get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO teams (user_id, team_name, created_at, last_modified)
                    VALUES (?, ?, ?, ?)
                """, (user_id, team_name, now, now))
                
                conn.commit()
                
                # Get the created team
                team = get_team_by_name(user_id, team_name)
                
                await interaction.response.send_message(
                    content="Team created successfully! Now add Veramon to your team with `/team_add`.",
                    embed=create_team_embed(team, interaction.user)
                )
                
            except Exception as e:
                log(f"Error creating team: {e}")
                await interaction.response.send_message(
                    "An error occurred while creating your team. Please try again.",
                    ephemeral=True
                )
            finally:
                conn.close()
                
        elif action == "delete":
            if not team_name:
                await interaction.response.send_message(
                    "Please specify which team to delete.", 
                    ephemeral=True
                )
                return
                
            # Check if team exists
            team = get_team_by_name(user_id, team_name)
            if not team:
                await interaction.response.send_message(
                    f"Team '{team_name}' not found. Use `/team list` to see your teams.", 
                    ephemeral=True
                )
                return
                
            # Delete the team
            conn = get_connection()
            cursor = conn.cursor()
            
            try:
                # Begin transaction
                conn.execute("BEGIN TRANSACTION")
                
                # Delete team members first (should cascade, but being explicit)
                cursor.execute("DELETE FROM team_members WHERE team_id = ?", (team["id"],))
                
                # Delete the team
                cursor.execute("DELETE FROM teams WHERE id = ?", (team["id"],))
                
                conn.commit()
                
                await interaction.response.send_message(
                    f"Team '{team_name}' has been deleted.",
                    ephemeral=True
                )
                
            except Exception as e:
                conn.rollback()
                log(f"Error deleting team: {e}")
                await interaction.response.send_message(
                    "An error occurred while deleting your team. Please try again.",
                    ephemeral=True
                )
            finally:
                conn.close()
                
        elif action == "edit":
            # This just initiates team editing UI
            if not team_name:
                await interaction.response.send_message(
                    "Please specify which team to edit.", 
                    ephemeral=True
                )
                return
                
            # Check if team exists
            team = get_team_by_name(user_id, team_name)
            if not team:
                await interaction.response.send_message(
                    f"Team '{team_name}' not found. Use `/team list` to see your teams.", 
                    ephemeral=True
                )
                return
                
            await interaction.response.send_message(
                f"To modify team '{team_name}', use:\n" +
                f"- `/team_add {team_name} <capture_id> <position>` to add Veramon\n" +
                f"- `/team_remove {team_name} <position>` to remove Veramon\n" +
                f"- `/team_rename {team_name} <new_name>` to rename the team",
                ephemeral=True
            )

    @app_commands.command(name="team_add", description="Add a Veramon to a team")
    @app_commands.describe(
        team_name="Name of the team to add Veramon to",
        capture_id="ID of the Veramon to add (from /collection)",
        position="Position in team (1-6)"
    )
    @require_permission_level(PermissionLevel.USER)
    async def team_add(
        self, 
        interaction: discord.Interaction, 
        team_name: str, 
        capture_id: int, 
        position: app_commands.Range[int, 1, 6]
    ):
        """Add a Veramon to a team."""
        user_id = str(interaction.user.id)
        
        # Security validation
        security = get_security_integration()
        validation_result = await security.validate_team_member_action(
            user_id, team_name, "add", capture_id, position
        )
        if not validation_result["valid"]:
            await interaction.response.send_message(validation_result["error"], ephemeral=True)
            return
            
        # Get the team
        team = get_team_by_name(user_id, team_name)
        if not team:
            await interaction.response.send_message(
                f"Team '{team_name}' not found. Use `/team list` to see your teams.", 
                ephemeral=True
            )
            return
            
        # Verify the capture exists and belongs to the user
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, veramon_name, level, shiny 
                FROM captures 
                WHERE id = ? AND user_id = ?
            """, (capture_id, user_id))
            
            capture_row = cursor.fetchone()
            if not capture_row:
                await interaction.response.send_message(
                    f"Veramon with capture ID {capture_id} not found in your collection. " +
                    "Use `/collection` to see your Veramon.",
                    ephemeral=True
                )
                conn.close()
                return
                
            capture_id, veramon_name, level, shiny = capture_row
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Check if position is already taken
            cursor.execute("""
                SELECT capture_id FROM team_members
                WHERE team_id = ? AND position = ?
            """, (team["id"], position))
            
            existing = cursor.fetchone()
            if existing:
                # Update existing position
                cursor.execute("""
                    UPDATE team_members
                    SET capture_id = ?
                    WHERE team_id = ? AND position = ?
                """, (capture_id, team["id"], position))
            else:
                # Add new team member
                cursor.execute("""
                    INSERT INTO team_members (team_id, capture_id, position)
                    VALUES (?, ?, ?)
                """, (team["id"], capture_id, position))
            
            # Update last_modified
            from datetime import datetime
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                UPDATE teams
                SET last_modified = ?
                WHERE id = ?
            """, (now, team["id"]))
            
            conn.commit()
            
            # Get updated team
            updated_team = get_team_by_name(user_id, team_name)
            
            shiny_text = "✨ " if shiny else ""
            await interaction.response.send_message(
                content=f"Added {shiny_text}{veramon_name} (Lvl {level}) to position {position} in team '{team_name}'.",
                embed=create_team_embed(updated_team, interaction.user)
            )
            
        except Exception as e:
            conn.rollback()
            log(f"Error adding to team: {e}")
            await interaction.response.send_message(
                "An error occurred while updating your team. Please try again.",
                ephemeral=True
            )
        finally:
            conn.close()
    
    @app_commands.command(name="team_remove", description="Remove a Veramon from a team")
    @app_commands.describe(
        team_name="Name of the team to remove Veramon from",
        position="Position in team to remove (1-6)"
    )
    @require_permission_level(PermissionLevel.USER)
    async def team_remove(
        self, 
        interaction: discord.Interaction, 
        team_name: str, 
        position: app_commands.Range[int, 1, 6]
    ):
        """Remove a Veramon from a team."""
        user_id = str(interaction.user.id)
        
        # Security validation
        security = get_security_integration()
        validation_result = await security.validate_team_member_action(
            user_id, team_name, "remove", None, position
        )
        if not validation_result["valid"]:
            await interaction.response.send_message(validation_result["error"], ephemeral=True)
            return
            
        # Get the team
        team = get_team_by_name(user_id, team_name)
        if not team:
            await interaction.response.send_message(
                f"Team '{team_name}' not found. Use `/team list` to see your teams.", 
                ephemeral=True
            )
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if position exists
            cursor.execute("""
                SELECT tm.capture_id, c.veramon_name 
                FROM team_members tm
                JOIN captures c ON tm.capture_id = c.id
                WHERE tm.team_id = ? AND tm.position = ?
            """, (team["id"], position))
            
            member_row = cursor.fetchone()
            if not member_row:
                await interaction.response.send_message(
                    f"No Veramon found at position {position} in team '{team_name}'.",
                    ephemeral=True
                )
                conn.close()
                return
                
            _, veramon_name = member_row
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Remove the team member
            cursor.execute("""
                DELETE FROM team_members
                WHERE team_id = ? AND position = ?
            """, (team["id"], position))
            
            # Update last_modified
            from datetime import datetime
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                UPDATE teams
                SET last_modified = ?
                WHERE id = ?
            """, (now, team["id"]))
            
            conn.commit()
            
            # Get updated team
            updated_team = get_team_by_name(user_id, team_name)
            
            await interaction.response.send_message(
                content=f"Removed {veramon_name} from position {position} in team '{team_name}'.",
                embed=create_team_embed(updated_team, interaction.user)
            )
            
        except Exception as e:
            conn.rollback()
            log(f"Error removing from team: {e}")
            await interaction.response.send_message(
                "An error occurred while updating your team. Please try again.",
                ephemeral=True
            )
        finally:
            conn.close()
            
    @app_commands.command(name="team_rename", description="Rename an existing team")
    @app_commands.describe(
        team_name="Current name of the team",
        new_name="New name for the team"
    )
    @require_permission_level(PermissionLevel.USER)
    async def team_rename(
        self, 
        interaction: discord.Interaction, 
        team_name: str, 
        new_name: str
    ):
        """Rename a team."""
        user_id = str(interaction.user.id)
        
        # Security validation
        security = get_security_integration()
        validation_result = await security.validate_team_action(user_id, "rename", team_name)
        if not validation_result["valid"]:
            await interaction.response.send_message(validation_result["error"], ephemeral=True)
            return
            
        # Check team name length
        if len(new_name) > 32:
            await interaction.response.send_message(
                "Team name cannot exceed 32 characters.", 
                ephemeral=True
            )
            return
            
        # Get the team
        team = get_team_by_name(user_id, team_name)
        if not team:
            await interaction.response.send_message(
                f"Team '{team_name}' not found. Use `/team list` to see your teams.", 
                ephemeral=True
            )
            return
            
        # Check if new name already exists
        if team_name != new_name:
            existing_team = get_team_by_name(user_id, new_name)
            if existing_team:
                await interaction.response.send_message(
                    f"You already have a team named '{new_name}'. Choose a different name.", 
                    ephemeral=True
                )
                return
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Update team name
            from datetime import datetime
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                UPDATE teams
                SET team_name = ?, last_modified = ?
                WHERE id = ?
            """, (new_name, now, team["id"]))
            
            conn.commit()
            
            # Get updated team
            updated_team = get_team_by_name(user_id, new_name)
            
            await interaction.response.send_message(
                content=f"Team renamed from '{team_name}' to '{new_name}'.",
                embed=create_team_embed(updated_team, interaction.user)
            )
            
        except Exception as e:
            log(f"Error renaming team: {e}")
            await interaction.response.send_message(
                "An error occurred while renaming your team. Please try again.",
                ephemeral=True
            )
        finally:
            conn.close()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))
