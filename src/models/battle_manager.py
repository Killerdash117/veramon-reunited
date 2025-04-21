"""
Battle Manager

This module provides a centralized manager for creating and accessing battles
through the actor system. It serves as the main interface between the Discord bot
and the battle actors.
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta

from src.utils.actor_system import ActorRef, get_actor_system
from src.models.battle import BattleType
from src.utils.performance_monitor import PerformanceMonitor
from src.utils.battle_metrics import BattleMetrics
from src.db.db import get_connection

logger = logging.getLogger(__name__)

class BattleManager:
    """Manager for battle actors."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'BattleManager':
        """Get the singleton instance of BattleManager."""
        if cls._instance is None:
            cls._instance = BattleManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the battle manager."""
        self.actor_system = get_actor_system()
        self.performance_monitor = PerformanceMonitor.get_instance()
        self.battle_metrics = BattleMetrics.get_instance()
        self.active_battles: Dict[int, ActorRef] = {}
        self._cleanup_task = None
        self._recovery_complete = False
        
    async def start(self):
        """Start the battle manager."""
        # Register the BattleActor class with the actor system
        from src.models.battle_actor import BattleActor
        self.actor_system.register_actor_type("battle", BattleActor)
        
        # Start the actor system
        await self.actor_system.start()
        
        # Start the cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_battles())
        
        # Recover active battles from database
        await self._recover_active_battles()
        
        logger.info("BattleManager started")
        
    async def stop(self):
        """Stop the battle manager."""
        # Cancel the cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Persist all active battles
        for battle_id, battle_ref in list(self.active_battles.items()):
            try:
                actor_id = battle_ref.actor_id
                actor = self.actor_system.get_actor(actor_id)
                if actor and hasattr(actor, 'persist_state'):
                    await actor.persist_state(force=True)
            except Exception as e:
                logger.exception(f"Error persisting battle {battle_id} during shutdown: {e}")
        
        # Stop the actor system
        await self.actor_system.stop()
        
        logger.info("BattleManager stopped")
        
    async def _recover_active_battles(self):
        """Recover active battles from the database after a restart."""
        try:
            # Get active battles from the database
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get battles that were not completed or cancelled
            cursor.execute("""
                SELECT battle_id, battle_type, host_id, status
                FROM battles
                WHERE status IN ('pending', 'active', 'waiting')
                AND created_at > ?
            """, (datetime.utcnow() - timedelta(days=1)).isoformat())  # Only recover recent battles
            
            active_battles = cursor.fetchall()
            conn.close()
            
            if not active_battles:
                logger.info("No active battles to recover")
                self._recovery_complete = True
                return
                
            logger.info(f"Recovering {len(active_battles)} active battles")
            
            # Restore each battle through the actor system
            for battle_row in active_battles:
                battle_id, battle_type_str, host_id, status = battle_row
                
                try:
                    # Convert battle type string to enum
                    battle_type = BattleType[battle_type_str.upper()] if isinstance(battle_type_str, str) else BattleType.PVP
                    
                    # The actor_id used for persistence
                    actor_id = f"battle_{battle_id}"
                    
                    # Attempt to recover the battle actor
                    battle_ref = await self.actor_system.get_or_create_actor(
                        actor_id=actor_id,
                        actor_type_name="battle",
                        battle_id=battle_id,
                        battle_type=battle_type,
                        host_id=host_id,
                        performance_monitor=self.performance_monitor,
                        battle_metrics=self.battle_metrics
                    )
                    
                    # Store the reference
                    self.active_battles[battle_id] = battle_ref
                    logger.info(f"Recovered battle actor for battle {battle_id}")
                    
                except Exception as e:
                    logger.exception(f"Error recovering battle {battle_id}: {e}")
            
            logger.info(f"Recovered {len(self.active_battles)} battle actors")
            
        except Exception as e:
            logger.exception(f"Error during battle recovery: {e}")
        finally:
            self._recovery_complete = True
        
    async def create_battle(self, battle_id: int, battle_type: BattleType, host_id: str, 
                           teams: List[Dict[str, Any]] = None) -> ActorRef:
        """Create a new battle actor."""
        # Wait for recovery to complete if still in progress
        recovery_wait_count = 0
        while not self._recovery_complete and recovery_wait_count < 20:  # Wait up to 2 seconds
            await asyncio.sleep(0.1)
            recovery_wait_count += 1
        
        # Generate a predictable actor ID based on the battle ID
        actor_id = f"battle_{battle_id}"
        
        # Create or retrieve the battle actor
        battle_ref = await self.actor_system.get_or_create_actor(
            actor_id=actor_id,
            actor_type_name="battle",
            battle_id=battle_id,
            battle_type=battle_type,
            host_id=host_id,
            teams=teams,
            performance_monitor=self.performance_monitor,
            battle_metrics=self.battle_metrics
        )
        
        # Store the reference
        self.active_battles[battle_id] = battle_ref
        
        logger.info(f"Created battle actor for battle {battle_id}")
        return battle_ref
        
    async def get_battle(self, battle_id: int) -> Optional[ActorRef]:
        """Get a reference to an existing battle actor."""
        # Check if we already have a reference
        if battle_id in self.active_battles:
            return self.active_battles[battle_id]
            
        # Wait for recovery to complete if still in progress
        recovery_wait_count = 0
        while not self._recovery_complete and recovery_wait_count < 20:  # Wait up to 2 seconds
            await asyncio.sleep(0.1)
            recovery_wait_count += 1
            
        # Try to find the actor in the system
        actor_id = f"battle_{battle_id}"
        
        try:
            # Try to recover from persistence
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if battle exists and is active
            cursor.execute("""
                SELECT battle_type, host_id, status
                FROM battles
                WHERE battle_id = ? AND status IN ('pending', 'active', 'waiting')
            """, (battle_id,))
            
            battle_row = cursor.fetchone()
            conn.close()
            
            if battle_row:
                battle_type_str, host_id, status = battle_row
                battle_type = BattleType[battle_type_str.upper()] if isinstance(battle_type_str, str) else BattleType.PVP
                
                # Recover the battle actor
                battle_ref = await self.actor_system.get_or_create_actor(
                    actor_id=actor_id,
                    actor_type_name="battle",
                    battle_id=battle_id,
                    battle_type=battle_type,
                    host_id=host_id,
                    performance_monitor=self.performance_monitor,
                    battle_metrics=self.battle_metrics
                )
                
                # Cache the reference
                self.active_battles[battle_id] = battle_ref
                return battle_ref
        except Exception as e:
            logger.exception(f"Error trying to recover battle {battle_id}: {e}")
            
        return None
        
    async def end_battle(self, battle_id: int, reason: str = "normal", winner_id: str = None) -> Dict[str, Any]:
        """End a battle and clean up resources."""
        battle_ref = await self.get_battle(battle_id)
        if not battle_ref:
            return {"error": f"Battle {battle_id} not found"}
            
        try:
            # Record end time
            end_time = time.time()
            
            # Send the end battle message
            result = await battle_ref.ask({
                "action": "end_battle",
                "reason": reason,
                "winner_id": winner_id
            })
            
            # Persist the final state
            actor = self.actor_system.get_actor(battle_ref.actor_id)
            if actor and hasattr(actor, 'persist_state'):
                await actor.persist_state(force=True)
                
            # Update database
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE battles
                SET status = 'completed', updated_at = ?
                WHERE battle_id = ?
            """, (datetime.utcnow().isoformat(), battle_id))
            
            conn.commit()
            conn.close()
            
            # Remove from active battles
            if battle_id in self.active_battles:
                del self.active_battles[battle_id]
                
            logger.info(f"Ended battle {battle_id}")
            return result
        except Exception as e:
            logger.exception(f"Error ending battle {battle_id}: {e}")
            return {"error": str(e)}
        
    async def _cleanup_inactive_battles(self):
        """Periodically clean up inactive battles."""
        CLEANUP_INTERVAL = 300  # 5 minutes
        INACTIVITY_THRESHOLD = 3600  # 1 hour
        
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL)
                
                # Wait for recovery to complete before cleanup
                if not self._recovery_complete:
                    continue
                    
                current_time = time.time()
                battles_to_remove = []
                
                # Check each active battle
                for battle_id, battle_ref in list(self.active_battles.items()):
                    actor = self.actor_system.get_actor(battle_ref.actor_id)
                    if not actor:
                        battles_to_remove.append(battle_id)
                        continue
                        
                    # Check if the battle has been inactive
                    if hasattr(actor, "last_activity") and current_time - actor.last_activity > INACTIVITY_THRESHOLD:
                        logger.info(f"Cleaning up inactive battle {battle_id}")
                        await self.end_battle(battle_id, reason="timeout")
                        battles_to_remove.append(battle_id)
                        
                # Remove cleaned up battles
                for battle_id in battles_to_remove:
                    if battle_id in self.active_battles:
                        del self.active_battles[battle_id]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in battle cleanup task")
