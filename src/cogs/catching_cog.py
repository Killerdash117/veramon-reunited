import json
import os
import random
from datetime import datetime

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

    @app_commands.command(name='explore', description='Explore a biome to encounter wild Veramon.')
    @app_commands.describe(biome='Name of the biome to explore.')
    @require_permission_level(PermissionLevel.USER)
    async def explore(self, interaction: discord.Interaction, biome: str):
        """Explore a biome and encounter a wild Veramon."""
        user_id = interaction.user.id
        
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
        spawn_table = self.biomes[biome_key].get('spawn_table', {})
        choices = []
        for rarity, names in spawn_table.items():
            weight = RARITY_WEIGHTS.get(rarity.lower(), 1)
            for name in names:
                choices.append((name, weight))
        if not choices:
            await interaction.response.send_message(f"No creatures to spawn in biome '{biome}'.", ephemeral=True)
            return
        chosen = weighted_choice(choices)
        data = self.veramon_data.get(chosen)
        if not data:
            await interaction.response.send_message(f"Data for '{chosen}' not found.", ephemeral=True)
            return
        shiny = random.random() < data.get('shiny_rate', 0)
        embed = discord.Embed(title='Wild Veramon Encounter!', color=0x1abc9c)
        
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
    @app_commands.describe(item='Catch item ID to use.')
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
                "INSERT INTO captures (user_id, veramon_name, caught_at, shiny, biome) VALUES (?, ?, ?, ?, ?)" ,
                (str(user_id), spawn['name'], datetime.utcnow().isoformat(), int(spawn['shiny']), spawn['biome'])
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
            
        veramon_data = self.veramon_data[name]
        evolution_data = veramon_data.get('evolution', {})
        
        if not evolution_data:
            await interaction.response.send_message(
                f"{name} doesn't have an evolution.",
                ephemeral=True
            )
            conn.close()
            return
            
        evolves_to = evolution_data.get('evolves_to')
        level_required = evolution_data.get('level_required', 100)
        
        if not evolves_to:
            await interaction.response.send_message(
                f"{name} doesn't have a defined evolution target.",
                ephemeral=True
            )
            conn.close()
            return
            
        if level < level_required:
            await interaction.response.send_message(
                f"{name} needs to be level {level_required} to evolve (currently level {level}).",
                ephemeral=True
            )
            conn.close()
            return
            
        # All checks passed, evolve the Veramon
        cursor.execute(
            "UPDATE captures SET veramon_name = ? WHERE id = ?",
            (evolves_to, capture_id)
        )
        
        conn.commit()
        conn.close()
        
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

async def setup(bot: commands.Bot):
    await bot.add_cog(CatchingCog(bot))
