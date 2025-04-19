import discord
import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

from src.models.event import Event, EventStatus, EventType

logger = logging.getLogger('veramon.event_manager')

class EventManager:
    """
    Manages loading, storing, and retrieving seasonal events.
    
    This is a global manager that loads event definitions from files
    and provides access to them.
    """
    
    def __init__(self, event_dir: str = "data/events"):
        self.event_dir = event_dir
        self.events = {}  # event_id -> Event object
        
        self.ensure_event_directory()
        self.load_all_events()
        
    def ensure_event_directory(self):
        """Ensure the event directory structure exists."""
        os.makedirs(self.event_dir, exist_ok=True)
            
    def load_all_events(self):
        """Load all event definitions from files."""
        count = 0
        if not os.path.exists(self.event_dir):
            return
            
        for filename in os.listdir(self.event_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.event_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    event_data = json.load(f)
                    
                # Single event or multiple events in one file
                if isinstance(event_data, list):
                    for e_data in event_data:
                        self._register_event(e_data)
                        count += 1
                else:
                    self._register_event(event_data)
                    count += 1
                    
            except Exception as e:
                logger.error(f"Error loading event from {filepath}: {e}")
                
        logger.info(f"Loaded {count} events from {self.event_dir}")
        
    def _register_event(self, event_data: Dict[str, Any]):
        """Register an event in the manager."""
        if 'id' not in event_data:
            logger.error(f"Event data missing 'id' field: {event_data}")
            return
            
        event = Event(event_data)
        self.events[event.id] = event
            
    def reload_events(self):
        """Reload all event definitions from files."""
        self.events = {}
        self.load_all_events()
        
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get an event by ID."""
        return self.events.get(event_id)
        
    def get_events_by_status(self, status: EventStatus) -> List[Event]:
        """Get all events with the specified status."""
        now = datetime.now()
        return [e for e in self.events.values() if e.get_status(now) == status]
        
    def get_active_events(self) -> List[Event]:
        """Get all currently active events."""
        return self.get_events_by_status(EventStatus.ACTIVE)
        
    def get_upcoming_events(self) -> List[Event]:
        """Get all upcoming events, sorted by start date."""
        events = self.get_events_by_status(EventStatus.UPCOMING)
        return sorted(events, key=lambda e: e.start_date)
        
    def get_recently_ended_events(self, days: int = 7) -> List[Event]:
        """Get events that ended within the specified number of days."""
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        return [
            e for e in self.events.values() 
            if e.get_status(now) == EventStatus.ENDED and e.end_date >= cutoff
        ]
        
    def create_event(self, event_data: Dict[str, Any]) -> Optional[Event]:
        """Create a new event and save it to file."""
        if 'id' not in event_data:
            logger.error("Cannot create event without an ID")
            return None
            
        event_id = event_data['id']
        
        # Check for existing event
        if event_id in self.events:
            logger.error(f"Cannot create event with duplicate ID: {event_id}")
            return None
            
        # Create and register the event
        event = Event(event_data)
        self.events[event_id] = event
        
        # Save to file
        self._save_event_to_file(event)
        
        return event
        
    def update_event(self, event_id: str, event_data: Dict[str, Any]) -> Optional[Event]:
        """Update an existing event and save changes to file."""
        if event_id not in self.events:
            logger.error(f"Cannot update non-existent event: {event_id}")
            return None
            
        # Update the event data
        existing_event = self.events[event_id]
        updated_data = existing_event.to_dict()
        updated_data.update(event_data)
        
        # Create updated event
        event = Event(updated_data)
        self.events[event_id] = event
        
        # Save to file
        self._save_event_to_file(event)
        
        return event
        
    def delete_event(self, event_id: str) -> bool:
        """Delete an event and its file."""
        if event_id not in self.events:
            logger.error(f"Cannot delete non-existent event: {event_id}")
            return False
            
        # Delete from memory
        del self.events[event_id]
                
        # Delete file
        filepath = os.path.join(self.event_dir, f"{event_id}.json")
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception as e:
                logger.error(f"Error deleting event file {filepath}: {e}")
                return False
        else:
            # File doesn't exist but we removed from memory
            return True
            
    def _save_event_to_file(self, event: Event) -> bool:
        """Save an event to its file."""
        os.makedirs(self.event_dir, exist_ok=True)
        
        filepath = os.path.join(self.event_dir, f"{event.id}.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(event.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving event to {filepath}: {e}")
            return False
            
    def update_community_goal(self, event_id: str, amount: int) -> bool:
        """Update progress for a community goal."""
        if event_id not in self.events:
            logger.error(f"Cannot update community goal for non-existent event: {event_id}")
            return False
            
        event = self.events[event_id]
        
        if not event.community_goal:
            logger.error(f"Event {event_id} has no community goal")
            return False
            
        # Update progress
        current = event.community_goal.get('current', 0)
        event.community_goal['current'] = current + amount
        
        # Save to file
        self._save_event_to_file(event)
        
        return True


# Global event manager instance
event_manager = None

def init_event_manager(event_dir: str = "data/events"):
    """Initialize the global event manager."""
    global event_manager
    event_manager = EventManager(event_dir)
    return event_manager
