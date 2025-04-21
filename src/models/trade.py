"""
Trading System for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module implements the core trading mechanics for all trade types,
supporting player-to-player trading with safety features.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Set

from src.models.veramon import Veramon
from src.db.db import get_connection

# Set up logging
logger = logging.getLogger("trade")

class TradeStatus(Enum):
    """Status values for trades."""
    PENDING = "pending"       # Initial state when trade is created
    NEGOTIATING = "negotiating"  # Both users adding items
    CONFIRMED = "confirmed"   # One user has confirmed
    COMPLETED = "completed"   # Both users confirmed, trade executed
    CANCELLED = "cancelled"   # Trade was cancelled by a user
    EXPIRED = "expired"       # Trade expired due to inactivity
    FAILED = "failed"         # Trade failed due to error

class ItemType(Enum):
    """Types of items that can be traded."""
    VERAMON = "veramon"     # A captured Veramon
    TOKEN = "token"         # In-game currency
    ITEM = "item"           # Usable item
    BADGE = "badge"         # Collectible badge

class TradeItem:
    """Represents an item being traded."""
    
    def __init__(
        self, 
        item_id: str, 
        owner_id: str, 
        item_type: ItemType = ItemType.VERAMON,
        name: str = None,
        details: Dict[str, Any] = None
    ):
        """
        Initialize a trade item.
        
        Args:
            item_id: Unique identifier for the item
            owner_id: User ID of the item owner
            item_type: Type of item being traded
            name: Display name of the item
            details: Additional item details
        """
        self.item_id = item_id
        self.owner_id = owner_id
        self.item_type = item_type if isinstance(item_type, ItemType) else ItemType(item_type)
        self.name = name
        self.details = details or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.item_id,
            "owner_id": self.owner_id,
            "type": self.item_type.value,
            "name": self.name,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeItem':
        """Create from dictionary."""
        return cls(
            item_id=data.get("id"),
            owner_id=data.get("owner_id"),
            item_type=data.get("type", "veramon"),
            name=data.get("name"),
            details=data.get("details", {})
        )
    
    @classmethod
    def from_veramon(cls, veramon: Veramon, owner_id: str) -> 'TradeItem':
        """Create from a Veramon instance."""
        details = {
            "level": veramon.level,
            "rarity": veramon.rarity,
            "types": veramon.types,
            "is_shiny": veramon.is_shiny
        }
        
        return cls(
            item_id=str(veramon.capture_id),
            owner_id=owner_id,
            item_type=ItemType.VERAMON,
            name=veramon.name,
            details=details
        )

class Trade:
    """Core trade class that handles trade state and logic."""
    
    def __init__(
        self,
        trade_id: int,
        creator_id: str,
        target_id: str,
        status: TradeStatus = TradeStatus.PENDING,
        created_at: Optional[datetime] = None,
        expiry_minutes: int = 30
    ):
        """
        Initialize a trade.
        
        Args:
            trade_id: Unique ID for this trade
            creator_id: User ID of trade creator
            target_id: User ID of trade recipient
            status: Current trade status
            created_at: When the trade was created
            expiry_minutes: Minutes until trade expires
        """
        self.trade_id = trade_id
        self.creator_id = creator_id
        self.target_id = target_id
        self.status = status if isinstance(status, TradeStatus) else TradeStatus(status)
        self.created_at = created_at or datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=expiry_minutes)
        
        # Trade items from each participant
        self.creator_items: List[TradeItem] = []
        self.target_items: List[TradeItem] = []
        
        # Confirmation status
        self.creator_confirmed = False
        self.target_confirmed = False
        
        # Log of trade events
        self.log_entries: List[Dict[str, Any]] = []
    
    def add_item(self, item: TradeItem) -> bool:
        """
        Add an item to the trade.
        
        Args:
            item: Item to add to the trade
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Verify trade is in a valid state
        if self.status not in [TradeStatus.PENDING, TradeStatus.NEGOTIATING]:
            logger.warning(f"Cannot add item to trade {self.trade_id} with status {self.status}")
            return False
        
        # Reset any confirmations when items change
        self.creator_confirmed = False
        self.target_confirmed = False
        
        # Add to appropriate list
        if item.owner_id == self.creator_id:
            self.creator_items.append(item)
            self._add_log_entry(self.creator_id, "add_item", {"item": item.to_dict()})
        elif item.owner_id == self.target_id:
            self.target_items.append(item)
            self._add_log_entry(self.target_id, "add_item", {"item": item.to_dict()})
        else:
            logger.warning(f"User {item.owner_id} cannot add items to trade {self.trade_id}")
            return False
        
        # Update status to negotiating if both users have participated
        if self.creator_items and self.target_items:
            self.status = TradeStatus.NEGOTIATING
        
        return True
    
    def remove_item(self, owner_id: str, item_id: str) -> bool:
        """
        Remove an item from the trade.
        
        Args:
            owner_id: ID of the item owner
            item_id: ID of the item to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Verify trade is in a valid state
        if self.status not in [TradeStatus.PENDING, TradeStatus.NEGOTIATING]:
            logger.warning(f"Cannot remove item from trade {self.trade_id} with status {self.status}")
            return False
        
        # Reset any confirmations when items change
        self.creator_confirmed = False
        self.target_confirmed = False
        
        # Remove from appropriate list
        if owner_id == self.creator_id:
            for i, item in enumerate(self.creator_items):
                if item.item_id == item_id:
                    removed_item = self.creator_items.pop(i)
                    self._add_log_entry(owner_id, "remove_item", {"item": removed_item.to_dict()})
                    
                    # Update status if needed
                    if not self.creator_items and self.status == TradeStatus.NEGOTIATING:
                        self.status = TradeStatus.PENDING
                    
                    return True
        elif owner_id == self.target_id:
            for i, item in enumerate(self.target_items):
                if item.item_id == item_id:
                    removed_item = self.target_items.pop(i)
                    self._add_log_entry(owner_id, "remove_item", {"item": removed_item.to_dict()})
                    
                    # Update status if needed
                    if not self.target_items and self.status == TradeStatus.NEGOTIATING:
                        self.status = TradeStatus.PENDING
                    
                    return True
        
        logger.warning(f"Item {item_id} not found in trade {self.trade_id} for user {owner_id}")
        return False
    
    def confirm_trade(self, user_id: str) -> bool:
        """
        Confirm the trade from one user's perspective.
        
        Args:
            user_id: ID of the user confirming
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Verify trade is in valid state
        if self.status != TradeStatus.NEGOTIATING:
            logger.warning(f"Cannot confirm trade {self.trade_id} with status {self.status}")
            return False
        
        # Verify both sides have items
        if not self.creator_items or not self.target_items:
            logger.warning(f"Cannot confirm trade {self.trade_id} with empty sides")
            return False
        
        # Set confirmation flag
        if user_id == self.creator_id:
            self.creator_confirmed = True
            self._add_log_entry(user_id, "confirm", {"side": "creator"})
        elif user_id == self.target_id:
            self.target_confirmed = True
            self._add_log_entry(user_id, "confirm", {"side": "target"})
        else:
            logger.warning(f"User {user_id} cannot confirm trade {self.trade_id}")
            return False
        
        # Check if both users have confirmed
        if self.creator_confirmed and self.target_confirmed:
            self.status = TradeStatus.COMPLETED
            self._add_log_entry(None, "complete", {"creator_items": len(self.creator_items), "target_items": len(self.target_items)})
        
        return True
    
    def accept_trade(self, user_id: str) -> bool:
        """
        Accept a trade (alias for confirm_trade for API compatibility).
        
        Args:
            user_id: ID of the user accepting the trade
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.confirm_trade(user_id)
        
    def cancel_trade(self, user_id: str, reason: str = None) -> bool:
        """
        Cancel the trade.
        
        Args:
            user_id: ID of the user cancelling
            reason: Optional reason for cancellation
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Only creator, target, or system (None) can cancel
        if user_id not in [self.creator_id, self.target_id, None]:
            logger.warning(f"User {user_id} cannot cancel trade {self.trade_id}")
            return False
        
        # Cannot cancel completed trades
        if self.status == TradeStatus.COMPLETED:
            logger.warning(f"Cannot cancel completed trade {self.trade_id}")
            return False
        
        # Set status to cancelled
        self.status = TradeStatus.CANCELLED
        self._add_log_entry(user_id, "cancel", {"reason": reason})
        
        return True
    
    def check_expiry(self) -> bool:
        """
        Check if the trade has expired.
        
        Returns:
            bool: True if expired, False otherwise
        """
        if datetime.now() > self.expires_at and self.status not in [TradeStatus.COMPLETED, TradeStatus.CANCELLED, TradeStatus.EXPIRED]:
            self.status = TradeStatus.EXPIRED
            self._add_log_entry(None, "expire", {"expires_at": self.expires_at.isoformat()})
            return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the trade.
        
        Returns:
            Dict: Trade status information
        """
        return {
            "trade_id": self.trade_id,
            "status": self.status.value,
            "creator_id": self.creator_id,
            "target_id": self.target_id,
            "creator_items": [item.to_dict() for item in self.creator_items],
            "target_items": [item.to_dict() for item in self.target_items],
            "creator_confirmed": self.creator_confirmed,
            "target_confirmed": self.target_confirmed,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "can_complete": self._can_complete()
        }
    
    def _add_log_entry(self, user_id: Optional[str], action: str, details: Dict[str, Any] = None) -> None:
        """Add an entry to the trade log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {}
        }
        self.log_entries.append(entry)
    
    def _can_complete(self) -> bool:
        """Check if the trade can be completed."""
        # Trade must be in negotiation state
        if self.status != TradeStatus.NEGOTIATING:
            return False
        
        # Both users must have added items
        if not self.creator_items or not self.target_items:
            return False
        
        # Both users must confirm
        if not self.creator_confirmed or not self.target_confirmed:
            return False
        
        return True
    
    def save_to_database(self) -> bool:
        """
        Save the trade to the database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Update trade record
            cursor.execute("""
            INSERT OR REPLACE INTO trades 
            (trade_id, creator_id, target_id, status, created_at, expires_at, creator_confirmed, target_confirmed) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.trade_id,
                self.creator_id,
                self.target_id,
                self.status.value,
                self.created_at.isoformat(),
                self.expires_at.isoformat(),
                self.creator_confirmed,
                self.target_confirmed
            ))
            
            # Clear existing trade items
            cursor.execute("DELETE FROM trade_items WHERE trade_id = ?", (self.trade_id,))
            
            # Add new trade items
            for item in self.creator_items + self.target_items:
                cursor.execute("""
                INSERT INTO trade_items (trade_id, item_id, owner_id, item_type, item_name, item_details)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.trade_id,
                    item.item_id,
                    item.owner_id,
                    item.item_type.value,
                    item.name,
                    json.dumps(item.details)
                ))
            
            # Add log entries
            for entry in self.log_entries:
                cursor.execute("""
                INSERT INTO trade_logs (trade_id, timestamp, user_id, action, details)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    self.trade_id,
                    entry["timestamp"],
                    entry["user_id"],
                    entry["action"],
                    json.dumps(entry["details"])
                ))
            
            # Clear processed log entries
            self.log_entries = []
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving trade {self.trade_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def load_from_database(cls, trade_id: int) -> Optional['Trade']:
        """
        Load a trade from the database.
        
        Args:
            trade_id: ID of the trade to load
            
        Returns:
            Trade: Loaded trade or None if not found
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Load trade data
            cursor.execute("""
            SELECT trade_id, creator_id, target_id, status, created_at, expires_at, creator_confirmed, target_confirmed
            FROM trades
            WHERE trade_id = ?
            """, (trade_id,))
            
            trade_data = cursor.fetchone()
            if not trade_data:
                return None
            
            # Create trade object
            trade = cls(
                trade_id=trade_data[0],
                creator_id=trade_data[1],
                target_id=trade_data[2],
                status=trade_data[3],
                created_at=datetime.fromisoformat(trade_data[4]),
                expiry_minutes=0  # Will be overridden by expires_at
            )
            
            # Set expiry and confirmation
            trade.expires_at = datetime.fromisoformat(trade_data[5])
            trade.creator_confirmed = bool(trade_data[6])
            trade.target_confirmed = bool(trade_data[7])
            
            # Load trade items
            cursor.execute("""
            SELECT item_id, owner_id, item_type, item_name, item_details
            FROM trade_items
            WHERE trade_id = ?
            """, (trade_id,))
            
            for item_data in cursor.fetchall():
                item = TradeItem(
                    item_id=item_data[0],
                    owner_id=item_data[1],
                    item_type=item_data[2],
                    name=item_data[3],
                    details=json.loads(item_data[4]) if item_data[4] else {}
                )
                
                # Add to appropriate list
                if item.owner_id == trade.creator_id:
                    trade.creator_items.append(item)
                elif item.owner_id == trade.target_id:
                    trade.target_items.append(item)
            
            return trade
        except Exception as e:
            logger.error(f"Error loading trade {trade_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def execute_trade(trade_id: int) -> bool:
        """
        Execute a completed trade, transferring ownership.
        
        Args:
            trade_id: ID of the trade to execute
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Load the trade
        trade = Trade.load_from_database(trade_id)
        if not trade or trade.status != TradeStatus.COMPLETED:
            logger.error(f"Cannot execute trade {trade_id}: not completed")
            return False
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Transfer Veramon ownership
            for item in trade.creator_items:
                if item.item_type == ItemType.VERAMON:
                    cursor.execute("""
                    UPDATE captures
                    SET user_id = ?
                    WHERE id = ?
                    """, (trade.target_id, item.item_id))
            
            for item in trade.target_items:
                if item.item_type == ItemType.VERAMON:
                    cursor.execute("""
                    UPDATE captures
                    SET user_id = ?
                    WHERE id = ?
                    """, (trade.creator_id, item.item_id))
            
            # Transfer tokens
            for item in trade.creator_items:
                if item.item_type == ItemType.TOKEN:
                    amount = int(item.details.get("amount", 0))
                    if amount > 0:
                        # Deduct from creator
                        cursor.execute("""
                        UPDATE users
                        SET tokens = tokens - ?
                        WHERE user_id = ?
                        """, (amount, trade.creator_id))
                        
                        # Add to target
                        cursor.execute("""
                        UPDATE users
                        SET tokens = tokens + ?
                        WHERE user_id = ?
                        """, (amount, trade.target_id))
            
            for item in trade.target_items:
                if item.item_type == ItemType.TOKEN:
                    amount = int(item.details.get("amount", 0))
                    if amount > 0:
                        # Deduct from target
                        cursor.execute("""
                        UPDATE users
                        SET tokens = tokens - ?
                        WHERE user_id = ?
                        """, (amount, trade.target_id))
                        
                        # Add to creator
                        cursor.execute("""
                        UPDATE users
                        SET tokens = tokens + ?
                        WHERE user_id = ?
                        """, (amount, trade.creator_id))
            
            # Commit transaction
            cursor.execute("COMMIT")
            
            return True
        except Exception as e:
            # Rollback on error
            if conn:
                cursor.execute("ROLLBACK")
            logger.error(f"Error executing trade {trade_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()
