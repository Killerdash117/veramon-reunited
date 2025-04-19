import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sqlite3
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Union, Literal, Any

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel, is_dev

class DeveloperCog(commands.Cog):
    """
    Developer commands for Veramon Reunited.
    
    Includes commands for debugging, data management, system control, and testing.
    Only accessible to users with the highest permission level.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result = None
        
    #-------------------------------------------------------------------
    # Debug Commands
    #-------------------------------------------------------------------
    
    @app_commands.command(name="dev_debug", description="Enable debug mode for a specific module (Dev only)")
    @app_commands.describe(
        module="Module to enable debug mode for (all, database, battle, etc.)"
    )
    @is_dev()
    async def dev_debug(self, interaction: discord.Interaction, module: str):
        """Enable debug mode for a specific module."""
        # Set debug flag in configuration
        config_file = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        if "debug" not in config:
            config["debug"] = {}
            
        config["debug"][module.lower()] = True
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        await interaction.response.send_message(
            f"Debug mode enabled for module: `{module}`\n"
            f"Debug output will be more verbose in logs.",
            ephemeral=True
        )
        
    @app_commands.command(name="dev_error_log", description="View recent error logs (Dev only)")
    @app_commands.describe(
        count="Number of recent errors to show (default: 5)"
    )
    @is_dev()
    async def dev_error_log(self, interaction: discord.Interaction, count: int = 5):
        """View recent error logs."""
        try:
            log_file = os.path.join(os.path.dirname(__file__), "..", "logs", "errors.log")
            
            if not os.path.exists(log_file):
                await interaction.response.send_message(
                    "No error log file found.",
                    ephemeral=True
                )
                return
                
            with open(log_file, 'r') as f:
                # Read the last N errors (separated by --- markers)
                log_content = f.read()
                error_entries = log_content.split("---")
                
                # Get the most recent errors
                recent_errors = error_entries[-min(count+1, len(error_entries)):-1]
                
                if not recent_errors:
                    await interaction.response.send_message(
                        "No recent errors found in the log.",
                        ephemeral=True
                    )
                    return
                    
                # Create embed for each error
                embeds = []
                for i, error in enumerate(reversed(recent_errors)):
                    if not error.strip():
                        continue
                        
                    # Try to parse the error entry
                    try:
                        error_lines = error.strip().split("\n")
                        timestamp_line = error_lines[0]
                        error_type = error_lines[1] if len(error_lines) > 1 else "Unknown Error"
                        details = "\n".join(error_lines[2:]) if len(error_lines) > 2 else "No details available"
                        
                        embed = discord.Embed(
                            title=f"Error #{i+1}",
                            description=f"**Type:** {error_type}",
                            color=discord.Color.red()
                        )
                        
                        embed.add_field(name="Timestamp", value=timestamp_line, inline=False)
                        embed.add_field(name="Details", value=f"```\n{details[:1000]}{'...' if len(details) > 1000 else ''}\n```", inline=False)
                        
                        embeds.append(embed)
                    except Exception:
                        # Fallback if parsing fails
                        embed = discord.Embed(
                            title=f"Error #{i+1}",
                            description=f"```\n{error[:4000]}{'...' if len(error) > 4000 else ''}\n```",
                            color=discord.Color.red()
                        )
                        embeds.append(embed)
                
                # Send the first embed with navigation if needed
                if embeds:
                    await interaction.response.send_message(
                        f"Showing {len(embeds)} recent errors:",
                        embed=embeds[0],
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Failed to parse any error logs.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            await interaction.response.send_message(
                f"Error retrieving error logs: {str(e)}",
                ephemeral=True
            )
            
    @app_commands.command(name="dev_memory_usage", description="View memory usage statistics (Dev only)")
    @is_dev()
    async def dev_memory_usage(self, interaction: discord.Interaction):
        """View memory usage statistics."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            
            # Get memory info
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # Format memory values
            rss_mb = memory_info.rss / (1024 * 1024)
            vms_mb = memory_info.vms / (1024 * 1024)
            
            # Get system memory info
            system_memory = psutil.virtual_memory()
            system_memory_total = system_memory.total / (1024 * 1024)
            system_memory_available = system_memory.available / (1024 * 1024)
            system_memory_used_percent = system_memory.percent
            
            # Create embed
            embed = discord.Embed(
                title="Memory Usage Statistics",
                description="Current memory usage of the Veramon Reunited bot process",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Process RSS", value=f"{rss_mb:.2f} MB", inline=True)
            embed.add_field(name="Process VMS", value=f"{vms_mb:.2f} MB", inline=True)
            embed.add_field(name="Memory Usage", value=f"{memory_percent:.1f}%", inline=True)
            
            embed.add_field(name="System Total", value=f"{system_memory_total:.2f} MB", inline=True)
            embed.add_field(name="System Available", value=f"{system_memory_available:.2f} MB", inline=True)
            embed.add_field(name="System Used", value=f"{system_memory_used_percent:.1f}%", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ImportError:
            await interaction.response.send_message(
                "Required module `psutil` not installed. Please install it to use this command.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error getting memory usage: {str(e)}",
                ephemeral=True
            )
            
    #-------------------------------------------------------------------
    # Data Management
    #-------------------------------------------------------------------
    
    @app_commands.command(name="dev_migration", description="Run database migrations (Dev only)")
    @app_commands.describe(
        version="Migration version to run (optional)"
    )
    @is_dev()
    async def dev_migration(self, interaction: discord.Interaction, version: Optional[str] = None):
        """Run database migrations."""
        try:
            from src.db.migrations import run_migrations
            
            await interaction.response.defer(ephemeral=True)
            
            # Run migrations
            result = run_migrations(version)
            
            await interaction.followup.send(
                f"Database migration completed!\n\n"
                f"Result: {result}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Error running migrations: {str(e)}\n\n"
                f"```\n{traceback.format_exc()}\n```",
                ephemeral=True
            )
            
    @app_commands.command(name="dev_rebuild_indices", description="Rebuild database indices (Dev only)")
    @is_dev()
    async def dev_rebuild_indices(self, interaction: discord.Interaction):
        """Rebuild database indices for performance optimization."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            await interaction.response.defer(ephemeral=True)
            
            # Analyze the database
            cursor.execute("ANALYZE")
            
            # Rebuild indices
            cursor.execute("REINDEX")
            
            # Vacuum the database
            cursor.execute("VACUUM")
            
            conn.commit()
            conn.close()
            
            await interaction.followup.send(
                "Successfully rebuilt database indices and optimized the database.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Error rebuilding indices: {str(e)}",
                ephemeral=True
            )
            
    @app_commands.command(name="dev_test_data", description="Generate test data (Dev only)")
    @app_commands.describe(
        amount="Amount of test data to generate (default: 5)"
    )
    @is_dev()
    async def dev_test_data(self, interaction: discord.Interaction, amount: int = 5):
        """Generate test data for development purposes."""
        try:
            from src.utils.test_data_generator import generate_test_data
            
            await interaction.response.defer(ephemeral=True)
            
            # Generate test data
            result = generate_test_data(amount)
            
            await interaction.followup.send(
                f"Test data generation completed!\n\n"
                f"Generated:\n"
                f"- {result.get('users', 0)} test users\n"
                f"- {result.get('veramon', 0)} veramon captures\n"
                f"- {result.get('battles', 0)} test battles\n"
                f"- {result.get('trades', 0)} test trades\n",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Error generating test data: {str(e)}",
                ephemeral=True
            )
            
    #-------------------------------------------------------------------
    # System Commands
    #-------------------------------------------------------------------
    
    @app_commands.command(name="dev_reload", description="Reload a specific code module (Dev only)")
    @app_commands.describe(
        module="Module to reload (e.g., 'economy_cog')"
    )
    @is_dev()
    async def dev_reload(self, interaction: discord.Interaction, module: str):
        """Reload a specific code module."""
        try:
            # Check if it's a cog
            if module.lower().endswith('_cog'):
                # Attempt to reload the cog
                await self.bot.reload_extension(f"src.cogs.{module.lower()}")
                
                await interaction.response.send_message(
                    f"Successfully reloaded cog: `{module}`",
                    ephemeral=True
                )
            else:
                # Try to reload a specific module
                module_path = f"src.{module}"
                if module_path in sys.modules:
                    import importlib
                    importlib.reload(sys.modules[module_path])
                    
                    await interaction.response.send_message(
                        f"Successfully reloaded module: `{module_path}`",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"Module `{module_path}` not found in loaded modules.",
                        ephemeral=True
                    )
        except Exception as e:
            await interaction.response.send_message(
                f"Error reloading module: {str(e)}\n\n"
                f"```\n{traceback.format_exc()}\n```",
                ephemeral=True
            )
            
    @app_commands.command(name="dev_config", description="Modify configuration values (Dev only)")
    @app_commands.describe(
        key="Configuration key to modify",
        value="New value for the configuration key"
    )
    @is_dev()
    async def dev_config(self, interaction: discord.Interaction, key: str, value: str):
        """Modify configuration values."""
        try:
            config_file = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Parse nested keys (e.g., "spawn.rates.common")
            key_parts = key.split('.')
            current = config
            
            # Navigate to the nested location
            for i, part in enumerate(key_parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
                
            # Try to parse the value as appropriate type
            final_key = key_parts[-1]
            
            # Try to interpret value as the right type
            if value.lower() == "true":
                parsed_value = True
            elif value.lower() == "false":
                parsed_value = False
            elif value.isdigit():
                parsed_value = int(value)
            elif value.replace('.', '', 1).isdigit():
                parsed_value = float(value)
            else:
                # Keep as string
                parsed_value = value
                
            # Update the value
            current[final_key] = parsed_value
            
            # Save the updated config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            await interaction.response.send_message(
                f"Configuration updated:\n"
                f"Key: `{key}`\n"
                f"New Value: `{parsed_value}`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error updating configuration: {str(e)}",
                ephemeral=True
            )
            
    #-------------------------------------------------------------------
    # Testing Tools
    #-------------------------------------------------------------------
    
    @app_commands.command(name="dev_simulate_catch", description="Simulate Veramon catches (Dev only)")
    @app_commands.describe(
        rarity="Rarity of Veramon to simulate",
        shiny_chance="Shiny chance multiplier (default: 1.0)",
        count="Number of simulations to run (default: 100)"
    )
    @is_dev()
    async def dev_simulate_catch(
        self, 
        interaction: discord.Interaction, 
        rarity: Literal["common", "uncommon", "rare", "legendary", "mythic"],
        shiny_chance: float = 1.0,
        count: int = 100
    ):
        """Simulate multiple Veramon catches for balance testing."""
        try:
            from src.models.veramon import calculate_catch_chance
            from src.utils.catch_simulator import simulate_catches
            
            await interaction.response.defer(ephemeral=True)
            
            # Limit to reasonable numbers
            count = min(count, 10000)
            
            # Run simulation
            results = simulate_catches(rarity, shiny_chance, count)
            
            # Create embed with results
            embed = discord.Embed(
                title="Catch Simulation Results",
                description=f"Simulated {count} catch attempts for {rarity.capitalize()} Veramon",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Success Rate", value=f"{results['success_rate']:.2f}%", inline=True)
            embed.add_field(name="Shiny Rate", value=f"{results['shiny_rate']:.2f}%", inline=True)
            embed.add_field(name="Avg Attempts", value=f"{results['avg_attempts']:.2f}", inline=True)
            
            # Add distribution info
            distribution = results.get('ball_distribution', {})
            if distribution:
                dist_text = "\n".join([f"{ball_name}: {count} uses ({(count/sum(distribution.values())*100):.1f}%)" 
                                      for ball_name, count in distribution.items()])
                embed.add_field(name="Ball Distribution", value=dist_text, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                f"Error simulating catches: {str(e)}",
                ephemeral=True
            )
            
    @app_commands.command(name="dev_simulate_battle", description="Simulate a battle outcome (Dev only)")
    @app_commands.describe(
        team1="First team (comma-separated Veramon names)",
        team2="Second team (comma-separated Veramon names)",
        iterations="Number of battles to simulate (default: 100)"
    )
    @is_dev()
    async def dev_simulate_battle(
        self, 
        interaction: discord.Interaction, 
        team1: str,
        team2: str,
        iterations: int = 100
    ):
        """Simulate multiple battles between two teams for balance testing."""
        try:
            from src.utils.battle_simulator import simulate_battles
            
            await interaction.response.defer(ephemeral=True)
            
            # Parse teams
            team1_veramon = [name.strip() for name in team1.split(',')]
            team2_veramon = [name.strip() for name in team2.split(',')]
            
            # Limit to reasonable numbers
            iterations = min(iterations, 1000)
            
            # Run simulation
            results = simulate_battles(team1_veramon, team2_veramon, iterations)
            
            # Create embed with results
            embed = discord.Embed(
                title="Battle Simulation Results",
                description=f"Simulated {iterations} battles between two teams",
                color=discord.Color.blue()
            )
            
            # Add team info
            embed.add_field(name="Team 1", value=", ".join(team1_veramon), inline=False)
            embed.add_field(name="Team 2", value=", ".join(team2_veramon), inline=False)
            
            # Add results
            team1_wins = results.get('team1_wins', 0)
            team2_wins = results.get('team2_wins', 0)
            ties = results.get('ties', 0)
            
            win_rate1 = (team1_wins / iterations) * 100
            win_rate2 = (team2_wins / iterations) * 100
            tie_rate = (ties / iterations) * 100
            
            embed.add_field(name="Team 1 Wins", value=f"{team1_wins} ({win_rate1:.1f}%)", inline=True)
            embed.add_field(name="Team 2 Wins", value=f"{team2_wins} ({win_rate2:.1f}%)", inline=True)
            embed.add_field(name="Ties", value=f"{ties} ({tie_rate:.1f}%)", inline=True)
            
            # Add average battle length
            avg_turns = results.get('avg_turns', 0)
            embed.add_field(name="Avg. Battle Length", value=f"{avg_turns:.1f} turns", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                f"Error simulating battles: {str(e)}",
                ephemeral=True
            )
            
async def setup(bot: commands.Bot):
    """Add the DeveloperCog to the bot."""
    await bot.add_cog(DeveloperCog(bot))
