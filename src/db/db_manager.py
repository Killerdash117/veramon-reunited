"""
Database Manager for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides centralized database management capabilities, including:
- Connection pooling
- Schema initialization and versioning
- Migration management
- Utilities for backup, restore, and resetting data
- Transaction management
- Performance optimization with caching
"""

import os
import sqlite3
import json
import time
import shutil
import gzip
import zlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from pathlib import Path
from functools import wraps

from src.db.db import get_connection  # Import existing connection function
from src.utils.config_manager import get_config
from src.db.cache_manager import get_cache_manager

# Set up logging
logger = logging.getLogger("db_manager")

# Database version tracking
CURRENT_DB_VERSION = "1.0.0"

# Default configuration - can be overridden in config.json
DEFAULT_CONFIG = {
    "max_backups": 10,                # Maximum number of auto backups to keep
    "backup_compression": True,       # Whether to compress backup files
    "auto_vacuum_days": 7,            # Days between automatic vacuum operations
    "max_backup_age_days": 30,        # Max age for auto backups before pruning
    "log_retention_days": 14,         # Days to keep log entries before cleanup
    "temp_data_retention_days": 7,     # Days to keep temporary data
    "enable_query_caching": True,     # Whether to enable query caching
    "cache_ttl_seconds": 300,         # Default TTL for cached queries (5 minutes)
    "cache_frequent_user_data": True  # Whether to cache frequently accessed user data
}

# Decorator to time database operations for performance monitoring
def time_database_operation(operation_name: str = None):
    """Decorator to time database operations for performance monitoring."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            # Log slow queries (more than 100ms)
            if elapsed_time > 0.1:
                op_name = operation_name or func.__name__
                logger.warning(f"Slow database operation: {op_name} took {elapsed_time:.4f}s")
                
            return result
        return wrapper
    return decorator

class DatabaseManager:
    """
    Database manager for Veramon Reunited.
    
    This class handles all database operations, including initialization,
    migrations, backups, and maintenance.
    """
    
    def __init__(self, db_path: str = "data/veramon.db"):
        """Initialize the database manager."""
        self.db_path = db_path
        self.backup_dir = "data/backups"
        self.config = self._load_config()
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Get cache manager
        self.cache_manager = get_cache_manager()
        
        # Track modified tables for cache invalidation
        self._modified_tables: Set[str] = set()
        
        # Check if automatic maintenance is needed
        self._check_auto_maintenance()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration with fallbacks to defaults."""
        config = get_config()
        db_config = {}
        
        # Use values from config.json if present, otherwise use defaults
        for key, default_value in DEFAULT_CONFIG.items():
            db_config[key] = config.get(key, default_value)
            
        return db_config
        
    def _check_auto_maintenance(self) -> None:
        """Check if automatic maintenance tasks should be run."""
        try:
            # Check when last vacuum was run
            last_vacuum = self._get_metadata_value("last_vacuum_time")
            
            if last_vacuum:
                last_vacuum_time = datetime.fromisoformat(last_vacuum)
                days_since_vacuum = (datetime.now() - last_vacuum_time).days
                
                # Run vacuum if it's been too long
                if days_since_vacuum >= self.config["auto_vacuum_days"]:
                    logger.info(f"Running automatic vacuum (last run: {days_since_vacuum} days ago)")
                    self.vacuum_database()
            
            # Prune old backups
            self._prune_old_backups()
            
            # Clean up old logs
            self._cleanup_logs()
            
        except Exception as e:
            logger.error(f"Error during auto maintenance check: {e}")
    
    def _prune_old_backups(self) -> None:
        """Remove old backups to save space."""
        try:
            # Get all backups sorted by creation date (newest first)
            backups = self.list_backups()
            
            # Keep manual backups (those without timestamp pattern)
            auto_backups = [b for b in backups if self._is_auto_backup(b["filename"])]
            manual_backups = [b for b in backups if not self._is_auto_backup(b["filename"])]
            
            # Limit number of auto backups
            max_auto_backups = self.config["max_backups"]
            backups_to_delete = auto_backups[max_auto_backups:]
            
            # Also identify any backups older than max_backup_age_days
            max_age = timedelta(days=self.config["max_backup_age_days"])
            now = datetime.now()
            
            for backup in auto_backups[:max_auto_backups]:
                created = datetime.fromisoformat(backup["created"])
                if now - created > max_age:
                    backups_to_delete.append(backup)
            
            # Remove duplicates from backups_to_delete
            backups_to_delete = list({b["path"]: b for b in backups_to_delete}.values())
            
            # Delete old backups
            for backup in backups_to_delete:
                try:
                    os.remove(backup["path"])
                    logger.info(f"Pruned old backup: {backup['filename']}")
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup['path']}: {e}")
        
        except Exception as e:
            logger.error(f"Error during backup pruning: {e}")
    
    def _is_auto_backup(self, filename: str) -> bool:
        """Check if a backup was automatically created vs user-created."""
        # Auto backups follow the pattern backup_YYYYMMDD_HHMMSS.db or backup_pre_*.db
        return (filename.startswith("backup_") and 
                (len(filename.split("_")) >= 3 or filename.startswith("backup_pre_")))
    
    def _cleanup_logs(self) -> None:
        """Clean up old log entries from the database."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Calculate cutoff date for log retention
            cutoff_days = self.config["log_retention_days"]
            cutoff_timestamp = (datetime.now() - timedelta(days=cutoff_days)).timestamp()
            
            # Delete old security logs
            cursor.execute("""
                DELETE FROM security_events 
                WHERE timestamp < ?
            """, (cutoff_timestamp,))
            
            security_logs_deleted = cursor.rowcount
            
            # Delete old transaction logs beyond retention period
            cursor.execute("""
                DELETE FROM token_transactions 
                WHERE transaction_time < ?
            """, (cutoff_timestamp,))
            
            transaction_logs_deleted = cursor.rowcount
            
            # Delete old battle logs
            cursor.execute("""
                DELETE FROM battle_logs 
                WHERE timestamp < ?
            """, (cutoff_timestamp,))
            
            battle_logs_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = security_logs_deleted + transaction_logs_deleted + battle_logs_deleted
            if total_deleted > 0:
                logger.info(f"Cleaned up {total_deleted} old log entries")
            
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    def initialize_database(self) -> None:
        """Initialize the database with all required tables."""
        logger.info("Initializing database...")
        
        # Create tables for all game systems
        self._initialize_core_tables()
        self._initialize_veramon_tables()
        self._initialize_user_tables()
        self._initialize_battle_tables()
        self._initialize_trading_tables()
        self._initialize_faction_tables()
        self._initialize_quest_tables()
        self._initialize_security_tables()
        
        # Set database version
        self._set_db_version(CURRENT_DB_VERSION)
        
        logger.info("Database initialization complete.")
    
    def reset_database(self, confirm_text: str = None) -> bool:
        """
        Reset the database by dropping all tables and recreating them.
        
        Args:
            confirm_text: Must be 'CONFIRM_RESET' to proceed with reset
            
        Returns:
            bool: True if reset was successful
        """
        if confirm_text != "CONFIRM_RESET":
            logger.warning("Reset cancelled: Confirmation text not provided.")
            return False
        
        # Create a backup before resetting
        self.create_backup("pre_reset")
        
        # Get all table names
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Drop all tables
        for table in tables:
            if table[0] != "sqlite_sequence" and not table[0].startswith("sqlite_"):
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
        
        conn.commit()
        conn.close()
        
        # Reinitialize the database
        self.initialize_database()
        
        return True
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Create a backup of the current database.
        
        Args:
            backup_name: Optional name for the backup
            
        Returns:
            str: Path to the created backup file
        """
        # Generate backup name if not provided
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        # Ensure .db extension
        if not backup_name.endswith(".db"):
            backup_name += ".db"
        
        # Create backup path
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        # Close connections to allow backup
        # This assumes get_connection uses a single connection pattern
        # If using connection pooling, you'd close the pool here
        conn = get_connection()
        conn.close()
        
        # Create the backup
        shutil.copy2(self.db_path, backup_path)
        
        # Compress backup if configured
        if self.config.get("backup_compression", DEFAULT_CONFIG["backup_compression"]):
            with open(backup_path, "rb") as f_in, gzip.open(backup_path + ".gz", "wb") as f_out:
                f_out.write(zlib.compress(f_in.read()))
            os.remove(backup_path)
            backup_path += ".gz"
        
        logger.info(f"Database backup created at {backup_path}")
        return backup_path
    
    def restore_backup(self, backup_path: str, confirm_text: str = None) -> bool:
        """
        Restore a database from a backup file.
        
        Args:
            backup_path: Path to the backup file
            confirm_text: Must be 'CONFIRM_RESTORE' to proceed
            
        Returns:
            bool: True if restore was successful
        """
        if confirm_text != "CONFIRM_RESTORE":
            logger.warning("Restore cancelled: Confirmation text not provided.")
            return False
        
        if not os.path.exists(backup_path):
            logger.error(f"Restore failed: Backup file {backup_path} not found.")
            return False
        
        # Create a backup of current state before restoring
        self.create_backup("pre_restore")
        
        # Close connections before restoring
        conn = get_connection()
        conn.close()
        
        # Decompress if it's a compressed backup
        if backup_path.endswith(".gz"):
            try:
                decompressed_path = backup_path[:-3]  # Remove .gz extension
                with gzip.open(backup_path, 'rb') as f_in, open(decompressed_path, 'wb') as f_out:
                    f_out.write(f_in.read())
                backup_path = decompressed_path
            except Exception as e:
                logger.error(f"Error decompressing backup: {e}")
                return False
        
        # Restore from backup
        shutil.copy2(backup_path, self.db_path)
        
        # Clean up temporary decompressed file if we created one
        if backup_path.endswith(".db") and os.path.exists(backup_path) and backup_path != self.db_path:
            try:
                os.remove(backup_path)
            except:
                pass
        
        logger.info(f"Database restored from {backup_path}")
        return True
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List[Dict[str, Any]]: List of backup information
        """
        backups = []
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".db") or filename.endswith(".db.gz"):
                file_path = os.path.join(self.backup_dir, filename)
                stat = os.stat(file_path)
                
                backups.append({
                    "filename": filename,
                    "path": file_path,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created"], reverse=True)
        
        return backups
    
    def clear_table(self, table_name: str, confirm: bool = False) -> bool:
        """
        Clear a specific table without dropping it.
        
        Args:
            table_name: Name of the table to clear
            confirm: Must be True to proceed
            
        Returns:
            bool: True if clear was successful
        """
        if not confirm:
            logger.warning(f"Clear cancelled: Confirmation not provided.")
            return False
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                logger.warning(f"Table {table_name} does not exist.")
                return False
            
            # Clear the table
            cursor.execute(f"DELETE FROM {table_name}")
            
            # Reset autoincrement if table has an INTEGER PRIMARY KEY
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name=?", (table_name,))
            
            conn.commit()
            logger.info(f"Table {table_name} cleared successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing table {table_name}: {e}")
            return False
        finally:
            conn.close()
    
    def get_table_sizes(self) -> List[Dict[str, Any]]:
        """
        Get sizes of all tables in the database.
        
        Returns:
            List[Dict[str, Any]]: List of table information sorted by size
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        table_sizes = []
        for table in tables:
            table_name = table[0]
            if table_name.startswith("sqlite_"):
                continue
                
            # Count rows
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Estimate size (this is approximate)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            if row_count > 0:
                # Get column names from cursor description
                columns = [description[0] for description in cursor.description]
                # Get a sample row to estimate size
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                sample_row = cursor.fetchone()
                # Estimate row size in bytes
                row_size = sum(len(str(value).encode('utf-8')) for value in sample_row)
                total_size = row_count * row_size
            else:
                columns = []
                row_size = 0
                total_size = 0
                
            table_sizes.append({
                "name": table_name,
                "rows": row_count,
                "columns": len(columns),
                "estimated_size_kb": round(total_size / 1024, 2),
                "column_names": columns
            })
        
        # Sort by size (largest first)
        table_sizes.sort(key=lambda x: x["estimated_size_kb"], reverse=True)
        
        conn.close()
        return table_sizes
    
    def vacuum_database(self) -> bool:
        """
        Run VACUUM to optimize database and reclaim space.
        
        Returns:
            bool: True if vacuum was successful
        """
        try:
            conn = get_connection()
            conn.execute("VACUUM")
            conn.close()
            
            # Update last vacuum time
            self._set_metadata_value("last_vacuum_time", datetime.now().isoformat())
            
            logger.info("Database vacuum completed successfully.")
            return True
        except Exception as e:
            logger.error(f"Error during database vacuum: {e}")
            return False
    
    def analyze_database_usage(self) -> Dict[str, Any]:
        """
        Analyze database usage and provide optimization recommendations.
        
        Returns:
            Dict[str, Any]: Analysis results and recommendations
        """
        results = {
            "total_size_mb": 0,
            "tables": [],
            "indices": [],
            "recommendations": []
        }
        
        try:
            # Get database file size
            db_size = os.path.getsize(self.db_path) / (1024 * 1024)
            results["total_size_mb"] = round(db_size, 2)
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get detailed table info
            total_rows = 0
            for table in tables:
                # Row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                total_rows += row_count
                
                # Table structure
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                # Get indices for this table
                cursor.execute(f"PRAGMA index_list({table})")
                indices = cursor.fetchall()
                index_names = [idx[1] for idx in indices]
                
                # Estimate average row size
                avg_row_size = 0
                if row_count > 0:
                    # Sample up to 100 rows to estimate size
                    cursor.execute(f"SELECT * FROM {table} LIMIT 100")
                    sample_rows = cursor.fetchall()
                    if sample_rows:
                        # Calculate the average size of the serialized row
                        avg_row_size = sum(len(str(row).encode('utf-8')) for row in sample_rows) / len(sample_rows)
                
                # Calculate estimated table size
                est_table_size = row_count * avg_row_size / 1024  # in KB
                
                results["tables"].append({
                    "name": table,
                    "rows": row_count,
                    "columns": len(columns),
                    "indices": len(indices),
                    "estimated_size_kb": round(est_table_size, 2),
                    "column_details": [{
                        "name": col[1], 
                        "type": col[2], 
                        "is_primary": bool(col[5])
                    } for col in columns],
                    "has_indices": bool(indices)
                })
                
                # Add indices details
                for idx in indices:
                    cursor.execute(f"PRAGMA index_info({idx[1]})")
                    idx_columns = cursor.fetchall()
                    results["indices"].append({
                        "name": idx[1],
                        "table": table,
                        "unique": bool(idx[2]),
                        "columns": [col[2] for col in idx_columns]
                    })
            
            # Generate recommendations
            tables_without_indices = [t["name"] for t in results["tables"] if not t["has_indices"] and t["rows"] > 1000]
            if tables_without_indices:
                results["recommendations"].append({
                    "type": "missing_indices",
                    "description": f"Tables with >1000 rows missing indices: {', '.join(tables_without_indices)}",
                    "impact": "high"
                })
            
            # Check database fragmentation
            if db_size > 50 and db_size > total_rows * avg_row_size * 2 / (1024 * 1024):
                results["recommendations"].append({
                    "type": "fragmentation",
                    "description": "Database appears fragmented. Consider running VACUUM.",
                    "impact": "medium"
                })
            
            # Check for oversized tables that could be archived
            large_log_tables = [t["name"] for t in results["tables"] 
                               if "log" in t["name"].lower() and t["estimated_size_kb"] > 5000]
            if large_log_tables:
                results["recommendations"].append({
                    "type": "large_logs",
                    "description": f"Consider archiving old log data from: {', '.join(large_log_tables)}",
                    "impact": "medium"
                })
            
            # Check for temporary tables that might not be cleaned up
            temp_tables = [t["name"] for t in results["tables"] if "temp" in t["name"].lower()]
            if temp_tables:
                results["recommendations"].append({
                    "type": "temp_tables",
                    "description": f"Temporary tables found that may need cleanup: {', '.join(temp_tables)}",
                    "impact": "low"
                })
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error analyzing database: {e}")
            results["error"] = str(e)
        
        return results
    
    def clean_temporary_data(self) -> bool:
        """
        Clean temporary data that may accumulate over time.
        
        Returns:
            bool: True if cleanup was successful
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Calculate cutoff time
            cutoff_days = self.config["temp_data_retention_days"]
            cutoff_timestamp = (datetime.now() - timedelta(days=cutoff_days)).timestamp()
            
            # Clean up expired spawn data
            cursor.execute("""
                DELETE FROM spawn_data 
                WHERE created_at < ? AND status = 'expired'
            """, (cutoff_timestamp,))
            
            spawn_deleted = cursor.rowcount
            
            # Clean up old battle data for completed battles
            cursor.execute("""
                DELETE FROM battles 
                WHERE ended_at < ? AND status IN ('completed', 'expired', 'cancelled')
            """, (cutoff_timestamp,))
            
            battles_deleted = cursor.rowcount
            
            # Clean up old trade data for completed trades
            cursor.execute("""
                DELETE FROM trades
                WHERE completed_at < ? AND status IN ('completed', 'rejected', 'cancelled')
            """, (cutoff_timestamp,))
            
            trades_deleted = cursor.rowcount
            
            # Clean up old event data
            cursor.execute("""
                DELETE FROM event_reminders
                WHERE reminded = 1 AND remind_at < ?
            """, (cutoff_timestamp,))
            
            events_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = spawn_deleted + battles_deleted + trades_deleted + events_deleted
            if total_deleted > 0:
                logger.info(f"Cleaned up {total_deleted} temporary data records")
            
            return True
        except Exception as e:
            logger.error(f"Error cleaning temporary data: {e}")
            return False
    
    def _get_metadata_value(self, key: str) -> Optional[str]:
        """Get a value from the database metadata table."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM db_metadata WHERE key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
        except Exception:
            return None
    
    def _set_metadata_value(self, key: str, value: str) -> None:
        """Set a value in the database metadata table."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ensure the metadata table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Insert or update the value
        timestamp = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO db_metadata (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, timestamp))
        
        conn.commit()
        conn.close()
    
    def _set_db_version(self, version: str) -> None:
        """Set the database version in the metadata table."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create metadata table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Insert or update version
        timestamp = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO db_metadata (key, value, updated_at)
            VALUES ('version', ?, ?)
        """, (version, timestamp))
        
        conn.commit()
        conn.close()
    
    def get_db_version(self) -> str:
        """Get the current database version."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT value FROM db_metadata WHERE key = 'version'")
            result = cursor.fetchone()
            return result[0] if result else "unknown"
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return "unknown"
        finally:
            conn.close()
    
    def _initialize_core_tables(self) -> None:
        """Initialize core database tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Metadata table for database versioning and configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create directories needed for data
        os.makedirs("data", exist_ok=True)
        
        conn.commit()
        conn.close()
    
    def _initialize_user_tables(self) -> None:
        """Initialize user-related tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                tokens INTEGER DEFAULT 0,
                last_daily_claim REAL DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                settings TEXT
            )
        """)
        
        # Inventory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                acquired_at TEXT NOT NULL,
                UNIQUE(user_id, item_id)
            )
        """)
        
        # User settings and preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                theme TEXT DEFAULT 'default',
                notifications INTEGER DEFAULT 1,
                privacy_level INTEGER DEFAULT 0,
                ui_settings TEXT,
                last_updated TEXT NOT NULL
            )
        """)
        
        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id)")
        
        conn.commit()
        conn.close()
    
    def _initialize_veramon_tables(self) -> None:
        """Initialize Veramon-related tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Captures table for Veramon owned by players
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                veramon_name TEXT NOT NULL,
                nickname TEXT,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                shiny INTEGER NOT NULL DEFAULT 0,
                caught_at TEXT NOT NULL,
                biome TEXT NOT NULL,
                stats TEXT NOT NULL,
                moves TEXT NOT NULL,
                active_form TEXT DEFAULT 'normal'
            )
        """)
        
        # Veramon forms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS veramon_forms (
                capture_id INTEGER NOT NULL,
                form_name TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                form_stats TEXT NOT NULL,
                PRIMARY KEY (capture_id, form_name),
                FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
            )
        """)
        
        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_captures_user_id ON captures(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_captures_veramon_name ON captures(veramon_name)")
        
        conn.commit()
        conn.close()
    
    def _initialize_battle_tables(self) -> None:
        """Initialize battle-related tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Battles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                battle_type TEXT NOT NULL,
                status TEXT NOT NULL,
                participant1_id TEXT NOT NULL,
                participant2_id TEXT,
                winner_id TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                battle_data TEXT,
                current_turn INTEGER DEFAULT 1,
                last_action_at TEXT NOT NULL
            )
        """)
        
        # Battle participants
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battle_participants (
                battle_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                team_id INTEGER,
                ready INTEGER DEFAULT 0,
                PRIMARY KEY (battle_id, user_id),
                FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE
            )
        """)
        
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
        
        # Team members
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                capture_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                UNIQUE(team_id, position)
            )
        """)
        
        # Battle logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battle_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                battle_id INTEGER NOT NULL,
                log_type TEXT NOT NULL,
                turn INTEGER NOT NULL,
                actor_id TEXT,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (battle_id) REFERENCES battles(id) ON DELETE CASCADE
            )
        """)
        
        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_participant1 ON battles(participant1_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_participant2 ON battles(participant2_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_status ON battles(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_logs_battle_id ON battle_logs(battle_id)")
        
        conn.commit()
        conn.close()
    
    def _initialize_trading_tables(self) -> None:
        """Initialize trading-related tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                initiator_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                message TEXT
            )
        """)
        
        # Trade Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
            )
        """)
        
        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_initiator ON trades(initiator_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_recipient ON trades(recipient_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_items_trade_id ON trade_items(trade_id)")
        
        conn.commit()
        conn.close()
    
    def _initialize_faction_tables(self) -> None:
        """Initialize faction-related tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Factions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                leader_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                treasury INTEGER DEFAULT 0,
                banner_url TEXT,
                settings TEXT
            )
        """)
        
        # Faction members
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faction_members (
                faction_id INTEGER NOT NULL,
                user_id TEXT NOT NULL PRIMARY KEY,
                rank TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                permissions TEXT,
                contribution INTEGER DEFAULT 0,
                FOREIGN KEY (faction_id) REFERENCES factions(id) ON DELETE CASCADE
            )
        """)
        
        # Faction buffs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faction_buffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faction_id INTEGER NOT NULL,
                buff_id TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (faction_id) REFERENCES factions(id) ON DELETE CASCADE
            )
        """)
        
        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_members_faction_id ON faction_members(faction_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_buffs_faction_id ON faction_buffs(faction_id)")
        
        conn.commit()
        conn.close()
    
    def _initialize_quest_tables(self) -> None:
        """Initialize quest-related tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # User quests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_quests (
                user_id TEXT NOT NULL,
                quest_id TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                started_at TEXT NOT NULL,
                PRIMARY KEY (user_id, quest_id)
            )
        """)
        
        # User achievements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id TEXT NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                PRIMARY KEY (user_id, achievement_id)
            )
        """)
        
        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_quests_user_id ON user_quests(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements(user_id)")
        
        conn.commit()
        conn.close()
    
    def _initialize_security_tables(self) -> None:
        """Initialize security-related tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Security events table for logging
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                severity TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ip_address TEXT
            )
        """)
        
        # Rate limiting table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                last_action_time REAL NOT NULL,
                action_count INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, action_type)
            )
        """)
        
        # Token transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT,
                recipient_id TEXT,
                amount INTEGER,
                transaction_time TEXT,
                message TEXT,
                transaction_type TEXT
            )
        """)
        
        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp)")
        
        conn.commit()
        conn.close()

    def execute_query(self, query: str, params: Tuple = None, fetch: str = "all", 
                      cacheable: bool = False, tables: List[str] = None,
                      ttl: int = None) -> Any:
        """
        Execute a database query with caching support.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Fetch mode ('all', 'one', or None for no fetch)
            cacheable: Whether this query result can be cached
            tables: Tables this query depends on (for invalidation)
            ttl: Time to live in seconds for cached result
            
        Returns:
            Query results based on fetch mode
        """
        # Only use cache for SELECT queries that are marked as cacheable
        is_select = query.strip().upper().startswith("SELECT")
        use_cache = (
            self.config.get("enable_query_caching", True) and 
            cacheable and 
            is_select and 
            fetch in ("all", "one")
        )
        
        result = None
        cache_hit = False
        
        # Try to get from cache
        if use_cache:
            cached_result = self.cache_manager.get_query_result(query, params)
            if cached_result is not None:
                result = cached_result
                cache_hit = True
        
        # Execute the query if not cached
        if not cache_hit:
            conn = get_connection()
            cursor = conn.cursor()
            
            start_time = time.time()
            cursor.execute(query, params or ())
            
            if fetch == "all":
                result = cursor.fetchall()
            elif fetch == "one":
                result = cursor.fetchone()
            else:
                result = None
                
            # Track slow queries
            elapsed_time = time.time() - start_time
            if elapsed_time > 0.1:  # Log queries taking more than 100ms
                logger.warning(f"Slow query: {query} took {elapsed_time:.4f}s")
            
            # If this is a write operation, track modified tables for cache invalidation
            if not is_select and tables:
                self._modified_tables.update(tables)
                
            # Cache the result if appropriate
            if use_cache and result is not None:
                ttl = ttl or self.config.get("cache_ttl_seconds", 300)
                self.cache_manager.cache_query_result(query, params, result, ttl, tables)
                
            conn.close()
            
        return result
        
    def execute_script(self, script: str, params: Dict[str, Any] = None) -> None:
        """
        Execute a SQL script with parameter substitution.
        
        Args:
            script: SQL script to execute
            params: Parameters to substitute in the script
        """
        # Substitute parameters if provided
        if params:
            for key, value in params.items():
                placeholder = f":{key}"
                # Convert value to string if not None
                if value is not None:
                    script = script.replace(placeholder, str(value))
                else:
                    script = script.replace(placeholder, "NULL")
                    
        conn = get_connection()
        start_time = time.time()
        
        try:
            conn.executescript(script)
            conn.commit()
            
            # Track slow script execution
            elapsed_time = time.time() - start_time
            if elapsed_time > 1.0:  # Log scripts taking more than 1s
                logger.warning(f"Slow script execution took {elapsed_time:.4f}s")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error executing script: {e}")
            raise
        finally:
            conn.close()
    
    def transaction(self) -> 'DatabaseTransaction':
        """
        Create a transaction context for executing multiple queries atomically.
        
        Returns:
            DatabaseTransaction object
        
        Usage:
            with db_manager.transaction() as tx:
                tx.execute("INSERT INTO ...", params)
                tx.execute("UPDATE ...", params)
        """
        return DatabaseTransaction(self)
        
    def invalidate_cache_for_tables(self, tables: List[str]) -> None:
        """
        Invalidate cache for specific tables.
        
        Args:
            tables: List of table names to invalidate
        """
        if not tables:
            return
            
        self.cache_manager.invalidate_tables(tables)
        logger.debug(f"Invalidated cache for tables: {', '.join(tables)}")
    
    def clear_all_caches(self) -> None:
        """Clear all database caches."""
        self.cache_manager.clear_all_caches()
        logger.info("Cleared all database caches")
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get database cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache_manager.get_cache_stats()
        
    # User data methods with caching
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data with caching support.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            User data dictionary or None if not found
        """
        # Try to get from cache first
        if self.config.get("cache_frequent_user_data", True):
            cached_user = self.cache_manager.get_user_data(user_id)
            if cached_user is not None:
                return cached_user
                
        # Query from database if not in cache
        result = self.execute_query(
            "SELECT * FROM users WHERE user_id = ?", 
            (user_id,), 
            fetch="one",
            cacheable=True,
            tables=["users"]
        )
        
        if result:
            # Convert to dictionary
            columns = [col[0] for col in result.description] if hasattr(result, 'description') else []
            user_data = dict(zip(columns, result))
            
            # Cache the result
            if self.config.get("cache_frequent_user_data", True):
                self.cache_manager.cache_user_data(user_id, user_data)
                
            return user_data
        
        return None
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update user data and invalidate cache.
        
        Args:
            user_id: Discord user ID
            updates: Dictionary of column names and values to update
            
        Returns:
            True if update was successful
        """
        if not updates:
            return False
            
        # Build SET clause for UPDATE statement
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
            
        # Add user_id to params
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = ?"
        
        result = self.execute_query(query, tuple(params), fetch=None, tables=["users"])
        
        # Invalidate cache for this user
        self.cache_manager.invalidate_user_data(user_id)
        
        return True
    
    # Veramon data methods with caching
    
    def get_veramon(self, veramon_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Veramon data with caching support.
        
        Args:
            veramon_id: Veramon instance ID
            
        Returns:
            Veramon data dictionary or None if not found
        """
        # Try to get from cache first
        cached_veramon = self.cache_manager.get_veramon_data(veramon_id)
        if cached_veramon is not None:
            return cached_veramon
                
        # Query from database if not in cache
        result = self.execute_query(
            "SELECT * FROM user_veramon WHERE id = ?", 
            (veramon_id,), 
            fetch="one",
            cacheable=True,
            tables=["user_veramon"]
        )
        
        if result:
            # Convert to dictionary
            columns = [col[0] for col in result.description] if hasattr(result, 'description') else []
            veramon_data = dict(zip(columns, result))
            
            # Cache the result
            self.cache_manager.cache_veramon_data(veramon_id, veramon_data)
                
            return veramon_data
        
        return None
    
    def update_veramon(self, veramon_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update Veramon data and invalidate cache.
        
        Args:
            veramon_id: Veramon instance ID
            updates: Dictionary of column names and values to update
            
        Returns:
            True if update was successful
        """
        if not updates:
            return False
            
        # Build SET clause for UPDATE statement
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
            
        # Add veramon_id to params
        params.append(veramon_id)
        
        query = f"UPDATE user_veramon SET {', '.join(set_clauses)} WHERE id = ?"
        
        result = self.execute_query(query, tuple(params), fetch=None, tables=["user_veramon"])
        
        # Invalidate cache for this Veramon
        self.cache_manager.invalidate_veramon_data(veramon_id)
        
        return True

class DatabaseTransaction:
    """
    Context manager for database transactions.
    
    This class allows for executing multiple queries as a single atomic transaction.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.conn = None
        self.cursor = None
        self.modified_tables: Set[str] = set()
        
    def __enter__(self) -> 'DatabaseTransaction':
        """Start a new transaction."""
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Commit or rollback the transaction."""
        if exc_type is None:
            # Commit if no exception
            self.conn.commit()
            
            # Invalidate cache for modified tables
            if self.modified_tables:
                self.db_manager.invalidate_cache_for_tables(list(self.modified_tables))
        else:
            # Rollback on exception
            self.conn.rollback()
            
        self.conn.close()
        
    def execute(self, query: str, params: Tuple = None, fetch: str = None, 
                tables: List[str] = None) -> Any:
        """
        Execute a query within this transaction.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Fetch mode ('all', 'one', or None for no fetch)
            tables: Tables affected by this query (for cache invalidation)
            
        Returns:
            Query results based on fetch mode
        """
        # Track modified tables for cache invalidation
        is_select = query.strip().upper().startswith("SELECT")
        if not is_select and tables:
            self.modified_tables.update(tables)
            
        # Execute the query
        start_time = time.time()
        self.cursor.execute(query, params or ())
        
        result = None
        if fetch == "all":
            result = self.cursor.fetchall()
        elif fetch == "one":
            result = self.cursor.fetchone()
            
        # Track slow queries
        elapsed_time = time.time() - start_time
        if elapsed_time > 0.1:  # Log queries taking more than 100ms
            logger.warning(f"Slow query in transaction: {query} took {elapsed_time:.4f}s")
            
        return result

# Singleton instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
        
    return _db_manager

# Database administration commands for the bot
async def clear_table_cmd(interaction, table_name: str) -> None:
    """Discord command to clear a specific table."""
    # Implementation here
    pass

async def backup_database_cmd(interaction, backup_name: Optional[str] = None) -> None:
    """Discord command to create a database backup."""
    # Implementation here
    pass

async def view_table_sizes_cmd(interaction) -> None:
    """Discord command to view sizes of database tables."""
    # Implementation here
    pass
