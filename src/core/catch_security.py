"""
Catching System Security for Veramon Reunited

This module provides security checks and validation for the catching system
to prevent exploits, duplication glitches, and spawn manipulation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import json
import random
import hashlib

from src.db.db import get_connection
from src.utils.config_manager import get_config
from src.core.security_manager import get_security_manager


class CatchSecurity:
    """
    Security implementation for the catching system.
    
    Prevents:
    - Spawn manipulation
    - Catch rate manipulation
    - Timer/cooldown bypassing
    - Client-side data tampering
    """
    
    @staticmethod
    def validate_spawn(user_id: str, biome: str, special_area: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a spawn request to prevent exploits.
        
        Args:
            user_id: ID of the user
            biome: Biome to explore
            special_area: Optional special area to explore
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Rate limiting
            security_manager = get_security_manager()
            cooldown_seconds = get_config("exploration", "base_spawn_cooldown", 30)
            max_spawns = get_config("exploration", "max_spawns_per_minute", 3)
            
            if not security_manager.check_rate_limit(
                user_id, "explore", max_spawns, 60
            ):
                return {
                    "valid": False,
                    "error": f"You can only explore {max_spawns} times per minute. Please wait a moment."
                }
            
            # Check if user is on cooldown
            cursor.execute("""
                SELECT MAX(timestamp) FROM exploration_history
                WHERE user_id = ?
            """, (user_id,))
            
            last_spawn = cursor.fetchone()[0]
            
            if last_spawn:
                last_spawn_time = datetime.fromisoformat(last_spawn)
                time_diff = (datetime.utcnow() - last_spawn_time).total_seconds()
                
                if time_diff < cooldown_seconds:
                    wait_time = round(cooldown_seconds - time_diff)
                    return {
                        "valid": False,
                        "error": f"You must wait {wait_time} seconds before exploring again"
                    }
            
            # Verify biome exists
            cursor.execute("""
                SELECT COUNT(*) FROM biomes
                WHERE biome_key = ?
            """, (biome,))
            
            if cursor.fetchone()[0] == 0:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="invalid_biome",
                    severity="medium",
                    details=f"Attempted to explore invalid biome: {biome}"
                )
                return {"valid": False, "error": "Invalid biome"}
            
            # If special area is specified, verify access
            if special_area:
                cursor.execute("""
                    SELECT COUNT(*) FROM user_special_areas
                    WHERE user_id = ? AND area_id = ?
                """, (user_id, special_area))
                
                if cursor.fetchone()[0] == 0:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="unauthorized_area_access",
                        severity="medium",
                        details=f"Attempted to access special area without permission: {special_area}"
                    )
                    return {"valid": False, "error": "You don't have access to this special area"}
            
            # All checks passed
            return {"valid": True}
            
        finally:
            conn.close()
    
    @staticmethod
    def validate_catch_attempt(user_id: str, spawn_id: str, item_id: str) -> Dict[str, Any]:
        """
        Validate a catch attempt to prevent exploits.
        
        Args:
            user_id: ID of the user
            spawn_id: ID of the spawned Veramon
            item_id: ID of the item used for catching
            
        Returns:
            Dict: Validation results with success flag and error message if failed
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Rate limiting
            security_manager = get_security_manager()
            max_catch_attempts = get_config("exploration", "max_catch_attempts_per_minute", 10)
            
            if not security_manager.check_rate_limit(
                user_id, "catch", max_catch_attempts, 60
            ):
                return {
                    "valid": False,
                    "error": f"You can only attempt to catch {max_catch_attempts} times per minute. Please wait a moment."
                }
            
            # Verify user owns the item
            cursor.execute("""
                SELECT quantity FROM inventory
                WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id))
            
            result = cursor.fetchone()
            if not result or result[0] <= 0:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="item_manipulation",
                    severity="medium",
                    details=f"Attempted to use non-existent item: {item_id}"
                )
                return {"valid": False, "error": "You don't have this item"}
            
            # Verify spawn exists and belongs to this user
            cursor.execute("""
                SELECT veramon_id, rarity, expiry FROM active_spawns
                WHERE spawn_id = ? AND user_id = ?
            """, (spawn_id, user_id))
            
            spawn = cursor.fetchone()
            if not spawn:
                security_manager.log_security_alert(
                    user_id=user_id,
                    alert_type="spawn_manipulation",
                    severity="high",
                    details=f"Attempted to catch invalid spawn: {spawn_id}"
                )
                return {"valid": False, "error": "Invalid spawn"}
            
            veramon_id, rarity, expiry = spawn
            
            # Check if spawn has expired
            if expiry:
                expiry_time = datetime.fromisoformat(expiry)
                if expiry_time < datetime.utcnow():
                    return {"valid": False, "error": "This spawn has expired"}
            
            # All checks passed
            return {
                "valid": True, 
                "veramon_id": veramon_id,
                "rarity": rarity
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def generate_catch_seed(user_id: str, spawn_id: str, timestamp: str) -> str:
        """
        Generate a secure catch seed to prevent client-side catch rate manipulation.
        
        Args:
            user_id: ID of the user
            spawn_id: ID of the spawn
            timestamp: ISO timestamp of the catch attempt
            
        Returns:
            str: Secure catch seed
        """
        # Generate a deterministic but unpredictable seed
        input_string = f"{user_id}:{spawn_id}:{timestamp}:{random.randint(1000, 9999)}"
        return hashlib.sha256(input_string.encode()).hexdigest()[:16]
    
    @staticmethod
    def calculate_catch_rate(user_id: str, veramon_id: str, rarity: str, 
                          item_id: str, catch_seed: str) -> float:
        """
        Calculate catch rate in a secure, server-side way.
        
        Args:
            user_id: ID of the user
            veramon_id: ID of the Veramon
            rarity: Rarity of the Veramon
            item_id: ID of the item used
            catch_seed: Secure catch seed
            
        Returns:
            float: Catch rate between 0 and 1
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get item catch rate modifier
            cursor.execute("""
                SELECT effects FROM items
                WHERE item_id = ?
            """, (item_id,))
            
            item_data = cursor.fetchone()
            if not item_data:
                return 0
            
            try:
                effects = json.loads(item_data[0])
                catch_modifier = effects.get("catch_rate_modifier", 1.0)
            except:
                catch_modifier = 1.0
            
            # Get base catch rate for rarity
            rarity_catch_rates = {
                "common": get_config("catch", "common_catch_rate", 0.8),
                "uncommon": get_config("catch", "uncommon_catch_rate", 0.5),
                "rare": get_config("catch", "rare_catch_rate", 0.3),
                "legendary": get_config("catch", "legendary_catch_rate", 0.1),
                "mythic": get_config("catch", "mythic_catch_rate", 0.05)
            }
            
            base_rate = rarity_catch_rates.get(rarity, 0.3)
            
            # Check for catch rate boosts from active boosters
            cursor.execute("""
                SELECT boost_type, multiplier FROM active_boosts
                WHERE user_id = ? AND boost_type = 'catch_rate' AND expires_at > ?
            """, (user_id, datetime.utcnow().isoformat()))
            
            boost = cursor.fetchone()
            boost_multiplier = boost[1] if boost else 1.0
            
            # Check for catch charm
            cursor.execute("""
                SELECT COUNT(*) FROM achievement_rewards
                WHERE user_id = ? AND reward_type = 'catch_charm'
            """, (user_id,))
            
            has_charm = cursor.fetchone()[0] > 0
            charm_bonus = 1.2 if has_charm else 1.0
            
            # Calculate final catch rate
            final_rate = base_rate * catch_modifier * boost_multiplier * charm_bonus
            
            # Cap at 95% to prevent guaranteed catches
            return min(final_rate, 0.95)
            
        finally:
            conn.close()
    
    @staticmethod
    def verify_catch_success(catch_rate: float, catch_seed: str) -> bool:
        """
        Verify catch success using the secure catch seed.
        
        Args:
            catch_rate: Calculated catch rate
            catch_seed: Secure catch seed
            
        Returns:
            bool: Whether the catch was successful
        """
        # Use the catch seed to deterministically decide success
        # This prevents result manipulation by the client
        random.seed(catch_seed)
        roll = random.random()
        return roll <= catch_rate
    
    @staticmethod
    def log_catch_attempt(user_id: str, spawn_id: str, item_id: str, 
                       success: bool, veramon_id: str, rarity: str) -> None:
        """
        Log a catch attempt for auditing.
        
        Args:
            user_id: ID of the user
            spawn_id: ID of the spawned Veramon
            item_id: ID of the item used
            success: Whether the catch was successful
            veramon_id: ID of the Veramon
            rarity: Rarity of the Veramon
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO catch_attempts (
                    user_id, spawn_id, item_id, success, veramon_id, 
                    rarity, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, spawn_id, item_id, 1 if success else 0,
                veramon_id, rarity, datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            
            # Check for suspicious catch patterns
            if success and rarity in ["legendary", "mythic"]:
                security_manager = get_security_manager()
                
                # Count recent legendary/mythic catches
                one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM catch_attempts
                    WHERE user_id = ? AND success = 1 
                    AND rarity IN ('legendary', 'mythic')
                    AND timestamp > ?
                """, (user_id, one_hour_ago))
                
                rare_catch_count = cursor.fetchone()[0]
                
                # Flag suspicious activity
                if rare_catch_count >= 3:
                    security_manager.log_security_alert(
                        user_id=user_id,
                        alert_type="unusual_catch_rate",
                        severity="medium",
                        details=f"Caught {rare_catch_count} legendary/mythic Veramon in the last hour"
                    )
                
        finally:
            conn.close()


# Create the tables needed for catch security
def initialize_catch_security_tables():
    """Initialize database tables for catch security."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Create catch attempts table for auditing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catch_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                spawn_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                veramon_id TEXT NOT NULL,
                rarity TEXT NOT NULL,
                success INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Create index for querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_catch_attempts_user_time
            ON catch_attempts (user_id, timestamp)
        """)
        
        conn.commit()
    finally:
        conn.close()


# Initialize tables
initialize_catch_security_tables()

# Singleton instance
_catch_security = None

def get_catch_security() -> CatchSecurity:
    """
    Get the global catch security instance.
    
    Returns:
        CatchSecurity: Global catch security instance
    """
    global _catch_security
    
    if _catch_security is None:
        _catch_security = CatchSecurity()
        
    return _catch_security
