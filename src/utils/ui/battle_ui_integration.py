"""
Battle UI Integration for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module integrates the enhanced battle UI with the battle cog system.
"""

import discord
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union

from src.utils.ui.battle_ui_enhanced import BattleUI
from src.utils.ui.ui_registry import get_ui_registry
from src.utils.ui_theme import theme_manager, ThemeColorType
from src.utils.ui.accessibility import (
    get_accessibility_manager, 
    apply_text_size, 
    apply_color_mode,
    get_alt_text,
    simplify_embed,
    TextSize,
    AnimationLevel,
    ColorMode
)
from src.models.battle import Battle, BattleType, BattleStatus, ParticipantStatus, ActionType

# Set up logging
logger = logging.getLogger('veramon.battle_ui_integration')

class BattleUIIntegration:
    """
    Integration layer between the battle cog and enhanced UI components.
    
    This class serves as an adapter that connects the enhanced themed UI
    components with the existing battle system, allowing for a seamless
    upgrade without requiring major changes to the cog itself.
    """
    
    def __init__(self, battle_cog):
        """Initialize the integration with a reference to the battle cog."""
        self.battle_cog = battle_cog
        self.ui_registry = get_ui_registry()
        self.active_views = {}
        self.accessibility_manager = get_accessibility_manager()
    
    async def create_battle_ui(
        self, 
        interaction: discord.Interaction, 
        battle_id: int, 
        user_id: str,
        opponent_id: Optional[str] = None,
        is_wild: bool = False
    ) -> BattleUI:
        """
        Create an enhanced battle UI for a battle.
        
        Args:
            interaction: The interaction that triggered this
            battle_id: The ID of the battle
            user_id: The ID of the user
            opponent_id: The ID of the opponent (if any)
            is_wild: Whether this is a wild encounter
        
        Returns:
            An enhanced battle UI instance
        """
        # Create a proxy battle manager that adapts the cog interface
        battle_manager = BattleCogAdapter(self.battle_cog)
        
        # Create the battle UI
        battle_ui = self.ui_registry.create_battle_ui(
            user_id=user_id,
            battle_id=battle_id,
            battle_manager=battle_manager,
            opponent_id=opponent_id,
            is_wild=is_wild
        )
        
        # Store the view for future reference
        view_key = f"battle_{battle_id}_{user_id}"
        self.active_views[view_key] = battle_ui
        
        # Get battle state from the cog
        battle_state = await self.battle_cog.get_battle_state(battle_id, user_id)
        
        # Create initial battle embed
        theme = theme_manager.get_user_theme(user_id)
        embed = self._create_battle_embed(battle_state, theme, user_id)
        
        # Send the battle UI to the user
        await battle_ui.send_to(
            interaction=interaction,
            embed=embed
        )
        
        return battle_ui
    
    def _create_battle_embed(self, battle_state: Dict[str, Any], theme, user_id: str) -> discord.Embed:
        """Create a themed battle embed from the battle state."""
        # Get battle and player information
        battle_type = battle_state.get("battle_type", "wild")
        opponent_name = battle_state.get("opponent_name", "Wild Veramon")
        player_active = battle_state.get("player_active", {})
        opponent_active = battle_state.get("opponent_active", {})
        turn_count = battle_state.get("turn_count", 1)
        current_turn = battle_state.get("current_turn", user_id)
        
        # Create embed with appropriate title
        if battle_type == "pvp":
            title = f"Battle: You vs {opponent_name}"
        elif battle_type == "wild":
            title = f"Wild Encounter: {opponent_active.get('name', 'Wild Veramon')}"
        elif battle_type == "trainer":
            title = f"Trainer Battle: {opponent_name}"
        else:
            title = "Battle"
        
        # Create the embed with theme
        embed = theme.create_embed(
            title=title,
            description=f"Turn {turn_count}\n" + ("Your turn" if current_turn == user_id else "Opponent's turn"),
            color_type=ThemeColorType.DANGER if battle_type == "wild" else ThemeColorType.PRIMARY
        )
        
        # Add player's active Veramon
        if player_active:
            hp_percent = max(0, min(100, int(player_active.get("current_hp", 0) / player_active.get("max_hp", 1) * 100)))
            hp_bar = self._create_hp_bar(hp_percent)
            
            embed.add_field(
                name=f"Your {player_active.get('name', 'Veramon')} (Lv.{player_active.get('level', 1)})",
                value=f"HP: {player_active.get('current_hp', 0)}/{player_active.get('max_hp', 0)}\n{hp_bar}",
                inline=True
            )
        
        # Add opponent's active Veramon
        if opponent_active:
            hp_percent = max(0, min(100, int(opponent_active.get("current_hp", 0) / opponent_active.get("max_hp", 1) * 100)))
            hp_bar = self._create_hp_bar(hp_percent)
            
            embed.add_field(
                name=f"Opponent's {opponent_active.get('name', 'Veramon')} (Lv.{opponent_active.get('level', 1)})",
                value=f"HP: {opponent_active.get('current_hp', 0)}/{opponent_active.get('max_hp', 0)}\n{hp_bar}",
                inline=True
            )
        
        # Add battle logs
        battle_logs = battle_state.get("battle_logs", [])
        if battle_logs:
            # Only show the last 5 log entries
            log_text = "\n".join(battle_logs[-5:])
            embed.add_field(
                name="Battle Log",
                value=log_text,
                inline=False
            )
        
        # Apply accessibility settings
        accessibility = self.accessibility_manager.get_settings(user_id)
        embed = self._apply_accessibility(embed, accessibility)
        
        return embed
    
    def _apply_accessibility(self, embed: discord.Embed, accessibility: Dict[str, Any]) -> discord.Embed:
        """Apply accessibility settings to the embed."""
        # Apply text size
        embed.title = apply_text_size(embed.title, accessibility.text_size)
        embed.description = apply_text_size(embed.description, accessibility.text_size)
        
        # Apply color mode
        embed.color = apply_color_mode(embed.color, accessibility.color_mode)
        
        # Simplify embed if needed
        if accessibility.simplified_ui:
            embed = simplify_embed(embed.to_dict(), True)
            embed = discord.Embed.from_dict(embed)
        
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
    
    async def update_battle_ui(
        self, 
        interaction: discord.Interaction, 
        battle_id: int, 
        user_id: str
    ) -> bool:
        """
        Update an existing battle UI with the latest battle state.
        
        Args:
            interaction: The interaction that triggered this
            battle_id: The ID of the battle
            user_id: The ID of the user
        
        Returns:
            True if successful, False otherwise
        """
        # Get the active view
        view_key = f"battle_{battle_id}_{user_id}"
        battle_ui = self.active_views.get(view_key)
        
        if not battle_ui:
            logger.warning(f"No active battle UI found for battle {battle_id} and user {user_id}")
            return False
        
        # Get battle state from the cog
        battle_state = await self.battle_cog.get_battle_state(battle_id, user_id)
        
        # Create updated embed
        theme = theme_manager.get_user_theme(user_id)
        embed = self._create_battle_embed(battle_state, theme, user_id)
        
        # Update the UI
        await battle_ui.update_battle_ui(interaction)
        
        # Update the message
        await interaction.response.edit_message(embed=embed, view=battle_ui)
        
        return True
    
    async def end_battle_ui(
        self, 
        interaction: discord.Interaction, 
        battle_id: int, 
        user_id: str,
        winner_id: Optional[str] = None,
        rewards: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        End a battle UI with the results.
        
        Args:
            interaction: The interaction that triggered this
            battle_id: The ID of the battle
            user_id: The ID of the user
            winner_id: The ID of the winner (if any)
            rewards: Rewards gained from the battle
        
        Returns:
            True if successful, False otherwise
        """
        # Get the active view
        view_key = f"battle_{battle_id}_{user_id}"
        battle_ui = self.active_views.get(view_key)
        
        if not battle_ui:
            logger.warning(f"No active battle UI found for battle {battle_id} and user {user_id}")
            return False
        
        # Create end of battle embed
        theme = theme_manager.get_user_theme(user_id)
        
        if winner_id:
            # Determine color based on if user won
            color_type = ThemeColorType.SUCCESS if winner_id == user_id else ThemeColorType.DANGER
            
            embed = theme.create_embed(
                title="Battle Ended!",
                description=f"Winner: <@{winner_id}>",
                color_type=color_type
            )
        else:
            # Draw or cancelled
            embed = theme.create_embed(
                title="Battle Ended",
                description="The battle ended in a draw.",
                color_type=ThemeColorType.NEUTRAL
            )
        
        # Add rewards if any
        if rewards:
            reward_text = []
            
            if "xp" in rewards:
                reward_text.append(f"XP: {rewards['xp']}")
            
            if "tokens" in rewards:
                reward_text.append(f"Tokens: {rewards['tokens']}")
                
            if "evolutions" in rewards:
                for evolution in rewards["evolutions"]:
                    reward_text.append(f"• {evolution['from_name']} evolved into {evolution['to_name']}!")
            
            if reward_text:
                embed.add_field(
                    name="Rewards",
                    value="\n".join(reward_text),
                    inline=False
                )
        
        # Apply accessibility settings
        accessibility = self.accessibility_manager.get_settings(user_id)
        embed = self._apply_accessibility(embed, accessibility)
        
        # Disable all buttons
        for child in battle_ui.children:
            child.disabled = True
        
        # Update the message
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=battle_ui)
        else:
            await interaction.response.edit_message(embed=embed, view=battle_ui)
        
        # Remove from active views
        del self.active_views[view_key]
        
        return True
    
    async def handle_battle_invite(
        self,
        interaction: discord.Interaction,
        battle_id: int,
        host_id: str,
        target_id: str
    ) -> discord.ui.View:
        """
        Create an enhanced battle invitation UI.
        
        Args:
            interaction: The interaction that triggered this
            battle_id: The ID of the battle
            host_id: The ID of the host
            target_id: The ID of the target
        
        Returns:
            A UI view for the battle invitation
        """
        # Create a themed invite embed
        theme = theme_manager.get_user_theme(target_id)
        
        embed = theme.create_embed(
            title="Battle Challenge!",
            description=f"<@{host_id}> has challenged you to a battle!",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Get host user info
        host_user = await interaction.client.fetch_user(int(host_id))
        host_name = host_user.name if host_user else "Unknown"
        
        embed.set_author(name=f"Challenge from {host_name}", icon_url=host_user.avatar.url if host_user and host_user.avatar else None)
        
        # Create invite view
        invite_view = discord.ui.View(timeout=300)  # 5 minute timeout
        
        # Add accept button
        accept_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Accept Challenge",
            custom_id=f"battle_accept_{battle_id}"
        )
        
        # Add decline button
        decline_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Decline Challenge",
            custom_id=f"battle_decline_{battle_id}"
        )
        
        # Add buttons to view
        invite_view.add_item(accept_button)
        invite_view.add_item(decline_button)
        
        # Store hook to handle interaction within the original cog
        accept_button.callback = lambda i: self.battle_cog._handle_battle_accept(i, battle_id)
        decline_button.callback = lambda i: self.battle_cog._handle_battle_decline(i, battle_id)
        
        return invite_view, embed

class BattleCogAdapter:
    """
    Adapter class to make the battle cog compatible with the enhanced battle UI.
    
    This provides a standardized interface expected by the BattleUI class.
    """
    
    def __init__(self, battle_cog):
        """Initialize the adapter with a reference to the battle cog."""
        self.battle_cog = battle_cog
    
    def get_battle(self, battle_id: int):
        """Get a battle reference that can be used with ask."""
        return BattleReference(self.battle_cog, battle_id)

class BattleReference:
    """Reference to a battle in the cog that supports the ask interface."""
    
    def __init__(self, battle_cog, battle_id: int):
        """Initialize the reference with a battle ID."""
        self.battle_cog = battle_cog
        self.battle_id = battle_id
    
    async def ask(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message from the UI."""
        message_type = message.get("type", "")
        
        if message_type == "get_battle_state":
            # Get battle state
            user_id = message.get("user_id")
            return await self.battle_cog.get_battle_state(self.battle_id, user_id)
        
        elif message_type == "execute_action":
            # Execute a battle action
            action_type = message.get("action_type")
            user_id = message.get("user_id")
            
            if action_type == "move":
                # Execute a move
                move_name = message.get("move_name")
                return await self.battle_cog.execute_move(self.battle_id, user_id, move_name)
            
            elif action_type == "switch":
                # Switch Veramon
                veramon_id = message.get("veramon_id")
                return await self.battle_cog.switch_veramon(self.battle_id, user_id, veramon_id)
            
            elif action_type == "item":
                # Use an item
                item_id = message.get("item_id")
                return await self.battle_cog.use_item(self.battle_id, user_id, item_id)
            
            elif action_type == "flee":
                # Attempt to flee
                return await self.battle_cog.attempt_flee(self.battle_id, user_id)
        
        # Default response
        return {"success": False, "message": "Unknown message type or action"}
