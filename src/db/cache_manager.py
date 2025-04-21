"""
Cache Manager for Veramon Reunited
© 2025 killerdash117 | https://github.com/killerdash117

This module provides a caching system for frequently accessed database data,
reducing query load and improving performance.
"""

import time
import logging
import threading
import json
from typing import Dict, Any, Optional, List, Tuple, Callable, Set
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger("cache")

class CacheEntry:
    """Represents a single cached entry with metadata."""
    
    def __init__(self, key: str, value: Any, ttl: int = 300):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.ttl = ttl  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > (self.created_at + self.ttl)
    
    def access(self) -> Any:
        """Access this entry and return its value."""
        self.last_accessed = time.time()
        self.access_count += 1
        return self.value
    
    def update(self, value: Any, reset_ttl: bool = True) -> None:
        """Update the entry's value and optionally reset its TTL."""
        self.value = value
        if reset_ttl:
            self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count += 1

class LRUCache:
    """
    LRU (Least Recently Used) cache implementation.
    
    This cache has a maximum size and evicts the least recently used items
    when it reaches capacity.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Any:
        """
        Get an item from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found/expired
        """
        with self.lock:
            if key not in self.cache:
                return None
                
            entry = self.cache[key]
            
            # Check if expired
            if entry.is_expired():
                del self.cache[key]
                return None
                
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            # Return value
            return entry.access()
    
    def put(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Add or update an item in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds
        """
        with self.lock:
            if key in self.cache:
                # Update existing entry
                self.cache[key].update(value, reset_ttl=True)
                # Move to end (most recently used)
                self.cache.move_to_end(key)
            else:
                # Add new entry
                self.cache[key] = CacheEntry(key, value, ttl)
                
            # Check if over capacity
            if len(self.cache) > self.max_size:
                # Remove the first item (least recently used)
                self.cache.popitem(last=False)
    
    def invalidate(self, key: str) -> bool:
        """
        Remove an item from the cache.
        
        Args:
            key: The cache key to remove
            
        Returns:
            True if the key was removed, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Remove all items matching a pattern from the cache.
        
        Args:
            pattern: The pattern to match against cache keys
            
        Returns:
            Number of items removed
        """
        with self.lock:
            # Find keys matching the pattern
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            
            # Remove matching keys
            for key in keys_to_remove:
                del self.cache[key]
                
            return len(keys_to_remove)
    
    def clear(self) -> int:
        """
        Clear all items from the cache.
        
        Returns:
            Number of items removed
        """
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired items from the cache.
        
        Returns:
            Number of expired items removed
        """
        with self.lock:
            # Find expired keys
            now = time.time()
            keys_to_remove = [
                k for k, v in self.cache.items() 
                if now > (v.created_at + v.ttl)
            ]
            
            # Remove expired keys
            for key in keys_to_remove:
                del self.cache[key]
                
            return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            total_items = len(self.cache)
            expired_items = sum(1 for entry in self.cache.values() if entry.is_expired())
            
            # Calculate age statistics
            now = time.time()
            if total_items > 0:
                ages = [(now - entry.created_at) for entry in self.cache.values()]
                avg_age = sum(ages) / len(ages)
                max_age = max(ages) if ages else 0
            else:
                avg_age = 0
                max_age = 0
                
            # Calculate access statistics
            access_counts = [entry.access_count for entry in self.cache.values()]
            avg_accesses = sum(access_counts) / len(access_counts) if access_counts else 0
            max_accesses = max(access_counts) if access_counts else 0
            
            return {
                "total_items": total_items,
                "capacity": self.max_size,
                "utilization": total_items / self.max_size if self.max_size > 0 else 0,
                "expired_items": expired_items,
                "avg_age_seconds": avg_age,
                "max_age_seconds": max_age,
                "avg_accesses": avg_accesses,
                "max_accesses": max_accesses
            }

class QueryCache:
    """
    Specialized cache for database queries.
    
    This cache is designed specifically for caching database query results,
    with features for managing table dependencies and invalidation.
    """
    
    def __init__(self, max_size: int = 500, default_ttl: int = 300):
        self.cache = LRUCache(max_size)
        self.default_ttl = default_ttl
        self.table_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.stats = {
            "hits": 0,
            "misses": 0,
            "inserts": 0,
            "invalidations": 0
        }
    
    def get(self, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
        """
        Get a cached query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cached result or None if not found
        """
        # Create cache key
        key = self._make_key(query, params)
        
        # Try to get from cache
        result = self.cache.get(key)
        
        if result is not None:
            self.stats["hits"] += 1
            return result
            
        self.stats["misses"] += 1
        return None
    
    def put(self, query: str, params: Optional[Tuple], result: Any, 
            ttl: Optional[int] = None, tables: Optional[List[str]] = None) -> None:
        """
        Cache a query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            result: Query result to cache
            ttl: Time to live in seconds (optional)
            tables: List of tables this query depends on (optional)
        """
        # Create cache key
        key = self._make_key(query, params)
        
        # Use default TTL if not specified
        if ttl is None:
            ttl = self.default_ttl
            
        # Track table dependencies if provided
        if tables:
            for table in tables:
                self.table_dependencies[table].add(key)
        
        # Insert into cache
        self.cache.put(key, result, ttl)
        self.stats["inserts"] += 1
    
    def invalidate_table(self, table: str) -> int:
        """
        Invalidate all queries dependent on a specific table.
        
        Args:
            table: Table name
            
        Returns:
            Number of entries invalidated
        """
        # Get keys dependent on this table
        keys = self.table_dependencies.get(table, set())
        
        # Invalidate each key
        count = 0
        for key in keys:
            if self.cache.invalidate(key):
                count += 1
                
        # Clear dependencies
        if table in self.table_dependencies:
            self.table_dependencies[table].clear()
            
        self.stats["invalidations"] += count
        return count
    
    def invalidate_tables(self, tables: List[str]) -> int:
        """
        Invalidate all queries dependent on any of the specified tables.
        
        Args:
            tables: List of table names
            
        Returns:
            Number of entries invalidated
        """
        count = 0
        for table in tables:
            count += self.invalidate_table(table)
        return count
    
    def invalidate_all(self) -> int:
        """
        Invalidate all cached queries.
        
        Returns:
            Number of entries invalidated
        """
        count = self.cache.clear()
        self.table_dependencies.clear()
        self.stats["invalidations"] += count
        return count
    
    def cleanup(self) -> int:
        """
        Remove expired entries and update dependencies.
        
        Returns:
            Number of entries removed
        """
        return self.cache.cleanup_expired()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        cache_stats = self.cache.get_stats()
        
        # Calculate hit rate
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **cache_stats,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "inserts": self.stats["inserts"],
            "invalidations": self.stats["invalidations"],
            "table_dependencies": {
                table: len(keys) for table, keys in self.table_dependencies.items()
            }
        }
    
    def _make_key(self, query: str, params: Optional[Tuple]) -> str:
        """
        Create a cache key from a query and parameters.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cache key string
        """
        # Normalize query by removing whitespace
        normalized_query = " ".join(query.split())
        
        # Create key with query and parameters
        if params:
            param_str = json.dumps(params, sort_keys=True)
            return f"{normalized_query}:{param_str}"
        else:
            return normalized_query


class CacheManager:
    """
    Central manager for all caching in the application.
    
    This class provides a unified interface for working with different types
    of caches and handles cache maintenance.
    """
    
    def __init__(self):
        # Initialize caches
        self.query_cache = QueryCache(max_size=500, default_ttl=300)  # 5 minutes TTL
        self.object_cache = LRUCache(max_size=1000)  # For general objects
        self.user_cache = LRUCache(max_size=200)     # For user data
        self.veramon_cache = LRUCache(max_size=300)  # For Veramon data
        
        # Start maintenance task
        self.maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True
        )
        self.maintenance_thread.start()
        
        logger.info("Cache manager initialized")
    
    def get_query_result(self, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
        """
        Get a cached query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cached result or None if not found
        """
        return self.query_cache.get(query, params)
    
    def cache_query_result(self, query: str, params: Optional[Tuple], result: Any,
                          ttl: Optional[int] = None, tables: Optional[List[str]] = None) -> None:
        """
        Cache a query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            result: Query result to cache
            ttl: Time to live in seconds (optional)
            tables: List of tables this query depends on (optional)
        """
        self.query_cache.put(query, params, result, ttl, tables)
    
    def invalidate_tables(self, tables: List[str]) -> None:
        """
        Invalidate all queries dependent on the specified tables.
        
        Args:
            tables: List of table names
        """
        self.query_cache.invalidate_tables(tables)
    
    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached user data.
        
        Args:
            user_id: User ID
            
        Returns:
            Cached user data or None if not found
        """
        return self.user_cache.get(f"user:{user_id}")
    
    def cache_user_data(self, user_id: str, data: Dict[str, Any], ttl: int = 600) -> None:
        """
        Cache user data.
        
        Args:
            user_id: User ID
            data: User data to cache
            ttl: Time to live in seconds (default: 10 minutes)
        """
        self.user_cache.put(f"user:{user_id}", data, ttl)
    
    def invalidate_user_data(self, user_id: str) -> None:
        """
        Invalidate cached user data.
        
        Args:
            user_id: User ID
        """
        self.user_cache.invalidate(f"user:{user_id}")
    
    def get_veramon_data(self, veramon_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached Veramon data.
        
        Args:
            veramon_id: Veramon ID
            
        Returns:
            Cached Veramon data or None if not found
        """
        return self.veramon_cache.get(f"veramon:{veramon_id}")
    
    def cache_veramon_data(self, veramon_id: str, data: Dict[str, Any], ttl: int = 900) -> None:
        """
        Cache Veramon data.
        
        Args:
            veramon_id: Veramon ID
            data: Veramon data to cache
            ttl: Time to live in seconds (default: 15 minutes)
        """
        self.veramon_cache.put(f"veramon:{veramon_id}", data, ttl)
    
    def invalidate_veramon_data(self, veramon_id: str) -> None:
        """
        Invalidate cached Veramon data.
        
        Args:
            veramon_id: Veramon ID
        """
        self.veramon_cache.invalidate(f"veramon:{veramon_id}")
    
    def get_object(self, key: str) -> Optional[Any]:
        """
        Get a cached object.
        
        Args:
            key: Cache key
            
        Returns:
            Cached object or None if not found
        """
        return self.object_cache.get(key)
    
    def cache_object(self, key: str, obj: Any, ttl: int = 300) -> None:
        """
        Cache an object.
        
        Args:
            key: Cache key
            obj: Object to cache
            ttl: Time to live in seconds (default: 5 minutes)
        """
        self.object_cache.put(key, obj, ttl)
    
    def invalidate_object(self, key: str) -> None:
        """
        Invalidate a cached object.
        
        Args:
            key: Cache key
        """
        self.object_cache.invalidate(key)
    
    def invalidate_pattern(self, pattern: str) -> None:
        """
        Invalidate all objects with keys matching a pattern.
        
        Args:
            pattern: Pattern to match against cache keys
        """
        self.object_cache.invalidate_pattern(pattern)
    
    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.query_cache.invalidate_all()
        self.object_cache.clear()
        self.user_cache.clear()
        self.veramon_cache.clear()
        logger.info("All caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all caches.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "query_cache": self.query_cache.get_stats(),
            "object_cache": self.object_cache.get_stats(),
            "user_cache": self.user_cache.get_stats(),
            "veramon_cache": self.veramon_cache.get_stats()
        }
    
    def _maintenance_loop(self) -> None:
        """Background thread for cache maintenance."""
        while True:
            try:
                # Clean up expired entries
                self.query_cache.cleanup()
                self.object_cache.cleanup_expired()
                self.user_cache.cleanup_expired()
                self.veramon_cache.cleanup_expired()
                
                # Log statistics every hour
                if datetime.now().minute == 0:
                    stats = self.get_cache_stats()
                    logger.info(f"Cache stats: {stats}")
                    
                # Sleep for 5 minutes
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in cache maintenance: {e}")
                # Sleep for 1 minute on error
                time.sleep(60)

# Global instance
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.
    
    Returns:
        The global CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
