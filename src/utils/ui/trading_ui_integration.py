"""
Trading UI Integration for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides the integration layer between the trading system and enhanced UI components.
"""

import discord
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union

from src.utils.ui_theme import theme_manager, ThemeColorType
from src.utils.ui.interactive_ui import InteractiveView, NavigableView, NavigationType
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

# Set up logging
logger = logging.getLogger('veramon.trading_ui_integration')

class TradeUIIntegration:
    """Integration layer between the trading system and enhanced UI components."""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_trades = {}
        self.accessibility_manager = get_accessibility_manager()
    
    async def create_trade_embed(
        self, 
        trade_data: Dict[str, Any], 
        user_id: str
    ) -> discord.Embed:
        """
        Create a trade embed with accessibility features applied.
        
        Args:
            trade_data: Trade data to display
            user_id: ID of the user viewing the embed
            
        Returns:
            discord.Embed: Themed and accessible trade embed
        """
        # Get user's theme
        theme = theme_manager.get_user_theme(user_id)
        
        # Get user's accessibility settings
        accessibility = self.accessibility_manager.get_settings(user_id)
        
        # Extract trade data
        trade_id = trade_data.get("trade_id", "unknown")
        trade_status = trade_data.get("status", "Pending")
        initiator = trade_data.get("initiator", {})
        receiver = trade_data.get("receiver", {})
        initiator_items = trade_data.get("initiator_items", [])
        receiver_items = trade_data.get("receiver_items", [])
        
        # Apply text size based on accessibility settings
        trade_title = apply_text_size(f"Trade #{trade_id}", accessibility.text_size)
        
        # Create description with accessibility considerations
        description = f"Trade Status: **{trade_status}**\n\n"
        
        if accessibility.simplified_ui:
            # Simpler description for improved readability
            description += (
                f"Initiated by: {initiator.get('name', 'Unknown')}\n"
                f"Trading with: {receiver.get('name', 'Unknown')}\n\n"
            )
        else:
            # Standard description
            description += (
                f"**Initiated by**: {initiator.get('name', 'Unknown')}\n"
                f"**Trading with**: {receiver.get('name', 'Unknown')}\n\n"
            )
        
        # Add accessibility notes if screen reader support is enabled
        if accessibility.screen_reader_support:
            description += "*Use the tabs below to navigate between trade options. " \
                          "The first tab shows offered items, the second tab shows requested items.*\n\n"
        
        # Create base embed
        embed = theme.create_embed(
            title=trade_title,
            description=description,
            color_type=ThemeColorType.TRADE
        )
        
        # Format initiator items with accessibility in mind
        initiator_value = ""
        for item in initiator_items:
            item_name = item.get("name", "Unknown Item")
            item_type = item.get("type", "item")
            item_level = item.get("level", "N/A")
            
            # Add alt text if enabled
            if accessibility.always_include_alt_text:
                alt_text = get_alt_text(item_type, {"name": item_name, "type": item.get("element_type", "Unknown")})
                initiator_value += f"• {item_name} (Lvl {item_level}) [*{alt_text}*]\n"
            else:
                initiator_value += f"• {item_name} (Lvl {item_level})\n"
        
        if not initiator_value:
            initiator_value = "No items offered yet."
        
        # Format receiver items with accessibility in mind
        receiver_value = ""
        for item in receiver_items:
            item_name = item.get("name", "Unknown Item")
            item_type = item.get("type", "item")
            item_level = item.get("level", "N/A")
            
            # Add alt text if enabled
            if accessibility.always_include_alt_text:
                alt_text = get_alt_text(item_type, {"name": item_name, "type": item.get("element_type", "Unknown")})
                receiver_value += f"• {item_name} (Lvl {item_level}) [*{alt_text}*]\n"
            else:
                receiver_value += f"• {item_name} (Lvl {item_level})\n"
        
        if not receiver_value:
            receiver_value = "No items requested yet."
        
        # Add fields with appropriate text size
        embed.add_field(
            name=apply_text_size(f"{initiator.get('name', 'Unknown')}'s Offer", accessibility.text_size),
            value=initiator_value,
            inline=True
        )
        
        embed.add_field(
            name=apply_text_size(f"{receiver.get('name', 'Unknown')}'s Offer", accessibility.text_size),
            value=receiver_value,
            inline=True
        )
        
        # Add trade instructions with appropriate formatting
        instructions = "Both players must add items and confirm the trade."
        if accessibility.text_size == TextSize.LARGE or accessibility.text_size == TextSize.EXTRA_LARGE:
            instructions = f"**{instructions}**"
        
        embed.add_field(
            name=apply_text_size("Instructions", accessibility.text_size),
            value=instructions,
            inline=False
        )
        
        # Apply simplification if enabled
        if accessibility.simplified_ui:
            embed_dict = simplify_embed(embed.to_dict(), True)
            embed = discord.Embed.from_dict(embed_dict)
        
        return embed
    
    def create_trade_view(
        self, 
        trade_data: Dict[str, Any], 
        user_id: str
    ) -> InteractiveView:
        """
        Create an interactive trade view with accessibility features.
        
        Args:
            trade_data: Trade data for the view
            user_id: ID of the user viewing the trade
            
        Returns:
            InteractiveView: Trade UI with accessibility features
        """
        # Get user's accessibility settings
        accessibility = self.accessibility_manager.get_settings(user_id)
        
        # Determine view timeout based on settings
        timeout = 300.0 if accessibility.extended_interaction_timeouts else 180.0
        
        # Create base view
        view = NavigableView(
            user_id=user_id,
            timeout=timeout,
            navigation_type=NavigationType.TABS
        )
        
        # Determine the user's role in the trade
        initiator_id = trade_data.get("initiator", {}).get("id", "")
        is_initiator = user_id == initiator_id
        
        # Set up tabs based on role and accessibility settings
        if accessibility.simplified_ui:
            # Simpler navigation with fewer tabs for improved readability
            view.setup_tabs(["Trade", "Options"])
        else:
            # Standard tabs
            view.setup_tabs(["Your Items", "Their Items", "Confirm", "Info"])
        
        # Add "Add Item" button
        add_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Add Item",
            row=1
        )
        add_button.custom_id = "trade_add_item"
        view.add_item(add_button)
        
        # Add "Remove Item" button
        remove_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Remove Item",
            row=1
        )
        remove_button.custom_id = "trade_remove_item"
        view.add_item(remove_button)
        
        # Add buttons with proper spacing based on accessibility settings
        row = 2 if accessibility.extra_button_spacing else 1
        
        # Add "Confirm Trade" button
        confirm_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Confirm Trade",
            row=row
        )
        confirm_button.custom_id = "trade_confirm"
        view.add_item(confirm_button)
        
        # Add "Cancel Trade" button
        cancel_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Cancel Trade",
            row=row
        )
        cancel_button.custom_id = "trade_cancel"
        view.add_item(cancel_button)
        
        # Add accessible tooltips if screen reader support is enabled
        if accessibility.screen_reader_support:
            for child in view.children:
                if hasattr(child, "custom_id"):
                    if child.custom_id == "trade_add_item":
                        child.label = "Add Item - Add a Veramon to your trade offer"
                    elif child.custom_id == "trade_remove_item":
                        child.label = "Remove Item - Remove a Veramon from your trade offer"
                    elif child.custom_id == "trade_confirm":
                        child.label = "Confirm Trade - Accept the current trade terms"
                    elif child.custom_id == "trade_cancel":
                        child.label = "Cancel Trade - Cancel the current trade"
        
        return view
    
    async def update_trade_ui(
        self,
        interaction: discord.Interaction,
        trade_data: Dict[str, Any],
        user_id: str
    ) -> None:
        """
        Update a trade UI with new data, applying accessibility settings.
        
        Args:
            interaction: Discord interaction to respond to
            trade_data: Updated trade data
            user_id: ID of the user viewing the trade
        """
        # Get user's accessibility settings
        accessibility = self.accessibility_manager.get_settings(user_id)
        
        # Create updated embed
        embed = await self.create_trade_embed(trade_data, user_id)
        
        # Create updated view
        view = self.create_trade_view(trade_data, user_id)
        
        # Check if trade has animations that need to be displayed
        has_animations = trade_data.get("has_animation", False)
        animation_data = trade_data.get("animation_data", {})
        
        # Handle animations based on accessibility settings
        if has_animations and accessibility.animation_level != AnimationLevel.NONE:
            # Check if we should show reduced animations
            if accessibility.animation_level == AnimationLevel.REDUCED:
                # Only show critical animations (like trade completion)
                show_animation = animation_data.get("critical", False)
            else:
                # Show all animations
                show_animation = True
            
            if show_animation:
                # Get animation frames
                frames = animation_data.get("frames", [])
                frame_delay = animation_data.get("frame_delay", 0.8)
                
                # Show animation frames
                for frame in frames:
                    # Create frame embed
                    frame_embed = discord.Embed.from_dict(frame)
                    
                    # Apply simplification if needed
                    if accessibility.simplified_ui:
                        frame_dict = simplify_embed(frame_embed.to_dict(), True)
                        frame_embed = discord.Embed.from_dict(frame_dict)
                    
                    # Update message with frame
                    await interaction.edit_original_response(embed=frame_embed)
                    
                    # Wait for next frame
                    await asyncio.sleep(frame_delay)
        
        # Update with final state
        await interaction.edit_original_response(embed=embed, view=view)
    
    async def apply_accessibility_to_existing_trade(
        self,
        message: discord.Message,
        trade_data: Dict[str, Any],
        user_id: str
    ) -> None:
        """
        Apply accessibility settings to an existing trade message.
        
        Args:
            message: Discord message containing the trade UI
            trade_data: Trade data
            user_id: ID of the user viewing the trade
        """
        # Get user's accessibility settings
        accessibility = self.accessibility_manager.get_settings(user_id)
        
        # Create updated embed
        embed = await self.create_trade_embed(trade_data, user_id)
        
        # Create updated view
        view = self.create_trade_view(trade_data, user_id)
        
        # Update message
        await message.edit(embed=embed, view=view)
    
    def get_timeout_duration(self, user_id: str) -> float:
        """
        Get the appropriate timeout duration based on user's accessibility settings.
        
        Args:
            user_id: User ID to check settings for
            
        Returns:
            float: Timeout duration in seconds
        """
        # Get user's accessibility settings
        accessibility = self.accessibility_manager.get_settings(user_id)
        
        # Return extended timeout if enabled, otherwise standard
        return 300.0 if accessibility.extended_interaction_timeouts else 180.0
