import discord
from discord import app_commands
from typing import List, Dict, Any, Optional, Callable, Union, Awaitable
import sqlite3
import functools
import os
import json
from src.db.db import get_connection

class AutocompleteHandlers:
    """
    Centralized collection of autocomplete handlers for various command parameters.
    These handlers provide suggestions as users type command arguments.
    """
    
    @staticmethod
    async def veramon_name(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for Veramon names.
        Provides suggestions for Veramon names based on the user's input.
        """
        # Load Veramon data
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "veramon_data.json")
        with open(data_path, 'r') as f:
            veramon_data = json.load(f)
            
        # Filter Veramon names based on current input
        matches = []
        for name in veramon_data.keys():
            if current.lower() in name.lower():
                matches.append(name)
                if len(matches) >= 25:  # Discord allows max 25 choices
                    break
                    
        return [
            app_commands.Choice(name=name, value=name)
            for name in sorted(matches)
        ]
        
    @staticmethod
    async def user_veramon(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for Veramon owned by the user.
        Provides suggestions for the user's captured Veramon.
        """
        user_id = str(interaction.user.id)
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Query for user's Veramon with names matching the current input
            cursor.execute("""
                SELECT c.id, c.veramon_name, c.nickname, c.level, c.shiny 
                FROM captures c
                WHERE c.user_id = ? AND (
                    c.nickname LIKE ? OR c.veramon_name LIKE ?
                )
                ORDER BY c.level DESC
                LIMIT 25
            """, (user_id, f"%{current}%", f"%{current}%"))
            
            results = cursor.fetchall()
            conn.close()
            
            # Format results as choices
            choices = []
            for row in results:
                # Format the display name
                shiny = "✨ " if row['shiny'] else ""
                name = row['nickname'] if row['nickname'] else row['veramon_name']
                display_name = f"{shiny}{name} (Lvl {row['level']})"
                
                choices.append(app_commands.Choice(
                    name=display_name[:100],  # Discord limits choice names to 100 chars
                    value=str(row['id'])
                ))
                
            return choices
        except Exception as e:
            print(f"Error in user_veramon autocomplete: {e}")
            return []
            
    @staticmethod
    async def biome_name(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for biome names.
        Provides suggestions for biomes based on the user's input.
        """
        # Load biome data
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "biomes.json")
        with open(data_path, 'r') as f:
            biome_data = json.load(f)
            
        # Filter biome names based on current input
        matches = []
        for biome_id, biome_info in biome_data.items():
            biome_name = biome_info.get("name", biome_id)
            if current.lower() in biome_name.lower():
                matches.append((biome_id, biome_name))
                if len(matches) >= 25:
                    break
                    
        return [
            app_commands.Choice(name=biome_name, value=biome_id)
            for biome_id, biome_name in sorted(matches, key=lambda x: x[1])
        ]
        
    @staticmethod
    async def item_name(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for item names.
        Provides suggestions for items based on the user's input.
        """
        # Load item data
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "items.json")
        with open(data_path, 'r') as f:
            item_data = json.load(f)
            
        # Filter item names based on current input
        matches = []
        for item_id, item_info in item_data.items():
            item_name = item_info.get("name", item_id)
            if current.lower() in item_name.lower():
                matches.append((item_id, item_name))
                if len(matches) >= 25:
                    break
                    
        return [
            app_commands.Choice(name=item_name, value=item_id)
            for item_id, item_name in sorted(matches, key=lambda x: x[1])
        ]
        
    @staticmethod
    async def ability_name(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for ability names.
        Provides suggestions for abilities based on the user's input.
        """
        # Load ability data
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "abilities.json")
        with open(data_path, 'r') as f:
            ability_data = json.load(f)
            
        # Filter ability names based on current input
        matches = []
        for ability_name, ability_info in ability_data.items():
            if current.lower() in ability_name.lower():
                matches.append(ability_name)
                if len(matches) >= 25:
                    break
                    
        return [
            app_commands.Choice(name=name, value=name)
            for name in sorted(matches)
        ]
        
    @staticmethod
    async def active_trade(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for active trades.
        Provides suggestions for trades the user is participating in.
        """
        user_id = str(interaction.user.id)
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Query for active trades involving the user
            cursor.execute("""
                SELECT t.id, 
                       CASE WHEN t.initiator_id = ? THEN r.username ELSE i.username END as other_user
                FROM trades t
                LEFT JOIN users i ON t.initiator_id = i.user_id
                LEFT JOIN users r ON t.recipient_id = r.user_id
                WHERE (t.initiator_id = ? OR t.recipient_id = ?) 
                  AND t.status = 'pending'
                  AND (CAST(t.id as TEXT) LIKE ? OR 
                       i.username LIKE ? OR 
                       r.username LIKE ?)
                ORDER BY t.created_at DESC
                LIMIT 25
            """, (
                user_id, user_id, user_id, 
                f"%{current}%", f"%{current}%", f"%{current}%"
            ))
            
            results = cursor.fetchall()
            conn.close()
            
            # Format results as choices
            choices = []
            for row in results:
                display_name = f"Trade #{row['id']} with {row['other_user']}"
                choices.append(app_commands.Choice(
                    name=display_name[:100],
                    value=str(row['id'])
                ))
                
            return choices
        except Exception as e:
            print(f"Error in active_trade autocomplete: {e}")
            return []
            
    @staticmethod
    async def active_battle(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocomplete for active battles.
        Provides suggestions for battles the user is participating in.
        """
        user_id = str(interaction.user.id)
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Query for active battles involving the user
            cursor.execute("""
                SELECT b.id, b.battle_type
                FROM battles b
                JOIN battle_participants bp ON b.id = bp.battle_id
                WHERE bp.user_id = ? AND b.status = 'active'
                  AND CAST(b.id as TEXT) LIKE ?
                ORDER BY b.start_time DESC
                LIMIT 25
            """, (user_id, f"%{current}%"))
            
            results = cursor.fetchall()
            conn.close()
            
            # Format results as choices
            choices = []
            for row in results:
                battle_type = row['battle_type'].upper()
                display_name = f"Battle #{row['id']} ({battle_type})"
                choices.append(app_commands.Choice(
                    name=display_name[:100],
                    value=str(row['id'])
                ))
                
            return choices
        except Exception as e:
            print(f"Error in active_battle autocomplete: {e}")
            return []

# Example usage in a command:
#
# @app_commands.command(name="catch", description="Catch a Veramon")
# @app_commands.describe(
#     veramon_name="Name of the Veramon to catch"
# )
# @app_commands.autocomplete(
#     veramon_name=AutocompleteHandlers.veramon_name
# )
# async def catch(self, interaction: discord.Interaction, veramon_name: str):
#     ...
