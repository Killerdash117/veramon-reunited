"""
UI Registry for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides a central registry for accessing and managing UI components.
"""

import discord
import logging
from typing import Dict, Any, Optional, Union, Type

from src.utils.ui.interactive_ui import InteractiveView, CarouselView, EnhancedSelectionView
from src.utils.ui.battle_ui_enhanced import BattleUI
from src.utils.ui.trading_ui_enhanced import TradeUI, TradeItemDisplay
from src.utils.ui_theme import theme_manager, ThemeColorType

# Set up logging
logger = logging.getLogger('veramon.ui_registry')

class UIRegistry:
    """
    Central registry for creating and managing UI components.
    
    This class provides factory methods for creating UI components with consistent
    theming and styling, making it easy to maintain a unified look and feel
    throughout the application.
    """
    
    def __init__(self):
        """Initialize the UI registry."""
        self.theme_manager = theme_manager
        
        # Store active views by key for reference
        self.active_views = {}
    
    def get_themed_embed(
        self, 
        user_id: str, 
        title: str = None, 
        description: str = None,
        color_type: ThemeColorType = ThemeColorType.PRIMARY,
        **kwargs
    ) -> discord.Embed:
        """
        Create a themed embed for a user.
        
        Args:
            user_id: The user's ID for theme preferences
            title: Embed title
            description: Embed description
            color_type: Type of color to use
            **kwargs: Additional embed parameters
        
        Returns:
            A themed discord.Embed
        """
        theme = self.theme_manager.get_user_theme(user_id)
        embed = theme.create_embed(title, description, color_type)
        
        # Add additional fields if provided
        if "fields" in kwargs:
            for field in kwargs["fields"]:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False)
                )
        
        # Set author if provided
        if "author" in kwargs:
            embed.set_author(
                name=kwargs["author"].get("name", ""),
                icon_url=kwargs["author"].get("icon_url", None)
            )
        
        # Set footer if provided
        if "footer" in kwargs:
            embed.set_footer(
                text=kwargs["footer"].get("text", ""),
                icon_url=kwargs["footer"].get("icon_url", None)
            )
        
        # Set image if provided
        if "image_url" in kwargs:
            embed.set_image(url=kwargs["image_url"])
        
        # Set thumbnail if provided
        if "thumbnail_url" in kwargs:
            embed.set_thumbnail(url=kwargs["thumbnail_url"])
        
        return embed
    
    def create_battle_ui(
        self,
        user_id: str,
        battle_id: int,
        battle_manager,
        opponent_id: Optional[str] = None,
        is_wild: bool = False,
        **kwargs
    ) -> BattleUI:
        """
        Create a battle UI component.
        
        Args:
            user_id: The user's ID
            battle_id: ID of the battle
            battle_manager: Reference to battle manager
            opponent_id: ID of opponent (if any)
            is_wild: Whether this is a wild encounter
            **kwargs: Additional parameters
        
        Returns:
            A BattleUI instance
        """
        battle_ui = BattleUI(
            user_id=user_id,
            battle_id=battle_id,
            battle_manager=battle_manager,
            opponent_id=opponent_id,
            is_wild=is_wild,
            **kwargs
        )
        
        # Store reference
        key = f"battle_{battle_id}"
        self.active_views[key] = battle_ui
        
        return battle_ui
    
    def create_trade_ui(
        self,
        user_id: str,
        trade_id: str,
        trade_manager,
        receiver_id: str,
        **kwargs
    ) -> TradeUI:
        """
        Create a trade UI component.
        
        Args:
            user_id: The user's ID
            trade_id: ID of the trade
            trade_manager: Reference to trade manager
            receiver_id: ID of the trade receiver
            **kwargs: Additional parameters
        
        Returns:
            A TradeUI instance
        """
        trade_ui = TradeUI(
            user_id=user_id,
            trade_id=trade_id,
            trade_manager=trade_manager,
            receiver_id=receiver_id,
            **kwargs
        )
        
        # Store reference
        key = f"trade_{trade_id}"
        self.active_views[key] = trade_ui
        
        return trade_ui
    
    def create_carousel(
        self,
        user_id: str,
        pages: Optional[list] = None,
        **kwargs
    ) -> CarouselView:
        """
        Create a carousel view.
        
        Args:
            user_id: The user's ID
            pages: Initial pages for the carousel
            **kwargs: Additional parameters
        
        Returns:
            A CarouselView instance
        """
        carousel = CarouselView(
            user_id=user_id,
            **kwargs
        )
        
        # Add pages if provided
        if pages:
            for page in pages:
                carousel.add_page(page)
        
        return carousel
    
    def create_selection_menu(
        self,
        user_id: str,
        placeholder: str = "Select an option",
        min_values: int = 1,
        max_values: int = 1,
        **kwargs
    ) -> EnhancedSelectionView:
        """
        Create an enhanced selection menu.
        
        Args:
            user_id: The user's ID
            placeholder: Placeholder text for the menu
            min_values: Minimum number of selections
            max_values: Maximum number of selections
            **kwargs: Additional parameters
        
        Returns:
            An EnhancedSelectionView instance
        """
        selection_view = EnhancedSelectionView(
            user_id=user_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            **kwargs
        )
        
        return selection_view
    
    def create_trade_item_display(
        self,
        user_id: str,
        items: list,
        **kwargs
    ) -> TradeItemDisplay:
        """
        Create a trade item display carousel.
        
        Args:
            user_id: The user's ID
            items: Items to display
            **kwargs: Additional parameters
        
        Returns:
            A TradeItemDisplay instance
        """
        item_display = TradeItemDisplay(
            user_id=user_id,
            items=items,
            **kwargs
        )
        
        return item_display
    
    def get_active_view(self, key: str) -> Optional[InteractiveView]:
        """
        Get an active view by key.
        
        Args:
            key: The view key
        
        Returns:
            The view instance if found, None otherwise
        """
        return self.active_views.get(key)
    
    def remove_active_view(self, key: str) -> bool:
        """
        Remove an active view by key.
        
        Args:
            key: The view key
        
        Returns:
            True if removed, False otherwise
        """
        if key in self.active_views:
            del self.active_views[key]
            return True
        return False
    
    def cleanup_expired_views(self):
        """Remove expired views from the registry."""
        expired_keys = []
        
        for key, view in self.active_views.items():
            if view.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.active_views[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired views")

# Create global instance
ui_registry = UIRegistry()

def get_ui_registry() -> UIRegistry:
    """Get the global UI registry instance."""
    global ui_registry
    return ui_registry
