import discord
from discord.ext import commands
from discord import app_commands
import json
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any

from src.db.db import get_connection
from src.models.permissions import require_permission_level, PermissionLevel
from src.models.veramon import Veramon
from src.models.battle import Battle, BattleType, BattleStatus, ParticipantStatus, ActionType
from src.utils.data_loader import load_all_veramon_data, load_abilities_data
from src.core.security_integration import get_security_integration

# Load data using the data loader utility
VERAMON_DATA = load_all_veramon_data()
ABILITIES_DATA = load_abilities_data()

# Type effectiveness data
TYPE_EFFECTIVENESS = {
    "Fire": {"Water": 0.5, "Grass": 2.0, "Fire": 0.5, "Rock": 0.5, "Ice": 2.0},
    "Water": {"Fire": 2.0, "Grass": 0.5, "Water": 0.5, "Electric": 0.5, "Ground": 2.0},
    "Grass": {"Water": 2.0, "Fire": 0.5, "Grass": 0.5, "Flying": 0.5, "Bug": 0.5, "Poison": 0.5},
    "Electric": {"Water": 2.0, "Electric": 0.5, "Ground": 0.0, "Flying": 2.0},
    "Ground": {"Electric": 2.0, "Poison": 2.0, "Rock": 2.0, "Water": 0.5, "Grass": 0.5, "Flying": 0.0},
    "Rock": {"Fire": 2.0, "Ice": 2.0, "Flying": 2.0, "Bug": 2.0, "Ground": 0.5, "Fighting": 0.5},
    "Normal": {"Ghost": 0.0, "Fighting": 0.5},
    "Fighting": {"Normal": 2.0, "Rock": 2.0, "Ice": 2.0, "Flying": 0.5, "Psychic": 0.5},
    "Flying": {"Fighting": 2.0, "Bug": 2.0, "Grass": 2.0, "Electric": 0.5, "Rock": 0.5},
    "Psychic": {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Dark": 0.0},
    "Ghost": {"Ghost": 2.0, "Psychic": 2.0, "Dark": 0.5, "Normal": 0.0},
    "Dark": {"Ghost": 2.0, "Psychic": 2.0, "Fighting": 0.5, "Dark": 0.5},
    "Ice": {"Grass": 2.0, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Fire": 0.5, "Water": 0.5, "Ice": 0.5},
    "Dragon": {"Dragon": 2.0, "Ice": 0.5, "Fairy": 0.0},
    "Fairy": {"Fighting": 2.0, "Dragon": 2.0, "Dark": 2.0, "Poison": 0.5, "Steel": 0.5},
    "Steel": {"Ice": 2.0, "Rock": 2.0, "Fairy": 2.0, "Fire": 0.5, "Water": 0.5, "Electric": 0.5},
    "Bug": {"Grass": 2.0, "Psychic": 2.0, "Dark": 2.0, "Fire": 0.5, "Fighting": 0.5, "Flying": 0.5},
    "Poison": {"Grass": 2.0, "Fairy": 2.0, "Poison": 0.5, "Ground": 0.5, "Psychic": 0.5, "Steel": 0.0}
}

class BattleMoveButton(discord.ui.Button):
    def __init__(self, move_name: str, row: int = 0):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=move_name,
            row=row
        )
        self.move_name = move_name

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_move_selected(interaction, self.move_name)

class BattleVeramonButton(discord.ui.Button):
    def __init__(self, veramon_name: str, slot: int, is_active: bool = False, is_fainted: bool = False):
        style = discord.ButtonStyle.success if is_active else discord.ButtonStyle.secondary
        if is_fainted:
            style = discord.ButtonStyle.danger
            
        super().__init__(
            style=style,
            label=veramon_name,
            disabled=is_fainted,
            row=1
        )
        self.slot = slot

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_veramon_selected(interaction, self.slot)

class BattleActionButton(discord.ui.Button):
    def __init__(self, action_type: str, label: str, row: int = 2):
        style = discord.ButtonStyle.secondary
        if action_type == "flee":
            style = discord.ButtonStyle.danger
        elif action_type == "item":
            style = discord.ButtonStyle.success
            
        super().__init__(
            style=style,
            label=label,
            row=row
        )
        self.action_type = action_type

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_action_selected(interaction, self.action_type)

class BattleView(discord.ui.View):
    def __init__(self, cog, battle_id: int, user_id: str):
        super().__init__(timeout=180)
        self.cog = cog
        self.battle_id = battle_id
        self.user_id = user_id
        self.selected_move = None
        self.selected_target = None
        self.selected_veramon = None
        self.mode = "main"  # main, moves, switch, target
        
    async def on_move_selected(self, interaction: discord.Interaction, move_name: str):
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This is not your battle!", ephemeral=True)
            return
            
        self.selected_move = move_name
        
        # Get battle data
        battle_data = await self.cog.get_battle(self.battle_id)
        if not battle_data:
            await interaction.response.send_message("Battle not found!")
            return
            
        # If only one possible target, auto-select it
        participants = battle_data.get("participants", {})
        if len(participants) == 2:  # 1v1 battle
            # Find the opponent
            opponent_id = next((pid for pid in participants.keys() if pid != self.user_id), None)
            if opponent_id:
                self.selected_target = opponent_id
                # Execute the move
                await self.execute_move(interaction)
                return
                
        # Otherwise, show target selection
        self.mode = "target"
        await self.update_view(interaction)
        
    async def on_veramon_selected(self, interaction: discord.Interaction, slot: int):
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This is not your battle!", ephemeral=True)
            return
            
        self.selected_veramon = slot
        
        # If in main mode, this is a switch command
        if self.mode == "main":
            await self.cog.switch_veramon(interaction, self.battle_id, self.user_id, slot)
        # If in switch mode, execute the switch
        elif self.mode == "switch":
            await self.cog.switch_veramon(interaction, self.battle_id, self.user_id, slot)
        # If in target mode, this is a target selection
        elif self.mode == "target":
            self.selected_target = self.user_id  # In this case, targeting your own Veramon
            await self.execute_move(interaction)
            
    async def on_action_selected(self, interaction: discord.Interaction, action_type: str):
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This is not your battle!", ephemeral=True)
            return
            
        if action_type == "moves":
            self.mode = "moves"
            await self.update_view(interaction)
        elif action_type == "switch":
            self.mode = "switch"
            await self.update_view(interaction)
        elif action_type == "item":
            await interaction.response.send_message("Items are not implemented yet!", ephemeral=True)
        elif action_type == "flee":
            await self.cog.attempt_flee(interaction, self.battle_id, self.user_id)
        elif action_type == "back":
            self.mode = "main"
            await self.update_view(interaction)
            
    async def execute_move(self, interaction: discord.Interaction):
        if not self.selected_move or not self.selected_target:
            await interaction.response.send_message("Move or target not selected!", ephemeral=True)
            return
            
        await self.cog.execute_move(interaction, self.battle_id, self.user_id, self.selected_move, [self.selected_target])
        
        # Reset selections
        self.selected_move = None
        self.selected_target = None
        self.mode = "main"
        
    async def update_view(self, interaction: discord.Interaction):
        # Clear existing items
        self.clear_items()
        
        # Get battle data
        battle_data = await self.cog.get_battle(self.battle_id)
        if not battle_data:
            await interaction.response.send_message("Battle not found!")
            return
            
        user_id_str = str(self.user_id)
        
        # Get user's Veramon
        user_veramon = battle_data.get("veramon", {}).get(user_id_str, [])
        active_veramon_slot = battle_data.get("active_veramon", {}).get(user_id_str)
        
        # Main battle menu
        if self.mode == "main":
            # Add action buttons
            self.add_item(BattleActionButton("moves", "Moves"))
            self.add_item(BattleActionButton("switch", "Switch"))
            self.add_item(BattleActionButton("item", "Item"))
            if battle_data.get("battle_type") == "pve":
                self.add_item(BattleActionButton("flee", "Flee"))
                
        # Moves selection
        elif self.mode == "moves":
            # Get active Veramon's moves
            if active_veramon_slot is not None and active_veramon_slot < len(user_veramon):
                veramon = user_veramon[active_veramon_slot]
                if veramon:
                    moves = veramon.get("moves", [])
                    for i, move in enumerate(moves):
                        self.add_item(BattleMoveButton(move, row=0))
            
            # Add back button
            self.add_item(BattleActionButton("back", "Back", row=2))
            
        # Switch Veramon
        elif self.mode == "switch":
            # Add buttons for each Veramon
            for i, veramon in enumerate(user_veramon):
                if veramon:
                    is_active = i == active_veramon_slot
                    is_fainted = veramon.get("current_hp", 0) <= 0
                    name = veramon.get("display_name", veramon.get("name", f"Veramon {i+1}"))
                    self.add_item(BattleVeramonButton(name, i, is_active, is_fainted))
            
            # Add back button
            self.add_item(BattleActionButton("back", "Back", row=2))
            
        # Target selection
        elif self.mode == "target":
            # For each participant, add a button for their active Veramon
            for pid, participant in battle_data.get("participants", {}).items():
                if participant.get("status") == "joined" and pid in battle_data.get("active_veramon", {}):
                    # Get active Veramon
                    slot = battle_data.get("active_veramon", {}).get(pid)
                    if slot is not None and pid in battle_data.get("veramon", {}) and slot < len(battle_data.get("veramon", {}).get(pid, [])):
                        veramon = battle_data.get("veramon", {}).get(pid, [])[slot]
                        if veramon:
                            name = veramon.get("display_name", veramon.get("name", "Opponent"))
                            # If it's the user's Veramon, mark as active
                            is_active = pid == user_id_str
                            self.add_item(BattleVeramonButton(name, int(pid), is_active))
            
            # Add back button
            self.add_item(BattleActionButton("back", "Back", row=2))
        
        # Update the message
        await interaction.response.edit_message(view=self)

class BattleInviteView(discord.ui.View):
    def __init__(self, cog, battle_id: int, host_id: str, target_id: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.battle_id = battle_id
        self.host_id = host_id
        self.target_id = target_id
        
    @discord.ui.button(label="Accept Battle", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.target_id):
            await interaction.response.send_message("This invitation is not for you!", ephemeral=True)
            return
            
        await self.cog.accept_battle_invitation(interaction, self.battle_id, self.target_id)
        self.stop()
        
    @discord.ui.button(label="Decline Battle", style=discord.ButtonStyle.red)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.target_id):
            await interaction.response.send_message("This invitation is not for you!", ephemeral=True)
            return
            
        await self.cog.decline_battle_invitation(interaction, self.battle_id, self.target_id)
        self.stop()

class EnhancedBattleCog(commands.Cog):
    """
    Enhanced battle system for Veramon Reunited with PvP, PvE, and multi-player battles.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_battles = {}  # battle_id -> Battle object
        self.battle_messages = {}  # battle_id -> message_id
        self.active_views = {}     # battle_id -> {user_id -> BattleView}
        
    @app_commands.command(name="battle_pve", description="Challenge an NPC trainer to a battle")
    @app_commands.describe(
        difficulty="Difficulty level of the NPC trainer"
    )
    @require_permission_level(PermissionLevel.USER)
    async def battle_pve(self, interaction: discord.Interaction, difficulty: str = "easy"):
        """Start a battle against an NPC trainer."""
        user_id = str(interaction.user.id)
        
        # Check if player has Veramon
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, veramon_name, shiny, nickname, level, experience
            FROM captures
            WHERE user_id = ? AND active = 1
            LIMIT 6
        """, (user_id,))
        
        active_veramon = cursor.fetchall()
        
        if not active_veramon:
            cursor.execute("""
                SELECT id, veramon_name, shiny, nickname, level, experience
                FROM captures
                WHERE user_id = ?
                LIMIT 6
            """, (user_id,))
            
            active_veramon = cursor.fetchall()
            
        if not active_veramon:
            await interaction.response.send_message(
                "You don't have any Veramon! Catch some with `/explore` and `/catch` first.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Create a new battle
        battle = await self._create_pve_battle(user_id, difficulty)
        
        # Store in active battles
        self.active_battles[battle.battle_id] = battle
        
        # Send battle start message
        embed = self._create_battle_start_embed(battle, "pve")
        
        # Create battle view for the player
        view = BattleView(self, battle.battle_id, user_id)
        self.active_views[battle.battle_id] = {user_id: view}
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Start the battle
        success = battle.start_battle()
        if not success:
            await interaction.followup.send("Failed to start battle!")
            return
            
        # Update battle state for the player
        await self._send_battle_update(interaction.channel, battle)

    @app_commands.command(name="battle_pvp", description="Challenge another player to a Veramon battle")
    @app_commands.describe(
        player="Player to challenge"
    )
    @require_permission_level(PermissionLevel.USER)
    async def battle_pvp(self, interaction: discord.Interaction, player: discord.Member):
        """Challenge another player to a battle."""
        user_id = str(interaction.user.id)
        target_id = str(player.id)
        
        # Security validation
        security = get_security_integration()
        validation_result = await security.validate_battle_creation(user_id, "pvp", target_id)
        
        if not validation_result["valid"]:
            await interaction.response.send_message(
                validation_result["error"],
                ephemeral=True
            )
            return
        
        # Check if user is trying to battle themselves
        if user_id == target_id:
            await interaction.response.send_message("You can't battle yourself!", ephemeral=True)
            return
            
        # Check if user has any Veramon
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM captures
            WHERE user_id = ? AND health > 0
        """, (user_id,))
        
        user_veramon_count = cursor.fetchone()[0]
        
        if user_veramon_count == 0:
            await interaction.response.send_message(
                "You don't have any battle-ready Veramon. Heal your Veramon at the healing center!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Check if target user has any Veramon
        cursor.execute("""
            SELECT COUNT(*) FROM captures
            WHERE user_id = ? AND health > 0
        """, (target_id,))
        
        target_veramon_count = cursor.fetchone()[0]
        
        if target_veramon_count == 0:
            await interaction.response.send_message(
                f"{player.display_name} doesn't have any battle-ready Veramon.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Create a new battle
        battle = await self._create_pvp_battle(user_id, target_id)
        
        # Store in active battles
        self.active_battles[battle.battle_id] = battle
        
        # Send battle invitation
        embed = discord.Embed(
            title="Battle Challenge!",
            description=f"{interaction.user.display_name} has challenged {player.display_name} to a Veramon battle!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Instructions",
            value=(
                f"{player.mention}, use the buttons below to accept or decline this challenge.\n"
                "The invitation will expire in 5 minutes."
            ),
            inline=False
        )
        
        view = BattleInviteView(self, battle.battle_id, user_id, target_id)
        
        await interaction.response.send_message(
            content=f"{player.mention}, you've been challenged to a battle!",
            embed=embed,
            view=view
        )
        
    @app_commands.command(name="battle_multi", description="Start a multi-player battle (2v2 or Free-for-All)")
    @app_commands.describe(
        battle_type="Type of multi-player battle",
        team_size="Number of players per team (2 for 2v2)"
    )
    @require_permission_level(PermissionLevel.USER)
    async def battle_multi(self, interaction: discord.Interaction, battle_type: str = "ffa", team_size: int = 2):
        """Start a multi-player battle."""
        # This is a placeholder for now - will be implemented in the next phase
        await interaction.response.send_message(
            "Multi-player battles will be coming soon!",
            ephemeral=True
        )
        
    @app_commands.command(name="battle_wild", description="Battle a wild Veramon in the current biome")
    @app_commands.describe(
        biome="Optional biome to search for wild Veramon (defaults to random)"
    )
    @require_permission_level(PermissionLevel.USER)
    async def battle_wild(self, interaction: discord.Interaction, biome: str = None):
        """Battle a wild Veramon in the specified biome (or random biome)."""
        user_id = str(interaction.user.id)
        
        # Check if player has Veramon
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, veramon_name, shiny, nickname, level, experience
            FROM captures
            WHERE user_id = ? AND active = 1
            LIMIT 6
        """, (user_id,))
        
        active_veramon = cursor.fetchall()
        
        if not active_veramon:
            cursor.execute("""
                SELECT id, veramon_name, shiny, nickname, level, experience
                FROM captures
                WHERE user_id = ?
                LIMIT 6
            """, (user_id,))
            
            active_veramon = cursor.fetchall()
            
        if not active_veramon:
            await interaction.response.send_message(
                "You don't have any Veramon! Catch some with `/explore` and `/catch` first.",
                ephemeral=True
            )
            conn.close()
            return
        
        # Load biome data
        with open(os.path.join(DATA_DIR, "biomes.json"), "r") as f:
            biomes_data = json.load(f)
            
        # Select biome
        if not biome or biome.lower() not in biomes_data:
            # Random biome if not specified or invalid
            biome = random.choice(list(biomes_data.keys()))
        else:
            biome = biome.lower()
            
        biome_data = biomes_data[biome]
        
        # Get spawn tables for the biome
        spawn_table = biome_data.get("spawn_table", {})
        if not spawn_table:
            await interaction.response.send_message(
                f"No Veramon found in the {biome} biome!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Create weighted choices based on rarity
        choices = []
        for rarity, names in spawn_table.items():
            # Rarity weights defined at top of file
            weight = {"common": 60, "uncommon": 30, "rare": 10, "legendary": 1, "mythic": 0.1}.get(rarity.lower(), 1)
            for name in names:
                choices.append((name, weight))
                
        if not choices:
            await interaction.response.send_message(
                f"No Veramon found in the {biome} biome!",
                ephemeral=True
            )
            conn.close()
            return
            
        # Select a wild Veramon
        chosen_name = random.choices(
            [name for name, _ in choices],
            weights=[weight for _, weight in choices],
            k=1
        )[0]
        
        if chosen_name not in VERAMON_DATA:
            await interaction.response.send_message(
                f"Error: Data for {chosen_name} is missing.",
                ephemeral=True
            )
            conn.close()
            return
            
        # Determine wild Veramon level based on rarity
        level_ranges = {
            "common": (1, 10),
            "uncommon": (5, 15),
            "rare": (10, 25),
            "legendary": (20, 40),
            "mythic": (30, 50)
        }
        
        # Find rarity of chosen Veramon
        chosen_rarity = "common"
        for rarity, names in spawn_table.items():
            if chosen_name in names:
                chosen_rarity = rarity.lower()
                break
                
        level_range = level_ranges.get(chosen_rarity, (1, 10))
        wild_level = random.randint(level_range[0], level_range[1])
        
        # Check for shiny
        shiny_chance = {
            "common": 0.001,    # 1/1000
            "uncommon": 0.002,  # 1/500
            "rare": 0.005,      # 1/200
            "legendary": 0.01,  # 1/100
            "mythic": 0.02      # 1/50
        }.get(chosen_rarity, 0.001)
        
        is_shiny = random.random() < shiny_chance
        
        # Create battle
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get a new battle ID
        cursor.execute("""
            INSERT INTO battles (
                battle_type, status, created_at, updated_at, expiry_time
            ) VALUES (
                'pve', 'waiting', ?, ?, ?
            )
        """, (
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        ))
        
        battle_id = cursor.lastrowid
        
        # Create battle instance
        battle = Battle(
            battle_id=battle_id,
            battle_type=BattleType.PVE,
            host_id=user_id
        )
        
        # Add player as participant
        battle.add_participant(user_id, team_id=0, is_host=True, status=ParticipantStatus.JOINED)
        
        # Add their Veramon
        for i, (capture_id, name, shiny, nickname, level, exp) in enumerate(active_veramon):
            if name in VERAMON_DATA:
                veramon_data = VERAMON_DATA[name]
                veramon = Veramon(
                    name=name,
                    data=veramon_data,
                    level=level,
                    shiny=bool(shiny),
                    nickname=nickname,
                    experience=exp,
                    capture_id=capture_id
                )
                
                # Get moves from ABILITIES_DATA
                veramon.moves = veramon.get_random_moves(ABILITIES_DATA)
                
                battle.add_veramon(user_id, veramon, i)
                
        # Create wild Veramon
        wild_id = f"wild_{battle_id}"
        battle.add_participant(wild_id, team_id=1, is_npc=True, status=ParticipantStatus.JOINED)
        
        # Add wild Veramon
        wild_data = VERAMON_DATA[chosen_name]
        wild_veramon = Veramon(
            name=chosen_name,
            data=wild_data,
            level=wild_level,
            shiny=is_shiny
        )
        
        # Get moves for wild Veramon
        wild_veramon.moves = wild_veramon.get_random_moves(ABILITIES_DATA)
        
        battle.add_veramon(wild_id, wild_veramon, 0)
        
        # Save to database
        cursor.execute("""
            UPDATE battles
            SET battle_data = ?
            WHERE battle_id = ?
        """, (json.dumps(battle.to_dict()), battle_id))
        
        # Add participants to database
        cursor.execute("""
            INSERT INTO battle_participants (
                battle_id, user_id, team_id, is_host, is_npc, status, joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            battle_id,
            user_id,
            0,
            1,
            0,
            "joined",
            datetime.utcnow().isoformat()
        ))
        
        cursor.execute("""
            INSERT INTO battle_participants (
                battle_id, user_id, team_id, is_host, is_npc, status, joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            battle_id,
            wild_id,
            1,
            0,
            1,
            "joined",
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Store in active battles
        self.active_battles[battle_id] = battle
        
        # Create battle view for the player
        view = BattleView(self, battle_id, user_id)
        self.active_views[battle_id] = {user_id: view}
        
        # Send wild encounter message
        embed = discord.Embed(
            title="Wild Veramon Encounter!",
            description=f"You encountered a wild {' ✨ ' if is_shiny else ''}{chosen_name} (Level {wild_level}) in the {biome_data.get('name', biome)} biome!",
            color=discord.Color.green()
        )
        
        # Add image if available
        if is_shiny and "shiny_image" in wild_data:
            embed.set_thumbnail(url=wild_data["shiny_image"])
        elif "image" in wild_data:
            embed.set_thumbnail(url=wild_data["image"])
            
        embed.add_field(
            name="Rarity",
            value=chosen_rarity.capitalize(),
            inline=True
        )
        
        embed.add_field(
            name="Type",
            value=" / ".join(wild_data.get("type", ["Normal"])),
            inline=True
        )
        
        # Add battle options
        embed.add_field(
            name="Options",
            value="Prepare for battle! Use the buttons below to select your actions.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Start the battle
        success = battle.start_battle()
        if not success:
            await interaction.followup.send("Failed to start battle!")
            return
            
        # Update battle state for the player
        await self._send_battle_update(interaction.channel, battle)

    async def _create_pve_battle(self, user_id: str, difficulty: str) -> Battle:
        """Create a PvE battle against an NPC trainer."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get a new battle ID
        cursor.execute("""
            INSERT INTO battles (
                battle_type, status, created_at, updated_at, expiry_time
            ) VALUES (
                'pve', 'waiting', ?, ?, ?
            )
        """, (
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        ))
        
        battle_id = cursor.lastrowid
        
        # Create battle instance
        battle = Battle(
            battle_id=battle_id,
            battle_type=BattleType.PVE,
            host_id=user_id
        )
        
        # Add player as participant
        battle.add_participant(user_id, team_id=0, is_host=True, status=ParticipantStatus.JOINED)
        
        # Add their Veramon
        cursor.execute("""
            SELECT id, veramon_name, shiny, nickname, level, experience
            FROM captures
            WHERE user_id = ? AND active = 1
            LIMIT 6
        """, (user_id,))
        
        active_veramon = cursor.fetchall()
        
        if not active_veramon:
            cursor.execute("""
                SELECT id, veramon_name, shiny, nickname, level, experience
                FROM captures
                WHERE user_id = ?
                LIMIT 6
            """, (user_id,))
            
            active_veramon = cursor.fetchall()
            
        for i, (capture_id, name, shiny, nickname, level, exp) in enumerate(active_veramon):
            if name in VERAMON_DATA:
                veramon_data = VERAMON_DATA[name]
                veramon = Veramon(
                    name=name,
                    data=veramon_data,
                    level=level,
                    shiny=bool(shiny),
                    nickname=nickname,
                    experience=exp,
                    capture_id=capture_id
                )
                
                # Get moves from ABILITIES_DATA
                veramon.moves = veramon.get_random_moves(ABILITIES_DATA)
                
                battle.add_veramon(user_id, veramon, i)
                
        # Create NPC trainer
        npc_id = f"npc_{battle_id}"
        battle.add_participant(npc_id, team_id=1, is_npc=True, status=ParticipantStatus.JOINED)
        
        # Add NPC Veramon based on difficulty
        npc_level = {"easy": 5, "medium": 15, "hard": 25, "gym_leader": 35, "elite": 50}.get(difficulty, 5)
        
        # Select 3-6 random Veramon based on difficulty
        num_veramon = random.randint(3, min(4 + {"easy": 0, "medium": 1, "hard": 1, "gym_leader": 2, "elite": 2}.get(difficulty, 0), 6))
        
        # Select Veramon names from VERAMON_DATA
        veramon_names = random.sample(list(VERAMON_DATA.keys()), num_veramon)
        
        for i, name in enumerate(veramon_names):
            veramon_data = VERAMON_DATA[name]
            
            # Adjust level based on difficulty
            level_variance = {"easy": 2, "medium": 3, "hard": 4, "gym_leader": 5, "elite": 8}.get(difficulty, 2)
            veramon_level = max(1, npc_level + random.randint(-level_variance, level_variance))
            
            # Create Veramon
            veramon = Veramon(
                name=name,
                data=veramon_data,
                level=veramon_level,
                shiny=random.random() < 0.05  # 5% chance for NPC to have shiny
            )
            
            # Get moves
            veramon.moves = veramon.get_random_moves(ABILITIES_DATA)
            
            battle.add_veramon(npc_id, veramon, i)
            
        # Save to database
        cursor.execute("""
            UPDATE battles
            SET battle_data = ?
            WHERE battle_id = ?
        """, (json.dumps(battle.to_dict()), battle_id))
        
        # Add participants to database
        cursor.execute("""
            INSERT INTO battle_participants (
                battle_id, user_id, team_id, is_host, is_npc, status, joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            battle_id,
            user_id,
            0,
            1,
            0,
            "joined",
            datetime.utcnow().isoformat()
        ))
        
        cursor.execute("""
            INSERT INTO battle_participants (
                battle_id, user_id, team_id, is_host, is_npc, status, joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            battle_id,
            npc_id,
            1,
            0,
            1,
            "joined",
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return battle

    async def _create_pvp_battle(self, host_id: str, target_id: str) -> Battle:
        """Create a PvP battle between two players."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get a new battle ID
        cursor.execute("""
            INSERT INTO battles (
                battle_type, status, created_at, updated_at, expiry_time
            ) VALUES (
                'pvp', 'waiting', ?, ?, ?
            )
        """, (
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        ))
        
        battle_id = cursor.lastrowid
        
        # Create battle instance
        battle = Battle(
            battle_id=battle_id,
            battle_type=BattleType.PVP,
            host_id=host_id
        )
        
        # Add host as participant (joined)
        battle.add_participant(host_id, team_id=0, is_host=True, status=ParticipantStatus.JOINED)
        
        # Add target as participant (invited)
        battle.add_participant(target_id, team_id=1, is_host=False, status=ParticipantStatus.INVITED)
        
        # Save to database
        cursor.execute("""
            UPDATE battles
            SET battle_data = ?
            WHERE battle_id = ?
        """, (json.dumps(battle.to_dict()), battle_id))
        
        # Add participants to database
        cursor.execute("""
            INSERT INTO battle_participants (
                battle_id, user_id, team_id, is_host, is_npc, status, joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            battle_id,
            host_id,
            0,
            1,
            0,
            "joined",
            datetime.utcnow().isoformat()
        ))
        
        cursor.execute("""
            INSERT INTO battle_participants (
                battle_id, user_id, team_id, is_host, is_npc, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            battle_id,
            target_id,
            1,
            0,
            0,
            "invited"
        ))
        
        conn.commit()
        conn.close()
        
        return battle
        
    async def accept_battle_invitation(self, interaction: discord.Interaction, battle_id: int, user_id: str):
        """Accept a battle invitation."""
        user_id_str = str(user_id)
        
        # Check if battle exists
        if battle_id not in self.active_battles:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT battle_data
                FROM battles
                WHERE battle_id = ?
            """, (battle_id,))
            
            battle_data_row = cursor.fetchone()
            
            if not battle_data_row:
                await interaction.response.send_message("Battle not found!")
                conn.close()
                return
                
            # Reconstruct battle from data
            battle_dict = json.loads(battle_data_row[0])
            battle = Battle.from_dict(battle_dict)
            
            self.active_battles[battle_id] = battle
        else:
            battle = self.active_battles[battle_id]
        
        # Check if user is invited
        if user_id_str not in battle.participants:
            await interaction.response.send_message("You are not invited to this battle!")
            return
            
        if battle.participants[user_id_str]["status"] != ParticipantStatus.INVITED:
            await interaction.response.send_message("You cannot accept this battle!")
            return
            
        # Update participant status
        battle.participants[user_id_str]["status"] = ParticipantStatus.JOINED
        battle.participants[user_id_str]["joined_at"] = datetime.utcnow().isoformat()
        
        # Update in database
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE battle_participants
            SET status = 'joined', joined_at = ?
            WHERE battle_id = ? AND user_id = ?
        """, (datetime.utcnow().isoformat(), battle_id, user_id_str))
        
        # Now we need to load the player's Veramon
        cursor.execute("""
            SELECT id, veramon_name, shiny, nickname, level, experience
            FROM captures
            WHERE user_id = ? AND active = 1
            LIMIT 6
        """, (user_id_str,))
        
        active_veramon = cursor.fetchall()
        
        if not active_veramon:
            cursor.execute("""
                SELECT id, veramon_name, shiny, nickname, level, experience
                FROM captures
                WHERE user_id = ?
                LIMIT 6
            """, (user_id_str,))
            
            active_veramon = cursor.fetchall()
            
        # Add Veramon to battle
        for i, (capture_id, name, shiny, nickname, level, exp) in enumerate(active_veramon):
            if name in VERAMON_DATA:
                veramon_data = VERAMON_DATA[name]
                veramon = Veramon(
                    name=name,
                    data=veramon_data,
                    level=level,
                    shiny=bool(shiny),
                    nickname=nickname,
                    experience=exp,
                    capture_id=capture_id
                )
                
                # Get moves from ABILITIES_DATA
                veramon.moves = veramon.get_random_moves(ABILITIES_DATA)
                
                battle.add_veramon(user_id_str, veramon, i)
                
        # Update battle data in database
        cursor.execute("""
            UPDATE battles
            SET battle_data = ?, updated_at = ?
            WHERE battle_id = ?
        """, (json.dumps(battle.to_dict()), datetime.utcnow().isoformat(), battle_id))
        
        conn.commit()
        conn.close()
        
        # Create battle views for both players
        host_id = battle.host_id
        
        host_view = BattleView(self, battle_id, host_id)
        player_view = BattleView(self, battle_id, user_id_str)
        
        self.active_views[battle_id] = {
            host_id: host_view,
            user_id_str: player_view
        }
        
        # Notify users and start battle
        await interaction.response.send_message("Battle accepted! Preparing battle...")
        
        # Get channel
        channel = interaction.channel
        
        # Start the battle
        success = battle.start_battle()
        if not success:
            await channel.send("Failed to start battle!")
            return
            
        # Send battle start message
        embed = self._create_battle_start_embed(battle, "pvp")
        await channel.send(embed=embed)
        
        # Send battle state to each player
        await self._send_battle_update(channel, battle)
        
    async def decline_battle_invitation(self, interaction: discord.Interaction, battle_id: int, user_id: str):
        """Decline a battle invitation."""
        user_id_str = str(user_id)
        
        # Check if battle exists
        if battle_id in self.active_battles:
            battle = self.active_battles[battle_id]
            
            # Update participant status
            if user_id_str in battle.participants:
                battle.participants[user_id_str]["status"] = ParticipantStatus.DECLINED
                
            # Cancel battle
            battle.status = BattleStatus.CANCELLED
            
            # Remove from active battles
            del self.active_battles[battle_id]
        
        # Update in database
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE battle_participants
            SET status = 'declined'
            WHERE battle_id = ? AND user_id = ?
        """, (battle_id, user_id_str))
        
        cursor.execute("""
            UPDATE battles
            SET status = 'cancelled', updated_at = ?
            WHERE battle_id = ?
        """, (datetime.utcnow().isoformat(), battle_id))
        
        conn.commit()
        conn.close()
        
        await interaction.response.send_message("Battle invitation declined.")
        
    async def execute_move(self, interaction: discord.Interaction, battle_id: int, user_id: str, move_name: str, target_ids: List[str]):
        """Execute a battle move."""
        # Security validation for battle action
        security = get_security_integration()
        action_data = {"move_name": move_name, "targets": target_ids}
        validation_result = await security.validate_battle_action(
            user_id, battle_id, "move", action_data
        )
        
        if not validation_result["valid"]:
            await interaction.response.send_message(
                validation_result["error"],
                ephemeral=True
            )
            return False
            
        # Get battle
        battle = self.active_battles.get(battle_id)
        if not battle:
            battle = await self.get_battle(battle_id)
            if not battle:
                await interaction.response.send_message("Battle not found.", ephemeral=True)
                return False
                
        # Check if it's the user's turn
        if battle.current_turn != user_id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return False
        
        # Execute the move
        battle.execute_move(user_id, move_name, target_ids)
        
        # Check if the battle is over
        if battle.status == BattleStatus.COMPLETED.value:
            channel = interaction.channel
            await self._handle_battle_end(channel, battle)
            return True
        
        # Update the battle state
        await self._send_battle_update(interaction.channel, battle)
        return True
        
    async def switch_veramon(self, interaction: discord.Interaction, battle_id: int, user_id: str, slot: int):
        """Switch active Veramon in battle."""
        user_id_str = str(user_id)
        
        # Check if battle exists
        if battle_id not in self.active_battles:
            await interaction.response.send_message("Battle not found!")
            return
            
        battle = self.active_battles[battle_id]
        
        # Check if it's user's turn
        if battle.current_turn != user_id_str:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
            
        # Execute the switch
        result = battle.switch_veramon(user_id_str, slot)
        
        if not result["success"]:
            await interaction.response.send_message(result["message"], ephemeral=True)
            return
            
        # Update battle in database
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE battles
            SET battle_data = ?, updated_at = ?
            WHERE battle_id = ?
        """, (json.dumps(battle.to_dict()), datetime.utcnow().isoformat(), battle_id))
        
        conn.commit()
        conn.close()
        
        # Update battle state for all players
        await self._send_battle_update(interaction.channel, battle)
        
    async def attempt_flee(self, interaction: discord.Interaction, battle_id: int, user_id: str):
        """Attempt to flee from a PVE battle."""
        user_id_str = str(user_id)
        
        # Check if battle exists
        if battle_id not in self.active_battles:
            await interaction.response.send_message("Battle not found!")
            return
            
        battle = self.active_battles[battle_id]
        
        # Check if it's user's turn
        if battle.current_turn != user_id_str:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
            
        # Execute the flee attempt
        result = battle.attempt_flee(user_id_str)
        
        # Update battle in database
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE battles
            SET battle_data = ?, updated_at = ?, status = ?
            WHERE battle_id = ?
        """, (
            json.dumps(battle.to_dict()), 
            datetime.utcnow().isoformat(),
            battle.status.value,
            battle_id
        ))
        
        conn.commit()
        conn.close()
        
        # Send result
        await interaction.response.send_message(result["message"])
        
        # If battle ended, clean up
        if battle.status == BattleStatus.CANCELLED:
            # Remove from active battles
            if battle_id in self.active_battles:
                del self.active_battles[battle_id]
            return
            
        # Otherwise update battle state
        await self._send_battle_update(interaction.channel, battle)

    async def get_battle(self, battle_id: int) -> Dict[str, Any]:
        """Get battle data by ID."""
        if battle_id in self.active_battles:
            return self.active_battles[battle_id].to_dict()
            
        # Try to load from database
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT battle_data
            FROM battles
            WHERE battle_id = ?
        """, (battle_id,))
        
        battle_data_row = cursor.fetchone()
        conn.close()
        
        if not battle_data_row:
            return None
            
        return json.loads(battle_data_row[0])
        
    def _create_battle_start_embed(self, battle, battle_type: str) -> discord.Embed:
        """Create an embed for battle start."""
        if battle_type == "pve":
            # Find NPC participant
            npc_id = next((pid for pid in battle.participants if pid.startswith("npc_")), None)
            player_id = battle.host_id
            
            # Get NPC's first Veramon
            if npc_id and npc_id in battle.veramon:
                npc_veramon = next((v for v in battle.veramon[npc_id] if v is not None), None)
                npc_name = "Wild Trainer"  # Could be customized based on difficulty
                
                embed = discord.Embed(
                    title="Battle Start!",
                    description=f"You are battling against {npc_name}!",
                    color=discord.Color.red()
                )
                
                if npc_veramon:
                    embed.add_field(
                        name=f"{npc_name}'s First Veramon",
                        value=f"{npc_veramon.display_name} (Lv. {npc_veramon.level})"
                    )
                    
                return embed
                
        elif battle_type == "pvp":
            # Get both participants
            host_id = battle.host_id
            opponent_id = next((pid for pid in battle.participants if pid != host_id), None)
            
            if opponent_id:
                embed = discord.Embed(
                    title="PvP Battle Start!",
                    description=f"<@{host_id}> vs <@{opponent_id}>",
                    color=discord.Color.gold()
                )
                
                embed.add_field(
                    name="Battle Type",
                    value="Player vs Player"
                )
                
                embed.add_field(
                    name="Turn Order",
                    value=", ".join([f"<@{pid}>" for pid in battle.turn_order]) if battle.turn_order else "Not determined yet"
                )
                
                return embed
                
        # Default embed
        return discord.Embed(
            title="Battle Start!",
            description="The battle has begun!",
            color=discord.Color.blue()
        )
        
    async def _send_battle_update(self, channel, battle):
        """Send battle update to all participants."""
        # Create embeds for each player
        for user_id in battle.participants:
            # Skip NPC participants
            if user_id.startswith("npc_"):
                continue
                
            # Get user's view
            view = self.active_views.get(battle.battle_id, {}).get(user_id)
            if not view:
                view = BattleView(self, battle.battle_id, user_id)
                if battle.battle_id not in self.active_views:
                    self.active_views[battle.battle_id] = {}
                self.active_views[battle.battle_id][user_id] = view
                
            # Create user's embed
            embed = self._create_battle_state_embed(battle, user_id)
            
            try:
                member = await self.bot.fetch_user(int(user_id))
                if member:
                    # Check if this is the player's turn
                    if battle.current_turn == user_id:
                        await channel.send(f"{member.mention}, it's your turn!", embed=embed, view=view)
                    else:
                        await channel.send(f"Battle update for {member.mention}", embed=embed, view=view)
            except Exception as e:
                print(f"Error sending battle update: {e}")
                
        # Check for battle end
        if battle.status == BattleStatus.COMPLETED:
            await self._handle_battle_end(channel, battle)
            
    def _create_battle_state_embed(self, battle, user_id: str) -> discord.Embed:
        """Create an embed showing the current battle state for a specific user."""
        # Create base embed
        if battle.battle_type == BattleType.PVE:
            title = "Battle vs. NPC Trainer"
        else:
            title = "PvP Battle"
            
        embed = discord.Embed(
            title=title,
            description=f"Turn {battle.turn_number} - " + 
                       (f"Your turn!" if battle.current_turn == user_id else f"<@{battle.current_turn}>'s turn"),
            color=discord.Color.blue()
        )
        
        # Add user's active Veramon
        if user_id in battle.active_veramon and battle.active_veramon[user_id] is not None:
            slot = battle.active_veramon[user_id]
            if user_id in battle.veramon and slot < len(battle.veramon[user_id]):
                veramon = battle.veramon[user_id][slot]
                if veramon:
                    embed.add_field(
                        name="Your Active Veramon",
                        value=(
                            f"**{veramon.display_name}** (Lv. {veramon.level})\n"
                            f"HP: {veramon.current_hp}/{veramon.max_hp}\n"
                            f"Moves: {', '.join(veramon.moves)}"
                        ),
                        inline=False
                    )
        
        # Add opponent's active Veramon
        for pid in battle.participants:
            if pid != user_id and pid in battle.active_veramon and battle.active_veramon[pid] is not None:
                slot = battle.active_veramon[pid]
                if pid in battle.veramon and slot < len(battle.veramon[pid]):
                    veramon = battle.veramon[pid][slot]
                    if veramon:
                        name = "Opponent's Veramon"
                        if pid.startswith("npc_"):
                            name = "NPC Trainer's Veramon"
                        embed.add_field(
                            name=name,
                            value=(
                                f"**{veramon.display_name}** (Lv. {veramon.level})\n"
                                f"HP: {veramon.current_hp}/{veramon.max_hp}"
                            ),
                            inline=False
                        )
        
        # Add recent battle logs
        if battle.battle_log:
            # Get last 3 logs
            recent_logs = battle.battle_log[-3:]
            log_texts = []
            
            for log in recent_logs:
                if log["action_type"] == "move":
                    if log["actor_id"] == "system":
                        if "type" in log["action_data"]:
                            if log["action_data"]["type"] == "battle_start":
                                log_texts.append("**Battle started!**")
                            elif log["action_data"]["type"] == "battle_end":
                                winner_id = log["result_data"].get("winner_id")
                                if winner_id == "draw":
                                    log_texts.append("**Battle ended in a draw!**")
                                else:
                                    if winner_id == user_id:
                                        log_texts.append("**You won the battle!**")
                                    else:
                                        if winner_id.startswith("npc_"):
                                            log_texts.append("**The NPC trainer won the battle!**")
                                        else:
                                            log_texts.append(f"**<@{winner_id}> won the battle!**")
                    else:
                        # Regular move
                        actor_name = f"<@{log['actor_id']}>" if log['actor_id'] == user_id else "You"
                        if log['actor_id'].startswith("npc_"):
                            actor_name = "NPC Trainer"
                            
                        move_name = log["action_data"].get("move_name", "Unknown Move")
                        targets = []
                        
                        for target_id in log.get("target_ids", []):
                            if target_id == user_id:
                                targets.append("your Veramon")
                            elif target_id.startswith("npc_"):
                                targets.append("the NPC's Veramon")
                            else:
                                targets.append(f"<@{target_id}>'s Veramon")
                                
                        target_text = " and ".join(targets) if targets else "no target"
                        
                        # Get result details
                        results = log["result_data"].get("results", [])
                        if results:
                            details = []
                            for result_data in results:
                                if result_data.get("success"):
                                    result = result_data.get("result", {})
                                    damage = result.get("damage", 0)
                                    critical = result.get("critical_hit", False)
                                    effectiveness = result.get("type_effectiveness", 1.0)
                                    
                                    damage_text = f"dealing {damage} damage"
                                    if critical:
                                        damage_text += " (Critical hit!)"
                                    if effectiveness > 1.0:
                                        damage_text += " (Super effective!)"
                                    elif effectiveness < 1.0:
                                        if effectiveness == 0:
                                            damage_text += " (No effect!)"
                                        else:
                                            damage_text += " (Not very effective...)"
                                            
                                    details.append(damage_text)
                                    
                                    if result.get("fainted"):
                                        details.append("The target Veramon fainted!")
                                    
                            if details:
                                detail_text = ", ".join(details)
                                log_texts.append(f"{actor_name} used **{move_name}** on {target_text}, {detail_text}!")
                            else:
                                log_texts.append(f"{actor_name} used **{move_name}** on {target_text}!")
                        else:
                            log_texts.append(f"{actor_name} used **{move_name}** on {target_text}!")
                elif log["action_type"] == "switch":
                    actor_name = "You" if log["actor_id"] == user_id else f"<@{log['actor_id']}>"
                    if log['actor_id'].startswith("npc_"):
                        actor_name = "NPC Trainer"
                        
                    old_slot = log["action_data"].get("old_slot")
                    new_slot = log["action_data"].get("new_slot")
                    
                    # Get Veramon name for the new slot
                    new_veramon_name = "a different Veramon"
                    if log["actor_id"] in battle.veramon and new_slot < len(battle.veramon[log["actor_id"]]):
                        new_veramon = battle.veramon[log["actor_id"]][new_slot]
                        if new_veramon:
                            new_veramon_name = new_veramon.display_name
                            
                    log_texts.append(f"{actor_name} switched to **{new_veramon_name}**!")
                elif log["action_type"] == "flee":
                    actor_name = "You" if log["actor_id"] == user_id else f"<@{log['actor_id']}>"
                    
                    if log["result_data"].get("success"):
                        log_texts.append(f"{actor_name} fled from the battle!")
                    else:
                        log_texts.append(f"{actor_name} tried to flee but failed!")
                        
            if log_texts:
                embed.add_field(
                    name="Battle Log",
                    value="\n".join(log_texts),
                    inline=False
                )
        
        return embed
        
    async def _handle_battle_end(self, channel, battle):
        """Handle the end of a battle."""
        # Award XP and rewards
        winner_id = battle.winner_id
        
        # For a draw or cancelled battle, no rewards
        if winner_id == "draw" or battle.status == BattleStatus.CANCELLED:
            await channel.send("The battle ended with no winner.")
            return
            
        # Create end of battle embed
        embed = discord.Embed(
            title="Battle Results",
            description="The battle has ended!",
            color=discord.Color.gold()
        )
        
        if winner_id.startswith("npc_"):
            embed.add_field(
                name="Winner",
                value="NPC Trainer",
                inline=False
            )
            
            # No rewards for losing to NPC
            await channel.send(embed=embed)
            return
            
        # For PvP battles, give rewards to winner
        if battle.battle_type == BattleType.PVP:
            # Calculate XP and tokens based on battle difficulty
            xp_gained = 100  # Base XP
            tokens_gained = 20  # Base tokens
            
            # Adjust based on opponent's Veramon
            opponent_id = next((pid for pid in battle.participants if pid != winner_id), None)
            if opponent_id and opponent_id in battle.veramon:
                # Calculate average level of opponent's Veramon
                opponent_veramon = [v for v in battle.veramon[opponent_id] if v is not None]
                if opponent_veramon:
                    avg_level = sum(v.level for v in opponent_veramon) / len(opponent_veramon)
                    xp_gained += int(avg_level * 5)
                    tokens_gained += int(avg_level)
                    
            # Award XP to winner's Veramon
            if winner_id in battle.veramon:
                winner_veramon = [v for v in battle.veramon[winner_id] if v is not None]
                
                # Update each Veramon's XP
                xp_entries = []
                for veramon in winner_veramon:
                    if veramon and veramon.capture_id:
                        # Split XP among participating Veramon
                        veramon_xp = xp_gained // len(winner_veramon)
                        
                        # Apply XP gain
                        new_level, evolved, evolution_name = veramon.gain_experience(veramon_xp)
                        
                        # Store results for database update
                        xp_entries.append({
                            "capture_id": veramon.capture_id,
                            "xp_gained": veramon_xp,
                            "new_level": new_level,
                            "evolved": evolved,
                            "evolution_name": evolution_name
                        })
                
                # Update database
                conn = get_connection()
                cursor = conn.cursor()
                
                for entry in xp_entries:
                    # Update Veramon XP and level
                    cursor.execute("""
                        UPDATE captures
                        SET experience = experience + ?, level = ?
                        WHERE id = ?
                    """, (entry["xp_gained"], entry["new_level"], entry["capture_id"]))
                    
                    # Handle evolution if needed
                    if entry["evolved"] and entry["evolution_name"]:
                        cursor.execute("""
                            UPDATE captures
                            SET veramon_name = ?
                            WHERE id = ?
                        """, (entry["evolution_name"], entry["capture_id"]))
                
                # Award tokens to winner
                cursor.execute("""
                    UPDATE users
                    SET tokens = tokens + ?,
                        xp = xp + ?
                    WHERE user_id = ?
                """, (tokens_gained, xp_gained // 2, winner_id))
                
                conn.commit()
                conn.close()
                
                # Create winner embed
                embed.add_field(
                    name="Winner",
                    value=f"<@{winner_id}>",
                    inline=False
                )
                
                embed.add_field(
                    name="Rewards",
                    value=f"XP: {xp_gained}\nTokens: {tokens_gained}",
                    inline=False
                )
                
                # Add evolution information
                evolutions = [e for e in xp_entries if e["evolved"]]
                if evolutions:
                    evo_text = ""
                    for evo in evolutions:
                        cursor.execute("""
                            SELECT nickname FROM captures WHERE id = ?
                        """, (evo["capture_id"],))
                        nickname_row = cursor.fetchone()
                        nickname = nickname_row[0] if nickname_row and nickname_row[0] else evo["evolution_name"]
                        
                        evo_text += f"• Your Veramon evolved into **{nickname}**!\n"
                        
                    embed.add_field(
                        name="Evolutions",
                        value=evo_text,
                        inline=False
                    )
                
                # Update quest progress for battle wins
                try:
                    # Get EconomyCog to update quest progress
                    economy_cog = self.bot.get_cog("EconomyCog")
                    if economy_cog:
                        battle_win_type = "pvp_win" if battle.battle_type == BattleType.PVP.value else "battle_win"
                        completed_quests = await economy_cog.update_quest_progress(
                            winner_id, 
                            battle_win_type, 
                            1, 
                            battle_type=battle.battle_type
                        )
                        
                        # If any quests were completed, add to the embed
                        if completed_quests:
                            quest_text = ""
                            for quest in completed_quests:
                                quest_text += f"• {quest['quest_id']}: +{quest['token_reward']} tokens, +{quest['xp_reward']} XP\n"
                            
                            if quest_text:
                                embed.add_field(
                                    name="🎯 Quests Completed!",
                                    value=quest_text,
                                    inline=False
                                )
                except Exception as e:
                    print(f"Error updating quest progress: {e}")
        
        await channel.send(embed=embed)
        
        # Clean up battle
        if battle.battle_id in self.active_battles:
            del self.active_battles[battle.battle_id]
        
        if battle.battle_id in self.active_views:
            del self.active_views[battle.battle_id]

async def setup(bot: commands.Bot):
    await bot.add_cog(EnhancedBattleCog(bot))
