"""
Core Trading System for Veramon Reunited

This module contains the core logic for the trading system, separated from the Discord interface.
It defines the Trading class, trade processing, and trade state tracking.
"""

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union, Tuple, Any

from src.db.db import get_connection
from src.utils.config_manager import get_config

class TradeStatus(Enum):
    """Enum for tracking the current status of a trade."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"
    EXPIRED = "expired"

class Trade:
    """
    Core trading class that handles all trade logic independent of the Discord UI.
    
    This class manages:
    - Trade participants and their offered items
    - Trade state tracking and persistence
    - Trade verification and completion
    """
    
    def __init__(self, trade_id: int, initiator_id: str, target_id: str):
        """
        Initialize a new trade.
        
        Args:
            trade_id: Unique identifier for this trade
            initiator_id: User ID of the trade initiator
            target_id: User ID of the trade target
        """
        self.id = trade_id
        self.initiator_id = initiator_id
        self.target_id = target_id
        self.status = TradeStatus.ACTIVE
        self.participants = {
            initiator_id: {"items": [], "confirmed": False},
            target_id: {"items": [], "confirmed": False}
        }
        
        # Set expiry time
        expiry_minutes = get_config("trading", "trade_expiry_minutes", 15)
        self.expiry_time = (datetime.utcnow() + timedelta(minutes=expiry_minutes)).isoformat()
        self.created_at = datetime.utcnow().isoformat()
        self.completed_at = None
        
    def add_item(self, user_id: str, item_id: int, item_type: str = "veramon", details: Dict = None) -> bool:
        """
        Add an item to a user's trade offer.
        
        Args:
            user_id: ID of the user adding the item
            item_id: ID of the item being added
            item_type: Type of item (veramon, currency, etc.)
            details: Additional details about the item
            
        Returns:
            bool: True if item was added successfully
        """
        if user_id not in self.participants:
            return False
            
        if self.status != TradeStatus.ACTIVE:
            return False
            
        # Check if max items limit reached
        max_items = get_config("trading", "max_trade_items", 6)
        if len(self.participants[user_id]["items"]) >= max_items:
            return False
            
        # Reset confirmation when items change
        for participant_id in self.participants:
            self.participants[participant_id]["confirmed"] = False
            
        # Add the item
        self.participants[user_id]["items"].append({
            "id": item_id,
            "type": item_type,
            "details": details or {}
        })
        
        return True
        
    def remove_item(self, user_id: str, item_id: int) -> bool:
        """
        Remove an item from a user's trade offer.
        
        Args:
            user_id: ID of the user removing the item
            item_id: ID of the item to remove
            
        Returns:
            bool: True if item was removed successfully
        """
        if user_id not in self.participants:
            return False
            
        if self.status != TradeStatus.ACTIVE:
            return False
            
        # Find and remove the item
        items = self.participants[user_id]["items"]
        for i, item in enumerate(items):
            if item["id"] == item_id:
                items.pop(i)
                
                # Reset confirmation when items change
                for participant_id in self.participants:
                    self.participants[participant_id]["confirmed"] = False
                    
                return True
                
        return False
        
    def confirm_trade(self, user_id: str) -> bool:
        """
        Confirm the trade for a user.
        
        Args:
            user_id: ID of the user confirming the trade
            
        Returns:
            bool: True if confirmation was successful
        """
        if user_id not in self.participants:
            return False
            
        if self.status != TradeStatus.ACTIVE:
            return False
            
        # Set the confirmation flag
        self.participants[user_id]["confirmed"] = True
        
        return True
        
    def is_ready_for_completion(self) -> bool:
        """
        Check if the trade is ready to be completed.
        
        Returns:
            bool: True if trade is ready for completion
        """
        # Both participants must have confirmed
        for participant_id, participant_data in self.participants.items():
            if not participant_data["confirmed"]:
                return False
                
        # Both participants must have at least one item
        for participant_id, participant_data in self.participants.items():
            if not participant_data["items"]:
                return False
                
        return True
        
    def complete_trade(self) -> bool:
        """
        Complete the trade.
        
        Returns:
            bool: True if trade was completed successfully
        """
        if not self.is_ready_for_completion():
            return False
            
        self.status = TradeStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()
        
        # In a real implementation, this is where we'd update the database
        # to transfer ownership of the items between users
        
        return True
        
    def cancel_trade(self) -> bool:
        """
        Cancel the trade.
        
        Returns:
            bool: True if trade was canceled successfully
        """
        if self.status != TradeStatus.ACTIVE:
            return False
            
        self.status = TradeStatus.CANCELED
        
        return True
        
    def is_expired(self) -> bool:
        """
        Check if the trade has expired.
        
        Returns:
            bool: True if trade has expired
        """
        if self.status != TradeStatus.ACTIVE:
            return False
            
        expiry_time = datetime.fromisoformat(self.expiry_time)
        
        return datetime.utcnow() > expiry_time

    def to_dict(self) -> Dict:
        """
        Convert trade to a dictionary for serialization.
        
        Returns:
            Dict: Dictionary representation of the trade
        """
        return {
            "id": self.id,
            "initiator_id": self.initiator_id,
            "target_id": self.target_id,
            "status": self.status.value,
            "participants": self.participants,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "expiry_time": self.expiry_time
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Trade':
        """
        Create a Trade instance from a dictionary.
        
        Args:
            data: Dictionary representation of a trade
            
        Returns:
            Trade: New Trade instance
        """
        trade = cls(data["id"], data["initiator_id"], data["target_id"])
        trade.status = TradeStatus(data["status"])
        trade.participants = data["participants"]
        trade.created_at = data["created_at"]
        trade.completed_at = data["completed_at"]
        trade.expiry_time = data["expiry_time"]
        
        return trade

# Database interaction functions
async def create_trade(initiator_id: str, target_id: str) -> Optional[int]:
    """
    Create a new trade in the database.
    
    Args:
        initiator_id: User ID of the trade initiator
        target_id: User ID of the trade target
        
    Returns:
        Optional[int]: New trade ID if successful, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert trade record
        cursor.execute("""
            INSERT INTO trades (initiator_id, target_id, status, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (initiator_id, target_id, TradeStatus.ACTIVE.value))
        
        trade_id = cursor.lastrowid
        
        # Insert participants
        cursor.execute("""
            INSERT INTO trade_participants (trade_id, user_id, role, confirmed)
            VALUES (?, ?, 'initiator', 0)
        """, (trade_id, initiator_id))
        
        cursor.execute("""
            INSERT INTO trade_participants (trade_id, user_id, role, confirmed)
            VALUES (?, ?, 'target', 0)
        """, (trade_id, target_id))
        
        conn.commit()
        return trade_id
    except Exception as e:
        print(f"Error creating trade: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

async def get_trade(trade_id: int) -> Optional[Dict]:
    """
    Get a trade by ID.
    
    Args:
        trade_id: ID of the trade to get
        
    Returns:
        Optional[Dict]: Trade data if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get trade data
        cursor.execute("""
            SELECT id, initiator_id, target_id, status, created_at, completed_at
            FROM trades
            WHERE id = ?
        """, (trade_id,))
        
        trade = cursor.fetchone()
        
        if not trade:
            return None
            
        trade_id, initiator_id, target_id, status, created_at, completed_at = trade
        
        # Get participants
        cursor.execute("""
            SELECT user_id, role, confirmed
            FROM trade_participants
            WHERE trade_id = ?
        """, (trade_id,))
        
        participants = {}
        for user_id, role, confirmed in cursor.fetchall():
            participants[user_id] = {
                "role": role,
                "confirmed": bool(confirmed),
                "items": []
            }
            
        # Get items
        cursor.execute("""
            SELECT ti.user_id, ti.item_type, ti.capture_id, ti.details
            FROM trade_items ti
            WHERE ti.trade_id = ?
        """, (trade_id,))
        
        for user_id, item_type, capture_id, details in cursor.fetchall():
            if user_id in participants:
                participants[user_id]["items"].append({
                    "id": capture_id,
                    "type": item_type,
                    "details": json.loads(details) if details else {}
                })
                
        # Calculate expiry time
        expiry_minutes = get_config("trading", "trade_expiry_minutes", 15)
        expiry_time = (datetime.fromisoformat(created_at) + timedelta(minutes=expiry_minutes)).isoformat()
                
        return {
            "id": trade_id,
            "initiator_id": initiator_id,
            "target_id": target_id,
            "status": status,
            "participants": participants,
            "created_at": created_at,
            "completed_at": completed_at,
            "expiry_time": expiry_time
        }
    except Exception as e:
        print(f"Error getting trade: {e}")
        return None
    finally:
        conn.close()
