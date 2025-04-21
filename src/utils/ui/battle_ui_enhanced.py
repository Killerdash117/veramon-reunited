"""
Enhanced Battle UI for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides modern Discord UI components for the battle system.
"""

import discord
from discord import ui
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Union, Awaitable
from enum import Enum

from src.utils.ui.interactive_ui import InteractiveView, CarouselView
from src.utils.ui_theme import theme_manager, ThemeColorType, Theme
from src.models.veramon import Veramon

# Set up logging
logger = logging.getLogger('veramon.battle_ui')

class BattleActionType(Enum):
    """Types of actions a player can take in battle."""
    MOVE = "move"
    SWITCH = "switch"
    ITEM = "item"
    FLEE = "flee"

class BattleUI(InteractiveView):
    """
    Enhanced battle UI with modern Discord components.
    
    Features:
    - Themed battle interface
    - Animated health bars
    - Status effect indicators
    - Turn counters and history
    - Enhanced move selection
    """
    
    def __init__(
        self,
        user_id: str,
        battle_id: int,
        battle_manager,
        opponent_id: Optional[str] = None,
        is_wild: bool = False,
        **kwargs
    ):
        super().__init__(
            user_id=user_id,
            timeout=300.0,  # 5 minute timeout for battles
            **kwargs
        )
        
        self.battle_id = battle_id
        self.battle_manager = battle_manager
        self.opponent_id = opponent_id
        self.is_wild = is_wild
        
        # Battle state
        self.selected_action = None
        self.selected_move = None
        self.selected_veramon = None
        self.selected_item = None
        self.is_waiting_for_opponent = False
        self.turn_count = 0
        self.battle_log = []
        
        # Theme
        self.theme = theme_manager.get_user_theme(user_id)
        
        # Add components based on the battle type
        self._setup_components()
    
    def _setup_components(self):
        """Set up the UI components based on battle type."""
        # Add move selection buttons (will be updated with actual moves)
        self._setup_move_buttons()
        
        # Add Veramon switching buttons (will be updated with actual team)
        self._setup_switch_buttons()
        
        # Add action buttons (item, flee)
        self._setup_action_buttons()
    
    def _setup_move_buttons(self, moves: List[str] = None):
        """Set up move selection buttons."""
        # Clear existing move buttons
        self.clear_items_of_type(BattleMoveButton)
        
        # Default moves if none provided
        if not moves:
            moves = ["—", "—", "—", "—"]
        
        # Add move buttons (max 4)
        for i, move_name in enumerate(moves[:4]):
            row = 0 if i < 2 else 1
            button = BattleMoveButton(
                move_name=move_name, 
                row=row,
                style=self.theme.get_button_style("primary"),
                disabled=move_name == "—"
            )
            self.add_item(button)
    
    def _setup_switch_buttons(self, team: List[Dict[str, Any]] = None):
        """Set up Veramon switching buttons."""
        # Clear existing switch buttons
        self.clear_items_of_type(BattleVeramonButton)
        
        # Default empty team if none provided
        if not team:
            team = []
        
        # Add up to 6 Veramon buttons
        for i, veramon in enumerate(team[:6]):
            is_active = veramon.get("is_active", False)
            is_fainted = veramon.get("is_fainted", False)
            
            button = BattleVeramonButton(
                veramon_name=veramon.get("name", f"Slot {i+1}"),
                veramon_id=veramon.get("id", None),
                slot=i,
                is_active=is_active,
                is_fainted=is_fainted,
                row=2 if i < 3 else 3
            )
            self.add_item(button)
    
    def _setup_action_buttons(self):
        """Set up additional action buttons."""
        # Add item button
        self.add_item(BattleActionButton(
            action_type=BattleActionType.ITEM,
            label="Item",
            style=self.theme.get_button_style("success"),
            row=4
        ))
        
        # Add flee button (only for wild battles or if configured)
        if self.is_wild:
            self.add_item(BattleActionButton(
                action_type=BattleActionType.FLEE,
                label="Flee",
                style=self.theme.get_button_style("danger"),
                row=4
            ))
    
    def clear_items_of_type(self, button_type):
        """Clear all items of a specific type from the view."""
        to_remove = [item for item in self.children if isinstance(item, button_type)]
        for item in to_remove:
            self.remove_item(item)
    
    async def on_move_selected(self, interaction: discord.Interaction, move_name: str):
        """Handle move selection."""
        # Set the selected move
        self.selected_action = BattleActionType.MOVE
        self.selected_move = move_name
        
        # Highlight the selected move button
        for child in self.children:
            if isinstance(child, BattleMoveButton):
                # Set selected style
                if child.move_name == move_name:
                    child.style = self.theme.get_button_style("success")
                else:
                    child.style = self.theme.get_button_style("primary")
        
        # Update the battle UI
        await self.update_battle_ui(interaction)
        
        # Send the move to the battle manager
        await self._submit_action(interaction)
    
    async def on_veramon_selected(self, interaction: discord.Interaction, veramon_id: str, slot: int):
        """Handle Veramon selection for switching."""
        # Set the selected veramon
        self.selected_action = BattleActionType.SWITCH
        self.selected_veramon = veramon_id
        
        # Highlight the selected Veramon button
        for child in self.children:
            if isinstance(child, BattleVeramonButton):
                # Set selected style
                if child.veramon_id == veramon_id:
                    child.style = self.theme.get_button_style("success")
                else:
                    # Reset to default style based on state
                    if child.is_active:
                        child.style = self.theme.get_button_style("primary")
                    elif child.is_fainted:
                        child.style = self.theme.get_button_style("danger")
                    else:
                        child.style = self.theme.get_button_style("secondary")
        
        # Update the battle UI
        await self.update_battle_ui(interaction)
        
        # Send the switch to the battle manager
        await self._submit_action(interaction)
    
    async def on_action_selected(self, interaction: discord.Interaction, action_type: BattleActionType):
        """Handle selection of other actions (item, flee)."""
        self.selected_action = action_type
        
        if action_type == BattleActionType.ITEM:
            # Open item selection menu
            await self._show_item_selection(interaction)
        elif action_type == BattleActionType.FLEE:
            # Attempt to flee
            await self._submit_action(interaction)
    
    async def _show_item_selection(self, interaction: discord.Interaction):
        """Show item selection menu."""
        # This would be implemented with the enhanced selection view
        # For now, just acknowledge
        await interaction.response.defer()
    
    async def _submit_action(self, interaction: discord.Interaction):
        """Submit the selected action to the battle manager."""
        if not self.selected_action:
            await interaction.response.send_message(
                "Please select an action first!",
                ephemeral=True
            )
            return
        
        # Set waiting state
        self.is_waiting_for_opponent = True
        
        # Update UI to show waiting state
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        # Prepare action data
        action_data = {
            "action_type": self.selected_action.value,
            "user_id": self.user_id,
            "battle_id": self.battle_id
        }
        
        # Add action-specific data
        if self.selected_action == BattleActionType.MOVE:
            action_data["move_name"] = self.selected_move
        elif self.selected_action == BattleActionType.SWITCH:
            action_data["veramon_id"] = self.selected_veramon
        elif self.selected_action == BattleActionType.ITEM:
            action_data["item_id"] = self.selected_item
        
        # Send to battle manager
        battle_ref = self.battle_manager.get_battle(self.battle_id)
        if battle_ref:
            try:
                result = await battle_ref.ask({
                    "type": "execute_action",
                    **action_data
                })
                
                # Process result
                await self._process_battle_result(interaction, result)
            except Exception as e:
                logger.error(f"Error submitting battle action: {e}")
                await interaction.followup.send(
                    "There was an error processing your action. Please try again.",
                    ephemeral=True
                )
        else:
            await interaction.followup.send(
                "Battle not found! It may have ended or timed out.",
                ephemeral=True
            )
    
    async def _process_battle_result(self, interaction: discord.Interaction, result: Dict[str, Any]):
        """Process the result of a battle action."""
        # Update battle state from result
        self.turn_count = result.get("turn_count", self.turn_count + 1)
        
        # Add to battle log
        if "message" in result:
            self.battle_log.append(result["message"])
        
        # Check if battle is over
        if result.get("battle_ended", False):
            await self._handle_battle_end(interaction, result)
            return
        
        # Update UI with new battle state
        self.is_waiting_for_opponent = False
        
        # Reset action selection
        self.selected_action = None
        self.selected_move = None
        self.selected_veramon = None
        self.selected_item = None
        
        # Update battle UI with new state
        await self.update_battle_ui(interaction)
    
    async def _handle_battle_end(self, interaction: discord.Interaction, result: Dict[str, Any]):
        """Handle the end of a battle."""
        # Create end of battle embed
        winner_id = result.get("winner_id")
        
        embed = self.theme.create_embed(
            title="Battle Ended!",
            description=f"Winner: <@{winner_id}>" if winner_id else "The battle ended in a draw!",
            color_type=ThemeColorType.SUCCESS if winner_id == self.user_id else ThemeColorType.DANGER
        )
        
        # Add rewards if any
        if "rewards" in result:
            rewards = result["rewards"]
            reward_text = []
            
            if "xp" in rewards:
                reward_text.append(f"XP: {rewards['xp']}")
            
            if "tokens" in rewards:
                reward_text.append(f"Tokens: {rewards['tokens']}")
            
            if reward_text:
                embed.add_field(
                    name="Rewards",
                    value="\n".join(reward_text),
                    inline=False
                )
        
        # Add battle stats
        embed.add_field(
            name="Battle Stats",
            value=f"Turns: {self.turn_count}\nDuration: {result.get('duration_seconds', 0)}s",
            inline=False
        )
        
        # Show last few battle log entries
        if self.battle_log:
            log_text = "\n".join(self.battle_log[-5:])
            embed.add_field(
                name="Battle Log",
                value=log_text,
                inline=False
            )
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        # Add a button to view detailed results
        self.add_item(ui.Button(
            label="View Battle Details",
            style=discord.ButtonStyle.primary,
            custom_id=f"battle_details_{self.battle_id}"
        ))
        
        # Update message
        await interaction.followup.send(embed=embed, view=self)
    
    async def update_battle_ui(self, interaction: discord.Interaction):
        """Update the battle UI with current state."""
        # This would get battle state from the manager and update the UI
        # For now, just acknowledge
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        # Get battle state from manager
        battle_ref = self.battle_manager.get_battle(self.battle_id)
        if not battle_ref:
            await interaction.followup.send(
                "Battle not found! It may have ended or timed out.",
                ephemeral=True
            )
            return
        
        try:
            battle_state = await battle_ref.ask({"type": "get_battle_state"})
            
            # Create battle state embed
            embed = self._create_battle_state_embed(battle_state)
            
            # Update active moves if it's user's turn
            if battle_state.get("current_turn_user_id") == self.user_id:
                # Enable buttons and update moves
                for child in self.children:
                    child.disabled = False
                
                active_veramon = battle_state.get("player_active_veramon", {})
                
                # Update move buttons
                moves = active_veramon.get("moves", [])
                self._setup_move_buttons(moves)
                
                # Update switch buttons
                team = battle_state.get("player_team", [])
                self._setup_switch_buttons(team)
            else:
                # Disable buttons if not user's turn
                for child in self.children:
                    child.disabled = True
            
            # Update message
            await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error updating battle UI: {e}")
            await interaction.followup.send(
                "There was an error updating the battle UI. Please try again.",
                ephemeral=True
            )
    
    def _create_battle_state_embed(self, battle_state: Dict[str, Any]) -> discord.Embed:
        """Create an embed showing the current battle state."""
        # Get player and opponent info
        player_veramon = battle_state.get("player_active_veramon", {})
        opponent_veramon = battle_state.get("opponent_active_veramon", {})
        
        player_name = battle_state.get("player_name", "Player")
        opponent_name = battle_state.get("opponent_name", "Opponent")
        
        # Create embed
        embed = self.theme.create_embed(
            title=f"Battle: {player_name} vs {opponent_name}",
            description=f"Turn {self.turn_count}\n{'Your turn!' if battle_state.get('current_turn_user_id') == self.user_id else 'Waiting for opponent...'}"
        )
        
        # Add player veramon
        if player_veramon:
            hp_percent = max(0, min(100, int(player_veramon.get("current_hp", 0) / player_veramon.get("max_hp", 1) * 100)))
            hp_bar = self._create_hp_bar(hp_percent)
            
            embed.add_field(
                name=f"Your {player_veramon.get('name', 'Veramon')} (Lv.{player_veramon.get('level', 1)})",
                value=f"HP: {player_veramon.get('current_hp', 0)}/{player_veramon.get('max_hp', 0)}\n{hp_bar}",
                inline=True
            )
        
        # Add opponent veramon
        if opponent_veramon:
            hp_percent = max(0, min(100, int(opponent_veramon.get("current_hp", 0) / opponent_veramon.get("max_hp", 1) * 100)))
            hp_bar = self._create_hp_bar(hp_percent)
            
            embed.add_field(
                name=f"Opponent's {opponent_veramon.get('name', 'Veramon')} (Lv.{opponent_veramon.get('level', 1)})",
                value=f"HP: {opponent_veramon.get('current_hp', 0)}/{opponent_veramon.get('max_hp', 0)}\n{hp_bar}",
                inline=True
            )
        
        # Add last few battle log entries
        if self.battle_log:
            log_text = "\n".join(self.battle_log[-5:])
            embed.add_field(
                name="Battle Log",
                value=log_text,
                inline=False
            )
        
        return embed
    
    def _create_hp_bar(self, percent: int) -> str:
        """Create a visual HP bar."""
        filled_char = "█"
        empty_char = "░"
        
        bar_length = 10
        filled_length = int(bar_length * percent / 100)
        
        # Choose color based on HP percentage
        if percent > 50:
            color = "🟩"  # Green
        elif percent > 25:
            color = "🟨"  # Yellow
        else:
            color = "🟥"  # Red
        
        # Create the bar
        bar = filled_char * filled_length + empty_char * (bar_length - filled_length)
        
        return f"{color} {bar} {percent}%"

class BattleMoveButton(ui.Button):
    """Button for selecting a move in battle."""
    
    def __init__(
        self,
        move_name: str,
        row: int = 0,
        style: discord.ButtonStyle = discord.ButtonStyle.primary,
        disabled: bool = False
    ):
        super().__init__(
            style=style,
            label=move_name,
            row=row,
            disabled=disabled
        )
        self.move_name = move_name
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await self.view.on_move_selected(interaction, self.move_name)

class BattleVeramonButton(ui.Button):
    """Button for switching Veramon in battle."""
    
    def __init__(
        self,
        veramon_name: str,
        veramon_id: Optional[str],
        slot: int,
        is_active: bool = False,
        is_fainted: bool = False,
        row: int = 2
    ):
        # Choose style based on state
        if is_active:
            style = discord.ButtonStyle.primary
        elif is_fainted:
            style = discord.ButtonStyle.danger
        else:
            style = discord.ButtonStyle.secondary
        
        super().__init__(
            style=style,
            label=veramon_name,
            row=row,
            disabled=is_fainted or is_active
        )
        
        self.veramon_id = veramon_id
        self.slot = slot
        self.is_active = is_active
        self.is_fainted = is_fainted
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        if self.veramon_id:
            await self.view.on_veramon_selected(interaction, self.veramon_id, self.slot)

class BattleActionButton(ui.Button):
    """Button for other battle actions (items, flee)."""
    
    def __init__(
        self,
        action_type: BattleActionType,
        label: str,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        row: int = 4
    ):
        super().__init__(
            style=style,
            label=label,
            row=row
        )
        self.action_type = action_type
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await self.view.on_action_selected(interaction, self.action_type)
