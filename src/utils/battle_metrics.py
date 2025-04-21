"""
Battle Metrics for Veramon Reunited
© 2025 killerdash117 | https://github.com/killerdash117

This module tracks and analyzes battle performance metrics, providing insights
into battle system efficiency and identifying bottlenecks.
"""

import time
import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict

from src.utils.performance_monitor import get_performance_monitor

# Set up logging
logger = logging.getLogger('battle_metrics')

class BattleMetrics:
    """
    Tracks performance metrics for the battle system.
    
    This class collects detailed metrics on battle operations and provides
    analysis to help identify performance bottlenecks.
    """
    
    def __init__(self):
        """Initialize the battle metrics tracker."""
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self.battle_durations: Dict[int, Dict[str, Any]] = {}
        self.move_calculation_times: List[float] = []
        self.status_effect_times: List[float] = []
        self.field_condition_times: List[float] = []
        self.battle_counts: Dict[str, int] = {
            'total': 0,
            'pvp': 0,
            'pve': 0,
            'multi': 0,
            'completed': 0,
            'cancelled': 0
        }
        self.metrics_lock = threading.RLock()
        
        # Get reference to performance monitor
        self.performance_monitor = get_performance_monitor()
        
    def record_battle_start(self, battle_id: int, battle_type: str) -> None:
        """
        Record the start of a battle.
        
        Args:
            battle_id: Unique ID for the battle
            battle_type: Type of battle (pvp, pve, multi)
        """
        with self.metrics_lock:
            self.battle_durations[battle_id] = {
                'start_time': time.time(),
                'battle_type': battle_type,
                'turns': 0,
                'moves_used': 0,
                'switches': 0,
                'items_used': 0,
                'status_effects_applied': 0,
                'field_conditions_applied': 0
            }
            
            # Increment battle type counter
            self.battle_counts['total'] += 1
            if battle_type in self.battle_counts:
                self.battle_counts[battle_type] += 1
    
    def record_battle_end(self, battle_id: int, outcome: str) -> None:
        """
        Record the end of a battle.
        
        Args:
            battle_id: Unique ID for the battle
            outcome: Battle outcome (completed or cancelled)
        """
        with self.metrics_lock:
            if battle_id not in self.battle_durations:
                return
                
            # Calculate duration
            start_time = self.battle_durations[battle_id]['start_time']
            duration = time.time() - start_time
            
            # Update metrics
            self.battle_durations[battle_id]['duration'] = duration
            self.battle_durations[battle_id]['end_time'] = time.time()
            self.battle_durations[battle_id]['outcome'] = outcome
            
            # Increment outcome counter
            if outcome in self.battle_counts:
                self.battle_counts[outcome] += 1
            
            # Record to performance monitor
            if self.performance_monitor:
                battle_type = self.battle_durations[battle_id]['battle_type']
                self.performance_monitor.record_custom_metric(
                    f"battle_duration_{battle_type}", 
                    duration
                )
    
    def record_turn(self, battle_id: int) -> None:
        """
        Record a turn in a battle.
        
        Args:
            battle_id: Unique ID for the battle
        """
        with self.metrics_lock:
            if battle_id in self.battle_durations:
                self.battle_durations[battle_id]['turns'] += 1
    
    def record_move_use(self, battle_id: int) -> None:
        """
        Record a move being used.
        
        Args:
            battle_id: Unique ID for the battle
        """
        with self.metrics_lock:
            if battle_id in self.battle_durations:
                self.battle_durations[battle_id]['moves_used'] += 1
    
    def record_switch(self, battle_id: int) -> None:
        """
        Record a Veramon switch.
        
        Args:
            battle_id: Unique ID for the battle
        """
        with self.metrics_lock:
            if battle_id in self.battle_durations:
                self.battle_durations[battle_id]['switches'] += 1
    
    def record_item_use(self, battle_id: int) -> None:
        """
        Record an item being used.
        
        Args:
            battle_id: Unique ID for the battle
        """
        with self.metrics_lock:
            if battle_id in self.battle_durations:
                self.battle_durations[battle_id]['items_used'] += 1
    
    def record_status_effect(self, battle_id: int) -> None:
        """
        Record a status effect being applied.
        
        Args:
            battle_id: Unique ID for the battle
        """
        with self.metrics_lock:
            if battle_id in self.battle_durations:
                self.battle_durations[battle_id]['status_effects_applied'] += 1
    
    def record_field_condition(self, battle_id: int) -> None:
        """
        Record a field condition being applied.
        
        Args:
            battle_id: Unique ID for the battle
        """
        with self.metrics_lock:
            if battle_id in self.battle_durations:
                self.battle_durations[battle_id]['field_conditions_applied'] += 1
    
    def record_operation_time(self, operation: str, duration: float) -> None:
        """
        Record the time taken for a battle operation.
        
        Args:
            operation: Name of the operation
            duration: Time taken in seconds
        """
        with self.metrics_lock:
            self.operation_times[operation].append(duration)
            
            # If we have too many samples, remove oldest ones
            if len(self.operation_times[operation]) > 1000:
                self.operation_times[operation] = self.operation_times[operation][-1000:]
    
    def record_move_calculation(self, duration: float) -> None:
        """
        Record the time taken to calculate a move result.
        
        Args:
            duration: Time taken in seconds
        """
        with self.metrics_lock:
            self.move_calculation_times.append(duration)
            
            # If we have too many samples, remove oldest ones
            if len(self.move_calculation_times) > 1000:
                self.move_calculation_times = self.move_calculation_times[-1000:]
            
            # Record to performance monitor
            if self.performance_monitor:
                self.performance_monitor.record_custom_metric("move_calculation", duration)
    
    def record_status_effect_processing(self, duration: float) -> None:
        """
        Record the time taken to process status effects.
        
        Args:
            duration: Time taken in seconds
        """
        with self.metrics_lock:
            self.status_effect_times.append(duration)
            
            # If we have too many samples, remove oldest ones
            if len(self.status_effect_times) > 1000:
                self.status_effect_times = self.status_effect_times[-1000:]
            
            # Record to performance monitor
            if self.performance_monitor:
                self.performance_monitor.record_custom_metric("status_effect_processing", duration)
    
    def record_field_condition_processing(self, duration: float) -> None:
        """
        Record the time taken to process field conditions.
        
        Args:
            duration: Time taken in seconds
        """
        with self.metrics_lock:
            self.field_condition_times.append(duration)
            
            # If we have too many samples, remove oldest ones
            if len(self.field_condition_times) > 1000:
                self.field_condition_times = self.field_condition_times[-1000:]
            
            # Record to performance monitor
            if self.performance_monitor:
                self.performance_monitor.record_custom_metric("field_condition_processing", duration)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of battle performance metrics.
        
        Returns:
            Dictionary with battle metrics summary
        """
        with self.metrics_lock:
            # Calculate operation time statistics
            operation_stats = {}
            for operation, times in self.operation_times.items():
                if times:
                    operation_stats[operation] = {
                        'count': len(times),
                        'average': sum(times) / len(times),
                        'min': min(times),
                        'max': max(times),
                        'total': sum(times)
                    }
            
            # Calculate move calculation statistics
            if self.move_calculation_times:
                move_calc_stats = {
                    'count': len(self.move_calculation_times),
                    'average': sum(self.move_calculation_times) / len(self.move_calculation_times),
                    'min': min(self.move_calculation_times),
                    'max': max(self.move_calculation_times),
                    'total': sum(self.move_calculation_times)
                }
            else:
                move_calc_stats = {'count': 0}
            
            # Calculate status effect statistics
            if self.status_effect_times:
                status_effect_stats = {
                    'count': len(self.status_effect_times),
                    'average': sum(self.status_effect_times) / len(self.status_effect_times),
                    'min': min(self.status_effect_times),
                    'max': max(self.status_effect_times),
                    'total': sum(self.status_effect_times)
                }
            else:
                status_effect_stats = {'count': 0}
            
            # Calculate field condition statistics
            if self.field_condition_times:
                field_condition_stats = {
                    'count': len(self.field_condition_times),
                    'average': sum(self.field_condition_times) / len(self.field_condition_times),
                    'min': min(self.field_condition_times),
                    'max': max(self.field_condition_times),
                    'total': sum(self.field_condition_times)
                }
            else:
                field_condition_stats = {'count': 0}
            
            # Calculate battle duration statistics
            completed_battles = [
                data for data in self.battle_durations.values() 
                if 'duration' in data
            ]
            
            if completed_battles:
                durations = [data['duration'] for data in completed_battles]
                turns = [data['turns'] for data in completed_battles]
                
                avg_duration = sum(durations) / len(durations)
                avg_turns = sum(turns) / len(turns)
                
                battle_stats = {
                    'count': len(completed_battles),
                    'average_duration': avg_duration,
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'average_turns': avg_turns,
                    'min_turns': min(turns),
                    'max_turns': max(turns),
                }
            else:
                battle_stats = {'count': 0}
            
            # Compile full summary
            return {
                'timestamp': datetime.now().isoformat(),
                'battle_counts': self.battle_counts.copy(),
                'battle_stats': battle_stats,
                'operation_stats': operation_stats,
                'move_calculation_stats': move_calc_stats,
                'status_effect_stats': status_effect_stats,
                'field_condition_stats': field_condition_stats
            }
    
    def get_recent_battles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get details of the most recent battles.
        
        Args:
            limit: Maximum number of battles to return
            
        Returns:
            List of recent battle data
        """
        with self.metrics_lock:
            # Get completed battles sorted by end time (most recent first)
            completed_battles = [
                {**data, 'battle_id': battle_id} 
                for battle_id, data in self.battle_durations.items() 
                if 'end_time' in data
            ]
            
            # Sort by end time (descending)
            completed_battles.sort(key=lambda x: x['end_time'], reverse=True)
            
            # Return limited number
            return completed_battles[:limit]
    
    def clear_metrics(self) -> None:
        """Clear all metrics data."""
        with self.metrics_lock:
            self.operation_times.clear()
            self.battle_durations.clear()
            self.move_calculation_times.clear()
            self.status_effect_times.clear()
            self.field_condition_times.clear()
            self.battle_counts = {
                'total': 0,
                'pvp': 0,
                'pve': 0,
                'multi': 0,
                'completed': 0,
                'cancelled': 0
            }
            
    def get_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Identify potential performance bottlenecks in the battle system.
        
        Returns:
            List of potential bottlenecks with severity and recommendations
        """
        bottlenecks = []
        with self.metrics_lock:
            # Check for slow move calculations
            if self.move_calculation_times and len(self.move_calculation_times) >= 10:
                avg_move_calc = sum(self.move_calculation_times) / len(self.move_calculation_times)
                if avg_move_calc > 0.05:  # More than 50ms
                    severity = "high" if avg_move_calc > 0.1 else "medium"
                    bottlenecks.append({
                        "component": "move_calculation",
                        "severity": severity,
                        "avg_time": avg_move_calc,
                        "recommendation": "Optimize move calculation logic and increase caching"
                    })
            
            # Check for slow status effect processing
            if self.status_effect_times and len(self.status_effect_times) >= 5:
                avg_status = sum(self.status_effect_times) / len(self.status_effect_times)
                if avg_status > 0.03:  # More than 30ms
                    severity = "high" if avg_status > 0.07 else "medium"
                    bottlenecks.append({
                        "component": "status_effects",
                        "severity": severity,
                        "avg_time": avg_status,
                        "recommendation": "Optimize status effect processing with batched updates"
                    })
            
            # Check for slow battle operations
            for operation, times in self.operation_times.items():
                if times and len(times) >= 5:
                    avg_time = sum(times) / len(times)
                    if avg_time > 0.1:  # More than 100ms
                        severity = "high" if avg_time > 0.2 else "medium"
                        bottlenecks.append({
                            "component": operation,
                            "severity": severity,
                            "avg_time": avg_time,
                            "recommendation": f"Optimize {operation} with improved algorithms and caching"
                        })
            
            # Check if battles take too many turns
            completed_battles = [
                data for data in self.battle_durations.values() 
                if 'duration' in data and 'turns' in data
            ]
            
            if completed_battles and len(completed_battles) >= 5:
                avg_turns = sum(data['turns'] for data in completed_battles) / len(completed_battles)
                if avg_turns > 15:  # More than 15 turns on average
                    severity = "medium" if avg_turns > 20 else "low"
                    bottlenecks.append({
                        "component": "battle_length",
                        "severity": severity,
                        "avg_turns": avg_turns,
                        "recommendation": "Balance battle mechanics to reduce average battle length"
                    })
        
        return bottlenecks

# Global instance
_battle_metrics = None

def get_battle_metrics() -> BattleMetrics:
    """
    Get the global battle metrics instance.
    
    Returns:
        The global BattleMetrics instance
    """
    global _battle_metrics
    if _battle_metrics is None:
        _battle_metrics = BattleMetrics()
    return _battle_metrics
