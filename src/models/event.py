import discord
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import json
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger('veramon.event')

class EventStatus(Enum):
    """Status of a seasonal event."""
    UPCOMING = 0
    ACTIVE = 1
    ENDED = 2

class EventType(Enum):
    """Types of seasonal events."""
    HOLIDAY = 1       # Holiday-themed events (Christmas, Halloween, etc.)
    SPECIAL = 2       # Special events (Anniversary, etc.)
    COMMUNITY = 3     # Community-driven events
    COMPETITIVE = 4   # Competitive-focused events
    COLLAB = 5        # Collaboration events with other servers or games

class Event:
    """
    Represents a seasonal event in the game.
    
    Attributes:
        id (str): Unique identifier for the event
        name (str): Display name for the event
        description (str): Long description of the event
        event_type (EventType): Type of the event
        start_date (datetime): When the event starts
        end_date (datetime): When the event ends
        banner_url (Optional[str]): URL to event banner image
        icon (str): Emoji or icon representing the event
        theme_color (int): Discord color code for the event theme
        special_encounters (List[Dict]): Special Veramon encounters during event
        special_items (List[Dict]): Special items available during event
        quests (List[str]): List of quest IDs associated with the event
        community_goal (Optional[Dict]): Community-wide goal and reward
        decorations (Optional[Dict]): UI decorations for the event
        rewards_claimed (Dict[str, List[str]]): Map of user IDs to claimed reward IDs
    """
    
    def __init__(self, event_data: Dict[str, Any]):
        self.id = event_data.get('id', '')
        self.name = event_data.get('name', 'Unnamed Event')
        self.description = event_data.get('description', '')
        self.event_type = EventType[event_data.get('event_type', 'SPECIAL')]
        
        # Time-related fields
        self.start_date = datetime.fromisoformat(event_data.get('start_date')) if event_data.get('start_date') else datetime.now()
        self.end_date = datetime.fromisoformat(event_data.get('end_date')) if event_data.get('end_date') else (datetime.now() + timedelta(days=7))
        
        # Visual elements
        self.banner_url = event_data.get('banner_url')
        self.icon = event_data.get('icon', '🎉')
        self.theme_color = event_data.get('theme_color', 0xE74C3C)  # Default: Red
        
        # Content
        self.special_encounters = event_data.get('special_encounters', [])
        self.special_items = event_data.get('special_items', [])
        self.quests = event_data.get('quests', [])
        self.community_goal = event_data.get('community_goal')
        self.decorations = event_data.get('decorations', {})
        
        # Tracking
        self.rewards_claimed = event_data.get('rewards_claimed', {})
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary for storage."""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'event_type': self.event_type.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'banner_url': self.banner_url,
            'icon': self.icon,
            'theme_color': self.theme_color,
            'special_encounters': self.special_encounters,
            'special_items': self.special_items,
            'quests': self.quests,
            'community_goal': self.community_goal,
            'decorations': self.decorations,
            'rewards_claimed': self.rewards_claimed
        }
        return result
        
    def get_status(self, now: Optional[datetime] = None) -> EventStatus:
        """Get the current status of the event."""
        if not now:
            now = datetime.now()
            
        if now < self.start_date:
            return EventStatus.UPCOMING
        elif now > self.end_date:
            return EventStatus.ENDED
        else:
            return EventStatus.ACTIVE
            
    def is_active(self, now: Optional[datetime] = None) -> bool:
        """Check if the event is currently active."""
        return self.get_status(now) == EventStatus.ACTIVE
        
    def time_until_start(self, now: Optional[datetime] = None) -> Optional[timedelta]:
        """Get the time until the event starts."""
        if not now:
            now = datetime.now()
            
        if now < self.start_date:
            return self.start_date - now
        return None
        
    def time_until_end(self, now: Optional[datetime] = None) -> Optional[timedelta]:
        """Get the time until the event ends."""
        if not now:
            now = datetime.now()
            
        if now < self.end_date:
            return self.end_date - now
        return None
        
    def has_claimed_reward(self, user_id: str, reward_id: str) -> bool:
        """Check if a user has claimed a specific reward."""
        return user_id in self.rewards_claimed and reward_id in self.rewards_claimed[user_id]
        
    def claim_reward(self, user_id: str, reward_id: str) -> bool:
        """Mark a reward as claimed by a user."""
        if self.has_claimed_reward(user_id, reward_id):
            return False
            
        if user_id not in self.rewards_claimed:
            self.rewards_claimed[user_id] = []
            
        self.rewards_claimed[user_id].append(reward_id)
        return True
        
    def create_embed(self, user_id: str = None) -> discord.Embed:
        """Create an embed to display the event details."""
        embed = discord.Embed(
            title=f"{self.icon} {self.name}",
            description=self.description,
            color=self.theme_color
        )
        
        # Add status info
        status = self.get_status()
        status_text = status.name.replace('_', ' ').title()
        
        if status == EventStatus.UPCOMING:
            time_until = self.time_until_start()
            days = time_until.days
            hours, remainder = divmod(time_until.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                time_str = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{minutes}m"
                
            embed.add_field(name="Status", value=f"{status_text} - Starts in {time_str}", inline=False)
            
        elif status == EventStatus.ACTIVE:
            time_until = self.time_until_end()
            days = time_until.days
            hours, remainder = divmod(time_until.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                time_str = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{minutes}m"
                
            embed.add_field(name="Status", value=f"{status_text} - Ends in {time_str}", inline=False)
            
        else:  # ENDED
            embed.add_field(name="Status", value=f"{status_text}", inline=False)
            
        # Add special encounters
        if self.special_encounters:
            encounters_text = ""
            for encounter in self.special_encounters[:5]:
                name = encounter.get('name', 'Unknown')
                rarity = encounter.get('rarity', 'Common')
                encounters_text += f"• {name} ({rarity})\n"
                
            if len(self.special_encounters) > 5:
                encounters_text += f"...and {len(self.special_encounters) - 5} more!"
                
            embed.add_field(name="Special Encounters", value=encounters_text, inline=True)
            
        # Add special items
        if self.special_items:
            items_text = ""
            for item in self.special_items[:5]:
                name = item.get('name', 'Unknown')
                description = item.get('description', '')
                items_text += f"• {name}\n"
                
            if len(self.special_items) > 5:
                items_text += f"...and {len(self.special_items) - 5} more!"
                
            embed.add_field(name="Special Items", value=items_text, inline=True)
            
        # Add community goal if present
        if self.community_goal:
            goal_type = self.community_goal.get('type', 'Unknown')
            target = self.community_goal.get('target', 0)
            current = self.community_goal.get('current', 0)
            percentage = int((current / target) * 100) if target > 0 else 0
            
            goal_text = f"Type: {goal_type}\n"
            goal_text += f"Progress: {current}/{target} ({percentage}%)\n"
            
            if 'reward' in self.community_goal:
                goal_text += f"Reward: {self.community_goal['reward']}"
                
            embed.add_field(name="Community Goal", value=goal_text, inline=False)
            
        # Add dates
        start_date_str = self.start_date.strftime("%B %d, %Y")
        end_date_str = self.end_date.strftime("%B %d, %Y")
        embed.set_footer(text=f"Event runs from {start_date_str} to {end_date_str}")
        
        # Add banner if available
        if self.banner_url:
            embed.set_image(url=self.banner_url)
            
        return embed
