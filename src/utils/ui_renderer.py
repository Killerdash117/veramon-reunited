import discord
from typing import Dict, Any, Optional, List, Union, Tuple
import json
import os
import random
from datetime import datetime

from src.utils.ui_theme import theme_manager, ThemeColorType, create_themed_embed
from src.utils.user_settings import get_user_settings

# Constants
ASSET_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
VERAMON_IMAGES_PATH = os.path.join(ASSET_BASE_PATH, "veramon")
ICON_PATH = os.path.join(ASSET_BASE_PATH, "icons")
BADGE_PATH = os.path.join(ASSET_BASE_PATH, "badges")
IMAGE_PLACEHOLDER = "https://via.placeholder.com/256?text=Veramon"

class UIRenderer:
    """
    Handles rendering UI elements for the bot.
    Controls how Veramon, battles, and other game elements appear in Discord.
    """
    
    @staticmethod
    def get_veramon_image_url(veramon_name: str, shiny: bool = False, form: str = "default") -> str:
        """
        Get the URL for a Veramon image.
        
        Args:
            veramon_name: The name of the Veramon
            shiny: Whether to show the shiny version
            form: The form of the Veramon (default, alt, mega, etc.)
            
        Returns:
            URL to the Veramon image
        """
        # Local image (if available)
        image_name = veramon_name.lower().replace(" ", "_")
        if shiny:
            image_name += "_shiny"
        if form != "default":
            image_name += f"_{form.lower()}"
            
        # Check if file exists
        image_path = os.path.join(VERAMON_IMAGES_PATH, f"{image_name}.png")
        if os.path.exists(image_path):
            # Return Discord CDN URL when deployed
            return f"attachment://{image_name}.png"
            
        # Fallback to placeholder or remote URL
        # This would be a URL to your image hosting service
        return IMAGE_PLACEHOLDER
        
    @staticmethod
    def get_type_icon_url(type_name: str) -> str:
        """Get URL for a type icon."""
        type_name = type_name.lower().replace(" ", "_")
        icon_path = os.path.join(ICON_PATH, "types", f"{type_name}.png")
        
        if os.path.exists(icon_path):
            return f"attachment://{type_name}_type.png"
            
        return f"https://via.placeholder.com/32?text={type_name}"
        
    @staticmethod
    def get_badge_url(badge_name: str) -> str:
        """Get URL for a badge."""
        badge_name = badge_name.lower().replace(" ", "_")
        badge_path = os.path.join(BADGE_PATH, f"{badge_name}.png")
        
        if os.path.exists(badge_path):
            return f"attachment://{badge_name}_badge.png"
            
        return f"https://via.placeholder.com/64?text={badge_name}"
        
    @staticmethod
    def get_veramon_thumbnail(veramon_data: Dict[str, Any], user_settings: Dict[str, Any] = None) -> Optional[str]:
        """Get appropriate thumbnail for a Veramon based on user settings."""
        if user_settings and not user_settings.get("show_veramon_images", True):
            return None
            
        shiny = veramon_data.get("shiny", False)
        form = veramon_data.get("form", "default")
        
        return UIRenderer.get_veramon_image_url(
            veramon_data["veramon_name"],
            shiny=shiny,
            form=form
        )
        
    @staticmethod
    def create_veramon_embed(
        user_id: str,
        veramon_data: Dict[str, Any],
        detailed: bool = False
    ) -> discord.Embed:
        """
        Create an embed to display a Veramon.
        
        Args:
            user_id: Discord user ID
            veramon_data: Data about the Veramon
            detailed: Whether to show detailed stats
            
        Returns:
            Discord Embed for the Veramon
        """
        # Get user preferences
        settings = get_user_settings(user_id)
        
        # Get Veramon info
        veramon_name = veramon_data.get("veramon_name", "Unknown Veramon")
        nickname = veramon_data.get("nickname", "")
        level = veramon_data.get("level", 1)
        shiny = veramon_data.get("shiny", False)
        
        # Format the title
        title = f"{nickname} ({veramon_name})" if nickname else veramon_name
        if shiny:
            title = f"✨ {title}"
            
        # Create the embed
        embed = create_themed_embed(
            user_id,
            title=title,
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add basic info
        types = veramon_data.get("types", [])
        types_str = ", ".join([t.capitalize() for t in types])
        
        embed.add_field(
            name="Type",
            value=types_str,
            inline=True
        )
        
        embed.add_field(
            name="Level",
            value=str(level),
            inline=True
        )
        
        # Add experience info if available
        if "experience" in veramon_data:
            current_exp = veramon_data["experience"]
            next_level_exp = (level * 100) + 50  # Example formula
            
            # Create experience bar
            progress = min(1.0, current_exp / next_level_exp)
            bar_length = 10
            filled_bars = int(progress * bar_length)
            
            exp_bar = "▰" * filled_bars + "▱" * (bar_length - filled_bars)
            
            embed.add_field(
                name="Experience",
                value=f"{exp_bar} ({current_exp}/{next_level_exp})",
                inline=True
            )
            
        # Add detailed stats if requested
        if detailed:
            # Add stats
            stats = veramon_data.get("stats", {})
            
            stats_text = ""
            if stats:
                stats_text += f"**HP:** {stats.get('hp', 0)}\n"
                stats_text += f"**Attack:** {stats.get('attack', 0)}\n"
                stats_text += f"**Defense:** {stats.get('defense', 0)}\n"
                stats_text += f"**Sp. Attack:** {stats.get('sp_attack', 0)}\n"
                stats_text += f"**Sp. Defense:** {stats.get('sp_defense', 0)}\n"
                stats_text += f"**Speed:** {stats.get('speed', 0)}\n"
            else:
                stats_text = "No stats available"
                
            embed.add_field(
                name="Stats",
                value=stats_text,
                inline=False
            )
            
            # Add moves
            moves = veramon_data.get("moves", [])
            move_text = ""
            
            if moves:
                for i, move in enumerate(moves[:4]):
                    move_name = move if isinstance(move, str) else move.get("name", "Unknown")
                    move_text += f"• {move_name}\n"
            else:
                move_text = "No moves learned"
                
            embed.add_field(
                name="Moves",
                value=move_text,
                inline=True
            )
            
            # Add ability if available
            ability = veramon_data.get("ability", "")
            if ability:
                embed.add_field(
                    name="Ability",
                    value=ability,
                    inline=True
                )
                
        # Add capture info if available
        if "caught_at" in veramon_data:
            caught_at = veramon_data["caught_at"]
            biome = veramon_data.get("biome", "Unknown")
            
            embed.add_field(
                name="Captured",
                value=f"Location: {biome}\nDate: {caught_at}",
                inline=False
            )
            
        # Add flavor text if available and no detailed stats
        if not detailed and "flavor_text" in veramon_data:
            embed.add_field(
                name="Description",
                value=veramon_data["flavor_text"],
                inline=False
            )
            
        # Set thumbnail if images are enabled
        if settings.get("show_veramon_images", True):
            thumbnail_url = UIRenderer.get_veramon_thumbnail(veramon_data)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
                
        return embed
        
    @staticmethod
    def create_battle_embed(
        user_id: str,
        battle_data: Dict[str, Any],
        current_turn: bool = False
    ) -> discord.Embed:
        """
        Create an embed for a battle.
        
        Args:
            user_id: Discord user ID
            battle_data: Data about the battle
            current_turn: Whether to highlight the current turn
            
        Returns:
            Discord Embed for the battle
        """
        # Get user preferences
        settings = get_user_settings(user_id)
        
        # Create the embed
        embed = create_themed_embed(
            user_id,
            title=f"Battle #{battle_data.get('id', '?')}",
            description=f"Battle Type: {battle_data.get('battle_type', 'Unknown').upper()}",
            color_type=ThemeColorType.DANGER
        )
        
        # Add participants
        participants = battle_data.get("participants", [])
        
        if participants:
            for i, participant in enumerate(participants):
                # Format participant info
                username = participant.get("username", f"Trainer {i+1}")
                side = participant.get("side", "?")
                is_current = participant.get("is_current", False)
                
                # Get active Veramon
                active_veramon = participant.get("active_veramon", None)
                
                if active_veramon:
                    veramon_name = active_veramon.get("nickname") or active_veramon.get("veramon_name", "?")
                    veramon_hp = active_veramon.get("current_hp", 0)
                    veramon_max_hp = active_veramon.get("max_hp", 0)
                    
                    # Calculate HP percentage
                    hp_percent = max(0, min(1.0, veramon_hp / veramon_max_hp))
                    bar_length = 10
                    filled_bars = int(hp_percent * bar_length)
                    
                    hp_bar = "█" * filled_bars + "░" * (bar_length - filled_bars)
                    
                    # Format display with optional current turn indicator
                    name_prefix = "➡️ " if is_current and current_turn else ""
                    value = f"**Active:** {veramon_name}\n**HP:** {hp_bar} ({veramon_hp}/{veramon_max_hp})"
                else:
                    value = "No active Veramon"
                    
                embed.add_field(
                    name=f"{name_prefix}Trainer: {username} (Side {side})",
                    value=value,
                    inline=False
                )
                
        # Add battle log if available
        battle_log = battle_data.get("battle_log", [])
        if battle_log:
            # Show the last 5 log entries
            recent_log = battle_log[-5:]
            log_text = "\n".join([f"• {entry}" for entry in recent_log])
            
            embed.add_field(
                name="Recent Battle Actions",
                value=log_text or "No recent actions",
                inline=False
            )
            
        return embed
        
    @staticmethod
    def create_trade_embed(
        user_id: str,
        trade_data: Dict[str, Any]
    ) -> discord.Embed:
        """
        Create an embed for a trade.
        
        Args:
            user_id: Discord user ID
            trade_data: Data about the trade
            
        Returns:
            Discord Embed for the trade
        """
        settings = get_user_settings(user_id)
        
        # Get trade info
        trade_id = trade_data.get("id", "?")
        initiator = trade_data.get("initiator_name", "Unknown")
        recipient = trade_data.get("recipient_name", "Unknown")
        status = trade_data.get("status", "pending").upper()
        
        # Create embed
        embed = create_themed_embed(
            user_id,
            title=f"Trade #{trade_id}",
            description=f"Status: {status}",
            color_type=ThemeColorType.ACCENT
        )
        
        # Add initiator's offers
        initiator_offers = trade_data.get("initiator_offers", [])
        if initiator_offers:
            offer_text = ""
            for i, offer in enumerate(initiator_offers):
                veramon_name = offer.get("nickname") or offer.get("veramon_name", "?")
                level = offer.get("level", "?")
                shiny = "✨ " if offer.get("shiny", False) else ""
                
                offer_text += f"{i+1}. {shiny}{veramon_name} (Lvl {level})\n"
        else:
            offer_text = "No Veramon offered"
            
        embed.add_field(
            name=f"Offered by {initiator}",
            value=offer_text,
            inline=True
        )
        
        # Add recipient's offers
        recipient_offers = trade_data.get("recipient_offers", [])
        if recipient_offers:
            offer_text = ""
            for i, offer in enumerate(recipient_offers):
                veramon_name = offer.get("nickname") or offer.get("veramon_name", "?")
                level = offer.get("level", "?")
                shiny = "✨ " if offer.get("shiny", False) else ""
                
                offer_text += f"{i+1}. {shiny}{veramon_name} (Lvl {level})\n"
        else:
            offer_text = "No Veramon offered"
            
        embed.add_field(
            name=f"Offered by {recipient}",
            value=offer_text,
            inline=True
        )
        
        # Add timestamps if requested
        if settings.get("show_timestamps", True):
            created_at = trade_data.get("created_at", "")
            if created_at:
                embed.set_footer(text=f"Created: {created_at}")
                
        return embed
        
    @staticmethod
    def create_profile_embed(
        user_id: str,
        profile_data: Dict[str, Any]
    ) -> discord.Embed:
        """
        Create an embed for a user profile.
        
        Args:
            user_id: Discord user ID
            profile_data: Data about the user's profile
            
        Returns:
            Discord Embed for the profile
        """
        settings = get_user_settings(user_id)
        
        # Get profile info
        username = profile_data.get("username", "Trainer")
        title = profile_data.get("title", "")
        bio = profile_data.get("bio", "No bio provided")
        
        # Get stats
        veramon_count = profile_data.get("veramon_count", 0)
        shiny_count = profile_data.get("shiny_count", 0)
        tokens = profile_data.get("tokens", 0)
        battles_won = profile_data.get("battles_won", 0)
        battles_lost = profile_data.get("battles_lost", 0)
        
        # Create title with optional title
        full_title = f"{username}" if not title else f"{username} - {title}"
        
        # Create embed with custom color if set
        custom_color = profile_data.get("color", None)
        
        if custom_color:
            try:
                color = int(custom_color.lstrip('#'), 16)
            except ValueError:
                color = None
        else:
            color = None
            
        if color:
            embed = discord.Embed(
                title=full_title,
                description=bio,
                color=color
            )
        else:
            embed = create_themed_embed(
                user_id,
                title=full_title,
                description=bio,
                color_type=ThemeColorType.ACCENT
            )
            
        # Add collection stats
        collection_stats = f"**Veramon Caught:** {veramon_count}\n"
        collection_stats += f"**Shiny Veramon:** {shiny_count}\n"
        collection_stats += f"**Completion Rate:** {int((veramon_count / 300) * 100)}%\n"
        
        embed.add_field(
            name="Collection",
            value=collection_stats,
            inline=True
        )
        
        # Add battle stats
        battle_stats = f"**Wins:** {battles_won}\n"
        battle_stats += f"**Losses:** {battles_lost}\n"
        
        if battles_won + battles_lost > 0:
            win_rate = int((battles_won / (battles_won + battles_lost)) * 100)
            battle_stats += f"**Win Rate:** {win_rate}%\n"
            
        embed.add_field(
            name="Battle Record",
            value=battle_stats,
            inline=True
        )
        
        # Add economy info
        embed.add_field(
            name="Economy",
            value=f"**Tokens:** {tokens:,}",
            inline=True
        )
        
        # Add badges if available
        badges = profile_data.get("badges", [])
        if badges:
            badge_text = ", ".join([f"`{badge}`" for badge in badges[:5]])
            if len(badges) > 5:
                badge_text += f" and {len(badges) - 5} more"
                
            embed.add_field(
                name="Badges",
                value=badge_text,
                inline=False
            )
            
        # Add favorite Veramon if available
        favorite = profile_data.get("favorite_veramon", None)
        if favorite and settings.get("show_veramon_images", True):
            # Create thumbnail URL
            thumbnail_url = UIRenderer.get_veramon_thumbnail(favorite)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
                
                # Add favorite text
                fav_name = favorite.get("nickname") or favorite.get("veramon_name", "?")
                fav_text = profile_data.get("showcase_message", f"Favorite Veramon: {fav_name}")
                
                embed.add_field(
                    name="Showcase",
                    value=fav_text,
                    inline=False
                )
                
        return embed

# Create global renderer instance
ui_renderer = UIRenderer()
