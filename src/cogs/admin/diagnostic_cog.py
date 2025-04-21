"""
Diagnostic Command Cog for Veramon Reunited
2025 killerdash117 | https://github.com/killerdash117

This module provides diagnostic tools for troubleshooting the Veramon bot,
including system information reports and health checks.
"""

import os
import sys
import json
import time
import logging
import platform
import sqlite3
import discord
from datetime import datetime
from typing import Dict, Any, List, Optional
from discord import app_commands
from discord.ext import commands

import psutil

from src.utils.env_config import get_env_value
from src.db.db import get_connection
from src.utils.cache import clear_cache, get_cache_stats
from src.utils.config_manager import get_config
from src.utils.performance_monitor import get_performance_stats

# Set up logging
logger = logging.getLogger("veramon.diagnostic")

class DiagnosticCog(commands.Cog):
    """
    Diagnostic commands for troubleshooting Veramon Reunited.
    
    Provides system information, performance metrics, and health checks.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now()
    
    @app_commands.command(
        name="debug_info", 
        description="Generate a diagnostic report for troubleshooting"
    )
    @app_commands.describe(
        include_system="Include system information in the report",
        include_database="Include database status in the report",
        include_cache="Include cache statistics in the report"
    )
    async def debug_info(
        self, 
        interaction: discord.Interaction, 
        include_system: bool = True,
        include_database: bool = True, 
        include_cache: bool = True
    ):
        """
        Generate a comprehensive diagnostic report for troubleshooting.
        
        This command collects information about the bot's status, system resources,
        database health, and cache statistics to help diagnose issues.
        """
        # Defer the response as this might take a moment
        await interaction.response.defer(ephemeral=True)
        
        # Start collecting diagnostic data
        report = {}
        
        # Basic bot information
        report["bot_info"] = {
            "bot_id": self.bot.user.id if self.bot.user else "Unknown",
            "bot_name": self.bot.user.name if self.bot.user else "Unknown",
            "uptime": str(datetime.now() - self.start_time),
            "discord_py_version": discord.__version__,
            "command_count": len(self.bot.tree.get_commands()),
            "guild_count": len(self.bot.guilds),
            "timestamp": datetime.now().isoformat()
        }
        
        # Version information
        try:
            with open(os.path.join("src", "utils", "version.py"), "r") as f:
                version_content = f.read()
                report["version"] = {
                    "raw": version_content,
                    "parsed": {
                        k: v for k, v in locals().items() 
                        if k.startswith("__") and k.endswith("__") and k != "__file__"
                    }
                }
        except Exception as e:
            report["version"] = {"error": str(e)}
        
        # System information (if requested)
        if include_system:
            try:
                report["system"] = {
                    "platform": platform.platform(),
                    "python_version": sys.version,
                    "cpu_count": psutil.cpu_count(),
                    "cpu_usage": psutil.cpu_percent(interval=0.5),
                    "memory_total": psutil.virtual_memory().total,
                    "memory_available": psutil.virtual_memory().available,
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": dict(psutil.disk_usage(".").__dict__) if hasattr(psutil.disk_usage("."), "__dict__") else str(psutil.disk_usage("."))
                }
            except Exception as e:
                report["system"] = {"error": str(e)}
        
        # Database status (if requested)
        if include_database:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Basic database info
                cursor.execute("PRAGMA database_list")
                db_info = cursor.fetchall()
                
                # Table counts
                table_counts = {}
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    table_counts[table_name] = cursor.fetchone()[0]
                
                # Database size and stats
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                report["database"] = {
                    "info": db_info,
                    "table_counts": table_counts,
                    "size_bytes": page_count * page_size,
                    "integrity_check": self._run_integrity_check(cursor)
                }
                
                conn.close()
            except Exception as e:
                report["database"] = {"error": str(e)}
        
        # Cache statistics (if requested)
        if include_cache:
            try:
                report["cache"] = get_cache_stats()
            except Exception as e:
                report["cache"] = {"error": str(e)}
        
        # Performance metrics
        try:
            report["performance"] = get_performance_stats()
        except Exception as e:
            report["performance"] = {"error": str(e)}
        
        # Create the diagnostic report embed
        embed = discord.Embed(
            title="📊 Diagnostic Report",
            description=f"Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=0x3498db
        )
        
        # Bot Info Section
        bot_info = report["bot_info"]
        embed.add_field(
            name="Bot Information",
            value=f"**Name:** {bot_info['bot_name']}\n"
                  f"**Uptime:** {bot_info['uptime']}\n"
                  f"**Discord.py:** {bot_info['discord_py_version']}\n"
                  f"**Commands:** {bot_info['command_count']}\n"
                  f"**Guilds:** {bot_info['guild_count']}",
            inline=False
        )
        
        # System Info Section (if included)
        if include_system and "error" not in report["system"]:
            system = report["system"]
            memory_used_gb = (system["memory_total"] - system["memory_available"]) / (1024**3)
            memory_total_gb = system["memory_total"] / (1024**3)
            
            embed.add_field(
                name="System Information",
                value=f"**Platform:** {system['platform']}\n"
                      f"**CPU Usage:** {system['cpu_usage']}%\n"
                      f"**Memory Usage:** {memory_used_gb:.2f} GB / {memory_total_gb:.2f} GB ({system['memory_percent']}%)",
                inline=False
            )
        
        # Database Info Section (if included)
        if include_database and "error" not in report["database"]:
            db = report["database"]
            db_size_mb = db["size_bytes"] / (1024**2)
            
            # Get table count summary (top 5)
            table_summary = "\n".join([
                f"**{table}:** {count} rows" 
                for table, count in sorted(
                    db["table_counts"].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]
            ])
            
            embed.add_field(
                name="Database Information",
                value=f"**Size:** {db_size_mb:.2f} MB\n"
                      f"**Integrity:** {db['integrity_check']}\n"
                      f"**Tables (Top 5):**\n{table_summary}",
                inline=False
            )
        
        # Cache Info Section (if included)
        if include_cache and "error" not in report["cache"]:
            cache = report["cache"]
            
            embed.add_field(
                name="Cache Statistics",
                value=f"**Hit Rate:** {cache.get('hit_rate', 0):.2f}%\n"
                      f"**Items Cached:** {cache.get('cached_items', 0)}\n"
                      f"**Memory Usage:** {cache.get('memory_usage', 0) / (1024**2):.2f} MB",
                inline=False
            )
        
        # Performance Metrics
        if "error" not in report["performance"]:
            perf = report["performance"]
            
            # Format the response time metrics
            response_times = perf.get("response_times", {})
            avg_response = response_times.get("average", 0) * 1000  # convert to ms
            
            embed.add_field(
                name="Performance Metrics",
                value=f"**Avg Response Time:** {avg_response:.2f} ms\n"
                      f"**Recent API Calls:** {perf.get('api_calls', {}).get('recent', 0)}\n"
                      f"**Active Battles:** {perf.get('active_sessions', {}).get('battles', 0)}\n"
                      f"**Active Trades:** {perf.get('active_sessions', {}).get('trades', 0)}",
                inline=False
            )
        
        # Generate a detailed report file
        report_json = json.dumps(report, indent=2, default=str)
        
        # Create a temporary file with the report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debug_report_{timestamp}.json"
        filepath = os.path.join("data", "debug", filename)
        
        # Ensure debug directory exists
        os.makedirs(os.path.join("data", "debug"), exist_ok=True)
        
        with open(filepath, "w") as f:
            f.write(report_json)
        
        # Send the report embed and file
        file = discord.File(filepath, filename=filename)
        embed.set_footer(text="Full report attached as JSON file | Use for troubleshooting")
        
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        
        # Log the diagnostic report generation
        logger.info(f"Diagnostic report generated by {interaction.user.name} (ID: {interaction.user.id})")
        
        return True
    
    def _run_integrity_check(self, cursor) -> str:
        """Run a quick integrity check on the database."""
        try:
            cursor.execute("PRAGMA quick_check")
            result = cursor.fetchone()
            return "OK" if result and result[0] == "ok" else "Failed"
        except Exception as e:
            return f"Error: {str(e)}"
    
    @app_commands.command(
        name="system_health", 
        description="Check the health of bot systems"
    )
    async def system_health(self, interaction: discord.Interaction):
        """
        Check the health status of various bot systems.
        
        This command runs quick health checks on database, cache, and API connections
        to identify potential issues.
        """
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        # Initialize health status
        health_status = {
            "database": {"status": "Unknown", "message": "Not tested"},
            "cache": {"status": "Unknown", "message": "Not tested"},
            "discord_api": {"status": "Unknown", "message": "Not tested"},
            "file_system": {"status": "Unknown", "message": "Not tested"}
        }
        
        # Check database health
        try:
            start_time = time.time()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            db_time = (time.time() - start_time) * 1000  # ms
            
            if result and result[0] == 1:
                health_status["database"] = {
                    "status": "OK", 
                    "message": f"Response time: {db_time:.2f}ms"
                }
            else:
                health_status["database"] = {
                    "status": "Warning", 
                    "message": "Unexpected response"
                }
            
            conn.close()
        except Exception as e:
            health_status["database"] = {
                "status": "Error", 
                "message": str(e)
            }
        
        # Check cache health
        try:
            start_time = time.time()
            stats = get_cache_stats()
            cache_time = (time.time() - start_time) * 1000  # ms
            
            if "error" not in stats:
                health_status["cache"] = {
                    "status": "OK", 
                    "message": f"Hit rate: {stats.get('hit_rate', 0):.1f}%, Response: {cache_time:.2f}ms"
                }
            else:
                health_status["cache"] = {
                    "status": "Warning", 
                    "message": stats["error"]
                }
        except Exception as e:
            health_status["cache"] = {
                "status": "Error", 
                "message": str(e)
            }
        
        # Check Discord API connection
        try:
            start_time = time.time()
            latency = self.bot.latency * 1000  # ms
            
            if latency > 0:
                status = "OK" if latency < 500 else "Warning"
                health_status["discord_api"] = {
                    "status": status, 
                    "message": f"Latency: {latency:.2f}ms"
                }
            else:
                health_status["discord_api"] = {
                    "status": "Warning", 
                    "message": "Could not determine latency"
                }
        except Exception as e:
            health_status["discord_api"] = {
                "status": "Error", 
                "message": str(e)
            }
        
        # Check file system
        try:
            start_time = time.time()
            data_path = os.path.join("data")
            if os.path.exists(data_path) and os.access(data_path, os.W_OK):
                # Try a quick write operation
                test_file = os.path.join(data_path, "health_check_test.tmp")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                
                fs_time = (time.time() - start_time) * 1000  # ms
                health_status["file_system"] = {
                    "status": "OK", 
                    "message": f"Write test: {fs_time:.2f}ms"
                }
            else:
                health_status["file_system"] = {
                    "status": "Error", 
                    "message": "Data directory not writable"
                }
        except Exception as e:
            health_status["file_system"] = {
                "status": "Error", 
                "message": str(e)
            }
        
        # Create health status embed
        embed = discord.Embed(
            title="🔍 System Health Check",
            description="Status of bot subsystems",
            color=0x2ecc71  # Green
        )
        
        # Determine overall status
        status_values = {"OK": 0, "Warning": 1, "Error": 2, "Unknown": 3}
        worst_status = "OK"
        for system, info in health_status.items():
            if status_values.get(info["status"], 3) > status_values.get(worst_status, 0):
                worst_status = info["status"]
        
        # Set color based on overall status
        if worst_status == "Error":
            embed.color = 0xe74c3c  # Red
        elif worst_status == "Warning":
            embed.color = 0xf39c12  # Orange
        
        # Add status for each system
        for system, info in health_status.items():
            status_emoji = "✅" if info["status"] == "OK" else "⚠️" if info["status"] == "Warning" else "❌"
            embed.add_field(
                name=f"{status_emoji} {system.replace('_', ' ').title()}",
                value=f"**Status:** {info['status']}\n**Details:** {info['message']}",
                inline=False
            )
        
        # Add timestamp
        embed.set_footer(text=f"Checked at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Send the health status report
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        return True

async def setup(bot):
    """Add the diagnostic cog to the bot."""
    await bot.add_cog(DiagnosticCog(bot))
