import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Union, Literal

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel, is_admin, is_dev

# Load data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class AdminBattleSystemCog(commands.Cog):
    """
    Admin commands for enhancing the battle system in Veramon Reunited.
    
    Includes tools for creating advanced abilities, managing evolution paths,
    and configuring PvE battle scenarios.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="admin_create_advanced_ability", description="Create an advanced ability with special effects (Admin only)")
    @app_commands.describe(
        name="Name of the new ability",
        ability_type="Type of the ability",
        power="Base power of the ability (0 for status moves)",
        accuracy="Accuracy of the ability (0.0-1.0)",
        effect_category="Category of the effect (status/stat/field/special)",
        effect_type="Specific effect type within the category",
        effect_value="Value for the effect (e.g., damage multiplier, stat change)",
        effect_chance="Chance of the effect occurring (0.0-1.0)",
        priority="Priority level (-5 to 5, higher goes first)",
        multi_hit="Whether the ability can hit multiple times",
        multi_hit_range="Range of hits (e.g., '2-5' for 2 to 5 hits)",
        description="Description of the ability"
    )
    @is_admin()
    async def admin_create_advanced_ability(
        self,
        interaction: discord.Interaction,
        name: str,
        ability_type: str,
        power: int,
        accuracy: float,
        effect_category: Literal["none", "status", "stat", "field", "special"] = "none",
        effect_type: str = None,
        effect_value: float = 0.0,
        effect_chance: float = 0.0,
        priority: int = 0,
        multi_hit: bool = False,
        multi_hit_range: str = None,
        description: str = None
    ):
        """Create an advanced ability with complex effects."""
        # Load ability data
        ability_file = os.path.join(DATA_DIR, "abilities.json")
        
        with open(ability_file, 'r') as f:
            ability_data = json.load(f)
            
        if name in ability_data:
            await interaction.response.send_message(
                f"An ability named '{name}' already exists!",
                ephemeral=True
            )
            return
        
        # Validate priority
        priority = max(-5, min(5, priority))
        
        # Parse multi-hit range if provided
        multi_hit_min = 1
        multi_hit_max = 1
        
        if multi_hit and multi_hit_range:
            try:
                if "-" in multi_hit_range:
                    parts = multi_hit_range.split("-")
                    multi_hit_min = max(1, min(10, int(parts[0])))
                    multi_hit_max = max(multi_hit_min, min(10, int(parts[1])))
                else:
                    multi_hit_min = multi_hit_max = max(1, min(10, int(multi_hit_range)))
            except (ValueError, IndexError):
                await interaction.response.send_message(
                    "Invalid multi-hit range format. Use '2-5' or a single number.",
                    ephemeral=True
                )
                return
        
        # Create new advanced ability
        new_ability = {
            "type": ability_type,
            "power": power,
            "accuracy": min(1.0, max(0.0, accuracy)),
            "priority": priority,
            "description": description or f"A {ability_type}-type move."
        }
        
        # Add effect if specified
        if effect_category and effect_category.lower() != "none":
            effect_data = {
                "category": effect_category,
                "type": effect_type or "none",
                "value": effect_value,
                "chance": min(1.0, max(0.0, effect_chance))
            }
            
            # Add more specific effect data based on category
            if effect_category == "status":
                # Status effects (burn, freeze, etc.)
                effect_data["duration"] = 3  # Default duration in turns
                
            elif effect_category == "stat":
                # Stat modifiers (attack, defense, etc.)
                effect_data["stages"] = int(effect_value)  # How many stages to change
                effect_data["target"] = "opponent"  # Default target
                
            elif effect_category == "field":
                # Field effects (weather, terrain)
                effect_data["duration"] = 5  # Default duration in turns
                
            new_ability["effect"] = effect_data
        else:
            new_ability["effect"] = None
            
        # Add multi-hit data if applicable
        if multi_hit:
            new_ability["multi_hit"] = {
                "min": multi_hit_min,
                "max": multi_hit_max
            }
        
        # Add to ability data
        ability_data[name] = new_ability
        
        # Save updated data
        with open(ability_file, 'w') as f:
            json.dump(ability_data, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="New Advanced Ability Created!",
            description=f"Successfully added {name} to the game.",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(name="Type", value=ability_type, inline=True)
        
        if power > 0:
            embed.add_field(name="Power", value=str(power), inline=True)
            embed.add_field(name="Accuracy", value=f"{int(accuracy * 100)}%", inline=True)
        else:
            embed.add_field(name="Move Type", value="Status", inline=True)
            
        if priority != 0:
            embed.add_field(name="Priority", value=str(priority), inline=True)
            
        if multi_hit:
            embed.add_field(
                name="Multi-Hit",
                value=f"{multi_hit_min}-{multi_hit_max} times",
                inline=True
            )
            
        if effect_category and effect_category.lower() != "none":
            effect_desc = f"{effect_category.capitalize()}: {effect_type or 'none'}"
            if effect_value != 0:
                effect_desc += f" ({effect_value})"
            if effect_chance < 1.0:
                effect_desc += f" - {int(effect_chance * 100)}% chance"
                
            embed.add_field(name="Effect", value=effect_desc, inline=False)
            
        if description:
            embed.add_field(name="Description", value=description, inline=False)
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_type_effectiveness", description="Configure type effectiveness chart (Admin only)")
    @app_commands.describe(
        attacking_type="The attacking type",
        defending_type="The defending type",
        effectiveness="The effectiveness multiplier",
        operation="Operation to perform on the type chart"
    )
    @is_admin()
    async def admin_type_effectiveness(
        self,
        interaction: discord.Interaction,
        attacking_type: str,
        defending_type: str,
        effectiveness: float,
        operation: Literal["set", "view", "reset"] = "set"
    ):
        """Configure the type effectiveness chart."""
        # Load type effectiveness data
        type_file = os.path.join(DATA_DIR, "type_effectiveness.json")
        
        try:
            with open(type_file, 'r') as f:
                type_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default type chart if file doesn't exist or is invalid
            type_data = {}
        
        # Normalize type names to lowercase
        attacking_type = attacking_type.lower()
        defending_type = defending_type.lower()
        
        if operation == "view":
            # Show current effectiveness
            if attacking_type not in type_data:
                await interaction.response.send_message(
                    f"Type '{attacking_type}' not found in the type chart.",
                    ephemeral=True
                )
                return
                
            if defending_type not in type_data[attacking_type]:
                await interaction.response.send_message(
                    f"No specific effectiveness defined for {attacking_type} against {defending_type}. Default is 1.0.",
                    ephemeral=True
                )
                return
                
            current_effectiveness = type_data[attacking_type][defending_type]
            
            embed = discord.Embed(
                title="Type Effectiveness",
                description=f"{attacking_type.capitalize()} vs {defending_type.capitalize()}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Effectiveness",
                value=f"{current_effectiveness}x damage",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            return
            
        elif operation == "reset":
            # Reset to default (1.0)
            if attacking_type in type_data and defending_type in type_data[attacking_type]:
                del type_data[attacking_type][defending_type]
                
                # Remove attacking type if it's empty
                if not type_data[attacking_type]:
                    del type_data[attacking_type]
                    
                # Save updated data
                with open(type_file, 'w') as f:
                    json.dump(type_data, f, indent=2)
                    
                await interaction.response.send_message(
                    f"Reset effectiveness of {attacking_type} against {defending_type} to default (1.0).",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"No custom effectiveness was set for {attacking_type} against {defending_type}.",
                    ephemeral=True
                )
                
            return
        
        # Set new effectiveness
        # Validate effectiveness
        effectiveness = max(0.0, min(4.0, effectiveness))
        
        # Ensure attacking type exists
        if attacking_type not in type_data:
            type_data[attacking_type] = {}
            
        # Set effectiveness
        type_data[attacking_type][defending_type] = effectiveness
        
        # Save updated data
        with open(type_file, 'w') as f:
            json.dump(type_data, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="Type Effectiveness Updated",
            description=f"Successfully updated effectiveness of {attacking_type} against {defending_type}.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="New Effectiveness",
            value=f"{effectiveness}x damage",
            inline=False
        )
        
        # Interpretation
        interpretation = "Normal damage"
        if effectiveness > 1.0:
            interpretation = "Super effective"
        elif effectiveness < 1.0 and effectiveness > 0:
            interpretation = "Not very effective"
        elif effectiveness == 0:
            interpretation = "No effect"
            
        embed.add_field(name="Interpretation", value=interpretation, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_create_trainer", description="Create or edit an NPC trainer (Admin only)")
    @app_commands.describe(
        name="Name of the NPC trainer",
        difficulty="Difficulty level of the trainer",
        theme="Theme/type specialization of the trainer",
        veramon_count="Number of Veramon in the trainer's team",
        min_level="Minimum level of the trainer's Veramon",
        max_level="Maximum level of the trainer's Veramon",
        token_reward="Token reward for defeating the trainer",
        experience_reward="Experience reward for defeating the trainer"
    )
    @is_admin()
    async def admin_create_trainer(
        self,
        interaction: discord.Interaction,
        name: str,
        difficulty: Literal["easy", "normal", "hard", "expert", "champion"],
        theme: str = "mixed",
        veramon_count: int = 3,
        min_level: int = 5,
        max_level: int = 15,
        token_reward: int = None,
        experience_reward: int = None
    ):
        """Create or edit an NPC trainer."""
        # Validate input
        veramon_count = max(1, min(6, veramon_count))
        min_level = max(1, min(100, min_level))
        max_level = max(min_level, min(100, max_level))
        
        # Set default rewards based on difficulty if not provided
        if token_reward is None:
            token_reward = {
                "easy": 10,
                "normal": 20,
                "hard": 35,
                "expert": 50,
                "champion": 100
            }.get(difficulty, 25)
            
        if experience_reward is None:
            experience_reward = {
                "easy": 100,
                "normal": 250,
                "hard": 500,
                "expert": 1000,
                "champion": 2000
            }.get(difficulty, 300)
        
        # Add to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if trainer already exists
        cursor.execute("SELECT trainer_id FROM npc_trainers WHERE name = ?", (name,))
        existing_trainer = cursor.fetchone()
        
        if existing_trainer:
            # Update existing trainer
            cursor.execute("""
                UPDATE npc_trainers SET
                    difficulty = ?,
                    theme = ?,
                    veramon_count = ?,
                    min_level = ?,
                    max_level = ?,
                    token_reward = ?,
                    experience_reward = ?,
                    updated_at = ?
                WHERE name = ?
            """, (
                difficulty,
                theme,
                veramon_count,
                min_level,
                max_level,
                token_reward,
                experience_reward,
                datetime.utcnow().isoformat(),
                name
            ))
            
            trainer_id = existing_trainer[0]
            created = False
        else:
            # Create new trainer
            cursor.execute("""
                INSERT INTO npc_trainers (
                    name, difficulty, theme, veramon_count, min_level, max_level,
                    token_reward, experience_reward, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                difficulty,
                theme,
                veramon_count,
                min_level,
                max_level,
                token_reward,
                experience_reward,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            trainer_id = cursor.lastrowid
            created = True
        
        conn.commit()
        conn.close()
        
        # Confirmation message
        embed = discord.Embed(
            title=f"NPC Trainer {'Created' if created else 'Updated'}",
            description=f"Successfully {'created' if created else 'updated'} NPC trainer: {name}",
            color=discord.Color.green() if created else discord.Color.blue()
        )
        
        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(name="Difficulty", value=difficulty.capitalize(), inline=True)
        embed.add_field(name="Theme", value=theme.capitalize(), inline=True)
        embed.add_field(name="Team Size", value=str(veramon_count), inline=True)
        embed.add_field(name="Level Range", value=f"{min_level}-{max_level}", inline=True)
        embed.add_field(name="Rewards", value=f"{token_reward} tokens, {experience_reward} XP", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_trainer_team", description="Set a specific Veramon team for an NPC trainer (Admin only)")
    @app_commands.describe(
        trainer_name="Name of the NPC trainer",
        veramon1="First Veramon (name:level)",
        veramon2="Second Veramon (name:level)",
        veramon3="Third Veramon (name:level)",
        veramon4="Fourth Veramon (name:level)",
        veramon5="Fifth Veramon (name:level)",
        veramon6="Sixth Veramon (name:level)"
    )
    @is_admin()
    async def admin_trainer_team(
        self,
        interaction: discord.Interaction,
        trainer_name: str,
        veramon1: str,
        veramon2: str = None,
        veramon3: str = None,
        veramon4: str = None,
        veramon5: str = None,
        veramon6: str = None
    ):
        """Set a specific team for an NPC trainer."""
        # Find veramon data file (use consolidated file if available)
        data_dir = os.path.join(DATA_DIR)
        complete_file = os.path.join(data_dir, "veramon_database.json")
        
        if os.path.exists(complete_file):
            veramon_file = complete_file
        else:
            veramon_file = os.path.join(data_dir, "veramon_data.json")
        
        with open(veramon_file, 'r') as f:
            veramon_data = json.load(f)
        
        # Find the trainer
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT trainer_id FROM npc_trainers WHERE name = ?", (trainer_name,))
        trainer = cursor.fetchone()
        
        if not trainer:
            await interaction.response.send_message(
                f"Trainer '{trainer_name}' not found!",
                ephemeral=True
            )
            conn.close()
            return
            
        trainer_id = trainer[0]
        
        # Parse Veramon entries
        veramon_entries = []
        for i, veramon_str in enumerate([veramon1, veramon2, veramon3, veramon4, veramon5, veramon6]):
            if not veramon_str:
                continue
                
            try:
                if ":" in veramon_str:
                    name, level = veramon_str.split(":")
                    level = int(level)
                else:
                    name = veramon_str
                    level = 5  # Default level
                    
                name = name.strip()
                
                # Validate Veramon exists
                if name not in veramon_data:
                    await interaction.response.send_message(
                        f"Veramon '{name}' not found!",
                        ephemeral=True
                    )
                    conn.close()
                    return
                    
                # Validate level
                level = max(1, min(100, level))
                
                veramon_entries.append({
                    "name": name,
                    "level": level,
                    "position": i + 1  # 1-based position
                })
            except ValueError:
                await interaction.response.send_message(
                    f"Invalid format for Veramon {i+1}. Use 'Name:Level'.",
                    ephemeral=True
                )
                conn.close()
                return
                
        if not veramon_entries:
            await interaction.response.send_message(
                "No valid Veramon provided for the team!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Remove existing team
        cursor.execute("DELETE FROM npc_trainer_teams WHERE trainer_id = ?", (trainer_id,))
        
        # Add new team
        for entry in veramon_entries:
            cursor.execute("""
                INSERT INTO npc_trainer_teams (
                    trainer_id, veramon_name, level, position, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                trainer_id,
                entry["name"],
                entry["level"],
                entry["position"],
                datetime.utcnow().isoformat()
            ))
            
        # Update trainer's team size
        cursor.execute(
            "UPDATE npc_trainers SET veramon_count = ? WHERE trainer_id = ?",
            (len(veramon_entries), trainer_id)
        )
        
        conn.commit()
        conn.close()
        
        # Confirmation message
        embed = discord.Embed(
            title="Trainer Team Updated",
            description=f"Successfully updated team for trainer: {trainer_name}",
            color=discord.Color.green()
        )
        
        team_description = "\n".join([f"{i+1}. {entry['name']} (Level {entry['level']})" 
                                     for i, entry in enumerate(veramon_entries)])
        
        embed.add_field(name="Team", value=team_description, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_battle_test", description="Test a battle against an NPC trainer (Admin only)")
    @app_commands.describe(
        trainer_name="Name of the NPC trainer to battle"
    )
    @is_admin()
    async def admin_battle_test(
        self,
        interaction: discord.Interaction,
        trainer_name: str
    ):
        """Test a battle against an NPC trainer."""
        await interaction.response.defer(thinking=True)
        
        # Import PVE battle functionality
        from cogs.enhanced_battle_cog import EnhancedBattleCog
        
        for cog in self.bot.cogs.values():
            if isinstance(cog, EnhancedBattleCog):
                battle_cog = cog
                break
        else:
            await interaction.followup.send(
                "Enhanced Battle Cog not found! Please ensure it's properly loaded.",
                ephemeral=True
            )
            return
        
        # Find the trainer
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT trainer_id, difficulty, theme, veramon_count, min_level, max_level,
                   token_reward, experience_reward
            FROM npc_trainers
            WHERE name = ?
        """, (trainer_name,))
        
        trainer = cursor.fetchone()
        
        if not trainer:
            await interaction.followup.send(
                f"Trainer '{trainer_name}' not found!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Start battle using the enhanced_battle_cog's battle_pve functionality
        try:
            # Create a custom context for testing
            await battle_cog.battle_pve_trainer(
                interaction=interaction,
                trainer_name=trainer_name,
                is_test=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Error starting test battle: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminBattleSystemCog(bot))
