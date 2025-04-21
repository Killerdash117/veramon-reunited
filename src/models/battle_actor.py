"""
Battle Actor implementation

This module implements the Battle logic as an Actor, which allows for better
isolation and potential future scaling across multiple instances.
"""

import asyncio
import logging
import time
import random
import json
from typing import Dict, Any, List, Optional, Tuple, Set

from src.utils.actor_system import Actor, ActorRef, time_actor_operation, get_actor_system, PersistableActor
from src.models.battle import Battle, BattleType
from src.utils.performance_monitor import PerformanceMonitor
from src.utils.battle_metrics import BattleMetrics

logger = logging.getLogger(__name__)

class BattleActor(Actor, PersistableActor):
    """Actor implementation of a Battle."""
    
    def __init__(self, battle_id: int, battle_type: BattleType, host_id: str, 
                 teams: List[Dict[str, Any]] = None, performance_monitor=None,
                 battle_metrics=None):
        Actor.__init__(self)
        PersistableActor.__init__(self)
        
        # Set the actor_id to a predictable value based on the battle_id
        self.actor_id = f"battle_{battle_id}"
        self._persistence_key = self.actor_id  # For persistence
        
        # Create the underlying Battle object
        self.battle = Battle(
            battle_id=battle_id,
            battle_type=battle_type,
            host_id=host_id,
            teams=teams
        )
        
        # Store references to monitoring systems
        self.performance_monitor = performance_monitor or PerformanceMonitor.get_instance()
        self.battle_metrics = battle_metrics or BattleMetrics.get_instance()
        
        # Actors this battle is waiting for responses from
        self._pending_responses: Set[str] = set()
        
        # Last activity timestamp (used for cleanup)
        self.last_activity = time.time()
        
    def get_persistent_state(self) -> Dict[str, Any]:
        """
        Get the state to persist. Returns a JSON-serializable representation 
        of the battle state.
        """
        # Get the battle's serializable state
        battle_state = self.battle.to_dict() if hasattr(self.battle, 'to_dict') else {}
        
        # Add actor-specific state
        state = {
            "battle_id": self.battle.battle_id,
            "battle_type": str(self.battle.battle_type),
            "host_id": self.battle.host_id,
            "battle_state": battle_state,
            "last_activity": self.last_activity
        }
        
        return state
        
    def restore_from_state(self, state: Dict[str, Any]) -> None:
        """
        Restore actor state from persisted data.
        """
        try:
            # Extract basic battle info
            battle_id = state.get("battle_id")
            battle_type_str = state.get("battle_type")
            host_id = state.get("host_id")
            battle_state = state.get("battle_state", {})
            
            # Convert battle_type string to enum if needed
            battle_type = BattleType(battle_type_str) if isinstance(battle_type_str, str) else battle_type_str
            
            # Create a new battle instance
            self.battle = Battle(
                battle_id=battle_id,
                battle_type=battle_type,
                host_id=host_id
            )
            
            # Restore battle state if possible
            if hasattr(self.battle, 'restore_from_dict') and battle_state:
                self.battle.restore_from_dict(battle_state)
            
            # Restore actor-specific state
            self.last_activity = state.get("last_activity", time.time())
            
            logger.info(f"Restored battle actor {self.actor_id} from persisted state")
        except Exception as e:
            logger.exception(f"Error restoring battle actor from state: {e}")
            # Still create a default battle to avoid None references
            if not hasattr(self, 'battle') or self.battle is None:
                battle_id = state.get("battle_id", int(self.actor_id.split('_')[1]) if '_' in self.actor_id else 0)
                battle_type = BattleType.PVP
                host_id = state.get("host_id", "0")
                self.battle = Battle(battle_id=battle_id, battle_type=battle_type, host_id=host_id)
                
    @time_actor_operation("battle_receive")
    async def receive(self, message: Dict[str, Any], sender: Optional[ActorRef] = None) -> Any:
        """Process a message sent to this battle actor."""
        self.last_activity = time.time()
        action = message.get("action")
        
        if not action:
            return {"error": "No action specified in message"}
            
        # Dispatch to the appropriate method based on the action
        if action == "start_battle":
            return await self._handle_start_battle(message)
            
        elif action == "execute_move":
            return await self._handle_execute_move(message)
            
        elif action == "switch_veramon":
            return await self._handle_switch_veramon(message)
            
        elif action == "use_item":
            return await self._handle_use_item(message)
            
        elif action == "end_battle":
            return await self._handle_end_battle(message)
            
        elif action == "get_battle_state":
            return await self._handle_get_battle_state(message)
            
        elif action == "process_turn":
            return await self._handle_process_turn(message)
        
        # Add more actions as needed
        else:
            return {"error": f"Unknown action: {action}"}
    
    @time_actor_operation("battle_start")
    async def _handle_start_battle(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle starting a battle."""
        try:
            # Retrieve any additional parameters
            options = message.get("options", {})
            
            # Record start time for metrics
            start_time = time.time()
            
            # Start the battle
            result = self.battle.start_battle()
            
            # Record metrics
            elapsed = time.time() - start_time
            self.battle_metrics.record_battle_start(
                battle_id=self.battle.battle_id,
                battle_type=str(self.battle.battle_type),
                setup_time=elapsed,
                team_count=len(self.battle.teams),
                veramon_count=sum(len(team.get("veramon", [])) for team in self.battle.teams)
            )
            
            # Mark the actor as dirty for persistence
            self.mark_dirty()
            
            return result
        except Exception as e:
            logger.exception(f"Error starting battle {self.battle.battle_id}")
            return {"error": str(e)}
    
    @time_actor_operation("battle_execute_move")
    async def _handle_execute_move(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle executing a move."""
        try:
            # Extract parameters
            user_id = message.get("user_id")
            move_name = message.get("move_name")
            target_ids = message.get("target_ids", [])
            
            if not user_id or not move_name:
                return {"error": "Missing required parameters"}
                
            # Record start time for metrics
            start_time = time.time()
            
            # Execute the move
            result = self.battle.execute_move(user_id, move_name, target_ids)
            
            # Record metrics
            elapsed = time.time() - start_time
            self.battle_metrics.record_move_execution(
                battle_id=self.battle.battle_id,
                move_name=move_name,
                execution_time=elapsed,
                damage=result.get("damage", 0),
                success=result.get("success", False)
            )
            
            # Mark the actor as dirty for persistence
            self.mark_dirty()
            
            return result
        except Exception as e:
            logger.exception(f"Error executing move in battle {self.battle.battle_id}")
            return {"error": str(e)}
            
    @time_actor_operation("battle_switch_veramon")
    async def _handle_switch_veramon(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle switching Veramon."""
        try:
            # Extract parameters
            user_id = message.get("user_id")
            veramon_id = message.get("veramon_id")
            
            if not user_id or not veramon_id:
                return {"error": "Missing required parameters"}
                
            # Record start time for metrics
            start_time = time.time()
            
            # Switch the Veramon
            result = self.battle.switch_veramon(user_id, veramon_id)
            
            # Record metrics
            elapsed = time.time() - start_time
            self.battle_metrics.record_switch(
                battle_id=self.battle.battle_id,
                execution_time=elapsed,
                success=result.get("success", False)
            )
            
            # Mark the actor as dirty for persistence
            self.mark_dirty()
            
            return result
        except Exception as e:
            logger.exception(f"Error switching Veramon in battle {self.battle.battle_id}")
            return {"error": str(e)}
    
    # Additional handlers for other battle actions
    @time_actor_operation("battle_use_item")
    async def _handle_use_item(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle using an item."""
        try:
            # Extract parameters
            user_id = message.get("user_id")
            item_id = message.get("item_id")
            target_id = message.get("target_id")
            
            if not user_id or not item_id:
                return {"error": "Missing required parameters"}
                
            # Record start time for metrics
            start_time = time.time()
            
            # Use the item
            result = self.battle.use_item(user_id, item_id, target_id)
            
            # Record metrics
            elapsed = time.time() - start_time
            self.battle_metrics.record_item_use(
                battle_id=self.battle.battle_id,
                item_id=item_id,
                execution_time=elapsed,
                success=result.get("success", False)
            )
            
            # Mark the actor as dirty for persistence
            self.mark_dirty()
            
            return result
        except Exception as e:
            logger.exception(f"Error using item in battle {self.battle.battle_id}")
            return {"error": str(e)}
        
    @time_actor_operation("battle_end")
    async def _handle_end_battle(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ending a battle."""
        try:
            # Extract parameters
            reason = message.get("reason", "normal")
            winner_id = message.get("winner_id")
            
            # Record start time for metrics
            start_time = time.time()
            
            # End the battle
            result = self.battle.end_battle(winner_id)
            
            # Record metrics
            elapsed = time.time() - start_time
            self.battle_metrics.record_battle_end(
                battle_id=self.battle.battle_id,
                duration=time.time() - self.battle.start_time if hasattr(self.battle, "start_time") else 0,
                cleanup_time=elapsed,
                reason=reason
            )
            
            # Mark the actor as dirty for persistence
            self.mark_dirty()
            
            return result
        except Exception as e:
            logger.exception(f"Error ending battle {self.battle.battle_id}")
            return {"error": str(e)}
    
    @time_actor_operation("battle_get_state")
    async def _handle_get_battle_state(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle getting the current battle state."""
        try:
            # Extract parameters
            user_id = message.get("user_id")
            include_private = message.get("include_private", False)
            
            # Get the battle state
            return self.battle.get_battle_state(user_id, include_private)
        except Exception as e:
            logger.exception(f"Error getting battle state for {self.battle.battle_id}")
            return {"error": str(e)}
    
    @time_actor_operation("battle_process_turn")
    async def _handle_process_turn(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle processing a turn."""
        try:
            # Record start time for metrics
            start_time = time.time()
            
            # Process the turn
            result = self.battle.process_turn()
            
            # Record metrics
            elapsed = time.time() - start_time
            self.battle_metrics.record_turn_processing(
                battle_id=self.battle.battle_id,
                turn_number=self.battle.current_turn,
                processing_time=elapsed
            )
            
            # Mark the actor as dirty for persistence
            self.mark_dirty()
            
            return result
        except Exception as e:
            logger.exception(f"Error processing turn in battle {self.battle.battle_id}")
            return {"error": str(e)}
