"""
Trading UI Component for Veramon Reunited
-----------------------------------------
This module provides Discord UI components for the trading system, including:
- Trade creation interface
- Veramon selection for trades
- Trade confirmation buttons
- Trade status display

These components integrate with the trading system to create a safe and
interactive Discord-based trading experience with anti-scam protections.
"""

import discord
from discord import ui
from discord.ui import Button, View, Select
from typing import List, Dict, Any, Optional, Union, Callable
import asyncio
import logging

# Set up logging
logger = logging.getLogger("trade_ui")

class TradeItemButton(Button):
    """Button to add or view a trade item."""
    
    def __init__(self, item_id: str, item_name: str, item_type: str, is_added: bool = False, is_owner: bool = True):
        """
        Initialize a trade item button.
        
        Args:
            item_id: ID of the item (capture_id for Veramon)
            item_name: Name of the item
            item_type: Type of item (veramon, token, etc.)
            is_added: Whether the item is already added to the trade
            is_owner: Whether the current user owns this item
        """
        # Set button style based on state
        if is_added:
            style = discord.ButtonStyle.success
            label = f"✓ {item_name}"
            disabled = False
        elif not is_owner:
            style = discord.ButtonStyle.secondary
            label = f"👁️ {item_name}"
            disabled = True
        else:
            style = discord.ButtonStyle.primary
            label = item_name
            disabled = False
        
        super().__init__(style=style, label=label, disabled=disabled)
        
        # Store item info for callback
        self.item_id = item_id
        self.item_name = item_name
        self.item_type = item_type
        self.is_added = is_added
        self.is_owner = is_owner
        self.custom_id = f"trade_item_{item_type}_{item_id}"

class TradeActionButton(Button):
    """Button for trade actions (confirm, cancel, etc.)."""
    
    def __init__(self, action: str, disabled: bool = False):
        """
        Initialize a trade action button.
        
        Args:
            action: Action type (confirm, cancel, etc.)
            disabled: Whether the button is disabled
        """
        # Set button style and label based on action
        if action == "confirm":
            style = discord.ButtonStyle.success
            label = "Confirm Trade"
        elif action == "cancel":
            style = discord.ButtonStyle.danger
            label = "Cancel Trade"
        elif action == "accept":
            style = discord.ButtonStyle.success
            label = "Accept Trade"
        elif action == "decline":
            style = discord.ButtonStyle.danger
            label = "Decline Trade"
        else:
            style = discord.ButtonStyle.secondary
            label = action.capitalize()
        
        super().__init__(style=style, label=label, disabled=disabled)
        
        # Store action for callback
        self.action = action
        self.custom_id = f"trade_action_{action}"

class TradeVeramonSelector(Select):
    """Dropdown select for choosing Veramon to trade."""
    
    def __init__(self, user_id: str, veramon_list: List[Dict[str, Any]], trade_id: int):
        """
        Initialize a Veramon selector dropdown.
        
        Args:
            user_id: ID of the user
            veramon_list: List of user's Veramon
            trade_id: ID of the trade
        """
        # Create options from Veramon list (max 25 options in a Discord select)
        options = []
        for v in veramon_list[:25]:
            v_id = v.get("id", "0")
            v_name = v.get("name", "Unknown")
            v_level = v.get("level", 1)
            v_rarity = v.get("rarity", "common").capitalize()
            
            # Format option with useful info
            option = discord.SelectOption(
                label=f"{v_name} (Lv.{v_level})",
                value=v_id,
                description=f"Rarity: {v_rarity}"
            )
            options.append(option)
        
        # Set placeholder text
        placeholder = "Select a Veramon to add to the trade..."
        
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
        
        # Store info for callback
        self.user_id = user_id
        self.trade_id = trade_id
        self.custom_id = f"trade_select_{trade_id}"
        self.veramon_map = {v.get("id", "0"): v for v in veramon_list[:25]}

class TradeView(View):
    """View for trade actions and item selection."""
    
    def __init__(self, trade_id: int, creator_id: str, target_id: str, timeout: float = 300.0):
        """
        Initialize a trade view.
        
        Args:
            trade_id: ID of the trade
            creator_id: ID of the trade creator
            target_id: ID of the trade target
            timeout: Button timeout in seconds
        """
        super().__init__(timeout=timeout)
        self.trade_id = trade_id
        self.creator_id = creator_id
        self.target_id = target_id
        
        # Callbacks
        self.add_item_callback = None
        self.remove_item_callback = None
        self.confirm_callback = None
        self.cancel_callback = None
    
    def add_trade_items(self, items: List[Dict[str, Any]], user_id: str):
        """
        Add trade item buttons to the view.
        
        Args:
            items: List of trade items
            user_id: ID of the current user viewing the trade
        """
        # Group items by owner first
        creator_items = []
        target_items = []
        
        for item in items:
            owner_id = item.get("owner_id", "")
            if owner_id == self.creator_id:
                creator_items.append(item)
            elif owner_id == self.target_id:
                target_items.append(item)
        
        # Add creator's items first (max 5 per person)
        for item in creator_items[:5]:
            button = TradeItemButton(
                item_id=item.get("id", "0"),
                item_name=item.get("name", "Unknown"),
                item_type=item.get("type", "veramon"),
                is_added=True,
                is_owner=(user_id == self.creator_id)
            )
            button.callback = self._create_item_callback(item.get("id", "0"), "remove")
            self.add_item(button)
        
        # Add target's items next (max 5 per person)
        for item in target_items[:5]:
            button = TradeItemButton(
                item_id=item.get("id", "0"),
                item_name=item.get("name", "Unknown"),
                item_type=item.get("type", "veramon"),
                is_added=True,
                is_owner=(user_id == self.target_id)
            )
            button.callback = self._create_item_callback(item.get("id", "0"), "remove")
            self.add_item(button)
    
    def add_veramon_selector(self, user_id: str, veramon_list: List[Dict[str, Any]]):
        """
        Add a Veramon selector dropdown to the view.
        
        Args:
            user_id: ID of the current user
            veramon_list: List of user's Veramon
        """
        # Only add selector if user is part of the trade
        if user_id != self.creator_id and user_id != self.target_id:
            return
        
        selector = TradeVeramonSelector(user_id, veramon_list, self.trade_id)
        selector.callback = self._create_selector_callback()
        self.add_item(selector)
    
    def add_action_buttons(self, user_id: str, trade_status: str):
        """
        Add action buttons to the view.
        
        Args:
            user_id: ID of the current user
            trade_status: Current status of the trade
        """
        # Determine which buttons to show based on trade status and user
        if trade_status == "pending":
            # Creator can cancel, target can accept/decline
            if user_id == self.creator_id:
                cancel_button = TradeActionButton("cancel")
                cancel_button.callback = self._create_action_callback("cancel")
                self.add_item(cancel_button)
            elif user_id == self.target_id:
                accept_button = TradeActionButton("accept")
                accept_button.callback = self._create_action_callback("accept")
                self.add_item(accept_button)
                
                decline_button = TradeActionButton("decline")
                decline_button.callback = self._create_action_callback("decline")
                self.add_item(decline_button)
        
        elif trade_status == "negotiating":
            # Both users can confirm or cancel
            confirm_button = TradeActionButton("confirm")
            confirm_button.callback = self._create_action_callback("confirm")
            
            cancel_button = TradeActionButton("cancel")
            cancel_button.callback = self._create_action_callback("cancel")
            
            self.add_item(confirm_button)
            self.add_item(cancel_button)
        
        # For completed/cancelled trades, no buttons needed
    
    def set_callbacks(self, add_callback: Callable, remove_callback: Callable, 
                    confirm_callback: Callable, cancel_callback: Callable):
        """Set callbacks for trade actions."""
        self.add_item_callback = add_callback
        self.remove_item_callback = remove_callback
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
    
    def _create_item_callback(self, item_id: str, action: str):
        """Create a callback for a trade item button."""
        async def callback(interaction: discord.Interaction):
            # Check if user is part of the trade
            user_id = str(interaction.user.id)
            if user_id != self.creator_id and user_id != self.target_id:
                await interaction.response.send_message(
                    "You are not part of this trade!", ephemeral=True
                )
                return
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the appropriate callback
            if action == "add" and self.add_item_callback:
                await self.add_item_callback(self.trade_id, user_id, item_id, interaction)
            elif action == "remove" and self.remove_item_callback:
                await self.remove_item_callback(self.trade_id, user_id, item_id, interaction)
        
        return callback
    
    def _create_selector_callback(self):
        """Create a callback for the Veramon selector."""
        async def callback(interaction: discord.Interaction):
            # Check if user is part of the trade
            user_id = str(interaction.user.id)
            if user_id != self.creator_id and user_id != self.target_id:
                await interaction.response.send_message(
                    "You are not part of this trade!", ephemeral=True
                )
                return
            
            # Get selected Veramon ID
            selected_id = interaction.data["values"][0]
            
            # Call the add item callback if it exists
            if self.add_item_callback:
                await interaction.response.defer(ephemeral=True)
                await self.add_item_callback(self.trade_id, user_id, selected_id, interaction)
        
        return callback
    
    def _create_action_callback(self, action: str):
        """Create a callback for a trade action button."""
        async def callback(interaction: discord.Interaction):
            # Check if user is part of the trade
            user_id = str(interaction.user.id)
            if user_id != self.creator_id and user_id != self.target_id:
                await interaction.response.send_message(
                    "You are not part of this trade!", ephemeral=True
                )
                return
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the appropriate callback
            if action == "confirm" and self.confirm_callback:
                await self.confirm_callback(self.trade_id, user_id, interaction)
            elif action in ["cancel", "decline"] and self.cancel_callback:
                await self.cancel_callback(self.trade_id, user_id, interaction)
            elif action == "accept" and self.confirm_callback:
                # Accept is the same as confirm for the target
                await self.confirm_callback(self.trade_id, user_id, interaction)
        
        return callback

class TradeUI:
    """Main class for handling trade UI components."""
    
    @staticmethod
    def create_trade_embed(trade_data: Dict[str, Any], for_user_id: Optional[str] = None) -> discord.Embed:
        """
        Create a trade status embed.
        
        Args:
            trade_data: Trade data
            for_user_id: User ID to create personalized view for
            
        Returns:
            discord.Embed: Trade status embed
        """
        # Get basic trade info
        trade_id = trade_data.get("trade_id", 0)
        status = trade_data.get("status", "pending").upper()
        creator_id = trade_data.get("creator_id", "unknown")
        target_id = trade_data.get("target_id", "unknown")
        creator_name = trade_data.get("creator_name", "Unknown")
        target_name = trade_data.get("target_name", "Unknown")
        created_at = trade_data.get("created_at", "Unknown time")
        
        # Parse trade items
        creator_items = trade_data.get("creator_items", [])
        target_items = trade_data.get("target_items", [])
        
        # Create embed with appropriate color based on status
        color = discord.Color.blue()
        if status == "COMPLETED":
            color = discord.Color.green()
        elif status == "CANCELLED":
            color = discord.Color.red()
        
        # Create the embed
        embed = discord.Embed(
            title=f"Trade #{trade_id}",
            description=f"Status: **{status}**\nCreated: {created_at}",
            color=color
        )
        
        # Add creator's info and items
        creator_value = ""
        if creator_items:
            for item in creator_items:
                item_name = item.get("name", "Unknown")
                item_type = item.get("type", "veramon").capitalize()
                item_details = item.get("details", "")
                creator_value += f"• {item_name} ({item_type}) {item_details}\n"
        else:
            creator_value = "No items added yet"
        
        # Format creator name based on viewer
        if for_user_id and creator_id == for_user_id:
            creator_title = f"Your Offer (👤 {creator_name})"
        else:
            creator_title = f"👤 {creator_name}'s Offer"
        
        embed.add_field(
            name=creator_title,
            value=creator_value,
            inline=False
        )
        
        # Add target's info and items
        target_value = ""
        if target_items:
            for item in target_items:
                item_name = item.get("name", "Unknown")
                item_type = item.get("type", "veramon").capitalize()
                item_details = item.get("details", "")
                target_value += f"• {item_name} ({item_type}) {item_details}\n"
        else:
            target_value = "No items added yet"
        
        # Format target name based on viewer
        if for_user_id and target_id == for_user_id:
            target_title = f"Your Offer (👤 {target_name})"
        else:
            target_title = f"👤 {target_name}'s Offer"
        
        embed.add_field(
            name=target_title,
            value=target_value,
            inline=False
        )
        
        # Add confirmation status
        creator_confirmed = trade_data.get("creator_confirmed", False)
        target_confirmed = trade_data.get("target_confirmed", False)
        
        confirmation_status = (
            f"👤 {creator_name}: {'✅ Confirmed' if creator_confirmed else '❌ Not confirmed'}\n"
            f"👤 {target_name}: {'✅ Confirmed' if target_confirmed else '❌ Not confirmed'}"
        )
        
        embed.add_field(
            name="Confirmation Status",
            value=confirmation_status,
            inline=False
        )
        
        # Add safety notice
        if status in ["PENDING", "NEGOTIATING"]:
            embed.set_footer(text=(
                "⚠️ Trade Safety: Please verify all items before confirming. "
                "Both users must add at least one item and confirm for a trade to complete."
            ))
        
        return embed
    
    @staticmethod
    async def create_trade_view(
        trade_data: Dict[str, Any],
        user_id: str,
        veramon_list: Optional[List[Dict[str, Any]]] = None,
        add_callback: Optional[Callable] = None,
        remove_callback: Optional[Callable] = None,
        confirm_callback: Optional[Callable] = None,
        cancel_callback: Optional[Callable] = None
    ) -> TradeView:
        """
        Create a view with trade buttons and selectors.
        
        Args:
            trade_data: Trade data
            user_id: ID of the current user
            veramon_list: List of user's Veramon (for selector)
            add_callback: Callback for adding items
            remove_callback: Callback for removing items
            confirm_callback: Callback for confirming trade
            cancel_callback: Callback for cancelling trade
            
        Returns:
            TradeView: View with trade components
        """
        # Get trade info
        trade_id = trade_data.get("trade_id", 0)
        creator_id = trade_data.get("creator_id", "")
        target_id = trade_data.get("target_id", "")
        status = trade_data.get("status", "pending")
        
        # Combine all trade items
        all_items = trade_data.get("creator_items", []) + trade_data.get("target_items", [])
        
        # Create view
        view = TradeView(
            trade_id=trade_id,
            creator_id=creator_id,
            target_id=target_id
        )
        
        # Set callbacks if provided
        if add_callback and remove_callback and confirm_callback and cancel_callback:
            view.set_callbacks(add_callback, remove_callback, confirm_callback, cancel_callback)
        
        # Add trade items if any exist
        if all_items:
            view.add_trade_items(all_items, user_id)
        
        # Add Veramon selector if user is part of the trade and has Veramon
        if (user_id == creator_id or user_id == target_id) and veramon_list:
            view.add_veramon_selector(user_id, veramon_list)
        
        # Add action buttons based on trade status
        view.add_action_buttons(user_id, status)
        
        return view
