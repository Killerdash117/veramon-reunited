"""
Battle UI Component for Veramon Reunited
----------------------------------------
This module provides Discord UI components for the battle system, including:
- Move selection buttons
- Veramon switching interface
- Battle status display
- Turn notifications

These components integrate with the battle system to create an interactive
Discord-based battle experience.
"""

import discord
from discord import ui
from discord.ui import Button, View
from typing import List, Dict, Any, Optional, Union, Callable
import asyncio
import logging

# Set up logging
logger = logging.getLogger("battle_ui")

class MoveButton(Button):
    """Button for selecting a move in battle."""
    
    def __init__(self, move_name: str, move_data: Dict[str, Any], disabled: bool = False):
        """
        Initialize a move button.
        
        Args:
            move_name: Name of the move
            move_data: Move data with power, type, etc.
            disabled: Whether the button is disabled
        """
        # Determine button style based on move type
        style_map = {
            "normal": discord.ButtonStyle.secondary,
            "fire": discord.ButtonStyle.danger,
            "water": discord.ButtonStyle.primary,
            "electric": discord.ButtonStyle.success,
            "grass": discord.ButtonStyle.success,
            "ice": discord.ButtonStyle.primary,
            "fighting": discord.ButtonStyle.danger,
            "poison": discord.ButtonStyle.secondary,
            "ground": discord.ButtonStyle.secondary,
            "flying": discord.ButtonStyle.blurple,
            "psychic": discord.ButtonStyle.secondary,
            "bug": discord.ButtonStyle.success,
            "rock": discord.ButtonStyle.secondary,
            "ghost": discord.ButtonStyle.secondary,
            "dragon": discord.ButtonStyle.danger,
            "dark": discord.ButtonStyle.secondary,
            "steel": discord.ButtonStyle.secondary,
            "fairy": discord.ButtonStyle.danger
        }
        
        # Default to secondary if type not found
        move_type = move_data.get("type", "normal").lower()
        style = style_map.get(move_type, discord.ButtonStyle.secondary)
        
        # Create button label with power
        power = move_data.get("power", 0)
        accuracy = move_data.get("accuracy", 100)
        label = f"{move_name} ({power})"
        
        super().__init__(style=style, label=label, disabled=disabled)
        
        # Store move info for callback
        self.move_name = move_name
        self.move_data = move_data
        self.custom_id = f"move_{move_name.lower().replace(' ', '_')}"

class SwitchButton(Button):
    """Button for switching active Veramon in battle."""
    
    def __init__(self, slot: int, veramon_name: str, current_hp: int, max_hp: int, is_active: bool = False):
        """
        Initialize a switch button.
        
        Args:
            slot: Slot position of the Veramon
            veramon_name: Name of the Veramon
            current_hp: Current HP of the Veramon
            max_hp: Max HP of the Veramon
            is_active: Whether this Veramon is currently active
        """
        # Calculate HP percentage for label
        hp_percent = int((current_hp / max_hp) * 100)
        
        # Create label with HP info
        label = f"{veramon_name} ({hp_percent}%)"
        
        # Determine style and disabled state
        if is_active:
            style = discord.ButtonStyle.success
            disabled = True
        elif current_hp <= 0:
            style = discord.ButtonStyle.danger
            disabled = True
        else:
            style = discord.ButtonStyle.primary
            disabled = False
        
        super().__init__(style=style, label=label, disabled=disabled)
        
        # Store Veramon info for callback
        self.slot = slot
        self.veramon_name = veramon_name
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.is_active = is_active
        self.custom_id = f"switch_{slot}"

class FleeButton(Button):
    """Button for attempting to flee from battle."""
    
    def __init__(self, can_flee: bool = True):
        """Initialize a flee button."""
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Flee",
            disabled=not can_flee,
            custom_id="flee"
        )

class BattleActionView(View):
    """View for battle actions (moves and switching)."""
    
    def __init__(self, battle_id: int, user_id: str, timeout: float = 60.0):
        """
        Initialize a battle action view.
        
        Args:
            battle_id: ID of the battle
            user_id: ID of the user
            timeout: Button timeout in seconds
        """
        super().__init__(timeout=timeout)
        self.battle_id = battle_id
        self.user_id = user_id
        self.move_callback = None
        self.switch_callback = None
        self.flee_callback = None
    
    def add_move_buttons(self, moves: Dict[str, Dict[str, Any]], callback: Callable):
        """
        Add move buttons to the view.
        
        Args:
            moves: Dictionary of moves {name: data}
            callback: Callback function for move selection
        """
        self.move_callback = callback
        
        # Add at most 5 moves
        for i, (name, data) in enumerate(list(moves.items())[:5]):
            button = MoveButton(name, data)
            button.callback = self._create_move_callback(name)
            self.add_item(button)
    
    def add_switch_buttons(self, veramon_list: List[Dict[str, Any]], callback: Callable):
        """
        Add switch buttons to the view.
        
        Args:
            veramon_list: List of Veramon data
            callback: Callback function for switch selection
        """
        self.switch_callback = callback
        
        # Add buttons for each Veramon
        for v in veramon_list:
            button = SwitchButton(
                slot=v.get("slot", 0),
                veramon_name=v.get("name", "Unknown"),
                current_hp=v.get("current_hp", 0),
                max_hp=v.get("max_hp", 100),
                is_active=v.get("is_active", False)
            )
            button.callback = self._create_switch_callback(v.get("slot", 0))
            self.add_item(button)
    
    def add_flee_button(self, can_flee: bool, callback: Callable):
        """
        Add a flee button to the view.
        
        Args:
            can_flee: Whether fleeing is allowed
            callback: Callback function for flee action
        """
        self.flee_callback = callback
        
        button = FleeButton(can_flee)
        button.callback = self._create_flee_callback()
        self.add_item(button)
    
    def _create_move_callback(self, move_name: str):
        """Create a callback for a move button."""
        async def callback(interaction: discord.Interaction):
            # Check if interaction is from the correct user
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message(
                    "This is not your battle turn!", ephemeral=True
                )
                return
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the move callback if it exists
            if self.move_callback:
                await self.move_callback(self.battle_id, self.user_id, move_name, interaction)
        
        return callback
    
    def _create_switch_callback(self, slot: int):
        """Create a callback for a switch button."""
        async def callback(interaction: discord.Interaction):
            # Check if interaction is from the correct user
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message(
                    "This is not your battle!", ephemeral=True
                )
                return
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the switch callback if it exists
            if self.switch_callback:
                await self.switch_callback(self.battle_id, self.user_id, slot, interaction)
        
        return callback
    
    def _create_flee_callback(self):
        """Create a callback for the flee button."""
        async def callback(interaction: discord.Interaction):
            # Check if interaction is from the correct user
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message(
                    "This is not your battle!", ephemeral=True
                )
                return
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the flee callback if it exists
            if self.flee_callback:
                await self.flee_callback(self.battle_id, self.user_id, interaction)
        
        return callback

class TargetSelectionView(View):
    """View for selecting a target in battle."""
    
    def __init__(self, battle_id: int, user_id: str, move_name: str, targets: List[Dict[str, Any]], timeout: float = 30.0):
        """
        Initialize a target selection view.
        
        Args:
            battle_id: ID of the battle
            user_id: ID of the user
            move_name: Name of the move
            targets: List of potential targets
            timeout: Button timeout in seconds
        """
        super().__init__(timeout=timeout)
        self.battle_id = battle_id
        self.user_id = user_id
        self.move_name = move_name
        self.target_callback = None
        
        # Add target buttons
        for target in targets:
            button = Button(
                style=discord.ButtonStyle.secondary,
                label=target.get("name", "Unknown"),
                custom_id=f"target_{target.get('id', '0')}"
            )
            button.callback = self._create_target_callback(target.get("id", "0"))
            self.add_item(button)
    
    def set_callback(self, callback: Callable):
        """Set the target selection callback."""
        self.target_callback = callback
    
    def _create_target_callback(self, target_id: str):
        """Create a callback for a target button."""
        async def callback(interaction: discord.Interaction):
            # Check if interaction is from the correct user
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message(
                    "This is not your battle turn!", ephemeral=True
                )
                return
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the target callback if it exists
            if self.target_callback:
                await self.target_callback(
                    self.battle_id, self.user_id, self.move_name, target_id, interaction
                )
        
        return callback

class BattleUI:
    """Main class for handling battle UI components."""
    
    @staticmethod
    def create_battle_embed(battle_data: Dict[str, Any], for_user_id: Optional[str] = None) -> discord.Embed:
        """
        Create a battle status embed.
        
        Args:
            battle_data: Battle data
            for_user_id: User ID to create personalized view for
            
        Returns:
            discord.Embed: Battle status embed
        """
        # Create embed with battle info
        embed = discord.Embed(
            title=f"Battle: {battle_data.get('type', 'PVP').upper()}",
            description=f"Status: {battle_data.get('status', 'Active')}",
            color=discord.Color.blue()
        )
        
        # Add participants
        for participant in battle_data.get("participants", []):
            user_id = participant.get("user_id", "unknown")
            user_name = participant.get("user_name", "Unknown")
            team_id = participant.get("team_id", 0)
            is_npc = participant.get("is_npc", False)
            
            # Get active Veramon
            active_veramon = participant.get("active_veramon", {})
            v_name = active_veramon.get("name", "None")
            v_hp = active_veramon.get("current_hp", 0)
            v_max_hp = active_veramon.get("max_hp", 100)
            hp_percent = int((v_hp / v_max_hp) * 100) if v_max_hp > 0 else 0
            
            # Format name based on whether it's the current user or NPC
            if is_npc:
                name = f"🤖 {user_name} (NPC)"
            elif for_user_id and user_id == for_user_id:
                name = f"👤 {user_name} (You)"
            else:
                name = f"👤 {user_name}"
            
            # Add field with active Veramon and HP
            embed.add_field(
                name=name,
                value=f"Active: **{v_name}** HP: {v_hp}/{v_max_hp} ({hp_percent}%)",
                inline=False
            )
        
        # Add current turn info
        if "current_turn" in battle_data:
            embed.add_field(
                name="Turn",
                value=f"#{battle_data['current_turn']}",
                inline=True
            )
        
        # Add weather/field condition if present
        if "field_condition" in battle_data:
            embed.add_field(
                name="Field Condition",
                value=battle_data["field_condition"],
                inline=True
            )
        
        # Add footer with battle ID
        embed.set_footer(text=f"Battle ID: {battle_data.get('battle_id', 0)}")
        
        return embed
    
    @staticmethod
    def create_battle_log_embed(battle_logs: List[Dict[str, Any]], max_entries: int = 10) -> discord.Embed:
        """
        Create an embed with battle logs.
        
        Args:
            battle_logs: List of battle log entries
            max_entries: Maximum number of log entries to show
            
        Returns:
            discord.Embed: Battle log embed
        """
        embed = discord.Embed(
            title="Battle Log",
            description="Recent battle actions:",
            color=discord.Color.gold()
        )
        
        # Add the most recent logs, limited to max_entries
        for log in battle_logs[-max_entries:]:
            # Format timestamp
            timestamp = log.get("timestamp", "Unknown")
            
            # Get action details
            action_type = log.get("action_type", "unknown").upper()
            actor = log.get("actor_name", "Unknown")
            result = log.get("result_text", "No details")
            
            # Add field for this log entry
            embed.add_field(
                name=f"{action_type} by {actor}",
                value=result,
                inline=False
            )
        
        return embed
    
    @staticmethod
    async def create_battle_action_view(
        battle_data: Dict[str, Any], 
        user_id: str,
        move_callback: Callable,
        switch_callback: Callable,
        flee_callback: Optional[Callable] = None
    ) -> BattleActionView:
        """
        Create a view with battle action buttons.
        
        Args:
            battle_data: Battle data
            user_id: User ID
            move_callback: Callback for move selection
            switch_callback: Callback for Veramon switching
            flee_callback: Callback for fleeing (optional)
            
        Returns:
            BattleActionView: View with battle action buttons
        """
        # Find the participant data for this user
        participant = next(
            (p for p in battle_data.get("participants", []) if p.get("user_id") == user_id),
            None
        )
        
        if not participant:
            logger.error(f"User {user_id} not found in battle {battle_data.get('battle_id')}")
            return None
        
        # Create view
        view = BattleActionView(
            battle_id=battle_data.get("battle_id", 0),
            user_id=user_id
        )
        
        # Add move buttons if the user has an active Veramon
        active_veramon = participant.get("active_veramon", {})
        if active_veramon and "abilities" in active_veramon:
            view.add_move_buttons(active_veramon["abilities"], move_callback)
        
        # Add switch buttons
        all_veramon = participant.get("veramon", [])
        view.add_switch_buttons(all_veramon, switch_callback)
        
        # Add flee button if callback provided and battle type allows fleeing
        battle_type = battle_data.get("type", "").lower()
        can_flee = battle_type == "pve"  # Only PvE battles allow fleeing
        
        if flee_callback and can_flee:
            view.add_flee_button(can_flee, flee_callback)
        
        return view
