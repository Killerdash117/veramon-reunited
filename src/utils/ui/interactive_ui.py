import discord
from discord.ext import commands
from discord import ui
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
import asyncio
import json
import os
import logging
import time

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
    CAROUSEL = auto()        # Image/card carousel navigation

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
        self.theme = theme_manager.get_user_theme(user_id)
        self.custom_id = f"view_{user_id}_{int(time.time())}"
        
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
                
    async def send_to(self, interaction: discord.Interaction, embed: discord.Embed = None, content: str = None, file: discord.File = None, embeds: List[discord.Embed] = None):
        """Send or update the view with optional embed(s) and file attachments."""
        kwargs = {
            "view": self,
            "ephemeral": self.ephemeral
        }
        
        # Add content if provided
        if content:
            kwargs["content"] = content
            
        # Add either a single embed or multiple embeds (but not both)
        if embed:
            kwargs["embed"] = embed
        elif embeds:
            kwargs["embeds"] = embeds
            
        # Add file if provided
        if file:
            kwargs["file"] = file
        
        if not interaction.response.is_done():
            # First interaction, send new message
            await interaction.response.send_message(**kwargs)
            
            # Store message for future updates
            self.message = await interaction.original_response()
        else:
            # Update existing message
            # For file, we need a followup as edit doesn't support files
            if file and hasattr(interaction, "followup"):
                await interaction.followup.send(**kwargs)
            else:
                # Remove file from kwargs for edit if present
                if "file" in kwargs:
                    del kwargs["file"]
                
                await interaction.edit_original_response(**kwargs)
        
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
            
        elif self.navigation_type == NavigationType.CAROUSEL:
            # Add carousel navigation buttons
            self.add_item(CarouselButton(is_next=False, row=4))
            self.add_item(CarouselButton(is_next=True, row=4))
            
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

class EnhancedSelectionView(InteractiveView):
    """
    Enhanced dropdown menu with modern styling and improved functionality.
    
    Features:
    - Multi-select support
    - Option sorting
    - Search filtering (client-side)
    - Categorized options
    - Custom styling
    """
    
    def __init__(
        self,
        user_id: str,
        placeholder: str = "Select an option",
        min_values: int = 1,
        max_values: int = 1,
        options: List[discord.SelectOption] = None,
        timeout: float = 180.0,
        ephemeral: bool = True,
        on_select_callback: Optional[Callable[[discord.Interaction, List[str]], Awaitable[None]]] = None,
        **kwargs
    ):
        super().__init__(
            user_id=user_id,
            timeout=timeout,
            ephemeral=ephemeral,
            **kwargs
        )
        
        self.placeholder = placeholder
        self.min_values = min_values
        self.max_values = max_values
        self.on_select_callback = on_select_callback
        
        # Store selection state
        self.selected_values = []
        self.selection_future = asyncio.get_running_loop().create_future()
        
        # Create select menu
        self.select_menu = ui.Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options or []
        )
        self.select_menu.callback = self._on_select
        self.add_item(self.select_menu)
        
        # Add confirm button for multi-select
        if max_values > 1:
            self.confirm_button = ui.Button(
                style=discord.ButtonStyle.success,
                label="Confirm",
                disabled=True,
                row=1
            )
            self.confirm_button.callback = self._on_confirm
            self.add_item(self.confirm_button)
            
            # Add clear button
            self.clear_button = ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Clear Selection",
                disabled=True,
                row=1
            )
            self.clear_button.callback = self._on_clear
            self.add_item(self.clear_button)
        
    def add_option(
        self,
        label: str,
        value: str,
        description: str = None,
        emoji: Union[str, discord.Emoji, discord.PartialEmoji] = None,
        default: bool = False
    ):
        """Add an option to the select menu."""
        option = discord.SelectOption(
            label=label,
            value=value,
            description=description,
            emoji=emoji,
            default=default
        )
        
        # Add to existing options
        options = list(self.select_menu.options)
        options.append(option)
        
        # Update select menu options
        self.select_menu.options = options
    
    def add_options(self, options: List[Dict[str, Any]]):
        """Add multiple options to the select menu."""
        new_options = []
        for option in options:
            select_option = discord.SelectOption(
                label=option.get("label", "Option"),
                value=option.get("value", "value"),
                description=option.get("description"),
                emoji=option.get("emoji"),
                default=option.get("default", False)
            )
            new_options.append(select_option)
        
        # Add to existing options
        options = list(self.select_menu.options) + new_options
        
        # Update select menu options
        self.select_menu.options = options
    
    def clear_options(self):
        """Clear all options from the select menu."""
        self.select_menu.options = []
    
    def sort_options(self, key: Callable = None, reverse: bool = False):
        """Sort the options in the select menu."""
        options = list(self.select_menu.options)
        
        if key:
            options.sort(key=key, reverse=reverse)
        else:
            options.sort(key=lambda option: option.label, reverse=reverse)
        
        # Update select menu options
        self.select_menu.options = options
    
    def categorize_options(self, categories: Dict[str, List[discord.SelectOption]]):
        """
        Organize options into categories using separators.
        
        Args:
            categories: Dict mapping category names to lists of SelectOption objects
        """
        all_options = []
        
        for category_name, options in categories.items():
            # Add category separator if there are options
            if options:
                separator = discord.SelectOption(
                    label=f"── {category_name} ──",
                    value=f"_separator_{category_name}",
                    description="",
                    default=False,
                    disabled=True
                )
                all_options.append(separator)
                all_options.extend(options)
        
        # Update select menu options
        self.select_menu.options = all_options
    
    async def _on_select(self, interaction: discord.Interaction):
        """Handle selection from the dropdown menu."""
        # Update selected values
        self.selected_values = self.select_menu.values
        
        # If multi-select, update button states
        if self.max_values > 1:
            self.confirm_button.disabled = len(self.selected_values) < self.min_values
            self.clear_button.disabled = len(self.selected_values) == 0
            await interaction.response.edit_message(view=self)
        else:
            # For single selection, immediately confirm
            if self.on_select_callback:
                await self.on_select_callback(interaction, self.selected_values)
            
            # Complete the future
            if not self.selection_future.done():
                self.selection_future.set_result(self.selected_values[0] if self.selected_values else None)
            
            # Close the view
            self.stop()
    
    async def _on_confirm(self, interaction: discord.Interaction):
        """Handle confirmation of multi-select."""
        if self.on_select_callback:
            await self.on_select_callback(interaction, self.selected_values)
        
        # Complete the future
        if not self.selection_future.done():
            self.selection_future.set_result(self.selected_values)
        
        # Close the view
        self.stop()
    
    async def _on_clear(self, interaction: discord.Interaction):
        """Clear the current selection."""
        self.selected_values = []
        
        # Reset default state of options
        options = list(self.select_menu.options)
        for option in options:
            option.default = False
        
        self.select_menu.options = options
        
        # Update button states
        self.confirm_button.disabled = True
        self.clear_button.disabled = True
        
        await interaction.response.edit_message(view=self)
    
    async def wait_for_selection(self) -> Optional[Union[str, List[str]]]:
        """
        Wait for user selection and return the selected value(s).
        
        Returns:
            For single-select: the selected value or None
            For multi-select: a list of selected values or empty list
        """
        try:
            result = await asyncio.wait_for(
                self.selection_future, 
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            return None if self.max_values == 1 else []
        finally:
            self.stop()

class CarouselView(NavigableView):
    """
    A carousel view for displaying images or cards with next/previous navigation.
    """
    
    def __init__(
        self, 
        user_id: str, 
        items: List[Dict[str, Any]],
        **kwargs
    ):
        """
        Initialize the carousel.
        
        Args:
            user_id: ID of the user who can interact with this carousel
            items: List of items to display in the carousel
                  Each item should be a dict with at least 'embed' or 'content' keys
                  Optional 'file' key for image attachment
            **kwargs: Additional arguments for NavigableView
        """
        super().__init__(
            user_id=user_id, 
            navigation_type=NavigationType.CAROUSEL,
            max_pages=len(items),
            current_page=0,
            **kwargs
        )
        
        self.items = items
        self.current_item_index = 0
        self.indicator_style = kwargs.get("indicator_style", "numbers")  # numbers, dots, none
    
    async def update_view(self, interaction: discord.Interaction):
        """Update the carousel to show the current item."""
        current_item = self.items[self.current_page]
        
        # Get embed if present
        embed = current_item.get("embed")
        
        # Get file if present (for image carousels)
        file = current_item.get("file")
        
        # Get content if present
        content = current_item.get("content")
        
        # Add page indicator based on style
        if self.indicator_style == "numbers":
            footer_text = f"Item {self.current_page + 1}/{len(self.items)}"
            if embed:
                embed.set_footer(text=footer_text)
            else:
                content = f"{content}\n{footer_text}" if content else footer_text
        elif self.indicator_style == "dots":
            dots = "○" * len(self.items)
            dots = dots[:self.current_page] + "●" + dots[self.current_page + 1:]
            if embed:
                embed.set_footer(text=dots)
            else:
                content = f"{content}\n{dots}" if content else dots
        
        # Send or update the message
        await self.send_to(interaction, embed=embed, content=content, file=file)
        
        # Update button states
        self._update_carousel_buttons()
    
    def _update_carousel_buttons(self):
        """Update the carousel navigation buttons based on current position."""
        # Find previous and next buttons
        prev_button = next((b for b in self.children if getattr(b, "is_prev", False)), None)
        next_button = next((b for b in self.children if getattr(b, "is_next", False)), None)
        
        # Update button states
        if prev_button:
            prev_button.disabled = self.current_page == 0
        
        if next_button:
            next_button.disabled = self.current_page == len(self.items) - 1

class CarouselButton(ui.Button):
    """Button for carousel navigation."""
    
    def __init__(self, is_next: bool = True, style: discord.ButtonStyle = discord.ButtonStyle.secondary, row: int = 0):
        self.is_next = is_next
        self.is_prev = not is_next
        emoji = "➡️" if is_next else "⬅️"
        super().__init__(style=style, emoji=emoji, row=row)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        
        if self.is_next and view.current_page < view.max_pages - 1:
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
