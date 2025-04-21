"""
Battle Schema Fix for Veramon Reunited
2025 killerdash117 | https://github.com/killerdash117

This script adds the missing 'type' column to the battles table to track
battle types (PvP, PvE, Tournament, etc.)
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.db import get_connection

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("battle_schema_fix")

def add_battle_type_column():
    """Add the missing 'type' column to the battles table."""
    try:
        # Get DB connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(battles)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "type" not in columns:
            logger.info("Adding 'type' column to battles table...")
            
            # Add the column
            cursor.execute("""
            ALTER TABLE battles 
            ADD COLUMN type TEXT DEFAULT 'pvp' NOT NULL
            """)
            
            # Update existing records with default values based on context
            # PvE battles typically have an npc_trainer_id
            cursor.execute("""
            UPDATE battles
            SET type = 'pve'
            WHERE npc_trainer_id IS NOT NULL
            """)
            
            logger.info("Column added successfully. Existing battles categorized as PvP/PvE.")
            
            # Create index on the new column for performance
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_battles_type ON battles(type)
            """)
            
            logger.info("Created index on battles.type")
            
            # Commit changes
            conn.commit()
            return True
        else:
            logger.info("Column 'type' already exists in battles table.")
            return True
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def main():
    """Main function to run the schema fix."""
    logger.info("Starting battle schema fix...")
    
    # Add the missing column
    success = add_battle_type_column()
    
    if success:
        logger.info("Battle schema fix completed successfully.")
    else:
        logger.error("Battle schema fix failed.")
        
    # Run a verification query
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(battles)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "type" in columns:
            logger.info("Verification successful: 'type' column exists in battles table.")
        else:
            logger.error("Verification failed: 'type' column not found in battles table.")
            
    except Exception as e:
        logger.error(f"Verification error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
