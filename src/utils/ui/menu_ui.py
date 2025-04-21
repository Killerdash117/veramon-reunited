"""
Menu UI Component for Veramon Reunited
--------------------------------------
This module provides Discord UI components for the main menu system, including:
- Main navigation menu
- Pagination controls
- Selection menus for Veramon categories
- Filtering and sorting options

These components create an intuitive interface for the Discord bot commands.
"""

import discord
from discord import ui
from discord.ui import Button, View, Select
from typing import List, Dict, Any, Optional, Union, Callable
import logging

# Set up logging
logger = logging.getLogger("menu_ui")

class MenuButton(Button):
    """Button for menu navigation."""
    
    def __init__(self, label: str, custom_id: str, style: discord.ButtonStyle = discord.ButtonStyle.primary, emoji: str = None, disabled: bool = False):
        """
        Initialize a menu button.
        
        Args:
            label: Button label
            custom_id: Button ID for callback reference
            style: Button style
            emoji: Optional emoji to display
            disabled: Whether the button is disabled
        """
        super().__init__(style=style, label=label, custom_id=custom_id, emoji=emoji, disabled=disabled)

class PaginationView(View):
    """View for pagination controls."""
    
    def __init__(self, current_page: int, total_pages: int, timeout: float = 60.0):
        """
        Initialize pagination controls.
        
        Args:
            current_page: Current page number
            total_pages: Total number of pages
            timeout: Button timeout in seconds
        """
        super().__init__(timeout=timeout)
        self.current_page = current_page
        self.total_pages = total_pages
        self.page_callback = None
        
        # Add navigation buttons
        self.add_navigation_buttons()
    
    def add_navigation_buttons(self):
        """Add navigation buttons to the view."""
        # First page button
        first_button = Button(
            style=discord.ButtonStyle.secondary,
            label="⏮️",
            custom_id="page_first",
            disabled=(self.current_page <= 1)
        )
        first_button.callback = self._create_page_callback(1)
        
        # Previous page button
        prev_button = Button(
            style=discord.ButtonStyle.primary,
            label="◀️",
            custom_id="page_prev",
            disabled=(self.current_page <= 1)
        )
        prev_button.callback = self._create_page_callback(self.current_page - 1)
        
        # Page indicator (non-interactive)
        page_indicator = Button(
            style=discord.ButtonStyle.secondary,
            label=f"Page {self.current_page}/{self.total_pages}",
            custom_id="page_indicator",
            disabled=True
        )
        
        # Next page button
        next_button = Button(
            style=discord.ButtonStyle.primary,
            label="▶️",
            custom_id="page_next",
            disabled=(self.current_page >= self.total_pages)
        )
        next_button.callback = self._create_page_callback(self.current_page + 1)
        
        # Last page button
        last_button = Button(
            style=discord.ButtonStyle.secondary,
            label="⏭️",
            custom_id="page_last",
            disabled=(self.current_page >= self.total_pages)
        )
        last_button.callback = self._create_page_callback(self.total_pages)
        
        # Add all buttons to the view
        self.add_item(first_button)
        self.add_item(prev_button)
        self.add_item(page_indicator)
        self.add_item(next_button)
        self.add_item(last_button)
    
    def set_page_callback(self, callback: Callable):
        """Set the page change callback."""
        self.page_callback = callback
    
    def _create_page_callback(self, page_number: int):
        """Create a callback for a pagination button."""
        async def callback(interaction: discord.Interaction):
            # Validate page number
            page = max(1, min(page_number, self.total_pages))
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the page callback if it exists
            if self.page_callback:
                await self.page_callback(page, interaction)
        
        return callback

class VeramonFilterSelect(Select):
    """Dropdown select for filtering Veramon lists."""
    
    def __init__(self, filter_type: str, options: List[str], custom_id: str = None):
        """
        Initialize a Veramon filter dropdown.
        
        Args:
            filter_type: Type of filter (type, rarity, etc.)
            options: List of filter options
            custom_id: Custom ID for the select
        """
        # Create select options
        select_options = [
            discord.SelectOption(label=option.capitalize(), value=option.lower())
            for option in options
        ]
        
        # Add an "All" option at the beginning
        select_options.insert(0, discord.SelectOption(label="All", value="all"))
        
        # Set placeholder based on filter type
        placeholder = f"Filter by {filter_type.capitalize()}..."
        
        # Generate custom ID if not provided
        if custom_id is None:
            custom_id = f"filter_{filter_type.lower()}"
        
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=select_options,
            custom_id=custom_id
        )
        
        self.filter_type = filter_type

class VeramonSortSelect(Select):
    """Dropdown select for sorting Veramon lists."""
    
    def __init__(self, custom_id: str = "sort_veramon"):
        """
        Initialize a Veramon sort dropdown.
        
        Args:
            custom_id: Custom ID for the select
        """
        # Create sort options
        options = [
            discord.SelectOption(label="ID (Ascending)", value="id_asc"),
            discord.SelectOption(label="ID (Descending)", value="id_desc"),
            discord.SelectOption(label="Name (A-Z)", value="name_asc"),
            discord.SelectOption(label="Name (Z-A)", value="name_desc"),
            discord.SelectOption(label="Rarity (Common First)", value="rarity_asc"),
            discord.SelectOption(label="Rarity (Rare First)", value="rarity_desc"),
            discord.SelectOption(label="Type", value="type")
        ]
        
        # Set placeholder
        placeholder = "Sort by..."
        
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            custom_id=custom_id
        )

class MainMenuView(View):
    """Main menu view with category buttons."""
    
    def __init__(self, timeout: float = 180.0):
        """
        Initialize the main menu view.
        
        Args:
            timeout: Button timeout in seconds
        """
        super().__init__(timeout=timeout)
        
        # Add main category buttons
        self.add_category_buttons()
    
    def add_category_buttons(self):
        """Add main category buttons to the view."""
        # Veramon Dex button
        dex_button = Button(
            style=discord.ButtonStyle.primary,
            label="Veradex",
            emoji="📖",
            custom_id="menu_veradex"
        )
        
        # My Veramon button
        my_veramon_button = Button(
            style=discord.ButtonStyle.success,
            label="My Veramon",
            emoji="🧪",
            custom_id="menu_my_veramon"
        )
        
        # Battle button
        battle_button = Button(
            style=discord.ButtonStyle.danger,
            label="Battle",
            emoji="⚔️",
            custom_id="menu_battle"
        )
        
        # Trading button
        trading_button = Button(
            style=discord.ButtonStyle.secondary,
            label="Trading",
            emoji="🔄",
            custom_id="menu_trading"
        )
        
        # Settings button
        settings_button = Button(
            style=discord.ButtonStyle.secondary,
            label="Settings",
            emoji="⚙️",
            custom_id="menu_settings"
        )
        
        # Add all buttons to the view
        self.add_item(dex_button)
        self.add_item(my_veramon_button)
        self.add_item(battle_button)
        self.add_item(trading_button)
        self.add_item(settings_button)
    
    def set_callbacks(self, callback_map: Dict[str, Callable]):
        """
        Set callbacks for each button.
        
        Args:
            callback_map: Dictionary mapping button IDs to callback functions
        """
        for child in self.children:
            if isinstance(child, Button) and child.custom_id in callback_map:
                child.callback = callback_map[child.custom_id]

class VeramonListView(View):
    """View for Veramon list with filters and pagination."""
    
    def __init__(self, filter_options: Dict[str, List[str]] = None, timeout: float = 120.0):
        """
        Initialize a Veramon list view.
        
        Args:
            filter_options: Dictionary of filter options
            timeout: Component timeout in seconds
        """
        super().__init__(timeout=timeout)
        
        # Add filter and sort components
        if filter_options:
            self.add_filter_components(filter_options)
            
    def add_filter_components(self, filter_options: Dict[str, List[str]]):
        """
        Add filter components to the view.
        
        Args:
            filter_options: Dictionary mapping filter types to option lists
        """
        # Add type filter if options provided
        if "type" in filter_options:
            type_select = VeramonFilterSelect("type", filter_options["type"])
            self.add_item(type_select)
        
        # Add rarity filter if options provided
        if "rarity" in filter_options:
            rarity_select = VeramonFilterSelect("rarity", filter_options["rarity"])
            self.add_item(rarity_select)
        
        # Add sort select
        sort_select = VeramonSortSelect()
        self.add_item(sort_select)
    
    def set_callbacks(self, filter_callback: Callable, sort_callback: Callable):
        """
        Set callbacks for filter and sort components.
        
        Args:
            filter_callback: Callback for filter selects
            sort_callback: Callback for sort select
        """
        for child in self.children:
            if isinstance(child, VeramonFilterSelect):
                child.callback = self._create_filter_callback(child.filter_type, filter_callback)
            elif isinstance(child, VeramonSortSelect):
                child.callback = self._create_sort_callback(sort_callback)
    
    def _create_filter_callback(self, filter_type: str, callback: Callable):
        """Create a callback for a filter select."""
        async def filter_callback(interaction: discord.Interaction):
            # Get selected value
            value = interaction.data["values"][0]
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the filter callback
            await callback(filter_type, value, interaction)
        
        return filter_callback
    
    def _create_sort_callback(self, callback: Callable):
        """Create a callback for the sort select."""
        async def sort_callback(interaction: discord.Interaction):
            # Get selected value
            value = interaction.data["values"][0]
            
            # Acknowledge the interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the sort callback
            await callback(value, interaction)
        
        return sort_callback

class MenuUI:
    """Main class for creating menu UI components."""
    
    @staticmethod
    def create_main_menu_embed(user_name: str, veramon_count: int) -> discord.Embed:
        """
        Create an embed for the main menu.
        
        Args:
            user_name: Name of the user
            veramon_count: Number of Veramon the user has
            
        Returns:
            discord.Embed: Main menu embed
        """
        embed = discord.Embed(
            title="Veramon Reunited",
            description=f"Welcome, **{user_name}**!",
            color=discord.Color.blue()
        )
        
        # Add user stats
        embed.add_field(
            name="Your Collection",
            value=f"You have **{veramon_count}** Veramon",
            inline=True
        )
        
        # Add version info
        embed.add_field(
            name="Version",
            value="1.0.0",
            inline=True
        )
        
        # Add footer
        embed.set_footer(text="Select an option below to continue")
        
        return embed
    
    @staticmethod
    def create_veramon_list_embed(
        veramon_list: List[Dict[str, Any]],
        current_page: int,
        total_pages: int,
        filters: Dict[str, str] = None,
        sort_by: str = None
    ) -> discord.Embed:
        """
        Create an embed for a Veramon list.
        
        Args:
            veramon_list: List of Veramon to display
            current_page: Current page number
            total_pages: Total number of pages
            filters: Applied filters
            sort_by: Applied sort
            
        Returns:
            discord.Embed: Veramon list embed
        """
        # Determine title based on applied filters
        title = "Veramon List"
        if filters and any(filters.values()):
            filter_parts = []
            for key, value in filters.items():
                if value and value != "all":
                    filter_parts.append(f"{key.capitalize()}: {value.capitalize()}")
            
            if filter_parts:
                title = f"Filtered Veramon: {', '.join(filter_parts)}"
        
        embed = discord.Embed(
            title=title,
            description=f"Displaying page {current_page} of {total_pages}",
            color=discord.Color.green()
        )
        
        # Add each Veramon to the embed
        for veramon in veramon_list:
            name = veramon.get("name", "Unknown")
            types = ", ".join(veramon.get("type", ["Unknown"]))
            rarity = veramon.get("rarity", "common").capitalize()
            
            # Format additional info
            info = []
            if "level" in veramon:
                info.append(f"Lv.{veramon['level']}")
            if "catch_rate" in veramon:
                catch_rate = int(veramon["catch_rate"] * 100)
                info.append(f"Catch: {catch_rate}%")
            
            # Format value with types and rarity
            value = f"Type: {types}\nRarity: {rarity}"
            
            # Add additional info if available
            if info:
                value += f"\n{' | '.join(info)}"
            
            embed.add_field(
                name=name,
                value=value,
                inline=True
            )
        
        # Add sort info to footer
        footer_text = f"Page {current_page}/{total_pages}"
        if sort_by:
            sort_name = {
                "id_asc": "ID (Ascending)",
                "id_desc": "ID (Descending)",
                "name_asc": "Name (A-Z)",
                "name_desc": "Name (Z-A)",
                "rarity_asc": "Rarity (Common First)",
                "rarity_desc": "Rarity (Rare First)",
                "type": "Type"
            }.get(sort_by, sort_by)
            
            footer_text += f" • Sorted by: {sort_name}"
        
        embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def create_main_menu() -> MainMenuView:
        """
        Create a main menu view.
        
        Returns:
            MainMenuView: Main menu with category buttons
        """
        return MainMenuView()
    
    @staticmethod
    def create_pagination_controls(current_page: int, total_pages: int) -> PaginationView:
        """
        Create pagination controls.
        
        Args:
            current_page: Current page number
            total_pages: Total number of pages
            
        Returns:
            PaginationView: Pagination controls view
        """
        return PaginationView(current_page, total_pages)
    
    @staticmethod
    def create_veramon_list_view(filter_options: Dict[str, List[str]] = None) -> VeramonListView:
        """
        Create a Veramon list view with filters.
        
        Args:
            filter_options: Dictionary of filter options
            
        Returns:
            VeramonListView: Veramon list view with filters
        """
        return VeramonListView(filter_options)
