#!/usr/bin/env python3
"""
Veramon Reunited - Health Check Script
Verifies that the bot's critical systems are functioning correctly
"""

import os
import sys
import socket
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("veramon-healthcheck")

# Check paths
DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "veramon_reunited.db"
BATTLE_DIR = Path("/app/battle-system-data")
TRADE_DIR = Path("/app/trading-data")

def check_discord_connection():
    """Test connectivity to Discord"""
    try:
        socket.socket().connect(("discord.com", 443))
        logger.info("Discord connectivity: OK")
        return True
    except Exception as e:
        logger.error(f"Discord connectivity failed: {e}")
        return False

def check_database():
    """Verify database is accessible and properly structured"""
    try:
        if not DB_PATH.exists():
            logger.error(f"Database file not found at {DB_PATH}")
            return False
            
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Check for battle tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='battles'")
        has_battle_table = cursor.fetchone() is not None
        
        # Check for trade tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        has_trade_table = cursor.fetchone() is not None
        
        if has_battle_table:
            logger.info("Battle system database: OK")
        else:
            logger.warning("Battle system tables not found in database")
            
        if has_trade_table:
            logger.info("Trading system database: OK")
        else:
            logger.warning("Trading system tables not found in database")
            
        conn.close()
        return has_battle_table and has_trade_table
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

def check_filesystem():
    """Verify that all required directories exist and are writable"""
    try:
        # Check data directory
        if not DATA_DIR.exists() or not os.access(DATA_DIR, os.W_OK):
            logger.error(f"Data directory issues: {DATA_DIR}")
            return False
            
        # Check battle system directory
        if not BATTLE_DIR.exists():
            logger.warning(f"Battle system directory not found: {BATTLE_DIR}")
            try:
                BATTLE_DIR.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created battle system directory: {BATTLE_DIR}")
            except Exception as e:
                logger.error(f"Failed to create battle directory: {e}")
                return False
                
        # Check trading system directory
        if not TRADE_DIR.exists():
            logger.warning(f"Trading system directory not found: {TRADE_DIR}")
            try:
                TRADE_DIR.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created trading system directory: {TRADE_DIR}")
            except Exception as e:
                logger.error(f"Failed to create trading directory: {e}")
                return False
                
        logger.info("Filesystem check: OK")
        return True
    except Exception as e:
        logger.error(f"Filesystem check failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Veramon Reunited health check")
    
    discord_ok = check_discord_connection()
    db_ok = check_database()
    fs_ok = check_filesystem()
    
    if discord_ok and db_ok and fs_ok:
        logger.info("All checks passed!")
        sys.exit(0)
    else:
        logger.error("Health check failed")
        sys.exit(1)
