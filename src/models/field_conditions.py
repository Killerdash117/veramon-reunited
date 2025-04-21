"""
Field Conditions for Veramon Reunited Battle System
© 2025 killerdash117 | https://github.com/killerdash117

This module implements battle field conditions that affect all Veramon
in the battle, creating strategic depth and environmental effects.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
import random
import math
from datetime import datetime

class FieldConditionType(Enum):
    """Types of field conditions that can affect a battle."""
    # Weather effects
    SUNNY = "sunny"                 # Powers up fire moves, weakens water moves
    RAINY = "rainy"                 # Powers up water moves, weakens fire moves
    SANDSTORM = "sandstorm"         # Damages all non-rock/ground Veramon each turn
    HAILSTORM = "hailstorm"         # Damages all non-ice Veramon each turn
    FOG = "fog"                     # Reduces accuracy of all moves
    
    # Terrain effects
    GRASSY = "grassy_terrain"       # Heals a small amount of HP each turn, powers up grass moves
    ELECTRIC = "electric_terrain"   # Prevents sleep, powers up electric moves
    MISTY = "misty_terrain"         # Prevents status conditions, powers up fairy moves
    PSYCHIC = "psychic_terrain"     # Prevents priority moves, powers up psychic moves
    
    # Environmental hazards
    SPIKES = "spikes"               # Damages Veramon when switching in (one side only)
    TOXIC_SPIKES = "toxic_spikes"   # Poisons Veramon when switching in (one side only)
    STEALTH_ROCK = "stealth_rock"   # Damages Veramon when switching in based on type effectiveness (one side only)
    
    # Special fields
    TRICK_ROOM = "trick_room"       # Reverses turn order (slower Veramon go first)
    MAGIC_ROOM = "magic_room"       # Prevents items from being used
    WONDER_ROOM = "wonder_room"     # Swaps defense and special defense
    
    @classmethod
    def weather_conditions(cls):
        """Get all weather-based field conditions."""
        return [cls.SUNNY, cls.RAINY, cls.SANDSTORM, cls.HAILSTORM, cls.FOG]
    
    @classmethod
    def terrain_conditions(cls):
        """Get all terrain-based field conditions."""
        return [cls.GRASSY, cls.ELECTRIC, cls.MISTY, cls.PSYCHIC]
    
    @classmethod
    def hazard_conditions(cls):
        """Get all hazard-based field conditions."""
        return [cls.SPIKES, cls.TOXIC_SPIKES, cls.STEALTH_ROCK]
    
    @classmethod
    def room_conditions(cls):
        """Get all room-based field conditions."""
        return [cls.TRICK_ROOM, cls.MAGIC_ROOM, cls.WONDER_ROOM]

class FieldCondition:
    """
    Represents a field condition that affects the battle environment.
    
    Field conditions can affect all Veramon in battle or specific sides,
    creating strategic depth and environmental effects.
    """
    
    def __init__(
        self,
        condition_type: FieldConditionType,
        duration: int = 5,
        intensity: int = 1,
        side_id: Optional[str] = None,  # None means affects both sides
        source_id: Optional[str] = None
    ):
        self.type = condition_type
        self.duration = duration
        self.intensity = max(1, min(3, intensity))  # Clamp intensity between 1-3
        self.side_id = side_id
        self.source_id = source_id  # ID of the Veramon that set up this condition
        self.created_at_turn = 0  # Will be set when applied
        self.last_proc_turn = 0   # Last turn this condition activated
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert field condition to a dictionary representation.
        
        Returns:
            Dictionary representation of the field condition
        """
        return {
            "type": self.type.value,
            "duration": self.duration,
            "intensity": self.intensity,
            "side_id": self.side_id,
            "source_id": self.source_id,
            "created_at_turn": self.created_at_turn,
            "last_proc_turn": self.last_proc_turn
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldCondition":
        """
        Create a field condition from a dictionary representation.
        
        Args:
            data: Dictionary representation of the field condition
            
        Returns:
            FieldCondition instance
        """
        condition_type = FieldConditionType(data["type"])
        condition = cls(
            condition_type=condition_type,
            duration=data.get("duration", 5),
            intensity=data.get("intensity", 1),
            side_id=data.get("side_id"),
            source_id=data.get("source_id")
        )
        condition.created_at_turn = data.get("created_at_turn", 0)
        condition.last_proc_turn = data.get("last_proc_turn", 0)
        return condition
    
    def is_expired(self, current_turn: int) -> bool:
        """
        Check if the field condition has expired.
        
        Args:
            current_turn: Current battle turn number
            
        Returns:
            True if expired, False otherwise
        """
        if self.duration <= 0:
            return False  # Permanent condition
            
        turns_active = current_turn - self.created_at_turn
        return turns_active >= self.duration
    
    def affects_side(self, side_id: str) -> bool:
        """
        Check if this condition affects a specific side.
        
        Args:
            side_id: Side ID to check
            
        Returns:
            True if condition affects this side, False otherwise
        """
        # If no side specified, affects everyone
        if self.side_id is None:
            return True
            
        return self.side_id == side_id
    
    def get_turn_effect(self, current_turn: int, veramon_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the effect to apply at the start/end of the turn.
        
        Args:
            current_turn: Current battle turn number
            veramon_data: Data about the affected Veramon
            
        Returns:
            Dictionary with effect details
        """
        # Skip if already processed this turn
        if self.last_proc_turn == current_turn:
            return {}
            
        self.last_proc_turn = current_turn
        
        # Return appropriate effect based on type
        if self.type == FieldConditionType.SANDSTORM:
            # Sandstorm damages non-Rock/Ground types
            veramon_types = veramon_data.get("types", [])
            if "rock" not in veramon_types and "ground" not in veramon_types:
                damage = max(1, math.floor(veramon_data["max_hp"] * 0.0625))
                return {
                    "damage": damage,
                    "message": "The sandstorm caused damage!"
                }
                
        elif self.type == FieldConditionType.HAILSTORM:
            # Hailstorm damages non-Ice types
            veramon_types = veramon_data.get("types", [])
            if "ice" not in veramon_types:
                damage = max(1, math.floor(veramon_data["max_hp"] * 0.0625))
                return {
                    "damage": damage,
                    "message": "The hailstorm caused damage!"
                }
                
        elif self.type == FieldConditionType.GRASSY:
            # Grassy terrain heals a bit each turn
            heal_amount = max(1, math.floor(veramon_data["max_hp"] * 0.0625))
            return {
                "heal": heal_amount,
                "message": "The grassy terrain restored some HP!"
            }
            
        # Return empty dict for conditions that don't have turn effects
        return {}
    
    def get_move_modifier(self, move_data: Dict[str, Any]) -> float:
        """
        Get the damage multiplier for a move based on the field condition.
        
        Args:
            move_data: Move data containing type and other attributes
            
        Returns:
            Multiplier to apply to move damage (1.0 means no change)
        """
        move_type = move_data.get("type", "normal").lower()
        
        # Weather effects on move types
        if self.type == FieldConditionType.SUNNY:
            if move_type == "fire":
                return 1.5
            elif move_type == "water":
                return 0.5
                
        elif self.type == FieldConditionType.RAINY:
            if move_type == "water":
                return 1.5
            elif move_type == "fire":
                return 0.5
                
        # Terrain effects on move types
        elif self.type == FieldConditionType.GRASSY and move_type == "grass":
            return 1.3
            
        elif self.type == FieldConditionType.ELECTRIC and move_type == "electric":
            return 1.3
            
        elif self.type == FieldConditionType.MISTY and move_type == "fairy":
            return 1.3
            
        elif self.type == FieldConditionType.PSYCHIC and move_type == "psychic":
            return 1.3
            
        # Default: no change
        return 1.0
    
    def get_accuracy_modifier(self, move_data: Dict[str, Any]) -> float:
        """
        Get the accuracy multiplier for a move based on the field condition.
        
        Args:
            move_data: Move data containing accuracy and other attributes
            
        Returns:
            Multiplier to apply to move accuracy (1.0 means no change)
        """
        # Fog reduces accuracy
        if self.type == FieldConditionType.FOG:
            return 0.7  # 70% of normal accuracy
            
        # Default: no change
        return 1.0
    
    def can_apply_status(self, status_type: str, veramon_data: Dict[str, Any]) -> bool:
        """
        Check if a status effect can be applied given this field condition.
        
        Args:
            status_type: Type of status effect
            veramon_data: Data about the target Veramon
            
        Returns:
            True if status can be applied, False if prevented
        """
        # Misty terrain prevents status conditions
        if self.type == FieldConditionType.MISTY:
            return False
            
        # Electric terrain prevents sleep
        if self.type == FieldConditionType.ELECTRIC and status_type == "sleep":
            return False
            
        # Default: status can be applied
        return True
    
    def get_switch_in_effect(self, veramon_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the effect to apply when a Veramon switches into battle.
        
        Args:
            veramon_data: Data about the switching Veramon
            
        Returns:
            Dictionary with effect details
        """
        if self.type == FieldConditionType.SPIKES:
            # Damage based on intensity (layers)
            damage_percent = 0.0625 * self.intensity  # 6.25% / 12.5% / 18.75%
            damage = max(1, math.floor(veramon_data["max_hp"] * damage_percent))
            return {
                "damage": damage,
                "message": f"The spikes caused {damage} damage!"
            }
            
        elif self.type == FieldConditionType.TOXIC_SPIKES:
            # Poison the Veramon unless it's a Poison type
            veramon_types = veramon_data.get("types", [])
            if "poison" not in veramon_types:
                return {
                    "status": "poison",
                    "message": "The toxic spikes poisoned it!"
                }
                
        elif self.type == FieldConditionType.STEALTH_ROCK:
            # Damage based on type effectiveness
            # This is a simplified version - would normally check type chart
            veramon_types = veramon_data.get("types", [])
            
            # Basic multiplier based on rock-type effectiveness
            multiplier = 1.0
            for vtype in veramon_types:
                if vtype in ["fire", "flying", "ice", "bug"]:
                    multiplier *= 2.0  # Weak to rock
                elif vtype in ["fighting", "ground", "steel"]:
                    multiplier *= 0.5  # Resistant to rock
                    
            damage = max(1, math.floor(veramon_data["max_hp"] * 0.125 * multiplier))
            return {
                "damage": damage,
                "message": f"The stealth rocks caused {damage} damage!"
            }
            
        # Default: no effect
        return {}

class FieldManager:
    """
    Manager class for handling all field conditions in a battle.
    """
    
    def __init__(self):
        self.conditions: List[FieldCondition] = []
        
    def add_condition(
        self,
        condition_type: FieldConditionType,
        current_turn: int,
        duration: int = 5,
        intensity: int = 1,
        side_id: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> (bool, str):
        """
        Add a field condition to the battle.
        
        Args:
            condition_type: Type of condition to add
            current_turn: Current battle turn
            duration: Duration in turns
            intensity: Condition intensity/potency
            side_id: ID of the affected side (None for both sides)
            source_id: ID of the source Veramon
            
        Returns:
            Tuple of (success, message)
        """
        # Check for existing contradictory conditions
        if condition_type in FieldConditionType.weather_conditions():
            # Remove existing weather conditions
            for condition in self.conditions[:]:
                if condition.type in FieldConditionType.weather_conditions():
                    self.conditions.remove(condition)
                    
        elif condition_type in FieldConditionType.terrain_conditions():
            # Remove existing terrain conditions
            for condition in self.conditions[:]:
                if condition.type in FieldConditionType.terrain_conditions():
                    self.conditions.remove(condition)
        
        # Check for existing condition of same type
        for i, condition in enumerate(self.conditions):
            if condition.type == condition_type and condition.side_id == side_id:
                # Update existing condition if more intense
                if intensity > condition.intensity:
                    self.conditions[i].intensity = intensity
                
                # Extend duration
                self.conditions[i].duration = max(condition.duration, duration)
                
                # Update creation turn if needed
                self.conditions[i].created_at_turn = current_turn
                
                return True, f"The {condition_type.value} intensified!"
        
        # Add new condition
        condition = FieldCondition(
            condition_type=condition_type,
            duration=duration,
            intensity=intensity,
            side_id=side_id,
            source_id=source_id
        )
        condition.created_at_turn = current_turn
        self.conditions.append(condition)
        
        # Return success message
        if condition_type == FieldConditionType.SUNNY:
            return True, "The sunlight became strong!"
        elif condition_type == FieldConditionType.RAINY:
            return True, "It started to rain!"
        elif condition_type == FieldConditionType.SANDSTORM:
            return True, "A sandstorm kicked up!"
        elif condition_type == FieldConditionType.HAILSTORM:
            return True, "It started to hail!"
        elif condition_type == FieldConditionType.FOG:
            return True, "The battlefield became covered in fog!"
        elif condition_type == FieldConditionType.GRASSY:
            return True, "Grass grew across the battlefield!"
        elif condition_type == FieldConditionType.ELECTRIC:
            return True, "Electricity surged across the ground!"
        elif condition_type == FieldConditionType.MISTY:
            return True, "Mist swirled around the field!"
        elif condition_type == FieldConditionType.PSYCHIC:
            return True, "The battlefield became strange!"
        elif condition_type == FieldConditionType.SPIKES:
            return True, "Spikes were scattered on the ground!"
        elif condition_type == FieldConditionType.TOXIC_SPIKES:
            return True, "Poison spikes were scattered on the ground!"
        elif condition_type == FieldConditionType.STEALTH_ROCK:
            return True, "Pointed stones float in the air!"
        elif condition_type == FieldConditionType.TRICK_ROOM:
            return True, "The dimensions became twisted!"
        elif condition_type == FieldConditionType.MAGIC_ROOM:
            return True, "Items became unusable!"
        elif condition_type == FieldConditionType.WONDER_ROOM:
            return True, "Defense and special defense were swapped!"
        else:
            return True, f"The field changed to {condition_type.value}!"
    
    def remove_condition(self, condition_type: FieldConditionType, side_id: Optional[str] = None) -> bool:
        """
        Remove a specific field condition.
        
        Args:
            condition_type: Type of condition to remove
            side_id: ID of the side (None to remove from all sides)
            
        Returns:
            True if condition was removed, False if not found
        """
        for i, condition in enumerate(self.conditions):
            if condition.type == condition_type:
                if side_id is None or condition.side_id == side_id:
                    self.conditions.pop(i)
                    return True
        return False
    
    def has_condition(self, condition_type: FieldConditionType, side_id: Optional[str] = None) -> bool:
        """
        Check if a specific field condition is active.
        
        Args:
            condition_type: Type of condition to check for
            side_id: ID of the side to check (None to check for any side)
            
        Returns:
            True if condition is active, False otherwise
        """
        for condition in self.conditions:
            if condition.type == condition_type:
                if side_id is None or condition.side_id == side_id or condition.side_id is None:
                    return True
        return False
    
    def get_condition(self, condition_type: FieldConditionType, side_id: Optional[str] = None) -> Optional[FieldCondition]:
        """
        Get a specific field condition if active.
        
        Args:
            condition_type: Type of condition to get
            side_id: ID of the side (None to get condition for any side)
            
        Returns:
            FieldCondition if found, None otherwise
        """
        for condition in self.conditions:
            if condition.type == condition_type:
                if side_id is None or condition.side_id == side_id or condition.side_id is None:
                    return condition
        return None
    
    def process_turn_start(self, current_turn: int, all_veramon: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process field conditions at the start of a turn.
        
        Args:
            current_turn: Current battle turn
            all_veramon: Dictionary of veramon data by ID
            
        Returns:
            Dictionary of {veramon_id: [effect_results]}
        """
        results = {veramon_id: [] for veramon_id in all_veramon}
        
        for condition in self.conditions[:]:  # Make a copy to safely modify during iteration
            # Check if condition has expired
            if condition.is_expired(current_turn):
                self.conditions.remove(condition)
                
                # Add expiry message to all Veramon
                expiry_result = {
                    "type": "condition_expired",
                    "condition": condition.type.value,
                    "message": f"The {condition.type.value} condition ended!"
                }
                
                for veramon_id in results:
                    results[veramon_id].append(expiry_result)
                    
                continue
            
            # Process turn effects for Veramon
            for veramon_id, veramon_data in all_veramon.items():
                # Check if this condition affects this Veramon's side
                side_id = veramon_data.get("side_id")
                if not condition.affects_side(side_id):
                    continue
                    
                # Get effect for this Veramon
                effect_result = condition.get_turn_effect(current_turn, veramon_data)
                
                if effect_result:
                    effect_result["condition"] = condition.type.value
                    results[veramon_id].append(effect_result)
        
        return results
    
    def process_turn_end(self, current_turn: int) -> List[Dict[str, Any]]:
        """
        Process field conditions at the end of a turn.
        
        Args:
            current_turn: Current battle turn
            
        Returns:
            List of condition updates
        """
        results = []
        
        # Update turn counters and check for expiring conditions
        for condition in self.conditions[:]:  # Make a copy to safely modify during iteration
            if condition.is_expired(current_turn):
                self.conditions.remove(condition)
                results.append({
                    "type": "condition_expired",
                    "condition": condition.type.value,
                    "message": f"The {condition.type.value} condition faded away!"
                })
                
        return results
    
    def get_move_modifiers(self, move_data: Dict[str, Any], user_side_id: str) -> Dict[str, float]:
        """
        Get all modifiers for a move from active field conditions.
        
        Args:
            move_data: Move data containing type and attributes
            user_side_id: Side ID of the move user
            
        Returns:
            Dictionary of {modifier_type: value}
        """
        modifiers = {
            "damage": 1.0,
            "accuracy": 1.0,
            "priority": 0  # Additive for priority
        }
        
        for condition in self.conditions:
            # Check global conditions or conditions affecting the user's side
            if condition.side_id is None or condition.side_id == user_side_id:
                # Apply damage modifier
                damage_mod = condition.get_move_modifier(move_data)
                modifiers["damage"] *= damage_mod
                
                # Apply accuracy modifier
                accuracy_mod = condition.get_accuracy_modifier(move_data)
                modifiers["accuracy"] *= accuracy_mod
                
                # Special case for Trick Room
                if condition.type == FieldConditionType.TRICK_ROOM:
                    # This is handled elsewhere by reversing turn order
                    pass
                
                # Special case for Psychic Terrain
                if condition.type == FieldConditionType.PSYCHIC:
                    # Disable priority moves (+1 and higher)
                    if move_data.get("priority", 0) > 0:
                        modifiers["priority"] = 0
                        
        return modifiers
    
    def process_switch_in(self, veramon_id: str, veramon_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process field conditions when a Veramon switches into battle.
        
        Args:
            veramon_id: ID of the switching Veramon
            veramon_data: Data about the Veramon
            
        Returns:
            List of effect results
        """
        results = []
        side_id = veramon_data.get("side_id")
        
        for condition in self.conditions:
            # Only process hazards that affect this Veramon's side
            if condition.type in FieldConditionType.hazard_conditions():
                if condition.side_id == side_id:
                    effect_result = condition.get_switch_in_effect(veramon_data)
                    
                    if effect_result:
                        effect_result["condition"] = condition.type.value
                        results.append(effect_result)
                        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert all field conditions to a dictionary representation.
        
        Returns:
            Dictionary of conditions
        """
        return {
            "conditions": [condition.to_dict() for condition in self.conditions]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldManager":
        """
        Create a field manager from a dictionary.
        
        Args:
            data: Dictionary of conditions
            
        Returns:
            FieldManager instance
        """
        manager = cls()
        
        if "conditions" in data:
            for condition_data in data["conditions"]:
                condition = FieldCondition.from_dict(condition_data)
                manager.conditions.append(condition)
                
        return manager
