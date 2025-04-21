"""
Enhanced Trading UI for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides modern Discord UI components for the trading system.
"""

import discord
from discord import ui
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Union, Awaitable
from enum import Enum

from src.utils.ui.interactive_ui import InteractiveView, CarouselView, EnhancedSelectionView
from src.utils.ui_theme import theme_manager, ThemeColorType, Theme

# Set up logging
logger = logging.getLogger('veramon.trading_ui')

class TradeStatus(Enum):
    """Status of a trade."""
    CREATING = "creating"
    NEGOTIATING = "negotiating" 
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TradeUI(InteractiveView):
    """
    Enhanced trading UI with modern Discord components.
    
    Features:
    - Themed trading interface
    - Visual representation of both sides of trade
    - Interactive item selection
    - Safety confirmations
    - Trade history
    """
    
    def __init__(
        self,
        user_id: str,
        trade_id: str,
        trade_manager,
        receiver_id: str,
        **kwargs
    ):
        super().__init__(
            user_id=user_id,
            timeout=600.0,  # 10 minute timeout for trades
            **kwargs
        )
        
        self.trade_id = trade_id
        self.trade_manager = trade_manager
        self.receiver_id = receiver_id
        
        # Trade state
        self.initiator_items = []
        self.receiver_items = []
        self.status = TradeStatus.CREATING
        self.initiator_confirmed = False
        self.receiver_confirmed = False
        
        # Theme
        self.theme = theme_manager.get_user_theme(user_id)
        
        # Add components
        self._setup_components()
    
    def _setup_components(self):
        """Set up UI components based on trade status."""
        # Clear existing items
        self.clear_items()
        
        if self.status == TradeStatus.CREATING or self.status == TradeStatus.NEGOTIATING:
            # Add item management buttons
            self.add_item(TradeActionButton(
                action="add_item",
                label="Add Item",
                style=self.theme.get_button_style("primary"),
                row=0
            ))
            
            self.add_item(TradeActionButton(
                action="remove_item",
                label="Remove Item",
                style=self.theme.get_button_style("secondary"),
                row=0
            ))
            
            # Add confirm/cancel buttons
            self.add_item(TradeActionButton(
                action="confirm",
                label="Confirm Trade",
                style=self.theme.get_button_style("success"),
                row=1
            ))
            
            self.add_item(TradeActionButton(
                action="cancel",
                label="Cancel Trade",
                style=self.theme.get_button_style("danger"),
                row=1
            ))
        
        elif self.status == TradeStatus.PENDING:
            # Only allow confirmation and cancellation at this stage
            confirm_button = TradeActionButton(
                action="confirm",
                label="Confirm Trade",
                style=self.theme.get_button_style("success"),
                row=0
            )
            confirm_button.disabled = self.initiator_confirmed if self.user_id == self.trade_id.split("-")[0] else self.receiver_confirmed
            self.add_item(confirm_button)
            
            self.add_item(TradeActionButton(
                action="cancel",
                label="Cancel Trade",
                style=self.theme.get_button_style("danger"),
                row=0
            ))
        
        elif self.status == TradeStatus.COMPLETED:
            # Add view history button
            self.add_item(TradeActionButton(
                action="view_history",
                label="View Trade History",
                style=self.theme.get_button_style("secondary"),
                row=0
            ))
        
        elif self.status == TradeStatus.CANCELLED or self.status == TradeStatus.REJECTED:
            # Add new trade button
            self.add_item(TradeActionButton(
                action="new_trade",
                label="Start New Trade",
                style=self.theme.get_button_style("primary"),
                row=0
            ))
    
    async def on_action(self, interaction: discord.Interaction, action: str):
        """Handle button actions."""
        if action == "add_item":
            await self._show_add_item_menu(interaction)
        
        elif action == "remove_item":
            await self._show_remove_item_menu(interaction)
        
        elif action == "confirm":
            await self._handle_confirmation(interaction)
        
        elif action == "cancel":
            await self._handle_cancellation(interaction)
        
        elif action == "view_history":
            await self._show_trade_history(interaction)
        
        elif action == "new_trade":
            await self._start_new_trade(interaction)
    
    async def _show_add_item_menu(self, interaction: discord.Interaction):
        """Show menu to add items to the trade."""
        # Create a selection view for choosing items
        selection_view = EnhancedSelectionView(
            user_id=self.user_id,
            placeholder="Select item to add to trade",
            min_values=1,
            max_values=1
        )
        
        # Get player's items from trade manager
        trade_ref = self.trade_manager.get_trade(self.trade_id)
        items = await trade_ref.ask({
            "type": "get_tradable_items",
            "user_id": self.user_id
        })
        
        # Add options
        for item in items:
            selection_view.add_option(
                label=item.get("name", "Unknown"),
                value=item.get("id", "unknown"),
                description=f"Level {item.get('level', '?')} - {item.get('type', 'Item')}",
                emoji=item.get("emoji", "🎁")
            )
        
        # Send selection menu
        embed = self.theme.create_embed(
            title="Add to Trade",
            description="Select an item to add to the trade.",
            color_type=ThemeColorType.PRIMARY
        )
        
        await selection_view.send_to(
            interaction,
            embed=embed,
            ephemeral=True
        )
        
        # Wait for selection
        selected_item = await selection_view.wait_for_selection()
        if selected_item:
            # Add item to trade
            trade_ref = self.trade_manager.get_trade(self.trade_id)
            result = await trade_ref.ask({
                "type": "add_item",
                "user_id": self.user_id,
                "item_id": selected_item
            })
            
            if result.get("success", False):
                # Update the trade
                await self.update_trade(interaction)
                
                # Send confirmation
                await interaction.followup.send(
                    f"Added item to the trade!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Failed to add item: {result.get('message', 'Unknown error')}",
                    ephemeral=True
                )
    
    async def _show_remove_item_menu(self, interaction: discord.Interaction):
        """Show menu to remove items from the trade."""
        # Create a selection view
        selection_view = EnhancedSelectionView(
            user_id=self.user_id,
            placeholder="Select item to remove from trade",
            min_values=1,
            max_values=1
        )
        
        # Get items in trade for this user
        items = self.initiator_items if self.user_id == self.trade_id.split("-")[0] else self.receiver_items
        
        if not items:
            await interaction.response.send_message(
                "You don't have any items in this trade.",
                ephemeral=True
            )
            return
        
        # Add options
        for item in items:
            selection_view.add_option(
                label=item.get("name", "Unknown"),
                value=item.get("id", "unknown"),
                description=f"Level {item.get('level', '?')} - {item.get('type', 'Item')}",
                emoji=item.get("emoji", "🎁")
            )
        
        # Send selection menu
        embed = self.theme.create_embed(
            title="Remove from Trade",
            description="Select an item to remove from the trade.",
            color_type=ThemeColorType.DANGER
        )
        
        await selection_view.send_to(
            interaction,
            embed=embed,
            ephemeral=True
        )
        
        # Wait for selection
        selected_item = await selection_view.wait_for_selection()
        if selected_item:
            # Remove item from trade
            trade_ref = self.trade_manager.get_trade(self.trade_id)
            result = await trade_ref.ask({
                "type": "remove_item",
                "user_id": self.user_id,
                "item_id": selected_item
            })
            
            if result.get("success", False):
                # Update the trade
                await self.update_trade(interaction)
                
                # Send confirmation
                await interaction.followup.send(
                    f"Removed item from the trade!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Failed to remove item: {result.get('message', 'Unknown error')}",
                    ephemeral=True
                )
    
    async def _handle_confirmation(self, interaction: discord.Interaction):
        """Handle trade confirmation."""
        # Check the safety first - are there items on both sides?
        if not self.initiator_items or not self.receiver_items:
            await interaction.response.send_message(
                "⚠️ Safety Warning: Both parties must add items to a trade! Please add items before confirming.",
                ephemeral=True
            )
            return
        
        # Show confirmation dialog
        embed = self.theme.create_embed(
            title="Confirm Trade",
            description="Are you sure you want to confirm this trade?\nThis cannot be undone once both parties confirm!",
            color_type=ThemeColorType.WARNING
        )
        
        # Add previews of what you're giving and getting
        user_items = self.initiator_items if self.user_id == self.trade_id.split("-")[0] else self.receiver_items
        other_items = self.receiver_items if self.user_id == self.trade_id.split("-")[0] else self.initiator_items
        
        giving_text = "\n".join([f"• {item.get('name', 'Unknown')} (Lv.{item.get('level', '?')})" for item in user_items])
        getting_text = "\n".join([f"• {item.get('name', 'Unknown')} (Lv.{item.get('level', '?')})" for item in other_items])
        
        embed.add_field(
            name="You are giving:",
            value=giving_text or "Nothing",
            inline=True
        )
        
        embed.add_field(
            name="You are receiving:",
            value=getting_text or "Nothing",
            inline=True
        )
        
        # Create confirmation buttons
        confirm_view = InteractiveView(user_id=self.user_id, timeout=60.0)
        
        confirm_button = ui.Button(
            style=discord.ButtonStyle.success,
            label="Confirm",
            row=0
        )
        
        cancel_button = ui.Button(
            style=discord.ButtonStyle.danger,
            label="Cancel",
            row=0
        )
        
        async def confirm_callback(confirm_interaction):
            # Set confirmed flag in trade
            trade_ref = self.trade_manager.get_trade(self.trade_id)
            result = await trade_ref.ask({
                "type": "confirm_trade",
                "user_id": self.user_id
            })
            
            if result.get("success", False):
                # Update confirmation status
                if self.user_id == self.trade_id.split("-")[0]:
                    self.initiator_confirmed = True
                else:
                    self.receiver_confirmed = True
                
                # Update the trade status if both confirmed
                if result.get("both_confirmed", False):
                    self.status = TradeStatus.ACCEPTED
                    
                    # Start the trade completion process
                    await self._complete_trade(confirm_interaction)
                else:
                    # Just update status to pending
                    self.status = TradeStatus.PENDING
                    
                    # Update UI
                    self._setup_components()
                    await self.update_trade_embed(interaction)
                    
                    # Send confirmation
                    await confirm_interaction.response.edit_message(
                        content="You've confirmed the trade! Waiting for the other party to confirm.",
                        embed=None,
                        view=None
                    )
            else:
                await confirm_interaction.response.edit_message(
                    content=f"Failed to confirm trade: {result.get('message', 'Unknown error')}",
                    embed=None,
                    view=None
                )
        
        async def cancel_callback(cancel_interaction):
            # Just close the confirmation dialog
            await cancel_interaction.response.edit_message(
                content="Trade confirmation cancelled.",
                embed=None,
                view=None
            )
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)
        
        # Send confirmation dialog
        await interaction.response.send_message(
            embed=embed,
            view=confirm_view,
            ephemeral=True
        )
    
    async def _handle_cancellation(self, interaction: discord.Interaction):
        """Handle trade cancellation."""
        # Show confirmation dialog
        embed = self.theme.create_embed(
            title="Cancel Trade",
            description="Are you sure you want to cancel this trade?\nAll items will be returned.",
            color_type=ThemeColorType.DANGER
        )
        
        # Create confirmation buttons
        confirm_view = InteractiveView(user_id=self.user_id, timeout=60.0)
        
        confirm_button = ui.Button(
            style=discord.ButtonStyle.danger,
            label="Cancel Trade",
            row=0
        )
        
        back_button = ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Go Back",
            row=0
        )
        
        async def confirm_callback(confirm_interaction):
            # Cancel the trade
            trade_ref = self.trade_manager.get_trade(self.trade_id)
            result = await trade_ref.ask({
                "type": "cancel_trade",
                "user_id": self.user_id
            })
            
            if result.get("success", False):
                # Update status
                self.status = TradeStatus.CANCELLED
                
                # Update UI
                self._setup_components()
                await self.update_trade_embed(interaction)
                
                # Send confirmation
                await confirm_interaction.response.edit_message(
                    content="Trade cancelled. All items have been returned.",
                    embed=None,
                    view=None
                )
            else:
                await confirm_interaction.response.edit_message(
                    content=f"Failed to cancel trade: {result.get('message', 'Unknown error')}",
                    embed=None,
                    view=None
                )
        
        async def back_callback(back_interaction):
            # Just close the confirmation dialog
            await back_interaction.response.edit_message(
                content="Returned to trade.",
                embed=None,
                view=None
            )
        
        confirm_button.callback = confirm_callback
        back_button.callback = back_callback
        
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(back_button)
        
        # Send confirmation dialog
        await interaction.response.send_message(
            embed=embed,
            view=confirm_view,
            ephemeral=True
        )
    
    async def _complete_trade(self, interaction: discord.Interaction):
        """Complete the trade after both parties confirm."""
        # Execute trade
        trade_ref = self.trade_manager.get_trade(self.trade_id)
        result = await trade_ref.ask({
            "type": "execute_trade"
        })
        
        if result.get("success", False):
            # Update status
            self.status = TradeStatus.COMPLETED
            
            # Update UI
            self._setup_components()
            
            # Create completion embed
            embed = self.theme.create_embed(
                title="Trade Completed!",
                description="The trade has been completed successfully. Items have been exchanged.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Add summary
            initiator_name = result.get("initiator_name", "Initiator")
            receiver_name = result.get("receiver_name", "Receiver")
            
            initiator_items_text = "\n".join([f"• {item.get('name', 'Unknown')} (Lv.{item.get('level', '?')})" for item in self.initiator_items])
            receiver_items_text = "\n".join([f"• {item.get('name', 'Unknown')} (Lv.{item.get('level', '?')})" for item in self.receiver_items])
            
            embed.add_field(
                name=f"{initiator_name} gave:",
                value=initiator_items_text or "Nothing",
                inline=True
            )
            
            embed.add_field(
                name=f"{receiver_name} gave:",
                value=receiver_items_text or "Nothing",
                inline=True
            )
            
            # Add trade ID for reference
            embed.set_footer(text=f"Trade ID: {self.trade_id}")
            
            # Update the message
            await self.parent_message.edit(embed=embed, view=self)
            
            # Send notification
            await interaction.channel.send(
                f"🎉 Trade between {initiator_name} and {receiver_name} has been completed successfully!",
                delete_after=30
            )
        else:
            # Something went wrong
            await interaction.followup.send(
                f"Failed to complete trade: {result.get('message', 'Unknown error')}",
                ephemeral=True
            )
    
    async def _show_trade_history(self, interaction: discord.Interaction):
        """Show trade history."""
        # Get trade history
        trade_ref = self.trade_manager.get_trade(self.trade_id)
        history = await trade_ref.ask({
            "type": "get_trade_history",
            "user_id": self.user_id
        })
        
        # Create history embed
        embed = self.theme.create_embed(
            title="Trade History",
            description=f"History for Trade {self.trade_id}",
            color_type=ThemeColorType.INFO
        )
        
        # Add events
        if "events" in history:
            events_text = ""
            for event in history["events"]:
                timestamp = event.get("timestamp", "Unknown time")
                action = event.get("action", "Unknown action")
                details = event.get("details", "")
                
                events_text += f"• {timestamp}: {action} {details}\n"
            
            embed.add_field(
                name="Events",
                value=events_text or "No events recorded",
                inline=False
            )
        
        # Add summary
        embed.add_field(
            name="Final Status",
            value=history.get("final_status", "Unknown"),
            inline=True
        )
        
        embed.add_field(
            name="Completed On",
            value=history.get("completed_at", "N/A"),
            inline=True
        )
        
        # Send the history
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
    
    async def _start_new_trade(self, interaction: discord.Interaction):
        """Start a new trade."""
        # Create confirmation dialog
        embed = self.theme.create_embed(
            title="New Trade",
            description="Do you want to start a new trade with the same player?",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Create confirmation buttons
        confirm_view = InteractiveView(user_id=self.user_id, timeout=60.0)
        
        confirm_button = ui.Button(
            style=discord.ButtonStyle.success,
            label="Start New Trade",
            row=0
        )
        
        cancel_button = ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Cancel",
            row=0
        )
        
        async def confirm_callback(confirm_interaction):
            # Start a new trade
            # This would be handled by the cog instead of directly
            await confirm_interaction.response.edit_message(
                content="Use `/trade_create` command to start a new trade.",
                embed=None,
                view=None
            )
        
        async def cancel_callback(cancel_interaction):
            # Just close the confirmation dialog
            await cancel_interaction.response.edit_message(
                content="Request cancelled.",
                embed=None,
                view=None
            )
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)
        
        # Send confirmation dialog
        await interaction.response.send_message(
            embed=embed,
            view=confirm_view,
            ephemeral=True
        )
    
    async def update_trade(self, interaction: discord.Interaction):
        """Update the trade UI with current state."""
        # Get trade state
        trade_ref = self.trade_manager.get_trade(self.trade_id)
        if trade_ref:
            try:
                trade_state = await trade_ref.ask({"type": "get_trade_state"})
                
                # Update local state
                self.initiator_items = trade_state.get("initiator_items", [])
                self.receiver_items = trade_state.get("receiver_items", [])
                self.status = TradeStatus(trade_state.get("status", "negotiating"))
                self.initiator_confirmed = trade_state.get("initiator_confirmed", False)
                self.receiver_confirmed = trade_state.get("receiver_confirmed", False)
                
                # Set up components based on new state
                self._setup_components()
                
                # Update trade embed
                await self.update_trade_embed(interaction)
            except Exception as e:
                logger.error(f"Error updating trade UI: {e}")
                await interaction.followup.send(
                    "There was an error updating the trade UI. Please try again.",
                    ephemeral=True
                )
        else:
            await interaction.followup.send(
                "Trade not found! It may have expired or been cancelled.",
                ephemeral=True
            )
    
    async def update_trade_embed(self, interaction: discord.Interaction):
        """Update the trade embed with current state."""
        # Get user names
        initiator_id = self.trade_id.split("-")[0]
        initiator_user = await interaction.guild.fetch_member(int(initiator_id))
        receiver_user = await interaction.guild.fetch_member(int(self.receiver_id))
        
        initiator_name = initiator_user.display_name if initiator_user else "Unknown"
        receiver_name = receiver_user.display_name if receiver_user else "Unknown"
        
        # Create the embed
        embed = self.theme.create_embed(
            title=f"Trade: {initiator_name} ⟷ {receiver_name}",
            description=f"Status: {self.status.name.title()}",
            color_type=ThemeColorType.PRIMARY if self.status == TradeStatus.NEGOTIATING else 
                       ThemeColorType.WARNING if self.status == TradeStatus.PENDING else
                       ThemeColorType.SUCCESS if self.status == TradeStatus.COMPLETED else
                       ThemeColorType.DANGER
        )
        
        # Add left side (initiator items)
        initiator_items_text = ""
        for item in self.initiator_items:
            initiator_items_text += f"• {item.get('name', 'Unknown')} (Lv.{item.get('level', '?')})\n"
        
        embed.add_field(
            name=f"{initiator_name}'s Offer" + (" ✅" if self.initiator_confirmed else ""),
            value=initiator_items_text or "Nothing yet",
            inline=True
        )
        
        # Add right side (receiver items)
        receiver_items_text = ""
        for item in self.receiver_items:
            receiver_items_text += f"• {item.get('name', 'Unknown')} (Lv.{item.get('level', '?')})\n"
        
        embed.add_field(
            name=f"{receiver_name}'s Offer" + (" ✅" if self.receiver_confirmed else ""),
            value=receiver_items_text or "Nothing yet",
            inline=True
        )
        
        # Add instructions
        if self.status == TradeStatus.NEGOTIATING:
            embed.add_field(
                name="Instructions",
                value="Add items to your offer, then click 'Confirm Trade' when ready.\nBoth parties must confirm for the trade to complete.",
                inline=False
            )
        elif self.status == TradeStatus.PENDING:
            embed.add_field(
                name="Instructions",
                value=f"Waiting for {initiator_name if not self.initiator_confirmed else receiver_name} to confirm the trade.",
                inline=False
            )
        
        # Update the message
        # Store a reference to the parent message for later updates
        if hasattr(interaction, 'message') and interaction.message:
            self.parent_message = interaction.message
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.followup.send(embed=embed, view=self)

class TradeActionButton(ui.Button):
    """Button for trade actions."""
    
    def __init__(
        self,
        action: str,
        label: str,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        row: int = 0,
        disabled: bool = False
    ):
        super().__init__(
            style=style,
            label=label,
            row=row,
            disabled=disabled
        )
        self.action = action
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await self.view.on_action(interaction, self.action)


class TradeItemDisplay(CarouselView):
    """Display of items in a trade with a carousel."""
    
    def __init__(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        **kwargs
    ):
        super().__init__(
            user_id=user_id,
            **kwargs
        )
        
        self.items = items
        
        # Set up the carousel
        for item in items:
            name = item.get("name", "Unknown")
            level = item.get("level", "?")
            item_type = item.get("type", "Item")
            description = item.get("description", "No description available.")
            
            # Create an embed for this item
            embed = discord.Embed(
                title=f"{name} (Lv.{level})",
                description=description,
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Type",
                value=item_type,
                inline=True
            )
            
            if "stats" in item:
                stats_text = ""
                for stat_name, stat_value in item["stats"].items():
                    stats_text += f"{stat_name}: {stat_value}\n"
                
                embed.add_field(
                    name="Stats",
                    value=stats_text,
                    inline=True
                )
            
            # Add to carousel
            self.add_page(embed)
    
    async def update_items(self, items: List[Dict[str, Any]]):
        """Update the displayed items."""
        self.items = items
        
        # Clear current pages
        self.pages.clear()
        
        # Add new pages
        for item in items:
            name = item.get("name", "Unknown")
            level = item.get("level", "?")
            item_type = item.get("type", "Item")
            description = item.get("description", "No description available.")
            
            # Create an embed for this item
            embed = discord.Embed(
                title=f"{name} (Lv.{level})",
                description=description,
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Type",
                value=item_type,
                inline=True
            )
            
            if "stats" in item:
                stats_text = ""
                for stat_name, stat_value in item["stats"].items():
                    stats_text += f"{stat_name}: {stat_value}\n"
                
                embed.add_field(
                    name="Stats",
                    value=stats_text,
                    inline=True
                )
            
            # Add to carousel
            self.add_page(embed)
