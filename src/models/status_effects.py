"""
Status Effects for Veramon Reunited Battle System
© 2025 killerdash117 | https://github.com/killerdash117

This module implements a comprehensive status effect system for battles,
including temporary buffs, debuffs, and altered states.
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import random
import math

class StatusEffectType(Enum):
    """Types of status effects that can be applied to Veramon."""
    # Primary status effects
    BURN = "burn"           # Reduces attack and deals damage over time
    POISON = "poison"       # Deals increasing damage over time
    PARALYSIS = "paralysis" # May prevent action and reduces speed
    SLEEP = "sleep"         # Prevents action for a few turns
    FREEZE = "freeze"       # Prevents action until cured or hit with fire
    CONFUSION = "confusion" # May cause self-damage on action
    
    # Secondary status effects
    FLINCH = "flinch"       # Prevents action for one turn
    BOUND = "bound"         # Prevents switching and deals damage
    LEECH = "leech"         # Drains HP each turn
    
    # Stat modifiers
    ATK_UP = "atk_up"       # Increases attack stat
    ATK_DOWN = "atk_down"   # Decreases attack stat
    DEF_UP = "def_up"       # Increases defense stat
    DEF_DOWN = "def_down"   # Decreases defense stat
    SPD_UP = "spd_up"       # Increases speed stat
    SPD_DOWN = "spd_down"   # Decreases speed stat
    
    # Special effects
    SHIELD = "shield"       # Reduces damage from next attack
    CHARGED = "charged"     # Next attack does extra damage
    FOCUS = "focus"         # Next attack has increased critical chance
    CURSE = "curse"         # Takes small damage each turn
    IMMUNITY = "immunity"   # Immune to status effects
    REFLECT = "reflect"     # Reflects a portion of damage
    
    @classmethod
    def primary_effects(cls):
        """Get all primary status effects."""
        return [cls.BURN, cls.POISON, cls.PARALYSIS, cls.SLEEP, cls.FREEZE, cls.CONFUSION]
    
    @classmethod
    def stat_modifiers(cls):
        """Get all stat modifier effects."""
        return [cls.ATK_UP, cls.ATK_DOWN, cls.DEF_UP, cls.DEF_DOWN, cls.SPD_UP, cls.SPD_DOWN]

class StatusEffect:
    """
    Represents a status effect that can be applied to a Veramon in battle.
    
    This class handles effect application, duration, and per-turn effects.
    """
    
    def __init__(
        self,
        effect_type: StatusEffectType,
        duration: int = -1,  # -1 means until battle ends or cured
        intensity: int = 1,
        source_id: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ):
        self.type = effect_type
        self.duration = duration
        self.intensity = max(1, min(5, intensity))  # Clamp intensity between 1-5
        self.source_id = source_id  # ID of the Veramon that caused this effect
        self.custom_data = custom_data or {}
        self.applied_at_turn = 0  # Will be set when applied
        self.last_proc_turn = 0   # Last turn this effect activated
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert status effect to a dictionary representation.
        
        Returns:
            Dictionary representation of the status effect
        """
        return {
            "type": self.type.value,
            "duration": self.duration,
            "intensity": self.intensity,
            "source_id": self.source_id,
            "custom_data": self.custom_data,
            "applied_at_turn": self.applied_at_turn,
            "last_proc_turn": self.last_proc_turn
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatusEffect":
        """
        Create a status effect from a dictionary representation.
        
        Args:
            data: Dictionary representation of the status effect
            
        Returns:
            StatusEffect instance
        """
        effect_type = StatusEffectType(data["type"])
        effect = cls(
            effect_type=effect_type,
            duration=data.get("duration", -1),
            intensity=data.get("intensity", 1),
            source_id=data.get("source_id"),
            custom_data=data.get("custom_data", {})
        )
        effect.applied_at_turn = data.get("applied_at_turn", 0)
        effect.last_proc_turn = data.get("last_proc_turn", 0)
        return effect
    
    def is_expired(self, current_turn: int) -> bool:
        """
        Check if the status effect has expired.
        
        Args:
            current_turn: Current battle turn number
            
        Returns:
            True if expired, False otherwise
        """
        if self.duration == -1:
            return False  # Permanent effect
            
        turns_active = current_turn - self.applied_at_turn
        return turns_active >= self.duration
    
    def get_turn_effect(self, current_turn: int, veramon_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the effect to apply at the start/end of the turn.
        
        Args:
            current_turn: Current battle turn number
            veramon_stats: Current stats of the affected Veramon
            
        Returns:
            Dictionary with effect details
        """
        # Skip if already processed this turn
        if self.last_proc_turn == current_turn:
            return {}
            
        self.last_proc_turn = current_turn
        
        # Return appropriate effect based on type
        if self.type == StatusEffectType.BURN:
            damage = max(1, math.floor(veramon_stats["max_hp"] * (0.0625 * self.intensity)))
            return {
                "damage": damage,
                "message": f"The burn caused {damage} damage!",
                "stat_changes": {"attack": -0.1 * self.intensity}
            }
            
        elif self.type == StatusEffectType.POISON:
            # Poison intensifies over time
            turns_active = current_turn - self.applied_at_turn
            modifier = min(1.5, 1 + (turns_active * 0.1))  # Up to 50% increase
            damage = max(1, math.floor(veramon_stats["max_hp"] * (0.075 * self.intensity * modifier)))
            return {
                "damage": damage,
                "message": f"The poison caused {damage} damage!"
            }
            
        elif self.type == StatusEffectType.LEECH:
            damage = max(1, math.floor(veramon_stats["max_hp"] * (0.0625 * self.intensity)))
            return {
                "damage": damage,
                "leech_amount": damage,
                "leech_target": self.source_id,
                "message": f"Energy was drained for {damage} damage!"
            }
            
        elif self.type == StatusEffectType.CURSE:
            damage = max(1, math.floor(veramon_stats["max_hp"] * 0.0625))
            return {
                "damage": damage,
                "message": "The curse sapped some health!"
            }
            
        # Return empty dict for effects that don't have turn effects
        return {}
    
    def can_act(self, veramon_stats: Dict[str, Any]) -> (bool, str):
        """
        Check if the Veramon can act with this status effect.
        
        Args:
            veramon_stats: Current stats of the affected Veramon
            
        Returns:
            Tuple of (can_act, message)
        """
        if self.type == StatusEffectType.SLEEP:
            return False, "It's fast asleep!"
            
        elif self.type == StatusEffectType.FREEZE:
            return False, "It's frozen solid!"
            
        elif self.type == StatusEffectType.FLINCH:
            # Flinch only lasts one turn, so always return that the Veramon can't act
            # The effect will be removed after this check
            return False, "It flinched!"
            
        elif self.type == StatusEffectType.PARALYSIS:
            # Chance of not being able to move based on intensity
            chance = 0.25 * self.intensity  # 25-125% chance
            if random.random() < min(0.75, chance):  # Cap at 75%
                return False, "It's paralyzed and couldn't move!"
                
        elif self.type == StatusEffectType.CONFUSION:
            # Chance of hurting itself based on intensity
            chance = 0.33 * self.intensity  # 33-165% chance
            if random.random() < min(0.75, chance):  # Cap at 75%
                # Return True but with special confusion flag
                return True, "confusion_self_damage"
                
        # Default: can act normally
        return True, ""
    
    def get_stat_modifier(self, stat_name: str) -> float:
        """
        Get the stat modification multiplier for this effect.
        
        Args:
            stat_name: Name of the stat to modify
            
        Returns:
            Multiplier to apply to the stat (1.0 means no change)
        """
        if self.type == StatusEffectType.ATK_UP and stat_name == "attack":
            return 1.0 + (0.2 * self.intensity)  # +20% per intensity
            
        elif self.type == StatusEffectType.ATK_DOWN and stat_name == "attack":
            return 1.0 - (0.2 * self.intensity)  # -20% per intensity
            
        elif self.type == StatusEffectType.DEF_UP and stat_name == "defense":
            return 1.0 + (0.2 * self.intensity)
            
        elif self.type == StatusEffectType.DEF_DOWN and stat_name == "defense":
            return 1.0 - (0.2 * self.intensity)
            
        elif self.type == StatusEffectType.SPD_UP and stat_name == "speed":
            return 1.0 + (0.2 * self.intensity)
            
        elif self.type == StatusEffectType.SPD_DOWN and stat_name == "speed":
            return 1.0 - (0.2 * self.intensity)
            
        elif self.type == StatusEffectType.BURN and stat_name == "attack":
            return 1.0 - (0.1 * self.intensity)  # Burn reduces attack
            
        elif self.type == StatusEffectType.PARALYSIS and stat_name == "speed":
            return 1.0 - (0.25 * self.intensity)  # Paralysis reduces speed
            
        # Default: no change
        return 1.0
    
    def on_hit(self, damage: int, move_type: str) -> (bool, str):
        """
        Process what happens when a Veramon with this effect is hit.
        
        Args:
            damage: Amount of damage taken
            move_type: Type of the move used
            
        Returns:
            Tuple of (effect_removed, message)
        """
        # Some effects can be removed by certain attacks
        if self.type == StatusEffectType.SLEEP:
            # 50% chance to wake up when hit, if damage > 0
            if damage > 0 and random.random() < 0.5:
                return True, "It woke up!"
                
        elif self.type == StatusEffectType.FREEZE:
            # Fire-type moves always thaw
            if move_type == "fire":
                return True, "It thawed out!"
                
            # Other moves have a smaller chance
            if damage > 0 and random.random() < 0.2:
                return True, "It thawed out!"
                
        elif self.type == StatusEffectType.CONFUSION:
            # Hard hits can knock out of confusion
            if damage > 20 and random.random() < 0.3:
                return True, "It snapped out of confusion!"
                
        elif self.type == StatusEffectType.SHIELD:
            # Shield is consumed when hit
            return True, "The shield absorbed some damage!"
            
        elif self.type == StatusEffectType.REFLECT:
            # Reflect stays
            return False, "The attack was partially reflected!"
            
        # Default: effect remains
        return False, ""
    
    def get_damage_modifier(self, incoming_damage: int, move_type: str) -> (int, str):
        """
        Modify incoming damage based on the status effect.
        
        Args:
            incoming_damage: Original damage amount
            move_type: Type of the move used
            
        Returns:
            Tuple of (modified_damage, message)
        """
        # Shield reduces damage
        if self.type == StatusEffectType.SHIELD:
            reduction = min(0.75, 0.25 * self.intensity)  # 25-75% reduction
            reduced_damage = math.floor(incoming_damage * (1 - reduction))
            return reduced_damage, f"The shield reduced damage by {incoming_damage - reduced_damage}!"
            
        # Reflect returns some damage
        elif self.type == StatusEffectType.REFLECT:
            reflection = min(0.5, 0.15 * self.intensity)  # 15-50% reflection
            # The reflection is handled elsewhere, just return a message
            return incoming_damage, f"Reflected {math.floor(incoming_damage * reflection)} damage!"
            
        # Default: no change
        return incoming_damage, ""


class StatusEffectManager:
    """
    Manager class for handling a collection of status effects on a Veramon.
    """
    
    def __init__(self):
        self.effects: List[StatusEffect] = []
        
    def add_effect(
        self, 
        effect_type: StatusEffectType,
        current_turn: int,
        duration: int = -1,
        intensity: int = 1,
        source_id: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> (bool, str):
        """
        Add a status effect to the Veramon.
        
        Args:
            effect_type: Type of effect to add
            current_turn: Current battle turn
            duration: Duration in turns (-1 for permanent)
            intensity: Effect intensity (1-5)
            source_id: ID of the source Veramon
            custom_data: Additional effect data
            
        Returns:
            Tuple of (success, message)
        """
        # Check if immune to status effects
        if self.has_effect(StatusEffectType.IMMUNITY):
            return False, "It's immune to status effects!"
            
        # Check if already has a primary effect
        if effect_type in StatusEffectType.primary_effects():
            for effect in self.effects:
                if effect.type in StatusEffectType.primary_effects():
                    return False, "It already has a status condition!"
        
        # Check for existing effect of same type
        for i, effect in enumerate(self.effects):
            if effect.type == effect_type:
                # Update existing effect with higher intensity/duration
                if intensity > effect.intensity:
                    self.effects[i].intensity = intensity
                    self.effects[i].applied_at_turn = current_turn
                    
                # Extend duration if longer
                if duration > effect.duration or duration == -1:
                    self.effects[i].duration = duration
                    
                return True, f"The {effect_type.value} effect was strengthened!"
        
        # Add new effect
        effect = StatusEffect(
            effect_type=effect_type,
            duration=duration,
            intensity=intensity,
            source_id=source_id,
            custom_data=custom_data
        )
        effect.applied_at_turn = current_turn
        self.effects.append(effect)
        
        # Return success message
        if effect_type == StatusEffectType.BURN:
            return True, "It was burned!"
        elif effect_type == StatusEffectType.POISON:
            return True, "It was poisoned!"
        elif effect_type == StatusEffectType.PARALYSIS:
            return True, "It was paralyzed!"
        elif effect_type == StatusEffectType.SLEEP:
            return True, "It fell asleep!"
        elif effect_type == StatusEffectType.FREEZE:
            return True, "It was frozen solid!"
        elif effect_type == StatusEffectType.CONFUSION:
            return True, "It became confused!"
        else:
            return True, f"It was afflicted with {effect_type.value}!"
    
    def remove_effect(self, effect_type: StatusEffectType) -> bool:
        """
        Remove a specific status effect.
        
        Args:
            effect_type: Type of effect to remove
            
        Returns:
            True if effect was removed, False if not found
        """
        for i, effect in enumerate(self.effects):
            if effect.type == effect_type:
                self.effects.pop(i)
                return True
        return False
    
    def has_effect(self, effect_type: StatusEffectType) -> bool:
        """
        Check if the Veramon has a specific status effect.
        
        Args:
            effect_type: Type of effect to check for
            
        Returns:
            True if effect is present, False otherwise
        """
        return any(effect.type == effect_type for effect in self.effects)
    
    def get_effect(self, effect_type: StatusEffectType) -> Optional[StatusEffect]:
        """
        Get a specific status effect if present.
        
        Args:
            effect_type: Type of effect to get
            
        Returns:
            StatusEffect if found, None otherwise
        """
        for effect in self.effects:
            if effect.type == effect_type:
                return effect
        return None
    
    def process_turn_start(self, current_turn: int, veramon_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process effects that trigger at the start of a turn.
        
        Args:
            current_turn: Current battle turn
            veramon_stats: Current stats of the Veramon
            
        Returns:
            List of effect results
        """
        results = []
        for effect in self.effects[:]:  # Make a copy to safely modify during iteration
            # Check if effect has expired
            if effect.is_expired(current_turn):
                self.effects.remove(effect)
                results.append({
                    "type": "effect_expired",
                    "effect": effect.type.value,
                    "message": f"The {effect.type.value} effect wore off!"
                })
                continue
            
            # Process turn effects for specific types
            if effect.type in [
                StatusEffectType.BURN, 
                StatusEffectType.POISON, 
                StatusEffectType.LEECH,
                StatusEffectType.CURSE
            ]:
                effect_result = effect.get_turn_effect(current_turn, veramon_stats)
                if effect_result:
                    effect_result["effect"] = effect.type.value
                    results.append(effect_result)
        
        return results
    
    def process_turn_end(self, current_turn: int) -> List[Dict[str, Any]]:
        """
        Process effects at the end of a turn.
        
        Args:
            current_turn: Current battle turn
            
        Returns:
            List of effect results
        """
        results = []
        
        # Remove single-turn effects like flinch
        for effect in self.effects[:]:  # Make a copy to safely modify during iteration
            if effect.type == StatusEffectType.FLINCH:
                self.effects.remove(effect)
                results.append({
                    "type": "effect_expired",
                    "effect": effect.type.value,
                    "message": "It's no longer flinching."
                })
                
        return results
    
    def can_act(self, veramon_stats: Dict[str, Any]) -> (bool, str):
        """
        Check if the Veramon can act based on its status effects.
        
        Args:
            veramon_stats: Current stats of the Veramon
            
        Returns:
            Tuple of (can_act, message)
        """
        for effect in self.effects:
            can_act, message = effect.can_act(veramon_stats)
            if not can_act:
                return False, message
            elif message == "confusion_self_damage":
                # Special case for confusion
                return True, "confusion_self_damage"
                
        return True, ""
    
    def get_stat_modifiers(self) -> Dict[str, float]:
        """
        Get all stat modifiers from active effects.
        
        Returns:
            Dictionary of {stat_name: multiplier}
        """
        modifiers = {
            "attack": 1.0,
            "defense": 1.0,
            "speed": 1.0,
            "special": 1.0
        }
        
        # Apply all modifiers
        for effect in self.effects:
            for stat in modifiers:
                modifier = effect.get_stat_modifier(stat)
                modifiers[stat] *= modifier
        
        return modifiers
    
    def on_hit(self, damage: int, move_type: str) -> List[Dict[str, Any]]:
        """
        Process effects when the Veramon is hit.
        
        Args:
            damage: Amount of damage taken
            move_type: Type of the move
            
        Returns:
            List of effect results
        """
        results = []
        
        for effect in self.effects[:]:  # Make a copy to safely modify during iteration
            removed, message = effect.on_hit(damage, move_type)
            
            if removed:
                self.effects.remove(effect)
                results.append({
                    "type": "effect_removed",
                    "effect": effect.type.value,
                    "message": message
                })
            elif message:
                results.append({
                    "type": "effect_triggered",
                    "effect": effect.type.value,
                    "message": message
                })
                
        return results
    
    def modify_incoming_damage(self, damage: int, move_type: str) -> (int, List[Dict[str, Any]]):
        """
        Modify incoming damage based on status effects.
        
        Args:
            damage: Original damage amount
            move_type: Type of the move
            
        Returns:
            Tuple of (modified_damage, results)
        """
        results = []
        modified_damage = damage
        
        for effect in self.effects:
            damage_mod, message = effect.get_damage_modifier(modified_damage, move_type)
            
            if damage_mod != modified_damage:
                results.append({
                    "type": "damage_modified",
                    "effect": effect.type.value,
                    "original_damage": modified_damage,
                    "new_damage": damage_mod,
                    "message": message
                })
                modified_damage = damage_mod
                
        return modified_damage, results
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert all status effects to a dictionary representation.
        
        Returns:
            Dictionary of effects
        """
        return {
            "effects": [effect.to_dict() for effect in self.effects]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatusEffectManager":
        """
        Create a status effect manager from a dictionary.
        
        Args:
            data: Dictionary of effects
            
        Returns:
            StatusEffectManager instance
        """
        manager = cls()
        
        if "effects" in data:
            for effect_data in data["effects"]:
                effect = StatusEffect.from_dict(effect_data)
                manager.effects.append(effect)
                
        return manager
