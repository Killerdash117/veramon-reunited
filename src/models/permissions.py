from enum import Enum
from functools import wraps
from typing import Callable, List, Union, Optional, Dict, Set
import os
import logging

import discord
from discord import app_commands
from discord.ext import commands


class PermissionLevel(Enum):
    """Permission levels for command access."""
    NONE = -1  # No access
    USER = 0  # Basic gameplay access
    VIP = 1   # Premium features
    MOD = 2   # Moderation tools
    ADMIN = 3 # Administrative control
    DEV = 4   # Full developer access
    OWNER = 5 # Bot owner


# Role name mappings for each permission level
ROLE_MAPPINGS = {
    PermissionLevel.USER: ["User", "Veramon Trainer"],
    PermissionLevel.VIP: ["VIP", "Premium", "Supporter"],
    PermissionLevel.MOD: ["Mod", "Moderator"],
    PermissionLevel.ADMIN: ["Admin", "Administrator"],
    PermissionLevel.DEV: ["Dev", "Developer"]
}

# Detailed permission descriptions for documentation
PERMISSION_DESCRIPTIONS = {
    PermissionLevel.USER: """
        **User**: Basic gameplay access
        - Explore biomes with `/explore`
        - Catch Veramon with `/catch`
        - Battle wild Veramon with `/battle_wild`
        - View profile with `/profile`
        - Check balance with `/balance`
        - View shop with `/shop`
        - Purchase items with `/shop_buy`
        - Transfer tokens with `/transfer`
        - Join guilds with `/guild_join`
        - Standard encounter rate and catch rates
    """,
    PermissionLevel.VIP: """
        **VIP**: Enhanced gameplay experience
        - All USER permissions
        - Reduced spawn cooldowns (15s vs 30s)
        - Increased catch rates (+10% bonus)
        - Enhanced shiny rates (+20% bonus)
        - Increased XP gain (+25% bonus)
        - Daily token bonus with `/daily_bonus`
        - Custom profile themes with `/set_profile_theme`
        - Special titles with `/set_title`
        - Exclusive VIP shop items
        - Additional guild member slots
    """,
    PermissionLevel.MOD: """
        **Mod**: Server moderation capabilities
        - All VIP permissions
        - Access to catch logs with `/view_logs`
        - Cancel other users' trades with `/cancel_trade`
        - Moderate faction/guild chat with `/moderate`
        - Issue temporary bans with `/temp_ban`
        - View user lookup data with `/lookup_user`
        - Reset cooldowns with `/reset_cooldown`
        - Monitor reports with `/view_reports`
    """,
    PermissionLevel.ADMIN: """
        **Admin**: Server management powers
        - All MOD permissions
        - Award tokens to users with `/award`
        - Create and manage events with `/event`
        - Configure spawn rates with `/config_spawns`
        - Override shop prices with `/override_price`
        - Manage user inventories with `/modify_inventory`
        - Delete captures with `/delete_capture`
        - Full access to spawn any Veramon with `/spawn_veramon`
        - Guild management with `/manage_guild`
        - Faction management with `/manage_faction`
    """,
    PermissionLevel.DEV: """
        **Dev**: Complete system control
        - All ADMIN permissions
        - Database management commands
        - Create/modify veramon with `/create_veramon`
        - System diagnostics with `/system_stats`
        - Update bot configuration with `/update_config`
        - Access to debug logs with `/debug_logs`
        - Reload bot modules with `/reload`
        - Execute custom queries with `/query`
        - Full bypass of all restrictions
    """,
    PermissionLevel.OWNER: """
        **Owner**: Bot owner
        - All DEV permissions
        - Bot owner access
    """
}

# Command permissions - Each command mapped to minimum required permission level
COMMAND_PERMISSIONS = {
    # User commands (Level 0)
    "explore": PermissionLevel.USER,
    "catch": PermissionLevel.USER,
    "battle_wild": PermissionLevel.USER,
    "profile": PermissionLevel.USER,
    "balance": PermissionLevel.USER,
    "earn": PermissionLevel.USER,
    "transfer": PermissionLevel.USER,
    "shop": PermissionLevel.USER,
    "shop_buy": PermissionLevel.USER,
    "inventory": PermissionLevel.USER,
    "collection": PermissionLevel.USER,
    "veramon_details": PermissionLevel.USER,
    "nickname": PermissionLevel.USER,
    "evolve": PermissionLevel.USER,
    "guild_join": PermissionLevel.USER,
    "guild_leave": PermissionLevel.USER,
    "guild_info": PermissionLevel.USER,
    "guild_list": PermissionLevel.USER,
    
    # VIP commands (Level 1)
    "daily_bonus": PermissionLevel.VIP,
    "set_profile_theme": PermissionLevel.VIP,
    "set_title": PermissionLevel.VIP,
    "vip_shop": PermissionLevel.VIP,
    "guild_create": PermissionLevel.VIP,  # Creating a guild requires VIP or higher
    
    # Mod commands (Level 2)
    "view_logs": PermissionLevel.MOD,
    "cancel_trade": PermissionLevel.MOD,
    "moderate": PermissionLevel.MOD,
    "temp_ban": PermissionLevel.MOD,
    "lookup_user": PermissionLevel.MOD,
    "reset_cooldown": PermissionLevel.MOD,
    "view_reports": PermissionLevel.MOD,
    
    # Admin commands (Level 3)
    "award": PermissionLevel.ADMIN,
    "event": PermissionLevel.ADMIN,
    "config_spawns": PermissionLevel.ADMIN,
    "override_price": PermissionLevel.ADMIN,
    "modify_inventory": PermissionLevel.ADMIN,
    "delete_capture": PermissionLevel.ADMIN,
    "spawn_veramon": PermissionLevel.ADMIN,
    "manage_guild": PermissionLevel.ADMIN,
    "manage_faction": PermissionLevel.ADMIN,
    "faction_create": PermissionLevel.ADMIN,  # Only admins can create factions (expensive)
    
    # Dev commands (Level 4)
    "create_veramon": PermissionLevel.DEV,
    "system_stats": PermissionLevel.DEV,
    "update_config": PermissionLevel.DEV,
    "debug_logs": PermissionLevel.DEV,
    "reload": PermissionLevel.DEV,
    "query": PermissionLevel.DEV
}

# Special perks by permission level
PERMISSION_PERKS = {
    PermissionLevel.USER: {
        "spawn_cooldown": 30,  # 30 seconds between spawns
        "daily_tokens": 50,    # Daily tokens
        "catch_multiplier": 1.0,  # Standard catch rate
        "shiny_multiplier": 1.0,  # Standard shiny rate
        "xp_multiplier": 1.0,     # Standard XP gain
        "max_guild_members": 0    # Can't create guilds, join only
    },
    PermissionLevel.VIP: {
        "spawn_cooldown": 15,     # 15 seconds between spawns
        "daily_tokens": 150,      # Enhanced daily tokens
        "catch_multiplier": 1.1,  # +10% catch rate
        "shiny_multiplier": 1.2,  # +20% shiny rate
        "xp_multiplier": 1.25,    # +25% XP gain
        "max_guild_members": 5    # Can create guilds with 5 slots
    },
    PermissionLevel.MOD: {
        "spawn_cooldown": 10,     # 10 seconds between spawns
        "daily_tokens": 200,      # Enhanced daily tokens for mods
        "catch_multiplier": 1.15, # +15% catch rate
        "shiny_multiplier": 1.3,  # +30% shiny rate
        "xp_multiplier": 1.5,     # +50% XP gain
        "max_guild_members": 7    # Can create guilds with 7 slots
    },
    PermissionLevel.ADMIN: {
        "spawn_cooldown": 5,      # 5 seconds between spawns
        "daily_tokens": 300,      # Enhanced daily tokens for admins
        "catch_multiplier": 1.2,  # +20% catch rate
        "shiny_multiplier": 1.5,  # +50% shiny rate
        "xp_multiplier": 1.75,    # +75% XP gain
        "max_guild_members": 10   # Can create guilds with 10 slots
    },
    PermissionLevel.DEV: {
        "spawn_cooldown": 0,      # No cooldown between spawns
        "daily_tokens": 500,      # Maximum daily tokens for devs
        "catch_multiplier": 2.0,  # +100% catch rate (guaranteed for common)
        "shiny_multiplier": 2.0,  # +100% shiny rate
        "xp_multiplier": 2.0,     # +100% XP gain
        "max_guild_members": 15   # Can create guilds with 15 slots
    },
    PermissionLevel.OWNER: {
        "spawn_cooldown": 0,      # No cooldown between spawns
        "daily_tokens": 500,      # Maximum daily tokens for owner
        "catch_multiplier": 2.0,  # +100% catch rate (guaranteed for common)
        "shiny_multiplier": 2.0,  # +100% shiny rate
        "xp_multiplier": 2.0,     # +100% XP gain
        "max_guild_members": 20   # Can create guilds with 20 slots
    }
}


async def check_permission_level(interaction: discord.Interaction, level: PermissionLevel) -> bool:
    """Check if user has permission at or above the specified level."""
    if interaction.user.id == interaction.guild.owner_id:
        return True  # Server owner always has all permissions
    
    user_roles = [role.name for role in interaction.user.roles]
    
    # Check if user has any role that grants the required permission level or higher
    for check_level in reversed(list(PermissionLevel)):
        if check_level.value < level.value:
            break
            
        for role_name in ROLE_MAPPINGS[check_level]:
            if role_name in user_roles:
                return True
                
    return False


def require_permission_level(level: PermissionLevel):
    """Decorator for requiring a specific permission level to use a command."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if await check_permission_level(interaction, level):
                return await func(self, interaction, *args, **kwargs)
            else:
                required_roles = ", ".join(f"'{role}'" for role in ROLE_MAPPINGS[level])
                await interaction.response.send_message(
                    f"You don't have permission to use this command. Required roles: {required_roles}",
                    ephemeral=True
                )
        return wrapper
    return decorator


def is_dev():
    """Check if user has developer permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await check_permission_level(interaction, PermissionLevel.DEV)
    return app_commands.check(predicate)


def is_admin():
    """Check if user has admin permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await check_permission_level(interaction, PermissionLevel.ADMIN)
    return app_commands.check(predicate)


def is_mod():
    """Check if user has mod permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await check_permission_level(interaction, PermissionLevel.MOD)
    return app_commands.check(predicate)


def is_vip():
    """Check if user has VIP permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await check_permission_level(interaction, PermissionLevel.VIP)
    return app_commands.check(predicate)


def get_user_perks(interaction: discord.Interaction) -> Dict:
    """Get user's permission perks based on their highest role."""
    # Default to USER level perks
    perks = PERMISSION_PERKS[PermissionLevel.USER].copy()
    
    # Server owner gets DEV perks
    if interaction.user.id == interaction.guild.owner_id:
        return PERMISSION_PERKS[PermissionLevel.DEV].copy()
    
    # Find user's highest permission level
    user_roles = [role.name for role in interaction.user.roles]
    highest_level = PermissionLevel.USER
    
    for level in reversed(list(PermissionLevel)):
        for role_name in ROLE_MAPPINGS[level]:
            if role_name in user_roles:
                highest_level = level
                break
        if highest_level != PermissionLevel.USER:
            break
            
    return PERMISSION_PERKS[highest_level].copy()


def command_requires_permission(command_name: str) -> PermissionLevel:
    """Get the permission level required for a specific command."""
    return COMMAND_PERMISSIONS.get(command_name, PermissionLevel.USER)


def get_permission_description(level: PermissionLevel) -> str:
    """Get detailed description of permissions for a level."""
    return PERMISSION_DESCRIPTIONS.get(level, "No description available.")


def get_available_commands(level: PermissionLevel) -> Set[str]:
    """Get all commands available to a specific permission level."""
    commands = set()
    for cmd, req_level in COMMAND_PERMISSIONS.items():
        if req_level.value <= level.value:
            commands.add(cmd)
    return commands


async def get_permission_level(interaction: discord.Interaction) -> PermissionLevel:
    """Get the permission level for a user.
    
    Args:
        interaction: The Discord interaction
        
    Returns:
        The permission level of the user
    """
    if interaction.guild is None:
        # In DMs, only the bot owner is considered admin
        return PermissionLevel.NONE
        
    user_id = str(interaction.user.id)
    
    # Check if user is the bot owner
    if user_id == os.getenv("BOT_OWNER_ID"):
        return PermissionLevel.OWNER
        
    # Check if user is server owner
    if interaction.guild.owner_id == interaction.user.id:
        return PermissionLevel.ADMIN
        
    # Query database for developer status
    from src.db.db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT permission_level FROM developers WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            try:
                return PermissionLevel(result[0])
            except (ValueError, KeyError):
                return PermissionLevel.NONE
    except Exception as e:
        logging.error(f"Error checking permission level: {e}")
    finally:
        conn.close()
        
    return PermissionLevel.NONE
