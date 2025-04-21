"""
Actor-based system for Veramon Reunited

This implements a lightweight actor model where each actor maintains its own state
and processes messages in isolation. This architecture allows for better scaling,
as actors can potentially be distributed across multiple instances.
"""

import asyncio
import logging
import uuid
import json
import time
import traceback
from typing import Dict, Any, Callable, Awaitable, List, Optional, Set
from functools import wraps
import pickle
import base64
import sqlite3
from datetime import datetime
from src.db.db import get_connection

logger = logging.getLogger(__name__)

def time_actor_operation(operation_name: str):
    """Decorator to time actor operations for performance monitoring."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                if hasattr(args[0], 'record_operation_time'):
                    args[0].record_operation_time(operation_name, elapsed)
                if elapsed > 0.5:  # Log slow operations
                    logger.warning(f"Actor operation {operation_name} took {elapsed:.4f}s")
        return wrapper
    return decorator

class ActorRef:
    """Reference to an actor that can be used to send messages to it."""
    def __init__(self, actor_id: str, actor_system):
        self.actor_id = actor_id
        self._actor_system = actor_system
        
    async def tell(self, message: Dict[str, Any], sender: Optional['ActorRef'] = None) -> None:
        """Send a fire-and-forget message to the actor."""
        return await self._actor_system.tell(self.actor_id, message, sender)
        
    async def ask(self, message: Dict[str, Any], timeout: float = 5.0) -> Any:
        """Send a message and wait for a response."""
        return await self._actor_system.ask(self.actor_id, message, timeout)
        
    def __eq__(self, other):
        if not isinstance(other, ActorRef):
            return False
        return self.actor_id == other.actor_id
        
    def __hash__(self):
        return hash(self.actor_id)

class PersistableActor:
    """Mixin for actors that can have their state persisted to a database."""
    
    def __init__(self):
        self._persistence_key = self.actor_id
        self._last_persisted = 0
        self._dirty = False
        
    def mark_dirty(self):
        """Mark this actor as having changes that need to be persisted."""
        self._dirty = True
        
    async def persist_state(self, force=False):
        """Persist the actor's state to the database."""
        if not force and not self._dirty:
            return False  # No changes to persist
            
        try:
            current_time = time.time()
            # Only persist if dirty and not persisted recently (to avoid db spam)
            if force or (self._dirty and (current_time - self._last_persisted > 5.0)):
                state = self.get_persistent_state()
                
                # Convert state to a serializable format
                serialized_state = json.dumps(state)
                
                conn = get_connection()
                cursor = conn.cursor()
                
                # Upsert the actor state
                cursor.execute("""
                    INSERT INTO actor_state 
                    (actor_id, actor_type, serialized_state, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(actor_id) DO UPDATE SET
                    serialized_state = excluded.serialized_state,
                    updated_at = excluded.updated_at
                """, (
                    self._persistence_key,
                    self.__class__.__name__,
                    serialized_state,
                    datetime.utcnow().isoformat()
                ))
                
                conn.commit()
                conn.close()
                
                self._last_persisted = current_time
                self._dirty = False
                return True
        except Exception as e:
            logger.exception(f"Error persisting actor state for {self.actor_id}: {e}")
            
        return False
    
    def get_persistent_state(self) -> Dict[str, Any]:
        """
        Get the state to persist. Override this in subclasses.
        The returned dictionary must be JSON serializable.
        """
        raise NotImplementedError("PersistableActor subclasses must implement get_persistent_state")
        
    def restore_from_state(self, state: Dict[str, Any]) -> None:
        """
        Restore actor state from persisted data. Override this in subclasses.
        """
        raise NotImplementedError("PersistableActor subclasses must implement restore_from_state")

class Actor:
    """Base actor class that processes messages one at a time."""
    def __init__(self):
        self.actor_id = str(uuid.uuid4())
        self._actor_system = None
        self._ref = None
        self._operation_times = {}
        self._metrics = {
            "message_count": 0,
            "error_count": 0,
            "last_message_time": 0,
            "max_processing_time": 0,
            "total_processing_time": 0
        }
        
    def record_operation_time(self, operation: str, time_taken: float) -> None:
        """Record the time taken for an operation for metrics."""
        if operation not in self._operation_times:
            self._operation_times[operation] = []
        self._operation_times[operation].append(time_taken)
        # Keep only the last 100 measurements
        if len(self._operation_times[operation]) > 100:
            self._operation_times[operation].pop(0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this actor."""
        metrics = self._metrics.copy()
        metrics["operations"] = {}
        
        for op, times in self._operation_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                metrics["operations"][op] = {
                    "avg_time": avg_time,
                    "max_time": max_time,
                    "count": len(times)
                }
                
        return metrics
            
    async def receive(self, message: Dict[str, Any], sender: Optional[ActorRef] = None) -> Any:
        """Process an incoming message and return a result."""
        # This should be overridden by subclasses
        raise NotImplementedError("Actors must implement the receive method")
        
    def get_ref(self) -> ActorRef:
        """Get a reference to this actor."""
        if not self._ref:
            if not self._actor_system:
                raise RuntimeError("Actor not registered with an ActorSystem")
            self._ref = ActorRef(self.actor_id, self._actor_system)
        return self._ref

class ActorSystem:
    """System that manages actors and routes messages between them."""
    def __init__(self, name: str):
        self.name = name
        self._actors: Dict[str, Actor] = {}
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._processor_task = None
        self._actor_types: Dict[str, type] = {}
        self._persistence_task = None
        self._shutdown_hook_task = None
        
        # Initialize actor_state table
        self._ensure_actor_state_table()
        
    def _ensure_actor_state_table(self):
        """Ensure the actor_state table exists in the database."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create the actor_state table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actor_state (
                actor_id TEXT PRIMARY KEY,
                actor_type TEXT NOT NULL,
                serialized_state TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
    def register_actor_type(self, actor_type_name: str, actor_class: type) -> None:
        """Register an actor type that can be created on demand."""
        if not issubclass(actor_class, Actor):
            raise ValueError(f"Actor class must be a subclass of Actor, got {actor_class}")
        self._actor_types[actor_type_name] = actor_class
        
    def register_actor(self, actor: Actor) -> ActorRef:
        """Register an actor with the system."""
        if actor.actor_id in self._actors:
            raise ValueError(f"Actor with ID {actor.actor_id} already registered")
        self._actors[actor.actor_id] = actor
        actor._actor_system = self
        return actor.get_ref()
        
    async def create_actor(self, actor_type_name: str, *args, **kwargs) -> ActorRef:
        """Create and register an actor of the given type."""
        if actor_type_name not in self._actor_types:
            raise ValueError(f"Unknown actor type: {actor_type_name}")
        
        actor_class = self._actor_types[actor_type_name]
        actor = actor_class(*args, **kwargs)
        return self.register_actor(actor)
        
    def get_actor(self, actor_id: str) -> Optional[Actor]:
        """Get an actor by its ID."""
        return self._actors.get(actor_id)
        
    async def get_or_create_actor(self, actor_id: str, actor_type_name: str, *args, **kwargs) -> ActorRef:
        """Get an existing actor or create a new one if it doesn't exist, with persistence."""
        if actor_id in self._actors:
            return self._actors[actor_id].get_ref()
        
        # Try to load from persistence
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT serialized_state, actor_type
                FROM actor_state
                WHERE actor_id = ?
            """, (actor_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                serialized_state, actor_type = row
                
                # Get the actor class
                if actor_type_name not in self._actor_types:
                    logger.warning(f"Actor type {actor_type_name} not registered, ignoring persisted state")
                else:
                    actor_class = self._actor_types[actor_type_name]
                    actor = actor_class(*args, **kwargs)
                    actor.actor_id = actor_id
                    
                    # Restore state if it's a PersistableActor
                    if isinstance(actor, PersistableActor):
                        try:
                            state = json.loads(serialized_state)
                            actor.restore_from_state(state)
                            logger.info(f"Restored actor {actor_id} from persistence")
                        except Exception as e:
                            logger.exception(f"Error restoring actor {actor_id} from persisted state: {e}")
                    
                    return self.register_actor(actor)
        except Exception as e:
            logger.exception(f"Error loading actor {actor_id} from persistence: {e}")
            
        # Create a new actor if it doesn't exist in persistence
        if actor_type_name not in self._actor_types:
            raise ValueError(f"Unknown actor type: {actor_type_name}")
            
        actor_class = self._actor_types[actor_type_name]
        actor = actor_class(*args, **kwargs)
        actor.actor_id = actor_id
        
        return self.register_actor(actor)
        
    async def tell(self, actor_id: str, message: Dict[str, Any], sender: Optional[ActorRef] = None) -> None:
        """Send a fire-and-forget message to an actor."""
        if not self._running:
            await self.start()
            
        await self._message_queue.put((actor_id, message, sender, None))
        
    async def ask(self, actor_id: str, message: Dict[str, Any], timeout: float = 5.0) -> Any:
        """Send a message to an actor and wait for a response."""
        if not self._running:
            await self.start()
            
        future = asyncio.Future()
        message_id = str(uuid.uuid4())
        self._response_futures[message_id] = future
        
        # Add a message_id to the message so the actor can respond
        message_with_id = message.copy()
        message_with_id["_message_id"] = message_id
        
        await self._message_queue.put((actor_id, message_with_id, None, message_id))
        
        try:
            result = await asyncio.wait_for(future, timeout)
            return result
        except asyncio.TimeoutError:
            del self._response_futures[message_id]
            raise TimeoutError(f"No response from actor {actor_id} after {timeout} seconds")
            
    async def _persist_actors(self):
        """Periodically persist all persistable actors."""
        while self._running:
            try:
                # Wait for a bit before checking for dirty actors
                await asyncio.sleep(30)  # Every 30 seconds
                
                # Persist all persistable actors
                for actor_id, actor in list(self._actors.items()):
                    if isinstance(actor, PersistableActor):
                        await actor.persist_state()
                        
            except asyncio.CancelledError:
                # Final persist on cancellation
                logger.info("Persistence task cancelled, performing final persist...")
                for actor_id, actor in list(self._actors.items()):
                    if isinstance(actor, PersistableActor):
                        await actor.persist_state(force=True)
                break
            except Exception as e:
                logger.exception(f"Error in actor persistence task: {e}")
                
    async def start(self) -> None:
        """Start the actor system message processor."""
        if self._running:
            return
            
        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
        self._persistence_task = asyncio.create_task(self._persist_actors())
        
        # Register shutdown hook
        try:
            loop = asyncio.get_running_loop()
            self._shutdown_hook_task = loop.create_task(self._register_shutdown_hook())
        except Exception:
            logger.warning("Could not register shutdown hook")
            
        logger.info(f"Started ActorSystem '{self.name}'")
        
    async def _register_shutdown_hook(self):
        """Register a hook to gracefully shut down when the event loop is closing."""
        try:
            loop = asyncio.get_running_loop()
            
            def shutdown_callback():
                if not self._persistence_task.done():
                    # Create a new event loop for the shutdown logic
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # Run the shutdown logic
                    new_loop.run_until_complete(self._final_persist())
                    new_loop.close()
            
            # Add the callback to be executed when the event loop is closing
            loop.add_signal_handler(15, shutdown_callback)  # SIGTERM
            loop.add_signal_handler(2, shutdown_callback)   # SIGINT
        except Exception as e:
            logger.warning(f"Failed to register shutdown hook: {e}")
            
    async def _final_persist(self):
        """Final persist of all actors when shutting down."""
        logger.info("Performing final persist of all actors...")
        for actor_id, actor in list(self._actors.items()):
            if isinstance(actor, PersistableActor):
                await actor.persist_state(force=True)
        logger.info("Final persist completed")
        
    async def stop(self) -> None:
        """Stop the actor system."""
        if not self._running:
            return
            
        self._running = False
        
        # Stop persistence task
        if self._persistence_task:
            self._persistence_task.cancel()
            try:
                await self._persistence_task
            except asyncio.CancelledError:
                pass
            
        # Final persist of all actors
        for actor_id, actor in list(self._actors.items()):
            if isinstance(actor, PersistableActor):
                await actor.persist_state(force=True)
                
        # Stop processor task
        if self._processor_task:
            await self._message_queue.put((None, None, None, None))  # Sentinel to stop processor
            await self._processor_task
            self._processor_task = None
            
        logger.info(f"Stopped ActorSystem '{self.name}'")
        
    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._running:
            actor_id, message, sender, message_id = await self._message_queue.get()
            
            # Check for stop sentinel
            if actor_id is None and message is None:
                break
                
            # Get the target actor
            actor = self._actors.get(actor_id)
            if not actor:
                logger.warning(f"Message sent to non-existent actor: {actor_id}")
                if message_id and message_id in self._response_futures:
                    self._response_futures[message_id].set_exception(
                        ValueError(f"Actor not found: {actor_id}")
                    )
                    del self._response_futures[message_id]
                continue
                
            # Process the message
            try:
                start_time = time.time()
                actor._metrics["message_count"] += 1
                actor._metrics["last_message_time"] = start_time
                
                result = await actor.receive(message, sender)
                
                processing_time = time.time() - start_time
                actor._metrics["total_processing_time"] += processing_time
                actor._metrics["max_processing_time"] = max(
                    actor._metrics["max_processing_time"], processing_time
                )
                
                # If this is a persistable actor, mark it as dirty after processing a message
                if isinstance(actor, PersistableActor):
                    actor.mark_dirty()
                
                # If this was an ask, set the result in the future
                if message_id and message_id in self._response_futures:
                    self._response_futures[message_id].set_result(result)
                    del self._response_futures[message_id]
                    
            except Exception as e:
                actor._metrics["error_count"] += 1
                logger.exception(f"Error in actor {actor_id} processing message {message}")
                
                # If this was an ask, set the exception in the future
                if message_id and message_id in self._response_futures:
                    self._response_futures[message_id].set_exception(e)
                    del self._response_futures[message_id]

# Singleton actor system
_default_system = None

def get_actor_system(name: str = "default") -> ActorSystem:
    """Get or create the default actor system."""
    global _default_system
    if not _default_system:
        _default_system = ActorSystem(name)
    return _default_system
