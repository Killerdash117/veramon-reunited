"""
Battle System Security for Veramon Reunited

This module provides security checks and validation for the battle system
to prevent exploits, turn manipulation, and reward farming.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import json
import random
import hashlib

from src.db.db import get_connection
from src.utils.config_manager import get_config
from src.core.security_manager import get_security_manager, ActionType


class BattleSecurity:
    """
    Security implementation for the battle system.
    
    Prevents:
    - Turn manipulation
    - Battle reward farming
    - Battle system exploits
    - Client-side data tampering
    """
    
    @staticmethod
    def validate_battle_creation(user_id: str, battle_type: str, 
                             opponent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a battle creation request to prevent exploits.
        
        Args:
            user_id: ID of the user creating the battle
            battle_type: Type of battle (pvp, pve, etc.)
            opponent_id: Optional ID of the opponent for PvP
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Rate limiting
            security_manager = get_security_manager()
            max_battles = get_config("battle", "max_battles_per_hour", 20)
            
            if not security_manager.check_rate_limit(
                user_id, ActionType.BATTLE_CREATE, max_battles, 3600
            ):
                return {
                    "valid": False,
                    "error": f"You can only start {max_battles} battles per hour. Please wait."
                }
            
            # Check for active battles
            cursor.execute("""
                SELECT COUNT(*) FROM battles
                WHERE (host_id = ? OR 
                      battle_id IN (SELECT battle_id FROM battle_participants WHERE user_id = ?))
                AND status = 'active'
            """, (user_id, user_id))
            
            active_battles = cursor.fetchone()[0]
            max_active = get_config("battle", "max_active_battles", 1)
            
            if active_battles >= max_active:
                return {
                    "valid": False,
                    "error": f"You can only have {max_active} active battle at a time"
                }
            
            # Additional checks for PvP battles
            if battle_type == "pvp" and opponent_id:
                # Check if opponent exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (opponent_id,))
                if cursor.fetchone()[0] == 0:
                    return {"valid": False, "error": "Opponent not found"}
                
                # Prevent battling yourself
                if user_id == opponent_id:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="battle_self",
                        severity="low",
                        details="Attempted to battle themselves"
                    )
                    return {"valid": False, "error": "You cannot battle yourself"}
                
                # Check for active invites
                cursor.execute("""
                    SELECT COUNT(*) FROM battle_invites
                    WHERE (sender_id = ? AND receiver_id = ?) OR
                          (sender_id = ? AND receiver_id = ?)
                    AND expires_at > ?
                """, (user_id, opponent_id, opponent_id, user_id, datetime.utcnow().isoformat()))
                
                if cursor.fetchone()[0] > 0:
                    return {
                        "valid": False,
                        "error": "There is already an active battle invite between you and this player"
                    }
                
                # Check opponent's active battles
                cursor.execute("""
                    SELECT COUNT(*) FROM battles
                    WHERE (host_id = ? OR 
                          battle_id IN (SELECT battle_id FROM battle_participants WHERE user_id = ?))
                    AND status = 'active'
                """, (opponent_id, opponent_id))
                
                if cursor.fetchone()[0] >= max_active:
                    return {
                        "valid": False,
                        "error": "Your opponent is already in an active battle"
                    }
            
            # Check if user has enough battle-ready Veramon
            cursor.execute("""
                SELECT COUNT(*) FROM captures
                WHERE user_id = ? AND health > 0
            """, (user_id,))
            
            available_veramon = cursor.fetchone()[0]
            
            if available_veramon == 0:
                return {
                    "valid": False,
                    "error": "You don't have any Veramon that can battle"
                }
            
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_battle_action(user_id: str, battle_id: int, 
                           action_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a battle action to prevent exploits.
        
        Args:
            user_id: ID of the user taking the action
            battle_id: ID of the battle
            action_type: Type of action (move, switch, item, flee)
            action_data: Data related to the action
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Rate limiting
            security_manager = get_security_manager()
            max_actions = get_config("battle", "max_actions_per_minute", 15)
            
            if not security_manager.check_rate_limit(
                user_id, ActionType.BATTLE_ACTION, max_actions, 60
            ):
                return {
                    "valid": False,
                    "error": "You're acting too quickly. Please slow down."
                }
            
            # Verify battle exists and is active
            cursor.execute("""
                SELECT status, current_turn, battle_type
                FROM battles
                WHERE battle_id = ?
            """, (battle_id,))
            
            battle = cursor.fetchone()
            if not battle:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="nonexistent_battle",
                    severity="medium",
                    details=f"Attempted action on nonexistent battle: {battle_id}"
                )
                return {"valid": False, "error": "Battle not found"}
            
            status, current_turn, battle_type = battle
            
            if status != "active":
                return {"valid": False, "error": "This battle is not active"}
            
            # Check if it's the user's turn
            if current_turn != user_id:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="turn_violation",
                    severity="medium",
                    details=f"Attempted action when it's not their turn"
                )
                return {"valid": False, "error": "It's not your turn"}
            
            # Verify user is a participant
            cursor.execute("""
                SELECT team_id FROM battle_participants
                WHERE battle_id = ? AND user_id = ?
            """, (battle_id, user_id))
            
            if not cursor.fetchone():
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="unauthorized_battle_action",
                    severity="high",
                    details=f"Attempted action in battle they're not part of"
                )
                return {"valid": False, "error": "You are not part of this battle"}
            
            # Action-specific validation
            if action_type == "move":
                move_name = action_data.get("move_name")
                
                # Verify move exists
                cursor.execute("""
                    SELECT COUNT(*) FROM moves
                    WHERE name = ?
                """, (move_name,))
                
                if cursor.fetchone()[0] == 0:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="invalid_move",
                        severity="medium",
                        details=f"Attempted to use non-existent move: {move_name}"
                    )
                    return {"valid": False, "error": "Invalid move"}
                
                # Verify user's active Veramon has this move
                cursor.execute("""
                    SELECT v.moves
                    FROM battle_veramon bv
                    JOIN veramon v ON bv.veramon_id = v.id
                    WHERE bv.battle_id = ? AND bv.user_id = ? AND bv.is_active = 1
                """, (battle_id, user_id))
                
                result = cursor.fetchone()
                if not result:
                    return {"valid": False, "error": "No active Veramon"}
                
                try:
                    moves = json.loads(result[0])
                    if move_name not in [m.get("name") for m in moves]:
                        security_manager.log_security_alert(
                            user_id=user_id,
                            alert_type="unauthorized_move",
                            severity="medium",
                            details=f"Attempted to use move their Veramon doesn't know: {move_name}"
                        )
                        return {"valid": False, "error": "Your Veramon doesn't know this move"}
                except:
                    return {"valid": False, "error": "Invalid move data"}
                
            elif action_type == "switch":
                new_slot = action_data.get("slot")
                
                # Verify slot is valid
                if not isinstance(new_slot, int) or new_slot < 0 or new_slot > 5:
                    return {"valid": False, "error": "Invalid slot"}
                
                # Verify Veramon exists in this slot
                cursor.execute("""
                    SELECT COUNT(*) FROM battle_veramon
                    WHERE battle_id = ? AND user_id = ? AND slot = ? AND health > 0
                """, (battle_id, user_id, new_slot))
                
                if cursor.fetchone()[0] == 0:
                    return {
                        "valid": False, 
                        "error": "No battle-ready Veramon in this slot"
                    }
                
                # Verify not already active
                cursor.execute("""
                    SELECT COUNT(*) FROM battle_veramon
                    WHERE battle_id = ? AND user_id = ? AND slot = ? AND is_active = 1
                """, (battle_id, user_id, new_slot))
                
                if cursor.fetchone()[0] > 0:
                    return {
                        "valid": False, 
                        "error": "This Veramon is already active"
                    }
                
            elif action_type == "item":
                item_id = action_data.get("item_id")
                
                # Verify item exists
                cursor.execute("""
                    SELECT category, usable_in_battle FROM items
                    WHERE item_id = ?
                """, (item_id,))
                
                item = cursor.fetchone()
                if not item:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="invalid_item",
                        severity="medium",
                        details=f"Attempted to use non-existent item: {item_id}"
                    )
                    return {"valid": False, "error": "Invalid item"}
                
                category, usable_in_battle = item
                
                if not usable_in_battle:
                    return {"valid": False, "error": "This item cannot be used in battle"}
                
                # Verify user has this item
                cursor.execute("""
                    SELECT quantity FROM inventory
                    WHERE user_id = ? AND item_id = ?
                """, (user_id, item_id))
                
                result = cursor.fetchone()
                if not result or result[0] <= 0:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="invalid_inventory",
                        severity="medium",
                        details=f"Attempted to use item they don't have: {item_id}"
                    )
                    return {"valid": False, "error": "You don't have this item"}
                
            elif action_type == "flee":
                # Can only flee from PvE battles
                if battle_type != "pve":
                    return {"valid": False, "error": "You can only flee from PvE battles"}
            
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_battle_rewards(battle_id: int, winner_id: str) -> Dict[str, Any]:
        """
        Validate and calculate legitimate battle rewards.
        
        Args:
            battle_id: ID of the battle
            winner_id: ID of the winner
            
        Returns:
            Dict: Reward details with tokens, XP, and any bonuses
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Verify battle exists and has completed
            cursor.execute("""
                SELECT battle_type, turn_number, host_id
                FROM battles
                WHERE battle_id = ? AND status = 'completed' AND winner_id = ?
            """, (battle_id, winner_id))
            
            battle = cursor.fetchone()
            if not battle:
                # Invalid or tampered battle
                security_manager = get_security_manager()
                security_manager.log_security_alert(
                    user_id=winner_id,
                    alert_type="reward_manipulation",
                    severity="high",
                    details=f"Attempted to claim rewards for invalid battle: {battle_id}"
                )
                return {"valid": False, "error": "Invalid battle"}
            
            battle_type, turn_number, host_id = battle
            
            # Check for battle farming (very short battles)
            min_turns = get_config("battle", "min_reward_turns", 2)
            if turn_number < min_turns:
                security_manager = get_security_manager()
                security_manager.log_security_alert(
                    user_id=winner_id,
                    alert_type="battle_farming",
                    severity="medium",
                    details=f"Suspiciously short battle: {turn_number} turns"
                )
                # Reduce rewards for very short battles
                reward_modifier = 0.5
            else:
                reward_modifier = 1.0
            
            # Calculate base rewards
            if battle_type == "pvp":
                base_tokens = get_config("battle", "pvp_token_reward", 200)
                base_xp = get_config("battle", "pvp_xp_reward", 100)
            elif battle_type == "pve":
                # For PvE, get NPC trainer level
                cursor.execute("""
                    SELECT level FROM npc_trainers
                    WHERE trainer_id = (
                        SELECT opponent_id FROM battle_participants
                        WHERE battle_id = ? AND user_id != ? LIMIT 1
                    )
                """, (battle_id, winner_id))
                
                npc_level = cursor.fetchone()
                if npc_level:
                    level_mult = min(2.0, max(0.5, npc_level[0] / 10))
                else:
                    level_mult = 1.0
                
                base_tokens = int(get_config("battle", "pve_token_reward", 100) * level_mult)
                base_xp = int(get_config("battle", "pve_xp_reward", 50) * level_mult)
            else:  # multi
                base_tokens = get_config("battle", "multi_token_reward", 150)
                base_xp = get_config("battle", "multi_xp_reward", 75)
            
            # Apply turn-based bonus (longer battles = more rewards)
            turn_bonus = min(1.5, 1.0 + (turn_number - min_turns) * 0.05)
            
            # Apply any active boosts
            cursor.execute("""
                SELECT boost_type, multiplier FROM active_boosts
                WHERE user_id = ? AND boost_type IN ('battle_rewards', 'token_boost', 'xp_boost')
                AND expires_at > ?
            """, (winner_id, datetime.utcnow().isoformat()))
            
            token_boost = 1.0
            xp_boost = 1.0
            
            for boost_type, multiplier in cursor.fetchall():
                if boost_type in ['battle_rewards', 'token_boost']:
                    token_boost = max(token_boost, multiplier)
                if boost_type in ['battle_rewards', 'xp_boost']:
                    xp_boost = max(xp_boost, multiplier)
            
            # Calculate final rewards
            final_tokens = int(base_tokens * turn_bonus * token_boost * reward_modifier)
            final_xp = int(base_xp * turn_bonus * xp_boost * reward_modifier)
            
            # Cap rewards to prevent abuse
            max_tokens = get_config("battle", "max_battle_tokens", 500)
            max_xp = get_config("battle", "max_battle_xp", 250)
            
            final_tokens = min(final_tokens, max_tokens)
            final_xp = min(final_xp, max_xp)
            
            # Check daily reward limits
            cursor.execute("""
                SELECT SUM(tokens), SUM(xp) FROM battle_rewards
                WHERE user_id = ? AND DATE(timestamp) = DATE('now')
            """, (winner_id,))
            
            daily_rewards = cursor.fetchone()
            daily_tokens = daily_rewards[0] or 0
            daily_xp = daily_rewards[1] or 0
            
            daily_token_limit = get_config("battle", "daily_token_limit", 5000)
            daily_xp_limit = get_config("battle", "daily_xp_limit", 2500)
            
            if daily_tokens + final_tokens > daily_token_limit:
                final_tokens = max(0, daily_token_limit - daily_tokens)
            
            if daily_xp + final_xp > daily_xp_limit:
                final_xp = max(0, daily_xp_limit - daily_xp)
            
            # Record the rewards
            cursor.execute("""
                INSERT INTO battle_rewards (
                    battle_id, user_id, tokens, xp, timestamp
                ) VALUES (?, ?, ?, ?, ?)
            """, (battle_id, winner_id, final_tokens, final_xp, datetime.utcnow().isoformat()))
            
            conn.commit()
            
            return {
                "valid": True,
                "tokens": final_tokens,
                "xp": final_xp,
                "turn_bonus": turn_bonus,
                "boost_multiplier": max(token_boost, xp_boost)
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def check_battle_timeout(battle_id: int) -> bool:
        """
        Check if a battle has timed out due to inactivity.
        
        Args:
            battle_id: ID of the battle
            
        Returns:
            bool: True if battle has timed out
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            timeout_minutes = get_config("battle", "turn_timeout_minutes", 10)
            timeout_threshold = (datetime.utcnow() - timedelta(minutes=timeout_minutes)).isoformat()
            
            cursor.execute("""
                SELECT status, current_turn, updated_at
                FROM battles
                WHERE battle_id = ?
            """, (battle_id,))
            
            battle = cursor.fetchone()
            if not battle:
                return False
            
            status, current_turn, updated_at = battle
            
            if status != "active":
                return False
            
            if updated_at < timeout_threshold:
                # Battle has timed out
                cursor.execute("""
                    UPDATE battles
                    SET status = 'cancelled', updated_at = ?
                    WHERE battle_id = ?
                """, (datetime.utcnow().isoformat(), battle_id))
                
                # Record timeout in battle log
                cursor.execute("""
                    INSERT INTO battle_log (
                        battle_id, log_type, user_id, message, timestamp
                    ) VALUES (?, 'system', ?, ?, ?)
                """, (
                    battle_id, 
                    current_turn, 
                    f"Battle cancelled due to inactivity from {current_turn}",
                    datetime.utcnow().isoformat()
                ))
                
                conn.commit()
                return True
                
            return False
            
        finally:
            conn.close()


# Create the tables needed for battle security
def initialize_battle_security_tables():
    """Initialize database tables for battle security."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Create battle rewards tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battle_rewards (
                reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
                battle_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                xp INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (battle_id) REFERENCES battles (battle_id)
            )
        """)
        
        # Create index for querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_battle_rewards_user_day
            ON battle_rewards (user_id, timestamp)
        """)
        
        conn.commit()
    finally:
        conn.close()


# Initialize tables
initialize_battle_security_tables()

# Singleton instance
_battle_security = None

def get_battle_security() -> BattleSecurity:
    """
    Get the global battle security instance.
    
    Returns:
        BattleSecurity: Global battle security instance
    """
    global _battle_security
    
    if _battle_security is None:
        _battle_security = BattleSecurity()
        
    return _battle_security
