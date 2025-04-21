"""
Battle System for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module implements the core battle mechanics for all battle types,
including PvP, PvE, and multi-player battles with turn-based combat.
"""

import json
import random
import time
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from functools import lru_cache

from src.models.veramon import Veramon
from src.db.cache_manager import get_cache_manager
from src.utils.performance_monitor import get_performance_monitor
from src.utils.battle_metrics import get_battle_metrics

# Set up logging
logger = logging.getLogger("battle")

class BattleType(Enum):
    PVP = "pvp"              # Player vs Player (1v1)
    PVE = "pve"              # Player vs NPC
    MULTI = "multi"          # Multiple players (2v2, FFA)

class BattleStatus(Enum):
    WAITING = "waiting"      # Waiting for players to join
    ACTIVE = "active"        # Battle in progress
    COMPLETED = "completed"  # Battle has ended with a winner
    CANCELLED = "cancelled"  # Battle was cancelled or abandoned

class ParticipantStatus(Enum):
    INVITED = "invited"      # Player has been invited
    JOINED = "joined"        # Player has joined
    DECLINED = "declined"    # Player declined invitation
    LEFT = "left"            # Player left the battle

class ActionType(Enum):
    MOVE = "move"            # Using a move/ability
    SWITCH = "switch"        # Switching active Veramon
    ITEM = "item"            # Using an item
    FLEE = "flee"            # Attempting to flee

# Performance decorator for battle operations
def time_battle_operation(operation_name: str = None):
    """Decorator to time battle operations for performance monitoring."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            # Get name of the operation
            op_name = operation_name or func.__name__
            
            # Log slow operations (more than 100ms)
            if elapsed_time > 0.1:
                logger.warning(f"Slow battle operation: {op_name} took {elapsed_time:.4f}s")
                
            # Record metrics in performance monitor
            monitor = get_performance_monitor()
            if monitor:
                if "battle_operation" in op_name:
                    monitor.record_battle_operation(op_name.replace("battle_operation_", ""), elapsed_time)
                else:
                    monitor.record_custom_metric(f"battle_{op_name}", elapsed_time)
                
            return result
        return wrapper
    return decorator

class Battle:
    """
    Core battle class that handles battle state and logic.
    This serves as the model for all types of battles (PVP, PVE, Multi).
    """
    STAT_KEYS = {
        "hp": "current_hp",  # Map from form modifier key to battle_veramon key
        "attack": "attack",
        "defense": "defense",
        "speed": "speed"
    }
    
    # Move type effectiveness multipliers
    TYPE_CHART = {
        # Format: {attacking_type: {defending_type: multiplier}}
        "normal": {"rock": 0.5, "steel": 0.5, "ghost": 0},
        "fire": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
        "water": {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
        "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2.0, "dragon": 0.5},
        "grass": {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
        "ice": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
        "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0, "dark": 2.0, "steel": 2.0, "fairy": 0.5},
        "poison": {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2.0},
        "ground": {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
        "flying": {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
        "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0, "steel": 0.5},
        "bug": {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5},
        "rock": {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
        "ghost": {"normal": 0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
        "dragon": {"dragon": 2.0, "steel": 0.5, "fairy": 0},
        "dark": {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
        "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5, "fairy": 2.0},
        "fairy": {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5}
    }
    
    # Critical hit chance and multiplier
    CRITICAL_HIT_CHANCE = 0.1  # 10% chance
    CRITICAL_HIT_MULTIPLIER = 1.5
    
    # Damage calculation constants
    DAMAGE_RANDOM_MIN = 0.85
    DAMAGE_RANDOM_MAX = 1.0
    
    def __init__(
        self,
        battle_id: int,
        battle_type: BattleType,
        host_id: str,
        teams: List[Dict[str, Any]] = None,
        expiry_minutes: int = 5
    ):
        self.battle_id = battle_id
        self.battle_type = battle_type
        self.status = BattleStatus.WAITING
        self.host_id = host_id
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.teams = teams or [{"team_id": 0, "name": "Default", "color": "blue"}]
        self.participants = {}  # user_id -> participant data
        self.veramon = {}       # user_id -> list of Veramon objects
        self.active_veramon = {}  # user_id -> active Veramon index
        self.turn_order = []    # List of user_ids in turn order
        self.current_turn = None  # user_id whose turn it is
        self.turn_number = 0
        self.winner_id = None
        self.battle_log = []
        self.expiry_time = (datetime.utcnow() + timedelta(minutes=expiry_minutes)).isoformat()
        self.weather_effects = {}
        self.status_effects = {}  # Veramon ID -> list of status effects
        self.field_conditions = {}  # Field-wide conditions
        
        # Cache manager for battle-related data
        self.cache_manager = get_cache_manager()
        
        # Calculation cache (in-memory for this battle instance)
        self._move_result_cache = {}
        self._stat_cache = {}
        
        # Performance tracking
        self.performance_monitor = get_performance_monitor()
        self.battle_metrics = get_battle_metrics()
        
        # Record battle start in metrics
        self.battle_metrics.record_battle_start(battle_id, battle_type.value)
        
        # Add host as first participant
        self.add_participant(host_id, team_id=0, is_host=True)
    
    def add_participant(
        self, 
        user_id: str, 
        team_id: int = 0, 
        is_host: bool = False,
        is_npc: bool = False,
        status: ParticipantStatus = ParticipantStatus.INVITED
    ) -> bool:
        """Add a participant to the battle."""
        if user_id in self.participants:
            return False
            
        self.participants[user_id] = {
            "team_id": team_id,
            "is_host": is_host,
            "is_npc": is_npc,
            "status": status,
            "joined_at": datetime.utcnow().isoformat() if status == ParticipantStatus.JOINED else None
        }
        self.updated_at = datetime.utcnow().isoformat()
        
        # Clear any participant-related caches
        self._invalidate_battle_caches()
        
        return True
        
    def add_veramon(self, user_id: str, veramon: Veramon, slot: int) -> bool:
        """Add a Veramon to a participant's team."""
        if user_id not in self.participants:
            return False
            
        if user_id not in self.veramon:
            self.veramon[user_id] = [None] * 6  # Max 6 slots
            
        if slot < 0 or slot >= 6:
            return False
            
        self.veramon[user_id][slot] = veramon
        self.updated_at = datetime.utcnow().isoformat()
        
        # Cache this Veramon's data for quick access
        if veramon and hasattr(veramon, 'id'):
            self.cache_manager.cache_veramon_data(str(veramon.id), veramon.to_dict())
            
        # Clear stat caches for this user
        if user_id in self._stat_cache:
            del self._stat_cache[user_id]
            
        return True
        
    def set_active_veramon(self, user_id: str, slot: int) -> bool:
        """Set a participant's active Veramon."""
        if user_id not in self.participants or user_id not in self.veramon:
            return False
            
        if slot < 0 or slot >= len(self.veramon[user_id]) or self.veramon[user_id][slot] is None:
            return False
            
        self.active_veramon[user_id] = slot
        self.updated_at = datetime.utcnow().isoformat()
        
        # Clear move result cache when active Veramon changes
        self._clear_move_result_cache(user_id)
        
        return True
    
    @time_battle_operation("battle_operation_start")
    def start_battle(self) -> Dict[str, Any]:
        """Start the battle if all conditions are met."""
        # Record timing for this operation
        start_time = time.time()
        
        # Check if battle can be started
        if self.status != BattleStatus.WAITING:
            return {"success": False, "message": "Battle already started or completed"}
            
        # Check if all participants have joined
        for user_id, data in self.participants.items():
            if data["status"] != ParticipantStatus.JOINED and not data["is_npc"]:
                return {"success": False, "message": "Not all participants have joined"}
                
        # Check if all participants have at least one Veramon
        for user_id in self.participants:
            if user_id not in self.veramon or not any(v is not None for v in self.veramon[user_id]):
                return {"success": False, "message": "Not all participants have Veramon"}
                
        # Set active Veramon for all participants (first non-null Veramon)
        for user_id in self.participants:
            if user_id not in self.active_veramon:
                for i, veramon in enumerate(self.veramon[user_id]):
                    if veramon is not None:
                        self.active_veramon[user_id] = i
                        break
                        
        # Determine turn order (speed-based)
        self._determine_turn_order()
        
        # Set current turn to first in turn order
        if self.turn_order:
            self.current_turn = self.turn_order[0]
            
        # Apply form modifiers to active Veramon
        for user_id in self.participants:
            active_slot = self.active_veramon.get(user_id)
            if active_slot is not None:
                veramon_obj = self.veramon[user_id][active_slot]
                if veramon_obj:
                    battle_veramon = {"current_hp": veramon_obj.hp}
                    self.apply_form_modifiers(veramon_obj, battle_veramon)
                    
                    # Initialize status effects for this Veramon
                    if veramon_obj.id not in self.status_effects:
                        self.status_effects[veramon_obj.id] = []
            
        # Mark battle as active
        self.status = BattleStatus.ACTIVE
        self.updated_at = datetime.utcnow().isoformat()
        
        # Add battle start log entry
        self._add_log_entry(
            ActionType.MOVE, 
            "system", 
            [], 
            {"type": "battle_start"}, 
            {"turn_order": self.turn_order, "current_turn": self.current_turn}
        )
        
        # Clear all caches at battle start for a clean state
        self._clear_all_caches()
        
        # Record operation time in battle metrics
        end_time = time.time()
        self.battle_metrics.record_operation_time("battle_start", end_time - start_time)
        
        return {
            "success": True,
            "message": "Battle started",
            "turn_order": self.turn_order,
            "current_turn": self.current_turn
        }
    
    def _determine_turn_order(self):
        """Determine turn order based on Veramon speed."""
        participant_speed = {}
        
        # Calculate speed for each participant's active Veramon
        for user_id in self.participants:
            if user_id in self.active_veramon and user_id in self.veramon:
                active_idx = self.active_veramon[user_id]
                active_veramon = self.veramon[user_id][active_idx]
                if active_veramon:
                    # Get base speed
                    speed = active_veramon.speed
                    
                    # Apply modifiers from form
                    if hasattr(active_veramon, "form") and active_veramon.form:
                        form_data = self._get_cached_form_data(active_veramon.form)
                        if form_data and "modifiers" in form_data:
                            if "speed" in form_data["modifiers"]:
                                speed_mod = form_data["modifiers"]["speed"]
                                if isinstance(speed_mod, (int, float)):
                                    speed *= speed_mod
                    
                    # Apply modifiers from status effects
                    if hasattr(active_veramon, "id") and active_veramon.id in self.status_effects:
                        for effect in self.status_effects[active_veramon.id]:
                            if "speed_modifier" in effect:
                                speed *= effect["speed_modifier"]
                    
                    participant_speed[user_id] = speed
        
        # Sort by speed (highest first)
        self.turn_order = sorted(participant_speed.keys(), 
                                key=lambda uid: participant_speed.get(uid, 0), 
                                reverse=True)

    def _get_cached_form_data(self, form_name: str) -> Dict[str, Any]:
        """Get cached form data or fetch it if not in cache."""
        # Try to get from cache
        cache_key = f"form_data:{form_name}"
        form_data = self.cache_manager.get_object(cache_key)
        
        if form_data is not None:
            return form_data
            
        # Not in cache - would normally fetch from database
        # For now, return empty dict, real implementation would query from database
        return {}
        
    def apply_form_modifiers(self, veramon_obj, battle_veramon):
        """Apply stat modifiers from active forms."""
        if not hasattr(veramon_obj, "form") or not veramon_obj.form:
            return
            
        # Calculate unique cache key for this specific Veramon's form stats
        cache_key = f"form_stats:{veramon_obj.id}:{veramon_obj.form}"
        
        # Check if cached
        cached_stats = self._stat_cache.get(cache_key)
        if cached_stats:
            for stat, value in cached_stats.items():
                battle_veramon[stat] = value
            return
            
        # Continue with regular calculation if not cached
        # Use cached form data
        form_data = self._get_cached_form_data(veramon_obj.form)
        
        if not form_data or "modifiers" not in form_data:
            return
            
        modifiers = form_data["modifiers"]
        
        # Apply modifiers to active stats
        modified_stats = {}
        
        # Apply all stat modifiers using a loop instead of repetitive conditionals
        for base_stat, battle_stat in self.STAT_KEYS.items():
            if base_stat in modifiers and isinstance(modifiers[base_stat], (int, float)):
                # Get base value from veramon object
                base_value = getattr(veramon_obj, base_stat)
                # Apply modifier
                modified_value = int(base_value * modifiers[base_stat])
                # Update battle veramon
                battle_veramon[battle_stat] = modified_value
                # Store for cache
                modified_stats[battle_stat] = modified_value
            
        # Cache the calculated stats
        self._stat_cache[cache_key] = modified_stats

    @time_battle_operation("battle_operation_execute_move")
    def execute_move(self, user_id: str, move_name: str, target_ids: List[str]) -> Dict[str, Any]:
        """Execute a move and return the results."""
        # Record timing for this operation
        start_time = time.time()
        
        # Check if it's the user's turn
        if self.current_turn != user_id:
            return {"success": False, "message": "Not your turn"}
            
        # Check if battle is active
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        # Get attacker's active Veramon
        if user_id not in self.active_veramon or user_id not in self.veramon:
            return {"success": False, "message": "No active Veramon"}
            
        active_slot = self.active_veramon[user_id]
        attacker = self.veramon[user_id][active_slot]
        
        if attacker is None:
            return {"success": False, "message": "No active Veramon"}
            
        # Validate move
        move_list = getattr(attacker, "moves", [])
        if not any(m["name"] == move_name for m in move_list):
            return {"success": False, "message": "Invalid move"}
            
        # Process targets
        results = []
        for target_id in target_ids:
            # Skip invalid targets
            if target_id not in self.active_veramon or target_id not in self.veramon:
                continue
                
            target_slot = self.active_veramon[target_id]
            target = self.veramon[target_id][target_slot]
            
            if target is None:
                continue
                
            # Check for cache hit first
            cache_key = f"{attacker.id}:{move_name}:{target.id}:{self.turn_number}"
            if cache_key in self._move_result_cache:
                result = self._move_result_cache[cache_key].copy()
            else:
                # Calculate result
                calculation_start = time.time()
                result = self._calculate_move_result(attacker, target, move_name)
                calculation_time = time.time() - calculation_start
                
                # Record move calculation time in metrics
                self.battle_metrics.record_move_calculation(calculation_time)
                
                # Cache for this turn
                self._move_result_cache[cache_key] = result.copy()
            
            # Apply damage to target
            if "damage" in result and result["damage"] > 0:
                target.current_hp = target.current_hp - result["damage"]
                if target.current_hp < 0:
                    target.current_hp = 0
                
                # Update result with new HP
                result["target_hp"] = target.current_hp
                result["target_max_hp"] = target.hp
                
            # Apply effects if present
            if "effects" in result and result["effects"]:
                self._apply_move_effects(attacker.id, target.id, result["effects"])
                
            results.append({
                "target_id": target_id,
                "result": result
            })
        
        # Add to battle log
        self._add_log_entry(
            ActionType.MOVE,
            user_id,
            target_ids,
            {"move_name": move_name},
            {"results": results}
        )
        
        # Record the move in battle metrics
        self.battle_metrics.record_move_use(self.battle_id)
        
        # Check if battle has ended
        battle_end = self._check_battle_end()
        
        # If battle continues, advance to next turn
        if not battle_end["ended"]:
            self._advance_turn()
        
        # Clear move cache for next turn calculations
        if battle_end["ended"]:
            self._clear_all_caches()
            
            # Record battle end in metrics
            outcome = "completed" if self.status == BattleStatus.COMPLETED else "cancelled"
            self.battle_metrics.record_battle_end(self.battle_id, outcome)
        
        # Record total operation time
        end_time = time.time()
        self.battle_metrics.record_operation_time("execute_move", end_time - start_time)
        
        return {
            "success": True,
            "message": f"Used {move_name}",
            "results": results,
            "battle_end": battle_end,
            "next_turn": self.current_turn
        }

    def _clear_move_result_cache(self, user_id=None):
        """Clear move result cache for a specific user or all users."""
        if user_id:
            # Clear only cache entries for this user
            keys_to_remove = []
            for key in self._move_result_cache:
                parts = key.split(":")
                if len(parts) >= 4 and (parts[0] == user_id or parts[2] == user_id):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._move_result_cache[key]
        else:
            # Clear entire cache
            self._move_result_cache.clear()
    
    def _clear_all_caches(self):
        """Clear all battle-related caches."""
        self._move_result_cache.clear()
        self._stat_cache.clear()
    
    def _invalidate_battle_caches(self):
        """Invalidate any persistent caches related to this battle."""
        battle_cache_key = f"battle:{self.battle_id}"
        self.cache_manager.invalidate_object(battle_cache_key)
        
        # Also invalidate any pattern-based caches for this battle
        self.cache_manager.invalidate_pattern(f"battle_{self.battle_id}")
    
    def _apply_move_effects(self, attacker_id, target_id, effects):
        """Apply effects from a move to the target."""
        # Initialize status effects for this target if needed
        if target_id not in self.status_effects:
            self.status_effects[target_id] = []
            
        # Process each effect
        for effect in effects:
            effect_type = effect.get("type")
            
            if effect_type == "status":
                # Add status effect with turn duration
                status_name = effect.get("name")
                duration = effect.get("duration", 3)  # Default 3 turns
                
                # Create effect entry
                effect_entry = {
                    "name": status_name,
                    "turns_remaining": duration,
                    "applied_by": attacker_id,
                    "applied_at_turn": self.turn_number,
                    **effect  # Include all other effect properties
                }
                
                # Add to status effects
                self.status_effects[target_id].append(effect_entry)
        
        # Clear caches affected by status changes
        battle_cache_key = f"battle:{self.battle_id}"
        self.cache_manager.invalidate_object(battle_cache_key)
        
    def _calculate_type_effectiveness(self, move_type: str, defender_type: str) -> float:
        """Calculate type effectiveness multiplier."""
        if not move_type or not defender_type:
            return 1.0
            
        # Get type chart for attacking move
        type_matchups = self.TYPE_CHART.get(move_type.lower(), {})
        
        # Return multiplier or default to 1.0 (neutral)
        return type_matchups.get(defender_type.lower(), 1.0)
    
    @lru_cache(maxsize=128)
    def _calculate_move_result(self, attacker: Veramon, defender: Veramon, move_name: str) -> Dict[str, Any]:
        """Calculate the result of a move, including damage and effects."""
        # Find the move in attacker's move list
        move = next((m for m in attacker.moves if m["name"] == move_name), None)
        
        if not move:
            return {"success": False, "message": "Move not found"}
            
        # Extract move properties
        power = move.get("power", 0)
        accuracy = move.get("accuracy", 100)
        move_type = move.get("type", "normal")
        
        # Check if move hits based on accuracy
        hit_roll = random.randint(1, 100)
        if hit_roll > accuracy:
            return {"success": False, "message": "Move missed"}
            
        # Initialize result
        result = {
            "success": True,
            "damage": 0
        }
            
        # Calculate damage for damaging moves
        if power > 0:
            # Get attacker's attack stat (with modifiers)
            attack_stat = getattr(attacker, "attack", 10)
            # Get defender's defense stat (with modifiers)
            defense_stat = getattr(defender, "defense", 10)
            
            # Apply type effectiveness
            type_multiplier = 1.0
            if hasattr(defender, "type"):
                defender_type = getattr(defender, "type", "normal")
                type_multiplier = self._calculate_type_effectiveness(move_type, defender_type)
            
            # Base damage formula
            damage_formula = (2 * attacker.level / 5 + 2) * power * attack_stat / defense_stat / 50 + 2
            
            # Apply type effectiveness
            damage = int(damage_formula * type_multiplier)
            
            # Critical hit check
            is_critical = random.random() < self.CRITICAL_HIT_CHANCE
            if is_critical:
                damage = int(damage * self.CRITICAL_HIT_MULTIPLIER)
                
            # Apply random factor
            random_factor = self.DAMAGE_RANDOM_MIN + random.random() * (self.DAMAGE_RANDOM_MAX - self.DAMAGE_RANDOM_MIN)
            damage = int(damage * random_factor)
            
            # Ensure minimum damage
            damage = max(1, damage)
                
            # Update result with damage info
            result.update({
                "damage": damage,
                "is_critical": is_critical,
                "effectiveness": type_multiplier
            })
            
        # Add effects if present
        if "effects" in move and move["effects"]:
            result["effects"] = move["effects"]
            
        return result

    def _check_battle_end(self) -> Dict[str, Any]:
        """Check if the battle has ended and determine the winner."""
        # Check each team's Veramon health
        team_health = {}
        
        # Group participants by team
        for user_id, data in self.participants.items():
            team_id = data["team_id"]
            if team_id not in team_health:
                team_health[team_id] = {"alive": 0, "total": 0, "participants": []}
                
            team_health[team_id]["participants"].append(user_id)
            
            # Skip if user has no Veramon
            if user_id not in self.veramon:
                continue
                
            # Count Veramon for this user
            total_veramon = 0
            alive_veramon = 0
            
            for veramon in self.veramon[user_id]:
                if veramon is not None:
                    total_veramon += 1
                    if veramon.current_hp > 0:
                        alive_veramon += 1
            
            # Update team totals
            team_health[team_id]["alive"] += alive_veramon
            team_health[team_id]["total"] += total_veramon
        
        # Check for teams with no living Veramon
        defeated_teams = [
            team_id for team_id, data in team_health.items()
            if data["alive"] == 0 and data["total"] > 0
        ]
        
        # If multiple teams and only one team has living Veramon, they win
        if len(team_health) > 1 and len(defeated_teams) == len(team_health) - 1:
            # Find the winning team
            for team_id, data in team_health.items():
                if team_id not in defeated_teams and data["alive"] > 0:
                    # This team wins
                    self.status = BattleStatus.COMPLETED
                    
                    # Set winner to the first participant in the winning team
                    if data["participants"]:
                        self.winner_id = data["participants"][0]
                        
                    # Add battle end log entry
                    self._add_log_entry(
                        ActionType.MOVE,
                        "system",
                        [],
                        {"type": "battle_end"},
                        {"winner_team": team_id, "winner_id": self.winner_id}
                    )
                    
                    return {
                        "ended": True,
                        "winner_team": team_id,
                        "winner_id": self.winner_id
                    }
        
        # PVE special case - if player has lost all Veramon, NPC wins
        if self.battle_type == BattleType.PVE:
            # Find player and NPC participants
            player_ids = [user_id for user_id, data in self.participants.items() if not data["is_npc"]]
            npc_ids = [user_id for user_id, data in self.participants.items() if data["is_npc"]]
            
            # Check if player has lost
            player_alive = False
            for user_id in player_ids:
                if user_id in self.veramon:
                    for veramon in self.veramon[user_id]:
                        if veramon is not None and veramon.current_hp > 0:
                            player_alive = True
                            break
                            
            if not player_alive and player_ids:
                self.status = BattleStatus.COMPLETED
                
                # NPC wins
                if npc_ids:
                    self.winner_id = npc_ids[0]
                
                # Add battle end log entry
                self._add_log_entry(
                    ActionType.MOVE,
                    "system",
                    [],
                    {"type": "battle_end"},
                    {"winner_id": self.winner_id, "npc_victory": True}
                )
                
                return {
                    "ended": True,
                    "winner_id": self.winner_id,
                    "npc_victory": True
                }
                
            # Check if NPC has lost
            npc_alive = False
            for user_id in npc_ids:
                if user_id in self.veramon:
                    for veramon in self.veramon[user_id]:
                        if veramon is not None and veramon.current_hp > 0:
                            npc_alive = True
                            break
                            
            if not npc_alive and npc_ids and player_ids:
                self.status = BattleStatus.COMPLETED
                
                # Player wins
                self.winner_id = player_ids[0]
                
                # Add battle end log entry
                self._add_log_entry(
                    ActionType.MOVE,
                    "system",
                    [],
                    {"type": "battle_end"},
                    {"winner_id": self.winner_id, "player_victory": True}
                )
                
                return {
                    "ended": True,
                    "winner_id": self.winner_id,
                    "player_victory": True
                }
        
        # Battle continues
        return {"ended": False}

    async def start_battle(self) -> bool:
        """Start the battle if all conditions are met."""
        # Check if all participants have joined
        for user_id, participant in self.participants.items():
            if participant["status"] != ParticipantStatus.JOINED:
                return False
                
        # Check if all participants have at least one Veramon
        for user_id in self.participants:
            if user_id not in self.veramon or not any(v is not None for v in self.veramon[user_id]):
                return False
                
        # Check if all participants have an active Veramon
        for user_id in self.participants:
            if user_id not in self.active_veramon:
                # Auto-select first available Veramon
                for i, v in enumerate(self.veramon[user_id]):
                    if v is not None:
                        self.active_veramon[user_id] = i
                        break
                else:
                    return False
        
        # Determine turn order based on speed
        self._determine_turn_order()
        
        # Set battle status to active
        self.status = BattleStatus.ACTIVE
        self.current_turn = self.turn_order[0]
        self.turn_number = 1
        self.updated_at = datetime.utcnow().isoformat()
        
        # Log battle start
        self._add_log_entry(
            action_type=ActionType.MOVE,
            actor_id="system",
            target_ids=[],
            action_data={"type": "battle_start"},
            result_data={"turn_order": self.turn_order}
        )
        
        # Record weather effects if the battle is taking place in a specific biome
        self.weather_effects = {}
        
        if hasattr(self, 'biome') and self.biome:
            # Get weather from CatchingCog if available
            catching_cog = self.bot.get_cog('CatchingCog')
            if catching_cog and hasattr(catching_cog, 'current_weather'):
                current_weather = catching_cog.current_weather.get(self.biome)
                
                if current_weather:
                    biome_data = catching_cog.biomes.get(self.biome, {})
                    weather_data = biome_data.get('weather_effects', {}).get(current_weather, {})
                    
                    # Store weather effects for use during battle
                    self.weather_effects = {
                        'name': current_weather,
                        'description': weather_data.get('description', f'{current_weather.capitalize()} weather'),
                        'type_modifiers': weather_data.get('spawn_modifiers', {})
                    }
        
        return True
        
    def apply_form_modifiers(self, veramon_obj, battle_veramon):
        """Apply stat modifiers from active forms."""
        if not hasattr(veramon_obj, 'active_form') or not veramon_obj.active_form:
            return
            
        # Get form data
        form_data = None
        for form in veramon_obj.data.get('forms', []):
            if form.get('id') == veramon_obj.active_form:
                form_data = form
                break
                
        if not form_data:
            return
            
        # Apply stat modifiers to battle stats
        stat_modifiers = form_data.get('stat_modifiers', {})
        
        if 'hp' in stat_modifiers:
            battle_veramon['max_hp'] = int(battle_veramon['max_hp'] * stat_modifiers['hp'])
            battle_veramon['current_hp'] = min(battle_veramon['current_hp'], battle_veramon['max_hp'])
            
        if 'atk' in stat_modifiers:
            battle_veramon['stats']['atk'] = int(battle_veramon['stats']['atk'] * stat_modifiers['atk'])
            
        if 'def' in stat_modifiers:
            battle_veramon['stats']['def'] = int(battle_veramon['stats']['def'] * stat_modifiers['def'])
            
        if 'sp_atk' in stat_modifiers:
            battle_veramon['stats']['sp_atk'] = int(battle_veramon['stats']['sp_atk'] * stat_modifiers['sp_atk'])
            
        if 'sp_def' in stat_modifiers:
            battle_veramon['stats']['sp_def'] = int(battle_veramon['stats']['sp_def'] * stat_modifiers['sp_def'])
            
        if 'speed' in stat_modifiers:
            battle_veramon['stats']['speed'] = int(battle_veramon['stats']['speed'] * stat_modifiers['speed'])
        
    async def execute_move(self, user_id: str, move_name: str, target_ids: List[str]) -> Dict[str, Any]:
        """Execute a move and return the results."""
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        if user_id != self.current_turn:
            return {"success": False, "message": "Not your turn"}
            
        if user_id not in self.active_veramon:
            return {"success": False, "message": "No active Veramon"}
            
        active_slot = self.active_veramon[user_id]
        attacker = self.veramon[user_id][active_slot]
        
        # Check if the move is valid for the Veramon
        if move_name not in attacker.moves:
            return {"success": False, "message": f"Your Veramon doesn't know {move_name}"}
            
        # Process the move against each target
        results = []
        for target_id in target_ids:
            if target_id not in self.active_veramon:
                results.append({
                    "target_id": target_id,
                    "success": False,
                    "message": "Invalid target"
                })
                continue
                
            target_slot = self.active_veramon[target_id]
            defender = self.veramon[target_id][target_slot]
            
            # Calculate damage and effects
            move_result = self._calculate_move_result(attacker, defender, move_name)
            
            # Apply damage and effects
            if move_result["damage"] > 0:
                defender.current_hp -= move_result["damage"]
                defender.current_hp = max(0, defender.current_hp)
                
            # Check if the defender fainted
            if defender.current_hp == 0:
                move_result["fainted"] = True
                
                # Check for battle end condition
                if self._check_battle_end():
                    move_result["battle_ended"] = True
                    move_result["winner_id"] = self.winner_id
            
            results.append({
                "target_id": target_id,
                "success": True,
                "result": move_result
            })
        
        # Log the move
        self._add_log_entry(
            ActionType.MOVE,
            user_id,
            target_ids,
            {"move_name": move_name},
            {"results": results}
        )
        
        # Apply weather effects if applicable
        if self.weather_effects and 'type_modifiers' in self.weather_effects:
            move_type = move_name.get('type', 'Normal')
            if move_type in self.weather_effects['type_modifiers']:
                type_modifier = self.weather_effects['type_modifiers'][move_type]
                damage = int(move_result["damage"] * type_modifier)
                if type_modifier > 1:
                    self._add_log_entry(
                        ActionType.MOVE,
                        "system",
                        [],
                        {"type": "weather_boost"},
                        {"weather": self.weather_effects['name'], "move_type": move_type}
                    )
                elif type_modifier < 1:
                    self._add_log_entry(
                        ActionType.MOVE,
                        "system",
                        [],
                        {"type": "weather_weakness"},
                        {"weather": self.weather_effects['name'], "move_type": move_type}
                    )
        
        # Advance to next turn if battle not over
        if self.status == BattleStatus.ACTIVE:
            self._advance_turn()
            
        return {"success": True, "results": results, "next_turn": self.current_turn}
        
    def _calculate_move_result(self, attacker: Veramon, defender: Veramon, move_name: str) -> Dict[str, Any]:
        """Calculate the result of a move, including damage and effects."""
        # This would use your ability data from abilities.json
        # For simplicity, we'll just do a basic calculation here
        base_damage = random.randint(10, 20)
        critical_hit = random.random() < 0.1
        type_effectiveness = random.choice([0.5, 1.0, 2.0])  # Simplified
        
        damage_multiplier = 1.0
        if critical_hit:
            damage_multiplier *= 1.5
        damage_multiplier *= type_effectiveness
        
        final_damage = int(base_damage * damage_multiplier)
        
        return {
            "damage": final_damage,
            "critical_hit": critical_hit,
            "type_effectiveness": type_effectiveness,
            "effects": [],
            "message": f"Dealt {final_damage} damage!"
        }
        
    def _check_battle_end(self) -> bool:
        """Check if the battle has ended and determine the winner."""
        # Group participants by team
        teams = {}
        for user_id, participant in self.participants.items():
            team_id = participant["team_id"]
            if team_id not in teams:
                teams[team_id] = []
            teams[team_id].append(user_id)
            
        # Check which teams still have conscious Veramon
        active_teams = set()
        for user_id in self.participants:
            if user_id not in self.veramon:
                continue
                
            # Check if user has any conscious Veramon
            has_conscious = False
            for veramon in self.veramon[user_id]:
                if veramon is not None and veramon.current_hp > 0:
                    has_conscious = True
                    break
                    
            if has_conscious:
                team_id = self.participants[user_id]["team_id"]
                active_teams.add(team_id)
        
        # If only one team remains, they win
        if len(active_teams) == 1:
            winning_team = list(active_teams)[0]
            # In FFA (each player on their own team), winner is the player
            if len(teams[winning_team]) == 1:
                self.winner_id = teams[winning_team][0]
            else:
                self.winner_id = str(winning_team)  # Team ID as string
                
            self.status = BattleStatus.COMPLETED
            self.updated_at = datetime.utcnow().isoformat()
            
            # Log battle end
            self._add_log_entry(
                action_type=ActionType.MOVE,
                actor_id="system",
                target_ids=[],
                action_data={"type": "battle_end"},
                result_data={"winner_id": self.winner_id}
            )
            
            return True
            
        # If no teams remain (should never happen), it's a draw
        if len(active_teams) == 0:
            self.status = BattleStatus.COMPLETED
            self.winner_id = "draw"
            self.updated_at = datetime.utcnow().isoformat()
            
            # Log battle end
            self._add_log_entry(
                action_type=ActionType.MOVE,
                actor_id="system",
                target_ids=[],
                action_data={"type": "battle_end"},
                result_data={"winner_id": self.winner_id}
            )
            
            return True
            
        return False
        
    @time_battle_operation("battle_operation_switch")
    def switch_veramon(self, user_id: str, new_slot: int) -> Dict[str, Any]:
        """Switch a player's active Veramon."""
        # Record timing for this operation
        start_time = time.time()
        
        # Check if it's the user's turn
        if self.current_turn != user_id:
            return {"success": False, "message": "Not your turn"}
            
        # Check if battle is active
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        # Check if switch is valid
        if user_id not in self.veramon:
            return {"success": False, "message": "No Veramon team"}
            
        if new_slot < 0 or new_slot >= len(self.veramon[user_id]):
            return {"success": False, "message": "Invalid slot"}
            
        # Check if veramon exists in the slot
        if self.veramon[user_id][new_slot] is None:
            return {"success": False, "message": "No Veramon in selected slot"}
            
        # Check if veramon is already active
        if self.active_veramon.get(user_id) == new_slot:
            return {"success": False, "message": "This Veramon is already active"}
            
        # Check if target Veramon has fainted
        if self.veramon[user_id][new_slot].current_hp <= 0:
            return {"success": False, "message": "Cannot switch to a fainted Veramon"}
            
        # Get current and new Veramon for log
        current_slot = self.active_veramon.get(user_id)
        current_veramon = self.veramon[user_id][current_slot] if current_slot is not None else None
        new_veramon = self.veramon[user_id][new_slot]
        
        # Perform the switch
        self.active_veramon[user_id] = new_slot
        self.updated_at = datetime.utcnow().isoformat()
        
        # Clear move result cache for this user
        self._clear_move_result_cache(user_id)
        
        # Add log entry
        self._add_log_entry(
            ActionType.SWITCH,
            user_id,
            [user_id],
            {
                "previous_slot": current_slot,
                "new_slot": new_slot,
                "previous_veramon": current_veramon.name if current_veramon else None,
                "new_veramon": new_veramon.name
            },
            {"success": True}
        )
        
        # Apply form modifiers to the newly active Veramon
        battle_veramon = {"current_hp": new_veramon.current_hp}
        self.apply_form_modifiers(new_veramon, battle_veramon)
        
        # Make sure status effects are initialized
        if new_veramon.id not in self.status_effects:
            self.status_effects[new_veramon.id] = []
        
        # Advance turn to next player
        self._advance_turn()
        
        # Record the switch in battle metrics
        self.battle_metrics.record_switch(self.battle_id)
        
        # Record total operation time
        end_time = time.time()
        self.battle_metrics.record_operation_time("switch_veramon", end_time - start_time)
        
        return {
            "success": True,
            "message": f"Switched to {new_veramon.name}",
            "previous_slot": current_slot,
            "new_slot": new_slot,
            "next_turn": self.current_turn
        }
    
    @time_battle_operation("battle_operation_use_item") 
    def use_item(self, user_id: str, item_id: str, target_id: str, target_slot: int = None) -> Dict[str, Any]:
        """Use an item in battle."""
        # Record timing for this operation
        start_time = time.time()
        
        # Check if it's the user's turn
        if self.current_turn != user_id:
            return {"success": False, "message": "Not your turn"}
            
        # Check if battle is active
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        # Get item data from cache or database
        item_data = self._get_cached_item_data(item_id)
        if not item_data:
            return {"success": False, "message": "Invalid item"}
            
        # Apply item effects (would implement item-specific logic)
        # For now, just a placeholder
        effect_result = {"applied": True, "message": f"Used {item_data.get('name', 'Unknown item')}"}
        
        # Add log entry
        self._add_log_entry(
            ActionType.ITEM,
            user_id,
            [target_id],
            {"item_id": item_id, "target_slot": target_slot},
            effect_result
        )
        
        # Invalidate relevant caches
        self._invalidate_battle_caches()
        
        # Record the item use in battle metrics
        self.battle_metrics.record_item_use(self.battle_id)
        
        # Record total operation time
        end_time = time.time()
        self.battle_metrics.record_operation_time("use_item", end_time - start_time)
        
        return {
            "success": True,
            "message": effect_result["message"],
            "effect": effect_result,
            "next_turn": self.current_turn
        }
    
    def _get_cached_item_data(self, item_id: str) -> Dict[str, Any]:
        """Get cached item data or fetch it if not in cache."""
        # Try to get from cache
        cache_key = f"item:{item_id}"
        item_data = self.cache_manager.get_object(cache_key)
        
        if item_data is not None:
            return item_data
            
        # Would normally fetch from database
        # For now, return a placeholder
        placeholder_item = {
            "id": item_id,
            "name": f"Item {item_id}",
            "type": "healing",
            "effect": {"heal_amount": 20}
        }
        
        # Cache for future use
        self.cache_manager.cache_object(cache_key, placeholder_item)
        
        return placeholder_item
    
    @time_battle_operation("battle_operation_flee")
    def attempt_flee(self, user_id: str) -> Dict[str, Any]:
        """Attempt to flee from a PVE battle."""
        # Check if it's the user's turn
        if self.current_turn != user_id:
            return {"success": False, "message": "Not your turn"}
            
        # Check if battle is active
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        # Check if this is a PVE battle (can only flee from PVE)
        if self.battle_type != BattleType.PVE:
            return {"success": False, "message": "Cannot flee from this type of battle"}
            
        # Calculate flee chance
        # Base 50% chance, modified by status effects and field conditions
        flee_chance = 0.5
        
        # Check for status effects that affect fleeing
        user_veramon_id = None
        if user_id in self.active_veramon and user_id in self.veramon:
            active_slot = self.active_veramon[user_id]
            active_veramon = self.veramon[user_id][active_slot]
            if active_veramon:
                user_veramon_id = active_veramon.id
                
        if user_veramon_id and user_veramon_id in self.status_effects:
            for effect in self.status_effects[user_veramon_id]:
                if "flee_chance_modifier" in effect:
                    flee_chance *= effect["flee_chance_modifier"]
        
        # Check field conditions that affect fleeing
        for condition in self.field_conditions.values():
            if "flee_chance_modifier" in condition:
                flee_chance *= condition["flee_chance_modifier"]
                
        # Attempt to flee
        roll = random.random()
        if roll < flee_chance:
            # Successfully fled
            self.status = BattleStatus.CANCELLED
            self.updated_at = datetime.utcnow().isoformat()
            
            # Add log entry
            self._add_log_entry(
                ActionType.FLEE,
                user_id,
                [],
                {"attempt": "flee"},
                {"success": True}
            )
            
            # Clear all caches
            self._clear_all_caches()
            
            return {"success": True, "message": "Successfully fled from battle"}
        
        # Failed to flee, lose the turn
        # Add log entry for failed flee attempt
        self._add_log_entry(
            ActionType.FLEE,
            user_id,
            [],
            {"attempt": "flee"},
            {"success": False}
        )
        
        self._advance_turn()
        return {"success": False, "message": "Failed to flee", "next_turn": self.current_turn}
        
    def _advance_turn(self):
        """Advance to the next player's turn."""
        if self.status != BattleStatus.ACTIVE:
            return
            
        current_index = self.turn_order.index(self.current_turn)
        next_index = (current_index + 1) % len(self.turn_order)
        
        # If we've looped back to the first player, increment turn number
        if next_index == 0:
            self.turn_number += 1
            
            # Process turn-based status effects
            self._process_status_effects()
            
            # Process field conditions
            self._process_field_conditions()
            
        self.current_turn = self.turn_order[next_index]
        self.updated_at = datetime.utcnow().isoformat()
    
    def _process_status_effects(self):
        """Process all status effects at the end of a full turn."""
        # Record timing for this operation
        start_time = time.time()
        
        # Process each Veramon's status effects
        for veramon_id, effects in list(self.status_effects.items()):
            for effect_index in range(len(effects) - 1, -1, -1):
                effect = effects[effect_index]
                
                # Reduce turns remaining
                if "turns_remaining" in effect:
                    effect["turns_remaining"] -= 1
                    
                    # Remove expired effects
                    if effect["turns_remaining"] <= 0:
                        effects.pop(effect_index)
                        continue
                
                # Apply recurring effects (like damage over time)
                if "recurring_effect" in effect:
                    # Apply effect to the correct Veramon
                    self._apply_recurring_effect(veramon_id, effect)
                    
                    # Record status effect application
                    self.battle_metrics.record_status_effect(self.battle_id)
        
        # Record status effect processing time
        end_time = time.time()
        self.battle_metrics.record_status_effect_processing(end_time - start_time)
    
    def _apply_recurring_effect(self, veramon_id, effect):
        """Apply a recurring effect to a Veramon."""
        # Find the Veramon with this ID
        for user_id, veramon_list in self.veramon.items():
            for slot, veramon in enumerate(veramon_list):
                if veramon and veramon.id == veramon_id:
                    recurring_effect = effect.get("recurring_effect", {})
                    
                    # Handle damage over time
                    if "damage" in recurring_effect:
                        damage = recurring_effect["damage"]
                        veramon.current_hp -= damage
                        if veramon.current_hp < 0:
                            veramon.current_hp = 0
                            
                        # Add log entry
                        self._add_log_entry(
                            ActionType.MOVE,
                            "system",
                            [user_id],
                            {"type": "status_effect", "effect_name": effect.get("name", "Unknown")},
                            {"damage": damage, "veramon_id": veramon_id}
                        )
                    
                    # Handle healing over time
                    if "healing" in recurring_effect:
                        healing = recurring_effect["healing"]
                        veramon.current_hp += healing
                        if veramon.current_hp > veramon.hp:
                            veramon.current_hp = veramon.hp
                            
                        # Add log entry
                        self._add_log_entry(
                            ActionType.MOVE,
                            "system",
                            [user_id],
                            {"type": "status_effect", "effect_name": effect.get("name", "Unknown")},
                            {"healing": healing, "veramon_id": veramon_id}
                        )
                    
                    return
    
    def _process_field_conditions(self):
        """Process field conditions at the end of a full turn."""
        # Record timing for this operation
        start_time = time.time()
        
        # Process each field condition
        for condition_id, condition in list(self.field_conditions.items()):
            # Reduce turns remaining
            if "turns_remaining" in condition:
                condition["turns_remaining"] -= 1
                
                # Remove expired conditions
                if condition["turns_remaining"] <= 0:
                    del self.field_conditions[condition_id]
                    continue
            
            # Apply recurring effects to all Veramon
            if "recurring_effect" in condition:
                self._apply_field_condition_effect(condition)
                
                # Record field condition application
                self.battle_metrics.record_field_condition(self.battle_id)
        
        # Record field condition processing time
        end_time = time.time()
        self.battle_metrics.record_field_condition_processing(end_time - start_time)
    
    def _apply_field_condition_effect(self, condition):
        """Apply a field condition effect to all Veramon."""
        recurring_effect = condition.get("recurring_effect", {})
        
        # Apply to all active Veramon
        for user_id, active_slot in self.active_veramon.items():
            if user_id in self.veramon and active_slot is not None:
                veramon = self.veramon[user_id][active_slot]
                if veramon is None:
                    continue
                    
                # Handle damage over time
                if "damage" in recurring_effect:
                    damage = recurring_effect["damage"]
                    veramon.current_hp -= damage
                    if veramon.current_hp < 0:
                        veramon.current_hp = 0
                        
                    # Add log entry
                    self._add_log_entry(
                        ActionType.MOVE,
                        "system",
                        [user_id],
                        {"type": "field_condition", "condition_name": condition.get("name", "Unknown")},
                        {"damage": damage, "veramon_id": veramon.id}
                    )
                
                # Handle healing over time
                if "healing" in recurring_effect:
                    healing = recurring_effect["healing"]
                    veramon.current_hp += healing
                    if veramon.current_hp > veramon.hp:
                        veramon.current_hp = veramon.hp
                        
                    # Add log entry
                    self._add_log_entry(
                        ActionType.MOVE,
                        "system",
                        [user_id],
                        {"type": "field_condition", "condition_name": condition.get("name", "Unknown")},
                        {"healing": healing, "veramon_id": veramon.id}
                    )
        
    def _add_log_entry(self, action_type: ActionType, actor_id: str, target_ids: List[str], 
                      action_data: Dict[str, Any], result_data: Dict[str, Any]):
        """Add an entry to the battle log."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type.value,
            "actor_id": actor_id,
            "target_ids": target_ids,
            "action_data": action_data,
            "result_data": result_data
        }
        self.battle_log.append(log_entry)
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the battle state to a serializable dictionary for persistence.
        """
        # Convert battle status to string if it's an enum
        status = self.status.value if hasattr(self.status, 'value') else self.status
        
        # Prepare serializable state
        state = {
            "battle_id": self.battle_id,
            "battle_type": self.battle_type.value if hasattr(self.battle_type, 'value') else self.battle_type,
            "host_id": self.host_id,
            "status": status,
            "current_turn": self.current_turn,
            "turn_number": self.turn_number,
            "winner_id": self.winner_id,
            "start_time": self.start_time,
            "end_time": getattr(self, "end_time", None),
            "participants": self.participants,
            "teams": self.teams,
            "veramon": self.veramon,
            "active_veramon": self.active_veramon,
            "battle_log": self.battle_log,
            "turn_order": self.turn_order,
            "field_conditions": getattr(self, "field_conditions", {})
        }
        
        return state
        
    def restore_from_dict(self, state: Dict[str, Any]) -> None:
        """
        Restore battle state from a dictionary.
        """
        # Restore basic attributes
        self.battle_id = state.get("battle_id", self.battle_id)
        self.host_id = state.get("host_id", self.host_id)
        
        # Restore status (convert from string to enum if needed)
        status_value = state.get("status")
        if status_value is not None:
            try:
                self.status = BattleStatus(status_value)
            except (ValueError, TypeError):
                self.status = status_value
        
        # Restore battle type (convert from string/value to enum if needed)
        battle_type_value = state.get("battle_type")
        if battle_type_value is not None:
            try:
                self.battle_type = BattleType(battle_type_value)
            except (ValueError, TypeError):
                self.battle_type = battle_type_value
        
        # Restore other attributes
        self.current_turn = state.get("current_turn", self.current_turn)
        self.turn_number = state.get("turn_number", 0)
        self.winner_id = state.get("winner_id")
        self.start_time = state.get("start_time")
        self.end_time = state.get("end_time")
        
        # Restore collections
        self.participants = state.get("participants", {})
        self.teams = state.get("teams", [])
        self.veramon = state.get("veramon", {})
        self.active_veramon = state.get("active_veramon", {})
        self.battle_log = state.get("battle_log", [])
        self.turn_order = state.get("turn_order", [])
        self.field_conditions = state.get("field_conditions", {})
        
        # Rebuild caches if needed
        self._clear_all_caches()
        
    def _clear_all_caches(self):
        """Clear all caches to ensure fresh data."""
        if hasattr(self, '_move_result_cache'):
            self._move_result_cache.clear()
        if hasattr(self, '_stat_cache'):
            self._stat_cache.clear()
        if hasattr(self, '_effect_cache'):
            self._effect_cache.clear()

    STATUS_EFFECT_TYPES = [
        "poison", "burn", "paralysis", "sleep", "confusion", 
        "freeze", "flinch", "bound", "leech_seed"
    ]
    
    STATUS_EFFECT_CHANCES = {
        "poison": 0.5,
        "burn": 0.4,
        "paralysis": 0.3,
        "sleep": 0.25,
        "confusion": 0.35,
        "freeze": 0.2,
        "flinch": 0.3,
        "bound": 0.4,
        "leech_seed": 0.5
    }
    
    def apply_status_effects(self, target_id: str, effects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply status effects from move effects."""
        if not effects:
            return {"applied": [], "message": "No effects applied"}
            
        target = self._get_veramon_by_id(target_id)
        if not target:
            return {"error": "Target not found"}
            
        applied_effects = []
        messages = []
        
        for effect in effects:
            effect_type = effect.get("type")
            
            if effect_type in self.STATUS_EFFECT_TYPES:
                # Get chance of applying this effect, default to 1.0 (100%)
                apply_chance = effect.get("chance", self.STATUS_EFFECT_CHANCES.get(effect_type, 1.0))
                
                # Check if effect should be applied based on chance
                if random.random() <= apply_chance:
                    # Check if target already has this effect
                    if effect_type not in target.get("status_effects", []):
                        # Add effect to target
                        if "status_effects" not in target:
                            target["status_effects"] = []
                        
                        # Get duration (turns)
                        duration = effect.get("duration", random.randint(1, 5))
                        
                        # Create effect data
                        effect_data = {
                            "type": effect_type,
                            "duration": duration,
                            "applied_turn": self.current_turn,
                            "source": effect.get("source", "move")
                        }
                        
                        # Add any additional effect parameters
                        for key, value in effect.items():
                            if key not in ["type", "chance", "duration", "source"]:
                                effect_data[key] = value
                                
                        # Apply the effect
                        target["status_effects"].append(effect_data)
                        applied_effects.append(effect_type)
                        
                        # Create message
                        messages.append(f"{target.get('name', 'Target')} was afflicted with {effect_type}!")
                    else:
                        messages.append(f"{target.get('name', 'Target')} is already affected by {effect_type}!")
                else:
                    messages.append(f"The {effect_type} effect failed to apply!")
        
        # Return results
        return {
            "applied": applied_effects,
            "message": "\n".join(messages) if messages else "No effects applied"
        }
        
    def process_status_effects(self, veramon_id: str) -> Dict[str, Any]:
        """Process active status effects for a Veramon at the start of its turn."""
        veramon = self._get_veramon_by_id(veramon_id)
        if not veramon or "status_effects" not in veramon or not veramon["status_effects"]:
            return {"processed": [], "damage": 0, "messages": []}
            
        processed = []
        total_damage = 0
        messages = []
        updated_effects = []
        
        # Process each effect in order of precedence
        for effect_type in self.STATUS_EFFECT_TYPES:
            # Find all instances of this effect type
            type_effects = [e for e in veramon["status_effects"] if e["type"] == effect_type]
            
            for effect in type_effects:
                # Skip if already processed this turn
                if effect.get("processed_turn") == self.current_turn:
                    updated_effects.append(effect)
                    continue
                    
                # Process based on effect type
                if effect["type"] == "poison":
                    # Calculate poison damage (5% of max HP)
                    damage = max(1, int(veramon["max_hp"] * 0.05))
                    veramon["current_hp"] -= damage
                    total_damage += damage
                    messages.append(f"{veramon['name']} took {damage} poison damage!")
                    processed.append("poison")
                    
                elif effect["type"] == "burn":
                    # Calculate burn damage (8% of max HP)
                    damage = max(1, int(veramon["max_hp"] * 0.08))
                    veramon["current_hp"] -= damage
                    total_damage += damage
                    messages.append(f"{veramon['name']} took {damage} burn damage!")
                    processed.append("burn")
                    
                elif effect["type"] == "paralysis":
                    # 25% chance to skip turn
                    if random.random() < 0.25:
                        messages.append(f"{veramon['name']} is paralyzed and couldn't move!")
                        processed.append("paralysis_skip")
                    else:
                        processed.append("paralysis")
                    
                elif effect["type"] == "sleep":
                    # Skip turn while asleep
                    messages.append(f"{veramon['name']} is fast asleep!")
                    processed.append("sleep_skip")
                    
                elif effect["type"] == "confusion":
                    # 33% chance to hurt itself
                    if random.random() < 0.33:
                        damage = max(1, int(veramon["max_hp"] * 0.1))
                        veramon["current_hp"] -= damage
                        total_damage += damage
                        messages.append(f"{veramon['name']} hurt itself in confusion for {damage} damage!")
                        processed.append("confusion_self_damage")
                    else:
                        processed.append("confusion")
                
                elif effect["type"] == "freeze":
                    # Skip turn while frozen
                    messages.append(f"{veramon['name']} is frozen solid!")
                    processed.append("freeze_skip")
                    
                    # 20% chance to thaw each turn
                    if random.random() < 0.2:
                        messages.append(f"{veramon['name']} thawed out!")
                        # Don't add to updated_effects so it gets removed
                        continue
                        
                elif effect["type"] == "leech_seed":
                    # Calculate leech damage (6% of max HP)
                    damage = max(1, int(veramon["max_hp"] * 0.06))
                    veramon["current_hp"] -= damage
                    total_damage += damage
                    
                    # Find first opponent to heal
                    team_id = veramon["team_id"]
                    opponent_team = next((t for t in self.teams if t["team_id"] != team_id), None)
                    
                    if opponent_team and opponent_team.get("active_veramon"):
                        opponent = self._get_veramon_by_id(opponent_team["active_veramon"])
                        if opponent:
                            heal_amount = max(1, int(damage * 0.75))
                            opponent["current_hp"] = min(opponent["max_hp"], opponent["current_hp"] + heal_amount)
                            messages.append(
                                f"{veramon['name']} had its energy drained by Leech Seed! "
                                f"{opponent['name']} was healed for {heal_amount} HP!"
                            )
                    else:
                        messages.append(f"{veramon['name']} had its energy drained by Leech Seed for {damage} damage!")
                    
                    processed.append("leech_seed")
                
                # Mark as processed this turn
                effect["processed_turn"] = self.current_turn
                
                # Decrement duration
                effect["duration"] -= 1
                
                # Keep effect if duration > 0
                if effect["duration"] > 0:
                    updated_effects.append(effect)
                else:
                    messages.append(f"{veramon['name']} is no longer affected by {effect['type']}!")
        
        # Update Veramon's status effects
        veramon["status_effects"] = updated_effects
        
        # Check for faint
        if veramon["current_hp"] <= 0:
            veramon["current_hp"] = 0
            veramon["is_fainted"] = True
            messages.append(f"{veramon['name']} fainted!")
        
        # Return results
        return {
            "processed": processed,
            "damage": total_damage,
            "messages": messages
        }
