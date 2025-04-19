import discord
from discord.ext import commands
from discord import ui
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
import asyncio
import json
import os
import logging

from src.utils.ui_theme import theme_manager, ThemeColorType
from src.utils.user_settings import get_user_settings

logger = logging.getLogger('veramon.ui')

class NavigationType(Enum):
    """Types of navigation for interactive UIs."""
    PAGES = auto()           # Next/previous page navigation
    MENU = auto()            # Menu-based navigation with categories
    WIZARD = auto()          # Step-by-step wizard navigation
    DASHBOARD = auto()       # Dashboard with multiple sections
    TABS = auto()            # Tabbed interface

class InteractiveView(ui.View):
    """
    Base class for all interactive views in the bot.
    Extends Discord's UI View with common functionality.
    """
    
    def __init__(
        self, 
        user_id: str, 
        timeout: float = 180.0,
        ephemeral: bool = True,
        allow_dm: bool = False
    ):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.ephemeral = ephemeral
        self.allow_dm = allow_dm
        self.message = None
        self.settings = get_user_settings(user_id)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Check if the user interacting with the view is the original user.
        Also handles DM permissions.
        """
        # Check if the interaction is from the original user
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "You cannot interact with someone else's menu.",
                ephemeral=True
            )
            return False
            
        # Check if this is in DMs and if the user is allowed to use DMs
        if isinstance(interaction.channel, discord.DMChannel) and not self.allow_dm:
            if not await self._check_dm_permissions(interaction):
                await interaction.response.send_message(
                    "You don't have permission to use this command in DMs. "
                    "Please use it in a server channel instead.",
                    ephemeral=True
                )
                return False
                
        return True
        
    async def _check_dm_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if the user has permission to use the bot in DMs."""
        from src.models.permissions import check_permission_level, PermissionLevel
        
        # VIP and higher can use the bot in DMs
        allowed = await check_permission_level(interaction, PermissionLevel.VIP)
        return allowed
        
    async def on_timeout(self):
        """Handle timeout by disabling all components."""
        if self.message:
            # Disable all components
            for item in self.children:
                if hasattr(item, "disabled"):
                    item.disabled = True
                    
            # Update the message if possible
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass  # Message was deleted
            except Exception as e:
                logger.error(f"Error updating view on timeout: {e}")
                
    async def send_to(self, interaction: discord.Interaction, embed: discord.Embed = None, content: str = None):
        """Send or update the view with an optional embed."""
        if not interaction.response.is_done():
            # First interaction, send new message
            await interaction.response.send_message(
                content=content,
                embed=embed,
                view=self,
                ephemeral=self.ephemeral
            )
            
            # Store message for future updates
            self.message = await interaction.original_response()
        else:
            # Update existing message
            await interaction.edit_original_response(
                content=content,
                embed=embed,
                view=self
            )
            
    @ui.button(label="Close", style=discord.ButtonStyle.secondary, row=4)
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        """Close the interactive menu."""
        # Disable all components to prevent further interaction
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
                
        # Update the message
        await interaction.response.edit_message(
            view=self, 
            content="Menu closed."
        )
        
        # Stop listening for interactions
        self.stop()
        
class NavigableView(InteractiveView):
    """
    View with navigation capabilities for multi-page or multi-section content.
    """
    
    def __init__(
        self, 
        user_id: str, 
        navigation_type: NavigationType = NavigationType.PAGES,
        max_pages: int = 1,
        current_page: int = 0,
        **kwargs
    ):
        super().__init__(user_id, **kwargs)
        self.navigation_type = navigation_type
        self.max_pages = max(1, max_pages)
        self.current_page = min(current_page, self.max_pages - 1)
        self.current_tab = 0
        self.tabs = []
        
        # Add navigation buttons based on type
        self._setup_navigation()
        
    def _setup_navigation(self):
        """Add appropriate navigation buttons based on the navigation type."""
        if self.navigation_type == NavigationType.PAGES:
            # Add previous/next page buttons if we have multiple pages
            if self.max_pages > 1:
                self.add_item(PageNavButton(is_next=False, row=4))
                self.add_item(PageNavButton(is_next=True, row=4))
                
        elif self.navigation_type == NavigationType.TABS:
            # We'll add tab buttons in the setup_tabs method
            pass
            
        elif self.navigation_type == NavigationType.MENU:
            # We'll add menu buttons in the setup_menu method
            pass
            
        elif self.navigation_type == NavigationType.WIZARD:
            # Add back/next buttons for wizard navigation
            self.add_item(WizardNavButton(is_next=False, row=4))
            self.add_item(WizardNavButton(is_next=True, row=4))
            
    def setup_tabs(self, tabs: List[str]):
        """Set up tabbed navigation with the given tab names."""
        self.tabs = tabs
        self.current_tab = 0
        
        # Add tab buttons (up to 5 tabs in row 0)
        for i, tab in enumerate(tabs[:5]):
            self.add_item(TabButton(tab, i, row=0))
            
    async def update_view(self, interaction: discord.Interaction):
        """Update the view when navigation changes."""
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement update_view")
        
    def get_current_page(self) -> int:
        """Get the current page number (1-based for display)."""
        return self.current_page + 1
        
    def get_max_pages(self) -> int:
        """Get the total number of pages."""
        return self.max_pages
        
    def get_current_tab(self) -> str:
        """Get the current tab name."""
        if self.tabs and 0 <= self.current_tab < len(self.tabs):
            return self.tabs[self.current_tab]
        return ""
        
class PageNavButton(ui.Button):
    """Button for page navigation."""
    
    def __init__(self, is_next: bool = True, row: int = 0):
        self.is_next = is_next
        emoji = "➡️" if is_next else "⬅️"
        label = "Next" if is_next else "Previous"
        style = discord.ButtonStyle.primary
        super().__init__(style=style, emoji=emoji, label=label, row=row)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        
        if self.is_next and view.current_page < view.max_pages - 1:
            view.current_page += 1
        elif not self.is_next and view.current_page > 0:
            view.current_page -= 1
            
        await view.update_view(interaction)
        
class TabButton(ui.Button):
    """Button for tab navigation."""
    
    def __init__(self, label: str, tab_index: int, row: int = 0):
        self.tab_index = tab_index
        style = discord.ButtonStyle.primary
        super().__init__(style=style, label=label, row=row)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.current_tab = self.tab_index
        await view.update_view(interaction)
        
class WizardNavButton(ui.Button):
    """Button for wizard navigation."""
    
    def __init__(self, is_next: bool = True, row: int = 0):
        self.is_next = is_next
        label = "Next" if is_next else "Back"
        emoji = "➡️" if is_next else "⬅️"
        style = discord.ButtonStyle.success if is_next else discord.ButtonStyle.secondary
        super().__init__(style=style, label=label, emoji=emoji, row=row)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        
        if self.is_next and view.current_page < view.max_pages - 1:
            # Validate the current page before moving to the next (for wizards)
            if hasattr(view, "validate_current_page"):
                valid = await view.validate_current_page(interaction)
                if not valid:
                    return
                    
            view.current_page += 1
        elif not self.is_next and view.current_page > 0:
            view.current_page -= 1
            
        await view.update_view(interaction)

class ConfirmView(InteractiveView):
    """
    Simple confirmation view with Yes/No buttons.
    """
    
    def __init__(
        self, 
        user_id: str, 
        confirm_callback: Callable[[discord.Interaction], Awaitable[None]],
        cancel_callback: Optional[Callable[[discord.Interaction], Awaitable[None]]] = None,
        confirm_label: str = "Yes",
        cancel_label: str = "No",
        **kwargs
    ):
        super().__init__(user_id, **kwargs)
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        
        # Add confirmation buttons
        self.add_item(ui.Button(
            style=discord.ButtonStyle.success,
            label=confirm_label,
            custom_id="confirm_button"
        ))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label=cancel_label,
            custom_id="cancel_button"
        ))
        
    @ui.button(custom_id="confirm_button")
    async def confirm_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Handle confirmation."""
        if self.confirm_callback:
            await self.confirm_callback(interaction)
        self.stop()
        
    @ui.button(custom_id="cancel_button")
    async def cancel_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Handle cancellation."""
        if self.cancel_callback:
            await self.cancel_callback(interaction)
        else:
            await interaction.response.edit_message(content="Action cancelled.", view=None)
        self.stop()

# Helpers for creating interactive UIs
def create_confirm_view(
    user_id: str,
    confirm_callback: Callable[[discord.Interaction], Awaitable[None]],
    cancel_callback: Optional[Callable[[discord.Interaction], Awaitable[None]]] = None,
    **kwargs
) -> ConfirmView:
    """Create a confirmation view with the given callbacks."""
    return ConfirmView(
        user_id=user_id,
        confirm_callback=confirm_callback,
        cancel_callback=cancel_callback,
        **kwargs
    )
