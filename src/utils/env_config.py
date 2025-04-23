"""
Environment Configuration Manager for Veramon Reunited

This module handles loading and accessing environment variables and sensitive
configuration that shouldn't be stored in the game configuration files.
"""

import os
import sys
import logging
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Global environment config cache
_env_config = None

def load_env_config() -> Dict[str, Any]:
    """
    Load environment configuration from .env file.
    
    Returns:
        Dict[str, Any]: Environment configuration dictionary
    """
    global _env_config
    
    # Load .env file if it exists
    load_dotenv()
    
    # Create a new config dictionary
    _env_config = {}
    
    # Discord Bot Configuration
    _env_config['BOT_TOKEN'] = os.getenv('BOT_TOKEN')
    _env_config['COMMAND_PREFIX'] = os.getenv('COMMAND_PREFIX', '!')
    _env_config['DEV_GUILD_ID'] = os.getenv('DEV_GUILD_ID')
    
    # Database Configuration
    _env_config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', 'data/veramon_reunited.db')
    
    # Logging Configuration
    _env_config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')
    _env_config['LOG_FILE'] = os.getenv('LOG_FILE', 'logs/veramon.log')
    
    # Administrator Configuration
    dev_ids = os.getenv('DEVELOPER_IDS', '')
    _env_config['DEVELOPER_IDS'] = [
        int(id.strip()) for id in dev_ids.split(',') if id.strip().isdigit()
    ] if dev_ids else []
    
    # External Services
    _env_config['WEBHOOK_URL'] = os.getenv('WEBHOOK_URL', '')
    _env_config['API_KEY'] = os.getenv('API_KEY', '')
    
    # Performance Settings
    _env_config['CONNECTION_POOL_SIZE'] = int(os.getenv('CONNECTION_POOL_SIZE', '10'))
    _env_config['CACHE_TTL'] = int(os.getenv('CACHE_TTL', '300'))
    
    # Advanced Settings
    _env_config['DEBUG_MODE'] = os.getenv('DEBUG_MODE', 'False').lower() in ('true', '1', 't', 'yes')
    _env_config['MAINTENANCE_MODE'] = os.getenv('MAINTENANCE_MODE', 'False').lower() in ('true', '1', 't', 'yes')
    
    # Validate required configuration
    if not _env_config['BOT_TOKEN']:
        logger.error("BOT_TOKEN is required but not set in .env file")
        print("ERROR: BOT_TOKEN is required but not set in .env file")
        print("Please copy .env.sample to .env and set your Discord bot token")
        sys.exit(1)
    
    return _env_config

def get_env(key: str, default: Any = None) -> Any:
    """
    Get environment configuration value.
    
    Args:
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Any: Configuration value or default if not found
    """
    global _env_config
    
    if _env_config is None:
        load_env_config()
    
    return _env_config.get(key, default)

def is_developer(user_id: int) -> bool:
    """
    Check if a user is a developer based on environment configuration.
    
    Args:
        user_id: Discord user ID to check
        
    Returns:
        bool: True if user is a developer, False otherwise
    """
    return user_id in get_env('DEVELOPER_IDS', [])

def is_maintenance_mode() -> bool:
    """
    Check if the bot is in maintenance mode.
    
    Returns:
        bool: True if in maintenance mode, False otherwise
    """
    return get_env('MAINTENANCE_MODE', False)

def is_debug_mode() -> bool:
    """
    Check if the bot is in debug mode.
    
    Returns:
        bool: True if in debug mode, False otherwise
    """
    return get_env('DEBUG_MODE', False)

def get_connection_pool_size() -> int:
    """
    Get the database connection pool size.
    
    Returns:
        int: Connection pool size
    """
    return get_env('CONNECTION_POOL_SIZE', 10)

def get_cache_ttl() -> int:
    """
    Get the cache time-to-live in seconds.
    
    Returns:
        int: Cache TTL in seconds
    """
    return get_env('CACHE_TTL', 300)

# Initialize by loading environment config
try:
    load_env_config()
except Exception as e:
    logger.error(f"Failed to load environment configuration: {e}")
