"""
Core Faction Economy System for Veramon Reunited

This module contains the core logic for the faction economy system,
including faction leveling, faction shops, and faction-exclusive items.
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union

from src.db.db import get_connection
from src.utils.config_manager import get_config

class FactionEconomy:
    """
    Core faction economy system that handles faction leveling,
    faction shops, and faction-exclusive items and upgrades.
    """
    
    @staticmethod
    def get_faction_level(faction_id: int) -> Tuple[int, int, int]:
        """
        Get the current level of a faction, current XP, and XP required for next level.
        
        Args:
            faction_id: ID of the faction
            
        Returns:
            Tuple containing:
            - int: Current faction level
            - int: Current faction XP
            - int: XP required for next level
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get faction XP
            cursor.execute("""
                SELECT faction_xp, faction_level
                FROM factions
                WHERE faction_id = ?
            """, (faction_id,))
            
            result = cursor.fetchone()
            if not result:
                return 1, 0, 100
                
            faction_xp, faction_level = result
            
            # Calculate XP for next level using the leveling formula
            xp_for_next_level = FactionEconomy.calculate_xp_for_level(faction_level + 1)
            
            return faction_level, faction_xp, xp_for_next_level
        finally:
            conn.close()
    
    @staticmethod
    def calculate_xp_for_level(level: int) -> int:
        """
        Calculate XP required to reach a specific level.
        
        Args:
            level: Target level
            
        Returns:
            int: XP required
        """
        # Get base values from config
        base_xp = get_config("faction", "base_level_xp", 100)
        xp_curve = get_config("faction", "xp_curve_exponent", 2.0)
        
        # Formula: base_xp * (level ^ xp_curve)
        return int(base_xp * (level ** xp_curve))
    
    @staticmethod
    async def add_faction_xp(faction_id: int, xp_amount: int) -> Dict[str, Any]:
        """
        Add XP to a faction and handle level-ups.
        
        Args:
            faction_id: ID of the faction
            xp_amount: Amount of XP to add
            
        Returns:
            Dict: Result including new level, xp, and any level-up information
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current faction data
            cursor.execute("""
                SELECT faction_xp, faction_level, name
                FROM factions
                WHERE faction_id = ?
            """, (faction_id,))
            
            result = cursor.fetchone()
            if not result:
                return {"success": False, "error": "Faction not found"}
                
            current_xp, current_level, faction_name = result
            
            # Apply XP
            new_xp = current_xp + xp_amount
            
            # Check for level up
            new_level = current_level
            level_ups = []
            
            while True:
                xp_for_next_level = FactionEconomy.calculate_xp_for_level(new_level + 1)
                
                if new_xp >= xp_for_next_level:
                    new_level += 1
                    level_ups.append(new_level)
                else:
                    break
            
            # Update faction data
            cursor.execute("""
                UPDATE factions
                SET faction_xp = ?, faction_level = ?
                WHERE faction_id = ?
            """, (new_xp, new_level, faction_id))
            
            # Record level up events if any
            for level in level_ups:
                cursor.execute("""
                    INSERT INTO faction_events (
                        faction_id, event_type, event_data, timestamp
                    ) VALUES (?, 'level_up', ?, datetime('now'))
                """, (faction_id, json.dumps({"new_level": level})))
            
            conn.commit()
            
            return {
                "success": True,
                "faction_id": faction_id,
                "faction_name": faction_name,
                "previous_level": current_level,
                "new_level": new_level,
                "previous_xp": current_xp,
                "new_xp": new_xp,
                "added_xp": xp_amount,
                "leveled_up": len(level_ups) > 0,
                "levels_gained": len(level_ups),
                "new_levels": level_ups
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def get_faction_shop_items(faction_level: int) -> List[Dict[str, Any]]:
        """
        Get all items available in the faction shop for a specific faction level.
        
        Args:
            faction_level: Current level of the faction
            
        Returns:
            List[Dict]: List of available items
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get faction shop items
            cursor.execute("""
                SELECT item_id, name, description, price, 
                       required_level, category, effects, image_url
                FROM faction_shop_items
                WHERE required_level <= ?
            """, (faction_level,))
            
            items = []
            for row in cursor.fetchall():
                item_id, name, description, price, req_level, category, effects, image_url = row
                
                items.append({
                    "item_id": item_id,
                    "name": name,
                    "description": description,
                    "price": price,
                    "required_level": req_level,
                    "category": category,
                    "effects": json.loads(effects) if effects else {},
                    "image_url": image_url,
                    "available": True
                })
            
            # Also get items that are not yet available (for display purposes)
            cursor.execute("""
                SELECT item_id, name, description, price, 
                       required_level, category, image_url
                FROM faction_shop_items
                WHERE required_level > ?
                ORDER BY required_level ASC
                LIMIT 5
            """, (faction_level,))
            
            for row in cursor.fetchall():
                item_id, name, description, price, req_level, category, image_url = row
                
                items.append({
                    "item_id": item_id,
                    "name": name,
                    "description": description,
                    "price": price,
                    "required_level": req_level,
                    "category": category,
                    "image_url": image_url,
                    "available": False,
                    "locked_message": f"Unlocks at Faction Level {req_level}"
                })
            
            return items
        finally:
            conn.close()
    
    @staticmethod
    async def purchase_faction_item(
        user_id: str,
        faction_id: int,
        item_id: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Purchase an item from the faction shop.
        
        Args:
            user_id: ID of the user
            faction_id: ID of the faction
            item_id: ID of the item
            quantity: Quantity to purchase
            
        Returns:
            Dict: Result of the purchase
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Verify user is in faction and has appropriate permissions
            cursor.execute("""
                SELECT fm.rank_id, fr.permissions
                FROM faction_members fm
                JOIN faction_ranks fr ON fm.faction_id = fr.faction_id AND fm.rank_id = fr.rank_id
                WHERE fm.faction_id = ? AND fm.user_id = ?
            """, (faction_id, user_id))
            
            member_data = cursor.fetchone()
            if not member_data:
                return {"success": False, "error": "You are not a member of this faction"}
                
            rank_id, permissions = member_data
            permissions = json.loads(permissions)
            
            # Check if user can make purchases
            if "make_purchases" not in permissions and "manage_faction" not in permissions:
                return {
                    "success": False, 
                    "error": "You don't have permission to make faction purchases"
                }
            
            # Get faction level and treasury
            cursor.execute("""
                SELECT faction_level, treasury
                FROM factions
                WHERE faction_id = ?
            """, (faction_id,))
            
            faction_data = cursor.fetchone()
            if not faction_data:
                return {"success": False, "error": "Faction not found"}
                
            faction_level, treasury = faction_data
            
            # Get item data
            cursor.execute("""
                SELECT name, price, required_level, category, effects
                FROM faction_shop_items
                WHERE item_id = ?
            """, (item_id,))
            
            item_data = cursor.fetchone()
            if not item_data:
                return {"success": False, "error": "Item not found"}
                
            name, price, required_level, category, effects = item_data
            
            # Check level requirement
            if faction_level < required_level:
                return {
                    "success": False, 
                    "error": f"Faction must be level {required_level} to purchase this item"
                }
            
            # Check if treasury has enough funds
            total_price = price * quantity
            if treasury < total_price:
                return {
                    "success": False, 
                    "error": f"Insufficient faction funds. Need {total_price} tokens, have {treasury}"
                }
            
            # Process the purchase
            if category == "consumable":
                # Add to user inventory for consumables
                cursor.execute("""
                    INSERT INTO inventory (user_id, item_id, quantity)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, item_id) DO UPDATE
                    SET quantity = quantity + ?
                """, (user_id, item_id, quantity, quantity))
            elif category == "buff":
                # Apply buff to faction
                effects_dict = json.loads(effects)
                buff_type = effects_dict.get("buff_type", "unknown")
                duration_hours = effects_dict.get("duration", 24)
                
                start_time = datetime.utcnow()
                end_time = start_time + timedelta(hours=duration_hours)
                
                cursor.execute("""
                    INSERT INTO faction_buffs (
                        faction_id, buff_type, start_time, end_time, 
                        activated_by, strength
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    faction_id, 
                    buff_type,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    user_id,
                    effects_dict.get("strength", 1.0)
                ))
            elif category == "upgrade":
                # Apply permanent upgrade to faction
                upgrade_id = effects_dict.get("upgrade_id")
                
                if not upgrade_id:
                    return {"success": False, "error": "Invalid upgrade configuration"}
                
                # Check if upgrade already exists and increment level
                cursor.execute("""
                    INSERT INTO faction_purchased_upgrades (
                        faction_id, upgrade_id, level, last_upgraded_by, last_upgraded_at
                    ) VALUES (?, ?, 1, ?, datetime('now'))
                    ON CONFLICT(faction_id, upgrade_id) DO UPDATE
                    SET level = level + 1,
                        last_upgraded_by = ?,
                        last_upgraded_at = datetime('now')
                """, (faction_id, upgrade_id, user_id, user_id))
            
            # Deduct tokens from treasury
            cursor.execute("""
                UPDATE factions
                SET treasury = treasury - ?
                WHERE faction_id = ?
            """, (total_price, faction_id))
            
            # Record purchase history
            cursor.execute("""
                INSERT INTO faction_purchase_history (
                    faction_id, user_id, item_id, quantity, total_price,
                    purchase_date
                ) VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (faction_id, user_id, item_id, quantity, total_price))
            
            conn.commit()
            
            return {
                "success": True,
                "item_id": item_id,
                "item_name": name,
                "quantity": quantity,
                "total_price": total_price,
                "remaining_treasury": treasury - total_price,
                "category": category
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def get_faction_treasury(faction_id: int) -> int:
        """
        Get the current treasury amount for a faction.
        
        Args:
            faction_id: ID of the faction
            
        Returns:
            int: Current treasury amount
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT treasury
                FROM factions
                WHERE faction_id = ?
            """, (faction_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            conn.close()
    
    @staticmethod
    async def contribute_to_treasury(
        user_id: str,
        faction_id: int,
        amount: int
    ) -> Dict[str, Any]:
        """
        Contribute tokens to the faction treasury.
        
        Args:
            user_id: ID of the user
            faction_id: ID of the faction
            amount: Amount to contribute
            
        Returns:
            Dict: Result of the contribution
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Verify user is in faction
            cursor.execute("""
                SELECT 1
                FROM faction_members
                WHERE faction_id = ? AND user_id = ?
            """, (faction_id, user_id))
            
            if not cursor.fetchone():
                return {"success": False, "error": "You are not a member of this faction"}
            
            # Check if user has enough tokens
            cursor.execute("""
                SELECT tokens
                FROM users
                WHERE user_id = ?
            """, (user_id,))
            
            user_tokens = cursor.fetchone()
            if not user_tokens or user_tokens[0] < amount:
                return {
                    "success": False, 
                    "error": f"Insufficient tokens. You have {user_tokens[0] if user_tokens else 0}, need {amount}"
                }
            
            # Update user tokens
            cursor.execute("""
                UPDATE users
                SET tokens = tokens - ?
                WHERE user_id = ?
            """, (amount, user_id))
            
            # Update faction treasury
            cursor.execute("""
                UPDATE factions
                SET treasury = treasury + ?
                WHERE faction_id = ?
            """, (amount, faction_id))
            
            # Record contribution
            cursor.execute("""
                INSERT INTO faction_contributions (
                    faction_id, user_id, amount, contribution_type, timestamp
                ) VALUES (?, ?, ?, 'tokens', datetime('now'))
            """, (faction_id, user_id, amount))
            
            # Add faction XP based on contribution
            xp_amount = int(amount * get_config("faction", "treasury_contribution_xp_rate", 0.1))
            if xp_amount > 0:
                cursor.execute("""
                    UPDATE factions
                    SET faction_xp = faction_xp + ?
                    WHERE faction_id = ?
                """, (xp_amount, faction_id))
            
            conn.commit()
            
            return {
                "success": True,
                "contribution_amount": amount,
                "new_user_balance": user_tokens[0] - amount if user_tokens else 0,
                "xp_gained": xp_amount
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def get_faction_contribution_leaderboard(faction_id: int) -> List[Dict[str, Any]]:
        """
        Get a leaderboard of member contributions to a faction.
        
        Args:
            faction_id: ID of the faction
            
        Returns:
            List[Dict]: Members sorted by contribution
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT fc.user_id, u.username, SUM(fc.amount) as total_contribution,
                       fm.joined_date, fr.name as rank_name
                FROM faction_contributions fc
                JOIN users u ON fc.user_id = u.user_id
                JOIN faction_members fm ON fc.faction_id = fm.faction_id AND fc.user_id = fm.user_id
                JOIN faction_ranks fr ON fm.faction_id = fr.faction_id AND fm.rank_id = fr.rank_id
                WHERE fc.faction_id = ?
                GROUP BY fc.user_id
                ORDER BY total_contribution DESC
                LIMIT 10
            """, (faction_id,))
            
            leaderboard = []
            for row in cursor.fetchall():
                user_id, username, total, joined_date, rank_name = row
                
                leaderboard.append({
                    "user_id": user_id,
                    "username": username,
                    "total_contribution": total,
                    "rank": rank_name,
                    "joined_date": joined_date
                })
            
            return leaderboard
        finally:
            conn.close()

# Function to get a global instance
_faction_economy = None

def get_faction_economy() -> FactionEconomy:
    """
    Get the global faction economy instance.
    
    Returns:
        FactionEconomy: Global faction economy instance
    """
    global _faction_economy
    
    if _faction_economy is None:
        _faction_economy = FactionEconomy()
        
    return _faction_economy
