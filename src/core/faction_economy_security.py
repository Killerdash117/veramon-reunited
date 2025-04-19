"""
Faction Economy Security Module for Veramon Reunited

This module provides security checks and validation for faction economy operations
to prevent exploits, cheating, and ensure fair gameplay.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

from src.db.db import get_connection
from src.utils.config_manager import get_config


class FactionEconomySecurity:
    """
    Security guards for faction economy operations to prevent exploits and ensure fair gameplay.
    """

    @staticmethod
    def validate_contribution(user_id: str, faction_id: int, amount: int) -> Dict[str, Any]:
        """
        Validate a treasury contribution to prevent exploits.
        
        Security checks:
        1. User must be in the faction
        2. Amount must be positive
        3. User must have sufficient tokens
        4. Prevent rapid contribution spam
        5. Ensure total contributions don't exceed configured limits
        
        Args:
            user_id: ID of the user
            faction_id: ID of the faction
            amount: Amount to contribute
            
        Returns:
            Dict: Validation result with success flag and error message if failed
        """
        if amount <= 0:
            return {"valid": False, "error": "Contribution amount must be positive"}
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check 1: User must be in the faction
            cursor.execute("""
                SELECT COUNT(*) FROM faction_members
                WHERE user_id = ? AND faction_id = ?
            """, (user_id, faction_id))
            
            if cursor.fetchone()[0] == 0:
                return {"valid": False, "error": "User is not a member of this faction"}
            
            # Check 2: User must have sufficient tokens
            cursor.execute("""
                SELECT tokens FROM users
                WHERE user_id = ?
            """, (user_id,))
            
            user_tokens = cursor.fetchone()
            if not user_tokens or user_tokens[0] < amount:
                return {
                    "valid": False, 
                    "error": f"Insufficient tokens. You have {user_tokens[0] if user_tokens else 0}, need {amount}"
                }
            
            # Check 3: Prevent contribution spam
            cooldown_seconds = get_config("faction", "contribution_cooldown_seconds", 5)
            
            cursor.execute("""
                SELECT COUNT(*) FROM faction_contributions
                WHERE user_id = ? AND faction_id = ?
                AND datetime(timestamp) > datetime('now', ?)
            """, (user_id, faction_id, f"-{cooldown_seconds} seconds"))
            
            recent_contributions = cursor.fetchone()[0]
            if recent_contributions > 0:
                return {
                    "valid": False,
                    "error": f"Please wait {cooldown_seconds} seconds between contributions"
                }
                
            # Check 4: Daily contribution limit
            daily_limit = get_config("faction", "daily_contribution_limit", 100000)
            
            cursor.execute("""
                SELECT SUM(amount) FROM faction_contributions
                WHERE user_id = ? AND faction_id = ?
                AND date(timestamp) = date('now')
            """, (user_id, faction_id))
            
            daily_total = cursor.fetchone()[0] or 0
            if daily_total + amount > daily_limit:
                return {
                    "valid": False,
                    "error": f"Daily contribution limit of {daily_limit:,} tokens reached"
                }
                
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_purchase(user_id: str, faction_id: int, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        Validate a faction shop purchase to prevent exploits.
        
        Security checks:
        1. User must be in the faction with proper permissions
        2. Item must exist and be available at faction's level
        3. Faction must have sufficient treasury funds
        4. Quantity must be positive and reasonable
        5. Prevent duplicate purchases of one-time-only items
        6. Enforce cooldowns on item purchases
        
        Args:
            user_id: ID of the user
            faction_id: ID of the faction
            item_id: ID of the item
            quantity: Quantity to purchase
            
        Returns:
            Dict: Validation result with success flag and error message if failed
        """
        if quantity <= 0:
            return {"valid": False, "error": "Quantity must be positive"}
            
        if quantity > 10:
            return {"valid": False, "error": "Maximum purchase quantity is 10"}
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check 1: User must be in the faction with proper permissions
            cursor.execute("""
                SELECT r.can_manage_treasury
                FROM faction_members m
                JOIN faction_ranks r ON m.faction_id = r.faction_id AND m.rank_id = r.rank_id
                WHERE m.user_id = ? AND m.faction_id = ?
            """, (user_id, faction_id))
            
            rank_data = cursor.fetchone()
            if not rank_data:
                return {"valid": False, "error": "User is not a member of this faction"}
                
            can_manage_treasury = rank_data[0]
            if not can_manage_treasury:
                return {"valid": False, "error": "You don't have permission to make purchases"}
                
            # Check 2: Item must exist and be available at faction's level
            cursor.execute("""
                SELECT i.price, i.required_level, i.category, 
                       f.faction_level, f.treasury,
                       i.effects
                FROM faction_shop_items i
                JOIN factions f ON f.faction_id = ?
                WHERE i.item_id = ?
            """, (faction_id, item_id))
            
            item_data = cursor.fetchone()
            if not item_data:
                return {"valid": False, "error": "Item not found"}
                
            price, required_level, category, faction_level, treasury, effects = item_data
            
            if faction_level < required_level:
                return {
                    "valid": False, 
                    "error": f"This item requires faction level {required_level}, but your faction is only level {faction_level}"
                }
                
            # Check 3: Faction must have sufficient treasury funds
            total_price = price * quantity
            
            if treasury < total_price:
                return {
                    "valid": False,
                    "error": f"Insufficient treasury funds. You have {treasury:,} tokens, need {total_price:,} tokens"
                }
                
            # Check 4: Prevent duplicate purchases of one-time-only items
            if "one_time_purchase" in effects:
                cursor.execute("""
                    SELECT COUNT(*) FROM faction_shop_purchases
                    WHERE faction_id = ? AND item_id = ?
                """, (faction_id, item_id))
                
                if cursor.fetchone()[0] > 0:
                    return {"valid": False, "error": "This item can only be purchased once"}
                    
            # Check 5: Enforce cooldowns on item purchases
            if category in ["buff", "consumable"]:
                cooldown_hours = get_config("faction", "buff_purchase_cooldown_hours", 6)
                
                cursor.execute("""
                    SELECT COUNT(*) FROM faction_shop_purchases
                    WHERE faction_id = ? AND item_id = ?
                    AND datetime(timestamp) > datetime('now', ?)
                """, (faction_id, item_id, f"-{cooldown_hours} hours"))
                
                if cursor.fetchone()[0] > 0:
                    return {
                        "valid": False,
                        "error": f"This item can only be purchased once every {cooldown_hours} hours"
                    }
                    
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()

    @staticmethod
    def validate_buff_stacking(faction_id: int, buff_type: str) -> Dict[str, Any]:
        """
        Validate if a faction buff can be activated based on existing buffs.
        
        Security checks:
        1. Prevent stacking multiple of the same buff
        2. Enforce limits on number of active buffs
        3. Prevent power-stacking of similar effect buffs
        
        Args:
            faction_id: ID of the faction
            buff_type: Type of buff being activated
            
        Returns:
            Dict: Validation result with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check 1: Prevent stacking same type buffs
            cursor.execute("""
                SELECT COUNT(*) FROM faction_buffs
                WHERE faction_id = ? AND buff_type = ? AND end_time > datetime('now')
            """, (faction_id, buff_type))
            
            if cursor.fetchone()[0] > 0:
                return {
                    "valid": False,
                    "error": f"A {buff_type} buff is already active. Wait for it to expire before activating another"
                }
                
            # Check 2: Enforce limits on number of active buffs
            max_active_buffs = get_config("faction", "max_active_buffs", 3)
            
            cursor.execute("""
                SELECT COUNT(*) FROM faction_buffs
                WHERE faction_id = ? AND end_time > datetime('now')
            """, (faction_id,))
            
            if cursor.fetchone()[0] >= max_active_buffs:
                return {
                    "valid": False,
                    "error": f"Maximum of {max_active_buffs} active buffs allowed. Wait for existing buffs to expire"
                }
                
            # Check 3: Prevent power-stacking similar effects
            # Group similar buffs that shouldn't stack
            buff_groups = {
                "resource_buffs": ["faction_token_boost", "faction_xp_boost"],
                "rate_buffs": ["faction_catch_boost", "faction_rare_boost", "faction_shiny_boost"],
                "battle_buffs": ["faction_battle_boost", "faction_skill_boost"]
            }
            
            # Find which group this buff belongs to
            target_group = None
            for group, buffs in buff_groups.items():
                if buff_type in buffs:
                    target_group = group
                    break
                    
            if target_group:
                group_buffs = ','.join([f"'{b}'" for b in buff_groups[target_group]])
                cursor.execute(f"""
                    SELECT COUNT(*) FROM faction_buffs
                    WHERE faction_id = ? AND buff_type IN ({group_buffs}) AND end_time > datetime('now')
                """, (faction_id,))
                
                if cursor.fetchone()[0] > 0:
                    return {
                        "valid": False,
                        "error": f"A similar effect buff is already active. Similar buffs cannot be stacked"
                    }
                    
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
            
    @staticmethod
    def validate_faction_level(faction_id: int, claimed_level: int) -> bool:
        """
        Verify that a faction's level is actually what is claimed.
        Prevents client-side manipulation of level data.
        
        Args:
            faction_id: ID of the faction
            claimed_level: The level that's being claimed
            
        Returns:
            bool: True if the claimed level matches the actual level
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT faction_level FROM factions
                WHERE faction_id = ?
            """, (faction_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
                
            actual_level = result[0]
            
            return actual_level == claimed_level
            
        finally:
            conn.close()
            
    @staticmethod
    def log_security_event(faction_id: int, user_id: str, event_type: str, details: str) -> None:
        """
        Log a security-related event for auditing and fraud detection.
        
        Args:
            faction_id: ID of the faction
            user_id: ID of the user involved
            event_type: Type of security event
            details: Additional details about the event
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO faction_security_log (
                    faction_id, user_id, event_type, details, timestamp
                ) VALUES (?, ?, ?, ?, datetime('now'))
            """, (faction_id, user_id, event_type, details))
            
            conn.commit()
            
        except sqlite3.OperationalError:
            # Table might not exist, create it
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faction_security_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faction_id INTEGER,
                    user_id TEXT,
                    event_type TEXT,
                    details TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (faction_id) REFERENCES factions(faction_id)
                )
            """)
            
            # Try again
            cursor.execute("""
                INSERT INTO faction_security_log (
                    faction_id, user_id, event_type, details, timestamp
                ) VALUES (?, ?, ?, ?, datetime('now'))
            """, (faction_id, user_id, event_type, details))
            
            conn.commit()
            
        finally:
            conn.close()
            
    @staticmethod
    def detect_unusual_activity(faction_id: int, user_id: str) -> bool:
        """
        Detect unusual or potentially fraudulent activity for a user.
        
        Args:
            faction_id: ID of the faction
            user_id: ID of the user
            
        Returns:
            bool: True if unusual activity is detected
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check for rapid, high-value contributions in short time
            cursor.execute("""
                SELECT COUNT(*) FROM faction_contributions
                WHERE faction_id = ? AND user_id = ?
                AND amount > 1000
                AND datetime(timestamp) > datetime('now', '-10 minutes')
            """, (faction_id, user_id))
            
            rapid_contributions = cursor.fetchone()[0]
            
            # Check for frequent back-and-forth transfers
            cursor.execute("""
                SELECT COUNT(*) FROM token_transfers
                WHERE (sender_id = ? OR recipient_id = ?)
                AND datetime(timestamp) > datetime('now', '-1 hour')
            """, (user_id, user_id))
            
            frequent_transfers = cursor.fetchone()[0]
            
            # Check for pattern of contribution followed by purchase
            cursor.execute("""
                SELECT COUNT(*) FROM faction_contributions c
                JOIN faction_shop_purchases p
                ON c.faction_id = p.faction_id AND c.user_id = p.user_id
                WHERE c.faction_id = ? AND c.user_id = ?
                AND datetime(p.timestamp) BETWEEN datetime(c.timestamp) AND datetime(c.timestamp, '+5 minutes')
            """, (faction_id, user_id))
            
            contribution_purchase_pattern = cursor.fetchone()[0]
            
            return (rapid_contributions > 5 or frequent_transfers > 10 or contribution_purchase_pattern > 3)
            
        except sqlite3.OperationalError:
            # Tables might not exist or columns not available, assume no unusual activity
            return False
            
        finally:
            conn.close()

# Create global validator
_faction_security = None

def get_faction_security() -> FactionEconomySecurity:
    """
    Get the global FactionEconomySecurity instance.
    
    Returns:
        FactionEconomySecurity: Global security instance
    """
    global _faction_security
    
    if _faction_security is None:
        _faction_security = FactionEconomySecurity()
        
    return _faction_security
