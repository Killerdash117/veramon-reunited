import json
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any

from src.models.veramon import Veramon

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

class Battle:
    """
    Core battle class that handles battle state and logic.
    This serves as the model for all types of battles (PVP, PVE, Multi).
    """
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
        return True
        
    def set_active_veramon(self, user_id: str, slot: int) -> bool:
        """Set a participant's active Veramon."""
        if user_id not in self.participants or user_id not in self.veramon:
            return False
            
        if slot < 0 or slot >= 6 or self.veramon[user_id][slot] is None:
            return False
            
        self.active_veramon[user_id] = slot
        self.updated_at = datetime.utcnow().isoformat()
        return True
        
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
            action_type=ActionType.MOVE,
            actor_id=user_id,
            target_ids=target_ids,
            action_data={"move_name": move_name},
            result_data={"results": results}
        )
        
        # Apply weather effects if applicable
        if self.weather_effects and 'type_modifiers' in self.weather_effects:
            move_type = move_name.get('type', 'Normal')
            if move_type in self.weather_effects['type_modifiers']:
                type_modifier = self.weather_effects['type_modifiers'][move_type]
                damage = int(move_result["damage"] * type_modifier)
                if type_modifier > 1:
                    self._add_log_entry(
                        action_type=ActionType.MOVE,
                        actor_id="system",
                        target_ids=[],
                        action_data={"type": "weather_boost"},
                        result_data={"weather": self.weather_effects['name'], "move_type": move_type}
                    )
                elif type_modifier < 1:
                    self._add_log_entry(
                        action_type=ActionType.MOVE,
                        actor_id="system",
                        target_ids=[],
                        action_data={"type": "weather_weakness"},
                        result_data={"weather": self.weather_effects['name'], "move_type": move_type}
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
        
    def switch_veramon(self, user_id: str, new_slot: int) -> Dict[str, Any]:
        """Switch a player's active Veramon."""
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        if user_id != self.current_turn:
            return {"success": False, "message": "Not your turn"}
            
        if user_id not in self.veramon:
            return {"success": False, "message": "No Veramon available"}
            
        if new_slot < 0 or new_slot >= 6 or self.veramon[user_id][new_slot] is None:
            return {"success": False, "message": "Invalid Veramon slot"}
            
        if self.veramon[user_id][new_slot].current_hp <= 0:
            return {"success": False, "message": "Cannot switch to fainted Veramon"}
            
        old_slot = self.active_veramon.get(user_id)
        self.active_veramon[user_id] = new_slot
        self.updated_at = datetime.utcnow().isoformat()
        
        # Log the switch
        self._add_log_entry(
            action_type=ActionType.SWITCH,
            actor_id=user_id,
            target_ids=[],
            action_data={"old_slot": old_slot, "new_slot": new_slot},
            result_data={"success": True}
        )
        
        # Switching uses a turn
        self._advance_turn()
        
        return {
            "success": True, 
            "message": f"Switched to {self.veramon[user_id][new_slot].display_name}",
            "next_turn": self.current_turn
        }
        
    def use_item(self, user_id: str, item_id: str, target_id: str, target_slot: int = None) -> Dict[str, Any]:
        """Use an item in battle."""
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        if user_id != self.current_turn:
            return {"success": False, "message": "Not your turn"}
            
        # Item effects would be implemented here
        # For simplicity, we'll just log it and advance the turn
        
        self._add_log_entry(
            action_type=ActionType.ITEM,
            actor_id=user_id,
            target_ids=[target_id],
            action_data={"item_id": item_id, "target_slot": target_slot},
            result_data={"success": True}
        )
        
        self._advance_turn()
        
        return {"success": True, "message": "Item used", "next_turn": self.current_turn}
        
    def attempt_flee(self, user_id: str) -> Dict[str, Any]:
        """Attempt to flee from a PVE battle."""
        if self.status != BattleStatus.ACTIVE:
            return {"success": False, "message": "Battle is not active"}
            
        if user_id != self.current_turn:
            return {"success": False, "message": "Not your turn"}
            
        if self.battle_type != BattleType.PVE:
            return {"success": False, "message": "Cannot flee from PVP battles"}
            
        # For PVE, 50% chance to flee
        flee_success = random.random() < 0.5
        
        self._add_log_entry(
            action_type=ActionType.FLEE,
            actor_id=user_id,
            target_ids=[],
            action_data={},
            result_data={"success": flee_success}
        )
        
        if flee_success:
            self.status = BattleStatus.CANCELLED
            self.updated_at = datetime.utcnow().isoformat()
            return {"success": True, "message": "Successfully fled from battle"}
        
        # Failed to flee, lose the turn
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
            
        self.current_turn = self.turn_order[next_index]
        self.updated_at = datetime.utcnow().isoformat()
        
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
        """Convert battle state to a dictionary for storage."""
        return {
            "battle_id": self.battle_id,
            "battle_type": self.battle_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "host_id": self.host_id,
            "teams": self.teams,
            "participants": {
                user_id: {
                    **data,
                    "status": data["status"].value if isinstance(data["status"], ParticipantStatus) else data["status"]
                }
                for user_id, data in self.participants.items()
            },
            "veramon": {
                user_id: [v.to_dict() if v is not None else None for v in veramon_list]
                for user_id, veramon_list in self.veramon.items()
            },
            "active_veramon": self.active_veramon,
            "turn_order": self.turn_order,
            "current_turn": self.current_turn,
            "turn_number": self.turn_number,
            "winner_id": self.winner_id,
            "battle_log": self.battle_log,
            "expiry_time": self.expiry_time,
            "weather_effects": self.weather_effects
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Battle':
        """Create a Battle instance from a dictionary."""
        battle = cls(
            battle_id=data["battle_id"],
            battle_type=BattleType(data["battle_type"]),
            host_id=data["host_id"],
            teams=data["teams"],
            expiry_minutes=0  # Not needed since we're loading from existing data
        )
        
        battle.status = BattleStatus(data["status"])
        battle.created_at = data["created_at"]
        battle.updated_at = data["updated_at"]
        battle.participants = {
            user_id: {
                **participant_data,
                "status": ParticipantStatus(participant_data["status"])
            }
            for user_id, participant_data in data["participants"].items()
        }
        
        # We'd need to reconstruct Veramon objects here
        # This would require loading the appropriate data
        
        battle.active_veramon = data["active_veramon"]
        battle.turn_order = data["turn_order"]
        battle.current_turn = data["current_turn"]
        battle.turn_number = data["turn_number"]
        battle.winner_id = data["winner_id"]
        battle.battle_log = data["battle_log"]
        battle.expiry_time = data["expiry_time"]
        battle.weather_effects = data.get("weather_effects", {})
        
        return battle
