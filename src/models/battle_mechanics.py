"""
Advanced Battle Mechanics for Veramon Reunited
© 2025 killerdash117 | https://github.com/killerdash117

This module integrates the status effects and field conditions systems
with the core battle mechanics, providing strategic depth to battles.
"""

import random
import math
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum

from src.models.status_effects import StatusEffectManager, StatusEffectType
from src.models.field_conditions import FieldManager, FieldConditionType

# Set up logging
logger = logging.getLogger("battle_mechanics")

class BattleItemType(Enum):
    """Types of items that can be used in battle."""
    HEALING = "healing"           # Restores HP
    STAT_BOOST = "stat_boost"     # Boosts a stat
    STATUS_CURE = "status_cure"   # Cures status conditions
    BATTLE_ENHANCER = "enhancer"  # Enhances specific moves
    HELD_ITEM = "held"            # Passive effect when held
    SPECIAL = "special"           # Special effect items

class BattleMechanics:
    """
    Integrates advanced battle systems with the core battle logic.
    
    This class connects status effects, field conditions, battle items,
    and other advanced mechanics to the main battle system.
    """
    
    def __init__(self, battle_data: Dict[str, Any]):
        self.battle_data = battle_data
        self.status_managers = {}  # {veramon_id: StatusEffectManager}
        self.field_manager = FieldManager()
        self.battle_items = {}     # {veramon_id: [items]}
        self.critical_modifiers = {}  # {veramon_id: modifier}
        self.used_zmoves = set()   # Veramon IDs that used their Z-move
        
        # Initialize status managers for each Veramon
        self._initialize_status_managers()
        
        # Set up logger
        self.battle_logger = logging.getLogger("battle")
    
    def _initialize_status_managers(self):
        """Initialize status effect managers for all Veramon in battle."""
        # Get all Veramon from battle data
        all_veramon = self._get_all_battle_veramon()
        
        for veramon_id, veramon_data in all_veramon.items():
            self.status_managers[veramon_id] = StatusEffectManager()
            self.critical_modifiers[veramon_id] = 1.0
    
    def _get_all_battle_veramon(self) -> Dict[str, Dict[str, Any]]:
        """
        Get data for all Veramon currently in the battle.
        
        Returns:
            Dictionary mapping Veramon ID to data
        """
        all_veramon = {}
        
        # Process all teams
        for team in self.battle_data.get("teams", []):
            team_id = team.get("team_id")
            
            for participant in team.get("participants", []):
                for veramon in participant.get("veramon", []):
                    veramon_id = veramon.get("veramon_id")
                    
                    if veramon_id:
                        all_veramon[veramon_id] = {
                            **veramon,
                            "side_id": team_id
                        }
        
        return all_veramon
    
    def _get_active_veramon(self) -> Dict[str, Dict[str, Any]]:
        """
        Get data for all active Veramon in the battle.
        
        Returns:
            Dictionary mapping Veramon ID to data
        """
        active_veramon = {}
        
        # Process all teams
        for team in self.battle_data.get("teams", []):
            team_id = team.get("team_id")
            
            for participant in team.get("participants", []):
                active_id = participant.get("active_veramon_id")
                
                if active_id:
                    for veramon in participant.get("veramon", []):
                        if veramon.get("veramon_id") == active_id:
                            active_veramon[active_id] = {
                                **veramon,
                                "side_id": team_id,
                                "participant_id": participant.get("participant_id")
                            }
        
        return active_veramon
    
    def process_turn_start(self, current_turn: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process mechanics at the start of a battle turn.
        
        Args:
            current_turn: Current battle turn number
            
        Returns:
            Dictionary of effects per Veramon ID
        """
        results = {}
        
        # Get all active Veramon
        active_veramon = self._get_active_veramon()
        
        # Process field conditions first
        field_results = self.field_manager.process_turn_start(current_turn, active_veramon)
        
        # Process status effects for each active Veramon
        for veramon_id, veramon_data in active_veramon.items():
            results[veramon_id] = []
            
            # Add field condition results
            if veramon_id in field_results:
                results[veramon_id].extend(field_results[veramon_id])
            
            # Process status effects
            if veramon_id in self.status_managers:
                status_results = self.status_managers[veramon_id].process_turn_start(
                    current_turn, veramon_data
                )
                results[veramon_id].extend(status_results)
        
        return results
    
    def process_turn_end(self, current_turn: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process mechanics at the end of a battle turn.
        
        Args:
            current_turn: Current battle turn number
            
        Returns:
            Dictionary of effects per Veramon ID
        """
        results = {}
        
        # Get all active Veramon
        active_veramon = self._get_active_veramon()
        
        # Process field conditions
        field_results = self.field_manager.process_turn_end(current_turn)
        
        # Add field results to all active Veramon
        for veramon_id in active_veramon:
            results[veramon_id] = field_results.copy()
            
            # Process status effects
            if veramon_id in self.status_managers:
                status_results = self.status_managers[veramon_id].process_turn_end(current_turn)
                results[veramon_id].extend(status_results)
        
        return results
    
    def can_act(self, veramon_id: str) -> (bool, str):
        """
        Check if a Veramon can act based on its status effects.
        
        Args:
            veramon_id: ID of the Veramon to check
            
        Returns:
            Tuple of (can_act, message)
        """
        # Veramon needs to have a status manager
        if veramon_id not in self.status_managers:
            return True, ""
            
        # Get Veramon data
        all_veramon = self._get_all_battle_veramon()
        veramon_data = all_veramon.get(veramon_id, {})
        
        # Check status effects
        return self.status_managers[veramon_id].can_act(veramon_data)
    
    def apply_status_effect(
        self,
        target_id: str,
        effect_type: StatusEffectType,
        current_turn: int,
        duration: int = -1,
        intensity: int = 1,
        source_id: Optional[str] = None
    ) -> (bool, str):
        """
        Apply a status effect to a Veramon.
        
        Args:
            target_id: ID of the target Veramon
            effect_type: Type of effect to apply
            current_turn: Current battle turn
            duration: Duration in turns (-1 for permanent)
            intensity: Effect intensity (1-5)
            source_id: ID of the source Veramon
            
        Returns:
            Tuple of (success, message)
        """
        # Veramon needs to have a status manager
        if target_id not in self.status_managers:
            return False, "Invalid target Veramon!"
            
        # Get target data
        all_veramon = self._get_all_battle_veramon()
        target_data = all_veramon.get(target_id, {})
        target_side = target_data.get("side_id")
        
        # Check if status effects are prevented by field conditions
        for condition in self.field_manager.conditions:
            if condition.affects_side(target_side):
                if not condition.can_apply_status(effect_type.value, target_data):
                    return False, f"The {condition.type.value} prevented the status effect!"
        
        # Apply the effect
        return self.status_managers[target_id].add_effect(
            effect_type, current_turn, duration, intensity, source_id
        )
    
    def apply_field_condition(
        self,
        condition_type: FieldConditionType,
        current_turn: int,
        duration: int = 5,
        intensity: int = 1,
        side_id: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> (bool, str):
        """
        Apply a field condition to the battle.
        
        Args:
            condition_type: Type of condition to apply
            current_turn: Current battle turn
            duration: Duration in turns
            intensity: Condition intensity (1-3)
            side_id: ID of the affected side (None for both sides)
            source_id: ID of the source Veramon
            
        Returns:
            Tuple of (success, message)
        """
        return self.field_manager.add_condition(
            condition_type, current_turn, duration, intensity, side_id, source_id
        )
    
    def modify_attack(
        self,
        attacker_id: str,
        defender_id: str,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply all modifiers to an attack based on status effects and field conditions.
        
        Args:
            attacker_id: ID of the attacking Veramon
            defender_id: ID of the defending Veramon
            move_data: Data for the move being used
            
        Returns:
            Dictionary with all modifiers and effects
        """
        # Get Veramon data
        all_veramon = self._get_all_battle_veramon()
        attacker_data = all_veramon.get(attacker_id, {})
        defender_data = all_veramon.get(defender_id, {})
        
        attacker_side = attacker_data.get("side_id")
        defender_side = defender_data.get("side_id")
        
        result = {
            "base_damage": move_data.get("power", 0),
            "final_damage": move_data.get("power", 0),
            "accuracy": move_data.get("accuracy", 95),
            "critical_chance": 6.25,  # Base 1/16 chance
            "effects": [],
            "stat_mods": {
                "attack": 1.0,
                "defense": 1.0,
                "speed": 1.0,
                "special": 1.0
            }
        }
        
        # Apply attacker status effects
        if attacker_id in self.status_managers:
            attacker_mods = self.status_managers[attacker_id].get_stat_modifiers()
            
            # Apply stat mods to result
            for stat, mod in attacker_mods.items():
                if stat in result["stat_mods"]:
                    result["stat_mods"][stat] *= mod
                    
            # Check if confused
            can_act, message = self.status_managers[attacker_id].can_act(attacker_data)
            if message == "confusion_self_damage":
                # Special case for confusion - self damage
                result["effects"].append({
                    "type": "confusion_self_damage",
                    "message": f"{attacker_data.get('name', 'The Veramon')} hurt itself in confusion!"
                })
                
                # Calculate confusion damage
                confusion_damage = max(1, math.floor(attacker_data.get("max_hp", 100) * 0.125))
                result["final_damage"] = confusion_damage
                result["target_override"] = attacker_id  # Target self
        
        # Apply defender status effects
        if defender_id in self.status_managers:
            defender_mods = self.status_managers[defender_id].get_stat_modifiers()
            
            # Apply stat mods to result
            for stat, mod in defender_mods.items():
                if stat in result["stat_mods"]:
                    # For defender, we invert the modifier
                    # Higher defense = less damage
                    if stat in ["defense", "special"]:
                        result["stat_mods"][stat] /= mod
        
        # Apply field condition modifiers
        field_mods = self.field_manager.get_move_modifiers(move_data, attacker_side)
        
        # Apply damage modifier from field
        if "damage" in field_mods:
            result["final_damage"] = math.floor(result["final_damage"] * field_mods["damage"])
            
            if field_mods["damage"] != 1.0:
                # Add effect to show the modification
                effect_type = "increased" if field_mods["damage"] > 1.0 else "decreased"
                condition_name = self._get_active_condition_name(attacker_side)
                
                result["effects"].append({
                    "type": f"damage_{effect_type}",
                    "message": f"The {condition_name} {effect_type} the power of the move!"
                })
        
        # Apply accuracy modifier from field
        if "accuracy" in field_mods:
            result["accuracy"] = math.floor(result["accuracy"] * field_mods["accuracy"])
            
            if field_mods["accuracy"] != 1.0:
                # Add effect to show the modification
                effect_type = "increased" if field_mods["accuracy"] > 1.0 else "decreased"
                condition_name = self._get_active_condition_name(attacker_side)
                
                result["effects"].append({
                    "type": f"accuracy_{effect_type}",
                    "message": f"The {condition_name} {effect_type} the accuracy of the move!"
                })
        
        # Apply critical hit modifiers
        if attacker_id in self.critical_modifiers:
            result["critical_chance"] *= self.critical_modifiers[attacker_id]
            
        # Apply focus effect if present
        if attacker_id in self.status_managers:
            if self.status_managers[attacker_id].has_effect(StatusEffectType.FOCUS):
                result["critical_chance"] *= 2.0
                result["effects"].append({
                    "type": "focus_boost",
                    "message": f"{attacker_data.get('name', 'The Veramon')} focused its energy for a critical hit!"
                })
                
                # Remove the focus after use
                self.status_managers[attacker_id].remove_effect(StatusEffectType.FOCUS)
        
        # Apply charged effect if present
        if attacker_id in self.status_managers:
            if self.status_managers[attacker_id].has_effect(StatusEffectType.CHARGED):
                result["final_damage"] = math.floor(result["final_damage"] * 1.5)
                result["effects"].append({
                    "type": "charged_boost",
                    "message": f"{attacker_data.get('name', 'The Veramon')} unleashed its charged energy!"
                })
                
                # Remove the charged effect after use
                self.status_managers[attacker_id].remove_effect(StatusEffectType.CHARGED)
        
        # Check for move-specific effects
        if "effects" in move_data:
            for effect in move_data["effects"]:
                effect_type = effect.get("type")
                effect_chance = effect.get("chance", 100)
                
                # Only include effects that have a chance to occur
                if random.randint(1, 100) <= effect_chance:
                    # Status effects
                    if effect_type == "status":
                        status_name = effect.get("status")
                        if status_name and hasattr(StatusEffectType, status_name.upper()):
                            status_effect = getattr(StatusEffectType, status_name.upper())
                            result["effects"].append({
                                "type": "apply_status",
                                "status": status_effect.value,
                                "target": effect.get("target", "defender"),
                                "duration": effect.get("duration", -1),
                                "intensity": effect.get("intensity", 1)
                            })
                    
                    # Stat changes
                    elif effect_type == "stat_change":
                        stat = effect.get("stat")
                        change = effect.get("change", 0)
                        target = effect.get("target", "defender")
                        
                        if stat and change:
                            result["effects"].append({
                                "type": "stat_change",
                                "stat": stat,
                                "change": change,
                                "target": target
                            })
                    
                    # Field conditions
                    elif effect_type == "field_condition":
                        condition_name = effect.get("condition")
                        if condition_name and hasattr(FieldConditionType, condition_name.upper()):
                            condition = getattr(FieldConditionType, condition_name.upper())
                            target_side = effect.get("side", None)
                            
                            # Determine which side to affect
                            if target_side == "opponent":
                                target_side = defender_side
                            elif target_side == "user":
                                target_side = attacker_side
                            elif target_side == "both":
                                target_side = None
                                
                            result["effects"].append({
                                "type": "field_condition",
                                "condition": condition.value,
                                "side": target_side,
                                "duration": effect.get("duration", 5),
                                "intensity": effect.get("intensity", 1)
                            })
                    
                    # Other effects
                    elif effect_type == "flinch":
                        result["effects"].append({
                            "type": "flinch",
                            "message": f"{defender_data.get('name', 'The Veramon')} flinched!"
                        })
                        
                    elif effect_type == "critical_boost":
                        result["critical_chance"] *= effect.get("multiplier", 2.0)
                        
                    elif effect_type == "drain":
                        drain_percent = effect.get("percent", 50)
                        result["effects"].append({
                            "type": "drain",
                            "percent": drain_percent,
                            "message": f"{attacker_data.get('name', 'The Veramon')} drained energy!"
                        })
                        
                    elif effect_type == "recoil":
                        recoil_percent = effect.get("percent", 25)
                        result["effects"].append({
                            "type": "recoil",
                            "percent": recoil_percent,
                            "message": f"{attacker_data.get('name', 'The Veramon')} was hurt by recoil!"
                        })
        
        return result
    
    def process_damage(
        self,
        defender_id: str,
        damage: int,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process incoming damage to a Veramon, applying defensive effects.
        
        Args:
            defender_id: ID of the defending Veramon
            damage: Amount of damage
            move_data: Data for the move used
            
        Returns:
            Dictionary with modified damage and effects
        """
        result = {
            "original_damage": damage,
            "final_damage": damage,
            "effects": []
        }
        
        # Apply defensive status effects
        if defender_id in self.status_managers:
            modified_damage, status_effects = self.status_managers[defender_id].modify_incoming_damage(
                damage, move_data.get("type", "normal")
            )
            
            result["final_damage"] = modified_damage
            result["effects"].extend(status_effects)
            
            # Process effects when hit by a move
            hit_effects = self.status_managers[defender_id].on_hit(
                damage, move_data.get("type", "normal")
            )
            result["effects"].extend(hit_effects)
        
        return result
    
    def process_switch(
        self,
        veramon_id: str,
        current_turn: int
    ) -> Dict[str, Any]:
        """
        Process effects when a Veramon switches into battle.
        
        Args:
            veramon_id: ID of the switching Veramon
            current_turn: Current battle turn
            
        Returns:
            Dictionary with switch-in effects
        """
        result = {
            "effects": []
        }
        
        # Get Veramon data
        all_veramon = self._get_all_battle_veramon()
        veramon_data = all_veramon.get(veramon_id, {})
        
        # Process hazards and other switch-in effects
        if veramon_data:
            switch_effects = self.field_manager.process_switch_in(veramon_id, veramon_data)
            
            for effect in switch_effects:
                # Handle damage
                if "damage" in effect:
                    result["damage"] = effect["damage"]
                
                # Handle status effects
                if "status" in effect:
                    status_name = effect["status"].upper()
                    if hasattr(StatusEffectType, status_name):
                        status_effect = getattr(StatusEffectType, status_name)
                        
                        # Apply the status
                        success, message = self.apply_status_effect(
                            veramon_id, status_effect, current_turn
                        )
                        
                        if success:
                            result["effects"].append({
                                "type": "status_applied",
                                "status": status_effect.value,
                                "message": message
                            })
                
                # Add message
                if "message" in effect:
                    result["effects"].append({
                        "type": "switch_effect",
                        "condition": effect.get("condition", "unknown"),
                        "message": effect["message"]
                    })
        
        return result
    
    def use_item(
        self,
        user_id: str,
        target_id: str,
        item_data: Dict[str, Any],
        current_turn: int
    ) -> Dict[str, Any]:
        """
        Use a battle item.
        
        Args:
            user_id: ID of the Veramon/trainer using the item
            target_id: ID of the target Veramon
            item_data: Data for the item
            current_turn: Current battle turn
            
        Returns:
            Dictionary with item effects
        """
        result = {
            "success": True,
            "effects": []
        }
        
        item_type = item_data.get("type", "unknown")
        item_name = item_data.get("name", "Unknown Item")
        
        # Process different item types
        if item_type == "healing":
            # Healing items
            heal_amount = item_data.get("heal_amount", 0)
            heal_percent = item_data.get("heal_percent", 0)
            
            # Get target data
            all_veramon = self._get_all_battle_veramon()
            target_data = all_veramon.get(target_id, {})
            max_hp = target_data.get("max_hp", 100)
            
            # Calculate final healing
            if heal_percent > 0:
                heal_amount = max(heal_amount, math.floor(max_hp * (heal_percent / 100)))
                
            result["effects"].append({
                "type": "healing",
                "amount": heal_amount,
                "message": f"{item_name} restored {heal_amount} HP!"
            })
            
        elif item_type == "status_cure":
            # Status curing items
            cure_all = item_data.get("cure_all", False)
            status_list = item_data.get("status_list", [])
            
            cured_something = False
            
            # Check if target has a status manager
            if target_id in self.status_managers:
                if cure_all:
                    # Remove all status effects
                    for effect_type in StatusEffectType:
                        if self.status_managers[target_id].remove_effect(effect_type):
                            cured_something = True
                else:
                    # Remove specific status effects
                    for status_name in status_list:
                        if hasattr(StatusEffectType, status_name.upper()):
                            status_effect = getattr(StatusEffectType, status_name.upper())
                            if self.status_managers[target_id].remove_effect(status_effect):
                                cured_something = True
                                
                if cured_something:
                    result["effects"].append({
                        "type": "status_cure",
                        "message": f"{item_name} cured the status condition!"
                    })
                else:
                    result["success"] = False
                    result["message"] = "But it had no effect!"
            else:
                result["success"] = False
                result["message"] = "But it had no effect!"
                
        elif item_type == "stat_boost":
            # Stat boosting items
            stat = item_data.get("stat", "attack")
            boost_amount = item_data.get("boost_amount", 1)
            
            # Create a status effect for the stat boost
            status_type = None
            
            if stat == "attack":
                status_type = StatusEffectType.ATK_UP
            elif stat == "defense":
                status_type = StatusEffectType.DEF_UP
            elif stat == "speed":
                status_type = StatusEffectType.SPD_UP
                
            if status_type and target_id in self.status_managers:
                success, message = self.apply_status_effect(
                    target_id, status_type, current_turn, 
                    duration=5, intensity=boost_amount
                )
                
                if success:
                    result["effects"].append({
                        "type": "stat_boost",
                        "stat": stat,
                        "message": f"{item_name} boosted {stat}!"
                    })
                else:
                    result["success"] = False
                    result["message"] = message
            else:
                result["success"] = False
                result["message"] = "But it had no effect!"
                
        elif item_type == "battle_enhancer":
            # Items that enhance battle abilities
            enhancer_type = item_data.get("enhancer_type", "")
            
            if enhancer_type == "critical":
                # Increase critical hit rate
                self.critical_modifiers[target_id] = 2.0
                result["effects"].append({
                    "type": "critical_boost",
                    "message": f"{item_name} increased the critical hit ratio!"
                })
                
            elif enhancer_type == "focus":
                # Apply focus effect for guaranteed critical
                if target_id in self.status_managers:
                    success, message = self.apply_status_effect(
                        target_id, StatusEffectType.FOCUS, current_turn
                    )
                    
                    if success:
                        result["effects"].append({
                            "type": "focus",
                            "message": f"{item_name} helped focus for a critical hit!"
                        })
                    else:
                        result["success"] = False
                        result["message"] = message
                else:
                    result["success"] = False
                    result["message"] = "But it had no effect!"
                    
            elif enhancer_type == "accuracy":
                # This would apply an accuracy boost
                # Implemented through move execution logic
                result["effects"].append({
                    "type": "accuracy_boost",
                    "message": f"{item_name} increased accuracy!"
                })
                
        return result
    
    def _get_active_condition_name(self, side_id: Optional[str] = None) -> str:
        """
        Get the name of an active field condition affecting a side.
        
        Args:
            side_id: Side ID to check for conditions
            
        Returns:
            Name of an active condition, or "field" if none found
        """
        # Check for weather conditions first
        for condition_type in FieldConditionType.weather_conditions():
            condition = self.field_manager.get_condition(condition_type, side_id)
            if condition:
                return condition.type.value
                
        # Check for terrain conditions
        for condition_type in FieldConditionType.terrain_conditions():
            condition = self.field_manager.get_condition(condition_type, side_id)
            if condition:
                return condition.type.value
                
        # Default name
        return "field"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert all battle mechanics data to a dictionary representation.
        
        Returns:
            Dictionary of battle mechanics data
        """
        status_data = {}
        for veramon_id, manager in self.status_managers.items():
            status_data[veramon_id] = manager.to_dict()
            
        return {
            "status_effects": status_data,
            "field_conditions": self.field_manager.to_dict(),
            "critical_modifiers": self.critical_modifiers,
            "used_zmoves": list(self.used_zmoves)
        }
    
    @classmethod
    def from_dict(cls, battle_data: Dict[str, Any], mechanics_data: Dict[str, Any]) -> "BattleMechanics":
        """
        Create a battle mechanics instance from a dictionary.
        
        Args:
            battle_data: Core battle data
            mechanics_data: Battle mechanics data
            
        Returns:
            BattleMechanics instance
        """
        mechanics = cls(battle_data)
        
        # Load status effects
        if "status_effects" in mechanics_data:
            for veramon_id, data in mechanics_data["status_effects"].items():
                mechanics.status_managers[veramon_id] = StatusEffectManager.from_dict(data)
                
        # Load field conditions
        if "field_conditions" in mechanics_data:
            mechanics.field_manager = FieldManager.from_dict(mechanics_data["field_conditions"])
            
        # Load critical modifiers
        if "critical_modifiers" in mechanics_data:
            mechanics.critical_modifiers = mechanics_data["critical_modifiers"]
            
        # Load used Z-moves
        if "used_zmoves" in mechanics_data:
            mechanics.used_zmoves = set(mechanics_data["used_zmoves"])
            
        return mechanics
