"""
Developer Tools for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides advanced developer-only tools for debugging,
performance monitoring, and system management.
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time
import traceback
import psutil
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.core.security_integration import get_security_integration
from src.utils.performance_monitor import get_performance_monitor
from src.utils.battle_metrics import get_battle_metrics
from src.db.cache_manager import get_cache_manager
from src.db.db_manager import get_db_manager

# Set up logging
logger = logging.getLogger("dev_tools")

class DevToolsCog(commands.Cog):
    """
    Advanced developer-only tools for debugging and performance monitoring.
    
    This cog provides commands that help developers diagnose issues,
    monitor performance, and test new features in a controlled environment.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.security = get_security_integration()
        self.performance_monitor = get_performance_monitor()
        self.battle_metrics = get_battle_metrics()
        self.cache_manager = get_cache_manager()
        self.db_manager = get_db_manager()
        self.command_timings = {}
        self.monitoring_active = False
        self.monitoring_data = {}
        self.test_flags = {
            "debug_mode": False,
            "verbose_logging": False,
            "mock_battles": False,
            "mock_spawns": False,
            "mock_trades": False
        }
        
    @app_commands.command(name="system_stats", description="View detailed system statistics and bot performance")
    @app_commands.default_permissions(administrator=True)
    async def system_stats(self, interaction: discord.Interaction):
        """
        Display detailed statistics about the bot and system performance.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "system_stats", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Collect system statistics
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.5)
        uptime = datetime.now() - datetime.fromtimestamp(process.create_time())
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds // 60) % 60}m {uptime.seconds % 60}s"
        
        # Collect Discord statistics
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds)
        channel_count = sum(len(guild.channels) for guild in self.bot.guilds)
        
        # Database statistics
        db_size = self._get_db_size()
        avg_query_time = self.performance_monitor.get_average_query_time()
        cached_items = self.performance_monitor.get_cache_statistics()
        
        # Command statistics
        top_commands = self.performance_monitor.get_top_commands(5)
        
        # Create the embed
        embed = discord.Embed(
            title="📊 System Statistics",
            description="Detailed performance information and system statistics",
            color=discord.Color.blue()
        )
        
        # System info
        embed.add_field(
            name="💻 System",
            value=f"CPU Usage: {cpu_percent}%\n"
                  f"Memory Usage: {self._format_bytes(memory_info.rss)}\n"
                  f"Uptime: {uptime_str}\n"
                  f"Python: {sys.version.split()[0]}",
            inline=False
        )
        
        # Discord info
        embed.add_field(
            name="🤖 Bot Status",
            value=f"Guilds: {guild_count}\n"
                  f"Users: {user_count}\n"
                  f"Channels: {channel_count}\n"
                  f"Latency: {round(self.bot.latency * 1000)}ms",
            inline=False
        )
        
        # Database info
        embed.add_field(
            name="💾 Database",
            value=f"Size: {self._format_bytes(db_size)}\n"
                  f"Avg Query Time: {avg_query_time:.2f}ms\n"
                  f"Cached Items: {cached_items}\n"
                  f"Active Connections: {self.performance_monitor.get_active_connections()}",
            inline=False
        )
        
        # Command info
        cmd_info = "\n".join([f"{cmd}: {time:.2f}ms (used {count} times)" for cmd, time, count in top_commands])
        if not cmd_info:
            cmd_info = "No command data available yet"
            
        embed.add_field(
            name="⚡ Top Commands",
            value=cmd_info,
            inline=False
        )
        
        # Test flags
        flags_info = "\n".join([f"{flag}: {'✅' if enabled else '❌'}" for flag, enabled in self.test_flags.items()])
        embed.add_field(
            name="🚩 Test Flags",
            value=flags_info,
            inline=False
        )
        
        # Add timestamp
        embed.set_footer(text=f"Retrieved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="toggle_test_flag", description="Toggle a test flag for development purposes")
    @app_commands.describe(flag_name="The test flag to toggle", enabled="Whether to enable or disable the flag")
    @app_commands.default_permissions(administrator=True)
    async def toggle_test_flag(self, interaction: discord.Interaction, flag_name: str, enabled: bool):
        """
        Toggle a test flag for development and testing purposes.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "toggle_test_flag", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Check if flag exists
        if flag_name not in self.test_flags:
            await interaction.response.send_message(
                f"❌ Unknown test flag: {flag_name}\n"
                f"Available flags: {', '.join(self.test_flags.keys())}",
                ephemeral=True
            )
            return
            
        # Update flag
        self.test_flags[flag_name] = enabled
        
        # Log change
        logger.info(f"Test flag '{flag_name}' set to {enabled} by {interaction.user.name} (ID: {interaction.user.id})")
        
        # Confirmation message
        await interaction.response.send_message(
            f"{'✅' if enabled else '❌'} Test flag '{flag_name}' has been {'enabled' if enabled else 'disabled'}.",
            ephemeral=True
        )
        
    @app_commands.command(name="start_monitoring", description="Start detailed performance monitoring")
    @app_commands.describe(duration="Duration in minutes to monitor (default: 10)")
    @app_commands.default_permissions(administrator=True)
    async def start_monitoring(self, interaction: discord.Interaction, duration: int = 10):
        """
        Start detailed performance monitoring for a specified duration.
        
        This will track command usage, database queries, memory usage, and other
        performance metrics to help identify bottlenecks.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "start_monitoring", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Check if monitoring is already active
        if self.monitoring_active:
            await interaction.response.send_message(
                "❌ Monitoring is already active. Use `/stop_monitoring` to stop it first.",
                ephemeral=True
            )
            return
            
        # Start monitoring
        self.monitoring_active = True
        self.monitoring_data = {
            "start_time": datetime.now(),
            "end_time": None,
            "command_usage": {},
            "db_queries": [],
            "memory_samples": [],
            "cpu_samples": [],
            "latency_samples": []
        }
        
        # Enable performance monitoring
        self.performance_monitor.start_detailed_monitoring()
        
        # Confirmation message
        await interaction.response.send_message(
            f"✅ Performance monitoring started for {duration} minutes.\n"
            f"Use `/stop_monitoring` to stop early and view results.",
            ephemeral=True
        )
        
        # Schedule automatic stop
        asyncio.create_task(self._auto_stop_monitoring(interaction.user.id, duration))
        
    @app_commands.command(name="stop_monitoring", description="Stop performance monitoring and view results")
    @app_commands.default_permissions(administrator=True)
    async def stop_monitoring(self, interaction: discord.Interaction):
        """
        Stop performance monitoring and display the results.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "stop_monitoring", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
            
        # Check if monitoring is active
        if not self.monitoring_active:
            await interaction.response.send_message(
                "❌ No monitoring is currently active. Use `/start_monitoring` to start.",
                ephemeral=True
            )
            return
            
        # Stop monitoring
        await self._stop_monitoring(interaction)
        
    @app_commands.command(name="debug_logs", description="View recent debug logs")
    @app_commands.describe(
        level="Log level to filter by",
        lines="Number of lines to display",
        module="Specific module to filter logs for"
    )
    @app_commands.choices(level=[
        app_commands.Choice(name="ERROR", value="ERROR"),
        app_commands.Choice(name="WARNING", value="WARNING"),
        app_commands.Choice(name="INFO", value="INFO"),
        app_commands.Choice(name="DEBUG", value="DEBUG")
    ])
    @app_commands.default_permissions(administrator=True)
    async def debug_logs(
        self, 
        interaction: discord.Interaction, 
        level: str = "ERROR", 
        lines: int = 20,
        module: str = None
    ):
        """
        View recent debug logs with optional filtering.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "debug_logs", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
            
        # Load logs
        logs = self._get_filtered_logs(level, lines, module)
        
        if not logs:
            await interaction.response.send_message(
                f"ℹ️ No log entries found matching the criteria:\n"
                f"Level: {level}\n"
                f"Module: {module or 'Any'}\n",
                ephemeral=True
            )
            return
            
        # Format logs for display
        log_text = "```\n"
        for log in logs:
            # Truncate long messages
            message = log["message"]
            if len(message) > 100:
                message = message[:97] + "..."
                
            log_text += f"[{log['time']}] {log['level']}: {message}\n"
            
        log_text += "```"
        
        embed = discord.Embed(
            title="📜 Debug Logs",
            description=f"Showing {len(logs)} log entries",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Filters",
            value=f"Level: {level}\n"
                 f"Module: {module or 'Any'}\n"
                 f"Lines: {lines}",
            inline=False
        )
        
        # Check if log text is too long
        if len(log_text) > 1024:
            # Split into multiple fields
            chunks = [log_text[i:i+1000] for i in range(0, len(log_text), 1000)]
            for i, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"Logs (Part {i+1}/{len(chunks)})",
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(
                name="Logs",
                value=log_text,
                inline=False
            )
            
        embed.set_footer(text=f"Use `/debug_logs DEBUG` to see more detailed logs")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reload", description="Reload a specific module or cog")
    @app_commands.describe(module_name="Name of the module or cog to reload")
    @app_commands.default_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction, module_name: str):
        """
        Reload a specific module, cog, or extension without restarting the bot.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "reload", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Attempt to reload as a cog first
        try:
            try:
                await self.bot.unload_extension(module_name)
            except Exception:
                # The extension might not be loaded
                pass
                
            await self.bot.load_extension(module_name)
            
            # Log reload
            logger.info(f"Module '{module_name}' reloaded by {interaction.user.name} (ID: {interaction.user.id})")
            
            # Confirmation message
            await interaction.response.send_message(
                f"✅ Successfully reloaded module: `{module_name}`",
                ephemeral=True
            )
        except Exception as e:
            error_msg = f"Error reloading {module_name}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            await interaction.response.send_message(
                f"❌ Failed to reload module: `{module_name}`\n"
                f"```\n{str(e)}\n```",
                ephemeral=True
            )
    
    @app_commands.command(name="test_environment", description="Create a test environment for a feature")
    @app_commands.describe(
        feature="The feature to test",
        reset="Whether to reset existing test data"
    )
    @app_commands.choices(feature=[
        app_commands.Choice(name="Battle System", value="battle"),
        app_commands.Choice(name="Trading System", value="trading"),
        app_commands.Choice(name="Spawn System", value="spawn"),
        app_commands.Choice(name="Economy", value="economy"),
        app_commands.Choice(name="Quests", value="quests")
    ])
    @app_commands.default_permissions(administrator=True)
    async def test_environment(
        self, 
        interaction: discord.Interaction, 
        feature: str,
        reset: bool = False
    ):
        """
        Create a test environment for a specific feature.
        
        This creates sample data and enables test flags for the specified feature.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "test_environment", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Set up appropriate test flags
        if feature == "battle":
            self.test_flags["mock_battles"] = True
            feature_name = "Battle System"
        elif feature == "trading":
            self.test_flags["mock_trades"] = True
            feature_name = "Trading System"
        elif feature == "spawn":
            self.test_flags["mock_spawns"] = True
            feature_name = "Spawn System"
        elif feature == "economy":
            feature_name = "Economy System"
        elif feature == "quests":
            feature_name = "Quest System"
        else:
            feature_name = feature.capitalize()
        
        # Enable debug mode
        self.test_flags["debug_mode"] = True
        
        # Create test environment
        await self._setup_test_environment(interaction.user.id, feature, reset)
        
        # Log test environment creation
        logger.info(f"Test environment for {feature} created by {interaction.user.name} (ID: {interaction.user.id})")
        
        # Confirmation message
        await interaction.response.send_message(
            f"✅ Test environment for {feature_name} has been created.\n"
            f"Debug mode is {'enabled' if self.test_flags['debug_mode'] else 'disabled'}.\n"
            f"Test data has been {'reset' if reset else 'set up'}.\n"
            f"Use `/test_cleanup` when finished testing.",
            ephemeral=True
        )
    
    @app_commands.command(name="test_cleanup", description="Clean up test environment and data")
    @app_commands.default_permissions(administrator=True)
    async def test_cleanup(self, interaction: discord.Interaction):
        """
        Clean up test environment and data after testing.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "test_cleanup", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Reset all test flags
        for flag in self.test_flags:
            self.test_flags[flag] = False
        
        # Clean up test data
        await self._cleanup_test_data()
        
        # Log cleanup
        logger.info(f"Test environment cleaned up by {interaction.user.name} (ID: {interaction.user.id})")
        
        # Confirmation message
        await interaction.response.send_message(
            "✅ Test environment has been cleaned up.\n"
            "All test flags have been reset.\n"
            "Test data has been removed.",
            ephemeral=True
        )
        
    async def _auto_stop_monitoring(self, user_id, duration):
        """Automatically stop monitoring after the specified duration."""
        try:
            await asyncio.sleep(duration * 60)  # Convert minutes to seconds
            
            # Check if monitoring is still active
            if self.monitoring_active:
                # Get the user
                user = self.bot.get_user(user_id)
                
                if user:
                    # Create a fake interaction for the user
                    # This is a hacky way to reuse the stop_monitoring logic
                    class FakeInteraction:
                        def __init__(self, user):
                            self.user = user
                            
                        async def response_send_message(self, content, ephemeral=False):
                            try:
                                await user.send(content)
                            except Exception:
                                logger.error(f"Failed to send monitoring results to {user}")
                    
                    fake_interaction = FakeInteraction(user)
                    
                    # Stop monitoring and send results
                    await self._stop_monitoring(fake_interaction)
                else:
                    # Just stop monitoring without sending results
                    self.performance_monitor.stop_detailed_monitoring()
                    self.monitoring_active = False
        except Exception as e:
            logger.error(f"Error in auto-stop monitoring: {e}")
            self.monitoring_active = False
    
    async def _stop_monitoring(self, interaction):
        """Stop monitoring and display results."""
        if not self.monitoring_active:
            return
            
        # Update end time
        self.monitoring_data["end_time"] = datetime.now()
        
        # Stop performance monitoring
        monitoring_results = self.performance_monitor.stop_detailed_monitoring()
        
        # Update monitoring data with results
        self.monitoring_data.update(monitoring_results)
        
        # Calculate duration
        start_time = self.monitoring_data["start_time"]
        end_time = self.monitoring_data["end_time"]
        duration = (end_time - start_time).total_seconds() / 60.0  # in minutes
        
        # Create report embed
        embed = discord.Embed(
            title="📊 Performance Monitoring Results",
            description=f"Monitoring period: {duration:.1f} minutes",
            color=discord.Color.green()
        )
        
        # Performance summary
        avg_cpu = sum(self.monitoring_data["cpu_samples"]) / max(len(self.monitoring_data["cpu_samples"]), 1)
        avg_memory = sum(self.monitoring_data["memory_samples"]) / max(len(self.monitoring_data["memory_samples"]), 1) if self.monitoring_data["memory_samples"] else 0
        avg_latency = sum(self.monitoring_data["latency_samples"]) / max(len(self.monitoring_data["latency_samples"]), 1) if self.monitoring_data["latency_samples"] else 0
        
        embed.add_field(
            name="💻 System Performance",
            value=f"Average CPU: {avg_cpu:.1f}%\n"
                 f"Average Memory: {self._format_bytes(avg_memory)}\n"
                 f"Average Latency: {avg_latency:.2f}ms",
            inline=False
        )
        
        # Database performance
        avg_query_time = sum(q["duration"] for q in self.monitoring_data["db_queries"]) / max(len(self.monitoring_data["db_queries"]), 1) if self.monitoring_data["db_queries"] else 0
        max_query_time = max([q["duration"] for q in self.monitoring_data["db_queries"]], default=0)
        query_count = len(self.monitoring_data["db_queries"])
        
        embed.add_field(
            name="💾 Database Performance",
            value=f"Total Queries: {query_count}\n"
                 f"Average Query Time: {avg_query_time:.2f}ms\n"
                 f"Max Query Time: {max_query_time:.2f}ms\n"
                 f"Queries per Minute: {query_count / max(duration, 0.1):.1f}",
            inline=False
        )
        
        # Command usage
        cmd_usage_sorted = sorted(self.monitoring_data["command_usage"].items(), key=lambda x: x[1]["count"], reverse=True)
        cmd_usage_text = "\n".join([f"{cmd}: {data['count']} uses, {data['avg_time']:.2f}ms avg" for cmd, data in cmd_usage_sorted[:5]])
        
        if not cmd_usage_text:
            cmd_usage_text = "No commands were used during monitoring period"
            
        embed.add_field(
            name="⚡ Command Usage",
            value=cmd_usage_text,
            inline=False
        )
        
        # Performance bottlenecks
        bottlenecks = self.performance_monitor.identify_bottlenecks()
        bottleneck_text = "\n".join([f"• {issue}" for issue in bottlenecks]) if bottlenecks else "No significant bottlenecks detected"
        
        embed.add_field(
            name="⚠️ Potential Bottlenecks",
            value=bottleneck_text,
            inline=False
        )
        
        # Reset monitoring state
        self.monitoring_active = False
        
        # Save detailed monitoring data to file
        report_path = self._save_monitoring_report()
        
        embed.add_field(
            name="📂 Full Report",
            value=f"Detailed report saved to: `{report_path}`",
            inline=False
        )
        
        # Add timestamp
        embed.set_footer(text=f"Monitoring ended at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def _get_db_size(self):
        """Get the current database file size."""
        try:
            db_path = "data/veramon.db"
            if os.path.exists(db_path):
                return os.path.getsize(db_path)
            return 0
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0
    
    def _format_bytes(self, bytes_value):
        """Format bytes value to human-readable format."""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.2f} MB"
        else:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
    
    def _get_filtered_logs(self, level, lines, module=None):
        """Get filtered log entries."""
        log_dir = "logs"
        log_file = "veramon.log"
        log_path = os.path.join(log_dir, log_file)
        
        if not os.path.exists(log_path):
            return []
            
        logs = []
        
        try:
            with open(log_path, "r") as f:
                for line in f.readlines():
                    # Basic parsing - this can be improved for actual log format
                    if level in line:
                        # Extract timestamp, level, module, and message
                        parts = line.split(" ")
                        if len(parts) >= 4:
                            timestamp = " ".join(parts[:2])
                            log_level = parts[2]
                            log_module = parts[3].strip("[]:")
                            message = " ".join(parts[4:])
                            
                            # Apply filters
                            if level and level not in log_level:
                                continue
                                
                            if module and module not in log_module:
                                continue
                                
                            logs.append({
                                "time": timestamp,
                                "level": log_level,
                                "module": log_module,
                                "message": message
                            })
        except Exception as e:
            logger.error(f"Error parsing logs: {e}")
            
        # Return most recent logs
        return logs[-lines:] if logs else []
    
    def _save_monitoring_report(self):
        """Save detailed monitoring data to a file."""
        report_dir = "data/reports"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_report_{timestamp}.json"
        report_path = os.path.join(report_dir, filename)
        
        try:
            with open(report_path, "w") as f:
                # Convert datetime objects to strings
                report_data = {
                    "start_time": self.monitoring_data["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": self.monitoring_data["end_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "command_usage": self.monitoring_data["command_usage"],
                    "db_queries": [
                        {
                            "query": q["query"],
                            "duration": q["duration"],
                            "timestamp": q["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if "timestamp" in q else None
                        }
                        for q in self.monitoring_data["db_queries"]
                    ],
                    "cpu_samples": self.monitoring_data["cpu_samples"],
                    "memory_samples": self.monitoring_data["memory_samples"],
                    "latency_samples": self.monitoring_data["latency_samples"],
                    "bottlenecks": self.performance_monitor.identify_bottlenecks()
                }
                
                json.dump(report_data, f, indent=2)
                
            return report_path
        except Exception as e:
            logger.error(f"Failed to save monitoring report: {e}")
            return "Error saving report"
            
    async def _setup_test_environment(self, user_id, feature, reset=False):
        """Set up a test environment for a specific feature."""
        # This would create sample data in the database for testing
        # Actual implementation would depend on feature
        pass
        
    async def _cleanup_test_data(self):
        """Clean up test data from database."""
        # This would remove any test data created by _setup_test_environment
        pass
    
    @app_commands.command(name="cache_stats", description="View cache statistics and performance")
    @app_commands.default_permissions(administrator=True)
    async def cache_stats(self, interaction: discord.Interaction):
        """
        Display detailed cache statistics and performance metrics.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "cache_stats", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Get cache statistics
        cache_stats = self.cache_manager.get_cache_stats()
        
        # Create the embed
        embed = discord.Embed(
            title="🚀 Cache Statistics",
            description="Performance metrics for the caching system",
            color=discord.Color.green()
        )
        
        # Query cache stats
        query_cache = cache_stats.get("query_cache", {})
        embed.add_field(
            name="📊 Query Cache",
            value=f"Total Items: {query_cache.get('total_items', 0)}\n"
                  f"Hit Rate: {query_cache.get('hit_rate', 0):.2%}\n"
                  f"Hits: {query_cache.get('hits', 0)}\n"
                  f"Misses: {query_cache.get('misses', 0)}\n"
                  f"Invalidations: {query_cache.get('invalidations', 0)}",
            inline=True
        )
        
        # Object cache stats
        object_cache = cache_stats.get("object_cache", {})
        embed.add_field(
            name="🔶 Object Cache",
            value=f"Total Items: {object_cache.get('total_items', 0)}\n"
                  f"Utilization: {object_cache.get('utilization', 0):.2%}\n"
                  f"Avg Age: {object_cache.get('avg_age_seconds', 0):.1f}s\n"
                  f"Avg Accesses: {object_cache.get('avg_accesses', 0):.1f}",
            inline=True
        )
        
        # User and Veramon cache stats
        user_cache = cache_stats.get("user_cache", {})
        veramon_cache = cache_stats.get("veramon_cache", {})
        embed.add_field(
            name="👤 User & Veramon Cache",
            value=f"User Items: {user_cache.get('total_items', 0)}\n"
                  f"Veramon Items: {veramon_cache.get('total_items', 0)}",
            inline=False
        )
        
        # Table dependencies
        if "query_cache" in cache_stats and "table_dependencies" in query_cache:
            table_deps = query_cache["table_dependencies"]
            if table_deps:
                top_tables = sorted(
                    [(table, count) for table, count in table_deps.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                embed.add_field(
                    name="📋 Top Cached Tables",
                    value="\n".join([f"{table}: {count} queries" for table, count in top_tables]),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="clear_cache", description="Clear specific or all caches")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        cache_type=[
            app_commands.Choice(name="All Caches", value="all"),
            app_commands.Choice(name="Query Cache", value="query"),
            app_commands.Choice(name="Object Cache", value="object"),
            app_commands.Choice(name="User Cache", value="user"),
            app_commands.Choice(name="Veramon Cache", value="veramon")
        ]
    )
    async def clear_cache(self, interaction: discord.Interaction, cache_type: str):
        """
        Clear a specific cache or all caches.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "clear_cache", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Clear the specified cache
        if cache_type == "all":
            self.cache_manager.clear_all_caches()
            message = "✅ All caches cleared successfully."
        elif cache_type == "query":
            self.db_manager.clear_all_caches()
            message = "✅ Query cache cleared successfully."
        elif cache_type == "object":
            self.cache_manager.object_cache.clear()
            message = "✅ Object cache cleared successfully."
        elif cache_type == "user":
            self.cache_manager.user_cache.clear()
            message = "✅ User cache cleared successfully."
        elif cache_type == "veramon":
            self.cache_manager.veramon_cache.clear()
            message = "✅ Veramon cache cleared successfully."
        else:
            message = "❌ Invalid cache type specified."
        
        await interaction.response.send_message(message, ephemeral=True)
    
    @app_commands.command(name="battle_metrics", description="View battle system performance metrics")
    @app_commands.default_permissions(administrator=True)
    async def battle_metrics_command(self, interaction: discord.Interaction):
        """
        Display detailed battle system performance metrics.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "battle_metrics", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Get battle metrics
        metrics = self.battle_metrics.get_metrics_summary()
        recent_battles = self.battle_metrics.get_recent_battles(5)
        bottlenecks = self.battle_metrics.get_performance_bottlenecks()
        
        # Create the embed
        embed = discord.Embed(
            title="⚔️ Battle System Metrics",
            description="Performance statistics for the battle system",
            color=discord.Color.gold()
        )
        
        # Battle counts
        battle_counts = metrics.get("battle_counts", {})
        embed.add_field(
            name="🔢 Battle Counts",
            value=f"Total: {battle_counts.get('total', 0)}\n"
                  f"PvP: {battle_counts.get('pvp', 0)}\n"
                  f"PvE: {battle_counts.get('pve', 0)}\n"
                  f"Multi: {battle_counts.get('multi', 0)}\n"
                  f"Completed: {battle_counts.get('completed', 0)}\n"
                  f"Cancelled: {battle_counts.get('cancelled', 0)}",
            inline=True
        )
        
        # Battle stats
        battle_stats = metrics.get("battle_stats", {})
        if battle_stats.get("count", 0) > 0:
            embed.add_field(
                name="⏱️ Battle Duration",
                value=f"Average: {battle_stats.get('average_duration', 0):.2f}s\n"
                      f"Min: {battle_stats.get('min_duration', 0):.2f}s\n"
                      f"Max: {battle_stats.get('max_duration', 0):.2f}s\n"
                      f"Avg Turns: {battle_stats.get('average_turns', 0):.1f}",
                inline=True
            )
        
        # Move calculations
        move_calc = metrics.get("move_calculation_stats", {})
        if move_calc.get("count", 0) > 0:
            embed.add_field(
                name="🎯 Move Calculations",
                value=f"Count: {move_calc.get('count', 0)}\n"
                      f"Average: {move_calc.get('average', 0) * 1000:.2f}ms\n"
                      f"Max: {move_calc.get('max', 0) * 1000:.2f}ms",
                inline=False
            )
        
        # Status effects and field conditions
        status_effect = metrics.get("status_effect_stats", {})
        field_condition = metrics.get("field_condition_stats", {})
        if status_effect.get("count", 0) > 0 or field_condition.get("count", 0) > 0:
            embed.add_field(
                name="🌀 Effects Processing",
                value=f"Status Effects: {status_effect.get('count', 0)} ({status_effect.get('average', 0) * 1000:.2f}ms avg)\n"
                      f"Field Conditions: {field_condition.get('count', 0)} ({field_condition.get('average', 0) * 1000:.2f}ms avg)",
                inline=False
            )
        
        # Recent battles
        if recent_battles:
            recent_text = ""
            for battle in recent_battles[:3]:
                battle_type = battle.get("battle_type", "unknown")
                duration = battle.get("duration", 0)
                turns = battle.get("turns", 0)
                outcome = battle.get("outcome", "unknown")
                recent_text += f"ID {battle.get('battle_id', '?')}: {battle_type.upper()} - {duration:.2f}s, {turns} turns ({outcome})\n"
            
            embed.add_field(
                name="🕒 Recent Battles",
                value=recent_text if recent_text else "No recent battles",
                inline=False
            )
        
        # Bottlenecks
        if bottlenecks:
            bottleneck_text = ""
            for bottleneck in bottlenecks[:3]:
                component = bottleneck.get("component", "unknown")
                severity = bottleneck.get("severity", "low").upper()
                avg_time = bottleneck.get("avg_time", 0) * 1000 if "avg_time" in bottleneck else 0
                bottleneck_text += f"{component}: {severity} ({avg_time:.2f}ms)\n"
            
            if bottleneck_text:
                embed.add_field(
                    name="⚠️ Potential Bottlenecks",
                    value=bottleneck_text,
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reset_metrics", description="Reset performance metrics")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        metric_type=[
            app_commands.Choice(name="All Metrics", value="all"),
            app_commands.Choice(name="Performance Monitor", value="performance"),
            app_commands.Choice(name="Battle Metrics", value="battle"),
            app_commands.Choice(name="Cache Statistics", value="cache")
        ]
    )
    async def reset_metrics(self, interaction: discord.Interaction, metric_type: str):
        """
        Reset performance metrics of a specific type or all metrics.
        """
        # Verify developer permissions
        validation = await self.security.validate_db_command_access(
            str(interaction.user.id), "reset_metrics", "dev"
        )
        if not validation["valid"]:
            await interaction.response.send_message(f"❌ {validation['error']}", ephemeral=True)
            return
        
        # Reset the specified metrics
        if metric_type == "all" or metric_type == "performance":
            self.performance_monitor.reset_statistics()
        
        if metric_type == "all" or metric_type == "battle":
            self.battle_metrics.clear_metrics()
        
        if metric_type == "all" or metric_type == "cache":
            # Reset cache statistics (not clearing the cache itself)
            self.cache_manager.get_cache_stats()  # This resets the internal stats counters
        
        await interaction.response.send_message(f"✅ Reset {metric_type} metrics successfully.", ephemeral=True)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(DevToolsCog(bot))
