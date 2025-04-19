import discord
from discord import ui
from typing import Dict, List, Optional, Any, Callable, Awaitable
import re
import json

class ProfileCustomizationModal(ui.Modal, title="Customize Your Profile"):
    """Modal for customizing user profile with multiple fields."""
    
    title = ui.TextInput(
        label="Title",
        placeholder="Enter your title or leave blank",
        required=False,
        max_length=50
    )
    
    bio = ui.TextInput(
        label="Biography",
        placeholder="Tell others about yourself...",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph
    )
    
    favorite_type = ui.TextInput(
        label="Favorite Type",
        placeholder="Enter your favorite Veramon type",
        required=False,
        max_length=20
    )
    
    showcase_message = ui.TextInput(
        label="Showcase Message",
        placeholder="Message to display with your showcase Veramon",
        required=False,
        max_length=100
    )
    
    color_hex = ui.TextInput(
        label="Profile Color (hex)",
        placeholder="e.g. #FF5500 (leave blank for default)",
        required=False,
        max_length=7,
        min_length=0
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the submitted form data."""
        # Validate color hex if provided
        color_hex = self.color_hex.value.strip()
        if color_hex and not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_hex):
            await interaction.response.send_message(
                "Invalid color hex code. Please use format #RRGGBB or #RGB.",
                ephemeral=True
            )
            return
            
        # Create profile data dictionary
        profile_data = {
            "title": self.title.value.strip(),
            "bio": self.bio.value.strip(),
            "favorite_type": self.favorite_type.value.strip(),
            "showcase_message": self.showcase_message.value.strip(),
            "color": color_hex if color_hex else None
        }
        
        # Pass to callback
        if hasattr(self, 'callback') and callable(self.callback):
            await self.callback(interaction, profile_data)
        else:
            await interaction.response.send_message(
                "Profile information saved!",
                ephemeral=True
            )
            
    def set_callback(self, callback: Callable[[discord.Interaction, Dict[str, Any]], Awaitable[None]]):
        """Set a callback function to handle the submitted data."""
        self.callback = callback

class TeamBuilderModal(ui.Modal, title="Build Your Team"):
    """Modal for building a Veramon team with name and description."""
    
    team_name = ui.TextInput(
        label="Team Name",
        placeholder="Enter a name for your team",
        required=True,
        max_length=50
    )
    
    team_description = ui.TextInput(
        label="Team Description",
        placeholder="Describe your team strategy...",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )
    
    team_type = ui.TextInput(
        label="Team Type",
        placeholder="e.g. Balanced, Offensive, Defensive...",
        required=False,
        max_length=30
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the submitted form data."""
        # Create team data dictionary
        team_data = {
            "name": self.team_name.value.strip(),
            "description": self.team_description.value.strip(),
            "type": self.team_type.value.strip()
        }
        
        # Pass to callback
        if hasattr(self, 'callback') and callable(self.callback):
            await self.callback(interaction, team_data)
        else:
            await interaction.response.send_message(
                "Team information saved!",
                ephemeral=True
            )
            
    def set_callback(self, callback: Callable[[discord.Interaction, Dict[str, Any]], Awaitable[None]]):
        """Set a callback function to handle the submitted data."""
        self.callback = callback

class VeramonNicknameModal(ui.Modal, title="Name Your Veramon"):
    """Modal for setting a Veramon's nickname."""
    
    def __init__(self, veramon_name: str, capture_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capture_id = capture_id
        self.veramon_name = veramon_name
        self.title = f"Name Your {veramon_name}"
        
    nickname = ui.TextInput(
        label="Nickname",
        placeholder="Enter a nickname or leave blank to reset",
        required=False,
        max_length=30
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the submitted nickname."""
        nickname = self.nickname.value.strip()
        
        # Pass to callback
        if hasattr(self, 'callback') and callable(self.callback):
            await self.callback(interaction, self.capture_id, nickname)
        else:
            await interaction.response.send_message(
                f"Nickname {'set' if nickname else 'reset'} for your {self.veramon_name}!",
                ephemeral=True
            )
            
    def set_callback(self, callback: Callable[[discord.Interaction, int, str], Awaitable[None]]):
        """Set a callback function to handle the submitted data."""
        self.callback = callback

class TournamentCreationModal(ui.Modal, title="Create Tournament"):
    """Modal for creating a new tournament with detailed settings."""
    
    name = ui.TextInput(
        label="Tournament Name",
        placeholder="Enter a name for your tournament",
        required=True,
        max_length=100
    )
    
    description = ui.TextInput(
        label="Description",
        placeholder="Describe the tournament rules and theme...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    max_participants = ui.TextInput(
        label="Max Participants",
        placeholder="Enter a number (4-64)",
        required=True,
        max_length=2,
        default="16"
    )
    
    level_cap = ui.TextInput(
        label="Level Cap (optional)",
        placeholder="Maximum Veramon level allowed (leave blank for no limit)",
        required=False,
        max_length=3
    )
    
    prize_pool = ui.TextInput(
        label="Prize Pool",
        placeholder="Describe the prizes for winners",
        required=False,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the submitted tournament data."""
        # Validate max participants
        try:
            max_participants = int(self.max_participants.value)
            if max_participants < 4 or max_participants > 64:
                await interaction.response.send_message(
                    "Max participants must be between 4 and 64.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "Max participants must be a number.",
                ephemeral=True
            )
            return
            
        # Validate level cap if provided
        level_cap = None
        if self.level_cap.value.strip():
            try:
                level_cap = int(self.level_cap.value)
                if level_cap < 1 or level_cap > 100:
                    await interaction.response.send_message(
                        "Level cap must be between 1 and 100.",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "Level cap must be a number.",
                    ephemeral=True
                )
                return
                
        # Create tournament data dictionary
        tournament_data = {
            "name": self.name.value.strip(),
            "description": self.description.value.strip(),
            "max_participants": max_participants,
            "level_cap": level_cap,
            "prize_pool": self.prize_pool.value.strip()
        }
        
        # Pass to callback
        if hasattr(self, 'callback') and callable(self.callback):
            await self.callback(interaction, tournament_data)
        else:
            await interaction.response.send_message(
                f"Tournament '{self.name.value}' created!",
                ephemeral=True
            )
            
    def set_callback(self, callback: Callable[[discord.Interaction, Dict[str, Any]], Awaitable[None]]):
        """Set a callback function to handle the submitted data."""
        self.callback = callback

class BatchRenameModal(ui.Modal, title="Batch Rename Veramon"):
    """Modal for batch renaming Veramon based on a pattern."""
    
    pattern = ui.TextInput(
        label="Naming Pattern",
        placeholder="Use {name}, {type}, {level}, {id}, {rarity}, {index}",
        required=True,
        max_length=100
    )
    
    filter_type = ui.TextInput(
        label="Filter by Type (optional)",
        placeholder="Type to filter by, e.g. 'Fire'",
        required=False,
        max_length=20
    )
    
    filter_level = ui.TextInput(
        label="Filter by Level (optional)",
        placeholder="e.g. '10+' for level 10 and above, '1-10' for range",
        required=False,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the batch rename request."""
        pattern = self.pattern.value.strip()
        filter_type = self.filter_type.value.strip()
        filter_level = self.filter_level.value.strip()
        
        # Validate pattern
        if not any(tag in pattern for tag in ["{name}", "{type}", "{level}", "{id}", "{rarity}", "{index}"]):
            await interaction.response.send_message(
                "Pattern must include at least one tag: {name}, {type}, {level}, {id}, {rarity}, or {index}",
                ephemeral=True
            )
            return
            
        # Validate level filter if provided
        level_min = None
        level_max = None
        if filter_level:
            if "+" in filter_level:
                try:
                    level_min = int(filter_level.replace("+", ""))
                    level_max = 100  # No upper limit
                except ValueError:
                    await interaction.response.send_message(
                        "Invalid level filter format. Use '10+' for level 10 and above.",
                        ephemeral=True
                    )
                    return
            elif "-" in filter_level:
                try:
                    parts = filter_level.split("-")
                    level_min = int(parts[0])
                    level_max = int(parts[1])
                except (ValueError, IndexError):
                    await interaction.response.send_message(
                        "Invalid level filter format. Use '1-10' for levels 1 to 10.",
                        ephemeral=True
                    )
                    return
            else:
                try:
                    level_exact = int(filter_level)
                    level_min = level_max = level_exact
                except ValueError:
                    await interaction.response.send_message(
                        "Invalid level filter. Use a number, range (e.g. '1-10'), or minimum (e.g. '10+').",
                        ephemeral=True
                    )
                    return
                    
        # Create filter data dictionary
        filter_data = {
            "pattern": pattern,
            "type": filter_type if filter_type else None,
            "level_min": level_min,
            "level_max": level_max
        }
        
        # Pass to callback
        if hasattr(self, 'callback') and callable(self.callback):
            await self.callback(interaction, filter_data)
        else:
            await interaction.response.send_message(
                "Batch rename pattern saved!",
                ephemeral=True
            )
            
    def set_callback(self, callback: Callable[[discord.Interaction, Dict[str, Any]], Awaitable[None]]):
        """Set a callback function to handle the submitted data."""
        self.callback = callback
