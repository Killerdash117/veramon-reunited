import discord
import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Iterator

from src.models.quest import Quest, QuestType, QuestStatus, QuestRequirementType, QuestRewardType, UserQuestManager

logger = logging.getLogger('veramon.quest_manager')

class QuestManager:
    """
    Manages loading, storing, and retrieving quests and achievements.
    
    This is a global manager that loads quest definitions from files
    and provides access to them. Individual user progress is tracked
    through the UserQuestManager.
    """
    
    def __init__(self, quest_dir: str = "data/quests"):
        self.quest_dir = quest_dir
        self.quests = {}  # quest_id -> Quest object
        self.event_quests = {}  # event_id -> list of quest_ids
        self.story_lines = {}  # story_line_id -> list of quest_ids in order
        
        self.ensure_quest_directory()
        self.load_all_quests()
        
    def ensure_quest_directory(self):
        """Ensure the quest directory structure exists."""
        for subdir in ['daily', 'weekly', 'story', 'achievements', 'events']:
            path = os.path.join(self.quest_dir, subdir)
            os.makedirs(path, exist_ok=True)
            
    def load_all_quests(self):
        """Load all quest definitions from files."""
        count = 0
        for quest_type in QuestType:
            type_dir = os.path.join(self.quest_dir, quest_type.name.lower())
            if not os.path.exists(type_dir):
                continue
                
            for filename in os.listdir(type_dir):
                if not filename.endswith('.json'):
                    continue
                    
                filepath = os.path.join(type_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        quest_data = json.load(f)
                        
                    # Single quest or multiple quests in one file
                    if isinstance(quest_data, list):
                        for q_data in quest_data:
                            self._register_quest(q_data, quest_type)
                            count += 1
                    else:
                        self._register_quest(quest_data, quest_type)
                        count += 1
                        
                except Exception as e:
                    logger.error(f"Error loading quest from {filepath}: {e}")
                    
        logger.info(f"Loaded {count} quests from {self.quest_dir}")
        
        # Organize story quests into storylines
        self._organize_storylines()
        
    def _register_quest(self, quest_data: Dict[str, Any], default_type: QuestType = None):
        """Register a quest in the manager."""
        if 'id' not in quest_data:
            logger.error(f"Quest data missing 'id' field: {quest_data}")
            return
            
        # Set default type if not specified
        if 'quest_type' not in quest_data and default_type:
            quest_data['quest_type'] = default_type.name
            
        quest = Quest(quest_data)
        self.quests[quest.id] = quest
        
        # Add to event tracking if it's an event quest
        if quest.quest_type == QuestType.EVENT and 'event_id' in quest_data:
            event_id = quest_data['event_id']
            if event_id not in self.event_quests:
                self.event_quests[event_id] = []
            self.event_quests[event_id].append(quest.id)
            
    def _organize_storylines(self):
        """Organize story quests into storylines."""
        story_quests = [q for q in self.quests.values() if q.quest_type == QuestType.STORY]
        
        # Group by storyline
        for quest in story_quests:
            storyline_id = quest.storyline_id
            if not storyline_id:
                continue
                
            if storyline_id not in self.story_lines:
                self.story_lines[storyline_id] = []
                
            self.story_lines[storyline_id].append(quest.id)
            
        # Sort each storyline by sequence
        for storyline_id, quest_ids in self.story_lines.items():
            quests = [self.quests[qid] for qid in quest_ids]
            sorted_quests = sorted(quests, key=lambda q: q.sequence)
            self.story_lines[storyline_id] = [q.id for q in sorted_quests]
            
    def reload_quests(self):
        """Reload all quest definitions from files."""
        self.quests = {}
        self.event_quests = {}
        self.story_lines = {}
        self.load_all_quests()
        
    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get a quest by ID."""
        return self.quests.get(quest_id)
        
    def get_quests_by_type(self, quest_type: QuestType) -> List[Quest]:
        """Get all quests of a specific type."""
        return [q for q in self.quests.values() if q.quest_type == quest_type]
        
    def get_available_quests(self, completed_quests: List[str] = None) -> List[Quest]:
        """Get all quests that are currently available."""
        completed = completed_quests or []
        now = datetime.now()
        
        return [
            q for q in self.quests.values() 
            if q.is_available(now) and (q.repeatable or q.id not in completed)
        ]
        
    def get_event_quests(self, event_id: str) -> List[Quest]:
        """Get all quests for a specific event."""
        quest_ids = self.event_quests.get(event_id, [])
        return [self.quests[qid] for qid in quest_ids if qid in self.quests]
        
    def get_storyline(self, storyline_id: str) -> List[Quest]:
        """Get all quests in a storyline in order."""
        quest_ids = self.story_lines.get(storyline_id, [])
        return [self.quests[qid] for qid in quest_ids if qid in self.quests]
        
    def get_next_story_quest(self, storyline_id: str, completed_quests: List[str]) -> Optional[Quest]:
        """Get the next story quest for a user based on their completed quests."""
        storyline = self.get_storyline(storyline_id)
        
        for quest in storyline:
            if quest.id not in completed_quests:
                return quest
                
        return None  # All quests in storyline completed
        
    def create_quest(self, quest_data: Dict[str, Any]) -> Optional[Quest]:
        """Create a new quest and save it to file."""
        if 'id' not in quest_data:
            logger.error("Cannot create quest without an ID")
            return None
            
        quest_id = quest_data['id']
        
        # Check for existing quest
        if quest_id in self.quests:
            logger.error(f"Cannot create quest with duplicate ID: {quest_id}")
            return None
            
        # Create and register the quest
        quest = Quest(quest_data)
        self.quests[quest_id] = quest
        
        # Save to file
        self._save_quest_to_file(quest)
        
        return quest
        
    def update_quest(self, quest_id: str, quest_data: Dict[str, Any]) -> Optional[Quest]:
        """Update an existing quest and save changes to file."""
        if quest_id not in self.quests:
            logger.error(f"Cannot update non-existent quest: {quest_id}")
            return None
            
        # Update the quest data
        existing_quest = self.quests[quest_id]
        updated_data = existing_quest.to_dict()
        updated_data.update(quest_data)
        
        # Create updated quest
        quest = Quest(updated_data)
        self.quests[quest_id] = quest
        
        # Save to file
        self._save_quest_to_file(quest)
        
        return quest
        
    def delete_quest(self, quest_id: str) -> bool:
        """Delete a quest and its file."""
        if quest_id not in self.quests:
            logger.error(f"Cannot delete non-existent quest: {quest_id}")
            return False
            
        quest = self.quests[quest_id]
        
        # Delete from memory
        del self.quests[quest_id]
        
        # Remove from event tracking
        for event_id, quest_ids in list(self.event_quests.items()):
            if quest_id in quest_ids:
                self.event_quests[event_id].remove(quest_id)
                
        # Remove from storylines
        for storyline_id, quest_ids in list(self.story_lines.items()):
            if quest_id in quest_ids:
                self.story_lines[storyline_id].remove(quest_id)
                
        # Delete file
        quest_type_dir = os.path.join(self.quest_dir, quest.quest_type.name.lower())
        filepath = os.path.join(quest_type_dir, f"{quest_id}.json")
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception as e:
                logger.error(f"Error deleting quest file {filepath}: {e}")
                return False
        else:
            # File doesn't exist but we removed from memory
            return True
            
    def _save_quest_to_file(self, quest: Quest) -> bool:
        """Save a quest to its file."""
        quest_type_dir = os.path.join(self.quest_dir, quest.quest_type.name.lower())
        os.makedirs(quest_type_dir, exist_ok=True)
        
        filepath = os.path.join(quest_type_dir, f"{quest.id}.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(quest.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving quest to {filepath}: {e}")
            return False
            
    def process_event(self, user_id: str, user_manager: UserQuestManager, 
                     event_type: QuestRequirementType, amount: int = 1, 
                     target: str = None) -> List[str]:
        """
        Process an event for a user, updating all relevant quest progress.
        
        Args:
            user_id: The user's ID
            user_manager: The user's quest manager
            event_type: The type of event that occurred
            amount: The amount to increase progress by
            target: Optional target (e.g., specific Veramon for CATCH type)
            
        Returns:
            List of quest IDs that were updated
        """
        updated_quests = []
        
        # Get active quests for the user
        active_quests = user_manager.get_active_quests()
        
        for quest_id, progress in active_quests.items():
            # Skip quests that aren't in progress
            if progress.get('status') != QuestStatus.IN_PROGRESS.value:
                continue
                
            quest = self.get_quest(quest_id)
            if not quest:
                continue
                
            # Update progress for matching requirements
            if user_manager.update_quest_progress(quest, event_type, amount, target):
                updated_quests.append(quest_id)
                
        return updated_quests
        
    def update_progress(self, user_id: str, requirement_type: str, amount: int = 1, 
                       metadata: Dict[str, Any] = None):
        """Update progress for all quests with a specific requirement type."""
        user_quests = self._get_user_quests(user_id)
        
        if not user_quests:
            return
            
        quests_updated = []
        
        # Process active daily and weekly quests
        for quest_id in user_quests.get('active_quests', []):
            quest_data = user_quests.get('quest_data', {}).get(quest_id)
            
            if not quest_data:
                continue
                
            if self._update_quest_progress(quest_data, requirement_type, amount, metadata):
                quests_updated.append(quest_id)
        
        # Process active story quests
        for storyline_id, story_data in user_quests.get('storylines', {}).items():
            current_quest_id = story_data.get('current_quest')
            
            if not current_quest_id:
                continue
                
            quest_data = user_quests.get('quest_data', {}).get(current_quest_id)
            
            if not quest_data:
                continue
                
            if self._update_quest_progress(quest_data, requirement_type, amount, metadata):
                quests_updated.append(current_quest_id)
        
        # Process achievements
        for achievement_id, achievement_data in user_quests.get('achievements', {}).items():
            if achievement_data.get('completed'):
                continue
                
            if self._update_quest_progress(achievement_data, requirement_type, amount, metadata):
                quests_updated.append(achievement_id)
        
        # Save updated quests
        if quests_updated:
            self._save_user_quests(user_id, user_quests)
            
        return quests_updated
        
    def _update_quest_progress(self, quest_data: Dict[str, Any], 
                              requirement_type: str, amount: int = 1,
                              metadata: Dict[str, Any] = None) -> bool:
        """Update progress for a specific quest data object."""
        if quest_data.get('completed'):
            return False
            
        requirements = quest_data.get('requirements', [])
        updated = False
        
        for req in requirements:
            if req.get('type') == requirement_type:
                # Check if metadata constraints match
                if metadata and not self._check_metadata_constraints(req, metadata):
                    continue
                    
                # Update progress
                current = req.get('progress', 0)
                new_progress = min(current + amount, req.get('amount', 1))
                req['progress'] = new_progress
                updated = True
        
        # Check if all requirements are met
        if updated:
            all_completed = True
            
            for req in requirements:
                progress = req.get('progress', 0)
                amount_needed = req.get('amount', 1)
                
                if progress < amount_needed:
                    all_completed = False
                    break
                    
            if all_completed:
                quest_data['completed'] = True
                quest_data['completed_at'] = time.time()
                
        return updated
        
    def _check_metadata_constraints(self, requirement: Dict[str, Any], 
                                   metadata: Dict[str, Any]) -> bool:
        """Check if metadata matches constraint conditions in the requirement."""
        constraints = requirement.get('constraints', {})
        
        for key, value in constraints.items():
            if key not in metadata or metadata[key] != value:
                return False
                
        return True
        
    def _get_user_quests(self, user_id: str) -> Dict[str, Any]:
        """Get user quest data from file."""
        filepath = os.path.join(self.quest_dir, f"{user_id}.json")
        
        if not os.path.exists(filepath):
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user quests from {filepath}: {e}")
            return {}
        
    def _save_user_quests(self, user_id: str, user_quests: Dict[str, Any]) -> bool:
        """Save user quest data to file."""
        filepath = os.path.join(self.quest_dir, f"{user_id}.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(user_quests, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving user quests to {filepath}: {e}")
            return False


# Global quest manager instance
quest_manager = None

def init_quest_manager(quest_dir: str = "data/quests"):
    """Initialize the global quest manager."""
    global quest_manager
    quest_manager = QuestManager(quest_dir)
    return quest_manager
