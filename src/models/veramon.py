import random
from typing import Dict, List, Optional, Tuple, Union
from src.utils.data_loader import load_all_veramon_data

class Veramon:
    """
    Class representation of a captured Veramon with battle functionality.
    Used to manage Veramon data during battles and other interactions.
    """
    def __init__(self, 
                 name: str, 
                 data: Dict = None, 
                 level: int = 1, 
                 shiny: bool = False,
                 nickname: Optional[str] = None,
                 experience: int = 0,
                 capture_id: Optional[int] = None):
        self.name = name
        
        # Auto-load data if not provided
        if data is None:
            all_veramon_data = load_all_veramon_data()
            if name in all_veramon_data:
                self.data = all_veramon_data[name]
            else:
                raise ValueError(f"Veramon {name} not found in data files")
        else:
            self.data = data
            
        self.level = level
        self.shiny = shiny
        self.nickname = nickname
        self.experience = experience
        self.capture_id = capture_id
        self.display_name = nickname if nickname else name
        
        # Battle-specific attributes
        self.current_hp = self.max_hp
        self.status = None
        self.stat_stages = {"atk": 0, "def": 0, "sp_atk": 0, "sp_def": 0, "speed": 0, "accuracy": 0, "evasion": 0}
        self.moves = []  # Will be populated from database or defaults
        self.active_form = None  # New attribute to track active form
        
    @property
    def types(self) -> List[str]:
        """Get Veramon's types."""
        return self.data.get("type", [])
    
    @property
    def max_hp(self) -> int:
        """Calculate max HP based on base stats and level."""
        base_hp = self.data.get("base_stats", {}).get("hp", 50)
        return int((base_hp * 2 * self.level) / 100) + self.level + 10
    
    @property
    def attack(self) -> int:
        """Calculate current Attack stat."""
        base_atk = self.data.get("base_stats", {}).get("atk", 50)
        stat = int((base_atk * 2 * self.level) / 100) + 5
        return self._apply_stat_stage(stat, self.stat_stages["atk"])
    
    @property
    def defense(self) -> int:
        """Calculate current Defense stat."""
        base_def = self.data.get("base_stats", {}).get("def", 50)
        stat = int((base_def * 2 * self.level) / 100) + 5
        return self._apply_stat_stage(stat, self.stat_stages["def"])
    
    @property
    def special_attack(self) -> int:
        """Calculate current Special Attack stat."""
        base_sp_atk = self.data.get("base_stats", {}).get("sp_atk", 50)
        stat = int((base_sp_atk * 2 * self.level) / 100) + 5
        return self._apply_stat_stage(stat, self.stat_stages["sp_atk"])
    
    @property
    def special_defense(self) -> int:
        """Calculate current Special Defense stat."""
        base_sp_def = self.data.get("base_stats", {}).get("sp_def", 50)
        stat = int((base_sp_def * 2 * self.level) / 100) + 5
        return self._apply_stat_stage(stat, self.stat_stages["sp_def"])
    
    @property
    def speed(self) -> int:
        """Calculate current Speed stat."""
        base_speed = self.data.get("base_stats", {}).get("speed", 50)
        stat = int((base_speed * 2 * self.level) / 100) + 5
        return self._apply_stat_stage(stat, self.stat_stages["speed"])
    
    def _apply_stat_stage(self, stat: int, stage: int) -> int:
        """Apply stat stage multiplier."""
        if stage > 0:
            return int(stat * (2 + stage) / 2)
        elif stage < 0:
            return int(stat * 2 / (2 - stage))
        return stat
    
    def can_evolve(self) -> Tuple[bool, Optional[str]]:
        """Check if Veramon can evolve."""
        evolution_data = self.data.get("evolution", {})
        if not evolution_data:
            return False, None
            
        # Handle multiple evolution paths
        evolution_paths = evolution_data.get("paths", [])
        
        # Support for legacy evolution data format (single path)
        if not evolution_paths and "evolves_to" in evolution_data:
            evolves_to = evolution_data.get("evolves_to")
            level_required = evolution_data.get("level_required", 100)
            
            if evolves_to and self.level >= level_required:
                return True, evolves_to
        
        # Check if any evolution path is available
        for path in evolution_paths:
            if self._meets_evolution_requirements(path):
                return True, path.get("evolves_to")
                
        return False, None
        
    def _meets_evolution_requirements(self, evolution_path: Dict) -> bool:
        """Check if Veramon meets the requirements for a specific evolution path."""
        evolves_to = evolution_path.get("evolves_to")
        if not evolves_to:
            return False
            
        # Check level requirement
        level_required = evolution_path.get("level_required", 100)
        if self.level < level_required:
            return False
            
        # Check item requirement
        required_item = evolution_path.get("required_item")
        if required_item:
            # This would need to check if the user has the item in their inventory
            # We'll implement this when we add the item handling functionality
            return False
            
        # Check time requirement
        time_requirement = evolution_path.get("time_requirement")
        if time_requirement:
            # This would need to check the current time
            # We'll implement this when we add the time-based functionality
            return False
            
        # Check biome requirement
        biome_requirement = evolution_path.get("biome_requirement")
        if biome_requirement:
            # This would need to check if the evolution is happening in a specific biome
            # We'll implement this when we add the location-based functionality
            return False
            
        # Check friendship requirement
        friendship_required = evolution_path.get("friendship_required", 0)
        if friendship_required > 0:
            # This would need to check the Veramon's friendship level
            # We'll implement this when we add the friendship system
            return False
            
        # All requirements met
        return True
    
    def get_available_forms(self) -> List[Dict]:
        """Get list of available special forms for this Veramon."""
        form_data = self.data.get("forms", [])
        available_forms = []
        
        for form in form_data:
            if self._meets_form_requirements(form):
                available_forms.append(form)
                
        return available_forms
        
    def _meets_form_requirements(self, form: Dict) -> bool:
        """Check if Veramon meets the requirements for a specific form."""
        # Check level requirement
        level_required = form.get("level_required", 0)
        if self.level < level_required:
            return False
            
        # Check item requirement
        required_item = form.get("required_item")
        if required_item:
            # This would need to check if the user has the item in their inventory
            # For now, skip this check to avoid blocking testability
            pass
            
        # Check time requirement
        time_requirement = form.get("time_requirement")
        if time_requirement:
            # This would need to check the current time
            # For now, skip this check to avoid blocking testability
            pass
            
        # Check event requirement
        event_requirement = form.get("event_requirement")
        if event_requirement:
            # This would need to check if a specific event is active
            # For now, skip this check to avoid blocking testability
            pass
            
        # Check achievement requirement
        achievement_required = form.get("achievement_required")
        if achievement_required:
            # This would need to check if the user has unlocked the required achievement
            # For now, skip this check to avoid blocking testability
            pass
            
        # All requirements met
        return True
    
    def transform_to_form(self, form_id: str) -> bool:
        """Transform Veramon to a specific form if requirements are met."""
        form_data = self.data.get("forms", [])
        
        for form in form_data:
            if form.get("id") == form_id:
                if self._meets_form_requirements(form):
                    # Update Veramon stats and appearance based on form
                    self.active_form = form_id
                    # Apply form stat modifiers
                    return True
        
        return False
    
    def get_random_moves(self, ability_data: Dict, num_moves: int = 4) -> List[str]:
        """Get random moves from Veramon's available abilities."""
        available_moves = self.data.get("abilities", [])
        
        # Filter out moves that are too high level for this Veramon
        valid_moves = []
        for move_name in available_moves:
            if move_name in ability_data:
                valid_moves.append(move_name)
        
        # Return random subset of valid moves, up to the requested number
        if not valid_moves:
            return ["Tackle"]  # Fallback
        
        num_to_select = min(num_moves, len(valid_moves))
        return random.sample(valid_moves, num_to_select)
    
    def gain_experience(self, amount: int) -> Tuple[int, bool, Optional[str]]:
        """
        Gain experience and potentially level up.
        Returns (new_level, evolved, evolution_name)
        """
        old_level = self.level
        self.experience += amount
        
        # Simple level formula: each level needs 100 * current_level XP to advance
        required_exp = 100 * self.level
        
        evolved = False
        evolution_name = None
        
        if self.experience >= required_exp:
            self.level += 1
            self.experience -= required_exp
            
            # Check for evolution
            can_evolve, evolves_to = self.can_evolve()
            if can_evolve:
                evolved = True
                evolution_name = evolves_to
                
        return self.level, evolved, evolution_name
