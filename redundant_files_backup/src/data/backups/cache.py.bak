import time
import threading
import json
from typing import Dict, Any, Optional, Callable, List, Tuple, Union
from functools import wraps
import logging

logger = logging.getLogger('veramon.cache')

class Cache:
    """
    A thread-safe cache system with TTL (time-to-live) for frequently accessed data.
    Supports automatic invalidation and lazy loading.
    """
    
    def __init__(self):
        self._cache = {}
        self._locks = {}
        self._global_lock = threading.RLock()
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            default: Default value to return if key is not in cache
            
        Returns:
            The cached value or default if not found
        """
        with self._global_lock:
            # Check if key exists and is not expired
            if key in self._cache:
                entry = self._cache[key]
                if entry['expires'] > time.time() or entry['expires'] == 0:
                    logger.debug(f"Cache hit: {key}")
                    return entry['value']
                else:
                    # Key is expired
                    del self._cache[key]
                    
            logger.debug(f"Cache miss: {key}")
            return default
            
    def set(self, key: str, value: Any, ttl: int = 600) -> None:
        """
        Set a value in the cache with a TTL.
        
        Args:
            key: The cache key
            value: Value to cache
            ttl: Time to live in seconds (0 for no expiration)
        """
        with self._global_lock:
            expires = time.time() + ttl if ttl > 0 else 0
            self._cache[key] = {
                'value': value,
                'expires': expires
            }
            logger.debug(f"Cache set: {key}, TTL: {ttl}s")
            
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: The cache key to delete
            
        Returns:
            True if key was deleted, False if it didn't exist
        """
        with self._global_lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache delete: {key}")
                return True
            return False
            
    def clear(self) -> None:
        """Clear all cached data."""
        with self._global_lock:
            self._cache.clear()
            logger.debug("Cache cleared")
            
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys that match a pattern.
        
        Args:
            pattern: String pattern to match against keys
            
        Returns:
            Number of keys invalidated
        """
        count = 0
        with self._global_lock:
            keys_to_delete = [k for k in self._cache if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
                
        logger.debug(f"Cache invalidated {count} keys matching pattern: {pattern}")
        return count
        
    def get_or_set(self, key: str, value_func: Callable[[], Any], ttl: int = 600) -> Any:
        """
        Get a value from the cache or set it if not present.
        
        Args:
            key: The cache key
            value_func: Function to call to get the value if not in cache
            ttl: Time to live in seconds
            
        Returns:
            The cached or newly computed value
        """
        # Try to get from cache first
        value = self.get(key)
        if value is not None:
            return value
            
        # Get a lock for this key to prevent multiple computations
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
                
        # Use the key-specific lock
        with self._locks[key]:
            # Check again in case another thread set the value while we were waiting
            value = self.get(key)
            if value is not None:
                return value
                
            # Compute the value
            value = value_func()
            self.set(key, value, ttl)
            return value
            
    def stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._global_lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() 
                               if entry['expires'] > 0 and entry['expires'] <= time.time())
            active_entries = total_entries - expired_entries
            
            # Categorize by expiration time
            expiration_groups = {
                'no_expiry': 0,      # Never expires
                'short_term': 0,     # < 5 minutes
                'medium_term': 0,    # 5-30 minutes
                'long_term': 0       # > 30 minutes
            }
            
            now = time.time()
            for entry in self._cache.values():
                if entry['expires'] == 0:
                    expiration_groups['no_expiry'] += 1
                elif entry['expires'] <= now:
                    pass  # Already expired, not counted
                elif entry['expires'] - now < 300:  # 5 minutes
                    expiration_groups['short_term'] += 1
                elif entry['expires'] - now < 1800:  # 30 minutes
                    expiration_groups['medium_term'] += 1
                else:
                    expiration_groups['long_term'] += 1
                    
            return {
                'total_entries': total_entries,
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'expiration_groups': expiration_groups
            }

# Create a global cache instance
cache = Cache()

def cached(key_prefix: str, ttl: int = 600, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for the cache key
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from function arguments
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate the cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key generation from arguments
                arg_str = ','.join([str(arg) for arg in args])
                kwarg_str = ','.join([f"{k}={v}" for k, v in sorted(kwargs.items())])
                key = f"{key_prefix}:{func.__name__}:{arg_str}:{kwarg_str}"
                
            # Get from cache or compute
            return cache.get_or_set(key, lambda: func(*args, **kwargs), ttl)
            
        return wrapper
    return decorator

def invalidate_cache(pattern: str):
    """
    Decorator to invalidate cache entries matching a pattern after a function call.
    
    Args:
        pattern: Pattern to match for invalidation
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cache.invalidate_pattern(pattern)
            return result
        return wrapper
    return decorator

# Common cached data - predefined wrappers for frequently accessed data

def get_veramon_data(veramon_name: str = None) -> Dict[str, Any]:
    """
    Get Veramon data from the cache or load it from the data file.
    
    Args:
        veramon_name: Optional specific Veramon to get data for
        
    Returns:
        Dict with Veramon data
    """
    def load_veramon_data():
        import os
        import json
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        
        # First try the consolidated file
        complete_data_path = os.path.join(data_dir, "veramon_database.json")
        if os.path.exists(complete_data_path):
            try:
                with open(complete_data_path, 'r') as f:
                    return json.load(f)
            except Exception:
                # Fallback to original file if error occurs
                pass
        
        # Fallback to original file
        original_data_path = os.path.join(data_dir, "veramon_data.json")
        with open(original_data_path, 'r') as f:
            return json.load(f)
            
    all_data = cache.get_or_set("veramon:all", load_veramon_data, ttl=3600)  # Cache for 1 hour
    
    if veramon_name:
        return all_data.get(veramon_name, {})
    return all_data

def get_user_veramon(user_id: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Get a user's Veramon from cache or database.
    
    Args:
        user_id: The user ID to get Veramon for
        force_refresh: Force a refresh from the database
        
    Returns:
        List of user's Veramon data
    """
    cache_key = f"user:{user_id}:veramon"
    
    if force_refresh:
        cache.delete(cache_key)
        
    def load_user_veramon():
        from src.db.db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.veramon_name, c.nickname, c.level, c.experience, c.shiny,
                   c.active, c.caught_at, c.biome
            FROM captures c
            WHERE c.user_id = ?
            ORDER BY c.level DESC, c.id ASC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        veramon_list = []
        for row in results:
            veramon_list.append(dict(row))
            
        return veramon_list
        
    return cache.get_or_set(cache_key, load_user_veramon, ttl=300)  # Cache for 5 minutes

def get_active_battles(user_id: str = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Get active battles from cache or database.
    
    Args:
        user_id: Optional user ID to filter battles for
        force_refresh: Force a refresh from the database
        
    Returns:
        List of active battle data
    """
    cache_key = f"battles:active:{user_id}" if user_id else "battles:active"
    
    if force_refresh:
        cache.delete(cache_key)
        
    def load_active_battles():
        from src.db.db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT b.id, b.battle_type, b.status, b.start_time, b.current_turn,
                       bp.user_id
                FROM battles b
                JOIN battle_participants bp ON b.id = bp.battle_id
                WHERE b.status = 'active' AND bp.user_id = ?
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT b.id, b.battle_type, b.status, b.start_time, b.current_turn
                FROM battles b
                WHERE b.status = 'active'
            """)
            
        results = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        battle_list = []
        for row in results:
            battle_list.append(dict(row))
            
        return battle_list
        
    return cache.get_or_set(cache_key, load_active_battles, ttl=60)  # Cache for 1 minute

def get_active_trades(user_id: str = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Get active trades from cache or database.
    
    Args:
        user_id: Optional user ID to filter trades for
        force_refresh: Force a refresh from the database
        
    Returns:
        List of active trade data
    """
    cache_key = f"trades:active:{user_id}" if user_id else "trades:active"
    
    if force_refresh:
        cache.delete(cache_key)
        
    def load_active_trades():
        from src.db.db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT t.id, t.initiator_id, t.recipient_id, t.status, t.created_at,
                       i.username AS initiator_name, r.username AS recipient_name
                FROM trades t
                LEFT JOIN users i ON t.initiator_id = i.user_id
                LEFT JOIN users r ON t.recipient_id = r.user_id
                WHERE t.status = 'pending' AND (t.initiator_id = ? OR t.recipient_id = ?)
            """, (user_id, user_id))
        else:
            cursor.execute("""
                SELECT t.id, t.initiator_id, t.recipient_id, t.status, t.created_at,
                       i.username AS initiator_name, r.username AS recipient_name
                FROM trades t
                LEFT JOIN users i ON t.initiator_id = i.user_id
                LEFT JOIN users r ON t.recipient_id = r.user_id
                WHERE t.status = 'pending'
            """)
            
        results = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        trade_list = []
        for row in results:
            trade_list.append(dict(row))
            
        return trade_list
        
    return cache.get_or_set(cache_key, load_active_trades, ttl=60)  # Cache for 1 minute
