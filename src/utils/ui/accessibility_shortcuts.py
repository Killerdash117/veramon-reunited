"""
Accessibility Shortcuts for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides command aliases and shortcut buttons for accessibility features.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable, Union

from src.utils.ui.accessibility import (
    get_accessibility_manager,
    TextSize,
    AnimationLevel,
    ColorMode
)
from src.utils.ui_theme import theme_manager, ThemeColorType

# Set up logging
logger = logging.getLogger('veramon.accessibility_shortcuts')

# Mapping of shortcut buttons to actions
SHORTCUT_MAPPINGS = {
    # Format: 'button_id': ('action_name', 'label', 'description')
    'text_size': ('toggle_text_size', 'Aa', 'Toggle between text sizes'),
    'color_mode': ('toggle_color_mode', '🎨', 'Toggle between color modes'),
    'animations': ('toggle_animations', '🎬', 'Toggle animations on/off'),
    'simplified_ui': ('toggle_simplified_ui', '📱', 'Toggle simplified UI'),
    'high_contrast': ('toggle_high_contrast', '👁️', 'Toggle high contrast mode'),
    'extended_timeout': ('toggle_extended_timeouts', '⏱️', 'Toggle extended timeouts'),
    'screen_reader': ('toggle_screen_reader', '🔊', 'Toggle screen reader support'),
    'button_spacing': ('toggle_button_spacing', '↔️', 'Toggle extra button spacing'),
}

# Mapping of command aliases to full commands
COMMAND_ALIASES = {
    # Format: 'alias': ('full_command', 'description')
    'a11y': ('accessibility', 'Open accessibility settings'),
    'access': ('accessibility', 'Open accessibility settings'),
    'text': ('text_size medium', 'Change text size to medium'),
    'bigtext': ('text_size large', 'Change text size to large'),
    'smalltext': ('text_size small', 'Change text size to small'),
    'color': ('color_mode normal', 'Change color mode to normal'),
    'contrast': ('color_mode high_contrast', 'Enable high contrast mode'),
    'colorblind': ('color_mode deuteranopia', 'Enable colorblind mode'),
    'simple': ('toggle_simplified_ui', 'Toggle simplified UI'),
    'timeout': ('toggle_extended_timeouts', 'Toggle extended timeouts'),
    'noanimations': ('toggle_animations none', 'Disable animations'),
    'animations': ('toggle_animations full', 'Enable full animations'),
    'reader': ('toggle_screen_reader', 'Toggle screen reader support'),
    'buttons': ('toggle_button_spacing', 'Toggle extra button spacing'),
}

class ShortcutButtonsView(discord.ui.View):
    """
    View that provides shortcut buttons for accessibility features.
    """
    
    def __init__(self, bot, user_id: str, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.user_id = user_id
        self.accessibility_manager = get_accessibility_manager()
        
        # Add shortcut buttons
        self._add_shortcut_buttons()
    
    def _add_shortcut_buttons(self):
        """Add all shortcut buttons to the view."""
        # Get user theme for colors
        theme = theme_manager.get_user_theme(self.user_id)
        
        # Row 1: Text and color settings
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Aa",
            custom_id="shortcut:text_size",
            row=0
        ))
        
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="🎨",
            custom_id="shortcut:color_mode",
            row=0
        ))
        
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="👁️",
            custom_id="shortcut:high_contrast",
            row=0
        ))
        
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="🔊",
            custom_id="shortcut:screen_reader",
            row=0
        ))
        
        # Row 2: UI and interaction settings
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="📱",
            custom_id="shortcut:simplified_ui",
            row=1
        ))
        
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="🎬",
            custom_id="shortcut:animations",
            row=1
        ))
        
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="⏱️",
            custom_id="shortcut:extended_timeout",
            row=1
        ))
        
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="↔️",
            custom_id="shortcut:button_spacing",
            row=1
        ))
        
        # Row 3: Help and settings
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Settings",
            custom_id="shortcut:open_settings",
            row=2
        ))
        
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Close",
            custom_id="shortcut:close",
            row=2
        ))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user interacting is the owner of these shortcuts."""
        return str(interaction.user.id) == self.user_id

class AccessibilityShortcutsHandler:
    """Handles shortcuts for accessibility features."""
    
    def __init__(self, bot):
        self.bot = bot
        self.accessibility_manager = get_accessibility_manager()
    
    async def handle_shortcut(self, interaction: discord.Interaction) -> bool:
        """
        Handle a shortcut button press.
        
        Args:
            interaction: The Discord interaction
            
        Returns:
            bool: True if handled, False otherwise
        """
        custom_id = interaction.data.get("custom_id", "")
        
        if not custom_id.startswith("shortcut:"):
            return False
        
        shortcut_id = custom_id.split(":", 1)[1]
        user_id = str(interaction.user.id)
        
        # Special cases
        if shortcut_id == "open_settings":
            # Get accessibility cog to open settings
            accessibility_cog = self.bot.get_cog("AccessibilityCog")
            if accessibility_cog:
                await accessibility_cog.accessibility_settings(interaction)
            return True
        
        elif shortcut_id == "close":
            # Just delete the message
            await interaction.message.delete()
            return True
        
        # Handle the standard shortcuts
        if shortcut_id == 'text_size':
            await self._cycle_text_size(interaction, user_id)
        elif shortcut_id == 'color_mode':
            await self._cycle_color_mode(interaction, user_id)
        elif shortcut_id == 'animations':
            await self._toggle_animations(interaction, user_id)
        elif shortcut_id == 'simplified_ui':
            await self._toggle_setting(interaction, user_id, 'simplified_ui')
        elif shortcut_id == 'high_contrast':
            await self._toggle_high_contrast(interaction, user_id)
        elif shortcut_id == 'extended_timeout':
            await self._toggle_setting(interaction, user_id, 'extended_interaction_timeouts')
        elif shortcut_id == 'screen_reader':
            await self._toggle_setting(interaction, user_id, 'screen_reader_support')
        elif shortcut_id == 'button_spacing':
            await self._toggle_setting(interaction, user_id, 'extra_button_spacing')
        
        return True
    
    async def _cycle_text_size(self, interaction: discord.Interaction, user_id: str):
        """Cycle through text size options."""
        settings = self.accessibility_manager.get_settings(user_id)
        
        # Determine next text size
        if settings.text_size == TextSize.SMALL:
            new_value = TextSize.MEDIUM.value
            display_name = "Medium"
        elif settings.text_size == TextSize.MEDIUM:
            new_value = TextSize.LARGE.value
            display_name = "Large"
        elif settings.text_size == TextSize.LARGE:
            new_value = TextSize.EXTRA_LARGE.value
            display_name = "Extra Large"
        else:
            new_value = TextSize.SMALL.value
            display_name = "Small"
        
        # Update setting
        self.accessibility_manager.update_settings(
            user_id,
            {"text_size": new_value}
        )
        
        # Send confirmation
        await interaction.response.send_message(
            f"Text size changed to {display_name}",
            ephemeral=True,
            delete_after=2
        )
    
    async def _cycle_color_mode(self, interaction: discord.Interaction, user_id: str):
        """Cycle through color mode options."""
        settings = self.accessibility_manager.get_settings(user_id)
        
        # Determine next color mode
        if settings.color_mode == ColorMode.NORMAL:
            new_value = ColorMode.HIGH_CONTRAST.value
            display_name = "High Contrast"
        elif settings.color_mode == ColorMode.HIGH_CONTRAST:
            new_value = ColorMode.DEUTERANOPIA.value
            display_name = "Deuteranopia"
        elif settings.color_mode == ColorMode.DEUTERANOPIA:
            new_value = ColorMode.PROTANOPIA.value
            display_name = "Protanopia"
        elif settings.color_mode == ColorMode.PROTANOPIA:
            new_value = ColorMode.TRITANOPIA.value
            display_name = "Tritanopia"
        elif settings.color_mode == ColorMode.TRITANOPIA:
            new_value = ColorMode.MONOCHROME.value
            display_name = "Monochrome"
        else:
            new_value = ColorMode.NORMAL.value
            display_name = "Normal"
        
        # Update setting
        self.accessibility_manager.update_settings(
            user_id,
            {"color_mode": new_value}
        )
        
        # Send confirmation
        await interaction.response.send_message(
            f"Color mode changed to {display_name}",
            ephemeral=True,
            delete_after=2
        )
    
    async def _toggle_animations(self, interaction: discord.Interaction, user_id: str):
        """Toggle animation level between full and none."""
        settings = self.accessibility_manager.get_settings(user_id)
        
        # Toggle animation level
        if settings.animation_level == AnimationLevel.FULL:
            new_value = AnimationLevel.NONE.value
            display_name = "No Animations"
        else:
            new_value = AnimationLevel.FULL.value
            display_name = "Full Animations"
        
        # Update setting
        self.accessibility_manager.update_settings(
            user_id,
            {"animation_level": new_value}
        )
        
        # Send confirmation
        await interaction.response.send_message(
            f"Animation setting changed to {display_name}",
            ephemeral=True,
            delete_after=2
        )
    
    async def _toggle_high_contrast(self, interaction: discord.Interaction, user_id: str):
        """Toggle high contrast mode."""
        settings = self.accessibility_manager.get_settings(user_id)
        
        # Toggle high contrast
        if settings.color_mode == ColorMode.HIGH_CONTRAST:
            new_value = ColorMode.NORMAL.value
            display_name = "Normal"
        else:
            new_value = ColorMode.HIGH_CONTRAST.value
            display_name = "High Contrast"
        
        # Update setting
        self.accessibility_manager.update_settings(
            user_id,
            {"color_mode": new_value}
        )
        
        # Send confirmation
        await interaction.response.send_message(
            f"Color mode changed to {display_name}",
            ephemeral=True,
            delete_after=2
        )
    
    async def _toggle_setting(self, interaction: discord.Interaction, user_id: str, setting_name: str):
        """Toggle a boolean setting."""
        settings = self.accessibility_manager.get_settings(user_id)
        
        # Get current value
        current_value = getattr(settings, setting_name, False)
        
        # Toggle value
        new_value = not current_value
        
        # Create a pretty display name from the setting name
        display_name = setting_name.replace('_', ' ').title()
        
        # Update setting
        self.accessibility_manager.update_settings(
            user_id,
            {setting_name: new_value}
        )
        
        # Send confirmation
        await interaction.response.send_message(
            f"{display_name} {'enabled' if new_value else 'disabled'}",
            ephemeral=True,
            delete_after=2
        )


# Command alias handling
def add_command_aliases(bot):
    """Add command aliases to the bot."""
    
    @bot.command(name="shortcuts", help="Show accessibility shortcuts panel")
    async def shortcuts_panel(ctx):
        """Show the accessibility shortcuts panel."""
        user_id = str(ctx.author.id)
        theme = theme_manager.get_user_theme(user_id)
        
        # Create shortcut view
        view = ShortcutButtonsView(bot, user_id)
        
        # Create embed
        embed = theme.create_embed(
            title="Accessibility Shortcuts",
            description="Click the buttons below for quick access to accessibility settings:",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add descriptions for each shortcut
        embed.add_field(
            name="Text & Color",
            value=(
                "**Aa** - Toggle text size\n"
                "**🎨** - Cycle color modes\n"
                "**👁️** - Toggle high contrast\n"
                "**🔊** - Toggle screen reader support"
            ),
            inline=True
        )
        
        embed.add_field(
            name="UI & Interactions",
            value=(
                "**📱** - Toggle simplified UI\n"
                "**🎬** - Toggle animations\n"
                "**⏱️** - Toggle extended timeouts\n"
                "**↔️** - Toggle button spacing"
            ),
            inline=True
        )
        
        await ctx.send(embed=embed, view=view)
    
    @bot.command(name="help_aliases", help="Show command aliases")
    async def help_aliases(ctx):
        """Show all available command aliases."""
        theme = theme_manager.get_user_theme(str(ctx.author.id))
        embed = theme.create_embed(
            title="Command Aliases",
            description="The following command aliases are available:",
            color_type=ThemeColorType.PRIMARY
        )
        
        for alias, (command, description) in COMMAND_ALIASES.items():
            embed.add_field(
                name=f"`!{alias}`",
                value=f"{description} (alias for `/{command}`)",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    # Add all command aliases
    for alias, (command, _) in COMMAND_ALIASES.items():
        @bot.command(name=alias)
        async def alias_command(ctx, *, args="", _command=command):
            """Handle an aliased command by converting it to a slash command."""
            # Construct the slash command
            full_command = f"/{_command}"
            if args:
                full_command += f" {args}"
            
            # Send a message showing what command was executed
            await ctx.send(
                f"Executing: `{full_command}`",
                delete_after=2
            )
            
            # Find the command in the bot's command tree
            cmd_parts = _command.split()
            cmd_name = cmd_parts[0]
            
            # Find the command
            command_obj = None
            for cmd in bot.tree.walk_commands():
                if cmd.name == cmd_name and isinstance(cmd, app_commands.Command):
                    command_obj = cmd
                    break
            
            if command_obj:
                # Try to invoke the slash command
                try:
                    # Create a mock interaction - this is a limitation because Discord
                    # doesn't let bots trigger slash commands directly
                    # Instead, we'll create a proper slash command context in the future
                    await ctx.send(
                        f"Please use `/{_command}` directly for full functionality. "
                        f"Alias commands have limited capabilities.",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"Error running aliased command: {e}")
                    await ctx.send(
                        f"Error executing command. Please use `/{_command}` directly.",
                        ephemeral=True
                    )
            else:
                await ctx.send(
                    f"Command not found. Please use slash commands directly.",
                    ephemeral=True
                )

def setup_shortcut_handler(bot):
    """Set up the shortcuts handler for the bot."""
    handler = AccessibilityShortcutsHandler(bot)
    
    # Register interaction handler for shortcut buttons
    @bot.event
    async def on_interaction(interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("shortcut:"):
                await handler.handle_shortcut(interaction)
    
    # Add command aliases
    add_command_aliases(bot)
    
    return handler
