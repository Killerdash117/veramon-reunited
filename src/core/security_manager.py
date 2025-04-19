"""
Security Manager for Veramon Reunited

This module provides centralized security functions for validating
user actions, preventing exploits, and enforcing rate limits across
all game systems.
"""

import json
import time
import sqlite3
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Union

from src.db.db import get_connection
from src.utils.config_manager import get_config


class ActionType(Enum):
    """Types of actions that can be rate-limited or validated"""
    EXPLORE = auto()              # Exploring for wild Veramon
    CATCH = auto()                  # Attempting to catch a Veramon
    BATTLE_CREATE = auto()  # Creating a new battle
    BATTLE_ACTION = auto()  # Taking an action in battle
    TRADE_CREATE = auto()    # Creating a new trade
    TRADE_ACTION = auto()    # Adding/removing items in a trade
    SHOP_BUY = auto()            # Buying from the shop
    DAILY_CLAIM = auto()      # Claiming daily rewards
    EVOLVE = auto()                # Evolving a Veramon
    TRANSFORM = auto()          # Transforming a Veramon
    TOKEN_TRANSFER = auto() # Transferring tokens
    CONTRIB_FACTION = auto() # Contributing to faction
    PROFILE_VIEW = auto()
    LEADERBOARD_VIEW = auto()
    TRANSACTION_HISTORY_VIEW = auto()
    TEAM_VIEW = auto()
    TEAM_MODIFY = auto()
    TEAM_MEMBER_MODIFY = auto()


class SecurityManager:
    """
    Provides security checks and validations for all game systems.
    
    This class handles:
    - Rate limiting for actions
    - Input validation
    - Transaction verification
    - Exploit prevention
    """
    
    def __init__(self):
        """Initialize the security manager and ensure DB tables exist."""
        self._initialize_database()
        
    def _initialize_database(self):
        """Set up required security database tables."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Rate limiting table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                first_action_time TEXT NOT NULL,
                last_action_time TEXT NOT NULL,
                PRIMARY KEY (user_id, action_type)
            )
            """)
            
            # Transaction log for audit trail
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                client_version TEXT
            )
            """)
            
            # Suspicious activity detection
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                resolved INTEGER DEFAULT 0
            )
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def check_rate_limit(self, user_id: str, action_type: Union[ActionType, str], 
                         max_actions: int, time_window_seconds: int) -> bool:
        """
        Check if a user has exceeded their rate limit for an action.
        
        Args:
            user_id: Discord ID of the user
            action_type: Type of action (explore, catch, etc.)
            max_actions: Maximum allowed actions in the time window
            time_window_seconds: Time window in seconds
            
        Returns:
            bool: True if action is allowed, False if rate limit exceeded
        """
        if isinstance(action_type, ActionType):
            action_type = action_type.name
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            current_time = datetime.utcnow()
            time_window_start = (current_time - timedelta(seconds=time_window_seconds)).isoformat()
            
            # Get current usage
            cursor.execute("""
            SELECT count, first_action_time, last_action_time 
            FROM rate_limits
            WHERE user_id = ? AND action_type = ?
            """, (user_id, action_type))
            
            result = cursor.fetchone()
            
            if not result:
                # First action, create new record
                cursor.execute("""
                INSERT INTO rate_limits (user_id, action_type, count, first_action_time, last_action_time)
                VALUES (?, ?, 1, ?, ?)
                """, (user_id, action_type, current_time.isoformat(), current_time.isoformat()))
                conn.commit()
                return True
                
            count, first_action_time, last_action_time = result
            
            # Reset counter if window has passed
            if first_action_time < time_window_start:
                cursor.execute("""
                UPDATE rate_limits
                SET count = 1, first_action_time = ?, last_action_time = ?
                WHERE user_id = ? AND action_type = ?
                """, (current_time.isoformat(), current_time.isoformat(), user_id, action_type))
                conn.commit()
                return True
                
            # Check if limit exceeded
            if count >= max_actions:
                # Log potential abuse attempt
                if count > max_actions + 3:  # Multiple attempts after hitting limit
                    self.log_security_alert(
                        user_id=user_id,
                        alert_type="rate_limit_abuse",
                        severity="medium",
                        details=f"Attempted {action_type} {count - max_actions} times after hitting rate limit"
                    )
                return False
                
            # Increment count
            cursor.execute("""
            UPDATE rate_limits
            SET count = count + 1, last_action_time = ?
            WHERE user_id = ? AND action_type = ?
            """, (current_time.isoformat(), user_id, action_type))
            conn.commit()
            return True
            
        finally:
            conn.close()
            
    def log_transaction(self, user_id: str, action_type: Union[ActionType, str], 
                       details: Dict[str, Any], ip_address: Optional[str] = None,
                       client_version: Optional[str] = None):
        """
        Log a transaction for audit purposes.
        
        Args:
            user_id: Discord ID of the user
            action_type: Type of action performed
            details: Details about the transaction (JSON serializable)
            ip_address: Optional IP address of the user
            client_version: Optional client version
        """
        if isinstance(action_type, ActionType):
            action_type = action_type.name
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            details_json = json.dumps(details)
            current_time = datetime.utcnow().isoformat()
            
            cursor.execute("""
            INSERT INTO transaction_log (user_id, action_type, details, timestamp, ip_address, client_version)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, action_type, details_json, current_time, ip_address, client_version))
            
            conn.commit()
        finally:
            conn.close()
            
    def log_security_alert(self, user_id: str, alert_type: str, 
                         severity: str, details: str):
        """
        Log a security alert for admin review.
        
        Args:
            user_id: Discord ID of the user
            alert_type: Type of security alert
            severity: Severity level (low, medium, high, critical)
            details: Details about the alert
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            current_time = datetime.utcnow().isoformat()
            
            cursor.execute("""
            INSERT INTO security_alerts (user_id, alert_type, severity, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, alert_type, severity, details, current_time))
            
            conn.commit()
        finally:
            conn.close()
            
    def validate_transaction(self, user_id: str, item_type: str, 
                           item_id: Any, action: str) -> bool:
        """
        Validate that a transaction is legitimate based on ownership status.
        
        Args:
            user_id: Discord ID of the user
            item_type: Type of item (veramon, item, currency)
            item_id: ID of the specific item
            action: Type of action (trade, battle, evolve, etc.)
            
        Returns:
            bool: True if transaction is valid, False otherwise
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            if item_type == "veramon":
                # Check Veramon ownership
                cursor.execute("""
                SELECT COUNT(*) FROM captures
                WHERE user_id = ? AND capture_id = ?
                """, (user_id, item_id))
                
                count = cursor.fetchone()[0]
                if count == 0:
                    # Log potential ownership manipulation attempt
                    self.log_security_alert(
                        user_id=user_id,
                        alert_type="ownership_manipulation",
                        severity="high",
                        details=f"Attempted {action} with unowned Veramon ID {item_id}"
                    )
                    return False
                    
                # Check if Veramon is locked in another transaction
                cursor.execute("""
                SELECT COUNT(*) FROM transaction_locks
                WHERE item_type = 'veramon' AND item_id = ? AND lock_type != ? AND expires_at > ?
                """, (item_id, action, datetime.utcnow().isoformat()))
                
                if cursor.fetchone()[0] > 0:
                    return False
                    
            elif item_type == "item":
                # Check item ownership and quantity
                cursor.execute("""
                SELECT quantity FROM inventory
                WHERE user_id = ? AND item_id = ?
                """, (user_id, item_id))
                
                result = cursor.fetchone()
                if not result or result[0] <= 0:
                    # Log potential inventory manipulation attempt
                    self.log_security_alert(
                        user_id=user_id,
                        alert_type="inventory_manipulation",
                        severity="medium",
                        details=f"Attempted {action} with unowned item {item_id}"
                    )
                    return False
                    
            elif item_type == "currency":
                # Check if user has enough tokens
                amount = item_id  # In this case, item_id is the amount
                cursor.execute("""
                SELECT tokens FROM users
                WHERE user_id = ?
                """, (user_id,))
                
                result = cursor.fetchone()
                if not result or result[0] < amount:
                    # Log potential currency manipulation attempt
                    self.log_security_alert(
                        user_id=user_id,
                        alert_type="currency_manipulation",
                        severity="high",
                        details=f"Attempted {action} with insufficient tokens (has {result[0] if result else 0}, needs {amount})"
                    )
                    return False
            
            return True
            
        finally:
            conn.close()
            
    def check_suspicious_patterns(self, user_id: str) -> bool:
        """
        Check for suspicious activity patterns for a user.
        
        Args:
            user_id: Discord ID of the user
            
        Returns:
            bool: True if suspicious activity detected, False otherwise
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check rapid transfers between accounts
            time_window = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            
            # Check for cycling tokens between accounts
            cursor.execute("""
            WITH token_transfers AS (
                SELECT recipient_id, COUNT(*) as transfer_count
                FROM transaction_log
                WHERE user_id = ? 
                AND action_type = 'token_transfer'
                AND timestamp > ?
                GROUP BY recipient_id
            )
            SELECT COUNT(*) FROM token_transfers
            WHERE transfer_count > 3
            """, (user_id, time_window))
            
            if cursor.fetchone()[0] > 0:
                self.log_security_alert(
                    user_id=user_id,
                    alert_type="token_cycling",
                    severity="high",
                    details="Detected potential token cycling between accounts"
                )
                return True
                
            # Check for suspicious catch rate
            cursor.execute("""
            SELECT COUNT(*) 
            FROM transaction_log
            WHERE user_id = ? 
            AND action_type = 'catch'
            AND details LIKE '%"rarity":"legendary"%'
            AND timestamp > ?
            """, (user_id, time_window))
            
            legendary_catches = cursor.fetchone()[0]
            
            if legendary_catches > 3:  # More than 3 legendary catches in an hour is very unlikely
                self.log_security_alert(
                    user_id=user_id,
                    alert_type="suspicious_catch_rate",
                    severity="medium",
                    details=f"Caught {legendary_catches} legendary Veramon in the last hour"
                )
                return True
                
            return False
            
        finally:
            conn.close()
            
    def validate_evolution(self, user_id: str, capture_id: int,
                          evolution_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate that a Veramon evolution is legitimate.
        
        Args:
            user_id: Discord ID of the user
            capture_id: ID of the captured Veramon
            evolution_id: ID of the evolution target
            
        Returns:
            Dict or None: Error dict if invalid, None if valid
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check ownership
            cursor.execute("""
            SELECT c.veramon_id, c.level, c.xp, v.evolutions
            FROM captures c
            JOIN veramon v ON c.veramon_id = v.id
            WHERE c.capture_id = ? AND c.user_id = ?
            """, (capture_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return {"error": "You don't own this Veramon"}
                
            veramon_id, level, xp, evolutions_json = result
            
            # Parse evolutions
            try:
                evolutions = json.loads(evolutions_json) if evolutions_json else {}
            except json.JSONDecodeError:
                return {"error": "Invalid evolution data in database"}
                
            # Check if this evolution is valid for this Veramon
            if evolution_id not in evolutions:
                self.log_security_alert(
                    user_id=user_id,
                    alert_type="invalid_evolution",
                    severity="high",
                    details=f"Attempted invalid evolution {evolution_id} for Veramon {veramon_id}"
                )
                return {"error": "Invalid evolution target"}
                
            evolution_data = evolutions[evolution_id]
            
            # Check level requirement
            if level < evolution_data.get("level_required", 999):
                return {"error": f"Your Veramon needs to be level {evolution_data.get('level_required')} to evolve"}
                
            # Check item requirement if any
            if "item_required" in evolution_data:
                item_id = evolution_data["item_required"]
                
                cursor.execute("""
                SELECT quantity FROM inventory
                WHERE user_id = ? AND item_id = ?
                """, (user_id, item_id))
                
                item_result = cursor.fetchone()
                if not item_result or item_result[0] <= 0:
                    return {"error": f"You need a {item_id} to perform this evolution"}
                    
            return None  # No errors, evolution is valid
            
        finally:
            conn.close()
            
    def validate_trade(self, trade_id: int, user_id: str, 
                      action: str, item_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Validate a trade action.
        
        Args:
            trade_id: ID of the trade
            user_id: Discord ID of the user
            action: Trade action (add_item, remove_item, confirm, cancel)
            item_data: Optional item data for add_item
            
        Returns:
            Dict or None: Error dict if invalid, None if valid
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check trade exists and user is a participant
            cursor.execute("""
            SELECT initiator_id, target_id, status
            FROM trades
            WHERE id = ?
            """, (trade_id,))
            
            trade = cursor.fetchone()
            if not trade:
                return {"error": "Trade not found"}
                
            initiator_id, target_id, status = trade
            
            # Check user is a participant
            if user_id != initiator_id and user_id != target_id:
                self.log_security_alert(
                    user_id=user_id,
                    alert_type="trade_impersonation",
                    severity="high",
                    details=f"Attempted to act on trade {trade_id} which they're not a participant in"
                )
                return {"error": "You are not a participant in this trade"}
                
            # Check trade is active
            if status != "active":
                return {"error": "Trade is not active"}
                
            # Validate specific actions
            if action == "add_item" and item_data:
                item_type = item_data.get("type")
                item_id = item_data.get("id")
                
                # Validate ownership
                if not self.validate_transaction(user_id, item_type, item_id, "trade"):
                    return {"error": f"You don't own this {item_type}"}
                    
                # Check if item is locked in another trade
                cursor.execute("""
                SELECT COUNT(*) FROM trade_items
                WHERE item_type = ? AND capture_id = ? AND trade_id != ?
                """, (item_type, item_id, trade_id))
                
                if cursor.fetchone()[0] > 0:
                    return {"error": f"This {item_type} is already in another active trade"}
                    
            return None  # No errors, trade action is valid
            
        finally:
            conn.close()
            
    def validate_battle_action(self, battle_id: int, user_id: str, 
                             action_type: str, action_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate a battle action.
        
        Args:
            battle_id: ID of the battle
            user_id: Discord ID of the user
            action_type: Type of action (move, switch, item, flee)
            action_data: Data specific to the action
            
        Returns:
            Dict or None: Error dict if invalid, None if valid
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check battle exists and user is a participant
            cursor.execute("""
            SELECT b.status, b.current_turn
            FROM battles b
            WHERE b.battle_id = ?
            """, (battle_id,))
            
            battle = cursor.fetchone()
            if not battle:
                return {"error": "Battle not found"}
                
            status, current_turn = battle
            
            # Check battle is active
            if status != "active":
                return {"error": "Battle is not active"}
                
            # Check if it's the user's turn
            if current_turn != user_id:
                self.log_security_alert(
                    user_id=user_id,
                    alert_type="battle_turn_manipulation",
                    severity="medium",
                    details=f"Attempted battle action when it's not their turn"
                )
                return {"error": "It's not your turn"}
                
            # Validate specific actions
            if action_type == "move":
                move_name = action_data.get("move_name")
                
                # Check if the move is valid for their active Veramon
                cursor.execute("""
                SELECT veramon_data
                FROM battle_veramon
                WHERE battle_id = ? AND user_id = ? AND is_active = 1
                """, (battle_id, user_id))
                
                veramon_data = cursor.fetchone()
                if not veramon_data:
                    return {"error": "No active Veramon found"}
                    
                try:
                    veramon = json.loads(veramon_data[0])
                    moves = veramon.get("moves", [])
                    
                    if move_name not in [m.get("name") for m in moves]:
                        self.log_security_alert(
                            user_id=user_id,
                            alert_type="invalid_move_attempt",
                            severity="medium",
                            details=f"Attempted to use move {move_name} that their Veramon doesn't have"
                        )
                        return {"error": "Your Veramon doesn't know this move"}
                except:
                    return {"error": "Invalid Veramon data"}
                    
            elif action_type == "item":
                item_id = action_data.get("item_id")
                
                # Check if user has the item
                cursor.execute("""
                SELECT quantity
                FROM inventory
                WHERE user_id = ? AND item_id = ?
                """, (user_id, item_id))
                
                item = cursor.fetchone()
                if not item or item[0] <= 0:
                    self.log_security_alert(
                        user_id=user_id,
                        alert_type="battle_item_manipulation",
                        severity="medium",
                        details=f"Attempted to use item {item_id} they don't have"
                    )
                    return {"error": "You don't have this item"}
                    
            return None  # No errors, battle action is valid
            
        finally:
            conn.close()
            
    def validate_catch(self, user_id: str, 
                      spawn_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a catch attempt.
        
        Args:
            user_id: Discord ID of the user
            spawn_id: ID of the spawned Veramon
            item_id: ID of the item used to catch
            
        Returns:
            Dict or None: Error dict if invalid, None if valid
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if spawn exists and is for this user
            cursor.execute("""
            SELECT veramon_id, expiry
            FROM active_spawns
            WHERE spawn_id = ? AND user_id = ?
            """, (spawn_id, user_id))
            
            spawn = cursor.fetchone()
            if not spawn:
                self.log_security_alert(
                    user_id=user_id,
                    alert_type="catch_manipulation",
                    severity="high",
                    details=f"Attempted to catch spawn {spawn_id} that doesn't exist or isn't theirs"
                )
                return {"error": "Invalid spawn"}
                
            veramon_id, expiry = spawn
            
            # Check if spawn has expired
            if expiry and datetime.fromisoformat(expiry) < datetime.utcnow():
                return {"error": "This spawn has expired"}
                
            # Check if user has the catching item
            cursor.execute("""
            SELECT quantity
            FROM inventory
            WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id))
            
            item = cursor.fetchone()
            if not item or item[0] <= 0:
                self.log_security_alert(
                    user_id=user_id,
                    alert_type="catch_item_manipulation",
                    severity="medium",
                    details=f"Attempted to use catch item {item_id} they don't have"
                )
                return {"error": "You don't have this item"}
                
            return None  # No errors, catch attempt is valid
            
        finally:
            conn.close()
            
    def lock_item_for_transaction(self, user_id: str, item_type: str, 
                                item_id: Any, lock_type: str, duration_seconds: int = 300) -> bool:
        """
        Lock an item to prevent it from being used in multiple transactions.
        
        Args:
            user_id: Discord ID of the user
            item_type: Type of item (veramon, item, currency)
            item_id: ID of the specific item
            lock_type: Type of lock (trade, battle, etc.)
            duration_seconds: How long to lock the item
            
        Returns:
            bool: True if item was locked successfully
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            expires_at = (datetime.utcnow() + timedelta(seconds=duration_seconds)).isoformat()
            
            # Check if already locked
            cursor.execute("""
            SELECT lock_type FROM transaction_locks
            WHERE item_type = ? AND item_id = ? AND expires_at > ?
            """, (item_type, item_id, datetime.utcnow().isoformat()))
            
            existing_lock = cursor.fetchone()
            if existing_lock and existing_lock[0] != lock_type:
                return False  # Already locked for a different transaction type
                
            # Clear any expired locks
            cursor.execute("""
            DELETE FROM transaction_locks
            WHERE expires_at <= ?
            """, (datetime.utcnow().isoformat(),))
            
            # Create or update lock
            cursor.execute("""
            INSERT OR REPLACE INTO transaction_locks
            (user_id, item_type, item_id, lock_type, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, item_type, item_id, lock_type, 
                  datetime.utcnow().isoformat(), expires_at))
                  
            conn.commit()
            return True
            
        finally:
            conn.close()
            
    def unlock_item(self, item_type: str, item_id: Any, lock_type: str) -> bool:
        """
        Unlock an item to allow it to be used in other transactions.
        
        Args:
            item_type: Type of item (veramon, item, currency)
            item_id: ID of the specific item
            lock_type: Type of lock to remove (trade, battle, etc.)
            
        Returns:
            bool: True if item was unlocked successfully
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            DELETE FROM transaction_locks
            WHERE item_type = ? AND item_id = ? AND lock_type = ?
            """, (item_type, item_id, lock_type))
            
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()


# Initialize tables when the module is loaded
def initialize_security_tables():
    """Initialize required security tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Transaction locks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_locks (
            user_id TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_id TEXT NOT NULL,
            lock_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            PRIMARY KEY (item_type, item_id)
        )
        """)
        
        # Create index on expires_at for performance
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transaction_locks_expiry
        ON transaction_locks (expires_at)
        """)
        
        conn.commit()
    finally:
        conn.close()


# Initialize the tables
initialize_security_tables()

# Create global instance
_security_manager = None

def get_security_manager() -> SecurityManager:
    """
    Get the global security manager instance.
    
    Returns:
        SecurityManager: Global security manager instance
    """
    global _security_manager
    
    if _security_manager is None:
        _security_manager = SecurityManager()
        
    return _security_manager
