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
        # Security checks first
        if quantity <= 0:
            return {"success": False, "error": "Quantity must be positive"}
            
        if quantity > 10:
            return {"success": False, "error": "Maximum purchase quantity is 10"}
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get security validator
            from src.core.faction_economy_security import get_faction_security
            security = get_faction_security()
            
            # Check purchase validation
            validation_result = security.validate_purchase(user_id, faction_id, item_id, quantity)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
            
            # Check user has proper permissions
            cursor.execute("""
                SELECT r.can_manage_treasury
                FROM faction_members m
                JOIN faction_ranks r ON m.faction_id = r.faction_id AND m.rank_id = r.rank_id
                WHERE m.user_id = ? AND m.faction_id = ?
            """, (user_id, faction_id))
            
            rank_data = cursor.fetchone()
            if not rank_data:
                return {"success": False, "error": "User is not a member of this faction"}
                
            can_manage_treasury = rank_data[0]
            if not can_manage_treasury:
                return {"success": False, "error": "You don't have permission to make purchases"}
            
            # Check if item exists and is available
            cursor.execute("""
                SELECT i.item_id, i.name, i.price, i.required_level, i.category, i.effects,
                       f.faction_level, f.treasury
                FROM faction_shop_items i
                JOIN factions f ON f.faction_id = ?
                WHERE i.item_id = ?
            """, (faction_id, item_id))
            
            item_data = cursor.fetchone()
            if not item_data:
                return {"success": False, "error": "Item not found"}
                
            item_id, item_name, price, required_level, category, effects_json, faction_level, treasury = item_data
            
            # Check if faction level is high enough
            if faction_level < required_level:
                return {
                    "success": False, 
                    "error": f"This item requires faction level {required_level}, but your faction is only level {faction_level}"
                }
            
            # Calculate total price
            total_price = price * quantity
            
            # Check if faction has enough tokens
            if treasury < total_price:
                return {
                    "success": False, 
                    "error": f"Insufficient treasury funds. You have {treasury:,} tokens, need {total_price:,} tokens"
                }
            
            # Parse effects
            try:
                effects = json.loads(effects_json) if effects_json else {}
            except json.JSONDecodeError:
                effects = {}
            
            # Check if this is a one-time purchase and already purchased
            if effects.get("one_time_purchase"):
                cursor.execute("""
                    SELECT COUNT(*) FROM faction_purchase_history
                    WHERE faction_id = ? AND item_id = ?
                """, (faction_id, item_id))
                
                if cursor.fetchone()[0] > 0:
                    return {"success": False, "error": "This item can only be purchased once"}
            
            # Check cooldown for buffs and consumables
            if category in ["buff", "consumable"]:
                cooldown_hours = get_config("faction", "buff_purchase_cooldown_hours", 6)
                
                cursor.execute("""
                    SELECT COUNT(*) FROM faction_purchase_history
                    WHERE faction_id = ? AND item_id = ?
                    AND datetime(purchase_date) > datetime('now', ?)
                """, (faction_id, item_id, f"-{cooldown_hours} hours"))
                
                if cursor.fetchone()[0] > 0:
                    return {
                        "success": False, 
                        "error": f"This item can only be purchased once every {cooldown_hours} hours"
                    }
            
            # Check buff stacking for buffs
            if category == "buff" and "buff_type" in effects:
                buff_validation = security.validate_buff_stacking(faction_id, effects["buff_type"])
                if not buff_validation["valid"]:
                    return {"success": False, "error": buff_validation["error"]}
            
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
                effects_dict = json.loads(effects_json)
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
                "item_name": item_name,
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
        # Security checks first
        if amount <= 0:
            return {"success": False, "error": "Contribution amount must be positive"}
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Rate limiting check
            from src.core.faction_economy_security import get_faction_security
            security = get_faction_security()
            
            # Check contribution validation
            validation_result = security.validate_contribution(user_id, faction_id, amount)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
            
            # Verify the user is in the faction
            cursor.execute("""
                SELECT COUNT(*) FROM faction_members
                WHERE user_id = ? AND faction_id = ?
            """, (user_id, faction_id))
            
            if cursor.fetchone()[0] == 0:
                return {"success": False, "error": "User is not a member of this faction"}
            
            # Verify the user has enough tokens
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
                
            # Check daily contribution limit
            cursor.execute("""
                SELECT SUM(amount) FROM faction_contributions
                WHERE user_id = ? AND faction_id = ?
                AND date(timestamp) = date('now')
            """, (user_id, faction_id))
            
            daily_total = cursor.fetchone()[0] or 0
            daily_limit = get_config("faction", "daily_contribution_limit", 100000)
            
            if daily_total + amount > daily_limit:
                return {
                    "success": False,
                    "error": f"Daily contribution limit of {daily_limit:,} tokens reached. Try again tomorrow."
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
            
            # Get total contribution amount for this user
            cursor.execute("""
                SELECT SUM(amount) FROM faction_contributions
                WHERE user_id = ? AND faction_id = ?
            """, (user_id, faction_id))
            
            total_contribution = cursor.fetchone()[0] or 0
            total_contribution += amount  # Include the current contribution
            
            # Check for contribution milestone rewards
            contribution_rewards = {
                5000: {"tokens": 100, "xp": 50},
                10000: {"tokens": 250, "xp": 100},
                25000: {"tokens": 500, "xp": 200},
                50000: {"tokens": 1000, "xp": 400},
                100000: {"tokens": 2500, "xp": 1000},
                250000: {"tokens": 6000, "xp": 2500},
                500000: {"tokens": 15000, "xp": 5000},
                1000000: {"tokens": 50000, "xp": 10000}
            }
            
            milestone_reward = None
            for threshold, reward in sorted(contribution_rewards.items()):
                # Check if this contribution pushed them over a milestone
                if total_contribution >= threshold > (total_contribution - amount):
                    milestone_reward = {
                        "threshold": threshold,
                        "tokens": reward["tokens"],
                        "xp": reward["xp"]
                    }
                    
                    # Grant the token reward
                    cursor.execute("""
                        UPDATE users
                        SET tokens = tokens + ?
                        WHERE user_id = ?
                    """, (reward["tokens"], user_id))
                    
                    # Record the milestone in faction history
                    cursor.execute("""
                        INSERT INTO faction_history (
                            faction_id, user_id, event_type, description, timestamp
                        ) VALUES (?, ?, 'contribution_milestone', ?, datetime('now'))
                    """, (faction_id, user_id, f"Reached {threshold:,} tokens contribution milestone"))
                    
                    break
            
            # Check for rank promotions based on contributions
            cursor.execute("""
                SELECT rank_id, autorank_contribution 
                FROM faction_ranks
                WHERE faction_id = ? AND autorank_contribution > 0
                ORDER BY autorank_contribution DESC
            """, (faction_id,))
            
            potential_ranks = cursor.fetchall()
            rank_promotion = None
            
            if potential_ranks:
                cursor.execute("""
                    SELECT rank_id FROM faction_members
                    WHERE user_id = ? AND faction_id = ?
                """, (user_id, faction_id))
                
                current_rank_id = cursor.fetchone()[0]
                
                for rank_id, contribution_requirement in potential_ranks:
                    if total_contribution >= contribution_requirement and rank_id > current_rank_id:
                        # Promote the user to this rank
                        cursor.execute("""
                            UPDATE faction_members
                            SET rank_id = ?
                            WHERE user_id = ? AND faction_id = ?
                        """, (rank_id, user_id, faction_id))
                        
                        # Get rank name
                        cursor.execute("""
                            SELECT name FROM faction_ranks
                            WHERE faction_id = ? AND rank_id = ?
                        """, (faction_id, rank_id))
                        
                        rank_name = cursor.fetchone()[0]
                        
                        rank_promotion = {
                            "rank_id": rank_id,
                            "rank_name": rank_name
                        }
                        
                        # Record promotion in faction history
                        cursor.execute("""
                            INSERT INTO faction_history (
                                faction_id, user_id, event_type, description, timestamp
                            ) VALUES (?, ?, 'rank_promotion', ?, datetime('now'))
                        """, (faction_id, user_id, f"Promoted to {rank_name} due to contributions"))
                        
                        break
            
            # Check for active boost items that affect contribution rates
            cursor.execute("""
                SELECT multiplier FROM faction_shop_purchases
                WHERE faction_id = ? AND item_id = 'faction_donation_booster'
                AND timestamp + duration > datetime('now')
                ORDER BY multiplier DESC
                LIMIT 1
            """, (faction_id,))
            
            donation_boost = cursor.fetchone()
            xp_multiplier = donation_boost[0] if donation_boost else 1.0
            
            if xp_multiplier > 1.0:
                bonus_xp = int(xp_amount * (xp_multiplier - 1.0))
                xp_amount += bonus_xp
                
                # Add the boosted XP
                cursor.execute("""
                    UPDATE factions
                    SET faction_xp = faction_xp + ?
                    WHERE faction_id = ?
                """, (bonus_xp, faction_id))
            
            conn.commit()
            
            return {
                "success": True,
                "contribution_amount": amount,
                "new_user_balance": user_tokens[0] - amount if user_tokens else 0,
                "total_contribution": total_contribution,
                "xp_gained": xp_amount,
                "xp_multiplier": xp_multiplier,
                "milestone_reward": milestone_reward,
                "rank_promotion": rank_promotion
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
