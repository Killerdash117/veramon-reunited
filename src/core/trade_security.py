"""
Trading System Security for Veramon Reunited

This module provides security checks and validation for the trading system
to prevent scams, item duplication, and other trade-related exploits.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import json
import hashlib

from src.db.db import get_connection
from src.utils.config_manager import get_config
from src.core.security_manager import get_security_manager, ActionType


class TradeSecurity:
    """
    Security implementation for the trading system.
    
    Prevents:
    - Trade manipulation and scams
    - Item duplication
    - Ownership validation
    - Trade flooding and spam
    """
    
    @staticmethod
    def validate_trade_creation(user_id: str, target_id: str) -> Dict[str, Any]:
        """
        Validate a trade creation request to prevent exploits.
        
        Args:
            user_id: ID of the user creating the trade
            target_id: ID of the trade target
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            security_manager = get_security_manager()
            
            # Rate limiting for trade creation
            max_trades = get_config("trading", "max_trades_per_hour", 10)
            if not security_manager.check_rate_limit(
                user_id, ActionType.TRADE_CREATE, max_trades, 3600
            ):
                return {
                    "valid": False,
                    "error": f"You can only start {max_trades} trades per hour. Please wait."
                }
            
            # Verify target user exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (target_id,))
            if cursor.fetchone()[0] == 0:
                return {"valid": False, "error": "Target user not found"}
            
            # Prevent trading with yourself
            if user_id == target_id:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="self_trade_attempt",
                    severity="low",
                    details="Attempted to trade with themselves"
                )
                return {"valid": False, "error": "You cannot trade with yourself"}
            
            # Check for existing active trades between these users
            cursor.execute("""
                SELECT COUNT(*) FROM trades
                WHERE ((initiator_id = ? AND target_id = ?) OR
                       (initiator_id = ? AND target_id = ?))
                AND status = 'active'
            """, (user_id, target_id, target_id, user_id))
            
            if cursor.fetchone()[0] > 0:
                return {
                    "valid": False,
                    "error": "You already have an active trade with this user"
                }
            
            # Check for trade ban flag
            cursor.execute("""
                SELECT COUNT(*) FROM user_flags
                WHERE user_id = ? AND flag_name = 'trade_banned' AND value = 1
                AND (expires_at IS NULL OR expires_at > ?)
            """, (user_id, datetime.utcnow().isoformat()))
            
            if cursor.fetchone()[0] > 0:
                return {
                    "valid": False,
                    "error": "Your trading privileges are currently suspended"
                }
            
            # Check if target user has blocked the initiator
            cursor.execute("""
                SELECT COUNT(*) FROM user_blocks
                WHERE user_id = ? AND blocked_id = ?
            """, (target_id, user_id))
            
            if cursor.fetchone()[0] > 0:
                return {
                    "valid": False,
                    "error": "You cannot trade with this user"
                }
            
            # Check if target user is accepting trades
            cursor.execute("""
                SELECT trade_setting FROM user_settings
                WHERE user_id = ?
            """, (target_id,))
            
            setting = cursor.fetchone()
            if setting and setting[0] == 'off':
                return {
                    "valid": False,
                    "error": "This user is not accepting trades right now"
                }
            
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_trade_action(
        trade_id: int, 
        user_id: str, 
        action: str, 
        item_id: Optional[int] = None,
        item_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a trade action to prevent exploits.
        
        Args:
            trade_id: ID of the trade
            user_id: ID of the user taking the action
            action: Type of action (add, remove, confirm, cancel)
            item_id: Optional ID of the item for add/remove actions
            item_type: Optional type of the item for add actions
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            security_manager = get_security_manager()
            
            # Rate limiting for trade actions
            max_actions = get_config("trading", "max_actions_per_minute", 20)
            if not security_manager.check_rate_limit(
                user_id, ActionType.TRADE_ACTION, max_actions, 60
            ):
                return {
                    "valid": False,
                    "error": "You're acting too quickly. Please slow down."
                }
            
            # Verify trade exists and is active
            cursor.execute("""
                SELECT initiator_id, target_id, status, created_at
                FROM trades
                WHERE id = ?
            """, (trade_id,))
            
            trade = cursor.fetchone()
            if not trade:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="nonexistent_trade",
                    severity="medium",
                    details=f"Attempted action on nonexistent trade: {trade_id}"
                )
                return {"valid": False, "error": "Trade not found"}
            
            initiator_id, target_id, status, created_at = trade
            
            # Verify user is a participant in the trade
            if user_id != initiator_id and user_id != target_id:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="unauthorized_trade_action",
                    severity="high",
                    details=f"Attempted action on trade they're not part of: {trade_id}"
                )
                return {"valid": False, "error": "You are not part of this trade"}
            
            # Check trade status
            if status != 'active':
                return {
                    "valid": False,
                    "error": f"This trade is no longer active (status: {status})"
                }
            
            # Check trade expiry
            expiry_minutes = get_config("trading", "trade_expiry_minutes", 15)
            expiry_time = datetime.fromisoformat(created_at) + timedelta(minutes=expiry_minutes)
            
            if datetime.utcnow() > expiry_time:
                # Mark trade as expired
                cursor.execute("""
                    UPDATE trades
                    SET status = 'expired', completed_at = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), trade_id))
                
                conn.commit()
                return {"valid": False, "error": "This trade has expired"}
            
            # Action-specific validation
            if action == 'add' and item_id is not None and item_type is not None:
                # Verify item ownership based on type
                if item_type == 'veramon':
                    # Check if user owns this Veramon
                    cursor.execute("""
                        SELECT COUNT(*) FROM captures
                        WHERE capture_id = ? AND user_id = ?
                    """, (item_id, user_id))
                    
                    if cursor.fetchone()[0] == 0:
                        security_manager.log_security_alert(
                            user_id=user_id,
                            alert_type="trade_nonowned_veramon",
                            severity="high",
                            details=f"Attempted to trade Veramon they don't own: {item_id}"
                        )
                        return {"valid": False, "error": "You don't own this Veramon"}
                    
                    # Check if Veramon is locked
                    cursor.execute("""
                        SELECT locked FROM captures
                        WHERE capture_id = ?
                    """, (item_id,))
                    
                    locked = cursor.fetchone()[0]
                    if locked:
                        return {"valid": False, "error": "This Veramon is locked and cannot be traded"}
                    
                    # Check if Veramon is in a party
                    cursor.execute("""
                        SELECT COUNT(*) FROM party_members
                        WHERE capture_id = ? AND user_id = ?
                    """, (item_id, user_id))
                    
                    if cursor.fetchone()[0] > 0:
                        return {
                            "valid": False, 
                            "error": "This Veramon is in your party. Remove it first to trade."
                        }
                    
                    # Check if Veramon is already in another active trade
                    cursor.execute("""
                        SELECT COUNT(*) FROM trade_items ti
                        JOIN trades t ON ti.trade_id = t.id
                        WHERE ti.item_type = 'veramon' 
                        AND ti.capture_id = ? 
                        AND t.status = 'active'
                        AND t.id != ?
                    """, (item_id, trade_id))
                    
                    if cursor.fetchone()[0] > 0:
                        return {
                            "valid": False, 
                            "error": "This Veramon is already in another active trade"
                        }
                    
                elif item_type == 'item':
                    # Check if user has enough of this item
                    cursor.execute("""
                        SELECT quantity FROM inventory
                        WHERE user_id = ? AND item_id = ?
                    """, (user_id, item_id))
                    
                    result = cursor.fetchone()
                    if not result or result[0] <= 0:
                        security_manager.log_security_alert(
                            user_id=user_id,
                            alert_type="trade_nonowned_item",
                            severity="medium",
                            details=f"Attempted to trade item they don't have: {item_id}"
                        )
                        return {"valid": False, "error": "You don't have this item"}
                    
                    # Check if item is tradeable
                    cursor.execute("""
                        SELECT tradeable FROM items
                        WHERE item_id = ?
                    """, (item_id,))
                    
                    tradeable = cursor.fetchone()[0]
                    if not tradeable:
                        return {"valid": False, "error": "This item cannot be traded"}
                
                # Check max items per trade
                cursor.execute("""
                    SELECT COUNT(*) FROM trade_items
                    WHERE trade_id = ? AND user_id = ?
                """, (trade_id, user_id))
                
                current_items = cursor.fetchone()[0]
                max_items = get_config("trading", "max_trade_items", 6)
                
                if current_items >= max_items:
                    return {
                        "valid": False, 
                        "error": f"You can only add up to {max_items} items to a trade"
                    }
                
                # Check if user has confirmed previously - must unconfirm
                cursor.execute("""
                    SELECT confirmed FROM trade_participants
                    WHERE trade_id = ? AND user_id = ?
                """, (trade_id, user_id))
                
                confirmed = cursor.fetchone()[0]
                if confirmed:
                    return {
                        "valid": False, 
                        "error": "You have already confirmed the trade. Cancel your confirmation first."
                    }
                
            elif action == 'remove' and item_id is not None:
                # Verify item is in the trade and owned by user
                cursor.execute("""
                    SELECT COUNT(*) FROM trade_items
                    WHERE trade_id = ? AND capture_id = ? AND user_id = ?
                """, (trade_id, item_id, user_id))
                
                if cursor.fetchone()[0] == 0:
                    return {"valid": False, "error": "This item is not in the trade or not yours"}
                
                # Check if user has confirmed previously - must unconfirm
                cursor.execute("""
                    SELECT confirmed FROM trade_participants
                    WHERE trade_id = ? AND user_id = ?
                """, (trade_id, user_id))
                
                confirmed = cursor.fetchone()[0]
                if confirmed:
                    return {
                        "valid": False, 
                        "error": "You have already confirmed the trade. Cancel your confirmation first."
                    }
                
            elif action == 'confirm':
                # Check if user has added any items
                cursor.execute("""
                    SELECT COUNT(*) FROM trade_items
                    WHERE trade_id = ? AND user_id = ?
                """, (trade_id, user_id))
                
                if cursor.fetchone()[0] == 0:
                    return {
                        "valid": False, 
                        "error": "You must add at least one item to the trade before confirming"
                    }
                
                # Check if the other user has added any items
                other_user = target_id if user_id == initiator_id else initiator_id
                
                cursor.execute("""
                    SELECT COUNT(*) FROM trade_items
                    WHERE trade_id = ? AND user_id = ?
                """, (trade_id, other_user))
                
                if cursor.fetchone()[0] == 0:
                    return {
                        "valid": False, 
                        "error": "The other user hasn't added any items yet"
                    }
            
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_trade_completion(trade_id: int) -> Dict[str, Any]:
        """
        Validate that a trade is ready for completion.
        
        Args:
            trade_id: ID of the trade
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check trade status
            cursor.execute("""
                SELECT initiator_id, target_id, status
                FROM trades
                WHERE id = ?
            """, (trade_id,))
            
            trade = cursor.fetchone()
            if not trade:
                return {"valid": False, "error": "Trade not found"}
            
            initiator_id, target_id, status = trade
            
            if status != 'active':
                return {"valid": False, "error": f"This trade is not active (status: {status})"}
            
            # Check if both users have confirmed
            cursor.execute("""
                SELECT user_id, confirmed
                FROM trade_participants
                WHERE trade_id = ?
            """, (trade_id,))
            
            participants = cursor.fetchall()
            confirmed_count = sum(1 for _, confirmed in participants if confirmed)
            
            if confirmed_count < 2:
                return {"valid": False, "error": "Both users must confirm the trade"}
            
            # Verify items still exist and are owned by the participants
            cursor.execute("""
                SELECT user_id, item_type, capture_id
                FROM trade_items
                WHERE trade_id = ?
            """, (trade_id,))
            
            all_items_valid = True
            error_message = None
            
            for user_id, item_type, capture_id in cursor.fetchall():
                if item_type == 'veramon':
                    # Verify Veramon ownership
                    cursor.execute("""
                        SELECT COUNT(*) FROM captures
                        WHERE capture_id = ? AND user_id = ?
                    """, (capture_id, user_id))
                    
                    if cursor.fetchone()[0] == 0:
                        all_items_valid = False
                        error_message = f"One of the Veramon is no longer available"
                        break
                        
                    # Verify Veramon isn't locked
                    cursor.execute("""
                        SELECT locked FROM captures
                        WHERE capture_id = ?
                    """, (capture_id,))
                    
                    if cursor.fetchone()[0]:
                        all_items_valid = False
                        error_message = f"One of the Veramon has been locked"
                        break
                        
                elif item_type == 'item':
                    # Verify item ownership
                    cursor.execute("""
                        SELECT quantity FROM inventory
                        WHERE user_id = ? AND item_id = ?
                    """, (user_id, capture_id))
                    
                    result = cursor.fetchone()
                    if not result or result[0] <= 0:
                        all_items_valid = False
                        error_message = f"One of the items is no longer available"
                        break
            
            if not all_items_valid:
                security_manager = get_security_manager()
                security_manager.log_security_alert(
                    user_id="system",
                    alert_type="trade_item_changed",
                    severity="medium",
                    details=f"Items changed during trade {trade_id}: {error_message}"
                )
                return {"valid": False, "error": error_message}
            
            # Check for recent suspicious activity
            for user_id in [initiator_id, target_id]:
                security_manager = get_security_manager()
                if security_manager.check_suspicious_patterns(user_id):
                    return {
                        "valid": False, 
                        "error": "Trade cancelled due to suspicious activity. Please try again later."
                    }
            
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def log_trade_completion(trade_id: int) -> None:
        """
        Log a completed trade for auditing.
        
        Args:
            trade_id: ID of the completed trade
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get trade details
            cursor.execute("""
                SELECT initiator_id, target_id
                FROM trades
                WHERE id = ?
            """, (trade_id,))
            
            trade = cursor.fetchone()
            if not trade:
                return
            
            initiator_id, target_id = trade
            
            # Get items exchanged
            cursor.execute("""
                SELECT user_id, item_type, capture_id
                FROM trade_items
                WHERE trade_id = ?
            """, (trade_id,))
            
            items = cursor.fetchall()
            
            # Group items by user
            initiator_items = [
                {"type": item_type, "id": capture_id}
                for user_id, item_type, capture_id in items
                if user_id == initiator_id
            ]
            
            target_items = [
                {"type": item_type, "id": capture_id}
                for user_id, item_type, capture_id in items
                if user_id == target_id
            ]
            
            # Log in trade history
            cursor.execute("""
                INSERT INTO trade_history (
                    trade_id, user_a_id, user_b_id,
                    user_a_items, user_b_items,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                initiator_id,
                target_id,
                json.dumps(initiator_items),
                json.dumps(target_items),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            
            # Monitor potential suspicious activity
            security_manager = get_security_manager()
            
            # Check for frequent trading between the same users
            cursor.execute("""
                SELECT COUNT(*) FROM trades
                WHERE ((initiator_id = ? AND target_id = ?) OR
                       (initiator_id = ? AND target_id = ?))
                AND status = 'completed'
                AND completed_at > ?
            """, (
                initiator_id, target_id,
                target_id, initiator_id,
                (datetime.utcnow() - timedelta(hours=3)).isoformat()
            ))
            
            trade_count = cursor.fetchone()[0]
            
            if trade_count > 5:
                security_manager.log_security_alert(
                    user_id=initiator_id,
                    alert_type="frequent_trading",
                    severity="medium",
                    details=f"Frequent trading with {target_id}: {trade_count} trades in 3 hours"
                )
                
                security_manager.log_security_alert(
                    user_id=target_id,
                    alert_type="frequent_trading",
                    severity="medium",
                    details=f"Frequent trading with {initiator_id}: {trade_count} trades in 3 hours"
                )
            
        finally:
            conn.close()
    
    @staticmethod
    def process_trade_completion(trade_id: int) -> Dict[str, Any]:
        """
        Securely process a trade completion, transferring items between users.
        
        Args:
            trade_id: ID of the trade
            
        Returns:
            Dict: Result of the trade processing
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Final validation
            validation = TradeSecurity.validate_trade_completion(trade_id)
            if not validation["valid"]:
                return validation
            
            # Begin transaction
            conn.isolation_level = None
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Get trade participants
                cursor.execute("""
                    SELECT initiator_id, target_id
                    FROM trades
                    WHERE id = ?
                """, (trade_id,))
                
                trade = cursor.fetchone()
                initiator_id, target_id = trade
                
                # Get items to transfer
                cursor.execute("""
                    SELECT user_id, item_type, capture_id
                    FROM trade_items
                    WHERE trade_id = ?
                """, (trade_id,))
                
                items = cursor.fetchall()
                
                # Process transfers
                for user_id, item_type, item_id in items:
                    # Determine recipient
                    recipient_id = target_id if user_id == initiator_id else initiator_id
                    
                    if item_type == 'veramon':
                        # Transfer Veramon
                        cursor.execute("""
                            UPDATE captures
                            SET user_id = ?,
                                obtained_from = ?,
                                obtained_method = 'trade',
                                obtained_date = ?
                            WHERE capture_id = ?
                        """, (
                            recipient_id,
                            f"trade_{user_id}",
                            datetime.utcnow().isoformat(),
                            item_id
                        ))
                        
                        # Remove from any parties
                        cursor.execute("""
                            DELETE FROM party_members
                            WHERE capture_id = ?
                        """, (item_id,))
                        
                    elif item_type == 'item':
                        # Remove from sender inventory
                        cursor.execute("""
                            UPDATE inventory
                            SET quantity = quantity - 1
                            WHERE user_id = ? AND item_id = ?
                        """, (user_id, item_id))
                        
                        # Add to recipient inventory
                        cursor.execute("""
                            INSERT INTO inventory (user_id, item_id, quantity)
                            VALUES (?, ?, 1)
                            ON CONFLICT(user_id, item_id) DO UPDATE
                            SET quantity = quantity + 1
                        """, (recipient_id, item_id))
                
                # Mark trade as completed
                cursor.execute("""
                    UPDATE trades
                    SET status = 'completed', completed_at = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), trade_id))
                
                cursor.execute("COMMIT")
                
                # Log trade completion for auditing
                TradeSecurity.log_trade_completion(trade_id)
                
                return {"valid": True, "message": "Trade completed successfully"}
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                
                # Log error
                security_manager = get_security_manager()
                security_manager.log_security_alert(
                    user_id="system",
                    alert_type="trade_completion_error",
                    severity="high",
                    details=f"Error completing trade {trade_id}: {str(e)}"
                )
                
                return {"valid": False, "error": "An error occurred processing the trade"}
                
        finally:
            conn.close()


# Create the tables needed for trade security
def initialize_trade_security_tables():
    """Initialize database tables for trade security."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Create trade history table for auditing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                user_a_id TEXT NOT NULL,
                user_b_id TEXT NOT NULL,
                user_a_items TEXT NOT NULL,
                user_b_items TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (trade_id) REFERENCES trades (id)
            )
        """)
        
        # Create user blocks table (for blocking trades)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_blocks (
                block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                blocked_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, blocked_id)
            )
        """)
        
        # Create user flags table (for trade bans, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_flags (
                flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                flag_name TEXT NOT NULL,
                value INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                created_by TEXT,
                reason TEXT,
                UNIQUE(user_id, flag_name)
            )
        """)
        
        # Create user settings table (for trade preferences)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                trade_setting TEXT DEFAULT 'on',
                last_updated TEXT
            )
        """)
        
        conn.commit()
    finally:
        conn.close()


# Initialize tables
initialize_trade_security_tables()

# Singleton instance
_trade_security = None

def get_trade_security() -> TradeSecurity:
    """
    Get the global trade security instance.
    
    Returns:
        TradeSecurity: Global trade security instance
    """
    global _trade_security
    
    if _trade_security is None:
        _trade_security = TradeSecurity()
        
    return _trade_security
