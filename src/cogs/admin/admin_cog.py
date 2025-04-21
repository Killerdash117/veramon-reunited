import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Union, Literal

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel, is_admin

# Load data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class AdminCog(commands.Cog):
    """
    Admin commands for managing Veramon Reunited.
    
    Includes commands for managing Veramon, abilities, items, and other game data.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="admin_add_veramon", description="Add a new Veramon to the game (Admin only)")
    @app_commands.describe(
        name="Name of the new Veramon",
        types="Types of the Veramon (comma-separated)",
        rarity="Rarity of the Veramon",
        evolution_from="Name of Veramon this evolves from (if any)",
        evolution_level="Level required for evolution (if applicable)",
        image_url="URL for the Veramon's image"
    )
    @is_admin()
    async def admin_add_veramon(
        self, 
        interaction: discord.Interaction, 
        name: str,
        types: str,
        rarity: str,
        evolution_from: str = None,
        evolution_level: int = None,
        image_url: str = None
    ):
        """Add a new Veramon to the game data."""
        # First, check if the Veramon already exists
        # Find veramon data file (use consolidated file if available)
        data_dir = os.path.join(DATA_DIR)
        complete_file = os.path.join(data_dir, "veramon_database.json")
        
        if os.path.exists(complete_file):
            veramon_file = complete_file
        else:
            veramon_file = os.path.join(data_dir, "veramon_data.json")
        
        with open(veramon_file, 'r') as f:
            veramon_data = json.load(f)
            
        if name in veramon_data:
            await interaction.response.send_message(
                f"A Veramon named '{name}' already exists!",
                ephemeral=True
            )
            return
            
        # Parse types
        type_list = [t.strip() for t in types.split(',')]
        
        # Create new Veramon data
        new_veramon = {
            "name": name,
            "type": type_list,
            "rarity": rarity.lower(),
            "base_stats": {
                "hp": 50,
                "attack": 50,
                "defense": 50,
                "sp_attack": 50,
                "sp_defense": 50,
                "speed": 50
            },
            "abilities": ["Tackle", "Quick Attack"],  # Default abilities
            "catch_rate": {
                "common": 45,
                "uncommon": 30,
                "rare": 15,
                "legendary": 5,
                "mythic": 1
            }.get(rarity.lower(), 30),
            "description": f"A {rarity.lower()} {'/'.join(type_list)} type Veramon."
        }
        
        # Add evolution data if provided
        if evolution_from:
            # This is an evolution of another Veramon
            # Find the base Veramon and update its evolution data
            if evolution_from in veramon_data:
                if "evolution" not in veramon_data[evolution_from]:
                    veramon_data[evolution_from]["evolution"] = {}
                
                veramon_data[evolution_from]["evolution"]["evolves_to"] = name
                veramon_data[evolution_from]["evolution"]["level_required"] = evolution_level or 20
                
                # Boost stats a bit from base form
                base_stats = veramon_data[evolution_from].get("base_stats", {})
                for stat in base_stats:
                    # Approximately 20% stat increase on evolution
                    new_veramon["base_stats"][stat] = int(base_stats.get(stat, 50) * 1.2)
            else:
                await interaction.response.send_message(
                    f"Warning: Base Veramon '{evolution_from}' not found. Creating {name} without evolution data.",
                    ephemeral=True
                )
        
        # Add image URL if provided
        if image_url:
            new_veramon["image"] = image_url
            
        # Add to Veramon data
        veramon_data[name] = new_veramon
        
        # Save updated data
        with open(veramon_file, 'w') as f:
            json.dump(veramon_data, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="New Veramon Added!",
            description=f"Successfully added {name} to the game.",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(name="Type", value="/".join(type_list), inline=True)
        embed.add_field(name="Rarity", value=rarity.capitalize(), inline=True)
        
        if evolution_from:
            embed.add_field(
                name="Evolution",
                value=f"Evolves from {evolution_from} at level {evolution_level or 20}",
                inline=False
            )
            
        if image_url:
            embed.set_thumbnail(url=image_url)
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_edit_veramon", description="Edit an existing Veramon (Admin only)")
    @app_commands.describe(
        name="Name of the Veramon to edit",
        field="Field to edit",
        value="New value for the field"
    )
    @is_admin()
    async def admin_edit_veramon(
        self,
        interaction: discord.Interaction,
        name: str,
        field: Literal["name", "type", "rarity", "hp", "attack", "defense", "sp_attack", "sp_defense", "speed", "catch_rate", "image_url", "evolution_to", "evolution_level"],
        value: str
    ):
        """Edit an existing Veramon's data."""
        # Load Veramon data
        # Find veramon data file (use consolidated file if available)
        data_dir = os.path.join(DATA_DIR)
        complete_file = os.path.join(data_dir, "veramon_database.json")
        
        if os.path.exists(complete_file):
            veramon_file = complete_file
        else:
            veramon_file = os.path.join(data_dir, "veramon_data.json")
        
        with open(veramon_file, 'r') as f:
            veramon_data = json.load(f)
            
        if name not in veramon_data:
            await interaction.response.send_message(
                f"Veramon '{name}' not found!",
                ephemeral=True
            )
            return
            
        # Edit the specified field
        veramon = veramon_data[name]
        
        if field == "name":
            # Special case: rename Veramon
            new_name = value
            if new_name in veramon_data:
                await interaction.response.send_message(
                    f"A Veramon named '{new_name}' already exists!",
                    ephemeral=True
                )
                return
                
            # Copy data to new name and delete old entry
            veramon_data[new_name] = veramon.copy()
            del veramon_data[name]
            
            # Update any evolutions that reference this Veramon
            for other_name, other_data in veramon_data.items():
                if "evolution" in other_data:
                    if other_data["evolution"].get("evolves_to") == name:
                        other_data["evolution"]["evolves_to"] = new_name
                        
            field_description = f"Changed name from '{name}' to '{new_name}'"
        elif field == "type":
            # Parse types
            veramon["type"] = [t.strip() for t in value.split(',')]
            field_description = f"Type changed to {'/'.join(veramon['type'])}"
        elif field == "rarity":
            veramon["rarity"] = value.lower()
            field_description = f"Rarity changed to {value.capitalize()}"
        elif field in ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]:
            try:
                stat_value = int(value)
                if "base_stats" not in veramon:
                    veramon["base_stats"] = {}
                veramon["base_stats"][field] = stat_value
                field_description = f"{field.capitalize()} changed to {stat_value}"
            except ValueError:
                await interaction.response.send_message(
                    f"Invalid value for {field}. Must be a number.",
                    ephemeral=True
                )
                return
        elif field == "catch_rate":
            try:
                catch_rate = int(value)
                veramon["catch_rate"] = catch_rate
                field_description = f"Catch rate changed to {catch_rate}"
            except ValueError:
                await interaction.response.send_message(
                    "Invalid catch rate. Must be a number.",
                    ephemeral=True
                )
                return
        elif field == "image_url":
            veramon["image"] = value
            field_description = "Image URL updated"
        elif field == "evolution_to":
            if value.lower() == "none":
                if "evolution" in veramon:
                    del veramon["evolution"]
                field_description = "Evolution removed"
            else:
                if value not in veramon_data:
                    await interaction.response.send_message(
                        f"Evolution target '{value}' not found!",
                        ephemeral=True
                    )
                    return
                    
                if "evolution" not in veramon:
                    veramon["evolution"] = {}
                    
                veramon["evolution"]["evolves_to"] = value
                
                # Set default evolution level if not present
                if "level_required" not in veramon["evolution"]:
                    veramon["evolution"]["level_required"] = 20
                    
                field_description = f"Evolution target set to {value}"
        elif field == "evolution_level":
            try:
                level = int(value)
                if "evolution" not in veramon:
                    await interaction.response.send_message(
                        "This Veramon doesn't have an evolution target set!",
                        ephemeral=True
                    )
                    return
                    
                veramon["evolution"]["level_required"] = level
                field_description = f"Evolution level set to {level}"
            except ValueError:
                await interaction.response.send_message(
                    "Invalid level. Must be a number.",
                    ephemeral=True
                )
                return
        else:
            await interaction.response.send_message(
                f"Unknown field: {field}",
                ephemeral=True
            )
            return
            
        # Save updated data
        with open(veramon_file, 'w') as f:
            json.dump(veramon_data, f, indent=2)
            
        # Confirmation message
        display_name = value if field == "name" else name
        embed = discord.Embed(
            title="Veramon Updated",
            description=f"Successfully updated {display_name}.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Field", value=field.capitalize(), inline=True)
        embed.add_field(name="Change", value=field_description, inline=True)
        
        # Add image if available
        if field == "name":
            image_url = veramon_data[new_name].get("image")
        else:
            image_url = veramon["image"] if "image" in veramon else None
            
        if image_url:
            embed.set_thumbnail(url=image_url)
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_add_ability", description="Add a new ability to the game (Admin only)")
    @app_commands.describe(
        name="Name of the new ability",
        ability_type="Type of the ability",
        power="Base power of the ability (0 for status moves)",
        accuracy="Accuracy of the ability (0.0-1.0)",
        effect_type="Type of special effect (if any)",
        effect_chance="Chance of the effect occurring (0.0-1.0)",
        description="Description of the ability"
    )
    @is_admin()
    async def admin_add_ability(
        self,
        interaction: discord.Interaction,
        name: str,
        ability_type: str,
        power: int,
        accuracy: float,
        effect_type: str = None,
        effect_chance: float = 0.0,
        description: str = None
    ):
        """Add a new ability to the game."""
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
            
        # Create new ability
        new_ability = {
            "type": ability_type,
            "power": power,
            "accuracy": min(1.0, max(0.0, accuracy)),
            "priority": 0,
            "description": description or f"A {ability_type}-type move."
        }
        
        # Add effect if specified
        if effect_type and effect_type.lower() != "none":
            new_ability["effect"] = {
                "type": effect_type,
                "chance": min(1.0, max(0.0, effect_chance))
            }
        else:
            new_ability["effect"] = None
            
        # Add to ability data
        ability_data[name] = new_ability
        
        # Save updated data
        with open(ability_file, 'w') as f:
            json.dump(ability_data, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="New Ability Added!",
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
            
        if effect_type and effect_type.lower() != "none":
            embed.add_field(
                name="Effect",
                value=f"{effect_type.capitalize()} ({int(effect_chance * 100)}% chance)",
                inline=True
            )
            
        if description:
            embed.add_field(name="Description", value=description, inline=False)
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_give_veramon", description="Give a Veramon to a player (Admin only)")
    @app_commands.describe(
        player="Player to give the Veramon to",
        veramon_name="Name of the Veramon to give",
        level="Level of the Veramon (1-100)",
        shiny="Whether the Veramon should be shiny",
        nickname="Nickname for the Veramon (optional)"
    )
    @is_admin()
    async def admin_give_veramon(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        veramon_name: str,
        level: int = 5,
        shiny: bool = False,
        nickname: str = None
    ):
        """Give a Veramon to a player."""
        # Load Veramon data
        # Find veramon data file (use consolidated file if available)
        data_dir = os.path.join(DATA_DIR)
        complete_file = os.path.join(data_dir, "veramon_database.json")
        
        if os.path.exists(complete_file):
            veramon_file = complete_file
        else:
            veramon_file = os.path.join(data_dir, "veramon_data.json")
        
        with open(veramon_file, 'r') as f:
            veramon_data = json.load(f)
            
        if veramon_name not in veramon_data:
            await interaction.response.send_message(
                f"Veramon '{veramon_name}' not found!",
                ephemeral=True
            )
            return
            
        # Validate level
        level = max(1, min(100, level))
        
        # Add to player's captures
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if player exists in users table
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (str(player.id),))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (user_id, tokens, xp, created_at) VALUES (?, 0, 0, ?)",
                (str(player.id), datetime.utcnow().isoformat())
            )
            
        # Calculate XP based on level
        xp = 0
        for i in range(1, level):
            xp += i * 100
            
        # Add the Veramon to captures
        cursor.execute("""
            INSERT INTO captures (
                user_id, veramon_name, caught_at, shiny, biome, nickname, level, experience
            ) VALUES (?, ?, ?, ?, 'admin', ?, ?, ?)
        """, (
            str(player.id),
            veramon_name,
            datetime.utcnow().isoformat(),
            1 if shiny else 0,
            nickname,
            level,
            xp
        ))
        
        capture_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Confirmation message
        veramon = veramon_data[veramon_name]
        embed = discord.Embed(
            title="Veramon Given!",
            description=f"Successfully gave a {veramon_name} to {player.display_name}.",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Name", value=nickname or veramon_name, inline=True)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Shiny", value="Yes" if shiny else "No", inline=True)
        embed.add_field(name="ID", value=str(capture_id), inline=True)
        
        # Add type and rarity
        embed.add_field(name="Type", value="/".join(veramon.get("type", ["Normal"])), inline=True)
        embed.add_field(name="Rarity", value=veramon.get("rarity", "common").capitalize(), inline=True)
        
        # Add image if available
        image_key = "shiny_image" if shiny and "shiny_image" in veramon else "image"
        if image_key in veramon:
            embed.set_thumbnail(url=veramon[image_key])
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="admin_spawn_rate", description="Adjust spawn rates for a biome (Admin only)")
    @app_commands.describe(
        biome="Biome to adjust spawn rates for",
        rarity="Rarity tier to adjust",
        percentage="New percentage for this rarity tier (0-100)"
    )
    @is_admin()
    async def admin_spawn_rate(
        self,
        interaction: discord.Interaction,
        biome: str,
        rarity: Literal["common", "uncommon", "rare", "legendary", "mythic"],
        percentage: float
    ):
        """Adjust spawn rates for a biome."""
        # Load biome data
        biome_file = os.path.join(DATA_DIR, "biomes.json")
        
        with open(biome_file, 'r') as f:
            biome_data = json.load(f)
            
        # Check if biome exists
        if biome not in biome_data:
            await interaction.response.send_message(
                f"Biome '{biome}' not found!",
                ephemeral=True
            )
            return
            
        # Validate percentage
        percentage = max(0, min(100, percentage))
        
        # Update spawn rate
        if "spawn_weights" not in biome_data[biome]:
            biome_data[biome]["spawn_weights"] = {
                "common": 70,
                "uncommon": 20,
                "rare": 9,
                "legendary": 1,
                "mythic": 0.1
            }
            
        biome_data[biome]["spawn_weights"][rarity] = percentage
        
        # Save updated data
        with open(biome_file, 'w') as f:
            json.dump(biome_data, f, indent=2)
            
        # Confirmation message
        embed = discord.Embed(
            title="Spawn Rate Updated",
            description=f"Successfully updated spawn rates for {biome}.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Biome", value=biome_data[biome].get("name", biome), inline=True)
        embed.add_field(name="Rarity", value=rarity.capitalize(), inline=True)
        embed.add_field(name="New Rate", value=f"{percentage}%", inline=True)
        
        # Show current weights
        weights = biome_data[biome]["spawn_weights"]
        weights_text = "\n".join([f"{r.capitalize()}: {weights.get(r, 0)}%" for r in ["common", "uncommon", "rare", "legendary", "mythic"]])
        
        embed.add_field(name="Current Weights", value=weights_text, inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
