"""
Veramon Database Index Optimization Tool
---------------------------------------
This script adds missing indices to the database to improve performance:
1. Creates an index on captures.user_id
2. Creates an index on trades.status
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_optimizer")

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
sys.path.insert(0, parent_dir)

# Import database connection
try:
    from src.db.db import get_connection
except ImportError as e:
    logger.error(f"Failed to import database module: {e}")
    sys.exit(1)

class DatabaseOptimizer:
    def __init__(self):
        """Initialize the database optimizer."""
        try:
            self.conn = get_connection()
            self.cursor = self.conn.cursor()
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
    def check_index_exists(self, table, column):
        """Check if an index exists for a specific column."""
        query = f"""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='{table}' AND sql LIKE '%{column}%'
        """
        
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        
        return result is not None
    
    def create_index(self, table, column, index_name=None):
        """Create an index on a table column."""
        if index_name is None:
            index_name = f"idx_{table}_{column}"
        
        if self.check_index_exists(table, column):
            logger.info(f"Index on {table}.{column} already exists")
            return False
        
        try:
            query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})"
            self.cursor.execute(query)
            self.conn.commit()
            logger.info(f"Created index {index_name} on {table}.{column}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index on {table}.{column}: {e}")
            return False
    
    def optimize_database(self):
        """Add all missing indices to optimize database performance."""
        # List of indices to create [table, column, index_name]
        indices = [
            ["captures", "user_id", "idx_captures_user_id"],
            ["trades", "status", "idx_trades_status"],
            ["battles", "host_id", "idx_battles_host_id"],
            ["battle_logs", "battle_id", "idx_battle_logs_battle_id"],
            ["trade_items", "trade_id", "idx_trade_items_trade_id"]
        ]
        
        created_count = 0
        failed_count = 0
        
        for table, column, index_name in indices:
            if self.create_index(table, column, index_name):
                created_count += 1
            else:
                failed_count += 1
        
        logger.info(f"Created {created_count} indices, {failed_count} failed or already existed")
        
        return created_count > 0
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    print("Veramon Database Index Optimization Tool")
    print("-" * 45)
    
    optimizer = DatabaseOptimizer()
    result = optimizer.optimize_database()
    optimizer.close()
    
    if result:
        print("\nDatabase optimization completed successfully!")
    else:
        print("\nNo new indices were created. Database may already be optimized.")
