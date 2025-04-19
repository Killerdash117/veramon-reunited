import discord
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import json
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger('veramon.quest')

class QuestType(Enum):
    """Types of quests available in the game."""
    DAILY = 1
    WEEKLY = 2
    STORY = 3
    ACHIEVEMENT = 4
    EVENT = 5

class QuestStatus(Enum):
    """Status of a quest for a user."""
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CLAIMED = 3
    FAILED = 4
    EXPIRED = 5

class QuestRequirementType(Enum):
    """Types of requirements that can be used for quests."""
    CATCH = 1         # Catch X Veramon (can be specific type/species)
    BATTLE_WIN = 2    # Win X battles (can be specific type)
    BATTLE_COMPLETE = 3  # Complete X battles (win or lose)
    TRADE = 4         # Complete X trades
    EXPLORE = 5       # Explore X times (can be specific biome)
    EVOLVE = 6        # Evolve X Veramon
    LEVEL_UP = 7      # Level up X Veramon
    USE_ITEM = 8      # Use X items (can be specific item)
    COLLECT = 9       # Collect X tokens
    INTERACT = 10     # Interact with X players
    DEFEAT_TRAINER = 11  # Defeat specific trainer
    CATCH_SPECIFIC = 12  # Catch specific Veramon

class QuestRewardType(Enum):
    """Types of rewards that can be given for quests."""
    TOKENS = 1
    EXPERIENCE = 2
    ITEMS = 3
    VERAMON = 4
    TITLE = 5
    BADGE = 6
    UI_THEME = 7
    PROFILE_BACKGROUND = 8

class Quest:
    """
    Represents a quest in the game.
    
    Attributes:
        id (str): Unique identifier for the quest
        title (str): Display title for the quest
        description (str): Long description of the quest
        quest_type (QuestType): Type of the quest
        requirements (List[Dict]): List of requirement dictionaries
        rewards (List[Dict]): List of reward dictionaries
        prerequisite_quests (List[str]): List of quest IDs that must be completed first
        expiry (Optional[datetime]): When the quest expires (None for permanent quests)
        start_date (Optional[datetime]): When the quest becomes available
        end_date (Optional[datetime]): When the quest is no longer available
        cooldown (Optional[timedelta]): Cooldown period before the quest can be repeated
        repeatable (bool): Whether the quest can be repeated
        max_completions (Optional[int]): Maximum number of times the quest can be completed
        is_hidden (bool): Whether the quest is hidden until prerequisites are met
        narrative (Optional[str]): Story text to display when starting/completing the quest
        icon (Optional[str]): Emoji or URL to use as the quest icon
        storyline_id (str): ID of the storyline this quest belongs to
        sequence (int): Sequence number of this quest in the storyline
    """
    
    def __init__(self, quest_data: Dict[str, Any]):
        self.id = quest_data.get('id', '')
        self.title = quest_data.get('title', 'Unnamed Quest')
        self.description = quest_data.get('description', '')
        self.quest_type = QuestType[quest_data.get('quest_type', 'DAILY')]
        self.requirements = quest_data.get('requirements', [])
        self.rewards = quest_data.get('rewards', [])
        self.prerequisite_quests = quest_data.get('prerequisite_quests', [])
        
        # Optional properties
        self.storyline_id = quest_data.get('storyline_id', '')
        self.sequence = quest_data.get('sequence', 0)
        
        # Time-related fields
        self.expiry = datetime.fromisoformat(quest_data.get('expiry')) if quest_data.get('expiry') else None
        self.start_date = datetime.fromisoformat(quest_data.get('start_date')) if quest_data.get('start_date') else None
        self.end_date = datetime.fromisoformat(quest_data.get('end_date')) if quest_data.get('end_date') else None
        
        cooldown_seconds = quest_data.get('cooldown_seconds')
        self.cooldown = timedelta(seconds=cooldown_seconds) if cooldown_seconds else None
        
        self.repeatable = quest_data.get('repeatable', False)
        self.max_completions = quest_data.get('max_completions')
        self.is_hidden = quest_data.get('is_hidden', False)
        self.narrative = quest_data.get('narrative', '')
        self.icon = quest_data.get('icon', '📜')
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the quest to a dictionary for storage."""
        result = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'quest_type': self.quest_type.name,
            'requirements': self.requirements,
            'rewards': self.rewards,
            'prerequisite_quests': self.prerequisite_quests,
            'repeatable': self.repeatable,
            'is_hidden': self.is_hidden,
            'narrative': self.narrative,
            'icon': self.icon,
            'storyline_id': self.storyline_id,
            'sequence': self.sequence
        }
        
        # Optional time fields
        if self.expiry:
            result['expiry'] = self.expiry.isoformat()
        if self.start_date:
            result['start_date'] = self.start_date.isoformat()
        if self.end_date:
            result['end_date'] = self.end_date.isoformat()
        if self.cooldown:
            result['cooldown_seconds'] = self.cooldown.total_seconds()
        if self.max_completions is not None:
            result['max_completions'] = self.max_completions
            
        return result
    
    def create_embed(self, user_progress: Optional[Dict[str, Any]] = None) -> discord.Embed:
        """Create an embed to display the quest details and progress."""
        # Determine color based on quest type
        color_map = {
            QuestType.DAILY: 0x3498db,  # Blue
            QuestType.WEEKLY: 0x9b59b6,  # Purple
            QuestType.STORY: 0xf1c40f,  # Yellow/Gold
            QuestType.ACHIEVEMENT: 0x2ecc71,  # Green
            QuestType.EVENT: 0xe74c3c   # Red
        }
        
        embed = discord.Embed(
            title=f"{self.icon} {self.title}",
            description=self.description,
            color=color_map.get(self.quest_type, 0xffffff)
        )
        
        # Add status if progress is provided
        if user_progress:
            status = QuestStatus(user_progress.get('status', 0))
            progress_text = f"Status: **{status.name.replace('_', ' ').title()}**\n"
            
            # Add progress for each requirement
            if status == QuestStatus.IN_PROGRESS:
                req_progress = user_progress.get('requirements_progress', {})
                for i, req in enumerate(self.requirements):
                    req_id = str(i)
                    current = req_progress.get(req_id, {}).get('current', 0)
                    target = req.get('amount', 1)
                    req_type = QuestRequirementType[req.get('type')].name
                    req_desc = req.get('description', req_type)
                    progress_text += f"• {req_desc}: {current}/{target}\n"
                    
            embed.add_field(name="Progress", value=progress_text, inline=False)
        
        # Add requirements
        requirements_text = ""
        for req in self.requirements:
            req_type = QuestRequirementType[req.get('type')].name
            amount = req.get('amount', 1)
            target = req.get('target', '')
            if target:
                requirements_text += f"• {amount}x {req.get('description', f'{req_type} {target}')}\n"
            else:
                requirements_text += f"• {amount}x {req.get('description', req_type)}\n"
                
        embed.add_field(name="Requirements", value=requirements_text, inline=False)
        
        # Add rewards
        rewards_text = ""
        for reward in self.rewards:
            reward_type = QuestRewardType[reward.get('type')].name
            amount = reward.get('amount', 1)
            item = reward.get('item', '')
            if item:
                rewards_text += f"• {amount}x {reward.get('description', f'{item}')}\n"
            else:
                rewards_text += f"• {amount}x {reward.get('description', reward_type)}\n"
                
        embed.add_field(name="Rewards", value=rewards_text, inline=False)
        
        # Add time information
        if self.expiry or self.end_date:
            expires = self.expiry or self.end_date
            now = datetime.now()
            if expires > now:
                time_left = expires - now
                days = time_left.days
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                if days > 0:
                    time_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m"
                    
                embed.add_field(name="Time Remaining", value=time_str, inline=True)
            else:
                embed.add_field(name="Status", value="Expired", inline=True)
        
        # Add repeatable info
        if self.repeatable:
            if self.max_completions:
                repeat_text = f"Repeatable ({self.max_completions} times maximum)"
            else:
                repeat_text = "Repeatable"
                
            if self.cooldown:
                days = self.cooldown.days
                hours, remainder = divmod(self.cooldown.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                if days > 0:
                    cooldown_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    cooldown_str = f"{hours}h {minutes}m"
                else:
                    cooldown_str = f"{minutes}m"
                    
                repeat_text += f" (Cooldown: {cooldown_str})"
                
            embed.add_field(name="Repeatability", value=repeat_text, inline=True)
            
        return embed
    
    def is_available(self, now: Optional[datetime] = None) -> bool:
        """Check if the quest is currently available based on start/end dates."""
        if not now:
            now = datetime.now()
            
        # Check start date
        if self.start_date and now < self.start_date:
            return False
            
        # Check end date
        if self.end_date and now > self.end_date:
            return False
            
        return True
    
    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """Check if the quest has expired."""
        if not now:
            now = datetime.now()
            
        if self.expiry and now > self.expiry:
            return True
            
        return False
    
    def can_start(self, completed_quests: List[str]) -> bool:
        """Check if all prerequisites are met to start this quest."""
        for prereq in self.prerequisite_quests:
            if prereq not in completed_quests:
                return False
                
        return True
    
    def check_requirement_progress(self, requirement_id: int, user_progress: Dict[str, Any]) -> bool:
        """Check if a specific requirement has been completed based on user progress."""
        if 'requirements_progress' not in user_progress:
            return False
            
        req_progress = user_progress['requirements_progress'].get(str(requirement_id), {})
        req = self.requirements[requirement_id]
        
        current = req_progress.get('current', 0)
        target = req.get('amount', 1)
        
        return current >= target
    
    def is_completed(self, user_progress: Dict[str, Any]) -> bool:
        """Check if all requirements for the quest have been completed."""
        if 'requirements_progress' not in user_progress:
            return False
            
        for i, req in enumerate(self.requirements):
            if not self.check_requirement_progress(i, user_progress):
                return False
                
        return True
    
    def update_progress(self, requirement_type: QuestRequirementType, user_progress: Dict[str, Any], 
                        amount: int = 1, target: str = None) -> Dict[str, Any]:
        """
        Update progress for a specific requirement type.
        
        Args:
            requirement_type: The type of requirement being updated
            user_progress: The user's current progress
            amount: The amount to increase progress by
            target: Optional target (e.g., specific Veramon for CATCH type)
            
        Returns:
            Updated user progress dictionary
        """
        # Initialize progress tracking if not present
        if 'requirements_progress' not in user_progress:
            user_progress['requirements_progress'] = {}
            
        # Check each requirement to see if it matches
        for i, req in enumerate(self.requirements):
            req_type = QuestRequirementType[req.get('type')]
            req_target = req.get('target')
            
            # If requirement type matches and target matches (if specified)
            if req_type == requirement_type and (not req_target or not target or req_target == target):
                req_id = str(i)
                if req_id not in user_progress['requirements_progress']:
                    user_progress['requirements_progress'][req_id] = {'current': 0, 'updated_at': time.time()}
                    
                # Update progress
                user_progress['requirements_progress'][req_id]['current'] += amount
                user_progress['requirements_progress'][req_id]['updated_at'] = time.time()
                
        # Check if all requirements are now complete
        if self.is_completed(user_progress) and user_progress.get('status') == QuestStatus.IN_PROGRESS.value:
            user_progress['status'] = QuestStatus.COMPLETED.value
            user_progress['completed_at'] = time.time()
            
        return user_progress


class UserQuestManager:
    """
    Manages quest progress and tracking for a single user.
    
    This is a helper class that works with QuestCog for tracking individual user progress.
    """
    
    def __init__(self, user_id: str, quest_data: Dict[str, Any] = None):
        self.user_id = user_id
        self.quest_data = quest_data or {
            'active_quests': {},      # quest_id -> progress dictionary
            'completed_quests': [],   # List of completed quest IDs
            'cooldowns': {},          # quest_id -> expiry timestamp
            'quest_history': [],      # List of quest completion records
            'last_daily_refresh': 0,  # Timestamp of last daily refresh
            'last_weekly_refresh': 0  # Timestamp of last weekly refresh
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert user quest data to a dictionary for storage."""
        return self.quest_data
    
    def get_active_quests(self) -> Dict[str, Dict[str, Any]]:
        """Get all active quests for the user."""
        return self.quest_data.get('active_quests', {})
    
    def get_quest_progress(self, quest_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a specific quest."""
        return self.quest_data.get('active_quests', {}).get(quest_id)
    
    def is_quest_active(self, quest_id: str) -> bool:
        """Check if a quest is active for the user."""
        return quest_id in self.quest_data.get('active_quests', {})
    
    def is_quest_completed(self, quest_id: str) -> bool:
        """Check if a quest has been completed."""
        return quest_id in self.quest_data.get('completed_quests', [])
    
    def is_quest_on_cooldown(self, quest_id: str) -> bool:
        """Check if a quest is currently on cooldown."""
        cooldowns = self.quest_data.get('cooldowns', {})
        if quest_id not in cooldowns:
            return False
            
        return cooldowns[quest_id] > time.time()
    
    def get_cooldown_expiry(self, quest_id: str) -> Optional[float]:
        """Get the timestamp when a quest cooldown expires."""
        return self.quest_data.get('cooldowns', {}).get(quest_id)
    
    def activate_quest(self, quest: Quest) -> bool:
        """
        Activate a quest for the user.
        
        Returns:
            True if the quest was activated, False otherwise
        """
        quest_id = quest.id
        
        # Check if quest is already active
        if self.is_quest_active(quest_id):
            return False
            
        # Check if quest can be started (not on cooldown, prerequisites met)
        if self.is_quest_on_cooldown(quest_id):
            return False
            
        if not quest.can_start(self.quest_data.get('completed_quests', [])):
            return False
            
        # Initialize new quest progress
        if 'active_quests' not in self.quest_data:
            self.quest_data['active_quests'] = {}
            
        self.quest_data['active_quests'][quest_id] = {
            'status': QuestStatus.IN_PROGRESS.value,
            'started_at': time.time(),
            'requirements_progress': {}
        }
        
        return True
    
    def complete_quest(self, quest_id: str) -> bool:
        """
        Mark a quest as completed (but not claimed).
        
        Returns:
            True if the quest was marked complete, False otherwise
        """
        if not self.is_quest_active(quest_id):
            return False
            
        quest_progress = self.quest_data['active_quests'][quest_id]
        
        if quest_progress.get('status') != QuestStatus.COMPLETED.value:
            quest_progress['status'] = QuestStatus.COMPLETED.value
            quest_progress['completed_at'] = time.time()
            
        return True
    
    def claim_quest_rewards(self, quest: Quest) -> bool:
        """
        Claim rewards for a completed quest.
        
        Returns:
            True if rewards were claimed, False otherwise
        """
        quest_id = quest.id
        
        if not self.is_quest_active(quest_id):
            return False
            
        quest_progress = self.quest_data['active_quests'][quest_id]
        
        if quest_progress.get('status') != QuestStatus.COMPLETED.value:
            return False
            
        # Mark as claimed
        quest_progress['status'] = QuestStatus.CLAIMED.value
        quest_progress['claimed_at'] = time.time()
        
        # Add to completed quests list if not already there
        if quest_id not in self.quest_data.get('completed_quests', []):
            if 'completed_quests' not in self.quest_data:
                self.quest_data['completed_quests'] = []
            self.quest_data['completed_quests'].append(quest_id)
            
        # Add to history
        if 'quest_history' not in self.quest_data:
            self.quest_data['quest_history'] = []
            
        self.quest_data['quest_history'].append({
            'quest_id': quest_id,
            'completed_at': quest_progress.get('completed_at'),
            'claimed_at': quest_progress.get('claimed_at')
        })
        
        # Set cooldown if repeatable
        if quest.repeatable and quest.cooldown:
            if 'cooldowns' not in self.quest_data:
                self.quest_data['cooldowns'] = {}
                
            cooldown_expiry = time.time() + quest.cooldown.total_seconds()
            self.quest_data['cooldowns'][quest_id] = cooldown_expiry
            
        # Remove from active quests if not repeatable or max completions reached
        if not quest.repeatable:
            del self.quest_data['active_quests'][quest_id]
        else:
            # Check max completions
            if quest.max_completions:
                # Count how many times this quest has been completed
                completed_count = sum(1 for entry in self.quest_data.get('quest_history', []) 
                                    if entry.get('quest_id') == quest_id)
                                    
                if completed_count >= quest.max_completions:
                    del self.quest_data['active_quests'][quest_id]
                else:
                    # Reset quest for next attempt
                    self.quest_data['active_quests'][quest_id] = {
                        'status': QuestStatus.IN_PROGRESS.value,
                        'started_at': time.time(),
                        'requirements_progress': {}
                    }
            else:
                # Reset quest for next attempt
                self.quest_data['active_quests'][quest_id] = {
                    'status': QuestStatus.IN_PROGRESS.value,
                    'started_at': time.time(),
                    'requirements_progress': {}
                }
                
        return True
    
    def update_quest_progress(self, quest: Quest, requirement_type: QuestRequirementType,
                             amount: int = 1, target: str = None) -> bool:
        """
        Update progress for a specific quest.
        
        Args:
            quest: The quest to update
            requirement_type: The type of requirement being updated
            amount: The amount to increase progress by
            target: Optional target (e.g., specific Veramon for CATCH type)
            
        Returns:
            True if the quest progress was updated, False otherwise
        """
        quest_id = quest.id
        
        if not self.is_quest_active(quest_id):
            return False
            
        quest_progress = self.quest_data['active_quests'][quest_id]
        
        if quest_progress.get('status') != QuestStatus.IN_PROGRESS.value:
            return False
            
        # Update quest progress
        updated_progress = quest.update_progress(requirement_type, quest_progress, amount, target)
        self.quest_data['active_quests'][quest_id] = updated_progress
        
        return True
    
    def refresh_daily_quests(self, quest_manager, force: bool = False) -> int:
        """
        Refresh daily quests.
        
        Args:
            quest_manager: The QuestManager to get new quests from
            force: Whether to force refresh regardless of time
            
        Returns:
            Number of quests refreshed
        """
        now = time.time()
        last_refresh = self.quest_data.get('last_daily_refresh', 0)
        
        # Check if it's time to refresh (24 hours have passed)
        one_day = 24 * 60 * 60
        if not force and now - last_refresh < one_day:
            return 0
            
        # Remove old daily quests
        active_quests = self.quest_data.get('active_quests', {})
        for quest_id in list(active_quests.keys()):
            quest = quest_manager.get_quest(quest_id)
            if quest and quest.quest_type == QuestType.DAILY:
                del active_quests[quest_id]
                
        # Get new daily quests
        daily_quests = quest_manager.get_quests_by_type(QuestType.DAILY)
        count = 0
        
        for quest in daily_quests:
            if quest.is_available() and not self.is_quest_on_cooldown(quest.id):
                if self.activate_quest(quest):
                    count += 1
                    
        # Update refresh time
        self.quest_data['last_daily_refresh'] = now
        return count
    
    def refresh_weekly_quests(self, quest_manager, force: bool = False) -> int:
        """
        Refresh weekly quests.
        
        Args:
            quest_manager: The QuestManager to get new quests from
            force: Whether to force refresh regardless of time
            
        Returns:
            Number of quests refreshed
        """
        now = time.time()
        last_refresh = self.quest_data.get('last_weekly_refresh', 0)
        
        # Check if it's time to refresh (7 days have passed)
        one_week = 7 * 24 * 60 * 60
        if not force and now - last_refresh < one_week:
            return 0
            
        # Remove old weekly quests
        active_quests = self.quest_data.get('active_quests', {})
        for quest_id in list(active_quests.keys()):
            quest = quest_manager.get_quest(quest_id)
            if quest and quest.quest_type == QuestType.WEEKLY:
                del active_quests[quest_id]
                
        # Get new weekly quests
        weekly_quests = quest_manager.get_quests_by_type(QuestType.WEEKLY)
        count = 0
        
        for quest in weekly_quests:
            if quest.is_available() and not self.is_quest_on_cooldown(quest.id):
                if self.activate_quest(quest):
                    count += 1
                    
        # Update refresh time
        self.quest_data['last_weekly_refresh'] = now
        return count
    
    def check_expired_quests(self, quest_manager) -> List[str]:
        """
        Check for expired quests and mark them as such.
        
        Returns:
            List of expired quest IDs
        """
        expired_ids = []
        active_quests = self.quest_data.get('active_quests', {})
        
        for quest_id in list(active_quests.keys()):
            quest = quest_manager.get_quest(quest_id)
            if not quest:
                continue
                
            if quest.is_expired():
                active_quests[quest_id]['status'] = QuestStatus.EXPIRED.value
                expired_ids.append(quest_id)
                
        return expired_ids
