import json
import os
import random
from datetime import datetime
import time
from enum import Enum

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import weighted_choice
from utils.data_loader import load_all_veramon_data, load_biomes_data, load_items_data
from db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel
from src.models.veramon import Veramon

# Rarity spawn weights
RARITY_WEIGHTS = {
    "common": 60,
    "uncommon": 30,
    "rare": 10,
    "legendary": 1,
    "mythic": 0.1
}

# Experience points gained from catching a Veramon
CATCH_XP = {
    "common": 20,
    "uncommon": 40,
    "rare": 80,
    "legendary": 160,
    "mythic": 320
}

class WeatherType(Enum):
    SUNNY = "sunny"
    RAINY = "rainy"
    FOGGY = "foggy"
    WINDY = "windy"
    SNOWY = "snowy"
    STORMY = "stormy"
    THUNDERSTORM = "thunderstorm"

class TimeOfDay(Enum):
    MORNING = "morning"
    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"

class CatchingCog(commands.Cog):
    """Handles exploring biomes and catching wild Veramon."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Load veramon and biome data using the new data loader
        self.veramon_data = load_all_veramon_data()
        self.biomes = load_biomes_data()
        self.items = load_items_data()
        self.last_spawn = {}
        self.spawn_cooldowns = {}
        self.cooldown_seconds = 30  # 30 seconds between spawns per user
        self.current_weather = {}  # Tracks current weather for each biome
        self.last_weather_update = 0  # Timestamp of last weather update
        self.weather_update_interval = 3600  # Update weather every hour
        self.unlocked_special_areas = {}  # Tracks unlocked special areas per user

    def _get_current_time_of_day(self):
        """Get the current time of day based on real-world time."""
        hour = datetime.now().hour
        
        if 5 <= hour < 11:
            return TimeOfDay.MORNING
        elif 11 <= hour < 17:
            return TimeOfDay.DAY
        elif 17 <= hour < 21:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT
    
    def _update_weather(self):
        """Update weather conditions for all biomes."""
        current_time = time.time()
        
        # Only update if enough time has passed since last update
        if current_time - self.last_weather_update < self.weather_update_interval:
            return
            
        self.last_weather_update = current_time
        
        # Update weather for each biome
        for biome_key, biome_data in self.biomes.items():
            weather_effects = biome_data.get('weather_effects', {})
            
            if not weather_effects:
                self.current_weather[biome_key] = None
                continue
                
            # Get possible weather types for this biome
            possible_weather = list(weather_effects.keys())
            
            # Select random weather with different weights
            # More common weather types would have higher probability
            weather_weights = {
                WeatherType.SUNNY.value: 40,
                WeatherType.RAINY.value: 25,
                WeatherType.FOGGY.value: 15,
                WeatherType.WINDY.value: 15,
                WeatherType.SNOWY.value: 5,
                WeatherType.STORMY.value: 5,
                WeatherType.THUNDERSTORM.value: 2
            }
            
            # Filter weights to only include weather types available for this biome
            available_weather = [(w, weather_weights.get(w, 1)) for w in possible_weather]
            
            if available_weather:
                self.current_weather[biome_key] = weighted_choice(available_weather)
            else:
                self.current_weather[biome_key] = None
    
    def _get_user_unlocked_areas(self, user_id: str):
        """Get special areas unlocked by a user."""
        if user_id not in self.unlocked_special_areas:
            # In a real implementation, this would load from database
            # For now, we'll initialize with a default empty set
            self.unlocked_special_areas[user_id] = set()
            
        return self.unlocked_special_areas[user_id]
    
    def _check_special_area_access(self, user_id: str, biome_key: str, area_id: str):
        """Check if a user has access to a special area."""
        if biome_key not in self.biomes:
            return False
            
        biome_data = self.biomes[biome_key]
        special_areas = biome_data.get('special_areas', [])
        
        for area in special_areas:
            if area.get('id') == area_id:
                # Check if already unlocked
                if area_id in self._get_user_unlocked_areas(user_id):
                    return True
                    
                # Check unlock requirements
                requirement = area.get('unlock_requirement', {})
                req_type = requirement.get('type')
                
                if req_type == 'achievement':
                    # Check if user has the required achievement
                    # This would need to query the achievement system
                    req_id = requirement.get('id')
                    # achievement_unlocked = self.bot.get_cog('AchievementCog').has_achievement(user_id, req_id)
                    # For now, we'll return False as we haven't implemented the achievement check yet
                    return False
                elif req_type == 'quest':
                    # Check if user has completed the required quest
                    # This would need to query the quest system
                    req_id = requirement.get('id')
                    # quest_completed = self.bot.get_cog('QuestCog').is_quest_completed(user_id, req_id)
                    # For now, we'll return False as we haven't implemented the quest check yet
                    return False
                elif req_type == 'level':
                    # Check if user has reached the required level
                    # This would need to query the user's level
                    req_value = requirement.get('value', 0)
                    # user_level = self.bot.get_cog('ProfileCog').get_user_level(user_id)
                    # For now, we'll return False as we haven't implemented the level check yet
                    return False
                    
        return False
    
    def _unlock_special_area(self, user_id: str, area_id: str):
        """Unlock a special area for a user."""
        self._get_user_unlocked_areas(user_id).add(area_id)
    
    @app_commands.command(name='explore', description='Explore a biome to encounter wild Veramon.')
    @app_commands.describe(
        biome='Name of the biome to explore.',
        special_area='Optional special area within the biome to explore.'
    )
    @require_permission_level(PermissionLevel.USER)
    async def explore(self, interaction: discord.Interaction, biome: str, special_area: str = None):
        """Explore a biome and encounter a wild Veramon."""
        user_id = str(interaction.user.id)
        
        # Check cooldown
        current_time = datetime.utcnow().timestamp()
        if user_id in self.spawn_cooldowns:
            time_diff = current_time - self.spawn_cooldowns[user_id]
            if time_diff < self.cooldown_seconds:
                remaining = int(self.cooldown_seconds - time_diff)
                await interaction.response.send_message(
                    f"You need to wait {remaining} seconds before exploring again.",
                    ephemeral=True
                )
                return
            
        # Set cooldown
        self.spawn_cooldowns[user_id] = current_time
        
        biome_key = biome.lower()
        if biome_key not in self.biomes:
            await interaction.response.send_message(f"Biome '{biome}' not found.", ephemeral=True)
            return
        
        # Update weather if needed
        self._update_weather()
        
        # Get current weather and time of day
        current_weather = self.current_weather.get(biome_key)
        time_of_day = self._get_current_time_of_day()
        
        # Main biome data
        biome_data = self.biomes[biome_key]
        
        # Update quest progress for exploration
        quest_cog = self.bot.get_cog("QuestCog")
        if quest_cog:
            try:
                metadata = {
                    "biome": biome_key,
                    "special_area": special_area,
                    "weather": current_weather,
                    "time_of_day": time_of_day.value
                }
                quest_cog.update_quest_progress(user_id, "EXPLORE", 1, metadata)
            except Exception as e:
                print(f"Error updating quest progress: {e}")
        
        # Handle special area if specified
        if special_area:
            area_id = special_area.lower().replace(' ', '_')
            has_access = self._check_special_area_access(user_id, biome_key, area_id)
            
            if not has_access:
                await interaction.response.send_message(
                    f"You don't have access to the {special_area} area yet. "
                    f"Complete the required achievement or quest to unlock it.",
                    ephemeral=True
                )
                return
                
            # Find the special area data
            special_area_data = None
            for area in biome_data.get('special_areas', []):
                if area.get('id') == area_id:
                    special_area_data = area
                    break
                    
            if not special_area_data:
                await interaction.response.send_message(
                    f"Special area '{special_area}' not found in {biome}.",
                    ephemeral=True
                )
                return
                
            # Use the special area's spawn table instead of the biome's
            spawn_table = special_area_data.get('spawn_table', {})
            encounter_rate_modifier = special_area_data.get('encounter_rate', 1.0)
            area_name = special_area_data.get('name', special_area)
            area_desc = special_area_data.get('description', '')
            area_image = special_area_data.get('image')
        else:
            # Use the biome's regular spawn table
            spawn_table = biome_data.get('spawn_table', {})
            encounter_rate_modifier = 1.0
            area_name = biome_data.get('name', biome)
            area_desc = biome_data.get('description', '')
            area_image = biome_data.get('image')
        
        # Apply weather effects to encounter rate and spawn tables
        if current_weather and current_weather in biome_data.get('weather_effects', {}):
            weather_data = biome_data['weather_effects'][current_weather]
            encounter_rate_modifier *= weather_data.get('encounter_rate', 1.0)
            weather_desc = weather_data.get('description', f"Current weather: {current_weather}")
            
            # Apply type spawn modifiers from weather
            spawn_modifiers = weather_data.get('spawn_modifiers', {})
        else:
            weather_desc = "Weather: Clear"
            spawn_modifiers = {}
            
        # Apply time of day effects
        if time_of_day.value in biome_data.get('time_effects', {}):
            time_data = biome_data['time_effects'][time_of_day.value]
            time_desc = time_data.get('description', f"Time: {time_of_day.name.title()}")
            
            # Combine time-based spawn modifiers with weather modifiers
            time_modifiers = time_data.get('spawn_modifiers', {})
            for type_name, modifier in time_modifiers.items():
                if type_name in spawn_modifiers:
                    # Combine modifiers multiplicatively
                    spawn_modifiers[type_name] *= modifier
                else:
                    spawn_modifiers[type_name] = modifier
        else:
            time_desc = f"Time: {time_of_day.name.title()}"
        
        # Random chance to not encounter anything based on encounter rate
        base_encounter_chance = 0.8  # 80% base chance to encounter something
        modified_chance = base_encounter_chance * encounter_rate_modifier
        
        if random.random() > modified_chance:
            embed = discord.Embed(
                title=f"Exploring {area_name}",
                description=f"You searched the area but didn't find any Veramon.\n\n{weather_desc}\n{time_desc}",
                color=discord.Color.from_rgb(100, 100, 100)
            )
            
            if area_image:
                embed.set_thumbnail(url=area_image)
                
            await interaction.response.send_message(embed=embed)
            return
        
        # Build choices list from spawn table with proper weights
        choices = []
        for rarity, names in spawn_table.items():
            weight = RARITY_WEIGHTS.get(rarity.lower(), 1)
            for name in names:
                if name in self.veramon_data:
                    veramon_types = self.veramon_data[name].get('type', [])
                    
                    # Apply type-based spawn modifiers from weather and time
                    type_modifier = 1.0
                    for vtype in veramon_types:
                        if vtype in spawn_modifiers:
                            type_modifier *= spawn_modifiers[vtype]
                    
                    adjusted_weight = weight * type_modifier
                    choices.append((name, adjusted_weight))
        
        if not choices:
            await interaction.response.send_message(
                f"No creatures to spawn in {area_name}.",
                ephemeral=True
            )
            return
            
        chosen = weighted_choice(choices)
        data = self.veramon_data.get(chosen)
        
        if not data:
            await interaction.response.send_message(
                f"Data for '{chosen}' not found.",
                ephemeral=True
            )
            return
            
        # Increased shiny chance during certain weather
        shiny_modifier = 1.0
        if current_weather == WeatherType.THUNDERSTORM.value:
            shiny_modifier = 2.0  # Double shiny chance during thunderstorms
        
        shiny = random.random() < (data.get('shiny_rate', 0) * shiny_modifier)
        
        # Create encounter embed
        embed = discord.Embed(
            title='Wild Veramon Encounter!',
            description=f"You encountered a wild {chosen} in the {area_name}!\n\n{weather_desc}\n{time_desc}",
            color=0x1abc9c
        )
        
        # Determine display image
        image_url = None
        if shiny and 'shiny_image' in data:
            image_url = data['shiny_image']
        elif 'image' in data:
            image_url = data['image']
            
        if image_url:
            embed.set_thumbnail(url=image_url)
            
        embed.add_field(name='Name', value=('✨ ' if shiny else '') + data['name'], inline=True)
        embed.add_field(name='Type', value=', '.join(data.get('type', [])), inline=True)
        embed.add_field(name='Rarity', value=data.get('rarity', '').capitalize(), inline=True)
        embed.add_field(name='Catch Rate', value=str(data.get('catch_rate', 0)), inline=True)
        
        # Show base stats
        stats = data.get('base_stats', {})
        stats_text = f"HP: {stats.get('hp', 0)} | ATK: {stats.get('atk', 0)} | DEF: {stats.get('def', 0)}"
        if 'sp_atk' in stats:
            stats_text += f" | SP.ATK: {stats.get('sp_atk', 0)} | SP.DEF: {stats.get('sp_def', 0)}"
        if 'speed' in stats:
            stats_text += f" | SPD: {stats.get('speed', 0)}"
        embed.add_field(name='Stats', value=stats_text, inline=False)
        
        embed.add_field(name='Flavor', value=data.get('flavor', ''), inline=False)
        
        # Get user's inventory for convenience
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0", (str(user_id),))
        inventory = cursor.fetchall()
        conn.close()
        
        # Show inventory hint
        if inventory:
            items_text = ", ".join([f"`{item_id}` ({qty})" for item_id, qty in inventory])
            footer_text = f"Your items: {items_text}\nUse /catch item:<item_id> to attempt capture."
        else:
            footer_text = "You have no catch items! Buy some with /shop_buy or use /catch item:standard_capsule"
            
        embed.set_footer(text=footer_text)
        
        # Save spawn state
        self.last_spawn[user_id] = {'name': chosen, 'shiny': shiny, 'biome': biome_key}
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='catch', description='Attempt to catch a wild Veramon.')
    @app_commands.describe(item='The item to use for catching (e.g., "basic_ball")')
    @require_permission_level(PermissionLevel.USER)
    async def catch(self, interaction: discord.Interaction, item: str):
        """Attempt to catch the last encountered Veramon using an item."""
        user_id = interaction.user.id
        spawn = self.last_spawn.pop(user_id, None)
        if not spawn:
            await interaction.response.send_message('No active encounter. Use /explore <biome> first.', ephemeral=True)
            return
        # Load item data
        info = self.items.get(item)
        if not info:
            await interaction.response.send_message(f"Item '{item}' not found.", ephemeral=True)
            return
        
        # Check if user has the item
        conn = get_connection()
        cursor = conn.cursor()
        
        # For standard_capsule, we'll always allow it even if not in inventory
        if item != "standard_capsule":
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (str(user_id), item))
            inventory_item = cursor.fetchone()
            
            if not inventory_item or inventory_item[0] <= 0:
                await interaction.response.send_message(f"You don't have any `{item}` in your inventory!", ephemeral=True)
                conn.close()
                return
                
            # Decrease quantity
            new_quantity = inventory_item[0] - 1
            cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?", 
                         (new_quantity, str(user_id), item))
        
        mult = info.get('multiplier', 1.0)
        base_rate = self.veramon_data[spawn['name']].get('catch_rate', 0)
        chance = min(1.0, base_rate * mult)
        success = random.random() < chance
        if success:
            # Find the next available slot for the Veramon
            cursor.execute("SELECT MAX(id) FROM captures")
            max_id = cursor.fetchone()[0]
            next_id = 1 if max_id is None else max_id + 1
            
            # Insert the capture
            cursor.execute(
                "INSERT INTO captures (user_id, veramon_name, caught_at, shiny, biome, active_form) VALUES (?, ?, ?, ?, ?, ?)" ,
                (str(user_id), spawn['name'], datetime.utcnow().isoformat(), int(spawn['shiny']), spawn['biome'], None)
            )
            
            # Grant XP to the user
            rarity = self.veramon_data[spawn['name']].get('rarity', 'common')
            xp_gain = CATCH_XP.get(rarity, 20)
            if spawn['shiny']:
                xp_gain *= 5  # 5x XP for shiny catches
                
            # Update user XP or create user entry if none exists
            cursor.execute("SELECT xp FROM users WHERE user_id = ?", (str(user_id),))
            user_row = cursor.fetchone()
            
            if user_row:
                new_xp = user_row[0] + xp_gain
                cursor.execute("UPDATE users SET xp = ? WHERE user_id = ?", (new_xp, str(user_id)))
            else:
                cursor.execute("INSERT INTO users (user_id, tokens, xp) VALUES (?, ?, ?)", 
                             (str(user_id), 0, xp_gain))
                new_xp = xp_gain
                
            conn.commit()
            
            result_msg = f"You caught {'✨ ' if spawn['shiny'] else ''}{spawn['name']}! 🎉"
            color = discord.Color.green()
            
            # Add XP info to result
            result_msg += f"\nGained {xp_gain} XP! (Total: {new_xp} XP)"
        else:
            conn.commit()  # Commit inventory change even on failed catch
            result_msg = f"You failed to catch {spawn['name']}. Better luck next time! 🤕"
            color = discord.Color.red()
        
        conn.close()
        
        # Update quest progress for catch
        quest_cog = self.bot.get_cog("QuestCog")
        if quest_cog:
            try:
                metadata = {
                    "veramon_name": spawn['name'],
                    "veramon_type": ", ".join(self.veramon_data[spawn['name']].get("type", [])),
                    "rarity": self.veramon_data[spawn['name']].get("rarity", "common"),
                    "shiny": spawn['shiny']
                }
                quest_cog.update_quest_progress(str(user_id), "CATCH", 1, metadata)
            except Exception as e:
                print(f"Error updating quest progress: {e}")
        
        embed = discord.Embed(title='Catch Attempt Result', description=result_msg, color=color)
        embed.add_field(name='Item', value=info.get('name', item), inline=True)
        embed.add_field(name='Chance', value=f"{chance*100:.1f}%", inline=True)
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='nickname', description='Give a nickname to one of your captured Veramon')
    @app_commands.describe(capture_id='ID of the captured Veramon', nickname='New nickname to give (none to reset)')
    @require_permission_level(PermissionLevel.USER)
    async def nickname(self, interaction: discord.Interaction, capture_id: int, nickname: str = None):
        """Change the nickname of a captured Veramon."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if the capture exists and belongs to the user
        cursor.execute(
            "SELECT veramon_name, shiny FROM captures WHERE id = ? AND user_id = ?", 
            (capture_id, user_id)
        )
        
        capture = cursor.fetchone()
        if not capture:
            await interaction.response.send_message(
                f"No Veramon found with ID {capture_id} that belongs to you.",
                ephemeral=True
            )
            conn.close()
            return
            
        veramon_name, is_shiny = capture
        
        # Update nickname
        cursor.execute(
            "UPDATE captures SET nickname = ? WHERE id = ?",
            (nickname, capture_id)
        )
        
        conn.commit()
        conn.close()
        
        if nickname:
            embed = discord.Embed(
                title="Nickname Set!",
                description=f"Your {'✨ ' if is_shiny else ''}{veramon_name} is now nicknamed **{nickname}**!",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="Nickname Removed",
                description=f"Your {'✨ ' if is_shiny else ''}{veramon_name} no longer has a nickname.",
                color=discord.Color.blue()
            )
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='collection', description='View your Veramon collection')
    @require_permission_level(PermissionLevel.USER)
    async def collection(self, interaction: discord.Interaction):
        """View your collection of captured Veramon."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all user's captures
        cursor.execute("""
            SELECT id, veramon_name, caught_at, shiny, biome, nickname, level
            FROM captures
            WHERE user_id = ?
            ORDER BY level DESC, id DESC
        """, (user_id,))
        
        captures = cursor.fetchall()
        conn.close()
        
        if not captures:
            await interaction.response.send_message(
                "You haven't caught any Veramon yet! Use `/explore` to find wild Veramon.",
                ephemeral=True
            )
            return
            
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Collection",
            description=f"You have {len(captures)} Veramon in your collection!",
            color=discord.Color.purple()
        )
        
        # Split into pages for long collections
        page_size = 15
        collection_list = []
        
        for i, (capture_id, name, caught_at, is_shiny, biome, nickname, level) in enumerate(captures):
            if i >= page_size:
                collection_list.append(f"... and {len(captures) - page_size} more.")
                break
                
            display_name = f"**{nickname}** ({name})" if nickname else f"**{name}**"
            if is_shiny:
                display_name = f"✨ {display_name}"
                
            level_str = f"Lv.{level}" if level else "Lv.1"
            date_str = datetime.fromisoformat(caught_at).strftime("%Y-%m-%d")
            
            collection_list.append(f"{capture_id}. {level_str} {display_name} - Caught: {date_str} in {biome}")
            
        embed.add_field(name="Your Veramon", value="\n".join(collection_list), inline=False)
        embed.set_footer(text="Use /nickname to name your Veramon | Use /battle_wild to train them")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='veramon_details', description='View details about a specific captured Veramon')
    @app_commands.describe(capture_id='ID of the captured Veramon to view details for')
    @require_permission_level(PermissionLevel.USER)
    async def veramon_details(self, interaction: discord.Interaction, capture_id: int):
        """View detailed information about a specific captured Veramon."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get capture details
        cursor.execute("""
            SELECT veramon_name, caught_at, shiny, biome, nickname, level, experience, active
            FROM captures
            WHERE id = ? AND user_id = ?
        """, (capture_id, user_id))
        
        capture = cursor.fetchone()
        conn.close()
        
        if not capture:
            await interaction.response.send_message(
                f"No Veramon found with ID {capture_id} that belongs to you.",
                ephemeral=True
            )
            return
            
        name, caught_at, is_shiny, biome, nickname, level, exp, is_active = capture
        level = level or 1
        exp = exp or 0
        
        # Get Veramon data
        if name not in self.veramon_data:
            await interaction.response.send_message(
                f"Error: Data for {name} is missing from the global database.",
                ephemeral=True
            )
            return
            
        veramon_data = self.veramon_data[name]
        
        # Create Veramon instance to calculate stats
        veramon = Veramon(name, veramon_data, level, bool(is_shiny), nickname, exp, capture_id)
        
        # Check if it can evolve
        can_evolve, evolves_to = veramon.can_evolve()
        
        # Create embed
        display_name = nickname if nickname else name
        title = f"{'✨ ' if is_shiny else ''}{display_name} (ID: {capture_id})"
        
        embed = discord.Embed(
            title=title,
            description=veramon_data.get('flavor', 'No description available.'),
            color=discord.Color.gold() if is_shiny else discord.Color.blue()
        )
        
        # Add basic info
        embed.add_field(name="Species", value=name, inline=True)
        embed.add_field(name="Type", value=" / ".join(veramon_data.get('type', ['Normal'])), inline=True)
        embed.add_field(name="Rarity", value=veramon_data.get('rarity', 'Common').capitalize(), inline=True)
        
        # Add stats
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{exp}/100", inline=True)
        embed.add_field(name="Active", value="Yes" if is_active else "No", inline=True)
        
        # Stats table
        stats = [
            f"HP: {veramon.max_hp}",
            f"Attack: {veramon.attack}",
            f"Defense: {veramon.defense}"
        ]
        
        if hasattr(veramon, 'special_attack'):
            stats.extend([
                f"Sp. Attack: {veramon.special_attack}",
                f"Sp. Defense: {veramon.special_defense}",
                f"Speed: {veramon.speed}"
            ])
            
        embed.add_field(name="Stats", value="\n".join(stats), inline=False)
        
        # Evolution info
        if can_evolve:
            embed.add_field(
                name="Evolution", 
                value=f"Ready to evolve into **{evolves_to}**!\nUse `/evolve {capture_id}` to evolve.",
                inline=False
            )
        elif evolves_to:
            required_level = veramon_data.get('evolution', {}).get('level_required', 0)
            embed.add_field(
                name="Evolution",
                value=f"Will evolve into **{evolves_to}** at level {required_level}.",
                inline=False
            )
        
        # Abilities
        abilities = veramon_data.get('abilities', [])
        if abilities:
            embed.add_field(name="Abilities", value=", ".join(abilities), inline=False)
            
        # Capture info
        date_str = datetime.fromisoformat(caught_at).strftime("%Y-%m-%d %H:%M")
        embed.set_footer(text=f"Caught on {date_str} in {biome}")
        
        # Set image if available
        if is_shiny and 'shiny_image' in veramon_data:
            embed.set_thumbnail(url=veramon_data['shiny_image'])
        elif 'image' in veramon_data:
            embed.set_thumbnail(url=veramon_data['image'])
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='evolve', description='Evolve an eligible Veramon')
    @app_commands.describe(capture_id='ID of the captured Veramon to evolve')
    @require_permission_level(PermissionLevel.USER)
    async def evolve(self, interaction: discord.Interaction, capture_id: int):
        """Evolve a Veramon that has reached the required evolution level."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get capture details
        cursor.execute("""
            SELECT veramon_name, shiny, nickname, level
            FROM captures
            WHERE id = ? AND user_id = ?
        """, (capture_id, user_id))
        
        capture = cursor.fetchone()
        
        if not capture:
            await interaction.response.send_message(
                f"No Veramon found with ID {capture_id} that belongs to you.",
                ephemeral=True
            )
            conn.close()
            return
            
        name, is_shiny, nickname, level = capture
        
        # Get Veramon data
        if name not in self.veramon_data:
            await interaction.response.send_message(
                f"Error: Data for {name} is missing from the global database.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Create Veramon instance to check evolution eligibility
        veramon = Veramon(name, data=self.veramon_data[name], level=level, shiny=is_shiny, nickname=nickname)
        can_evolve, evolves_to = veramon.can_evolve()
        
        if not can_evolve:
            # Check evolution paths for more specific requirements
            evolution_data = self.veramon_data[name].get('evolution', {})
            evolution_paths = evolution_data.get("paths", [])
            
            if not evolution_paths:
                await interaction.response.send_message(
                    f"{name} doesn't have an evolution.",
                    ephemeral=True
                )
                conn.close()
                return
            
            # List all possible evolution paths
            embed = discord.Embed(
                title="Evolution Requirements",
                description=f"**{name}** can evolve, but additional requirements must be met:",
                color=discord.Color.blue()
            )
            
            for i, path in enumerate(evolution_paths, 1):
                evolves_to = path.get("evolves_to", "Unknown")
                requirements = []
                
                if "level_required" in path:
                    requirements.append(f"Level {path['level_required']} (Current: {level})")
                
                if "required_item" in path:
                    requirements.append(f"Item: {path['required_item']}")
                
                if "biome_requirement" in path:
                    requirements.append(f"Biome: {path['biome_requirement']}")
                
                if "time_requirement" in path:
                    requirements.append(f"Time: {path['time_requirement']}")
                
                if "friendship_required" in path:
                    requirements.append(f"Friendship: {path['friendship_required']}")
                
                req_text = "\n".join([f"• {req}" for req in requirements])
                embed.add_field(
                    name=f"Evolution Path {i}: {evolves_to}",
                    value=req_text or "No additional requirements",
                    inline=False
                )
            
            if is_shiny and 'shiny_image' in self.veramon_data[name]:
                embed.set_thumbnail(url=self.veramon_data[name]['shiny_image'])
            elif 'image' in self.veramon_data[name]:
                embed.set_thumbnail(url=self.veramon_data[name]['image'])
            
            await interaction.response.send_message(embed=embed)
            conn.close()
            return
        
        # All checks passed, evolve the Veramon
        cursor.execute(
            "UPDATE captures SET veramon_name = ? WHERE id = ?",
            (evolves_to, capture_id)
        )
        
        conn.commit()
        conn.close()
        
        # Update quest progress for evolution
        quest_cog = self.bot.get_cog("QuestCog")
        if quest_cog:
            try:
                metadata = {
                    "veramon_name": name,
                    "evolved_to": evolves_to,
                    "from_type": ", ".join(self.veramon_data[name].get("type", [])),
                    "to_type": ", ".join(self.veramon_data.get(evolves_to, {}).get("type", [])),
                }
                quest_cog.update_quest_progress(user_id, "EVOLUTION", 1, metadata)
            except Exception as e:
                print(f"Error updating quest progress: {e}")
        
        # Create evolution message
        display_name = nickname if nickname else name
        evolved_name = nickname if nickname else evolves_to
        
        embed = discord.Embed(
            title="Evolution Complete!",
            description=f"{'✨ ' if is_shiny else ''}{display_name} has evolved into **{evolved_name}**!",
            color=discord.Color.purple()
        )
        
        # Add evolved Veramon data if available
        if evolves_to in self.veramon_data:
            evolved_data = self.veramon_data[evolves_to]
            
            embed.add_field(name="Type", value=" / ".join(evolved_data.get('type', ['Normal'])), inline=True)
            embed.add_field(name="Abilities", value=", ".join(evolved_data.get('abilities', ['None'])), inline=False)
            
            if is_shiny and 'shiny_image' in evolved_data:
                embed.set_thumbnail(url=evolved_data['shiny_image'])
            elif 'image' in evolved_data:
                embed.set_thumbnail(url=evolved_data['image'])
                
        embed.set_footer(text="Use /veramon_details to see the new stats!")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='transform', description='Transform your Veramon into a special form')
    @app_commands.describe(
        capture_id='ID of the captured Veramon to transform',
        form_id='ID of the form to transform into'
    )
    @require_permission_level(PermissionLevel.USER)
    async def transform(self, interaction: discord.Interaction, capture_id: int, form_id: str = None):
        """Transform a Veramon into a special form if requirements are met."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get capture details
        cursor.execute("""
            SELECT veramon_name, shiny, nickname, level, 
                   COALESCE(active_form, '') as active_form
            FROM captures
            WHERE id = ? AND user_id = ?
        """, (capture_id, user_id))
        
        capture = cursor.fetchone()
        
        if not capture:
            await interaction.response.send_message(
                f"No Veramon found with ID {capture_id} that belongs to you.",
                ephemeral=True
            )
            conn.close()
            return
            
        name, is_shiny, nickname, level, active_form = capture
        
        # Get Veramon data
        if name not in self.veramon_data:
            await interaction.response.send_message(
                f"Error: Data for {name} is missing from the global database.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Create Veramon instance
        veramon = Veramon(name, data=self.veramon_data[name], level=level, shiny=is_shiny, nickname=nickname)
        veramon.active_form = active_form if active_form else None
        
        # If no form_id provided, list available forms
        if not form_id:
            available_forms = veramon.get_available_forms()
            
            if not available_forms:
                await interaction.response.send_message(
                    f"{name} doesn't have any special forms available.",
                    ephemeral=True
                )
                conn.close()
                return
            
            embed = discord.Embed(
                title="Available Forms",
                description=f"**{nickname or name}** can transform into the following forms:",
                color=discord.Color.gold()
            )
            
            for form in available_forms:
                form_name = form.get("name", "Unknown Form")
                form_id = form.get("id", "unknown")
                form_desc = form.get("description", "No description available.")
                
                embed.add_field(
                    name=form_name,
                    value=f"**ID:** {form_id}\n{form_desc}",
                    inline=False
                )
            
            # Show current form if active
            if veramon.active_form:
                embed.set_footer(text=f"Current form: {veramon.active_form}")
            
            # Set thumbnail based on active form or default
            if is_shiny and 'shiny_image' in self.veramon_data[name]:
                embed.set_thumbnail(url=self.veramon_data[name]['shiny_image'])
            elif 'image' in self.veramon_data[name]:
                embed.set_thumbnail(url=self.veramon_data[name]['image'])
            
            await interaction.response.send_message(embed=embed)
            conn.close()
            return
        
        # Attempt to transform to the specified form
        success = veramon.transform_to_form(form_id)
        
        if not success:
            await interaction.response.send_message(
                f"Unable to transform {nickname or name} into the {form_id} form. "
                f"Requirements may not be met or the form doesn't exist.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Update the database with the new form
        cursor.execute(
            "UPDATE captures SET active_form = ? WHERE id = ?",
            (form_id, capture_id)
        )
        
        conn.commit()
        conn.close()
        
        # Find form details to display
        form_name = form_id
        form_description = "Special form"
        for form in veramon.get_available_forms():
            if form.get("id") == form_id:
                form_name = form.get("name", form_id)
                form_description = form.get("description", "Special form")
                break
        
        # Create transformation message
        display_name = nickname if nickname else name
        
        embed = discord.Embed(
            title="Transformation Complete!",
            description=f"{'✨ ' if is_shiny else ''}{display_name} has transformed into **{form_name}**!",
            color=discord.Color.teal()
        )
        
        embed.add_field(name="Form Description", value=form_description, inline=False)
        
        # Use form image if available
        form_image = None
        for form in self.veramon_data[name].get("forms", []):
            if form.get("id") == form_id:
                form_image = form.get("image")
                if is_shiny:
                    form_image = form.get("shiny_image", form_image)
                break
        
        if form_image:
            embed.set_thumbnail(url=form_image)
        elif is_shiny and 'shiny_image' in self.veramon_data[name]:
            embed.set_thumbnail(url=self.veramon_data[name]['shiny_image'])
        elif 'image' in self.veramon_data[name]:
            embed.set_thumbnail(url=self.veramon_data[name]['image'])
        
        embed.set_footer(text="Use /veramon_details to see the new stats!")
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='revert_form', description='Revert your Veramon to its normal form')
    @app_commands.describe(capture_id='ID of the captured Veramon to revert')
    @require_permission_level(PermissionLevel.USER)
    async def revert_form(self, interaction: discord.Interaction, capture_id: int):
        """Revert a Veramon from a special form to its normal form."""
        user_id = str(interaction.user.id)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get capture details
        cursor.execute("""
            SELECT veramon_name, shiny, nickname, active_form
            FROM captures
            WHERE id = ? AND user_id = ?
        """, (capture_id, user_id))
        
        capture = cursor.fetchone()
        
        if not capture:
            await interaction.response.send_message(
                f"No Veramon found with ID {capture_id} that belongs to you.",
                ephemeral=True
            )
            conn.close()
            return
            
        name, is_shiny, nickname, active_form = capture
        
        if not active_form:
            await interaction.response.send_message(
                f"{nickname or name} is not currently in a special form.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Update the database to remove the form
        cursor.execute(
            "UPDATE captures SET active_form = NULL WHERE id = ?",
            (capture_id,)
        )
        
        conn.commit()
        conn.close()
        
        # Create reversion message
        display_name = nickname if nickname else name
        
        embed = discord.Embed(
            title="Form Reverted!",
            description=f"{'✨ ' if is_shiny else ''}{display_name} has returned to its normal form!",
            color=discord.Color.green()
        )
        
        if is_shiny and 'shiny_image' in self.veramon_data[name]:
            embed.set_thumbnail(url=self.veramon_data[name]['shiny_image'])
        elif 'image' in self.veramon_data[name]:
            embed.set_thumbnail(url=self.veramon_data[name]['image'])
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='weather', description='Check the current weather in different biomes.')
    @require_permission_level(PermissionLevel.USER)
    async def check_weather(self, interaction: discord.Interaction):
        """Check the current weather conditions in all biomes."""
        # Update weather if needed
        self._update_weather()
        
        embed = discord.Embed(
            title="Current Weather Conditions",
            description="Weather affects which Veramon you encounter and their spawn rates.",
            color=discord.Color.blue()
        )
        
        time_of_day = self._get_current_time_of_day()
        embed.add_field(
            name="Time of Day",
            value=f"**{time_of_day.name.title()}** - Different Veramon may appear at different times!",
            inline=False
        )
        
        for biome_key, biome_data in self.biomes.items():
            biome_name = biome_data.get('name', biome_key.capitalize())
            weather = self.current_weather.get(biome_key)
            
            if weather and weather in biome_data.get('weather_effects', {}):
                weather_data = biome_data['weather_effects'][weather]
                weather_desc = weather_data.get('description', f"{weather.capitalize()}")
                weather_text = f"**{weather.capitalize()}** - {weather_desc}"
            else:
                weather_text = "Clear skies"
                
            embed.add_field(
                name=f"{biome_data.get('emoji', '🏞️')} {biome_name}",
                value=weather_text,
                inline=True
            )
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='special_areas', description='View special exploration areas you can access.')
    @require_permission_level(PermissionLevel.USER)
    async def list_special_areas(self, interaction: discord.Interaction, biome: str = None):
        """List all special areas a user has unlocked or can potentially unlock."""
        user_id = str(interaction.user.id)
        unlocked_areas = self._get_user_unlocked_areas(user_id)
        
        embed = discord.Embed(
            title="Special Exploration Areas",
            description="Discover hidden areas with rare Veramon!",
            color=discord.Color.dark_purple()
        )
        
        no_areas = True
        
        # Filter by biome if specified
        if biome:
            biome_key = biome.lower()
            if biome_key not in self.biomes:
                await interaction.response.send_message(
                    f"Biome '{biome}' not found.",
                    ephemeral=True
                )
                return
                
            biomes_to_check = {biome_key: self.biomes[biome_key]}
        else:
            biomes_to_check = self.biomes
            
        # Check each biome for special areas
        for biome_key, biome_data in biomes_to_check.items():
            biome_name = biome_data.get('name', biome_key.capitalize())
            special_areas = biome_data.get('special_areas', [])
            
            if not special_areas:
                continue
                
            # List of area descriptions for this biome
            area_descriptions = []
            
            for area in special_areas:
                area_id = area.get('id')
                area_name = area.get('name', area_id)
                area_desc = area.get('description', 'A special area.')
                
                # Check if the area is unlocked
                is_unlocked = area_id in unlocked_areas
                
                # Get unlock requirement text
                requirement = area.get('unlock_requirement', {})
                req_type = requirement.get('type', 'unknown')
                
                if req_type == 'achievement':
                    req_text = f"🏆 Requires achievement: {requirement.get('id', 'unknown')}"
                elif req_type == 'quest':
                    req_text = f"📜 Requires quest: {requirement.get('id', 'unknown')}"
                elif req_type == 'level':
                    req_text = f"📊 Requires level: {requirement.get('value', 0)}"
                else:
                    req_text = "❓ Unknown requirement"
                    
                # Format the area entry
                if is_unlocked:
                    status = "✅ UNLOCKED"
                else:
                    status = "🔒 LOCKED"
                    
                area_text = f"**{area_name}** - {status}\n{area_desc}\n{req_text}\n"
                area_descriptions.append(area_text)
                no_areas = False
                
            # Add field for this biome if it has any areas
            if area_descriptions:
                embed.add_field(
                    name=f"{biome_data.get('emoji', '🏞️')} {biome_name}",
                    value="\n".join(area_descriptions),
                    inline=False
                )
                
        if no_areas:
            if biome:
                embed.description = f"No special areas found in '{biome}'. Try exploring other biomes!"
            else:
                embed.description = "No special areas available yet. Complete achievements and quests to unlock them!"
                
        await interaction.response.send_message(embed=embed)
        
async def setup(bot: commands.Bot):
    await bot.add_cog(CatchingCog(bot))
