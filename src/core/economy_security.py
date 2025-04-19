"""
Economy System Security for Veramon Reunited

This module provides security checks and validation for the economy system
to prevent token duplication, shop exploits, and economy manipulation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import json

from src.db.db import get_connection
from src.utils.config_manager import get_config
from src.core.security_manager import get_security_manager, ActionType


class EconomySecurity:
    """
    Security implementation for the economy system.
    
    Prevents:
    - Token duplication and manipulation
    - Shop exploits and price manipulation
    - Economy system abuse
    """
    
    @staticmethod
    def validate_token_transaction(
        user_id: str, 
        amount: int, 
        transaction_type: str,
        recipient_id: Optional[str] = None,
        item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a token transaction to prevent exploitation.
        
        Args:
            user_id: ID of the user
            amount: Amount of tokens
            transaction_type: Type of transaction (add, remove, transfer)
            recipient_id: Optional ID of recipient for transfers
            item_id: Optional ID of related item
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            security_manager = get_security_manager()
            
            # Rate limiting
            if transaction_type == 'transfer':
                max_transfers = get_config("economy", "max_transfers_per_day", 20)
                
                if not security_manager.check_rate_limit(
                    user_id, ActionType.TOKEN_TRANSFER, max_transfers, 86400
                ):
                    return {
                        "valid": False,
                        "error": f"You can only perform {max_transfers} token transfers per day."
                    }
            
            # Validate amount
            if amount <= 0:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="invalid_token_amount",
                    severity="medium",
                    details=f"Attempted transaction with invalid amount: {amount}"
                )
                return {"valid": False, "error": "Invalid token amount"}
            
            # Check if user exists
            cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {"valid": False, "error": "User not found"}
            
            user_tokens = user[0]
            
            # For 'remove' or 'transfer', check if user has enough tokens
            if transaction_type in ['remove', 'transfer']:
                if user_tokens < amount:
                    return {"valid": False, "error": "You don't have enough tokens"}
            
            # For 'add', validate the maximum allowed tokens
            if transaction_type == 'add':
                daily_gain_limit = get_config("economy", "max_daily_token_gain", 10000)
                
                # Check daily gains
                cursor.execute("""
                    SELECT SUM(amount) FROM token_transactions
                    WHERE user_id = ? AND type = 'add' 
                    AND timestamp > ?
                """, (
                    user_id, 
                    (datetime.utcnow() - timedelta(days=1)).isoformat()
                ))
                
                daily_gains = cursor.fetchone()[0] or 0
                
                if daily_gains + amount > daily_gain_limit:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="daily_token_limit",
                        severity="medium",
                        details=f"Exceeded daily token gain limit: {daily_gains + amount}/{daily_gain_limit}"
                    )
                    return {
                        "valid": False, 
                        "error": f"You have reached the daily limit for gaining tokens ({daily_gain_limit})"
                    }
                
                # Check for token balance ceiling
                max_tokens = get_config("economy", "max_token_balance", 1000000)
                
                if user_tokens + amount > max_tokens:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="token_balance_ceiling",
                        severity="low",
                        details=f"Reached token balance ceiling: {user_tokens + amount}/{max_tokens}"
                    )
                    return {
                        "valid": False,
                        "error": f"Your token balance cannot exceed {max_tokens}"
                    }
            
            # For 'transfer', validate recipient
            if transaction_type == 'transfer' and recipient_id:
                # Check if recipient exists
                cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (recipient_id,))
                if not cursor.fetchone():
                    return {"valid": False, "error": "Recipient not found"}
                
                # Prevent transfer to self
                if user_id == recipient_id:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="self_transfer",
                        severity="low",
                        details="Attempted to transfer tokens to themselves"
                    )
                    return {"valid": False, "error": "You cannot transfer tokens to yourself"}
                
                # Check for suspicious transfer patterns
                # Large transfers
                if amount > 10000:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="large_token_transfer",
                        severity="medium",
                        details=f"Large token transfer of {amount} to {recipient_id}"
                    )
                
                # Frequent transfers to same recipient
                cursor.execute("""
                    SELECT COUNT(*) FROM token_transactions
                    WHERE user_id = ? AND recipient_id = ? AND type = 'transfer' 
                    AND timestamp > ?
                """, (
                    user_id,
                    recipient_id,
                    (datetime.utcnow() - timedelta(hours=24)).isoformat()
                ))
                
                transfer_count = cursor.fetchone()[0]
                
                if transfer_count > 5:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="frequent_transfers",
                        severity="medium",
                        details=f"Frequent transfers to {recipient_id}: {transfer_count} in 24 hours"
                    )
            
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_shop_purchase(
        user_id: str, 
        item_id: str, 
        quantity: int,
        shop_type: str = "main"
    ) -> Dict[str, Any]:
        """
        Validate a shop purchase to prevent exploits.
        
        Args:
            user_id: ID of the user
            item_id: ID of the item
            quantity: Quantity to purchase
            shop_type: Type of shop (main, faction, event)
            
        Returns:
            Dict: Validation results with success flag and related data if successful
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            security_manager = get_security_manager()
            
            # Rate limiting
            max_purchases = get_config("economy", "max_purchases_per_hour", 30)
            
            if not security_manager.check_rate_limit(
                user_id, ActionType.SHOP_PURCHASE, max_purchases, 3600
            ):
                return {
                    "valid": False,
                    "error": f"You can only make {max_purchases} shop purchases per hour."
                }
            
            # Validate quantity
            if quantity <= 0:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="invalid_purchase_quantity",
                    severity="medium",
                    details=f"Attempted purchase with invalid quantity: {quantity}"
                )
                return {"valid": False, "error": "Invalid quantity"}
            
            # Check if user exists
            cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {"valid": False, "error": "User not found"}
            
            user_tokens = user[0]
            
            # Check if item exists and get price
            if shop_type == "main":
                cursor.execute("""
                    SELECT price, available, purchase_limit, category, name
                    FROM items
                    WHERE item_id = ?
                """, (item_id,))
            elif shop_type == "faction":
                cursor.execute("""
                    SELECT price, purchase_limit, category, name
                    FROM faction_shop_items
                    WHERE item_id = ?
                """, (item_id,))
                
                if not cursor.fetchone():
                    return {"valid": False, "error": "Item not found in faction shop"}
                
                # Get user faction
                cursor.execute("""
                    SELECT faction_id FROM faction_members
                    WHERE user_id = ?
                """, (user_id,))
                
                faction = cursor.fetchone()
                if not faction:
                    return {"valid": False, "error": "You are not in a faction"}
                
                # Re-query with faction info
                cursor.execute("""
                    SELECT price, purchase_limit, category, name
                    FROM faction_shop_items
                    WHERE item_id = ?
                """, (item_id,))
            else:  # event
                cursor.execute("""
                    SELECT price, available, purchase_limit, category, name
                    FROM event_shop_items
                    WHERE item_id = ?
                """, (item_id,))
            
            item = cursor.fetchone()
            if not item:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="nonexistent_item_purchase",
                    severity="medium",
                    details=f"Attempted to purchase non-existent item: {item_id}"
                )
                return {"valid": False, "error": "Item not found"}
            
            # Extract item details
            if shop_type == "main":
                price, available, purchase_limit, category, name = item
                if not available:
                    return {"valid": False, "error": "This item is not available for purchase"}
            else:
                price, purchase_limit, category, name = item
            
            total_price = price * quantity
            
            # Check if user has enough tokens
            if user_tokens < total_price:
                return {"valid": False, "error": "You don't have enough tokens"}
            
            # Check purchase limits if applicable
            if purchase_limit > 0:
                # Calculate time period (daily, weekly, or one-time)
                if category == "one-time":
                    time_period = None  # No time restriction
                elif category == "weekly":
                    time_period = (datetime.utcnow() - timedelta(days=7)).isoformat()
                else:  # daily by default
                    time_period = (datetime.utcnow() - timedelta(days=1)).isoformat()
                
                # Check previous purchases
                if time_period:
                    cursor.execute("""
                        SELECT SUM(quantity) FROM purchase_history
                        WHERE user_id = ? AND item_id = ? AND timestamp > ?
                    """, (user_id, item_id, time_period))
                else:
                    cursor.execute("""
                        SELECT SUM(quantity) FROM purchase_history
                        WHERE user_id = ? AND item_id = ?
                    """, (user_id, item_id))
                
                purchased = cursor.fetchone()[0] or 0
                
                if purchased + quantity > purchase_limit:
                    remaining = max(0, purchase_limit - purchased)
                    return {
                        "valid": False,
                        "error": f"Purchase limit reached for this item. You can purchase {remaining} more."
                    }
            
            # All checks passed
            return {
                "valid": True,
                "price": total_price,
                "item_name": name,
                "category": category
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_crafting(
        user_id: str, 
        recipe_id: str, 
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Validate a crafting attempt to prevent exploits.
        
        Args:
            user_id: ID of the user
            recipe_id: ID of the recipe
            quantity: Quantity to craft
            
        Returns:
            Dict: Validation results with success flag and related data if successful
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            security_manager = get_security_manager()
            
            # Rate limiting
            max_crafts = get_config("economy", "max_crafts_per_hour", 20)
            
            if not security_manager.check_rate_limit(
                user_id, ActionType.CRAFTING, max_crafts, 3600
            ):
                return {
                    "valid": False,
                    "error": f"You can only perform {max_crafts} crafting operations per hour."
                }
            
            # Validate quantity
            if quantity <= 0:
                return {"valid": False, "error": "Invalid quantity"}
            
            # Get recipe details
            cursor.execute("""
                SELECT recipe_name, ingredients, result_item_id, result_quantity
                FROM crafting_recipes
                WHERE recipe_id = ?
            """, (recipe_id,))
            
            recipe = cursor.fetchone()
            if not recipe:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="nonexistent_recipe",
                    severity="medium",
                    details=f"Attempted to use non-existent recipe: {recipe_id}"
                )
                return {"valid": False, "error": "Recipe not found"}
            
            recipe_name, ingredients_json, result_item_id, result_quantity = recipe
            
            try:
                ingredients = json.loads(ingredients_json)
            except:
                return {"valid": False, "error": "Invalid recipe data"}
            
            # Check if user has the required ingredients
            for ingredient in ingredients:
                item_id = ingredient.get("item_id")
                required = ingredient.get("quantity", 1) * quantity
                
                cursor.execute("""
                    SELECT quantity FROM inventory
                    WHERE user_id = ? AND item_id = ?
                """, (user_id, item_id))
                
                result = cursor.fetchone()
                available = result[0] if result else 0
                
                if available < required:
                    return {
                        "valid": False,
                        "error": f"You don't have enough {item_id} (need {required}, have {available})"
                    }
            
            # Check inventory space (preventing excessive item accumulation)
            cursor.execute("""
                SELECT COUNT(*) FROM inventory
                WHERE user_id = ?
            """, (user_id,))
            
            inventory_count = cursor.fetchone()[0]
            max_items = get_config("economy", "max_inventory_items", 1000)
            
            # Check if result item already exists
            cursor.execute("""
                SELECT quantity FROM inventory
                WHERE user_id = ? AND item_id = ?
            """, (user_id, result_item_id))
            
            has_item = cursor.fetchone() is not None
            
            if not has_item and inventory_count >= max_items:
                return {
                    "valid": False,
                    "error": f"Your inventory is full (max {max_items} unique items)"
                }
            
            # All checks passed
            return {
                "valid": True,
                "recipe_name": recipe_name,
                "result_item_id": result_item_id,
                "result_quantity": result_quantity * quantity,
                "ingredients": ingredients
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def log_transaction(
        user_id: str,
        transaction_type: str,
        amount: int,
        item_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an economy transaction for auditing.
        
        Args:
            user_id: ID of the user
            transaction_type: Type of transaction
            amount: Amount of tokens
            item_id: Optional ID of related item
            recipient_id: Optional ID of recipient
            details: Optional additional details
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO token_transactions (
                    user_id, type, amount, recipient_id, 
                    item_id, details, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                transaction_type,
                amount,
                recipient_id,
                item_id,
                json.dumps(details) if details else None,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            
        finally:
            conn.close()


# Create the tables needed for economy security
def initialize_economy_security_tables():
    """Initialize database tables for economy security."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Create token transactions table for auditing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                recipient_id TEXT,
                item_id TEXT,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Create purchase history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_history (
                purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                shop_type TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Create indices for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_transactions_user_type
            ON token_transactions (user_id, type, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_purchase_history_user_item
            ON purchase_history (user_id, item_id, timestamp)
        """)
        
        conn.commit()
    finally:
        conn.close()


# Initialize tables
initialize_economy_security_tables()

# Singleton instance
_economy_security = None

def get_economy_security() -> EconomySecurity:
    """
    Get the global economy security instance.
    
    Returns:
        EconomySecurity: Global economy security instance
    """
    global _economy_security
    
    if _economy_security is None:
        _economy_security = EconomySecurity()
        
    return _economy_security
