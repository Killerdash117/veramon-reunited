"""
Performance Monitoring System for Veramon Reunited
© 2025 killerdash117 | https://github.com/killerdash117

This module provides utilities for tracking, analyzing, and optimizing
performance across the bot's systems.
"""

import time
import asyncio
import psutil
import threading
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict, deque

# Set up logging
logger = logging.getLogger("performance")

class PerformanceMonitor:
    """
    Tracks and analyzes performance metrics across the bot's systems.
    
    This class provides methods to:
    - Track command execution times
    - Monitor database query performance
    - Measure memory and CPU usage
    - Identify performance bottlenecks
    - Optimize high-traffic operations
    """
    
    def __init__(self):
        self.command_timings = defaultdict(lambda: {"total_time": 0, "count": 0, "avg_time": 0})
        self.query_timings = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.active_connections = 0
        self.max_connections = 0
        
        # Performance thresholds
        self.slow_command_threshold = 500  # ms
        self.slow_query_threshold = 100    # ms
        self.high_memory_threshold = 80    # percent
        self.high_cpu_threshold = 70       # percent
        
        # Recent samples (for rolling statistics)
        self.recent_queries = deque(maxlen=100)
        self.recent_commands = deque(maxlen=50)
        
        # Detailed monitoring data
        self.detailed_monitoring = False
        self.detailed_data = {
            "command_usage": {},
            "db_queries": [],
            "cpu_samples": [],
            "memory_samples": [],
            "latency_samples": []
        }
        
        # Start background monitoring thread for system resources
        self.monitoring_thread = None
        self.monitoring_active = False
        
    def record_command_execution(self, command_name: str, execution_time: float):
        """
        Record the execution time of a command.
        
        Args:
            command_name: Name of the command
            execution_time: Execution time in milliseconds
        """
        self.command_timings[command_name]["total_time"] += execution_time
        self.command_timings[command_name]["count"] += 1
        self.command_timings[command_name]["avg_time"] = (
            self.command_timings[command_name]["total_time"] / 
            self.command_timings[command_name]["count"]
        )
        
        # Add to recent commands
        self.recent_commands.append({
            "command": command_name,
            "time": execution_time,
            "timestamp": datetime.now()
        })
        
        # Add to detailed monitoring if active
        if self.detailed_monitoring:
            if command_name not in self.detailed_data["command_usage"]:
                self.detailed_data["command_usage"][command_name] = {
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "timestamps": []
                }
                
            self.detailed_data["command_usage"][command_name]["count"] += 1
            self.detailed_data["command_usage"][command_name]["total_time"] += execution_time
            self.detailed_data["command_usage"][command_name]["avg_time"] = (
                self.detailed_data["command_usage"][command_name]["total_time"] / 
                self.detailed_data["command_usage"][command_name]["count"]
            )
            self.detailed_data["command_usage"][command_name]["timestamps"].append(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
        # Log if it's a slow command
        if execution_time > self.slow_command_threshold:
            logger.warning(f"Slow command execution: {command_name} took {execution_time:.2f}ms")
    
    def record_query_execution(self, query: str, execution_time: float):
        """
        Record the execution time of a database query.
        
        Args:
            query: SQL query string
            execution_time: Execution time in milliseconds
        """
        # Store query timing
        query_entry = {
            "query": query,
            "duration": execution_time,
            "timestamp": datetime.now()
        }
        self.query_timings.append(query_entry)
        self.recent_queries.append(query_entry)
        
        # Add to detailed monitoring if active
        if self.detailed_monitoring:
            self.detailed_data["db_queries"].append(query_entry)
            
        # Log if it's a slow query
        if execution_time > self.slow_query_threshold:
            logger.warning(f"Slow query execution: {query} took {execution_time:.2f}ms")
            # Truncate query for logging if too long
            log_query = query if len(query) <= 100 else query[:97] + "..."
            logger.warning(f"Slow query: {log_query} - {execution_time:.2f}ms")
    
    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses += 1
    
    def record_connection_open(self):
        """Record a database connection being opened."""
        self.active_connections += 1
        self.max_connections = max(self.max_connections, self.active_connections)
    
    def record_connection_close(self):
        """Record a database connection being closed."""
        self.active_connections = max(0, self.active_connections - 1)
    
    def get_average_query_time(self):
        """Get the average query execution time in milliseconds."""
        if not self.query_timings:
            return 0
        
        # Average of recent queries
        recent_durations = [q["duration"] for q in self.recent_queries]
        if not recent_durations:
            return 0
            
        return sum(recent_durations) / len(recent_durations)
    
    def get_average_command_time(self, command_name: Optional[str] = None):
        """
        Get the average command execution time in milliseconds.
        
        Args:
            command_name: Optional specific command to get stats for
            
        Returns:
            Average execution time
        """
        if command_name:
            if command_name in self.command_timings:
                return self.command_timings[command_name]["avg_time"]
            return 0
            
        # Average across all commands
        if not self.command_timings:
            return 0
            
        total_time = sum(stats["total_time"] for stats in self.command_timings.values())
        total_count = sum(stats["count"] for stats in self.command_timings.values())
        
        if total_count == 0:
            return 0
            
        return total_time / total_count
    
    def get_top_commands(self, limit: int = 5):
        """
        Get the top N commands by execution count.
        
        Args:
            limit: Number of commands to return
            
        Returns:
            List of (command_name, avg_time, count) tuples
        """
        sorted_commands = sorted(
            self.command_timings.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return [
            (cmd, stats["avg_time"], stats["count"]) 
            for cmd, stats in sorted_commands[:limit]
        ]
    
    def get_slowest_commands(self, limit: int = 5):
        """
        Get the slowest N commands by average execution time.
        
        Args:
            limit: Number of commands to return
            
        Returns:
            List of (command_name, avg_time, count) tuples
        """
        sorted_commands = sorted(
            self.command_timings.items(),
            key=lambda x: x[1]["avg_time"],
            reverse=True
        )
        
        return [
            (cmd, stats["avg_time"], stats["count"]) 
            for cmd, stats in sorted_commands[:limit]
        ]
    
    def get_cache_statistics(self):
        """
        Get cache hit/miss statistics.
        
        Returns:
            String with cache statistics
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return "No cache data available"
            
        hit_rate = (self.cache_hits / total) * 100
        return f"{self.cache_hits} hits, {self.cache_misses} misses ({hit_rate:.1f}% hit rate)"
    
    def get_active_connections(self):
        """Get the current number of active database connections."""
        return self.active_connections
    
    def identify_bottlenecks(self):
        """
        Identify potential performance bottlenecks.
        
        Returns:
            List of bottleneck descriptions
        """
        bottlenecks = []
        
        # Check command performance
        slow_commands = [(cmd, stats["avg_time"]) for cmd, stats in self.command_timings.items() 
                         if stats["avg_time"] > self.slow_command_threshold and stats["count"] > 5]
        
        if slow_commands:
            for cmd, avg_time in slow_commands:
                bottlenecks.append(f"Slow command: {cmd} ({avg_time:.1f}ms average)")
        
        # Check query performance
        slow_queries = [q for q in self.recent_queries if q["duration"] > self.slow_query_threshold]
        if len(slow_queries) > 5:  # If there are multiple slow queries
            bottlenecks.append(f"Database queries are slow (found {len(slow_queries)} slow queries)")
        
        # Check cache performance
        total_cache = self.cache_hits + self.cache_misses
        if total_cache > 100 and (self.cache_misses / total_cache) > 0.4:
            hit_rate = (self.cache_hits / total_cache) * 100
            bottlenecks.append(f"Low cache hit rate: {hit_rate:.1f}%")
        
        # Check system resources from detailed monitoring
        if self.detailed_data["cpu_samples"]:
            avg_cpu = sum(self.detailed_data["cpu_samples"]) / len(self.detailed_data["cpu_samples"])
            if avg_cpu > self.high_cpu_threshold:
                bottlenecks.append(f"High CPU usage: {avg_cpu:.1f}%")
                
        if self.detailed_data["memory_samples"]:
            avg_memory_percent = sum(self.detailed_data["memory_samples"]) / len(self.detailed_data["memory_samples"])
            if avg_memory_percent > self.high_memory_threshold:
                bottlenecks.append(f"High memory usage: {avg_memory_percent:.1f}%")
        
        return bottlenecks
    
    def start_detailed_monitoring(self):
        """Start detailed performance monitoring."""
        self.detailed_monitoring = True
        self.detailed_data = {
            "command_usage": {},
            "db_queries": [],
            "cpu_samples": [],
            "memory_samples": [],
            "latency_samples": []
        }
        
        # Start sampling system resources
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system_resources)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("Detailed performance monitoring started")
    
    def stop_detailed_monitoring(self):
        """
        Stop detailed performance monitoring.
        
        Returns:
            Dict of monitoring results
        """
        self.detailed_monitoring = False
        self.monitoring_active = False
        
        # Wait for monitoring thread to stop
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)
        
        logger.info("Detailed performance monitoring stopped")
        
        return self.detailed_data
    
    def _monitor_system_resources(self):
        """Background thread to monitor system resources."""
        process = psutil.Process()
        
        while self.monitoring_active:
            try:
                # CPU usage (percent)
                cpu_percent = process.cpu_percent(interval=1)
                self.detailed_data["cpu_samples"].append(cpu_percent)
                
                # Memory usage (bytes)
                memory_info = process.memory_info()
                self.detailed_data["memory_samples"].append(memory_info.rss)
                
                # Sleep between samples
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error monitoring system resources: {e}")
                break
    
    def optimize_query(self, query: str) -> str:
        """
        Suggest optimizations for a database query.
        
        Args:
            query: SQL query to optimize
            
        Returns:
            Optimized query or original query if no optimizations found
        """
        # This is a placeholder - real implementation would have more sophisticated
        # query optimization logic based on database schema and query patterns
        
        # Convert to lowercase for easier analysis
        query_lower = query.lower()
        
        optimized = query
        optimization_applied = False
        
        # Check for SELECT * without WHERE clause on large tables
        if "select *" in query_lower and "where" not in query_lower:
            # This could be inefficient
            # Suggest adding a WHERE clause or selecting specific columns
            logger.warning(f"Potentially inefficient query (SELECT * without WHERE): {query}")
        
        # Check for missing indexes (this would need knowledge of table schemas)
        if "where" in query_lower and "index" not in query_lower:
            # This might benefit from an index, depending on the columns
            pass
        
        # Check for LIKE with leading wildcard
        if "like '%" in query_lower:
            # Leading wildcard prevents index usage
            logger.warning(f"Query uses leading wildcard which prevents index usage: {query}")
        
        return optimized if optimization_applied else query
        
    def reset_statistics(self):
        """Reset all performance statistics."""
        self.command_timings = defaultdict(lambda: {"total_time": 0, "count": 0, "avg_time": 0})
        self.query_timings = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.recent_queries.clear()
        self.recent_commands.clear()
        
        logger.info("Performance statistics reset")
        
# Global instance for use throughout the codebase
_performance_monitor = None

def get_performance_monitor():
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

# Command timing decorator
def track_command_performance(func):
    """Decorator to track command execution time."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            command_name = func.__name__
            monitor = get_performance_monitor()
            monitor.record_command_execution(command_name, execution_time)
    return wrapper

# Query timing decorator
def track_query_performance(func):
    """Decorator to track database query execution time."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            # Extract query string from args (assumes query is first argument)
            query = args[0] if args else "Unknown query"
            monitor = get_performance_monitor()
            monitor.record_query_execution(query, execution_time)
    return wrapper
