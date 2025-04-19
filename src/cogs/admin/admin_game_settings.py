import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Union, Literal

from src.db.db import get_connection, create_tables
from src.models.permissions import require_permission_level, PermissionLevel, is_admin, is_dev

# Load data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class AdminGameSettingsCog(commands.Cog):
    """
    Admin commands for managing game settings in Veramon Reunited.
    
    Includes configuration for rarity tiers, evolution rules, and battle settings.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="admin_config_rarity", description="Configure rarity tier settings (Admin only)")
    @app_commands.describe(
        rarity="Rarity tier to configure",
        catch_rate="Base catch rate for this rarity (0-100)",
        spawn_weight="Global spawn weight for this rarity (0-100)",
        experience_multiplier="XP multiplier for this rarity (e.g., 1.0, 1.5, 2.0)",
        token_reward="Token reward for catching a Veramon of this rarity"
    )
    @is_admin()
    async def admin_config_rarity(
        self,
        interaction: discord.Interaction,
        rarity: Literal["common", "uncommon", "rare", "legendary", "mythic", "shiny"],
        catch_rate: Optional[float] = None,
        spawn_weight: Optional[float] = None,
        experience_multiplier: Optional[float] = None,
        token_reward: Optional[int] = None
    ):
        """Configure rarity tier settings."""
        # Load rarity settings
        rarity_file = os.path.join(DATA_DIR, "rarity_settings.json")
        
        try:
            with open(rarity_file, 'r') as f:
                rarity_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default settings if file doesn't exist or is invalid
            rarity_settings = {
                "common": {
                    "catch_rate": 70.0,
                    "spawn_weight": 70.0,
                    "experience_multiplier": 1.0,
                    "token_reward": 1
                },
                "uncommon": {
                    "catch_rate": 45.0,
                    "spawn_weight": 20.0,
                    "experience_multiplier": 1.2,
                    "token_reward": 2
                },
                "rare": {
                    "catch_rate": 25.0,
                    "spawn_weight": 8.0,
                    "experience_multiplier": 1.5,
                    "token_reward": 5
                },
                "legendary": {
                    "catch_rate": 10.0,
                    "spawn_weight": 1.5,
                    "experience_multiplier": 2.0,
                    "token_reward": 10
                },
                "mythic": {
                    "catch_rate": 3.0,
                    "spawn_weight": 0.5,
                    "experience_multiplier": 2.5,
                    "token_reward": 20
                },
                "shiny": {
                    "catch_rate": 0.0,  # No modifier for shiny
                    "spawn_weight": 0.0,  # Controlled by shiny_rate
                    "experience_multiplier": 1.5,
                    "token_reward": 15
                }
            }
            
        # Create rarity if it doesn't exist
        if rarity not in rarity_settings:
            rarity_settings[rarity] = {
                "catch_rate": 50.0,
                "spawn_weight": 10.0,
                "experience_multiplier": 1.0,
                "token_reward": 1
            }
            
        # Update settings if provided
        if catch_rate is not None:
            rarity_settings[rarity]["catch_rate"] = max(0, min(100, catch_rate))
            
        if spawn_weight is not None:
            rarity_settings[rarity]["spawn_weight"] = max(0, min(100, spawn_weight))
            
        if experience_multiplier is not None:
            rarity_settings[rarity]["experience_multiplier"] = max(0.1, experience_multiplier)
            
        if token_reward is not None:
            rarity_settings[rarity]["token_reward"] = max(0, token_reward)
            
        # Save updated settings
        with open(rarity_file, 'w') as f:
            json.dump(rarity_settings, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="Rarity Settings Updated",
            description=f"Successfully updated settings for {rarity.capitalize()}.",
            color=discord.Color.blue()
        )
        
        settings = rarity_settings[rarity]
        
        embed.add_field(name="Catch Rate", value=f"{settings['catch_rate']}%", inline=True)
        embed.add_field(name="Spawn Weight", value=f"{settings['spawn_weight']}%", inline=True)
        embed.add_field(name="XP Multiplier", value=f"{settings['experience_multiplier']}x", inline=True)
        embed.add_field(name="Token Reward", value=str(settings['token_reward']), inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_evolution_rules", description="Configure evolution rules (Admin only)")
    @app_commands.describe(
        rule_type="Type of evolution rule to configure",
        value="New value for the rule"
    )
    @is_admin()
    async def admin_evolution_rules(
        self,
        interaction: discord.Interaction,
        rule_type: Literal["level_mult", "stats_mult", "shiny_chance", "max_evolutions"],
        value: float
    ):
        """Configure global evolution rules."""
        # Load evolution rules
        evolution_file = os.path.join(DATA_DIR, "evolution_rules.json")
        
        try:
            with open(evolution_file, 'r') as f:
                evolution_rules = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default rules if file doesn't exist or is invalid
            evolution_rules = {
                "level_mult": 1.0,  # Level multiplier on evolution
                "stats_mult": 1.2,  # Stats multiplier on evolution
                "shiny_chance": 0.01,  # Chance of becoming shiny on evolution
                "max_evolutions": 3  # Maximum evolution stages
            }
            
        # Validate and update rule
        if rule_type == "level_mult":
            evolution_rules["level_mult"] = max(0.1, min(5.0, value))
        elif rule_type == "stats_mult":
            evolution_rules["stats_mult"] = max(1.0, min(3.0, value))
        elif rule_type == "shiny_chance":
            evolution_rules["shiny_chance"] = max(0.0, min(1.0, value))
        elif rule_type == "max_evolutions":
            evolution_rules["max_evolutions"] = max(1, min(10, int(value)))
            
        # Save updated rules
        with open(evolution_file, 'w') as f:
            json.dump(evolution_rules, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="Evolution Rules Updated",
            description=f"Successfully updated {rule_type}.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Rule", value=rule_type, inline=True)
        embed.add_field(name="New Value", value=str(evolution_rules[rule_type]), inline=True)
        
        # Show all current rules
        rules_text = "\n".join([f"**{k}**: {v}" for k, v in evolution_rules.items()])
        embed.add_field(name="Current Rules", value=rules_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_battle_settings", description="Configure battle system settings (Admin only)")
    @app_commands.describe(
        setting="Battle setting to configure",
        value="New value for the setting"
    )
    @is_admin()
    async def admin_battle_settings(
        self,
        interaction: discord.Interaction,
        setting: Literal["base_xp_reward", "token_reward_mult", "crit_chance", "crit_damage", "turn_timeout", "max_participants", "type_effectiveness_mult"],
        value: float
    ):
        """Configure battle system settings."""
        # Load battle settings
        battle_file = os.path.join(DATA_DIR, "battle_settings.json")
        
        try:
            with open(battle_file, 'r') as f:
                battle_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default settings if file doesn't exist or is invalid
            battle_settings = {
                "base_xp_reward": 100.0,  # Base XP for winning a battle
                "token_reward_mult": 0.1,  # Token reward multiplier
                "crit_chance": 0.06,  # Critical hit chance (6%)
                "crit_damage": 1.5,  # Critical damage multiplier
                "turn_timeout": 60.0,  # Seconds before a turn times out
                "max_participants": 4,  # Maximum participants in a multi-battle
                "type_effectiveness_mult": 0.5,  # Type effectiveness multiplier (0.5 = 2x damage / 0.5x damage)
                "status_duration": 3,  # Default status effect duration in turns
                "status_chance": 0.3,  # Default status effect chance
                "pve_difficulty_mult": {
                    "easy": 0.8,
                    "normal": 1.0,
                    "hard": 1.2,
                    "expert": 1.5
                }
            }
            
        # Validate and update setting
        if setting == "base_xp_reward":
            battle_settings["base_xp_reward"] = max(10.0, value)
        elif setting == "token_reward_mult":
            battle_settings["token_reward_mult"] = max(0.0, min(10.0, value))
        elif setting == "crit_chance":
            battle_settings["crit_chance"] = max(0.0, min(1.0, value))
        elif setting == "crit_damage":
            battle_settings["crit_damage"] = max(1.0, min(5.0, value))
        elif setting == "turn_timeout":
            battle_settings["turn_timeout"] = max(10.0, min(300.0, value))
        elif setting == "max_participants":
            battle_settings["max_participants"] = max(2, min(10, int(value)))
        elif setting == "type_effectiveness_mult":
            battle_settings["type_effectiveness_mult"] = max(0.1, min(1.0, value))
            
        # Save updated settings
        with open(battle_file, 'w') as f:
            json.dump(battle_settings, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="Battle Settings Updated",
            description=f"Successfully updated {setting}.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Setting", value=setting, inline=True)
        embed.add_field(name="New Value", value=str(battle_settings[setting]), inline=True)
        
        # Show primary settings
        primary_settings = ["base_xp_reward", "token_reward_mult", "crit_chance", 
                            "crit_damage", "turn_timeout", "max_participants", 
                            "type_effectiveness_mult"]
                            
        settings_text = "\n".join([f"**{k}**: {battle_settings[k]}" for k in primary_settings])
        embed.add_field(name="Current Settings", value=settings_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_rebuild_db", description="Rebuild database tables (Admin only)")
    @app_commands.describe(
        confirm="Type 'confirm' to verify you want to rebuild the database",
        keep_data="Whether to keep existing data or clear it"
    )
    @is_dev()
    async def admin_rebuild_db(
        self,
        interaction: discord.Interaction,
        confirm: str,
        keep_data: bool = True
    ):
        """Rebuild database tables (for schema updates)."""
        if confirm.lower() != "confirm":
            await interaction.response.send_message(
                "Database rebuild cancelled. Please type 'confirm' to proceed.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            # Get connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Backup data if keeping it
            data_backup = {}
            if keep_data:
                # Get list of tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [table[0] for table in cursor.fetchall() if table[0] != "sqlite_sequence"]
                
                # Backup each table
                for table in tables:
                    try:
                        cursor.execute(f"SELECT * FROM {table}")
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        
                        data_backup[table] = {
                            "columns": columns,
                            "rows": rows
                        }
                    except sqlite3.Error as e:
                        await interaction.followup.send(f"Error backing up table {table}: {e}")
                        return
            
            # Drop all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall() if table[0] != "sqlite_sequence"]
            
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                
            # Recreate tables
            create_tables()
            
            # Restore data if keeping it
            if keep_data:
                for table, data in data_backup.items():
                    columns = data["columns"]
                    rows = data["rows"]
                    
                    for row in rows:
                        try:
                            placeholders = ", ".join(["?"] * len(columns))
                            column_names = ", ".join(columns)
                            cursor.execute(
                                f"INSERT OR IGNORE INTO {table} ({column_names}) VALUES ({placeholders})",
                                row
                            )
                        except sqlite3.Error as e:
                            await interaction.followup.send(f"Error restoring row in table {table}: {e}")
                            continue
            
            conn.commit()
            conn.close()
            
            # Success message
            if keep_data:
                await interaction.followup.send("Database successfully rebuilt with data preserved.")
            else:
                await interaction.followup.send("Database successfully rebuilt. All data has been cleared.")
                
        except Exception as e:
            await interaction.followup.send(f"Error rebuilding database: {str(e)}")
            
    @app_commands.command(name="admin_export_data", description="Export game data to JSON files (Admin only)")
    @app_commands.describe(
        data_type="Type of data to export"
    )
    @is_admin()
    async def admin_export_data(
        self,
        interaction: discord.Interaction,
        data_type: Literal["veramon", "abilities", "items", "biomes", "all"]
    ):
        """Export game data to JSON files for backup or external editing."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            # Determine which files to export
            files_to_export = []
            if data_type == "veramon" or data_type == "all":
                files_to_export.append("veramon_data.json")
            if data_type == "abilities" or data_type == "all":
                files_to_export.append("abilities.json")
            if data_type == "items" or data_type == "all":
                files_to_export.append("items.json")
            if data_type == "biomes" or data_type == "all":
                files_to_export.append("biomes.json")
                
            if not files_to_export:
                await interaction.followup.send(f"No data files selected for export.")
                return
                
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(DATA_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate timestamp for backup files
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            # Export each file
            exported_files = []
            for file_name in files_to_export:
                source_path = os.path.join(DATA_DIR, file_name)
                
                if not os.path.exists(source_path):
                    await interaction.followup.send(f"Warning: Source file {file_name} not found.")
                    continue
                    
                # Read the source file
                with open(source_path, 'r') as f:
                    data = json.load(f)
                    
                # Write to backup file
                backup_file = f"{os.path.splitext(file_name)[0]}_{timestamp}.json"
                backup_path = os.path.join(backup_dir, backup_file)
                
                with open(backup_path, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                exported_files.append(backup_file)
                
            # Success message
            if exported_files:
                files_message = "\n".join([f"- {file}" for file in exported_files])
                await interaction.followup.send(
                    f"Successfully exported the following data files to the backups directory:\n{files_message}"
                )
            else:
                await interaction.followup.send("No files were exported.")
                
        except Exception as e:
            await interaction.followup.send(f"Error exporting data: {str(e)}")
            
    @app_commands.command(name="admin_import_data", description="Import game data from JSON files (Admin only)")
    @app_commands.describe(
        data_type="Type of data to import",
        backup_name="Name of the backup file to import (without timestamp)"
    )
    @is_admin()
    async def admin_import_data(
        self,
        interaction: discord.Interaction,
        data_type: Literal["veramon", "abilities", "items", "biomes"],
        backup_name: str
    ):
        """Import game data from backup JSON files."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            # Determine the file mapping
            file_mappings = {
                "veramon": "veramon_data.json",
                "abilities": "abilities.json",
                "items": "items.json",
                "biomes": "biomes.json"
            }
            
            target_file = file_mappings.get(data_type)
            if not target_file:
                await interaction.followup.send(f"Unknown data type: {data_type}")
                return
                
            # Get list of backup files
            backup_dir = os.path.join(DATA_DIR, "backups")
            if not os.path.exists(backup_dir):
                await interaction.followup.send("Backup directory not found.")
                return
                
            # Find matching backup file
            backup_prefix = f"{data_type}_"
            matching_files = [f for f in os.listdir(backup_dir) if f.startswith(backup_prefix) and f.endswith(".json")]
            
            if not matching_files:
                await interaction.followup.send(f"No backup files found for {data_type}.")
                return
                
            # Sort by timestamp (newest first)
            matching_files.sort(reverse=True)
            
            # Find the specific backup if provided
            selected_backup = None
            if backup_name:
                for backup_file in matching_files:
                    if backup_name in backup_file:
                        selected_backup = backup_file
                        break
                        
                if not selected_backup:
                    files_list = "\n".join([f"- {file}" for file in matching_files[:10]])
                    await interaction.followup.send(
                        f"Backup file with name '{backup_name}' not found. Available backups:\n{files_list}"
                    )
                    return
            else:
                # Use the most recent backup
                selected_backup = matching_files[0]
                
            # Import the backup
            backup_path = os.path.join(backup_dir, selected_backup)
            target_path = os.path.join(DATA_DIR, target_file)
            
            # Create backup of current file
            current_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            current_backup = f"{data_type}_current_{current_timestamp}.json"
            current_backup_path = os.path.join(backup_dir, current_backup)
            
            # Backup current file if it exists
            if os.path.exists(target_path):
                with open(target_path, 'r') as f:
                    current_data = json.load(f)
                    
                with open(current_backup_path, 'w') as f:
                    json.dump(current_data, f, indent=2)
                    
            # Import the backup file
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
                
            with open(target_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
                
            # Success message
            await interaction.followup.send(
                f"Successfully imported {data_type} data from {selected_backup}. "
                f"Current data backed up to {current_backup}."
            )
                
        except Exception as e:
            await interaction.followup.send(f"Error importing data: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminGameSettingsCog(bot))
