import discord
from discord.ext import commands
from typing import Dict, Any, Optional, List, Union
import logging
import asyncio

from src.models.permissions import check_permission_level, PermissionLevel, is_vip, is_admin
from src.utils.user_settings import get_user_settings

logger = logging.getLogger('veramon.dm')

class DMHandler:
    """
    Handles Direct Message interactions for VIP and Admin+ users.
    Provides permission checking and routing for DM commands.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dm_commands = {}  # Maps command names to permission levels
        self.dm_sessions = {}  # Tracks active DM sessions by user ID
        
    def register_dm_command(self, command_name: str, permission_level: PermissionLevel = PermissionLevel.VIP):
        """
        Register a command as being available in DMs for users with the given permission level.
        
        Args:
            command_name: The command name (without slash)
            permission_level: Minimum permission level required to use the command in DMs
        """
        self.dm_commands[command_name] = permission_level
        logger.info(f"Registered DM command: {command_name} (requires {permission_level.name})")
        
    async def is_dm_allowed(self, interaction: discord.Interaction, command_name: str) -> bool:
        """
        Check if a user is allowed to use a command in DMs.
        
        Args:
            interaction: The Discord interaction
            command_name: The command name
            
        Returns:
            True if the user is allowed to use the command in DMs, False otherwise
        """
        # If not in DMs, always allow
        if not isinstance(interaction.channel, discord.DMChannel):
            return True
            
        # If command not registered for DMs, disallow
        if command_name not in self.dm_commands:
            logger.debug(f"Command {command_name} not registered for DMs")
            return False
            
        # Check user permission level
        required_level = self.dm_commands[command_name]
        user_has_permission = await check_permission_level(interaction, required_level)
        
        if not user_has_permission:
            logger.debug(f"User {interaction.user.id} lacks permission ({required_level.name}) for DM command {command_name}")
            return False
            
        return True
        
    async def start_dm_session(self, user_id: str, context_data: Dict[str, Any] = None) -> bool:
        """
        Start a DM session for a user.
        
        Args:
            user_id: The Discord user ID
            context_data: Optional context data for the session
            
        Returns:
            True if the session was started successfully, False otherwise
        """
        # Check if user already has an active session
        if user_id in self.dm_sessions:
            logger.debug(f"User {user_id} already has an active DM session")
            return False
            
        # Create a new session
        self.dm_sessions[user_id] = {
            "started_at": discord.utils.utcnow(),
            "context": context_data or {},
            "active": True
        }
        
        logger.info(f"Started DM session for user {user_id}")
        return True
        
    def end_dm_session(self, user_id: str) -> bool:
        """
        End a DM session for a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            True if the session was ended successfully, False if no session exists
        """
        if user_id not in self.dm_sessions:
            logger.debug(f"No active DM session for user {user_id}")
            return False
            
        # Mark session as inactive but keep it for history
        self.dm_sessions[user_id]["active"] = False
        logger.info(f"Ended DM session for user {user_id}")
        return True
        
    def get_session_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the context data for a user's DM session.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            The session context data, or None if no active session exists
        """
        if user_id not in self.dm_sessions or not self.dm_sessions[user_id]["active"]:
            return None
            
        return self.dm_sessions[user_id]["context"]
        
    def update_session_context(self, user_id: str, context_update: Dict[str, Any]) -> bool:
        """
        Update the context data for a user's DM session.
        
        Args:
            user_id: The Discord user ID
            context_update: The data to update in the context
            
        Returns:
            True if the context was updated successfully, False if no active session exists
        """
        if user_id not in self.dm_sessions or not self.dm_sessions[user_id]["active"]:
            return False
            
        # Update the context
        self.dm_sessions[user_id]["context"].update(context_update)
        return True
        
    async def send_dm(self, user_id: str, content: str = None, embed: discord.Embed = None, view: discord.ui.View = None) -> Optional[discord.Message]:
        """
        Send a DM to a user.
        
        Args:
            user_id: The Discord user ID
            content: Optional text content
            embed: Optional embed
            view: Optional view
            
        Returns:
            The sent message if successful, None otherwise
        """
        try:
            # Get the user
            user = await self.bot.fetch_user(int(user_id))
            if not user:
                logger.error(f"Could not find user with ID {user_id}")
                return None
                
            # Send the DM
            message = await user.send(content=content, embed=embed, view=view)
            return message
        except discord.Forbidden:
            logger.error(f"Cannot send DM to user {user_id} (forbidden)")
            return None
        except Exception as e:
            logger.error(f"Error sending DM to user {user_id}: {e}")
            return None

# Create a global DM handler instance - will be initialized in the bot
dm_handler = None

def setup_dm_handler(bot: commands.Bot):
    """Set up the global DM handler instance."""
    global dm_handler
    dm_handler = DMHandler(bot)
    
    # Register commands that should be available in DMs
    
    # VIP-level commands
    for cmd in [
        "profile", "collection", "settings", "theme", 
        "daily_vip", "vip_shop", "explore", "catch"
    ]:
        dm_handler.register_dm_command(cmd, PermissionLevel.VIP)
        
    # Admin-level commands
    for cmd in [
        "admin_add_veramon", "admin_edit_veramon", "admin_remove_veramon",
        "admin_give_tokens", "admin_broadcast"
    ]:
        dm_handler.register_dm_command(cmd, PermissionLevel.ADMIN)
        
    # Developer-level commands
    for cmd in [
        "dev_test", "dev_log", "dev_debug", "dev_reload"
    ]:
        dm_handler.register_dm_command(cmd, PermissionLevel.DEV)
        
    return dm_handler
