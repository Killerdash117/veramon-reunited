"""
Database tables for faction economy security features.

This module initializes additional security tables for tracking
rate limiting, transaction history, and security logs.
"""

import sqlite3
from datetime import datetime, timedelta
from src.db.db import get_connection

def create_security_tables():
    """
    Create database tables for security features.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Create rate limit tracking table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS faction_rate_limits (
            user_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            last_action_time TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, action_type)
        )
        """)
        
        # Create detailed transaction audit log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS faction_transaction_log (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            faction_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            item_id TEXT,
            pre_balance INTEGER NOT NULL,
            post_balance INTEGER NOT NULL,
            ip_address TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (faction_id) REFERENCES factions(faction_id)
        )
        """)
        
        # Create security incident log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS faction_security_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            faction_id INTEGER,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            details TEXT,
            resolved INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (faction_id) REFERENCES factions(faction_id)
        )
        """)
        
        # Create faction action limits table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS faction_action_limits (
            faction_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            daily_limit INTEGER NOT NULL,
            weekly_limit INTEGER,
            current_daily_usage INTEGER DEFAULT 0,
            current_weekly_usage INTEGER DEFAULT 0,
            last_reset_daily TEXT,
            last_reset_weekly TEXT,
            PRIMARY KEY (faction_id, action_type),
            FOREIGN KEY (faction_id) REFERENCES factions(faction_id)
        )
        """)
        
        # Create initial default limits if none exist
        cursor.execute("""
        INSERT OR IGNORE INTO faction_action_limits
        (faction_id, action_type, daily_limit, weekly_limit, last_reset_daily, last_reset_weekly)
        SELECT 
            faction_id, 
            'contribution', 
            500000, 
            2500000,
            datetime('now'),
            datetime('now')
        FROM factions
        """)
        
        cursor.execute("""
        INSERT OR IGNORE INTO faction_action_limits
        (faction_id, action_type, daily_limit, weekly_limit, last_reset_daily, last_reset_weekly)
        SELECT 
            faction_id, 
            'purchase', 
            10, 
            50,
            datetime('now'),
            datetime('now')
        FROM factions
        """)
        
        # Create user-faction transfer limits
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_faction_limits (
            user_id TEXT NOT NULL,
            faction_id INTEGER NOT NULL,
            transfer_in_daily_limit INTEGER NOT NULL DEFAULT 100000,
            transfer_out_daily_limit INTEGER NOT NULL DEFAULT 100000,
            transfer_in_current INTEGER DEFAULT 0,
            transfer_out_current INTEGER DEFAULT 0,
            last_reset TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, faction_id),
            FOREIGN KEY (faction_id) REFERENCES factions(faction_id)
        )
        """)
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
def reset_daily_limits():
    """
    Reset daily limits for all factions. This should be called once per day.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Reset faction action daily limits
        cursor.execute("""
        UPDATE faction_action_limits
        SET current_daily_usage = 0,
            last_reset_daily = datetime('now')
        WHERE date(last_reset_daily) < date('now')
        """)
        
        # Reset user-faction transfer daily limits
        cursor.execute("""
        UPDATE user_faction_limits
        SET transfer_in_current = 0,
            transfer_out_current = 0,
            last_reset = datetime('now')
        WHERE date(last_reset) < date('now')
        """)
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
def reset_weekly_limits():
    """
    Reset weekly limits for all factions. This should be called once per week.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check which faction action limits need to be reset
        cursor.execute("""
        UPDATE faction_action_limits
        SET current_weekly_usage = 0,
            last_reset_weekly = datetime('now')
        WHERE julianday('now') - julianday(last_reset_weekly) >= 7
        """)
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
def log_security_event(user_id: str, faction_id: int, event_type: str, severity: str, details: str):
    """
    Log a security event for later review.
    
    Args:
        user_id: ID of the user involved
        faction_id: ID of the faction
        event_type: Type of security event
        severity: Severity level (low, medium, high, critical)
        details: Details about the security event
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO faction_security_log
        (user_id, faction_id, event_type, severity, details, timestamp)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (user_id, faction_id, event_type, severity, details))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        # Don't raise the exception - we don't want security logging to break functionality
    finally:
        conn.close()
        
def check_and_update_rate_limit(user_id: str, action_type: str, max_count: int, interval_seconds: int) -> bool:
    """
    Check if a user has exceeded their rate limit for an action.
    
    Args:
        user_id: ID of the user
        action_type: Type of action being rate limited
        max_count: Maximum number of actions allowed in the interval
        interval_seconds: Time interval in seconds
        
    Returns:
        bool: True if action is allowed, False if rate limit exceeded
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get current rate limit info
        cursor.execute("""
        SELECT last_action_time, count
        FROM faction_rate_limits
        WHERE user_id = ? AND action_type = ?
        """, (user_id, action_type))
        
        result = cursor.fetchone()
        
        current_time = datetime.now()
        
        if not result:
            # First time this user is performing this action
            cursor.execute("""
            INSERT INTO faction_rate_limits (user_id, action_type, last_action_time, count)
            VALUES (?, ?, datetime('now'), 1)
            """, (user_id, action_type))
            conn.commit()
            return True
            
        last_time_str, count = result
        last_time = datetime.fromisoformat(last_time_str.replace(' ', 'T'))
        
        # Check if interval has passed
        if (current_time - last_time).total_seconds() > interval_seconds:
            # Reset count
            cursor.execute("""
            UPDATE faction_rate_limits
            SET last_action_time = datetime('now'), count = 1
            WHERE user_id = ? AND action_type = ?
            """, (user_id, action_type))
            conn.commit()
            return True
            
        # Check if count is below max
        if count < max_count:
            # Increment count
            cursor.execute("""
            UPDATE faction_rate_limits
            SET count = count + 1
            WHERE user_id = ? AND action_type = ?
            """, (user_id, action_type))
            conn.commit()
            return True
            
        # Rate limit exceeded
        return False
        
    except Exception as e:
        conn.rollback()
        # If there's an error, we'll allow the action but log it
        log_security_event(
            user_id, 0, "rate_limit_error", "medium", 
            f"Error checking rate limit: {str(e)}"
        )
        return True
    finally:
        conn.close()
