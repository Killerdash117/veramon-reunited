"""
Accessibility Settings UI for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides UI components for managing accessibility settings.
"""

import discord
from discord import ui
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable

from src.utils.ui.interactive_ui import InteractiveView, NavigableView, NavigationType
from src.utils.ui.ui_registry import get_ui_registry
from src.utils.ui_theme import theme_manager, ThemeColorType
from src.utils.ui.accessibility import (
    get_accessibility_manager, 
    AccessibilitySettings,
    TextSize, 
    UpdateFrequency, 
    ColorMode
)

# Set up logging
logger = logging.getLogger('veramon.accessibility_ui')

class AccessibilitySettingsView(NavigableView):
    """
    Settings interface for accessibility options.
    
    Features:
    - Text size adjustment
    - Update frequency control
    - Color mode selection
    - Screen reader support
    - UI simplification options
    """
    
    def __init__(
        self,
        user_id: str,
        **kwargs
    ):
        super().__init__(
            user_id=user_id,
            navigation_type=NavigationType.TABS,
            **kwargs
        )
        
        # Set up tabs
        self.setup_tabs([
            "General",
            "Visual",
            "Controls",
            "Advanced"
        ])
        
        # Get current settings
        self.accessibility_manager = get_accessibility_manager()
        self.settings = self.accessibility_manager.get_settings(user_id)
        
        # Theme settings
        self.theme = theme_manager.get_user_theme(user_id)
        
        # Set up UI components for each tab
        self._setup_general_tab()
        self._setup_visual_tab()
        self._setup_controls_tab()
        self._setup_advanced_tab()
        
        # Add reset button
        self.add_item(ui.Button(
            style=discord.ButtonStyle.danger,
            label="Reset All Settings",
            row=4
        ).callback(self._on_reset_settings))
    
    def _setup_general_tab(self):
        """Set up the general accessibility settings tab."""
        # Text size selection
        text_size_select = ui.Select(
            placeholder="Select Text Size",
            options=[
                discord.SelectOption(
                    label="Small",
                    value=TextSize.SMALL.value,
                    description="Default text size",
                    default=self.settings.text_size == TextSize.SMALL
                ),
                discord.SelectOption(
                    label="Medium",
                    value=TextSize.MEDIUM.value,
                    description="Slightly larger text",
                    default=self.settings.text_size == TextSize.MEDIUM
                ),
                discord.SelectOption(
                    label="Large",
                    value=TextSize.LARGE.value,
                    description="Bold text for better readability",
                    default=self.settings.text_size == TextSize.LARGE
                ),
                discord.SelectOption(
                    label="Extra Large",
                    value=TextSize.EXTRA_LARGE.value,
                    description="Very large text for maximum visibility",
                    default=self.settings.text_size == TextSize.EXTRA_LARGE
                )
            ],
            row=1
        )
        text_size_select.callback = self._on_text_size_changed
        self.add_item(text_size_select)
        
        # Screen reader toggle
        screen_reader_button = ui.Button(
            style=discord.ButtonStyle.success if self.settings.screen_reader_support else discord.ButtonStyle.secondary,
            label="Screen Reader Support: " + ("ON" if self.settings.screen_reader_support else "OFF"),
            row=2
        )
        screen_reader_button.callback = self._on_screen_reader_toggled
        self.add_item(screen_reader_button)
        
        # Simplified UI toggle
        simplified_ui_button = ui.Button(
            style=discord.ButtonStyle.success if self.settings.simplified_ui else discord.ButtonStyle.secondary,
            label="Simplified UI: " + ("ON" if self.settings.simplified_ui else "OFF"),
            row=2
        )
        simplified_ui_button.callback = self._on_simplified_ui_toggled
        self.add_item(simplified_ui_button)
    
    def _setup_visual_tab(self):
        """Set up the visual accessibility settings tab."""
        # Update frequency selection
        update_frequency_select = ui.Select(
            placeholder="Select Update Frequency",
            options=[
                discord.SelectOption(
                    label="Standard Updates",
                    value=UpdateFrequency.STANDARD.value,
                    description="Show all updates",
                    default=self.settings.update_frequency == UpdateFrequency.STANDARD
                ),
                discord.SelectOption(
                    label="Reduced Updates",
                    value=UpdateFrequency.REDUCED.value,
                    description="Show only essential updates",
                    default=self.settings.update_frequency == UpdateFrequency.REDUCED
                ),
                discord.SelectOption(
                    label="Minimal Updates",
                    value=UpdateFrequency.MINIMAL.value,
                    description="Disable most updates",
                    default=self.settings.update_frequency == UpdateFrequency.MINIMAL
                )
            ],
            row=1
        )
        update_frequency_select.callback = self._on_update_frequency_changed
        self.add_item(update_frequency_select)
        
        # Color mode selection
        color_mode_select = ui.Select(
            placeholder="Select Color Mode",
            options=[
                discord.SelectOption(
                    label="Normal Colors",
                    value=ColorMode.NORMAL.value,
                    description="Standard theme colors",
                    default=self.settings.color_mode == ColorMode.NORMAL
                ),
                discord.SelectOption(
                    label="High Contrast",
                    value=ColorMode.HIGH_CONTRAST.value,
                    description="Enhanced visibility with high contrast",
                    default=self.settings.color_mode == ColorMode.HIGH_CONTRAST
                ),
                discord.SelectOption(
                    label="Deuteranopia",
                    value=ColorMode.DEUTERANOPIA.value,
                    description="Optimized for green color blindness",
                    default=self.settings.color_mode == ColorMode.DEUTERANOPIA
                ),
                discord.SelectOption(
                    label="Protanopia",
                    value=ColorMode.PROTANOPIA.value,
                    description="Optimized for red color blindness",
                    default=self.settings.color_mode == ColorMode.PROTANOPIA
                ),
                discord.SelectOption(
                    label="Tritanopia",
                    value=ColorMode.TRITANOPIA.value,
                    description="Optimized for blue color blindness",
                    default=self.settings.color_mode == ColorMode.TRITANOPIA
                ),
                discord.SelectOption(
                    label="Monochrome",
                    value=ColorMode.MONOCHROME.value,
                    description="Grayscale mode",
                    default=self.settings.color_mode == ColorMode.MONOCHROME
                )
            ],
            row=2
        )
        color_mode_select.callback = self._on_color_mode_changed
        self.add_item(color_mode_select)
        
        # Color mode preview button
        preview_button = ui.Button(
            style=discord.ButtonStyle.primary,
            label="Preview Color Mode",
            row=3
        )
        preview_button.callback = self._on_preview_color_mode
        self.add_item(preview_button)
    
    def _setup_controls_tab(self):
        """Set up the controls accessibility settings tab."""
        # Extra button spacing toggle
        button_spacing_button = ui.Button(
            style=discord.ButtonStyle.success if self.settings.extra_button_spacing else discord.ButtonStyle.secondary,
            label="Extra Button Spacing: " + ("ON" if self.settings.extra_button_spacing else "OFF"),
            row=1
        )
        button_spacing_button.callback = self._on_button_spacing_toggled
        self.add_item(button_spacing_button)
        
        # Extended timeouts toggle
        extended_timeouts_button = ui.Button(
            style=discord.ButtonStyle.success if self.settings.extended_interaction_timeouts else discord.ButtonStyle.secondary,
            label="Extended Timeouts: " + ("ON" if self.settings.extended_interaction_timeouts else "OFF"),
            row=1
        )
        extended_timeouts_button.callback = self._on_extended_timeouts_toggled
        self.add_item(extended_timeouts_button)
        
        # Button scale demo
        if self.settings.extra_button_spacing:
            # Show sample buttons with extra spacing
            for i in range(3):
                demo_button = ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label=f"Demo {i+1}",
                    disabled=True,
                    row=2
                )
                self.add_item(demo_button)
        else:
            # Show sample buttons with normal spacing
            for i in range(5):
                demo_button = ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label=f"Demo {i+1}",
                    disabled=True,
                    row=2
                )
                self.add_item(demo_button)
    
    def _setup_advanced_tab(self):
        """Set up the advanced accessibility settings tab."""
        # Alt text toggle
        alt_text_button = ui.Button(
            style=discord.ButtonStyle.success if self.settings.always_include_alt_text else discord.ButtonStyle.secondary,
            label="Always Include Alt Text: " + ("ON" if self.settings.always_include_alt_text else "OFF"),
            row=1
        )
        alt_text_button.callback = self._on_alt_text_toggled
        self.add_item(alt_text_button)
        
        # Add theme recommendation button
        theme_button = ui.Button(
            style=discord.ButtonStyle.primary,
            label="Recommend Accessible Theme",
            row=2
        )
        theme_button.callback = self._on_recommend_theme
        self.add_item(theme_button)
    
    async def _on_text_size_changed(self, interaction: discord.Interaction):
        """Handle text size change."""
        text_size_value = interaction.data["values"][0]
        try:
            self.settings.text_size = TextSize(text_size_value)
            self.accessibility_manager.update_settings(
                self.user_id,
                {"text_size": text_size_value}
            )
            
            # Update the view with new text size
            await self.update_view(interaction)
            
            # Send a confirmation
            await interaction.response.send_message(
                f"Text size updated to {text_size_value}.",
                ephemeral=True,
                delete_after=3
            )
        except Exception as e:
            logger.error(f"Error updating text size: {e}")
            await interaction.response.send_message(
                "There was an error updating the text size. Please try again.",
                ephemeral=True
            )
    
    async def _on_update_frequency_changed(self, interaction: discord.Interaction):
        """Handle update frequency change."""
        update_frequency_value = interaction.data["values"][0]
        try:
            self.settings.update_frequency = UpdateFrequency(update_frequency_value)
            self.accessibility_manager.update_settings(
                self.user_id,
                {"update_frequency": update_frequency_value}
            )
            
            # Update the view
            await self.update_view(interaction)
            
            # Send a confirmation
            await interaction.response.send_message(
                f"Update frequency updated to {update_frequency_value}.",
                ephemeral=True,
                delete_after=3
            )
        except Exception as e:
            logger.error(f"Error updating update frequency: {e}")
            await interaction.response.send_message(
                "There was an error updating the update frequency. Please try again.",
                ephemeral=True
            )
    
    async def _on_color_mode_changed(self, interaction: discord.Interaction):
        """Handle color mode change."""
        color_mode_value = interaction.data["values"][0]
        try:
            self.settings.color_mode = ColorMode(color_mode_value)
            self.accessibility_manager.update_settings(
                self.user_id,
                {"color_mode": color_mode_value}
            )
            
            # Update the view
            await self.update_view(interaction)
            
            # Recommend the high contrast theme if high contrast color mode is selected
            if color_mode_value == ColorMode.HIGH_CONTRAST.value:
                await interaction.response.send_message(
                    "High Contrast color mode selected. Would you also like to use the High Contrast theme for maximum visibility?",
                    ephemeral=True,
                    view=ConfirmThemeChangeView(self.user_id, "high_contrast")
                )
            else:
                # Send a confirmation
                await interaction.response.send_message(
                    f"Color mode updated to {color_mode_value}.",
                    ephemeral=True,
                    delete_after=3
                )
        except Exception as e:
            logger.error(f"Error updating color mode: {e}")
            await interaction.response.send_message(
                "There was an error updating the color mode. Please try again.",
                ephemeral=True
            )
    
    async def _on_screen_reader_toggled(self, interaction: discord.Interaction):
        """Handle screen reader support toggle."""
        new_value = not self.settings.screen_reader_support
        try:
            self.settings.screen_reader_support = new_value
            self.accessibility_manager.update_settings(
                self.user_id,
                {"screen_reader_support": new_value}
            )
            
            # Update the button
            for child in self.children:
                if isinstance(child, ui.Button) and child.label and "Screen Reader Support" in child.label:
                    child.label = "Screen Reader Support: " + ("ON" if new_value else "OFF")
                    child.style = discord.ButtonStyle.success if new_value else discord.ButtonStyle.secondary
            
            # Update the view
            await self.update_view(interaction)
        except Exception as e:
            logger.error(f"Error toggling screen reader support: {e}")
            await interaction.response.send_message(
                "There was an error updating the screen reader setting. Please try again.",
                ephemeral=True
            )
    
    async def _on_simplified_ui_toggled(self, interaction: discord.Interaction):
        """Handle simplified UI toggle."""
        new_value = not self.settings.simplified_ui
        try:
            self.settings.simplified_ui = new_value
            self.accessibility_manager.update_settings(
                self.user_id,
                {"simplified_ui": new_value}
            )
            
            # Update the button
            for child in self.children:
                if isinstance(child, ui.Button) and child.label and "Simplified UI" in child.label:
                    child.label = "Simplified UI: " + ("ON" if new_value else "OFF")
                    child.style = discord.ButtonStyle.success if new_value else discord.ButtonStyle.secondary
            
            # Update the view
            await self.update_view(interaction)
        except Exception as e:
            logger.error(f"Error toggling simplified UI: {e}")
            await interaction.response.send_message(
                "There was an error updating the simplified UI setting. Please try again.",
                ephemeral=True
            )
    
    async def _on_button_spacing_toggled(self, interaction: discord.Interaction):
        """Handle button spacing toggle."""
        new_value = not self.settings.extra_button_spacing
        try:
            self.settings.extra_button_spacing = new_value
            self.accessibility_manager.update_settings(
                self.user_id,
                {"extra_button_spacing": new_value}
            )
            
            # Update the button
            for child in self.children:
                if isinstance(child, ui.Button) and child.label and "Extra Button Spacing" in child.label:
                    child.label = "Extra Button Spacing: " + ("ON" if new_value else "OFF")
                    child.style = discord.ButtonStyle.success if new_value else discord.ButtonStyle.secondary
            
            # We need to reload all components for this tab
            self.clear_items()
            
            # Set up UI components for each tab again
            self._setup_general_tab()
            self._setup_visual_tab()
            self._setup_controls_tab()
            self._setup_advanced_tab()
            
            # Update the view
            await self.update_view(interaction)
        except Exception as e:
            logger.error(f"Error toggling button spacing: {e}")
            await interaction.response.send_message(
                "There was an error updating the button spacing setting. Please try again.",
                ephemeral=True
            )
    
    async def _on_extended_timeouts_toggled(self, interaction: discord.Interaction):
        """Handle extended timeouts toggle."""
        new_value = not self.settings.extended_interaction_timeouts
        try:
            self.settings.extended_interaction_timeouts = new_value
            self.accessibility_manager.update_settings(
                self.user_id,
                {"extended_interaction_timeouts": new_value}
            )
            
            # Update the button
            for child in self.children:
                if isinstance(child, ui.Button) and child.label and "Extended Timeouts" in child.label:
                    child.label = "Extended Timeouts: " + ("ON" if new_value else "OFF")
                    child.style = discord.ButtonStyle.success if new_value else discord.ButtonStyle.secondary
            
            # Update the view
            await self.update_view(interaction)
        except Exception as e:
            logger.error(f"Error toggling extended timeouts: {e}")
            await interaction.response.send_message(
                "There was an error updating the extended timeouts setting. Please try again.",
                ephemeral=True
            )
    
    async def _on_alt_text_toggled(self, interaction: discord.Interaction):
        """Handle alt text toggle."""
        new_value = not self.settings.always_include_alt_text
        try:
            self.settings.always_include_alt_text = new_value
            self.accessibility_manager.update_settings(
                self.user_id,
                {"always_include_alt_text": new_value}
            )
            
            # Update the button
            for child in self.children:
                if isinstance(child, ui.Button) and child.label and "Always Include Alt Text" in child.label:
                    child.label = "Always Include Alt Text: " + ("ON" if new_value else "OFF")
                    child.style = discord.ButtonStyle.success if new_value else discord.ButtonStyle.secondary
            
            # Update the view
            await self.update_view(interaction)
        except Exception as e:
            logger.error(f"Error toggling alt text: {e}")
            await interaction.response.send_message(
                "There was an error updating the alt text setting. Please try again.",
                ephemeral=True
            )
    
    async def _on_preview_color_mode(self, interaction: discord.Interaction):
        """Show a preview of the current color mode."""
        color_mode = self.settings.color_mode
        
        # Create a preview embed
        embed = self.theme.create_embed(
            title=f"Color Mode Preview: {color_mode.value}",
            description="This is how UI elements will appear with your selected color mode.",
            color_type=ThemeColorType.PRIMARY
        )
        
        # Add sample fields
        embed.add_field(
            name="Normal Text",
            value="This is regular text in an embed field.",
            inline=True
        )
        
        embed.add_field(
            name="Colored Elements",
            value="🟥 Red\n🟩 Green\n🟦 Blue\n⬜ White\n⬛ Black",
            inline=True
        )
        
        # Create preview view with sample buttons
        preview_view = discord.ui.View(timeout=30)
        
        # Add sample buttons with different styles
        preview_view.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Primary Button",
            disabled=True
        ))
        
        preview_view.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Secondary Button",
            disabled=True
        ))
        
        preview_view.add_item(ui.Button(
            style=discord.ButtonStyle.success,
            label="Success Button",
            disabled=True
        ))
        
        preview_view.add_item(ui.Button(
            style=discord.ButtonStyle.danger,
            label="Danger Button",
            disabled=True
        ))
        
        # Send the preview
        await interaction.response.send_message(
            content="**Color Mode Preview**\nThis shows how UI elements will appear with your selected color settings. This message will disappear in 20 seconds.",
            embed=embed,
            view=preview_view,
            ephemeral=True,
            delete_after=20
        )
    
    async def _on_recommend_theme(self, interaction: discord.Interaction):
        """Recommend an appropriate theme based on accessibility settings."""
        # Determine the best theme based on current settings
        recommended_theme = "default"
        
        if self.settings.color_mode == ColorMode.HIGH_CONTRAST:
            recommended_theme = "high_contrast"
        elif self.settings.color_mode == ColorMode.MONOCHROME:
            recommended_theme = "retro"  # Retro has good contrast
        
        # Send recommendation
        await interaction.response.send_message(
            f"Based on your accessibility settings, we recommend the '{recommended_theme}' theme. Would you like to apply this theme?",
            view=ConfirmThemeChangeView(self.user_id, recommended_theme),
            ephemeral=True
        )
    
    async def _on_reset_settings(self, interaction: discord.Interaction):
        """Reset all accessibility settings to defaults."""
        # Confirm reset
        confirm_view = discord.ui.View(timeout=60)
        
        confirm_button = ui.Button(
            style=discord.ButtonStyle.danger,
            label="Yes, Reset All Settings",
            row=0
        )
        
        cancel_button = ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Cancel",
            row=0
        )
        
        async def confirm_callback(confirm_interaction):
            # Reset settings
            self.settings = self.accessibility_manager.reset_settings(self.user_id)
            
            # Rebuild the UI
            self.clear_items()
            
            # Set up tabs
            self.setup_tabs([
                "General",
                "Visual",
                "Controls",
                "Advanced"
            ])
            
            # Set up UI components for each tab
            self._setup_general_tab()
            self._setup_visual_tab()
            self._setup_controls_tab()
            self._setup_advanced_tab()
            
            # Add reset button
            self.add_item(ui.Button(
                style=discord.ButtonStyle.danger,
                label="Reset All Settings",
                row=4
            ).callback(self._on_reset_settings))
            
            # Update the view
            await self.update_view(interaction)
            
            # Close the confirmation dialog
            await confirm_interaction.response.edit_message(
                content="All accessibility settings have been reset to default values.",
                view=None
            )
        
        async def cancel_callback(cancel_interaction):
            # Just close the confirmation dialog
            await cancel_interaction.response.edit_message(
                content="Reset cancelled. No changes were made.",
                view=None
            )
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)
        
        await interaction.response.send_message(
            "Are you sure you want to reset all accessibility settings to their default values?",
            view=confirm_view,
            ephemeral=True
        )
    
    async def update_view(self, interaction: discord.Interaction):
        """Update the view when tab changes or settings are updated."""
        # Get current tab
        current_tab = self.get_current_tab()
        
        # Create an embed based on the current tab and settings
        if self.settings.simplified_ui:
            # Create a simplified embed with less formatting
            embed = discord.Embed(
                title=f"Accessibility Settings - {current_tab}",
                description="Adjust settings to customize your experience.",
                color=self.theme.get_color(ThemeColorType.PRIMARY).value
            )
        else:
            # Create a normal themed embed
            embed = self.theme.create_embed(
                title=f"Accessibility Settings - {current_tab}",
                description="Adjust settings to customize your experience.",
                color_type=ThemeColorType.PRIMARY
            )
        
        # Add field with current settings summary
        embed.add_field(
            name="Current Settings",
            value=(
                f"Text Size: {self.settings.text_size.value}\n"
                f"Update Frequency: {self.settings.update_frequency.value}\n"
                f"Color Mode: {self.settings.color_mode.value}"
            ),
            inline=False
        )
        
        # Add tab-specific instructions
        if current_tab == "General":
            embed.add_field(
                name="General Settings",
                value="Adjust text size and basic accessibility features.",
                inline=False
            )
        elif current_tab == "Visual":
            embed.add_field(
                name="Visual Settings",
                value="Customize update frequency and color modes.",
                inline=False
            )
        elif current_tab == "Controls":
            embed.add_field(
                name="Control Settings",
                value="Adjust button spacing and interaction timeouts.",
                inline=False
            )
        elif current_tab == "Advanced":
            embed.add_field(
                name="Advanced Settings",
                value="Configure additional accessibility features.",
                inline=False
            )
        
        # Update the message
        await interaction.response.edit_message(embed=embed, view=self)
        
class ConfirmThemeChangeView(InteractiveView):
    """View for confirming theme changes based on accessibility settings."""
    
    def __init__(self, user_id: str, theme_id: str, **kwargs):
        super().__init__(user_id=user_id, timeout=60.0, **kwargs)
        self.theme_id = theme_id
        
        # Add confirmation buttons
        self.add_item(ui.Button(
            style=discord.ButtonStyle.success,
            label="Apply Theme",
            row=0
        ).callback(self._on_confirm))
        
        self.add_item(ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Cancel",
            row=0
        ).callback(self._on_cancel))
        
        # Add preview button
        self.add_item(ui.Button(
            style=discord.ButtonStyle.primary,
            label="Preview Theme",
            row=1
        ).callback(self._on_preview))
    
    async def _on_confirm(self, interaction: discord.Interaction):
        """Apply the theme."""
        success = theme_manager.set_user_theme(self.user_id, self.theme_id)
        
        if success:
            # Get the new theme
            theme = theme_manager.get_theme(self.theme_id)
            
            # Create confirmation embed
            embed = theme.create_embed(
                title="Theme Applied",
                description=f"Your theme has been updated to **{theme.name}**.",
                color_type=ThemeColorType.SUCCESS
            )
            
            # Update the message
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=None
            )
        else:
            await interaction.response.edit_message(
                content="Failed to update theme. Please try again.",
                view=None
            )
    
    async def _on_cancel(self, interaction: discord.Interaction):
        """Cancel the theme change."""
        await interaction.response.edit_message(
            content="Theme change cancelled.",
            view=None
        )
    
    async def _on_preview(self, interaction: discord.Interaction):
        """Preview the theme."""
        theme = theme_manager.get_theme(self.theme_id)
        
        # Create preview embed
        embed = theme.create_embed(
            title=f"Theme Preview: {theme.name}",
            description=theme.description,
            color_type=ThemeColorType.INFO
        )
        
        # Add sample content
        embed.add_field(
            name="This is a field title",
            value="This is the field content showing how text appears",
            inline=True
        )
        
        embed.add_field(
            name="Another field",
            value="More sample text to demonstrate styling",
            inline=True
        )
        
        embed.add_field(
            name="Color Samples",
            value="Different colors demonstrate how the theme looks",
            inline=False
        )
        
        # Send preview
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
            delete_after=15
        )
